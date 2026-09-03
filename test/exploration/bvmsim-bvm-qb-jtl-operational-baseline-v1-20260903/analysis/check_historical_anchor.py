#!/usr/bin/env python3
"""Compare the historical BVMSim raw with the state-1111 baseline raw."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

from bvmtools.compare import compare_series  # noqa: E402
from bvmtools.raw import read_csv  # noqa: E402


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    historical = REPO / "BVMSim/data_tran.csv"
    current = EXP / "runs/four/1111/raw/run-01.csv"
    old = read_csv(historical)
    new = read_csv(current)
    labels = [
        "I(BVMOUT)",
        "V(QBIN)",
        "V(QBOUT)",
        "P(BJ1|XBQ1)",
        "P(B01|XJTL1_1)",
        "P(B01|XJTL1_2)",
    ]
    result = {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "historical_raw": {"path": str(historical.relative_to(REPO)), "sha256": sha256(historical), "duplicate_columns": old.duplicate_columns},
        "baseline_raw": {"path": str(current.relative_to(REPO)), "sha256": sha256(current)},
        "grid": {
            "historical_samples": old.sample_count,
            "baseline_samples": new.sample_count,
            "exact": old.time == new.time,
            "interpolation": "none",
        },
        "signals": {},
        "interpretation": "Electrical/probe-preservation check only; not a physical correctness or convergence claim.",
    }
    for label in labels:
        result["signals"][label] = compare_series(old.time, old.column(label), new.time, new.column(label))
    (EXP / "analysis/historical_anchor_check.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps({"grid_exact": result["grid"]["exact"], "signals": len(labels)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
