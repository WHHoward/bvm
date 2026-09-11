#!/usr/bin/env python3
"""Register the RJ2=11 midpoint experiment without invoking JoSIM."""

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
AUTH = REPO / "test/exploration/bvm-population-scaling-rj2p12-l1p14-l2p20-ib260-rj32-bjs400-v1-20260910"
AUTH_PACKAGE = AUTH / "handoff/bvm-population-scaling-rj2p12-l1p14-l2p20-ib260-rj32-bjs400-v1-20260910_raw_handoff.zip"
DRIVE_PACKAGE = Path("/mnt/d/BVM_Backages/bvm-population-scaling-rj2p12-l1p14-l2p20-ib260-rj32-bjs400-v1-20260910_raw_handoff.zip")
SOLVER = REPO / "build/josim-cli"
CONTRACT_SENTENCE = "This experiment is governed by docs/EXPERIMENT_CONTRACT.md."
AUTH_PACKAGE_SHA256 = "3ceba168be95b7e48cbb77ccb13d4f4133893cb39813c025b7d4a3f631a09dff"
AUTH_PACKAGE_BYTES = 130901740
AUTH_SOURCE_MANIFEST_SHA256 = "99be7c3d7ad62a4ff03684b7d1b127a98d5262b15bfcdb9e5dfecb598f930502"
AUTH_ORACLE_SHA256 = "b07056580cdd913efcf5317a8856c9a8023c8c9499ede89d236e837d20950166"
SOLVER_SHA256 = "48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2"
FIXED = {"L1_pH": 1.4, "L2_pH": 2.0, "IBias_uA": 260.0, "RJ1_ohm": 32.0, "RJ2_ohm": 11.0}
REFERENCE_FIXED = {**FIXED, "RJ2_ohm": 12.0}
MASKS = ("0001", "0011", "0111", "1111")
NEW_RUNS = tuple(f"ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P11_{mask}" for mask in MASKS)
RUN_TO_MASK = {run_id: run_id.rsplit("_", 1)[1] for run_id in NEW_RUNS}
REFERENCE_RUNS = tuple(f"ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_{mask}" for mask in MASKS)
REFERENCE_ARCHIVE_ENTRIES = {
    "0001": "references/reused/ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_0001",
    "0011": "references/reused/ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_0011",
    "0111": "runs/ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_0111",
    "1111": "runs/ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_1111",
}
INPUT_HASHES = {
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


def write_once(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file():
        if path.read_text(encoding="utf-8") != text:
            raise RuntimeError(f"refusing to overwrite existing artifact: {path}")
        return
    path.write_text(text, encoding="utf-8")


def write_json_once(path: Path, value: Any) -> None:
    write_once(path, json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def local_reference(mask: str) -> Path:
    return EXP / "references/rj2p12" / f"ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_{mask}"


def authority_reference(mask: str) -> Path:
    if mask in {"0001", "0011"}:
        return AUTH / "references/reused" / f"ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_{mask}"
    return AUTH / "runs" / f"ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_{mask}"


def verify_authority() -> dict[str, Any]:
    paths = {"git_package": AUTH_PACKAGE, "drive_package": DRIVE_PACKAGE, "git_source_manifest": AUTH / "SOURCE_MANIFEST.json"}
    if any(not path.is_file() for path in paths.values()):
        raise RuntimeError(f"missing authority artifact: {paths}")
    if sha256(AUTH_PACKAGE) != AUTH_PACKAGE_SHA256 or sha256(DRIVE_PACKAGE) != AUTH_PACKAGE_SHA256 or AUTH_PACKAGE.stat().st_size != AUTH_PACKAGE_BYTES or DRIVE_PACKAGE.stat().st_size != AUTH_PACKAGE_BYTES:
        raise RuntimeError("latest canonical RJ2=12 package hash/size mismatch")
    if sha256(paths["git_source_manifest"]) != AUTH_SOURCE_MANIFEST_SHA256:
        raise RuntimeError("latest Git source manifest hash mismatch")
    with zipfile.ZipFile(DRIVE_PACKAGE) as archive:
        manifest_bytes = archive.read("SOURCE_MANIFEST.json")
        if hashlib.sha256(manifest_bytes).hexdigest() != AUTH_SOURCE_MANIFEST_SHA256:
            raise RuntimeError("latest Drive source manifest hash mismatch")
    return {"git_package_sha256": sha256(AUTH_PACKAGE), "drive_package_sha256": sha256(DRIVE_PACKAGE), "package_bytes": AUTH_PACKAGE.stat().st_size, "source_manifest_sha256": AUTH_SOURCE_MANIFEST_SHA256, "authority_remote": "WHHoward/bvm", "authority_head": head()}


def verify_references() -> dict[str, Any]:
    records: dict[str, Any] = {}
    with zipfile.ZipFile(DRIVE_PACKAGE) as archive:
        for mask in MASKS:
            local = local_reference(mask)
            authority = authority_reference(mask)
            archive_root = REFERENCE_ARCHIVE_ENTRIES[mask]
            if not local.is_dir() or not authority.is_dir():
                raise RuntimeError(f"missing RJ2=12 reference directory: {mask}")
            artifacts: dict[str, Any] = {}
            for name in ("raw.csv", "deck.cir", "metadata.json", "run.log"):
                local_path, authority_path = local / name, authority / name
                archive_bytes = archive.read(f"{archive_root}/{name}")
                if sha256(local_path) != sha256(authority_path) or sha256(local_path) != hashlib.sha256(archive_bytes).hexdigest() or local_path.stat().st_size != len(archive_bytes):
                    raise RuntimeError(f"RJ2=12 reference byte mismatch: {mask}/{name}")
                artifacts[name] = {"path": str(local_path.relative_to(REPO)), "source_git_path": str(authority_path.relative_to(REPO)), "source_archive_entry": f"{archive_root}/{name}", "sha256": sha256(local_path), "bytes": local_path.stat().st_size}
            metadata = json.loads((local / "metadata.json").read_text(encoding="utf-8"))
            deck_text = (local / "deck.cir").read_text(encoding="utf-8")
            metadata_rj2 = metadata.get("rj2_ohm", metadata.get("working_point", {}).get("RJ2_ohm"))
            if metadata_rj2 != 12.0 or metadata.get("mask") != mask or ".param RJ2_VALUE=12" not in deck_text or ".tran 0.1p 200p" not in deck_text:
                raise RuntimeError(f"RJ2=12 reference metadata/deck mismatch: {mask}")
            records[mask] = {"run_id": REFERENCE_RUNS[MASKS.index(mask)], "parameters": {**REFERENCE_FIXED, "mask": mask, "timestep_ps": 0.1}, "source_git_run": str(authority.relative_to(REPO)), "source_archive_root": archive_root, "physical_solve_this_experiment": False, "artifacts": artifacts}
    return records


def write_reference_manifest(authority: dict[str, Any], references: dict[str, Any]) -> dict[str, Any]:
    path = EXP / "REFERENCE_MANIFEST.json"
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    record = {"schema": "bjs400-rj2p11-exact-rj2p12-reference-manifest-v1", "experiment_id": EXP.name, "created_at_local": now(), "source_authority": "WHHoward/bvm", "source_authority_git_head": authority["authority_head"], "source_authority_experiment": str(AUTH.relative_to(REPO)), "source_authority_package_git": str(AUTH_PACKAGE.relative_to(REPO)), "source_authority_package_drive": str(DRIVE_PACKAGE), "source_authority_package_sha256": AUTH_PACKAGE_SHA256, "source_authority_package_bytes": AUTH_PACKAGE_BYTES, "source_authority_source_manifest_sha256": AUTH_SOURCE_MANIFEST_SHA256, "references": references, "reference_case_count": 4, "exact_reference_verification": "PASS", "rj2p12_is_comparison_only": True, "no_rj2p11_reuse": True}
    write_json_once(path, record)
    return record


def write_source_manifest(authority: dict[str, Any]) -> dict[str, Any]:
    path = EXP / "SOURCE_MANIFEST.json"
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    sources = []
    for name, role in ((name, "frozen BJS400 input closure") for name in INPUT_HASHES):
        source = EXP / "inputs" / name
        sources.append({"path": name, "repo_relative_path": str(source.relative_to(REPO)), "sha256": sha256(source), "bytes": source.stat().st_size, "role": role})
    sources.append({"path": str(SOLVER.relative_to(REPO)), "sha256": sha256(SOLVER), "bytes": SOLVER.stat().st_size, "role": "solver identity", "version": subprocess.check_output([str(SOLVER), "--version"], cwd=REPO, text=True)})
    record = {"schema": "bjs400-rj2p11-midpoint-source-manifest-v1", "experiment_id": EXP.name, "created_at_local": now(), "authority_remote": "WHHoward/bvm", "authority_git_head": authority["authority_head"], "authority_experiment": str(AUTH.relative_to(REPO)), "authority_package_sha256": AUTH_PACKAGE_SHA256, "authority_package_bytes": AUTH_PACKAGE_BYTES, "authority_source_manifest_sha256": AUTH_SOURCE_MANIFEST_SHA256, "local_sources": sources, "fixed_working_point": {**FIXED, "BJS_area": 4, "BJS_Ic_uA": 400}, "authorized_new_masks": list(MASKS), "reference_masks": list(MASKS), "only_registered_physical_delta": "RJ2 12ohm -> 11ohm"}
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


def build_deck(mask: str) -> str:
    base = (local_reference("0001") / "deck.cir").read_text(encoding="utf-8")
    token = ".param RJ2_VALUE=12"
    if base.count(token) != 1:
        raise RuntimeError("reference deck does not contain one RJ2_VALUE=12 declaration")
    base = base.replace(token, ".param RJ2_VALUE=11", 1)
    for instance in range(1, 5):
        for kind in ("WL", "BL", "SE"):
            old_token = f"I_{kind}{instance}"
            old_lines = [line for line in base.splitlines() if line.startswith(old_token + " ")]
            if len(old_lines) != 1:
                raise RuntimeError(f"control line is not unique: {old_token}")
            base = base.replace(old_lines[0], control_line(instance, kind, mask[instance - 1] == "1"), 1)
    return base


def normalize_deck(text: str) -> tuple[str, ...]:
    return tuple(line for line in text.splitlines() if not line.startswith(".param RJ2_VALUE=") and not line.startswith("I_WL") and not line.startswith("I_BL") and not line.startswith("I_SE"))


def generate_decks() -> dict[str, Any]:
    generated = {}
    for run_id in NEW_RUNS:
        path = EXP / "runs" / run_id / "deck.cir"
        write_once(path, build_deck(RUN_TO_MASK[run_id]))
        generated[run_id] = {"mask": RUN_TO_MASK[run_id], "parameters": {**FIXED, "mask": RUN_TO_MASK[run_id]}, "path": str(path.relative_to(REPO)), "sha256": sha256(path), "bytes": path.stat().st_size}
    return generated


def verify_decks() -> dict[str, Any]:
    failures: list[str] = []
    reference = (local_reference("0001") / "deck.cir").read_text(encoding="utf-8")
    for run_id in NEW_RUNS:
        path = EXP / "runs" / run_id / "deck.cir"
        text = path.read_text(encoding="utf-8")
        if normalize_deck(text) != normalize_deck(reference):
            failures.append(f"{run_id}: changed content outside RJ2 declaration and FINAL READ controls")
        if text.count(".param RJ2_VALUE=11") != 1 or ".param RJ2_VALUE=12" in text or ".tran 0.1p 200p" not in text:
            failures.append(f"{run_id}: RJ2/timestep declaration mismatch")
        for instance in range(1, 5):
            for kind in ("WL", "BL", "SE"):
                expected = control_line(instance, kind, RUN_TO_MASK[run_id][instance - 1] == "1")
                if text.count(expected) != 1:
                    failures.append(f"{run_id}: control mismatch {kind}{instance}")
    return {"schema": "bjs400-rj2p11-deck-diff-preflight-v1", "status": "PASS" if not failures else "FAIL", "only_rj2_and_mask_delta": not failures, "new_run_count": len(NEW_RUNS), "failures": failures, "runs": {run_id: {"mask": RUN_TO_MASK[run_id], "deck_sha256": sha256(EXP / "runs" / run_id / "deck.cir")} for run_id in NEW_RUNS}}


def preflight_markdown(record: dict[str, Any]) -> str:
    return "\n".join([
        "# RJ2=11 midpoint — PREFLIGHT", "", CONTRACT_SENTENCE, "",
        f"- Experiment: `{EXP.name}`", f"- Preflight HEAD: `{record['head']}`", "- Latest remote/source HEAD was rechecked before registration.",
        "- Frozen working point: L1=1.4pH, L2=2.0pH, IBias=260uA, RJ1=32ohm, RJ2=11ohm, BJS area=4/Ic=400uA.",
        "- Sole physical parameter delta from the RJ2=12 authority: RJ2 12ohm -> 11ohm.", "",
        "## Exact matrix", "", "- Fresh physical solves: `0001`, `0011`, `0111`, `1111` only.", "- Four RJ2=12 reference cases are byte-exact comparison evidence only; no RJ2=12 raw is reused as an RJ2=11 physical case.", "- Total new physical solves: exactly 4; no other masks, RJ2 values or timestep values.", "",
        "## Frozen protocol", "", "- IDLE 0–50ps; WRITE0 50–61ps; IDLE 61–70ps; ZERO_STATE_READ_CONTROL 70–81ps; IDLE 81–90ps; WRITE1 90–101ps; SETTLE 101–110ps; mask-selective FINAL READ 110–121ps; TAIL 121–200ps.", "- Amplitude 100uA; 1ps rise/fall; 9ps plateau; `.tran 0.1p 200p`; bit order b3b2b1b0=BVM1/BVM2/BVM3/BVM4.", "",
        "## Evidence ceiling", "", "- Raw waveform files are the scientific authority for later review.", "- Phase landmarks use raw radians converted by `/ (2*pi)` for navigation only; no phase turn, area, current peak, L1 crossing or terminal pulse is an SFQ count.", "- The generalized oracle and mechanical checker are subordinate QA/navigation tools; conflicts with raw evidence remain visible.", "", f"- Authority package equality: `{record['authority_package_status']}`; exact references: `{record['reference_status']}`; deck checks: `{record['deck_status']}`.", "- Physical execution has not started at preflight.", "",
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
    authority = verify_authority()
    references = verify_references()
    reference_manifest = write_reference_manifest(authority, references)
    source_manifest = write_source_manifest(authority)
    generated = generate_decks()
    decks = verify_decks()
    if decks["status"] != "PASS" or reference_manifest.get("exact_reference_verification") != "PASS":
        raise RuntimeError("RJ2=11 midpoint preflight failed")
    path = EXP / "analysis/preflight.json"
    prior = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    record = {"schema": "bjs400-rj2p11-midpoint-preflight-v1", "experiment_id": EXP.name, "created_at_local": now(), "status": "PASS", "head": head(), "head_refresh": args.refresh_head, "preregistration_head": prior.get("preregistration_head", head()), "new_physical_solve_count": 4, "reference_case_count": 4, "unauthorized_extra_solves": 0, "authorized_masks": list(MASKS), "reference_masks": list(MASKS), "fixed_working_point": {**FIXED, "BJS_area": 4, "BJS_Ic_uA": 400}, "authority_package_status": "PASS_GIT_DRIVE_SHA_AND_BYTES", "authority_package_sha256": AUTH_PACKAGE_SHA256, "authority_package_bytes": AUTH_PACKAGE_BYTES, "authority_source_manifest_sha256": AUTH_SOURCE_MANIFEST_SHA256, "authority_oracle_sha256": AUTH_ORACLE_SHA256, "reference_status": "PASS", "reference_manifest_sha256": sha256(EXP / "REFERENCE_MANIFEST.json"), "source_manifest_sha256": sha256(EXP / "SOURCE_MANIFEST.json"), "deck_status": decks["status"], "deck_checks": decks, "generated_decks": generated, "scientific_analysis_performed": False}
    if args.refresh_head:
        path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        (EXP / "PREFLIGHT.md").write_text(preflight_markdown(record), encoding="utf-8")
    elif not path.is_file():
        write_json_once(path, record)
        write_once(EXP / "PREFLIGHT.md", preflight_markdown(record))
    print(json.dumps({"status": "PASS", "head": head(), "new_physical_solve_count": 4, "reference_case_count": 4, "authorized_masks": list(MASKS), "solver_invoked": False, "scientific_analysis_performed": False}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
