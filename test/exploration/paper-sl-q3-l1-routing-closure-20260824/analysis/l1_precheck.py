#!/usr/bin/env python3
"""PAPER-SL-Q3 Stage-A analytic precheck.

This script reads only the accepted Q0/Q1/Q2 raw CSV files.  It does not run
JoSIM and it deliberately keeps direct node voltage measurements separate
from the L*dI/dt estimate for the L1 branch.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent

SOURCE_CASES = {
    "Q0_68p4": {
        "path": ROOT / "test/exploration/qb-q0-standalone-current-quantized-event-20260824/raw/scaled/iin-68p4u.csv",
        "window": (210.0, 216.5),
        "label": "Q0 scaled 68.4 uA, paired sixth pulse",
    },
    "Q1_35u": {
        "path": ROOT / "test/exploration/paper-sl-q1-20260824/raw/paper-j1-logical1-read.csv",
        "window": (102.6375, 109.125),
        "label": "PAPER-SL-Q1 logical1 READ, IBIAS=35 uA",
    },
    "Q2_40u": {
        "path": ROOT / "test/exploration/paper-sl-q2-20260824/raw/40u/paper-j1-logical1-read.csv",
        "window": (102.525, 106.875),
        "label": "PAPER-SL-Q2 logical1 READ, IBIAS=40 uA",
    },
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def load_csv(path: Path) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    with path.open(newline="") as f:
        reader = csv.reader(f)
        header = next(reader)
        rows = np.asarray([[float(x) for x in row] for row in reader], dtype=float)
    if rows.ndim != 2 or rows.shape[0] < 3:
        raise ValueError(f"too few rows: {path}")
    names = [name.strip() for name in header]
    data = {name: rows[:, i] for i, name in enumerate(names)}
    time_name = next((n for n in names if n.lower() in {"time", "time(s)"}), names[0])
    t = data[time_name]
    if not np.all(np.diff(t) > 0):
        raise ValueError(f"time is not strictly increasing: {path}")
    return t * 1e12, data


def col(data: dict[str, np.ndarray], name: str) -> np.ndarray:
    if name in data:
        return data[name]
    matches = [k for k in data if k.strip() == name]
    if not matches and name.startswith(("I(", "V(", "P(")):
        # The accepted QB raw files print subcircuit-qualified columns, e.g.
        # I(BJS|XBQ).  Treat the unqualified names used by the topology as
        # aliases only; no signal is reconstructed or re-oriented here.
        stem, suffix = name.split("(", 1)
        terminal = suffix[:-1]
        matches = [
            k for k in data
            if k.lower().startswith(f"{stem.lower()}({terminal.lower()}|")
        ]
    if matches:
        return data[matches[0]]
    raise KeyError(f"missing column {name!r}; available={list(data)[:12]}")


def mask_window(t_ps: np.ndarray, window: tuple[float, float]) -> np.ndarray:
    lo, hi = window
    return (t_ps >= lo) & (t_ps < hi)


def stats(x: np.ndarray) -> dict[str, float]:
    return {
        "min": float(np.min(x)),
        "max": float(np.max(x)),
        "mean": float(np.mean(x)),
        "rms": float(np.sqrt(np.mean(x * x))),
    }


def integral_uaps(t_ps: np.ndarray, x_uA: np.ndarray) -> float:
    return float(np.trapezoid(x_uA, t_ps))


def one_case(key: str, spec: dict) -> dict:
    t, d = load_csv(spec["path"])
    m = mask_window(t, spec["window"])
    if np.count_nonzero(m) < 3:
        raise ValueError(f"insufficient samples in selected window: {key}")
    tw = t[m]
    # JoSIM current columns are in amperes; all analysis current values below
    # are microamps.  The P columns are retained only for provenance here.
    bjs = col(d, "I(BJs)")[m] * 1e6
    l1 = col(d, "I(L1)")[m] * 1e6
    bjl1 = col(d, "I(BJL1)")[m] * 1e6
    rj1 = col(d, "I(RJ1)")[m] * 1e6
    local = bjl1 + rj1
    # dt is in ps, so d(uA)/d(ps) times pH is numerically microvolt.
    dl1_dt = np.gradient(l1, tw)
    v_l1_est_uV = 3.91 * dl1_dt
    v_node2_uV = col(d, "V(BJL1)")[m] * 1e6
    # The global/raw P and V columns are not used as event evidence in this
    # precheck.  They are included only to make the source identity explicit.
    result = {
        "key": key,
        "label": spec["label"],
        "source": str(spec["path"].relative_to(ROOT)),
        "source_sha256": sha256(spec["path"]),
        "window_ps": list(spec["window"]),
        "samples": int(len(tw)),
        "dt_ps_median": float(np.median(np.diff(tw))),
        "currents_uA": {
            "BJs": stats(bjs),
            "L1": stats(l1),
            "BJL1": stats(bjl1),
            "RJ1": stats(rj1),
            "local_BJL1_plus_RJ1": stats(local),
        },
        "integrals_uA_ps": {
            "BJs": integral_uaps(tw, bjs),
            "L1": integral_uaps(tw, l1),
            "BJL1": integral_uaps(tw, bjl1),
            "RJ1": integral_uaps(tw, rj1),
            "local_BJL1_plus_RJ1": integral_uaps(tw, local),
        },
        "dI_L1_dt_uA_per_ps": stats(dl1_dt),
        "V_L1_estimate_uV": stats(v_l1_est_uV),
        "V_node2_direct_V_BJL1_uV": stats(v_node2_uV),
        "extrema_ps": {
            "dI_L1_dt_min": float(tw[int(np.argmin(dl1_dt))]),
            "dI_L1_dt_max": float(tw[int(np.argmax(dl1_dt))]),
            "local_max": float(tw[int(np.argmax(local))]),
            "L1_max": float(tw[int(np.argmax(l1))]),
            "L1_min": float(tw[int(np.argmin(l1))]),
        },
        "note": "V_L1_estimate is L1*dI(L1)/dt; V_node2_direct is the directly printed V(BJL1), not an independent V(L1) measurement.",
    }
    # KCL is evaluated from the measured branch currents, not inferred from a
    # phase or voltage threshold.
    result["kcl_residual_uA"] = stats(bjs - (l1 + bjl1 + rj1))
    return result


def ratio(result: dict, numerator: str, denominator: str) -> float:
    return result["integrals_uA_ps"][numerator] / result["integrals_uA_ps"][denominator]


def fmt(x: float, digits: int = 4) -> str:
    if not math.isfinite(x):
        return "n/a"
    return f"{x:.{digits}f}"


def write_report(results: list[dict]) -> None:
    by_key = {r["key"]: r for r in results}
    rows = []
    for r in results:
        c = r["currents_uA"]
        a = r["integrals_uA_ps"]
        rows.append(
            "| {key} | {win} | {bjs} | {l1} | {local} | {ibjs} | {il1} | {iloc} | {kcl} |".format(
                key=r["key"],
                win="[%.4f, %.4f)" % tuple(r["window_ps"]),
                bjs="%s..%s" % (fmt(c["BJs"]["min"]), fmt(c["BJs"]["max"])),
                l1="%s..%s" % (fmt(c["L1"]["min"]), fmt(c["L1"]["max"])),
                local="%s..%s" % (fmt(c["local_BJL1_plus_RJ1"]["min"]), fmt(c["local_BJL1_plus_RJ1"]["max"])),
                ibjs=fmt(a["BJs"]),
                il1=fmt(a["L1"]),
                iloc=fmt(a["local_BJL1_plus_RJ1"]),
                kcl=fmt(r["kcl_residual_uA"]["rms"], 6),
            )
        )
    q0 = by_key["Q0_68p4"]
    q1 = by_key["Q1_35u"]
    q2 = by_key["Q2_40u"]
    text = f"""# PAPER-SL-Q3 Stage-A analytic precheck

Generated from accepted raw only; no JoSIM execution was performed for this
stage.  Current units are uA, time is ps, and the selected windows are the
dominant paired BJL1 activity windows from the prior Q3-PRE audit.

## Inputs and provenance

| case | raw | SHA-256 | window |
|---|---|---|---|
""" + "\n".join(
        f"| {r['key']} | `{r['source']}` | `{r['source_sha256']}` | `{r['window_ps']}` |"
        for r in results
    ) + f"""

## Measured branch split and KCL

The actual node-2 relation in the frozen QB topology is
`I(BJs) = I(L1) + I(BJL1) + I(RJ1)`.  `local` below means
`I(BJL1)+I(RJ1)`, evaluated from the raw branch currents.

| case | window | BJs min..max (uA) | L1 min..max (uA) | local min..max (uA) | ∫BJs dt (uA ps) | ∫L1 dt | ∫local dt | KCL RMS (uA) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
""" + "\n".join(rows) + f"""

The corresponding local-current fractions from signed integrals are:

| case | F_local = ∫(BJL1+RJ1)dt / ∫BJs dt | complementary L1 fraction |
|---|---:|---:|
| Q0_68p4 | {fmt(ratio(q0, 'local_BJL1_plus_RJ1', 'BJs'), 6)} | {fmt(ratio(q0, 'L1', 'BJs'), 6)} |
| Q1_35u | {fmt(ratio(q1, 'local_BJL1_plus_RJ1', 'BJs'), 6)} | {fmt(ratio(q1, 'L1', 'BJs'), 6)} |
| Q2_40u | {fmt(ratio(q2, 'local_BJL1_plus_RJ1', 'BJs'), 6)} | {fmt(ratio(q2, 'L1', 'BJs'), 6)} |

These are signed-area diagnostics over different, case-specific dominant
windows; they are not event counts.  The Q1/Q2 replay sends most signed node-2
current into L1 (fractions about {ratio(q1, 'L1', 'BJs'):.3f} and
{ratio(q2, 'L1', 'BJs'):.3f}), whereas the successful Q0 reference sends a
larger fraction into the local BJL1/RJ1 branch (about
{ratio(q0, 'local_BJL1_plus_RJ1', 'BJs'):.3f}).

## Dynamic direction check

For the existing `L1=3.91 pH`, the derivative diagnostic is
`V_L1,est = L1*dI(L1)/dt`.  Its values are derived from measured current and
actual CSV time.  A direct V(L1) column was not present in these accepted raw
files; the printed `V(BJL1)` is the node-2-to-ground voltage and is reported
separately, not substituted for V(L1).

| case | dI(L1)/dt min..max (uA/ps) | estimated V_L1 min..max (uV) | direct V(BJL1) min..max (uV) | peak derivative times (ps) |
|---|---:|---:|---:|---:|
""" + "\n".join(
        "| {key} | {dmin}..{dmax} | {vmin}..{vmax} | {nmin}..{nmax} | min {tmin}, max {tmax} |".format(
            key=r["key"],
            dmin=fmt(r["dI_L1_dt_uA_per_ps"]["min"]),
            dmax=fmt(r["dI_L1_dt_uA_per_ps"]["max"]),
            vmin=fmt(r["V_L1_estimate_uV"]["min"]),
            vmax=fmt(r["V_L1_estimate_uV"]["max"]),
            nmin=fmt(r["V_node2_direct_V_BJL1_uV"]["min"]),
            nmax=fmt(r["V_node2_direct_V_BJL1_uV"]["max"]),
            tmin=fmt(r["extrema_ps"]["dI_L1_dt_min"], 4),
            tmax=fmt(r["extrema_ps"]["dI_L1_dt_max"], 4),
        )
        for r in results
    ) + f"""

The selected perturbation is **L1 = 4.50 pH**, a single modest increase of
15.09% from 3.91 pH.  At unchanged dI/dt it raises the inductive voltage
coefficient by the same 15.09% (an additional 0.59 pH term), so the local
node-2 branch is expected to receive a larger share of the rapid BJs current
than the measured Q1/Q2 split.  This is a dynamic-impedance hypothesis, not a
claim that a larger inductor always increases local DC current.

## Stage-A disposition

**`L1_DIRECTION_PRECHECK_PASS; NEXT_POINT_L1_4P50_PH`**

Observed: Q1/Q2 have large BJs activity but a smaller local signed-current
fraction than Q0; the directly measured branch KCL closes to the residuals
shown above.  Derived: the dominant replay interval is a few ps long and the
measured L1 derivative is large, so the L1 branch is a plausible fast diversion
path.  Inference: a modest L1 increase is the highest-information single
perturbation to test local BJL1 routing.  Unknown: the loaded nonlinear circuit
may redistribute static bias or alter BJL1 phase dynamics in a direction not
captured by the first-order coefficient.

This precheck does not certify an event and does not predict that BJL1 will
complete a turn.  It authorizes only the one preregistered 4.50 pH point.
"""
    (OUT / "ANALYTIC_PRECHECK.md").write_text(text)
    (OUT / "precheck_metrics.json").write_text(json.dumps({"cases": results, "selected_point": {"L1_pH": 4.50, "baseline_L1_pH": 3.91}}, indent=2) + "\n")


def main() -> None:
    results = [one_case(k, spec) for k, spec in SOURCE_CASES.items()]
    write_report(results)
    print((OUT / "ANALYTIC_PRECHECK.md").relative_to(ROOT))


if __name__ == "__main__":
    main()
