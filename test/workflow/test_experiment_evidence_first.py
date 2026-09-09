#!/usr/bin/env python3
"""Regression tests for the evidence-first Compact workflow.

All fixtures are synthetic or copied existing raw; no JoSIM executable is
invoked by this test module.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import sys
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

import yaml


REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))

spec = importlib.util.spec_from_file_location("bvm_exp_evidence_first", REPO / "scripts/bvm-exp.py")
if spec is None or spec.loader is None:  # pragma: no cover
    raise RuntimeError("cannot import bvm-exp.py")
BVM_EXP = importlib.util.module_from_spec(spec)
spec.loader.exec_module(BVM_EXP)

from build_experiment_package import PackageError, build_package  # noqa: E402


class EvidenceFirstTests(unittest.TestCase):
    SOURCE_RAW = REPO / (
        "test/exploration/bvmsim-qb-strict-qualification-v1-20260902/raw/s1/run-01.csv"
    )
    SOURCE_DECK = REPO / (
        "test/exploration/bvmsim-qb-strict-qualification-v1-20260902/migrated/s1_bvmsim_qb.cir"
    )

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="josim-evidence-first-")
        self.root = Path(self.temp.name) / "experiment"
        (self.root / "runs" / "A001").mkdir(parents=True)
        shutil.copyfile(self.SOURCE_RAW, self.root / "runs" / "A001" / "raw.csv")
        shutil.copyfile(self.SOURCE_DECK, self.root / "runs" / "A001" / "deck.cir")
        (self.root / "runs" / "A001" / "run.log").write_text("synthetic fixture\n", encoding="utf-8")
        config = {
            "schema_version": "compact-quick-v2",
            "workflow_policy": "EVIDENCE_FIRST_V1",
            "id": "evidence-first-test",
            "mode": "QUICK",
            "question": "Can the tool preserve an existing raw artifact?",
            "hypothesis": "The raw artifact remains mechanically readable.",
            "changed": "tooling path",
            "scientific_review_authorization": "NOT_GRANTED",
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
                "profile": "CLASSIC_LOCKED_COMPACT",
                "signals": ["I(BVMOUT)", "P(BJ2|XBQ1)", "P(B01|XJTL1_1)"],
            },
            "package": {"include_plots": False, "additional_paths": []},
        }
        (self.root / "experiment.yaml").write_text(
            yaml.safe_dump(config, sort_keys=False), encoding="utf-8"
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_default_qa_does_not_call_scientific_analyzer(self) -> None:
        normalized = BVM_EXP.validate_compact_config(
            BVM_EXP._load_yaml(self.root / "experiment.yaml"), self.root / "experiment.yaml"
        )
        with mock.patch.object(BVM_EXP, "_analyze_raw", side_effect=AssertionError("scientific analyzer called")):
            result = BVM_EXP._compact_mechanical_qa(normalized, self.root / "runs" / "A001")
        self.assertEqual(result["artifact_status"], "VALID")
        self.assertFalse(result["scientific_analysis_performed"])
        self.assertEqual(result["analysis_status"], "NOT_PERFORMED")
        self.assertNotIn("signals", result)
        self.assertNotIn("strict_event", result)

    def test_v21_visualization_requires_ordered_five_layer_boundaries(self) -> None:
        config = BVM_EXP._load_yaml(self.root / "experiment.yaml")
        config["visualization"]["profile"] = "SYSTEM_CHAIN_V2_1"
        config["visualization"]["focused_windows_ps"] = [[110.0, 121.0]]
        config["visualization"]["layers"] = [
            {
                "id": layer_id,
                "input_boundary": ["INPUT"],
                "internal_state": ["INTERNAL"],
                "output_boundary": ["OUTPUT"],
                "overview_window_ps": [0.0, 200.0],
                "focused_windows_ps": [[110.0, 121.0]],
            }
            for layer_id in (
                "01_SIGNAL_TIMING",
                "02_BVM_STATE",
                "03_JSL_CHAIN",
                "04_QB_STATE",
                "05_JTL_CHAIN",
            )
        ]
        normalized = BVM_EXP.validate_compact_config(config, self.root / "experiment.yaml")
        self.assertEqual(normalized["visual_profile"], "SYSTEM_CHAIN_V2_1")
        config["visualization"]["layers"] = config["visualization"]["layers"][:-1]
        with self.assertRaises(BVM_EXP.ConfigError):
            BVM_EXP.validate_compact_config(config, self.root / "experiment.yaml")

    def test_v21_renderer_emits_overview_and_focus_for_each_layer(self) -> None:
        config = BVM_EXP._load_yaml(self.root / "experiment.yaml")
        labels = ["I(BVMOUT)", "P(BJ2|XBQ1)", "P(B01|XJTL1_1)"]
        config["visualization"].update({
            "profile": "SYSTEM_CHAIN_V2_1",
            "signals": labels,
            "focused_windows_ps": [[0.0, 10.0]],
            "layers": [
                {
                    "id": layer_id,
                    "input_boundary": [labels[0]],
                    "internal_state": [labels[1]],
                    "output_boundary": [labels[2]],
                    "overview_window_ps": [0.0, 200.0],
                    "focused_windows_ps": [[0.0, 10.0]],
                }
                for layer_id in (
                    "01_SIGNAL_TIMING",
                    "02_BVM_STATE",
                    "03_JSL_CHAIN",
                    "04_QB_STATE",
                    "05_JTL_CHAIN",
                )
            ],
        })
        normalized = BVM_EXP.validate_compact_config(config, self.root / "experiment.yaml")
        rendered = BVM_EXP._compact_render(normalized, self.root / "runs" / "A001")
        self.assertEqual(rendered["status"], "PASS")
        visualization = BVM_EXP._compact_write_visualization_artifacts(
            normalized, self.root / "runs" / "A001", {}, rendered
        )
        self.assertEqual(visualization["qa"]["status"], "PASS", visualization["qa"])
        self.assertEqual(len(visualization["manifest"]["standalone_entries"]), 10)
        self.assertEqual(
            len(list((self.root / "analysis" / "visualization_derived").rglob("*.csv"))),
            10,
        )
        self.assertTrue((self.root / "analysis" / "visualization_qa.json").is_file())

    def test_scientific_review_requires_explicit_flag(self) -> None:
        self.assertEqual(BVM_EXP.compact_analyze(self.root, "A001"), 0)
        self.assertFalse((self.root / "analysis" / "scientific_review.json").exists())
        result_before = (self.root / "runs" / "A001" / "result.yaml").read_bytes()
        with mock.patch.object(
            BVM_EXP,
            "_compact_compute_analysis",
            return_value={"artifact_status": "VALID", "test_double": True},
        ):
            self.assertEqual(
                BVM_EXP.compact_analyze(
                    self.root, "A001", scientific_review_authorized=True
                ),
                0,
            )
        review = json.loads((self.root / "analysis" / "scientific_review.json").read_text(encoding="utf-8"))
        self.assertEqual(review["authorization"], "SCIENTIFIC_REVIEW_AUTHORIZED")
        self.assertTrue(review["scientific_analysis_performed"])
        self.assertEqual((self.root / "runs" / "A001" / "result.yaml").read_bytes(), result_before)

    def _prepare_package_inputs(self) -> None:
        (self.root / "PREFLIGHT.md").write_text(
            "# Preflight\n\nThis experiment is governed by docs/EXPERIMENT_CONTRACT.md.\n",
            encoding="utf-8",
        )
        analysis = self.root / "analysis"
        analysis.mkdir()
        for name in (
            "raw_qa.json",
            "deck_diff_qa.json",
            "provenance.json",
            "execution_summary.json",
            "transformation_registry.json",
        ):
            (analysis / name).write_text(json.dumps({"status": "PASS"}) + "\n", encoding="utf-8")
        (analysis / "provenance.json").write_text(
            json.dumps({"status": "PASS", "raw": {"path": "runs/A001/raw.csv"}}) + "\n",
            encoding="utf-8",
        )
        (analysis / "visualization_manifest.json").write_text(
            json.dumps({"schema": "test-viz", "standalone": ["A001"]}) + "\n", encoding="utf-8"
        )
        (analysis / "visualization_qa.json").write_text(
            json.dumps({"status": "PASS"}) + "\n", encoding="utf-8"
        )
        (analysis / "run_summaries").mkdir()
        (analysis / "run_summaries" / "A001.md").write_text("A001 navigation\n", encoding="utf-8")
        (self.root / "runs" / "A001" / "metadata.json").write_text(
            json.dumps({"run_id": "A001", "artifact_status": "VALID"}) + "\n", encoding="utf-8"
        )

    def test_package_contents_hashes_and_immutability(self) -> None:
        self._prepare_package_inputs()
        raw = self.root / "runs" / "A001" / "raw.csv"
        before = hashlib.sha256(raw.read_bytes()).hexdigest()
        result = build_package(self.root, requested_attempt="A001")
        package = self.root / result["package_path"]
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["raw_files_modified"], 0)
        self.assertEqual(result["source_raw_sha256"]["A001"], before)
        self.assertTrue((self.root / result["qa_path"]).is_file())
        with zipfile.ZipFile(package) as archive:
            names = set(archive.namelist())
            for required in (
                "experiment.yaml",
                "PREFLIGHT.md",
                "EVIDENCE_MANIFEST.md",
                "RAW_ANALYSIS_HANDOFF_MANIFEST.json",
                "SOURCE_MANIFEST.json",
                "runs/A001/deck.cir",
                "runs/A001/raw.csv",
                "runs/A001/metadata.json",
                "runs/A001/run.log",
                "analysis/raw_qa.json",
                "analysis/deck_diff_qa.json",
                "analysis/provenance.json",
                "analysis/execution_summary.json",
                "analysis/transformation_registry.json",
                "analysis/visualization_manifest.json",
                "analysis/visualization_qa.json",
                "analysis/run_summaries/A001.md",
            ):
                self.assertIn(required, names)
            self.assertEqual(hashlib.sha256(archive.read("runs/A001/raw.csv")).hexdigest(), before)
            self.assertNotIn("handoff/PACKAGE_QA.json", names)
        self.assertEqual(hashlib.sha256(raw.read_bytes()).hexdigest(), before)
        with self.assertRaises(PackageError):
            build_package(self.root, requested_attempt="A001")

    def test_package_failure_writes_detached_fail_qa_and_no_zip(self) -> None:
        self._prepare_package_inputs()
        (self.root / "runs" / "A001" / "metadata.json").unlink()
        with self.assertRaises(PackageError):
            build_package(self.root, requested_attempt="A001")
        qa = json.loads((self.root / "handoff" / "PACKAGE_QA.json").read_text(encoding="utf-8"))
        self.assertEqual(qa["status"], "FAIL")
        self.assertFalse((self.root / "handoff" / "evidence-first-test_raw_handoff.zip").exists())

    def test_in_repository_package_commit_is_default_and_closes_qa(self) -> None:
        repo = Path(self.temp.name) / "git-repo"
        root = repo / "experiment"
        (root / "handoff").mkdir(parents=True)
        (root / "runs" / "A001").mkdir(parents=True)
        (root / "runs" / "A001" / "metadata.json").write_text("{}\n", encoding="utf-8")
        package_path = root / "handoff" / "commit-test_raw_handoff.zip"
        package_path.write_bytes(b"immutable package")
        qa_path = root / "handoff" / "PACKAGE_QA.json"
        qa_path.write_text(json.dumps({"status": "PASS", "zip_committed": False}) + "\n", encoding="utf-8")
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@example.invalid"], check=True)
        subprocess.run(["git", "-C", str(repo), "config", "user.name", "Evidence Test"], check=True)
        with mock.patch.object(BVM_EXP, "REPO", repo):
            result = BVM_EXP._compact_commit_experiment(
                root, {"package_path": "handoff/commit-test_raw_handoff.zip"}
            )
        self.assertEqual(result["status"], "PASS")
        self.assertTrue(json.loads(qa_path.read_text(encoding="utf-8"))["zip_committed"])
        self.assertIn("commit-test_raw_handoff.zip", subprocess.run(
            ["git", "-C", str(repo), "ls-tree", "-r", "--name-only", "HEAD"],
            check=True, capture_output=True, text=True,
        ).stdout)

    def test_run_default_packages_and_stops_without_scientific_analysis(self) -> None:
        """A fake solver exercises the workflow wiring without a JoSIM solve."""

        root = Path(self.temp.name) / "run"
        (root / "inputs").mkdir(parents=True)
        deck = root / "inputs" / "main.cir"
        deck.write_text("* synthetic deck\n", encoding="utf-8")
        fake_solver = root / "fake_solver.py"
        fake_solver.write_text(
            "#!/usr/bin/env python3\n"
            "import pathlib, sys\n"
            "if '--version' in sys.argv:\n"
            "    print('fake-solver 1')\n"
            "    raise SystemExit(0)\n"
            "out = pathlib.Path(sys.argv[sys.argv.index('-o') + 1])\n"
            "out.write_text('time,I(IN),P(P),V(OUT)\\n0,0,0,0\\n1e-12,1,0.1,2\\n2e-12,0,0.2,0\\n', encoding='utf-8')\n",
            encoding="utf-8",
        )
        fake_solver.chmod(0o755)
        config = {
            "schema_version": "compact-quick-v2",
            "workflow_policy": "EVIDENCE_FIRST_V1",
            "id": "run-package-test",
            "mode": "QUICK",
            "question": "Does the default runner make an evidence package?",
            "hypothesis": "The runner stops after packaging.",
            "changed": "none",
            "scientific_review_authorization": "NOT_GRANTED",
            "frozen": ["synthetic deck", "synthetic solver output"],
            "deck": "inputs/main.cir",
            "run": {"solver": str(fake_solver), "args": []},
            "analysis": {"metrics": ["raw_qa", "waveform"], "signals": ["I(IN)", "P(P)", "V(OUT)"]},
            "visualization": {
                "mode": "compact",
                "style": "CLASSIC_LOCKED",
                "profile": "CLASSIC_LOCKED_COMPACT",
                "signals": ["I(IN)", "P(P)", "V(OUT)"],
            },
            "package": {"include_plots": False, "additional_paths": []},
        }
        (root / "experiment.yaml").write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
        with mock.patch.object(BVM_EXP, "_compact_compute_analysis", side_effect=AssertionError("scientific analyzer called")):
            self.assertEqual(BVM_EXP.compact_run(root), 0)
        result = yaml.safe_load((root / "runs" / "A001" / "result.yaml").read_text(encoding="utf-8"))
        self.assertEqual(result["status"], "AWAITING_SCIENTIFIC_REVIEW")
        self.assertEqual(result["outcome"], "EVIDENCE_READY")
        self.assertFalse(result["scientific_analysis_performed"])
        self.assertFalse((root / "analysis" / "scientific_review.json").exists())
        package = root / "handoff" / "run-package-test_raw_handoff.zip"
        self.assertTrue(package.is_file())
        qa = json.loads((root / "handoff" / "PACKAGE_QA.json").read_text(encoding="utf-8"))
        self.assertEqual(qa["status"], "PASS")
        self.assertFalse(qa["zip_committed"])
        with self.assertRaises(BVM_EXP.ConfigError):
            BVM_EXP.compact_run(root)


if __name__ == "__main__":
    unittest.main(verbosity=2)
