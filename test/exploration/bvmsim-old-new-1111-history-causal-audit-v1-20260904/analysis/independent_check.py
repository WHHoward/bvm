#!/usr/bin/env python3
"""Small independent arithmetic cross-check for the history audit.

It reuses the repository raw reader and unwrap implementation, but recomputes
the key parity, voltage-area, and integer-crossing assertions without reading
the analyzer's intermediate values as the source of those facts.
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
OLD = REPO / "test/exploration/bvmsim-4bvm-jm2-connected-state-position-ab-v1-20260903/runs/1111/raw.csv"
NEW = REPO / "test/exploration/bvmsim-4bvm-allone-selective-read-additivity-isolation-v1-20260904/runs/1111/raw.csv"

sys.path.insert(0, str(REPO / "scripts"))
from bvmtools.phase import TAU, continuous_unwrap  # noqa: E402
from bvmtools.raw import read_csv  # noqa: E402
from bvmtools.sfq import PHI0  # noqa: E402


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def indices(time_s: tuple[float, ...], start_ps: float, end_ps: float) -> list[int]:
    return [index for index, value in enumerate(time_s) if start_ps <= value * 1.0e12 < end_ps]


def area_over_phi0(time_s: tuple[float, ...], voltage: tuple[float, ...], selected: list[int]) -> float:
    return sum(
        0.5 * (voltage[left] + voltage[right]) * (time_s[right] - time_s[left])
        for left, right in zip(selected, selected[1:])
    ) / PHI0


def crossing_times(time_s: tuple[float, ...], phase: tuple[float, ...], start_ps: float, end_ps: float) -> list[float]:
    selected = indices(time_s, start_ps, end_ps)
    baseline = phase[selected[0]]
    result = []
    for number in range(1, 7):
        target = baseline + number * TAU
        for index in selected:
            if phase[index] >= target:
                result.append(time_s[index] * 1.0e12)
                break
    return result


def main() -> int:
    old = read_csv(OLD)
    new = read_csv(NEW)
    if old.time != new.time:
        raise AssertionError("time grids differ")
    common = [name for name in old.headers if name != "time" and name in new.headers]
    pre = indices(old.time, 45.0, 70.0)
    for name in common:
        left = old.column(name)
        right = new.column(name)
        if any(left[index] != right[index] for index in pre):
            raise AssertionError(f"pre70 mismatch: {name}")
    old_phase = continuous_unwrap(old.column("P(BJ2|XBQ1)"))
    new_phase = continuous_unwrap(new.column("P(BJ2|XBQ1)"))
    response = indices(old.time, 110.0, 170.0)
    old_net = (old_phase[response[-1]] - old_phase[response[0]]) / TAU
    new_net = (new_phase[response[-1]] - new_phase[response[0]]) / TAU
    old_area = area_over_phi0(old.time, old.column("V(BJ2|XBQ1)"), response)
    new_area = area_over_phi0(new.time, new.column("V(BJ2|XBQ1)"), response)
    old_cross = crossing_times(old.time, old_phase, 110.0, 170.0)
    new_cross = crossing_times(new.time, new_phase, 110.0, 170.0)
    expected = {
        "old_net_turns": 3.9991979977555987,
        "new_net_turns": 4.9991599108350515,
        "old_area_turns": 3.9991796646395255,
        "new_area_turns": 4.9991438584341745,
    }
    observed = {
        "old_net_turns": old_net,
        "new_net_turns": new_net,
        "old_area_turns": old_area,
        "new_area_turns": new_area,
        "old_crossing_times_ps": old_cross,
        "new_crossing_times_ps": new_cross,
        "pre70_common_probe_count": len(common),
        "old_raw_sha256": digest(OLD),
        "new_raw_sha256": digest(NEW),
    }
    for key, value in expected.items():
        if not math.isclose(observed[key], value, rel_tol=0.0, abs_tol=1.0e-12):
            raise AssertionError(f"{key} changed: {observed[key]} != {value}")
    old_cross_rounded = [round(value, 6) for value in old_cross]
    new_cross_rounded = [round(value, 6) for value in new_cross]
    if old_cross_rounded != [118.3, 121.7, 125.5, 138.8]:
        raise AssertionError(f"unexpected OLD crossings: {old_cross}")
    if new_cross_rounded != [118.1, 121.4, 124.9, 129.5, 141.4]:
        raise AssertionError(f"unexpected NEW crossings: {new_cross}")
    result = {
        "status": "PASS",
        "checks": [
            "exact common-grid pre70 equality",
            "same-JJ BJ2 phase endpoint delta",
            "same-JJ BJ2 voltage area over Phi0",
            "sample-based integer crossing order",
            "raw hashes unchanged at independent check",
        ],
        "observed": observed,
        "comparison_to_analyzer_expected_values": expected,
        "interpretation_boundary": "crossings are trajectory markers, not SFQ event counts",
    }
    (EXP / "analysis/independent_check.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
