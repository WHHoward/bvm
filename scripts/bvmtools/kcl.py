"""Generic signed linear KCL residual helpers.

The module is intentionally circuit-name agnostic.  Experiment analyzers own
the branch mapping and equation labels; this file only evaluates signed linear
combinations on a shared sampled grid and summarizes the residual.
"""

from __future__ import annotations

import math
from typing import Mapping, Sequence

from .phase import window_indices
from .waveform import percentile, waveform_window_metrics


def linear_kcl_residual(
    branches: Mapping[str, Sequence[float]],
    coefficients: Mapping[str, float],
) -> tuple[float, ...]:
    """Return ``sum(coefficients[name] * branches[name])`` sample-wise."""

    if not branches:
        raise ValueError("branches must not be empty")
    lengths = {len(values) for values in branches.values()}
    if len(lengths) != 1 or next(iter(lengths), 0) == 0:
        raise ValueError("all branches must have equal nonzero length")
    if set(coefficients) != set(branches):
        raise ValueError("coefficients must name every branch exactly once")
    if any(not math.isfinite(float(coefficient)) for coefficient in coefficients.values()):
        raise ValueError("coefficients contain NaN or Inf")
    if any(
        not math.isfinite(float(value))
        for values in branches.values()
        for value in values
    ):
        raise ValueError("branches contain NaN or Inf")
    count = next(iter(lengths))
    return tuple(
        sum(float(coefficients[name]) * float(branches[name][index]) for name in branches)
        for index in range(count)
    )


def kcl_window_metrics(
    times_s: Sequence[float],
    residual: Sequence[float],
    window_s: tuple[float, float],
    *,
    unit: str = "A",
) -> dict[str, float | int | str | list[float]]:
    """Summarize a residual on a fixed window using actual sample times."""

    if unit != "A":
        raise ValueError("KCL residual unit must be 'A'")
    indices = window_indices(times_s, *window_s)
    if len(indices) < 2:
        raise ValueError("KCL window requires at least two samples")
    selected = [float(residual[index]) for index in indices]
    waveform = waveform_window_metrics(times_s, residual, window_s, unit="A")
    abs_uA = [abs(value) * 1.0e6 for value in selected]
    return {
        "unit": "uA",
        "window_s": [float(window_s[0]), float(window_s[1])],
        "sample_count": int(waveform["sample_count"]),
        "max_abs_uA": float(waveform["max_abs"]),
        "p95_abs_uA": float(percentile(abs_uA, 0.95)),
        "rms_uA": float(waveform["rms"]),
    }
