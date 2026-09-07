#!/usr/bin/env python3
"""Independent standard-library cross-check for the aligned replay analysis.

This checker deliberately does not import the production analysis helpers.  It
re-reads the immutable CSV tokens, uses Decimal arithmetic on their stored
time values, and compares the three N4 source windows with the versioned
analysis artifact.
"""

from __future__ import annotations

import csv
import hashlib
import json
from decimal import Decimal
from pathlib import Path


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
N1 = REPO / "test/exploration/bvmsim-jm2-passive-capture-replay-v1-20260907/runs/replay_array/raw.csv"
N3 = EXP / "runs/n3_replay/raw.csv"
N4 = EXP / "runs/n4_replay/raw.csv"
ANALYSIS = EXP / "analysis/n3_n4_internal_time_aligned_analysis_v3.json"
QA = EXP / "analysis/internal_time_aligned_v2_qa.json"
EXPECTED_HASHES = {
    "N1_REPLAY": "11bce2601a6f3b63dff33a32771bb7c406e0b6e64236facabbfd25676220151e",
    "N3_REPLAY": "555e850fde892da7fd2328d2ac34081b45459ab48e8181a8e95d7cd531e7c225",
    "N4_REPLAY": "5cac782aa9dfa5d467d81e2988e772f1978abfe8313d7896089d5dfa84517b28",
}
PATHS = {"N1_REPLAY": N1, "N3_REPLAY": N3, "N4_REPLAY": N4}
TAU = Decimal("6.2831853071795864769252867665590057683943387987502")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def read_raw(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or reader.fieldnames.count("time") != 1:
            raise RuntimeError(f"invalid time header: {path}")
        headers = list(reader.fieldnames)
        rows = list(reader)
    times = [Decimal(row["time"]) for row in rows]
    if len(times) != 1999 or any(right <= left for left, right in zip(times, times[1:])):
        raise RuntimeError(f"invalid stored time grid: {path}")
    for row in rows:
        for label in headers:
            value = Decimal(row[label])
            if not value.is_finite():
                raise RuntimeError(f"non-finite raw value: {path} {label}")
    return headers, rows


def selected(rows: list[dict[str, str]], start_ps: Decimal, end_ps: Decimal) -> list[dict[str, str]]:
    output = [
        row
        for row in rows
        if start_ps <= Decimal(row["time"]) * Decimal("1e12") < end_ps
    ]
    if len(output) < 2:
        raise RuntimeError(f"too few samples in [{start_ps},{end_ps}) ps")
    return output


def integral(rows: list[dict[str, str]], label: str, transform=lambda value: value) -> Decimal:
    total = Decimal("0")
    for left, right in zip(rows, rows[1:]):
        left_value = transform(Decimal(left[label]))
        right_value = transform(Decimal(right[label]))
        dt = Decimal(right["time"]) - Decimal(left["time"])
        total += (left_value + right_value) * dt / Decimal("2")
    return total


def source_metrics(rows: list[dict[str, str]], start_ps: Decimal, end_ps: Decimal) -> dict[str, object]:
    chosen = selected(rows, start_ps, end_ps)
    values = [Decimal(row["I(I_REPLAY)"]) for row in chosen]
    maximum = max(values)
    minimum = min(values)
    maximum_abs = max(abs(value) for value in values)
    above = [row for row in chosen if Decimal(row["I(I_REPLAY)"]) > Decimal("5e-6")]
    return {
        "sample_count": len(chosen),
        "positive_peak": float(maximum * Decimal("1e6")),
        "negative_peak": float(minimum * Decimal("1e6")),
        "max_abs": float(maximum_abs * Decimal("1e6")),
        "rms": float((sum(value * value for value in values) / Decimal(len(values))).sqrt() * Decimal("1e6")),
        "signed_area": float(integral(chosen, "I(I_REPLAY)") * Decimal("1e18")),
        "positive_area": float(integral(chosen, "I(I_REPLAY)", lambda value: max(value, Decimal("0"))) * Decimal("1e18")),
        "negative_area": float(integral(chosen, "I(I_REPLAY)", lambda value: min(value, Decimal("0"))) * Decimal("1e18")),
        "significant_positive_sample_count": len(above),
        "significant_positive_first_ps": float(Decimal(above[0]["time"]) * Decimal("1e12")) if above else None,
        "significant_positive_last_ps": float(Decimal(above[-1]["time"]) * Decimal("1e12")) if above else None,
        "significant_positive_duration_span_ps": float(
            (Decimal(above[-1]["time"]) - Decimal(above[0]["time"])) * Decimal("1e12")
        ) if above else 0.0,
        "actual_time_grid_for_integration": True,
    }


def independent_unwrap(values: list[Decimal]) -> list[Decimal]:
    result = [values[0]]
    previous = values[0]
    half_tau = TAU / Decimal("2")
    for current in values[1:]:
        delta = current - previous
        while delta > half_tau:
            delta -= TAU
        while delta < -half_tau:
            delta += TAU
        result.append(result[-1] + delta)
        previous = current
    return result


def phase_delta(rows: list[dict[str, str]], label: str, start_ps: Decimal, end_ps: Decimal) -> float:
    chosen = selected(rows, start_ps, end_ps)
    values = independent_unwrap([Decimal(row[label]) for row in chosen])
    return float(values[-1] - values[0])


def compare(actual: object, expected: object, path: str, differences: list[dict[str, object]]) -> None:
    if actual is None or expected is None:
        passed = actual == expected
        difference = None
    else:
        actual_float = float(actual)
        expected_float = float(expected)
        difference = actual_float - expected_float
        passed = abs(difference) <= max(1.0e-9, abs(expected_float) * 1.0e-9)
    differences.append(
        {
            "path": path,
            "independent": actual,
            "analysis": expected,
            "difference": difference,
            "pass": passed,
        }
    )


def write_once(path: Path, content: str) -> None:
    if path.exists():
        if path.read_text(encoding="utf-8") == content:
            return
        raise RuntimeError(f"refusing to overwrite existing artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main() -> int:
    failures: list[str] = []
    hashes_before = {name: sha256(path) for name, path in PATHS.items()}
    headers: dict[str, list[str]] = {}
    rows: dict[str, list[dict[str, str]]] = {}
    for name, path in PATHS.items():
        headers[name], rows[name] = read_raw(path)
        if hashes_before[name] != EXPECTED_HASHES[name]:
            failures.append(f"{name}: unexpected raw hash")
    if [Decimal(row["time"]) for row in rows["N3_REPLAY"]] != [Decimal(row["time"]) for row in rows["N4_REPLAY"]]:
        failures.append("N3/N4 stored time grids differ")

    analysis = json.loads(ANALYSIS.read_text(encoding="utf-8"))
    independent_windows: dict[str, object] = {}
    differences: list[dict[str, object]] = []
    for key, start in (("after_t3_BJ1", Decimal("120.0")), ("after_t3_BJ2", Decimal("121.4")), ("after_t3_QBOUT", Decimal("121.9"))):
        actual = source_metrics(rows["N4_REPLAY"], start, Decimal("135.0"))
        expected = analysis["source_after_internal_references"]["N4_REPLAY"][key]
        independent_windows[key] = actual
        for field in (
            "sample_count",
            "positive_peak",
            "negative_peak",
            "max_abs",
            "rms",
            "signed_area",
            "positive_area",
            "negative_area",
            "significant_positive_sample_count",
            "significant_positive_duration_span_ps",
        ):
            compare(actual[field], expected[field], f"source_after_internal_references.N4_REPLAY.{key}.{field}", differences)

    phase_checks: dict[str, object] = {}
    for label in ("P(BJS|XBQ1)", "P(BJ1|XBQ1)", "P(BJ2|XBQ1)"):
        actual = phase_delta(rows["N4_REPLAY"], label, Decimal("120.0"), Decimal("135.0"))
        expected = analysis["fourth_attempt_candidate_inventory"]["candidates"]["phase_activity"][label]["unwrapped_delta_rad"]
        compare(actual, expected, f"fourth_attempt_candidate_inventory.candidates.phase_activity.{label}.unwrapped_delta_rad", differences)
        phase_checks[label] = {"independent_unwrapped_delta_rad": actual, "analysis": expected}

    hashes_after = {name: sha256(path) for name, path in PATHS.items()}
    if hashes_before != hashes_after:
        failures.append("raw hash changed during independent cross-check")
    qa = json.loads(QA.read_text(encoding="utf-8"))
    if qa.get("raw_unchanged") is not True or qa.get("status") != "PASS":
        failures.append("production raw QA is not PASS/unchanged")
    failures.extend(item["path"] for item in differences if not item["pass"])
    record = {
        "schema": "jm2-n3-n4-internal-time-aligned-independent-check-v1",
        "status": "PASS" if not failures else "FAIL",
        "method": "independent csv.DictReader + Decimal arithmetic; no production analysis helper imported",
        "raw_hashes_before": hashes_before,
        "raw_hashes_after": hashes_after,
        "raw_unchanged": hashes_before == hashes_after,
        "source_windows": independent_windows,
        "phase_checks": phase_checks,
        "comparisons": differences,
        "failures": failures,
        "disclaimer": "cross-check validates arithmetic/provenance only; it does not certify switching, SFQ count, recovery mechanism, or root cause",
    }
    output = EXP / "analysis/internal_time_aligned_v2_independent_check.json"
    write_once(output, json.dumps(record, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"status": record["status"], "comparison_count": len(differences), "raw_unchanged": record["raw_unchanged"], "failures": failures}, ensure_ascii=False))
    return 0 if record["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
