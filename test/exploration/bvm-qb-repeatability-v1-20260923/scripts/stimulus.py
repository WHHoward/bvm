"""Pure stimulus/timing planner for the repeatability platform."""

from __future__ import annotations

from typing import Any


def number(params: dict[str, Any], key: str) -> float:
    try:
        value = float(params[key])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"{key} must be a numeric value in ps/µA as named") from exc
    return value


def fmt_ps(value: float) -> str:
    return "0" if abs(value) < 1e-12 else f"{value:g}p"


def fmt_ua(value: float) -> str:
    return "0" if abs(value) < 1e-15 else f"{value:+g}u"


def add_pulse(points: list[tuple[float, float]], start: float, width: float,
              rise: float, fall: float, amplitude: float) -> None:
    if min(width, rise, fall) <= 0 or rise + fall >= width:
        raise ValueError("pulse requires positive width/rise/fall and rise+fall < width")
    points.extend(((start, 0.0), (start + rise, amplitude),
                   (start + width - fall, amplitude), (start + width, 0.0)))


def normalize_points(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    normalized: list[tuple[float, float]] = []
    for time_ps, value in sorted(points, key=lambda item: item[0]):
        if normalized and abs(normalized[-1][0] - time_ps) < 1e-10:
            if abs(normalized[-1][1] - value) > 1e-12:
                raise ValueError(f"conflicting PWL values at {time_ps:g} ps")
            continue
        normalized.append((time_ps, value))
    return normalized


def line_for_source(index: int, signal: str, points: list[tuple[float, float]], stop_ps: float) -> str:
    points = normalize_points(points + [(stop_ps, 0.0)])
    rendered = " ".join(f"{fmt_ps(t)} {fmt_ua(i)}" for t, i in points)
    return f"I_{signal}{index} 0 {signal}{index} pwl({rendered})"


def plan_stimulus(params: dict[str, Any]) -> dict[str, Any]:
    """Return PWL text, exact read schedule, windows, and computed STOP."""
    mode = str(params["TEST_MODE"])
    size = int(params["ARRAY_SIZE"])
    mask = str(params["MASK"])
    bit_order = str(params["BIT_ORDER"])
    source_points = {(index, signal): [(0.0, 0.0)]
                     for index in range(1, size + 1)
                     for signal in ("WL", "BL", "SE")}
    schedule: list[dict[str, Any]] = []
    pulses: list[dict[str, Any]] = []

    write_width = number(params, "WRITE_WIDTH_PS")
    write_rise = number(params, "WRITE_RISE_PS")
    write_fall = number(params, "WRITE_FALL_PS")
    write_amp = number(params, "WRITE_AMP_UA")
    read_width = number(params, "READ_WIDTH_PS")
    read_rise = number(params, "READ_RISE_PS")
    read_fall = number(params, "READ_FALL_PS")
    read_amp = number(params, "READ_AMP_UA")

    def pulse(index: int, signal: str, start: float, width: float,
              rise: float, fall: float, amp: float, label: str) -> None:
        add_pulse(source_points[(index, signal)], start, width, rise, fall, amp)
        pulses.append({"source": f"{signal}{index}", "label": label,
                       "start_ps": start, "end_ps": start + width,
                       "amplitude_uA": amp, "rise_ps": rise, "fall_ps": fall})

    def stage_all(label: str, start_key: str, amplitudes: dict[str, float],
                  width: float, rise: float, fall: float) -> float:
        start = number(params, start_key)
        for index in range(1, size + 1):
            for signal in ("WL", "BL", "SE"):
                pulse(index, signal, start, width, rise, fall,
                      amplitudes[signal], label)
        return start + width

    read_starts: list[float] = []
    if mode in {"REPEAT_READ", "RECOVERY_PROBE"}:
        stage_all("WRITE0", "WRITE0_START_PS",
                  {"WL": -write_amp, "BL": -write_amp, "SE": 0.0},
                  write_width, write_rise, write_fall)
        stage_all("CONTROL", "CONTROL_START_PS",
                  {"WL": number(params, "CONTROL_WL_AMP_UA"),
                   "BL": number(params, "CONTROL_BL_AMP_UA"),
                   "SE": number(params, "CONTROL_SE_AMP_UA")},
                  number(params, "CONTROL_WIDTH_PS"),
                  number(params, "CONTROL_RISE_PS"),
                  number(params, "CONTROL_FALL_PS"))
        # Preserve the existing repeated-read protocol: WRITE1 addresses all cells;
        # MASK selects which cells receive subsequent READ pulses.
        stage_all("WRITE1", "WRITE1_START_PS",
                  {"WL": write_amp, "BL": write_amp, "SE": 0.0},
                  write_width, write_rise, write_fall)
        count = int(params["READ_COUNT"])
        first = number(params, "READ_START_PS")
        period = number(params, "READ_PERIOD_PS")
        read_starts = [first + period * ordinal for ordinal in range(count)]
        for ordinal, start in enumerate(read_starts, start=1):
            for index in range(1, size + 1):
                active = mask[index - 1] == "1"
                for signal in ("WL", "BL", "SE"):
                    amp = read_amp if active and signal in ("WL", "SE") else 0.0
                    pulse(index, signal, start, read_width,
                          read_rise, read_fall, amp, f"READ{ordinal}")
            schedule.append({"ordinal": ordinal, "state": mask,
                             "read_start_ps": start,
                             "read_end_ps": start + read_width,
                             "source": "USER_CASE.env"})
    elif mode == "REWRITE_READ":
        states = [item.strip() for item in str(params["STATE_SEQUENCE"]).split(",") if item.strip()]
        reset_start = number(params, "REWRITE_START_PS")
        reset_to_write = number(params, "RESET_TO_WRITE_DELAY_PS")
        write_to_read = number(params, "WRITE_TO_READ_DELAY_PS")
        read_to_reset = number(params, "READ_TO_NEXT_RESET_DELAY_PS")
        interval = number(params, "STATE_INTERVAL_PS")
        if reset_to_write < write_width or write_to_read < write_width:
            raise ValueError("rewrite reset/write/read pulse windows must not overlap within a state")
        for ordinal, state in enumerate(states, start=1):
            write1_start = reset_start + reset_to_write
            read_start = write1_start + write_to_read
            for index in range(1, size + 1):
                one = state[index - 1] == "1"
                for signal in ("WL", "BL", "SE"):
                    reset_amp = -write_amp if signal in ("WL", "BL") else 0.0
                    write_amp_state = write_amp if one and signal in ("WL", "BL") else 0.0
                    read_amp_state = read_amp if one and signal in ("WL", "SE") else 0.0
                    pulse(index, signal, reset_start, write_width,
                          write_rise, write_fall, reset_amp,
                          f"STATE{ordinal}_WRITE0")
                    pulse(index, signal, write1_start, write_width,
                          write_rise, write_fall, write_amp_state,
                          f"STATE{ordinal}_WRITE1")
                    pulse(index, signal, read_start, read_width,
                          read_rise, read_fall, read_amp_state,
                          f"STATE{ordinal}_READ")
            read_starts.append(read_start)
            schedule.append({"ordinal": ordinal, "state": state,
                             "read_start_ps": read_start,
                             "read_end_ps": read_start + read_width,
                             "reset_start_ps": reset_start,
                             "write1_start_ps": write1_start,
                             "source": "STATE_SEQUENCE"})
            next_reset = reset_start + interval
            if read_start + read_width + read_to_reset > next_reset + 1e-9:
                raise ValueError("rewrite pulses overlap: read end plus READ_TO_NEXT_RESET exceeds STATE_INTERVAL")
            reset_start = next_reset
    else:
        raise ValueError(f"unsupported TEST_MODE {mode!r}")

    if not schedule:
        raise ValueError("the planned run has no READ schedule")
    last_stimulus_ps = max(item["read_end_ps"] for item in schedule)
    if mode == "RECOVERY_PROBE":
        stop_ps = last_stimulus_ps + number(params, "RECOVERY_TAIL_PS")
        effective_tail = number(params, "RECOVERY_TAIL_PS")
    else:
        actual_period = (read_starts[1] - read_starts[0] if len(read_starts) > 1
                         else number(params, "STATE_INTERVAL_PS") if mode == "REWRITE_READ"
                         else number(params, "READ_PERIOD_PS"))
        tail = max(number(params, "TAIL_MARGIN_MIN_PS"),
                   number(params, "TAIL_MARGIN_PERIODS") * actual_period)
        stop_ps = last_stimulus_ps + tail
        effective_tail = tail

    if stop_ps <= last_stimulus_ps:
        raise ValueError("computed STOP must be strictly later than the final stimulus endpoint")
    latency_max = number(params, "LATENCY_MAX_PS")
    if stop_ps < last_stimulus_ps + latency_max:
        raise ValueError("computed STOP truncates the registered terminal candidate search horizon")
    dt_seconds = params["_DT_SECONDS"]
    dt_ps = dt_seconds * 1e12
    if abs(stop_ps / dt_ps - round(stop_ps / dt_ps)) > 1e-8:
        raise ValueError("computed STOP is not aligned to DT")

    # Ensure every scheduled pulse is completely represented before STOP.
    if any(item["end_ps"] > stop_ps for item in pulses):
        raise ValueError("a stimulus pulse extends beyond computed STOP")

    pre_width = number(params, "PRE_WINDOW_PS")
    post_offset = number(params, "POST_OFFSET_PS")
    post_width = number(params, "POST_WINDOW_PS")
    cycles: list[dict[str, Any]] = []
    for index, item in enumerate(schedule):
        start = item["read_start_ps"]
        next_start = schedule[index + 1]["read_start_ps"] if index + 1 < len(schedule) else start + (
            read_starts[index] - read_starts[index - 1] if index else
            number(params, "STATE_INTERVAL_PS") if mode == "REWRITE_READ" else
            number(params, "READ_PERIOD_PS"))
        cycle_end = schedule[index + 1]["read_start_ps"] if index + 1 < len(schedule) else stop_ps
        pre = [start - pre_width, start]
        read = [start, item["read_end_ps"]]
        post = [item["read_end_ps"] + post_offset,
                item["read_end_ps"] + post_offset + post_width]
        next_pre = [next_start - pre_width, next_start]
        if pre[0] < 0 or next_pre[1] > stop_ps + 1e-9:
            raise ValueError("PRE/NEXT_PRE window falls outside the simulated time range")
        if post[1] > next_pre[0] + 1e-9:
            raise ValueError(f"POST and NEXT_PRE windows overlap for READ{index + 1}")
        if read[1] > cycle_end + 1e-9:
            raise ValueError(f"READ{index + 1} extends beyond its unique upstream cycle")
        cycles.append({"cycle_index": index + 1,
                       "cycle_window_ps": [start, cycle_end],
                       "cycle_window_semantics": "[start,next_read_start)" if index + 1 < len(schedule) else "[start,STOP)",
                       "pre_window_ps": pre,
                       "read_window_ps": read,
                       "post_window_ps": post,
                       "next_pre_window_ps": next_pre,
                       "next_pre_is_virtual": index + 1 == len(schedule),
                       "read_start_ps": start,
                       "read_end_ps": item["read_end_ps"],
                       "state": item["state"]})

    lines = [f"* Generated {mode} stimulus; candidate={params['CANDIDATE']}; ARRAY_SIZE={size}; MASK={mask}; {bit_order}"]
    lines.append("* Source waveform values and all transition times are resolved from the immutable config snapshot.")
    for index in range(1, size + 1):
        for signal in ("WL", "BL", "SE"):
            lines.append(line_for_source(index, signal, source_points[(index, signal)], stop_ps))
    text = "\n".join(lines) + "\n"
    return {"text": text, "schedule": schedule, "cycles": cycles,
            "read_starts_ps": read_starts,
            "last_stimulus_time_ps": last_stimulus_ps,
            "tail_margin_ps": effective_tail, "stop_ps": stop_ps,
            "source_pulse_count": len(pulses), "pulses": pulses}
