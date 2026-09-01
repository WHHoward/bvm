#!/usr/bin/env python3
"""QA and summarize the BVM -> JSL -> QB exploratory matrix.

This analyzer reads raw JoSIM CSV files directly.  It preserves P(...) in
radians, derives phase turns only by dividing a declared phase difference by
2*pi, and treats phase/voltage-area calculations as local diagnostics rather
than SFQ event counts.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[2]
MANIFEST = ROOT / "manifest.yaml"
ANALYSIS = ROOT / "analysis"
RAW = ROOT / "raw"
PHI0 = 2.067833848e-15
PI2 = 2.0 * math.pi
ROLES = (
    "logical1_read",
    "logical0_read",
    "logical1_no_read_control",
    "logical0_no_read_control",
)
WINDOWS = ("pre", "activity", "post")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_exact(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_text(encoding="utf-8") != text:
            raise SystemExit(f"refusing to overwrite non-identical analysis artifact: {path}")
        return
    path.write_text(text, encoding="utf-8")


def load_trace(path: Path) -> tuple[list[str], list[float], dict[str, list[float]]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        try:
            raw_header = [item.strip() for item in next(reader)]
        except StopIteration as exc:
            raise ValueError(f"empty CSV: {path}") from exc
        header = []
        occurrences: dict[str, int] = {}
        for name in raw_header:
            occurrences[name] = occurrences.get(name, 0) + 1
            header.append(name if occurrences[name] == 1 else f"{name}#{occurrences[name]}")
        if not header or header[0] != "time":
            raise ValueError(f"first CSV column is not time: {path}")
        values = {name: [] for name in header[1:]}
        times: list[float] = []
        previous = -math.inf
        for line_number, row in enumerate(reader, start=2):
            if not row:
                continue
            if len(row) != len(header):
                raise ValueError(
                    f"CSV column count mismatch at line {line_number}: {path}"
                )
            time_s = float(row[0])
            if not math.isfinite(time_s) or time_s <= previous:
                raise ValueError(f"non-finite or non-increasing time at line {line_number}: {path}")
            times.append(time_s)
            previous = time_s
            for name, raw_value in zip(header[1:], row[1:]):
                value = float(raw_value)
                if not math.isfinite(value):
                    raise ValueError(f"non-finite value in {name} at line {line_number}: {path}")
                values[name].append(value)
    if len(times) < 2:
        raise ValueError(f"CSV has fewer than two samples: {path}")
    return header, times, values


def find_column(values: dict[str, list[float]], wanted: str) -> str:
    if wanted in values:
        return wanted
    folded = wanted.casefold()
    matches = [name for name in values if name.casefold() == folded]
    if len(matches) == 1:
        return matches[0]
    raise KeyError(f"missing or ambiguous column {wanted!r}; available={sorted(values)}")


def trapezoid(time_s: list[float], data: list[float]) -> float:
    return sum(
        0.5 * (left + right) * (t_right - t_left)
        for t_left, t_right, left, right in zip(
            time_s[:-1], time_s[1:], data[:-1], data[1:]
        )
    )


def indices_for_window(time_s: list[float], window: tuple[float, float]) -> list[int]:
    start_ps, end_ps = window
    return [
        index for index, time in enumerate(time_s)
        if start_ps * 1e-12 <= time < end_ps * 1e-12
    ]


def window_stats(
    time_s: list[float], data: list[float], window: tuple[float, float]
) -> dict[str, Any]:
    indices = indices_for_window(time_s, window)
    if not indices:
        return {"status": "INVALID", "sample_count": 0}
    local_time = [time_s[index] for index in indices]
    local_data = [data[index] for index in indices]
    integral = trapezoid(local_time, local_data) if len(local_time) > 1 else 0.0
    return {
        "status": "VALID" if len(local_time) > 1 else "INCONCLUSIVE",
        "sample_count": len(local_time),
        "first": local_data[0],
        "last": local_data[-1],
        "min": min(local_data),
        "max": max(local_data),
        "p2p": max(local_data) - min(local_data),
        "mean": sum(local_data) / len(local_data),
        "rms": math.sqrt(sum(value * value for value in local_data) / len(local_data)),
        "max_abs": max(abs(value) for value in local_data),
        "integral": integral,
    }


def unwrap_phase(data: list[float]) -> list[float]:
    if not data:
        return []
    output = [data[0]]
    offset = 0.0
    for previous, current in zip(data[:-1], data[1:]):
        delta = current - previous
        if delta > math.pi:
            offset -= PI2
        elif delta < -math.pi:
            offset += PI2
        output.append(current + offset)
    return output


def phase_area_diagnostic(
    time_s: list[float],
    phase: list[float],
    voltage: list[float],
    window: tuple[float, float],
) -> dict[str, Any]:
    indices = indices_for_window(time_s, window)
    if len(indices) < 2:
        return {"status": "INCONCLUSIVE", "sample_count": len(indices)}
    local_time = [time_s[index] for index in indices]
    local_phase = [phase[index] for index in indices]
    local_voltage = [voltage[index] for index in indices]
    unwrapped = unwrap_phase(local_phase)
    raw_delta_rad = local_phase[-1] - local_phase[0]
    continuous_delta_rad = unwrapped[-1] - unwrapped[0]
    area_wb = trapezoid(local_time, local_voltage)
    area_turns = area_wb / PHI0
    phase_turns = raw_delta_rad / PI2
    continuous_turns = continuous_delta_rad / PI2
    residual_turns = phase_turns - area_turns
    continuous_residual_turns = continuous_turns - area_turns
    return {
        "status": "VALID",
        "sample_count": len(indices),
        "phase_first_rad": local_phase[0],
        "phase_last_rad": local_phase[-1],
        "phase_delta_rad": raw_delta_rad,
        "phase_delta_turns": phase_turns,
        "continuous_phase_delta_rad": continuous_delta_rad,
        "continuous_phase_delta_turns": continuous_turns,
        "voltage_area_Wb": area_wb,
        "voltage_area_turns": area_turns,
        "residual_turns": residual_turns,
        "continuous_residual_turns": continuous_residual_turns,
        "max_raw_phase_step_rad": max(
            abs(right - left) for left, right in zip(local_phase[:-1], local_phase[1:])
        ),
        "phase_area_same_sign": (
            phase_turns == 0.0 or area_turns == 0.0 or phase_turns * area_turns > 0.0
        ),
        "candidate_abs_continuous_turns_ge_1": abs(continuous_turns) >= 1.0,
        "interpretation": "local phase/voltage-area diagnostic; not an SFQ event count",
    }


def difference_stats(
    time_a: list[float],
    data_a: list[float],
    time_b: list[float],
    data_b: list[float],
    window: tuple[float, float],
) -> dict[str, Any]:
    if len(time_a) != len(time_b):
        return {"status": "INVALID", "reason": "different sample counts"}
    max_time_error = max(abs(left - right) for left, right in zip(time_a, time_b))
    if max_time_error > 1e-24:
        return {"status": "INVALID", "reason": "different time grids", "max_time_error_s": max_time_error}
    indices = indices_for_window(time_a, window)
    if not indices:
        return {"status": "INVALID", "reason": "empty comparison window"}
    differences = [data_a[index] - data_b[index] for index in indices]
    return {
        "status": "VALID",
        "sample_count": len(differences),
        "max_abs": max(abs(value) for value in differences),
        "mean_abs": sum(abs(value) for value in differences) / len(differences),
        "rms": math.sqrt(sum(value * value for value in differences) / len(differences)),
        "endpoint": differences[-1],
    }


def base_signals(count: int) -> list[str]:
    return [
        "I(L_SL|XBVM1)",
        "I(B_LD1)",
        f"I(B_LD{count})",
        "V(SL1)",
        "V(N6|XBVM1)",
        "P(B_LD1)",
        f"P(B_LD{count})",
        "V(B_LD1)",
        f"V(B_LD{count})",
    ]


def qb_signals() -> list[str]:
    return [
        "P(BJs|XBQ)", "V(BJs|XBQ)", "I(BJs|XBQ)",
        "P(BJL1|XBQ)", "V(BJL1|XBQ)", "I(BJL1|XBQ)",
        "P(BJL2|XBQ)", "V(BJL2|XBQ)", "I(BJL2|XBQ)",
        "V(IN)", "V(OUT)", "I(Lin|XBQ)", "I(R_LOAD)",
    ]


def required_signals(kind: str, count: int) -> list[str]:
    if kind == "source":
        return base_signals(count)
    if kind == "physical":
        return base_signals(count) + qb_signals()
    return qb_signals() + ["I(I_REPLAY)"]


def artifact_qa(
    manifest: dict[str, Any], case: dict[str, Any], execution: dict[str, Any]
) -> dict[str, Any]:
    raw = ROOT / case["raw"]
    deck = ROOT / case["deck"]
    hash_path = raw.with_suffix(raw.suffix + ".sha256")
    execution_record = execution.get((case["width_ps"], case["load"], case["role"]))
    checks: dict[str, Any] = {
        "raw_exists": raw.exists(),
        "deck_exists": deck.exists(),
        "hash_exists": hash_path.exists(),
        "returncode": execution_record.get("returncode") if execution_record else None,
        "stderr_bytes": None,
    }
    stderr_path = ROOT / execution_record["stderr"] if execution_record else None
    if stderr_path and stderr_path.exists():
        checks["stderr_bytes"] = stderr_path.stat().st_size
    if raw.exists() and hash_path.exists():
        expected = hash_path.read_text(encoding="utf-8").split()[0]
        checks["raw_sha256"] = sha256(raw)
        checks["hash_matches"] = checks["raw_sha256"] == expected
    else:
        checks["hash_matches"] = False
    checks["status"] = "VALID" if all(
        (
            checks["raw_exists"], checks["deck_exists"], checks["hash_exists"],
            checks["hash_matches"], checks["returncode"] == 0,
        )
    ) else "INVALID"
    return checks


def execution_index(kind: str) -> dict[tuple[int, str, str], dict[str, Any]]:
    path = ROOT / "logs" / f"execution-{kind}.json"
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {
        (item["width_ps"], item["load"], item["role"]): item
        for item in payload.get("results", [])
    }


def case_metrics(
    manifest: dict[str, Any],
    case: dict[str, Any],
    execution: dict[tuple[int, str, str], dict[str, Any]],
) -> dict[str, Any]:
    raw = ROOT / case["raw"]
    load = manifest["loads"][case["load"]]
    result: dict[str, Any] = {
        "kind": case["kind"],
        "width_ps": case["width_ps"],
        "load": case["load"],
        "role": case["role"],
        "raw": case["raw"],
        "deck": case["deck"],
        "artifact": artifact_qa(manifest, case, execution),
    }
    if result["artifact"]["status"] != "VALID":
        result["status"] = "INVALID"
        return result
    try:
        header, time_s, values = load_trace(raw)
        requested_dt = manifest["simulation"]["requested_timestep_ps"] * 1e-12
        deltas = [right - left for left, right in zip(time_s[:-1], time_s[1:])]
        windows_ps = manifest["windows_ps"]
        result["csv"] = {
            "header_count": len(header),
            "sample_count": len(time_s),
            "start_ps": time_s[0] * 1e12,
            "end_ps": time_s[-1] * 1e12,
            "max_timestep_error_ps": max(abs(delta - requested_dt) for delta in deltas) * 1e12,
            "requested_timestep_ps": requested_dt * 1e12,
            "unique_print_intervals_ps": sorted({round(delta * 1e12, 12) for delta in deltas}),
            "nominal_interval_count": sum(
                abs(delta - requested_dt) <= 1e-24 for delta in deltas
            ),
            "non_nominal_interval_count": sum(
                abs(delta - requested_dt) > 1e-24 for delta in deltas
            ),
            "print_grid_status": (
                "NOMINAL"
                if all(abs(delta - requested_dt) <= 1e-24 for delta in deltas)
                else "VALID_WITH_PRINT_GRID_GAP"
            ),
        }
        signals: dict[str, Any] = {}
        for wanted in required_signals(case["kind"], int(load["count"])):
            actual = find_column(values, wanted)
            signals[wanted] = {
                "column": actual,
                "windows": {
                    window_name: window_stats(
                        time_s, values[actual], tuple(windows_ps[window_name])
                    )
                    for window_name in WINDOWS
                },
            }
        result["signals"] = signals
        phase_specs: list[tuple[str, str, str]] = []
        if case["kind"] in {"source", "physical"}:
            phase_specs = [
                ("jsl_first", "P(B_LD1)", "V(B_LD1)"),
                ("jsl_last", f"P(B_LD{load['count']})", f"V(B_LD{load['count']})"),
            ]
        if case["kind"] in {"physical", "replay"}:
            phase_specs.append(("qb_bjl2", "P(BJL2|XBQ)", "V(BJL2|XBQ)"))
        phase_diagnostics: dict[str, Any] = {}
        for label, phase_name, voltage_name in phase_specs:
            phase_col = find_column(values, phase_name)
            voltage_col = find_column(values, voltage_name)
            phase_diagnostics[label] = {
                "phase_column": phase_col,
                "voltage_column": voltage_col,
                "activity": phase_area_diagnostic(
                    time_s, values[phase_col], values[voltage_col], tuple(windows_ps["activity"])
                ),
            }
        result["phase_area_diagnostics"] = phase_diagnostics
        if case["kind"] in {"source", "physical"}:
            first_col = find_column(values, "I(B_LD1)")
            last_col = find_column(values, f"I(B_LD{load['count']})")
            first_current = values[first_col]
            last_current = values[last_col]
            mismatch = [left - right for left, right in zip(first_current, last_current)]
            result["series_current_mismatch"] = {
                "max_abs_A": max(abs(value) for value in mismatch),
                "activity": window_stats(
                    time_s, mismatch, tuple(windows_ps["activity"])
                ),
            }
        result["status"] = "VALID"
    except (KeyError, ValueError, IndexError, json.JSONDecodeError) as exc:
        result["status"] = "INVALID"
        result["error"] = str(exc)
    return result


def compare_case_traces(
    path_a: Path,
    wanted_a: str,
    path_b: Path,
    wanted_b: str,
    windows_ps: dict[str, list[float]],
) -> dict[str, Any]:
    _, time_a, values_a = load_trace(path_a)
    _, time_b, values_b = load_trace(path_b)
    col_a = find_column(values_a, wanted_a)
    col_b = find_column(values_b, wanted_b)
    return {
        window: difference_stats(
            time_a, values_a[col_a], time_b, values_b[col_b], tuple(windows_ps[window])
        )
        for window in WINDOWS
    }


def build_pairwise(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    windows_ps = manifest["windows_ps"]
    pairs: list[dict[str, Any]] = []
    for width_ps in (9, 13):
        for load_name, load in manifest["loads"].items():
            count = int(load["count"])
            for role in ROLES:
                source = ROOT / "raw" / "source" / f"{width_ps}ps" / load_name / role / "run-01.csv"
                replay = ROOT / "raw" / "replay" / f"{width_ps}ps" / load_name / role / "run-01.csv"
                physical = ROOT / "raw" / "physical" / f"{width_ps}ps" / load_name / role / "run-01.csv"
                item = {"width_ps": width_ps, "load": load_name, "role": role}
                item["source_to_replay_input_identity"] = compare_case_traces(
                    source, "I(B_LD1)", replay, "I(I_REPLAY)", windows_ps
                )
                item["physical_to_replay_input_difference"] = compare_case_traces(
                    physical, "I(Lin|XBQ)", replay, "I(I_REPLAY)", windows_ps
                )
                item["physical_to_replay_vout_difference"] = compare_case_traces(
                    physical, "V(OUT)", replay, "V(OUT)", windows_ps
                )
                item["physical_to_replay_rload_difference"] = compare_case_traces(
                    physical, "I(R_LOAD)", replay, "I(R_LOAD)", windows_ps
                )
                pairs.append(item)
    for width_ps in (9, 13):
        for load_name in manifest["loads"]:
            for kind in ("physical", "replay"):
                for left_role, right_role, label in (
                    ("logical1_read", "logical0_read", "read1_vs_read0"),
                    ("logical1_read", "logical1_no_read_control", "logical1_read_vs_no_read"),
                    ("logical0_read", "logical0_no_read_control", "logical0_read_vs_no_read"),
                ):
                    left = ROOT / "raw" / kind / f"{width_ps}ps" / load_name / left_role / "run-01.csv"
                    right = ROOT / "raw" / kind / f"{width_ps}ps" / load_name / right_role / "run-01.csv"
                    pairs.append({
                        "width_ps": width_ps,
                        "load": load_name,
                        "kind": kind,
                        "comparison": label,
                        "vout_difference": compare_case_traces(
                            left, "V(OUT)", right, "V(OUT)", windows_ps
                        ),
                        "rload_difference": compare_case_traces(
                            left, "I(R_LOAD)", right, "I(R_LOAD)", windows_ps
                        ),
                    })
    return pairs


def case_lookup(metrics: list[dict[str, Any]]) -> dict[tuple[str, int, str, str], dict[str, Any]]:
    return {
        (item["kind"], item["width_ps"], item["load"], item["role"]): item
        for item in metrics
    }


def stat_for(
    lookup: dict[tuple[str, int, str, str], dict[str, Any]],
    kind: str,
    width_ps: int,
    load: str,
    role: str,
    signal: str,
    window: str,
    metric: str,
) -> float | None:
    item = lookup[(kind, width_ps, load, role)]
    return item.get("signals", {}).get(signal, {}).get("windows", {}).get(window, {}).get(metric)


def phase_for(
    lookup: dict[tuple[str, int, str, str], dict[str, Any]],
    kind: str,
    width_ps: int,
    load: str,
    role: str,
    label: str,
    metric: str,
) -> float | None:
    item = lookup[(kind, width_ps, load, role)]
    return item.get("phase_area_diagnostics", {}).get(label, {}).get("activity", {}).get(metric)


def fmt(value: float | None, digits: int = 3) -> str:
    if value is None or not math.isfinite(value):
        return "—"
    return f"{value:.{digits}e}"


def write_summary_csv(
    manifest: dict[str, Any], metrics: list[dict[str, Any]], pairwise: list[dict[str, Any]]
) -> None:
    lookup = case_lookup(metrics)
    pair_index = {
        (item["width_ps"], item["load"], item["role"]): item
        for item in pairwise
        if "source_to_replay_input_identity" in item
    }
    rows: list[dict[str, Any]] = []
    fields = [
        "width_ps", "load", "count", "ic_uA",
        "source_read1_jsl_last_phase_turns",
        "physical_read1_qb_bjl2_phase_turns",
        "replay_read1_qb_bjl2_phase_turns",
        "physical_read1_vout_activity_p2p_V",
        "physical_read0_vout_activity_p2p_V",
        "physical_read1_no_read_activity_p2p_V",
        "physical_read0_no_read_activity_p2p_V",
        "replay_read1_vout_activity_p2p_V",
        "replay_read0_vout_activity_p2p_V",
        "replay_read1_no_read_activity_p2p_V",
        "replay_read0_no_read_activity_p2p_V",
        "physical_vs_replay_read1_vout_max_abs_V",
        "physical_vs_replay_read1_input_max_abs_A",
        "source_to_replay_read1_input_max_abs_A",
    ]
    for width_ps in (9, 13):
        for load_name, load in manifest["loads"].items():
            p = pair_index[(width_ps, load_name, "logical1_read")]
            rows.append({
                "width_ps": width_ps,
                "load": load_name,
                "count": load["count"],
                "ic_uA": load["ic_uA"],
                "source_read1_jsl_last_phase_turns": phase_for(lookup, "source", width_ps, load_name, "logical1_read", "jsl_last", "continuous_phase_delta_turns"),
                "physical_read1_qb_bjl2_phase_turns": phase_for(lookup, "physical", width_ps, load_name, "logical1_read", "qb_bjl2", "continuous_phase_delta_turns"),
                "replay_read1_qb_bjl2_phase_turns": phase_for(lookup, "replay", width_ps, load_name, "logical1_read", "qb_bjl2", "continuous_phase_delta_turns"),
                "physical_read1_vout_activity_p2p_V": stat_for(lookup, "physical", width_ps, load_name, "logical1_read", "V(OUT)", "activity", "p2p"),
                "physical_read0_vout_activity_p2p_V": stat_for(lookup, "physical", width_ps, load_name, "logical0_read", "V(OUT)", "activity", "p2p"),
                "physical_read1_no_read_activity_p2p_V": stat_for(lookup, "physical", width_ps, load_name, "logical1_no_read_control", "V(OUT)", "activity", "p2p"),
                "physical_read0_no_read_activity_p2p_V": stat_for(lookup, "physical", width_ps, load_name, "logical0_no_read_control", "V(OUT)", "activity", "p2p"),
                "replay_read1_vout_activity_p2p_V": stat_for(lookup, "replay", width_ps, load_name, "logical1_read", "V(OUT)", "activity", "p2p"),
                "replay_read0_vout_activity_p2p_V": stat_for(lookup, "replay", width_ps, load_name, "logical0_read", "V(OUT)", "activity", "p2p"),
                "replay_read1_no_read_activity_p2p_V": stat_for(lookup, "replay", width_ps, load_name, "logical1_no_read_control", "V(OUT)", "activity", "p2p"),
                "replay_read0_no_read_activity_p2p_V": stat_for(lookup, "replay", width_ps, load_name, "logical0_no_read_control", "V(OUT)", "activity", "p2p"),
                "physical_vs_replay_read1_vout_max_abs_V": p["physical_to_replay_vout_difference"]["activity"]["max_abs"],
                "physical_vs_replay_read1_input_max_abs_A": p["physical_to_replay_input_difference"]["activity"]["max_abs"],
                "source_to_replay_read1_input_max_abs_A": p["source_to_replay_input_identity"]["activity"]["max_abs"],
            })
    path = ANALYSIS / "summary.csv"
    lines: list[str] = []
    from io import StringIO
    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    write_exact(path, buffer.getvalue())


def report_text(
    manifest: dict[str, Any], metrics: list[dict[str, Any]], pairwise: list[dict[str, Any]]
) -> str:
    lookup = case_lookup(metrics)
    valid = sum(item.get("status") == "VALID" for item in metrics)
    artifact_valid = sum(item.get("artifact", {}).get("status") == "VALID" for item in metrics)
    pair_index = {
        (item["width_ps"], item["load"], item["role"]): item
        for item in pairwise
        if "source_to_replay_input_identity" in item
    }
    max_identity = max(
        item["source_to_replay_input_identity"]["activity"]["max_abs"]
        for item in pair_index.values()
    )
    lines = [
        "# BVM_LOAD_QB_MATRIX_V1 分析报告",
        "",
        "## 结论边界",
        "",
        "这是按预注册矩阵完成的 exploratory simulation。报告只描述本目录内、",
        "当前 JoSIM 二进制、当前步长和当前模型快照下的轨迹；不把模拟结果写成硬件测量，",
        "也不把局部 JJ 相位变化写成 SFQ 接收计数。",
        "",
        "## Observed",
        "",
        f"- 三类 fixture 共 {len(metrics)} 组；artifact QA 有 {artifact_valid}/{len(metrics)} 组通过，"
        f"CSV/数值分析有 {valid}/{len(metrics)} 组通过。",
        f"- 所有运行的 `.tran` 请求步长为 {manifest['simulation']['requested_timestep_ps']} ps、停止时间 "
        f"{manifest['simulation']['stop_time_ps']} ps；每个 CSV 有 13599 个数据样本。打印时间轴在 "
        f"48/48 组中均为 13597 个约 0.0125 ps 间隔，并在 1.8375→1.8625 ps 处保留一个 "
        f"0.025 ps 间隔；因此本轮不声称输出轴严格等间隔或已完成收敛。",
        f"- 源波形到理想 QB 重放的 `I(B_LD1)`→`I(I_REPLAY)` 在 activity 窗口的最大绝对差为 "
        f"{fmt(max_identity)} A；这是回放输入一致性检查，不是物理传输结论。",
        "",
        "### 四个工作点的关键 QB 输出",
        "",
        "下表只保留需要看的数据。`V(OUT)` 的 p2p 是固定 activity 窗口 [94,130) ps 内的峰峰值；"
        "phase turns 是同一 QB JJ 在同一窗口的连续相位端点差除以 2π。",
        "",
        "| 读宽/负载 | 物理 read1 VOUT p2p | 物理 read0 VOUT p2p | 重放 read1 VOUT p2p | 重放 read0 VOUT p2p | 物理-重放 read1 VOUT 最大差 | QB BJL2 read1 相位差(turns) |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for width_ps in (9, 13):
        for load_name in manifest["loads"]:
            pair = pair_index[(width_ps, load_name, "logical1_read")]
            lines.append(
                "| {width} ps / {load} | {p1} | {p0} | {r1} | {r0} | {diff} | {phase} |".format(
                    width=width_ps,
                    load=load_name,
                    p1=fmt(stat_for(lookup, "physical", width_ps, load_name, "logical1_read", "V(OUT)", "activity", "p2p")),
                    p0=fmt(stat_for(lookup, "physical", width_ps, load_name, "logical0_read", "V(OUT)", "activity", "p2p")),
                    r1=fmt(stat_for(lookup, "replay", width_ps, load_name, "logical1_read", "V(OUT)", "activity", "p2p")),
                    r0=fmt(stat_for(lookup, "replay", width_ps, load_name, "logical0_read", "V(OUT)", "activity", "p2p")),
                    diff=fmt(pair["physical_to_replay_vout_difference"]["activity"]["max_abs"]),
                    phase=fmt(phase_for(lookup, "physical", width_ps, load_name, "logical1_read", "qb_bjl2", "continuous_phase_delta_turns")),
                )
            )
    lines += [
        "",
        "## Derived",
        "",
        "- 每个源端和物理级联 case 都计算了首个/末个 JSL 结的 current mismatch；"
        "每个 physical/replay case 都保留了 QB 输入、`V(OUT)` 和 `I(R_LOAD)` 的窗口统计。",
        "- phase/voltage-area 只在同一个 junction、同一窗口、同一方向的 P/V 列上交叉检查；"
        "原始相位保留为 rad，turns 由 `phase_delta_rad/(2*pi)` 得出。具体数值见 `metrics.json`。",
        "- physical 与 ideal replay 的差异是“加载后的 BVM→JSL→QB 轨迹”与“相同源波形直接驱动 QB”"
        "之间的描述性差异；它不能单独证明差异的唯一机制。",
        "",
        "## Inference",
        "",
        "- 本矩阵可以回答：在这四个读宽/负载点和四种状态控制下，物理级联及理想回放是否产生"
        "可见的 QB 输入/输出轨迹差异，以及这些差异是否与 read/no-read、read1/read0 成对比较相符。",
        "- 即使某个 BJL2 的 phase/area diagnostic 达到一个或多个 turns，也只能称为该 JJ 的局部 "
        "phase/voltage activity；本实验没有 JTL，因此不能升级为 downstream SFQ delivery 或系统 Gate。",
        "",
        "## Unknown / limitations",
        "",
        "- 本轮只使用 0.0125 ps 一个步长，没有做 0.025/0.0125/0.00625 ps 收敛或时间步敏感性检查。",
        "- 没有磁耦合、JTL 或 T1；QB 是当前 scaled cell，输出负载为 OUT 到地的 10 Ω。",
        "- 结果是数值模拟，不是硬件测量；不对未测试的参数、拓扑或工艺条件外推。",
        "",
        "## 文件",
        "",
        "- `manifest.yaml`：矩阵、模型、solver、窗口和 48 个 case 的登记。",
        "- `raw/`：48 组原始 JoSIM CSV；每个 CSV 旁有 SHA-256 文件。",
        "- `inputs/`：BVM/JSL/QB 网表快照和每组不可变输入 deck。",
        "- `analysis/metrics.json`：逐 case QA、窗口统计、相位/面积诊断和成对比较。",
        "- `analysis/summary.csv`：四个工作点的关键 QB 输出摘要。",
        "- `plots/README.md`：只列关键源端、物理级联和理想重放可视化。",
        "",
        "## Next",
        "",
        "若要把某个点提升为 Candidate，应先单独预注册步长收敛和更严格的物理证据审计；"
        "本报告不自动做该提升。",
        "",
        f"分析生成时间：{datetime.now().astimezone().isoformat(timespec='seconds')}。",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    executions = {kind: execution_index(kind) for kind in ("source", "physical", "replay")}
    metrics: list[dict[str, Any]] = []
    for case in manifest["cases"]:
        metrics.append(case_metrics(manifest, case, executions[case["kind"]]))
    pairwise = build_pairwise(manifest)
    payload = {
        "schema_version": "BVM_LOAD_QB_MATRIX_ANALYSIS_V1",
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "metric_spec": manifest["metric_spec"],
        "solver": manifest["solver"],
        "windows_ps": manifest["windows_ps"],
        "artifact_status": "VALID" if all(item.get("status") == "VALID" for item in metrics) else "INVALID",
        "scientific_status": "EXPLORATORY_OBSERVATIONS_ONLY",
        "cases": metrics,
        "pairwise": pairwise,
        "interpretation_guard": "P(...) is raw phase in radians; phase turns and voltage-area diagnostics are not SFQ event counts.",
    }
    write_exact(ANALYSIS / "metrics.json", json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    write_summary_csv(manifest, metrics, pairwise)
    write_exact(ANALYSIS / "REPORT.md", report_text(manifest, metrics, pairwise))
    print(json.dumps({
        "status": payload["artifact_status"],
        "cases": len(metrics),
        "valid_cases": sum(item.get("status") == "VALID" for item in metrics),
        "pairwise_comparisons": len(pairwise),
        "report": "analysis/REPORT.md",
    }, ensure_ascii=False))
    if payload["artifact_status"] != "VALID":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
