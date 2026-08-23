#!/usr/bin/env python3
"""Evidence audit for the single-point R15-D J_Q compressor exploration."""

import csv
import json
import math
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
R15C = Path("/home/howard/JoSIM/test/exploration/bvm-sfq-receiver-r15c-jset-causal-20260823")
R15B = Path("/home/howard/JoSIM/test/exploration/bvm-sfq-receiver-r15b-magnetic-correction-20260823")
PHI0 = 2.067833848e-15
TWOPI = 2.0 * math.pi
WINDOWS = {"pre": (80.0, 90.0), "activity": (94.0, 130.0), "post": (150.0, 170.0)}
CASES = ["logical1-read0-control", "logical1-read", "logical0-read", "logical0-read0-control"]

PHASES = {
    "B_DET": ("P(B_DET|XR15D)", "V(B_DET|XR15D)"),
    "B_SET": ("P(B_SET|XR15D)", "V(B_SET|XR15D)"),
    "B_Q": ("P(B_Q|XR15D)", "V(B_Q|XR15D)"),
}

CURRENT_COLUMNS = {
    "I_BDET": "I(B_DET|XR15D)",
    "I_BSET": "I(B_SET|XR15D)",
    "I_BQ": "I(B_Q|XR15D)",
    "I_ISET": "I(I_SET|XR15D)",
    "I_RBIAS": "I(R_BIAS|XR15D)",
    "I_LRET": "I(L_RET|XR15D)",
    "I_LS": "I(L_S|XR15D)",
    "I_LQ": "I(L_Q|XR15D)",
    "I_RQ": "I(R_Q|XR15D)",
    "I_IQ": "I(I_Q|XR15D)",
    "I_LTX": "I(L_TX|XR15D)",
    "I_RIN": "I(R_IN|XR15D)",
    "I_IDET": "I(I_DET|XR15D)",
}

SOURCE_COLUMNS = {
    "V(SL)": "V(SL1)",
    "V(N6)": "V(N6|XBVM1)",
    "I(L_SL)": "I(L_SL|XBVM1)",
    "P(JM1)": "P(B_JM1|XBVM1)",
    "P(JM2)": "P(B_JM2|XBVM1)",
    "P(JS1)": "P(B_JS1|XBVM1)",
    "P(JS2)": "P(B_JS2|XBVM1)",
}


def load(path):
    with path.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError(f"empty CSV: {path}")
    names = list(rows[0])
    if "time" not in names:
        raise ValueError(f"missing time column: {path}")
    t = np.asarray([float(row["time"]) for row in rows]) * 1e12
    data = {name: np.asarray([float(row[name]) for row in rows]) for name in names if name != "time"}
    if not np.all(np.diff(t) > 0) or not all(np.all(np.isfinite(v)) for v in data.values()):
        raise ValueError(f"invalid time/data: {path}")
    return t, data


def mask(t, window):
    return (t >= window[0]) & (t < window[1])


def stats(values, scale=1.0):
    x = np.asarray(values) * scale
    return {
        "min": float(np.min(x)),
        "max": float(np.max(x)),
        "p2p": float(np.ptp(x)),
        "rms": float(np.sqrt(np.mean(x * x))),
        "median": float(np.median(x)),
    }


def phase_segments(t, phase, voltage, window):
    m = mask(t, window)
    idx = np.flatnonzero(m)
    if len(idx) < 2:
        return []
    p = np.unwrap(phase[m])
    d = np.diff(p)
    signs = np.sign(d)
    for i in range(1, len(signs)):
        if signs[i] == 0:
            signs[i] = signs[i - 1]
    if len(signs) and signs[0] == 0:
        signs[0] = 1
    starts = [0]
    for i in range(1, len(signs)):
        if signs[i] != signs[i - 1]:
            starts.append(i)
    result = []
    for start, end0 in zip(starts, starts[1:] + [len(p) - 1]):
        if end0 <= start:
            continue
        gi = idx[start : end0 + 1]
        delta = float((p[end0] - p[start]) / TWOPI)
        area = float(np.trapezoid(voltage[gi], t[gi] * 1e-12) / PHI0)
        residual = area - delta
        result.append(
            {
                "start_ps": float(t[gi[0]]),
                "end_ps": float(t[gi[-1]]),
                "phase_delta_turns": delta,
                "phase_abs_turns": abs(delta),
                "voltage_area_turns": area,
                "phase_area_residual_turns": residual,
                "complete_candidate": bool(
                    abs(delta) >= 1.0 and abs(residual) <= max(0.02, 0.05 * abs(delta))
                ),
            }
        )
    return sorted(result, key=lambda x: x["phase_abs_turns"], reverse=True)


def phase_metrics(t, data, phase_col, voltage_col):
    result = {}
    for label, window in WINDOWS.items():
        m = mask(t, window)
        p = np.unwrap(data[phase_col][m])
        segs = phase_segments(t, data[phase_col], data[voltage_col], window)
        result[label] = {
            "activity_range_turns": float(np.ptp(p) / TWOPI),
            "phase_start_rad": float(p[0]),
            "phase_end_rad": float(p[-1]),
            "phase_rad": stats(data[phase_col][m]),
            "voltage_uV": stats(data[voltage_col][m], 1e6),
            "segments": segs,
            "largest_segment": segs[0] if segs else None,
            "complete_candidate_count": int(sum(x["complete_candidate"] for x in segs)),
        }
    return result


def artifact(path, t):
    exit_path = ROOT / "logs" / f"{path.stem}.exitcode.txt"
    exit_code = int(exit_path.read_text().strip()) if exit_path.exists() else None
    dt = np.diff(t)
    return {
        "path": str(path.relative_to(ROOT)),
        "rows": int(len(t)),
        "start_ps": float(t[0]),
        "end_ps": float(t[-1]),
        "dt_median_ps": float(np.median(dt)),
        "dt_max_ps": float(np.max(dt)),
        "exit_code": exit_code,
        "strict_time": bool(np.all(dt > 0)),
    }


def source_delta(t, data, c_t, c_data):
    result = {}
    for label, column in SOURCE_COLUMNS.items():
        scale = 1e6 if label.startswith("V(") or label.startswith("I(") else 1.0
        result[label] = {}
        for window_name, window in WINDOWS.items():
            a = data[column][mask(t, window)]
            b = c_data[column][mask(c_t, window)]
            result[label][window_name] = {
                "r15d": stats(a, scale),
                "r15c": stats(b, scale),
                "p2p_change_r15d_minus_r15c": float((np.ptp(a) - np.ptp(b)) * scale),
                "rms_waveform_difference": float(np.sqrt(np.mean((a - b) ** 2)) * scale),
            }
    return result


def absolute_source_post(t, data, c_t, c_data, b_t, b_data):
    result = {}
    window = WINDOWS["post"]
    for label, column in SOURCE_COLUMNS.items():
        scale = 1e6 if label.startswith("V(") or label.startswith("I(") else 1.0
        result[label] = {
            "r15d_p2p": float(np.ptp(data[column][mask(t, window)]) * scale),
            "r15c_p2p": float(np.ptp(c_data[column][mask(c_t, window)]) * scale),
            "r15b_p2p": float(np.ptp(b_data[column][mask(b_t, window)]) * scale),
        }
    return result


def lq_refractory(t, data, bq_metrics):
    pre_m = mask(t, WINDOWS["pre"])
    activity_m = mask(t, WINDOWS["activity"])
    post_m = mask(t, WINDOWS["post"])
    ilq = data[CURRENT_COLUMNS["I_LQ"]]
    pre = float(np.median(ilq[pre_m]))
    activity_i = np.flatnonzero(activity_m)
    if len(activity_i):
        local = activity_i[int(np.argmin(ilq[activity_i]))]
        minimum = float(ilq[local])
        t_min = float(t[local])
    else:
        minimum = float("nan")
        t_min = float("nan")
    depth = pre - minimum
    post = float(np.median(ilq[post_m]))
    recovery_ps = None
    if np.isfinite(depth) and depth > 0:
        target = minimum + 0.9 * depth
        for i in range(activity_i[0] if len(activity_i) else 0, len(t)):
            if t[i] >= t_min and ilq[i] >= target:
                recovery_ps = float(t[i] - t_min)
                break
    first_end = None
    complete = [x for x in bq_metrics["activity"]["segments"] if x["complete_candidate"]]
    if complete:
        first_end = min(x["end_ps"] for x in complete)
    later_lobes = [x for x in bq_metrics["activity"]["segments"] if x["start_ps"] > (first_end or 0.0)]
    return {
        "pre_median_uA": pre * 1e6,
        "activity_min_uA": minimum * 1e6,
        "minimum_time_ps": t_min,
        "depletion_depth_uA": depth * 1e6,
        "post_median_uA": post * 1e6,
        "recovery_90_time_ps": recovery_ps,
        "first_complete_bq_end_ps": first_end,
        "detector_later_activity_segments_after_first_bq": len(later_lobes),
    }


def case_metrics(case):
    path = ROOT / "raw" / f"{case}.csv"
    t, data = load(path)
    c_path = R15C / "raw" / f"{case}.csv"
    c_t, c_data = load(c_path)
    b_path = R15B / "raw" / f"{case}.csv"
    b_t, b_data = load(b_path)
    phases = {name: phase_metrics(t, data, pcol, vcol) for name, (pcol, vcol) in PHASES.items()}
    cur = {
        name: {window: stats(data[column][mask(t, bounds)], 1e6) for window, bounds in WINDOWS.items()}
        for name, column in CURRENT_COLUMNS.items()
    }
    # Element currents follow the declared branch orientation. These residuals
    # are diagnostic KCL checks, not event metrics.
    kcl_set = data[CURRENT_COLUMNS["I_ISET"]] - data[CURRENT_COLUMNS["I_RBIAS"]] - data[CURRENT_COLUMNS["I_LRET"]]
    kcl_q_source = data[CURRENT_COLUMNS["I_IQ"]] - data[CURRENT_COLUMNS["I_RQ"]] - data[CURRENT_COLUMNS["I_LQ"]]
    kcl_q_node = data[CURRENT_COLUMNS["I_BSET"]] + data[CURRENT_COLUMNS["I_LQ"]] - data[CURRENT_COLUMNS["I_BQ"]]
    return {
        "artifact": artifact(path, t),
        "phase": phases,
        "current": cur,
        "node_voltage_uV": {
            "N_QJ": {w: stats(data["V(N_QJ|XR15D)"][mask(t, b)], 1e6) for w, b in WINDOWS.items()},
            "N_QB": {w: stats(data["V(N_QB|XR15D)"][mask(t, b)], 1e6) for w, b in WINDOWS.items()},
        },
        "kcl_residual_uA": {
            "I_SET_minus_RBIAS_minus_LRET": stats(kcl_set[mask(t, WINDOWS["activity"])], 1e6),
            "I_Q_minus_RQ_minus_LQ": stats(kcl_q_source[mask(t, WINDOWS["activity"])], 1e6),
            "B_SET_plus_LQ_minus_B_Q": stats(kcl_q_node[mask(t, WINDOWS["activity"])], 1e6),
        },
        "lq_refractory": lq_refractory(t, data, phases["B_Q"]),
        "source_delta_vs_r15c": source_delta(t, data, c_t, c_data),
        "absolute_source_post_p2p": absolute_source_post(t, data, c_t, c_data, b_t, b_data),
    }


def max_abs(stat):
    return max(abs(stat["min"]), abs(stat["max"]))


def main():
    cases = {case: case_metrics(case) for case in CASES}
    read1 = cases["logical1-read"]
    read0 = cases["logical0-read"]
    ctrls = [cases["logical1-read0-control"], cases["logical0-read0-control"]]

    bset_r1 = read1["phase"]["B_SET"]["activity"]
    bset_r0 = read0["phase"]["B_SET"]["activity"]
    bq_r1 = read1["phase"]["B_Q"]["activity"]
    bq_r0 = read0["phase"]["B_Q"]["activity"]
    ctrl_bq = [c["phase"]["B_Q"]["activity"] for c in ctrls]
    read1_bq_events = bq_r1["complete_candidate_count"]
    read0_bq_events = bq_r0["complete_candidate_count"]
    ctrl_bq_events = sum(x["complete_candidate_count"] for x in ctrl_bq)
    read1_jset_mod = read1["current"]["I_BSET"]["activity"]["p2p"]
    read0_jset_mod = read0["current"]["I_BSET"]["activity"]["p2p"]
    ctrl_jset_mod = max(c["current"]["I_BSET"]["activity"]["p2p"] for c in ctrls)
    causal_ratio = read1_jset_mod / read0_jset_mod if read0_jset_mod else math.inf

    # A control event is a hard nonselectivity boundary. The near-threshold
    # label is used for a selective sub-turn response with no B_Q event.
    if ctrl_bq_events or read0_bq_events:
        verdict = "NONSELECTIVE_TRIGGER"
    elif read1_bq_events > 1:
        verdict = "MULTIFIRE"
    elif read1_bq_events == 1:
        refractory = read1["lq_refractory"]
        if refractory["depletion_depth_uA"] > 0 and refractory["recovery_90_time_ps"] is not None:
            verdict = "JQ_ONE_SHOT_REFRACTORY_PASS"
        else:
            verdict = "INCONCLUSIVE"
    elif read1_jset_mod > max(2.0 * read0_jset_mod, 5.0 * ctrl_jset_mod):
        verdict = "JQ_CAUSAL_NEAR_THRESHOLD"
    elif read1_jset_mod <= max(2.0 * read0_jset_mod, 2.0 * ctrl_jset_mod):
        verdict = "UPSTREAM_CAUSAL_LOADING_FAILURE"
    else:
        verdict = "INCONCLUSIVE"

    result = {
        "experiment": "R15-D",
        "windows_ps": WINDOWS,
        "parameters": {
            "R_IN_ohm": 12.0,
            "L_TX_pH": 0.20,
            "K_IN": -0.80,
            "I_DET_uA": 15.0,
            "I_SET_uA": 5.6,
            "R_BIAS_ohm": 27.5,
            "L_RET_pH": 5.0,
            "L_S_pH": 50.0,
            "B_DET_AREA": 0.50,
            "B_SET_AREA": 0.08,
            "I_Q_uA": 2.30,
            "R_Q_ohm": 2.0,
            "L_Q_pH": 40.0,
            "B_Q_AREA": 0.10,
        },
        "verdict": verdict,
        "read1_read0_jset_modulation_ratio": causal_ratio,
        "read1_control_jset_modulation_ratio": read1_jset_mod / ctrl_jset_mod if ctrl_jset_mod else math.inf,
        "read1_jset_activity_p2p_uA": read1_jset_mod,
        "read0_jset_activity_p2p_uA": read0_jset_mod,
        "control_jset_activity_p2p_uA": ctrl_jset_mod,
        "accepted_canonical_read1_post_p2p": {
            "V(SL)_uV": 1.631,
            "V(N6)_uV": 3.271,
            "I(L_SL)_uA": 0.1359,
            "P(JM2)_rad": 0.26827,
            "P(JS1)_rad": 0.05604,
            "P(JS2)_rad": 0.00554,
        },
        "cases": cases,
    }
    metrics_path = ROOT / "analysis" / "r15d-execution-metrics.json"
    metrics_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")

    fields = [
        "case", "B_DET_largest_turns", "B_SET_largest_turns", "B_SET_area_turns", "B_SET_events",
        "B_Q_activity_turns", "B_Q_largest_turns", "B_Q_area_turns", "B_Q_events",
        "I_BSET_min_uA", "I_BSET_max_uA", "I_BSET_p2p_uA", "I_BQ_min_uA", "I_BQ_max_uA",
        "I_LQ_pre_uA", "I_LQ_min_uA", "I_LQ_depletion_uA", "I_LQ_recovery90_ps",
    ]
    with (ROOT / "analysis" / "r15d-case-summary.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for case, item in cases.items():
            bs = item["phase"]["B_SET"]["activity"]
            bq = item["phase"]["B_Q"]["activity"]
            bs_seg = bs["largest_segment"] or {}
            bq_seg = bq["largest_segment"] or {}
            lq = item["lq_refractory"]
            writer.writerow({
                "case": case,
                "B_DET_largest_turns": (item["phase"]["B_DET"]["activity"]["largest_segment"] or {}).get("phase_delta_turns"),
                "B_SET_largest_turns": bs_seg.get("phase_delta_turns"),
                "B_SET_area_turns": bs_seg.get("voltage_area_turns"),
                "B_SET_events": bs["complete_candidate_count"],
                "B_Q_activity_turns": bq["activity_range_turns"],
                "B_Q_largest_turns": bq_seg.get("phase_delta_turns"),
                "B_Q_area_turns": bq_seg.get("voltage_area_turns"),
                "B_Q_events": bq["complete_candidate_count"],
                "I_BSET_min_uA": item["current"]["I_BSET"]["activity"]["min"],
                "I_BSET_max_uA": item["current"]["I_BSET"]["activity"]["max"],
                "I_BSET_p2p_uA": item["current"]["I_BSET"]["activity"]["p2p"],
                "I_BQ_min_uA": item["current"]["I_BQ"]["activity"]["min"],
                "I_BQ_max_uA": item["current"]["I_BQ"]["activity"]["max"],
                "I_LQ_pre_uA": lq["pre_median_uA"],
                "I_LQ_min_uA": lq["activity_min_uA"],
                "I_LQ_depletion_uA": lq["depletion_depth_uA"],
                "I_LQ_recovery90_ps": lq["recovery_90_time_ps"],
            })

    lines = [
        "# R15-D execution report",
        "",
        f"Verdict: **`{verdict}`**",
        "",
        "This report audits the single preregistered split-node + independent J_Q bias + RL refractory compressor point. No J_OUT, DCSFQ, JTL, or T1 is present.",
        "",
        "## Matched cases",
        "",
        "| case | B_DET largest (turn) | B_SET largest (turn) | B_SET area (turn) | B_Q activity (turn) | B_Q largest (turn) | B_Q area (turn) | B_Q events | I_BSET activity min..max (uA) | I_LQ depletion (uA) | recovery 90% (ps) |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for case, item in cases.items():
        bd = item["phase"]["B_DET"]["activity"]["largest_segment"] or {}
        bs = item["phase"]["B_SET"]["activity"]["largest_segment"] or {}
        bq = item["phase"]["B_Q"]["activity"]
        bqs = bq["largest_segment"] or {}
        cur = item["current"]["I_BSET"]["activity"]
        lq = item["lq_refractory"]
        lines.append(
            f"| {case} | {bd.get('phase_delta_turns', float('nan')):.6g} | "
            f"{bs.get('phase_delta_turns', float('nan')):.6g} | {bs.get('voltage_area_turns', float('nan')):.6g} | "
            f"{bq['activity_range_turns']:.6g} | {bqs.get('phase_delta_turns', float('nan')):.6g} | "
            f"{bqs.get('voltage_area_turns', float('nan')):.6g} | {bq['complete_candidate_count']} | "
            f"{cur['min']:.6g}..{cur['max']:.6g} | {lq['depletion_depth_uA']:.6g} | {lq['recovery_90_time_ps']} |"
        )
    lines += [
        "",
        "## Event boundary",
        "",
        "A complete event requires a continuous monotonic unwrapped phase segment of at least one turn and same-segment voltage area consistency under the task-local 5%/0.02-turn rule. Current or voltage peaks alone are not used.",
        "",
        "## R15-C comparison",
        "",
        f"Read1 B_SET current modulation p2p: {read1_jset_mod:.6g} uA; read0: {read0_jset_mod:.6g} uA; maximum control: {ctrl_jset_mod:.6g} uA; read1/read0 ratio: {causal_ratio:.6g}.",
        "The full per-window source comparison against matching R15-C raw cases is stored in `r15d-execution-metrics.json`. This is a differential guard; R15-C's accepted comparison to its canonical/no-receiver baseline remains unchanged.",
        "",
        "### Absolute read1 post-window source comparison",
        "",
        "The canonical column is the accepted no-receiver read1 post-window reference quoted in the R15-B report; R15-B/R15-C/R15-D are recomputed from their matching raw CSVs.",
        "",
        "| quantity | canonical no receiver | R15-B | R15-C | R15-D |",
        "|---|---:|---:|---:|---:|",
        f"| V(SL) p2p (uV) | 1.631 | {read1['absolute_source_post_p2p']['V(SL)']['r15b_p2p']:.6g} | {read1['absolute_source_post_p2p']['V(SL)']['r15c_p2p']:.6g} | {read1['absolute_source_post_p2p']['V(SL)']['r15d_p2p']:.6g} |",
        f"| V(N6) p2p (uV) | 3.271 | {read1['absolute_source_post_p2p']['V(N6)']['r15b_p2p']:.6g} | {read1['absolute_source_post_p2p']['V(N6)']['r15c_p2p']:.6g} | {read1['absolute_source_post_p2p']['V(N6)']['r15d_p2p']:.6g} |",
        f"| I(L_SL) p2p (uA) | 0.1359 | {read1['absolute_source_post_p2p']['I(L_SL)']['r15b_p2p']:.6g} | {read1['absolute_source_post_p2p']['I(L_SL)']['r15c_p2p']:.6g} | {read1['absolute_source_post_p2p']['I(L_SL)']['r15d_p2p']:.6g} |",
        f"| P(JM2) p2p (rad) | 0.26827 | {read1['absolute_source_post_p2p']['P(JM2)']['r15b_p2p']:.6g} | {read1['absolute_source_post_p2p']['P(JM2)']['r15c_p2p']:.6g} | {read1['absolute_source_post_p2p']['P(JM2)']['r15d_p2p']:.6g} |",
        f"| P(JS1) p2p (rad) | 0.05604 | {read1['absolute_source_post_p2p']['P(JS1)']['r15b_p2p']:.6g} | {read1['absolute_source_post_p2p']['P(JS1)']['r15c_p2p']:.6g} | {read1['absolute_source_post_p2p']['P(JS1)']['r15d_p2p']:.6g} |",
        f"| P(JS2) p2p (rad) | 0.00554 | {read1['absolute_source_post_p2p']['P(JS2)']['r15b_p2p']:.6g} | {read1['absolute_source_post_p2p']['P(JS2)']['r15c_p2p']:.6g} | {read1['absolute_source_post_p2p']['P(JS2)']['r15d_p2p']:.6g} |",
        "",
        "R15-D remains bounded and has no control running or storage-sign collapse, but its read1 post-window source ringing is still orders of magnitude above the canonical no-receiver reference and is higher than R15-C for the listed SL/N6/JM2/JS probes. The source guard is therefore a bounded extra-back-action disposition, not a pristine isolation pass.",
        "",
        "## Settled operating point and refractory diagnostic",
        "",
        f"In the new READ=0 settled window, representative medians are I(B_SET)={read1['current']['I_BSET']['pre']['median']:.6g} uA, I(L_Q)={read1['current']['I_LQ']['pre']['median']:.6g} uA, I(R_Q)={read1['current']['I_RQ']['pre']['median']:.6g} uA, and I(B_Q)={read1['current']['I_BQ']['pre']['median']:.6g} uA. B_Q AREA=.10 has Ic=10 uA; this ratio is only an operating-point diagnostic, not event evidence.",
        f"For read1, I(L_Q) reaches {read1['lq_refractory']['activity_min_uA']:.6g} uA at {read1['lq_refractory']['minimum_time_ps']:.6g} ps from a pre median of {read1['lq_refractory']['pre_median_uA']:.6g} uA, a derived depletion of {read1['lq_refractory']['depletion_depth_uA']:.6g} uA; 90% recovery takes {read1['lq_refractory']['recovery_90_time_ps']:.6g} ps and the post median is {read1['lq_refractory']['post_median_uA']:.6g} uA. This is an observed L_Q transient, but because B_Q never completes a phase event it is not refractory one-shot evidence.",
        "",
        "## Stage disposition",
        "",
        "- Stage 1 `UPSTREAM_CAUSAL_PRESERVED`: met for state selectivity; B_DET read1 remains multi-turn and read0/control remain sub-turn, while loaded B_SET current remains strongly read1 selective.",
        "- Stage 2 `JQ_ONE_SHOT`: not met; read1 B_Q largest segment is 0.111790 turn with same-segment area 0.111829 turn, and all read0/control cases have zero complete candidates.",
        "- Stage 3 `REFRACTORY_ESTABLISHED`: not met; L_Q depletion/recovery is visible but no first complete J_Q event exists from which to establish refractory suppression.",
        "- Stage 4 `SOURCE_GUARD`: bounded but not pristine; no startup/free-running or control event, but loaded read1 source ringing remains materially above canonical and is not lower than R15-C on all probes.",
        "",
        "## Observed / Derived / Inference / Unknown",
        "",
        "- **Observed:** raw phase, same-JJ voltage, currents, node voltages, BVM guard probes, KCL residuals, and L_Q time behavior for each completed case are recorded in the metrics JSON.",
        "- **Derived:** event candidates, phase/area residuals, read1/read0 J_SET modulation ratios, and L_Q depletion/recovery metrics are computed from the same raw run and preregistered windows.",
        "- **Inference:** the verdict is limited to this frozen loaded fixture; it does not generalize to the broader active-stage family.",
        "- **Unknown:** downstream output conversion and JTL transport were not tested by design.",
        "",
    ]
    (ROOT / "analysis" / "R15D_EXECUTION_REPORT.md").write_text("\n".join(lines))

    summary = [
        "# R15-D summary",
        "",
        f"- Verdict: **`{verdict}`**",
        f"- Parent: R15-C `{R15C.name}` / accepted commit `97598b4dc3d461b79310a15108f170eb16f7fb91`",
        "- Point: B_SET AREA=.08; I_Q=2.30 uA; R_Q=2 ohm; L_Q=40 pH; B_Q AREA=.10; upstream R15-C values frozen.",
        "- No downstream J_OUT/DCSFQ/JTL/T1.",
        "- Stage 1 causal/selective response preserved; Stage 2 complete J_Q event and Stage 3 refractory criterion not met.",
        "- Source disposition: bounded extra back-action, not a pristine isolation pass relative to canonical/R15-C.",
        "- Full evidence: `analysis/R15D_EXECUTION_REPORT.md`, `analysis/r15d-case-summary.csv`, and `analysis/r15d-execution-metrics.json`.",
    ]
    (ROOT / "SUMMARY.md").write_text("\n".join(summary) + "\n")


if __name__ == "__main__":
    main()
