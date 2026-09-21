#!/usr/bin/env python3
"""Single-user-entry platform for future BVM tuning cases.

The default path is intentionally safe: --dry-run renders and validates a
temporary preview but never creates a case directory and never invokes JoSIM.
Without --dry-run this script creates one immutable Uxxx_NAME case and runs
only the masks requested by USER_CASE.env.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any

SERIES = Path(__file__).resolve().parents[1]
REPO = next(path for path in (SERIES, *SERIES.parents) if (path / ".git").exists())
sys.path.insert(0, str(SERIES / "scripts"))
import run_candidate as legacy  # noqa: E402

USER_CONFIG = SERIES / "USER_CASE.env"
REFERENCE_CONFIG = SERIES / "config" / "canonical_reference.env"
CANONICAL_BVM = REPO / "test" / "exploration" / "bvm-qb-l1-l3-bj2-targeted-closure-v1-20260914" / "inputs" / "bvm_jm2_connected.cir"
LEGACY_HASHES = SERIES / "analysis" / "legacy_raw_hashes.json"
MASKS = {"quick": ["0001", "0011", "0111"], "full": ["0000", "0001", "0011", "0111", "1111"]}
NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
TIME_KEYS = ("IDLE_START", "IDLE_END", "WRITE0_START", "WRITE0_END", "CONTROL_READ_START", "CONTROL_READ_END", "WRITE1_START", "WRITE1_END", "FINAL_READ_START", "FINAL_READ_END", "RECOVERY_END", "TAIL_START", "STOP")
RESISTANCE_KEYS = ("RJM1", "RJM2", "RSH_JS1", "RSH_JS2", "RBL", "RWL", "RSE", "RS", "RSL")
INDUCTANCE_KEYS = ("LM1", "LM2", "LM3", "LPM", "LS1", "LS2", "LS3", "LPSL", "LSL", "LPBL", "LPWL", "LPSE")
AREA_KEYS = ("JM1_AREA", "JM2_AREA", "JS1_AREA", "JS2_AREA")
QB_AREA_KEYS = ("QB_BJS_AREA", "QB_BJ1_AREA", "QB_BJ2_AREA")
QB_RESISTANCE_KEYS = ("QB_RJ1", "QB_RJ2")
QB_INDUCTANCE_KEYS = ("QB_LIN", "QB_L1", "QB_L2", "QB_L3")
QB_CURRENT_KEYS = ("QB_IB",)
CIRCUIT_KEYS = set(AREA_KEYS + RESISTANCE_KEYS + INDUCTANCE_KEYS + QB_AREA_KEYS + QB_RESISTANCE_KEYS + QB_INDUCTANCE_KEYS + QB_CURRENT_KEYS)
STIMULUS_KEYS = {key for key in (
    *TIME_KEYS, "DT", "WRITE0_WL_AMP", "WRITE0_BL_AMP", "WRITE0_SE_AMP",
    "CONTROL_WL_AMP", "CONTROL_BL_AMP", "CONTROL_SE_AMP", "WRITE1_WL_AMP",
    "WRITE1_BL_AMP", "WRITE1_SE_AMP", "READ_WL_AMP", "READ_BL_AMP", "READ_SE_AMP",
    "WRITE0_WL_RISE", "WRITE0_WL_FALL", "WRITE0_BL_RISE", "WRITE0_BL_FALL",
    "WRITE0_SE_RISE", "WRITE0_SE_FALL", "CONTROL_WL_RISE", "CONTROL_WL_FALL",
    "CONTROL_BL_RISE", "CONTROL_BL_FALL", "CONTROL_SE_RISE", "CONTROL_SE_FALL",
    "WRITE1_WL_RISE", "WRITE1_WL_FALL", "WRITE1_BL_RISE", "WRITE1_BL_FALL",
    "WRITE1_SE_RISE", "WRITE1_SE_FALL", "READ_WL_RISE", "READ_WL_FALL",
    "READ_BL_RISE", "READ_BL_FALL", "READ_SE_RISE", "READ_SE_FALL")}


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def repo_rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def load_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in stripped:
            raise RuntimeError(f"invalid config line {path}:{number}")
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def parse_number(token: str, label: str) -> float:
    match = re.fullmatch(r"\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)([munpfk]?)\s*", token, re.IGNORECASE)
    if not match:
        raise RuntimeError(f"{label}: invalid numeric token {token!r}")
    scale = {"": 1.0, "p": 1e-12, "n": 1e-9, "u": 1e-6, "m": 1e-3, "f": 1e-15, "k": 1e3}[match.group(2).lower()]
    return float(match.group(1)) * scale


def time_ps(token: str, label: str) -> float:
    return parse_number(token, label) * 1e12


def format_time(value_ps: float) -> str:
    return "0" if abs(value_ps) < 1e-15 else f"{value_ps:g}p"


def format_current(value_a: float) -> str:
    if abs(value_a) < 1e-30:
        return "0"
    return f"{value_a * 1e6:+g}u"


def resolve_masks(value: str) -> list[str]:
    key = value.strip().lower()
    if key in MASKS:
        return list(MASKS[key])
    result = [item.strip() for item in value.split(",") if item.strip()]
    if not result or any(not re.fullmatch(r"[01]{4}", item) for item in result) or len(set(result)) != len(result):
        raise RuntimeError("MASKS must be quick, full, one four-bit mask, or a comma-separated list of unique four-bit masks")
    return result


def required(values: dict[str, str], key: str) -> str:
    if not values.get(key):
        raise RuntimeError(f"USER_CASE.env is missing {key}")
    return values[key]


def canonical_source_guard(reference: dict[str, str]) -> None:
    expected = required(reference, "CANONICAL_BVM_SOURCE_SHA256")
    actual = sha256(CANONICAL_BVM)
    if actual != expected:
        raise RuntimeError(f"CANONICAL_AUTHORITY_CHANGED: BVM source SHA {actual} != registered {expected}")


def validate(values: dict[str, str], reference: dict[str, str]) -> dict[str, Any]:
    canonical_source_guard(reference)
    name = required(values, "NAME")
    if not NAME_RE.fullmatch(name):
        raise RuntimeError("NAME must contain only letters, digits, underscore, or hyphen")
    mode = required(values, "MODE").lower()
    if mode not in {"passive", "closed"}:
        raise RuntimeError("MODE must be passive or closed")
    masks = resolve_masks(required(values, "MASKS"))
    for key in AREA_KEYS:
        if parse_number(required(values, key), key) <= 0:
            raise RuntimeError(f"{key} must be positive")
    for key in QB_AREA_KEYS + QB_INDUCTANCE_KEYS + QB_CURRENT_KEYS:
        if parse_number(required(values, key), key) <= 0:
            raise RuntimeError(f"{key} must be positive")
    for key in QB_RESISTANCE_KEYS:
        if parse_number(required(values, key), key) <= 0:
            raise RuntimeError(f"{key} must be positive")
    for key in RESISTANCE_KEYS:
        token = required(values, key)
        if token.upper() != "OPEN" and parse_number(token, key) <= 0:
            raise RuntimeError(f"{key} must be OPEN or positive")
    for key in INDUCTANCE_KEYS:
        if parse_number(required(values, key), key) <= 0:
            raise RuntimeError(f"{key} must be positive")
    for key in ("DT", "STOP"):
        if parse_number(required(values, key), key) <= 0:
            raise RuntimeError(f"{key} must be positive")
    times = {key: time_ps(required(values, key), key) for key in TIME_KEYS}
    if not (times["IDLE_START"] <= times["IDLE_END"] <= times["WRITE0_START"] < times["WRITE0_END"] <= times["CONTROL_READ_START"] < times["CONTROL_READ_END"] <= times["WRITE1_START"] < times["WRITE1_END"] <= times["FINAL_READ_START"] < times["FINAL_READ_END"] < times["RECOVERY_END"] <= times["TAIL_START"] < times["STOP"]):
        raise RuntimeError("timing ordering is invalid; expected IDLE <= WRITE0 < CONTROL < WRITE1 < FINAL READ < RECOVERY <= TAIL < STOP")
    operations = (("WRITE0", "WRITE0_START", "WRITE0_END"), ("CONTROL", "CONTROL_READ_START", "CONTROL_READ_END"), ("WRITE1", "WRITE1_START", "WRITE1_END"), ("READ", "FINAL_READ_START", "FINAL_READ_END"))
    for operation, start_key, end_key in operations:
        width = times[end_key] - times[start_key]
        for signal in ("WL", "BL", "SE"):
            rise_key = f"{operation}_" + signal + "_RISE"
            fall_key = f"{operation}_" + signal + "_FALL"
            rise = time_ps(required(values, rise_key), rise_key)
            fall = time_ps(required(values, fall_key), fall_key)
            if rise < 0 or fall < 0 or width - rise - fall <= 0:
                raise RuntimeError(f"{operation} {signal}: rise/fall leave no positive plateau")
    for key in STIMULUS_KEYS - set(TIME_KEYS) - {"DT", "STOP"}:
        parse_number(required(values, key), key)
    params = dict(values)
    params.update({"MODE": mode, "MASKS": masks, "NAME": name, "CASE_ID": ""})
    params["windows"] = dynamic_windows(times)
    params["time_ps"] = times
    return params


def dynamic_windows(times: dict[str, float]) -> dict[str, list[float]]:
    return {
        "idle_0_50": [times["IDLE_START"], times["IDLE_END"]],
        "write0_50_61": [times["WRITE0_START"], times["WRITE0_END"]],
        "settle0_61_70": [times["WRITE0_END"], times["CONTROL_READ_START"]],
        "zero_read_control_70_81": [times["CONTROL_READ_START"], times["CONTROL_READ_END"]],
        "settle1_81_90": [times["CONTROL_READ_END"], times["WRITE1_START"]],
        "write1_90_101": [times["WRITE1_START"], times["WRITE1_END"]],
        "settle_101_110": [times["WRITE1_END"], times["FINAL_READ_START"]],
        "final_read_110_121": [times["FINAL_READ_START"], times["FINAL_READ_END"]],
        "recovery_121_130": [times["FINAL_READ_END"], times["RECOVERY_END"]],
        "tail_150_200": [times["TAIL_START"], times["STOP"]],
        "whole_0_200": [times["IDLE_START"], times["STOP"]],
    }


def change_rows(values: dict[str, str], reference: dict[str, str]) -> list[dict[str, str]]:
    rows = []
    for key, current in values.items():
        if key in {"NAME", "MODE", "MASKS"} or key not in reference or key == "CANONICAL_BVM_SOURCE_SHA256":
            continue
        if current != reference[key]:
            rows.append({"key": key, "from": reference[key], "to": current, "section": "circuit" if key in CIRCUIT_KEYS else "stimulus" if key in STIMULUS_KEYS else "other"})
    return rows


def next_case_id() -> str:
    numbers = []
    for path in (SERIES / "runs").iterdir() if (SERIES / "runs").is_dir() else []:
        match = re.match(r"^U(\d{3})(?:_|$)", path.name)
        if match:
            numbers.append(int(match.group(1)))
    return f"U{max(numbers, default=0) + 1:03d}"


def source_points(params: dict[str, str], mask: str, index: int, signal: str) -> list[tuple[float, float]]:
    active = mask[index - 1] == "1"
    stages = [
        ("WRITE0", "WRITE0_START", "WRITE0_END", f"WRITE0_{signal}_AMP", f"WRITE0_{signal}_RISE", f"WRITE0_{signal}_FALL", True),
        ("CONTROL", "CONTROL_READ_START", "CONTROL_READ_END", f"CONTROL_{signal}_AMP", f"CONTROL_{signal}_RISE", f"CONTROL_{signal}_FALL", True),
        ("WRITE1", "WRITE1_START", "WRITE1_END", f"WRITE1_{signal}_AMP", f"WRITE1_{signal}_RISE", f"WRITE1_{signal}_FALL", True),
        ("READ", "FINAL_READ_START", "FINAL_READ_END", f"READ_{signal}_AMP", f"READ_{signal}_RISE", f"READ_{signal}_FALL", active),
    ]
    points: list[tuple[float, float]] = [(time_ps(params["IDLE_START"], "IDLE_START"), 0.0)]
    for _name, start_key, end_key, amp_key, rise_key, fall_key, enabled in stages:
        start = time_ps(params[start_key], start_key)
        end = time_ps(params[end_key], end_key)
        rise = time_ps(params[rise_key], rise_key)
        fall = time_ps(params[fall_key], fall_key)
        amp = parse_number(params[amp_key], amp_key) if enabled else 0.0
        points.extend(((start, 0.0), (start + rise, amp), (end - fall, amp), (end, 0.0)))
    points.append((time_ps(params["STOP"], "STOP"), 0.0))
    normalized: list[tuple[float, float]] = []
    for point in sorted(points, key=lambda item: item[0]):
        if normalized and abs(normalized[-1][0] - point[0]) < 1e-12 and abs(normalized[-1][1] - point[1]) < 1e-30:
            continue
        normalized.append(point)
    return normalized


def stimulus_text(params: dict[str, str], mask: str) -> str:
    lines = [f"* GENERATED user case stimulus; mask={mask}; {legacy.BIT_ORDER}", "* Timing is generated from USER_CASE.env; analysis windows use the same snapshot."]
    for index in range(1, 5):
        for signal in ("WL", "BL", "SE"):
            values = []
            for time_value, current in source_points(params, mask, index, signal):
                values.extend((format_time(time_value), format_current(current)))
            lines.append(f"I_{signal}{index} 0 {signal}{index} pwl(" + " ".join(values) + ")")
    return "\n".join(lines) + "\n"


def render_case_sources(case_root: Path, params: dict[str, Any]) -> dict[str, Path]:
    source_dir = case_root / "snapshot" / "sources"
    source_dir.mkdir(parents=True, exist_ok=False)
    sources: dict[str, Path] = {}
    for role, source in (("JJ_MODEL", legacy.JJ_SOURCE), ("JTL", legacy.JTL_SOURCE)):
        target = source_dir / source.name
        shutil.copy2(source, target)
        sources[role] = target
    target = source_dir / "bvm_tunable.cir"
    target.write_text(legacy.render_bvm(params), encoding="utf-8")
    sources["BVM"] = target
    if params["MODE"] == "closed":
        target = source_dir / "bq_tunable.cir"
        target.write_text(legacy.render_qb(params), encoding="utf-8")
        sources["QB"] = target
    return sources


def render_one(case_root: Path, params: dict[str, Any], sources: dict[str, Path], mask: str) -> dict[str, Any]:
    mode = params["MODE"]
    run_id = f"{mode.upper()}_N{mask.count('1')}_{mask}"
    run_dir = case_root / "cases" / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    stimulus_path = run_dir / "stimulus.inc"
    stimulus_path.write_text(stimulus_text(params, mask), encoding="utf-8")
    deck_text = legacy.render_deck(mode, params, sources, stimulus_path, run_dir)
    deck_path = run_dir / "actual_deck.cir"
    deck_path.write_text(deck_text, encoding="utf-8")
    (run_dir / "deck.cir").write_text(deck_text, encoding="utf-8")
    raw_path = run_dir / "raw.csv"
    command = [str(REPO / "build" / "josim-cli"), "-a", "1", "-o", str(raw_path), str(deck_path)]
    started = now(); clock = time.monotonic()
    completed = subprocess.run(command, cwd=run_dir, capture_output=True, text=True, check=False)
    runtime = time.monotonic() - clock; finished = now()
    (run_dir / "stdout.txt").write_text(completed.stdout, encoding="utf-8")
    (run_dir / "stderr.txt").write_text(completed.stderr, encoding="utf-8")
    (run_dir / "run.log").write_text("\n".join((f"experiment={SERIES.name}", f"run_id={run_id}", f"started_at={started}", f"finished_at={finished}", f"runtime_seconds={runtime:.6f}", f"command={shlex.join(command)}", f"exit_code={completed.returncode}", "")), encoding="utf-8")
    if completed.returncode != 0 or not raw_path.is_file() or raw_path.stat().st_size == 0:
        raise RuntimeError(f"JoSIM failed for {run_id}; raw/deck/log preserved at {run_dir}")
    headers = legacy.read_header(raw_path)
    manifest = legacy.write_signal_manifest(run_dir, mode, params, headers)
    metadata = {"run_id": run_id, "mode": mode, "mask": mask, "parameters": params, "windows": params["windows"], "config_changes": params["config_changes"], "command": command, "started_at": started, "finished_at": finished, "runtime_seconds": runtime, "execution_status": "RUN_PASS", "solver": {"path": legacy.repo_rel(REPO / "build" / "josim-cli"), "sha256": legacy.sha256(REPO / "build" / "josim-cli"), "version": subprocess.check_output([str(REPO / "build" / "josim-cli"), "--version"], text=True).strip()}, "deck": {"path": legacy.repo_rel(deck_path), "sha256": legacy.sha256(deck_path)}, "stimulus": {"path": legacy.repo_rel(stimulus_path), "sha256": legacy.sha256(stimulus_path)}, "raw": {"path": legacy.repo_rel(raw_path), "sha256": legacy.sha256(raw_path), "bytes": raw_path.stat().st_size, "headers": len(headers)}, "signal_manifest": manifest}
    write_json(run_dir / "metadata.json", metadata)
    return metadata


def dry_run(params: dict[str, Any], changes: list[dict[str, str]], case_id: str, preview: str, qb_preview: str | None = None) -> None:
    print("NEW CASE")
    print(f"{case_id}_{params['NAME']}")
    print("\nMODE")
    print(params["MODE"].upper())
    print("\nMASKS")
    print(" / ".join(f"N{mask.count('1')}" for mask in params["MASKS"]))
    print("\nCIRCUIT CHANGES")
    circuit = [row for row in changes if row["section"] == "circuit"]
    print("\n".join(f"{row['key']:<18} {row['from']} -> {row['to']}" for row in circuit) or "none")
    print("\nSTIMULUS CHANGES")
    stimulus = [row for row in changes if row["section"] == "stimulus"]
    print("\n".join(f"{row['key']:<18} {row['from']} -> {row['to']}" for row in stimulus) or "none")
    print("\nWINDOWS")
    for name, window in params["windows"].items():
        print(f"{name:<24} [{window[0]:g}, {window[1]:g}) ps")
    print(f"\nPREVIEW: generated BVM/stimulus validation PASS ({len(preview.splitlines())} stimulus lines)")
    if qb_preview is not None:
        print(f"PREVIEW: rendered QB snapshot validation PASS ({len(qb_preview.splitlines())} netlist lines)")
    print("No solve executed.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run or preview one USER_CASE.env BVM candidate")
    parser.add_argument("--config", default=str(USER_CONFIG))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--set", action="append", default=[], metavar="KEY=VALUE", help="temporary dry-run override; may be repeated")
    args = parser.parse_args()
    config_path = Path(args.config).resolve()
    values = load_env(config_path)
    for override in args.set:
        if "=" not in override:
            raise RuntimeError(f"--set requires KEY=VALUE, got {override!r}")
        key, value = override.split("=", 1)
        values[key] = value
    reference = load_env(REFERENCE_CONFIG)
    if values.get("SWEEP_ENABLED", "no").strip().lower() == "yes":
        from sweep_candidate import execute_sweep
        return execute_sweep(values, reference, args)
    params = validate(values, reference)
    changes = change_rows(values, reference)
    params["config_changes"] = changes
    case_id = next_case_id()
    # Rendering a temporary BVM/stimulus is part of dry-run validation and does not touch the repository.
    with tempfile.TemporaryDirectory(prefix="bvm_user_preview_") as temp:
        preview_root = Path(temp)
        preview_bvm = preview_root / "bvm_tunable.cir"
        preview_bvm.write_text(legacy.render_bvm(params), encoding="utf-8")
        preview_qb_text = None
        if params["MODE"] == "closed":
            preview_qb = preview_root / "bq_tunable.cir"
            preview_qb_text = legacy.render_qb(params)
            preview_qb.write_text(preview_qb_text, encoding="utf-8")
            if "{{" in preview_qb.read_text(encoding="utf-8"):
                raise RuntimeError("unresolved QB marker in preview")
        preview = stimulus_text(params, params["MASKS"][0])
        if "{{" in preview_bvm.read_text(encoding="utf-8"):
            raise RuntimeError("unresolved BVM marker in preview")
    if args.dry_run:
        dry_run(params, changes, case_id, preview, preview_qb_text)
        return 0
    # A physical run is allowed only for a new U case and only after all validation above.
    legacy_hashes = json.loads(LEGACY_HASHES.read_text(encoding="utf-8"))
    for path_text, expected in legacy_hashes.items():
        path = REPO / path_text
        if sha256(path) != expected:
            raise RuntimeError(f"LEGACY_RAW_CHANGED: {path_text}")
    case_root = SERIES / "runs" / f"{case_id}_{params['NAME']}"
    if case_root.exists():
        raise RuntimeError(f"refusing to overwrite existing generated case: {case_root}")
    params["CASE_ID"] = case_root.name
    parent = legacy.git_snapshot()
    case_root.mkdir(parents=True, exist_ok=False)
    (case_root / "config_snapshot.env").write_text(config_path.read_text(encoding="utf-8"), encoding="utf-8")
    stimulus_snapshot = "# Stimulus snapshot generated from USER_CASE.env\n" + "\n".join(f"{key}={values[key]}" for key in sorted(STIMULUS_KEYS | set(TIME_KEYS) | {"DT", "STOP", "MASKS", "MODE", "NAME"}) if key in values) + "\n"
    (case_root / "stimulus_snapshot.env").write_text(stimulus_snapshot, encoding="utf-8")
    sources = render_case_sources(case_root, params)
    source_records = [{"role": role, "path": legacy.repo_rel(path), "sha256": sha256(path), "bytes": path.stat().st_size} for role, path in sources.items()]
    by_role = {record["role"]: record for record in source_records}
    user_case_record = {"path": legacy.repo_rel(USER_CONFIG), "sha256": sha256(USER_CONFIG)}
    effective_config_record = {"path": legacy.repo_rel(config_path), "sha256": sha256(config_path)}
    source_manifest = {"schema": "bvm-rloop-user-case-source-manifest-v1", "created_at": now(), "parent": parent, "case_id": case_root.name, "canonical_bvm_reference": {"path": legacy.repo_rel(CANONICAL_BVM), "sha256": sha256(CANONICAL_BVM)}, "sources": source_records, "bvm_rendered_snapshot": by_role.get("BVM"), "qb_rendered_snapshot": by_role.get("QB") if params["MODE"] == "closed" else None, "jj_model_snapshot": by_role.get("JJ_MODEL"), "jtl_snapshot": by_role.get("JTL"), "user_config": effective_config_record, "user_case_config": user_case_record, "reference_config": {"path": legacy.repo_rel(REFERENCE_CONFIG), "sha256": sha256(REFERENCE_CONFIG)}, "config_changes": changes}
    write_json(case_root / "source_manifest.json", source_manifest)
    records = []
    for mask in params["MASKS"]:
        records.append(render_one(case_root, params, sources, mask))
    # Preserve a representative root deck/stimulus while per-mask copies remain authoritative.
    first_run = case_root / "cases" / records[0]["run_id"]
    shutil.copy2(first_run / "actual_deck.cir", case_root / "actual_deck.cir")
    shutil.copy2(first_run / "stimulus.inc", case_root / "stimulus.inc")
    case_manifest = {"schema": "bvm-rloop-user-case-v1", "case_id": case_root.name, "name": params["NAME"], "parameters": params, "windows": params["windows"], "parent": parent, "source_manifest": {"path": legacy.repo_rel(case_root / "source_manifest.json"), "sha256": sha256(case_root / "source_manifest.json")}, "run_order": [record["run_id"] for record in records], "physical_solve_count": len(records), "config_changes": changes, "scientific_interpretation_performed": False, "automatic_follow_up": False}
    write_json(case_root / "case_manifest.json", case_manifest)
    write_json(case_root / "provenance.json", {"schema": "bvm-rloop-user-case-provenance-v1", "case_id": case_root.name, "parent": parent, "run_order": [record["run_id"] for record in records], "runs": {record["run_id"]: record for record in records}, "config_changes": changes, "scientific_interpretation_performed": False, "automatic_follow_up": False})
    subprocess.run([sys.executable, str(SERIES / "scripts" / "user_analyze.py"), "--case-root", str(case_root)], cwd=REPO, check=True)
    subprocess.run([sys.executable, str(SERIES / "scripts" / "user_plot.py"), "--case-root", str(case_root)], cwd=REPO, check=True)
    latest = SERIES / "LATEST_REVIEW.html"
    latest.write_text(f"<!doctype html><html><head><meta charset='utf-8'><meta http-equiv='refresh' content='0; url=plots/{case_root.name}/review.html'><title>Latest BVM review</title></head><body><p><a href='plots/{case_root.name}/review.html'>Latest review: {case_root.name}</a></p></body></html>\n", encoding="utf-8")
    print(f"CASE COMPLETE\n\n{case_root.name}\n\nRuns:\n" + "\n".join(f"{record['run_id']} PASS" for record in records) + f"\n\nReview:\nLATEST_REVIEW.html\n\nRaw:\n{legacy.repo_rel(case_root)}/")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
