from __future__ import annotations

import contextlib
import csv
import hashlib
import io
import json
import sys
import tempfile
import unittest
import zipfile
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

SERIES = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERIES / "scripts"))

import run_platform as platform  # noqa: E402
import build_batch_comparison as batch_compare  # noqa: E402

OPTIONAL_E_CASE_FIELDS = {
    "SECOND_READ_ENABLE", "SECOND_ROW_BITS", "SECOND_COL_BITS",
}


def render(preset: str | None = None):
    case, stimulus = platform.load_config(preset)
    preview_run = SERIES / "runs" / "A999_PREVIEW_ONLY"
    return case, stimulus, platform.render(case, stimulus, preview_run)


def parse_pwl_sources(stimulus_text: str):
    parsed = {}
    for line in stimulus_text.splitlines():
        if not line.startswith("I_"):
            continue
        source, _ground, node, expression = line.split(maxsplit=3)
        body = expression.removeprefix("PWL(").removesuffix(")")
        tokens = body.split()
        points = [(platform.quantity(tokens[index], f"{source} time"),
                   tokens[index + 1]) for index in range(0, len(tokens), 2)]
        parsed[source] = {"node": node, "points": points}
    return parsed


class RowColumnPlatformTests(unittest.TestCase):
    def test_frozen_sources_and_port_orders_match_canonical(self):
        sources = platform.verify_sources()
        self.assertEqual(platform.parse_subckt("BVM"), ("WL", "BL", "SE", "SL"))
        self.assertEqual(platform.parse_subckt("QB"), ("IN", "OUT"))
        self.assertEqual(platform.parse_subckt("SJTL"), ("IN", "OUT"))
        self.assertEqual(platform.parse_subckt("POST_CB"), ("IN", "OUT"))
        self.assertEqual(sources["BVM"]["sha256"], platform.SOURCE_SHA256["BVM"])

    def test_preset_effective_crosspoints_and_driver_counts(self):
        cases = (
            ("A_INDEPENDENT_10_10", "INDEPENDENT", ["R1C1"], ["R1C2", "R2C1"], ["R2C2"], 12, "100u"),
            ("B_SHARED_10_10", "SHARED", ["R1C1"], ["R1C2", "R2C1"], ["R2C2"], 6, "200u"),
            ("C_SHARED_11_11", "SHARED", ["R1C1", "R1C2", "R2C1", "R2C2"], [], [], 6, "200u"),
        )
        for preset, mode, active, half, unselected, driver_count, amplitude in cases:
            with self.subTest(preset=preset):
                case, _stimulus, rendered = render(preset)
                topology = rendered["topology"]
                self.assertEqual(case["DRIVE_MODE"], mode)
                self.assertEqual(topology["cell_selection"]["active_crosspoints"], active)
                self.assertEqual(topology["cell_selection"]["half_selected"], half)
                self.assertEqual(topology["cell_selection"]["unselected"], unselected)
                self.assertEqual(topology["driver_count"], driver_count)
                self.assertEqual(case["ROW_WL_READ_AMPLITUDE"], amplitude)
                self.assertEqual(len(topology["cell_instances"]), 4)

    def test_existing_presets_keep_se_behavior_and_second_read_defaults_off(self):
        for preset, mode, se_topology, gate_mode, count in (
            ("A_INDEPENDENT_10_10", "INDEPENDENT", "SHARED_COLUMN", "COLUMN", 12),
            ("B_SHARED_10_10", "SHARED", "SHARED_COLUMN", "COLUMN", 6),
            ("C_SHARED_11_11", "SHARED", "SHARED_COLUMN", "COLUMN", 6),
            ("D0_CELL_SE_COLUMN_10_10", "SHARED", "CELL", "COLUMN", 8),
            ("D1_CELL_SE_CROSSPOINT_10_10", "SHARED", "CELL", "CROSSPOINT", 8),
        ):
            with self.subTest(preset=preset):
                case, _stimulus, rendered = render(preset)
                self.assertEqual(case["SE_TOPOLOGY"], se_topology)
                self.assertEqual(case["SE_GATE_MODE"], gate_mode)
                self.assertEqual(case["SECOND_READ_ENABLE"], "0")
                self.assertEqual(rendered["topology"]["driver_count"], count)
                self.assertEqual(rendered["static_qa"]["status"], "PASS")

    def test_legacy_user_case_missing_new_keys_loads_with_compatibility_defaults(self):
        legacy_case = SERIES / "runs/A001_INDEPENDENT_R10_C10/USER_CASE.snapshot.env"
        with patch.object(platform, "USER_CASE", legacy_case):
            case, _stimulus = platform.load_config()
        self.assertEqual(case["SE_TOPOLOGY"], "SHARED_COLUMN")
        self.assertEqual(case["SE_GATE_MODE"], "COLUMN")
        self.assertEqual(case["SECOND_READ_ENABLE"], "0")
        self.assertEqual(case["DRIVE_MODE"], "INDEPENDENT")

    def test_legacy_run_snapshots_render_byte_identically(self):
        run_ids = (
            "A001_INDEPENDENT_R10_C10",
            "A002_SHARED_R10_C10",
            "A003_SHARED_R10_C10",
            "A004_SHARED_R10_C10",
            "A005_SHARED_R10_C10",
            "A006_SHARED_R10_C10",
            "A007_SHARED_R10_C10",
            "A008_SHARED_R10_C10",
            "A009_SHARED_R10_C11",
        )
        for run_id in run_ids:
            with self.subTest(run_id=run_id):
                run_dir = SERIES / "runs" / run_id
                case = platform.parse_env(run_dir / "USER_CASE.snapshot.env", platform.CASE_KEYS)
                case = platform._with_se_defaults(case)
                case = platform._with_second_read_defaults(case)
                case = platform._with_write_sequence_defaults(case)
                stimulus = platform.parse_env(run_dir / "STIMULUS.snapshot.env",
                                              platform.STIMULUS_KEYS,
                                              required=platform.BASE_STIMULUS_KEYS)
                platform.validate_config(case, stimulus)
                rendered = platform.render(case, stimulus, run_dir)
                self.assertEqual(rendered["deck"], (run_dir / "actual_deck.cir").read_text())
                self.assertEqual(rendered["stimulus_text"], (run_dir / "stimulus.inc").read_text())

    def test_cell_se_topology_is_four_real_nodes_with_exact_bvm_wiring(self):
        case0, _stimulus0, d0 = render("D0_CELL_SE_COLUMN_10_10")
        case1, _stimulus1, d1 = render("D1_CELL_SE_CROSSPOINT_10_10")
        expected_instances = {
            "XBVM_R1C1 WL_R1 BL_C1 SE_R1C1 SL_R1C1 BVM",
            "XBVM_R1C2 WL_R1 BL_C2 SE_R1C2 SL_R1C2 BVM",
            "XBVM_R2C1 WL_R2 BL_C1 SE_R2C1 SL_R2C1 BVM",
            "XBVM_R2C2 WL_R2 BL_C2 SE_R2C2 SL_R2C2 BVM",
        }
        for case, rendered in ((case0, d0), (case1, d1)):
            topology = rendered["topology"]
            self.assertEqual(case["ROW_BITS"], "10")
            self.assertEqual(case["COL_BITS"], "10")
            self.assertEqual(case["DRIVE_MODE"], "SHARED")
            self.assertEqual(topology["driver_count"], 8)
            self.assertEqual(topology["driver_count_by_branch"], {"WL": 2, "BL": 2, "SE": 4})
            self.assertEqual(topology["shared_nodes"], {
                "WL": {"ROW1": "WL_R1", "ROW2": "WL_R2"},
                "BL": {"COL1": "BL_C1", "COL2": "BL_C2"},
            })
            se_drivers = [item for item in topology["input_lines"] if item["branch"] == "SE"]
            self.assertEqual({item["node"] for item in se_drivers},
                             {"SE_R1C1", "SE_R1C2", "SE_R2C1", "SE_R2C2"})
            self.assertEqual({item["source"] for item in se_drivers},
                             {"I_SE_R1C1", "I_SE_R1C2", "I_SE_R2C1", "I_SE_R2C2"})
            actual_bvm = {line for line in rendered["deck"].splitlines() if line.startswith("XBVM_")}
            self.assertEqual(actual_bvm, expected_instances)
            self.assertEqual(rendered["deck"].splitlines().count(".include stimulus.inc"), 1)
            self.assertNotIn("SE_C1", rendered["deck"])
            self.assertNotIn("SE_C2", rendered["deck"])
            self.assertEqual(len([line for line in rendered["drive_lines"] if line.startswith("I_")]), 8)
            self.assertEqual(rendered["static_qa"]["cell_se_nodes_independent"], True)
            self.assertEqual(rendered["static_qa"]["physical_solve_count"], 0)
            probe_labels = {item["label"] for item in rendered["probes"]["signals"]}
            for source, node in (("I_SE_R1C1", "SE_R1C1"), ("I_SE_R1C2", "SE_R1C2"),
                                 ("I_SE_R2C1", "SE_R2C1"), ("I_SE_R2C2", "SE_R2C2")):
                self.assertIn(f"I({source})", probe_labels)
                self.assertIn(f"V({node})", probe_labels)

    def test_d0_d1_preparation_matches_and_only_r2c1_final_se_changes(self):
        case0, _stimulus, d0 = render("D0_CELL_SE_COLUMN_10_10")
        case1, _stimulus, d1 = render("D1_CELL_SE_CROSSPOINT_10_10")
        self.assertEqual({key: value for key, value in case0.items() if key != "SE_GATE_MODE"},
                         {key: value for key, value in case1.items() if key != "SE_GATE_MODE"})
        expected_common = {
            "I_WL_R1": {"WRITE0": "-200u", "READ0": "200u", "WRITE1": "200u", "FINAL_READ": "200u"},
            "I_WL_R2": {"WRITE0": "-200u", "READ0": "200u", "WRITE1": "200u", "FINAL_READ": "0"},
            "I_BL_C1": {"WRITE0": "-200u", "READ0": "0", "WRITE1": "200u", "FINAL_READ": "0"},
            "I_BL_C2": {"WRITE0": "-200u", "READ0": "0", "WRITE1": "200u", "FINAL_READ": "0"},
            "I_SE_R1C1": {"WRITE0": "0", "READ0": "100u", "WRITE1": "0", "FINAL_READ": "100u"},
            "I_SE_R1C2": {"WRITE0": "0", "READ0": "100u", "WRITE1": "0", "FINAL_READ": "0"},
            "I_SE_R2C2": {"WRITE0": "0", "READ0": "100u", "WRITE1": "0", "FINAL_READ": "0"},
        }
        for source, phases in expected_common.items():
            self.assertEqual(d0["driver_stages"][source], phases)
            self.assertEqual(d1["driver_stages"][source], phases)
        self.assertEqual(d0["driver_stages"]["I_SE_R2C1"],
                         {"WRITE0": "0", "READ0": "100u", "WRITE1": "0", "FINAL_READ": "100u"})
        self.assertEqual(d1["driver_stages"]["I_SE_R2C1"],
                         {"WRITE0": "0", "READ0": "100u", "WRITE1": "0", "FINAL_READ": "0"})
        self.assertEqual(
            {source for source in d0["driver_stages"]
             if d0["driver_stages"][source] != d1["driver_stages"][source]},
            {"I_SE_R2C1"})
        d0_pwl = {line.split()[0]: line for line in d0["stimulus_text"].splitlines()
                  if line.startswith("I_")}
        d1_pwl = {line.split()[0]: line for line in d1["stimulus_text"].splitlines()
                  if line.startswith("I_")}
        self.assertEqual(set(d0_pwl), set(d1_pwl))
        self.assertEqual({source for source in d0_pwl if d0_pwl[source] != d1_pwl[source]},
                         {"I_SE_R2C1"})
        self.assertEqual(
            d0_pwl["I_SE_R2C1"],
            "I_SE_R2C1 0 SE_R2C1 PWL(0 0 50p 0 51p 0 60p 0 61p 0 "
            "70p 0 71p 100u 80p 100u 81p 0 90p 0 91p 0 100p 0 101p 0 "
            "110p 0 111p 100u 120p 100u 121p 0 250p 0)")
        self.assertEqual(
            d1_pwl["I_SE_R2C1"],
            "I_SE_R2C1 0 SE_R2C1 PWL(0 0 50p 0 51p 0 60p 0 61p 0 "
            "70p 0 71p 100u 80p 100u 81p 0 90p 0 91p 0 100p 0 101p 0 "
            "110p 0 111p 0 120p 0 121p 0 250p 0)")
        self.assertIn(
            "I_WL_R1 0 WL_R1 PWL(0 0 50p 0 51p -200u 60p -200u 61p 0 "
            "70p 0 71p 200u 80p 200u 81p 0 90p 0 91p 200u 100p 200u "
            "101p 0 110p 0 111p 200u 120p 200u 121p 0 250p 0)",
            d0["stimulus_text"])
        self.assertEqual(d0["deck"], d1["deck"])
        self.assertEqual(d0["topology"]["se_configuration"]["final_read_enabled_by_cell"],
                         {"R1C1": True, "R1C2": False, "R2C1": True, "R2C2": False})
        self.assertEqual(d1["topology"]["se_configuration"]["final_read_enabled_by_cell"],
                         {"R1C1": True, "R1C2": False, "R2C1": False, "R2C2": False})
        self.assertEqual(d0["sources"], d1["sources"])
        self.assertEqual({role: item["sha256"] for role, item in d0["sources"].items()},
                         platform.SOURCE_SHA256)

    def test_second_read_defaults_off_preserve_historical_a001_a006_decks(self):
        for run_id in ("A001_INDEPENDENT_R10_C10", "A002_SHARED_R10_C10",
                       "A003_SHARED_R10_C10", "A004_SHARED_R10_C10",
                       "A005_SHARED_R10_C10", "A006_SHARED_R10_C10"):
            with self.subTest(run_id=run_id):
                run_dir = SERIES / "runs" / run_id
                case = platform._with_second_read_defaults(
                    platform._with_se_defaults(
                        platform.parse_env(run_dir / "USER_CASE.snapshot.env", platform.CASE_KEYS)))
                case = platform._with_write_sequence_defaults(case)
                stimulus = platform.parse_env(run_dir / "STIMULUS.snapshot.env",
                                              platform.STIMULUS_KEYS,
                                              required=platform.BASE_STIMULUS_KEYS)
                platform.validate_config(case, stimulus)
                rendered = platform.render(case, stimulus, run_dir)
                self.assertEqual(case["SECOND_READ_ENABLE"], "0")
                self.assertNotIn("SECOND_READ", next(iter(rendered["driver_stages"].values())))
                self.assertEqual(rendered["deck"], (run_dir / "actual_deck.cir").read_text())
                self.assertEqual(rendered["stimulus_text"], (run_dir / "stimulus.inc").read_text())

    def test_e0_e1_second_read_is_fixed_cell_crosspoint_and_separate_from_first_gate(self):
        case0, stimulus0, e0 = render("E0_A005_CROSSPOINT_SECOND_READ")
        case1, stimulus1, e1 = render("E1_A006_COLUMN_SECOND_READ")
        for case, stimulus, rendered in ((case0, stimulus0, e0), (case1, stimulus1, e1)):
            self.assertEqual(case["DRIVE_MODE"], "SHARED")
            self.assertEqual(case["SE_TOPOLOGY"], "CELL")
            self.assertEqual(case["ROW_BITS"], "10")
            self.assertEqual(case["COL_BITS"], "10")
            self.assertEqual(case["SECOND_READ_ENABLE"], "1")
            self.assertEqual(case["SECOND_ROW_BITS"], "01")
            self.assertEqual(case["SECOND_COL_BITS"], "10")
            self.assertEqual(case["DT"], "0.01p")
            self.assertEqual(case["STOP"], "300p")
            self.assertEqual(len(rendered["drivers"]), 8)
            self.assertEqual(rendered["static_qa"]["status"], "PASS")
            self.assertEqual(rendered["static_qa"]["second_read_crosspoint_gate_exact"], True)
            self.assertEqual(
                {line for line in rendered["deck"].splitlines() if line.startswith("XBVM_")},
                {
                    "XBVM_R1C1 WL_R1 BL_C1 SE_R1C1 SL_R1C1 BVM",
                    "XBVM_R1C2 WL_R1 BL_C2 SE_R1C2 SL_R1C2 BVM",
                    "XBVM_R2C1 WL_R2 BL_C1 SE_R2C1 SL_R2C1 BVM",
                    "XBVM_R2C2 WL_R2 BL_C2 SE_R2C2 SL_R2C2 BVM",
                })
            self.assertEqual(rendered["topology"]["second_read"]["se_gate_mode"], "CELL_CROSSPOINT")
            self.assertEqual(rendered["topology"]["second_read"]["active_crosspoints"], ["R2C1"])
            self.assertEqual(
                rendered["topology"]["second_read"]["enabled_by_cell"],
                {"R1C1": False, "R1C2": False, "R2C1": True, "R2C2": False})
            self.assertEqual(rendered["driver_stages"]["I_WL_R1"]["SECOND_READ"], "0")
            self.assertEqual(rendered["driver_stages"]["I_WL_R2"]["SECOND_READ"], "200u")
            self.assertEqual(rendered["driver_stages"]["I_BL_C1"]["SECOND_READ"], "0")
            self.assertEqual(rendered["driver_stages"]["I_BL_C2"]["SECOND_READ"], "0")
            for source in ("I_SE_R1C1", "I_SE_R1C2", "I_SE_R2C2"):
                self.assertEqual(rendered["driver_stages"][source]["SECOND_READ"], "0")
            self.assertEqual(rendered["driver_stages"]["I_SE_R2C1"]["SECOND_READ"], "100u")

        self.assertEqual(case0["SE_GATE_MODE"], "CROSSPOINT")
        self.assertEqual(case1["SE_GATE_MODE"], "COLUMN")
        for key in case0.keys() - {"SE_GATE_MODE"}:
            self.assertEqual(case0[key], case1[key], key)
        self.assertEqual(stimulus0, stimulus1)
        self.assertEqual(e0["deck"], e1["deck"])
        self.assertEqual(e0["sources"], e1["sources"])
        self.assertEqual({role: item["sha256"] for role, item in e0["sources"].items()},
                         platform.SOURCE_SHA256)
        self.assertEqual(
            e0["driver_stages"]["I_SE_R2C1"]["FINAL_READ"], "0")
        self.assertEqual(
            e1["driver_stages"]["I_SE_R2C1"]["FINAL_READ"], "100u")
        expected_second_se = [
            (Decimal("170e-12"), "0"), (Decimal("171e-12"), "100u"),
            (Decimal("180e-12"), "100u"), (Decimal("181e-12"), "0")]
        expected_second_wl = [
            (Decimal("170e-12"), "0"), (Decimal("171e-12"), "200u"),
            (Decimal("180e-12"), "200u"), (Decimal("181e-12"), "0")]
        for rendered in (e0, e1):
            for source in rendered["driver_points"]:
                second_points = [(time, value) for time, value in rendered["driver_points"][source]
                                 if Decimal("170e-12") <= time <= Decimal("181e-12")]
                expected = (expected_second_se if source == "I_SE_R2C1" else
                            expected_second_wl if source == "I_WL_R2" else
                            [(time, "0") for time, _ in expected_second_se])
                self.assertEqual(second_points, expected, source)
                self.assertEqual(rendered["driver_points"][source][-1],
                                 (Decimal("300e-12"), "0"), source)
        self.assertEqual(
            {source for source in e0["driver_stages"]
             if e0["driver_stages"][source] != e1["driver_stages"][source]},
            {"I_SE_R2C1"})
        self.assertEqual(
            {source for source in e0["driver_stages"]
             if e0["driver_stages"][source]["SECOND_READ"] !=
             e1["driver_stages"][source]["SECOND_READ"]}, set())
        windows = platform._stage_windows(case0, stimulus0)
        expected_ps = {
            "FINAL_READ": (110, 121),
            "RECOVERY_BEFORE_SECOND_READ": (121, 170),
            "SECOND_READ": (170, 181),
            "POST_SECOND_READ": (181, 300),
        }
        for name, bounds in expected_ps.items():
            self.assertEqual(windows[name], tuple(Decimal(value) * Decimal("1e-12")
                                                  for value in bounds))
        self.assertNotIn("TAIL", windows)

    def test_e0_e1_first_170ps_pwl_matches_a005_a006_except_stop_and_second_stage(self):
        second_start = Decimal("170e-12")
        historical_ids = {
            "E0_A005_CROSSPOINT_SECOND_READ": "A005_SHARED_R10_C10",
            "E1_A006_COLUMN_SECOND_READ": "A006_SHARED_R10_C10",
        }
        for preset, run_id in historical_ids.items():
            with self.subTest(preset=preset):
                run_dir = SERIES / "runs" / run_id
                base_case = platform._with_second_read_defaults(
                    platform._with_se_defaults(
                        platform.parse_env(run_dir / "USER_CASE.snapshot.env", platform.CASE_KEYS)))
                base_stimulus = platform.parse_env(
                    run_dir / "STIMULUS.snapshot.env", platform.STIMULUS_KEYS,
                    required=platform.BASE_STIMULUS_KEYS)
                baseline_text = (run_dir / "stimulus.inc").read_text()
                current_case, current_stimulus, rendered = render(preset)
                ignored_case_fields = OPTIONAL_E_CASE_FIELDS
                for key, value in base_case.items():
                    if key not in ignored_case_fields | {"STOP"}:
                        self.assertEqual(current_case[key], value, f"{preset} {key}")
                for key in platform.BASE_STIMULUS_KEYS:
                    self.assertEqual(current_stimulus[key], base_stimulus[key], f"{preset} {key}")
                baseline = parse_pwl_sources(baseline_text)
                extended = parse_pwl_sources(rendered["stimulus_text"])
                self.assertEqual(set(baseline), set(extended))
                for source in baseline:
                    self.assertEqual(baseline[source]["node"], extended[source]["node"])
                    base_prefix = [(time, value) for time, value in baseline[source]["points"]
                                   if time < second_start]
                    new_prefix = [(time, value) for time, value in extended[source]["points"]
                                  if time < second_start]
                    self.assertEqual(new_prefix, base_prefix, source)
                    self.assertEqual(base_prefix[-1][1], "0", source)
                    self.assertEqual(new_prefix[-1][1], "0", source)

        case0, _stimulus0, e0 = render("E0_A005_CROSSPOINT_SECOND_READ")
        case1, _stimulus1, e1 = render("E1_A006_COLUMN_SECOND_READ")
        pwl0 = parse_pwl_sources(e0["stimulus_text"])
        pwl1 = parse_pwl_sources(e1["stimulus_text"])
        self.assertEqual(set(pwl0), set(pwl1))
        self.assertEqual({source for source in pwl0 if pwl0[source] != pwl1[source]},
                         {"I_SE_R2C1"})
        r2c1_second = [
            (time, value) for time, value in pwl0["I_SE_R2C1"]["points"]
            if Decimal("170e-12") <= time <= Decimal("181e-12")]
        self.assertEqual(r2c1_second, [
            (Decimal("170e-12"), "0"), (Decimal("171e-12"), "100u"),
            (Decimal("180e-12"), "100u"), (Decimal("181e-12"), "0")])
        self.assertEqual(
            [(time, value) for time, value in pwl1["I_SE_R2C1"]["points"]
             if Decimal("170e-12") <= time <= Decimal("181e-12")],
            r2c1_second)

    def test_registered_a_b_c_batch_configs_and_shared_selective_write_truth_table(self):
        case_a, _stimulus_a, a = render("A_SAME_COLUMN_DUAL_CROSSPOINT")
        case_b, _stimulus_b, b = render("B_ALL_CELL_CROSSPOINT")
        case_c, stimulus_c, c = render("C_MIXED_STORAGE_SEQUENTIAL_WRITE")
        for case, rendered in ((case_a, a), (case_b, b), (case_c, c)):
            self.assertEqual(case["DRIVE_MODE"], "SHARED")
            self.assertEqual(case["SE_TOPOLOGY"], "CELL")
            self.assertEqual(case["SE_GATE_MODE"], "CROSSPOINT")
            self.assertEqual(case["ROW_WL_READ_AMPLITUDE"], "200u")
            self.assertEqual(case["COL_SE_READ_AMPLITUDE"], "100u")
            self.assertEqual(case["ROW_WL_WRITE_AMPLITUDE"], "200u")
            self.assertEqual(case["COL_BL_WRITE_AMPLITUDE"], "200u")
            self.assertEqual(rendered["topology"]["driver_count_by_branch"],
                             {"WL": 2, "BL": 2, "SE": 4})
            self.assertEqual(rendered["static_qa"]["status"], "PASS")
            self.assertEqual({role: item["sha256"]
                              for role, item in rendered["sources"].items()},
                             platform.SOURCE_SHA256)
        self.assertEqual((case_a["ROW_BITS"], case_a["COL_BITS"],
                          case_a["SECOND_READ_ENABLE"], case_a["SECOND_ROW_BITS"],
                          case_a["SECOND_COL_BITS"], case_a["DT"], case_a["STOP"]),
                         ("11", "10", "1", "10", "10", "0.01p", "250p"))
        self.assertEqual(a["driver_stages"]["I_SE_R1C1"]["FINAL_READ"], "100u")
        self.assertEqual(a["driver_stages"]["I_SE_R2C1"]["FINAL_READ"], "100u")
        self.assertEqual(a["driver_stages"]["I_SE_R1C2"]["FINAL_READ"], "0")
        self.assertEqual(a["driver_stages"]["I_SE_R2C2"]["FINAL_READ"], "0")
        self.assertEqual(a["driver_stages"]["I_SE_R1C1"]["SECOND_READ"], "100u")
        self.assertEqual(a["driver_stages"]["I_SE_R2C1"]["SECOND_READ"], "0")
        self.assertEqual((case_b["ROW_BITS"], case_b["COL_BITS"],
                          case_b["SECOND_READ_ENABLE"], case_b["STOP"]),
                         ("11", "11", "0", "250p"))
        for driver in b["drivers"]:
            expected = ("100u" if driver["branch"] == "SE" else
                        "200u" if driver["branch"] == "WL" else "0")
            self.assertEqual(b["driver_stages"][driver["source"]]["FINAL_READ"], expected)

        self.assertEqual((case_c["READ0_ENABLE"], case_c["WRITE1_MODE"],
                          case_c["WRITE1_TARGET_1"], case_c["WRITE1_TARGET_2"],
                          case_c["SECOND_READ_ENABLE"], case_c["DT"], case_c["STOP"]),
                         ("0", "SEQUENTIAL_CROSSPOINT", "R1C1", "R2C2", "0", "0.01p", "300p"))
        self.assertEqual(stimulus_c["FINAL_READ_START"], "170p")
        self.assertTrue(c["static_qa"]["selective_write_keeps_shared_wl_bl"])
        events = c["topology"]["write1_sequence"]["events"]
        self.assertEqual([(event["target_cell"], event["wl_only_cells"],
                           event["bl_only_cells"], event["unselected_cells"])
                          for event in events], [
            ("R1C1", ["R1C2"], ["R2C1"], ["R2C2"]),
            ("R2C2", ["R2C1"], ["R1C2"], ["R1C1"]),
        ])
        expected = {
            "R1C1": {"WRITE1_TARGET_1": ("200u", "200u"), "WRITE1_TARGET_2": ("0", "0")},
            "R1C2": {"WRITE1_TARGET_1": ("200u", "0"), "WRITE1_TARGET_2": ("0", "200u")},
            "R2C1": {"WRITE1_TARGET_1": ("0", "200u"), "WRITE1_TARGET_2": ("200u", "0")},
            "R2C2": {"WRITE1_TARGET_1": ("0", "0"), "WRITE1_TARGET_2": ("200u", "200u")},
        }
        for cell in c["topology"]["cell_instances"]:
            sources = cell["source_for_each_input"]
            for stage, (wl, bl) in expected[cell["cell"]].items():
                self.assertEqual(c["driver_stages"][sources["WL"]][stage], wl)
                self.assertEqual(c["driver_stages"][sources["BL"]][stage], bl)
                self.assertEqual(c["driver_stages"][sources["SE"]][stage], "0")
        self.assertTrue(all("READ0" not in values for values in c["driver_stages"].values()))
        self.assertTrue(all(values["FINAL_READ"] == "200u"
                            for source, values in c["driver_stages"].items()
                            if source.startswith("I_WL_")))
        self.assertTrue(all(values["FINAL_READ"] == "100u"
                            for source, values in c["driver_stages"].items()
                            if source.startswith("I_SE_")))
        pwls = parse_pwl_sources(c["stimulus_text"])
        first_edges = [(Decimal("90e-12"), "0"), (Decimal("91e-12"), "200u"),
                       (Decimal("100e-12"), "200u"), (Decimal("101e-12"), "0")]
        second_edges = [(Decimal("120e-12"), "0"), (Decimal("121e-12"), "200u"),
                        (Decimal("130e-12"), "200u"), (Decimal("131e-12"), "0")]
        for source in ("I_WL_R1", "I_BL_C1"):
            self.assertTrue(all(edge in pwls[source]["points"] for edge in first_edges))
        for source in ("I_WL_R2", "I_BL_C2"):
            self.assertTrue(all(edge in pwls[source]["points"] for edge in second_edges))
        self.assertEqual(platform._stage_windows(case_c, stimulus_c)["FINAL_READ"],
                         (Decimal("170e-12"), Decimal("181e-12")))
        self.assertEqual(platform._stage_windows(case_c, stimulus_c)["READ_RESPONSE"],
                         (Decimal("170e-12"), Decimal("300e-12")))
        c_windows = [page for page in platform.plot_page_plan(c["topology"], c["probes"])
                     if page.get("window_name") == "READ_RESPONSE"]
        self.assertEqual({page["file"] for page in c_windows}, {
            f"windows/first_read_response_{cell}.html"
            for cell in ("R1C1", "R1C2", "R2C1", "R2C2")})
        a_windows = [page for page in platform.plot_page_plan(a["topology"], a["probes"])
                     if page.get("window_name")]
        self.assertEqual({page["file"] for page in a_windows}, {
            "windows/first_read_response_R1C1.html",
            "windows/first_read_response_R2C1.html",
            "windows/recovery_R1C1.html",
            "windows/second_read_response_R1C1.html",
        })

    def test_registered_batch_dry_runs_are_static_and_show_half_selects(self):
        original_runs = platform.RUNS
        try:
            with tempfile.TemporaryDirectory(prefix="rowcol-batch-dry-run-") as temp:
                platform.RUNS = Path(temp) / "runs"
                for preset in ("A_SAME_COLUMN_DUAL_CROSSPOINT", "B_ALL_CELL_CROSSPOINT",
                               "C_MIXED_STORAGE_SEQUENTIAL_WRITE"):
                    output = io.StringIO()
                    with patch.object(platform.subprocess, "run",
                                      side_effect=AssertionError("process invoked")):
                        with contextlib.redirect_stdout(output):
                            result = platform.main(["--dry-run", "--preset", preset])
                    self.assertEqual(result, 0)
                    self.assertFalse(platform.RUNS.exists())
                    self.assertIn("physical_solve_count=0", output.getvalue())
                    self.assertIn("static QA=PASS", output.getvalue())
                text = output.getvalue()
                self.assertIn("WRITE1_TARGET_1 at 90p, target=R1C1", text)
                self.assertIn("R1C2: 200u, 0, 0", text)
                self.assertIn("R2C1: 0, 200u, 0", text)
                self.assertIn("WRITE1_TARGET_2 at 120p, target=R2C2", text)
                self.assertIn("R2C1: 200u, 0, 0", text)
                self.assertIn("R1C2: 0, 200u, 0", text)
        finally:
            platform.RUNS = original_runs

    def test_batch_comparison_alignment_uses_exact_common_rows_only(self):
        series = {
            "left": {Decimal("0"): ("1",), Decimal("1"): ("2",), Decimal("2"): ("3",)},
            "right": {Decimal("0"): ("4",), Decimal("2"): ("6",), Decimal("3"): ("7",)},
        }
        times, selected = batch_compare.align_exact_rows(
            series, (Decimal("0"), Decimal("3")))
        self.assertEqual(times, [Decimal("0"), Decimal("2")])
        self.assertEqual(selected["left"][Decimal("2")], ("3",))
        self.assertEqual(selected["right"][Decimal("2")], ("6",))
        with self.assertRaisesRegex(ValueError, "fewer than two exact common"):
            batch_compare.align_exact_rows(
                {"left": series["left"], "right": {Decimal("1"): ("5",)}},
                (Decimal("0"), Decimal("3")))

    def test_second_read_requires_cell_se_and_valid_nonoverlapping_window(self):
        case, stimulus, _rendered = render("E1_A006_COLUMN_SECOND_READ")
        bad_topology = dict(case, SE_TOPOLOGY="SHARED_COLUMN")
        with self.assertRaisesRegex(platform.ConfigError, "requires independent per-cell SE"):
            platform.validate_config(bad_topology, stimulus)
        overlapping = dict(stimulus, SECOND_READ_START="120p")
        with self.assertRaisesRegex(platform.ConfigError, "overlaps FINAL_READ"):
            platform.validate_config(case, overlapping)
        too_late = dict(stimulus)
        case_late = dict(case, STOP="180p")
        with self.assertRaisesRegex(platform.ConfigError, "ends after STOP"):
            platform.validate_config(case_late, too_late)

    def test_e0_e1_dry_runs_are_static_show_windows_and_do_not_allocate(self):
        original_runs = platform.RUNS
        try:
            with tempfile.TemporaryDirectory(prefix="rowcol-e-dry-run-") as temp:
                platform.RUNS = Path(temp) / "runs"
                for preset, gate in (
                    ("E0_A005_CROSSPOINT_SECOND_READ", "CROSSPOINT"),
                    ("E1_A006_COLUMN_SECOND_READ", "COLUMN"),
                ):
                    output = io.StringIO()
                    with patch.object(platform.subprocess, "run",
                                      side_effect=AssertionError("process/solver invoked")):
                        with contextlib.redirect_stdout(output):
                            status = platform.main(["--dry-run", "--preset", preset])
                    rendered = output.getvalue()
                    self.assertEqual(status, 0)
                    self.assertIn("physical_solve_count=0", rendered)
                    self.assertIn(f"gate={gate}", rendered)
                    self.assertIn("RECOVERY_BEFORE_SECOND_READ 121–170ps", rendered)
                    self.assertIn("SECOND_READ 170–181ps", rendered)
                    self.assertIn("SECOND_READ programmed source values", rendered)
                    self.assertIn("R2C1: 200u, 0, 100u", rendered)
                    self.assertIn("STOP=300p", rendered)
                    self.assertIn("static QA=PASS", rendered)
                    self.assertFalse(platform.RUNS.exists())
        finally:
            platform.RUNS = original_runs

    def test_second_read_probe_and_separate_plot_windows_cover_selected_read_cells(self):
        _case, _stimulus, rendered = render("E0_A005_CROSSPOINT_SECOND_READ")
        labels = {item["label"] for item in rendered["probes"]["signals"]}
        instance = "XBVM_R2C1"
        for branch in ("R_WL", "R_BL", "R_SE"):
            self.assertIn(f"I({branch}|{instance})", labels)
        for jj in platform.CELL_JJS:
            self.assertIn(f"P({jj}|{instance})", labels)
            self.assertIn(f"V({jj}|{instance})", labels)
        for signal in ("V(SL_R2C1)", "V(QBOUT_R2C1)", "V(SJTL_OUT_R2C1)",
                       "V(VOUT_R2C1)"):
            self.assertIn(signal, labels)
        pages = platform.plot_page_plan(rendered["topology"], rendered["probes"])
        windows = [page for page in pages if page.get("window_name")]
        self.assertEqual([page["window_name"] for page in windows],
                         ["FIRST_READ_RESPONSE", "RECOVERY_BEFORE_SECOND_READ",
                          "SECOND_READ_RESPONSE"])
        self.assertIn("windows/first_read_response_R1C1.html", {page["file"] for page in windows})
        self.assertTrue(all("I(R_SE|XBVM_R2C1)" in page["signals"]
                            for page in windows if "R2C1" in page["file"]))
        first_page = next(page for page in windows if "first_read_response" in page["file"])
        self.assertTrue(all(f"P({jj}|XBVM_R1C1)" in first_page["signals"] for jj in platform.CELL_JJS))
        for page in windows:
            cell = "R1C1" if "first_read_response" in page["file"] else "R2C1"
            for jj in platform.CELL_JJS:
                self.assertIn(f"P({jj}|XBVM_{cell})", page["signals"])
                self.assertIn(f"V({jj}|XBVM_{cell})", page["signals"])
            for signal in (f"P(BJ1|XBQ_{cell})", f"P(BJ1|XSJTL_{cell})",
                           f"P(BJ1|XCB_{cell})", f"V(SL_{cell})", f"V(QBOUT_{cell})",
                           f"V(SJTL_OUT_{cell})", f"V(VOUT_{cell})"):
                self.assertIn(signal, page["signals"])
        self.assertEqual(rendered["static_qa"]["physical_solve_count"], 0)

    def test_second_read_disabled_is_noop_and_cell_gate_requires_cell_se_topology(self):
        case, stimulus = platform.load_config("D1_CELL_SE_CROSSPOINT_10_10")
        self.assertEqual(case["SECOND_READ_ENABLE"], "0")
        _case, _stimulus, rendered = render("D1_CELL_SE_CROSSPOINT_10_10")
        self.assertFalse(rendered["topology"]["second_read"]["enabled"])
        self.assertTrue(all("SECOND_READ" not in values
                            for values in rendered["driver_stages"].values()))
        self.assertNotIn("SECOND_READ", platform._stage_windows(_case, _stimulus))
        case["SE_TOPOLOGY"] = "SHARED_COLUMN"
        case["DRIVE_MODE"] = "SHARED"
        case["SECOND_READ_ENABLE"] = "1"
        with self.assertRaisesRegex(platform.ConfigError, "requires independent per-cell SE"):
            platform.validate_config(case, stimulus)

    def test_shared_column_crosspoint_is_rejected(self):
        case, stimulus = platform.load_config("B_SHARED_10_10")
        case["SE_GATE_MODE"] = "CROSSPOINT"
        with self.assertRaisesRegex(platform.ConfigError, "requires independent per-cell SE"):
            platform.validate_config(case, stimulus)

    def test_d0_d1_dry_runs_do_not_call_solver_or_allocate_runs(self):
        original_runs = platform.RUNS
        try:
            with tempfile.TemporaryDirectory(prefix="rowcol-d-dry-run-") as temp:
                platform.RUNS = Path(temp) / "runs"
                for preset in ("D0_CELL_SE_COLUMN_10_10", "D1_CELL_SE_CROSSPOINT_10_10"):
                    output = io.StringIO()
                    with patch.object(platform.subprocess, "run",
                                      side_effect=AssertionError("solver/process invoked")):
                        with contextlib.redirect_stdout(output):
                            status = platform.main(["--dry-run", "--preset", preset])
                    self.assertEqual(status, 0)
                    self.assertIn("physical_solve_count=0", output.getvalue())
                    self.assertIn("Drivers: 8 sources (WL/BL/SE = 2/2/4)", output.getvalue())
                    self.assertFalse(platform.RUNS.exists())
        finally:
            platform.RUNS = original_runs

    def test_new_run_number_advances_without_overwriting_existing_ids(self):
        original_runs = platform.RUNS
        try:
            with tempfile.TemporaryDirectory(prefix="rowcol-run-number-") as temp:
                platform.RUNS = Path(temp) / "runs"
                platform.RUNS.mkdir()
                for run_id in ("A001_INDEPENDENT_R10_C10", "A003_SHARED_R10_C10",
                               "A007_SHARED_R11_C11"):
                    (platform.RUNS / run_id).mkdir()
                case, _stimulus, _rendered = render("D0_CELL_SE_COLUMN_10_10")
                run_id, run_path = platform.next_run_path(case)
                self.assertEqual(run_id, "A008_SHARED_R10_C10")
                self.assertFalse(run_path.exists())
        finally:
            platform.RUNS = original_runs

    def test_historical_run_manifest_raw_hashes_and_archives_are_intact(self):
        manifest = json.loads((SERIES / "experiment_manifest.json").read_text())
        for row in manifest["runs"]:
            raw = SERIES / row["path"] / "raw.csv"
            self.assertEqual(hashlib.sha256(raw.read_bytes()).hexdigest(), row["raw_sha256"])
        for package in (SERIES / "handoff").glob("*.zip"):
            qa_path = package.with_name(f"{package.stem}_PACKAGE_QA.json")
            qa = json.loads(qa_path.read_text())
            self.assertEqual(qa["package_sha256"], hashlib.sha256(package.read_bytes()).hexdigest())
            with zipfile.ZipFile(package) as archive:
                self.assertIsNone(archive.testzip())

    def test_shared_mode_has_six_real_distinct_sources_and_no_column_short(self):
        _case, _stimulus, rendered = render("B_SHARED_10_10")
        drivers = rendered["drivers"]
        self.assertEqual(len(drivers), 6)
        self.assertEqual(rendered["topology"]["driver_count_by_branch"],
                         {"WL": 2, "BL": 2, "SE": 2})
        for branch in ("WL", "BL", "SE"):
            branch_drivers = [item for item in drivers if item["branch"] == branch]
            self.assertEqual(len(branch_drivers), 2)
            self.assertTrue(all(len(item["cells"]) == 2 for item in branch_drivers))
        node_sets = [
            {item["node"] for item in drivers if item["branch"] == branch}
            for branch in ("WL", "BL", "SE")
        ]
        self.assertFalse(node_sets[0] & node_sets[1])
        self.assertFalse(node_sets[0] & node_sets[2])
        self.assertFalse(node_sets[1] & node_sets[2])
        self.assertIn("I_WL_R1 0 WL_R1 PWL(", rendered["stimulus_text"])
        self.assertIn("I_BL_C1 0 BL_C1 PWL(", rendered["stimulus_text"])
        self.assertIn("I_SE_C1 0 SE_C1 PWL(", rendered["stimulus_text"])
        for cell in rendered["topology"]["cell_instances"]:
            self.assertEqual(cell["input_nodes"]["WL"], f"WL_R{cell['row']}")
            self.assertEqual(cell["input_nodes"]["BL"], f"BL_C{cell['column']}")
            self.assertEqual(cell["input_nodes"]["SE"], f"SE_C{cell['column']}")

    def test_independent_mode_has_twelve_cell_drivers_and_unique_nodes(self):
        _case, _stimulus, rendered = render("A_INDEPENDENT_10_10")
        self.assertEqual(len(rendered["drivers"]), 12)
        self.assertEqual(len({item["node"] for item in rendered["drivers"]}), 12)
        self.assertTrue(all(len(item["cells"]) == 1 for item in rendered["drivers"]))

    def test_all_cells_share_the_same_pre_final_sequence_and_bl_is_zero_on_final_read(self):
        for preset in ("A_INDEPENDENT_10_10", "B_SHARED_10_10", "C_SHARED_11_11"):
            with self.subTest(preset=preset):
                _case, _stimulus, rendered = render(preset)
                stages = rendered["driver_stages"]
                for cell in rendered["topology"]["cell_instances"]:
                    for branch in ("WL", "BL", "SE"):
                        source = cell["source_for_each_input"][branch]
                        values = stages[source]
                        self.assertIn("WRITE0", values)
                        self.assertIn("READ0", values)
                        self.assertIn("WRITE1", values)
                        if branch == "BL":
                            self.assertEqual(values["FINAL_READ"], "0")
                self.assertTrue(all(values["FINAL_READ"] == "0"
                                    for source, values in stages.items()
                                    if next(d for d in rendered["drivers"]
                                            if d["source"] == source)["branch"] == "BL"))

    def test_four_independent_load_chains_and_outputs_no_merge_no_t1(self):
        _case, _stimulus, rendered = render("B_SHARED_10_10")
        topology, deck = rendered["topology"], rendered["deck"]
        self.assertEqual(len({item["output_node"] for item in topology["cell_instances"]}), 4)
        self.assertEqual(len([line for line in deck.splitlines() if line.startswith("R_TERM_")]), 4)
        self.assertEqual(len([line for line in deck.splitlines() if line.startswith("XBVM_")]), 4)
        self.assertEqual(len([line for line in deck.splitlines() if line.startswith("XBQ_")]), 4)
        self.assertEqual(len([line for line in deck.splitlines() if line.startswith("XSJTL_")]), 4)
        self.assertEqual(len([line for line in deck.splitlines() if line.startswith("XCB_")]), 4)
        self.assertNotIn("XT1", deck)
        self.assertNotIn("MERGE", deck)
        self.assertIn(".include stimulus.inc", deck)
        self.assertIn(".tran 0.01p 250p", deck)
        self.assertEqual(rendered["probes"]["signal_count"],
                         len({item["label"] for item in rendered["probes"]["signals"]}))

    def test_required_probe_and_plot_sets_cover_all_cells_and_four_outputs(self):
        _case, _stimulus, rendered = render("B_SHARED_10_10")
        labels = {item["label"] for item in rendered["probes"]["signals"]}
        for cell in ("R1C1", "R1C2", "R2C1", "R2C2"):
            for branch in ("R_WL", "R_BL", "R_SE"):
                self.assertIn(f"I({branch}|XBVM_{cell})", labels)
            for jj in platform.CELL_JJS:
                self.assertIn(f"P({jj}|XBVM_{cell})", labels)
                self.assertIn(f"V({jj}|XBVM_{cell})", labels)
            for jj in platform.QB_JJS:
                self.assertIn(f"P({jj}|XBQ_{cell})", labels)
                self.assertIn(f"V({jj}|XBQ_{cell})", labels)
        pages = platform.plot_page_plan(rendered["topology"], rendered["probes"])
        self.assertEqual(len(pages), 7)
        outputs = next(page for page in pages if page["file"] == "01_outputs.html")["signals"]
        self.assertEqual({label for label in outputs if label.startswith("V(VOUT_")},
                         {f"V(VOUT_{cell})" for cell in ("R1C1", "R1C2", "R2C1", "R2C2")})

    def test_exact_stimulus_windows_and_registered_read_bl_zero(self):
        _case, stimulus, _rendered = render("B_SHARED_10_10")
        windows = platform._stage_windows(_case, stimulus)
        expected_ps = {"WRITE0": (50, 61), "READ0": (70, 81),
                       "WRITE1": (90, 101), "FINAL_READ": (110, 121)}
        for stage, (start, end) in expected_ps.items():
            self.assertEqual(windows[stage], (Decimal(start) * Decimal("1e-12"),
                                              Decimal(end) * Decimal("1e-12")))

    def test_dry_run_invokes_no_process_and_creates_no_run_directory(self):
        original_runs = platform.RUNS
        try:
            with tempfile.TemporaryDirectory(prefix="rowcol-dry-run-") as temp:
                platform.RUNS = Path(temp) / "runs"
                output = io.StringIO()
                with patch.object(platform.subprocess, "run", side_effect=AssertionError("process invoked")):
                    with contextlib.redirect_stdout(output):
                        result = platform.main(["--dry-run", "--preset", "B_SHARED_10_10"])
                self.assertEqual(result, 0)
                self.assertFalse(platform.RUNS.exists())
                text = output.getvalue()
                self.assertIn("DRY RUN PASS — no solver call; physical_solve_count=0", text)
                self.assertIn("Drivers: 6 sources (WL/BL/SE = 2/2/2)", text)
                self.assertIn("active=R1C1 | half-selected=R1C2,R2C1 | off=R2C2", text)
                self.assertIn("FINAL_READ +WL(row bits)/+SE(column bits), BL=0", text)
                self.assertNotIn("PROBE MANIFEST", text)
                self.assertNotIn(".print ", text)
                self.assertNotIn("ACTUAL RENDERED DECK", text)
        finally:
            platform.RUNS = original_runs

    def test_verbose_dry_run_retains_full_manifest_pwl_and_netlist_view(self):
        original_runs = platform.RUNS
        try:
            with tempfile.TemporaryDirectory(prefix="rowcol-verbose-dry-run-") as temp:
                platform.RUNS = Path(temp) / "runs"
                output = io.StringIO()
                with patch.object(platform.subprocess, "run", side_effect=AssertionError("process invoked")):
                    with contextlib.redirect_stdout(output):
                        result = platform.main(["--dry-run", "--verbose", "--preset", "B_SHARED_10_10"])
                self.assertEqual(result, 0)
                self.assertFalse(platform.RUNS.exists())
                text = output.getvalue()
                self.assertIn("VERBOSE: exact PWL source lines", text)
                self.assertIn("I_WL_R1 0 WL_R1 PWL(", text)
                self.assertIn("VERBOSE: exact actual deck", text)
                self.assertIn(".include stimulus.inc", text)
                self.assertIn(".print I(R_WL|XBVM_R1C1)", text)
        finally:
            platform.RUNS = original_runs

    def test_mocked_runner_writes_complete_artifacts_without_real_josim(self):
        from types import SimpleNamespace

        original_runs, original_series = platform.RUNS, platform.SERIES
        with tempfile.TemporaryDirectory(prefix="rowcol-mock-run-") as temp:
            root = Path(temp) / "series"
            platform.RUNS = root / "runs"
            platform.SERIES = root
            platform.RUNS.mkdir(parents=True)
            case, stimulus = platform.load_config("B_SHARED_10_10")
            run_id, run_dir = platform.next_run_path(case)

            calls = []

            def fake_solver(command, cwd, capture_output, text, check):
                calls.append(command)
                deck_path = Path(command[-1])
                output_path = Path(command[command.index("-o") + 1])
                labels = [line.split(None, 1)[1] for line in deck_path.read_text().splitlines()
                          if line.startswith(".print ")]
                with output_path.open("w", encoding="utf-8", newline="") as stream:
                    writer = csv.writer(stream)
                    writer.writerow(["time", *labels])
                    for ps in range(251):
                        writer.writerow([f"{ps}e-12", *("0" for _ in labels)])
                return SimpleNamespace(returncode=0, stdout="mock solver stdout\n",
                                       stderr="mock solver stderr\n")

            try:
                with patch.object(platform, "_solver_info", return_value={
                        "path": "mock-josim", "version": "MOCK", "sha256": "0" * 64,
                        "parent_head": "a155b7f820efbad4447c8d1985a66e4192b7e614"}), \
                     patch.object(platform.subprocess, "run", side_effect=fake_solver):
                    status = platform._execute(case, stimulus)
                self.assertEqual(status, 0)
                self.assertEqual(len(calls), 1)
                self.assertEqual(run_id, "A001_SHARED_R10_C10")
                self.assertTrue((run_dir / "raw.csv").is_file())
                self.assertEqual(json.loads((run_dir / "result.json").read_text())["physical_solve_count"], 1)
                self.assertEqual(json.loads((run_dir / "analysis/static_qa.json").read_text())["status"], "PASS")
                self.assertEqual(json.loads((run_dir / "analysis/raw_qa.json").read_text())["status"], "PASS")
                self.assertEqual(json.loads((run_dir / "analysis/stimulus_qa.json").read_text())["status"], "PASS")
                self.assertEqual(json.loads((run_dir / "analysis/plot_qa.json").read_text())["status"], "PASS")
                self.assertTrue((root / "experiment_manifest.json").is_file())
            finally:
                platform.RUNS, platform.SERIES = original_runs, original_series


if __name__ == "__main__":
    unittest.main(verbosity=2)
