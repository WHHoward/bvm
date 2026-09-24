from __future__ import annotations

import contextlib
import hashlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SERIES = Path(__file__).resolve().parents[1]
REPO = next(path for path in (SERIES, *SERIES.parents) if (path / ".git").exists())
sys.path.insert(0, str(SERIES / "scripts"))

import try_case  # noqa: E402
import submit  # noqa: E402
from config import COMPONENT_KEYS, USER_CASE_KEYS, load_env  # noqa: E402
from stimulus import load_stimulus  # noqa: E402


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class TryCaseTests(unittest.TestCase):
    def test_dry_run_set_is_visible_and_has_no_batch_run_or_solver_side_effects(self):
        user_path = SERIES / "USER_CASE.env"
        stimulus_path = SERIES / "STIMULUS.env"
        before = (sha(user_path), sha(stimulus_path),
                  sorted(path.name for path in (SERIES / "runs").iterdir()),
                  sorted(path.name for path in (SERIES / "batches").iterdir())
                  if (SERIES / "batches").exists() else [])
        output, error = io.StringIO(), io.StringIO()
        baseline = load_env(user_path, USER_CASE_KEYS)
        reference = try_case.load_reference()
        baseline.update({key: reference[key] for key in COMPONENT_KEYS})
        baseline.update({"NAME": "dry_run_test", "ARRAY_SIZE": "2", "MASKS": "00,01,10,11",
                         "QB_CB": "0,1", "SJTL_COUNT": "1,1", "POST_SJTL_CB": "0,0"})
        with tempfile.TemporaryDirectory() as tmp:
            user_fixture = Path(tmp) / "USER_CASE.env"
            user_fixture.write_text(try_case.stable_env(baseline), encoding="utf-8")
            with patch.object(try_case.subprocess, "run", side_effect=AssertionError("process invoked")), \
                 contextlib.redirect_stdout(output), contextlib.redirect_stderr(error):
                rc = try_case.main(["--dry-run", "--user-case", str(user_fixture),
                                    "--set", "QB_BJ3_AREA=2.2"])
        self.assertEqual(rc, 0, error.getvalue())
        self.assertIn("QB_BJ3_AREA 2 -> 2.2", output.getvalue())
        self.assertIn("physical_solve_count = 4", output.getvalue())
        self.assertIn("No physical solve executed.", output.getvalue())
        after = (sha(user_path), sha(stimulus_path),
                 sorted(path.name for path in (SERIES / "runs").iterdir()),
                 sorted(path.name for path in (SERIES / "batches").iterdir())
                 if (SERIES / "batches").exists() else [])
        self.assertEqual(after, before)

    def test_unknown_set_hard_stops_and_mask_override_changes_solve_count(self):
        errors = io.StringIO()
        with contextlib.redirect_stderr(errors):
            rc = try_case.main(["--dry-run", "--set", "UNKNOWN=123"])
        self.assertEqual(rc, 2)
        self.assertIn("unknown --set key", errors.getvalue())

        current = load_env(SERIES / "USER_CASE.env", USER_CASE_KEYS)
        zeros, ones = "0" * int(current["ARRAY_SIZE"]), "1" * int(current["ARRAY_SIZE"])
        mask_override = f"MASKS={zeros},{ones}"
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            rc = try_case.main(["--dry-run", "--set", mask_override])
        self.assertEqual(rc, 0)
        self.assertIn(mask_override, output.getvalue())
        self.assertIn("physical_solve_count = 2", output.getvalue())

    def test_actual_batch_model_executes_each_requested_mask_once_with_stubbed_runner(self):
        with tempfile.TemporaryDirectory() as tmp:
            series = Path(tmp) / "series"
            (series / "tests" / "fixtures").mkdir(parents=True)
            (series / "runs").mkdir()
            user_path = SERIES / "USER_CASE.env"
            stimulus_path = SERIES / "STIMULUS.env"
            user_values = load_env(user_path, USER_CASE_KEYS)
            user_values.update({"NAME": "stub_batch", "ARRAY_SIZE": "2", "MASKS": "01,11",
                                "QB_CB": "0,1", "SJTL_COUNT": "1,1", "POST_SJTL_CB": "0,0"})
            stimulus_values = load_stimulus(stimulus_path)
            params = try_case.validate_user_case(user_values)
            user_text = try_case.stable_env(user_values)
            stimulus_text = try_case.stable_env(stimulus_values)
            calls: list[str] = []

            def fake_runner(values, stimulus, mask, *, run_id, solver,
                            user_snapshot_text, stimulus_snapshot_text, overrides):
                calls.append(mask)
                run_dir = series / "runs" / run_id
                run_dir.mkdir()
                raw_bytes = f"fixture-only {mask}\n".encode()
                raw_sha = hashlib.sha256(raw_bytes).hexdigest()
                (run_dir / "raw.csv").write_bytes(raw_bytes)
                plot_pages = []
                for relative in sorted(submit.REQUIRED_PLOT_FILES):
                    plot_path = run_dir / relative
                    plot_path.parent.mkdir(parents=True, exist_ok=True)
                    plot_bytes = f"fixture plot {mask} {relative}\n".encode()
                    plot_path.write_bytes(plot_bytes)
                    plot_pages.append({"path": relative,
                                       "sha256": hashlib.sha256(plot_bytes).hexdigest(),
                                       "status": "PASS"})
                parameter_path = run_dir / "parameter_manifest.json"
                parameter_path.write_text(json.dumps({"mask": mask}), encoding="utf-8")
                parameter_sha = hashlib.sha256(parameter_path.read_bytes()).hexdigest()
                result = {"run_id": run_id, "mask": mask, "solver_exit_code": 0,
                          "artifact_status": "VALID", "raw_sha256": raw_sha,
                          "plot_qa": {"status": "PASS"}, "physical_solve_count": 1}
                provenance = {"physical_solve_count": 1, "raw": {"sha256": raw_sha},
                              "parameter_manifest": {"sha256": parameter_sha}}
                (run_dir / "result.json").write_text(json.dumps(result), encoding="utf-8")
                (run_dir / "analysis" / "plot_qa.json").parent.mkdir(parents=True, exist_ok=True)
                plot_qa = {"status": "PASS", "page_count": 5, "pages": plot_pages,
                           "raw_sha256_before": raw_sha, "raw_sha256_after": raw_sha,
                           "raw_immutable": True, "shared_asset_reference_pass": True,
                           "full_stored_time_range": True}
                (run_dir / "analysis" / "plot_qa.json").write_text(
                    json.dumps(plot_qa), encoding="utf-8")
                (run_dir / "provenance.json").write_text(json.dumps(provenance), encoding="utf-8")
                return 0

            manifest = try_case.execute_batch(
                user_values, stimulus_values, params, user_text, stimulus_text, [], {
                    "bvm": {}, "qb": {}, "cb": {}, "sjtl": {}, "topology": {},
                    "solver": {}, "stimulus_reference": {},
                },
                series_root=series, head="fixture-head", runner=fake_runner,
            )
            self.assertEqual(calls, ["01", "11"])
            self.assertEqual(manifest["status"], "COMPLETE_MECHANICAL")
            self.assertEqual(manifest["total_physical_solve_count"], 2)
            self.assertEqual(len(manifest["runs"]), 2)
            self.assertTrue((series / "analysis" / "LATEST_BATCH.json").is_file())
            self.assertFalse(any((series / "batches" / manifest["batch_id"]).glob("raw.csv")))
            runs, batch = submit.validate_batch(series)
            self.assertEqual(len(runs), 2)
            self.assertEqual(batch["status"], "COMPLETE_MECHANICAL")

    def test_solver_failure_preserves_attempt_and_stops_remaining_masks_without_retry(self):
        with tempfile.TemporaryDirectory() as tmp:
            series = Path(tmp) / "series"
            (series / "tests" / "fixtures").mkdir(parents=True)
            (series / "runs").mkdir()
            user_values = load_env(SERIES / "USER_CASE.env", USER_CASE_KEYS)
            user_values.update({"NAME": "failed_batch", "ARRAY_SIZE": "2", "MASKS": "01,11",
                                "QB_CB": "0,1", "SJTL_COUNT": "1,1", "POST_SJTL_CB": "0,0"})
            stimulus_values = load_stimulus(SERIES / "STIMULUS.env")
            params = try_case.validate_user_case(user_values)
            calls: list[str] = []

            def failed_runner(values, stimulus, mask, *, run_id, **kwargs):
                calls.append(mask)
                run_dir = series / "runs" / run_id
                run_dir.mkdir()
                (run_dir / "result.json").write_text(json.dumps({
                    "run_id": run_id, "mask": mask, "status": "SOLVER_FAIL",
                    "solver_exit_code": 1, "artifact_status": "INVALID",
                    "physical_solve_count": 1, "plot_qa": {"status": "NOT_RUN"},
                }), encoding="utf-8")
                (run_dir / "provenance.json").write_text(json.dumps({
                    "physical_solve_count": 1,
                }), encoding="utf-8")
                return 1

            manifest = try_case.execute_batch(
                user_values, stimulus_values, params, try_case.stable_env(user_values),
                try_case.stable_env(stimulus_values), [], {
                    "bvm": {}, "qb": {}, "cb": {}, "sjtl": {}, "topology": {},
                    "solver": {}, "stimulus_reference": {},
                }, series_root=series, head="fixture-head", runner=failed_runner,
            )
            self.assertEqual(calls, ["01"])
            self.assertEqual(manifest["status"], "SOLVER_FAILURE")
            self.assertEqual(manifest["total_physical_solve_count"], 1)
            self.assertEqual(len(manifest["runs"]), 1)
            self.assertTrue((series / "runs" / manifest["runs"][0]["run_id"] / "result.json").is_file())


if __name__ == "__main__":
    unittest.main(verbosity=2)
