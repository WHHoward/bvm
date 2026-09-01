#!/usr/bin/env python3
"""Config and review-gate regressions for the minimal Quick CLI."""

from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))
SCRIPT = REPO / "scripts" / "bvm-exp.py"
SPEC = importlib.util.spec_from_file_location("bvm_exp", SCRIPT)
if SPEC is None or SPEC.loader is None:  # pragma: no cover
    raise RuntimeError(f"cannot import {SCRIPT}")
BVM_EXP = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BVM_EXP)


class QuickConfigTests(unittest.TestCase):
    CONFIG = REPO / "test/exploration/tooling-consolidation-smoke-v1-20260901/experiment.yaml"

    def test_smoke_config_is_explicit_and_compact(self) -> None:
        config = BVM_EXP._load_yaml(self.CONFIG)
        normalized = BVM_EXP.validate_config(config, self.CONFIG)
        self.assertEqual(normalized["mode"], "QUICK")
        self.assertTrue(normalized["smoke"])
        self.assertEqual(normalized["visual_mode"], "compact")
        self.assertEqual(len(normalized["cases"]), 2)
        self.assertEqual(
            [case["id"] for case in normalized["cases"]],
            ["9ps-12x320-replay", "13ps-12x320-replay"],
        )
        self.assertEqual(
            BVM_EXP._check_deck_run(
                REPO / "test/exploration/bvm-load-qb-matrix-v1-20260901/inputs/replay/9ps/12x320/logical1_read.cir",
                timestep_ps=0.0125,
                stop_ps=170.0,
            ),
            {"timestep_ps": 0.0125, "stop_ps": 170.0},
        )

    def test_alternative_style_requires_explicit_authorization(self) -> None:
        config = BVM_EXP._load_yaml(self.CONFIG)
        config["visualization"]["style"] = "NEW_STYLE"
        config.pop("alternative_style_authorized", None)
        with self.assertRaises(BVM_EXP.ConfigError):
            BVM_EXP.validate_config(config, self.CONFIG)

    def test_existing_quick_output_is_never_reused(self) -> None:
        output = self.CONFIG.parent / "quick/tooling-consolidation-smoke-v1"
        self.assertTrue(output.is_dir())
        analysis = json.loads((output / "analysis.json").read_text(encoding="utf-8"))
        self.assertEqual(analysis["outcome"], "TOOLING_SMOKE_TEST_ONLY")
        self.assertEqual(analysis["visualization"]["status"], "PASS")
        self.assertTrue((output / "RESULT_BRIEF.md").is_file())
        self.assertIn("AWAITING_USER_REVIEW", (output / "RESULT_BRIEF.md").read_text(encoding="utf-8"))

    def test_smoke_brief_separates_tooling_action_from_historical_comparison(self) -> None:
        output = self.CONFIG.parent / "quick/tooling-consolidation-smoke-v1"
        brief = (output / "RESULT_BRIEF.md").read_text(encoding="utf-8")
        self.assertIn("Tooling action performed in this smoke:", brief)
        self.assertIn("- no circuit change", brief)
        self.assertIn("- no parameter change", brief)
        self.assertIn("- no JoSIM rerun", brief)
        self.assertIn("- READ width: 9 ps → 13 ps", brief)
        self.assertIn(
            "- all other registered scientific conditions remain existing historical fixture conditions",
            brief,
        )
        self.assertNotIn("- Baseline:", brief)
        self.assertNotIn("- Candidate:", brief)
        self.assertNotIn("Changed variables: tooling path only", brief)


if __name__ == "__main__":
    unittest.main(verbosity=2)
