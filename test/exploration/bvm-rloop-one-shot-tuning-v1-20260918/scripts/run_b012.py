#!/usr/bin/env python3
"""Prepare, strictly reuse, and execute the registered B012 matrix."""

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
BATCH = SERIES / "batches" / "B012_high_se_js_area_operating_map"
CONFIG_DIR = BATCH / "configs"
USER_CONFIG = SERIES / "USER_CASE.env"
MASK_PASSIVE = ("PASSIVE_N1_0001", "PASSIVE_N4_1111")
MASK_CLOSED = ("CLOSED_N1_0001", "CLOSED_N2_0011", "CLOSED_N4_1111")
FINGERPRINT_KEYS = (
    "MODE", "JM1_AREA", "JM2_AREA", "RJM1", "RJM2", "LM1", "LM2", "LM3", "LPM",
    "JS1_AREA", "JS2_AREA", "RSH_JS1", "RSH_JS2", "LS1", "LS2", "LS3", "RS", "LPSL", "RSL", "LSL",
    "RBL", "LPBL", "RWL", "LPWL", "RSE", "LPSE", "DT", "STOP", "IDLE_START", "IDLE_END",
    "WRITE0_START", "WRITE0_END", "WRITE0_WL_AMP", "WRITE0_BL_AMP", "WRITE0_SE_AMP", "WRITE0_WL_RISE", "WRITE0_WL_FALL", "WRITE0_BL_RISE", "WRITE0_BL_FALL", "WRITE0_SE_RISE", "WRITE0_SE_FALL",
    "CONTROL_READ_START", "CONTROL_READ_END", "CONTROL_WL_AMP", "CONTROL_BL_AMP", "CONTROL_SE_AMP", "CONTROL_WL_RISE", "CONTROL_WL_FALL", "CONTROL_BL_RISE", "CONTROL_BL_FALL", "CONTROL_SE_RISE", "CONTROL_SE_FALL",
    "WRITE1_START", "WRITE1_END", "WRITE1_WL_AMP", "WRITE1_BL_AMP", "WRITE1_SE_AMP", "WRITE1_WL_RISE", "WRITE1_WL_FALL", "WRITE1_BL_RISE", "WRITE1_BL_FALL", "WRITE1_SE_RISE", "WRITE1_SE_FALL",
    "FINAL_READ_START", "FINAL_READ_END", "READ_WL_AMP", "READ_BL_AMP", "READ_SE_AMP", "READ_WL_RISE", "READ_WL_FALL", "READ_BL_RISE", "READ_BL_FALL", "READ_SE_RISE", "READ_SE_FALL",
)

sys.path.insert(0, str(SERIES / "scripts"))
import run_candidate as legacy  # noqa: E402
import try_candidate as platform  # noqa: E402


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def load_env(path: Path) -> dict[str, str]:
    return platform.load_env(path)


def set_value(text: str, key: str, value: str) -> str:
    pattern = re.compile(rf"(?m)^{re.escape(key)}=.*$")
    if not pattern.search(text):
        raise RuntimeError(f"missing config key: {key}")
    return pattern.sub(f"{key}={value}", text, count=1)


def variant(group: str, label: str, name: str, mode: str, masks: str, changes: dict[str, str], reference: str | None = None) -> dict[str, Any]:
    return {"group": group, "variant": label, "name": name, "mode": mode, "masks": masks, "changes": changes, "reference": reference}


def definitions() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    # Track A references and symmetric grid.
    items.extend([
        variant("A0", "A0-REF-100", "b012_a0_ref_100", "passive", "0001,1111", {"CONTROL_SE_AMP": "100u", "READ_SE_AMP": "100u", "JS1_AREA": "0.52", "JS2_AREA": "0.74"}, "U040_b010_b0_baseline"),
        variant("A0", "A0-REF-110", "b012_a0_ref_110", "passive", "0001,1111", {"CONTROL_SE_AMP": "110u", "READ_SE_AMP": "110u", "JS1_AREA": "0.52", "JS2_AREA": "0.74"}, "U045_b010_g5_se_110"),
    ])
    for se in (100, 110, 120, 130):
        areas = (0.74, 0.80, 0.90, 1.00)
        for area in areas:
            token = f"{area:.2f}".rstrip("0").rstrip(".").replace(".", "p")
            items.append(variant("A1", f"A1-{se}-{area:g}", f"b012_a1_se{se}_a{token}", "passive", "0001,1111", {"CONTROL_SE_AMP": f"{se}u", "READ_SE_AMP": f"{se}u", "JS1_AREA": f"{area:.3f}", "JS2_AREA": f"{area:.3f}"}))
    # Track A asymmetric JS2-protection grid.
    asymmetric = ((110, .74, .80), (110, .74, .90), (110, .80, .90), (110, .80, 1.00), (110, .90, 1.00),
                  (120, .74, .80), (120, .74, .90), (120, .80, .90), (120, .80, 1.00), (120, .90, 1.00),
                  (130, .74, .80), (130, .74, .90), (130, .80, .90), (130, .80, 1.00), (130, .90, 1.00))
    for se, js1, js2 in asymmetric:
        t1 = f"{js1:.2f}".replace(".", "p")
        t2 = f"{js2:.2f}".replace(".", "p")
        items.append(variant("A2", f"A2-{se}-{js1:g}-{js2:g}", f"b012_a2_se{se}_js{t1}_{t2}", "passive", "0001,1111", {"CONTROL_SE_AMP": f"{se}u", "READ_SE_AMP": f"{se}u", "JS1_AREA": f"{js1:.3f}", "JS2_AREA": f"{js2:.3f}"}))
    # Track B closed RSL route.
    for rsl, ref in ((12, "U039_closed_cons_12_20_full"), (10, None), (8, None), (6, None)):
        items.append(variant("B", f"B-RSL-{rsl}", f"b012_b_rsl_{rsl}_closed", "closed", "0001,0011,1111", {"RSL": f"{rsl}.0" if rsl == 12 else str(rsl)}, ref))
    # Track C closed LM3 route.
    items.append(variant("C", "C-LM3-8.7", "b012_c_lm3_8p7_closed", "closed", "0001,0011,1111", {"LM3": "8.7p"}))
    return items


def normalized(value: Any, key: str) -> Any:
    if key == "MODE":
        return str(value).lower() if value is not None else None
    if value is None:
        return None
    if str(value).upper() == "OPEN":
        return "OPEN"
    try:
        return round(platform.parse_number(str(value), key), 30)
    except RuntimeError:
        return str(value)


def fingerprint(params: dict[str, Any]) -> dict[str, Any]:
    return {key: normalized(params.get(key), key) for key in FINGERPRINT_KEYS}


def source_hashes(params: dict[str, Any]) -> dict[str, str]:
    return {
        "bvm_tunable.cir": hashlib.sha256(legacy.render_bvm(params).encode()).hexdigest(),
        "jjmit.cir": sha256(legacy.JJ_SOURCE), "bq_parameterized_v1.cir": sha256(legacy.QB_SOURCE), "jtl2.cir": sha256(legacy.JTL_SOURCE),
    }


def prepare_configs(items: list[dict[str, Any]]) -> list[Path]:
    template = USER_CONFIG.read_text(encoding="utf-8")
    paths = []
    for item in items:
        text = template
        for key, value in (("NAME", item["name"]), ("MODE", item["mode"]), ("MASKS", item["masks"]), ("SWEEP_ENABLED", "no"), ("SWEEP_KEY", "NONE"), ("SWEEP_VALUES", ""), ("SWEEP_REUSE_EXISTING", "no")):
            text = set_value(text, key, value)
        for key, value in item["changes"].items():
            text = set_value(text, key, value)
        path = CONFIG_DIR / f"{item['name']}.env"
        path.write_text(text, encoding="utf-8")
        paths.append(path)
    return paths


def present_at_commit(case_root: Path, commit: str) -> bool:
    rel = case_root.resolve().relative_to(REPO.resolve()).as_posix()
    return subprocess.run(["git", "cat-file", "-e", f"{commit}:{rel}/case_manifest.json"], cwd=REPO, capture_output=True, check=False).returncode == 0


def strict_match(case_root: Path, params: dict[str, Any], run_id: str) -> tuple[bool, list[str]]:
    reasons = []
    manifest_path = case_root / "case_manifest.json"
    if not manifest_path.is_file():
        return False, ["case_manifest_missing"]
    manifest = json.loads(manifest_path.read_text())
    actual = manifest.get("parameters", {})
    if fingerprint(actual) != fingerprint(params):
        reasons.append("parameter_fingerprint_mismatch")
    source_expect = source_hashes(params)
    for name, expected in source_expect.items():
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
        expected_stimulus = platform.stimulus_text(params, run_id.rsplit("_", 1)[-1]).encode()
        if sha256(run / "stimulus.inc") != hashlib.sha256(expected_stimulus).hexdigest():
            reasons.append(f"stimulus_hash_mismatch:{run_id}")
    if not (case_root / "qa" / "plot_qa.json").is_file() or json.loads((case_root / "qa" / "plot_qa.json").read_text()).get("status") != "PASS":
        reasons.append("plot_qa_not_pass")
    return not reasons, reasons


def find_reuse(params: dict[str, Any], run_id: str, base_commit: str) -> tuple[Path | None, list[str]]:
    rejected = []
    for case in sorted((SERIES / "runs").glob("U*_*")):
        if not present_at_commit(case, base_commit):
            continue
        ok, reasons = strict_match(case, params, run_id)
        if ok:
            return case, []
        if reasons:
            rejected.append(f"{case.name}:{','.join(reasons)}")
    return None, rejected


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    parent = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()
    items = definitions()
    config_paths = prepare_configs(items)
    # Persist the machine-readable registration before solving.
    plan = {"schema": "bvm-b012-registration-v1", "batch_id": "B012_high_se_js_area_operating_map", "parent_head": parent, "variant_count": len(items), "logical_point_count": sum(len(item["masks"].split(",")) for item in items), "variants": [{**item, "config_path": str(path.relative_to(SERIES))} for item, path in zip(items, config_paths)]}
    (BATCH / "B012_PLAN.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n")
    planned = []
    for item, config_path in zip(items, config_paths):
        params = platform.validate(load_env(config_path), load_env(platform.REFERENCE_CONFIG))
        mask_ids = [f"{item['mode'].upper()}_N{mask.count('1')}_{mask}" for mask in item["masks"].split(",")]
        refs = {}
        for run_id in mask_ids:
            case = None
            rejected = []
            if item.get("reference"):
                reference_case = SERIES / "runs" / item["reference"]
                if present_at_commit(reference_case, parent):
                    ok, reference_reasons = strict_match(reference_case, params, run_id)
                    if not ok:
                        raise RuntimeError(f"registered reference failed strict match: {item['variant']} {run_id} {reference_reasons}")
                    case = reference_case
                else:
                    raise RuntimeError(f"registered reference missing at parent: {item['reference']}")
            else:
                case, rejected = find_reuse(params, run_id, parent)
            refs[run_id] = {"case": case, "rejected": rejected}
        planned.append({"item": item, "config": config_path, "params": params, "refs": refs})
    if args.dry_run:
        for entry in planned:
            print(json.dumps({"variant": entry["item"]["variant"], "name": entry["item"]["name"], "reuse": {k: (v["case"].name if v["case"] else None) for k, v in entry["refs"].items()}, "new_physical_solve_count": 0 if all(v["case"] for v in entry["refs"].values()) else len(entry["refs"])}, ensure_ascii=False))
        return 0
    records = []
    for entry in planned:
        item, config, refs = entry["item"], entry["config"], entry["refs"]
        if not all(ref["case"] for ref in refs.values()):
            named = sorted((SERIES / "runs").glob(f"U*_{item['name']}"))
            if not named:
                completed = subprocess.run([sys.executable, str(SERIES / "scripts" / "try_candidate.py"), "--config", str(config)], cwd=REPO, text=True, capture_output=True, check=False)
                (BATCH / "logs").mkdir(parents=True, exist_ok=True)
                stem=item["variant"].replace("/", "_")
                (BATCH / "logs" / f"{stem}.stdout.txt").write_text(completed.stdout)
                (BATCH / "logs" / f"{stem}.stderr.txt").write_text(completed.stderr)
                if completed.returncode != 0:
                    raise RuntimeError(f"solve failed for {item['variant']}: {completed.stderr[-2000:]}")
                named = sorted((SERIES / "runs").glob(f"U*_{item['name']}"))
            if len(named) != 1:
                raise RuntimeError(f"expected one generated case for {item['variant']}, found {named}")
            case = named[0]
            params = entry["params"]
            refs = {run_id: {"case": case, "rejected": []} for run_id in refs}
            for run_id in refs:
                ok, reasons = strict_match(case, params, run_id)
                if not ok:
                    raise RuntimeError(f"post-run strict verification failed for {item['variant']} {run_id}: {reasons}")
        for run_id, ref in refs.items():
            raw_qa=json.loads((ref["case"]/'qa/raw_qa.json').read_text())
            row=next(x for x in raw_qa['rows'] if x['run_id']==run_id)
            records.append({"group": item["group"], "variant": item["variant"], "name": item["name"], "case_id": ref["case"].name, "run_id": run_id, "source_type": "REUSED_EXISTING" if present_at_commit(ref["case"], parent) else "NEW_PHYSICAL", "config_path": str(config.relative_to(SERIES)), "raw_path": row['path'], "raw_sha256": row['sha256'], "raw_qa_status": row['status']})
    reused=sum(x['source_type']=='REUSED_EXISTING' for x in records)
    new=len(records)-reused
    manifest={"schema":"bvm-b012-execution-v1","batch_id":"B012_high_se_js_area_operating_map","status":"PASS","logical_variant_count":len(items),"logical_point_count":len(records),"reused_point_count":reused,"new_physical_solve_count":new,"scientific_interpretation_performed":False,"scientific_review_status":"SCIENTIFIC_REVIEW_REQUIRED","qb_jtl_modified":False,"automatic_closed_followup":False,"points":records}
    (BATCH/'B012_EXECUTION_MANIFEST.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps({k:manifest[k] for k in ('status','logical_variant_count','logical_point_count','reused_point_count','new_physical_solve_count','scientific_review_status')},ensure_ascii=False,indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
