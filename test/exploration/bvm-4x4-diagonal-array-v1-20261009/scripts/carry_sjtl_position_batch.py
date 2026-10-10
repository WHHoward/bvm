#!/usr/bin/env python3
"""Preflight and execute exactly the registered A034-A039 carry-sJTL batch."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import diagonal_platform as platform

SERIES = platform.SERIES
REPO = platform.REPO
RUNS = platform.RUNS
TASK = platform.CARRY_SJTL_POSITION_ANALYSIS
PREFLIGHT_DIR = TASK / "attempts" / "003"
PREFLIGHT = PREFLIGHT_DIR / "PREFLIGHT.md"
STATIC_QA = PREFLIGHT_DIR / "STATIC_QA.json"
WORK_UNIT = PREFLIGHT_DIR / "WORK_UNIT.json"
METRIC_SPEC = PREFLIGHT_DIR / "METRIC_SPEC.json"
PROBE_MANIFEST = PREFLIGHT_DIR / "PROBE_MANIFEST.json"
BATCH_MANIFEST = PREFLIGHT_DIR / "BATCH_MANIFEST.json"
REVISION_NOTE = PREFLIGHT_DIR / "REVISION_NOTE.md"
EXPERIMENT_MANIFEST = platform.EXPERIMENT_MANIFEST
BASE_HEAD = "9db7929608bf25fd8c2f86fb99e84b9a4387ba81"
STATIC_SUBCKTS = ("THmitll_MERGE", "THmitll_DFF", "D0_JTL", "T1", "BVM", "BQ", "sJTL", "CB")
BASELINE_RAW = {
    "A027_FULL_CB_CHAIN_ALL_CLOCK": "939e6024928be84df809532ecd8b716b815a9b96ea498324fc5c30b712100e46",
    "A028_FULL_CB_CHAIN_PAPER_CLOCK": "59ba22b2c31bd04993989c16a7c37d1e5bb904c078ef9db979657de81e604701",
    "A029_FULL_CB_CHAIN_3X3_CLOCK": "d943765ab3e47c1607ab3c29ff08a1088f2444dfd8a3266e9670a1d75d24ac0f",
    "A030_CARRY_POST_CB_SJTL_ALL_200": "027bb32757c1b426b2876ad2d694b6560cea58e6d54a733fd821408538ae166b",
    "A031_CARRY_POST_CB_SJTL_ALL_210": "c796e9b13024720fc1f5e3268e4174b4064343ab83a57bed3967ac4ed2c3dddf",
    "A032_CARRY_POST_CB_SJTL_PAPER_210": "439e9444964adf59043d11b39808c33fcd4f29d63d45835af4fa8cb5333546b5",
    "A033_CARRY_POST_CB_SJTL_3X3_210": "d4ed238cf7f7b113bb2e32c94b904d027ad5cf2c443502ae5183f3c4d3b1383c",
}


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def jread(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def jwrite_new(path: Path, value: Any) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite preflight artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    content = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    path.write_text(content if content.endswith("\n") else content + "\n", encoding="utf-8")


def _assert_json_object_keys(value: Any, path: str = "root") -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            if not isinstance(key, (str, int, float, bool, type(None))):
                raise TypeError(f"non-JSON object key at {path}: {key!r} ({type(key).__name__})")
            _assert_json_object_keys(nested, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, nested in enumerate(value):
            _assert_json_object_keys(nested, f"{path}[{index}]")


def git(*args: str, check: bool = True) -> str:
    proc = subprocess.run(["git", *args], cwd=REPO, text=True, capture_output=True, check=check)
    return proc.stdout.strip()


def _case_record(run_id: str) -> dict[str, Any]:
    return jread(RUNS / run_id / "case_manifest.json")


def _verify_base_runs() -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for run_id, expected_sha in BASELINE_RAW.items():
        run_dir = RUNS / run_id
        raw = run_dir / "raw.csv"
        result, qa, chain_qa = (jread(run_dir / name) for name in ("result.json", "qa.json", "chain_qa.json"))
        actual_sha = sha(raw)
        if (actual_sha != expected_sha or result.get("raw_sha256") != actual_sha or
                result.get("artifact_status") != "VALID" or qa.get("status") != "PASS" or
                chain_qa.get("status") != "PASS" or chain_qa.get("raw_sha256_after_analysis") != actual_sha):
            raise RuntimeError(f"baseline raw/QA identity mismatch; preserving and stopping: {run_id}")
        records[run_id] = {"raw_path": raw.relative_to(SERIES).as_posix(), "raw_sha256": actual_sha,
                           "raw_bytes": raw.stat().st_size, "physical_solve_count": 0}
    return records


def _baseline_case(run_id: str) -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
    saved = _case_record(run_id)
    case = dict(saved["case"])
    case.setdefault("CARRY_POST_CB_SJTL_COUNT", "0")
    case.setdefault("CARRY_SJTL_POSITION", "POST_CB")
    case.setdefault("CARRY_SJTL_STAGE_MASK", "000000")
    stimulus = saved["stimulus"]
    param_values: dict[str, str] = {}
    for filename in ("T1_PARAMS.snapshot.env", "CBU_PARAMS.snapshot.env", "DFF_PARAMS.snapshot.env",
                     "D0_JTL_PARAMS.snapshot.env"):
        param_values.update(platform.parse_env(RUNS / run_id / filename))
    return case, stimulus, param_values


def _differences(actual: dict[str, str], baseline: dict[str, str], allowed: set[str]) -> list[str]:
    return sorted(key for key in set(actual) | set(baseline)
                  if actual.get(key) != baseline.get(key) and key not in allowed)


def _static_syntax_check(rendered: dict[str, Any], run_id: str) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix=f".carry-sjtl-{run_id}-", dir=RUNS) as temp_name:
        temp = Path(temp_name)
        (temp / "deck.cir").write_text(rendered["deck"], encoding="utf-8")
        (temp / "stimulus.inc").write_text(rendered["stimulus_text"], encoding="utf-8")
        t1_source = temp / "sources" / "t1_cell_tunable.cir"
        t1_source.parent.mkdir(parents=True, exist_ok=True)
        t1_source.write_text(rendered["t1_source_text"], encoding="utf-8")
        for relative, source_text in rendered["chain_source_texts"].items():
            target = temp / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(source_text, encoding="utf-8")
        command = [str(platform.SOLVER)]
        for subckt in STATIC_SUBCKTS:
            command.extend(("-s", subckt))
        command.append(str(temp / "deck.cir"))
        proc = subprocess.run(command, cwd=temp, capture_output=True, text=True, check=False)
        output = proc.stdout + proc.stderr
        if proc.returncode:
            raise RuntimeError(f"JoSIM static syntax check failed for {run_id}: {output[-2400:]}")
        lines = [line.strip() for line in output.splitlines() if line.strip()]
        return {"status": "PASS", "exit_code": proc.returncode,
                "stdout_stderr_sha256": hashlib.sha256(output.encode()).hexdigest(),
                "output_line_count": len(lines), "output_tail": lines[-8:]}


def _check_topology(run_id: str, case: dict[str, str], rendered: dict[str, Any],
                    position: str, mask: str) -> None:
    lines = set(rendered["deck"].splitlines())
    stages = {i for i, enabled in enumerate(mask, 1) if enabled == "1"}
    if case.get("CBU_CHAIN_TOPOLOGY") != "CB_CARRY_BUFFER_ALL" or case.get("CBU_OVERRIDE_D1") != "NONE":
        raise RuntimeError(f"CB-only carry-buffer chain fixed topology differs: {run_id}")
    if (case.get("CARRY_POST_CB_SJTL_COUNT") != "0" or case.get("CARRY_SJTL_POSITION") != position or
            case.get("CARRY_SJTL_STAGE_MASK") != mask):
        raise RuntimeError(f"effective Carry sJTL position/mask differs: {run_id}")
    if (case["OUTPUT_MODE"] != "DIAGONAL_T1_CHAIN" or case["T1_MODE"] != "CHAIN" or
            case["DT"] != "0.01p" or case["STOP"] != "300p" or
            case["PROBE_PROFILE"] != "t1_chain_focus" or case["SE_ENABLE_MASK"] != "ALL" or
            case["ROW_WL_WRITE_AMPLITUDE"] != "400u" or case["COL_BL_WRITE_AMPLITUDE"] != "400u" or
            case["ROW_WL_READ_AMPLITUDE"] != "400u" or case["COL_SE_READ_AMPLITUDE"] != "100u" or
            case["T1_CHAIN_CLOCK_MODE"] != "GLOBAL_ONESHOT"):
        raise RuntimeError(f"frozen physical settings differ: {run_id}")
    expected_population = {"1111": [1, 2, 3, 4, 3, 2, 1],
                           "1101": [1, 1, 1, 3, 1, 1, 1],
                           "1100": [1, 2, 1, 0, 0, 0, 0]}[case["ROW_BITS"]]
    actual_population = [sum(cell in platform._active_cells(case) for cell in cells)
                         for cells in platform.DIAGONALS.values()]
    if actual_population != expected_population:
        raise RuntimeError(f"registered diagonal population differs: {run_id}: {actual_population}")
    if tuple(tuple(platform._sjtl_counts(case, diag)) for diag in platform.DIAGONALS) != (
            (1,), (1, 1), (1, 2, 1), (1, 2, 2, 1), (1, 2, 1), (1, 1), (1,)):
        raise RuntimeError(f"array-internal sJTL count changed: {run_id}")
    if len([line for line in lines if line.startswith("XT1_D")]) != 7:
        raise RuntimeError(f"expected exactly seven T1 instances: {run_id}")
    if len([line for line in lines if line.startswith("XCB_CARRY_D")]) != 6:
        raise RuntimeError(f"expected six Carry CB_0928 instances: {run_id}")
    if len([line for line in lines if line.startswith("XSJTL_CARRY_D")]) != len(stages):
        raise RuntimeError(f"Carry sJTL instance count differs from mask: {run_id}")
    if len([line for line in lines if line.startswith("XCB_D")]) != 16:
        raise RuntimeError(f"array CB count changed: {run_id}")
    if any(line.startswith(("XCBU_D", "XJTL_CBU", "XSJTL_CBU", "R_TERM_D", "R_C_D")) for line in lines):
        raise RuntimeError(f"unexpected MERGE/array-output device or parallel Carry load: {run_id}")
    for index in range(1, 7):
        common = {f"V_CBU_A_D{index} DOUT_D{index} CBU_JOIN_D{index} 0",
                  f"V_T1_LINK_D{index} CBU_JOIN_D{index} T1_I_D{index} 0"}
        if index in stages and position == "PRE_CB":
            expected = common | {
                f"V_CARRY_IN_D{index} C_D{index-1} CARRY_SJTL_IN_D{index} 0",
                f"XSJTL_CARRY_D{index} CARRY_SJTL_IN_D{index} CARRY_SJTL_OUT_D{index} sJTL",
                f"V_CARRY_SJTL_OUT_D{index} CARRY_SJTL_OUT_D{index} CARRY_CB_IN_D{index} 0",
                f"XCB_CARRY_D{index} CARRY_CB_IN_D{index} CARRY_CB_OUT_D{index} CB",
                f"V_CBU_B_D{index} CARRY_CB_OUT_D{index} CBU_JOIN_D{index} 0",
            }
        elif index in stages:
            expected = common | {
                f"V_CARRY_IN_D{index} C_D{index-1} CARRY_CB_IN_D{index} 0",
                f"XCB_CARRY_D{index} CARRY_CB_IN_D{index} CARRY_CB_OUT_D{index} CB",
                f"V_CARRY_SJTL_IN_D{index} CARRY_CB_OUT_D{index} CARRY_SJTL_IN_D{index} 0",
                f"XSJTL_CARRY_D{index} CARRY_SJTL_IN_D{index} CARRY_SJTL_OUT_D{index} sJTL",
                f"V_CBU_B_D{index} CARRY_SJTL_OUT_D{index} CBU_JOIN_D{index} 0",
            }
        else:
            expected = common | {
                f"V_CARRY_IN_D{index} C_D{index-1} CARRY_CB_IN_D{index} 0",
                f"XCB_CARRY_D{index} CARRY_CB_IN_D{index} CARRY_CB_OUT_D{index} CB",
                f"V_CBU_B_D{index} CARRY_CB_OUT_D{index} CBU_JOIN_D{index} 0",
            }
        actual = {line for line in lines if line.startswith((f"V_CBU_A_D{index} ", f"V_CARRY_IN_D{index} ",
                                                              f"XSJTL_CARRY_D{index} ",
                                                              f"V_CARRY_SJTL_IN_D{index} ",
                                                              f"V_CARRY_SJTL_OUT_D{index} ",
                                                              f"XCB_CARRY_D{index} ", f"V_CBU_B_D{index} ",
                                                              f"V_T1_LINK_D{index} "))}
        if actual != expected:
            raise RuntimeError(f"carry branch wiring differs at D{index} in {run_id}: {actual ^ expected}")
        if sum(f"CBU_JOIN_D{index}" in line for line in lines
               if not line.startswith(("*", ".print"))) != 3:
            raise RuntimeError(f"JOIN must have exactly array, Carry and T1-link branches: {run_id}/D{index}")
    if rendered["static_qa"].get("status") != "PASS":
        raise RuntimeError(f"platform static QA failed: {run_id}")
    if rendered["static_qa"]["raw_estimate_bytes"] >= platform.MAX_RAW_BYTES:
        raise RuntimeError(f"raw storage estimate exceeds limit: {run_id}")


def prepare_preflight() -> dict[str, Any]:
    if git("rev-parse", "HEAD") != BASE_HEAD:
        raise RuntimeError(f"preflight must start from {BASE_HEAD}; HEAD={git('rev-parse','HEAD')}")
    if any(path.exists() for path in (PREFLIGHT, STATIC_QA, WORK_UNIT, METRIC_SPEC,
                                      PROBE_MANIFEST, BATCH_MANIFEST, REVISION_NOTE)):
        raise RuntimeError("preflight output already exists; refusing overwrite")
    manifest = jread(EXPERIMENT_MANIFEST)
    seen_runs = {item.get("run_id") for item in manifest.get("runs", [])}
    for run_id, *_ in platform.CARRY_SJTL_POSITION_RUN_MATRIX:
        if (RUNS / run_id).exists() or run_id in seen_runs:
            raise RuntimeError(f"immutable run ID is occupied; refusing overwrite: {run_id}")
    prior_auth = [item for item in manifest.get("authorization_batches", [])
                  if item.get("batch_id") == platform.CARRY_SJTL_POSITION_BATCH_ID]
    if (len(prior_auth) != 1 or prior_auth[0].get("authorized_physical_solve_count") != 6 or
            prior_auth[0].get("physical_solve_count_completed") != 0 or
            prior_auth[0].get("run_ids") != [item[0] for item in platform.CARRY_SJTL_POSITION_RUN_MATRIX]):
        raise RuntimeError("the prior preflight registration is missing/duplicated or already has a solve")
    baselines = _verify_base_runs()
    if platform.verify_sources().keys() != platform.SOURCE_SHA256.keys():
        raise RuntimeError("canonical source closure differs from pinned source list")
    solver_info = platform._solver_info()
    if solver_info["parent_head"] != BASE_HEAD:
        raise RuntimeError("solver identity recorded against an unexpected parent HEAD")
    if not platform.PLOTTER.is_file() or not platform.PLOTLY_ASSET.is_file():
        raise RuntimeError("classic plotter or shared Plotly asset is missing")
    analyzer_path = SERIES / "scripts" / "analyze_carry_sjtl_position.py"
    if not analyzer_path.is_file():
        raise RuntimeError("registered mechanical analyzer is missing")

    baseline_cases = {run_id: _baseline_case(run_id)
                      for run_id in ("A027_FULL_CB_CHAIN_ALL_CLOCK", "A028_FULL_CB_CHAIN_PAPER_CLOCK",
                                     "A029_FULL_CB_CHAIN_3X3_CLOCK", *[item[0] for item in platform.CARRY_POST_CB_SJTL_RUN_MATRIX])}
    baseline_parameters = platform.load_config("FULL_CB_CHAIN_ALL_CLOCK")[2]
    for run_id, (_case, _stimulus, params) in baseline_cases.items():
        if params != baseline_parameters:
            raise RuntimeError(f"frozen T1/CBU/DFF/D0-JTL parameters differ in baseline {run_id}")
    if len({json.dumps(baseline_cases[run_id][1], sort_keys=True)
            for run_id in baseline_cases}) != 1:
        raise RuntimeError("registered baseline BVM stimulus changed across A027-A033")

    allowed_by_preset: dict[str, set[str]] = {}
    for run_id, preset, rows, cols, clock, position, mask, reference in platform.CARRY_SJTL_POSITION_RUN_MATRIX:
        case, stimulus, params = platform.load_config(preset)
        if (case["ROW_BITS"], case["COL_BITS"], case["T1_CHAIN_CLK_START"]) != (rows, cols, clock):
            raise RuntimeError(f"registered row/column/clock differs for {run_id}")
        if params != baseline_parameters or stimulus != baseline_cases[reference][1]:
            raise RuntimeError(f"stimulus or device parameter changed from matched baseline in {run_id}")
        if [sum(cell in platform._active_cells(case) for cell in group)
            for group in platform.DIAGONALS.values()] != [
                [1, 2, 3, 4, 3, 2, 1] if rows == "1111" else
                [1, 1, 1, 3, 1, 1, 1] if rows == "1101" else [1, 2, 1, 0, 0, 0, 0]
            ][0]:
            raise RuntimeError(f"row/column active population differs from registered mapping: {run_id}")
        rendered = platform.render(case, stimulus, params, RUNS / run_id)
        _check_topology(run_id, case, rendered, position, mask)
        baseline_case = baseline_cases[reference][0]
        allowed = {"CASE", "CARRY_POST_CB_SJTL_COUNT", "CARRY_SJTL_POSITION",
                   "CARRY_SJTL_STAGE_MASK", "FOCUS_STAGE"}
        if rows != baseline_case["ROW_BITS"]:
            allowed |= {"ROW_BITS", "COL_BITS"}
        if clock != baseline_case["T1_CHAIN_CLK_START"]:
            allowed.add("T1_CHAIN_CLK_START")
        differences = _differences(case, baseline_case, allowed)
        if differences:
            raise RuntimeError(f"unregistered case parameter differences vs {reference}: {run_id}: {differences}")
        allowed_by_preset[preset] = allowed

    old_render_records = []
    for run_id, preset, *_rest in platform.CARRY_POST_CB_SJTL_RUN_MATRIX:
        case, stimulus, params = platform.load_config(preset)
        rendered = platform.render(case, stimulus, params, RUNS / run_id)
        old_deck = (RUNS / run_id / "deck.cir").read_text(encoding="utf-8")
        if rendered["deck"] != old_deck:
            raise RuntimeError(f"legacy A030-A033 deck render changed: {run_id}")
        old_render_records.append({"run_id": run_id, "deck_sha256": sha(RUNS / run_id / "deck.cir"),
                                  "render_matches_historical_deck": True})
    a027_case, a027_stim, a027_params = platform.load_config("FULL_CB_CHAIN_ALL_CLOCK")
    a027_render = platform.render(a027_case, a027_stim, a027_params,
                                  RUNS / "A027_FULL_CB_CHAIN_ALL_CLOCK")
    if a027_render["deck"] != (RUNS / "A027_FULL_CB_CHAIN_ALL_CLOCK" / "deck.cir").read_text(encoding="utf-8"):
        raise RuntimeError("A027 CB-only baseline render changed")

    records = []
    probe_records = {}
    for run_id, preset, rows, cols, clock, position, mask, reference in platform.CARRY_SJTL_POSITION_RUN_MATRIX:
        case, stimulus, params = platform.load_config(preset)
        rendered = platform.render(case, stimulus, params, RUNS / run_id)
        syntax_qa = _static_syntax_check(rendered, run_id)
        probe_bytes = (json.dumps(rendered["probes"], ensure_ascii=False, indent=2) + "\n").encode()
        probe_sha = hashlib.sha256(probe_bytes).hexdigest()
        record = {"run_id": run_id, "preset": preset, "reference_run": reference,
                  "row_bits": rows, "column_bits": cols, "clock_start": clock,
                  "carry_sjtl_position": position, "carry_sjtl_stage_mask": mask,
                  "carry_sjtl_stages": rendered["static_qa"]["carry_sjtl_stages"],
                  "deck_sha256": hashlib.sha256(rendered["deck"].encode()).hexdigest(),
                  "stimulus_sha256": hashlib.sha256(rendered["stimulus_text"].encode()).hexdigest(),
                  "probe_manifest_sha256": probe_sha, "static_qa": rendered["static_qa"],
                  "syntax_qa": syntax_qa, "physical_solve_count": 0}
        records.append(record)
        probe_records[run_id] = rendered["probes"]

    config_paths = [platform.USER_CASE, platform.STIMULUS, platform.T1_PARAMS, platform.CBU_PARAMS,
                    platform.DFF_PARAMS, platform.D0_JTL_PARAMS]
    preset_paths = [SERIES / "presets" / f"{preset}.env"
                    for _, preset, *_ in platform.CARRY_SJTL_POSITION_RUN_MATRIX]
    locked_files = {path.resolve().relative_to(REPO).as_posix(): sha(path)
                    for path in (*config_paths, *preset_paths)}
    locked_files[Path(platform.__file__).resolve().relative_to(REPO).as_posix()] = sha(Path(platform.__file__).resolve())
    locked_files[Path(__file__).resolve().relative_to(REPO).as_posix()] = sha(Path(__file__).resolve())
    locked_files[analyzer_path.relative_to(REPO).as_posix()] = sha(analyzer_path)
    test_file = SERIES / "tests" / "test_platform.py"
    locked_files[test_file.resolve().relative_to(REPO).as_posix()] = sha(test_file)
    probe_manifest = {"schema": "bvm4x4-carry-sjtl-position-probe-registry-v1",
                      "raw_phase_unit": "P(...) radians",
                      "display_convention": "rad/(2*pi) navigation arithmetic only",
                      "integration": "actual stored grid, trapezoid, half-open windows, no interpolation",
                      "runs": probe_records, "scientific_interpretation_performed": False}
    metric_spec = {"schema": "bvm4x4-carry-sjtl-position-metric-spec-v1",
                   "windows": {"ARRAY_FINAL_READ": [110, 121], "PRE_CLOCK": "[FINAL_READ end, configured clock start)",
                               "BEFORE_CLOCK": "[0, configured clock start)",
                               "CLOCK_EDGE": "[configured clock start, clock end + 1 ps)",
                               "POST_CLOCK": "[clock end + 1 ps, STOP)", "TOTAL": [0, 300]},
                   "required_arithmetic": ["node V min/max/time/area", "branch I min/max/charge",
                                           "same-JJ phase delta and voltage integral",
                                           "positive/negative unwrapped phase variation"],
                   "phase_unit": "raw radians; /2pi display is navigation only",
                   "shared_dout_voltage": "mixed DOUT/JOIN boundary; not array-only event count",
                   "event_classifier": None, "SFQ_count": "NOT_PERFORMED",
                   "product_bit_decode": "NOT_PERFORMED", "scientific_interpretation_performed": False,
                   "automatic_follow_up": False}
    static_qa = {"schema": "bvm4x4-carry-sjtl-position-static-qa-v1", "status": "PASS",
                 "parent_head": BASE_HEAD, "solver": solver_info,
                 "canonical_sources": platform.verify_sources(), "baseline_raw_references": baselines,
                 "legacy_render_regression": old_render_records + [{"run_id": "A027_FULL_CB_CHAIN_ALL_CLOCK",
                     "deck_sha256": sha(RUNS / "A027_FULL_CB_CHAIN_ALL_CLOCK" / "deck.cir"),
                     "render_matches_historical_deck": True}],
                 "new_runs": records, "config_file_sha256": locked_files,
                 "plotter_sha256": sha(platform.PLOTTER), "plotly_asset_sha256": sha(platform.PLOTLY_ASSET),
                 "physical_solve_count": 0, "scientific_interpretation_performed": False}
    work_unit = {"schema": "bvm4x4-carry-sjtl-position-work-unit-v1",
                 "batch_id": platform.CARRY_SJTL_POSITION_BATCH_ID,
                 "experiment_risk_level": "NORMAL", "parent_head_before_changes": BASE_HEAD,
                 "authorized_run_ids": [item[0] for item in platform.CARRY_SJTL_POSITION_RUN_MATRIX],
                 "authorized_physical_solve_count": 6, "physical_solve_count_completed": 0,
                 "registered_run_matrix": [records_item for records_item in records],
                 "locked_file_sha256": locked_files, "baseline_raw_sha256": baselines,
                 "no_parameter_sweep": True, "automatic_follow_up": False,
                 "scientific_interpretation_performed": False}
    preflight_lines = [
        "# BVM 4x4 Carry sJTL placement and stage-mask preflight", "",
        "> This experiment is governed by docs/EXPERIMENT_CONTRACT.md.", "",
        f"- Starting HEAD: `{BASE_HEAD}`; authorized solves: exactly 6 (A034-A039).",
        "- Risk: NORMAL. Only canonical sJTL placement/stage mask varies as registered; no device or clock sweep.",
        "- Canonical BVM/QB/CB/sJTL/jjmit SHA-256 values are pinned below; T1/DFF/CBU snapshots must match A027-A033.",
        "- All cases use SHARED 400u WL/BL, independent 100u SE, DT=0.01p, STOP=300p, synchronous GLOBAL_ONESHOT clock at only 200p/210p.",
        "- Topology: 7 T1, six CB_0928 Carry buffers, D1-D6 JOINs with independent DOUT/Carry branches, no ColdFlux MERGE, no added output-side devices.",
        "- Measurements: array final CB BJ1/BJ2 P/V, DOUT branch current, Carry CB BJ1/BJ2, selected sJTL BJ1 and boundary current, JOIN currents, T1 input/S/C/clock and DFF boundary/internal probes.",
        "- P(...) is radians. Same-JJ phase and voltage area use identical stored rows and windows; positive/negative variation is navigation arithmetic, not an event count.",
        "- Shared V(DOUT_Dk)/JOIN voltage is source-mixed and is not treated as array-only pulse count.",
        "- Artifact validity and mechanical QA only; scientific interpretation, event classification, and bit decoding are NOT_PERFORMED.",
        "- STOP: finish the six registered solves, QA, local classic plots, evidence package, commit/push, then await user/ChatGPT review.", "",
        "## Registered matrix", "", "| Run | Mask | Carry sJTL | Clock | Reference | Deck SHA-256 | Probe count | Raw estimate |",
        "|---|---|---|---:|---|---|---:|---:|",
    ]
    for row in records:
        preflight_lines.append(f"| {row['run_id']} | {row['row_bits']}/{row['column_bits']} | {row['carry_sjtl_position']} {row['carry_sjtl_stage_mask']} | {row['clock_start']} | {row['reference_run']} | `{row['deck_sha256']}` | {row['static_qa']['probe_count']} | {row['static_qa']['raw_estimate_bytes']} B |")
    preflight_lines.extend(["", "## Pinned source closure", ""])
    for role, info in platform.verify_sources().items():
        preflight_lines.append(f"- {role}: `{info['path']}` — `{info['sha256']}`")
    preflight_lines.extend(["", "Physical solves are not performed by preflight. JoSIM `-s` static syntax checks were run on all six rendered decks.", ""])
    preflight_text = "\n".join(preflight_lines) + "\n"
    _assert_json_object_keys(static_qa)
    _assert_json_object_keys(work_unit)
    prior_attempt = int(prior_auth[0].get("preflight_attempt", 1))
    prior_preflight = {"attempt": prior_attempt, "status": "STATIC_QA_PASS_SUPERSEDED_BEFORE_ANY_SOLVE",
                       "preflight_sha256": prior_auth[0].get("preflight_sha256"),
                       "static_qa_status": prior_auth[0].get("static_qa_status"),
                       "physical_solve_count_completed": 0}
    prior_revisions = list(prior_auth[0].get("preflight_revisions", [])) + [prior_preflight]
    revision_note = ("# Preflight revision 3\n\n"
                     "Attempts 1 and 2 passed static QA but were superseded before execution: attempt 1 lacked "
                     "run-phase authorization progress bookkeeping, and attempt 2 recorded mixed relative path "
                     "roots that would fail the execution lock. No transient solver was invoked and no A034-A039 "
                     "run directory was created. This locked attempt 3 fixes both bookkeeping and path resolution.\n\n"
                     + "\n".join(f"- Attempt {item['attempt']} preflight SHA-256: `{item['preflight_sha256']}`"
                                  for item in prior_revisions) + "\n")
    work_unit["preflight_attempt"] = 3
    work_unit["superseded_preflight_attempts"] = prior_revisions
    work_unit["preflight_sha256"] = hashlib.sha256(preflight_text.encode()).hexdigest()
    work_unit["static_qa_sha256"] = hashlib.sha256(
        (json.dumps(static_qa, ensure_ascii=False, indent=2) + "\n").encode()).hexdigest()
    work_unit["metric_spec_sha256"] = hashlib.sha256(
        (json.dumps(metric_spec, ensure_ascii=False, indent=2) + "\n").encode()).hexdigest()
    work_unit["probe_manifest_sha256"] = hashlib.sha256(
        (json.dumps(probe_manifest, ensure_ascii=False, indent=2) + "\n").encode()).hexdigest()

    prior_auth[0].setdefault("preflight_revisions", []).append(prior_preflight)
    prior_auth[0].update({"preflight_attempt": 2, "parent_head_at_preflight": BASE_HEAD,
                          "preflight_sha256": work_unit["preflight_sha256"],
                          "static_qa_status": "PASS", "physical_solve_count_completed": 0,
                          "scientific_interpretation_performed": False, "automatic_follow_up": False})
    work_unit["revision_note_sha256"] = hashlib.sha256(revision_note.encode()).hexdigest()
    EXPERIMENT_MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    jwrite_new(REVISION_NOTE, revision_note)
    jwrite_new(PREFLIGHT, preflight_text)
    jwrite_new(STATIC_QA, static_qa)
    jwrite_new(WORK_UNIT, work_unit)
    jwrite_new(METRIC_SPEC, metric_spec)
    jwrite_new(PROBE_MANIFEST, probe_manifest)
    batch = {"schema": "bvm4x4-carry-sjtl-position-batch-manifest-v1",
             "batch_id": platform.CARRY_SJTL_POSITION_BATCH_ID,
             "status": "PREFLIGHT_PASS_READY", "parent_head": BASE_HEAD,
             "authorized_run_ids": [item[0] for item in platform.CARRY_SJTL_POSITION_RUN_MATRIX],
             "physical_solve_count_authorized": 6, "physical_solve_count_completed": 0,
             "static_qa_status": "PASS", "runs": [], "scientific_interpretation_performed": False,
             "automatic_follow_up": False}
    jwrite_new(BATCH_MANIFEST, batch)
    return {"status": "PREFLIGHT_PASS", "batch_id": platform.CARRY_SJTL_POSITION_BATCH_ID,
            "runs": records, "physical_solve_count": 0,
            "preflight": PREFLIGHT.relative_to(SERIES).as_posix()}


def run_batch() -> int:
    if not all(path.is_file() for path in (PREFLIGHT, STATIC_QA, WORK_UNIT, METRIC_SPEC, PROBE_MANIFEST, BATCH_MANIFEST)):
        raise RuntimeError("locked preflight package is incomplete; run --prepare-preflight first")
    static = jread(STATIC_QA)
    work_unit = jread(WORK_UNIT)
    batch = jread(BATCH_MANIFEST)
    if (static.get("status") != "PASS" or batch.get("status") != "PREFLIGHT_PASS_READY" or
            work_unit.get("authorized_run_ids") != [item[0] for item in platform.CARRY_SJTL_POSITION_RUN_MATRIX] or
            work_unit.get("authorized_physical_solve_count") != 6 or work_unit.get("physical_solve_count_completed") != 0):
        raise RuntimeError("preflight does not authorize exactly A034-A039")
    for relative, expected in work_unit["locked_file_sha256"].items():
        path = REPO / relative
        if not path.is_file() or sha(path) != expected:
            raise RuntimeError(f"locked implementation/config file changed after preflight: {relative}")
    for path, key in ((PREFLIGHT, "preflight_sha256"), (STATIC_QA, "static_qa_sha256"),
                      (METRIC_SPEC, "metric_spec_sha256"), (PROBE_MANIFEST, "probe_manifest_sha256")):
        if not work_unit.get(key) or sha(path) != work_unit[key]:
            raise RuntimeError(f"preflight-bound artifact changed after lock: {path.name}")
    if not REVISION_NOTE.is_file() or sha(REVISION_NOTE) != work_unit.get("revision_note_sha256"):
        raise RuntimeError("preflight revision note changed after lock")
    if subprocess.run(["git", "merge-base", "--is-ancestor", BASE_HEAD, "HEAD"], cwd=REPO).returncode != 0:
        raise RuntimeError("preflight parent is not an ancestor of current HEAD")
    if any((RUNS / run_id).exists() for run_id, *_ in platform.CARRY_SJTL_POSITION_RUN_MATRIX):
        raise RuntimeError("new immutable run directory already exists; refusing physical solve")
    manifest = jread(EXPERIMENT_MANIFEST)
    if int(manifest.get("physical_solve_count", -1)) != 33:
        raise RuntimeError("unexpected pre-batch physical solve count; refusing to continue")
    if _verify_base_runs() != work_unit["baseline_raw_sha256"]:
        raise RuntimeError("baseline raw identity changed after preflight")

    solver_info = platform._solver_info()
    current_head = git("rev-parse", "HEAD")
    auth = [item for item in manifest.get("authorization_batches", [])
            if item.get("batch_id") == platform.CARRY_SJTL_POSITION_BATCH_ID]
    if len(auth) != 1:
        raise RuntimeError("authorized batch registration missing or duplicated")
    auth[0]["parent_head_at_execution"] = current_head
    auth[0]["solver"] = solver_info
    auth[0]["preflight_sha256"] = sha(PREFLIGHT)
    manifest["authorization_batches"] = manifest.get("authorization_batches", [])
    EXPERIMENT_MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    batch.update({"status": "RUNNING", "execution_head": current_head,
                  "preflight_sha256": sha(PREFLIGHT), "static_qa_sha256": sha(STATIC_QA),
                  "solver": solver_info})
    batch_path = BATCH_MANIFEST
    batch_path.write_text(json.dumps(batch, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    locked_runs = {item["run_id"]: item for item in static["new_runs"]}
    for run_id, preset, rows, cols, clock, position, mask, _reference in platform.CARRY_SJTL_POSITION_RUN_MATRIX:
        case, stimulus, params = platform.load_config(preset)
        rendered = platform.render(case, stimulus, params, RUNS / run_id)
        locked = locked_runs[run_id]
        deck_sha = hashlib.sha256(rendered["deck"].encode()).hexdigest()
        probe_sha = hashlib.sha256((json.dumps(rendered["probes"], ensure_ascii=False, indent=2) + "\n").encode()).hexdigest()
        if (deck_sha != locked["deck_sha256"] or probe_sha != locked["probe_manifest_sha256"] or
                rendered["static_qa"].get("status") != "PASS"):
            raise RuntimeError(f"locked deck/probe/static QA mismatch before solve: {run_id}")
        print(f"START {run_id}: {preset} ROW/COL={rows}/{cols} CARRY_SJTL={position}:{mask} CLK={clock}", flush=True)
        code, result = platform.run_one(case, stimulus, params, solver_info,
                                        batch_id=platform.CARRY_SJTL_POSITION_BATCH_ID,
                                        run_id_override=run_id, rendered_override=rendered,
                                        preflight_path=PREFLIGHT,
                                        metric_spec_path_override=METRIC_SPEC,
                                        expected_deck_sha256=locked["deck_sha256"])
        row = {key: result.get(key) for key in ("run_id", "case", "status", "artifact_status",
                                                "physical_solve_count", "qa_status", "raw_sha256",
                                                "raw_bytes", "deck_sha256", "probe_count")}
        batch["runs"].append(row)
        batch["physical_solve_count_completed"] += int(result.get("physical_solve_count", 1))
        batch["status"] = "RUNNING" if code == 0 else "STOPPED_AFTER_SOLVER_OR_ARTIFACT_FAILURE"
        batch_path.write_text(json.dumps(batch, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        manifest = jread(EXPERIMENT_MANIFEST)
        auth = [item for item in manifest.get("authorization_batches", [])
                if item.get("batch_id") == platform.CARRY_SJTL_POSITION_BATCH_ID]
        if len(auth) != 1:
            raise RuntimeError("authorization registration lost while recording run progress")
        auth[0]["physical_solve_count_completed"] = batch["physical_solve_count_completed"]
        auth[0]["execution_status"] = batch["status"]
        EXPERIMENT_MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False), flush=True)
        if code != 0:
            print("STOP: no retry or later solve after solver/artifact failure.", file=sys.stderr, flush=True)
            return code
    batch["status"] = "ALL_RUNS_MECHANICAL_QA_PASS"
    batch_path.write_text(json.dumps(batch, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    from analyze_carry_sjtl_position import analyze_batch
    summary = analyze_batch()
    batch["analysis_status"] = summary["status"]
    batch["summary_path"] = summary["summary_path"]
    batch["status"] = "BATCH_COMPLETE_AWAITING_USER_CHATGPT_REVIEW"
    batch_path.write_text(json.dumps(batch, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    manifest = jread(EXPERIMENT_MANIFEST)
    auth = [item for item in manifest.get("authorization_batches", [])
            if item.get("batch_id") == platform.CARRY_SJTL_POSITION_BATCH_ID]
    if len(auth) != 1 or auth[0].get("physical_solve_count_completed") != 6:
        raise RuntimeError("completed batch did not close all six authorized solves")
    auth[0]["execution_status"] = batch["status"]
    auth[0]["mechanical_analysis_status"] = summary["status"]
    EXPERIMENT_MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--prepare-preflight", action="store_true")
    group.add_argument("--run-batch", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.prepare_preflight:
            result = prepare_preflight()
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        return run_batch()
    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
