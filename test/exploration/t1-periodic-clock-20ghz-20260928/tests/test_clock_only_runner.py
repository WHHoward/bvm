from __future__ import annotations

import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

EXPERIMENT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EXPERIMENT / "scripts"))

import run_clock_only  # noqa: E402


class ClockOnlyRunnerTests(unittest.TestCase):
    def test_registered_config_renders_only_one_grounded_t1_with_series_pulse_drive(self):
        values, structure, probes = run_clock_only.load_config()
        with tempfile.TemporaryDirectory(prefix="t1-clock-deck-") as temp:
            deck = run_clock_only.render_deck(values, structure, Path(temp))
        self.assertEqual(values["PROBE_PROFILE"], "debug")
        self.assertEqual(values["T1_CLK_START"], "170p")
        self.assertEqual(values["T1_CLK_PERIOD"], "50p")
        self.assertEqual(len([line for line in deck.splitlines() if line.startswith("XT1 ")]), 1)
        self.assertIn("XT1 0 CLK S C N_BIAS1 N_BIAS2 N_BIAS3 T1", deck)
        self.assertIn("V_TRIG_CLK CLK_RAW 0 PULSE(0 1.2m 170p 1p 1p 2p 50p)", deck)
        self.assertIn("R_TRIG_CLK CLK_RAW CLK 5", deck)
        self.assertNotIn("R_CLK_QUIET", deck)
        self.assertNotIn("XBVM", deck)
        self.assertNotIn("XBQ", deck)
        self.assertNotIn("XCB", deck)
        self.assertIn(".tran 0.01p 370p", deck)
        for jj in ("B_J2", "B_J3", "B_J7", "B_J9", "B_J11"):
            self.assertIn(f"P({jj}|XT1)", probes)
            self.assertIn(f"V({jj}|XT1)", probes)
        self.assertIn("V(CLK_RAW)", probes)
        self.assertIn("V(CLK)", probes)
        self.assertIn("V(S)", probes)
        self.assertIn("V(C)", probes)

    def test_dry_run_invokes_no_solver_and_creates_no_run_directory(self):
        original_runs = run_clock_only.RUNS
        try:
            with tempfile.TemporaryDirectory(prefix="t1-clock-dry-run-test-") as temp:
                run_clock_only.RUNS = Path(temp) / "runs"
                self.assertFalse(run_clock_only.RUNS.exists())
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    status = run_clock_only.main(["--dry-run"])
                self.assertFalse(run_clock_only.RUNS.exists())
        finally:
            run_clock_only.RUNS = original_runs
        self.assertEqual(status, 0)
        self.assertIn('"solver_invoked": false', output.getvalue())
        self.assertEqual(output.getvalue().count("V_TRIG_CLK CLK_RAW"), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
