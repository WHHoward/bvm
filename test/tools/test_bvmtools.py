#!/usr/bin/env python3
"""Focused regressions for the reusable JoSIM/BVM analysis core."""

from __future__ import annotations

import csv
import hashlib
import math
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))

from bvmtools.compare import (  # noqa: E402
    TimeGridMismatch,
    compare_series,
    compare_windowed_series,
)
from bvmtools.kcl import kcl_window_metrics, linear_kcl_residual  # noqa: E402
from bvmtools.onset import (  # noqa: E402
    first_persistent_exceedance,
    pre_noise_referenced_threshold,
    tie_groups,
)
from bvmtools.phase import (  # noqa: E402
    TAU,
    continuous_unwrap,
    monotonic_segments,
    phase_delta_turns,
    phase_window_metrics,
    window_indices,
)
from bvmtools.provenance import file_snapshot  # noqa: E402
from bvmtools.raw import DuplicateColumnError, RawTraceError, read_csv  # noqa: E402
from bvmtools.sfq import (  # noqa: E402
    PHI0,
    StrictLocalEventSpec,
    strict_event_summary,
    strict_segment_metrics,
)
from bvmtools.waveform import waveform_metrics, waveform_window_metrics  # noqa: E402


def _independent_anchor(path: Path) -> tuple[float, float, float]:
    """Independent raw CSV arithmetic used as an oracle-side cross-check."""

    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    time_s = np.asarray([float(row["time"]) for row in rows], dtype=float)
    phase = np.asarray([float(row["P(BJL2|XBQ)"]) for row in rows], dtype=float)
    voltage = np.asarray([float(row["V(BJL2|XBQ)"]) for row in rows], dtype=float)
    unwrapped = np.unwrap(phase)
    selected = np.flatnonzero((time_s >= 94e-12) & (time_s < 130e-12))
    local = unwrapped[selected]
    signs = np.sign(np.diff(local))
    nonzero = np.flatnonzero(signs)
    start = 0
    current = signs[nonzero[0]]
    segments: list[tuple[int, int]] = []
    for position in nonzero[1:]:
        if signs[position] != current:
            segments.append((start, int(position)))
            start = int(position)
            current = signs[position]
    segments.append((start, len(local) - 1))
    left, right = max(segments, key=lambda item: abs(unwrapped[selected[item[1]]] - unwrapped[selected[item[0]]]))
    indices = selected[left : right + 1]
    delta_turns = float((unwrapped[indices[-1]] - unwrapped[indices[0]]) / (2.0 * math.pi))
    area_turns = float(np.trapezoid(voltage[indices], time_s[indices]) / PHI0)
    return delta_turns, area_turns, float(time_s[indices[-1]] * 1e12)


class RawReaderTests(unittest.TestCase):
    def _write(self, content: str) -> Path:
        handle = tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8")
        self.addCleanup(lambda: Path(handle.name).unlink(missing_ok=True))
        handle.write(content)
        handle.close()
        return Path(handle.name)

    def test_quoted_headers_and_duplicate_occurrences_are_preserved(self) -> None:
        path = self._write(
            '"time","P(X)","P(X)","V(X)"\n'
            '0,"1","2","0"\n'
            '1,"3","4","1"\n'
        )
        trace = read_csv(path)
        self.assertEqual(trace.headers, ("time", "P(X)", "P(X)", "V(X)"))
        self.assertEqual(trace.sample_count, 2)
        self.assertEqual(trace.duplicate_columns, {"P(X)": 2})
        with self.assertRaises(DuplicateColumnError):
            trace.column("P(X)")
        self.assertEqual(trace.column("P(X)", occurrence=0), (1.0, 3.0))
        self.assertEqual(trace.column("P(X)", occurrence=1), (2.0, 4.0))
        self.assertEqual(trace.column("P(X)", all_matches=True), ((1.0, 3.0), (2.0, 4.0)))

    def test_nonuniform_grid_is_valid_and_visible(self) -> None:
        path = self._write("time,V(X)\n0,1\n1,2\n3,4\n")
        trace = read_csv(path)
        qa = trace.qa()
        self.assertEqual(qa["status"], "VALID")
        self.assertTrue(qa["nonuniform_time_grid"])
        self.assertEqual(qa["dt_min"], 1.0)
        self.assertEqual(qa["dt_max"], 2.0)

    def test_time_and_nonfinite_values_are_rejected(self) -> None:
        for content in (
            "time,V(X)\n0,1\n0,2\n",
            "time,V(X)\n0,1\n1,nan\n",
            "time,V(X)\n0,1\n1,inf\n",
        ):
            with self.subTest(content=content):
                path = self._write(content)
                with self.assertRaises(RawTraceError):
                    read_csv(path)


class PhaseAndStrictEventTests(unittest.TestCase):
    def test_fixed_window_is_half_open(self) -> None:
        self.assertEqual(
            window_indices((0.0, 1.0e-12, 2.0e-12), 1.0e-12, 2.0e-12),
            (1,),
        )

    def test_fixed_window_phase_metrics_unwraps_before_turn_conversion(self) -> None:
        result = phase_window_metrics(
            (0.0, 1.0e-12, 2.0e-12),
            (0.0, math.pi, TAU),
            (0.0, 3.0e-12),
        )
        self.assertEqual(result["raw_unit"], "rad")
        self.assertEqual(result["display_unit"], "turns")
        self.assertAlmostEqual(result["mean_turns"], 0.5, places=12)
        self.assertAlmostEqual(result["rms_turns"], math.sqrt(5.0 / 12.0), places=12)
        self.assertAlmostEqual(result["endpoint_delta_turns"], 1.0, places=12)

    def test_unwrap_and_turn_conversion(self) -> None:
        raw = (0.0, 6.0, 0.5)
        unwrapped = continuous_unwrap(raw)
        self.assertAlmostEqual(unwrapped[-1], 0.5, places=12)
        self.assertAlmostEqual(phase_delta_turns((0.0, math.pi, TAU)), 1.0, places=12)
        self.assertAlmostEqual(phase_delta_turns((TAU, math.pi, 0.0)), -1.0, places=12)

    def test_monotonic_segmentation_is_deterministic_and_overlaps_turn(self) -> None:
        segments = monotonic_segments((0.0, 1.0, 2.0, 1.0, 0.0))
        self.assertEqual(
            [(item.start_index, item.end_index, item.direction) for item in segments],
            [(0, 2, 1), (2, 4, -1)],
        )

    def test_same_segment_area_uses_actual_time_grid(self) -> None:
        times = (0.0, 1.0e-12, 3.0e-12)
        phase = (0.0, 1.0, 3.0)
        voltage = tuple(PHI0 / TAU * 1.0e12 for _ in times)
        records = strict_segment_metrics(times, phase, voltage, (0.0, 4.0e-12))
        self.assertEqual(len(records), 1)
        self.assertAlmostEqual(records[0]["delta_turns"], 3.0 / TAU, places=12)
        self.assertAlmostEqual(records[0]["area_turns"], 3.0 / TAU, places=12)
        self.assertAlmostEqual(records[0]["phase_area_residual_turns"], 0.0, places=12)
        self.assertIsNone(records[0]["area_consistent"])

    def test_missing_strict_spec_is_inconclusive(self) -> None:
        result = strict_event_summary(
            (0.0, 1.0, 2.0),
            (0.0, 1.0, 2.0),
            (0.0, PHI0 / TAU, 0.0),
            activity_window_s=(0.0, 3.0),
            post_window_s=(0.0, 3.0),
            post_tail_window_s=(0.0, 3.0),
        )
        self.assertEqual(result["compatibility_classification"], "INCONCLUSIVE")
        self.assertIsNone(result["complete_segment_count"])

    def test_frozen_anchor_a_and_b(self) -> None:
        raw_root = REPO / "test/exploration/bvm-load-qb-matrix-v1-20260901/raw/replay"
        expected = {
            9: (0.8925272335342432, 0.8925370087565057, 109.65, "SUBTHRESHOLD"),
            13: (1.0160289228944646, 1.0160368344325381, 110.175, "CLEAN_ONE_SFQ_CANDIDATE"),
        }
        for width, (turns, area, end_ps, classification) in expected.items():
            with self.subTest(width=width):
                path = raw_root / f"{width}ps/12x320/logical1_read/run-01.csv"
                independent = _independent_anchor(path)
                self.assertAlmostEqual(independent[0], turns, places=12)
                self.assertAlmostEqual(independent[1], area, places=12)
                self.assertAlmostEqual(independent[2], end_ps, places=12)
                trace = read_csv(path)
                spec = StrictLocalEventSpec.from_mapping({
                    "id": "bvm-qb-strict-event-anchor-compatibility-v1",
                    "scope": "task-local",
                    "status": "FROZEN",
                    "mapping_status": "UNVERIFIED_BQ_BVM_PV_MAPPING",
                    "phase_column": "P(BJL2|XBQ)",
                    "voltage_column": "V(BJL2|XBQ)",
                    "branch_endpoints": "BJL2 branch orientation declared by the frozen replay fixture",
                    "voltage_to_phase_sign": 1,
                    "reporting_direction": 1,
                    "run_id": f"bvm-load-qb-matrix-v1-20260901/replay/{width}ps/12x320/logical1_read",
                    "window_id": "activity-94-130ps-post-140-170ps-tail-165-170ps",
                    "raw_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    "metric_spec": {
                        "path": "docs/research/METRIC_SPEC_V2.md",
                        "version": "2.0.0",
                        "sha256": "f88a36f4d310b2572efdc7408d734640f25dd5aea2246b74fbb8b7bb7f0be470",
                    },
                    "tolerance": {
                        "id": "bvm-qb-strict-event-anchor-task-local-v1",
                        "scope": "task-local",
                        "status": "FROZEN",
                        "evidence": "test/exploration/bvm-load-qb-strict-event-reclassification-v1-20260901/analysis/REPORT.md",
                        "phase_area_residual_abs_floor_turns": 0.05,
                        "phase_area_residual_relative": 0.10,
                        "complete_min_turns": 1.0,
                        "clean_upper_turns": 1.15,
                        "post_range_max_turns": 1.0,
                        "post_tail_p2p_max_turns": 0.25,
                    },
                    "compatibility_profile": "STRICT_EVENT_ANCHOR_COMPATIBILITY_V1",
                })
                result = strict_event_summary(
                    trace.time,
                    trace.column("P(BJL2|XBQ)"),
                    trace.column("V(BJL2|XBQ)"),
                    activity_window_s=(94.0e-12, 130.0e-12),
                    post_window_s=(140.0e-12, 170.0e-12),
                    post_tail_window_s=(165.0e-12, 170.0e-12),
                    spec=spec,
                    actual_raw_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                    actual_metric_spec_sha256="f88a36f4d310b2572efdc7408d734640f25dd5aea2246b74fbb8b7bb7f0be470",
                )
                largest = result["largest_monotonic_segment"]
                self.assertAlmostEqual(largest["delta_turns"], turns, places=12)
                self.assertAlmostEqual(largest["area_turns"], area, places=12)
                self.assertAlmostEqual(largest["start_time_ps"], 103.0375, places=12)
                self.assertAlmostEqual(largest["end_time_ps"], end_ps, places=12)
                self.assertEqual(result["compatibility_classification"], classification)
                self.assertEqual(result["raw_sha256_match"], True)
                self.assertEqual(result["metric_spec_sha256_match"], True)
                self.assertEqual(result["complete_segment_count"], 1 if width == 13 else 0)
                self.assertEqual(result["second_complete_segment_present"], False)
                self.assertEqual(result["post_boundedness"]["status"], "VALID")

    def test_13ps_anchor_activity_window_is_not_truncated_at_110ps(self) -> None:
        path = REPO / "test/exploration/bvm-load-qb-matrix-v1-20260901/raw/replay/13ps/12x320/logical1_read/run-01.csv"
        trace = read_csv(path)
        raw_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        spec = StrictLocalEventSpec.from_mapping({
            "id": "bvm-qb-strict-event-anchor-compatibility-v1",
            "scope": "task-local",
            "status": "FROZEN",
            "mapping_status": "UNVERIFIED_BQ_BVM_PV_MAPPING",
            "phase_column": "P(BJL2|XBQ)",
            "voltage_column": "V(BJL2|XBQ)",
            "branch_endpoints": "BJL2 branch orientation declared by the frozen replay fixture",
            "voltage_to_phase_sign": 1,
            "reporting_direction": 1,
            "run_id": "bvm-qb-lsl-removal-quick-v1-20260901/strict-anchor",
            "window_id": "activity-95-115ps-post-115-130ps-tail-125-130ps",
            "raw_sha256": raw_hash,
            "metric_spec": {
                "path": "docs/research/METRIC_SPEC_V2.md",
                "version": "2.0.0",
                "sha256": "f88a36f4d310b2572efdc7408d734640f25dd5aea2246b74fbb8b7bb7f0be470",
            },
            "tolerance": {
                "id": "bvm-qb-strict-event-anchor-task-local-v1",
                "scope": "task-local",
                "status": "FROZEN",
                "evidence": "test/exploration/bvm-load-qb-strict-event-reclassification-v1-20260901/analysis/REPORT.md",
                "phase_area_residual_abs_floor_turns": 0.05,
                "phase_area_residual_relative": 0.10,
                "complete_min_turns": 1.0,
                "clean_upper_turns": 1.15,
                "post_range_max_turns": 1.0,
                "post_tail_p2p_max_turns": 0.25,
            },
            "compatibility_profile": "STRICT_EVENT_ANCHOR_COMPATIBILITY_V1",
        })
        result = strict_event_summary(
            trace.time,
            trace.column("P(BJL2|XBQ)"),
            trace.column("V(BJL2|XBQ)"),
            activity_window_s=(95.0e-12, 115.0e-12),
            post_window_s=(115.0e-12, 130.0e-12),
            post_tail_window_s=(125.0e-12, 130.0e-12),
            spec=spec,
            actual_raw_sha256=raw_hash,
            actual_metric_spec_sha256="f88a36f4d310b2572efdc7408d734640f25dd5aea2246b74fbb8b7bb7f0be470",
        )
        largest = result["largest_monotonic_segment"]
        self.assertAlmostEqual(largest["delta_turns"], 1.0160289228944646, places=12)
        self.assertAlmostEqual(largest["area_turns"], 1.0160368344325381, places=12)
        self.assertAlmostEqual(largest["start_time_ps"], 103.0375, places=12)
        self.assertAlmostEqual(largest["end_time_ps"], 110.175, places=12)
        self.assertEqual(result["compatibility_classification"], "CLEAN_ONE_SFQ_CANDIDATE")
        self.assertEqual(result["complete_segment_count"], 1)


class WaveformAndCompareTests(unittest.TestCase):
    def test_fixed_window_waveform_normalizes_si_units(self) -> None:
        result = waveform_window_metrics(
            (0.0, 1.0e-12, 2.0e-12),
            (0.0, 1.0e-6, 0.0),
            (0.0, 3.0e-12),
            unit="A",
        )
        self.assertEqual(result["unit"], "uA")
        self.assertEqual(result["area_unit"], "uA*ps")
        self.assertAlmostEqual(result["peak_value"], 1.0, places=12)
        self.assertAlmostEqual(result["signed_time_integral"], 1.0, places=12)

    def test_waveform_metrics_and_centroid(self) -> None:
        result = waveform_metrics((0.0, 1.0, 2.0), (0.0, 2.0, 0.0), include_centroid=True)
        self.assertEqual(result["sample_count"], 3)
        self.assertEqual(result["p2p"], 2.0)
        self.assertAlmostEqual(result["signed_time_integral"], 2.0, places=12)
        self.assertEqual(result["peak_time"], 1.0)
        self.assertAlmostEqual(result["centroid_time"], 1.0, places=12)

    def test_waveform_occupancy_and_zero_crossings_are_shared(self) -> None:
        result = waveform_metrics((0.0, 1.0, 2.0, 3.0), (-1.0, 0.0, 2.0, -3.0))
        self.assertAlmostEqual(result["median"], -0.5, places=12)
        self.assertAlmostEqual(result["positive_occupancy"], 0.25, places=12)
        self.assertAlmostEqual(result["negative_occupancy"], 0.5, places=12)
        self.assertAlmostEqual(result["zero_occupancy"], 0.25, places=12)
        self.assertEqual(result["zero_crossing_count"], 2)

    def test_compare_metrics_use_exact_grid_by_default(self) -> None:
        result = compare_series((0.0, 1.0, 2.0), (1.0, 2.0, 3.0), (0.0, 1.0, 2.0), (2.0, 1.0, 4.0), include_correlation=True, include_scalar_fit=True)
        self.assertEqual(result["time_grid_exact"], True)
        self.assertEqual(result["pointwise_difference"], [1.0, -1.0, 1.0])
        self.assertEqual(result["max_abs_difference"], 1.0)
        self.assertEqual(result["p95_abs_difference"], 1.0)
        self.assertIn("correlation", result)
        self.assertIn("scalar_fit", result)
        with self.assertRaises(TimeGridMismatch):
            compare_series((0.0, 1.0), (1.0, 2.0), (0.0, 2.0), (1.0, 2.0))

    def test_fixed_window_compare_refuses_interpolation(self) -> None:
        with self.assertRaises(TimeGridMismatch):
            compare_windowed_series(
                (0.0, 1.0e-12, 2.0e-12),
                (0.0, 1.0, 2.0),
                (0.0, 1.5e-12, 3.0e-12),
                (0.0, 1.0, 2.0),
                (0.0, 3.0e-12),
            )


class OnsetAndKclTests(unittest.TestCase):
    def test_pre_noise_threshold_uses_only_pre_reference_scale(self) -> None:
        pre = (0.1, 0.2, 0.3)
        threshold = pre_noise_referenced_threshold(pre, 1.0)
        self.assertAlmostEqual(threshold, 1.49, places=12)
        result = first_persistent_exceedance(
            (0.0, 1.0, 2.0),
            (1.0, 1.5, 1.6),
            threshold,
        )
        self.assertEqual(result["status"], "CROSSED")
        self.assertEqual(result["first_index"], 1)

    def test_one_sample_and_three_sample_persistence_are_distinct(self) -> None:
        times = (0.0, 1.0, 2.0, 3.0)
        values = (0.0, 2.0, 0.0, 2.0)
        one = first_persistent_exceedance(times, values, 1.0, min_consecutive_samples=1)
        three = first_persistent_exceedance(times, values, 1.0, min_consecutive_samples=3)
        self.assertEqual(one["status"], "CROSSED")
        self.assertEqual(one["first_index"], 1)
        self.assertEqual(three["status"], "NO_CROSSING")

    def test_time_aware_persistence_reports_actual_nonuniform_span(self) -> None:
        times = (0.0, 0.010e-12, 0.035e-12, 0.060e-12)
        values = (0.0, 2.0, 2.0, 0.0)
        result = first_persistent_exceedance(
            times,
            values,
            1.0,
            min_consecutive_samples=3,
            min_duration_s=0.025e-12,
        )
        self.assertEqual(result["status"], "CROSSED")
        self.assertEqual(result["first_index"], 1)
        self.assertAlmostEqual(result["persistence_span_s"], 0.025e-12, places=24)
        self.assertEqual(result["persistence_sample_count"], 2)

    def test_tie_groups_use_declared_absolute_tolerance(self) -> None:
        groups = tie_groups(
            {"L0": 95.0, "L1": 95.025, "L2": 95.026},
            0.025,
        )
        self.assertEqual(groups[0]["layers"], ["L0", "L1"])
        self.assertEqual(groups[1]["layers"], ["L2"])

    def test_generic_kcl_uses_signed_coefficients(self) -> None:
        residual = linear_kcl_residual(
            {
                "a": (1.0e-6, 2.0e-6),
                "b": (0.5e-6, 1.0e-6),
                "c": (0.1e-6, 0.2e-6),
            },
            {"a": 1.0, "b": -2.0, "c": -1.0},
        )
        self.assertEqual(residual, (-0.1e-6, -0.2e-6))

    def test_kcl_window_summary_uses_actual_window_samples(self) -> None:
        result = kcl_window_metrics(
            (0.0, 1.0e-12, 3.0e-12),
            (1.0e-6, -2.0e-6, 4.0e-6),
            (0.0, 4.0e-12),
        )
        self.assertEqual(result["sample_count"], 3)
        self.assertAlmostEqual(result["max_abs_uA"], 4.0, places=12)
        self.assertAlmostEqual(result["rms_uA"], math.sqrt(7.0), places=12)

    def test_file_provenance_contains_hash_and_size(self) -> None:
        with tempfile.NamedTemporaryFile("wb", delete=False) as handle:
            handle.write(b"abc")
            path = Path(handle.name)
        self.addCleanup(lambda: path.unlink(missing_ok=True))
        snapshot = file_snapshot(path)
        self.assertEqual(snapshot["bytes"], 3)
        self.assertEqual(snapshot["sha256"], "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad")


if __name__ == "__main__":
    unittest.main(verbosity=2)
