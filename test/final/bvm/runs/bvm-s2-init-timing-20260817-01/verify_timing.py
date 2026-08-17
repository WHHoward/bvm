#!/usr/bin/env python3
"""verify_timing.py -- independent verifier for bvm-s2-init-timing-20260817-01.

Reads ONLY raw CSVs + frozen preregistration; recomputes every p2p,
readiness, contrast, and disposition; compares against analysis.json.
Decimal-exact timestamps; no interpolation/resampling/alignment.
"""
import csv
import json
import pathlib
import sys
from decimal import Decimal

RUN = pathlib.Path(__file__).resolve().parent
RAW = RUN / "raw"
WINDOWS_PS = {"settling_early": (Decimal("30"), Decimal("40")),
              "settling_mid": (Decimal("50"), Decimal("60")),
              "settling_late": (Decimal("70"), Decimal("80")),
              "readiness": (Decimal("80"), Decimal("90"))}
THRESHOLD_RAD = Decimal("0.020")
CASES = ["A-positive", "B-positive", "A-negative", "B-negative"]


def load(path: pathlib.Path) -> tuple[list[Decimal], dict]:
    rows = list(csv.reader(open(path, encoding="utf-8")))
    hdr = [h.strip().strip('"') for h in rows[0]]
    times = [Decimal(r[0]) for r in rows[1:]]
    cols = {h: [Decimal(r[j]) for r in rows[1:]]
            for j, h in enumerate(hdr[1:], start=1)}
    return times, cols


def p2p(times, vals, lo_ps, hi_ps):
    lo = lo_ps * Decimal("1e-12")
    hi = hi_ps * Decimal("1e-12")
    sel = [v for t, v in zip(times, vals) if lo <= t < hi]
    if not sel:
        raise ValueError("empty window coverage")
    return max(sel) - min(sel)


def main() -> int:
    analysis = json.loads((RUN / "analysis.json").read_text())
    recomputed = {"runs": [], "contrasts": {}, "disposition": ""}
    runs = []
    for case in CASES:
        times, cols = load(RAW / case / "run-01.csv")
        entry = {"id": case, "windows": {}, "readiness": {}}
        for wname, (lo, hi) in WINDOWS_PS.items():
            jm1 = p2p(times, cols["P(B_JM1|XBVM1)"], lo, hi)
            jm2 = p2p(times, cols["P(B_JM2|XBVM1)"], lo, hi)
            entry["windows"][wname] = {"jm1_p2p_rad": str(jm1),
                                       "jm2_p2p_rad": str(jm2)}
            if wname == "readiness":
                entry["readiness"] = {
                    "jm1_ready": jm1 <= THRESHOLD_RAD,
                    "jm2_ready": jm2 <= THRESHOLD_RAD,
                    "co_primary_ready": jm1 <= THRESHOLD_RAD
                    and jm2 <= THRESHOLD_RAD}
        runs.append(entry)
    recomputed["runs"] = runs
    by_pol = {"positive": {}, "negative": {}}
    for e in runs:
        pol = "positive" if "positive" in e["id"] else "negative"
        timing = "S2_REGISTERED" if e["id"].startswith("A") else "S1_REGISTERED"
        by_pol[pol][timing] = e
    for pol in ("positive", "negative"):
        a, b = by_pol[pol]["S2_REGISTERED"], by_pol[pol]["S1_REGISTERED"]
        d2 = (Decimal(b["windows"]["readiness"]["jm2_p2p_rad"])
              - Decimal(a["windows"]["readiness"]["jm2_p2p_rad"]))
        d1 = (Decimal(b["windows"]["readiness"]["jm1_p2p_rad"])
              - Decimal(a["windows"]["readiness"]["jm1_p2p_rad"]))
        recomputed["contrasts"][pol] = {
            "delta_jm2_readiness_p2p_rad": str(d2),
            "delta_jm1_readiness_p2p_rad": str(d1),
            "abs_delta_jm2_ge_threshold": abs(d2) >= THRESHOLD_RAD,
            "readiness_classification_changed": (
                a["readiness"]["co_primary_ready"]
                != b["readiness"]["co_primary_ready"])}
    pos, neg = recomputed["contrasts"]["positive"], recomputed["contrasts"]["negative"]
    ps = pos["abs_delta_jm2_ge_threshold"] or pos["readiness_classification_changed"]
    ns = neg["abs_delta_jm2_ge_threshold"] or neg["readiness_classification_changed"]
    same = (Decimal(pos["delta_jm2_readiness_p2p_rad"])
            * Decimal(neg["delta_jm2_readiness_p2p_rad"])) > 0
    if ps and ns and same:
        recomputed["disposition"] = "CONSISTENT_TIMING_SENSITIVITY_SUPPORTED"
    elif ps != ns:
        recomputed["disposition"] = "POLARITY_CONTINGENT_TIMING_SENSITIVITY"
    elif not ps and not ns:
        recomputed["disposition"] = "NO_REGISTERED_TIMING_SENSITIVITY_OBSERVED"
    else:
        recomputed["disposition"] = "INCONCLUSIVE"

    fails = []
    for e in recomputed["runs"]:
        want = next(x for x in analysis["runs"] if x["id"] == e["id"])
        for wname in WINDOWS_PS:
            for k in ("jm1_p2p_rad", "jm2_p2p_rad"):
                if e["windows"][wname][k] != want["windows"][wname][k]:
                    fails.append(f"{e['id']} {wname} {k} mismatch")
        if e["readiness"] != want["readiness"]:
            fails.append(f"{e['id']} readiness mismatch")
    for pol in ("positive", "negative"):
        if recomputed["contrasts"][pol] != analysis["contrasts"][pol]:
            fails.append(f"{pol} contrast mismatch")
    if recomputed["disposition"] != analysis["disposition"]:
        fails.append("disposition mismatch")
    if fails:
        print("VERIFY FAIL:")
        for f in fails:
            print(f"  - {f}")
        return 1
    print(f"VERIFY PASS: {len(CASES)} runs, 4 windows x 2 junctions, "
          f"2 contrasts, disposition "
          f"{recomputed['disposition']} recomputed from raw+spec")
    return 0


if __name__ == "__main__":
    sys.exit(main())
