#!/usr/bin/env python3
"""Build immutable physical BVM -> 12-JSL -> scaled-QB fixtures."""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[2]
INPUT = ROOT / "inputs"
SOURCE = REPO / "test/exploration/bvm-read-semantics-audit-and-jsl-width-bracket-v1-20260824/inputs"
SNAPSHOTS = ("jjmit.cir", "bvm_cell.cir", "bq_cell.cir")


def copy_snapshot(name: str) -> None:
    src = SOURCE / name
    dst = INPUT / name
    data = src.read_bytes()
    if dst.exists() and dst.read_bytes() != data:
        raise SystemExit(f"refusing to overwrite changed snapshot: {dst}")
    dst.write_bytes(data)


def source_lines(state: str, width: int, read: bool) -> list[str]:
    init = "+100U" if state == "logical1" else "-100U"
    if read:
        read_wl = f"96p +100U {96 + width}p +100U {97 + width}p 0"
        read_se = f"96p +100U {96 + width}p +100U {97 + width}p 0"
    else:
        read_wl = "96p 0 105p 0 106p 0"
        read_se = "96p 0 105p 0 106p 0"
    return [
        f"I_WL1 0 WL1 pwl(0p 0 10p 0 11p {init} 20p {init} 21p 0 95p 0 {read_wl} 170p 0)",
        f"I_BL1 0 BL1 pwl(0p 0 10p 0 11p {init} 20p {init} 21p 0 170p 0)",
        f"I_SE1 0 SE1 pwl(0p 0 95p 0 {read_se} 170p 0)",
    ]


def jsl_lines() -> list[str]:
    lines = ["B_LD1  SL1  njsl1 jjmit area=3.2"]
    for idx in range(2, 12):
        lines.append(f"B_LD{idx}  njsl{idx - 1} njsl{idx} jjmit area=3.2")
    lines.append("B_LD12 njsl11 IN    jjmit area=3.2")
    return lines


def print_lines() -> list[str]:
    lines = [
        ".print P(B_JM1|XBVM1) V(B_JM1|XBVM1) P(B_JM2|XBVM1) V(B_JM2|XBVM1)",
        ".print P(B_JS1|XBVM1) V(B_JS1|XBVM1) P(B_JS2|XBVM1) V(B_JS2|XBVM1)",
        ".print V(N6|XBVM1) V(SL1) I(L_PSL|XBVM1) I(L_SL|XBVM1)",
    ]
    for idx in range(1, 13):
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


def deck(state: str, width: int, read: bool) -> str:
    role = f"{state}_{'read' if read else 'no_read_control'}"
    lines = [
        f"* PHYSICAL_BVM_JSL12_QB_SFQ_CLOSURE_V1: {width}ps {role}",
        "* canonical BVM -> 12 series JSL -> frozen scaled QB; no ideal replay source",
        ".include ../jjmit.cir",
        ".include ../bvm_cell.cir",
        ".include ../bq_cell.cir",
        "XBVM1 WL1 BL1 SE1 SL1 BVM",
        *jsl_lines(),
        "XBQ IN OUT IBIAS BQ",
        "R_LOAD OUT 0 10",
        "I_IBIAS 0 IBIAS pwl(0p 0 1p 35u 2p 35u 170p 35u)",
        *source_lines(state, width, read),
        ".tran 0.0125p 170p",
        *print_lines(),
        ".end",
    ]
    return "\n".join(lines) + "\n"


def topology_precheck() -> dict[str, object]:
    physical = deck("logical1", 13, True)
    checks = {
        "jsl_count": physical.count("jjmit area=3.2"),
        "last_jsl_ends_at_qb_in": "B_LD12 njsl11 IN    jjmit area=3.2" in physical,
        "qb_instantiated_at_in": "XBQ IN OUT IBIAS BQ" in physical,
        "no_jsl_ground_termination": "B_LD12 njsl11 0" not in physical,
        "no_ideal_replay_source": "I_REPLAY" not in physical,
        "single_qb_load": physical.count("R_LOAD OUT 0 10") == 1,
        "single_qb_bias": physical.count("I_IBIAS 0 IBIAS") == 1,
    }
    checks["status"] = "PASS" if all(value for key, value in checks.items() if key != "status") and checks["jsl_count"] == 12 else "FAIL"
    return checks


def main() -> None:
    INPUT.mkdir(parents=True, exist_ok=True)
    for name in SNAPSHOTS:
        copy_snapshot(name)
    precheck = topology_precheck()
    (ROOT / "analysis/topology-precheck.json").write_text(json.dumps(precheck, indent=2) + "\n", encoding="utf-8")
    if precheck["status"] != "PASS":
        raise SystemExit(f"topology precheck failed: {precheck}")
    manifest: dict[str, object] = {
        "schema_version": "physical-bvm-jsl12-qb-v1",
        "parent_head": "52fdd7212e44dff1d94a6f64b21a31f9927ec4c3",
        "topology_precheck": "analysis/topology-precheck.json",
        "solver": {"path": "build/josim-cli", "version": "v2.7.2837d13"},
        "topology": "canonical BVM SL -> B_LD1...B_LD12 -> QB IN; B_LD12 no GND termination",
        "cases": {},
    }
    for width in (13, 14):
        for state in ("logical1", "logical0"):
            for read in (True, False):
                role = f"{state}_{'read' if read else 'no_read_control'}"
                path = INPUT / str(width) / f"{role}.cir"
                expected = deck(state, width, read)
                if path.exists() and path.read_text(encoding="utf-8") != expected:
                    raise SystemExit(f"refusing to overwrite non-identical fixture: {path}")
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(expected, encoding="utf-8")
                manifest["cases"][f"{width}ps_{role}"] = {
                    "input": path.relative_to(ROOT).as_posix(),
                    "width_ps": width,
                    "role": role,
                    "sha256": hashlib.sha256(expected.encode()).hexdigest(),
                }
    (ROOT / "manifest.yaml").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "cases": len(manifest["cases"]), "topology": precheck}, indent=2))


if __name__ == "__main__":
    main()
