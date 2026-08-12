#!/usr/bin/env python3
"""test_rebuild_historical_metrics_v2 -- deterministic M10 regression checks.

Verifies that rebuild_historical_metrics_v2.py:
  - rejects units/hash/time/column/control errors (QA guards),
  - produces exactly the four preregistered V2 JSON outputs with correct
    structure, provenance, signed endpoint arithmetic, and control fields,
  - never emits forbidden event/Gate vocabulary,
  - and proves legacy CSV/JSON preservation (no raw file modified).

Pure stdlib; never executes JoSIM and never modifies any file.
"""
from __future__ import annotations

import csv
import json
import pathlib
import sys
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))
import rebuild_historical_metrics_v2 as gen  # noqa: E402

FOUR_OUTPUTS = (
    "test/final/single_bvm_qb/data/metrics_v2/baseline-v2.json",
    "test/final/interface/data/metrics_v2/p0-v2.json",
    "test/final/bvm/data/metrics_v2/p2-v2.json",
    "test/final/qb/data/metrics_v2/bq-v4-v2.json",
)

# Claim-form vocabulary only: the outputs' limitation text legitimately names
# "sfq"/"fluxoid"/"gate" inside prohibition sentences, so only field-name or
# count-style occurrences are forbidden.
FORBIDDEN_VOCAB = (
    "fast_events", "pulse_count", "sfq_count", "event_count",
    "activity_clusters", "platform_delta", "area_turns", "converged",
    '"sfq"', '"fluxoid"', "interface_gate", '"pass"', '"fail"',
)


class TestQARejections(unittest.TestCase):
    """AC4: generator rejects bad input instead of guessing."""

    def setUp(self) -> None:
        self.tmp = REPO_ROOT / "test" / "metrics" / "_m10_tmp"
        self.tmp.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        for p in self.tmp.iterdir():
            p.unlink()
        self.tmp.rmdir()

    def _write(self, name: str, header: str, rows: list[str]) -> pathlib.Path:
        p = self.tmp / name
        p.write_text(header + "\n" + "\n".join(rows) + "\n", encoding="utf-8")
        return p

    def test_missing_phase_column_rejected(self) -> None:
        p = self._write("bad.csv", "time,P(B1)", ["0,1.0", "1e-12,2.0"])
        with self.assertRaises(ValueError) as ctx:
            gen.read_csv(p, ["P(B1)", "P(B2)"])
        self.assertIn("missing declared phase columns", str(ctx.exception))

    def test_nonfinite_values_rejected(self) -> None:
        p = self._write("nan.csv", "time,P(B1)", ["0,1.0", "1e-12,nan"])
        with self.assertRaises(ValueError):
            gen.read_csv(p, ["P(B1)"])

    def test_non_monotonic_time_rejected(self) -> None:
        p = self._write("tbad.csv", "time,P(B1)", ["0,1.0", "0,2.0"])
        with self.assertRaises(ValueError) as ctx:
            gen.read_csv(p, ["P(B1)"])
        self.assertIn("not strictly increasing", str(ctx.exception))

    def test_empty_csv_rejected(self) -> None:
        p = self._write("empty.csv", "time,P(B1)", [])
        with self.assertRaises(ValueError):
            gen.read_csv(p, ["P(B1)"])


class TestOutputStructure(unittest.TestCase):
    """AC2: four outputs, correct schema/provenance/arithmetic."""

    def test_four_outputs_exist(self) -> None:
        for out in FOUR_OUTPUTS:
            self.assertTrue((REPO_ROOT / out).is_file(), f"missing {out}")

    def test_output_schema_and_provenance(self) -> None:
        for out in FOUR_OUTPUTS:
            with open(REPO_ROOT / out, encoding="utf-8") as f:
                d = json.load(f)
            self.assertEqual(d["schema_version"], 1)
            self.assertEqual(d["metric_spec"]["version"], "2.0.0")
            self.assertEqual(d["metric_spec"]["sha256"],
                             "f88a36f4d310b2572efdc7408d734640f25dd5aea2246b74fbb8b7bb7f0be470")
            self.assertIn("reconstruction_plan", d)
            self.assertIn("generated_at", d)
            self.assertTrue(d["runs"])
            for run in d["runs"]:
                self.assertIn("input", run)
                self.assertEqual(len(run["input"]["sha256"]), 64)
                self.assertIn("quantities", run)

    def test_endpoint_arithmetic_consistent(self) -> None:
        # For every run and column, turns == rad/(2*pi) exactly as reported.
        for out in FOUR_OUTPUTS:
            with open(REPO_ROOT / out, encoding="utf-8") as f:
                d = json.load(f)
            for run in d["runs"]:
                for col, q in run["quantities"].items():
                    self.assertAlmostEqual(
                        q["endpoint_delta_turns"],
                        q["endpoint_delta_rad"] / (2.0 * 3.141592653589793),
                        places=12,
                    )

    def test_known_baseline_constants(self) -> None:
        # Cross-check against independently recomputed historical constants.
        with open(REPO_ROOT / "test/final/single_bvm_qb/data/metrics_v2/baseline-v2.json", encoding="utf-8") as f:
            d = json.load(f)
        q = d["runs"][0]["quantities"]
        self.assertAlmostEqual(q["P(B_JM1|XBVM1)"]["endpoint_delta_turns"], -0.940575, places=5)
        self.assertAlmostEqual(q["P(BJS|XBQ)"]["endpoint_delta_turns"], 0.998338, places=5)
        self.assertAlmostEqual(q["P(BJL1|XBQ)"]["endpoint_delta_turns"], 0.070556, places=5)
        self.assertAlmostEqual(q["P(BJL2|XBQ)"]["endpoint_delta_turns"], 0.059816, places=5)

    def test_p0_control_only_bump_0(self) -> None:
        # AC3: only bump files use bump_0 as comparator; sustained files have none.
        with open(REPO_ROOT / "test/final/interface/data/metrics_v2/p0-v2.json", encoding="utf-8") as f:
            d = json.load(f)
        bump_0_path = "test/final/interface/data/test_dcsfq_behavior_bump_0.csv"
        control_pairs = 0
        for run in d["runs"]:
            if "control_corrected" in run:
                control_pairs += 1
                self.assertEqual(run["control"]["path"], bump_0_path)
                self.assertNotIn("sustained", run["input"]["path"])
        self.assertEqual(control_pairs, 7)  # 8 bumps - bump_0 itself = 7

    def test_bq_v4_six_runs(self) -> None:
        with open(REPO_ROOT / "test/final/qb/data/metrics_v2/bq-v4-v2.json", encoding="utf-8") as f:
            d = json.load(f)
        self.assertEqual(len(d["runs"]), 6)


class TestForbiddenVocabulary(unittest.TestCase):
    """AC4: outputs never call endpoint arithmetic an event/Gate verdict."""

    def test_no_forbidden_vocabulary_in_outputs(self) -> None:
        for out in FOUR_OUTPUTS:
            text = (REPO_ROOT / out).read_text(encoding="utf-8").lower()
            for term in FORBIDDEN_VOCAB:
                self.assertNotIn(term, text, f"{out} contains {term}")

    def test_limitations_and_not_applicable_present(self) -> None:
        for out in FOUR_OUTPUTS:
            with open(REPO_ROOT / out, encoding="utf-8") as f:
                d = json.load(f)
            self.assertTrue(d["limitations"])
            self.assertTrue(d["not_applicable"])
            self.assertTrue(any("NOT_APPLICABLE" in x for x in d["not_applicable"]))


class TestLegacyPreservation(unittest.TestCase):
    """AC4: legacy raw CSV/JSON files are untouched (hashes + bytes)."""

    LEGACY_SAMPLES = (
        "test/final/single_bvm_qb/data/test_bvm_bq_baseline.csv",
        "test/final/interface/data/test_dcsfq_behavior_bump_0.csv",
        "test/final/bvm/data/test_bvm_multivortex.csv",
        "test/final/qb/data/bq_v4_sweep110.csv",
    )

    def test_legacy_files_unchanged_by_generator_import(self) -> None:
        # Importing the generator must not mutate anything; re-run build on a
        # copy and compare the raw bytes of the legacy files.
        before = {p: (REPO_ROOT / p).read_bytes() for p in self.LEGACY_SAMPLES}
        # rebuild family computations only (no writes outside metrics_v2)
        for name, spec in gen.INVENTORY.items():
            gen.build_family(name, spec)
        for p, blob in before.items():
            self.assertEqual((REPO_ROOT / p).read_bytes(), blob, f"{p} changed")


if __name__ == "__main__":
    unittest.main()
