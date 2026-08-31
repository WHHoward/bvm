#!/usr/bin/env python3
"""Build the frozen 13 ps BVM -> 8xAREA=5 JSL -> scaled-QB fixture."""
from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[2]
INPUT = ROOT / "inputs"
REFERENCE = REPO / "test/exploration/physical-bvm-jsl12-qb-sfq-closure-v1-20260824"
SNAPSHOTS = ("jjmit.cir", "bvm_cell.cir", "bq_cell.cir")
ROLES = ("logical1_read", "logical0_read", "logical1_no_read_control", "logical0_no_read_control")
HEAD = "ff80ce285a2ce97f2414a19a7f8d6b92d8b1d3ae"
SOLVER_SHA256 = "48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2"
METRIC_SPEC_SHA256 = "f88a36f4d310b2572efdc7408d734640f25dd5aea2246b74fbb8b7bb7f0be470"


def copy_snapshot(name: str) -> None:
    src = REFERENCE / "inputs" / name
    dst = INPUT / name
    data = src.read_bytes()
    if dst.exists() and dst.read_bytes() != data:
        raise SystemExit(f"refusing to overwrite changed snapshot: {dst}")
    if not dst.exists():
        shutil.copyfile(src, dst)


def source_lines(state: str, read: bool) -> list[str]:
    init = "+100U" if state == "logical1" else "-100U"
    if read:
        read_wl = "96p +100U 109p +100U 110p 0"
        read_se = "96p +100U 109p +100U 110p 0"
    else:
        read_wl = "96p 0 105p 0 106p 0"
        read_se = "96p 0 105p 0 106p 0"
    return [
        f"I_WL1 0 WL1 pwl(0p 0 10p 0 11p {init} 20p {init} 21p 0 95p 0 {read_wl} 170p 0)",
        f"I_BL1 0 BL1 pwl(0p 0 10p 0 11p {init} 20p {init} 21p 0 170p 0)",
        f"I_SE1 0 SE1 pwl(0p 0 95p 0 {read_se} 170p 0)",
    ]


def jsl_lines() -> list[str]:
    lines = ["B_LD1  SL1  njsl1 jjmit area=5"]
    for idx in range(2, 8):
        lines.append(f"B_LD{idx}  njsl{idx - 1} njsl{idx} jjmit area=5")
    lines.append("B_LD8  njsl7 IN    jjmit area=5")
    return lines


def print_lines() -> list[str]:
    lines = [
        ".print P(B_JM1|XBVM1) V(B_JM1|XBVM1) P(B_JM2|XBVM1) V(B_JM2|XBVM1)",
        ".print P(B_JS1|XBVM1) V(B_JS1|XBVM1) P(B_JS2|XBVM1) V(B_JS2|XBVM1)",
        ".print V(N6|XBVM1) V(SL1) I(L_PSL|XBVM1) I(L_SL|XBVM1)",
    ]
    for idx in range(1, 9):
        lines.append(f".print P(B_LD{idx}) V(B_LD{idx}) I(B_LD{idx})")
    lines += [
        ".print P(BJs|XBQ) V(BJs|XBQ) I(BJs|XBQ)",
        ".print P(BJL1|XBQ) V(BJL1|XBQ) I(BJL1|XBQ)",
        ".print P(BJL2|XBQ) V(BJL2|XBQ) I(BJL2|XBQ)",
        ".print V(IN) V(OUT) I(Lin|XBQ) I(L0|XBQ) I(L1|XBQ) I(L2|XBQ)",
        ".print I(RB|XBQ) I(RJ1|XBQ) I(RJ2|XBQ) I(R_LOAD) I(I_IBIAS)",
        ".print I(I_WL1) I(I_BL1) I(I_SE1)",
    ]
    return lines


def deck(state: str, read: bool) -> str:
    role = f"{state}_{'read' if read else 'no_read_control'}"
    lines = [
        f"* BVM_JSL8_500_PHYSICAL_QB_RECHECK_V1: 13ps {role}",
        "* canonical BVM -> 8 series AREA=5 JSL -> frozen scaled QB; no ideal replay source",
        ".include ../jjmit.cir",
        ".include ../bvm_cell.cir",
        ".include ../bq_cell.cir",
        "XBVM1 WL1 BL1 SE1 SL1 BVM",
        *jsl_lines(),
        "XBQ IN OUT IBIAS BQ",
        "R_LOAD OUT 0 10",
        "I_IBIAS 0 IBIAS pwl(0p 0 1p 35u 2p 35u 170p 35u)",
        *source_lines(state, read),
        ".tran 0.0125p 170p",
        *print_lines(),
        ".end",
    ]
    return "\n".join(lines) + "\n"


def topology_precheck() -> dict[str, object]:
    physical = deck("logical1", True)
    checks = {
        "jsl_count": physical.count("jjmit area=5"),
        "all_jsl_area_5": physical.count("jjmit area=5") == 8,
        "last_jsl_ends_at_qb_in": "B_LD8  njsl7 IN    jjmit area=5" in physical,
        "qb_instantiated_at_in": "XBQ IN OUT IBIAS BQ" in physical,
        "no_jsl_ground_termination": "B_LD8  njsl7 0" not in physical,
        "no_ideal_replay_source": "I_REPLAY" not in physical,
        "single_qb_load": physical.count("R_LOAD OUT 0 10") == 1,
        "single_qb_bias": physical.count("I_IBIAS 0 IBIAS") == 1,
        "no_magnetic_coupling": "\nK" not in physical,
    }
    checks["status"] = "PASS" if all(bool(value) for key, value in checks.items() if key != "status") and checks["jsl_count"] == 8 else "FAIL"
    return checks


def main() -> None:
    INPUT.mkdir(parents=True, exist_ok=True)
    (ROOT / "analysis").mkdir(parents=True, exist_ok=True)
    for name in SNAPSHOTS:
        copy_snapshot(name)
    precheck = topology_precheck()
    (ROOT / "analysis/topology-precheck.json").write_text(json.dumps(precheck, indent=2) + "\n", encoding="utf-8")
    if precheck["status"] != "PASS":
        raise SystemExit(f"topology precheck failed: {precheck}")

    cases: dict[str, object] = {}
    for state in ("logical1", "logical0"):
        for read in (True, False):
            role = f"{state}_{'read' if read else 'no_read_control'}"
            expected = deck(state, read)
            path = INPUT / "13" / f"{role}.cir"
            if path.exists() and path.read_text(encoding="utf-8") != expected:
                raise SystemExit(f"refusing to overwrite non-identical fixture: {path}")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(expected, encoding="utf-8")
            cases[f"13ps_{role}"] = {
                "input": path.relative_to(ROOT).as_posix(),
                "read_width_ps": 13,
                "role": role,
                "sha256": hashlib.sha256(expected.encode()).hexdigest(),
            }

    snapshots = {
        name: {
            "path": (INPUT / name).relative_to(ROOT).as_posix(),
            "sha256": hashlib.sha256((INPUT / name).read_bytes()).hexdigest(),
        }
        for name in SNAPSHOTS
    }
    manifest: dict[str, object] = {
        "schema_version": "BVM_JSL8_500_PHYSICAL_QB_RECHECK_V1",
        "recorded_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "parent_head": HEAD,
        "paper_interface_audit": "docs/BVM_QB_PAPER_INTERFACE_AUDIT.md",
        "reference_experiment": "test/exploration/physical-bvm-jsl12-qb-sfq-closure-v1-20260824",
        "solver": {"path": "build/josim-cli", "version": "v2.7.2837d13", "sha256": SOLVER_SHA256},
        "metric_spec": {"path": "docs/METRIC_SPEC_V2.md", "sha256": METRIC_SPEC_SHA256},
        "timestep_ps": 0.0125,
        "stop_ps": 170.0,
        "topology": "canonical BVM SL -> B_LD1...B_LD8 AREA=5 -> QB IN; B_LD8 no GND termination",
        "frozen_qb": {"BJs_area": 0.5, "BJL1_area": 0.36, "BJL2_area": 0.54, "Lin_pH": 0.8, "L0_pH": 1.323, "L1_pH": 3.91, "L2_pH": 3.91, "RJ1_ohm": 33.0, "RJ2_ohm": 22.0, "RB_ohm": 6.0, "IBIAS_uA": 35.0, "RLOAD_ohm": 10.0},
        "small_signal_diagnostic_only": {"label": "ZERO_PHASE_SMALL_SIGNAL_ESTIMATE_ONLY", "L_12x320_pH": 12.34, "L_8x500_pH": 5.27, "ratio_8x500_over_12x320": 0.427},
        "snapshots": snapshots,
        "topology_precheck": "analysis/topology-precheck.json",
        "cases": cases,
        "execution": {"status": "PRE_REGISTERED", "case_count": 4, "roles": list(ROLES), "no_14ps_run": True},
        "analysis": {"status": "PENDING", "phase_semantics": "continuous_absolute", "windows_ps": {"pre": [80.0, 94.0], "active": [94.0, 130.0], "post": [140.0, 170.0]}},
    }
    manifest_path = ROOT / "manifest.yaml"
    if manifest_path.exists():
        try:
            old = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise SystemExit(f"existing manifest is not JSON-compatible: {manifest_path}") from exc
        if old.get("schema_version") != manifest["schema_version"]:
            raise SystemExit(f"refusing to overwrite another manifest: {manifest_path}")
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "cases": len(cases), "topology": precheck}, indent=2))


if __name__ == "__main__":
    main()
