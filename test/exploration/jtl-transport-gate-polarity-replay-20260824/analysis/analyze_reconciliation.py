#!/usr/bin/env python3
"""Reconcile strict local-event evidence with full-window well evidence.

No legacy fast-event counter is imported.  Every phase/area pair is computed
from the same JJ, same run, same direction and same CSV time window.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path

import numpy as np


PHI0 = 2.067833848e-15
HERE = Path(__file__).resolve().parent
EXP = HERE.parent
ROOT = EXP.parents[2]
OUT = EXP / "analysis"

JTL_PHASE = [
    "P(B1|XJTL1)",
    "P(B2|XJTL1)",
    "P(B1|XJTL2)",
    "P(B2|XJTL2)",
]
JTL_VOLTAGE = [x.replace("P(", "V(", 1) for x in JTL_PHASE]

SPECS = {
    "R11-positive-control": {
        "path": ROOT / "test/exploration/bvm-sfq-receiver-r11a-direct-jtl-compatibility-20260823/raw/positive-control/run-02.csv",
        "pre": (8.0, 10.0), "activity": (10.0, 35.0), "post": (35.0, 60.0),
        "topology": "standard JTL; accepted R11 positive control",
    },
    "M1-ideal-replay": {
        "path": ROOT / "test/exploration/parallel-qb-jtl-interface-mechanism-20260824/raw-v2/M1-ideal-replay/run.csv",
        "pre": (8.0, 10.0), "activity": (10.0, 35.0), "post": (35.0, 60.0),
        "topology": "standard JTL; Q0 ideal V(OUT) replay",
    },
    "M5-positive-control": {
        "path": ROOT / "test/exploration/parallel-qb-jtl-interface-mechanism-20260824/raw-v2/M5-positive-control/run.csv",
        "pre": (8.0, 10.0), "activity": (10.0, 35.0), "post": (35.0, 60.0),
        "topology": "scaled-JTL control from accepted M5-PC",
    },
    "pulse5-original": {
        "path": EXP / "raw/original/run.csv",
        "pre": (208.0, 210.0), "activity": (210.0, 235.0), "post": (235.0, 260.0),
        "topology": "standard JTL; exact accepted Q0 pulse-5 V(OUT,t), original polarity",
    },
    "pulse5-reverse": {
        "path": EXP / "raw/reverse/run.csv",
        "pre": (208.0, 210.0), "activity": (210.0, 235.0), "post": (235.0, 260.0),
        "topology": "standard JTL; exact accepted Q0 pulse-5 V(OUT,t), reversed polarity",
    },
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def load_csv(path: Path) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    lines = path.read_text().splitlines()
    header_index = next((i for i, line in enumerate(lines) if line.startswith("time")), None)
    if header_index is None:
        raise ValueError(f"no CSV header in {path}")
    headers = next(csv.reader([lines[header_index]]))
    values: list[list[float]] = []
    for line in lines[header_index + 1:]:
        if not line.strip():
            continue
        fields = next(csv.reader([line]))
        if len(fields) != len(headers):
            continue
        values.append([float(x) for x in fields])
    matrix = np.asarray(values, dtype=float)
    if matrix.ndim != 2 or matrix.shape[0] < 2:
        raise ValueError(f"insufficient rows in {path}")
    time_ps = matrix[:, 0] * 1.0e12
    if np.any(~np.isfinite(matrix)) or np.any(np.diff(time_ps) <= 0.0):
        raise ValueError(f"invalid time/data in {path}")
    return time_ps, {name: matrix[:, i] for i, name in enumerate(headers[1:], 1)}


def mask(time_ps: np.ndarray, window: tuple[float, float]) -> np.ndarray:
    return (time_ps >= window[0]) & (time_ps < window[1])


def trapz_area(time_ps: np.ndarray, voltage: np.ndarray) -> float:
    return float(np.trapezoid(voltage, time_ps * 1.0e-12) / PHI0)


def monotonic_segments(time_ps: np.ndarray, phase: np.ndarray, voltage: np.ndarray,
                       window: tuple[float, float]) -> list[dict]:
    idx = np.flatnonzero(mask(time_ps, window))
    if len(idx) < 2:
        return []
    phase_u = np.unwrap(phase)
    dphi = np.diff(phase_u[idx])
    result: list[dict] = []
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
            turns = float((phase_u[e] - phase_u[s]) / (2.0 * math.pi))
            area = trapz_area(time_ps[s:e + 1], voltage[s:e + 1])
            result.append({
                "direction": direction,
                "start_ps": float(time_ps[s]),
                "end_ps": float(time_ps[e]),
                "duration_ps": float(time_ps[e] - time_ps[s]),
                "phase_delta_rad": float(phase_u[e] - phase_u[s]),
                "turns": turns,
                "area_turns": area,
                "residual_turns": float(area - turns),
            })
            i = j + 1
    return result


def empty_segment() -> dict:
    return {"direction": "none", "start_ps": None, "end_ps": None,
            "duration_ps": 0.0, "phase_delta_rad": 0.0, "turns": 0.0,
            "area_turns": 0.0, "residual_turns": 0.0}


def event_ok(segment: dict) -> bool:
    turns = abs(segment["turns"])
    residual_limit = max(0.02, 0.05 * turns)
    return (turns >= 1.0 and segment["turns"] * segment["area_turns"] > 0.0
            and abs(segment["residual_turns"]) <= residual_limit)


def segment_summary(segments: list[dict]) -> dict:
    if not segments:
        return {"largest_absolute": empty_segment(), "largest_forward": empty_segment(),
                "largest_backward": empty_segment(), "event_segments": [], "count": 0}
    forward = [x for x in segments if x["direction"] == "forward"]
    backward = [x for x in segments if x["direction"] == "backward"]
    largest = max(segments, key=lambda x: abs(x["turns"]))
    largest_forward = max(forward, key=lambda x: x["turns"]) if forward else empty_segment()
    largest_backward = min(backward, key=lambda x: x["turns"]) if backward else empty_segment()
    events = [x for x in segments if event_ok(x)]
    return {"largest_absolute": largest, "largest_forward": largest_forward,
            "largest_backward": largest_backward, "event_segments": events,
            "count": len(events)}


def well_metrics(time_ps: np.ndarray, phase: np.ndarray, voltage: np.ndarray,
                 window: tuple[float, float]) -> dict:
    active = mask(time_ps, window)
    phase_u = np.unwrap(phase)
    p = phase_u[active]
    v = voltage[active]
    return {
        "median_phase_rad": float(np.median(p)),
        "phase_p2p_turns": float((np.max(p) - np.min(p)) / (2.0 * math.pi)),
        "voltage_rms_V": float(np.sqrt(np.mean(v * v))),
    }


def trace(time_ps: np.ndarray, phase: np.ndarray, voltage: np.ndarray,
          pre: tuple[float, float], activity: tuple[float, float],
          post: tuple[float, float]) -> dict:
    phase_u = np.unwrap(phase)
    active = mask(time_ps, activity)
    idx = np.flatnonzero(active)
    segments = monotonic_segments(time_ps, phase, voltage, activity)
    summary = segment_summary(segments)
    pre_well = well_metrics(time_ps, phase, voltage, pre)
    post_well = well_metrics(time_ps, phase, voltage, post)
    post_segments = monotonic_segments(time_ps, phase, voltage, post)
    return {
        "activity_range_turns": float((np.max(phase_u[active]) - np.min(phase_u[active])) / (2.0 * math.pi)),
        "full_window_phase_turns": float((phase_u[idx[-1]] - phase_u[idx[0]]) / (2.0 * math.pi)),
        "full_window_area_turns": trapz_area(time_ps[active], voltage[active]),
        "segments": segments,
        "strict": summary,
        "pre_well": pre_well,
        "post_well": post_well,
        "well_delta_turns": float((post_well["median_phase_rad"] - pre_well["median_phase_rad"]) / (2.0 * math.pi)),
        "post_segments": post_segments,
        "post_complete_event_count": int(sum(event_ok(x) for x in post_segments)),
    }


def signal_metrics(time_ps: np.ndarray, values: np.ndarray, window: tuple[float, float]) -> dict:
    x = values[mask(time_ps, window)]
    return {"min": float(np.min(x)), "max": float(np.max(x)),
            "p2p": float(np.max(x) - np.min(x)),
            "rms": float(np.sqrt(np.mean(x * x)))}


def analyze_case(name: str, spec: dict) -> dict:
    time_ps, arrays = load_csv(spec["path"])
    traces = {}
    for phase_col, voltage_col in zip(JTL_PHASE, JTL_VOLTAGE):
        traces[phase_col] = trace(time_ps, arrays[phase_col], arrays[voltage_col],
                                  spec["pre"], spec["activity"], spec["post"])
    signals = {}
    for col in ("V(JTL_IN)", "V(JTL_MID)", "V(JTL_OUT)", "I(V_REPLAY)",
                "I(L1|XJTL1)", "I(R_TERM)"):
        if col in arrays:
            signals[col] = signal_metrics(time_ps, arrays[col], spec["activity"])
    strict_vector = [traces[p]["strict"]["count"] for p in JTL_PHASE]
    full_vector = [
        abs(traces[p]["full_window_phase_turns"]) >= 0.90
        and abs(traces[p]["full_window_area_turns"]) >= 0.90
        and abs(traces[p]["full_window_area_turns"] - traces[p]["full_window_phase_turns"])
        <= max(0.02, 0.05 * abs(traces[p]["full_window_phase_turns"]))
        for p in JTL_PHASE
    ]
    if all(x == 1 for x in strict_vector):
        local_verdict = "STRICT_FULL_CHAIN_LOCAL_EVENTS"
    elif strict_vector[0] == 1 and all(x == 0 for x in strict_vector[1:]):
        local_verdict = "STRICT_FIRST_STAGE_ONLY"
    elif any(x > 1 for x in strict_vector):
        local_verdict = "STRICT_MULTIFIRE"
    elif any(x == 1 for x in strict_vector):
        local_verdict = "STRICT_PARTIAL_CHAIN"
    else:
        local_verdict = "NO_STRICT_LOCAL_EVENT"
    return {
        "name": name,
        "raw": str(spec["path"].relative_to(ROOT)),
        "raw_sha256": sha256(spec["path"]),
        "topology": spec["topology"],
        "rows": int(len(time_ps)),
        "time_start_ps": float(time_ps[0]),
        "time_end_ps": float(time_ps[-1]),
        "windows_ps": {"pre": spec["pre"], "activity": spec["activity"], "post": spec["post"]},
        "jtl": traces,
        "signals": signals,
        "strict_event_vector": strict_vector,
        "full_window_approx_one_turn_vector": full_vector,
        "local_verdict": local_verdict,
    }


def fmt(value: float | None, digits: int = 6) -> str:
    if value is None:
        return "—"
    return f"{value:.{digits}g}"


def render_report(results: dict[str, dict], source_hashes: dict[str, str]) -> str:
    lines = [
        "# JTL transport-gate reconciliation + pulse-5 polarity replay",
        "",
        "parent HEAD: `090b8268132b9d5d4ae2e81a0131cafc458c24c1`",
        "JoSIM: `v2.7.2837d13`; raw phase is radians; turns are derived by `ΔP/(2π)`.",
        "",
        "本报告将 strict monotonic local-event evidence 与 full-window/pre-post settled-well evidence 分开。",
        "full-window 接近一圈不能替代一个连续单调 segment 的 local event。未使用 legacy `fast_events`。",
        "",
        "## 1. Artifact / fixture boundary",
        "",
        "新 replay 是理想电压源 counterfactual fixture：只用于检验 accepted Q0 pulse 5 的极性/波形对冻结标准 JTL 的 transport response，不是物理 Q0→JTL 接口。",
        "原极性和反极性各自独立 deck；后者只把同一 pulse-5 V(OUT,t) 逐点乘以 -1。",
        "",
        "| fixture | topology | raw | strict vector | full-window approx-one-turn vector | local verdict |",
        "|---|---|---|---|---|---|",
    ]
    for result in results.values():
        lines.append(f"| {result['name']} | {result['topology']} | `{result['raw']}` | "
                     f"`{result['strict_event_vector']}` | `{result['full_window_approx_one_turn_vector']}` | "
                     f"**{result['local_verdict']}** |")

    lines += ["", "## 2. Strict monotonic local-event evidence", "",
              "事件计数只来自同一 JJ 的连续单调 segment：`|Δphase| >= 1 turn`、同段直接电压面积同号且残差在注册限制内。",
              "", "| fixture | JJ | count | largest forward (turn/area) | largest backward (turn/area) | onset of largest segment (ps) |",
              "|---|---|---:|---:|---:|---|"]
    for result in results.values():
        for phase_col in JTL_PHASE:
            strict = result["jtl"][phase_col]["strict"]
            fwd = strict["largest_forward"]
            back = strict["largest_backward"]
            largest = strict["largest_absolute"]
            fwd_text = f"{fmt(fwd['turns'])}/{fmt(fwd['area_turns'])}" if fwd["direction"] != "none" else "—"
            back_text = f"{fmt(back['turns'])}/{fmt(back['area_turns'])}" if back["direction"] != "none" else "—"
            onset = "—" if largest["start_ps"] is None else f"{fmt(largest['start_ps'])}→{fmt(largest['end_ps'])}"
            lines.append(f"| {result['name']} | `{phase_col}` | {strict['count']} | {fwd_text} | {back_text} | {onset} |")

    lines += ["", "### Strict evidence details for every JTL JJ", "",
              "| fixture | JJ | largest absolute turns | same-segment area Φ0 | residual turns | direction | start→end ps |",
              "|---|---|---:|---:|---:|---|---|"]
    for result in results.values():
        for phase_col in JTL_PHASE:
            largest = result["jtl"][phase_col]["strict"]["largest_absolute"]
            lines.append(f"| {result['name']} | `{phase_col}` | {fmt(largest['turns'])} | "
                         f"{fmt(largest['area_turns'])} | {fmt(largest['residual_turns'])} | "
                         f"{largest['direction']} | {fmt(largest['start_ps'])}→{fmt(largest['end_ps'])} |")

    lines += ["", "## 3. Full-window and pre/post settled-well evidence", "",
              "这些量描述注册 activity/full window 的端点净变化，以及 activity 前后的稳定井；它们不单独构成 strict local event。",
              "", "| fixture | JJ | full phase turns | full V-area Φ0 | residual | pre p2p | post p2p | pre→post median turns | post V RMS (µV) | post complete segments |",
              "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for result in results.values():
        for phase_col in JTL_PHASE:
            tr = result["jtl"][phase_col]
            lines.append(f"| {result['name']} | `{phase_col}` | {fmt(tr['full_window_phase_turns'])} | "
                         f"{fmt(tr['full_window_area_turns'])} | {fmt(tr['full_window_area_turns'] - tr['full_window_phase_turns'])} | "
                         f"{fmt(tr['pre_well']['phase_p2p_turns'])} | {fmt(tr['post_well']['phase_p2p_turns'])} | "
                         f"{fmt(tr['well_delta_turns'])} | {fmt(tr['post_well']['voltage_rms_V'] * 1e6)} | "
                         f"{tr['post_complete_event_count']} |")

    lines += ["", "## 4. Timing / transport observables", "",
              "`onset` 使用各 JJ 最大绝对单调段的起点；它是 activity timing，不自动等于 event onset。",
              "", "| fixture | JTL JJ | largest-segment onset (ps) | duration (ps) | activity range (turn) |",
              "|---|---|---|---:|---:|"]
    for result in results.values():
        for phase_col in JTL_PHASE:
            tr = result["jtl"][phase_col]
            largest = tr["strict"]["largest_absolute"]
            lines.append(f"| {result['name']} | `{phase_col}` | {fmt(largest['start_ps'])}→{fmt(largest['end_ps'])} | "
                         f"{fmt(largest['duration_ps'])} | {fmt(tr['activity_range_turns'])} |")
    lines += ["", "| fixture | V(JTL_IN) p2p (mV) | V(JTL_MID) p2p (mV) | V(JTL_OUT) p2p (mV) | I(L1/XJTL1) p2p (µA) | I(R_TERM) p2p (µA) |",
              "|---|---:|---:|---:|---:|---:|"]
    for result in results.values():
        sig = result["signals"]
        def p2p(col: str, scale: float) -> str:
            return fmt(sig[col]["p2p"] * scale) if col in sig else "—"
        lines.append(f"| {result['name']} | {p2p('V(JTL_IN)',1e3)} | {p2p('V(JTL_MID)',1e3)} | "
                     f"{p2p('V(JTL_OUT)',1e3)} | {p2p('I(L1|XJTL1)',1e6)} | {p2p('I(R_TERM)',1e6)} |")

    lines += ["", "## 5. Reconciliation", "",
              "### Observed", "",
              "- R11 standard positive control has approximately one-turn full-window phase/area response in all four JJ, but its strict largest monotonic segments are not all one turn; therefore full-window calibration and strict local-event evidence are different rows of evidence.",
              "- M1 Q0 V(OUT) ideal replay and the new original pulse-5 replay are the same diagnostic family: first-stage response may have a strict event while downstream segments can remain below one turn.",
              "- M5-PC is a scaled-JTL positive-control fixture; it is reported as its own topology and is not silently merged with standard-JTL results.",
              "- The reverse replay is a polarity diagnostic only; any resulting JTL activity is not read0 evidence and cannot establish selectivity.",
              "",
              "### Derived", "",
              "- For every table above, strict count uses the same-JJ direct voltage area over the exact reported monotonic segment. Full-window residuals use the activity-window endpoints and its direct same-JJ voltage integral.",
              "- Pre/post well deltas and p2p values quantify retrap/boundedness evidence separately; a small post p2p does not repair a sub-turn strict segment.",
              "",
              "### Inference", "",
              "- This batch can reconcile polarity and transport behavior of the frozen diagnostic JTL fixture, but cannot identify a physical QB→JTL interface mechanism because the new source is ideal voltage replay.",
              "",
              "### Unknown", "",
              "- No new read0/BVM case is run in this batch, no additional timestep convergence group is run, and no T1 is attached. Reverse polarity is not a logical-state control.",
              "",
              "## 6. Stop / disposition", "",
              "本 checkpoint 在两个 polarity replay 与统一 evidence table 完成后停止；不进行任何 R/L/Ic/bias sweep，不修改 QB/JTL 参数，不连接 T1。",
              ""]
    return "\n".join(lines)


def main() -> None:
    results = {name: analyze_case(name, spec) for name, spec in SPECS.items()}
    source_hashes = {
        "standard_JTL.cir": sha256(EXP / "inputs/source/JTL.cir"),
        "jjmit.cir": sha256(EXP / "inputs/source/jjmit.cir"),
        "q0_source_raw": sha256(EXP / "inputs/source/q0-scaled-iin-68p4u.csv"),
        "pulse5_vout.csv": sha256(EXP / "inputs/source/pulse5_vout.csv"),
        "original_deck": sha256(EXP / "inputs/original/main.cir"),
        "reverse_deck": sha256(EXP / "inputs/reverse/main.cir"),
        "original_raw": sha256(EXP / "raw/original/run.csv"),
        "reverse_raw": sha256(EXP / "raw/reverse/run.csv"),
    }
    payload = {"parent_head": "090b8268132b9d5d4ae2e81a0131cafc458c24c1",
               "cases": results, "source_hashes": source_hashes}
    (OUT / "results.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    (OUT / "summary.json").write_text(json.dumps({
        "parent_head": payload["parent_head"],
        "strict_vectors": {name: result["strict_event_vector"] for name, result in results.items()},
        "full_window_approx_one_turn_vectors": {name: result["full_window_approx_one_turn_vector"] for name, result in results.items()},
        "local_verdicts": {name: result["local_verdict"] for name, result in results.items()},
        "raw_hashes": {name: result["raw_sha256"] for name, result in results.items()},
    }, indent=2), encoding="utf-8")
    (OUT / "REPORT.md").write_text(render_report(results, source_hashes), encoding="utf-8")
    artifact_hashes: dict[str, str] = {}
    for path in sorted(EXP.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(EXP).as_posix()
        if relative in {"analysis/manifest.json", "analysis/SHA256SUMS.txt"} or "__pycache__" in path.parts:
            continue
        artifact_hashes[relative] = sha256(path)
    manifest = {
        "parent_head": payload["parent_head"],
        "josim": {
            "version": "v2.7.2837d13",
            "binary": "build/josim-cli",
            "binary_sha256": "48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2",
        },
        "metric_spec_v2_sha256": "f88a36f4d310b2572efdc7408d734640f25dd5aea2246b74fbb8b7bb7f0be470",
        "source_hashes": source_hashes,
        "artifact_hashes_excluding_manifest_and_sums": artifact_hashes,
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    sums = "".join(f"{digest}  {relative}\n" for relative, digest in sorted(artifact_hashes.items()))
    (OUT / "SHA256SUMS.txt").write_text(sums, encoding="utf-8")
    print(json.dumps({name: result["local_verdict"] for name, result in results.items()}, indent=2))


if __name__ == "__main__":
    main()
