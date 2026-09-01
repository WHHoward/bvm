"""Small waveform diagnostics on the actual sampled time grid."""

from __future__ import annotations

import math
from typing import Sequence


def _validate(times: Sequence[float], values: Sequence[float]) -> None:
    if len(times) != len(values):
        raise ValueError("times and values must have equal length")
    if len(times) < 1:
        raise ValueError("waveform must contain at least one sample")
    if any(
        not math.isfinite(float(value))
        for value in list(times) + list(values)
    ):
        raise ValueError("waveform contains NaN or Inf")
    if any(times[index + 1] <= times[index] for index in range(len(times) - 1)):
        raise ValueError("time must be strictly increasing")


def trapezoid_integral(values: Sequence[float], times: Sequence[float]) -> float:
    """Integrate values using the actual, possibly nonuniform, time grid."""

    if len(values) != len(times):
        raise ValueError("values and times must have equal length")
    if len(values) < 2:
        raise ValueError("trapezoid integration requires at least two samples")
    return sum(
        0.5 * (float(values[index]) + float(values[index + 1]))
        * (float(times[index + 1]) - float(times[index]))
        for index in range(len(values) - 1)
    )


def _integral_or_zero(values: Sequence[float], times: Sequence[float]) -> float:
    return 0.0 if len(values) < 2 else trapezoid_integral(values, times)


def waveform_metrics(
    times: Sequence[float],
    values: Sequence[float],
    *,
    include_centroid: bool = False,
) -> dict[str, float | int | None]:
    """Return descriptive min/max/area/peak diagnostics.

    ``signed_time_integral`` and the positive/negative areas are waveform
    diagnostics only.  They must not be renamed as an SFQ quantity.
    If requested, ``centroid_time`` is the first moment
    ``integral(t*f(t)dt) / integral(f(t)dt)`` on the same grid.
    """

    _validate(times, values)
    t = [float(item) for item in times]
    y = [float(item) for item in values]
    peak_index = max(range(len(y)), key=lambda index: y[index])
    minimum_index = min(range(len(y)), key=lambda index: y[index])
    signed_area = _integral_or_zero(y, t)
    positive_area = _integral_or_zero([max(value, 0.0) for value in y], t)
    negative_area = _integral_or_zero([min(value, 0.0) for value in y], t)
    result: dict[str, float | int | None] = {
        "sample_count": len(y),
        "minimum": min(y),
        "maximum": max(y),
        "p2p": max(y) - min(y),
        "mean": sum(y) / len(y),
        "rms": math.sqrt(sum(value * value for value in y) / len(y)),
        "max_abs": max(abs(value) for value in y),
        "signed_time_integral": signed_area,
        "positive_area": positive_area,
        "negative_area": negative_area,
        "peak_value": y[peak_index],
        "peak_time": t[peak_index],
        "minimum_value": y[minimum_index],
        "minimum_time": t[minimum_index],
    }
    if include_centroid:
        first_moment = _integral_or_zero([time * value for time, value in zip(t, y)], t)
        result["centroid_time"] = first_moment / signed_area if signed_area else None
    return result
