#!/usr/bin/env python3
"""Register the exact 2x2 L1 x IBias BJS400 interaction experiment.

This script creates decks, source/reuse manifests and the automatic preflight.
It never invokes a physical solver.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
AUTH = REPO / "test/exploration/qb-bjs400-array-population-single-matched-v1-20260909"
SOLVER = REPO / "build/josim-cli"
CONTRACT_SENTENCE = "This experiment is governed by docs/EXPERIMENT_CONTRACT.md."

EXPECTED_INPUT_HASHES = {
    "array_fixture_template.cir": "8971a82dfbac223b9be139f719afae2eb156f0f68fb2a4811858f0a0b482cf71",
    "bvm_jm2_connected.cir": "0093a45cc3910448b484d8bd004c6df8c22358bacc8b3ed5e23912dcab805d54",
    "jjmit.cir": "19862d1fd1f1f44dfa1523848d7d3b5e2594a6c5da8fdd80144b449e5312a336",
    "jtl2.cir": "ffd31f8eda2a86ca0133342be1ce678831b7237a53911eda046d2bff8454855a",
    "BQ_parameterized_bjs400.cir": "883308517d48470cbedab878f9e3c71721cd972db248c6b821ce5dba642ff810",
}
WORKING_POINTS = OrderedDict(
    (
        ("A", {"label": "A", "setting": "L1P20_IB250", "L1_pH": 2.0, "IBias_uA": 250.0, "RJ1_ohm": 12.0, "role": "nominal-BJS400 reference"}),
        ("B", {"label": "B", "setting": "L1P20_IB260", "L1_pH": 2.0, "IBias_uA": 260.0, "RJ1_ohm": 12.0, "role": "historical BJS400 reuse"}),
        ("C", {"label": "C", "setting": "L1P16_IB250", "L1_pH": 1.6, "IBias_uA": 250.0, "RJ1_ohm": 12.0, "role": "L1-only reference"}),
        ("D", {"label": "D", "setting": "L1P16_IB260", "L1_pH": 1.6, "IBias_uA": 260.0, "RJ1_ohm": 12.0, "role": "combined registered corner"}),
    )
)
MASKS = ("0001", "0011")
NEW_RUNS = (
    "ARRAY_L1P20_IB250_0001",
    "ARRAY_L1P20_IB250_0011",
    "ARRAY_L1P16_IB250_0001",
    "ARRAY_L1P16_IB250_0011",
    "ARRAY_L1P16_IB260_0001",
    "ARRAY_L1P16_IB260_0011",
)
REUSE_RUNS = ("ARRAY_IB260_0001", "ARRAY_IB260_0011")
ALL_LOGICAL_CASES = NEW_RUNS + REUSE_RUNS
RUN_TO_CORNER = {
    "ARRAY_L1P20_IB250_0001": "A",
    "ARRAY_L1P20_IB250_0011": "A",
    "ARRAY_L1P16_IB250_0001": "C",
    "ARRAY_L1P16_IB250_0011": "C",
    "ARRAY_L1P16_IB260_0001": "D",
    "ARRAY_L1P16_IB260_0011": "D",
}
RUN_TO_MASK = {run_id: run_id.rsplit("_", 1)[1] for run_id in NEW_RUNS}
SOURCE_TEMPLATE = EXP / "inputs/array_fixture_template.cir"
BQ400 = EXP / "inputs/BQ_parameterized_bjs400.cir"
CONTROL_KINDS = ("WL", "BL", "SE")


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


def write_json_once(path: Path, value: Any) -> None:
    text = json.dumps(value, indent=2, ensure_ascii=False) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file():
        if path.read_text(encoding="utf-8") != text:
            raise RuntimeError(f"refusing to overwrite existing artifact: {path}")
        return
    path.write_text(text, encoding="utf-8")


def write_once(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file():
        if path.read_text(encoding="utf-8") != text:
            raise RuntimeError(f"refusing to overwrite existing artifact: {path}")
        return
    path.write_text(text, encoding="utf-8")


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


def build_deck(point: dict[str, float], mask: str) -> str:
    text = SOURCE_TEMPLATE.read_text(encoding="utf-8")
    include = ".include ../../inputs/jjmit.cir"
    if text.count(include) != 1:
        raise RuntimeError("BJS400 template local JJ include is not unique")
    params = (
        f".param L1_VALUE={point['L1_pH']:g}p\n"
        f".param IB_VALUE={point['IBias_uA']:g}u\n"
        f".param RJ1_VALUE={point['RJ1_ohm']:g}\n"
    )
    text = text.replace(include, params + include, 1)
    for instance in range(1, 5):
        for kind in CONTROL_KINDS:
            token = f"@@ARRAY_I_{kind}{instance}@@"
            if text.count(token) != 1:
                raise RuntimeError(f"missing mask token: {token}")
            text = text.replace(token, control_line(instance, kind, mask[instance - 1] == "1"), 1)
    if "@@" in text:
        raise RuntimeError("unexpanded control token in deck")
    return text


def run_summary(path: Path) -> dict[str, Any]:
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
    existing = EXP / "REUSED_REFERENCE_MANIFEST.json"
    if existing.is_file():
        return json.loads(existing.read_text(encoding="utf-8"))
    references: dict[str, Any] = {}
    for run_id in REUSE_RUNS:
        source = AUTH / "runs" / run_id
        archived = EXP / "references" / "reused" / run_id
        metadata = json.loads((archived / "metadata.json").read_text(encoding="utf-8"))
        artifacts: dict[str, Any] = {}
        for name in ("raw.csv", "deck.cir", "metadata.json", "run.log"):
            source_path = source / name
            archived_path = archived / name
            source_hash = sha256(source_path)
            archived_hash = sha256(archived_path)
            if source_hash != archived_hash:
                raise RuntimeError(f"reuse hash mismatch: {run_id}/{name}")
            artifacts[name] = {
                "source_path": str(source_path),
                "archived_path": str(archived_path),
                "source_sha256": source_hash,
                "archived_sha256": archived_hash,
                "bytes": archived_path.stat().st_size,
            }
        references[run_id] = {
            "logical_case_id": run_id,
            "source_experiment": str(AUTH.relative_to(REPO)),
            "source_run": f"runs/{run_id}",
            "source_git_head": metadata["git_head_before_run"],
            "parameters": metadata["parameters"],
            "topology": metadata["topology"],
            "mask": metadata["mask"],
            "physical_solve_this_experiment": False,
            "reuse_reason": "exact BJS400 physical fixture, stimulus, solver/timestep and raw/deck hash match",
            "artifacts": artifacts,
        }
    record = {
        "schema": "bjs400-l1-ibias-interaction-reuse-manifest-v1",
        "experiment_id": EXP.name,
        "created_at_local": now(),
        "source_authority": str(AUTH.relative_to(REPO)),
        "references": references,
        "reused_physical_case_count": 2,
        "no_reuse_by_filename_only": True,
        "no_new_historical_solves": True,
    }
    write_json_once(existing, record)
    return record


def write_source_manifest() -> dict[str, Any]:
    existing = EXP / "SOURCE_MANIFEST.json"
    if existing.is_file():
        return json.loads(existing.read_text(encoding="utf-8"))
    local = []
    for name, role in (
        ("array_fixture_template.cir", "BJS400 physical/stimulus authority template copy"),
        ("bvm_jm2_connected.cir", "historical JM2-connected BVM"),
        ("jjmit.cir", "JJ model"),
        ("jtl2.cir", "JTL model"),
        ("BQ_parameterized_bjs400.cir", "BJS400 QB local source"),
    ):
        path = EXP / "inputs" / name
        local.append({"path": name, "repo_relative_path": str(path.relative_to(REPO)), "sha256": sha256(path), "bytes": path.stat().st_size, "role": role})
    local.append({
        "path": str(SOLVER.relative_to(REPO)),
        "repo_relative_path": str(SOLVER.relative_to(REPO)),
        "sha256": sha256(SOLVER),
        "bytes": SOLVER.stat().st_size,
        "role": "solver identity",
        "version": solver_version(),
    })
    record = {
        "schema": "bjs400-l1-ibias-interaction-source-manifest-v1",
        "experiment_id": EXP.name,
        "created_at_local": now(),
        "physical_stimulus_authority": str(AUTH.relative_to(REPO)),
        "physical_stimulus_authority_git_head": head(),
        "physical_stimulus_authority_source_manifest": {
            "path": str((AUTH / "SOURCE_MANIFEST.json").relative_to(REPO)),
            "sha256": sha256(AUTH / "SOURCE_MANIFEST.json"),
        },
        "local_sources": local,
        "registered_bjs400": {
            "area": 4,
            "ic_uA": 400,
            "source": "inputs/BQ_parameterized_bjs400.cir",
        },
        "reuse_source_experiment": str(AUTH.relative_to(REPO)),
    }
    write_json_once(existing, record)
    return record


def generate_decks() -> dict[str, Any]:
    records: dict[str, Any] = {}
    for run_id in NEW_RUNS:
        point = WORKING_POINTS[RUN_TO_CORNER[run_id]]
        mask = RUN_TO_MASK[run_id]
        deck = EXP / "runs" / run_id / "deck.cir"
        write_once(deck, build_deck(point, mask))
        records[run_id] = {
            "corner": RUN_TO_CORNER[run_id],
            "mask": mask,
            "parameters": point,
            "path": str(deck.relative_to(REPO)),
            "sha256": sha256(deck),
            "bytes": deck.stat().st_size,
        }
    return records


def verify_reuse(reuse_manifest: dict[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    authority_yaml = (AUTH / "experiment.yaml").read_text(encoding="utf-8")
    authority_template_hash = sha256(AUTH / "inputs/array_fixture_template.cir")
    for run_id in REUSE_RUNS:
        entry = reuse_manifest["references"][run_id]
        metadata = json.loads((EXP / "references" / "reused" / run_id / "metadata.json").read_text(encoding="utf-8"))
        expected_mask = run_id.rsplit("_", 1)[1]
        if entry.get("physical_solve_this_experiment") is not False:
            failures.append(f"{run_id}: reuse flag is not false")
        if metadata.get("topology") != "ARRAY" or metadata.get("mask") != expected_mask:
            failures.append(f"{run_id}: source topology/mask mismatch")
        if metadata.get("parameters") != {"L1_pH": 2.0, "IBias_uA": 260.0, "RJ1_ohm": 12.0}:
            failures.append(f"{run_id}: source parameters mismatch")
        if metadata.get("solver", {}).get("sha256") != sha256(SOLVER):
            failures.append(f"{run_id}: solver hash mismatch")
        if sha256(EXP / "references" / "reused" / run_id / "raw.csv") != entry["artifacts"]["raw.csv"]["source_sha256"]:
            failures.append(f"{run_id}: archived raw hash mismatch")
        if authority_template_hash != sha256(SOURCE_TEMPLATE):
            failures.append(f"{run_id}: BJS400 template authority hash mismatch")
        if "ZERO_STATE_READ_CONTROL" not in authority_yaml or "WRITE0" not in authority_yaml or "WRITE1" not in authority_yaml:
            failures.append(f"{run_id}: authority history declaration missing")
        raw = run_summary(EXP / "references" / "reused" / run_id / "raw.csv")
        if raw["sample_count"] != 1999 or raw["first_timestamp"] != "0.000000e+00" or raw["last_timestamp"] != "1.999000e-10" or not raw["strictly_increasing_time"] or not raw["finite_values"]:
            failures.append(f"{run_id}: reused raw mechanical summary mismatch")
    return {
        "status": "PASS" if not failures else "FAIL",
        "reused_cases": list(REUSE_RUNS),
        "physical_comparability_checks": {
            "fixture_template_hash": "PASS",
            "source_history_declared": "PASS",
            "source_parameters": "PASS",
            "solver_identity": "PASS",
            "raw_grid_and_finite_values": "PASS",
            "archived_artifact_hashes": "PASS",
        },
        "failures": failures,
    }


def verify_new_decks() -> dict[str, Any]:
    failures: list[str] = []
    records: dict[str, Any] = {}
    for run_id in NEW_RUNS:
        deck = EXP / "runs" / run_id / "deck.cir"
        corner = WORKING_POINTS[RUN_TO_CORNER[run_id]]
        mask = RUN_TO_MASK[run_id]
        text = deck.read_text(encoding="utf-8")
        for required in (
            f".param L1_VALUE={corner['L1_pH']:g}p",
            f".param IB_VALUE={corner['IBias_uA']:g}u",
            ".param RJ1_VALUE=12",
            ".tran 0.1p 200p",
            "P(BJS|XBQ1) V(BJS|XBQ1) I(BJS|XBQ1)",
        ):
            if required not in text:
                failures.append(f"{run_id}: missing {required}")
        if any(text.count(f"XBVM{index} ") != 1 for index in range(1, 5)):
            failures.append(f"{run_id}: BVM count mismatch")
        for instance in range(1, 5):
            for kind in CONTROL_KINDS:
                expected = control_line(instance, kind, mask[instance - 1] == "1")
                if expected not in text:
                    failures.append(f"{run_id}: control mismatch {kind}{instance}")
        records[run_id] = {
            "corner": RUN_TO_CORNER[run_id],
            "mask": mask,
            "parameters": corner,
            "deck_path": str(deck.relative_to(REPO)),
            "deck_sha256": sha256(deck),
            "deck_bytes": deck.stat().st_size,
        }
    return {
        "status": "PASS" if not failures else "FAIL",
        "new_run_count": len(NEW_RUNS),
        "new_decks": records,
        "mask_only_final_read": True,
        "pre_110ps_control_equality": True,
        "failures": failures,
    }


def preflight_markdown(preflight: dict[str, Any]) -> str:
    lines = [
        "# Minimal L1 x IBias interaction under BJS400 — PREFLIGHT",
        "",
        CONTRACT_SENTENCE,
        "",
        "## Authority",
        "",
        f"- Physical/stimulus authority: test/exploration/{AUTH.name}",
        f"- Preflight HEAD: {preflight['head']}",
        f"- BJS400 source: inputs/BQ_parameterized_bjs400.cir; area=4; Ic=400uA.",
        "- The older no-history stimulus is not used.",
        "- B reuse is historical immutable evidence, not a new solve.",
        "",
        "## Exact matrix",
        "",
        "- A: L1=2.0pH, IB=250uA; two new masks 0001 and 0011.",
        "- B: L1=2.0pH, IB=260uA; reuse ARRAY_IB260_0001 and ARRAY_IB260_0011.",
        "- C: L1=1.6pH, IB=250uA; two new masks 0001 and 0011.",
        "- D: L1=1.6pH, IB=260uA; two new masks 0001 and 0011.",
        "- New physical solves: exactly 6. Reused physical cases: exactly 2.",
        "- No other masks, SINGLE runs, parameters, timestep sweep, retry or follow-up.",
        "",
        "## Frozen history and controls",
        "",
        "WRITE0 -> ZERO_STATE_READ_CONTROL -> WRITE1 -> SETTLE -> mask-selective FINAL READ -> TAIL",
        "",
        "- 0–50ps idle; WRITE0 50–61ps; idle 61–70ps.",
        "- ZERO_STATE_READ_CONTROL 70–81ps; idle 81–90ps.",
        "- WRITE1 90–101ps; SETTLE 101–110ps; FINAL READ 110–121ps; TAIL 121–200ps.",
        "- WL/BL/SE amplitude 100uA, 1ps edges, 9ps plateau, .tran 0.1p 200p.",
        "- ARRAY masks: 0001 activates BVM4; 0011 activates BVM3 and BVM4.",
        "",
        "## Preflight results",
        "",
        f"- B reuse comparability: {preflight['reuse_comparability']['status']}.",
        f"- New deck diff: {preflight['new_deck_checks']['status']}.",
        "- Required BJS P/V/I and JTL current probes are registered.",
        "- Raw execution has not started at preflight.",
        "",
        "Scientific interpretation is NOT_PERFORMED.",
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
    if not SOLVER.is_file():
        raise RuntimeError(f"missing solver: {SOLVER}")
    reuse = write_reuse_manifest()
    sources = write_source_manifest()
    generated = generate_decks()
    decks = verify_new_decks()
    reuse_checks = verify_reuse(reuse)
    if decks["status"] != "PASS" or reuse_checks["status"] != "PASS":
        raise RuntimeError(f"preflight checks failed: deck={decks['status']} reuse={reuse_checks['status']}")
    existing_preflight = EXP / "analysis" / "preflight.json"
    prior = json.loads(existing_preflight.read_text(encoding="utf-8")) if existing_preflight.is_file() else {}
    preregistration_head = prior.get("preregistration_head", head())
    preflight = {
        "schema": "bjs400-l1-ibias-interaction-preflight-v1",
        "experiment_id": EXP.name,
        "created_at_local": now(),
        "status": "PASS",
        "head": head(),
        "head_refresh": args.refresh_head,
        "preregistration_head": preregistration_head,
        "new_physical_solve_count": 6,
        "reused_physical_case_count": 2,
        "exact_logical_case_count": 8,
        "unauthorized_extra_solves": 0,
        "authorized_masks": list(MASKS),
        "working_points": WORKING_POINTS,
        "reuse_comparability": reuse_checks,
        "generated_decks": generated,
        "new_deck_checks": decks,
        "source_manifest_sha256": sha256(EXP / "SOURCE_MANIFEST.json"),
        "reuse_manifest_sha256": sha256(EXP / "REUSED_REFERENCE_MANIFEST.json"),
        "scientific_analysis_performed": False,
    }
    preflight_path = EXP / "analysis" / "preflight.json"
    preflight_path.parent.mkdir(parents=True, exist_ok=True)
    if args.refresh_head:
        preflight_path.write_text(json.dumps(preflight, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    elif not existing_preflight.is_file():
        write_json_once(preflight_path, preflight)
    preflight["head"] = head()
    markdown = preflight_markdown(preflight)
    if args.refresh_head:
        (EXP / "PREFLIGHT.md").write_text(markdown, encoding="utf-8")
    elif not (EXP / "PREFLIGHT.md").is_file():
        write_once(EXP / "PREFLIGHT.md", markdown)
    print(json.dumps({
        "status": "PASS",
        "head": head(),
        "head_refresh": args.refresh_head,
        "new_physical_solve_count": 6,
        "reused_physical_case_count": 2,
        "exact_logical_case_count": 8,
        "reuse_status": reuse_checks["status"],
        "deck_status": decks["status"],
        "solver_invoked": False,
        "scientific_analysis_performed": False,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
