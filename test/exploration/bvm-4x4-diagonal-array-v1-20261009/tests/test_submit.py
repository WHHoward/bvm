from importlib.util import module_from_spec, spec_from_file_location
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


SERIES = Path(__file__).resolve().parents[1]
SCRIPT = SERIES / "scripts" / "submit.py"
SPEC = spec_from_file_location("bvm4x4_submit", SCRIPT)
submit = module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(submit)


class DeltaPackageTests(unittest.TestCase):
    def test_v9_run_evidence_closure_is_distinct_from_legacy_manual_runs(self):
        run_id = "A109_V9_A0_B0_80P68"
        with tempfile.TemporaryDirectory(prefix="bvm4x4-v9-submit-closure-") as temp:
            runs = Path(temp) / "runs"
            run_dir = runs / run_id
            run_dir.mkdir(parents=True)
            for name in submit.V9_MANUAL_RUN_REQUIRED_FILES:
                (run_dir / name).write_text("fixture-only\n", encoding="utf-8")
            with mock.patch.object(submit, "RUNS", runs):
                files, raw = submit._manual_run_file_set(run_id)
            self.assertEqual(raw, run_dir / "raw.csv")
            self.assertEqual({path.name for path in files}, submit.V9_MANUAL_RUN_REQUIRED_FILES)

    def test_delta_closure_adds_a017_to_a019_after_a013_to_a016_checkpoint(self):
        self.assertEqual(submit.DELTA_RUN_IDS, (
            "A017_PAPER_1101_1101", "A018_T1_ALL_QUIET", "A019_T1_ALL_PLUSE"))
        self.assertEqual(submit.PREVIOUS_DELTA_RUN_IDS, (
            "A013_T1_ALL_QUIET", "A014_T1_ALL_CLOCK",
            "A015_T1_PAPER_QUIET", "A016_T1_PAPER_CLOCK"))
        self.assertEqual(submit.DELTA_BASE_COMMIT, "684531519dda6e0a1e8ffec24d0711ee08adf6d1")
        self.assertEqual(submit.DELTA_BASE_PACKAGE_NAME, submit.T1_A013_A016_SOURCE_NAME)
        self.assertEqual(submit.INVALID_PRESERVED_DELTA_RUN_IDS, {"A017_PAPER_1101_1101"})

    def test_historical_raw_is_referenced_not_reincluded(self):
        a007_raw = f"test/exploration/{SERIES.name}/runs/A007_BUS400_D3_N0/raw.csv"
        a009_raw = f"test/exploration/{SERIES.name}/runs/A009_paper_like/raw.csv"
        a006_raw = f"test/exploration/{SERIES.name}/runs/A006_PAPER_1101_1101/raw.csv"
        a013_raw = f"test/exploration/{SERIES.name}/runs/A013_T1_ALL_QUIET/raw.csv"
        a017_raw = f"test/exploration/{SERIES.name}/runs/A017_PAPER_1101_1101/raw.csv"
        self.assertFalse(submit.is_allowed_delta_run_path(a007_raw))
        self.assertFalse(submit.is_allowed_delta_run_path(a009_raw))
        self.assertFalse(submit.is_allowed_delta_run_path(a006_raw))
        self.assertFalse(submit.is_allowed_delta_run_path(
            f"test/exploration/{SERIES.name}/runs/A010_PAPER_1101_1101/raw.csv"))
        self.assertFalse(submit.is_allowed_delta_run_path(a013_raw))
        self.assertTrue(submit.is_allowed_delta_run_path(a017_raw))
        self.assertTrue(submit.is_allowed_delta_run_path(
            f"test/exploration/{SERIES.name}/runs/A019_T1_ALL_PLUSE/raw.csv"))

    def test_new_run_sources_partition_from_shared_source_and_are_unique(self):
        sources = []
        shared = SERIES / "USER_CASE.env"
        sources.append((shared, shared.relative_to(submit.REPO).as_posix()))
        for run_id in submit.DELTA_RUN_IDS:
            for name in ("raw.csv", "result.json"):
                path = SERIES / "runs" / run_id / name
                sources.append((path, path.relative_to(submit.REPO).as_posix()))

        by_run, shared_sources = submit.partition_delta_sources(sources)

        self.assertEqual([member for _, member in shared_sources], [shared.relative_to(submit.REPO).as_posix()])
        self.assertEqual(set(by_run), set(submit.DELTA_RUN_IDS))
        for run_id, group in by_run.items():
            self.assertEqual({Path(member).name for _, member in group}, {"raw.csv", "result.json"})

    def test_post_prune_submit_sh_uses_retained_git_tree_without_legacy_zips(self):
        selected = {
            18: "A018_T1_ALL_QUIET", 19: "A019_T1_ALL_PLUSE",
            27: "A027_FULL_CB_CHAIN_ALL_CLOCK",
            30: "A030_CARRY_POST_CB_SJTL_ALL_200",
            31: "A031_CARRY_POST_CB_SJTL_ALL_210",
            32: "A032_CARRY_POST_CB_SJTL_PAPER_210",
            33: "A033_CARRY_POST_CB_SJTL_3X3_210",
            107: "A107_MANUAL_CARRY5_11x13_210",
            108: "A108_MANUAL_CARRY5_3x3_210",
        }
        with tempfile.TemporaryDirectory(prefix="bvm4x4-prune-submit-") as temp:
            sandbox = Path(temp) / "repo"
            series = sandbox / "test" / "exploration" / SERIES.name
            runs = series / "runs"
            handoff = series / "handoff"
            analysis = series / "analysis"
            (sandbox / "scripts").mkdir(parents=True)
            (series / "scripts").mkdir(parents=True)
            shutil.copy2(submit.REPO / ".gitignore", sandbox / ".gitignore")
            runs.mkdir(parents=True)
            handoff.mkdir()
            analysis.mkdir()
            mirror = Path(temp) / "mirror"
            mirror.mkdir()

            shutil.copy2(SERIES / "scripts" / "submit.py", series / "scripts" / "submit.py")
            shutil.copy2(SERIES / "submit.sh", series / "submit.sh")
            shutil.copy2(submit.REPO / "scripts" / "submit.py", sandbox / "scripts" / "submit.py")
            shutil.copy2(SERIES / "README.md", series / "README.md")
            checkpoint_source = SERIES / "analysis" / "MANUAL_RUN_DELTA_CHECKPOINTS.json"
            shutil.copy2(checkpoint_source, analysis / checkpoint_source.name)

            manifest = json.loads((SERIES / "experiment_manifest.json").read_text(encoding="utf-8"))
            for row in manifest["runs"]:
                run_number = int(row["run_id"][1:4])
                if run_number not in selected:
                    continue
                raw = f"temporary, non-physical packaging fixture: {row['run_id']}\n".encode()
                row["raw_sha256"] = hashlib.sha256(raw).hexdigest()
                row["raw_bytes"] = len(raw)
                raw_path = runs / row["run_id"] / "raw.csv"
                raw_path.parent.mkdir(parents=True)
                raw_path.write_bytes(raw)
            manifest_path = series / "experiment_manifest.json"
            manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

            subprocess.run(["git", "init", "-q", "-b", "master"], cwd=sandbox, check=True)
            subprocess.run(["git", "config", "user.name", "Prune Compatibility Test"], cwd=sandbox, check=True)
            subprocess.run(["git", "config", "user.email", "prune-test@example.invalid"], cwd=sandbox, check=True)
            subprocess.run(["git", "add", "--all"], cwd=sandbox, check=True)
            forced_fixture_paths = [
                (runs / run_id / "raw.csv").relative_to(sandbox).as_posix()
                for run_id in selected.values()
            ] + [(analysis / "MANUAL_RUN_DELTA_CHECKPOINTS.json").relative_to(sandbox).as_posix(),
                 manifest_path.relative_to(sandbox).as_posix()]
            subprocess.run(["git", "add", "-f", "--", *forced_fixture_paths], cwd=sandbox, check=True)
            subprocess.run(["git", "commit", "-q", "-m", "fixture: post-prune retained Git-tree baseline"],
                           cwd=sandbox, check=True)
            base_head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=sandbox, text=True,
                                       capture_output=True, check=True).stdout.strip()
            subprocess.run(["git", "remote", "add", "bvm", "https://example.invalid/WHHoward/bvm.git"],
                           cwd=sandbox, check=True)
            subprocess.run(["git", "update-ref", "refs/remotes/bvm/master", base_head],
                           cwd=sandbox, check=True)
            subprocess.run(["git", "config", "branch.master.remote", "bvm"], cwd=sandbox, check=True)
            subprocess.run(["git", "config", "branch.master.merge", "refs/heads/master"],
                           cwd=sandbox, check=True)

            def run_submit(*args: str) -> dict:
                completed = subprocess.run(
                    ["bash", str(series / "submit.sh"), *args, "--mirror-dir", str(mirror)],
                    cwd=series, text=True, capture_output=True, check=False)
                self.assertEqual(completed.returncode, 0,
                                 f"submit.sh failed\nstdout={completed.stdout}\nstderr={completed.stderr}")
                return json.loads(completed.stdout)

            def run_submit_raw(*args: str) -> subprocess.CompletedProcess:
                return subprocess.run(
                    ["bash", str(series / "submit.sh"), *args, "--mirror-dir", str(mirror)],
                    cwd=series, text=True, capture_output=True, check=False)

            def run_repo_submit(tag: str) -> dict:
                completed = subprocess.run(
                    [sys.executable, str(sandbox / "scripts" / "submit.py"), "--tag", tag,
                     "--scope", f"test/exploration/{SERIES.name}", "--dry-run",
                     "--mirror-dir", str(mirror)],
                    cwd=sandbox, text=True, capture_output=True, check=False)
                self.assertEqual(completed.returncode, 0,
                                 f"root submit dispatcher failed\nstdout={completed.stdout}\nstderr={completed.stderr}")
                return json.loads(completed.stdout)

            self.assertEqual(len(list(runs.iterdir())), 9)
            self.assertEqual(list(handoff.iterdir()), [])
            self.assertEqual(run_submit("NO_PENDING", "--dry-run")["status"], "NO_PENDING_RUNS")
            self.assertEqual(run_repo_submit("ROOT_NO_PENDING")["status"], "NO_PENDING_RUNS")
            tracking = run_submit("TRACK_RETAINED", "--track-packaged-raws", "--dry-run")
            self.assertEqual(tracking["status"], "RAW_ALREADY_TRACKED")
            self.assertEqual(tracking["checkpoint_raw_reference_count"], 9)
            retired_mode = run_submit_raw("A040_A041", "--d3-carry-timing", "--dry-run")
            self.assertEqual(retired_mode.returncode, 2)
            self.assertIn("legacy submit mode --d3-carry-timing is unavailable", retired_mode.stderr)

            run_id = "A109_POST_PRUNE"
            run_dir = runs / run_id
            run_dir.mkdir()
            raw = b"temporary, non-physical packaging fixture\ntime,value\n0,0\n"
            raw_sha = hashlib.sha256(raw).hexdigest()
            deck = b"* temporary submit fixture deck\n.end\n"
            deck_sha = hashlib.sha256(deck).hexdigest()
            (run_dir / "raw.csv").write_bytes(raw)
            (run_dir / "deck.cir").write_bytes(deck)
            (run_dir / "run.log").write_text("fixture only\n")
            (run_dir / "stdout.txt").write_text("")
            (run_dir / "stderr.txt").write_text("")
            for name in ("USER_CASE.snapshot.env", "STIMULUS.snapshot.env", "T1_PARAMS.snapshot.env",
                         "CBU_PARAMS.snapshot.env", "DFF_PARAMS.snapshot.env", "D0_JTL_PARAMS.snapshot.env",
                         "stimulus.inc", "RESULT_BRIEF.md"):
                (run_dir / name).write_text("fixture only\n")
            json_files = {
                "case_manifest.json": {"case": {"CASE": "POST_PRUNE"}},
                "provenance.json": {}, "source_manifest.json": {}, "topology_manifest.json": {},
                "probe_manifest.json": {}, "static_qa.json": {"status": "PASS"},
                "stimulus_manifest.json": {}, "metrics.json": {},
                "raw_qa.json": {"status": "PASS", "raw_sha256_before": raw_sha,
                                "raw_sha256_after_analysis": raw_sha},
                "qa.json": {"status": "PASS", "raw_sha256_before_analysis": raw_sha,
                            "raw_sha256_after_analysis": raw_sha},
                "chain_qa.json": {"status": "PASS"},
                "plot_manifest.json": {}, "plot_qa.json": {"status": "PASS", "pages": []},
                "metadata.json": {"solver": {"parent_head": base_head}},
                "result.json": {"run_id": run_id, "physical_solve_count": 1,
                                "solver_exit_code": 0, "artifact_status": "VALID",
                                "qa_status": "PASS", "raw_sha256": raw_sha,
                                "raw_bytes": len(raw), "deck_sha256": deck_sha},
            }
            for name, value in json_files.items():
                (run_dir / name).write_text(json.dumps(value) + "\n", encoding="utf-8")
            manifest["runs"].append({"run_id": run_id, "case": "POST_PRUNE", "batch_id": None,
                                     "physical_solve_count": 1, "raw_sha256": raw_sha,
                                     "deck_sha256": deck_sha})
            manifest["physical_solve_count"] = 109
            manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

            plan = run_repo_submit("POST_PRUNE")
            self.assertEqual(plan["status"], "DRY_RUN_PASS")
            self.assertEqual(plan["base_checkpoint_type"], "git_tree")
            self.assertEqual(plan["referenced_existing_raw_count"], 9)
            self.assertEqual(plan["new_run_ids"], [run_id])
            self.assertEqual(plan["solver_invocations_this_task"], 0)
            self.assertEqual(list(handoff.iterdir()), [])

            manifest["runs"][-1]["batch_id"] = "POST_PRUNE_REGISTERED_BATCH"
            manifest.setdefault("authorization_batches", []).append({
                "batch_id": "POST_PRUNE_REGISTERED_BATCH", "run_ids": [run_id],
                "authorized_physical_solve_count": 1,
            })
            manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
            registered_plan = run_repo_submit("POST_PRUNE_REGISTERED")
            self.assertEqual(registered_plan["status"], "DRY_RUN_PASS")
            self.assertEqual(registered_plan["registered_batch_ids"], ["POST_PRUNE_REGISTERED_BATCH"])
            self.assertEqual(registered_plan["new_run_ids"], [run_id])
            self.assertEqual(registered_plan["solver_invocations_this_task"], 0)
            self.assertEqual(list(handoff.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
