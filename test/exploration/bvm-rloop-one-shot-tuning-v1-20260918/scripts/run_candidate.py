#!/usr/bin/env python3
"""Manual single-candidate runner for the BVM R-loop tuning platform."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

SERIES = Path(__file__).resolve().parents[1]
REPO = next(path for path in (SERIES, *SERIES.parents) if (path / ".git").exists())
CONFIG = SERIES / "config" / "current_candidate.env"
JJ_SOURCE = REPO / "circuits" / "models" / "jjmit.cir"
CANONICAL_BVM = REPO / "test" / "exploration" / "bvm-qb-l1-l3-bj2-targeted-closure-v1-20260914" / "inputs" / "bvm_jm2_connected.cir"
QB_SOURCE = REPO / "circuits" / "qb" / "bq_parameterized_v1.cir"
JTL_SOURCE = REPO / "test" / "exploration" / "bvm-qb-l1-l3-bj2-targeted-closure-v1-20260914" / "inputs" / "jtl2.cir"
TUNABLE_TEMPLATE = SERIES / "circuits" / "bvm_tunable.cir"
MASK_ORDER = ("0000", "0001", "0011", "0111", "1111")
BIT_ORDER = "b3b2b1b0=BVM1/BVM2/BVM3/BVM4"
CONTRACT = "This experiment is governed by docs/EXPERIMENT_CONTRACT.md."
FINAL_MARKER = "EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW"
STAGE_A = {
    "A000_CANONICAL": ("OPEN", "OPEN"),
    "A001": ("20", "20"),
    "A002": ("12", "12"),
    "A003": ("8", "8"),
}


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


def load_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in stripped:
            raise RuntimeError(f"invalid config line {path}:{number}")
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip()
    return values


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


def file_record(role: str, path: Path) -> dict[str, Any]:
    return {"role": role, "path": repo_rel(path), "sha256": sha256(path), "bytes": path.stat().st_size}


def parse_masks(value: str) -> list[str]:
    masks = [item.strip() for item in value.split(",") if item.strip()]
    if not masks:
        raise RuntimeError("MASKS must contain at least one binary mask")
    for mask in masks:
        if not re.fullmatch(r"[01]{4}", mask):
            raise RuntimeError(f"invalid mask {mask!r}; expected four bits")
    if len(set(masks)) != len(masks):
        raise RuntimeError("MASKS contains a duplicate")
    return masks


def normalize_shunt(value: str) -> str:
    value = value.strip()
    if value.upper() == "OPEN":
        return "OPEN"
    if not re.fullmatch(r"(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?", value):
        raise RuntimeError(f"invalid shunt value {value!r}; use OPEN or resistance in ohms")
    return value


def required_config(values: dict[str, str], key: str) -> str:
    if key not in values or not values[key]:
        raise RuntimeError(f"missing {key} in {CONFIG}")
    return values[key]


def effective_config(raw: dict[str, str], args: argparse.Namespace) -> dict[str, Any]:
    case_id = args.case_id or required_config(raw, "CASE_ID")
    mode = (args.mode or required_config(raw, "MODE")).lower()
    if mode not in {"passive", "closed"}:
        raise RuntimeError(f"MODE must be passive or closed, got {mode!r}")
    masks = parse_masks(args.masks if args.masks is not None else required_config(raw, "MASKS"))
    params = {
        "CASE_ID": case_id,
        "MODE": mode,
        "MASKS": masks,
        "JS1_AREA": required_config(raw, "JS1_AREA"),
        "JS2_AREA": required_config(raw, "JS2_AREA"),
        "RSH_JS1": normalize_shunt(required_config(raw, "RSH_JS1")),
        "RSH_JS2": normalize_shunt(required_config(raw, "RSH_JS2")),
        "LS1": required_config(raw, "LS1"),
        "LS2": required_config(raw, "LS2"),
        "LS3": required_config(raw, "LS3"),
        "RS": required_config(raw, "RS"),
        "LPSL": required_config(raw, "LPSL"),
        "RSL": required_config(raw, "RSL"),
        "LSL": required_config(raw, "LSL"),
        "DT": required_config(raw, "DT"),
        "STOP": required_config(raw, "STOP"),
    }
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", case_id):
        raise RuntimeError(f"invalid CASE_ID {case_id!r}")
    return params


def validate_stage_a(params: dict[str, Any]) -> None:
    case_id = params["CASE_ID"]
    if case_id not in STAGE_A:
        return
    expected = STAGE_A[case_id]
    actual = (params["RSH_JS1"], params["RSH_JS2"])
    if params["MODE"] != "passive" or tuple(params["MASKS"]) != MASK_ORDER or actual != expected:
        raise RuntimeError(
            f"registered Stage-A case {case_id} requires PASSIVE, masks {','.join(MASK_ORDER)}, "
            f"and shunts {expected[0]}/{expected[1]}; got {params['MODE']}, {params['MASKS']}, {actual}"
        )


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
        time_token = "0" if time_ps == 0 else f"{time_ps:g}p"
        current_token = "0" if current_ua == 0 else f"{current_ua:+g}u"
        values.extend((time_token, current_token))
    return f"I_{name} 0 {node} pwl(" + " ".join(values) + ")"


def stimulus(mask: str) -> str:
    lines = [
        f"* GENERATED one-shot tuning stimulus; mask={mask}; {BIT_ORDER}",
        "* IDLE 0-50; WRITE0 50-61; zero-state read control 70-81; WRITE1 90-101; SETTLE 101-110; final READ 110-121; RECOVERY 121-130; TAIL 150-200.",
    ]
    for index in range(1, 5):
        for name in ("WL", "BL", "SE"):
            lines.append(pwl(f"{name}{index}", f"{name}{index}", source_points(mask, index, name)))
    return "\n".join(lines) + "\n"


def probe_lines(mode: str, params: dict[str, Any]) -> list[str]:
    lines = [
        ".print " + " ".join(f"I(I_{name}{index})" for index in range(1, 5) for name in ("WL", "BL", "SE")),
    ]
    junctions = ("B_JM1", "B_JM2", "B_JS1", "B_JS2")
    branches = ("L_M1", "L_M2", "L_M3", "L_PM", "L_S1", "L_S2", "L_S3", "R_S", "L_PSL", "R_SL", "L_SL", "R_JM1", "R_SE", "L_PSE")
    for index in range(1, 5):
        for element in junctions:
            lines.append(f".print P({element}|XBVM{index}) V({element}|XBVM{index}) I({element}|XBVM{index})")
        for element in branches:
            lines.append(f".print I({element}|XBVM{index}) V({element}|XBVM{index})")
        if params["RSH_JS1"] != "OPEN":
            lines.append(f".print I(R_JS1_SHUNT|XBVM{index}) V(R_JS1_SHUNT|XBVM{index})")
        if params["RSH_JS2"] != "OPEN":
            lines.append(f".print I(R_JS2_SHUNT|XBVM{index}) V(R_JS2_SHUNT|XBVM{index})")
    lines.append(".print V(COMMON_SL)")
    for index in range(1, 9):
        lines.append(f".print P(B_JSL{index}) V(B_JSL{index}) I(B_JSL{index})")
    if mode == "closed":
        lines.append(".print V(QBIN) V(QBOUT)")
        lines.append(".print I(LIN|XBQ1) V(LIN|XBQ1) I(L1|XBQ1) V(L1|XBQ1) I(L2|XBQ1) V(L2|XBQ1) I(L3|XBQ1) V(L3|XBQ1)")
        lines.append(".print I(RJ1|XBQ1) V(RJ1|XBQ1) I(RJ2|XBQ1) V(RJ2|XBQ1) I(IB|XBQ1) V(IB|XBQ1)")
        for junction in ("BJS", "BJ1", "BJ2"):
            lines.append(f".print P({junction}|XBQ1) V({junction}|XBQ1) I({junction}|XBQ1)")
        for stage in range(1, 7):
            lines.append(f".print P(B01|XJTL1_{stage}) V(B01|XJTL1_{stage}) I(B01|XJTL1_{stage}) P(B02|XJTL1_{stage}) V(B02|XJTL1_{stage}) I(B02|XJTL1_{stage})")
            lines.append(f".print V(JTL{stage}_OUT)")
        lines.append(".print I(R_TERM) V(R_TERM)")
    return lines


def render_bvm(params: dict[str, Any]) -> str:
    text = TUNABLE_TEMPLATE.read_text(encoding="utf-8")
    rjm1 = str(params.get("RJM1", "8"))
    rjm2 = str(params.get("RJM2", "OPEN"))
    replacements = {
        "{{JM1_AREA}}": str(params.get("JM1_AREA", "1.2")),
        "{{JM2_AREA}}": str(params.get("JM2_AREA", "1.4")),
        "{{RJM1_LINE}}": "* RJM1 OPEN" if rjm1.upper() == "OPEN" else f"R_JM1 2 7 {rjm1}",
        "{{RJM2_LINE}}": "* RJM2 OPEN" if rjm2.upper() == "OPEN" else f"R_JM2 3 4 {rjm2}",
        "{{LM1}}": str(params.get("LM1", "12.5p")),
        "{{LM2}}": str(params.get("LM2", "24.5p")),
        "{{LM3}}": str(params.get("LM3", "8.5p")),
        "{{LPM}}": str(params.get("LPM", "0.5p")),
        "{{RBL}}": str(params.get("RBL", "20.0")),
        "{{LPBL}}": str(params.get("LPBL", "0.5p")),
        "{{RWL}}": str(params.get("RWL", "20.0")),
        "{{LPWL}}": str(params.get("LPWL", "0.5p")),
        "{{RSE}}": str(params.get("RSE", "20.0")),
        "{{LPSE}}": str(params.get("LPSE", "0.5p")),
        "{{JS1_AREA}}": params["JS1_AREA"],
        "{{JS2_AREA}}": params["JS2_AREA"],
        "{{LS1}}": params["LS1"],
        "{{LS2}}": params["LS2"],
        "{{LS3}}": params["LS3"],
        "{{RS}}": params["RS"],
        "{{LPSL}}": params["LPSL"],
        "{{RSL}}": params["RSL"],
        "{{LSL}}": params["LSL"],
        "{{R_JS1_SHUNT}}": "* R_JS1_SHUNT OPEN" if params["RSH_JS1"] == "OPEN" else f"R_JS1_SHUNT 5 6 {params['RSH_JS1']}",
        "{{R_JS2_SHUNT}}": "* R_JS2_SHUNT OPEN" if params["RSH_JS2"] == "OPEN" else f"R_JS2_SHUNT 9 10 {params['RSH_JS2']}",
    }
    for marker, value in replacements.items():
        text = text.replace(marker, value)
    if "{{" in text:
        raise RuntimeError("unresolved marker in rendered BVM")
    return text


def include_line(source: Path, case_dir: Path, label: str) -> str:
    return f".include {Path(os.path.relpath(source, case_dir)).as_posix()}" if source else f"* {label}: absent"


def render_deck(mode: str, params: dict[str, Any], sources: dict[str, Path], stimulus_path: Path, case_dir: Path) -> str:
    template_path = SERIES / "circuits" / ("passive_top.cir" if mode == "passive" else "closed_top.cir")
    text = template_path.read_text(encoding="utf-8")
    replacements = {
        "{{JJ_INCLUDE}}": include_line(sources["JJ_MODEL"], case_dir, "JJ_MODEL"),
        "{{BVM_INCLUDE}}": include_line(sources["BVM"], case_dir, "BVM"),
        "{{QB_INCLUDE}}": include_line(sources["QB"], case_dir, "QB") if mode == "closed" else "* QB: intentionally absent in PASSIVE",
        "{{JTL_INCLUDE}}": include_line(sources["JTL"], case_dir, "JTL") if mode == "closed" else "* JTL: intentionally absent in PASSIVE",
        "{{STIMULUS_INCLUDE}}": include_line(stimulus_path, case_dir, "STIMULUS"),
        "{{PROBES}}": "\n".join(probe_lines(mode, params)),
        "{{DT}}": params["DT"],
        "{{STOP_TIME}}": params["STOP"],
    }
    for marker, value in replacements.items():
        text = text.replace(marker, value)
    if "{{" in text:
        raise RuntimeError(f"unresolved top-deck marker in {mode}")
    if mode == "passive" and any(token in text for token in ("XBQ1", "XJTL1_", "R_TERM")):
        raise RuntimeError("PASSIVE deck contains QB/JTL/terminal")
    if mode == "closed" and any(token not in text for token in ("XBQ1 QBIN QBOUT BQ", "XJTL1_6 JTL5_OUT JTL6_OUT jtl", "R_TERM JTL6_OUT 0 10")):
        raise RuntimeError("CLOSED deck is missing the registered downstream path")
    return text


def read_header(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8", newline="") as stream:
        return next(csv.reader(stream))


def requested_signals(mode: str, params: dict[str, Any]) -> list[tuple[str, str, str]]:
    requested: list[tuple[str, str, str]] = []
    for index in range(1, 5):
        for name in ("WL", "BL", "SE"):
            requested.append((f"I(I_{name}{index})", "stimulus", "current"))
        for junction in ("B_JM1", "B_JM2", "B_JS1", "B_JS2"):
            for quantity, unit in (("P", "rad"), ("V", "V"), ("I", "A")):
                requested.append((f"{quantity}({junction}|XBVM{index})", "BVM", "phase" if quantity == "P" else "voltage" if quantity == "V" else "current"))
        for branch in ("L_M1", "L_M2", "L_M3", "L_PM", "L_S1", "L_S2", "L_S3", "R_S", "L_PSL", "R_SL", "L_SL", "R_JM1", "R_SE", "L_PSE"):
            for quantity, unit in (("I", "A"), ("V", "V")):
                requested.append((f"{quantity}({branch}|XBVM{index})", "BVM", "current" if quantity == "I" else "voltage"))
        if params["RSH_JS1"] != "OPEN":
            requested.extend(((f"I(R_JS1_SHUNT|XBVM{index})", "BVM", "current"), (f"V(R_JS1_SHUNT|XBVM{index})", "BVM", "voltage")))
        if params["RSH_JS2"] != "OPEN":
            requested.extend(((f"I(R_JS2_SHUNT|XBVM{index})", "BVM", "current"), (f"V(R_JS2_SHUNT|XBVM{index})", "BVM", "voltage")))
    requested.append(("V(COMMON_SL)", "shared_SL", "voltage"))
    for index in range(1, 9):
        for quantity, unit in (("P", "rad"), ("V", "V"), ("I", "A")):
            requested.append((f"{quantity}(B_JSL{index})", "JSL", "phase" if quantity == "P" else "voltage" if quantity == "V" else "current"))
    if mode == "closed":
        for signal, subsystem, quantity in (("V(QBIN)", "QB", "voltage"), ("V(QBOUT)", "QB", "voltage"), ("I(LIN|XBQ1)", "QB", "current"), ("V(LIN|XBQ1)", "QB", "voltage"), ("I(L1|XBQ1)", "QB", "current"), ("V(L1|XBQ1)", "QB", "voltage"), ("I(L2|XBQ1)", "QB", "current"), ("V(L2|XBQ1)", "QB", "voltage"), ("I(L3|XBQ1)", "QB", "current"), ("V(L3|XBQ1)", "QB", "voltage"), ("I(RJ1|XBQ1)", "QB", "current"), ("V(RJ1|XBQ1)", "QB", "voltage"), ("I(RJ2|XBQ1)", "QB", "current"), ("V(RJ2|XBQ1)", "QB", "voltage"), ("I(IB|XBQ1)", "QB", "current"), ("V(IB|XBQ1)", "QB", "voltage"), ("I(R_TERM)", "terminal", "current"), ("V(R_TERM)", "terminal", "voltage")):
            requested.append((signal, subsystem, quantity))
        for junction in ("BJS", "BJ1", "BJ2"):
            for quantity, unit in (("P", "rad"), ("V", "V"), ("I", "A")):
                requested.append((f"{quantity}({junction}|XBQ1)", "QB", "phase" if quantity == "P" else "voltage" if quantity == "V" else "current"))
        for stage in range(1, 7):
            for junction in ("B01", "B02"):
                for quantity, unit in (("P", "rad"), ("V", "V"), ("I", "A")):
                    requested.append((f"{quantity}({junction}|XJTL1_{stage})", "JTL", "phase" if quantity == "P" else "voltage" if quantity == "V" else "current"))
            requested.append((f"V(JTL{stage}_OUT)", "JTL", "voltage"))
    return requested


def write_signal_manifest(case_dir: Path, mode: str, params: dict[str, Any], headers: list[str]) -> dict[str, Any]:
    present = set(headers)
    rows = []
    for signal, subsystem, quantity in requested_signals(mode, params):
        if signal in present:
            status, reason, plotted = "PRESENT", "", "yes"
        else:
            status, plotted = "KNOWN_UNSUPPORTED_OR_NOT_EMITTED", "no"
            reason = "JoSIM did not emit the requested raw column for this branch or source in this deck; raw data retained without silent substitution."
        rows.append({"raw_column_index": headers.index(signal) + 1 if signal in present else None, "exact_raw_column_name": signal, "subsystem": subsystem, "physical_quantity": quantity, "status": status, "plotted": plotted, "reason": reason})
    manifest = case_dir / "signal_manifest.csv"
    with manifest.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=("raw_column_index", "exact_raw_column_name", "subsystem", "physical_quantity", "status", "plotted", "reason"))
        writer.writeheader()
        writer.writerows(rows)
    return {"path": repo_rel(manifest), "sha256": sha256(manifest), "requested": len(rows), "present": sum(row["status"] == "PRESENT" for row in rows), "unsupported_or_not_emitted": sum(row["status"] != "PRESENT" for row in rows)}


def snapshot_sources(case_root: Path, params: dict[str, Any]) -> dict[str, Path]:
    source_dir = case_root / "snapshot" / "sources"
    source_dir.mkdir(parents=True, exist_ok=False)
    sources: dict[str, Path] = {}
    for role, source in (("JJ_MODEL", JJ_SOURCE), ("QB", QB_SOURCE), ("JTL", JTL_SOURCE)):
        target = source_dir / source.name
        shutil.copy2(source, target)
        sources[role] = target
    bvm_target = source_dir / "bvm_tunable.cir"
    bvm_target.write_text(render_bvm(params), encoding="utf-8")
    sources["BVM"] = bvm_target
    return sources


def source_manifest(case_root: Path, sources: dict[str, Path], params: dict[str, Any], parent: dict[str, Any]) -> dict[str, Any]:
    records = [file_record(role, path) for role, path in sources.items()]
    records.extend(file_record(role, SERIES / "circuits" / filename) for role, filename in (("TOP_PASSIVE", "passive_top.cir"), ("TOP_CLOSED", "closed_top.cir")))
    records.append(file_record("CONFIG", CONFIG))
    records.append(file_record("TUNABLE_TEMPLATE", TUNABLE_TEMPLATE))
    return {"schema": "bvm-rloop-one-shot-source-manifest-v1", "created_at": now(), "parent": parent, "contract_sentence": CONTRACT, "case_parameters": params, "sources": records, "canonical_bvm_source": file_record("CANONICAL_BVM_REFERENCE", CANONICAL_BVM), "raw_not_copied_from_history": True}


def solve_one(case_dir: Path, mode: str, mask: str, params: dict[str, Any], sources: dict[str, Path]) -> dict[str, Any]:
    run_id = f"{mode.upper()}_N{mask.count('1')}_{mask}"
    solve_dir = case_dir / "cases" / run_id
    solve_dir.mkdir(parents=True, exist_ok=False)
    stimulus_path = solve_dir / "stimulus.inc"
    stimulus_path.write_text(stimulus(mask), encoding="utf-8")
    deck_text = render_deck(mode, params, sources, stimulus_path, solve_dir)
    deck_path = solve_dir / "actual_deck.cir"
    deck_path.write_text(deck_text, encoding="utf-8")
    compatibility = solve_dir / "deck.cir"
    compatibility.write_text(deck_text, encoding="utf-8")
    raw_path = solve_dir / "raw.csv"
    command = [str(REPO / "build" / "josim-cli"), "-a", "1", "-o", str(raw_path), str(deck_path)]
    started = now()
    clock = time.monotonic()
    completed = subprocess.run(command, cwd=solve_dir, capture_output=True, text=True, check=False)
    runtime = time.monotonic() - clock
    finished = now()
    (solve_dir / "stdout.txt").write_text(completed.stdout, encoding="utf-8")
    (solve_dir / "stderr.txt").write_text(completed.stderr, encoding="utf-8")
    (solve_dir / "run.log").write_text("\n".join((f"experiment={SERIES.name}", f"run_id={run_id}", f"mode={mode}", f"mask={mask}", f"started_at={started}", f"finished_at={finished}", f"runtime_seconds={runtime:.6f}", f"command={shlex.join(command)}", f"exit_code={completed.returncode}", "")), encoding="utf-8")
    if completed.returncode != 0 or not raw_path.is_file() or raw_path.stat().st_size == 0:
        metadata = {"run_id": run_id, "mode": mode, "mask": mask, "execution_status": "SOLVER_FAIL", "command": command, "started_at": started, "finished_at": finished, "runtime_seconds": runtime, "raw": {"exists": raw_path.is_file(), "path": repo_rel(raw_path) if raw_path.exists() else None}, "stderr_tail": completed.stderr[-4000:]}
        write_json(solve_dir / "metadata.json", metadata)
        raise RuntimeError(f"JoSIM failed for {run_id}; preserved {solve_dir}")
    headers = read_header(raw_path)
    manifest = write_signal_manifest(solve_dir, mode, params, headers)
    metadata = {"run_id": run_id, "mode": mode, "mask": mask, "bit_order": BIT_ORDER, "parameters": params, "command": command, "started_at": started, "finished_at": finished, "runtime_seconds": runtime, "execution_status": "RUN_PASS", "solver": {"path": repo_rel(REPO / "build" / "josim-cli"), "sha256": sha256(REPO / "build" / "josim-cli"), "version": subprocess.check_output([str(REPO / "build" / "josim-cli"), "--version"], text=True).strip()}, "deck": {"path": repo_rel(deck_path), "sha256": sha256(deck_path), "bytes": deck_path.stat().st_size}, "stimulus": {"path": repo_rel(stimulus_path), "sha256": sha256(stimulus_path), "bytes": stimulus_path.stat().st_size}, "raw": {"path": repo_rel(raw_path), "sha256": sha256(raw_path), "bytes": raw_path.stat().st_size, "headers": len(headers)}, "signal_manifest": manifest, "stdout": {"path": repo_rel(solve_dir / "stdout.txt"), "sha256": sha256(solve_dir / "stdout.txt")}, "stderr": {"path": repo_rel(solve_dir / "stderr.txt"), "sha256": sha256(solve_dir / "stderr.txt")}, "run_log": {"path": repo_rel(solve_dir / "run.log"), "sha256": sha256(solve_dir / "run.log")}}
    write_json(solve_dir / "metadata.json", metadata)
    metadata["metadata"] = {"path": repo_rel(solve_dir / "metadata.json"), "sha256": sha256(solve_dir / "metadata.json")}
    return metadata


def update_root(case_root: Path, params: dict[str, Any], parent: dict[str, Any], source_info: dict[str, Any], records: list[dict[str, Any]]) -> None:
    provenance = read_json(SERIES / "provenance.json") if (SERIES / "provenance.json").is_file() else {"schema": "bvm-rloop-one-shot-tuning-v1-provenance-v1", "experiment_id": SERIES.name, "runs": {}, "run_order": []}
    case_id = params["CASE_ID"]
    provenance.setdefault("cases", {})[case_id] = {"path": repo_rel(case_root), "parameters": params, "parent": parent, "source_manifest": source_info, "runs": records}
    provenance["runs"].update({record["run_id"]: record for record in records})
    provenance["run_order"] = [run_id for case in provenance["cases"].values() for run_id in [record["run_id"] for record in case.get("runs", [])]]
    provenance["actual_physical_solve_count"] = len(provenance["run_order"])
    provenance["authorized_solve_count"] = 20
    provenance["scientific_interpretation_performed"] = False
    provenance["automatic_follow_up"] = False
    provenance["status"] = "ALL_REGISTERED_STAGE_A_SOLVES_COMPLETE" if len(provenance["run_order"]) == 20 else "CASE_SOLVES_COMPLETE"
    write_json(SERIES / "provenance.json", provenance)
    result = read_json(SERIES / "result.json") if (SERIES / "result.json").is_file() else {"schema": "bvm-rloop-one-shot-tuning-v1-result-v1", "experiment_id": SERIES.name}
    result.update({"status": "ALL_REGISTERED_STAGE_A_SOLVES_COMPLETE_ANALYSIS_PENDING" if len(provenance["run_order"]) == 20 else "CASE_SOLVES_COMPLETE_ANALYSIS_PENDING", "artifact_status": "PENDING", "authorized_solve_count": 20, "actual_physical_solve_count": len(provenance["run_order"]), "case_order": list(provenance["cases"].keys()), "scientific_interpretation_performed": False, "automatic_follow_up": False, "stop": {"final_marker": None}})
    write_json(SERIES / "result.json", result)


def dry_run(params: dict[str, Any]) -> None:
    print(f"EXPERIMENT: {SERIES.name}")
    print(f"PARENT_HEAD: {git_head()}")
    print(f"REMOTE_HEAD: {remote_head()}")
    print(f"CASE_ID: {params['CASE_ID']}")
    print(f"MODE: {params['MODE']}")
    print(f"MASKS: {','.join(params['MASKS'])}")
    print(f"SHUNTS: JS1={params['RSH_JS1']} ohm; JS2={params['RSH_JS2']} ohm")
    print(f"TRAN: dt={params['DT']} stop={params['STOP']}")
    for mask in params["MASKS"]:
        run_id = f"{params['MODE'].upper()}_N{mask.count('1')}_{mask}"
        print(f"  {run_id}: runs/{params['CASE_ID']}/cases/{run_id}/raw.csv")
    print("DRY_RUN: no case directory created; JoSIM not invoked")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one non-overwriting BVM R-loop candidate")
    parser.add_argument("--config", default=str(CONFIG))
    parser.add_argument("--case", dest="case_id")
    parser.add_argument("--mode", choices=("passive", "closed"))
    parser.add_argument("--masks", help="comma-separated masks, e.g. 0001,0011,0111")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    config_path = Path(args.config).resolve()
    raw_config = load_env(config_path)
    params = effective_config(raw_config, args)
    validate_stage_a(params)
    if not args.dry_run and remote_head() not in {None, git_head()}:
        raise RuntimeError(f"parent HEAD differs from bvm/master: {git_head()} vs {remote_head()}")
    if args.dry_run:
        dry_run(params)
        return 0
    case_root = SERIES / "runs" / params["CASE_ID"]
    if case_root.exists():
        raise RuntimeError(f"STOP: CASE_ID already exists and will not be overwritten: {case_root}")
    parent = git_snapshot()
    case_root.mkdir(parents=True, exist_ok=False)
    (case_root / "config_snapshot.env").write_text(config_path.read_text(encoding="utf-8"), encoding="utf-8")
    sources = snapshot_sources(case_root, params)
    source_info = source_manifest(case_root, sources, params, parent)
    write_json(case_root / "source_manifest.json", source_info)
    records = []
    for mask in params["MASKS"]:
        records.append(solve_one(case_root, params["MODE"], mask, params, sources))
    case_manifest = {"schema": "bvm-rloop-one-shot-case-v1", "case_id": params["CASE_ID"], "parameters": params, "parent": parent, "source_manifest": {"path": repo_rel(case_root / "source_manifest.json"), "sha256": sha256(case_root / "source_manifest.json")}, "run_order": [record["run_id"] for record in records], "physical_solve_count": len(records), "automatic_follow_up": False, "scientific_interpretation_performed": False}
    write_json(case_root / "case_manifest.json", case_manifest)
    update_root(case_root, params, parent, source_info, records)
    print(json.dumps({"status": "CASE_SOLVES_COMPLETE", "case_id": params["CASE_ID"], "mode": params["MODE"], "masks": params["MASKS"], "physical_solve_count": len(records), "case_path": repo_rel(case_root)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
