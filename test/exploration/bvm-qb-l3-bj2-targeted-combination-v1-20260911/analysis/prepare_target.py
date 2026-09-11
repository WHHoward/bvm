#!/usr/bin/env python3
"""Register the targeted L3 plus BJ2-area full closed-loop experiment."""

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
PREVIOUS = REPO / "test/exploration/bvm-qb-l3-highside-selective-window-v1-20260911"
PREVIOUS_OFAT = REPO / "test/exploration/bvm-full-closed-loop-qb-parameter-screening-v1-20260911"
SOLVER = REPO / "build/josim-cli"
SOLVER_SHA256 = "48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2"
CONTRACT_SENTENCE = "This experiment is governed by docs/EXPERIMENT_CONTRACT.md."
BASELINE = OrderedDict((("Lin_pH", 1.5), ("L1_pH", 1.4), ("L2_pH", 2.0), ("RJ1_ohm", 32.0), ("RJ2_ohm", 12.0), ("IBias_uA", 260.0), ("BJS_area", 4.0), ("BJ1_area", 0.9), ("BJ2_area", 2.0), ("L3_pH", 1.3)))
POINTS = (("TARGET_L3_2_BJ2_2p2", OrderedDict((("L3_pH", 2.0), ("BJ2_area", 2.2)))),)
MASKS = ("0011", "0111")
VALIDATION_MASKS = ("0001", "1111")
ALL_MASKS = MASKS + VALIDATION_MASKS


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


def token(value: float) -> str:
    return f"{value:g}".replace(".", "p").replace("-", "m")


def variant_name(point_id: str, changes: OrderedDict[str, float]) -> str:
    return point_id + "_" + "_".join(f"{key}{token(value)}" for key, value in changes.items()) + ".cir"


def make_variant(changes: OrderedDict[str, float]) -> str:
    text = (EXP / "inputs/BQ_parameterized_bjs400_rj2.cir").read_text(encoding="utf-8")
    replacements = {
        "BJ2_area": ("BJ2 4 0 jjmit area=2", f"BJ2 4 0 jjmit area={changes['BJ2_area']:g}"),
        "L3_pH": ("L3 4 OUT 1.3p", f"L3 4 OUT {changes['L3_pH']:g}p"),
    }
    for parameter, (old, new) in replacements.items():
        if parameter in changes:
            if text.count(old) != 1:
                raise RuntimeError(f"{parameter} source token is not unique")
            text = text.replace(old, new, 1)
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


def build_deck(point_id: str, mask: str, variant: str) -> str:
    base = (EXP / "references/canonical_l3p13/0011/deck.cir").read_text(encoding="utf-8")
    if base.count(".include ../../inputs/BQ_parameterized_bjs400_rj2.cir") != 1:
        raise RuntimeError("baseline BQ include is not unique")
    base = base.replace(".include ../../inputs/BQ_parameterized_bjs400_rj2.cir", f".include ../../inputs/bq_variants/{variant}", 1)
    for instance in range(1, 5):
        for kind in ("WL", "BL", "SE"):
            prefix = f"I_{kind}{instance} "
            lines = [line for line in base.splitlines() if line.startswith(prefix)]
            if len(lines) != 1:
                raise RuntimeError(f"control line is not unique: {prefix}")
            base = base.replace(lines[0], f"I_{kind}{instance} 0 {kind}{instance} {control_values(kind, mask[instance - 1] == '1')}", 1)
    return base.replace(base.splitlines()[0], f"* GENERATED FULL CLOSED-LOOP BJ2/L3 TARGET DECK: {point_id}; mask={mask}", 1)


def active_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip() and not line.lstrip().startswith(("*", ".", "+"))]


def signature(path: Path) -> tuple[str, ...]:
    lines = []
    for line in path.read_text(encoding="utf-8").splitlines():
        value = line.strip()
        if not value or value.startswith(("*", ".param", "I_WL", "I_BL", "I_SE")) or "bq_variants/" in value or "BQ_parameterized_bjs400_rj2.cir" in value:
            continue
        lines.append(value)
    return tuple(lines)


def deck_check(path: Path, point_id: str, mask: str, variant: str) -> dict[str, Any]:
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
    if signature(path) != signature(EXP / "references/canonical_l3p13/0011/deck.cir"):
        failures.append("topology/protocol structural signature differs")
    variant_text = (EXP / "inputs/bq_variants" / variant).read_text(encoding="utf-8")
    if "BJ2 4 0 jjmit area=2.2" not in variant_text or "L3 4 OUT 2p" not in variant_text:
        failures.append("candidate variant does not bind BJ2=2.2 and L3=2.0")
    return {"status": "PASS" if not failures else "FAIL", "path": path.relative_to(REPO).as_posix(), "sha256": sha256(path), "bytes": path.stat().st_size, "point_id": point_id, "mask": mask, "variant": variant, "failures": failures}


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
    failures: list[str] = []
    points: list[dict[str, Any]] = []
    for point_id_value, changes in POINTS:
        variant = variant_name(point_id_value, changes)
        variant_path = EXP / "inputs/bq_variants" / variant
        write_once(variant_path, make_variant(changes))
        item: dict[str, Any] = {"point_id": point_id_value, "changes": changes, "variant_path": variant_path.relative_to(REPO).as_posix(), "variant_sha256": sha256(variant_path), "cases": {}}
        for mask in ALL_MASKS:
            deck = EXP / "screening/decks" / point_id_value / f"{mask}.cir"
            write_once(deck, build_deck(point_id_value, mask, variant))
            item["cases"][mask] = deck_check(deck, point_id_value, mask, variant)
            failures.extend(f"{point_id_value}/{mask}: {message}" for message in item["cases"][mask]["failures"])
        points.append(item)
    inputs = []
    for name, role in (("array_fixture_template.cir", "full closed-loop template"), ("bvm_jm2_connected.cir", "BVM include"), ("jjmit.cir", "JJ model"), ("jtl2.cir", "six-stage JTL"), ("BQ_parameterized_bjs400.cir", "BQ baseline"), ("BQ_parameterized_bjs400_rj2.cir", "BQ parameterized source")):
        local, origin = EXP / "inputs" / name, PREVIOUS / "inputs" / name
        inputs.append(artifact(local, role, origin))
        if sha256(local) != sha256(origin):
            failures.append(f"input mismatch: {name}")
    reference_origins = {
        "canonical_l3p13/0011": PREVIOUS / "references/canonical_l3p13/0011",
        "canonical_l3p13/0111": PREVIOUS / "references/canonical_l3p13/0111",
        "l3p20/0011": PREVIOUS / "runs/L3_H2_L3_2_0011",
        "l3p20/0111": PREVIOUS / "runs/L3_H2_L3_2_0111",
        "bj2p22_l3p13/0011": PREVIOUS_OFAT / "runs/SCREEN_BJ2_area_2p2_0011",
        "bj2p22_l3p13/0111": PREVIOUS_OFAT / "runs/SCREEN_BJ2_area_2p2_0111",
    }
    references = {}
    for key, origin in reference_origins.items():
        local = EXP / "references" / key
        references[key] = {name: artifact(local / name, "immutable targeted-combination reference", origin / name) for name in ("raw.csv", "deck.cir", "metadata.json", "run.log")}
        for name in ("raw.csv", "deck.cir", "metadata.json", "run.log"):
            if sha256(local / name) != sha256(origin / name):
                failures.append(f"reference mismatch: {key}/{name}")
    previous_package = PREVIOUS / "handoff/bvm-qb-l3-highside-selective-window-v1-20260911_raw_handoff.zip"
    ofat_package = PREVIOUS_OFAT / "handoff/bvm-full-closed-loop-qb-parameter-screening-v1-20260911_raw_handoff_v2.zip"
    source_manifest = {"schema": "bvm-qb-l3-bj2-targeted-combination-source-manifest-v1", "experiment_id": EXP.name, "created_at_local": now(), "repository_head_at_registration": head(), "remote_master_at_registration": remote_head(), "inputs": inputs, "references": references, "variants": [artifact(REPO / point["variant_path"], "targeted BJ2/L3 BQ variant") for point in points], "previous_l3_package": artifact(previous_package, "previous L3 high-side evidence package"), "previous_ofat_package": artifact(ofat_package, "previous BJ2-area OFAT evidence package"), "baseline": BASELINE, "target_changes": {"L3_pH": 2.0, "BJ2_area": 2.2}, "solver": {"path": SOLVER.relative_to(REPO).as_posix(), "sha256": sha256(SOLVER), "version": subprocess.check_output([str(SOLVER), "--version"], cwd=REPO, text=True)}, "logical_new_point_count": 1, "logical_new_case_count": 2, "maximum_new_screening_solve_count": 2, "maximum_total_new_physical_solve_count_if_clean_2_to_3": 4, "conditional_validation_masks": list(VALIDATION_MASKS), "no_replay": True, "no_passive_capture": True, "no_source_scaling": True, "no_jtl_change": True, "no_timestep_change": True}
    source_path = EXP / "SOURCE_MANIFEST.json"
    write_once(source_path, json.dumps(source_manifest, ensure_ascii=False, indent=2) + "\n", args.refresh_head)
    matrix = {"schema": "bvm-qb-l3-bj2-targeted-combination-matrix-v1", "experiment_id": EXP.name, "created_at_local": now(), "baseline": BASELINE, "target_changes": {"L3_pH": 2.0, "BJ2_area": 2.2}, "points": points, "masks": list(MASKS), "logical_new_point_count": 1, "logical_new_case_count": 2, "maximum_new_screening_solve_count": 2, "conditional_validation_masks": list(VALIDATION_MASKS), "validation_condition": "only if the screening pair is a clean ordered 2/3 candidate", "failures": failures}
    matrix_path = EXP / "screening/TARGET_MATRIX.json"
    write_once(matrix_path, json.dumps(matrix, ensure_ascii=False, indent=2) + "\n", args.refresh_head)
    table = "\n".join(["# BJ2/L3 targeted full closed-loop combination matrix", "", "| point | L3 | BJ2 area | masks | use |", "|---|---:|---:|---|---|", "| TARGET_L3_2_BJ2_2p2 | 2.0 pH | 2.2 | 0011, 0111 | registered screening pair |", "", "References: canonical L3=1.3/BJ2=2.0, L3=2.0/BJ2=2.0, and L3=1.3/BJ2=2.2 are immutable context only.", "", "Maximum new screening solves: 2. Conditional validation masks 0001 and 1111 are authorized only after a clean 2/3 screening result.", ""])
    write_once(EXP / "screening/TARGET_TABLE.md", table, args.refresh_head)
    previous = json.loads((EXP / "analysis/preflight.json").read_text(encoding="utf-8")) if (EXP / "analysis/preflight.json").is_file() else {}
    record = {"schema": "bvm-qb-l3-bj2-targeted-combination-preflight-v1", "experiment_id": EXP.name, "created_at_local": now(), "status": "PASS" if not failures else "FAIL", "registration_head": previous.get("registration_head", head()), "head_at_preflight": head(), "remote_master_at_preflight": remote_head(), "logical_new_point_count": 1, "logical_new_case_count": 2, "maximum_new_screening_solve_count": 2, "authorized_points": [point_id_value for point_id_value, _changes in POINTS], "authorized_screening_masks": list(MASKS), "conditional_validation_masks": list(VALIDATION_MASKS), "validation_condition": "clean ordered 2/3 screening result only", "phase_baseline_window_ps": [101.0, 110.0], "phase_navigation_thresholds_turns": [0.5, 1.5, 2.5, 3.5, 4.5], "corrected_control_windows_ps": [[70.0, 81.0], [81.0, 90.0], [90.0, 101.0], [101.0, 110.0]], "rollback_excluded_from_control": True, "physical_solve_count_before_preflight": 0, "scientific_analysis_performed": False, "n1_n4_validation_authorized": "CONDITIONAL_ONLY_IF_CLEAN_2_TO_3", "matrix_sha256": sha256(matrix_path), "source_manifest_sha256": sha256(source_path), "failures": failures}
    preflight_path = EXP / "analysis/preflight.json"
    write_once(preflight_path, json.dumps(record, ensure_ascii=False, indent=2) + "\n", args.refresh_head)
    preflight_md = "\n".join([
        "# BVM QB BJ2/L3 targeted combination - PREFLIGHT", "", CONTRACT_SENTENCE, "",
        f"- Experiment: {EXP.name}", f"- Registration HEAD: {record['registration_head']}", f"- Sealed preflight HEAD: {record['head_at_preflight']}", f"- Remote bvm/master: {record.get('remote_master_at_preflight')}", "- Status: PASS", "- Solver has not been invoked at preflight.", "",
        "## Exact scope", "", "The only new screening point is L3=2.0 pH plus BJ2 area=2.2, with masks 0011 and 0111. Frozen parameters are Lin=1.5 pH, L1=1.4 pH, L2=2.0 pH, RJ1=32 ohm, RJ2=12 ohm, IBias=260 uA, BJS area=4.0 and BJ1 area=0.9. Three reference pairs are immutable context and are not rerun.", "",
        "## Source and topology", "", "The resolved closure is inputs/jjmit.cir + inputs/bvm_jm2_connected.cir + the target BQ variant + inputs/jtl2.cir; topology is BVM1..4 -> COMMON_SL -> eight-JJ JSL -> QB -> six-stage JTL -> R_TERM. The BQ variant changes only BJ2 area 2.0 -> 2.2 and L3 1.3 pH -> 2.0 pH.", "",
        "## Exact probes and metrics", "", "Raw preserves the full BVM boundary, COMMON_SL, P/V/I for B_JSL1..8, QBIN, LIN/L1/L2/L3, BJS/BJ1/BJ2, RJ1/RJ2, all P/V/I B01/B02 JTL probes, every JTL output and I(R_TERM). Metrics are raw SHA-256, 1999-point actual grid 0..199.9 ps, phase navigation from the 101-110 ps baseline at +0.5/+1.5/+2.5/+3.5/+4.5 turns, corrected 70-110 ps control windows, actual-grid integrals of V(BJ1)-V(BJ2) over 118-121/121-124/124-128 ps, and I(B_JSL8) signed areas over 110-112/110-121/121-124/121-126 ps.", "",
        "## Conditional validation", "", "If and only if the screening pair is a clean ordered 2/3 candidate, run exactly the reserved masks 0001 and 1111 at the same physical point. Otherwise stop after the two screening solves. Absolute maximum is four new physical solves.", "",
        "## Corrected history/control", "", "Use actual stored samples in 70-81 ps ZERO_STATE_READ_CONTROL, 81-90 ps idle, 90-101 ps WRITE1 and 101-110 ps SETTLE. Only unintended complete QBOUT->JTL1..6 propagation before FINAL READ is contamination. FINAL/Tail rollback is separate.", "",
        "## Interpretation ceiling", "", "P values are raw radians; rad/(2*pi) is navigation only, not an SFQ count. The result is bounded to this source, receiver, load, history, solver and 0.1 ps grid. No additional parameter/scan, replay, source modification, timestep refinement or positional validation is authorized.", "",
        "## Known UNKNOWNs", "", "No timestep convergence, parameter sensitivity, hardware equivalence, exact continuous optimum or universal mechanism is established by this Quick experiment.", "",
        "## Stop", "", "After the screening pair, or after the conditional validation pair if a clean 2/3 candidate is found, stop at EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW.", "",
    ])
    write_once(EXP / "PREFLIGHT.md", preflight_md, args.refresh_head)
    print(json.dumps({"status": record["status"], "logical_new_points": 1, "logical_cases": 2, "maximum_new_physical_solves": 2, "failures": failures}, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
