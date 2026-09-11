#!/usr/bin/env python3
"""Register the bounded L3 high-side selective-window experiment."""

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
PREVIOUS = REPO / "test/exploration/bvm-full-closed-loop-qb-parameter-screening-v1-20260911"
SOLVER = REPO / "build/josim-cli"
SOLVER_SHA256 = "48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2"
CONTRACT_SENTENCE = "This experiment is governed by docs/EXPERIMENT_CONTRACT.md."
BASELINE = OrderedDict((("Lin_pH", 1.5), ("L1_pH", 1.4), ("L2_pH", 2.0), ("RJ1_ohm", 32.0), ("RJ2_ohm", 12.0), ("IBias_uA", 260.0), ("BJS_area", 4.0), ("BJ1_area", 0.9), ("BJ2_area", 2.0), ("L3_pH", 1.3)))
POINTS = (("H1_L3_1p8", OrderedDict((("L3_pH", 1.8),))), ("H2_L3_2", OrderedDict((("L3_pH", 2.0),))))
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


def token(value: float) -> str:
    return f"{value:g}".replace(".", "p").replace("-", "m")


def variant_name(point_id: str, changes: OrderedDict[str, float]) -> str:
    return point_id + "_" + "_".join(f"{key}{token(value)}" for key, value in changes.items()) + ".cir"


def make_variant(changes: OrderedDict[str, float]) -> str:
    text = (EXP / "inputs/BQ_parameterized_bjs400_rj2.cir").read_text(encoding="utf-8")
    old = "L3 4 OUT 1.3p"
    if "L3_pH" in changes:
        if text.count(old) != 1:
            raise RuntimeError("L3 source token is not unique")
        text = text.replace(old, f"L3 4 OUT {changes['L3_pH']:g}p", 1)
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
    return base.replace(base.splitlines()[0], f"* GENERATED FULL CLOSED-LOOP L3 HIGHSIDE DECK: {point_id}; mask={mask}", 1)


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
        for mask in MASKS:
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
        "l3_1p6/0011": PREVIOUS / "runs/SCREEN_L3_pH_1p6_0011",
        "l3_1p6/0111": PREVIOUS / "runs/SCREEN_L3_pH_1p6_0111",
        "canonical_l3p13/0011": PREVIOUS / "references/baseline_rj2p12/ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_0011",
        "canonical_l3p13/0111": PREVIOUS / "references/baseline_rj2p12/ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_0111",
    }
    references = {}
    for key, origin in reference_origins.items():
        local = EXP / "references" / key
        references[key] = {name: artifact(local / name, "immutable L3 reference", origin / name) for name in ("raw.csv", "deck.cir", "metadata.json", "run.log")}
        for name in ("raw.csv", "deck.cir", "metadata.json", "run.log"):
            if sha256(local / name) != sha256(origin / name):
                failures.append(f"reference mismatch: {key}/{name}")
    previous_package = PREVIOUS / "handoff/bvm-full-closed-loop-qb-parameter-screening-v1-20260911_raw_handoff_v2.zip"
    source_manifest = {"schema": "bvm-qb-l3-highside-selective-window-source-manifest-v1", "experiment_id": EXP.name, "created_at_local": now(), "repository_head_at_registration": head(), "remote_master_at_registration": remote_head(), "inputs": inputs, "references": references, "variants": [artifact(REPO / point["variant_path"], "L3 highside BQ variant") for point in points], "previous_screening_package": artifact(previous_package, "previous OFAT evidence package"), "baseline": BASELINE, "fixed_reference_L3_pH": 1.6, "solver": {"path": SOLVER.relative_to(REPO).as_posix(), "sha256": sha256(SOLVER), "version": subprocess.check_output([str(SOLVER), "--version"], cwd=REPO, text=True)}, "logical_new_point_count": 2, "logical_new_case_count": 4, "maximum_new_screening_solve_count": 4, "maximum_total_new_solve_count_if_later_validation_authorized": 6, "no_replay": True, "no_passive_capture": True, "no_source_scaling": True, "no_jtl_change": True, "no_timestep_change": True}
    source_path = EXP / "SOURCE_MANIFEST.json"
    write_once(source_path, json.dumps(source_manifest, ensure_ascii=False, indent=2) + "\n", args.refresh_head)
    matrix = {"schema": "bvm-qb-l3-highside-selective-window-matrix-v1", "experiment_id": EXP.name, "created_at_local": now(), "baseline": BASELINE, "reference_L3_pH": 1.6, "points": points, "masks": list(MASKS), "logical_new_point_count": 2, "logical_new_case_count": 4, "maximum_new_screening_solve_count": 4, "validation_reserved_but_not_authorized": ["0001", "1111"], "failures": failures}
    matrix_path = EXP / "screening/L3_MATRIX.json"
    write_once(matrix_path, json.dumps(matrix, ensure_ascii=False, indent=2) + "\n", args.refresh_head)
    table = "\n".join(["# L3 highside selective-window matrix", "", "| L3 | status | masks | expected use |", "|---:|---|---|---|", "| 1.6 pH | immutable reference | 0011, 0111 | known N2=2, N3=4 |", "| 1.8 pH | registered new point | 0011, 0111 | H1 |", "| 2.0 pH | registered new point | 0011, 0111 | H2, only if H1 is not clean 2/3 |", "", "Maximum new screening solves: 4. N1/N4 validation is reserved but not authorized in this experiment.", ""])
    write_once(EXP / "screening/L3_TABLE.md", table, args.refresh_head)
    previous = json.loads((EXP / "analysis/preflight.json").read_text(encoding="utf-8")) if (EXP / "analysis/preflight.json").is_file() else {}
    record = {"schema": "bvm-qb-l3-highside-selective-window-preflight-v1", "experiment_id": EXP.name, "created_at_local": now(), "status": "PASS" if not failures else "FAIL", "registration_head": previous.get("registration_head", head()), "head_at_preflight": head(), "remote_master_at_preflight": remote_head(), "logical_new_point_count": 2, "logical_new_case_count": 4, "maximum_new_screening_solve_count": 4, "authorized_points": [point_id_value for point_id_value, _changes in POINTS], "authorized_masks": list(MASKS), "reference_L3_pH": 1.6, "phase_baseline_window_ps": [101.0, 110.0], "phase_navigation_thresholds_turns": [0.5, 1.5, 2.5, 3.5, 4.5], "corrected_control_windows_ps": [[70.0, 81.0], [81.0, 90.0], [90.0, 101.0], [101.0, 110.0]], "rollback_excluded_from_control": True, "physical_solve_count_before_preflight": 0, "scientific_analysis_performed": False, "n1_n4_validation_authorized": False, "matrix_sha256": sha256(matrix_path), "source_manifest_sha256": sha256(source_path), "failures": failures}
    preflight_path = EXP / "analysis/preflight.json"
    write_once(preflight_path, json.dumps(record, ensure_ascii=False, indent=2) + "\n", args.refresh_head)
    preflight_md = "\n".join(["# BVM QB L3 highside selective-window search - PREFLIGHT", "", CONTRACT_SENTENCE, "", f"- Experiment: {EXP.name}", f"- Registration HEAD: {record['registration_head']}", f"- Sealed preflight HEAD: {record['head_at_preflight']}", f"- Remote bvm/master: {record.get('remote_master_at_preflight')}", "- Status: PASS", "- Solver has not been invoked at preflight.", "", "## Exact scope", "", "Only H1 L3=1.8 pH and H2 L3=2.0 pH are new registered points, each with 0011 and 0111. L3=1.6 pH is an immutable reference. H2 runs only when H1 is not a clean 2/3 point.", "", "## Corrected history/control", "", "Use actual stored samples in 70-81 ps ZERO_STATE_READ_CONTROL, 81-90 ps idle, 90-101 ps WRITE1 and 101-110 ps SETTLE. Only unintended complete QBOUT->JTL1..6 propagation before FINAL READ is contamination. FINAL/Tail rollback is separate.", "", "## Interpretation ceiling", "", "P values are raw radians; rad/(2*pi) is navigation only, not an SFQ count. The result is bounded to this source, receiver, load, history, solver and 0.1 ps grid. No extra L3, third parameter, replay, source modification, timestep refinement or N1/N4 validation is authorized.", "", "## Stop", "", "After H1 alone if clean 2/3, otherwise after H1 and H2, stop at EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW. Population validation requires later scientific authorization.", ""])
    write_once(EXP / "PREFLIGHT.md", preflight_md, args.refresh_head)
    print(json.dumps({"status": record["status"], "logical_new_points": 2, "logical_cases": 4, "maximum_new_physical_solves": 4, "failures": failures}, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
