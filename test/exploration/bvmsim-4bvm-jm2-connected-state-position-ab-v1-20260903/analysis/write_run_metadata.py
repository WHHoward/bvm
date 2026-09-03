#!/usr/bin/env python3
"""在每个 solver 调用后写入一次、不可覆盖的运行 metadata。"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def digest(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--state", required=True)
    parser.add_argument("--deck", type=Path, required=True)
    parser.add_argument("--raw", type=Path, required=True)
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--exit-code", type=int, required=True)
    parser.add_argument("--command-text", required=True)
    args = parser.parse_args()
    if args.metadata.exists():
        raise RuntimeError(f"refusing to overwrite metadata: {args.metadata}")
    solver = args.repo / "build/josim-cli"
    log_text = args.log.read_text(encoding="utf-8", errors="replace") if args.log.is_file() else ""
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=args.repo, text=True).strip()
    try:
        solver_version = subprocess.check_output([str(solver), "--version"], cwd=args.repo, text=True)
    except Exception as exc:  # metadata remains useful for a failed run
        solver_version = f"unavailable: {exc}"
    record = {
        "schema": "bvmsim-4bvm-jm2-connected-run-metadata-v1",
        "created_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "state": args.state,
        "source_class": "HISTORICAL_BVMSIM_JM2_CONNECTED_VARIANT",
        "git_head_before_solver": head,
        "command": args.command_text,
        "exit_code": args.exit_code,
        "deck": str(args.deck.relative_to(args.repo)),
        "deck_sha256": digest(args.deck),
        "raw": str(args.raw.relative_to(args.repo)),
        "raw_sha256": digest(args.raw),
        "run_log": str(args.log.relative_to(args.repo)),
        "run_log_sha256": digest(args.log),
        "solver": {
            "path": str(solver.relative_to(args.repo)),
            "sha256": digest(solver),
            "version": solver_version,
        },
        "requested_timestep_ps": 0.1,
        "stop_time_ps": 200,
        "output_start_ps": 45,
        "model_warning_detected": bool(re.search(r"Missing model:|Using default model", log_text, re.I)),
        "artifact_status": "EXECUTION_COMPLETE" if args.exit_code == 0 and args.raw.is_file() else "EXECUTION_FAILED",
    }
    args.metadata.parent.mkdir(parents=True, exist_ok=True)
    args.metadata.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
