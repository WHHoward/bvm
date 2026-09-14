#!/usr/bin/env python3
"""Run two same-configuration JTL6 mask reruns without overwriting raw data."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import zipfile
from pathlib import Path

os.environ.setdefault("BVM_QB_T1_EXPERIMENT_ID", "bvm-qb-t1-interface-topology-v1-20260914-bias-1p8-rj4-4-masks-0111-1111-rerun")
from bvm_qb_t1_interface import (  # noqa: E402
    BVM,
    EXP,
    JTL,
    MODEL,
    PLOTTER,
    QB,
    REPO,
    SOLVER,
    T1,
    required_headers,
    run_data,
    run_dir,
    run_id,
    run_metrics,
    run_one,
    select_columns,
    sha256,
    solver_context,
    now,
    read_json,
    rel,
    write_json,
)


TOPOLOGY = "jtl6"
MASKS = ("0111", "1111")
TEMPLATE_DEFAULT = REPO / "test/exploration/bvm-qb-t1-interface-topology-v1-20260914-bias-1p8-rj4-4-rerun/runs/jtl6/0011/deck.cir"
TEMPLATE = Path(os.environ.get("BVM_QB_T1_TEMPLATE_DECK", str(TEMPLATE_DEFAULT))).resolve()
TEMPLATE_SHA256 = "0d441ec28c3da9c5d55384659b747af17e66a0df6b97725e3b9c966893025c81"
OLD_EXP = REPO / "test/exploration/bvm-qb-t1-interface-topology-v1-20260914-bias-1p8-rj4-4-rerun"
OLD_RAW = OLD_EXP / "runs/jtl6/0011/raw.csv"
PACKAGE = REPO / f"{EXP.name}_raw_evidence.zip"


def replace_mask_lines(template: str, mask: str) -> str:
    if mask not in MASKS:
        raise RuntimeError(f"unsupported mask: {mask}")
    result = template.replace("topology=jtl6; mask=0011", f"topology=jtl6; mask={mask}")
    for index, bit in enumerate(mask, start=1):
        value = "+100u" if bit == "1" else "0"
        for source in ("WL", "SE"):
            pattern = rf"(^I_{source}{index} 0 {source}{index} .*?110p 0 )111p (?:\+100u|0) 120p (?:\+100u|0) 121p 0 200p 0\)$"
            replacement = rf"\g<1>111p {value} 120p {value} 121p 0 200p 0)"
            result, count = re.subn(pattern, replacement, result, flags=re.MULTILINE)
            if count != 1:
                raise RuntimeError(f"expected one final-read line for I_{source}{index}, found {count}")
    template_lines = template.splitlines()
    result_lines = result.splitlines()
    changed = []
    for before, after in zip(template_lines, result_lines):
        if before != after:
            changed.append((before, after))
    if not any(line.startswith("* REGISTERED") for line, _ in changed):
        raise RuntimeError("mask header was not changed")
    template_mask = "0011"
    expected_changes = 1 + 2 * sum(left != right for left, right in zip(template_mask, mask))
    if len(changed) != expected_changes:
        raise RuntimeError(f"mask transform changed {len(changed)} lines; expected {expected_changes}")
    for before, after in changed[1:]:
        if not (before.startswith("I_WL") or before.startswith("I_SE")):
            raise RuntimeError(f"unexpected non-mask deck change: {before}")
    return result


def source_entries() -> list[dict[str, object]]:
    values = [
        ("canonical_qb", QB, "frozen canonical QB"),
        ("global_jjmit_model", MODEL, "global BVM/JSL/T1 model closure"),
        ("t1_cell", T1, "current T1 netlist"),
        ("bvm_jm2_connected", BVM, "frozen BVM source"),
        ("jtl2_source", JTL, "frozen JTL source"),
        ("template_deck", TEMPLATE, "previous bias deck; only final-read mask lines are transformed"),
        ("josim_solver", SOLVER, "recorded solver"),
        ("plotter", PLOTTER, "standard renderer"),
    ]
    return [{"name": name, "path": rel(path), "sha256": sha256(path), "bytes": path.stat().st_size, "role": role} for name, path, role in values]


def prepare() -> None:
    if not TEMPLATE.is_file() or sha256(TEMPLATE) != TEMPLATE_SHA256:
        raise RuntimeError("previous bias template deck is missing or changed")
    if not OLD_RAW.is_file():
        raise RuntimeError("previous same-configuration 0011 raw is missing")
    template = TEMPLATE.read_text(encoding="utf-8")
    EXP.mkdir(parents=True, exist_ok=True)
    registered_decks: dict[str, dict[str, object]] = {}
    for mask in MASKS:
        directory = run_dir(TOPOLOGY, mask)
        directory.mkdir(parents=True, exist_ok=True)
        deck = directory / "deck.cir"
        text = replace_mask_lines(template, mask)
        if deck.exists() and deck.read_text(encoding="utf-8") != text:
            raise RuntimeError(f"refusing to overwrite changed deck: {deck}")
        if not deck.exists():
            deck.write_text(text, encoding="utf-8")
        registered_decks[run_id(TOPOLOGY, mask)] = {"path": rel(deck), "sha256": sha256(deck), "bytes": deck.stat().st_size}
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()
    remote = subprocess.check_output(["git", "ls-remote", "bvm", "refs/heads/master"], cwd=REPO, text=True).split()[0]
    entries = source_entries()
    provenance = {
        "schema": "bvm-qb-t1-mask-pair-rerun-provenance-v1",
        "experiment_id": EXP.name,
        "created_at": now(),
        "registration_head": head,
        "remote_bvm_master": remote,
        "solver": solver_context(),
        "sources": entries,
        "configuration": {"topology": TOPOLOGY, "masks": list(MASKS), "template_deck": {"path": rel(TEMPLATE), "sha256": TEMPLATE_SHA256}, "only_deck_transform": "final-read WL/SE values for selected mask", "t1_sha256": sha256(T1), "t1_R_J4_ohm": 4},
        "registered_decks": registered_decks,
        "comparison_reference": {"experiment": OLD_EXP.name, "raw_path": rel(OLD_RAW), "raw_sha256": sha256(OLD_RAW), "not_copied": True},
        "raw_hash_before_analysis": {},
        "raw_hash_after_analysis": {},
        "transformations": [{"name": "mask_line_transform", "raw_mutated": False, "only_changes": "I_WL1..4 and I_SE1..4 final-read values plus deck header mask"}, {"name": "phase_unwrap_for_navigation", "raw_mutated": False}, {"name": "phase_turn_display", "formula": "raw_phase_rad/(2*pi)", "raw_mutated": False}, {"name": "actual_grid_trapezoid", "interpolation": False, "raw_mutated": False}],
        "runs": {},
        "scientific_analysis_performed": False,
    }
    write_json(EXP / "provenance.json", provenance)
    write_json(EXP / "SOURCE_MANIFEST.json", {"schema": "bvm-qb-t1-mask-pair-source-manifest-v1", "experiment_id": EXP.name, "sources": entries, "comparison_reference": {"path": rel(OLD_RAW), "sha256": sha256(OLD_RAW), "not_copied": True}})
    write_json(EXP / "run_state.json", {"schema": "bvm-qb-t1-mask-pair-state-v1", "experiment_id": EXP.name, "created_at": now(), "updated_at": now(), "status": "PREFLIGHT_PASS", "run_order": [], "authorized_physical_solve_count": 2, "actual_physical_solve_count": 0, "final_marker": None})
    print(json.dumps({"status": "PREFLIGHT_PASS", "masks": MASKS, "template_sha256": TEMPLATE_SHA256, "t1_sha256": sha256(T1)}, ensure_ascii=False, indent=2))


def execute() -> None:
    state = read_json(EXP / "run_state.json")
    provenance = read_json(EXP / "provenance.json")
    if state.get("actual_physical_solve_count") or state.get("final_marker"):
        raise RuntimeError("execution already started; refusing overwrite")
    for mask in MASKS:
        name = run_id(TOPOLOGY, mask)
        deck = run_dir(TOPOLOGY, mask) / "deck.cir"
        if sha256(deck) != provenance["registered_decks"][name]["sha256"]:
            raise RuntimeError(f"deck changed after preflight: {name}")
    if sha256(T1) != provenance["configuration"]["t1_sha256"]:
        raise RuntimeError("T1 changed after preflight")
    for mask in MASKS:
        run_one(TOPOLOGY, mask, state, provenance)
    state["status"] = "RUN_COMPLETE"
    state["updated_at"] = now()
    write_json(EXP / "run_state.json", state)
    analyze()


def analyze() -> None:
    state = read_json(EXP / "run_state.json")
    provenance = read_json(EXP / "provenance.json")
    before = {run_id(TOPOLOGY, mask): sha256(run_dir(TOPOLOGY, mask) / "raw.csv") for mask in MASKS}
    provenance["raw_hash_before_analysis"] = before
    write_json(EXP / "provenance.json", provenance)
    metrics = {run_id(TOPOLOGY, mask): run_metrics(TOPOLOGY, mask) for mask in MASKS}
    after = {run_id(TOPOLOGY, mask): sha256(run_dir(TOPOLOGY, mask) / "raw.csv") for mask in MASKS}
    if before != after:
        raise RuntimeError("raw changed during analysis")
    result = {"schema": "bvm-qb-t1-mask-pair-result-v1", "experiment_id": EXP.name, "generated_at": now(), "artifact_status": "VALID", "execution": {"authorized_physical_solve_count": 2, "actual_physical_solve_count": 2, "completed_runs": [run_id(TOPOLOGY, mask) for mask in MASKS]}, "observed": {"topology": TOPOLOGY, "masks": list(MASKS), "deck_unchanged_except_final_read_mask": True, "phase_raw_unit": "radians", "raw_time_unit": "seconds"}, "derived": {"registered_window_arithmetic": metrics}, "comparison_reference": {"experiment": OLD_EXP.name, "raw_path": rel(OLD_RAW), "raw_sha256": sha256(OLD_RAW), "not_copied": True}, "unknown": ["SFQ count/event identity", "JJ switching certification", "interface Gate", "T1 truth table", "mechanism", "convergence", "route selection"], "interpretation": {"scientific_analysis_performed": False, "physical_verdict": "NOT_ASSIGNED", "review_state": "AWAITING_SCIENTIFIC_REVIEW", "phase_turns_are_navigation_only": True}, "stop": {"final_marker": "EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW", "automatic_follow_up": False}}
    write_json(EXP / "result.json", result)
    provenance = read_json(EXP / "provenance.json")
    provenance["raw_hash_after_analysis"] = after
    provenance["analysis"] = {"generated_at": now(), "raw_hashes_equal_before_after": True, "scientific_analysis_performed": False}
    write_json(EXP / "provenance.json", provenance)
    state["status"] = "ANALYSIS_COMPLETE"
    state["final_marker"] = "EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW"
    state["updated_at"] = now()
    write_json(EXP / "run_state.json", state)
    (EXP / "RESULT.md").write_text("\n".join(["# BVM -> QB -> T1 same-configuration mask pair rerun", "", "- Artifact status: `VALID`.", "- Authorized/completed physical solves: `2/2` (`jtl6/0111`, `jtl6/1111`).", "- Deck configuration is unchanged except the registered final-read mask lines.", "- Scientific interpretation: `NOT_PERFORMED`; physical verdict: `NOT_ASSIGNED`.", "", "The prior same-configuration `0011` raw is preserved and referenced only by path/hash. P(...) remains raw radians; displayed turns are navigation only, not SFQ counts.", "", "EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW", ""]), encoding="utf-8")


def qa() -> None:
    state = read_json(EXP / "run_state.json")
    provenance = read_json(EXP / "provenance.json")
    checks = {}
    failures = []
    for mask in MASKS:
        name = run_id(TOPOLOGY, mask)
        directory = run_dir(TOPOLOGY, mask)
        raw = directory / "raw.csv"
        deck = directory / "deck.cir"
        log = directory / "run.log"
        unexpected = sorted(path.name for path in directory.iterdir() if path.name not in {"deck.cir", "raw.csv", "run.log", "plots"})
        warnings = [line for line in log.read_text(errors="replace").splitlines() if "Missing model:" in line or "Using default model" in line] if log.is_file() else ["missing_log"]
        try:
            header, _, times = run_data(TOPOLOGY, mask)
            missing = sorted(required_headers(TOPOLOGY) - set(header))
        except Exception as exc:
            header, times, missing = [], [], [f"read_error:{exc}"]
        hash_match = raw.is_file() and sha256(raw) == provenance.get("runs", {}).get(name, {}).get("raw", {}).get("sha256")
        invalid = bool(unexpected or warnings or missing or not all(path.is_file() for path in (deck, raw, log)) or not hash_match)
        if invalid:
            failures.append(name)
        checks[name] = {"status": "ARTIFACT_INVALID" if invalid else "PASS", "unexpected_entries": unexpected, "solver_model_warnings": warnings, "missing_required_probes": missing, "raw_hash_match": hash_match, "sample_count": len(times), "first_time_ps": times[0] * 1e12 if times else None, "last_time_ps": times[-1] * 1e12 if times else None, "deck_sha256": sha256(deck) if deck.is_file() else None}
    result = {"schema": "bvm-qb-t1-mask-pair-mechanical-qa-v1", "experiment_id": EXP.name, "generated_at": now(), "status": "PASS" if not failures else "FAIL", "artifact_status": "VALID" if not failures else "ARTIFACT_INVALID", "completed_run_count": len(MASKS) - len(failures), "authorized_run_count": 2, "runs": checks, "raw_hash_before_after_equal": provenance.get("analysis", {}).get("raw_hashes_equal_before_after", False), "scientific_interpretation_performed": False}
    write_json(EXP / "mechanical_qa.json", result)
    if result["status"] != "PASS":
        raise RuntimeError("mask pair mechanical QA failed")
    print(json.dumps(result, ensure_ascii=False, indent=2))


def viz() -> None:
    if read_json(EXP / "mechanical_qa.json").get("status") != "PASS":
        raise RuntimeError("run QA before visualization")
    entries = []
    for mask in MASKS:
        header, _, _ = run_data(TOPOLOGY, mask)
        directory = run_dir(TOPOLOGY, mask)
        outdir = directory / "plots"
        outdir.mkdir(exist_ok=True)
        for view in ("01_bvm_phase", "02_bvm_currents", "03_source_jsl", "04_qb", "05_jtl", "06_t1_jj", "07_t1_io"):
            subset = select_columns(header, view, TOPOLOGY)
            output = outdir / f"{view}.html"
            if output.exists():
                raise RuntimeError(f"refusing overwrite: {output}")
            command = [sys.executable, str(PLOTTER), str(directory / "raw.csv"), "-x", str(output), "-t", "sep_comb", "-c", "dark", "-j", "2pi", "-w", f"{EXP.name} | jtl6 | mask={mask} | {view} | raw 0-200 ps", "-s", *subset]
            completed = subprocess.run(command, cwd=REPO, capture_output=True, text=True, check=False)
            if completed.returncode or not output.is_file() or not output.stat().st_size:
                raise RuntimeError(f"visualization failed: {output}: {completed.stderr[-500:]}")
            entries.append({"path": rel(output), "run_id": run_id(TOPOLOGY, mask), "mask": mask, "view": view, "raw_path": rel(directory / "raw.csv"), "raw_sha256": sha256(directory / "raw.csv"), "renderer": {"path": rel(PLOTTER), "sha256": sha256(PLOTTER)}, "window_ps": [0, 200], "phase_display": "2pi turns display from raw radians; not SFQ count"})
    manifest = {"schema": "bvm-qb-t1-mask-pair-visualization-manifest-v1", "experiment_id": EXP.name, "generated_at": now(), "renderer": {"path": rel(PLOTTER), "sha256": sha256(PLOTTER), "layout": "sep_comb", "color": "dark", "phase_option": "2pi"}, "whole_run_window_ps": [0, 200], "focused_windows": [], "comparison_entries": [], "entries": entries, "entry_count": len(entries), "scientific_interpretation_performed": False, "status": "PASS"}
    write_json(EXP / "visualization_manifest.json", manifest)
    write_json(EXP / "visualization_qa.json", {"schema": "bvm-qb-t1-mask-pair-visualization-qa-v1", "experiment_id": EXP.name, "generated_at": now(), "status": "PASS", "entry_count": len(entries), "full_run_only": True, "focused_windows": [], "comparisons": 0, "image_files": [], "raw_hashes_rechecked": all(item["raw_sha256"] == sha256(REPO / item["raw_path"]) for item in entries), "scientific_interpretation_performed": False})
    print(json.dumps({"status": "PASS", "html_count": len(entries)}, ensure_ascii=False, indent=2))


def package() -> None:
    if read_json(EXP / "mechanical_qa.json").get("status") != "PASS" or read_json(EXP / "visualization_qa.json").get("status") != "PASS":
        raise RuntimeError("QA must pass before packaging")
    if PACKAGE.exists():
        raise RuntimeError(f"refusing overwrite: {PACKAGE}")
    root_names = ("PREFLIGHT.md", "experiment.yaml", "RESULT.md", "run.sh", "result.json", "provenance.json", "SOURCE_MANIFEST.json", "mechanical_qa.json", "visualization_manifest.json", "visualization_qa.json", "run_state.json")
    files = [EXP / name for name in root_names if (EXP / name).is_file()] + [path for path in sorted((EXP / "runs").rglob("*")) if path.is_file()]
    records = [{"path": path.relative_to(EXP).as_posix(), "sha256": sha256(path), "bytes": path.stat().st_size} for path in files]
    with zipfile.ZipFile(PACKAGE, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in files:
            archive.write(path, path.relative_to(EXP).as_posix())
    with zipfile.ZipFile(PACKAGE) as archive:
        reopened = {name: hashlib.sha256(archive.read(name)).hexdigest() for name in archive.namelist()}
    expected = {item["path"]: item["sha256"] for item in records}
    qa = {"schema": "bvm-qb-t1-mask-pair-package-qa-v1", "experiment_id": EXP.name, "generated_at": now(), "package_path": str(PACKAGE), "package_sha256": sha256(PACKAGE), "package_bytes": PACKAGE.stat().st_size, "git_head_at_packaging": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip(), "authorized_physical_solve_count": 2, "actual_physical_solve_count": 2, "file_count": len(records), "expected_file_hashes_match_after_reopen": expected == reopened, "contains_old_raw_copy": False, "files": records, "status": "PASS" if expected == reopened else "FAIL"}
    write_json(EXP / "PACKAGE_QA.json", qa)
    print(json.dumps({"status": qa["status"], "package": str(PACKAGE), "sha256": qa["package_sha256"], "bytes": qa["package_bytes"], "files": len(records)}, ensure_ascii=False, indent=2))


def main() -> int:
    command = sys.argv[1] if len(sys.argv) > 1 else ""
    if command == "prepare": prepare()
    elif command == "run": execute()
    elif command == "analyze": analyze()
    elif command == "qa": qa()
    elif command == "viz": viz()
    elif command == "package": package()
    else: raise SystemExit("usage: bvm_qb_t1_mask_pair_rerun.py {prepare|run|analyze|qa|viz|package}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
