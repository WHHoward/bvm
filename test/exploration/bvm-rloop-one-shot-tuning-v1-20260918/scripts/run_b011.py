#!/usr/bin/env python3
"""Preflight, strict-reuse audit, and execution driver for B011.

The driver only executes the registered PASSIVE N1/N4 matrix. It records raw
and artifact facts and deliberately does not compute scientific Gate or gain
classifications.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

SERIES = Path(__file__).resolve().parents[1]
REPO = next(path for path in (SERIES, *SERIES.parents) if (path / ".git").exists())
BATCH = SERIES / "batches" / "B011_high_current_operating_region"
CONFIG_DIR = BATCH / "configs"
PLAN = BATCH / "B011_PLAN.json"
USER_CONFIG = SERIES / "USER_CASE.env"
MASKS = ("PASSIVE_N1_0001", "PASSIVE_N4_1111")
FINGERPRINT_KEYS = (
    "MODE", "MASKS", "JM1_AREA", "JM2_AREA", "RJM1", "RJM2", "LM1", "LM2", "LM3", "LPM",
    "JS1_AREA", "JS2_AREA", "RSH_JS1", "RSH_JS2", "LS1", "LS2", "LS3", "RS", "LPSL", "RSL", "LSL",
    "RBL", "LPBL", "RWL", "LPWL", "RSE", "LPSE", "DT", "STOP", "IDLE_START", "IDLE_END",
    "WRITE0_START", "WRITE0_END", "WRITE0_WL_AMP", "WRITE0_BL_AMP", "WRITE0_SE_AMP", "WRITE0_WL_RISE", "WRITE0_WL_FALL", "WRITE0_BL_RISE", "WRITE0_BL_FALL", "WRITE0_SE_RISE", "WRITE0_SE_FALL",
    "CONTROL_READ_START", "CONTROL_READ_END", "CONTROL_WL_AMP", "CONTROL_BL_AMP", "CONTROL_SE_AMP", "CONTROL_WL_RISE", "CONTROL_WL_FALL", "CONTROL_BL_RISE", "CONTROL_BL_FALL", "CONTROL_SE_RISE", "CONTROL_SE_FALL",
    "WRITE1_START", "WRITE1_END", "WRITE1_WL_AMP", "WRITE1_BL_AMP", "WRITE1_SE_AMP", "WRITE1_WL_RISE", "WRITE1_WL_FALL", "WRITE1_BL_RISE", "WRITE1_BL_FALL", "WRITE1_SE_RISE", "WRITE1_SE_FALL",
    "FINAL_READ_START", "FINAL_READ_END", "READ_WL_AMP", "READ_BL_AMP", "READ_SE_AMP", "READ_WL_RISE", "READ_WL_FALL", "READ_BL_RISE", "READ_BL_FALL", "READ_SE_RISE", "READ_SE_FALL",
)
EXPECTED_BASE = {
    "JM1_AREA": "1.2", "JM2_AREA": "1.4", "RJM1": "8", "RJM2": "OPEN",
    "LM1": "12.5p", "LM2": "24.5p", "LM3": "8.5p", "LPM": "0.5p", "JS1_AREA": "0.52", "JS2_AREA": "0.74",
    "RSH_JS1": "12", "RSH_JS2": "20", "LS1": "0.5p", "LS2": "0.5p", "LS3": "0.5p", "RS": "3.0",
    "LPSL": "0.5p", "RSL": "12.0", "LSL": "0.4p", "RBL": "20.0", "LPBL": "0.5p", "RWL": "20.0", "LPWL": "0.5p", "RSE": "20.0", "LPSE": "0.5p",
    "DT": "0.1p", "STOP": "200p", "CONTROL_WL_AMP": "100u", "READ_WL_AMP": "100u", "CONTROL_SE_AMP": "100u", "READ_SE_AMP": "100u",
}

sys.path.insert(0, str(SERIES / "scripts"))
import run_candidate as legacy  # noqa: E402
import try_candidate as platform  # noqa: E402


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_env(path: Path) -> dict[str, str]:
    return platform.load_env(path)


def set_config_value(text: str, key: str, value: str) -> str:
    pattern = re.compile(rf"(?m)^{re.escape(key)}=.*$")
    if not pattern.search(text):
        raise RuntimeError(f"config key missing in template: {key}")
    return pattern.sub(f"{key}={value}", text, count=1)


def flatten_variants(plan: dict[str, Any]) -> list[dict[str, Any]]:
    variants = []
    for group, items in plan["groups"].items():
        for item in items:
            variants.append({"group": group, **item})
    return variants


def prepare_configs(variants: list[dict[str, Any]]) -> list[Path]:
    template = USER_CONFIG.read_text(encoding="utf-8")
    current = load_env(USER_CONFIG)
    mismatches = {key: (current.get(key), value) for key, value in EXPECTED_BASE.items() if current.get(key) != value}
    if mismatches:
        raise RuntimeError(f"current USER_CASE baseline mismatch: {mismatches}")
    paths = []
    for item in variants:
        text = template
        text = set_config_value(text, "NAME", item["name"])
        text = set_config_value(text, "MODE", "passive")
        text = set_config_value(text, "MASKS", "0001,1111")
        text = set_config_value(text, "SWEEP_ENABLED", "no")
        text = set_config_value(text, "SWEEP_KEY", "NONE")
        text = set_config_value(text, "SWEEP_VALUES", "")
        text = set_config_value(text, "SWEEP_REUSE_EXISTING", "no")
        for key, value in item["changes"].items():
            text = set_config_value(text, key, value)
        path = CONFIG_DIR / f"{item['name']}.env"
        path.write_text(text, encoding="utf-8")
        paths.append(path)
    return paths


def expected_params(config_path: Path) -> dict[str, Any]:
    values = load_env(config_path)
    reference = load_env(platform.REFERENCE_CONFIG)
    params = platform.validate(values, reference)
    params["config_changes"] = platform.change_rows(values, reference)
    return params


def fingerprint_params(params: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for key in FINGERPRINT_KEYS:
        value = params.get(key)
        if key == "MASKS":
            normalized[key] = tuple(value or [])
        elif key == "MODE":
            normalized[key] = str(value).lower() if value is not None else None
        elif value is None or str(value).upper() == "OPEN":
            normalized[key] = "OPEN" if value is not None else None
        else:
            try:
                normalized[key] = round(platform.parse_number(str(value), key), 30)
            except RuntimeError:
                normalized[key] = str(value)
    return normalized


def source_hashes(params: dict[str, Any]) -> dict[str, str]:
    bvm_text = legacy.render_bvm(params).encode("utf-8")
    return {
        "bvm_tunable.cir": hashlib.sha256(bvm_text).hexdigest(),
        "jjmit.cir": sha256(legacy.JJ_SOURCE),
        "bq_parameterized_v1.cir": sha256(legacy.QB_SOURCE),
        "jtl2.cir": sha256(legacy.JTL_SOURCE),
    }


def strict_existing_match(case_root: Path, params: dict[str, Any]) -> tuple[bool, list[str], dict[str, Any]]:
    reasons: list[str] = []
    if not (case_root / "case_manifest.json").is_file():
        return False, ["case_manifest_missing"], {}
    manifest = load_json(case_root / "case_manifest.json")
    case_params = manifest.get("parameters", {})
    expected_fp = fingerprint_params(params)
    actual_fp = fingerprint_params(case_params)
    if expected_fp != actual_fp:
        reasons.append("parameter_fingerprint_mismatch")
    if manifest.get("run_order") != list(MASKS):
        reasons.append("mask_order_mismatch")
    raw_qa_path = case_root / "qa" / "raw_qa.json"
    plot_qa_path = case_root / "qa" / "plot_qa.json"
    if not raw_qa_path.is_file() or load_json(raw_qa_path).get("status") != "PASS":
        reasons.append("raw_qa_not_pass")
    if not plot_qa_path.is_file() or load_json(plot_qa_path).get("status") != "PASS":
        reasons.append("plot_qa_not_pass")
    expected_sources = source_hashes(params)
    for filename, expected in expected_sources.items():
        path = case_root / "snapshot" / "sources" / filename
        if not path.is_file() or sha256(path) != expected:
            reasons.append(f"source_hash_mismatch:{filename}")
    for mask in MASKS:
        run = case_root / "cases" / mask
        if not (run / "raw.csv").is_file():
            reasons.append(f"raw_missing:{mask}")
            continue
        expected_stimulus = platform.stimulus_text(params, mask.rsplit("_", 1)[-1]).encode("utf-8")
        if sha256(run / "stimulus.inc") != hashlib.sha256(expected_stimulus).hexdigest():
            reasons.append(f"stimulus_hash_mismatch:{mask}")
    return not reasons, reasons, manifest


def present_at_commit(case_root: Path, commit: str) -> bool:
    rel = case_root.resolve().relative_to(REPO.resolve()).as_posix()
    return subprocess.run(["git", "cat-file", "-e", f"{commit}:{rel}/case_manifest.json"], cwd=REPO, capture_output=True, check=False).returncode == 0


def find_existing(params: dict[str, Any], base_commit: str) -> tuple[Path | None, list[str]]:
    candidates = sorted((SERIES / "runs").glob("U*_*"))
    rejected = []
    for case in candidates:
        if not present_at_commit(case, base_commit):
            continue
        matched, reasons, _ = strict_existing_match(case, params)
        if matched:
            return case, []
        if reasons and case.name.startswith("U"):
            rejected.append(f"{case.name}:{','.join(reasons)}")
    return None, rejected


def case_record(item: dict[str, Any], config_path: Path, case_root: Path, source_type: str) -> dict[str, Any]:
    raw_qa = load_json(case_root / "qa" / "raw_qa.json")
    rows = {row["run_id"]: row for row in raw_qa.get("rows", [])}
    return {
        "group": item["group"], "variant": item["variant"], "name": item["name"], "case_id": case_root.name,
        "case_path": str(case_root.relative_to(SERIES)),
        "source_type": source_type, "config_path": str(config_path.relative_to(SERIES)),
        "runs": [{"run_id": mask, "raw_path": str((case_root / "cases" / mask / "raw.csv").relative_to(SERIES)), "raw_sha256": rows.get(mask, {}).get("sha256"), "raw_qa_status": rows.get(mask, {}).get("status")} for mask in MASKS],
        "physical_solve_count": 0 if source_type == "REUSED_EXISTING" else len(MASKS),
        "raw_qa_status": raw_qa.get("status"), "plot_qa_status": load_json(case_root / "qa" / "plot_qa.json").get("status"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    plan = load_json(PLAN)
    base_commit = plan["preflight_commit"]
    variants = flatten_variants(plan)
    config_paths = prepare_configs(variants)
    planned = []
    for item, config_path in zip(variants, config_paths):
        params = expected_params(config_path)
        existing, rejected = find_existing(params, base_commit)
        named = sorted((SERIES / "runs").glob(f"U*_{item['name']}"))
        completed = None
        for candidate in named:
            matched, _, _ = strict_existing_match(candidate, params)
            if matched and not present_at_commit(candidate, base_commit):
                completed = candidate
                break
        if named and existing is None and completed is None:
            raise RuntimeError(f"existing case name has no strict match: {named[0]}; rejected={rejected[:5]}")
        planned.append({"item": item, "config_path": config_path, "params": params, "existing": existing, "completed": completed, "rejected": rejected})
    if args.dry_run:
        for entry in planned:
            print(json.dumps({"variant": entry["item"]["variant"], "name": entry["item"]["name"], "reuse": entry["existing"].name if entry["existing"] else None, "already_completed": entry["completed"].name if entry["completed"] else None, "new_physical_solve_count": 0 if entry["existing"] or entry["completed"] else 2}, ensure_ascii=False))
        return 0
    records = []
    for entry in planned:
        item, config_path, existing, completed = entry["item"], entry["config_path"], entry["existing"], entry["completed"]
        if existing:
            records.append(case_record(item, config_path, existing, "REUSED_EXISTING"))
            continue
        if completed:
            records.append(case_record(item, config_path, completed, "NEW_PHYSICAL"))
            continue
        completed = subprocess.run([sys.executable, str(SERIES / "scripts" / "try_candidate.py"), "--config", str(config_path)], cwd=REPO, text=True, capture_output=True, check=False)
        (BATCH / "logs").mkdir(parents=True, exist_ok=True)
        (BATCH / "logs" / f"{item['variant'].replace('/', '_')}.stdout.txt").write_text(completed.stdout, encoding="utf-8")
        (BATCH / "logs" / f"{item['variant'].replace('/', '_')}.stderr.txt").write_text(completed.stderr, encoding="utf-8")
        if completed.returncode != 0:
            raise RuntimeError(f"solve failed for {item['variant']}: {completed.stderr[-2000:]}")
        candidates = sorted((SERIES / "runs").glob(f"U*_{item['name']}"))
        if len(candidates) != 1:
            raise RuntimeError(f"expected one generated case for {item['variant']}, found {candidates}")
        matched, reasons, _ = strict_existing_match(candidates[0], entry["params"])
        if not matched:
            raise RuntimeError(f"generated case failed strict post-run verification for {item['variant']}: {reasons}")
        records.append(case_record(item, config_path, candidates[0], "NEW_PHYSICAL"))
    manifest = {"schema": "bvm-b011-execution-v1", "batch_id": plan["batch_id"], "status": "PASS", "logical_variant_count": len(records), "logical_point_count": len(records) * len(MASKS), "reused_point_count": sum(len(MASKS) for record in records if record["source_type"] == "REUSED_EXISTING"), "new_physical_solve_count": sum(record["physical_solve_count"] for record in records), "scientific_interpretation_performed": False, "scientific_review_status": "SCIENTIFIC_REVIEW_REQUIRED", "qb_jtl_modified": False, "variants": records}
    (BATCH / "B011_EXECUTION_MANIFEST.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: manifest[k] for k in ("status", "logical_variant_count", "logical_point_count", "reused_point_count", "new_physical_solve_count", "scientific_review_status")}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
