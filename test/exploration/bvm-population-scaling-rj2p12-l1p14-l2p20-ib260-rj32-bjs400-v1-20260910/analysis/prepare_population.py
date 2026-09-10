#!/usr/bin/env python3
"""Register the selected-mask population experiment without solving."""

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
AUTH = REPO / "test/exploration/qb-rj2p12-timestep-robustness-l1p14-l2p20-ib260-rj32-bjs400-v1-20260910"
SOLVER = REPO / "build/josim-cli"
CONTRACT_SENTENCE = "This experiment is governed by docs/EXPERIMENT_CONTRACT.md."
AUTH_MANIFEST_SHA256 = "e0def923f36c6e8c7b7e60e03f76a1864d7fc304970cd3ebcab4775e5a40d08e"
AUTH_PACKAGE_SHA256 = "a6e2e0b6d9bfa9dab002aa38979e8b12029ad3c16cb2dc203e5069b9f8e1e287"
AUTH_PACKAGE_BYTES = 16990172
AUTH_ORACLE_SHA256 = "4d39bc457e0ea010ac9f312dbc1c40b6e65dea123865608f4ad066a05773e860"
SOLVER_SHA256 = "48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2"
FIXED = {"L1_pH": 1.4, "L2_pH": 2.0, "IBias_uA": 260.0, "RJ1_ohm": 32.0, "RJ2_ohm": 12.0}
MASKS = ("0001", "0011", "0110", "1100", "1110", "0111", "1111")
NEW_MASKS = ("0110", "1100", "1110", "0111", "1111")
REUSE_RUNS = tuple(f"ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_{mask}" for mask in ("0001", "0011"))
NEW_RUNS = tuple(f"ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_{mask}" for mask in NEW_MASKS)
ALL_RUNS = REUSE_RUNS + NEW_RUNS
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


def reuse_source(mask: str) -> Path:
    return AUTH / "references/reused" / f"ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_DT0100_{mask}"


def local_reuse(mask: str) -> Path:
    return EXP / "references/reused" / f"ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_{mask}"


def write_reuse_manifest() -> dict[str, Any]:
    path = EXP / "REUSED_REFERENCE_MANIFEST.json"
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    source_manifest = AUTH / "SOURCE_MANIFEST.json"
    package = AUTH / "handoff/qb-rj2p12-timestep-robustness-l1p14-l2p20-ib260-rj32-bjs400-v1-20260910_corrected-v2_raw_handoff.zip"
    if sha256(source_manifest) != AUTH_MANIFEST_SHA256 or sha256(package) != AUTH_PACKAGE_SHA256 or package.stat().st_size != AUTH_PACKAGE_BYTES:
        raise RuntimeError("latest timestep candidate authority manifest/package changed")
    references: dict[str, Any] = {}
    for run_id in REUSE_RUNS:
        mask = RUN_TO_MASK[run_id]
        source_dir, local_dir = reuse_source(mask), local_reuse(mask)
        artifacts: dict[str, Any] = {}
        for name in ("raw.csv", "deck.cir", "metadata.json", "run.log"):
            source, local = source_dir / name, local_dir / name
            if not source.is_file() or not local.is_file() or sha256(source) != sha256(local):
                raise RuntimeError(f"exact RJ2=12 reuse mismatch: {run_id}/{name}")
            artifacts[name] = {"source_path": str(source), "archived_path": str(local), "source_sha256": sha256(source), "archived_sha256": sha256(local), "bytes": local.stat().st_size}
        metadata = json.loads((local_dir / "metadata.json").read_text(encoding="utf-8"))
        deck_text = (local_dir / "deck.cir").read_text(encoding="utf-8")
        if metadata.get("rj2_ohm") != 12.0 or metadata.get("mask") != mask or ".tran 0.1p 200p" not in deck_text:
            raise RuntimeError(f"reuse metadata mismatch: {run_id}")
        references[run_id] = {"logical_case_id": run_id, "source_experiment": str(AUTH.relative_to(REPO)), "source_run": f"references/reused/ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_DT0100_{mask}", "source_git_head": metadata.get("git_head_before_run"), "parameters": {**FIXED, "mask": mask, "timestep_ps": 0.1}, "mask": mask, "physical_solve_this_experiment": False, "reuse_reason": "exact immutable RJ2=12, 0.1ps, mask, protocol, solver and stored raw reuse", "source_evidence_package": {"path": str(package.relative_to(REPO)), "sha256": AUTH_PACKAGE_SHA256, "bytes": AUTH_PACKAGE_BYTES}, "artifacts": artifacts}
    record = {"schema": "bjs400-population-rj2p12-reuse-manifest-v1", "experiment_id": EXP.name, "created_at_local": now(), "source_authority": str(AUTH.relative_to(REPO)), "source_authority_manifest_sha256": AUTH_MANIFEST_SHA256, "source_authority_package_sha256": AUTH_PACKAGE_SHA256, "corrected_oracle_sha256": AUTH_ORACLE_SHA256, "references": references, "reused_physical_case_count": 2, "exact_reuse_verification": "PASS", "no_reuse_by_filename_only": True}
    write_json_once(path, record)
    return record


def write_source_manifest() -> dict[str, Any]:
    path = EXP / "SOURCE_MANIFEST.json"
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    sources = []
    for name, role in (("array_fixture_template.cir", "BJS400 ARRAY fixture/stimulus template"), ("bvm_jm2_connected.cir", "historical JM2-connected BVM include"), ("jjmit.cir", "JJ model include"), ("jtl2.cir", "JTL model include"), ("BQ_parameterized_bjs400.cir", "unmodified BJS400 QB authority include"), ("BQ_parameterized_bjs400_rj2.cir", "derived BJS400 QB RJ2 parameter include")):
        source = EXP / "inputs" / name
        sources.append({"path": name, "repo_relative_path": str(source.relative_to(REPO)), "sha256": sha256(source), "bytes": source.stat().st_size, "role": role})
    sources.append({"path": str(SOLVER.relative_to(REPO)), "sha256": sha256(SOLVER), "bytes": SOLVER.stat().st_size, "role": "solver identity", "version": solver_version()})
    record = {"schema": "bjs400-population-rj2p12-source-manifest-v1", "experiment_id": EXP.name, "created_at_local": now(), "physical_stimulus_authority": str(AUTH.relative_to(REPO)), "physical_stimulus_authority_git_head": "ddcdfe0309be4b492698a01e15a9ef7d9bb99f1e", "physical_stimulus_authority_manifest_sha256": AUTH_MANIFEST_SHA256, "physical_stimulus_authority_package_sha256": AUTH_PACKAGE_SHA256, "corrected_oracle_sha256": AUTH_ORACLE_SHA256, "local_sources": sources, "fixed_working_point": {**FIXED, "BJS_area": 4, "BJS_Ic_uA": 400}, "new_masks": list(NEW_MASKS), "reuse_masks": ["0001", "0011"], "only_registered_physical_delta": "FINAL READ BVM mask"}
    write_json_once(path, record)
    return record


def build_deck(mask: str) -> str:
    base = (local_reuse("0001") / "deck.cir").read_text(encoding="utf-8")
    for instance in range(1, 5):
        for kind in ("WL", "BL", "SE"):
            token = f"I_{kind}{instance}"
            old_lines = [line for line in base.splitlines() if line.startswith(token + " ")]
            if len(old_lines) != 1:
                raise RuntimeError(f"control line is not unique: {token}")
            old = old_lines[0]
            new = control_line(instance, kind, mask[instance - 1] == "1")
            base = base.replace(old, new, 1)
    return base


def normalize_deck(text: str) -> tuple[str, ...]:
    return tuple(line for line in text.splitlines() if not line.startswith("I_WL") and not line.startswith("I_BL") and not line.startswith("I_SE"))


def generate_decks() -> dict[str, Any]:
    output: dict[str, Any] = {}
    for run_id in NEW_RUNS:
        mask = RUN_TO_MASK[run_id]
        path = EXP / "runs" / run_id / "deck.cir"
        write_once(path, build_deck(mask))
        output[run_id] = {"mask": mask, "parameters": {**FIXED, "mask": mask}, "path": str(path.relative_to(REPO)), "sha256": sha256(path), "bytes": path.stat().st_size}
    return output


def verify_decks() -> dict[str, Any]:
    failures: list[str] = []
    base_norm = normalize_deck((local_reuse("0001") / "deck.cir").read_text(encoding="utf-8"))
    for run_id in NEW_RUNS:
        path = EXP / "runs" / run_id / "deck.cir"
        text = path.read_text(encoding="utf-8")
        if normalize_deck(text) != base_norm:
            failures.append(f"{run_id}: deck changed outside FINAL READ control lines")
        for instance in range(1, 5):
            for kind in ("WL", "BL", "SE"):
                if text.count(control_line(instance, kind, RUN_TO_MASK[run_id][instance - 1] == "1")) != 1:
                    failures.append(f"{run_id}: control mismatch {kind}{instance}")
    return {"schema": "bjs400-population-rj2p12-deck-diff-preflight-v1", "status": "PASS" if not failures else "FAIL", "only_mask_delta": not failures, "new_run_count": len(NEW_RUNS), "failures": failures, "runs": {run_id: {"mask": RUN_TO_MASK[run_id], "deck_sha256": sha256(EXP / "runs" / run_id / "deck.cir")} for run_id in NEW_RUNS}}


def preflight_markdown(record: dict[str, Any]) -> str:
    return "\n".join([
        "# Selected-mask population scaling — PREFLIGHT", "", CONTRACT_SENTENCE, "",
        f"- Experiment: `{EXP.name}`", f"- Preflight HEAD: `{record['head']}`", f"- Frozen candidate: RJ2=12ohm; canonical `.tran=0.1p 200p`.",
        f"- Generalized oracle regression: required before new runs; code SHA-256 `{AUTH_ORACLE_SHA256}`.",
        "- Only the FINAL READ BVM mask changes. L1/L2/RJ1/IBias/BJS/BJ1/BJ2/L3/load/JTL/history/timing remain unchanged.", "",
        "## Exact matrix", "", "- Immutable reuse: masks `0001` and `0011` from the latest RJ2=12 timestep candidate.", "- New physical solves: exactly masks `0110`, `1100`, `1110`, `0111`, `1111`.", "- Total: 7 logical population cases, 2 reuse cases and exactly 5 new solves; no other masks and no finer timestep.", "",
        "## Frozen protocol", "", "- IDLE 0–50ps; WRITE0 50–61ps; IDLE 61–70ps; ZERO_STATE_READ_CONTROL 70–81ps; IDLE 81–90ps; WRITE1 90–101ps; SETTLE 101–110ps; mask-selective FINAL READ 110–121ps; TAIL 121–200ps.", "- Amplitude 100uA, 1ps rise/fall, 9ps plateau; `.tran 0.1p 200p`.", "- Bit order b3b2b1b0=BVM1/BVM2/BVM3/BVM4.", "",
        "## Evidence ceiling", "", "- Generalized response multiplicity requires cumulative baseline phase landmarks, direct stored-sample voltage clusters, ordered JTL progression and valley-segmented terminal pulses for each response.", "- Hamming weight is used only after oracle classification; it is never passed to the response detector as an expected count.", "- No phase, pulse area, terminal area, current peak or L1 crossing is an SFQ count.", "", f"- Exact reuse: `{record['reuse_status']}`; deck checks: `{record['deck_status']}`.", "- Physical execution has not started at preflight.", ""])


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
        raise RuntimeError("population preflight failed")
    path = EXP / "analysis/preflight.json"
    prior = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    record = {"schema": "bjs400-population-scaling-preflight-v1", "experiment_id": EXP.name, "created_at_local": now(), "status": "PASS", "head": head(), "head_refresh": args.refresh_head, "preregistration_head": prior.get("preregistration_head", head()), "new_physical_solve_count": 5, "reused_physical_case_count": 2, "logical_case_count": 7, "new_masks": list(NEW_MASKS), "reuse_masks": ["0001", "0011"], "unauthorized_extra_solves": 0, "fixed_working_point": {**FIXED, "BJS_area": 4, "BJS_Ic_uA": 400}, "reuse_status": "PASS", "deck_status": decks["status"], "reuse_manifest_sha256": sha256(EXP / "REUSED_REFERENCE_MANIFEST.json"), "generated_decks": generated, "deck_checks": decks, "authority_package_sha256": AUTH_PACKAGE_SHA256, "authority_manifest_sha256": AUTH_MANIFEST_SHA256, "oracle_code_sha256": AUTH_ORACLE_SHA256, "scientific_analysis_performed": False}
    if args.refresh_head:
        path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        (EXP / "PREFLIGHT.md").write_text(preflight_markdown(record), encoding="utf-8")
    elif not path.is_file():
        write_json_once(path, record)
        write_once(EXP / "PREFLIGHT.md", preflight_markdown(record))
    print(json.dumps({"status": "PASS", "head": head(), "new_physical_solve_count": 5, "reused_physical_case_count": 2, "logical_case_count": 7, "solver_invoked": False, "scientific_analysis_performed": False}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
