#!/usr/bin/env python3
"""Create and verify the immutable raw-evidence handoff package."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

SERIES = Path(__file__).resolve().parents[1]
REPO = next((path for path in (SERIES, *SERIES.parents) if (path / ".git").exists()), SERIES)
DELIVERY = Path("/mnt/d/BVM_Backages")


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"expected JSON object: {path}")
    return value


def repo_rel(path: Path) -> str:
    return path.resolve().relative_to(REPO.resolve()).as_posix()


def write_evidence_manifest() -> None:
    files = []
    for path in sorted(SERIES.rglob("*")):
        if not path.is_file() or path.name in {"delivery_manifest.json"} or path.suffix == ".tmp" or "__pycache__" in path.parts:
            continue
        files.append({"path": path.relative_to(SERIES).as_posix(), "sha256": sha256(path), "bytes": path.stat().st_size})
    write_json(SERIES / "analysis" / "RAW_ANALYSIS_HANDOFF_MANIFEST.json", {"schema": "bvm-qb-current-baseline-raw-analysis-handoff-v1", "experiment_id": SERIES.name, "raw_is_immutable_solver_output": True, "files_excluding_delivery_manifest": files})
    lines = ["# Evidence manifest", "", "| path | SHA-256 | bytes |", "|---|---|---:"] + [f"| `{item['path']}` | `{item['sha256']}` | {item['bytes']} |" for item in files]
    (SERIES / "EVIDENCE_MANIFEST.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def package(attempt: str) -> dict[str, Any]:
    provenance = read_json(SERIES / "provenance.json")
    result = read_json(SERIES / "result.json")
    if len(provenance.get("run_order", [])) != 15:
        raise RuntimeError("package requires exactly 15 completed runs")
    if result.get("qa", {}).get("raw_qa") != "PASS" or result.get("qa", {}).get("pre110_identity_qa") != "PASS" or result.get("qa", {}).get("replay_fidelity_qa") != "PASS":
        raise RuntimeError("raw and registered QA must pass before packaging")
    if result.get("visualization", {}).get("status") != "PASS":
        raise RuntimeError("visualization QA must pass before packaging")
    write_evidence_manifest()
    DELIVERY.mkdir(parents=True, exist_ok=True)
    package_path = DELIVERY / f"{SERIES.name}_raw_handoff.zip"
    version = "v1"
    number = 2
    while package_path.exists():
        version = f"v{number}"
        package_path = DELIVERY / f"{SERIES.name}_{version}_raw_handoff.zip"
        number += 1
    files: list[tuple[Path, str]] = []
    for path in sorted(SERIES.rglob("*")):
        if not path.is_file() or path.name in {"delivery_manifest.json"} or path.suffix == ".tmp" or "__pycache__" in path.parts:
            continue
        files.append((path, path.relative_to(SERIES).as_posix()))
    files.append((Path(__file__), "executor/package.py"))
    records = [{"path": archive_name, "sha256": sha256(path), "bytes": path.stat().st_size} for path, archive_name in files]
    with zipfile.ZipFile(package_path, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path, archive_name in files:
            archive.write(path, archive_name)
    with zipfile.ZipFile(package_path, "r") as archive:
        reopened = {name: hashlib.sha256(archive.read(name)).hexdigest() for name in archive.namelist()}
    expected = {item["path"]: item["sha256"] for item in records}
    raw_members = [f"runs/{attempt}/cases/{run_id}/raw.csv" for run_id in provenance["run_order"]]
    qa = {"schema": "bvm-qb-current-baseline-package-qa-v1", "status": "PASS" if expected == reopened and all(member in reopened for member in raw_members) else "FAIL", "package_version": version, "package_path": str(package_path), "package_sha256": sha256(package_path), "package_bytes": package_path.stat().st_size, "file_count": len(records), "expected_file_hashes_match_after_reopen": expected == reopened, "contains_all_new_run_raw": all(member in reopened for member in raw_members), "new_run_raw_members": raw_members, "contains_reference_raw_copies": False, "contains_delivery_manifest": False, "delivery_manifest_outside_zip": True, "no_cross_run_comparison_plots": True, "not_in_git": True, "zip_files": records}
    write_json(SERIES / "analysis" / "PACKAGE_QA.json", qa)
    manifest = {"schema": "bvm-qb-current-baseline-delivery-manifest-v1", "experiment_id": SERIES.name, "attempt": attempt, "status": "READY_FOR_DRIVE_UPLOAD" if qa["status"] == "PASS" else "PACKAGE_INVALID", "package_version": version, "package_path": str(package_path), "package_sha256": qa["package_sha256"], "package_bytes": qa["package_bytes"], "package_qa": qa, "drive_folder_id": "1--nlY7Nq5ArVPydJNrnQf-EGmwN-undh", "drive_file_id": None, "drive_url": None}
    write_json(SERIES / "delivery_manifest.json", manifest)
    provenance["package"] = {"status": manifest["status"], "package_version": version, "package_path": str(package_path), "package_sha256": qa["package_sha256"], "package_bytes": qa["package_bytes"], "package_qa": qa, "delivery_manifest_path": "delivery_manifest.json", "drive_file_id": None, "drive_url": None}
    write_json(SERIES / "provenance.json", provenance)
    result["package"] = {"status": manifest["status"], "package_version": version, "package_path": str(package_path), "package_sha256": qa["package_sha256"], "package_bytes": qa["package_bytes"], "file_count": qa["file_count"], "delivery_manifest_path": "delivery_manifest.json"}
    write_json(SERIES / "result.json", result)
    brief = SERIES / "RESULT_BRIEF.md"
    text = brief.read_text(encoding="utf-8") if brief.is_file() else ""
    if "## Evidence package" not in text:
        text += f"\n## Evidence package\n\n- ZIP: `{package_path}`\n- SHA-256: `{qa['package_sha256']}`\n- Bytes: `{qa['package_bytes']}`\n- Package QA: `{qa['status']}`\n"
        brief.write_text(text, encoding="utf-8")
    if qa["status"] != "PASS":
        raise RuntimeError("package QA failed")
    print(json.dumps({"status": "PASS", "package_path": str(package_path), "sha256": qa["package_sha256"], "bytes": qa["package_bytes"], "files": qa["file_count"]}, ensure_ascii=False, indent=2))
    return manifest


def record_drive(file_id: str, url: str, size: int) -> None:
    manifest_path = SERIES / "delivery_manifest.json"
    manifest = read_json(manifest_path)
    package_path = Path(manifest["package_path"])
    if not package_path.is_file() or sha256(package_path) != manifest["package_sha256"] or int(size) != int(manifest["package_bytes"]):
        raise RuntimeError("local package SHA/bytes verification failed")
    manifest.update({"status": "UPLOADED", "drive_file_id": file_id, "drive_url": url, "uploaded_at": now(), "drive_verified_local_sha256": manifest["package_sha256"], "drive_verified_local_bytes": manifest["package_bytes"], "remote_sha256_from_connector": None})
    write_json(manifest_path, manifest)
    provenance = read_json(SERIES / "provenance.json")
    provenance["package"].update({"status": "UPLOADED", "drive_file_id": file_id, "drive_url": url, "drive_uploaded_at": manifest["uploaded_at"], "delivery_manifest_sha256": sha256(manifest_path), "drive_sha256_verified": "metadata SHA not supplied by connector"})
    write_json(SERIES / "provenance.json", provenance)
    result = read_json(SERIES / "result.json")
    result["package"].update({"status": "UPLOADED", "drive_file_id": file_id, "drive_url": url})
    write_json(SERIES / "result.json", result)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("attempt", nargs="?")
    parser.add_argument("command", nargs="?", choices=("record-drive",))
    parser.add_argument("drive_id", nargs="?")
    parser.add_argument("drive_url", nargs="?")
    parser.add_argument("drive_bytes", nargs="?", type=int)
    args = parser.parse_args()
    if args.command == "record-drive":
        if not args.drive_id or args.drive_url is None or args.drive_bytes is None:
            raise RuntimeError("record-drive requires FILE_ID URL BYTES")
        record_drive(args.drive_id, args.drive_url, args.drive_bytes)
        return 0
    if not args.attempt:
        raise RuntimeError("package requires attempt such as A001")
    package(args.attempt)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
