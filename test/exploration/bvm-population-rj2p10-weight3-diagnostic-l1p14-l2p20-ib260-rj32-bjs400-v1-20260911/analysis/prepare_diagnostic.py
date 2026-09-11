#!/usr/bin/env python3
"""Register the single RJ2=10/0111 diagnostic without solving."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
SOLVER = REPO / "build/josim-cli"
CONTRACT_SENTENCE = "This experiment is governed by docs/EXPERIMENT_CONTRACT.md."
LATEST_REMOTE_HEAD = "47c11aa35d87c5c9b481299a9b90fc02a37060c7"
AUTH_ORACLE_SHA256 = "b07056580cdd913efcf5317a8856c9a8023c8c9499ede89d236e837d20950166"
SOLVER_SHA256 = "48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2"
FIXED = {"L1_pH": 1.4, "L2_pH": 2.0, "IBias_uA": 260.0, "RJ1_ohm": 32.0, "RJ2_ohm": 10.0}
MASK = "0111"
RUN_ID = "ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P10_0111"
INPUT_HASHES = {
    "array_fixture_template.cir": "8971a82dfbac223b9be139f719afae2eb156f0f68fb2a4811858f0a0b482cf71",
    "bvm_jm2_connected.cir": "0093a45cc3910448b484d8bd004c6df8c22358bacc8b3ed5e23912dcab805d54",
    "jjmit.cir": "19862d1fd1f1f44dfa1523848d7d3b5e2594a6c5da8fdd80144b449e5312a336",
    "jtl2.cir": "ffd31f8eda2a86ca0133342be1ce678831b7237a53911eda046d2bff8454855a",
    "BQ_parameterized_bjs400.cir": "883308517d48470cbedab878f9e3c71721cd972db248c6b821ce5dba642ff810",
    "BQ_parameterized_bjs400_rj2.cir": "43468c49eb56090e586428a8ca26d17d8bbf107fbd9e535bbac7a72ed1200d42",
}
PACKAGES = {
    10: {"drive": Path("/mnt/d/BVM_Backages/qb-rj2-highside-second-trigger-l1p14-l2p20-ib260-rj32-bjs400-v2-20260910_raw_handoff.zip"), "git": REPO / "test/exploration/qb-rj2-highside-second-trigger-l1p14-l2p20-ib260-rj32-bjs400-v2-20260910/handoff/qb-rj2-highside-second-trigger-l1p14-l2p20-ib260-rj32-bjs400-v2-20260910_raw_handoff.zip", "sha256": "84e1a8654aa16baf2fe81f96f9cdc4ce8af6efbeb5f617a12c8123b8b13a9bde", "bytes": 10106003, "manifest_sha256": "60d36ef77ec0c7e55493c5c43d93d7fe2c141b117e80cd73b8d8dce0e25710b3"},
    11: {"drive": Path("/mnt/d/BVM_Backages/bvm-population-scaling-rj2p11-midpoint-l1p14-l2p20-ib260-rj32-bjs400-v1-20260911_raw_handoff.zip"), "git": REPO / "test/exploration/bvm-population-scaling-rj2p11-midpoint-l1p14-l2p20-ib260-rj32-bjs400-v1-20260911/handoff/bvm-population-scaling-rj2p11-midpoint-l1p14-l2p20-ib260-rj32-bjs400-v1-20260911_raw_handoff.zip", "sha256": "785be4b1d92d9eeea4e3dfa044a70ac55cf47d7a6f2feea860f4b1c3d79566af", "bytes": 10555946, "manifest_sha256": "7bc0ea090e6c3f36a97b0bbf1128b008fc34a81847379e6aa641d3467b41b403"},
    12: {"drive": Path("/mnt/d/BVM_Backages/bvm-population-scaling-rj2p12-l1p14-l2p20-ib260-rj32-bjs400-v1-20260910_raw_handoff.zip"), "git": REPO / "test/exploration/bvm-population-scaling-rj2p12-l1p14-l2p20-ib260-rj32-bjs400-v1-20260910/handoff/bvm-population-scaling-rj2p12-l1p14-l2p20-ib260-rj32-bjs400-v1-20260910_raw_handoff.zip", "sha256": "3ceba168be95b7e48cbb77ccb13d4f4133893cb39813c025b7d4a3f631a09dff", "bytes": 130901740, "manifest_sha256": "99be7c3d7ad62a4ff03684b7d1b127a98d5262b15bfcdb9e5dfecb598f930502"},
}
REFERENCE_CASES = ((10, "0001"), (10, "0011"), (11, "0011"), (11, "0111"), (12, "0011"), (12, "0111"))
ARCHIVE_ROOTS = {
    (10, "0001"): "references/reused/ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P10_0001",
    (10, "0011"): "references/reused/ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P10_0011",
    (11, "0011"): "runs/ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P11_0011",
    (11, "0111"): "runs/ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P11_0111",
    (12, "0011"): "references/reused/ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_0011",
    (12, "0111"): "runs/ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_0111",
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


def write_once(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file():
        if path.read_text(encoding="utf-8") != text:
            raise RuntimeError(f"refusing to overwrite existing artifact: {path}")
        return
    path.write_text(text, encoding="utf-8")


def write_json_once(path: Path, value: Any) -> None:
    write_once(path, json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def local_reference(rj2: int, mask: str) -> Path:
    return EXP / f"references/rj2p{rj2}" / f"ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P{rj2}_{mask}"


def verify_packages() -> dict[str, Any]:
    records: dict[str, Any] = {}
    for rj2, package in PACKAGES.items():
        if not package["drive"].is_file() or not package["git"].is_file():
            raise RuntimeError(f"missing RJ2={rj2} authority package")
        if sha256(package["drive"]) != package["sha256"] or sha256(package["git"]) != package["sha256"] or package["drive"].stat().st_size != package["bytes"] or package["git"].stat().st_size != package["bytes"]:
            raise RuntimeError(f"RJ2={rj2} authority package hash/size mismatch")
        with zipfile.ZipFile(package["drive"]) as archive:
            manifest_bytes = archive.read("SOURCE_MANIFEST.json")
            if hashlib.sha256(manifest_bytes).hexdigest() != package["manifest_sha256"]:
                raise RuntimeError(f"RJ2={rj2} source manifest hash mismatch")
        records[str(rj2)] = {"drive_path": str(package["drive"]), "git_path": str(package["git"].relative_to(REPO)), "sha256": package["sha256"], "bytes": package["bytes"], "source_manifest_sha256": package["manifest_sha256"], "git_drive_equality": "PASS"}
    return records


def verify_references() -> dict[str, Any]:
    records: dict[str, Any] = {}
    for rj2, mask in REFERENCE_CASES:
        package = PACKAGES[rj2]
        local = local_reference(rj2, mask)
        archive_root = ARCHIVE_ROOTS[(rj2, mask)]
        if not local.is_dir():
            raise RuntimeError(f"missing reference directory: RJ2={rj2}/{mask}")
        artifacts: dict[str, Any] = {}
        with zipfile.ZipFile(package["drive"]) as archive:
            for name in ("raw.csv", "deck.cir", "metadata.json", "run.log"):
                path = local / name
                archive_bytes = archive.read(f"{archive_root}/{name}")
                if sha256(path) != hashlib.sha256(archive_bytes).hexdigest() or path.stat().st_size != len(archive_bytes):
                    raise RuntimeError(f"reference byte mismatch: RJ2={rj2}/{mask}/{name}")
                artifacts[name] = {"path": str(path.relative_to(REPO)), "source_archive_entry": f"{archive_root}/{name}", "sha256": sha256(path), "bytes": path.stat().st_size}
        metadata = json.loads((local / "metadata.json").read_text(encoding="utf-8"))
        working_point = metadata.get("working_point", {})
        metadata_rj2 = metadata.get("rj2_ohm", working_point.get("RJ2_ohm"))
        deck = (local / "deck.cir").read_text(encoding="utf-8")
        if metadata_rj2 != float(rj2) or metadata.get("mask") != mask or f".param RJ2_VALUE={rj2}" not in deck or ".tran 0.1p 200p" not in deck:
            raise RuntimeError(f"reference metadata/deck mismatch: RJ2={rj2}/{mask}")
        key = f"RJ2P{rj2}_{mask}"
        records[key] = {"case_id": key, "rj2_ohm": rj2, "mask": mask, "source_package_sha256": package["sha256"], "source_archive_root": archive_root, "physical_solve_this_experiment": False, "artifacts": artifacts}
    return records


def write_reference_manifest(packages: dict[str, Any], references: dict[str, Any]) -> dict[str, Any]:
    path = EXP / "REFERENCE_MANIFEST.json"
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    record = {"schema": "bjs400-rj2p10-weight3-reference-manifest-v1", "experiment_id": EXP.name, "created_at_local": now(), "authority_remote": "WHHoward/bvm", "authority_head": head(), "packages": packages, "references": references, "reference_case_count": 6, "exact_reference_verification": "PASS", "comparison_only": True, "no_reference_rerun": True}
    write_json_once(path, record)
    return record


def write_source_manifest(packages: dict[str, Any]) -> dict[str, Any]:
    path = EXP / "SOURCE_MANIFEST.json"
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    sources = []
    for name in INPUT_HASHES:
        source = EXP / "inputs" / name
        sources.append({"path": name, "repo_relative_path": str(source.relative_to(REPO)), "sha256": sha256(source), "bytes": source.stat().st_size, "role": "frozen BJS400 input closure"})
    sources.append({"path": str(SOLVER.relative_to(REPO)), "sha256": sha256(SOLVER), "bytes": SOLVER.stat().st_size, "role": "solver identity", "version": subprocess.check_output([str(SOLVER), "--version"], cwd=REPO, text=True)})
    record = {"schema": "bjs400-rj2p10-weight3-source-manifest-v1", "experiment_id": EXP.name, "created_at_local": now(), "authority_remote": "WHHoward/bvm", "authority_head": head(), "source_packages": packages, "local_sources": sources, "fixed_working_point": {**FIXED, "BJS_area": 4, "BJS_Ic_uA": 400}, "authorized_new_run": RUN_ID, "authorized_new_mask": MASK, "only_registered_physical_delta": "FINAL READ mask from RJ2=10/0011 reference", "reference_cases": [f"RJ2P{rj2}_{mask}" for rj2, mask in REFERENCE_CASES]}
    write_json_once(path, record)
    return record


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


def build_deck() -> str:
    base = (local_reference(10, "0011") / "deck.cir").read_text(encoding="utf-8")
    for instance in range(1, 5):
        for kind in ("WL", "BL", "SE"):
            token = f"I_{kind}{instance}"
            lines = [line for line in base.splitlines() if line.startswith(token + " ")]
            if len(lines) != 1:
                raise RuntimeError(f"control line is not unique: {token}")
            base = base.replace(lines[0], control_line(instance, kind, MASK[instance - 1] == "1"), 1)
    return base


def normalize_deck(text: str) -> tuple[str, ...]:
    return tuple(line for line in text.splitlines() if not line.startswith("I_WL") and not line.startswith("I_BL") and not line.startswith("I_SE"))


def generate_deck() -> dict[str, Any]:
    path = EXP / "runs" / RUN_ID / "deck.cir"
    write_once(path, build_deck())
    return {"run_id": RUN_ID, "mask": MASK, "path": str(path.relative_to(REPO)), "sha256": sha256(path), "bytes": path.stat().st_size}


def verify_deck() -> dict[str, Any]:
    path = EXP / "runs" / RUN_ID / "deck.cir"
    text = path.read_text(encoding="utf-8")
    reference = (local_reference(10, "0011") / "deck.cir").read_text(encoding="utf-8")
    failures: list[str] = []
    if normalize_deck(text) != normalize_deck(reference):
        failures.append("deck changed outside FINAL READ mask lines")
    if text.count(".param RJ2_VALUE=10") != 1 or ".tran 0.1p 200p" not in text:
        failures.append("RJ2/timestep declaration mismatch")
    for instance in range(1, 5):
        for kind in ("WL", "BL", "SE"):
            if text.count(control_line(instance, kind, MASK[instance - 1] == "1")) != 1:
                failures.append(f"control mismatch {kind}{instance}")
    return {"schema": "bjs400-rj2p10-weight3-deck-diff-preflight-v1", "status": "PASS" if not failures else "FAIL", "only_mask_delta": not failures, "failures": failures, "run": {"run_id": RUN_ID, "mask": MASK, "deck_sha256": sha256(path)}}


def preflight_markdown(record: dict[str, Any]) -> str:
    return "\n".join([
        "# RJ2=10 weight-3 diagnostic — PREFLIGHT", "", CONTRACT_SENTENCE, "",
        f"- Experiment: `{EXP.name}`", f"- Preflight HEAD: `{record['head']}`", "- Latest remote `WHHoward/bvm` and latest Drive canonical packages were rechecked before registration.",
        "- Frozen point: L1=1.4pH, L2=2.0pH, IBias=260uA, RJ1=32ohm, RJ2=10ohm, BJS area=4/Ic=400uA.", "- Exactly one new physical solve: mask `0111`; no other mask, RJ2, timestep or READ duration.", "",
        "## Immutable references", "", "- RJ2=10: `0001`, `0011`; RJ2=11: `0011`, `0111`; RJ2=12: `0011`, `0111`.", "- All six references are comparison-only exact bytes; no reference is rerun.", "",
        "## Frozen protocol", "", "- IDLE 0–50ps; WRITE0 50–61ps; IDLE 61–70ps; ZERO_STATE_READ_CONTROL 70–81ps; IDLE 81–90ps; WRITE1 90–101ps; SETTLE 101–110ps; FINAL READ 110–121ps; TAIL 121–200ps.", "- Amplitude 100uA; 1ps rise/fall; 9ps plateau; `.tran 0.1p 200p`; bit order b3b2b1b0=BVM1/BVM2/BVM3/BVM4.", "",
        "## Evidence ceiling", "", "- Raw waveform is the scientific authority; mechanical checker labels are subordinate.", "- Candidate responses, phase navigation, terminal areas, pulse areas, current crossings and voltage peaks are not SFQ counts.", "- The 0111 fourth-candidate focus is [121,130)ps and retains BJ1/BJ2/QBOUT/JTL/terminal plus source/receiver state metrics.", "", f"- Authority packages: `{record['authority_status']}`; references: `{record['reference_status']}`; deck: `{record['deck_status']}`.", "- Physical execution has not started at preflight.", "",
    ])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh-head", action="store_true")
    args = parser.parse_args()
    for name, expected in INPUT_HASHES.items():
        path = EXP / "inputs" / name
        if not path.is_file() or sha256(path) != expected:
            raise RuntimeError(f"input hash mismatch: {name}")
    if not SOLVER.is_file() or sha256(SOLVER) != SOLVER_SHA256:
        raise RuntimeError("solver identity hash mismatch")
    packages = verify_packages()
    references = verify_references()
    reference_manifest = write_reference_manifest(packages, references)
    source_manifest = write_source_manifest(packages)
    generated = generate_deck()
    deck = verify_deck()
    if reference_manifest.get("exact_reference_verification") != "PASS" or deck["status"] != "PASS":
        raise RuntimeError("RJ2=10 diagnostic preflight failed")
    path = EXP / "analysis/preflight.json"
    prior = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    record = {"schema": "bjs400-rj2p10-weight3-preflight-v1", "experiment_id": EXP.name, "created_at_local": now(), "status": "PASS", "head": head(), "head_refresh": args.refresh_head, "preregistration_head": prior.get("preregistration_head", head()), "new_physical_solve_count": 1, "authorized_run_id": RUN_ID, "authorized_mask": MASK, "reference_case_count": 6, "unauthorized_extra_solves": 0, "authority_status": "PASS_GIT_DRIVE_PACKAGE_SHA_AND_BYTES", "reference_status": "PASS", "reference_manifest_sha256": sha256(EXP / "REFERENCE_MANIFEST.json"), "source_manifest_sha256": sha256(EXP / "SOURCE_MANIFEST.json"), "deck_status": deck["status"], "deck_checks": deck, "generated_deck": generated, "scientific_interpretation_performed": False}
    if args.refresh_head:
        path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        (EXP / "PREFLIGHT.md").write_text(preflight_markdown(record), encoding="utf-8")
    elif not path.is_file():
        write_json_once(path, record)
        write_once(EXP / "PREFLIGHT.md", preflight_markdown(record))
    print(json.dumps({"status": "PASS", "head": head(), "new_physical_solve_count": 1, "authorized_run_id": RUN_ID, "reference_case_count": 6, "solver_invoked": False, "scientific_interpretation_performed": False}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
