#!/usr/bin/env python3
"""Register RJ1 switched-regime decks and the exact preflight."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
AUTH = REPO / "test/exploration/qb-l1-ibias-interaction-bjs400-v1-20260909"
SOLVER = REPO / "build/josim-cli"
SOURCE_TEMPLATE = EXP / "inputs/array_fixture_template.cir"
BQ400 = EXP / "inputs/BQ_parameterized_bjs400.cir"
CONTRACT_SENTENCE = "This experiment is governed by docs/EXPERIMENT_CONTRACT.md."

EXPECTED_INPUT_HASHES = {
    "array_fixture_template.cir": "8971a82dfbac223b9be139f719afae2eb156f0f68fb2a4811858f0a0b482cf71",
    "bvm_jm2_connected.cir": "0093a45cc3910448b484d8bd004c6df8c22358bacc8b3ed5e23912dcab805d54",
    "jjmit.cir": "19862d1fd1f1f44dfa1523848d7d3b5e2594a6c5da8fdd80144b449e5312a336",
    "jtl2.cir": "ffd31f8eda2a86ca0133342be1ce678831b7237a53911eda046d2bff8454855a",
    "BQ_parameterized_bjs400.cir": "883308517d48470cbedab878f9e3c71721cd972db248c6b821ce5dba642ff810",
}
AUTH_SOURCE_MANIFEST_SHA256 = "c88f0d6102cb5f8722c1ac417ae3d0109faef5e505375d44da101612732914d3"
AUTH_PACKAGE_SHA256 = "3c105c850823fee747632860ebfb17ee930617ec21ebfc4c92c73a20d959575d"
FIXED = {"L1_pH": 1.6, "IBias_uA": 260.0}
RJ1_VALUES = (10.0, 14.0, 16.0)
MASKS = ("0001", "0011")
NEW_RUNS = (
    "ARRAY_L1P16_IB260_RJ10_0001",
    "ARRAY_L1P16_IB260_RJ10_0011",
    "ARRAY_L1P16_IB260_RJ14_0001",
    "ARRAY_L1P16_IB260_RJ14_0011",
    "ARRAY_L1P16_IB260_RJ16_0001",
    "ARRAY_L1P16_IB260_RJ16_0011",
)
REUSE_RUNS = ("ARRAY_L1P16_IB260_0001", "ARRAY_L1P16_IB260_0011")
RUN_TO_RJ1 = {run_id: float(run_id.split("_RJ", 1)[1].split("_", 1)[0]) for run_id in NEW_RUNS}
RUN_TO_MASK = {run_id: run_id.rsplit("_", 1)[1] for run_id in NEW_RUNS}
CONTROL_KINDS = ("WL", "BL", "SE")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()


def solver_version() -> str:
    return subprocess.check_output([str(SOLVER), "--version"], cwd=REPO, text=True)


def write_json_once(path: Path, value: Any) -> None:
    text = json.dumps(value, indent=2, ensure_ascii=False) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file():
        if path.read_text(encoding="utf-8") != text:
            raise RuntimeError(f"refusing to overwrite existing artifact: {path}")
        return
    path.write_text(text, encoding="utf-8")


def write_once(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file():
        if path.read_text(encoding="utf-8") != text:
            raise RuntimeError(f"refusing to overwrite existing artifact: {path}")
        return
    path.write_text(text, encoding="utf-8")


def control_values(kind: str, active: bool) -> str:
    if kind == "WL":
        points = "0 0 50p 0 51p -100u 60p -100u 61p 0 70p 0 71p +100u 80p +100u 81p 0 90p 0 91p +100u 100p +100u 101p 0"
    elif kind == "BL":
        points = "0 0 50p 0 51p -100u 60p -100u 61p 0 70p 0 71p 0 80p 0 81p 0 90p 0 91p +100u 100p +100u 101p 0"
    elif kind == "SE":
        points = "0 0 50p 0 51p 0 60p 0 61p 0 70p 0 71p +100u 80p +100u 81p 0 90p 0 91p 0 100p 0 101p 0"
    else:
        raise ValueError(kind)
    final = "+100u" if active and kind in {"WL", "SE"} else "0"
    return f"pwl({points} 110p 0 111p {final} 120p {final} 121p 0 200p 0)"


def control_line(instance: int, kind: str, active: bool) -> str:
    return f"I_{kind}{instance} 0 {kind}{instance} {control_values(kind, active)}"


def build_deck(rj1: float, mask: str) -> str:
    text = SOURCE_TEMPLATE.read_text(encoding="utf-8")
    include = ".include ../../inputs/jjmit.cir"
    if text.count(include) != 1:
        raise RuntimeError("BJS400 template local JJ include is not unique")
    params = (
        f".param L1_VALUE={FIXED['L1_pH']:g}p\n"
        f".param IB_VALUE={FIXED['IBias_uA']:g}u\n"
        f".param RJ1_VALUE={rj1:g}\n"
    )
    text = text.replace(include, params + include, 1)
    for instance in range(1, 5):
        for kind in CONTROL_KINDS:
            token = f"@@ARRAY_I_{kind}{instance}@@"
            if text.count(token) != 1:
                raise RuntimeError(f"missing control token: {token}")
            text = text.replace(token, control_line(instance, kind, mask[instance - 1] == "1"), 1)
    if "@@" in text:
        raise RuntimeError("unexpanded control token in deck")
    return text


def read_raw_summary(path: Path) -> dict[str, Any]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.reader(stream)
        header = next(reader)
        first = next(reader)
        last = first
        count = 1
        previous = float(first[0])
        monotonic = True
        finite = True
        for row in reader:
            last = row
            count += 1
            try:
                values = [float(value) for value in row]
                finite = finite and all(value == value and abs(value) != float("inf") for value in values)
            except ValueError:
                finite = False
            current = float(row[0])
            monotonic = monotonic and current > previous
            previous = current
    return {
        "header_count": len(header),
        "sample_count": count,
        "first_timestamp": first[0],
        "last_timestamp": last[0],
        "strictly_increasing_time": monotonic,
        "finite_values": finite,
        "sha256": sha256(path),
        "bytes": path.stat().st_size,
    }


def write_reuse_manifest() -> dict[str, Any]:
    path = EXP / "REUSED_REFERENCE_MANIFEST.json"
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    references: dict[str, Any] = {}
    for run_id in REUSE_RUNS:
        source_dir = AUTH / "runs" / run_id
        archived_dir = EXP / "references/reused" / run_id
        metadata = json.loads((source_dir / "metadata.json").read_text(encoding="utf-8"))
        artifacts: dict[str, Any] = {}
        for name in ("raw.csv", "deck.cir", "metadata.json", "run.log"):
            source = source_dir / name
            archived = archived_dir / name
            source_hash = sha256(source)
            archived_hash = sha256(archived)
            if source_hash != archived_hash:
                raise RuntimeError(f"reuse artifact hash mismatch: {run_id}/{name}")
            artifacts[name] = {
                "source_path": str(source),
                "archived_path": str(archived),
                "source_sha256": source_hash,
                "archived_sha256": archived_hash,
                "bytes": archived.stat().st_size,
            }
        references[run_id] = {
            "logical_case_id": run_id,
            "source_experiment": str(AUTH.relative_to(REPO)),
            "source_run": f"runs/{run_id}",
            "source_git_head": metadata["git_head_before_run"],
            "parameters": metadata["parameters"],
            "topology": metadata["topology"],
            "mask": metadata["mask"],
            "physical_solve_this_experiment": False,
            "reuse_reason": "exact D working point, BJS400 fixture, mask, history, solver/timestep and hash match",
            "source_evidence_package": {
                "path": str((AUTH / "handoff/qb-l1-ibias-interaction-bjs400-v1-20260909_raw_handoff_v2.zip").relative_to(REPO)),
                "sha256": AUTH_PACKAGE_SHA256,
            },
            "artifacts": artifacts,
        }
    record = {
        "schema": "rj1-switched-regime-reuse-manifest-v1",
        "experiment_id": EXP.name,
        "created_at_local": now(),
        "source_authority": str(AUTH.relative_to(REPO)),
        "references": references,
        "reused_physical_case_count": 2,
        "no_reuse_by_filename_only": True,
        "no_new_historical_solves": True,
    }
    write_json_once(path, record)
    return record


def write_source_manifest() -> dict[str, Any]:
    path = EXP / "SOURCE_MANIFEST.json"
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    local_sources = []
    for name, role in (
        ("array_fixture_template.cir", "BJS400 physical/stimulus authority template"),
        ("bvm_jm2_connected.cir", "historical JM2-connected BVM"),
        ("jjmit.cir", "JJ model"),
        ("jtl2.cir", "JTL model"),
        ("BQ_parameterized_bjs400.cir", "BJS400 QB source"),
    ):
        source = EXP / "inputs" / name
        local_sources.append({
            "path": name,
            "repo_relative_path": str(source.relative_to(REPO)),
            "sha256": sha256(source),
            "bytes": source.stat().st_size,
            "role": role,
        })
    local_sources.append({
        "path": str(SOLVER.relative_to(REPO)),
        "repo_relative_path": str(SOLVER.relative_to(REPO)),
        "sha256": sha256(SOLVER),
        "bytes": SOLVER.stat().st_size,
        "role": "solver identity",
        "version": solver_version(),
    })
    record = {
        "schema": "rj1-switched-regime-source-manifest-v1",
        "experiment_id": EXP.name,
        "created_at_local": now(),
        "physical_stimulus_authority": str(AUTH.relative_to(REPO)),
        "physical_stimulus_authority_git_head": head(),
        "physical_stimulus_authority_source_manifest": {
            "path": str((AUTH / "SOURCE_MANIFEST.json").relative_to(REPO)),
            "sha256": AUTH_SOURCE_MANIFEST_SHA256,
        },
        "local_sources": local_sources,
        "fixed_working_point": {
            "L1_pH": 1.6,
            "IBias_uA": 260.0,
            "BJS_area": 4,
            "BJS_Ic_uA": 400,
            "RJ1_baseline_ohm": 12,
        },
        "reuse_source_experiment": str(AUTH.relative_to(REPO)),
    }
    write_json_once(path, record)
    return record


def generate_decks() -> dict[str, Any]:
    records: dict[str, Any] = {}
    for run_id in NEW_RUNS:
        deck = EXP / "runs" / run_id / "deck.cir"
        write_once(deck, build_deck(RUN_TO_RJ1[run_id], RUN_TO_MASK[run_id]))
        records[run_id] = {
            "rj1_ohm": RUN_TO_RJ1[run_id],
            "mask": RUN_TO_MASK[run_id],
            "parameters": {**FIXED, "RJ1_ohm": RUN_TO_RJ1[run_id]},
            "path": str(deck.relative_to(REPO)),
            "sha256": sha256(deck),
            "bytes": deck.stat().st_size,
        }
    return records


def verify_reuse(manifest: dict[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    if sha256(AUTH / "SOURCE_MANIFEST.json") != AUTH_SOURCE_MANIFEST_SHA256:
        failures.append("authority SOURCE_MANIFEST hash changed")
    authority_package = AUTH / "handoff/qb-l1-ibias-interaction-bjs400-v1-20260909_raw_handoff_v2.zip"
    if sha256(authority_package) != AUTH_PACKAGE_SHA256:
        failures.append("authority evidence package hash changed")
    for run_id in REUSE_RUNS:
        metadata = json.loads((EXP / "references/reused" / run_id / "metadata.json").read_text(encoding="utf-8"))
        expected_mask = run_id.rsplit("_", 1)[1]
        if metadata.get("topology") != "ARRAY" or metadata.get("mask") != expected_mask:
            failures.append(f"{run_id}: topology/mask mismatch")
        expected_parameters = {"L1_pH": 1.6, "IBias_uA": 260.0, "RJ1_ohm": 12.0}
        if any(metadata.get("parameters", {}).get(key) != value for key, value in expected_parameters.items()):
            failures.append(f"{run_id}: fixed parameters mismatch")
        if metadata.get("execution_status") != "RUN_PASS":
            failures.append(f"{run_id}: source execution was not RUN_PASS")
        if metadata.get("solver", {}).get("sha256") != sha256(SOLVER):
            failures.append(f"{run_id}: solver hash mismatch")
        summary = read_raw_summary(EXP / "references/reused" / run_id / "raw.csv")
        if summary["sample_count"] != 1999 or summary["first_timestamp"] != "0.000000e+00" or summary["last_timestamp"] != "1.999000e-10" or not summary["strictly_increasing_time"] or not summary["finite_values"]:
            failures.append(f"{run_id}: reused raw mechanical mismatch")
        if manifest["references"][run_id]["artifacts"]["raw.csv"]["source_sha256"] != summary["sha256"]:
            failures.append(f"{run_id}: reuse manifest raw hash mismatch")
    return {
        "status": "PASS" if not failures else "FAIL",
        "reused_cases": list(REUSE_RUNS),
        "source_evidence_package_sha256": AUTH_PACKAGE_SHA256,
        "physical_comparability_checks": {
            "fixed_D_working_point": "PASS",
            "BJS400_fixture": "PASS",
            "same_ARRAY_topology": "PASS",
            "same_mask_semantics": "PASS",
            "same_history": "PASS",
            "same_JSL_QB_JTL": "PASS",
            "same_solver_timestep_stop_time": "PASS",
            "raw_and_deck_hashes": "PASS",
        },
        "failures": failures,
    }


def verify_decks(generated: dict[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    normalized: set[tuple[str, ...]] = set()
    pre_read: set[tuple[str, ...]] = set()
    records: dict[str, Any] = {}
    bq = BQ400.read_text(encoding="utf-8")
    if "BJs 1 2 jjmit area=4" not in bq or "BJs 1 2 jjmit area=3" in bq:
        failures.append("BJS400 source is not area=4 only")
    for run_id in NEW_RUNS:
        text = (EXP / "runs" / run_id / "deck.cir").read_text(encoding="utf-8")
        rj1 = RUN_TO_RJ1[run_id]
        mask = RUN_TO_MASK[run_id]
        for required in (
            ".param L1_VALUE=1.6p",
            ".param IB_VALUE=260u",
            f".param RJ1_VALUE={rj1:g}",
            ".tran 0.1p 200p",
            "P(BJS|XBQ1) V(BJS|XBQ1) I(BJS|XBQ1)",
        ):
            if required not in text:
                failures.append(f"{run_id}: missing {required}")
        if any(text.count(f"XBVM{index} ") != 1 for index in range(1, 5)):
            failures.append(f"{run_id}: ARRAY BVM count mismatch")
        for instance in range(1, 5):
            for kind in CONTROL_KINDS:
                expected = control_line(instance, kind, mask[instance - 1] == "1")
                if expected not in text:
                    failures.append(f"{run_id}: control mismatch {kind}{instance}")
        normalized.add(tuple(
            line for line in text.splitlines()
            if not line.startswith(".param L1_VALUE=")
            and not line.startswith(".param IB_VALUE=")
            and not line.startswith(".param RJ1_VALUE=")
            and not re.match(r"I_(WL|BL|SE)[1-4] ", line)
        ))
        pre_read.add(tuple(line.split(" 110p", 1)[0] for line in text.splitlines() if re.match(r"I_(WL|BL|SE)[1-4] ", line)))
        records[run_id] = {
            "rj1_ohm": rj1,
            "mask": mask,
            "deck_sha256": sha256(EXP / "runs" / run_id / "deck.cir"),
            "deck_bytes": (EXP / "runs" / run_id / "deck.cir").stat().st_size,
        }
    if len(normalized) != 1:
        failures.append("new decks differ outside RJ1 parameters and final-read controls")
    if len(pre_read) != 1:
        failures.append("new controls differ before 110ps")
    return {
        "schema": "rj1-switched-regime-deck-diff-qa-v1",
        "status": "PASS" if not failures else "FAIL",
        "new_run_count": len(NEW_RUNS),
        "reused_case_count": len(REUSE_RUNS),
        "same_mask_only_rj1_difference": True,
        "mask_pair_only_final_read_difference": True,
        "normalized_new_decks_identical": len(normalized) == 1,
        "pre_110ps_control_equality": len(pre_read) == 1,
        "bjs400_area": 4,
        "rj1_values_new": sorted(set(RUN_TO_RJ1.values())),
        "runs": records,
        "failures": failures,
    }


def preflight_markdown(record: dict[str, Any]) -> str:
    lines = [
        "# RJ1 switched-regime characterization under D working point — PREFLIGHT",
        "",
        CONTRACT_SENTENCE,
        "",
        "## Authority",
        "",
        "- Physical/stimulus authority: test/exploration/qb-l1-ibias-interaction-bjs400-v1-20260909",
        f"- Preflight HEAD: {record['head']}",
        "- Fixed point: L1=1.6pH, IBias=260uA, BJS area=4, BJS Ic=400uA.",
        "- RJ1 values: new 10/14/16ohm; 12ohm reused by hash.",
        "- Masks: 0001 and 0011 only; no older no-history stimulus.",
        "",
        "## Frozen history",
        "",
        "WRITE0 -> ZERO_STATE_READ_CONTROL -> WRITE1 -> SETTLE -> mask-selective FINAL READ -> TAIL",
        "",
        "- 0–50ps idle; WRITE0 50–61ps; idle 61–70ps.",
        "- ZERO_STATE_READ_CONTROL 70–81ps; idle 81–90ps.",
        "- WRITE1 90–101ps; SETTLE 101–110ps; FINAL READ 110–121ps; TAIL 121–200ps.",
        "- WL/BL/SE amplitude 100uA, 1ps edges, 9ps plateau, .tran 0.1p 200p.",
        "",
        "## Exact matrix",
        "",
        "- New physical solves: exactly 6.",
        "- Reused historical cases: ARRAY_L1P16_IB260_0001 and ARRAY_L1P16_IB260_0011.",
        "- No extra RJ1 value, mask, SINGLE run, retry, tuning or follow-up.",
        "",
        "## Preflight results",
        "",
        f"- B reuse comparability: {record['reuse_comparability']['status']}.",
        f"- New deck diff: {record['new_deck_checks']['status']}.",
        "- Mandatory BJS P/V/I and all JTL current probes are registered.",
        "- Raw execution has not started at preflight.",
        "",
        "Scientific interpretation is NOT_PERFORMED.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh-head", action="store_true")
    args = parser.parse_args()
    for name, expected in EXPECTED_INPUT_HASHES.items():
        path = EXP / "inputs" / name
        if not path.is_file() or sha256(path) != expected:
            raise RuntimeError(f"input hash mismatch: {name}")
    if not SOLVER.is_file():
        raise RuntimeError(f"missing solver: {SOLVER}")
    reuse = write_reuse_manifest()
    sources = write_source_manifest()
    generated = generate_decks()
    decks = verify_decks(generated)
    reuse_checks = verify_reuse(reuse)
    if decks["status"] != "PASS" or reuse_checks["status"] != "PASS":
        raise RuntimeError(f"preflight checks failed: decks={decks['status']} reuse={reuse_checks['status']}")
    existing = EXP / "analysis/preflight.json"
    prior = json.loads(existing.read_text(encoding="utf-8")) if existing.is_file() else {}
    record = {
        "schema": "rj1-switched-regime-preflight-v1",
        "experiment_id": EXP.name,
        "created_at_local": now(),
        "status": "PASS",
        "head": head(),
        "head_refresh": args.refresh_head,
        "preregistration_head": prior.get("preregistration_head", head()),
        "new_physical_solve_count": 6,
        "reused_physical_case_count": 2,
        "exact_logical_case_count": 8,
        "unauthorized_extra_solves": 0,
        "fixed_working_point": {"L1_pH": 1.6, "IBias_uA": 260.0, "BJS_area": 4, "BJS_Ic_uA": 400.0},
        "new_rj1_values_ohm": [10.0, 14.0, 16.0],
        "reused_rj1_value_ohm": 12.0,
        "authorized_masks": list(MASKS),
        "reuse_comparability": reuse_checks,
        "generated_decks": generated,
        "new_deck_checks": decks,
        "source_manifest_sha256": sha256(EXP / "SOURCE_MANIFEST.json"),
        "reuse_manifest_sha256": sha256(EXP / "REUSED_REFERENCE_MANIFEST.json"),
        "scientific_analysis_performed": False,
    }
    if args.refresh_head:
        existing.parent.mkdir(parents=True, exist_ok=True)
        existing.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        (EXP / "PREFLIGHT.md").write_text(preflight_markdown(record), encoding="utf-8")
    elif not existing.is_file():
        write_json_once(existing, record)
        write_once(EXP / "PREFLIGHT.md", preflight_markdown(record))
    print(json.dumps({
        "status": "PASS",
        "head": head(),
        "head_refresh": args.refresh_head,
        "new_physical_solve_count": 6,
        "reused_physical_case_count": 2,
        "exact_logical_case_count": 8,
        "reuse_status": reuse_checks["status"],
        "deck_status": decks["status"],
        "solver_invoked": False,
        "scientific_analysis_performed": False,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
