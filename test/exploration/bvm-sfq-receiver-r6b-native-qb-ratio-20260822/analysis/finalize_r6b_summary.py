#!/usr/bin/env python3
"""Attach the manually adjudicated R6-B Exploration classification."""

from __future__ import annotations

import json
from pathlib import Path


RUN = Path(__file__).resolve().parents[1]
SUMMARY = RUN / "analysis/r6b-summary.json"


def main():
    data = json.loads(SUMMARY.read_text(encoding="utf-8"))
    data.pop("provisional_verdict", None)
    data["artifact_status"] = "VALID"
    data["verdict"] = "DRIVE_GAIN_WITH_ISOLATION_PRESERVED"
    data["highest_evidence_level"] = "isolated early-native-QB drive gain with bounded source/storage guard"
    data["classification_basis"] = {
        "read1_secondary_voltage_peak_gain_vs_r6a": 64.43943 / 53.79025,
        "read1_secondary_current_excursion_gain_vs_r6a": 18.816419 / 9.6671,
        "read1_bjl2_activity_range_gain_vs_r6a": 0.0029640379981662203 / 0.0028851926393584945,
        "read1_bjl2_largest_segment_gain_vs_r6a": 0.0015879525292050761 / 0.001584610275400143,
        "read1_bjl2_complete_segment_count": 0,
        "read0_bjl2_complete_segment_count": 0,
        "logical1_read0_control_bjl2_complete_segment_count": 0,
        "logical0_read0_control_bjl2_complete_segment_count": 0,
        "source_guard": "R6-B read1/read0 SL/N6/primary/storage/post-window comparison remains close to canonical and R6-A",
        "local_pass": False,
        "downstream_delivery": "not_tested",
    }
    data["limitations"] = [
        "single operating point; no secondary/K sweep",
        "no timestep refinement ladder",
        "native QB parameters unchanged",
        "no JTL or T1",
        "classification is descriptive Exploration evidence, not a universal Gate",
    ]
    SUMMARY.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(data, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
