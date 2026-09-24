"""Render staged BVM stimuli while applying MASK only to final read."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from config import ConfigError, STIMULUS_KEYS, format_time, load_env, parse_quantity


STAGES = (
    ("WRITE0", "WRITE0"),
    ("READ0", "READ0"),
    ("WRITE1", "WRITE1"),
    ("READ", "READ"),
)


def load_stimulus(path: str | Path) -> dict[str, str]:
    values = load_env(path, STIMULUS_KEYS)
    validate_stimulus(values)
    return values


def validate_stimulus(values: dict[str, str], stop_seconds: Decimal | None = None) -> dict[str, object]:
    intervals: list[tuple[str, Decimal, Decimal]] = []
    for prefix, _ in STAGES:
        start = parse_quantity(values[f"{prefix}_START"], label=f"{prefix}_START")
        rise = parse_quantity(values[f"{prefix}_RISE"], label=f"{prefix}_RISE")
        hold = parse_quantity(values[f"{prefix}_HOLD"], label=f"{prefix}_HOLD")
        fall = parse_quantity(values[f"{prefix}_FALL"], label=f"{prefix}_FALL")
        if start < 0 or rise <= 0 or hold < 0 or fall <= 0:
            raise ConfigError(f"{prefix}: start/hold must be nonnegative; rise/fall must be positive")
        end = start + rise + hold + fall
        intervals.append((prefix, start, end))
    for previous, current in zip(intervals, intervals[1:]):
        if current[1] < previous[2]:
            raise ConfigError(f"stimulus stages overlap: {previous[0]} ends after {current[0]} starts")
    if stop_seconds is not None and intervals[-1][2] > stop_seconds:
        raise ConfigError("FINAL READ ends after STOP")

    amplitude_keys = sorted(STIMULUS_KEYS - {
        f"{stage}_{field}" for stage, fields in {
            "WRITE0": ("START", "RISE", "HOLD", "FALL"),
            "READ0": ("START", "RISE", "HOLD", "FALL"),
            "WRITE1": ("START", "RISE", "HOLD", "FALL"),
            "READ": ("START", "RISE", "HOLD", "FALL"),
        }.items() for field in fields
    })
    for key in amplitude_keys:
        parse_quantity(values[key], label=key)
    return {
        "status": "STATIC_VALID",
        "stage_intervals_seconds": [
            {"stage": name, "start": float(start), "end": float(end)}
            for name, start, end in intervals
        ],
        "final_read_only_masked": True,
    }


def _insert_point(points: list[tuple[Decimal, str]], time: Decimal, value: str) -> None:
    if points and time < points[-1][0]:
        raise ConfigError("generated PWL times are not monotonic")
    if points and time == points[-1][0]:
        if value != points[-1][1]:
            raise ConfigError("conflicting stimulus values at the same PWL time")
        return
    points.append((time, value))


def _branch_points(
    values: dict[str, str], branch: str, final_read_active: bool, stop_seconds: Decimal
) -> list[tuple[Decimal, str]]:
    points: list[tuple[Decimal, str]] = [(Decimal(0), "0")]
    for prefix, stage in STAGES:
        start = parse_quantity(values[f"{prefix}_START"], label=f"{prefix}_START")
        rise = parse_quantity(values[f"{prefix}_RISE"], label=f"{prefix}_RISE")
        hold = parse_quantity(values[f"{prefix}_HOLD"], label=f"{prefix}_HOLD")
        fall = parse_quantity(values[f"{prefix}_FALL"], label=f"{prefix}_FALL")
        if stage == "READ":
            amp_key = f"READ_{'ACTIVE' if final_read_active else 'INACTIVE'}_{branch}"
        else:
            amp_key = f"{stage}_{branch}"
        amplitude = values[amp_key]
        _insert_point(points, start, "0")
        _insert_point(points, start + rise, amplitude)
        _insert_point(points, start + rise + hold, amplitude)
        _insert_point(points, start + rise + hold + fall, "0")
    _insert_point(points, stop_seconds, "0")
    return points


def render_stimulus(values: dict[str, str], params: dict[str, object], mask: str) -> str:
    size = int(params["ARRAY_SIZE"])
    if len(mask) != size or any(bit not in "01" for bit in mask):
        raise ConfigError(f"MASK must contain exactly {size} binary digits")
    stop = params["STOP_SECONDS"]
    assert isinstance(stop, Decimal)
    validate_stimulus(values, stop)
    lines = [f"* Generated stimulus; MASK={mask}; leftmost bit is BVM1."]
    for index, bit in enumerate(mask, 1):
        active = bit == "1"
        for branch, node in (("WL", f"WL{index}"), ("BL", f"BL{index}"), ("SE", f"SE{index}")):
            points = _branch_points(values, branch, active, stop)
            pairs = " ".join(f"{format_time(time)} {amp}" for time, amp in points)
            lines.append(f"I_{branch}{index} 0 {node} pwl({pairs})")
    return "\n".join(lines) + "\n"
