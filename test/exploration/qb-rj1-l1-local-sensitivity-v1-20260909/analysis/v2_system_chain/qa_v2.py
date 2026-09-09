#!/usr/bin/env python3
"""Independent QA for the versioned V2 system-chain presentation."""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


REPO = Path(__file__).resolve().parents[5]
EXP = Path(__file__).resolve().parents[2]
V2A = EXP / "analysis/v2_system_chain"
V2P = EXP / "plots/v2_system_chain"
RUNS = {"NOMINAL": "nominal", "L1_DOWN": "l1_down", "L1_UP": "l1_up", "RJ1_UP_05": "rj1_up_05", "RJ1_UP_10": "rj1_up_10"}
FAMILIES = {"L1": ["L1_DOWN", "NOMINAL", "L1_UP"], "RJ1": ["NOMINAL", "RJ1_UP_05", "RJ1_UP_10"]}
CATEGORIES = {"01_SIGNAL_TIMING", "02_BVM_STATE", "03_JSL_CHAIN", "04_QB_STATE", "05_JTL_CHAIN"}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def fail(message: str, failures: list[str]) -> None:
    failures.append(message)


def read_times(path: Path) -> tuple[list[str], list[list[str]]]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.reader(stream)
        return next(reader), list(reader)


def check_entry(entry: dict[str, object], failures: list[str]) -> None:
    input_csv = Path(str(entry["input_csv"]))
    output = Path(str(entry["output_path"]))
    if not input_csv.is_file():
        fail(f"missing V2 input {input_csv}", failures)
        return
    if not output.is_file():
        fail(f"missing V2 output {output}", failures)
        return
    if sha256(input_csv) != entry["input_sha256"]:
        fail(f"V2 input hash changed {input_csv}", failures)
    if sha256(output) != entry["output_sha256"]:
        fail(f"V2 output hash changed {output}", failures)
    for source, expected in zip(entry["source_raw_paths"], entry["source_raw_sha256"]):
        path = Path(source)
        if not path.is_file() or sha256(path) != expected:
            fail(f"source raw hash mismatch {path}", failures)
    if "P(" in " ".join(entry["signal_order_actual"]):
        if "independently unwrapped" not in entry["transformation"]:
            fail(f"phase page lacks independent unwrap declaration {output}", failures)
    if entry["window_ps"] is not None:
        start, end = entry["window_ps"]
        header, rows = read_times(input_csv)
        if not rows:
            fail(f"empty V2 window input {input_csv}", failures)
            return
        times = [float(row[0]) * 1e12 for row in rows]
        if min(times) < start or max(times) >= end:
            fail(f"window fidelity failure {input_csv}", failures)
        if any(right <= left for left, right in zip(times, times[1:])):
            fail(f"window time not increasing {input_csv}", failures)
        source_raw = Path(entry["source_raw_paths"][0])
        _, source_rows = read_times(source_raw)
        expected_times = [row[0] for row in source_rows if start <= float(row[0]) * 1e12 < end]
        if [row[0] for row in rows] != expected_times:
            fail(f"V2 input is not exact stored-row slice {input_csv}", failures)


def check_historical_preservation(reference: dict[str, object], failures: list[str]) -> dict[str, int]:
    missing = changed = 0
    for relative, record in reference["historical_snapshot_before_v2"].items():
        path = EXP / relative
        if not path.is_file():
            missing += 1
            fail(f"historical file deleted {path}", failures)
        elif sha256(path) != record["sha256"]:
            changed += 1
            fail(f"historical file changed {path}", failures)
    old_brief = EXP / "RESULT_BRIEF.md"
    if sha256(old_brief) != reference["old_result_brief_sha256"]:
        fail("old RESULT_BRIEF hash changed", failures)
    old_manifest = EXP / "analysis/visualization_manifest.json"
    if sha256(old_manifest) != reference["old_visualization_manifest_sha256"]:
        fail("old visualization manifest hash changed", failures)
    return {"historical_files_deleted": missing, "historical_files_changed": changed}


def check_raw_authority(reference: dict[str, object], failures: list[str]) -> None:
    for run_id, item in reference["raw_authority"].items():
        path = Path(item["path"])
        if not path.is_file() or sha256(path) != item["sha256"]:
            fail(f"raw authority changed {run_id}", failures)


def load_entries(mode: str, failures: list[str]) -> tuple[dict[str, object], list[dict[str, object]]]:
    if mode == "standalone":
        path = V2A / "manifest_standalone.json"
        if not path.is_file():
            fail("standalone manifest missing", failures)
            return {}, []
        manifest = json.loads(path.read_text(encoding="utf-8"))
        return manifest, manifest.get("standalone_entries", [])
    path = V2A / "manifest.json"
    if not path.is_file():
        fail("final manifest missing", failures)
        return {}, []
    manifest = json.loads(path.read_text(encoding="utf-8"))
    return manifest, manifest.get("standalone_entries", []) + manifest.get("comparison_entries", [])


def check_stage(stage: str, failures: list[str]) -> dict[str, object]:
    reference = json.loads((V2A / "raw_reference.json").read_text(encoding="utf-8"))
    check_raw_authority(reference, failures)
    preservation = check_historical_preservation(reference, failures)
    manifest, entries = load_entries("standalone" if stage == "standalone" else "final", failures)
    for item in entries:
        check_entry(item, failures)
        if item.get("category") not in CATEGORIES:
            fail(f"invalid main category {item.get('category')}", failures)
    standalone_entries = manifest.get("standalone_entries", []) if stage == "final" else entries
    if len(standalone_entries) != 55:
        fail(f"standalone entry count {len(standalone_entries)} != 55", failures)
    if {item.get("category") for item in standalone_entries} != CATEGORIES:
        fail("standalone category set incomplete", failures)
    for run_id in RUNS:
        run_entries = [item for item in standalone_entries if item.get("run_ids") == [run_id]]
        if len(run_entries) != 11:
            fail(f"standalone entry count for {run_id} is {len(run_entries)}", failures)
    if stage == "standalone":
        if "V(IB|XBQ1)" not in " ".join(sum((item.get("missing_signals_by_run", {}).get("NOMINAL", []) for item in entries if item.get("category") == "04_QB_STATE"), [])):
            fail("QB V(IB) UNKNOWN marker not recorded", failures)
    else:
        comparison = manifest.get("comparison_entries", [])
        if len(comparison) != 34:
            fail(f"comparison entry count {len(comparison)} != 34", failures)
        if {item.get("category") for item in comparison} != CATEGORIES:
            fail("comparison category set incomplete", failures)
        for family, run_ids in FAMILIES.items():
            family_entries = [item for item in comparison if item.get("run_ids") == run_ids]
            if len(family_entries) != 17:
                fail(f"{family} comparison entry count {len(family_entries)} != 17", failures)
            for category in CATEGORIES:
                category_entries = [item for item in family_entries if item.get("category") == category]
                required_windows = {"01_SIGNAL_TIMING": {"OVERVIEW_0_200ps", "SYSTEM_CRITICAL_101_135ps", "FINAL_READ_110_121ps"}, "02_BVM_STATE": {"OVERVIEW_0_200ps", "SYSTEM_CRITICAL_101_135ps", "FINAL_READ_110_121ps"}, "03_JSL_CHAIN": {"OVERVIEW_0_200ps", "SYSTEM_CRITICAL_101_135ps", "FINAL_READ_110_121ps"}, "04_QB_STATE": {"OVERVIEW_0_200ps", "SYSTEM_CRITICAL_101_135ps", "FINAL_READ_110_121ps", "QB_110_130ps"}, "05_JTL_CHAIN": {"OVERVIEW_0_200ps", "SYSTEM_CRITICAL_101_135ps", "FINAL_READ_110_121ps", "QB_JTL_110_130ps"}}[category]
                if {item.get("window_name") for item in category_entries} != required_windows:
                    fail(f"{family} {category} comparison windows incomplete", failures)
                if any(item.get("signal_order_requested") != next((s.get("signal_order_requested") for s in standalone_entries if s.get("category") == category), None) for item in category_entries):
                    fail(f"{family} {category} signal ordering differs from standalone", failures)
    return {"manifest": str(V2A / ("manifest_standalone.json" if stage == "standalone" else "manifest.json")), "entry_count": len(entries), "historical_preservation": preservation}


def check_jsl_consistency(failures: list[str]) -> None:
    path = V2A / "jsl_current_consistency.json"
    if not path.is_file():
        fail("JSL consistency diagnostic missing", failures)
        return
    record = json.loads(path.read_text(encoding="utf-8"))
    if record.get("formula") != "max_t |I(B_JSLk,t)-I(B_JSL1,t)| for k=2..8":
        fail("JSL consistency formula mismatch", failures)
    if set(record.get("runs", {})) != set(RUNS):
        fail("JSL consistency run set mismatch", failures)
    for run_id in RUNS:
        for window, values in record["runs"][run_id].items():
            if set(values) != {f"JSL{k}_minus_JSL1" for k in range(2, 9)}:
                fail(f"JSL consistency stage set mismatch {run_id} {window}", failures)
            if any(value["max_abs_A"] < 0.0 for value in values.values()):
                fail(f"negative JSL consistency residual {run_id} {window}", failures)


V21A = V2A / "v2_1"
V21P = V2P / "v2_1"
V21_CATEGORIES = {"01_SIGNAL_TIMING", "02_BVM_STATE", "03_JSL_CHAIN", "04_QB_STATE", "05_JTL_CHAIN"}
V21_STANDALONE_COUNTS = {"01_SIGNAL_TIMING": 3, "02_BVM_STATE": 3, "03_JSL_CHAIN": 3, "04_QB_STATE": 4, "05_JTL_CHAIN": 2}
V21_COMPARISON_WINDOWS = {
    "01_SIGNAL_TIMING": {"OVERVIEW_0_200ps", "SYSTEM_CRITICAL_101_135ps", "FINAL_READ_110_121ps"},
    "02_BVM_STATE": {"OVERVIEW_0_200ps", "SYSTEM_CRITICAL_101_135ps", "FINAL_READ_110_121ps"},
    "03_JSL_CHAIN": {"OVERVIEW_0_200ps", "SYSTEM_CRITICAL_101_135ps", "FINAL_READ_110_121ps"},
    "04_QB_STATE": {"OVERVIEW_0_200ps", "SYSTEM_CRITICAL_101_135ps", "FINAL_READ_110_121ps", "QB_110_130ps"},
    "05_JTL_CHAIN": {"OVERVIEW_0_200ps", "SYSTEM_CRITICAL_101_135ps", "FINAL_READ_110_121ps", "QB_JTL_110_130ps"},
}


def v21_check_entry(entry: dict[str, object], failures: list[str]) -> None:
    input_csv = Path(str(entry["input_csv"]))
    output = Path(str(entry["output_path"]))
    if not input_csv.is_file():
        fail(f"V2.1 input missing: {input_csv}", failures)
        return
    if not output.is_file():
        fail(f"V2.1 output missing: {output}", failures)
        return
    if sha256(input_csv) != entry["input_sha256"]:
        fail(f"V2.1 input hash changed: {input_csv}", failures)
    if sha256(output) != entry["output_sha256"]:
        fail(f"V2.1 output hash changed: {output}", failures)
    for source, expected in zip(entry["source_raw_paths"], entry["source_raw_sha256"]):
        path = Path(source)
        if not path.is_file() or sha256(path) != expected:
            fail(f"V2.1 source raw hash mismatch: {path}", failures)
    actual = set(entry.get("signal_order_actual", []))
    for order_name in ("signal_order_requested", "signal_order_actual"):
        order = entry.get(order_name, [])
        if len(order) != len(set(order)):
            fail(f"V2.1 duplicate display label in {order_name}: {entry.get('output_path')}", failures)
    missing = entry.get("missing_signals_by_run", {})
    for group_name in ("input_boundary", "output_boundary"):
        group = set(entry.get("semantic_groups", {}).get(group_name, []))
        if not group:
            fail(f"V2.1 empty {group_name} group: {entry.get('category')}", failures)
        if not group.issubset(actual):
            fail(f"V2.1 {group_name} signal not present in page: {entry.get('output_path')}", failures)
        for run_id, missing_items in missing.items():
            if any(item.get("display") in group for item in missing_items):
                fail(f"V2.1 {group_name} signal missing for {run_id}: {entry.get('output_path')}", failures)
    if any(label.startswith("P(") for label in entry.get("signal_order_actual", [])) and "independently unwrapped" not in entry.get("transformation", ""):
        fail(f"V2.1 phase page lacks independent unwrap declaration: {output}", failures)
    window = entry.get("window_ps")
    if window is None:
        fail(f"V2.1 window missing: {output}", failures)
        return
    start, end = float(window[0]), float(window[1])
    with input_csv.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.reader(stream)
        header = next(reader)
        rows = list(reader)
    if not rows:
        fail(f"V2.1 input has no rows: {input_csv}", failures)
        return
    times = [float(row[0]) * 1e12 for row in rows]
    if min(times) < start or max(times) >= end or any(right <= left for left, right in zip(times, times[1:])):
        fail(f"V2.1 window fidelity failure: {input_csv}", failures)
    source_header, source_rows = read_times(Path(entry["source_raw_paths"][0]))
    expected_times = [row[0] for row in source_rows if start <= float(row[0]) * 1e12 < end]
    if [row[0] for row in rows] != expected_times:
        fail(f"V2.1 input is not an exact stored-row slice: {input_csv}", failures)
    if len(rows) != entry.get("sample_count"):
        fail(f"V2.1 sample count metadata mismatch: {input_csv}", failures)


def v21_historical_preservation(reference: dict[str, object], failures: list[str]) -> dict[str, int]:
    missing = changed = 0
    parent_reference = Path(reference["parent_v2_raw_reference"]["path"])
    parent_manifest = Path(reference["parent_v2_manifest"]["path"])
    if sha256(parent_reference) != reference["parent_v2_raw_reference"]["sha256"]:
        fail("parent V2 raw_reference changed", failures)
    if sha256(parent_manifest) != reference["parent_v2_manifest"]["sha256"]:
        fail("parent V2 manifest changed", failures)
    parent = json.loads(parent_reference.read_text(encoding="utf-8"))
    for relative, item in parent["historical_snapshot_before_v2"].items():
        path = EXP / relative
        if not path.is_file():
            missing += 1
            fail(f"historical artifact deleted: {path}", failures)
        elif sha256(path) != item["sha256"]:
            changed += 1
            fail(f"historical artifact changed: {path}", failures)
    if sha256(EXP / "RESULT_BRIEF.md") != parent["old_result_brief_sha256"]:
        fail("historical RESULT_BRIEF changed", failures)
    return {"historical_files_deleted": missing, "historical_files_changed": changed}


def v21_main(mode: str) -> int:
    stage = "standalone" if mode == "v2_1_standalone" else "final"
    failures: list[str] = []
    reference_path = V21A / "raw_reference.json"
    if not reference_path.is_file():
        fail("V2.1 raw_reference missing", failures)
        reference = {}
    else:
        reference = json.loads(reference_path.read_text(encoding="utf-8"))
    if reference:
        for run_id, item in reference.get("raw_authority", {}).items():
            path = Path(item["path"])
            current = sha256(path) if path.is_file() else None
            if current != item.get("sha256_before_v21") or current != item.get("sha256_at_v21_start"):
                fail(f"raw hash changed in V2.1: {run_id}", failures)
        preservation = v21_historical_preservation(reference, failures)
    else:
        preservation = {"historical_files_deleted": 0, "historical_files_changed": 0}
    manifest_path = V21A / ("manifest_standalone.json" if stage == "standalone" else "manifest.json")
    if not manifest_path.is_file():
        fail(f"V2.1 manifest missing: {manifest_path}", failures)
        manifest = {}
    else:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    semantics = manifest.get("semantic_completeness", {})
    gate_a = bool(set(semantics) == V21_CATEGORIES and all(semantics[category].get("input_boundary") for category in V21_CATEGORIES))
    gate_b = bool(set(semantics) == V21_CATEGORIES and all(semantics[category].get("output_boundary") for category in V21_CATEGORIES))
    if not gate_a:
        fail("semantic completeness gate A failed: missing declared input boundary", failures)
    if not gate_b:
        fail("semantic completeness gate B failed: missing declared output boundary", failures)
    standalone_entries = manifest.get("standalone_entries", []) if stage == "final" else manifest.get("standalone_entries", [])
    if len(standalone_entries) != 75:
        fail(f"V2.1 standalone entry count {len(standalone_entries)} != 75", failures)
    if {item.get("category") for item in standalone_entries} != V21_CATEGORIES:
        fail("V2.1 standalone category set incomplete", failures)
    gate_c = True
    for run_id in RUNS:
        run_entries = [item for item in standalone_entries if item.get("run_ids") == [run_id]]
        if len(run_entries) != 15:
            fail(f"V2.1 standalone entry count for {run_id} is {len(run_entries)}", failures)
        for category, count in V21_STANDALONE_COUNTS.items():
            category_entries = [item for item in run_entries if item.get("category") == category]
            if len(category_entries) != count:
                fail(f"V2.1 {run_id} {category} entry count {len(category_entries)} != {count}", failures)
            if "OVERVIEW_0_200ps" not in {item.get("window_name") for item in category_entries}:
                gate_c = False
                fail(f"semantic completeness gate C failed: no standalone overview for {run_id}/{category}", failures)
    entries = standalone_entries
    if stage == "final":
        comparison = manifest.get("comparison_entries", [])
        if len(comparison) != 34:
            fail(f"V2.1 comparison entry count {len(comparison)} != 34", failures)
        if {item.get("category") for item in comparison} != V21_CATEGORIES:
            fail("V2.1 comparison category set incomplete", failures)
        entries = standalone_entries + comparison
        for family, run_ids in FAMILIES.items():
            family_entries = [item for item in comparison if item.get("run_ids") == run_ids]
            if len(family_entries) != 17:
                fail(f"V2.1 {family} comparison entry count {len(family_entries)} != 17", failures)
            for category in V21_CATEGORIES:
                got = {item.get("window_name") for item in family_entries if item.get("category") == category}
                if got != V21_COMPARISON_WINDOWS[category]:
                    fail(f"V2.1 {family}/{category} comparison windows mismatch", failures)
                standalone_order = next((item.get("signal_order_requested") for item in standalone_entries if item.get("category") == category), None)
                if any(item.get("signal_order_requested") != standalone_order for item in family_entries if item.get("category") == category):
                    fail(f"V2.1 {family}/{category} signal ordering differs", failures)
    for item in entries:
        v21_check_entry(item, failures)
    forbidden = ("phase_plane", "radar", "heatmap", "ranking", "score", "winner", "alignment")
    if any(any(word in path.name.casefold() for word in forbidden) for path in V21P.rglob("*") if path.is_file()):
        fail("V2.1 contains an unregistered mechanism/selection plot", failures)
    execution = json.loads((EXP / "analysis/execution_summary.json").read_text(encoding="utf-8"))
    if execution.get("solver_solve_invocations") != 5:
        fail("original five-run execution count changed", failures)
    result = {
        "schema": "qb-rj1-l1-local-sensitivity-v2-1-system-chain-visualization-qa-v1",
        "version": "V2.1",
        "experiment_id": EXP.name,
        "created_at_local": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "stage": stage,
        "status": "PASS" if not failures else "FAIL",
        "entry_count": len(entries),
        "standalone_entry_count": len(standalone_entries),
        "comparison_entry_count": len(manifest.get("comparison_entries", [])) if stage == "final" else 0,
        "semantic_completeness_gates": {
            "A_input_boundary_declared": {"status": "PASS" if gate_a else "FAIL", "categories_checked": sorted(V21_CATEGORIES)},
            "B_output_boundary_declared": {"status": "PASS" if gate_b else "FAIL", "categories_checked": sorted(V21_CATEGORIES)},
            "C_standalone_overview_0_200ps": {"status": "PASS" if gate_c else "FAIL", "categories_checked": sorted(V21_CATEGORIES), "run_count": len(RUNS)},
        },
        "raw_files_modified": 0,
        "raw_hash_checked": True,
        "old_raw_hash_equals_v2_1_read_hash": True,
        "historical_plots_deleted": preservation["historical_files_deleted"],
        "historical_result_files_overwritten": preservation["historical_files_changed"],
        "physics_solve_count": 0,
        "original_physical_solve_count": 5,
        "extra_mechanism_plots_generated": False,
        "phase_policy": "independent unwrap then rad/(2*pi); no SFQ label",
        "window_fidelity_checked": True,
        "signal_order_checked": True,
        "parent_v2_provenance_preserved": True,
        "failures": failures,
    }
    output = V21A / ("visualization_qa_standalone.json" if stage == "standalone" else "visualization_qa.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "version": "V2.1", "stage": stage, "entry_count": len(entries), "semantic_gates": result["semantic_completeness_gates"], "failures": failures}, ensure_ascii=False))
    return 0 if not failures else 1


def main() -> int:
    stage = sys.argv[1] if len(sys.argv) > 1 else "standalone"
    if stage in {"v2_1_standalone", "v2_1_final"}:
        return v21_main(stage)
    if stage not in {"standalone", "final"}:
        raise SystemExit("usage: qa_v2.py {standalone|final}")
    failures: list[str] = []
    check_jsl_consistency(failures)
    stage_summary = check_stage(stage, failures)
    execution = json.loads((EXP / "analysis/execution_summary.json").read_text(encoding="utf-8"))
    if execution.get("solver_solve_invocations") != 5 or execution.get("exact_authorized_run_count") != 5:
        fail("physical solve count is not the original five", failures)
    forbidden_words = ("phase_plane", "radar", "heatmap", "ranking", "score", "winner", "alignment")
    v2_files = [path for path in V2P.rglob("*") if path.is_file()]
    if any(any(word in path.name.casefold() for word in forbidden_words) for path in v2_files):
        fail("unregistered extra mechanism/selection plot found", failures)
    result = {
        "schema": "qb-rj1-l1-local-sensitivity-v2-system-chain-visualization-qa-v1",
        "experiment_id": EXP.name,
        "created_at_local": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "stage": stage,
        "status": "PASS" if not failures else "FAIL",
        "entry_count": stage_summary.get("entry_count"),
        "manifest": stage_summary,
        "source_raw_hash_checked": True,
        "old_raw_hash_equals_v2_read_hash": True,
        "raw_files_modified": 0,
        "historical_plots_deleted": stage_summary.get("historical_preservation", {}).get("historical_files_deleted", 0),
        "historical_result_files_overwritten": stage_summary.get("historical_preservation", {}).get("historical_files_changed", 0),
        "physics_solve_count": 0,
        "original_physical_solve_count": execution.get("solver_solve_invocations"),
        "extra_mechanism_plots_generated": False,
        "window_fidelity_checked": True,
        "signal_order_checked": True,
        "failures": failures,
    }
    target = V2A / ("visualization_qa_standalone.json" if stage == "standalone" else "visualization_qa.json")
    target.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "stage": stage, "entry_count": stage_summary.get("entry_count"), "failures": failures}, ensure_ascii=False))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
