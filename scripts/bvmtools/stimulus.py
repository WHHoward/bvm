"""Task-neutral stimulus plateau measurement and protocol validation."""

from __future__ import annotations

import math
from typing import Mapping, Sequence

from .compare import compare_windowed_series
from .phase import window_indices
from .waveform import waveform_window_metrics


def _values(source: object, label: str) -> Sequence[float]:
    if hasattr(source, "column"):
        return source.column(label)  # type: ignore[no-any-return,attr-defined]
    if isinstance(source, Mapping):
        try:
            return source[label]  # type: ignore[index,return-value]
        except KeyError as exc:
            raise KeyError(f"missing stimulus label {label!r}") from exc
    raise TypeError("source must provide column(label) or be a mapping")


def _display_factor(unit: str) -> tuple[float, str]:
    if unit == "A":
        return 1.0e6, "uA"
    if unit == "V":
        return 1.0e3, "mV"
    if unit == "raw":
        return 1.0, "raw"
    raise ValueError("unit must be 'A', 'V', or 'raw'")


def plateau_metrics(
    time_s: Sequence[float],
    values: Sequence[float],
    window_s: tuple[float, float],
    *,
    unit: str = "A",
) -> dict[str, float | int | str | list[float]]:
    """Measure one declared plateau using shared waveform arithmetic."""

    return waveform_window_metrics(time_s, values, window_s, unit=unit)


def validate_expected_plateau(
    time_s: Sequence[float],
    values: Sequence[float],
    window_s: tuple[float, float],
    expected_value: float,
    *,
    tolerance: float,
    unit: str = "A",
) -> dict[str, object]:
    """Validate a plateau against an explicit SI expected value/tolerance."""

    expected = float(expected_value)
    allowed = float(tolerance)
    if not math.isfinite(expected) or not math.isfinite(allowed) or allowed < 0.0:
        raise ValueError("expected_value must be finite and tolerance nonnegative")
    # Delegate finite-value, monotonic-grid, and minimum-window validation to
    # the shared waveform implementation before inspecting the selected data.
    plateau_metrics(time_s, values, window_s, unit=unit)
    indices = window_indices(time_s, *window_s)
    if len(indices) < 2:
        raise ValueError("plateau window requires at least two samples")
    selected = [float(values[index]) for index in indices]
    max_error = max(abs(value - expected) for value in selected)
    factor, display_unit = _display_factor(unit)
    return {
        "status": "PASS" if max_error <= allowed else "MISMATCH",
        "unit": display_unit,
        "window_s": [float(window_s[0]), float(window_s[1])],
        "sample_count": len(selected),
        "expected_value_si": expected,
        "expected_value_display": expected * factor,
        "max_abs_error_si": max_error,
        "max_abs_error_display": max_error * factor,
        "tolerance_si": allowed,
        "tolerance_display": allowed * factor,
        "actual_min_display": min(selected) * factor,
        "actual_max_display": max(selected) * factor,
    }


def compare_stimuli(
    time_a: Sequence[float],
    signals_a: Mapping[str, Sequence[float]],
    time_b: Sequence[float],
    signals_b: Mapping[str, Sequence[float]],
    window_s: tuple[float, float],
    *,
    unit: str = "A",
) -> dict[str, object]:
    """Compare same-named stimulus traces on an explicit common window."""

    labels_a = tuple(signals_a)
    labels_b = tuple(signals_b)
    if set(labels_a) != set(labels_b):
        return {
            "status": "SIGNAL_SET_MISMATCH",
            "only_a": sorted(set(labels_a) - set(labels_b)),
            "only_b": sorted(set(labels_b) - set(labels_a)),
            "window_s": [float(window_s[0]), float(window_s[1])],
        }
    return {
        "status": "VALID",
        "window_s": [float(window_s[0]), float(window_s[1])],
        "signals": {
            label: compare_windowed_series(
                time_a,
                signals_a[label],
                time_b,
                signals_b[label],
                window_s,
                unit=unit,
            )
            for label in labels_a
        },
    }


def validate_bvm_write_read_protocol(
    source: object,
    time_s: Sequence[float],
    *,
    write_window_s: tuple[float, float],
    read_window_s: tuple[float, float],
    expected_write: Mapping[str, float],
    expected_read: Mapping[str, float],
    tolerance: float,
    unit: str = "A",
) -> dict[str, object]:
    """Validate caller-declared WRITE and READ plateau expectations.

    The function does not define BVM semantics. For example, a task must
    explicitly pass WL+BL and WL+SE expectations; a missing or wrong READ
    branch is reported as ``READ_PROTOCOL_MISMATCH``.
    """

    if not expected_write or not expected_read:
        raise ValueError("expected_write and expected_read must not be empty")
    write: dict[str, object] = {}
    read: dict[str, object] = {}
    for label, expected in expected_write.items():
        write[label] = validate_expected_plateau(
            time_s,
            _values(source, label),
            write_window_s,
            expected,
            tolerance=tolerance,
            unit=unit,
        )
    for label, expected in expected_read.items():
        read[label] = validate_expected_plateau(
            time_s,
            _values(source, label),
            read_window_s,
            expected,
            tolerance=tolerance,
            unit=unit,
        )
    write_ok = all(item["status"] == "PASS" for item in write.values())  # type: ignore[index]
    read_ok = all(item["status"] == "PASS" for item in read.values())  # type: ignore[index]
    if write_ok and read_ok:
        status = "PROTOCOL_VALID"
    elif not read_ok:
        status = "READ_PROTOCOL_MISMATCH"
    else:
        status = "WRITE_PROTOCOL_MISMATCH"
    return {
        "status": status,
        "write_window_s": [float(write_window_s[0]), float(write_window_s[1])],
        "read_window_s": [float(read_window_s[0]), float(read_window_s[1])],
        "unit": _display_factor(unit)[1],
        "write": write,
        "read": read,
        "expected_protocol_is_caller_declared": True,
    }
