#!/usr/bin/env python3
"""Independent Decimal reconstruction and key-metric check.

This checker deliberately uses only the standard library and does not import
the production analyzer or bvmtools measurement functions.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import re
from decimal import Decimal
from pathlib import Path


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
OLD = REPO / "test/exploration/bvmsim-jm2-read-count-passive-replay-v1-20260907"
HEAD = "2a3e3caeaefd511aa6e555dff18e596bd968f3a2"
CONTROL_PATHS = {
    "N3_REPLAY": OLD / "runs/n3_replay/raw.csv",
    "N4_REPLAY": OLD / "runs/n4_replay/raw.csv",
}
RUNS = (
    "DELTA4_DELAY_3PS",
    "DELTA4_DELAY_6PS",
    "DELTA4_GAIN_1P25",
    "DELTA4_GAIN_1P50",
)
SNAPSHOT_PATHS = {
    "N3_PASSIVE": OLD / "data/n3_passive_JSL8_source.csv",
    "N4_PASSIVE": OLD / "data/n4_passive_JSL8_source.csv",
}
EXPECTED_HASHES = {
    "N3_PASSIVE": "93e41cf604bd373ad63f8fce2eadfd88d735b481fffc2e5e6434b0ff4ce7b586",
    "N4_PASSIVE": "f917c119fb9920a167188c45bd31f93895720f71e5ebe35f753181307860e2e6",
    "N3_REPLAY": "555e850fde892da7fd2328d2ac34081b45459ab48e8181a8e95d7cd531e7c225",
    "N4_REPLAY": "5cac782aa9dfa5d467d81e2988e772f1978abfe8313d7896089d5dfa84517b28",
}
PAIR_RE = re.compile(
    r"([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)[pP]\s+"
    r"([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)"
)
PHI0 = Decimal("2.067833848e-15")
INTERNAL_WINDOW_PS = (Decimal("118.0"), Decimal("140.0"))
TOL_METRIC = 1.0e-9


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def write_once(path: Path, content: str) -> None:
    if path.exists():
        if path.read_text(encoding="utf-8") != content:
            raise RuntimeError(f"refusing to overwrite existing artifact: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def snapshot(path: Path) -> list[tuple[Decimal, Decimal]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return [
            (Decimal(row["time_ps"]), Decimal(row["I_REPLAY_A"]))
            if "I_REPLAY_A" in row
            else (Decimal(row["time_s"]) * Decimal("1e12"), Decimal(row["current_A"]))
            for row in csv.DictReader(handle)
        ]


def source(path: Path) -> list[tuple[Decimal, Decimal]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return [
            (Decimal(row["time_s"]) * Decimal("1e12"), Decimal(row["current_A"]))
            for row in csv.DictReader(handle)
        ]


def transformed_source(path: Path) -> list[tuple[Decimal, Decimal, Decimal, Decimal]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return [
            (
                Decimal(row["time_ps"]),
                Decimal(row["I_N3_BACKGROUND_A"]),
                Decimal(row["delta_I4_COMPONENT_A"]),
                Decimal(row["I_REPLAY_A"]),
            )
            for row in csv.DictReader(handle)
        ]


def deck_pairs(path: Path) -> list[tuple[Decimal, Decimal]]:
    text = path.read_text(encoding="utf-8")
    start = text.lower().index("pwl(") + 4
    end = text.index(")", start)
    return [(Decimal(time), Decimal(value)) for time, value in PAIR_RE.findall(text[start:end])]


def raw(path: Path) -> tuple[list[Decimal], dict[str, list[Decimal]]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames or []
        rows = list(reader)
    times = [Decimal(row["time"]) * Decimal("1e12") for row in rows]
    columns = {
        label: [Decimal(row[label]) for row in rows]
        for label in fields[1:]
    }
    return times, columns


def unwrap(values: list[Decimal]) -> list[float]:
    output = [float(values[0])]
    previous = float(values[0])
    tau = 2.0 * math.pi
    for value in values[1:]:
        current = float(value)
        delta = current - previous
        while delta > math.pi:
            delta -= tau
        while delta < -math.pi:
            delta += tau
        output.append(output[-1] + delta)
        previous = current
    return output


def window_indices(times: list[Decimal], window: tuple[Decimal, Decimal]) -> list[int]:
    return [i for i, value in enumerate(times) if window[0] <= value < window[1]]


def phase_area(
    times: list[Decimal],
    columns: dict[str, list[Decimal]],
    phase_label: str,
    voltage_label: str,
) -> dict[str, float]:
    indices = window_indices(times, INTERNAL_WINDOW_PS)
    phase_values = unwrap([columns[phase_label][i] for i in indices])
    voltage_values = [columns[voltage_label][i] for i in indices]
    selected_times = [times[i] * Decimal("1e-12") for i in indices]
    area = sum(
        Decimal("0.5")
        * (voltage_values[i] + voltage_values[i + 1])
        * (selected_times[i + 1] - selected_times[i])
        for i in range(len(indices) - 1)
    ) / PHI0
    phase_turns = (Decimal(str(phase_values[-1])) - Decimal(str(phase_values[0]))) / (Decimal("2") * Decimal(str(math.pi)))
    return {
        "phase_delta_turns": float(phase_turns),
        "voltage_area_over_phi0": float(area),
    }


def approx_equal(left: float, right: float) -> bool:
    return abs(left - right) <= TOL_METRIC * max(1.0, abs(left), abs(right))


def main() -> int:
    failures: list[str] = []
    registry = json.loads((EXP / "analysis/transformation_registry.json").read_text(encoding="utf-8"))
    metrics = json.loads((EXP / "analysis/metrics.json").read_text(encoding="utf-8"))
    if registry.get("head") != HEAD:
        failures.append("registry HEAD mismatch")
    if list(registry.get("authorized_runs", {})) != list(RUNS):
        failures.append("registry run list mismatch")

    n3 = source(SNAPSHOT_PATHS["N3_PASSIVE"])
    n4 = source(SNAPSHOT_PATHS["N4_PASSIVE"])
    if [time for time, _ in n3] != [time for time, _ in n4]:
        failures.append("N3/N4 source grids differ")
    delta = {time: right - left for (time, left), (_, right) in zip(n3, n4)}
    residuals = {time: left + delta[time] - right for (time, left), (_, right) in zip(n3, n4)}
    if any(value != 0 for value in residuals.values()):
        failures.append("source reconstruction has nonzero Decimal residual")
    if max(abs(value) for value in residuals.values()) > Decimal("1e-21"):
        failures.append("source reconstruction exceeds tolerance")

    transform_checks: dict[str, object] = {}
    for run_id in RUNS:
        data_path = EXP / "data" / f"{run_id}_source.csv"
        deck_path = EXP / "runs" / run_id / "deck.cir"
        data_rows = transformed_source(data_path)
        pairs = deck_pairs(deck_path)
        source_pairs = [(row[0], row[3]) for row in data_rows]
        if source_pairs != pairs:
            failures.append(f"{run_id}: deck PWL differs from derived source CSV")
        transform = registry["authorized_runs"][run_id]
        component_mismatches = []
        formula = str(registry["authorized_runs"][run_id]["formula"])
        delay_match = re.search(r"delta_I4\(t - ([0-9.]+) ps\)", formula)
        gain_match = re.search(r"\+ ([0-9.]+) \* delta_I4\(t\)", formula)
        for time_ps, background, component, replay_value in data_rows:
            expected_background = n3[-1][1] if time_ps > n3[-1][0] else dict(n3)[time_ps]
            if background != expected_background:
                component_mismatches.append((str(time_ps), "background"))
            if transform["kind"] == "exact_timestamp_shift":
                if delay_match is None:
                    component_mismatches.append((str(time_ps), "missing_delay_in_formula"))
                    argument = time_ps
                else:
                    argument = time_ps - Decimal(delay_match.group(1))
                expected_component = delta.get(argument, Decimal("0"))
            else:
                if gain_match is None:
                    component_mismatches.append((str(time_ps), "missing_gain_in_formula"))
                    gain = Decimal("0")
                else:
                    gain = Decimal(gain_match.group(1))
                expected_component = delta.get(time_ps, Decimal("0")) * gain
            if component != expected_component:
                component_mismatches.append((str(time_ps), "component"))
            if replay_value != background + component:
                component_mismatches.append((str(time_ps), "sum"))
        if component_mismatches:
            failures.append(f"{run_id}: transformation mismatches {component_mismatches[:3]}")
        transform_checks[run_id] = {
            "source_sha256": sha256(data_path),
            "deck_sha256": sha256(deck_path),
            "sample_count": len(data_rows),
            "deck_pair_count": len(pairs),
            "exact_formula_check": not component_mismatches and source_pairs == pairs,
        }

    raw_hashes = {}
    for case, path in CONTROL_PATHS.items():
        actual = sha256(path)
        raw_hashes[case] = {"path": str(path.relative_to(REPO)), "sha256": actual, "expected": EXPECTED_HASHES[case], "unchanged": actual == EXPECTED_HASHES[case]}
        if actual != EXPECTED_HASHES[case]:
            failures.append(f"{case}: control hash changed")
    for run_id in RUNS:
        path = EXP / "runs" / run_id / "raw.csv"
        actual = sha256(path)
        execution_hash = json.loads((EXP / "runs" / run_id / "metadata.json").read_text(encoding="utf-8"))["artifacts"]["raw"]["sha256"]
        raw_hashes[run_id] = {"path": str(path.relative_to(REPO)), "sha256": actual, "hash_at_execution": execution_hash, "unchanged": actual == execution_hash}
        if actual != execution_hash:
            failures.append(f"{run_id}: raw hash changed after execution")

    metric_reproduction: dict[str, object] = {}
    for case in ("N3_REPLAY", "N4_REPLAY") + RUNS:
        path = CONTROL_PATHS[case] if case in CONTROL_PATHS else EXP / "runs" / case / "raw.csv"
        times, columns = raw(path)
        facts = {}
        for name, pair in {
            "BJ1": ("P(BJ1|XBQ1)", "V(BJ1|XBQ1)"),
            "BJ2": ("P(BJ2|XBQ1)", "V(BJ2|XBQ1)"),
            "JTL1_B01": ("P(B01|XJTL1_1)", "V(B01|XJTL1_1)"),
            "JTL6_B01": ("P(B01|XJTL1_6)", "V(B01|XJTL1_6)"),
        }.items():
            actual = phase_area(times, columns, *pair)
            expected = metrics["cases"][case]["phase_area"]["facts"][name]
            checks = {
                field: approx_equal(actual[field], float(expected[field]))
                for field in ("phase_delta_turns", "voltage_area_over_phi0")
            }
            if not all(checks.values()):
                failures.append(f"{case}/{name}: independent phase-area mismatch")
            facts[name] = {"actual": actual, "expected": {field: expected[field] for field in checks}, "checks": checks}
        metric_reproduction[case] = facts

    record = {
        "schema": "jm2-delta4-independent-mechanical-check-v1",
        "experiment_id": EXP.name,
        "head": HEAD,
        "status": "PASS" if not failures else "FAIL",
        "source_reconstruction": {
            "same_actual_decimal_grid": [time for time, _ in n3] == [time for time, _ in n4],
            "sample_count": len(n3),
            "max_abs_residual_A": str(max(abs(value) for value in residuals.values())),
            "tolerance_A": "1e-21",
            "nonzero_residual_count": sum(value != 0 for value in residuals.values()),
        },
        "transform_checks": transform_checks,
        "raw_hashes": raw_hashes,
        "metric_reproduction": metric_reproduction,
        "method": "independent standard-library CSV/Decimal parser, exact lookup, and actual-grid trapezoid/unwrap arithmetic",
        "failures": failures,
    }
    write_once(EXP / "analysis/independent_check.json", json.dumps(record, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"status": record["status"], "failures": failures, "run_count": len(RUNS)}, ensure_ascii=False))
    return 0 if record["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
