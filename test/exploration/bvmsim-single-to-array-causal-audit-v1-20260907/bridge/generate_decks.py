#!/usr/bin/env python3
"""Generate the two newly required one-BVM bridge decks.

G1 and G2 deliberately share the same BVM, 12-JSL boundary, QB, JTL and
probe schema.  Only the sensing boundary (G1) and then the stimulus
history/protocol (G2) change.  Existing G0/G3/G4 raw artifacts are referenced
by the analysis and are never regenerated here.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
BRIDGE = Path(__file__).resolve().parent
VARIANT = REPO / "test/exploration/bvmsim-jm2-connected-single-ab-v1-20260903/variants/bvm_jm2_connected.cir"
BQ = REPO / "BVMSim/BQ.cir"
JTL = REPO / "BVMSim/library_josim/jtl2.cir"
JJMIT = REPO / "circuits/models/jjmit.cir"
SOLVER = REPO / "build/josim-cli"
EXPECTED_HEAD = "470ad38cdaea0e55ed2a77d5e72c3ec7d001192e"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def active_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip() and not line.lstrip().startswith("*")]


def bvm_probe_labels() -> list[str]:
    labels: list[str] = []
    for control in ("WL", "BL", "SE"):
        labels.append(f"I(I_{control}1)")
    for junction in ("B_JM1", "B_JM2", "B_JS1", "B_JS2"):
        labels.extend(f"{quantity}({junction}|XBVM1)" for quantity in ("P", "V", "I"))
    for branch in (
        "L_M1", "L_M2", "L_M3", "L_PM", "R_JM1", "L_S1", "L_S2", "R_S",
        "L_S3", "R_SE", "L_PSE", "L_PSL", "R_SL", "L_SL",
    ):
        labels.extend((f"I({branch}|XBVM1)", f"V({branch}|XBVM1)"))
    return labels


def jsl_lines() -> list[str]:
    return [
        f"B_JSL{index:02d} {'COMMON_SL' if index == 1 else f'COL{index - 1:02d}'} {'QBIN' if index == 12 else f'COL{index:02d}'} jjmit area=5.0"
        for index in range(1, 13)
    ]


def receiver_lines() -> list[str]:
    return [
        "XBQ1 QBIN QBOUT BQ",
        "xjtl1_1 QBOUT JTL1_OUT jtl",
        "xjtl1_2 JTL1_OUT JTL2_OUT jtl",
        "xjtl1_3 JTL2_OUT JTL3_OUT jtl",
        "xjtl1_4 JTL3_OUT JTL4_OUT jtl",
        "xjtl1_5 JTL4_OUT JTL5_OUT jtl",
        "xjtl1_6 JTL5_OUT JTL6_OUT jtl",
        "R_TERM JTL6_OUT 0 10",
    ]


def qb_jtl_probe_labels() -> list[str]:
    labels = ["V(COMMON_SL)", "V(QBIN)", "V(QBOUT)"]
    labels.extend(f"{quantity}(B_JSL{index:02d})" for index in range(1, 13) for quantity in ("P", "V", "I"))
    labels.extend(f"I({branch}|XBQ1)" for branch in ("LIN", "L1", "L2", "L3", "RJ1", "RJ2", "IB"))
    labels.extend(f"{quantity}({junction}|XBQ1)" for junction in ("BJS", "BJ1", "BJ2") for quantity in ("P", "V", "I"))
    labels.extend(f"V(JTL{stage}_OUT)" for stage in range(1, 7))
    labels.append("I(R_TERM)")
    for stage in range(1, 7):
        labels.extend(
            f"{quantity}({junction}|XJTL1_{stage})"
            for junction in ("B01", "B02")
            for quantity in ("P", "V")
        )
    return labels


def probes() -> list[str]:
    result: list[str] = []
    for label in bvm_probe_labels() + qb_jtl_probe_labels():
        if label not in result:
            result.append(label)
    return result


def source_lines(generation: str) -> list[str]:
    if generation == "G1":
        return [
            "I_WL1 0 WL1 pwl(0 0 50p 0 51p +100u 60p +100u 61p 0 70p 0 71p 100u 80p 100u 81p 0 200p 0)",
            "I_BL1 0 BL1 pwl(0 0 50p 0 51p +100u 60p +100u 61p 0 70p 0 71p 0 80p 0 81p 0 200p 0)",
            "I_SE1 0 SE1 pwl(0 0 50p 0 51p 0 60p 0 61p 0 70p 0 71p 100u 80p 100u 81p 0 200p 0)",
        ]
    if generation == "G2":
        return [
            "I_WL1 0 WL1 pwl(0 0 50p 0 51p -100u 60p -100u 61p 0 70p 0 90p 0 91p 100u 100p 100u 101p 0 110p 0 111p 100u 120p 100u 121p 0 200p 0)",
            "I_BL1 0 BL1 pwl(0 0 50p 0 51p -100u 60p -100u 61p 0 70p 0 90p 0 91p 100u 100p 100u 101p 0 110p 0 111p 0 120p 0 121p 0 200p 0)",
            "I_SE1 0 SE1 pwl(0 0 50p 0 70p 0 90p 0 110p 0 111p 100u 120p 100u 121p 0 200p 0)",
        ]
    raise ValueError(generation)


def deck_text(generation: str) -> str:
    history = "G0 single S1 protocol" if generation == "G1" else "array history/protocol with one active BVM"
    lines = [
        f"* SINGLE -> ARRAY CAUSAL BRIDGE {generation}",
        "* source_class=HISTORICAL_BVMSIM_JM2_CONNECTED_VARIANT",
        f"* unique change under test: {'single sensing boundary -> shared 12-JSL boundary' if generation == 'G1' else 'G1 protocol/history -> array protocol/history'}",
        f"* protocol={history}",
        "* canonical BVM is not used; BVM variant is bvm_jm2_connected.cir",
        "",
        ".include ../../../../../circuits/models/jjmit.cir",
        ".include ../../../../../test/exploration/bvmsim-jm2-connected-single-ab-v1-20260903/variants/bvm_jm2_connected.cir",
        ".include ../../../../../BVMSim/BQ.cir",
        ".include ../../../../../BVMSim/library_josim/jtl2.cir",
        "",
        "XBVM1 WL1 BL1 SE1 COMMON_SL BVM",
        "",
        *jsl_lines(),
        "",
        *receiver_lines(),
        "",
        *source_lines(generation),
        "",
        ".tran 0.1p 200p",
        "",
    ]
    probe_list = probes()
    for start in range(0, len(probe_list), 8):
        lines.append(".print " + " ".join(probe_list[start:start + 8]))
    lines.extend((".end", ""))
    return "\n".join(lines)


def validate(generation: str, text: str) -> None:
    lines = active_lines(text)
    if lines.count(".end") != 1:
        raise RuntimeError(f"{generation}: expected one .end")
    if ".tran 0.1p 200p" not in lines:
        raise RuntimeError(f"{generation}: tran changed")
    if any("circuits/bvm/bvm_cell.cir" in line for line in text.splitlines()):
        raise RuntimeError(f"{generation}: canonical BVM included")
    if lines.count("XBVM1 WL1 BL1 SE1 COMMON_SL BVM") != 1:
        raise RuntimeError(f"{generation}: BVM endpoint changed")
    expected_jsl = jsl_lines()
    actual_jsl = [line for line in lines if line.startswith("B_JSL")]
    if actual_jsl != expected_jsl:
        raise RuntimeError(f"{generation}: JSL topology changed")
    if [line for line in lines if line.startswith(("XBQ1", "xjtl1_", "R_TERM"))] != receiver_lines():
        raise RuntimeError(f"{generation}: receiver topology changed")
    printed = [token for line in text.splitlines() if line.strip().lower().startswith(".print") for token in line.split()[1:]]
    if len(printed) != len(set(printed)):
        raise RuntimeError(f"{generation}: duplicate print label")
    missing = sorted(set(probes()) - set(printed))
    if missing:
        raise RuntimeError(f"{generation}: missing probes {missing}")
    sources = [line for line in lines if line.startswith(("I_WL1 ", "I_BL1 ", "I_SE1 "))]
    if sources != source_lines(generation):
        raise RuntimeError(f"{generation}: source protocol mismatch")


def current_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()


def main() -> int:
    if current_head() != EXPECTED_HEAD:
        raise RuntimeError(f"generator must run at preregistered HEAD {EXPECTED_HEAD}, got {current_head()}")
    for source in (VARIANT, BQ, JTL, JJMIT, SOLVER):
        if not source.is_file():
            raise RuntimeError(f"missing source: {source}")
    records: dict[str, object] = {}
    for generation in ("G1", "G2"):
        content = deck_text(generation)
        validate(generation, content)
        target = BRIDGE / "runs" / generation / "deck.cir"
        if target.exists():
            raise RuntimeError(f"refusing to overwrite deck: {target}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        records[generation] = {"path": str(target.relative_to(REPO)), "sha256": sha256(target), "probe_count": len(probes())}
    print(json.dumps({"status": "PASS", "records": records}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
