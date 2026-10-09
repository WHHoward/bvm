from __future__ import annotations

import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

SERIES = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERIES / "scripts"))
import diagonal_platform as platform  # noqa: E402
import cb_direct_d1_batch as cb_batch  # noqa: E402


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
        case, _stim, _t1, output = rendered("D3_N4", [
            "SJTL_COUNT_D0=1", "SJTL_COUNT_D1=1,1", "SJTL_COUNT_D2=1,1,1",
            "SJTL_COUNT_D3=1,1,1,1", "SJTL_COUNT_D4=1,1,1",
            "SJTL_COUNT_D5=1,1", "SJTL_COUNT_D6=1",
        ])
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
        with self.assertRaisesRegex(platform.ConfigError, "pair DIAGONAL_TERMINAL/OFF"):
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
        self.assertEqual(windows["FINAL_READ_RESPONSE"], (110.0, 300.0))

    def test_paper_preset_keeps_terminal_mode_independent_of_manual_user_case(self):
        case, _stimulus, _t1 = platform.load_config("PAPER_1101_1101")
        self.assertEqual(case["CASE"], "PAPER_1101_1101")
        self.assertEqual(case["OUTPUT_MODE"], "DIAGONAL_TERMINAL")
        self.assertEqual(case["T1_MODE"], "OFF")
        for key in ("ROW_BITS", "COL_BITS", "SE_ENABLE_MASK"):
            self.assertEqual(case[key], {"ROW_BITS": "1101", "COL_BITS": "1101",
                                         "SE_ENABLE_MASK": "ALL"}[key])
        self.assertEqual(platform._active_cells(case), [
            "R1C1", "R1C2", "R1C4", "R2C1", "R2C2", "R2C4", "R4C1", "R4C2", "R4C4"
        ])

    def test_classic_sep_comb_canvas_does_not_scale_height_by_trace_count(self):
        two_groups = platform.plot_layout_metrics(["I(A)", "V(B)"])
        three_groups = platform.plot_layout_metrics(["V(A)", "P(B)", "I(C)"])
        four_groups = platform.plot_layout_metrics(["V(A)", "P(B)", "I(C)", "X(D)"])
        self.assertEqual([item["group_count"] for item in (two_groups, three_groups, four_groups)], [2, 3, 4])
        self.assertTrue(all(item["height_px"] is None and
                            item["height_mode"] == "classic_plotly_default"
                            for item in (two_groups, three_groups, four_groups)))
        self.assertTrue(all(item["width_mode"] == "responsive_full_width"
                            for item in (two_groups, three_groups, four_groups)))

    def _render_t1_array_case(self, clock_mode: str) -> dict:
        case, stimulus, t1 = platform.load_config()
        case.update({"CASE": f"T1_STATIC_{clock_mode}", "ROW_BITS": "1111", "COL_BITS": "1111",
                     "SE_ENABLE_MASK": "ALL", "OUTPUT_MODE": "DIAGONAL_T1_INDEPENDENT",
                     "T1_MODE": "ALL_INDEPENDENT", "T1_CLK_MODE": clock_mode,
                     "CBU_MODE": "OFF", "CARRY_MODE": "NONE",
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

    def test_user_case_clock_mode_overrides_t1_params_default(self):
        quiet_case, _stimulus, quiet_t1 = platform.load_config()
        pulse_case, _stimulus, pulse_t1 = platform.load_config(sets=["T1_CLK_MODE=PULSE"])
        configured_mode = platform.parse_env(platform.USER_CASE)["T1_CLK_MODE"]
        self.assertEqual(quiet_case["T1_CLK_MODE"], configured_mode)
        self.assertEqual(quiet_t1["T1_CLK_MODE"], configured_mode)
        self.assertEqual(pulse_case["T1_CLK_MODE"], "PULSE")
        self.assertEqual(pulse_t1["T1_CLK_MODE"], "PULSE")

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

    def test_t1_mode_fails_closed_without_t1_probe_profile(self):
        case, stimulus, t1 = platform.load_config()
        case.update({"OUTPUT_MODE": "DIAGONAL_T1_INDEPENDENT", "T1_MODE": "ALL_INDEPENDENT",
                     "CBU_MODE": "OFF", "CARRY_MODE": "NONE", "PROBE_PROFILE": "focus"})
        with self.assertRaisesRegex(platform.ConfigError, "requires PROBE_PROFILE=t1_array_focus"):
            platform.validate_config(case, stimulus, t1)

    def test_chain_default_render_is_seven_t1_six_physical_cbu_jtl_and_dff(self):
        case, stimulus, params = platform.load_config("CHAIN_ALL_GLOBAL_CLOCK")
        rendered = platform.render(case, stimulus, params, platform.RUNS / "_TEST_CHAIN")
        deck = rendered["deck"].splitlines()
        self.assertEqual(len([line for line in deck if line.startswith("XT1_D")]), 7)
        self.assertEqual(len([line for line in deck if line.startswith("XCBU_D")]), 6)
        self.assertEqual(len([line for line in deck if line.startswith("XJTL_D0_")]), 1)
        self.assertEqual(len([line for line in deck if line.startswith("XDFF ")]), 1)
        self.assertFalse(any(line.startswith("R_TERM_D") for line in deck))
        self.assertFalse(any(line.startswith("R_C_D") for line in deck))
        self.assertEqual(len([line for line in deck if line.startswith("R_S_D")]), 7)
        for index in range(1, 7):
            self.assertIn(f"V_CBU_A_D{index} DOUT_D{index} CBU_A_D{index} 0", deck)
            self.assertIn(f"V_CBU_B_D{index} C_D{index-1} CBU_B_D{index} 0", deck)
            self.assertIn(f"XCBU_D{index} CBU_A_D{index} CBU_B_D{index} CBU_OUT_D{index} THmitll_MERGE", deck)
            self.assertIn(f"V_T1_LINK_D{index} CBU_OUT_D{index} T1_I_D{index} 0", deck)
        self.assertIn("V_DFF_DATA C_D6 DFF_IN 0", deck)
        self.assertIn("XDFF DFF_IN CLK_DFF DFF_O THmitll_DFF", deck)
        self.assertEqual(rendered["static_qa"]["status"], "PASS")
        self.assertEqual((rendered["static_qa"]["t1_count"], rendered["static_qa"]["cbu_count"],
                          rendered["static_qa"]["d0_jtl_count"], rendered["static_qa"]["dff_count"]),
                         (7, 6, 1, 1))
        self.assertEqual(rendered["static_qa"]["terminal_count"], 0)
        self.assertLess(rendered["static_qa"]["raw_estimate_bytes"], platform.MAX_RAW_BYTES)

    def test_default_cbu_override_preserves_a021_a022_deck_bytes(self):
        expected = {
            "CHAIN_ALL_GLOBAL_CLOCK": "678b08e181ecaba8b96b81f2798dc949309c76e3f14ead7ea2b7773bb0369364",
            "CHAIN_PAPER_GLOBAL_CLOCK": "678b08e181ecaba8b96b81f2798dc949309c76e3f14ead7ea2b7773bb0369364",
        }
        for preset, digest in expected.items():
            case, stimulus, params, output = rendered(preset)
            self.assertEqual(case["CBU_OVERRIDE_D1"], "NONE")
            self.assertEqual(hashlib.sha256(output["deck"].encode("utf-8")).hexdigest(), digest)
            self.assertEqual(output["static_qa"]["status"], "PASS")

    def test_cb_direct_d1_uses_exact_shared_node_sensor_and_canonical_cb_ports(self):
        case, _stimulus, _params, output = rendered("CB_DIRECT_D1_ALL_CLOCK")
        deck = output["deck"].splitlines()
        self.assertEqual(case["CBU_TYPE"], "THmitll_MERGE")
        self.assertEqual(case["CBU_OVERRIDE_D1"], "CB_DIRECT")
        self.assertEqual(sum(line.startswith("XCBU_D1 ") for line in deck), 1)
        self.assertIn("V_CBU_A_D1 DOUT_D1 CBU_JOIN_D1 0", deck)
        self.assertIn("V_CBU_B_D1 C_D0 CBU_JOIN_D1 0", deck)
        self.assertIn("XCBU_D1 CBU_JOIN_D1 CBU_OUT_D1 CB", deck)
        self.assertIn("V_T1_LINK_D1 CBU_OUT_D1 T1_I_D1 0", deck)
        self.assertFalse(any(line.startswith("XCBU_D1 ") and line.endswith("THmitll_MERGE") for line in deck))
        for index in range(2, 7):
            self.assertIn(f"XCBU_D{index} CBU_A_D{index} CBU_B_D{index} CBU_OUT_D{index} THmitll_MERGE", deck)
        self.assertEqual(sum(line.startswith("XSJTL_D1_") for line in deck), 2)
        self.assertFalse(any(line.startswith("XSJTL_CBU_D1") for line in deck))
        self.assertEqual(platform.subckt_pins(platform.REPO / platform.SOURCE_PATHS["CB"], "CB"),
                         ("IN", "OUT"))
        probes = {item["label"] for item in output["probes"]["signals"]}
        for label in ("V(DOUT_D1)", "P(BJ1|XCB_D1_L2)", "V(BJ1|XCB_D1_L2)",
                      "V(C_D0)", "P(B_J11|XT1_D0)", "V(B_J11|XT1_D0)",
                      "V(CBU_JOIN_D1)", "I(V_CBU_A_D1)", "I(V_CBU_B_D1)",
                      "P(BJ1|XCBU_D1)", "V(BJ1|XCBU_D1)",
                      "P(BJ2|XCBU_D1)", "V(BJ2|XCBU_D1)", "V(CBU_OUT_D1)",
                      "I(V_T1_LINK_D1)", "V(T1_I_D1)", "P(B_J1|XT1_D1)",
                      "P(B_J9|XT1_D1)", "P(B_J10|XT1_D1)", "P(B_J11|XT1_D1)",
                      "V(S_D1)", "V(C_D1)", "V(CLK_D1)"):
            self.assertIn(label, probes)
        page_signals = {label for page in platform.plot_signals(output["probes"]) for label in page["signals"]}
        self.assertIn("V(CBU_JOIN_D1)", page_signals)
        self.assertIn("P(BJ2|XCBU_D1)", page_signals)
        self.assertEqual(output["topology"]["cbu_type_by_stage"]["D1"], "CB")
        self.assertEqual(output["topology"]["cbu_type_by_stage"]["D2"], "THmitll_MERGE")
        self.assertEqual(output["static_qa"]["status"], "PASS")

    def test_cb_carry_buffer_d1_uses_canonical_cb_only_on_carry_branch(self):
        case, stimulus, params, output = rendered("CARRY_CB_D1_ALL_CLOCK")
        deck = output["deck"].splitlines()
        expected = {
            "V_CBU_A_D1 DOUT_D1 CBU_JOIN_D1 0",
            "V_CARRY_IN_D1 C_D0 CARRY_CB_IN_D1 0",
            "XCB_CARRY_D1 CARRY_CB_IN_D1 CARRY_CB_OUT_D1 CB",
            "V_CBU_B_D1 CARRY_CB_OUT_D1 CBU_JOIN_D1 0",
            "V_T1_LINK_D1 CBU_JOIN_D1 T1_I_D1 0",
        }
        self.assertTrue(expected.issubset(set(deck)))
        self.assertFalse(any(line.startswith("XCBU_D1 ") for line in deck))
        self.assertEqual(len([line for line in deck if line.startswith("XCB_CARRY_D1 ")]), 1)
        self.assertFalse(any(line.startswith(("XSJTL_CBU_D1", "XJTL_CBU_D1")) for line in deck))
        self.assertIn("V_CARRY_IN_D1 C_D0 CARRY_CB_IN_D1 0", deck)
        self.assertIn("XCB_CARRY_D1 CARRY_CB_IN_D1 CARRY_CB_OUT_D1 CB", deck)
        self.assertIn("V_CBU_B_D1 CARRY_CB_OUT_D1 CBU_JOIN_D1 0", deck)
        self.assertEqual(sum("CBU_JOIN_D1" in line for line in deck
                             if not line.startswith(("*", ".print"))), 3)
        self.assertEqual(platform.subckt_pins(platform.REPO / platform.SOURCE_PATHS["CB"], "CB"),
                         ("IN", "OUT"))
        self.assertEqual(output["sources"]["CBU_D1_CARRY_BUFFER"]["sha256"],
                         platform.SOURCE_SHA256["CB"])
        self.assertEqual(output["topology"]["cbu_type_by_stage"]["D1"], "CB_CARRY_BUFFER")
        self.assertEqual(output["topology"]["cbu_type_by_stage"]["D2"], "THmitll_MERGE")
        self.assertFalse(any(line.startswith("R_TERM_D") or line.startswith("R_C_D") for line in deck))
        self.assertIn("XJTL_D0_1 D0_JTL_IN_1 D0_JTL_OUT_1 D0_JTL", deck)
        self.assertIn("V_DFF_DATA C_D6 DFF_IN 0", deck)
        self.assertEqual(output["static_qa"]["status"], "PASS")
        self.assertLess(output["static_qa"]["raw_estimate_bytes"], platform.MAX_RAW_BYTES)
        self.assertEqual(case["DT"], "0.01p")
        self.assertEqual(case["STOP"], "300p")
        self.assertEqual(params["T1_CLK_SERIES_R"], "2")

        labels = {item["label"] for item in output["probes"]["signals"]}
        for label in (
                "V(C_D0)", "P(B_J1|XT1_D0)", "V(B_J11|XT1_D0)",
                "V(CARRY_CB_IN_D1)", "I(V_CARRY_IN_D1)",
                "P(BJ1|XCB_CARRY_D1)", "V(BJ2|XCB_CARRY_D1)",
                "V(CARRY_CB_OUT_D1)", "I(V_CBU_B_D1)", "V(CBU_JOIN_D1)",
                "I(V_CBU_A_D1)", "P(BJ2|XCB_D1_L2)", "V(T1_I_D1)",
                "P(B_J1|XT1_D1)", "V(B_J11|XT1_D1)", "V(S_D1)",
                "V(C_D1)", "V(CLK_D1)", "V(T1_I_D2)", "V(C_D2)"):
            self.assertIn(label, labels)
        for diagonal in ("D2", "D3", "D4", "D5", "D6"):
            self.assertNotIn(f"P(B_J1|XT1_{diagonal})", labels)
            self.assertIn(f"V(T1_I_{diagonal})", labels)

        pages = platform.plot_signals(output["probes"])
        self.assertEqual([page["file"] for page in pages], [
            "01_full_chain_overview.html", "02_carry_propagation.html", "03_stage_focus.html"])
        self.assertIn("V(CARRY_CB_OUT_D1)", pages[1]["signals"])
        self.assertIn("P(BJ1|XCB_CARRY_D1)", pages[2]["signals"])

    def test_cb_carry_buffer_can_be_selected_with_set_and_preserves_paper_mask(self):
        case, _stimulus, _params, output = rendered_with_set(
            "CHAIN_PAPER_GLOBAL_CLOCK", "CBU_OVERRIDE_D1=CB_CARRY_BUFFER")
        self.assertEqual(case["ROW_BITS"], "1101")
        self.assertEqual(case["COL_BITS"], "1101")
        self.assertIn("XCB_CARRY_D1 CARRY_CB_IN_D1 CARRY_CB_OUT_D1 CB", output["deck"].splitlines())
        self.assertEqual(output["static_qa"]["status"], "PASS")

    def test_carry_buffer_presets_match_a021_a022_except_registered_case_and_d1_override(self):
        pairs = (("CHAIN_ALL_GLOBAL_CLOCK", "CARRY_CB_D1_ALL_CLOCK", "1111"),
                 ("CHAIN_PAPER_GLOBAL_CLOCK", "CARRY_CB_D1_PAPER_CLOCK", "1101"))
        for baseline_name, candidate_name, bits in pairs:
            base, base_stim, base_params, base_render = rendered(baseline_name)
            cand, cand_stim, cand_params, cand_render = rendered(candidate_name)
            allowed = {"CASE", "CBU_OVERRIDE_D1", "FOCUS_STAGE"}
            diffs = {key for key in base if base.get(key) != cand.get(key)}
            self.assertLessEqual(diffs, allowed)
            self.assertEqual(cand["ROW_BITS"], bits)
            self.assertEqual(cand["COL_BITS"], bits)
            self.assertEqual(base_stim, cand_stim)
            self.assertEqual(base_params, cand_params)
            self.assertEqual(base_render["stimulus_text"], cand_render["stimulus_text"])
            self.assertEqual(cand["T1_CHAIN_CLOCK_START"] if "T1_CHAIN_CLOCK_START" in cand else
                             cand["T1_CHAIN_CLK_START"], "200p")
            self.assertEqual(cand["DT"], "0.01p")
            self.assertEqual(cand["STOP"], "300p")

    def test_cb_carry_buffer_all_wires_six_isolated_stages_and_captures_full_chain(self):
        case, _stimulus, _params, output = rendered("FULL_CB_CHAIN_ALL_CLOCK")
        deck = output["deck"].splitlines()
        expected_carry = set()
        for index in range(1, 7):
            expected_carry.update({
                f"V_CBU_A_D{index} DOUT_D{index} CBU_JOIN_D{index} 0",
                f"V_CARRY_IN_D{index} C_D{index-1} CARRY_CB_IN_D{index} 0",
                f"XCB_CARRY_D{index} CARRY_CB_IN_D{index} CARRY_CB_OUT_D{index} CB",
                f"V_CBU_B_D{index} CARRY_CB_OUT_D{index} CBU_JOIN_D{index} 0",
                f"V_T1_LINK_D{index} CBU_JOIN_D{index} T1_I_D{index} 0",
            })
        self.assertTrue(expected_carry.issubset(set(deck)))
        self.assertEqual(len([line for line in deck if line.startswith("XCB_CARRY_D")]), 6)
        self.assertFalse(any(line.startswith("XCBU_D") for line in deck))
        self.assertFalse(any(line.startswith(("XJTL_CBU_D", "XSJTL_CBU_D")) for line in deck))
        self.assertFalse(any(line.startswith(("R_TERM_D", "R_C_D")) for line in deck))
        self.assertEqual(len([line for line in deck if line.startswith("XBVM_")]), 16)
        self.assertEqual(len([line for line in deck if line.startswith("XBQ_")]), 16)
        self.assertEqual(len([line for line in deck if line.startswith("XCB_D")]), 16)
        self.assertEqual(len([line for line in deck if line.startswith("XSJTL_")]), 20)
        self.assertEqual(len([line for line in deck if line.startswith("XT1_D")]), 7)
        self.assertEqual(len([line for line in deck if line.startswith("XDFF ")]), 1)
        self.assertIn("XJTL_D0_1 D0_JTL_IN_1 D0_JTL_OUT_1 D0_JTL", deck)
        self.assertIn("V_DFF_DATA C_D6 DFF_IN 0", deck)
        self.assertEqual(output["static_qa"]["status"], "PASS")
        self.assertEqual(output["static_qa"]["cbu_carry_buffer_count"], 6)
        self.assertTrue(output["static_qa"]["cbu_carry_buffer_all"])
        self.assertLess(output["static_qa"]["raw_estimate_bytes"], platform.MAX_RAW_BYTES)
        self.assertEqual(output["topology"]["cbu_type_by_stage"], {
            f"D{index}": "CB_CARRY_BUFFER" for index in range(1, 7)})
        self.assertEqual(output["topology"]["carry_links"], {
            "C_D0": "V_CARRY_IN_D1 -> XCB_CARRY_D1 -> V_CBU_B_D1 -> CBU_JOIN_D1",
            "C_D1": "V_CARRY_IN_D2 -> XCB_CARRY_D2 -> V_CBU_B_D2 -> CBU_JOIN_D2",
            "C_D2": "V_CARRY_IN_D3 -> XCB_CARRY_D3 -> V_CBU_B_D3 -> CBU_JOIN_D3",
            "C_D3": "V_CARRY_IN_D4 -> XCB_CARRY_D4 -> V_CBU_B_D4 -> CBU_JOIN_D4",
            "C_D4": "V_CARRY_IN_D5 -> XCB_CARRY_D5 -> V_CBU_B_D5 -> CBU_JOIN_D5",
            "C_D5": "V_CARRY_IN_D6 -> XCB_CARRY_D6 -> V_CBU_B_D6 -> CBU_JOIN_D6",
            "C_D6": "DFF_IN"})

        labels = {item["label"] for item in output["probes"]["signals"]}
        for diagonal, cells in platform.DIAGONALS.items():
            array_cb = f"XCB_{diagonal}_L{len(cells)}"
            self.assertIn(f"P(BJ1|{array_cb})", labels)
            self.assertIn(f"V(BJ1|{array_cb})", labels)
        for index in range(1, 7):
            instance = f"XCB_CARRY_D{index}"
            for label in (f"V(DOUT_D{index})", f"V(C_D{index-1})",
                          f"V(CARRY_CB_IN_D{index})", f"V(CARRY_CB_OUT_D{index})",
                          f"V(CBU_JOIN_D{index})", f"I(V_CBU_A_D{index})",
                          f"I(V_CARRY_IN_D{index})", f"I(V_CBU_B_D{index})",
                          f"I(V_T1_LINK_D{index})", f"P(BJ1|{instance})", f"V(BJ1|{instance})",
                          f"P(BJ2|{instance})", f"V(BJ2|{instance})"):
                self.assertIn(label, labels)
        for diagonal in platform.DIAGONALS:
            self.assertIn(f"P(B_J11|XT1_{diagonal})", labels)
            self.assertIn(f"V(B_J11|XT1_{diagonal})", labels)
            self.assertIn(f"V(CLK_{diagonal})", labels)
        for label in ("V(DFF_IN)", "V(CLK_DFF)", "V(DFF_O)",
                      "P(B1|XDFF)", "V(B1|XDFF)", "I(V_DFF_DATA)"):
            self.assertIn(label, labels)
        pages = platform.plot_signals(output["probes"])
        self.assertEqual([page["file"] for page in pages], [
            "01_full_chain_overview.html", "02_carry_propagation.html",
            "03_stage_D1_focus.html", "04_stage_D2_focus.html", "05_stage_D3_focus.html",
            "06_stage_D4_focus.html", "07_stage_D5_focus.html", "08_stage_D6_focus.html"])

    def test_cb_carry_buffer_all_three_masks_match_existing_diagonal_map_and_fail_closed(self):
        expected = {
            "FULL_CB_CHAIN_ALL_CLOCK": ("1111", "1111", [1, 2, 3, 4, 3, 2, 1]),
            "FULL_CB_CHAIN_PAPER_CLOCK": ("1101", "1101", [1, 1, 1, 3, 1, 1, 1]),
            "FULL_CB_CHAIN_3X3_CLOCK": ("1100", "0011", [1, 2, 1, 0, 0, 0, 0]),
        }
        for preset, (rows, cols, counts) in expected.items():
            case, _stimulus, _params, output = rendered(preset)
            actual = [sum(cell in platform._active_cells(case) for cell in group)
                      for group in platform.DIAGONALS.values()]
            self.assertEqual((case["ROW_BITS"], case["COL_BITS"]), (rows, cols))
            self.assertEqual(actual, counts)
            self.assertEqual(case["CBU_CHAIN_TOPOLOGY"], "CB_CARRY_BUFFER_ALL")
            self.assertEqual(case["CBU_OVERRIDE_D1"], "NONE")
            self.assertEqual(output["static_qa"]["status"], "PASS")
        with self.assertRaisesRegex(platform.ConfigError, "CBU_OVERRIDE_D1=NONE"):
            platform.load_config("FULL_CB_CHAIN_ALL_CLOCK", ["CBU_OVERRIDE_D1=CB_DIRECT"])

    def test_cbu_override_d1_is_selectable_by_set_and_rejects_unknown_values(self):
        case, _stimulus, _params, output = rendered_with_set(
            "CHAIN_ALL_GLOBAL_CLOCK", "CBU_OVERRIDE_D1=CB_DIRECT")
        self.assertIn("XCBU_D1 CBU_JOIN_D1 CBU_OUT_D1 CB", output["deck"].splitlines())
        with self.assertRaisesRegex(platform.ConfigError, "CBU_OVERRIDE_D1"):
            platform.load_config("CHAIN_ALL_GLOBAL_CLOCK", ["CBU_OVERRIDE_D1=INVALID"])

    def test_cb_direct_batch_locks_candidate_deck_not_merge_baseline_deck(self):
        _case, _stimulus, _params, output = rendered("CB_DIRECT_D1_ALL_CLOCK")
        rendered_deck_sha = hashlib.sha256(output["deck"].encode("utf-8")).hexdigest()
        rendered_stim_sha = hashlib.sha256(output["stimulus_text"].encode("utf-8")).hexdigest()
        probe_sha = hashlib.sha256((platform.json.dumps(output["probes"], ensure_ascii=False, indent=2)+"\n").encode()).hexdigest()
        locked_candidate = {"deck_sha256": rendered_deck_sha, "stimulus_sha256": rendered_stim_sha,
                           "probe_sha256": probe_sha}
        self.assertNotEqual(rendered_deck_sha,
                            "678b08e181ecaba8b96b81f2798dc949309c76e3f14ead7ea2b7773bb0369364")
        self.assertEqual(cb_batch._render_lock_mismatches(output, locked_candidate, output["probes"]), [])
        wrong_baseline_lock = {**locked_candidate,
                               "deck_sha256": "678b08e181ecaba8b96b81f2798dc949309c76e3f14ead7ea2b7773bb0369364"}
        self.assertIn("candidate deck", "; ".join(
            cb_batch._render_lock_mismatches(output, wrong_baseline_lock, output["probes"])))

    def test_global_chain_clock_is_one_shot_on_eight_independent_branches(self):
        case, stimulus, params, rendered_output = rendered("CHAIN_ALL_GLOBAL_CLOCK")
        deck = rendered_output["deck"].splitlines()
        clock_sources = [line for line in deck if line.startswith("V_TRIG_CLK_")]
        series = [line for line in deck if line.startswith("R_TRIG_CLK_")]
        self.assertEqual(len(clock_sources), 8)
        self.assertEqual(len(series), 8)
        self.assertEqual(len({line.split("PWL(", 1)[1] for line in clock_sources}), 1)
        self.assertTrue(all("PWL(0p 0 200p 0 201p 1.2m 203p 1.2m 204p 0)" in line
                            for line in clock_sources))
        self.assertFalse(any("PULSE(" in line for line in clock_sources))
        self.assertFalse(any(line.startswith("R_CLK_QUIET_") for line in deck))
        self.assertEqual(rendered_output["static_qa"]["clock_driver_count"], 8)
        self.assertEqual(rendered_output["static_qa"]["pulse_clock_count"], 8)

    def test_quiet_chain_clamps_all_eight_clock_inputs_and_has_no_pulse_source(self):
        case, stimulus, params, output = rendered("CHAIN_ALL_QUIET")
        deck = output["deck"].splitlines()
        clamps = [line for line in deck if line.startswith("R_CLK_QUIET_")]
        self.assertEqual(len(clamps), 8)
        self.assertTrue(all(line.endswith(" 5") for line in clamps))
        self.assertFalse(any(line.startswith(("V_TRIG_CLK_", "R_TRIG_CLK_")) for line in deck))
        self.assertEqual(output["static_qa"]["quiet_clock_count"], 8)

    def test_chain_probe_manifests_are_clock_mode_specific_and_complete(self):
        quiet = rendered("CHAIN_ALL_QUIET")[3]["probes"]
        global_clock = rendered("CHAIN_ALL_GLOBAL_CLOCK")[3]["probes"]
        quiet_labels = {item["label"] for item in quiet["signals"]}
        global_labels = {item["label"] for item in global_clock["signals"]}
        self.assertEqual(quiet["signal_count"], global_clock["signal_count"])
        self.assertIn("I(R_CLK_QUIET_D0)", quiet_labels)
        self.assertNotIn("I(R_TRIG_CLK_D0)", quiet_labels)
        self.assertIn("I(R_TRIG_CLK_D0)", global_labels)
        self.assertNotIn("I(R_CLK_QUIET_D0)", global_labels)
        for run_probes in (quiet, global_clock):
            self.assertIn("P(B_J11|XT1_D6)", {item["label"] for item in run_probes["signals"]})
            self.assertIn("I(V_CBU_B_D6)", {item["label"] for item in run_probes["signals"]})
            self.assertIn("I(R_DFF_OUT)", {item["label"] for item in run_probes["signals"]})

    def test_chain_local_candidate_sources_preserve_default_physical_bodies(self):
        case, stimulus, params, output = rendered("CHAIN_ALL_GLOBAL_CLOCK")
        info = output["chain_source_info"]
        self.assertTrue(info["CBU_RENDERED"]["default_body_equivalent_after_registered_syntax_fix"])
        self.assertEqual(info["CBU_RENDERED"]["syntax_replacements"], [
            {"before": "BiasCoef=0.7’", "after": "BiasCoef=0.7", "scope": "experiment-local source only"}])
        self.assertTrue(info["DFF_RENDERED"]["default_body_equivalent_after_registered_syntax_fix"])
        self.assertTrue(info["D0_JTL_RENDERED"]["canonical_sJTL_defaults_match"])
        self.assertNotIn(".model jjmit", output["chain_source_texts"]["sources/d0_jtl_tunable.cir"].lower())
        changed = rendered("CHAIN_ALL_GLOBAL_CLOCK", ["CBU_B1=2.6"])[3]
        self.assertIn(".param B1=2.6", changed["chain_source_texts"]["sources/cbu_tunable.cir"])

    def test_t1_dry_run_reports_actual_rendered_instance_count(self):
        case, stimulus, t1 = platform.load_config()
        case.update({"CASE": "T1_DRY_RUN_TEST", "ROW_BITS": "1111", "COL_BITS": "1111",
                     "SE_ENABLE_MASK": "ALL", "OUTPUT_MODE": "DIAGONAL_T1_INDEPENDENT",
                     "T1_MODE": "ALL_INDEPENDENT", "PROBE_PROFILE": "t1_array_focus"})
        import contextlib
        import io
        captured = io.StringIO()
        with contextlib.redirect_stdout(captured):
            status = platform.dry_run(case, stimulus, t1)
        self.assertEqual(status, 0)
        self.assertIn("T1 instances=7", captured.getvalue())
        self.assertNotIn("T1 instance=0", captured.getvalue())

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
