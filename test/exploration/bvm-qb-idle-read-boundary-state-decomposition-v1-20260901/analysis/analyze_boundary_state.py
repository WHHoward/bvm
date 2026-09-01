#!/usr/bin/env python3
"""Existing-raw QUICK analysis for the BVM/QB idle-read boundary.

This script intentionally does not invoke JoSIM.  It reads exactly the three
raw traces registered in experiment.yaml, uses the shared bvmtools primitives,
and writes immutable analysis artifacts into this new Exploration directory.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from statistics import median
from typing import Any

import yaml

REPO = Path(__file__).resolve().parents[4]
ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = ROOT / "analysis"
PLOTS = ROOT / "plots"
CONFIG_PATH = ROOT / "experiment.yaml"
sys.path.insert(0, str(REPO / "scripts"))

from bvmtools.compare import compare_series, exact_time_grid_identity  # noqa: E402
from bvmtools.phase import TAU, continuous_unwrap, window_indices  # noqa: E402
from bvmtools.raw import RawTrace, read_csv  # noqa: E402
from bvmtools.waveform import waveform_metrics  # noqa: E402


WINDOW_ORDER = [
    "W0_bias",
    "W1_initialization",
    "W2_settled_idle",
    "W3_read",
    "W4_post_read",
]
AC_PHASE = [
    "P(B_JM1|XBVM1)",
    "P(B_JM2|XBVM1)",
    "P(B_JS1|XBVM1)",
    "P(B_JS2|XBVM1)",
]
AC_SUPPORT = [
    "I(L_PSL|XBVM1)",
    "I(L_SL|XBVM1)",
    "I(B_LD1)",
    "I(B_LD12)",
    "V(SL1)",
]
BC_PHASE = ["P(BJS|XBQ)", "P(BJL1|XBQ)", "P(BJL2|XBQ)"]
BC_SUPPORT = ["I(L1|XBQ)", "I(LIN|XBQ)", "I(RB|XBQ)", "I(L2|XBQ)"]
PLOT_LABELS = [
    "I(grounded source · B_LD1)",
    "I(physical QB · B_LD1)",
    "P(grounded source · B_JM2)",
    "P(physical QB · B_JM2)",
    "P(ideal replay QB · BJS)",
    "P(physical QB · BJS)",
    "I(ideal replay QB · L1)",
    "I(physical QB · L1)",
    "P(ideal replay QB · BJL1)",
    "P(physical QB · BJL1)",
]


def fail(message: str) -> None:
    raise RuntimeError(message)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def repo_path(relative: str) -> Path:
    path = REPO / relative
    if not path.is_file():
        fail(f"registered file does not exist: {relative}")
    return path


def load_config() -> dict[str, Any]:
    with CONFIG_PATH.open(encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    if not isinstance(config, dict):
        fail("experiment.yaml must contain a mapping")
    if config.get("raw_execution") != "EXISTING_RAW_ONLY":
        fail("this analyzer accepts only EXISTING_RAW_ONLY")
    if config.get("joSIM_run") is not False:
        fail("this analyzer must not run JoSIM")
    return config


def case_map(config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    cases = config.get("cases")
    if not isinstance(cases, list) or len(cases) != 3:
        fail("exactly three registered cases are required")
    result: dict[str, dict[str, Any]] = {}
    for case in cases:
        if not isinstance(case, dict) or not isinstance(case.get("id"), str):
            fail("each case must have an id")
        result[case["id"]] = case
    expected = {
        "A_grounded_source_reference",
        "B_ideal_replay_qb",
        "C_physical_bvm_jsl_qb",
    }
    if set(result) != expected:
        fail(f"registered case ids differ from expected: {sorted(result)}")
    return result


def sidecar_check(csv_path: Path) -> dict[str, str]:
    actual = sha256_file(csv_path)
    sidecar = Path(str(csv_path) + ".sha256")
    if not sidecar.is_file():
        fail(f"raw sidecar is missing: {sidecar}")
    tokens = sidecar.read_text(encoding="utf-8").split()
    if not tokens or tokens[0] != actual:
        fail(f"raw sidecar hash mismatch: {csv_path}")
    return {
        "path": str(csv_path.relative_to(REPO)),
        "sha256": actual,
        "sidecar": str(sidecar.relative_to(REPO)),
    }


def select_column(trace: RawTrace, name: str, config: dict[str, Any]) -> tuple[float, ...]:
    duplicates = trace.duplicate_columns
    occurrence = config.get("duplicate_occurrence", {}).get(name)
    if duplicates.get(name, 1) > 1 and occurrence is None:
        fail(f"duplicate signal {name!r} has no registered occurrence")
    if occurrence is None:
        values = trace.column(name)
    else:
        values = trace.column(name, occurrence=occurrence)
    if not isinstance(values, tuple) or (values and isinstance(values[0], tuple)):
        fail(f"invalid selected column for {name!r}")
    return tuple(float(value) for value in values)


def window_parts(
    trace: RawTrace, window_ps: list[float] | tuple[float, float]
) -> tuple[list[float], tuple[int, ...]]:
    start_ps, end_ps = (float(window_ps[0]), float(window_ps[1]))
    indices = window_indices(trace.time, start_ps * 1e-12, end_ps * 1e-12)
    if len(indices) < 2:
        fail(f"window [{start_ps},{end_ps}) has fewer than two samples")
    return [float(trace.time[index]) for index in indices], indices


def scale_waveform(
    times: list[float], values: tuple[float, ...] | list[float], unit: str
) -> dict[str, Any]:
    base = waveform_metrics(times, values)
    if unit == "A":
        value_factor = 1e6
        area_factor = 1e18
        display_unit = "uA"
        area_unit = "uA*ps"
    elif unit == "V":
        value_factor = 1e3
        area_factor = 1e15
        display_unit = "mV"
        area_unit = "mV*ps"
    else:
        value_factor = 1.0
        area_factor = 1.0
        display_unit = unit
        area_unit = f"{unit}*s"
    result: dict[str, Any] = {
        "unit": display_unit,
        "sample_count": int(base["sample_count"]),
        "minimum": float(base["minimum"]) * value_factor,
        "maximum": float(base["maximum"]) * value_factor,
        "p2p": float(base["p2p"]) * value_factor,
        "mean": float(base["mean"]) * value_factor,
        "rms": float(base["rms"]) * value_factor,
        "max_abs": float(base["max_abs"]) * value_factor,
        "peak_value": float(base["peak_value"]) * value_factor,
        "peak_time_ps": float(base["peak_time"]) * 1e12,
        "minimum_value": float(base["minimum_value"]) * value_factor,
        "minimum_time_ps": float(base["minimum_time"]) * 1e12,
        "signed_time_integral": float(base["signed_time_integral"]) * area_factor,
        "positive_area": float(base["positive_area"]) * area_factor,
        "negative_area": float(base["negative_area"]) * area_factor,
        "area_unit": area_unit,
    }
    return result


def phase_stats(trace: RawTrace, signal: str, window: list[float], config: dict[str, Any]) -> dict[str, Any]:
    raw = select_column(trace, signal, config)
    unwrapped_turns = tuple(value / TAU for value in continuous_unwrap(raw))
    times, indices = window_parts(trace, window)
    selected = [unwrapped_turns[index] for index in indices]
    return {
        "raw_unit": "rad",
        "display_unit": "turns",
        "sample_count": len(selected),
        "median_turns": float(median(selected)),
        "minimum_turns": float(min(selected)),
        "maximum_turns": float(max(selected)),
        "p2p_turns": float(max(selected) - min(selected)),
        "endpoint_delta_turns": float(selected[-1] - selected[0]),
        "window_start_ps": float(times[0] * 1e12),
        "window_last_sample_ps": float(times[-1] * 1e12),
    }


def waveform_stats(
    trace: RawTrace, signal: str, unit: str, window: list[float], config: dict[str, Any]
) -> dict[str, Any]:
    values = select_column(trace, signal, config)
    times, indices = window_parts(trace, window)
    selected = [values[index] for index in indices]
    return scale_waveform(times, selected, unit)


def selected_series(
    trace: RawTrace, signal: str, phase: bool, window: list[float], config: dict[str, Any]
) -> tuple[list[float], list[float]]:
    raw = select_column(trace, signal, config)
    values: tuple[float, ...] = (
        tuple(value / TAU for value in continuous_unwrap(raw)) if phase else raw
    )
    times, indices = window_parts(trace, window)
    return times, [values[index] for index in indices]


def compare_window(
    left: RawTrace,
    right: RawTrace,
    signal: str,
    unit: str,
    window: list[float],
    config: dict[str, Any],
) -> dict[str, Any]:
    phase = signal.startswith("P")
    left_time, left_values = selected_series(left, signal, phase, window, config)
    right_time, right_values = selected_series(right, signal, phase, window, config)
    comparison = compare_series(
        left_time,
        left_values,
        right_time,
        right_values,
        interpolation=None,
    )
    if phase:
        factor = 1.0
        display_unit = "turns"
    elif unit == "A":
        factor = 1e6
        display_unit = "uA"
    elif unit == "V":
        factor = 1e3
        display_unit = "mV"
    else:
        factor = 1.0
        display_unit = unit
    return {
        "status": str(comparison["status"]),
        "difference_convention": "right_minus_left",
        "interpolation_mode": comparison["interpolation_mode"],
        "time_grid_exact": bool(comparison["time_grid_exact"]),
        "sample_count": int(comparison["sample_count"]),
        "max_abs_difference": float(comparison["max_abs_difference"]) * factor,
        "rms_difference": float(comparison["rms_difference"]) * factor,
        "p95_abs_difference": float(comparison["p95_abs_difference"]) * factor,
        "unit": display_unit,
    }


def compact_qa(trace: RawTrace, source_record: dict[str, str]) -> dict[str, Any]:
    qa = trace.qa()
    return {
        "path": source_record["path"],
        "sha256": source_record["sha256"],
        "sample_count": qa["sample_count"],
        "time_start_ps": float(qa["time_start"]) * 1e12,
        "time_end_ps": float(qa["time_end"]) * 1e12,
        "dt_min_ps": float(qa["dt_min"]) * 1e12,
        "dt_max_ps": float(qa["dt_max"]) * 1e12,
        "strictly_increasing_time": qa["strictly_increasing_time"],
        "nan_inf_status": qa["nan_inf_status"],
        "duplicate_columns": qa["duplicate_columns"],
    }


def duplicate_checks(trace: RawTrace) -> dict[str, Any]:
    checks: dict[str, Any] = {}
    for name, count in trace.duplicate_columns.items():
        occurrences = trace.occurrences(name)
        if count == 2:
            differences = [right - left for left, right in zip(occurrences[0], occurrences[1])]
            checks[name] = {
                "occurrences": count,
                "selected_occurrence": 0,
                "occurrence_0_vs_1_max_abs": max(abs(value) for value in differences),
                "occurrence_0_vs_1_rms": math.sqrt(
                    sum(value * value for value in differences) / len(differences)
                ),
            }
        else:
            checks[name] = {"occurrences": count, "selected_occurrence": 0}
    return checks


def build_stats(
    traces: dict[str, RawTrace],
    config: dict[str, Any],
    windows: dict[str, list[float]],
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for case_id, signals in {
        "A_grounded_source_reference": [(name, "phase") for name in AC_PHASE]
        + [(name, "A" if name.startswith("I") else "V") for name in AC_SUPPORT],
        "B_ideal_replay_qb": [(name, "phase") for name in BC_PHASE]
        + [(name, "A") for name in BC_SUPPORT],
        "C_physical_bvm_jsl_qb": [(name, "phase") for name in AC_PHASE + BC_PHASE]
        + [(name, "A" if name.startswith("I") else "V") for name in AC_SUPPORT]
        + [(name, "A") for name in BC_SUPPORT],
    }.items():
        case_result: dict[str, Any] = {}
        for signal, unit in signals:
            case_result[signal] = {}
            for window_name in WINDOW_ORDER:
                window = windows[window_name]
                if unit == "phase":
                    case_result[signal][window_name] = phase_stats(
                        traces[case_id], signal, window, config
                    )
                else:
                    case_result[signal][window_name] = waveform_stats(
                        traces[case_id], signal, unit, window, config
                    )
        result[case_id] = case_result
    return result


def build_comparisons(
    traces: dict[str, RawTrace], config: dict[str, Any], windows: dict[str, list[float]]
) -> dict[str, Any]:
    ac: dict[str, Any] = {"phase": {}, "support": {}}
    for signal in AC_PHASE:
        ac["phase"][signal] = {
            window_name: compare_window(
                traces["A_grounded_source_reference"],
                traces["C_physical_bvm_jsl_qb"],
                signal,
                "phase",
                windows[window_name],
                config,
            )
            for window_name in WINDOW_ORDER
        }
    for signal in AC_SUPPORT:
        unit = "A" if signal.startswith("I") else "V"
        ac["support"][signal] = {
            window_name: compare_window(
                traces["A_grounded_source_reference"],
                traces["C_physical_bvm_jsl_qb"],
                signal,
                unit,
                windows[window_name],
                config,
            )
            for window_name in WINDOW_ORDER
        }

    bc: dict[str, Any] = {"phase": {}, "support": {}}
    for signal in BC_PHASE:
        bc["phase"][signal] = {
            window_name: compare_window(
                traces["B_ideal_replay_qb"],
                traces["C_physical_bvm_jsl_qb"],
                signal,
                "phase",
                windows[window_name],
                config,
            )
            for window_name in ("W2_settled_idle", "W3_read")
        }
    for signal in BC_SUPPORT:
        bc["support"][signal] = {
            window_name: compare_window(
                traces["B_ideal_replay_qb"],
                traces["C_physical_bvm_jsl_qb"],
                signal,
                "A",
                windows[window_name],
                config,
            )
            for window_name in ("W2_settled_idle", "W3_read")
        }
    return {"A_vs_C": ac, "B_vs_C": bc}


def build_reference_check(
    traces: dict[str, RawTrace], config: dict[str, Any], reference_window: list[float]
) -> dict[str, Any]:
    signal = "I(B_LD1)"
    grounded = waveform_stats(
        traces["A_grounded_source_reference"], signal, "A", reference_window, config
    )
    physical = waveform_stats(
        traces["C_physical_bvm_jsl_qb"], signal, "A", reference_window, config
    )
    comparison = compare_window(
        traces["A_grounded_source_reference"],
        traces["C_physical_bvm_jsl_qb"],
        signal,
        "A",
        reference_window,
        config,
    )
    return {
        "signal": signal,
        "window_ps": reference_window,
        "grounded_source_reference": grounded,
        "physical_bvm_jsl_qb": physical,
        "comparison": comparison,
        "area_boundary": "current-time area is a waveform diagnostic, not an SFQ quantity",
    }


def write_plot(
    traces: dict[str, RawTrace], config: dict[str, Any], output: Path
) -> dict[str, Any]:
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        fail(f"refusing to overwrite existing plot: {output}")
    a = traces["A_grounded_source_reference"]
    b = traces["B_ideal_replay_qb"]
    c = traces["C_physical_bvm_jsl_qb"]
    if not exact_time_grid_identity(a.time, b.time) or not exact_time_grid_identity(a.time, c.time):
        fail("plot source traces do not have identical full time grids")
    columns: list[tuple[str, tuple[float, ...]]] = [
        (PLOT_LABELS[0], select_column(a, "I(B_LD1)", config)),
        (PLOT_LABELS[1], select_column(c, "I(B_LD1)", config)),
        (PLOT_LABELS[2], select_column(a, "P(B_JM2|XBVM1)", config)),
        (PLOT_LABELS[3], select_column(c, "P(B_JM2|XBVM1)", config)),
        (PLOT_LABELS[4], select_column(b, "P(BJS|XBQ)", config)),
        (PLOT_LABELS[5], select_column(c, "P(BJS|XBQ)", config)),
        (PLOT_LABELS[6], select_column(b, "I(L1|XBQ)", config)),
        (PLOT_LABELS[7], select_column(c, "I(L1|XBQ)", config)),
        (PLOT_LABELS[8], select_column(b, "P(BJL1|XBQ)", config)),
        (PLOT_LABELS[9], select_column(c, "P(BJL1|XBQ)", config)),
    ]
    with tempfile.TemporaryDirectory(prefix="bvm-qb-boundary-") as temp_dir:
        merged = Path(temp_dir) / "selected_key_signals.csv"
        with merged.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["time", *PLOT_LABELS])
            for index, time_value in enumerate(a.time):
                writer.writerow([time_value, *(values[index] for _, values in columns)])
        command = [
            sys.executable,
            str(REPO / "scripts/josim-plot2.py"),
            str(merged),
            "-t",
            "sep_comb",
            "-c",
            "dark",
            "-j",
            "2pi",
            "-s",
            *PLOT_LABELS,
            "-x",
            str(output),
            "-w",
            "BVM/QB idle-read boundary: selected key signals",
        ]
        completed = subprocess.run(
            command,
            cwd=REPO,
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            fail(
                "josim-plot2 failed:\n"
                + completed.stdout[-2000:]
                + "\n"
                + completed.stderr[-2000:]
            )
    if not output.is_file() or output.stat().st_size == 0:
        fail("plot command completed without a non-empty HTML output")
    html = output.read_text(encoding="utf-8")
    missing = [label for label in PLOT_LABELS if label not in html]
    if missing:
        fail(f"plot HTML is missing selected labels: {missing}")
    return {
        "path": str(output.relative_to(REPO)),
        "backend": "scripts/josim-plot2.py",
        "command_profile": "-t sep_comb -c dark -j 2pi",
        "style": "CLASSIC_LOCKED",
        "mode": "compact",
        "signal_count": len(PLOT_LABELS),
        "signals": PLOT_LABELS,
        "full_time_grid_exact": True,
    }


def fmt(value: Any, digits: int = 6) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, int):
        return str(value)
    return f"{float(value):.{digits}g}"


def stat(stats: dict[str, Any], key: str) -> Any:
    return stats[key]


def make_brief(metrics: dict[str, Any]) -> str:
    stats = metrics["window_stats"]
    comparisons = metrics["comparisons"]
    reference = metrics["historical_reference_check"]
    a_w2_jm = max(
        comparisons["A_vs_C"]["phase"][signal]["W2_settled_idle"]["max_abs_difference"]
        for signal in AC_PHASE
    )
    a_w1_phase = max(
        comparisons["A_vs_C"]["phase"][signal]["W1_initialization"]["max_abs_difference"]
        for signal in AC_PHASE
    )
    a_w3_current = comparisons["A_vs_C"]["support"]["I(B_LD1)"]["W3_read"]
    a_w2_current = comparisons["A_vs_C"]["support"]["I(B_LD1)"]["W2_settled_idle"]
    grounded_w3 = stats["A_grounded_source_reference"]["I(B_LD1)"]["W3_read"]
    physical_w3 = stats["C_physical_bvm_jsl_qb"]["I(B_LD1)"]["W3_read"]
    b_w2_bjs = stats["B_ideal_replay_qb"]["P(BJS|XBQ)"]["W2_settled_idle"]
    c_w2_bjs = stats["C_physical_bvm_jsl_qb"]["P(BJS|XBQ)"]["W2_settled_idle"]
    b_w3_bjs = stats["B_ideal_replay_qb"]["P(BJS|XBQ)"]["W3_read"]
    c_w3_bjs = stats["C_physical_bvm_jsl_qb"]["P(BJS|XBQ)"]["W3_read"]
    b_w3_bjl1 = stats["B_ideal_replay_qb"]["P(BJL1|XBQ)"]["W3_read"]
    c_w3_bjl1 = stats["C_physical_bvm_jsl_qb"]["P(BJL1|XBQ)"]["W3_read"]
    b_w2_l1 = stats["B_ideal_replay_qb"]["I(L1|XBQ)"]["W2_settled_idle"]
    c_w2_l1 = stats["C_physical_bvm_jsl_qb"]["I(L1|XBQ)"]["W2_settled_idle"]
    b_w3_lin = stats["B_ideal_replay_qb"]["I(LIN|XBQ)"]["W3_read"]
    c_w3_lin = stats["C_physical_bvm_jsl_qb"]["I(LIN|XBQ)"]["W3_read"]
    return f"""# BVM_QB_IDLE_AND_READ_BOUNDARY_STATE_DECOMPOSITION_V1

## 状态

`QUICK_AMBIGUOUS` / `INCONCLUSIVE` / `AWAITING_USER_REVIEW` / `STOP`

## 本轮改变、固定与目的

- **改变**：没有改变科学参数或拓扑；只对父矩阵中 13 ps / 12×320 /
  logical1_read 的三份既有 raw 做边界条件分解。
- **固定**：A 为 BVM→12×320 JSL→ground 的 grounded-JSL source reference；
  B 为 exact source waveform→ideal current replay→QB；C 为
  BVM→12×320 JSL→physical QB。窗口和信号登记见 `PREREGISTRATION.md`。
- **目的**：区分 QB 是否改变 BVM 的初始化/稳定存储状态，以及主要不兼容是否在
  READ 动态阶段出现。本轮没有运行 JoSIM、没有重采样、没有插值。

## 主要观察（仅保留关键数据）

1. **[OBSERVED] A↔C 的 settled idle 差异很小，初始化扰动较大但仍是有限窗观测。**
   W2 的四个 BVM phase 信号最大 exact-grid 差为
   `{fmt(a_w2_jm)} turns`，`I(B_LD1)` 最大差为 `{fmt(a_w2_current['max_abs_difference'])} uA`；
   W1 的 BVM phase 最大差为 `{fmt(a_w1_phase)} turns`。

2. **[OBSERVED] READ 时 BVM/JSL 电流轨迹明显改变。** W3 grounded reference 的
   `I(B_LD1)` 正峰为 `{fmt(grounded_w3['peak_value'])} uA`（{fmt(grounded_w3['peak_time_ps'])} ps），
   physical QB 为 `{fmt(physical_w3['peak_value'])} uA`（{fmt(physical_w3['peak_time_ps'])} ps）；
   正面积分别为 `{fmt(grounded_w3['positive_area'])}` 和 `{fmt(physical_w3['positive_area'])} uA*ps`，
   signed area 分别为 `{fmt(grounded_w3['signed_time_integral'])}` 和
   `{fmt(physical_w3['signed_time_integral'])} uA*ps`。W3 exact-grid 最大差为
   `{fmt(a_w3_current['max_abs_difference'])} uA`。这些是电流波形诊断量，不是 SFQ 计数。

3. **[OBSERVED] B↔C 的 QB pre-READ preload 接近。** W2 `BJS` median 为
   `{fmt(b_w2_bjs['median_turns'])}` 与 `{fmt(c_w2_bjs['median_turns'])} turns`，
   其 exact-grid 最大差为
   `{fmt(comparisons['B_vs_C']['phase']['P(BJS|XBQ)']['W2_settled_idle']['max_abs_difference'])} turns`；
   `L1` mean 为 `{fmt(b_w2_l1['mean'])}` 与 `{fmt(c_w2_l1['mean'])} uA`，
   exact-grid 最大差为
   `{fmt(comparisons['B_vs_C']['support']['I(L1|XBQ)']['W2_settled_idle']['max_abs_difference'])} uA`。

4. **[OBSERVED] B↔C 的主要 QB 差异出现在 READ。** W3 `BJS` p2p 为
   `{fmt(b_w3_bjs['p2p_turns'])}`（ideal replay）与 `{fmt(c_w3_bjs['p2p_turns'])} turns`（physical），
   `BJL1` p2p 为 `{fmt(b_w3_bjl1['p2p_turns'])}` 与 `{fmt(c_w3_bjl1['p2p_turns'])} turns`；
   `LIN` mean 为 `{fmt(b_w3_lin['mean'])}` 与 `{fmt(c_w3_lin['mean'])} uA`。

5. **[PHYSICS-BASED INFERENCE]** 在本固定工作点和固定窗口下，证据最符合
   “pre-READ 状态大体保留、主要不兼容在 READ 动态阶段显现”的有界描述，即 H-D
   较一致；H-A/H-B/H-C 不能被本轮数据单独确立。W4 中部分 JS phase 仍在活动，
   所以不能把它当作最终 retrapped state，也不能从 local phase turns 推出下游 SFQ。

## 不证明什么

- 不证明唯一的 backfeed、界面 preload 或 READ 机制；未观测的节点仍为 `UNKNOWN`。
- 不证明硬件测量、SFQ delivery、系统逻辑 Gate、步长收敛或普适不可行性。
- 父实验冻结的历史 `[94,130)` 核对值与本报告的 W3 `[95,110)` 不同，不能混用。

## 后续选项（本轮未执行）

1. 由用户审核本 QUICK 结果后，选择是否把某个边界差异提升为 Candidate 复核。
2. 若需要机制定位，另行预注册节点级 interface/preload 证据，不回写本轮 raw。
3. 若需要结论级主张，另行冻结 timestep/convergence 与独立证据审计。

父窗口历史核对：grounded signed/positive/negative area =
`{fmt(reference['grounded_source_reference']['signed_time_integral'])}` /
`{fmt(reference['grounded_source_reference']['positive_area'])}` /
`{fmt(reference['grounded_source_reference']['negative_area'])} uA*ps`；
physical = `{fmt(reference['physical_bvm_jsl_qb']['signed_time_integral'])}` /
`{fmt(reference['physical_bvm_jsl_qb']['positive_area'])}` /
`{fmt(reference['physical_bvm_jsl_qb']['negative_area'])} uA*ps`。
"""


def make_report(metrics: dict[str, Any]) -> str:
    stats = metrics["window_stats"]
    comparisons = metrics["comparisons"]
    reference = metrics["historical_reference_check"]
    raw_qa = metrics["raw_qa"]
    lines = [
        "# BVM_QB_IDLE_AND_READ_BOUNDARY_STATE_DECOMPOSITION_V1 分析报告",
        "",
        "## 结论边界",
        "",
        "这是对父矩阵已有 raw 的 `EXISTING_RAW_ONLY` QUICK 分析，不运行 JoSIM，不改变",
        "BVM/JSL/QB 参数或拓扑。结果是当前模型、当前单一请求步长和三个既有边界条件",
        "下的 simulation evidence，不是硬件测量。raw `P(...)` 单位为 rad；报告中的",
        "phase turns 是连续 unwrap 后除以 `2π` 的显示单位，不是 SFQ 计数。",
        "",
        "## 输入与固定窗口",
        "",
        "| Case | topology meaning | samples | time range (ps) | hash prefix |",
        "|---|---|---:|---:|---|",
    ]
    labels = {
        "A_grounded_source_reference": "A grounded-JSL source reference",
        "B_ideal_replay_qb": "B ideal current replay QB",
        "C_physical_bvm_jsl_qb": "C physical BVM/JSL/QB",
    }
    for case_id in labels:
        qa = raw_qa[case_id]
        lines.append(
            f"| {case_id} | {labels[case_id]} | {qa['sample_count']} | "
            f"[{fmt(qa['time_start_ps'])}, {fmt(qa['time_end_ps'])}] | {qa['sha256'][:12]} |"
        )
    lines.extend(
        [
            "",
            "| Window | interval (ps) | samples | meaning |",
            "|---|---:|---:|---|",
        ]
    )
    meanings = {
        "W0_bias": "QB bias established, before BVM init",
        "W1_initialization": "BVM initialization",
        "W2_settled_idle": "settled idle / stored-state",
        "W3_read": "READ",
        "W4_post_read": "post-READ settling",
    }
    for window_name in WINDOW_ORDER:
        interval = metrics["windows_ps"][window_name]
        sample_count = stats["A_grounded_source_reference"][AC_PHASE[0]][window_name]["sample_count"]
        lines.append(
            f"| {window_name} | [{fmt(interval[0])}, {fmt(interval[1])}) | {sample_count} | {meanings[window_name]} |"
        )
    lines.extend(
        [
            "",
            "A/C 与 B/C 均使用 exact-grid、无插值比较；差值定义为 `right - left`。",
            "A/C 的重复 `I(B_LD1)` 与 `I(B_LD12)` 选 occurrence 0；raw 中 occurrence 0/1",
            "的 QA 相同结果记录在 `metrics.json`。",
            "",
            "## Q1：physical QB 是否改变 BVM 状态",
            "",
            "### Observed：初始化与 settled idle",
            "",
            "| signal | W1 A→C max diff | W2 A→C max diff | W2 grounded median/mean | W2 physical median/mean | unit |",
            "|---|---:|---:|---:|---:|---|",
        ]
    )
    for signal in AC_PHASE:
        a = stats["A_grounded_source_reference"][signal]["W2_settled_idle"]
        c = stats["C_physical_bvm_jsl_qb"][signal]["W2_settled_idle"]
        lines.append(
            f"| `{signal}` | {fmt(comparisons['A_vs_C']['phase'][signal]['W1_initialization']['max_abs_difference'])} | "
            f"{fmt(comparisons['A_vs_C']['phase'][signal]['W2_settled_idle']['max_abs_difference'])} | "
            f"{fmt(a['median_turns'])} | {fmt(c['median_turns'])} | turns |"
        )
    for signal in ["I(B_LD1)", "I(B_LD12)"]:
        a = stats["A_grounded_source_reference"][signal]["W2_settled_idle"]
        c = stats["C_physical_bvm_jsl_qb"][signal]["W2_settled_idle"]
        lines.append(
            f"| `{signal}` | n/a | {fmt(comparisons['A_vs_C']['support'][signal]['W2_settled_idle']['max_abs_difference'])} | "
            f"{fmt(a['mean'])} | {fmt(c['mean'])} | uA mean |"
        )
    lines.extend(
        [
            "",
            "W2 的 BVM core phase 差异很小，W1 的有限启动扰动较大；这支持把 persistent",
            "idle-state backfeed 作为未被当前数据支持的主解释，而不是把它宣称为不可能。",
            "",
            "### Observed：READ current and BVM phase trajectory",
            "",
            "| signal | grounded W3 key statistic | physical W3 key statistic | exact-grid max diff | unit |",
            "|---|---|---|---:|---|",
        ]
    )
    for signal in ["I(B_LD1)", "I(L_PSL|XBVM1)", "I(L_SL|XBVM1)"]:
        a = stats["A_grounded_source_reference"][signal]["W3_read"]
        c = stats["C_physical_bvm_jsl_qb"][signal]["W3_read"]
        key_a = f"peak={fmt(a['peak_value'])}, rms={fmt(a['rms'])}"
        key_c = f"peak={fmt(c['peak_value'])}, rms={fmt(c['rms'])}"
        unit = "uA"
        lines.append(
            f"| `{signal}` | {key_a} | {key_c} | "
            f"{fmt(comparisons['A_vs_C']['support'][signal]['W3_read']['max_abs_difference'])} | {unit} |"
        )
    for signal in AC_PHASE:
        a = stats["A_grounded_source_reference"][signal]["W3_read"]
        c = stats["C_physical_bvm_jsl_qb"][signal]["W3_read"]
        lines.append(
            f"| `{signal}` | end Δ={fmt(a['endpoint_delta_turns'])} | end Δ={fmt(c['endpoint_delta_turns'])} | "
            f"{fmt(comparisons['A_vs_C']['phase'][signal]['W3_read']['max_abs_difference'])} | turns |"
        )
    lines.extend(
        [
            "",
            "### W3 `I(B_LD1)` required waveform diagnostics",
            "",
            "| condition | positive peak (uA) | peak time (ps) | positive area (uA*ps) | negative area (uA*ps) | signed area (uA*ps) | RMS (uA) |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for case_id in ["A_grounded_source_reference", "C_physical_bvm_jsl_qb"]:
        item = stats[case_id]["I(B_LD1)"]["W3_read"]
        lines.append(
            f"| {labels[case_id]} | {fmt(item['peak_value'])} | {fmt(item['peak_time_ps'])} | "
            f"{fmt(item['positive_area'])} | {fmt(item['negative_area'])} | "
            f"{fmt(item['signed_time_integral'])} | {fmt(item['rms'])} |"
        )
    lines.extend(
        [
            "",
            "这里的面积是电流对时间的 waveform diagnostic；不命名为 SFQ area，也不从它",
            "单独推导 SFQ 接收。W4 的 JS1/JS2 仍有显著 phase activity，因此 W4 不能被当作",
            "最终静止态；W4 统计仍完整保存在机器可读指标中。",
            "",
            "## Q2：QB 是 preloaded 还是在 READ 才发生主要差异",
            "",
            "### Observed：W2 pre-READ",
            "",
            "| QB signal | ideal replay (median / p2p) | physical (median / p2p) | exact-grid max diff | unit/stat |",
            "|---|---:|---:|---:|---|",
        ]
    )
    for signal in BC_PHASE:
        b = stats["B_ideal_replay_qb"][signal]["W2_settled_idle"]
        c = stats["C_physical_bvm_jsl_qb"][signal]["W2_settled_idle"]
        lines.append(
            f"| `{signal}` | {fmt(b['median_turns'])} / {fmt(b['p2p_turns'])} | "
            f"{fmt(c['median_turns'])} / {fmt(c['p2p_turns'])} | "
            f"{fmt(comparisons['B_vs_C']['phase'][signal]['W2_settled_idle']['max_abs_difference'])} | median turns |"
        )
    for signal in BC_SUPPORT:
        b = stats["B_ideal_replay_qb"][signal]["W2_settled_idle"]
        c = stats["C_physical_bvm_jsl_qb"][signal]["W2_settled_idle"]
        lines.append(
            f"| `{signal}` | {fmt(b['mean'])} / {fmt(b['p2p'])} / {fmt(b['rms'])} / {fmt(b['max_abs'])} | "
            f"{fmt(c['mean'])} / {fmt(c['p2p'])} / {fmt(c['rms'])} / {fmt(c['max_abs'])} | "
            f"{fmt(comparisons['B_vs_C']['support'][signal]['W2_settled_idle']['max_abs_difference'])} | "
            f"mean / p2p / RMS / maxabs uA |"
        )
    lines.extend(
        [
            "",
            "W2 的 `RB` 两侧均为固定 35 uA；其它 QB current 的 exact-grid 最大差不超过",
            f"{fmt(max(comparisons['B_vs_C']['support'][s]['W2_settled_idle']['max_abs_difference'] for s in BC_SUPPORT))} uA。",
            "",
            "### Observed：W3 READ",
            "",
            "| QB signal | ideal replay W3 median / p2p | physical W3 median / p2p | exact-grid max diff | unit/stat |",
            "|---|---:|---:|---:|---|",
        ]
    )
    for signal in BC_PHASE:
        b = stats["B_ideal_replay_qb"][signal]["W3_read"]
        c = stats["C_physical_bvm_jsl_qb"][signal]["W3_read"]
        lines.append(
            f"| `{signal}` | {fmt(b['median_turns'])} / {fmt(b['p2p_turns'])} | "
            f"{fmt(c['median_turns'])} / {fmt(c['p2p_turns'])} | "
            f"{fmt(comparisons['B_vs_C']['phase'][signal]['W3_read']['max_abs_difference'])} | turns |"
        )
    for signal in BC_SUPPORT:
        b = stats["B_ideal_replay_qb"][signal]["W3_read"]
        c = stats["C_physical_bvm_jsl_qb"][signal]["W3_read"]
        lines.append(
            f"| `{signal}` | {fmt(b['mean'])} / {fmt(b['p2p'])} / {fmt(b['rms'])} / {fmt(b['max_abs'])} | "
            f"{fmt(c['mean'])} / {fmt(c['p2p'])} / {fmt(c['rms'])} / {fmt(c['max_abs'])} | "
            f"{fmt(comparisons['B_vs_C']['support'][signal]['W3_read']['max_abs_difference'])} | "
            f"mean / p2p / RMS / maxabs uA |"
        )
    lines.extend(
        [
            "",
            "## Hypothesis disposition",
            "",
            "| hypothesis | bounded disposition | evidence label |",
            "|---|---|---|",
            "| H-A persistent QB-bias backfeed changes BVM idle state | W2 BVM core差异小，主导解释未获支持；不能排除未观测节点的有限 backfeed | OBSERVED + UNKNOWN |",
            "| H-B QB mainly changes initialization and leaves persistent stored-state difference | W1 有限扰动，但 W2 未见同量级 persistent core shift | OBSERVED / INCONCLUSIVE |",
            "| H-C BVM stored state preserved but interface preload differs | W2 已测 QB internal preload 接近；未测界面节点仍未知 | OBSERVED + UNKNOWN |",
            "| H-D pre-READ approximately preserved, dominant incompatibility during READ | 与 W2 接近、W3 分叉的 pattern 最一致；不是唯一机制证明 | PHYSICS-BASED INFERENCE |",
            "",
            "## Frozen historical reference check",
            "",
            "该表使用预注册的 `[94,130)` ps，而不是 W3 `[95,110)` ps：",
            "",
            "| condition | positive area | negative area | signed area | peak time | max diff vs other | RMS diff vs other |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for case_id in ["A_grounded_source_reference", "C_physical_bvm_jsl_qb"]:
        item = reference["grounded_source_reference"] if case_id.startswith("A_") else reference["physical_bvm_jsl_qb"]
        lines.append(
            f"| {labels[case_id]} | {fmt(item['positive_area'])} | {fmt(item['negative_area'])} | "
            f"{fmt(item['signed_time_integral'])} | {fmt(item['peak_time_ps'])} | — | — |"
        )
    comparison = reference["comparison"]
    lines.append(
        f"| A→C exact-grid difference | — | — | — | — | {fmt(comparison['max_abs_difference'])} uA | "
        f"{fmt(comparison['rms_difference'])} uA |"
    )
    lines.extend(
        [
            "",
            "## Unknown / limitations",
            "",
            "- 没有改变任何科学参数或运行新的 JoSIM；因此不提供 timestep convergence。",
            "- 没有磁耦合、JTL、T1，也没有把 local JJ phase 或 current-time area 解释为下游 SFQ delivery。",
            "- 本分析只覆盖 13 ps / 12×320 / logical1_read；不向其它负载、读宽或状态外推。",
            "- plot 是描述性证据，不是科学 Gate；唯一结果页见 `plots/RESULT_OVERVIEW.html`。",
            "",
            "## Artifacts",
            "",
            "- `analysis/metrics.json`：固定窗统计、exact-grid 差值、重复列 QA 和历史核对。",
            "- `analysis/provenance.json`：raw/hash、父 manifest、metric spec 与本次分析命令边界。",
            "- `plots/RESULT_OVERVIEW.html`：classic `sep_comb` / dark / `-j 2pi` 的五组 paired key signals。",
            "",
            "## Gate",
            "",
            "`QUICK_AMBIGUOUS` / `INCONCLUSIVE` / `AWAITING_USER_REVIEW` / `STOP`",
        ]
    )
    return "\n".join(lines) + "\n"


def write_new(path: Path, content: str) -> None:
    if path.exists():
        fail(f"refusing to overwrite existing artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main() -> int:
    config = load_config()
    cases = case_map(config)
    windows = {name: [float(value) for value in bounds] for name, bounds in config["windows_ps"].items()}
    if list(windows) != WINDOW_ORDER:
        fail(f"window order differs from preregistration: {list(windows)}")
    traces: dict[str, RawTrace] = {}
    raw_records: dict[str, dict[str, str]] = {}
    raw_qa: dict[str, Any] = {}
    for case_id, case in cases.items():
        raw_path = repo_path(case["raw"])
        record = sidecar_check(raw_path)
        trace = read_csv(raw_path)
        traces[case_id] = trace
        raw_records[case_id] = record
        raw_qa[case_id] = compact_qa(trace, record)
        raw_qa[case_id]["duplicate_checks"] = duplicate_checks(trace)
    a, b, c = (
        traces["A_grounded_source_reference"],
        traces["B_ideal_replay_qb"],
        traces["C_physical_bvm_jsl_qb"],
    )
    if not exact_time_grid_identity(a.time, b.time) or not exact_time_grid_identity(a.time, c.time):
        fail("the three registered raw traces do not share an exact full time grid")

    parent_manifest_path = repo_path(config["parent_experiment"]["manifest"])
    parent_manifest = json.loads(parent_manifest_path.read_text(encoding="utf-8"))
    metric_spec_path = repo_path(parent_manifest["metric_spec"]["path"])
    metric_spec_hash = sha256_file(metric_spec_path)
    if metric_spec_hash != parent_manifest["metric_spec"]["sha256"]:
        fail("parent metric spec hash does not match its manifest")
    reference_window = [float(value) for value in config["reference_check"]["window_ps"]]
    metrics: dict[str, Any] = {
        "schema_version": config["schema_version"],
        "analysis_status": config["outcome"],
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "joSIM_run": False,
        "raw_execution": "EXISTING_RAW_ONLY",
        "windows_ps": windows,
        "raw_records": raw_records,
        "raw_qa": raw_qa,
        "full_time_grid_exact": True,
        "window_sample_counts": {
            name: len(window_indices(a.time, bounds[0] * 1e-12, bounds[1] * 1e-12))
            for name, bounds in windows.items()
        },
    }
    metrics["window_stats"] = build_stats(traces, config, windows)
    metrics["comparisons"] = build_comparisons(traces, config, windows)
    metrics["historical_reference_check"] = build_reference_check(
        traces, config, reference_window
    )
    metrics["parent_reference"] = {
        "manifest": str(parent_manifest_path.relative_to(REPO)),
        "manifest_sha256": sha256_file(parent_manifest_path),
        "parent_head": parent_manifest["parent_head"],
        "metric_spec": parent_manifest["metric_spec"],
        "metric_spec_hash_verified": True,
        "inherited_solver": parent_manifest["solver"],
    }
    plot = write_plot(traces, config, PLOTS / "RESULT_OVERVIEW.html")
    metrics["visualization"] = plot

    generated_command = "PYTHONPATH=scripts python3 analysis/analyze_boundary_state.py"
    provenance = {
        "analysis_id": config["id"],
        "recorded_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "mode": "EXPLORATORY_QUICK",
        "raw_execution": "EXISTING_RAW_ONLY",
        "joSIM_run": False,
        "command": generated_command,
        "config": str(CONFIG_PATH.relative_to(REPO)),
        "config_sha256": sha256_file(CONFIG_PATH),
        "preregistration": str((ROOT / "PREREGISTRATION.md").relative_to(REPO)),
        "preregistration_sha256": sha256_file(ROOT / "PREREGISTRATION.md"),
        "parent_reference": metrics["parent_reference"],
        "raw_records": raw_records,
        "windows_ps": windows,
        "comparison_rules": config["comparison_rules"],
        "plot_profile": plot,
        "integrity_note": "No raw CSV, source sidecar, parent input or science netlist was modified.",
    }
    gate = """status: AWAITING_USER_REVIEW
outcome: QUICK_AMBIGUOUS
physical_disposition: INCONCLUSIVE
raw_execution: EXISTING_RAW_ONLY
joSIM_run: false
next_action: STOP
scientific_escalation: false
note: >-
  Fixed-window existing-raw decomposition is complete. Do not execute the listed
  next options or change the BVM/JSL/QB route without renewed authorization.
"""
    write_new(ANALYSIS / "metrics.json", json.dumps(metrics, ensure_ascii=False, indent=2) + "\n")
    write_new(ANALYSIS / "provenance.json", json.dumps(provenance, ensure_ascii=False, indent=2) + "\n")
    write_new(ROOT / "RESULT_BRIEF.md", make_brief(metrics))
    write_new(ANALYSIS / "REPORT.md", make_report(metrics))
    write_new(ANALYSIS / "human-gate.yaml", gate)
    print(json.dumps({"status": "OK", "root": str(ROOT.relative_to(REPO)), "plot": plot}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
