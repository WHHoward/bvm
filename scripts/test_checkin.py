#!/usr/bin/env python3
"""Unit tests for checkin task-state classification (stdlib only)."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest


SCRIPT_PATH = Path(__file__).with_name("checkin.py")
SPEC = importlib.util.spec_from_file_location("josim_checkin", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
CHECKIN = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECKIN)


TASK_ID = "JH-20260811-M4-002"


class CheckinStateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="josim-checkin-")
        self.root = Path(self.temporary.name)
        self.original_repo = CHECKIN.REPO
        self.original_worktrees = CHECKIN._worktree_paths
        self.original_verify = CHECKIN._verify_task
        CHECKIN.REPO = self.root
        CHECKIN._worktree_paths = lambda: []

    def tearDown(self) -> None:
        CHECKIN.REPO = self.original_repo
        CHECKIN._worktree_paths = self.original_worktrees
        CHECKIN._verify_task = self.original_verify
        self.temporary.cleanup()

    def _task_dir(self) -> Path:
        task_dir = self.root / "research" / "tasks" / TASK_ID
        task_dir.mkdir(parents=True)
        (task_dir / "request.yaml").write_text(
            "workflow_state: ISSUED\nobjective: \"unit test\"\n", encoding="utf-8"
        )
        (task_dir / "request.sha256").write_text("placeholder\n", encoding="utf-8")
        return task_dir

    def test_unconfirmed_standin_overrides_receipt_state(self) -> None:
        task_dir = self._task_dir()
        record = task_dir / "standin" / "S01" / "record.yaml"
        record.parent.mkdir(parents=True)
        record.write_text("status: PROVISIONAL\n", encoding="utf-8")
        receipt = task_dir / "attempts" / "A01" / "receipt.yaml"
        receipt.parent.mkdir(parents=True)
        receipt.write_text("receipt\n", encoding="utf-8")
        CHECKIN._verify_task = lambda _task: True

        self.assertIn("PROVISIONAL（阻断执行）", CHECKIN.open_tasks()[0])

    def test_verified_receipt_is_delivered_not_accepted(self) -> None:
        task_dir = self._task_dir()
        receipt = task_dir / "attempts" / "A01" / "receipt.yaml"
        receipt.parent.mkdir(parents=True)
        receipt.write_text("receipt\n", encoding="utf-8")
        CHECKIN._verify_task = lambda _task: True

        self.assertIn("DELIVERED（已验证，等审计）", CHECKIN.open_tasks()[0])

    def test_failed_validation_is_invalid(self) -> None:
        self._task_dir()
        CHECKIN._verify_task = lambda _task: False

        self.assertIn("INVALID（合同校验失败）", CHECKIN.open_tasks()[0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
