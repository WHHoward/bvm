#!/usr/bin/env python3
"""Register the bounded one-factor full closed-loop screening matrix."""

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
CURRENT = REPO / "test/exploration/bvm-population-scaling-rj2p12-l1p14-l2p20-ib260-rj32-bjs400-v1-20260910"
R10 = REPO / "test/exploration/bvm-population-rj2p10-weight3-diagnostic-l1p14-l2p20-ib260-rj32-bjs400-v1-20260911"
R11 = REPO / "test/exploration/bvm-population-scaling-rj2p11-midpoint-l1p14-l2p20-ib260-rj32-bjs400-v1-20260911"
SOLVER = REPO / "build/josim-cli"
CONTRACT_SENTENCE = "This experiment is governed by docs/EXPERIMENT_CONTRACT.md."
SOLVER_SHA256 = "48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2"
INPUT_HASHES = {
    "array_fixture_template.cir": "8971a82dfbac223b9be139f719afae2eb156f0f68fb2a4811858f0a0b482cf71",
    "bvm_jm2_connected.cir": "0093a45cc3910448b484d8bd004c6df8c22358bacc8b3ed5e23912dcab805d54",
    "jjmit.cir": "19862d1fd1f1f44dfa1523848d7d3b5e2594a6c5da8fdd80144b449e5312a336",
    "jtl2.cir": "ffd31f8eda2a86ca0133342be1ce678831b7237a53911eda046d2bff8454855a",
    "BQ_parameterized_bjs400.cir": "883308517d48470cbedab878f9e3c71721cd972db248c6b821ce5dba642ff810",
    "BQ_parameterized_bjs400_rj2.cir": "43468c49eb56090e586428a8ca26d17d8bbf107fbd9e535bbac7a72ed1200d42",
}
PARAMETERS = OrderedDict((
    ("BJ2_area", [1.6, 1.8, 2.2, 2.4]),
    ("Lin_pH", [1.0, 1.25, 1.75, 2.0]),
    ("L1_pH", [1.2, 1.6, 1.8, 2.0]),
    ("L2_pH", [1.6, 1.8, 2.2, 2.4]),
    ("RJ1_ohm", [24, 28, 36, 40]),
    ("IBias_uA", [240, 250, 270, 280]),
    ("BJ1_area", [0.75, 0.80, 1.00, 1.10]),
    ("BJS_area", [3.0, 3.5, 4.5, 5.0]),
    ("RJ2_ohm", [10, 14, 16]),
    ("L3_pH", [1.0, 1.6]),
))
BASELINE = {"Lin_pH": 1.5, "L1_pH": 1.4, "L2_pH": 2.0, "RJ1_ohm": 32.0, "RJ2_ohm": 12.0, "IBias_uA": 260.0, "BJS_area": 4.0, "BJ1_area": 0.9, "BJ2_area": 2.0, "L3_pH": 1.3}
MASKS = ("0011", "0111")


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


def write_once(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_text(encoding="utf-8") != content:
            raise RuntimeError(f"refusing to overwrite existing artifact: {path}")
        return
    path.write_text(content, encoding="utf-8")


def write_json_once(path: Path, value: Any, overwrite: bool = False) -> None:
    text = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    if overwrite and path.exists():
        path.write_text(text, encoding="utf-8")
        return
    write_once(path, text)


def token(value: float) -> str:
    text = f"{value:g}"
    return text.replace(".", "p").replace("-", "m")


def point_id(parameter: str, value: float) -> str:
    return f"{parameter}_{token(value)}"


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


def bq_variant(parameter: str, value: float) -> str:
    text = (EXP / "inputs/BQ_parameterized_bjs400_rj2.cir").read_text(encoding="utf-8")
    replacements = {
        "Lin_pH": ("Lin IN 1 1.5p", f"Lin IN 1 {value:g}p"),
        "L2_pH": ("L2 3 4 2p", f"L2 3 4 {value:g}p"),
        "BJS_area": ("BJs 1 2 jjmit area=4", f"BJs 1 2 jjmit area={value:g}"),
        "BJ1_area": ("BJ1 2 0 jjmit area=0.9", f"BJ1 2 0 jjmit area={value:g}"),
        "BJ2_area": ("BJ2 4 0 jjmit area=2", f"BJ2 4 0 jjmit area={value:g}"),
        "L3_pH": ("L3 4 OUT 1.3p", f"L3 4 OUT {value:g}p"),
    }
    if parameter in replacements:
        old, new = replacements[parameter]
        if text.count(old) != 1:
            raise RuntimeError(f"variant source token is not unique: {old}")
        text = text.replace(old, new, 1)
    return text


def active_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip() and not line.lstrip().startswith(("*", ".", "+"))]


def build_deck(parameter: str, value: float, mask: str, variant_name: str) -> str:
    base = (CURRENT / "references/reused/ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_0011/deck.cir").read_text(encoding="utf-8")
    replacements = {
        ".param L1_VALUE=1.4p": f".param L1_VALUE={value:g}p" if parameter == "L1_pH" else ".param L1_VALUE=1.4p",
        ".param IB_VALUE=260u": f".param IB_VALUE={value:g}u" if parameter == "IBias_uA" else ".param IB_VALUE=260u",
        ".param RJ1_VALUE=32": f".param RJ1_VALUE={value:g}" if parameter == "RJ1_ohm" else ".param RJ1_VALUE=32",
        ".param RJ2_VALUE=12": f".param RJ2_VALUE={value:g}" if parameter == "RJ2_ohm" else ".param RJ2_VALUE=12",
        ".include ../../inputs/BQ_parameterized_bjs400_rj2.cir": f".include ../../inputs/bq_variants/{variant_name}",
    }
    for old, new in replacements.items():
        if base.count(old) != 1:
            raise RuntimeError(f"base deck token is not unique: {old}")
        base = base.replace(old, new, 1)
    for instance in range(1, 5):
        for kind in ("WL", "BL", "SE"):
            prefix = f"I_{kind}{instance} "
            lines = [line for line in base.splitlines() if line.startswith(prefix)]
            if len(lines) != 1:
                raise RuntimeError(f"control line not unique: {prefix}")
            old = lines[0]
            active = mask[instance - 1] == "1"
            new = f"I_{kind}{instance} 0 {kind}{instance} {control_values(kind, active)}"
            base = base.replace(old, new, 1)
    header = f"* GENERATED FULL CLOSED-LOOP SCREEN DECK: {parameter}={value:g}; mask={mask}"
    base = base.replace(base.splitlines()[0], header, 1)
    return base


def check_deck(path: Path, parameter: str, value: float, mask: str, variant_name: str) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    lines = active_lines(text)
    failures: list[str] = []
    if sum(line.endswith("BVM") for line in lines) != 4 or sum(line.startswith("B_JSL") for line in lines) != 8:
        failures.append("BVM/JSL count mismatch")
    if sum(line == "XBQ1 QBIN QBOUT BQ" for line in lines) != 1 or sum(line.startswith("XJTL1_") and line.endswith(" jtl") for line in lines) != 6:
        failures.append("QB/JTL topology mismatch")
    if sum(line == "R_TERM JTL6_OUT 0 10" for line in lines) != 1:
        failures.append("terminal mismatch")
    for token_value in (".include ../../inputs/bvm_jm2_connected.cir", f".include ../../inputs/bq_variants/{variant_name}", ".include ../../inputs/jtl2.cir"):
        if token_value not in text:
            failures.append(f"missing source include: {token_value}")
    if [line for line in text.splitlines() if line.lower().startswith(".tran")] != [".tran 0.1p 200p"]:
        failures.append("tran mismatch")
    expected_params = {"L1_pH": "1.4", "IBias_uA": "260", "RJ1_ohm": "32", "RJ2_ohm": "12"}
    if parameter == "L1_pH": expected_params["L1_pH"] = f"{value:g}"
    if parameter == "IBias_uA": expected_params["IBias_uA"] = f"{value:g}"
    if parameter == "RJ1_ohm": expected_params["RJ1_ohm"] = f"{value:g}"
    if parameter == "RJ2_ohm": expected_params["RJ2_ohm"] = f"{value:g}"
    parameter_tokens = {"L1_pH": "L1_VALUE", "IBias_uA": "IB_VALUE", "RJ1_ohm": "RJ1_VALUE", "RJ2_ohm": "RJ2_VALUE"}
    for name, expected in expected_params.items():
        suffix = "p" if name == "L1_pH" else "u" if name == "IBias_uA" else ""
        if f".param {parameter_tokens[name]}={expected}{suffix}" not in text:
            failures.append(f"parameter mismatch: {name}")
    if any(line.startswith("I_REPLAY") for line in lines):
        failures.append("replay source present in full closed-loop deck")
    return {"status": "PASS" if not failures else "FAIL", "path": path.relative_to(REPO).as_posix(), "sha256": sha256(path), "bytes": path.stat().st_size, "parameter": parameter, "value": value, "mask": mask, "bvm_count": 4, "jsl_count": 8, "failures": failures}


def artifact(path: Path, role: str, origin: Path | None = None) -> dict[str, Any]:
    value: dict[str, Any] = {"path": path.relative_to(REPO).as_posix(), "sha256": sha256(path), "bytes": path.stat().st_size, "role": role}
    if origin is not None:
        value["origin_path"] = origin.relative_to(REPO).as_posix()
        value["origin_sha256"] = sha256(origin)
    return value


def structural_signature(path: Path) -> tuple[str, ...]:
    lines = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(("*", ".param", "I_WL", "I_BL", "I_SE")):
            continue
        lines.append(stripped)
    return tuple(lines)


def verify_reuse_cases() -> dict[str, Any]:
    cases = {
        "RJ2_10_0011": (R10 / "references/rj2p10/ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P10_0011", EXP / "references/reused_rj2p10/ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P10_0011", 10.0, "0011"),
        "RJ2_10_0111": (R10 / "runs/ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P10_0111", EXP / "references/reused_rj2p10/ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P10_0111", 10.0, "0111"),
        "RJ2_11_0011": (R11 / "runs/ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P11_0011", EXP / "references/reused_rj2p11/ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P11_0011", 11.0, "0011"),
        "RJ2_11_0111": (R11 / "runs/ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P11_0111", EXP / "references/reused_rj2p11/ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P11_0111", 11.0, "0111"),
    }
    baseline_signature = structural_signature(EXP / "references/baseline_rj2p12/ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_0011/deck.cir")
    records: dict[str, Any] = {}
    failures: list[str] = []
    for name, (origin, local, rj2, mask) in cases.items():
        local_failures: list[str] = []
        artifacts: dict[str, Any] = {}
        for suffix in ("raw.csv", "deck.cir", "metadata.json", "run.log"):
            source, copied = origin / suffix, local / suffix
            if not source.is_file() or not copied.is_file() or sha256(source) != sha256(copied):
                local_failures.append(f"not exact copied: {suffix}")
            if copied.is_file():
                artifacts[suffix] = {"source_sha256": sha256(source), "copied_sha256": sha256(copied), "bytes": copied.stat().st_size, "exact": source.is_file() and sha256(source) == sha256(copied)}
        if local.is_dir() and (local / "deck.cir").is_file() and structural_signature(local / "deck.cir") != baseline_signature:
            local_failures.append("topology/stimulus structural signature differs from current baseline")
        if (local / "deck.cir").is_file() and ".tran 0.1p 200p" not in (local / "deck.cir").read_text(encoding="utf-8"):
            local_failures.append("tran mismatch")
        if (local / "metadata.json").is_file():
            metadata = json.loads((local / "metadata.json").read_text(encoding="utf-8"))
            if metadata.get("mask") != mask or metadata.get("working_point", {}).get("RJ2_ohm") != rj2:
                local_failures.append("reuse metadata parameter/mask mismatch")
        records[name] = {"status": "PASS" if not local_failures else "FAIL", "source_path": origin.relative_to(REPO).as_posix(), "copied_path": local.relative_to(REPO).as_posix(), "RJ2_ohm": rj2, "mask": mask, "physical_solve_this_experiment": False, "artifacts": artifacts, "topology_structural_signature_matches_baseline": not local_failures, "failures": local_failures}
        failures.extend(f"{name}: {failure}" for failure in local_failures)
    return {"status": "PASS" if not failures else "FAIL", "cases": records, "failures": failures, "no_reuse_by_filename_only": True, "exact_copy_and_topology_checked": True}


def source_manifest(points: list[dict[str, Any]]) -> dict[str, Any]:
    inputs = []
    for name, role in (("array_fixture_template.cir", "current full closed-loop stimulus template"), ("bvm_jm2_connected.cir", "current BVM source include"), ("jjmit.cir", "current JJ model"), ("jtl2.cir", "current six-stage JTL"), ("BQ_parameterized_bjs400.cir", "current BQ baseline"), ("BQ_parameterized_bjs400_rj2.cir", "current canonical RJ2=12 BQ")):
        local = EXP / "inputs" / name
        origin = CURRENT / "inputs" / name
        if not local.is_file() or sha256(local) != sha256(origin) or (name in INPUT_HASHES and sha256(local) != INPUT_HASHES[name]):
            raise RuntimeError(f"source input mismatch: {name}")
        inputs.append(artifact(local, role, origin))
    variants = [artifact(EXP / "inputs/bq_variants" / f"{point['point_id']}.cir", "one-factor QB variant") for point in points]
    refs: dict[str, Any] = {}
    for root in (EXP / "references").glob("*/*"):
        if root.is_dir():
            refs[root.relative_to(EXP).as_posix()] = {name: artifact(root / name, "immutable reuse/reference") for name in ("raw.csv", "deck.cir", "metadata.json", "run.log")}
    reuse = verify_reuse_cases()
    return {"schema": "bvm-full-closed-loop-qb-screening-source-manifest-v1", "experiment_id": EXP.name, "created_at_local": now(), "repository_head_at_registration": head(), "remote_master_at_registration": remote_head(), "current_population_source_manifest": artifact(CURRENT / "SOURCE_MANIFEST.json", "current RJ2=12 population source manifest"), "current_population_packages": {"rj2p10": artifact(R10 / "handoff/bvm-population-rj2p10-weight3-diagnostic-l1p14-l2p20-ib260-rj32-bjs400-v1-20260911_corrected-v2_raw_handoff.zip", "latest RJ2=10 evidence"), "rj2p11": artifact(R11 / "handoff/bvm-population-scaling-rj2p11-midpoint-l1p14-l2p20-ib260-rj32-bjs400-v1-20260911_raw_handoff.zip", "latest RJ2=11 evidence"), "rj2p12": artifact(CURRENT / "handoff/bvm-population-scaling-rj2p12-l1p14-l2p20-ib260-rj32-bjs400-v1-20260910_raw_handoff.zip", "latest RJ2=12 evidence")}, "inputs": inputs, "variants": variants, "references": refs, "reuse_verification": reuse, "solver": {"path": str(SOLVER.relative_to(REPO)), "sha256": sha256(SOLVER), "bytes": SOLVER.stat().st_size, "version": subprocess.check_output([str(SOLVER), "--version"], cwd=REPO, text=True)}, "baseline": BASELINE, "logical_screening_point_count": len(points), "logical_screening_case_count": len(points) * 2, "reuse_case_count": 2, "maximum_new_screening_solve_count": len(points) * 2 - 2, "maximum_total_new_solve_count_including_validation": len(points) * 2, "no_replay": True, "no_passive_capture": True}


def preflight_markdown(record: dict[str, Any]) -> str:
    return "\n".join([
        "# Full closed-loop QB parameter screening — PREFLIGHT", "", CONTRACT_SENTENCE, "",
        f"- Experiment: `{EXP.name}`", f"- Initial registration HEAD: `{record['preregistration_head']}`", f"- Sealed preflight HEAD: `{record['head_at_preflight']}`", f"- Remote `bvm/master`: `{record.get('remote_master_at_preflight')}`", f"- Status: **{record['status']}**", "- Solver has not been invoked at preflight.", "",
        "## Exact matrix", "",
        "The 37 non-baseline one-factor points are each paired with masks `0011` (N2) and `0111` (N3), for 74 logical screening cases. Strictly equivalent RJ2=10/0011 and RJ2=10/0111 raw cases are reused, so the maximum number of new screening solves is 72; logical and physical counts will be reported separately. RJ2=12 baseline 0011/0111 and RJ2=11 context cases are immutable references.", "",
        "Priority order: `BJ2_area → Lin_pH → L1_pH → L2_pH → RJ1_ohm → IBias_uA → BJ1_area → BJS_area → RJ2_ohm(14,16) → L3_pH`.", "Each generated deck retains full BVM/COMMON_SL/JSL/QB/JTL/terminal topology, `.tran 0.1p 200p`, and the stored protocol. Exactly one QB parameter is changed per point; no JTL/BVM/stimulus/timestep change is registered.", "",
        "## Early stop", "",
        "A raw-supported `N2=2` and `N3=3` point is `DIRECT_2_TO_3_CANDIDATE` (class S): broad screening stops, then only the registered 0001 and 1111 full-population validation solves may be run. No combinations, positional checks or timestep checks start automatically. If no S point is found, stop with the bounded screening result and at most two promising A directions.", "",
        "## Evidence ceiling", "",
        "Raw CSV is authoritative. Phase is stored in radians; `rad/(2*pi)` is display/navigation only. Current threshold activity, voltage area, terminal area and response candidates are not SFQ counts. CONTROL contamination is a guardrail classification, not a parameter winner.", "",
        "Machine record: `analysis/preflight.json`.", "",
    ])


def matrix_markdown(points: list[dict[str, Any]]) -> str:
    lines = ["# Full closed-loop QB screening matrix", "", "All entries are full physical closed-loop decks. Each non-baseline point changes exactly one QB parameter and is paired with masks `0011` and `0111`. RJ2=10/0011 and RJ2=10/0111 are logical cases backed by exact immutable reuse references.", "", "| order | parameter | value | point id | N2 deck | N3 deck |", "|---:|---|---:|---|---|---|"]
    for order, item in enumerate(points, 1):
        lines.append(f"| {order} | `{item['parameter']}` | {item['value']:g} | `{item['point_id']}` | `{item['cases']['0011']['path']}` | `{item['cases']['0111']['path']}` |")
    lines.extend(["", "Logical screening cases: `74`. Maximum new screening solves after exact RJ2=10 reuse: `72`. Candidate validation may add only 0001 and 1111 at the selected point, maximum total new solves `74`.", ""])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh-head", action="store_true")
    args = parser.parse_args()
    points: list[dict[str, Any]] = []
    for parameter, values in PARAMETERS.items():
        for value in values:
            pid = point_id(parameter, value)
            variant = EXP / "inputs/bq_variants" / f"{pid}.cir"
            write_once(variant, bq_variant(parameter, value))
            item = {"parameter": parameter, "value": value, "point_id": pid, "variant_path": variant.relative_to(REPO).as_posix(), "variant_sha256": sha256(variant), "cases": {}}
            for mask in MASKS:
                deck = EXP / "screening/decks" / pid / f"{mask}.cir"
                write_once(deck, build_deck(parameter, value, mask, variant.name))
                item["cases"][mask] = check_deck(deck, parameter, value, mask, variant.name)
            points.append(item)
    failures = [f"{item['point_id']}/{mask}: {error}" for item in points for mask, case in item["cases"].items() for error in case["failures"]]
    manifest = source_manifest(points)
    failures.extend(f"reuse: {error}" for error in manifest["reuse_verification"]["failures"])
    write_json_once(EXP / "SOURCE_MANIFEST.json", manifest, overwrite=args.refresh_head)
    matrix = {"schema": "bvm-full-closed-loop-qb-screening-matrix-v1", "experiment_id": EXP.name, "created_at_local": now(), "baseline": BASELINE, "priority_order": list(PARAMETERS), "parameters": {key: values for key, values in PARAMETERS.items()}, "masks": list(MASKS), "logical_point_count": len(points), "logical_case_count": len(points) * 2, "points": points, "reuse_cases": {"RJ2_10_0011": "references/reused_rj2p10/ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P10_0011", "RJ2_10_0111": "references/reused_rj2p10/ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P10_0111"}, "candidate_validation_masks": ["0001", "0011", "0111", "1111"], "failures": failures}
    write_json_once(EXP / "screening/SCREENING_MATRIX.json", matrix, overwrite=args.refresh_head)
    matrix_md_path = EXP / "screening/SCREENING_MATRIX.md"
    matrix_md = matrix_markdown(points)
    if args.refresh_head and matrix_md_path.exists():
        matrix_md_path.write_text(matrix_md, encoding="utf-8")
    else:
        write_once(matrix_md_path, matrix_md)
    base = json.loads((EXP / "analysis/preflight.json").read_text(encoding="utf-8")) if (EXP / "analysis/preflight.json").is_file() else {"preregistration_head": head()}
    record: dict[str, Any] = {"schema": "bvm-full-closed-loop-qb-screening-preflight-v1", "experiment_id": EXP.name, "created_at_local": now(), "status": "PASS" if not failures else "FAIL", "preregistration_head": base.get("preregistration_head", head()), "head_at_preflight": head(), "head_refresh": args.refresh_head, "remote_master_at_preflight": remote_head(), "logical_screening_point_count": len(points), "logical_screening_case_count": len(points) * 2, "maximum_new_screening_solve_count": len(points) * 2 - 2, "maximum_total_new_solve_count_including_validation": len(points) * 2, "reuse_case_count": 2, "baseline_reference_case_count": 2, "authorized_masks": list(MASKS), "priority_order": list(PARAMETERS), "one_factor_only": True, "full_closed_loop_only": True, "no_replay": True, "no_passive_capture": True, "no_extra_parameter_values": True, "physical_solve_count_before_preflight": 0, "scientific_analysis_performed": False, "matrix_sha256": sha256(EXP / "screening/SCREENING_MATRIX.json"), "source_manifest_sha256": sha256(EXP / "SOURCE_MANIFEST.json"), "points": points, "failures": failures}
    text = json.dumps(record, ensure_ascii=False, indent=2) + "\n"
    output = EXP / "analysis/preflight.json"
    if args.refresh_head:
        output.write_text(text, encoding="utf-8")
        (EXP / "PREFLIGHT.md").write_text(preflight_markdown(record), encoding="utf-8")
    else:
        write_once(output, text)
        write_once(EXP / "PREFLIGHT.md", preflight_markdown(record))
    print(json.dumps({"status": record["status"], "logical_points": len(points), "logical_cases": len(points) * 2, "maximum_new_screening_solves": len(points) * 2 - 2, "physical_solve_count_before_preflight": 0, "solver_invoked": False, "failures": failures[:20]}, ensure_ascii=False, indent=2))
    return 0 if record["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
