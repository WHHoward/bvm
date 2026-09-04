#!/usr/bin/env python3
"""Write one immutable metadata record after one JoSIM invocation."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path


REPO = Path(__file__).resolve().parents[4]


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
        raise RuntimeError(f"refusing to overwrite immutable metadata: {args.metadata}")

    log_text = args.log.read_text(encoding="utf-8", errors="replace") if args.log.is_file() else ""
    version = subprocess.run(
        [str(args.solver), "--version"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    record = {
        "schema": "bvmsim-4bvm-allone-selective-read-run-metadata-v1",
        "created_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "mask": args.mask,
        "bit_order": "b3b2b1b0 -> BVM1/BVM2/BVM3/BVM4",
        "source_class": "HISTORICAL_BVMSIM_JM2_CONNECTED_VARIANT",
        "git_head_before_run": args.git_head_before_run,
        "command": {"text": args.command_text, "exit_code": args.exit_code},
        "paths": {
            "deck": str(args.deck.resolve().relative_to(REPO.resolve())),
            "raw": str(args.raw.resolve().relative_to(REPO.resolve())),
            "log": str(args.log.resolve().relative_to(REPO.resolve())),
        },
        "hashes": {
            "deck_sha256": digest(args.deck),
            "raw_sha256": digest(args.raw),
            "log_sha256": digest(args.log),
        },
        "solver": {
            "path": str(args.solver.resolve().relative_to(REPO.resolve())),
            "sha256": digest(args.solver),
            "version_exit_code": version.returncode,
            "version_stdout": version.stdout.strip(),
            "version_stderr": version.stderr.strip(),
        },
        "numerics": {
            "timestep_ps": 0.1,
            "stop_time_ps": 200.0,
            "output_start_ps": 45.0,
        },
        "model_warning_detected": bool(re.search(r"Missing model:|Using default model", log_text, re.I)),
        "artifact_status": (
            "EXECUTION_COMPLETE"
            if args.exit_code == 0 and args.raw.is_file() and args.raw.stat().st_size > 0
            else "EXECUTION_FAILED"
        ),
    }
    args.metadata.parent.mkdir(parents=True, exist_ok=True)
    args.metadata.write_text(
        json.dumps(record, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
