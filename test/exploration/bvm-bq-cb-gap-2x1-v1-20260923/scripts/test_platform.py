#!/usr/bin/env python3
"""No-solver unit checks for frozen topology, stimulus, probes, and arithmetic."""

from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from analyze_run import integrate, unwrap, window_indices
from common import MATRIX, TEMPLATE, cases, probe_signals, render_deck, source_pwl, stimulus_text
from plot_run import plot_sets


class ExperimentPlatformTests(unittest.TestCase):
    def test_exact_matrix_and_masks(self):
        self.assertEqual([case["run_id"] for case in cases()], ["N0_00", "N1_01", "N1_10", "N2_11"])
        self.assertEqual({case["mask"]: case["active_bvms"] for case in cases()},
                         {"00": [], "01": [2], "10": [1], "11": [1, 2]})

    def test_fixed_timestep_and_windows(self):
        from common import read_json
        matrix = read_json(MATRIX)
        self.assertEqual((matrix["dt"], matrix["stop"], matrix["save_start"]), ("0.01p", "200p", "0p"))
        self.assertEqual(matrix["windows_ps"]["final_read"], [110, 121])

    def test_stimulus_has_six_sources_and_all_write_preambles(self):
        texts = {case["mask"]: stimulus_text(case["mask"]) for case in cases()}
        expected = {"I_WL1", "I_BL1", "I_SE1", "I_WL2", "I_BL2", "I_SE2"}
        for mask, text in texts.items():
            lines = [line for line in text.splitlines() if line and not line.startswith("*")]
            self.assertEqual(len(lines), 6)
        self.assertEqual({line.split()[0] for line in lines}, expected)
        self.assertIn("50p 0 51p -100u 60p -100u 61p 0", lines[0])
        for line_index in range(1, 7):
            source_name = texts["00"].splitlines()[line_index].split()[0]
            marker = "101p 0" if source_name.startswith(("I_WL", "I_BL")) else "81p 0"
            left = texts["00"].splitlines()[line_index].split(marker)[0] + marker
            right = texts["01"].splitlines()[line_index].split(marker)[0] + marker
            self.assertEqual(left, right)
        self.assertIn("111p 100u 120p 100u", texts["01"].splitlines()[6])
        self.assertIn("111p 100u 120p 100u", texts["10"].splitlines()[1])

    def test_pwl_source_node_and_points(self):
        line = source_pwl("I_WL1", [(50, "-100u"), (70, "100u")])
        self.assertTrue(line.startswith("I_WL1 0 WL1 pwl("))
        self.assertIn("51p -100u 60p -100u 61p 0", line)
        self.assertTrue(line.endswith("200p 0)"))

    def test_rendered_topology_has_direct_gap2_contributions(self):
        text = render_deck("stimulus.inc").lower()
        for instance in ("xbvm1", "xbq1", "xcb1", "xacc1", "xgap1",
                         "xbvm2", "xbq2", "xcb2", "xacc2", "xgap2"):
            self.assertEqual(sum(line.strip().startswith(instance + " ") for line in text.splitlines()), 1)
        self.assertIn("xgap1 acc1_out gap2_in sjtl", text)
        self.assertIn("xacc2 cb2_out gap2_in sjtl", text)
        self.assertIn("xgap2 gap2_in final_out sjtl", text)
        self.assertIn("r_term final_out 0 2", text)
        self.assertIn(".tran 0.01p 200p 0p", text)
        self.assertIn(".model jjmit jj(rtype=1, vg=2.8m, cap=0.07p, r0=160, rn=16, icrit=0.1m)", text)
        self.assertNotIn("xgap1_extra", text)

    def test_registered_probe_closure(self):
        signals = probe_signals()
        self.assertEqual(len(signals), len(set(signals)))
        for required in ("I(I_WL1)", "I(I_BL1)", "I(I_SE1)", "P(B_JM1|XBVM1)",
                         "P(B_JS2|XBVM2)", "V(BVM1_SL)", "P(BJ3|XBQ1)",
                         "V(QB2_OUT)", "P(BJ2|XCB1)", "P(BJ1|XACC2)",
                         "I(L2|XACC2)", "I(L2|XGAP1)", "V(GAP2_IN)",
                         "P(BJ1|XGAP2)", "V(FINAL_OUT)", "V(R_TERM)", "I(R_TERM)"):
            self.assertIn(required, signals)
        self.assertIn("V(ACC1_OUT)", signals)
        self.assertNotIn("V(ACC2_OUT)", signals)

    def test_required_plot_sets_include_excitation_and_outputs(self):
        sets = plot_sets("N2_11")
        self.assertEqual(set(sets), {"01_overview_whole_chain", "02_local_branches",
                                     "03_gap2_merge_debug", "04_bvm_state"})
        overview = sets["01_overview_whole_chain"]
        self.assertTrue(any(signal.startswith("I(I_WL") for signal in overview))
        self.assertIn("V(FINAL_OUT)", overview)
        self.assertEqual(len(sets["03_gap2_merge_debug"]), 7)
        self.assertEqual(set(sets["03_gap2_merge_debug"]), {
            "P(BJ1|XACC2)", "P(BJ1|XGAP1)", "I(L2|XACC2)", "I(L2|XGAP1)",
            "V(GAP2_IN)", "P(BJ1|XGAP2)", "V(FINAL_OUT)"})

    def test_actual_grid_helpers(self):
        unwrapped = unwrap([3.0, -3.0, 0.0])
        self.assertAlmostEqual(unwrapped[0], 3.0)
        self.assertAlmostEqual(unwrapped[1], -3.0 + 2.0 * 3.141592653589793)
        self.assertAlmostEqual(unwrapped[2], 2.0 * 3.141592653589793)
        self.assertAlmostEqual(integrate([0.0, 1.0, 2.0], [0.0, 2.0, 0.0]), 2.0)
        self.assertEqual(window_indices([100, 110, 120, 130], [110, 130]), [1, 2])

    def test_plot_projection_keeps_original_value_tokens(self):
        from plot_run import headers_and_rows
        with tempfile.TemporaryDirectory() as temp:
            raw = Path(temp) / "raw.csv"
            raw.write_text("time,V(A)\n0,0.0\n1e-10,1.2500000000000000\n1.5e-10,-2\n2e-10,9\n", encoding="utf-8")
            fields, rows, times = headers_and_rows(raw, ["V(A)"], (100.0, 200.0))
            self.assertEqual(fields, ["time", "V(A)"])
            self.assertEqual(rows, [{"time": "1e-10", "V(A)": "1.2500000000000000"},
                                    {"time": "1.5e-10", "V(A)": "-2"}])
            self.assertEqual(times, [100.0, 150.0])


if __name__ == "__main__":
    unittest.main()
