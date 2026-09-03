"""Shared, task-neutral measurement facts for JoSIM traces.

This module deliberately answers only ``how is this number measured?``.
Experiment-local analyzers retain windows, tolerances, event meaning, and
scientific verdicts. All integrations use the supplied sampled time grid; no
resampling or hidden timestep assumption is introduced here.
"""

from __future__ import annotations

import math
from typing import Sequence

from .phase import TAU, phase_window_metrics, window_indices
from .sfq import PHI0, strict_segment_metrics
from .waveform import trapezoid_integral, waveform_metrics, waveform_window_metrics


def _validate_sign(value: int, name: str) -> int:
    if isinstance(value, bool) or value not in (-1, 1):
        raise ValueError(f"{name} must be +1 or -1")
    return int(value)


def _validate_pair(
    time_s: Sequence[float], values: Sequence[float], *, name: str
) -> None:
    if len(time_s) != len(values):
        raise ValueError(f"time and {name} must have equal length")
    if len(time_s) < 2:
        raise ValueError("at least two samples are required")
    if any(not math.isfinite(float(value)) for value in time_s):
        raise ValueError("time contains NaN or Inf")
    if any(not math.isfinite(float(value)) for value in values):
        raise ValueError(f"{name} contains NaN or Inf")
    if any(
        float(time_s[index + 1]) <= float(time_s[index])
        for index in range(len(time_s) - 1)
    ):
        raise ValueError("time must be strictly increasing")


def signed_integral(time_s: Sequence[float], values: Sequence[float]) -> float:
    """Integrate a signed waveform on its actual stored time grid."""

    _validate_pair(time_s, values, name="values")
    return float(trapezoid_integral(values, time_s))


def waveform_window_summary(
    time_s: Sequence[float],
    values: Sequence[float],
    window_s: tuple[float, float],
    *,
    unit: str = "raw",
) -> dict[str, float | int | str | list[float]]:
    """Return the shared waveform summary for one explicit window."""

    return waveform_window_metrics(time_s, values, window_s, unit=unit)


def phase_area_consistency(
    phase_delta_turns: float,
    voltage_area_turns: float,
    *,
    absolute_tolerance_turns: float,
    relative_tolerance: float,
    relative_scale_floor_turns: float = 0.0,
) -> dict[str, float | bool | str]:
    """Compare same-JJ phase and voltage-area measurements.

    The tolerances and relative-scale floor are caller choices; they are not
    scientific defaults. ``voltage_area_turns`` must already be aligned to
    the declared phase/reporting direction.
    """

    phase = float(phase_delta_turns)
    area = float(voltage_area_turns)
    absolute = float(absolute_tolerance_turns)
    relative = float(relative_tolerance)
    floor = float(relative_scale_floor_turns)
    if not all(math.isfinite(value) for value in (phase, area, absolute, relative, floor)):
        raise ValueError("phase/area values and tolerances must be finite")
    if absolute < 0.0 or relative < 0.0 or floor < 0.0:
        raise ValueError("phase/area tolerances must be nonnegative")

    residual = phase - area
    tolerance = max(absolute, relative * max(abs(phase), abs(area), floor))
    same_sign = phase == 0.0 or area == 0.0 or phase * area > 0.0
    consistent = bool(abs(residual) <= tolerance and same_sign)
    return {
        "phase_delta_turns": phase,
        "voltage_area_turns": area,
        "phase_area_residual_turns": residual,
        "phase_area_tolerance_turns": tolerance,
        "same_sign": same_sign,
        "phase_area_consistent": consistent,
        "tolerance_definition": "max(absolute_tolerance_turns, relative_tolerance * max(abs(phase), abs(area), relative_scale_floor_turns))",
    }


def phase_area_window(
    time_s: Sequence[float],
    phase_raw: Sequence[float],
    voltage_v: Sequence[float],
    window_s: tuple[float, float],
    *,
    voltage_to_phase_sign: int = 1,
    reporting_direction: int = 1,
    include_segments: bool = True,
) -> dict[str, object]:
    """Measure same-JJ phase displacement and voltage area in one window.

    ``phase_raw`` is JoSIM phase in radians. The returned phase displacement
    and voltage area are expressed in turns / ``Phi0`` only after conversion.
    The optional segment list is descriptive arithmetic from the shared strict
    segmentation helper; it is never an event count by itself.
    """

    _validate_pair(time_s, phase_raw, name="phase")
    if len(time_s) != len(voltage_v):
        raise ValueError("time, phase, and voltage must have equal lengths")
    voltage_sign = _validate_sign(voltage_to_phase_sign, "voltage_to_phase_sign")
    direction = _validate_sign(reporting_direction, "reporting_direction")
    indices = window_indices(time_s, *window_s)
    if len(indices) < 2:
        raise ValueError("phase/area window requires at least two samples")

    phase_metrics = phase_window_metrics(time_s, phase_raw, window_s)
    selected_times = [float(time_s[index]) for index in indices]
    selected_voltage = [float(voltage_v[index]) for index in indices]
    raw_area_wb = signed_integral(selected_times, selected_voltage)
    phase_delta_turns = direction * float(phase_metrics["endpoint_delta_turns"])
    aligned_area_wb = voltage_sign * raw_area_wb
    area_turns = direction * aligned_area_wb / PHI0
    raw_delta_rad = phase_delta_turns * TAU

    raw_min_turns = float(phase_metrics["minimum_turns"])
    raw_max_turns = float(phase_metrics["maximum_turns"])
    result: dict[str, object] = {
        "window_s": [float(window_s[0]), float(window_s[1])],
        "phase_delta_rad": raw_delta_rad,
        "phase_delta_turns": phase_delta_turns,
        "voltage_area_wb": aligned_area_wb,
        "voltage_area_over_phi0": area_turns,
        "voltage_area_turns": area_turns,
        "phase_area_residual_turns": phase_delta_turns - area_turns,
        "phase_min_turns": min(direction * raw_min_turns, direction * raw_max_turns),
        "phase_max_turns": max(direction * raw_min_turns, direction * raw_max_turns),
        "phase_p2p_turns": float(phase_metrics["p2p_turns"]),
        "sample_count": int(phase_metrics["sample_count"]),
        "window_first_s": float(selected_times[0]),
        "window_last_sample_s": float(selected_times[-1]),
        "window_first_ps": float(selected_times[0]) * 1.0e12,
        "window_last_ps": float(selected_times[-1]) * 1.0e12,
        "raw_phase_unit": "rad",
        "display_conversion": "continuous_unwrap(rad)/(2*pi)",
        "branch_orientation": {
            "voltage_to_phase_sign": voltage_sign,
            "reporting_direction": direction,
            "description": "direct same-JJ P/V mapping with explicit sign conventions",
        },
    }
    if include_segments:
        segments = strict_segment_metrics(time_s, phase_raw, voltage_v, window_s)
        result["segment_diagnostic"] = {
            "method": "bvmtools.sfq.strict_segment_metrics",
            "classification": "DESCRIPTIVE_ONLY_NO_TASK_LOCAL_STRICT_TOLERANCE",
            "segment_count": len(segments),
            "largest_abs_segment_turns": max(
                (abs(float(item["phase_reported_turns"])) for item in segments),
                default=0.0,
            ),
            "any_segment_spans_over_1_15_turns": any(
                abs(float(item["phase_reported_turns"])) > 1.15 for item in segments
            ),
            "continuous_multiturn_running_descriptive": any(
                abs(float(item["phase_reported_turns"])) > 1.15 for item in segments
            ),
            "segments": segments,
        }
    return result


def burst_total_metrics(
    time_s: Sequence[float],
    phase_raw: Sequence[float],
    voltage_v: Sequence[float],
    window_s: tuple[float, float],
    *,
    absolute_tolerance_turns: float | None = None,
    relative_tolerance: float | None = None,
    relative_scale_floor_turns: float = 0.0,
    voltage_to_phase_sign: int = 1,
    reporting_direction: int = 1,
) -> dict[str, object]:
    """Return burst-total phase/area facts, with optional consistency.

    This helper intentionally does not return an SFQ count. A task may use
    these facts together with its own event/transport semantics.
    """

    result = phase_area_window(
        time_s,
        phase_raw,
        voltage_v,
        window_s,
        voltage_to_phase_sign=voltage_to_phase_sign,
        reporting_direction=reporting_direction,
    )
    if (absolute_tolerance_turns is None) != (relative_tolerance is None):
        raise ValueError("both consistency tolerances must be supplied together")
    if absolute_tolerance_turns is not None and relative_tolerance is not None:
        result["phase_area_consistency"] = phase_area_consistency(
            float(result["phase_delta_turns"]),
            float(result["voltage_area_over_phi0"]),
            absolute_tolerance_turns=absolute_tolerance_turns,
            relative_tolerance=relative_tolerance,
            relative_scale_floor_turns=relative_scale_floor_turns,
        )
    return result


def peak_timing_metrics(
    time_s: Sequence[float],
    values: Sequence[float],
    window_s: tuple[float, float],
    *,
    unit: str = "raw",
) -> dict[str, object]:
    """Return peak and timing descriptors for one explicit window."""

    _validate_pair(time_s, values, name="values")
    indices = window_indices(time_s, *window_s)
    if len(indices) < 2:
        raise ValueError("peak/timing window requires at least two samples")
    selected_times = [float(time_s[index]) for index in indices]
    selected_values = [float(values[index]) for index in indices]
    summary = waveform_metrics(selected_times, selected_values)
    peak_abs_index = max(
        range(len(selected_values)), key=lambda index: abs(selected_values[index])
    )
    if unit == "A":
        factor = 1.0e6
        display_unit = "uA"
    elif unit == "V":
        factor = 1.0e3
        display_unit = "mV"
    elif unit == "raw":
        factor = 1.0
        display_unit = "raw"
    else:
        raise ValueError("unit must be 'A', 'V', or 'raw'")
    return {
        "unit": display_unit,
        "window_s": [float(window_s[0]), float(window_s[1])],
        "sample_count": int(summary["sample_count"]),
        "minimum": float(summary["minimum"]) * factor,
        "maximum": float(summary["maximum"]) * factor,
        "p2p": float(summary["p2p"]) * factor,
        "rms": float(summary["rms"]) * factor,
        "signed_time_integral": float(summary["signed_time_integral"]),
        "peak_value": float(summary["peak_value"]) * factor,
        "peak_time_s": float(summary["peak_time"]),
        "peak_abs_value": abs(selected_values[peak_abs_index]) * factor,
        "peak_abs_time_s": selected_times[peak_abs_index],
        "peak_abs_signed_value": selected_values[peak_abs_index] * factor,
        "window_first_s": selected_times[0],
        "window_last_sample_s": selected_times[-1],
    }
