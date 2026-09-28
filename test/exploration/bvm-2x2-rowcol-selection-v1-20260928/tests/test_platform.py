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


def render(preset: str | None = None):
    case, stimulus = platform.load_config(preset)
    preview_run = SERIES / "runs" / "A999_PREVIEW_ONLY"
    return case, stimulus, platform.render(case, stimulus, preview_run)


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

    def test_legacy_presets_keep_shared_column_column_defaults_and_old_counts(self):
        for preset, mode, count in (
            ("A_INDEPENDENT_10_10", "INDEPENDENT", 12),
            ("B_SHARED_10_10", "SHARED", 6),
            ("C_SHARED_11_11", "SHARED", 6),
        ):
            with self.subTest(preset=preset):
                case, _stimulus, rendered = render(preset)
                self.assertEqual(case["SE_TOPOLOGY"], "SHARED_COLUMN")
                self.assertEqual(case["SE_GATE_MODE"], "COLUMN")
                self.assertEqual(rendered["topology"]["driver_count"], count)
                self.assertEqual(rendered["static_qa"]["status"], "PASS")

    def test_legacy_user_case_missing_new_keys_loads_with_compatibility_defaults(self):
        legacy_case = SERIES / "runs/A001_INDEPENDENT_R10_C10/USER_CASE.snapshot.env"
        with patch.object(platform, "USER_CASE", legacy_case):
            case, _stimulus = platform.load_config()
        self.assertEqual(case["SE_TOPOLOGY"], "SHARED_COLUMN")
        self.assertEqual(case["SE_GATE_MODE"], "COLUMN")
        self.assertEqual(case["DRIVE_MODE"], "INDEPENDENT")

    def test_legacy_run_snapshots_render_byte_identically(self):
        run_ids = (
            "A001_INDEPENDENT_R10_C10",
            "A002_SHARED_R10_C10",
            "A003_SHARED_R10_C10",
        )
        for run_id in run_ids:
            with self.subTest(run_id=run_id):
                run_dir = SERIES / "runs" / run_id
                case = platform.parse_env(run_dir / "USER_CASE.snapshot.env", platform.CASE_KEYS)
                case = platform._with_se_defaults(case)
                stimulus = platform.parse_env(run_dir / "STIMULUS.snapshot.env",
                                              platform.STIMULUS_KEYS, required=platform.STIMULUS_KEYS)
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
        self.assertEqual(len(pages), 6)
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
