#!/usr/bin/env python3
"""Read-only raw reanalysis for the user-run C4R28_210 matrix; never invokes JoSIM."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ANALYSIS_DIR = Path(__file__).resolve().parent
SERIES = ANALYSIS_DIR.parents[1]
REPO = SERIES.parents[2]
RUNS = SERIES / "runs"
PLOTS_DIR = SERIES / "plots" / "carry4-functional-28-20261010"
MANUAL_DIR = SERIES / "manual_batches" / "C4R28_210"
MANUAL_SCRIPT = SERIES / "run_carry4_functional_28.sh"
MANIFEST_PATH = SERIES / "experiment_manifest.json"
ANCHOR_ID = "A045_MANUAL_CARRY4_15x15_210"
PARENT_HEAD = "e246b41421e4341bf43f5a6c92797dd990cc6889"
WINDOWS = ("ARRAY_FINAL_READ", "PRE_CLOCK", "BEFORE_CLOCK", "CLOCK_EDGE", "POST_CLOCK", "TOTAL")
DIAGONAL_LENGTHS = (1, 2, 3, 4, 3, 2, 1)
EXPECTED_CARRY_COUNTS = {"D1": 1, "D2": 1, "D3": 4, "D4": 1, "D5": 1, "D6": 1}

CATEGORIES = [
    ("G01", [(15, 14), (14, 15), (14, 14)]),
    ("G02", [(15, 13), (13, 15), (15, 11), (11, 15)]),
    ("G03", [(15, 7), (7, 15), (7, 7)]),
    ("G04", [(7, 14), (14, 7), (9, 13), (13, 9)]),
    ("G05", [(5, 10), (10, 5)]),
    ("G06", [(1, 1), (1, 15), (15, 1)]),
    ("G07", [(2, 15), (15, 2)]),
    ("G08", [(4, 15), (15, 4)]),
    ("G09", [(8, 15), (15, 8)]),
    ("G10", [(0, 0), (0, 15), (15, 0)]),
]
EXPECTED_PAIRS = [pair for _, pairs in CATEGORIES for pair in pairs]

sys.path.insert(0, str((SERIES / "scripts").resolve()))
import diagonal_platform as dp  # noqa: E402


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def json_cell(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def row_bits(a: int) -> str:
    return "".join(str((a >> bit) & 1) for bit in range(4))


def col_bits(b: int) -> str:
    return "".join(str((b >> bit) & 1) for bit in (3, 2, 1, 0))


def active_cells(a: int, b: int) -> list[str]:
    cells = []
    for row in range(1, 5):
        for col in range(1, 5):
            if ((a >> (row - 1)) & 1) and ((b >> (4 - col)) & 1):
                cells.append(f"R{row}C{col}")
    return cells


def expected_diagonal_counts(cells: list[str]) -> dict[str, int]:
    counts = {f"D{i}": 0 for i in range(7)}
    for cell in cells:
        row, col = int(cell[1]), int(cell[3])
        counts[f"D{row + 3 - col}"] += 1
    return counts


def map_records(items: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    return {item[key]: item for item in items}


def metric_index(metrics: dict[str, Any]) -> tuple[dict[tuple[str, str], dict[str, Any]],
                                                  dict[tuple[str, str], dict[str, Any]],
                                                  dict[tuple[str, str], dict[str, Any]]]:
    wave = {(item["signal"], item["window"]): item for item in metrics["waveforms"]}
    junction = {(item["phase_signal"], item["window"]): item for item in metrics["same_jj_phase_voltage"]}
    current = {(item["signal"], item["window"]): item for item in metrics["currents"]}
    return wave, junction, current


def phase_bundle(index: dict[tuple[str, str], dict[str, Any]], signal: str) -> dict[str, Any]:
    result = {"signal": signal, "phase_raw_unit": "rad", "windows": {}}
    found = False
    for window in WINDOWS:
        item = index.get((signal, window))
        if item is None:
            result["windows"][window] = {"status": "UNKNOWN_MISSING_PROBE"}
            continue
        found = True
        result["windows"][window] = {
            "sample_count": item.get("sample_count"),
            "phase_delta_rad": item["phase_delta_rad"],
            "phase_delta_over_2pi_navigation": item["phase_delta_rad_over_2pi_navigation"],
            "positive_phase_variation_turns_navigation": item["positive_phase_variation_turns_navigation"],
            "negative_phase_variation_turns_navigation": item["negative_phase_variation_turns_navigation"],
            "same_jj_voltage_area_v_s": item["voltage_area_v_s_same_jj_same_rows"],
            "same_jj_voltage_area_phi0_arithmetic": item["voltage_area_phi0_arithmetic"],
            "phase_minus_area_turn_arithmetic": item["phase_minus_area_turn_arithmetic"],
            "interpolation_or_resampling": item["interpolation_or_resampling"],
        }
    result["status"] = "OBSERVED_DERIVED_FROM_RAW" if found else "UNKNOWN_MISSING_PROBE"
    return result


def wave_bundle(index: dict[tuple[str, str], dict[str, Any]], signal: str) -> dict[str, Any]:
    result = {"signal": signal, "unit": "V", "windows": {}}
    found = False
    for window in WINDOWS:
        item = index.get((signal, window))
        if item is None:
            result["windows"][window] = {"status": "UNKNOWN_MISSING_PROBE"}
            continue
        found = True
        result["windows"][window] = {
            "sample_count": item.get("sample_count"),
            "min_v": item["min_v"], "max_v": item["max_v"],
            "peak_to_peak_v": item["peak_to_peak_v"],
            "time_of_min_ps": item["time_of_min_s"] * 1e12,
            "time_of_max_ps": item["time_of_max_s"] * 1e12,
            "signed_area_v_s": item["signed_area_v_s"],
            "signed_area_phi0_arithmetic": item["signed_area_phi0_arithmetic"],
            "descriptive_lobe_candidates": item.get("descriptive_lobe_candidates"),
            "interpolation_or_resampling": item["interpolation_or_resampling"],
        }
    result["status"] = "OBSERVED_DERIVED_FROM_RAW" if found else "UNKNOWN_MISSING_PROBE"
    return result


def current_bundle(index: dict[tuple[str, str], dict[str, Any]], signal: str | None) -> dict[str, Any]:
    if not signal:
        return {"status": "NOT_APPLICABLE"}
    result = {"signal": signal, "unit": "A", "windows": {}}
    found = False
    for window in WINDOWS:
        item = index.get((signal, window))
        if item is None:
            result["windows"][window] = {"status": "UNKNOWN_MISSING_PROBE"}
            continue
        found = True
        result["windows"][window] = {
            "min_a": item["min_a"], "max_a": item["max_a"],
            "peak_to_peak_a": item["peak_to_peak_a"],
            "charge_c": item["charge_c"], "direction": item["direction"],
        }
    result["status"] = "OBSERVED_DERIVED_FROM_RAW" if found else "UNKNOWN_MISSING_PROBE"
    return result


def compare_metrics(recomputed: dict[str, Any], stored: dict[str, Any]) -> dict[str, Any]:
    errors: list[float] = []
    mismatches = []
    for section, key_fields, value_fields in (
        ("waveforms", ("signal", "window"), ("signed_area_v_s", "signed_area_phi0_arithmetic")),
        ("currents", ("signal", "window"), ("charge_c",)),
        ("same_jj_phase_voltage", ("phase_signal", "window"),
         ("phase_delta_rad", "voltage_area_v_s_same_jj_same_rows", "voltage_area_phi0_arithmetic")),
    ):
        left = {tuple(item[k] for k in key_fields): item for item in recomputed.get(section, [])}
        right = {tuple(item[k] for k in key_fields): item for item in stored.get(section, [])}
        if left.keys() != right.keys():
            mismatches.append(f"{section}:key_set")
            continue
        for key, item in left.items():
            for field in value_fields:
                a, b = item.get(field), right[key].get(field)
                if a is None or b is None:
                    if a != b:
                        mismatches.append(f"{section}:{key}:{field}")
                    continue
                errors.append(abs(float(a) - float(b)))
                if float(a) != float(b):
                    mismatches.append(f"{section}:{key}:{field}")
    return {"exact_metric_replay_match": not mismatches, "mismatch_count": len(mismatches),
            "mismatch_examples": mismatches[:10], "max_absolute_numeric_difference": max(errors, default=0.0)}


def parse_pwl_sources(path: Path) -> dict[str, dict[str, str]]:
    output: dict[str, dict[str, str]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^(\S+)\s+\S+\s+\S+\s+PWL\((.*)\)\s*$", line)
        if not match:
            continue
        tokens = match.group(2).split()
        if len(tokens) % 2:
            raise ValueError(f"malformed PWL pair list for {match.group(1)}")
        output[match.group(1)] = dict(zip(tokens[::2], tokens[1::2], strict=True))
    return output


def verify_stimulus(run_dir: Path, a: int, b: int) -> dict[str, Any]:
    sources = parse_pwl_sources(run_dir / "stimulus.inc")
    expected_names = {*(f"I_WL_R{r}" for r in range(1, 5)), *(f"I_BL_C{c}" for c in range(1, 5)),
                      *(f"I_SE_R{r}C{c}" for r in range(1, 5) for c in range(1, 5))}
    if set(sources) != expected_names:
        raise ValueError(f"stimulus source set mismatch: {run_dir.name}")
    checks = 0
    failures = []
    for r in range(1, 5):
        row_active = (a >> (r - 1)) & 1
        if sources[f"I_WL_R{r}"].get("111p") != ("400u" if row_active else "0"):
            failures.append(f"I_WL_R{r}:FINAL_READ")
        if sources[f"I_WL_R{r}"].get("71p") != "400u":
            failures.append(f"I_WL_R{r}:READ0")
        if sources[f"I_WL_R{r}"].get("51p") != "-400u":
            failures.append(f"I_WL_R{r}:WRITE0")
        if sources[f"I_WL_R{r}"].get("91p") != "400u":
            failures.append(f"I_WL_R{r}:WRITE1")
        checks += 4
    for c in range(1, 5):
        col_active = (b >> (4 - c)) & 1
        if sources[f"I_BL_C{c}"].get("111p") != "0":
            failures.append(f"I_BL_C{c}:FINAL_READ")
        if sources[f"I_BL_C{c}"].get("51p") != "-400u" or sources[f"I_BL_C{c}"].get("91p") != "400u":
            failures.append(f"I_BL_C{c}:WRITE")
        if sources[f"I_BL_C{c}"].get("71p") != "0":
            failures.append(f"I_BL_C{c}:READ0")
        checks += 4
        for r in range(1, 5):
            active = bool(((a >> (r - 1)) & 1) and col_active)
            name = f"I_SE_R{r}C{c}"
            if sources[name].get("111p") != ("100u" if active else "0"):
                failures.append(f"{name}:FINAL_READ")
            if sources[name].get("71p") != "100u":
                failures.append(f"{name}:READ0")
            if sources[name].get("51p") != "0" or sources[name].get("91p") != "0":
                failures.append(f"{name}:WRITE")
            checks += 4
    return {"status": "PASS" if not failures else "FAIL", "source_count": len(sources),
            "expected_source_count": 24, "assertion_count": checks,
            "failures": failures, "final_read_policy": "WL by row; BL=0; SE=ROW AND COLUMN AND ALL mask"}


def collect_runs(limit: int | None = None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    experiment = load_json(MANIFEST_PATH)
    selected_records = [item for item in experiment["runs"]
                        if item.get("case", "").startswith("C4R28_210_")]
    run_records = {item["case"]: item for item in selected_records}
    expected_cases = [f"C4R28_210_{a}x{b}" for a, b in EXPECTED_PAIRS]
    if len(selected_records) != 28 or len(run_records) != 28 or set(run_records) != set(expected_cases):
        raise ValueError(f"expected exactly the 28 registered case names; discovered {len(run_records)}")
    if len(EXPECTED_PAIRS) != 28 or len(set(EXPECTED_PAIRS)) != 28:
        raise ValueError("analysis input matrix itself contains duplicate or missing pairs")

    preflight_ok = (MANUAL_DIR / "preflight.ok").read_text(encoding="utf-8").strip().split("\t")
    if len(preflight_ok) != 2:
        raise ValueError("preflight.ok malformed")
    script_sha = sha256(MANUAL_SCRIPT)
    if preflight_ok != [script_sha, PARENT_HEAD]:
        raise ValueError("preflight.ok does not match the observed script SHA and registered parent HEAD")
    preflight_logs = sorted(MANUAL_DIR.glob("preflight_C4R28_210_*.log"))
    if len(preflight_logs) != 28 or any("DRY RUN PASS" not in p.read_text(errors="replace") for p in preflight_logs):
        raise ValueError("preflight logs are not exactly 28 dry-run PASS records")

    anchor_dir = RUNS / ANCHOR_ID
    anchor_result = load_json(anchor_dir / "result.json")
    anchor_metadata = load_json(anchor_dir / "metadata.json")
    anchor_case = anchor_metadata["effective_case"]
    anchor_sha = sha256(anchor_dir / "deck.cir")
    if anchor_sha != anchor_result.get("deck_sha256"):
        raise ValueError("A045 anchor deck hash differs from its result record")
    analysis_records = []
    stage_rows_all = []
    case_pairs = list(zip(expected_cases, EXPECTED_PAIRS, strict=True))
    if limit is not None:
        case_pairs = case_pairs[:limit]

    for case_name, (a, b) in case_pairs:
        record = run_records[case_name]
        run_id = record["run_id"]
        run_dir = RUNS / run_id
        if not run_dir.is_dir():
            raise FileNotFoundError(run_dir)
        result = load_json(run_dir / "result.json")
        qa = load_json(run_dir / "qa.json")
        raw_qa_existing = load_json(run_dir / "raw_qa.json")
        static_qa = load_json(run_dir / "static_qa.json")
        chain_qa = load_json(run_dir / "chain_qa.json")
        plot_qa = load_json(run_dir / "plot_qa.json")
        metadata = load_json(run_dir / "metadata.json")
        provenance = load_json(run_dir / "provenance.json")
        source_manifest = load_json(run_dir / "source_manifest.json")
        probe_manifest = load_json(run_dir / "probe_manifest.json")
        required_files = {
            "deck.cir", "stimulus.inc", "raw.csv", "result.json", "qa.json", "raw_qa.json",
            "static_qa.json", "chain_qa.json", "plot_qa.json", "metadata.json", "provenance.json",
            "probe_manifest.json", "source_manifest.json", "stdout.txt", "stderr.txt", "run.log",
            "USER_CASE.snapshot.env", "STIMULUS.snapshot.env", "T1_PARAMS.snapshot.env",
            "CBU_PARAMS.snapshot.env", "DFF_PARAMS.snapshot.env", "D0_JTL_PARAMS.snapshot.env",
        }
        missing_files = sorted(name for name in required_files if not (run_dir / name).is_file())
        if missing_files:
            raise ValueError(f"run evidence files missing: {run_id}: {missing_files}")
        case = metadata["effective_case"]
        expected_rows, expected_cols = row_bits(a), col_bits(b)
        if (result.get("case") != case_name or result.get("run_id") != run_id or
                case.get("CASE") != case_name or case.get("ROW_BITS") != expected_rows or
                case.get("COL_BITS") != expected_cols or record.get("row_bits") != expected_rows or
                record.get("column_bits") != expected_cols):
            raise ValueError(f"input-to-run mapping mismatch: {case_name}/{run_id}")
        allowed_case_variation = {"CASE", "ROW_BITS", "COL_BITS"}
        base_compare = {k: v for k, v in anchor_case.items() if k not in allowed_case_variation}
        run_compare = {k: v for k, v in case.items() if k not in allowed_case_variation}
        if run_compare != base_compare:
            raise ValueError(f"effective config differs from A045 outside CASE/ROW_BITS/COL_BITS: {run_id}")
        if metadata.get("effective_stimulus") != anchor_metadata.get("effective_stimulus"):
            raise ValueError(f"effective stimulus timing/config mismatch: {run_id}")
        deck_sha = sha256(run_dir / "deck.cir")
        if (deck_sha != anchor_sha or deck_sha != result.get("deck_sha256") or
                record.get("deck_sha256") != deck_sha):
            raise ValueError(f"deck identity differs from A045: {run_id}")
        if (result.get("artifact_status") != "VALID" or result.get("physical_solve_count") != 1 or
                result.get("solver_exit_code") != 0 or result.get("qa_status") != "PASS" or
                qa.get("status") != "PASS" or qa.get("artifact_status") != "VALID" or
                qa.get("physical_solve_count") != 1 or qa.get("solver_exit_code") != 0 or
                raw_qa_existing.get("status") != "PASS" or static_qa.get("status") != "PASS" or
                chain_qa.get("status") != "PASS" or plot_qa.get("status") != "PASS"):
            raise ValueError(f"run artifact/mechanical/visual QA failure: {run_id}")
        if (metadata.get("solver", {}).get("parent_head") != PARENT_HEAD or
                metadata.get("solver", {}).get("sha256") != anchor_metadata.get("solver", {}).get("sha256") or
                metadata.get("source_sha256") != anchor_metadata.get("source_sha256") or
                provenance.get("parent_head") != PARENT_HEAD or
                provenance.get("raw_sha256") != result.get("raw_sha256") or
                provenance.get("deck_sha256") != result.get("deck_sha256") or
                provenance.get("source_sha256") != metadata.get("source_sha256")):
            raise ValueError(f"solver/source provenance differs from A045: {run_id}")
        manifest_source_hashes = {name: entry.get("sha256") for name, entry in source_manifest.get("sources", {}).items()}
        if manifest_source_hashes != metadata.get("source_sha256"):
            raise ValueError(f"source_manifest/metadata source SHA map differs: {run_id}")
        for name, entry in source_manifest.get("sources", {}).items():
            source_path = Path(entry["path"])
            if entry.get("mode", "").startswith("RUN_LOCAL"):
                source_path = run_dir / source_path
            else:
                source_path = REPO / source_path
            if not source_path.is_file() or sha256(source_path) != entry.get("sha256"):
                raise ValueError(f"source file SHA mismatch {run_id}/{name}: {source_path}")
        if raw_qa_existing.get("raw_sha256_before") != result.get("raw_sha256") or \
                raw_qa_existing.get("raw_sha256_after_analysis") != result.get("raw_sha256") or \
                qa.get("raw_sha256_before_analysis") != result.get("raw_sha256") or \
                qa.get("raw_sha256_after_analysis") != result.get("raw_sha256") or \
                provenance.get("raw_sha256") != result.get("raw_sha256"):
            raise ValueError(f"existing raw SHA chain mismatch: {run_id}")
        if sha256(run_dir / "stimulus.inc") != result.get("stimulus_sha256"):
            raise ValueError(f"stimulus.inc SHA mismatch: {run_id}")
        expected_cells = active_cells(a, b)
        derived_counts = expected_diagonal_counts(expected_cells)
        actual_crosspoints = record.get("active_final_crosspoints", result.get("active_final_crosspoints", []))
        if sorted(actual_crosspoints) != sorted(expected_cells):
            raise ValueError(f"active FINAL_READ crosspoints mismatch from bit encoding: {run_id}")

        stimulus_qa = verify_stimulus(run_dir, a, b)
        if stimulus_qa["status"] != "PASS":
            raise ValueError(f"stimulus PWL mismatch: {run_id}: {stimulus_qa['failures'][:8]}")
        raw_metrics, raw_qa = dp.analyze_t1_chain_raw(run_dir, probe_manifest, case)
        if (raw_qa.get("status") != "PASS" or raw_qa.get("raw_sha256_before") != result.get("raw_sha256") or
                raw_qa.get("raw_sha256_after_analysis") != result.get("raw_sha256") or
                raw_qa.get("sample_count") != result.get("sample_count")):
            raise ValueError(f"independent raw reread QA failed: {run_id}")
        stored_metrics = load_json(run_dir / "metrics.json")
        metric_check = compare_metrics(raw_metrics, stored_metrics)
        if not metric_check["exact_metric_replay_match"]:
            raise ValueError(f"raw-recomputed metrics do not match stored mechanics: {run_id}: {metric_check['mismatch_examples']}")
        if raw_metrics.get("actual_product_bit_decoding") != "NOT_PERFORMED; no decode threshold preregistered":
            raise ValueError(f"unexpected or changed product decoder metric: {run_id}")

        wave, junction, current = metric_index(raw_metrics)
        pair_group = next(group_id for group_id, pairs in CATEGORIES if (a, b) in pairs)
        theoretical_product = a * b
        expected_bits = "".join(str((theoretical_product >> bit) & 1) for bit in range(8))
        output_areas = {f"S{d}": {window: wave_bundle(wave, f"V(S_D{d})")["windows"][window].get("signed_area_phi0_arithmetic")
                                          for window in ("ARRAY_FINAL_READ", "PRE_CLOCK", "CLOCK_EDGE", "POST_CLOCK", "TOTAL")}
                        for d in range(7)}
        output_areas["DFF_O"] = {window: wave_bundle(wave, "V(DFF_O)")["windows"][window].get("signed_area_phi0_arithmetic")
                                 for window in ("ARRAY_FINAL_READ", "PRE_CLOCK", "CLOCK_EDGE", "POST_CLOCK", "TOTAL")}
        timing_by_stage = {item["stage"]: item for item in raw_metrics["stage_timing_descriptors"]}
        stage_rows = []
        for d in range(7):
            stage_name = f"D{d}"
            array_cb = f"XCB_D{d}_L{DIAGONAL_LENGTHS[d]}"
            array_cb_jjs = {f"BJ{jj}": phase_bundle(junction, f"P(BJ{jj}|{array_cb})") for jj in (1, 2)}
            if d == 0:
                pre_cb_jj_signals = [item["label"] for item in probe_manifest["signals"]
                                     if item["label"].startswith("P(") and "XJTL_D0_" in item["label"]]
                carry_cb_jjs = {"status": "NOT_APPLICABLE_D0"}
                input_currents = ["I(V_T1_LINK_D0)"]
                carry_current_names: list[str] = []
            else:
                pre_cb_jj_signals = [item["label"] for item in probe_manifest["signals"]
                                     if item["label"].startswith("P(") and
                                     item.get("group", "").startswith(f"chain_pre_cb_sjtl:{stage_name}:")]
                carry_cb_jjs = {f"BJ{jj}": phase_bundle(junction, f"P(BJ{jj}|XCB_CARRY_{stage_name})")
                                for jj in (1, 2)}
                input_currents = [f"I(V_CBU_A_{stage_name})"]
                carry_current_names = [f"I(V_CARRY_IN_{stage_name})", f"I(V_CARRY_SJTL_OUT_{stage_name})"]
                carry_current_names.extend(item["label"] for item in probe_manifest["signals"]
                                            if item["label"].startswith("I(V_CARRY_SJTL_LINK_") and
                                            f"_{stage_name}_" in item["label"])
            pre_cb = [phase_bundle(junction, signal) for signal in sorted(pre_cb_jj_signals)]
            t1_jjs = {f"B_J{jj}": phase_bundle(junction, f"P(B_J{jj}|XT1_D{d})")
                      for jj in (1, 2, 9, 10, 11)}
            t1_missing = [jj for jj, metrics_value in t1_jjs.items()
                          if metrics_value["status"] == "UNKNOWN_MISSING_PROBE"]
            stage_current_signals = set(input_currents + carry_current_names)
            stage_current_signals.update(item["label"] for item in probe_manifest["signals"]
                                         if item["label"].startswith((f"I(R_S_D{d})", f"I(R_C_D{d})")))
            stage_current_records = {signal: current_bundle(current, signal) for signal in sorted(stage_current_signals)}
            stage_rows.append({
                "run_id": run_id, "case": case_name, "A_decimal": a, "B_decimal": b,
                "ROW_BITS": expected_rows, "COL_BITS": expected_cols, "stage": stage_name,
                "theoretical_active_cell_count": derived_counts[stage_name],
                "array_last_cb_instance": array_cb,
                "array_last_cb_bj1_metrics_json": json_cell(array_cb_jjs["BJ1"]),
                "array_last_cb_bj2_metrics_json": json_cell(array_cb_jjs["BJ2"]),
                "pre_cb_sjtl_jj_metrics_json": json_cell(pre_cb if pre_cb else {"status": "NOT_APPLICABLE_D0"}),
                "carry_cb_bj1_metrics_json": json_cell(carry_cb_jjs.get("BJ1", carry_cb_jjs)),
                "carry_cb_bj2_metrics_json": json_cell(carry_cb_jjs.get("BJ2", carry_cb_jjs)),
                "t1_input_bj1_metrics_json": json_cell(t1_jjs["B_J1"]),
                "t1_carry_path_bj11_metrics_json": json_cell(t1_jjs["B_J11"]),
                "t1_other_internal_jj_metrics_json": json_cell({jj: t1_jjs[jj] for jj in ("B_J2", "B_J9", "B_J10")}),
                "t1_internal_missing_probe_names": json_cell(t1_missing),
                "sum_voltage_area_phi0_by_window_json": json_cell(output_areas[f"S{d}"]),
                "carry_voltage_area_phi0_by_window_json": json_cell(
                    {w: wave_bundle(wave, f"V(C_D{d})")["windows"][w].get("signed_area_phi0_arithmetic")
                     for w in ("ARRAY_FINAL_READ", "PRE_CLOCK", "CLOCK_EDGE", "POST_CLOCK", "TOTAL")}),
                "current_metrics_by_signal_json": json_cell(stage_current_records),
                "stage_timing_descriptor_json": json_cell(timing_by_stage.get(stage_name, {"status": "UNKNOWN"})),
                "raw_sha256": result["raw_sha256"],
                "evidence_path": f"runs/{run_id}/raw.csv",
                "interpretation_boundary": "DERIVED_ARITHMETIC_ONLY; descriptive lobe timing is not event count",
            })

        analysis_records.append({
            "run_id": run_id, "case": case_name, "group_id": pair_group,
            "A_decimal": a, "B_decimal": b, "ROW_BITS": expected_rows, "COL_BITS": expected_cols,
            "theoretical_product_decimal": theoretical_product,
            "theoretical_output_bits_lsb_first": expected_bits,
            "configured_clock_time_ps": float(case["T1_CHAIN_CLK_START"].removesuffix("p")),
            "carry_sjtl_count_by_stage": case["CARRY_SJTL_COUNT_BY_STAGE"],
            "raw_sha256": result["raw_sha256"], "raw_bytes": (run_dir / "raw.csv").stat().st_size,
            "deck_sha256": deck_sha, "stimulus_sha256": result["stimulus_sha256"],
            "qa_status": qa["status"], "artifact_status": result["artifact_status"],
            "raw_sample_count": raw_qa["sample_count"],
            "dt_min_ps": raw_qa["dt_min_s"] * 1e12, "dt_max_ps": raw_qa["dt_max_s"] * 1e12,
            "raw_time_start_ps": raw_qa["time_start_s"] * 1e12,
            "raw_time_end_ps": raw_qa["time_end_s"] * 1e12,
            "uniform_time_grid": raw_qa["uniform_time_grid"],
            "physical_solve_count": result["physical_solve_count"],
            "solver_exit_code": result["solver_exit_code"],
            "output_area_phi0_arithmetic": output_areas,
            "descriptive_binary_candidate": "UNKNOWN",
            "descriptive_decimal_candidate": "UNKNOWN",
            "candidate_status": "INDETERMINATE",
            "candidate_indeterminate_reason": "No product-bit decode threshold was preregistered; existing metrics state NOT_PERFORMED. No threshold inferred or tuned.",
            "preflight_stimulus_qa": stimulus_qa,
            "raw_qa_recomputed": raw_qa,
            "metrics_replay_check": metric_check,
            "existing_actual_product_bit_decoding": raw_metrics["actual_product_bit_decoding"],
            "raw_qa_status": raw_qa_existing["status"],
            "static_qa_status": static_qa["status"],
            "chain_qa_status": chain_qa["status"],
            "provenance_qa_status": qa.get("provenance_qa_status"),
            "stage_rows": stage_rows,
            "existing_plot_qa_page_count": plot_qa.get("page_count"),
            "existing_plot_pages_present": all((SERIES / page["path"]).is_file() for page in plot_qa.get("pages", [])),
            "independent_numerical_cross_check": independent_spot_check(run_id, raw_metrics)
            if run_id in {"A048_C4R28_210_15x14", "A073_C4R28_210_0x0"} else None,
            "plot_qa_status": plot_qa["status"],
            "solver_binary_sha256": metadata["solver"]["sha256"],
            "solver_version": metadata["solver"]["version"].splitlines()[-1],
            "source_sha256": metadata["source_sha256"],
            "provenance_path": f"runs/{run_id}/provenance.json",
            "metrics_status": raw_metrics["status"],
        })
        stage_rows_all.extend(stage_rows)
    return analysis_records, stage_rows_all


def independent_spot_check(run_id: str, metrics: dict[str, Any]) -> dict[str, Any]:
    """Recompute one same-JJ phase/area pair and two output areas with a separate CSV loop."""
    raw = RUNS / run_id / "raw.csv"
    target_phase = "P(B_J1|XT1_D0)"
    target_voltage = "V(B_J1|XT1_D0)"
    target_output = "V(DFF_O)"
    start, end = 215e-12, 300e-12
    selected_t: list[float] = []
    selected_p: list[float] = []
    selected_v: list[float] = []
    selected_dff: list[float] = []
    with raw.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.reader(stream)
        header = next(reader)
        indexes = {label: header.index(label) for label in (target_phase, target_voltage, target_output)}
        previous_raw = None
        previous_unwrapped = None
        for row in reader:
            t = float(row[0])
            p_raw = float(row[indexes[target_phase]])
            if previous_raw is None:
                p_unwrapped = p_raw
            else:
                delta = p_raw - previous_raw
                while delta > math.pi:
                    delta -= 2 * math.pi
                while delta < -math.pi:
                    delta += 2 * math.pi
                p_unwrapped = previous_unwrapped + delta
            previous_raw, previous_unwrapped = p_raw, p_unwrapped
            if start <= t < end:
                selected_t.append(t)
                selected_p.append(p_unwrapped)
                selected_v.append(float(row[indexes[target_voltage]]))
                selected_dff.append(float(row[indexes[target_output]]))
    if len(selected_t) < 2:
        raise ValueError(f"independent spot-check window too short for {run_id}")
    def trapz(values: list[float]) -> float:
        return math.fsum((values[i] + values[i + 1]) * 0.5 *
                         (selected_t[i + 1] - selected_t[i]) for i in range(len(selected_t) - 1))
    phase_turns = (selected_p[-1] - selected_p[0]) / (2 * math.pi)
    voltage_phi0 = trapz(selected_v) / dp.PHI0
    dff_phi0 = trapz(selected_dff) / dp.PHI0
    phase_metric = next(item for item in metrics["same_jj_phase_voltage"]
                        if item["phase_signal"] == target_phase and item["window"] == "POST_CLOCK")
    dff_metric = next(item for item in metrics["waveforms"]
                      if item["signal"] == target_output and item["window"] == "POST_CLOCK")
    return {
        "run_id": run_id,
        "window_ps": [215, 300],
        "sample_count": len(selected_t),
        "phase_signal": target_phase,
        "phase_delta_rad_independent": selected_p[-1] - selected_p[0],
        "phase_delta_over_2pi_navigation_independent": phase_turns,
        "same_jj_voltage_area_phi0_independent": voltage_phi0,
        "same_jj_phase_area_difference_turns_independent": phase_turns - voltage_phi0,
        "platform_phase_delta_rad": phase_metric["phase_delta_rad"],
        "platform_same_jj_voltage_area_phi0": phase_metric["voltage_area_phi0_arithmetic"],
        "phase_delta_abs_difference_rad_vs_platform":
            abs(phase_metric["phase_delta_rad"] - (selected_p[-1] - selected_p[0])),
        "same_jj_area_abs_difference_phi0_vs_platform":
            abs(phase_metric["voltage_area_phi0_arithmetic"] - voltage_phi0),
        "dff_output_voltage_area_phi0_independent": dff_phi0,
        "platform_dff_output_voltage_area_phi0": dff_metric["signed_area_phi0_arithmetic"],
        "dff_area_abs_difference_phi0_vs_platform": abs(dff_metric["signed_area_phi0_arithmetic"] - dff_phi0),
        "interpolation_or_resampling": False,
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"refusing to write empty table: {path}")
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_plots(records: list[dict[str, Any]], stage_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    if PLOTS_DIR.exists() and any(PLOTS_DIR.iterdir()):
        raise FileExistsError(f"refusing to overwrite existing plot output: {PLOTS_DIR}")
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    labels = [f"{r['A_decimal']}×{r['B_decimal']}\n{r['run_id'][:4]}" for r in records]
    stage_index = {(r["run_id"], r["stage"]): r for r in stage_rows}
    produced = []

    def save(fig: Any, name: str, description: str) -> None:
        path = PLOTS_DIR / name
        fig.savefig(path, dpi=170, bbox_inches="tight")
        plt.close(fig)
        produced.append({"path": str(path.relative_to(SERIES)), "sha256": sha256(path),
                         "bytes": path.stat().st_size, "description": description,
                         "source": "derived arithmetic from immutable raw; not a bit/event classifier"})

    # Continuous output area comparison: no threshold or bit rounding is applied.
    output_keys = [*(f"S{d}" for d in range(7)), "DFF_O"]
    output_labels = [*(f"S{d}" for d in range(7)), "DFF.O"]
    output_matrix = np.array([[r["output_area_phi0_arithmetic"][key]["POST_CLOCK"]
                               for key in output_keys] for r in records], dtype=float)
    limit = float(np.nanmax(np.abs(output_matrix))) or 1.0
    fig, ax = plt.subplots(figsize=(15, 10))
    image = ax.imshow(output_matrix, aspect="auto", interpolation="nearest", cmap="coolwarm",
                      vmin=-limit, vmax=limit)
    ax.set_xticks(range(len(output_labels)), output_labels)
    ax.set_yticks(range(len(labels)), labels, fontsize=6)
    ax.set_title("C4R28_210 post-clock signed output area (arithmetic only)")
    ax.set_xlabel("Output signal")
    ax.set_ylabel("Input pair / run")
    fig.colorbar(image, ax=ax, label="signed V·s / Φ0 (not bit/event count)")
    save(fig, "01_output_area_post_clock.png", "28×8 signed post-clock output voltage-area matrix")

    # T1 input JJ phase navigation, from the same registered PRE_CLOCK window.
    phase_matrix = []
    for record in records:
        row = []
        for d in range(7):
            try:
                bundle = json.loads(stage_index[(record["run_id"], f"D{d}")]["t1_input_bj1_metrics_json"])
                row.append(bundle["windows"]["PRE_CLOCK"]["phase_delta_over_2pi_navigation"])
            except (KeyError, TypeError):
                row.append(float("nan"))
        phase_matrix.append(row)
    phase_matrix = np.array(phase_matrix, dtype=float)
    lim = float(np.nanmax(np.abs(phase_matrix))) or 1.0
    fig, ax = plt.subplots(figsize=(14, 10))
    image = ax.imshow(phase_matrix, aspect="auto", interpolation="nearest", cmap="coolwarm",
                      vmin=-lim, vmax=lim)
    ax.set_xticks(range(7), [f"D{d}" for d in range(7)])
    ax.set_yticks(range(len(labels)), labels, fontsize=6)
    ax.set_title("T1 input B_J1 PRE_CLOCK net phase change (navigation only)")
    ax.set_xlabel("T1 stage")
    ax.set_ylabel("Input pair / run")
    fig.colorbar(image, ax=ax, label="Δphase / 2π (navigation; not event count)")
    save(fig, "02_t1_input_bj1_pre_clock.png", "T1 input B_J1 PRE_CLOCK net phase-navigation matrix")

    # Carry-CB BJ1 arithmetic by stage; D0 has no carry-CB.
    carry_matrix = []
    for record in records:
        row = []
        for d in range(1, 7):
            value = stage_index[(record["run_id"], f"D{d}")]["carry_cb_bj1_metrics_json"]
            try:
                row.append(json.loads(value)["windows"]["PRE_CLOCK"]["phase_delta_over_2pi_navigation"])
            except (KeyError, TypeError):
                row.append(float("nan"))
        carry_matrix.append(row)
    carry_matrix = np.array(carry_matrix, dtype=float)
    lim = float(np.nanmax(np.abs(carry_matrix))) or 1.0
    fig, ax = plt.subplots(figsize=(14, 10))
    image = ax.imshow(carry_matrix, aspect="auto", interpolation="nearest", cmap="coolwarm",
                      vmin=-lim, vmax=lim)
    ax.set_xticks(range(6), [f"D{d}" for d in range(1, 7)])
    ax.set_yticks(range(len(labels)), labels, fontsize=6)
    ax.set_title("Carry CB BJ1 PRE_CLOCK net phase change (navigation only)")
    ax.set_xlabel("Carry stage")
    ax.set_ylabel("Input pair / run")
    fig.colorbar(image, ax=ax, label="Δphase / 2π (navigation; not event count)")
    save(fig, "03_carry_cb_bj1_pre_clock.png", "Carry-CB BJ1 PRE_CLOCK net phase-navigation matrix")

    # Registered runner's descriptive lobe timing only; not event/arrival counts.
    margins = np.full((len(records), 7), np.nan)
    for i, record in enumerate(records):
        for d in range(7):
            timing = json.loads(stage_index[(record["run_id"], f"D{d}")]["stage_timing_descriptor_json"])
            margin = timing.get("candidate_time_to_clock_margin_ps")
            if margin is not None:
                margins[i, d] = margin
    finite = margins[np.isfinite(margins)]
    lim = float(np.max(np.abs(finite))) if finite.size else 1.0
    fig, ax = plt.subplots(figsize=(15, 10))
    image = ax.imshow(margins, aspect="auto", interpolation="nearest", cmap="coolwarm",
                      vmin=-lim, vmax=lim)
    ax.set_xticks(range(7), [f"D{d}" for d in range(7)])
    ax.set_yticks(range(len(labels)), labels, fontsize=6)
    ax.set_title("Configured 210 ps clock minus last descriptive lobe candidate")
    ax.set_xlabel("Stage")
    ax.set_ylabel("Input pair / run")
    fig.colorbar(image, ax=ax, label="candidate-time margin (ps); navigation only")
    save(fig, "04_descriptive_lobe_clock_margin.png", "Descriptive lobe-candidate time margin to configured clock")

    group_ids = [group for group, _ in CATEGORIES]
    counts = [sum(r["group_id"] == group for r in records) for group in group_ids]
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.bar(group_ids, counts, color="#7089a6")
    ax.set_ylim(0, max(counts) + 1)
    ax.set_ylabel("Cases")
    ax.set_title("Input matrix coverage by task-listed input group")
    for i, count in enumerate(counts):
        ax.text(i, count + 0.1, f"{count} / {count} INDETERMINATE", ha="center", fontsize=7)
    save(fig, "05_input_group_candidate_status.png", "Case counts by listed input group; candidate status is all indeterminate")

    # Candidate-decoding status is shown separately from physical output areas.
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(["CANDIDATE_MATCH", "CANDIDATE_MISMATCH", "INDETERMINATE"], [0, 0, len(records)],
           color=["#5b8", "#c66", "#c9a227"])
    ax.set_ylim(0, len(records) + 3)
    ax.set_ylabel("Cases")
    ax.set_title("Product-bit classification availability")
    ax.text(2, len(records) + 0.5, "No decode threshold preregistered", ha="center", fontsize=8)
    save(fig, "06_candidate_decode_status.png", "Classification availability; no product-bit threshold invented")
    return produced


def write_summary(records: list[dict[str, Any]], stage_rows: list[dict[str, Any]],
                  qa: dict[str, Any], figures: list[dict[str, Any]]) -> None:
    category_counts = {group: sum(r["group_id"] == group for r in records) for group, _ in CATEGORIES}
    lines = [
        "# CARRY4 functional 28 — mechanical raw summary",
        "",
        "Status: `MECHANICAL_ANALYSIS_COMPLETE / AWAITING_SCIENTIFIC_REVIEW`.",
        "",
        "No JoSIM solver was invoked by this analysis (physical solve count for this work unit: 0). "
        "All reported phase/voltage values were recomputed from each immutable raw.csv using actual stored timestamps.",
        "",
        "## Classification boundary",
        "",
        "All 28 rows are `INDETERMINATE` for product-bit matching. The bound run metrics explicitly state "
        "`actual_product_bit_decoding = NOT_PERFORMED; no decode threshold preregistered`. This analysis does not "
        "invent a threshold or round signed voltage-area/Φ0 values to bits. Thus this is not a report of 0 matches "
        "or 28 physical failures; candidate match and mismatch counts are both zero, and 28 are undecoded.",
        "",
        "The raw-derived output areas and same-JJ phase/area arithmetic are presented as measurements/arithmetic, "
        "not as SFQ counts, bit values, or a scientific functional verdict. For T1 stages D0/D1/D4/D5/D6, the "
        "stored focus probe set lacks B_J2/B_J9/B_J10; those internal values remain `UNKNOWN`. B_J1 and B_J11 "
        "P/V and S/C output waveforms are present. D2/D3 have the broader internal T1 P/V set.",
        "",
        "## Coverage and QA",
        "",
        f"- Unique input pairs/runs: {len(records)}/{len(records)}.",
        f"- Artifact+mechanical QA: {qa['artifact_qa_pass_count']}/{len(records)} PASS.",
        f"- Raw/static/chain/plot/provenance QA: {qa['raw_qa_pass_count']}/{qa['static_qa_pass_count']}/{qa['chain_qa_pass_count']}/{qa['plot_qa_pass_count']}/{qa['provenance_qa_pass_count']} PASS, each of {len(records)}.",
        f"- Effective circuit deck SHA equals A045: {qa['deck_sha_match_anchor_count']}/{len(records)}.",
        f"- Exact PWL input mapping checks: {qa['stimulus_pwl_check_pass_count']}/{len(records)} PASS.",
        f"- Raw-recomputed metrics match stored same-version mechanical metrics: {qa['raw_metric_replay_match_count']}/{len(records)}.",
        f"- Independent raw arithmetic spot checks: {len(qa['independent_numerical_cross_checks'])} run(s); maximum absolute same-JJ area difference versus platform arithmetic: {qa['independent_cross_check_max_abs_area_diff_phi0']:.3g} Φ₀ arithmetic.",
        f"- Candidate statuses: 0 `CANDIDATE_MATCH`, 0 `CANDIDATE_MISMATCH`, {len(records)} `INDETERMINATE`.",
        f"- Existing experiment manifest remains at observed solve count {qa['observed_experiment_manifest_physical_solve_count']} with registered maximum {qa['registered_experiment_maximum_physical_solve_count']}; this analysis added no authorization record.",
        f"- Duplicate raw-content hashes: {len(qa['duplicate_raw_sha256_groups'])} group(s); distinct case/run evidence was preserved.",
        f"- Manual wrapper run logs empty: {qa['empty_manual_wrapper_run_log_count']} of 28; each run still has its own solver stdout/stderr/run.log artifacts.",
        "- All generated HTML remains local and is excluded from the DELTA archive.",
        "",
        "## Input, encoding and candidate results",
        "",
        "ROW encoding: R1 is bit 0 / least-significant bit. COL encoding: C1 is the highest-valued / leftmost bit. "
        "Expected output bits below are theoretical LSB-first 8-bit products only.",
        "",
        "| Run | A×B | ROW_BITS | COL_BITS | Theoretical product | Theoretical bits LSB→MSB | Candidate status |",
        "|---|---:|---|---|---:|---|---|",
    ]
    for item in records:
        lines.append(f"| {item['run_id']} | {item['A_decimal']}×{item['B_decimal']} | {item['ROW_BITS']} | "
                     f"{item['COL_BITS']} | {item['theoretical_product_decimal']} | "
                     f"{item['theoretical_output_bits_lsb_first']} | {item['candidate_status']} |")
    lines.extend(["", "## Task-listed input group counts", "",
                  "| Group | Cases | Candidate status |", "|---|---:|---|"])
    for group, pairs in CATEGORIES:
        lines.append(f"| {group} (`{', '.join(f'{a}×{b}' for a,b in pairs)}`) | "
                     f"{category_counts[group]} | INDETERMINATE for each case |")
    lines.extend(["", "## Raw-derived output-area and stage tables", "",
                  "`FUNCTIONAL_28_CASES.csv` contains S0–S6 and DFF.O signed V·s/Φ0 arithmetic in "
                  "ARRAY_FINAL_READ, PRE_CLOCK, CLOCK_EDGE, POST_CLOCK, and TOTAL windows. "
                  "`FUNCTIONAL_28_STAGE_DETAILS.csv` contains 196 case×D0…D6 records including array last-CB, "
                  "configured pre-CB sJTL, Carry-CB, T1 input/carry-path JJ P/V arithmetic, branch currents, "
                  "S/C areas, and descriptive lobe timing. These tables preserve rad, turns-navigation, and "
                  "same-JJ area values separately; they do not count events.",
                  "", "## First-anomaly classification", "",
                  "No case can be assigned a first abnormal physical stage from the current frozen metrics: "
                  "the product-bit decoder has no preregistered decision threshold, and no post-hoc threshold was added. "
                  "`FUNCTIONAL_28_ANOMALIES.csv` therefore lists each undecoded case with first supported anomaly "
                  "stage `UNKNOWN`, rather than infer a stage from area rounding or a local phase excursion.",
                  "", "## Figures", ""])
    for figure in figures:
        lines.append(f"- `{figure['path']}` — {figure['description']}.")
    lines.extend(["", "The per-run classic full-chain overview and subsystem pages generated at run time remain available "
                  "under `plots/runs/<run_id>/`; this summary does not duplicate the 28×11 HTML pages.",
                  "", "## Evidence and interpretation boundary", "",
                  "A073 (0×0) and A074 (0×15) have identical raw SHA-256 content; both distinct run directories, "
                  "configuration snapshots, and run identities are preserved. Identical file hashes are not treated "
                  "as a missing run. The original experiment maximum 41 / observed manifest count 75 discrepancy is "
                  "not modified by this analysis. A045–A047 are read-only anchors and their raw is not recopied.",
                  "", "Scientific interpretation: `NOT_PERFORMED`. No physical mechanism, successful multiplication, "
                  "or functional gate is claimed.", ""])
    (ANALYSIS_DIR / "FUNCTIONAL_28_SUMMARY.md").write_text("\n".join(lines), encoding="utf-8")


def write_outputs(records: list[dict[str, Any]], stage_rows: list[dict[str, Any]],
                  meta: dict[str, Any]) -> dict[str, Any]:
    outputs = ["FUNCTIONAL_28_CASES.csv", "FUNCTIONAL_28_STAGE_DETAILS.csv",
               "FUNCTIONAL_28_ANOMALIES.csv", "FUNCTIONAL_28_SUMMARY.md",
               "EVIDENCE_MANIFEST.json", "SUMMARY_QA.json", "VISUALIZATION_QA.json"]
    existing = [str(ANALYSIS_DIR / name) for name in outputs if (ANALYSIS_DIR / name).exists()]
    if existing:
        raise FileExistsError("refusing to overwrite prior analysis outputs: " + ", ".join(existing))
    if PLOTS_DIR.exists() and any(PLOTS_DIR.iterdir()):
        raise FileExistsError(f"refusing to overwrite existing local plot output: {PLOTS_DIR}")

    case_rows: list[dict[str, Any]] = []
    for item in records:
        row = {k: v for k, v in item.items() if k not in {
            "output_area_phi0_arithmetic", "preflight_stimulus_qa", "raw_qa_recomputed",
            "metrics_replay_check", "existing_actual_product_bit_decoding", "stage_rows",
            "independent_numerical_cross_check",
            "existing_plot_qa_page_count", "existing_plot_pages_present", "solver_binary_sha256",
            "solver_version", "source_sha256", "provenance_path", "metrics_status",
        }}
        for signal, windows in item["output_area_phi0_arithmetic"].items():
            for window in ("ARRAY_FINAL_READ", "PRE_CLOCK", "CLOCK_EDGE", "POST_CLOCK", "TOTAL"):
                row[f"{signal}_{window}_SIGNED_AREA_PHI0_ARITHMETIC"] = windows.get(window)
        row["candidate_indeterminate_reason"] = item["candidate_indeterminate_reason"]
        case_rows.append(row)
    write_csv(ANALYSIS_DIR / "FUNCTIONAL_28_CASES.csv", case_rows)
    stage_fields = list(stage_rows[0])
    write_csv(ANALYSIS_DIR / "FUNCTIONAL_28_STAGE_DETAILS.csv", stage_rows)

    anomaly_rows = []
    for item in records:
        anomaly_rows.append({
            "run_id": item["run_id"], "input": f"{item['A_decimal']}x{item['B_decimal']}",
            "theoretical_product": item["theoretical_product_decimal"],
            "descriptive_candidate": "UNKNOWN", "candidate_status": "INDETERMINATE",
            "differing_output_bits": "UNKNOWN_NO_DECODE_RULE",
            "first_supported_anomaly_level": "UNKNOWN",
            "evidence_limit": item["candidate_indeterminate_reason"],
            "output_area_phi0_arithmetic_json": json_cell(item["output_area_phi0_arithmetic"]),
            "raw_sha256": item["raw_sha256"],
            "scientific_review_needed_for_bit_claim": True,
        })
    write_csv(ANALYSIS_DIR / "FUNCTIONAL_28_ANOMALIES.csv", anomaly_rows)

    figures = write_plots(records, stage_rows)
    (ANALYSIS_DIR / "VISUALIZATION_QA.json").write_text(
        json.dumps({"schema": "carry4-functional-28-visualization-qa-v1", "status": "PASS",
                    "plot_style": "compact static derived-metric figures; existing run-level classic josim-plot2 pages retained",
                    "html_included": False, "figures": figures,
                    "raw_csv_sha256_unchanged": True,
                    "scientific_interpretation_performed": False}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    write_summary(records, stage_rows, meta["summary_qa"], figures)

    evidence = {
        "schema": "carry4-functional-28-evidence-manifest-v1",
        "analysis_id": "CARRY4_FUNCTIONAL_28_20261010",
        "parent_head": PARENT_HEAD,
        "analysis_script_sha256": sha256(Path(__file__).resolve()),
        "analysis_scope_sha256": sha256(ANALYSIS_DIR / "ANALYSIS_SCOPE.json"),
        "preflight_sha256": sha256(ANALYSIS_DIR / "PREFLIGHT.md"),
        "platform_analysis_source": "scripts/diagonal_platform.py:analyze_t1_chain_raw",
        "platform_analysis_source_sha256": sha256(SERIES / "scripts" / "diagonal_platform.py"),
        "physical_solver_invocations": 0,
        "existing_physical_run_count": 28,
        "scientific_interpretation_performed": False,
        "metric_semantics": {
            "phase_raw_unit": "rad",
            "phase_turns": "per-run unwrapped Δphase/(2π), navigation only",
            "voltage_area": "signed trapezoid integral using actual stored timestamps / Phi0 arithmetic",
            "windows_ps_half_open": load_json(ANALYSIS_DIR / "ANALYSIS_SCOPE.json")["windows_ps_half_open"],
            "candidate_decode": "NOT_PERFORMED; no threshold preregistered; all cases INDETERMINATE",
            "event_classifier": None,
            "interpolation_or_resampling": False,
            "shared_dout_join_semantics": "DOUT/JOIN boundary voltage is not an array-only event count",
        },
        "input_encoding": load_json(ANALYSIS_DIR / "ANALYSIS_SCOPE.json")["input_encoding"],
        "run_records": [{k: r[k] for k in ("run_id", "case", "A_decimal", "B_decimal", "ROW_BITS", "COL_BITS",
                                            "theoretical_product_decimal", "theoretical_output_bits_lsb_first",
                                            "raw_sha256", "raw_bytes", "deck_sha256", "stimulus_sha256",
                                            "raw_sample_count", "dt_min_ps", "dt_max_ps", "uniform_time_grid",
                                            "physical_solve_count", "solver_exit_code", "qa_status", "artifact_status",
                                            "solver_binary_sha256", "solver_version", "source_sha256")}
                        for r in records],
        "reference_anchors": [
            {"run_id": anchor, "raw_sha256": load_json(RUNS / anchor / "result.json")["raw_sha256"],
             "raw_path": f"runs/{anchor}/raw.csv", "included_again": False}
            for anchor in ("A045_MANUAL_CARRY4_15x15_210", "A046_MANUAL_CARRY4_11x13_210",
                           "A047_MANUAL_CARRY4_3x3_210")],
        "duplicate_raw_hash_groups": meta["summary_qa"]["duplicate_raw_sha256_groups"],
        "manual_batch_wrapper_run_log_empty_count": meta["summary_qa"]["empty_manual_wrapper_run_log_count"],
        "independent_numerical_cross_checks": [r["independent_numerical_cross_check"] for r in records
                                                if r.get("independent_numerical_cross_check")],
        "output_files": [],
    }
    for name in outputs:
        path = ANALYSIS_DIR / name
        if path.is_file():
            evidence["output_files"].append({"path": str(path.relative_to(SERIES)), "sha256": sha256(path),
                                             "bytes": path.stat().st_size})
    evidence["output_files"].extend({"path": item["path"], "sha256": item["sha256"], "bytes": item["bytes"]}
                                    for item in figures)
    evidence_path = ANALYSIS_DIR / "EVIDENCE_MANIFEST.json"
    evidence_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    qa = dict(meta["summary_qa"])
    qa.update({"schema": "carry4-functional-28-summary-qa-v1",
               "status": "PASS_WITH_INDETERMINATE_CANDIDATE_DECODING",
               "physical_solver_invocations": 0,
               "candidate_decode_status": "NOT_PERFORMED_NO_PREREGISTERED_THRESHOLD",
               "candidate_match_count": 0, "candidate_mismatch_count": 0,
               "candidate_indeterminate_count": len(records),
               "case_csv_row_count": len(case_rows), "stage_csv_row_count": len(stage_rows),
               "anomaly_csv_row_count": len(anomaly_rows),
               "visualization_qa_sha256": sha256(ANALYSIS_DIR / "VISUALIZATION_QA.json"),
               "evidence_manifest_sha256": sha256(evidence_path),
               "analysis_file_sha256": {
                   name: sha256(ANALYSIS_DIR / name) for name in outputs
                   if (ANALYSIS_DIR / name).is_file() and name != "SUMMARY_QA.json"
               },
               "figure_sha256": {item["path"]: item["sha256"] for item in figures},
               "html_included": False})
    (ANALYSIS_DIR / "SUMMARY_QA.json").write_text(json.dumps(qa, ensure_ascii=False, indent=2) + "\n",
                                                    encoding="utf-8")
    return qa


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only C4R28 raw reanalysis; never invokes JoSIM")
    parser.add_argument("--limit", type=int, default=None,
                        help="analysis smoke-check limit; do not use for final artifact generation")
    parser.add_argument("--check-only", action="store_true", help="read raw and validate, write no result files")
    args = parser.parse_args()
    records, stage_rows = collect_runs(args.limit)
    if args.check_only:
        print(json.dumps({"status": "READ_ONLY_RAW_CHECK_PASS", "cases_checked": len(records),
                          "stages_checked": len(stage_rows), "solver_invocations": 0,
                          "raw_sha256": {item["run_id"]: item["raw_sha256"] for item in records},
                          "metric_replay_exact_match": all(item["metrics_replay_check"]["exact_metric_replay_match"]
                                                             for item in records)},
                         ensure_ascii=False, indent=2))
        return 0
    if args.limit is not None:
        raise ValueError("--limit is only valid with --check-only")
    summary_qa = {
        "case_count": len(records), "distinct_input_pair_count": len({(r["A_decimal"], r["B_decimal"]) for r in records}),
        "distinct_run_id_count": len({r["run_id"] for r in records}),
        "registered_experiment_maximum_physical_solve_count": 41,
        "observed_experiment_manifest_physical_solve_count": load_json(MANIFEST_PATH)["physical_solve_count"],
        "new_batch_added_to_authorization_manifest": False,
        "artifact_qa_pass_count": sum(r["qa_status"] == "PASS" and r["artifact_status"] == "VALID" for r in records),
        "raw_qa_pass_count": sum(r["raw_qa_status"] == "PASS" for r in records),
        "static_qa_pass_count": sum(r["static_qa_status"] == "PASS" for r in records),
        "chain_qa_pass_count": sum(r["chain_qa_status"] == "PASS" for r in records),
        "plot_qa_pass_count": sum(r["plot_qa_status"] == "PASS" for r in records),
        "provenance_qa_pass_count": sum(r["provenance_qa_status"] == "PASS" for r in records),
        "deck_sha_match_anchor_count": sum(r["deck_sha256"] == records[0]["deck_sha256"] for r in records),
        "stimulus_pwl_check_pass_count": sum(r["preflight_stimulus_qa"]["status"] == "PASS" for r in records),
        "raw_metric_replay_match_count": sum(r["metrics_replay_check"]["exact_metric_replay_match"] for r in records),
        "raw_duplicate_groups": [], "duplicate_raw_sha256_groups": [],
        "empty_manual_wrapper_run_log_count": sum(
            (MANUAL_DIR / f"run_C4R28_210_{r['A_decimal']}x{r['B_decimal']}.log").stat().st_size == 0
            for r in records),
    }
    by_sha: dict[str, list[str]] = defaultdict(list)
    for record in records:
        by_sha[record["raw_sha256"]].append(record["run_id"])
    summary_qa["duplicate_raw_sha256_groups"] = [
        {"raw_sha256": digest, "run_ids": run_ids}
        for digest, run_ids in sorted(by_sha.items()) if len(run_ids) > 1]
    summary_qa["raw_sha_unique_count"] = len(by_sha)
    summary_qa["all_candidate_decodes_indeterminate"] = all(r["candidate_status"] == "INDETERMINATE" for r in records)
    independent_checks = [r["independent_numerical_cross_check"] for r in records
                          if r.get("independent_numerical_cross_check")]
    area_diffs = [item["same_jj_area_abs_difference_phi0_vs_platform"] for item in independent_checks]
    summary_qa["independent_numerical_cross_checks"] = independent_checks
    summary_qa["independent_cross_check_max_abs_area_diff_phi0"] = max(area_diffs, default=0.0)
    qa = write_outputs(records, stage_rows, {"summary_qa": summary_qa})
    print(json.dumps({"status": qa["status"], "cases": qa["case_count"],
                      "stages": qa["stage_csv_row_count"], "solver_invocations": 0,
                      "candidate_counts": {"match": 0, "mismatch": 0, "indeterminate": len(records)},
                      "analysis_dir": str(ANALYSIS_DIR), "plot_dir": str(PLOTS_DIR)},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
