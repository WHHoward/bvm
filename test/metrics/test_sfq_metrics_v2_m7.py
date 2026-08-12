#!/usr/bin/env python3
"""M7 (M7-LITE-001) calibration tests: M7A synthetic ground truth, M7B
canonical-JTL pipeline replay, M7C historical regression.

All oracles are first-principles constants or direct independent raw-CSV
arithmetic written in this file (literal constants + elementary loops), never
calls to `sfq_metrics_v2` helpers. The M7B production comparison is the only
place the production analyzer is invoked, and only to check agreement with
the independent arithmetic at floating-point precision.

Claim ceiling: CALIBRATION only. The M7C bq_v4_sweep110 constants are
periodic historical phase-platform regression constants, NOT a count of
physical events and NOT a BQ interface Gate.
"""
from __future__ import annotations

import csv
import math
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import sfq_metrics_v2  # noqa: E402  (production; used only for M7B agreement check)

TAU = 2.0 * math.pi
PHI0 = 2.067833848e-15  # Wb, flux quantum (literal constant)


# ---------------------------------------------------------------------------
# independent elementary helpers (oracle-side arithmetic, not production)
# ---------------------------------------------------------------------------

def _half_open_indices(times: list[float], start_s: float, end_s: float) -> list[int]:
    """start_s <= t < end_s (half-open), elementary."""
    return [i for i, t in enumerate(times) if start_s <= t < end_s]


def _trapezoid(values: list[float], times: list[float]) -> float:
    """Elementary trapezoid on the actual time axis."""
    return sum(
        0.5 * (values[i] + values[i + 1]) * (times[i + 1] - times[i])
        for i in range(len(values) - 1)
    )


def _nearest_index(times: list[float], target_s: float) -> int:
    """Row whose actual time is closest to target_s."""
    return min(range(len(times)), key=lambda i: abs(times[i] - target_s))


def _write_csv(path: Path, time_s: list[float], cols: dict[str, list[float]]) -> None:
    header = ["time"] + list(cols)
    with path.open("w", encoding="utf-8") as f:
        f.write(",".join(f'"{h}"' for h in header) + "\n")
        for i, t in enumerate(time_s):
            row = [f"{t:e}"] + [f"{cols[c][i]!r}" for c in cols]
            f.write(",".join(row) + "\n")


# ---------------------------------------------------------------------------
# M7A — synthetic mathematical ground truth
# ---------------------------------------------------------------------------

class RadToTurnsSignTests(unittest.TestCase):
    """M7A: raw-rad -> turn conversion including sign (literal constants)."""

    def test_plus_two_pi_is_one_turn(self) -> None:
        self.assertAlmostEqual(sfq_metrics_v2.rad_to_turns(TAU), 1.0, places=12)

    def test_minus_two_pi_is_minus_one_turn(self) -> None:
        self.assertAlmostEqual(sfq_metrics_v2.rad_to_turns(-TAU), -1.0, places=12)

    def test_minus_pi_is_minus_half_turn(self) -> None:
        self.assertAlmostEqual(sfq_metrics_v2.rad_to_turns(-math.pi), -0.5, places=12)

    def test_plus_one_rad_is_one_over_two_pi(self) -> None:
        self.assertAlmostEqual(
            sfq_metrics_v2.rad_to_turns(1.0), 1.0 / TAU, places=12
        )


class TrapezoidNonUniformTests(unittest.TestCase):
    """M7A: non-uniform actual-time trapezoid (elementary constants)."""

    def test_constant_one_over_irregular_times(self) -> None:
        # 0.5*(1+1)*1 + 0.5*(1+1)*2 = 3.0
        self.assertEqual(sfq_metrics_v2.trapezoid_integral([1.0, 1.0, 1.0], [0.0, 1.0, 3.0]), 3.0)

    def test_varying_values(self) -> None:
        # 0.5*(0+2)*1 + 0.5*(2+0)*1 = 2.0
        self.assertEqual(sfq_metrics_v2.trapezoid_integral([0.0, 2.0, 0.0], [0.0, 1.0, 2.0]), 2.0)

    def test_rejects_short_input(self) -> None:
        with self.assertRaises(ValueError):
            sfq_metrics_v2.trapezoid_integral([1.0], [0.0])

    def test_rejects_length_mismatch(self) -> None:
        with self.assertRaises(ValueError):
            sfq_metrics_v2.trapezoid_integral([1.0, 2.0], [0.0, 1.0, 2.0])


class OrientationSignTests(unittest.TestCase):
    """M7A: same-JJ P/V orientation sign flips area but not phase."""

    def _run(self, orientation: int) -> dict:
        v0 = (PHI0 / TAU) * 2.0  # V for phi slope 2 rad/s
        times = [i * 0.1 for i in range(51)]
        phase: list[float] = []
        volt: list[float] = []
        for i, t in enumerate(times):
            if t < 1.0:
                phase.append(0.0)
                volt.append(0.0)
            elif t < 3.0:
                phase.append(2.0 * (t - 1.0))
                volt.append(v0)
            else:
                phase.append(4.0)
                volt.append(0.0)
        with tempfile.TemporaryDirectory() as td:
            csv_path = Path(td) / "sig.csv"
            _write_csv(csv_path, times, {"P(X)": phase, "V(X)": volt})
            plan = {
                "schema_version": 1,
                "windows_s": {
                    "pre": [0.0, 1.0],
                    "activity": [1.0, 3.0],
                    "post": [4.0, 5.0],
                    "cross": [0.5, 4.5],
                },
                "voltage_area": {
                    "P(X)": {
                        "voltage_column": "V(X)",
                        "orientation": orientation,
                        "endpoint_window": "cross",
                    }
                },
            }
            return sfq_metrics_v2.voltage_area_analyze(str(csv_path), plan)

    def test_orientation_flips_area_sign(self) -> None:
        plus = self._run(1)["runs"]["signal"]["P(X)"]
        minus = self._run(-1)["runs"]["signal"]["P(X)"]
        self.assertEqual(plus["phase_delta_rad"], minus["phase_delta_rad"])
        self.assertAlmostEqual(plus["area_turns"], -minus["area_turns"], places=12)

    def test_residual_zero_for_exact_synthetic(self) -> None:
        m = self._run(1)["runs"]["signal"]["P(X)"]
        # phi ramps 2 rad/s over 2 s -> 4 rad -> 4/(2pi) turns; area identical.
        self.assertAlmostEqual(m["phase_delta_turns"], 4.0 / TAU, places=12)
        self.assertAlmostEqual(m["area_turns"], 4.0 / TAU, places=12)
        self.assertAlmostEqual(m["residual_turns"], 0.0, places=12)


class WindowAndClusteringTests(unittest.TestCase):
    """M7A: half-open endpoints, strict threshold, cluster separation."""

    def _analyze_windowed(self, phase: list[float], control: list[float] | None = None) -> dict:
        times = [i * 0.1 for i in range(130)]
        with tempfile.TemporaryDirectory() as td:
            sig = Path(td) / "sig.csv"
            _write_csv(sig, times, {"P(X)": phase})
            ctl = None
            if control is not None:
                ctl_path = Path(td) / "ctl.csv"
                _write_csv(ctl_path, times, {"P(X)": control})
                ctl = str(ctl_path)
            plan = {
                "schema_version": 1,
                "windows_s": {
                    "pre": [0.0, 2.0],
                    "activity": [2.0, 8.0],
                    "post": [10.0, 12.0],
                },
                "phase_directions": {"P(X)": 1},
                "activity_threshold_rad": 0.3,
            }
            return sfq_metrics_v2.windowed_analyze(str(sig), plan, control_csv=ctl)

    def test_half_open_window_excludes_end(self) -> None:
        # pre [0.0, 2.0) on 0.1 grid -> t=0.0..1.9 (20 samples), t=2.0 excluded.
        result = self._analyze_windowed([0.0] * 130)
        col = result["signal"]["P(X)"]
        self.assertEqual(col["pre"]["sample_count"], 20)
        self.assertEqual(col["pre"]["selected_last_time_s"], 1.9)
        self.assertEqual(col["activity"]["sample_count"], 60)  # t=2.0..7.9
        self.assertEqual(col["post"]["sample_count"], 20)

    def test_strict_threshold_equality_inactive(self) -> None:
        # exact 0.25 rad increments (2^-2 exact) with threshold 0.3: active.
        # threshold 0.25: equality inactive.
        phase = [0.0] * 20 + [0.25 * k for k in range(0, 11)] + [2.5] * 99
        plan = {
            "schema_version": 1,
            "windows_s": {"pre": [0.0, 2.0], "activity": [2.0, 8.0], "post": [10.0, 12.0]},
            "phase_directions": {"P(X)": 1},
            "activity_threshold_rad": 0.25,
        }
        times = [i * 0.1 for i in range(130)]
        with tempfile.TemporaryDirectory() as td:
            sig = Path(td) / "sig.csv"
            _write_csv(sig, times, {"P(X)": phase})
            result = sfq_metrics_v2.windowed_analyze(str(sig), plan)
        col = result["signal"]["P(X)"]
        self.assertEqual(col["over_threshold_sample_count"], 0)
        self.assertEqual(col["activity_clusters"], [])

    def test_separated_clusters_not_bridged(self) -> None:
        phase = [0.0] * 130
        for i in range(20, 25):
            phase[i + 1] = phase[i] + 0.5
        for i in range(25, 40):
            phase[i + 1] = phase[i]
        for i in range(40, 45):
            phase[i + 1] = phase[i] + 0.5
        for i in range(45, 130):
            phase[i] = 5.0
        result = self._analyze_windowed(phase)
        col = result["signal"]["P(X)"]
        self.assertEqual(len(col["activity_clusters"]), 2)
        self.assertEqual(col["over_threshold_sample_count"], 10)

    def test_matched_control_subtraction(self) -> None:
        # signal and control share a startup ramp; corrected delta is 5.0 exactly.
        def _with_startup(post_flat: float) -> list[float]:
            phase = [0.0] * 130
            for i in range(0, 20):
                phase[i + 1] = phase[i] + 0.1
            for i in range(20, 30):
                phase[i + 1] = phase[i] + (0.5 if post_flat > 2.0 else 0.0)
            for i in range(30, 130):
                phase[i] = post_flat
            return phase

        result = self._analyze_windowed(_with_startup(7.0), control=_with_startup(2.0))
        corrected = result["control_corrected"]["P(X)"]["corrected_delta_rad"]
        self.assertAlmostEqual(corrected, 5.0, places=12)

    def test_malformed_input_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            bad = Path(td) / "bad.csv"
            bad.write_text(
                'time,"P(X)"\n0.0,0.0\n0.1,1.0\n0.1,2.0\n', encoding="utf-8"
            )
            with self.assertRaises(ValueError):
                sfq_metrics_v2.windowed_analyze(str(bad), {
                    "schema_version": 1,
                    "windows_s": {"pre": [0.0, 1.0], "activity": [1.0, 2.0], "post": [2.0, 3.0]},
                    "phase_directions": {"P(X)": 1},
                    "activity_threshold_rad": 0.3,
                })


# ---------------------------------------------------------------------------
# M7B — canonical JTL measurement-pipeline replay
# ---------------------------------------------------------------------------

class CanonicalJtlCalibrationTests(unittest.TestCase):
    """M7B: run CSV from attempts/A01/runs/m7-jtl-cal-20260812-01; independent
    arithmetic must agree with the production output at float precision."""

    RUN_CSV = (
        REPO_ROOT
        / "research/tasks/M7-LITE-001/attempts/A01/runs/m7-jtl-cal-20260812-01"
        / "raw/m7-jtl-cal-20260812-01.csv"
    )
    WINDOW = (6e-12, 50e-12)  # predeclared post-bias / end-of-run window

    def _csv(self) -> tuple[list[float], dict[str, list[float]]]:
        self.assertTrue(self.RUN_CSV.is_file(), f"missing run CSV: {self.RUN_CSV}")
        with self.RUN_CSV.open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        times = [float(r["time"]) for r in rows]
        cols = {c: [float(r[c]) for r in rows] for c in rows[0].keys() if c != "time"}
        for c in ("V(B1|XDUT)", "V(B2|XDUT)", "P(B1|XDUT)", "P(B2|XDUT)"):
            self.assertIn(c, cols)
        return times, cols

    def test_independent_arithmetic_matches_production(self) -> None:
        times, cols = self._csv()
        lo, hi = self.WINDOW
        for j in (1, 2):
            p_col, v_col = f"P(B{j}|XDUT)", f"V(B{j}|XDUT)"
            idx = _half_open_indices(times, lo, hi)
            self.assertGreaterEqual(len(idx), 2)
            first, last = idx[0], idx[-1]
            # independent arithmetic
            phase_delta_rad = cols[p_col][last] - cols[p_col][first]
            area = _trapezoid([cols[v_col][i] for i in idx], [times[i] for i in idx])
            indep = {
                "phase_delta_turns": phase_delta_rad / TAU,
                "area_turns": area / PHI0,
                "residual_turns": phase_delta_rad / TAU - area / PHI0,
            }
            # production output on the same window / same JJ pair
            plan = {
                "schema_version": 1,
                "windows_s": {
                    "pre": [0.0, 5e-12],
                    "activity": [5e-12, 6e-12],
                    "post": [50e-12, 51e-12],
                    "cross": [lo, hi],
                },
                "voltage_area": {
                    p_col: {
                        "voltage_column": v_col,
                        "orientation": 1,
                        "endpoint_window": "cross",
                    }
                },
            }
            result = sfq_metrics_v2.voltage_area_analyze(str(self.RUN_CSV), plan)
            prod = result["runs"]["signal"][p_col]
            self.assertAlmostEqual(
                indep["phase_delta_turns"], prod["phase_delta_turns"], places=9
            )
            self.assertAlmostEqual(indep["area_turns"], prod["area_turns"], places=9)
            self.assertAlmostEqual(
                indep["residual_turns"], prod["residual_turns"], places=9
            )
            # report raw signed residual for the record
            print(f"M7B B{j} raw signed residual (turns): {prod['residual_turns']:.6e}")


# ---------------------------------------------------------------------------
# M7C — deterministic historical regression
# ---------------------------------------------------------------------------

class HistoricalDcsfqReplayTests(unittest.TestCase):
    """M7C: frozen DCSFQ 300u - 0u matched-control replay (AC4 constants)."""

    DATA = REPO_ROOT / "test/final/interface/data"
    EXPECTED_TURNS = {
        "P(B1|XDCSFQ)": 0.999999982941839,
        "P(B2|XDCSFQ)": 1.00000006251931,
        "P(B3|XDCSFQ)": 1.00000001477283,
    }
    EXPECTED_CLUSTERS = {"P(B1|XDCSFQ)": 1, "P(B2|XDCSFQ)": 0, "P(B3|XDCSFQ)": 1}
    FIXED_PLAN = {
        "schema_version": 1,
        "windows_s": {
            "pre": [6e-12, 9e-12],
            "activity": [9e-12, 50e-12],
            "post": [100e-12, 190e-12],
        },
        "phase_directions": {
            "P(B1|XDCSFQ)": -1,
            "P(B2|XDCSFQ)": 1,
            "P(B3|XDCSFQ)": 1,
        },
        "activity_threshold_rad": 0.3,
    }

    def test_frozen_replay_constants(self) -> None:
        sig = self.DATA / "test_dcsfq_behavior_bump_300u.csv"
        ctl = self.DATA / "test_dcsfq_behavior_bump_0.csv"
        result = sfq_metrics_v2.windowed_analyze(
            str(sig), self.FIXED_PLAN, control_csv=str(ctl)
        )
        self.assertEqual(result["control_applied"], True)
        for col, expected in self.EXPECTED_TURNS.items():
            s = result["signal"][col]
            self.assertEqual(s["pre"]["sample_count"], 30)
            self.assertEqual(s["activity"]["sample_count"], 409)
            self.assertEqual(s["post"]["sample_count"], 900)
            corrected = result["control_corrected"][col]
            self.assertLess(
                abs((corrected["corrected_delta_turns"] - expected) * TAU), 1e-9
            )
            self.assertEqual(len(s["activity_clusters"]), self.EXPECTED_CLUSTERS[col])
            ctl_act = result["zero_input_control"][col]
            self.assertEqual(ctl_act["activity_clusters"], [])


class HistoricalBqV4RegressionTests(unittest.TestCase):
    """M7C: bq_v4_sweep110.csv JTL-B1 phase increments at the actual-time
    samples 49/99/149/199/249/299 ps relative to the actual 5 ps sample.

    These are periodic historical phase-platform regression constants, NOT a
    count of physical events and NOT a BQ interface Gate.
    """

    CSV = REPO_ROOT / "test/final/qb/data/bq_v4_sweep110.csv"
    EXPECTED = [
        1.0133756508381797,
        2.0133738512446557,
        3.013374598130222,
        4.0133737534663565,
        5.013374500351922,
        6.013373655688058,
    ]
    TARGETS_PS = [49, 99, 149, 199, 249, 299]

    def test_phase_increments_at_actual_samples(self) -> None:
        with self.CSV.open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        times = [float(r["time"]) for r in rows]
        phase = [float(r["P(B1|XJTL)"]) for r in rows]
        ref_i = _nearest_index(times, 5e-12)
        self.assertLess(abs(times[ref_i] - 5e-12), 0.11e-12)
        for target_ps, expected in zip(self.TARGETS_PS, self.EXPECTED):
            i = _nearest_index(times, target_ps * 1e-12)
            self.assertLess(abs(times[i] - target_ps * 1e-12), 0.11e-12)
            turns = (phase[i] - phase[ref_i]) / TAU
            self.assertLess(abs(turns - expected), 1e-9)  # absolute tolerance


if __name__ == "__main__":
    unittest.main(verbosity=2)
