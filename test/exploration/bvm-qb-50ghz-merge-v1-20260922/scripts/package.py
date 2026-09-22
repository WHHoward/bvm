#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = next(path for path in (ROOT, *ROOT.parents) if (path / ".git").exists())


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def excluded(path: Path) -> bool:
    return "__pycache__" in path.parts or path.suffix == ".pyc" or path.name == "PACKAGE_QA.json" or (path.parent.name == "handoff" and path.suffix == ".zip")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", default="v1")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    files = [path for path in sorted(ROOT.rglob("*")) if path.is_file() and not excluded(path)]
    package_name = f"{ROOT.name}_raw_handoff_{args.tag}.zip" if args.tag != "v1" else f"{ROOT.name}_raw_handoff.zip"
    package = ROOT / "handoff" / package_name
    mirror = Path("/mnt/d/BVM_Backages") / package_name
    plan = {"package": str(package), "mirror": str(mirror), "file_count": len(files), "files": [str(path.relative_to(ROOT)) for path in files]}
    if args.dry_run:
        print(json.dumps(plan, ensure_ascii=False, indent=2)); return 0
    package.parent.mkdir(parents=True, exist_ok=True)
    if package.exists():
        raise SystemExit(f"immutable package already exists: {package}")
    with zipfile.ZipFile(package, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in files:
            archive.write(path, arcname=path.relative_to(ROOT).as_posix())
    included = {str(path.relative_to(ROOT)): digest(path) for path in files}
    with zipfile.ZipFile(package, "r") as archive:
        names = sorted(archive.namelist())
        if names != sorted(included):
            raise SystemExit("package contents changed while reopening archive")
    if mirror.exists() and digest(mirror) != digest(package):
        raise SystemExit(f"mirror exists with different bytes: {mirror}")
    mirror.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(package, mirror)
    qa = {"schema": "bvm-qb-50ghz-package-qa-v1", "status": "PASS" if digest(package) == digest(mirror) else "FAIL", "package_type": "raw_handoff", "package": str(package.relative_to(REPO)), "package_sha256": digest(package), "package_bytes": package.stat().st_size, "package_file_count": len(files), "mirror": str(mirror), "mirror_sha256": digest(mirror), "mirror_bytes": mirror.stat().st_size, "included_file_sha256": included, "raw_immutable": True, "scientific_interpretation_performed": False, "phase_d_status": "NOT_RUN_DIRECT_MERGE_GATE_FAIL"}
    (ROOT / "analysis" / "PACKAGE_QA.json").write_text(json.dumps(qa, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    checkpoints = ROOT / "analysis" / "PACKAGE_CHECKPOINTS.json"
    data = json.loads(checkpoints.read_text(encoding="utf-8")) if checkpoints.is_file() else {"schema": "bvm-qb-50ghz-package-checkpoints-v1", "checkpoints": []}
    data["checkpoints"].append({"package_name": package.name, "package_path": qa["package"], "package_sha256": qa["package_sha256"], "head_commit_at_package": __import__("subprocess").check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip(), "source": args.tag})
    checkpoints.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(qa, ensure_ascii=False, indent=2))
    return 0 if qa["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
