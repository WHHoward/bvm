"""Explicitly aligned trace comparison metrics."""

from __future__ import annotations

import bisect
import math
from typing import Sequence

from .phase import window_indices


class TimeGridMismatch(ValueError):
    """Traces need explicit interpolation before they can be compared."""


def _validate(values: Sequence[float], name: str) -> None:
    if len(values) == 0:
        raise ValueError(f"{name} must not be empty")
    if any(not math.isfinite(float(value)) for value in values):
        raise ValueError(f"{name} contains NaN or Inf")


def exact_time_grid_identity(
    time_a: Sequence[float], time_b: Sequence[float]
) -> bool:
    """Return exact (length and token value) time-grid identity."""

    return len(time_a) == len(time_b) and all(a == b for a, b in zip(time_a, time_b))


def _linear_interpolate(
    source_time: Sequence[float], source_values: Sequence[float], target_time: Sequence[float]
) -> list[float]:
    if len(source_time) != len(source_values) or len(source_time) < 2:
        raise ValueError("linear interpolation needs at least two source samples")
    if any(source_time[index + 1] <= source_time[index] for index in range(len(source_time) - 1)):
        raise ValueError("source time must be strictly increasing")
    if target_time[0] < source_time[0] or target_time[-1] > source_time[-1]:
        raise TimeGridMismatch("linear interpolation would extrapolate outside source time")
    output: list[float] = []
    for value in target_time:
        right = bisect.bisect_left(source_time, value)
        if right < len(source_time) and source_time[right] == value:
            output.append(float(source_values[right]))
            continue
        if right == 0 or right == len(source_time):
            raise TimeGridMismatch("target time cannot be interpolated")
        left = right - 1
        fraction = (value - source_time[left]) / (source_time[right] - source_time[left])
        output.append(float(source_values[left]) + fraction * (float(source_values[right]) - float(source_values[left])))
    return output


def _p95(values: Sequence[float]) -> float:
    ordered = sorted(float(value) for value in values)
    if len(ordered) == 1:
        return ordered[0]
    rank = 0.95 * (len(ordered) - 1)
    lower = math.floor(rank)
    upper = math.ceil(rank)
    if lower == upper:
        return ordered[lower]
    weight = rank - lower
    return ordered[lower] + weight * (ordered[upper] - ordered[lower])


def _correlation(left: Sequence[float], right: Sequence[float]) -> float | None:
    mean_left = sum(left) / len(left)
    mean_right = sum(right) / len(right)
    centered_left = [value - mean_left for value in left]
    centered_right = [value - mean_right for value in right]
    denom = math.sqrt(
        sum(value * value for value in centered_left)
        * sum(value * value for value in centered_right)
    )
    if denom == 0.0:
        return 1.0 if all(a == b for a, b in zip(left, right)) else None
    return sum(a * b for a, b in zip(centered_left, centered_right)) / denom


def _scalar_fit(left: Sequence[float], right: Sequence[float]) -> dict[str, float | None]:
    denominator = sum(value * value for value in left)
    if denominator == 0.0:
        return {"status": "NOT_DEFINED", "k": None, "normalized_residual": None}
    k = sum(a * b for a, b in zip(left, right)) / denominator
    residual = [b - k * a for a, b in zip(left, right)]
    norm = math.sqrt(sum(value * value for value in residual))
    right_norm = math.sqrt(sum(value * value for value in right))
    return {
        "status": "VALID",
        "k": k,
        "normalized_residual": norm / right_norm if right_norm else 0.0,
    }


def compare_series(
    time_a: Sequence[float],
    values_a: Sequence[float],
    time_b: Sequence[float],
    values_b: Sequence[float],
    *,
    interpolation: str | None = None,
    include_correlation: bool = False,
    include_scalar_fit: bool = False,
) -> dict[str, object]:
    """Compare two traces; no interpolation occurs unless explicitly named."""

    if len(time_a) != len(values_a) or len(time_b) != len(values_b):
        raise ValueError("each time/value pair must have equal lengths")
    _validate(time_a, "time_a")
    _validate(time_b, "time_b")
    _validate(values_a, "values_a")
    _validate(values_b, "values_b")
    if any(time_a[index + 1] <= time_a[index] for index in range(len(time_a) - 1)):
        raise ValueError("time_a must be strictly increasing")
    if any(time_b[index + 1] <= time_b[index] for index in range(len(time_b) - 1)):
        raise ValueError("time_b must be strictly increasing")

    grid_exact = exact_time_grid_identity(time_a, time_b)
    if interpolation is None:
        if not grid_exact:
            raise TimeGridMismatch(
                "time grids differ; pass interpolation='linear' explicitly if justified"
            )
        aligned_a = [float(value) for value in values_a]
        aligned_b = [float(value) for value in values_b]
        mode = "none"
    elif interpolation == "linear":
        aligned_a = [float(value) for value in values_a]
        aligned_b = _linear_interpolate(time_b, values_b, time_a)
        mode = "linear"
    else:
        raise ValueError("interpolation must be None or 'linear'")

    difference = [right - left for left, right in zip(aligned_a, aligned_b)]
    result: dict[str, object] = {
        "status": "VALID",
        "time_grid_exact": grid_exact,
        "interpolation_mode": mode,
        "sample_count": len(difference),
        "pointwise_difference": difference,
        "max_abs_difference": max(abs(value) for value in difference),
        "rms_difference": math.sqrt(sum(value * value for value in difference) / len(difference)),
        "p95_abs_difference": _p95([abs(value) for value in difference]),
    }
    if include_correlation:
        result["correlation"] = _correlation(aligned_a, aligned_b)
    if include_scalar_fit:
        result["scalar_fit"] = _scalar_fit(aligned_a, aligned_b)
    return result


def compare_windowed_series(
    time_a: Sequence[float],
    values_a: Sequence[float],
    time_b: Sequence[float],
    values_b: Sequence[float],
    window_s: tuple[float, float],
    *,
    value_scale: float = 1.0,
    unit: str = "raw",
    include_correlation: bool = False,
    include_scalar_fit: bool = False,
) -> dict[str, object]:
    """Compare two traces on the same fixed window without interpolation."""

    if len(time_a) != len(values_a) or len(time_b) != len(values_b):
        raise ValueError("each time/value pair must have equal lengths")
    indices_a = window_indices(time_a, *window_s)
    indices_b = window_indices(time_b, *window_s)
    selected_time_a = [float(time_a[index]) for index in indices_a]
    selected_time_b = [float(time_b[index]) for index in indices_b]
    selected_values_a = [float(values_a[index]) for index in indices_a]
    selected_values_b = [float(values_b[index]) for index in indices_b]
    comparison = compare_series(
        selected_time_a,
        selected_values_a,
        selected_time_b,
        selected_values_b,
        interpolation=None,
        include_correlation=include_correlation,
        include_scalar_fit=include_scalar_fit,
    )
    if not math.isfinite(float(value_scale)):
        raise ValueError("value_scale must be finite")
    result: dict[str, object] = {
        "status": str(comparison["status"]),
        "difference_convention": "right_minus_left",
        "interpolation_mode": comparison["interpolation_mode"],
        "time_grid_exact": bool(comparison["time_grid_exact"]),
        "window_s": [float(window_s[0]), float(window_s[1])],
        "sample_count": int(comparison["sample_count"]),
        "max_abs_difference": float(comparison["max_abs_difference"]) * value_scale,
        "rms_difference": float(comparison["rms_difference"]) * value_scale,
        "p95_abs_difference": float(comparison["p95_abs_difference"]) * value_scale,
        "unit": unit,
    }
    if include_correlation:
        result["correlation"] = comparison["correlation"]
    if include_scalar_fit:
        result["scalar_fit"] = comparison["scalar_fit"]
    return result
