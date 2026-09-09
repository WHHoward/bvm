#!/usr/bin/env python3
"""Raw-only artifact QA for the five registered runs."""

from __future__ import annotations

import hashlib
import json
import math
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
from bvmtools.raw import read_csv  # noqa: E402


RUNS = {
    "NOMINAL": "nominal",
    "L1_DOWN": "l1_down",
    "L1_UP": "l1_up",
    "RJ1_UP_05": "rj1_up_05",
    "RJ1_UP_10": "rj1_up_10",
}
WINDOWS_PS = {
    "PRE_FINAL": (101.0, 110.0),
    "EARLY_TRIGGER": (110.0, 116.0),
    "FULL_READ": (110.0, 121.0),
    "TAIL": (121.0, 200.0),
    "FULL_FINAL": (110.0, 200.0),
}


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def expected_probes() -> list[str]:
    probes: list[str] = []
    for instance in range(1, 5):
        h = f"XBVM{instance}"
        probes.extend(f"{kind}({jj}|{h})" for jj in ("B_JM1", "B_JM2", "B_JS1", "B_JS2") for kind in ("P", "V", "I"))
        probes.extend(
            f"{kind}({branch}|{h})"
            for branch in ("L_M1", "L_M2", "L_M3", "L_PM", "R_JM1", "L_S1", "L_S2", "R_S", "L_S3", "R_SE", "L_PSE", "L_PSL", "R_SL", "L_SL")
            for kind in ("I", "V")
        )
        probes.extend((f"I(I_WL{instance})", f"I(I_BL{instance})", f"I(I_SE{instance})"))
    probes.append("V(COMMON_SL)")
    for index in range(1, 9):
        probes.extend((f"P(B_JSL{index})", f"V(B_JSL{index})", f"I(B_JSL{index})"))
    probes.extend(("V(QBIN)", "V(QBOUT)"))
    for branch in ("LIN", "L1", "L2", "L3", "RJ1", "RJ2", "IB"):
        probes.extend((f"I({branch}|XBQ1)", f"V({branch}|XBQ1)"))
    # JoSIM emits the BQ BJs instance label as BJS in this fixture's CSV.
    for jj in ("BJS", "BJ1", "BJ2"):
        probes.extend((f"P({jj}|XBQ1)", f"V({jj}|XBQ1)", f"I({jj}|XBQ1)"))
    for stage in range(1, 7):
        h = f"XJTL1_{stage}"
        probes.extend(
            (f"P(B01|{h})", f"V(B01|{h})", f"I(B01|{h})", f"P(B02|{h})", f"V(B02|{h})", f"I(B02|{h})", f"V(JTL{stage}_OUT)")
        )
    probes.append("I(R_TERM)")
    return probes


def write_or_update(path: Path, record: dict[str, object]) -> None:
    content = json.dumps(record, indent=2, ensure_ascii=False) + "\n"
    if path.exists():
        old = json.loads(path.read_text(encoding="utf-8"))
        if old.get("pre_analysis_sha256") != record.get("pre_analysis_sha256"):
            raise RuntimeError(f"refusing to change pre-analysis raw identity: {path}")
        path.write_text(content, encoding="utf-8")
    else:
        path.write_text(content, encoding="utf-8")


def main() -> int:
    stage = sys.argv[1] if len(sys.argv) > 1 else "pre"
    if stage not in {"pre", "post"}:
        raise SystemExit("usage: raw_qa.py [pre|post]")
    current_head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()
    probe_list = expected_probes()
    cases: dict[str, object] = {}
    pre_hashes: dict[str, str] = {}
    post_hashes: dict[str, str] = {}
    overall_artifact_valid = True
    any_missing_probe = False
    for run_id, directory in RUNS.items():
        path = EXP / "runs" / directory / "raw.csv"
        if not path.is_file():
            raise RuntimeError(f"missing raw: {path}")
        raw_hash = digest(path)
        trace = read_csv(path)
        qa = trace.qa()
        missing = sorted(set(probe_list) - set(trace.headers))
        duplicate = trace.duplicate_columns
        dt = trace.dt
        dt_ps = [value * 1e12 for value in dt]
        times_ps = [value * 1e12 for value in trace.time]
        grid_hash = hashlib.sha256("\n".join(f"{value:.17g}" for value in trace.time).encode()).hexdigest()
        case = {
            "run_id": run_id,
            "raw_path": str(path),
            "raw_sha256": raw_hash,
            "bytes": path.stat().st_size,
            "sample_count": trace.sample_count,
            "header_count": len(trace.headers),
            "time_start_s": trace.time[0],
            "time_end_s": trace.time[-1],
            "time_start_ps": times_ps[0],
            "time_end_ps": times_ps[-1],
            "strictly_increasing_time": qa["strictly_increasing_time"],
            "dt_min_ps": min(dt_ps) if dt_ps else None,
            "dt_max_ps": max(dt_ps) if dt_ps else None,
            "uniform_time_grid": qa["uniform_time_grid"],
            "stored_time_grid_sha256": grid_hash,
            "finite_values": qa["nan_inf_status"] == "PASS",
            "duplicate_columns": duplicate,
            "required_probe_presence": {"status": "PASS" if not missing else "UNKNOWN", "missing": missing},
            "unit_sign_convention": {
                "time": "seconds in raw CSV; display ps",
                "current": "A; display uA where requested",
                "voltage": "V; display mV where requested",
                "phase": "P(...) raw radians",
                "direction": "raw JoSIM branch/node labels retained; no sign correction",
                "transformations": "none",
            },
        }
        cases[run_id] = case
        pre_hashes[run_id] = raw_hash
        if missing:
            any_missing_probe = True
        if not case["strictly_increasing_time"] or not case["finite_values"] or duplicate:
            overall_artifact_valid = False
        if stage == "post":
            post_hashes[run_id] = digest(path)
            if post_hashes[run_id] != raw_hash:
                overall_artifact_valid = False

    if stage == "post":
        target = EXP / "analysis/raw_qa.json"
        if not target.is_file():
            raise RuntimeError("pre-stage raw_qa.json is missing")
        prior = json.loads(target.read_text(encoding="utf-8"))
        if prior.get("pre_analysis_sha256") != pre_hashes:
            raise RuntimeError("pre-analysis raw hashes no longer match")
        record = prior
        record["post_analysis_sha256"] = post_hashes
        record["raw_unchanged_pre_to_post"] = pre_hashes == post_hashes
        record["post_analysis_timestamp_local"] = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
        record["artifact_validity"] = "VALID" if overall_artifact_valid and record["raw_unchanged_pre_to_post"] else "INVALID"
        write_or_update(target, record)
    else:
        record = {
            "schema": "qb-rj1-l1-local-sensitivity-raw-qa-v1",
            "experiment_id": EXP.name,
            "stage": "PRE_ANALYSIS",
            "created_at_local": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
            "head": current_head,
            "cases": cases,
            "pre_analysis_sha256": pre_hashes,
            "post_analysis_sha256": None,
            "raw_unchanged_pre_to_post": None,
            "overall_required_probe_status": "UNKNOWN" if any_missing_probe else "PASS",
            "artifact_validity": "VALID" if overall_artifact_valid else "INVALID",
            "missing_probe_is_not_fabricated": True,
            "no_solver_invoked_by_qa": True,
        }
        write_or_update(EXP / "analysis/raw_qa.json", record)
    print(json.dumps({"status": "PASS" if record["artifact_validity"] == "VALID" else "INVALID", "stage": stage, "case_count": len(RUNS), "missing_probe_cases": sum(bool(case["required_probe_presence"]["missing"]) for case in cases.values())}, ensure_ascii=False))
    return 0 if record["artifact_validity"] == "VALID" else 1


if __name__ == "__main__":
    raise SystemExit(main())
