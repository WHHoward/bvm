#!/usr/bin/env python3
"""Rebuild only the failed comparison-input attempt after COMPARISON-01."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from analyze import ARRAY_RAW, EXP, SIGNALS, SINGLE_RAW, load_trace, rel, sha256, write_derived_csv


def write_once(path: Path, content: str) -> None:
    if path.exists():
        if path.read_text(encoding="utf-8") == content:
            return
        raise RuntimeError(f"refusing to overwrite repair manifest: {path}")
    path.write_text(content, encoding="utf-8")


def main() -> int:
    single = load_trace(SINGLE_RAW)
    array = load_trace(ARRAY_RAW)
    records = {}
    for group in ("CONTROL", "BVM_STORAGE", "BVM_RLOOP", "BVM_OUTPUT", "JSL_ENDPOINTS", "QB_INTERNAL", "JTL_ENDPOINTS"):
        path = EXP / "plots/comparison/data" / f"{group}_RAW_DELTA.csv"
        records[group] = write_derived_csv(path, single, SIGNALS[group], "comparison", other=array)
    result = {
        "schema": "jm2-single-vs-4bvm-shared-sl-comparison-repair-v1",
        "experiment_id": EXP.name,
        "created_at_local": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "reason": "COMPARISON-01: emit SINGLE original + ARRAY BVM1 original + ARRAY minus SINGLE for each observable",
        "raw_hashes": {"single": sha256(SINGLE_RAW), "array": sha256(ARRAY_RAW)},
        "records": records,
        "phase_rule": "continuous_unwrap(raw radians); plot2 -j 2pi is the only display conversion",
    }
    write_once(EXP / "analysis/comparison_repair_manifest.json", json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"status": "PASS", "groups": list(records), "manifest": rel(EXP / 'analysis/comparison_repair_manifest.json')}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
