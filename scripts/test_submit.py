#!/usr/bin/env python3
"""Focused adversarial tests for the global submit/package entry point."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import submit


class SubmitWorkflowTests(unittest.TestCase):
    def test_porcelain_parser_preserves_spaces_in_paths(self) -> None:
        parsed = submit.parse_porcelain_z("?? test/exploration/x/snapshot (2).zip\0 M test/exploration/x/deck.cir\0")
        self.assertEqual(parsed["test/exploration/x/snapshot (2).zip"], "??")
        self.assertEqual(parsed["test/exploration/x/deck.cir"], "M")

    def test_package_filter_does_not_drop_run_snapshots(self) -> None:
        self.assertTrue(submit.package_output_path("test/exploration/x/handoff/x.zip"))
        self.assertTrue(submit.package_output_path("test/exploration/x/handoff/PACKAGE_QA.json"))
        self.assertFalse(submit.package_output_path("test/exploration/x/runs/N1/snapshot.zip"))
        self.assertFalse(submit.generated_cache_path("test/exploration/x/runs/N1/run.log"))

    def test_scope_cannot_escape_repository(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(RuntimeError):
                submit.normalize_scopes([temp], submit.head(), submit.head())

    def test_component_groups_cover_all_five_families_and_four_runs(self) -> None:
        scope = submit.REPO / "test/exploration/bvm-bq-cb-gap-2x1-v2-20260923"
        specs = submit.component_bundle_specs(scope, "test-only")
        self.assertEqual({spec["component"] for spec in specs}, {"BVM", "QB", "CB", "ACC", "GAP"})
        for spec in specs:
            page_paths = [member for _, member in spec["sources"] if "component_" in member and member.endswith(".html")]
            self.assertEqual(len(page_paths), 4)
            self.assertLess(sum(path.stat().st_size for path, _ in spec["sources"]), submit.MAX_GIT_FILE_BYTES)

    def test_existing_source_bundle_is_reopened_and_hash_checked(self) -> None:
        package = submit.REPO / "test/exploration/2x1-bvm-qb-c-sim1/handoff/2x1-bvm-qb-c-sim1_source_bundle_v1.zip"
        qa = package.with_name(package.stem + "_PACKAGE_QA.json")
        result = submit.verify_existing_bundle(package, qa)
        self.assertEqual(result["status"], "PASS")


if __name__ == "__main__":
    unittest.main(verbosity=2)
