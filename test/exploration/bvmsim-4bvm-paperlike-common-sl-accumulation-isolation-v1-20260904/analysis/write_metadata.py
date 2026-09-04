#!/usr/bin/env python3
"""Write one immutable execution receipt after a JoSIM invocation."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def digest(path: Path) -> str | None:
    if not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mask", required=True)
    parser.add_argument("--deck", type=Path, required=True)
    parser.add_argument("--raw", type=Path, required=True)
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--solver", type=Path, required=True)
    parser.add_argument("--exit-code", type=int, required=True)
    parser.add_argument("--git-head-before-run", required=True)
    parser.add_argument("--command-text", required=True)
    args = parser.parse_args()
    if args.metadata.exists():
        raise RuntimeError(f"refusing to overwrite metadata: {args.metadata}")
    try:
        version = subprocess.check_output([str(args.solver), "--version"], text=True, stderr=subprocess.STDOUT).strip()
    except Exception as exc:  # pragma: no cover - receipt must preserve solver failure context
        version = f"unavailable: {exc}"
    record = {
        "schema": "bvmsim-paperlike-common-sl-run-metadata-v1",
        "mask": args.mask,
        "created_at_local": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "git_head_before_run": args.git_head_before_run,
        "command": args.command_text,
        "solver": {"path": str(args.solver), "sha256": digest(args.solver), "version": version},
        "artifacts": {
            "deck": {"path": str(args.deck), "sha256": digest(args.deck)},
            "raw": {"path": str(args.raw), "sha256": digest(args.raw), "exists": args.raw.is_file(), "size_bytes": args.raw.stat().st_size if args.raw.is_file() else None},
            "log": {"path": str(args.log), "sha256": digest(args.log), "exists": args.log.is_file(), "size_bytes": args.log.stat().st_size if args.log.is_file() else None},
        },
        "exit_code": args.exit_code,
        "execution_status": "RUN_PASS" if args.exit_code == 0 and args.raw.is_file() and args.raw.stat().st_size > 0 else "RUN_FAIL",
        "raw_immutable": True,
    }
    args.metadata.parent.mkdir(parents=True, exist_ok=True)
    args.metadata.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
