#!/usr/bin/env python3
"""Final machine gate between deck generation and the four authorized solves."""

from __future__ import annotations

import csv
import json
import re
from decimal import Decimal
from pathlib import Path

from common import (
    CONTROL_RAWS,
    EXPECTED_HASHES,
    EXP,
    HEAD,
    RUNS,
    current_head,
    json_text,
    sha256,
    write_once,
)


PAIR_RE = re.compile(
    r"([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)[pP]\s+"
    r"([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)"
)


def deck_pairs(path: Path) -> list[tuple[Decimal, Decimal]]:
    text = path.read_text(encoding="utf-8")
    start = text.lower().index("pwl(") + 4
    end = text.index(")", start)
    return [(Decimal(time), Decimal(value)) for time, value in PAIR_RE.findall(text[start:end])]


def source_pairs(path: Path) -> list[tuple[Decimal, Decimal]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return [
            (Decimal(row["time_ps"]), Decimal(row["I_REPLAY_A"]))
            for row in csv.DictReader(handle)
        ]


def main() -> int:
    failures: list[str] = []
    preflight_path = EXP / "analysis/preflight.json"
    registry_path = EXP / "analysis/transformation_registry.json"
    reconstruction_path = EXP / "analysis/source_reconstruction.json"
    preflight = json.loads(preflight_path.read_text(encoding="utf-8"))
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    reconstruction = json.loads(reconstruction_path.read_text(encoding="utf-8"))
    if current_head() != HEAD:
        failures.append(f"HEAD changed: {current_head()}")
    if preflight.get("status") != "PASS":
        failures.append("preflight is not PASS")
    if registry.get("head") != HEAD:
        failures.append("transformation registry HEAD mismatch")
    if reconstruction.get("status") != "PASS":
        failures.append("source reconstruction is not PASS")
    if list(registry.get("authorized_runs", {})) != list(RUNS):
        failures.append("authorized run IDs are not exactly the four registered runs")
    if "Status: PASS; READY_TO_SOLVE" not in (EXP / "PREFLIGHT.md").read_text(encoding="utf-8"):
        failures.append("PREFLIGHT.md is not marked PASS; READY_TO_SOLVE")

    for name, path in CONTROL_RAWS.items():
        if sha256(path) != EXPECTED_HASHES[f"{name}_raw"]:
            failures.append(f"immutable control changed: {name}")

    frozen_artifacts: dict[str, object] = {}
    for run_id in RUNS:
        record = registry["authorized_runs"].get(run_id)
        if not record:
            failures.append(f"missing registry record: {run_id}")
            continue
        source_path = EXP.parent.parent.parent / record["source_path"]
        deck_path = EXP.parent.parent.parent / record["deck_path"]
        if not source_path.is_file() or not deck_path.is_file():
            failures.append(f"missing generated artifact: {run_id}")
            continue
        source = source_pairs(source_path)
        deck = deck_pairs(deck_path)
        if len(source) != 2059 or len(deck) != 2059:
            failures.append(f"{run_id}: expected 2059 source/deck pairs")
        if source != deck:
            failures.append(f"{run_id}: deck PWL does not exactly match source CSV")
        netlist = [
            line.strip()
            for line in deck_path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith(("*", ".", "+"))
        ]
        if sum(line == "XBQ1 QBIN QBOUT BQ" for line in netlist) != 1:
            failures.append(f"{run_id}: QB topology mismatch")
        if sum(line.startswith("XJTL1_") and line.endswith(" jtl") for line in netlist) != 6:
            failures.append(f"{run_id}: JTL stage count mismatch")
        if sum(line == "R_TERM JTL6_OUT 0 10" for line in netlist) != 1:
            failures.append(f"{run_id}: termination mismatch")
        if any("BVM" in line or "B_JSL" in line or "COMMON_SL" in line for line in netlist):
            failures.append(f"{run_id}: physical BVM/JSL element leaked into replay")
        if [line for line in deck_path.read_text(encoding="utf-8").splitlines() if line.lower().startswith(".tran")] != [".tran 0.1p 206p"]:
            failures.append(f"{run_id}: timing mismatch")
        frozen_artifacts[run_id] = {
            "source_path": record["source_path"],
            "source_sha256": sha256(source_path),
            "source_bytes": source_path.stat().st_size,
            "deck_path": record["deck_path"],
            "deck_sha256": sha256(deck_path),
            "deck_bytes": deck_path.stat().st_size,
            "pwl_pairs": len(deck),
        }

    unexpected = []
    for run_id in RUNS:
        run_dir = EXP / "runs" / run_id
        for filename in ("raw.csv", "run.log", "metadata.json"):
            if (run_dir / filename).exists():
                unexpected.append(f"{run_id}/{filename}")
    if unexpected:
        failures.append(f"new solve artifacts exist before solve: {unexpected}")

    record = {
        "schema": "jm2-delta4-ready-to-solve-gate-v1",
        "experiment_id": EXP.name,
        "head": current_head(),
        "status": "PASS" if not failures else "FAIL",
        "preflight_status": preflight.get("status"),
        "source_reconstruction_status": reconstruction.get("status"),
        "authorized_new_physical_solves": list(RUNS),
        "new_physical_solve_count": 4,
        "controls": {"N3_REPLAY": "immutable", "N4_REPLAY": "immutable"},
        "frozen_generated_artifacts": frozen_artifacts,
        "failures": failures,
    }
    write_once(EXP / "analysis/pre_solve_gate.json", json_text(record))
    print(json.dumps({"status": record["status"], "runs": list(RUNS), "failures": failures}, ensure_ascii=False))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
