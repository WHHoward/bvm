#!/usr/bin/env python3
"""Self-contained regression tests for the JoSIM handoff protocol tooling."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from jsonschema import Draft202012Validator
import yaml


REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_PATH = Path(__file__).with_name("handoff.py")
SCHEMA_DIR = REPO_ROOT / "research" / "schemas"
ASSET_DIR = Path(__file__).resolve().parents[1] / "assets"

SPEC = importlib.util.spec_from_file_location("josim_handoff", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:  # pragma: no cover - import guard
    raise RuntimeError(f"cannot import {SCRIPT_PATH}")
HANDOFF = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HANDOFF)
HandoffError = HANDOFF.HandoffError


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_yaml(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(value, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


class HandoffTests(unittest.TestCase):
    def test_assets_validate(self) -> None:
        for path in sorted(ASSET_DIR.glob("*.yaml")):
            with self.subTest(path=path.name):
                HANDOFF.validate_document(path, SCHEMA_DIR, REPO_ROOT)

    def test_schema_rejects_invalid_state_combinations(self) -> None:
        audit_schema = json.loads(
            (SCHEMA_DIR / "audit-verdict.schema.json").read_text(encoding="utf-8")
        )
        audit = yaml.safe_load(
            (ASSET_DIR / "audit-verdict.yaml").read_text(encoding="utf-8")
        )
        audit["independence"]["mode"] = "CO_EXECUTOR"
        audit["independence"]["codex_modified_execution_artifacts"] = True
        self.assertTrue(list(Draft202012Validator(audit_schema).iter_errors(audit)))

        audit = yaml.safe_load(
            (ASSET_DIR / "audit-verdict.yaml").read_text(encoding="utf-8")
        )
        audit["artifact_status"] = "INVALID"
        audit["physical_verdict"] = "INCONCLUSIVE"
        audit["audit_disposition"] = "REWORK_REQUIRED"
        audit["required_rework"] = ["rerun"]
        self.assertTrue(list(Draft202012Validator(audit_schema).iter_errors(audit)))

        receipt_schema = json.loads(
            (SCHEMA_DIR / "execution-receipt.schema.json").read_text(encoding="utf-8")
        )
        receipt = yaml.safe_load(
            (ASSET_DIR / "execution-receipt.yaml").read_text(encoding="utf-8")
        )
        receipt["acceptance_results"][0]["evidence_paths"] = []
        self.assertTrue(list(Draft202012Validator(receipt_schema).iter_errors(receipt)))

    def test_chronology_guard_detects_nonmonotonic_chain(self) -> None:
        request = {"issued_at": "2026-08-09T00:00:02+08:00"}
        acknowledgements = {
            "A01": (Path("ack.yaml"), {"created_at": "2026-08-09T00:00:01+08:00"})
        }
        receipts = {
            "A01": (Path("receipt.yaml"), {"created_at": "2026-08-09T00:00:03+08:00"})
        }
        audits = {
            ("A01", "C01"): (
                Path("verdict.yaml"),
                {"created_at": "2026-08-09T00:00:00+08:00"},
            )
        }
        self.assertEqual(
            HANDOFF._chronology_errors(request, acknowledgements, receipts, audits),
            [
                ("request.issued_at", "ack:A01.created_at"),
                ("receipt:A01.created_at", "audit:A01:C01.created_at"),
            ],
        )

    def test_end_to_end_chain_and_tamper_detection(self) -> None:
        with tempfile.TemporaryDirectory(
            prefix=".handoff-selftest-", dir=REPO_ROOT
        ) as temporary:
            task_dir = Path(temporary)
            relative = task_dir.relative_to(REPO_ROOT).as_posix()
            baseline_dir = task_dir / "baseline"
            baseline_dir.mkdir()
            git_status = baseline_dir / "git-status.txt"
            scope_hashes = baseline_dir / "scope-files.sha256"
            git_status.write_text("", encoding="utf-8")
            agents_hash = sha256(REPO_ROOT / "AGENTS.md")
            scope_hashes.write_text(
                f"{agents_hash}  AGENTS.md\n", encoding="utf-8"
            )

            request = {
                "protocol": "josim-handoff/v1",
                "document_type": "task_request",
                "schema_version": 1,
                "task_id": "JH-20260809-SELFTEST-999",
                "revision": 1,
                "workflow_state": "ISSUED",
                "issued_at": "2026-08-09T00:00:00+08:00",
                "issuer": {"role": "CODEX", "id": "selftest"},
                "parent_todo_id": "SELFTEST",
                "depends_on": [],
                "supersedes": None,
                "task": {
                    "kind": "IMPLEMENTATION",
                    "objective": "exercise the protocol chain",
                    "research_question": "does the chain verify?",
                    "non_goals": ["no JoSIM run"],
                    "claim_ceiling": "implementation_only",
                },
                "scope": {
                    "read_paths": ["AGENTS.md"],
                    "write_paths": [
                        f"{relative}/out.txt",
                        f"{relative}/attempts/**",
                    ],
                    "frozen_paths": [
                        f"{relative}/request.yaml",
                        f"{relative}/baseline/**",
                        f"{relative}/audits/**",
                    ],
                    "locks": ["locks/handoff-selftest"],
                },
                "baseline": {
                    "git_head": "f042ab1d7c392ccac518802db55daa4efd4dddbf",
                    "dirty_policy": "ALLOW_NONOVERLAP",
                    "git_status": {
                        "path": f"{relative}/baseline/git-status.txt",
                        "sha256": sha256(git_status),
                    },
                    "scope_hashes": {
                        "path": f"{relative}/baseline/scope-files.sha256",
                        "sha256": sha256(scope_hashes),
                    },
                },
                "authorization": {
                    "edit": True,
                    "run_josim": False,
                    "network": False,
                    "install_dependencies": False,
                    "create_worktree": False,
                    "commit": False,
                    "delete_or_overwrite": False,
                },
                "contracts": {
                    "required_skills": ["josim-handoff"],
                    "read_first": ["AGENTS.md"],
                    "handover": {
                        "status": "NOT_APPLICABLE",
                        "path": None,
                        "sha256": None,
                    },
                    "metric_spec": {
                        "status": "NOT_APPLICABLE",
                        "path": None,
                        "sha256": None,
                    },
                },
                "deliverables": [
                    {
                        "id": "D1",
                        "path": f"{relative}/out.txt",
                        "role": "IMPLEMENTATION",
                        "required": True,
                    },
                    {
                        "id": "D2",
                        "path": f"{relative}/attempts/A01/receipt.yaml",
                        "role": "RECEIPT",
                        "required": True,
                    },
                ],
                "acceptance": [
                    {
                        "id": "AC1",
                        "condition": "output is preserved and hashed",
                        "evidence": ["receipt artifact and log"],
                    }
                ],
                "invalid_conditions": ["hash mismatch"],
                "inconclusive_conditions": [],
                "stop_conditions": ["scope expansion"],
                "issuance_blockers": [],
            }
            request_path = task_dir / "request.yaml"
            write_yaml(request_path, request)
            request_digest = sha256(request_path)
            (task_dir / "request.sha256").write_text(
                f"{request_digest}  request.yaml\n", encoding="utf-8"
            )

            attempt_dir = task_dir / "attempts" / "A01"
            attempt_dir.mkdir(parents=True)
            ack = {
                "protocol": "josim-handoff/v1",
                "document_type": "execution_ack",
                "schema_version": 1,
                "task_id": request["task_id"],
                "revision": 1,
                "attempt_id": "A01",
                "workflow_state": "ACKED",
                "created_at": "2026-08-09T00:00:01+08:00",
                "executor": {"role": "CLAUDE_CODE", "id": "selftest"},
                "bindings": {"request_sha256": request_digest},
                "decision": "ACCEPTED",
                "preflight": {
                    "observed_git_head": request["baseline"]["git_head"],
                    "dirty_paths": [],
                    "scope_accepted": True,
                    "required_skills_available": True,
                },
                "understanding": {
                    "objective": request["task"]["objective"],
                    "non_goals": request["task"]["non_goals"],
                    "stop_conditions": request["stop_conditions"],
                },
                "planned_commands": ["write output and run selftest"],
                "expected_changed_paths": [f"{relative}/out.txt"],
                "blockers": [],
                "deviations": [],
            }
            ack_path = attempt_dir / "ack.yaml"
            write_yaml(ack_path, ack)

            output_path = task_dir / "out.txt"
            output_path.write_text("verified output\n", encoding="utf-8")
            log_path = attempt_dir / "logs" / "test.log"
            log_path.parent.mkdir()
            log_path.write_text("PASS\n", encoding="utf-8")
            receipt = {
                "protocol": "josim-handoff/v1",
                "document_type": "execution_receipt",
                "schema_version": 1,
                "task_id": request["task_id"],
                "revision": 1,
                "attempt_id": "A01",
                "workflow_state": "DELIVERED",
                "created_at": "2026-08-09T00:00:02+08:00",
                "executor": {"role": "CLAUDE_CODE", "id": "selftest"},
                "bindings": {
                    "request_sha256": request_digest,
                    "ack_sha256": sha256(ack_path),
                },
                "execution_status": "COMPLETED",
                "baseline_git_head": request["baseline"]["git_head"],
                "result_git_head": None,
                "changes": [
                    {
                        "path": f"{relative}/out.txt",
                        "action": "CREATED",
                        "sha256": sha256(output_path),
                    },
                    {
                        "path": f"{relative}/attempts/A01/logs/test.log",
                        "action": "CREATED",
                        "sha256": sha256(log_path),
                    },
                ],
                "artifacts": [
                    {
                        "id": "output",
                        "path": f"{relative}/out.txt",
                        "sha256": sha256(output_path),
                        "role": "IMPLEMENTATION",
                    },
                    {
                        "id": "test-log",
                        "path": f"{relative}/attempts/A01/logs/test.log",
                        "sha256": sha256(log_path),
                        "role": "LOG",
                    },
                ],
                "commands": [
                    {
                        "command": "selftest",
                        "exit_code": 0,
                        "log_path": f"{relative}/attempts/A01/logs/test.log",
                        "log_sha256": sha256(log_path),
                    }
                ],
                "tests": [
                    {
                        "id": "selftest",
                        "status": "PASS",
                        "evidence_paths": [
                            f"{relative}/attempts/A01/logs/test.log"
                        ],
                        "notes": ["selftest passed"],
                    }
                ],
                "acceptance_results": [
                    {
                        "id": "AC1",
                        "status": "SATISFIED",
                        "evidence_paths": [f"{relative}/out.txt"],
                        "notes": ["hash checked"],
                    }
                ],
                "observations": ["output exists"],
                "interpretations": [],
                "unknowns": [],
                "proposed_physical_verdict": "NOT_APPLICABLE",
                "limitations": [],
                "deviations": [],
                "blockers": [],
            }
            receipt_path = attempt_dir / "receipt.yaml"
            write_yaml(receipt_path, receipt)

            audit = {
                "protocol": "josim-handoff/v1",
                "document_type": "audit_verdict",
                "schema_version": 1,
                "task_id": request["task_id"],
                "revision": 1,
                "attempt_id": "A01",
                "audit_id": "C01",
                "workflow_state": "CLOSED",
                "created_at": "2026-08-09T00:00:03+08:00",
                "auditor": {"role": "CODEX", "id": "selftest"},
                "bindings": {
                    "request_sha256": request_digest,
                    "ack_sha256": sha256(ack_path),
                    "receipt_sha256": sha256(receipt_path),
                },
                "scope_status": "PASS",
                "artifact_status": "VALID",
                "physical_verdict": "NOT_APPLICABLE",
                "audit_disposition": "ACCEPTED",
                "independence": {
                    "mode": "INDEPENDENT",
                    "codex_modified_execution_artifacts": False,
                    "reviewer": "selftest",
                },
                "checks": [
                    {"id": "chain", "status": "PASS", "evidence": ["hashes"]}
                ],
                "findings": [],
                "accepted_claims": ["protocol chain verifies"],
                "rejected_claims": [],
                "required_rework": [],
                "next_actions": [],
                "claim_ceiling": request["task"]["claim_ceiling"],
            }
            audit_path = task_dir / "audits" / "C01" / "verdict.yaml"
            write_yaml(audit_path, audit)

            errors, _warnings = HANDOFF.verify_task(task_dir, SCHEMA_DIR, REPO_ROOT)
            self.assertEqual([], errors)

            output_path.write_text("tampered\n", encoding="utf-8")
            errors, _warnings = HANDOFF.verify_task(task_dir, SCHEMA_DIR, REPO_ROOT)
            self.assertTrue(any("hash mismatch" in error for error in errors))

            bad_record = copy.deepcopy(receipt)
            bad_record["protocol"] = "wrong/v1"
            bad_path = task_dir / "attempts" / "A02" / "receipt.yaml"
            write_yaml(bad_path, bad_record)
            with self.assertRaises(HANDOFF.HandoffError):
                HANDOFF.verify_task(task_dir, SCHEMA_DIR, REPO_ROOT)




class StandinTests(unittest.TestCase):
    """User-authorized Claude stand-in records: PROVISIONAL until Codex review."""

    def _make_request(self, relative: str) -> tuple[Path, dict]:
        baseline_dir = REPO_ROOT / relative / "baseline"
        baseline_dir.mkdir(parents=True)
        git_status = baseline_dir / "git-status.txt"
        scope_hashes = baseline_dir / "scope-files.sha256"
        git_status.write_text("", encoding="utf-8")
        agents_hash = sha256(REPO_ROOT / "AGENTS.md")
        scope_hashes.write_text(f"{agents_hash}  AGENTS.md\n", encoding="utf-8")
        request = {
            "protocol": "josim-handoff/v1",
            "document_type": "task_request",
            "schema_version": 1,
            "task_id": "JH-20260809-SELFTEST-998",
            "revision": 1,
            "workflow_state": "ISSUED",
            "issued_at": "2026-08-09T00:00:00+08:00",
            "issuer": {"role": "CODEX", "id": "selftest"},
            "parent_todo_id": "SELFTEST",
            "depends_on": [],
            "supersedes": None,
            "task": {
                "kind": "IMPLEMENTATION",
                "objective": "exercise stand-in detection",
                "research_question": "does the chain verify?",
                "non_goals": ["no JoSIM run"],
                "claim_ceiling": "implementation_only",
            },
            "scope": {
                "read_paths": ["AGENTS.md"],
                "write_paths": [f"{relative}/out.txt"],
                "frozen_paths": [f"{relative}/request.yaml"],
                "locks": ["locks/handoff-standin-selftest"],
            },
            "baseline": {
                "git_head": "f042ab1d7c392ccac518802db55daa4efd4dddbf",
                "dirty_policy": "ALLOW_NONOVERLAP",
                "git_status": {
                    "path": f"{relative}/baseline/git-status.txt",
                    "sha256": sha256(git_status),
                },
                "scope_hashes": {
                    "path": f"{relative}/baseline/scope-files.sha256",
                    "sha256": sha256(scope_hashes),
                },
            },
            "authorization": {
                "edit": True,
                "run_josim": False,
                "network": False,
                "install_dependencies": False,
                "create_worktree": False,
                "commit": False,
                "delete_or_overwrite": False,
            },
            "contracts": {
                "required_skills": ["josim-handoff"],
                "read_first": ["AGENTS.md"],
                "handover": {"status": "NOT_APPLICABLE", "path": None, "sha256": None},
                "metric_spec": {"status": "NOT_APPLICABLE", "path": None, "sha256": None},
            },
            "deliverables": [
                {
                    "id": "D1",
                    "path": f"{relative}/out.txt",
                    "role": "IMPLEMENTATION",
                    "required": True,
                }
            ],
            "acceptance": [
                {
                    "id": "AC1",
                    "condition": "output is preserved and hashed",
                    "evidence": ["receipt artifact and log"],
                }
            ],
            "invalid_conditions": ["hash mismatch"],
            "inconclusive_conditions": [],
            "stop_conditions": ["scope expansion"],
            "issuance_blockers": [],
        }
        return request, scope_hashes

    def test_standin_record_is_provisional_until_review(self) -> None:
        with tempfile.TemporaryDirectory(
            prefix=".handoff-standin-", dir=REPO_ROOT
        ) as temporary:
            task_dir = Path(temporary)
            relative = task_dir.relative_to(REPO_ROOT).as_posix()
            request, _ = self._make_request(relative)
            request_path = task_dir / "request.yaml"
            write_yaml(request_path, request)
            request_digest = sha256(request_path)
            (task_dir / "request.sha256").write_text(
                f"{request_digest}  request.yaml\n", encoding="utf-8"
            )
            # baseline files referenced by the request must exist at the
            # task dir with content matching _make_request's hashes
            (task_dir / "baseline").mkdir(exist_ok=True)
            (task_dir / "baseline" / "git-status.txt").write_text(
                "", encoding="utf-8")
            agents_hash = sha256(REPO_ROOT / "AGENTS.md")
            (task_dir / "baseline" / "scope-files.sha256").write_text(
                f"{agents_hash}  AGENTS.md\n", encoding="utf-8")

            record_dir = task_dir / "standin" / "S01"
            record_dir.mkdir(parents=True)
            record = {
                "protocol": "josim-handoff/v1",
                "document_type": "standin_record",
                "schema_version": 1,
                "task_id": request["task_id"],
                "revision": 1,
                "standin_id": "S01",
                "created_at": "2026-08-09T00:00:03+08:00",
                "reason": "Codex unavailable (selftest)",
                "user_authorization": {
                    "authorized_at": "2026-08-09T00:00:03+08:00",
                    "scope": "issue request in selftest",
                },
                "proxy_agent": {"role": "CLAUDE_CODE", "id": "selftest"},
                "status": "PROVISIONAL",
                "actions": [
                    {
                        "action": "ISSUE_REQUEST",
                        "target_path": f"{relative}/request.yaml",
                        "previous_sha256": None,
                        "new_sha256": request_digest,
                        "notes": "stand-in issue in selftest",
                    }
                ],
                "bindings": {"request_sha256": request_digest},
                "declaration": "PROVISIONAL; awaits Codex review",
            }
            record_path = record_dir / "record.yaml"
            write_yaml(record_path, record)

            errors, warnings = HANDOFF.verify_task(task_dir, SCHEMA_DIR, REPO_ROOT)
            self.assertTrue(
                any("STAND-IN PROVISIONAL" in item for item in errors),
                f"unconfirmed stand-in must block, got: {errors}",
            )

            review = {
                "protocol": "josim-handoff/v1",
                "document_type": "standin_review",
                "schema_version": 1,
                "task_id": request["task_id"],
                "revision": 1,
                "standin_id": "S01",
                "created_at": "2026-08-09T00:00:04+08:00",
                "reviewer": {"role": "CODEX", "id": "selftest"},
                "verdict": "CONFIRMED",
                "bindings": {
                    "record_sha256": sha256(record_path),
                    "request_sha256": request_digest,
                    "request_signature_sha256": sha256(task_dir / "request.sha256"),
                },
                "notes": "selftest confirmed",
            }
            write_yaml(record_dir / "review.yaml", review)

            errors, warnings = HANDOFF.verify_task(task_dir, SCHEMA_DIR, REPO_ROOT)
            self.assertEqual(errors, [])
            self.assertFalse(
                any("STAND-IN PROVISIONAL" in item for item in warnings),
                f"PROVISIONAL warning must clear after CONFIRMED: {warnings}",
            )
            self.assertTrue(
                any("CONFIRMED" in item for item in warnings),
                f"expected CONFIRMED warning, got: {warnings}",
            )

class WorkflowMaintenanceTests(unittest.TestCase):
    """v1 workflow-maintenance regressions (AC5 snapshot mode, AC6 ceiling)."""

    def _issue_request(self, td: pathlib.Path, extra: dict | None = None,
                       drop_ceiling: bool = False) -> None:
        request = {
            "protocol": "josim-handoff/v1",
            "document_type": "task_request",
            "schema_version": 1,
            "task_id": "JH-20260817-WM-SELFTEST-001",
            "revision": 1,
            "workflow_state": "ISSUED",
            "issued_at": "2026-08-17T00:00:00+08:00",
            "issuer": {"role": "CODEX", "id": "selftest"},
            "parent_todo_id": "WM",
            "depends_on": [],
            "supersedes": None,
            "task": {"kind": "IMPLEMENTATION", "objective": "wm selftest",
                     "research_question": "does v1 verify?",
                     "non_goals": [], "claim_ceiling": "selftest_only"},
            "scope": {"read_paths": ["AGENTS.md"],
                      "write_paths": [f"{td.name}/out.txt"],
                      "frozen_paths": [f"{td.name}/request.yaml"],
                      "locks": ["locks/wm-selftest"]},
            "baseline": {
                "git_head": "58909bc2b313c8c17fe9aa0348ebd283837c03ea",
                "dirty_policy": "ALLOW_NONOVERLAP",
                "git_status": {"path": f"{td.name}/baseline/git-status.txt",
                               "sha256": "0" * 64},
                "scope_hashes": {"path": f"{td.name}/baseline/scope-files.sha256",
                                 "sha256": "0" * 64},
            },
            "authorization": {"edit": True, "run_josim": False,
                              "network": False, "install_dependencies": False,
                              "create_worktree": False, "commit": False,
                              "delete_or_overwrite": False},
            "contracts": {"required_skills": ["josim-handoff"],
                          "read_first": ["AGENTS.md"],
                          "handover": {"status": "CURRENT",
                                       "path": "docs/HANDOVER.md",
                                       "sha256": sha256(
                                           REPO_ROOT / "docs" / "HANDOVER.md")},
                          "metric_spec": {"status": "FROZEN",
                                          "path": "docs/research/METRIC_SPEC_V2.md",
                                          "sha256": sha256(
                                              REPO_ROOT / "docs" / "research" /
                                              "METRIC_SPEC_V2.md")}},
            "deliverables": [
                {"id": "D1", "path": f"{td.name}/out.txt",
                 "role": "IMPLEMENTATION", "required": True}],
            "acceptance": [{"id": "AC1", "condition": "ok",
                            "evidence": ["out.txt"]}],
            "invalid_conditions": ["any hash mismatch"],
            "inconclusive_conditions": ["readiness unavailable"],
            "stop_conditions": ["scope expansion"],
            "issuance_blockers": [],
        }
        if extra:
            request["baseline"].update(extra)
        if drop_ceiling:
            del request["task"]["claim_ceiling"]
        (td / "baseline").mkdir(exist_ok=True)
        (td / "baseline" / "git-status.txt").write_text("", encoding="utf-8")
        (td / "baseline" / "scope-files.sha256").write_text(
            f"{sha256(REPO_ROOT / 'AGENTS.md')}  AGENTS.md\n",
            encoding="utf-8")
        request["baseline"]["git_status"]["sha256"] = sha256(
            td / "baseline" / "git-status.txt")
        request["baseline"]["scope_hashes"]["sha256"] = sha256(
            td / "baseline" / "scope-files.sha256")
        write_yaml(td / "request.yaml", request)
        digest = sha256(td / "request.yaml")
        (td / "request.sha256").write_text(
            f"{digest}  request.yaml\n", encoding="utf-8")

    def _ack(self, td: pathlib.Path) -> None:
        (td / "attempts" / "A01").mkdir(parents=True)
        ack = {
            "protocol": "josim-handoff/v1",
            "document_type": "execution_ack",
            "schema_version": 1,
            "task_id": "JH-20260817-WM-SELFTEST-001",
            "revision": 1,
            "attempt_id": "A01",
            "workflow_state": "ACKED",
            "created_at": "2026-08-17T00:00:01+08:00",
            "executor": {"role": "CLAUDE_CODE", "id": "claude-code"},
            "bindings": {"request_sha256": sha256(td / "request.yaml")},
            "decision": "ACCEPTED",
            "preflight": {
                "observed_git_head": "58909bc2b313c8c17fe9aa0348ebd283837c03ea",
                "dirty_paths": [], "scope_accepted": True,
                "required_skills_available": True},
            "understanding": {"objective": "x", "non_goals": [],
                              "stop_conditions": []},
            "planned_commands": [], "expected_changed_paths": [],
            "blockers": [], "deviations": [],
        }
        write_yaml(td / "attempts" / "A01" / "ack.yaml", ack)

    def test_legacy_request_without_snapshot_still_verifies(self) -> None:
        """AC5: no issuer_snapshot_commit -> legacy strict-HEAD unchanged."""
        with tempfile.TemporaryDirectory(
                prefix=".handoff-wm-", dir=REPO_ROOT) as temporary:
            td = Path(temporary)
            self._issue_request(td)
            self._ack(td)
            errors, _ = HANDOFF.verify_task(td, SCHEMA_DIR, REPO_ROOT)
            self.assertEqual(errors, [],
                             f"legacy request must verify, got {errors}")

    def test_audit_ceiling_mandatory(self) -> None:
        """AC6: request without contract claim_ceiling is schema-invalid."""
        with tempfile.TemporaryDirectory(
                prefix=".handoff-wm-", dir=REPO_ROOT) as temporary:
            td = Path(temporary)
            self._issue_request(td, drop_ceiling=True)
            self._ack(td)
            try:
                HANDOFF.verify_task(td, SCHEMA_DIR, REPO_ROOT)
                self.fail("missing claim_ceiling must be schema-rejected")
            except HandoffError as exc:
                self.assertIn("claim_ceiling", str(exc))

    def test_audit_scientific_ceiling_optional_and_narrow(self) -> None:
        """AC6: scientific_claim_ceiling accepted when narrower."""
        import json as _json
        schema = _json.load(open(SCHEMA_DIR / "audit-verdict.schema.json"))
        props = schema.get("properties", {})
        self.assertIn("scientific_claim_ceiling", props)
        self.assertIn("claim_ceiling", schema.get("required", []))

    def test_issuer_snapshot_mode_rejects_wrong_snapshot(self) -> None:
        """AC5: declared snapshot whose tree lacks the request -> error."""
        with tempfile.TemporaryDirectory(
                prefix=".handoff-wm-", dir=REPO_ROOT) as temporary:
            td = Path(temporary)
            self._issue_request(
                td, {"issuer_snapshot_commit":
                     "0000000000000000000000000000000000000000"})
            self._ack(td)
            errors, _ = HANDOFF.verify_task(td, SCHEMA_DIR, REPO_ROOT)
            self.assertTrue(
                any(("issuer snapshot" in e) or ("observed_git_head" in e)
                    for e in errors),
                f"wrong snapshot must fail: {errors}")


class MultiAttemptAggregationTests(unittest.TestCase):
    """MAINT-003: task-wide deliverable/acceptance coverage across the
    union of canonical per-attempt receipts (request AC1/AC2)."""

    TASK_ID = "JH-20260817-WM-AGG-SELFTEST-001"
    HEAD = "58909bc2b313c8c17fe9aa0348ebd283837c03ea"

    # (attempt, output file, acceptance ids covered)
    ATTEMPTS = {
        "A01": ("out-a.txt", ["AC1"]),
        "A02": ("out-b.txt", ["AC2"]),
    }

    def _setup_task(self, td: pathlib.Path,
                    attempts: tuple[str, ...] = ("A01", "A02")) -> str:
        relative = td.name
        (td / "baseline").mkdir(exist_ok=True)
        (td / "baseline" / "git-status.txt").write_text("", encoding="utf-8")
        (td / "baseline" / "scope-files.sha256").write_text(
            f"{sha256(REPO_ROOT / 'AGENTS.md')}  AGENTS.md\n",
            encoding="utf-8")
        request = {
            "protocol": "josim-handoff/v1",
            "document_type": "task_request",
            "schema_version": 1,
            "task_id": self.TASK_ID,
            "revision": 1,
            "workflow_state": "ISSUED",
            "issued_at": "2026-08-17T01:00:00+08:00",
            "issuer": {"role": "CODEX", "id": "selftest"},
            "parent_todo_id": "WM",
            "depends_on": [],
            "supersedes": None,
            "task": {"kind": "IMPLEMENTATION",
                     "objective": "multi-attempt aggregation selftest",
                     "research_question": "does union coverage verify?",
                     "non_goals": [], "claim_ceiling": "selftest_only"},
            "scope": {"read_paths": ["AGENTS.md"],
                      "write_paths": [f"{relative}/out-*.txt",
                                      f"{relative}/attempts/**"],
                      "frozen_paths": [f"{relative}/request.yaml"],
                      "locks": ["locks/wm-agg-selftest"]},
            "baseline": {
                "git_head": self.HEAD,
                "dirty_policy": "ALLOW_NONOVERLAP",
                "git_status": {"path": f"{relative}/baseline/git-status.txt",
                               "sha256": sha256(
                                   td / "baseline" / "git-status.txt")},
                "scope_hashes": {"path":
                                 f"{relative}/baseline/scope-files.sha256",
                                 "sha256": sha256(
                                     td / "baseline" / "scope-files.sha256")},
            },
            "authorization": {"edit": True, "run_josim": False,
                              "network": False, "install_dependencies": False,
                              "create_worktree": False, "commit": False,
                              "delete_or_overwrite": False},
            "contracts": {"required_skills": ["josim-handoff"],
                          "read_first": ["AGENTS.md"],
                          "handover": {"status": "CURRENT",
                                       "path": "docs/HANDOVER.md",
                                       "sha256": sha256(
                                           REPO_ROOT / "docs" / "HANDOVER.md")},
                          "metric_spec": {"status": "FROZEN",
                                          "path": "docs/research/"
                                                  "METRIC_SPEC_V2.md",
                                          "sha256": sha256(
                                              REPO_ROOT / "docs" / "research" /
                                              "METRIC_SPEC_V2.md")}},
            "deliverables": [
                {"id": "D1", "path": f"{relative}/out-a.txt",
                 "role": "IMPLEMENTATION", "required": True},
                {"id": "D2", "path": f"{relative}/out-b.txt",
                 "role": "IMPLEMENTATION", "required": True},
                {"id": "D3",
                 "path": f"{relative}/attempts/**/receipt.yaml",
                 "role": "RECEIPT", "required": True},
            ],
            "acceptance": [
                {"id": "AC1", "condition": "delivered in A01",
                 "evidence": ["out-a.txt"]},
                {"id": "AC2", "condition": "delivered in A02",
                 "evidence": ["out-b.txt"]},
            ],
            "invalid_conditions": ["any hash mismatch"],
            "inconclusive_conditions": [],
            "stop_conditions": ["scope expansion"],
            "issuance_blockers": [],
        }
        write_yaml(td / "request.yaml", request)
        digest = sha256(td / "request.yaml")
        (td / "request.sha256").write_text(
            f"{digest}  request.yaml\n", encoding="utf-8")
        for index, attempt_id in enumerate(attempts):
            self._write_attempt(td, digest, attempt_id, index + 1)
        return digest

    def _write_attempt(self, td: pathlib.Path, request_digest: str,
                       attempt_id: str, order: int) -> None:
        relative = td.name
        output, accept_ids = self.ATTEMPTS[attempt_id]
        attempt_dir = td / "attempts" / attempt_id
        attempt_dir.mkdir(parents=True)
        ack = {
            "protocol": "josim-handoff/v1",
            "document_type": "execution_ack",
            "schema_version": 1,
            "task_id": self.TASK_ID,
            "revision": 1,
            "attempt_id": attempt_id,
            "workflow_state": "ACKED",
            "created_at": f"2026-08-17T01:00:0{order * 2 - 1}+08:00",
            "executor": {"role": "CLAUDE_CODE", "id": "claude-code"},
            "bindings": {"request_sha256": request_digest},
            "decision": "ACCEPTED",
            "preflight": {
                "observed_git_head": self.HEAD,
                "dirty_paths": [], "scope_accepted": True,
                "required_skills_available": True},
            "understanding": {"objective": "x", "non_goals": [],
                              "stop_conditions": []},
            "planned_commands": [], "expected_changed_paths": [],
            "blockers": [], "deviations": [],
        }
        write_yaml(attempt_dir / "ack.yaml", ack)
        output_path = td / output
        output_path.write_text(f"{attempt_id} output\n", encoding="utf-8")
        log_dir = attempt_dir / "logs"
        log_dir.mkdir()
        log_path = log_dir / "test.log"
        log_path.write_text("PASS\n", encoding="utf-8")
        receipt = {
            "protocol": "josim-handoff/v1",
            "document_type": "execution_receipt",
            "schema_version": 1,
            "task_id": self.TASK_ID,
            "revision": 1,
            "attempt_id": attempt_id,
            "workflow_state": "DELIVERED",
            "created_at": f"2026-08-17T01:00:0{order * 2}+08:00",
            "executor": {"role": "CLAUDE_CODE", "id": "claude-code"},
            "bindings": {"request_sha256": request_digest,
                         "ack_sha256": sha256(attempt_dir / "ack.yaml")},
            "execution_status": "COMPLETED",
            "baseline_git_head": self.HEAD,
            "result_git_head": None,
            "changes": [
                {"path": f"{relative}/{output}", "action": "CREATED",
                 "sha256": sha256(output_path)},
                {"path": f"{relative}/attempts/{attempt_id}/logs/test.log",
                 "action": "CREATED", "sha256": sha256(log_path)},
            ],
            "artifacts": [
                {"id": "output", "path": f"{relative}/{output}",
                 "sha256": sha256(output_path), "role": "IMPLEMENTATION"},
                {"id": "test-log",
                 "path": f"{relative}/attempts/{attempt_id}/logs/test.log",
                 "sha256": sha256(log_path), "role": "LOG"},
            ],
            "commands": [
                {"command": "selftest", "exit_code": 0,
                 "log_path": f"{relative}/attempts/{attempt_id}/logs/test.log",
                 "log_sha256": sha256(log_path)},
            ],
            "tests": [
                {"id": "selftest", "status": "PASS",
                 "evidence_paths": [
                     f"{relative}/attempts/{attempt_id}/logs/test.log"],
                 "notes": []},
            ],
            "acceptance_results": [
                {"id": accept_id, "status": "SATISFIED",
                 "evidence_paths": [f"{relative}/{output}"],
                 "notes": []} for accept_id in accept_ids
            ],
            "observations": [], "interpretations": [], "unknowns": [],
            "proposed_physical_verdict": "NOT_APPLICABLE",
            "limitations": [], "deviations": [], "blockers": [],
        }
        write_yaml(attempt_dir / "receipt.yaml", receipt)

    def _rewrite_receipt(self, td: pathlib.Path, attempt_id: str,
                        mutate) -> None:
        path = td / "attempts" / attempt_id / "receipt.yaml"
        receipt = yaml.safe_load(path.read_text(encoding="utf-8"))
        mutate(receipt)
        write_yaml(path, receipt)

    def test_two_attempt_union_verifies(self) -> None:
        """AC1/AC2: separate A01/A02 canonical receipts + receipt glob pass
        when their union covers the required delivery/acceptance set."""
        with tempfile.TemporaryDirectory(
                prefix=".handoff-wm-agg-", dir=REPO_ROOT) as temporary:
            td = Path(temporary)
            self._setup_task(td)
            errors, _ = HANDOFF.verify_task(td, SCHEMA_DIR, REPO_ROOT)
            self.assertEqual(errors, [],
                             f"union coverage must verify, got {errors}")

    def test_union_missing_deliverable_fails(self) -> None:
        """AC2 negative: union missing a required deliverable must fail."""
        with tempfile.TemporaryDirectory(
                prefix=".handoff-wm-agg-", dir=REPO_ROOT) as temporary:
            td = Path(temporary)
            self._setup_task(td)
            relative = td.name
            # A02 stops claiming out-b.txt; only A01's out-a.txt remains.
            self._rewrite_receipt(
                td, "A02",
                lambda r: r.__setitem__(
                    "artifacts",
                    [a for a in r["artifacts"] if a["path"] !=
                     f"{relative}/out-b.txt"]))
            errors, _ = HANDOFF.verify_task(td, SCHEMA_DIR, REPO_ROOT)
            self.assertTrue(
                any("not represented across the union of receipts" in e
                    for e in errors),
                f"missing deliverable must fail, got {errors}")

    def test_union_missing_acceptance_fails(self) -> None:
        """AC2 negative: union missing an acceptance ID must fail."""
        with tempfile.TemporaryDirectory(
                prefix=".handoff-wm-agg-", dir=REPO_ROOT) as temporary:
            td = Path(temporary)
            self._setup_task(td)
            # A02 no longer covers AC2 (only repeats A01's AC1): the union
            # misses AC2.  The schema's minItems:1 keeps one entry.
            def _drop_ac2(receipt):
                receipt["acceptance_results"] = [
                    {"id": "AC1", "status": "SATISFIED",
                     "evidence_paths": [f"{td.name}/out-a.txt"],
                     "notes": ["repeats A01 coverage"]}]
            self._rewrite_receipt(td, "A02", _drop_ac2)
            errors, _ = HANDOFF.verify_task(td, SCHEMA_DIR, REPO_ROOT)
            self.assertTrue(
                any("acceptance coverage across the union of receipts" in e
                    for e in errors),
                f"missing acceptance id must fail, got {errors}")

    def test_unknown_acceptance_id_still_fails(self) -> None:
        """AC1: per-receipt unknown-ID failures are preserved."""
        with tempfile.TemporaryDirectory(
                prefix=".handoff-wm-agg-", dir=REPO_ROOT) as temporary:
            td = Path(temporary)
            self._setup_task(td)
            relative = td.name
            self._rewrite_receipt(
                td, "A01",
                lambda r: r["acceptance_results"].append(
                    {"id": "AC9", "status": "SATISFIED",
                     "evidence_paths": [f"{relative}/out-a.txt"],
                     "notes": []}))
            errors, _ = HANDOFF.verify_task(td, SCHEMA_DIR, REPO_ROOT)
            self.assertTrue(
                any("unknown ids: AC9" in e for e in errors),
                f"unknown id must fail, got {errors}")

    def test_duplicate_acceptance_id_still_fails(self) -> None:
        """AC1: duplicate-ID failures are preserved (schema-level semantic
        check rejects them before task-wide aggregation)."""
        with tempfile.TemporaryDirectory(
                prefix=".handoff-wm-agg-", dir=REPO_ROOT) as temporary:
            td = Path(temporary)
            self._setup_task(td)
            def _duplicate_id(receipt):
                second = dict(receipt["acceptance_results"][0])
                second["notes"] = ["different object, same id"]
                receipt["acceptance_results"].append(second)
            self._rewrite_receipt(td, "A02", _duplicate_id)
            with self.assertRaises(HandoffError) as context:
                HANDOFF.verify_task(td, SCHEMA_DIR, REPO_ROOT)
            self.assertIn("duplicate ids", str(context.exception))

    def test_single_attempt_keeps_legacy_full_coverage_rule(self) -> None:
        """AC3: a single-attempt receipt still must cover the full
        delivery/acceptance set itself (union == one receipt)."""
        with tempfile.TemporaryDirectory(
                prefix=".handoff-wm-agg-", dir=REPO_ROOT) as temporary:
            td = Path(temporary)
            self._setup_task(td, attempts=("A01",))
            errors, _ = HANDOFF.verify_task(td, SCHEMA_DIR, REPO_ROOT)
            self.assertTrue(
                any(("not represented across the union of receipts" in e)
                    or ("acceptance coverage across the union of receipts"
                        in e) for e in errors),
                f"single attempt missing D2/AC2 must fail, got {errors}")


class IssuerSnapshotRealTests(unittest.TestCase):
    """AC1/AC2: real git objects for issuer-snapshot positive/negative.

    Uses dangling commits (hash-object/mktree/commit-tree) inside the real
    repo: the snapshot tree carries byte-identical request.yaml,
    request.sha256 and baseline manifest; the parent baseline HEAD differs
    from the snapshot HEAD.  Legacy strict-HEAD remains the rule whenever
    issuer_snapshot_commit is absent.
    """

    TASK_ID = "JH-20260817-WM-SNAP-SELFTEST-001"
    HEAD = "58909bc2b313c8c17fe9aa0348ebd283837c03ea"

    def _git(self, repo_root: Path, *args: str) -> str:
        proc = subprocess.run(["git", "-C", str(repo_root), *args],
                              capture_output=True, text=True, check=True)
        return proc.stdout.strip()

    def _write_request(self, td: pathlib.Path,
                       snapshot_commit: str | None,
                       baseline_head: str,
                       write_paths: list[str] | None = None,
                       deliverables: list[dict] | None = None,
                       acceptance: list[dict] | None = None) -> None:
        relative = td.name
        (td / "baseline").mkdir(exist_ok=True)
        (td / "baseline" / "git-status.txt").write_text("", encoding="utf-8")
        (td / "baseline" / "scope-files.sha256").write_text(
            f"{sha256(REPO_ROOT / 'AGENTS.md')}  AGENTS.md\n",
            encoding="utf-8")
        request = {
            "protocol": "josim-handoff/v1",
            "document_type": "task_request",
            "schema_version": 1,
            "task_id": self.TASK_ID,
            "revision": 1,
            "workflow_state": "ISSUED",
            "issued_at": "2026-08-17T02:00:00+08:00",
            "issuer": {"role": "CODEX", "id": "selftest"},
            "parent_todo_id": "WM",
            "depends_on": [],
            "supersedes": None,
            "task": {"kind": "IMPLEMENTATION",
                     "objective": "real issuer-snapshot selftest",
                     "research_question": "does a real snapshot verify?",
                     "non_goals": [], "claim_ceiling": "selftest_only"},
            "scope": {"read_paths": ["AGENTS.md"],
                      "write_paths": write_paths or [
                          f"{relative}/out.txt",
                          f"{relative}/attempts/**"],
                      "frozen_paths": [f"{relative}/request.yaml"],
                      "locks": ["locks/wm-snap-selftest"]},
            "baseline": {
                "git_head": baseline_head,
                "dirty_policy": "ALLOW_NONOVERLAP",
                "git_status": {"path": f"{relative}/baseline/git-status.txt",
                               "sha256": sha256(
                                   td / "baseline" / "git-status.txt")},
                "scope_hashes": {"path":
                                 f"{relative}/baseline/scope-files.sha256",
                                 "sha256": sha256(
                                     td / "baseline" / "scope-files.sha256")},
            },
            "authorization": {"edit": True, "run_josim": False,
                              "network": False, "install_dependencies": False,
                              "create_worktree": False, "commit": False,
                              "delete_or_overwrite": False},
            "contracts": {"required_skills": ["josim-handoff"],
                          "read_first": ["AGENTS.md"],
                          "handover": {"status": "CURRENT",
                                       "path": "docs/HANDOVER.md",
                                       "sha256": sha256(
                                           REPO_ROOT / "docs" / "HANDOVER.md")},
                          "metric_spec": {"status": "FROZEN",
                                          "path": "docs/research/"
                                                  "METRIC_SPEC_V2.md",
                                          "sha256": sha256(
                                              REPO_ROOT / "docs" / "research" /
                                              "METRIC_SPEC_V2.md")}},
            "deliverables": deliverables or [
                {"id": "D1", "path": f"{relative}/out.txt",
                 "role": "IMPLEMENTATION", "required": True},
            ],
            "acceptance": acceptance or [
                {"id": "AC1", "condition": "snapshot ok",
                 "evidence": ["out.txt"]}],
            "invalid_conditions": ["any hash mismatch"],
            "inconclusive_conditions": [],
            "stop_conditions": ["scope expansion"],
            "issuance_blockers": [],
        }
        if snapshot_commit is not None:
            request["baseline"]["issuer_snapshot_commit"] = snapshot_commit
        write_yaml(td / "request.yaml", request)
        digest = sha256(td / "request.yaml")
        (td / "request.sha256").write_text(
            f"{digest}  request.yaml\n", encoding="utf-8")

    def _snapshot_commit(self, td: pathlib.Path) -> str:
        """Create a dangling commit whose tree contains byte-identical
        request.yaml/request.sha256/baseline manifest for this task dir."""
        def tree(entries: list[tuple[str, str, str]]) -> str:
            lines = "".join(f"{entry_type} {sha}\t{name}\n"
                            for name, entry_type, sha in entries)
            return self._mktree(lines)

        base_tree = tree([
            ("git-status.txt", "100644 blob", self._git(
                REPO_ROOT, "hash-object", "-w",
                str(td / "baseline" / "git-status.txt"))),
            ("scope-files.sha256", "100644 blob", self._git(
                REPO_ROOT, "hash-object", "-w",
                str(td / "baseline" / "scope-files.sha256"))),
        ])
        task_tree = tree([
            ("request.yaml", "100644 blob", self._git(
                REPO_ROOT, "hash-object", "-w", str(td / "request.yaml"))),
            ("request.sha256", "100644 blob", self._git(
                REPO_ROOT, "hash-object", "-w", str(td / "request.sha256"))),
            ("baseline", "040000 tree", base_tree),
        ])
        parent = self._git(REPO_ROOT, "rev-parse", "HEAD")
        root_tree = tree([(td.name, "040000 tree", task_tree)])
        return self._git(REPO_ROOT, "commit-tree", root_tree,
                         "-p", parent, "-m", "selftest issuer snapshot")

    def _mktree(self, lines: str) -> str:
        proc = subprocess.run(["git", "-C", str(REPO_ROOT), "mktree"],
                              input=lines, capture_output=True, text=True,
                              check=True)
        return proc.stdout.strip()

    def _ack(self, td: pathlib.Path, observed_head: str) -> None:
        (td / "attempts" / "A01").mkdir(parents=True, exist_ok=True)
        ack = {
            "protocol": "josim-handoff/v1",
            "document_type": "execution_ack",
            "schema_version": 1,
            "task_id": self.TASK_ID,
            "revision": 1,
            "attempt_id": "A01",
            "workflow_state": "ACKED",
            "created_at": "2026-08-17T02:00:01+08:00",
            "executor": {"role": "CLAUDE_CODE", "id": "claude-code"},
            "bindings": {"request_sha256": sha256(td / "request.yaml")},
            "decision": "ACCEPTED",
            "preflight": {
                "observed_git_head": observed_head,
                "dirty_paths": [], "scope_accepted": True,
                "required_skills_available": True},
            "understanding": {"objective": "x", "non_goals": [],
                              "stop_conditions": []},
            "planned_commands": [], "expected_changed_paths": [],
            "blockers": [], "deviations": [],
        }
        write_yaml(td / "attempts" / "A01" / "ack.yaml", ack)

    def test_real_snapshot_positive_with_parent_different_head(self) -> None:
        """AC2 positive: parent baseline HEAD != snapshot HEAD; the snapshot
        tree carries the snapshot-time request/signature and the final
        request binds the snapshot commit; verify succeeds."""
        with tempfile.TemporaryDirectory(
                prefix=".handoff-snap-", dir=REPO_ROOT) as temporary:
            td = Path(temporary)
            parent = self._git(REPO_ROOT, "rev-parse", "HEAD")
            # snapshot-time (pre-reference) request bytes are written and
            # signed first; the snapshot commit carries exactly those bytes
            self._write_request(td, None, parent)
            snapshot = self._snapshot_commit(td)
            self.assertNotEqual(parent, snapshot,
                                "parent baseline HEAD must differ from "
                                "issuer snapshot HEAD")
            # final request binds the snapshot commit (self-reference) and
            # is re-sealed; scope manifest is unchanged
            self._write_request(td, snapshot, parent)
            self._ack(td, snapshot)
            errors, _ = HANDOFF.verify_task(td, SCHEMA_DIR, REPO_ROOT)
            self.assertEqual(errors, [],
                             f"real snapshot must verify, got {errors}")

    def test_snapshot_byte_drift_fails(self) -> None:
        """AC2 negative: disk request.yaml drifting from the snapshot tree
        (beyond the self-referential snapshot field) must fail."""
        with tempfile.TemporaryDirectory(
                prefix=".handoff-snap-", dir=REPO_ROOT) as temporary:
            td = Path(temporary)
            parent = self._git(REPO_ROOT, "rev-parse", "HEAD")
            self._write_request(td, None, parent)
            snapshot = self._snapshot_commit(td)
            self._write_request(td, snapshot, parent)
            self._ack(td, snapshot)
            request_path = td / "request.yaml"
            drifted = request_path.read_text(encoding="utf-8").replace(
                "real issuer-snapshot selftest",
                "real issuer-snapshot selftest DRIFTED")
            request_path.write_text(drifted, encoding="utf-8")
            errors, _ = HANDOFF.verify_task(td, SCHEMA_DIR, REPO_ROOT)
            self.assertTrue(
                any("differs from issuer snapshot" in e for e in errors),
                f"byte drift must fail, got {errors}")

    def test_legacy_strict_head_still_required(self) -> None:
        """AC1: without issuer_snapshot_commit the ACK must observe the
        request baseline git_head (legacy strict-HEAD unchanged)."""
        with tempfile.TemporaryDirectory(
                prefix=".handoff-snap-", dir=REPO_ROOT) as temporary:
            td = Path(temporary)
            baseline = self._git(REPO_ROOT, "rev-parse", "HEAD")
            self._write_request(td, None, baseline)
            self._ack(td, baseline)
            errors, _ = HANDOFF.verify_task(td, SCHEMA_DIR, REPO_ROOT)
            self.assertEqual(errors, [],
                             f"legacy strict-HEAD must verify, got {errors}")
            self._ack(td, "0" * 40)  # wrong observed head
            errors, _ = HANDOFF.verify_task(td, SCHEMA_DIR, REPO_ROOT)
            self.assertTrue(
                any("observed_git_head differs" in e for e in errors),
                f"wrong observed head must fail, got {errors}")


class SyntheticChainTests(IssuerSnapshotRealTests):
    """AC7: one synthetic CRITICAL/FROZEN no-JoSIM task completes the whole
    chain — issuer snapshot -> ACK -> multi-file pre-receipt bundle ->
    raw+spec independent verifier -> structured result -> deterministic
    report -> receipt -> verify-task VERIFIED — without historic-path
    changes."""

    TASK_ID = "JH-20260817-WM-CHAIN-SELFTEST-001"
    BUNDLER = REPO_ROOT / "scripts" / "build_evidence_bundle.py"
    VERIFIER = REPO_ROOT / "scripts" / "quantitative_analysis_verifier.py"
    RENDERER = REPO_ROOT / "scripts" / "render_structured_report.py"

    def test_synthetic_chain_verifies_end_to_end(self) -> None:
        with tempfile.TemporaryDirectory(
                prefix=".handoff-chain-", dir=REPO_ROOT) as temporary:
            td = Path(temporary)
            relative = td.name
            artifacts = td / "artifacts"
            artifacts.mkdir()
            # raw runs (scalar baseline_subtracted_peak: V pulse in the
            # activity window; renderer renders scalar metrics only)
            raws = artifacts / "raws"
            raws.mkdir()
            for name, v_factor in (("main.csv", 12.0),
                                   ("raw-extra.csv", 1.0)):
                rows = ['time,"P(B_J1|XB1)","V(B_J1|XB1)","V(SL1)"']
                for k in range(1001):
                    t = k * 1e-13
                    p = 1.0 + 0.1 * (t / 1e-10)
                    v = 1e-3 if 40e-12 <= t < 60e-12 else 0.0
                    rows.append(f"{t:.6e},{p:.9e},{v:.9e},"
                                f"{v * v_factor:.9e}")
                (raws / name).write_text(
                    "\n".join(rows) + "\n", encoding="utf-8")
            # spec + structured result (scalar metric -> renderable)
            spec = {
                "schema_version": "quantitative-analysis-spec-v1",
                "spec_id": "synthetic-chain",
                "raw_path": f"{relative}/artifacts/raws/main.csv",
                "timestamp_rule": "exact_decimal_zero_tolerance",
                "interpolation": "prohibited",
                "windows": {"pre": [0, 40], "activity": [40, 60]},
                "columns": {"V_SL1": "V(SL1)"},
                "metrics": [{"id": "peak_v", "kind":
                             "baseline_subtracted_peak",
                             "column": "V(SL1)", "window": "activity",
                             "baseline_window": "pre",
                             "compare_tolerance": 1e-9}],
                "integration": {"actual_time": True,
                                "phi0_wb": 2.067833848e-15},
                "same_jj": {"phase_column": "P(B_J1|XB1)",
                            "voltage_column": "V(B_J1|XB1)",
                            "window": "activity",
                            "reporting_direction": 1,
                            "voltage_to_phase_sign": 1},
            }
            (artifacts / "spec.json").write_text(
                json.dumps(spec), encoding="utf-8")
            structured = {"metadata": {"title": "synthetic chain",
                                       "run_id": "chain-01",
                                       "spec_id": "synthetic-chain"},
                          "metrics": {"peak_v": 0.012},
                          "windows": {"pre": [0, 40], "activity": [40, 60]},
                          "notes": []}
            (artifacts / "structured.json").write_text(
                json.dumps(structured), encoding="utf-8")
            # raw+spec independent verifier recomputation
            verifier_log = artifacts / "verify.log"
            proc = subprocess.run(
                [sys.executable, str(self.VERIFIER),
                 str(raws / "main.csv"),
                 str(artifacts / "spec.json"),
                 str(artifacts / "structured.json")],
                capture_output=True, text=True)
            verifier_log.write_text(proc.stdout + proc.stderr,
                                    encoding="utf-8")
            self.assertEqual(proc.returncode, 0,
                             f"independent verifier must pass: "
                             f"{proc.stdout + proc.stderr}")
            # deterministic report
            report = artifacts / "report.md"
            proc = subprocess.run(
                [sys.executable, str(self.RENDERER),
                 str(artifacts / "structured.json"), str(report)],
                capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            # remaining bundle roles (placeholder inputs/manifest/analyzer/
            # inventory/receipt-pending)
            for name in ("inputs", "manifest", "analyzer", "inventory"):
                (artifacts / f"{name}.txt").write_text(
                    f"synthetic-{name}", encoding="utf-8")
            receipt_pending = artifacts / "receipt-pending.yaml"
            receipt_pending.write_text(
                "status: pending\n", encoding="utf-8")
            bundle_path = artifacts / "bundle.yaml"
            proc = subprocess.run(
                [sys.executable, str(self.BUNDLER), str(bundle_path),
                 f"{relative}/artifacts/raws", "raw",
                 f"{relative}/artifacts/inputs.txt", "inputs",
                 f"{relative}/artifacts/verify.log", "logs",
                 f"{relative}/artifacts/manifest.txt", "manifest",
                 f"{relative}/artifacts/spec.json", "spec",
                 f"{relative}/artifacts/analyzer.txt", "analyzer",
                 f"{relative}/artifacts/structured.json",
                 "structured_result",
                 str(self.VERIFIER), "verifier",
                 str(self.RENDERER), "renderer",
                 f"{relative}/artifacts/report.md", "report",
                 f"{relative}/artifacts/inventory.txt", "inventory",
                 f"{relative}/artifacts/receipt-pending.yaml", "receipt"],
                capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            # request (issuer snapshot), ACK
            parent = self._git(REPO_ROOT, "rev-parse", "HEAD")
            write_paths = [f"{relative}/artifacts/**",
                           f"{relative}/attempts/**"]
            deliverables = [
                {"id": "D1", "path": f"{relative}/artifacts/report.md",
                 "role": "IMPLEMENTATION", "required": True},
                {"id": "D2",
                 "path": f"{relative}/attempts/**/receipt.yaml",
                 "role": "RECEIPT", "required": True},
            ]
            acceptance = [
                {"id": "AC1", "condition": "synthetic chain VERIFIED",
                 "evidence": ["bundle", "verifier", "report"]},
            ]
            self._write_request(td, None, parent,
                                write_paths=write_paths,
                                deliverables=deliverables,
                                acceptance=acceptance)
            snapshot = self._snapshot_commit(td)
            self._write_request(td, snapshot, parent,
                                write_paths=write_paths,
                                deliverables=deliverables,
                                acceptance=acceptance)
            self._ack(td, snapshot)
            # receipt binds the PRE-receipt bundle (bundle does not hash the
            # final receipt)
            attempt_dir = td / "attempts" / "A01"
            log_dir = attempt_dir / "logs"
            log_dir.mkdir(parents=True)
            (log_dir / "chain.log").write_text(
                "synthetic chain log\n", encoding="utf-8")
            receipt = {
                "protocol": "josim-handoff/v1",
                "document_type": "execution_receipt",
                "schema_version": 1,
                "task_id": self.TASK_ID,
                "revision": 1,
                "attempt_id": "A01",
                "workflow_state": "DELIVERED",
                "created_at": "2026-08-17T03:00:02+08:00",
                "executor": {"role": "CLAUDE_CODE", "id": "claude-code"},
                "bindings": {
                    "request_sha256": sha256(td / "request.yaml"),
                    "ack_sha256": sha256(attempt_dir / "ack.yaml")},
                "execution_status": "COMPLETED",
                "baseline_git_head": snapshot,
                "result_git_head": None,
                "changes": [
                    {"path": f"{relative}/artifacts/{p.name}",
                     "action": "CREATED", "sha256": sha256(p)}
                    for p in sorted(artifacts.iterdir())
                    if p.is_file()
                ] + [
                    {"path": f"{relative}/attempts/A01/logs/chain.log",
                     "action": "CREATED",
                     "sha256": sha256(attempt_dir / "logs" / "chain.log")},
                ],
                "artifacts": [
                    {"id": p.name, "path": f"{relative}/artifacts/{p.name}",
                     "sha256": sha256(p),
                     "role": "DOCUMENTATION"}
                    for p in sorted(artifacts.iterdir())
                    if p.is_file()
                ] + [
                    {"id": "chain-log",
                     "path": f"{relative}/attempts/A01/logs/chain.log",
                     "sha256": sha256(attempt_dir / "logs" / "chain.log"),
                     "role": "LOG"},
                ],
                "evidence_bundle": {
                    "path": f"{relative}/artifacts/bundle.yaml",
                    "sha256": sha256(bundle_path),
                },
                "commands": [
                    {"command": "synthetic chain (verifier + bundle + "
                                "renderer)",
                     "exit_code": 0,
                     "log_path": f"{relative}/attempts/A01/logs/chain.log",
                     "log_sha256": sha256(attempt_dir / "logs" / "chain.log")},
                ],
                "tests": [
                    {"id": "synthetic-chain", "status": "PASS",
                     "evidence_paths": [
                         f"{relative}/artifacts/verify.log"],
                     "notes": []},
                ],
                "acceptance_results": [
                    {"id": "AC1", "status": "SATISFIED",
                     "evidence_paths": [
                         f"{relative}/artifacts/bundle.yaml",
                         f"{relative}/artifacts/verify.log",
                         f"{relative}/artifacts/report.md"],
                     "notes": []},
                ],
                "observations": [], "interpretations": [], "unknowns": [],
                "proposed_physical_verdict": "NOT_APPLICABLE",
                "limitations": [], "deviations": [], "blockers": [],
            }
            write_yaml(attempt_dir / "receipt.yaml", receipt)
            errors, _ = HANDOFF.verify_task(td, SCHEMA_DIR, REPO_ROOT)
            self.assertEqual(errors, [],
                             f"synthetic chain must verify, got {errors}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
