from __future__ import annotations

import hashlib
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SERIES = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERIES / "scripts"))

import submit  # noqa: E402
import try_case  # noqa: E402
from config import USER_CASE_KEYS, load_env  # noqa: E402
from stimulus import load_stimulus  # noqa: E402


MASKS = ["00", "01", "10", "11"]


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")


def make_batch(root: Path, *, omit: str | None = None,
               plot_fail: str | None = None) -> Path:
    batch_id = "U001_test_batch"
    batch_dir = root / "batches" / batch_id
    user_values = load_env(SERIES / "USER_CASE.env", USER_CASE_KEYS)
    user_values.update({"NAME": "test_batch", "MASKS": ",".join(MASKS)})
    user_bytes = "".join(f"{key}={user_values[key]}\n" for key in sorted(user_values)).encode()
    stimulus_values = load_stimulus(SERIES / "STIMULUS.env")
    stimulus_bytes = "".join(f"{key}={stimulus_values[key]}\n" for key in sorted(stimulus_values)).encode()
    (batch_dir / "USER_CASE.effective.env").parent.mkdir(parents=True, exist_ok=True)
    (batch_dir / "USER_CASE.effective.env").write_bytes(user_bytes)
    (batch_dir / "STIMULUS.effective.env").write_bytes(stimulus_bytes)
    write_json(batch_dir / "parameter_manifest.json", {
        "bvm": {}, "qb": {}, "cb": {}, "sjtl": {}, "topology": {}, "solver": {},
        "stimulus_reference": {},
    })
    parameter_batch_sha = hashlib.sha256((batch_dir / "parameter_manifest.json").read_bytes()).hexdigest()
    rows = []
    for index, mask in enumerate(MASKS, 1):
        if mask == omit:
            continue
        run_id = f"A{index:03d}_T001_M{mask}"
        run_dir = root / "runs" / run_id
        run_dir.mkdir(parents=True)
        raw = f"synthetic raw fixture {mask}\n".encode()
        raw_sha = hashlib.sha256(raw).hexdigest()
        (run_dir / "raw.csv").write_bytes(raw)
        plot_status = "FAIL" if mask == plot_fail else "PASS"
        plot_pages = []
        for page_name in ("01_overview.html", "02_bvm.html", "03_qb.html",
                          "04_cb.html", "05_acc_gap.html"):
            page_path = run_dir / "plots" / page_name
            page_path.parent.mkdir(parents=True, exist_ok=True)
            page_bytes = f"fixture page {mask} {page_name}\n".encode()
            page_path.write_bytes(page_bytes)
            plot_pages.append({"path": f"plots/{page_name}",
                               "sha256": hashlib.sha256(page_bytes).hexdigest(),
                               "status": "PASS"})
        result = {
            "run_id": run_id, "mask": mask, "solver_exit_code": 0,
            "artifact_status": "VALID", "raw_sha256": raw_sha,
            "plot_qa": {"status": plot_status}, "physical_solve_count": 1,
        }
        write_json(run_dir / "result.json", result)
        write_json(run_dir / "analysis" / "plot_qa.json", {
            "status": plot_status, "page_count": 5, "pages": plot_pages,
            "raw_sha256_before": raw_sha, "raw_sha256_after": raw_sha,
            "raw_immutable": True, "shared_asset_reference_pass": True,
            "full_stored_time_range": True,
        })
        write_json(run_dir / "parameter_manifest.json", {"mask": mask})
        parameter_sha = hashlib.sha256((run_dir / "parameter_manifest.json").read_bytes()).hexdigest()
        write_json(run_dir / "provenance.json", {
            "physical_solve_count": 1, "raw": {"sha256": raw_sha},
            "parameter_manifest": {"sha256": parameter_sha},
        })
        rows.append({
            "mask": mask, "run_id": run_id, "path": f"runs/{run_id}",
            "solver_exit": 0, "artifact_status": "VALID", "raw_sha256": raw_sha,
            "plot_qa": {"status": plot_status}, "physical_solve_count": 1,
        })
    status = "COMPLETE_MECHANICAL" if len(rows) == len(MASKS) and plot_fail is None else "INCOMPLETE"
    manifest = {
        "schema": "bvm-qb-cb-array-batch-v1", "batch_id": batch_id,
        "name": "test_batch",
        "array_size": 2, "requested_masks": MASKS, "runs": rows,
        "effective_user_case_sha256": hashlib.sha256(user_bytes).hexdigest(),
        "effective_stimulus_sha256": hashlib.sha256(stimulus_bytes).hexdigest(),
        "parameter_manifest_sha256": parameter_batch_sha,
        "total_physical_solve_count": len(rows), "status": status,
    }
    write_json(batch_dir / "batch_manifest.json", manifest)
    write_json(root / "analysis" / "LATEST_BATCH.json", {
        "batch_id": batch_id, "path": f"batches/{batch_id}", "status": status,
    })
    return batch_dir


class BatchSubmitTests(unittest.TestCase):
    def test_missing_requested_mask_is_rejected_as_incomplete(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_batch(root, omit="10")
            with self.assertRaisesRegex(RuntimeError, r"BATCH_INCOMPLETE:.*mask 10"):
                submit.validate_batch(root)

    def test_complete_batch_passes_mechanical_preview_and_plot_failure_does_not_rerun(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_batch(root)
            with patch.object(submit.subprocess, "run", side_effect=AssertionError("JoSIM/process called")):
                runs, validation = submit.completed_runs(root)
            self.assertEqual(len(runs), 4)
            self.assertEqual(validation["status"], "COMPLETE_MECHANICAL")
            plan = submit.build_submission_plan(
                "B001-example", "full", [], {"head_commit": "fixture", "files": []},
                package_only=False, no_push=False, batch_validation=validation,
            )
            self.assertEqual(plan["status"], "SUBMIT_DRY_RUN_PASS")
            self.assertEqual(plan["batch_validation"]["total_physical_solve_count"], 4)

            package_plan = {
                "head_commit": "fixture-head", "base": None, "files": [],
                "package_path": SERIES / "handoff" / "preview-only.zip",
                "mirror_path": Path("/mnt/d/BVM_Backages/preview-only.zip"),
            }
            output = io.StringIO()
            with patch.object(submit, "SERIES", root), \
                 patch.object(submit, "staged_outside_series", return_value=[]), \
                 patch.object(submit, "series_changes", return_value=["batches/U001_test_batch/batch_manifest.json"]), \
                 patch.object(submit, "current_head", return_value="fixture-head"), \
                 patch.object(submit.package, "build_plan", return_value=package_plan), \
                 patch.object(submit.package, "create_package", side_effect=AssertionError("ZIP created")), \
                 contextlib.redirect_stdout(output):
                rc = submit.main(["B001-test", "--dry-run", "--mode", "full"])
            self.assertEqual(rc, 0)
            preview = json.loads(output.getvalue())
            self.assertEqual(preview["batch_validation"]["status"], "COMPLETE_MECHANICAL")
            self.assertFalse(preview["package_created"])

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_batch(root, plot_fail="01")
            with patch.object(submit.subprocess, "run", side_effect=AssertionError("JoSIM rerun")):
                with self.assertRaisesRegex(RuntimeError, r"BATCH_INCOMPLETE:.*mask 01: plot QA"):
                    submit.validate_batch(root)
                run_id = "A002_T001_M01"
                result_path = root / "runs" / run_id / "result.json"
                result = json.loads(result_path.read_text(encoding="utf-8"))
                result["plot_qa"] = {"status": "PASS"}
                write_json(result_path, result)
                qa_path = root / "runs" / run_id / "analysis" / "plot_qa.json"
                qa = json.loads(qa_path.read_text(encoding="utf-8"))
                qa["status"] = "PASS"
                write_json(qa_path, qa)
                self.assertEqual(
                    try_case.refresh_batch_for_run(root / "runs" / run_id, root),
                    "COMPLETE_MECHANICAL",
                )
                runs, batch = submit.validate_batch(root)
                self.assertEqual(len(runs), 4)
                self.assertEqual(batch["status"], "COMPLETE_MECHANICAL")


if __name__ == "__main__":
    unittest.main(verbosity=2)
