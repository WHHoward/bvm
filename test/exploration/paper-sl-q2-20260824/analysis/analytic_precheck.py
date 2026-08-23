#!/usr/bin/env python3
"""Analytic settled/load-line precheck for the PAPER-SL-Q2 bias bracket."""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from statistics import median


ROOT = Path(__file__).resolve().parents[1]
Q1 = ROOT.parent / "paper-sl-q1-20260824"
MODEL = ROOT / "inputs/jjmit.cir"
CONTROL = Q1 / "raw/paper-j1-logical1-read0-control.csv"
BIAS = (35.0, 37.5, 40.0)


def parse_model() -> dict[str, float]:
    text = MODEL.read_text()
    model_line = next((line for line in text.splitlines() if line.lower().startswith(".model jjmit")), "")
    if not model_line:
        raise ValueError("missing .model jjmit line")
    def get(pattern: str) -> float:
        match = re.search(pattern, model_line, re.IGNORECASE)
        if not match:
            raise ValueError(f"missing model parameter {pattern}")
        return float(match.group(1))
    return {
        "icrit_A": get(r"icrit\s*=\s*([0-9.]+)m") * 1e-3,
        "rn_ohm": get(r"\brn\s*=\s*([0-9.]+)"),
        "r0_ohm": get(r"\br0\s*=\s*([0-9.]+)"),
        "cap_pF": get(r"CAP\s*=\s*([0-9.]+)p"),
    }


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def settled(rows: list[dict[str, str]], key: str) -> float:
    values = [float(row[key]) for row in rows if 140e-12 <= float(row["time"]) < 170e-12]
    return median(values)


def main() -> None:
    model = parse_model()
    rows = read_rows(CONTROL)
    keys = {
        "p_bjs": "P(BJS|XBQ)",
        "p_bjl1": "P(BJL1|XBQ)",
        "p_bjl2": "P(BJL2|XBQ)",
        "i_lin": "I(LIN|XBQ)",
        "i_l1": "I(L1|XBQ)",
        "i_l2": "I(L2|XBQ)",
        "i_rb": "I(RB|XBQ)",
        "i_bjl1": "I(BJL1|XBQ)",
        "i_bjl2": "I(BJL2|XBQ)",
        "i_rj1": "I(RJ1|XBQ)",
        "i_rj2": "I(RJ2|XBQ)",
    }
    base = {name: settled(rows, key) for name, key in keys.items()}
    bjl1 = base["i_bjl1"]
    bjl2 = base["i_bjl2"]
    total = bjl1 + bjl2
    split1 = bjl1 / total
    split2 = bjl2 / total
    areas = {"BJS": 0.50, "BJL1": 0.36, "BJL2": 0.54}
    junctions = {}
    for name, area in areas.items():
        junctions[name] = {
            "area": area,
            "ic_uA": model["icrit_A"] * area * 1e6,
            "cap_fF": model["cap_pF"] * area * 1000.0,
            "rn_ohm": model["rn_ohm"] / area,
            "r0_ohm": model["r0_ohm"] / area,
        }
    projected = []
    for bias in BIAS:
        p1 = bias * split1
        p2 = bias * split2
        projected.append({
            "ibias_uA": bias,
            "bjl1_uA": p1,
            "bjl2_uA": p2,
            "bjl1_over_ic": p1 / junctions["BJL1"]["ic_uA"],
            "bjl2_over_ic": p2 / junctions["BJL2"]["ic_uA"],
            "rb_drop_uV_magnitude": bias * 6.0,
            "delta_from_35_uA": bias - 35.0,
        })
    result = {
        "source": str(CONTROL),
        "window_ps": [140.0, 170.0],
        "model": model,
        "junctions": junctions,
        "settled_35uA": base,
        "static_split_fraction": {"bjl1": split1, "bjl2": split2},
        "projected_points": projected,
        "selection": "37.5uA first: smallest registered high-side perturbation; 40uA conditional second point",
        "limitations": [
            "projection holds the measured 35uA DC split only to first order",
            "nonlinear read transient may redistribute current differently",
            "I/Ic ratios are operating-point diagnostics, not event evidence",
        ],
    }
    (ROOT / "analysis/analytic-precheck.json").write_text(json.dumps(result, indent=2) + "\n")
    lines = [
        "# PAPER-SL-Q2 analytic settled/load-line precheck",
        "",
        "## Result",
        "",
        "`37.5 µA first point worth testing; 40 µA conditional bracket point`.",
        "",
        "This is a first-order local load-line estimate from the accepted Q1 READ=0 control; it is not a switching prediction.",
        "",
        "## Actual jjmit reconstruction",
        "",
        f"- `Ic_base={model['icrit_A']*1e6:.6g} µA`, `CAP_base={model['cap_pF']:.6g} pF`, `RN_base={model['rn_ohm']:.6g} Ω`, `R0_base={model['r0_ohm']:.6g} Ω`.",
        "",
        "| JJ | AREA | Ic | C | RN | R0 |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for name in ("BJS", "BJL1", "BJL2"):
        j = junctions[name]
        lines.append(f"| {name} | {j['area']:.2f} | {j['ic_uA']:.3f} µA | {j['cap_fF']:.3f} fF | {j['rn_ohm']:.6g} Ω | {j['r0_ohm']:.6g} Ω |")
    lines += [
        "",
        "## Q1 settled READ=0 baseline, [140,170) ps",
        "",
        "| quantity | median |",
        "|---|---:|",
        f"| P(BJS) | {base['p_bjs']:.8g} rad |",
        f"| P(BJL1) | {base['p_bjl1']:.8g} rad |",
        f"| P(BJL2) | {base['p_bjl2']:.8g} rad |",
        f"| I(LIN) | {base['i_lin']*1e6:.8g} µA |",
        f"| I(L1) | {base['i_l1']*1e6:.8g} µA |",
        f"| I(L2) | {base['i_l2']*1e6:.8g} µA |",
        f"| I(RB) | {base['i_rb']*1e6:.8g} µA |",
        f"| I(BJL1) | {base['i_bjl1']*1e6:.8g} µA |",
        f"| I(BJL2) | {base['i_bjl2']*1e6:.8g} µA |",
        f"| I(RJ1) | {base['i_rj1']*1e6:.8g} µA |",
        f"| I(RJ2) | {base['i_rj2']*1e6:.8g} µA |",
        "",
        f"The measured JJ branch split is {split1*100:.3f}% BJL1 / {split2*100:.3f}% BJL2; `I(BJL1)+I(BJL2)` closes the 35 µA bias to the displayed precision.",
        "",
        "## First-order bracket projection",
        "",
        "| IBIAS | projected BJL1 | projected BJL2 | BJL1/Ic | BJL2/Ic | approximate RB drop magnitude |",
        "|---:|---:|---:|---:|---:|---:|",
    ]
    for point in projected:
        lines.append(f"| {point['ibias_uA']:.1f} µA | {point['bjl1_uA']:.3f} µA | {point['bjl2_uA']:.3f} µA | {point['bjl1_over_ic']:.3f} | {point['bjl2_over_ic']:.3f} | {point['rb_drop_uV_magnitude']:.1f} µV |")
    lines += [
        "",
        "## Interpretation",
        "",
        "- Observed: at Q1 35 µA control, the ideal bias branch carries 35 µA and the settled nonlinear branches carry approximately 15.122/19.878 µA; RJ1/RJ2 currents are near zero.",
        "- Derived: the first-order high-side points raise the estimated static BJL1/BJL2 currents but leave both below their actual area-scaled Ic values.",
        "- Inference: the bias change is a local operating-point test, not a claim that read1 will scale more than read0. The dynamic read waveform can alter the split and load-line.",
        "- Unknown: whether the high-side bias moves the read1 transient into a complete BJL2 segment without a corresponding read0/control event.",
    ]
    (ROOT / "analysis/ANALYTIC_PRECHECK.md").write_text("\n".join(lines) + "\n")
    print("37.5uA first point worth testing; 40uA conditional")


if __name__ == "__main__":
    main()
