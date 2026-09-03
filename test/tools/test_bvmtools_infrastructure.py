#!/usr/bin/env python3
"""Focused tests for the small shared measurement/probe/QA layer."""

from __future__ import annotations

import math
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))

from bvmtools.deckqa import deck_qa  # noqa: E402
from bvmtools.metrics import (  # noqa: E402
    burst_total_metrics,
    peak_timing_metrics,
    phase_area_consistency,
    phase_area_window,
    signed_integral,
)
from bvmtools.probes import (  # noqa: E402
    flatten_probe_labels,
    historical_bvm_array_probes,
    historical_jtl_probes,
    original_bvmsim_qb_probes,
)
from bvmtools.stimulus import (  # noqa: E402
    compare_stimuli,
    validate_bvm_write_read_protocol,
)
from bvmtools.sfq import PHI0  # noqa: E402


class SharedMetricsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.time = (0.0, 1.0e-12, 3.0e-12)
        self.phase = (0.0, math.pi, 2.0 * math.pi)
        self.voltage = (PHI0 / 3.0e-12,) * 3

    def test_nonuniform_signed_integral_and_phase_area_use_actual_grid(self) -> None:
        self.assertAlmostEqual(signed_integral(self.time, self.voltage), PHI0, places=30)
        result = phase_area_window(self.time, self.phase, self.voltage, (0.0, 4.0e-12))
        self.assertAlmostEqual(float(result["phase_delta_turns"]), 1.0, places=12)
        self.assertAlmostEqual(float(result["voltage_area_over_phi0"]), 1.0, places=12)

    def test_consistency_requires_explicit_tolerances_and_sign(self) -> None:
        result = phase_area_consistency(
            1.0,
            1.01,
            absolute_tolerance_turns=0.02,
            relative_tolerance=0.0,
        )
        self.assertTrue(result["phase_area_consistent"])
        opposite = phase_area_consistency(
            1.0,
            -1.0,
            absolute_tolerance_turns=2.0,
            relative_tolerance=0.0,
        )
        self.assertFalse(opposite["phase_area_consistent"])

    def test_burst_total_has_no_count_authority(self) -> None:
        result = burst_total_metrics(
            self.time,
            self.phase,
            self.voltage,
            (0.0, 4.0e-12),
            absolute_tolerance_turns=0.01,
            relative_tolerance=0.0,
        )
        self.assertNotIn("count", result)
        self.assertTrue(result["phase_area_consistency"]["phase_area_consistent"])

    def test_peak_timing_reports_signed_and_absolute_peak(self) -> None:
        result = peak_timing_metrics(
            self.time,
            (-1.0e-6, 4.0e-6, -3.0e-6),
            (0.0, 4.0e-12),
            unit="A",
        )
        self.assertEqual(result["unit"], "uA")
        self.assertAlmostEqual(float(result["peak_abs_value"]), 4.0, places=12)
        self.assertAlmostEqual(float(result["peak_abs_time_s"]), 1.0e-12, places=24)


class ProbeFactoryTests(unittest.TestCase):
    def test_four_bvm_factory_covers_all_internal_instances(self) -> None:
        probes = historical_bvm_array_probes(4)
        self.assertEqual(tuple(probes)[:4], ("BVM1", "BVM2", "BVM3", "BVM4"))
        labels = flatten_probe_labels(probes)
        for instance in range(1, 5):
            for junction in ("JM1", "JM2", "JS1", "JS2"):
                self.assertIn(f"P(B_{junction}|XBVM{instance})", labels)
            self.assertIn(f"I(L_SL|XBVM{instance})", labels)
        self.assertIn("P(BVMOUT)", labels)

    def test_qb_and_jtl_factories_are_complete(self) -> None:
        qb = flatten_probe_labels(original_bvmsim_qb_probes())
        self.assertIn("I(LIN|XBQ1)", qb)
        self.assertIn("P(BJ2|XBQ1)", qb)
        jtl = flatten_probe_labels(historical_jtl_probes(6))
        for stage in range(1, 7):
            self.assertIn(f"P(B01|XJTL1_{stage})", jtl)
            self.assertIn(f"V(B02|XJTL1_{stage})", jtl)


class StimulusAndDeckQATests(unittest.TestCase):
    def test_protocol_validation_reports_read_mismatch(self) -> None:
        time = (0.0, 1.0e-12, 2.0e-12)
        signals = {
            "I(I_WL1)": (100.0e-6,) * 3,
            "I(I_BL1)": (100.0e-6,) * 3,
            "I(I_SE1)": (0.0,) * 3,
        }
        result = validate_bvm_write_read_protocol(
            signals,
            time,
            write_window_s=(0.0, 2.0e-12),
            read_window_s=(0.0, 2.0e-12),
            expected_write={"I(I_WL1)": 100.0e-6, "I(I_BL1)": 100.0e-6},
            expected_read={
                "I(I_WL1)": 100.0e-6,
                "I(I_BL1)": 0.0,
                "I(I_SE1)": 100.0e-6,
            },
            tolerance=1.0e-12,
        )
        self.assertEqual(result["status"], "READ_PROTOCOL_MISMATCH")

    def test_stimulus_compare_requires_same_signal_set(self) -> None:
        result = compare_stimuli(
            (0.0, 1.0e-12),
            {"WL": (1.0, 1.0)},
            (0.0, 1.0e-12),
            {"BL": (1.0, 1.0)},
            (0.0, 2.0e-12),
        )
        self.assertEqual(result["status"], "SIGNAL_SET_MISMATCH")

    def test_deck_qa_is_artifact_only_and_detects_missing_model(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            deck = Path(directory) / "deck.cir"
            lines = [
                ".include ../../BVMSim/bvm_cell.cir",
                ".include ../../BVMSim/BQ.cir",
                ".include ../../BVMSim/library_josim/jtl2.cir",
                "xBQ1 QBin QBout BQ",
                "RBQ1 o6 0 10",
                ".tran 0.1p 200p",
                ".print P(BJ2|XBQ1)",
            ]
            lines.extend(f"XBVM{index} WL{index} BL{index} SE{index} SL{index} BVM" for index in range(1, 5))
            lines.extend(f"B_LD4_{index:02d} n{index} n{index + 1} jjmit" for index in range(1, 12))
            lines.append("BVMout n12 QBin jjmit")
            lines.extend(f"xjtl1_{stage} in{stage} out{stage} jtl" for stage in range(1, 7))
            deck.write_text("\n".join(lines) + "\n", encoding="utf-8")
            result = deck_qa(
                deck,
                log_text="Missing model: JJMIT\nUsing default model",
                expected_includes=("BVMSim/bvm_cell.cir", "BVMSim/BQ.cir", "BVMSim/library_josim/jtl2.cir"),
                expected_bvm_instances=4,
                expected_terminal_sensing_jj_count=12,
                expected_jtl_stages=6,
                expected_termination_ohm=10.0,
                expected_tran_timestep_ps=0.1,
                required_probes=("P(BJ2|XBQ1)",),
                raw_headers=("time", "P(BJ2|XBQ1)"),
            )
            self.assertEqual(result["status"], "MODEL_CLOSURE_FAIL")
            self.assertTrue(result["model_warning_detected"])


if __name__ == "__main__":
    unittest.main()
