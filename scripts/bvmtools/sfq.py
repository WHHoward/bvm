"""Authoritative local strict-event calculations for JoSIM phase traces.

This module is intentionally local-JJ only.  It never upgrades a local phase
trajectory into downstream reception, a closed-loop fluxoid count, or a
system Gate.
"""

from __future__ import annotations

import math
from statistics import mean, median
from typing import Sequence

from .phase import TAU, continuous_unwrap, monotonic_segments, window_indices
from .waveform import trapezoid_integral


PHI0 = 2.067833848e-15
COMPLETE_MIN_TURNS = 1.0
CLEAN_ONE_UPPER_TURNS = 1.15
DEFAULT_RESIDUAL_ABS_FLOOR_TURNS = 0.05
DEFAULT_RESIDUAL_RELATIVE = 0.10
DEFAULT_POST_RANGE_MAX_TURNS = 1.0
DEFAULT_POST_TAIL_P2P_MAX_TURNS = 0.25


def _validate_series(
    time_s: Sequence[float], phase_raw: Sequence[float], voltage_v: Sequence[float]
) -> None:
    if len(time_s) != len(phase_raw) or len(time_s) != len(voltage_v):
        raise ValueError("time, phase, and voltage must have equal lengths")
    if len(time_s) < 2:
        raise ValueError("strict-event analysis needs at least two samples")
    if any(time_s[index + 1] <= time_s[index] for index in range(len(time_s) - 1)):
        raise ValueError("time must be strictly increasing")
    for name, values in (("time", time_s), ("phase", phase_raw), ("voltage", voltage_v)):
        if any(not math.isfinite(float(value)) for value in values):
            raise ValueError(f"{name} contains NaN or Inf")


def _phase_range_turns(values: Sequence[float]) -> float:
    return (max(values) - min(values)) / TAU


def strict_segment_metrics(
    time_s: Sequence[float],
    phase_raw: Sequence[float],
    voltage_v: Sequence[float],
    window_s: tuple[float, float],
    *,
    residual_abs_floor_turns: float = DEFAULT_RESIDUAL_ABS_FLOOR_TURNS,
    residual_relative: float = DEFAULT_RESIDUAL_RELATIVE,
) -> list[dict[str, object]]:
    """Measure every exact-sign monotonic segment inside one declared window."""

    _validate_series(time_s, phase_raw, voltage_v)
    phase_unwrapped = continuous_unwrap(phase_raw)
    selected = window_indices(time_s, *window_s)
    if len(selected) < 2:
        return []
    local_phase = [phase_unwrapped[index] for index in selected]
    records: list[dict[str, object]] = []
    for ordinal, segment in enumerate(monotonic_segments(local_phase), start=1):
        indices = selected[segment.start_index : segment.end_index + 1]
        start = indices[0]
        end = indices[-1]
        delta_turns = (phase_unwrapped[end] - phase_unwrapped[start]) / TAU
        area_turns = trapezoid_integral(
            [voltage_v[index] for index in indices],
            [time_s[index] for index in indices],
        ) / PHI0
        residual = delta_turns - area_turns
        tolerance = max(residual_abs_floor_turns, residual_relative * abs(delta_turns))
        phase_candidate = abs(delta_turns) >= COMPLETE_MIN_TURNS
        area_consistent = bool(
            phase_candidate
            and delta_turns * area_turns > 0.0
            and abs(residual) <= tolerance
        )
        records.append({
            "ordinal": ordinal,
            "start_index": start,
            "end_index": end,
            "start_time_s": time_s[start],
            "end_time_s": time_s[end],
            "start_time_ps": time_s[start] * 1.0e12,
            "end_time_ps": time_s[end] * 1.0e12,
            "duration_s": time_s[end] - time_s[start],
            "duration_ps": (time_s[end] - time_s[start]) * 1.0e12,
            "direction": segment.direction,
            "delta_rad": phase_unwrapped[end] - phase_unwrapped[start],
            "delta_turns": delta_turns,
            "area_wb": area_turns * PHI0,
            "area_turns": area_turns,
            "phase_area_residual_turns": residual,
            "area_minus_phase_turns": area_turns - delta_turns,
            "residual_tolerance_turns": tolerance,
            "phase_candidate": phase_candidate,
            "area_consistent": area_consistent,
            "complete_event_units": int(math.floor(abs(delta_turns))) if area_consistent else 0,
        })
    return records


def _post_boundedness(
    time_s: Sequence[float],
    phase_unwrapped: Sequence[float],
    post_segments: Sequence[dict[str, object]],
    post_window_s: tuple[float, float],
    post_tail_window_s: tuple[float, float],
    *,
    post_range_max_turns: float,
    post_tail_p2p_max_turns: float,
) -> dict[str, object]:
    post = window_indices(time_s, *post_window_s)
    tail = window_indices(time_s, *post_tail_window_s)
    if len(post) < 2 or len(tail) < 2:
        return {
            "status": "INCONCLUSIVE",
            "bounded": None,
            "reason": "post or post-tail window has fewer than two samples",
            "post_complete_segment_count": sum(
                bool(item["area_consistent"]) for item in post_segments
            ),
        }
    post_range = _phase_range_turns([phase_unwrapped[index] for index in post])
    tail_range = _phase_range_turns([phase_unwrapped[index] for index in tail])
    post_complete = sum(bool(item["area_consistent"]) for item in post_segments)
    bounded = bool(
        post_complete == 0
        and post_range <= post_range_max_turns
        and tail_range <= post_tail_p2p_max_turns
    )
    return {
        "status": "VALID",
        "bounded": bounded,
        "post_window_s": list(post_window_s),
        "post_tail_window_s": list(post_tail_window_s),
        "post_phase_range_turns": post_range,
        "post_tail_p2p_turns": tail_range,
        "post_complete_segment_count": post_complete,
        "retrap_gate": tail_range <= post_tail_p2p_max_turns,
        "reason": "no post complete segment and bounded tail" if bounded else "post boundedness gate failed",
    }


def _classify(
    activity_segments: Sequence[dict[str, object]],
    post_segments: Sequence[dict[str, object]],
    post_status: dict[str, object],
) -> tuple[str, str]:
    activity_complete = [item for item in activity_segments if item["area_consistent"]]
    post_complete = [item for item in post_segments if item["area_consistent"]]
    second_present = len(activity_complete) >= 2 or bool(activity_complete and post_complete)
    if post_status["status"] != "VALID":
        return "INCONCLUSIVE", "post window unavailable"
    if second_present:
        return "MULTI_EVENT", "at least two independent complete segments"
    if not activity_complete:
        if not activity_segments:
            return "NO_EVENT", "no nonzero monotonic activity segment"
        if not bool(post_status["bounded"]):
            return "INCONCLUSIVE", "post boundedness is insufficient"
        largest = max(activity_segments, key=lambda item: abs(float(item["delta_turns"])))
        if abs(float(largest["delta_turns"])) >= COMPLETE_MIN_TURNS:
            return "INCONCLUSIVE", "one-turn phase candidate failed phase/area consistency"
        return "SUBTHRESHOLD", "no complete phase/area-consistent activity segment"
    if not bool(post_status["bounded"]):
        return "INCONCLUSIVE", "complete segment but post boundedness failed"
    event = activity_complete[0]
    if abs(float(event["delta_turns"])) <= CLEAN_ONE_UPPER_TURNS:
        return "CLEAN_ONE_SFQ_CANDIDATE", "one clean complete local segment"
    return "OVERDRIVEN_ONE_PLUS_RESIDUAL", "one complete segment above clean upper band"


def strict_event_summary(
    time_s: Sequence[float],
    phase_raw: Sequence[float],
    voltage_v: Sequence[float],
    *,
    activity_window_s: tuple[float, float],
    post_window_s: tuple[float, float] | None = None,
    post_tail_window_s: tuple[float, float] | None = None,
    residual_abs_floor_turns: float = DEFAULT_RESIDUAL_ABS_FLOOR_TURNS,
    residual_relative: float = DEFAULT_RESIDUAL_RELATIVE,
    post_range_max_turns: float = DEFAULT_POST_RANGE_MAX_TURNS,
    post_tail_p2p_max_turns: float = DEFAULT_POST_TAIL_P2P_MAX_TURNS,
) -> dict[str, object]:
    """Return local strict-event evidence with explicit boundedness status."""

    _validate_series(time_s, phase_raw, voltage_v)
    phase_unwrapped = continuous_unwrap(phase_raw)
    activity_segments = strict_segment_metrics(
        time_s,
        phase_raw,
        voltage_v,
        activity_window_s,
        residual_abs_floor_turns=residual_abs_floor_turns,
        residual_relative=residual_relative,
    )
    post_segments: list[dict[str, object]] = []
    if post_window_s is not None:
        post_segments = strict_segment_metrics(
            time_s,
            phase_raw,
            voltage_v,
            post_window_s,
            residual_abs_floor_turns=residual_abs_floor_turns,
            residual_relative=residual_relative,
        )
    if post_window_s is not None and post_tail_window_s is not None:
        post_status = _post_boundedness(
            time_s,
            phase_unwrapped,
            post_segments,
            post_window_s,
            post_tail_window_s,
            post_range_max_turns=post_range_max_turns,
            post_tail_p2p_max_turns=post_tail_p2p_max_turns,
        )
    else:
        post_status = {
            "status": "NOT_REQUESTED",
            "bounded": None,
            "reason": "post boundedness was not requested",
        }
    classification, reason = _classify(activity_segments, post_segments, post_status)
    selected = window_indices(time_s, *activity_window_s)
    window_delta = (
        (phase_unwrapped[selected[-1]] - phase_unwrapped[selected[0]]) / TAU
        if len(selected) >= 2
        else None
    )
    complete_activity = [item for item in activity_segments if item["area_consistent"]]
    complete_post = [item for item in post_segments if item["area_consistent"]]
    largest = max(activity_segments, key=lambda item: abs(float(item["delta_turns"]))) if activity_segments else None
    return {
        "mode": "strict_event_segment",
        "phase_units": "raw JoSIM radians; continuous unwrap for turns",
        "area_units": "integral(V dt) / Phi0",
        "disclaimer": (
            "Local same-JJ phase/area evidence only; WINDOW_PHASE_DISPLACEMENT "
            "is not EVENT_COUNT, and local evidence is not downstream reception "
            "or a system Gate."
        ),
        "activity_window_s": list(activity_window_s),
        "window_phase_displacement_turns": window_delta,
        "activity_segments": activity_segments,
        "post_segments": post_segments,
        "largest_monotonic_segment": largest,
        "complete_segment_count": len(complete_activity),
        "complete_event_units": sum(int(item["complete_event_units"]) for item in complete_activity),
        "post_complete_segment_count": len(complete_post),
        "second_complete_segment_present": bool(len(complete_activity) >= 2 or (complete_activity and complete_post)),
        "post_boundedness": post_status,
        "strict_classification": classification,
        "classification_reason": reason,
    }
