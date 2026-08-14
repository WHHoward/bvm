#!/usr/bin/env python3
"""M4 unit-layer tests for sfq_metrics_v2.

Expectations are written from first principles (independent constants), never
computed from the implementation under test. Runs with stdlib only: no JoSIM,
no network, no installed dependencies.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import sfq_metrics_v2  # noqa: E402

# Independent constants (hand-written, not derived from the implementation):
TAU = 2.0 * math.pi  # one full turn in radians
HALF_TURN_TURNS = 0.75  # 1.5*pi rad -> 3/4 turn, from 1.5/2 = 0.75
ONE_RAD_TURNS = 0.1591549430918953  # 1/(2*pi), independent decimal


def write_csv(path: Path, columns: dict[str, list[float]]) -> None:
    n = max(len(v) for v in columns.values())
    header = ["time"] + list(columns)
    with path.open("w", encoding="utf-8") as f:
        f.write(",".join(f'"{h}"' for h in header) + "\n")
        for i in range(n):
            t = i * 0.1  # 0.1 s spacing, actual dt from the time column
            row = [str(t)] + [str(columns[c][i]) for c in columns]
            f.write(",".join(row) + "\n")


class RadToTurnsTests(unittest.TestCase):
    """AC2: independent constant assertions, no circular expectations."""

    def test_zero_rad_is_zero_turns(self) -> None:
        self.assertEqual(sfq_metrics_v2.rad_to_turns(0.0), 0.0)

    def test_plus_two_pi_is_one_turn(self) -> None:
        self.assertAlmostEqual(sfq_metrics_v2.rad_to_turns(TAU), 1.0, places=12)

    def test_minus_two_pi_is_minus_one_turn(self) -> None:
        self.assertAlmostEqual(sfq_metrics_v2.rad_to_turns(-TAU), -1.0, places=12)

    def test_plus_four_pi_is_two_turns(self) -> None:
        self.assertAlmostEqual(sfq_metrics_v2.rad_to_turns(2.0 * TAU), 2.0, places=12)

    def test_non_integer_turns(self) -> None:
        self.assertAlmostEqual(
            sfq_metrics_v2.rad_to_turns(1.5 * math.pi), HALF_TURN_TURNS, places=12
        )
        self.assertAlmostEqual(sfq_metrics_v2.rad_to_turns(1.0), ONE_RAD_TURNS, places=12)


class AnalyzeTests(unittest.TestCase):
    """AC1: raw rad preserved AND turns derived explicitly."""

    def _run(self, columns: dict[str, list[float]], threshold_rad: float = 0.3):
        with tempfile.TemporaryDirectory(prefix="m4metrics-") as tmp:
            csv_path = Path(tmp) / "synth.csv"
            write_csv(csv_path, columns)
            return sfq_metrics_v2.analyze(csv_path, threshold_rad=threshold_rad)

    def test_endpoint_delta_preserves_rad_and_derives_turns(self) -> None:
        # +1 turn: raw phase goes 0 -> 2*pi rad
        result = self._run({"P(A)": [0.0, 1.0, 3.0, TAU]})
        junction = result["phases"]["P(A)"]
        self.assertAlmostEqual(junction["phase_delta_rad"], TAU, places=12)
        self.assertAlmostEqual(junction["phase_delta_turns"], 1.0, places=12)

    def test_negative_and_quadruple_turns(self) -> None:
        result = self._run(
            {"P(A)": [TAU, TAU, 1.0, 0.0], "P(B)": [0.0, 1.0, 3.0, 2.0 * TAU]}
        )
        self.assertAlmostEqual(result["phases"]["P(A)"]["phase_delta_turns"], -1.0, places=12)
        self.assertAlmostEqual(result["phases"]["P(B)"]["phase_delta_turns"], 2.0, places=12)

    def test_units_and_disclaimer_in_metadata(self) -> None:
        result = self._run({"P(A)": [0.0, TAU]})
        self.assertEqual(result["units"]["phase"], "rad")
        self.assertIn("turns", result["units"])
        disclaimer = result["disclaimer"]
        self.assertIn("M5", disclaimer)
        self.assertIn("M6", disclaimer)
        self.assertIn("physical Gate", disclaimer)

    def test_no_event_semantics_field_names(self) -> None:
        result = self._run({"P(A)": [0.0, 1.0, 3.0, TAU]})
        forbidden = {"fast_events", "pulse_count", "sfq_count", "event_count"}
        def collect_keys(obj: object) -> set[str]:
            keys: set[str] = set()
            if isinstance(obj, dict):
                keys.update(obj.keys())
                for value in obj.values():
                    keys |= collect_keys(value)
            return keys
        keys = collect_keys(result)
        self.assertEqual(keys & forbidden, set())
        # AC3 applies to per-sample threshold STATISTICS (junction fields),
        # not to configuration keys like threshold_rad (an input setting).
        for col, junction in result["phases"].items():
            for key in junction:
                if "threshold" in key or "activity" in key:
                    self.assertTrue(
                        "sample" in key or "interval" in key,
                        f"activity/threshold statistic must use sample/interval "
                        f"naming: {col}.{key!r}",
                    )

    def test_activity_counts_samples_and_intervals(self) -> None:
        # 5 slow diffs, 3 consecutive big diffs (one interval),
        # 5 slow, 1 isolated big diff (second interval), 5 slow
        slow = 0.01
        big = 0.5
        phase = [0.0]
        for _ in range(5):
            phase.append(phase[-1] + slow)
        for _ in range(3):
            phase.append(phase[-1] + big)
        for _ in range(5):
            phase.append(phase[-1] + slow)
        phase.append(phase[-1] + big)
        for _ in range(5):
            phase.append(phase[-1] + slow)
        result = self._run({"P(A)": phase})
        junction = result["phases"]["P(A)"]
        self.assertEqual(junction["over_threshold_sample_count"], 4)
        self.assertEqual(len(junction["activity_intervals"]), 2)

    def test_time_axis_comes_from_csv_column(self) -> None:
        result = self._run({"P(A)": [0.0, 0.0, 0.0]})
        self.assertEqual(result["t_start_s"], 0.0)
        self.assertEqual(result["t_end_s"], 0.2)
        self.assertAlmostEqual(result["dt_s"], 0.1)


class CliTests(unittest.TestCase):
    """AC1/AC4: help text states units; JSON output on stdout."""

    def _cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "sfq_metrics_v2.py"), *args],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
        )

    def test_help_lists_units(self) -> None:
        proc = self._cli("--help")
        self.assertEqual(proc.returncode, 0)
        self.assertIn("rad", proc.stdout)
        self.assertIn("turns", proc.stdout)

    def test_cli_json_output(self) -> None:
        with tempfile.TemporaryDirectory(prefix="m4metrics-") as tmp:
            csv_path = Path(tmp) / "synth.csv"
            write_csv(csv_path, {"P(A)": [0.0, 1.0, TAU]})
            proc = self._cli(str(csv_path))
            self.assertEqual(proc.returncode, 0, proc.stderr)
            result = json.loads(proc.stdout)
            self.assertAlmostEqual(
                result["phases"]["P(A)"]["phase_delta_turns"], 1.0, places=12
            )

    def test_auto_discovers_phase_columns(self) -> None:
        with tempfile.TemporaryDirectory(prefix="m4metrics-") as tmp:
            csv_path = Path(tmp) / "synth.csv"
            write_csv(csv_path, {"V(VIN)": [0.1, 0.2], "P(B01)": [0.0, TAU]})
            proc = self._cli(str(csv_path))
            result = json.loads(proc.stdout)
            self.assertIn("P(B01)", result["phases"])
            self.assertNotIn("V(VIN)", result["phases"])


class FrozenFilesTests(unittest.TestCase):
    """AC5: v1 script content unchanged (hash from the request baseline manifest)."""

    V1_SHA256 = "84600d3e5c80374ae30c77cf2ad000964416729a3f07f4b7e53dec13e03c6264"

    def test_v1_metrics_script_unchanged(self) -> None:
        digest = hashlib.sha256((SCRIPTS_DIR / "sfq_metrics.py").read_bytes()).hexdigest()
        self.assertEqual(digest, self.V1_SHA256)

    def test_module_docstring_carries_m4_boundary(self) -> None:
        doc = sfq_metrics_v2.__doc__ or ""
        self.assertIn("rad", doc)
        self.assertIn("turns", doc)
        self.assertIn("M4", doc)


if __name__ == "__main__":
    unittest.main(verbosity=2)
