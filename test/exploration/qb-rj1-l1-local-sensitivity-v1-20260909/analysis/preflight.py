#!/usr/bin/env python3
"""Machine preflight for the five-run local QB parameter experiment.

This script performs only setup/deck/source checks. It never invokes JoSIM.
"""

from __future__ import annotations

import difflib
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
TEMPLATE = EXP / "inputs/array_fixture_template.cir"
FIXTURE_RAW = EXP / "inputs/historical_array_reference_raw.csv"
BVM = EXP / "inputs/bvm_jm2_connected.cir"
JJMIT = EXP / "inputs/jjmit.cir"
BQ_SOURCE = EXP / "inputs/BQ_source.cir"
BQ_PARAM = EXP / "inputs/BQ_parameterized.cir"
JTL = EXP / "inputs/jtl2.cir"
SOLVER = REPO / "build/josim-cli"

EXPECTED_HEAD = "08c7320bdd6e871d9b9536dcd27f5e8b2b0d5604"
EXPECTED = {
    "fixture_template": "85227538d48d69251f4276b94b28adfc83cd25f95aa6609fa9eb2375c873f1cf",
    "fixture_raw": "8543abc6d7a7d276c0bfa3159a4d3d37d569200e5fa30082466e66df8ab24dc2",
    "bvm": "0093a45cc3910448b484d8bd004c6df8c22358bacc8b3ed5e23912dcab805d54",
    "jjmit": "19862d1fd1f1f44dfa1523848d7d3b5e2594a6c5da8fdd80144b449e5312a336",
    "bq_source": "f3dcbf5f9bb3898faf5194b5f7c4771df3fa1ed16150496de4b52cb6f7256dfd",
    "jtl": "ffd31f8eda2a86ca0133342be1ce678831b7237a53911eda046d2bff8454855a",
    "solver": "48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2",
}

RUNS = {
    "nominal": {"run_id": "NOMINAL", "rj1": "12", "l1": "2p", "rj1_value": 12.0, "l1_value": 2.0},
    "l1_down": {"run_id": "L1_DOWN", "rj1": "12", "l1": "1.9p", "rj1_value": 12.0, "l1_value": 1.9},
    "l1_up": {"run_id": "L1_UP", "rj1": "12", "l1": "2.1p", "rj1_value": 12.0, "l1_value": 2.1},
    "rj1_up_05": {"run_id": "RJ1_UP_05", "rj1": "12.5", "l1": "2p", "rj1_value": 12.5, "l1_value": 2.0},
    "rj1_up_10": {"run_id": "RJ1_UP_10", "rj1": "13", "l1": "2p", "rj1_value": 13.0, "l1_value": 2.0},
}

OLD_INCLUDE_BLOCK = (
    ".include ../../../../../circuits/models/jjmit.cir\n"
    ".include ../../../bvmsim-jm2-connected-single-ab-v1-20260903/variants/bvm_jm2_connected.cir\n"
    ".include ../../../../../BVMSim/BQ.cir\n"
    ".include ../../../../../BVMSim/library_josim/jtl2.cir"
)
LOCAL_INCLUDE_BLOCK = (
    ".include ../../inputs/jjmit.cir\n"
    ".include ../../inputs/bvm_jm2_connected.cir\n"
    ".include ../../inputs/BQ_parameterized.cir\n"
    ".include ../../inputs/jtl2.cir"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def write_once(path: Path, content: str) -> None:
    if path.exists():
        if path.read_text(encoding="utf-8") == content:
            return
        raise RuntimeError(f"refusing to overwrite existing preflight artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def active_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip() and not line.strip().startswith("*")]


def normalize_deck(text: str, rj1: str, l1: str) -> str:
    parameter_block = f".param RJ1_VALUE={rj1}\n.param L1_VALUE={l1}\n"
    expected_block = parameter_block + LOCAL_INCLUDE_BLOCK
    if text.count(expected_block) != 1:
        raise RuntimeError("parameter/include block is not unique")
    return text.replace(expected_block, OLD_INCLUDE_BLOCK, 1)


def source_active_lines(text: str) -> list[str]:
    return active_lines(text)


def check_bq_parameterization(failures: list[str]) -> dict[str, object]:
    source = source_active_lines(BQ_SOURCE.read_text(encoding="utf-8"))
    derived = source_active_lines(BQ_PARAM.read_text(encoding="utf-8"))
    expected_derived = []
    for line in source:
        if line == "L1 2 3 2p":
            expected_derived.append("L1 2 3 {L1_VALUE}")
        elif line == "RJ1 2 0 12":
            expected_derived.append("RJ1 2 0 {RJ1_VALUE}")
        else:
            expected_derived.append(line)
    ok = derived == expected_derived
    if not ok:
        failures.append("bq_parameterization: active BQ differs beyond L1/RJ1 placeholders")
    return {
        "status": "PASS" if ok else "FAIL",
        "source_sha256": sha256(BQ_SOURCE),
        "derived_sha256": sha256(BQ_PARAM),
        "active_source_lines": len(source),
        "active_derived_lines": len(derived),
        "only_registered_placeholders": ok,
    }


def check_deck(directory: str, spec: dict[str, object], nominal_text: str | None, failures: list[str]) -> dict[str, object]:
    path = EXP / "runs" / directory / "deck.cir"
    result: dict[str, object] = {
        "run_id": spec["run_id"],
        "path": path.relative_to(REPO).as_posix(),
        "exists": path.is_file(),
        "sha256": sha256(path) if path.is_file() else None,
        "parameter": {"RJ1_VALUE": spec["rj1"], "L1_VALUE": spec["l1"]},
        "failures": [],
    }
    local_failures: list[str] = []
    if not path.is_file():
        local_failures.append("deck missing")
        failures.extend(f"{spec['run_id']}.{item}" for item in local_failures)
        result["failures"] = local_failures
        result["status"] = "FAIL"
        return result
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    expected_param_rj = f".param RJ1_VALUE={spec['rj1']}"
    expected_param_l1 = f".param L1_VALUE={spec['l1']}"
    if lines.count(expected_param_rj) != 1:
        local_failures.append("RJ1 parameter line mismatch")
    if lines.count(expected_param_l1) != 1:
        local_failures.append("L1 parameter line mismatch")
    if sum(line.startswith(".param ") for line in lines) != 2:
        local_failures.append("unexpected parameter line count")
    normalized = normalize_deck(text, str(spec["rj1"]), str(spec["l1"]))
    if normalized != TEMPLATE.read_text(encoding="utf-8"):
        local_failures.append("normalized deck differs from frozen ARRAY fixture template")
    if nominal_text is not None:
        nominal_lines = nominal_text.splitlines()
        variant_lines = text.splitlines()
        if len(nominal_lines) != len(variant_lines):
            local_failures.append("line count differs from NOMINAL")
        else:
            changed = [
                {"line": index + 1, "nominal": nominal_lines[index], "variant": variant_lines[index]}
                for index in range(len(nominal_lines))
                if nominal_lines[index] != variant_lines[index]
            ]
            allowed = [] if spec["run_id"] == "NOMINAL" else [
                {"line": next(i + 1 for i, line in enumerate(nominal_lines) if line.startswith(".param RJ1_VALUE=")) if spec["rj1"] != "12" else next(i + 1 for i, line in enumerate(nominal_lines) if line.startswith(".param L1_VALUE=")),
                 "nominal": ".param RJ1_VALUE=12" if spec["rj1"] != "12" else ".param L1_VALUE=2p",
                 "variant": expected_param_rj if spec["rj1"] != "12" else expected_param_l1}
            ]
            if changed != allowed:
                local_failures.append(f"NOMINAL diff is not exactly one registered parameter line: {changed}")
            result["nominal_diff"] = {"changed_lines": changed, "allowed_lines": allowed, "status": "PASS" if changed == allowed else "FAIL"}
    active = active_lines(text)
    if active.count(".tran 0.1p 200p") != 1:
        local_failures.append(".tran is not exactly .tran 0.1p 200p")
    if text.count("XBQ1 QBIN QBOUT BQ") != 1:
        local_failures.append("QB instance mismatch")
    if len(re.findall(r"(?im)^XJTL1_[1-6]\s+\S+\s+\S+\s+jtl$", text)) != 6:
        local_failures.append("JTL instance count mismatch")
    if len(re.findall(r"(?im)^R_TERM\s+JTL6_OUT\s+0\s+10$", text)) != 1:
        local_failures.append("termination mismatch")
    bvm_lines = [line for line in active if re.match(r"^XBVM[1-4]\s+", line, re.IGNORECASE)]
    if len(bvm_lines) != 4 or any(not line.endswith("COMMON_SL BVM") for line in bvm_lines):
        local_failures.append("BVM shared COMMON_SL topology mismatch")
    jsl_lines = [line for line in active if re.match(r"^B_JSL[1-8]\s+", line, re.IGNORECASE)]
    if len(jsl_lines) != 8 or any("jjmit area=5.0" not in line for line in jsl_lines):
        local_failures.append("JSL count/model/area mismatch")
    if "B_JSL8 JSL_NODE7 QBIN jjmit area=5.0" not in text:
        local_failures.append("JSL8 QBIN boundary mismatch")
    required_includes = set(LOCAL_INCLUDE_BLOCK.splitlines())
    if not required_includes.issubset(set(active)):
        local_failures.append("local include closure mismatch")
    run_dir = path.parent
    if (run_dir / "raw.csv").exists() or (run_dir / "run.log").exists() or (run_dir / "metadata.json").exists():
        local_failures.append("run output already exists; refusing overwrite")
    failures.extend(f"{spec['run_id']}.{item}" for item in local_failures)
    result["failures"] = local_failures
    result["status"] = "PASS" if not local_failures else "FAIL"
    return result


def main() -> int:
    failures: list[str] = []
    required = (TEMPLATE, FIXTURE_RAW, BVM, JJMIT, BQ_SOURCE, BQ_PARAM, JTL, SOLVER)
    for path in required:
        if not path.is_file():
            failures.append(f"missing_source:{path}")
    source_hashes = {
        "fixture_template": sha256(TEMPLATE) if TEMPLATE.is_file() else None,
        "fixture_raw": sha256(FIXTURE_RAW) if FIXTURE_RAW.is_file() else None,
        "bvm": sha256(BVM) if BVM.is_file() else None,
        "jjmit": sha256(JJMIT) if JJMIT.is_file() else None,
        "bq_source": sha256(BQ_SOURCE) if BQ_SOURCE.is_file() else None,
        "bq_parameterized": sha256(BQ_PARAM) if BQ_PARAM.is_file() else None,
        "jtl": sha256(JTL) if JTL.is_file() else None,
        "solver": sha256(SOLVER) if SOLVER.is_file() else None,
    }
    for name, expected in EXPECTED.items():
        if source_hashes.get(name) != expected:
            failures.append(f"source_hash:{name}:{source_hashes.get(name)} != {expected}")
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()
    if head != EXPECTED_HEAD:
        failures.append(f"HEAD:{head} != {EXPECTED_HEAD}")

    bq_check = check_bq_parameterization(failures) if BQ_SOURCE.is_file() and BQ_PARAM.is_file() else {"status": "FAIL"}
    nominal_text = (EXP / "runs/nominal/deck.cir").read_text(encoding="utf-8") if (EXP / "runs/nominal/deck.cir").is_file() else None
    deck_checks = {}
    for directory, spec in RUNS.items():
        deck_checks[spec["run_id"]] = check_deck(directory, spec, nominal_text, failures)

    if set(p.name for p in (EXP / "runs").iterdir() if p.is_dir()) != set(RUNS):
        failures.append("run_directory_set differs from exact five-run matrix")
    if not FIXTURE_RAW.is_file() or (FIXTURE_RAW.is_file() and sum(1 for _ in FIXTURE_RAW.open("rb")) < 2):
        failures.append("fixture raw is empty")

    status = "PASS" if not failures and all(item["status"] == "PASS" for item in deck_checks.values()) and bq_check["status"] == "PASS" else "FAIL"
    timestamp = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    diff_artifact = {
        "schema": "qb-rj1-l1-local-sensitivity-deck-diff-qa-v1",
        "experiment_id": EXP.name,
        "created_at_local": timestamp,
        "baseline": "runs/nominal/deck.cir",
        "allowed_variant_change": "exactly one registered .param line for the relevant single parameter",
        "runs": deck_checks,
        "status": status,
        "failures": failures,
    }
    preflight = {
        "schema": "qb-rj1-l1-local-sensitivity-preflight-v1",
        "experiment_id": EXP.name,
        "created_at_local": timestamp,
        "status": status,
        "head": head,
        "expected_head": EXPECTED_HEAD,
        "source_hashes": source_hashes,
        "expected_source_hashes": EXPECTED,
        "bq_parameterization": bq_check,
        "deck_diff_qa": diff_artifact,
        "exact_authorized_run_ids": [spec["run_id"] for spec in RUNS.values()],
        "exact_authorized_physical_solve_count": 5,
        "solver_invoked_by_preflight": False,
        "failures": failures,
    }
    write_once(EXP / "analysis/deck_diff_qa.json", json.dumps(diff_artifact, indent=2, ensure_ascii=False) + "\n")
    write_once(EXP / "analysis/preflight.json", json.dumps(preflight, indent=2, ensure_ascii=False) + "\n")
    md = f"""# PREFLIGHT — QB RJ1/L1 local sensitivity\n\nThis experiment is governed by docs/EXPERIMENT_CONTRACT.md.\n\n- Status: **{status}**\n- Preflight time: `{timestamp}`\n- HEAD at preflight: `{head}`\n- Role: `Experimental Operator + Evidence Packager`\n- Study phase: `EXPLORATORY / QUICK`; this is a registered local sensitivity matrix, not an optimization sweep.\n\n## Exact authorized physical solves\n\n| run | RJ1 | L1 | purpose |\n|---|---:|---:|---|\n| NOMINAL | 12.0 ohm | 2.0 pH | new internal matched baseline |\n| L1_DOWN | 12.0 ohm | 1.9 pH | L1 decrease intervention |\n| L1_UP | 12.0 ohm | 2.1 pH | opposite-direction L1 control |\n| RJ1_UP_05 | 12.5 ohm | 2.0 pH | small RJ1 increase |\n| RJ1_UP_10 | 13.0 ohm | 2.0 pH | larger RJ1 increase |\n\nExactly five physical solves are authorized. No combined RJ1+L1 point, other mask, other parameter, timestep/solver sensitivity or automatic follow-up is authorized.\n\n## Frozen fixture and input closure\n\n- Fixture: `test/exploration/bvmsim-jm2-single-vs-4bvm-shared-sl-v1-20260907/runs/array/deck.cir`, SHA-256 `{source_hashes.get('fixture_template')}`; historical array reference raw SHA-256 `{source_hashes.get('fixture_raw')}`.\n- BVM: historical JM2-connected variant, SHA-256 `{source_hashes.get('bvm')}`; canonical BVM is not used.\n- JJ model: `circuits/models/jjmit.cir`, SHA-256 `{source_hashes.get('jjmit')}`.\n- QB base: `BVMSim/BQ.cir`, SHA-256 `{source_hashes.get('bq_source')}`. The local derived parameterized copy is `{source_hashes.get('bq_parameterized')}` and changes only active `L1`/`RJ1` to registered parameter references.\n- JTL: `BVMSim/library_josim/jtl2.cir`, SHA-256 `{source_hashes.get('jtl')}`.\n- Solver: `build/josim-cli`, SHA-256 `{source_hashes.get('solver')}`.\n- Topology: four BVMs on `COMMON_SL`; 8 x `jjmit area=5.0` JSL; QB; six JTL stages; `R_TERM=10 ohm`.\n\n## Frozen stimulus and windows\n\nStored-1111 protocol; BVM1 final READ mask 1000; BVM1 `WL1=+100uA`, `BL1=0`, `SE1=+100uA`; BVM2--4 are quiet at final READ. Rise/fall are 1 ps and the plateau is 9 ps. `.tran 0.1p 200p` is fixed. Windows are half-open and use actual stored timestamps: `PRE_FINAL=[101,110) ps`, `EARLY_TRIGGER=[110,116) ps`, `FULL_READ=[110,121) ps`, `TAIL=[121,200) ps`, `FULL_FINAL=[110,200) ps`.\n\n## Probes and analysis ceiling\n\nThe deck retains full registered BVM, COMMON_SL, 8-JSL, QB and all-six-stage JTL probes, including P/V/I where requested. Missing columns emitted by the solver are recorded as `UNKNOWN`; no signal is fabricated. Metrics use actual-grid trapezoid integration. Raw phase is radians; independent unwrap followed by explicit division by `2*pi` is display/derived arithmetic only. Phase displacement, voltage area, `I>Ic`, or a pulse-like trace is not an SFQ count.\n\n## Mechanical gate\n\n- Parameterized deck normalized text must equal the frozen ARRAY fixture template.\n- Each variant may differ from NOMINAL in exactly one registered `.param` line.\n- Raw outputs must not exist before execution; raw files are never overwritten.\n- No interpolation, resampling, smoothing, time shift, alignment or parameter tuning is permitted.\n\nMachine records: `analysis/preflight.json` and `analysis/deck_diff_qa.json`.\n\n## Decision\n\n{"Preflight passed. The five registered physical solves may execute directly." if status == "PASS" else "Preflight failed. Do not invoke the solver; preserve this failed preflight."}\n\nFinal state after the exact matrix and QA is `AWAITING_USER_REVIEW`.\n"""
    write_once(EXP / "PREFLIGHT.md", md)
    print(json.dumps({"status": status, "failures": failures, "solver_invoked": False, "record": "analysis/preflight.json"}, ensure_ascii=False))
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
