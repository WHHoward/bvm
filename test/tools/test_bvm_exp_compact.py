#!/usr/bin/env python3
"""Focused tests for the Compact Quick V2 interface; no JoSIM science run."""

from __future__ import annotations

import importlib.util
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import yaml


REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "bvm-exp.py"
SPEC = importlib.util.spec_from_file_location("bvm_exp_compact", SCRIPT)
if SPEC is None or SPEC.loader is None:  # pragma: no cover
    raise RuntimeError(f"cannot import {SCRIPT}")
BVM_EXP = importlib.util.module_from_spec(SPEC)
sys.path.insert(0, str(REPO / "scripts"))
SPEC.loader.exec_module(BVM_EXP)


class CompactQuickTests(unittest.TestCase):
    SOURCE_RAW = REPO / (
        "test/exploration/bvmsim-qb-strict-qualification-v1-20260902/raw/s1/run-01.csv"
    )
    SOURCE_DECK = REPO / (
        "test/exploration/bvmsim-qb-strict-qualification-v1-20260902/migrated/s1_bvmsim_qb.cir"
    )

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="josim-compact-v2-")
        self.root = Path(self.temp.name) / "quick"
        self.root.mkdir()
        (self.root / "runs" / "A001").mkdir(parents=True)
        shutil.copyfile(self.SOURCE_RAW, self.root / "runs" / "A001" / "raw.csv")
        shutil.copyfile(self.SOURCE_DECK, self.root / "runs" / "A001" / "deck.cir")
        (self.root / "runs" / "A001" / "run.log").write_text("raw-only fixture\n", encoding="utf-8")
        config = {
            "schema_version": "compact-quick-v2",
            "id": "compact-test",
            "mode": "QUICK",
            "question": "Does the existing raw parse through the compact path?",
            "hypothesis": "The raw artifact remains readable.",
            "changed": "tooling path",
            "frozen": ["existing raw", "signal labels"],
            "deck": str(self.SOURCE_DECK),
            "run": {"solver": str(REPO / "build/josim-cli"), "args": []},
            "analysis": {
                "metrics": ["raw_qa", "waveform"],
                "signals": ["I(BVMOUT)", "P(BJ2|XBQ1)", "P(B01|XJTL1_1)"],
            },
            "visualization": {
                "mode": "compact",
                "style": "CLASSIC_LOCKED",
                "signals": ["I(BVMOUT)", "P(BJ2|XBQ1)", "P(B01|XJTL1_1)"],
            },
        }
        (self.root / "experiment.yaml").write_text(
            yaml.safe_dump(config, sort_keys=False), encoding="utf-8"
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_compact_config_and_next_attempt(self) -> None:
        normalized = BVM_EXP.validate_compact_config(
            BVM_EXP._load_yaml(self.root / "experiment.yaml"), self.root / "experiment.yaml"
        )
        self.assertEqual(normalized["mode"], "QUICK")
        self.assertEqual(normalized["visual_mode"], "compact")
        self.assertEqual(BVM_EXP._compact_next_attempt(self.root), "A002")
        (self.root / "runs" / "A003").mkdir()
        self.assertEqual(BVM_EXP._compact_next_attempt(self.root), "A004")

    def test_raw_only_analyze_is_idempotent_and_plot_is_classic(self) -> None:
        self.assertEqual(BVM_EXP.compact_analyze(self.root, "A001"), 0)
        result_path = self.root / "runs" / "A001" / "result.yaml"
        first = result_path.read_bytes()
        result = yaml.safe_load(first)
        self.assertEqual(result["schema_version"], "compact-quick-v2-result")
        self.assertEqual(result["status"], "AWAITING_USER_REVIEW")
        self.assertEqual(result["execution"], "EXISTING_RAW_ONLY")
        self.assertEqual(result["hypothesis"], "The raw artifact remains readable.")
        self.assertEqual(BVM_EXP.compact_analyze(self.root, "A001"), 0)
        self.assertEqual(result_path.read_bytes(), first)
        self.assertEqual(BVM_EXP.compact_plot(self.root, "A001"), 0)
        overview = self.root / "plots" / "RESULT_OVERVIEW.html"
        self.assertTrue(overview.is_file())
        self.assertGreater(overview.stat().st_size, 0)
        self.assertIn("BVMOUT", overview.read_text(encoding="utf-8"))

    def test_inspect_is_human_facing_and_compact(self) -> None:
        self.assertEqual(BVM_EXP.compact_analyze(self.root, "A001"), 0)
        self.assertEqual(BVM_EXP.compact_inspect(self.root, "A001"), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
