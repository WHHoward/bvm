#!/usr/bin/env python3
"""Generate the frozen common-SL -> 12-JSL -> BVMSim BQ -> JTL decks."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


REPO = Path(__file__).resolve().parents[3]
EXP = Path(__file__).resolve().parent
PASSIVE = REPO / "test/exploration/bvmsim-4bvm-paperlike-common-sl-accumulation-isolation-v1-20260904"
PASSIVE_TEMPLATE_SHA256 = "4159a81074053eabd310f08e955953a12d412e00e9bb9d4cc0ebbc7512c9bef6"
BVM_VARIANT = REPO / "test/exploration/bvmsim-jm2-connected-single-ab-v1-20260903/variants/bvm_jm2_connected.cir"
BQ = REPO / "BVMSim/BQ.cir"
JTL = REPO / "BVMSim/library_josim/jtl2.cir"
SHARED_JJMIT = REPO / "circuits/models/jjmit.cir"
CANONICAL_BVM = REPO / "circuits/bvm/bvm_cell.cir"
SOLVER = REPO / "build/josim-cli"
MASKS = ("0000", "0001", "0010", "0100", "1000", "0011", "0111", "1100", "1110", "1111")
BASE_HEAD = "a58bbb3b566b466110bccda8f89fc36c4ce2d368"
EXPECTED_HASHES = {
    "bvm_variant": "0093a45cc3910448b484d8bd004c6df8c22358bacc8b3ed5e23912dcab805d54",
    "bq": "f3dcbf5f9bb3898faf5194b5f7c4771df3fa1ed16150496de4b52cb6f7256dfd",
    "jtl": "ffd31f8eda2a86ca0133342be1ce678831b7237a53911eda046d2bff8454855a",
    "shared_jjmit": "19862d1fd1f1f44dfa1523848d7d3b5e2594a6c5da8fdd80144b449e5312a336",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO.resolve()).as_posix()


def live_timestamp() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def active_lines(path: Path) -> list[str]:
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("*")
    ]


def bit(mask: str, instance: int) -> bool:
    return mask[instance - 1] == "1"


def base_sources(mask: str) -> list[str]:
    source = PASSIVE / "runs" / mask / "deck.cir"
    if not source.is_file():
        raise RuntimeError(f"missing passive deck: {source}")
    lines = active_lines(source)
    result = [line for line in lines if line.startswith(("I_WL", "I_BL", "I_SE"))]
    expected = [
        line
        for instance in range(1, 5)
        for control in ("I_WL", "I_BL", "I_SE")
        for line in result
        if line.startswith(f"{control}{instance} ")
    ]
    if len(result) != 12 or len(expected) != 12:
        raise RuntimeError(f"{mask}: passive stimulus source count is not 12")
    return expected


def bvm_instances() -> list[str]:
    return [f"XBVM{i} WL{i} BL{i} SE{i} COMMON_SL BVM" for i in range(1, 5)]


def jsl_lines() -> list[str]:
    rows: list[str] = []
    for index in range(1, 13):
        first = "COMMON_SL" if index == 1 else f"COL{index - 1:02d}"
        second = "QBIN" if index == 12 else f"COL{index:02d}"
        rows.append(f"B_JSL{index:02d} {first} {second} jjmit area=5.0")
    return rows


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


def add_unique(labels: list[str], label: str) -> None:
    if label not in labels:
        labels.append(label)


def per_bvm_probe_labels(instance: int) -> list[str]:
    hierarchy = f"XBVM{instance}"
    labels: list[str] = []
    for junction in ("B_JM1", "B_JM2", "B_JS1", "B_JS2"):
        for quantity in ("P", "V", "I"):
            add_unique(labels, f"{quantity}({junction}|{hierarchy})")
    branch_names = (
        "L_M1", "L_M2", "L_M3", "L_PM", "R_JM1", "L_S1", "L_S2", "R_S",
        "L_S3", "R_SE", "L_PSE", "L_PSL", "R_SL", "L_SL",
    )
    for branch in branch_names:
        add_unique(labels, f"I({branch}|{hierarchy})")
        add_unique(labels, f"V({branch}|{hierarchy})")
    return labels


def required_probe_labels() -> list[str]:
    labels: list[str] = []
    for instance in range(1, 5):
        for control in ("WL", "BL", "SE"):
            add_unique(labels, f"I(I_{control}{instance})")
        for label in per_bvm_probe_labels(instance):
            add_unique(labels, label)
    add_unique(labels, "V(COMMON_SL)")
    for index in range(1, 13):
        branch = f"B_JSL{index:02d}"
        for quantity in ("P", "V", "I"):
            add_unique(labels, f"{quantity}({branch})")
    for label in ("V(QBIN)", "V(QBOUT)", "V(JTL1_OUT)", "V(JTL2_OUT)", "V(JTL3_OUT)", "V(JTL4_OUT)", "V(JTL5_OUT)", "V(JTL6_OUT)", "I(R_TERM)"):
        add_unique(labels, label)
    # Keep the QB branch probes to currents.  These are the branch
    # observables already used by the historical BVMSim deck; node voltages
    # and JJ voltages below cover the voltage-side evidence without relying
    # on optional branch-voltage syntax for inductors/resistors/sources.
    for branch in ("LIN", "L1", "L2", "L3", "RJ1", "RJ2", "IB"):
        add_unique(labels, f"I({branch}|XBQ1)")
    for junction in ("BJS", "BJ1", "BJ2"):
        for quantity in ("P", "V", "I"):
            add_unique(labels, f"{quantity}({junction}|XBQ1)")
    for stage in range(1, 7):
        hierarchy = f"XJTL1_{stage}"
        for junction in ("B01", "B02"):
            for quantity in ("P", "V"):
                add_unique(labels, f"{quantity}({junction}|{hierarchy})")
    return labels


def print_block(labels: list[str], width: int = 8) -> str:
    return "\n".join(".print " + " ".join(labels[index:index + width]) for index in range(0, len(labels), width))


def deck_text(mask: str) -> str:
    active = ", ".join(f"BVM{i}" for i in range(1, 5) if bit(mask, i)) or "none"
    lines = [
        f"* GENERATED COMMON-SL 12-JSL QB INTEGRATION DECK: mask={mask}",
        "* source_class=HISTORICAL_BVMSIM_JM2_CONNECTED_COMMON_SL_12JSL_QB_VARIANT",
        "* causal continuity: passive COMMON_SL -> same 12x500uA JSL -> GND",
        "* authorized boundary only: JSL12 downstream GND -> QBIN",
        "* all four BVMs stored-1111; exactly one final selective READ; no history READ",
        f"* final READ active BVMs: {active}",
        "",
        ".include ../../../../../circuits/models/jjmit.cir",
        ".include ../../../bvmsim-jm2-connected-single-ab-v1-20260903/variants/bvm_jm2_connected.cir",
        ".include ../../../../../BVMSim/BQ.cir",
        ".include ../../../../../BVMSim/library_josim/jtl2.cir",
        "",
        *bvm_instances(),
        "",
        "* Same twelve shared JSL elements as passive baseline; only B_JSL12 endpoint is QBIN.",
        *jsl_lines(),
        "",
        "* Frozen historical BVMSim QB and six-stage BVMSim JTL chain.",
        *receiver_lines(),
        "",
        *base_sources(mask),
        "",
        ".tran 0.1p 200p 45p",
        "",
        "* Full registered probe schema: BVM source, JSL interface, QB, JTL, termination.",
        print_block(required_probe_labels()),
        ".end",
        "",
    ]
    return "\n".join(lines)


def validate_deck(mask: str, text: str) -> None:
    lines = active_lines_from_text(text)
    if lines.count(".end") != 1:
        raise RuntimeError(f"{mask}: expected exactly one .end")
    if ".tran 0.1p 200p 45p" not in lines:
        raise RuntimeError(f"{mask}: .tran changed")
    for required in (
        "../../../../../BVMSim/BQ.cir",
        "../../../../../BVMSim/library_josim/jtl2.cir",
        "bvm_jm2_connected.cir",
    ):
        if not any(required in line for line in lines if line.lower().startswith(".include")):
            raise RuntimeError(f"{mask}: missing include {required}")
    instances = [line for line in lines if line.startswith("XBVM")]
    if instances != bvm_instances():
        raise RuntimeError(f"{mask}: BVM instance topology changed")
    jsl = [line.split() for line in lines if line.startswith("B_JSL")]
    expected = [row.split() for row in jsl_lines()]
    if jsl != expected:
        raise RuntimeError(f"{mask}: JSL chain mismatch")
    receiver = [line for line in lines if line.startswith(("XBQ1", "xjtl1_", "R_TERM"))]
    if receiver != receiver_lines():
        raise RuntimeError(f"{mask}: receiver chain mismatch")
    if any(line.startswith(("B_COL_LOAD", "B_LD", "BVMout", "R_SL")) for line in lines):
        raise RuntimeError(f"{mask}: stale distributed/per-cell load or external RSL remains")
    printed = [token for line in text.splitlines() if line.strip().lower().startswith(".print") for token in line.split()[1:]]
    if len(printed) != len(set(printed)):
        raise RuntimeError(f"{mask}: duplicate probe labels")
    missing = sorted(set(required_probe_labels()) - set(printed))
    if missing:
        raise RuntimeError(f"{mask}: missing probes: {missing}")
    source_lines = [line for line in lines if line.startswith(("I_WL", "I_BL", "I_SE"))]
    if source_lines != base_sources(mask):
        raise RuntimeError(f"{mask}: stimulus differs from passive baseline")


def active_lines_from_text(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip() and not line.lstrip().startswith("*")]


def current_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()


def provenance(deck_records: dict[str, object], head: str) -> dict[str, object]:
    source_paths: dict[str, Path] = {
        "passive_baseline_experiment": PASSIVE / "experiment.yaml",
        "passive_baseline_template_deck": PASSIVE / "runs/1111/deck.cir",
        "jm2_connected_bvm_variant": BVM_VARIANT,
        "bvmsim_bq": BQ,
        "bvmsim_jtl": JTL,
        "shared_jjmit": SHARED_JJMIT,
        "canonical_bvm_not_used": CANONICAL_BVM,
        "solver": SOLVER,
    }
    passive_raw_hashes = {
        mask: sha256(PASSIVE / "runs" / mask / "raw.csv")
        for mask in MASKS
        if (PASSIVE / "runs" / mask / "raw.csv").is_file()
    }
    return {
        "schema": "bvmsim-common-sl-12jsl-qb-integration-provenance-v1",
        "experiment_id": EXP.name,
        "created_at_local": live_timestamp(),
        "head_before_setup": head,
        "base_head_expected": BASE_HEAD,
        "source_class": "HISTORICAL_BVMSIM_JM2_CONNECTED_COMMON_SL_12JSL_QB_VARIANT",
        "source_records": {name: {"path": rel(path), "sha256": sha256(path)} for name, path in source_paths.items() if path.is_file()},
        "expected_hashes": EXPECTED_HASHES,
        "passive_baseline": {
            "path": rel(PASSIVE),
            "template_deck_sha256": sha256(PASSIVE / "runs/1111/deck.cir"),
            "template_deck_expected_sha256": PASSIVE_TEMPLATE_SHA256,
            "raw_sha256_by_mask": passive_raw_hashes,
        },
        "authorized_boundary_change": {
            "from": "B_JSL12 COL11 0 jjmit area=5.0",
            "to": "B_JSL12 COL11 QBIN jjmit area=5.0",
            "all_upstream_bvm_common_sl_jsl_physics_frozen": True,
            "frozen_bq_added": True,
            "frozen_six_stage_jtl_added": True,
            "termination_ohm": 10.0,
        },
        "deck_records": deck_records,
        "canonical_bvm_used": False,
        "qb_authority": "BVMSim/BQ.cir exact file; no handwritten replacement",
        "jtl_authority": "BVMSim/library_josim/jtl2.cir exact file; no normalization",
        "phase_statement": "P is raw radians; turns are continuous_unwrap(rad)/(2*pi)",
        "event_statement": "phase displacement, voltage area, and crossings are not SFQ counts",
        "gate": {
            "state": "AWAITING_USER_REVIEW",
            "user_reviewed": False,
            "next_step_authorized": False,
            "automatic_next_experiment": False,
            "next_action": "STOP",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-head", default=BASE_HEAD)
    args = parser.parse_args()
    if args.base_head != BASE_HEAD:
        raise RuntimeError(f"unexpected base head: {args.base_head}")
    if current_head() != BASE_HEAD:
        raise RuntimeError(f"generator must run at base HEAD {BASE_HEAD}, got {current_head()}")
    if sha256(PASSIVE / "runs/1111/deck.cir") != PASSIVE_TEMPLATE_SHA256:
        raise RuntimeError("passive baseline template hash changed")
    for name, path in (("bvm_variant", BVM_VARIANT), ("bq", BQ), ("jtl", JTL), ("shared_jjmit", SHARED_JJMIT)):
        actual = sha256(path)
        if actual != EXPECTED_HASHES[name]:
            raise RuntimeError(f"{name} hash changed: {actual}")
    records: dict[str, object] = {}
    for mask in MASKS:
        output = EXP / "runs" / mask / "deck.cir"
        if output.exists():
            raise RuntimeError(f"refusing to overwrite frozen deck: {output}")
        text = deck_text(mask)
        validate_deck(mask, text)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")
        records[mask] = {"path": rel(output), "sha256": sha256(output), "mask": mask, "population": mask.count("1")}
    provenance_path = EXP / "provenance.json"
    if provenance_path.exists():
        raise RuntimeError(f"refusing to overwrite provenance: {provenance_path}")
    provenance_path.write_text(json.dumps(provenance(records, current_head()), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "mask_count": len(MASKS), "probe_count": len(required_probe_labels()), "output": rel(provenance_path)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
