#!/usr/bin/env python3
"""Registered BVM -> QB receiver-boundary R20 shunt experiment.

The runner prepares and executes exactly the two registered candidate solves,
preserves raw artifacts, performs registered arithmetic only, renders
descriptive plots, and packages the evidence. Scientific interpretation is
left to a separately authorized review.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

SCRIPT = Path(__file__).resolve()
REPO = SCRIPT.parents[1]
EXP = REPO / "test" / "exploration" / "bvm-qb-qbin-shunt-r20-v1-20260914"

SOLVER = REPO / "build" / "josim-cli"
PLOTTER = REPO / "scripts" / "josim-plot2.py"
MODEL = REPO / "circuits" / "models" / "jjmit.cir"
QB = REPO / "circuits" / "qb" / "bq_parameterized_v1.cir"
BVM = REPO / "test" / "exploration" / "bvm-population-scaling-rj2p12-l1p14-l2p20-ib260-rj32-bjs400-v1-20260910" / "inputs" / "bvm_jm2_connected.cir"
JTL = REPO / "test" / "exploration" / "bvm-population-scaling-rj2p12-l1p14-l2p20-ib260-rj32-bjs400-v1-20260910" / "inputs" / "jtl2.cir"

BASELINE_ROOT = REPO / "test" / "exploration" / "bvm-full-closed-loop-qb-parameter-screening-v1-20260911" / "references" / "baseline_rj2p12"
PASSIVE_ROOT = REPO / "test" / "exploration" / "bvm-population-passive-source-replay-rj2p12-l1p14-l2p20-ib260-rj32-bjs400-v1-20260911" / "runs"

MASKS = ("0011", "0111")
WINDOWS_PS = (
    (101.0, 110.0),
    (110.0, 113.0),
    (113.0, 117.0),
    (117.0, 121.0),
    (121.0, 130.0),
    (130.0, 160.0),
    (160.0, 200.0),
)
KCL_TOLERANCE_A = 1.0e-9
PHI0 = 2.067833848e-15
CONTRACT_SENTENCE = "This experiment is governed by docs/EXPERIMENT_CONTRACT.md."
FINAL_MARKER = "EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW"
PACKAGE = EXP / f"{EXP.name}_raw_evidence.zip"
PACKAGE_QA = EXP / "PACKAGE_QA.json"

EXPECTED_SOURCE_SHA256 = {
    MODEL: "19862d1fd1f1f44dfa1523848d7d3b5e2594a6c5da8fdd80144b449e5312a336",
    QB: "f676ba1ecb9b2607631a5cfc2f99b7d67e09b9e821457015fba375b8a39f13b0",
    BVM: "0093a45cc3910448b484d8bd004c6df8c22358bacc8b3ed5e23912dcab805d54",
    JTL: "ffd31f8eda2a86ca0133342be1ce678831b7237a53911eda046d2bff8454855a",
    SOLVER: "48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2",
}
EXPECTED_BASELINE_RAW_SHA256 = {
    "0011": "3da7b754c990316ff8e5981692afa958d8056a61020a1912548bf6f2b7e0249c",
    "0111": "1ca15a938b23d4ed08eb964713f91476256c4caf0677d1bfd3dc43020271ec75",
}
EXPECTED_PASSIVE_RAW_SHA256 = {
    "0011": "90fd0c3ebeb8f03f2a941bf6bfd576b6af50c14c732df4a098274ddbdc9f7123",
    "0111": "55589ac102aba281f5c61f99d587a07c50f5d058308f956d0b52c9c5d9666dbc",
}


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


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


def git_status() -> str:
    return subprocess.check_output(["git", "status", "--short", "--untracked-files=all"], cwd=REPO, text=True).strip()


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
        raise RuntimeError(f"missing solver: {SOLVER}")
    version = subprocess.check_output([str(SOLVER), "--version"], cwd=REPO, text=True).strip()
    return {"path": rel(SOLVER), "sha256": sha256(SOLVER), "version": version}


def source_record(name: str, path: Path, role: str) -> dict[str, Any]:
    if not path.is_file():
        raise RuntimeError(f"missing source: {path}")
    return {
        "name": name,
        "path": rel(path),
        "sha256": sha256(path),
        "bytes": path.stat().st_size,
        "role": role,
    }


def candidate_sources() -> list[dict[str, Any]]:
    return [
        source_record("global_jjmit_model", MODEL, "global BVM/JSL model closure; required before subcircuits"),
        source_record("canonical_qb", QB, "canonical QB source; no candidate parameter override"),
        source_record("bvm_jm2_connected", BVM, "latest 4x1 historical JM2-connected BVM source"),
        source_record("jtl2_source", JTL, "latest standard JTL source instantiated six times"),
        source_record("josim_solver", SOLVER, "recorded physical solver"),
        source_record("plotter", PLOTTER, "standard descriptive renderer"),
    ]


def reference_sources() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for mask in MASKS:
        baseline_dir = BASELINE_ROOT / f"ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_{mask}"
        records.append(source_record(f"baseline_{mask}_raw", baseline_dir / "raw.csv", "read-only baseline raw; not copied"))
        records.append(source_record(f"baseline_{mask}_deck", baseline_dir / "deck.cir", "read-only baseline deck provenance; not copied"))
        passive_name = f"PASSIVE_N2_{mask}" if mask == "0011" else f"PASSIVE_N3_{mask}"
        records.append(source_record(f"passive_{mask}_raw", PASSIVE_ROOT / passive_name / "raw.csv", "read-only passive counterfactual; not copied"))
    return records


def assert_sources() -> None:
    for path, expected in EXPECTED_SOURCE_SHA256.items():
        if not path.is_file() or sha256(path) != expected:
            raise RuntimeError(f"registered source changed or is missing: {path}")
    if remote_head() != git_head():
        raise RuntimeError("bvm/master is not equal to current HEAD; refresh repository before preflight")
    for mask in MASKS:
        baseline = BASELINE_ROOT / f"ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_{mask}" / "raw.csv"
        if sha256(baseline) != EXPECTED_BASELINE_RAW_SHA256[mask]:
            raise RuntimeError(f"baseline raw hash changed: {baseline}")
        passive_name = f"PASSIVE_N2_{mask}" if mask == "0011" else f"PASSIVE_N3_{mask}"
        passive = PASSIVE_ROOT / passive_name / "raw.csv"
        if sha256(passive) != EXPECTED_PASSIVE_RAW_SHA256[mask]:
            raise RuntimeError(f"passive reference hash changed: {passive}")


def include_path(path: Path, deck_dir: Path) -> str:
    return Path(os.path.relpath(path, deck_dir)).as_posix()


def pwl(points: Iterable[tuple[float, float]]) -> str:
    tokens: list[str] = []
    for time_ps, current_uA in points:
        value = f"{current_uA:+g}u" if current_uA else "0"
        tokens.extend((f"{time_ps:g}p", value))
    return "pwl(" + " ".join(tokens) + ")"


def stimulus(mask: str, index: int, kind: str) -> list[tuple[float, float]]:
    active = mask[index - 1] == "1"
    if kind == "WL":
        final = 100.0 if active else 0.0
        return [
            (0, 0), (50, 0), (51, -100), (60, -100), (61, 0),
            (70, 0), (71, 100), (80, 100), (81, 0),
            (90, 0), (91, 100), (100, 100), (101, 0),
            (110, 0), (111, final), (120, final), (121, 0), (200, 0),
        ]
    if kind == "BL":
        return [
            (0, 0), (50, 0), (51, -100), (60, -100), (61, 0),
            (70, 0), (81, 0), (90, 0), (91, 100), (100, 100), (101, 0),
            (110, 0), (121, 0), (200, 0),
        ]
    if kind == "SE":
        final = 100.0 if active else 0.0
        return [
            (0, 0), (70, 0), (81, 0), (90, 0), (101, 0), (110, 0),
            (111, final), (120, final), (121, 0), (200, 0),
        ]
    raise ValueError(kind)


def probe_lines() -> list[str]:
    lines: list[str] = []
    for index in range(1, 5):
        lines.append(f".print I(I_WL{index}) I(I_BL{index}) I(I_SE{index})")
        for element in ("B_JM1", "B_JM2", "B_JS1", "B_JS2"):
            lines.append(f".print P({element}|XBVM{index}) V({element}|XBVM{index}) I({element}|XBVM{index})")
        for element in ("L_M1", "L_M2", "L_M3", "L_S1", "L_S2", "L_S3", "L_PSL", "L_SL"):
            lines.append(f".print I({element}|XBVM{index}) V({element}|XBVM{index})")
    lines.append(".print V(COMMON_SL)")
    for index in range(1, 9):
        lines.append(f".print P(B_JSL{index}) V(B_JSL{index}) I(B_JSL{index})")
    lines += [
        ".print V(QBIN)",
        ".print I(R_QBIN_SHUNT) V(R_QBIN_SHUNT)",
        ".print I(LIN|XBQ) V(LIN|XBQ)",
        ".print I(L1|XBQ) V(L1|XBQ)",
        ".print I(L2|XBQ) V(L2|XBQ)",
        ".print I(L3|XBQ) V(L3|XBQ)",
        ".print I(RJ1|XBQ) V(RJ1|XBQ)",
        ".print I(RJ2|XBQ) V(RJ2|XBQ)",
        ".print P(BJS|XBQ) V(BJS|XBQ) I(BJS|XBQ)",
        ".print P(BJ1|XBQ) V(BJ1|XBQ) I(BJ1|XBQ)",
        ".print P(BJ2|XBQ) V(BJ2|XBQ) I(BJ2|XBQ)",
        ".print V(QBOUT)",
    ]
    for index in range(1, 7):
        instance = f"XJTL1_{index}"
        lines.append(
            f".print P(B01|{instance}) V(B01|{instance}) I(B01|{instance}) "
            f"P(B02|{instance}) V(B02|{instance}) I(B02|{instance})"
        )
        lines.append(f".print V(JTL{index}_OUT)")
    lines += [".print I(R_TERM)"]
    return lines


def deck_text(mask: str, deck_dir: Path) -> str:
    lines = [
        f"* REGISTERED BVM -> COMMON_SL/JSL -> canonical QB -> six-stage JTL; mask={mask}",
        "* This candidate changes exactly one component relative to the baseline: R_QBIN_SHUNT QBIN 0 20.",
        "* P(...) is raw phase in radians; plots use -j 2pi only as a display conversion.",
        f".include {include_path(MODEL, deck_dir)}",
        f".include {include_path(QB, deck_dir)}",
        f".include {include_path(BVM, deck_dir)}",
        f".include {include_path(JTL, deck_dir)}",
        "",
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
        "* Registered receiver-boundary intervention; positive current QBIN -> ground.",
        "R_QBIN_SHUNT QBIN 0 20",
        "",
        "XBQ QBIN QBOUT BQ",
        "XJTL1_1 QBOUT JTL1_OUT jtl",
        "XJTL1_2 JTL1_OUT JTL2_OUT jtl",
        "XJTL1_3 JTL2_OUT JTL3_OUT jtl",
        "XJTL1_4 JTL3_OUT JTL4_OUT jtl",
        "XJTL1_5 JTL4_OUT JTL5_OUT jtl",
        "XJTL1_6 JTL5_OUT JTL6_OUT jtl",
        "R_TERM JTL6_OUT 0 10",
        "",
    ]
    for index in range(1, 5):
        for kind in ("WL", "BL", "SE"):
            lines.append(f"I_{kind}{index} 0 {kind}{index} {pwl(stimulus(mask, index, kind))}")
    lines += ["", ".tran 0.1p 200p", ""]
    lines += probe_lines()
    lines += [".end", ""]
    return "\n".join(lines)


def run_id(mask: str) -> str:
    return f"R20_{mask}"


def run_dir(mask: str) -> Path:
    return EXP / "runs" / mask


def raw_path(mask: str) -> Path:
    return run_dir(mask) / "raw.csv"


def expected_headers() -> set[str]:
    required: set[str] = set()
    for index in range(1, 5):
        required.update(f"I(I_{kind}{index})" for kind in ("WL", "BL", "SE"))
        for element in ("B_JM1", "B_JM2", "B_JS1", "B_JS2"):
            required.update(f"{kind}({element}|XBVM{index})" for kind in ("P", "V", "I"))
        for element in ("L_M1", "L_M2", "L_M3", "L_S1", "L_S2", "L_S3", "L_PSL", "L_SL"):
            required.update(f"{kind}({element}|XBVM{index})" for kind in ("I", "V"))
    required.add("V(COMMON_SL)")
    for index in range(1, 9):
        required.update(f"{kind}(B_JSL{index})" for kind in ("P", "V", "I"))
    required.update({"V(QBIN)", "I(R_QBIN_SHUNT)", "V(R_QBIN_SHUNT)", "V(QBOUT)"})
    for element in ("LIN", "L1", "L2", "L3", "RJ1", "RJ2"):
        required.update(f"{kind}({element}|XBQ)" for kind in ("I", "V"))
    for element in ("BJS", "BJ1", "BJ2"):
        required.update(f"{kind}({element}|XBQ)" for kind in ("P", "V", "I"))
    for index in range(1, 7):
        instance = f"XJTL1_{index}"
        for element in ("B01", "B02"):
            required.update(f"{kind}({element}|{instance})" for kind in ("P", "V", "I"))
        required.add(f"V(JTL{index}_OUT)")
    required.update({"V(JTL6_OUT)", "I(R_TERM)"})
    return required


def yaml_quote(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def experiment_yaml(sources: list[dict[str, Any]], references: list[dict[str, Any]]) -> str:
    source_lines = "\n".join(
        f"  - name: {item['name']}\n"
        f"    path: {yaml_quote(item['path'])}\n"
        f"    sha256: {item['sha256']}\n"
        f"    bytes: {item['bytes']}\n"
        f"    role: {yaml_quote(item['role'])}"
        for item in sources
    )
    reference_lines = "\n".join(
        f"  - name: {item['name']}\n"
        f"    path: {yaml_quote(item['path'])}\n"
        f"    sha256: {item['sha256']}\n"
        f"    bytes: {item['bytes']}\n"
        f"    role: {yaml_quote(item['role'])}"
        for item in references
    )
    return f"""schema_version: bvm-qb-qbin-shunt-r20-v1
id: {EXP.name}
study_phase: EXPLORATORY
role: Experimental Operator + Evidence Packager
status: PREFLIGHT_PASS
scientific_review_authorized: false
scientific_interpretation_performed: false

question:
  primary: {yaml_quote("Under the frozen 4x1 BVM -> COMMON_SL -> 8JSL -> canonical QB -> six-stage JTL closure, does only adding R_QBIN_SHUNT QBIN 0 20 change the registered N2/N3 receiver-boundary waveforms?")}
  scope: {yaml_quote("This is a two-case receiver-boundary intervention, not a parameter sweep, QB tuning study, or Gate.")}
  interpretation_ceiling: {yaml_quote("Record raw observations and registered arithmetic only. Do not assign mechanism, functional success, overdamping, no-effect, pathology, SFQ count, or system Gate without SCIENTIFIC_REVIEW_AUTHORIZED.")}

changed:
  exact_component: R_QBIN_SHUNT QBIN 0 20
  perturbation: {yaml_quote("One 20 ohm shunt from QBIN to ground; no BVM/JSL/QB/JTL/model/stimulus/bias/timing changes.")}
  candidate_instance_name: XBQ

frozen:
  topology: {yaml_quote("Four historical JM2-connected BVMs -> COMMON_SL -> eight JSL junctions -> canonical QB -> six existing JTL stages -> 10 ohm terminal load")}
  canonical_qb_parameters: {{Lin_pH: 1.5, L1_pH: 1.4, L2_pH: 2.0, RJ1_ohm: 32.0, RJ2_ohm: 12.0, IB_uA: 260.0, BJS_area: 4.0, BJ1_area: 0.9, BJ2_area: 2.0, L3_pH: 1.3}}
  jsl_area: 5.0
  stimulus: {yaml_quote("IDLE 0-50; WRITE0 50-61; zero-state read control 70-81; WRITE1 90-101; SETTLE 101-110; mask-selective final read 110-121; TAIL 121-200 ps")}
  stimulus_amplitude_uA: 100.0
  rise_fall_ps: 1.0
  plateau_ps: 9.0
  bit_order: b3b2b1b0 = BVM1/BVM2/BVM3/BVM4
  tran: .tran 0.1p 200p
  stored_grid_expected: 0 to 199.9 ps at nominal 0.1 ps spacing
  terminal_load_ohm: 10.0

authorized_runs:
  masks: ["0011", "0111"]
  active_cells: {{"0011": [BVM3, BVM4], "0111": [BVM2, BVM3, BVM4]}}
  physical_solve_count: 2
  no_other_masks: true
  no_retry_or_followup: true

sources:
{source_lines}
read_only_references:
{reference_lines}
baseline_policy: {yaml_quote("Baseline raw is referenced by path and SHA-256 only; it is not copied into this experiment. Baseline deck uses a derived BQ include but has the same registered physical values.")}

probes:
  bvm: {yaml_quote("Every BVM B_JM1/B_JM2/B_JS1/B_JS2 P/V/I; L_M1/L_M2/L_M3/L_S1/L_S2/L_S3/L_PSL/L_SL I/V; I(I_WLn), I(I_BLn), I(I_SEn).")}
  shared_boundary: {yaml_quote("V(COMMON_SL); P/V/I B_JSL1..8; V(QBIN); I(B_JSL8); I(R_QBIN_SHUNT); I(LIN|XBQ).")}
  qb: {yaml_quote("P/V/I BJS/BJ1/BJ2; I/V LIN/L1/L2/L3; I/V RJ1/RJ2; V(QBOUT). Canonical internal IB source is fixed in the included QB; JoSIM does not expose a reliable hierarchical I(IB) column, so no value is fabricated.")}
  jtl: {yaml_quote("P/V/I B01/B02 for every XJTL1_1..XJTL1_6; V(JTL1_OUT)..V(JTL6_OUT); I(R_TERM).")}
  direction_convention: {yaml_quote("B_JSL8: JSL_NODE7 -> QBIN; R_QBIN_SHUNT: QBIN -> ground; LIN|XBQ: QBIN -> BQ internal node 1. KCL residual = I(B_JSL8) - I(R_QBIN_SHUNT) - I(LIN|XBQ).")}

registered_windows_ps:
  - [101, 110]
  - [110, 113]
  - [113, 117]
  - [117, 121]
  - [121, 130]
  - [130, 160]
  - [160, 200]
window_semantics: half-open; actual stored timestamps; no interpolation or resampling
registered_arithmetic:
  kcl_tolerance_A: {KCL_TOLERANCE_A}
  phase_conversion: raw_phase_rad / (2*pi), after independent continuous unwrap; navigation only
  voltage_area: actual-grid trapezoid on the same signal, endpoints, direction and registered window
  comparison: exact same-time pointwise deltas only if candidate and reference grids match

visualization:
  renderer: scripts/josim-plot2.py
  layout: sep_comb
  color: dark
  phase_option: 2pi
  whole_run_window_ps: [0, 200]
  standalone_pages: [01_bvm_phase.html, 02_bvm_currents.html, 03_common_jsl.html, 04_qbin_boundary.html, 05_qb.html, 06_jtl.html, 07_terminal.html]
  focused_pages: none (explicitly not generated)
  comparison_pages: [comparison_A_0011.html, comparison_B_0111.html, comparison_C_n2_n3.html, comparison_D_passive_reference.html]

references:
  passive_reference: {yaml_quote("Counterfactual BVM/JSL-to-ground runs; descriptive reference only and not topology-equivalent to candidate/baseline.")}
  no_raw_copy: true

stop:
  final_state: {FINAL_MARKER}
  scientific_interpretation: NOT_PERFORMED
  automatic_followup: false
"""


def preflight_text(sources: list[dict[str, Any]], references: list[dict[str, Any]], decks: dict[str, dict[str, Any]]) -> str:
    source_lines = "\n".join(
        f"- {item['name']}: {item['path']}; SHA-256 {item['sha256']}; {item['role']}."
        for item in sources
    )
    reference_lines = "\n".join(
        f"- {item['name']}: {item['path']}; SHA-256 {item['sha256']}; {item['role']}."
        for item in references
    )
    deck_lines = "\n".join(
        f"- {mask}: {record['path']}; SHA-256 {record['sha256']}; {record['bytes']} bytes."
        for mask, record in decks.items()
    )
    return f"""# BVM -> QB receiver-boundary R20 shunt — PREFLIGHT

{CONTRACT_SENTENCE}

- Experiment: {EXP.name}
- Generated at: {now()}
- Registration HEAD: {git_head()}
- Remote bvm/master at registration: {remote_head()}
- Worktree status at registration is recorded in provenance.json; no tracked source is changed by this experiment.
- Preflight status: PASS; no solver has been invoked.
- Solver: {solver_context()['version']}; SHA-256 {sha256(SOLVER)}.

## Scientific scope

This is an EXPLORATORY two-case receiver-boundary intervention. The only
candidate change is the top-level resistor R_QBIN_SHUNT QBIN 0 20. No QB
parameter, BVM/JSL source, JTL source, model, bias, stimulus, timing, terminal
load, or read mask outside 0011 and 0111 is authorized. The experiment has
no SCIENTIFIC_REVIEW_AUTHORIZED token; execution produces evidence and
registered arithmetic, not a physical verdict.

## Candidate source closure

{source_lines}

The global jjmit model is included before BVM/JSL devices. The QB source is
the exact canonical circuits/qb/bq_parameterized_v1.cir text. The QB internal
IB source is fixed by that source; JoSIM's hierarchical I(IB|XBQ) probe is
not reliable and is intentionally not fabricated.

## Read-only baseline and passive references

{reference_lines}

Baseline raw files are not copied or modified. Baseline decks are provenance
only; their derived BQ include is semantically parameter-equivalent to the
canonical QB values used by the candidate. Passive references are a
counterfactual BVM/JSL topology and are not a matched full-closure baseline.

## Exact topology, protocol and parameters

- Topology: four historical JM2-connected BVMs -> COMMON_SL -> B_JSL1..8 -> QBIN -> canonical QB -> six existing JTL stages -> R_TERM=10 ohm.
- Candidate intervention: exactly one line, R_QBIN_SHUNT QBIN 0 20 (positive current QBIN -> 0).
- QB parameters: Lin=1.5pH, L1=1.4pH, L2=2.0pH, RJ1=32ohm, RJ2=12ohm, IB=260uA, BJS area=4, BJ1 area=0.9, BJ2 area=2, L3=1.3pH.
- JSL junction area: 5.0; terminal load: 10ohm.
- History: IDLE 0-50; WRITE0 50-61; IDLE 61-70; zero-state read control 70-81; IDLE 81-90; WRITE1 90-101; settle 101-110; final read 110-121; tail 121-200 ps.
- Stimulus: 100uA, 1 ps rise/fall, 9 ps plateau; bit order b3b2b1b0=BVM1/BVM2/BVM3/BVM4.
- Timing: .tran 0.1p 200p; expected stored time range 0..199.9 ps.

Registered decks:

{deck_lines}

## Exact solve matrix

- Physical solves: exactly 0011, then 0111.
- Maximum/authorized solve count: 2.
- No automatic sweep, retry, parameter change, timing change, mask change or follow-up solve.
- A solver/tool failure is preserved in its run log and stops the matrix.

## Probes and arithmetic

- Every BVM has P/V/I for B_JM1, B_JM2, B_JS1, B_JS2; I/V for L_M1, L_M2, L_M3, L_S1, L_S2, L_S3, L_PSL, L_SL; and local source currents I(I_WLn), I(I_BLn), I(I_SEn).
- Shared boundary has V(COMMON_SL), P/V/I for every JSL JJ, V(QBIN), I(B_JSL8), I(R_QBIN_SHUNT), and I(LIN|XBQ).
- QB has P/V/I for BJS, BJ1, BJ2; I/V for LIN, L1, L2, L3; I/V for RJ1, RJ2; and V(QBOUT).
- Every JTL stage has P/V/I for B01 and B02, stage output voltage, and final I(R_TERM).
- Boundary directions: I(B_JSL8) is JSL_NODE7 -> QBIN; I(R_QBIN_SHUNT) is QBIN -> 0; I(LIN|XBQ) is QBIN -> BQ internal node 1. Registered residual: I(B_JSL8) - I(R_QBIN_SHUNT) - I(LIN|XBQ).
- Windows are half-open [start,end) ps and use actual stored timestamps. Phase is raw radians; turns are only unwrap(rad)/(2*pi) for navigation. Voltage-area arithmetic uses actual-grid trapezoids and is not an event count.

## Visualization and interpretation ceiling

- Each run receives seven standalone full-window HTML pages: 01_bvm_phase, 02_bvm_currents, 03_common_jsl, 04_qbin_boundary, 05_qb, 06_jtl, 07_terminal.
- Four full-window comparison HTML pages are generated after standalone QA. No focused/cropped HTML, PNG, PDF, derived plot CSV, or giant dashboard is generated.
- 04_qbin_boundary explicitly includes V(COMMON_SL), V(QBIN), I(B_JSL8), I(R_QBIN_SHUNT), and I(LIN|XBQ) with direction notes.
- Scientific labels such as mechanism support, functional success, overdamping, no effect, pathology, SFQ count, and Gate status remain unassigned.

After mechanical QA, visualization QA, package QA and commit, stop at
{FINAL_MARKER}. No raw is overwritten, silently corrected, or deleted.
"""


def prepare() -> None:
    if EXP.exists():
        existing_physical = [
            path
            for path in EXP.rglob("*")
            if path.is_file() and path.name in {"raw.csv", "run.log"}
        ]
        if existing_physical:
            raise RuntimeError(
                f"physical artifacts already exist; refusing to overwrite: {existing_physical}"
            )
    assert_sources()
    EXP.mkdir(parents=True, exist_ok=True)
    sources = candidate_sources()
    references = reference_sources()
    decks: dict[str, dict[str, Any]] = {}
    for mask in MASKS:
        directory = run_dir(mask)
        directory.mkdir(parents=True, exist_ok=True)
        deck = directory / "deck.cir"
        deck.write_text(deck_text(mask, directory), encoding="utf-8")
        decks[mask] = {"path": rel(deck), "sha256": sha256(deck), "bytes": deck.stat().st_size}
    write_json(EXP / "SOURCE_MANIFEST.json", {
        "schema": "bvm-qb-qbin-shunt-r20-source-manifest-v1",
        "experiment_id": EXP.name,
        "created_at": now(),
        "registration_head": git_head(),
        "remote_bvm_master": remote_head(),
        "sources": sources,
        "read_only_references": references,
        "no_raw_copy": True,
    })
    provenance = {
        "schema": "bvm-qb-qbin-shunt-r20-provenance-v1",
        "experiment_id": EXP.name,
        "created_at": now(),
        "registration_head": git_head(),
        "remote_bvm_master": remote_head(),
        "worktree_status_at_registration": git_status(),
        "solver": solver_context(),
        "sources": sources,
        "read_only_references": references,
        "registered_decks": decks,
        "intervention": {
            "line": "R_QBIN_SHUNT QBIN 0 20",
            "resistance_ohm": 20.0,
            "from": "QBIN",
            "to": "0",
            "only_physical_difference": True,
        },
        "baseline_policy": {
            "raw_copied": False,
            "baseline_root": rel(BASELINE_ROOT),
            "baseline_deck_source_difference": "baseline uses derived BQ include text; candidate uses canonical QB source with identical frozen physical values",
        },
        "direction_convention": {
            "I(B_JSL8)": "JSL_NODE7 -> QBIN",
            "I(R_QBIN_SHUNT)": "QBIN -> 0",
            "I(LIN|XBQ)": "QBIN -> BQ internal node 1",
            "kcl_residual": "I(B_JSL8) - I(R_QBIN_SHUNT) - I(LIN|XBQ)",
        },
        "transformations": [
            {"name": "continuous_phase_unwrap", "scope": "analysis/display only", "formula": "unwrap(raw_phase_rad)", "raw_mutated": False},
            {"name": "phase_turn_display", "scope": "analysis/display only", "formula": "unwrap(raw_phase_rad)/(2*pi)", "raw_mutated": False, "not_an_sfq_count": True},
            {"name": "actual_grid_trapezoid", "scope": "registered arithmetic", "interpolation": False, "raw_mutated": False},
            {"name": "temporary_comparison_csv", "scope": "renderer input only", "raw_mutated": False, "deleted_after_render": True},
        ],
        "runs": {},
        "raw_hash_before_analysis": {},
        "raw_hash_after_analysis": {},
        "scientific_analysis_performed": False,
    }
    write_json(EXP / "provenance.json", provenance)
    write_json(EXP / "run_state.json", {
        "schema": "bvm-qb-qbin-shunt-r20-state-v1",
        "experiment_id": EXP.name,
        "created_at": now(),
        "updated_at": now(),
        "status": "PREFLIGHT_PASS",
        "run_order": [],
        "authorized_physical_solve_count": 2,
        "actual_physical_solve_count": 0,
        "final_marker": None,
    })
    (EXP / "experiment.yaml").write_text(experiment_yaml(sources, references), encoding="utf-8")
    (EXP / "PREFLIGHT.md").write_text(preflight_text(sources, references, decks), encoding="utf-8")
    print(json.dumps({
        "status": "PREFLIGHT_PASS",
        "experiment": EXP.name,
        "head": git_head(),
        "remote": remote_head(),
        "authorized_runs": list(MASKS),
        "physical_solve_count": 2,
    }, ensure_ascii=False, indent=2))


def load_raw(path: Path) -> Any:
    # Use the repository's duplicate-aware raw reader; do not copy a parser
    # into the experiment directory.
    sys.path.insert(0, str(SCRIPT.parent))
    from bvmtools.raw import read_csv

    return read_csv(path)


def window_indices_ps(times: Iterable[float], start_ps: float, end_ps: float) -> list[int]:
    return [
        index
        for index, value in enumerate(times)
        if start_ps * 1.0e-12 <= value < end_ps * 1.0e-12
    ]


def raw_stats(
    times: tuple[float, ...] | list[float],
    values: Iterable[float],
    start_ps: float,
    end_ps: float,
    unit: str,
) -> dict[str, Any]:
    values_list = [float(value) for value in values]
    ids = window_indices_ps(times, start_ps, end_ps)
    if len(ids) < 2:
        return {
            "status": "UNKNOWN",
            "reason": "fewer than two actual stored samples",
            "window_ps": [start_ps, end_ps],
            "unit": unit,
        }
    selected_times = [float(times[index]) for index in ids]
    selected = [values_list[index] for index in ids]
    area = sum(
        0.5
        * (selected[index] + selected[index + 1])
        * (selected_times[index + 1] - selected_times[index])
        for index in range(len(selected) - 1)
    )
    max_index = max(range(len(selected)), key=lambda index: selected[index])
    min_index = min(range(len(selected)), key=lambda index: selected[index])
    peak_index = max(range(len(selected)), key=lambda index: abs(selected[index]))
    result: dict[str, Any] = {
        "status": "DERIVED",
        "window_ps": [start_ps, end_ps],
        "sample_count": len(selected),
        "unit": unit,
        "first": selected[0],
        "last": selected[-1],
        "minimum": selected[min_index],
        "maximum": selected[max_index],
        "range": selected[max_index] - selected[min_index],
        "peak_abs": abs(selected[peak_index]),
        "time_of_peak_abs_ps": selected_times[peak_index] * 1.0e12,
        "signed_time_integral": area,
        "actual_grid_first_ps": selected_times[0] * 1.0e12,
        "actual_grid_last_ps": selected_times[-1] * 1.0e12,
    }
    if unit == "A":
        result.update(
            {
                "display_unit": "uA",
                "display_first_uA": selected[0] * 1.0e6,
                "display_last_uA": selected[-1] * 1.0e6,
                "display_minimum_uA": selected[min_index] * 1.0e6,
                "display_maximum_uA": selected[max_index] * 1.0e6,
                "display_peak_abs_uA": abs(selected[peak_index]) * 1.0e6,
                "signed_integral_uA_ps": area * 1.0e18,
            }
        )
    elif unit == "V":
        result.update(
            {
                "display_unit": "mV",
                "display_first_mV": selected[0] * 1.0e3,
                "display_last_mV": selected[-1] * 1.0e3,
                "display_minimum_mV": selected[min_index] * 1.0e3,
                "display_maximum_mV": selected[max_index] * 1.0e3,
                "display_peak_abs_mV": abs(selected[peak_index]) * 1.0e3,
                "signed_integral_mV_ps": area * 1.0e15,
            }
        )
    return result


def phase_stats(trace: Any, signal: str, start_ps: float, end_ps: float) -> dict[str, Any]:
    from bvmtools.phase import continuous_unwrap, phase_window_metrics

    values = trace.column(signal)
    metrics = phase_window_metrics(
        trace.time,
        values,
        (start_ps * 1.0e-12, end_ps * 1.0e-12),
    )
    unwrapped = continuous_unwrap(values)
    ids = window_indices_ps(trace.time, start_ps, end_ps)
    metrics["raw_signal"] = signal
    metrics["window_ps"] = [start_ps, end_ps]
    metrics["raw_endpoint_first_rad"] = values[ids[0]]
    metrics["raw_endpoint_last_rad"] = values[ids[-1]]
    metrics["unwrapped_endpoint_first_rad"] = unwrapped[ids[0]]
    metrics["unwrapped_endpoint_last_rad"] = unwrapped[ids[-1]]
    return metrics


def signal_stats(trace: Any, signal: str, start_ps: float, end_ps: float) -> dict[str, Any]:
    if signal.startswith("P("):
        return phase_stats(trace, signal, start_ps, end_ps)
    return raw_stats(
        trace.time,
        trace.column(signal),
        start_ps,
        end_ps,
        "A" if signal.startswith("I(") else "V",
    ) | {"raw_signal": signal}


def window_metrics(trace: Any, signals: Iterable[str]) -> dict[str, dict[str, dict[str, Any]]]:
    return {
        f"[{start:g},{end:g})ps": {
            signal: signal_stats(trace, signal, start, end)
            for signal in signals
        }
        for start, end in WINDOWS_PS
    }


def kcl_metrics(trace: Any) -> dict[str, Any]:
    inflow = trace.column("I(B_JSL8)")
    shunt = trace.column("I(R_QBIN_SHUNT)")
    lin = trace.column("I(LIN|XBQ)")
    residual = tuple(
        a - b - c for a, b, c in zip(inflow, shunt, lin)
    )
    return {
        "equation": "I(B_JSL8) - I(R_QBIN_SHUNT) - I(LIN|XBQ)",
        "directions": {
            "I(B_JSL8)": "JSL_NODE7 -> QBIN",
            "I(R_QBIN_SHUNT)": "QBIN -> 0",
            "I(LIN|XBQ)": "QBIN -> BQ internal node 1",
        },
        "residual_unit": "A",
        "windows": {
            "[0,200)ps": raw_stats(
                trace.time, residual, 0.0, 200.0, "A"
            )
        },
        "registered_window_residuals": {
            f"[{start:g},{end:g})ps": raw_stats(
                trace.time, residual, start, end, "A"
            )
            for start, end in WINDOWS_PS
        },
    }


def baseline_signal(signal: str) -> str:
    return signal.replace("|XBQ)", "|XBQ1)")


def diff_stats(
    times: tuple[float, ...],
    values: Iterable[float],
    start_ps: float,
    end_ps: float,
    unit: str,
    phase: bool = False,
) -> dict[str, Any]:
    result = raw_stats(times, values, start_ps, end_ps, unit)
    if phase and result.get("status") == "DERIVED":
        for key in ("first", "last", "minimum", "maximum", "range", "peak_abs"):
            result[f"{key}_turns"] = result[key] / (2.0 * math.pi)
        result["phase_difference_convention"] = (
            "independently unwrapped candidate/reference phases, then candidate-reference"
        )
    return result


def compare_traces(
    left: Any,
    right: Any,
    signals: Iterable[str],
    right_name_mapper=lambda signal: signal,
) -> dict[str, Any]:
    same_grid = tuple(left.time) == tuple(right.time)
    output: dict[str, Any] = {
        "same_time_grid": same_grid,
        "left_samples": left.sample_count,
        "right_samples": right.sample_count,
        "signals": {},
    }
    if not same_grid:
        output["status"] = "DESCRIPTIVE_ONLY_TIME_GRID_MISMATCH"
        return output
    from bvmtools.phase import continuous_unwrap

    for signal in signals:
        mapped = right_name_mapper(signal)
        if signal not in left.headers or mapped not in right.headers:
            continue
        left_values = left.column(signal)
        right_values = right.column(mapped)
        if signal.startswith("P("):
            left_values = continuous_unwrap(left_values)
            right_values = continuous_unwrap(right_values)
            unit = "rad"
            is_phase = True
        else:
            unit = "A" if signal.startswith("I(") else "V"
            is_phase = False
        delta = tuple(
            left_value - right_value
            for left_value, right_value in zip(left_values, right_values)
        )
        output["signals"][signal] = {
            f"[{start:g},{end:g})ps": diff_stats(
                left.time, delta, start, end, unit, is_phase
            )
            for start, end in WINDOWS_PS
        }
    output["status"] = (
        "DERIVED_POINTWISE_SAME_TIME"
        if output["signals"]
        else "UNKNOWN_NO_COMMON_SIGNALS"
    )
    return output


def active_cells(mask: str) -> list[int]:
    return [index for index, bit in enumerate(mask, start=1) if bit == "1"]


def symmetry_metrics(trace: Any, mask: str) -> dict[str, Any]:
    indices = active_cells(mask)
    templates = (
        "P(B_JM1|XBVM{index})",
        "P(B_JM2|XBVM{index})",
        "I(L_SL|XBVM{index})",
        "V(B_JM1|XBVM{index})",
        "V(B_JM2|XBVM{index})",
    )
    pairs: dict[str, Any] = {}
    from bvmtools.phase import continuous_unwrap

    for offset, left_index in enumerate(indices):
        for right_index in indices[offset + 1:]:
            pair_name = f"XBVM{left_index}_vs_XBVM{right_index}"
            pair: dict[str, Any] = {}
            for template in templates:
                left_signal = template.format(index=left_index)
                right_signal = template.format(index=right_index)
                phase = left_signal.startswith("P(")
                left_values = trace.column(left_signal)
                right_values = trace.column(right_signal)
                if phase:
                    left_values = continuous_unwrap(left_values)
                    right_values = continuous_unwrap(right_values)
                delta = tuple(
                    left_value - right_value
                    for left_value, right_value in zip(left_values, right_values)
                )
                pair[left_signal] = {
                    "right_signal": right_signal,
                    "tail": diff_stats(
                        trace.time,
                        delta,
                        160.0,
                        200.0,
                        "rad" if phase else (
                            "A" if left_signal.startswith("I(") else "V"
                        ),
                        phase,
                    ),
                }
            pairs[pair_name] = pair
    return {
        "active_cells": [f"XBVM{index}" for index in indices],
        "tail_window_ps": [160.0, 200.0],
        "pairwise_same_time_differences": pairs,
    }


def metric_signal_sets() -> dict[str, tuple[str, ...]]:
    bvm_phase = tuple(
        f"P(B_{element}|XBVM{index})"
        for index in range(1, 5)
        for element in ("JM1", "JM2", "JS1", "JS2")
    )
    bvm_state = tuple(
        f"{kind}({element}|XBVM{index})"
        for index in range(1, 5)
        for element in ("B_JM1", "B_JM2", "B_JS1", "B_JS2")
        for kind in ("P", "V", "I")
    )
    boundary = (
        "V(COMMON_SL)",
        "V(QBIN)",
        "I(B_JSL8)",
        "I(R_QBIN_SHUNT)",
        "V(R_QBIN_SHUNT)",
        "I(LIN|XBQ)",
        "V(LIN|XBQ)",
        "V(QBOUT)",
        "I(R_TERM)",
    )
    qb_all = (
        "I(LIN|XBQ)", "V(LIN|XBQ)",
        "I(L1|XBQ)", "V(L1|XBQ)",
        "I(L2|XBQ)", "V(L2|XBQ)",
        "I(L3|XBQ)", "V(L3|XBQ)",
        "I(RJ1|XBQ)", "V(RJ1|XBQ)",
        "I(RJ2|XBQ)", "V(RJ2|XBQ)",
        "P(BJS|XBQ)", "V(BJS|XBQ)", "I(BJS|XBQ)",
        "P(BJ1|XBQ)", "V(BJ1|XBQ)", "I(BJ1|XBQ)",
        "P(BJ2|XBQ)", "V(BJ2|XBQ)", "I(BJ2|XBQ)",
        "V(QBOUT)",
    )
    jtl = tuple(
        signal
        for index in range(1, 7)
        for signal in (
            f"P(B01|XJTL1_{index})",
            f"V(B01|XJTL1_{index})",
            f"I(B01|XJTL1_{index})",
            f"P(B02|XJTL1_{index})",
            f"V(B02|XJTL1_{index})",
            f"I(B02|XJTL1_{index})",
            f"V(JTL{index}_OUT)",
        )
    )
    compare = (
        "V(COMMON_SL)", "P(B_JSL8)", "I(B_JSL8)", "V(QBIN)",
        "I(LIN|XBQ)", "P(BJS|XBQ)", "P(BJ1|XBQ)", "P(BJ2|XBQ)",
        "V(QBOUT)", "V(JTL1_OUT)", "V(JTL3_OUT)", "V(JTL6_OUT)",
        "I(R_TERM)", "I(L_SL|XBVM1)", "I(L_SL|XBVM2)",
        "I(L_SL|XBVM3)", "I(L_SL|XBVM4)",
    )
    passive_compare = (
        "V(COMMON_SL)", "P(B_JSL8)", "I(B_JSL8)",
        "I(L_SL|XBVM1)", "I(L_SL|XBVM2)",
        "I(L_SL|XBVM3)", "I(L_SL|XBVM4)",
    )
    return {
        "bvm_phase": bvm_phase,
        "bvm_state": bvm_state,
        "boundary": boundary,
        "qb_all": qb_all,
        "jtl": jtl,
        "compare": compare,
        "passive_compare": passive_compare,
    }


def run_metrics(mask: str, trace: Any) -> dict[str, Any]:
    sets = metric_signal_sets()
    registered = {
        "boundary": window_metrics(trace, sets["boundary"]),
        "bvm_state": window_metrics(trace, sets["bvm_state"]),
        "qb": window_metrics(trace, sets["qb_all"]),
        "jtl": window_metrics(trace, sets["jtl"]),
    }
    return {
        "run_id": run_id(mask),
        "mask": mask,
        "active_cells": [f"XBVM{index}" for index in active_cells(mask)],
        "raw_sha256": sha256(raw_path(mask)),
        "raw_qa": trace.qa(),
        "registered_window_arithmetic": registered,
        "boundary_kcl": kcl_metrics(trace),
        "active_cell_symmetry": symmetry_metrics(trace, mask),
    }


def review_questions(metrics: dict[str, Any], comparisons: dict[str, Any]) -> list[dict[str, Any]]:
    by_mask = {item["mask"]: item for item in metrics["runs"]}
    questions: list[dict[str, Any]] = []
    questions.append({
        "id": 1,
        "question": "Does R20 reduce the N3 V(QBIN) high-voltage excursion?",
        "status": "SCIENTIFIC_REVIEW_REQUIRED",
        "registered_data": {
            "candidate_0111": by_mask["0111"]["registered_window_arithmetic"]["boundary"],
            "baseline_0111": comparisons["candidate_vs_baseline"]["0111"]["signals"].get("V(QBIN)"),
        },
    })
    questions.append({
        "id": 2,
        "question": "When does the registered shunt branch current become nonzero or large on the actual grid?",
        "status": "SCIENTIFIC_REVIEW_REQUIRED",
        "registered_data": {
            mask: by_mask[mask]["registered_window_arithmetic"]["boundary"].get("I(R_QBIN_SHUNT)")
            for mask in MASKS
        },
    })
    questions.append({
        "id": 3,
        "question": "Does the QBIN boundary KCL residual satisfy the registered arithmetic check?",
        "status": "SCIENTIFIC_REVIEW_REQUIRED",
        "registered_data": {mask: by_mask[mask]["boundary_kcl"] for mask in MASKS},
    })
    questions.append({
        "id": 4,
        "question": "Are the first and second QB response windows retained in N2?",
        "status": "SCIENTIFIC_REVIEW_REQUIRED",
        "registered_data": {
            "candidate_0011": {
                window: {
                    signal: by_mask["0011"]["registered_window_arithmetic"]["qb"].get(window, {}).get(signal)
                    for signal in ("P(BJS|XBQ)", "P(BJ1|XBQ)", "P(BJ2|XBQ)")
                }
                for window in ("[110,113)ps", "[113,117)ps", "[117,121)ps")
            }
        },
    })
    questions.append({
        "id": 5,
        "question": "Do N3 BVM JS1/JS2 traces move between the registered navigation windows?",
        "status": "SCIENTIFIC_REVIEW_REQUIRED",
        "registered_data": {
            "candidate_0111": {
                window: {
                    signal: by_mask["0111"]["registered_window_arithmetic"]["bvm_state"].get(window, {}).get(signal)
                    for signal in (
                        "P(B_JS1|XBVM2)", "P(B_JS2|XBVM2)",
                        "P(B_JS1|XBVM3)", "P(B_JS2|XBVM3)",
                        "P(B_JS1|XBVM4)", "P(B_JS2|XBVM4)",
                    )
                }
                for window in ("[113,117)ps", "[117,121)ps")
            }
        },
    })
    questions.append({
        "id": 6,
        "question": "After the first BJ2 handoff window, what is the signed I(B_JSL8) trajectory?",
        "status": "SCIENTIFIC_REVIEW_REQUIRED",
        "registered_data": {
            mask: {
                window: by_mask[mask]["registered_window_arithmetic"]["boundary"].get(window, {}).get("I(B_JSL8)")
                for window in ("[113,117)ps", "[117,121)ps")
            }
            for mask in MASKS
        },
    })
    questions.append({
        "id": 7,
        "question": "Are BVM JM1/JM2 storage traces unchanged in the registered tail comparison?",
        "status": "SCIENTIFIC_REVIEW_REQUIRED",
        "registered_data": {
            mask: {
                window: {
                    signal: by_mask[mask]["registered_window_arithmetic"]["bvm_state"].get(window, {}).get(signal)
                    for signal in (
                        f"P(B_JM1|XBVM{active_cells(mask)[0]})",
                        f"P(B_JM2|XBVM{active_cells(mask)[0]})",
                    )
                }
                for window in ("[101,110)ps", "[160,200)ps")
            }
            for mask in MASKS
        },
    })
    questions.append({
        "id": 8,
        "question": "Is active-cell position symmetry present on the registered tail window?",
        "status": "SCIENTIFIC_REVIEW_REQUIRED",
        "registered_data": {mask: by_mask[mask]["active_cell_symmetry"] for mask in MASKS},
    })
    questions.append({
        "id": 9,
        "question": "What is the N2 final registered phase/current state?",
        "status": "SCIENTIFIC_REVIEW_REQUIRED",
        "registered_data": {
            "candidate_0011": by_mask["0011"]["registered_window_arithmetic"],
            "baseline_0011": comparisons["candidate_vs_baseline"]["0011"],
        },
    })
    questions.append({
        "id": 10,
        "question": "What is the N3 final registered phase/current state?",
        "status": "SCIENTIFIC_REVIEW_REQUIRED",
        "registered_data": {
            "candidate_0111": by_mask["0111"]["registered_window_arithmetic"],
            "baseline_0111": comparisons["candidate_vs_baseline"]["0111"],
        },
    })
    questions.append({
        "id": 11,
        "question": "Which scientific label applies: mechanism support, functional success, overdamping, no effect, or new pathology?",
        "status": "SCIENTIFIC_REVIEW_REQUIRED",
        "assigned_label": None,
        "allowed_labels": [
            "mechanism support",
            "functional success",
            "overdamping",
            "no effect",
            "new pathology",
        ],
    })
    return questions


def execute() -> None:
    state = read_json(EXP / "run_state.json")
    if state.get("status") != "PREFLIGHT_PASS" or state.get("actual_physical_solve_count") != 0:
        raise RuntimeError("execution requires untouched PREFLIGHT_PASS state")
    provenance = read_json(EXP / "provenance.json")
    if git_head() != provenance["registration_head"]:
        raise RuntimeError("HEAD changed after preflight")
    for item in provenance["sources"]:
        path = REPO / item["path"]
        if sha256(path) != item["sha256"]:
            raise RuntimeError(f"registered source changed after preflight: {path}")

    for mask in MASKS:
        directory = run_dir(mask)
        deck = directory / "deck.cir"
        raw = directory / "raw.csv"
        log = directory / "run.log"
        if raw.exists() or log.exists():
            raise RuntimeError(f"refusing overwrite or retry of existing artifacts: {directory}")
        expected = provenance["registered_decks"][mask]
        if sha256(deck) != expected["sha256"]:
            raise RuntimeError(f"registered deck changed after preflight: {deck}")

        command = [str(SOLVER), "-a", "1", "-o", str(raw), str(deck)]
        started = now()
        with log.open("x", encoding="utf-8") as stream:
            stream.write(
                f"experiment={EXP.name}\n"
                f"run_id={run_id(mask)}\n"
                f"started_at={started}\n"
                f"command={' '.join(command)}\n"
            )
            stream.flush()
            completed = subprocess.run(
                command,
                cwd=REPO,
                stdout=stream,
                stderr=subprocess.STDOUT,
                check=False,
            )
            stream.write(f"finished_at={now()}\nexit_code={completed.returncode}\n")

        record: dict[str, Any] = {
            "run_id": run_id(mask),
            "mask": mask,
            "deck": {
                "path": rel(deck),
                "sha256": sha256(deck),
                "bytes": deck.stat().st_size,
            },
            "log": {
                "path": rel(log),
                "sha256": sha256(log),
                "bytes": log.stat().st_size,
            },
            "command": command,
            "solver": solver_context(),
            "started_at": started,
            "finished_at": now(),
            "raw_immutable": True,
            "scientific_interpretation_performed": False,
        }
        if completed.returncode != 0 or not raw.is_file() or raw.stat().st_size == 0:
            record["execution_status"] = "SOLVER_FAIL"
            provenance.setdefault("runs", {})[run_id(mask)] = record
            state["run_order"].append(run_id(mask))
            state["actual_physical_solve_count"] = len(state["run_order"])
            state["status"] = "SOLVER_FAILURE_STOP"
            state["updated_at"] = now()
            write_json(EXP / "provenance.json", provenance)
            write_json(EXP / "run_state.json", state)
            raise RuntimeError(f"solver failed for {mask}; failure preserved and no retry authorized")

        try:
            trace = load_raw(raw)
        except Exception as exc:
            record["execution_status"] = "RAW_PARSE_FAILURE"
            record["raw"] = {
                "path": rel(raw),
                "sha256": sha256(raw),
                "bytes": raw.stat().st_size,
            }
            record["raw_parse_error"] = str(exc)
            provenance.setdefault("runs", {})[run_id(mask)] = record
            state["run_order"].append(run_id(mask))
            state["actual_physical_solve_count"] = len(state["run_order"])
            state["status"] = "RAW_FAILURE_STOP"
            state["updated_at"] = now()
            write_json(EXP / "provenance.json", provenance)
            write_json(EXP / "run_state.json", state)
            raise RuntimeError(f"raw QA failed for {mask}; artifact preserved and no retry authorized") from exc

        missing = sorted(expected_headers() - set(trace.headers))
        record["raw"] = {
            "path": rel(raw),
            "sha256": sha256(raw),
            "bytes": raw.stat().st_size,
            "sample_count": trace.sample_count,
            "time_start_ps": trace.time[0] * 1.0e12,
            "time_end_ps": trace.time[-1] * 1.0e12,
        }
        record["execution_status"] = "RUN_PASS" if not missing else "RUN_PASS_MISSING_PROBES"
        record["missing_required_probes"] = missing
        provenance.setdefault("runs", {})[run_id(mask)] = record
        state["run_order"].append(run_id(mask))
        state["actual_physical_solve_count"] = len(state["run_order"])
        state["updated_at"] = now()
        write_json(EXP / "provenance.json", provenance)
        write_json(EXP / "run_state.json", state)
        if missing:
            state["status"] = "RAW_PROBE_FAILURE_STOP"
            write_json(EXP / "run_state.json", state)
            raise RuntimeError(f"missing required probes for {mask}; no retry authorized: {missing}")
        print(json.dumps({
            "run_id": run_id(mask),
            "status": "RUN_PASS",
            "raw_bytes": raw.stat().st_size,
        }, ensure_ascii=False))

    state["status"] = "RUN_COMPLETE"
    state["updated_at"] = now()
    write_json(EXP / "run_state.json", state)


def result_markdown(result: dict[str, Any]) -> str:
    runs = {item["mask"]: item for item in result["derived"]["runs"]}
    lines = [
        f"# BVM -> QB receiver-boundary R20 shunt ({EXP.name})",
        "",
        f"- Status: {FINAL_MARKER}",
        f"- Artifact status after raw parsing: {result.get('artifact_status', 'VALID')}",
        "- Authorized/completed physical solves: 2/2 (0011, 0111).",
        "- Scientific interpretation: NOT_PERFORMED; scientific questions remain SCIENTIFIC_REVIEW_REQUIRED.",
        "- Intervention: exactly R_QBIN_SHUNT QBIN 0 20; no other circuit or protocol change.",
        "",
        "## Registered numeric observations",
        "",
        "These values are registered raw observations or mechanical arithmetic only;",
        "they are not physical classifications.",
        "",
        "| case | V(QBIN) peak abs, [113,117) ps (mV) | I(R_QBIN_SHUNT) peak abs, [113,117) ps (uA) | KCL max abs, [0,200) ps (A) |",
        "|---|---:|---:|---:|",
    ]
    for mask in MASKS:
        boundary = runs[mask]["registered_window_arithmetic"]["boundary"]["[113,117)ps"]
        vqbin = boundary["V(QBIN)"].get("display_peak_abs_mV")
        ishunt = boundary["I(R_QBIN_SHUNT)"].get("display_peak_abs_uA")
        kcl = runs[mask]["boundary_kcl"]["windows"]["[0,200)ps"].get("peak_abs")
        lines.append(
            f"| {mask} | {vqbin:.9g} | {ishunt:.9g} | {kcl:.9g} |"
        )
    lines += [
        "",
        "## Registered review questions",
        "",
    ]
    for question in result["review_questions"]:
        lines.append(
            f"{question['id']}. {question['question']} — {question['status']}"
        )
    lines += [
        "",
        "## Evidence boundary",
        "",
        "P(...) remains raw phase in radians. Displayed phase turns use",
        "unwrap(rad)/(2*pi) only for navigation; they are not SFQ counts or",
        "closed-loop fluxoid counts. KCL residuals are registered arithmetic and",
        "do not certify switching, SFQ delivery, a Gate, or a mechanism.",
        "",
        "Baseline and passive raw files are referenced by path and SHA-256 only;",
        "no historical raw was copied or changed. No focused plots or unregistered",
        "follow-up solves were generated.",
        "",
        f"Stop marker: {FINAL_MARKER}",
        "",
    ]
    return "\n".join(lines)


def analyze() -> None:
    state = read_json(EXP / "run_state.json")
    if (
        state.get("actual_physical_solve_count") != 2
        or state.get("run_order") != [run_id(mask) for mask in MASKS]
    ):
        raise RuntimeError("analysis requires exactly the two completed registered runs")

    provenance = read_json(EXP / "provenance.json")
    traces: dict[str, Any] = {}
    before: dict[str, str] = {}
    metrics_list: list[dict[str, Any]] = []
    for mask in MASKS:
        path = raw_path(mask)
        before[run_id(mask)] = sha256(path)
        trace = load_raw(path)
        missing = sorted(expected_headers() - set(trace.headers))
        if missing:
            raise RuntimeError(f"missing candidate probes for {mask}: {missing}")
        traces[mask] = trace
        metrics_list.append(run_metrics(mask, trace))

    provenance["raw_hash_before_analysis"] = before
    write_json(EXP / "provenance.json", provenance)

    sets = metric_signal_sets()
    baseline_comparisons: dict[str, Any] = {}
    passive_metadata: dict[str, Any] = {}
    for mask in MASKS:
        baseline_raw = (
            BASELINE_ROOT
            / f"ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_{mask}"
            / "raw.csv"
        )
        baseline = load_raw(baseline_raw)
        baseline_comparisons[mask] = compare_traces(
            traces[mask], baseline, sets["compare"], baseline_signal
        )
        passive_name = f"PASSIVE_N2_{mask}" if mask == "0011" else f"PASSIVE_N3_{mask}"
        passive_raw = PASSIVE_ROOT / passive_name / "raw.csv"
        passive = load_raw(passive_raw)
        passive_metadata[mask] = {
            "path": rel(passive_raw),
            "sha256": sha256(passive_raw),
            "sample_count": passive.sample_count,
            "time_start_ps": passive.time[0] * 1.0e12,
            "time_end_ps": passive.time[-1] * 1.0e12,
            "shared_signal_count": len(
                set(sets["passive_compare"]) & set(passive.headers)
            ),
        }

    candidate_n2_n3 = compare_traces(
        traces["0011"], traces["0111"], sets["compare"]
    )
    comparisons = {
        "candidate_vs_baseline": baseline_comparisons,
        "candidate_n2_vs_n3": candidate_n2_n3,
        "passive_references": passive_metadata,
    }
    after = {run_id(mask): sha256(raw_path(mask)) for mask in MASKS}
    if before != after:
        raise RuntimeError("raw changed during analysis")
    provenance["raw_hash_after_analysis"] = after
    provenance["analysis"] = {
        "generated_at": now(),
        "raw_hashes_equal_before_after": True,
        "scientific_interpretation_performed": False,
        "registered_arithmetic_only": True,
    }
    write_json(EXP / "provenance.json", provenance)

    result = {
        "schema": "bvm-qb-qbin-shunt-r20-result-v1",
        "experiment_id": EXP.name,
        "generated_at": now(),
        "artifact_status": "VALID",
        "execution": {
            "authorized_physical_solve_count": 2,
            "actual_physical_solve_count": 2,
            "completed_runs": [run_id(mask) for mask in MASKS],
        },
        "observed": {
            "intervention": "R_QBIN_SHUNT QBIN 0 20",
            "masks": list(MASKS),
            "topology": "4xBVM -> COMMON_SL -> 8JSL -> canonical QB -> JTL1..6 -> R_TERM",
            "raw_phase_unit": "radians",
            "raw_time_unit": "seconds",
            "no_raw_copy": True,
        },
        "derived": {
            "windows_ps": [list(window) for window in WINDOWS_PS],
            "runs": metrics_list,
            "comparisons": comparisons,
            "phi0_reference_Wb": PHI0,
            "voltage_area_method": "actual-grid trapezoid; no interpolation",
        },
        "review_questions": review_questions({"runs": metrics_list}, comparisons),
        "unknown": [
            "scientific meaning of QBIN excursion",
            "mechanism",
            "SFQ event identity/count",
            "JJ switching certification",
            "N2/N3 functional classification",
            "convergence",
            "parameter ranking",
            "interface/system Gate",
            "hardware implication",
        ],
        "interpretation": {
            "scientific_analysis_performed": False,
            "physical_verdict": "NOT_ASSIGNED",
            "review_state": "AWAITING_SCIENTIFIC_REVIEW",
            "phase_turns_are_navigation_only": True,
            "classification_assigned": None,
        },
        "stop": {
            "final_marker": FINAL_MARKER,
            "automatic_follow_up": False,
        },
    }
    write_json(EXP / "result.json", result)
    (EXP / "RESULT.md").write_text(result_markdown(result), encoding="utf-8")
    (EXP / "RESULT_BRIEF.md").write_text(result_markdown(result), encoding="utf-8")
    (EXP / "EVIDENCE_MANIFEST.md").write_text(
        "\n".join(
            [
                f"# Evidence manifest — {EXP.name}",
                "",
                f"- Final state: {FINAL_MARKER}",
                "- Scientific interpretation: NOT_PERFORMED.",
                "- Candidate raw: runs/0011/raw.csv, runs/0111/raw.csv.",
                "- Standalone plots: plots/0011/, plots/0111/.",
                "- Full-window comparisons: plots/comparisons/.",
                "- Machine evidence: mechanical_qa.json, visualization_manifest.json, visualization_qa.json, PACKAGE_QA.json.",
                "- Baseline/passive inputs are path+SHA references only; no raw copy exists in this experiment.",
                "- The package is at the experiment root because the registered compact layout explicitly omits a handoff/ subdirectory.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    write_json(EXP / "RAW_ANALYSIS_HANDOFF_MANIFEST.json", {
        "schema": "bvm-qb-qbin-shunt-r20-raw-analysis-manifest-v1",
        "experiment_id": EXP.name,
        "created_at": now(),
        "raw_is_immutable_solver_output": True,
        "scientific_interpretation_performed": False,
        "authorized_runs": [
            {
                "run_id": run_id(mask),
                "deck": rel(run_dir(mask) / "deck.cir"),
                "raw": rel(raw_path(mask)),
                "run_log": rel(run_dir(mask) / "run.log"),
                "raw_sha256": after[run_id(mask)],
            }
            for mask in MASKS
        ],
        "source_manifest_path": "SOURCE_MANIFEST.json",
        "provenance_path": "provenance.json",
        "mechanical_qa_path": "mechanical_qa.json",
        "visualization_manifest_path": "visualization_manifest.json",
        "package_qa_path": "PACKAGE_QA.json",
    })
    state["status"] = "ANALYSIS_COMPLETE"
    state["updated_at"] = now()
    state["final_marker"] = FINAL_MARKER
    write_json(EXP / "run_state.json", state)
    print(json.dumps({
        "status": "ANALYSIS_COMPLETE",
        "raw_hashes_equal_before_after": True,
        "scientific_interpretation_performed": False,
    }, ensure_ascii=False, indent=2))


def mechanical_qa() -> None:
    provenance = read_json(EXP / "provenance.json")
    state = read_json(EXP / "run_state.json")
    failures: list[str] = []
    checks: dict[str, Any] = {}
    required = expected_headers()

    for mask in MASKS:
        directory = run_dir(mask)
        deck = directory / "deck.cir"
        raw = directory / "raw.csv"
        log = directory / "run.log"
        deck_value = deck.read_text(encoding="utf-8") if deck.is_file() else ""
        shunt_lines = [
            line.strip()
            for line in deck_value.splitlines()
            if line.strip().startswith("R_QBIN_SHUNT")
        ]
        forbidden_qbin_resistors = [
            line.strip()
            for line in deck_value.splitlines()
            if line.strip().startswith("R_")
            and "QBIN" in line
            and "R_QBIN_SHUNT" not in line
        ]
        unexpected = (
            sorted(
                path.name
                for path in directory.iterdir()
                if path.name not in {"deck.cir", "raw.csv", "run.log"}
            )
            if directory.is_dir()
            else ["missing_run_directory"]
        )
        warning_lines = []
        if log.is_file():
            warning_lines = [
                line.strip()
                for line in log.read_text(errors="replace").splitlines()
                if any(
                    token in line
                    for token in (
                        "Missing model:",
                        "Using default model",
                        "Unknown device/node",
                        "Cannot store results",
                    )
                )
            ]
        try:
            trace = load_raw(raw)
            missing = sorted(required - set(trace.headers))
            duplicate = trace.duplicate_columns
            raw_qa = trace.qa()
        except Exception as exc:
            trace = None
            missing = [f"raw_parse_error:{exc}"]
            duplicate = {}
            raw_qa = {}
        expected_hash = (
            provenance.get("runs", {})
            .get(run_id(mask), {})
            .get("raw", {})
            .get("sha256")
        )
        raw_hash_match = raw.is_file() and sha256(raw) == expected_hash
        kcl_max = None
        kcl_rms = None
        if trace is not None:
            full = kcl_metrics(trace)["windows"]["[0,200)ps"]
            kcl_max = full.get("peak_abs")
            residual = tuple(
                a - b - c
                for a, b, c in zip(
                    trace.column("I(B_JSL8)"),
                    trace.column("I(R_QBIN_SHUNT)"),
                    trace.column("I(LIN|XBQ)"),
                )
            )
            kcl_rms = math.sqrt(
                sum(value * value for value in residual) / len(residual)
            )
        deck_ok = (
            shunt_lines == ["R_QBIN_SHUNT QBIN 0 20"]
            and not forbidden_qbin_resistors
            and ".param" not in deck_value
            and "BQ_parameterized_bjs400" not in deck_value
            and "XBQ1" not in deck_value
        )
        run_pass = bool(
            deck_ok
            and not unexpected
            and not warning_lines
            and not missing
            and not duplicate
            and raw_hash_match
            and trace is not None
            and raw_qa.get("sample_count") == 1999
            and raw_qa.get("strictly_increasing_time") is True
            and kcl_max is not None
            and kcl_max <= KCL_TOLERANCE_A
            and state.get("actual_physical_solve_count") == 2
        )
        if not run_pass:
            failures.append(run_id(mask))
        checks[run_id(mask)] = {
            "status": "PASS" if run_pass else "ARTIFACT_INVALID",
            "deck": {
                "path": rel(deck),
                "sha256": sha256(deck) if deck.is_file() else None,
                "exact_shunt_lines": shunt_lines,
                "forbidden_qbin_resistor_lines": forbidden_qbin_resistors,
                "no_param_override": ".param" not in deck_value,
                "uses_canonical_candidate_instance_name": "XBQ1" not in deck_value,
            },
            "raw": {
                "path": rel(raw),
                "sha256": sha256(raw) if raw.is_file() else None,
                "recorded_hash": expected_hash,
                "hash_match": raw_hash_match,
                "qa": raw_qa,
                "missing_required_probes": missing,
                "duplicate_columns": duplicate,
            },
            "solver_warning_lines": warning_lines,
            "kcl_full_window_max_abs_A": kcl_max,
            "kcl_full_window_rms_A": kcl_rms,
            "kcl_tolerance_A": KCL_TOLERANCE_A,
            "unexpected_run_entries": unexpected,
        }

    qa = {
        "schema": "bvm-qb-qbin-shunt-r20-mechanical-qa-v1",
        "experiment_id": EXP.name,
        "generated_at": now(),
        "status": "PASS" if not failures else "FAIL",
        "artifact_status": "VALID" if not failures else "ARTIFACT_INVALID",
        "authorized_run_count": 2,
        "completed_run_count": 2 if not failures else 2 - len(failures),
        "head": provenance.get("registration_head"),
        "remote_bvm_master": provenance.get("remote_bvm_master"),
        "raw_hash_before_after_equal": provenance.get("analysis", {}).get(
            "raw_hashes_equal_before_after", False
        ),
        "scientific_interpretation_performed": False,
        "runs": checks,
        "no_raw_copy": True,
        "no_unregistered_shunt": not failures,
    }
    write_json(EXP / "mechanical_qa.json", qa)
    if failures:
        raise RuntimeError(
            f"mechanical QA failed; artifact status is ARTIFACT_INVALID: {failures}"
        )
    print(json.dumps({
        "status": "PASS",
        "runs": list(checks),
        "kcl_tolerance_A": KCL_TOLERANCE_A,
    }, ensure_ascii=False, indent=2))


def render_plot(
    input_path: Path,
    output_path: Path,
    subset: list[str],
    title: str,
) -> None:
    if output_path.exists():
        raise RuntimeError(f"refusing overwrite of visualization: {output_path}")
    command = [
        sys.executable,
        str(PLOTTER),
        str(input_path),
        "-x",
        str(output_path),
        "-t",
        "sep_comb",
        "-c",
        "dark",
        "-j",
        "2pi",
        "-w",
        title,
        "-s",
        *subset,
    ]
    completed = subprocess.run(
        command, cwd=REPO, capture_output=True, text=True, check=False
    )
    if (
        completed.returncode != 0
        or not output_path.is_file()
        or output_path.stat().st_size == 0
    ):
        raise RuntimeError(
            f"plot failed: {output_path}: {completed.stderr[-1000:]}"
        )


def prefixed_label(case: str, signal: str) -> str:
    if len(signal) < 3 or signal[1] != "(" or not signal.endswith(")"):
        raise ValueError(signal)
    return f"{signal[0]}({case}|{signal[2:-1]})"


def comparison_csv(
    cases: list[tuple[str, Any, Any]],
    signals: Iterable[str],
) -> tuple[Path, list[str]]:
    signal_list = list(signals)
    times = cases[0][1].time
    if any(tuple(trace.time) != tuple(times) for _, trace, _ in cases[1:]):
        raise RuntimeError("comparison raw grids do not match")
    labels: list[str] = []
    selected: list[tuple[str, list[float]]] = []
    for case, trace, mapper in cases:
        for signal in signal_list:
            mapped = mapper(signal)
            if mapped in trace.headers:
                label = prefixed_label(case, signal)
                labels.append(label)
                selected.append((label, list(trace.column(mapped))))
    handle = tempfile.NamedTemporaryFile(
        prefix="bvm_qb_r20_compare_",
        suffix=".csv",
        delete=False,
        dir="/tmp",
    )
    temp_path = Path(handle.name)
    handle.close()
    with temp_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["time", *labels])
        for index, timestamp in enumerate(times):
            writer.writerow(
                [
                    f"{timestamp:.17e}",
                    *(f"{values[index]:.17e}" for _, values in selected),
                ]
            )
    return temp_path, labels


def tracesafe(mask: str) -> Any:
    return load_raw(raw_path(mask))


def viz() -> None:
    qa = read_json(EXP / "mechanical_qa.json")
    if qa.get("status") != "PASS":
        raise RuntimeError("mechanical QA must pass before visualization")
    sets = metric_signal_sets()
    entries: list[dict[str, Any]] = []
    view_specs: dict[str, tuple[list[str], str]] = {}
    bvm_phase = list(sets["bvm_phase"])
    bvm_currents = [
        f"I(I_{kind}{index})"
        for index in range(1, 5)
        for kind in ("WL", "BL", "SE")
    ] + [
        f"I({element}|XBVM{index})"
        for index in range(1, 5)
        for element in (
            "L_M1", "L_M2", "L_M3", "L_S1",
            "L_S2", "L_S3", "L_PSL", "L_SL",
        )
    ]
    common_jsl = ["V(COMMON_SL)"] + [
        signal
        for index in range(1, 9)
        for signal in (
            f"P(B_JSL{index})",
            f"V(B_JSL{index})",
            f"I(B_JSL{index})",
        )
    ]
    qbin = [
        "V(COMMON_SL)",
        "V(QBIN)",
        "I(B_JSL8)",
        "I(R_QBIN_SHUNT)",
        "I(LIN|XBQ)",
    ]
    qb = list(sets["qb_all"])
    jtl = list(sets["jtl"])
    terminal = ["V(QBOUT)", "V(JTL6_OUT)", "I(R_TERM)"]
    view_specs.update({
        "01_bvm_phase": (
            bvm_phase,
            "BVM STATE: raw P radians; -j 2pi displays continuous phase turns for navigation only",
        ),
        "02_bvm_currents": (
            bvm_currents,
            "BVM INPUT/STATE: raw currents; source and branch directions follow the netlist",
        ),
        "03_common_jsl": (
            common_jsl,
            "JSL CHAIN: COMMON_SL -> B_JSL1 -> ... -> B_JSL8 -> QBIN; raw signals",
        ),
        "04_qbin_boundary": (
            qbin,
            "QBIN BOUNDARY: B_JSL8 JSL_NODE7->QBIN; shunt QBIN->0; LIN QBIN->BQ node1",
        ),
        "05_qb": (
            qb,
            "QB STATE: raw QB P/V/I and branch currents; phase display is rad/(2*pi) navigation",
        ),
        "06_jtl": (
            jtl,
            "JTL CHAIN: six stages with raw B01/B02 P/V/I and stage outputs; no event count implied",
        ),
        "07_terminal": (
            terminal,
            "OUTPUT BOUNDARY: QBOUT -> JTL6_OUT -> R_TERM; terminal current JTL6_OUT->ground",
        ),
    })

    for mask in MASKS:
        trace = load_raw(raw_path(mask))
        output_dir = EXP / "plots" / mask
        output_dir.mkdir(parents=True, exist_ok=True)
        for view, (signals, note) in view_specs.items():
            missing = [signal for signal in signals if signal not in trace.headers]
            if missing:
                raise RuntimeError(f"missing plot signals for {mask}/{view}: {missing}")
            output = output_dir / f"{view}.html"
            title = (
                f"{EXP.name} | candidate={mask} | {view} | raw 0-200 ps | {note}"
            )
            render_plot(raw_path(mask), output, signals, title)
            entries.append({
                "kind": "standalone",
                "run_id": run_id(mask),
                "mask": mask,
                "view": view,
                "path": rel(output),
                "raw_path": rel(raw_path(mask)),
                "raw_sha256": sha256(raw_path(mask)),
                "renderer_path": rel(PLOTTER),
                "renderer_sha256": sha256(PLOTTER),
                "window_ps": [0.0, 200.0],
                "phase_display": "P raw radians; -j 2pi = rad/(2*pi) turns navigation only",
                "direction_note": note,
            })

    comparisons = [
        (
            "comparison_A_0011",
            [
                ("candidate_0011", tracesafe("0011"), lambda signal: signal),
                (
                    "baseline_0011",
                    load_raw(
                        BASELINE_ROOT
                        / "ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_0011"
                        / "raw.csv"
                    ),
                    baseline_signal,
                ),
            ],
            list(sets["compare"]),
            "A: candidate 0011 vs read-only baseline 0011",
        ),
        (
            "comparison_B_0111",
            [
                ("candidate_0111", tracesafe("0111"), lambda signal: signal),
                (
                    "baseline_0111",
                    load_raw(
                        BASELINE_ROOT
                        / "ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_0111"
                        / "raw.csv"
                    ),
                    baseline_signal,
                ),
            ],
            list(sets["compare"]),
            "B: candidate 0111 vs read-only baseline 0111",
        ),
        (
            "comparison_C_n2_n3",
            [
                ("candidate_N2_0011", tracesafe("0011"), lambda signal: signal),
                ("candidate_N3_0111", tracesafe("0111"), lambda signal: signal),
            ],
            list(sets["compare"]),
            "C: candidate N2 0011 vs candidate N3 0111",
        ),
    ]
    passive_cases = [
        ("candidate_0011", tracesafe("0011"), lambda signal: signal),
        (
            "baseline_0011",
            load_raw(
                BASELINE_ROOT
                / "ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_0011"
                / "raw.csv"
            ),
            baseline_signal,
        ),
        (
            "passive_0011",
            load_raw(PASSIVE_ROOT / "PASSIVE_N2_0011" / "raw.csv"),
            lambda signal: signal,
        ),
    ]
    comparisons.append(
        (
            "comparison_D_passive_reference",
            passive_cases,
            list(sets["passive_compare"]),
            "D: passive reference vs candidate vs baseline (shared BVM/JSL only)",
        )
    )

    comparison_entries: list[dict[str, Any]] = []
    comparison_dir = EXP / "plots" / "comparisons"
    comparison_dir.mkdir(parents=True, exist_ok=True)
    for stem, cases, signals, note in comparisons:
        temp_path, labels = comparison_csv(cases, signals)
        output = comparison_dir / f"{stem}.html"
        try:
            render_plot(
                temp_path,
                output,
                labels,
                f"{EXP.name} | {note} | full raw 0-200 ps | P display rad/(2*pi)",
            )
        finally:
            temp_path.unlink(missing_ok=True)
        comparison_entries.append({
            "kind": "comparison",
            "comparison": stem,
            "path": rel(output),
            "source_cases": [
                {
                    "case": case,
                    "raw_path": rel(trace.path),
                    "raw_sha256": sha256(trace.path),
                }
                for case, trace, _ in cases
            ],
            "signals": signals,
            "rendered_labels": labels,
            "renderer_path": rel(PLOTTER),
            "renderer_sha256": sha256(PLOTTER),
            "window_ps": [0.0, 200.0],
            "full_window_only": True,
            "phase_display": "independently display raw phase as rad/(2*pi) only",
            "direction_note": note,
        })

    manifest = {
        "schema": "bvm-qb-qbin-shunt-r20-visualization-manifest-v1",
        "experiment_id": EXP.name,
        "generated_at": now(),
        "renderer": {
            "path": rel(PLOTTER),
            "sha256": sha256(PLOTTER),
            "layout": "sep_comb",
            "color": "dark",
            "phase_option": "2pi",
        },
        "whole_run_window_ps": [0.0, 200.0],
        "focused_windows": [],
        "explicit_no_focused_html": True,
        "standalone_entries": entries,
        "comparison_entries": comparison_entries,
        "entries": entries + comparison_entries,
        "entry_count": len(entries) + len(comparison_entries),
        "scientific_interpretation_performed": False,
        "status": "PASS",
    }
    write_json(EXP / "visualization_manifest.json", manifest)
    html_files = sorted(
        path for path in (EXP / "plots").rglob("*") if path.is_file()
    )
    non_html = [
        rel(path) for path in html_files if path.suffix.lower() != ".html"
    ]
    expected_paths = [REPO / item["path"] for item in manifest["entries"]]
    viz_qa = {
        "schema": "bvm-qb-qbin-shunt-r20-visualization-qa-v1",
        "experiment_id": EXP.name,
        "generated_at": now(),
        "status": (
            "PASS"
            if not non_html
            and all(
                path.is_file() and path.stat().st_size > 0
                for path in expected_paths
            )
            and len(entries) == 14
            and len(comparison_entries) == 4
            else "FAIL"
        ),
        "standalone_count": len(entries),
        "comparison_count": len(comparison_entries),
        "expected_standalone_count": 14,
        "expected_comparison_count": 4,
        "full_window_only": True,
        "focused_windows": [],
        "non_html_plot_files": non_html,
        "html_files": [
            {
                "path": rel(path),
                "sha256": sha256(path),
                "bytes": path.stat().st_size,
            }
            for path in html_files
        ],
        "raw_hashes_rechecked": all(
            item["raw_sha256"] == sha256(REPO / item["raw_path"])
            for item in entries
        ),
        "scientific_interpretation_performed": False,
    }
    write_json(EXP / "visualization_qa.json", viz_qa)
    if viz_qa["status"] != "PASS":
        raise RuntimeError("visualization QA failed")
    print(json.dumps({
        "status": "PASS",
        "standalone_html": len(entries),
        "comparison_html": len(comparison_entries),
    }, ensure_ascii=False, indent=2))


def visualization_qa_only() -> None:
    manifest = read_json(EXP / "visualization_manifest.json")
    entries = manifest.get("entries", [])
    html_files = sorted(
        path for path in (EXP / "plots").rglob("*") if path.is_file()
    )
    non_html = [
        rel(path) for path in html_files if path.suffix.lower() != ".html"
    ]
    expected_paths = [REPO / item["path"] for item in entries]
    raw_ok = all(
        item.get("kind") != "standalone"
        or item.get("raw_sha256") == sha256(REPO / item["raw_path"])
        for item in entries
    )
    qa = {
        "schema": "bvm-qb-qbin-shunt-r20-visualization-qa-v1",
        "experiment_id": EXP.name,
        "generated_at": now(),
        "status": (
            "PASS"
            if not non_html
            and all(
                path.is_file() and path.stat().st_size > 0
                for path in expected_paths
            )
            and len(manifest.get("standalone_entries", [])) == 14
            and len(manifest.get("comparison_entries", [])) == 4
            and raw_ok
            else "FAIL"
        ),
        "standalone_count": len(manifest.get("standalone_entries", [])),
        "comparison_count": len(manifest.get("comparison_entries", [])),
        "expected_standalone_count": 14,
        "expected_comparison_count": 4,
        "full_window_only": manifest.get("focused_windows") == [],
        "focused_windows": manifest.get("focused_windows", []),
        "non_html_plot_files": non_html,
        "html_files": [
            {
                "path": rel(path),
                "sha256": sha256(path),
                "bytes": path.stat().st_size,
            }
            for path in html_files
        ],
        "raw_hashes_rechecked": raw_ok,
        "scientific_interpretation_performed": False,
        "renderer_not_rerun": True,
    }
    write_json(EXP / "visualization_qa.json", qa)
    provenance = read_json(EXP / "provenance.json")
    provenance["postsolve_tooling_revision"] = {
        "script_path": rel(SCRIPT),
        "script_sha256": sha256(SCRIPT),
        "reason": "read-only visualization QA path correction; no raw, deck, or HTML renderer rerun",
        "raw_mutated": False,
    }
    write_json(EXP / "provenance.json", provenance)
    if qa["status"] != "PASS":
        raise RuntimeError("visualization QA failed")
    print(json.dumps({
        "status": "PASS",
        "standalone_html": qa["standalone_count"],
        "comparison_html": qa["comparison_count"],
        "renderer_not_rerun": True,
    }, ensure_ascii=False, indent=2))


def package() -> None:
    if (
        read_json(EXP / "mechanical_qa.json").get("status") != "PASS"
        or read_json(EXP / "visualization_qa.json").get("status") != "PASS"
    ):
        raise RuntimeError(
            "mechanical and visualization QA must pass before packaging"
        )
    if PACKAGE.exists():
        raise RuntimeError(f"refusing overwrite of immutable package: {PACKAGE}")

    root_names = (
        "PREFLIGHT.md",
        "experiment.yaml",
        "RESULT.md",
        "RESULT_BRIEF.md",
        "run.sh",
        "result.json",
        "provenance.json",
        "SOURCE_MANIFEST.json",
        "mechanical_qa.json",
        "visualization_manifest.json",
        "visualization_qa.json",
        "EVIDENCE_MANIFEST.md",
        "RAW_ANALYSIS_HANDOFF_MANIFEST.json",
        "run_state.json",
    )
    files: list[tuple[Path, str]] = []
    for name in root_names:
        path = EXP / name
        if path.is_file():
            files.append((path, path.relative_to(EXP).as_posix()))
    for path in sorted((EXP / "runs").rglob("*")):
        if path.is_file():
            files.append((path, path.relative_to(EXP).as_posix()))
    for path in sorted((EXP / "plots").rglob("*.html")):
        files.append((path, path.relative_to(EXP).as_posix()))
    files.append((SCRIPT, "executor/bvm_qb_qbin_shunt_r20.py"))

    records = [
        {
            "path": archive_name,
            "sha256": sha256(path),
            "bytes": path.stat().st_size,
            "source_path": rel(path) if path.is_relative_to(REPO) else str(path),
        }
        for path, archive_name in files
    ]
    with zipfile.ZipFile(
        PACKAGE, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=6
    ) as archive:
        for path, archive_name in files:
            archive.write(path, archive_name)
    with zipfile.ZipFile(PACKAGE, "r") as archive:
        reopened = {
            name: hashlib.sha256(archive.read(name)).hexdigest()
            for name in archive.namelist()
        }
    expected = {record["path"]: record["sha256"] for record in records}
    qa = {
        "schema": "bvm-qb-qbin-shunt-r20-package-qa-v1",
        "experiment_id": EXP.name,
        "generated_at": now(),
        "package_path": rel(PACKAGE),
        "package_sha256": sha256(PACKAGE),
        "package_bytes": PACKAGE.stat().st_size,
        "git_head_at_packaging": git_head(),
        "authorized_physical_solve_count": 2,
        "actual_physical_solve_count": 2,
        "file_count": len(records),
        "expected_file_hashes_match_after_reopen": expected == reopened,
        "contains_raw_reference_copy": False,
        "qa_outside_zip": True,
        "zip_files": records,
        "status": "PASS" if expected == reopened else "FAIL",
    }
    write_json(PACKAGE_QA, qa)
    if qa["status"] != "PASS":
        raise RuntimeError("package QA failed; package is not eligible for commit")
    state = read_json(EXP / "run_state.json")
    state["status"] = "PACKAGED"
    state["updated_at"] = now()
    state["final_marker"] = FINAL_MARKER
    write_json(EXP / "run_state.json", state)
    print(json.dumps({
        "status": "PASS",
        "package": rel(PACKAGE),
        "sha256": qa["package_sha256"],
        "bytes": qa["package_bytes"],
        "files": qa["file_count"],
    }, ensure_ascii=False, indent=2))


def main() -> int:
    command = sys.argv[1] if len(sys.argv) > 1 else "all"
    actions = {
        "prepare": prepare,
        "run": execute,
        "analyze": analyze,
        "qa": mechanical_qa,
        "viz": viz,
        "viz-qa": visualization_qa_only,
        "package": package,
    }
    if command == "all":
        for action in (prepare, execute, analyze, mechanical_qa, viz, package):
            action()
        return 0
    if command not in actions:
        print(
            f"usage: {Path(sys.argv[0]).name} "
            "[prepare|run|analyze|qa|viz|viz-qa|package|all]",
            file=sys.stderr,
        )
        return 2
    actions[command]()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
