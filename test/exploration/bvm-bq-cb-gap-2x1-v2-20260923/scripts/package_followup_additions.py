#!/usr/bin/env python3
"""Package all 2026-09-24 additions without rewriting the canonical raw handoff."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path
from typing import Any

from common import ROOT, current_head, read_json, sha256, write_json

REPO = next(path for path in (ROOT, *ROOT.parents) if (path / ".git").exists())
BASE_ZIP = ROOT / "handoff" / "bvm-bq-cb-gap-2x1-v2-20260923_raw_handoff.zip"
BASE_QA = ROOT / "handoff" / "PACKAGE_QA.json"
PLOT_MANIFEST = ROOT / "analysis" / "component_plot_manifest_v1.json"
PLOT_QA = ROOT / "qa" / "component_plot_qa_v1.json"
PACKAGER = ROOT / "scripts" / "package_followup_additions.py"

SOURCE_BUNDLES = [
    ("2x1-bvm-qb-c-sim1", REPO / "test/exploration/2x1-bvm-qb-c-sim1"),
    ("2x1-bvm-qb-c-sim1-v2", REPO / "test/exploration/2x1-bvm-qb-c-sim1-v2"),
    ("2x1-bvm-qb-c-sim1-v3", REPO / "test/exploration/2x1-bvm-qb-c-sim1-v3"),
]
SNAPSHOT_ADDITIONS = [
    REPO / "test/exploration/bvm-bq-cb-gap-2x1-v2-20260923/runs/N1_10/snapshot.zip",
    REPO / "test/exploration/bvm-bq-cb-gap-2x1-v2-20260923/runs/N1_10/snapshot (2).zip",
]


def records_for(paths: list[tuple[Path, str]]) -> list[dict[str, Any]]:
    records = []
    seen = set()
    for source, member in paths:
        if member in seen:
            raise ValueError(f"duplicate archive member: {member}")
        seen.add(member)
        if not source.is_file() or source.is_symlink():
            raise FileNotFoundError(f"missing/non-regular input: {source}")
        records.append({"source_repo_path": source.relative_to(REPO).as_posix(),
                        "archive_path": member, "sha256": sha256(source),
                        "bytes": source.stat().st_size})
    return records


def directory_sources(name: str, directory: Path) -> list[tuple[Path, str]]:
    paths = []
    for source in sorted(directory.rglob("*")):
        if not source.is_file() or source.is_symlink():
            continue
        relative = source.relative_to(directory)
        if any(part in {".git", "__pycache__", "handoff"} for part in relative.parts):
            continue
        if source.suffix == ".pyc":
            continue
        paths.append((source, f"{name}/{relative.as_posix()}"))
    expected = {
        "111.html", "actual_deck.cir", "data_tran.csv", "deck.cir", "josim-plot-v2.py",
        "run.sh", "stimulus.inc", "snapshot/sources/BQ_0923.cir",
        "snapshot/sources/CB_0923.cir", "snapshot/sources/bvm_cell_0923.cir",
        "snapshot/sources/sJTL_0923.cir",
    }
    actual = {source.relative_to(directory).as_posix() for source, _ in paths}
    if actual != expected:
        raise RuntimeError(f"unexpected source snapshot membership for {name}: missing={sorted(expected-actual)}, extra={sorted(actual-expected)}")
    return paths


def base_identity() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    base_qa = read_json(BASE_QA)
    plot_manifest = read_json(PLOT_MANIFEST)
    plot_qa = read_json(PLOT_QA)
    if base_qa.get("status") != "PASS" or sha256(BASE_ZIP) != base_qa.get("package_sha256"):
        raise RuntimeError("canonical raw handoff failed its detached PACKAGE_QA identity")
    if plot_qa.get("status") != "PASS" or plot_manifest.get("parent_package_sha256") != base_qa.get("package_sha256"):
        raise RuntimeError("component views are not QA-bound to the canonical raw handoff")
    included = base_qa.get("included_file_sha256", {})
    raw_by_run = {}
    for item in plot_manifest.get("entries", []):
        run_id, raw_path, raw_hash = item["run_id"], item["raw_path"], item["raw_sha256"]
        if sha256(ROOT / raw_path) != raw_hash:
            raise RuntimeError(f"raw hash changed since component visualization: {run_id}")
        if included.get(f"runs/{run_id}/raw.csv") != raw_hash:
            raise RuntimeError(f"raw hash does not match base package manifest: {run_id}")
        if run_id in raw_by_run and raw_by_run[run_id] != raw_hash:
            raise RuntimeError(f"run raw hash inconsistent across plot entries: {run_id}")
        raw_by_run[run_id] = raw_hash
    if set(raw_by_run) != {"N0_00", "N1_01", "N1_10", "N2_11"} or len(plot_manifest.get("entries", [])) != 20:
        raise RuntimeError("component plot manifest does not cover the four registered runs")
    return base_qa, plot_manifest, {"raw_by_run": raw_by_run, "plot_qa": plot_qa}


def component_sources(plot_manifest: dict[str, Any]) -> list[tuple[Path, str]]:
    paths = [
        (PLOT_MANIFEST, "analysis/component_plot_manifest_v1.json"),
        (PLOT_QA, "qa/component_plot_qa_v1.json"),
        (ROOT / "plots/component_views/index.html", "plots/component_views/index.html"),
        (ROOT / "plots/assets/plotly.min.js", "plots/assets/plotly.min.js"),
        (PACKAGER, "scripts/package_followup_additions.py"),
    ]
    for entry in plot_manifest["entries"]:
        source = ROOT / entry["path"]
        if sha256(source) != entry["sha256"]:
            raise RuntimeError(f"component plot hash mismatch: {entry['path']}")
        paths.append((source, entry["path"]))
    for source in SNAPSHOT_ADDITIONS:
        paths.append((source, source.relative_to(REPO).as_posix()))
    return paths


def bundle_readme(kind: str, base_name: str | None, base_sha: str | None) -> bytes:
    if kind == "component_views_supplement":
        text = ("Full-run component-view supplement for the BVM -> BQ -> CB -> ACC -> GAP 2x1 experiment.\n"
                f"Base canonical raw handoff: {base_name}\nBase SHA-256: {base_sha}\n"
                "Open plots/component_views/index.html. Raw CSVs are referenced by exact path and SHA-256;\n"
                "they remain in the base handoff and were not duplicated or modified.\n"
                "Two N1_10 source snapshot archives are included exactly as found in the workspace.\n"
                "This supplement makes no scientific interpretation and includes no new simulation.\n")
    else:
        text = ("Workspace snapshot bundle of files as present on 2026-09-24.\n"
                "This archive preserves the files byte-for-byte but does not independently certify\n"
                "solver identity, run completion, raw semantics, or scientific validity.\n"
                "No simulation was run while packaging. See BUNDLE_MANIFEST.json for member hashes.\n")
    return text.encode("utf-8")


def create_bundle(*, name: str, output: Path, qa_path: Path, kind: str,
                  sources: list[tuple[Path, str]], source_commit: str,
                  base_name: str | None = None, base_sha: str | None = None,
                  raw_by_run: dict[str, str] | None = None, dry_run: bool = False) -> dict[str, Any]:
    if output.exists() or qa_path.exists():
        raise FileExistsError(f"refusing to overwrite existing package/QA: {output}, {qa_path}")
    records = records_for(sources)
    total_bytes = sum(record["bytes"] for record in records)
    if dry_run:
        return {"bundle": name, "kind": kind, "package_path": output.relative_to(REPO).as_posix(),
                "source_count": len(records), "uncompressed_source_bytes": total_bytes,
                "base_package_sha256": base_sha, "overwrite": False}

    archive_manifest = {
        "schema": "josim-workspace-additions-bundle-v1",
        "bundle_name": name,
        "bundle_type": kind,
        "source_commit": source_commit,
        "parent_package_name": base_name,
        "parent_package_sha256": base_sha,
        "raw_sha256_by_run": raw_by_run or {},
        "scientific_interpretation_performed": False,
        "included_source_files": records,
    }
    manifest_bytes = (json.dumps(archive_manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    readme = bundle_readme(kind, base_name, base_sha)
    internal_manifest = "BUNDLE_MANIFEST.json"
    internal_readme = "README_BUNDLE.txt"

    with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for record, (source, _) in zip(records, sources, strict=True):
            archive.write(source, record["archive_path"])
        archive.writestr(internal_manifest, manifest_bytes)
        archive.writestr(internal_readme, readme)

    member_hashes = {}
    with zipfile.ZipFile(output, "r") as archive:
        bad = archive.testzip()
        if bad:
            raise RuntimeError(f"ZIP CRC check failed: {bad}")
        expected_names = {record["archive_path"] for record in records} | {internal_manifest, internal_readme}
        if set(archive.namelist()) != expected_names:
            raise RuntimeError(f"archive member set mismatch for {name}")
        for record in records:
            data = archive.read(record["archive_path"])
            actual = hashlib.sha256(data).hexdigest()
            if actual != record["sha256"] or len(data) != record["bytes"]:
                raise RuntimeError(f"archive member hash/size mismatch: {record['archive_path']}")
            member_hashes[record["archive_path"]] = actual
        if archive.read(internal_manifest) != manifest_bytes or archive.read(internal_readme) != readme:
            raise RuntimeError(f"embedded bundle metadata mismatch for {name}")
        member_hashes[internal_manifest] = hashlib.sha256(manifest_bytes).hexdigest()
        member_hashes[internal_readme] = hashlib.sha256(readme).hexdigest()

    qa = {"schema": "josim-workspace-additions-package-qa-v1", "status": "PASS",
          "bundle_name": name, "bundle_type": kind,
          "package_path": output.relative_to(REPO).as_posix(),
          "package_sha256": sha256(output), "package_bytes": output.stat().st_size,
          "file_count": len(member_hashes), "source_commit": source_commit,
          "parent_package_name": base_name, "parent_package_sha256": base_sha,
          "raw_sha256_by_run": raw_by_run or {},
          "reopened_zip_crc_and_member_hashes_pass": True,
          "included_file_sha256": member_hashes}
    write_json(qa_path, qa)
    return {"bundle": name, "kind": kind, "package_path": qa["package_path"],
            "package_sha256": qa["package_sha256"], "package_bytes": qa["package_bytes"],
            "file_count": qa["file_count"], "qa_status": qa["status"]}


def specs() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    base_qa, plot_manifest, reference = base_identity()
    source_specs = []
    for name, directory in SOURCE_BUNDLES:
        zip_path = directory / "handoff" / f"{name}_source_bundle_v1.zip"
        qa_path = directory / "handoff" / f"{name}_source_bundle_v1_PACKAGE_QA.json"
        source_specs.append({"name": name, "kind": "experiment_directory_snapshot",
                             "sources": directory_sources(name, directory),
                             "zip_path": zip_path, "qa_path": qa_path,
                             "base_name": None, "base_sha": None, "raw_by_run": {}})
    component_name = "bvm-bq-cb-gap-2x1-v2-20260923_component_views_v1"
    component_zip = ROOT / "handoff" / f"{component_name}.zip"
    component_qa = ROOT / "handoff" / f"{component_name}_PACKAGE_QA.json"
    component_paths = component_sources(plot_manifest)
    source_specs.append({"name": component_name, "kind": "component_views_supplement",
                         "sources": component_paths, "zip_path": component_zip,
                         "qa_path": component_qa,
                         "base_name": base_qa["package_path"].split("/")[-1],
                         "base_sha": base_qa["package_sha256"],
                         "raw_by_run": reference["raw_by_run"]})
    return source_specs, reference


def main() -> int:
    parser = argparse.ArgumentParser(description="Package all scoped new BVM experiment additions")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    bundles, reference = specs()
    commit = current_head()
    results = [create_bundle(name=spec["name"], output=spec["zip_path"], qa_path=spec["qa_path"],
                             kind=spec["kind"], sources=spec["sources"], source_commit=commit,
                             base_name=spec["base_name"], base_sha=spec["base_sha"],
                             raw_by_run=spec["raw_by_run"], dry_run=args.dry_run)
               for spec in bundles]
    print(json.dumps({"status": "DRY_RUN_PASS" if args.dry_run else "PASS",
                      "source_head": commit,
                      "canonical_base_package_sha256": reference["raw_by_run"] and
                      read_json(BASE_QA)["package_sha256"],
                      "bundles": results}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
