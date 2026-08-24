#!/usr/bin/env python3
"""Recompute the frozen JTL transport gate from existing CSV only.

This script deliberately keeps strict local evidence separate from settled-well
transport evidence.  It never imports the legacy fast-event metric.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path

import numpy as np


PHI0 = 2.067833848e-15
ROOT = Path(__file__).resolve().parents[4]
EXP = ROOT / "test/exploration/jtl-transport-gate-v1-methodology-20260824"
OUT = EXP / "analysis"
PARENT_HEAD = "edf9b6d6c9a26c999a9f95f8ca604993475c51d4"
EXPECTED_SIGN = 1.0
WELL_TOL = 0.02
AREA_RESIDUAL_TOL = 2.0e-4
PRE_P2P_TOL = 0.01
POST_P2P_TOL = 0.07
ONSET_MARKER_TURN = 0.5
ONSET_ORDER_SLACK_PS = 0.5

JTL_PHASE = ["P(B1|XJTL1)", "P(B2|XJTL1)",
             "P(B1|XJTL2)", "P(B2|XJTL2)"]
JTL_VOLTAGE = [x.replace("P(", "V(", 1) for x in JTL_PHASE]

SPECS = {
    "R11-positive-control": {
        "path": ROOT / "test/exploration/bvm-sfq-receiver-r11a-direct-jtl-compatibility-20260823/raw/positive-control/run-02.csv",
        "pre": (8.0, 10.0), "activity": (10.0, 35.0), "post": (35.0, 60.0),
        "topology": "standard JTL; accepted R11 positive control",
        "reference": True,
    },
    "M1-ideal-replay": {
        "path": ROOT / "test/exploration/parallel-qb-jtl-interface-mechanism-20260824/raw-v2/M1-ideal-replay/run.csv",
        "pre": (8.0, 10.0), "activity": (10.0, 35.0), "post": (35.0, 60.0),
        "topology": "standard JTL; Q0 ideal V(OUT) replay",
        "reference": False,
    },
    "M5-positive-control": {
        "path": ROOT / "test/exploration/parallel-qb-jtl-interface-mechanism-20260824/raw-v2/M5-positive-control/run.csv",
        "pre": (8.0, 10.0), "activity": (10.0, 35.0), "post": (35.0, 60.0),
        "topology": "scaled-JTL positive control; not standard JTL",
        "reference": False,
    },
    "pulse5-original": {
        "path": ROOT / "test/exploration/jtl-transport-gate-polarity-replay-20260824/raw/original/run.csv",
        "pre": (208.0, 210.0), "activity": (210.0, 235.0), "post": (235.0, 260.0),
        "topology": "standard JTL; accepted Q0 pulse-5 V(OUT,t), original polarity",
        "reference": False,
    },
    "pulse5-reverse": {
        "path": ROOT / "test/exploration/jtl-transport-gate-polarity-replay-20260824/raw/reverse/run.csv",
        "pre": (208.0, 210.0), "activity": (210.0, 235.0), "post": (235.0, 260.0),
        "topology": "standard JTL; same pulse-5 V(OUT,t), reversed polarity",
        "reference": False,
    },
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def load_csv(path: Path) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    lines = path.read_text().splitlines()
    header_index = next(i for i, line in enumerate(lines) if line.startswith("time"))
    headers = next(csv.reader([lines[header_index]]))
    rows = []
    for line in lines[header_index + 1:]:
        if not line.strip():
            continue
        fields = next(csv.reader([line]))
        if len(fields) == len(headers):
            rows.append([float(value) for value in fields])
    matrix = np.asarray(rows, dtype=float)
    if matrix.ndim != 2 or matrix.shape[0] < 2 or not np.all(np.isfinite(matrix)):
        raise ValueError(f"invalid data: {path}")
    time_ps = matrix[:, 0] * 1.0e12
    if np.any(np.diff(time_ps) <= 0.0):
        raise ValueError(f"non-monotonic time: {path}")
    return time_ps, {name: matrix[:, i] for i, name in enumerate(headers[1:], 1)}


def window_mask(time_ps: np.ndarray, window: tuple[float, float]) -> np.ndarray:
    return (time_ps >= window[0]) & (time_ps < window[1])


def voltage_area(time_ps: np.ndarray, voltage: np.ndarray) -> float:
    return float(np.trapezoid(voltage, time_ps * 1.0e-12) / PHI0)


def strict_segments(time_ps: np.ndarray, phase: np.ndarray, voltage: np.ndarray,
                    window: tuple[float, float]) -> list[dict]:
    indices = np.flatnonzero(window_mask(time_ps, window))
    if len(indices) < 2:
        return []
    phase_u = np.unwrap(phase)
    derivative = np.diff(phase_u[indices])
    segments = []
    for sign, direction in ((1.0, "forward"), (-1.0, "backward")):
        good = sign * derivative >= 0.0
        i = 0
        while i < len(good):
            while i < len(good) and not good[i]:
                i += 1
            if i >= len(good):
                break
            j = i
            while j + 1 < len(good) and good[j + 1]:
                j += 1
            start = int(indices[i])
            end = int(indices[j + 1])
            turns = float((phase_u[end] - phase_u[start]) / (2.0 * math.pi))
            area = voltage_area(time_ps[start:end + 1], voltage[start:end + 1])
            segments.append({
                "direction": direction,
                "start_ps": float(time_ps[start]),
                "end_ps": float(time_ps[end]),
                "duration_ps": float(time_ps[end] - time_ps[start]),
                "turns": turns,
                "area_turns": area,
                "residual_turns": float(area - turns),
            })
            i = j + 1
    return segments


def strict_event(segment: dict) -> bool:
    turns = abs(segment["turns"])
    residual = max(0.02, 0.05 * turns)
    return (turns >= 1.0 and segment["turns"] * segment["area_turns"] > 0.0
            and abs(segment["residual_turns"]) <= residual)


def empty_segment() -> dict:
    return {"direction": "none", "start_ps": None, "end_ps": None,
            "duration_ps": 0.0, "turns": 0.0, "area_turns": 0.0,
            "residual_turns": 0.0}


def summarize_segments(segments: list[dict]) -> dict:
    if not segments:
        return {"largest_absolute": empty_segment(), "largest_forward": empty_segment(),
                "largest_backward": empty_segment(), "event_segments": [], "event_count": 0}
    forward = [segment for segment in segments if segment["direction"] == "forward"]
    backward = [segment for segment in segments if segment["direction"] == "backward"]
    largest_forward = max(forward, key=lambda x: x["turns"]) if forward else empty_segment()
    largest_backward = min(backward, key=lambda x: x["turns"]) if backward else empty_segment()
    events = [segment for segment in segments if strict_event(segment)]
    return {
        "largest_absolute": max(segments, key=lambda x: abs(x["turns"])),
        "largest_forward": largest_forward,
        "largest_backward": largest_backward,
        "event_segments": events,
        "event_count": len(events),
    }


def stable_well(time_ps: np.ndarray, phase: np.ndarray, voltage: np.ndarray,
                window: tuple[float, float]) -> dict:
    selected = window_mask(time_ps, window)
    phase_u = np.unwrap(phase)
    values = phase_u[selected]
    return {
        "mean_phase_rad": float(np.mean(values)),
        "median_phase_rad": float(np.median(values)),
        "p2p_turns": float(np.ptp(values) / (2.0 * math.pi)),
        "voltage_rms_uV": float(np.sqrt(np.mean(voltage[selected] ** 2)) * 1.0e6),
    }


def first_marker(time_ps: np.ndarray, phase: np.ndarray,
                 pre: tuple[float, float], activity: tuple[float, float],
                 sign: float) -> float | None:
    phase_u = np.unwrap(phase)
    pre_mask = window_mask(time_ps, pre)
    active_mask = window_mask(time_ps, activity)
    pre_mean = float(np.mean(phase_u[pre_mask]))
    candidates = np.flatnonzero(active_mask &
                                (sign * (phase_u - pre_mean) >= ONSET_MARKER_TURN * 2.0 * math.pi))
    return float(time_ps[candidates[0]]) if len(candidates) else None


def analyze_trace(time_ps: np.ndarray, phase: np.ndarray, voltage: np.ndarray,
                  spec: dict) -> dict:
    phase_u = np.unwrap(phase)
    pre = stable_well(time_ps, phase, voltage, spec["pre"])
    post = stable_well(time_ps, phase, voltage, spec["post"])
    active = window_mask(time_ps, spec["activity"])
    indices = np.flatnonzero(active)
    segments = strict_segments(time_ps, phase, voltage, spec["activity"])
    summary = summarize_segments(segments)
    full_phase = float((phase_u[indices[-1]] - phase_u[indices[0]]) / (2.0 * math.pi))
    full_area = voltage_area(time_ps[active], voltage[active])
    mean_delta = float((post["mean_phase_rad"] - pre["mean_phase_rad"]) /
                       (2.0 * math.pi))
    median_delta = float((post["median_phase_rad"] - pre["median_phase_rad"]) /
                         (2.0 * math.pi))
    nearest_well = int(round(mean_delta))
    well_residual = abs(mean_delta - nearest_well)
    marker = first_marker(time_ps, phase, spec["pre"], spec["activity"], EXPECTED_SIGN)
    post_segments = strict_segments(time_ps, phase, voltage, spec["post"])
    transport_ok = {
        "pre_stable": pre["p2p_turns"] <= PRE_P2P_TOL,
        "post_stable": post["p2p_turns"] <= POST_P2P_TOL,
        "one_adjacent_well": nearest_well == 1 and well_residual <= WELL_TOL,
        "full_window_one_well": abs(full_phase - 1.0) <= WELL_TOL and abs(full_area - 1.0) <= WELL_TOL,
        "phase_area_consistent": abs(full_area - full_phase) <= AREA_RESIDUAL_TOL,
        "onset_marker_present": marker is not None,
        "no_post_extra_complete_segment": sum(strict_event(x) for x in post_segments) == 0,
    }
    transport_ok["jj_pass"] = all(transport_ok.values())
    return {
        "activity_range_turns": float(np.ptp(phase_u[active]) / (2.0 * math.pi)),
        "full_window_phase_turns": full_phase,
        "full_window_area_turns": full_area,
        "full_window_phase_area_residual": float(full_phase - full_area),
        "segments": segments,
        "strict": summary,
        "pre_well": pre,
        "post_well": post,
        "pre_post_mean_delta_turns": mean_delta,
        "pre_post_median_delta_turns": median_delta,
        "nearest_integer_well": nearest_well,
        "well_residual_turns": float(well_residual),
        "onset_marker_ps": marker,
        "post_segments": post_segments,
        "post_complete_event_count": int(sum(strict_event(x) for x in post_segments)),
        "transport_checks": transport_ok,
    }


def signal_metrics(time_ps: np.ndarray, values: np.ndarray, window: tuple[float, float]) -> dict:
    selected = values[window_mask(time_ps, window)]
    return {"min": float(np.min(selected)), "max": float(np.max(selected)),
            "p2p": float(np.ptp(selected)), "rms": float(np.sqrt(np.mean(selected ** 2)))}


def analyze_case(name: str, spec: dict) -> dict:
    time_ps, arrays = load_csv(spec["path"])
    traces = {
        phase: analyze_trace(time_ps, arrays[phase], arrays[voltage], spec)
        for phase, voltage in zip(JTL_PHASE, JTL_VOLTAGE)
    }
    onset = [traces[phase]["onset_marker_ps"] for phase in JTL_PHASE]
    order_ok = all(value is not None for value in onset)
    if order_ok:
        order_ok = all(onset[i + 1] + ONSET_ORDER_SLACK_PS >= onset[i]
                       for i in range(len(onset) - 1))
    chain_ok = all(traces[phase]["transport_checks"]["jj_pass"] for phase in JTL_PHASE)
    transport_pass = bool(chain_ok and order_ok)
    strict_vector = [traces[phase]["strict"]["event_count"] for phase in JTL_PHASE]
    if transport_pass:
        if name == "R11-positive-control":
            verdict = "JTL_TRANSPORT_REFERENCE_PASS"
        else:
            verdict = "JTL_TRANSPORT_PASS_COUNTERFACTUAL"
    elif name == "M5-positive-control" and all(traces[p]["nearest_integer_well"] == 2 for p in JTL_PHASE):
        verdict = "MULTI_WELL_TRANSPORT_NOT_ONE_TURN"
    elif name == "pulse5-reverse":
        verdict = "REVERSE_POLARITY_NOT_A_ONE_WELL_TRANSPORT_EVENT"
    else:
        verdict = "JTL_TRANSPORT_GATE_FAIL"
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
        "onset_order_ps": onset,
        "onset_order_ok": order_ok,
        "strict_event_vector": strict_vector,
        "transport_pass": transport_pass,
        "verdict": verdict,
    }


def f(value: float | int | None, digits: int = 6) -> str:
    if value is None:
        return "—"
    return f"{value:.{digits}g}"


def report(payload: dict) -> str:
    cases = payload["cases"]
    lines = [
        "# JTL_TRANSPORT_GATE_V1 — existing-evidence reconciliation",
        "",
        f"parent accepted HEAD: `{PARENT_HEAD}`  ",
        "本报告只重算既有 CSV；没有 JoSIM execution、没有 topology/parameter change。",
        "`P(...)` raw unit 是 rad；所有 turns 为同一窗口 `ΔP/(2π)`。未使用 `fast_events`。",
        "",
        "## 1. Gate definition",
        "",
        "Strict local event 与 settled-well transport evidence 分开。transport gate 要求每颗 JJ 的 pre/post bounded、+1 adjacent-well、activity phase/area 一致、无 +2 或额外 post event，并满足四级因果 onset 顺序。",
        "",
        "Provisional retrospective tolerances: one-well `±0.02 turn`; phase/area residual `≤2e-4 turn`; pre p2p `≤0.01`; post p2p `≤0.07`; onset marker `t50` at `+0.5 turn`; onset order slack `0.5 ps`。这些值来自本批 accepted references，但不是 global Authority freeze，详见 `../PREREGISTRATION.md`。",
        "",
        "## 2. Case-level disposition",
        "",
        "| fixture | strict local vector (B1/B2/B1/B2) | transport vector | onset order (ps) | verdict |",
        "|---|---|---|---|---|",
    ]
    for name, case in cases.items():
        vector = ["1" if case["jtl"][phase]["transport_checks"]["jj_pass"] else "0" for phase in JTL_PHASE]
        onset = ", ".join("—" if x is None else f(x) for x in case["onset_order_ps"])
        lines.append(f"| {name} | `{case['strict_event_vector']}` | `{vector}` | `{onset}` | **{case['verdict']}** |")

    lines += ["", "## 3. Per-JJ strict and settled-well evidence", "",
              "`largest segment` 是 strict local candidate；`pre→post`、full-window phase/area 是独立 transport evidence。",
              "", "| fixture | JJ | largest strict turn / area | full phase / area | pre median / p2p / Vrms | post median / p2p / Vrms | pre→post mean / median | full phase-area residual | post extra events |",
              "|---|---|---:|---:|---:|---:|---:|---:|---:|"]
    for name, case in cases.items():
        for phase in JTL_PHASE:
            tr = case["jtl"][phase]
            seg = tr["strict"]["largest_absolute"]
            lines.append(
                f"| {name} | `{phase}` | {f(seg['turns'])} / {f(seg['area_turns'])} | "
                f"{f(tr['full_window_phase_turns'])} / {f(tr['full_window_area_turns'])} | "
                f"{f(tr['pre_well']['median_phase_rad']/(2*math.pi))} / {f(tr['pre_well']['p2p_turns'])} / {f(tr['pre_well']['voltage_rms_uV'])} | "
                f"{f(tr['post_well']['median_phase_rad']/(2*math.pi))} / {f(tr['post_well']['p2p_turns'])} / {f(tr['post_well']['voltage_rms_uV'])} | "
                f"{f(tr['pre_post_mean_delta_turns'])} / {f(tr['pre_post_median_delta_turns'])} (n={tr['nearest_integer_well']}) | "
                f"{f(tr['full_window_phase_area_residual'], 4)} | {tr['post_complete_event_count']} |"
            )

    lines += ["", "## 4. Explicit transport checks", "",
              "| fixture | JJ | pre | post | one well | full one well | phase/area | t50 | no post event | JJ transport |",
              "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for name, case in cases.items():
        for phase in JTL_PHASE:
            checks = case["jtl"][phase]["transport_checks"]
            values = ["Y" if checks[key] else "N" for key in
                      ("pre_stable", "post_stable", "one_adjacent_well", "full_window_one_well",
                       "phase_area_consistent", "onset_marker_present", "no_post_extra_complete_segment")]
            values.append("Y" if checks["jj_pass"] else "N")
            lines.append(f"| {name} | `{phase}` | " + " | ".join(values[:2] + values[2:]) + " |")

    lines += ["", "## 5. Observed", "",
              "- R11 standard-JTL positive control：四颗 JJ 的 full-window phase/area 与 mean pre→post 都支持 +1 adjacent well；strict largest monotonic segment 只有第一颗超过 1 turn。",
              "- M1 ideal Q0 replay：同样通过四颗 JJ 的 settled-well transport 条件，但它是 ideal voltage replay；strict vector 仍为 `[1,0,0,0]`。",
              "- pulse-5 original：四颗 JJ 的 transport vector 与 R11 相同，onset 顺序为正向逐级延迟；strict vector 仍为 `[1,0,0,0]`。",
              "- pulse-5 reverse：方向相反且下游幅度快速衰减，不能满足预期 +1 one-well transport；它不是 logical0 control。",
              "- M5-PC：四颗 JJ 的 full-window/pre→post 都约为 +2 wells；旧的 `abs(turns)>=0.90` 规则因此不能表达 exactly-one。",
              "",
              "## 6. Derived", "",
              "- R11 与 pulse-5 original 在本批 provisional gate 的离散 transport signature（四颗 +1、bounded、phase/area residual、t50 order）一致；这支持“在 task-local transport-signature 层面落入同一类”，不表示波形或物理接口相同。",
              "- M1 与 pulse-5 original 也通过同一 ideal-replay transport gate，但仍不能据此证明 physical Q0→JTL coupling。",
              "- `full-window≈1 turn` 不会回写或升级 strict local-event vector。",
              "",
              "## 7. Inference", "",
              "- 原极性 Q0 pulse 对冻结 standard JTL 的理想 replay具备可重复的 +1-well、逐级 transport-compatible response；反极性则不具备该方向的 one-well chain response。",
              "- 若后续要解释 physical Q0→JTL failure，下一层问题仍是 impedance/loading isolation；本 checkpoint 本身不选择 transformer 或 matching topology。",
              "",
              "## 8. Unknown / boundary", "",
              "- 没有新的 physical QB→JTL coupling、canonical BVM→JTL、T1 或 timestep convergence run。",
              "- transport gate 是针对当前 frozen standard-JTL/replay fixture 的回顾性 provisional 方法学门，不是所有 underdamped JTL 的 universal acceptance spec。",
              "- reverse polarity 不提供 logical0 的 state-selective evidence。",
              "",
              "## 9. Final disposition", "",
              "`JTL_TRANSPORT_GATE_V1` 回顾性方法学分类完成：保留 strict local 与 settled-well transport 两条证据链；R11 positive、M1 ideal replay、pulse-5 original 落入 provisional one-well transport-signature class，M5-PC 降级为 two-well scaled-JTL control，reverse replay 不通过 one-well positive-polarity 条件。该结果不是 global Authority metric freeze；停止，不运行后续电路实验。",
              ""]
    return "\n".join(lines)


def main() -> None:
    cases = {name: analyze_case(name, spec) for name, spec in SPECS.items()}
    source_paths = {
        "metric_spec_v2": ROOT / "docs/research/METRIC_SPEC_V2.md",
        "standard_JTL": ROOT / "test/exploration/jtl-transport-gate-polarity-replay-20260824/inputs/source/JTL.cir",
        "jjmit": ROOT / "test/exploration/jtl-transport-gate-polarity-replay-20260824/inputs/source/jjmit.cir",
        "pulse5_source": ROOT / "test/exploration/jtl-transport-gate-polarity-replay-20260824/inputs/source/pulse5_vout.csv",
        "q0_source": ROOT / "test/exploration/jtl-transport-gate-polarity-replay-20260824/inputs/source/q0-scaled-iin-68p4u.csv",
    }
    payload = {
        "parent_head": PARENT_HEAD,
        "gate": {
            "expected_sign": EXPECTED_SIGN,
            "well_tolerance_turns": WELL_TOL,
            "phase_area_residual_tolerance_turns": AREA_RESIDUAL_TOL,
            "pre_p2p_tolerance_turns": PRE_P2P_TOL,
            "post_p2p_tolerance_turns": POST_P2P_TOL,
            "onset_marker_turns": ONSET_MARKER_TURN,
            "onset_order_slack_ps": ONSET_ORDER_SLACK_PS,
        },
        "cases": cases,
        "source_hashes": {name: sha256(path) for name, path in source_paths.items()},
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "results.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    (OUT / "REPORT.md").write_text(report(payload), encoding="utf-8")
    summary = {
        "parent_head": PARENT_HEAD,
        "strict_vectors": {name: case["strict_event_vector"] for name, case in cases.items()},
        "transport_vectors": {name: [int(case["jtl"][phase]["transport_checks"]["jj_pass"]) for phase in JTL_PHASE] for name, case in cases.items()},
        "case_verdicts": {name: case["verdict"] for name, case in cases.items()},
        "raw_hashes": {name: case["raw_sha256"] for name, case in cases.items()},
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    artifact_hashes = {}
    for path in sorted(EXP.rglob("*")):
        if path.is_file() and path.name not in {"manifest.json", "SHA256SUMS.txt"} and "__pycache__" not in path.parts:
            artifact_hashes[path.relative_to(EXP).as_posix()] = sha256(path)
    manifest = {
        "parent_head": PARENT_HEAD,
        "joSIM_executed": False,
        "metric_spec_v2_sha256": payload["source_hashes"]["metric_spec_v2"],
        "source_hashes": payload["source_hashes"],
        "raw_hashes": summary["raw_hashes"],
        "artifact_hashes_excluding_manifest_and_sums": artifact_hashes,
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (OUT / "SHA256SUMS.txt").write_text(
        "".join(f"{digest}  {relative}\n" for relative, digest in sorted(artifact_hashes.items())),
        encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
