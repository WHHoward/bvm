#!/usr/bin/env python3
"""R5-C analytic saddle precheck from committed R4-A/R5-A CSV evidence.

This script does not run JoSIM.  It calculates the static nonlinear loop
branches and reports source/phase quantities from the existing raw files.
"""

from __future__ import annotations

import argparse
import csv
import glob
import json
import math
import os
from statistics import median


PHI0 = 2.067833848e-15
L_H = 100.0e-12
L_TX = 0.20e-12
K = -0.80
M = K * math.sqrt(L_H * L_TX)
IC = 0.05 * 0.1e-3
RN = 16.0 / 0.05
R0 = 160.0 / 0.05
C = 0.07e-12 * 0.05
BETA_L = 2.0 * math.pi * L_H * IC / PHI0
BETA_C = 2.0 * math.pi * IC * RN * RN * C / PHI0
PHI_S = math.acos(-1.0 / BETA_L)


def read_rows(path: str):
    with open(path, newline="") as stream:
        reader = csv.DictReader(stream)
        rows = []
        for row in reader:
            loop_key = "I(L_QB|XTRIG)" if "I(L_QB|XTRIG)" in row else "I(L_H|XTRIG)"
            rows.append(
                {
                    "t_ps": float(row["time"]) * 1.0e12,
                    "p_set": float(row["P(B_SET|XTRIG)"]),
                    "i_tx": float(row["I(L_TX|XTRIG)"]),
                    "i_loop": float(row[loop_key]),
                }
            )
    return rows


def select(rows, lo, hi):
    return [row for row in rows if lo <= row["t_ps"] < hi]


def trap(rows, key):
    return sum(
        0.5 * (a[key] + b[key]) * (b["t_ps"] - a["t_ps"])
        for a, b in zip(rows, rows[1:])
    )


def static_branch(bias_uA):
    ib = bias_uA * 1.0e-6 / IC

    def f(phi):
        return phi + BETA_L * (ib + math.sin(phi))

    # n=0 zero-voltage branch connected continuously to the R5-A point.
    lo, hi = -math.pi / 2.0, 0.0
    if f(lo) * f(hi) > 0.0:
        raise RuntimeError(f"n=0 branch bracket failed for bias={bias_uA} uA")
    flo = f(lo)
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        fmid = f(mid)
        if flo * fmid <= 0.0:
            hi = mid
        else:
            lo, flo = mid, fmid
    phi_op = 0.5 * (lo + hi)

    def saddle_external(phi_s):
        # phi + beta_L*(i_b + sin(phi)) + phi_ext = 0 for n=0.
        return -phi_s - BETA_L * (ib + math.sin(phi_s))

    ext_reverse = saddle_external(-PHI_S)
    ext_forward = saddle_external(PHI_S)
    return {
        "bias_uA": bias_uA,
        "bias_over_ic": ib,
        "phi_op_rad": phi_op,
        "phi_op_turn": phi_op / (2.0 * math.pi),
        "reverse_saddle_rad": -PHI_S,
        "reverse_saddle_turn": -PHI_S / (2.0 * math.pi),
        "forward_saddle_rad": PHI_S,
        "forward_saddle_turn": PHI_S / (2.0 * math.pi),
        "reverse_margin_turn": abs((-PHI_S) - phi_op) / (2.0 * math.pi),
        "forward_margin_turn": abs(PHI_S - phi_op) / (2.0 * math.pi),
        "reverse_required_external_phi_rad": ext_reverse,
        "reverse_required_external_flux_phi0": ext_reverse / (2.0 * math.pi),
        "reverse_required_equivalent_loop_current_uA": ext_reverse * PHI0 / (2.0 * math.pi * L_H) * 1.0e6,
        "reverse_required_primary_current_uA": ext_reverse * PHI0 / (2.0 * math.pi * M) * 1.0e6,
        "forward_required_external_phi_rad": ext_forward,
        "forward_required_external_flux_phi0": ext_forward / (2.0 * math.pi),
        "forward_required_equivalent_loop_current_uA": ext_forward * PHI0 / (2.0 * math.pi * L_H) * 1.0e6,
        "forward_required_primary_current_uA": ext_forward * PHI0 / (2.0 * math.pi * M) * 1.0e6,
    }


def raw_case(path):
    rows = read_rows(path)
    pre = select(rows, 80.0, 90.0)
    activity = select(rows, 97.0, 130.0)
    p0 = median(row["p_set"] for row in pre)
    pmin = min(row["p_set"] for row in activity)
    pmax = max(row["p_set"] for row in activity)
    i_min = min(row["i_tx"] for row in activity)
    i_max = max(row["i_tx"] for row in activity)
    ext_min = M * i_max / PHI0
    ext_max = M * i_min / PHI0
    n_values = [
        row["p_set"] / (2.0 * math.pi)
        + (L_H * row["i_loop"] + M * row["i_tx"]) / PHI0
        for row in activity
    ]
    return {
        "case": os.path.basename(os.path.dirname(path)),
        "path": path,
        "rows": len(rows),
        "end_ps": rows[-1]["t_ps"],
        "p_pre_rad": p0,
        "p_pre_turn": p0 / (2.0 * math.pi),
        "p_activity_min_turn_abs": pmin / (2.0 * math.pi),
        "p_activity_max_turn_abs": pmax / (2.0 * math.pi),
        "p_activity_min_rel_turn": (pmin - p0) / (2.0 * math.pi),
        "p_activity_max_rel_turn": (pmax - p0) / (2.0 * math.pi),
        "i_tx_min_uA": i_min * 1.0e6,
        "i_tx_max_uA": i_max * 1.0e6,
        "phi_ext_min_phi0": ext_min,
        "phi_ext_max_phi0": ext_max,
        "fluxoid_n_activity_min": min(n_values),
        "fluxoid_n_activity_max": max(n_values),
        # trap() uses t_ps, so A*ps -> microA*ps multiplies by 1e6.
        "i_tx_area_uA_ps": trap(activity, "i_tx") * 1.0e6,
        "i_tx_positive_area_uA_ps": trap([{**row, "i_tx": max(row["i_tx"], 0.0)} for row in activity], "i_tx") * 1.0e6,
        "i_tx_negative_area_uA_ps": trap([{**row, "i_tx": min(row["i_tx"], 0.0)} for row in activity], "i_tx") * 1.0e6,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--r4-glob", required=True)
    parser.add_argument("--r5-glob", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    r4_paths = sorted(glob.glob(args.r4_glob))
    r5_paths = sorted(glob.glob(args.r5_glob))
    report = {
        "constants": {
            "phi0_Wb": PHI0,
            "L_H_H": L_H,
            "L_TX_H": L_TX,
            "K": K,
            "M_H": M,
            "M_pH": M * 1.0e12,
            "area": 0.05,
            "Ic_A": IC,
            "RN_ohm": RN,
            "R0_ohm": R0,
            "C_F": C,
            "beta_L": BETA_L,
            "beta_c": BETA_C,
            "saddle_abs_rad": PHI_S,
            "saddle_abs_turn": PHI_S / (2.0 * math.pi),
        },
        "static": {
            "bias_4p2_uA": static_branch(4.2),
            "candidate_bias_9p93_uA": static_branch(9.93),
        },
        "r4a_raw": [raw_case(path) for path in r4_paths],
        "r5a_raw": [raw_case(path) for path in r5_paths],
        "method_note": "External flux is Phi_ext=M*I(L_TX); its signed Phi0 value uses the declared L_TX/L_H/K orientation. Phase margins use same-JJ P(B_SET) relative to the 80-90 ps pre median. Candidate projection keeps the measured R5-A relative excursion fixed; it is an inference, not a dynamic simulation.",
    }
    with open(args.output, "w", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
