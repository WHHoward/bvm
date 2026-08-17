#!/usr/bin/env python3
"""analyze_timing.py -- BVM S2 init-timing structured analysis (frozen).

Decimal-exact half-open windows over raw CSV literal timestamps; computes
JM1/JM2 phase p2p per registered window, readiness classification
(<=0.020 rad) separately by polarity, contrasts, and disposition per
preregistration.yaml (bvm-s2-timing-preregistration-v1).
"""
import csv
import json
import pathlib
from decimal import Decimal

RUN = pathlib.Path(__file__).resolve().parent
RAW = RUN / "raw"
WINDOWS = {"settling_early": [Decimal("30e-12"), Decimal("40e-12")],
           "settling_mid": [Decimal("50e-12"), Decimal("60e-12")],
           "settling_late": [Decimal("70e-12"), Decimal("80e-12")],
           "readiness": [Decimal("80e-12"), Decimal("90e-12")]}
THRESHOLD = Decimal("0.020")
CASES = ["A-positive", "B-positive", "A-negative", "B-negative"]


def load_csv(path: pathlib.Path) -> tuple[list[Decimal], dict]:
    rows = list(csv.reader(open(path, encoding="utf-8")))
    hdr = [h.strip().strip('"') for h in rows[0]]
    times = [Decimal(r[0]) for r in rows[1:]]
    cols = {h: [Decimal(r[j]) for r in rows[1:]] for j, h in enumerate(hdr[1:], start=1)}
    return times, cols


def p2p_window(times, values, lo: Decimal, hi: Decimal) -> Decimal:
    sel = [v for t, v in zip(times, values) if lo <= t < hi]
    if not sel:
        return Decimal("NaN")
    return max(sel) - min(sel)


def main() -> None:
    result = {"schema_version": "bvm-s2-timing-analysis-v1",
              "run_id": "bvm-s2-init-timing-20260817-01",
              "metric_spec": {"readiness_threshold_rad": "0.020",
                              "p2p_window_semantics": "half_open_actual_csv_time",
                              "timestamp": "Decimal_from_literal_CSV_token"},
              "provenance": {"binary": "build/josim-cli",
                             "version": "v2.7.2837d13",
                             "timestep_ps": "0.0125", "tstop_ps": "92.0"},
              "windows": {"settling_early": [30.0, 40.0],
                          "settling_mid": [50.0, 60.0],
                          "settling_late": [70.0, 80.0],
                          "readiness": [80.0, 90.0]},
              "runs": [], "contrasts": {}, "disposition": "", "unknowns": []}
    runs_out = []
    for case in CASES:
        times, cols = load_csv(RAW / case / "run-01.csv")
        entry = {"id": case, "polarity": "positive" if "positive" in case else "negative",
                 "timing": "S2_REGISTERED" if case.startswith("A") else "S1_REGISTERED",
                 "windows": {}}
        for wname, (lo, hi) in WINDOWS.items():
            p2p_jm1 = p2p_window(times, cols["P(B_JM1|XBVM1)"], lo, hi)
            p2p_jm2 = p2p_window(times, cols["P(B_JM2|XBVM1)"], lo, hi)
            entry["windows"][wname] = {"jm1_p2p_rad": str(p2p_jm1),
                                       "jm2_p2p_rad": str(p2p_jm2)}
            if wname == "readiness":
                entry["readiness"] = {
                    "jm1_ready": str(p2p_jm1) <= str(THRESHOLD),
                    "jm2_ready": str(p2p_jm2) <= str(THRESHOLD),
                    "co_primary_ready": (str(p2p_jm1) <= str(THRESHOLD)
                                         and str(p2p_jm2) <= str(THRESHOLD))}
        runs_out.append(entry)
    result["runs"] = runs_out
    by_pol = {"positive": {}, "negative": {}}
    for e in runs_out:
        by_pol[e["polarity"]][e["timing"]] = e
    for pol in ("positive", "negative"):
        a = by_pol[pol]["S2_REGISTERED"]
        b = by_pol[pol]["S1_REGISTERED"]
        d_jm2 = Decimal(b["windows"]["readiness"]["jm2_p2p_rad"]) - \
                Decimal(a["windows"]["readiness"]["jm2_p2p_rad"])
        d_jm1 = Decimal(b["windows"]["readiness"]["jm1_p2p_rad"]) - \
                Decimal(a["windows"]["readiness"]["jm1_p2p_rad"])
        changed = (a["readiness"]["co_primary_ready"]
                   != b["readiness"]["co_primary_ready"])
        result["contrasts"][pol] = {
            "delta_jm2_readiness_p2p_rad": str(d_jm2),
            "delta_jm1_readiness_p2p_rad": str(d_jm1),
            "abs_delta_jm2_ge_threshold": str(abs(d_jm2)) >= str(THRESHOLD),
            "readiness_classification_changed": changed}
    pos = result["contrasts"]["positive"]
    neg = result["contrasts"]["negative"]
    pos_sig = pos["abs_delta_jm2_ge_threshold"] or pos["readiness_classification_changed"]
    neg_sig = neg["abs_delta_jm2_ge_threshold"] or neg["readiness_classification_changed"]
    same_sign = (Decimal(pos["delta_jm2_readiness_p2p_rad"]) *
                 Decimal(neg["delta_jm2_readiness_p2p_rad"])) > 0
    if pos_sig and neg_sig and same_sign:
        result["disposition"] = "CONSISTENT_TIMING_SENSITIVITY_SUPPORTED"
    elif pos_sig != neg_sig:
        result["disposition"] = "POLARITY_CONTINGENT_TIMING_SENSITIVITY"
    elif not pos_sig and not neg_sig:
        result["disposition"] = "NO_REGISTERED_TIMING_SENSITIVITY_OBSERVED"
    else:
        result["disposition"] = "INCONCLUSIVE"
    (RUN / "analysis.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8")
    print("analysis written:", result["disposition"])


if __name__ == "__main__":
    main()
