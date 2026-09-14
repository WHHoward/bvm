#!/usr/bin/env python3
"""Execute and package one explicitly authorized T1 parameter rerun.

The experiment ID is supplied with BVM_QB_T1_EXPERIMENT_ID. This wrapper reuses
the canonical deck/probe/arithmetic helpers without reusing or overwriting an
existing raw file.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path

os.environ.setdefault("BVM_QB_T1_EXPERIMENT_ID", "bvm-qb-t1-interface-topology-v1-20260914-t1-rj4-2-rerun")
from bvm_qb_t1_interface import (  # noqa: E402
    BVM,
    EXP,
    JTL,
    LINK_DIFF_V,
    MASKS,
    MODEL,
    PACKAGE_QA,
    PLOTTER,
    QB,
    REPO,
    SOLVER,
    T1,
    V_ACTIVITY,
    actual_integral,
    assert_current_sources,
    deck_text,
    include_path,
    now,
    read_json,
    rel,
    required_headers,
    run_data,
    run_dir,
    run_id,
    run_metrics,
    run_one,
    select_columns,
    sha256,
    solver_context,
    unwrap,
    value_stats,
    window_indices,
    write_json,
)


TOPOLOGY = "jtl6"
MASK = "0011"
RUN = run_dir(TOPOLOGY, MASK)
OLD_EXP = REPO / "test/exploration/bvm-qb-t1-interface-topology-v1-20260914-v2"
OLD_RAW = OLD_EXP / "runs/jtl6/0011/raw.csv"
PACKAGE = REPO / f"{EXP.name}_raw_evidence.zip"
DECK_SOURCE_ENV = os.environ.get("BVM_QB_T1_DECK_SOURCE")
DECK_SOURCE = Path(DECK_SOURCE_ENV).resolve() if DECK_SOURCE_ENV else None


def prepare() -> None:
    EXP.mkdir(parents=True, exist_ok=True)
    assert_current_sources()
    if not OLD_RAW.is_file():
        raise RuntimeError(f"missing immutable comparison raw: {OLD_RAW}")
    old_deck = OLD_EXP / "runs/jtl6/0011/deck.cir"
    if not old_deck.is_file():
        raise RuntimeError(f"missing comparison deck: {old_deck}")
    RUN.mkdir(parents=True, exist_ok=True)
    deck = RUN / "deck.cir"
    if DECK_SOURCE is not None:
        if not DECK_SOURCE.is_file():
            raise RuntimeError(f"missing registered deck source: {DECK_SOURCE}")
        registered = DECK_SOURCE.read_text(encoding="utf-8")
    else:
        registered = deck_text(TOPOLOGY, MASK, RUN)
    if deck.exists() and deck.read_text(encoding="utf-8") != registered:
        raise RuntimeError(f"refusing to overwrite changed registered deck: {deck}")
    if not deck.exists():
        deck.write_text(registered, encoding="utf-8")
    entries = []
    for name, path, role in [
        ("canonical_qb", QB, "frozen canonical QB"),
        ("global_jjmit_model", MODEL, "global BVM/JSL/T1 model closure"),
        ("t1_cell", T1, "current user-modified T1"),
        ("bvm_jm2_connected", BVM, "frozen BVM source"),
        ("jtl2_source", JTL, "frozen JTL source"),
        ("josim_solver", SOLVER, "recorded solver"),
        ("plotter", PLOTTER, "standard renderer"),
    ]:
        entries.append({"name": name, "path": rel(path), "sha256": sha256(path), "bytes": path.stat().st_size, "role": role})
    old = {"path": rel(OLD_RAW), "sha256": sha256(OLD_RAW), "bytes": OLD_RAW.stat().st_size}
    provenance = {
        "schema": "bvm-qb-t1-single-rerun-provenance-v1",
        "experiment_id": EXP.name,
        "created_at": now(),
        "registration_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip(),
        "remote_bvm_master": subprocess.check_output(["git", "ls-remote", "bvm", "refs/heads/master"], cwd=REPO, text=True).split()[0],
        "solver": solver_context(),
        "sources": entries,
        "changed": {"path": rel(T1), "element": "R_J4", "before_ohm": 4, "after_ohm": 2, "t1_sha256": sha256(T1)},
        "registered_deck": {"path": rel(deck), "sha256": sha256(deck), "source_path": rel(DECK_SOURCE) if DECK_SOURCE is not None else None, "source_sha256": sha256(DECK_SOURCE) if DECK_SOURCE is not None else None},
        "comparison_reference": {"experiment": OLD_EXP.name, "raw": old, "not_copied": True},
        "raw_hash_before_analysis": {},
        "raw_hash_after_analysis": {},
        "transformations": [{"name": "phase_unwrap_for_navigation", "raw_mutated": False}, {"name": "phase_turn_display", "formula": "raw_phase_rad/(2*pi)", "raw_mutated": False}, {"name": "actual_grid_trapezoid", "interpolation": False, "raw_mutated": False}],
        "runs": {},
        "scientific_analysis_performed": False,
    }
    write_json(EXP / "provenance.json", provenance)
    write_json(EXP / "SOURCE_MANIFEST.json", {"schema": "bvm-qb-t1-single-rerun-source-manifest-v1", "experiment_id": EXP.name, "sources": entries, "old_raw_reference": old})
    state = {"schema": "bvm-qb-t1-single-rerun-state-v1", "experiment_id": EXP.name, "created_at": now(), "updated_at": now(), "status": "PREFLIGHT_PASS", "run_order": [], "authorized_physical_solve_count": 1, "actual_physical_solve_count": 0, "final_marker": None}
    write_json(EXP / "run_state.json", state)
    print(json.dumps({"status": "PREFLIGHT_PASS", "run": run_id(TOPOLOGY, MASK), "t1_sha256": sha256(T1)}, ensure_ascii=False, indent=2))


def execute() -> None:
    state = read_json(EXP / "run_state.json")
    provenance = read_json(EXP / "provenance.json")
    if state.get("actual_physical_solve_count") or state.get("final_marker"):
        raise RuntimeError("rerun already executed; refusing overwrite")
    registered_deck = provenance.get("registered_deck", {}).get("sha256")
    if registered_deck and sha256(RUN / "deck.cir") != registered_deck:
        raise RuntimeError("deck changed after preflight; refusing physical solve")
    registered_t1 = provenance.get("changed", {}).get("t1_sha256")
    if registered_t1 and sha256(T1) != registered_t1:
        raise RuntimeError("T1 source changed after preflight; refusing physical solve")
    run_one(TOPOLOGY, MASK, state, provenance)
    state["status"] = "RUN_COMPLETE"
    state["updated_at"] = now()
    write_json(EXP / "run_state.json", state)
    analyze()


def analyze() -> None:
    state = read_json(EXP / "run_state.json")
    provenance = read_json(EXP / "provenance.json")
    raw = RUN / "raw.csv"
    before = sha256(raw)
    provenance["raw_hash_before_analysis"] = {run_id(TOPOLOGY, MASK): before}
    write_json(EXP / "provenance.json", provenance)
    metrics = run_metrics(TOPOLOGY, MASK)
    after = sha256(raw)
    if before != after:
        raise RuntimeError("raw changed during analysis")
    result = {"schema": "bvm-qb-t1-single-rerun-result-v1", "experiment_id": EXP.name, "generated_at": now(), "artifact_status": "VALID", "execution": {"authorized_physical_solve_count": 1, "actual_physical_solve_count": 1, "completed_runs": [run_id(TOPOLOGY, MASK)]}, "observed": {"t1_change": "R_J4 4 -> 2 ohm", "phase_raw_unit": "radians", "raw_time_unit": "seconds"}, "derived": {"registered_window_arithmetic": metrics}, "comparison_reference": {"path": rel(OLD_RAW), "raw_sha256": sha256(OLD_RAW), "not_copied": True}, "unknown": ["SFQ count/event identity", "JJ switching certification", "interface Gate", "T1 truth table", "mechanism", "convergence", "route selection"], "interpretation": {"scientific_analysis_performed": False, "physical_verdict": "NOT_ASSIGNED", "review_state": "AWAITING_SCIENTIFIC_REVIEW", "phase_turns_are_navigation_only": True}, "stop": {"final_marker": "EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW", "automatic_follow_up": False}}
    write_json(EXP / "result.json", result)
    provenance = read_json(EXP / "provenance.json")
    provenance["raw_hash_after_analysis"] = {run_id(TOPOLOGY, MASK): after}
    provenance["analysis"] = {"raw_hashes_equal_before_after": True, "generated_at": now(), "scientific_analysis_performed": False}
    write_json(EXP / "provenance.json", provenance)
    state["status"] = "ANALYSIS_COMPLETE"
    state["final_marker"] = "EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW"
    state["updated_at"] = now()
    write_json(EXP / "run_state.json", state)
    (EXP / "RESULT.md").write_text("\n".join(["# BVM -> QB -> T1 T1-parameter rerun", "", "- Artifact status: `VALID`.", "- Authorized/completed physical solves: `1/1`.", "- Registered change: `R_J4 4 -> 2 ohm`.", "- Scientific interpretation: `NOT_PERFORMED`; physical verdict: `NOT_ASSIGNED`.", "", "The prior v2 `jtl6/0011` raw is preserved and referenced only by path/hash. P(...) remains raw radians; displayed turns are navigation only, not SFQ counts.", "", "EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW", ""]), encoding="utf-8")


def qa() -> None:
    state = read_json(EXP / "run_state.json")
    provenance = read_json(EXP / "provenance.json")
    raw = RUN / "raw.csv"
    header, _, times = run_data(TOPOLOGY, MASK)
    deck = RUN / "deck.cir"
    log = RUN / "run.log"
    unexpected = sorted(path.name for path in RUN.iterdir() if path.name not in {"deck.cir", "raw.csv", "run.log", "plots"})
    warnings = [line for line in log.read_text(errors="replace").splitlines() if "Missing model:" in line or "Using default model" in line]
    check = {"schema": "bvm-qb-t1-single-rerun-mechanical-qa-v1", "experiment_id": EXP.name, "generated_at": now(), "status": "PASS" if not unexpected and not warnings and sha256(raw) == provenance["raw_hash_after_analysis"][run_id(TOPOLOGY, MASK)] else "FAIL", "artifact_status": "VALID" if not unexpected and not warnings else "ARTIFACT_INVALID", "required_files_present": all(path.is_file() for path in (deck, raw, log)), "unexpected_entries": unexpected, "solver_model_warnings": warnings, "required_probe_count": len(required_headers(TOPOLOGY)), "header_count": len(header), "sample_count": len(times), "first_time_ps": times[0] * 1e12, "last_time_ps": times[-1] * 1e12, "raw_hash_before_after_equal": provenance.get("raw_hash_before_analysis") == provenance.get("raw_hash_after_analysis"), "scientific_interpretation_performed": False, "changed_t1_sha256": sha256(T1)}
    write_json(EXP / "mechanical_qa.json", check)
    if check["status"] != "PASS":
        raise RuntimeError("single rerun mechanical QA failed")
    print(json.dumps(check, ensure_ascii=False, indent=2))


def viz() -> None:
    if read_json(EXP / "mechanical_qa.json").get("status") != "PASS":
        raise RuntimeError("run QA before visualization")
    header, _, _ = run_data(TOPOLOGY, MASK)
    outdir = RUN / "plots"
    outdir.mkdir(exist_ok=True)
    entries = []
    for view in ("01_bvm_phase", "02_bvm_currents", "03_source_jsl", "04_qb", "05_jtl", "06_t1_jj", "07_t1_io"):
        subset = select_columns(header, view, TOPOLOGY)
        output = outdir / f"{view}.html"
        if output.exists():
            raise RuntimeError(f"refusing overwrite: {output}")
        command = [sys.executable, str(PLOTTER), str(RUN / "raw.csv"), "-x", str(output), "-t", "sep_comb", "-c", "dark", "-j", "2pi", "-w", f"{EXP.name} | jtl6 | mask=0011 | {view} | raw 0-200 ps", "-s", *subset]
        completed = subprocess.run(command, cwd=REPO, capture_output=True, text=True, check=False)
        if completed.returncode or not output.is_file() or not output.stat().st_size:
            raise RuntimeError(f"visualization failed: {output}: {completed.stderr[-500:]}")
        entries.append({"path": rel(output), "view": view, "run_id": run_id(TOPOLOGY, MASK), "raw_path": rel(RUN / "raw.csv"), "raw_sha256": sha256(RUN / "raw.csv"), "renderer": {"path": rel(PLOTTER), "sha256": sha256(PLOTTER)}, "window_ps": [0, 200], "phase_display": "2pi turns display from raw radians; not SFQ count"})
    manifest = {"schema": "bvm-qb-t1-single-rerun-visualization-manifest-v1", "experiment_id": EXP.name, "generated_at": now(), "entries": entries, "entry_count": len(entries), "renderer": "scripts/josim-plot2.py", "layout": "sep_comb", "color": "dark", "phase_option": "2pi", "focused_windows": [], "comparison_entries": [], "scientific_interpretation_performed": False, "status": "PASS"}
    write_json(EXP / "visualization_manifest.json", manifest)
    write_json(EXP / "visualization_qa.json", {"schema": "bvm-qb-t1-single-rerun-visualization-qa-v1", "experiment_id": EXP.name, "generated_at": now(), "status": "PASS", "entry_count": len(entries), "raw_hash_rechecked": all(item["raw_sha256"] == sha256(REPO / item["raw_path"]) for item in entries), "full_run_only": True, "focused_windows": [], "comparisons": 0, "image_files": [], "scientific_interpretation_performed": False})
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
    qa = {"schema": "bvm-qb-t1-single-rerun-package-qa-v1", "experiment_id": EXP.name, "generated_at": now(), "package_path": str(PACKAGE), "package_sha256": sha256(PACKAGE), "package_bytes": PACKAGE.stat().st_size, "git_head_at_packaging": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip(), "authorized_physical_solve_count": 1, "actual_physical_solve_count": 1, "file_count": len(records), "expected_file_hashes_match_after_reopen": expected == reopened, "contains_old_raw_copy": False, "files": records, "status": "PASS" if expected == reopened else "FAIL"}
    write_json(PACKAGE_QA, qa)
    print(json.dumps({"status": qa["status"], "package": str(PACKAGE), "sha256": qa["package_sha256"], "bytes": qa["package_bytes"], "files": len(records)}, ensure_ascii=False, indent=2))


def main() -> int:
    command = sys.argv[1] if len(sys.argv) > 1 else ""
    if command == "prepare": prepare()
    elif command == "run": execute()
    elif command == "analyze": analyze()
    elif command == "qa": qa()
    elif command == "viz": viz()
    elif command == "package": package()
    else:
        raise SystemExit("usage: bvm_qb_t1_single_rerun.py {prepare|run|analyze|qa|viz|package}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
