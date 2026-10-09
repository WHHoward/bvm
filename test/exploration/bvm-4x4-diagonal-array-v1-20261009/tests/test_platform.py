from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

SERIES = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERIES / "scripts"))
import diagonal_platform as platform  # noqa: E402


def rendered(preset: str, overrides: list[str] | None = None):
    case, stimulus, t1 = platform.load_config(preset, overrides)
    return case, stimulus, t1, platform.render(case, stimulus, t1, platform.RUNS / "_TEST_PREVIEW")


def rendered_with_set(preset: str, assignment: str):
    case, stimulus, t1 = platform.load_config(preset, [assignment])
    return case, stimulus, t1, platform.render(case, stimulus, t1, platform.RUNS / "_TEST_PREVIEW")


class DiagonalPlatformTests(unittest.TestCase):
    def test_diagonal_map_is_exact_partition(self):
        flat = [cell for group in platform.DIAGONALS.values() for cell in group]
        self.assertEqual(len(flat), 16)
        self.assertEqual(set(flat), set(platform.CELLS))
        self.assertEqual([len(platform.DIAGONALS[f"D{i}"]) for i in range(7)], [1, 2, 3, 4, 3, 2, 1])
        for row in range(1, 5):
            for col in range(1, 5):
                cell = f"R{row}C{col}"
                diagonal = next(name for name, cells in platform.DIAGONALS.items() if cell in cells)
                self.assertEqual(int(diagonal[1]), row + 3 - col)

    def test_registered_masks_and_paper_target_vector(self):
        expected = {
            "D3_N0": [],
            "D3_N1": ["R1C1"],
            "D3_N2": ["R1C1", "R2C2"],
            "D3_N3": ["R1C1", "R2C2", "R3C3"],
            "D3_N4": ["R1C1", "R2C2", "R3C3", "R4C4"],
        }
        for name, cells in expected.items():
            case, _stim, _t1, output = rendered(name)
            self.assertEqual(platform._active_cells(case), cells)
            self.assertEqual(output["static_qa"]["status"], "PASS")
        case, _stim, _t1, output = rendered("PAPER_1101_1101")
        counts = [sum(cell in platform._active_cells(case) for cell in cells)
                  for cells in platform.DIAGONALS.values()]
        self.assertEqual(counts, [1, 1, 1, 3, 1, 1, 1])
        self.assertEqual(case["SE_ENABLE_MASK"], "ALL")
        self.assertEqual(output["static_qa"]["active_final_crosspoints"],
                         ["R1C1", "R1C2", "R1C4", "R2C1", "R2C2", "R2C4", "R4C1", "R4C2", "R4C4"])

    def test_render_has_shared_rows_columns_independent_cell_se_and_serial_chains(self):
        case, _stim, _t1, output = rendered("D3_N4", ["SJTL_COUNT_D3=1,1,1,1"])
        deck = output["deck"].splitlines()
        self.assertEqual(len([line for line in deck if line.startswith("XBVM_")]), 16)
        self.assertEqual(len([line for line in deck if line.startswith("XBQ_")]), 16)
        self.assertEqual(len([line for line in deck if line.startswith("XSJTL_")]), 16)
        self.assertEqual(len([line for line in deck if line.startswith("XCB_")]), 16)
        self.assertEqual(len([line for line in deck if line.startswith("R_TERM_")]), 7)
        self.assertIn("XBVM_R1C1 WL_R1 BL_C1 SE_R1C1 SL_R1C1 BVM", deck)
        self.assertIn("XBVM_R4C4 WL_R4 BL_C4 SE_R4C4 SL_R4C4 BVM", deck)
        self.assertIn("XBQ_R1C1 SL_R1C1 MERGE_D3_L1 BQ", deck)
        self.assertIn("XCB_D3_L1 SJTL_OUT_D3_L1 MERGE_D3_L2 CB", deck)
        self.assertIn("XCB_D3_L4 SJTL_OUT_D3_L4 DOUT_D3 CB", deck)
        self.assertFalse(any("MERGE_D3" in line and "MERGE_D2" in line for line in deck))
        self.assertEqual(output["static_qa"]["driver_count_by_branch"], {"WL": 4, "BL": 4, "SE": 16})
        self.assertTrue(output["static_qa"]["unique_outputs"])

    def test_registered_d3_cases_only_change_final_read_se_mask(self):
        outputs = {name: rendered(name, ["SJTL_COUNT_D3=1,1,1,1"])[3]
                   for name in ("D3_N0", "D3_N1", "D3_N2", "D3_N3", "D3_N4")}
        stimuli = {name: {line.split()[0]: line for line in outputs[name]["stimulus_text"].splitlines()
                          if line.startswith("I_")} for name in outputs}
        base_non_se = {source: line for source, line in stimuli["D3_N0"].items()
                       if not source.startswith("I_SE_")}
        targets = {
            "D3_N0": set(),
            "D3_N1": {"R1C1"},
            "D3_N2": {"R1C1", "R2C2"},
            "D3_N3": {"R1C1", "R2C2", "R3C3"},
            "D3_N4": set(platform.DIAGONALS["D3"]),
        }
        def knots(line: str):
            tokens=line.split("PWL(",1)[1].removesuffix(")").split()
            return list(zip(tokens[0::2],tokens[1::2]))
        for name, lines in stimuli.items():
            self.assertEqual({src: line for src,line in lines.items() if not src.startswith("I_SE_")}, base_non_se)
            self.assertEqual(len([src for src in lines if src.startswith("I_SE_")]), 16)
            for cell in platform.CELLS:
                points=knots(lines[f"I_SE_{cell}"])
                baseline=knots(stimuli["D3_N0"][f"I_SE_{cell}"])
                self.assertEqual([point for point in points if point[0] != "111p" and point[0] != "120p" and point[0] != "121p"],
                                 [point for point in baseline if point[0] != "111p" and point[0] != "120p" and point[0] != "121p"])
                final_value=dict(points).get("111p")
                self.assertEqual(final_value, "100u" if cell in targets[name] else "0")
            self.assertEqual(outputs[name]["static_qa"]["status"], "PASS")
        self.assertEqual(outputs["D3_N0"]["probes"]["signal_count"], 124)

    def test_canonical_sources_and_t1_off_isolation(self):
        source = platform.verify_sources()
        case, stimulus, t1, output = rendered("PAPER_1101_1101")
        self.assertEqual({k: v["sha256"] for k, v in source.items()}, platform.SOURCE_SHA256)
        self.assertEqual(output["static_qa"]["status"], "PASS")
        self.assertNotIn("t1_cell.cir", output["deck"])
        self.assertFalse(any(line.startswith(("XT1", "V_BIAS", "V_TRIG_CLK", "XCBU", "XDFF"))
                             for line in output["deck"].splitlines()))
        changed_t1 = dict(t1)
        changed_t1["T1_J1_AREA"] = "99"
        changed_t1["T1_L1"] = "99p"
        self.assertEqual(output["deck"], platform.render(case, stimulus, changed_t1,
                                                           platform.RUNS / "_TEST_PREVIEW")["deck"])
        with self.assertRaisesRegex(platform.ConfigError, "DIAGONAL_TERMINAL/T1_MODE=OFF"):
            platform.validate_config({**case, "OUTPUT_MODE": "DIAGONAL_T1_CHAIN"}, stimulus, t1)

    def test_focus_profile_stays_compact_and_keeps_required_state_diagnostics(self):
        case, _stim, _t1, output = rendered("D3_N4", ["SJTL_COUNT_D3=1,1,1,1"])
        labels = {item["label"] for item in output["probes"]["signals"]}
        self.assertEqual(output["probes"]["profile"], "focus")
        self.assertEqual(output["probes"]["signal_count"], 124)
        self.assertLess(platform.estimate_raw_bytes(output["probes"]["signal_count"]), 100_000_000)
        for cell in platform.CELLS:
            for branch, element in (("WL", "R_WL"), ("BL", "R_BL"), ("SE", "R_SE")):
                self.assertIn(f"I({element}|XBVM_{cell})", labels)
        for cell in platform.DIAGONALS["D3"]:
            self.assertIn(f"V(SL_{cell})", labels)
            for jj in ("B_JM1", "B_JM2"):
                self.assertIn(f"P({jj}|XBVM_{cell})", labels)
                self.assertIn(f"V({jj}|XBVM_{cell})", labels)
        for diagonal in platform.DIAGONALS:
            self.assertIn(f"V(DOUT_{diagonal})", labels)
        for jj in ("BJ1", "BJ2", "BJ3"):
            self.assertIn(f"P({jj}|XBQ_R1C1)", labels)
            self.assertIn(f"V({jj}|XBQ_R1C1)", labels)
        for level in range(1, 5):
            self.assertIn(f"V(MERGE_D3_L{level})", labels)
            self.assertIn(f"V(SJTL_OUT_D3_L{level})", labels)
            self.assertIn(f"P(BJ1|XSJTL_D3_L{level})", labels)
            self.assertIn(f"P(BJ1|XCB_D3_L{level})", labels)

    def test_profiles_are_ordered_and_compact_records_shared_source_currents(self):
        compact_case, compact_stim, compact_t1 = platform.load_config(
            "BUS400_D3_N1", ["PROBE_PROFILE=compact"])
        compact = platform.render(compact_case, compact_stim, compact_t1,
                                  platform.RUNS / "_TEST_PREVIEW")
        focus_case, focus_stim, focus_t1 = platform.load_config("BUS400_D3_N1")
        focus = platform.render(focus_case, focus_stim, focus_t1, platform.RUNS / "_TEST_PREVIEW")
        debug_case, debug_stim, debug_t1 = platform.load_config(
            "BUS400_D3_N1", ["PROBE_PROFILE=debug"])
        debug = platform.render(debug_case, debug_stim, debug_t1, platform.RUNS / "_TEST_PREVIEW")
        self.assertLess(compact["probes"]["signal_count"], focus["probes"]["signal_count"])
        self.assertLess(focus["probes"]["signal_count"], debug["probes"]["signal_count"])
        compact_labels = {item["label"] for item in compact["probes"]["signals"]}
        self.assertIn("I(I_WL_R1)", compact_labels)
        self.assertIn("I(I_BL_C1)", compact_labels)
        self.assertIn("I(I_SE_R1C1)", compact_labels)
        self.assertEqual(len(platform.plot_signals(focus["probes"])), 2)

    def test_sjtl_defaults_preserve_legacy_names_and_parameterize_multistage_or_zero(self):
        _case, _stim, _t1, default = rendered("BUS400_D3_N1")
        expected_legacy = {
            f"XSJTL_{diagonal}_L{level} MERGE_{diagonal}_L{level} SJTL_OUT_{diagonal}_L{level} sJTL"
            for diagonal, cells in platform.DIAGONALS.items()
            for level in range(1, len(cells) + 1)
        }
        self.assertTrue(expected_legacy.issubset(set(default["deck"].splitlines())))

        _case, _stim, _t1, multi = rendered_with_set("BUS400_D3_N1", "SJTL_COUNT_D3=1,2,1,1")
        self.assertEqual(multi["static_qa"]["sjtl_count"], 17)
        self.assertEqual(multi["static_qa"]["cb_count"], 16)
        self.assertIn("XSJTL_D3_L2_S1 MERGE_D3_L2 SJTL_MID_D3_L2_S1 sJTL", multi["deck"].splitlines())
        self.assertIn("XSJTL_D3_L2_S2 SJTL_MID_D3_L2_S1 SJTL_OUT_D3_L2 sJTL", multi["deck"].splitlines())
        self.assertIn("XCB_D3_L2 SJTL_OUT_D3_L2 MERGE_D3_L3 CB", multi["deck"].splitlines())

        _case, _stim, _t1, zero = rendered_with_set("BUS400_D3_N1", "SJTL_COUNT_D3=0,1,1,1")
        self.assertEqual(zero["static_qa"]["sjtl_count"], 15)
        self.assertIn("XCB_D3_L1 MERGE_D3_L1 MERGE_D3_L2 CB", zero["deck"].splitlines())

    def test_sjtl_count_validation_rejects_wrong_lengths_and_negative_values(self):
        with self.assertRaisesRegex(platform.ConfigError, "comma-separated nonnegative"):
            platform.load_config("BUS400_D3_N1", ["SJTL_COUNT_D3=1,2"])
        with self.assertRaisesRegex(platform.ConfigError, "comma-separated nonnegative"):
            platform.load_config("BUS400_D3_N1", ["SJTL_COUNT_D3=1,-1,1,1"])

    def test_bus400_pair_is_exact_and_legacy_presets_keep_200u(self):
        already_executed = any((platform.RUNS / run_id).exists()
                               for run_id in ("A007_BUS400_D3_N0", "A008_BUS400_D3_N1"))
        if already_executed:
            with self.assertRaises(platform.ConfigError):
                platform.validate_bus400_matrix()
            outputs = []
            for preset in platform.BUS400_CASES:
                case, stimulus, t1 = platform.load_config(preset)
                outputs.append(platform.render(case, stimulus, t1, platform.RUNS / "_TEST_PREVIEW"))
            self.assertEqual(outputs[0]["deck"], outputs[1]["deck"])
            self.assertTrue(all(item["static_qa"]["status"] == "PASS" for item in outputs))
        else:
            cases = platform.validate_bus400_matrix()
            self.assertEqual([item["case"]["CASE"] for item in cases], list(platform.BUS400_CASES))
            self.assertEqual([item["next_run_id"] for item in cases],
                             ["A007_BUS400_D3_N0", "A008_BUS400_D3_N1"])
            self.assertEqual(cases[0]["rendered"]["deck"], cases[1]["rendered"]["deck"])
        for preset in platform.REGISTERED_CASES:
            case, _stimulus, _t1 = platform.load_config(preset)
            self.assertEqual(case["ROW_WL_WRITE_AMPLITUDE"], "200u")
            self.assertEqual(case["COL_BL_WRITE_AMPLITUDE"], "200u")
            self.assertEqual(case["ROW_WL_READ_AMPLITUDE"], "200u")

    def test_stage_windows_use_full_pwl_interval_and_final_response_stop(self):
        windows = platform._windows_for_run(platform.RUNS / "_NONEXISTENT_TEST_ONLY")
        self.assertEqual(windows["WRITE0"], (50.0, 61.0))
        self.assertEqual(windows["READ0"], (70.0, 81.0))
        self.assertEqual(windows["WRITE1"], (90.0, 101.0))
        self.assertEqual(windows["FINAL_READ"], (110.0, 121.0))
        self.assertEqual(windows["FINAL_READ_RESPONSE"], (110.0, 250.0))

    def test_user_case_label_matches_the_live_paper_like_mask(self):
        case = platform.parse_env(platform.USER_CASE)
        preset = platform.parse_env(SERIES / "presets" / "PAPER_1101_1101.env")
        self.assertEqual(case["CASE"], "PAPER_1101_1101")
        for key in ("ROW_BITS", "COL_BITS", "SE_ENABLE_MASK"):
            self.assertEqual(case[key], preset[key])
        self.assertEqual(platform._active_cells(case), [
            "R1C1", "R1C2", "R1C4", "R2C1", "R2C2", "R2C4", "R4C1", "R4C2", "R4C4"
        ])

    def test_plot_height_tracks_sep_comb_signal_groups_and_browser_width(self):
        two_groups = platform.plot_layout_metrics(["I(A)", "V(B)"])
        three_groups = platform.plot_layout_metrics(["V(A)", "P(B)", "I(C)"])
        four_groups = platform.plot_layout_metrics(["V(A)", "P(B)", "I(C)", "X(D)"])
        self.assertEqual(two_groups["height_px"], 780)
        self.assertEqual(three_groups["height_px"], 1080)
        self.assertEqual(four_groups["height_px"], 1380)
        self.assertTrue(all(item["width_mode"] == "responsive_full_width"
                            for item in (two_groups, three_groups, four_groups)))

    def _render_t1_array_case(self, clock_mode: str) -> dict:
        case, stimulus, t1 = platform.load_config()
        case.update({"CASE": f"T1_STATIC_{clock_mode}", "ROW_BITS": "1111", "COL_BITS": "1111",
                     "SE_ENABLE_MASK": "ALL", "OUTPUT_MODE": "DIAGONAL_T1_INDEPENDENT",
                     "T1_MODE": "ALL_INDEPENDENT", "CBU_MODE": "OFF", "CARRY_MODE": "NONE",
                     "PROBE_PROFILE": "t1_array_focus", "FOCUS_DIAGONAL": "D3",
                     "ROW_WL_WRITE_AMPLITUDE": "400u", "COL_BL_WRITE_AMPLITUDE": "400u",
                     "ROW_WL_READ_AMPLITUDE": "400u", "COL_SE_READ_AMPLITUDE": "100u",
                     "DT": "0.01p", "STOP": "250p",
                     "SJTL_COUNT_D0": "1", "SJTL_COUNT_D1": "1,1", "SJTL_COUNT_D2": "1,1,1",
                     "SJTL_COUNT_D3": "1,2,2,1", "SJTL_COUNT_D4": "1,1,1",
                     "SJTL_COUNT_D5": "1,1", "SJTL_COUNT_D6": "1"})
        t1["T1_CLK_MODE"] = clock_mode
        platform.validate_config(case, stimulus, t1)
        return platform.render(case, stimulus, t1, platform.RUNS / "_T1_TEST_PREVIEW")

    def test_t1_tunable_source_default_is_canonical_body_equivalent(self):
        _case, _stimulus, t1 = platform.load_config()
        rendered, info = platform.render_t1_source(t1)
        self.assertTrue(info["topology_equivalent"])
        self.assertTrue(info["default_body_equivalent_to_canonical"])
        self.assertEqual(set(info["parameters_consumed"]), set(platform.T1_INTERNAL_PARAM_KEYS))
        self.assertIn(".subckt T1 I CLK S C N_BIAS1 N_BIAS2 N_BIAS3", rendered)
        changed = dict(t1)
        changed["T1_J1_AREA"] = "3.6"
        changed_rendered, changed_info = platform.render_t1_source(changed)
        self.assertTrue(changed_info["topology_equivalent"])
        self.assertFalse(changed_info["default_body_equivalent_to_canonical"])
        self.assertIn("B_J1 N2 0 jjmit area=3.6", changed_rendered)

    def test_t1_array_static_topology_quiet_and_pulse_are_seven_independent_channels(self):
        quiet = self._render_t1_array_case("QUIET")
        pulse = self._render_t1_array_case("PULSE")
        for output, mode in ((quiet, "QUIET"), (pulse, "PULSE")):
            deck = output["deck"].splitlines()
            self.assertEqual(output["static_qa"]["status"], "PASS")
            self.assertEqual(output["static_qa"]["t1_count"], 7)
            self.assertEqual(output["static_qa"]["terminal_count"], 0)
            self.assertEqual(len([line for line in deck if line.startswith("XT1_D")]), 7)
            self.assertEqual(len([line for line in deck if line.startswith("V_T1_LINK_D")]), 7)
            self.assertEqual(len([line for line in deck if line.startswith("XSJTL_")]), 18)
            self.assertEqual(len([line for line in deck if line.startswith("R_S_D")]), 7)
            self.assertEqual(len([line for line in deck if line.startswith("R_C_D")]), 7)
            self.assertFalse(any(line.startswith("R_TERM_D") for line in deck))
            self.assertFalse(any("XCBU" in line or "XDFF" in line for line in deck))
            self.assertEqual(output["probes"]["profile"], "t1_array_focus")
            self.assertIn("V(S_D3)", {signal["label"] for signal in output["probes"]["signals"]})
            if mode == "QUIET":
                self.assertEqual(len([line for line in deck if line.startswith("R_CLK_QUIET_D")]), 7)
                self.assertFalse(any(line.startswith("V_TRIG_CLK_D") for line in deck))
            else:
                self.assertEqual(len([line for line in deck if line.startswith("V_TRIG_CLK_D")]), 7)
                self.assertEqual(len([line for line in deck if line.startswith("R_TRIG_CLK_D")]), 7)
                self.assertFalse(any(line.startswith("R_CLK_QUIET_D") for line in deck))

    def test_raw_reader_allows_focus_subset_but_can_enforce_exact_registered_header(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            raw = Path(temp_dir) / "subset.csv"
            raw.write_text("time,V(DOUT_D3),I(R_SE|XBVM_R1C1)\n0,1,2\n1,3,4\n", encoding="utf-8")
            times, columns, header = platform.read_raw(raw, {"V(DOUT_D3)"})
            self.assertEqual(len(times), 2)
            self.assertEqual(set(columns), {"V(DOUT_D3)"})
            self.assertEqual(len(header), 3)
            with self.assertRaisesRegex(platform.ConfigError, "undeclared probes"):
                platform.read_raw(raw, {"V(DOUT_D3)"}, exact_header=True)

    def test_t1_summary_identity_uses_raw_sha_after_analysis_field(self):
        digest = "a" * 64
        result = {"artifact_status": "VALID", "raw_sha256": digest,
                  "physical_solve_count": 1}
        qa = {"status": "PASS"}
        t1_qa = {"status": "PASS", "raw_sha256_after_analysis": digest}
        metrics = {"t1_array": {"raw_sha256": digest}}
        platform._validate_t1_run_identity("A013_T1_ALL_QUIET", result, qa,
                                           t1_qa, metrics, digest)
        with self.assertRaisesRegex(platform.ConfigError, "QA/raw identity"):
            platform._validate_t1_run_identity("A013_T1_ALL_QUIET", result, qa,
                                               {"status": "PASS", "raw_sha256_after": digest},
                                               metrics, digest)


if __name__ == "__main__":
    unittest.main()
