from __future__ import annotations

import contextlib
import csv
import io
import json
import sys
import tempfile
import unittest
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
                self.assertIn("Drivers: 6 line sources (WL/BL/SE = 2/2/2)", text)
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
