#!/usr/bin/env python3
"""M5 (M5-LITE-PILOT-001) windowed-metric tests for sfq_metrics_v2.

AC5 synthetic tests plus the AC6 frozen-CSV replay. All expectations are
first-principles constants (never calls to the production helpers): window
sample counts come from the fixed time grid, corrected deltas from the
constructed ramp heights, and the AC6 replay constants from the TASK's
frozen values. stdlib only: no JoSIM, no network, no installed dependencies.
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

# Fixed synthetic time grid: t = i * 0.1 s, 130 samples (0.0 .. 12.9).
N_SAMPLES = 130
DT = 0.1
# Plan windows on that grid (half-open [start, end)):
#   pre      [0.0, 2.0)  -> i = 0..19   (20 samples)
#   activity [2.0, 8.0)  -> i = 20..79  (60 samples)
#   post     [10.0, 12.0) -> i = 100..119 (20 samples)
PRE_LO, PRE_HI = 0.0, 2.0
ACT_LO, ACT_HI = 2.0, 8.0
POST_LO, POST_HI = 10.0, 12.0

PLAN = {
    "schema_version": 1,
    "windows_s": {
        "pre": [PRE_LO, PRE_HI],
        "activity": [ACT_LO, ACT_HI],
        "post": [POST_LO, POST_HI],
    },
    "phase_directions": {"P(X)": 1},
    "activity_threshold_rad": 0.3,
}


def _times(n: int = N_SAMPLES) -> list[float]:
    return [i * DT for i in range(n)]


def _write_csv(path: Path, phase: list[float]) -> None:
    with path.open("w", encoding="utf-8") as f:
        f.write('time,"P(X)"\n')
        for t, p in zip(_times(len(phase)), phase):
            f.write(f"{t:e},{p!r}\n")


class PlanValidationTests(unittest.TestCase):
    """AC2: plan and CSV validation rejects invalid input."""

    def test_bad_schema_version(self) -> None:
        plan = dict(PLAN, schema_version=2)
        with self.assertRaises(ValueError):
            sfq_metrics_v2.validate_plan(plan)

    def test_overlapping_windows_rejected(self) -> None:
        plan = {
            "schema_version": 1,
            "windows_s": {"pre": [0.0, 3.0], "activity": [2.0, 8.0], "post": [10.0, 12.0]},
            "phase_directions": {"P(X)": 1},
            "activity_threshold_rad": 0.3,
        }
        with self.assertRaises(ValueError):
            sfq_metrics_v2.validate_plan(plan)

    def test_invalid_direction_rejected(self) -> None:
        for bad in (0, 2, "x", True, None):
            plan = dict(PLAN)
            plan["phase_directions"] = {"P(X)": bad}
            with self.assertRaises(ValueError):
                sfq_metrics_v2.validate_plan(plan)

    def test_missing_threshold_rejected(self) -> None:
        plan = {k: v for k, v in PLAN.items() if k != "activity_threshold_rad"}
        with self.assertRaises(ValueError):
            sfq_metrics_v2.validate_plan(plan)

    def test_nonmonotonic_time_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            csv = Path(td) / "bad.csv"
            csv.write_text('time,"P(X)"\n0.0,0.0\n0.1,1.0\n0.1,2.0\n', encoding="utf-8")
            with self.assertRaises(ValueError):
                sfq_metrics_v2.windowed_analyze(str(csv), PLAN)

    def test_nonfinite_phase_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            csv = Path(td) / "bad.csv"
            csv.write_text('time,"P(X)"\n0.0,0.0\n0.1,nan\n0.2,2.0\n', encoding="utf-8")
            with self.assertRaises(ValueError):
                sfq_metrics_v2.windowed_analyze(str(csv), PLAN)

    def test_missing_phase_column_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            csv = Path(td) / "bad.csv"
            csv.write_text('time,"P(X)"\n0.0,0.0\n', encoding="utf-8")
            plan = dict(PLAN)
            plan["phase_directions"] = {"P(NOPE)": 1}
            with self.assertRaises(ValueError):
                sfq_metrics_v2.windowed_analyze(str(csv), plan)

    def test_undersampled_window_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            csv = Path(td) / "short.csv"
            _write_csv(csv, [0.0] * N_SAMPLES)
            plan = {
                "schema_version": 1,
                "windows_s": {
                    "pre": [PRE_LO, PRE_HI],
                    "activity": [ACT_LO, ACT_HI],
                    "post": [100.0, 102.0],  # beyond the data -> 0 samples
                },
                "phase_directions": {"P(X)": 1},
                "activity_threshold_rad": 0.3,
            }
            with self.assertRaises(ValueError):
                sfq_metrics_v2.windowed_analyze(str(csv), plan)


class ControlAlignmentTests(unittest.TestCase):
    """AC2/AC5: malformed or misaligned controls fail."""

    def test_control_missing_phase_column_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            sig = Path(td) / "sig.csv"
            ctl = Path(td) / "ctl.csv"
            _write_csv(sig, [0.0] * N_SAMPLES)
            ctl.write_text('time,"P(Y)"\n' + "".join(f"{i*DT:e},0.0\n" for i in range(N_SAMPLES)), encoding="utf-8")
            with self.assertRaises(ValueError):
                sfq_metrics_v2.windowed_analyze(str(sig), PLAN, control_csv=str(ctl))

    def test_control_time_array_mismatch_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            sig = Path(td) / "sig.csv"
            ctl = Path(td) / "ctl.csv"
            _write_csv(sig, [0.0] * N_SAMPLES)
            _write_csv(ctl, [0.0] * (N_SAMPLES - 1))  # shorter time array
            with self.assertRaises(ValueError):
                sfq_metrics_v2.windowed_analyze(str(sig), PLAN, control_csv=str(ctl))

    def test_control_shifted_time_array_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            sig = Path(td) / "sig.csv"
            ctl = Path(td) / "ctl.csv"
            _write_csv(sig, [0.0] * N_SAMPLES)
            ctl.write_text('time,"P(X)"\n' + "".join(f"{(i*DT+0.05):e},0.0\n" for i in range(N_SAMPLES)), encoding="utf-8")
            with self.assertRaises(ValueError):
                sfq_metrics_v2.windowed_analyze(str(sig), PLAN, control_csv=str(ctl))


class ClusteringTests(unittest.TestCase):
    """AC4/AC5: contiguous activity clustering inside the activity window."""

    def _analyze(self, phase: list[float], plan=PLAN, control=None):
        with tempfile.TemporaryDirectory() as td:
            sig = Path(td) / "sig.csv"
            _write_csv(sig, phase)
            ctl_csv = None
            if control is not None:
                ctl = Path(td) / "ctl.csv"
                _write_csv(ctl, control)
                ctl_csv = str(ctl)
            return sfq_metrics_v2.windowed_analyze(str(sig), plan, control_csv=ctl_csv)

    def test_ten_contiguous_active_increments_one_cluster(self) -> None:
        # Ramp: 0.5 rad per increment for i=20..29 (10 increments, all > 0.3),
        # then flat at 5.0. Pre mean 0.0, post mean 5.0 -> delta 5.0 (exact).
        phase = [0.0] * N_SAMPLES
        for i in range(20, 30):
            phase[i + 1] = phase[i] + 0.5
        for i in range(30, N_SAMPLES):
            phase[i] = 5.0
        result = self._analyze(phase)
        act = result["signal"]["P(X)"]["activity"]
        self.assertEqual(act["over_threshold_sample_count"], 10)
        self.assertEqual(len(act["activity_clusters"]), 1)
        cluster = act["activity_clusters"][0]
        self.assertEqual(cluster["n_increments"], 10)
        self.assertEqual(cluster["start_index"], 20)
        self.assertEqual(cluster["end_index"], 30)
        self.assertAlmostEqual(
            result["control_corrected"]["P(X)"]["corrected_delta_rad"], 5.0, places=12
        )

    def test_two_separated_ramps_two_clusters(self) -> None:
        # Ramp i=20..24 (5 increments), flat, ramp i=40..44 (5 increments),
        # flat at 5.0. Two clusters, 10 over-threshold increments total.
        phase = [0.0] * N_SAMPLES
        for i in range(20, 25):
            phase[i + 1] = phase[i] + 0.5
        for i in range(25, 40):
            phase[i + 1] = phase[i]
        for i in range(40, 45):
            phase[i + 1] = phase[i] + 0.5
        for i in range(45, N_SAMPLES):
            phase[i] = 5.0
        result = self._analyze(phase)
        act = result["signal"]["P(X)"]["activity"]
        self.assertEqual(act["over_threshold_sample_count"], 10)
        self.assertEqual(len(act["activity_clusters"]), 2)
        self.assertEqual(act["activity_clusters"][0]["start_index"], 20)
        self.assertEqual(act["activity_clusters"][1]["start_index"], 40)

    def test_equality_at_threshold_inactive(self) -> None:
        # Increments exactly 0.25 rad (exactly representable in binary, so the
        # increments are exact) with threshold 0.25: strict > threshold means
        # equality is inactive -> no activity. 10 increments x 0.25 -> delta
        # 2.5 rad (exact).
        plan = dict(PLAN)
        plan["activity_threshold_rad"] = 0.25
        # 0.25 = 2^-2: every 0.25*k is exactly representable, so the ten
        # activity-window increments are EXACTLY 0.25 rad. Pre flat at 0.0,
        # post flat at 2.5 -> delta 2.5 rad (exact).
        phase = [0.0] * 20 + [0.25 * k for k in range(0, 11)] + [2.5] * (N_SAMPLES - 31)
        result = self._analyze(phase, plan=plan)
        act = result["signal"]["P(X)"]["activity"]
        self.assertEqual(act["over_threshold_sample_count"], 0)
        self.assertEqual(act["activity_clusters"], [])
        self.assertAlmostEqual(
            result["control_corrected"]["P(X)"]["corrected_delta_rad"], 2.5, places=12
        )

    def test_activity_outside_window_ignored(self) -> None:
        # Big jumps in pre and post windows must not count as activity.
        phase = [0.0] * N_SAMPLES
        for i in range(0, 6):
            phase[i + 1] = phase[i] + 1.0
        for i in range(6, 20):
            phase[i] = 6.0
        for i in range(100, 106):
            phase[i + 1] = phase[i] + 1.0
        result = self._analyze(phase)
        act = result["signal"]["P(X)"]["activity"]
        self.assertEqual(act["over_threshold_sample_count"], 0)
        self.assertEqual(act["activity_clusters"], [])


class ControlCorrectionTests(unittest.TestCase):
    """AC3/AC5: zero-input control correction semantics."""

    def _analyze_pair(self, signal, control, direction=1):
        with tempfile.TemporaryDirectory() as td:
            sig = Path(td) / "sig.csv"
            ctl = Path(td) / "ctl.csv"
            _write_csv(sig, signal)
            _write_csv(ctl, control)
            plan = dict(PLAN)
            plan["phase_directions"] = {"P(X)": direction}
            return sfq_metrics_v2.windowed_analyze(str(sig), plan, control_csv=str(ctl))

    def test_common_startup_background_cancellation(self) -> None:
        # Both signal and control ramp +2.0 rad across the pre window
        # (i=0..19, 0.1 rad/increment). Signal additionally ramps 0.5 rad x 10
        # in the activity window to +7.0; control stays flat at +2.0.
        # corrected = direction * ((7-1) - (2-1)) = 5.0 (exact).
        def _with_startup(post_flat: float) -> list[float]:
            phase = [0.0] * N_SAMPLES
            for i in range(0, 20):
                phase[i + 1] = phase[i] + 0.1
            for i in range(20, 30):
                phase[i + 1] = phase[i] + (0.5 if post_flat > 2.0 else 0.0)
            for i in range(30, N_SAMPLES):
                phase[i] = post_flat
            return phase

        signal = _with_startup(7.0)
        control = _with_startup(2.0)
        result = self._analyze_pair(signal, control)
        self.assertEqual(result["control_applied"], True)
        corrected = result["control_corrected"]["P(X)"]
        self.assertAlmostEqual(corrected["corrected_delta_rad"], 5.0, places=12)
        self.assertAlmostEqual(
            corrected["corrected_delta_turns"], 5.0 / TAU, places=12
        )

    def test_identical_signal_control_zero_corrected_delta(self) -> None:
        phase = [0.0] * N_SAMPLES
        for i in range(20, 30):
            phase[i + 1] = phase[i] + 0.5
        for i in range(30, N_SAMPLES):
            phase[i] = 5.0
        result = self._analyze_pair(phase, phase)
        self.assertEqual(result["control_corrected"]["P(X)"]["corrected_delta_rad"], 0.0)
        self.assertEqual(result["control_corrected"]["P(X)"]["corrected_delta_turns"], 0.0)

    def test_direction_reversal_flips_deltas_not_activity(self) -> None:
        # Same signal, zero control, direction +1 vs -1: corrected delta is
        # +5.0 vs -5.0 (exact); activity is direction-independent.
        phase = [0.0] * N_SAMPLES
        for i in range(20, 30):
            phase[i + 1] = phase[i] + 0.5
        for i in range(30, N_SAMPLES):
            phase[i] = 5.0
        zero = [0.0] * N_SAMPLES
        plus = self._analyze_pair(phase, zero, direction=1)
        minus = self._analyze_pair(phase, zero, direction=-1)
        self.assertAlmostEqual(
            plus["control_corrected"]["P(X)"]["corrected_delta_rad"], 5.0, places=12
        )
        self.assertAlmostEqual(
            minus["control_corrected"]["P(X)"]["corrected_delta_rad"], -5.0, places=12
        )
        self.assertEqual(
            plus["signal"]["P(X)"]["activity"],
            minus["signal"]["P(X)"]["activity"],
        )

    def test_constant_offsets_do_not_alter_deltas(self) -> None:
        # Adding a constant offset shifts both window means equally.
        base = [0.0] * N_SAMPLES
        for i in range(20, 30):
            base[i + 1] = base[i] + 0.5
        for i in range(30, N_SAMPLES):
            base[i] = 5.0
        offset = [v + 5.0 for v in base]
        with tempfile.TemporaryDirectory() as td:
            sig_base = Path(td) / "base.csv"
            sig_off = Path(td) / "off.csv"
            _write_csv(sig_base, base)
            _write_csv(sig_off, offset)
            r_base = sfq_metrics_v2.windowed_analyze(str(sig_base), PLAN)
            r_off = sfq_metrics_v2.windowed_analyze(str(sig_off), PLAN)
        self.assertEqual(
            r_base["control_corrected"]["P(X)"]["corrected_delta_rad"],
            r_off["control_corrected"]["P(X)"]["corrected_delta_rad"],
        )
        self.assertAlmostEqual(
            r_base["control_corrected"]["P(X)"]["corrected_delta_rad"], 5.0, places=12
        )


class WindowSelectionTests(unittest.TestCase):
    """Half-open window selection on the fixed 0.1 s grid."""

    def test_half_open_window_sample_counts(self) -> None:
        phase = [0.0] * N_SAMPLES
        with tempfile.TemporaryDirectory() as td:
            sig = Path(td) / "sig.csv"
            _write_csv(sig, phase)
            result = sfq_metrics_v2.windowed_analyze(str(sig), PLAN)
        col = result["signal"]["P(X)"]
        self.assertEqual(col["pre"]["sample_count"], 20)   # i=0..19, t=1.9 last
        self.assertEqual(col["post"]["sample_count"], 20)  # i=100..119, t=11.9 last
        self.assertEqual(col["pre"]["selected_first_time_s"], 0.0)
        self.assertEqual(col["pre"]["selected_last_time_s"], 1.9)
        self.assertEqual(col["post"]["selected_last_time_s"], 11.9)
        # Boundaries are half-open: t=2.0 belongs to activity, t=8.0 to neither.
        self.assertEqual(col["activity"]["over_threshold_sample_count"], 0)


class FrozenReplayTests(unittest.TestCase):
    """AC6: arithmetic replay of the frozen DCSFQ bump CSVs with the 0 uA
    control, using the fixed plan (directions fixed by the TASK constants:
    B1=-1, B2=+1, B3=+1). Constants are independent, from TASK AC6."""

    FROZEN_CSV_HASHES = {
        "bump_0.csv": "2420b99ae10135de14db2a4dd0ea63649e225ff6a467dabe6b7514c1096bd9c3",
        "bump_300u.csv": "dfe20406ee1bc54be483b3bc5935cac87ab545af06c47082720523569b90549d",
    }
    EXPECTED_TURNS = {
        "P(B1|XDCSFQ)": 0.999999982941839,
        "P(B2|XDCSFQ)": 1.00000006251931,
        "P(B3|XDCSFQ)": 1.00000001477283,
    }
    EXPECTED_PRINTED_RAD = {
        "P(B1|XDCSFQ)": 6.2831852,
        "P(B2|XDCSFQ)": 6.2831857,
        "P(B3|XDCSFQ)": 6.2831854,
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

    def _paths(self) -> tuple[Path, Path]:
        data = REPO_ROOT / "test" / "final" / "interface" / "data"
        return data / "test_dcsfq_behavior_bump_300u.csv", data / "test_dcsfq_behavior_bump_0.csv"

    def test_frozen_input_hashes(self) -> None:
        sig, ctl = self._paths()
        self.assertEqual(sfq_metrics_v2.file_sha256(str(sig)), self.FROZEN_CSV_HASHES["bump_300u.csv"])
        self.assertEqual(sfq_metrics_v2.file_sha256(str(ctl)), self.FROZEN_CSV_HASHES["bump_0.csv"])

    def test_frozen_replay_values(self) -> None:
        sig, ctl = self._paths()
        result = sfq_metrics_v2.windowed_analyze(
            str(sig), self.FIXED_PLAN, control_csv=str(ctl)
        )
        self.assertEqual(result["control_applied"], True)
        self.assertEqual(result["threshold_status"], "descriptive_unfrozen")
        for col in self.EXPECTED_TURNS:
            s = result["signal"][col]
            self.assertEqual(s["pre"]["sample_count"], 30)
            self.assertEqual(s["post"]["sample_count"], 900)
            corrected = result["control_corrected"][col]
            turns = corrected["corrected_delta_turns"]
            # TASK AC6: within 1e-9 rad computational precision.
            self.assertLess(abs((turns - self.EXPECTED_TURNS[col]) * TAU), 1e-9)
            self.assertLess(
                abs(turns * TAU - self.EXPECTED_PRINTED_RAD[col]), 1e-7
            )
            self.assertEqual(
                len(s["activity"]["activity_clusters"]),
                self.EXPECTED_CLUSTERS[col],
            )
            ctl_act = result["zero_input_control"][col]["activity"]
            self.assertEqual(ctl_act["activity_clusters"], [])


class TerminologyTests(unittest.TestCase):
    """AC4: windowed output never uses event semantics anywhere."""

    FORBIDDEN = {"fast_events", "pulse_count", "sfq_count", "event_count"}

    def test_no_event_semantics_keys_anywhere(self) -> None:
        phase = [0.0] * N_SAMPLES
        for i in range(20, 30):
            phase[i + 1] = phase[i] + 0.5
        with tempfile.TemporaryDirectory() as td:
            sig = Path(td) / "sig.csv"
            _write_csv(sig, phase)
            result = sfq_metrics_v2.windowed_analyze(str(sig), PLAN)

        def collect(obj: object) -> set[str]:
            keys: set[str] = set()
            if isinstance(obj, dict):
                keys.update(obj.keys())
                for value in obj.values():
                    keys |= collect(value)
            return keys

        self.assertEqual(collect(result) & self.FORBIDDEN, set())


class CliTests(unittest.TestCase):
    """AC2: CLI failures are nonzero and actionable; plan mode works."""

    def test_plan_mode_cli_success(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            sig = Path(td) / "sig.csv"
            plan = Path(td) / "plan.json"
            _write_csv(sig, [0.0] * N_SAMPLES)
            plan.write_text(json.dumps(PLAN), encoding="utf-8")
            proc = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS_DIR / "sfq_metrics_v2.py"),
                    str(sig),
                    "--measurement-plan",
                    str(plan),
                ],
                capture_output=True,
                text=True,
            )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("control_corrected", proc.stdout)
        self.assertIn("descriptive_unfrozen", proc.stdout)

    def test_invalid_plan_cli_failure(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            sig = Path(td) / "sig.csv"
            plan = Path(td) / "plan.json"
            _write_csv(sig, [0.0] * N_SAMPLES)
            plan.write_text(json.dumps({"schema_version": 1}), encoding="utf-8")
            proc = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS_DIR / "sfq_metrics_v2.py"),
                    str(sig),
                    "--measurement-plan",
                    str(plan),
                ],
                capture_output=True,
                text=True,
            )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("error:", proc.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
