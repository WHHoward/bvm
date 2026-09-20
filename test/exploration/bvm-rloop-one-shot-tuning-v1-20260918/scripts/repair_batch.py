#!/usr/bin/env python3
"""Repair a stopped batch analysis from immutable existing point artifacts."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

SERIES = Path(__file__).resolve().parents[1]
REPO = next(path for path in (SERIES, *SERIES.parents) if (path / ".git").exists())
sys.path.insert(0, str(SERIES / "scripts"))
import sweep_candidate as sweep  # noqa: E402
import try_candidate as platform  # noqa: E402

POINT_CASES = {
    "0.58": "U002_js1_ic_sweep_js1_area_0p58",
    "0.64": "U003_js1_ic_sweep_js1_area_0p64",
    "0.70": "U001_js1_area_70",
    "0.74": "A002",
    "0.80": "U004_js1_ic_sweep_js1_area_0p80",
    "0.86": "U005_js1_ic_sweep_js1_area_0p86",
    "0.92": "U006_js1_ic_sweep_js1_area_0p92",
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Repair a stopped sweep batch without solving")
    parser.add_argument("--batch", default="B002_js1_ic_sweep")
    args = parser.parse_args()
    values = platform.load_env(platform.USER_CONFIG)
    reference = platform.load_env(platform.REFERENCE_CONFIG)
    config, points, _ = sweep.sweep_setup(values, reference)
    batch_root = SERIES / "batches" / args.batch
    if not batch_root.is_dir():
        raise RuntimeError(f"batch directory missing: {batch_root}")
    point_records=[]; flat=[]; new_cases=[]; reused=[]
    for point in points:
        value=point["value"]
        case_name=POINT_CASES.get(value)
        if not case_name:
            raise RuntimeError(f"no immutable case mapping registered for {value}")
        case_root=SERIES / "runs" / case_name
        params=dict(values); params[config["key"]]=value; params["MASKS"]="1111"; params=platform.validate(params,reference)
        verification=sweep.verify_existing(case_root,params,value)
        if verification.get("status") != "REUSE":
            raise RuntimeError(f"strict artifact verification failed for {value}: {verification.get('reasons')}")
        raw_path=case_root / "cases" / "PASSIVE_N4_1111" / "raw.csv"
        qa=sweep.raw_qa_for(case_root,"PASSIVE_N4_1111") or {}
        record={"value":value,"source_type":"REUSED_EXISTING" if case_name in {"U001_js1_area_70","A002"} else "NEW_PHYSICAL","source_case":case_name,"case_path":case_name,"run_id":"PASSIVE_N4_1111","physical_solve_new":case_name not in {"U001_js1_area_70","A002"},"raw_sha256":verification["raw_sha256"],"raw_qa_status":"PASS","grid_status":verification.get("grid_status") or qa.get("grid_status")}
        if record["physical_solve_new"]: new_cases.append(case_name)
        else: reused.append(record)
        point_records.append(record)
        row=sweep.load_point_metrics({**record,"params":params},config)
        row["case_review_path"]=f"../../plots/{case_name}/review.html"
        row["raw_path"]=f"../../runs/{case_name}/cases/PASSIVE_N4_1111/raw.csv"
        row["config_path"]=f"../../runs/{case_name}/config_snapshot.env"
        flat.append(row)
    fields=sorted({key for row in flat for key in row})
    with (batch_root/"BATCH_SUMMARY.csv").open("w",newline="",encoding="utf-8") as stream:
        writer=csv.DictWriter(stream,fieldnames=fields); writer.writeheader(); writer.writerows(flat)
    sweep.write_batch_review(batch_root,config,flat,reused,new_cases,[])
    qa={"schema":"bvm-rloop-sweep-batch-qa-v1","status":"PASS","logical_points":len(points),"reused_points":len(reused),"new_physical_solve_count":len(new_cases),"failed_points":[],"raw_hashes_rechecked":True,"repair":"analysis-only repair from immutable existing point artifacts"}
    platform.write_json(batch_root/"BATCH_QA.json",qa)
    manifest=json.loads((batch_root/"BATCH_MANIFEST.json").read_text()) if (batch_root/"BATCH_MANIFEST.json").is_file() else {}
    manifest.update({"points":point_records,"qa":qa,"status":"BATCH_COMPLETE_AWAITING_SCIENTIFIC_REVIEW"})
    platform.write_json(batch_root/"BATCH_MANIFEST.json",manifest)
    (SERIES/"LATEST_BATCH_REVIEW.html").write_text(f"<!doctype html><html><head><meta http-equiv='refresh' content='0; url=batches/{args.batch}/BATCH_REVIEW.html'></head><body><a href='batches/{args.batch}/BATCH_REVIEW.html'>{args.batch}</a></body></html>\n",encoding="utf-8")
    print(json.dumps({"status":"PASS","batch":args.batch,"logical_points":len(points),"reused_points":len(reused),"new_physical_solve_count":len(new_cases),"solve_executed":False},ensure_ascii=False,indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
