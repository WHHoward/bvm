"""Authoritative phase-unit and deterministic monotonic segmentation helpers."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence


TAU = 2.0 * math.pi


@dataclass(frozen=True)
class MonotonicSegment:
    """Inclusive index range; adjacent direction changes share one endpoint."""

    start_index: int
    end_index: int
    direction: int

    @property
    def sample_count(self) -> int:
        return self.end_index - self.start_index + 1


def _validate_phase(values: Sequence[float]) -> None:
    if len(values) == 0:
        raise ValueError("phase sequence must not be empty")
    if any(not math.isfinite(float(value)) for value in values):
        raise ValueError("phase sequence contains NaN or Inf")


def continuous_unwrap(values: Sequence[float]) -> tuple[float, ...]:
    """Unwrap raw phase radians with deterministic NumPy-compatible semantics."""

    _validate_phase(values)
    result = [float(values[0])]
    previous_raw = float(values[0])
    for raw_value in values[1:]:
        current_raw = float(raw_value)
        delta = current_raw - previous_raw
        if delta > math.pi:
            delta -= TAU * math.ceil((delta - math.pi) / TAU)
        elif delta < -math.pi:
            delta += TAU * math.ceil((-delta - math.pi) / TAU)
        result.append(result[-1] + delta)
        previous_raw = current_raw
    return tuple(result)


def phase_delta_rad(values: Sequence[float], *, unwrap: bool = True) -> float:
    """Return endpoint phase difference in raw radians."""

    _validate_phase(values)
    sequence = continuous_unwrap(values) if unwrap else tuple(float(value) for value in values)
    return sequence[-1] - sequence[0]


def phase_delta_turns(values: Sequence[float], *, unwrap: bool = True) -> float:
    """Return ``phase_delta_rad / (2*pi)`` without rounding or abs()."""

    return phase_delta_rad(values, unwrap=unwrap) / TAU


def window_indices(
    times: Sequence[float], start: float, end: float
) -> tuple[int, ...]:
    """Select the half-open window ``start <= t < end``."""

    if not math.isfinite(float(start)) or not math.isfinite(float(end)):
        raise ValueError("window bounds must be finite")
    if start > end:
        raise ValueError("window start must be <= end")
    if any(not math.isfinite(float(value)) for value in times):
        raise ValueError("time sequence contains NaN or Inf")
    if any(times[index + 1] <= times[index] for index in range(len(times) - 1)):
        raise ValueError("time must be strictly increasing")
    return tuple(index for index, value in enumerate(times) if start <= value < end)


def monotonic_segments(values: Sequence[float]) -> tuple[MonotonicSegment, ...]:
    """Segment exact-sign monotonic runs, preserving the strict legacy rule.

    Zero increments are neutral.  The first run starts at index zero and a
    direction change overlaps the boundary sample.  This is the segmentation
    used by the accepted 9 ps/13 ps strict-event reclassification and is kept
    intentionally deterministic; no smoothing, resampling, or threshold
    tuning is performed here.
    """

    _validate_phase(values)
    if len(values) < 2:
        return ()
    signs: list[int] = []
    for index in range(len(values) - 1):
        difference = float(values[index + 1]) - float(values[index])
        signs.append(1 if difference > 0.0 else -1 if difference < 0.0 else 0)
    nonzero = [index for index, sign in enumerate(signs) if sign]
    if not nonzero:
        return ()
    output: list[MonotonicSegment] = []
    start = 0
    current = signs[nonzero[0]]
    for position in nonzero[1:]:
        sign = signs[position]
        if sign != current:
            if position > start:
                output.append(MonotonicSegment(start, position, current))
            start = position
            current = sign
    end = len(values) - 1
    if end > start:
        output.append(MonotonicSegment(start, end, current))
    return tuple(output)
