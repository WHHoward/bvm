#!/usr/bin/env python3
"""Lock, statically validate, and run exactly A030-A033 for the post-CB sJTL batch."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import diagonal_platform as platform

SERIES = platform.SERIES
REPO = platform.REPO
RUNS = platform.RUNS
TASK = platform.CARRY_POST_CB_SJTL_ANALYSIS
BATCH_ID = platform.CARRY_POST_CB_SJTL_BATCH_ID
BASE_HEAD = "a5168f187e97b23685863d3d0964e898bbf19863"
PREFLIGHT = TASK / "PREFLIGHT.md"
STATIC_QA = TASK / "STATIC_QA.json"
WORK_UNIT = TASK / "WORK_UNIT.json"
PROBE_REGISTRY = TASK / "PROBE_MANIFEST.json"
BATCH_MANIFEST = TASK / "BATCH_MANIFEST.json"
EXPERIMENT_MANIFEST = SERIES / "experiment_manifest.json"
ANALYZER = SERIES / "scripts" / "analyze_carry_post_cb_sjtl.py"
TEST_FILE = SERIES / "tests" / "test_platform.py"
STATIC_SUBCKTS = ("THmitll_MERGE", "THmitll_DFF", "D0_JTL", "T1", "BVM", "BQ", "sJTL", "CB")
BASELINE_RAW = {
    "A027_FULL_CB_CHAIN_ALL_CLOCK": "939e6024928be84df809532ecd8b716b815a9b96ea498324fc5c30b712100e46",
    "A028_FULL_CB_CHAIN_PAPER_CLOCK": "59ba22b2c31bd04993989c16a7c37d1e5bb904c078ef9db979657de81e604701",
    "A029_FULL_CB_CHAIN_3X3_CLOCK": "d943765ab3e47c1607ab3c29ff08a1088f2444dfd8a3266e9670a1d75d24ac0f",
}
EXPECTED_ARRAY_SJTL = {"D0": [1], "D1": [1, 1], "D2": [1, 2, 1],
                       "D3": [1, 2, 2, 1], "D4": [1, 2, 1], "D5": [1, 1], "D6": [1]}


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def jread(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def jnew(path: Path, value: Any) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite preflight artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def jreplace(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def git(*args: str, check: bool = True) -> str:
    completed = subprocess.run(["git", *args], cwd=REPO, text=True,
                               capture_output=True, check=check)
    return completed.stdout.strip()


def _assert_batch_ids_free() -> None:
    manifest = jread(EXPERIMENT_MANIFEST)
    seen = {item.get("run_id") for item in manifest.get("runs", [])}
    for run_id, *_ in platform.CARRY_POST_CB_SJTL_RUN_MATRIX:
        if (RUNS / run_id).exists() or run_id in seen:
            raise RuntimeError(f"immutable run ID already occupied; refusing overwrite: {run_id}")
    if any(item.get("batch_id") == BATCH_ID for item in manifest.get("authorization_batches", [])):
        raise RuntimeError(f"authorization batch already registered: {BATCH_ID}")
    if any(path.exists() for path in (PREFLIGHT, STATIC_QA, WORK_UNIT, PROBE_REGISTRY, BATCH_MANIFEST)):
        raise RuntimeError("task output path collision; refusing to overwrite existing preflight artifacts")
    if git("rev-parse", "HEAD") != BASE_HEAD:
        raise RuntimeError(f"preflight must start at {BASE_HEAD}; current HEAD={git('rev-parse','HEAD')}")


def _verify_baselines() -> dict[str, dict[str, Any]]:
    records = {}
    for run_id, expected_raw_sha in BASELINE_RAW.items():
        run_dir = RUNS / run_id
        raw = run_dir / "raw.csv"
        result, qa, chain_qa = (jread(run_dir / name) for name in
                                ("result.json", "qa.json", "chain_qa.json"))
        raw_sha = sha(raw)
        if (raw_sha != expected_raw_sha or result.get("raw_sha256") != raw_sha or
                result.get("artifact_status") != "VALID" or qa.get("status") != "PASS" or
                chain_qa.get("status") != "PASS" or
                chain_qa.get("raw_sha256_after_analysis") != raw_sha):
            raise RuntimeError(f"registered baseline raw/QA identity mismatch: {run_id}")
        records[run_id] = {"raw_path": raw.relative_to(SERIES).as_posix(),
                           "raw_sha256": raw_sha, "raw_bytes": raw.stat().st_size,
                           "deck_sha256": result.get("deck_sha256"),
                           "physical_solve_count": 1, "artifact_status": "VALID", "qa_status": "PASS"}
    return records


def _case_diff(actual: dict[str, str], baseline: dict[str, str], allowed: set[str]) -> list[str]:
    keys = set(actual) | set(baseline)
    return sorted(key for key in keys if actual.get(key) != baseline.get(key) and key not in allowed)


def _clock_lines(deck: str) -> list[str]:
    return sorted(line for line in deck.splitlines() if line.startswith("V_TRIG_CLK_"))


def _normalized_clock_deck(deck: str) -> list[str]:
    return [line for line in deck.splitlines() if not line.startswith("V_TRIG_CLK_")]


def _run_syntax_static(rendered: dict[str, Any], run_id: str) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix=f".post-cb-sjtl-{run_id}-", dir=RUNS) as tmp_name:
        temp = Path(tmp_name)
        (temp / "deck.cir").write_text(rendered["deck"], encoding="utf-8")
        (temp / "stimulus.inc").write_text(rendered["stimulus_text"], encoding="utf-8")
        t1_path = temp / "sources" / "t1_cell_tunable.cir"
        t1_path.parent.mkdir(parents=True, exist_ok=True)
        t1_path.write_text(rendered["t1_source_text"], encoding="utf-8")
        for relpath, text in rendered["chain_source_texts"].items():
            target = temp / relpath
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8")
        command = [str(platform.SOLVER)]
        for subckt in STATIC_SUBCKTS:
            command.extend(("-s", subckt))
        command.append(str(temp / "deck.cir"))
        proc = subprocess.run(command, cwd=temp, capture_output=True, text=True, check=False)
        combined = proc.stdout + proc.stderr
        if proc.returncode:
            raise RuntimeError(f"JoSIM static -s failed for {run_id}: {combined[-3000:]}")
        lines = [line.strip() for line in combined.splitlines() if line.strip()]
        return {"status": "PASS", "command": command, "exit_code": proc.returncode,
                "stdout_stderr_sha256": hashlib.sha256(combined.encode()).hexdigest(),
                "output_line_count": len(lines), "output_tail": lines[-8:]}


def _render_and_validate(*, run_syntax: bool) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if not platform.SOLVER.is_file() or not platform.PLOTTER.is_file() or not platform.PLOTLY_ASSET.is_file():
        raise RuntimeError("recorded solver, josim-plot2, or shared Plotly JS asset is missing")
    submit_script = SERIES / "scripts" / "submit.py"
    submit_wrapper = SERIES / "submit.sh"
    test_file = SERIES / "tests" / "test_platform.py"
    test_submit_file = SERIES / "tests" / "test_submit.py"
    if any(not path.is_file() for path in (submit_script, submit_wrapper, test_file, test_submit_file, ANALYZER)):
        raise RuntimeError("task runner, analyzer, submit workflow or tests are missing")
    sources = platform.verify_sources()
    if set(sources) != set(platform.SOURCE_SHA256):
        raise RuntimeError("pinned canonical source closure is incomplete")
    if sha(REPO / platform.SOURCE_PATHS["SJTL"]) != platform.SOURCE_SHA256["SJTL"]:
        raise RuntimeError("canonical sJTL_0923 SHA differs from the pinned source")
    if sha(REPO / platform.SOURCE_PATHS["CB"]) != platform.SOURCE_SHA256["CB"]:
        raise RuntimeError("canonical CB_0928 SHA differs from the pinned source")
    baselines = _verify_baselines()
    expected_next = platform.allocate_run_id("probe")
    if not expected_next.startswith("A030_"):
        raise RuntimeError(f"automatic run allocation is not A030: {expected_next}")

    a027_case = jread(RUNS / "A027_FULL_CB_CHAIN_ALL_CLOCK" / "case_manifest.json")["case"]
    a027_case.setdefault("CARRY_POST_CB_SJTL_COUNT", "0")
    a028_case = jread(RUNS / "A028_FULL_CB_CHAIN_PAPER_CLOCK" / "case_manifest.json")["case"]
    a028_case.setdefault("CARRY_POST_CB_SJTL_COUNT", "0")
    a029_case = jread(RUNS / "A029_FULL_CB_CHAIN_3X3_CLOCK" / "case_manifest.json")["case"]
    a029_case.setdefault("CARRY_POST_CB_SJTL_COUNT", "0")
    baseline_cases = {"A027_FULL_CB_CHAIN_ALL_CLOCK": a027_case,
                      "A028_FULL_CB_CHAIN_PAPER_CLOCK": a028_case,
                      "A029_FULL_CB_CHAIN_3X3_CLOCK": a029_case}
    baseline_stimulus = {run_id: jread(RUNS / run_id / "case_manifest.json")["stimulus"]
                         for run_id in baseline_cases}
    baseline_params = platform.load_config("FULL_CB_CHAIN_ALL_CLOCK")[2]
    for run_id in baseline_cases:
        saved_params = {}
        for name in ("T1_PARAMS.snapshot.env", "CBU_PARAMS.snapshot.env", "DFF_PARAMS.snapshot.env",
                     "D0_JTL_PARAMS.snapshot.env"):
            saved_params.update(platform.parse_env(RUNS / run_id / name))
        if saved_params != baseline_params:
            raise RuntimeError(f"fixed T1/CBU/DFF/D0-JTL parameter snapshot mismatch in {run_id}")

    rows = []
    allowed_case_differences = {
        "A030_CARRY_POST_CB_SJTL_ALL_200": {"CASE", "CARRY_POST_CB_SJTL_COUNT"},
        "A031_CARRY_POST_CB_SJTL_ALL_210": {"CASE", "CARRY_POST_CB_SJTL_COUNT", "T1_CHAIN_CLK_START"},
        "A032_CARRY_POST_CB_SJTL_PAPER_210": {"CASE", "ROW_BITS", "COL_BITS",
                                              "CARRY_POST_CB_SJTL_COUNT", "T1_CHAIN_CLK_START"},
        "A033_CARRY_POST_CB_SJTL_3X3_210": {"CASE", "ROW_BITS", "COL_BITS", "FOCUS_STAGE",
                                            "CARRY_POST_CB_SJTL_COUNT", "T1_CHAIN_CLK_START"},
    }
    expected_population = {
        "A030_CARRY_POST_CB_SJTL_ALL_200": [1, 2, 3, 4, 3, 2, 1],
        "A031_CARRY_POST_CB_SJTL_ALL_210": [1, 2, 3, 4, 3, 2, 1],
        "A032_CARRY_POST_CB_SJTL_PAPER_210": [1, 1, 1, 3, 1, 1, 1],
        "A033_CARRY_POST_CB_SJTL_3X3_210": [1, 2, 1, 0, 0, 0, 0],
    }
    for run_id, preset, row_bits, col_bits, clock_start, reference in platform.CARRY_POST_CB_SJTL_RUN_MATRIX:
        if (RUNS / run_id).exists() or any(entry.get("run_id") == run_id
                                           for entry in jread(EXPERIMENT_MANIFEST).get("runs", [])):
            raise RuntimeError(f"immutable run ID already occupied: {run_id}")
        case, stimulus, params = platform.load_config(preset)
        expected_bits = (row_bits, col_bits)
        if (case["ROW_BITS"], case["COL_BITS"]) != expected_bits:
            raise RuntimeError(f"registered row/column mismatch for {run_id}")
        if (case.get("CBU_CHAIN_TOPOLOGY") != "CB_CARRY_BUFFER_ALL" or
                case.get("CBU_OVERRIDE_D1") != "NONE" or case.get("CARRY_POST_CB_SJTL_COUNT") != "1" or
                case.get("T1_CHAIN_CLOCK_MODE") != "GLOBAL_ONESHOT" or
                case.get("T1_CHAIN_CLK_START") != clock_start):
            raise RuntimeError(f"registered topology/clock mismatch for {run_id}")
        if (case["OUTPUT_MODE"] != "DIAGONAL_T1_CHAIN" or case["T1_MODE"] != "CHAIN" or
                case["DT"] != "0.01p" or case["STOP"] != "300p" or
                case["PROBE_PROFILE"] != "t1_chain_focus" or case["SE_ENABLE_MASK"] != "ALL"):
            raise RuntimeError(f"fixed chain baseline differs for {run_id}")
        population = [sum(cell in platform._active_cells(case) for cell in cells)
                      for cells in platform.DIAGONALS.values()]
        if population != expected_population[run_id]:
            raise RuntimeError(f"row/column mapping for {run_id} produced {population}")
        if {name: list(platform._sjtl_counts(case, name)) for name in platform.DIAGONALS} != EXPECTED_ARRAY_SJTL:
            raise RuntimeError(f"array-internal sJTL topology changed for {run_id}")
        if stimulus != baseline_stimulus[reference]:
            raise RuntimeError(f"BVM PWL stimulus differs from matched baseline {reference}: {run_id}")
        if params != baseline_params:
            raise RuntimeError(f"T1/CBU/DFF/D0-JTL parameters changed for {run_id}")
        allowed = allowed_case_differences[run_id]
        differences = _case_diff(case, baseline_cases[reference], allowed)
        if differences:
            raise RuntimeError(f"unregistered case differences vs {reference} in {run_id}: {differences}")

        rendered = platform.render(case, stimulus, params, RUNS / run_id)
        if rendered["static_qa"].get("status") != "PASS":
            raise RuntimeError(f"platform static QA failed for {run_id}")
        if rendered["static_qa"]["raw_estimate_bytes"] >= platform.MAX_RAW_BYTES:
            raise RuntimeError(f"raw estimate exceeds single-file limit for {run_id}")
        deck_lines = rendered["deck"].splitlines()
        for index in range(1, 7):
            required = {
                f"V_CBU_A_D{index} DOUT_D{index} CBU_JOIN_D{index} 0",
                f"V_CARRY_IN_D{index} C_D{index-1} CARRY_CB_IN_D{index} 0",
                f"XCB_CARRY_D{index} CARRY_CB_IN_D{index} CARRY_CB_OUT_D{index} CB",
                f"V_CARRY_SJTL_IN_D{index} CARRY_CB_OUT_D{index} CARRY_SJTL_IN_D{index} 0",
                f"XSJTL_CARRY_D{index} CARRY_SJTL_IN_D{index} CARRY_SJTL_OUT_D{index} sJTL",
                f"V_CBU_B_D{index} CARRY_SJTL_OUT_D{index} CBU_JOIN_D{index} 0",
                f"V_T1_LINK_D{index} CBU_JOIN_D{index} T1_I_D{index} 0",
            }
            if not required.issubset(set(deck_lines)):
                raise RuntimeError(f"incomplete CB→sJTL→JOIN topology at D{index}: {required - set(deck_lines)}")
            if sum(f"CBU_JOIN_D{index}" in line for line in deck_lines
                   if not line.startswith(("*", ".print"))) != 3:
                raise RuntimeError(f"JOIN_D{index} has unexpected branches or loads")
        if len([line for line in deck_lines if line.startswith("XCB_CARRY_D")]) != 6:
            raise RuntimeError(f"expected exactly six Carry CBs in {run_id}")
        if len([line for line in deck_lines if line.startswith("XSJTL_CARRY_D")]) != 6:
            raise RuntimeError(f"expected exactly six post-CB sJTLs in {run_id}")
        if len([line for line in deck_lines if line.startswith("XCB_D")]) != 16:
            raise RuntimeError(f"array-side CB count changed in {run_id}")
        if any(line.startswith(("XCBU_D", "R_TERM_D", "R_C_D", "XJTL_CBU", "XSJTL_CBU"))
               for line in deck_lines):
            raise RuntimeError(f"forbidden MERGE/terminal/load/extra isolator found in {run_id}")
        expected_clock = "PWL(" + " ".join(
            f"{time} {value}" for time, value in platform._global_clock_points(case, params)) + ")"
        clock_sources = [line for line in deck_lines if line.startswith("V_TRIG_CLK_")]
        clock_series = [line for line in deck_lines if line.startswith("R_TRIG_CLK_")]
        if len(clock_sources) != 8 or len(clock_series) != 8 or any(expected_clock not in line for line in clock_sources):
            raise RuntimeError(f"all eight independent one-shot clocks are not identical at {run_id}")
        if any("PULSE(" in line for line in clock_sources) or any("R_CLK_QUIET" in line for line in deck_lines):
            raise RuntimeError(f"unexpected periodic or quiet clock source in {run_id}")
        pages = platform.plot_signals(rendered["probes"])
        if [item["file"] for item in pages] != ["01_array.html", "02_carry.html", "03_join.html", "04_t1.html"]:
            raise RuntimeError(f"subsystem HTML set differs for {run_id}")
        syntax = _run_syntax_static(rendered, run_id) if run_syntax else {"status": "NOT_RUN"}
        rows.append({"run_id": run_id, "preset": preset, "reference_run": reference,
                     "row_bits": row_bits, "column_bits": col_bits, "diagonal_population": population,
                     "clock_start": clock_start, "carry_post_cb_sjtl_count_per_stage": 1,
                     "array_sjtl_count": rendered["static_qa"]["array_sjtl_count"],
                     "total_sjtl_count": rendered["static_qa"]["sjtl_count"],
                     "probe_count": rendered["probes"]["signal_count"],
                     "raw_estimate_bytes": rendered["static_qa"]["raw_estimate_bytes"],
                     "deck_sha256": hashlib.sha256(rendered["deck"].encode()).hexdigest(),
                     "stimulus_sha256": hashlib.sha256(rendered["stimulus_text"].encode()).hexdigest(),
                     "probe_manifest": rendered["probes"], "plot_pages": pages,
                     "source_hashes": {key: value["sha256"] for key, value in rendered["sources"].items()},
                     "static_qa": rendered["static_qa"], "josim_static_parse": syntax,
                     "case": case, "stimulus": stimulus, "effective_parameters": params,
                     "t1_and_device_params_sha256": hashlib.sha256(
                         json.dumps(params, sort_keys=True).encode()).hexdigest()})

    by_id = {row["run_id"]: row for row in rows}
    if _normalized_clock_deck(platform.render(
            *platform.load_config("CARRY_POST_CB_SJTL_ALL_200"), RUNS / "_RENDER_ONLY_A030")["deck"]) != \
            _normalized_clock_deck(platform.render(
                *platform.load_config("CARRY_POST_CB_SJTL_ALL_210"), RUNS / "_RENDER_ONLY_A031")["deck"]):
        raise RuntimeError("A030/A031 decks differ beyond the global clock PWL start")
    if by_id["A030_CARRY_POST_CB_SJTL_ALL_200"]["stimulus_sha256"] != \
            by_id["A031_CARRY_POST_CB_SJTL_ALL_210"]["stimulus_sha256"]:
        raise RuntimeError("A030/A031 stimulus must be identical")
    parameter_paths = {"USER_CASE.env": platform.USER_CASE, "STIMULUS.env": platform.STIMULUS,
                       "T1_PARAMS.env": platform.T1_PARAMS, "CBU_PARAMS.env": platform.CBU_PARAMS,
                       "DFF_PARAMS.env": platform.DFF_PARAMS, "D0_JTL_PARAMS.env": platform.D0_JTL_PARAMS}
    parameter_paths.update({f"presets/{preset}.env": SERIES / "presets" / f"{preset}.env"
                            for _, preset, *_ in platform.CARRY_POST_CB_SJTL_RUN_MATRIX})
    parameter_file_hashes = {name: sha(path) for name, path in parameter_paths.items()}
    legacy_case, legacy_stim, legacy_params = platform.load_config("FULL_CB_CHAIN_ALL_CLOCK")
    legacy_render = platform.render(legacy_case, legacy_stim, legacy_params,
                                    RUNS / "A027_FULL_CB_CHAIN_ALL_CLOCK")
    legacy_deck = (RUNS / "A027_FULL_CB_CHAIN_ALL_CLOCK" / "deck.cir").read_text(encoding="utf-8")
    if (legacy_render["deck"] != legacy_deck or legacy_case["CARRY_POST_CB_SJTL_COUNT"] != "0" or
            legacy_render["static_qa"].get("carry_post_cb_sjtl_count") != 0):
        raise RuntimeError("legacy CB_CARRY_BUFFER_ALL render-only regression failed")
    terminal_case, terminal_stim, terminal_params = platform.load_config("PAPER_1101_1101")
    terminal_render = platform.render(terminal_case, terminal_stim, terminal_params,
                                      RUNS / "_CARRY_POST_SJTL_TERMINAL_REGRESSION")
    if terminal_render["static_qa"].get("status") != "PASS" or terminal_render["static_qa"].get("t1_count", 0) != 0:
        raise RuntimeError("DIAGONAL_TERMINAL render-only regression failed")
    summary = {"status": "PASS", "base_head": BASE_HEAD, "source_tree_head_before_preflight": git("rev-parse", "HEAD"),
               "physical_solve_count": 0, "authorized_physical_solve_count": 4,
               "baseline_runs": baselines, "canonical_source_hashes": {key: value["sha256"] for key, value in sources.items()},
               "solver_path": str(platform.SOLVER), "solver_version": subprocess.run(
                   [str(platform.SOLVER), "--version"], cwd=REPO, capture_output=True, text=True,
                   check=True).stdout.strip(), "solver_sha256": sha(platform.SOLVER),
               "plotter_sha256": sha(platform.PLOTTER), "plotly_asset_sha256": sha(platform.PLOTLY_ASSET),
               "local_submit_script_sha256": sha(submit_script), "local_submit_wrapper_sha256": sha(submit_wrapper),
               "platform_test_sha256": sha(test_file), "submit_test_sha256": sha(test_submit_file),
               "legacy_cb_carry_buffer_all_render_byte_identical_to_A027": True,
               "terminal_mode_render_only": terminal_render["static_qa"]["status"],
               "parameter_file_sha256": parameter_file_hashes,
               "cases": [{key: value for key, value in row.items() if key not in {"probe_manifest", "plot_pages", "static_qa"}}
                         for row in rows],
               "a030_a031_only_clock_pwl_changed": True,
               "no_physical_solve_invoked": True, "scientific_interpretation_performed": False}
    return rows, summary


def _render_preflight(summary: dict[str, Any]) -> str:
    lines = ["# Carry CB + canonical sJTL batch preflight", "",
             "> This experiment is governed by docs/EXPERIMENT_CONTRACT.md.", "",
             f"- Experiment: `{BATCH_ID}`; risk: `NORMAL`.",
             f"- Preflight revision: `{summary.get('preflight_revision', 1)}`.",
             f"- Parent HEAD: `{BASE_HEAD}`; current preflight HEAD: `{git('rev-parse','HEAD')}`.",
             "- Exact authorized runs: A030, A031, A032, A033; physical solve count is capped at four.",
             "- Changed topology: one canonical `sJTL_0923` per Carry CB, D1-D6, using the pinned canonical source SHA.",
             "- Frozen: all BVM/QB/CB/T1/DFF parameters, array topology and array-internal sJTL counts, D0 entrance JTL, shared stimulus, clock pulse shape, DT=0.01p and STOP=300p.",
             "- Absolute one-shot clock starts: A030=200p, A031/A032/A033=210p. No per-stage staggering or periodic clock.",
             "- `V(DOUT_Dk)` and `V(CBU_JOIN_Dk)` are shared boundary voltages separated by ideal 0-V current sensors; their voltage-area arithmetic is not an array-only pulse/count measure.",
             "- Analysis is mechanical only: actual-grid extrema/areas/currents and same-JJ phase/voltage checks; no event classifier, bit decode, or mechanism interpretation.",
             "- Execution gate: run A030 and A031 first. A solver/artifact hard failure stops the remainder; a functioning artifact with any physical outcome continues only through A032/A033 as authorized.",
             "- A001-A029 are immutable; the A027/A028/A029 raw hashes below are regression references.", "",
             "## Registered run matrix", "",
             "| Run | ROW/COL | Clock start | Baseline | Diagonal population reference | Probes | Raw estimate | Deck SHA-256 |",
             "|---|---|---:|---|---|---:|---:|---|"]
    for row in summary["cases"]:
        lines.append(f"| {row['run_id']} | {row['row_bits']}/{row['column_bits']} | {row['clock_start']} | {row['reference_run']} | "
                     f"{row['diagonal_population']} | {row['probe_count']} | {row['raw_estimate_bytes']} B | `{row['deck_sha256']}` |")
    lines.extend(["", "## Canonical sources and identities", ""])
    for role, digest in summary["canonical_source_hashes"].items():
        lines.append(f"- `{role}` SHA-256: `{digest}`")
    lines.extend(["", "## Frozen configuration, probe and metric identities", "",
                  f"- `STATIC_QA.json` SHA-256: `{sha(STATIC_QA)}`; it contains the exact effective case, stimulus and complete device-parameter map for each candidate.",
                  f"- `PROBE_MANIFEST.json` SHA-256: `{sha(PROBE_REGISTRY)}`; exact probe endpoints, directions, units and four subsystem plot groups.",
                  f"- `METRIC_SPEC.json` SHA-256: `{sha(TASK / 'METRIC_SPEC.json')}`.",
                  f"- `experiment.yaml` SHA-256: `{sha(TASK / 'experiment.yaml')}`; `human-gate.yaml` SHA-256: `{sha(TASK / 'human-gate.yaml')}`."])
    for name, digest in summary["parameter_file_sha256"].items():
        lines.append(f"- `{name}` SHA-256: `{digest}`")
    lines.extend(["", f"- Solver: `{summary['solver_path']}`; SHA-256 `{summary['solver_sha256']}`.",
                  f"- Solver version: `{summary['solver_version'].splitlines()[-1]}`.",
                  f"- josim-plot2 SHA-256: `{summary['plotter_sha256']}`; shared Plotly asset SHA-256: `{summary['plotly_asset_sha256']}`.",
                  f"- Local submit.py SHA-256: `{summary['local_submit_script_sha256']}`; submit.sh SHA-256: `{summary['local_submit_wrapper_sha256']}`.",
                  f"- Legacy CB_CARRY_BUFFER_ALL render-only deck matches A027: `{summary['legacy_cb_carry_buffer_all_render_byte_identical_to_A027']}`; terminal render-only QA: `{summary['terminal_mode_render_only']}`.",
                  "- JoSIM `-s` syntax/model parse is static only; it does not execute transient solves.",
                  "- Prohibited: second Carry sJTL, clock later than 210p, parameter sweep, repeated 50ps clock, bit decode, or follow-up solve.",
                  "- After the four valid runs and evidence package: STOP / AWAITING_SCIENTIFIC_REVIEW.", ""])
    return "\n".join(lines)


def _probe_registry(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        raise RuntimeError("cannot freeze an empty probe registry")
    signals = rows[0]["probe_manifest"]["signals"]
    for row in rows[1:]:
        if row["probe_manifest"]["signals"] != signals:
            raise RuntimeError(f"registered run probe set differs: {row['run_id']}")
    return {"schema": "bvm4x4-carry-post-cb-sjtl-probe-registry-v1",
            "batch_id": BATCH_ID, "authorized_run_ids": [row["run_id"] for row in rows],
            "signal_count": len(signals), "signals": signals,
            "per_run_deck_sha256": {row["run_id"]: row["deck_sha256"] for row in rows},
            "per_run_stimulus_sha256": {row["run_id"]: row["stimulus_sha256"] for row in rows},
            "plot_pages": rows[0]["plot_pages"],
            "dout_semantics": "shared DOUT/JOIN voltage; current attribution uses I(V_CBU_A_Dk)",
            "raw_phase_unit": "radians", "scientific_interpretation_performed": False}


def prepare_preflight() -> int:
    _assert_batch_ids_free()
    rows, static = _render_and_validate(run_syntax=True)
    static["preflight_revision"] = 1
    manifest = jread(EXPERIMENT_MANIFEST)
    auth_batches = manifest.setdefault("authorization_batches", [])
    if any(item.get("batch_id") == BATCH_ID for item in auth_batches):
        raise RuntimeError(f"authorization already registered: {BATCH_ID}")
    run_ids = [item[0] for item in platform.CARRY_POST_CB_SJTL_RUN_MATRIX]
    presets = [item[1] for item in platform.CARRY_POST_CB_SJTL_RUN_MATRIX]
    auth_batches.append({"batch_id": BATCH_ID, "risk_level": "NORMAL",
                         "authorized_cases": presets, "run_ids": run_ids,
                         "authorized_physical_solve_count": 4,
                         "physical_solve_count_completed": 0,
                         "preflight_revision": 1,
                         "preflight_parent_head": BASE_HEAD,
                         "preflight_path": PREFLIGHT.relative_to(SERIES).as_posix(),
                         "scientific_interpretation_performed": False,
                         "automatic_follow_up": False})
    authorized = manifest.setdefault("authorized_physical_solves", [])
    for preset in presets:
        if preset not in authorized:
            authorized.append(preset)
    manifest["maximum_physical_solve_count"] = max(int(manifest.get("maximum_physical_solve_count", 0)), 33)
    TASK.mkdir(parents=True, exist_ok=True)
    jnew(STATIC_QA, static)
    probe_registry = _probe_registry(rows)
    jnew(PROBE_REGISTRY, probe_registry)
    jreplace(EXPERIMENT_MANIFEST, manifest)
    preflight_text = _render_preflight(static)
    if PREFLIGHT.exists():
        raise FileExistsError(f"refusing to overwrite preflight: {PREFLIGHT}")
    PREFLIGHT.parent.mkdir(parents=True, exist_ok=True)
    PREFLIGHT.write_text(preflight_text, encoding="utf-8")
    work_unit = {"schema": "bvm4x4-carry-post-cb-sjtl-work-unit-v1", "batch_id": BATCH_ID,
                 "preflight_attempt": 1,
                 "experiment_risk_level": "NORMAL", "parent_head_at_preflight": BASE_HEAD,
                 "authorized_run_ids": run_ids, "authorized_presets": presets,
                 "physical_solve_count_authorized": 4, "physical_solve_count_completed_at_preflight": 0,
                 "preflight_path": PREFLIGHT.relative_to(SERIES).as_posix(),
                 "preflight_sha256": sha(PREFLIGHT), "static_qa_path": STATIC_QA.relative_to(SERIES).as_posix(),
                 "static_qa_sha256": sha(STATIC_QA), "probe_manifest_path": PROBE_REGISTRY.relative_to(SERIES).as_posix(),
                 "probe_manifest_sha256": sha(PROBE_REGISTRY),
                 "experiment_yaml_sha256": sha(TASK / "experiment.yaml"),
                 "metric_spec_sha256": sha(TASK / "METRIC_SPEC.json"),
                 "human_gate_sha256": sha(TASK / "human-gate.yaml"),
                 "experiment_manifest_sha256": sha(EXPERIMENT_MANIFEST),
                 "platform_runner_sha256": sha(Path(platform.__file__).resolve()),
                 "batch_runner_sha256": sha(Path(__file__).resolve()),
                 "analysis_runner_sha256": sha(ANALYZER),
                 "local_submit_script_sha256": static["local_submit_script_sha256"],
                 "local_submit_wrapper_sha256": static["local_submit_wrapper_sha256"],
                 "platform_test_sha256": static["platform_test_sha256"],
                 "submit_test_sha256": static["submit_test_sha256"],
                 "parameter_file_sha256": static["parameter_file_sha256"],
                 "baseline_raw_sha256": BASELINE_RAW,
                 "execution_order": ["A030", "A031", "A032", "A033"],
                 "failure_gate": "stop on solver or artifact/mechanical hard failure; do not classify functional outcome here",
                 "automatic_follow_up": False, "scientific_interpretation_performed": False,
                 "next_action": "COMMIT_LOCKED_PREFLIGHT_THEN_RUN_EXACTLY_A030_A033_AND_STOP"}
    jnew(WORK_UNIT, work_unit)
    batch = {"schema": "bvm4x4-carry-post-cb-sjtl-batch-v1", "batch_id": BATCH_ID,
             "status": "PREFLIGHT_PASS_READY", "preflight_revision": 1, "preflight_parent_head": BASE_HEAD,
             "preflight_path": PREFLIGHT.relative_to(SERIES).as_posix(), "preflight_sha256": sha(PREFLIGHT),
             "static_qa_path": STATIC_QA.relative_to(SERIES).as_posix(), "static_qa_sha256": sha(STATIC_QA),
             "work_unit_path": WORK_UNIT.relative_to(SERIES).as_posix(), "work_unit_sha256": sha(WORK_UNIT),
             "authorized_run_ids": run_ids, "runs": [], "physical_solve_count_authorized": 4,
             "physical_solve_count_completed": 0, "analysis_path": None,
             "scientific_interpretation_performed": False, "automatic_follow_up": False}
    jnew(BATCH_MANIFEST, batch)
    print(json.dumps({"status": "PREFLIGHT_PASS_READY", "batch_id": BATCH_ID,
                      "parent_head": BASE_HEAD, "physical_solve_count": 0,
                      "authorized_run_ids": run_ids,
                      "probe_count_per_run": [row["probe_count"] for row in rows],
                      "raw_estimate_bytes": [row["raw_estimate_bytes"] for row in rows],
                      "joSIM_static_parse": [row["josim_static_parse"]["status"] for row in static["cases"]],
                      "preflight_sha256": sha(PREFLIGHT)}, ensure_ascii=False, indent=2))
    return 0


def refresh_preflight() -> int:
    """Supersede a pre-solve lock only when no authorized run has started."""
    if not BATCH_MANIFEST.is_file() or not EXPERIMENT_MANIFEST.is_file():
        raise RuntimeError("cannot refresh: initial preflight/batch registration is missing")
    old_batch = jread(BATCH_MANIFEST)
    manifest = jread(EXPERIMENT_MANIFEST)
    authorization = [item for item in manifest.get("authorization_batches", [])
                     if item.get("batch_id") == BATCH_ID]
    if (len(authorization) != 1 or old_batch.get("status") != "PREFLIGHT_PASS_READY" or
            old_batch.get("physical_solve_count_completed") != 0 or
            any((RUNS / run_id).exists() for run_id in [item[0] for item in platform.CARRY_POST_CB_SJTL_RUN_MATRIX]) or
            int(manifest.get("physical_solve_count", -1)) != 29):
        raise RuntimeError("preflight refresh is allowed only before any A030-A033 run or physical solve")
    previous_attempt = int(old_batch.get("preflight_revision", 1))
    next_attempt = previous_attempt + 1
    attempt_dir = TASK / "attempts" / f"{previous_attempt:03d}"
    if attempt_dir.exists():
        raise FileExistsError(f"refusing to overwrite prior preflight attempt: {attempt_dir}")
    attempt_dir.mkdir(parents=True, exist_ok=False)
    saved = {}
    for path in (PREFLIGHT, STATIC_QA, WORK_UNIT, PROBE_REGISTRY, BATCH_MANIFEST):
        if not path.is_file():
            raise RuntimeError(f"cannot archive incomplete previous preflight attempt: {path}")
        target = attempt_dir / path.name
        shutil.copy2(path, target)
        saved[path.name] = {"path": target.relative_to(SERIES).as_posix(), "sha256": sha(target)}
    attempt_record = {"schema": "bvm4x4-carry-post-cb-sjtl-preflight-attempt-v1",
                      "attempt": previous_attempt, "status": "SUPERSEDED_BEFORE_SOLVE",
                      "reason": "A read-only implementation review corrected analyzer/probe metadata and DELTA closure before any A030-A033 solve; this preflight snapshot is preserved as superseded.",
                      "physical_solve_count": 0, "authorized_run_directories_created": False,
                      "archived_files": saved, "scientific_interpretation_performed": False}
    jnew(attempt_dir / "ATTEMPT_MANIFEST.json", attempt_record)

    rows, static = _render_and_validate(run_syntax=True)
    static["preflight_revision"] = next_attempt
    jreplace(STATIC_QA, static)
    probe_registry = _probe_registry(rows)
    jreplace(PROBE_REGISTRY, probe_registry)
    authorization[0].update({"preflight_revision": next_attempt,
                             "preflight_path": PREFLIGHT.relative_to(SERIES).as_posix(),
                             f"preflight_attempt_{previous_attempt:03d}_manifest": (attempt_dir / "ATTEMPT_MANIFEST.json").relative_to(SERIES).as_posix(),
                             f"preflight_attempt_{previous_attempt:03d}_sha256": sha(attempt_dir / "ATTEMPT_MANIFEST.json")})
    jreplace(EXPERIMENT_MANIFEST, manifest)
    preflight_text = _render_preflight(static)
    PREFLIGHT.write_text(preflight_text, encoding="utf-8")
    run_ids = [item[0] for item in platform.CARRY_POST_CB_SJTL_RUN_MATRIX]
    presets = [item[1] for item in platform.CARRY_POST_CB_SJTL_RUN_MATRIX]
    work_unit = {"schema": "bvm4x4-carry-post-cb-sjtl-work-unit-v1", "batch_id": BATCH_ID,
                 "preflight_attempt": next_attempt, "experiment_risk_level": "NORMAL",
                 "parent_head_at_preflight": BASE_HEAD, "authorized_run_ids": run_ids,
                 "authorized_presets": presets, "physical_solve_count_authorized": 4,
                 "physical_solve_count_completed_at_preflight": 0,
                 "preflight_path": PREFLIGHT.relative_to(SERIES).as_posix(), "preflight_sha256": sha(PREFLIGHT),
                 "static_qa_path": STATIC_QA.relative_to(SERIES).as_posix(), "static_qa_sha256": sha(STATIC_QA),
                 "probe_manifest_path": PROBE_REGISTRY.relative_to(SERIES).as_posix(),
                 "probe_manifest_sha256": sha(PROBE_REGISTRY),
                 "experiment_yaml_sha256": sha(TASK / "experiment.yaml"),
                 "metric_spec_sha256": sha(TASK / "METRIC_SPEC.json"),
                 "human_gate_sha256": sha(TASK / "human-gate.yaml"),
                 "experiment_manifest_sha256": sha(EXPERIMENT_MANIFEST),
                 "platform_runner_sha256": sha(Path(platform.__file__).resolve()),
                 "batch_runner_sha256": sha(Path(__file__).resolve()),
                 "analysis_runner_sha256": sha(ANALYZER),
                 "local_submit_script_sha256": static["local_submit_script_sha256"],
                 "local_submit_wrapper_sha256": static["local_submit_wrapper_sha256"],
                 "platform_test_sha256": static["platform_test_sha256"],
                 "submit_test_sha256": static["submit_test_sha256"],
                 "parameter_file_sha256": static["parameter_file_sha256"],
                 "baseline_raw_sha256": BASELINE_RAW,
                 "execution_order": ["A030", "A031", "A032", "A033"],
                 "failure_gate": "stop on solver or artifact/mechanical hard failure; no physical classification",
                 "supersedes_preflight_attempt": previous_attempt,
                 "superseded_attempt_manifest_sha256": sha(attempt_dir / "ATTEMPT_MANIFEST.json"),
                 "automatic_follow_up": False, "scientific_interpretation_performed": False,
                 "next_action": "COMMIT_LOCKED_PREFLIGHT_THEN_RUN_EXACTLY_A030_A033_AND_STOP"}
    jreplace(WORK_UNIT, work_unit)
    batch = {"schema": "bvm4x4-carry-post-cb-sjtl-batch-v1", "batch_id": BATCH_ID,
             "status": "PREFLIGHT_PASS_READY", "preflight_revision": next_attempt,
             "superseded_preflight_attempt": previous_attempt,
             "superseded_attempt_manifest_path": (attempt_dir / "ATTEMPT_MANIFEST.json").relative_to(SERIES).as_posix(),
             "superseded_attempt_manifest_sha256": sha(attempt_dir / "ATTEMPT_MANIFEST.json"),
             "preflight_parent_head": BASE_HEAD, "preflight_path": PREFLIGHT.relative_to(SERIES).as_posix(),
             "preflight_sha256": sha(PREFLIGHT), "static_qa_path": STATIC_QA.relative_to(SERIES).as_posix(),
             "static_qa_sha256": sha(STATIC_QA), "work_unit_path": WORK_UNIT.relative_to(SERIES).as_posix(),
             "work_unit_sha256": sha(WORK_UNIT), "authorized_run_ids": run_ids, "runs": [],
             "physical_solve_count_authorized": 4, "physical_solve_count_completed": 0,
             "scientific_interpretation_performed": False, "automatic_follow_up": False}
    jreplace(BATCH_MANIFEST, batch)
    print(json.dumps({"status": "PREFLIGHT_PASS_READY", "preflight_revision": next_attempt,
                      "superseded_attempt": previous_attempt, "physical_solve_count": 0,
                      "preflight_sha256": sha(PREFLIGHT), "authorized_run_ids": run_ids,
                      "probe_count_per_run": [row["probe_count"] for row in rows],
                      "raw_estimate_bytes": [row["raw_estimate_bytes"] for row in rows],
                      "joSIM_static_parse": [row["josim_static_parse"]["status"] for row in static["cases"]]},
                     ensure_ascii=False, indent=2))
    return 0


def _verify_locked_preflight() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    if git("status", "--porcelain"):
        raise RuntimeError("A030-A033 execution requires a committed, clean preflight worktree")
    unit, qa, batch = jread(WORK_UNIT), jread(STATIC_QA), jread(BATCH_MANIFEST)
    ancestor = subprocess.run(["git", "merge-base", "--is-ancestor", BASE_HEAD, "HEAD"],
                             cwd=REPO, check=False)
    if ancestor.returncode:
        raise RuntimeError(f"locked preflight parent {BASE_HEAD} is not an ancestor of HEAD")
    if (qa.get("status") != "PASS" or batch.get("status") != "PREFLIGHT_PASS_READY" or
            unit.get("authorized_run_ids") != [row[0] for row in platform.CARRY_POST_CB_SJTL_RUN_MATRIX] or
            unit.get("physical_solve_count_authorized") != 4 or batch.get("physical_solve_count_completed") != 0):
        raise RuntimeError("locked preflight does not authorize exactly A030-A033")
    for path, expected in ((PREFLIGHT, unit["preflight_sha256"]),
                           (STATIC_QA, unit["static_qa_sha256"]),
                           (PROBE_REGISTRY, unit["probe_manifest_sha256"]),
                           (WORK_UNIT, batch.get("work_unit_sha256", "")),
                           (TASK / "experiment.yaml", unit["experiment_yaml_sha256"]),
                           (TASK / "METRIC_SPEC.json", unit["metric_spec_sha256"]),
                           (TASK / "human-gate.yaml", unit["human_gate_sha256"]),
                           (EXPERIMENT_MANIFEST, unit["experiment_manifest_sha256"])):
        if sha(path) != expected:
            raise RuntimeError(f"preflight-bound input changed: {path.relative_to(SERIES)}")
    parameter_paths = {"USER_CASE.env": platform.USER_CASE, "STIMULUS.env": platform.STIMULUS,
                       "T1_PARAMS.env": platform.T1_PARAMS, "CBU_PARAMS.env": platform.CBU_PARAMS,
                       "DFF_PARAMS.env": platform.DFF_PARAMS, "D0_JTL_PARAMS.env": platform.D0_JTL_PARAMS}
    parameter_paths.update({f"presets/{preset}.env": SERIES / "presets" / f"{preset}.env"
                            for _, preset, *_ in platform.CARRY_POST_CB_SJTL_RUN_MATRIX})
    if {name: sha(path) for name, path in parameter_paths.items()} != unit["parameter_file_sha256"]:
        raise RuntimeError("preflight-bound environment/preset configuration changed")
    for path, expected in ((Path(platform.__file__).resolve(), unit["platform_runner_sha256"]),
                           (Path(__file__).resolve(), unit["batch_runner_sha256"]),
                           (ANALYZER, unit["analysis_runner_sha256"]),
                           (SERIES / "scripts" / "submit.py", unit["local_submit_script_sha256"]),
                           (SERIES / "submit.sh", unit["local_submit_wrapper_sha256"]),
                           (SERIES / "tests" / "test_platform.py", unit["platform_test_sha256"]),
                           (SERIES / "tests" / "test_submit.py", unit["submit_test_sha256"])):
        if sha(path) != expected:
            raise RuntimeError(f"preflight-bound runner changed: {path.relative_to(REPO)}")
    return unit, qa, batch


def run_batch() -> int:
    unit, qa, batch = _verify_locked_preflight()
    _verify_baselines()
    solver_info = platform._solver_info()
    if solver_info["parent_head"] != git("rev-parse", "HEAD"):
        raise RuntimeError("solver parent HEAD changed during batch startup")
    for index, (run_id, preset, _rows, _cols, _clock, _reference) in enumerate(
            platform.CARRY_POST_CB_SJTL_RUN_MATRIX):
        case, stimulus, params = platform.load_config(preset)
        rendered = platform.render(case, stimulus, params, RUNS / run_id)
        locked = next(item for item in qa["cases"] if item["run_id"] == run_id)
        deck_sha = hashlib.sha256(rendered["deck"].encode()).hexdigest()
        stimulus_sha = hashlib.sha256(rendered["stimulus_text"].encode()).hexdigest()
        if (deck_sha != locked["deck_sha256"] or stimulus_sha != locked["stimulus_sha256"] or
                rendered["probes"]["signal_count"] != locked["probe_count"] or
                rendered["static_qa"].get("status") != "PASS"):
            raise RuntimeError(f"locked rendered input differs before solve: {run_id}")
        if (RUNS / run_id).exists() or any(item.get("run_id") == run_id
                                           for item in jread(EXPERIMENT_MANIFEST).get("runs", [])):
            raise RuntimeError(f"run ID became occupied; refusing overwrite: {run_id}")
        print(f"START {run_id} ({index+1}/4), clock={case['T1_CHAIN_CLK_START']}", flush=True)
        code, result = platform.run_one(
            case, stimulus, params, solver_info, batch_id=BATCH_ID, run_id_override=run_id,
            rendered_override=rendered, preflight_path=PREFLIGHT,
            metric_spec_path_override=TASK / "METRIC_SPEC.json", expected_deck_sha256=locked["deck_sha256"])
        print(json.dumps(result, ensure_ascii=False), flush=True)
        batch = jread(BATCH_MANIFEST)
        batch["physical_solve_count_completed"] = index + 1
        batch["execution_source_head"] = solver_info["parent_head"]
        batch["runs"].append({"run_id": run_id, "status": result.get("status"),
                              "artifact_status": result.get("artifact_status"),
                              "physical_solve_count": result.get("physical_solve_count", 1),
                              "raw_sha256": result.get("raw_sha256"), "raw_bytes": result.get("raw_bytes"),
                              "deck_sha256": result.get("deck_sha256"), "solver_exit_code": result.get("solver_exit_code")})
        jreplace(BATCH_MANIFEST, batch)
        if code != 0:
            batch["status"] = "STOPPED_HARD_FAILURE"
            batch["stop_reason"] = "solver or post-solve artifact/mechanical QA failure; no retries or later runs"
            jreplace(BATCH_MANIFEST, batch)
            print(f"STOP: hard failure at {run_id}; remaining authorized cases were not run.", file=sys.stderr)
            return code

    from analyze_carry_post_cb_sjtl import analyze_batch
    analysis = analyze_batch()
    batch = jread(BATCH_MANIFEST)
    batch.update({"status": "MECHANICAL_QA_PASS_AWAITING_USER_REVIEW",
                  "analysis_path": (TASK / "CARRY_POST_CB_SJTL_SUMMARY.json").relative_to(SERIES).as_posix(),
                  "analysis_sha256": sha(TASK / "CARRY_POST_CB_SJTL_SUMMARY.json"),
                  "analysis_status": analysis["status"], "scientific_interpretation_performed": False,
                  "automatic_follow_up": False, "next_action": "STOP_AWAITING_USER_AND_CHATGPT_REVIEW"})
    jreplace(BATCH_MANIFEST, batch)
    manifest = jread(EXPERIMENT_MANIFEST)
    authorization = [item for item in manifest.get("authorization_batches", []) if item.get("batch_id") == BATCH_ID]
    if len(authorization) != 1:
        raise RuntimeError("experiment manifest lost or duplicated current batch authorization")
    authorization[0]["physical_solve_count_completed"] = batch["physical_solve_count_completed"]
    authorization[0]["execution_source_head"] = solver_info["parent_head"]
    authorization[0]["batch_manifest_sha256"] = sha(BATCH_MANIFEST)
    authorization[0]["summary_sha256"] = sha(TASK / "CARRY_POST_CB_SJTL_SUMMARY.json")
    jreplace(EXPERIMENT_MANIFEST, manifest)
    print(json.dumps({"status": batch["status"], "physical_solve_count_completed": 4,
                      "run_ids": [item["run_id"] for item in batch["runs"]],
                      "summary_sha256": batch["analysis_sha256"], "scientific_interpretation_performed": False,
                      "automatic_follow_up": False}, ensure_ascii=False, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--prepare-preflight", action="store_true")
    group.add_argument("--refresh-preflight", action="store_true",
                       help="supersede a pre-solve preflight attempt only when no A030-A033 solve has started")
    group.add_argument("--run-batch", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.prepare_preflight:
            return prepare_preflight()
        if args.refresh_preflight:
            return refresh_preflight()
        return run_batch()
    except (OSError, RuntimeError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
