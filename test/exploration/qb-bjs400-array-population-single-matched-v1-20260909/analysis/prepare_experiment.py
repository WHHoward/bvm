#!/usr/bin/env python3
"""Create the frozen BJS400 ARRAY/SINGLE decks and machine preflight.

This module never invokes JoSIM. It only creates registered templates/decks,
source manifests, the historical bridge manifest and preflight records.
"""

from __future__ import annotations

import argparse
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
AUTH = REPO / "test/exploration/qb-l1-ibias-rj1-independent-characterization-v1-20260909"
MASK_STYLE = REPO / "test/exploration/bvmsim-4bvm-paperlike-common-sl-accumulation-isolation-v1-20260904"
SOLVER = REPO / "build/josim-cli"
CONTRACT_SENTENCE = "This experiment is governed by docs/EXPERIMENT_CONTRACT.md."

EXPECTED_AUTHORITY_HASHES = {
    "array_fixture": "85227538d48d69251f4276b94b28adfc83cd25f95aa6609fa9eb2375c873f1cf",
    "bq_bjs300": "427385991d51acd330f9b3a5fc1596a3ecb161a98900f3b5341d88962aac874e",
    "bvm": "0093a45cc3910448b484d8bd004c6df8c22358bacc8b3ed5e23912dcab805d54",
    "jjmit": "19862d1fd1f1f44dfa1523848d7d3b5e2594a6c5da8fdd80144b449e5312a336",
    "jtl": "ffd31f8eda2a86ca0133342be1ce678831b7237a53911eda046d2bff8454855a",
    "solver": "48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2",
}

WORKING_POINTS: OrderedDict[str, dict[str, float]] = OrderedDict(
    (
        ("L1P12", {"L1_pH": 1.2, "IBias_uA": 250.0, "RJ1_ohm": 12.0}),
        ("L1P14", {"L1_pH": 1.4, "IBias_uA": 250.0, "RJ1_ohm": 12.0}),
        ("IB260", {"L1_pH": 2.0, "IBias_uA": 260.0, "RJ1_ohm": 12.0}),
        ("IB270", {"L1_pH": 2.0, "IBias_uA": 270.0, "RJ1_ohm": 12.0}),
    )
)
MASKS = ("0000", "1000", "0001", "0011")
ARRAY_RUNS = tuple(f"ARRAY_{setting}_{mask}" for setting in WORKING_POINTS for mask in MASKS)
SINGLE_RUNS = tuple(f"SINGLE_{setting}_{active}" for setting in WORKING_POINTS for active in ("0", "1"))
ALL_RUNS = ARRAY_RUNS + SINGLE_RUNS
HISTORICAL_RUNS = {
    "L1P12": "L1_1P2",
    "L1P14": "L1_1P4",
    "IB260": "IB_260",
    "IB270": "IB_270",
}

CONTROL_KINDS = ("WL", "BL", "SE")
ARRAY_TEMPLATE = EXP / "inputs/array_fixture_template.cir"
SINGLE_TEMPLATE = EXP / "inputs/single_fixture_template.cir"
BQ400 = EXP / "inputs/BQ_parameterized_bjs400.cir"
BQ300 = EXP / "inputs/BQ_parameterized_bjs300_reference.cir"
AUTHORITY_TEMPLATE = EXP / "inputs/array_fixture_authority_reference.cir"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def current_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()


def solver_version() -> str:
    return subprocess.check_output([str(SOLVER), "--version"], cwd=REPO, text=True)


def write_json_once(path: Path, value: Any) -> None:
    text = json.dumps(value, indent=2, ensure_ascii=False) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_text(encoding="utf-8") != text:
            raise RuntimeError(f"refusing to overwrite existing artifact: {path}")
        return
    path.write_text(text, encoding="utf-8")


def write_once(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_text(encoding="utf-8") != text:
            raise RuntimeError(f"refusing to overwrite existing artifact: {path}")
        return
    path.write_text(text, encoding="utf-8")


def control_values(kind: str, active: bool) -> str:
    """Return the exact registered PWL values for one control."""

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


def control_line(source_name: str, node: str, kind: str, active: bool) -> str:
    return f"{source_name} 0 {node} {control_values(kind, active)}"


def make_array_template() -> str:
    source = AUTHORITY_TEMPLATE.read_text(encoding="utf-8")
    if sha256(AUTHORITY_TEMPLATE) != EXPECTED_AUTHORITY_HASHES["array_fixture"]:
        raise RuntimeError("physical authority array template hash mismatch")
    include_old = (
        ".include ../../../../../circuits/models/jjmit.cir\n"
        ".include ../../../bvmsim-jm2-connected-single-ab-v1-20260903/variants/bvm_jm2_connected.cir\n"
        ".include ../../../../../BVMSim/BQ.cir\n"
        ".include ../../../../../BVMSim/library_josim/jtl2.cir"
    )
    include_new = (
        ".include ../../inputs/jjmit.cir\n"
        ".include ../../inputs/bvm_jm2_connected.cir\n"
        ".include ../../inputs/BQ_parameterized_bjs400.cir\n"
        ".include ../../inputs/jtl2.cir"
    )
    if source.count(include_old) != 1:
        raise RuntimeError("authority include block is not unique")
    source = source.replace(include_old, include_new, 1)
    source = source.replace(
        "* ARRAY: four identical historical JM2-connected BVMs share COMMON_SL; BVM1 is the selective final-read target.",
        "* ARRAY: four identical historical JM2-connected BVMs share COMMON_SL; only FINAL READ mask differs.",
        1,
    )
    lines = source.splitlines()
    for instance in range(1, 5):
        for kind in CONTROL_KINDS:
            prefix = f"I_{kind}{instance} "
            matches = [index for index, line in enumerate(lines) if line.startswith(prefix)]
            if len(matches) != 1:
                raise RuntimeError(f"missing unique authority control line: {prefix}")
            lines[matches[0]] = f"@@ARRAY_I_{kind}{instance}@@"
    return "\n".join(lines) + "\n"


def make_single_template(array_template: str) -> str:
    lines: list[str] = []
    for line in array_template.splitlines():
        if line.startswith("* ARRAY:"):
            lines.append("* SINGLE: one historical JM2-connected BVM feeds the same COMMON_SL, JSL, BJS400 QB and 6-stage JTL.")
        elif line.startswith("XBVM1 "):
            lines.append("XBVM1 WL BL SE COMMON_SL BVM")
        elif re.match(r"XBVM[234] ", line):
            continue
        elif line.startswith("@@ARRAY_I_"):
            if line.endswith("1@@"):
                kind = line.split("@@ARRAY_I_", 1)[1][:-3]
                lines.append(f"@@SINGLE_I_{kind}@@")
            continue
        elif line.startswith(".print I(I_WL1)"):
            lines.append(".print I(I_WL) I(I_BL) I(I_SE)")
        elif "|XBVM2" in line or "|XBVM3" in line or "|XBVM4" in line:
            continue
        elif line.startswith("* Full probe is intentionally retained"):
            lines.append("* Full probe is retained for the single historical BVM and all eight JSL elements.")
        else:
            lines.append(line)
    result = "\n".join(lines) + "\n"
    if "XBVM2" in result or "@@ARRAY_" in result or "I_WL2" in result:
        raise RuntimeError("single fixture still contains ARRAY-only content")
    return result


def build_deck(template: Path, *, topology: str, point: dict[str, float], mask: str | None = None, active: bool | None = None) -> str:
    text = template.read_text(encoding="utf-8")
    include = ".include ../../inputs/jjmit.cir"
    if text.count(include) != 1:
        raise RuntimeError(f"local JJ include is not unique in {template}")
    params = (
        f".param L1_VALUE={point['L1_pH']:g}p\n"
        f".param IB_VALUE={point['IBias_uA']:g}u\n"
        f".param RJ1_VALUE={point['RJ1_ohm']:g}\n"
    )
    text = text.replace(include, params + include, 1)
    if topology == "array":
        if mask not in MASKS:
            raise RuntimeError(f"unregistered ARRAY mask: {mask}")
        for instance in range(1, 5):
            for kind in CONTROL_KINDS:
                token = f"@@ARRAY_I_{kind}{instance}@@"
                line = control_line(f"I_{kind}{instance}", f"{kind}{instance}", kind, mask[instance - 1] == "1")
                if text.count(token) != 1:
                    raise RuntimeError(f"missing ARRAY control token: {token}")
                text = text.replace(token, line, 1)
    elif topology == "single":
        if active not in {False, True}:
            raise RuntimeError("SINGLE active control must be boolean")
        for kind in CONTROL_KINDS:
            token = f"@@SINGLE_I_{kind}@@"
            line = control_line(f"I_{kind}", kind, kind, bool(active))
            if text.count(token) != 1:
                raise RuntimeError(f"missing SINGLE control token: {token}")
            text = text.replace(token, line, 1)
    else:
        raise RuntimeError(f"unknown topology: {topology}")
    if "@@" in text:
        raise RuntimeError(f"unexpanded template token in {template}")
    if text.count(".param L1_VALUE=") != 1 or text.count(".param IB_VALUE=") != 1 or text.count(".param RJ1_VALUE=") != 1:
        raise RuntimeError("parameter block was not inserted exactly once")
    return text


def copy_hash_record(source: Path, archived: Path) -> dict[str, Any]:
    source_hash = sha256(source)
    archived_hash = sha256(archived)
    if source_hash != archived_hash:
        raise RuntimeError(f"historical bridge copy hash mismatch: {source} -> {archived}")
    return {
        "source_path": str(source),
        "archived_path": str(archived),
        "sha256": source_hash,
        "bytes": source.stat().st_size,
        "physical_solve_this_experiment": False,
    }


def write_bridge_manifest() -> dict[str, Any]:
    existing_path = EXP / "HISTORICAL_BRIDGE_MANIFEST.json"
    if existing_path.is_file():
        return json.loads(existing_path.read_text(encoding="utf-8"))
    references: dict[str, Any] = {}
    for setting, source_run in HISTORICAL_RUNS.items():
        source_dir = AUTH / "runs" / source_run
        archive_dir = EXP / "references" / "historical_bjs300" / setting
        references[setting] = {
            "logical_case_id": f"BJS300_{setting}",
            "source_experiment": str(AUTH.relative_to(REPO)),
            "source_run": f"runs/{source_run}",
            "physical_solve_this_experiment": False,
            "purpose": "read-only BJS300 bridge comparison against BJS400",
            "artifacts": {
                name: copy_hash_record(source_dir / name, archive_dir / name)
                for name in ("raw.csv", "deck.cir", "metadata.json", "run.log")
            },
        }
    record = {
        "schema": "bjs300-historical-bridge-manifest-v1",
        "experiment_id": EXP.name,
        "created_at_local": now(),
        "source_authority": str(AUTH.relative_to(REPO)),
        "references": references,
        "no_new_historical_solves": True,
    }
    write_json_once(EXP / "HISTORICAL_BRIDGE_MANIFEST.json", record)
    return record


def source_manifest() -> dict[str, Any]:
    existing_path = EXP / "SOURCE_MANIFEST.json"
    if existing_path.is_file():
        return json.loads(existing_path.read_text(encoding="utf-8"))
    paths = OrderedDict(
        (
            ("inputs/array_fixture_authority_reference.cir", "20260909 physical/stimulus authority template"),
            ("inputs/array_fixture_template.cir", "BJS400 ARRAY template derived from authority"),
            ("inputs/single_fixture_template.cir", "matched SINGLE template derived from ARRAY authority"),
            ("inputs/BQ_parameterized_bjs300_reference.cir", "20260909 BJS300 BQ reference"),
            ("inputs/BQ_parameterized_bjs400.cir", "experiment-local BJS400 BQ variant"),
            ("inputs/bvm_jm2_connected.cir", "historical BVM variant"),
            ("inputs/jjmit.cir", "JJ model"),
            ("inputs/jtl2.cir", "JTL model"),
        )
    )
    entries = []
    for relative, role in paths.items():
        path = EXP / relative
        entries.append({
            "repo_relative_path": str(path.relative_to(REPO)),
            "path": relative,
            "sha256": sha256(path),
            "bytes": path.stat().st_size,
            "role": role,
        })
    entries.extend(
        (
            {
                "repo_relative_path": str(SOLVER.relative_to(REPO)),
                "path": str(SOLVER.relative_to(REPO)),
                "sha256": sha256(SOLVER),
                "bytes": SOLVER.stat().st_size,
                "role": "solver identity",
                "version": solver_version(),
            },
            {
                "repo_relative_path": str(AUTH.relative_to(REPO)),
                "path": str(AUTH.relative_to(REPO)),
                "sha256": None,
                "bytes": None,
                "role": "physical/stimulus authority experiment; no copy treated as new source",
                "authority_git_head": current_head(),
            },
            {
                "repo_relative_path": str(MASK_STYLE.relative_to(REPO)),
                "path": str(MASK_STYLE.relative_to(REPO)),
                "sha256": sha256(MASK_STYLE / "experiment.yaml"),
                "bytes": (MASK_STYLE / "experiment.yaml").stat().st_size,
                "role": "mask bit-order and flat plot style reference only",
                "physical_authority": False,
                "stimulus_authority": False,
            },
        )
    )
    record = {
        "schema": "bjs400-array-single-source-manifest-v1",
        "experiment_id": EXP.name,
        "created_at_local": now(),
        "physical_stimulus_authority": str(AUTH.relative_to(REPO)),
        "mask_visual_reference_only": str(MASK_STYLE.relative_to(REPO)),
        "sources": entries,
        "bjs_modification": {
            "reference": "inputs/BQ_parameterized_bjs300_reference.cir",
            "variant": "inputs/BQ_parameterized_bjs400.cir",
            "changed_line": "BJs 1 2 jjmit area=3 -> BJs 1 2 jjmit area=4",
            "icrit_uA": 100,
            "reference_ic_uA": 300,
            "variant_ic_uA": 400,
        },
    }
    write_json_once(EXP / "SOURCE_MANIFEST.json", record)
    return record


def deck_records() -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for setting, point in WORKING_POINTS.items():
        for mask in MASKS:
            run_id = f"ARRAY_{setting}_{mask}"
            deck = EXP / "runs" / run_id / "deck.cir"
            write_once(deck, build_deck(ARRAY_TEMPLATE, topology="array", point=point, mask=mask))
            records[run_id] = {"topology": "ARRAY", "setting": setting, "mask": mask, "active_instances": [i + 1 for i, bit in enumerate(mask) if bit == "1"], "parameters": point, "path": str(deck.relative_to(REPO)), "sha256": sha256(deck), "bytes": deck.stat().st_size}
    for setting, point in WORKING_POINTS.items():
        for active in (False, True):
            suffix = "1" if active else "0"
            run_id = f"SINGLE_{setting}_{suffix}"
            deck = EXP / "runs" / run_id / "deck.cir"
            write_once(deck, build_deck(SINGLE_TEMPLATE, topology="single", point=point, active=active))
            records[run_id] = {"topology": "SINGLE", "setting": setting, "final_read_active": active, "parameters": point, "path": str(deck.relative_to(REPO)), "sha256": sha256(deck), "bytes": deck.stat().st_size}
    return records


def bq_delta() -> dict[str, Any]:
    reference = BQ300.read_text(encoding="utf-8").splitlines()
    variant = BQ400.read_text(encoding="utf-8").splitlines()
    if len(reference) != len(variant):
        raise RuntimeError("BJS300/BJS400 BQ line counts differ")
    changes = [(index + 1, before, after) for index, (before, after) in enumerate(zip(reference, variant)) if before != after]
    expected = [(line_no, before, after) for line_no, before, after in changes if "BJs 1 2 jjmit" in before]
    if changes != expected or len(changes) != 1 or expected[0][1] != "BJs 1 2 jjmit area=3" or expected[0][2] != "BJs 1 2 jjmit area=4":
        raise RuntimeError(f"BJS400 BQ diff is not exactly one registered line: {changes}")
    return {
        "status": "PASS",
        "changed_line_count": 1,
        "changed_line": {"line": changes[0][0], "reference": changes[0][1], "variant": changes[0][2]},
        "reference_sha256": sha256(BQ300),
        "variant_sha256": sha256(BQ400),
        "reference_bjs_uA": 300,
        "variant_bjs_uA": 400,
    }


def pre_read_control_signature(deck: Path, *, topology: str) -> tuple[str, ...]:
    lines = deck.read_text(encoding="utf-8").splitlines()
    selected = []
    for line in lines:
        if topology == "array" and re.match(r"I_(WL|BL|SE)[1-4] ", line):
            selected.append(line.split(" 110p", 1)[0])
        elif topology == "single" and re.match(r"I_(WL|BL|SE) ", line):
            selected.append(line.split(" 110p", 1)[0])
    return tuple(selected)


def verify_decks(records: dict[str, dict[str, Any]]) -> dict[str, Any]:
    failures: list[str] = []
    bq = BQ400.read_text(encoding="utf-8")
    if "BJs 1 2 jjmit area=4" not in bq or "BJs 1 2 jjmit area=3" in bq:
        failures.append("BJS400 active line is not exactly area=4")
    if "ZERO_STATE_READ_CONTROL" not in (EXP / "inputs/array_fixture_template.cir").read_text(encoding="utf-8"):
        failures.append("ZERO_STATE_READ_CONTROL marker absent from ARRAY template")
    array_pre_read: dict[str, tuple[str, ...]] = {}
    for run_id in ARRAY_RUNS:
        deck = EXP / "runs" / run_id / "deck.cir"
        text = deck.read_text(encoding="utf-8")
        setting = run_id.split("_")[1]
        mask = run_id.rsplit("_", 1)[1]
        expected = WORKING_POINTS[setting]
        for key, value in (
            (".param L1_VALUE=", f".param L1_VALUE={expected['L1_pH']:g}p"),
            (".param IB_VALUE=", f".param IB_VALUE={expected['IBias_uA']:g}u"),
            (".param RJ1_VALUE=", f".param RJ1_VALUE={expected['RJ1_ohm']:g}"),
        ):
            if value not in text:
                failures.append(f"{run_id}: missing {value}")
        if text.count("XBVM1 ") != 1 or text.count("XBVM2 ") != 1 or text.count("XBVM3 ") != 1 or text.count("XBVM4 ") != 1:
            failures.append(f"{run_id}: ARRAY BVM instance count mismatch")
        for instance in range(1, 5):
            for kind in CONTROL_KINDS:
                expected_line = control_line(f"I_{kind}{instance}", f"{kind}{instance}", kind, mask[instance - 1] == "1")
                if expected_line not in text:
                    failures.append(f"{run_id}: control mismatch {kind}{instance}")
        if ".tran 0.1p 200p" not in text:
            failures.append(f"{run_id}: timing mismatch")
        if "P(BJS|XBQ1) V(BJS|XBQ1) I(BJS|XBQ1)" not in text:
            failures.append(f"{run_id}: mandatory BJS probe missing")
        array_pre_read[run_id] = pre_read_control_signature(deck, topology="array")
    if len(set(array_pre_read.values())) != 1:
        failures.append("ARRAY controls differ before 110ps")
    single_pre_read: dict[str, tuple[str, ...]] = {}
    for run_id in SINGLE_RUNS:
        deck = EXP / "runs" / run_id / "deck.cir"
        text = deck.read_text(encoding="utf-8")
        setting = run_id.split("_")[1]
        active = run_id.rsplit("_", 1)[1] == "1"
        expected = WORKING_POINTS[setting]
        for value in (
            f".param L1_VALUE={expected['L1_pH']:g}p",
            f".param IB_VALUE={expected['IBias_uA']:g}u",
            f".param RJ1_VALUE={expected['RJ1_ohm']:g}",
        ):
            if value not in text:
                failures.append(f"{run_id}: missing {value}")
        if text.count("XBVM1 ") != 1 or "XBVM2 " in text or "XBVM3 " in text or "XBVM4 " in text:
            failures.append(f"{run_id}: SINGLE topology mismatch")
        for kind in CONTROL_KINDS:
            expected_line = control_line(f"I_{kind}", kind, kind, active)
            if expected_line not in text:
                failures.append(f"{run_id}: SINGLE control mismatch {kind}")
        if ".tran 0.1p 200p" not in text or "P(BJS|XBQ1) V(BJS|XBQ1) I(BJS|XBQ1)" not in text:
            failures.append(f"{run_id}: timing or mandatory BJS probe missing")
        single_pre_read[run_id] = pre_read_control_signature(deck, topology="single")
    if len(set(single_pre_read.values())) != 1:
        failures.append("SINGLE controls differ before 110ps")
    if failures:
        raise RuntimeError("deck preflight failures: " + "; ".join(failures))
    return {
        "status": "PASS",
        "array_run_count": len(ARRAY_RUNS),
        "single_run_count": len(SINGLE_RUNS),
        "exact_physical_solve_count": len(ALL_RUNS),
        "array_pre_110ps_control_equal": True,
        "single_pre_110ps_control_equal": True,
        "all_bjs400_probe_declared": True,
        "records": records,
    }


def preflight_markdown(head: str, preregistration_head: str, records: dict[str, dict[str, Any]], bq: dict[str, Any]) -> str:
    lines = [
        "# BJS400 ARRAY population + matched SINGLE functional experiment — PREFLIGHT",
        "",
        CONTRACT_SENTENCE,
        "",
        "## Frozen authority",
        "",
        f"- Physical/stimulus authority: test/exploration/{AUTH.name}",
        f"- Mask bit-order and flat visualization style reference only: test/exploration/{MASK_STYLE.name}",
        f"- Preflight HEAD: {head}",
        f"- Preregistration/base HEAD: {preregistration_head}",
        f"- Solver: build/josim-cli; SHA-256 {sha256(SOLVER)}",
        f"- Solver version: {solver_version().strip()}",
        "",
        "The 20260904 experiment is not used for physical topology, source or stimulus.",
        "",
        "## Registered physical change",
        "",
        "- Experiment-local BQ copy changes exactly BJs 1 2 jjmit area=3 to area=4.",
        "- The local jjmit model has icrit=100uA; the registered BJS current is therefore 400uA.",
        "- All other BQ, BVM, JSL, JTL, termination, solver, timestep and stop-time values are frozen.",
        "",
        "## Frozen history",
        "",
        "Every ARRAY and SINGLE run uses:",
        "",
        "WRITE0 -> ZERO_STATE_READ_CONTROL -> WRITE1 -> SETTLE -> mask-selective FINAL READ -> TAIL",
        "",
        "- 0–50ps idle; WRITE0 50–61ps; idle 61–70ps; ZERO_STATE_READ_CONTROL 70–81ps.",
        "- idle 81–90ps; WRITE1 90–101ps; SETTLE 101–110ps.",
        "- FINAL READ 110–121ps; TAIL 121–200ps; .tran 0.1p 200p.",
        "- ARRAY bit order is b3b2b1b0 = BVM1/BVM2/BVM3/BVM4.",
        "- Authorized masks only: 0000, 1000, 0001, 0011.",
        "- SINGLE_0 final controls are WL=BL=SE=0; SINGLE_1 is WL=SE=+100uA and BL=0.",
        "",
        "## Exact matrix",
        "",
        f"- ARRAY: {len(ARRAY_RUNS)} runs = 4 working points × 4 masks.",
        f"- SINGLE: {len(SINGLE_RUNS)} runs = 4 working points × 2 final-read controls.",
        f"- Total authorized physical solves: {len(ALL_RUNS)}.",
        "- No combination intervention, extra mask, extra parameter, retry, tuning or follow-up is authorized.",
        "",
        "## Preflight checks",
        "",
        "- BJS400 source diff: PASS (exactly one active line changed).",
        "- All ARRAY cases are identical before 110ps except registered working-point parameters.",
        "- All SINGLE cases are identical before 110ps except registered working-point parameters.",
        "- Full raw probe declarations include mandatory P/V/I(BJS), JTL current probes and all requested boundaries.",
        "- Raw is not yet present; execution has not started.",
        "",
        "## Interpretation ceiling",
        "",
        "scientific_interpretation = NOT_PERFORMED; this directory records evidence only.",
        "No SFQ/event count, mechanism, ranking, equivalence, Gate or next-experiment claim is authorized.",
        "",
    ]
    return "\n".join(lines)


def write_preflight(head: str, preregistration_head: str, records: dict[str, dict[str, Any]], bq: dict[str, Any], *, refresh: bool) -> None:
    markdown = preflight_markdown(head, preregistration_head, records, bq)
    path = EXP / "PREFLIGHT.md"
    path_json = EXP / "analysis" / "preflight.json"
    if not refresh and path.is_file() and path_json.is_file():
        return
    if refresh:
        path.write_text(markdown, encoding="utf-8")
    else:
        write_once(path, markdown)
    record = {
        "schema": "bjs400-array-single-preflight-v1",
        "experiment_id": EXP.name,
        "created_at_local": now(),
        "status": "PASS",
        "head": head,
        "head_refresh": refresh,
        "preregistration_head": preregistration_head,
        "exact_physical_solve_count": len(ALL_RUNS),
        "array_solve_count": len(ARRAY_RUNS),
        "single_solve_count": len(SINGLE_RUNS),
        "working_points": WORKING_POINTS,
        "authorized_masks": list(MASKS),
        "array_pre_110ps_equal": True,
        "single_pre_110ps_equal": True,
        "bjs400": bq,
        "source_manifest_sha256": sha256(EXP / "SOURCE_MANIFEST.json"),
        "historical_bridge_manifest_sha256": sha256(EXP / "HISTORICAL_BRIDGE_MANIFEST.json"),
        "decks": records,
        "scientific_analysis_performed": False,
        "unauthorized_extra_solves": 0,
    }
    if refresh:
        path_json.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    else:
        write_json_once(path_json, record)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh-head", action="store_true")
    args = parser.parse_args()
    if not EXP.is_dir():
        raise SystemExit(f"missing experiment directory: {EXP}")
    local_expected = {
        "inputs/array_fixture_authority_reference.cir": EXPECTED_AUTHORITY_HASHES["array_fixture"],
        "inputs/BQ_parameterized_bjs300_reference.cir": EXPECTED_AUTHORITY_HASHES["bq_bjs300"],
        "inputs/bvm_jm2_connected.cir": EXPECTED_AUTHORITY_HASHES["bvm"],
        "inputs/jjmit.cir": EXPECTED_AUTHORITY_HASHES["jjmit"],
        "inputs/jtl2.cir": EXPECTED_AUTHORITY_HASHES["jtl"],
    }
    for relative, expected in local_expected.items():
        path = EXP / relative
        if not path.is_file() or sha256(path) != expected:
            raise RuntimeError(f"local authority input hash mismatch: {relative}")
    generated_array = make_array_template()
    generated_single = make_single_template(generated_array)
    write_once(ARRAY_TEMPLATE, generated_array)
    write_once(SINGLE_TEMPLATE, generated_single)
    records = deck_records()
    bridge = write_bridge_manifest()
    sources = source_manifest()
    bq = bq_delta()
    checked = verify_decks(records)
    preregistration_head = json.loads((EXP / "analysis/preflight.json").read_text(encoding="utf-8")).get("preregistration_head") if (EXP / "analysis/preflight.json").is_file() else current_head()
    write_preflight(current_head(), preregistration_head, records, bq, refresh=args.refresh_head)
    print(json.dumps({"status": "PASS", "head": current_head(), "head_refresh": args.refresh_head, "array_runs": len(ARRAY_RUNS), "single_runs": len(SINGLE_RUNS), "physical_solve_count": len(ALL_RUNS), "bjs_delta": bq, "deck_checks": checked["status"], "bridge_references": len(bridge["references"]), "source_count": len(sources["sources"]), "solver_invoked": False}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
