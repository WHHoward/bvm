#!/usr/bin/env python3
"""R10-A analytic single-point selection from the accepted R9-A raw data.

This is a calibrated static/load-line precheck, not a JoSIM run and not an
event detector.  It keeps the three native JJ current relations, the R9-A
fluxoid branch, the complete L1/L2/RB KCL, and a finite-current local feed at
native node 4.  The input-loop constant absorbs the fixed R6-B source/mutual
state measured in the R9-A settled window.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from scipy.optimize import root


RUN = Path(__file__).resolve().parents[1]
REPO = RUN.parents[2]
R9 = REPO / "test/exploration/bvm-sfq-receiver-r9a-l2-routing-20260823"
RAW = R9 / "raw"
OUT = RUN / "analysis"

PHI0_PHUA = 2067.833848  # Phi0 in pH*microampere
TWO_PI = 2.0 * math.pi
IB_UA = 90.0
LIN_PH = 0.8
L1_PH = 2.50
L2_PH = 2.50
ICS_UA = 133.0
IC1_UA = 112.0
IC2_UA = 189.0
R_LOCAL_OHM = 100.0
L_LOCAL_PH = 10.0
TARGET_FEED_UA = 214.0
WINDOW_PRE = (80.0, 90.0)
WINDOW_ACTIVITY = (94.0, 130.0)

CASES = {
    "read1": RAW / "read1" / "run-02.csv",
    "read0": RAW / "read0" / "run-02.csv",
    "logical1_read0_control": RAW / "logical1-read0-control" / "run-02.csv",
    "logical0_read0_control": RAW / "logical0-read0-control" / "run-02.csv",
}


def load(path: Path):
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        lookup = {field.casefold(): field for field in (reader.fieldnames or [])}
        rows = []
        for raw in reader:
            rows.append({key: float(raw[original]) for key, original in lookup.items()})
    return rows, lookup


def value(row, lookup, key):
    return row[key.casefold()]


def in_window(row, lookup, window):
    return window[0] <= value(row, lookup, "time") * 1.0e12 < window[1]


def median(rows, lookup, key, window):
    vals = [value(row, lookup, key) for row in rows if in_window(row, lookup, window)]
    vals.sort()
    if not vals:
        raise RuntimeError(f"empty window for {key}: {window}")
    middle = len(vals) // 2
    if len(vals) % 2:
        return vals[middle]
    return 0.5 * (vals[middle - 1] + vals[middle])


def extrema(rows, lookup, key, window):
    vals = [value(row, lookup, key) for row in rows if in_window(row, lookup, window)]
    return {"min": min(vals), "max": max(vals), "p2p": max(vals) - min(vals)}


loaded = {name: load(path) for name, path in CASES.items()}
baseline_rows, baseline_lookup = loaded["logical1_read0_control"]

ps0 = median(baseline_rows, baseline_lookup, "P(BJs|XBQ)", WINDOW_PRE)
p10 = median(baseline_rows, baseline_lookup, "P(BJL1|XBQ)", WINDOW_PRE)
p20 = median(baseline_rows, baseline_lookup, "P(BJL2|XBQ)", WINDOW_PRE)
is0 = median(baseline_rows, baseline_lookup, "I(BJs|XBQ)", WINDOW_PRE) * 1.0e6
i10 = median(baseline_rows, baseline_lookup, "I(BJL1|XBQ)", WINDOW_PRE) * 1.0e6
i20 = median(baseline_rows, baseline_lookup, "I(BJL2|XBQ)", WINDOW_PRE) * 1.0e6
il10 = median(baseline_rows, baseline_lookup, "I(L1|XBQ)", WINDOW_PRE) * 1.0e6
il20 = median(baseline_rows, baseline_lookup, "I(L2|XBQ)", WINDOW_PRE) * 1.0e6

kphi = TWO_PI / PHI0_PHUA


def jj_currents(x):
    ps, p1, p2 = x
    return (
        ICS_UA * math.sin(ps),
        IC1_UA * math.sin(p1),
        IC2_UA * math.sin(p2),
    )


def branch_currents(x):
    is_, i1, i2 = jj_currents(x)
    il1 = is_ - i1
    il2 = IB_UA + il1
    return {"BJs": is_, "BJL1": i1, "BJL2": i2, "L1": il1, "L2": il2}


# The input-loop constant includes the fixed R6-B mutual/source fluxoid state.
# It is calibrated to the measured R9-A settled branch, not assumed to be zero.
C_INPUT = ps0 + p10 + kphi * LIN_PH * is0
C_LOOP = p10 - p20 - kphi * (L1_PH * il10 + L2_PH * il20)


def equations(x, feed_ua):
    currents = branch_currents(x)
    return np.array(
        [
            x[0] + x[1] + kphi * LIN_PH * currents["BJs"] - C_INPUT,
            x[1]
            - x[2]
            - kphi * (L1_PH * currents["L1"] + L2_PH * currents["L2"])
            - C_LOOP,
            currents["BJL2"] - currents["L2"] - feed_ua,
        ],
        dtype=float,
    )


def jacobian(x):
    ps, p1, p2 = x
    dis = ICS_UA * math.cos(ps)
    di1 = IC1_UA * math.cos(p1)
    di2 = IC2_UA * math.cos(p2)
    return np.array(
        [
            [1.0 + kphi * LIN_PH * dis, 1.0, 0.0],
            [-kphi * (L1_PH + L2_PH) * dis, 1.0 + kphi * (L1_PH + L2_PH) * di1, -1.0],
            [-dis, di1, di2],
        ],
        dtype=float,
    )


baseline_x = np.array([ps0, p10, p20], dtype=float)
baseline_residual = float(np.linalg.norm(equations(baseline_x, 0.0)))


def solve_feed(feed_ua, guess=baseline_x):
    solution = root(lambda x: equations(x, feed_ua), guess)
    if not solution.success or np.linalg.norm(equations(solution.x, feed_ua)) > 1.0e-7:
        raise RuntimeError(f"load-line solve failed at {feed_ua} uA: {solution.message}")
    return solution.x


def fold_equations(z):
    x = z[:3]
    feed = z[3]
    return np.r_[equations(x, feed), np.linalg.det(jacobian(x)) / 1000.0]


fold_solution = root(fold_equations, np.array([-0.44, 0.64, 1.83, 216.2]))
if not fold_solution.success or np.linalg.norm(fold_equations(fold_solution.x)) > 1.0e-6:
    raise RuntimeError(f"fold solve failed: {fold_solution.message}")
fold_x = fold_solution.x[:3]
fold_feed_ua = float(fold_solution.x[3])
target_x = solve_feed(TARGET_FEED_UA, guess=np.array([-0.41, 0.60, 1.68]))


def static_record(x, feed_ua):
    branch = branch_currents(x)
    singular_values = np.linalg.svd(jacobian(x), compute_uv=False)
    return {
        "feed_uA": feed_ua,
        "phase_rad": {"BJs": x[0], "BJL1": x[1], "BJL2": x[2]},
        "phase_turns_absolute": {name: phase / TWO_PI for name, phase in zip(("BJs", "BJL1", "BJL2"), x)},
        "current_uA": branch,
        "residual_norm": float(np.linalg.norm(equations(x, feed_ua))),
        "jacobian_singular_values": singular_values.tolist(),
        "BJL2_bare_saddle_phase_margin_rad": math.pi / 2.0 - x[2],
        "coupled_fold_feed_margin_uA": fold_feed_ua - feed_ua,
        "coupled_fold_phase_margin_rad": fold_x[2] - x[2],
    }


read1_rows, read1_lookup = loaded["read1"]
read0_rows, read0_lookup = loaded["read0"]
settled_bjl2 = i20
read1_bjl2 = extrema(read1_rows, read1_lookup, "I(BJL2|XBQ)", WINDOW_ACTIVITY)
read0_bjl2 = extrema(read0_rows, read0_lookup, "I(BJL2|XBQ)", WINDOW_ACTIVITY)
read1_positive = read1_bjl2["max"] * 1.0e6 - settled_bjl2
read1_negative = read1_bjl2["min"] * 1.0e6 - settled_bjl2
read0_positive = read0_bjl2["max"] * 1.0e6 - settled_bjl2
read0_negative = read0_bjl2["min"] * 1.0e6 - settled_bjl2

target = static_record(target_x, TARGET_FEED_UA)
fold = static_record(fold_x, fold_feed_ua)
read1_equivalent_margin = fold_feed_ua - TARGET_FEED_UA - read1_positive
read0_equivalent_margin = fold_feed_ua - TARGET_FEED_UA - read0_positive

ic_parameters = {
    "BJs": {"AREA": 1.33, "Ic_uA": 133.0, "C_fF": 93.1, "RN_ohm": 16.0 / 1.33, "R0_ohm": 160.0 / 1.33},
    "BJL1": {"AREA": 1.12, "Ic_uA": 112.0, "C_fF": 78.4, "RN_ohm": 16.0 / 1.12, "R0_ohm": 160.0 / 1.12},
    "BJL2": {"AREA": 1.89, "Ic_uA": 189.0, "C_fF": 132.3, "RN_ohm": 16.0 / 1.89, "R0_ohm": 160.0 / 1.89},
}

result = {
    "artifact": "R10-A analytic precheck; no JoSIM execution",
    "source_raw": {name: str(path) for name, path in CASES.items()},
    "windows_ps": {"settled": WINDOW_PRE, "activity": WINDOW_ACTIVITY},
    "r9_settled_read0_source": {
        "P_BJs_rad": ps0,
        "P_BJL1_rad": p10,
        "P_BJL2_rad": p20,
        "I_BJs_uA": is0,
        "I_BJL1_uA": i10,
        "I_BJL2_uA": i20,
        "I_L1_uA": il10,
        "I_L2_uA": il20,
    },
    "r9_bjl2_activity_current_uA": {
        "read1": read1_bjl2,
        "read0": read0_bjl2,
        "read1_positive_excursion_uA": read1_positive,
        "read1_negative_excursion_uA": read1_negative,
        "read0_positive_excursion_uA": read0_positive,
        "read0_negative_excursion_uA": read0_negative,
    },
    "model": {
        "equations": [
            "iBJs=Ics*sin(phi_s), iBJL1=Ic1*sin(phi_1), iBJL2=Ic2*sin(phi_2)",
            "iL1=iBJs-iBJL1; iL2=IB+iL1",
            "iFeed=iBJL2-iL2",
            "phi_s+phi_1+2pi*Lin*iBJs/Phi0=C_INPUT",
            "phi_1-phi_2-2pi*(L1*iL1+L2*iL2)/Phi0=C_LOOP",
        ],
        "calibrated_constants": {"C_INPUT_rad": C_INPUT, "C_LOOP_rad": C_LOOP},
        "baseline_residual_norm": baseline_residual,
        "flux_unit": "pH*uA; Phi0=2067.833848 pH*uA",
    },
    "fold": fold,
    "selected_point": target,
    "first_order_selection_check": {
        "fold_minus_read1_positive_uA": fold_feed_ua - read1_positive,
        "selected_feed_uA": TARGET_FEED_UA,
        "read1_equivalent_margin_uA": read1_equivalent_margin,
        "read0_equivalent_margin_uA": read0_equivalent_margin,
        "interpretation": "equivalent-feed margin only; not an event criterion",
    },
    "source_impedance": {
        "R_DC_ohm": R_LOCAL_OHM,
        "L_series_pH": L_LOCAL_PH,
        "DC_feed_uA": TARGET_FEED_UA,
        "V_source_mV": TARGET_FEED_UA * R_LOCAL_OHM / 1000.0,
        "omega_at_1p5ps_rad_s": 2.0 * math.pi / 1.5e-12,
        "X_L_at_1p5ps_ohm": 2.0 * math.pi / 1.5e-12 * L_LOCAL_PH * 1.0e-12,
        "Z_abs_at_1p5ps_ohm": math.hypot(R_LOCAL_OHM, 2.0 * math.pi / 1.5e-12 * L_LOCAL_PH * 1.0e-12),
        "not_a_direct_BJL2_shunt": True,
    },
    "jjmit_actual_parameters": ic_parameters,
}

(OUT / "r10a-analytic-precheck.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")

md = []
md.append("# R10-A analytic precheck: output-side local BJL2 bias feed\n")
md.append("## Status and selected point\n")
md.append("This is a physics-informed static/load-line precheck using accepted R9-A raw data. It does not run JoSIM and does not use static saddle crossing as an event criterion.\n")
md.append("Selected single point: **source-to-node-4 feed = 214.0 µA DC**, implemented by a 21.4 mV independent voltage source through 100 Ω in series with 10 pH. The positive feed direction is source → resistor → inductor → native QB node 4 (the BJL2 top node).\n")
md.append("## Topology and source impedances\n")
md.append("```text\nVLB(BIAS,0) -- RLB=100 ohm -- LLB=10 pH -- native node 4\n                                                   |\n                                                BJL2||RJ2\n                                                   |\n                                                  GND\n```\n")
md.append("The source return is the independent voltage-source return to ground. The branch is a finite-impedance bias injection, not a resistor directly placed across BJL2 and not a passive damping shunt. At DC, `Z=100 ohm` and the selected 21.4 mV source sets 214 µA only when the full network settles; the injected current then splits according to node-4 KCL. At 1.5 ps, `X_L=41.89 ohm` and `|Z|=108.42 ohm`; this is intentionally larger than RJ2=22 ohm and BJL2 RN=8.47 ohm, limiting AC loading.\n")
md.append("## Calibrated nonlinear load-line\n")
md.append("The model retains all three native JJ sine current relations, IB=90 µA, L1=L2=2.50 pH, the complete L1/L2/RB KCL, and the R9-A fluxoid branch. The input-loop constant is calibrated from the R9-A settled R6-B state; it includes the fixed source/mutual fluxoid contribution. For a feed current `iF` from the local source into node 4:\n")
md.append("```text\niL1 = iBJs - iBJL1\niL2 = IB + iL1\niF  = iBJL2 - iL2\n```\n")
md.append("This explicitly prevents the incorrect assumption that all 214 µA enters BJL2.\n")
md.append("## Fold and selection\n")
md.append(f"The calibrated positive continuation reaches its coupled static fold at feed **{fold_feed_ua:.6f} µA**, with phase `(BJs,BJL1,BJL2)=({fold_x[0]:.6f},{fold_x[1]:.6f},{fold_x[2]:.6f}) rad`. The selected 214.0 µA point is on the stable side with coupled fold distance **{fold_feed_ua-TARGET_FEED_UA:.6f} µA** and BJL2 phase **{target_x[2]:.6f} rad**. Its bare BJL2 π/2 comparison is only a diagnostic; the coupled fold is the relevant static continuation marker.\n")
md.append(f"R9 read1 BJL2 positive activity excursion was +{read1_positive:.6f} µA; read0 was +{read0_positive:.6f} µA. The first-order equivalent-feed estimate puts the read1 excursion {read1_equivalent_margin:.6f} µA beyond the fold and leaves read0 {read0_equivalent_margin:.6f} µA below it. This is only a single-point selection heuristic; it is not an event or switching claim. The negative lobes move away from this positive fold.\n")
md.append("## Full-network selected settled split (analytic prediction)\n")
md.append("| quantity | predicted value |\n|---|---:|\n")
for name, val in [("P(BJs)", target["phase_rad"]["BJs"]), ("P(BJL1)", target["phase_rad"]["BJL1"]), ("P(BJL2)", target["phase_rad"]["BJL2"]), ("I(BJs)=I(Lin) [µA]", target["current_uA"]["BJs"]), ("I(BJL1) [µA]", target["current_uA"]["BJL1"]), ("I(BJL2) [µA]", target["current_uA"]["BJL2"]), ("I(L1) [µA]", target["current_uA"]["L1"]), ("I(L2) [µA]", target["current_uA"]["L2"]), ("I(RB) [µA]", IB_UA), ("I(local feed) [µA]", TARGET_FEED_UA)]:
    md.append(f"| `{name}` | {val:.8f} |\n")
md.append("At this point, the feed current is predicted to split into approximately 187.97 µA through BJL2 and -26.03 µA through the declared 3→4 L2 branch; the remainder of the bias redistribution appears in BJs/BJL1/L1. The actual JoSIM settled values will be measured again.\n")
md.append("## jjmit scaling used\n")
md.append("`jjmit` gives Ic,C proportional to AREA and RN,R0 proportional to 1/AREA. The unchanged receiver values are BJs AREA=1.33 (Ic=133 µA, C=93.1 fF, RN=12.03 Ω, R0=120.30 Ω), BJL1 AREA=1.12 (112 µA, 78.4 fF, 14.29 Ω, 142.86 Ω), and BJL2 AREA=1.89 (189 µA, 132.3 fF, 8.47 Ω, 84.66 Ω).\n")
md.append("## Precheck verdict\n")
md.append("**R10A_SINGLE_POINT_WORTH_TESTING**. The model has a stable-side selected operating point, a finite read0 equivalent margin, and a read1-near-fold first-order rationale. The actual four-case result must be judged by continuous phase, same-JJ voltage area, retrap/free-running, selectivity, and source guards; crossing the static continuation marker alone will not count as an event.\n")
(OUT / "R10A_ANALYTIC_PRECHECK.md").write_text("".join(md), encoding="utf-8")

print(json.dumps({
    "selected_feed_uA": TARGET_FEED_UA,
    "selected_source_mV": result["source_impedance"]["V_source_mV"],
    "fold_feed_uA": fold_feed_ua,
    "read1_positive_excursion_uA": read1_positive,
    "read0_positive_excursion_uA": read0_positive,
    "read1_equivalent_margin_uA": read1_equivalent_margin,
    "read0_equivalent_margin_uA": read0_equivalent_margin,
    "selected_static": target,
}, indent=2))
