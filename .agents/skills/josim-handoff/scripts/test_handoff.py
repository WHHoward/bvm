#!/usr/bin/env python3
"""Self-contained regression tests for the JoSIM handoff protocol tooling."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
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
        baseline_dir = Path(relative) / "baseline"
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

if __name__ == "__main__":
    unittest.main(verbosity=2)
