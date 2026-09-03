#!/usr/bin/env python3
"""Run probe-only copies of the six historical PHASE-B decks."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from extend_sl_endpoint_decks import (  # noqa: E402
    EXP,
    OUTPUT_ROOT,
    PARENT_ROOT,
    REPO,
    STATES,
    added_endpoint_labels,
    digest,
    endpoint_labels,
    make_deck,
    write_once,
)


SOLVER = REPO / "build/josim-cli"
PHASE_A_GATE = REPO / "test/exploration/research-workflow-tooling-consolidation-v1-20260903/parity/parity.json"


def main() -> int:
    if not SOLVER.is_file() or not SOLVER.stat().st_mode & 0o111:
        raise RuntimeError(f"missing executable solver: {SOLVER}")
    gate = json.loads(PHASE_A_GATE.read_text(encoding="utf-8"))
    if gate.get("status") != "INFRA_REGRESSION_PASS" or gate.get("simulation_invoked") is not False:
        raise RuntimeError("PHASE A gate is not INFRA_REGRESSION_PASS with simulation_invoked=false")

    parent_raw_hashes = {}
    planned: list[tuple[str, Path, Path, Path, Path, Path]] = []
    for state in STATES:
        parent_deck = PARENT_ROOT / state / "deck.cir"
        parent_raw = PARENT_ROOT / state / "raw.csv"
        if not parent_deck.is_file() or not parent_raw.is_file():
            raise RuntimeError(f"missing parent artifact for state {state}")
        run_dir = OUTPUT_ROOT / state
        paths = (run_dir / "deck.cir", run_dir / "raw.csv", run_dir / "run.log", run_dir / "metadata.json")
        for path in paths:
            if path.exists():
                raise RuntimeError(f"refusing to overwrite immutable endpoint artifact: {path}")
        parent_raw_hashes[state] = digest(parent_raw)
        planned.append((state, parent_deck, *paths))

    failed = 0
    for state, parent_deck, deck, raw, log, metadata in planned:
        content = make_deck(parent_deck)
        write_once(deck, content)
        command = [str(SOLVER), "-o", str(raw), str(deck)]
        with log.open("x", encoding="utf-8") as handle:
            completed = subprocess.run(
                command,
                cwd=REPO,
                stdout=handle,
                stderr=subprocess.STDOUT,
                check=False,
            )
        log_text = log.read_text(encoding="utf-8", errors="replace")
        record = {
            "schema": "bvmsim-4bvm-sl-endpoint-probe-run-metadata-v1",
            "created_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
            "state": state,
            "source_class": "HISTORICAL_BVMSIM",
            "probe_extension_only": True,
            "command": " ".join(command),
            "exit_code": completed.returncode,
            "parent_deck": str(parent_deck.relative_to(REPO)),
            "parent_deck_sha256": digest(parent_deck),
            "parent_raw": str((PARENT_ROOT / state / "raw.csv").relative_to(REPO)),
            "parent_raw_sha256": parent_raw_hashes[state],
            "deck": str(deck.relative_to(REPO)),
            "deck_sha256": digest(deck),
            "raw": str(raw.relative_to(REPO)),
            "raw_sha256": digest(raw) if raw.is_file() else None,
            "run_log": str(log.relative_to(REPO)),
            "run_log_sha256": digest(log),
            "solver": {
                "path": str(SOLVER),
                "sha256": digest(SOLVER),
            },
            "requested_timestep_ps": 0.1,
            "stop_time_ps": 200,
            "output_start_ps": 45,
            "added_probe_labels": list(added_endpoint_labels()),
            "all_sl_endpoint_labels": list(endpoint_labels()),
            "model_warning_detected": bool(re.search(r"Missing model:|Using default model", log_text, re.I)),
            "artifact_status": "EXECUTION_COMPLETE" if completed.returncode == 0 and raw.is_file() else "EXECUTION_FAILED",
        }
        write_once(metadata, json.dumps(record, indent=2, ensure_ascii=False) + "\n")
        if completed.returncode != 0 or not raw.is_file():
            failed = 1
            print(f"state {state}: solver exit {completed.returncode}", file=sys.stderr)
        else:
            print(f"state {state}: solver exit 0; raw={raw}")

    for state in STATES:
        parent_raw = PARENT_ROOT / state / "raw.csv"
        if digest(parent_raw) != parent_raw_hashes[state]:
            raise RuntimeError(f"parent raw changed during endpoint probe run: {parent_raw}")
    print(f"SL endpoint probe runs complete: {len(STATES) - failed}/{len(STATES)}")
    return failed


if __name__ == "__main__":
    raise SystemExit(main())
