#!/usr/bin/env python3
"""No-solver unit checks for frozen topology, stimulus, probes, and arithmetic."""

from __future__ import annotations

import base64
import csv
import hashlib
import json
import re
import struct
import subprocess
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import analyze_run
from analyze_run import JJ_PAIRS, integrate, integrate_actual, stage_window_metrics, window_indices
import independent_verify
from independent_verify import compare_scalar, dec_integral
from common import (MATRIX, PHI0, TEMPLATE, cases, in_half_open_window, probe_signals,
                    PLOTTER, REPO, raw_time_ps, render_deck, sha256, source_pwl,
                    stimulus_text, write_json)
from plot_run import headers_and_rows, plot_sets


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
        for mask, expected_active in (("00", set()), ("01", {2}), ("10", {1}), ("11", {1, 2})):
            lines = texts[mask].splitlines()
            for bvm, wl_index, se_index in ((1, 1, 3), (2, 4, 6)):
                should_read = bvm in expected_active
                self.assertEqual("111p 100u 120p 100u" in lines[wl_index], should_read)
                self.assertEqual("111p 100u 120p 100u" in lines[se_index], should_read)
            self.assertTrue(all("110p" not in lines[index] for index in (2, 5)))

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
        self.assertEqual(len(signals), 223)
        for optional_internal in ("I(IB2|XBQ1)", "I(RJ3|XBQ2)", "V(RJ2|XBQ1)",
                                  "I(RJ1|XCB1)", "I(IB1|XACC2)", "V(RJ1|XGAP2)"):
            self.assertIn(optional_internal, signals)

    def test_required_plot_sets_include_excitation_and_outputs(self):
        sets = plot_sets("N2_11")
        self.assertEqual(set(sets), {"01_overview_whole_chain", "02_local_branch_1", "02_local_branch_2",
                                     "03_gap2_merge_debug", "04_bvm_state"})
        overview = sets["01_overview_whole_chain"]
        self.assertTrue(any(signal.startswith("I(I_WL") for signal in overview))
        self.assertIn("V(FINAL_OUT)", overview)
        self.assertEqual(len(sets["03_gap2_merge_debug"]), 7)
        self.assertEqual(set(sets["03_gap2_merge_debug"]), {
            "P(BJ1|XACC2)", "P(BJ1|XGAP1)", "I(L2|XACC2)", "I(L2|XGAP1)",
            "V(GAP2_IN)", "P(BJ1|XGAP2)", "V(FINAL_OUT)"})

    def test_actual_grid_helpers(self):
        self.assertAlmostEqual(integrate([0.0, 1.0, 2.0], [0.0, 2.0, 0.0]), 2.0)
        self.assertAlmostEqual(integrate_actual(["0", "1e-12", "3e-12"], [0.0, 2.0, 0.0]), 3e-12)
        self.assertEqual(dec_integral([Decimal("0"), Decimal("1e-12"), Decimal("3e-12")],
                                      [Decimal("0"), Decimal("2"), Decimal("0")]),
                         Decimal("3e-12"))
        self.assertEqual(compare_scalar("mechanical", 1.0, 1.0, 1e-12)["status"], "PASS")
        stored = ["1.099999999999e-10", "1.1e-10", "1.209999e-10", "1.21e-10"]
        self.assertEqual(window_indices(stored, [110, 121]), [1, 2])
        self.assertEqual(raw_time_ps("1.1e-10"), raw_time_ps("0.00000000011"))
        self.assertTrue(in_half_open_window("1.1e-10", [110, 121]))
        self.assertFalse(in_half_open_window("1.21e-10", [110, 121]))
        tokens = ["1.10e-10", "1.20e-10"]
        values = {}
        for _stage, phase_signal, voltage_signal in JJ_PAIRS:
            values[phase_signal] = [0.0, 7.0]
            values[voltage_signal] = [0.0, 0.0]
        metric = next(row for row in stage_window_metrics(tokens, values)
                      if row["stage"] == "BQ1_BJ3" and row["window"] == "final_read")
        self.assertEqual(metric["delta_phase_rad"], 7.0)  # Raw JoSIM P is not modulo-reduced.
        self.assertAlmostEqual(metric["phase_delta_turns_navigation"], 7.0 / (2.0 * 3.141592653589793))

    def test_plot_projection_keeps_original_value_tokens(self):
        with tempfile.TemporaryDirectory() as temp:
            raw = Path(temp) / "raw.csv"
            raw.write_text("time,V(A)\n0,0.0\n1.1e-10,1.2500000000000000\n1.209999e-10,-2\n1.21e-10,9\n", encoding="utf-8")
            fields, rows, times, tokens = headers_and_rows(raw, ["V(A)"], (110.0, 121.0))
            self.assertEqual(fields, ["time", "V(A)"])
            self.assertEqual(rows, [{"time": "1.1e-10", "V(A)": "1.2500000000000000"},
                                    {"time": "1.209999e-10", "V(A)": "-2"}])
            self.assertEqual(times, [110.0, 120.9999])
            self.assertEqual(tokens, ["1.1e-10", "1.209999e-10"])

    def test_classic_plotter_phase_conversion_and_axis_qa(self):
        with tempfile.TemporaryDirectory(prefix="josim_plot2_smoke_") as temp:
            temp_root = Path(temp)
            raw = temp_root / "phase_smoke.csv"
            raw.write_text("time,P(TEST)\n0,0\n1e-12,6.283185307179586\n2e-12,12.566370614359172\n", encoding="utf-8")
            raw_hash_before = hashlib.sha256(raw.read_bytes()).hexdigest()
            plot = temp_root / "phase_smoke.html"
            command = [sys.executable, str(PLOTTER), str(raw), "-x", str(plot),
                       "-t", "sep_comb", "-c", "dark", "-j", "2pi", "-s", "P(TEST)"]
            completed = subprocess.run(command, cwd=REPO, capture_output=True, text=True, check=False)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            content = plot.read_text(encoding="utf-8")
            runtime = next(match for match in re.finditer(
                r"<script(?P<attrs>[^>]*)>(?P<body>.*?)</script>", content, flags=re.S | re.I)
                if len(match.group("body")) > 1_000_000 and
                ("plotly.js v" in match.group("body") or "var Plotly=" in match.group("body")))
            compact = content[:runtime.start()] + "<script src='runtime.js'></script>" + content[runtime.end():]
            self.assertIn("Phase (turns) [rad\\u002f2pi]", compact)
            self.assertNotIn("unknown", compact.lower())
            y_match = re.search(r'"y":\{"dtype":"f8","bdata":"([^"]+)"\}', compact)
            self.assertIsNotNone(y_match)
            y_bytes = base64.b64decode(y_match.group(1))
            y_values = list(struct.unpack("<3d", y_bytes))
            self.assertEqual(y_values, [0.0, 1.0, 2.0])
            self.assertEqual(hashlib.sha256(raw.read_bytes()).hexdigest(), raw_hash_before)

    def test_independent_decimal_raw_recalculation(self):
        with tempfile.TemporaryDirectory(prefix="bvm_independent_raw_") as temp:
            run_root = Path(temp) / "N0_00"
            run_root.mkdir()
            raw = run_root / "raw.csv"
            tokens = ["0", "1.01e-10", "1.0999e-10", "1.1e-10",
                      "1.2e-10", "1.21e-10", "1.9999e-10"]
            signals = probe_signals()
            voltage = PHI0 / (2.0 * 3.141592653589793) * 1e11
            with raw.open("w", encoding="utf-8", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=["time", *signals])
                writer.writeheader()
                for token in tokens:
                    time_ps = float(raw_time_ps(token))
                    row = {"time": token}
                    for signal in signals:
                        if signal.startswith("P("):
                            row[signal] = repr(time_ps * 0.1)
                        elif signal.startswith("V("):
                            row[signal] = repr(voltage)
                        else:
                            row[signal] = "0"
                    writer.writerow(row)
            write_json(run_root / "metadata.json", {"parameters": {"MASK": "00"},
                        "raw": {"sha256": sha256(raw)}})
            with patch.object(analyze_run, "run_dir", side_effect=lambda _run_id: run_root), \
                 patch.object(independent_verify, "run_dir", side_effect=lambda _run_id: run_root):
                mechanical = analyze_run.analyze("N0_00")
                independent = independent_verify.verify("N0_00")
            self.assertEqual(mechanical["status"], "PASS")
            self.assertEqual(independent["status"], "PASS")
            self.assertEqual(len(independent["checks"]), 35)


if __name__ == "__main__":
    unittest.main()
