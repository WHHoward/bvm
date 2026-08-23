#!/usr/bin/env python3
"""R15-C waveform-level pre-switch J_SET prediction from R15-B I(L_TX) raw."""

import argparse
import csv
import json
import math
from pathlib import Path


L_SUM = 55e-12
R_BIAS = 27.5
M = -2.529822e-12
I_BASE = 5.6e-6
IC_SET = 8.0e-6
WINDOW_START = 94e-12
WINDOW_END = 130e-12


def read_trace(path):
    with path.open(newline="") as handle:
        rows = csv.DictReader(handle)
        names = rows.fieldnames or []
        t_name = "time"
        tx_name = next(name for name in names if name.startswith("I(L_TX|"))
        t = []
        tx = []
        for row in rows:
            t.append(float(row[t_name]))
            tx.append(float(row[tx_name]))
    if len(t) < 2 or any(b <= a for a, b in zip(t, t[1:])):
        raise ValueError(f"invalid time axis: {path}")
    return t, tx, tx_name


def solve(t, tx):
    delta = [0.0]
    rhs = []
    mdidt = []
    for i, (ta, tb) in enumerate(zip(t, t[1:])):
        dt = tb - ta
        slope = (tx[i + 1] - tx[i]) / dt
        md = M * slope
        forcing = -md
        decay = math.exp(-R_BIAS * dt / L_SUM)
        delta_next = delta[-1] * decay + (forcing / R_BIAS) * (1.0 - decay)
        delta.append(delta_next)
        mdidt.append(md)
        rhs.append(forcing)
    mdidt.append(mdidt[-1])
    rhs.append(rhs[-1])
    return delta, mdidt, rhs


def stats(values, times):
    index_max = max(range(len(values)), key=values.__getitem__)
    index_min = min(range(len(values)), key=values.__getitem__)
    peak_abs_index = max(range(len(values)), key=lambda i: abs(values[i]))
    return {
        "max_A": values[index_max],
        "max_time_ps": times[index_max] * 1e12,
        "min_A": values[index_min],
        "min_time_ps": times[index_min] * 1e12,
        "peak_abs_A": values[peak_abs_index],
        "peak_abs_time_ps": times[peak_abs_index] * 1e12,
        "rms_A": math.sqrt(sum(x * x for x in values) / len(values)),
        "p2p_A": max(values) - min(values),
    }


def one_case(path):
    t, tx, tx_name = read_trace(path)
    delta, mdidt, forcing = solve(t, tx)
    mask = [WINDOW_START <= x < WINDOW_END for x in t]
    window_times = [x for x, keep in zip(t, mask) if keep]
    window_delta = [x for x, keep in zip(delta, mask) if keep]
    window_mdidt = [x for x, keep in zip(mdidt, mask) if keep]
    window_forcing = [x for x, keep in zip(forcing, mask) if keep]
    predicted = [I_BASE + x for x in delta]
    window_predicted = [I_BASE + x for x in window_delta]
    return {
        "source": str(path),
        "tx_column": tx_name,
        "sample_count": len(t),
        "time_start_ps": t[0] * 1e12,
        "time_end_ps": t[-1] * 1e12,
        "window_ps": [94.0, 130.0],
        "M_dI_TX_dt": stats(window_mdidt, window_times),
        "forcing_minus_M_dI_TX_dt": stats(window_forcing, window_times),
        "delta_I_JSET": stats(window_delta, window_times),
        "predicted_I_JSET": stats(window_predicted, window_times),
        "baseline_I_JSET_uA": I_BASE * 1e6,
        "Ic_BSET_uA": IC_SET * 1e6,
        "delta_over_Ic": max(abs(x) for x in window_delta) / IC_SET,
        "waveform": {
            "time_s": t,
            "I_TX_A": tx,
            "delta_I_JSET_A": delta,
            "I_JSET_A": predicted,
            "M_dI_TX_dt_V": mdidt,
            "forcing_V": forcing,
        },
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--r15b-root", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    cases = [
        "logical1-read",
        "logical0-read",
        "logical1-read0-control",
        "logical0-read0-control",
    ]
    results = {}
    for case in cases:
        results[case] = one_case(args.r15b_root / "raw" / f"{case}.csv")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    compact = {case: {k: v for k, v in result.items() if k != "waveform"}
               for case, result in results.items()}
    (args.out_dir / "r15c-analytic-precheck.json").write_text(
        json.dumps(compact, indent=2, sort_keys=True) + "\n"
    )

    with (args.out_dir / "r15c-analytic-precheck.csv").open("w", newline="") as handle:
        fields = [
            "case", "delta_min_uA", "delta_max_uA", "delta_p2p_uA", "delta_rms_uA",
            "I_JSET_min_uA", "I_JSET_max_uA", "forcing_min_mV", "forcing_max_mV",
            "forcing_peak_signed_mV", "forcing_peak_time_ps",
            "delta_peak_signed_uA", "delta_peak_time_ps", "delta_peak_lag_ps",
        ]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for case, result in results.items():
            d = result["delta_I_JSET"]
            p = result["predicted_I_JSET"]
            f = result["forcing_minus_M_dI_TX_dt"]
            writer.writerow({
                "case": case,
                "delta_min_uA": d["min_A"] * 1e6,
                "delta_max_uA": d["max_A"] * 1e6,
                "delta_p2p_uA": d["p2p_A"] * 1e6,
                "delta_rms_uA": d["rms_A"] * 1e6,
                "I_JSET_min_uA": p["min_A"] * 1e6,
                "I_JSET_max_uA": p["max_A"] * 1e6,
                "forcing_min_mV": f["min_A"] * 1e3,
                "forcing_max_mV": f["max_A"] * 1e3,
                "forcing_peak_signed_mV": f["peak_abs_A"] * 1e3,
                "forcing_peak_time_ps": f["peak_abs_time_ps"],
                "delta_peak_signed_uA": d["peak_abs_A"] * 1e6,
                "delta_peak_time_ps": d["peak_abs_time_ps"],
                "delta_peak_lag_ps": d["peak_abs_time_ps"] - f["peak_abs_time_ps"],
            })

    lines = [
        "# R15-C analytic precheck results",
        "",
        "Input: R15-B saved `I(L_TX)` raw; no JoSIM run was used for this precheck.",
        "",
        "Equation: `55 pH*d(delta_I)/dt + 27.5 ohm*delta_I = -M*dI_TX/dt`, "
        "with `M=-2.529822 pH` and baseline `I_JSET=5.6 uA`.",
        "",
        "| case | delta I min (uA) | delta I max (uA) | I_JSET min (uA) | I_JSET max (uA) | forcing min (mV) | forcing max (mV) |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for case, result in results.items():
        d = result["delta_I_JSET"]
        p = result["predicted_I_JSET"]
        f = result["forcing_minus_M_dI_TX_dt"]
        lines.append(
            f"| {case} | {d['min_A']*1e6:.6f} | {d['max_A']*1e6:.6f} | "
            f"{p['min_A']*1e6:.6f} | {p['max_A']*1e6:.6f} | "
            f"{f['min_A']*1e3:.6f} | {f['max_A']*1e3:.6f} |"
        )
    lines += [
        "",
        "## Polarity and timing",
        "",
        "The forcing column is the signed RHS `-M*dI_TX/dt`; the response is the signed `delta_I_JSET`. A positive lag means the finite `LΣ/R_BIAS` network reaches its largest absolute current excursion after the forcing peak.",
        "",
        "| case | forcing peak signed (mV) @ ps | delta peak signed (uA) @ ps | response lag (ps) |",
        "|---|---:|---:|---:|",
    ]
    for case, result in results.items():
        d = result["delta_I_JSET"]
        f = result["forcing_minus_M_dI_TX_dt"]
        lines.append(
            f"| {case} | {f['peak_abs_A']*1e3:+.6f} @ {f['peak_abs_time_ps']:.4f} | "
            f"{d['peak_abs_A']*1e6:+.6f} @ {d['peak_abs_time_ps']:.4f} | "
            f"{d['peak_abs_time_ps']-f['peak_abs_time_ps']:+.4f} |"
        )
    read1_p2p = results["logical1-read"]["delta_I_JSET"]["p2p_A"] * 1e6
    read0_p2p = results["logical0-read"]["delta_I_JSET"]["p2p_A"] * 1e6
    control_p2p = max(
        results[name]["delta_I_JSET"]["p2p_A"] * 1e6
        for name in ("logical1-read0-control", "logical0-read0-control")
    )
    lines += [
        "",
        f"In the analytic window, read1/read0 modulation p2p is `{read1_p2p/read0_p2p:.3f}x`; the largest READ=0 control p2p is `{control_p2p:.6g} uA`. The sign follows the mutual polarity through the `-M*dI_TX/dt` forcing, with the expected finite-network lag.",
        "",
        "The predicted current is a linear pre-switch estimate only; it is not event evidence and is not a substitute for JoSIM phase/area analysis.",
        "",
    ]
    (args.out_dir / "R15C_ANALYTIC_PRECHECK.md").write_text("\n".join(lines))


if __name__ == "__main__":
    main()
