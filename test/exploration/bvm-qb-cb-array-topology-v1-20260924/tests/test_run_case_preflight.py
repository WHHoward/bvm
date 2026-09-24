from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SERIES = Path(__file__).resolve().parents[1]
REPO = next(path for path in (SERIES, *SERIES.parents) if (path / ".git").exists())
sys.path.insert(0, str(SERIES / "scripts"))
sys.path.insert(0, str(REPO / "scripts"))

import run_case  # noqa: E402
from bvmtools import provenance  # noqa: E402
from config import USER_CASE_KEYS, load_env  # noqa: E402
from stimulus import load_stimulus  # noqa: E402


class StopBeforePhysicalSolve(Exception):
    pass


class RunCasePreflightTests(unittest.TestCase):
    def test_selected_mask_is_available_to_preflight_before_solver_call(self):
        user_values = load_env(SERIES / "USER_CASE.env", USER_CASE_KEYS)
        stimulus_values = load_stimulus(SERIES / "STIMULUS.env")
        mask = user_values["MASKS"].split(",")[0]

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            series_root = root / "series"
            (series_root / "runs").mkdir(parents=True)
            fake_solver = root / "josim-never-invoked"
            fake_solver.write_text("mock solver placeholder\n", encoding="utf-8")
            run_id = f"A999_T999_M{mask}"

            def stop_at_solver(command, **kwargs):
                self.assertEqual(Path(command[0]), fake_solver.resolve())
                raise StopBeforePhysicalSolve

            with patch.object(run_case, "SERIES", series_root), \
                 patch.object(provenance, "git_snapshot", return_value={"head": "fixture-head"}), \
                 patch.object(provenance, "solver_provenance", return_value={
                     "path": str(fake_solver), "sha256": "fixture-sha",
                     "version_returncode": 0, "version_stdout": "fixture-version",
                 }), \
                 patch.object(run_case.subprocess, "run", side_effect=stop_at_solver) as solver_call:
                with self.assertRaises(StopBeforePhysicalSolve):
                    run_case.execute_run(
                        user_values, stimulus_values, mask, run_id=run_id, solver=fake_solver,
                        user_snapshot_text=run_case.stable_env(user_values),
                        stimulus_snapshot_text=run_case.stable_env(stimulus_values),
                    )

            run_dir = series_root / "runs" / run_id
            self.assertTrue((run_dir / "PREFLIGHT.md").is_file())
            preflight = (run_dir / "PREFLIGHT.md").read_text(encoding="utf-8")
            self.assertIn(f"FINAL READ MASK: `{mask}`", preflight)
            solver_call.assert_called_once()
            self.assertFalse((run_dir / "raw.csv").exists())
            self.assertFalse((run_dir / "run.log").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
