#!/usr/bin/env python3
"""Mechanical preflight for the passive capture stage and replay contract."""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
SOURCE_MANIFEST = EXP / "source/source_manifest.json"
HEAD_AT_SETUP = "510cb59ebaa237268980133435aa2ff32468c935"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def now_local() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def write_once(path: Path, content: str) -> None:
    if path.exists():
        if path.read_text(encoding="utf-8") == content:
            return
        raise RuntimeError(f"refusing to overwrite existing artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def netlist_lines(path: Path) -> list[str]:
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith(("*", "."))
    ]


def passive_check(name: str, expected_bvm: int, endpoint: str, instances: tuple[int, ...]) -> dict[str, object]:
    path = EXP / "runs" / name / "deck.cir"
    lines = netlist_lines(path)
    bvm = [line for line in lines if line.endswith("BVM")]
    jsl = [line for line in lines if line.startswith("B_JSL")]
    controls = [line for line in lines if line.startswith("I_")]
    failures: list[str] = []
    if len(bvm) != expected_bvm:
        failures.append(f"BVM count {len(bvm)} != {expected_bvm}")
    if len(jsl) != 8:
        failures.append(f"JSL count {len(jsl)} != 8")
    if any("area=5.0" not in line or "jjmit" not in line for line in jsl):
        failures.append("JSL model/area mismatch")
    if not jsl or not jsl[-1].split()[2] == "0":
        failures.append("JSL8 does not terminate at ground")
    if any(token in line.lower() for line in lines for token in ("bq", "jtl", "r_term")):
        failures.append("forbidden QB/JTL/termination element found")
    if any(f"XBVM{i} " not in " ".join(bvm) for i in instances):
        failures.append("BVM instance set mismatch")
    if expected_bvm == 4 and any(endpoint not in line for line in bvm):
        failures.append("array BVM endpoint is not COMMON_SL")
    if expected_bvm == 1 and endpoint not in bvm[0]:
        failures.append("single BVM endpoint is not SL1")
    if len(controls) != 3 * len(instances):
        failures.append("control-source count mismatch")
    tran = [line for line in path.read_text(encoding="utf-8").splitlines() if line.lower().startswith(".tran")]
    if tran != [".tran 0.1p 200p"]:
        failures.append(f"timing line mismatch: {tran}")
    return {
        "status": "PASS" if not failures else "FAIL",
        "path": path.relative_to(REPO).as_posix(),
        "deck_sha256": sha256(path),
        "bvm_count": len(bvm),
        "jsl_count": len(jsl),
        "jsl8_to_ground": bool(jsl and jsl[-1].split()[2] == "0"),
        "controls": len(controls),
        "has_qb": any("bq" in line.lower() for line in lines),
        "has_jtl": any("jtl" in line.lower() for line in lines),
        "has_termination": any("r_term" in line.lower() for line in lines),
        "failures": failures,
    }


def main() -> int:
    current_head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()
    manifest = json.loads(SOURCE_MANIFEST.read_text(encoding="utf-8"))
    source_failures: list[str] = []
    if current_head != HEAD_AT_SETUP:
        source_failures.append(f"HEAD changed since preregistration: {current_head}")
    for key in ("bvm_variant", "jjmit", "qb", "jtl", "solver"):
        record = manifest["sources"][key]
        path = REPO / record["path"]
        if sha256(path) != record["sha256"]:
            source_failures.append(f"source hash changed: {key}")
    single = passive_check("single_passive", 1, "SL1", (1,))
    array = passive_check("array_passive", 4, "COMMON_SL", (1, 2, 3, 4))
    failures = source_failures + single["failures"] + array["failures"]
    record = {
        "schema": "jm2-passive-capture-replay-topology-preflight-v1",
        "experiment_id": EXP.name,
        "created_at_local": now_local(),
        "stage": "PASSIVE_BEFORE_CAPTURE",
        "status": "PASS" if not failures else "FAIL",
        "head_at_setup": HEAD_AT_SETUP,
        "head_at_preflight": current_head,
        "source_hashes_unchanged": not source_failures,
        "passive": {"single_passive": single, "array_passive": array},
        "replay_contract": {
            "status": "REGISTERED_POST_CAPTURE_MECHANICAL_CHECK_REQUIRED",
            "contains_bvm": False,
            "contains_jsls": False,
            "qb_source": manifest["sources"]["qb"],
            "jtl_source": manifest["sources"]["jtl"],
            "termination_ohm": 10.0,
            "pwl_source": "captured I(B_JSL8) exact stored timestamp/value pairs",
        },
        "failures": failures,
    }
    write_once(EXP / "analysis/topology_preflight.json", json.dumps(record, indent=2, ensure_ascii=False) + "\n")
    markdown = f"""# PREFLIGHT — passive capture + current replay\n\n- Status: **{record['status']}**\n- Preflight time: `{record['created_at_local']}`\n- HEAD at setup/preflight: `{HEAD_AT_SETUP}` / `{current_head}`\n- Scope: passive capture first; replay decks are generated only from the resulting exact raw `I(B_JSL8)` snapshots.\n\n## Passive fixtures\n\n| case | BVM | JSL | JSL8 endpoint | QB/JTL/termination | result |\n|---|---:|---:|---|---|---|\n| `SINGLE_PASSIVE` | 1 | 8 × `jjmit area=5.0` | GND | absent | `{single['status']}` |\n| `ARRAY_PASSIVE` | 4 → `COMMON_SL` | 8 × `jjmit area=5.0` | GND | absent | `{array['status']}` |\n\nThe BVM input is the historical JM2-connected variant; the canonical BVM is not an input. All passive decks use `.tran 0.1p 200p` and the registered WRITE0 → ZERO_STATE_READ_CONTROL → WRITE1 → selective READ history.\n\n## Replay contract\n\nReplay decks will contain only `I_REPLAY 0 QBIN`, the exact `BVMSim/BQ.cir`, the exact six-stage `BVMSim/library_josim/jtl2.cir`, and `R_TERM ... 10`. The source snapshots will retain every passive raw timestamp/current pair without interpolation, smoothing, fitting, scaling, shifting, rectification or truncation. A separate post-capture replay preflight will verify the generated decks and source fidelity before either replay run.\n\nMachine record: `analysis/topology_preflight.json`.\n"""
    write_once(EXP / "PREFLIGHT.md", markdown)
    print(json.dumps({"status": record["status"], "record": "analysis/topology_preflight.json", "failures": failures}, ensure_ascii=False))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
