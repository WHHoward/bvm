#!/usr/bin/env python3
"""Scoped source/package/push workflow for the new 4x4 diagonal experiment."""

from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

SERIES = Path(__file__).resolve().parents[1]
REPO = SERIES.parents[2]
RUNS = SERIES / "runs"
HANDOFF = SERIES / "handoff"
MIRROR_DEFAULT = Path("/mnt/d/BVM_Backages")
MIRROR_DEFAULT = Path("/mnt/d/BVM_Backages")
ROOT_SUBMIT_PATH = REPO / "scripts" / "submit.py"


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


def validate_scope() -> None:
    root = load_root_submit()
    changes = root.working_changes()
    outside = sorted(path for path in changes if not root.in_scope(path, [SERIES]))
    if outside:
        raise RuntimeError("unrelated worktree changes outside this experiment: " + ", ".join(outside))
    if not RUNS.is_dir():
        raise RuntimeError("runs/ is missing; no completed physical batch found")
    run_dirs = sorted(path for path in RUNS.iterdir() if path.is_dir() and path.name.startswith("A"))
    expected = [f"A{i:03d}_{case}" for i, case in enumerate(
        ("D3_N0", "D3_N1", "D3_N2", "D3_N3", "D3_N4", "PAPER_1101_1101"), start=1)]
    if [path.name for path in run_dirs] != expected:
        raise RuntimeError(f"exact six-run closure required; found {[p.name for p in run_dirs]}")
    for path in run_dirs:
        result = json.loads((path / "result.json").read_text(encoding="utf-8"))
        qa = json.loads((path / "qa.json").read_text(encoding="utf-8"))
        if result.get("artifact_status") != "VALID" or qa.get("status") != "PASS":
            raise RuntimeError(f"run is not mechanically valid: {path.name}")
        if int(result.get("physical_solve_count", 0)) != 1:
            raise RuntimeError(f"run physical_solve_count is not one: {path.name}")


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


def append_metadata_package(result: dict[str, Any], all_results: list[dict[str, Any]]) -> None:
    summary = SERIES / "BATCH_SUMMARY.md"
    text = summary.read_text(encoding="utf-8")
    marker = "<!-- METADATA_PACKAGE -->"
    total_bytes = sum(int(item["bytes"]) for item in all_results)
    replacement = (f"| metadata | {result['bytes']:,} | `{result['sha256']}` |\n\n"
                   f"Total compressed ZIP bytes (7 archives): **{total_bytes:,}**.\n"
                   "The metadata ZIP's internal summary predates this self-identity row; its detached QA sidecar is authoritative.\n")
    if marker not in text:
        raise RuntimeError("BATCH_SUMMARY metadata package marker is missing")
    summary.write_text(text.replace(marker, replacement), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Submit/package only this 4x4 experiment scope")
    parser.add_argument("tag")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-push", action="store_true")
    parser.add_argument("--message", default="experiment: add BVM 4x4 diagonal batch")
    parser.add_argument("--mirror-dir", default=str(MIRROR_DEFAULT))
    args = parser.parse_args()
    try:
        validate_scope()
        root = load_root_submit()
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
        subprocess.run(["git", "commit", "-m", args.message], cwd=REPO, check=True)
        source_commit = git("rev-parse", "HEAD")
        package_results = []
        for spec in specs[:-1]:
            package_results.append(root.archive_bundle(spec, source_commit))
        update_summary_with_packages(package_results)
        subprocess.run(["git", "add", "--", (SERIES / "BATCH_SUMMARY.md").relative_to(REPO).as_posix()],
                       cwd=REPO, check=True)
        if git("diff", "--cached", "--quiet", check=False) != "":
            subprocess.run(["git", "commit", "-m", "docs: record 4x4 run package hashes"], cwd=REPO, check=True)
        summary_commit = git("rev-parse", "HEAD")
        package_results.append(root.archive_bundle(specs[-1], summary_commit))
        append_metadata_package(package_results[-1], package_results)
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
