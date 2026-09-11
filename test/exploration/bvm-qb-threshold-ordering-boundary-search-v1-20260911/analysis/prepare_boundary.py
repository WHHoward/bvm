#!/usr/bin/env python3
"""Register the two midpoint threshold-ordering boundary cases."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
PREVIOUS_SCREEN = REPO / "test/exploration/bvm-full-closed-loop-qb-parameter-screening-v1-20260911"
PREVIOUS_COMB = REPO / "test/exploration/bvm-qb-two-parameter-combination-v1-20260911"
SOLVER = REPO / "build/josim-cli"
SOLVER_SHA256 = "48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2"
CONTRACT_SENTENCE = "This experiment is governed by docs/EXPERIMENT_CONTRACT.md."
BASELINE = OrderedDict((("Lin_pH", 1.5), ("L1_pH", 1.4), ("L2_pH", 2.0), ("RJ1_ohm", 32.0), ("RJ2_ohm", 12.0), ("IBias_uA", 260.0), ("BJS_area", 4.0), ("BJ1_area", 0.9), ("BJ2_area", 2.0), ("L3_pH", 1.3)))
POINTS = (
    ("STAGE_A_L2_MIDPOINT", OrderedDict((("L2_pH", 1.8), ("L3_pH", 1.6)))),
    ("STAGE_B_IBIAS_MIDPOINT", OrderedDict((("IBias_uA", 250.0), ("L3_pH", 1.6)))),
)
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


def write_once(path: Path, text: str, overwrite: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not overwrite:
        if path.read_text(encoding="utf-8") != text:
            raise RuntimeError(f"refusing to overwrite: {path}")
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


def token(value: float) -> str:
    return f"{value:g}".replace(".", "p").replace("-", "m")


def variant_name(point_id: str, changes: OrderedDict[str, float]) -> str:
    return point_id + "_" + "_".join(f"{key}{token(value)}" for key, value in changes.items()) + ".cir"


def make_variant(changes: OrderedDict[str, float]) -> str:
    text = (EXP / "inputs/BQ_parameterized_bjs400_rj2.cir").read_text(encoding="utf-8")
    replacements = {"L2_pH": ("L2 3 4 2p", "L2 3 4 {value:g}p"), "L3_pH": ("L3 4 OUT 1.3p", "L3 4 OUT {value:g}p")}
    for key, value in changes.items():
        if key in replacements:
            old, template = replacements[key]
            if text.count(old) != 1:
                raise RuntimeError(f"nonunique BQ token: {old}")
            text = text.replace(old, template.format(value=value), 1)
    return text


def build_deck(point_id: str, changes: OrderedDict[str, float], mask: str, variant: str) -> str:
    base = (EXP / "references/canonical_baseline/0011/deck.cir").read_text(encoding="utf-8")
    current = dict(BASELINE)
    current.update(changes)
    replacements = {".param L1_VALUE=1.4p": f".param L1_VALUE={current['L1_pH']:g}p", ".param IB_VALUE=260u": f".param IB_VALUE={current['IBias_uA']:g}u", ".param RJ1_VALUE=32": f".param RJ1_VALUE={current['RJ1_ohm']:g}", ".param RJ2_VALUE=12": f".param RJ2_VALUE={current['RJ2_ohm']:g}", ".include ../../inputs/BQ_parameterized_bjs400_rj2.cir": f".include ../../inputs/bq_variants/{variant}"}
    for old, new in replacements.items():
        if base.count(old) != 1:
            raise RuntimeError(f"nonunique deck token: {old}")
        base = base.replace(old, new, 1)
    for instance in range(1, 5):
        for kind in ("WL", "BL", "SE"):
            prefix = f"I_{kind}{instance} "
            lines = [line for line in base.splitlines() if line.startswith(prefix)]
            if len(lines) != 1:
                raise RuntimeError(f"nonunique control line: {prefix}")
            base = base.replace(lines[0], f"I_{kind}{instance} 0 {kind}{instance} {control_values(kind, mask[instance - 1] == '1')}", 1)
    return base.replace(base.splitlines()[0], f"* GENERATED FULL CLOSED-LOOP THRESHOLD MIDPOINT DECK: {point_id}; mask={mask}", 1)


def active_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip() and not line.lstrip().startswith(("*", ".", "+"))]


def structural_signature(path: Path) -> tuple[str, ...]:
    lines = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(("*", ".param", "I_WL", "I_BL", "I_SE")) or "bq_variants/" in stripped or "BQ_parameterized_bjs400_rj2.cir" in stripped:
            continue
        lines.append(stripped)
    return tuple(lines)


def deck_check(path: Path, point_id: str, changes: OrderedDict[str, float], mask: str, variant: str) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    lines = active_lines(text)
    failures: list[str] = []
    if sum(line.endswith("BVM") for line in lines) != 4 or sum(line.startswith("B_JSL") for line in lines) != 8:
        failures.append("BVM/JSL count mismatch")
    if sum(line == "XBQ1 QBIN QBOUT BQ" for line in lines) != 1 or sum(line.startswith("XJTL1_") and line.endswith(" jtl") for line in lines) != 6:
        failures.append("QB/JTL count mismatch")
    if sum(line == "R_TERM JTL6_OUT 0 10" for line in lines) != 1:
        failures.append("terminal mismatch")
    for required in (".include ../../inputs/jjmit.cir", ".include ../../inputs/bvm_jm2_connected.cir", f".include ../../inputs/bq_variants/{variant}", ".include ../../inputs/jtl2.cir", ".tran 0.1p 200p"):
        if required not in text:
            failures.append(f"missing {required}")
    if "I_REPLAY" in text or "PASSIVE" in text.upper():
        failures.append("replay/passive token present")
    if structural_signature(path) != structural_signature(EXP / "references/canonical_baseline/0011/deck.cir"):
        failures.append("topology/protocol structural signature differs")
    return {"status": "PASS" if not failures else "FAIL", "path": path.relative_to(REPO).as_posix(), "sha256": sha256(path), "bytes": path.stat().st_size, "point_id": point_id, "mask": mask, "changes": changes, "failures": failures}


def artifact(path: Path, role: str, origin: Path | None = None) -> dict[str, Any]:
    value: dict[str, Any] = {"path": path.relative_to(REPO).as_posix(), "sha256": sha256(path), "bytes": path.stat().st_size, "role": role}
    if origin is not None:
        value["origin_path"] = origin.relative_to(REPO).as_posix()
        value["origin_sha256"] = sha256(origin)
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh-head", action="store_true")
    args = parser.parse_args()
    points: list[dict[str, Any]] = []
    failures: list[str] = []
    for point_id_value, changes in POINTS:
        name = variant_name(point_id_value, changes)
        variant_path = EXP / "inputs/bq_variants" / name
        write_once(variant_path, make_variant(changes))
        item: dict[str, Any] = {"point_id": point_id_value, "changes": changes, "variant_path": variant_path.relative_to(REPO).as_posix(), "variant_sha256": sha256(variant_path), "cases": {}}
        for mask in MASKS:
            deck = EXP / "screening/decks" / point_id_value / f"{mask}.cir"
            write_once(deck, build_deck(point_id_value, changes, mask, name))
            item["cases"][mask] = deck_check(deck, point_id_value, changes, mask, name)
            failures.extend(f"{point_id_value}/{mask}: {message}" for message in item["cases"][mask]["failures"])
        points.append(item)
    inputs = []
    for name, role in (("array_fixture_template.cir", "full closed-loop template"), ("bvm_jm2_connected.cir", "BVM include"), ("jjmit.cir", "JJ model"), ("jtl2.cir", "six-stage JTL"), ("BQ_parameterized_bjs400.cir", "BQ baseline"), ("BQ_parameterized_bjs400_rj2.cir", "BQ parameterized source")):
        local = EXP / "inputs" / name
        origin = PREVIOUS_SCREEN / "inputs" / name
        inputs.append(artifact(local, role, origin))
        if sha256(local) != sha256(origin):
            failures.append(f"input mismatch: {name}")
    origins = {
        "canonical_baseline": {"0011": PREVIOUS_SCREEN / "references/baseline_rj2p12/ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_0011", "0111": PREVIOUS_SCREEN / "references/baseline_rj2p12/ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_0111"},
        "l2_low_l3p16": {"0011": PREVIOUS_COMB / "runs/COMB_C01_0011", "0111": PREVIOUS_COMB / "runs/COMB_C01_0111"},
        "l2_high_l3p16": {"0011": PREVIOUS_SCREEN / "runs/SCREEN_L3_pH_1p6_0011", "0111": PREVIOUS_SCREEN / "runs/SCREEN_L3_pH_1p6_0111"},
        "ib_low_l3p16": {"0011": PREVIOUS_COMB / "runs/COMB_C07_0011", "0111": PREVIOUS_COMB / "runs/COMB_C07_0111"},
        "ib_high_l3p16": {"0011": PREVIOUS_SCREEN / "runs/SCREEN_L3_pH_1p6_0011", "0111": PREVIOUS_SCREEN / "runs/SCREEN_L3_pH_1p6_0111"},
    }
    references: dict[str, Any] = {}
    for group, masks in origins.items():
        for mask, origin in masks.items():
            reference_root = EXP / "references" / ("endpoints" if group != "canonical_baseline" else "")
            local = reference_root / group / mask
            key = f"{group}/{mask}"
            references[key] = {name: artifact(local / name, "immutable endpoint/reference", origin / name) for name in ("raw.csv", "deck.cir", "metadata.json", "run.log")}
            for name in ("raw.csv", "deck.cir", "metadata.json", "run.log"):
                if sha256(local / name) != sha256(origin / name):
                    failures.append(f"reference mismatch: {key}/{name}")
    previous_packages = {"screening": PREVIOUS_SCREEN / "handoff/bvm-full-closed-loop-qb-parameter-screening-v1-20260911_raw_handoff_v2.zip", "combination": PREVIOUS_COMB / "handoff/bvm-qb-two-parameter-combination-v1-20260911_raw_handoff.zip"}
    source_manifest = {"schema": "bvm-qb-threshold-ordering-boundary-source-manifest-v1", "experiment_id": EXP.name, "created_at_local": now(), "repository_head_at_registration": head(), "remote_master_at_registration": remote_head(), "inputs": inputs, "references": references, "variants": [artifact(REPO / point["variant_path"], "midpoint BQ variant") for point in points], "previous_packages": {key: artifact(path, "previous experiment package") for key, path in previous_packages.items()}, "baseline": BASELINE, "solver": {"path": SOLVER.relative_to(REPO).as_posix(), "sha256": sha256(SOLVER), "version": subprocess.check_output([str(SOLVER), "--version"], cwd=REPO, text=True)}, "logical_midpoint_count": 2, "logical_case_count": 4, "maximum_new_physical_solve_count": 4, "no_replay": True, "no_passive_capture": True, "no_source_scaling": True, "no_read_extension": True, "no_jtl_change": True, "no_timestep_change": True}
    source_path = EXP / "SOURCE_MANIFEST.json"
    write_once(source_path, json.dumps(source_manifest, ensure_ascii=False, indent=2) + "\n", overwrite=args.refresh_head)
    matrix = {"schema": "bvm-qb-threshold-ordering-boundary-matrix-v1", "experiment_id": EXP.name, "created_at_local": now(), "baseline": BASELINE, "fixed_L3_pH": 1.6, "points": points, "masks": list(MASKS), "logical_midpoint_count": 2, "logical_case_count": 4, "maximum_new_physical_solve_count": 4, "known_endpoints": {"L2": {"low": {"L2_pH": 1.6, "L3_pH": 1.6, "result": "1/3", "source": "references/endpoints/l2_low_l3p16"}, "midpoint": {"L2_pH": 1.8, "L3_pH": 1.6, "result": "PENDING"}, "high": {"L2_pH": 2.0, "L3_pH": 1.6, "result": "2/4", "source": "references/endpoints/l2_high_l3p16"}}, "IBias": {"low": {"IBias_uA": 240.0, "L3_pH": 1.6, "result": "1/3", "source": "references/endpoints/ib_low_l3p16"}, "midpoint": {"IBias_uA": 250.0, "L3_pH": 1.6, "result": "PENDING"}, "high": {"IBias_uA": 260.0, "L3_pH": 1.6, "result": "2/4", "source": "references/endpoints/ib_high_l3p16"}}}, "failures": failures}
    matrix_path = EXP / "boundary/BOUNDARY_MATRIX.json"
    write_once(matrix_path, json.dumps(matrix, ensure_ascii=False, indent=2) + "\n", overwrite=args.refresh_head)
    boundary_md = "\n".join(["# QB threshold-ordering boundary matrix", "", "| axis | low endpoint | midpoint | high endpoint | bounded interpretation |", "|---|---|---|---|---|", "| L2 with L3=1.6 pH | L2=1.6 -> 1/3 | L2=1.8 -> pending | L2=2.0 -> 2/4 | threshold ordering only; no exact continuous threshold |", "| IBias with L3=1.6 pH | IB=240 -> 1/3 | IB=250 -> pending | IB=260 -> 2/4 | threshold ordering only; no exact continuous threshold |", "", "Only the two midpoint rows are new physical solves. Endpoint files are immutable context and are not counted in the four-solve budget.", ""])
    write_once(EXP / "boundary/BOUNDARY_TABLE.md", boundary_md, overwrite=args.refresh_head)
    previous = json.loads((EXP / "analysis/preflight.json").read_text(encoding="utf-8")) if (EXP / "analysis/preflight.json").is_file() else {}
    record = {"schema": "bvm-qb-threshold-ordering-boundary-preflight-v1", "experiment_id": EXP.name, "created_at_local": now(), "status": "PASS" if not failures else "FAIL", "registration_head": previous.get("registration_head", head()), "head_at_preflight": head(), "remote_master_at_preflight": remote_head(), "logical_midpoint_count": 2, "logical_case_count": 4, "maximum_new_physical_solve_count": 4, "authorized_points": [point_id_value for point_id_value, _ in POINTS], "authorized_masks": list(MASKS), "fixed_L3_pH": 1.6, "phase_baseline_window_ps": [101.0, 110.0], "phase_navigation_thresholds_turns": [0.5, 1.5, 2.5, 3.5, 4.5], "corrected_control_windows_ps": [[70.0, 81.0], [81.0, 90.0], [90.0, 101.0], [101.0, 110.0]], "control_criterion": "unintended complete QBOUT->JTL1..6 propagation before FINAL READ", "rollback_excluded_from_control": True, "physical_solve_count_before_preflight": 0, "scientific_analysis_performed": False, "no_n1_n4_before_later_authorization": True, "matrix_sha256": sha256(matrix_path), "source_manifest_sha256": sha256(source_path), "failures": failures}
    preflight_path = EXP / "analysis/preflight.json"
    write_once(preflight_path, json.dumps(record, ensure_ascii=False, indent=2) + "\n", overwrite=args.refresh_head)
    preflight_md = "\n".join(["# QB threshold-ordering boundary search - PREFLIGHT", "", CONTRACT_SENTENCE, "", f"- Experiment: {EXP.name}", f"- Registration HEAD: {record['registration_head']}", f"- Sealed preflight HEAD: {record['head_at_preflight']}", f"- Remote bvm/master: {record.get('remote_master_at_preflight')}", "- Status: PASS", "- Solver has not been invoked at preflight.", "", "## Exact scope", "", "Only two midpoint points are registered: Stage A L2=1.8 pH, L3=1.6 pH and Stage B IBias=250 uA, L3=1.6 pH; each uses masks 0011 and 0111, for exactly four new physical solves. L3=1.6 is fixed and all other parameters remain canonical.", "", "## Corrected history/control", "", "Use only actual stored samples in 70-81 ps ZERO_STATE_READ_CONTROL, 81-90 ps idle, 90-101 ps WRITE1 and 101-110 ps SETTLE. CONTROL contamination requires an unintended complete QBOUT->JTL1->...->JTL6 chain in those windows. FINAL/Tail rollback is separate and cannot mark CONTROL.", "", "## Interpretation ceiling", "", "Phase is raw radians; rad/(2*pi) is navigation only and not an SFQ count. The midpoint result can only establish bounded threshold ordering under this model, history, load, solver and 0.1 ps grid. No L2=1.7/1.9, IB=245/255, N1/N4, positional validation, timestep refinement or third-parameter solve is authorized.", "", "## Stop", "", "After the four midpoint solves, or earlier if a clean N2=2/N3=3 is observed, stop at EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW. Any population validation requires later scientific authorization.", ""])
    write_once(EXP / "PREFLIGHT.md", preflight_md, overwrite=args.refresh_head)
    print(json.dumps({"status": record["status"], "logical_midpoints": 2, "logical_cases": 4, "maximum_new_physical_solves": 4, "failures": failures}, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
