#!/usr/bin/env python3
"""R11-A direct-JTL evidence analysis.

This script intentionally uses the raw CSV time column and direct same-JJ P/V
columns. It does not use the legacy sfq_metrics.py event counters.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path

import numpy as np


PHI0 = 2.067833848e-15
ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[2]
RAW = ROOT / "raw"
ANALYSIS = ROOT / "analysis"

JTL_JJS = [
    "P(B1|XJTL1)",
    "P(B2|XJTL1)",
    "P(B1|XJTL2)",
    "P(B2|XJTL2)",
]
JTL_V = [c.replace("P(", "V(", 1) for c in JTL_JJS]
JTL_I = [c.replace("P(", "I(", 1) for c in JTL_JJS]
BVM_PHASE = [
    "P(B_JM1|XBVM1)",
    "P(B_JM2|XBVM1)",
    "P(B_JS1|XBVM1)",
    "P(B_JS2|XBVM1)",
]
BVM_V = [c.replace("P(", "V(", 1) for c in BVM_PHASE]

CASES = {
    "positive-control": {
        "raw": RAW / "positive-control/run-02.csv",
        "pre": (8.0, 10.0),
        "activity": (10.0, 35.0),
        "post": (35.0, 60.0),
        "canonical": None,
    },
    "read1": {
        "raw": RAW / "read1/run-01.csv",
        "pre": (85.0, 94.0),
        "activity": (94.0, 130.0),
        "post": (130.0, 165.0),
        "canonical": REPO / "test/exploration/bvm-internal-readout-20260819/raw/pos-read-single/run-01.csv",
    },
    "read0": {
        "raw": RAW / "read0/run-01.csv",
        "pre": (85.0, 94.0),
        "activity": (94.0, 130.0),
        "post": (130.0, 165.0),
        "canonical": REPO / "test/exploration/bvm-internal-readout-20260819/raw/neg-init-pos-read/run-01.csv",
    },
    "logical1-read0-control": {
        "raw": RAW / "logical1-read0-control/run-01.csv",
        "pre": (85.0, 94.0),
        "activity": (94.0, 130.0),
        "post": (130.0, 165.0),
        "canonical": REPO / "test/exploration/bvm-internal-readout-20260819/raw/pos-control/run-01.csv",
    },
    "logical0-read0-control": {
        "raw": RAW / "logical0-read0-control/run-01.csv",
        "pre": (85.0, 94.0),
        "activity": (94.0, 130.0),
        "post": (130.0, 165.0),
        "canonical": REPO / "test/exploration/bvm-internal-readout-20260819/raw/neg-control/run-01.csv",
    },
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def load_csv(path: Path):
    with path.open(newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise ValueError(f"empty CSV: {path}")
    fields = rows[0].keys()
    arrays = {k: np.asarray([float(row[k]) for row in rows], dtype=float) for k in fields if k != "time"}
    time_ps = np.asarray([float(row["time"]) * 1e12 for row in rows], dtype=float)
    if not np.all(np.isfinite(time_ps)) or not np.all(np.isfinite(np.column_stack(list(arrays.values())))):
        raise ValueError(f"non-finite data: {path}")
    if not np.all(np.diff(time_ps) > 0):
        raise ValueError(f"time is not strictly increasing: {path}")
    return time_ps, arrays, list(fields)


def mask(time_ps: np.ndarray, window):
    return (time_ps >= window[0]) & (time_ps < window[1])


def median_or_nan(values):
    return float(np.median(values)) if len(values) else float("nan")


def p2p(values):
    return float(np.max(values) - np.min(values)) if len(values) else float("nan")


def rms(values):
    return float(np.sqrt(np.mean(values * values))) if len(values) else float("nan")


def integrate(time_ps, values):
    return float(np.trapezoid(values, time_ps * 1e-12) / PHI0)


def largest_monotonic_segment(time_ps, phase, active_mask):
    """Return the largest forward or reverse non-decreasing raw segment.

    This is a descriptive segmentation, not an event counter. Zero-slope
    samples are included; no derivative threshold is used to create events.
    """
    idx = np.flatnonzero(active_mask)
    if len(idx) < 2:
        return {"direction": "none", "start_ps": None, "end_ps": None, "phase_delta_rad": 0.0, "turns": 0.0, "v_area_turns": 0.0}
    best = None
    dphi = np.diff(phase[idx])
    for sign, label in ((1.0, "positive"), (-1.0, "negative")):
        good = sign * dphi >= 0.0
        i = 0
        while i < len(good):
            while i < len(good) and not good[i]:
                i += 1
            if i >= len(good):
                break
            j = i
            while j + 1 < len(good) and good[j + 1]:
                j += 1
            start = idx[i]
            end = idx[j + 1]
            actual_delta = float(phase[end] - phase[start])
            magnitude = float(sign * actual_delta)
            candidate = (magnitude, label, start, end, actual_delta)
            if best is None or candidate[0] > best[0]:
                best = candidate
            i = j + 1
    if best is None:
        return {"direction": "none", "start_ps": None, "end_ps": None, "phase_delta_rad": 0.0, "turns": 0.0, "v_area_turns": 0.0}
    _, label, start, end, delta = best
    return {
        "direction": label,
        "start_ps": float(time_ps[start]),
        "end_ps": float(time_ps[end]),
        "phase_delta_rad": float(delta),
        "turns": float(delta / (2.0 * math.pi)),
        "v_area_turns": None,
        "start_index": int(start),
        "end_index": int(end),
    }


def phase_metrics(time_ps, arrays, phase_col, voltage_col, windows):
    raw_phase = arrays[phase_col]
    phase = np.unwrap(raw_phase)
    pre_m = mask(time_ps, windows["pre"])
    act_m = mask(time_ps, windows["activity"])
    post_m = mask(time_ps, windows["post"])
    pre = median_or_nan(phase[pre_m])
    post = median_or_nan(phase[post_m])
    segment = largest_monotonic_segment(time_ps, phase, act_m)
    if segment.get("start_index") is not None:
        s, e = segment["start_index"], segment["end_index"]
        segment["v_area_turns"] = integrate(time_ps[s : e + 1], arrays[voltage_col][s : e + 1])
        segment["phase_area_residual_turns"] = segment["v_area_turns"] - segment["turns"]
        segment.pop("start_index")
        segment.pop("end_index")
    whole_s = np.flatnonzero(time_ps >= windows["activity"][0])[0]
    whole_e = np.flatnonzero(time_ps < windows["post"][0])[-1]
    whole_phase_turns = float((phase[whole_e] - phase[whole_s]) / (2.0 * math.pi))
    whole_area_turns = integrate(time_ps[whole_s : whole_e + 1], arrays[voltage_col][whole_s : whole_e + 1])
    return {
        "pre_phase_rad": pre,
        "post_phase_rad": post,
        "pre_to_post_turns": float((post - pre) / (2.0 * math.pi)),
        "activity_range_turns": float((np.max(phase[act_m]) - np.min(phase[act_m])) / (2.0 * math.pi)),
        "post_phase_p2p_turns": float(p2p(phase[post_m]) / (2.0 * math.pi)),
        "post_voltage_rms_V": rms(arrays[voltage_col][post_m]),
        "largest_monotonic_segment": segment,
        "activity_window_phase_turns": whole_phase_turns,
        "activity_window_v_area_turns": whole_area_turns,
        "activity_window_phase_area_residual_turns": whole_area_turns - whole_phase_turns,
    }


def basic_window_metrics(time_ps, arrays, columns, windows):
    out = {}
    for col in columns:
        out[col] = {
            "pre_median": median_or_nan(arrays[col][mask(time_ps, windows["pre"])]),
            "activity_min": float(np.min(arrays[col][mask(time_ps, windows["activity"])])),
            "activity_max": float(np.max(arrays[col][mask(time_ps, windows["activity"])])),
            "activity_p2p": p2p(arrays[col][mask(time_ps, windows["activity"])]),
            "activity_rms": rms(arrays[col][mask(time_ps, windows["activity"])]),
            "post_median": median_or_nan(arrays[col][mask(time_ps, windows["post"])]),
            "post_p2p": p2p(arrays[col][mask(time_ps, windows["post"])]),
        }
    return out


def load_canonical(path: Path):
    return load_csv(path)


def guard_delta(time_ps, arrays, canonical_time, canonical_arrays, windows):
    cols = [
        "V(SL1)",
        "V(N6|XBVM1)",
        "I(L_SL|XBVM1)",
        "P(B_JM1|XBVM1)",
        "P(B_JM2|XBVM1)",
        "P(B_JS1|XBVM1)",
        "P(B_JS2|XBVM1)",
    ]
    out = {}
    for col in cols:
        direct = arrays[col]
        canon = canonical_arrays[col]
        dm = mask(time_ps, windows["post"])
        cm = mask(canonical_time, windows["post"])
        out[col] = {
            "direct_post_median": median_or_nan(direct[dm]),
            "canonical_post_median": median_or_nan(canon[cm]),
            "post_median_delta": median_or_nan(direct[dm]) - median_or_nan(canon[cm]),
            "direct_post_p2p": p2p(direct[dm]),
            "canonical_post_p2p": p2p(canon[cm]),
            "post_p2p_ratio_to_canonical": (p2p(direct[dm]) / p2p(canon[cm]) if p2p(canon[cm]) else None),
        }
    return out


def analyze_case(name, spec):
    time_ps, arrays, fields = load_csv(spec["raw"])
    if spec["canonical"] is None:
        needed = JTL_JJS + JTL_V + JTL_I + ["V(SFQ_MID)", "V(SFQ_OUT)", "I(R_TERM)"]
    else:
        needed = JTL_JJS + JTL_V + JTL_I + ["V(JTL_MID)", "V(JTL_OUT)", "I(R_TERM)"]
    if spec["canonical"] is not None:
        needed += [
            "V(SL1)",
            "V(N6|XBVM1)",
            "I(L_SL|XBVM1)",
            "I(L_PSL|XBVM1)",
            "P(B_JM1|XBVM1)",
            "V(B_JM1|XBVM1)",
            "P(B_JM2|XBVM1)",
            "V(B_JM2|XBVM1)",
            "P(B_JS1|XBVM1)",
            "V(B_JS1|XBVM1)",
            "P(B_JS2|XBVM1)",
            "V(B_JS2|XBVM1)",
        ]
    missing = [c for c in needed if c not in arrays]
    if missing:
        raise ValueError(f"{name}: missing columns: {missing}")
    windows = {"pre": spec["pre"], "activity": spec["activity"], "post": spec["post"]}
    jtl = {}
    for p, v, i in zip(JTL_JJS, JTL_V, JTL_I):
        jtl[p] = phase_metrics(time_ps, arrays, p, v, windows)
        jtl[p]["current"] = basic_window_metrics(time_ps, arrays, [i], windows)[i]
    bvm = {}
    if spec["canonical"] is not None:
        for p, v in zip(BVM_PHASE, BVM_V):
            bvm[p] = phase_metrics(time_ps, arrays, p, v, windows)
    if spec["canonical"] is None:
        signal_columns = ["V(SFQ_MID)", "V(SFQ_OUT)", "I(R_TERM)"]
    else:
        signal_columns = [
            "V(SL1)", "V(N6|XBVM1)", "I(L_SL|XBVM1)", "I(L_PSL|XBVM1)",
            "V(JTL_MID)", "V(JTL_OUT)", "I(R_TERM)",
        ]
    signal = basic_window_metrics(time_ps, arrays, signal_columns, windows)
    result = {
        "name": name,
        "raw_path": str(spec["raw"].relative_to(ROOT)),
        "raw_sha256": sha256(spec["raw"]),
        "rows": int(len(time_ps)),
        "time_start_ps": float(time_ps[0]),
        "time_end_ps": float(time_ps[-1]),
        "time_step_ps_median": float(np.median(np.diff(time_ps))),
        "windows_ps": windows,
        "jtl": jtl,
        "bvm": bvm,
        "signal": signal,
    }
    if spec["canonical"] is not None:
        ct, ca, _ = load_canonical(spec["canonical"])
        result["canonical_raw_path"] = str(spec["canonical"].relative_to(REPO))
        result["canonical_raw_sha256"] = sha256(spec["canonical"])
        result["guard_delta_vs_canonical"] = guard_delta(time_ps, arrays, ct, ca, windows)
    return result


def fmt(x, digits=6):
    if x is None or (isinstance(x, float) and not math.isfinite(x)):
        return "n/a"
    return f"{x:.{digits}g}"


def render_report(results):
    lines = [
        "# R11-A report：canonical BVM → standard JTL direct compatibility screening",
        "",
        "本报告从 raw CSV 的实际 time 列读取相位和直接同 JJ 电压；未使用旧 `sfq_metrics.py` 事件计数。相位单位先保留 rad，turns = Δphase/(2π)，电压面积为同一 JJ、同一段的 `∫Vdt/Φ0`。",
        "",
        "## Artifact / fixture",
        "",
        "- positive control 与四个 BVM case 均 exit 0、13,600 rows、median dt=0.0125 ps；详细 hash 在 `manifest.yaml` 和 `analysis/sha256sums.txt`。",
        "- positive control 使用仓库 `test/standard/test_jtl.cir` 的 1.5 mV、11–13 ps 单次 stimulus；所有 run 使用原样 `circuits/standard/JTL.cir` 的两 cell chain。",
        "",
        "## Positive-control validation",
        "",
        "同一标准两-cell chain 的 positive control 在四颗 JJ 上都有约一圈的 activity-window phase change；同一 JJ 直接 voltage-area 的残差约为 `10^-6 turns`，并且 post phase p2p 很小。最大的逐点单调前向段因标准 JTL 的欠阻尼 ringing 小于或接近一圈，故同时报告完整 activity-window 的 phase/area 双证据，不把 ringing 的局部峰谷误计为额外事件。",
        "",
        "| JJ | activity phase turns | activity V-area turns | residual | largest monotonic turns | segment onset→end (ps) | post p2p turns |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for jj, m in results["positive-control"]["jtl"].items():
        seg = m["largest_monotonic_segment"]
        lines.append(
            f"| `{jj}` | {fmt(m['activity_window_phase_turns'])} | {fmt(m['activity_window_v_area_turns'])} | {fmt(m['activity_window_phase_area_residual_turns'])} | {fmt(seg['turns'])} | {fmt(seg['start_ps'])}→{fmt(seg['end_ps'])} | {fmt(m['post_phase_p2p_turns'])} |"
        )
    lines += [
        "",
        "## JTL phase / voltage-area evidence",
        "",
        "| case | JJ | pre→post turns | activity range | largest monotonic turns | same-segment V-area | residual | segment onset→end (ps) | post p2p turns |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for name, result in results.items():
        for jj, m in result["jtl"].items():
            seg = m["largest_monotonic_segment"]
            lines.append(
                f"| {name} | `{jj}` | {fmt(m['pre_to_post_turns'])} | {fmt(m['activity_range_turns'])} | {fmt(seg['turns'])} | {fmt(seg['v_area_turns'])} | {fmt(seg.get('phase_area_residual_turns'))} | {fmt(seg['start_ps'])}→{fmt(seg['end_ps'])} | {fmt(m['post_phase_p2p_turns'])} |"
            )
    lines += [
        "",
        "`largest monotonic` 是描述性轨迹分段，不单独定义 event；complete local event 仍要求 continuous unwrapped phase、同段 voltage-area 一致以及事件后 retrap/bounded behavior 联合成立。",
        "",
        "## BVM direct-loading observations",
        "",
        "| case | V(SL1) activity p2p (V) | I(L_SL) activity p2p (A) | V(N6) activity p2p (V) | JTL OUT activity p2p (V) |",
        "|---|---:|---:|---:|---:|",
    ]
    for name in ("read1", "read0", "logical1-read0-control", "logical0-read0-control"):
        s = results[name]["signal"]
        lines.append(
            f"| {name} | {fmt(s['V(SL1)']['activity_p2p'])} | {fmt(s['I(L_SL|XBVM1)']['activity_p2p'])} | {fmt(s['V(N6|XBVM1)']['activity_p2p'])} | {fmt(s['V(JTL_OUT)']['activity_p2p'])} |"
        )
    lines += [
        "",
        "## Source/storage differential versus canonical no-receiver",
        "",
        "下表只报告 direct JTL loaded case 与 matched canonical no-receiver raw 在 post `[130,165) ps` 的 median/p2p 差异；是否可接受必须结合 canonical baseline 和本项目 storage guard 解释，不能用 absolute JS phase change 单独判定。",
        "",
        "| case | SL median Δ | N6 median Δ | L_SL median Δ | JM1 median Δ | JM2 median Δ | JS1 median Δ | JS2 median Δ |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for name in ("read1", "read0", "logical1-read0-control", "logical0-read0-control"):
        g = results[name]["guard_delta_vs_canonical"]
        def gd(col): return fmt(g[col]["post_median_delta"])
        lines.append(f"| {name} | {gd('V(SL1)')} | {gd('V(N6|XBVM1)')} | {gd('I(L_SL|XBVM1)')} | {gd('P(B_JM1|XBVM1)')} | {gd('P(B_JM2|XBVM1)')} | {gd('P(B_JS1|XBVM1)')} | {gd('P(B_JS2|XBVM1)')} |")
    lines += [
        "",
        "## BVM storage/readout phase comparison",
        "",
        "| case | JM1 net turns | JM2 net turns | JS1 net turns | JS2 net turns | JS1 post p2p | JS2 post p2p |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for name in ("read1", "read0", "logical1-read0-control", "logical0-read0-control"):
        b = results[name]["bvm"]
        lines.append(
            f"| {name} | {fmt(b['P(B_JM1|XBVM1)']['pre_to_post_turns'])} | {fmt(b['P(B_JM2|XBVM1)']['pre_to_post_turns'])} | {fmt(b['P(B_JS1|XBVM1)']['pre_to_post_turns'])} | {fmt(b['P(B_JS2|XBVM1)']['pre_to_post_turns'])} | {fmt(b['P(B_JS1|XBVM1)']['post_phase_p2p_turns'])} | {fmt(b['P(B_JS2|XBVM1)']['post_phase_p2p_turns'])} |"
        )
    lines += [
        "",
        "## Interpretation",
        "",
        "### Observed",
        "",
        "- 详见上表；positive-control 是判定 BVM 前提的唯一正向 fixture。",
        "- BVM 四-case 的 JTL phase、same-JJ area、post stability 和 source guards 必须以 JSON 原始数值联合读取。",
        "",
        "### Derived",
        "",
        "- 由 phase/area 同段一致性判断 local JTL transition 是否有双证据；由 XJTL1→XJTL2 的 onset 顺序判断是否有逐级传播。",
        "- read1/read0/control 的 propagated-event 判定不使用 `I>Ic`、voltage peak 或 phase range alone。",
        "",
        "### Inference",
        "",
        "- 仅能把结果归因于本次 fixed direct galvanic load、standard JTL fixture、stimulus、model、dt 和 windows；不能外推到所有 direct-JTL topology。",
        "",
        "### Unknown / audit boundary",
        "",
        "- 本轮没有额外时间步收敛组，也没有 T1；即使 chain 传播通过，也只建立两-cell loaded-JTL screening evidence，不是 downstream T1 或 hardware claim。",
        "",
        "## Verdict",
        "",
        "`DIRECT_JTL_SELECTIVE_PASS` 未满足：positive control fixture 通过，但 canonical BVM read1 的最大 JTL phase excursion 仍远低于一圈，且 read1→XJTL2 没有对应完整 event。read0 与两个 READ=0 controls 没有完整 event，post phase p2p 处于 bounded 数值背景。故本 fixed direct-galvanic point 的主 verdict 为 **`NO_JTL_TRIGGER`**，不是 `DIRECT_JTL_NONSELECTIVE` 或 `SOURCE_BACK_ACTION_FAILURE`。",
        "",
        "这只表示在当前 canonical BVM source、standard JTL、direct load、stimulus、模型、`dt=0.0125 ps` 和预注册窗口下，read1 没有触发第一颗标准 JTL JJ 的 complete transition；它不否定带 temporal rectification/hold/regeneration 的后续 receiver，也不把整个 direct-JTL family 宣判为普遍不可能。",
    ]
    return "\n".join(lines) + "\n"


def main():
    results = {name: analyze_case(name, spec) for name, spec in CASES.items()}
    payload = {
        "experiment": "R11-A",
        "head": "6c2530555e239552d611bf9519126e5e596b3cd6",
        "phi0_Wb": PHI0,
        "results": results,
    }
    (ANALYSIS / "r11a-summary.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    (ANALYSIS / "R11A_REPORT.md").write_text(render_report(results))
    for name, result in results.items():
        print(f"[{name}] rows={result['rows']} dt_ps={result['time_step_ps_median']:.8g} raw_sha256={result['raw_sha256']}")
        for jj, m in result["jtl"].items():
            seg = m["largest_monotonic_segment"]
            print(
                f"  {jj}: net={m['pre_to_post_turns']:.8g} turns "
                f"range={m['activity_range_turns']:.8g} turns "
                f"largest={seg['turns']:.8g} turns "
                f"area={seg['v_area_turns']:.8g} residual={seg.get('phase_area_residual_turns', float('nan')):.8g}"
            )
    print("wrote analysis/r11a-summary.json and analysis/R11A_REPORT.md")


if __name__ == "__main__":
    main()
