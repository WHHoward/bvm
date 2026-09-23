#!/usr/bin/env python3
"""Build a traceable delta handoff package and verify its Drive mirror."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

from common import REPO, ROOT, read_json, repo_rel, sha256, write_json

CHECKPOINTS = ROOT / "analysis" / "PACKAGE_CHECKPOINTS.json"
PACKAGE_QA = ROOT / "analysis" / "PACKAGE_QA.json"
MIRROR_DIR = Path("/mnt/d/BVM_Backages")


def excluded(path: Path) -> bool:
    return "__pycache__" in path.parts or path.suffix == ".pyc" or path.name == "PACKAGE_QA.json" or (
        path.parent.name == "handoff" and path.suffix == ".zip")


def excluded_from_finalization_seal(path: Path) -> bool:
    return ("__pycache__" in path.parts or path.suffix == ".pyc" or
            path.name in {"FINAL_QA.json", "FINAL_QA.sha256", "PACKAGE_QA.json", "PACKAGE_CHECKPOINTS.json"} or
            (path.parent.name == "handoff" and path.suffix == ".zip"))


def head_commit() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()


def commit_exists(commit: str) -> bool:
    return subprocess.run(["git", "cat-file", "-e", f"{commit}^{{commit}}"], cwd=REPO,
                          capture_output=True, check=False).returncode == 0


def is_ancestor(base: str, head: str) -> bool:
    return subprocess.run(["git", "merge-base", "--is-ancestor", base, head], cwd=REPO,
                          capture_output=True, check=False).returncode == 0


def registry() -> list[dict[str, Any]]:
    if not CHECKPOINTS.is_file():
        raise RuntimeError("package checkpoint registry missing")
    return list(read_json(CHECKPOINTS).get("checkpoints", []))


def select_base(explicit: str | None, head: str) -> dict[str, Any]:
    candidates = registry()
    valid = []
    for checkpoint in candidates:
        commit = checkpoint.get("head_commit")
        package_path = checkpoint.get("package_path")
        package = REPO / str(package_path or "")
        if not commit or not commit_exists(commit) or not package.is_file():
            continue
        if sha256(package) != checkpoint.get("package_sha256"):
            continue
        valid.append(checkpoint)
    if explicit:
        matches = [item for item in valid if item.get("head_commit") == explicit]
        if not matches:
            raise RuntimeError("explicit base commit has no verified package identity in PACKAGE_CHECKPOINTS.json")
        base = matches[-1]
    else:
        if not valid:
            raise RuntimeError("no verified successful package checkpoint; hard stop, no full-package fallback")
        base = valid[-1]
    if not is_ancestor(str(base["head_commit"]), head):
        raise RuntimeError(f"delta base is not an ancestor of current HEAD: {base['head_commit']} -> {head}")
    return {"base_package_name": base["package_name"],
            "base_package_path": base["package_path"],
            "base_package_sha256": base["package_sha256"],
            "base_commit": base["head_commit"]}


def changed_paths(base: str, head: str) -> dict[str, str]:
    paths: dict[str, str] = {}
    output = subprocess.check_output(["git", "diff", "--name-status", base, head, "--",
                                      repo_rel(ROOT), ".gitattributes"], cwd=REPO, text=True)
    for line in output.splitlines():
        if line.strip():
            status, path = line.split("\t", 1)
            paths[path] = status[0]
    output = subprocess.check_output(["git", "status", "--short", "--untracked-files=all", "--",
                                      repo_rel(ROOT), ".gitattributes"], cwd=REPO, text=True)
    for line in output.splitlines():
        if len(line) >= 4:
            paths[line[3:]] = line[:2].strip()[:1] or "?"
    return paths


def gather_delta(base: str, head: str) -> tuple[list[Path], dict[str, str]]:
    statuses = changed_paths(base, head)
    files = []
    for rel in statuses:
        path = REPO / rel
        if path.is_file() and not excluded(path):
            files.append(path)
    return sorted(set(files)), statuses


def reference_records(base: dict[str, Any]) -> list[dict[str, Any]]:
    comparison = read_json(ROOT / "analysis" / "REGRESSION_COMPARISON.json")
    scope = read_json(ROOT / "analysis" / "REFERENCE_ANALYSIS_SCOPE.json")
    source_lock = read_json(ROOT / "analysis" / "PLATFORM_SOURCE_LOCK.json").get("source_hashes", {})
    frozen_hashes = {item["path"]: item["sha256"] for item in scope.get("authorized_inputs", [])}
    records = []
    for item in comparison.get("comparisons", []):
        raw = REPO / item["reference_raw_path"]
        actual = sha256(raw)
        if actual != item["reference_raw_sha256"] or actual != frozen_hashes.get(item["reference_raw_path"]):
            raise RuntimeError(f"historical reference raw hash changed: {raw}")
        run = REPO / item["reference_run"]
        for suffix, path in (("METADATA", run / "metadata.json"), ("DECK", run / "actual_deck.cir"),
                             ("STIMULUS", run / "stimulus.inc"), ("SOURCE_MANIFEST", run / "source_manifest.json"),
                             ("BVM", run / "snapshot" / "sources" / "bvm_tunable.cir"),
                             ("QB", run / "snapshot" / "sources" / "bq_tunable.cir"),
                             ("JJ", run / "snapshot" / "sources" / "jjmit.cir"),
                             ("JTL", run / "snapshot" / "sources" / "jtl2.cir")):
            locked = source_lock.get(f"{item['case_id']}_REFERENCE_{suffix}", {}).get("sha256")
            if not path.is_file() or not locked or sha256(path) != locked:
                raise RuntimeError(f"historical input differs from frozen source lock: {path}")
        records.append({"source_case": item["case_id"], "raw_path": item["reference_raw_path"],
                        "raw_sha256": actual, "source_package": base["base_package_name"],
                        "source_package_sha256": base["base_package_sha256"],
                        "source_base_commit": base["base_commit"]})
    return records


def included_hashes(files: list[Path]) -> dict[str, str]:
    return {repo_rel(path): sha256(path) for path in files}


def verify_finalization_seal() -> dict[str, Any]:
    final_path = ROOT / "analysis" / "FINAL_QA.json"
    sidecar_path = ROOT / "analysis" / "FINAL_QA.sha256"
    if not final_path.is_file() or not sidecar_path.is_file():
        raise RuntimeError("finalization seal or FINAL_QA SHA sidecar missing")
    final = read_json(final_path)
    sidecar = sidecar_path.read_text(encoding="utf-8").split()
    if len(sidecar) < 1 or sidecar[0] != sha256(final_path):
        raise RuntimeError("FINAL_QA.json differs from its committed SHA-256 sidecar")
    if final.get("status") != "PASS" or final.get("physical_solve_count") != 5 or final.get("authorized_solve_count") != 5:
        raise RuntimeError("delta package requires a valid final QA for exactly five registered solves")
    preflight_path = ROOT / "analysis" / "PREFLIGHT_QA.json"
    execution_path = ROOT / "analysis" / "REGRESSION_EXECUTION.json"
    lock_path = ROOT / "analysis" / "PLATFORM_SOURCE_LOCK.json"
    preflight = read_json(preflight_path)
    execution = read_json(execution_path)
    source_lock = read_json(lock_path)
    if (preflight.get("status") != "PASS" or execution.get("status") != "ALL_REGISTERED_RUNS_COMPLETE" or
            execution.get("completed_solve_count") != 5 or execution.get("authorized_solve_count") != 5 or
            execution.get("physical_solve_count") != 5 or
            execution.get("new_physical_solve_count") != (4 if execution.get("existing_physical_solve_count") == 1 else 5) or
            execution.get("preflight_qa_sha256") != sha256(preflight_path) or
            preflight.get("platform_source_lock_sha256") != sha256(lock_path)):
        raise RuntimeError("delta package refuses stale or incomplete preflight/execution receipts")
    attrs_record = source_lock.get("source_hashes", {}).get("GIT_ATTRIBUTES", {})
    if attrs_record.get("path") != ".gitattributes" or attrs_record.get("sha256") != sha256(REPO / ".gitattributes"):
        raise RuntimeError("Git LFS attributes changed after the registered physical runs")
    expected_ids = [case["case_id"] for case in read_json(ROOT / "REGRESSION_MATRIX.json")["cases"]]
    if [item.get("case_id") for item in execution.get("runs", [])] != expected_ids:
        raise RuntimeError("execution receipt order/case IDs differ from the frozen A–E matrix")
    expected_actions = (["REANALYZED_EXISTING_RAW", *(["NEW_PHYSICAL_SOLVE"] * 4)]
                        if execution.get("existing_physical_solve_count") == 1 else
                        ["NEW_PHYSICAL_SOLVE"] * 5)
    if [item.get("action") for item in execution.get("runs", [])] != expected_actions:
        raise RuntimeError("execution actions do not match a fresh A–E batch or registered A-recovery/B–E resume")
    for item in execution["runs"]:
        expected_receipt = ROOT / "analysis" / "receipts" / f"{item['case_id']}.json"
        if item.get("receipt_path") != repo_rel(expected_receipt):
            raise RuntimeError(f"execution receipt path escapes/does not match case ID: {item.get('case_id')}")
        receipt_path = expected_receipt
        if not receipt_path.is_file() or sha256(receipt_path) != item.get("receipt_sha256"):
            raise RuntimeError(f"independent execution receipt changed: {item.get('case_id')}")
        receipt = read_json(receipt_path)
        expected_run = ROOT / "runs" / item["case_id"]
        if receipt.get("run_dir") != repo_rel(expected_run):
            raise RuntimeError(f"receipt run path escapes/does not match case ID: {item.get('case_id')}")
        run = expected_run
        if item.get("action") == "REANALYZED_EXISTING_RAW":
            if (receipt.get("execution_status") != "RUN_PASS" or
                    receipt.get("artifact_status") != "INVALID" or
                    receipt.get("runner_exit_code") == 0 or
                    receipt.get("physical_solve_count") != 1):
                raise RuntimeError(f"original recovered-A solve receipt is not preserved: {item.get('case_id')}")
            recovery_path = ROOT / "analysis" / "receipts" / f"{item['case_id']}_reanalysis.json"
            if (item.get("analysis_recovery_receipt_path") != repo_rel(recovery_path) or
                    not recovery_path.is_file() or
                    sha256(recovery_path) != item.get("analysis_recovery_receipt_sha256")):
                raise RuntimeError(f"A reanalysis receipt is missing or changed: {item.get('case_id')}")
            recovery = read_json(recovery_path)
            current_tree = {repo_rel(path): sha256(path) for path in sorted(run.rglob("*"))
                            if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"}
            if (recovery.get("action") != "REANALYZED_EXISTING_RAW_NO_SOLVE" or
                    recovery.get("artifact_status") != "VALID" or
                    recovery.get("physical_solve_count") != 1 or
                    recovery.get("new_physical_solve_count") != 0 or
                    recovery.get("raw_sha256") != receipt.get("artifact_sha256", {}).get("raw") or
                    recovery.get("run_tree_file_sha256") != current_tree):
                raise RuntimeError(f"A analysis-recovery receipt does not bind the current run: {item.get('case_id')}")
            stable_keys = ("raw", "deck", "stimulus", "config_snapshot", "stimulus_snapshot",
                           "metadata", "source_manifest")
            for key in stable_keys:
                path = {"raw": run / "raw.csv", "deck": run / "actual_deck.cir",
                        "stimulus": run / "stimulus.inc", "config_snapshot": run / "config_snapshot.env",
                        "stimulus_snapshot": run / "stimulus_snapshot.json", "metadata": run / "metadata.json",
                        "source_manifest": run / "source_manifest.json"}[key]
                if not path.is_file() or sha256(path) != receipt.get("artifact_sha256", {}).get(key):
                    raise RuntimeError(f"original A solve input/provenance changed: {item.get('case_id')}/{key}")
            for key, path in (("raw", run / "raw.csv"), ("deck", run / "actual_deck.cir"),
                              ("stimulus", run / "stimulus.inc"), ("config_snapshot", run / "config_snapshot.env"),
                              ("stimulus_snapshot", run / "stimulus_snapshot.json"),
                              ("metadata", run / "metadata.json"), ("result", run / "result.json"),
                              ("source_manifest", run / "source_manifest.json")):
                if not path.is_file() or sha256(path) != recovery.get("artifact_sha256", {}).get(key):
                    raise RuntimeError(f"reanalyzed A artifact changed: {item.get('case_id')}/{key}")
        else:
            if receipt.get("runner_exit_code") != 0 or receipt.get("artifact_status") != "VALID" or receipt.get("physical_solve_count") != 1:
                raise RuntimeError(f"invalid physical run receipt: {item.get('case_id')}")
            for key, path in (("raw", run / "raw.csv"), ("deck", run / "actual_deck.cir"),
                              ("stimulus", run / "stimulus.inc"), ("config_snapshot", run / "config_snapshot.env"),
                              ("stimulus_snapshot", run / "stimulus_snapshot.json"),
                              ("metadata", run / "metadata.json"), ("result", run / "result.json"),
                              ("source_manifest", run / "source_manifest.json")):
                if not path.is_file() or sha256(path) != receipt.get("artifact_sha256", {}).get(key):
                    raise RuntimeError(f"solve receipt artifact changed: {item.get('case_id')}/{key}")
    sealed = final.get("sealed_file_sha256", {})
    actual_files = {repo_rel(path): path for path in ROOT.rglob("*")
                    if path.is_file() and not excluded_from_finalization_seal(path)}
    # These two files are excluded from the self-seal to avoid recursion, but must exist
    # and are checked separately (FINAL_QA.json via its SHA sidecar above).
    actual_files[repo_rel(final_path)] = final_path
    actual_files[repo_rel(sidecar_path)] = sidecar_path
    expected_paths = set(sealed) | {repo_rel(final_path), repo_rel(sidecar_path)}
    if set(actual_files) != expected_paths:
        raise RuntimeError(f"evidence file set differs from finalization seal: unexpected={sorted(set(actual_files)-expected_paths)[:8]}, missing={sorted(expected_paths-set(actual_files))[:8]}")
    for relative, expected_hash in sealed.items():
        path = REPO / relative
        if not path.is_file() or sha256(path) != expected_hash:
            raise RuntimeError(f"evidence changed after finalization: {relative}")
    result = read_json(ROOT / "result.json")
    if (result.get("artifact_status") != "VALID" or result.get("physical_solve_count") != 5 or
            result.get("new_physical_solve_count") != final.get("new_physical_solve_count")):
        raise RuntimeError("root result.json is not bound to five valid artifacts")
    return final


def require_clean_pushed_head() -> str:
    status = subprocess.check_output(["git", "status", "--short", "--untracked-files=all"], cwd=REPO, text=True)
    if status.strip():
        raise RuntimeError("evidence/package inputs must be committed with a clean worktree before archive creation")
    head = head_commit()
    try:
        remote = subprocess.check_output(["git", "ls-remote", "bvm", "refs/heads/master"], cwd=REPO,
                                         text=True, timeout=30).strip()
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError(f"cannot verify pushed bvm/master before packaging: {exc}") from exc
    remote_head = remote.split()[0] if remote else ""
    if not remote_head or not is_ancestor(head, remote_head):
        raise RuntimeError("the committed evidence HEAD must be pushed to bvm/master before delta archive creation")
    return head


def make_manifest(base: dict[str, Any], head: str, files: list[Path], statuses: dict[str, str]) -> dict[str, Any]:
    new_files = []
    modified_files = []
    for path in files:
        rel = repo_rel(path)
        exists = subprocess.run(["git", "cat-file", "-e", f"{base['base_commit']}:{rel}"], cwd=REPO,
                                capture_output=True, check=False).returncode == 0
        (modified_files if exists else new_files).append(rel)
    final_qa = verify_finalization_seal()
    solve_count = int(final_qa.get("physical_solve_count", -1))
    new_solve_count = int(final_qa.get("new_physical_solve_count", -1))
    if final_qa.get("status") != "PASS" or solve_count != int(final_qa.get("authorized_solve_count", -2)) or solve_count != 5:
        raise RuntimeError("evidence delta requires FINAL_QA PASS with exactly five authorized solves")
    return {
        "schema": "bvm-qb-repeatability-delta-manifest-v1", "package_type": "delta",
        "base_package_name": base["base_package_name"],
        "base_package_path": base["base_package_path"],
        "base_package_sha256": base["base_package_sha256"],
        "base_commit": base["base_commit"], "head_commit": head,
        "included_files": [repo_rel(path) for path in files],
        "included_file_sha256": included_hashes(files),
        "new_files": sorted(new_files), "modified_files": sorted(modified_files),
        "referenced_existing_cases": reference_records(base),
        "referenced_existing_raw_sha256": {item["raw_path"]: item["raw_sha256"] for item in reference_records(base)},
        "physical_solve_count": solve_count,
        "existing_physical_solve_count": int(final_qa.get("existing_physical_solve_count", 0)),
        "new_physical_solve_count": new_solve_count, "reused_point_count": 0,
        "scientific_interpretation_performed": False,
    }


def preview(tag: str, head: str, base: dict[str, Any], files: list[Path], manifest: dict[str, Any]) -> None:
    print("PACKAGE PREVIEW")
    print(f"mode=delta\ntag={tag}\nhead_commit={head}")
    print(f"base_package={base['base_package_name']}\nbase_sha256={base['base_package_sha256']}\nbase_commit={base['base_commit']}")
    print(f"included_files={len(files)}\nestimated_uncompressed_bytes={sum(path.stat().st_size for path in files)}")
    print(f"new_files={len(manifest['new_files'])}\nmodified_files={len(manifest['modified_files'])}")
    print("REFERENCED EXISTING RAWS")
    for item in manifest["referenced_existing_cases"]:
        print(f"{item['source_case']} {item['raw_path']} sha256={item['raw_sha256']}")
    print(f"new_physical_solve_count={manifest['new_physical_solve_count']} reused_point_count=0")
    print("No archive created.")


def verify_archive(package: Path, files: list[Path], manifest: dict[str, Any]) -> dict[str, Any]:
    expected = set(manifest["included_files"]) | {"DELTA_MANIFEST.json"}
    included_checks = {}
    with zipfile.ZipFile(package, "r") as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or set(names) != expected:
            raise RuntimeError("archive member list differs from the registered delta manifest")
        for rel, expected_hash in manifest["included_file_sha256"].items():
            actual = hashlib.sha256(archive.read(rel)).hexdigest()
            included_checks[rel] = actual == expected_hash
            if actual != expected_hash:
                raise RuntimeError(f"archive member hash mismatch: {rel}")
        embedded = json.loads(archive.read("DELTA_MANIFEST.json"))
        if embedded != manifest:
            raise RuntimeError("embedded DELTA_MANIFEST.json differs from the generated manifest")
    return included_checks


def verify_existing_archive(package: Path) -> dict[str, Any]:
    with zipfile.ZipFile(package, "r") as archive:
        names = archive.namelist()
        if names.count("DELTA_MANIFEST.json") != 1:
            raise RuntimeError("delta archive has no unique embedded manifest")
        manifest = json.loads(archive.read("DELTA_MANIFEST.json"))
        expected = set(manifest.get("included_files", [])) | {"DELTA_MANIFEST.json"}
        if len(names) != len(set(names)) or set(names) != expected:
            raise RuntimeError("delta archive contents do not match its embedded manifest")
        for rel, expected_hash in manifest.get("included_file_sha256", {}).items():
            actual = hashlib.sha256(archive.read(rel)).hexdigest()
            if actual != expected_hash:
                raise RuntimeError(f"archived file hash mismatch during mirror completion: {rel}")
    return manifest


def complete_mirror() -> int:
    if not PACKAGE_QA.is_file():
        raise RuntimeError("PACKAGE_QA.json missing; create the immutable delta package first")
    qa = read_json(PACKAGE_QA)
    if qa.get("package_type") != "delta" or qa.get("status") not in {"ANALYSIS_MIRROR_PENDING", "PASS"}:
        raise RuntimeError("package QA is not awaiting mirror completion")
    verify_finalization_seal()
    package = REPO / qa["package"]
    if not package.is_file() or sha256(package) != qa.get("package_sha256"):
        raise RuntimeError("local package is missing or its SHA-256 changed")
    package_rel = repo_rel(package)
    tracked = subprocess.run(["git", "ls-files", "--error-unmatch", package_rel], cwd=REPO,
                             capture_output=True, check=False).returncode == 0
    pointer_commit = subprocess.run(["git", "cat-file", "-e", f"HEAD:{package_rel}"], cwd=REPO,
                                    capture_output=True, check=False).returncode == 0
    attributes = subprocess.check_output(["git", "check-attr", "filter", "--", package_rel], cwd=REPO, text=True)
    is_lfs = attributes.rstrip().endswith("filter: lfs")
    status = subprocess.check_output(["git", "status", "--short", "--", package_rel], cwd=REPO, text=True)
    if not (tracked and pointer_commit and is_lfs and not status.strip()):
        raise RuntimeError("package LFS pointer must be committed before Drive mirror completion")
    try:
        remote = subprocess.check_output(["git", "ls-remote", "bvm", "refs/heads/master"], cwd=REPO,
                                         text=True, timeout=30).strip()
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError(f"cannot verify pushed bvm/master before Drive mirroring: {exc}") from exc
    remote_head = remote.split()[0] if remote else ""
    current_head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()
    if not remote_head or not is_ancestor(current_head, remote_head):
        raise RuntimeError("current committed package pointer has not been pushed to bvm/master")
    lfs_paths = subprocess.check_output(["git", "lfs", "ls-files", "--name-only"], cwd=REPO, text=True).splitlines()
    if package_rel not in lfs_paths:
        raise RuntimeError("package path is not registered as a Git LFS object")
    embedded = verify_existing_archive(package)
    if embedded.get("package_type") != "delta" or embedded.get("base_package_sha256") != qa.get("base_package_sha256"):
        raise RuntimeError("embedded delta base identity differs from PACKAGE_QA")
    verified_base = select_base(qa.get("base_commit"), current_head)
    if (verified_base["base_package_sha256"] != qa.get("base_package_sha256") or
            verified_base["base_package_name"] != qa.get("base_package_name")):
        raise RuntimeError("delta base identity no longer verifies")
    scope = read_json(ROOT / "analysis" / "REFERENCE_ANALYSIS_SCOPE.json")
    frozen_reference_hashes = {item["path"]: item["sha256"] for item in scope.get("authorized_inputs", [])}
    for path, expected_hash in embedded.get("referenced_existing_raw_sha256", {}).items():
        raw = REPO / path
        if (not raw.is_file() or sha256(raw) != expected_hash or
                frozen_reference_hashes.get(path) != expected_hash):
            raise RuntimeError(f"reference raw hash changed before Drive mirroring: {path}")
    mirror = Path(qa.get("mirror") or (MIRROR_DIR / package.name))
    mirror.parent.mkdir(parents=True, exist_ok=True)
    if mirror.exists():
        if sha256(mirror) != qa["package_sha256"]:
            raise RuntimeError(f"refusing to overwrite a different existing mirror: {mirror}")
    else:
        shutil.copy2(package, mirror)
    mirror_hash = sha256(mirror)
    if mirror_hash != qa["package_sha256"]:
        raise RuntimeError("Drive mirror SHA-256 differs from the committed package")
    qa.update({"status": "PASS", "mirror": str(mirror), "mirror_sha256": mirror_hash,
               "mirror_bytes": mirror.stat().st_size,
               "mirror_completed_after_package_commit": True,
               "mirror_completion_head_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip(),
               "archive_contents_verified_after_package_commit": True})
    write_json(PACKAGE_QA, qa)
    print(json.dumps(qa, ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Package the immutable A–E evidence delta")
    parser.add_argument("--tag", required=True)
    parser.add_argument("--base-commit")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--create-only", action="store_true", help="create and QA the archive; mirror it only after its LFS commit is pushed")
    parser.add_argument("--complete-mirror", action="store_true", help="after commit/push, copy exact bytes to the configured Drive mirror and finalize PACKAGE_QA")
    args = parser.parse_args()
    if args.complete_mirror:
        if args.dry_run or args.create_only or args.base_commit:
            raise RuntimeError("--complete-mirror cannot be combined with creation options")
        return complete_mirror()
    if not args.dry_run and not args.create_only:
        raise RuntimeError("delta creation must use --create-only; Drive mirroring is blocked until the committed LFS pointer is pushed")
    head = head_commit()
    base = select_base(args.base_commit, head)
    files, statuses = gather_delta(base["base_commit"], head)
    manifest = make_manifest(base, head, files, statuses)
    if args.dry_run:
        preview(args.tag, head, base, files, manifest)
        return 0
    pushed_head = require_clean_pushed_head()
    if pushed_head != head:
        raise RuntimeError("HEAD changed during package planning; rerun delta dry-run")

    handoff = ROOT / "handoff"
    handoff.mkdir(parents=True, exist_ok=True)
    package = handoff / f"{ROOT.name}_delta_{args.tag}.zip"
    if package.exists():
        raise RuntimeError(f"refusing to overwrite immutable package: {package}")
    with zipfile.ZipFile(package, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in files:
            archive.write(path, repo_rel(path))
        archive.writestr("DELTA_MANIFEST.json", json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    included_qa = verify_archive(package, files, manifest)
    package_hash = sha256(package)
    mirror = MIRROR_DIR / package.name
    mirror_hash = None
    mirror_bytes = None
    status = "ANALYSIS_MIRROR_PENDING"
    final_base = select_base(base["base_commit"], head)
    ref_checks = []
    for item in manifest["referenced_existing_cases"]:
        path = REPO / item["raw_path"]
        match = path.is_file() and sha256(path) == item["raw_sha256"]
        ref_checks.append({"raw_path": item["raw_path"], "sha256": item["raw_sha256"], "verified": match})
    qa = {
        "schema": "bvm-qb-repeatability-package-qa-v1",
        "status": status if all(included_qa.values()) and all(x["verified"] for x in ref_checks) else "FAIL",
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "package_type": "delta", "package": repo_rel(package), "package_sha256": package_hash,
        "package_bytes": package.stat().st_size, "package_file_count": len(files) + 1,
        "included_file_sha256": manifest["included_file_sha256"],
        "included_file_hashes_verified": all(included_qa.values()),
        "mirror": str(mirror), "mirror_sha256": mirror_hash, "mirror_bytes": mirror_bytes,
        "base_package_name": final_base["base_package_name"],
        "base_package_sha256": final_base["base_package_sha256"], "base_commit": final_base["base_commit"],
        "head_commit": head, "referenced_existing_raw_checks": ref_checks,
        "new_physical_solve_count": int(manifest["new_physical_solve_count"]), "reused_point_count": 0,
        "raw_immutable": True, "scientific_interpretation_performed": False,
    }
    if args.create_only:
        qa["mirror_completion_required_after_commit_push"] = True
    write_json(PACKAGE_QA, qa)
    checkpoints = read_json(CHECKPOINTS)
    checkpoints["checkpoints"].append({"package_name": package.name,
                                       "package_path": repo_rel(package),
                                       "package_sha256": package_hash,
                                       "head_commit": head,
                                       "source": args.tag})
    write_json(CHECKPOINTS, checkpoints)
    print(json.dumps(qa, ensure_ascii=False, indent=2))
    return 0 if qa["status"] in {"PASS", "ANALYSIS_MIRROR_PENDING"} else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, ValueError, KeyError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
