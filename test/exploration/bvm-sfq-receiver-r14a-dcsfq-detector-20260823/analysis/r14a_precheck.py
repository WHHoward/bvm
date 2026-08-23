#!/usr/bin/env python3
"""Reproduce the non-simulation R14-A interstage scale precheck."""

from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[2]
R1A_RAW = (
    REPO
    / "test/exploration/bvm-sfq-receiver-r1a-transfer-20260819/raw/l020-k080/read1/run-01.csv"
)
R13_METRICS = (
    REPO
    / "test/exploration/bvm-sfq-receiver-r13a-temporal-conditioning-20260823/analysis/input-waveform-metrics.json"
)
L1_DCSFQ_PH = 1.672
LSEC_PH = 2.0
K = 0.80
RSEC_OHM = 12.0
READ_WINDOW = (94.0, 130.0)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def load_r1a() -> tuple[np.ndarray, dict[str, np.ndarray]]:
    with R1A_RAW.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    time_ps = np.asarray([float(row["time"]) * 1e12 for row in rows])
    arrays = {
        field: np.asarray([float(row[field]) for row in rows])
        for field in rows[0]
        if field != "time"
    }
    return time_ps, arrays


def main() -> None:
    time_ps, arrays = load_r1a()
    activity = (time_ps >= READ_WINDOW[0]) & (time_ps < READ_WINDOW[1])
    v_sec = arrays["V(N_SEC|XTRIG)"][activity]
    i_load = arrays["I(R_SEC_LOAD|XTRIG)"][activity]
    i_sec = arrays["I(L_SEC|XTRIG)"][activity]
    positive_idx_local = int(np.argmax(v_sec))
    negative_idx_local = int(np.argmin(v_sec))
    positive_peak_v = float(v_sec[positive_idx_local])
    negative_peak_v = float(v_sec[negative_idx_local])
    v_peak_v = float(max(abs(positive_peak_v), abs(negative_peak_v)))
    i_load_peak_a = float(np.max(np.abs(i_load)))
    i_sec_peak_a = float(np.max(np.abs(i_sec)))
    v_peak_idx = np.flatnonzero(activity)[int(np.argmax(np.abs(v_sec)))]
    positive_peak_time_ps = float(time_ps[np.flatnonzero(activity)[positive_idx_local]])
    negative_peak_time_ps = float(time_ps[np.flatnonzero(activity)[negative_idx_local]])
    # R1a has two opposite-polarity voltage extrema. Use their measured
    # separation as a local dominant-lobe timescale rather than inventing a
    # Fourier threshold or hard-coding the result.
    lobe_timescale_ps = abs(positive_peak_time_ps - negative_peak_time_ps)
    x_l1_ohm = 2.0 * math.pi * (L1_DCSFQ_PH * 1e-12) / (lobe_timescale_ps * 1e-12)
    x_lsec_ohm = 2.0 * math.pi * (LSEC_PH * 1e-12) / (lobe_timescale_ps * 1e-12)
    # Optimistic upper estimate: all measured R1a secondary voltage appears
    # across the DCSFQ input L1, before any reflected-load voltage reduction.
    i_dcsfq_est_a = v_peak_v / x_l1_ohm
    i_rload_est_a = v_peak_v / RSEC_OHM
    i_total_est_a = i_dcsfq_est_a + i_rload_est_a
    payload = {
        "experiment": "R14-A",
        "type": "analytic_precheck_no_josim",
        "source_raw_path": str(R1A_RAW.relative_to(REPO)),
        "source_raw_sha256": sha256(R1A_RAW),
        "r13_metrics_path": str(R13_METRICS.relative_to(REPO)),
        "r13_metrics_sha256": sha256(R13_METRICS),
        "window_ps": READ_WINDOW,
        "r1a_measured": {
            "v_sec_abs_peak_uV": v_peak_v * 1e6,
            "v_sec_positive_peak_uV": positive_peak_v * 1e6,
            "v_sec_negative_peak_uV": negative_peak_v * 1e6,
            "i_rsec_load_abs_peak_uA": i_load_peak_a * 1e6,
            "i_lsec_abs_peak_uA": i_sec_peak_a * 1e6,
            "peak_time_ps": float(time_ps[v_peak_idx]),
            "positive_peak_time_ps": positive_peak_time_ps,
            "negative_peak_time_ps": negative_peak_time_ps,
            "dominant_lobe_timescale_ps": lobe_timescale_ps,
        },
        "proposed_point": {
            "L_PRI_pH": 0.20,
            "L_SEC_pH": LSEC_PH,
            "K": K,
            "M_pH": K * math.sqrt(0.20 * LSEC_PH),
            "R_SEC_LOAD_ohm": RSEC_OHM,
            "DCSFQ_L1_pH": L1_DCSFQ_PH,
        },
        "reactance_estimate": {
            "X_L1_ohm": x_l1_ohm,
            "X_LSEC_ohm": x_lsec_ohm,
            "dcsfq_I_L1_optimistic_uA": i_dcsfq_est_a * 1e6,
            "rsec_load_current_uA": i_rload_est_a * 1e6,
            "secondary_total_branch_current_uA": i_total_est_a * 1e6,
        },
        "empirical_comparison_uA": {
            "R1A_secondary_load_current": 5.564035,
            "R13_DCSFQ_I_L1_read1_peak": 110.1997,
            "R12_68p4_controlled_bump": 68.4,
            "R12_300_controlled_bump": 300.0,
        },
        "decision": "PRECHECK_NO_GO",
        "reason": (
            "Even the optimistic DCSFQ L1 branch estimate is single-digit "
            "microampere and the actual parallel termination adds intentional "
            "double-loading; no active current-gain evidence exists at this "
            "interface before simulation."
        ),
    }
    out = ROOT / "analysis/r14a-precheck-metrics.json"
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps(payload["reactance_estimate"], indent=2, sort_keys=True))
    print("decision=PRECHECK_NO_GO")


if __name__ == "__main__":
    main()
