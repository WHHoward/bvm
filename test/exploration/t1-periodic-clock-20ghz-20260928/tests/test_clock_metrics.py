from __future__ import annotations

import csv
import math
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

EXPERIMENT = Path(__file__).resolve().parents[1]
REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(EXPERIMENT / "scripts"))
sys.path.insert(0, str(REPO / "scripts"))

from bvmtools.raw import read_csv  # noqa: E402
from clock_metrics import (PHI0_VS, TARGET_JUNCTIONS, analyze_trace,
                           exact_stored_times)  # noqa: E402


CONFIG = {
    "T1_CLK_MODE": "PULSE", "T1_CLK_START": "170p", "T1_CLK_PERIOD": "50p",
    "T1_CLK_AMPLITUDE": "1.2m", "T1_CLK_RISE": "1p", "T1_CLK_WIDTH": "2p",
    "T1_CLK_FALL": "1p", "T1_CLK_R_SERIES": "5", "STOP": "370p",
}


def pulse_value(time_ps: float, start_ps: float) -> float:
    relative = time_ps - start_ps
    if relative < 0 or relative >= 4:
        return 0.0
    if relative < 1:
        return 1.2e-3 * relative
    if relative < 3:
        return 1.2e-3
    return 1.2e-3 * (4 - relative)


def make_synthetic_raw(path: Path) -> None:
    junctions = tuple(f"B_J{i}" for i in range(1, 12))
    inductors = tuple(f"L{i}" for i in range(1, 18))
    resistors = ("R_J1", "R_J3", "R_J4", "R_J5", "R_J6", "R_J7", "R_J8",
                 "R_J9", "R_J10", "R_J11", "RB1", "RB2", "RB3")
    headers = ["time", "V(CLK_RAW)", "V(CLK)", "I(R_TRIG_CLK)", "V(S)", "V(C)",
               "I(R_S)", "I(R_C)", "V(N_BIAS1)", "V(N_BIAS2)", "V(N_BIAS3)"]
    for jj in junctions:
        headers.extend((f"P({jj}|XT1)", f"V({jj}|XT1)", f"I({jj}|XT1)"))
    for inductor in inductors:
        headers.extend((f"I({inductor}|XT1)", f"V({inductor}|XT1)"))
    for resistor in resistors:
        headers.extend((f"I({resistor}|XT1)", f"V({resistor}|XT1)"))
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(headers)
        for tick in range(3700):
            if tick % 7 == 3 and tick % 10 != 0:
                continue
            time_ps = tick / 10.0
            time_s = time_ps * 1e-12
            clk_raw = sum(pulse_value(time_ps, start) for start in (170, 220, 270, 320))
            clk = 0.42 * clk_raw
            s = 0.2e-3
            c = 0.1e-3
            row = [time_s, clk_raw, clk, (clk_raw - clk) / 5, s, c, s / 12, c / 12,
                   1.8e-3, 1.8e-3, 1.8e-3]
            for index, _jj in enumerate(junctions):
                rate_rad_s = (3.0e11 + index * 1.0e9)
                raw_phase = (rate_rad_s * time_s) % (2 * math.pi)
                voltage = PHI0_VS * rate_rad_s / (2 * math.pi)
                row.extend((raw_phase, voltage, 0.0))
            for _inductor in inductors:
                row.extend((0.0, 0.0))
            for _resistor in resistors:
                row.extend((0.0, 0.0))
            writer.writerow(row)


class ClockMetricsTests(unittest.TestCase):
    def test_registered_actual_grid_cycle_arithmetic_and_phase_area_crosscheck(self):
        with tempfile.TemporaryDirectory(prefix="clock-metrics-grid-") as temp:
            raw = Path(temp) / "raw.csv"
            make_synthetic_raw(raw)
            trace = read_csv(raw)
            metrics = analyze_trace(trace, CONFIG)
            exact_times = exact_stored_times(raw)
        self.assertFalse(trace.qa()["uniform_time_grid"])
        self.assertEqual(len(metrics["cycles"]), 4)
        self.assertEqual([round(cycle["scheduled_start_s"] * 1e12) for cycle in metrics["cycles"]],
                         [170, 220, 270, 320])
        self.assertLess(metrics["cycles"][0]["last_sample_s"], 220e-12)
        self.assertEqual(metrics["cycles"][1]["first_sample_s"], 220e-12)
        self.assertEqual(metrics["cycles"][0]["sample_count"],
                         sum(Decimal("170e-12") <= time < Decimal("220e-12")
                             for time in exact_times))
        first = metrics["cycles"][0]
        self.assertAlmostEqual(first["clock"]["source_node"]["max"], 1.2e-3, places=12)
        self.assertAlmostEqual(first["clock"]["t1_input"]["max"], 0.504e-3, places=12)
        self.assertEqual(first["clock"]["input_arrival"]["status"], "MEASURED_NAVIGATION_MARKER")
        self.assertFalse(first["clock"]["input_arrival"]["interpolation_or_resampling"])
        s_metric = first["outputs"]["V(S)"]
        self.assertAlmostEqual(s_metric["voltage_area_v_s"],
                               0.2e-3 * (s_metric["last_sample_s"]
                                         - s_metric["first_sample_s"]), places=23)
        jj = first["junctions"]["B_J2"]
        self.assertAlmostEqual(jj["phase_delta_rad"],
                               3.01e11 * (jj["last_sample_s"] - jj["first_sample_s"]),
                               places=7)
        self.assertAlmostEqual(jj["phase_minus_area_turns_arithmetic"], 0.0, places=10)
        self.assertAlmostEqual(first["inter_pulse_tail"]["window_s"][0], 174e-12, places=24)
        self.assertGreater(abs(first["inter_pulse_tail"]["junction_phase_delta_rad"]["B_J2"]), 1.0)
        self.assertFalse(metrics["interpolation_or_resampling"])
        self.assertFalse(metrics["scientific_interpretation_performed"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
