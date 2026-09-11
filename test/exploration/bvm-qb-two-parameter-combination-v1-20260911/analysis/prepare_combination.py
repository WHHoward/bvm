#!/usr/bin/env python3
"""Register the bounded two-parameter full closed-loop combination matrix."""

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
PREVIOUS = REPO / "test/exploration/bvm-full-closed-loop-qb-parameter-screening-v1-20260911"
SOLVER = REPO / "build/josim-cli"
SOLVER_SHA256 = "48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2"
CONTRACT_SENTENCE = "This experiment is governed by docs/EXPERIMENT_CONTRACT.md."
INPUT_HASHES = {
    "array_fixture_template.cir": "8971a82dfbac223b9be139f719afae2eb156f0f68fb2a4811858f0a0b482cf71",
    "bvm_jm2_connected.cir": "0093a45cc3910448b484d8bd004c6df8c22358bacc8b3ed5e23912dcab805d54",
    "jjmit.cir": "19862d1fd1f1f44dfa1523848d7d3b5e2594a6c5da8fdd80144b449e5312a336",
    "jtl2.cir": "ffd31f8eda2a86ca0133342be1ce678831b7237a53911eda046d2bff8454855a",
    "BQ_parameterized_bjs400.cir": "883308517d48470cbedab878f9e3c71721cd972db248c6b821ce5dba642ff810",
    "BQ_parameterized_bjs400_rj2.cir": "43468c49eb56090e586428a8ca26d17d8bbf107fbd9e535bbac7a72ed1200d42",
}
BASELINE = OrderedDict((
    ("Lin_pH", 1.5), ("L1_pH", 1.4), ("L2_pH", 2.0), ("RJ1_ohm", 32.0),
    ("RJ2_ohm", 12.0), ("IBias_uA", 260.0), ("BJS_area", 4.0),
    ("BJ1_area", 0.9), ("BJ2_area", 2.0), ("L3_pH", 1.3),
))
POINTS = (
    ("C01", OrderedDict((("L2_pH", 1.6), ("L3_pH", 1.6)))),
    ("C02", OrderedDict((("L2_pH", 1.6), ("L1_pH", 1.2)))),
    ("C04", OrderedDict((("BJ1_area", 1.1), ("L3_pH", 1.6)))),
    ("C03", OrderedDict((("L2_pH", 1.6), ("RJ1_ohm", 40.0)))),
    ("C05", OrderedDict((("BJ1_area", 1.1), ("L1_pH", 1.2)))),
    ("C07", OrderedDict((("IBias_uA", 240.0), ("L3_pH", 1.6)))),
    ("C06", OrderedDict((("BJ1_area", 1.1), ("RJ1_ohm", 40.0)))),
    ("C08", OrderedDict((("IBias_uA", 240.0), ("L1_pH", 1.2)))),
    ("C09", OrderedDict((("IBias_uA", 240.0), ("RJ1_ohm", 40.0)))),
)
MASKS = ("0011", "0111")
BASELINE_CASES = {
    "0011": PREVIOUS / "references/baseline_rj2p12/ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_0011",
    "0111": PREVIOUS / "references/baseline_rj2p12/ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_0111",
}


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()


def remote_head() -> str | None:
    try:
        return subprocess.check_output(["git", "ls-remote", "bvm", "refs/heads/master"], cwd=REPO, text=True).split()[0]
    except (OSError, subprocess.CalledProcessError, IndexError):
        return None


def write_once(path: Path, text: str, *, overwrite: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not overwrite:
        if path.read_text(encoding="utf-8") != text:
            raise RuntimeError(f"refusing to overwrite registered artifact: {path}")
        return
    path.write_text(text, encoding="utf-8")


def token(value: float) -> str:
    return f"{value:g}".replace(".", "p").replace("-", "m")


def variant_name(point_id: str, changes: OrderedDict[str, float]) -> str:
    return point_id + "_" + "_".join(f"{key}{token(value)}" for key, value in changes.items()) + ".cir"


def bq_variant(changes: OrderedDict[str, float]) -> str:
    text = (EXP / "inputs/BQ_parameterized_bjs400_rj2.cir").read_text(encoding="utf-8")
    replacements = {
        "L2_pH": ("L2 3 4 2p", "L2 3 4 {value:g}p"),
        "BJ1_area": ("BJ1 2 0 jjmit area=0.9", "BJ1 2 0 jjmit area={value:g}"),
        "L3_pH": ("L3 4 OUT 1.3p", "L3 4 OUT {value:g}p"),
    }
    for parameter, value in changes.items():
        if parameter not in replacements:
            continue
        old, template = replacements[parameter]
        if text.count(old) != 1:
            raise RuntimeError(f"combination source token is not unique: {old}")
        text = text.replace(old, template.format(value=value), 1)
    return text


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


def build_deck(point_id: str, changes: OrderedDict[str, float], mask: str, variant: str) -> str:
    base = (EXP / "references/baseline_rj2p12/ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_0011/deck.cir").read_text(encoding="utf-8")
    current = dict(BASELINE)
    current.update(changes)
    replacements = {
        ".param L1_VALUE=1.4p": f".param L1_VALUE={current['L1_pH']:g}p",
        ".param IB_VALUE=260u": f".param IB_VALUE={current['IBias_uA']:g}u",
        ".param RJ1_VALUE=32": f".param RJ1_VALUE={current['RJ1_ohm']:g}",
        ".param RJ2_VALUE=12": f".param RJ2_VALUE={current['RJ2_ohm']:g}",
        ".include ../../inputs/BQ_parameterized_bjs400_rj2.cir": f".include ../../inputs/bq_variants/{variant}",
    }
    for old, new in replacements.items():
        if base.count(old) != 1:
            raise RuntimeError(f"base combination deck token is not unique: {old}")
        base = base.replace(old, new, 1)
    for instance in range(1, 5):
        for kind in ("WL", "BL", "SE"):
            prefix = f"I_{kind}{instance} "
            lines = [line for line in base.splitlines() if line.startswith(prefix)]
            if len(lines) != 1:
                raise RuntimeError(f"control line is not unique: {prefix}")
            base = base.replace(lines[0], f"I_{kind}{instance} 0 {kind}{instance} {control_values(kind, mask[instance - 1] == '1')}", 1)
    base = base.replace(base.splitlines()[0], f"* GENERATED FULL CLOSED-LOOP COMBINATION DECK: {point_id}; mask={mask}", 1)
    return base


def active_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip() and not line.lstrip().startswith(("*", ".", "+"))]


def structural_signature(path: Path) -> tuple[str, ...]:
    output = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(("*", ".param", "I_WL", "I_BL", "I_SE")) or "bq_variants/" in stripped or "BQ_parameterized_bjs400_rj2.cir" in stripped:
            continue
        output.append(stripped)
    return tuple(output)


def deck_check(path: Path, point_id: str, changes: OrderedDict[str, float], mask: str, variant: str) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    lines = active_lines(text)
    failures: list[str] = []
    if sum(line.endswith("BVM") for line in lines) != 4 or sum(line.startswith("B_JSL") for line in lines) != 8:
        failures.append("BVM/JSL topology count mismatch")
    if sum(line == "XBQ1 QBIN QBOUT BQ" for line in lines) != 1 or sum(line.startswith("XJTL1_") and line.endswith(" jtl") for line in lines) != 6:
        failures.append("QB/JTL topology mismatch")
    if sum(line == "R_TERM JTL6_OUT 0 10" for line in lines) != 1:
        failures.append("terminal mismatch")
    for include in (".include ../../inputs/jjmit.cir", ".include ../../inputs/bvm_jm2_connected.cir", f".include ../../inputs/bq_variants/{variant}", ".include ../../inputs/jtl2.cir"):
        if include not in text:
            failures.append(f"missing include: {include}")
    if ".tran 0.1p 200p" not in text:
        failures.append("timestep/stop mismatch")
    if "I_REPLAY" in text or "PASSIVE" in text.upper():
        failures.append("replay/passive source present")
    current = dict(BASELINE)
    current.update(changes)
    active_expected = {
        "L1_pH": f".param L1_VALUE={current['L1_pH']:g}p",
        "IBias_uA": f".param IB_VALUE={current['IBias_uA']:g}u",
        "RJ1_ohm": f".param RJ1_VALUE={current['RJ1_ohm']:g}",
        "RJ2_ohm": f".param RJ2_VALUE={current['RJ2_ohm']:g}",
    }
    for expected in active_expected.values():
        if expected not in text:
            failures.append(f"active parameter missing: {expected}")
    if structural_signature(path) != structural_signature(EXP / "references/baseline_rj2p12/ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_0011/deck.cir"):
        failures.append("full topology/protocol structural signature differs from baseline")
    return {"status": "PASS" if not failures else "FAIL", "path": path.relative_to(REPO).as_posix(), "sha256": sha256(path), "bytes": path.stat().st_size, "point_id": point_id, "mask": mask, "changes": changes, "failures": failures}


def artifact(path: Path, role: str, origin: Path | None = None) -> dict[str, Any]:
    record = {"path": path.relative_to(REPO).as_posix(), "sha256": sha256(path), "bytes": path.stat().st_size, "role": role}
    if origin is not None:
        record["origin_path"] = origin.relative_to(REPO).as_posix()
        record["origin_sha256"] = sha256(origin)
    return record


def matrix_markdown(points: list[dict[str, Any]]) -> str:
    lines = ["# Two-parameter full closed-loop QB combination matrix", "", "All points use the registered full BVM→COMMON_SL/JSL→QB→six-stage JTL→terminal topology, `.tran 0.1p 200p`, and masks `0011`/`0111`.", "", "| order | id | changed parameters | N2 deck | N3 deck |", "|---:|---|---|---|---|"]
    for index, point in enumerate(points, 1):
        changed = ", ".join(f"`{key}={value:g}`" for key, value in point["changes"].items())
        lines.append(f"| {index} | `{point['point_id']}` | {changed} | `{point['cases']['0011']['path']}` | `{point['cases']['0111']['path']}` |")
    lines.extend(["", "Registered combination points: `9`; logical cases: `18`; maximum new screening solves: `18`; validation, if and only if a clean S point is found: `0001` and `1111` (at most 2 additional solves).", ""])
    return "\n".join(lines)


def preflight_markdown(record: dict[str, Any]) -> str:
    return "\n".join([
        "# Two-parameter full closed-loop QB combination — PREFLIGHT", "", CONTRACT_SENTENCE, "",
        f"- Experiment: `{EXP.name}`", f"- Registration HEAD: `{record['registration_head']}`", f"- Sealed preflight HEAD: `{record['head_at_preflight']}`", f"- Remote `bvm/master`: `{record.get('remote_master_at_preflight')}`", "- Status: **PASS**", "- Solver has not been invoked at preflight.", "",
        "## Exact scope", "", "Nine registered two-parameter points run in order `C01 → C02 → C04 → C03 → C05 → C07 → C06 → C08 → C09`; each has exactly masks `0011` and `0111`. C01 is `L2=1.6pH + L3=1.6pH`; the other eight combinations are recorded in `screening/COMBINATION_MATRIX.json`. No third parameter, replay, passive capture, source scaling, read extension, JTL change or timestep change is registered.", "",
        "## Corrected CONTROL/history rule", "", "CONTROL/history is evaluated only on actual stored samples in `70≤t<81 ps` ZERO_STATE_READ_CONTROL, `81≤t<90 ps` post-control idle, `90≤t<101 ps` WRITE1 and `101≤t<110 ps` SETTLE. `CONTROL_CONTAMINATED` requires an unintended complete downstream `V(QBOUT) → V(JTL1_OUT) → ... → V(JTL6_OUT)` chain inside this history interval. Phase rollback after FINAL READ or TAIL is recorded separately and is never a CONTROL criterion.", "",
        "## Evidence ceiling", "", "Raw CSV is authoritative. P values remain radians; `rad/(2*pi)` is navigation/display only and never an SFQ count. Terminal area and voltage peaks are diagnostics, not event counts. No timestep convergence or parameter robustness is claimed in this experiment.", "",
        "## Stop", "", "A clean raw-supported N2=2/N3=3 pair is `DIRECT_2_TO_3_COMBINATION_CANDIDATE`, stops all not-yet-started combinations and permits only 0001/1111 validation. Otherwise the nine-point matrix ends at `NO_DIRECT_2_TO_3_TWO_PARAMETER_COMBINATION`; no third-parameter search starts automatically.", "",
    ])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh-head", action="store_true")
    args = parser.parse_args()
    points: list[dict[str, Any]] = []
    for point_id_value, changes in POINTS:
        variant = variant_name(point_id_value, changes)
        variant_path = EXP / "inputs/bq_variants" / variant
        write_once(variant_path, bq_variant(changes))
        item: dict[str, Any] = {"point_id": point_id_value, "changes": changes, "variant_path": variant_path.relative_to(REPO).as_posix(), "variant_sha256": sha256(variant_path), "cases": {}}
        for mask in MASKS:
            deck = EXP / "screening/decks" / point_id_value / f"{mask}.cir"
            write_once(deck, build_deck(point_id_value, changes, mask, variant))
            item["cases"][mask] = deck_check(deck, point_id_value, changes, mask, variant)
        points.append(item)
    failures = [f"{point['point_id']}/{mask}: {message}" for point in points for mask, case in point["cases"].items() for message in case["failures"]]
    inputs = []
    for name, role in (("array_fixture_template.cir", "historical full-closed-loop template"), ("bvm_jm2_connected.cir", "BVM source include"), ("jjmit.cir", "JJ model"), ("jtl2.cir", "six-stage JTL"), ("BQ_parameterized_bjs400.cir", "BQ baseline source"), ("BQ_parameterized_bjs400_rj2.cir", "BQ canonical parameterized source")):
        local = EXP / "inputs" / name
        origin = PREVIOUS / "inputs" / name
        if sha256(local) != sha256(origin) or sha256(local) != INPUT_HASHES[name]:
            failures.append(f"input mismatch: {name}")
        inputs.append(artifact(local, role, origin))
    references = {}
    for mask, origin in BASELINE_CASES.items():
        local = EXP / "references/baseline_rj2p12" / origin.name
        references[local.relative_to(EXP).as_posix()] = {name: artifact(local / name, "immutable canonical baseline reference", origin / name) for name in ("raw.csv", "deck.cir", "metadata.json", "run.log")}
    source_manifest = {
        "schema": "bvm-qb-two-parameter-combination-source-manifest-v1", "experiment_id": EXP.name, "created_at_local": now(), "repository_head_at_registration": head(), "remote_master_at_registration": remote_head(),
        "previous_screening_experiment": {"id": PREVIOUS.name, "package_path": (PREVIOUS / "handoff/bvm-full-closed-loop-qb-parameter-screening-v1-20260911_raw_handoff_v2.zip").relative_to(REPO).as_posix(), "package_sha256": sha256(PREVIOUS / "handoff/bvm-full-closed-loop-qb-parameter-screening-v1-20260911_raw_handoff_v2.zip"), "matrix_sha256": sha256(PREVIOUS / "screening/SCREENING_MATRIX.json"), "table_sha256": sha256(PREVIOUS / "screening/SCREENING_TABLE.json")},
        "inputs": inputs, "references": references, "variants": [artifact(REPO / point["variant_path"], "two-parameter QB variant") for point in points], "baseline": BASELINE,
        "solver": {"path": SOLVER.relative_to(REPO).as_posix(), "sha256": sha256(SOLVER), "version": subprocess.check_output([str(SOLVER), "--version"], cwd=REPO, text=True)}, "logical_combination_point_count": len(points), "logical_combination_case_count": len(points) * 2, "maximum_new_physical_solve_count": len(points) * 2, "maximum_total_new_solve_count_including_validation": len(points) * 2 + 2, "no_replay": True, "no_passive_capture": True, "no_source_scaling": True, "no_read_extension": True, "no_jtl_change": True, "no_timestep_change": True,
    }
    manifest_path = EXP / "SOURCE_MANIFEST.json"
    write_once(manifest_path, json.dumps(source_manifest, ensure_ascii=False, indent=2) + "\n", overwrite=args.refresh_head)
    matrix = {"schema": "bvm-qb-two-parameter-combination-matrix-v1", "experiment_id": EXP.name, "created_at_local": now(), "baseline": BASELINE, "execution_order": [point_id_value for point_id_value, _ in POINTS], "points": points, "masks": list(MASKS), "logical_combination_point_count": len(points), "logical_combination_case_count": len(points) * 2, "maximum_new_physical_solve_count": len(points) * 2, "candidate_validation_masks": ["0001", "0011", "0111", "1111"], "failures": failures}
    write_once(EXP / "screening/COMBINATION_MATRIX.json", json.dumps(matrix, ensure_ascii=False, indent=2) + "\n", overwrite=args.refresh_head)
    write_once(EXP / "screening/COMBINATION_MATRIX.md", matrix_markdown(points), overwrite=args.refresh_head)
    previous = json.loads((EXP / "analysis/preflight.json").read_text(encoding="utf-8")) if (EXP / "analysis/preflight.json").is_file() else {}
    record = {"schema": "bvm-qb-two-parameter-combination-preflight-v1", "experiment_id": EXP.name, "created_at_local": now(), "status": "PASS" if not failures else "FAIL", "registration_head": previous.get("registration_head", head()), "head_at_preflight": head(), "remote_master_at_preflight": remote_head(), "logical_combination_point_count": len(points), "logical_combination_case_count": len(points) * 2, "maximum_new_physical_solve_count": len(points) * 2, "maximum_total_new_solve_count_including_validation": len(points) * 2 + 2, "execution_order": [point_id_value for point_id_value, _ in POINTS], "authorized_masks": list(MASKS), "corrected_control_windows_ps": [[70.0, 81.0], [81.0, 90.0], [90.0, 101.0], [101.0, 110.0]], "control_complete_chain_thresholds": {"QBOUT_V": 2.0e-4, "JTL_V": 2.0e-4}, "phase_baseline_window_ps": [101.0, 110.0], "phase_thresholds_turns": [0.5, 1.5, 2.5, 3.5, 4.5], "physical_solve_count_before_preflight": 0, "scientific_analysis_performed": False, "matrix_sha256": sha256(EXP / "screening/COMBINATION_MATRIX.json"), "source_manifest_sha256": sha256(manifest_path), "failures": failures}
    write_once(EXP / "analysis/preflight.json", json.dumps(record, ensure_ascii=False, indent=2) + "\n", overwrite=args.refresh_head)
    write_once(EXP / "PREFLIGHT.md", preflight_markdown(record), overwrite=args.refresh_head)
    print(json.dumps({"status": record["status"], "points": len(points), "logical_cases": len(points) * 2, "maximum_new_physical_solves": len(points) * 2, "failures": failures}, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
