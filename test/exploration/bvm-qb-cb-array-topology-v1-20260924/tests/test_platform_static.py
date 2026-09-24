from __future__ import annotations

import contextlib
import hashlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SERIES = Path(__file__).resolve().parents[1]
REPO = next(path for path in (SERIES, *SERIES.parents) if (path / ".git").exists())
sys.path.insert(0, str(SERIES / "scripts"))

import package  # noqa: E402
import plot_run  # noqa: E402
import run_case  # noqa: E402
from config import COMPONENT_KEYS, USER_CASE_KEYS, load_env  # noqa: E402
from components import load_reference  # noqa: E402
from stimulus import load_stimulus  # noqa: E402


CASES = (
    ("2x1_M01", 2, "01", "0,1", "13,2", "1,0"),
    ("3x1_M011", 3, "011", "1,0,1", "0,3,1", "0,1,0"),
    ("4x1_M1011", 4, "1011", "0,1,0,1", "1,2,3,1", "1,0,1,0"),
)


def values_for(size: int, mask: str, qb: str, sjtl: str, post: str) -> dict[str, str]:
    values = load_env(SERIES / "USER_CASE.env", USER_CASE_KEYS)
    reference = load_reference()
    values.update({key: reference[key] for key in COMPONENT_KEYS})
    values.update({"NAME": "static_render_fixture", "OUTPUT_MODE": "TERMINAL",
                   "TERM_R": "2", "DT": "0.01p", "STOP": "200p"})
    masks = "00,01,10,11" if size == 2 else mask
    values.update({"ARRAY_SIZE": str(size), "MASKS": masks, "QB_CB": qb,
                   "SJTL_COUNT": sjtl, "POST_SJTL_CB": post})
    return values


def digest_tree(root: Path) -> dict[str, str]:
    result = {}
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        result[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


class PlatformStaticTests(unittest.TestCase):
    def test_package_git_status_parser_preserves_first_path_character(self):
        self.assertEqual(
            package.parse_worktree_changes(
                " M test/exploration/bvm-qb-cb-array-topology-v1-20260924/scripts/package.py\n"),
            {"test/exploration/bvm-qb-cb-array-topology-v1-20260924/scripts/package.py": "M"},
        )

    def test_plot_only_result_edit_does_not_count_as_new_physical_solve(self):
        self.assertEqual(package._new_solve_count({"physical_solve_count": 1}, existed_at_base=True), 0)
        self.assertEqual(package._new_solve_count({"physical_solve_count": 1}, existed_at_base=False), 1)
        self.assertEqual(package._new_solve_count({"physical_solve_count": 0}, existed_at_base=False), 0)

    def test_three_render_fixtures_are_deterministic_and_non_experimental(self):
        stimulus = load_stimulus(SERIES / "STIMULUS.env")
        with tempfile.TemporaryDirectory(prefix="render-fixture-test-") as tmp:
            for name, size, mask, qb, sjtl, post in CASES:
                user = values_for(size, mask, qb, sjtl, post)
                fixture = Path(tmp) / name
                result = run_case.render_case(user, stimulus, mask, fixture, fixture_only=True)
                plot_manifest = plot_run.plan_only(fixture)
                self.assertEqual(result["status"], "RENDER_FIXTURE_ONLY")
                self.assertEqual(result["physical_solve_count"], 0)
                self.assertEqual(len(plot_manifest["pages"]), 5)
                self.assertEqual(plot_manifest["render_status"], "RENDER_FIXTURE_ONLY")
                self.assertIsNone(plot_manifest["raw_sha256"])
                if name == "2x1_M01":
                    cb_page = next(page for page in plot_manifest["pages"] if page["page"] == "cb")
                    self.assertEqual([item["role"] for item in cb_page["component_roles"]],
                                     ["Level 1 post-sJTL CB", "Level 2 QB-side CB"])
                self.assertFalse((fixture / "raw.csv").exists())
                self.assertFalse(list(fixture.rglob("*.html")))
                self.assertIn("RENDER_FIXTURE_ONLY", (fixture / "actual_deck.cir").read_text())
                self.assertIn("RENDER_FIXTURE_ONLY", (fixture / "stimulus.inc").read_text())
                for manifest_name in ("topology_manifest.json", "source_manifest.json",
                                      "probe_manifest.json"):
                    manifest = json.loads((fixture / manifest_name).read_text())
                    self.assertEqual(manifest["render_status"], "RENDER_FIXTURE_ONLY")
                deck_text = (fixture / "actual_deck.cir").read_text()
                self.assertRegex(deck_text, r"(?m)^R_TERM FINAL_OUT 0 2$")
                self.assertRegex(deck_text, r"(?m)^\.tran 0.01p 200p$")
                self.assertNotRegex(deck_text, r"(?mi)^\s*\.title\b")
                expected_includes = [
                    ".include snapshot/sources/bvm_tunable.cir",
                    ".include snapshot/sources/BQ_tunable.cir",
                    ".include snapshot/sources/CB_tunable.cir",
                    ".include snapshot/sources/sJTL_tunable.cir",
                    ".include stimulus.inc",
                ]
                include_lines = [line for line in deck_text.splitlines()
                                 if line.lstrip().startswith(".include")]
                self.assertEqual(include_lines, expected_includes)
                self.assertFalse(any('"' in line for line in include_lines))
                parameter_data = json.loads((fixture / "parameter_manifest.json").read_text())
                self.assertEqual(set(parameter_data), {
                    "schema", "bvm", "qb", "cb", "sjtl", "topology", "solver",
                    "stimulus_reference", "mask", "overrides",
                })
                top_level_elements = [line.split()[0].casefold() for line in deck_text.splitlines()
                                      if line.strip() and not line.lstrip().startswith(("*", "."))]
                self.assertEqual(len(top_level_elements), len(set(top_level_elements)))
                before = digest_tree(fixture)
                rerendered = run_case.render_case(user, stimulus, mask, fixture, fixture_only=True)
                plot_run.plan_only(fixture)
                self.assertEqual(before, digest_tree(fixture))
                self.assertEqual(rerendered["status"], "RENDER_FIXTURE_ONLY")
        assets = list((SERIES / "plots").rglob("plotly.min.js"))
        self.assertEqual(assets, [SERIES / "plots" / "assets" / "plotly.min.js"])

    def test_render_only_cli_never_calls_subprocess(self):
        with patch.object(run_case.subprocess, "run", side_effect=AssertionError("solver/process called")):
            with tempfile.TemporaryDirectory(
                    prefix="render-only-cli-test-", dir=SERIES / "tests" / "fixtures") as tmp:
                output_dir = Path(tmp) / "rendered"
                user_fixture = Path(tmp) / "USER_CASE.env"
                user_fixture.write_text(run_case.stable_env(values_for(2, "01", "0,1", "1,1", "0,0")),
                                        encoding="utf-8")
                rc = run_case.main(["--user-case", str(user_fixture), "--render-only", "--mask", "01",
                                    "--output-dir", str(output_dir)])
                self.assertFalse((output_dir / "raw.csv").exists())
        self.assertEqual(rc, 0)
        self.assertFalse((SERIES / "tests/fixtures/rendered/2x1_M01/raw.csv").exists())

    def test_package_and_submit_dry_run_logic_is_pure(self):
        output = io.StringIO()
        with patch.object(package, "create_package", side_effect=AssertionError("package created")):
            with contextlib.redirect_stdout(output):
                rc = package.main(["--mode", "full", "--tag", "STATIC-SMOKE", "--dry-run"])
        self.assertEqual(rc, 0)
        package_plan = json.loads(output.getvalue())
        self.assertEqual(package_plan["status"], "PACKAGE_DRY_RUN_PASS")
        self.assertFalse(package_plan["archive_created"])
        self.assertFalse(package_plan["mirror_created"])

        import submit  # noqa: E402
        plan = submit.build_submission_plan(
            "STATIC-SMOKE", "full", ["scripts/run_case.py"],
            {"head_commit": "fixture-head", "base": None,
             "files": [], "package_path": "handoff/not-created.zip",
             "mirror_path": "/mnt/d/BVM_Backages/not-created.zip",
             "physical_solve_count": 0},
            package_only=False, no_push=False,
        )
        self.assertFalse(plan["package_created"])
        self.assertFalse(plan["solver_invoked"])
        self.assertFalse(plan["mirror_written"])

        package_plan = {
            "head_commit": "fixture-head", "base": None, "files": [],
            "package_path": SERIES / "handoff" / "not-created.zip",
            "mirror_path": Path("/mnt/d/BVM_Backages/not-created.zip"),
            "manifest": {"new_physical_solve_count": 1},
        }
        with patch.object(submit, "staged_outside_series", return_value=[]), \
             patch.object(submit, "completed_runs", return_value=([], {
                 "batch_id": "fixture-batch", "status": "COMPLETE_MECHANICAL",
                 "requested_masks": ["01"], "total_physical_solve_count": 1,
             })), \
             patch.object(submit, "series_changes", return_value=["runs/fixture/result.json"]), \
             patch.object(submit, "current_head", return_value="fixture-head"), \
             patch.object(submit.package, "build_plan", return_value=package_plan), \
             patch.object(submit.package, "create_package", side_effect=AssertionError("archive created")), \
             patch.object(submit.subprocess, "run", side_effect=AssertionError("external process called")):
            preview = io.StringIO()
            with contextlib.redirect_stdout(preview):
                rc = submit.main(["STATIC-SMOKE", "--mode", "full", "--dry-run"])
        self.assertEqual(rc, 0)
        submission = json.loads(preview.getvalue())
        self.assertFalse(submission["package_created"])
        self.assertFalse(submission["solver_invoked"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
