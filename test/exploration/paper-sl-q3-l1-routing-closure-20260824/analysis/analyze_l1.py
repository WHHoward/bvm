#!/usr/bin/env python3
"""PAPER-SL-Q3 post-run phase/area and routing audit.

The low-level monotonic-segment implementation is imported from the accepted
Q3-PRE analysis script so the phase/area convention remains identical.  This
wrapper adds the frozen-Q2 versus L1=4.50 pH comparison and full-window event
counts for the four matched cases.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
Q3_ANALYSIS = ROOT / "test/exploration/paper-sl-q3-pre-20260824/analysis"
sys.path.insert(0, str(Q3_ANALYSIS))
from analyze_q3_pre import (  # noqa: E402
    JUNCTIONS,
    TWO_PI,
    analyze_case,
    column,
    load_csv,
    segment_records,
)


MAIN_WINDOW = (94.0, 130.0)
POST_WINDOW = (140.0, 170.0)
CASE_NAMES = [
    "paper-j1-logical1-read0-control",
    "paper-j0-logical0-read0-control",
    "paper-j0-logical0-read",
    "paper-j1-logical1-read",
]
JUNCTION_ORDER = ("BJs", "BJL1", "BJL2")
BRANCHES = (
    "I(BJS|XBQ)", "I(BJL1|XBQ)", "I(RJ1|XBQ)", "I(L1|XBQ)",
    "I(RB|XBQ)", "I(L2|XBQ)", "I(BJL2|XBQ)", "I(RJ2|XBQ)",
    "I(L0|XBQ)", "I(LIN|XBQ)",
)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def spec(path: Path, label: str) -> dict[str, Any]:
    return {
        "label": label,
        "path": path.resolve(),
        "windows": [MAIN_WINDOW],
        "dt_ps": 0.0125,
        "ibias_uA": 35.0,
    }


def all_segments_for(data: dict[str, np.ndarray], window: tuple[float, float]) -> dict[str, list[dict[str, Any]]]:
    t_ps = column(data, "time") * 1e12
    result: dict[str, list[dict[str, Any]]] = {}
    for name, names in JUNCTIONS.items():
        phase = np.unwrap(column(data, names[0]))
        result[name] = segment_records(t_ps, phase, column(data, names[1]), window, 0)
    return result


def event_summary(path: Path) -> dict[str, Any]:
    data = load_csv(path)
    t_ps = column(data, "time") * 1e12
    windows = {"main": MAIN_WINDOW, "post": POST_WINDOW}
    by_window: dict[str, Any] = {}
    for label, window in windows.items():
        segs = all_segments_for(data, window)
        by_window[label] = {}
        for name in JUNCTION_ORDER:
            complete = [s for s in segs[name] if s["area_consistent"]]
            by_window[label][name] = {
                "activity_range_turns": float(
                    np.ptp(np.unwrap(column(data, JUNCTIONS[name][0]))[(t_ps >= window[0]) & (t_ps < window[1])]) / TWO_PI
                ),
                "segment_count": len(segs[name]),
                "complete_segment_count": len(complete),
                "complete_event_units": int(sum(int(s["complete_event_units"]) for s in complete)),
                "complete_segments": complete,
            }
    return by_window


def current_rms(path: Path, control_path: Path, branch: str, window: tuple[float, float]) -> dict[str, float]:
    data = load_csv(path)
    ctrl = load_csv(control_path)
    t = column(data, "time") * 1e12
    tc = column(ctrl, "time") * 1e12
    if t.shape != tc.shape or not np.allclose(t, tc, rtol=0, atol=1e-9):
        raise ValueError(f"time axes do not match for control subtraction: {path} / {control_path}")
    m = (t >= window[0]) & (t < window[1])
    delta_uA = (column(data, branch)[m] - column(ctrl, branch)[m]) * 1e6
    return {
        "rms_uA": float(np.sqrt(np.mean(delta_uA * delta_uA))),
        "p2p_uA": float(np.ptp(delta_uA)),
        "signed_area_uA_ps": float(np.trapezoid(delta_uA, t[m])),
    }


def analyze_set(prefix: str, raw_dir: Path) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for name in CASE_NAMES:
        path = raw_dir / f"{name}.csv"
        label = f"{prefix} {name}"
        result[name] = analyze_case(name, spec(path, label))
        result[name]["raw_sha256"] = sha256(path)
        result[name]["event_summary"] = event_summary(path)
    read1 = raw_dir / "paper-j1-logical1-read.csv"
    read1_ctrl = raw_dir / "paper-j1-logical1-read0-control.csv"
    read0 = raw_dir / "paper-j0-logical0-read.csv"
    read0_ctrl = raw_dir / "paper-j0-logical0-read0-control.csv"
    result["control_subtracted"] = {
        "logical1_read_minus_read0_control": {
            branch: current_rms(read1, read1_ctrl, branch, MAIN_WINDOW) for branch in BRANCHES
        },
        "logical0_read_minus_read0_control": {
            branch: current_rms(read0, read0_ctrl, branch, MAIN_WINDOW) for branch in BRANCHES
        },
    }
    return result


def f(x: Any, digits: int = 6) -> str:
    if x is None:
        return "—"
    if isinstance(x, float) and (math.isnan(x) or math.isinf(x)):
        return "n/a"
    if isinstance(x, (float, int)):
        return f"{x:.{digits}g}"
    return str(x)


def phase_row(case_id: str, case: dict[str, Any], name: str) -> str:
    seg = case["trajectory"][name]["paired_window_largest"]
    return (
        f"| {case_id} | {name} | {f(seg['start_ps'])}–{f(seg['end_ps'])} | "
        f"{f(seg['delta_turns'])} | {f(seg['area_turns'])} | "
        f"{f(seg['area_residual_turns'])} | "
        f"{'yes' if seg['area_consistent'] else 'no'} |"
    )


def event_cell(case: dict[str, Any], name: str) -> str:
    main = case["event_summary"]["main"][name]
    post = case["event_summary"]["post"][name]
    return f"{main['complete_event_units']} / {post['complete_event_units']}"


def routing_display(case: dict[str, Any], key: str) -> str:
    metrics = case["routing_metrics"]
    # A nearly zero signed BJs area makes a signed fraction numerically
    # ill-conditioned for READ=0 controls.  Preserve the raw value in JSON,
    # but do not present it as a physical routing fraction in the report.
    if abs(float(metrics["q_bjs_uA_ps"])) < 5.0:
        return "ill-conditioned"
    return f(metrics[key])


def report(baseline: dict[str, Any], perturbed: dict[str, Any], comparison: dict[str, Any], verdict: str) -> str:
    lines = [
        "# PAPER-SL-Q3 — L1 Routing Closure 报告",
        "",
        "## 结论等级",
        "",
        f"主 verdict：**`{verdict}`**",
        "",
        "本 Exploration 使用 accepted PAPER-SL-Q2 40-uA replay 作为 source-isolated QB fixture；没有连接 physical BVM/JSL，也没有接 JTL。基线和单点都使用同一 0.0125 ps / 170 ps source deck；唯一电路变更是 native QB 的 `L1=3.91 pH -> 4.50 pH`。phase/area 事件判断使用同一 JJ、同一 monotonic segment、直接 V(BJJ) 和 CSV 实际时间。",
        "",
        "## 事件计数摘要",
        "",
        "表格中的 `main/post` 是 `[94,130) ps` 与 `[140,170) ps` 内满足 phase/area 一致性的完整 event units；它不是 derivative/peak 计数。",
        "",
        "| case | baseline BJs | baseline BJL1 | baseline BJL2 | L1=4.50 BJs | L1=4.50 BJL1 | L1=4.50 BJL2 |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for name in CASE_NAMES:
        lines.append(
            f"| {name} | {event_cell(baseline[name], 'BJs')} | {event_cell(baseline[name], 'BJL1')} | {event_cell(baseline[name], 'BJL2')} | {event_cell(perturbed[name], 'BJs')} | {event_cell(perturbed[name], 'BJL1')} | {event_cell(perturbed[name], 'BJL2')} |"
        )
    lines += [
        "",
        "## Continuous phase / same-JJ voltage-area",
        "",
        "下表是每个 case 主 `[94,130) ps` 中与 dominant BJs window 配对的最大 monotonic segment；它用于 routing comparison，不把 total phase range 当作 event。",
        "",
        "| case | JJ | baseline segment (ps) | baseline Δturn | baseline area (Φ0) | perturbed segment (ps) | perturbed Δturn | perturbed area (Φ0) | phase/area aligned | complete event |",
        "|---|---|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for name in CASE_NAMES:
        for jj in JUNCTION_ORDER:
            b = baseline[name]["trajectory"][jj]["paired_window_largest"]
            p = perturbed[name]["trajectory"][jj]["paired_window_largest"]
            lines.append(
                f"| {name} | {jj} | {f(b['start_ps'])}–{f(b['end_ps'])} | {f(b['delta_turns'])} | {f(b['area_turns'])} | {f(p['start_ps'])}–{f(p['end_ps'])} | {f(p['delta_turns'])} | {f(p['area_turns'])} | {'yes' if p['phase_area_consistent'] else 'no'} | {'yes' if p['area_consistent'] else 'no'} |"
            )
    lines += [
        "",
        "## BJs→BJL1 node2 routing",
        "",
        "node2 KCL 为 `I(BJs)=I(L1)+I(BJL1)+I(RJ1)`。`F_local` 与 `F_L1` 是配对 BJL1 segment 内 signed current-area 的派生分流指标；KCL residual 用 dominant BJs interval 计算。",
        "",
        "| case | baseline F_local | L1=4.50 F_local | ΔF_local | baseline F_L1 | L1=4.50 F_L1 | ΔF_L1 | baseline node2 KCL RMS (uA) | perturbed node2 KCL RMS (uA) |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for name in CASE_NAMES:
        br = baseline[name]["routing_metrics"]
        pr = perturbed[name]["routing_metrics"]
        bk = baseline[name]["kcl"]["node2_BJs_minus_L1_BJL1_RJ1"]["rms_uA"]
        pk = perturbed[name]["kcl"]["node2_BJs_minus_L1_BJL1_RJ1"]["rms_uA"]
        lines.append(
            f"| {name} | {routing_display(baseline[name], 'local_fraction_of_bjs')} | {routing_display(perturbed[name], 'local_fraction_of_bjs')} | {('ill-conditioned' if abs(float(br['q_bjs_uA_ps'])) < 5.0 or abs(float(pr['q_bjs_uA_ps'])) < 5.0 else f(pr['local_fraction_of_bjs']-br['local_fraction_of_bjs']))} | {routing_display(baseline[name], 'l1_fraction_of_bjs')} | {routing_display(perturbed[name], 'l1_fraction_of_bjs')} | {('ill-conditioned' if abs(float(br['q_bjs_uA_ps'])) < 5.0 or abs(float(pr['q_bjs_uA_ps'])) < 5.0 else f(pr['l1_fraction_of_bjs']-br['l1_fraction_of_bjs']))} | {f(bk)} | {f(pk)} |"
        )
    lines += [
        "",
        "配对窗口 signed current-area（单位 µA·ps）如下；它直接显示 node2 分流的分子/分母，READ=0 control 的近零 BJs signed area 不用于计算有意义的 fraction。",
        "",
        "| case | baseline ∫BJs | L1=4.50 ∫BJs | baseline ∫BJL1 | L1=4.50 ∫BJL1 | baseline ∫RJ1 | L1=4.50 ∫RJ1 | baseline ∫L1 | L1=4.50 ∫L1 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for name in CASE_NAMES:
        br = baseline[name]["routing_metrics"]
        pr = perturbed[name]["routing_metrics"]
        lines.append(
            f"| {name} | {f(br['q_bjs_uA_ps'])} | {f(pr['q_bjs_uA_ps'])} | {f(br['q_bjl1_uA_ps'])} | {f(pr['q_bjl1_uA_ps'])} | {f(br['q_rj1_uA_ps'])} | {f(pr['q_rj1_uA_ps'])} | {f(br['q_l1_uA_ps'])} | {f(pr['q_l1_uA_ps'])} |"
        )
    lines += [
        "",
        "### Read/control-subtracted RMS",
        "",
        "`δI(t)=I_read(t)-I_READ0_control(t)`，仅在 `[94,130) ps` 逐点相减；这是同一 source fixture 下的 routing diagnostic，不是事件判据。",
        "",
        "| set | baseline RMS δBJs (uA) | L1=4.50 RMS δBJs | baseline RMS δlocal (uA) | L1=4.50 RMS δlocal | baseline G_local | L1=4.50 G_local | baseline RMS δL1 | L1=4.50 RMS δL1 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for set_name in ("logical1_read_minus_read0_control", "logical0_read_minus_read0_control"):
        b = baseline["control_subtracted"][set_name]
        p = perturbed["control_subtracted"][set_name]
        lines.append(
            f"| {set_name} | {f(b['I(BJS|XBQ)']['rms_uA'])} | {f(p['I(BJS|XBQ)']['rms_uA'])} | {f(b['I(BJL1_plus_RJ1|XBQ)']['rms_uA'])} | {f(p['I(BJL1_plus_RJ1|XBQ)']['rms_uA'])} | {f(b['routing_gain_local_over_BJs_rms'])} | {f(p['routing_gain_local_over_BJs_rms'])} | {f(b['I(L1|XBQ)']['rms_uA'])} | {f(p['I(L1|XBQ)']['rms_uA'])} |"
        )
    lines += [
        "",
        "说明：`RMS(local)` 是先将 `δI(BJL1)+δI(RJ1)` 逐点相加后再求 RMS，不是两个 RMS 的相加；完整 waveform、比值和 signed area 也保存在 `metrics.json` 的 `control_subtracted` 字段中。",
        "",
        "## Settled / post behavior",
        "",
        "各 case 的 post-window phase p2p、branch current ranges、完整 segment 列表和 phase/area consistency 保存在 `metrics.json`。本报告只把 post-window 中满足同一-JJ phase/area 条件的 segment 计入 event summary；未满足者保留为 activity，不称 event。",
        "",
        "## Observed",
        "",
        "- 四个单点 raw 均生成且 exit code 为 0；首跑 logical1 READ=0 control 没有 startup/free-running 或完整 phase/area-consistent transition，因此按预注册停止条件完成全部 matched cases。",
        "- 具体 BJL1/BJL2 的 phase、同段 voltage area、KCL 和 read1/read0/control event count 见上表和 `metrics.json`；任何 sub-turn excursion 均不被写成 switching event。",
        "- 本 replay fixture 不包含 canonical BVM 的 `SL/N6/I(L_SL)/JM/JS` 列，因此本轮不能独立证明 physical BVM source/back-action guard；这不是“guard 通过”，而是 replay scope 的已知边界。",
        "",
        "## Derived",
        "",
        "- `L1=4.50 pH` 的效果以 signed branch split、control-subtracted waveform 和 same-JJ phase/area 三组量共同判断；不能以 `I/Ic`、电压峰值或 total phase range 单独判定。READ=0 control 的 signed-area fraction 因分母接近零而标为 ill-conditioned，不参与 read1 routing gain 的解释。",
        "- 如果 `F_local`/control-subtracted local routing 提高但 BJL1 仍没有完整同段 transition，最强结论只能是 routing gain with subthreshold BJL1，不能推断 threshold 已闭合。",
        "",
        "## Inference",
        "",
        "本单点只用于裁决 L1 routing hypothesis。在当前 scope 内，不能把一个 bounded local response升级为 downstream SFQ delivery；也不能从单点失败宣称所有 L1/load-line 方向不可能。",
        "",
        "## Unknown",
        "",
        "- 没有 physical BVM→12JSL→QB 接入；source/back-action guard 仍需后续具有 BVM 列的实验才能验证。",
        "- 本轮未做 L1 sweep、convergence rerun 或 BJL1/BJL2 ratio tuning；单点结果不定义连续参数窗口。",
        "",
        "## Stop rule / disposition",
        "",
        "本 checkpoint 后不追加 L1 sweep，不改变 BJL1/BJL2 AREA、central bias、L2、RB/RJ1/RJ2，不连接 physical BVM/JSL/QB 或 JTL。若 routing gain 但 BJL1 仍 subthreshold，关闭本轮 L1 单点并保留 bounded routing conclusion。",
        "",
        "## Provenance",
        "",
        "- preregistration：`PREREGISTRATION.md`；",
        "- Stage-A：`analysis/ANALYTIC_PRECHECK.md`；",
        "- modified fixture：`inputs/l1-4p5/`；",
        "- source deck identity/hash：`inputs/deck-hashes.json`；",
        "- raw/log/hash manifest：`manifest.yaml`、`sha256sums.txt`；",
        "- phase/area helper dependency：accepted `test/exploration/paper-sl-q3-pre-20260824/analysis/analyze_q3_pre.py`。",
    ]
    return "\n".join(lines) + "\n"


def add_local_rms(dataset: dict[str, Any]) -> None:
    """Add RMS of the actual summed local waveform to saved metrics."""
    for set_name, d in dataset["control_subtracted"].items():
        # Reconstruct from the raw case/control pair so the cross term is not
        # lost.  The two case names are fixed by the preregistration.
        if set_name.startswith("logical1"):
            case = "paper-j1-logical1-read"
            ctrl = "paper-j1-logical1-read0-control"
        else:
            case = "paper-j0-logical0-read"
            ctrl = "paper-j0-logical0-read0-control"
        case_path = Path(dataset[case]["raw_path"])
        ctrl_path = Path(dataset[ctrl]["raw_path"])
        cdata = load_csv(case_path)
        kdata = load_csv(ctrl_path)
        t = column(cdata, "time") * 1e12
        tc = column(kdata, "time") * 1e12
        m = (t >= MAIN_WINDOW[0]) & (t < MAIN_WINDOW[1])
        mc = (tc >= MAIN_WINDOW[0]) & (tc < MAIN_WINDOW[1])
        delta_local = (
            (column(cdata, "I(BJL1|XBQ)")[m] + column(cdata, "I(RJ1|XBQ)")[m])
            - (column(kdata, "I(BJL1|XBQ)")[mc] + column(kdata, "I(RJ1|XBQ)")[mc])
        ) * 1e6
        delta_bjs = (column(cdata, "I(BJS|XBQ)")[m] - column(kdata, "I(BJS|XBQ)")[mc]) * 1e6
        d["I(BJL1_plus_RJ1|XBQ)"] = {
            "rms_uA": float(np.sqrt(np.mean(delta_local * delta_local))),
            "p2p_uA": float(np.ptp(delta_local)),
            "signed_area_uA_ps": float(np.trapezoid(delta_local, t[m])),
        }
        d["routing_gain_local_over_BJs_rms"] = float(
            d["I(BJL1_plus_RJ1|XBQ)"]["rms_uA"] / np.sqrt(np.mean(delta_bjs * delta_bjs))
        ) if np.any(delta_bjs) else math.nan


def main() -> None:
    base_dir = ROOT / "test/exploration/paper-sl-q2-20260824/raw/40u"
    new_dir = EXP / "raw/l1-4p5"
    baseline = analyze_set("R9/Q2 baseline", base_dir)
    perturbed = analyze_set("Q3 L1=4.50 pH", new_dir)
    add_local_rms(baseline)
    add_local_rms(perturbed)

    read1_b = baseline["paper-j1-logical1-read"]["routing_metrics"]["local_fraction_of_bjs"]
    read1_p = perturbed["paper-j1-logical1-read"]["routing_metrics"]["local_fraction_of_bjs"]
    read1_bjl1 = perturbed["paper-j1-logical1-read"]["trajectory"]["BJL1"]["global_largest"]
    read0_p = perturbed["paper-j0-logical0-read"]["event_summary"]
    ctrl1_p = perturbed["paper-j1-logical1-read0-control"]["event_summary"]
    ctrl0_p = perturbed["paper-j0-logical0-read0-control"]["event_summary"]
    bjl1_complete_read1 = bool(read1_bjl1["area_consistent"])
    any_nonselective = any(
        perturbed[name]["event_summary"][window][jj]["complete_event_units"] > 0
        for name in ("paper-j0-logical0-read", "paper-j1-logical1-read0-control", "paper-j0-logical0-read0-control")
        for window in ("main", "post")
        for jj in ("BJL1", "BJL2")
    )
    read1_multi = any(
        perturbed["paper-j1-logical1-read"]["event_summary"][window][jj]["complete_event_units"] > 1
        for window in ("main", "post") for jj in ("BJL1", "BJL2")
    )
    if any_nonselective:
        verdict = "NONSELECTIVE_OR_FREE_RUNNING_FAILURE"
    elif read1_multi:
        verdict = "NONSELECTIVE_OR_FREE_RUNNING_FAILURE"
    elif bjl1_complete_read1:
        verdict = "ROUTING_GAIN_WITH_SELECTIVITY_PRESERVED"
    elif read1_p > read1_b + 1e-12:
        verdict = "ROUTING_GAIN_WITH_BJL1_SUBTHRESHOLD"
    else:
        verdict = "L1_ROUTING_NO_GAIN"

    comparison = {
        "read1_local_fraction_baseline": read1_b,
        "read1_local_fraction_perturbed": read1_p,
        "read1_local_fraction_delta": read1_p - read1_b,
        "read1_bjl1_global_largest": read1_bjl1,
        "perturbed_control_event_summaries": {"logical1_read0": ctrl1_p, "logical0_read0": ctrl0_p, "logical0_read": read0_p},
        "verdict_rule_inputs": {"bjl1_complete_read1": bjl1_complete_read1, "any_nonselective": any_nonselective, "read1_multi": read1_multi},
    }
    result = {
        "study": "PAPER-SL-Q3",
        "verdict": verdict,
        "parameters": {"baseline_L1_pH": 3.91, "perturbed_L1_pH": 4.50, "all_other_parameters_frozen": True},
        "windows_ps": {"main": list(MAIN_WINDOW), "post": list(POST_WINDOW)},
        "baseline": baseline,
        "perturbed": perturbed,
        "comparison": comparison,
        "analysis_dependency": str(Q3_ANALYSIS / "analyze_q3_pre.py"),
        "analysis_dependency_sha256": sha256(Q3_ANALYSIS / "analyze_q3_pre.py"),
    }
    (EXP / "analysis/metrics.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    (EXP / "analysis/REPORT.md").write_text(report(baseline, perturbed, comparison, verdict))
    with (EXP / "analysis/case-summary.csv").open("w", newline="") as fcsv:
        writer = csv.writer(fcsv, lineterminator="\n")
        writer.writerow(["set", "case", "BJs_turn", "BJL1_turn", "BJL2_turn", "BJs_events_main/post", "BJL1_events_main/post", "BJL2_events_main/post", "F_local"])
        for label, dataset in (("baseline", baseline), ("L1_4p50", perturbed)):
            for name in CASE_NAMES:
                c = dataset[name]
                writer.writerow([
                    label, name,
                    c["trajectory"]["BJs"]["global_largest"]["delta_turns"],
                    c["trajectory"]["BJL1"]["global_largest"]["delta_turns"],
                    c["trajectory"]["BJL2"]["global_largest"]["delta_turns"],
                    event_cell(c, "BJs"), event_cell(c, "BJL1"), event_cell(c, "BJL2"),
                    c["routing_metrics"]["local_fraction_of_bjs"],
                ])
    print(verdict)
    print(json.dumps(comparison, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
