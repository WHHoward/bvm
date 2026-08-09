#!/usr/bin/env python3
"""Validate and cryptographically bind JoSIM Codex↔Claude handoff records."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import sys
from typing import Any, Iterable

import yaml
from jsonschema import Draft202012Validator, FormatChecker


PROTOCOL = "josim-handoff/v1"
SCHEMA_FILES = {
    "task_request": "task-request.schema.json",
    "execution_ack": "execution-ack.schema.json",
    "execution_receipt": "execution-receipt.schema.json",
    "audit_verdict": "audit-verdict.schema.json",
}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
MANIFEST_LINE_RE = re.compile(r"^([0-9a-f]{64})  (.+)$")


class HandoffError(RuntimeError):
    """Raised for a handoff contract or evidence error."""


class _StringTimestampLoader(yaml.SafeLoader):
    """Load YAML timestamps as strings so JSON Schema sees their source type."""


_StringTimestampLoader.yaml_implicit_resolvers = {
    key: [
        resolver
        for resolver in resolvers
        if resolver[0] != "tag:yaml.org,2002:timestamp"
    ]
    for key, resolvers in yaml.SafeLoader.yaml_implicit_resolvers.items()
}


def _find_repo_root(start: Path) -> Path:
    candidate = start.resolve()
    if candidate.is_file():
        candidate = candidate.parent
    for directory in (candidate, *candidate.parents):
        if (directory / ".git").exists():
            return directory
    raise HandoffError(f"cannot find repository root from {start}")


def _ensure_inside_repo(path: Path, repo_root: Path, label: str) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(repo_root)
    except ValueError as exc:
        raise HandoffError(f"{label} is outside repository: {path}") from exc
    return resolved


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise HandoffError(f"cannot read {path}: {exc}") from exc
    return digest.hexdigest()


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as stream:
            value = yaml.load(stream, Loader=_StringTimestampLoader)
    except (OSError, yaml.YAMLError) as exc:
        raise HandoffError(f"cannot load YAML {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise HandoffError(f"document must be a YAML mapping: {path}")
    return value


def _load_schema(schema_dir: Path, document_type: str) -> dict[str, Any]:
    filename = SCHEMA_FILES.get(document_type)
    if filename is None:
        known = ", ".join(sorted(SCHEMA_FILES))
        raise HandoffError(
            f"unknown document_type {document_type!r}; expected one of: {known}"
        )
    schema_path = schema_dir / filename
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HandoffError(f"cannot load schema {schema_path}: {exc}") from exc
    Draft202012Validator.check_schema(schema)
    return schema


def _format_error_path(parts: Iterable[Any]) -> str:
    result = "$"
    for part in parts:
        if isinstance(part, int):
            result += f"[{part}]"
        else:
            result += f".{part}"
    return result


def _validate_repo_path(value: str, label: str) -> None:
    if not isinstance(value, str) or not value:
        raise HandoffError(f"{label} must be a non-empty repository-relative path")
    if "\\" in value:
        raise HandoffError(f"{label} must use '/' separators: {value!r}")
    pure = PurePosixPath(value)
    if pure.is_absolute() or value.startswith("./"):
        raise HandoffError(f"{label} must be repository-relative: {value!r}")
    if any(part in {"", ".", ".."} for part in value.split("/")):
        raise HandoffError(f"{label} contains an unsafe path component: {value!r}")


def _semantic_path_checks(document: dict[str, Any]) -> None:
    document_type = document.get("document_type")
    paths: list[tuple[str, str]] = []

    def add(value: Any, label: str) -> None:
        if isinstance(value, str):
            paths.append((value, label))

    def add_many(values: Any, label: str) -> None:
        if isinstance(values, list):
            for index, value in enumerate(values):
                add(value, f"{label}[{index}]")

    if document_type == "task_request":
        scope = document.get("scope", {})
        for key in ("read_paths", "write_paths", "frozen_paths", "locks"):
            add_many(scope.get(key), f"scope.{key}")
        baseline = document.get("baseline", {})
        for key in ("git_status", "scope_hashes"):
            add(baseline.get(key, {}).get("path"), f"baseline.{key}.path")
        contracts = document.get("contracts", {})
        add_many(contracts.get("read_first"), "contracts.read_first")
        for key in ("handover", "metric_spec"):
            add(contracts.get(key, {}).get("path"), f"contracts.{key}.path")
        for index, item in enumerate(document.get("deliverables", [])):
            add(item.get("path"), f"deliverables[{index}].path")
    elif document_type == "execution_ack":
        add_many(document.get("preflight", {}).get("dirty_paths"), "preflight.dirty_paths")
        add_many(document.get("expected_changed_paths"), "expected_changed_paths")
    elif document_type == "execution_receipt":
        for index, item in enumerate(document.get("changes", [])):
            add(item.get("path"), f"changes[{index}].path")
            add(item.get("previous_path"), f"changes[{index}].previous_path")
        for index, item in enumerate(document.get("artifacts", [])):
            add(item.get("path"), f"artifacts[{index}].path")
        for index, item in enumerate(document.get("commands", [])):
            add(item.get("log_path"), f"commands[{index}].log_path")
        for index, item in enumerate(document.get("tests", [])):
            add_many(item.get("evidence_paths"), f"tests[{index}].evidence_paths")
        for index, item in enumerate(document.get("acceptance_results", [])):
            add_many(
                item.get("evidence_paths"),
                f"acceptance_results[{index}].evidence_paths",
            )

    for value, label in paths:
        _validate_repo_path(value, label)

    if document_type == "task_request" and document.get("supersedes"):
        supersedes = document["supersedes"]
        if supersedes["task_id"] == document["task_id"]:
            raise HandoffError(
                "supersedes must use a new task_id so the old signed request remains addressable"
            )

    if document_type == "task_request":
        write_paths = document["scope"]["write_paths"]
        frozen_paths = document["scope"]["frozen_paths"]
        for write_path in write_paths:
            for frozen_path in frozen_paths:
                if _matches_scope(write_path, frozen_path) or _matches_scope(
                    frozen_path, write_path
                ):
                    raise HandoffError(
                        "scope.write_paths overlaps scope.frozen_paths: "
                        f"{write_path} <> {frozen_path}"
                    )
        for deliverable in document["deliverables"]:
            if not any(
                _matches_scope(deliverable["path"], write_path)
                for write_path in write_paths
            ):
                raise HandoffError(
                    f"deliverable {deliverable['id']} is outside scope.write_paths: "
                    f"{deliverable['path']}"
                )
        for field in ("deliverables", "acceptance"):
            ids = [item["id"] for item in document[field]]
            duplicates = sorted({item_id for item_id in ids if ids.count(item_id) > 1})
            if duplicates:
                raise HandoffError(
                    f"{field} contains duplicate ids: {', '.join(duplicates)}"
                )
    elif document_type == "execution_receipt":
        for field in ("artifacts", "tests", "acceptance_results"):
            ids = [item["id"] for item in document[field]]
            duplicates = sorted({item_id for item_id in ids if ids.count(item_id) > 1})
            if duplicates:
                raise HandoffError(
                    f"{field} contains duplicate ids: {', '.join(duplicates)}"
                )
    elif document_type == "audit_verdict":
        ids = [item["id"] for item in document["checks"]]
        duplicates = sorted({item_id for item_id in ids if ids.count(item_id) > 1})
        if duplicates:
            raise HandoffError(f"checks contains duplicate ids: {', '.join(duplicates)}")


def validate_document(path: Path, schema_dir: Path, repo_root: Path) -> dict[str, Any]:
    path = _ensure_inside_repo(path, repo_root, "document")
    document = _load_yaml(path)
    if document.get("protocol") != PROTOCOL:
        raise HandoffError(f"{path}: protocol must be {PROTOCOL!r}")
    document_type = document.get("document_type")
    if not isinstance(document_type, str):
        raise HandoffError(f"{path}: missing string document_type")
    schema = _load_schema(schema_dir, document_type)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(
        validator.iter_errors(document),
        key=lambda error: tuple(str(part) for part in error.absolute_path),
    )
    if errors:
        messages = [
            f"{_format_error_path(error.absolute_path)}: {error.message}"
            for error in errors
        ]
        raise HandoffError(f"schema validation failed for {path}:\n  " + "\n  ".join(messages))
    _semantic_path_checks(document)
    return document


def _bound_file_error(
    binding: dict[str, Any], repo_root: Path, label: str
) -> str | None:
    path_value = binding.get("path")
    expected = binding.get("sha256")
    if path_value is None or expected is None:
        return None
    try:
        _validate_repo_path(path_value, f"{label}.path")
        path = _ensure_inside_repo(repo_root / path_value, repo_root, label)
        actual = _sha256(path)
    except HandoffError as exc:
        return str(exc)
    if actual != expected:
        return f"{label} hash mismatch: expected {expected}, got {actual} ({path_value})"
    return None


def _request_reference_errors(request: dict[str, Any], repo_root: Path) -> list[str]:
    errors: list[str] = []
    baseline = request["baseline"]
    for key in ("git_status", "scope_hashes"):
        error = _bound_file_error(baseline[key], repo_root, f"baseline.{key}")
        if error:
            errors.append(error)
    contracts = request["contracts"]
    for key in ("handover", "metric_spec"):
        error = _bound_file_error(contracts[key], repo_root, f"contracts.{key}")
        if error:
            errors.append(error)
    errors.extend(_scope_manifest_errors(request, repo_root))
    return errors


def _scope_manifest_errors(
    request: dict[str, Any], repo_root: Path
) -> list[str]:
    """Verify every file authorized by read_paths against scope-files.sha256."""
    binding = request["baseline"]["scope_hashes"]
    manifest_value = binding.get("path")
    manifest_digest = binding.get("sha256")
    if manifest_value is None or manifest_digest is None:
        return []
    manifest_path = repo_root / manifest_value
    errors: list[str] = []
    entries: dict[str, str] = {}
    try:
        lines = manifest_path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        return [f"cannot read scope hash manifest {manifest_value}: {exc}"]
    for line_number, line in enumerate(lines, start=1):
        match = MANIFEST_LINE_RE.fullmatch(line)
        if match is None:
            errors.append(
                f"scope hash manifest line {line_number} must be '<sha256>  <path>'"
            )
            continue
        expected, path_value = match.groups()
        try:
            _validate_repo_path(path_value, f"scope manifest line {line_number}")
        except HandoffError as exc:
            errors.append(str(exc))
            continue
        if path_value in entries:
            errors.append(f"scope hash manifest repeats path: {path_value}")
            continue
        entries[path_value] = expected

    required: set[str] = set()
    for pattern in request["scope"]["read_paths"]:
        has_glob = any(character in pattern for character in "*?[")
        if has_glob:
            matches = sorted(
                path
                for path in repo_root.glob(pattern)
                if path.is_file()
            )
            if not matches:
                errors.append(f"scope.read_paths pattern matched no files: {pattern}")
            required.update(path.relative_to(repo_root).as_posix() for path in matches)
        else:
            path = repo_root / pattern
            if not path.is_file():
                errors.append(f"scope.read_paths file is missing: {pattern}")
            else:
                required.add(pattern)

    missing = sorted(required - set(entries))
    unexpected = sorted(set(entries) - required)
    if missing:
        errors.append("scope hash manifest is missing paths: " + ", ".join(missing))
    if unexpected:
        errors.append("scope hash manifest has out-of-scope paths: " + ", ".join(unexpected))
    for path_value, expected in entries.items():
        error = _repo_file_hash_error(
            repo_root, path_value, expected, f"scope manifest entry {path_value}"
        )
        if error:
            errors.append(error)
    return errors


def _parse_signature(path: Path, expected_filename: str) -> str:
    try:
        content = path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise HandoffError(f"cannot read signature {path}: {exc}") from exc
    match = re.fullmatch(r"([0-9a-f]{64})(?:\s+\*?([^\s]+))?", content)
    if not match:
        raise HandoffError(f"malformed SHA-256 signature file: {path}")
    signed_name = match.group(2)
    if signed_name is not None and signed_name != expected_filename:
        raise HandoffError(
            f"signature {path} names {signed_name!r}, expected {expected_filename!r}"
        )
    return match.group(1)


def _matches_scope(path: str, pattern: str) -> bool:
    if path == pattern:
        return True
    if pattern.endswith("/**"):
        prefix = pattern[:-3].rstrip("/")
        return path == prefix or path.startswith(prefix + "/")
    if pattern.endswith("/"):
        return path.startswith(pattern)
    return PurePosixPath(path).match(pattern)


def _scope_errors(receipt: dict[str, Any], request: dict[str, Any]) -> list[str]:
    write_paths = request["scope"]["write_paths"]
    frozen_paths = request["scope"]["frozen_paths"]
    errors: list[str] = []
    seen: set[str] = set()
    for change in receipt["changes"]:
        path = change["path"]
        if path in seen:
            errors.append(f"receipt lists changed path more than once: {path}")
        seen.add(path)
        if not any(_matches_scope(path, allowed) for allowed in write_paths):
            errors.append(f"changed path is outside request scope.write_paths: {path}")
        if any(_matches_scope(path, frozen) for frozen in frozen_paths):
            errors.append(f"changed path intersects request scope.frozen_paths: {path}")
        previous_path = change.get("previous_path")
        if previous_path is not None:
            if not any(
                _matches_scope(previous_path, allowed) for allowed in write_paths
            ):
                errors.append(
                    "renamed source is outside request scope.write_paths: "
                    f"{previous_path}"
                )
            if any(_matches_scope(previous_path, frozen) for frozen in frozen_paths):
                errors.append(
                    "renamed source intersects request scope.frozen_paths: "
                    f"{previous_path}"
                )
    return errors


def _ack_scope_errors(ack: dict[str, Any], request: dict[str, Any]) -> list[str]:
    if ack["decision"] != "ACCEPTED":
        return []
    write_paths = request["scope"]["write_paths"]
    frozen_paths = request["scope"]["frozen_paths"]
    errors: list[str] = []
    for path in ack["expected_changed_paths"]:
        if not any(_matches_scope(path, allowed) for allowed in write_paths):
            errors.append(f"expected changed path is outside scope.write_paths: {path}")
        if any(_matches_scope(path, frozen) for frozen in frozen_paths):
            errors.append(f"expected changed path intersects scope.frozen_paths: {path}")
    return errors


def _acceptance_mapping_errors(
    receipt: dict[str, Any], request: dict[str, Any]
) -> list[str]:
    required_ids = [item["id"] for item in request["acceptance"]]
    reported_ids = [item["id"] for item in receipt["acceptance_results"]]
    errors: list[str] = []
    if len(reported_ids) != len(set(reported_ids)):
        errors.append("acceptance_results contains duplicate ids")
    missing = sorted(set(required_ids) - set(reported_ids))
    unknown = sorted(set(reported_ids) - set(required_ids))
    if missing:
        errors.append(f"acceptance_results is missing request ids: {', '.join(missing)}")
    if unknown:
        errors.append(f"acceptance_results contains unknown ids: {', '.join(unknown)}")
    return errors


def _deliverable_errors(
    receipt_path: Path,
    receipt: dict[str, Any],
    request: dict[str, Any],
    repo_root: Path,
) -> list[str]:
    """Require every request deliverable to appear in the receipt or be the receipt."""
    errors: list[str] = []
    receipt_relative = receipt_path.relative_to(repo_root).as_posix()
    artifact_paths = [item["path"] for item in receipt["artifacts"]]
    for deliverable in request["deliverables"]:
        if not deliverable["required"]:
            continue
        pattern = deliverable["path"]
        if deliverable["role"] == "RECEIPT":
            present = _matches_scope(receipt_relative, pattern)
        else:
            present = any(_matches_scope(path, pattern) for path in artifact_paths)
        if not present:
            errors.append(
                f"required deliverable {deliverable['id']} is not represented: {pattern}"
            )
    return errors


def _repo_file_hash_error(
    repo_root: Path, path_value: str, expected: str, label: str
) -> str | None:
    try:
        _validate_repo_path(path_value, label)
        path = _ensure_inside_repo(repo_root / path_value, repo_root, label)
        if not path.is_file():
            return f"{label} is missing or not a file: {path_value}"
        actual = _sha256(path)
    except HandoffError as exc:
        return str(exc)
    if actual != expected:
        return (
            f"{label} hash mismatch: expected {expected}, got {actual} "
            f"({path_value})"
        )
    return None


def _receipt_file_errors(
    receipt: dict[str, Any], request: dict[str, Any], repo_root: Path
) -> list[str]:
    errors: list[str] = []
    authorization = request["authorization"]
    changes = receipt["changes"]
    change_paths = {change["path"] for change in changes}
    artifact_paths = {artifact["path"] for artifact in receipt["artifacts"]}
    if changes and not authorization["edit"]:
        errors.append("receipt reports file changes but authorization.edit is false")
    for index, change in enumerate(changes):
        action = change["action"]
        if action in {"DELETED", "RENAMED"} and not authorization["delete_or_overwrite"]:
            errors.append(
                f"changes[{index}] action {action} requires "
                "authorization.delete_or_overwrite"
            )
        if action != "DELETED":
            error = _repo_file_hash_error(
                repo_root,
                change["path"],
                change["sha256"],
                f"changes[{index}]",
            )
            if error:
                errors.append(error)
    for index, artifact in enumerate(receipt["artifacts"]):
        if artifact["path"] not in change_paths:
            errors.append(
                f"artifacts[{index}] is not represented in changes: {artifact['path']}"
            )
        error = _repo_file_hash_error(
            repo_root,
            artifact["path"],
            artifact["sha256"],
            f"artifacts[{index}]",
        )
        if error:
            errors.append(error)
    for index, command in enumerate(receipt["commands"]):
        if command["log_path"] not in change_paths:
            errors.append(
                f"commands[{index}].log_path is not represented in changes: "
                f"{command['log_path']}"
            )
        if command["log_path"] not in artifact_paths:
            errors.append(
                f"commands[{index}].log_path is not represented in artifacts: "
                f"{command['log_path']}"
            )
        error = _repo_file_hash_error(
            repo_root,
            command["log_path"],
            command["log_sha256"],
            f"commands[{index}].log",
        )
        if error:
            errors.append(error)
    for field in ("tests", "acceptance_results"):
        for index, record in enumerate(receipt[field]):
            for evidence_path in record["evidence_paths"]:
                if evidence_path not in artifact_paths:
                    errors.append(
                        f"{field}[{index}] evidence is not a hashed artifact: "
                        f"{evidence_path}"
                    )
    return errors


def _discover_protocol_documents(
    task_dir: Path, schema_dir: Path, repo_root: Path
) -> list[tuple[Path, dict[str, Any]]]:
    documents: list[tuple[Path, dict[str, Any]]] = []
    candidates = sorted(set(task_dir.rglob("*.yaml")) | set(task_dir.rglob("*.yml")))
    protocol_names = {"request.yaml", "ack.yaml", "receipt.yaml", "verdict.yaml"}
    for path in candidates:
        if path.name not in protocol_names:
            continue
        path = _ensure_inside_repo(path, repo_root, "protocol document")
        document = _load_yaml(path)
        if document.get("protocol") != PROTOCOL:
            raise HandoffError(
                f"reserved protocol record has wrong or missing protocol: {path}"
            )
        document = validate_document(path, schema_dir, repo_root)
        documents.append((path, document))
    return documents


def _supersession_errors(
    request: dict[str, Any], schema_dir: Path, repo_root: Path
) -> list[str]:
    errors: list[str] = []
    reference = request.get("supersedes")
    seen = {(request["task_id"], request["revision"])}
    while reference is not None:
        key = (reference["task_id"], reference["revision"])
        if key in seen:
            errors.append(f"supersedes cycle detected at {key[0]} revision {key[1]}")
            break
        seen.add(key)
        target_dir = repo_root / "research" / "tasks" / reference["task_id"]
        target_path = target_dir / "request.yaml"
        if not target_path.is_file():
            errors.append(f"supersedes target request is missing: {target_path}")
            break
        try:
            target = validate_document(target_path, schema_dir, repo_root)
        except HandoffError as exc:
            errors.append(f"invalid supersedes target {target_path}: {exc}")
            break
        if target["task_id"] != reference["task_id"]:
            errors.append(f"supersedes target task_id mismatch: {target_path}")
            break
        if target["revision"] != reference["revision"]:
            errors.append(f"supersedes target revision mismatch: {target_path}")
            break
        if target["workflow_state"] != "ISSUED":
            errors.append(f"supersedes target is not ISSUED: {target_path}")
            break
        signature_path = target_dir / "request.sha256"
        if not signature_path.is_file():
            errors.append(f"supersedes target signature is missing: {signature_path}")
            break
        try:
            signed_digest = _parse_signature(signature_path, target_path.name)
        except HandoffError as exc:
            errors.append(str(exc))
            break
        if signed_digest != _sha256(target_path):
            errors.append(f"supersedes target signature mismatch: {target_path}")
            break
        reference = target.get("supersedes")
    return errors


def verify_task(task_dir: Path, schema_dir: Path, repo_root: Path) -> tuple[list[str], list[str]]:
    task_dir = _ensure_inside_repo(task_dir, repo_root, "task directory")
    if not task_dir.is_dir():
        raise HandoffError(f"task directory does not exist: {task_dir}")
    request_path = task_dir / "request.yaml"
    if not request_path.is_file():
        raise HandoffError(f"missing task request: {request_path}")
    request = validate_document(request_path, schema_dir, repo_root)
    if request["document_type"] != "task_request":
        raise HandoffError(f"{request_path} is not a task_request")

    errors = _request_reference_errors(request, repo_root)
    errors.extend(_supersession_errors(request, schema_dir, repo_root))
    warnings: list[str] = []
    request_digest = _sha256(request_path)
    signature_path = task_dir / "request.sha256"
    state = request["workflow_state"]
    if state == "DRAFT":
        if signature_path.exists():
            errors.append("DRAFT request must not carry request.sha256; issue and sign it first")
        errors.append("request is DRAFT and is not authorized for execution")
    else:
        if not signature_path.is_file():
            errors.append(f"{state} request is missing request.sha256")
        else:
            try:
                signed_digest = _parse_signature(signature_path, request_path.name)
                if signed_digest != request_digest:
                    errors.append(
                        "request signature mismatch: "
                        f"expected {signed_digest}, got {request_digest}"
                    )
            except HandoffError as exc:
                errors.append(str(exc))

    documents = _discover_protocol_documents(task_dir, schema_dir, repo_root)
    acknowledgements: dict[str, tuple[Path, dict[str, Any]]] = {}
    receipts: dict[str, tuple[Path, dict[str, Any]]] = {}
    audits: dict[tuple[str, str], tuple[Path, dict[str, Any]]] = {}
    for path, document in documents:
        document_type = document["document_type"]
        if document_type == "task_request":
            if path != request_path:
                errors.append(f"unexpected second task_request: {path}")
            continue
        if document["task_id"] != request["task_id"]:
            errors.append(f"{path}: task_id does not match request")
        if document["revision"] != request["revision"]:
            errors.append(f"{path}: revision does not match request")
        attempt_id = document["attempt_id"]
        target: dict[Any, tuple[Path, dict[str, Any]]]
        if document_type == "execution_ack":
            target = acknowledgements
            record_key: Any = attempt_id
        elif document_type == "execution_receipt":
            target = receipts
            record_key = attempt_id
        else:
            target = audits
            record_key = (attempt_id, document["audit_id"])
        if record_key in target:
            errors.append(
                f"duplicate {document_type} for {record_key}: "
                f"{target[record_key][0]} and {path}"
            )
        else:
            target[record_key] = (path, document)

    if state == "DRAFT" and (acknowledgements or receipts or audits):
        errors.append("DRAFT request contains executor or audit records")

    for attempt_id, (ack_path, ack) in acknowledgements.items():
        if ack["bindings"]["request_sha256"] != request_digest:
            errors.append(f"{ack_path}: request_sha256 does not bind current request")
        if (
            ack["decision"] == "ACCEPTED"
            and ack["preflight"]["observed_git_head"] != request["baseline"]["git_head"]
        ):
            errors.append(f"{ack_path}: accepted ACK observed_git_head differs from baseline")
        errors.extend(
            f"{ack_path}: {error}" for error in _ack_scope_errors(ack, request)
        )

    for attempt_id, (receipt_path, receipt) in receipts.items():
        ack_entry = acknowledgements.get(attempt_id)
        if ack_entry is None:
            errors.append(f"{receipt_path}: no matching execution_ack for {attempt_id}")
            continue
        ack_path, ack = ack_entry
        if ack["decision"] != "ACCEPTED":
            errors.append(f"{receipt_path}: matching ACK is BLOCKED")
        bindings = receipt["bindings"]
        if bindings["request_sha256"] != request_digest:
            errors.append(f"{receipt_path}: request_sha256 does not bind current request")
        if bindings["ack_sha256"] != _sha256(ack_path):
            errors.append(f"{receipt_path}: ack_sha256 does not bind {ack_path}")
        if receipt["baseline_git_head"] != request["baseline"]["git_head"]:
            errors.append(f"{receipt_path}: baseline_git_head differs from request")
        errors.extend(f"{receipt_path}: {error}" for error in _scope_errors(receipt, request))
        errors.extend(
            f"{receipt_path}: {error}"
            for error in _acceptance_mapping_errors(receipt, request)
        )
        errors.extend(
            f"{receipt_path}: {error}"
            for error in _deliverable_errors(
                receipt_path, receipt, request, repo_root
            )
        )
        errors.extend(
            f"{receipt_path}: {error}"
            for error in _receipt_file_errors(receipt, request, repo_root)
        )

    for (attempt_id, _audit_id), (audit_path, audit) in audits.items():
        ack_entry = acknowledgements.get(attempt_id)
        receipt_entry = receipts.get(attempt_id)
        if ack_entry is None:
            errors.append(f"{audit_path}: no matching execution_ack for {attempt_id}")
            continue
        if receipt_entry is None:
            errors.append(f"{audit_path}: no matching execution_receipt for {attempt_id}")
            continue
        ack_path, _ack = ack_entry
        receipt_path, _receipt = receipt_entry
        bindings = audit["bindings"]
        if bindings["request_sha256"] != request_digest:
            errors.append(f"{audit_path}: request_sha256 does not bind current request")
        if bindings["ack_sha256"] != _sha256(ack_path):
            errors.append(f"{audit_path}: ack_sha256 does not bind {ack_path}")
        if bindings["receipt_sha256"] != _sha256(receipt_path):
            errors.append(f"{audit_path}: receipt_sha256 does not bind {receipt_path}")
        if audit["claim_ceiling"] != request["task"]["claim_ceiling"]:
            errors.append(f"{audit_path}: claim_ceiling does not match request")

    warnings.append(
        "records: "
        f"{len(acknowledgements)} ACK, {len(receipts)} receipt, {len(audits)} audit"
    )
    return errors, warnings


def _schema_dir_from_argument(value: str | None, repo_root: Path) -> Path:
    schema_dir = Path(value) if value else repo_root / "research" / "schemas"
    if not schema_dir.is_absolute():
        schema_dir = repo_root / schema_dir
    return _ensure_inside_repo(schema_dir, repo_root, "schema directory")


def _cmd_validate(args: argparse.Namespace) -> int:
    path = Path(args.document)
    repo_root = _find_repo_root(path if path.exists() else Path.cwd())
    schema_dir = _schema_dir_from_argument(args.schema_dir, repo_root)
    document = validate_document(path, schema_dir, repo_root)
    print(f"VALID {document['document_type']} {path}")
    return 0


def _cmd_sign_request(args: argparse.Namespace) -> int:
    request_path = Path(args.request)
    repo_root = _find_repo_root(request_path if request_path.exists() else Path.cwd())
    request_path = _ensure_inside_repo(request_path, repo_root, "request")
    schema_dir = _schema_dir_from_argument(args.schema_dir, repo_root)
    request = validate_document(request_path, schema_dir, repo_root)
    if request["document_type"] != "task_request":
        raise HandoffError(f"not a task_request: {request_path}")
    if request["workflow_state"] != "ISSUED":
        raise HandoffError("sign-request requires workflow_state: ISSUED")
    reference_errors = _request_reference_errors(request, repo_root)
    if reference_errors:
        raise HandoffError("cannot sign request:\n  " + "\n  ".join(reference_errors))

    digest = _sha256(request_path)
    signature_path = request_path.with_name("request.sha256")
    if signature_path.exists():
        existing = _parse_signature(signature_path, request_path.name)
        if existing != digest:
            raise HandoffError(
                f"refusing to overwrite different signature in {signature_path}"
            )
        print(f"UNCHANGED {signature_path} {digest}")
        return 0
    try:
        descriptor = os.open(signature_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(f"{digest}  {request_path.name}\n")
    except OSError as exc:
        raise HandoffError(f"cannot create signature {signature_path}: {exc}") from exc
    print(f"SIGNED {signature_path} {digest}")
    return 0


def _cmd_verify_task(args: argparse.Namespace) -> int:
    task_dir = Path(args.task_dir)
    repo_root = _find_repo_root(task_dir if task_dir.exists() else Path.cwd())
    schema_dir = _schema_dir_from_argument(args.schema_dir, repo_root)
    errors, warnings = verify_task(task_dir, schema_dir, repo_root)
    for warning in warnings:
        print(f"WARNING {warning}")
    if errors:
        raise HandoffError("task verification failed:\n  " + "\n  ".join(errors))
    print(f"VERIFIED {task_dir}")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate and bind JoSIM Codex↔Claude handoff records."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser(
        "validate", help="validate one YAML protocol document"
    )
    validate_parser.add_argument("document")
    validate_parser.add_argument("--schema-dir")
    validate_parser.set_defaults(handler=_cmd_validate)

    sign_parser = subparsers.add_parser(
        "sign-request", help="create request.sha256 for a valid ISSUED request"
    )
    sign_parser.add_argument("request")
    sign_parser.add_argument("--schema-dir")
    sign_parser.set_defaults(handler=_cmd_sign_request)

    verify_parser = subparsers.add_parser(
        "verify-task", help="verify a task directory and all protocol bindings"
    )
    verify_parser.add_argument("task_dir")
    verify_parser.add_argument("--schema-dir")
    verify_parser.set_defaults(handler=_cmd_verify_task)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        return args.handler(args)
    except HandoffError as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
