"""Generic onset and persistence primitives for sampled traces.

These helpers deliberately know nothing about QB, BVM, or a physical event.
They only describe when a sampled scalar remains above a declared threshold.
"""

from __future__ import annotations

import math
from typing import Mapping, Sequence

from .waveform import percentile


def first_persistent_exceedance(
    times_s: Sequence[float],
    values: Sequence[float],
    threshold: float,
    *,
    min_consecutive_samples: int = 1,
    min_duration_s: float | None = None,
) -> dict[str, float | int | None | str]:
    """Find the first finite above-threshold run satisfying persistence.

    A run qualifies when it has at least ``min_consecutive_samples`` samples
    OR spans at least ``min_duration_s`` between its first and last sampled
    times.  NaN/Inf values break a run.  The returned span is the actual
    sampled span, never an assumed uniform timestep.
    """

    if len(times_s) != len(values) or not times_s:
        raise ValueError("times and values must have equal nonzero length")
    if any(not math.isfinite(float(value)) for value in times_s):
        raise ValueError("times contain NaN or Inf")
    if any(float(times_s[index + 1]) <= float(times_s[index]) for index in range(len(times_s) - 1)):
        raise ValueError("times must be strictly increasing")
    if not math.isfinite(float(threshold)) or float(threshold) < 0.0:
        raise ValueError("threshold must be finite and nonnegative")
    if min_consecutive_samples < 1:
        raise ValueError("min_consecutive_samples must be positive")
    if min_duration_s is not None and (
        not math.isfinite(float(min_duration_s)) or float(min_duration_s) < 0.0
    ):
        raise ValueError("min_duration_s must be finite and nonnegative")

    required_samples = int(min_consecutive_samples)
    required_duration = None if min_duration_s is None else float(min_duration_s)
    run_start: int | None = None
    finite_above = 0
    for index in range(len(values) + 1):
        above = (
            index < len(values)
            and math.isfinite(float(values[index]))
            and float(values[index]) > float(threshold)
        )
        if above:
            if run_start is None:
                run_start = index
                finite_above = 0
            finite_above += 1
            duration = float(times_s[index]) - float(times_s[run_start])
            qualifies = finite_above >= required_samples or (
                required_duration is not None and duration >= required_duration
            )
            if qualifies:
                end_index = index
                return {
                    "status": "CROSSED",
                    "threshold": float(threshold),
                    "first_index": int(run_start),
                    "first_time_s": float(times_s[run_start]),
                    "persistence_start_s": float(times_s[run_start]),
                    "persistence_end_s": float(times_s[end_index]),
                    "persistence_span_s": duration,
                    "persistence_sample_count": int(finite_above),
                    "required_consecutive_samples": required_samples,
                    "required_duration_s": required_duration,
                }
        else:
            run_start = None
            finite_above = 0
    return {
        "status": "NO_CROSSING",
        "threshold": float(threshold),
        "first_index": None,
        "first_time_s": None,
        "persistence_start_s": None,
        "persistence_end_s": None,
        "persistence_span_s": None,
        "persistence_sample_count": 0,
        "required_consecutive_samples": required_samples,
        "required_duration_s": required_duration,
    }


def tie_groups(
    layer_first_time_ps: Mapping[str, float | None],
    tie_resolution_ps: float,
) -> list[dict[str, object]]:
    """Group layer onsets within a fixed absolute tie resolution."""

    if not math.isfinite(float(tie_resolution_ps)) or float(tie_resolution_ps) < 0.0:
        raise ValueError("tie_resolution_ps must be finite and nonnegative")
    present = sorted(
        (float(time), str(layer))
        for layer, time in layer_first_time_ps.items()
        if time is not None and math.isfinite(float(time))
    )
    groups: list[dict[str, object]] = []
    for time, layer in present:
        difference = time - float(groups[-1]["first_time_ps"]) if groups else None
        tolerance = float(tie_resolution_ps) + 1.0e-12
        if not groups or float(difference) > tolerance:
            groups.append({"first_time_ps": time, "layers": [layer]})
        else:
            groups[-1]["layers"].append(layer)  # type: ignore[index]
    return groups


def p99(values: Sequence[float]) -> float:
    """Convenience wrapper for the PRE noise scale."""

    return percentile(values, 0.99)


def pre_noise_referenced_threshold(
    pre_abs_difference: Sequence[float],
    floor: float,
    *,
    multiplier: float = 5.0,
) -> float:
    """Return ``max(floor, multiplier * PRE p99(abs difference))``."""

    if not math.isfinite(float(floor)) or float(floor) < 0.0:
        raise ValueError("floor must be finite and nonnegative")
    if not math.isfinite(float(multiplier)) or float(multiplier) < 0.0:
        raise ValueError("multiplier must be finite and nonnegative")
    return max(float(floor), float(multiplier) * p99(pre_abs_difference))
