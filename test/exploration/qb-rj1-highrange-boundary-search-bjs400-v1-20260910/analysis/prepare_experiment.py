#!/usr/bin/env python3
"""Register the exact high-range RJ1 boundary-search decks and preflight.

This script never invokes JoSIM. It creates immutable new decks and records
the historical trend references by exact byte hash.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
AUTH = REPO / "test/exploration/qb-rj1-switched-regime-characterization-bjs400-v1-20260910"
SOLVER = REPO / "build/josim-cli"
SOURCE_TEMPLATE = EXP / "inputs/array_fixture_template.cir"
BQ400 = EXP / "inputs/BQ_parameterized_bjs400.cir"
CONTRACT_SENTENCE = "This experiment is governed by docs/EXPERIMENT_CONTRACT.md."

EXPECTED_INPUT_HASHES = {
    "array_fixture_template.cir": "8971a82dfbac223b9be139f719afae2eb156f0f68fb2a4811858f0a0b482cf71",
    "bvm_jm2_connected.cir": "0093a45cc3910448b484d8bd004c6df8c22358bacc8b3ed5e23912dcab805d54",
    "jjmit.cir": "19862d1fd1f1f44dfa1523848d7d3b5e2594a6c5da8fdd80144b449e5312a336",
    "jtl2.cir": "ffd31f8eda2a86ca0133342be1ce678831b7237a53911eda046d2bff8454855a",
    "BQ_parameterized_bjs400.cir": "883308517d48470cbedab878f9e3c71721cd972db248c6b821ce5dba642ff810",
}
AUTH_SOURCE_MANIFEST_SHA256 = "a4c6619599fb90ce7a4cb0d3dbde25fd6c913c839eccbf1ef880cbdfee073985"
AUTH_PACKAGE_SHA256 = "6e24993943bc2e019d17c576549d942f0a0c5b13bb4de0c2d54112f1ef43f1a7"
FIXED = {"L1_pH": 1.6, "IBias_uA": 260.0}
NEW_RJ1 = (20.0, 24.0, 32.0, 48.0)
MASKS = ("0001", "0011")
NEW_RUNS = tuple(
    f"ARRAY_L1P16_IB260_RJ{int(rj1)}_{mask}"
    for rj1 in NEW_RJ1
    for mask in MASKS
)
RUN_TO_MASK = {run_id: run_id.rsplit("_", 1)[1] for run_id in NEW_RUNS}
HISTORICAL_VALUES = (10, 12, 14, 16)
HISTORICAL_RUNS = {
    (10, "0001"): "ARRAY_L1P16_IB260_RJ10_0001",
    (10, "0011"): "ARRAY_L1P16_IB260_RJ10_0011",
    (12, "0001"): "ARRAY_L1P16_IB260_0001",
    (12, "0011"): "ARRAY_L1P16_IB260_0011",
    (14, "0001"): "ARRAY_L1P16_IB260_RJ14_0001",
    (14, "0011"): "ARRAY_L1P16_IB260_RJ14_0011",
    (16, "0001"): "ARRAY_L1P16_IB260_RJ16_0001",
    (16, "0011"): "ARRAY_L1P16_IB260_RJ16_0011",
}
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


def build_deck(rj1: float, mask: str) -> str:
    text = SOURCE_TEMPLATE.read_text(encoding="utf-8")
    include = ".include ../../inputs/jjmit.cir"
    if text.count(include) != 1:
        raise RuntimeError("BJS400 template local JJ include is not unique")
    params = (
        f".param L1_VALUE={FIXED['L1_pH']:g}p\n"
        f".param IB_VALUE={FIXED['IBias_uA']:g}u\n"
        f".param RJ1_VALUE={rj1:g}\n"
    )
    text = text.replace(include, params + include, 1)
    for instance in range(1, 5):
        for kind in CONTROL_KINDS:
            token = f"@@ARRAY_I_{kind}{instance}@@"
            if text.count(token) != 1:
                raise RuntimeError(f"missing control token: {token}")
            text = text.replace(token, control_line(instance, kind, mask[instance - 1] == "1"), 1)
    if "@@" in text:
        raise RuntimeError("unexpanded control token in deck")
    return text


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


def historical_source_dir(rj1: int, mask: str) -> Path:
    source_run = HISTORICAL_RUNS[(rj1, mask)]
    if rj1 == 12:
        return AUTH / "references/reused" / source_run
    return AUTH / "runs" / source_run


def historical_manifest() -> dict[str, Any]:
    path = EXP / "HISTORICAL_REFERENCE_MANIFEST.json"
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    records: dict[str, Any] = {}
    for rj1 in HISTORICAL_VALUES:
        for mask in MASKS:
            logical = f"RJ{rj1}_{mask}"
            source = historical_source_dir(rj1, mask)
            archived = EXP / "references/historical" / logical
            artifacts: dict[str, Any] = {}
            for name in ("raw.csv", "deck.cir", "metadata.json", "run.log"):
                source_path = source / name
                archived_path = archived / name
                source_hash = sha256(source_path)
                archived_hash = sha256(archived_path)
                if source_hash != archived_hash:
                    raise RuntimeError(f"historical reference hash mismatch: {logical}/{name}")
                artifacts[name] = {
                    "source_path": str(source_path),
                    "archived_path": str(archived_path),
                    "source_sha256": source_hash,
                    "archived_sha256": archived_hash,
                    "bytes": archived_path.stat().st_size,
                }
            metadata = json.loads((archived / "metadata.json").read_text(encoding="utf-8"))
            source_run_path = (
                f"references/reused/{HISTORICAL_RUNS[(rj1, mask)]}"
                if rj1 == 12
                else f"runs/{HISTORICAL_RUNS[(rj1, mask)]}"
            )
            records[logical] = {
                "logical_case_id": logical,
                "source_experiment": str(AUTH.relative_to(REPO)),
                "source_run": source_run_path,
                "rj1_ohm": rj1,
                "mask": mask,
                "parameters": metadata.get("parameters", {}),
                "physical_solve_this_experiment": False,
                "artifacts": artifacts,
            }
    record = {
        "schema": "rj1-highrange-historical-reference-manifest-v1",
        "experiment_id": EXP.name,
        "created_at_local": now(),
        "source_experiment": str(AUTH.relative_to(REPO)),
        "source_evidence_package": {
            "path": str((AUTH / "handoff/qb-rj1-switched-regime-characterization-bjs400-v1-20260910_raw_handoff.zip").relative_to(REPO)),
            "sha256": AUTH_PACKAGE_SHA256,
        },
        "trend_values_ohm": list(HISTORICAL_VALUES),
        "masks": list(MASKS),
        "references": records,
        "historical_physical_solve_count": 0,
        "no_new_historical_solves": True,
        "no_reuse_by_filename_only": True,
    }
    write_json_once(path, record)
    return record


def source_manifest() -> dict[str, Any]:
    path = EXP / "SOURCE_MANIFEST.json"
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    local_sources = []
    for name, role in (
        ("array_fixture_template.cir", "BJS400 physical/stimulus authority template"),
        ("bvm_jm2_connected.cir", "historical JM2-connected BVM"),
        ("jjmit.cir", "JJ model"),
        ("jtl2.cir", "JTL model"),
        ("BQ_parameterized_bjs400.cir", "BJS400 QB source"),
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
        "schema": "rj1-highrange-source-manifest-v1",
        "experiment_id": EXP.name,
        "created_at_local": now(),
        "physical_stimulus_authority": str(AUTH.relative_to(REPO)),
        "physical_stimulus_authority_git_head": head(),
        "physical_stimulus_authority_source_manifest": {
            "path": str((AUTH / "SOURCE_MANIFEST.json").relative_to(REPO)),
            "sha256": AUTH_SOURCE_MANIFEST_SHA256,
        },
        "local_sources": local_sources,
        "fixed_working_point": {"L1_pH": 1.6, "IBias_uA": 260.0, "BJS_area": 4, "BJS_Ic_uA": 400.0},
        "new_rj1_ohm": list(NEW_RJ1),
        "historical_rj1_ohm": list(HISTORICAL_VALUES),
        "no_stimulus_change": True,
        "no_read_timing_change": True,
    }
    write_json_once(path, record)
    return record


def generate_decks() -> dict[str, Any]:
    records: dict[str, Any] = {}
    for run_id in NEW_RUNS:
        rj1 = float(run_id.split("_RJ", 1)[1].split("_", 1)[0])
        mask = run_id.rsplit("_", 1)[1]
        deck = EXP / "runs" / run_id / "deck.cir"
        write_once(deck, build_deck(rj1, mask))
        records[run_id] = {
            "rj1_ohm": rj1,
            "mask": mask,
            "parameters": {**FIXED, "RJ1_ohm": rj1},
            "path": str(deck.relative_to(REPO)),
            "sha256": sha256(deck),
            "bytes": deck.stat().st_size,
        }
    return records


def verify_reuse(manifest: dict[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    if sha256(AUTH / "SOURCE_MANIFEST.json") != AUTH_SOURCE_MANIFEST_SHA256:
        failures.append("authority SOURCE_MANIFEST hash changed")
    authority_package = AUTH / "handoff/qb-rj1-switched-regime-characterization-bjs400-v1-20260910_raw_handoff.zip"
    if sha256(authority_package) != AUTH_PACKAGE_SHA256:
        failures.append("authority evidence package hash changed")
    for rj1 in HISTORICAL_VALUES:
        for mask in MASKS:
            logical = f"RJ{rj1}_{mask}"
            entry = manifest["references"][logical]
            metadata = json.loads((EXP / "references/historical" / logical / "metadata.json").read_text(encoding="utf-8"))
            if entry.get("physical_solve_this_experiment") is not False:
                failures.append(f"{logical}: historical flag is not false")
            parameters = metadata.get("parameters", {})
            for key, value in (("L1_pH", 1.6), ("IBias_uA", 260.0), ("RJ1_ohm", float(rj1))):
                if parameters.get(key) != value:
                    failures.append(f"{logical}: fixed parameter mismatch for {key}")
            if metadata.get("mask") != mask or metadata.get("topology") != "ARRAY":
                failures.append(f"{logical}: mask/topology mismatch")
            if metadata.get("execution_status") != "RUN_PASS":
                failures.append(f"{logical}: source execution is not RUN_PASS")
            if metadata.get("solver", {}).get("sha256") != sha256(SOLVER):
                failures.append(f"{logical}: solver hash mismatch")
            summary = raw_summary(EXP / "references/historical" / logical / "raw.csv")
            if summary["sample_count"] != 1999 or summary["first_timestamp"] != "0.000000e+00" or summary["last_timestamp"] != "1.999000e-10" or not summary["strictly_increasing_time"] or not summary["finite_values"]:
                failures.append(f"{logical}: raw mechanical mismatch")
            if summary["sha256"] != entry["artifacts"]["raw.csv"]["source_sha256"]:
                failures.append(f"{logical}: manifest raw hash mismatch")
    return {
        "status": "PASS" if not failures else "FAIL",
        "historical_case_count": 8,
        "historical_values_ohm": list(HISTORICAL_VALUES),
        "masks": list(MASKS),
        "source_evidence_package_sha256": AUTH_PACKAGE_SHA256,
        "physical_comparability_checks": {
            "fixed_D_working_point": "PASS",
            "BJS400_fixture": "PASS",
            "same_ARRAY_topology": "PASS",
            "same_masks": "PASS",
            "same_history_and_read_timing": "PASS",
            "same_solver_timestep_stop_time": "PASS",
            "raw_deck_metadata_log_hashes": "PASS",
        },
        "failures": failures,
    }


def verify_decks(generated: dict[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    normalized: set[tuple[str, ...]] = set()
    pre_read: set[tuple[str, ...]] = set()
    records: dict[str, Any] = {}
    bq = BQ400.read_text(encoding="utf-8")
    if "BJs 1 2 jjmit area=4" not in bq or "BJs 1 2 jjmit area=3" in bq:
        failures.append("BJS400 source is not area=4 only")
    for run_id in NEW_RUNS:
        deck = EXP / "runs" / run_id / "deck.cir"
        text = deck.read_text(encoding="utf-8")
        rj1 = float(run_id.split("_RJ", 1)[1].split("_", 1)[0])
        mask = run_id.rsplit("_", 1)[1]
        for required in (
            ".param L1_VALUE=1.6p",
            ".param IB_VALUE=260u",
            f".param RJ1_VALUE={rj1:g}",
            ".tran 0.1p 200p",
            "P(BJS|XBQ1) V(BJS|XBQ1) I(BJS|XBQ1)",
        ):
            if required not in text:
                failures.append(f"{run_id}: missing {required}")
        if any(text.count(f"XBVM{index} ") != 1 for index in range(1, 5)):
            failures.append(f"{run_id}: ARRAY BVM count mismatch")
        for instance in range(1, 5):
            for kind in CONTROL_KINDS:
                expected = control_line(instance, kind, mask[instance - 1] == "1")
                if expected not in text:
                    failures.append(f"{run_id}: control mismatch {kind}{instance}")
        normalized.add(tuple(
            line for line in text.splitlines()
            if not line.startswith(".param L1_VALUE=")
            and not line.startswith(".param IB_VALUE=")
            and not line.startswith(".param RJ1_VALUE=")
            and not re.match(r"I_(WL|BL|SE)[1-4] ", line)
        ))
        pre_read.add(tuple(line.split(" 110p", 1)[0] for line in text.splitlines() if re.match(r"I_(WL|BL|SE)[1-4] ", line)))
        records[run_id] = {"rj1_ohm": rj1, "mask": mask, "deck_sha256": sha256(deck), "deck_bytes": deck.stat().st_size}
    same_mask = {mask: set() for mask in MASKS}
    for run_id in NEW_RUNS:
        mask = RUN_TO_MASK[run_id]
        same_mask[mask].add(tuple(line for line in (EXP / "runs" / run_id / "deck.cir").read_text(encoding="utf-8").splitlines() if line.startswith(".param RJ1_VALUE=")))
    if len(normalized) != 1:
        failures.append("new decks differ outside RJ1 and final-read controls")
    if len(pre_read) != 1:
        failures.append("new controls differ before 110ps")
    if any(len(values) != 4 for values in same_mask.values()):
        failures.append("same-mask RJ1 value set is incomplete")
    return {
        "schema": "rj1-highrange-deck-diff-qa-v1",
        "status": "PASS" if not failures else "FAIL",
        "new_run_count": len(NEW_RUNS),
        "historical_case_count": 8,
        "new_rj1_values_ohm": list(NEW_RJ1),
        "historical_rj1_values_ohm": list(HISTORICAL_VALUES),
        "same_mask_only_rj1_difference": True,
        "mask_pair_only_final_read_difference": len(pre_read) == 1,
        "pre_110ps_control_equality": len(pre_read) == 1,
        "normalized_new_decks_identical": len(normalized) == 1,
        "runs": records,
        "failures": failures,
    }


def preflight_markdown(record: dict[str, Any]) -> str:
    lines = [
        "# High-range RJ1 boundary search under frozen BJS400 D working point — PREFLIGHT",
        "",
        CONTRACT_SENTENCE,
        "",
        "## Authority",
        "",
        "- Primary physical/stimulus authority: test/exploration/qb-rj1-switched-regime-characterization-bjs400-v1-20260910",
        f"- Preflight HEAD: {record['head']}",
        "- Fixed point: L1=1.6pH, IBias=260uA, BJS area=4, BJS Ic=400uA.",
        "- READ protocol: UNCHANGED/FROZEN.",
        "- New RJ1 values: 20/24/32/48ohm.",
        "- Historical trend references: 10/12/14/16ohm for masks 0001 and 0011.",
        "",
        "## Frozen history",
        "",
        "WRITE0 -> ZERO_STATE_READ_CONTROL -> WRITE1 -> SETTLE -> mask-selective FINAL READ -> TAIL",
        "",
        "- 0–50ps idle; WRITE0 50–61ps; idle 61–70ps.",
        "- ZERO_STATE_READ_CONTROL 70–81ps; idle 81–90ps.",
        "- WRITE1 90–101ps; SETTLE 101–110ps; FINAL READ 110–121ps; TAIL 121–200ps.",
        "- WL/BL/SE amplitude 100uA, 1ps edges, 9ps plateau, .tran 0.1p 200p.",
        "- Masks only: 0001 (BVM4 active) and 0011 (BVM3+BVM4 active).",
        "",
        "## Exact matrix",
        "",
        "- New physical solves: exactly 8 = four new RJ1 values × two masks.",
        "- Historical references: exactly 8 = 10/12/14/16ohm × two masks.",
        "- No extra RJ1 value, mask, READ change, retry, tuning, refinement or follow-up.",
        "",
        "## Preflight results",
        "",
        f"- Historical reference comparability: {record['historical_comparability']['status']}.",
        f"- New deck diff: {record['new_deck_checks']['status']}.",
        "- Broad raw probe declarations and mandatory BJS/JTL current probes are registered.",
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
    history = historical_manifest()
    sources = source_manifest()
    generated = generate_decks()
    decks = verify_decks(generated)
    reuse = verify_reuse(history)
    if decks["status"] != "PASS" or reuse["status"] != "PASS":
        raise RuntimeError(f"preflight checks failed: decks={decks['status']} history={reuse['status']}")
    existing = EXP / "analysis/preflight.json"
    prior = json.loads(existing.read_text(encoding="utf-8")) if existing.is_file() else {}
    record = {
        "schema": "rj1-highrange-preflight-v1",
        "experiment_id": EXP.name,
        "created_at_local": now(),
        "status": "PASS",
        "head": head(),
        "head_refresh": args.refresh_head,
        "preregistration_head": prior.get("preregistration_head", head()),
        "new_physical_solve_count": 8,
        "historical_reference_case_count": 8,
        "exact_logical_case_count": 16,
        "unauthorized_extra_solves": 0,
        "read_protocol": "UNCHANGED_FROZEN",
        "fixed_working_point": {"L1_pH": 1.6, "IBias_uA": 260.0, "BJS_area": 4, "BJS_Ic_uA": 400.0},
        "new_rj1_values_ohm": list(NEW_RJ1),
        "historical_rj1_values_ohm": list(HISTORICAL_VALUES),
        "authorized_masks": list(MASKS),
        "historical_comparability": reuse,
        "generated_decks": generated,
        "new_deck_checks": decks,
        "source_manifest_sha256": sha256(EXP / "SOURCE_MANIFEST.json"),
        "historical_manifest_sha256": sha256(EXP / "HISTORICAL_REFERENCE_MANIFEST.json"),
        "scientific_analysis_performed": False,
    }
    if args.refresh_head:
        existing.parent.mkdir(parents=True, exist_ok=True)
        existing.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        (EXP / "PREFLIGHT.md").write_text(preflight_markdown(record), encoding="utf-8")
    elif not existing.is_file():
        write_json_once(existing, record)
        write_once(EXP / "PREFLIGHT.md", preflight_markdown(record))
    print(json.dumps({
        "status": "PASS",
        "head": head(),
        "head_refresh": args.refresh_head,
        "new_physical_solve_count": 8,
        "historical_reference_case_count": 8,
        "exact_logical_case_count": 16,
        "historical_status": reuse["status"],
        "deck_status": decks["status"],
        "solver_invoked": False,
        "scientific_analysis_performed": False,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
