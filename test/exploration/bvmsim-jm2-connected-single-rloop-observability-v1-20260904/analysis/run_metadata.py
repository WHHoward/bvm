#!/usr/bin/env python3
"""Write immutable Workflow-V1 metadata for one executed run."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def relative(path: Path) -> str:
    return path.resolve().relative_to(REPO.resolve()).as_posix()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("condition")
    parser.add_argument("state", type=int)
    parser.add_argument("exit_code", type=int)
    parser.add_argument("deck", type=Path)
    parser.add_argument("raw", type=Path)
    parser.add_argument("log", type=Path)
    parser.add_argument("solver", type=Path)
    parser.add_argument("--git-head-before-run", required=True)
    parser.add_argument("--command", nargs=argparse.REMAINDER, required=True)
    # argparse treats a literal ``--`` before a REMAINDER option as an
    # unrecognized option on the Python version used in this workspace.  The
    # run script deliberately keeps that separator for command clarity, so
    # remove only that one marker before parsing; the solver argv itself is
    # preserved byte-for-byte.
    argv = sys.argv[1:]
    if "--command" in argv:
        command_index = argv.index("--command")
        if command_index + 1 < len(argv) and argv[command_index + 1] == "--":
            del argv[command_index + 1]
    args = parser.parse_args(argv)
    command = list(args.command)
    if command and command[0] == "--":
        command.pop(0)
    run_dir = args.deck.parent
    metadata = run_dir / "metadata.json"
    if metadata.exists():
        raise RuntimeError(f"refusing to overwrite metadata: {metadata}")
    solver_version = subprocess.run([str(args.solver), "--version"], capture_output=True, text=True, check=False)
    log_text = args.log.read_text(encoding="utf-8", errors="replace") if args.log.is_file() else ""
    warnings = []
    if "Missing model:" in log_text:
        warnings.append("Missing model")
    if "Using default model" in log_text:
        warnings.append("Using default model")
    record = {
        "schema": "josim-experiment-workflow-v1-run-metadata",
        "condition": args.condition,
        "state": args.state,
        "source_class": "HISTORICAL_BVMSIM_JM2_CONNECTED_VARIANT",
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "git_commit_before_run": args.git_head_before_run,
        "solver": {
            "path": str(args.solver.resolve()),
            "version": solver_version.stdout.strip(),
            "sha256": sha256(args.solver),
        },
        "command": {"argv": command, "exit_code": args.exit_code},
        "paths": {
            "deck": relative(args.deck),
            "raw": relative(args.raw),
            "log": relative(args.log),
        },
        "hashes": {
            "deck_sha256": sha256(args.deck),
            "raw_sha256": sha256(args.raw),
            "log_sha256": sha256(args.log),
        },
        "numerics": {"timestep": "0.1 ps", "stop_time": "200 ps"},
        "model_warning": warnings,
        "artifact_status": "VALID" if args.exit_code == 0 and args.raw.is_file() and args.raw.stat().st_size > 0 else "ARTIFACT_INVALID",
    }
    metadata.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
