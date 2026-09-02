#!/usr/bin/env python3
"""Focused tests for the task-local voltage-gap candidate association."""

from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

import numpy as np


ANALYSIS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ANALYSIS_DIR))
from analyze import PHI0, TAU, voltage_gap_candidates  # noqa: E402


def synthetic_trace(pulses: list[tuple[int, int, float]], sample_count: int = 800):
    """Build phase/voltage traces on a 0.025 ps grid from signed pulse turns."""

    dt_s = 0.025e-12
    time_s = tuple(index * dt_s for index in range(sample_count))
    voltage = np.zeros(sample_count, dtype=float)
    for start, end, turns in pulses:
        width_s = (end - start) * dt_s
        voltage[start:end] = turns * PHI0 / width_s
    phase = np.zeros(sample_count, dtype=float)
    for index in range(1, sample_count):
        phase[index] = phase[index - 1] + TAU * 0.5 * (voltage[index - 1] + voltage[index]) * dt_s / PHI0
    return time_s, tuple(phase), tuple(voltage)


class VoltageGapCandidateTests(unittest.TestCase):
    def test_zero_event(self) -> None:
        time_s, phase, voltage = synthetic_trace([])
        result = voltage_gap_candidates(time_s, phase, voltage)
        self.assertEqual(result["candidate_count"], 0)
        self.assertEqual(result["complete_segment_count"], 0)

    def test_one_clean_event_has_retrap(self) -> None:
        result = voltage_gap_candidates(*synthetic_trace([(100, 140, 1.0)]))
        self.assertEqual(result["candidate_count"], 1)
        self.assertEqual(result["complete_segment_count"], 1)
        self.assertEqual(result["clean_separated_event_count"], 1)
        self.assertAlmostEqual(result["candidates"][0]["phase_delta_turns"], 1.0, places=10)
        self.assertAlmostEqual(result["candidates"][0]["voltage_area_turns"], 1.0, places=10)

    def test_four_separated_events_are_four_candidates(self) -> None:
        pulses = [(100, 120, 1.0), (140, 160, 1.0), (180, 200, 1.0), (220, 240, 1.0)]
        result = voltage_gap_candidates(*synthetic_trace(pulses))
        self.assertEqual(result["candidate_count"], 4)
        self.assertEqual(result["complete_segment_count"], 4)
        self.assertEqual(result["clean_separated_event_count"], 4)

    def test_one_continuous_four_turn_segment_is_not_four_events(self) -> None:
        result = voltage_gap_candidates(*synthetic_trace([(100, 260, 4.0)]))
        self.assertEqual(result["candidate_count"], 1)
        self.assertEqual(result["complete_segment_count"], 1)
        self.assertEqual(result["clean_separated_event_count"], 0)
        self.assertTrue(result["continuous_multiturn_running"])

    def test_mixed_sign_sequence_preserves_order_and_polarity(self) -> None:
        pulses = [(100, 120, 1.0), (150, 170, -1.0)]
        result = voltage_gap_candidates(*synthetic_trace(pulses))
        self.assertEqual(result["candidate_count"], 2)
        self.assertEqual(result["complete_segment_count"], 2)
        self.assertEqual([item["direction"] for item in result["candidates"]], [1, -1])


if __name__ == "__main__":
    unittest.main(verbosity=2)
