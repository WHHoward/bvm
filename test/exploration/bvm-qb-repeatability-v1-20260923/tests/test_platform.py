#!/usr/bin/env python3
"""Bounded no-solver platform regression tests."""

from __future__ import annotations

import re
import sys
import tempfile
import unittest
import csv
import json
import importlib.util
import subprocess
from pathlib import Path

SERIES = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERIES / "scripts"))

from common import REPO, legacy, public_params, render_deck, resolve_params, sha256, snapshot_sources  # noqa: E402
from run_case import (resolve_reference_path, resolve_run_path,
                      unexpected_registered_worktree_paths,
                      validate_registered_invocation)  # noqa: E402
import analyze_case  # noqa: E402
import plot_case  # noqa: E402
_package_spec = importlib.util.spec_from_file_location("repeatability_package_test", SERIES / "scripts" / "package.py")
package = importlib.util.module_from_spec(_package_spec)
_package_spec.loader.exec_module(package)

HIST = SERIES.parent / "bvm-qb-50ghz-merge-v1-20260922" / "phase_a_repeated_read" / "runs"


def parse_unit(token: str) -> float:
    match = re.fullmatch(r"([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)([munpf]?)", token)
    if not match:
        raise ValueError(token)
    factor = {"": 1.0, "m": 1e-3, "u": 1e-6, "n": 1e-9, "p": 1e-12, "f": 1e-15}[match.group(2)]
    return float(match.group(1)) * factor


def parsed_sources(text: str, last_ps: float) -> dict[str, list[tuple[float, float]]]:
    result = {}
    for line in text.splitlines():
        if line.startswith("*") or " pwl(" not in line.lower():
            continue
        head, tail = line.split("pwl(", 1)
        source_name = head.split()[0]
        tokens = tail.rstrip(") ").split()
        pairs = [(parse_unit(tokens[i]) * 1e12, parse_unit(tokens[i + 1]))
                 for i in range(0, len(tokens), 2)]
        result[source_name] = [(t, value) for t, value in pairs if t <= last_ps + 1e-9]
    return result


def normalized_deck(text: str) -> list[str]:
    rows = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("*") or stripped.lower().startswith(".include"):
            continue
        if stripped.lower().startswith(".tran"):
            tokens = stripped.split()
            rows.append(f".tran {tokens[1].lower()} <computed-stop>")
        else:
            rows.append(" ".join(stripped.lower().split()))
    return rows


def build_finalization_fixture(root: Path) -> None:
    analysis = root / "analysis"
    runs = root / "runs"
    receipts = analysis / "receipts"
    receipts.mkdir(parents=True)
    lock_path = analysis / "PLATFORM_SOURCE_LOCK.json"
    lock_path.write_text(json.dumps({"source_hashes": {"GIT_ATTRIBUTES": {
        "path": ".gitattributes", "sha256": sha256(REPO / ".gitattributes")}}}), encoding="utf-8")
    preflight = {"status": "PASS", "git": {"head": "a" * 40},
                 "platform_source_lock_sha256": analyze_case.sha256(lock_path)}
    preflight_path = analysis / "PREFLIGHT_QA.json"
    preflight_path.write_text(json.dumps(preflight), encoding="utf-8")
    (root / "REGRESSION_MATRIX.json").write_text(
        json.dumps({"cases": [{"case_id": f"CASE{i}"} for i in range(5)]}), encoding="utf-8")
    entries = []
    cases = []
    for index in range(5):
        case_id = f"CASE{index}"
        run_dir = runs / case_id
        run_dir.mkdir(parents=True)
        artifacts = {
            "raw.csv": "time,V(QBIN)\n1e-12,0\n",
            "actual_deck.cir": "deck\n", "stimulus.inc": "stimulus\n",
            "config_snapshot.env": "config\n", "stimulus_snapshot.json": "{}\n",
            "source_manifest.json": "{}\n",
        }
        for name, value in artifacts.items():
            (run_dir / name).write_text(value, encoding="utf-8")
        params = {"CANDIDATE": "QB_2X1", "MASK": "11"}
        solver = {"sha256": "solver-sha", "version": "solver-v"}
        metadata = {"execution_status": "RUN_PASS", "physical_solve_count": 1,
                    "parameters": params, "solver": solver}
        (run_dir / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
        result = {"artifact_status": "VALID", "raw_sha256": "unused"}
        (run_dir / "result.json").write_text(json.dumps(result), encoding="utf-8")
        artifact_hashes = {key.replace(".csv", "").replace(".cir", "").replace(".inc", ""): analyze_case.sha256(run_dir / key)
                           for key in artifacts}
        # Receipt names use the run artifact key spellings expected by the package verifier.
        artifact_hashes.update({"metadata": analyze_case.sha256(run_dir / "metadata.json"),
                                "result": analyze_case.sha256(run_dir / "result.json"),
                                "config_snapshot": analyze_case.sha256(run_dir / "config_snapshot.env"),
                                "stimulus_snapshot": analyze_case.sha256(run_dir / "stimulus_snapshot.json")})
        artifact_hashes["deck"] = analyze_case.sha256(run_dir / "actual_deck.cir")
        artifact_hashes["stimulus"] = analyze_case.sha256(run_dir / "stimulus.inc")
        artifact_hashes["source_manifest"] = analyze_case.sha256(run_dir / "source_manifest.json")
        receipt = {"run_dir": package.repo_rel(run_dir), "runner_exit_code": 0,
                   "execution_status": "RUN_PASS", "artifact_status": "VALID",
                   "physical_solve_count": 1, "parameters": params, "solver": solver,
                   "artifact_sha256": artifact_hashes}
        receipt_path = receipts / f"{case_id}.json"
        receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
        entries.append({"case_id": case_id, "action": "NEW_PHYSICAL_SOLVE",
                        "receipt_path": package.repo_rel(receipt_path),
                        "receipt_sha256": analyze_case.sha256(receipt_path)})
        cases.append(run_dir)
    execution = {"status": "ALL_REGISTERED_RUNS_COMPLETE", "completed_solve_count": 5,
                 "authorized_solve_count": 5, "physical_solve_count": 5,
                 "new_physical_solve_count": 5, "existing_physical_solve_count": 0,
                 "preflight_status": "PASS",
                 "preflight_qa_sha256": analyze_case.sha256(preflight_path),
                 "runs": entries}
    execution_path = analysis / "REGRESSION_EXECUTION.json"
    execution_path.write_text(json.dumps(execution), encoding="utf-8")
    final_result = {"artifact_status": "VALID", "physical_solve_count": 5,
                    "new_physical_solve_count": 5}
    (root / "result.json").write_text(json.dumps(final_result), encoding="utf-8")
    sealed = {package.repo_rel(path): analyze_case.sha256(path)
              for path in root.rglob("*")
              if path.is_file() and not package.excluded_from_finalization_seal(path)}
    final_qa = {"status": "PASS", "physical_solve_count": 5,
                "new_physical_solve_count": 5, "existing_physical_solve_count": 0,
                "authorized_solve_count": 5,
                "sealed_file_sha256": sealed}
    final_path = analysis / "FINAL_QA.json"
    final_path.write_text(json.dumps(final_qa), encoding="utf-8")
    (analysis / "FINAL_QA.sha256").write_text(f"{analyze_case.sha256(final_path)}  FINAL_QA.json\n", encoding="utf-8")


class PlatformTest(unittest.TestCase):
    def test_candidate_profiles_are_independent_and_expand(self):
        qb2, _ = resolve_params({"NAME": "profile2", "CANDIDATE": "QB_2X1", "ARRAY_SIZE": "2", "MASK": "11"})
        qb3, _ = resolve_params({"NAME": "profile3", "CANDIDATE": "QB_3X1", "ARRAY_SIZE": "3", "MASK": "111"})
        self.assertEqual((qb2["JS1_AREA"], qb2["JS2_AREA"], qb2["QB_BJ1_AREA"]), ("0.90", "0.90", "0.85"))
        self.assertEqual((qb3["JS1_AREA"], qb3["JS2_AREA"], qb3["QB_BJ1_AREA"]), ("0.86", "0.86", "0.85"))
        self.assertNotEqual(qb2["ARRAY_SIZE"], qb3["ARRAY_SIZE"])

    def test_five_registered_schedules_and_stop_coverage(self):
        common = {"ARRAY_SIZE": "2", "CANDIDATE": "QB_2X1", "MASK": "11"}
        a, pa = resolve_params({**common, "NAME": "a", "TEST_MODE": "REPEAT_READ", "READ_COUNT": "5"})
        self.assertEqual(pa["read_starts_ps"], [110, 130, 150, 170, 190])
        self.assertEqual(pa["stop_ps"], 241)
        d, pd = resolve_params({**common, "NAME": "d", "TEST_MODE": "RECOVERY_PROBE", "READ_COUNT": "1", "RECOVERY_TAIL_PS": "100"})
        self.assertEqual(pd["stop_ps"], 221)
        e, pe = resolve_params({**common, "NAME": "e", "TEST_MODE": "REWRITE_READ", "STATE_SEQUENCE": "00,01,11", "STATE_INTERVAL_PS": "70"})
        self.assertEqual(pe["read_starts_ps"], [95, 165, 235])
        self.assertEqual(pe["last_stimulus_time_ps"], 246)
        self.assertEqual(pe["stop_ps"], 386)
        for params, plan in ((a, pa), (d, pd), (e, pe)):
            self.assertGreater(plan["stop_ps"], plan["last_stimulus_time_ps"] + float(params["LATENCY_MAX_PS"]))
            windows = plan["cycles"]
            for left, right in zip(windows, windows[1:]):
                self.assertLessEqual(left["cycle_window_ps"][1], right["cycle_window_ps"][0])

    def test_pwl_source_count_and_no_high_numbered_source(self):
        for candidate, size, mask in (("QB_2X1", 2, "11"), ("QB_3X1", 3, "111")):
            params, plan = resolve_params({"NAME": f"src{size}", "CANDIDATE": candidate,
                                          "ARRAY_SIZE": str(size), "MASK": mask})
            qa = legacy.fan_in.stimulus_source_inventory(plan["text"], size)
            self.assertEqual(qa["status"], "PASS")
            self.assertEqual(qa["expected_group_count"], 3 * size)
            self.assertEqual(qa["high_numbered_sources"], [])

    def test_invalid_overlap_hard_stops(self):
        with self.assertRaises(ValueError):
            resolve_params({"NAME": "overlap", "TEST_MODE": "REPEAT_READ", "READ_WIDTH_PS": "19"})
        with self.assertRaises(ValueError):
            resolve_params({"NAME": "rewrite_overlap", "TEST_MODE": "REWRITE_READ", "STATE_SEQUENCE": "00,01,11", "STATE_INTERVAL_PS": "50"})
        with self.assertRaises(ValueError):
            resolve_params({"NAME": "rewrite_reset_overlap", "TEST_MODE": "REWRITE_READ", "STATE_SEQUENCE": "00,01,11", "RESET_TO_WRITE_DELAY_PS": "5"})
        with self.assertRaises(ValueError):
            resolve_params({"NAME": "rewrite_read_overlap", "TEST_MODE": "REWRITE_READ", "STATE_SEQUENCE": "00,01,11", "WRITE_TO_READ_DELAY_PS": "5"})

    def test_a_b_c_stimulus_and_normalized_deck_match_historical_fixture(self):
        references = (("QB_2X1_01", "QB_2X1", "2", "01"),
                      ("QB_2X1_11", "QB_2X1", "2", "11"),
                      ("QB_3X1_111", "QB_3X1", "3", "111"))
        for old_id, candidate, size, mask in references:
            with self.subTest(old_id=old_id):
                params, plan = resolve_params({"NAME": f"eq_{old_id}", "CANDIDATE": candidate,
                                              "ARRAY_SIZE": size, "MASK": mask,
                                              "TEST_MODE": "REPEAT_READ", "READ_COUNT": "5"})
                old_dir = HIST / old_id
                old_stimulus = (old_dir / "stimulus.inc").read_text(encoding="utf-8")
                self.assertEqual(parsed_sources(plan["text"], plan["last_stimulus_time_ps"]),
                                 parsed_sources(old_stimulus, plan["last_stimulus_time_ps"]))
                with tempfile.TemporaryDirectory(prefix="bvm_repeat_eq_") as temp:
                    temp_dir = Path(temp)
                    stimulus_path = temp_dir / "stimulus.inc"
                    stimulus_path.write_text(plan["text"], encoding="utf-8")
                    sources = snapshot_sources(temp_dir, params)
                    new_deck = render_deck(temp_dir, params, sources, stimulus_path)
                    old_deck = (old_dir / "actual_deck.cir").read_text(encoding="utf-8")
                    self.assertEqual(normalized_deck(new_deck), normalized_deck(old_deck))
                    old_bvm = (old_dir / "snapshot" / "sources" / "bvm_tunable.cir").read_text(encoding="utf-8")
                    old_qb = (old_dir / "snapshot" / "sources" / "bq_tunable.cir").read_text(encoding="utf-8")
                    clean_bvm = [" ".join(line.lower().split()) for line in sources["BVM"].read_text().splitlines()
                                 if line.strip() and not line.lstrip().startswith("*")]
                    clean_old_bvm = [" ".join(line.lower().split()) for line in old_bvm.splitlines()
                                     if line.strip() and not line.lstrip().startswith("*")]
                    clean_qb = [" ".join(line.lower().split()) for line in sources["QB"].read_text().splitlines()
                                if line.strip() and not line.lstrip().startswith("*")]
                    clean_old_qb = [" ".join(line.lower().split()) for line in old_qb.splitlines()
                                    if line.strip() and not line.lstrip().startswith("*")]
                    self.assertEqual(clean_bvm, clean_old_bvm)
                    self.assertEqual(clean_qb, clean_old_qb)

    def test_analysis_and_classic_plot_smoke_on_temporary_nonphysical_fixture(self):
        params, plan = resolve_params({"NAME": "temporary_analysis_smoke", "TEST_MODE": "REPEAT_READ"})
        signals = [signal for signal in dict.fromkeys(row[0] for row in legacy.requested_signals("closed", params))
                   if signal != "V(IB|XBQ1)"]
        with tempfile.TemporaryDirectory(prefix="bvm_repeat_analysis_test_", dir=SERIES / "runs") as temporary:
            run_dir = Path(temporary)
            fields = ["time", *signals]
            raw = run_dir / "raw.csv"
            with raw.open("w", encoding="utf-8", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=fields)
                writer.writeheader()
                final_index = int(float(params["STOP_PS"]) * 10)
                for index in range(1, final_index):
                    time_s = index * 0.1e-12
                    writer.writerow({"time": f"{time_s:.13g}", **{signal: "0" for signal in signals}})
            run_id = "TEMPORARY_SOFTWARE_FIXTURE"
            (run_dir / "metadata.json").write_text(json.dumps({"run_id": run_id,
                                                               "parameters": public_params(params),
                                                               "raw": {"sha256": analyze_case.sha256(raw)}}), encoding="utf-8")
            (run_dir / "stderr.txt").write_text("W: Controls\nUnknown device/node IB|XBQ1\nCannot store results for this device/node.\nIgnoring this store request.\n", encoding="utf-8")
            (run_dir / "stimulus_snapshot.json").write_text(json.dumps({
                "registered_windows": plan["cycles"], "read_schedule": plan["schedule"],
                "last_stimulus_time_ps": plan["last_stimulus_time_ps"]}), encoding="utf-8")
            qa = analyze_case.analyze_run(run_dir)
            self.assertEqual(qa["status"], "PASS")
            self.assertTrue((run_dir / "analysis" / "recovery_trace.csv").is_file())
            self.assertTrue((run_dir / "analysis" / "event_assignment.csv").is_file())
            self.assertTrue(qa["raw_unchanged"])
            raw_qa = json.loads((run_dir / "analysis" / "raw_qa.json").read_text(encoding="utf-8"))
            self.assertEqual(raw_qa["known_unsupported_probe_columns"], ["V(IB|XBQ1)"])
            with (run_dir / "analysis" / "signal_manifest.csv").open("r", encoding="utf-8", newline="") as stream:
                signal_rows = list(csv.DictReader(stream))
            unknown_rows = [row for row in signal_rows if row["raw_column"] == "V(IB|XBQ1)"]
            self.assertEqual(len(unknown_rows), 1)
            self.assertEqual(unknown_rows[0]["physical_quantity"], "voltage")
            self.assertEqual(unknown_rows[0]["status"], "UNKNOWN")
            comparison = run_dir / "temporary_plot_input.csv"
            with comparison.open("w", encoding="utf-8", newline="") as stream:
                writer = csv.writer(stream)
                writer.writerow(["time", "V(QBIN)", "V(R_TERM)"])
                writer.writerow(["1e-12", "0", "0"])
                writer.writerow(["1.1e-12", "0", "0"])
            plot_path = run_dir / "temporary_classic_plot.html"
            entry = plot_case.render_classic(comparison, plot_path, ["V(QBIN)", "V(R_TERM)"],
                                             "temporary classic plot smoke", run_dir / "plotly.min.js",
                                             raw, analyze_case.sha256(raw))
            self.assertTrue(plot_path.is_file())
            self.assertTrue((run_dir / "plotly.min.js").is_file())
            self.assertIn("josim-plot2.py", entry["renderer"])

    def test_ambiguous_candidate_pair_never_reuses_terminal(self):
        cycles = [{"cycle_index": 1, "cycle_window_ps": [0.0, 30.0]},
                  {"cycle_index": 2, "cycle_window_ps": [30.0, 60.0]}]
        upstream = [
            {"candidate_id": "BJ2C0001", "start_ps": 10.0, "end_ps": 11.0, "peak_time_ps": 10.0,
             "peak_voltage_v": 1e-3, "sample_count_above_threshold": 2},
            {"candidate_id": "BJ2C0002", "start_ps": 12.0, "end_ps": 13.0, "peak_time_ps": 12.0,
             "peak_voltage_v": 1e-3, "sample_count_above_threshold": 2},
        ]
        terminal = [{"candidate_id": "TERMC0001", "start_ps": 20.0, "end_ps": 21.0,
                     "peak_time_ps": 20.0, "peak_voltage_v": 1e-3,
                     "sample_count_above_threshold": 2}]
        assigned, terminal_rows, qa = analyze_case.assign_candidates(upstream, terminal, cycles, 5.0, 15.0)
        self.assertEqual(qa["status"], "PASS")
        self.assertTrue(all(row["terminal_candidate_id"] is None for row in assigned))
        self.assertEqual({row["assignment_status"] for row in assigned}, {"AMBIGUOUS_SHARED_TERMINAL_CANDIDATE"})
        self.assertIsNone(terminal_rows[0]["assigned_upstream_candidate_id"])

    def test_pipeline_candidate_may_arrive_in_next_read_cycle_but_is_labeled(self):
        cycles = [{"cycle_index": 1, "cycle_window_ps": [110.0, 130.0]},
                  {"cycle_index": 2, "cycle_window_ps": [130.0, 150.0]}]
        upstream = [{"candidate_id": "BJ2C0001", "start_ps": 115.0, "end_ps": 116.0,
                     "peak_time_ps": 115.0, "peak_voltage_v": 1e-3,
                     "sample_count_above_threshold": 2}]
        terminal = [{"candidate_id": "TERMC0001", "start_ps": 136.0, "end_ps": 137.0,
                     "peak_time_ps": 136.0, "peak_voltage_v": 1e-3,
                     "sample_count_above_threshold": 2}]
        assigned, terminal_rows, qa = analyze_case.assign_candidates(upstream, terminal, cycles, 10.0, 25.0)
        self.assertEqual(qa["status"], "PASS")
        self.assertEqual(assigned[0]["read_cycle_index"], 1)
        self.assertEqual(assigned[0]["terminal_observed_cycle_index"], 2)
        self.assertEqual(assigned[0]["assignment_status"], "ASSIGNED_UNIQUE_MONOTONIC")
        self.assertEqual(terminal_rows[0]["assigned_upstream_candidate_id"], "BJ2C0001")

    def test_jtl_candidate_chain_requires_all_twelve_ordered_junctions(self):
        upstream = [{"upstream_candidate_id": "BJ2C0001", "upstream_event_time_ps": 10.0,
                     "read_cycle_index": 1, "terminal_candidate_id": "TERMC0001",
                     "terminal_event_time_ps": 40.0, "terminal_observed_cycle_index": 2,
                     "assignment_status": "ASSIGNED_UNIQUE_MONOTONIC"}]
        nodes = {}
        ordinal = 1
        for stage in range(1, 7):
            for junction in ("B01", "B02"):
                name = f"JTL{stage}_{junction}"
                time_ps = 10.0 + ordinal * 2.0
                nodes[name] = [{"candidate_id": f"{name}C0001", "peak_time_ps": time_ps}]
                ordinal += 1
        paths, qa = analyze_case.assign_jtl_candidate_paths(upstream, nodes)
        self.assertEqual(qa["status"], "COMPLETE_PATHS_OBSERVED")
        self.assertEqual(qa["invariant_status"], "PASS")
        self.assertEqual(paths[0]["jtl_path_status"], "UNIQUE_MONOTONIC_CANDIDATE_PATH")
        nodes["JTL3_B01"] = []
        incomplete, qa_incomplete = analyze_case.assign_jtl_candidate_paths(upstream, nodes)
        self.assertEqual(qa_incomplete["status"], "NO_COMPLETE_PATH_OBSERVED")
        self.assertEqual(qa_incomplete["invariant_status"], "PASS")
        self.assertEqual(incomplete[0]["jtl_path_status"], "INCOMPLETE_NO_JTL3_B01_CANDIDATE")

    def test_reference_headers_cover_compact_classic_plot_groups(self):
        references = (("QB_2X1_01", "QB_2X1", "2", "01"),
                      ("QB_2X1_11", "QB_2X1", "2", "11"),
                      ("QB_3X1_111", "QB_3X1", "3", "111"))
        for old_id, candidate, size, mask in references:
            with self.subTest(old_id=old_id):
                raw = HIST / old_id / "raw.csv"
                with raw.open("r", encoding="utf-8", newline="") as stream:
                    headers = next(csv.reader(stream))
                params, plan = resolve_params({"NAME": f"plots_{old_id}", "CANDIDATE": candidate,
                                              "ARRAY_SIZE": size, "MASK": mask})
                groups = plot_case.groups_for_run(headers, params, plan["cycles"])
                self.assertTrue(all(2 <= len(signals) <= 5 for rows in groups.values()
                                    for _stem, signals, _window in rows))
                missing = [signal for rows in groups.values() for _stem, signals, _window in rows
                           for signal in signals if signal not in headers]
                self.assertEqual(missing, [])
                timing = {stem: signals for stem, signals, _window in groups["01_SIGNAL_TIMING"]}
                for index in range(1, int(size) + 1):
                    expected = [f"I(I_WL{index})", f"I(I_BL{index})", f"I(I_SE{index})",
                                "V(QBOUT)", "V(R_TERM)"]
                    self.assertEqual(timing[f"input_to_output_BVM{index}"], expected)
                    self.assertTrue(all(signal in headers for signal in expected))

    def test_delta_base_is_hash_bound_and_ancestral(self):
        import subprocess
        from common import REPO
        head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()
        base = package.select_base(None, head)
        self.assertEqual(base["base_package_name"], "bvm-qb-50ghz-merge-v1-20260922_raw_handoff_classic-v4.zip")
        self.assertEqual(base["base_package_sha256"], "e965bac4653748faa6761fd29fcb991043a800065ffad4f66cedc508e8af5c8a")

    def test_package_finalization_seal_accepts_exact_files_and_rejects_mutations(self):
        original_root = package.ROOT
        try:
            with tempfile.TemporaryDirectory(prefix="bvm_repeat_package_seal_") as temporary:
                root = Path(temporary)
                build_finalization_fixture(root)
                package.ROOT = root
                verified = package.verify_finalization_seal()
                self.assertEqual(verified["physical_solve_count"], 5)
                (root / "runs" / "CASE0" / "raw.csv").write_text("tampered\n", encoding="utf-8")
                with self.assertRaises(RuntimeError):
                    package.verify_finalization_seal()

            with tempfile.TemporaryDirectory(prefix="bvm_repeat_package_extra_") as temporary:
                root = Path(temporary)
                build_finalization_fixture(root)
                package.ROOT = root
                (root / "unsealed_after_finalize.txt").write_text("extra\n", encoding="utf-8")
                with self.assertRaises(RuntimeError):
                    package.verify_finalization_seal()
        finally:
            package.ROOT = original_root

    def test_regression_scope_blocks_unregistered_direct_solver_invocation(self):
        params, _plan = resolve_params()
        with self.assertRaises(ValueError):
            validate_registered_invocation(None, {}, None, params)
        manual_params, _manual_plan = resolve_params({"EXECUTION_SCOPE": "MANUAL"})
        validate_registered_invocation(None, {}, None, manual_params)
        direct = subprocess.run([sys.executable, str(SERIES / "scripts" / "run_case.py")],
                                cwd=SERIES.parents[2], capture_output=True, text=True, check=False)
        self.assertEqual(direct.returncode, 2)
        self.assertIn("REGRESSION_MATRIX scope blocks direct solves", direct.stderr)
        self.assertFalse((SERIES / "runs" / "RR_QB2X1_N1").exists())
        scope_bypass = subprocess.run([sys.executable, str(SERIES / "scripts" / "run_case.py"),
                                       "--set", "EXECUTION_SCOPE=MANUAL"],
                                      cwd=SERIES.parents[2], capture_output=True, text=True, check=False)
        self.assertEqual(scope_bypass.returncode, 2)
        self.assertIn("only be changed in USER_CASE.env", scope_bypass.stderr)

    def test_analyzer_and_plotter_cli_reject_path_traversal(self):
        old_run = "../../bvm-qb-50ghz-merge-v1-20260922/phase_a_repeated_read/runs/QB_2X1_01"
        for script in ("analyze_case.py", "plot_case.py"):
            result = subprocess.run([sys.executable, str(SERIES / "scripts" / script), old_run],
                                    cwd=SERIES.parents[2], capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode, 2)
            self.assertIn("filesystem-safe identifier", result.stderr)
        sweep = subprocess.run([sys.executable, str(SERIES / "scripts" / "run_sweep.py"),
                                "--key", "READ_PERIOD_PS", "--values", "20,25"],
                               cwd=SERIES.parents[2], capture_output=True, text=True, check=False)
        self.assertEqual(sweep.returncode, 2)
        self.assertIn("physical sweeps are disabled", sweep.stderr)

    def test_reference_binding_and_analysis_only_paths_are_scoped(self):
        matrix = json.loads((SERIES / "REGRESSION_MATRIX.json").read_text(encoding="utf-8"))
        a = matrix["cases"][0]
        reference = resolve_reference_path(a["reference_run"])
        self.assertEqual(reference, SERIES.parents[2] / a["reference_run"])
        with self.assertRaises(ValueError):
            resolve_run_path("../../bvm-qb-50ghz-merge-v1-20260922/phase_a_repeated_read/runs/QB_2X1_01")

    def test_registered_child_allows_only_generated_runtime_paths(self):
        prefix = SERIES.relative_to(SERIES.parents[2]).as_posix()
        allowed = ("?? " + prefix + "/runs/REG_A_QB2X1_N1/raw.csv\n" +
                   "?? " + prefix + "/analysis/PREFLIGHT_QA.json\n" +
                   "?? " + prefix + "/analysis/receipts/REG_A_QB2X1_N1_reanalysis.json\n" +
                   "?? " + prefix + "/analysis/attempts/PLATFORM_ATTEMPT1/archive_manifest.json\n")
        self.assertEqual(unexpected_registered_worktree_paths(allowed, {"REG_A_QB2X1_N1"}), [])
        extra = allowed + "?? " + prefix + "/scripts/unregistered.py\n"
        self.assertEqual(unexpected_registered_worktree_paths(extra, {"REG_A_QB2X1_N1"}), [prefix + "/scripts/unregistered.py"])

    def test_analyzer_refuses_raw_that_differs_from_solve_time_hash(self):
        with tempfile.TemporaryDirectory(prefix="bvm_repeat_raw_tamper_test_", dir=SERIES / "runs") as temporary:
            run_dir = Path(temporary)
            (run_dir / "raw.csv").write_text("time,V(QBIN)\n1e-12,0\n", encoding="utf-8")
            (run_dir / "metadata.json").write_text(json.dumps({"raw": {"sha256": "not-the-raw-hash"}}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "differs from solve-time metadata"):
                analyze_case.analyze_run(run_dir)
            self.assertFalse((run_dir / "analysis").exists())

    def test_numeric_units_unwrap_actual_grid_integration_and_half_open_windows(self):
        wrapped = analyze_case.unwrap([3.0, -3.0])
        delta = wrapped[-1] - wrapped[0]
        self.assertAlmostEqual(delta, 2.0 * 3.141592653589793 - 6.0, places=12)
        area = analyze_case.integrate([0.0, 0.1e-12, 0.3e-12], [0.0, 2.0, 2.0])
        self.assertAlmostEqual(area, 0.5e-12, places=24)
        times_ps = [0.0, 0.1, 0.2]
        self.assertEqual(analyze_case.indices_in(times_ps, [0.1, 0.2]), [1])

    def test_same_jj_phase_area_crosscheck_uses_same_actual_window(self):
        phi0 = analyze_case.PHI0
        rows = [
            {"time": 0.0, "P(BJ1|XBQ1)": 0.0, "V(BJ1|XBQ1)": phi0 / (2 * 0.5e-12),
             "P(BJ2|XBQ1)": 0.0, "V(BJ2|XBQ1)": 0.0},
            {"time": 0.5e-12, "P(BJ1|XBQ1)": 3.141592653589793, "V(BJ1|XBQ1)": phi0 / (2 * 0.5e-12),
             "P(BJ2|XBQ1)": 0.0, "V(BJ2|XBQ1)": 0.0},
            {"time": 1e-12, "P(BJ1|XBQ1)": 2 * 3.141592653589793, "V(BJ1|XBQ1)": phi0 / (2 * 0.5e-12),
             "P(BJ2|XBQ1)": 0.0, "V(BJ2|XBQ1)": 0.0},
            {"time": 1.5e-12, "P(BJ1|XBQ1)": 3 * 3.141592653589793, "V(BJ1|XBQ1)": phi0 / (2 * 0.5e-12),
             "P(BJ2|XBQ1)": 0.0, "V(BJ2|XBQ1)": 0.0},
            {"time": 2e-12, "P(BJ1|XBQ1)": 4 * 3.141592653589793, "V(BJ1|XBQ1)": phi0 / (2 * 0.5e-12),
             "P(BJ2|XBQ1)": 0.0, "V(BJ2|XBQ1)": 0.0},
        ]
        headers = list(rows[0])
        times_ps = [row["time"] * 1e12 for row in rows]
        phases = {key: analyze_case.unwrap([row[key] for row in rows])
                  for key in ("P(BJ1|XBQ1)", "P(BJ2|XBQ1)")}
        result = analyze_case.phase_area_crosscheck(headers, rows, times_ps, phases,
                                                    "P(BJ1|XBQ1)", "V(BJ1|XBQ1)", [0.0, 2.0])
        self.assertEqual(result["actual_last_sample_ps"], 1.5)
        self.assertAlmostEqual(result["phase_delta_turns_navigation"], 1.5, places=12)
        self.assertAlmostEqual(result["voltage_area_phi0"], 1.5, places=12)
        self.assertAlmostEqual(result["phase_area_residual_turns_navigation"], 0.0, places=12)

    def test_candidate_threshold_includes_exact_boundary_without_count_claim(self):
        times_ps = [1.0, 1.1, 1.2]
        rows = [{"V(R_TERM)": 99e-6}, {"V(R_TERM)": 100e-6}, {"V(R_TERM)": 99e-6}]
        candidates = analyze_case.candidate_clusters(times_ps, rows, "V(R_TERM)", 100e-6, 0.5, "T")
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["peak_time_ps"], 1.1)
        self.assertTrue(candidates[0]["candidate_only_not_event_count"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
