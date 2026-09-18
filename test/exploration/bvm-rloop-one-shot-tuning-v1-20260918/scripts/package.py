#!/usr/bin/env python3
"""Create an immutable evidence ZIP and verify the configured local mirror."""

from __future__ import annotations

import json
import os
import shutil
import zipfile
import argparse
from datetime import datetime
from pathlib import Path

SERIES = Path(__file__).resolve().parents[1]
REPO = next(path for path in (SERIES, *SERIES.parents) if (path / ".git").exists())


def sha256(path: Path) -> str:
    import hashlib
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def repo_rel(path: Path) -> str:
    return path.resolve().relative_to(REPO.resolve()).as_posix()


def main() -> int:
    parser = argparse.ArgumentParser(description="Create an immutable evidence ZIP")
    parser.add_argument("--tag", default="", help="optional package tag, e.g. v2")
    args = parser.parse_args()
    handoff = SERIES / "handoff"
    handoff.mkdir(parents=True, exist_ok=True)
    suffix = f"_{args.tag}" if args.tag else ""
    package = handoff / f"{SERIES.name}_raw_handoff{suffix}.zip"
    if package.exists():
        raise RuntimeError(f"refusing to overwrite existing package: {package}")
    files = []
    for path in sorted(SERIES.rglob("*")):
        if not path.is_file() or path == package:
            continue
        if "__pycache__" in path.parts or path.suffix == ".pyc" or (path.parent == handoff and path.suffix == ".zip") or path.name == "PACKAGE_QA.json":
            continue
        files.append(path)
    with zipfile.ZipFile(package, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in files:
            archive.write(path, repo_rel(path))
    package_hash = sha256(package)
    mirror = Path("/mnt/d/BVM_Backages") / package.name
    mirror.parent.mkdir(parents=True, exist_ok=True)
    if mirror.exists():
        raise RuntimeError(f"refusing to overwrite existing mirror: {mirror}")
    shutil.copy2(package, mirror)
    mirror_hash = sha256(mirror)
    qa = {"schema": "bvm-rloop-one-shot-package-qa-v1", "status": "PASS" if package_hash == mirror_hash else "FAIL", "created_at": datetime.now().astimezone().isoformat(timespec="seconds"), "package": repo_rel(package), "package_sha256": package_hash, "package_bytes": package.stat().st_size, "package_file_count": len(files), "mirror": str(mirror), "mirror_sha256": mirror_hash, "mirror_bytes": mirror.stat().st_size, "raw_immutable": True, "scientific_interpretation_performed": False}
    (SERIES / "analysis" / "PACKAGE_QA.json").write_text(json.dumps(qa, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    result_path = SERIES / "result.json"
    if result_path.is_file():
        result = json.loads(result_path.read_text(encoding="utf-8"))
        result["package"] = qa
        result["status"] = "EXPERIMENT_COMPLETE_AWAITING_SCIENTIFIC_REVIEW" if qa["status"] == "PASS" else "PACKAGE_QA_FAILED"
        result["artifact_status"] = "VALID" if qa["status"] == "PASS" else "INVALID"
        result["scientific_interpretation_performed"] = False
        result["automatic_follow_up"] = False
        result["stop"] = {"final_marker": "EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW", "automatic_follow_up": False}
        result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(qa, ensure_ascii=False, indent=2))
    return 0 if qa["status"] == "PASS" else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(f"ERROR: {exc}")
        raise SystemExit(2)
