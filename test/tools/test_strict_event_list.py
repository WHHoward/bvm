#!/usr/bin/env python3
"""Focused tests for the reusable strict multi-event list helper."""

from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))

from bvmtools.sfq import PHI0, StrictLocalEventSpec, strict_event_list  # noqa: E402


def _spec() -> StrictLocalEventSpec:
    return StrictLocalEventSpec.from_mapping(
        {
            "id": "synthetic-strict-event-list-test-v1",
            "scope": "task-local",
            "status": "FROZEN",
            "mapping_status": "SYNTHETIC_DIRECT_PV",
            "phase_column": "P(J)",
            "voltage_column": "V(J)",
            "branch_endpoints": "synthetic direct branch",
            "voltage_to_phase_sign": 1,
            "reporting_direction": 1,
            "run_id": "synthetic",
            "window_id": "full",
            "raw_sha256": "0" * 64,
            "metric_spec": {"path": "test", "version": "test", "sha256": "1" * 64},
            "tolerance": {
                "id": "synthetic",
                "scope": "task-local",
                "status": "FROZEN",
                "evidence": "test",
                "phase_area_residual_abs_floor_turns": 0.05,
                "phase_area_residual_relative": 0.10,
                "complete_min_turns": 1.0,
                "clean_upper_turns": 1.15,
                "post_range_max_turns": 1.0,
                "post_tail_p2p_max_turns": 0.25,
            },
        }
    )


def _trace(
    sequence: list[int], *, continuous: bool = False
) -> tuple[tuple[float, ...], tuple[float, ...], tuple[float, ...]]:
    """Create a piecewise-linear phase/voltage trace on a uniform grid."""

    dt = 1.0e-12
    steps_per_event = 1000
    retrap_steps = 100
    time = [0.0]
    phase = [0.0]
    voltage = [0.0]
    for direction in sequence:
        event_steps = steps_per_event * (len(sequence) if continuous else 1)
        event_turns = 4.0 if continuous else 1.05
        event_voltage = direction * PHI0 * event_turns / dt / event_steps
        if not time[1:]:
            voltage[-1] = event_voltage
        for _ in range(event_steps):
            phase.append(phase[-1] + direction * 2.0 * math.pi * event_turns / event_steps)
            voltage.append(event_voltage)
            time.append(time[-1] + dt)
        if not continuous:
            retrap_voltage = -direction * PHI0 * 0.05 / dt / retrap_steps
            for _ in range(retrap_steps):
                phase.append(phase[-1] - direction * 2.0 * math.pi * 0.05 / retrap_steps)
                voltage.append(retrap_voltage)
                time.append(time[-1] + dt)
    for _ in range(20):
        phase.append(phase[-1])
        voltage.append(0.0)
        time.append(time[-1] + dt)
    return tuple(time), tuple(phase), tuple(voltage)


class StrictEventListTests(unittest.TestCase):
    def _analyze(self, sequence: list[int], *, continuous: bool = False) -> dict[str, object]:
        time, phase, voltage = _trace(sequence, continuous=continuous)
        end = time[-1] + 1.0e-12
        return strict_event_list(
            time,
            phase,
            voltage,
            event_window_s=(0.0, end),
            scan_window_s=(0.0, end),
            retrap_max_p2p_turns=0.25,
            spec=_spec(),
        )

    def test_zero_event_trace(self) -> None:
        result = self._analyze([])
        self.assertEqual(result["complete_segment_count"], 0)
        self.assertEqual(result["clean_separated_event_count"], 0)
        self.assertFalse(result["continuous_multi_turn_running"])

    def test_one_clean_event(self) -> None:
        result = self._analyze([1])
        self.assertEqual(result["complete_segment_count"], 1)
        self.assertEqual(result["clean_separated_event_count"], 1)
        self.assertEqual(result["clean_event_directions"], [1])

    def test_four_separated_events_are_not_one_event(self) -> None:
        result = self._analyze([1, 1, 1, 1])
        self.assertEqual(result["complete_segment_count"], 4)
        self.assertEqual(result["clean_separated_event_count"], 4)
        self.assertFalse(result["continuous_multi_turn_running"])

    def test_continuous_four_turn_segment_is_not_four_events(self) -> None:
        result = self._analyze([1], continuous=True)
        self.assertEqual(result["complete_segment_count"], 1)
        self.assertEqual(result["clean_separated_event_count"], 0)
        self.assertTrue(result["continuous_multi_turn_running"])
        self.assertAlmostEqual(float(result["largest_segment_turns"]), 4.0, places=6)

    def test_mixed_sign_sequence_preserves_order_and_polarity(self) -> None:
        result = self._analyze([1, -1, 1])
        self.assertEqual(result["complete_segment_count"], 3)
        self.assertEqual(
            [int(item["direction"]) for item in result["complete_events"]],
            [1, -1, 1],
        )


if __name__ == "__main__":
    unittest.main()
