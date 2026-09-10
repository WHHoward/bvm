#!/usr/bin/env python3
"""Register the RJ2=12 local timestep robustness spot-check.

Preparation performs no physical solve.  The 0.1 ps pair is copied as exact
immutable reuse; only the 0.05 ps and 0.025 ps pairs receive new decks.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
AUTH = REPO / "test/exploration/qb-rj2-highside-second-trigger-l1p14-l2p20-ib260-rj32-bjs400-v2-20260910"
SOLVER = REPO / "build/josim-cli"
CONTRACT_SENTENCE = "This experiment is governed by docs/EXPERIMENT_CONTRACT.md."
AUTH_SOURCE_MANIFEST_SHA256 = "60d36ef77ec0c7e55493c5c43d93d7fe2c141b117e80cd73b8d8dce0e25710b3"
AUTH_PACKAGE_SHA256 = "84e1a8654aa16baf2fe81f96f9cdc4ce8af6efbeb5f617a12c8123b8b13a9bde"
AUTH_PACKAGE_BYTES = 10106003
AUTH_ORACLE_SHA256 = "f5365ba4651cc1828b32a5932eb5c4cab7bda3317c81563e0cbb6571abe7230f"
SOLVER_SHA256 = "48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2"
FIXED = {"L1_pH": 1.4, "L2_pH": 2.0, "IBias_uA": 260.0, "RJ1_ohm": 32.0, "RJ2_ohm": 12.0}
DT_VALUES = (0.05, 0.025)
MASKS = ("0001", "0011")
REUSE_RUNS = tuple(f"ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_DT0100_{mask}" for mask in MASKS)
NEW_RUNS = tuple(f"ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_DT{int(round(dt * 1000)):04d}_{mask}" for dt in DT_VALUES for mask in MASKS)
ALL_RUNS = REUSE_RUNS + NEW_RUNS
RUN_TO_DT = {run_id: 0.1 for run_id in REUSE_RUNS}
RUN_TO_DT.update({run_id: dt for dt in DT_VALUES for run_id in (f"ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_DT{int(round(dt * 1000)):04d}_0001", f"ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_DT{int(round(dt * 1000)):04d}_0011")})
RUN_TO_MASK = {run_id: run_id.rsplit("_", 1)[1] for run_id in ALL_RUNS}
EXPECTED_INPUT_HASHES = {
    "array_fixture_template.cir": "8971a82dfbac223b9be139f719afae2eb156f0f68fb2a4811858f0a0b482cf71",
    "bvm_jm2_connected.cir": "0093a45cc3910448b484d8bd004c6df8c22358bacc8b3ed5e23912dcab805d54",
    "jjmit.cir": "19862d1fd1f1f44dfa1523848d7d3b5e2594a6c5da8fdd80144b449e5312a336",
    "jtl2.cir": "ffd31f8eda2a86ca0133342be1ce678831b7237a53911eda046d2bff8454855a",
    "BQ_parameterized_bjs400.cir": "883308517d48470cbedab878f9e3c71721cd972db248c6b821ce5dba642ff810",
    "BQ_parameterized_bjs400_rj2.cir": "43468c49eb56090e586428a8ca26d17d8bbf107fbd9e535bbac7a72ed1200d42",
}


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()


def solver_version() -> str:
    return subprocess.check_output([str(SOLVER), "--version"], cwd=REPO, text=True)


def write_once(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file():
        if path.read_text(encoding="utf-8") != text:
            raise RuntimeError(f"refusing to overwrite existing artifact: {path}")
        return
    path.write_text(text, encoding="utf-8")


def write_json_once(path: Path, value: Any) -> None:
    write_once(path, json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def source_reuse_run(mask: str) -> Path:
    return AUTH / "runs" / f"ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_{mask}"


def local_reuse_run(mask: str) -> Path:
    return EXP / "references/reused" / f"ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_DT0100_{mask}"


def write_reuse_manifest() -> dict[str, Any]:
    path = EXP / "REUSED_REFERENCE_MANIFEST.json"
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    source_manifest = AUTH / "SOURCE_MANIFEST.json"
    package = AUTH / "handoff/qb-rj2-highside-second-trigger-l1p14-l2p20-ib260-rj32-bjs400-v2-20260910_raw_handoff.zip"
    if sha256(source_manifest) != AUTH_SOURCE_MANIFEST_SHA256 or sha256(package) != AUTH_PACKAGE_SHA256 or package.stat().st_size != AUTH_PACKAGE_BYTES:
        raise RuntimeError("latest canonical RJ2 source manifest/package changed")
    references: dict[str, Any] = {}
    for run_id in REUSE_RUNS:
        mask = RUN_TO_MASK[run_id]
        source_dir = source_reuse_run(mask)
        local_dir = local_reuse_run(mask)
        artifacts: dict[str, Any] = {}
        for name in ("raw.csv", "deck.cir", "metadata.json", "run.log"):
            source = source_dir / name
            local = local_dir / name
            if not source.is_file() or not local.is_file() or sha256(source) != sha256(local):
                raise RuntimeError(f"exact 0.1ps reuse mismatch: {run_id}/{name}")
            artifacts[name] = {"source_path": str(source), "archived_path": str(local), "source_sha256": sha256(source), "archived_sha256": sha256(local), "bytes": local.stat().st_size}
        metadata = json.loads((local_dir / "metadata.json").read_text(encoding="utf-8"))
        if metadata.get("rj2_ohm") != 12.0 or metadata.get("mask") != mask or metadata.get("execution_status") != "RUN_PASS":
            raise RuntimeError(f"0.1ps reuse metadata mismatch: {run_id}")
        references[run_id] = {
            "logical_case_id": run_id,
            "source_experiment": str(AUTH.relative_to(REPO)),
            "source_run": f"runs/ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_{mask}",
            "source_git_head": metadata.get("git_head_before_run"),
            "parameters": {**FIXED, "dt_ps": 0.1},
            "mask": mask,
            "physical_solve_this_experiment": False,
            "reuse_reason": "exact immutable RJ2=12, mask, protocol, solver and canonical 0.1ps raw/deck/history reuse",
            "source_evidence_package": {"path": str(package.relative_to(REPO)), "sha256": AUTH_PACKAGE_SHA256, "bytes": AUTH_PACKAGE_BYTES},
            "artifacts": artifacts,
        }
    record = {"schema": "bjs400-rj2p12-timestep-reuse-manifest-v1", "experiment_id": EXP.name, "created_at_local": now(), "source_authority": str(AUTH.relative_to(REPO)), "source_authority_source_manifest_sha256": AUTH_SOURCE_MANIFEST_SHA256, "source_authority_package_sha256": AUTH_PACKAGE_SHA256, "source_oracle_code_sha256": AUTH_ORACLE_SHA256, "references": references, "reused_physical_case_count": 2, "exact_reuse_verification": "PASS", "no_new_0p1ps_solve": True}
    write_json_once(path, record)
    return record


def write_source_manifest() -> dict[str, Any]:
    path = EXP / "SOURCE_MANIFEST.json"
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    local_sources = []
    for name, role in (("array_fixture_template.cir", "BJS400 ARRAY fixture/stimulus template"), ("bvm_jm2_connected.cir", "historical JM2-connected BVM include"), ("jjmit.cir", "JJ model include"), ("jtl2.cir", "JTL model include"), ("BQ_parameterized_bjs400.cir", "unmodified BJS400 QB authority include"), ("BQ_parameterized_bjs400_rj2.cir", "derived BJS400 QB include with RJ2 parameter exposure")):
        source = EXP / "inputs" / name
        local_sources.append({"path": name, "repo_relative_path": str(source.relative_to(REPO)), "sha256": sha256(source), "bytes": source.stat().st_size, "role": role})
    local_sources.append({"path": str(SOLVER.relative_to(REPO)), "sha256": sha256(SOLVER), "bytes": SOLVER.stat().st_size, "role": "solver identity", "version": solver_version()})
    record = {"schema": "bjs400-rj2p12-timestep-source-manifest-v1", "experiment_id": EXP.name, "created_at_local": now(), "physical_stimulus_authority": str(AUTH.relative_to(REPO)), "physical_stimulus_authority_git_head": "5886c84863a215f596050ad3c91df6af2d6e13b2", "physical_stimulus_authority_source_manifest_sha256": AUTH_SOURCE_MANIFEST_SHA256, "base_stimulus_source_manifest_sha256": "31752f9e74b95d1d787d88c146a1a7d650da5d37ac3a4a3a035494a604ef1b4d", "physical_stimulus_authority_package_sha256": AUTH_PACKAGE_SHA256, "corrected_oracle_sha256": AUTH_ORACLE_SHA256, "local_sources": local_sources, "fixed_working_point": {**FIXED, "BJS_area": 4, "BJS_Ic_uA": 400}, "timestep_values_new_ps": list(DT_VALUES), "timestep_baseline_reused_ps": 0.1, "only_registered_physical_delta": "tran timestep"}
    write_json_once(path, record)
    return record


def build_deck(dt_ps: float, mask: str) -> str:
    base = (local_reuse_run(mask) / "deck.cir").read_text(encoding="utf-8")
    token = ".tran 0.1p 200p"
    if base.count(token) != 1:
        raise RuntimeError(f"0.1ps source deck has unexpected tran line: {mask}")
    text = base.replace(token, f".tran {dt_ps:g}p 200p", 1)
    if text.replace(f".tran {dt_ps:g}p 200p", token, 1) != base:
        raise RuntimeError("timestep deck changed outside .tran line")
    return text


def generate_decks() -> dict[str, Any]:
    output: dict[str, Any] = {}
    for run_id in NEW_RUNS:
        dt = RUN_TO_DT[run_id]
        mask = RUN_TO_MASK[run_id]
        path = EXP / "runs" / run_id / "deck.cir"
        write_once(path, build_deck(dt, mask))
        output[run_id] = {"dt_ps": dt, "mask": mask, "parameters": {**FIXED, "dt_ps": dt}, "path": str(path.relative_to(REPO)), "sha256": sha256(path), "bytes": path.stat().st_size}
    return output


def verify_decks() -> dict[str, Any]:
    failures: list[str] = []
    for run_id in NEW_RUNS:
        dt = RUN_TO_DT[run_id]
        mask = RUN_TO_MASK[run_id]
        path = EXP / "runs" / run_id / "deck.cir"
        text = path.read_text(encoding="utf-8")
        expected = build_deck(dt, mask)
        if text != expected:
            failures.append(f"{run_id}: deck differs from exact .tran-only transformation")
        if text.count(f".tran {dt:g}p 200p") != 1:
            failures.append(f"{run_id}: timestep line mismatch")
        if ".tran 0.1p 200p" in text:
            failures.append(f"{run_id}: stale 0.1p line remains")
    return {"schema": "bjs400-rj2p12-timestep-deck-preflight-v1", "status": "PASS" if not failures else "FAIL", "new_run_count": len(NEW_RUNS), "reused_case_count": len(REUSE_RUNS), "new_dt_ps": list(DT_VALUES), "only_tran_delta": not failures, "failures": failures, "runs": {run_id: {"dt_ps": RUN_TO_DT[run_id], "mask": RUN_TO_MASK[run_id], "deck_sha256": sha256(EXP / "runs" / run_id / "deck.cir")} for run_id in NEW_RUNS}}


def preflight_markdown(record: dict[str, Any]) -> str:
    return "\n".join([
        "# RJ2=12 timestep robustness spot-check — PREFLIGHT",
        "",
        CONTRACT_SENTENCE,
        "",
        f"- Experiment: `{EXP.name}`",
        f"- Preflight HEAD: `{record['head']}`",
        f"- Phase A oracle repair commit: `{record['oracle_repair_commit']}`; oracle SHA-256 `{AUTH_ORACLE_SHA256}`.",
        "- Canonical timestep remains `.tran=0.1p`; this experiment uses 0.05ps and 0.025ps only as local robustness spot-checks.",
        "- Fixed L1=1.4pH, L2=2.0pH, IBias=260uA, RJ1=32ohm, RJ2=12ohm, BJS area=4/Ic=400uA, BJ1/BJ2/L3/load/topology/history unchanged.",
        "",
        "## Exact matrix",
        "",
        "- 0.1ps: exact immutable reuse for masks 0001 and 0011; no 0.1ps solver invocation.",
        "- 0.05ps: new physical solves for masks 0001 and 0011.",
        "- 0.025ps: new physical solves for masks 0001 and 0011.",
        "- Total: 6 logical timestep/mask cases, 2 reuse cases, exactly 4 new solves; no RJ2=14/16 finer rerun or other parameter sweep.",
        "",
        "## Frozen protocol and interpretation ceiling",
        "",
        "- IDLE 0–50ps; WRITE0 50–61ps; IDLE 61–70ps; ZERO_STATE_READ_CONTROL 70–81ps; IDLE 81–90ps; WRITE1 90–101ps; SETTLE 101–110ps; FINAL READ 110–121ps; TAIL 121–200ps.",
        "- Amplitude 100uA, rise/fall 1ps, plateau 9ps, stop time 200ps; only the `.tran` timestep changes.",
        "- Repaired oracle uses FINAL baseline [101,110)ps, cumulative +0.5/+1.5 navigation landmarks, direct voltage clusters and valley-gated terminal pulse segmentation.",
        "- Phase, pulse area, current peak, L1 crossing and terminal area are not SFQ counts. A stable classification here is a finite `TIMESTEP_ROBUST_CANDIDATE_WITHIN_TESTED_DT`, not convergence or final SFQ proof.",
        "",
        "## Automatic preflight result",
        "",
        f"- Exact 0.1ps reuse: `{record['reuse_status']}`; deck checks: `{record['deck_status']}`.",
        "- Physical execution has not started at preflight.",
        "",
    ])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh-head", action="store_true")
    args = parser.parse_args()
    for name, expected in EXPECTED_INPUT_HASHES.items():
        path = EXP / "inputs" / name
        if not path.is_file() or sha256(path) != expected:
            raise RuntimeError(f"input hash mismatch: {name}")
    if not SOLVER.is_file() or sha256(SOLVER) != SOLVER_SHA256:
        raise RuntimeError("solver identity hash mismatch")
    reuse = write_reuse_manifest()
    write_source_manifest()
    generated = generate_decks()
    decks = verify_decks()
    if reuse.get("exact_reuse_verification") != "PASS" or decks["status"] != "PASS":
        raise RuntimeError(f"preflight failed: reuse={reuse.get('exact_reuse_verification')} decks={decks['status']}")
    preflight_path = EXP / "analysis/preflight.json"
    prior = json.loads(preflight_path.read_text(encoding="utf-8")) if preflight_path.is_file() else {}
    record = {"schema": "bjs400-rj2p12-timestep-preflight-v1", "experiment_id": EXP.name, "created_at_local": now(), "status": "PASS", "head": head(), "head_refresh": args.refresh_head, "preregistration_head": prior.get("preregistration_head", head()), "oracle_repair_commit": "fd1fc5cf", "new_physical_solve_count": 4, "authorized_new_physical_solve_count": 4, "reused_physical_case_count": 2, "logical_case_count": 6, "unauthorized_extra_solves": 0, "fixed_working_point": {**FIXED, "BJS_area": 4, "BJS_Ic_uA": 400}, "new_timestep_ps": list(DT_VALUES), "reused_timestep_ps": 0.1, "authorized_masks": list(MASKS), "reuse_status": "PASS", "reuse_manifest_sha256": sha256(EXP / "REUSED_REFERENCE_MANIFEST.json"), "generated_decks": generated, "deck_status": decks["status"], "deck_checks": decks, "oracle_code_sha256": AUTH_ORACLE_SHA256, "canonical_timestep_policy": "0.1ps remains standard; 0.05/0.025ps are local robustness spot-checks only", "scientific_analysis_performed": False}
    if args.refresh_head:
        preflight_path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        (EXP / "PREFLIGHT.md").write_text(preflight_markdown(record), encoding="utf-8")
    elif not preflight_path.is_file():
        write_json_once(preflight_path, record)
        write_once(EXP / "PREFLIGHT.md", preflight_markdown(record))
    print(json.dumps({"status": "PASS", "head": head(), "new_physical_solve_count": 4, "reused_physical_case_count": 2, "logical_case_count": 6, "solver_invoked": False, "scientific_analysis_performed": False}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
