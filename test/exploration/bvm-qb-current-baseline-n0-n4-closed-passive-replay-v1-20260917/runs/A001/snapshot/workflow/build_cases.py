#!/usr/bin/env python3
"""Build and execute the registered 15-run N0-N4 baseline.

This is a series-local runner. It intentionally does not implement a global
experiment manager or scientific verdict engine. The three families are built
and solved in dependency order: CLOSED, PASSIVE, then exact PASSIVE-current
REPLAY into the current QB/JTL receiver.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
from datetime import datetime
from decimal import Decimal, localcontext
from pathlib import Path
from typing import Any

SERIES = Path(__file__).resolve().parents[1]
REPO = next((path for path in (SERIES, *SERIES.parents) if (path / ".git").exists()), SERIES)
sys.path.insert(0, str(REPO / "scripts"))

FAMILIES = ("CLOSED", "PASSIVE", "REPLAY")
MASKS = ("0000", "0001", "0011", "0111", "1111")
CASE_ORDER = tuple(f"{family}_N{index}_{mask}" for family in FAMILIES for index, mask in enumerate(MASKS))
EXPECTED_SOLVES = 15
BIT_ORDER = "b3b2b1b0=BVM1/BVM2/BVM3/BVM4"
WINDOWS = ((0, 50), (50, 61), (61, 70), (70, 81), (81, 90), (90, 101), (101, 110), (110, 121), (121, 130), (130, 150), (150, 200), (0, 200))
WINDOW_LABELS = ("idle_0_50", "write0_50_61", "settle0_61_70", "zero_read_control_70_81", "settle1_81_90", "write1_90_101", "settle_101_110", "final_read_110_121", "tail_121_130", "tail_130_150", "tail_150_200", "whole_0_200")
EXPECTED_QB = {"Lin_pH": 1.5, "L1_pH": 1.4, "L2_pH": 2.0, "BJS_area": 4.0, "BJ1_area": 0.9, "RJ1_ohm": 32.0, "BJ2_area": 2.0, "RJ2_ohm": 12.0, "L3_pH": 1.3, "IBias_uA": 260.0}
PROTOCOL_REFERENCE = REPO / "test" / "exploration" / "bvm-qb-threshold-ordering-boundary-search-v1-20260911" / "references" / "canonical_baseline" / "0011" / "deck.cir"
FINAL_MARKER = "EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW"
CONTRACT = "This experiment is governed by docs/EXPERIMENT_CONTRACT.md."


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"expected JSON object: {path}")
    return value


def repo_rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def resolve(value: str) -> Path:
    path = Path(value)
    return path.resolve() if path.is_absolute() else (SERIES / path).resolve()


def git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()


def remote_head() -> str | None:
    try:
        output = subprocess.check_output(["git", "ls-remote", "bvm", "refs/heads/master"], cwd=REPO, text=True, timeout=30).strip()
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None
    return output.split()[0] if output else None


def git_snapshot() -> dict[str, Any]:
    status = subprocess.check_output(["git", "status", "--short", "--untracked-files=all"], cwd=REPO, text=True)
    return {"head": git_head(), "remote_bvm_master": remote_head(), "working_tree_dirty": bool(status), "status_porcelain": status}


def solver_snapshot(path: Path) -> dict[str, Any]:
    result: dict[str, Any] = {"path": repo_rel(path), "sha256": sha256(path), "bytes": path.stat().st_size}
    version = subprocess.run([str(path), "--version"], cwd=REPO, capture_output=True, text=True, check=False)
    result.update({"version_returncode": version.returncode, "version_stdout": version.stdout.strip(), "version_stderr": version.stderr.strip()})
    return result


def parse_value(token: str) -> float:
    match = re.fullmatch(r"\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)([munpfk]?)\s*", token, flags=re.IGNORECASE)
    if not match:
        raise RuntimeError(f"cannot parse numeric token: {token!r}")
    number = float(match.group(1))
    suffix = match.group(2).lower()
    scale = {"": 1.0, "p": 1.0, "n": 1.0e3, "u": 1.0e6, "m": 1.0e9, "f": 1.0e-3, "k": 1.0e3}[suffix]
    return number * scale


def qb_capture(pattern: str, text: str, label: str) -> float:
    match = re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
    if not match:
        raise RuntimeError(f"current QB parameter not found: {label}")
    return parse_value(match.group(1))


def qb_capture_microamps(pattern: str, text: str, label: str) -> float:
    match = re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
    if not match:
        raise RuntimeError(f"current QB parameter not found: {label}")
    token = match.group(1).strip()
    number = re.fullmatch(r"([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)(?:u)?", token, flags=re.IGNORECASE)
    if not number:
        raise RuntimeError(f"cannot parse microamp token for {label}: {token!r}")
    return float(number.group(1))


def extract_qb_parameters(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    values = {
        "Lin_pH": qb_capture(r"^\s*Lin\s+IN\s+1\s+([^\s]+)", text, "Lin"),
        "L1_pH": qb_capture(r"^\s*L1\s+2\s+3\s+([^\s]+)", text, "L1"),
        "L2_pH": qb_capture(r"^\s*L2\s+3\s+4\s+([^\s]+)", text, "L2"),
        "BJS_area": qb_capture(r"^\s*BJS\s+1\s+2\s+jjmit\s+area=([^\s]+)", text, "BJS area"),
        "BJ1_area": qb_capture(r"^\s*BJ1\s+2\s+0\s+jjmit\s+area=([^\s]+)", text, "BJ1 area"),
        "RJ1_ohm": qb_capture(r"^\s*RJ1\s+2\s+0\s+([^\s]+)", text, "RJ1"),
        "BJ2_area": qb_capture(r"^\s*BJ2\s+4\s+0\s+jjmit\s+area=([^\s]+)", text, "BJ2 area"),
        "RJ2_ohm": qb_capture(r"^\s*RJ2\s+4\s+0\s+([^\s]+)", text, "RJ2"),
        "L3_pH": qb_capture(r"^\s*L3\s+4\s+OUT\s+([^\s]+)", text, "L3"),
        "IBias_uA": qb_capture_microamps(r"^\s*IB\s+0\s+3\s+pwl\([^\n]*?\s([^\s()]+)\s*\)", text, "IBias"),
    }
    mismatches = {key: {"expected": EXPECTED_QB[key], "actual": value} for key, value in values.items() if not math.isclose(value, EXPECTED_QB[key], rel_tol=0.0, abs_tol=1.0e-12)}
    return {"path": repo_rel(path), "sha256": sha256(path), "bytes": path.stat().st_size, "extracted": values, "expected": EXPECTED_QB, "status": "PASS" if not mismatches else "FAIL", "mismatches": mismatches}


def record_file(role: str, path: Path, snapshot: Path | None = None) -> dict[str, Any]:
    result = {"role": role, "path": repo_rel(path), "sha256": sha256(path), "bytes": path.stat().st_size}
    if snapshot is not None:
        result["snapshot_path"] = repo_rel(snapshot)
    return result


def case_id(family: str, mask: str) -> str:
    return f"{family}_N{mask.count('1')}_{mask}"


def case_dir(attempt: Path, family: str, mask: str) -> Path:
    return attempt / "cases" / case_id(family, mask)


def source_points(mask: str, index: int, name: str) -> list[tuple[float, float]]:
    active = mask[index - 1] == "1"
    amplitude = 100.0
    final = amplitude if active and name in {"WL", "SE"} else 0.0
    write0 = -amplitude if name in {"WL", "BL"} else 0.0
    zero_read = amplitude if name in {"WL", "SE"} else 0.0
    write1 = amplitude if name in {"WL", "BL"} else 0.0
    return [(0, 0), (50, 0), (51, write0), (60, write0), (61, 0), (70, 0), (71, zero_read), (80, zero_read), (81, 0), (90, 0), (91, write1), (100, write1), (101, 0), (110, 0), (111, final), (120, final), (121, 0), (200, 0)]


def pwl(name: str, node: str, points: list[tuple[float, float]]) -> str:
    values: list[str] = []
    for time_ps, current_ua in points:
        current = "0" if current_ua == 0 else f"{current_ua:+g}u"
        time_token = "0" if time_ps == 0 else f"{time_ps:g}p"
        values.extend([time_token, current])
    return f"I_{name} 0 {node} pwl(" + " ".join(values) + ")"


def generated_stimulus(mask: str) -> str:
    lines = [f"* GENERATED baseline stimulus; mask={mask}; {BIT_ORDER}", "* IDLE 0-50; WRITE0 50-61; zero-state read control 70-81; WRITE1 90-101; SETTLE 101-110; final READ 110-121; TAIL 121-200."]
    for index in range(1, 5):
        lines.extend([pwl(f"WL{index}", f"WL{index}", source_points(mask, index, "WL")), pwl(f"BL{index}", f"BL{index}", source_points(mask, index, "BL")), pwl(f"SE{index}", f"SE{index}", source_points(mask, index, "SE"))])
    return "\n".join(lines) + "\n"


def probe_lines(family: str) -> list[str]:
    lines: list[str] = []
    if family in {"CLOSED", "PASSIVE"}:
        lines.append(".print " + " ".join(f"I(I_{name}{index})" for index in range(1, 5) for name in ("WL", "BL", "SE")))
        junctions = ("B_JM1", "B_JM2", "B_JS1", "B_JS2")
        branches = ("L_M1", "L_M2", "L_M3", "L_PM", "R_JM1", "L_S1", "L_S2", "R_S", "L_S3", "R_SE", "L_PSE", "L_PSL", "R_SL", "L_SL")
        for index in range(1, 5):
            for element in junctions:
                lines.append(f".print P({element}|XBVM{index}) V({element}|XBVM{index}) I({element}|XBVM{index})")
            for element in branches:
                lines.append(f".print I({element}|XBVM{index}) V({element}|XBVM{index})")
        lines.append(".print V(COMMON_SL)")
        for index in range(1, 9):
            lines.append(f".print P(B_JSL{index}) V(B_JSL{index}) I(B_JSL{index})")
        if family == "PASSIVE":
            return lines
    if family == "REPLAY":
        lines.append(".print V(QBIN) V(QBOUT) I(I_REPLAY)")
    else:
        lines.append(".print V(QBIN) V(QBOUT)")
    lines.extend([
        ".print I(LIN|XBQ1) V(LIN|XBQ1) I(L1|XBQ1) V(L1|XBQ1) I(L2|XBQ1) V(L2|XBQ1) I(L3|XBQ1) V(L3|XBQ1)",
        ".print I(RJ1|XBQ1) V(RJ1|XBQ1) I(RJ2|XBQ1) V(RJ2|XBQ1) I(IB|XBQ1) V(IB|XBQ1)",
    ])
    for junction in ("BJS", "BJ1", "BJ2"):
        lines.append(f".print P({junction}|XBQ1) V({junction}|XBQ1) I({junction}|XBQ1)")
    for stage in range(1, 7):
        lines.append(f".print P(B01|XJTL1_{stage}) V(B01|XJTL1_{stage}) I(B01|XJTL1_{stage}) P(B02|XJTL1_{stage}) V(B02|XJTL1_{stage}) I(B02|XJTL1_{stage})")
        lines.append(f".print V(JTL{stage}_OUT)")
    lines.append(".print I(R_TERM) V(R_TERM)")
    return lines


def template_for(family: str, args: argparse.Namespace) -> Path:
    value = {"CLOSED": args.closed_top_deck, "PASSIVE": args.passive_top_deck, "REPLAY": args.replay_top_deck}[family]
    return resolve(value)


def include_line(snapshot_source: Path | None, case: Path, role: str) -> str:
    if snapshot_source is None:
        return f"* {role}: INLINE_OR_ABSENT"
    return f".include {Path(os.path.relpath(snapshot_source, case)).as_posix()}"


def render_deck(family: str, mask: str, args: argparse.Namespace, attempt: Path, case: Path, selected: dict[str, Path], stimulus: Path) -> str:
    text = template_for(family, args).read_text(encoding="utf-8")
    replacements = {
        "{{JJ_INCLUDE}}": include_line(selected.get("JJ_MODEL"), case, "JJ_MODEL"),
        "{{BVM_INCLUDE}}": include_line(selected.get("BVM"), case, "BVM"),
        "{{QB_INCLUDE}}": include_line(selected.get("QB"), case, "QB"),
        "{{JTL_INCLUDE}}": include_line(selected.get("JTL"), case, "JTL"),
        "{{STIMULUS_INCLUDE}}": f".include {Path(os.path.relpath(stimulus, case)).as_posix()}",
        "{{PROBES}}": "\n".join(probe_lines(family)),
        "{{DT}}": args.dt,
        "{{STOP_TIME}}": args.stop_time,
        "{{MASK}}": mask,
    }
    for marker, value in replacements.items():
        text = text.replace(marker, value)
    if "{{" in text:
        raise RuntimeError(f"unresolved top-deck marker in {family} {mask}")
    if family == "PASSIVE" and any(token in text for token in ("XBQ1", "XJTL1_", "R_TERM")):
        raise RuntimeError("PASSIVE deck contains QB/JTL/terminal")
    if family in {"CLOSED", "REPLAY"} and any(token not in text for token in ("XBQ1 QBIN QBOUT BQ", "XJTL1_6 JTL5_OUT JTL6_OUT jtl", "R_TERM JTL6_OUT 0 10")):
        raise RuntimeError(f"{family} forward path is incomplete")
    if family == "PASSIVE" and "B_JSL8 JSL_NODE7 0 jjmit area=5.0" not in text:
        raise RuntimeError("PASSIVE endpoint convention is not B_JSL8 JSL_NODE7 0")
    if ".tran 0.1p 200p" not in text:
        raise RuntimeError("registered .tran is not exact 0.1p 200p")
    return text if text.endswith("\n") else text + "\n"


def read_raw_columns(path: Path) -> tuple[list[str], list[list[str]]]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        rows = list(csv.reader(stream))
    if not rows or not rows[0]:
        raise RuntimeError(f"empty raw: {path}")
    if len(rows[0]) != len(set(rows[0])):
        raise RuntimeError(f"duplicate raw columns: {path}")
    return rows[0], rows[1:]


def replay_stimulus(passive_raw: Path, output: Path, source_signal: str) -> dict[str, Any]:
    headers, rows = read_raw_columns(passive_raw)
    if "time" not in headers or source_signal not in headers:
        raise RuntimeError(f"replay source columns missing in {passive_raw}: {source_signal}")
    time_index = headers.index("time")
    current_index = headers.index(source_signal)
    if len(rows) != 1999:
        raise RuntimeError(f"unexpected passive sample count for replay: {len(rows)}")
    times = [Decimal(row[time_index]) for row in rows]
    if any(right <= left for left, right in zip(times, times[1:])):
        raise RuntimeError("passive replay source grid is not strictly increasing")
    pairs: list[str] = []
    with localcontext() as context:
        context.prec = 60
        for row in rows:
            value = Decimal(row[time_index]) * Decimal("1e12")
            time_text = format(value, "f").rstrip("0").rstrip(".") if "." in format(value, "f") else format(value, "f")
            pairs.append(f"{time_text or '0'}p {row[current_index]}")
    lines = [f"* EXACT stored-grid replay from {passive_raw}", f"* source_signal={source_signal}; orientation=B_JSL8 JSL_NODE7 -> 0; replay=I_REPLAY 0 -> QBIN; no transformation."]
    for start in range(0, len(pairs), 18):
        chunk = pairs[start : start + 18]
        prefix = "I_REPLAY 0 QBIN pwl(" if start == 0 else "+ "
        suffix = ")" if start + 18 >= len(pairs) else ""
        lines.append(prefix + " ".join(chunk) + suffix)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"source_raw_path": repo_rel(passive_raw), "source_raw_sha256": sha256(passive_raw), "source_signal": source_signal, "source_column_index": current_index, "sample_count": len(rows), "time_start_ps": float(times[0] * Decimal("1e12")), "time_end_ps": float(times[-1] * Decimal("1e12")), "same_timestamps": True, "sign_change": False, "interpolation": False, "smoothing": False, "resampling": False, "replay_orientation": "I_REPLAY 0 QBIN; positive current toward downstream QBIN"}


def snapshot_sources(args: argparse.Namespace, attempt: Path) -> tuple[dict[str, Any], dict[str, Path]]:
    snapshot = attempt / "snapshot"
    sources_dir = snapshot / "sources"
    tops_dir = snapshot / "tops"
    workflow_dir = snapshot / "workflow"
    sources_dir.mkdir(parents=True, exist_ok=False)
    tops_dir.mkdir(parents=True, exist_ok=False)
    workflow_dir.mkdir(parents=True, exist_ok=False)
    selected: dict[str, Path] = {}
    records: list[dict[str, Any]] = []
    source_values = (("JJ_MODEL", args.jj_model), ("BVM", args.bvm_circuit), ("QB", args.qb_circuit), ("JTL", args.jtl_circuit))
    for role, value in source_values:
        source = resolve(value)
        if not source.is_file():
            raise RuntimeError(f"{role} source missing: {source}")
        target = sources_dir / source.name
        shutil.copy2(source, target)
        selected[role] = target
        records.append(record_file(role, source, target))
    for family, value in (("CLOSED", args.closed_top_deck), ("PASSIVE", args.passive_top_deck), ("REPLAY", args.replay_top_deck)):
        source = resolve(value)
        if not source.is_file():
            raise RuntimeError(f"{family} TOP_DECK missing: {source}")
        target = tops_dir / f"{family.lower()}_top.cir"
        shutil.copy2(source, target)
        records.append(record_file(f"TOP_{family}", source, target))
    for source in (SERIES / "run.sh", SERIES / "analyze.sh", SERIES / "plot.sh", Path(__file__), SERIES / "scripts" / "analyze.py", SERIES / "scripts" / "render_plots.py", SERIES / "scripts" / "package.py"):
        target = workflow_dir / source.name
        shutil.copy2(source, target)
        records.append(record_file(f"WORKFLOW_{source.name}", source, target))
    return {"schema": "bvm-qb-current-baseline-source-manifest-v1", "created_at": now(), "sources": records, "bit_order": BIT_ORDER, "current_qb_authority": extract_qb_parameters(resolve(args.qb_circuit)), "read_only_implementation_references": [{"path": repo_rel(PROTOCOL_REFERENCE), "sha256": sha256(PROTOCOL_REFERENCE), "role": "2026-09-11 topology/protocol reference only; raw not copied"}], "raw_not_copied_from_history": True}, selected


def write_series_registration(args: argparse.Namespace, source_manifest: dict[str, Any], parent: dict[str, Any]) -> None:
    qb = source_manifest["current_qb_authority"]
    preflight = f"""# Current QB N0-N4 closed/passive/replay baseline

{CONTRACT}

## Registration

- Experiment ID: `{SERIES.name}`
- Parent HEAD: `{parent['head']}`; remote `bvm/master`: `{parent['remote_bvm_master']}`.
- Study phase: `CALIBRATION`; role: `Experimental Operator + Evidence Packager`.
- Scientific interpretation: not authorized; this series reports exhaustive raw, mechanical statistics, and visualization QA only.
- Bit order: `{BIT_ORDER}`. Masks are N0=`0000`, N1=`0001`, N2=`0011`, N3=`0111`, N4=`1111`.
- Exact authorized solve count: `15`, in family order CLOSED N0-N4, PASSIVE N0-N4, REPLAY N0-N4.

## Frozen source authority

- JJ model: `{args.jj_model}`; SHA-256 `{source_manifest['sources'][0]['sha256']}`.
- BVM: `{args.bvm_circuit}`; SHA-256 `{next(item['sha256'] for item in source_manifest['sources'] if item['role'] == 'BVM')}`.
- Current QB: `{args.qb_circuit}`; SHA-256 `{qb['sha256']}`.
- JTL: `{args.jtl_circuit}`; SHA-256 `{next(item['sha256'] for item in source_manifest['sources'] if item['role'] == 'JTL')}`.
- Current QB extraction: `{json.dumps(qb['extracted'], sort_keys=True)}`; expected values: `{json.dumps(qb['expected'], sort_keys=True)}`; status `{qb['status']}`.

## Frozen stimulus

- IDLE 0-50 ps; WRITE0 50-61 ps; zero-state read control 70-81 ps; WRITE1 90-101 ps; SETTLE 101-110 ps; final READ 110-121 ps; TAIL 121-200 ps.
- Amplitude 100 uA; edge 1 ps; plateau 9 ps; `.tran 0.1p 200p`; expected raw grid 0-199.9 ps.
- Only the final-read mask differs across N0-N4. No timing or amplitude modification is registered.

## Families

- CLOSED: BVM array -> COMMON_SL -> JSL1..8 -> current QB -> six-stage JTL -> 10 ohm terminal.
- PASSIVE: BVM array -> COMMON_SL -> JSL1..8; QB/JTL/terminal removed; `B_JSL8 JSL_NODE7 0` retained as the established passive endpoint convention.
- REPLAY: exact stored `I(B_JSL8)` from this experiment's PASSIVE raw -> `I_REPLAY 0 QBIN` -> current QB -> six-stage JTL -> 10 ohm terminal. No interpolation, smoothing, resampling, scaling, or sign correction.

## Analysis and visualization boundary

- Each run retains untouched raw, actual deck, stimulus, logs, metadata, and signal manifest.
- Per-signal windows are 0-50, 50-61, 61-70, 70-81, 81-90, 90-101, 101-110, 110-121, 121-130, 130-150, 150-200, and 0-200 ps.
- Phase is retained in raw radians; unwrapped radians and `rad/(2*pi)` turns are navigation views only, never formal SFQ counts.
- No cross-run comparison visualization and no scientific mechanism, winner, or population interpretation is generated.

Final stop marker: `{FINAL_MARKER}`.
"""
    (SERIES / "PREFLIGHT.md").write_text(preflight, encoding="utf-8")
    (SERIES / "experiment.yaml").write_text("\n".join([
        "schema_version: bvm-qb-current-baseline-n0-n4-closed-passive-replay-v1",
        f"id: {SERIES.name}",
        "study_phase: CALIBRATION",
        "role: Experimental Operator + Evidence Packager",
        "status: PREFLIGHT_PASS",
        f"registration_head: {parent['head']}",
        f"remote_bvm_master_at_registration: {parent['remote_bvm_master']}",
        f"working_tree_dirty_at_registration: {parent['working_tree_dirty']}",
        f"contract_sentence: {CONTRACT}",
        "scientific_review_authorized: false",
        f"bit_order: {BIT_ORDER}",
        "masks: [0000, 0001, 0011, 0111, 1111]",
        "authorized_solve_count: 15",
        "family_order: [CLOSED, PASSIVE, REPLAY]",
        f"case_order: {json.dumps(list(CASE_ORDER), ensure_ascii=False)}",
        "stimulus: IDLE=0-50ps, WRITE0=50-61ps, ZERO_READ=70-81ps, WRITE1=90-101ps, SETTLE=101-110ps, FINAL_READ=110-121ps, TAIL=121-200ps",
        "amplitude_uA: 100",
        "edge_ps: 1",
        "plateau_ps: 9",
        "dt: 0.1p",
        "stop_time: 200p",
        "replay_source_signal: I(B_JSL8)",
        "replay_orientation: I_REPLAY 0 QBIN",
        "no_cross_run_comparison_plots: true",
        "scientific_classification: NOT_ASSIGNED_SCIENTIFIC_REVIEW_REQUIRED",
        "",
        "current_qb_parameters:",
    ] + [f"  {key}: {value}" for key, value in qb["extracted"].items()] + ["", "source_manifest: analysis/SOURCE_MANIFEST.json", ""]), encoding="utf-8")
    write_json(SERIES / "SOURCE_MANIFEST.json", source_manifest)
    write_json(SERIES / "analysis" / "SOURCE_MANIFEST.json", source_manifest)


def initial_provenance(args: argparse.Namespace, parent: dict[str, Any], source_manifest: dict[str, Any]) -> dict[str, Any]:
    solver = resolve(args.josim_bin)
    return {"schema": "bvm-qb-current-baseline-n0-n4-closed-passive-replay-provenance-v1", "experiment_id": SERIES.name, "created_at": now(), "parent": parent, "contract_sentence": CONTRACT, "scientific_interpretation_performed": False, "solver": solver_snapshot(solver), "source_manifest": source_manifest, "authorized": {"solve_count": EXPECTED_SOLVES, "case_order": list(CASE_ORDER), "no_cross_run_comparison": True}, "runs": {}, "run_order": [], "analysis": {"status": "PENDING"}, "qa": {"status": "PENDING"}, "visualization": {"status": "PENDING"}, "package": {"status": "PENDING"}, "stop": {"final_marker": None, "automatic_follow_up": False}}


def dry_run(args: argparse.Namespace) -> None:
    qb = extract_qb_parameters(resolve(args.qb_circuit))
    attempt = next_attempt()
    print("EXPERIMENT")
    print(f"  id: {SERIES.name}")
    print(f"  parent: {git_head()}")
    print(f"  ATTEMPT would be: {attempt}")
    print("CIRCUITS")
    print(f"  TOP CLOSED: {args.closed_top_deck}")
    print(f"  TOP PASSIVE: {args.passive_top_deck}")
    print(f"  TOP REPLAY: {args.replay_top_deck}")
    print(f"  BVM: {args.bvm_circuit}")
    print(f"  QB: {args.qb_circuit} ({qb['status']})")
    print(f"  JTL: {args.jtl_circuit}")
    print("STIMULUS")
    print(f"  mode: {args.stimulus_mode}")
    print(f"  mask(s): {' '.join(args.masks)}")
    print("  history: IDLE 0-50; WRITE0 50-61; ZERO_READ 70-81; WRITE1 90-101; SETTLE 101-110; FINAL_READ 110-121; TAIL 121-200 ps")
    print("  amplitude: WL/BL/SE=100uA; edges=1ps; plateau=9ps")
    print("EXPERIMENT PARAMETERS")
    print(f"  bit order: {BIT_ORDER}")
    print("  families: CLOSED, PASSIVE, REPLAY")
    print("SOLVER")
    print(f"  JoSIM: {args.josim_bin}")
    print(f"  dt: {args.dt}")
    print(f"  stop: {args.stop_time}")
    print("CASES")
    for family in FAMILIES:
        for mask in MASKS:
            key = case_id(family, mask)
            deck = SERIES / "runs" / attempt / "cases" / key / "actual_deck.cir"
            raw = SERIES / "runs" / attempt / "cases" / key / "raw.csv"
            print(f"  {key}: actual_deck={deck} raw={raw} exact_cli={shlex.join([args.josim_bin, '-a', '1', '-o', str(raw), str(deck)])}")
    print("TOTAL SOLVES")
    print("  15")
    print("DRY_RUN: no attempt created; JoSIM not invoked")


def next_attempt(create: bool = False) -> str:
    runs = SERIES / "runs"
    if create:
        runs.mkdir(parents=True, exist_ok=True)
    numbers = [int(match.group(1)) for path in runs.iterdir() if path.is_dir() and (match := re.fullmatch(r"A(\d+)", path.name))] if runs.is_dir() else []
    return f"A{max(numbers, default=0) + 1:03d}"


def prepare_attempt(args: argparse.Namespace) -> tuple[Path, dict[str, Any], dict[str, Path], dict[str, Any]]:
    if remote_head() != git_head():
        raise RuntimeError(f"HEAD and remote master differ: {git_head()} vs {remote_head()}")
    if tuple(args.masks) != MASKS or args.stimulus_mode != "generated" or args.bit_order != BIT_ORDER:
        raise RuntimeError("registered baseline requires generated stimulus and masks 0000/0001/0011/0111/1111")
    if args.dt != "0.1p" or args.stop_time != "200p":
        raise RuntimeError("registered baseline requires .tran 0.1p 200p")
    if not math.isclose(float(args.terminal_ohm), 10.0) or not math.isclose(float(args.jsl_area), 5.0):
        raise RuntimeError("registered baseline requires terminal=10 ohm and JSL area=5.0")
    protocol_values = {
        "write0_start_ps": 50.0, "write0_rise_ps": 1.0, "write0_fall_ps": 1.0, "write0_width_ps": 9.0,
        "zero_read_start_ps": 70.0, "zero_read_rise_ps": 1.0, "zero_read_fall_ps": 1.0, "zero_read_width_ps": 9.0,
        "write1_start_ps": 90.0, "write1_rise_ps": 1.0, "write1_fall_ps": 1.0, "write1_width_ps": 9.0,
        "final_read_start_ps": 110.0, "final_read_rise_ps": 1.0, "final_read_fall_ps": 1.0, "final_read_width_ps": 9.0,
        "wl_amplitude_ua": 100.0, "bl_amplitude_ua": 100.0, "se_amplitude_ua": 100.0,
    }
    protocol_mismatches = {name: {"expected": expected, "actual": getattr(args, name)} for name, expected in protocol_values.items() if not math.isclose(float(getattr(args, name)), expected, rel_tol=0.0, abs_tol=1.0e-12)}
    if protocol_mismatches:
        raise RuntimeError(f"FROZEN_STIMULUS_PROTOCOL_MISMATCH: {json.dumps(protocol_mismatches, sort_keys=True)}")
    if resolve(args.qb_circuit).resolve() != (REPO / "circuits/qb/bq_parameterized_v1.cir").resolve():
        raise RuntimeError("current QB authority must be circuits/qb/bq_parameterized_v1.cir")
    qb = extract_qb_parameters(resolve(args.qb_circuit))
    if qb["status"] != "PASS":
        raise RuntimeError(f"CURRENT_QB_PARAMETER_MISMATCH: {json.dumps(qb['mismatches'], sort_keys=True)}")
    for path_value in (args.closed_top_deck, args.passive_top_deck, args.replay_top_deck, args.jj_model, args.bvm_circuit, args.qb_circuit, args.jtl_circuit, args.josim_bin):
        if not resolve(path_value).is_file():
            raise RuntimeError(f"missing registered source: {resolve(path_value)}")
    if SERIES.exists():
        allowed = {"run.sh", "analyze.sh", "plot.sh", "README.md", "scripts", "circuits", "__pycache__"}
        stale = [path for path in SERIES.iterdir() if path.name not in allowed]
        if stale:
            raise RuntimeError(f"series already contains experiment artifacts; use a new series ID: {stale}")
    parent = git_snapshot()
    attempt = SERIES / "runs" / next_attempt(create=True)
    attempt.mkdir(parents=True, exist_ok=False)
    source_manifest, selected = snapshot_sources(args, attempt)
    source_manifest["registration_parent"] = parent
    source_manifest["current_qb_parameter_check"] = qb
    source_manifest["run_sh_sha256"] = sha256(SERIES / "run.sh")
    write_series_registration(args, source_manifest, parent)
    provenance = initial_provenance(args, parent, source_manifest)
    write_json(SERIES / "provenance.json", provenance)
    write_json(SERIES / "result.json", {"schema": "bvm-qb-current-baseline-n0-n4-closed-passive-replay-result-v1", "experiment_id": SERIES.name, "status": "PREFLIGHT_PASS", "artifact_status": "PENDING", "authorized_solve_count": EXPECTED_SOLVES, "actual_physical_solve_count": 0, "run_order": [], "families": {family: {"status": "NOT_RUN"} for family in FAMILIES}, "qa": {"status": "PENDING"}, "visualization": {"status": "PENDING"}, "scientific_interpretation_performed": False, "stop": {"final_marker": None, "automatic_follow_up": False}})
    write_json(attempt / "snapshot" / "source_manifest.json", source_manifest)
    return attempt, provenance, selected, source_manifest


def write_case_files(family: str, mask: str, args: argparse.Namespace, attempt: Path, selected: dict[str, Path], replay_meta: dict[str, Any] | None = None) -> dict[str, Any]:
    directory = case_dir(attempt, family, mask)
    directory.mkdir(parents=True, exist_ok=False)
    stimulus = directory / "stimulus.inc"
    if family == "REPLAY":
        if replay_meta is None:
            raise RuntimeError("REPLAY requires passive source metadata")
        passive_raw = REPO / replay_meta["source_raw_path"]
        replay_source = replay_stimulus(passive_raw, stimulus, args.replay_source_signal)
    else:
        stimulus.write_text(generated_stimulus(mask), encoding="utf-8")
        replay_source = {"mode": "generated_canonical_history", "mask": mask, "sha256": sha256(stimulus), "bytes": stimulus.stat().st_size, "path": repo_rel(stimulus)}
    deck_text = render_deck(family, mask, args, attempt, directory, selected, stimulus)
    actual = directory / "actual_deck.cir"
    actual.write_text(deck_text, encoding="utf-8")
    compatibility = directory / "deck.cir"
    compatibility.write_text(deck_text, encoding="utf-8")
    return {"run_id": case_id(family, mask), "family": family, "mask": mask, "path": repo_rel(actual), "actual_deck": {"path": repo_rel(actual), "sha256": sha256(actual), "bytes": actual.stat().st_size}, "deck_compatibility": {"path": repo_rel(compatibility), "sha256": sha256(compatibility), "bytes": compatibility.stat().st_size, "identical_to_actual_deck": sha256(actual) == sha256(compatibility)}, "stimulus": replay_source if family == "REPLAY" else {"path": repo_rel(stimulus), "sha256": sha256(stimulus), "bytes": stimulus.stat().st_size, "mode": "generated", "mask": mask}, "probes": {"family": family, "generated_by": repo_rel(Path(__file__)), "exhaustive": family != "REPLAY" or True}}


def solve_case(case_record: dict[str, Any], args: argparse.Namespace, attempt: Path, provenance: dict[str, Any]) -> None:
    directory = REPO / case_record["path"]
    raw = directory / "raw.csv"
    stdout = directory / "stdout.txt"
    stderr = directory / "stderr.txt"
    log = directory / "run.log"
    metadata = directory / "metadata.json"
    command = [str(resolve(args.josim_bin)), "-a", "1", "-o", str(raw), str(directory / "actual_deck.cir")]
    started = now()
    clock = time.monotonic()
    completed = subprocess.run(command, cwd=directory, capture_output=True, text=True, check=False)
    runtime = time.monotonic() - clock
    finished = now()
    stdout.write_text(completed.stdout, encoding="utf-8")
    stderr.write_text(completed.stderr, encoding="utf-8")
    log.write_text("\n".join([f"experiment={SERIES.name}", f"run_id={case_record['run_id']}", f"started_at={started}", f"finished_at={finished}", f"runtime_seconds={runtime:.6f}", f"command={shlex.join(command)}", f"exit_code={completed.returncode}", ""]), encoding="utf-8")
    case_record.update({"command": command, "started_at": started, "finished_at": finished, "runtime_seconds": runtime, "stdout": {"path": repo_rel(stdout), "sha256": sha256(stdout), "bytes": stdout.stat().st_size}, "stderr": {"path": repo_rel(stderr), "sha256": sha256(stderr), "bytes": stderr.stat().st_size}, "run_log": {"path": repo_rel(log), "sha256": sha256(log), "bytes": log.stat().st_size}, "solver": solver_snapshot(resolve(args.josim_bin)), "execution_status": "RUN_PASS" if completed.returncode == 0 and raw.is_file() and raw.stat().st_size > 0 else "SOLVER_FAIL", "raw": {"path": repo_rel(raw), "exists": raw.is_file(), "sha256": sha256(raw) if raw.is_file() else None, "bytes": raw.stat().st_size if raw.is_file() else None}})
    write_json(metadata, case_record)
    case_record["metadata"] = {"path": repo_rel(metadata), "sha256": sha256(metadata), "bytes": metadata.stat().st_size}
    provenance["runs"][case_record["run_id"]] = case_record
    provenance["run_order"].append(case_record["run_id"])
    provenance["execution"] = {"authorized_solve_count": EXPECTED_SOLVES, "actual_physical_solve_count": len(provenance["run_order"]), "run_order": provenance["run_order"]}
    write_json(SERIES / "provenance.json", provenance)
    if case_record["execution_status"] != "RUN_PASS":
        raise RuntimeError(f"solver failed; preserved attempt at {attempt}: {case_record['run_id']}")


def run_all(args: argparse.Namespace) -> None:
    attempt, provenance, selected, source_manifest = prepare_attempt(args)
    passive_records: dict[str, Any] = {}
    for family in ("CLOSED", "PASSIVE"):
        for mask in MASKS:
            record = write_case_files(family, mask, args, attempt, selected, None)
            solve_case(record, args, attempt, provenance)
            if family == "PASSIVE":
                passive_records[mask] = record
    for mask in MASKS:
        record = write_case_files("REPLAY", mask, args, attempt, selected, {"source_raw_path": passive_records[mask]["raw"]["path"]})
        solve_case(record, args, attempt, provenance)
    provenance["status"] = "ALL_15_SOLVES_COMPLETE"
    provenance["stop"] = {"final_marker": FINAL_MARKER, "automatic_follow_up": False, "scientific_interpretation_performed": False}
    write_json(SERIES / "provenance.json", provenance)
    write_json(SERIES / "result.json", {"schema": "bvm-qb-current-baseline-n0-n4-closed-passive-replay-result-v1", "experiment_id": SERIES.name, "status": "ALL_15_SOLVES_COMPLETE_ANALYSIS_PENDING", "artifact_status": "PENDING", "authorized_solve_count": EXPECTED_SOLVES, "actual_physical_solve_count": len(provenance["run_order"]), "run_order": provenance["run_order"], "families": {family: {"status": "SOLVE_COMPLETE"} for family in FAMILIES}, "qa": {"status": "PENDING"}, "visualization": {"status": "PENDING"}, "scientific_interpretation_performed": False, "stop": {"final_marker": None, "automatic_follow_up": False}})
    if not args.no_analysis:
        subprocess.run([str(SERIES / "analyze.sh"), attempt.name], cwd=SERIES, check=True)
    if not args.no_plots:
        subprocess.run([str(SERIES / "plot.sh"), attempt.name], cwd=SERIES, check=True)
    subprocess.run([str(sys.executable), str(SERIES / "scripts" / "package.py"), attempt.name], cwd=SERIES, check=True)
    print(json.dumps({"status": "ALL_15_SOLVES_COMPLETE", "attempt": attempt.name, "physical_solve_count": EXPECTED_SOLVES, "analysis_requested": not args.no_analysis, "plots_requested": not args.no_plots}, ensure_ascii=False, indent=2))


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build and run the registered 15-case baseline")
    parser.add_argument("--series-dir", required=True)
    parser.add_argument("--closed-top-deck", required=True)
    parser.add_argument("--passive-top-deck", required=True)
    parser.add_argument("--replay-top-deck", required=True)
    parser.add_argument("--jj-model", required=True)
    parser.add_argument("--bvm-circuit", required=True)
    parser.add_argument("--qb-circuit", required=True)
    parser.add_argument("--jtl-circuit", required=True)
    parser.add_argument("--stimulus-mode", required=True)
    parser.add_argument("--manual-stimulus", default="")
    parser.add_argument("--masks", nargs="+", required=True)
    parser.add_argument("--bit-order", default=BIT_ORDER)
    for name in ("write0", "zero_read", "write1", "final_read"):
        parser.add_argument(f"--{name.replace('_', '-')}-start-ps", required=True)
        parser.add_argument(f"--{name.replace('_', '-')}-rise-ps", required=True)
        parser.add_argument(f"--{name.replace('_', '-')}-fall-ps", required=True)
        parser.add_argument(f"--{name.replace('_', '-')}-width-ps", required=True)
    parser.add_argument("--wl-amplitude-ua", required=True)
    parser.add_argument("--bl-amplitude-ua", required=True)
    parser.add_argument("--se-amplitude-ua", required=True)
    parser.add_argument("--terminal-ohm", required=True)
    parser.add_argument("--jsl-area", required=True)
    parser.add_argument("--replay-source-signal", required=True)
    parser.add_argument("--josim-bin", required=True)
    parser.add_argument("--dt", required=True)
    parser.add_argument("--stop-time", required=True)
    parser.add_argument("--only")
    parser.add_argument("--case")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-analysis", action="store_true")
    parser.add_argument("--no-plots", action="store_true")
    return parser


def main() -> int:
    args = make_parser().parse_args()
    if args.dry_run:
        dry_run(args)
        return 0
    if args.only or args.case:
        raise RuntimeError("this registered baseline requires the default 15-case matrix; --only/--case are dry-run inspection options only")
    run_all(args)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
