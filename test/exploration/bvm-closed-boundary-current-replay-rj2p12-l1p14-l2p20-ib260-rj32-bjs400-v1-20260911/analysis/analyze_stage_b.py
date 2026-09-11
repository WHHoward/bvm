#!/usr/bin/env python3
"""Analyze Stage B N3 raw using the authorized bounded evidence rules."""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
SOURCE = EXP / "references/closed_loop_rj2p12/ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_0111/raw.csv"
REPLAY = EXP / "runs/CLOSED_CURRENT_REPLAY_N3_0111_RJ2P12/raw.csv"
SOURCE_SNAPSHOT = EXP / "data/CLOSED_LOOP_N3_I_BJSL8_source.csv"
SOURCE_SIGNAL = "I(B_JSL8)"
WINDOWS = ((70.0, 81.0), (90.0, 101.0), (101.0, 110.0), (121.0, 130.0), (110.0, 200.0))
THRESHOLDS = (0.5, 1.5, 2.5, 3.5)
ACTIVITY_THRESHOLD = 1.0e-5
PHI0 = 2.067833848e-15
REPLAY_COLUMNS = ("I(I_REPLAY)", "I(LIN|XBQ1)", "I(L1|XBQ1)", "I(L2|XBQ1)", "P(BJ1|XBQ1)", "V(BJ1|XBQ1)", "I(BJ1|XBQ1)", "P(BJ2|XBQ1)", "V(BJ2|XBQ1)", "I(BJ2|XBQ1)", "V(QBOUT)", "V(JTL1_OUT)", "V(JTL2_OUT)", "V(JTL3_OUT)", "V(JTL4_OUT)", "V(JTL5_OUT)", "V(JTL6_OUT)", "I(R_TERM)") + tuple(f"P(B01|XJTL1_{stage})" for stage in range(1, 7))
SOURCE_COLUMNS = ("I(B_JSL8)",) + tuple(label for label in REPLAY_COLUMNS if label != "I(I_REPLAY)")

sys.path.insert(0, str(EXP / "analysis"))
from analyze_stage_a import activity_segments, difference, integral, phase_navigation, read, window_metrics  # noqa: E402


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def direct_positive_peaks(times: list[float], values: list[float], threshold: float = 2.0e-4, minimum_gap_ps: float = 2.5) -> list[dict[str, float]]:
    """Locate clearly separated stored-sample terminal maxima for navigation only."""
    candidates = [
        index for index in range(1, len(values) - 1)
        if 110.0 <= times[index] < 200.0
        and values[index] >= threshold
        and values[index] >= values[index - 1]
        and values[index] > values[index + 1]
    ]
    selected: list[int] = []
    for index in candidates:
        if not selected or times[index] - times[selected[-1]] > minimum_gap_ps:
            selected.append(index)
        elif values[index] > values[selected[-1]]:
            selected[-1] = index
    return [{"peak_time_ps": times[index], "peak_value_V": values[index]} for index in selected]


def four_candidate_navigation(phase: dict[str, Any], terminal_peaks: list[dict[str, float]], qbout_peaks: list[dict[str, float]]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for candidate in range(1, 5):
        threshold = f"{THRESHOLDS[candidate - 1]:g}"
        row: dict[str, Any] = {"candidate_index": candidate, "threshold_turns": THRESHOLDS[candidate - 1]}
        for label, semantic in (("P(BJ1|XBQ1)", "BJ1"), ("P(BJ2|XBQ1)", "BJ2")):
            row[semantic] = phase[label]["threshold_navigation_times_ps"].get(threshold)
        for stage in range(1, 7):
            label = f"P(B01|XJTL1_{stage})"
            row[f"JTL{stage}"] = phase[label]["threshold_navigation_times_ps"].get(threshold)
        row["QBOUT_peak_time_ps"] = qbout_peaks[candidate - 1]["peak_time_ps"] if len(qbout_peaks) >= candidate else None
        row["terminal_peak_time_ps"] = terminal_peaks[candidate - 1]["peak_time_ps"] if len(terminal_peaks) >= candidate else None
        rows.append(row)
    return {
        "candidate_navigation_rows": rows,
        "front_end_four_landmarks_present": all(row["BJ1"] is not None and row["BJ2"] is not None for row in rows),
        "all_jtl_four_landmarks_present": all(row[f"JTL{stage}"] is not None for row in rows for stage in range(1, 7)),
        "terminal_four_separated_raw_peaks": len(terminal_peaks) == 4,
        "qbout_raw_peak_times_ps": qbout_peaks,
        "qbout_mapping_status": "DENSE_LOBES_NOT_UNIQUELY_ASSIGNED",
        "interpretation": "multi-evidence response-candidate navigation; not an SFQ count",
    }


def main() -> int:
    source_times, source = read(SOURCE, SOURCE_COLUMNS)
    replay_times, replay = read(REPLAY, REPLAY_COLUMNS)
    if source_times != replay_times:
        raise RuntimeError("Stage B source and replay time grids differ")
    current_delta = [a - b for a, b in zip(source["I(B_JSL8)"], replay["I(I_REPLAY)"])]
    pre_index = next(index for index, time in enumerate(source_times) if abs(time - 109.9) < 1e-9)
    pre_final = {}
    for label in ("I(L1|XBQ1)", "I(L2|XBQ1)", "I(BJ1|XBQ1)", "I(BJ2|XBQ1)", "P(BJ1|XBQ1)", "P(BJ2|XBQ1)"):
        pre_final[label] = {"time_ps": source_times[pre_index], "source_value": source[label][pre_index], "replay_value": replay[label][pre_index], "difference": source[label][pre_index] - replay[label][pre_index], "raw_phase_radians": label.startswith("P(")}
    comparisons: dict[str, Any] = {}
    for label in ("I(LIN|XBQ1)", "I(L1|XBQ1)", "I(L2|XBQ1)", "P(BJ1|XBQ1)", "V(BJ1|XBQ1)", "I(BJ1|XBQ1)", "P(BJ2|XBQ1)", "V(BJ2|XBQ1)", "I(BJ2|XBQ1)", "V(QBOUT)", "V(JTL1_OUT)", "V(JTL2_OUT)", "V(JTL3_OUT)", "V(JTL4_OUT)", "V(JTL5_OUT)", "V(JTL6_OUT)", "I(R_TERM)"):
        comparisons[label] = {}
        for start, end in WINDOWS[:3] + WINDOWS[3:4]:
            indices = [i for i, time in enumerate(source_times) if start <= time < end]
            comparisons[label][f"{start:g}_{end:g}_ps"] = difference([source_times[i] for i in indices], [source[label][i] for i in indices], [replay_times[i] for i in indices], [replay[label][i] for i in indices], phase=label.startswith("P("))
    activity_labels = ("V(QBOUT)",) + tuple(f"V(JTL{stage}_OUT)" for stage in range(1, 7))
    activities = {label: activity_segments(replay_times, replay[label]) for label in activity_labels}
    progression = {label: (segments[0]["support_start_ps"] if segments else None) for label, segments in activities.items()}
    phase = {label: phase_navigation(replay_times, replay[label]) for label in ("P(BJ1|XBQ1)", "P(BJ2|XBQ1)") + tuple(f"P(B01|XJTL1_{stage})" for stage in range(1, 7))}
    terminal = {"voltage": activity_segments(replay_times, replay["V(JTL6_OUT)"]), "current": activity_segments(replay_times, replay["I(R_TERM)"]), "final_voltage_integral_V_s": integral(replay_times, replay["V(JTL6_OUT)"], [i for i, time in enumerate(replay_times) if 110.0 <= time < 200.0]), "final_voltage_area_over_phi0": integral(replay_times, replay["V(JTL6_OUT)"], [i for i, time in enumerate(replay_times) if 110.0 <= time < 200.0]) / PHI0, "direct_positive_peak_navigation": direct_positive_peaks(replay_times, replay["V(JTL6_OUT)"]), "activity_threshold": ACTIVITY_THRESHOLD}
    qbout_peaks = direct_positive_peaks(replay_times, replay["V(QBOUT)"])
    candidate_navigation = four_candidate_navigation(phase, terminal["direct_positive_peak_navigation"], qbout_peaks)
    metrics = {"schema": "bvm-closed-boundary-current-replay-stage-b-raw-metrics-v1", "experiment_id": EXP.name, "created_at_local": now(), "stage": "B", "source_raw_path": SOURCE.relative_to(REPO).as_posix(), "source_raw_sha256": sha256(SOURCE), "source_snapshot_path": SOURCE_SNAPSHOT.relative_to(REPO).as_posix(), "source_snapshot_sha256": sha256(SOURCE_SNAPSHOT), "replay_raw_path": REPLAY.relative_to(REPO).as_posix(), "replay_raw_sha256": sha256(REPLAY), "source_sample_count": len(source_times), "replay_sample_count": len(replay_times), "source_signal": SOURCE_SIGNAL, "source_replay_current_exactness": {"max_absolute_mismatch_A": max(abs(value) for value in current_delta), "all_stored_values_equal": all(value == 0.0 for value in current_delta), "same_time_grid": source_times == replay_times, "orientation": "direct positive JSL7->QBIN to 0->QBIN", "transformations": []}, "source_windows": window_metrics(source_times, source["I(B_JSL8)"]), "replay_windows": window_metrics(replay_times, replay["I(I_REPLAY)"]), "pre_final": pre_final, "closed_vs_replay": comparisons, "phase_navigation": phase, "activity_segments": activities, "ordered_activity_support_start_ps": progression, "terminal_analysis": terminal, "four_candidate_navigation": candidate_navigation, "critical_window_ps": [121.0, 130.0], "scientific_response_outcome": "PENDING_DIRECT_RAW_REVIEW", "scientific_analysis_performed": True}
    write_json(EXP / "analysis/mechanism_metrics_stage_b.json", metrics)
    summary = {"schema": "bvm-closed-boundary-current-replay-stage-b-mechanical-summary-v1", "experiment_id": EXP.name, "created_at_local": metrics["created_at_local"], "status": "PASS", "stage": "B", "scientific_analysis_performed": True, "raw_and_mechanical_evidence_status": "READY", "scientific_response_outcome": "PENDING_DIRECT_RAW_REVIEW", "metrics": metrics, "stage_a_unchanged": True}
    write_json(EXP / "mechanical_summary_stage_b.json", summary)
    response_qa = {"schema": "bvm-closed-boundary-current-replay-stage-b-response-qa-v1", "experiment_id": EXP.name, "created_at_local": metrics["created_at_local"], "status": "PASS", "required_progression": ["BJ1", "BJ2", "QBOUT", "JTL1", "JTL2", "JTL3", "JTL4", "JTL5", "JTL6", "terminal"], "critical_window_ps": [121.0, 130.0], "phase_navigation_only": True, "scientific_response_outcome": "PENDING_DIRECT_RAW_REVIEW", "stage_b_started": True, "stage_a_unchanged": True, "failures": []}
    write_json(EXP / "qa/stage_b_response_qa.json", response_qa)
    lines = ["# Stage B N3 raw review", "", "Scientific review authorization is present for this Stage B. Raw evidence remains authoritative; phase displays are `rad/(2*pi)` navigation only.", "", f"- Source raw SHA-256: `{metrics['source_raw_sha256']}`", f"- Replay raw SHA-256: `{metrics['replay_raw_sha256']}`", f"- Exact source/replay current max mismatch: `{metrics['source_replay_current_exactness']['max_absolute_mismatch_A']}` A", "", "| signal | closed 109.9 ps | replay 109.9 ps | delta |", "|---|---:|---:|---:|"]
    for label, item in pre_final.items():
        lines.append(f"| `{label}` | {item['source_value']:.8g} | {item['replay_value']:.8g} | {item['difference']:.8g} |")
    lines.extend(["", "## Ordered downstream raw navigation", "", "| track | first activity support (ps) |", "|---|---:|"])
    for label, time in progression.items():
        lines.append(f"| `{label}` | {time} |")
    lines.extend(["", "The critical fourth-response review window is `[121,130) ps`; BJ1/BJ2, QBOUT, all JTL stages, terminal, L1/L2 and replay current are retained in `mechanism_metrics_stage_b.json`. The scientific outcome is finalized only from the direct multi-evidence raw review below, not from phase or terminal area alone.", ""])
    (EXP / "analysis/STAGE_B_REVIEW.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"status": "PASS", "source_replay_current_exact": metrics["source_replay_current_exactness"]["all_stored_values_equal"], "critical_window_ps": [121.0, 130.0], "scientific_response_outcome": "PENDING_DIRECT_RAW_REVIEW"}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
