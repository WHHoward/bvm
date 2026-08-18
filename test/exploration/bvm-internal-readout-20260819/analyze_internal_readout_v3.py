#!/usr/bin/env python3
"""analyze_internal_readout_v3.py -- rev3 analysis driver.

Explicitly analyzes the corrected-negative runs and READ=0 controls,
reusing the rev2 joint unwrapped-phase + same-junction-voltage
segmentation.  Generates machine-readable analysis-v3.json.

Run set:
  JS/phase dynamics: pos-read-single, pos-read-repeated,
    neg-read-single-corr, neg-read-repeated-corr,
    pos-control, neg-control
  Storage signatures: pos-diag, neg-diag-corr
Superseded (not analyzed here): neg-read-single, neg-read-repeated,
  neg-diag (ramp-init artifacts, kept append-only).
"""

import importlib.util
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent

# rev2 methodology reused verbatim (single source of truth)
_v2 = importlib.util.spec_from_file_location(
    "analyze_internal_readout_v2", ROOT / "analyze_internal_readout_v2.py")
v2 = importlib.util.module_from_spec(_v2)
_v2.loader.exec_module(v2)

PHASE_RUNS = ["pos-read-single", "pos-read-repeated",
              "neg-read-single-corr", "neg-read-repeated-corr",
              "pos-control", "neg-control"]
STORAGE_RUNS = ["pos-diag", "neg-diag-corr"]


def main() -> int:
    results = {}
    for run in PHASE_RUNS:
        hdr, ts, cols = v2.load(v2.RAW / run / "run-01.csv")
        r = {"run": run}
        for wname, (lo, hi) in (("READ1", v2.READ1), ("READ2", v2.READ2)):
            r[wname] = v2.window_metrics(ts, cols, lo, hi)
        results[run] = r
    for run in STORAGE_RUNS:
        hdr, ts, cols = v2.load(v2.RAW / run / "run-01.csv")
        r = {"run": run}
        for sname, (lo, hi) in (("PRE", v2.PRE), ("POST1", v2.POST1),
                                ("POST2", v2.POST2)):
            r[f"storage_{sname}"] = v2.storage_signature(ts, cols, lo, hi)
        results[run] = r
    out = ROOT / "analysis-v3.json"
    out.write_text(json.dumps(results, indent=2, ensure_ascii=False))
    print(f"wrote {out}")
    for run in PHASE_RUNS:
        r = results[run]
        parts = []
        for wname in ("READ1", "READ2"):
            for jj in ("P(B_JS1|XBVM1)", "P(B_JS2|XBVM1)"):
                parts.append(f"{wname} {jj.split('|')[0]}="
                             f"{r[wname][f'{jj}_classification']}")
        print(f"{run}: {' | '.join(parts)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
