#!/usr/bin/env python3
"""Locked preflight and exactly-two-run executor for the bounded D3 timing batch."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import diagonal_platform as platform

SERIES = platform.SERIES
REPO = platform.REPO
RUNS = platform.RUNS
TASK = platform.CARRY_D3_TIMING_ANALYSIS
MANIFEST = platform.EXPERIMENT_MANIFEST
BASELINE = "A036_PRE_CB_SJTL_ALL_200"
BASELINE_RAW_SHA256 = "586ba6eafa62d25bf6cd7a7ea8b533903826616b4b5575a9023f7393b74faf75"
START_HEAD = "d7089ace75f1450b0f48c76762373c8d105d4549"
RUN_MATRIX = (
    ("A040_D3_PRE_CB_SJTL_0_ALL_200", "D3_PRE_CB_SJTL_0_ALL_200", "1,1,0,1,1,1", "110111"),
    ("A041_D3_PRE_CB_SJTL_2_ALL_200", "D3_PRE_CB_SJTL_2_ALL_200", "1,1,2,1,1,1", "111111"),
)
HISTORICAL_MATRIX = (
    *platform.CB_CARRY_BUFFER_ALL_RUN_MATRIX,
    *((row[0], row[1], row[2], row[3]) for row in platform.CARRY_POST_CB_SJTL_RUN_MATRIX),
    *((row[0], row[1], row[2], row[3]) for row in platform.CARRY_SJTL_POSITION_RUN_MATRIX),
)
STATIC_SUBCKTS = ("THmitll_MERGE", "THmitll_DFF", "D0_JTL", "T1", "BVM", "BQ", "sJTL", "CB")
FILES = {
    "experiment": TASK / "experiment.yaml",
    "preflight": TASK / "PREFLIGHT.md",
    "static": TASK / "STATIC_QA.json",
    "work_unit": TASK / "WORK_UNIT.json",
    "metric_spec": TASK / "METRIC_SPEC.json",
    "probes": TASK / "PROBE_MANIFEST.json",
    "batch": TASK / "BATCH_MANIFEST.json",
}


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def git(*args: str, check: bool = True) -> str:
    return subprocess.run(["git", *args], cwd=REPO, text=True, capture_output=True,
                          check=check).stdout.strip()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_new(path: Path, data: Any) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite locked preflight artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    text = data if isinstance(data, str) else json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    path.write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8")


def _historical_raws() -> dict[str, dict[str, Any]]:
    manifest = read_json(MANIFEST)
    records = {item.get("run_id"): item for item in manifest.get("runs", [])}
    output: dict[str, dict[str, Any]] = {}
    for run_id, *_ in HISTORICAL_MATRIX:
        run_dir = RUNS / run_id
        raw = run_dir / "raw.csv"
        if not raw.is_file():
            raise RuntimeError(f"historical raw missing; stop without mutation: {run_id}")
        digest = sha(raw)
        result = read_json(run_dir / "result.json")
        metadata = read_json(run_dir / "metadata.json")
        qa = read_json(run_dir / "qa.json")
        chain_qa = read_json(run_dir / "chain_qa.json")
        if (digest != result.get("raw_sha256") or digest != metadata.get("raw_sha256") or
                digest != records.get(run_id, {}).get("raw_sha256") or
                result.get("artifact_status") != "VALID" or qa.get("status") != "PASS" or
                chain_qa.get("status") != "PASS" or
                chain_qa.get("raw_sha256_after_analysis") != digest):
            raise RuntimeError(f"historical run evidence identity/QA mismatch: {run_id}")
        output[run_id] = {"raw_path": raw.relative_to(SERIES).as_posix(), "raw_sha256": digest,
                          "raw_bytes": raw.stat().st_size, "physical_solve_count": 0}
    if output[BASELINE]["raw_sha256"] != BASELINE_RAW_SHA256:
        raise RuntimeError("A036 raw SHA differs from the preregistered immutable baseline")
    return output


def _historical_render_regression() -> list[dict[str, Any]]:
    records = []
    seen = set()
    for run_id, preset, *_ in HISTORICAL_MATRIX:
        if run_id in seen:
            continue
        seen.add(run_id)
        case, stimulus, params = platform.load_config(preset)
        rendered = platform.render(case, stimulus, params, RUNS / "_D3_TIMING_RENDER_ONLY")
        run_dir = RUNS / run_id
        deck_path, stimulus_path = run_dir / "deck.cir", run_dir / "stimulus.inc"
        saved_probe = read_json(run_dir / "probe_manifest.json")
        actual_labels = [item["label"] for item in rendered["probes"]["signals"]]
        saved_labels = [item["label"] for item in saved_probe["signals"]]
        if (rendered["static_qa"].get("status") != "PASS" or
                rendered["deck"] != deck_path.read_text(encoding="utf-8") or
                rendered["stimulus_text"] != stimulus_path.read_text(encoding="utf-8") or
                actual_labels != saved_labels):
            raise RuntimeError(f"historical render regression mismatch: {run_id}")
        records.append({"run_id": run_id, "preset": preset,
                        "deck_sha256": sha(deck_path), "stimulus_sha256": sha(stimulus_path),
                        "probe_signal_count": len(actual_labels), "render_matches": True,
                        "physical_solve_count": 0})
    return records


def _baseline_parameters() -> dict[str, str]:
    baseline = RUNS / BASELINE
    values = {}
    for filename in ("T1_PARAMS.snapshot.env", "CBU_PARAMS.snapshot.env", "DFF_PARAMS.snapshot.env",
                     "D0_JTL_PARAMS.snapshot.env"):
        values.update(platform.parse_env(baseline / filename))
    return values


def _syntax_qa(rendered: dict[str, Any], run_id: str) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix=f".d3-carry-{run_id}-", dir=RUNS) as temp_name:
        temp = Path(temp_name)
        (temp / "deck.cir").write_text(rendered["deck"], encoding="utf-8")
        (temp / "stimulus.inc").write_text(rendered["stimulus_text"], encoding="utf-8")
        t1_path = temp / "sources" / "t1_cell_tunable.cir"
        t1_path.parent.mkdir(parents=True, exist_ok=True)
        t1_path.write_text(rendered["t1_source_text"], encoding="utf-8")
        for relative, content in rendered["chain_source_texts"].items():
            target = temp / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        command = [str(platform.SOLVER)]
        for name in STATIC_SUBCKTS:
            command.extend(("-s", name))
        command.append(str(temp / "deck.cir"))
        proc = subprocess.run(command, cwd=temp, capture_output=True, text=True, check=False)
        combined = proc.stdout + proc.stderr
        if proc.returncode:
            raise RuntimeError(f"JoSIM syntax check failed for {run_id}: {combined[-2000:]}")
        meaningful = [line.strip() for line in combined.splitlines() if line.strip()]
        return {"status": "PASS", "exit_code": proc.returncode,
                "stdout_stderr_sha256": hashlib.sha256(combined.encode()).hexdigest(),
                "output_line_count": len(meaningful), "output_tail": meaningful[-8:]}


def _normalized_deck(deck: str, *, exclude_d3_branch: bool) -> list[str]:
    output = []
    d3_prefixes = ("V_CBU_A_D3 ", "V_CARRY_IN_D3 ", "XCB_CARRY_D3 ", "V_CBU_B_D3 ",
                   "V_CARRY_SJTL_IN_D3 ", "V_CARRY_SJTL_OUT_D3 ", "V_CARRY_SJTL_LINK_D3_",
                   "XSJTL_CARRY_D3", "V_T1_LINK_D3 ")
    for line in deck.splitlines():
        if line.startswith("*") or line.startswith(".print "):
            continue
        if exclude_d3_branch and line.startswith(d3_prefixes):
            continue
        output.append(line)
    return output


def _prepare_records(*, run_syntax: bool) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    baseline_dir = RUNS / BASELINE
    baseline_case = read_json(baseline_dir / "case_manifest.json")["case"]
    baseline_stimulus = read_json(baseline_dir / "case_manifest.json")["stimulus"]
    baseline_params = _baseline_parameters()
    baseline_deck = (baseline_dir / "deck.cir").read_text(encoding="utf-8")
    baseline_stim_text = (baseline_dir / "stimulus.inc").read_text(encoding="utf-8")
    case_records = []
    rendered_map = {}
    allowed_case_differences = {"CASE", "CARRY_SJTL_STAGE_MASK", "CARRY_SJTL_COUNT_BY_STAGE", "FOCUS_STAGE"}
    for run_id, preset, counts, mask in RUN_MATRIX:
        case, stimulus, params = platform.load_config(preset)
        rendered = platform.render(case, stimulus, params, RUNS / run_id)
        differences = sorted(key for key in set(case) | set(baseline_case)
                             if case.get(key) != baseline_case.get(key) and key not in allowed_case_differences)
        if differences:
            raise RuntimeError(f"unregistered circuit/stimulus parameter changes vs A036 in {run_id}: {differences}")
        if stimulus != baseline_stimulus or params != baseline_params:
            raise RuntimeError(f"stimulus or T1/CBU/DFF/D0-JTL physical parameters differ from A036: {run_id}")
        if case["CARRY_SJTL_COUNT_BY_STAGE"] != counts or case["CARRY_SJTL_STAGE_MASK"] != mask:
            raise RuntimeError(f"registered D1-D6 sJTL counts/mask differ: {run_id}")
        if (case["ROW_BITS"], case["COL_BITS"], case["SE_ENABLE_MASK"], case["DT"], case["STOP"],
                case["T1_CHAIN_CLK_START"], case["CARRY_SJTL_POSITION"]) != (
                "1111", "1111", "ALL", "0.01p", "300p", "200p", "PRE_CB"):
            raise RuntimeError(f"frozen mask, timing, or position differs: {run_id}")
        if rendered["static_qa"].get("status") != "PASS":
            raise RuntimeError(f"platform static QA failed: {run_id}")
        if rendered["stimulus_text"] != baseline_stim_text:
            raise RuntimeError(f"PWL stimulus changed from A036: {run_id}")
        if _normalized_deck(rendered["deck"], exclude_d3_branch=True) != _normalized_deck(
                baseline_deck, exclude_d3_branch=True):
            raise RuntimeError(f"deck differs from A036 outside D3 Carry branch/probe print directives: {run_id}")
        deck_lines = rendered["deck"].splitlines()
        branch = set(platform._carry_buffer_stage_lines(case, 3))
        actual_branch = {line for line in deck_lines if line.startswith((
            "V_CBU_A_D3 ", "V_CARRY_IN_D3 ", "XCB_CARRY_D3 ", "V_CBU_B_D3 ",
            "V_CARRY_SJTL_IN_D3 ", "V_CARRY_SJTL_OUT_D3 ", "V_CARRY_SJTL_LINK_D3_",
            "XSJTL_CARRY_D3", "V_T1_LINK_D3 "))}
        if branch != actual_branch:
            raise RuntimeError(f"D3 branch connection set differs from its registered count: {run_id}")
        sjtl_instances = [line for line in deck_lines if line.startswith("XSJTL_CARRY_D3")]
        expected_count = int(counts.split(",")[2])
        if len(sjtl_instances) != expected_count:
            raise RuntimeError(f"D3 carry sJTL instance count mismatch: {run_id}")
        if sum(line.startswith("XCB_CARRY_D3 ") for line in deck_lines) != 1:
            raise RuntimeError(f"D3 must retain exactly one Carry CB_0928: {run_id}")
        if any(line.startswith("R_TERM_D3") or line.startswith("R_C_D3") for line in deck_lines):
            raise RuntimeError(f"D3 must not have a DOUT/Carry parallel load: {run_id}")
        syntax = _syntax_qa(rendered, run_id) if run_syntax else {"status": "NOT_RUN"}
        plot_pages = platform.plot_signals(rendered["probes"])
        record = {"run_id": run_id, "preset": preset,
                  "case_sha256": hashlib.sha256(json.dumps(case, sort_keys=True).encode()).hexdigest(),
                  "stimulus_sha256": hashlib.sha256(rendered["stimulus_text"].encode()).hexdigest(),
                  "deck_sha256": hashlib.sha256(rendered["deck"].encode()).hexdigest(),
                  "probe_manifest_sha256": hashlib.sha256(
                      (json.dumps(rendered["probes"], ensure_ascii=False, indent=2) + "\n").encode()).hexdigest(),
                  "probe_count": rendered["probes"]["signal_count"],
                  "carry_sjtl_count_by_stage": {f"D{i}": platform._carry_sjtl_count_at(case, i)
                                                for i in range(1, 7)},
                  "carry_sjtl_instances": [line.split()[0] for line in deck_lines
                                           if line.startswith("XSJTL_CARRY_D")],
                  "plot_page_schema": [{"file": page["file"], "signals": page["signals"]}
                                       for page in plot_pages],
                  "static_qa": rendered["static_qa"], "syntax_qa": syntax,
                  "physical_solve_count": 0}
        case_records.append(record)
        rendered_map[run_id] = {"case": case, "stimulus": stimulus, "params": params,
                                "rendered": rendered}
    return case_records, rendered_map


def _render_raw_projection(raw: Path, added_probes: int) -> dict[str, Any]:
    baseline = RUNS / BASELINE / "raw.csv"
    baseline_size = baseline.stat().st_size
    samples, total_chars, max_value_chars = 0, 0, 0
    import csv
    with baseline.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.reader(stream)
        header = next(reader)
        signal_count = len(header) - 1
        for row in reader:
            samples += 1
            lengths = [len(value) for value in row[1:]]
            total_chars += sum(lengths)
            max_value_chars = max(max_value_chars, max(lengths, default=0))
    mean_chars = total_chars / max(1, samples * signal_count)
    average_projection = math.ceil(baseline_size + samples * added_probes * (mean_chars + 1))
    conservative_projection = math.ceil(baseline_size + samples * added_probes * (max_value_chars + 1) + 2048)
    if conservative_projection >= platform.MAX_RAW_BYTES:
        raise RuntimeError(f"conservative raw projection reaches storage guard: {conservative_projection}")
    return {"reference_run": BASELINE, "reference_raw_sha256": sha(baseline),
            "reference_raw_bytes": baseline_size, "reference_sample_count": samples,
            "reference_signal_count": signal_count, "added_probe_count": added_probes,
            "mean_numeric_chars_per_value": mean_chars, "max_observed_numeric_chars": max_value_chars,
            "average_projection_bytes": average_projection,
            "conservative_projection_bytes": conservative_projection,
            "projection_method": "A036 raw row count and maximum observed numeric field width plus one delimiter per added probe and 2 KiB header allowance",
            "projection_is_not_solver_output": True}


def prepare_preflight(*, write: bool) -> dict[str, Any]:
    if git("rev-parse", "HEAD") != START_HEAD and subprocess.run(
            ["git", "merge-base", "--is-ancestor", START_HEAD, git("rev-parse", "HEAD")],
            cwd=REPO, check=False).returncode != 0:
        raise RuntimeError(f"preflight HEAD is not descended from the registered start: {START_HEAD}")
    if git("status", "--porcelain"):
        raise RuntimeError("preflight generation requires a clean worktree after the platform/source commit")
    if TASK.exists():
        raise RuntimeError(f"D3 timing task directory already exists; refusing overwrite: {TASK}")
    manifest = read_json(MANIFEST)
    if int(manifest.get("physical_solve_count", -1)) != 39:
        raise RuntimeError("expected exactly 39 completed historical solves before A040/A041")
    existing_ids = {item.get("run_id") for item in manifest.get("runs", [])}
    for run_id, *_ in RUN_MATRIX:
        if (RUNS / run_id).exists() or run_id in existing_ids:
            raise RuntimeError(f"immutable run ID is occupied; refusing overwrite: {run_id}")
    if any(item.get("batch_id") == platform.CARRY_D3_TIMING_BATCH_ID
           for item in manifest.get("authorization_batches", [])):
        raise RuntimeError("D3 timing authorization batch already exists; refusing duplicate registration")
    if set(platform.verify_sources()) != set(platform.SOURCE_SHA256):
        raise RuntimeError("canonical source closure is incomplete")
    history = _historical_raws()
    legacy_render = _historical_render_regression()
    run_records, rendered = _prepare_records(run_syntax=True)
    baseline_probe_count = read_json(RUNS / BASELINE / "static_qa.json")["probe_count"]
    projections = {}
    for record in run_records:
        projections[record["run_id"]] = _render_raw_projection(
            RUNS / record["run_id"] / "raw.csv", record["probe_count"] - baseline_probe_count)
    solver = platform._solver_info()
    plotly_sha = sha(platform.PLOTLY_ASSET)
    source_files = [platform.USER_CASE, platform.STIMULUS, platform.T1_PARAMS,
                    platform.CBU_PARAMS, platform.DFF_PARAMS, platform.D0_JTL_PARAMS,
                    platform.PLOTTER, platform.PLOTLY_ASSET,
                    SERIES / "scripts" / "diagonal_platform.py",
                    SERIES / "scripts" / "d3_carry_timing_batch.py",
                    SERIES / "scripts" / "analyze_d3_carry_timing.py",
                    SERIES / "scripts" / "submit.py",
                    SERIES / "README.md",
                    SERIES / "tests" / "test_platform.py",
                    *(SERIES / "presets" / f"{preset}.env" for _run, preset, *_ in RUN_MATRIX)]
    locked = {path.resolve().relative_to(REPO).as_posix(): sha(path) for path in source_files}
    locked[Path(platform.__file__).resolve().relative_to(REPO).as_posix()] = sha(Path(platform.__file__).resolve())
    raw_hashes = {run_id: item["raw_sha256"] for run_id, item in history.items()}
    windows = {"ARRAY_FINAL_READ": {"interval_ps": [110, 121], "boundary": "[start,end)"},
               "PRE_CLOCK": {"interval_ps": [121, 200], "boundary": "[start,end)"},
               "BEFORE_CLOCK": {"interval_ps": [0, 200], "boundary": "[start,end)"},
               "CLOCK_EDGE": {"interval_ps": [200, 205], "boundary": "[start,end)"},
               "POST_CLOCK": {"interval_ps": [205, 300], "boundary": "[start,end)"},
               "TOTAL": {"interval_ps": [0, 300], "boundary": "[start,end)"}}
    probe_registry = {record["run_id"]: rendered[record["run_id"]]["rendered"]["probes"]
                      for record in run_records}
    experiment = """experiment_id: bvm4x4-d3-carry-timing-a040-a041-20261010
experiment_risk_level: NORMAL
question: Under the frozen A036 15x15 chain and 200 ps global one-shot clock, what raw trajectory differences are observed when only the D3 PRE-CB Carry sJTL count changes from one to zero or two?
source_class: canonical-derived platform with historical A036 comparison
run_set:
  - run_id: A040_D3_PRE_CB_SJTL_0_ALL_200
    preset: D3_PRE_CB_SJTL_0_ALL_200
  - run_id: A041_D3_PRE_CB_SJTL_2_ALL_200
    preset: D3_PRE_CB_SJTL_2_ALL_200
changed: [D3 PRE-CB carry sJTL count only]
frozen: [A036 BVM/QB/array CB/sJTL/T1/DFF parameters, all other Carry stages, shared 400u WL/BL, independent 100u SE, 200p global clock, DT=0.01p, STOP=300p, stimulus]
windows: [ARRAY_FINAL_READ, PRE_CLOCK, BEFORE_CLOCK, CLOCK_EDGE, POST_CLOCK, TOTAL]
visual_authority: scripts/josim-plot2.py; sep_comb; dark; phase rad/(2*pi) navigation only
interpretation_ceiling: mechanical raw arithmetic and descriptive waveform timing only; no event/SFQ classification, mechanism attribution, or product-bit verdict
prohibited_followups: [rerun A036, A038, or A039, parameter changes, sJTL sweep beyond A040/A041, clock changes, automatic next experiment]
scientific_review_authorization: NOT_GRANTED
"""
    preflight_lines = [
        "# BVM 4x4 D3 Carry timing A040/A041 preflight", "",
        "> This experiment is governed by docs/EXPERIMENT_CONTRACT.md.", "",
        f"- Registered start HEAD: `{START_HEAD}`; source/preflight parent HEAD: `{git('rev-parse','HEAD')}`.",
        "- Risk: NORMAL. Exactly two new physical solves are authorized: A040 then A041.",
        "- A036 is a read-only comparison baseline; no A027-A039 raw/deck is modified or recomputed.",
        "- Only the D3 PRE-CB Carry sJTL count changes: 1→0 (A040) and 1→2 (A041). The canonical CB_0928 remains the last physical element before JOIN.",
        "- All non-D3 topology, BVM/QB/CB/sJTL/T1/DFF sources and parameters, PWL stimulus, 400u shared WL/BL, 100u independent SE, 200p global clock, DT and STOP match A036.",
        "- Probes include D3 array last-CB BJ1/BJ2 P/V and DOUT branch current; D2 Carry JJ; each configured D3 PRE-CB sJTL BJ1 P/V and interstage boundary/current; Carry-CB BJ1/BJ2; JOIN currents; T1_D3 B_J1/B_J2/B_J9/B_J10/B_J11 P/V; D4-D6 stage evidence; DFF data/clock/output.",
        "- To control raw size, this task-local focus omits representative external bias-current and clock-series-current traces plus DFF internal JJ/bias/output-load-current traces; all physical bias, clock, and load settings remain unchanged, while clock voltage and DFF data/clock/output voltage plus data-link current are retained.",
        "- A036 lacks D3 T1 B_J2/B_J9/B_J10 probes; those are UNKNOWN for A036 and will be plotted only for A040/A041.",
        "- `P(...)` is radians. Same-JJ phase and voltage-area values use identical stored rows/windows and actual timestamps; no interpolation/resampling.",
        "- DOUT_D3 and CBU_JOIN_D3 share the electrical boundary; DOUT voltage area is not an array-only event count.",
        "- Descriptive local waveform candidates, if present in platform output, are not event classifications. Scientific interpretation: NOT PERFORMED.",
        "- STOP after exact runs, mechanical QA, standard/local comparison plots, DELTA package QA, commit/push and archive handoff.", "",
        "## Run matrix", "", "| Run | D3 sJTL count | D1..D6 counts | Mask | Clock | Deck SHA-256 | Probes | Conservative raw projection |",
        "|---|---:|---|---|---|---|---:|---:|",
    ]
    for record in run_records:
        preflight_lines.append(f"| {record['run_id']} | {record['carry_sjtl_count_by_stage']['D3']} | "
                               f"{','.join(str(record['carry_sjtl_count_by_stage'][f'D{i}']) for i in range(1,7))} | "
                               f"{record['static_qa']['carry_sjtl_stage_mask']} | 200p | `{record['deck_sha256']}` | "
                               f"{record['probe_count']} | {projections[record['run_id']]['conservative_projection_bytes']} B |")
    preflight_lines.extend(["", "## Canonical sources and solver", ""])
    for role, item in platform.verify_sources().items():
        preflight_lines.append(f"- {role}: `{item['path']}` — `{item['sha256']}`")
    preflight_lines.extend([f"- Solver: `{solver['path']}`; SHA-256 `{solver['sha256']}`; version recorded in STATIC_QA.",
                            f"- Shared Plotly asset SHA-256: `{plotly_sha}`.",
                            "- Historical render-only regression covers A027-A039; solver static syntax checks are run only for the two new rendered decks.", ""])
    preflight_text = "\n".join(preflight_lines) + "\n"
    static_qa = {"schema": "bvm4x4-d3-carry-timing-static-qa-v1", "status": "PASS",
                 "parent_head": git("rev-parse", "HEAD"), "registered_start_head": START_HEAD,
                 "solver": solver, "canonical_sources": platform.verify_sources(),
                 "historical_raw_identity": history, "historical_render_only_regression": legacy_render,
                 "new_runs": run_records, "raw_projection": projections,
                 "config_and_tool_sha256": locked, "plotter_sha256": sha(platform.PLOTTER),
                 "plotly_asset_sha256": plotly_sha, "physical_solve_count": 0,
                 "scientific_interpretation_performed": False}
    metric_spec = {"schema": "bvm4x4-d3-carry-timing-metric-spec-v1", "windows": windows,
                   "required_arithmetic": ["P/V same-JJ phase-area arithmetic on identical raw rows",
                                           "positive/negative unwrapped phase variation in radians",
                                           "stored-grid signal extrema and signed areas",
                                           "branch current extrema and charge on actual timestamps"],
                   "phase_unit": "P(...) radians; rad/(2*pi) navigation only",
                   "integration": "trapezoid over actual stored timestamps; no interpolation or resampling",
                   "preexisting_voltage_lobe_candidates": platform.T1_CANDIDATE_MORPHOLOGY_SPEC,
                   "candidate_semantics": "descriptive local waveform extrema only; not switching, event, or SFQ counts",
                   "threshold_or_event_classifier": None, "SFQ_count": "NOT_PERFORMED",
                   "product_bit_decode": "NOT_PERFORMED", "scientific_interpretation_performed": False,
                   "automatic_follow_up": False}
    probes = {"schema": "bvm4x4-d3-carry-timing-probe-manifest-v1",
              "runs": probe_registry, "historical_A036_raw_sha256": BASELINE_RAW_SHA256,
              "raw_phase_unit": "P(...) radians", "interpolation_or_resampling": False,
              "scientific_interpretation_performed": False}
    work_unit = {"schema": "bvm4x4-d3-carry-timing-work-unit-v1",
                 "batch_id": platform.CARRY_D3_TIMING_BATCH_ID,
                 "experiment_risk_level": "NORMAL", "registered_start_head": START_HEAD,
                 "preflight_parent_head": git("rev-parse", "HEAD"),
                 "authorized_run_ids": [item[0] for item in RUN_MATRIX],
                 "authorized_physical_solve_count": 2, "physical_solve_count_completed": 0,
                 "locked_file_sha256": locked, "historical_raw_sha256": raw_hashes,
                 "authorized_matrix": run_records, "no_parameter_sweep": True,
                 "automatic_follow_up": False, "scientific_interpretation_performed": False}
    work_unit["preflight_sha256"] = hashlib.sha256(preflight_text.encode()).hexdigest()
    work_unit["static_qa_sha256"] = hashlib.sha256((json.dumps(static_qa, ensure_ascii=False, indent=2)+"\n").encode()).hexdigest()
    work_unit["metric_spec_sha256"] = hashlib.sha256((json.dumps(metric_spec, ensure_ascii=False, indent=2)+"\n").encode()).hexdigest()
    work_unit["probe_manifest_sha256"] = hashlib.sha256((json.dumps(probes, ensure_ascii=False, indent=2)+"\n").encode()).hexdigest()
    batch = {"schema": "bvm4x4-d3-carry-timing-batch-manifest-v1",
             "batch_id": platform.CARRY_D3_TIMING_BATCH_ID, "status": "PREFLIGHT_PASS_READY",
             "preflight_parent_head": git("rev-parse", "HEAD"),
             "authorized_run_ids": [item[0] for item in RUN_MATRIX],
             "physical_solve_count_authorized": 2, "physical_solve_count_completed": 0,
             "runs": [], "static_qa_status": "PASS",
             "scientific_interpretation_performed": False, "automatic_follow_up": False}
    output = {"experiment": experiment, "preflight": preflight_text, "static": static_qa,
              "work_unit": work_unit, "metric_spec": metric_spec, "probes": probes, "batch": batch}
    if write:
        for key, path in FILES.items():
            _write_new(path, output[key])
        manifest.setdefault("authorization_batches", []).append({
            "batch_id": platform.CARRY_D3_TIMING_BATCH_ID, "risk_level": "NORMAL",
            "authorized_cases": [item[1] for item in RUN_MATRIX],
            "run_ids": [item[0] for item in RUN_MATRIX],
            "authorized_physical_solve_count": 2, "physical_solve_count_completed": 0,
            "preflight_parent_head": git("rev-parse", "HEAD"),
            "preflight_sha256": work_unit["preflight_sha256"],
            "static_qa_sha256": work_unit["static_qa_sha256"],
            "execution_status": "PREFLIGHT_PASS_READY",
            "scientific_interpretation_performed": False, "automatic_follow_up": False})
        manifest.setdefault("authorized_physical_solves", []).extend(item[1] for item in RUN_MATRIX)
        manifest["maximum_physical_solve_count"] = max(int(manifest.get("maximum_physical_solve_count", 0)), 41)
        platform._json(MANIFEST, manifest)
    return {"status": "PREFLIGHT_PASS", "batch_id": platform.CARRY_D3_TIMING_BATCH_ID,
            "parent_head": git("rev-parse", "HEAD"), "run_ids": [item[0] for item in RUN_MATRIX],
            "physical_solve_count": 0, "historical_runs_rendered": len(legacy_render),
            "new_decks_syntax_checked": len(run_records),
            "probe_count_by_run": {item["run_id"]: item["probe_count"] for item in run_records},
            "conservative_raw_projection_bytes": {key: value["conservative_projection_bytes"]
                                                  for key, value in projections.items()},
            "preflight_sha256": work_unit["preflight_sha256"], "written": write}


def execute() -> int:
    if git("status", "--porcelain"):
        raise RuntimeError("physical batch requires clean worktree after source and preflight commits")
    if not all(path.is_file() for path in FILES.values()):
        raise RuntimeError("locked preflight files are incomplete; no solver invoked")
    work = read_json(FILES["work_unit"])
    batch = read_json(FILES["batch"])
    static = read_json(FILES["static"])
    if (batch.get("status") != "PREFLIGHT_PASS_READY" or static.get("status") != "PASS" or
            work.get("authorized_run_ids") != [item[0] for item in RUN_MATRIX] or
            work.get("authorized_physical_solve_count") != 2 or work.get("physical_solve_count_completed") != 0 or
            work.get("preflight_sha256") != sha(FILES["preflight"]) or
            work.get("static_qa_sha256") != sha(FILES["static"]) or
            work.get("metric_spec_sha256") != sha(FILES["metric_spec"]) or
            work.get("probe_manifest_sha256") != sha(FILES["probes"])):
        raise RuntimeError("locked preflight hashes or exact two-run authorization do not match")
    if git("rev-parse", "HEAD^") != work["preflight_parent_head"]:
        raise RuntimeError("execution HEAD is not the single preflight commit over the locked source HEAD")
    for relative, expected in work["locked_file_sha256"].items():
        path = REPO / relative
        if not path.is_file() or sha(path) != expected:
            raise RuntimeError(f"locked source/config changed after preflight: {relative}")
    hist_before = _historical_raws()
    if {key: value["raw_sha256"] for key, value in hist_before.items()} != work["historical_raw_sha256"]:
        raise RuntimeError("A027-A039 raw SHA changed after preflight")
    cases, _ = _prepare_records(run_syntax=False)
    locked_records = {item["run_id"]: item for item in static["new_runs"]}
    for item in cases:
        ref = locked_records.get(item["run_id"])
        if not ref or any(item[key] != ref[key] for key in ("deck_sha256", "stimulus_sha256", "probe_manifest_sha256")):
            raise RuntimeError(f"rendered input differs from locked static preflight: {item['run_id']}")
    solver = platform._solver_info()
    if (solver["path"], solver["version"], solver["sha256"]) != (
            static["solver"]["path"], static["solver"]["version"], static["solver"]["sha256"]):
        raise RuntimeError("JoSIM binary identity differs from locked preflight")
    manifest = read_json(MANIFEST)
    auth = [item for item in manifest.get("authorization_batches", [])
            if item.get("batch_id") == platform.CARRY_D3_TIMING_BATCH_ID]
    if (len(auth) != 1 or auth[0].get("run_ids") != [item[0] for item in RUN_MATRIX] or
            auth[0].get("physical_solve_count_completed") != 0):
        raise RuntimeError("experiment_manifest authorization is missing, duplicated, or already consumed")
    for run_id, *_ in RUN_MATRIX:
        if (RUNS / run_id).exists() or any(row.get("run_id") == run_id for row in manifest.get("runs", [])):
            raise RuntimeError(f"run ID became occupied after preflight; refusing overwrite: {run_id}")

    auth[0].update({"execution_status": "RUNNING", "parent_head_at_execution": solver["parent_head"]})
    platform._json(MANIFEST, manifest)
    batch.update({"status": "RUNNING", "execution_head": solver["parent_head"],
                  "physical_solve_count_completed": 0, "runs": []})
    platform._json(FILES["batch"], batch)
    for index, record in enumerate(static["new_runs"]):
        run_id = record["run_id"]
        case_item = cases[index]
        case, stimulus, params = platform.load_config(record["preset"])
        print(f"START {run_id}: D3 PRE_CB sJTL count={case_item['carry_sjtl_count_by_stage']['D3']}; "
              f"DT={case['DT']} STOP={case['STOP']}; estimated raw="
              f"{case_item['static_qa']['raw_estimate_bytes']} B; solver={solver['path']}", flush=True)
        rendered = platform.render(case, stimulus, params, RUNS / run_id)
        code, result = platform.run_one(case, stimulus, params, solver,
                                        batch_id=platform.CARRY_D3_TIMING_BATCH_ID,
                                        run_id_override=run_id, rendered_override=rendered,
                                        preflight_path=FILES["preflight"],
                                        metric_spec_path_override=FILES["metric_spec"],
                                        expected_deck_sha256=record["deck_sha256"])
        batch_run = {"run_id": run_id, "status": result.get("status"),
                     "artifact_status": result.get("artifact_status"),
                     "physical_solve_count": result.get("physical_solve_count", 1),
                     "qa_status": result.get("qa_status"), "raw_sha256": result.get("raw_sha256"),
                     "raw_bytes": result.get("raw_bytes"), "deck_sha256": result.get("deck_sha256")}
        batch["runs"].append(batch_run)
        batch["physical_solve_count_completed"] += int(result.get("physical_solve_count", 1))
        batch["status"] = "RUNNING" if code == 0 else "STOPPED_AFTER_ARTIFACT_FAILURE"
        platform._json(FILES["batch"], batch)
        manifest = read_json(MANIFEST)
        auth = next(item for item in manifest["authorization_batches"]
                    if item.get("batch_id") == platform.CARRY_D3_TIMING_BATCH_ID)
        auth["physical_solve_count_completed"] = batch["physical_solve_count_completed"]
        auth["execution_status"] = batch["status"]
        platform._json(MANIFEST, manifest)
        print(json.dumps(result, ensure_ascii=False), flush=True)
        if code != 0:
            print("STOP: preserve this run and do not launch the remaining authorized case after artifact/solver failure.",
                  file=sys.stderr, flush=True)
            return code
    import analyze_d3_carry_timing as analyzer
    summary = analyzer.analyze()
    hist_after = _historical_raws()
    if {key: value["raw_sha256"] for key, value in hist_after.items()} != work["historical_raw_sha256"]:
        raise RuntimeError("historical A027-A039 raw SHA changed during the batch")
    batch["status"] = "BATCH_COMPLETE_AWAITING_USER_CHATGPT_REVIEW"
    batch["physical_solve_count_completed"] = 2
    batch["summary_path"] = (TASK / "D3_CARRY_TIMING_SUMMARY.json").relative_to(SERIES).as_posix()
    batch["summary_sha256"] = sha(TASK / "D3_CARRY_TIMING_SUMMARY.json")
    platform._json(FILES["batch"], batch)
    manifest = read_json(MANIFEST)
    auth = next(item for item in manifest["authorization_batches"]
                if item.get("batch_id") == platform.CARRY_D3_TIMING_BATCH_ID)
    auth["physical_solve_count_completed"] = 2
    auth["execution_status"] = batch["status"]
    auth["mechanical_analysis_status"] = "MECHANICAL_QA_PASS"
    platform._json(MANIFEST, manifest)
    print(json.dumps({"status": batch["status"], "batch_id": batch["batch_id"],
                      "run_ids": [item[0] for item in RUN_MATRIX], "physical_solve_count": 2,
                      "raw_sha256_by_run": {item["run_id"]: item["raw_sha256"] for item in batch["runs"]},
                      "comparison_pages": [item["path"] for item in summary["comparison_pages"]],
                      "scientific_interpretation_performed": False,
                      "automatic_follow_up": False}, ensure_ascii=False, indent=2), flush=True)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Preflight/execute exactly A040 and A041; no automatic follow-up")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true", help="run read-only render, historical regression, syntax, and raw-size checks")
    group.add_argument("--prepare-preflight", action="store_true", help="write the immutable preflight artifacts after source commit")
    group.add_argument("--execute", action="store_true", help="execute exactly the locked A040/A041 matrix")
    args = parser.parse_args()
    try:
        if args.execute:
            return execute()
        print(json.dumps(prepare_preflight(write=args.prepare_preflight), ensure_ascii=False, indent=2))
        return 0
    except (OSError, KeyError, ValueError, RuntimeError, platform.ConfigError) as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
