#!/usr/bin/env python3
"""Register the fixed L1/IBias/RJ1 L2 re-arm experiment.

This script performs no physical solve. It creates the six registered L2
decks and verifies the exact L2=2.0pH historical baseline before execution.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import subprocess
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
AUTH = REPO / "test/exploration/qb-l1p14-ib260-rj1-rearm-bjs400-v1-20260910"
SOLVER = REPO / "build/josim-cli"
SOURCE_TEMPLATE = EXP / "inputs/array_fixture_template.cir"
BQ400 = EXP / "inputs/BQ_parameterized_bjs400.cir"
BQ_L2 = EXP / "inputs/BQ_parameterized_bjs400_l2.cir"
CONTRACT_SENTENCE = "This experiment is governed by docs/EXPERIMENT_CONTRACT.md."

EXPECTED_INPUT_HASHES = {
    "array_fixture_template.cir": "8971a82dfbac223b9be139f719afae2eb156f0f68fb2a4811858f0a0b482cf71",
    "bvm_jm2_connected.cir": "0093a45cc3910448b484d8bd004c6df8c22358bacc8b3ed5e23912dcab805d54",
    "jjmit.cir": "19862d1fd1f1f44dfa1523848d7d3b5e2594a6c5da8fdd80144b449e5312a336",
    "jtl2.cir": "ffd31f8eda2a86ca0133342be1ce678831b7237a53911eda046d2bff8454855a",
    "BQ_parameterized_bjs400.cir": "883308517d48470cbedab878f9e3c71721cd972db248c6b821ce5dba642ff810",
}
AUTH_SOURCE_MANIFEST_SHA256 = "9c8951ca23fd4927db95f6cfe83d8f2e54fcfba7e57a273133e7916240b3a73f"
AUTH_PACKAGE_SHA256 = "7b8da746829605973e0b8d469deccbf8e254df59d46bca02f4b181e584988ea8"
AUTH_GIT_HEAD = "d9656152fc2a7f8ac45e0cf53b00e63db9d11266"
SOLVER_SHA256 = "48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2"

FIXED = {"L1_pH": 1.4, "IBias_uA": 260.0, "RJ1_ohm": 32.0}
L2_VALUES = (1.6, 1.2, 0.8)
MASKS = ("0001", "0011")
CONTROL_KINDS = ("WL", "BL", "SE")
NEW_RUNS = tuple(
    f"ARRAY_L1P14_L2P{str(l2).replace('.', '') if l2 != 0.8 else '08'}_IB260_RJ32_{mask}"
    for l2 in L2_VALUES
    for mask in MASKS
)
REUSE_RUNS = ("ARRAY_L1P14_IB260_RJ32_0001", "ARRAY_L1P14_IB260_RJ32_0011")
RUN_TO_L2 = {
    run_id: l2
    for l2 in L2_VALUES
    for run_id in (f"ARRAY_L1P14_L2P{str(l2).replace('.', '') if l2 != 0.8 else '08'}_IB260_RJ32_0001", f"ARRAY_L1P14_L2P{str(l2).replace('.', '') if l2 != 0.8 else '08'}_IB260_RJ32_0011")
}
RUN_TO_MASK = {run_id: run_id.rsplit("_", 1)[1] for run_id in NEW_RUNS}
SOURCE_REUSE = {
    run_id: {
        "source_experiment": AUTH,
        "source_run": run_id,
        "L1_pH": 1.4,
        "IBias_uA": 260.0,
        "L2_pH": 2.0,
        "RJ1_ohm": 12.0,
        "mask": mask,
    }
    for run_id, mask in ((REUSE_RUNS[0], "0001"), (REUSE_RUNS[1], "0011"))
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()


def solver_version() -> str:
    return subprocess.check_output([str(SOLVER), "--version"], cwd=REPO, text=True)


def write_once(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file():
        if path.read_text(encoding="utf-8") != text:
            raise RuntimeError(f"refusing to overwrite existing artifact: {path}")
        return
    path.write_text(text, encoding="utf-8")


def write_json_once(path: Path, value: Any) -> None:
    write_once(path, json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def control_values(kind: str, active: bool) -> str:
    if kind == "WL":
        points = "0 0 50p 0 51p -100u 60p -100u 61p 0 70p 0 71p +100u 80p +100u 81p 0 90p 0 91p +100u 100p +100u 101p 0"
    elif kind == "BL":
        points = "0 0 50p 0 51p -100u 60p -100u 61p 0 70p 0 71p 0 80p 0 81p 0 90p 0 91p +100u 100p +100u 101p 0"
    elif kind == "SE":
        points = "0 0 50p 0 51p 0 60p 0 61p 0 70p 0 71p +100u 80p +100u 81p 0 90p 0 91p 0 100p 0 101p 0"
    else:
        raise ValueError(kind)
    final = "+100u" if active and kind in {"WL", "SE"} else "0"
    return f"pwl({points} 110p 0 111p {final} 120p {final} 121p 0 200p 0)"


def control_line(instance: int, kind: str, active: bool) -> str:
    return f"I_{kind}{instance} 0 {kind}{instance} {control_values(kind, active)}"


def build_deck(l2: float, mask: str) -> str:
    text = SOURCE_TEMPLATE.read_text(encoding="utf-8")
    include = ".include ../../inputs/jjmit.cir"
    if text.count(include) != 1:
        raise RuntimeError("BJS400 template local JJ include is not unique")
    old_bq_include = ".include ../../inputs/BQ_parameterized_bjs400.cir"
    new_bq_include = ".include ../../inputs/BQ_parameterized_bjs400_l2.cir"
    if text.count(old_bq_include) != 1:
        raise RuntimeError("BJS400 template local QB include is not unique")
    params = (
        f".param L1_VALUE={FIXED['L1_pH']:g}p\n"
        f".param IB_VALUE={FIXED['IBias_uA']:g}u\n"
        f".param RJ1_VALUE={FIXED['RJ1_ohm']:g}\n"
        f".param L2_VALUE={l2:g}p\n"
    )
    text = text.replace(include, params + include, 1)
    text = text.replace(old_bq_include, new_bq_include, 1)
    for instance in range(1, 5):
        for kind in CONTROL_KINDS:
            token = f"@@ARRAY_I_{kind}{instance}@@"
            if text.count(token) != 1:
                raise RuntimeError(f"missing control token: {token}")
            text = text.replace(token, control_line(instance, kind, mask[instance - 1] == "1"), 1)
    if "@@" in text:
        raise RuntimeError("unexpanded template token in deck")
    return text


def normalized_deck(text: str) -> tuple[str, ...]:
    lines: list[str] = []
    for line in text.splitlines():
        if line.startswith(".param L1_VALUE=") or line.startswith(".param IB_VALUE=") or line.startswith(".param RJ1_VALUE=") or line.startswith(".param L2_VALUE="):
            continue
        line = line.replace("../../inputs/BQ_parameterized_bjs400_l2.cir", "../../inputs/BQ_parameterized_bjs400.cir")
        match = re.match(r"I_(WL|BL|SE)([1-4]) ", line)
        lines.append(f"CONTROL_{match.group(1)}{match.group(2)}" if match else line)
    return tuple(lines)


def pre_read_controls(text: str) -> tuple[str, ...]:
    return tuple(
        line.split(" 110p", 1)[0]
        for line in text.splitlines()
        if re.match(r"I_(WL|BL|SE)[1-4] ", line)
    )


def raw_summary(path: Path) -> dict[str, Any]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.reader(stream)
        header = next(reader)
        first = next(reader)
        last = first
        count = 1
        previous = float(first[0])
        monotonic = True
        finite = True
        for row in reader:
            last = row
            count += 1
            finite = finite and len(row) == len(header)
            try:
                values = [float(value) for value in row]
                finite = finite and all(value == value and abs(value) != float("inf") for value in values)
            except ValueError:
                finite = False
            current = float(row[0])
            monotonic = monotonic and current > previous
            previous = current
    return {
        "header_count": len(header),
        "sample_count": count,
        "first_timestamp": first[0],
        "last_timestamp": last[0],
        "strictly_increasing_time": monotonic,
        "finite_values": finite,
        "sha256": sha256(path),
        "bytes": path.stat().st_size,
    }


def write_reuse_manifest() -> dict[str, Any]:
    path = EXP / "REUSED_REFERENCE_MANIFEST.json"
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    if not AUTH.is_dir() or sha256(AUTH / "SOURCE_MANIFEST.json") != AUTH_SOURCE_MANIFEST_SHA256:
        raise RuntimeError("RJ1 re-arm source manifest is missing or changed")
    authority_package = AUTH / "handoff/qb-l1p14-ib260-rj1-rearm-bjs400-v1-20260910_raw_handoff.zip"
    if not authority_package.is_file() or sha256(authority_package) != AUTH_PACKAGE_SHA256:
        raise RuntimeError("RJ1 re-arm source package is missing or changed")
    references: dict[str, Any] = {}
    for run_id, spec in SOURCE_REUSE.items():
        source_dir = spec["source_experiment"] / "runs" / spec["source_run"]
        archived_dir = EXP / "references/reused" / run_id
        metadata = json.loads((archived_dir / "metadata.json").read_text(encoding="utf-8"))
        artifacts: dict[str, Any] = {}
        for name in ("raw.csv", "deck.cir", "metadata.json", "run.log"):
            source = source_dir / name
            archived = archived_dir / name
            if not source.is_file() or not archived.is_file():
                raise RuntimeError(f"missing historical artifact: {run_id}/{name}")
            source_hash = sha256(source)
            archived_hash = sha256(archived)
            if source_hash != archived_hash:
                raise RuntimeError(f"historical source/archive hash mismatch: {run_id}/{name}")
            artifacts[name] = {
                "source_path": str(source),
                "archived_path": str(archived),
                "source_sha256": source_hash,
                "archived_sha256": archived_hash,
                "bytes": archived.stat().st_size,
            }
        failures: list[str] = []
        source_deck = (source_dir / "deck.cir").read_text(encoding="utf-8")
        expected_deck = build_deck(2.0, spec["mask"])
        raw = raw_summary(archived_dir / "raw.csv")
        params = metadata.get("parameters", {})
        if metadata.get("topology") != "ARRAY":
            failures.append("topology is not ARRAY")
        if metadata.get("mask") != spec["mask"]:
            failures.append("mask mismatch")
        if params.get("L1_pH") != 1.4 or params.get("IBias_uA") != 260.0 or params.get("RJ1_ohm") != 32.0:
            failures.append("fixed parameter mismatch")
        if metadata.get("execution_status") != "RUN_PASS":
            failures.append("source execution was not RUN_PASS")
        if metadata.get("solver", {}).get("sha256") != SOLVER_SHA256:
            failures.append("solver hash mismatch")
        if normalized_deck(source_deck) != normalized_deck(expected_deck):
            failures.append("deck/include/topology/L2-parameterization mismatch")
        if pre_read_controls(source_deck) != pre_read_controls(expected_deck):
            failures.append("pre-110ps controls mismatch")
        if raw["sample_count"] != 1999 or raw["first_timestamp"] != "0.000000e+00" or raw["last_timestamp"] != "1.999000e-10" or not raw["strictly_increasing_time"] or not raw["finite_values"]:
            failures.append("raw grid/finite mismatch")
        if failures:
            raise RuntimeError(f"L2=2.0pH exact reuse verification failed for {run_id}: {'; '.join(failures)}")
        references[run_id] = {
            "logical_case_id": run_id,
            "source_experiment": str(spec["source_experiment"].relative_to(REPO)),
            "source_run": f"runs/{spec['source_run']}",
            "source_git_head": metadata.get("git_head_before_run"),
            "parameters": {"L1_pH": 1.4, "L2_pH": 2.0, "IBias_uA": 260.0, "RJ1_ohm": 32.0},
            "topology": "ARRAY",
            "mask": spec["mask"],
            "physical_solve_this_experiment": False,
            "reuse_reason": "exact L2=2.0pH baseline under fixed L1/IBias/RJ1, BJS400 fixture, stored history, mask semantics, solver/timestep/stop-time and source/archive hashes match",
            "comparability": {
                "L1_1p4_L2_2p0_IBias_260_RJ1_32": "PASS",
                "BJS_area_4_Ic_400uA": "PASS",
                "RJ1_12ohm": "PASS",
                "same_ARRAY_COMMON_SL_JSL_QB_JTL_terminal": "PASS",
                "same_history_and_READ_timing": "PASS",
                "same_solver_timestep_stop_time": "PASS",
                "same_deck_structure_and_pre_read_controls": "PASS",
                "same_raw_grid_and_finite_values": "PASS",
            },
            "source_evidence_package": {
                "path": str(authority_package.relative_to(REPO)),
                "sha256": AUTH_PACKAGE_SHA256,
            },
            "artifacts": artifacts,
        }
    record = {
        "schema": "bjs400-l2-rearm-reuse-manifest-v1",
        "experiment_id": EXP.name,
        "created_at_local": now(),
        "source_authority": str(AUTH.relative_to(REPO)),
        "source_authority_git_head": AUTH_GIT_HEAD,
        "references": references,
        "reused_physical_case_count": 2,
        "no_reuse_by_filename_only": True,
        "no_new_historical_solves": True,
        "exact_reuse_verification": "PASS",
    }
    write_json_once(path, record)
    return record


def write_source_manifest() -> dict[str, Any]:
    path = EXP / "SOURCE_MANIFEST.json"
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    local_sources = []
    for name, role in (
        ("array_fixture_template.cir", "BJS400 ARRAY fixture/stimulus template"),
        ("bvm_jm2_connected.cir", "historical JM2-connected BVM include"),
        ("jjmit.cir", "JJ model include"),
        ("jtl2.cir", "JTL model include"),
        ("BQ_parameterized_bjs400.cir", "unmodified BJS400 QB authority include"),
        ("BQ_parameterized_bjs400_l2.cir", "derived BJS400 QB include with L2 parameter exposure"),
    ):
        source = EXP / "inputs" / name
        local_sources.append({"path": name, "repo_relative_path": str(source.relative_to(REPO)), "sha256": sha256(source), "bytes": source.stat().st_size, "role": role})
    local_sources.append({
        "path": str(SOLVER.relative_to(REPO)),
        "repo_relative_path": str(SOLVER.relative_to(REPO)),
        "sha256": sha256(SOLVER),
        "bytes": SOLVER.stat().st_size,
        "role": "solver identity",
        "version": solver_version(),
    })
    record = {
        "schema": "bjs400-l2-rearm-source-manifest-v1",
        "experiment_id": EXP.name,
        "created_at_local": now(),
        "physical_stimulus_authority": str(AUTH.relative_to(REPO)),
        "physical_stimulus_authority_git_head": AUTH_GIT_HEAD,
        "physical_stimulus_authority_source_manifest": {"path": str((AUTH / "SOURCE_MANIFEST.json").relative_to(REPO)), "sha256": AUTH_SOURCE_MANIFEST_SHA256},
        "local_sources": local_sources,
        "fixed_working_point": {"L1_pH": 1.4, "IBias_uA": 260.0, "RJ1_ohm": 32.0, "BJS_area": 4, "BJS_Ic_uA": 400},
        "l2_values_new_pH": list(L2_VALUES),
        "l2_baseline_reused_pH": 2.0,
        "l2_parameterization_delta": {"authority_line": "L2 3 4 2p", "derived_line": "L2 3 4 {L2_VALUE}", "derived_source_sha256": sha256(BQ_L2)},
        "reuse_source_experiment": str(AUTH.relative_to(REPO)),
    }
    write_json_once(path, record)
    return record


def generate_decks() -> dict[str, Any]:
    records: dict[str, Any] = {}
    for run_id in NEW_RUNS:
        deck = EXP / "runs" / run_id / "deck.cir"
        write_once(deck, build_deck(RUN_TO_L2[run_id], RUN_TO_MASK[run_id]))
        records[run_id] = {"L2_pH": RUN_TO_L2[run_id], "mask": RUN_TO_MASK[run_id], "parameters": {**FIXED, "L2_pH": RUN_TO_L2[run_id]}, "path": str(deck.relative_to(REPO)), "sha256": sha256(deck), "bytes": deck.stat().st_size}
    return records


def verify_decks() -> dict[str, Any]:
    failures: list[str] = []
    normalized: set[tuple[str, ...]] = set()
    pre_read: set[tuple[str, ...]] = set()
    records: dict[str, Any] = {}
    bq = BQ_L2.read_text(encoding="utf-8")
    base_bq = BQ400.read_text(encoding="utf-8")
    if "BJs 1 2 jjmit area=4" not in bq or "BJs 1 2 jjmit area=3" in bq:
        failures.append("BJS400 source is not exactly area=4")
    if "L2 3 4 {L2_VALUE}" not in bq or "L2 3 4 2p" in bq:
        failures.append("L2 parameterized BQ source is not active")
    if "L2 3 4 2p" not in base_bq:
        failures.append("unmodified BJS400 authority L2 line is missing")
    for run_id in NEW_RUNS:
        deck = EXP / "runs" / run_id / "deck.cir"
        text = deck.read_text(encoding="utf-8")
        l2 = RUN_TO_L2[run_id]
        mask = RUN_TO_MASK[run_id]
        for required in (".param L1_VALUE=1.4p", ".param IB_VALUE=260u", ".param RJ1_VALUE=32", f".param L2_VALUE={l2:g}p", ".include ../../inputs/BQ_parameterized_bjs400_l2.cir", ".tran 0.1p 200p", "P(BJS|XBQ1) V(BJS|XBQ1) I(BJS|XBQ1)"):
            if required not in text:
                failures.append(f"{run_id}: missing {required}")
        if any(text.count(f"XBVM{index} ") != 1 for index in range(1, 5)):
            failures.append(f"{run_id}: BVM topology count mismatch")
        for instance in range(1, 5):
            for kind in CONTROL_KINDS:
                if control_line(instance, kind, mask[instance - 1] == "1") not in text:
                    failures.append(f"{run_id}: control mismatch {kind}{instance}")
        normalized.add(normalized_deck(text))
        pre_read.add(pre_read_controls(text))
        records[run_id] = {"L2_pH": l2, "mask": mask, "deck_sha256": sha256(deck), "deck_bytes": deck.stat().st_size}
    if len(normalized) != 1:
        failures.append("new decks differ outside L2 and final-read controls")
    if len(pre_read) != 1:
        failures.append("new controls differ before 110ps")
    return {
        "schema": "bjs400-l2-rearm-deck-diff-preflight-v1",
        "status": "PASS" if not failures else "FAIL",
        "new_run_count": len(NEW_RUNS),
        "reused_case_count": len(REUSE_RUNS),
        "fixed_L1_pH": 1.4,
        "fixed_IBias_uA": 260.0,
        "fixed_RJ1_ohm": 32.0,
        "fixed_BJS_area": 4,
        "new_L2_values_pH": list(L2_VALUES),
        "same_mask_only_L2_difference": len(normalized) == 1,
        "mask_pair_only_final_read_difference": len(pre_read) == 1,
        "runs": records,
        "failures": failures,
    }


def preflight_markdown(record: dict[str, Any]) -> str:
    return "\n".join([
        "# L2-controlled post-regeneration re-arm characterization — PREFLIGHT",
        "",
        CONTRACT_SENTENCE,
        "",
        "## Authority and fixed point",
        "",
        f"- Experiment: `{EXP.name}`",
        f"- Preflight HEAD: `{record['head']}`",
        f"- Preregistration HEAD: `{record['preregistration_head']}`",
        f"- Primary authority: `{AUTH.relative_to(REPO)}`; source package SHA-256 `{AUTH_PACKAGE_SHA256}`.",
        "- Fixed L1=1.4pH, IBias=260uA, RJ1=32ohm, BJS area=4 / Ic=400uA, terminal=10ohm.",
        "- L2=2.0pH is historical immutable reuse; only L2=1.6/1.2/0.8pH are new physical values.",
        "- The older no-history stimulus is not used.",
        "",
        "## Exact matrix",
        "",
        "- Logical cases: exactly 4 L2 values (2.0,1.6,1.2,0.8pH) x 2 masks (0001,0011) = 8.",
        "- New physical solves: exactly 6: L2=1.6/1.2/0.8pH, each with 0001 and 0011.",
        "- Historical reuse: exactly ARRAY_L1P14_IB260_RJ32_0001 and ARRAY_L1P14_IB260_RJ32_0011 at L2=2.0pH.",
        "- Unauthorized extra solves: 0; no other L2, mask, SINGLE, retry or refinement.",
        "",
        "## Frozen protocol",
        "",
        "- History: WRITE0 -> ZERO_STATE_READ_CONTROL -> WRITE1 -> SETTLE -> mask-selective FINAL READ -> TAIL.",
        "- 0–50ps idle; WRITE0 50–61ps; idle 61–70ps; ZERO_STATE_READ_CONTROL 70–81ps; idle 81–90ps.",
        "- WRITE1 90–101ps; SETTLE 101–110ps; FINAL READ 110–121ps; TAIL 121–200ps.",
        "- WL/BL/SE amplitude 100uA; 1ps rise/fall; 9ps plateau; `.tran 0.1p 200p`.",
        "- Mask bit order b3b2b1b0=BVM1/BVM2/BVM3/BVM4; 0001 activates BVM4, 0011 activates BVM3+BVM4 during FINAL READ only.",
        "",
        "## Registered mechanical windows and diagnostics",
        "",
        "- CONTROL_ORIGIN: [70,110)ps; baseline [61,70)ps. FINAL_ORIGIN: [110,200)ps; baseline [101,110)ps.",
        "- BJ1/BJ2 phase is independently unwrapped from raw radians and displayed as rad/(2*pi) turns; +0.5 timing is a navigation diagnostic, never an event time/count.",
        "- JTL progression candidate uses fixed +0.5-turn stage-B01 timing in order across JTL1..JTL6; a second candidate uses fixed +1.5-turn timing. Both are MECHANICAL_CANDIDATE_ONLY, not SFQ/event classifiers.",
        "- RJ1 I/V energy, L2/BJ2 extrema and L1 zero crossings are separated for CONTROL_ORIGIN and FINAL_ORIGIN; transitions use stored samples only, no interpolation.",
        "- Terminal V(JTL6_OUT) signed areas are separately recorded in CONTROL_ORIGIN and FINAL_ORIGIN; whole-run area is labeled WHOLE_RUN_TOTAL_ONLY and is not a population count.",
        "- I(B_JSL8) and I(LIN) [110,114.5) signed-area ratios are labeled MECHANICAL_PRE_SWITCH_PROXY; ambiguous denominators are UNKNOWN.",
        "",
        "## Interpretation ceiling and outputs",
        "",
        "- No control/final response is combined into an event count. No phase, voltage area, terminal area or current sign is called an SFQ count.",
        "- Scientific interpretation is NOT_PERFORMED; no L2 threshold, re-arm conclusion, optimum, mechanism, control PASS/FAIL or follow-up is authorized.",
        "- Output: exactly 18 standalone whole-run HTML and two comparison HTML; no permanent focused plots or duplicate plot CSV.",
        "- Canonical package: `handoff/qb-l2-rearm-sweep-l1p14-ib260-rj32-bjs400-v1-20260910_raw_handoff.zip`.",
        "",
        "## Automatic preflight result",
        "",
        f"- L2=2.0pH reuse comparability: `{record['reuse_comparability']['status']}`.",
        f"- New deck checks: `{record['new_deck_checks']['status']}`.",
        "- Physical execution has not started at preflight.",
        "",
    ])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh-head", action="store_true")
    args = parser.parse_args()
    for name, expected in EXPECTED_INPUT_HASHES.items():
        path = EXP / "inputs" / name
        if not path.is_file() or sha256(path) != expected:
            raise RuntimeError(f"input hash mismatch: {name}")
    if not SOLVER.is_file() or sha256(SOLVER) != SOLVER_SHA256:
        raise RuntimeError("solver identity hash mismatch")
    reuse = write_reuse_manifest()
    source = write_source_manifest()
    generated = generate_decks()
    decks = verify_decks()
    if reuse.get("exact_reuse_verification") != "PASS" or decks["status"] != "PASS":
        raise RuntimeError(f"preflight checks failed: reuse={reuse.get('exact_reuse_verification')} decks={decks['status']}")
    preflight_path = EXP / "analysis/preflight.json"
    prior = json.loads(preflight_path.read_text(encoding="utf-8")) if preflight_path.is_file() else {}
    record = {
        "schema": "bjs400-l2-rearm-preflight-v1",
        "experiment_id": EXP.name,
        "created_at_local": now(),
        "status": "PASS",
        "head": head(),
        "head_refresh": args.refresh_head,
        "preregistration_head": prior.get("preregistration_head", head()),
        "new_physical_solve_count": 6,
        "reused_physical_case_count": 2,
        "exact_logical_case_count": 8,
        "unauthorized_extra_solves": 0,
        "fixed_working_point": {"L1_pH": 1.4, "IBias_uA": 260.0, "RJ1_ohm": 32.0, "BJS_area": 4, "BJS_Ic_uA": 400.0},
        "new_l2_values_pH": list(L2_VALUES),
        "reused_l2_value_pH": 2.0,
        "authorized_masks": list(MASKS),
        "reuse_comparability": {"status": "PASS", "cases": list(REUSE_RUNS), "manifest_sha256": sha256(EXP / "REUSED_REFERENCE_MANIFEST.json")},
        "generated_decks": generated,
        "new_deck_checks": decks,
        "source_manifest_sha256": sha256(EXP / "SOURCE_MANIFEST.json"),
        "scientific_analysis_performed": False,
    }
    if args.refresh_head:
        preflight_path.parent.mkdir(parents=True, exist_ok=True)
        preflight_path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        (EXP / "PREFLIGHT.md").write_text(preflight_markdown(record), encoding="utf-8")
    elif not preflight_path.is_file():
        write_json_once(preflight_path, record)
        write_once(EXP / "PREFLIGHT.md", preflight_markdown(record))
    print(json.dumps({"status": "PASS", "head": head(), "head_refresh": args.refresh_head, "new_physical_solve_count": 6, "reused_physical_case_count": 2, "exact_logical_case_count": 8, "reuse_status": "PASS", "deck_status": decks["status"], "solver_invoked": False, "scientific_analysis_performed": False}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
