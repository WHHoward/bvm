#!/usr/bin/env python3
"""Compare BVM source/storage behavior against committed no-load/direct-QB raw."""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from statistics import median


RUN = Path(__file__).resolve().parents[1]
REPO = RUN.parents[2]
PATHS = {
    "canonical_source": REPO / "test/exploration/bvm-internal-readout-20260819/raw/pos-read-single/run-01.csv",
    "direct_native_qb": REPO / "test/exploration/bvm-sfq-receiver-native-qb-20260822/raw/read1/run-01.csv",
    "r6a_isolated_qb": RUN / "raw/read1/run-01.csv",
}
KEYS = [
    "I(L_SL|XBVM1)",
    "V(SL1)",
    "V(N6|XBVM1)",
    "P(B_JM1|XBVM1)",
    "P(B_JM2|XBVM1)",
    "P(B_JS1|XBVM1)",
    "P(B_JS2|XBVM1)",
]


def value(row, key):
    wanted = key.casefold()
    for actual, raw in row.items():
        if actual.casefold() == wanted:
            return float(raw)
    raise KeyError(key)


def metric(path):
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    out = {"raw_path": str(path.relative_to(REPO)), "rows": len(rows)}
    for key in KEYS:
        pre = [value(row, key) for row in rows if 80.0 <= value(row, "time") * 1e12 < 90.0]
        activity = [value(row, key) for row in rows if 94.0 <= value(row, "time") * 1e12 < 130.0]
        post = [value(row, key) for row in rows if 150.0 <= value(row, "time") * 1e12 < 170.0]
        if key.startswith("I("):
            scale = 1.0e6
            unit = "uA"
        elif key.startswith("V("):
            scale = 1.0e6
            unit = "uV"
        else:
            scale = 1.0
            unit = "rad"
        pre_median = median(pre)
        post_median = median(post)
        out[key] = {
            "unit": unit,
            "activity_peak_abs": max(abs(item) for item in activity) * scale,
            "post_peak_to_peak": (max(post) - min(post)) * scale,
            "post_median": post_median * scale,
            "pre_median": pre_median * scale,
            "post_minus_pre": (post_median - pre_median) * scale,
            "post_minus_pre_turn": (post_median - pre_median) / (2.0 * math.pi) if unit == "rad" else None,
        }
    return out


def main():
    result = {
        "comparison": "canonical_source_vs_direct_native_qb_vs_r6a_isolated_qb",
        "windows_ps": {"pre": [80.0, 90.0], "activity": [94.0, 130.0], "post": [150.0, 170.0]},
        "cases": {name: metric(path) for name, path in PATHS.items()},
        "interpretation": {
            "read1_JS_multi_turn_is_source_behavior": True,
            "isolation_test": "compare post waveform/median to canonical_source, not require read1 JS phase to remain near zero",
        },
    }
    (RUN / "analysis/r6a-source-guard-comparison.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
