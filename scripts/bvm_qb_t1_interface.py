#!/usr/bin/env python3
"""Registered BVM -> canonical QB -> T1 topology experiment runner.

The experiment-local layout is intentionally small.  This program never
rewrites a raw CSV, never retries a failed solve, and only performs registered
mechanical arithmetic before a separately authorized scientific review.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


REPO = Path(__file__).resolve().parents[1]
EXP_ID = os.environ.get("BVM_QB_T1_EXPERIMENT_ID", "bvm-qb-t1-interface-topology-v1-20260914")
EXP = REPO / "test/exploration" / EXP_ID
QB = REPO / "circuits/qb/bq_parameterized_v1.cir"
MODEL = REPO / "circuits/models/jjmit.cir"
T1 = REPO / "circuits/t1/t1_cell.cir"
BVM = REPO / "test/exploration/bvm-qb-l1-l3-bj2-targeted-closure-v1-20260914/inputs/bvm_jm2_connected.cir"
JTL = REPO / "test/exploration/bvm-qb-l1-l3-bj2-targeted-closure-v1-20260914/inputs/jtl2.cir"
SOLVER = REPO / "build/josim-cli"
PLOTTER = REPO / "scripts/josim-plot2.py"
TOPOLOGIES = ("jtl6", "jtl2", "direct")
MASKS = ("0000", "0001", "0011", "0111", "1111")
STAGE_A = MASKS
WINDOWS = ((70, 81), (90, 101), (101, 110), (110, 121), (121, 126), (126, 150), (150, 200))
QUIET_WINDOWS = ((10, 50), (150, 200))
V_ACTIVITY = 2.0e-4
PHASE_ACTIVITY_TURNS = 1.0
MIN_ACTIVITY_SAMPLES = 3
LINK_DIFF_V = 1.0e-9
PHI0 = 2.067833848e-15
CANONICAL_QB_SHA256 = "f676ba1ecb9b2607631a5cfc2f99b7d67e09b9e821457015fba375b8a39f13b0"
CONTRACT_SENTENCE = "This experiment is governed by docs/EXPERIMENT_CONTRACT.md."
PACKAGE = REPO / f"{EXP.name}_raw_evidence.zip"
PACKAGE_QA = EXP / "PACKAGE_QA.json"
MIRROR_RECEIPT = EXP / "MIRROR_RECEIPT.json"


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO.resolve()).as_posix()


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


def git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()


def remote_head() -> str | None:
    try:
        output = subprocess.check_output(
            ["git", "ls-remote", "bvm", "refs/heads/master"],
            cwd=REPO,
            text=True,
            timeout=30,
        ).strip()
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None
    return output.split()[0] if output else None


def solver_context() -> dict[str, Any]:
    if not SOLVER.is_file():
        raise RuntimeError(f"missing registered solver: {SOLVER}")
    return {
        "path": rel(SOLVER),
        "sha256": sha256(SOLVER),
        "version": subprocess.check_output([str(SOLVER), "--version"], cwd=REPO, text=True).strip(),
    }


def source_entries() -> list[dict[str, Any]]:
    sources = [
        ("canonical_qb", QB, "frozen canonical QB include; exact user-registered text"),
        ("global_jjmit_model", MODEL, "global model closure for BVM/JSL/T1; same values as the QB-local model"),
        ("t1_cell", T1, "current T1 cell; no modification"),
        ("bvm_jm2_connected", BVM, "current JM2-connected BVM source used by the latest 4x1 closure"),
        ("jtl2_source", JTL, "current JTL source used for the six- and two-stage chains"),
        ("josim_solver", SOLVER, "recorded solver binary"),
        ("plotter", PLOTTER, "standard descriptive visualization renderer"),
    ]
    result: list[dict[str, Any]] = []
    for name, path, role in sources:
        if not path.is_file():
            raise RuntimeError(f"missing source: {path}")
        result.append({"name": name, "path": rel(path), "sha256": sha256(path), "bytes": path.stat().st_size, "role": role})
    return result


def assert_current_sources() -> None:
    if not QB.is_file() or sha256(QB) != CANONICAL_QB_SHA256:
        raise RuntimeError("canonical QB is missing or its exact registered text changed")
    if not MODEL.is_file():
        raise RuntimeError("global jjmit model closure is missing")
    t1_text = T1.read_text(encoding="utf-8")
    if not re.search(r"^B_J7\s+N13\s+N17\s+jjmit\s+area=1\.0\s*$", t1_text, flags=re.MULTILINE) or not re.search(r"^R_J7\s+N13\s+N17\s+10\s*$", t1_text, flags=re.MULTILINE):
        raise RuntimeError("current T1 J7 definition does not match the registered source")
    if re.search(r"^R_J7\s+N18\s+N17\b", t1_text, flags=re.MULTILINE):
        raise RuntimeError("old T1 R_J7 N18 N17 definition is present")
    solver_context()


def run_id(topology: str, mask: str) -> str:
    return f"{topology}_{mask}"


def run_dir(topology: str, mask: str) -> Path:
    return EXP / "runs" / topology / mask


def raw_path(topology: str, mask: str) -> Path:
    return run_dir(topology, mask) / "raw.csv"


def include_path(path: Path, destination: Path) -> str:
    return Path(os.path.relpath(path, destination)).as_posix()


def pwl(points: Iterable[tuple[float, float]]) -> str:
    tokens: list[str] = []
    for time_ps, current_uA in points:
        value = f"{current_uA:+g}u" if current_uA else "0"
        tokens.extend((f"{time_ps:g}p", value))
    return "pwl(" + " ".join(tokens) + ")"


def bvm_sources(final_active: bool) -> tuple[list[tuple[float, float]], list[tuple[float, float]], list[tuple[float, float]]]:
    """Return the registered WL, BL and SE sources for one BVM."""
    wl = [
        (0, 0), (50, 0), (51, -100), (60, -100), (61, 0),
        (70, 0), (71, 100), (80, 100), (81, 0),
        (90, 0), (91, 100), (100, 100), (101, 0),
        (110, 0), (111, 100 if final_active else 0), (120, 100 if final_active else 0), (121, 0), (200, 0),
    ]
    bl = [
        (0, 0), (50, 0), (51, -100), (60, -100), (61, 0),
        (70, 0), (81, 0), (90, 0), (91, 100), (100, 100), (101, 0),
        (110, 0), (121, 0), (200, 0),
    ]
    se = [
        (0, 0), (70, 0), (81, 0), (90, 0), (101, 0), (110, 0),
        (111, 100 if final_active else 0), (120, 100 if final_active else 0), (121, 0), (200, 0),
    ]
    return wl, bl, se


def probes(topology: str) -> list[str]:
    lines: list[str] = []
    for index in range(1, 5):
        for element in ("B_JM1", "B_JM2", "B_JS1", "B_JS2"):
            lines.append(f".print P({element}|XBVM{index}) V({element}|XBVM{index}) I({element}|XBVM{index})")
        for element in ("L_M1", "L_M2", "L_M3", "L_PM", "L_PSL", "L_SL"):
            lines.append(f".print I({element}|XBVM{index})")
        lines.append(f".print I(I_WL{index}) I(I_BL{index}) I(I_SE{index})")
    lines.append(".print V(COMMON_SL)")
    for index in range(1, 9):
        lines.append(f".print P(B_JSL{index}) V(B_JSL{index}) I(B_JSL{index})")
    lines.append(".print V(QBIN)")
    for element in ("LIN", "L1", "L2", "L3"):
        lines.append(f".print I({element}|XBQ) V({element}|XBQ)")
    lines += [
        ".print P(BJS|XBQ) V(BJS|XBQ) I(BJS|XBQ)",
        ".print P(BJ1|XBQ) V(BJ1|XBQ) I(BJ1|XBQ)",
        ".print P(BJ2|XBQ) V(BJ2|XBQ) I(BJ2|XBQ)",
        ".print I(RJ1|XBQ) I(RJ2|XBQ)",
        ".print V(QBOUT)",
    ]
    if topology != "direct":
        count = 6 if topology == "jtl6" else 2
        for index in range(1, count + 1):
            lines.append(f".print P(B01|XJTL{index}) V(B01|XJTL{index}) I(B01|XJTL{index}) P(B02|XJTL{index}) V(B02|XJTL{index}) I(B02|XJTL{index})")
            lines.append(f".print V(JTL{index}_OUT)")
    lines.append(".print V(T1_I) V(CLK) V(S) V(C) I(R_S) I(R_C)")
    for index in range(1, 12):
        lines.append(f".print P(B_J{index}|XT1) V(B_J{index}|XT1) I(B_J{index}|XT1)")
    for element in ("L1", "L3", "L7", "L8", "L9", "L10", "L15", "L16", "L17", "L11", "L13"):
        lines.append(f".print I({element}|XT1)")
    return lines


def deck_text(topology: str, mask: str, destination: Path) -> str:
    active = [bit == "1" for bit in mask]
    lines = [
        f"* REGISTERED BVM -> QB -> T1 INTEGRATION DECK; topology={topology}; mask={mask}",
        "* No replay, passive capture, source scaling/filtering, parameter override, or T1 modification.",
        "* P(...) is raw phase in radians; -j 2pi is visualization-only display conversion.",
        f".include {include_path(MODEL, destination)}",
        f".include {include_path(QB, destination)}",
        f".include {include_path(BVM, destination)}",
    ]
    if topology != "direct":
        lines.append(f".include {include_path(JTL, destination)}")
    lines += [
        f".include {include_path(T1, destination)}",
        "",
        "* Four identical historical JM2-connected BVMs share the physical COMMON_SL node.",
        "XBVM1 WL1 BL1 SE1 COMMON_SL BVM",
        "XBVM2 WL2 BL2 SE2 COMMON_SL BVM",
        "XBVM3 WL3 BL3 SE3 COMMON_SL BVM",
        "XBVM4 WL4 BL4 SE4 COMMON_SL BVM",
        "",
        "B_JSL1 COMMON_SL JSL_NODE1 jjmit area=5.0",
        "B_JSL2 JSL_NODE1 JSL_NODE2 jjmit area=5.0",
        "B_JSL3 JSL_NODE2 JSL_NODE3 jjmit area=5.0",
        "B_JSL4 JSL_NODE3 JSL_NODE4 jjmit area=5.0",
        "B_JSL5 JSL_NODE4 JSL_NODE5 jjmit area=5.0",
        "B_JSL6 JSL_NODE5 JSL_NODE6 jjmit area=5.0",
        "B_JSL7 JSL_NODE6 JSL_NODE7 jjmit area=5.0",
        "B_JSL8 JSL_NODE7 QBIN jjmit area=5.0",
        "",
        "XBQ QBIN QBOUT BQ",
    ]
    if topology == "jtl6":
        for index in range(1, 7):
            source = "QBOUT" if index == 1 else f"JTL{index - 1}_OUT"
            lines.append(f"XJTL{index} {source} JTL{index}_OUT jtl")
        final_node = "JTL6_OUT"
    elif topology == "jtl2":
        lines += ["XJTL1 QBOUT JTL1_OUT jtl", "XJTL2 JTL1_OUT JTL2_OUT jtl"]
        final_node = "JTL2_OUT"
    else:
        final_node = "QBOUT"
    lines += [
        "",
        f"* Ideal zero-drop link only exposes the named T1_I terminal: V_T1_LINK {final_node} T1_I 0",
        "V_T1_LINK %s T1_I 0" % final_node,
        "XT1 T1_I CLK S C N_BIAS1 N_BIAS2 N_BIAS3 T1",
        "V_BIAS1 N_BIAS1 0 DC 1.67m",
        "V_BIAS2 N_BIAS2 0 DC 1.67m",
        "I_BIAS3 N_BIAS3 0 DC 35u",
        "R_S S 0 12",
        "R_C C 0 12",
        "R_CLK_QUIET CLK 0 5",
        "",
    ]
    for index in range(1, 5):
        wl, bl, se = bvm_sources(active[index - 1])
        lines += [
            f"I_WL{index} 0 WL{index} {pwl(wl)}",
            f"I_BL{index} 0 BL{index} {pwl(bl)}",
            f"I_SE{index} 0 SE{index} {pwl(se)}",
        ]
    lines += ["", ".tran 0.1p 200p", ""]
    lines += probes(topology)
    lines += [".end", ""]
    return "\n".join(lines)


def expected_headers(topology: str) -> set[str]:
    required: set[str] = set()
    for index in range(1, 5):
        for element in ("B_JM1", "B_JM2", "B_JS1", "B_JS2"):
            required.update(f"{kind}({element}|XBVM{index})" for kind in ("P", "V", "I"))
        required.update(f"I({element}|XBVM{index})" for element in ("L_M1", "L_M2", "L_M3", "L_PM", "L_PSL", "L_SL"))
        required.update(f"I({element})" for element in (f"I_WL{index}", f"I_BL{index}", f"I_SE{index}"))
    required.add("V(COMMON_SL)")
    for index in range(1, 9):
        required.update(f"{kind}(B_JSL{index})" for kind in ("P", "V", "I"))
    required.update({"V(QBIN)", "V(QBOUT)", "I(RJ1|XBQ)", "I(RJ2|XBQ)"})
    required.update(f"{kind}({element}|XBQ)" for element in ("BJS", "BJ1", "BJ2") for kind in ("P", "V", "I"))
    required.update(f"{kind}({element}|XBQ)" for element in ("LIN", "L1", "L2", "L3") for kind in ("I", "V"))
    if topology != "direct":
        count = 6 if topology == "jtl6" else 2
        for index in range(1, count + 1):
            required.update(f"{kind}(B{element}|XJTL{index})" for element in ("01", "02") for kind in ("P", "V", "I"))
            required.add(f"V(JTL{index}_OUT)")
    required.update({"V(T1_I)", "V(CLK)", "V(S)", "V(C)", "I(R_S)", "I(R_C)"})
    required.update(f"{kind}(B_J{index}|XT1)" for index in range(1, 12) for kind in ("P", "V", "I"))
    required.update(f"I({element}|XT1)" for element in ("L1", "L3", "L7", "L8", "L9", "L10", "L15", "L16", "L17", "L11", "L13"))
    return required


def prepare() -> None:
    EXP.mkdir(parents=True, exist_ok=True)
    assert_current_sources()
    (EXP / "PREFLIGHT.md").write_text(
        "\n".join([
            "# BVM -> QB -> T1 interface topology v1 — PREFLIGHT",
            "",
            CONTRACT_SENTENCE,
            "",
            f"- Experiment: `{EXP.name}`",
            f"- Generated at: `{now()}`",
            f"- Registration HEAD: `{git_head()}`",
            f"- Remote `bvm/master` at registration: `{remote_head() or 'UNAVAILABLE'}`",
            "- Preflight status: `PASS`; solver has not been invoked at preflight.",
            f"- Solver: `{solver_context()['version']}`; SHA-256 `{sha256(SOLVER)}`",
            "",
            "## Frozen source closure",
            "",
            *[f"- `{item['name']}`: `{item['path']}`; SHA-256 `{item['sha256']}`; {item['role']}." for item in source_entries()],
            "",
            "The canonical QB file is byte-checked against the exact registered text. No deck defines QB parameters or copies the QB source. Existing BVM/JTL source files are referenced by repository-relative include paths; no old raw/reference artifact is copied.",
            "The current `circuits/t1/t1_cell.cir` is included without modification and has `B_J7 N13 N17` plus `R_J7 N13 N17 10`; the old `R_J7 N18 N17` definition is absent.",
            "",
            "## Exact run matrix and automatic gate",
            "",
            "- Stage A: `jtl6/{0000,0001,0011,0111,1111}`.",
            "- If the registered sanity screen flags `JTL6_T1_INTEGRATION_SANITY_FAILED`, stop and do not invoke `jtl2` or `direct`.",
            "- If sane: Stage B `jtl2/{0000,0001,0011,0111,1111}`; Stage C `direct/{0000,0001,0011,0111,1111}`.",
            "- Maximum and, if Stage A passes, exact physical solve count: 15. No retries, replay, parameter sweep, timing change, or follow-up solve.",
            "",
            "## Frozen topology, timing, and bias",
            "",
            "- `jtl6`: `4xBVM -> COMMON_SL -> JSL1..8 -> canonical QB -> JTL1..6 -> T1.I`.",
            "- `jtl2`: `4xBVM -> COMMON_SL -> JSL1..8 -> canonical QB -> JTL1..2 -> T1.I`.",
            "- `direct`: `4xBVM -> COMMON_SL -> JSL1..8 -> canonical QB -> T1.I`.",
            "- Full galvanic BVM/JSL↔QB loop is retained; no passive capture, source replacement/scaling/filtering, topology modification, or extra/matching resistor is added. The only zero-drop link is the named `T1_I` observation terminal.",
            "- History: `IDLE 0-50; WRITE0 50-61; IDLE 61-70; ZERO_STATE_READ_CONTROL 70-81; IDLE 81-90; WRITE1 90-101; SETTLE 101-110; FINAL READ 110-121; TAIL 121-200 ps`.",
            "- Amplitude `100uA`, 1 ps rise/fall, 9 ps plateau; `.tran 0.1p 200p`. Masks are exactly `0000`, `0001`, `0011`, `0111`, `1111` with bit order `b3b2b1b0 = BVM1/BVM2/BVM3/BVM4`.",
            "- T1: current unmodified cell; `V_BIAS1=1.67m`, `V_BIAS2=1.67m`, `I_BIAS3=35u`, `R_S=12`, `R_C=12`, `R_CLK_QUIET=5`; no clock source and CLK is not floating.",
            "",
            "## Probes and registered arithmetic",
            "",
            "- Every BVM: P/V/I for `B_JM1`, `B_JM2`, `B_JS1`, `B_JS2`; currents `L_M1`, `L_M2`, `L_M3`, `L_PM`, `L_PSL`, `L_SL`; drive-source currents are `I(I_WLn)`, `I(I_BLn)`, `I(I_SEn)`.",
            "- Shared/JSL: `V(COMMON_SL)`, P/V/I `B_JSL1..8`, `I(B_JSL8)`, `V(QBIN)`.",
            "- QB: I/V `LIN`, `L1`, `L2`, `L3`; P/V/I `BJS`, `BJ1`, `BJ2`; I `RJ1`, `RJ2`; `V(QBOUT)`.",
            "- All present JTL levels: P/V/I `B01/B02`, `V(JTLx_OUT)`; T1 all 11 junctions and the requested input/output/inductor probes.",
            "- Analysis windows use actual stored timestamps: `[70,81)`, `[90,101)`, `[101,110)`, `[110,121)`, `[121,126)`, `[126,150)`, `[150,200)` ps. Integrals are actual-grid trapezoids with no interpolation.",
            "- P(...) is raw radians. Displayed turns are explicitly `rad/(2*pi)` and are navigation only, never an SFQ count.",
            "",
            "## Mechanical sanity flags",
            "",
            f"- Voltage activity: at least `{MIN_ACTIVITY_SAMPLES}` actual samples with `abs(V) >= {V_ACTIVITY:g} V` in registered quiet/tail windows.",
            f"- Phase activity: `{PHASE_ACTIVITY_TURNS:g}` turn navigation threshold, activity only; T1 quiet/clock monitors and 0000 carry/J1 tail are checked.",
            f"- JTL6-to-T1.I link consistency: max `abs(V(JTL6_OUT)-V(T1_I)) <= {LINK_DIFF_V:g} V`.",
            "- These are stop flags only, not SFQ, switching, Gate, or physical correctness criteria.",
            "",
            "## Minimal layout override and stop",
            "",
            "The user-requested minimal layout omits `screening/`, `references/`, `qa/`, `handoff/`, `visualization/run_summaries/`, and `analysis/archive/`; root-level machine-readable evidence is retained. Each run contains only `deck.cir`, `raw.csv`, `run.log`, and `plots/`.",
            "After package QA and commit, stop at `EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW`; scientific interpretation, parameter modification, and follow-up solves are not authorized.",
            "",
        ]),
        encoding="utf-8",
    )
    write_json(EXP / "SOURCE_MANIFEST.json", {"schema": "bvm-qb-t1-interface-source-manifest-v1", "experiment_id": EXP.name, "created_at": now(), "registration_head": git_head(), "remote_bvm_master": remote_head(), "sources": source_entries(), "external_source_policy": "Existing repository-relative BVM/JTL inputs are referenced; old raw/reference artifacts are not copied."})
    write_json(EXP / "provenance.json", {"schema": "bvm-qb-t1-interface-provenance-v1", "experiment_id": EXP.name, "created_at": now(), "registration_head": git_head(), "remote_bvm_master": remote_head(), "solver": solver_context(), "sources": source_entries(), "canonical_qb_exact_text_sha256": sha256(QB), "t1_j7_verification": {"required": "B_J7 N13 N17 jjmit area=1.0; R_J7 N13 N17 10", "old_definition_absent": True}, "contract": {"sentence": CONTRACT_SENTENCE, "minimal_layout_override": True, "scientific_analysis_performed": False}, "transformations": [{"name": "phase_unwrap_for_navigation", "scope": "analysis only", "raw_mutated": False, "algorithm": "sequential +/-pi correction by adding/subtracting 2*pi"}, {"name": "phase_turn_display", "scope": "josim-plot2 display only", "formula": "raw_phase_rad/(2*pi)", "raw_mutated": False}, {"name": "actual_grid_trapezoid", "scope": "registered arithmetic", "interpolation": False, "raw_mutated": False}], "runs": {}, "raw_hash_before_analysis": {}, "raw_hash_after_analysis": {}})
    for topology in TOPOLOGIES:
        for mask in MASKS:
            directory = run_dir(topology, mask)
            directory.mkdir(parents=True, exist_ok=True)
            deck = directory / "deck.cir"
            text = deck_text(topology, mask, directory)
            if deck.exists() and deck.read_text(encoding="utf-8") != text:
                raise RuntimeError(f"refusing to overwrite changed registered deck: {deck}")
            if not deck.exists():
                deck.write_text(text, encoding="utf-8")
    write_json(EXP / "run_state.json", {"schema": "bvm-qb-t1-interface-execution-state-v1", "experiment_id": EXP.name, "created_at": now(), "updated_at": now(), "status": "PREFLIGHT_PASS", "stage_a_sanity": None, "run_order": [], "authorized_physical_solve_count": 15, "actual_physical_solve_count": 0, "final_marker": None})
    print(json.dumps({"status": "PREFLIGHT_PASS", "experiment": EXP.name, "registered_runs": 15, "head": git_head()}, ensure_ascii=False, indent=2))


def read_raw(path: Path) -> tuple[list[str], dict[str, list[float]], list[float]]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.reader(stream)
        try:
            header = [value.strip() for value in next(reader)]
        except StopIteration as exc:
            raise RuntimeError(f"empty raw CSV: {path}") from exc
        if len(header) != len(set(header)):
            raise RuntimeError(f"duplicate raw columns: {path}")
        columns = {name: [] for name in header}
        for row_number, row in enumerate(reader, start=2):
            if not row or not any(cell.strip() for cell in row):
                continue
            if len(row) != len(header):
                raise RuntimeError(f"raw row width mismatch at {path}:{row_number}")
            for name, value in zip(header, row):
                try:
                    parsed = float(value)
                except ValueError as exc:
                    raise RuntimeError(f"non-numeric raw value at {path}:{row_number}:{name}") from exc
                if not math.isfinite(parsed):
                    raise RuntimeError(f"non-finite raw value at {path}:{row_number}:{name}")
                columns[name].append(parsed)
    if "time" not in columns or len(columns["time"]) < 2:
        raise RuntimeError(f"raw time column missing/short: {path}")
    times = columns["time"]
    if any(right <= left for left, right in zip(times, times[1:])):
        raise RuntimeError(f"raw time is not strictly increasing: {path}")
    return header, columns, times


def window_indices(times: list[float], start_ps: float, end_ps: float) -> list[int]:
    return [index for index, value in enumerate(times) if start_ps <= value * 1.0e12 < end_ps]


def actual_integral(times: list[float], values: list[float], start_ps: float, end_ps: float) -> float | None:
    ids = window_indices(times, start_ps, end_ps)
    if len(ids) < 2:
        return None
    return sum(0.5 * (values[left] + values[right]) * (times[right] - times[left]) for left, right in zip(ids, ids[1:]))


def unwrap(values: list[float]) -> list[float]:
    if not values:
        return []
    result = [values[0]]
    two_pi = 2.0 * math.pi
    for value in values[1:]:
        adjusted = value
        while adjusted - result[-1] > math.pi:
            adjusted -= two_pi
        while adjusted - result[-1] < -math.pi:
            adjusted += two_pi
        result.append(adjusted)
    return result


def stats(times: list[float], values: list[float], start_ps: float, end_ps: float, *, phase: bool = False) -> dict[str, Any]:
    ids = window_indices(times, start_ps, end_ps)
    if not ids:
        return {"status": "UNKNOWN", "reason": "no actual stored samples in window"}
    peak_index = max(ids, key=lambda index: abs(values[index]))
    max_index = max(ids, key=lambda index: values[index])
    min_index = min(ids, key=lambda index: values[index])
    result: dict[str, Any] = {
        "status": "DERIVED",
        "window_ps": [start_ps, end_ps],
        "sample_count": len(ids),
        "first": values[ids[0]],
        "final": values[ids[-1]],
        "max": values[max_index],
        "min": values[min_index],
        "peak_abs": abs(values[peak_index]),
        "time_of_peak_abs_ps": times[peak_index] * 1.0e12,
        "range": values[max_index] - values[min_index],
        "rollback_from_peak": values[ids[-1]] - values[peak_index],
    }
    if phase:
        result.update({"first_turns": values[ids[0]] / (2 * math.pi), "final_turns": values[ids[-1]] / (2 * math.pi), "delta_turns": (values[ids[-1]] - values[ids[0]]) / (2 * math.pi), "range_turns": result["range"] / (2 * math.pi)})
    return result


def activity(values: list[float], times: list[float], start_ps: float, end_ps: float, *, phase: bool = False) -> dict[str, Any]:
    ids = window_indices(times, start_ps, end_ps)
    if not ids:
        return {"status": "UNKNOWN", "sample_count": 0}
    if phase:
        reference = values[ids[0]]
        active = [index for index in ids if abs((values[index] - reference) / (2 * math.pi)) >= PHASE_ACTIVITY_TURNS]
        threshold: Any = {"turns": PHASE_ACTIVITY_TURNS}
    else:
        active = [index for index in ids if abs(values[index]) >= V_ACTIVITY]
        threshold = {"voltage_V": V_ACTIVITY}
    return {"status": "FLAG" if len(active) >= MIN_ACTIVITY_SAMPLES else "QUIET_BY_REGISTERED_SCREEN", "threshold": threshold, "sample_count": len(ids), "activity_sample_count": len(active), "minimum_activity_samples": MIN_ACTIVITY_SAMPLES, "first_activity_time_ps": times[active[0]] * 1.0e12 if active else None, "last_activity_time_ps": times[active[-1]] * 1.0e12 if active else None}


def required_headers(topology: str) -> set[str]:
    required: set[str] = set()
    for index in range(1, 5):
        for element in ("B_JM1", "B_JM2", "B_JS1", "B_JS2"):
            required.update(f"{kind}({element}|XBVM{index})" for kind in ("P", "V", "I"))
        required.update(f"I({element}|XBVM{index})" for element in ("L_M1", "L_M2", "L_M3", "L_PM", "L_PSL", "L_SL"))
        required.update(f"I({element})" for element in (f"I_WL{index}", f"I_BL{index}", f"I_SE{index}"))
    required.add("V(COMMON_SL)")
    for index in range(1, 9):
        required.update(f"{kind}(B_JSL{index})" for kind in ("P", "V", "I"))
    required.update({"V(QBIN)", "V(QBOUT)", "I(RJ1|XBQ)", "I(RJ2|XBQ)"})
    required.update(f"{kind}({element}|XBQ)" for element in ("BJS", "BJ1", "BJ2") for kind in ("P", "V", "I"))
    required.update(f"{kind}({element}|XBQ)" for element in ("LIN", "L1", "L2", "L3") for kind in ("I", "V"))
    if topology != "direct":
        count = 6 if topology == "jtl6" else 2
        for index in range(1, count + 1):
            required.update(f"{kind}(B{element}|XJTL{index})" for element in ("01", "02") for kind in ("P", "V", "I"))
            required.add(f"V(JTL{index}_OUT)")
    required.update({"V(T1_I)", "V(CLK)", "V(S)", "V(C)", "I(R_S)", "I(R_C)"})
    required.update(f"{kind}(B_J{index}|XT1)" for index in range(1, 12) for kind in ("P", "V", "I"))
    required.update(f"I({element}|XT1)" for element in ("L1", "L3", "L7", "L8", "L9", "L10", "L15", "L16", "L17", "L11", "L13"))
    return required


def prepare() -> None:
    EXP.mkdir(parents=True, exist_ok=True)
    assert_current_sources()
    preflight = [
        "# BVM -> QB -> T1 interface topology v1 — PREFLIGHT",
        "",
        CONTRACT_SENTENCE,
        "",
        f"- Experiment: `{EXP.name}`",
        f"- Generated at: `{now()}`",
        f"- Registration HEAD: `{git_head()}`",
        f"- Remote `bvm/master` at registration: `{remote_head() or 'UNAVAILABLE'}`",
        "- Preflight status: `PASS`; solver has not been invoked at preflight.",
        f"- Solver: `{solver_context()['version']}`; SHA-256 `{sha256(SOLVER)}`",
        "",
        "## Frozen source closure",
        "",
    ]
    preflight += [f"- `{item['name']}`: `{item['path']}`; SHA-256 `{item['sha256']}`; {item['role']}." for item in source_entries()]
    preflight += [
        "",
        "The canonical QB file is byte-checked against the exact registered text. No deck defines QB parameters or copies the QB source. Existing BVM/JTL files are referenced by repository-relative includes; no old raw/reference artifact is copied.",
        "The current `circuits/t1/t1_cell.cir` is included without modification and has `B_J7 N13 N17` plus `R_J7 N13 N17 10`; the old `R_J7 N18 N17` definition is absent.",
        "",
        "## Exact run matrix and automatic gate",
        "",
        "- Stage A: `jtl6/{0000,0001,0011,0111,1111}`.",
        "- If the registered sanity screen flags `JTL6_T1_INTEGRATION_SANITY_FAILED`, stop and do not invoke `jtl2` or `direct`.",
        "- If sane: Stage B `jtl2/{0000,0001,0011,0111,1111}`; Stage C `direct/{0000,0001,0011,0111,1111}`.",
        "- Maximum and, if Stage A passes, exact physical solve count: 15. No retries, replay, parameter sweep, timing change, or follow-up solve.",
        "",
        "## Frozen topology, timing, and bias",
        "",
        "- `jtl6`: `4xBVM -> COMMON_SL -> JSL1..8 -> canonical QB -> JTL1..6 -> T1.I`.",
        "- `jtl2`: `4xBVM -> COMMON_SL -> JSL1..8 -> canonical QB -> JTL1..2 -> T1.I`.",
        "- `direct`: `4xBVM -> COMMON_SL -> JSL1..8 -> canonical QB -> T1.I`.",
        "- Full galvanic BVM/JSL↔QB loop is retained; no passive capture, source replacement/scaling/filtering, topology modification, or extra/matching resistor is added. The only zero-drop link is the named `T1_I` observation terminal.",
        "- History: `IDLE 0-50; WRITE0 50-61; IDLE 61-70; ZERO_STATE_READ_CONTROL 70-81; IDLE 81-90; WRITE1 90-101; SETTLE 101-110; FINAL READ 110-121; TAIL 121-200 ps`.",
        "- Amplitude `100uA`, 1 ps rise/fall, 9 ps plateau; `.tran 0.1p 200p`. Masks are exactly `0000`, `0001`, `0011`, `0111`, `1111` with bit order `b3b2b1b0 = BVM1/BVM2/BVM3/BVM4`.",
        "- T1: current unmodified cell; `V_BIAS1=1.67m`, `V_BIAS2=1.67m`, `I_BIAS3=35u`, `R_S=12`, `R_C=12`, `R_CLK_QUIET=5`; no clock source and CLK is not floating.",
        "",
        "## Probes and registered arithmetic",
        "",
        "- Every BVM: P/V/I for `B_JM1`, `B_JM2`, `B_JS1`, `B_JS2`; currents `L_M1`, `L_M2`, `L_M3`, `L_PM`, `L_PSL`, `L_SL`; drive-source currents are `I(I_WLn)`, `I(I_BLn)`, `I(I_SEn)`.",
        "- Shared/JSL: `V(COMMON_SL)`, P/V/I `B_JSL1..8`, `I(B_JSL8)`, `V(QBIN)`.",
        "- QB: I/V `LIN`, `L1`, `L2`, `L3`; P/V/I `BJS`, `BJ1`, `BJ2`; I `RJ1`, `RJ2`; `V(QBOUT)`.",
        "- All present JTL levels: P/V/I `B01/B02`, `V(JTLx_OUT)`; T1 all 11 junctions and the requested input/output/inductor probes.",
        "- Analysis windows use actual stored timestamps: `[70,81)`, `[90,101)`, `[101,110)`, `[110,121)`, `[121,126)`, `[126,150)`, `[150,200)` ps. Integrals are actual-grid trapezoids with no interpolation.",
        "- P(...) is raw radians. Displayed turns are explicitly `rad/(2*pi)` and are navigation only, never an SFQ count.",
        "",
        "## Mechanical sanity flags",
        "",
        f"- Voltage activity: at least `{MIN_ACTIVITY_SAMPLES}` actual samples with `abs(V) >= {V_ACTIVITY:g} V` in registered quiet/tail windows.",
        f"- Phase activity: `{PHASE_ACTIVITY_TURNS:g}` turn navigation threshold, activity only; T1 quiet/clock monitors and 0000 carry/J1 tail are checked.",
        f"- JTL6-to-T1.I link consistency: max `abs(V(JTL6_OUT)-V(T1_I)) <= {LINK_DIFF_V:g} V`.",
        "- These are stop flags only, not SFQ, switching, Gate, or physical correctness criteria.",
        "",
        "## Minimal layout override and stop",
        "",
        "The user-requested minimal layout omits `screening/`, `references/`, `qa/`, `handoff/`, `visualization/run_summaries/`, and `analysis/archive/`; root-level machine-readable evidence is retained. Each run contains only `deck.cir`, `raw.csv`, `run.log`, and `plots/`.",
        "After package QA and commit, stop at `EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW`; scientific interpretation, parameter modification, and follow-up solves are not authorized.",
        "",
    ]
    (EXP / "PREFLIGHT.md").write_text("\n".join(preflight), encoding="utf-8")
    entries = source_entries()
    write_json(EXP / "SOURCE_MANIFEST.json", {"schema": "bvm-qb-t1-interface-source-manifest-v1", "experiment_id": EXP.name, "created_at": now(), "registration_head": git_head(), "remote_bvm_master": remote_head(), "sources": entries, "external_source_policy": "Existing repository-relative BVM/JTL inputs are referenced; old raw/reference artifacts are not copied."})
    write_json(EXP / "provenance.json", {"schema": "bvm-qb-t1-interface-provenance-v1", "experiment_id": EXP.name, "created_at": now(), "registration_head": git_head(), "remote_bvm_master": remote_head(), "solver": solver_context(), "sources": entries, "canonical_qb_exact_text_sha256": sha256(QB), "t1_j7_verification": {"required": "B_J7 N13 N17 jjmit area=1.0; R_J7 N13 N17 10", "old_definition_absent": True}, "contract": {"sentence": CONTRACT_SENTENCE, "minimal_layout_override": True, "scientific_analysis_performed": False}, "transformations": [{"name": "phase_unwrap_for_navigation", "scope": "analysis only", "raw_mutated": False, "algorithm": "sequential +/-pi correction by adding/subtracting 2*pi"}, {"name": "phase_turn_display", "scope": "josim-plot2 display only", "formula": "raw_phase_rad/(2*pi)", "raw_mutated": False}, {"name": "actual_grid_trapezoid", "scope": "registered arithmetic", "interpolation": False, "raw_mutated": False}], "runs": {}, "raw_hash_before_analysis": {}, "raw_hash_after_analysis": {}})
    for topology in TOPOLOGIES:
        for mask in MASKS:
            directory = run_dir(topology, mask)
            directory.mkdir(parents=True, exist_ok=True)
            deck = directory / "deck.cir"
            text = deck_text(topology, mask, directory)
            if deck.exists() and deck.read_text(encoding="utf-8") != text:
                raise RuntimeError(f"refusing to overwrite changed registered deck: {deck}")
            if not deck.exists():
                deck.write_text(text, encoding="utf-8")
    write_json(EXP / "run_state.json", {"schema": "bvm-qb-t1-interface-execution-state-v1", "experiment_id": EXP.name, "created_at": now(), "updated_at": now(), "status": "PREFLIGHT_PASS", "stage_a_sanity": None, "run_order": [], "authorized_physical_solve_count": 15, "actual_physical_solve_count": 0, "final_marker": None})
    print(json.dumps({"status": "PREFLIGHT_PASS", "experiment": EXP.name, "registered_runs": 15, "head": git_head()}, ensure_ascii=False, indent=2))


def run_one(topology: str, mask: str, state: dict[str, Any], provenance: dict[str, Any]) -> None:
    directory = run_dir(topology, mask)
    deck = directory / "deck.cir"
    raw = directory / "raw.csv"
    log = directory / "run.log"
    if raw.exists() or log.exists():
        raise RuntimeError(f"refusing overwrite/retry of existing run artifacts: {directory}")
    if not deck.is_file():
        raise RuntimeError(f"missing prepared deck: {deck}")
    command = [str(SOLVER), "-a", "1", "-o", str(raw), str(deck)]
    started = now()
    with log.open("x", encoding="utf-8") as stream:
        stream.write(f"started_at={started}\ncommand={' '.join(command)}\n")
        stream.flush()
        completed = subprocess.run(command, cwd=REPO, stdout=stream, stderr=subprocess.STDOUT, check=False)
        stream.write(f"finished_at={now()}\nexit_code={completed.returncode}\n")
    if completed.returncode != 0 or not raw.is_file():
        raise RuntimeError(f"solver failed for {topology}/{mask}; no retry authorized")
    item = {"run_id": run_id(topology, mask), "topology": topology, "mask": mask, "deck": {"path": rel(deck), "sha256": sha256(deck), "bytes": deck.stat().st_size}, "raw": {"path": rel(raw), "sha256": sha256(raw), "bytes": raw.stat().st_size}, "log": {"path": rel(log), "sha256": sha256(log), "bytes": log.stat().st_size}, "command": command, "solver": solver_context(), "started_at": started, "finished_at": now(), "execution_status": "RUN_PASS", "raw_immutable": True, "scientific_analysis_performed": False}
    provenance.setdefault("runs", {})[run_id(topology, mask)] = item
    state["run_order"].append(run_id(topology, mask))
    state["actual_physical_solve_count"] = len(state["run_order"])
    state["updated_at"] = now()
    write_json(EXP / "provenance.json", provenance)
    write_json(EXP / "run_state.json", state)
    print(json.dumps({"run_id": run_id(topology, mask), "status": "RUN_PASS", "raw_bytes": raw.stat().st_size}, ensure_ascii=False))


def load_provenance() -> dict[str, Any]:
    path = EXP / "provenance.json"
    if not path.is_file():
        raise RuntimeError("prepare has not been completed: missing provenance.json")
    return read_json(path)


def execution_gate() -> tuple[dict[str, Any], dict[str, Any]]:
    assert_current_sources()
    state = read_json(EXP / "run_state.json")
    provenance = load_provenance()
    if provenance.get("registration_head") != git_head():
        raise RuntimeError("HEAD changed after preflight; refusing physical solve")
    recorded = {entry["name"]: entry["sha256"] for entry in provenance.get("sources", [])}
    current = {entry["name"]: entry["sha256"] for entry in source_entries()}
    if recorded != current:
        raise RuntimeError("registered source closure changed after preflight")
    if state.get("final_marker") or state.get("actual_physical_solve_count", 0):
        raise RuntimeError("physical execution already started or experiment finalized; no rerun is authorized")
    return state, provenance


def value_stats(times: list[float], values: list[float], start: float, end: float, *, phase: bool = False) -> dict[str, Any]:
    ids = window_indices(times, start, end)
    if not ids:
        return {"status": "UNKNOWN", "reason": "no actual stored samples"}
    peak = max(ids, key=lambda index: abs(values[index]))
    high = max(ids, key=lambda index: values[index])
    low = min(ids, key=lambda index: values[index])
    result: dict[str, Any] = {
        "status": "DERIVED",
        "window_ps": [start, end],
        "sample_count": len(ids),
        "first": values[ids[0]],
        "final": values[ids[-1]],
        "max": values[high],
        "min": values[low],
        "peak_abs": abs(values[peak]),
        "time_of_peak_abs_ps": times[peak] * 1e12,
        "range": values[high] - values[low],
        "rollback_from_peak": values[ids[-1]] - values[peak],
    }
    if phase:
        result.update({
            "first_turns": values[ids[0]] / (2 * math.pi),
            "final_turns": values[ids[-1]] / (2 * math.pi),
            "delta_turns": (values[ids[-1]] - values[ids[0]]) / (2 * math.pi),
            "range_turns": result["range"] / (2 * math.pi),
        })
    return result


def activity_stats(times: list[float], values: list[float], start: float, end: float, *, phase: bool = False) -> dict[str, Any]:
    ids = window_indices(times, start, end)
    if phase:
        if not ids:
            return {"status": "UNKNOWN", "sample_count": 0}
        base = values[ids[0]]
        active = [index for index in ids if abs((values[index] - base) / (2 * math.pi)) >= PHASE_ACTIVITY_TURNS]
        threshold = {"turns": PHASE_ACTIVITY_TURNS}
    else:
        active = [index for index in ids if abs(values[index]) >= V_ACTIVITY]
        threshold = {"voltage_V": V_ACTIVITY}
    return {
        "status": "FLAG" if len(active) >= MIN_ACTIVITY_SAMPLES else "QUIET_BY_REGISTERED_SCREEN",
        "threshold": threshold,
        "sample_count": len(ids),
        "activity_sample_count": len(active),
        "minimum_activity_samples": MIN_ACTIVITY_SAMPLES,
        "first_activity_time_ps": times[active[0]] * 1e12 if active else None,
        "last_activity_time_ps": times[active[-1]] * 1e12 if active else None,
    }


def run_data(topology: str, mask: str) -> tuple[list[str], dict[str, list[float]], list[float]]:
    path = raw_path(topology, mask)
    header, data, times = read_raw(path)
    missing = sorted(required_headers(topology) - set(header))
    if missing:
        raise RuntimeError(f"missing required probes for {topology}/{mask}: {missing}")
    return header, data, times


def window_map(times: list[float], values: list[float], *, phase: bool = False, windows: Iterable[tuple[int, int]] = WINDOWS) -> dict[str, Any]:
    return {f"{start:g}_{end:g}": value_stats(times, values, start, end, phase=phase) for start, end in windows}


def phase_area_map(times: list[float], data: dict[str, list[float]], phase_signal: str, windows: Iterable[tuple[int, int]] = WINDOWS) -> dict[str, Any]:
    voltage_signal = phase_signal.replace("P(", "V(", 1)
    phase_values = unwrap(data[phase_signal])
    result: dict[str, Any] = {}
    for start, end in windows:
        ids = window_indices(times, start, end)
        delta = unwrap(data[phase_signal])[ids[-1]] - unwrap(data[phase_signal])[ids[0]] if ids else None
        area = actual_integral(times, data[voltage_signal], start, end)
        result[f"{start:g}_{end:g}"] = {
            "phase_delta_rad": delta,
            "phase_delta_turns": delta / (2 * math.pi) if delta is not None else None,
            "voltage_area_Vs": area,
            "voltage_area_over_phi0": area / PHI0 if area is not None else None,
            "same_jj_same_direction_same_window": True,
            "actual_grid_trapezoid": True,
        }
    return result


def run_metrics(topology: str, mask: str) -> dict[str, Any]:
    header, data, times = run_data(topology, mask)
    phases = {name: unwrap(data[name]) for name in header if name.startswith("P(")}
    result: dict[str, Any] = {
        "run_id": run_id(topology, mask),
        "topology": topology,
        "mask": mask,
        "raw": {"path": rel(raw_path(topology, mask)), "sha256": sha256(raw_path(topology, mask)), "bytes": raw_path(topology, mask).stat().st_size},
        "raw_grid": {"sample_count": len(times), "first_time_ps": times[0] * 1e12, "last_time_ps": times[-1] * 1e12, "strictly_increasing": True, "raw_time_unit": "s", "display_time_unit": "ps"},
        "observed": {"header_count": len(header), "required_probe_count": len(required_headers(topology)), "required_probes_present": True, "phase_raw_unit": "radians"},
        "derived": {"window_stats": {}, "phase_voltage_area": {}, "bvm": {}, "t1_clock_quiet_monitors": {}},
        "unknown": [],
    }
    key_signals = [
        "P(B_JM1|XBVM1)", "P(B_JM2|XBVM1)", "P(B_JS1|XBVM1)", "P(B_JS2|XBVM1)", "I(L_SL|XBVM1)",
        "V(COMMON_SL)", "I(B_JSL8)", "V(QBIN)", "P(BJ1|XBQ)", "P(BJ2|XBQ)", "I(L1|XBQ)", "I(L2|XBQ)", "I(L3|XBQ)", "V(QBOUT)",
        "P(B_J1|XT1)", "P(B_J6|XT1)", "P(B_J10|XT1)", "P(B_J11|XT1)", "V(T1_I)", "V(C)",
    ]
    if topology != "direct":
        last = 6 if topology == "jtl6" else 2
        key_signals += [f"V(JTL{last}_OUT)", f"P(B01|XJTL{last})", f"P(B02|XJTL{last})"]
    for signal in key_signals:
        if signal not in data and signal not in phases:
            continue
        values = phases[signal] if signal.startswith("P(") else data[signal]
        result["derived"]["window_stats"][signal] = window_map(times, values, phase=signal.startswith("P("))
    phase_targets = [
        *(f"P({element}|XBVM{index})" for index in range(1, 5) for element in ("B_JM1", "B_JM2", "B_JS1", "B_JS2")),
        "P(BJS|XBQ)", "P(BJ1|XBQ)", "P(BJ2|XBQ)",
    ]
    for signal in phase_targets:
        if signal in phases:
            result["derived"]["phase_voltage_area"][signal] = phase_area_map(times, data, signal)
    for index in range(1, 5):
        tag = f"XBVM{index}"
        item = {"phase": {}, "currents": {}, "drive_source_currents": {}}
        for element in ("B_JM1", "B_JM2", "B_JS1", "B_JS2"):
            signal = f"P({element}|{tag})"
            item["phase"][element] = window_map(times, phases[signal], phase=True)
        for element in ("L_M1", "L_M2", "L_M3", "L_PM", "L_PSL", "L_SL"):
            signal = f"I({element}|{tag})"
            item["currents"][element] = window_map(times, data[signal])
        for element in (f"I_WL{index}", f"I_BL{index}", f"I_SE{index}"):
            signal = f"I({element})"
            item["drive_source_currents"][element] = window_map(times, data[signal])
        result["derived"]["bvm"][tag] = item
    result["derived"]["t1_clock_quiet_monitors"] = {
        element: {f"{start:g}_{end:g}": activity_stats(times, data[f"V({element}|XT1)"], start, end) for start, end in QUIET_WINDOWS}
        for element in ("B_J2", "B_J3")
    }
    result["derived"]["phase_display_convention"] = "raw P radians; turns = independently unwrapped radians/(2*pi); navigation only, not SFQ count"
    return result


def compare_traces(left: list[float], right: list[float], times: list[float]) -> dict[str, Any]:
    if len(left) != len(right) or len(left) != len(times):
        return {"status": "UNKNOWN", "reason": "different actual grids"}
    differences = [a - b for a, b in zip(left, right)]
    peak = max(range(len(differences)), key=lambda index: abs(differences[index]))
    rms = math.sqrt(sum(value * value for value in differences) / len(differences))
    return {"status": "DERIVED", "max_abs_difference": abs(differences[peak]), "rms_difference": rms, "time_of_max_difference_ps": times[peak] * 1e12, "declared_trace_tolerance": 1e-8, "within_declared_trace_tolerance": abs(differences[peak]) <= 1e-8}


def population_symmetry(topology: str, mask: str) -> dict[str, Any]:
    if mask == "0011":
        pairs = ((3, 4),)
    elif mask == "0111":
        pairs = ((2, 3), (3, 4))
    else:
        return {"status": "NOT_REGISTERED_FOR_THIS_MASK", "mask": mask, "comparisons": []}
    _, data, times = run_data(topology, mask)
    comparisons: list[dict[str, Any]] = []
    for left_index, right_index in pairs:
        for element in ("B_JM1", "B_JM2", "B_JS1", "B_JS2"):
            for kind in ("P", "V", "I"):
                left = f"{kind}({element}|XBVM{left_index})"
                right = f"{kind}({element}|XBVM{right_index})"
                item = compare_traces(data[left], data[right], times)
                item.update({"population_pair": [left_index, right_index], "signal": element, "kind": kind, "left": left, "right": right})
                comparisons.append(item)
        left = f"I(L_SL|XBVM{left_index})"
        right = f"I(L_SL|XBVM{right_index})"
        item = compare_traces(data[left], data[right], times)
        item.update({"population_pair": [left_index, right_index], "signal": "L_SL", "kind": "I", "left": left, "right": right})
        comparisons.append(item)
    return {"status": "DERIVED", "mask": mask, "comparisons": comparisons, "all_within_declared_trace_tolerance": all(item.get("within_declared_trace_tolerance", False) for item in comparisons)}


def population_across_masks(topology: str) -> dict[str, Any]:
    """Compare BVM3/BVM4 in 0011 versus 0111 using registered windows."""
    result: dict[str, Any] = {"topology": topology, "mask_pair": ["0011", "0111"], "populations": {}}
    for index in (3, 4):
        result["populations"][f"BVM{index}"] = {}
        for mask in ("0011", "0111"):
            _, data, times = run_data(topology, mask)
            item: dict[str, Any] = {}
            for element in ("B_JS1", "B_JS2"):
                signal = f"P({element}|XBVM{index})"
                item[signal] = window_map(times, unwrap(data[signal]), phase=True, windows=((110, 121), (121, 126), (126, 150), (150, 200)))
            signal = f"I(L_SL|XBVM{index})"
            item[signal] = window_map(times, data[signal], windows=((110, 121), (121, 126), (126, 150), (150, 200)))
            item["requested_L_SL_peak_and_integral"] = {}
            for start, end in ((110, 121), (121, 126)):
                summary = value_stats(times, data[signal], start, end)
                integral = actual_integral(times, data[signal], start, end)
                item["requested_L_SL_peak_and_integral"][f"{start:g}_{end:g}"] = {
                    "peak_abs_A": summary["peak_abs"],
                    "peak_time_ps": summary["time_of_peak_abs_ps"],
                    "final_A": summary["final"],
                    "rollback_from_peak_A": summary["rollback_from_peak"],
                    "integral_A_s": integral,
                    "integral_pC": integral * 1e12 if integral is not None else None,
                    "actual_grid_trapezoid": True,
                }
            result["populations"][f"BVM{index}"][mask] = item
    # The pointwise comparison is legal here because the two masks share the
    # same topology, stimulus timing and registered actual-grid protocol.
    for index in (3, 4):
        _, left, left_times = run_data(topology, "0011")
        _, right, right_times = run_data(topology, "0111")
        if left_times != right_times:
            result.setdefault("unknown", []).append(f"BVM{index}: actual grids differ")
            continue
        for element in ("B_JS1", "B_JS2"):
            signal = f"P({element}|XBVM{index})"
            result.setdefault("pointwise_same_protocol_differences", {})[f"BVM{index}:{element}"] = compare_traces(left[signal], right[signal], left_times)
    return result


def cross_topology_summary() -> dict[str, Any]:
    signals = [
        *(f"P({element}|XBVM{index})" for index in (3, 4) for element in ("B_JM1", "B_JM2", "B_JS1", "B_JS2")),
        *(f"I(L_SL|XBVM{index})" for index in (3, 4)),
        "V(COMMON_SL)", "I(B_JSL8)", "V(QBIN)", "P(BJ1|XBQ)", "P(BJ2|XBQ)",
        "I(L1|XBQ)", "I(L2|XBQ)", "I(L3|XBQ)", "V(QBOUT)",
        "P(B_J1|XT1)", "P(B_J6|XT1)", "P(B_J10|XT1)", "P(B_J11|XT1)", "V(T1_I)", "V(C)",
    ]
    result: dict[str, Any] = {"same_mask": {}, "note": "same-mask registered numeric summaries; no topology ranking or winner selection"}
    compare_windows = ((110, 121), (121, 126), (126, 150), (150, 200))
    for mask in MASKS:
        result["same_mask"][mask] = {}
        for topology in TOPOLOGIES:
            _, data, times = run_data(topology, mask)
            values: dict[str, Any] = {}
            for signal in signals:
                if signal not in data:
                    continue
                series = unwrap(data[signal]) if signal.startswith("P(") else data[signal]
                values[signal] = window_map(times, series, phase=signal.startswith("P("), windows=compare_windows)
            result["same_mask"][mask][topology] = values
    return result


def stage_a_sanity() -> dict[str, Any]:
    """Run the preregistered Stage-A mechanical stop screen on jtl6/0000."""
    _, data, times = run_data("jtl6", "0000")

    def voltage(signal: str, start: float, end: float) -> dict[str, Any]:
        return activity_stats(times, data[signal], start, end)

    def phase(signal: str, start: float, end: float) -> dict[str, Any]:
        return activity_stats(times, unwrap(data[signal]), start, end, phase=True)

    carry_signals = ("V(B_J6|XT1)", "V(B_J10|XT1)", "V(B_J11|XT1)", "V(C)")
    carry = {signal: voltage(signal, 150, 200) for signal in carry_signals}
    j1 = {"voltage": voltage("V(B_J1|XT1)", 150, 200), "phase": phase("P(B_J1|XT1)", 150, 200)}
    clock_quiet = {
        signal: {f"{start:g}_{end:g}": voltage(signal, start, end) for start, end in QUIET_WINDOWS}
        for signal in ("V(B_J2|XT1)", "V(B_J3|XT1)")
    }
    link_difference = [data["V(JTL6_OUT)"][index] - data["V(T1_I)"][index] for index in range(len(times))]
    peak_index = max(range(len(link_difference)), key=lambda index: abs(link_difference[index]))
    link = {
        "source": "V(JTL6_OUT)",
        "sink": "V(T1_I)",
        "max_abs_difference_V": abs(link_difference[peak_index]),
        "time_of_max_difference_ps": times[peak_index] * 1e12,
        "declared_tolerance_V": LINK_DIFF_V,
        "within_declared_tolerance": abs(link_difference[peak_index]) <= LINK_DIFF_V,
    }

    def has_flag(value: Any) -> bool:
        if isinstance(value, dict):
            if value.get("status") == "FLAG":
                return True
            return any(has_flag(child) for child in value.values())
        return False

    flags: list[str] = []
    if has_flag(carry):
        flags.append("ZERO_POPULATION_T1_CARRY_SELF_ACTIVITY")
    if has_flag(j1):
        flags.append("J1_RUNAWAY_WITHOUT_FINAL_BVM_INPUT")
    if has_flag(clock_quiet):
        flags.append("T1_BIAS_OR_QUIET_BRANCH_ACTIVITY_WITHOUT_CLOCK")
    if not link["within_declared_tolerance"]:
        flags.append("6JTL_EVENT_CANNOT_ENTER_T1_I")
    return {
        "schema": "bvm-qb-t1-stage-a-sanity-v1",
        "control_run": "jtl6_0000",
        "registered_thresholds": {"voltage_activity_V": V_ACTIVITY, "phase_activity_turns": PHASE_ACTIVITY_TURNS, "minimum_activity_samples": MIN_ACTIVITY_SAMPLES, "link_difference_V": LINK_DIFF_V},
        "checks": {"0000_t1_carry_self_activity": carry, "0000_j1_tail_activity_without_final_bvm_input": j1, "t1_bias_or_quiet_branch_activity_without_clock": clock_quiet, "jtl6_to_t1_i_link": link},
        "flags": flags,
        "status": "FAIL" if flags else "PASS",
        "stop_marker": "JTL6_T1_INTEGRATION_SANITY_FAILED" if flags else None,
        "scientific_interpretation": "NOT_PERFORMED",
    }


def write_result(state: dict[str, Any], stage_a: dict[str, Any] | None) -> dict[str, Any]:
    completed: list[tuple[str, str]] = []
    for item in state.get("run_order", []):
        topology, mask = item.split("_", 1)
        if raw_path(topology, mask).is_file():
            completed.append((topology, mask))
    per_run = {run_id(topology, mask): run_metrics(topology, mask) for topology, mask in completed}
    symmetry = {run_id(topology, mask): population_symmetry(topology, mask) for topology, mask in completed if mask in ("0011", "0111")}
    across_masks = {topology: population_across_masks(topology) for topology in TOPOLOGIES if all(raw_path(topology, mask).is_file() for mask in ("0011", "0111"))}
    comparisons = cross_topology_summary() if len(completed) == 15 else {}
    stop_marker = "EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW" if len(completed) == 15 or (stage_a and stage_a.get("status") == "FAIL") else "RUNNING"
    result: dict[str, Any] = {
        "schema": "bvm-qb-t1-interface-result-v1",
        "experiment_id": EXP.name,
        "generated_at": now(),
        "artifact_status": "VALID" if completed else "UNKNOWN",
        "execution": {"authorized_physical_solve_count": 15, "actual_physical_solve_count": len(completed), "completed_runs": [run_id(topology, mask) for topology, mask in completed], "stage_a_sanity_status": stage_a.get("status") if stage_a else None, "stage_a_stop_marker": stage_a.get("stop_marker") if stage_a else None},
        "observed": {"completed_topologies": sorted({topology for topology, _ in completed}), "completed_run_count": len(completed), "raw_files_immutable": True, "phase_raw_unit": "radians", "time_raw_unit": "seconds"},
        "derived": {"per_run_registered_window_arithmetic": per_run, "within_run_population_symmetry": symmetry, "across_mask_bvm3_bvm4": across_masks, "same_mask_cross_topology": comparisons},
        "unknown": ["SFQ count/event identity", "JJ switching certification from any single trace", "physical interface Gate", "T1 truth table", "mechanism/root cause", "timestep convergence", "hardware equivalence", "parameter ranking or route selection"],
        "interpretation": {"scientific_analysis_performed": False, "physical_verdict": "NOT_ASSIGNED", "review_state": "AWAITING_SCIENTIFIC_REVIEW", "phase_turns_are_navigation_only": True},
        "stop": {"final_marker": stop_marker, "automatic_follow_up": False, "automatic_parameter_change": False},
    }
    write_json(EXP / "result.json", result)
    completed_text = ", ".join(result["execution"]["completed_runs"]) or "none"
    lines = [
        "# BVM -> QB -> T1 interface topology v1",
        "",
        "## Evidence status",
        "",
        f"- Artifact status: `{result['artifact_status']}`.",
        f"- Physical solves completed: `{len(completed)}` / `15` authorized.",
        f"- Completed runs: `{completed_text}`.",
        f"- Stage A sanity: `{result['execution']['stage_a_sanity_status'] or 'NOT_RUN'}`.",
        "- Scientific interpretation: `NOT_PERFORMED`; physical verdict: `NOT_ASSIGNED`; review state: `AWAITING_SCIENTIFIC_REVIEW`.",
        "",
        "This file records raw observations and registered arithmetic only. P(...) is raw radians; derived turns are independently unwrapped radians divided by `2*pi` and are navigation, not SFQ counts. Voltage-area arithmetic uses the same JJ, direction, stored grid and half-open window.",
        "",
        "## Registered scope",
        "",
        "The canonical QB is the shared `circuits/qb/bq_parameterized_v1.cir` source. All three topologies retain the galvanic BVM/JSL↔QB loop and use the current unmodified T1 cell. No replay, passive capture, source scaling/filtering, parameter sweep, matching resistor, clock source, timing change or retry was authorized.",
        "",
        "## Machine-readable evidence",
        "",
        "- [PREFLIGHT.md](PREFLIGHT.md)",
        "- [SOURCE_MANIFEST.json](SOURCE_MANIFEST.json)",
        "- [provenance.json](provenance.json)",
        "- [result.json](result.json)",
        "- [mechanical_qa.json](mechanical_qa.json)",
        "- [visualization_manifest.json](visualization_manifest.json)",
        "- [visualization_qa.json](visualization_qa.json)",
        "",
        "## Review boundary",
        "",
        "The raw data do not by themselves certify SFQ counts, JJ switching, downstream reception, an interface Gate, T1 logic, mechanism, convergence, hardware behavior, parameter ranking, or a follow-up experiment.",
        "",
        stop_marker,
        "",
    ]
    (EXP / "RESULT.md").write_text("\n".join(lines), encoding="utf-8")
    return result


def analyze() -> None:
    state = read_json(EXP / "run_state.json")
    stage_a = read_json(EXP / "stage_a_sanity.json") if (EXP / "stage_a_sanity.json").is_file() else None
    provenance = load_provenance()
    before = {item: sha256(raw_path(*item.split("_", 1))) for item in state.get("run_order", [])}
    provenance["raw_hash_before_analysis"] = before
    write_json(EXP / "provenance.json", provenance)
    result = write_result(state, stage_a)
    after = {item: sha256(raw_path(*item.split("_", 1))) for item in state.get("run_order", [])}
    if before != after:
        raise RuntimeError("raw hash changed during analysis")
    provenance = load_provenance()
    provenance["raw_hash_after_analysis"] = after
    provenance["analysis"] = {"result_path": rel(EXP / "result.json"), "generated_at": now(), "raw_hashes_equal_before_after": True, "scientific_analysis_performed": False}
    write_json(EXP / "provenance.json", provenance)
    print(json.dumps({"status": "ANALYSIS_ARITHMETIC_COMPLETE", "run_count": len(result["execution"]["completed_runs"]), "raw_hashes_equal": True}, ensure_ascii=False, indent=2))


def run_all() -> None:
    state, provenance = execution_gate()
    for mask in STAGE_A:
        run_one("jtl6", mask, state, provenance)
    sanity = stage_a_sanity()
    state["stage_a_sanity"] = sanity
    state["updated_at"] = now()
    write_json(EXP / "stage_a_sanity.json", sanity)
    write_json(EXP / "run_state.json", state)
    if sanity["status"] == "FAIL":
        state["status"] = "STOPPED_STAGE_A_SANITY_FAILURE"
        state["final_marker"] = "EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW"
        write_json(EXP / "run_state.json", state)
        analyze()
        print(json.dumps({"status": "JTL6_T1_INTEGRATION_SANITY_FAILED", "stage_b_and_c_invoked": False}, ensure_ascii=False, indent=2))
        return
    for topology in ("jtl2", "direct"):
        for mask in MASKS:
            run_one(topology, mask, state, provenance)
    state["status"] = "ALL_AUTHORIZED_RUNS_COMPLETE"
    state["final_marker"] = "EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW"
    state["updated_at"] = now()
    write_json(EXP / "run_state.json", state)
    analyze()
    print(json.dumps({"status": "ALL_AUTHORIZED_RUNS_COMPLETE", "physical_solve_count": state["actual_physical_solve_count"]}, ensure_ascii=False, indent=2))


def mechanical_qa() -> dict[str, Any]:
    state = read_json(EXP / "run_state.json")
    provenance = load_provenance()
    forbidden = ("screening", "references", "qa", "handoff", "visualization/run_summaries", "analysis/archive")
    forbidden_found = [item for item in forbidden if (EXP / item).exists()]
    completed: list[tuple[str, str]] = []
    for item in state.get("run_order", []):
        topology, mask = item.split("_", 1)
        if raw_path(topology, mask).is_file():
            completed.append((topology, mask))
    checks: dict[str, Any] = {}
    failures: list[str] = []
    for topology, mask in completed:
        name = run_id(topology, mask)
        directory = run_dir(topology, mask)
        actual_entries = {path.name for path in directory.iterdir()}
        unexpected = sorted(actual_entries - {"deck.cir", "raw.csv", "run.log", "plots"})
        required_files = all((directory / item).is_file() for item in ("deck.cir", "raw.csv", "run.log"))
        try:
            header, _, times = run_data(topology, mask)
            missing = sorted(required_headers(topology) - set(header))
            grid = {"sample_count": len(times), "first_time_ps": times[0] * 1e12, "last_time_ps": times[-1] * 1e12, "strictly_increasing": True}
        except Exception as exc:  # preserve invalid-artifact status separately from physical status
            missing = [f"read_error:{exc}"]
            grid = {"status": "ARTIFACT_INVALID"}
        recorded = provenance.get("runs", {}).get(name, {})
        raw = directory / "raw.csv"
        raw_hash = sha256(raw) if raw.is_file() else None
        hash_match = raw_hash == recorded.get("raw", {}).get("sha256")
        deck_text_value = (directory / "deck.cir").read_text(encoding="utf-8") if (directory / "deck.cir").is_file() else ""
        deck_checks = {
            "contains_canonical_qb_include": any("bq_parameterized_v1.cir" in line for line in deck_text_value.splitlines() if line.strip().startswith(".include")),
            "contains_qb_parameter_override": any(token in deck_text_value for token in ("L1_VALUE", "RJ1_VALUE", "RJ2_VALUE", "IB_VALUE")),
            "tran_exact": ".tran 0.1p 200p" in deck_text_value,
            "contains_clock_source": bool(re.search(r"^V_?CLK\b|sfq_gen_clk", deck_text_value, flags=re.MULTILINE | re.IGNORECASE)),
            "has_quiet_clock_resistor": "R_CLK_QUIET CLK 0 5" in deck_text_value,
            "has_current_t1": "XT1 T1_I CLK S C N_BIAS1 N_BIAS2 N_BIAS3 T1" in deck_text_value,
            "has_unmodified_t1_include": "t1_cell.cir" in deck_text_value,
        }
        invalid = bool(unexpected or not required_files or missing or not hash_match or not deck_checks["contains_canonical_qb_include"] or deck_checks["contains_qb_parameter_override"] or not deck_checks["tran_exact"] or deck_checks["contains_clock_source"] or not deck_checks["has_quiet_clock_resistor"] or not deck_checks["has_current_t1"] or not deck_checks["has_unmodified_t1_include"])
        if invalid:
            failures.append(name)
        checks[name] = {
            "status": "ARTIFACT_INVALID" if invalid else "PASS",
            "unexpected_entries": unexpected,
            "required_files_present": required_files,
            "missing_required_probes": missing,
            "raw_sha256": raw_hash,
            "recorded_raw_sha256": recorded.get("raw", {}).get("sha256"),
            "raw_hash_match": hash_match,
            "deck": deck_checks,
            "grid": grid,
        }
    expected_count_ok = len(completed) in (5, 15)
    result = {
        "schema": "bvm-qb-t1-mechanical-qa-v1",
        "experiment_id": EXP.name,
        "generated_at": now(),
        "status": "PASS" if not failures and not forbidden_found and expected_count_ok else "FAIL",
        "artifact_status": "VALID" if not failures and not forbidden_found and expected_count_ok else "ARTIFACT_INVALID",
        "completed_run_count": len(completed),
        "authorized_run_count": 15,
        "forbidden_paths_found": forbidden_found,
        "runs": checks,
        "raw_immutability": {"analysis_before_after_equal": provenance.get("analysis", {}).get("raw_hashes_equal_before_after", False), "raw_files_modified_by_qa": 0},
        "scientific_interpretation_performed": False,
    }
    write_json(EXP / "mechanical_qa.json", result)
    print(json.dumps({"status": result["status"], "artifact_status": result["artifact_status"], "run_count": len(completed), "failures": failures}, ensure_ascii=False, indent=2))
    if result["status"] != "PASS":
        raise RuntimeError("mechanical QA failed; artifact is invalid")
    return result


def select_columns(header: list[str], view: str, topology: str) -> list[str]:
    def is_bvm_phase(name: str) -> bool:
        return name.startswith("P(B_JM1|") or name.startswith("P(B_JM2|") or name.startswith("P(B_JS1|") or name.startswith("P(B_JS2|")

    def is_bvm_current(name: str) -> bool:
        return name.startswith("I(L_M1|") or name.startswith("I(L_M2|") or name.startswith("I(L_M3|") or name.startswith("I(L_PM|") or name.startswith("I(L_PSL|") or name.startswith("I(L_SL|") or re.fullmatch(r"I\(I_(WL|BL|SE)[1-4]\)", name) is not None

    def is_source_jsl(name: str) -> bool:
        return name == "V(COMMON_SL)" or name == "V(QBIN)" or re.fullmatch(r"[PVI]\(B_JSL[1-8]\)", name) is not None

    def is_qb(name: str) -> bool:
        return re.fullmatch(r"[IV]\((LIN|L1|L2|L3)\|XBQ\)", name) is not None or re.fullmatch(r"[PVI]\((BJS|BJ1|BJ2)\|XBQ\)", name) is not None or name in {"I(RJ1|XBQ)", "I(RJ2|XBQ)", "V(QBOUT)"}

    def is_jtl(name: str) -> bool:
        return re.fullmatch(r"[PVI]\((B01|B02)\|XJTL[1-6]\)", name) is not None or re.fullmatch(r"V\(JTL[1-6]_OUT\)", name) is not None

    def is_t1_jj(name: str) -> bool:
        return re.fullmatch(r"[PVI]\(B_J([1-9]|10|11)\|XT1\)", name) is not None

    def is_t1_io(name: str) -> bool:
        return name in {"V(T1_I)", "V(CLK)", "V(S)", "V(C)", "I(R_S)", "I(R_C)"} or re.fullmatch(r"I\((L1|L3|L7|L8|L9|L10|L15|L16|L17|L11|L13)\|XT1\)", name) is not None

    predicates = {"01_bvm_phase": is_bvm_phase, "02_bvm_currents": is_bvm_current, "03_source_jsl": is_source_jsl, "04_qb": is_qb, "05_jtl": is_jtl, "06_t1_jj": is_t1_jj, "07_t1_io": is_t1_io}
    if topology == "direct":
        predicates.pop("05_jtl")
    return [name for name in header if name != "time" and predicates[view](name)]


def visualize() -> dict[str, Any]:
    qa = read_json(EXP / "mechanical_qa.json")
    if qa.get("status") != "PASS":
        raise RuntimeError("run mechanical QA before visualization")
    entries: list[dict[str, Any]] = []
    failures: list[str] = []
    for topology in TOPOLOGIES:
        for mask in MASKS:
            raw = raw_path(topology, mask)
            if not raw.is_file():
                continue
            header, _, _ = run_data(topology, mask)
            output_dir = run_dir(topology, mask) / "plots"
            output_dir.mkdir(exist_ok=True)
            for view in ("01_bvm_phase", "02_bvm_currents", "03_source_jsl", "04_qb", "05_jtl", "06_t1_jj", "07_t1_io"):
                if topology == "direct" and view == "05_jtl":
                    continue
                subset = select_columns(header, view, topology)
                if not subset:
                    failures.append(f"{rel(output_dir / (view + '.html'))}:empty_subset")
                    continue
                output = output_dir / f"{view}.html"
                if output.exists():
                    raise RuntimeError(f"refusing to overwrite visualization: {output}")
                title = f"{EXP.name} | {topology} | mask={mask} | {view} | raw 0-200 ps"
                command = [sys.executable, str(PLOTTER), str(raw), "-x", str(output), "-t", "sep_comb", "-c", "dark", "-j", "2pi", "-w", title, "-s", *subset]
                completed = subprocess.run(command, cwd=REPO, capture_output=True, text=True, check=False)
                if completed.returncode != 0 or not output.is_file() or output.stat().st_size == 0:
                    failures.append(f"{rel(output)}:renderer_exit_{completed.returncode}")
                    continue
                entries.append({"path": rel(output), "run_id": run_id(topology, mask), "topology": topology, "mask": mask, "view": view, "raw_path": rel(raw), "raw_sha256": sha256(raw), "renderer": {"path": rel(PLOTTER), "sha256": sha256(PLOTTER)}, "command": command, "window_ps": [0, 200], "phase_display": "2pi turns display from raw radians; not SFQ count", "standalone": True, "comparison": False})
    manifest = {"schema": "bvm-qb-t1-visualization-manifest-v1", "experiment_id": EXP.name, "generated_at": now(), "renderer": {"path": rel(PLOTTER), "sha256": sha256(PLOTTER), "layout": "sep_comb", "color": "dark", "phase_option": "2pi"}, "whole_run_window_ps": [0, 200], "focused_windows": [], "comparison_entries": [], "entries": entries, "entry_count": len(entries), "no_focused_html": True, "no_png_pdf": True, "scientific_interpretation_performed": False, "status": "PASS" if not failures else "FAIL"}
    write_json(EXP / "visualization_manifest.json", manifest)
    image_files = [rel(path) for path in EXP.rglob("*") if path.is_file() and path.suffix.lower() in {".png", ".pdf", ".jpeg", ".webp", ".svg"}]
    vizqa = {"schema": "bvm-qb-t1-visualization-qa-v1", "experiment_id": EXP.name, "generated_at": now(), "status": "PASS" if not failures and not image_files else "FAIL", "entry_count": len(entries), "failures": failures, "full_run_only": True, "focused_windows": [], "comparisons": 0, "image_files": image_files, "raw_hashes_rechecked": all(item["raw_sha256"] == sha256(REPO / item["raw_path"]) for item in entries), "phase_unit_note": "raw P values remain radians; -j 2pi is display conversion only", "scientific_interpretation_performed": False}
    if not vizqa["raw_hashes_rechecked"]:
        vizqa["status"] = "FAIL"
        vizqa["failures"].append("raw_hash_changed_after_render")
    write_json(EXP / "visualization_qa.json", vizqa)
    print(json.dumps({"status": vizqa["status"], "html_count": len(entries), "failures": failures}, ensure_ascii=False, indent=2))
    if vizqa["status"] != "PASS":
        raise RuntimeError("visualization QA failed")
    return manifest


def invalidate_superseded() -> None:
    """Mark an immutable predecessor invalid without touching its raw data."""
    state_path = EXP / "run_state.json"
    result_path = EXP / "result.json"
    provenance_path = EXP / "provenance.json"
    if not state_path.is_file() or not result_path.is_file() or not provenance_path.is_file():
        raise RuntimeError("cannot supersede predecessor without its root evidence")
    defect = {
        "status": "ARTIFACT_INVALID",
        "reason": "JoSIM logs reported Missing model: JJMIT and Using default model for top-level BVM/JSL/T1 junctions; the QB-local exact model was not global scope.",
        "evidence": "runs/*/*/run.log",
        "raw_and_logs_preserved": True,
        "superseded_by": "bvm-qb-t1-interface-topology-v1-20260914-v2",
        "repair": "add existing circuits/models/jjmit.cir as a global include while keeping canonical QB byte-identical",
    }
    result = read_json(result_path)
    result["artifact_status"] = "ARTIFACT_INVALID"
    result["defect"] = defect
    result.setdefault("interpretation", {})["scientific_analysis_performed"] = False
    result["interpretation"]["physical_verdict"] = "NOT_ASSIGNED"
    result["interpretation"]["review_state"] = "SUPERSEDED_ARTIFACT_INVALID"
    result["stop"] = {"final_marker": "ARTIFACT_INVALID / SUPERSEDED", "automatic_follow_up": False, "automatic_parameter_change": False}
    write_json(result_path, result)
    state = read_json(state_path)
    state["status"] = "ARTIFACT_INVALID_SUPERSEDED"
    state["final_marker"] = "ARTIFACT_INVALID / SUPERSEDED"
    state["superseded_by"] = defect["superseded_by"]
    state["updated_at"] = now()
    write_json(state_path, state)
    provenance = read_json(provenance_path)
    provenance["artifact_status"] = "ARTIFACT_INVALID"
    provenance["defect"] = defect
    provenance["superseded_by"] = defect["superseded_by"]
    write_json(provenance_path, provenance)
    mechanical_path = EXP / "mechanical_qa.json"
    if mechanical_path.is_file():
        mechanical = read_json(mechanical_path)
        mechanical["status"] = "FAIL"
        mechanical["artifact_status"] = "ARTIFACT_INVALID"
        mechanical["supersession_defect"] = defect
        write_json(mechanical_path, mechanical)
    visualization_path = EXP / "visualization_qa.json"
    if visualization_path.is_file():
        visualization = read_json(visualization_path)
        visualization["status"] = "SUPERSEDED_ARTIFACT_INVALID"
        visualization["supersession_defect"] = defect
        write_json(visualization_path, visualization)
    visualization_manifest_path = EXP / "visualization_manifest.json"
    if visualization_manifest_path.is_file():
        visualization_manifest = read_json(visualization_manifest_path)
        visualization_manifest["status"] = "SUPERSEDED_ARTIFACT_INVALID"
        visualization_manifest["supersession_defect"] = defect
        write_json(visualization_manifest_path, visualization_manifest)
    package_qa_path = EXP / "PACKAGE_QA.json"
    if package_qa_path.is_file():
        package_qa = read_json(package_qa_path)
        package_qa["status"] = "SUPERSEDED_ARTIFACT_INVALID"
        package_qa["supersession_defect"] = defect
        package_qa["scientific_use"] = False
        write_json(package_qa_path, package_qa)
    (EXP / "RESULT.md").write_text("\n".join([
        "# BVM -> QB -> T1 interface topology v1 — superseded",
        "",
        "`ARTIFACT_INVALID / SUPERSEDED`",
        "",
        "The immutable raw/deck/log/plot history is retained, but JoSIM logs repeatedly reported `Missing model: JJMIT` and `Using default model` for top-level BVM/JSL/T1 junctions. The exact QB-local model was not global scope, so these raw files are not valid evidence for this experiment.",
        "",
        "The corrected same-matrix experiment is [bvm-qb-t1-interface-topology-v1-20260914-v2](../bvm-qb-t1-interface-topology-v1-20260914-v2/). No v1 raw file was overwritten or rerun.",
        "",
        "Scientific interpretation: `NOT_PERFORMED`; physical verdict: `NOT_ASSIGNED`.",
        "",
    ]), encoding="utf-8")
    print(json.dumps({"status": "ARTIFACT_INVALID_SUPERSEDED", "superseded_by": defect["superseded_by"], "raw_preserved": True}, ensure_ascii=False, indent=2))


def package() -> dict[str, Any]:
    mechanical = read_json(EXP / "mechanical_qa.json")
    visualization = read_json(EXP / "visualization_qa.json")
    if mechanical.get("status") != "PASS" or visualization.get("status") != "PASS":
        raise RuntimeError("package requires passing mechanical and visualization QA")
    if PACKAGE.exists():
        raise RuntimeError(f"refusing to overwrite existing package: {PACKAGE}")
    root_files = ("PREFLIGHT.md", "experiment.yaml", "RESULT.md", "result.json", "provenance.json", "SOURCE_MANIFEST.json", "mechanical_qa.json", "visualization_manifest.json", "visualization_qa.json", "stage_a_sanity.json", "run_state.json")
    files = [EXP / name for name in root_files if (EXP / name).is_file()]
    files += [path for path in sorted((EXP / "runs").rglob("*")) if path.is_file()]
    forbidden = {"screening", "references", "handoff", "analysis", "visualization"}
    if any(any(part in forbidden for part in path.relative_to(EXP).parts) for path in files):
        raise RuntimeError("package would include a forbidden historical/auxiliary directory")
    records = [{"path": path.relative_to(EXP).as_posix(), "sha256": sha256(path), "bytes": path.stat().st_size} for path in files]
    with zipfile.ZipFile(PACKAGE, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in files:
            archive.write(path, path.relative_to(EXP).as_posix())
    with zipfile.ZipFile(PACKAGE, "r") as archive:
        names = sorted(archive.namelist())
        reopened = {name: hashlib.sha256(archive.read(name)).hexdigest() for name in names}
    expected = {item["path"]: item["sha256"] for item in records}
    qa = {
        "schema": "bvm-qb-t1-package-qa-v1",
        "experiment_id": EXP.name,
        "generated_at": now(),
        "package_path": str(PACKAGE),
        "package_sha256": sha256(PACKAGE),
        "package_bytes": PACKAGE.stat().st_size,
        "git_head_at_packaging": git_head(),
        "remote_bvm_master_at_packaging": remote_head(),
        "authorized_physical_solve_count": 15,
        "actual_physical_solve_count": read_json(EXP / "run_state.json").get("actual_physical_solve_count"),
        "file_count": len(records),
        "zip_contents_only_current_experiment": True,
        "contains_old_raw_or_reference_copy": False,
        "expected_file_hashes_match_after_reopen": expected == reopened,
        "files": records,
        "status": "PASS" if expected == reopened else "FAIL",
    }
    write_json(PACKAGE_QA, qa)
    print(json.dumps({"status": qa["status"], "package": str(PACKAGE), "sha256": qa["package_sha256"], "bytes": qa["package_bytes"], "files": len(records)}, ensure_ascii=False, indent=2))
    if qa["status"] != "PASS":
        raise RuntimeError("package QA failed")
    return qa


def mirror() -> None:
    if not PACKAGE.is_file() or not PACKAGE_QA.is_file():
        raise RuntimeError("build package and PACKAGE_QA before mirror")
    candidates = (Path("/mnt/d/BVM_Backages"),)
    destination_root = next((path for path in candidates if path.is_dir() and os.access(path, os.W_OK)), None)
    if destination_root is None:
        receipt = {"schema": "bvm-qb-t1-mirror-receipt-v1", "status": "ANALYSIS_MIRROR_PENDING", "package_sha256": sha256(PACKAGE), "package_bytes": PACKAGE.stat().st_size, "checked_paths": [str(path) for path in candidates], "generated_at": now()}
        write_json(MIRROR_RECEIPT, receipt)
        print(json.dumps(receipt, ensure_ascii=False, indent=2))
        return
    destination = destination_root / PACKAGE.name
    if destination.exists():
        raise RuntimeError(f"refusing to overwrite existing Drive mirror: {destination}")
    shutil.copy2(PACKAGE, destination)
    source_hash = sha256(PACKAGE)
    target_hash = sha256(destination)
    receipt = {"schema": "bvm-qb-t1-mirror-receipt-v1", "status": "PASS" if source_hash == target_hash else "FAIL", "source": str(PACKAGE), "destination": str(destination), "package_sha256": source_hash, "destination_sha256": target_hash, "package_bytes": PACKAGE.stat().st_size, "generated_at": now()}
    write_json(MIRROR_RECEIPT, receipt)
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    if receipt["status"] != "PASS":
        raise RuntimeError("Drive mirror hash mismatch")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "run", "analyze", "qa", "viz", "invalidate", "package", "mirror"))
    args = parser.parse_args()
    if args.command == "prepare":
        prepare()
    elif args.command == "run":
        run_all()
    elif args.command == "analyze":
        analyze()
    elif args.command == "qa":
        mechanical_qa()
    elif args.command == "viz":
        visualize()
    elif args.command == "invalidate":
        invalidate_superseded()
    elif args.command == "package":
        package()
    elif args.command == "mirror":
        mirror()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
