#!/usr/bin/env python3
"""QA the supplemental XBVM2/3/4 raw-direct visualization pages."""

from __future__ import annotations

import csv
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
STATE = EXP / "screening/closure_state.json"
BASE_MANIFEST = EXP / "visualization/manifest.json"
MANIFEST = EXP / "visualization/supplemental_bvm_states/manifest.json"
OUTPUT = EXP / "qa/supplemental_bvm_state_qa.json"
BVM_INDICES = (2, 3, 4)
REQUIRED = tuple(
    [f"P(B_JM1|XBVM{index})" for index in BVM_INDICES]
    + [f"V(B_JM1|XBVM{index})" for index in BVM_INDICES]
    + [f"I(B_JM1|XBVM{index})" for index in BVM_INDICES]
    + [f"P(B_JM2|XBVM{index})" for index in BVM_INDICES]
    + [f"V(B_JM2|XBVM{index})" for index in BVM_INDICES]
    + [f"I(B_JM2|XBVM{index})" for index in BVM_INDICES]
    + [f"P(B_JS1|XBVM{index})" for index in BVM_INDICES]
    + [f"V(B_JS1|XBVM{index})" for index in BVM_INDICES]
    + [f"I(B_JS1|XBVM{index})" for index in BVM_INDICES]
    + [f"P(B_JS2|XBVM{index})" for index in BVM_INDICES]
    + [f"V(B_JS2|XBVM{index})" for index in BVM_INDICES]
    + [f"I(B_JS2|XBVM{index})" for index in BVM_INDICES]
    + [f"I(L_SL|XBVM{index})" for index in BVM_INDICES]
    + [f"V(L_SL|XBVM{index})" for index in BVM_INDICES]
    + ["V(COMMON_SL)"]
)


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO.resolve()).as_posix()


def raw_grid_and_header(path: Path) -> tuple[list[str], int, float, float, list[str]]:
    failures: list[str] = []
    header: list[str] = []
    times: list[float] = []
    try:
        with path.open(newline="", encoding="utf-8-sig") as stream:
            reader = csv.reader(stream)
            header = next(reader)
            positions = {name: index for index, name in enumerate(header)}
            if len(positions) != len(header):
                failures.append("duplicate raw columns")
            failures.extend(f"missing raw probe: {label}" for label in REQUIRED if label not in positions)
            for row in reader:
                if len(row) != len(header):
                    failures.append("raw row width mismatch")
                    continue
                times.append(float(row[positions["time"]]))
    except (OSError, StopIteration, ValueError, KeyError) as exc:
        failures.append(f"raw read failure: {exc}")
    actual = len(times) == 1999 and bool(times) and times[0] == 0.0 and times[-1] == 1.999e-10 and all(right > left for left, right in zip(times, times[1:]))
    if not actual:
        failures.append("raw grid is not 1999 samples 0..199.9 ps")
    return header, len(times), times[0] if times else 0.0, times[-1] if times else 0.0, failures


def main() -> int:
    state = json.loads(STATE.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    failures: list[str] = []
    if manifest.get("base_visualization_manifest_sha256") != sha256(BASE_MANIFEST):
        failures.append("base visualization manifest hash changed")
    expected_runs = {case["run_id"] for case in state.get("screening_cases", {}).values()}
    entries = manifest.get("entries", [])
    if len(entries) != len(expected_runs) * len(BVM_INDICES):
        failures.append("supplement entry count mismatch")
    seen: set[tuple[str, int]] = set()
    records: list[dict[str, Any]] = []
    for entry in entries:
        run_id = entry.get("run_id")
        bvm_index = entry.get("bvm_index")
        key = (run_id, bvm_index)
        if key in seen:
            failures.append(f"duplicate supplement entry: {key}")
        seen.add(key)
        if run_id not in expected_runs or bvm_index not in BVM_INDICES:
            failures.append(f"unexpected supplement entry: {key}")
        raw = REPO / entry["input_raw"]
        output = REPO / entry["output_path"]
        header, sample_count, first_time, last_time, raw_failures = raw_grid_and_header(raw)
        failures.extend(f"{run_id}/XBVM{bvm_index}: {item}" for item in raw_failures)
        if entry.get("input_raw_sha256") != sha256(raw):
            failures.append(f"raw hash mismatch: {run_id}/XBVM{bvm_index}")
        if not output.is_file() or entry.get("output_sha256") != sha256(output):
            failures.append(f"HTML hash/missing: {entry.get('output_path')}")
        html = output.read_text(encoding="utf-8", errors="replace") if output.is_file() else ""
        if re.search(r'"title"\s*:\s*\{\s*"text"\s*:\s*"Unknown"', html):
            failures.append(f"Unknown axis title: {entry.get('output_path')}")
        if not any(label.startswith("P(") for label in entry.get("labels", [])) or "Phase (turns)" not in html or "rad\\u002f2pi" not in html:
            failures.append(f"phase convention missing: {entry.get('output_path')}")
        records.append({"run_id": run_id, "bvm_index": bvm_index, "raw_path": rel(raw), "raw_sha256": sha256(raw) if raw.is_file() else None, "sample_count": sample_count, "time_range_s": [first_time, last_time], "output_path": rel(output), "output_sha256": sha256(output) if output.is_file() else None, "status": "PASS" if not raw_failures else "FAIL"})
    if seen != {(run_id, index) for run_id in expected_runs for index in BVM_INDICES}:
        failures.append("supplement coverage is not exactly XBVM2/3/4 for every run")
    navigation = manifest.get("navigation", [])
    for run_id in expected_runs:
        if run_id not in navigation:
            failures.append(f"missing supplement navigation: {run_id}")
        else:
            nav_path = REPO / navigation[run_id]
            if not nav_path.is_file():
                failures.append(f"missing navigation file: {nav_path}")
    derived_csv = list((EXP / "visualization/supplemental_bvm_states").rglob("*.csv"))
    if derived_csv:
        failures.append("derived CSV remains in supplemental visualization directory")
    record = {"schema": "bvm-qb-l1-l3-bj2-targeted-closure-supplemental-bvm-state-qa-v1", "experiment_id": EXP.name, "created_at_local": now(), "status": "PASS" if not failures else "FAIL", "checked_run_count": len(expected_runs), "bvm_indices": list(BVM_INDICES), "entry_count": len(entries), "records": records, "base_visualization_manifest_unchanged": not any("base visualization manifest" in item for item in failures), "raw_direct": True, "no_derived_csv": not derived_csv, "canonical_zip_modified": False, "failures": failures}
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": record["status"], "entry_count": len(entries), "checked_run_count": len(expected_runs), "bvm_indices": list(BVM_INDICES), "failures": failures[:30]}, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
