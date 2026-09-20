#!/usr/bin/env python3
"""Prepare, strictly reuse, and execute the registered B013 crossover matrix."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

SERIES = Path(__file__).resolve().parents[1]
REPO = next(path for path in (SERIES, *SERIES.parents) if (path / ".git").exists())
BATCH = SERIES / "batches" / "B013_high_current_low_rsl_crossover"
CONFIG_DIR = BATCH / "configs"
USER_CONFIG = SERIES / "USER_CASE.env"
sys.path.insert(0, str(SERIES / "scripts"))
import run_b012 as helper  # noqa: E402


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def load_env(path: Path) -> dict[str, str]:
    return helper.platform.load_env(path)


def set_value(text: str, key: str, value: str) -> str:
    import re
    pattern = re.compile(rf"(?m)^{re.escape(key)}=.*$")
    if not pattern.search(text):
        raise RuntimeError(f"missing config key: {key}")
    return pattern.sub(f"{key}={value}", text, count=1)


def present_at_commit(case_root: Path, commit: str) -> bool:
    rel = case_root.resolve().relative_to(REPO.resolve()).as_posix()
    return subprocess.run(["git", "cat-file", "-e", f"{commit}:{rel}/case_manifest.json"], cwd=REPO, capture_output=True, check=False).returncode == 0


def strict_match(case_root: Path, params: dict[str, Any], run_id: str) -> tuple[bool, list[str]]:
    reasons = []
    manifest_path = case_root / "case_manifest.json"
    if not manifest_path.is_file():
        return False, ["case_manifest_missing"]
    manifest = json.loads(manifest_path.read_text())
    if helper.fingerprint(manifest.get("parameters", {})) != helper.fingerprint(params):
        reasons.append("parameter_fingerprint_mismatch")
    for name, expected in helper.source_hashes(params).items():
        path = case_root / "snapshot" / "sources" / name
        if not path.is_file() or sha256(path) != expected:
            reasons.append(f"source_hash_mismatch:{name}")
    run = case_root / "cases" / run_id
    if not (run / "raw.csv").is_file() or not (run / "stimulus.inc").is_file():
        reasons.append(f"run_missing:{run_id}")
    else:
        raw_qa = json.loads((case_root / "qa" / "raw_qa.json").read_text())
        row = next((x for x in raw_qa.get("rows", []) if x.get("run_id") == run_id), None)
        if not row or row.get("status") != "PASS":
            reasons.append(f"raw_qa_not_pass:{run_id}")
        expected = helper.platform.stimulus_text(params, run_id.rsplit("_", 1)[-1]).encode()
        if sha256(run / "stimulus.inc") != hashlib.sha256(expected).hexdigest():
            reasons.append(f"stimulus_hash_mismatch:{run_id}")
    if not (case_root / "qa" / "plot_qa.json").is_file() or json.loads((case_root / "qa" / "plot_qa.json").read_text()).get("status") != "PASS":
        reasons.append("plot_qa_not_pass")
    return not reasons, reasons


def find_reuse(params: dict[str, Any], run_id: str, base_commit: str) -> Path | None:
    for case in sorted((SERIES / "runs").glob("U*_*")):
        if present_at_commit(case, base_commit) and strict_match(case, params, run_id)[0]:
            return case
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    plan = json.loads((BATCH / "B013_PLAN.json").read_text())
    base_commit = plan["parent_head"]
    template = USER_CONFIG.read_text(encoding="utf-8")
    items = plan["variants"]
    prepared = []
    for item in items:
        text = template
        for key, value in (("NAME", item["name"]), ("MODE", item["mode"]), ("MASKS", item["masks"]), ("SWEEP_ENABLED", "no"), ("SWEEP_KEY", "NONE"), ("SWEEP_VALUES", ""), ("SWEEP_REUSE_EXISTING", "no")):
            text = set_value(text, key, value)
        for key, value in item["changes"].items():
            text = set_value(text, key, value)
        config = CONFIG_DIR / f"{item['name']}.env"
        config.write_text(text, encoding="utf-8")
        params = helper.platform.validate(load_env(config), load_env(helper.platform.REFERENCE_CONFIG))
        run_ids = [f"{item['mode'].upper()}_N{mask.count('1')}_{mask}" for mask in item["masks"].split(",")]
        refs = {}
        for run_id in run_ids:
            if item.get("reference"):
                case = SERIES / "runs" / item["reference"]
                if not present_at_commit(case, base_commit) or not strict_match(case, params, run_id)[0]:
                    raise RuntimeError(f"registered reference failed strict match: {item['variant']} {run_id}")
                refs[run_id] = case
            else:
                refs[run_id] = find_reuse(params, run_id, base_commit)
        prepared.append({"item": item, "config": config, "params": params, "run_ids": run_ids, "refs": refs})
    if args.dry_run:
        for entry in prepared:
            print(json.dumps({"variant": entry["item"]["variant"], "name": entry["item"]["name"], "reuse": {run: (case.name if case else None) for run, case in entry["refs"].items()}, "new_physical_solve_count": 0 if all(entry["refs"].values()) else len(entry["run_ids"])}, ensure_ascii=False))
        return 0
    points = []
    for entry in prepared:
        item, config = entry["item"], entry["config"]
        refs = entry["refs"]
        if not all(refs.values()):
            named = sorted((SERIES / "runs").glob(f"U*_{item['name']}"))
            if named:
                case = named[0]
                if not all(strict_match(case, entry["params"], run)[0] for run in entry["run_ids"]):
                    raise RuntimeError(f"existing named case failed strict verification: {item['name']}")
            else:
                completed = subprocess.run([sys.executable, str(SERIES / "scripts" / "try_candidate.py"), "--config", str(config)], cwd=REPO, text=True, capture_output=True, check=False)
                (BATCH / "logs").mkdir(parents=True, exist_ok=True)
                stem=item["variant"].replace("/", "_")
                (BATCH / "logs" / f"{stem}.stdout.txt").write_text(completed.stdout)
                (BATCH / "logs" / f"{stem}.stderr.txt").write_text(completed.stderr)
                if completed.returncode != 0:
                    raise RuntimeError(f"solve failed for {item['variant']}: {completed.stderr[-2000:]}")
                candidates = sorted((SERIES / "runs").glob(f"U*_{item['name']}"))
                if len(candidates) != 1:
                    raise RuntimeError(f"expected one generated case for {item['variant']}, found {candidates}")
                case = candidates[0]
                if not all(strict_match(case, entry["params"], run)[0] for run in entry["run_ids"]):
                    raise RuntimeError(f"post-run strict verification failed: {item['variant']}")
            refs = {run: case for run in entry["run_ids"]}
        for run_id, case in refs.items():
            raw_qa = json.loads((case / "qa" / "raw_qa.json").read_text())
            row = next(x for x in raw_qa["rows"] if x["run_id"] == run_id)
            points.append({"group": item["group"], "variant": item["variant"], "name": item["name"], "case_id": case.name, "run_id": run_id, "source_type": "REUSED_EXISTING" if present_at_commit(case, base_commit) else "NEW_PHYSICAL", "config_path": str(config.relative_to(SERIES)), "raw_path": row["path"], "raw_sha256": row["sha256"], "raw_qa_status": row["status"]})
    reused=sum(point["source_type"] == "REUSED_EXISTING" for point in points)
    new=len(points)-reused
    manifest={"schema":"bvm-b013-execution-v1","batch_id":"B013_high_current_low_rsl_crossover","status":"PASS","logical_variant_count":len(items),"logical_point_count":len(points),"reused_point_count":reused,"new_physical_solve_count":new,"scientific_interpretation_performed":False,"scientific_review_status":"SCIENTIFIC_REVIEW_REQUIRED","qb_jtl_modified":False,"automatic_closed_followup":False,"points":points}
    (BATCH/'B013_EXECUTION_MANIFEST.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps({k:manifest[k] for k in ('status','logical_variant_count','logical_point_count','reused_point_count','new_physical_solve_count','scientific_review_status')},ensure_ascii=False,indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
