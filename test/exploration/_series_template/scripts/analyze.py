#!/usr/bin/env python3
"""Read raw CSV files for one attempt and write mechanical summaries only."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import platform
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def attempt_dir(series: Path, value: str) -> Path:
    if value == "latest":
        candidates = sorted(path for path in (series / "runs").glob("A*") if path.is_dir())
        if not candidates:
            raise RuntimeError(f"no attempts found under {series / 'runs'}")
        return candidates[-1]
    path = series / "runs" / value
    if not path.is_dir():
        raise RuntimeError(f"attempt does not exist: {path}")
    return path


def signal_kind(name: str) -> tuple[str, str]:
    if name.startswith("P("):
        return "phase", "radians"
    if name.startswith("V("):
        return "voltage", "V"
    if name.startswith("I("):
        return "current", "A"
    return "other", "raw"


def parse_time(value: str, header: str) -> float:
    number = float(value)
    return number * 1.0e12 if header in {"time_s", "time"} and abs(number) < 1.0 else number


def read_raw(path: Path) -> tuple[list[str], list[list[str]]]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        rows = list(csv.reader(stream))
    if not rows or not rows[0]:
        raise RuntimeError(f"empty raw CSV: {path}")
    return rows[0], rows[1:]


def summarize_case(case_dir: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    raw = case_dir / "raw.csv"
    if not raw.is_file():
        raise RuntimeError(f"missing raw.csv: {raw}")
    headers, rows = read_raw(raw)
    duplicates = sorted(name for name, count in Counter(headers).items() if count > 1)
    time_index = next((index for index, name in enumerate(headers) if name in {"time", "time_s", "time_ps"}), 0)
    time_header = headers[time_index]
    times = []
    for row in rows:
        if len(row) <= time_index:
            continue
        times.append(parse_time(row[time_index], time_header))
    numeric: list[dict[str, Any]] = []
    for index, name in enumerate(headers):
        if index == time_index:
            continue
        values: list[float] = []
        for row in rows:
            if len(row) <= index or row[index] == "":
                continue
            try:
                values.append(float(row[index]))
            except ValueError:
                continue
        kind, unit = signal_kind(name)
        if not values:
            numeric.append({"signal": name, "kind": kind, "unit": unit, "status": "NON_NUMERIC_OR_EMPTY", "sample_count": 0})
            continue
        mean = sum(values) / len(values)
        numeric.append({"signal": name, "kind": kind, "unit": unit, "status": "DERIVED", "sample_count": len(values), "minimum": min(values), "maximum": max(values), "p2p": max(values) - min(values), "mean": mean, "rms": math.sqrt(sum(value * value for value in values) / len(values))})
    grid = {"sample_count": len(times), "time_header": time_header, "time_start_ps": times[0] if times else None, "time_end_ps": times[-1] if times else None, "strictly_increasing": all(right > left for left, right in zip(times, times[1:])), "duplicate_headers": duplicates}
    result = {"case": case_dir.name, "raw_path": str(raw), "raw_sha256": sha256(raw), "raw_bytes": raw.stat().st_size, "headers": headers, "grid": grid, "signals": numeric, "phase_semantics": "P(...) raw radians; any turns must be explicitly rad/(2*pi) navigation only", "scientific_interpretation_performed": False}
    return result, [{"case": case_dir.name, **item} for item in numeric]


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze existing raw CSV files for one attempt")
    parser.add_argument("--series-dir", required=True)
    parser.add_argument("attempt")
    args = parser.parse_args()
    series = Path(args.series_dir).resolve()
    attempt = attempt_dir(series, args.attempt)
    cases_root = attempt / "cases"
    case_dirs = sorted(path for path in cases_root.iterdir() if path.is_dir())
    if not case_dirs:
        raise RuntimeError(f"no case directories under {cases_root}")
    before = {str(path): sha256(path) for case in case_dirs for path in [case / "raw.csv"] if path.is_file()}
    summaries: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    for case in case_dirs:
        summary, csv_rows = summarize_case(case)
        summaries.append(summary)
        rows.extend(csv_rows)
    after = {str(path): sha256(path) for case in case_dirs for path in [case / "raw.csv"] if path.is_file()}
    if before != after:
        raise RuntimeError("raw CSV changed during analysis")
    output = attempt / "analysis"
    output.mkdir(parents=True, exist_ok=True)
    summary = {"schema": "josim-experiment-series-mechanical-summary-v1", "series": series.name, "attempt": attempt.name, "generated_at": now(), "python": platform.python_version(), "cases": summaries, "raw_hashes_before": before, "raw_hashes_after": after, "raw_immutable": before == after, "scientific_interpretation_performed": False, "scientific_verdict": "NOT_ASSIGNED_SCIENTIFIC_REVIEW_REQUIRED"}
    write_json(output / "summary.json", summary)
    with (output / "summary.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=["case", "signal", "kind", "unit", "status", "sample_count", "minimum", "maximum", "p2p", "mean", "rms"])
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in writer.fieldnames})
    write_json(output / "analysis_metadata.json", {"schema": "josim-experiment-series-analysis-metadata-v1", "attempt": attempt.name, "analyzer": str(Path(__file__)), "analyzer_sha256": sha256(Path(__file__)), "summary_sha256": sha256(output / "summary.json"), "raw_hashes_unchanged": before == after, "scientific_interpretation_performed": False})
    print(json.dumps({"status": "PASS", "attempt": attempt.name, "summary": str(output / "summary.json"), "case_count": len(summaries), "raw_hashes_unchanged": before == after}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
