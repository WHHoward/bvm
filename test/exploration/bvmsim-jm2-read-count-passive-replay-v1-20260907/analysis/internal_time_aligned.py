#!/usr/bin/env python3
"""Build the versioned, internal-time-aligned N3/N4 replay evidence pack.

This is a read-only analysis.  It reads the already sealed N1/N3/N4 replay
CSVs, preserves their raw SI values, and writes only new derived evidence.
It never invokes JoSIM and never edits a deck, a parameter, a timing value, or
an existing raw artifact.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import subprocess
import sys
from bisect import bisect_left
from collections import OrderedDict
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from typing import Iterable, Sequence


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
N1_REPLAY = REPO / "test/exploration/bvmsim-jm2-passive-capture-replay-v1-20260907/runs/replay_array/raw.csv"
N3_REPLAY = EXP / "runs/n3_replay/raw.csv"
N4_REPLAY = EXP / "runs/n4_replay/raw.csv"

sys.path.insert(0, str(REPO / "scripts"))
from bvmtools.phase import continuous_unwrap  # noqa: E402
from bvmtools.raw import RawTrace, read_csv  # noqa: E402
from bvmtools.waveform import trapezoid_integral  # noqa: E402


TAU = 2.0 * math.pi
WINDOW_START_PS = 110.0
WINDOW_END_PS = 200.0
INTERNAL_SEARCH_PS = (120.0, 135.0)
INTERNAL_CONTEXT_PS = (118.0, 140.0)
SOURCE_THRESHOLD_A = 5.0e-6
WINDOW_BOUNDARY_EPS_PS = 1.0e-9

RAW_CASES: OrderedDict[str, Path] = OrderedDict(
    [
        ("N1_REPLAY", N1_REPLAY),
        ("N3_REPLAY", N3_REPLAY),
        ("N4_REPLAY", N4_REPLAY),
    ]
)

# These are descriptive raw-timing references.  They are not event counts,
# JJ switching labels, or SFQ labels.  In particular, the N4 R_TERM value is
# retained as a downstream arrival reference, not used as an internal t3.
RESPONSE_TIMES_PS: OrderedDict[str, OrderedDict[str, list[float]]] = OrderedDict(
    [
        (
            "N3_REPLAY",
            OrderedDict(
                [
                    ("BJ1", [113.4, 117.8, 122.3]),
                    ("BJ2", [115.2, 119.6, 125.4]),
                    ("QBOUT", [115.4, 119.7, 125.9]),
                    ("JTL1", [116.4, 120.8, 126.6]),
                    ("JTL6", [131.2, 136.8, 142.6]),
                    ("R_TERM", [132.8, 138.4, 144.2]),
                ]
            ),
        ),
        (
            "N4_REPLAY",
            OrderedDict(
                [
                    ("BJ1", [113.0, 116.1, 120.0]),
                    ("BJ2", [114.5, 118.3, 121.4]),
                    ("QBOUT", [114.7, 118.4, 121.9]),
                    ("JTL1", [115.8, 119.5, 123.3]),
                    ("JTL6", [130.5, 135.4, 140.1]),
                    ("R_TERM", [132.1, 137.0, 141.6]),
                ]
            ),
        ),
    ]
)

QB_FULL_LABELS = [
    "I(I_REPLAY)",
    "V(QBIN)",
    "I(LIN|XBQ1)",
    "V(LIN|XBQ1)",
    "P(BJS|XBQ1)",
    "V(BJS|XBQ1)",
    "I(BJS|XBQ1)",
    "I(L1|XBQ1)",
    "V(L1|XBQ1)",
    "P(BJ1|XBQ1)",
    "V(BJ1|XBQ1)",
    "I(BJ1|XBQ1)",
    "I(RJ1|XBQ1)",
    "V(RJ1|XBQ1)",
    "I(L2|XBQ1)",
    "V(L2|XBQ1)",
    "I(IB|XBQ1)",
    "P(BJ2|XBQ1)",
    "V(BJ2|XBQ1)",
    "I(BJ2|XBQ1)",
    "I(RJ2|XBQ1)",
    "V(RJ2|XBQ1)",
    "I(L3|XBQ1)",
    "V(L3|XBQ1)",
    "V(QBOUT)",
]

JTL_FULL_LABELS: list[str] = []
for _stage in range(1, 7):
    _handle = f"XJTL1_{_stage}"
    JTL_FULL_LABELS.extend(
        [
            f"P(B01|{_handle})",
            f"V(B01|{_handle})",
            f"I(B01|{_handle})",
            f"P(B02|{_handle})",
            f"V(B02|{_handle})",
            f"I(B02|{_handle})",
            f"V(JTL{_stage}_OUT)",
        ]
    )

JTL_ENDPOINT_LABELS = [
    label
    for stage in (1, 6)
    for label in (
        f"P(B01|XJTL1_{stage})",
        f"V(B01|XJTL1_{stage})",
        f"I(B01|XJTL1_{stage})",
        f"P(B02|XJTL1_{stage})",
        f"V(B02|XJTL1_{stage})",
        f"I(B02|XJTL1_{stage})",
        f"V(JTL{stage}_OUT)",
    )
]
DOWNSTREAM_REFERENCE_LABELS = JTL_ENDPOINT_LABELS + ["I(R_TERM)"]
ALL_REQUIRED_LABELS = QB_FULL_LABELS + JTL_FULL_LABELS + ["I(R_TERM)"]
PHASE_LABELS = [label for label in ALL_REQUIRED_LABELS if label.startswith("P(")]

EVENT_LOCAL_OFFSETS_PS = [-0.5, 0.0, 0.5, 1.0, 2.0, 3.0]
EVENT_ALIGNED_OFFSETS_PS = [round(-10.0 + 0.1 * index, 10) for index in range(351)]
DATA_DIR = EXP / "plots/deep_dive/internal_time_aligned_v2/data"
QA_OUTPUT = EXP / "analysis/internal_time_aligned_v2_qa.json"
MANIFEST_OUTPUT = EXP / "analysis/internal_time_aligned_v2_plot_manifest.json"
ANALYSIS_OUTPUT = EXP / "analysis/n3_n4_internal_time_aligned_analysis_v3.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(REPO).as_posix()


def write_once(path: Path, content: str) -> None:
    if path.exists():
        if path.read_text(encoding="utf-8") == content:
            return
        raise RuntimeError(f"refusing to overwrite existing artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def json_once(path: Path, value: object) -> None:
    write_once(path, json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def ps(time_s: float) -> float:
    return float(time_s) * 1.0e12


def seconds(time_ps: float) -> float:
    return float(time_ps) * 1.0e-12


def unit_for(label: str) -> str:
    if label.startswith("I("):
        return "A"
    if label.startswith("V("):
        return "V"
    if label.startswith("P("):
        return "rad"
    return "raw"


def display_unit_for(unit: str) -> str:
    return {"A": "uA", "V": "mV", "rad": "rad", "raw": "raw"}[unit]


def display_factor_for(unit: str) -> float:
    return {"A": 1.0e6, "V": 1.0e3, "rad": 1.0, "raw": 1.0}[unit]


def area_factor_for(unit: str) -> float:
    return {"A": 1.0e18, "V": 1.0e15, "rad": 1.0, "raw": 1.0}[unit]


def window_indices(trace: RawTrace, start_ps: float, end_ps: float) -> list[int]:
    return [
        index
        for index, value in enumerate(trace.time)
        if float(start_ps) - WINDOW_BOUNDARY_EPS_PS <= ps(value) < float(end_ps) - WINDOW_BOUNDARY_EPS_PS
    ]


def exact_time_index(trace: RawTrace, target_ps: float) -> tuple[int, float]:
    target_s = seconds(target_ps)
    insertion = bisect_left(trace.time, target_s)
    candidate_indices = [index for index in (insertion - 1, insertion) if 0 <= index < trace.sample_count]
    index = min(candidate_indices, key=lambda item: abs(ps(trace.time[item]) - target_ps))
    error = abs(ps(trace.time[index]) - target_ps)
    if error > 1.0e-6:
        raise RuntimeError(f"target {target_ps} ps is not on stored grid for {trace.path}: error={error}")
    return index, error


def raw_grid_record(trace: RawTrace) -> dict[str, object]:
    dt_ps = [ps(trace.time[index + 1] - trace.time[index]) for index in range(trace.sample_count - 1)]
    median_dt = sorted(dt_ps)[len(dt_ps) // 2]
    gaps = [
        {
            "from_ps": ps(trace.time[index]),
            "to_ps": ps(trace.time[index + 1]),
            "dt_ps": dt_ps[index],
        }
        for index in range(len(dt_ps))
        if dt_ps[index] > median_dt * 1.5
    ]
    return {
        "sample_count": trace.sample_count,
        "time_start_ps": ps(trace.time[0]),
        "time_end_ps": ps(trace.time[-1]),
        "dt_min_ps": min(dt_ps),
        "dt_max_ps": max(dt_ps),
        "nominal_median_dt_ps": median_dt,
        "uniform_time_grid": all(value == dt_ps[0] for value in dt_ps),
        "strictly_increasing": all(trace.time[i + 1] > trace.time[i] for i in range(trace.sample_count - 1)),
        "large_gap_records": gaps,
        "analysis_windows": {
            "FINAL_READ_RESPONSE": {
                "window_ps": [WINDOW_START_PS, WINDOW_END_PS],
                "sample_count": len(window_indices(trace, WINDOW_START_PS, WINDOW_END_PS)),
                "actual_time_values_used_for_integration": True,
            },
            "INTERNAL_TIME_ALIGNED": {
                "window_ps": list(INTERNAL_SEARCH_PS),
                "sample_count": len(window_indices(trace, *INTERNAL_SEARCH_PS)),
                "actual_time_values_used_for_integration": True,
            },
        },
    }


def validate_trace(trace: RawTrace) -> None:
    missing = [label for label in ALL_REQUIRED_LABELS if label not in trace.headers]
    if missing:
        raise RuntimeError(f"{trace.path}: missing required replay headers: {missing}")
    if trace.duplicate_columns:
        raise RuntimeError(f"{trace.path}: duplicate columns require explicit occurrence selection: {trace.duplicate_columns}")


def sign_change_count(values: Sequence[float]) -> int:
    previous = 0
    count = 0
    for value in values:
        sign = 1 if float(value) > 0.0 else -1 if float(value) < 0.0 else 0
        if sign == 0:
            continue
        if previous and sign != previous:
            count += 1
        previous = sign
    return count


def local_abs_peaks(
    trace: RawTrace,
    label: str,
    start_ps: float,
    end_ps: float,
    threshold: float,
    *,
    positive_only: bool = False,
    merge_ps: float = 0.0,
) -> list[dict[str, float]]:
    values = trace.column(label)
    indices = window_indices(trace, start_ps, end_ps)
    candidates: list[dict[str, float]] = []
    for index in indices:
        if index <= 0 or index >= trace.sample_count - 1:
            continue
        value = float(values[index])
        score = value if positive_only else abs(value)
        if score <= threshold:
            continue
        previous = float(values[index - 1]) if positive_only else abs(float(values[index - 1]))
        following = float(values[index + 1]) if positive_only else abs(float(values[index + 1]))
        if score >= previous and score > following:
            candidates.append(
                {
                    "time_ps": ps(trace.time[index]),
                    "value_raw": value,
                    "score_raw": score,
                }
            )
    merged: list[dict[str, float]] = []
    for candidate in candidates:
        if not merged or candidate["time_ps"] - merged[-1]["time_ps"] > merge_ps:
            merged.append(candidate)
        elif candidate["score_raw"] > merged[-1]["score_raw"]:
            merged[-1] = candidate
    return merged


def threshold_clusters(
    trace: RawTrace,
    label: str,
    start_ps: float,
    end_ps: float,
    threshold: float,
) -> list[dict[str, object]]:
    indices = [index for index in window_indices(trace, start_ps, end_ps) if float(trace.column(label)[index]) > threshold]
    if not indices:
        return []
    clusters: list[list[int]] = []
    for index in indices:
        if not clusters or index != clusters[-1][-1] + 1:
            clusters.append([index])
        else:
            clusters[-1].append(index)
    factor = display_factor_for(unit_for(label))
    output: list[dict[str, object]] = []
    for cluster in clusters:
        values = [float(trace.column(label)[index]) for index in cluster]
        covered_ps = sum(
            ps(trace.time[left + 1] - trace.time[left])
            for left, right in zip(cluster, cluster[1:])
            if right == left + 1
        )
        peak_index = max(cluster, key=lambda index: float(trace.column(label)[index]))
        output.append(
            {
                "first_sample_ps": ps(trace.time[cluster[0]]),
                "last_sample_ps": ps(trace.time[cluster[-1]]),
                "span_ps": ps(trace.time[cluster[-1]] - trace.time[cluster[0]]),
                "covered_interval_duration_ps": covered_ps,
                "sample_count": len(cluster),
                "peak_time_ps": ps(trace.time[peak_index]),
                "peak_value": float(trace.column(label)[peak_index]) * factor,
                "display_unit": display_unit_for(unit_for(label)),
                "meaning": "threshold activity cluster; not an event count",
            }
        )
    return output


def waveform_stats(
    trace: RawTrace,
    label: str,
    start_ps: float,
    end_ps: float,
    *,
    threshold: float | None = None,
    include_structure: bool = False,
) -> dict[str, object]:
    indices = window_indices(trace, start_ps, end_ps)
    if len(indices) < 2:
        raise RuntimeError(f"fewer than two samples for {label} in [{start_ps},{end_ps}) ps")
    times = [trace.time[index] for index in indices]
    values = [float(trace.column(label)[index]) for index in indices]
    unit = unit_for(label)
    factor = display_factor_for(unit)
    area_factor = area_factor_for(unit)
    peak_index = max(range(len(values)), key=lambda index: values[index])
    negative_index = min(range(len(values)), key=lambda index: values[index])
    abs_index = max(range(len(values)), key=lambda index: abs(values[index]))
    result: dict[str, object] = {
        "label": label,
        "window_ps": [start_ps, end_ps],
        "first_sample_ps": ps(times[0]),
        "last_sample_ps": ps(times[-1]),
        "sample_count": len(indices),
        "raw_unit": unit,
        "display_unit": display_unit_for(unit),
        "area_unit": f"{display_unit_for(unit)}*ps" if unit in ("A", "V") else "raw*s",
        "positive_peak": values[peak_index] * factor,
        "positive_peak_time_ps": ps(times[peak_index]),
        "negative_peak": values[negative_index] * factor,
        "negative_peak_time_ps": ps(times[negative_index]),
        "max_abs": abs(values[abs_index]) * factor,
        "max_abs_time_ps": ps(times[abs_index]),
        "rms": math.sqrt(sum(value * value for value in values) / len(values)) * factor,
        "signed_area": trapezoid_integral(values, times) * area_factor,
        "positive_area": trapezoid_integral([max(value, 0.0) for value in values], times) * area_factor,
        "negative_area": trapezoid_integral([min(value, 0.0) for value in values], times) * area_factor,
        "actual_time_grid_for_integration": True,
        "integration_method": "trapezoid on actual stored time values; no interpolation or resampling",
    }
    if threshold is not None:
        clusters = threshold_clusters(trace, label, start_ps, end_ps, threshold)
        result.update(
            {
                "significant_positive_threshold": threshold * factor,
                "significant_positive_threshold_unit": display_unit_for(unit),
                "significant_positive_sample_count": sum(int(item["sample_count"]) for item in clusters),
                "significant_positive_duration_span_ps": (
                    max(float(item["last_sample_ps"]) for item in clusters)
                    - min(float(item["first_sample_ps"]) for item in clusters)
                    if clusters
                    else 0.0
                ),
                "significant_positive_covered_interval_duration_ps": sum(
                    float(item["covered_interval_duration_ps"]) for item in clusters
                ),
                "significant_positive_clusters": clusters,
            }
        )
    if include_structure:
        positive_peaks = local_abs_peaks(
            trace,
            label,
            start_ps,
            end_ps,
            0.0,
            positive_only=True,
            merge_ps=0.0,
        )
        negative_peaks = [
            item
            for item in local_abs_peaks(trace, label, start_ps, end_ps, 0.0, positive_only=False, merge_ps=0.0)
            if item["value_raw"] < 0.0
        ]
        result["temporal_structure"] = {
            "zero_crossing_count": sign_change_count(values),
            "positive_local_maxima": [
                {
                    "time_ps": item["time_ps"],
                    "value": item["value_raw"] * factor,
                    "unit": display_unit_for(unit),
                }
                for item in positive_peaks[:24]
            ],
            "negative_local_abs_maxima": [
                {
                    "time_ps": item["time_ps"],
                    "value": item["value_raw"] * factor,
                    "unit": display_unit_for(unit),
                }
                for item in negative_peaks[:24]
            ],
            "interpretation": "waveform structure only; activity clusters and extrema are not event counts",
        }
    return result


def phase_window_stats(
    trace: RawTrace,
    label: str,
    unwrapped: Sequence[float],
    start_ps: float,
    end_ps: float,
) -> dict[str, object]:
    indices = window_indices(trace, start_ps, end_ps)
    values = [float(unwrapped[index]) for index in indices]
    return {
        "label": label,
        "raw_unit": "rad",
        "display_unit": "turns",
        "window_ps": [start_ps, end_ps],
        "raw_phase_min_rad": min(float(trace.column(label)[index]) for index in indices),
        "raw_phase_max_rad": max(float(trace.column(label)[index]) for index in indices),
        "unwrapped_start_rad": values[0],
        "unwrapped_end_rad": values[-1],
        "unwrapped_delta_rad": values[-1] - values[0],
        "unwrapped_delta_turns": (values[-1] - values[0]) / TAU,
        "unwrapped_p2p_rad": max(values) - min(values),
        "unwrapped_p2p_turns": (max(values) - min(values)) / TAU,
        "phase_conversion": "continuous_unwrap(raw radians), then divide by 2*pi for display turns",
        "not_an_event_count": True,
    }


def write_csv(
    path: Path,
    times: Sequence[float],
    columns: Sequence[tuple[str, Sequence[float]]],
) -> dict[str, object]:
    if not times or any(len(values) != len(times) for _, values in columns):
        raise RuntimeError(f"derived column length mismatch or empty time vector: {path}")
    labels = [label for label, _ in columns]
    if len(labels) != len(set(labels)):
        raise RuntimeError(f"derived CSV has duplicate labels: {path}")
    buffer = StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(["time"] + labels)
    for row_index, time in enumerate(times):
        writer.writerow(
            [f"{float(time):.17g}"]
            + [f"{float(values[row_index]):.17g}" for _, values in columns]
        )
    content = buffer.getvalue()
    write_once(path, content)
    return {
        "path": rel(path),
        "sha256": sha256(path),
        "labels": labels,
        "sample_count": len(times),
        "time_start_ps": ps(times[0]),
        "time_end_ps": ps(times[-1]),
    }


def raw_label(label: str, case: str) -> str:
    return f"{label} | {case} | raw | {unit_for(label)}"


def delta_label(label: str, *, context: str) -> str:
    if label.startswith("P("):
        return f"{label} | N4_MINUS_N3 | derived independent-unwrap delta | rad | {context}"
    return f"{label} | N4_MINUS_N3 | derived delta | {unit_for(label)} | {context}"


def phase_trajectory_delta(
    n3_unwrapped: Sequence[float],
    n4_unwrapped: Sequence[float],
    n3_anchor: int,
    n4_anchor: int,
    indices3: Sequence[int],
    indices4: Sequence[int],
) -> list[float]:
    n3_ref = float(n3_unwrapped[n3_anchor])
    n4_ref = float(n4_unwrapped[n4_anchor])
    return [
        (float(n4_unwrapped[index4]) - n4_ref) - (float(n3_unwrapped[index3]) - n3_ref)
        for index3, index4 in zip(indices3, indices4)
    ]


def comparison_csv(
    traces: dict[str, RawTrace],
    unwrapped: dict[str, dict[str, Sequence[float]]],
    labels: Sequence[str],
    start_ps: float,
    end_ps: float,
    output: Path,
    *,
    context: str,
) -> dict[str, object]:
    n3 = traces["N3_REPLAY"]
    n4 = traces["N4_REPLAY"]
    indices3 = window_indices(n3, start_ps, end_ps)
    indices4 = window_indices(n4, start_ps, end_ps)
    if [n3.time[index] for index in indices3] != [n4.time[index] for index in indices4]:
        raise RuntimeError(f"N3/N4 exact time grids differ in comparison window {start_ps}-{end_ps} ps")
    times = [n3.time[index] for index in indices3]
    columns: list[tuple[str, Sequence[float]]] = []
    for label in labels:
        columns.append((raw_label(label, "N3_REPLAY"), [float(n3.column(label)[index]) for index in indices3]))
        columns.append((raw_label(label, "N4_REPLAY"), [float(n4.column(label)[index]) for index in indices4]))
        if label.startswith("P("):
            values = phase_trajectory_delta(
                unwrapped["N3_REPLAY"][label],
                unwrapped["N4_REPLAY"][label],
                indices3[0],
                indices4[0],
                indices3,
                indices4,
            )
        else:
            values = [float(n4.column(label)[index4]) - float(n3.column(label)[index3]) for index3, index4 in zip(indices3, indices4)]
        columns.append((delta_label(label, context=context), values))
    record = write_csv(output, times, columns)
    record.update(
        {
            "case_tracks": ["N3_REPLAY", "N4_REPLAY"],
            "comparison": "N4 minus N3; phase delta uses independently unwrapped trajectories anchored at the window start",
            "window_ps": [start_ps, end_ps],
            "transformations": [
                "same exact stored time grid required",
                "non-phase delta is N4 raw minus N3 raw",
                "phase delta is (N4 independently unwrapped displacement) minus (N3 independently unwrapped displacement)",
            ],
        }
    )
    return record


def zoom_csv(
    trace: RawTrace,
    case: str,
    labels: Sequence[str],
    start_ps: float,
    end_ps: float,
    output: Path,
) -> dict[str, object]:
    indices = window_indices(trace, start_ps, end_ps)
    columns = [
        (raw_label(label, case), [float(trace.column(label)[index]) for index in indices])
        for label in labels
    ]
    record = write_csv(output, [trace.time[index] for index in indices], columns)
    record.update(
        {
            "case": case,
            "window_ps": [start_ps, end_ps],
            "source_kind": "windowed_raw_projection",
            "transformations": ["half-open window selection only", "no interpolation", "no smoothing", "no resampling", "no scaling", "no time shifting"],
        }
    )
    return record


def event_aligned_csv(
    traces: dict[str, RawTrace],
    unwrapped: dict[str, dict[str, Sequence[float]]],
    labels: Sequence[str],
    event_index: int,
    output: Path,
) -> dict[str, object]:
    refs = {
        case: RESPONSE_TIMES_PS[case]["BJ1"][event_index - 1]
        for case in ("N3_REPLAY", "N4_REPLAY")
    }
    index_refs = {case: exact_time_index(traces[case], refs[case])[0] for case in refs}
    columns: list[tuple[str, Sequence[float]]] = []
    for label in labels:
        values3: list[float] = []
        values4: list[float] = []
        for offset in EVENT_ALIGNED_OFFSETS_PS:
            index3, _ = exact_time_index(traces["N3_REPLAY"], refs["N3_REPLAY"] + offset)
            index4, _ = exact_time_index(traces["N4_REPLAY"], refs["N4_REPLAY"] + offset)
            values3.append(float(traces["N3_REPLAY"].column(label)[index3]))
            values4.append(float(traces["N4_REPLAY"].column(label)[index4]))
        columns.append((f"{label} | N3_REPLAY | raw | {unit_for(label)} | event{event_index} relative BJ1", values3))
        columns.append((f"{label} | N4_REPLAY | raw | {unit_for(label)} | event{event_index} relative BJ1", values4))
        if label.startswith("P("):
            delta_values = []
            for offset in EVENT_ALIGNED_OFFSETS_PS:
                index3, _ = exact_time_index(traces["N3_REPLAY"], refs["N3_REPLAY"] + offset)
                index4, _ = exact_time_index(traces["N4_REPLAY"], refs["N4_REPLAY"] + offset)
                delta_values.append(
                    (float(unwrapped["N4_REPLAY"][label][index4]) - float(unwrapped["N4_REPLAY"][label][index_refs["N4_REPLAY"]]))
                    - (float(unwrapped["N3_REPLAY"][label][index3]) - float(unwrapped["N3_REPLAY"][label][index_refs["N3_REPLAY"]]))
                )
        else:
            delta_values = [right - left for left, right in zip(values3, values4)]
        columns.append((f"{label} | N4_MINUS_N3 | derived delta | {unit_for(label)} | event{event_index} relative BJ1", delta_values))
    record = write_csv(output, [seconds(offset) for offset in EVENT_ALIGNED_OFFSETS_PS], columns)
    record.update(
        {
            "event_index": event_index,
            "reference_signal": "BJ1 descriptive voltage-peak reference",
            "reference_time_ps": refs,
            "relative_window_ps": [EVENT_ALIGNED_OFFSETS_PS[0], EVENT_ALIGNED_OFFSETS_PS[-1]],
            "alignment": "each case independently rebased to its own BJ1 reference; exact stored samples, no interpolation or value normalization",
            "phase_alignment": "each case independently unwrapped, then displacement delta formed relative to its own BJ1 reference",
        }
    )
    return record


def event_local_state_record(
    traces: dict[str, RawTrace],
    unwrapped: dict[str, dict[str, Sequence[float]]],
) -> dict[str, object]:
    states: dict[str, object] = OrderedDict()
    for case in ("N3_REPLAY", "N4_REPLAY"):
        case_states: list[dict[str, object]] = []
        for response_index in (1, 2, 3):
            ref = RESPONSE_TIMES_PS[case]["BJ1"][response_index - 1]
            offset_states: list[dict[str, object]] = []
            for offset in EVENT_LOCAL_OFFSETS_PS:
                index, grid_error = exact_time_index(traces[case], ref + offset)
                values: dict[str, object] = {}
                for label in QB_FULL_LABELS:
                    raw_value = float(traces[case].column(label)[index])
                    unit = unit_for(label)
                    item: dict[str, object] = {
                        "raw_value": raw_value,
                        "raw_unit": unit,
                        "display_value": raw_value * display_factor_for(unit),
                        "display_unit": display_unit_for(unit),
                    }
                    if label.startswith("P("):
                        item.update(
                            {
                                "unwrapped_phase_rad": float(unwrapped[case][label][index]),
                                "display_turns": float(unwrapped[case][label][index]) / TAU,
                                "phase_conversion": "independent full-trace unwrap then rad/(2*pi)",
                                "not_an_event_count": True,
                            }
                        )
                    values[label] = item
                offset_states.append(
                    {
                        "offset_ps": offset,
                        "target_time_ps": ref + offset,
                        "actual_time_ps": ps(traces[case].time[index]),
                        "grid_error_ps": grid_error,
                        "signals": values,
                    }
                )
            case_states.append(
                {
                    "response_index": response_index,
                    "alignment_reference": "BJ1",
                    "reference_time_ps": ref,
                    "uniform_offsets_ps": EVENT_LOCAL_OFFSETS_PS,
                    "states": offset_states,
                }
            )
        states[case] = case_states

    phase_summaries: dict[str, object] = {}
    for case in ("N3_REPLAY", "N4_REPLAY"):
        phase_summaries[case] = {}
        for label in ("P(BJS|XBQ1)", "P(BJ1|XBQ1)", "P(BJ2|XBQ1)"):
            phase_summaries[case][label] = []
            for response_index in (1, 2, 3):
                ref = RESPONSE_TIMES_PS[case]["BJ1"][response_index - 1]
                phase_summaries[case][label].append(
                    phase_window_stats(
                        traces[case],
                        label,
                        unwrapped[case][label],
                        ref + EVENT_LOCAL_OFFSETS_PS[0],
                        ref + EVENT_LOCAL_OFFSETS_PS[-1] + 0.1,
                    )
                )
    return {
        "alignment_reference": "BJ1 internal response time",
        "offsets_ps": EVENT_LOCAL_OFFSETS_PS,
        "state_signals": QB_FULL_LABELS,
        "cases": states,
        "phase_local_summaries": phase_summaries,
        "recovery_assessment": {
            "status": "UNKNOWN",
            "label": "UNKNOWN / NOT ESTABLISHED",
            "evidence": "the same fixed offsets expose response-dependent current, voltage, and phase differences, but no preregistered monotonic unrecovered-state scalar or threshold is established",
            "prohibited_inference": "shorter spacing alone is not dead-time or recovery-failure evidence",
        },
    }


def timing_observations() -> dict[str, object]:
    return {
        "internal_response_vs_downstream_arrival": {
            "N4_response_3": {
                "t3_BJ1_ps": 120.0,
                "t3_BJ2_ps": 121.4,
                "t3_QBOUT_ps": 121.9,
                "t3_JTL1_ps": 123.3,
                "t3_JTL6_ps": 140.1,
                "t3_RTERM_ps": 141.6,
            },
            "definition": "BJ1/BJ2/QBOUT are internal receiver references; JTL1/JTL6/R_TERM are downstream references",
            "R_TERM_semantics": "141.6 ps is an observed downstream terminal arrival reference, not QB internal third-response time",
        },
        "all_descriptive_response_times_ps": RESPONSE_TIMES_PS,
        "spacing_ps": {
            case: {
                signal: [
                    RESPONSE_TIMES_PS[case][signal][index + 1] - RESPONSE_TIMES_PS[case][signal][index]
                    for index in range(2)
                ]
                for signal in RESPONSE_TIMES_PS[case]
            }
            for case in RESPONSE_TIMES_PS
        },
        "evidence_class": "OBSERVED/DERIVED descriptive timing; not a discrete event count",
    }


def candidate_inventory(
    trace: RawTrace,
    unwrapped: dict[str, Sequence[float]],
) -> dict[str, object]:
    context_start_ps, context_end_ps = INTERNAL_SEARCH_PS
    candidate_specs = OrderedDict(
        [
            ("QBIN", {"label": "V(QBIN)", "threshold": 0.25e-3, "mode": "absolute", "start_ps": 122.0, "end_ps": 135.0, "candidate_status": "PARTIAL_EXCURSION_CANDIDATE"}),
            ("BJS", {"label": "V(BJS|XBQ1)", "threshold": 0.10e-3, "mode": "absolute", "start_ps": 122.0, "end_ps": 135.0, "candidate_status": "RESIDUAL_NONLINEAR_ACTIVITY"}),
            ("BJ1", {"label": "V(BJ1|XBQ1)", "threshold": 0.30e-3, "mode": "absolute", "start_ps": 122.0, "end_ps": 135.0, "candidate_status": "PARTIAL_EXCURSION_CANDIDATE"}),
            ("BJ2", {"label": "V(BJ2|XBQ1)", "threshold": 0.50e-3, "mode": "absolute", "start_ps": 122.0, "end_ps": 135.0, "candidate_status": "NO_SEPARABLE_POST_QBOUT_CANDIDATE"}),
            ("QBOUT", {"label": "V(QBOUT)", "threshold": 0.45e-3, "mode": "absolute", "start_ps": 122.0, "end_ps": 135.0, "candidate_status": "AMBIGUOUS_POST_QBOUT_ACTIVITY"}),
            ("JTL1", {"label": "V(B01|XJTL1_1)", "threshold": 0.50e-3, "mode": "absolute", "start_ps": 123.4, "end_ps": 140.0, "candidate_status": "NO_SEPARABLE_FOURTH_DOWNSTREAM_CANDIDATE"}),
            ("JTL6", {"label": "V(B01|XJTL1_6)", "threshold": 0.50e-3, "mode": "absolute", "start_ps": 140.2, "end_ps": 200.0, "candidate_status": "NO_SEPARABLE_FOURTH_DOWNSTREAM_CANDIDATE"}),
            ("R_TERM", {"label": "I(R_TERM)", "threshold": 5.0e-6, "mode": "absolute", "start_ps": 141.7, "end_ps": 200.0, "candidate_status": "NO_SEPARABLE_FOURTH_DOWNSTREAM_CANDIDATE"}),
        ]
    )
    inventory: dict[str, object] = OrderedDict()
    for key, spec in candidate_specs.items():
        label = str(spec["label"])
        threshold = float(spec["threshold"])
        unit = unit_for(label)
        start_ps = float(spec["start_ps"])
        end_ps = float(spec["end_ps"])
        peaks = local_abs_peaks(trace, label, start_ps, end_ps, threshold, positive_only=False, merge_ps=0.2)
        stats = waveform_stats(trace, label, start_ps, end_ps, include_structure=False)
        for peak in peaks:
            peak["value"] = peak["value_raw"] * display_factor_for(unit)
            peak["score"] = peak["score_raw"] * display_factor_for(unit)
            peak["unit"] = display_unit_for(unit)
            peak.pop("value_raw", None)
            peak.pop("score_raw", None)
        if peaks:
            status = str(spec["candidate_status"])
            evidence_class = "OBSERVED"
        else:
            status = "NO_SEPARABLE_ACTIVITY_ABOVE_REGISTERED_THRESHOLD"
            evidence_class = "BOUNDED_RESULT"
        inventory[key] = {
            "raw_label": label,
            "search_window_ps": [start_ps, end_ps],
            "context_window_ps": [context_start_ps, context_end_ps],
            "threshold": threshold * display_factor_for(unit),
            "threshold_unit": display_unit_for(unit),
            "mode": spec["mode"],
            "peak_like_activity": peaks,
            "window_waveform_stats": stats,
            "candidate_status": status,
            "evidence_class": evidence_class,
            "interpretation": "partial excursion / failed candidate / incomplete progression / residual nonlinear activity only; no switching or SFQ label is assigned",
        }
    inventory["phase_activity"] = {
        label: phase_window_stats(trace, label, unwrapped[label], context_start_ps, context_end_ps)
        for label in ("P(BJS|XBQ1)", "P(BJ1|XBQ1)", "P(BJ2|XBQ1)")
    }
    return {
        "search_window_ps": [context_start_ps, context_end_ps],
        "context_window_ps": list(INTERNAL_CONTEXT_PS),
        "post_third_probe_windows_ps": {
            key: [float(spec["start_ps"]), float(spec["end_ps"])]
            for key, spec in candidate_specs.items()
        },
        "post_third_internal_reference": {
            "t3_BJ1_ps": 120.0,
            "t3_BJ2_ps": 121.4,
            "t3_QBOUT_ps": 121.9,
        },
        "candidates": inventory,
        "summary": {
            "QBIN_BJS_BJ1_activity_present": bool(inventory["QBIN"]["peak_like_activity"] or inventory["BJS"]["peak_like_activity"] or inventory["BJ1"]["peak_like_activity"]),
            "post_QBOUT_BJ2_progression_observed": bool(inventory["BJ2"]["peak_like_activity"]),
            "new_JTL1_activity_observed": bool(inventory["JTL1"]["peak_like_activity"]),
            "fourth_complete_response": "NOT_OBSERVED",
            "fourth_partial_attempt": "OBSERVED_AS_BOUNDED_CANDIDATE_ACTIVITY" if inventory["QBIN"]["peak_like_activity"] or inventory["BJS"]["peak_like_activity"] or inventory["BJ1"]["peak_like_activity"] else "NOT_ESTABLISHED",
        },
    }


def classification_matrix(candidate: dict[str, object]) -> dict[str, object]:
    return {
        "previous_interpretation": {
            "artifact": "analysis/n4_post_third_response.json",
            "old_primary": "D_EFFECTIVE_STIMULUS_LIMIT",
            "status": "PRESERVED_BUT_SUPERSEDED",
            "reason": "the old [141.6,200) source residual used downstream R_TERM arrival as the internal third-response reference",
        },
        "current_primary": "F_MIXED_OR_UNRESOLVED",
        "evidence_class": "BOUNDED_RESULT",
        "matrix": [
            {
                "candidate": "A_FRONT_END_ACCEPTANCE_LIMIT",
                "assessment": "INCONCLUSIVE",
                "supports": ["post-QBOUT QBIN and BJS activity is present", "a unique front-end acceptance threshold is not registered"],
                "against": ["the raw trace still contains internal activity and partial BJ1/QBOUT candidates", "the exact BJS-to-BJ1 boundary is not isolated"],
            },
            {
                "candidate": "B_INTERNAL_REGENERATION_LIMIT",
                "assessment": "INCONCLUSIVE",
                "supports": ["partial BJ1 activity is visible after the internal third-response references", "no separable post-QBOUT BJ2 candidate is detected"],
                "against": ["the first three response chains reach BJ2, JTL1, JTL6 and R_TERM", "there is no independent intervention isolating BJ1-to-BJ2 regeneration"],
            },
            {
                "candidate": "C_RECOVERY_OR_DEAD_TIME_LIMIT",
                "assessment": "UNKNOWN",
                "supports": ["N4 descriptive internal spacing is shorter than N3 for the listed responses"],
                "against": ["fixed-offset state comparison has no monotonic unrecovered-state evidence", "spacing alone is not dead-time or recovery-failure evidence"],
            },
            {
                "candidate": "D_EFFECTIVE_STIMULUS_LIMIT",
                "assessment": "INCONCLUSIVE",
                "supports": ["source drive decays across the 120-135 ps window and is below the N1 first-response reference on some aggregate measures"],
                "against": ["I(I_REPLAY) remains tens of microamps after each internal reference", "the aligned window does not establish source exhaustion or a complete fourth-pulse absence"],
            },
            {
                "candidate": "E_DOWNSTREAM_PROPAGATION_LIMIT",
                "assessment": "NOT_SUPPORTED_AS_PRIMARY",
                "supports": [],
                "against": ["the first three QB responses propagate through JTL1-JTL6 to termination", "the fourth complete BJ2 trajectory is not observed before downstream loss can be isolated"],
            },
            {
                "candidate": "F_MIXED_OR_UNRESOLVED",
                "assessment": "SELECTED",
                "supports": ["front-end/internal residual activity and missing BJ2 progression coexist", "A/B/C/D cannot be uniquely separated from this replay"],
                "against": [],
            },
        ],
        "earliest_missing_progression": {
            "search_window_ps": list(INTERNAL_SEARCH_PS),
            "observed_before_missing": ["QBIN partial excursion candidate", "BJS residual nonlinear activity", "BJ1 partial excursion candidate", "ambiguous QBOUT activity"],
            "first_missing_complete_progression": "BJ1-to-BJ2 / post-QBOUT internal progression",
            "location": "between residual front-end/internal activity and a complete BJ2 trajectory",
            "precise_boundary": "UNKNOWN",
            "not_root_cause": True,
        },
        "no_root_cause_disclaimer": "earliest divergence or missing progression is not a root-cause finding; replay observation is not intervention evidence",
    }


def make_plot_manifest(
    traces: dict[str, RawTrace],
    unwrapped: dict[str, dict[str, Sequence[float]]],
) -> tuple[dict[str, object], dict[str, object]]:
    data_dir = DATA_DIR
    pages: OrderedDict[str, dict[str, object]] = OrderedDict()
    derived: OrderedDict[str, dict[str, object]] = OrderedDict()

    final_indices = window_indices(traces["N3_REPLAY"], WINDOW_START_PS, WINDOW_END_PS)
    final_times = [traces["N3_REPLAY"].time[index] for index in final_indices]
    for case in ("N3_REPLAY", "N4_REPLAY"):
        pages[f"{case}_QB_FULL_INTERNAL"] = {
            "input": rel(RAW_CASES[case]),
            "input_sha256": sha256(RAW_CASES[case]),
            "labels": QB_FULL_LABELS,
            "source_kind": "raw_direct_standalone",
            "case": case,
            "window_ps": [WINDOW_START_PS, WINDOW_END_PS],
            "title": f"{case} | QB full internal | raw direct | time window [{WINDOW_START_PS:g},{WINDOW_END_PS:g}) ps | SI units; phase raw rad shown as rad/(2*pi) turns",
        }
        pages[f"{case}_JTL_FULL_CHAIN"] = {
            "input": rel(RAW_CASES[case]),
            "input_sha256": sha256(RAW_CASES[case]),
            "labels": JTL_FULL_LABELS + ["I(R_TERM)"],
            "source_kind": "raw_direct_standalone",
            "case": case,
            "window_ps": [WINDOW_START_PS, WINDOW_END_PS],
            "title": f"{case} | JTL1-JTL6 full chain | raw direct | time window [{WINDOW_START_PS:g},{WINDOW_END_PS:g}) ps | SI units; phase raw rad shown as rad/(2*pi) turns",
        }

    qb_comparison = comparison_csv(
        traces,
        unwrapped,
        QB_FULL_LABELS,
        WINDOW_START_PS,
        WINDOW_END_PS,
        data_dir / "N3_VS_N4_QB_FULL_INTERNAL.csv",
        context="FINAL_READ_RESPONSE",
    )
    derived["N3_VS_N4_QB_FULL_INTERNAL"] = qb_comparison
    pages["N3_VS_N4_QB_FULL_INTERNAL"] = {
        "input": qb_comparison["path"],
        "input_sha256": qb_comparison["sha256"],
        "labels": qb_comparison["labels"],
        "source_kind": "derived_raw_track_pair_plus_delta",
        "case": "N3_REPLAY and N4_REPLAY",
        "window_ps": [WINDOW_START_PS, WINDOW_END_PS],
        "title": f"N3 vs N4 | QB full internal raw tracks + delta | time window [{WINDOW_START_PS:g},{WINDOW_END_PS:g}) ps | phase delta independently unwrapped",
    }

    jtl_comparison = comparison_csv(
        traces,
        unwrapped,
        JTL_FULL_LABELS + ["I(R_TERM)"],
        WINDOW_START_PS,
        WINDOW_END_PS,
        data_dir / "N3_VS_N4_JTL_FULL_CHAIN.csv",
        context="FINAL_READ_RESPONSE",
    )
    derived["N3_VS_N4_JTL_FULL_CHAIN"] = jtl_comparison
    pages["N3_VS_N4_JTL_FULL_CHAIN"] = {
        "input": jtl_comparison["path"],
        "input_sha256": jtl_comparison["sha256"],
        "labels": jtl_comparison["labels"],
        "source_kind": "derived_raw_track_pair_plus_delta",
        "case": "N3_REPLAY and N4_REPLAY",
        "window_ps": [WINDOW_START_PS, WINDOW_END_PS],
        "title": f"N3 vs N4 | JTL1-JTL6 full-chain raw tracks + delta | time window [{WINDOW_START_PS:g},{WINDOW_END_PS:g}) ps | phase delta independently unwrapped",
    }

    zoom_labels = QB_FULL_LABELS + JTL_ENDPOINT_LABELS + ["I(R_TERM)"]
    zoom = zoom_csv(
        traces["N4_REPLAY"],
        "N4_REPLAY",
        zoom_labels,
        *INTERNAL_CONTEXT_PS,
        data_dir / "N4_FOURTH_ATTEMPT_ZOOM_118_140.csv",
    )
    derived["N4_FOURTH_ATTEMPT_ZOOM_118_140"] = zoom
    pages["N4_FOURTH_ATTEMPT_ZOOM_118_140"] = {
        "input": zoom["path"],
        "input_sha256": zoom["sha256"],
        "labels": zoom["labels"],
        "source_kind": "windowed_raw_projection",
        "case": "N4_REPLAY",
        "window_ps": list(INTERNAL_CONTEXT_PS),
        "title": f"N4_REPLAY | fourth-attempt deep zoom | raw projection | time window [{INTERNAL_CONTEXT_PS[0]:g},{INTERNAL_CONTEXT_PS[1]:g}) ps | residual activity only",
    }

    event_labels = QB_FULL_LABELS + JTL_ENDPOINT_LABELS + ["I(R_TERM)"]
    for event_index in (1, 2, 3):
        record = event_aligned_csv(
            traces,
            unwrapped,
            event_labels,
            event_index,
            data_dir / f"EVENT{event_index}_N3_N4_INTERNAL_ALIGNED.csv",
        )
        key = f"EVENT{event_index}_N3_N4_INTERNAL_ALIGNED"
        derived[key] = record
        pages[key] = {
            "input": record["path"],
            "input_sha256": record["sha256"],
            "labels": record["labels"],
            "source_kind": "derived_event_aligned_raw_tracks_plus_delta",
            "case": "N3_REPLAY and N4_REPLAY",
            "window_ps": record["relative_window_ps"],
            "title": f"N3 vs N4 | event {event_index} internal-time aligned raw tracks + delta | relative BJ1 window [{record['relative_window_ps'][0]:g},{record['relative_window_ps'][1]:g}] ps | phase independently unwrapped",
        }

    manifest = {
        "schema": "jm2-n3-n4-internal-time-aligned-plot-manifest-v1",
        "phase_rule": "raw P values remain radians; comparison deltas are formed after independent per-case unwrap; -j 2pi only changes display to turns",
        "no_count_semantics": "phase displacement, voltage/current area, threshold activity, and continuous phase winding are not SFQ or event counts",
        "renderer": {
            "path": rel(REPO / "scripts/josim-plot2.py"),
            "plot_type": "sep_comb",
            "color": "dark",
            "phase_jump": "2pi",
            "command_template": "scripts/josim-plot2.py INPUT -x OUTPUT -t sep_comb -c dark -j 2pi -w TITLE -s LABELS...",
        },
        "pages": pages,
        "standalone_pages": [
            "N3_REPLAY_QB_FULL_INTERNAL",
            "N4_REPLAY_QB_FULL_INTERNAL",
            "N3_REPLAY_JTL_FULL_CHAIN",
            "N4_REPLAY_JTL_FULL_CHAIN",
        ],
        "comparison_pages": [
            "N3_VS_N4_QB_FULL_INTERNAL",
            "N3_VS_N4_JTL_FULL_CHAIN",
            "EVENT1_N3_N4_INTERNAL_ALIGNED",
            "EVENT2_N3_N4_INTERNAL_ALIGNED",
            "EVENT3_N3_N4_INTERNAL_ALIGNED",
        ],
        "zoom_pages": ["N4_FOURTH_ATTEMPT_ZOOM_118_140"],
        "required_signal_coverage": {
            "QB_full_internal": QB_FULL_LABELS,
            "JTL_full_chain": JTL_FULL_LABELS + ["I(R_TERM)"],
        },
        "derived_csvs": derived,
        "raw_direct_standalone_provenance": {
            case: {"path": rel(RAW_CASES[case]), "sha256": sha256(RAW_CASES[case])}
            for case in ("N3_REPLAY", "N4_REPLAY")
        },
    }
    return manifest, derived


def main() -> int:
    raw_before = {case: sha256(path) for case, path in RAW_CASES.items()}
    traces = {case: read_csv(path) for case, path in RAW_CASES.items()}
    for trace in traces.values():
        validate_trace(trace)
    if traces["N3_REPLAY"].time != traces["N4_REPLAY"].time:
        raise RuntimeError("N3/N4 raw time arrays are not identical; refusing unaligned comparison")

    unwrapped = {
        case: {label: continuous_unwrap(traces[case].column(label)) for label in PHASE_LABELS}
        for case in ("N3_REPLAY", "N4_REPLAY")
    }
    timing = timing_observations()
    source_reference_times = {
        case: RESPONSE_TIMES_PS[case]["R_TERM"][0]
        for case in ("N3_REPLAY", "N4_REPLAY")
    }
    n1_terminal_candidates = local_abs_peaks(
        traces["N1_REPLAY"],
        "I(R_TERM)",
        WINDOW_START_PS,
        WINDOW_END_PS,
        5.0e-6,
        positive_only=True,
        merge_ps=1.0,
    )
    if not n1_terminal_candidates:
        raise RuntimeError("N1_REPLAY has no first terminal reference")
    n1_first_terminal_ps = n1_terminal_candidates[0]["time_ps"]
    n1_reference = waveform_stats(
        traces["N1_REPLAY"],
        "I(I_REPLAY)",
        WINDOW_START_PS,
        n1_first_terminal_ps,
        threshold=SOURCE_THRESHOLD_A,
        include_structure=True,
    )
    n1_reference.update(
        {
            "reference_time_ps": n1_first_terminal_ps,
            "reference_definition": "N1 first positive I(R_TERM) terminal peak-like maximum; source reference stops before that downstream peak",
            "role": "bounded first-response source reference only",
        }
    )

    source_after_internal: dict[str, object] = OrderedDict()
    for case in ("N3_REPLAY", "N4_REPLAY"):
        if case != "N4_REPLAY":
            continue
        source_after_internal[case] = OrderedDict()
        for key, start in (
            ("after_t3_BJ1", RESPONSE_TIMES_PS[case]["BJ1"][2]),
            ("after_t3_BJ2", RESPONSE_TIMES_PS[case]["BJ2"][2]),
            ("after_t3_QBOUT", RESPONSE_TIMES_PS[case]["QBOUT"][2]),
        ):
            metrics = waveform_stats(
                traces[case],
                "I(I_REPLAY)",
                start,
                INTERNAL_SEARCH_PS[1],
                threshold=SOURCE_THRESHOLD_A,
                include_structure=True,
            )
            metrics["internal_reference"] = key
            metrics["reference_time_ps"] = start
            metrics["comparison_to_N1_first_response"] = {
                "positive_area_ratio": metrics["positive_area"] / n1_reference["positive_area"],
                "positive_peak_ratio": metrics["positive_peak"] / n1_reference["positive_peak"],
                "rms_ratio": metrics["rms"] / n1_reference["rms"],
                "comparison_note": "window lengths differ; ratios are bounded descriptive comparisons, not a complete fourth-pulse test",
            }
            source_after_internal[case][key] = metrics

    candidate = candidate_inventory(traces["N4_REPLAY"], unwrapped["N4_REPLAY"])
    state_record = event_local_state_record(traces, unwrapped)
    classification = classification_matrix(candidate)

    raw_after_analysis = {case: sha256(path) for case, path in RAW_CASES.items()}
    raw_qa = {
        "schema": "jm2-n3-n4-internal-time-aligned-raw-qa-v1",
        "status": "PASS" if raw_before == raw_after_analysis else "FAIL",
        "raw_unchanged": raw_before == raw_after_analysis,
        "raw_hashes_before": raw_before,
        "raw_hashes_after": raw_after_analysis,
        "no_solver": True,
        "no_circuit_parameter_timing_changes": True,
        "transformation_registry": [
            "raw reads preserve stored values and stored time values",
            "derived CSV comparisons use exact common stored time grid",
            "event alignment selects exact stored samples at registered offsets",
            "zoom uses half-open window selection only",
            "no interpolation, smoothing, resampling, scaling, sign correction, unit correction, or time shifting",
        ],
        "cases": {
            case: {
                "path": rel(RAW_CASES[case]),
                "sha256": raw_after_analysis[case],
                "role": "N1 first-response source reference" if case == "N1_REPLAY" else "N3/N4 replay deep-dive raw",
                "grid": raw_grid_record(traces[case]),
                "required_header_count": len(ALL_REQUIRED_LABELS),
                "required_headers_present": True,
                "optional_absent_headers": ["V(IB|XBQ1)"] if "V(IB|XBQ1)" not in traces[case].headers else [],
            }
            for case in RAW_CASES
        },
        "analysis_windows_ps": {
            "FINAL_READ_RESPONSE": [WINDOW_START_PS, WINDOW_END_PS],
            "INTERNAL_SEARCH": list(INTERNAL_SEARCH_PS),
            "INTERNAL_CONTEXT": list(INTERNAL_CONTEXT_PS),
        },
        "integration": {
            "actual_stored_time_grid": True,
            "method": "trapezoid on actual time values",
            "irregular_grid_retained": True,
        },
        "window_boundary_policy": {
            "semantics": "half-open [start,end)",
            "floating_representation_tolerance_ps": WINDOW_BOUNDARY_EPS_PS,
            "purpose": "include an intended registered boundary sample when binary floating-point conversion represents it just below the decimal ps value; no sample values are altered",
        },
        "phase": {
            "raw_unit": "rad",
            "comparison_rule": "independently unwrap each case before delta",
            "display": "rad/(2*pi) turns",
            "not_an_SFQ_count": True,
        },
    }
    json_once(QA_OUTPUT, raw_qa)

    plot_manifest, derived_records = make_plot_manifest(traces, unwrapped)
    json_once(MANIFEST_OUTPUT, plot_manifest)

    analysis = {
        "schema": "jm2-n3-n4-internal-time-aligned-analysis-v1",
        "analysis_version": "internal-time-aligned-v3",
        "created_at_local": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "git_head_at_analysis": subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, text=True, capture_output=True, check=True).stdout.strip(),
        "task_scope": {
            "mode": "READ_ONLY_ANALYSIS / EVIDENCE_PACKAGING",
            "new_josim_solve": False,
            "circuit_parameter_timing_changed": False,
            "replay_waveform_changed": False,
            "existing_raw_changed": False,
            "sweep_or_optimization": False,
        },
        "supersedes": {
            "old_artifact": "analysis/n4_post_third_response.json",
            "old_interpretation": "D_EFFECTIVE_STIMULUS_LIMIT based on source residual beginning at downstream R_TERM t3=141.6 ps",
            "superseding_reason": "third internal response must be aligned to BJ1/BJ2/QBOUT times; R_TERM 141.6 ps is downstream arrival",
            "old_artifact_preserved": True,
        },
        "raw_provenance": raw_qa["cases"],
        "exact_windows_ps": {
            "final_read_response": [WINDOW_START_PS, WINDOW_END_PS],
            "source_after_t3_BJ1_BJ2_QBOUT": [INTERNAL_SEARCH_PS[0], INTERNAL_SEARCH_PS[1]],
            "fourth_attempt_search": list(INTERNAL_SEARCH_PS),
            "fourth_attempt_context": list(INTERNAL_CONTEXT_PS),
            "event_local_state_offsets_relative_to_BJ1": EVENT_LOCAL_OFFSETS_PS,
            "event_aligned_plot_offsets_relative_to_BJ1": [EVENT_ALIGNED_OFFSETS_PS[0], EVENT_ALIGNED_OFFSETS_PS[-1]],
            "window_boundary_tolerance_ps": WINDOW_BOUNDARY_EPS_PS,
        },
        "exact_response_reference_times_ps": timing,
        "source_first_response_reference": {
            "case": "N1_REPLAY",
            "metrics": n1_reference,
            "comparison_boundary": "N1 is a bounded first-response source reference; it does not establish a complete N4 fourth pulse",
        },
        "source_after_internal_references": source_after_internal,
        "fourth_attempt_candidate_inventory": candidate,
        "event_local_qb_state_comparison": state_record,
        "classification_evidence_matrix": classification,
        "unknown_fields": [
            "unique physical separation among front-end acceptance, internal regeneration, recovery/dead-time, and effective stimulus limits",
            "whether residual QBIN/BJS/BJ1/QBOUT activity would form a complete fourth response under another intervention",
            "timestep convergence and parameter/solver sensitivity for this replay",
            "hardware behavior and any universal mechanism claim",
        ],
        "evidence_labels": {
            "OBSERVED": "raw waveform or raw-derived descriptive timing/activity directly visible in the sealed CSV",
            "DERIVED": "explicit arithmetic from raw using exact stored time values or independent phase unwrap",
            "BOUNDED_RESULT": "conclusion limited to these replay raw files, fixed topology/parameters, and declared windows",
            "UNKNOWN": "current raw does not uniquely determine the mechanism or state claim",
        },
        "disclaimers": {
            "no_SFQ_count": "phase winding, phase displacement, voltage/current area, threshold activity, and waveform peaks are not SFQ or event counts",
            "no_root_cause": "earliest divergence or missing progression is not a root-cause finding; no intervention evidence was added",
            "replay_oracle": "ideal current replay tests waveform sufficiency under ideal forcing and is not a circuit-equivalent source reconstruction",
        },
        "visualization": {
            "manifest": rel(MANIFEST_OUTPUT),
            "qa": rel(EXP / "analysis/internal_time_aligned_v2_viz_qa.json"),
            "descriptive_only": True,
            "derived_csvs": derived_records,
        },
        "qa": {
            "raw_qa": rel(QA_OUTPUT),
            "independent_check": rel(EXP / "analysis/internal_time_aligned_v2_independent_check.json"),
            "raw_status": raw_qa["status"],
            "raw_unchanged": raw_qa["raw_unchanged"],
            "required_probe_coverage": {
                "QB_full_internal": len(QB_FULL_LABELS),
                "JTL_full_chain": len(JTL_FULL_LABELS),
                "JTL_stages_covered": list(range(1, 7)),
            },
        },
    }
    json_once(ANALYSIS_OUTPUT, analysis)
    print(
        json.dumps(
            {
                "status": raw_qa["status"],
                "new_josim_solve": False,
                "raw_unchanged": raw_qa["raw_unchanged"],
                "source_windows": list(source_after_internal["N4_REPLAY"]),
                "fourth_partial_attempt": candidate["summary"]["fourth_partial_attempt"],
                "classification": classification["current_primary"],
                "analysis_artifact": rel(ANALYSIS_OUTPUT),
                "pages": len(plot_manifest["pages"]),
            },
            ensure_ascii=False,
        )
    )
    return 0 if raw_qa["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
