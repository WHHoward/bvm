from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

SERIES = Path(__file__).resolve().parents[1]
REPO = next(path for path in (SERIES, *SERIES.parents) if (path / ".git").exists())
sys.path.insert(0, str(SERIES / "scripts"))

import package  # noqa: E402
import submit  # noqa: E402
from config import USER_CASE_KEYS, load_env  # noqa: E402
from evidence import PackageMember, discover_batch_manifests, validate_complete_batch  # noqa: E402
from stimulus import load_stimulus  # noqa: E402


PAGES = (
    ("01_overview.html", "overview"), ("02_bvm.html", "bvm"),
    ("03_qb.html", "qb"), ("04_cb.html", "cb"),
    ("05_acc_gap.html", "acc_gap"),
)


def digest_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_json(path: Path, value: dict) -> bytes:
    data = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return data


def fixture_config(name: str, profile: str) -> tuple[dict[str, str], str, str, dict]:
    values = load_env(SERIES / "USER_CASE.env", USER_CASE_KEYS)
    values.update({"NAME": name, "ARRAY_SIZE": "1", "MASKS": "1", "QB_CB": "0",
                   "SJTL_COUNT": "0", "POST_SJTL_CB": "0", "PROBE_PROFILE": profile})
    user_text = "".join(f"{key}={values[key]}\n" for key in sorted(values))
    stimulus = load_stimulus(SERIES / "STIMULUS.env")
    stimulus_text = "".join(f"{key}={stimulus[key]}\n" for key in sorted(stimulus))
    return values, user_text, stimulus_text, stimulus


def make_run(series: Path, run_id: str, profile: str, user_text: str,
             stimulus_text: str, mask: str = "1") -> str:
    run = series / "runs" / run_id
    (run / "snapshot" / "sources").mkdir(parents=True)
    (run / "analysis").mkdir()
    (run / "plots").mkdir()
    (run / "PREFLIGHT.md").write_text("fixture preflight\n", encoding="utf-8")
    (run / "RESULT_BRIEF.md").write_text("fixture result\n", encoding="utf-8")
    (run / "USER_CASE.snapshot.env").write_text(user_text, encoding="utf-8")
    (run / "STIMULUS.snapshot.env").write_text(stimulus_text, encoding="utf-8")
    raw = b"time,V(FINAL_OUT)\n0,0\n1e-12,1e-6\n"
    (run / "raw.csv").write_bytes(raw)
    raw_sha = digest_bytes(raw)
    (run / "actual_deck.cir").write_text("* fixture deck\n.end\n", encoding="utf-8")
    (run / "stimulus.inc").write_text("* fixture stimulus\n", encoding="utf-8")
    write_json(run / "topology_manifest.json", {
        "schema": "fixture-topology", "array_size": 1, "mask": mask,
        "probe_profile": profile, "instances": [], "levels": [],
    })
    probe = {"schema": "fixture-probes", "profile": profile, "signal_count": 0, "signals": []}
    write_json(run / "probe_manifest.json", probe)
    parameter = {
        "bvm": {}, "qb": {}, "cb": {}, "sjtl": {}, "topology": {}, "solver": {},
        "acquisition": {"probe_profile": profile}, "stimulus_reference": {},
    }
    parameter_bytes = write_json(run / "parameter_manifest.json", parameter)
    sources = []
    for role, filename in (("BVM", "bvm_tunable.cir"), ("QB", "BQ_tunable.cir"),
                           ("CB", "CB_tunable.cir"), ("SJTL", "sJTL_tunable.cir")):
        relative = f"snapshot/sources/{filename}"
        snapshot_bytes = f"* {role} fixture snapshot\n".encode()
        (run / relative).write_bytes(snapshot_bytes)
        sources.append({"role": role, "rendered_snapshot_path": relative,
                        "rendered_snapshot_sha256": digest_bytes(snapshot_bytes)})
    source_bytes = write_json(run / "source_manifest.json", {"sources": sources})
    deck_sha = digest_bytes((run / "actual_deck.cir").read_bytes())
    stimulus_sha = digest_bytes((run / "stimulus.inc").read_bytes())
    topology_sha = digest_bytes((run / "topology_manifest.json").read_bytes())
    probe_sha = digest_bytes((run / "probe_manifest.json").read_bytes())
    parameter_sha = digest_bytes(parameter_bytes)
    source_sha = digest_bytes(source_bytes)
    provenance = {
        "physical_solve_count": 1,
        "probe_profile": profile,
        "raw": {"sha256": raw_sha},
        "actual_deck": {"sha256": deck_sha},
        "stimulus": {"sha256": stimulus_sha},
        "topology_manifest": {"sha256": topology_sha},
        "probe_manifest": {"sha256": probe_sha},
        "parameter_manifest": {"sha256": parameter_sha},
        "source_manifest": {"sha256": source_sha},
    }
    write_json(run / "provenance.json", provenance)
    plot_pages = []
    manifest_pages = []
    for filename, page_name in PAGES:
        relative = f"plots/{filename}"
        page_bytes = f"fixture html {filename}\n".encode()
        (run / relative).write_bytes(page_bytes)
        page_sha = digest_bytes(page_bytes)
        plot_pages.append({"path": relative, "sha256": page_sha, "status": "PASS"})
        manifest_pages.append({"file": filename, "page": page_name,
                               "time_range": "FULL_STORED_TIME_RANGE", "signals": []})
    write_json(run / "analysis" / "plot_manifest.json", {
        "raw_sha256": raw_sha, "pages": manifest_pages, "probe_profile": profile,
    })
    plot_qa = {
        "status": "PASS", "page_count": 5, "pages": plot_pages,
        "raw_sha256_before": raw_sha, "raw_sha256_after": raw_sha,
        "raw_immutable": True, "shared_asset_reference_pass": True,
        "full_stored_time_range": True,
    }
    write_json(run / "analysis" / "plot_qa.json", plot_qa)
    write_json(run / "analysis" / "raw_qa.json", {
        "status": "PASS", "sha256": raw_sha, "sha256_after_plot": raw_sha,
        "raw_immutable": True,
    })
    write_json(run / "analysis" / "mechanical_metrics.json", {"sample_count": 2})
    (run / "run.log").write_text("fixture log\n", encoding="utf-8")
    (run / "stdout.txt").write_text("fixture stdout\n", encoding="utf-8")
    (run / "stderr.txt").write_text("", encoding="utf-8")
    write_json(run / "result.json", {
        "run_id": run_id, "mask": mask, "solver_exit_code": 0,
        "artifact_status": "VALID", "physical_solve_count": 1,
        "raw_sha256": raw_sha, "plot_qa": {"status": "PASS"},
    })
    return raw_sha


def make_batch(series: Path, batch_id: str, *, status: str = "COMPLETE_MECHANICAL",
               profile: str = "core", run_id: str = "A001_T001_M1") -> tuple[Path, str]:
    values, user_text, stimulus_text, _ = fixture_config("fixture_case", profile)
    batch = series / "batches" / batch_id
    batch.mkdir(parents=True)
    (batch / "USER_CASE.effective.env").write_text(user_text, encoding="utf-8")
    (batch / "STIMULUS.effective.env").write_text(stimulus_text, encoding="utf-8")
    parameter = {
        "bvm": {}, "qb": {}, "cb": {}, "sjtl": {}, "topology": {}, "solver": {},
        "acquisition": {"probe_profile": profile}, "stimulus_reference": {},
    }
    parameter_bytes = write_json(batch / "parameter_manifest.json", parameter)
    raw_sha = make_run(series, run_id, profile, user_text, stimulus_text)
    manifest = {
        "schema": "fixture-batch", "batch_id": batch_id, "name": "fixture_case",
        "array_size": 1, "requested_masks": ["1"], "runs": [{
            "mask": "1", "run_id": run_id, "path": f"runs/{run_id}",
            "solver_exit": 0, "artifact_status": "VALID", "raw_sha256": raw_sha,
            "plot_qa": {"status": "PASS"}, "physical_solve_count": 1,
        }],
        "total_physical_solve_count": 1, "status": status,
        "probe_profile": profile,
        "effective_user_case_sha256": digest_bytes(user_text.encode()),
        "effective_stimulus_sha256": digest_bytes(stimulus_text.encode()),
        "parameter_manifest_sha256": digest_bytes(parameter_bytes),
    }
    write_json(batch / "batch_manifest.json", manifest)
    (batch / "BATCH_SUMMARY.md").write_text("fixture batch summary\n", encoding="utf-8")
    return batch, raw_sha


class EvidencePackageTests(unittest.TestCase):
    def test_manifest_selection_excludes_incomplete_unreferenced_and_html_by_default(self):
        with tempfile.TemporaryDirectory() as temp:
            series = Path(temp) / "series"
            series.mkdir()
            accepted, raw_sha = make_batch(series, "U001_accepted")
            make_batch(series, "U002_failed", status="SOLVER_FAILURE", run_id="A002_T001_M1")
            stray = series / "runs" / "A999_T999_M1"
            stray.mkdir(parents=True)
            (stray / "raw.csv").write_bytes(b"unreferenced\n")
            fixture = series / "tests" / "fixtures" / "rendered"
            fixture.mkdir(parents=True)
            (fixture / "actual_deck.cir").write_text("fixture-only\n", encoding="utf-8")

            with patch.object(package, "SERIES", series), \
                 patch.object(package, "SERIES_REL", "test/series"):
                default = package._select_batches("full", None, False)
                plotted = package._select_batches("full", None, True)

            default_members, batches, runs, excluded, _ = default
            paths = {member.archive_path for member in default_members}
            self.assertEqual([batch["batch_id"] for batch in batches], ["U001_accepted"])
            self.assertEqual([run["run_id"] for run in runs], ["A001_T001_M1"])
            self.assertEqual(raw_sha, json.loads((accepted / "batch_manifest.json").read_text())["runs"][0]["raw_sha256"])
            self.assertEqual(len(excluded), 1)
            self.assertIn("test/series/runs/A001_T001_M1/raw.csv", paths)
            self.assertFalse(any(path.endswith(".html") for path in paths))
            self.assertFalse(any("tests/fixtures" in path for path in paths))
            self.assertFalse(any("A999_T999_M1" in path for path in paths))
            plot_paths = {member.archive_path for member in plotted[0]}
            self.assertEqual(sum(path.endswith(".html") for path in plot_paths), 5)

    def test_full_plan_is_a_manifest_checkpoint_not_a_directory_snapshot(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            series = root / "test" / "series"
            series.mkdir(parents=True)
            mirror = root / "mirror"
            mirror.mkdir()
            make_batch(series, "U001_accepted")
            make_batch(series, "U002_failed", status="SOLVER_FAILURE", run_id="A002_T001_M1")
            stray = series / "runs" / "A999_T999_M1"
            stray.mkdir(parents=True)
            (stray / "raw.csv").write_bytes(b"unreferenced raw\n")
            fixtures = series / "tests" / "fixtures" / "rendered"
            fixtures.mkdir(parents=True)
            (fixtures / "actual_deck.cir").write_text("fixture only\n", encoding="utf-8")
            (series / "README.md").write_text("fixture README\n", encoding="utf-8")
            reproduction_plotter = root / "scripts" / "josim-plot2.py"
            reproduction_plotter.parent.mkdir()
            reproduction_plotter.write_text('vers = "fixture-plotter"\n', encoding="utf-8")
            reproduction_asset = root / "plotly.min.js"
            reproduction_asset.write_bytes(b"fixture plotly runtime\n")
            with patch.object(package, "REPO", root), \
                 patch.object(package, "SERIES", series), \
                 patch.object(package, "SERIES_REL", "test/series"), \
                 patch.object(package, "MIRROR", mirror), \
                 patch.object(package, "PLOTTER", reproduction_plotter), \
                 patch.object(package, "PLOTLY_ASSET", reproduction_asset), \
                 patch.object(package, "PLATFORM_PATHS", {"README.md"}), \
                 patch.object(package, "head_commit", return_value="fixture-head"), \
                 patch.object(package, "worktree_changes", return_value={}):
                plan = package.build_plan("full", "fixture-full")
                plot_plan = package.build_plan("full", "fixture-full-plots", include_plots=True)

            files = set(plan["manifest"]["included_files"])
            self.assertIn("test/series/runs/A001_T001_M1/raw.csv", files)
            self.assertIn("test/series/runs/A001_T001_M1/analysis/plot_manifest.json", files)
            self.assertIn("test/series/runs/A001_T001_M1/analysis/plot_qa.json", files)
            self.assertFalse(any("tests/fixtures/rendered" in member for member in files))
            self.assertFalse(any("A002_T001_M1" in member or "A999_T999_M1" in member
                                 for member in files))
            self.assertFalse(any(member.endswith(".html") for member in files))
            self.assertEqual(plan["manifest"]["selected_batches"][0]["batch_id"], "U001_accepted")
            self.assertEqual(plan["manifest"]["new_physical_solve_count"], 1)
            self.assertEqual(plan["manifest"]["reproduction_tools"][0]["version"], "fixture-plotter")
            self.assertIn("reproduction/scripts/josim-plot2.py", files)
            self.assertIn("reproduction/plotly.min.js", files)
            self.assertEqual(sum(item["file_count"] for item in plan["manifest"]["size_breakdown"].values()),
                             len(plan["members"]))
            self.assertEqual(sum(item["uncompressed_bytes"]
                                 for item in plan["manifest"]["size_breakdown"].values()),
                             plan["estimated_uncompressed_bytes"])
            self.assertEqual(sum(member.archive_path.endswith(".html")
                                 for member in plot_plan["members"]), 5)

    def test_delta_references_base_raw_without_copying_it(self):
        with tempfile.TemporaryDirectory() as temp:
            series = Path(temp) / "series"
            series.mkdir()
            _, raw_sha = make_batch(series, "U001_base")
            batch_dir = series / "batches" / "U002_reuse"
            batch_dir.mkdir(parents=True)
            values, user_text, stimulus_text, _ = fixture_config("fixture_case", "core")
            (batch_dir / "USER_CASE.effective.env").write_text(user_text, encoding="utf-8")
            (batch_dir / "STIMULUS.effective.env").write_text(stimulus_text, encoding="utf-8")
            parameter_bytes = write_json(batch_dir / "parameter_manifest.json", {
                "bvm": {}, "qb": {}, "cb": {}, "sjtl": {}, "topology": {}, "solver": {},
                "acquisition": {"probe_profile": "core"}, "stimulus_reference": {},
            })
            manifest = {
                "schema": "fixture-batch", "batch_id": "U002_reuse", "name": "fixture_case",
                "array_size": 1, "requested_masks": ["1"],
                "runs": [{"mask": "1", "run_id": "A002_T001_M1", "path": "runs/A001_T001_M1",
                          "solver_exit": 0, "artifact_status": "VALID", "physical_solve_count": 0,
                          "reused_existing_case": {"source_case": "A001_T001_M1",
                                                   "raw_path": "runs/A001_T001_M1/raw.csv",
                                                   "raw_sha256": raw_sha,
                                                   "source_package": "base.zip"}}],
                "total_physical_solve_count": 0, "status": "COMPLETE_MECHANICAL",
                "probe_profile": "core",
                "effective_user_case_sha256": digest_bytes(user_text.encode()),
                "effective_stimulus_sha256": digest_bytes(stimulus_text.encode()),
                "parameter_manifest_sha256": digest_bytes(parameter_bytes),
            }
            write_json(batch_dir / "batch_manifest.json", manifest)
            (batch_dir / "BATCH_SUMMARY.md").write_text("fixture reuse summary\n", encoding="utf-8")
            known = {
                "U001_base": {"manifest_sha256": digest_bytes((series / "batches/U001_base/batch_manifest.json").read_bytes())},
                "runs/A001_T001_M1/raw.csv": {"raw_sha256": raw_sha, "source_package": "base.zip"},
                "A001_T001_M1": {"raw_sha256": raw_sha, "source_package": "base.zip"},
            }
            with patch.object(package, "SERIES", series), \
                 patch.object(package, "SERIES_REL", "test/series"), \
                 patch.object(package, "_checkpoint_evidence", return_value=(
                     {"U001_base"}, known, {"U001_base": known["U001_base"]["manifest_sha256"]}
                 )):
                members, batches, runs, _, references = package._select_batches("delta", {"base_commit": "fixture"}, False)
            paths = {member.archive_path for member in members}
            self.assertEqual([batch["batch_id"] for batch in batches], ["U002_reuse"])
            self.assertEqual(runs[0]["reused"], True)
            self.assertEqual(references[0]["source_package"], "base.zip")
            self.assertFalse(any(path.endswith("/raw.csv") for path in paths))

    def test_package_zip_qa_records_sizes_crc_member_hashes_and_mirror_sha(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            series = root / "series"
            handoff = series / "handoff"
            mirror = root / "mirror"
            handoff.mkdir(parents=True)
            mirror.mkdir()
            (series / "analysis").mkdir()
            payload = series / "reproduction.txt"
            payload.write_bytes(b"reproduction fixture\n" * 4)
            member = PackageMember(payload, "series/reproduction.txt", "platform_reproduction_metadata")
            record = {"archive_path": member.archive_path, "category": member.category,
                      "bytes": payload.stat().st_size, "sha256": digest_bytes(payload.read_bytes())}
            manifest = {
                "included_file_sha256": {member.archive_path: record["sha256"]},
                "new_physical_solve_count": 0, "reused_point_count": 0,
                "referenced_existing_cases": [], "included_runs": [], "selected_batches": [],
                "size_breakdown": package._size_breakdown([record]),
            }
            plan = {
                "dirty_source_paths": [], "package_path": handoff / "fixture.zip",
                "mirror_path": mirror / "fixture.zip", "members": [member], "manifest": manifest,
                "manifest_path": "FULL_MANIFEST.json", "mode": "full", "head_commit": "fixture",
                "base": None, "include_plots": False,
            }
            with patch.object(package, "REPO", root), patch.object(package, "PACKAGE_QA", series / "analysis/PACKAGE_QA.json"):
                qa = package.create_package(plan)
            self.assertEqual(qa["status"], "PASS")
            self.assertTrue(qa["zip_crc_pass"])
            self.assertTrue(qa["member_sha256_pass"])
            self.assertGreater(qa["compressed_bytes"], 0)
            self.assertGreater(qa["uncompressed_bytes"], 0)
            self.assertGreater(qa["compression_ratio"], 0)
            self.assertLessEqual(qa["compression_ratio"], 1)
            self.assertEqual(qa["uncompressed_bytes"], payload.stat().st_size + len(
                (json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()))
            self.assertEqual(digest_bytes(plan["package_path"].read_bytes()), digest_bytes(plan["mirror_path"].read_bytes()))


if __name__ == "__main__":
    unittest.main(verbosity=2)
