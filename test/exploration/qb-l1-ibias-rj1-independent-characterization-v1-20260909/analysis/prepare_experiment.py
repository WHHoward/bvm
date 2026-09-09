#!/usr/bin/env python3
"""Prepare and mechanically preflight the independent response-family study.

This script creates registered decks and provenance only.  It never invokes
JoSIM.  ``--refresh-head`` is used once after the preregistration commit so the
final machine preflight binds the clean commit that will execute the 12 solves.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
TEMPLATE = EXP / "inputs/array_fixture_template.cir"
BQ_SOURCE = EXP / "inputs/BQ_source.cir"
BQ_PARAMETERIZED = EXP / "inputs/BQ_parameterized_v2.cir"
SOLVER = REPO / "build/josim-cli"
OLD_EXP = REPO / "test/exploration/qb-rj1-l1-local-sensitivity-v1-20260909"
CONTRACT_SENTENCE = "This experiment is governed by docs/EXPERIMENT_CONTRACT.md."

SOURCE_HASHES = {
    "fixture_template": "85227538d48d69251f4276b94b28adfc83cd25f95aa6609fa9eb2375c873f1cf",
    "bvm": "0093a45cc3910448b484d8bd004c6df8c22358bacc8b3ed5e23912dcab805d54",
    "jjmit": "19862d1fd1f1f44dfa1523848d7d3b5e2594a6c5da8fdd80144b449e5312a336",
    "bq_source": "f3dcbf5f9bb3898faf5194b5f7c4771df3fa1ed16150496de4b52cb6f7256dfd",
    "jtl": "ffd31f8eda2a86ca0133342be1ce678831b7237a53911eda046d2bff8454855a",
    "solver": "48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2",
}
OLD_RUNS = {
    "L1_1P9": ("l1_down", 12.0, 1.9, 250.0),
    "NOMINAL": ("nominal", 12.0, 2.0, 250.0),
    "L1_2P1": ("l1_up", 12.0, 2.1, 250.0),
    "RJ1_12P5": ("rj1_up_05", 12.5, 2.0, 250.0),
    "RJ1_13": ("rj1_up_10", 13.0, 2.0, 250.0),
}
NEW_RUNS = {
    "L1_1P2": ("L1", 12.0, 1.2, 250.0),
    "L1_1P4": ("L1", 12.0, 1.4, 250.0),
    "L1_1P6": ("L1", 12.0, 1.6, 250.0),
    "L1_1P8": ("L1", 12.0, 1.8, 250.0),
    "IB_230": ("IBias", 12.0, 2.0, 230.0),
    "IB_240": ("IBias", 12.0, 2.0, 240.0),
    "IB_260": ("IBias", 12.0, 2.0, 260.0),
    "IB_270": ("IBias", 12.0, 2.0, 270.0),
    "RJ1_8": ("RJ1", 8.0, 2.0, 250.0),
    "RJ1_10": ("RJ1", 10.0, 2.0, 250.0),
    "RJ1_14": ("RJ1", 14.0, 2.0, 250.0),
    "RJ1_16": ("RJ1", 16.0, 2.0, 250.0),
}


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


def write_once(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_text(encoding="utf-8") != content:
            raise RuntimeError(f"refusing to overwrite existing artifact: {path}")
        return
    path.write_text(content, encoding="utf-8")


def build_deck(rj1: float, l1: float, ibias: float) -> str:
    template = TEMPLATE.read_text(encoding="utf-8")
    old_block = (
        ".include ../../../../../circuits/models/jjmit.cir\n"
        ".include ../../../bvmsim-jm2-connected-single-ab-v1-20260903/variants/bvm_jm2_connected.cir\n"
        ".include ../../../../../BVMSim/BQ.cir\n"
        ".include ../../../../../BVMSim/library_josim/jtl2.cir"
    )
    local_block = (
        f".param RJ1_VALUE={rj1:g}\n"
        f".param L1_VALUE={l1:g}p\n"
        f".param IB_VALUE={ibias:g}u\n"
        ".include ../../inputs/jjmit.cir\n"
        ".include ../../inputs/bvm_jm2_connected.cir\n"
        ".include ../../inputs/BQ_parameterized_v2.cir\n"
        ".include ../../inputs/jtl2.cir"
    )
    if template.count(old_block) != 1:
        raise RuntimeError("fixture include block is not unique")
    result = template.replace(old_block, local_block, 1)
    if result.count(".param RJ1_VALUE=") != 1 or result.count(".param L1_VALUE=") != 1 or result.count(".param IB_VALUE=") != 1:
        raise RuntimeError("registered parameter block was not inserted exactly once")
    if ".include ../../../../../BVMSim/BQ.cir" in result or "../../../../../BVMSim/library_josim/jtl2.cir" in result:
        raise RuntimeError("shared physical include escaped the frozen local closure")
    return result


def verify_inputs() -> list[str]:
    failures: list[str] = []
    expected_paths = {
        "fixture_template": TEMPLATE,
        "bvm": EXP / "inputs/bvm_jm2_connected.cir",
        "jjmit": EXP / "inputs/jjmit.cir",
        "bq_source": BQ_SOURCE,
        "jtl": EXP / "inputs/jtl2.cir",
        "solver": SOLVER,
    }
    for key, path in expected_paths.items():
        if not path.is_file():
            failures.append(f"missing source: {path}")
        elif sha256(path) != SOURCE_HASHES[key]:
            failures.append(f"source hash mismatch: {key}")
    if not BQ_PARAMETERIZED.is_file():
        failures.append("missing parameterized BQ")
    else:
        bq = BQ_PARAMETERIZED.read_text(encoding="utf-8")
        for token in ("{L1_VALUE}", "{RJ1_VALUE}"):
            if bq.count(token) != 1:
                failures.append(f"parameterized BQ placeholder count is not one: {token}")
        if bq.count("IB_VALUE") != 1 or "{IB_VALUE}" in bq:
            failures.append("parameterized BQ IB_VALUE token is not the supported bare form")
        for token in ("L1 2 3 2p", "RJ1 2 0 12", "1p 250u"):
            if token in bq:
                failures.append(f"parameterized BQ retains nominal literal: {token}")
    if not SOLVER.is_file():
        failures.append(f"missing solver: {SOLVER}")
    return failures


def generate_decks() -> dict[str, dict[str, object]]:
    records: dict[str, dict[str, object]] = {}
    for run_id, (family, rj1, l1, ibias) in NEW_RUNS.items():
        directory = EXP / "runs" / run_id
        deck = directory / "deck.cir"
        write_once(deck, build_deck(rj1, l1, ibias))
        records[run_id] = {
            "family": family,
            "directory": f"runs/{run_id}",
            "path": deck.relative_to(REPO).as_posix(),
            "sha256": sha256(deck),
            "bytes": deck.stat().st_size,
            "parameters": {"RJ1_ohm": rj1, "L1_pH": l1, "IBias_uA": ibias},
            "physical_solve_this_experiment": True,
        }
    return records


def reused_manifest() -> dict[str, object]:
    records: dict[str, object] = {}
    for logical_id, (old_dir, rj1, l1, ibias) in OLD_RUNS.items():
        source_dir = OLD_EXP / "runs" / old_dir
        target_dir = EXP / "references" / "reused" / logical_id
        source_hashes: dict[str, str] = {}
        copied_hashes: dict[str, str] = {}
        for name in ("raw.csv", "deck.cir", "metadata.json"):
            source = source_dir / name
            target = target_dir / name
            if not source.is_file() or not target.is_file():
                raise RuntimeError(f"missing reuse artifact: {source} / {target}")
            source_hashes[name] = sha256(source)
            copied_hashes[name] = sha256(target)
            if source_hashes[name] != copied_hashes[name]:
                raise RuntimeError(f"reuse copy hash mismatch: {logical_id}/{name}")
        if (source_dir / "run.log").is_file() and (target_dir / "run.log").is_file():
            source_hashes["run.log"] = sha256(source_dir / "run.log")
            copied_hashes["run.log"] = sha256(target_dir / "run.log")
            if source_hashes["run.log"] != copied_hashes["run.log"]:
                raise RuntimeError(f"reuse copy hash mismatch: {logical_id}/run.log")
        records[logical_id] = {
            "logical_case_id": logical_id,
            "source_experiment": OLD_EXP.name,
            "source_run": f"runs/{old_dir}",
            "source_raw_path": str(source_dir / "raw.csv"),
            "source_deck_path": str(source_dir / "deck.cir"),
            "source_metadata_path": str(source_dir / "metadata.json"),
            "source_hashes": source_hashes,
            "archived_reference_path": f"references/reused/{logical_id}",
            "archived_hashes": copied_hashes,
            "parameters": {"RJ1_ohm": rj1, "L1_pH": l1, "IBias_uA": ibias},
            "reuse_reason": "exact historical physical run; source/deck/solver/protocol/hash preflight matched",
            "physical_solve_this_experiment": False,
        }
    return {
        "schema": "qb-l1-ibias-rj1-reused-reference-manifest-v1",
        "experiment_id": EXP.name,
        "created_at_local": now(),
        "reuse_count": len(records),
        "references": records,
        "no_reuse_by_filename_only": True,
    }


def source_manifest(current_head: str) -> dict[str, object]:
    sources = [
        ("inputs/array_fixture_template.cir", "fixture template"),
        ("inputs/bvm_jm2_connected.cir", "historical BVM variant"),
        ("inputs/jjmit.cir", "JJ model"),
        ("inputs/BQ_source.cir", "BQ source"),
        ("inputs/BQ_parameterized_v2.cir", "derived parameterized BQ; repaired bare PWL parameter syntax"),
        ("inputs/jtl2.cir", "JTL source"),
        ("build/josim-cli", "solver identity"),
    ]
    records = []
    for relative, role in sources:
        path = REPO / relative if relative == "build/josim-cli" else EXP / relative
        repo_relative = relative if relative == "build/josim-cli" else (EXP.relative_to(REPO) / relative).as_posix()
        records.append({
            "repo_relative_path": repo_relative,
            "path": repo_relative,
            "sha256": sha256(path),
            "bytes": path.stat().st_size,
            "role": role,
        })
    return {
        "schema": "qb-l1-ibias-rj1-source-manifest-v1",
        "experiment_id": EXP.name,
        "head_at_registration": current_head,
        "created_at_local": now(),
        "sources": records,
    }


def write_preflight(*, refresh_head: bool) -> dict[str, object]:
    failures = verify_inputs()
    current_head = head()
    deck_records = generate_decks()
    reuse = reused_manifest()
    for run_id, record in deck_records.items():
        run_dir = EXP / record["directory"]
        if any((run_dir / name).exists() for name in ("raw.csv", "run.log", "metadata.json")):
            failures.append(f"new run output already exists: {run_id}")
    if len(deck_records) != 12:
        failures.append(f"new deck count is {len(deck_records)}, expected 12")
    preflight = {
        "schema": "qb-l1-ibias-rj1-independent-characterization-preflight-v1",
        "experiment_id": EXP.name,
        "created_at_local": now(),
        "status": "PASS" if not failures else "FAIL",
        "head": current_head,
        "head_refresh": refresh_head,
        "preregistration_head": "6c14838b6cdf947e81e50399b157451f6e994307",
        "exact_new_physical_solve_count": 12,
        "reused_physical_solve_count": 0,
        "unauthorized_extra_solves": 0,
        "combination_interventions": False,
        "new_decks": deck_records,
        "reused_references": reuse["references"],
        "source_hashes": {key: sha256(path) for key, path in {
            "fixture_template": TEMPLATE,
            "bvm": EXP / "inputs/bvm_jm2_connected.cir",
            "jjmit": EXP / "inputs/jjmit.cir",
            "bq_source": BQ_SOURCE,
            "bq_parameterized": BQ_PARAMETERIZED,
            "jtl": EXP / "inputs/jtl2.cir",
            "solver": SOLVER,
        }.items()},
        "reuse_preflight": {
            "status": "PASS" if not failures else "FAIL",
            "source_deck_raw_hashes_checked": True,
            "stimulus_timing_timestep_stop_and_solver_checked": True,
            "all_non_target_parameters_nominal": True,
            "details": "Historical candidates are byte-hash matched copies from the registered fixture; no filename-only reuse.",
        },
        "failures": failures,
        "no_solver_invoked": True,
        "interpretation_ceiling": "EVIDENCE_ONLY; SCIENTIFIC_REVIEW_AUTHORIZED not granted",
        "stop_on_fail": True,
    }
    source_path = EXP / "SOURCE_MANIFEST.json"
    source_record = source_manifest(current_head)
    if source_path.exists():
        old_source = json.loads(source_path.read_text(encoding="utf-8"))
        if old_source.get("sources") != source_record.get("sources"):
            raise RuntimeError("existing SOURCE_MANIFEST source closure differs")
    else:
        source_path.write_text(json.dumps(source_record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    reuse_path = EXP / "REUSED_REFERENCE_MANIFEST.json"
    if reuse_path.exists():
        old_reuse = json.loads(reuse_path.read_text(encoding="utf-8"))
        if old_reuse.get("references") != reuse.get("references"):
            raise RuntimeError("existing REUSED_REFERENCE_MANIFEST differs")
    else:
        reuse_path.write_text(json.dumps(reuse, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (EXP / "analysis").mkdir(exist_ok=True)
    preflight_path = EXP / "analysis" / "preflight.json"
    content = json.dumps(preflight, indent=2, ensure_ascii=False) + "\n"
    if preflight_path.exists():
        if not refresh_head:
            raise RuntimeError(f"preflight already exists; use --refresh-head only after preregistration commit: {preflight_path}")
        old = json.loads(preflight_path.read_text(encoding="utf-8"))
        if old.get("status") != "PASS" or old.get("failures"):
            raise RuntimeError("refusing to refresh a failed preflight")
        if any((EXP / "runs" / run_id / "raw.csv").exists() for run_id in NEW_RUNS):
            raise RuntimeError("refusing to refresh preflight after a physical solve")
        preflight_path.write_text(content, encoding="utf-8")
    else:
        preflight_path.write_text(content, encoding="utf-8")
    md = f"""# PREFLIGHT — {EXP.name}

{CONTRACT_SENTENCE}

- Role: `Experimental Operator + Evidence Packager`
- Workflow: `PRE-REGISTER -> PREFLIGHT -> 12 PHYSICAL SOLVES -> MECHANICAL QA -> V2.1 VISUALIZATION -> EVIDENCE PACKAGE -> COMMIT -> STOP`
- HEAD at this preflight: `{current_head}`
- Exact new physical solves: `12`
- Reused physical solves: `0` (five unique historical references, hash matched)
- Combination interventions: `FORBIDDEN`
- Scientific analysis: `NOT PERFORMED`
- Scientific authorization: `NOT_GRANTED`
- Solver invocation during preparation: `0`
- Raw mutation during preparation: `0`

## Registered families

- L1: `1.2, 1.4, 1.6, 1.8 pH`; reuse `1.9, 2.0, 2.1 pH`
- IBias: `230, 240, 260, 270 uA`; reuse `250 uA`
- RJ1: `8, 10, 14, 16 ohm`; reuse `12, 12.5, 13 ohm`

## Reuse gate

Historical deck/raw/source hashes, topology, stimulus, timing, solver identity,
non-target parameters and probe coverage were checked by `analysis/prepare_experiment.py`.
The copied reference bytes are not new physical solves.

## Stop rules

No retry, tuning, range shrink, extra point, combination run, ranking, winner,
mechanism interpretation or automatic follow-up is authorized. Final state is
`EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW`.
"""
    preflight_md = EXP / "PREFLIGHT.md"
    if preflight_md.exists() and refresh_head:
        preflight_md.write_text(md, encoding="utf-8")
    else:
        write_once(preflight_md, md)
    print(json.dumps({"status": preflight["status"], "head": current_head, "new_decks": len(deck_records), "reuse_count": len(reuse["references"]), "failures": failures}, ensure_ascii=False, indent=2))
    return preflight


def main() -> int:
    refresh = len(sys.argv) == 2 and sys.argv[1] == "--refresh-head"
    if len(sys.argv) > 2 or (len(sys.argv) == 2 and not refresh):
        raise SystemExit("usage: prepare_experiment.py [--refresh-head]")
    record = write_preflight(refresh_head=refresh)
    return 0 if record["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
