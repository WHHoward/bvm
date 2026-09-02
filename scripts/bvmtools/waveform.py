"""Small waveform diagnostics on the actual sampled time grid."""

from __future__ import annotations

import math
from typing import Sequence

from .phase import window_indices


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


def percentile(values: Sequence[float], fraction: float) -> float:
    """Return a deterministic linearly interpolated sample percentile."""

    if not 0.0 <= float(fraction) <= 1.0:
        raise ValueError("fraction must be between 0 and 1")
    ordered = sorted(float(value) for value in values)
    if not ordered:
        raise ValueError("percentile requires at least one value")
    rank = (len(ordered) - 1) * float(fraction)
    lower = math.floor(rank)
    upper = math.ceil(rank)
    if lower == upper:
        return ordered[lower]
    weight = rank - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * weight


def zero_crossing_count(values: Sequence[float]) -> int:
    """Count sign changes while ignoring exact zero samples."""

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
        "median": percentile(y, 0.5),
        "rms": math.sqrt(sum(value * value for value in y) / len(y)),
        "max_abs": max(abs(value) for value in y),
        "positive_occupancy": sum(value > 0.0 for value in y) / len(y),
        "negative_occupancy": sum(value < 0.0 for value in y) / len(y),
        "zero_occupancy": sum(value == 0.0 for value in y) / len(y),
        "zero_crossing_count": zero_crossing_count(y),
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


def waveform_window_metrics(
    times: Sequence[float],
    values: Sequence[float],
    window_s: tuple[float, float],
    *,
    unit: str = "raw",
) -> dict[str, float | int | str | list[float]]:
    """Return unit-normalized waveform statistics in a fixed half-open window.

    Input values remain in their JoSIM SI units (A or V).  The returned
    value/area fields are normalized only for display: A→uA and A·s→uA·ps,
    V→mV and V·s→mV·ps.  Integration always uses the actual input time grid.
    """

    if len(times) != len(values):
        raise ValueError("times and values must have equal length")
    indices = window_indices(times, *window_s)
    if len(indices) < 2:
        raise ValueError("waveform window requires at least two samples")
    selected_times = [float(times[index]) for index in indices]
    selected_values = [float(values[index]) for index in indices]
    base = waveform_metrics(selected_times, selected_values)
    if unit == "A":
        value_factor = 1.0e6
        area_factor = 1.0e18
        display_unit = "uA"
        area_unit = "uA*ps"
    elif unit == "V":
        value_factor = 1.0e3
        area_factor = 1.0e15
        display_unit = "mV"
        area_unit = "mV*ps"
    elif unit == "raw":
        value_factor = 1.0
        area_factor = 1.0
        display_unit = "raw"
        area_unit = "raw*s"
    else:
        raise ValueError("unit must be 'A', 'V', or 'raw'")
    return {
        "unit": display_unit,
        "area_unit": area_unit,
        "window_s": [float(window_s[0]), float(window_s[1])],
        "sample_count": int(base["sample_count"]),
        "minimum": float(base["minimum"]) * value_factor,
        "maximum": float(base["maximum"]) * value_factor,
        "p2p": float(base["p2p"]) * value_factor,
        "mean": float(base["mean"]) * value_factor,
        "median": float(base["median"]) * value_factor,
        "rms": float(base["rms"]) * value_factor,
        "max_abs": float(base["max_abs"]) * value_factor,
        "positive_occupancy": float(base["positive_occupancy"]),
        "negative_occupancy": float(base["negative_occupancy"]),
        "zero_occupancy": float(base["zero_occupancy"]),
        "zero_crossing_count": int(base["zero_crossing_count"]),
        "peak_value": float(base["peak_value"]) * value_factor,
        "peak_time_s": float(base["peak_time"]),
        "minimum_value": float(base["minimum_value"]) * value_factor,
        "minimum_time_s": float(base["minimum_time"]),
        "window_start_s": float(selected_times[0]),
        "window_last_sample_s": float(selected_times[-1]),
        "signed_time_integral": float(base["signed_time_integral"]) * area_factor,
        "positive_area": float(base["positive_area"]) * area_factor,
        "negative_area": float(base["negative_area"]) * area_factor,
    }
