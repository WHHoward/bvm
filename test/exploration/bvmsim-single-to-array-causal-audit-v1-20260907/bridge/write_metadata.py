#!/usr/bin/env python3
"""Write immutable metadata for one G1/G2 JoSIM run."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--generation", required=True)
    parser.add_argument("--deck", type=Path, required=True)
    parser.add_argument("--raw", type=Path, required=True)
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--solver", type=Path, required=True)
    parser.add_argument("--exit-code", type=int, required=True)
    parser.add_argument("--git-head-before-run", required=True)
    parser.add_argument("--command", nargs=argparse.REMAINDER, required=True)
    args = parser.parse_args()
    if args.metadata.exists():
        raise RuntimeError(f"refusing to overwrite metadata: {args.metadata}")
    command = list(args.command)
    if command[:1] == ["--"]:
        command = command[1:]
    payload = {
        "schema": "bvmsim-single-to-array-bridge-run-metadata-v1",
        "generation": args.generation,
        "created_at_local": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "git_head_before_run": args.git_head_before_run,
        "command": command,
        "solver": {"path": str(args.solver.resolve()), "sha256": sha256(args.solver), "version": subprocess.check_output([str(args.solver), "--version"], text=True, stderr=subprocess.STDOUT)},
        "artifacts": {
            "deck": {"path": str(args.deck.resolve()), "sha256": sha256(args.deck)},
            "raw": {"path": str(args.raw.resolve()), "sha256": sha256(args.raw), "size_bytes": args.raw.stat().st_size},
            "log": {"path": str(args.log.resolve()), "sha256": sha256(args.log), "size_bytes": args.log.stat().st_size},
        },
        "exit_code": args.exit_code,
        "execution_status": "RUN_PASS" if args.exit_code == 0 else "RUN_FAIL",
        "raw_immutable": True,
        "parameter_tuning": False,
    }
    args.metadata.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
