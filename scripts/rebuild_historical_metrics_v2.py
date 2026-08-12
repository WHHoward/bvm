#!/usr/bin/env python3
"""rebuild_historical_metrics_v2 -- M10 (JH-20260813-M10-003) historical
endpoint-arithmetic reconstruction.

Deterministic, stdlib-only. For every preregistered historical CSV and every
declared P(...) column it:
  1. verifies header, finite numeric values, strictly increasing actual time,
     and records the raw file SHA-256;
  2. selects the declared full-record provenance interval [0, run_end + dt)
     (first and last actual CSV samples; NOT a pre/post stability window);
  3. reports only endpoint_delta_rad = P_last - P_first and
     endpoint_delta_turns = endpoint_delta_rad / (2*pi), preserving sign and
     raw radians;
  4. where a named matched zero-input control is declared (P0 bump: bump_0),
     reports each run first and then signal-minus-control
     control_corrected_endpoint_delta, with the historical-regression
     limitation recorded.

It never reports activity clusters, events, SFQs, fluxoids, platform deltas,
voltage area, residuals, or convergence verdicts, and never modifies any
legacy raw CSV/JSON. Governing contract: METRIC_SPEC_V2 v2.0.0.

Usage:
    python3 scripts/rebuild_historical_metrics_v2.py [--out-root DIR]
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]

METRIC_SPEC_PATH = "docs/research/METRIC_SPEC_V2.md"
METRIC_SPEC_VERSION = "2.0.0"
METRIC_SPEC_SHA256 = "f88a36f4d310b2572efdc7408d734640f25dd5aea2246b74fbb8b7bb7f0be470"
PLAN_PATH = "research/tasks/JH-20260813-M10-001/design/reconstruction-plan.md"

# Fixed generation timestamp keeps the outputs byte-deterministic.
GENERATION_TIMESTAMP = "2026-08-13T03:15:00+08:00"

GENERATOR_VERSION = "1.0.0"

INVENTORY = {
    "baseline": {
        "out": "test/final/single_bvm_qb/data/metrics_v2/baseline-v2.json",
        "inputs": ["test/final/single_bvm_qb/data/test_bvm_bq_baseline.csv"],
        "phase_columns": ["P(B_JM1|XBVM1)", "P(B_JM2|XBVM1)", "P(BJS|XBQ)", "P(BJL1|XBQ)", "P(BJL2|XBQ)"],
        "control": None,
    },
    "p0": {
        "out": "test/final/interface/data/metrics_v2/p0-v2.json",
        "inputs": [f"test/final/interface/data/test_dcsfq_behavior_bump_{s}.csv"
                   for s in ("0", "1u4", "20u", "40u", "68u", "100u", "150u", "300u")]
                + [f"test/final/interface/data/test_dcsfq_behavior_sustained_{s}.csv"
                   for s in ("68u", "150u", "300u")],
        "phase_columns": ["P(B1|XDCSFQ)", "P(B2|XDCSFQ)", "P(B3|XDCSFQ)"],
        "control": "test/final/interface/data/test_dcsfq_behavior_bump_0.csv",
        "control_note": "bump_0 is the declared historical zero-input comparator for every nonzero bump file only",
    },
    "p2": {
        "out": "test/final/bvm/data/metrics_v2/p2-v2.json",
        "inputs": [f"test/final/bvm/data/test_bvm_multivortex{s}.csv" for s in ("", "_wl80", "_wl120")],
        "phase_columns": ["P(B_JM1|XBVM1)", "P(B_JM2|XBVM1)"],
        "control": None,
    },
    "bq_v4": {
        "out": "test/final/qb/data/metrics_v2/bq-v4-v2.json",
        "inputs": [f"test/final/qb/data/bq_v4_sweep{s}.csv" for s in ("70", "90", "110", "130", "150")]
                + ["test/final/qb/data/bq_v4_sfq.csv"],
        "phase_columns": ["P(BJS|XBQ)", "P(BJL1|XBQ)", "P(BJL2|XBQ)", "P(B1|XJTL)", "P(B2|XJTL)"],
        "control": None,
    },
}

LIMITATION_TEXT = (
    "full-record endpoint arithmetic on historical CSVs; not a pre/post "
    "platform result, not an activity/event/SFQ/fluxoid count, not a "
    "voltage-area cross-check, not a convergence verdict, and not a physical "
    "Gate or candidate conclusion. Missing controls/windows/mappings remain "
    "explicit NOT_APPLICABLE/INCONCLUSIVE."
)


def file_sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_csv(path: pathlib.Path, phase_columns: list[str]) -> dict:
    """Validate and read a historical CSV.

    Returns dict with header, times, per-column values, raw sha256, and the
    declared full-record interval [0, run_end + dt).
    Raises ValueError on any QA failure (missing column, non-finite,
    non-monotonic time, empty).
    """
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise ValueError(f"{path}: empty csv")
    header = list(rows[0].keys())
    missing = [c for c in phase_columns if c not in header]
    if missing:
        raise ValueError(f"{path}: missing declared phase columns {missing}")
    times: list[float] = []
    cols: dict[str, list[float]] = {c: [] for c in phase_columns}
    for i, r in enumerate(rows):
        try:
            t = float(r["time"])
        except (KeyError, TypeError, ValueError):
            raise ValueError(f"{path}: non-numeric time at row {i}")
        if not math.isfinite(t):
            raise ValueError(f"{path}: nonfinite time at row {i}")
        if i > 0 and t <= times[-1]:
            raise ValueError(f"{path}: time not strictly increasing at row {i}")
        times.append(t)
        for c in phase_columns:
            try:
                v = float(r[c])
            except (KeyError, TypeError, ValueError):
                raise ValueError(f"{path}: non-numeric {c} at row {i}")
            if not math.isfinite(v):
                raise ValueError(f"{path}: nonfinite {c} at row {i}")
            cols[c].append(v)
    n = len(times)
    dt = (times[-1] - times[0]) / (n - 1) if n > 1 else 0.0
    return {
        "path": str(path.relative_to(REPO_ROOT)),
        "sha256": file_sha256(path),
        "n_samples": n,
        "interval": {"declared": f"[0, {times[-1] + dt:.12g})", "start_s": 0.0, "end_s": times[-1] + dt},
        "selected": {"first_time_s": times[0], "last_time_s": times[-1]},
        "times": times,
        "columns": cols,
    }


def endpoint_quantity(values: list[float]) -> dict:
    rad = values[-1] - values[0]
    return {
        "endpoint_delta_rad": rad,
        "endpoint_delta_turns": rad / (2.0 * math.pi),
    }


def build_family(name: str, spec: dict) -> dict:
    inputs = [read_csv(REPO_ROOT / p, spec["phase_columns"]) for p in spec["inputs"]]
    control = None
    if spec.get("control"):
        control = read_csv(REPO_ROOT / spec["control"], spec["phase_columns"])
    entries = []
    for inp in inputs:
        entry = {
            "input": {"path": inp["path"], "sha256": inp["sha256"],
                      "n_samples": inp["n_samples"],
                      "interval": inp["interval"],
                      "selected_first_time_s": inp["selected"]["first_time_s"],
                      "selected_last_time_s": inp["selected"]["last_time_s"]},
            "quantities": {},
        }
        for c in spec["phase_columns"]:
            entry["quantities"][c] = endpoint_quantity(inp["columns"][c])
        # bump_0 control applies ONLY to bump files (plan: sustained family
        # has no matched zero-input control committed).
        if (control is not None and inp["path"] != control["path"]
                and "bump" in inp["path"]):
            corrected = {}
            for c in spec["phase_columns"]:
                sig = endpoint_quantity(inp["columns"][c])["endpoint_delta_rad"]
                ctl = endpoint_quantity(control["columns"][c])["endpoint_delta_rad"]
                d = sig - ctl
                corrected[c] = {
                    "signal_endpoint_delta_rad": sig,
                    "control_endpoint_delta_rad": ctl,
                    "control_corrected_endpoint_delta_rad": d,
                    "control_corrected_endpoint_delta_turns": d / (2.0 * math.pi),
                }
            entry["control_corrected"] = corrected
            entry["control"] = {"path": control["path"], "sha256": control["sha256"]}
        entries.append(entry)
    result = {
        "schema_version": 1,
        "family": name,
        "generator": {"name": "scripts/rebuild_historical_metrics_v2.py",
                      "version": GENERATOR_VERSION,
                      "sha256": file_sha256(pathlib.Path(__file__))},
        "metric_spec": {"path": METRIC_SPEC_PATH, "version": METRIC_SPEC_VERSION,
                        "sha256": METRIC_SPEC_SHA256},
        "reconstruction_plan": {"path": PLAN_PATH, "sha256": file_sha256(REPO_ROOT / PLAN_PATH)},
        "generated_at": GENERATION_TIMESTAMP,
        "units": {"phase": "rad", "turns": "endpoint_delta_rad / (2*pi)"},
        "control_relationship": spec.get("control_note"),
        "runs": entries,
        "limitations": LIMITATION_TEXT,
        "not_applicable": [
            "activity clusters / event counts: NOT_APPLICABLE (no predeclared windows)",
            "voltage-area cross-check: NOT_APPLICABLE (no direct same-JJ V mapping in this family)",
            "convergence verdict: NOT_APPLICABLE (no preregistered ladder)",
        ],
    }
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out-root", default=str(REPO_ROOT),
                        help="repo root for output paths (default: repo root)")
    args = parser.parse_args(argv)
    root = pathlib.Path(args.out_root)
    for name, spec in INVENTORY.items():
        family = build_family(name, spec)
        out = root / spec["out"]
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(family, indent=2) + "\n")
        print(f"wrote {out.relative_to(root)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
