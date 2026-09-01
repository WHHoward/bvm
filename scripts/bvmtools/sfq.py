"""Local phase/area arithmetic with an explicit, task-scoped specification.

The arithmetic in this module is reusable.  A strict compatibility label is
only produced when the caller supplies a complete, hash-bound local mapping
and frozen task-local tolerances.  The module never claims downstream
reception, a closed-loop fluxoid count, or a system Gate.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field, replace
from typing import Mapping, Sequence

from .phase import TAU, continuous_unwrap, monotonic_segments, window_indices
from .waveform import trapezoid_integral


PHI0 = 2.067833848e-15
_COMPATIBILITY_PROFILE = "STRICT_EVENT_ANCHOR_COMPATIBILITY_V1"
_SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")


def _optional_text(value: object) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _optional_number(value: object) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _optional_sign(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value not in (-1, 1):
        return None
    return value


@dataclass(frozen=True)
class StrictLocalEventSpec:
    """Explicit mapping/provenance/tolerance declaration for local analysis.

    This object deliberately has no scientific defaults.  Incomplete specs
    remain useful for reporting raw arithmetic, but strict compatibility
    classification becomes ``INCONCLUSIVE`` until every required field is
    present and frozen.
    """

    id: str | None = None
    scope: str | None = None
    status: str | None = None
    mapping_status: str | None = None
    phase_column: str | None = None
    voltage_column: str | None = None
    branch_endpoints: str | None = None
    voltage_to_phase_sign: int | None = None
    reporting_direction: int | None = None
    run_id: str | None = None
    window_id: str | None = None
    raw_sha256: str | None = None
    metric_spec: Mapping[str, object] = field(default_factory=dict)
    tolerance: Mapping[str, object] = field(default_factory=dict)
    compatibility_profile: str | None = None

    @classmethod
    def from_mapping(cls, value: Mapping[str, object] | None) -> "StrictLocalEventSpec":
        raw = value if isinstance(value, Mapping) else {}
        metric_spec = raw.get("metric_spec")
        tolerance = raw.get("tolerance")
        metric = metric_spec if isinstance(metric_spec, Mapping) else {}
        tol = tolerance if isinstance(tolerance, Mapping) else {}
        return cls(
            id=_optional_text(raw.get("id")),
            scope=_optional_text(raw.get("scope")),
            status=_optional_text(raw.get("status")),
            mapping_status=_optional_text(raw.get("mapping_status")),
            phase_column=_optional_text(raw.get("phase_column")),
            voltage_column=_optional_text(raw.get("voltage_column")),
            branch_endpoints=_optional_text(raw.get("branch_endpoints")),
            voltage_to_phase_sign=_optional_sign(raw.get("voltage_to_phase_sign")),
            reporting_direction=_optional_sign(raw.get("reporting_direction")),
            run_id=_optional_text(raw.get("run_id")),
            window_id=_optional_text(raw.get("window_id")),
            raw_sha256=_optional_text(raw.get("raw_sha256")),
            metric_spec=dict(metric),
            tolerance=dict(tol),
            compatibility_profile=_optional_text(raw.get("compatibility_profile")),
        )

    @property
    def residual_abs_floor_turns(self) -> float | None:
        return _optional_number(self.tolerance.get("phase_area_residual_abs_floor_turns"))

    @property
    def residual_relative(self) -> float | None:
        return _optional_number(self.tolerance.get("phase_area_residual_relative"))

    @property
    def complete_min_turns(self) -> float | None:
        return _optional_number(self.tolerance.get("complete_min_turns"))

    @property
    def clean_upper_turns(self) -> float | None:
        return _optional_number(self.tolerance.get("clean_upper_turns"))

    @property
    def post_range_max_turns(self) -> float | None:
        return _optional_number(self.tolerance.get("post_range_max_turns"))

    @property
    def post_tail_p2p_max_turns(self) -> float | None:
        return _optional_number(self.tolerance.get("post_tail_p2p_max_turns"))

    def readiness_issues(self) -> tuple[str, ...]:
        issues: list[str] = []
        for name in (
            "id",
            "phase_column",
            "voltage_column",
            "branch_endpoints",
            "run_id",
            "window_id",
            "raw_sha256",
        ):
            if getattr(self, name) is None:
                issues.append(f"missing spec.{name}")
        if self.scope not in {"fixture", "procedure", "task-local"}:
            issues.append("spec.scope must be fixture, procedure, or task-local")
        if self.status != "FROZEN":
            issues.append("spec.status is not FROZEN")
        if self.mapping_status is None:
            issues.append("missing spec.mapping_status")
        if self.voltage_to_phase_sign not in (-1, 1):
            issues.append("spec.voltage_to_phase_sign must be +1 or -1")
        if self.reporting_direction not in (-1, 1):
            issues.append("spec.reporting_direction must be +1 or -1")
        if self.raw_sha256 is not None and _SHA256_RE.fullmatch(self.raw_sha256) is None:
            issues.append("spec.raw_sha256 must be a 64-digit SHA-256")

        metric_required = ("path", "version", "sha256")
        if any(not _optional_text(self.metric_spec.get(name)) for name in metric_required):
            issues.append("spec.metric_spec must include path, version, and sha256")
        elif _SHA256_RE.fullmatch(str(self.metric_spec["sha256"])) is None:
            issues.append("spec.metric_spec.sha256 must be a 64-digit SHA-256")

        if _optional_text(self.tolerance.get("id")) is None:
            issues.append("missing spec.tolerance.id")
        if _optional_text(self.tolerance.get("scope")) is None:
            issues.append("missing spec.tolerance.scope")
        if _optional_text(self.tolerance.get("evidence")) is None:
            issues.append("missing spec.tolerance.evidence")
        if self.tolerance.get("status") != "FROZEN":
            issues.append("spec.tolerance.status is not FROZEN")
        numeric = (
            ("phase_area_residual_abs_floor_turns", self.residual_abs_floor_turns),
            ("phase_area_residual_relative", self.residual_relative),
            ("complete_min_turns", self.complete_min_turns),
            ("clean_upper_turns", self.clean_upper_turns),
            ("post_range_max_turns", self.post_range_max_turns),
            ("post_tail_p2p_max_turns", self.post_tail_p2p_max_turns),
        )
        for name, number in numeric:
            if number is None or number < 0.0:
                issues.append(f"missing or invalid spec.tolerance.{name}")
        if self.complete_min_turns is not None and self.complete_min_turns <= 0.0:
            issues.append("spec.tolerance.complete_min_turns must be positive")
        if (
            self.clean_upper_turns is not None
            and self.complete_min_turns is not None
            and self.clean_upper_turns < self.complete_min_turns
        ):
            issues.append("spec.tolerance.clean_upper_turns must be >= complete_min_turns")
        return tuple(issues)

    @property
    def classification_ready(self) -> bool:
        return not self.readiness_issues()

    def metadata(self) -> dict[str, object]:
        return {
            "id": self.id,
            "scope": self.scope,
            "status": self.status,
            "mapping_status": self.mapping_status,
            "phase_column": self.phase_column,
            "voltage_column": self.voltage_column,
            "branch_endpoints": self.branch_endpoints,
            "voltage_to_phase_sign": self.voltage_to_phase_sign,
            "reporting_direction": self.reporting_direction,
            "run_id": self.run_id,
            "window_id": self.window_id,
            "raw_sha256": self.raw_sha256,
            "metric_spec": dict(self.metric_spec),
            "tolerance": dict(self.tolerance),
            "compatibility_profile": self.compatibility_profile,
            "readiness_issues": list(self.readiness_issues()),
        }


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


def _sign_or_one(value: int | None) -> int:
    return value if value in (-1, 1) else 1


def strict_segment_metrics(
    time_s: Sequence[float],
    phase_raw: Sequence[float],
    voltage_v: Sequence[float],
    window_s: tuple[float, float],
    *,
    spec: StrictLocalEventSpec | None = None,
) -> list[dict[str, object]]:
    """Measure exact-sign monotonic segments on an actual time grid.

    Without a complete spec this function still returns raw arithmetic, but
    ``area_consistent`` and classification-related fields are ``None`` rather
    than being decided using hidden global tolerances.
    """

    _validate_series(time_s, phase_raw, voltage_v)
    phase_unwrapped = continuous_unwrap(phase_raw)
    selected = window_indices(time_s, *window_s)
    if len(selected) < 2:
        return []
    local_phase = [phase_unwrapped[index] for index in selected]
    ready = spec is not None and spec.classification_ready
    reporting_direction = _sign_or_one(spec.reporting_direction if spec else None)
    voltage_to_phase_sign = _sign_or_one(spec.voltage_to_phase_sign if spec else None)
    records: list[dict[str, object]] = []
    for ordinal, segment in enumerate(monotonic_segments(local_phase), start=1):
        indices = selected[segment.start_index : segment.end_index + 1]
        start = indices[0]
        end = indices[-1]
        raw_delta_rad = phase_unwrapped[end] - phase_unwrapped[start]
        phase_reported_turns = reporting_direction * raw_delta_rad / TAU
        raw_area_wb = trapezoid_integral(
            [voltage_v[index] for index in indices],
            [time_s[index] for index in indices],
        )
        area_aligned_wb = voltage_to_phase_sign * raw_area_wb
        area_reported_turns = reporting_direction * area_aligned_wb / PHI0
        residual = phase_reported_turns - area_reported_turns
        if ready:
            assert spec is not None
            tolerance = max(
                float(spec.residual_abs_floor_turns),
                float(spec.residual_relative) * abs(phase_reported_turns),
            )
            phase_candidate: bool | None = abs(phase_reported_turns) >= float(spec.complete_min_turns)
            area_consistent: bool | None = bool(
                phase_candidate
                and phase_reported_turns * area_reported_turns > 0.0
                and abs(residual) <= tolerance
            )
            whole_turns: int | None = (
                int(math.floor(abs(phase_reported_turns))) if area_consistent else 0
            )
        else:
            tolerance = None
            phase_candidate = None
            area_consistent = None
            whole_turns = None
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
            "delta_rad": raw_delta_rad,
            "phase_delta_rad": raw_delta_rad,
            "phase_reported_turns": phase_reported_turns,
            "delta_turns": phase_reported_turns,
            "raw_area_wb": raw_area_wb,
            "area_wb": area_aligned_wb,
            "area_reported_turns": area_reported_turns,
            "area_turns": area_reported_turns,
            "phase_area_residual_turns": residual,
            "area_minus_phase_turns": -residual,
            "residual_tolerance_turns": tolerance,
            "phase_candidate": phase_candidate,
            "area_consistent": area_consistent,
            "whole_turns_floor_diagnostic": whole_turns,
        })
    return records


def _post_boundedness(
    time_s: Sequence[float],
    phase_unwrapped: Sequence[float],
    post_segments: Sequence[dict[str, object]],
    post_window_s: tuple[float, float],
    post_tail_window_s: tuple[float, float],
    *,
    spec: StrictLocalEventSpec,
) -> dict[str, object]:
    post = window_indices(time_s, *post_window_s)
    tail = window_indices(time_s, *post_tail_window_s)
    if not spec.classification_ready:
        return {
            "status": "INCONCLUSIVE",
            "bounded": None,
            "reason": "strict local spec is incomplete or unfrozen",
            "post_complete_segment_count": None,
        }
    if len(post) < 2 or len(tail) < 2:
        return {
            "status": "INCONCLUSIVE",
            "bounded": None,
            "reason": "post or post-tail window has fewer than two samples",
            "post_complete_segment_count": 0,
        }
    post_range = _phase_range_turns([phase_unwrapped[index] for index in post])
    tail_range = _phase_range_turns([phase_unwrapped[index] for index in tail])
    post_complete = sum(item["area_consistent"] is True for item in post_segments)
    bounded = bool(
        post_complete == 0
        and post_range <= float(spec.post_range_max_turns)
        and tail_range <= float(spec.post_tail_p2p_max_turns)
    )
    return {
        "status": "VALID",
        "bounded": bounded,
        "post_window_s": list(post_window_s),
        "post_tail_window_s": list(post_tail_window_s),
        "post_phase_range_turns": post_range,
        "post_tail_p2p_turns": tail_range,
        "post_complete_segment_count": post_complete,
        "retrap_gate": tail_range <= float(spec.post_tail_p2p_max_turns),
        "reason": "no post complete segment and bounded tail" if bounded else "post boundedness gate failed",
    }


def _compatibility_label(
    spec: StrictLocalEventSpec,
    *,
    clean: bool,
) -> str:
    if spec.compatibility_profile == _COMPATIBILITY_PROFILE:
        return "CLEAN_ONE_SFQ_CANDIDATE" if clean else "OVERDRIVEN_ONE_PLUS_RESIDUAL"
    return "ONE_COMPLETE_LOCAL_SEGMENT" if clean else "ABOVE_CLEAN_LOCAL_BAND"


def _classify(
    activity_segments: Sequence[dict[str, object]],
    post_segments: Sequence[dict[str, object]],
    post_status: dict[str, object],
    spec: StrictLocalEventSpec,
) -> tuple[str, str]:
    if not spec.classification_ready:
        issues = "; ".join(spec.readiness_issues()[:4])
        return "INCONCLUSIVE", f"strict local spec is incomplete or unfrozen: {issues}"
    activity_complete = [item for item in activity_segments if item["area_consistent"] is True]
    post_complete = [item for item in post_segments if item["area_consistent"] is True]
    second_present = len(activity_complete) >= 2 or bool(activity_complete and post_complete)
    if post_status["status"] != "VALID":
        return "INCONCLUSIVE", "post window unavailable"
    if second_present:
        return "MULTIPLE_COMPLETE_SEGMENTS", "at least two independent complete local segments"
    if not activity_complete:
        if not activity_segments:
            return "NO_NONZERO_MONOTONIC_SEGMENT", "no nonzero monotonic activity segment"
        largest = max(activity_segments, key=lambda item: abs(float(item["phase_reported_turns"])))
        if abs(float(largest["phase_reported_turns"])) >= float(spec.complete_min_turns):
            return "ONE_TURN_PHASE_CANDIDATE_NOT_AREA_CONSISTENT", "one-turn phase candidate failed phase/area consistency"
        return "SUBTHRESHOLD", "no complete phase/area-consistent activity segment"
    if not bool(post_status["bounded"]):
        return "INCONCLUSIVE", "complete segment but post boundedness failed"
    event = activity_complete[0]
    if abs(float(event["phase_reported_turns"])) <= float(spec.clean_upper_turns):
        return _compatibility_label(spec, clean=True), "one clean complete local segment"
    return _compatibility_label(spec, clean=False), "one complete segment above clean upper band"


def strict_event_summary(
    time_s: Sequence[float],
    phase_raw: Sequence[float],
    voltage_v: Sequence[float],
    *,
    activity_window_s: tuple[float, float],
    post_window_s: tuple[float, float] | None = None,
    post_tail_window_s: tuple[float, float] | None = None,
    spec: StrictLocalEventSpec | None = None,
    actual_raw_sha256: str | None = None,
    actual_metric_spec_sha256: str | None = None,
) -> dict[str, object]:
    """Return local arithmetic plus a guarded compatibility classification."""

    _validate_series(time_s, phase_raw, voltage_v)
    active_spec = spec if spec is not None else StrictLocalEventSpec()
    phase_unwrapped = continuous_unwrap(phase_raw)
    activity_segments = strict_segment_metrics(
        time_s,
        phase_raw,
        voltage_v,
        activity_window_s,
        spec=active_spec,
    )
    post_segments: list[dict[str, object]] = []
    if post_window_s is not None:
        post_segments = strict_segment_metrics(
            time_s,
            phase_raw,
            voltage_v,
            post_window_s,
            spec=active_spec,
        )
    if post_window_s is not None and post_tail_window_s is not None:
        post_status = _post_boundedness(
            time_s,
            phase_unwrapped,
            post_segments,
            post_window_s,
            post_tail_window_s,
            spec=active_spec,
        )
    else:
        post_status = {
            "status": "NOT_REQUESTED",
            "bounded": None,
            "reason": "post boundedness was not requested",
            "post_complete_segment_count": None,
        }
    raw_hash_match = None
    if active_spec.raw_sha256 is not None and actual_raw_sha256 is not None:
        raw_hash_match = active_spec.raw_sha256.casefold() == actual_raw_sha256.casefold()
    metric_spec_hash_match = None
    expected_metric_hash = active_spec.metric_spec.get("sha256")
    if expected_metric_hash is not None and actual_metric_spec_sha256 is not None:
        metric_spec_hash_match = str(expected_metric_hash).casefold() == actual_metric_spec_sha256.casefold()
    if raw_hash_match is False or metric_spec_hash_match is False:
        active_spec = replace(active_spec, status="INVALID_PROVENANCE")
    classification, reason = _classify(
        activity_segments,
        post_segments,
        post_status,
        active_spec,
    )
    selected = window_indices(time_s, *activity_window_s)
    window_delta = (
        (
            active_spec.reporting_direction
            if active_spec.reporting_direction in (-1, 1)
            else 1
        )
        * (phase_unwrapped[selected[-1]] - phase_unwrapped[selected[0]])
        / TAU
        if len(selected) >= 2
        else None
    )
    complete_activity = [item for item in activity_segments if item["area_consistent"] is True]
    complete_post = [item for item in post_segments if item["area_consistent"] is True]
    largest = (
        max(activity_segments, key=lambda item: abs(float(item["phase_reported_turns"])))
        if activity_segments
        else None
    )
    return {
        "mode": "strict_local_segment_compatibility",
        "claim_ceiling": "LOCAL_ONLY",
        "phase_units": "raw JoSIM radians; continuous unwrap for turns",
        "area_units": "integral(V dt) / Phi0 with explicit mapping signs",
        "disclaimer": (
            "Local same-JJ phase/area arithmetic only; compatibility labels are "
            "not event counts, downstream reception, or a system Gate."
        ),
        "spec": active_spec.metadata(),
        "raw_sha256_match": raw_hash_match,
        "metric_spec_sha256_match": metric_spec_hash_match,
        "activity_window_s": list(activity_window_s),
        "window_phase_displacement_turns": window_delta,
        "activity_segments": activity_segments,
        "post_segments": post_segments,
        "largest_monotonic_segment": largest,
        "complete_segment_count": len(complete_activity) if active_spec.classification_ready else None,
        "whole_turns_floor_diagnostic": (
            sum(int(item["whole_turns_floor_diagnostic"] or 0) for item in complete_activity)
            if active_spec.classification_ready
            else None
        ),
        "post_complete_segment_count": len(complete_post) if active_spec.classification_ready else None,
        "second_complete_segment_present": (
            bool(len(complete_activity) >= 2 or (complete_activity and complete_post))
            if active_spec.classification_ready
            else None
        ),
        "post_boundedness": post_status,
        "compatibility_classification": classification,
        "classification_reason": reason,
        "classification_namespace": (
            "ANCHOR_COMPATIBILITY_ONLY"
            if active_spec.compatibility_profile == _COMPATIBILITY_PROFILE
            else "LOCAL_STRICT_DIAGNOSTIC"
        ),
    }
