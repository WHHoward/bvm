#!/usr/bin/env python3
"""Scoped source/package/push workflow for the new 4x4 diagonal experiment."""

from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Any

SERIES = Path(__file__).resolve().parents[1]
REPO = SERIES.parents[2]
RUNS = SERIES / "runs"
HANDOFF = SERIES / "handoff"
MIRROR_DEFAULT = Path("/mnt/d/BVM_Backages")
ROOT_SUBMIT_PATH = REPO / "scripts" / "submit.py"
BUS400_PARENT_HEAD = "3de08ba0fd5997b253269849dbc1a535786c8fd6"
BUS400_RUN_IDS = ("A007_BUS400_D3_N0", "A008_BUS400_D3_N1")
A009_RUN_IDS = ("A009_paper_like",)
DELTA_RUN_IDS = ("A010_PAPER_1101_1101", "A011_PAPER_1101_1101", "A012_PAPER_1101_1101")
BUS400_DELTA_NAME = f"{SERIES.name}_delta_BVM4X4_BUS400_20261009.zip"
BUS400_DELTA_SHA256 = "2c7747d5fcff639985880af4c8c6cc4e9f54bd0ecfbac95daa4787dbc58e1bf1"
BUS400_DELTA_HEAD = "9e1070f85b3e7fcfdc1357f3e9e7bf64f834a29d"
A009_DELTA_NAME = f"{SERIES.name}_delta_A009_RESPONSIVE_20261009.zip"
A009_DELTA_SHA256 = "a852fa8453ca5d7315767958a96c35dce3465956e1b8a964035af4bc071a2a91"
A009_DELTA_HEAD = "617311779e996494194ef1aa9bb172295158ea81"
LEGACY_RUN_IDS = tuple(f"A{i:03d}_{case}" for i, case in enumerate(
    ("D3_N0", "D3_N1", "D3_N2", "D3_N3", "D3_N4", "PAPER_1101_1101"), start=1))
BASE_METADATA_NAME = f"{SERIES.name}_metadata_v2_BVM4X4_20261009.zip"
BASE_METADATA_QA = HANDOFF / f"{Path(BASE_METADATA_NAME).stem}_PACKAGE_QA.json"
BASE_METADATA_SHA256 = "19af77800333d2c596b25606c26ac84fbd0ae4101b5b14f83fefc121c5975be1"
BASE_METADATA_SOURCE_COMMIT = "364dd2b6dc0589f1ca1de614a16583a32331a51d"
BASE_RUN_PACKAGE_SHA256 = {
    "A001_D3_N0": "a720b89bfc318937c22e8c456cad80000b5aa47527d1470e4577b2413c851585",
    "A002_D3_N1": "8e3d18c8ca9d24c4c88a2cd7bb34826154a2556d8d4b034a81d3bdf78c7ee063",
    "A003_D3_N2": "a41e44a10b6021560a329047490b2b79b18a2f49d5d6bef145d81b46bba8a306",
    "A004_D3_N3": "b8af1acc2241e56c77374734336f49719f1e476717c5b1337592c1409bb874f9",
    "A005_D3_N4": "83e7d33b8ea44af3e80a7254596a93bf2b73ce51315add066a3f14a8dde1ec4d",
    "A006_PAPER_1101_1101": "c3cd4bd7477b3b5b43b78313a9392808d78da9949d3a8feb593ca72bfbf28c46",
}
BASE_RUN_RAW_SHA256 = {
    "A001_D3_N0": "af13bc5105c12919b7d93817d21ebd4a3f31123fb18f1e1d39b6a90958199c4d",
    "A002_D3_N1": "f977347a31d24a932262d2a87a145d344b96b56393bce99ebf592cf6dd7a2be2",
    "A003_D3_N2": "62301133c8faa92e078032270091920710ff361ba052450c4c006092308e9ec4",
    "A004_D3_N3": "79357f4a5401f11cae7fc5ec1ba496b81a30fec24c6d426982f42c6fcbb56908",
    "A005_D3_N4": "3b8cb325ed025ae83c3be83226284473357d5e7ec3a472dda6c75fcdd4050060",
    "A006_PAPER_1101_1101": "a318d8c09a958886ab1b3ec8ed636bf42c7b46b7fc9055353cff47ae0432b9cc",
}
DELTA_GLOBAL_PATHS = {
    "AGENTS.md", "CLAUDE.md", ".agents/skills/josim-experiment/SKILL.md",
    ".agents/skills/josim-experiment/agents/openai.yaml",
    "docs/EXPERIMENT_CONTRACT.md", "docs/research/EXPERIMENT_WORKFLOW_V1.md",
    "docs/research/COMPACT_WORKFLOW_V2.md", "memory/EXECUTOR_NOW.md",
    "memory/BVM_CURRENT_CONTEXT.md", "memory/LUNA_EXECUTOR_MEMORY.md",
    "memory/skill-usage.md", "scripts/README.md", "scripts/submit.py",
}


def load_root_submit() -> Any:
    spec = importlib.util.spec_from_file_location("josim_root_submit", ROOT_SUBMIT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load repository submit helper: {ROOT_SUBMIT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def git(*args: str, check: bool = True) -> str:
    return subprocess.run(["git", *args], cwd=REPO, text=True,
                          capture_output=True, check=check).stdout.strip()


def included_files(root: Path) -> list[Path]:
    files = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(SERIES)
        if (not path.is_file() or path.is_symlink() or "handoff" in relative.parts
                or "__pycache__" in relative.parts or path.suffix.lower() in {".html", ".pyc", ".tmp"}):
            continue
        files.append(path)
    return files


def base_records(root: Any) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Verify prior package identities from QA sidecars without reopening old raw or ZIP members."""
    metadata = json.loads(BASE_METADATA_QA.read_text(encoding="utf-8"))
    metadata_path = HANDOFF / BASE_METADATA_NAME
    if (metadata.get("status") != "PASS" or metadata.get("package_sha256") != BASE_METADATA_SHA256 or
            metadata.get("source_commit") != BASE_METADATA_SOURCE_COMMIT or
            not metadata_path.is_file() or root.sha256(metadata_path) != BASE_METADATA_SHA256 or
            metadata.get("package_bytes") != metadata_path.stat().st_size):
        raise RuntimeError("bound metadata-v2 base identity/QA does not match the registered checkpoint")
    manifest = json.loads((SERIES / "experiment_manifest.json").read_text(encoding="utf-8"))
    recorded_raw = {item.get("run_id"): item.get("raw_sha256") for item in manifest.get("runs", [])}
    records = []
    for run_id in LEGACY_RUN_IDS:
        package_name = f"{SERIES.name}_raw_handoff_{run_id}_BVM4X4_20261009.zip"
        package = HANDOFF / package_name
        qa_path = HANDOFF / f"{Path(package_name).stem}_PACKAGE_QA.json"
        qa = json.loads(qa_path.read_text(encoding="utf-8"))
        raw_sha = qa.get("raw_sha256_by_run", {}).get(run_id)
        expected_package_sha = BASE_RUN_PACKAGE_SHA256[run_id]
        expected_raw_sha = BASE_RUN_RAW_SHA256[run_id]
        if (qa.get("status") != "PASS" or qa.get("package_sha256") != expected_package_sha or
                qa.get("package_bytes") != package.stat().st_size or
                root.sha256(package) != expected_package_sha or raw_sha != expected_raw_sha or
                recorded_raw.get(run_id) != expected_raw_sha):
            raise RuntimeError(f"registered legacy package/raw identity mismatch: {run_id}")
        records.append({"run_id": run_id,
                        "raw_path": f"runs/{run_id}/raw.csv",
                        "raw_sha256": expected_raw_sha,
                        "source_package_name": package_name,
                        "source_package_sha256": expected_package_sha})
    return metadata, records


def _excluded_delta_path(path: Path) -> bool:
    parts = path.parts
    return ("handoff" in parts or "plots" in parts or "__pycache__" in parts or
            path.suffix.lower() in {".html", ".pyc", ".tmp"})


def is_allowed_delta_run_path(rel_path: str) -> bool:
    parts = Path(rel_path).parts
    if len(parts) < 6 or parts[:4] != ("test", "exploration", SERIES.name, "runs"):
        return False
    run_id = parts[4]
    if run_id in DELTA_RUN_IDS:
        return True
    return False


def verify_prior_bus400_delta(root: Any, legacy_refs: list[dict[str, Any]]) -> tuple[
        dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    package = HANDOFF / BUS400_DELTA_NAME
    qa_path = HANDOFF / f"{Path(BUS400_DELTA_NAME).stem}_PACKAGE_QA.json"
    qa = root.verify_existing_bundle(package, qa_path)
    if (qa.get("status") != "PASS" or qa.get("package_sha256") != BUS400_DELTA_SHA256 or
            qa.get("source_commit") != BUS400_DELTA_HEAD or
            qa.get("base_package_name") != BASE_METADATA_NAME or
            qa.get("base_package_sha256") != BASE_METADATA_SHA256):
        raise RuntimeError("registered A007/A008 delta package identity or QA mismatch")
    with zipfile.ZipFile(package, "r") as archive:
        prior_manifest = json.loads(archive.read("DELTA_MANIFEST.json"))
    if (prior_manifest.get("head_commit") != BUS400_DELTA_HEAD or
            prior_manifest.get("base_package_name") != BASE_METADATA_NAME or
            prior_manifest.get("base_package_sha256") != BASE_METADATA_SHA256):
        raise RuntimeError("registered A007/A008 delta manifest lineage mismatch")
    manifest_raw = prior_manifest.get("raw_sha256_by_run", {})
    if set(manifest_raw) != set(BUS400_RUN_IDS):
        raise RuntimeError("registered A007/A008 delta raw closure is incomplete")
    manifest_rows = {item.get("run_id"): item for item in
                     json.loads((SERIES / "experiment_manifest.json").read_text(encoding="utf-8")).get("runs", [])}
    added_refs = []
    for run_id in BUS400_RUN_IDS:
        result = json.loads((RUNS / run_id / "result.json").read_text(encoding="utf-8"))
        raw = RUNS / run_id / "raw.csv"
        if (manifest_raw.get(run_id) != result.get("raw_sha256") or
                not manifest_rows.get(run_id) or
                manifest_rows[run_id].get("raw_sha256") != result.get("raw_sha256") or
                root.sha256(raw) != result.get("raw_sha256")):
            raise RuntimeError(f"A007/A008 raw identity no longer matches its delta base: {run_id}")
        added_refs.append({"run_id": run_id, "raw_path": f"runs/{run_id}/raw.csv",
                           "raw_sha256": result["raw_sha256"],
                           "source_package_name": BUS400_DELTA_NAME,
                           "source_package_sha256": BUS400_DELTA_SHA256})
    return qa, prior_manifest, legacy_refs + added_refs


def verify_prior_a009_delta(root: Any, prior_refs: list[dict[str, Any]]) -> tuple[
        dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    expected_prior_refs = list(prior_refs)
    package = HANDOFF / A009_DELTA_NAME
    qa_path = HANDOFF / f"{Path(A009_DELTA_NAME).stem}_PACKAGE_QA.json"
    qa = root.verify_existing_bundle(package, qa_path)
    if (qa.get("status") != "PASS" or qa.get("package_sha256") != A009_DELTA_SHA256 or
            qa.get("source_commit") != A009_DELTA_HEAD or
            qa.get("base_package_name") != BUS400_DELTA_NAME or
            qa.get("base_package_sha256") != BUS400_DELTA_SHA256):
        raise RuntimeError("registered A009 delta package identity or QA mismatch")
    with zipfile.ZipFile(package, "r") as archive:
        prior_manifest = json.loads(archive.read("DELTA_MANIFEST.json"))
    if (prior_manifest.get("head_commit") != A009_DELTA_HEAD or
            prior_manifest.get("base_package_name") != BUS400_DELTA_NAME or
            prior_manifest.get("base_package_sha256") != BUS400_DELTA_SHA256):
        raise RuntimeError("registered A009 delta manifest lineage mismatch")
    recorded_prior_refs = prior_manifest.get("referenced_existing_raw_sha256", [])
    prior_identities = {(item.get("run_id"), item.get("raw_sha256"), item.get("source_package_name"),
                         item.get("source_package_sha256")) for item in recorded_prior_refs}
    expected_identities = {(item["run_id"], item["raw_sha256"], item["source_package_name"],
                            item["source_package_sha256"]) for item in expected_prior_refs}
    if len(prior_identities) != len(recorded_prior_refs) or prior_identities != expected_identities:
        raise RuntimeError("registered A009 delta existing-raw references are malformed")
    raw_map = prior_manifest.get("raw_sha256_by_run", {})
    if set(raw_map) != set(A009_RUN_IDS):
        raise RuntimeError("registered A009 delta raw closure is incomplete")
    manifest_rows = {item.get("run_id"): item for item in
                     json.loads((SERIES / "experiment_manifest.json").read_text(encoding="utf-8")).get("runs", [])}
    added_refs = []
    for run_id in A009_RUN_IDS:
        result = json.loads((RUNS / run_id / "result.json").read_text(encoding="utf-8"))
        raw = RUNS / run_id / "raw.csv"
        if (raw_map.get(run_id) != result.get("raw_sha256") or
                not manifest_rows.get(run_id) or
                manifest_rows[run_id].get("raw_sha256") != result.get("raw_sha256") or
                root.sha256(raw) != result.get("raw_sha256")):
            raise RuntimeError(f"A009 raw identity no longer matches its delta base: {run_id}")
        added_refs.append({"run_id": run_id, "raw_path": f"runs/{run_id}/raw.csv",
                           "raw_sha256": result["raw_sha256"],
                           "source_package_name": A009_DELTA_NAME,
                           "source_package_sha256": A009_DELTA_SHA256})
    return qa, prior_manifest, recorded_prior_refs + added_refs


def partition_delta_sources(sources: list[tuple[Path, str]]) -> tuple[
        dict[str, list[tuple[Path, str]]], list[tuple[Path, str]]]:
    by_run = {run_id: [] for run_id in DELTA_RUN_IDS}
    shared = []
    for item in sources:
        parts = Path(item[1]).parts
        if len(parts) >= 5 and parts[:4] == ("test", "exploration", SERIES.name, "runs") and parts[4] in by_run:
            by_run[parts[4]].append(item)
        else:
            shared.append(item)
    members = [member for _source, member in shared]
    members.extend(member for group in by_run.values() for _source, member in group)
    if len(members) != len(sources) or len(members) != len(set(members)):
        raise RuntimeError("delta source partition is incomplete or contains duplicate members")
    missing = [run_id for run_id, group in by_run.items()
               if not any(Path(member).name == "raw.csv" for _source, member in group)]
    if missing:
        raise RuntimeError(f"delta partition is missing run raw files: {missing}")
    if not shared:
        raise RuntimeError("delta has no shared source/config/manifest files")
    return by_run, shared


def _delta_sources(root: Any) -> tuple[list[tuple[Path, str]], list[str], list[str]]:
    changes = dict(root.committed_changes(A009_DELTA_HEAD, git("rev-parse", "HEAD")))
    changes.update(root.working_changes())
    for path in root.untracked_files():
        changes.setdefault(path, "??")
    sources: dict[str, Path] = {}
    excluded_html: set[str] = set()
    changed_paths: set[str] = set()
    for rel_path, status in changes.items():
        path = Path(rel_path)
        if not (root.in_scope(rel_path, [SERIES]) or rel_path in DELTA_GLOBAL_PATHS):
            continue
        if status == "D":
            raise RuntimeError(f"delta submission refuses file deletion: {rel_path}")
        if path.parts[:2] == ("test", "exploration") and path.parts[2:3] == (SERIES.name,):
            if len(path.parts) >= 4 and path.parts[3] == "runs":
                if not is_allowed_delta_run_path(rel_path):
                    raise RuntimeError(f"delta submission detected a historical run edit: {rel_path}")
        if _excluded_delta_path(path):
            if path.suffix.lower() == ".html":
                excluded_html.add(rel_path)
            continue
        source = REPO / path
        if source.is_file() and not source.is_symlink():
            sources[rel_path] = source
            changed_paths.add(rel_path)

    # Run evidence may be ignored by Git until the submission explicitly stages it.
    for run_id in DELTA_RUN_IDS:
        run_dir = RUNS / run_id
        if not run_dir.is_dir():
            raise RuntimeError(f"new authorized run directory is missing: {run_id}")
        for path in included_files(run_dir):
            rel_path = path.relative_to(REPO).as_posix()
            sources[rel_path] = path
            changed_paths.add(rel_path)

    for path in SERIES.rglob("*.html"):
        if path.is_file():
            excluded_html.add(path.relative_to(REPO).as_posix())

    required_run_files = {"deck.cir", "raw.csv", "run.log", "stdout.txt", "stderr.txt",
                          "USER_CASE.snapshot.env", "STIMULUS.snapshot.env", "T1_PARAMS.snapshot.env",
                          "stimulus.inc", "case_manifest.json", "metadata.json", "provenance.json",
                          "source_manifest.json", "topology_manifest.json", "probe_manifest.json",
                          "static_qa.json", "stimulus_manifest.json", "metrics.json", "raw_qa.json",
                          "qa.json", "plot_manifest.json", "plot_qa.json", "result.json",
                          "RESULT_BRIEF.md"}
    for run_id in DELTA_RUN_IDS:
        have = {Path(item).name for item in sources if Path(item).parts[-2:-1] == (run_id,)}
        missing = required_run_files - have
        if missing:
            raise RuntimeError(f"{run_id} delta evidence is incomplete: {sorted(missing)}")

    # Every existing, non-HTML change from the registered Git base must appear.
    for rel_path, status in changes.items():
        path = Path(rel_path)
        if status == "D" or _excluded_delta_path(path):
            continue
        if root.in_scope(rel_path, [SERIES]) or rel_path in DELTA_GLOBAL_PATHS:
            if path.parts[:2] == ("test", "exploration") and path.parts[2:3] == (SERIES.name,):
                if len(path.parts) >= 4 and path.parts[3] == "runs":
                    continue
            if (REPO / path).is_file() and rel_path not in sources:
                raise RuntimeError(f"changed evidence/source omitted from delta inventory: {rel_path}")
    ordered = [(sources[key], key) for key in sorted(sources)]
    return ordered, sorted(changed_paths), sorted(excluded_html)


def delta_specs(tag: str, root: Any) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if not root.TAG_RE.fullmatch(tag):
        raise RuntimeError(f"invalid delta tag: {tag!r}")
    metadata, legacy_raw_refs = base_records(root)
    bus400_qa, _bus400_manifest, bus400_refs = verify_prior_bus400_delta(root, legacy_raw_refs)
    prior_delta_qa, prior_delta_manifest, existing_raw_refs = verify_prior_a009_delta(root, bus400_refs)
    sources, changed_paths, excluded_html = _delta_sources(root)
    prior_hashes = prior_delta_manifest.get("included_file_sha256", {})
    current_sources = []
    for source, member in sources:
        digest = root.sha256(source)
        if prior_hashes.get(member) != digest:
            current_sources.append((source, member))
    if not current_sources:
        raise RuntimeError("delta has no source or evidence changes since the A009 checkpoint")
    per_run_sources, shared_sources = partition_delta_sources(current_sources)
    current_head = git("rev-parse", "HEAD")
    run_raw_sha = {}
    for run_id in DELTA_RUN_IDS:
        result = json.loads((RUNS / run_id / "result.json").read_text(encoding="utf-8"))
        run_raw_sha[run_id] = result["raw_sha256"]
    experiment_manifest = json.loads((SERIES / "experiment_manifest.json").read_text(encoding="utf-8"))
    manifest_limit_audit = {
        "recorded_physical_solve_count": experiment_manifest.get("physical_solve_count"),
        "declared_maximum_physical_solve_count": experiment_manifest.get("maximum_physical_solve_count"),
        "status": ("EXCEEDED_PRESERVED" if
                   int(experiment_manifest.get("physical_solve_count", 0)) >
                   int(experiment_manifest.get("maximum_physical_solve_count", 0)) else "WITHIN_DECLARED_MAXIMUM"),
        "manifest_modified_by_packaging": False,
    }
    groups = [("source", shared_sources, None)] + [
        (run_id, per_run_sources[run_id], run_id) for run_id in DELTA_RUN_IDS]
    specs, plans = [], []
    for label, group_sources, run_id in groups:
        if not group_sources:
            raise RuntimeError(f"delta package group is empty: {label}")
        source_records = root.file_records(group_sources)
        source_bytes = sum(record["bytes"] for record in source_records)
        included_hashes = {record["archive_path"]: record["sha256"] for record in source_records}
        new_files, modified_files = [], []
        for record in source_records:
            member, digest = record["archive_path"], record["sha256"]
            if member not in prior_hashes:
                new_files.append(member)
            elif prior_hashes[member] != digest:
                modified_files.append(member)
        package_name = f"{SERIES.name}_delta_{tag}_{label}.zip"
        target = HANDOFF / package_name
        qa_target = HANDOFF / f"{Path(package_name).stem}_PACKAGE_QA.json"
        if target.exists() or qa_target.exists():
            raise FileExistsError(f"refusing to overwrite immutable delta package: {package_name}")
        package_raw_sha = {run_id: run_raw_sha[run_id]} if run_id else {}
        solve_count = 1 if run_id else 0
        manifest = {
            "schema": "bvm-4x4-incremental-evidence-delta-v3",
            "package_type": "directory_snapshot_delta",
            "package_group": label,
            "base_commit": A009_DELTA_HEAD,
            "head_commit": "PENDING_EVIDENCE_COMMIT",
            "base_package_name": A009_DELTA_NAME,
            "base_package_sha256": A009_DELTA_SHA256,
            "base_package_source_commit": prior_delta_qa["source_commit"],
            "base_metadata_package_name": BASE_METADATA_NAME,
            "base_metadata_package_sha256": metadata["package_sha256"],
            "base_metadata_source_commit": metadata["source_commit"],
            "base_run_packages": existing_raw_refs,
            "included_files": source_records,
            "included_file_sha256": included_hashes,
            "new_files": new_files,
            "modified_files": modified_files,
            "deleted_files": [],
            "referenced_existing_cases": existing_raw_refs,
            "referenced_existing_raw_sha256": existing_raw_refs,
            "new_physical_solve_count": solve_count,
            "reused_point_count": 0,
            "raw_sha256_by_run": package_raw_sha,
            "preexisting_experiment_manifest_limit_audit": manifest_limit_audit,
            "excluded_html": excluded_html,
            "generated_from_head": current_head,
        }
        extra = {"DELTA_MANIFEST.json": (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")}
        if source_bytes + sum(len(value) for value in extra.values()) >= root.MAX_GIT_FILE_BYTES:
            raise RuntimeError(f"{label} delta exceeds the 100MB uncompressed archive guard: {source_bytes}")
        spec = {"name": package_name, "kind": "bvm_4x4_evidence_delta_v1", "scope": SERIES,
                "target": target, "qa_path": qa_target, "sources": group_sources,
                "extra_members": extra, "delta_manifest": manifest,
                "readme": (f"Incremental evidence delta for {SERIES.name}; tag={tag}; group={label}.\n"
                           f"Base delta: {A009_DELTA_NAME} ({A009_DELTA_SHA256})\n"
                           f"Base source HEAD: {A009_DELTA_HEAD}\n"
                           f"Batch additions: {', '.join(DELTA_RUN_IDS)}.\n"
                           "A001-A009 raw is referenced by exact package/raw SHA; no previous raw is copied again.\n"
                           "Generated HTML is excluded. No scientific interpretation.\n").encode(),
                "excluded_files": excluded_html, "base_name": A009_DELTA_NAME,
                "base_sha": A009_DELTA_SHA256, "raw_by_run": package_raw_sha}
        specs.append(spec)
        plans.append({"package": package_name, "group": label,
                      "new_raw_files": [f"runs/{run_id}/raw.csv"] if run_id else [],
                      "raw_sha256_by_run": package_raw_sha,
                      "raw_bytes_by_run": {run_id: (RUNS / run_id / "raw.csv").stat().st_size} if run_id else {},
                      "new_physical_solve_count": solve_count,
                      "source_file_count": len(group_sources),
                      "uncompressed_source_bytes": source_bytes,
                      "new_files": new_files, "modified_files": modified_files,
                      "qa": qa_target.relative_to(REPO).as_posix()})
    plan = {"base_commit": A009_DELTA_HEAD,
            "generated_from_head": current_head,
            "base_package_name": A009_DELTA_NAME,
            "base_package_sha256": A009_DELTA_SHA256,
            "base_metadata_package": BASE_METADATA_NAME,
            "base_metadata_sha256": metadata["package_sha256"],
            "packages": plans,
            "referenced_existing_cases": existing_raw_refs,
            "new_physical_solve_count": len(DELTA_RUN_IDS),
            "reused_point_count": 0,
            "experiment_manifest_limit_audit": manifest_limit_audit,
            "excluded_html_count": len(excluded_html), "html_included": False,
            "total_uncompressed_source_bytes": sum(item["uncompressed_source_bytes"] for item in plans),
            "package_count": len(specs)}
    return specs, {"plan": plan, "source_paths": [rel for _, rel in sources],
                   "total_new_physical_solve_count": len(DELTA_RUN_IDS),
                   "referenced_existing_cases": existing_raw_refs}


def validate_scope(*, delta: bool = False) -> None:
    root = load_root_submit()
    changes = dict(root.committed_changes(A009_DELTA_HEAD, git("rev-parse", "HEAD"))) if delta else {}
    changes.update(root.working_changes())
    for path in root.untracked_files():
        changes.setdefault(path, "??")
    allowed = lambda path: root.in_scope(path, [SERIES]) or path in DELTA_GLOBAL_PATHS
    outside = sorted(path for path in changes if not allowed(path))
    if outside:
        raise RuntimeError("unrelated worktree changes outside this experiment: " + ", ".join(outside))
    if not RUNS.is_dir():
        raise RuntimeError("runs/ is missing; no completed physical batch found")
    run_dirs = sorted(path for path in RUNS.iterdir() if path.is_dir() and path.name.startswith("A"))
    expected = list(LEGACY_RUN_IDS + BUS400_RUN_IDS + A009_RUN_IDS + DELTA_RUN_IDS) if delta else list(LEGACY_RUN_IDS)
    if [path.name for path in run_dirs] != expected:
        raise RuntimeError(f"run closure mismatch; expected {expected}, found {[p.name for p in run_dirs]}")
    check_dirs = [RUNS / run_id for run_id in DELTA_RUN_IDS] if delta else run_dirs
    for path in check_dirs:
        result = json.loads((path / "result.json").read_text(encoding="utf-8"))
        qa = json.loads((path / "qa.json").read_text(encoding="utf-8"))
        if result.get("run_id") != path.name or qa.get("raw_sha256_before_analysis") != result.get("raw_sha256"):
            raise RuntimeError(f"run/result/QA identity mismatch: {path.name}")
        if result.get("artifact_status") != "VALID" or qa.get("status") != "PASS":
            raise RuntimeError(f"run is not mechanically valid: {path.name}")
        if int(result.get("physical_solve_count", 0)) != 1:
            raise RuntimeError(f"run physical_solve_count is not one: {path.name}")
        raw = path / "raw.csv"
        if (not raw.is_file() or raw.stat().st_size != result.get("raw_bytes") or
                root.sha256(raw) != result.get("raw_sha256")):
            raise RuntimeError(f"new raw does not match its result identity: {path.name}")
    manifest = json.loads((SERIES / "experiment_manifest.json").read_text(encoding="utf-8"))
    recorded = {item.get("run_id"): item for item in manifest.get("runs", [])}
    for path in check_dirs:
        result = json.loads((path / "result.json").read_text(encoding="utf-8"))
        row = recorded.get(path.name)
        if not row or row.get("raw_sha256") != result.get("raw_sha256"):
            raise RuntimeError(f"experiment_manifest raw identity missing/mismatched: {path.name}")


def package_specs(tag: str, root: Any, *, dry_run: bool) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    run_dirs = sorted(path for path in RUNS.iterdir() if path.is_dir() and path.name.startswith("A"))
    meta_paths = [path for path in included_files(SERIES)
                  if path.relative_to(SERIES).parts[0] not in {"runs", "plots"}]
    specs = []
    plan = []
    all_raw: dict[str, str] = {}
    for run_dir in run_dirs:
        result = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
        raw = run_dir / "raw.csv"
        raw_hash = result.get("raw_sha256")
        if not isinstance(raw_hash, str) or len(raw_hash) != 64 or raw.stat().st_size == 0:
            raise RuntimeError(f"run result/raw identity is incomplete: {run_dir.name}")
        if result.get("raw_bytes") != raw.stat().st_size:
            raise RuntimeError(f"raw byte count disagrees with result manifest: {run_dir.name}")
        all_raw[run_dir.name] = raw_hash
        paths = included_files(run_dir)
        sources = [(path, path.relative_to(SERIES).as_posix()) for path in paths]
        uncompressed = sum(path.stat().st_size for path in paths)
        if uncompressed >= root.MAX_GIT_FILE_BYTES:
            raise RuntimeError(f"single run bundle exceeds 100MB guard: {run_dir.name} ({uncompressed} bytes)")
        name = f"{SERIES.name}_raw_handoff_{run_dir.name}_{tag}.zip"
        target = HANDOFF / name
        qa_target = HANDOFF / f"{Path(name).stem}_PACKAGE_QA.json"
        if target.exists() or qa_target.exists():
            raise FileExistsError(f"refusing to overwrite immutable package {name}")
        raw_map = {run_dir.name: raw_hash}
        spec = {"name": name, "kind": "directory_snapshot", "scope": SERIES,
                "target": target, "qa_path": qa_target, "sources": sources,
                "extra_members": {}, "excluded_files": [],
                "readme": (f"One-run evidence snapshot for {run_dir.name}.\n"
                           f"Raw SHA-256: {raw_hash}\n"
                           "Generated HTML is intentionally excluded and remains local.\n"
                           "Mechanical artifact QA only; no scientific interpretation.\n").encode(),
                "base_name": None, "base_sha": None, "raw_by_run": raw_map}
        specs.append(spec)
        plan.append({"name": name, "file_count": len(paths), "uncompressed_bytes": uncompressed,
                     "raw_bytes": raw.stat().st_size, "new_physical_solve_count": result["physical_solve_count"]})

    metadata_sources = [(path, path.relative_to(SERIES).as_posix()) for path in meta_paths]
    metadata_bytes = sum(path.stat().st_size for path in meta_paths)
    if metadata_bytes >= root.MAX_GIT_FILE_BYTES:
        raise RuntimeError(f"shared metadata bundle exceeds 100MB guard: {metadata_bytes} bytes")
    metadata_name = f"{SERIES.name}_metadata_{tag}.zip"
    metadata_target = HANDOFF / metadata_name
    metadata_qa = HANDOFF / f"{Path(metadata_name).stem}_PACKAGE_QA.json"
    if metadata_target.exists() or metadata_qa.exists():
        raise FileExistsError(f"refusing to overwrite immutable package {metadata_name}")
    metadata_spec = {"name": metadata_name, "kind": "directory_snapshot", "scope": SERIES,
                     "target": metadata_target, "qa_path": metadata_qa,
                     "sources": metadata_sources, "extra_members": {}, "excluded_files": [],
                     "readme": (f"Shared metadata snapshot for {SERIES.name}.\n"
                                f"Authorized runs: {', '.join(all_raw)}\n"
                                "Per-run raw files are stored only in their own handoff archives.\n"
                                "Generated HTML/Plotly JS and historical artifacts are excluded.\n"
                                "No new physical solve or scientific interpretation by packaging.\n").encode(),
                     "base_name": None, "base_sha": None, "raw_by_run": all_raw}
    specs.append(metadata_spec)
    plan.append({"name": metadata_name, "file_count": len(meta_paths),
                 "uncompressed_bytes": metadata_bytes, "raw_bytes": 0,
                 "new_physical_solve_count": 0})
    excluded_html = [p.relative_to(SERIES).as_posix() for p in SERIES.rglob("*.html") if p.is_file()]
    if dry_run:
        print(json.dumps({"status": "DRY_RUN_PASS", "scope": SERIES.relative_to(REPO).as_posix(),
                          "head": git("rev-parse", "HEAD"),
                          "package_count": len(specs), "raw_references_not_copied": [],
                          "excluded_html_count": len(excluded_html),
                          "html_included": False, "new_physical_solve_count_in_package": 6,
                          "packages": plan,
                          "notes": ["New experiment has no previous archive base; run archives are standalone snapshots.",
                                    "Shared metadata archive contains no raw.csv; each raw is included once in its run archive."]},
                         ensure_ascii=False, indent=2))
    return specs, {"plan": plan, "excluded_html": excluded_html, "raw_sha256_by_run": all_raw}


def update_summary_with_packages(results: list[dict[str, Any]], package_table_marker: str = "<!-- PACKAGE_TABLE -->") -> None:
    summary = SERIES / "BATCH_SUMMARY.md"
    text = summary.read_text(encoding="utf-8")
    rows = ["| Archive | Bytes | SHA-256 |", "|---|---:|---|"]
    for item in results:
        name = Path(item["path"]).name
        rows.append(f"| `{name}` | {item['bytes']} | `{item['sha256']}` |")
    total = sum(int(item["bytes"]) for item in results)
    replacement = (f"{package_table_marker}\n" + "\n".join(rows) +
                   f"\n\nSix per-run ZIP total: **{total:,} bytes**.\n"
                   "<!-- METADATA_PACKAGE -->\n"
                   "The metadata ZIP carries this run-package table; its own identity is appended below after creation.\n"
                   "Each ZIP's detached PACKAGE_QA.json is the member/CRC/SHA authority.\n")
    if package_table_marker not in text:
        raise RuntimeError("BATCH_SUMMARY package table marker is missing")
    summary.write_text(text.replace(package_table_marker, replacement), encoding="utf-8")


def submit_metadata_v2(args: argparse.Namespace, root: Any) -> int:
    summary = SERIES / "BATCH_SUMMARY.md"
    package_name = f"{SERIES.name}_metadata_v2_{args.tag}.zip"
    target = HANDOFF / package_name
    qa_target = HANDOFF / f"{Path(package_name).stem}_PACKAGE_QA.json"
    if target.exists() or qa_target.exists():
        raise FileExistsError(f"refusing to overwrite immutable metadata-v2 package {package_name}")
    metadata_paths = [path for path in included_files(SERIES)
                      if path.relative_to(SERIES).parts[0] not in {"runs", "plots"}]
    source_bytes = sum(path.stat().st_size for path in metadata_paths)
    if source_bytes >= root.MAX_GIT_FILE_BYTES:
        raise RuntimeError(f"metadata-v2 input exceeds 100MB guard: {source_bytes}")
    rel_paths = [path.relative_to(REPO).as_posix() for path in metadata_paths]
    if rel_paths:
        subprocess.run(["git", "add", "-A", "-f", "--", *rel_paths], cwd=REPO, check=True)
    staged_empty = subprocess.run(["git", "diff", "--cached", "--quiet"],
                                   cwd=REPO, check=False).returncode == 0
    if not staged_empty:
        subprocess.run(["git", "commit", "-m", "docs: supersede unbound 4x4 metadata archive"],
                       cwd=REPO, check=True)
    source_commit = git("rev-parse", "HEAD")
    raw_by_run = {d.name: json.loads((d / "result.json").read_text(encoding="utf-8"))["raw_sha256"]
                  for d in sorted(RUNS.iterdir()) if d.is_dir() and d.name.startswith("A")}
    sources = [(path, path.relative_to(SERIES).as_posix()) for path in metadata_paths]
    spec = {"name": package_name, "kind": "directory_snapshot", "scope": SERIES,
            "target": target, "qa_path": qa_target, "sources": sources,
            "extra_members": {}, "excluded_files": [],
            "readme": (f"Bound shared metadata v2 for {SERIES.name}.\n"
                       f"Source commit: {source_commit}\n"
                       "Supersedes only the unbound first metadata snapshot; all six raw-run ZIPs are unchanged.\n"
                       "No new physical solve or scientific interpretation.\n").encode(),
            "base_name": None, "base_sha": None, "raw_by_run": raw_by_run}
    result = root.archive_bundle(spec, source_commit)
    subprocess.run(["git", "add", "-f", "--", result["path"], result["qa_path"]], cwd=REPO, check=True)
    subprocess.run(["git", "commit", "-m", "package: add bound 4x4 metadata v2"], cwd=REPO, check=True)
    if not args.no_push:
        subprocess.run(["git", "push"], cwd=REPO, check=True)
    mirror = root.copy_mirror([target], Path(args.mirror_dir).expanduser().resolve())
    print(json.dumps({"status": "METADATA_V2_COMPLETE", "source_commit": source_commit,
                      "final_commit": git("rev-parse", "HEAD"), "push": "SKIPPED" if args.no_push else "PASS",
                      "supersedes": "metadata_BVM4X4_20261009.zip",
                      "package": result, "mirror": mirror}, ensure_ascii=False, indent=2))
    return 0


def submit_delta(args: argparse.Namespace, root: Any) -> int:
    validate_scope(delta=True)
    specs, context = delta_specs(args.tag, root)
    mirror_dir = Path(args.mirror_dir).expanduser().resolve()
    if not mirror_dir.is_dir():
        raise RuntimeError(f"mirror directory is not accessible: {mirror_dir}")
    collisions = [str(mirror_dir / spec["name"]) for spec in specs
                  if (mirror_dir / spec["name"]).exists()]
    if collisions:
        raise FileExistsError("same-name mirror target already exists: " + ", ".join(collisions))
    if args.dry_run:
        print(json.dumps({"status": "DRY_RUN_PASS", "scope": SERIES.relative_to(REPO).as_posix(),
                          "package_mode": "DELTA",
                          **context["plan"],
                          "push": "SKIPPED" if args.no_push else "bvm/master",
                          "mirror_dir": str(mirror_dir), "no_files_modified": True},
                         ensure_ascii=False, indent=2))
        return 0

    stage_paths = context["source_paths"]
    if stage_paths:
        subprocess.run(["git", "add", "-A", "-f", "--", *stage_paths], cwd=REPO, check=True)
    if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=REPO, check=False).returncode != 0:
        subprocess.run(["git", "commit", "-m", args.message or "experiment: record BVM4x4 BUS400 diagnostic batch"],
                       cwd=REPO, check=True)
    source_commit = git("rev-parse", "HEAD")

    # Bind the precomputed, hash-listed source set to the evidence commit.
    manifest = spec["delta_manifest"]
    manifest["head_commit"] = source_commit
    manifest["generated_from_head"] = source_commit
    spec["extra_members"]["DELTA_MANIFEST.json"] = (
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    package_results = []
    for spec in specs:
        manifest = spec["delta_manifest"]
        manifest["head_commit"] = source_commit
        manifest["generated_from_head"] = source_commit
        spec["extra_members"]["DELTA_MANIFEST.json"] = (
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        package_result = root.archive_bundle(spec, source_commit)
        qa_path = REPO / package_result["qa_path"]
        qa = json.loads(qa_path.read_text(encoding="utf-8"))
        qa.update({"package_mode": "DELTA_SPLIT_BY_RUN", "base_commit": manifest["base_commit"],
                   "head_commit": source_commit, "base_package_name": manifest["base_package_name"],
                   "base_package_sha256": manifest["base_package_sha256"],
                   "base_package_source_commit": manifest["base_package_source_commit"],
                   "delta_included_files": manifest["included_files"],
                   "delta_included_file_sha256": manifest["included_file_sha256"],
                   "new_files": manifest["new_files"], "modified_files": manifest["modified_files"],
                   "referenced_existing_cases": manifest["referenced_existing_cases"],
                   "referenced_existing_raw_sha256": manifest["referenced_existing_raw_sha256"],
                   "new_physical_solve_count": manifest["new_physical_solve_count"],
                   "reused_point_count": manifest["reused_point_count"],
                   "html_included": False,
                   "package_group": manifest["package_group"],
                   "preexisting_experiment_manifest_limit_audit": manifest["preexisting_experiment_manifest_limit_audit"],
                   "raw_sha256_by_run": manifest["raw_sha256_by_run"]})
        if (qa.get("status") != "PASS" or qa.get("package_sha256") != root.sha256(spec["target"]) or
                qa.get("package_bytes") != spec["target"].stat().st_size):
            raise RuntimeError(f"delta PACKAGE_QA identity failed: {spec['name']}")
        qa_path.write_text(json.dumps(qa, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        package_results.append(package_result)

    package_paths = [path for result in package_results for path in (result["path"], result["qa_path"])]
    subprocess.run(["git", "add", "-f", "--", *package_paths], cwd=REPO, check=True)
    subprocess.run(["git", "commit", "-m", f"package: archive BVM4x4 A010-A012 delta {args.tag}"],
                   cwd=REPO, check=True)
    push_status = "SKIPPED"
    if not args.no_push:
        subprocess.run(["git", "push"], cwd=REPO, check=True)
        push_status = "PASS"
    mirror = root.copy_mirror([spec["target"] for spec in specs], mirror_dir)
    print(json.dumps({"status": "DELTA_SUBMIT_COMPLETE", "source_commit": source_commit,
                      "final_commit": git("rev-parse", "HEAD"), "push": push_status,
                      "packages": package_results,
                      "base_commit": specs[0]["delta_manifest"]["base_commit"],
                      "base_package": specs[0]["delta_manifest"]["base_package_name"],
                      "referenced_existing_raw_count": len(context["referenced_existing_cases"]),
                      "new_physical_solve_count": context["total_new_physical_solve_count"],
                      "mirror": mirror},
                     ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Submit/package only this 4x4 experiment scope")
    parser.add_argument("tag")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-push", action="store_true")
    parser.add_argument("--delta", action="store_true",
                        help="append A010-A012 to the verified A009 delta, split per run")
    parser.add_argument("--metadata-v2", action="store_true",
                        help="create a corrected metadata-only v2; never runs JoSIM")
    parser.add_argument("--message")
    parser.add_argument("--mirror-dir", default=str(MIRROR_DEFAULT))
    args = parser.parse_args()
    try:
        root = load_root_submit()
        if args.delta:
            if args.metadata_v2:
                raise RuntimeError("--delta and --metadata-v2 are mutually exclusive")
            return submit_delta(args, root)
        validate_scope()
        if args.metadata_v2:
            return submit_metadata_v2(args, root)
        specs, _plan = package_specs(args.tag, root, dry_run=args.dry_run)
        mirror_dir = Path(args.mirror_dir).expanduser().resolve()
        if not mirror_dir.is_dir():
            raise RuntimeError(f"mirror directory is not accessible: {mirror_dir}")
        mirror_collisions = [spec["name"] for spec in specs if (mirror_dir / spec["name"]).exists()]
        if mirror_collisions:
            raise FileExistsError("same-name mirror target already exists: " + ", ".join(mirror_collisions))
        if args.dry_run:
            return 0
        source_paths = included_files(SERIES)
        relative_paths = [path.relative_to(REPO).as_posix() for path in source_paths]
        if relative_paths:
            subprocess.run(["git", "add", "-A", "-f", "--", *relative_paths], cwd=REPO, check=True)
        staged_empty = subprocess.run(["git", "diff", "--cached", "--quiet"],
                                       cwd=REPO, check=False).returncode == 0
        if staged_empty:
            raise RuntimeError("no scoped experiment/source changes to commit")
        subprocess.run(["git", "commit", "-m", args.message or "experiment: add BVM 4x4 diagonal batch"],
                       cwd=REPO, check=True)
        source_commit = git("rev-parse", "HEAD")
        package_results = []
        for spec in specs[:-1]:
            package_results.append(root.archive_bundle(spec, source_commit))
        update_summary_with_packages(package_results)
        subprocess.run(["git", "add", "--", (SERIES / "BATCH_SUMMARY.md").relative_to(REPO).as_posix()],
                       cwd=REPO, check=True)
        if subprocess.run(["git", "diff", "--cached", "--quiet"],
                          cwd=REPO, check=False).returncode != 0:
            subprocess.run(["git", "commit", "-m", "docs: record 4x4 run package hashes"], cwd=REPO, check=True)
        summary_commit = git("rev-parse", "HEAD")
        package_results.append(root.archive_bundle(specs[-1], summary_commit))
        package_paths = []
        for result in package_results:
            package_paths.extend((REPO / result["path"], REPO / result["qa_path"]))
        subprocess.run(["git", "add", "--", (SERIES / "BATCH_SUMMARY.md").relative_to(REPO).as_posix()],
                       cwd=REPO, check=True)
        subprocess.run(["git", "add", "-f", "--", *[p.relative_to(REPO).as_posix() for p in package_paths]],
                       cwd=REPO, check=True)
        subprocess.run(["git", "commit", "-m", f"package: archive 4x4 diagonal batch {args.tag}"],
                       cwd=REPO, check=True)
        push_status = "SKIPPED"
        if not args.no_push:
            subprocess.run(["git", "push"], cwd=REPO, check=True)
            push_status = "PASS"
        mirror_results = root.copy_mirror([REPO / x["path"] for x in package_results], mirror_dir)
        print(json.dumps({"status": "SUBMIT_COMPLETE", "source_commit": source_commit,
                          "summary_commit": summary_commit, "final_commit": git("rev-parse", "HEAD"),
                          "push": push_status, "packages": package_results,
                          "mirror": mirror_results}, ensure_ascii=False, indent=2))
        return 0
    except (OSError, RuntimeError, ValueError, KeyError, json.JSONDecodeError, subprocess.CalledProcessError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
