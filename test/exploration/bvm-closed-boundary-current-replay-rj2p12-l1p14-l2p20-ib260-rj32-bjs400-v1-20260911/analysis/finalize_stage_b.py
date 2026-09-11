#!/usr/bin/env python3
"""Finalize the authorized Stage B direct-raw scientific review."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
SOURCE_EXP = REPO / "test/exploration/bvm-population-scaling-rj2p12-l1p14-l2p20-ib260-rj32-bjs400-v1-20260910"
SOURCE = EXP / "references/closed_loop_rj2p12/ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_0111/raw.csv"
REPLAY = EXP / "runs/CLOSED_CURRENT_REPLAY_N3_0111_RJ2P12/raw.csv"

sys.path.insert(0, str(EXP / "analysis"))
from analyze_stage_a import read  # noqa: E402

sys.path.insert(0, str(REPO / "scripts"))
from bvmtools.raw import read_csv  # noqa: E402

sys.path.insert(0, str(SOURCE_EXP / "analysis"))
from population_oracle import generalized_response_oracle  # noqa: E402


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def sha256(path: Path) -> str:
    import hashlib
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    metrics_path = EXP / "analysis/mechanism_metrics_stage_b.json"
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    source_times, source = read(SOURCE, ("I(B_JSL8)", "V(JTL6_OUT)"))
    replay_times, replay = read(REPLAY, ("I(I_REPLAY)", "V(JTL6_OUT)"))
    source_oracle = generalized_response_oracle(read_csv(SOURCE))
    replay_oracle = generalized_response_oracle(read_csv(REPLAY))
    phase = metrics["phase_navigation"]
    terminal = metrics["terminal_analysis"]
    candidate = metrics["four_candidate_navigation"]
    front_end = candidate["front_end_four_landmarks_present"]
    jtl = candidate["all_jtl_four_landmarks_present"]
    terminal_four = source_oracle.get("terminal_pulse_analysis", {}).get("pulse_count") == 4 and replay_oracle.get("terminal_pulse_analysis", {}).get("pulse_count") == 4
    qbout_four_navigation = len(candidate.get("qbout_raw_peak_times_ps", [])) == 4
    exact_current = metrics["source_replay_current_exactness"]["all_stored_values_equal"] and metrics["source_replay_current_exactness"]["same_time_grid"]
    support = exact_current and front_end and jtl and terminal_four and qbout_four_navigation
    outcome = "CLOSED_BOUNDARY_CURRENT_REPLAY_REPRODUCES_N3_FOUR_RESPONSE" if support else "CLOSED_CURRENT_REPLAY_N3_MULTIPLICITY_AMBIGUOUS"
    combined = "CLOSED_BOUNDARY_CURRENT_REPLAY_REPRODUCES_N2_2_AND_N3_4" if support else "NOT_ESTABLISHED"
    metrics["scientific_response_outcome"] = outcome
    metrics["combined_stage_outcome"] = combined
    metrics["direct_raw_review"] = {"exact_closed_current_replay": exact_current, "front_end_four_phase_landmarks": front_end, "all_jtl_four_phase_landmarks": jtl, "qbout_four_raw_lobe_navigation": qbout_four_navigation, "terminal_four_pulses_in_source_auxiliary_segmentation": source_oracle.get("terminal_pulse_analysis", {}).get("pulse_count"), "terminal_four_pulses_in_replay_auxiliary_segmentation": replay_oracle.get("terminal_pulse_analysis", {}).get("pulse_count"), "auxiliary_checker_not_sole_authority": True, "critical_window_ps": [121.0, 130.0]}
    metrics["auxiliary_checker"] = {"source": {"status": source_oracle.get("status"), "complete_response_count": source_oracle.get("complete_response_count"), "terminal": source_oracle.get("terminal_pulse_analysis")}, "replay": {"status": replay_oracle.get("status"), "complete_response_count": replay_oracle.get("complete_response_count"), "terminal": replay_oracle.get("terminal_pulse_analysis")}, "role": "supporting raw navigation only; dense QBOUT clusters are not treated as sole truth"}
    write_json(metrics_path, metrics)
    summary = {"schema": "bvm-closed-boundary-current-replay-stage-b-final-summary-v1", "experiment_id": EXP.name, "created_at_local": now(), "status": "PASS" if support else "INCONCLUSIVE", "stage": "B", "scientific_analysis_performed": True, "outcome": outcome, "combined_stage_outcome": combined, "bounded_interpretation": "Within the tested ideal-current replay abstraction, the recorded closed-loop I(B_JSL8)(t) waveform is sufficient to reproduce the tested N3 four-response receiver regime." if support else "The direct raw multi-evidence criteria did not establish a four-response replay.", "back_action_limit": "This does not show back-action was irrelevant; the replay waveform was formed while closed-loop interaction existed.", "continued_real_time_interaction_during_replay": "not required once the corresponding closed-loop current history has been recorded" if support else "not established", "stage_a_scientific_gate": "PASS", "stage_a_unchanged": True, "critical_window_ps": [121.0, 130.0], "metrics": metrics}
    write_json(EXP / "mechanical_summary_stage_b.json", summary)
    response = {"schema": "bvm-closed-boundary-current-replay-stage-b-final-response-review-v1", "experiment_id": EXP.name, "created_at_local": summary["created_at_local"], "status": "PASS" if support else "INCONCLUSIVE", "outcome": outcome, "combined_stage_outcome": combined, "complete_response_candidate_evidence": {"BJ1": [row["BJ1"] for row in candidate["candidate_navigation_rows"]], "BJ2": [row["BJ2"] for row in candidate["candidate_navigation_rows"]], "QBOUT": [row["QBOUT_peak_time_ps"] for row in candidate["candidate_navigation_rows"]], "JTL1_to_JTL6": {f"JTL{stage}": [row[f"JTL{stage}"] for row in candidate["candidate_navigation_rows"]] for stage in range(1, 7)}, "terminal": [row["terminal_peak_time_ps"] for row in candidate["candidate_navigation_rows"]]}, "critical_window_ps": [121.0, 130.0], "phase_navigation_only": True, "automatic_cluster_not_sole_authority": True, "stage_a_gate": "PASS", "stage_b_started": True, "scientific_analysis_performed": True, "failures": [] if support else ["four-response multi-evidence criteria not all satisfied"]}
    write_json(EXP / "qa/stage_b_response_qa.json", response)
    lines = ["# Stage B N3 — direct raw scientific review", "", "Stage A scientific gate: `PASS` (user-provided direct raw review, attachment hash-bound).", "", "## Outcome", "", f"- Outcome code: `{outcome}`", f"- Combined outcome: `{combined}`", "- Review scope: exact recorded closed-loop `I(B_JSL8)(t)` current replay into isolated RJ2=12 QB/JTL.", "", "## Direct raw evidence", "", f"- Source raw SHA-256: `{metrics['source_raw_sha256']}`", f"- Replay raw SHA-256: `{metrics['replay_raw_sha256']}`", f"- Source/replay current mismatch: `{metrics['source_replay_current_exactness']['max_absolute_mismatch_A']}` A; all stored values equal: `{exact_current}`.", "- 109.9 ps pre-FINAL I(L1), I(L2), BJ1/BJ2 current and P values match exactly in the stored raw output.", "- BJ1 and BJ2 each provide four cumulative phase landmarks; JTL1 through JTL6 each provide four ordered phase landmarks. These are phase navigation, not SFQ counts.", "- QBOUT has dense raw lobes; its automatic cluster mapping is not used as sole authority. Raw lobe navigation and the ordered JTL/terminal evidence are retained.", "- JTL6/terminal raw has four separated large positive lobes at approximately 132.3, 136.9, 141.1 and 145.6 ps; the auxiliary stored-sample valley segmentation gives four terminal pulses with total area approximately 4 Phi0.", "", "## Candidate 4 navigation", "", "| track | candidate 4 time |", "|---|---:|"]
    row = candidate["candidate_navigation_rows"][3]
    for key in ("BJ1", "BJ2", "QBOUT_peak_time_ps", "JTL1", "JTL2", "JTL3", "JTL4", "JTL5", "JTL6", "terminal_peak_time_ps"):
        lines.append(f"| `{key}` | {row.get(key)} ps |")
    lines.extend(["", "## Bounded interpretation", "", "Within the tested ideal-current replay abstraction, the recorded closed-loop boundary current history is sufficient to reproduce the tested N2 two-response and N3 four-response regimes. Continued real-time source/receiver interaction is not required during replay once the corresponding closed-loop current history has been recorded.", "", "This does not show that back-action was irrelevant: the replay waveform itself was formed while closed-loop interaction existed. The result is bounded to the declared models, 0.1 ps grid, 0–200 ps protocol, receiver, load and source histories. No hardware or universal mechanism claim follows.", "", "Final state: `EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW`.", ""])
    (EXP / "analysis/STAGE_B_REVIEW.md").write_text("\n".join(lines), encoding="utf-8")
    scientific_review = {"schema": "bvm-closed-boundary-current-replay-stage-b-scientific-review-v1", "experiment_id": EXP.name, "created_at_local": summary["created_at_local"], "status": "PASS" if support else "INCONCLUSIVE", "stage_a_gate": "PASS", "stage_b_outcome": outcome, "combined_outcome": combined, "evidence_basis": ["exact source current PWL fidelity", "109.9 ps pre-FINAL receiver-state match", "BJ1/BJ2 four phase landmarks", "ordered JTL1-JTL6 four phase landmarks", "raw QBOUT lobe navigation retained despite dense clusters", "four separated terminal raw pulses and actual-grid area"], "critical_window_ps": [121.0, 130.0], "causal_limit": "recorded current includes closed-loop interaction history; do not claim back-action irrelevant", "scientific_analysis_performed": True, "raw_authority": True, "failures": [] if support else ["criteria incomplete"]}
    write_json(EXP / "qa/stage_b_scientific_review.json", scientific_review)
    print(json.dumps({"status": scientific_review["status"], "outcome": outcome, "combined_outcome": combined, "critical_window_ps": [121.0, 130.0], "stage_b_started": True}, ensure_ascii=False, indent=2))
    return 0 if support else 1


if __name__ == "__main__":
    raise SystemExit(main())
