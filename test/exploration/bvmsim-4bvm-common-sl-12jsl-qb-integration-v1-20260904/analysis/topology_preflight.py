#!/usr/bin/env python3
"""Static, hash-bound preflight for the common-SL receiver integration.

This checker intentionally operates on netlist text and source hashes only.
It does not run JoSIM and it does not make a physical claim.  The purpose is
to prove that the receiver experiment differs from the accepted passive
fixture only at the explicitly authorized JSL12 downstream boundary and by
the frozen receiver chain added after that boundary.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


SCRIPT = Path(__file__).resolve()
EXP = SCRIPT.parents[1]
REPO = SCRIPT.parents[4]
PASSIVE = REPO / "test/exploration/bvmsim-4bvm-paperlike-common-sl-accumulation-isolation-v1-20260904"
BVM_VARIANT = REPO / "test/exploration/bvmsim-jm2-connected-single-ab-v1-20260903/variants/bvm_jm2_connected.cir"
BQ = REPO / "BVMSim/BQ.cir"
JTL = REPO / "BVMSim/library_josim/jtl2.cir"
SHARED_JJMIT = REPO / "circuits/models/jjmit.cir"
CANONICAL_BVM = REPO / "circuits/bvm/bvm_cell.cir"
MASKS = ("0000", "0001", "0010", "0100", "1000", "0011", "0111", "1100", "1110", "1111")
BASE_HEAD = "a58bbb3b566b466110bccda8f89fc36c4ce2d368"
PASSIVE_TEMPLATE_SHA256 = "4159a81074053eabd310f08e955953a12d412e00e9bb9d4cc0ebbc7512c9bef6"
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


def now_local() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def active_lines(path: Path) -> list[str]:
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("*")
    ]


def active_lines_text(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip() and not line.lstrip().startswith("*")]


def load_generator():
    path = EXP / "generate_decks.py"
    spec = importlib.util.spec_from_file_location("common_sl_qb_generator", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load generator: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def current_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()


def git_status() -> list[str]:
    output = subprocess.check_output(["git", "status", "--porcelain"], cwd=REPO, text=True)
    return [line for line in output.splitlines() if line]


def require(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def parse_junction(line: str) -> tuple[str, str, str, str, str]:
    tokens = line.split()
    if len(tokens) != 6 or tokens[0].startswith("*"):
        raise RuntimeError(f"unexpected JJ line: {line}")
    # name, node+, node-, model, area=..., with the element prefix retained
    return tokens[0], tokens[1], tokens[2], tokens[3], tokens[4]


def parsed_junction(line: str) -> tuple[str, str, str, str]:
    tokens = line.split()
    if len(tokens) != 5:
        raise RuntimeError(f"unexpected JSL line: {line}")
    return tokens[1], tokens[2], tokens[3], tokens[4]


def expected_sources(passive_deck: Path) -> list[str]:
    lines = active_lines(passive_deck)
    return [line for line in lines if line.startswith(("I_WL", "I_BL", "I_SE"))]


def source_paths() -> dict[str, Path]:
    return {
        "jm2_connected_bvm_variant": BVM_VARIANT,
        "bvmsim_bq": BQ,
        "bvmsim_jtl": JTL,
        "shared_jjmit": SHARED_JJMIT,
        "canonical_bvm_not_used": CANONICAL_BVM,
        "passive_template_deck": PASSIVE / "runs/1111/deck.cir",
    }


def check_sources(failures: list[str]) -> dict[str, object]:
    hashes: dict[str, str] = {}
    for name, path in source_paths().items():
        require(path.is_file(), f"missing source: {rel(path)}", failures)
        if path.is_file():
            hashes[name] = sha256(path)
    for name, key in (
        ("jm2_connected_bvm_variant", "bvm_variant"),
        ("bvmsim_bq", "bq"),
        ("bvmsim_jtl", "jtl"),
        ("shared_jjmit", "shared_jjmit"),
    ):
        if name in hashes:
            require(hashes[name] == EXPECTED_HASHES[key], f"{name} hash changed: {hashes[name]}", failures)
    if "passive_template_deck" in hashes:
        require(
            hashes["passive_template_deck"] == PASSIVE_TEMPLATE_SHA256,
            f"passive template hash changed: {hashes['passive_template_deck']}",
            failures,
        )
    return hashes


def check_fixture(mask: str, generator, provenance: dict[str, object], failures: list[str]) -> dict[str, object]:
    new_path = EXP / "runs" / mask / "deck.cir"
    old_path = PASSIVE / "runs" / mask / "deck.cir"
    require(new_path.is_file(), f"{mask}: missing new deck", failures)
    require(old_path.is_file(), f"{mask}: missing passive deck", failures)
    if not new_path.is_file() or not old_path.is_file():
        return {"mask": mask, "status": "MISSING"}

    new_lines = active_lines(new_path)
    old_lines = active_lines(old_path)
    new_hash = sha256(new_path)
    record = (provenance.get("deck_records") or {}).get(mask, {})
    require(new_hash == record.get("sha256"), f"{mask}: deck hash does not match provenance", failures)
    require(new_lines.count(".end") == 1, f"{mask}: expected one .end", failures)
    require(".tran 0.1p 200p 45p" in new_lines, f"{mask}: .tran changed", failures)
    require(new_lines.count(".tran 0.1p 200p 45p") == 1, f"{mask}: duplicate .tran", failures)

    bvm_rows = [line for line in new_lines if line.startswith("XBVM")]
    expected_bvm = [f"XBVM{i} WL{i} BL{i} SE{i} COMMON_SL BVM" for i in range(1, 5)]
    require(bvm_rows == expected_bvm, f"{mask}: BVM topology differs from common-SL fixture", failures)
    old_bvm_rows = [line for line in old_lines if line.startswith("XBVM")]
    require(old_bvm_rows == expected_bvm, f"{mask}: passive BVM topology is not expected reference", failures)

    old_sources = expected_sources(old_path)
    new_sources = [line for line in new_lines if line.startswith(("I_WL", "I_BL", "I_SE"))]
    require(new_sources == old_sources, f"{mask}: stimulus differs from passive same-mask deck", failures)

    old_jsl = [line for line in old_lines if line.startswith("B_COL_LOAD")]
    new_jsl = [line for line in new_lines if line.startswith("B_JSL")]
    require(len(old_jsl) == 12, f"{mask}: passive JSL count is not 12", failures)
    require(len(new_jsl) == 12, f"{mask}: new JSL count is not 12", failures)
    jsl_boundary_change = False
    for index, (old, new) in enumerate(zip(old_jsl, new_jsl), start=1):
        old_parsed = parsed_junction(old.replace(old.split()[0], "JSL", 1))
        new_parsed = parsed_junction(new.replace(new.split()[0], "JSL", 1))
        if index < 12:
            require(new_parsed == old_parsed, f"{mask}: JSL{index:02d} upstream chain changed", failures)
        else:
            expected_new = (old_parsed[0], "QBIN", old_parsed[2], old_parsed[3])
            require(new_parsed == expected_new, f"{mask}: JSL12 boundary is not COL11 -> QBIN", failures)
            jsl_boundary_change = old_parsed[1] == "0" and new_parsed[1] == "QBIN"
    require(jsl_boundary_change, f"{mask}: authorized JSL12 GND -> QBIN change not isolated", failures)

    receiver = [line for line in new_lines if line.startswith(("XBQ1", "xjtl1_", "R_TERM"))]
    expected_receiver = [
        "XBQ1 QBIN QBOUT BQ",
        "xjtl1_1 QBOUT JTL1_OUT jtl",
        "xjtl1_2 JTL1_OUT JTL2_OUT jtl",
        "xjtl1_3 JTL2_OUT JTL3_OUT jtl",
        "xjtl1_4 JTL3_OUT JTL4_OUT jtl",
        "xjtl1_5 JTL4_OUT JTL5_OUT jtl",
        "xjtl1_6 JTL5_OUT JTL6_OUT jtl",
        "R_TERM JTL6_OUT 0 10",
    ]
    require(receiver == expected_receiver, f"{mask}: receiver chain changed", failures)

    includes = [line for line in new_lines if line.lower().startswith(".include")]
    for required in (
        "../../../../../circuits/models/jjmit.cir",
        "../../../bvmsim-jm2-connected-single-ab-v1-20260903/variants/bvm_jm2_connected.cir",
        "../../../../../BVMSim/BQ.cir",
        "../../../../../BVMSim/library_josim/jtl2.cir",
    ):
        require(any(required in line for line in includes), f"{mask}: missing include {required}", failures)

    forbidden_prefixes = ("B_COL_LOAD", "B_LD", "BVMout", "R_SL")
    stale = [line for line in new_lines if line.startswith(forbidden_prefixes)]
    require(not stale, f"{mask}: stale load/RSL topology remains: {stale}", failures)
    stale_tokens = [
        line
        for line in new_lines
        if any(token.lower() in {"sl1", "sl2", "sl3", "sl4", "nld"} for token in line.split())
    ]
    require(not stale_tokens, f"{mask}: stale daisy/distributed-network token remains: {stale_tokens}", failures)
    require(sum(line.startswith("R_TERM ") for line in new_lines) == 1, f"{mask}: termination count is not one", failures)
    require(sum(line.startswith("XBQ1 ") for line in new_lines) == 1, f"{mask}: BQ count is not one", failures)
    require(sum(line.startswith("xjtl1_") for line in new_lines) == 6, f"{mask}: JTL count is not six", failures)

    printed = [
        token
        for line in new_path.read_text(encoding="utf-8").splitlines()
        if line.strip().lower().startswith(".print")
        for token in line.split()[1:]
    ]
    required_probes = generator.required_probe_labels()
    require(len(printed) == len(set(printed)), f"{mask}: duplicate probes", failures)
    missing = sorted(set(required_probes) - set(printed))
    require(not missing, f"{mask}: missing probes: {missing}", failures)

    # The only normalized active-topology difference allowed before the
    # receiver is the JSL12 endpoint.  BVM rows and stimulus are compared
    # exactly above; the model/area/order checks are explicit here too.
    normalized_old = [(parsed_junction(line.replace(line.split()[0], "JSL", 1))) for line in old_jsl]
    normalized_new = [(parsed_junction(line.replace(line.split()[0], "JSL", 1))) for line in new_jsl]
    upstream_diff = [index for index, (old, new) in enumerate(zip(normalized_old, normalized_new), start=1) if old[0:1] != new[0:1] or old[2:] != new[2:]]
    require(not upstream_diff, f"{mask}: unclassified JSL model/area/upstream changes: {upstream_diff}", failures)

    return {
        "mask": mask,
        "new_deck_sha256": new_hash,
        "passive_deck_sha256": sha256(old_path),
        "bvm_rows_identical": bvm_rows == old_bvm_rows,
        "stimulus_identical": new_sources == old_sources,
        "jsl_count_new": len(new_jsl),
        "authorized_boundary": "B_JSL12 COL11 0 -> COL11 QBIN",
        "upstream_unclassified_change_count": len(upstream_diff),
        "receiver_instance_count": {"bq": 1, "jtl": 6, "termination": 1},
        "probe_count": len(printed),
        "status": "PASS",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-only", action="store_true", help="validate the frozen preflight JSON without rewriting it")
    parser.add_argument("--require-clean", action="store_true", help="require a clean git worktree")
    args = parser.parse_args()

    failures: list[str] = []
    if args.require_clean:
        status = git_status()
        require(not status, f"working tree is not clean: {status}", failures)

    provenance_path = EXP / "provenance.json"
    require(provenance_path.is_file(), "missing experiment provenance.json", failures)
    provenance: dict[str, object] = {}
    if provenance_path.is_file():
        provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
        require(provenance.get("base_head_expected") == BASE_HEAD, "provenance base HEAD changed", failures)
        require(provenance.get("canonical_bvm_used") is False, "canonical BVM is marked used", failures)

    hashes = check_sources(failures)
    generator = load_generator()
    run_records = [check_fixture(mask, generator, provenance, failures) for mask in MASKS]

    # Confirm that the frozen source subcircuits are the intended historical
    # interfaces, without normalizing or rewriting their files.
    bq_lines = active_lines(BQ) if BQ.is_file() else []
    jtl_lines = active_lines(JTL) if JTL.is_file() else []
    require(sum(line.lower().startswith(".subckt bq ") for line in bq_lines) == 1, "BVMSim/BQ.cir BQ interface is not exactly BQ IN OUT", failures)
    require(any(line.lower().startswith(".subckt bq in out") for line in bq_lines), "BVMSim/BQ.cir active interface changed", failures)
    require(sum(line.lower().startswith(".subckt jtl ") for line in jtl_lines) == 1, "BVMSim JTL interface is not exactly one jtl subckt", failures)
    require(any(line.lower().startswith(".subckt jtl 4 5") for line in jtl_lines), "BVMSim JTL interface changed", failures)
    require(any(line.startswith("IB ") for line in bq_lines), "BVMSim BQ bias source missing", failures)
    require(any(line.startswith("IB01 ") for line in jtl_lines), "BVMSim JTL bias source missing", failures)

    report = {
        "schema": "common-sl-12jsl-qb-topology-preflight-v1",
        "experiment_id": EXP.name,
        "created_at_local": now_local(),
        "head_at_check": current_head(),
        "base_head_expected": BASE_HEAD,
        "source_sha256": hashes,
        "canonical_bvm_used": False,
        "authorized_change": {
            "old": "COMMON_SL -> B_JSL01..12 -> GND",
            "new": "COMMON_SL -> same B_JSL01..12 -> QBIN -> BQ -> JTL1..6 -> R_TERM(10 ohm)",
            "only_boundary_change": "B_JSL12 COL11 0 -> COL11 QBIN",
        },
        "checks": {
            "mask_count": len(run_records),
            "masks": list(MASKS),
            "all_fixture_checks_pass": not failures,
            "upstream_unclassified_change_count": sum(int(row.get("upstream_unclassified_change_count", 1)) for row in run_records),
            "receiver_counts": {"BQ": 1, "JTL": 6, "R_TERM": 1},
            "probe_schema_from_generator": len(generator.required_probe_labels()),
            "frozen_bq_interface": ".subckt BQ IN OUT",
            "frozen_jtl_interface": ".subckt jtl 4 5",
            "stimulus_and_tran_frozen": not failures,
        },
        "run_records": run_records,
        "status": "PASS" if not failures else "FAIL",
        "failures": failures,
    }

    output = EXP / "analysis" / "topology_preflight.json"
    if args.check_only:
        require(output.is_file(), f"missing frozen preflight output: {rel(output)}", failures)
        if output.is_file():
            frozen = json.loads(output.read_text(encoding="utf-8"))
            require(frozen.get("status") == "PASS", "frozen topology preflight was not PASS", failures)
            require(frozen.get("checks", {}).get("mask_count") == len(MASKS), "frozen mask count changed", failures)
            require(frozen.get("checks", {}).get("upstream_unclassified_change_count") == 0, "frozen upstream diff is nonzero", failures)
            for row in frozen.get("run_records", []):
                mask = row.get("mask")
                if mask in MASKS:
                    current = next(item for item in run_records if item.get("mask") == mask)
                    require(row.get("new_deck_sha256") == current.get("new_deck_sha256"), f"{mask}: frozen deck hash changed", failures)
            report["status"] = "PASS" if not failures else "FAIL"
            report["failures"] = failures
        if failures:
            print(json.dumps({"status": "FAIL", "failures": failures}, ensure_ascii=False))
            return 1
        print(json.dumps({"status": "PASS", "check_only": True, "head": current_head()}, ensure_ascii=False))
        return 0

    if failures:
        report["status"] = "FAIL"
        output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps({"status": "FAIL", "failures": failures}, ensure_ascii=False))
        return 1
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "output": rel(output), "mask_count": len(MASKS)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
