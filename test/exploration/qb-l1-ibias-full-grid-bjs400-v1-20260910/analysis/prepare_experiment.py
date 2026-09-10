#!/usr/bin/env python3
"""Register the complete BJS400 L1 x IBias grid.

This module creates only registered new decks and immutable provenance
manifests.  It never invokes JoSIM.  Historical raw is copied into
``references/reused`` before this script is run and is checked by hash and by
structural deck/protocol comparison.
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
ARRAY_AUTH = REPO / "test/exploration/qb-bjs400-array-population-single-matched-v1-20260909"
INTERACTION_AUTH = REPO / "test/exploration/qb-l1-ibias-interaction-bjs400-v1-20260909"
SOLVER = REPO / "build/josim-cli"
CONTRACT_SENTENCE = "This experiment is governed by docs/EXPERIMENT_CONTRACT.md."

ARRAY_PACKAGE = ARRAY_AUTH / "handoff/qb-bjs400-array-population-single-matched-v1-20260909_raw_handoff.zip"
INTERACTION_PACKAGE = INTERACTION_AUTH / "handoff/qb-l1-ibias-interaction-bjs400-v1-20260909_raw_handoff_v2.zip"
ARRAY_SOURCE_MANIFEST = ARRAY_AUTH / "SOURCE_MANIFEST.json"
INTERACTION_SOURCE_MANIFEST = INTERACTION_AUTH / "SOURCE_MANIFEST.json"

EXPECTED_INPUT_HASHES = {
    "array_fixture_template.cir": "8971a82dfbac223b9be139f719afae2eb156f0f68fb2a4811858f0a0b482cf71",
    "bvm_jm2_connected.cir": "0093a45cc3910448b484d8bd004c6df8c22358bacc8b3ed5e23912dcab805d54",
    "jjmit.cir": "19862d1fd1f1f44dfa1523848d7d3b5e2594a6c5da8fdd80144b449e5312a336",
    "jtl2.cir": "ffd31f8eda2a86ca0133342be1ce678831b7237a53911eda046d2bff8454855a",
    "BQ_parameterized_bjs400.cir": "883308517d48470cbedab878f9e3c71721cd972db248c6b821ce5dba642ff810",
}
ARRAY_SOURCE_MANIFEST_SHA256 = "3069d48ade02fed285cb1f01a578f7bbd7342cd0f810e6a0242e3eea7621ef33"
INTERACTION_SOURCE_MANIFEST_SHA256 = "c88f0d6102cb5f8722c1ac417ae3d0109faef5e505375d44da101612732914d3"
ARRAY_PACKAGE_SHA256 = "2e0647daf57c62e25dea3e9e4165a33ef169f0cc05888b33bb645bef6339f68a"
INTERACTION_PACKAGE_SHA256 = "3c105c850823fee747632860ebfb17ee930617ec21ebfc4c92c73a20d959575d"
SOLVER_SHA256 = "48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2"

L1_VALUES = (1.2, 1.4, 1.6, 2.0)
IBIAS_VALUES = (250.0, 260.0, 270.0)
MASKS = ("0001", "0011")
CONTROL_KINDS = ("WL", "BL", "SE")

NEW_POINTS = (
    ("L1P12_IB260", 1.2, 260.0),
    ("L1P12_IB270", 1.2, 270.0),
    ("L1P14_IB260", 1.4, 260.0),
    ("L1P14_IB270", 1.4, 270.0),
    ("L1P16_IB270", 1.6, 270.0),
)
NEW_RUNS = tuple(f"ARRAY_{setting}_{mask}" for setting, _l1, _ib in NEW_POINTS for mask in MASKS)

REUSE_SPECS = OrderedDict(
    (
        ("ARRAY_L1P12_0001", {"source": ARRAY_AUTH, "source_run": "ARRAY_L1P12_0001", "L1_pH": 1.2, "IBias_uA": 250.0, "mask": "0001"}),
        ("ARRAY_L1P12_0011", {"source": ARRAY_AUTH, "source_run": "ARRAY_L1P12_0011", "L1_pH": 1.2, "IBias_uA": 250.0, "mask": "0011"}),
        ("ARRAY_L1P14_0001", {"source": ARRAY_AUTH, "source_run": "ARRAY_L1P14_0001", "L1_pH": 1.4, "IBias_uA": 250.0, "mask": "0001"}),
        ("ARRAY_L1P14_0011", {"source": ARRAY_AUTH, "source_run": "ARRAY_L1P14_0011", "L1_pH": 1.4, "IBias_uA": 250.0, "mask": "0011"}),
        ("ARRAY_IB260_0001", {"source": ARRAY_AUTH, "source_run": "ARRAY_IB260_0001", "L1_pH": 2.0, "IBias_uA": 260.0, "mask": "0001"}),
        ("ARRAY_IB260_0011", {"source": ARRAY_AUTH, "source_run": "ARRAY_IB260_0011", "L1_pH": 2.0, "IBias_uA": 260.0, "mask": "0011"}),
        ("ARRAY_IB270_0001", {"source": ARRAY_AUTH, "source_run": "ARRAY_IB270_0001", "L1_pH": 2.0, "IBias_uA": 270.0, "mask": "0001"}),
        ("ARRAY_IB270_0011", {"source": ARRAY_AUTH, "source_run": "ARRAY_IB270_0011", "L1_pH": 2.0, "IBias_uA": 270.0, "mask": "0011"}),
        ("ARRAY_L1P20_IB250_0001", {"source": INTERACTION_AUTH, "source_run": "ARRAY_L1P20_IB250_0001", "L1_pH": 2.0, "IBias_uA": 250.0, "mask": "0001"}),
        ("ARRAY_L1P20_IB250_0011", {"source": INTERACTION_AUTH, "source_run": "ARRAY_L1P20_IB250_0011", "L1_pH": 2.0, "IBias_uA": 250.0, "mask": "0011"}),
        ("ARRAY_L1P16_IB250_0001", {"source": INTERACTION_AUTH, "source_run": "ARRAY_L1P16_IB250_0001", "L1_pH": 1.6, "IBias_uA": 250.0, "mask": "0001"}),
        ("ARRAY_L1P16_IB250_0011", {"source": INTERACTION_AUTH, "source_run": "ARRAY_L1P16_IB250_0011", "L1_pH": 1.6, "IBias_uA": 250.0, "mask": "0011"}),
        ("ARRAY_L1P16_IB260_0001", {"source": INTERACTION_AUTH, "source_run": "ARRAY_L1P16_IB260_0001", "L1_pH": 1.6, "IBias_uA": 260.0, "mask": "0001"}),
        ("ARRAY_L1P16_IB260_0011", {"source": INTERACTION_AUTH, "source_run": "ARRAY_L1P16_IB260_0011", "L1_pH": 1.6, "IBias_uA": 260.0, "mask": "0011"}),
    )
)
REUSE_RUNS = tuple(REUSE_SPECS)

SOURCE_TEMPLATE = EXP / "inputs/array_fixture_template.cir"
BQ400 = EXP / "inputs/BQ_parameterized_bjs400.cir"


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


def build_deck(l1_ph: float, ibias_ua: float, mask: str) -> str:
    text = SOURCE_TEMPLATE.read_text(encoding="utf-8")
    include = ".include ../../inputs/jjmit.cir"
    if text.count(include) != 1:
        raise RuntimeError("array fixture template JJ include is not unique")
    params = (
        f".param L1_VALUE={l1_ph:g}p\n"
        f".param IB_VALUE={ibias_ua:g}u\n"
        ".param RJ1_VALUE=12\n"
    )
    text = text.replace(include, params + include, 1)
    for instance in range(1, 5):
        for kind in CONTROL_KINDS:
            token = f"@@ARRAY_I_{kind}{instance}@@"
            if text.count(token) != 1:
                raise RuntimeError(f"missing mask token: {token}")
            text = text.replace(token, control_line(instance, kind, mask[instance - 1] == "1"), 1)
    if "@@" in text:
        raise RuntimeError("unexpanded template token in deck")
    return text


def read_raw_summary(path: Path) -> dict[str, Any]:
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
            if len(row) != len(header):
                finite = False
            last = row
            count += 1
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


def normalized_deck(text: str) -> tuple[str, ...]:
    """Normalize only registered parameter/control substitutions."""

    lines: list[str] = []
    for line in text.splitlines():
        if line.startswith(".param L1_VALUE=") or line.startswith(".param IB_VALUE=") or line.startswith(".param RJ1_VALUE="):
            continue
        match = re.match(r"I_(WL|BL|SE)([1-4]) ", line)
        if match:
            lines.append(f"CONTROL_{match.group(1)}{match.group(2)}")
        else:
            lines.append(line)
    return tuple(lines)


def pre_read_controls(text: str) -> tuple[str, ...]:
    return tuple(
        line.split(" 110p", 1)[0]
        for line in text.splitlines()
        if re.match(r"I_(WL|BL|SE)[1-4] ", line)
    )


def source_package_info(source: Path) -> dict[str, Any]:
    if source == ARRAY_AUTH:
        package, package_sha, manifest, manifest_sha, authority_head = (
            ARRAY_PACKAGE, ARRAY_PACKAGE_SHA256, ARRAY_SOURCE_MANIFEST,
            ARRAY_SOURCE_MANIFEST_SHA256, "e72b4f568a1d49100b5e4fefa60bee8955bb0db8",
        )
    else:
        package, package_sha, manifest, manifest_sha, authority_head = (
            INTERACTION_PACKAGE, INTERACTION_PACKAGE_SHA256, INTERACTION_SOURCE_MANIFEST,
            INTERACTION_SOURCE_MANIFEST_SHA256, "74c64cf1fe74f6b9dc01d08e854e825329e31f6c",
        )
    if not package.is_file() or sha256(package) != package_sha:
        raise RuntimeError(f"historical source package hash mismatch: {package}")
    if not manifest.is_file() or sha256(manifest) != manifest_sha:
        raise RuntimeError(f"historical source manifest hash mismatch: {manifest}")
    return {
        "experiment": str(source.relative_to(REPO)),
        "authority_git_head": authority_head,
        "package_path": str(package.relative_to(REPO)),
        "package_sha256": package_sha,
        "source_manifest_path": str(manifest.relative_to(REPO)),
        "source_manifest_sha256": manifest_sha,
    }


def write_reuse_manifest() -> dict[str, Any]:
    path = EXP / "REUSED_REFERENCE_MANIFEST.json"
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    source_cache: dict[Path, dict[str, Any]] = {}
    references: dict[str, Any] = {}
    for run_id, spec in REUSE_SPECS.items():
        source_dir = spec["source"] / "runs" / spec["source_run"]
        archived_dir = EXP / "references/reused" / run_id
        metadata_path = archived_dir / "metadata.json"
        if not metadata_path.is_file():
            raise RuntimeError(f"missing staged historical metadata: {metadata_path}")
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        source_cache.setdefault(spec["source"], source_package_info(spec["source"]))
        artifacts: dict[str, Any] = {}
        for name in ("raw.csv", "deck.cir", "metadata.json", "run.log"):
            source_path = source_dir / name
            archived_path = archived_dir / name
            if not source_path.is_file() or not archived_path.is_file():
                raise RuntimeError(f"missing historical artifact: {run_id}/{name}")
            source_hash = sha256(source_path)
            archived_hash = sha256(archived_path)
            if source_hash != archived_hash:
                raise RuntimeError(f"historical source/archive hash mismatch: {run_id}/{name}")
            artifacts[name] = {
                "source_path": str(source_path),
                "archived_path": str(archived_path),
                "source_sha256": source_hash,
                "archived_sha256": archived_hash,
                "bytes": archived_path.stat().st_size,
            }
        expected_deck = build_deck(spec["L1_pH"], spec["IBias_uA"], spec["mask"])
        source_deck_text = (source_dir / "deck.cir").read_text(encoding="utf-8")
        raw = read_raw_summary(archived_dir / "raw.csv")
        failures: list[str] = []
        if metadata.get("topology") != "ARRAY":
            failures.append("topology is not ARRAY")
        if metadata.get("mask") != spec["mask"]:
            failures.append("mask metadata mismatch")
        parameters = metadata.get("parameters", {})
        if parameters.get("L1_pH") != spec["L1_pH"] or parameters.get("IBias_uA") != spec["IBias_uA"] or parameters.get("RJ1_ohm") != 12.0:
            failures.append("parameter metadata mismatch")
        if metadata.get("execution_status") != "RUN_PASS":
            failures.append("historical execution was not RUN_PASS")
        if metadata.get("solver", {}).get("sha256") != SOLVER_SHA256:
            failures.append("historical solver hash mismatch")
        if normalized_deck(source_deck_text) != normalized_deck(expected_deck):
            failures.append("deck structure/include/topology mismatch")
        if pre_read_controls(source_deck_text) != pre_read_controls(expected_deck):
            failures.append("pre-110ps controls mismatch")
        if raw["sample_count"] != 1999 or raw["first_timestamp"] != "0.000000e+00" or raw["last_timestamp"] != "1.999000e-10" or not raw["strictly_increasing_time"] or not raw["finite_values"]:
            failures.append("raw grid/finite QA mismatch")
        if failures:
            raise RuntimeError(f"historical comparability failure {run_id}: {'; '.join(failures)}")
        references[run_id] = {
            "logical_case_id": run_id,
            "source_experiment": str(spec["source"].relative_to(REPO)),
            "source_run": f"runs/{spec['source_run']}",
            "source_git_head": metadata.get("git_head_before_run"),
            "parameters": {"L1_pH": spec["L1_pH"], "IBias_uA": spec["IBias_uA"], "RJ1_ohm": 12.0},
            "topology": "ARRAY",
            "mask": spec["mask"],
            "physical_solve_this_experiment": False,
            "reuse_reason": "exact BJS400 ARRAY fixture, stored-history stimulus, mask semantics, solver/timestep/stop-time and source/archive hashes match",
            "comparability": {
                "BJS_area_4_Ic_400uA": "PASS",
                "RJ1_12ohm": "PASS",
                "four_BVM_COMMON_SL_JSL_QB_JTL_terminal": "PASS",
                "stored_history_and_final_read": "PASS",
                "read_timing_amplitude_duration": "PASS",
                "solver_timestep_stop_time": "PASS",
                "deck_structure_and_pre_read_controls": "PASS",
                "raw_grid_finite_monotonic": "PASS",
            },
            "source_evidence_package": source_cache[spec["source"]],
            "artifacts": artifacts,
        }
    record = {
        "schema": "bjs400-l1-ibias-full-grid-reuse-manifest-v1",
        "experiment_id": EXP.name,
        "created_at_local": now(),
        "source_authorities": [str(ARRAY_AUTH.relative_to(REPO)), str(INTERACTION_AUTH.relative_to(REPO))],
        "references": references,
        "reused_physical_case_count": len(REUSE_RUNS),
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
        ("BQ_parameterized_bjs400.cir", "BJS400 QB include"),
    ):
        source = EXP / "inputs" / name
        local_sources.append({
            "path": name,
            "repo_relative_path": str(source.relative_to(REPO)),
            "sha256": sha256(source),
            "bytes": source.stat().st_size,
            "role": role,
        })
    local_sources.append({
        "path": str(SOLVER.relative_to(REPO)),
        "repo_relative_path": str(SOLVER.relative_to(REPO)),
        "sha256": sha256(SOLVER),
        "bytes": SOLVER.stat().st_size,
        "role": "solver identity",
        "version": solver_version(),
    })
    record = {
        "schema": "bjs400-l1-ibias-full-grid-source-manifest-v1",
        "experiment_id": EXP.name,
        "created_at_local": now(),
        "physical_stimulus_authority": str(ARRAY_AUTH.relative_to(REPO)),
        "physical_stimulus_authority_git_head": "e72b4f568a1d49100b5e4fefa60bee8955bb0db8",
        "physical_stimulus_authority_source_manifest": {
            "path": str(ARRAY_SOURCE_MANIFEST.relative_to(REPO)),
            "sha256": ARRAY_SOURCE_MANIFEST_SHA256,
        },
        "historical_interaction_authority": {
            "path": str(INTERACTION_AUTH.relative_to(REPO)),
            "git_head": "74c64cf1fe74f6b9dc01d08e854e825329e31f6c",
            "source_manifest": str(INTERACTION_SOURCE_MANIFEST.relative_to(REPO)),
            "source_manifest_sha256": INTERACTION_SOURCE_MANIFEST_SHA256,
        },
        "local_sources": local_sources,
        "registered_fixture": {
            "topology": "ARRAY",
            "BJS_area": 4,
            "BJS_Ic_uA": 400,
            "RJ1_ohm": 12,
            "terminal_load_ohm": 10,
            "solver_sha256": SOLVER_SHA256,
        },
        "reuse_source_experiments": [str(ARRAY_AUTH.relative_to(REPO)), str(INTERACTION_AUTH.relative_to(REPO))],
    }
    write_json_once(path, record)
    return record


def generate_decks() -> dict[str, Any]:
    records: dict[str, Any] = {}
    for setting, l1, ibias in NEW_POINTS:
        for mask in MASKS:
            run_id = f"ARRAY_{setting}_{mask}"
            deck = EXP / "runs" / run_id / "deck.cir"
            write_once(deck, build_deck(l1, ibias, mask))
            records[run_id] = {
                "mask": mask,
                "parameters": {"L1_pH": l1, "IBias_uA": ibias, "RJ1_ohm": 12.0},
                "path": str(deck.relative_to(REPO)),
                "sha256": sha256(deck),
                "bytes": deck.stat().st_size,
            }
    return records


def verify_new_decks() -> dict[str, Any]:
    failures: list[str] = []
    normalized: set[tuple[str, ...]] = set()
    pre_read: set[tuple[str, ...]] = set()
    records: dict[str, Any] = {}
    bq = BQ400.read_text(encoding="utf-8")
    if "BJs 1 2 jjmit area=4" not in bq or "BJs 1 2 jjmit area=3" in bq:
        failures.append("BJS400 source is not exactly area=4")
    point_map = {f"ARRAY_{setting}_{mask}": (l1, ibias, mask) for setting, l1, ibias in NEW_POINTS for mask in MASKS}
    for run_id in NEW_RUNS:
        l1, ibias, mask = point_map[run_id]
        deck = EXP / "runs" / run_id / "deck.cir"
        text = deck.read_text(encoding="utf-8")
        for required in (f".param L1_VALUE={l1:g}p", f".param IB_VALUE={ibias:g}u", ".param RJ1_VALUE=12", ".tran 0.1p 200p", "P(BJS|XBQ1) V(BJS|XBQ1) I(BJS|XBQ1)"):
            if required not in text:
                failures.append(f"{run_id}: missing {required}")
        if any(text.count(f"XBVM{index} ") != 1 for index in range(1, 5)):
            failures.append(f"{run_id}: BVM topology count mismatch")
        for instance in range(1, 5):
            for kind in CONTROL_KINDS:
                expected = control_line(instance, kind, mask[instance - 1] == "1")
                if expected not in text:
                    failures.append(f"{run_id}: control mismatch {kind}{instance}")
        normalized.add(normalized_deck(text))
        pre_read.add(pre_read_controls(text))
        records[run_id] = {"mask": mask, "parameters": {"L1_pH": l1, "IBias_uA": ibias, "RJ1_ohm": 12.0}, "deck_sha256": sha256(deck), "deck_bytes": deck.stat().st_size}
    if len(pre_read) != 1:
        failures.append("new controls differ before 110ps")
    return {
        "status": "PASS" if not failures else "FAIL",
        "new_run_count": len(NEW_RUNS),
        "normalized_new_decks_identical_outside_registered_parameters_and_final_read": len(normalized) == 1,
        "pre_110ps_control_equality": len(pre_read) == 1,
        "bjs400_source": "PASS" if not failures else "FAIL",
        "runs": records,
        "failures": failures,
    }


def preflight_markdown(record: dict[str, Any]) -> str:
    lines = [
        "# BJS400 ARRAY L1 x IBias complete coarse grid — PREFLIGHT",
        "",
        CONTRACT_SENTENCE,
        "",
        "## Identity and authority",
        "",
        f"- Experiment: `{EXP.name}`",
        f"- Preflight HEAD: `{record['head']}`",
        f"- Preregistration HEAD: `{record['preregistration_head']}`",
        f"- Physical/stimulus authority: `{ARRAY_AUTH.relative_to(REPO)}`",
        f"- Historical interaction reuse authority: `{INTERACTION_AUTH.relative_to(REPO)}`",
        f"- Solver: `build/josim-cli`; SHA-256 `{SOLVER_SHA256}`",
        f"- BJS source: `inputs/BQ_parameterized_bjs400.cir`; area=4; Ic=400uA.",
        "- The older no-history stimulus is not used.",
        "",
        "## Exact registered grid",
        "",
        "- L1: 1.2, 1.4, 1.6, 2.0pH.",
        "- IBias: 250, 260, 270uA.",
        "- Final-read masks only: 0001 and 0011; b3b2b1b0 = BVM1/BVM2/BVM3/BVM4.",
        "- Logical cases: exactly 4 x 3 x 2 = 24.",
        "- Historical immutable reuse: exactly 14.",
        "- New physical solves: exactly 10, with only these settings: L1P12_IB260, L1P12_IB270, L1P14_IB260, L1P14_IB270, L1P16_IB270, each mask pair.",
        "- Unauthorized extra solves: 0; no other masks, SINGLE, sweep, retry or follow-up.",
        "",
        "## Frozen fixture and history",
        "",
        "- ARRAY: four BVMs -> COMMON_SL -> eight-JJ JSL -> QB -> six-stage JTL -> 10ohm terminal.",
        "- RJ1=12ohm; all BVM, COMMON_SL, JSL, QB, BJ1, L2, BJ2, RJ2, L3, JTL, load, models and solver values frozen.",
        "- History: WRITE0 -> ZERO_STATE_READ_CONTROL -> WRITE1 -> SETTLE -> mask-selective FINAL READ -> TAIL.",
        "- 0–50ps idle; WRITE0 50–61ps; idle 61–70ps; zero-state read 70–81ps; idle 81–90ps; WRITE1 90–101ps; SETTLE 101–110ps; FINAL READ 110–121ps; TAIL 121–200ps.",
        "- Controls: 100uA amplitude; 1ps rise/fall; 9ps plateau; `.tran 0.1p 200p`; expected stored timestamps 0–199.9ps.",
        "",
        "## Registered mechanical metrics",
        "",
        "- Raw P values remain radians. Continuous unwrap followed by division by 2π is display/diagnostic only; it is not an SFQ count or event classifier.",
        "- BJ1/BJ2: first +0.5-turn timing diagnostic, max continuous relative phase and final continuous relative phase; baseline [101,110)ps, post-read [110,200)ps.",
        "- Currents: extrema for I(L1), I(L2), I(RJ1), I(B_JSL8); signed actual-grid areas for I(B_JSL8) and I(LIN) in [110,121)ps and [121,200)ps.",
        "- Optional V(QBIN) and V(COMMON_SL) extrema; missing V(IB|XBQ1) remains UNKNOWN if absent.",
        "- BJ1 voltage positive/negative area and RJ1 dissipated energy use actual stored-grid trapezoids in FINAL READ [110,121)ps.",
        "- 0011/0001 ratios: I(B_JSL8) max-absolute peak, EARLY_READ signed area and I(LIN) EARLY_READ signed area. Denominator tolerance is 1e-12A for peak and 1e-18A·s or <1% of absolute area for signed areas; otherwise UNKNOWN.",
        "- Pre-switch navigation proxy: 0011/0001 signed-area ratio in [110,114.5)ps for I(B_JSL8) and I(LIN), labeled MECHANICAL_PRE_SWITCH_PROXY; not population scaling proof.",
        "",
        "## Output and interpretation ceiling",
        "",
        "- New raw outputs: `runs/<run_id>/raw.csv`; decks, metadata and logs remain immutable.",
        "- Mechanical QA: `qa/raw_qa.json`, `qa/deck_diff_qa.json`, `qa/provenance.json`, `qa/execution_summary.json`, `qa/transformation_registry.json`, `mechanical_summary.json`.",
        "- Visualization: exactly 30 standalone whole-run pages and exactly two full-grid comparison pages; no focused pages, heatmaps, dashboards or permanent comparison CSV.",
        "- Package: `handoff/qb-l1-ibias-full-grid-bjs400-v1-20260910_raw_handoff.zip`; detached PACKAGE_QA remains outside ZIP.",
        "- Scientific interpretation: NOT_PERFORMED. No optimum, regime, mechanism, event/SFQ count, Gate, ranking, or follow-up is authorized.",
        "",
        f"## Automatic preflight result: `{record['status']}`",
        "",
        f"- Historical reuse comparability: `{record['reuse_comparability']['status']}`.",
        f"- New deck checks: `{record['new_deck_checks']['status']}`.",
        "- Physical execution has not started at this preflight record.",
        "",
    ]
    return "\n".join(lines)


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
    decks = generate_decks()
    deck_checks = verify_new_decks()
    if deck_checks["status"] != "PASS" or reuse.get("exact_reuse_verification") != "PASS":
        raise RuntimeError(f"preflight checks failed: deck={deck_checks['status']} reuse={reuse.get('exact_reuse_verification')}")
    preflight_path = EXP / "analysis/preflight.json"
    prior = json.loads(preflight_path.read_text(encoding="utf-8")) if preflight_path.is_file() else {}
    preregistration_head = prior.get("preregistration_head", current_head())
    record = {
        "schema": "bjs400-l1-ibias-full-grid-preflight-v1",
        "experiment_id": EXP.name,
        "created_at_local": now(),
        "status": "PASS",
        "head": current_head(),
        "head_refresh": args.refresh_head,
        "preregistration_head": preregistration_head,
        "authorized_l1_pH": list(L1_VALUES),
        "authorized_ibias_uA": list(IBIAS_VALUES),
        "authorized_masks": list(MASKS),
        "new_physical_solve_count": len(NEW_RUNS),
        "reused_physical_case_count": len(REUSE_RUNS),
        "exact_logical_case_count": len(L1_VALUES) * len(IBIAS_VALUES) * len(MASKS),
        "unauthorized_extra_solves": 0,
        "authorized_new_runs": list(NEW_RUNS),
        "authorized_reuse_runs": list(REUSE_RUNS),
        "reuse_comparability": {"status": "PASS", "references": list(REUSE_RUNS), "manifest_sha256": sha256(EXP / "REUSED_REFERENCE_MANIFEST.json")},
        "new_deck_checks": deck_checks,
        "generated_decks": decks,
        "source_manifest_sha256": sha256(EXP / "SOURCE_MANIFEST.json"),
        "scientific_analysis_performed": False,
    }
    if args.refresh_head or not preflight_path.is_file():
        write_json_once(preflight_path, record) if not args.refresh_head else preflight_path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    markdown = preflight_markdown(record)
    preflight_md = EXP / "PREFLIGHT.md"
    if args.refresh_head:
        preflight_md.write_text(markdown, encoding="utf-8")
    else:
        write_once(preflight_md, markdown)
    print(json.dumps({"status": "PASS", "head": current_head(), "head_refresh": args.refresh_head, "new_physical_solve_count": len(NEW_RUNS), "reused_physical_case_count": len(REUSE_RUNS), "exact_logical_case_count": 24, "solver_invoked": False}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
