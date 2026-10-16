from __future__ import annotations

import argparse
import csv
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

SERIES = Path(__file__).resolve().parents[1]
REPO = SERIES.parents[2]
sys.path.insert(0, str(SERIES / "scripts"))
import diagonal_platform as legacy  # noqa: E402

V9_PATH = SERIES / "scripts" / "v9_multiply_batch.py"
V9_SPEC = importlib.util.spec_from_file_location("v9_multiply_batch_test", V9_PATH)
assert V9_SPEC is not None and V9_SPEC.loader is not None
v9 = importlib.util.module_from_spec(V9_SPEC)
V9_SPEC.loader.exec_module(v9)


class V9MigrationTests(unittest.TestCase):
    def setUp(self):
        self.config = v9.load_config([])
        self.reference_text = v9.REFERENCE_DECK.read_text(encoding="utf-8")
        self.sources = v9.source_records()

    def test_v9_11x13_stimulus_active_sources_match_current_reference(self):
        scenario = v9.scenario_config(self.config, 11, 13)
        stimulus, _drivers = v9.bvm_stimulus.make_v9_stimulus(
            v9.stimulus_parameters(self.config, scenario))
        self.assertEqual(v9._active_sources(stimulus),
                         v9._active_sources(v9.REFERENCE_STIMULUS.read_text(encoding="utf-8")))
        self.assertEqual(scenario["selected_se_rows"], ["SE_R1", "SE_R2", "SE_R4"])
        self.assertEqual(scenario["selected_bl_columns"], ["BL_C1", "BL_C2", "BL_C4"])

    def test_v9_sources_and_legacy_source_counts_remain_separate(self):
        scenario = v9.scenario_config(self.config, 15, 15)
        v9_text, _ = v9.bvm_stimulus.make_v9_stimulus(
            v9.stimulus_parameters(self.config, scenario))
        v9_sources = v9._active_sources(v9_text)
        self.assertEqual(len(v9_sources), 20)
        self.assertEqual(sum(name.startswith("I_SE_R") for name in v9_sources), 4)
        self.assertEqual(sum(name.startswith("I_WL_R") for name in v9_sources), 4)
        self.assertEqual(sum(name.startswith("I_BL_C") for name in v9_sources), 4)

        args = argparse.Namespace(
            a=15, b=15, read_interval_ps=70.0, clock_period_ps=70.0,
            se_clock_delay_ps=70.0, first_read_ps=110.0, write_start_ps=50.0,
            dt_ps=0.01, tail_ps=70.0, stop_ps=None, rounds=3, round_cases=None,
        )
        legacy_params = v9.bvm_stimulus.params(args)
        legacy_sources = [line for line in v9.bvm_stimulus.make_stimulus(legacy_params).splitlines()
                          if line.startswith(("I_WL_", "I_BL_", "I_SE_", "V_TRIG_CLK_"))]
        self.assertEqual(len(legacy_sources), 32)
        self.assertTrue(any(line.startswith("I_SE_R1C1 ") for line in legacy_sources))
        self.assertFalse(any(line.startswith("I_SE_R1 ") for line in legacy_sources))

    def test_all_256_operand_encodings_are_static_only(self):
        scenarios = [v9.scenario_config(self.config, a, b)
                     for a in range(16) for b in range(16)]
        self.assertEqual(len(scenarios), 256)
        for case in scenarios:
            self.assertEqual(case["expected_product"], case["a"] * case["b"])
            self.assertEqual(case["expected_bits_msb_first"], format(case["a"] * case["b"], "08b"))
            self.assertEqual(case["row_bits_R1_lsb"], "".join(str((case["a"] >> i) & 1) for i in range(4)))
            self.assertEqual(case["column_bits_C1_msb"], "".join(str((case["b"] >> (3-i)) & 1) for i in range(4)))
        self.assertEqual(legacy.next_run_number(), 109)

    def test_registered_decks_match_reference_topology_and_raw_guard(self):
        v9.registered_values_ok(self.config)
        scenarios = v9._build_cases(self.config, True)
        payloads = v9._case_payloads(self.config, scenarios, self.reference_text, self.sources)
        qa = v9.validate_rendered(self.config, scenarios, payloads, self.reference_text, self.sources)
        self.assertEqual(qa["status"], "PASS")
        self.assertEqual(qa["bvm_count"], 16)
        self.assertEqual(qa["qb_count"], 16)
        self.assertEqual(qa["shared_row_se_source_count"], 4)
        self.assertEqual(qa["carry_sjtl_count_by_stage"],
                         {"D1": 1, "D2": 1, "D3": 5, "D4": 2, "D5": 1, "D6": 1})
        self.assertLess(qa["raw_estimate_bytes"], v9.MAX_RAW_BYTES)
        self.assertTrue(qa["v9_template_topology_equal_except_registered_print_and_tran"])

    def test_v9_plot_pages_are_classic_focus_sets(self):
        scenario = v9.scenario_config(self.config, 11, 13)
        manifest = v9.make_probe_manifest(scenario)
        pages = legacy.plot_signals(manifest)
        self.assertEqual([item["file"] for item in pages], [
            "01_excitation_and_outputs.html", "02_clock_data_timing.html", "03_v9_chain_focus.html"])
        self.assertEqual(len(pages[0]["signals"]), 20)
        self.assertTrue(all(signal in {item["label"] for item in manifest["signals"]}
                            for page in pages for signal in page["signals"]))

    def test_v9_classic_html_rebuilds_from_temporary_probe_fixture(self):
        scenario = v9.scenario_config(self.config, 11, 13)
        manifest = v9.make_probe_manifest(scenario)
        labels = [item["label"] for item in manifest["signals"]]
        with tempfile.TemporaryDirectory(prefix="v9-plot-fixture-", dir=SERIES / "plots") as temp:
            root = Path(temp)
            run_dir = root / "fixture"
            run_dir.mkdir()
            raw = run_dir / "raw.csv"
            with raw.open("w", encoding="utf-8", newline="") as stream:
                writer = csv.writer(stream)
                writer.writerow(["time", *labels])
                for t in (0.0, 1e-14, 2e-14, 3e-14):
                    writer.writerow([t, *([0.0] * len(labels))])
            qa = legacy.render_plots(run_dir, manifest, plot_root_override=root / "pages")
            self.assertEqual(qa["status"], "PASS")
            self.assertEqual(qa["page_count"], 3)
            self.assertTrue(all(item["responsive"] and item["zoom_hover_legend_interactive"]
                                for item in qa["pages"]))
            self.assertTrue(all((root / "pages" / Path(item["path"]).name).is_file()
                                for item in qa["pages"]))


if __name__ == "__main__":
    unittest.main()
