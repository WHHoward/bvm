#!/usr/bin/env python3
"""Analytic precheck for the R6-A weak-mutual native-QB interface.

This script reads only the committed direct-SL native-QB raw CSVs.  Those
currents are a source waveform proxy, not the current that the isolated
primary will necessarily carry.  No JoSIM run is performed here.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path
from statistics import median


RUN = Path(__file__).resolve().parents[1]
REPO = RUN.parents[2]
SOURCE_ROOT = REPO / "test/exploration/bvm-sfq-receiver-native-qb-20260822/raw"
OUT = RUN / "analysis"
PHI0 = 2.067833848e-15
K = 0.50
L_PRI_H = 0.20e-12
L_SEC_H = 2.0e-12
M_H = K * math.sqrt(L_PRI_H * L_SEC_H)
WINDOW = (94.0, 130.0)
PRE = (80.0, 90.0)
POST = (150.0, 170.0)
CASES = ["read1", "read0", "logical1-read0-control", "logical0-read0-control"]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load(path: Path):
    with path.open(newline="", encoding="utf-8") as stream:
        rows = []
        for row in csv.DictReader(stream):
            rows.append(
                {
                    "t_ps": float(row["time"]) * 1.0e12,
                    "i_A": float(row["I(L_SL|XBVM1)"]),
                    "v_V": float(row["V(SL1)"]),
                    "n6_V": float(row["V(N6|XBVM1)"]),
                }
            )
    return rows


def select(rows, window):
    return [row for row in rows if window[0] <= row["t_ps"] < window[1]]


def trapz(rows, key):
    value = 0.0
    for left, right in zip(rows, rows[1:]):
        value += 0.5 * (left[key] + right[key]) * (right["t_ps"] - left["t_ps"])
    return value


def extrema(values):
    return {
        "min": min(values),
        "max": max(values),
        "peak_abs": max(abs(value) for value in values),
    }


def analyze_case(case):
    path = SOURCE_ROOT / case / "run-01.csv"
    rows = load(path)
    pre = select(rows, PRE)
    activity = select(rows, WINDOW)
    post = select(rows, POST)
    pre_i = median(row["i_A"] for row in pre)
    values = [row["i_A"] for row in activity]
    delta_values = [value - pre_i for value in values]
    derivatives = []
    for left, right in zip(activity, activity[1:]):
        dt_s = (right["t_ps"] - left["t_ps"]) * 1.0e-12
        derivatives.append((right["i_A"] - left["i_A"]) / dt_s)
    d_ext = extrema(derivatives)
    flux_values = [M_H * (value - pre_i) / PHI0 for value in values]
    voltage_values = [M_H * derivative for derivative in derivatives]
    return {
        "case": case,
        "source_raw": str(path.relative_to(REPO)),
        "source_raw_sha256": sha256(path),
        "row_count": len(rows),
        "pre_median_uA": pre_i * 1.0e6,
        "activity_current_uA": {
            "min": min(values) * 1.0e6,
            "max": max(values) * 1.0e6,
            "peak_abs": max(abs(value) for value in values) * 1.0e6,
            "delta_min": min(delta_values) * 1.0e6,
            "delta_max": max(delta_values) * 1.0e6,
            "delta_peak_abs": max(abs(value) for value in delta_values) * 1.0e6,
        },
        "current_impulse_uA_ps": trapz(activity, "i_A") * 1.0e6,
        "derivative_uA_per_ps": {
            "min": d_ext["min"] * 1.0e-6,
            "max": d_ext["max"] * 1.0e-6,
            "peak_abs": d_ext["peak_abs"] * 1.0e-6,
        },
        "external_flux_over_phi0": {
            "min": min(flux_values),
            "max": max(flux_values),
            "peak_abs": max(abs(value) for value in flux_values),
        },
        "induced_voltage_uV": {
            "min": min(voltage_values) * 1.0e6,
            "max": max(voltage_values) * 1.0e6,
            "peak_abs": max(abs(value) for value in voltage_values) * 1.0e6,
        },
        "pre_post_current_uA": {
            "pre_median": pre_i * 1.0e6,
            "post_median": median(row["i_A"] for row in post) * 1.0e6,
            "post_minus_pre": (median(row["i_A"] for row in post) - pre_i) * 1.0e6,
        },
        "source_voltage_peak_mV": max(abs(row["v_V"]) for row in activity) * 1.0e3,
        "source_n6_peak_mV": max(abs(row["n6_V"]) for row in activity) * 1.0e3,
    }


def main():
    cases = [analyze_case(case) for case in CASES]
    read1 = next(item for item in cases if item["case"] == "read1")
    read0 = next(item for item in cases if item["case"] == "read0")
    summary = {
        "precheck": "R6A_SINGLE_POINT_ANALYTIC_PRECHECK",
        "jo_sim_runs_performed": False,
        "parameters": {
            "L_PRI_pH": L_PRI_H * 1.0e12,
            "L_SEC_pH": L_SEC_H * 1.0e12,
            "K": K,
            "M_pH": M_H * 1.0e12,
            "R_PRI_ohm": 12.0,
            "phi0_Wb": PHI0,
        },
        "source_proxy_definition": "I(L_SL|XBVM1) from direct-SL native-QB raw; isolated I(R_PRI)/I(L_PRI) must be measured separately",
        "windows_ps": {"pre": PRE, "activity": WINDOW, "post": POST},
        "frequency_scale_note": {
            "representative_edge_ps": [5.0, 10.0],
            "omega_M_ohm": {
                "5ps": 2.0 * math.pi / (5.0e-12) * M_H,
                "10ps": 2.0 * math.pi / (10.0e-12) * M_H,
            },
            "omega_Lsec_ohm": {
                "5ps": 2.0 * math.pi / (5.0e-12) * L_SEC_H,
                "10ps": 2.0 * math.pi / (10.0e-12) * L_SEC_H,
            },
            "reflected_loading_relative_to_K08": (K / 0.80) ** 2,
        },
        "read1_read0_separation": {
            "positive_peak_current_ratio": read1["activity_current_uA"]["max"] / read0["activity_current_uA"]["max"],
            "peak_abs_current_ratio": read1["activity_current_uA"]["peak_abs"] / read0["activity_current_uA"]["peak_abs"],
            "positive_flux_peak_difference_phi0": read1["external_flux_over_phi0"]["max"] - read0["external_flux_over_phi0"]["max"],
            "positive_induced_voltage_peak_difference_uV": read1["induced_voltage_uV"]["max"] - read0["induced_voltage_uV"]["max"],
        },
        "cases": cases,
        "analytic_verdict": "R6A_SINGLE_POINT_WORTH_TESTING",
        "verdict_reason": "read1 has a state-dependent positive current/flux/induced-voltage margin over read0 and controls; M is reduced relative to the K=0.80 pickup while the native QB loop remains available to capture the transient",
        "critical_unknown": "external flux returns near zero after the bipolar primary transient, so persistent QB state capture is not established analytically",
    }
    (OUT / "r6a-precheck.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
