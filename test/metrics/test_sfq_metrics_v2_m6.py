#!/usr/bin/env python3
"""M6 (JH-20260811-M6-001) same-JJ phase vs voltage-area cross-check tests.

Expectations are first-principles constants (hand-computed areas, exact
decimal values, Phi0 constructions) and never call the production
integration under test. stdlib only: no JoSIM, no network, no installed
dependencies.
"""
from __future__ import annotations

import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import sfq_metrics_v2  # noqa: E402

TAU = 2.0 * math.pi
PHI0 = 2.067833848e-15  # flux quantum, Wb (independent constant)

# Synthetic grid: t = i * 0.1 s, 51 samples (0.0 .. 5.0).
N = 51
DT = 0.1

PLAN = {
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
            "orientation": 1,
            "endpoint_window": "cross",
        }
    },
}


def _write_csv(path: Path, phase: list[float], volt: list[float]) -> None:
    assert len(phase) == len(volt)
    with path.open("w", encoding="utf-8") as f:
        f.write('time,"P(X)","V(X)"\n')
        for i, (p, v) in enumerate(zip(phase, volt)):
            f.write(f"{i * DT:e},{p!r},{v!r}\n")


class TrapezoidTests(unittest.TestCase):
    """Trapezoidal integration on the ACTUAL (non-uniform) time axis."""

    def test_nonuniform_time_first_principles(self) -> None:
        # V constant 1.0 over t = [0, 1, 3]: 0.5*(1+1)*1 + 0.5*(1+1)*2 = 3.0.
        self.assertEqual(
            sfq_metrics_v2.trapezoid_integral([1.0, 1.0, 1.0], [0.0, 1.0, 3.0]),
            3.0,
        )

    def test_varying_values(self) -> None:
        # V = [0, 2, 0] over t = [0, 1, 2]: 0.5*2*1 + 0.5*2*1 = 2.0.
        self.assertEqual(
            sfq_metrics_v2.trapezoid_integral([0.0, 2.0, 0.0], [0.0, 1.0, 2.0]),
            2.0,
        )

    def test_rejects_length_mismatch(self) -> None:
        with self.assertRaises(ValueError):
            sfq_metrics_v2.trapezoid_integral([1.0, 2.0], [0.0, 1.0, 2.0])

    def test_rejects_single_sample(self) -> None:
        with self.assertRaises(ValueError):
            sfq_metrics_v2.trapezoid_integral([1.0], [0.0])


class Phi0ConversionTests(unittest.TestCase):
    """area_turns = orientation * trapezoid(V, time) / Phi0."""

    def test_constant_one_volt_for_phi0_seconds_is_one_turn(self) -> None:
        # int V dt = 1.0 V * Phi0 s = Phi0 Wb -> exactly 1.0 turn.
        self.assertEqual(
            sfq_metrics_v2.trapezoid_integral([1.0, 1.0], [0.0, PHI0]) / PHI0,
            1.0,
        )

    def test_half_volt_for_phi0_seconds_is_half_turn(self) -> None:
        self.assertAlmostEqual(
            sfq_metrics_v2.trapezoid_integral([0.5, 0.5], [0.0, PHI0]) / PHI0,
            0.5,
            places=15,
        )


class EndpointConsistencyTests(unittest.TestCase):
    """AC2: the same window's first/last actual samples drive BOTH the phase
    endpoints and the voltage trapezoid (never the trace edges)."""

    def _result(self, phase, volt, plan=PLAN):
        with tempfile.TemporaryDirectory() as td:
            csv = Path(td) / "sig.csv"
            _write_csv(csv, phase, volt)
            return sfq_metrics_v2.voltage_area_analyze(str(csv), plan)

    def test_window_cut_through_trace_uses_selected_samples(self) -> None:
        # Window [0.5, 4.5) on the 0.1 s grid selects t = 0.5..4.4 (40
        # samples). With P(t) = t and V(t) = 2.0 const:
        #   phase_first = 0.5, phase_last = 4.4, delta = 3.9 rad
        #   area = 2.0 * (4.4 - 0.5) = 7.8 V*s
        phase = [i * DT for i in range(N)]
        volt = [2.0] * N
        result = self._result(phase, volt)
        m = result["runs"]["signal"]["P(X)"]
        self.assertEqual(m["window"]["sample_count"], 40)
        self.assertEqual(m["window"]["selected_first_time_s"], 0.5)
        self.assertEqual(m["window"]["selected_last_time_s"], 4.4)
        self.assertEqual(m["phase_first_rad"], 0.5)
        self.assertEqual(m["phase_last_rad"], 4.4)
        # 4.4 and 3.9 are not exactly representable in binary; the parsed
        # CSV values are within 1 ulp of the exact decimals. The synthetic
        # V=2 V over seconds makes area_turns ~ 3.8e15, so the area/residual
        # comparisons use a relative 1e-9 tolerance (absolute ULP at that
        # magnitude is ~0.5).
        self.assertAlmostEqual(m["phase_delta_rad"], 3.9, places=12)
        self.assertAlmostEqual(m["area_vs"], 7.8, places=12)
        self.assertAlmostEqual(
            m["area_turns"], 7.8 / PHI0, delta=1e-9 * (7.8 / PHI0)
        )
        self.assertAlmostEqual(
            m["residual_turns"],
            3.9 / TAU - 7.8 / PHI0,
            delta=1e-9 * (7.8 / PHI0),
        )

    def test_phase_and_area_agree_on_consistent_synthetic_run(self) -> None:
        # Positive control: phi(t) ramps at 2 rad/s for t in [1, 3) and is
        # flat elsewhere; V(t) = (Phi0/2pi)*2 exactly on the ramp. Then over
        # the window [0.5, 4.5): delta_phi = 4.0 rad and the trapezoid of V
        # telescopes to 4*Phi0/(2pi) -> residual ~ 0 (float precision).
        v0 = (PHI0 / TAU) * 2.0
        phase: list[float] = []
        volt: list[float] = []
        for i in range(N):
            t = i * DT
            if t < 1.0:
                phase.append(0.0)
                volt.append(0.0)
            elif t < 3.0:
                phase.append(2.0 * (t - 1.0))
                volt.append(v0)
            else:
                phase.append(4.0)
                volt.append(0.0)
        result = self._result(phase, volt)
        m = result["runs"]["signal"]["P(X)"]
        self.assertAlmostEqual(m["phase_delta_rad"], 4.0, places=12)
        self.assertAlmostEqual(m["phase_delta_turns"], 4.0 / TAU, places=12)
        self.assertAlmostEqual(m["area_turns"], 4.0 / TAU, places=12)
        self.assertAlmostEqual(m["residual_turns"], 0.0, places=12)


class OrientationTests(unittest.TestCase):
    """AC6: +/- orientation flips area_turns, not the phase delta."""

    def _run(self, orientation):
        plan = dict(PLAN)
        plan["voltage_area"] = {
            "P(X)": {
                "voltage_column": "V(X)",
                "orientation": orientation,
                "endpoint_window": "cross",
            }
        }
        with tempfile.TemporaryDirectory() as td:
            csv = Path(td) / "sig.csv"
            phase = [2.0] * N  # flat phase
            volt = [3.0] * N  # constant 3.0 V
            _write_csv(csv, phase, volt)
            return sfq_metrics_v2.voltage_area_analyze(str(csv), plan)

    def test_orientation_flips_area_sign(self) -> None:
        plus = self._run(1)["runs"]["signal"]["P(X)"]
        minus = self._run(-1)["runs"]["signal"]["P(X)"]
        self.assertEqual(plus["phase_delta_rad"], minus["phase_delta_rad"])
        self.assertAlmostEqual(plus["area_turns"], -minus["area_turns"], places=15)


class ControlCorrectionTests(unittest.TestCase):
    """AC5: per-run results come first; the 0/300-style difference is a
    separate control_corrected listing."""

    def test_identical_signal_control_zero_corrected_residual(self) -> None:
        phase = [i * DT for i in range(N)]
        volt = [2.0] * N
        with tempfile.TemporaryDirectory() as td:
            sig = Path(td) / "sig.csv"
            ctl = Path(td) / "ctl.csv"
            _write_csv(sig, phase, volt)
            _write_csv(ctl, phase, volt)
            result = sfq_metrics_v2.voltage_area_analyze(
                str(sig), PLAN, control_csv=str(ctl)
            )
        self.assertIn("zero_input_control", result["runs"])
        cc = result["control_corrected"]["P(X)"]
        self.assertEqual(cc["corrected_phase_delta_turns"], 0.0)
        self.assertEqual(cc["corrected_area_turns"], 0.0)
        self.assertEqual(cc["corrected_residual_turns"], 0.0)


class ValidationTests(unittest.TestCase):
    """AC2: invalid input is rejected with actionable errors."""

    def test_missing_voltage_column_rejected(self) -> None:
        plan = dict(PLAN)
        plan["voltage_area"] = {
            "P(X)": {"voltage_column": "V(MISSING)", "orientation": 1, "endpoint_window": "cross"}
        }
        with tempfile.TemporaryDirectory() as td:
            csv = Path(td) / "sig.csv"
            _write_csv(csv, [0.0] * N, [0.0] * N)
            with self.assertRaises(ValueError):
                sfq_metrics_v2.voltage_area_analyze(str(csv), plan)

    def test_missing_phase_column_rejected(self) -> None:
        plan = dict(PLAN)
        plan["voltage_area"] = {
            "P(MISSING)": {"voltage_column": "V(X)", "orientation": 1, "endpoint_window": "cross"}
        }
        with tempfile.TemporaryDirectory() as td:
            csv = Path(td) / "sig.csv"
            _write_csv(csv, [0.0] * N, [0.0] * N)
            with self.assertRaises(ValueError):
                sfq_metrics_v2.voltage_area_analyze(str(csv), plan)

    def test_invalid_orientation_rejected(self) -> None:
        for bad in (0, 2, "x", True):
            plan = dict(PLAN)
            plan["voltage_area"] = {
                "P(X)": {"voltage_column": "V(X)", "orientation": bad, "endpoint_window": "cross"}
            }
            with self.assertRaises(ValueError):
                sfq_metrics_v2.validate_voltage_plan(plan)

    def test_unknown_endpoint_window_rejected(self) -> None:
        plan = dict(PLAN)
        plan["voltage_area"] = {
            "P(X)": {"voltage_column": "V(X)", "orientation": 1, "endpoint_window": "nope"}
        }
        with self.assertRaises(ValueError):
            sfq_metrics_v2.validate_voltage_plan(plan)

    def test_window_fewer_than_two_samples_rejected(self) -> None:
        plan = dict(PLAN)
        plan["windows_s"] = {
            "pre": [0.0, 1.0],
            "activity": [1.0, 3.0],
            "post": [4.0, 5.0],
            "cross": [99.0, 100.0],  # beyond the data -> 0 samples
        }
        with tempfile.TemporaryDirectory() as td:
            csv = Path(td) / "sig.csv"
            _write_csv(csv, [0.0] * N, [0.0] * N)
            with self.assertRaises(ValueError):
                sfq_metrics_v2.voltage_area_analyze(str(csv), plan)

    def test_nonfinite_voltage_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            csv = Path(td) / "bad.csv"
            csv.write_text(
                'time,"P(X)","V(X)"\n0.0,0.0,0.0\n0.1,1.0,nan\n0.2,2.0,0.0\n',
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                sfq_metrics_v2.voltage_area_analyze(str(csv), PLAN)

    def test_nonmonotonic_time_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            csv = Path(td) / "bad.csv"
            csv.write_text(
                'time,"P(X)","V(X)"\n0.0,0.0,0.0\n0.1,1.0,1.0\n0.1,2.0,1.0\n',
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                sfq_metrics_v2.voltage_area_analyze(str(csv), PLAN)

    def test_misaligned_control_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            sig = Path(td) / "sig.csv"
            ctl = Path(td) / "ctl.csv"
            _write_csv(sig, [0.0] * N, [0.0] * N)
            _write_csv(ctl, [0.0] * (N - 1), [0.0] * (N - 1))
            with self.assertRaises(ValueError):
                sfq_metrics_v2.voltage_area_analyze(str(sig), PLAN, control_csv=str(ctl))


class TerminologyTests(unittest.TestCase):
    """AC6/claim ceiling: cross-check output never uses event semantics."""

    FORBIDDEN = {"fast_events", "pulse_count", "sfq_count", "event_count"}

    def test_no_event_semantics_keys_anywhere(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            csv = Path(td) / "sig.csv"
            _write_csv(csv, [0.0] * N, [0.0] * N)
            result = sfq_metrics_v2.voltage_area_analyze(str(csv), PLAN)

        def collect(obj: object) -> set[str]:
            keys: set[str] = set()
            if isinstance(obj, dict):
                keys.update(obj.keys())
                for value in obj.values():
                    keys |= collect(value)
            return keys

        self.assertEqual(collect(result) & self.FORBIDDEN, set())


class CliTests(unittest.TestCase):
    """AC2: CLI cross-check mode succeeds and fails actionably."""

    def test_voltage_area_cli_success(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            csv = Path(td) / "sig.csv"
            plan = Path(td) / "plan.json"
            _write_csv(csv, [0.0] * N, [0.0] * N)
            plan.write_text(json.dumps(PLAN), encoding="utf-8")
            proc = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS_DIR / "sfq_metrics_v2.py"),
                    str(csv),
                    "--measurement-plan",
                    str(plan),
                    "--voltage-area",
                ],
                capture_output=True,
                text=True,
            )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("voltage_area_crosscheck", proc.stdout)
        self.assertIn("residual_turns", proc.stdout)

    def test_voltage_area_cli_bad_plan_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            csv = Path(td) / "sig.csv"
            plan = Path(td) / "plan.json"
            _write_csv(csv, [0.0] * N, [0.0] * N)
            plan.write_text(json.dumps({"schema_version": 1}), encoding="utf-8")
            proc = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS_DIR / "sfq_metrics_v2.py"),
                    str(csv),
                    "--measurement-plan",
                    str(plan),
                    "--voltage-area",
                ],
                capture_output=True,
                text=True,
            )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("error:", proc.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
