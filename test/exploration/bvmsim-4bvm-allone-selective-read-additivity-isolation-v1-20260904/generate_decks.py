#!/usr/bin/env python3
"""Generate the ten independent all-one/selective-read executed decks.

The 1111 JM2-connected deck from the accepted six-state fixture is the
physical template.  This generator changes only the declared source PWLs and
adds the frozen single/array branch probe schema; all circuit element lines,
model closure, QB, JTL and termination lines are inherited mechanically.
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path


REPO = Path(__file__).resolve().parents[3]
EXP = Path(__file__).resolve().parent
TEMPLATE_EXPERIMENT = REPO / "test/exploration/bvmsim-4bvm-jm2-connected-state-position-ab-v1-20260903"
TEMPLATE = TEMPLATE_EXPERIMENT / "runs/1111/deck.cir"
VARIANT = REPO / "test/exploration/bvmsim-jm2-connected-single-ab-v1-20260903/variants/bvm_jm2_connected.cir"
HISTORICAL_BVM = REPO / "BVMSim/bvm_cell.cir"
HISTORICAL_QB = REPO / "BVMSim/BQ.cir"
HISTORICAL_JTL = REPO / "BVMSim/library_josim/jtl2.cir"
SHARED_JJMIT = REPO / "circuits/models/jjmit.cir"
CANONICAL_BVM = REPO / "circuits/bvm/bvm_cell.cir"
SOLVER = REPO / "build/josim-cli"
AUTHORIZED_HEAD = "9e8fa5aed3346a30531d5001874e27dbee8eb81a"
TEMPLATE_SHA256 = "3fcdb8b0d61c91cadcacee77c3c06b3a03f8f9392a8c838e9b8574b8938b4e88"
MASKS = ("0000", "0001", "0010", "0100", "1000", "0011", "0111", "1100", "1110", "1111")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def relative(path: Path) -> str:
    return path.resolve().relative_to(REPO.resolve()).as_posix()


def write_once(path: Path, content: str) -> None:
    if path.exists():
        if path.read_text(encoding="utf-8") == content:
            return
        raise RuntimeError(f"refusing to overwrite existing artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def bit(mask: str, instance: int) -> bool:
    if len(mask) != 4 or any(value not in "01" for value in mask):
        raise ValueError(f"invalid mask: {mask}")
    return mask[instance - 1] == "1"


def source_line(instance: int, control: str, active: bool = False) -> str:
    """Return one explicit PWL source with the fixed all-one/selective timing."""

    if control == "WL":
        read_value = "100u" if active else "0"
        return (
            f"I_WL{instance} 0 WL{instance} pwl(0 0 50p 0 51p -100u 60p -100u 61p 0 "
            f"70p 0 81p 0 90p 0 91p 100u 100p 100u 101p 0 110p 0 111p {read_value} "
            f"120p {read_value} 121p 0 200p 0)"
        )
    if control == "BL":
        return (
            f"I_BL{instance} 0 BL{instance} pwl(0 0 50p 0 51p -100u 60p -100u 61p 0 "
            f"70p 0 90p 0 91p 100u 100p 100u 101p 0 110p 0 111p 0 120p 0 121p 0 200p 0)"
        )
    if control == "SE":
        read_value = "100u" if active else "0"
        return (
            f"I_SE{instance} 0 SE{instance} pwl(0 0 50p 0 70p 0 90p 0 110p 0 "
            f"111p {read_value} 120p {read_value} 121p 0 200p 0)"
        )
    raise ValueError(f"unknown control: {control}")


def replace_sources(text: str, mask: str) -> str:
    lines = text.splitlines()
    replacements = {
        f"I_{control}{instance}": source_line(instance, control, active=bit(mask, instance))
        if control in ("WL", "SE")
        else source_line(instance, control)
        for instance in range(1, 5)
        for control in ("WL", "BL", "SE")
    }
    seen: set[str] = set()
    output: list[str] = []
    for line in lines:
        match = re.match(r"^\s*(I_(WL|BL|SE)([1-4]))\s+", line)
        if match and not line.lstrip().startswith("*"):
            name = match.group(1)
            output.append(replacements[name])
            seen.add(name)
        else:
            output.append(line)
    expected = set(replacements)
    if seen != expected:
        raise RuntimeError(f"source replacement mismatch for {mask}: missing={sorted(expected-seen)} extra={sorted(seen-expected)}")
    return "\n".join(output)


def per_bvm_probe_labels(instance: int) -> list[str]:
    hierarchy = f"XBVM{instance}"
    labels: list[str] = []
    for junction in ("B_JM1", "B_JM2", "B_JS1", "B_JS2"):
        labels.extend((f"P({junction}|{hierarchy})", f"V({junction}|{hierarchy})", f"I({junction}|{hierarchy})"))
    for name in (
        "L_M1", "L_M2", "L_M3", "L_PM", "R_JM1", "L_S1", "L_S2", "R_S",
        "L_S3", "R_SE", "L_PSE", "L_PSL", "R_SL", "L_SL",
    ):
        labels.append(f"I({name}|{hierarchy})")
    for name in (
        "R_JM1", "L_S1", "B_JS1", "L_S2", "B_JS2", "R_S", "L_S3",
        "R_SE", "L_PSE", "L_PSL", "R_SL", "L_SL",
    ):
        labels.append(f"V({name}|{hierarchy})")
    labels.append(f"V(SL{instance})")
    return labels


def required_probe_labels() -> list[str]:
    labels: list[str] = []
    labels.extend(f"I(I_{control}{instance})" for instance in range(1, 5) for control in ("WL", "BL", "SE"))
    for instance in range(1, 5):
        labels.extend(per_bvm_probe_labels(instance))
    for name in ("B_LD01", "B_LD12", "B_LD2_01", "B_LD2_12", "B_LD3_01", "B_LD3_12", "B_LD4_01", "B_LD4_11", "BVMOUT"):
        labels.extend((f"P({name})", f"V({name})", f"I({name})"))
    labels.extend(("V(QBIN)", "V(QBOUT)", "I(LIN|XBQ1)"))
    for name in ("BJS", "BJ1", "BJ2"):
        labels.extend((f"P({name}|XBQ1)", f"V({name}|XBQ1)", f"I({name}|XBQ1)"))
    labels.extend(("I(RJ1|XBQ1)", "I(RJ2|XBQ1)", "I(L1|XBQ1)", "I(L2|XBQ1)", "I(L3|XBQ1)", "I(IB|XBQ1)"))
    for stage in range(1, 7):
        for junction in ("B01", "B02"):
            labels.extend((f"P({junction}|XJTL1_{stage})", f"V({junction}|XJTL1_{stage})"))
    return list(dict.fromkeys(labels))


def active_print_labels(text: str) -> list[str]:
    labels: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith(".print"):
            labels.extend(stripped.split()[1:])
    return labels


def normalized_physics(text: str) -> list[str]:
    """Remove comments, active prints and all source PWLs for identity QA."""

    result: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("*"):
            continue
        if stripped.startswith(".print"):
            continue
        if re.match(r"^I_(WL|BL|SE)[1-4]\s+", stripped):
            continue
        result.append(stripped)
    return result


def append_probe_block(text: str) -> str:
    existing = active_print_labels(text)
    counts = {label: existing.count(label) for label in set(existing)}
    if any(count > 1 for count in counts.values()):
        duplicates = sorted(label for label, count in counts.items() if count > 1)
        raise RuntimeError(f"template already has duplicate active probes: {duplicates}")
    missing = [label for label in required_probe_labels() if label not in existing]
    if not missing:
        raise RuntimeError("no branch probes are missing from template")
    blocks: list[str] = [
        "* BVM_SINGLE_ARRAY_BRANCH_V1: direct branch probes for hierarchy/sign/KCL QA.",
        "* Strict-series probes are intentionally retained; this block changes observability only.",
    ]
    for instance in range(1, 5):
        labels = [label for label in per_bvm_probe_labels(instance) if label in missing]
        if labels:
            blocks.append(f"* BVM{instance} branch schema")
            blocks.extend(".print " + " ".join(labels[index:index + 12]) for index in range(0, len(labels), 12))
    remaining = [label for label in missing if not any(label in per_bvm_probe_labels(instance) for instance in range(1, 5))]
    if remaining:
        blocks.append("* shared/QB/JTL labels missing from template")
        blocks.extend(".print " + " ".join(remaining[index:index + 12]) for index in range(0, len(remaining), 12))
    lines = text.splitlines()
    end_positions = [index for index, line in enumerate(lines) if line.strip().lower() == ".end"]
    if len(end_positions) != 1:
        raise RuntimeError(f"expected one .end, found {len(end_positions)}")
    lines.insert(end_positions[0], "\n".join(blocks))
    return "\n".join(lines) + "\n"


def make_deck(mask: str) -> str:
    if not TEMPLATE.is_file():
        raise RuntimeError(f"missing physical template: {TEMPLATE}")
    if sha256(TEMPLATE) != TEMPLATE_SHA256:
        raise RuntimeError(f"template hash changed: {TEMPLATE}")
    text = TEMPLATE.read_text(encoding="utf-8")
    text = replace_sources(text, mask)
    text = append_probe_block(text)
    header = (
        f"* GENERATED ALL-ONE SELECTIVE-READ DECK: mask={mask}\n"
        "* source_class=HISTORICAL_BVMSIM_JM2_CONNECTED_VARIANT\n"
        "* all four BVMs are initialized to 1111; only READ WL+SE follows mask\n"
        "* no-read interval 70--81 ps is deliberately zero for all BVMs\n"
    )
    return header + text


def validate_deck_identity(mask: str, content: str) -> None:
    base = TEMPLATE.read_text(encoding="utf-8")
    normalized_base = normalized_physics(base)
    normalized_new = normalized_physics(content)
    if normalized_base != normalized_new:
        diff = "\n".join(difflib.unified_diff(normalized_base, normalized_new, fromfile="template", tofile=mask, lineterm=""))
        raise RuntimeError(f"{mask}: physics identity failed:\n{diff}")
    active = active_print_labels(content)
    duplicates = sorted({label for label in active if active.count(label) > 1})
    if duplicates:
        raise RuntimeError(f"{mask}: duplicate active probe labels: {duplicates}")
    required = required_probe_labels()
    missing = [label for label in required if label not in active]
    if missing:
        raise RuntimeError(f"{mask}: missing required probes: {missing}")
    for instance in range(1, 5):
        for control in ("WL", "BL", "SE"):
            name = f"I_{control}{instance}"
            if not re.search(rf"(?m)^\s*{name}\s+", content):
                raise RuntimeError(f"{mask}: source {name} missing")
    # The write-to-1111 and selective-read invariants are checked from source text.
    for instance in range(1, 5):
        for token in ("51p -100u 60p -100u", "91p 100u 100p 100u"):
            line = next(line for line in content.splitlines() if line.startswith(f"I_WL{instance} "))
            if token not in line:
                raise RuntimeError(f"{mask}: WL{instance} missing {token}")
        bl_line = next(line for line in content.splitlines() if line.startswith(f"I_BL{instance} "))
        if "91p 100u 100p 100u" not in bl_line:
            raise RuntimeError(f"{mask}: BL{instance} does not write all-one")
        for control in ("WL", "SE"):
            line = next(line for line in content.splitlines() if line.startswith(f"I_{control}{instance} "))
            expected = "100u" if bit(mask, instance) else "0"
            if f"111p {expected} 120p {expected}" not in line:
                raise RuntimeError(f"{mask}: {control}{instance} read mask mismatch")
        if "111p 0 120p 0" not in bl_line:
            raise RuntimeError(f"{mask}: BL{instance} is not zero during READ")


def write_provenance(deck_records: dict[str, dict[str, object]], head: str) -> None:
    sources = {
        "template_deck": TEMPLATE,
        "historical_bvm": HISTORICAL_BVM,
        "historical_qb": HISTORICAL_QB,
        "historical_jtl": HISTORICAL_JTL,
        "shared_jjmit_reference": SHARED_JJMIT,
        "jm2_connected_variant": VARIANT,
        "canonical_bvm_not_used": CANONICAL_BVM,
        "single_s1_reference_raw": REPO / "test/exploration/bvmsim-jm2-connected-single-rloop-observability-v1-20260904/runs/S1-J-RLOOP/raw.csv",
        "single_s1_reference_deck": REPO / "test/exploration/bvmsim-jm2-connected-single-rloop-observability-v1-20260904/runs/S1-J-RLOOP/deck.cir",
    }
    record = {
        "schema": "bvmsim-4bvm-allone-selective-read-provenance-v1",
        "experiment_id": EXP.name,
        "created_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "head_before_setup": head,
        "authorized_head": AUTHORIZED_HEAD,
        "source_class": "HISTORICAL_BVMSIM_JM2_CONNECTED_VARIANT",
        "template": {"path": relative(TEMPLATE), "sha256": sha256(TEMPLATE)},
        "source_records": {
            name: {"path": relative(path), "sha256": sha256(path)} for name, path in sources.items()
        },
        "variant_identity": {
            "historical_bvm_sha256": sha256(HISTORICAL_BVM),
            "jm2_connected_variant_sha256": sha256(VARIANT),
            "expected_topology_delta": "L_M2 second node 4 -> 3 only",
        },
        "b_side_decks": deck_records,
        "frozen": {
            "masks": list(MASKS),
            "all_stored_initialization": "WRITE0 then all-four WRITE1; no read before selective READ",
            "read_mapping": "b3b2b1b0 -> BVM1/BVM2/BVM3/BVM4",
            "timestep_ps": 0.1,
            "stop_time_ps": 200,
            "output_start_ps": 45,
            "qb": "BVMSim/BQ.cir; RJ1=12 ohm; RJ2=4 ohm; IB=250 uA",
            "jtl": "BVMSim/library_josim/jtl2.cir; six stages; 280 uA each; 10 ohm termination",
        },
        "canonical_bvm_statement": "canonical circuits/bvm/bvm_cell.cir was not used; historical BVM remains the authority",
    }
    write_once(EXP / "provenance.json", json.dumps(record, indent=2, ensure_ascii=False) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    if not TEMPLATE.is_file():
        raise RuntimeError(f"missing template: {TEMPLATE}")
    if sha256(TEMPLATE) != TEMPLATE_SHA256:
        raise RuntimeError("template SHA-256 mismatch")
    for path in (VARIANT, HISTORICAL_BVM, HISTORICAL_QB, HISTORICAL_JTL, SHARED_JJMIT, SOLVER, CANONICAL_BVM):
        if not path.is_file():
            raise RuntimeError(f"missing source: {path}")
    records: dict[str, dict[str, object]] = {}
    contents: dict[str, str] = {}
    for mask in MASKS:
        content = make_deck(mask)
        validate_deck_identity(mask, content)
        target = EXP / "runs" / mask / "deck.cir"
        contents[mask] = content
        records[mask] = {
            "path": relative(target),
            "sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
            "template": relative(TEMPLATE),
            "mask": mask,
            "read_active_bvms": [instance for instance in range(1, 5) if bit(mask, instance)],
        }
    if args.check_only:
        print(json.dumps({"status": "PASS", "masks": list(MASKS), "writes": False}, ensure_ascii=False))
        return 0
    for mask, content in contents.items():
        write_once(EXP / "runs" / mask / "deck.cir", content)
    write_provenance(records, AUTHORIZED_HEAD)
    print(json.dumps({"status": "PASS", "masks": list(MASKS), "writes": True}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
