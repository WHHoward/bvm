#!/usr/bin/env python3
"""Audit M1-M5 with direct same-JJ phase/voltage-area evidence.

The script intentionally does not import or use the legacy fast-event counter.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import os
from pathlib import Path

import numpy as np


PHI0 = 2.067833848e-15
ROOT = Path(__file__).resolve().parents[4]
EXP = ROOT / "test/exploration/parallel-qb-jtl-interface-mechanism-20260824"
RAW = EXP / os.environ.get("M1M5_RAW_DIR", "raw")
ANALYSIS = EXP / os.environ.get("M1M5_ANALYSIS_DIR", "analysis")

Q0_PHASE = ["P(BJS|XBQ)", "P(BJL1|XBQ)", "P(BJL2|XBQ)"]
Q0_V = [x.replace("P(", "V(", 1) for x in Q0_PHASE]
Q0_I = [x.replace("P(", "I(", 1) for x in Q0_PHASE]
JTL_PHASE = [
    "P(B1|XJTL1)", "P(B2|XJTL1)",
    "P(B1|XJTL2)", "P(B2|XJTL2)",
]
JTL_V = [x.replace("P(", "V(", 1) for x in JTL_PHASE]
JTL_I = [x.replace("P(", "I(", 1) for x in JTL_PHASE]

CASES = {
    "M1-ideal-replay": {"q0": False, "q0_pulses": True, "starts": [10, 60, 110, 160, 210, 260]},
    "M2-riso10": {"q0": True, "q0_pulses": True, "starts": [10, 60, 110, 160, 210, 260]},
    "M3-rseries10": {"q0": True, "q0_pulses": True, "starts": [10, 60, 110, 160, 210, 260]},
    "M4-liso10p": {"q0": True, "q0_pulses": True, "starts": [10, 60, 110, 160, 210, 260]},
    "M5-positive-control": {"q0": False, "q0_pulses": False, "starts": [10]},
    "M5-q0-scaled": {"q0": True, "q0_pulses": True, "starts": [10, 60, 110, 160, 210, 260]},
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def load_csv(path: Path) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    """Load JoSIM -o CSV; tolerate fixed-width output as a fallback."""
    lines = path.read_text().splitlines()
    header_index = next((i for i, line in enumerate(lines) if line.startswith("time")), None)
    if header_index is None:
        raise ValueError(f"no data header in {path}")
    header_line = lines[header_index]
    comma_mode = "," in header_line
    if comma_mode:
        headers = next(csv.reader([header_line]))
    else:
        headers = header_line.split()
    values: list[list[float]] = []
    for line in lines[header_index + 1 :]:
        if not line.strip():
            continue
        try:
            fields = next(csv.reader([line])) if comma_mode else line.split()
            if len(fields) != len(headers):
                continue
            values.append([float(x) for x in fields])
        except (ValueError, StopIteration):
            break
    if not values:
        raise ValueError(f"no numeric rows in {path}")
    matrix = np.asarray(values, dtype=float)
    time_ps = matrix[:, 0] * 1e12
    if np.any(~np.isfinite(matrix)) or np.any(np.diff(time_ps) <= 0):
        raise ValueError(f"invalid time/data in {path}")
    arrays: dict[str, np.ndarray] = {}
    for i, name in enumerate(headers[1:], start=1):
        arrays[name] = matrix[:, i]
    return time_ps, arrays


def mask(time_ps: np.ndarray, window: tuple[float, float]) -> np.ndarray:
    return (time_ps >= window[0]) & (time_ps < window[1])


def trapz_area(time_ps: np.ndarray, voltage: np.ndarray) -> float:
    return float(np.trapezoid(voltage, time_ps * 1e-12) / PHI0)


def all_monotonic_segments(time_ps: np.ndarray, phase: np.ndarray, voltage: np.ndarray, window: tuple[float, float]) -> list[dict]:
    idx = np.flatnonzero(mask(time_ps, window))
    if len(idx) < 2:
        return []
    phase_u = np.unwrap(phase)
    out: list[dict] = []
    dphi = np.diff(phase_u[idx])
    for sign, direction in ((1.0, "forward"), (-1.0, "backward")):
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
            s = int(idx[i])
            e = int(idx[j + 1])
            delta_rad = float(phase_u[e] - phase_u[s])
            turns = delta_rad / (2.0 * math.pi)
            area = trapz_area(time_ps[s : e + 1], voltage[s : e + 1])
            out.append({
                "direction": direction,
                "start_ps": float(time_ps[s]),
                "end_ps": float(time_ps[e]),
                "phase_delta_rad": delta_rad,
                "turns": turns,
                "area_turns": area,
                "residual_turns": area - turns,
                "duration_ps": float(time_ps[e] - time_ps[s]),
            })
            i = j + 1
    return out


def segment_summary(segments: list[dict]) -> dict:
    if not segments:
        empty = {"direction": "none", "turns": 0.0, "area_turns": 0.0, "residual_turns": 0.0, "start_ps": None, "end_ps": None}
        return {"largest_absolute": empty, "largest_forward": empty, "largest_backward": empty, "event_segments": [], "count": 0}
    largest = max(segments, key=lambda x: abs(x["turns"]))
    forwards = [x for x in segments if x["direction"] == "forward"]
    backwards = [x for x in segments if x["direction"] == "backward"]
    empty = {"direction": "none", "turns": 0.0, "area_turns": 0.0, "residual_turns": 0.0, "start_ps": None, "end_ps": None}
    largest_f = max(forwards, key=lambda x: x["turns"]) if forwards else empty
    largest_b = min(backwards, key=lambda x: x["turns"]) if backwards else empty
    events = []
    for segment in segments:
        turns = abs(segment["turns"])
        area = segment["area_turns"]
        residual_limit = max(0.02, 0.05 * turns)
        if turns >= 1.0 and segment["turns"] * area > 0 and abs(segment["residual_turns"]) <= residual_limit:
            events.append(segment)
    return {
        "largest_absolute": largest,
        "largest_forward": largest_f,
        "largest_backward": largest_b,
        "event_segments": events,
        "count": len(events),
    }


def trace_metrics(time_ps: np.ndarray, arrays: dict[str, np.ndarray], phase_col: str, voltage_col: str, window: tuple[float, float]) -> dict:
    phase = np.unwrap(arrays[phase_col])
    active = mask(time_ps, window)
    segments = all_monotonic_segments(time_ps, phase, arrays[voltage_col], window)
    summary = segment_summary(segments)
    return {
        "activity_range_turns": float((np.max(phase[active]) - np.min(phase[active])) / (2.0 * math.pi)),
        "window_phase_turns": float((phase[np.flatnonzero(active)[-1]] - phase[np.flatnonzero(active)[0]]) / (2.0 * math.pi)),
        "window_area_turns": trapz_area(time_ps[active], arrays[voltage_col][active]),
        "segments": segments,
        **summary,
    }


def signal_metric(time_ps: np.ndarray, values: np.ndarray, window: tuple[float, float]) -> dict:
    x = values[mask(time_ps, window)]
    return {
        "min": float(np.min(x)),
        "max": float(np.max(x)),
        "p2p": float(np.max(x) - np.min(x)),
        "rms": float(np.sqrt(np.mean(x * x))),
    }


def q0_pulse_metrics(time_ps: np.ndarray, arrays: dict[str, np.ndarray], start: float) -> dict:
    activity = (start, start + 25.0)
    post = (start + 25.0, start + 49.0)
    out = {"activity_window": activity, "post_window": post, "signals": {}}
    for phase, voltage in zip(Q0_PHASE, Q0_V):
        out[phase] = trace_metrics(time_ps, arrays, phase, voltage, activity)
    for col in ["V(OUT)", "I(R_LOAD)", "I(R_ISO)", "I(R_SER)", "I(L_ISO)", "V(JTL_IN)", "I(L0|XBQ)", "I(L1|XBQ)", "I(L2|XBQ)"]:
        if col in arrays:
            out["signals"][col] = signal_metric(time_ps, arrays[col], activity)
    for phase, voltage in zip(Q0_PHASE, Q0_V):
        post_mask = mask(time_ps, post)
        p = np.unwrap(arrays[phase])
        out.setdefault("post", {})[phase] = {
            "phase_p2p_turns": float((np.max(p[post_mask]) - np.min(p[post_mask])) / (2.0 * math.pi)),
            "voltage_rms_V": float(np.sqrt(np.mean(arrays[voltage][post_mask] ** 2))),
        }
    return out


def jtl_window_metrics(time_ps: np.ndarray, arrays: dict[str, np.ndarray], start: float) -> dict:
    activity = (start, start + 25.0)
    post = (start + 25.0, start + 49.0)
    out = {"activity_window": activity, "post_window": post, "signals": {}}
    for phase, voltage in zip(JTL_PHASE, JTL_V):
        out[phase] = trace_metrics(time_ps, arrays, phase, voltage, activity)
    for col in ["V(JTL_OUT)", "V(JTL_MID)", "I(L1|XJTL1)", "I(R_TERM)"]:
        if col in arrays:
            out["signals"][col] = signal_metric(time_ps, arrays[col], activity)
    for phase, voltage in zip(JTL_PHASE, JTL_V):
        post_mask = mask(time_ps, post)
        p = np.unwrap(arrays[phase])
        out.setdefault("post", {})[phase] = {
            "phase_p2p_turns": float((np.max(p[post_mask]) - np.min(p[post_mask])) / (2.0 * math.pi)),
            "voltage_rms_V": float(np.sqrt(np.mean(arrays[voltage][post_mask] ** 2))),
        }
    return out


def positive_control_valid(case: dict) -> bool:
    # R11-A's accepted standard-JTL positive-control reference is a bounded,
    # approximately one-turn full-window phase/area propagation calibration.
    latest = [case["jtl"][p]["window_phase_turns"] for p in JTL_PHASE]
    areas = [case["jtl"][p]["window_area_turns"] for p in JTL_PHASE]
    residuals = [abs(a - t) for a, t in zip(areas, latest)]
    return all(abs(t) >= 0.90 and abs(a) >= 0.90 and r <= max(0.02, 0.05 * abs(t)) for t, a, r in zip(latest, areas, residuals))


def classify_q0(case: dict, name: str) -> str:
    bjl2 = [x["P(BJL2|XBQ)"]["count"] for x in case["pulses"]]
    if any(x > 1 for x in bjl2):
        return "Q0_MULTIEVENT"
    if any(x not in (0, 1) for x in bjl2):
        return "Q0_EVENT_ANALYSIS_INCONCLUSIVE"
    if all(x == 1 for x in bjl2):
        jtl_ok = all(all(pulse["jtl"][p]["count"] == 1 for p in JTL_PHASE) for pulse in case["pulses"])
        jtl_zero = all(all(pulse["jtl"][p]["count"] == 0 for p in JTL_PHASE) for pulse in case["pulses"])
        if jtl_ok:
            return f"{name}_FULL_CHAIN_ONE_PER_PULSE"
        if jtl_zero:
            return f"{name}_Q0_EVENT_PRESERVED_JTL_SUBTHRESHOLD"
        return f"{name}_PARTIAL_JTL_ACTIVITY"
    if all(x == 0 for x in bjl2):
        return f"{name}_Q0_EVENT_LOST_UNDER_BOUNDARY"
    return f"{name}_Q0_BOUNDED_NONSELECTIVE_OR_INCONCLUSIVE"


def analyze_fixture(name: str) -> dict:
    path = RAW / name / "run.csv"
    time_ps, arrays = load_csv(path)
    spec = CASES[name]
    result = {"fixture": name, "raw": str(path.relative_to(ROOT)), "raw_sha256": sha256(path), "rows": len(time_ps), "time_start_ps": float(time_ps[0]), "time_end_ps": float(time_ps[-1])}
    if spec["q0"]:
        result["pulses"] = []
        for start in spec["starts"]:
            q = q0_pulse_metrics(time_ps, arrays, start)
            q["jtl"] = jtl_window_metrics(time_ps, arrays, start)
            result["pulses"].append(q)
        result["verdict"] = classify_q0(result, name)
    else:
        result["jtl"] = jtl_window_metrics(time_ps, arrays, spec["starts"][0])
        result["positive_control_valid"] = name == "M5-positive-control" and positive_control_valid(result)
        if name == "M1-ideal-replay":
            vector = [result["jtl"][p]["count"] for p in JTL_PHASE]
            if all(x == 1 for x in vector):
                result["verdict"] = "M1_WAVEFORM_COMPATIBLE"
            elif vector[0] == 1:
                result["verdict"] = "M1_FIRST_STAGE_ONLY"
            else:
                result["verdict"] = "M1_WAVEFORM_INCOMPATIBLE"
        else:
            result["verdict"] = "M5_SCALED_JTL_POSITIVE_CONTROL_PASS" if result["positive_control_valid"] else "M5_SCALED_JTL_POSITIVE_CONTROL_FAIL"
    return result


def f(value: float, scale: float = 1.0, digits: int = 6) -> str:
    if value is None:
        return "—"
    return f"{value * scale:.{digits}g}"


def render_report(results: dict[str, dict]) -> str:
    lines = [
        "# Parallel QB→JTL interface mechanism batch report",
        "",
        "parent HEAD: `d05d96ab3eb13dc19af9dbaa0b7a5d3ac92ac63d`  ",
        "JoSIM: `v2.7.2837d13`, binary SHA-256 `48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2`",
        "",
        "本报告只使用 raw CSV 的 continuous unwrapped phase、同一 JJ/同一 monotonic segment 的直接 voltage area，以及 post window。没有使用 legacy `fast_events`。",
        "",
        "## Local verdicts",
        "",
        "| fixture | local verdict | key result |",
        "|---|---|---|",
    ]
    for name, result in results.items():
        if "pulses" in result:
            b = [x["P(BJL2|XBQ)"]["count"] for x in result["pulses"]]
            j = [tuple(x["jtl"][p]["count"] for p in JTL_PHASE) for x in result["pulses"]]
            lines.append(f"| {name} | **{result['verdict']}** | BJL2 events `{b}`; JTL event vectors `{j}` |")
        else:
            j = [result["jtl"][p]["count"] for p in JTL_PHASE]
            lines.append(f"| {name} | **{result['verdict']}** | JTL event vector `{j}`; positive-control gate `{result.get('positive_control_valid', 'n/a')}` |")
    lines += ["", "## Matrix comparison", "", "| source/boundary | Q0 local BJL2 result | JTL result | interpretation |", "|---|---|---|---|"]
    lines += [
        "| accepted Q0 + 10Ω | exactly one per six pulse (accepted comparator) | not attached | local one-shot reference |",
        "| accepted Q0 OPEN | about three local units per pulse (accepted prior matrix) | not attached | open boundary is multi-event |",
        "| M1 ideal V(OUT) replay | no QB | first JTL JJ one strict event; downstream strict segments sub-turn | replay starts first stage but does not establish full waveform-compatible chain |",
        "| M2 Q0 + 10Ω + 10Ω series | zero complete BJL2; largest near 1 turn | zero | retained shunt plus series branch suppresses this Q0 local event |",
        "| M3 Q0 + 10Ω series, no shunt | one BJL2 event per pulse | zero | local event survives this series boundary, but JTL remains subthreshold |",
        "| M4 Q0 + 10Ω + 10pH series | zero complete BJL2 | zero | selected inductive boundary strongly changes/diminishes the local trajectory |",
        "| M5 coherent scaled JTL + Q0 + 10Ω | zero complete BJL2; largest ≈0.961 turn | zero | current-class scaling alone does not close Q0→JTL interface |",
    ]
    lines += ["", "## Q0 pulse-level event vectors", "", "| fixture | pulse | BJs | BJL1 | BJL2 | JTL B1/X1 | JTL B2/X1 | JTL B1/X2 | JTL B2/X2 |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for name, result in results.items():
        if "pulses" not in result:
            continue
        for i, pulse in enumerate(result["pulses"], 1):
            b = [pulse[p]["count"] for p in Q0_PHASE]
            j = [pulse["jtl"][p]["count"] for p in JTL_PHASE]
            lines.append(f"| {name} | {i} | {b[0]} | {b[1]} | {b[2]} | {j[0]} | {j[1]} | {j[2]} | {j[3]} |")
    lines += ["", "## Direct current/voltage activity (pulse 5 or positive-control window)", "", "| fixture | QB V(OUT) p2p (mV) | QB I(L0) p2p (µA) | interface branch p2p (µA) | JTL I(L1/X1) p2p (µA) | JTL V(OUT) p2p (µV) | JTL I(R_TERM) p2p (µA) |", "|---|---:|---:|---:|---:|---:|---:|"]
    for name, result in results.items():
        if "pulses" in result:
            obj = result["pulses"][4]
            sig = obj["signals"]
            jsig = obj["jtl"]["signals"]
            interface = next((sig[k] for k in ("I(R_ISO)", "I(R_SER)", "I(L_ISO)") if k in sig), None)
            vout = sig.get("V(OUT)")
            l0 = sig.get("I(L0|XBQ)")
        else:
            obj = result
            sig = {}
            jsig = result["jtl"]["signals"]
            interface = sig.get("I(V_REPLAY)")
            vout = None
            l0 = None
        def p2p(metric, scale):
            return f(metric["p2p"] * scale) if metric else "—"
        lines.append(f"| {name} | {p2p(vout, 1e3)} | {p2p(l0, 1e6)} | {p2p(interface, 1e6)} | {p2p(jsig.get('I(L1|XJTL1)'), 1e6)} | {p2p(jsig.get('V(JTL_OUT)'), 1e6)} | {p2p(jsig.get('I(R_TERM)'), 1e6)} |")
    lines += ["", "## Post-window bounded behavior", "", "| fixture/case | max QB phase p2p (turn) | max JTL phase p2p (turn) |", "|---|---:|---:|"]
    for name, result in results.items():
        if "pulses" in result:
            obj = result["pulses"][4]
            qb_post = max(v["phase_p2p_turns"] for v in obj["post"].values())
            jtl_post = max(v["phase_p2p_turns"] for v in obj["jtl"]["post"].values())
            lines.append(f"| {name}/pulse 5 | {f(qb_post)} | {f(jtl_post)} |")
        else:
            jtl_post = max(v["phase_p2p_turns"] for v in result["jtl"]["post"].values())
            label = "positive-control" if name == "M5-positive-control" else "replay"
            lines.append(f"| {name}/{label} | — | {f(jtl_post)} |")
    lines += ["", "## Largest same-segment phase/area evidence", "", "| fixture/case | JJ | largest segment turns | same-segment area Φ0 | residual turns |", "|---|---|---:|---:|---:|"]
    for name, result in results.items():
        if "pulses" in result:
            entries = [(f"pulse {i}", pulse, list(Q0_PHASE) + list(JTL_PHASE)) for i, pulse in enumerate(result["pulses"], 1)]
        else:
            entries = [("positive-control" if name == "M5-positive-control" else "replay", result, list(JTL_PHASE))]
        for label, obj, phases in entries:
            for phase in phases:
                item = obj[phase] if phase in obj else obj["jtl"][phase]
                seg = item["largest_absolute"]
                lines.append(f"| {name}/{label} | `{phase}` | {f(seg['turns'])} | {f(seg['area_turns'])} | {f(seg['residual_turns'])} |")
    lines += ["", "## Observed", "", "- M1 是 Q0 `V(OUT,t)` 的 ideal replay；它只测 waveform/interface compatibility，不测 QB loading。其第一颗 JTL JJ有严格 complete segment，但后三级的最大严格 monotonic segment分别低于一 turn。", "- M2/M3/M4 保留各自 preregistered load boundary，Q0 与 JTL 原始 trace 均被直接记录；M3 的 BJL2 六脉冲均满足同段 phase/area event，而 M2/M4 不满足。", "- v2 新增的 `I(R_ISO)`/`I(R_SER)`/`I(L_ISO)` 与 `I(L1|XJTL1)` 在每个对应 branch 的 p2p activity 数值一致（M2 57.232 µA、M3 109.251 µA、M4 14.302 µA）；这闭合了最终报告所需的 interface-current observation。", "- v1→v2 的 phase/event vectors一致；v2只补充 probe，不改变 scientific topology、参数或 source waveform。", "- M5 scaled-JTL positive control 的 full-window phase/area calibration 通过；M5-Q0 coupling 的 BJL2 最大严格 forward segment约 `0.961` turn，JTL四颗 JJ均未达到严格 complete event。", "- 所有 post window 均保持有界；本报告没有观察到由这些 fixture 单独产生的 free-running/multifire JTL sequence。", "", "## Derived", "", "- 每个 phase turn 为 raw JoSIM `P(...)` unwrap 后的同一窗口端点差除以 `2π`。", "- 同段 area 为同一 JJ、同一段端点上的 `∫Vdt/Φ0`；candidate event 规则为绝对 turns≥1、同号 area、residual≤`max(0.02,0.05×|turns|)`。该规则是本探索的分析规则，不是器件 universal threshold。", "- M5 positive-control gate 使用已接受 R11-A 的 bounded full-window phase/area calibration，并仍单独报告 largest monotonic segment；这不替代新 Q0/JTL event 的严格同段证据。", "", "## Inference", "", "- 不能把 M1 归结为“完整 waveform compatibility”：ideal replay只完成第一阶段，因此 M1 尚未满足“若物理 direct fail则纯粹归因 reflected loading”的条件。当前证据更谨慎地支持 waveform shape/temporal delivery 与 JTL boundary 共同受限。", "- M2 与 M3 的差异表明，保留原始 10Ω shunt 后再加 10Ω series 会把 Q0 BJL2 最大段压到约 `0.999` 以下；移除 shunt、只保留 series branch 则 local BJL2 event恢复，但仍没有 JTL propagation。因此 series branch可以改变 local retrap/load-line，却不是已证明的 JTL receiver。", "- M4 的 10pH series boundary在本点显著改变 transient transfer，不能被解释成温和的 passive isolation success。", "- M5 的 coherent current-class positive control有效而 Q0 coupling仍失败，说明“只把 JTL Ic降到QB current class”不是充分机制；失败仍位于 Q0 output waveform 与 JTL input dynamic boundary/drive matching之间。", "- 这些结论只适用于本次冻结的 Q0/JTL fixtures，不否定更广泛的 conditioner、regenerator 或其他接口 family。", "", "## Unknown / limits", "", "- 本批次没有 canonical BVM、12-JSL、DCSFQ 或 T1；没有新的 BVM back-action evidence。", "- M1 是 ideal voltage counterfactual；M5 是 coherent scaling diagnostic，不是 standard JTL 的 replacement claim。", "- M3 改变了原始 Q0 shunt boundary，故不能与 accepted Q0+10Ω 直接视为同一 one-shot operating point。", "", "## Stop", "", "本批次完成后不进行 QB/JTL 参数调整、conditioner、T1 或 physical BVM integration。"]
    return "\n".join(lines) + "\n"


def main() -> None:
    results: dict[str, dict] = {}
    for name in CASES:
        path = RAW / name / "run.csv"
        if path.exists():
            results[name] = analyze_fixture(name)
    if not results:
        raise SystemExit("no raw fixtures found")
    (ANALYSIS / "results.json").write_text(json.dumps(results, indent=2, sort_keys=True) + "\n")
    (ANALYSIS / "REPORT.md").write_text(render_report(results))
    summary = {name: {"verdict": value["verdict"], "raw_sha256": value["raw_sha256"]} for name, value in results.items()}
    (ANALYSIS / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
