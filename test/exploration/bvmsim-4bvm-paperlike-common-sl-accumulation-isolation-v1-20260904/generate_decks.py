#!/usr/bin/env python3
"""Freeze the ten common-SL topology decks without touching physical BVM lines."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path


REPO = Path(__file__).resolve().parents[3]
EXP = Path(__file__).resolve().parent
TEMPLATE = REPO / "test/exploration/bvmsim-4bvm-allone-selective-read-additivity-isolation-v1-20260904/runs/1111/deck.cir"
VARIANT = REPO / "test/exploration/bvmsim-jm2-connected-single-ab-v1-20260903/variants/bvm_jm2_connected.cir"
SHARED_JJMIT = REPO / "circuits/models/jjmit.cir"
CANONICAL_BVM = REPO / "circuits/bvm/bvm_cell.cir"
SOLVER = REPO / "build/josim-cli"
OLD_DISTRIBUTED = REPO / "test/exploration/bvmsim-4bvm-allone-selective-read-additivity-isolation-v1-20260904"
TEMPLATE_SHA256 = "5ee085051cfdc2cc6e45deac657230e86c64795d9cd9be100735b13974c3222e"
VARIANT_SHA256 = "0093a45cc3910448b484d8bd004c6df8c22358bacc8b3ed5e23912dcab805d54"
JJMIT_SHA256 = "19862d1fd1f1f44dfa1523848d7d3b5e2594a6c5da8fdd80144b449e5312a336"
MASKS = ("0000", "0001", "0010", "0100", "1000", "0011", "0111", "1100", "1110", "1111")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def rel(path: Path) -> str:
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
    raise ValueError(control)


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
    return labels


def required_probe_labels() -> list[str]:
    labels: list[str] = [
        f"I(I_{control}{instance})"
        for instance in range(1, 5)
        for control in ("WL", "BL", "SE")
    ]
    for instance in range(1, 5):
        labels.extend(per_bvm_probe_labels(instance))
    labels.append("V(COMMON_SL)")
    for index in range(1, 13):
        name = f"B_COL_LOAD{index:02d}"
        labels.extend((f"P({name})", f"V({name})", f"I({name})"))
    return list(dict.fromkeys(labels))


def print_block(labels: list[str], width: int = 10) -> str:
    return "\n".join(".print " + " ".join(labels[index:index + width]) for index in range(0, len(labels), width))


def deck_text(mask: str) -> str:
    active_comments = ", ".join(f"BVM{index}" for index in range(1, 5) if bit(mask, index)) or "none"
    lines = [
        f"* GENERATED PAPERLIKE COMMON-SL DECK: mask={mask}",
        "* source_class=HISTORICAL_BVMSIM_JM2_CONNECTED_VARIANT",
        "* all four BVMs are initialized to stored-1111; only final READ WL+SE follows mask",
        "* topology change: each internal BVM RSL/LSL terminates directly on COMMON_SL",
        "* exactly one shared twelve-junction 500-uA load; no QB/JTL/termination",
        f"* final READ active BVMs: {active_comments}",
        "",
        ".include ../../../../../circuits/models/jjmit.cir",
        ".include ../../../bvmsim-jm2-connected-single-ab-v1-20260903/variants/bvm_jm2_connected.cir",
        "",
        "XBVM1 WL1 BL1 SE1 COMMON_SL BVM",
        "XBVM2 WL2 BL2 SE2 COMMON_SL BVM",
        "XBVM3 WL3 BL3 SE3 COMMON_SL BVM",
        "XBVM4 WL4 BL4 SE4 COMMON_SL BVM",
        "",
        "* One common column load; jjmit base Ic=100uA and area=5.0 => Ic=500uA.",
    ]
    for index in range(1, 13):
        first = "COMMON_SL" if index == 1 else f"COL{index - 1:02d}"
        second = "0" if index == 12 else f"COL{index:02d}"
        lines.append(f"B_COL_LOAD{index:02d} {first} {second} jjmit area=5.0")
    lines.extend(("",))
    for instance in range(1, 5):
        lines.extend((source_line(instance, "WL", active=bit(mask, instance)),
                      source_line(instance, "BL"),
                      source_line(instance, "SE", active=bit(mask, instance))))
    lines.extend(("", ".tran 0.1p 200p 45p", "", "* Controls and complete per-BVM branch schema", print_block(required_probe_labels()), ".end", ""))
    return "\n".join(lines)


def validate_deck(mask: str, text: str) -> None:
    active_lines = [line.strip() for line in text.splitlines() if line.strip() and not line.lstrip().startswith("*")]
    if active_lines.count(".end") != 1:
        raise RuntimeError(f"{mask}: expected one .end")
    if ".tran 0.1p 200p 45p" not in active_lines:
        raise RuntimeError(f"{mask}: timestep/stop/output-start changed")
    if any("circuits/bvm/bvm_cell.cir" in line for line in text.splitlines()):
        raise RuntimeError(f"{mask}: canonical BVM included")
    forbidden_patterns = (
        r"\bB_LD", r"\bBVMout\b", r"\bBQ\b", r"\bQB", r"\bjtl\b", r"\bJTL",
        r"\bxjtl", r"\bRBQ", r"\bSL[1-4]\b", r"\bnld",
    )
    active_text = "\n".join(active_lines)
    for pattern in forbidden_patterns:
        if re.search(pattern, active_text, flags=re.IGNORECASE):
            raise RuntimeError(f"{mask}: forbidden topology token matched {pattern}")
    instances = [line.split() for line in active_lines if line.startswith("XBVM")]
    expected_instances = [[f"XBVM{i}", f"WL{i}", f"BL{i}", f"SE{i}", "COMMON_SL", "BVM"] for i in range(1, 5)]
    if instances != expected_instances:
        raise RuntimeError(f"{mask}: BVM connectivity mismatch: {instances}")
    loads = [tokens for tokens in (line.split() for line in active_lines) if tokens and tokens[0].startswith("B_COL_LOAD")]
    if len(loads) != 12:
        raise RuntimeError(f"{mask}: expected exactly 12 shared load elements")
    expected_loads = []
    for index in range(1, 13):
        first = "COMMON_SL" if index == 1 else f"COL{index - 1:02d}"
        second = "0" if index == 12 else f"COL{index:02d}"
        expected_loads.append([f"B_COL_LOAD{index:02d}", first, second, "jjmit", "area=5.0"])
    if loads != expected_loads:
        raise RuntimeError(f"{mask}: common-load stack mismatch: {loads}")
    printed = [token for line in text.splitlines() if line.strip().lower().startswith(".print") for token in line.split()[1:]]
    if len(printed) != len(set(printed)):
        duplicates = sorted({label for label in printed if printed.count(label) > 1})
        raise RuntimeError(f"{mask}: duplicate probes: {duplicates}")
    required = required_probe_labels()
    missing = sorted(set(required) - set(printed))
    if missing:
        raise RuntimeError(f"{mask}: missing probes: {missing}")
    for instance in range(1, 5):
        for control in ("WL", "BL", "SE"):
            prefix = f"I_{control}{instance} "
            lines = [line for line in text.splitlines() if line.startswith(prefix)]
            if len(lines) != 1:
                raise RuntimeError(f"{mask}: source count mismatch for {prefix}")
    for instance in range(1, 5):
        wl = next(line for line in text.splitlines() if line.startswith(f"I_WL{instance} "))
        se = next(line for line in text.splitlines() if line.startswith(f"I_SE{instance} "))
        expected = "100u" if bit(mask, instance) else "0"
        if f"111p {expected} 120p {expected}" not in wl or f"111p {expected} 120p {expected}" not in se:
            raise RuntimeError(f"{mask}: final READ mask mismatch for BVM{instance}")


def current_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()


def live_timestamp() -> str:
    return subprocess.check_output(["date", "--iso-8601=seconds"], text=True).strip()


def provenance(records: dict[str, dict[str, object]], head: str) -> dict[str, object]:
    source_paths = {
        "template_deck": TEMPLATE,
        "jm2_connected_bvm_variant": VARIANT,
        "shared_jjmit_model": SHARED_JJMIT,
        "canonical_bvm_not_used": CANONICAL_BVM,
        "solver": SOLVER,
        "old_distributed_reference": OLD_DISTRIBUTED / "analysis/metrics.json",
    }
    return {
        "schema": "bvmsim-paperlike-common-sl-provenance-v1",
        "experiment_id": EXP.name,
        "created_at_local": live_timestamp(),
        "head_before_setup": head,
        "authorized_head": head,
        "source_class": "HISTORICAL_BVMSIM_JM2_CONNECTED_VARIANT",
        "source_records": {
            name: {"path": rel(path), "sha256": sha256(path)}
            for name, path in source_paths.items()
            if path.is_file()
        },
        "expected_reference_hashes": {
            "template_deck": TEMPLATE_SHA256,
            "jm2_connected_bvm_variant": VARIANT_SHA256,
            "shared_jjmit_model": JJMIT_SHA256,
        },
        "authorized_topology_delta": {
            "from": "four distributed per-BVM sensing chains with historical terminal section",
            "to": "four BVM internal RSL/LSL endpoints on COMMON_SL plus one shared 12-JJ stack",
            "bvm_internal_physics_changed": False,
            "external_rsl_added": False,
            "per_cell_load_added": False,
            "daisy_segment_retained": False,
            "qb_or_jtl_present": False,
        },
        "shared_load_derivation": {
            "model": "circuits/models/jjmit.cir:jjmit",
            "base_ic_uA": 100.0,
            "area": 5.0,
            "effective_ic_uA": 500.0,
            "all_twelve_identical": True,
        },
        "deck_records": records,
        "canonical_bvm_statement": "circuits/bvm/bvm_cell.cir is preserved as a boundary reference and was not included",
        "phase_statement": "JoSIM P is radians; continuous phase turns are derived only as continuous_unwrap(P)/(2*pi)",
        "event_statement": "No phase displacement or voltage area is used as an SFQ count",
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
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    for path in (TEMPLATE, VARIANT, SHARED_JJMIT, CANONICAL_BVM, SOLVER, OLD_DISTRIBUTED / "analysis/metrics.json"):
        if not path.is_file():
            raise RuntimeError(f"missing required source: {path}")
    if sha256(TEMPLATE) != TEMPLATE_SHA256:
        raise RuntimeError("accepted no-history template hash changed")
    if sha256(VARIANT) != VARIANT_SHA256 or sha256(SHARED_JJMIT) != JJMIT_SHA256:
        raise RuntimeError("frozen BVM/model source hash changed")
    head = current_head()
    expected_head = "9b89b95e0e43c3a21571d67db4cf98b46d9bea90"
    if head != expected_head:
        raise RuntimeError(f"unexpected setup HEAD: {head}; expected {expected_head}")
    records: dict[str, dict[str, object]] = {}
    contents: dict[str, str] = {}
    for mask in MASKS:
        content = deck_text(mask)
        validate_deck(mask, content)
        target = EXP / "runs" / mask / "deck.cir"
        contents[mask] = content
        records[mask] = {
            "path": rel(target),
            "sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
            "mask": mask,
            "active_bvms": [instance for instance in range(1, 5) if bit(mask, instance)],
        }
    if args.check_only:
        print(json.dumps({"status": "PASS", "writes": False, "masks": list(MASKS)}, ensure_ascii=False))
        return 0
    for mask, content in contents.items():
        write_once(EXP / "runs" / mask / "deck.cir", content)
    write_once(EXP / "provenance.json", json.dumps(provenance(records, head), indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"status": "PASS", "writes": True, "masks": list(MASKS)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
