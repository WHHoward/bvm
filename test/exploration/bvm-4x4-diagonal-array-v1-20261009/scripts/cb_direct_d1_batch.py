#!/usr/bin/env python3
"""Preflight and execute the registered two-run D1 CB_DIRECT comparison."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any

SERIES = Path(__file__).resolve().parents[1]
REPO = SERIES.parents[2]
ANALYSIS = SERIES / "analysis" / "cb-direct-d1-20261009"
PREFLIGHT = ANALYSIS / "PREFLIGHT.md"
STATIC_QA = ANALYSIS / "STATIC_QA.json"
PROBES = ANALYSIS / "PROBE_MANIFEST.json"
WORK_UNIT = ANALYSIS / "WORK_UNIT.json"
BATCH = ANALYSIS / "BATCH_MANIFEST.json"
EXPERIMENT_MANIFEST = SERIES / "experiment_manifest.json"
BASE_HEAD = "c29af07ce782af4b44f9f47d14a9a39783e9d96f"
BASELINE_RUNS = (
    ("A021_CHAIN_ALL_GLOBAL_CLOCK", "CB_DIRECT_D1_ALL_CLOCK", "1111", "1111",
     "85ffd3a00a6815115307d917c9b35d3b06dd7ac240c61ca8bfd47b957e975e9e",
     "678b08e181ecaba8b96b81f2798dc949309c76e3f14ead7ea2b7773bb0369364",
     "d149f6f4e83360d8a1b1671e655ed1c9ea241722ebbbc1de48ae4e9fc792f4e2"),
    ("A022_CHAIN_PAPER_GLOBAL_CLOCK", "CB_DIRECT_D1_PAPER_CLOCK", "1101", "1101",
     "2095fc87f129e844abfe21a0ccafb21e9ef2c72b67e7b6c34c8ca8f50935d9cb",
     "678b08e181ecaba8b96b81f2798dc949309c76e3f14ead7ea2b7773bb0369364",
     "d129cc80bceae1382a3d8011c3265dfc451993a2ae7211ed4f1a341ae9ca7926"),
)
RUNS = ("A023_CB_DIRECT_D1_ALL_CLOCK", "A024_CB_DIRECT_D1_PAPER_CLOCK")
STATIC_SUBCKTS = ("THmitll_MERGE", "THmitll_DFF", "D0_JTL", "T1", "BVM", "BQ", "sJTL", "CB")

sys.path.insert(0, str(SERIES / "scripts"))
import diagonal_platform as platform  # noqa: E402


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def json_read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def json_new(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True,
                          check=True).stdout.strip()


def _cb_default_check() -> dict[str, Any]:
    path = REPO / platform.SOURCE_PATHS["CB"]
    expected = {
        ".subckt CB IN OUT", "L1 IN 1 1.5p", "L2 1 2 .5p", "L3 3 4 .5p",
        "L4 4 OUT 3.5p", "BJ1 1 0 jjmit area=2.2", "RJ1 1 0 5",
        "BJ2 2 3 jjmit area=1.8", "RJ2 2 3 6", "IB1 0 4 pwl(0 0 5p 160u)",
    }
    lines = {line.strip() for line in path.read_text(encoding="utf-8").splitlines()}
    missing = sorted(expected - lines)
    if missing:
        raise RuntimeError(f"canonical CB_0928 active default lines differ: {missing}")
    digest = sha(path)
    if digest != platform.SOURCE_SHA256["CB"]:
        raise RuntimeError(f"canonical CB_0928 SHA changed: {digest}")
    return {"path": path.relative_to(REPO).as_posix(), "sha256": digest,
            "ports": ["IN", "OUT"], "expected_active_lines": sorted(expected),
            "matches_registered_defaults": True}


def _baseline_identity(run_id: str, raw_sha: str, deck_sha: str, stimulus_sha: str) -> dict[str, Any]:
    run_dir = SERIES / "runs" / run_id
    result = json_read(run_dir / "result.json")
    qa = json_read(run_dir / "qa.json")
    chain_qa = json_read(run_dir / "chain_qa.json")
    raw = run_dir / "raw.csv"
    if (result.get("artifact_status") != "VALID" or result.get("physical_solve_count") != 1 or
            result.get("raw_sha256") != raw_sha or result.get("deck_sha256") != deck_sha or
            result.get("stimulus_sha256") != stimulus_sha or qa.get("status") != "PASS" or
            chain_qa.get("status") != "PASS" or sha(raw) != raw_sha):
        raise RuntimeError(f"A021/A022 baseline identity or QA mismatch: {run_id}")
    return {"run_id": run_id, "raw_path": raw.relative_to(SERIES).as_posix(),
            "raw_sha256": raw_sha, "raw_bytes": raw.stat().st_size,
            "deck_sha256": deck_sha, "stimulus_sha256": stimulus_sha,
            "artifact_status": "VALID", "qa_status": "PASS"}


def _case_equivalence(case: dict[str, str], stimulus: dict[str, str], params: dict[str, str],
                      baseline_run: str, expected_case_name: str, expected_rows: str,
                      expected_cols: str) -> dict[str, Any]:
    baseline_dir = SERIES / "runs" / baseline_run
    baseline = json_read(baseline_dir / "case_manifest.json")
    baseline_case = dict(baseline["case"])
    baseline_case.setdefault("CBU_OVERRIDE_D1", "NONE")
    allowed = {"CASE", "ROW_BITS", "COL_BITS", "FOCUS_STAGE", "CBU_OVERRIDE_D1"}
    diffs = {key: {"baseline": baseline_case.get(key), "candidate": case.get(key)}
             for key in sorted(set(baseline_case) | set(case))
             if baseline_case.get(key) != case.get(key)}
    if set(diffs) - allowed:
        raise RuntimeError(f"unregistered case configuration differences vs {baseline_run}: {diffs}")
    expected = {"CASE": expected_case_name, "ROW_BITS": expected_rows, "COL_BITS": expected_cols,
                "FOCUS_STAGE": "D1", "CBU_OVERRIDE_D1": "CB_DIRECT"}
    if any(case.get(key) != value for key, value in expected.items()):
        raise RuntimeError(f"candidate preset values do not match the registered matrix: {case}")
    if stimulus != baseline["stimulus"]:
        raise RuntimeError(f"stimulus differs from {baseline_run}")

    snapshots = {}
    for name in ("T1_PARAMS.snapshot.env", "CBU_PARAMS.snapshot.env",
                 "DFF_PARAMS.snapshot.env", "D0_JTL_PARAMS.snapshot.env"):
        snapshots.update(platform.parse_env(baseline_dir / name))
    if snapshots != params:
        raise RuntimeError(f"effective T1/CBU/DFF/D0-JTL parameters differ from {baseline_run}")
    return {"baseline_run_id": baseline_run, "allowed_case_differences": diffs,
            "stimulus_identical": True, "effective_device_parameters_identical": True}


def _normalized_deck(lines: list[str]) -> list[str]:
    ignored_prefixes = ("*", ".print ", "V_CBU_A_D1 ", "V_CBU_B_D1 ", "XCBU_D1 ")
    return [line for line in lines if line and not line.startswith(ignored_prefixes)]


def _write_static_gate() -> dict[str, Any]:
    if subprocess.run(["git", "merge-base", "--is-ancestor", BASE_HEAD, "HEAD"],
                      cwd=REPO, check=False).returncode != 0:
        raise RuntimeError(f"preflight HEAD must descend from the current checkpoint {BASE_HEAD}")
    if git("status", "--porcelain"):
        raise RuntimeError("preflight generation requires clean worktree")
    if any((SERIES / "runs" / run_id).exists() for run_id in RUNS):
        raise RuntimeError("A023/A024 run path already exists; refusing overwrite")
    if any(path.exists() for path in (PREFLIGHT, STATIC_QA, PROBES, WORK_UNIT, BATCH)):
        raise RuntimeError("CB_DIRECT D1 registration artifacts already exist; refusing overwrite")

    cb_identity = _cb_default_check()
    baselines = {}
    rendered_cases = []
    merge_regression = {}
    for run_id, preset, rows, cols, raw_sha, deck_sha, stimulus_sha in BASELINE_RUNS:
        baseline_record = _baseline_identity(run_id, raw_sha, deck_sha, stimulus_sha)
        baselines[run_id] = baseline_record
        case, stimulus, params = platform.load_config(preset)
        equivalence = _case_equivalence(case, stimulus, params, run_id, preset, rows, cols)
        baseline_deck = (SERIES / "runs" / run_id / "deck.cir").read_text(encoding="utf-8").splitlines()
        static_regression = platform.load_config("CHAIN_ALL_GLOBAL_CLOCK" if rows == "1111"
                                                  else "CHAIN_PAPER_GLOBAL_CLOCK")
        old_render = platform.render(*static_regression, SERIES / "runs" / "_CB_DIRECT_REGRESSION")
        if sha(SERIES / "runs" / run_id / "deck.cir") != deck_sha or old_render["deck"].splitlines() != baseline_deck:
            raise RuntimeError(f"default MERGE render-only regression differs from {run_id}")
        merge_regression[preset] = {"status": "PASS", "baseline_run_id": run_id,
                                    "deck_sha256": deck_sha, "byte_identical": True}

        candidate_case = dict(case)
        candidate_case.update({"CASE": preset, "ROW_BITS": rows, "COL_BITS": cols,
                               "CBU_OVERRIDE_D1": "CB_DIRECT", "FOCUS_STAGE": "D1"})
        prospective = SERIES / "runs" / run_id.replace("CHAIN_", "CB_DIRECT_D1_")
        # Rendering to an existing-depth path makes the .include closure identical to the eventual run.
        rendered = platform.render(candidate_case, stimulus, params, prospective)
        labels = {signal["label"] for signal in rendered["probes"]["signals"]}
        pages = platform.plot_signals(rendered["probes"])
        if rendered["static_qa"]["status"] != "PASS" or not pages or any(
                signal not in labels for page in pages for signal in page["signals"]):
            raise RuntimeError(f"candidate static/probe/plot validation failed: {preset}")
        if rendered["static_qa"]["raw_estimate_bytes"] >= platform.MAX_RAW_BYTES:
            raise RuntimeError(f"candidate raw estimate exceeds the registered file guard: {preset}")
        base_deck = baseline_deck
        if _normalized_deck(rendered["deck"].splitlines()) != _normalized_deck(base_deck):
            raise RuntimeError(f"candidate changes non-D1 physical deck content vs {run_id}")
        if hashlib.sha256(rendered["stimulus_text"].encode("utf-8")).hexdigest() != stimulus_sha:
            raise RuntimeError(f"candidate stimulus SHA differs from {run_id}")
        rendered_cases.append({"run_id": RUNS[len(rendered_cases)], "preset": preset,
                               "baseline_run_id": run_id, "case": candidate_case,
                               "stimulus": stimulus, "params": params, "rendered": rendered,
                               "deck_sha256": hashlib.sha256(rendered["deck"].encode()).hexdigest(),
                               "stimulus_sha256": hashlib.sha256(rendered["stimulus_text"].encode()).hexdigest(),
                               "probe_sha256": hashlib.sha256((json.dumps(rendered["probes"], ensure_ascii=False,
                                                                         indent=2)+"\n").encode()).hexdigest(),
                               "probe_count": rendered["probes"]["signal_count"],
                               "raw_estimate_bytes": rendered["static_qa"]["raw_estimate_bytes"],
                               "case_equivalence": equivalence,
                               "netlist_diff_allowlist": ["D1 input sensor endpoints", "D1 CBU instance type/pins",
                                                          ".print/probe directives", "comments"]})

    solver = platform._solver_info()
    static_records = []
    for item in rendered_cases:
        with tempfile.TemporaryDirectory(prefix=".cb-direct-d1-static-", dir=platform.RUNS) as temp_name:
            temp = Path(temp_name)
            rendered = platform.render(item["case"], item["stimulus"], item["params"], temp)
            (temp / "deck.cir").write_text(rendered["deck"], encoding="utf-8")
            (temp / "stimulus.inc").write_text(rendered["stimulus_text"], encoding="utf-8")
            if rendered.get("t1_source_text") is not None:
                target = temp / "sources" / "t1_cell_tunable.cir"
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(rendered["t1_source_text"], encoding="utf-8")
            for relative, source_text in rendered.get("chain_source_texts", {}).items():
                target = temp / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(source_text, encoding="utf-8")
            command = [str(platform.SOLVER)]
            for subckt in STATIC_SUBCKTS:
                command.extend(("-s", subckt))
            command.append(str(temp / "deck.cir"))
            completed = subprocess.run(command, cwd=temp, capture_output=True, text=True,
                                       check=False, timeout=120)
            stdout = completed.stdout.encode("utf-8")
            stderr = completed.stderr.encode("utf-8")
            summary = {"run_id": item["run_id"], "preset": item["preset"],
                       "command_subcircuits": list(STATIC_SUBCKTS),
                       "exit_code": completed.returncode, "physical_solve_count": 0,
                       "stdout_sha256": hashlib.sha256(stdout).hexdigest(),
                       "stdout_bytes": len(stdout), "stdout_line_count": len(completed.stdout.splitlines()),
                       "stdout_tail": completed.stdout.splitlines()[-8:],
                       "stderr_sha256": hashlib.sha256(stderr).hexdigest(),
                       "stderr_bytes": len(stderr), "stderr_tail": completed.stderr.splitlines()[-8:]}
            static_records.append(summary)
            if completed.returncode != 0:
                raise RuntimeError(f"JoSIM static -s check failed for {item['preset']}: {summary}")

    source_records = platform.verify_sources()
    config_paths = (platform.USER_CASE, platform.STIMULUS, platform.T1_PARAMS,
                    platform.CBU_PARAMS, platform.DFF_PARAMS, platform.D0_JTL_PARAMS)
    qa = {"schema": "bvm-4x4-cb-direct-d1-static-qa-v1", "status": "PASS",
          "experiment_id": "bvm-4x4-cb-direct-d1-20261009", "batch_id": platform.CB_DIRECT_D1_BATCH_ID,
          "parent_head": git("rev-parse", "HEAD"), "physical_solve_count": 0,
          "solver": solver, "platform_sha256": sha(Path(platform.__file__).resolve()),
          "batch_runner_sha256": sha(Path(__file__).resolve()),
          "registration_sha256": {
              "experiment_yaml": sha(ANALYSIS / "experiment.yaml"),
              "metric_spec": sha(ANALYSIS / "METRIC_SPEC.json"),
              "human_gate": sha(ANALYSIS / "human-gate.yaml"),
              "analysis_runner": sha(SERIES / "scripts" / "analyze_cb_direct_d1.py")},
          "config_sha256": {path.relative_to(SERIES).as_posix(): sha(path) for path in config_paths},
          "canonical_source_sha256": {role: item["sha256"] for role, item in source_records.items()},
          "canonical_cb_direct": cb_identity, "baseline_runs": baselines,
          "merge_render_only_regression": merge_regression,
          "circuit_checks": {"D1_one_CB_0928_instance": True,
                             "D1_no_THmitll_MERGE_instance": True,
                             "D1_no_added_sJTL": True,
                             "D2_D6_remain_THmitll_MERGE": True,
                             "D0_entry_JTL_unchanged": True,
                             "seven_T1_and_DFF_unchanged": True,
                             "global_one_shot_clock_unchanged": True,
                             "input_sensor_terminals_and_directions": "PASS",
                             "unique_names_and_probe_resolution": "PASS",
                             "other_physical_deck_lines_match_A021_A022": True},
          "josim_static_sanity": static_records,
          "runs": [{key: item[key] for key in ("run_id", "preset", "baseline_run_id", "deck_sha256",
                                                "stimulus_sha256", "probe_sha256", "probe_count",
                                                "raw_estimate_bytes", "case_equivalence",
                                                "netlist_diff_allowlist")} for item in rendered_cases],
          "raw_limit_bytes": platform.MAX_RAW_BYTES, "raw_storage_guard": "PASS",
          "scientific_interpretation_performed": False}
    json_new(STATIC_QA, qa)
    json_new(PROBES, {"schema": "bvm-4x4-cb-direct-d1-probe-registry-v1",
                      "manifests_by_run_id": {item["run_id"]: item["rendered"]["probes"]
                                               for item in rendered_cases}})
    preflight_text = _preflight_text(qa, rendered_cases)
    PREFLIGHT.write_text(preflight_text, encoding="utf-8", newline="\n")
    preflight_sha = sha(PREFLIGHT)

    manifest = json_read(EXPERIMENT_MANIFEST)
    batches = manifest.setdefault("authorization_batches", [])
    if any(item.get("batch_id") == platform.CB_DIRECT_D1_BATCH_ID for item in batches):
        raise RuntimeError("CB_DIRECT D1 authorization batch already exists")
    batches.append({"batch_id": platform.CB_DIRECT_D1_BATCH_ID, "risk_level": "NORMAL",
                    "authorized_cases": [item["preset"] for item in rendered_cases],
                    "run_ids": list(RUNS), "authorized_physical_solve_count": 2,
                    "physical_solve_count_completed": 0,
                    "parent_head_at_preflight": qa["parent_head"],
                    "preflight_sha256": preflight_sha,
                    "static_qa_sha256": sha(STATIC_QA), "probe_manifest_sha256": sha(PROBES),
                    "scientific_interpretation_performed": False, "automatic_follow_up": False})
    with EXPERIMENT_MANIFEST.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(manifest, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    unit = {"schema": "bvm-4x4-cb-direct-d1-work-unit-v1",
            "experiment_id": "bvm-4x4-cb-direct-d1-20261009",
            "experiment_risk_level": "NORMAL", "batch_id": platform.CB_DIRECT_D1_BATCH_ID,
            "source_parent_head": qa["parent_head"], "preflight_sha256": preflight_sha,
            "static_qa_sha256": sha(STATIC_QA), "probe_manifest_sha256": sha(PROBES),
            "experiment_manifest_sha256": sha(EXPERIMENT_MANIFEST),
            "experiment_yaml_sha256": sha(ANALYSIS / "experiment.yaml"),
            "metric_spec_sha256": sha(ANALYSIS / "METRIC_SPEC.json"),
            "analysis_runner_sha256": sha(SERIES / "scripts" / "analyze_cb_direct_d1.py"),
            "authorized_run_ids": list(RUNS), "physical_solve_count_authorized": 2,
            "physical_solve_count_completed_at_registration": 0,
            "baseline_raw_sha256_by_run": {run_id: record["raw_sha256"]
                                             for run_id, record in baselines.items()},
            "scientific_interpretation_performed": False, "automatic_follow_up": False,
            "next_action": "RUN_EXACT_TWO_CASE_BATCH_THEN_PACKAGE_AND_STOP"}
    json_new(WORK_UNIT, unit)
    batch = {"schema": "bvm-4x4-cb-direct-d1-batch-v1", "batch_id": platform.CB_DIRECT_D1_BATCH_ID,
             "status": "REGISTERED_NOT_RUN", "preflight_path": PREFLIGHT.relative_to(SERIES).as_posix(),
             "preflight_sha256": preflight_sha, "static_qa_path": STATIC_QA.relative_to(SERIES).as_posix(),
             "static_qa_sha256": sha(STATIC_QA), "probe_manifest_path": PROBES.relative_to(SERIES).as_posix(),
             "probe_manifest_sha256": sha(PROBES), "authorized_run_ids": list(RUNS),
             "physical_solve_count_completed": 0, "runs": [],
             "scientific_interpretation_performed": False, "automatic_follow_up": False}
    json_new(BATCH, batch)
    return {"status": "STATIC_PREFLIGHT_PASS", "run_ids": list(RUNS),
            "physical_solve_count": 0, "preflight_sha256": preflight_sha,
            "static_qa_sha256": sha(STATIC_QA), "probe_manifest_sha256": sha(PROBES),
            "raw_estimates": {item["run_id"]: item["raw_estimate_bytes"] for item in qa["runs"]},
            "merge_render_only_regression": merge_regression,
            "scientific_interpretation_performed": False}


def _preflight_text(qa: dict[str, Any], cases: list[dict[str, Any]]) -> str:
    rows = []
    for item in cases:
        rows.append(f"| {item['run_id']} | {item['preset']} | {item['case']['ROW_BITS']}/{item['case']['COL_BITS']} | "
                    f"{item['deck_sha256']} | {item['stimulus_sha256']} | {item['probe_count']} | "
                    f"{item['raw_estimate_bytes']} |")
    return "\n".join([
        "# CB_DIRECT D1 A023-A024 preflight", "",
        "This experiment is governed by docs/EXPERIMENT_CONTRACT.md.", "",
        "## Frozen identity", "",
        f"- Experiment: `bvm-4x4-cb-direct-d1-20261009` (risk `NORMAL`).",
        f"- Static preflight source HEAD: `{qa['parent_head']}`.",
        f"- Batch: `{platform.CB_DIRECT_D1_BATCH_ID}`; exactly two authorized physical solves.",
        f"- Static QA: `STATIC_QA.json`, SHA-256 `{sha(STATIC_QA)}`; probes registry SHA-256 `{sha(PROBES)}`.",
        f"- A021 raw SHA: `{qa['baseline_runs']['A021_CHAIN_ALL_GLOBAL_CLOCK']['raw_sha256']}`; "
        f"A022 raw SHA: `{qa['baseline_runs']['A022_CHAIN_PAPER_GLOBAL_CLOCK']['raw_sha256']}`.",
        "- Canonical CB_0928 SHA: `70a6af05acccb7c354799d5b1b7542c86c677970681473f559bbf0f7e4d6d370`.",
        "", "## Question and topology", "",
        "Only the D1 CBU implementation changes. DOUT_D1 and T1_D0.C each pass through their own zero-volt "
        "current sensor to the shared `CBU_JOIN_D1` node; canonical `.subckt CB IN OUT` consumes that common "
        "input and its OUT feeds T1_D1 through `V_T1_LINK_D1`. No isolator, sJTL, delay element, or ideal "
        "current adder is inserted. D2-D6 remain THmitll_MERGE; D0 entrance JTL and all remaining stages are frozen.",
        "", "## Fixed parameters and stimulus", "",
        "A021/A022 settings are retained: shared WL/BL 400u, independent SE 100u, array CB/sJTL topology, "
        "D0 entry sJTL, seven T1s, DFF, all device parameters, and one-shot global clock at 200 ps "
        "(1.2m amplitude, 1/2/1 ps edges/hold, 2 ohm series R). `DT=0.01p`, `STOP=300p`; no extra sJTL.",
        "", "## Exact run matrix", "",
        "| Run | Preset | ROW/COL | Deck SHA-256 | Stimulus SHA-256 | Probes | Raw estimate bytes |",
        "|---|---|---|---|---|---:|---:|", *rows, "",
        "The paired controls are A021→A023 (`1111/1111`) and A022→A024 (`1101/1101`). Exact PWL/stimulus "
        "hashes must match each baseline. Existing A001-A022 evidence remains immutable.",
        "", "## Registered windows and arithmetic", "",
        "Use actual stored timestamps only; windows are half-open: ARRAY_FINAL_READ `[110,121) ps`, "
        "PRE_CLOCK `[121,200) ps`, CLOCK_EDGE `[200,205) ps`, POST_CLOCK `[205,300) ps`, TOTAL `[0,300) ps`. "
        "Report D1 upstream CB BJ1 P/V; branch currents `I(V_CBU_A_D1)` and `I(V_CBU_B_D1)` in the stated "
        "source directions; CB BJ1/BJ2 P/V and output-link current; T1_D1 input and B_J1/B_J9/B_J10/B_J11 "
        "P/V, S/C; D0 C and carry-JJ P/V. Phase remains radians; `delta/(2*pi)` is navigation only. "
        "Same-JJ voltage areas use the same run, JJ, direction, actual rows, and window. No time interpolation.",
        "", "## QA, plots, and interpretation ceiling", "",
        "Static checks require one D1 CB_0928, no D1 THmitll_MERGE, no D1 output sJTL, D2-D6 MERGE, "
        "unchanged D0/T1/DFF/clock, unique names, resolved probes, exact stimulus, pinned canonical SHA, "
        "and JoSIM `-s` syntax checks. Every run gets the existing classic `josim-plot2.py` responsive "
        "focus pages; two matched comparison pages use common signals in separate sections and their native grids.",
        "No SFQ/event classifier, physical success threshold, functional verdict, or mechanism explanation "
        "is authorized. A waveform peak, lobe candidate, local phase change, or mechanical QA PASS is not an "
        "event count or a functional-success decision. Timestep convergence is `UNKNOWN`; no follow-up is authorized.",
        "", "Scientific interpretation: `NOT PERFORMED`. Automatic follow-up: `NONE`.",
        "",
    ])


def run_batch() -> int:
    if git("status", "--porcelain"):
        raise RuntimeError("physical batch requires a clean worktree after preflight commit")
    if not BATCH.is_file() or not WORK_UNIT.is_file() or not PREFLIGHT.is_file():
        raise RuntimeError("locked CB_DIRECT D1 preflight files are missing")
    work = json_read(WORK_UNIT)
    batch = json_read(BATCH)
    if (batch.get("status") != "REGISTERED_NOT_RUN" or batch.get("physical_solve_count_completed") != 0 or
            batch.get("authorized_run_ids") != list(RUNS) or work.get("physical_solve_count_authorized") != 2):
        raise RuntimeError("CB_DIRECT D1 batch is not an untouched exact two-run authorization")
    static = json_read(STATIC_QA)
    if (sha(PREFLIGHT) != work.get("preflight_sha256") or sha(STATIC_QA) != work.get("static_qa_sha256") or
            sha(PROBES) != work.get("probe_manifest_sha256") or sha(EXPERIMENT_MANIFEST) != work.get("experiment_manifest_sha256")):
        raise RuntimeError("preflight, static QA, probes, or experiment authorization hash changed")
    registration = static.get("registration_sha256", {})
    if (sha(ANALYSIS / "experiment.yaml") != registration.get("experiment_yaml") or
            sha(ANALYSIS / "METRIC_SPEC.json") != registration.get("metric_spec") or
            sha(ANALYSIS / "human-gate.yaml") != registration.get("human_gate") or
            sha(SERIES / "scripts" / "analyze_cb_direct_d1.py") != registration.get("analysis_runner") or
            sha(SERIES / "scripts" / "cb_direct_d1_batch.py") != static.get("batch_runner_sha256") or
            sha(SERIES / "scripts" / "diagonal_platform.py") != static.get("platform_sha256")):
        raise RuntimeError("platform, analyzer, experiment, or metric specification changed after preflight")
    expected_configs = static.get("config_sha256", {})
    for rel_path, digest in expected_configs.items():
        if sha(SERIES / rel_path) != digest:
            raise RuntimeError(f"effective configuration changed after preflight: {rel_path}")
    if git("rev-parse", "HEAD^") != work.get("source_parent_head"):
        raise RuntimeError("execution HEAD is not the preflight commit directly on the recorded source parent")
    if static.get("status") != "PASS" or static.get("physical_solve_count") != 0:
        raise RuntimeError("CB_DIRECT D1 static QA is not PASS")
    solver = platform._solver_info()
    if solver.get("path") != static["solver"].get("path") or solver.get("version") != static["solver"].get("version") or \
            solver.get("sha256") != static["solver"].get("sha256"):
        raise RuntimeError("JoSIM executable identity changed since preflight")
    for row in BASELINE_RUNS:
        _baseline_identity(row[0], row[4], row[5], row[6])

    batch.update({"status": "RUNNING", "execution_head": solver["parent_head"],
                  "solver": solver, "runs": [], "physical_solve_count_completed": 0})
    json_write(BATCH, batch)
    _mark_execution_head(solver["parent_head"])
    registry = json_read(PROBES)["manifests_by_run_id"]
    cases = []
    for index, item in enumerate(BASELINE_RUNS):
        _baseline_run, preset, rows, cols, _raw, expected_deck, expected_stim = item
        case, stimulus, params = platform.load_config(preset)
        run_id = RUNS[index]
        prospective = SERIES / "runs" / run_id
        rendered = platform.render(case, stimulus, params, prospective)
        probe_digest = hashlib.sha256((json.dumps(rendered["probes"], ensure_ascii=False, indent=2)+"\n").encode()).hexdigest()
        locked = next(record for record in static["runs"] if record["run_id"] == run_id)
        if (hashlib.sha256(rendered["deck"].encode()).hexdigest() != expected_deck or
                hashlib.sha256(rendered["stimulus_text"].encode()).hexdigest() != expected_stim or
                probe_digest != locked["probe_sha256"] or rendered["probes"] != registry[run_id]):
            raise RuntimeError(f"frozen deck/stimulus/probe mismatch before {run_id}")
        if prospective.exists():
            raise RuntimeError(f"refusing to overwrite run directory: {prospective}")
        cases.append({"run_id": run_id, "preset": preset, "case": case,
                      "stimulus": stimulus, "params": params, "rendered": rendered,
                      "deck_sha256": expected_deck})

    for item in cases:
        print(f"START {item['run_id']} {item['preset']}; physical_solve_count before this run="
              f"{batch['physical_solve_count_completed']}", flush=True)
        code, result = platform.run_one(
            item["case"], item["stimulus"], item["params"], solver,
            batch_id=platform.CB_DIRECT_D1_BATCH_ID, run_id_override=item["run_id"],
            preflight_path=PREFLIGHT,
            metric_spec_path_override=ANALYSIS / "METRIC_SPEC.json",
            expected_deck_sha256=item["deck_sha256"])
        record = {"run_id": item["run_id"], "preset": item["preset"],
                  "status": result.get("status"), "artifact_status": result.get("artifact_status"),
                  "qa_status": result.get("qa_status"), "physical_solve_count": result.get("physical_solve_count", 1),
                  "raw_sha256": result.get("raw_sha256"), "raw_bytes": result.get("raw_bytes"),
                  "deck_sha256": result.get("deck_sha256"), "stimulus_sha256": result.get("stimulus_sha256")}
        batch["runs"].append(record)
        batch["physical_solve_count_completed"] += int(record["physical_solve_count"])
        batch["status"] = ("RUNNING" if code == 0 else "STOPPED_AFTER_SOLVER_OR_ARTIFACT_FAILURE")
        json_write(BATCH, batch)
        print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
        if code != 0 or record["artifact_status"] != "VALID" or record["qa_status"] != "PASS":
            print("STOP: preserving this run's raw/evidence and not starting a later case.",
                  file=sys.stderr, flush=True)
            _mark_completed_count(batch["physical_solve_count_completed"])
            return code or 2

    try:
        import analyze_cb_direct_d1
        analysis_result = analyze_cb_direct_d1.build_postrun_evidence(batch)
    except Exception as exc:
        batch.update({"status": "RUNS_VALID_POSTRUN_ANALYSIS_FAILURE_RAW_PRESERVED",
                      "postrun_analysis_error": f"{type(exc).__name__}: {exc}"})
        json_write(BATCH, batch)
        _mark_completed_count(batch["physical_solve_count_completed"])
        raise
    batch.update({"status": "MECHANICAL_QA_PASS_AWAITING_USER_REVIEW",
                  "physical_solve_count_completed": 2,
                  "comparison_path": analysis_result["comparison_path"],
                  "comparison_sha256": analysis_result["comparison_sha256"],
                  "comparison_qa_path": analysis_result["comparison_qa_path"],
                  "comparison_qa_sha256": analysis_result["comparison_qa_sha256"],
                  "result_brief_path": analysis_result["result_brief_path"],
                  "evidence_manifest_path": analysis_result["evidence_manifest_path"],
                  "raw_sha256_by_run": {item["run_id"]: item["raw_sha256"] for item in batch["runs"]},
                  "scientific_interpretation_performed": False, "automatic_follow_up": False})
    json_write(BATCH, batch)
    _mark_completed_count(2)
    print(json.dumps({"status": batch["status"], "run_ids": list(RUNS),
                      "physical_solve_count": 2, "raw_sha256_by_run": batch["raw_sha256_by_run"],
                      "scientific_interpretation_performed": False,
                      "automatic_follow_up": False}, ensure_ascii=False, indent=2))
    return 0


def _mark_execution_head(execution_head: str) -> None:
    data = json_read(EXPERIMENT_MANIFEST)
    matches = [item for item in data.get("authorization_batches", [])
               if item.get("batch_id") == platform.CB_DIRECT_D1_BATCH_ID]
    if len(matches) != 1 or matches[0].get("physical_solve_count_completed") != 0:
        raise RuntimeError("CB_DIRECT D1 authorization record is missing, duplicated, or already consumed")
    matches[0]["execution_parent_head"] = execution_head
    with EXPERIMENT_MANIFEST.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def _mark_completed_count(count: int) -> None:
    data = json_read(EXPERIMENT_MANIFEST)
    matches = [item for item in data.get("authorization_batches", [])
               if item.get("batch_id") == platform.CB_DIRECT_D1_BATCH_ID]
    if len(matches) == 1:
        matches[0]["physical_solve_count_completed"] = count
        with EXPERIMENT_MANIFEST.open("w", encoding="utf-8", newline="\n") as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.write("\n")


def json_write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Bounded A023/A024 D1 CB_DIRECT experiment")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--prepare-preflight", action="store_true")
    group.add_argument("--run-batch", action="store_true")
    args = parser.parse_args()
    try:
        if args.prepare_preflight:
            result = _write_static_gate()
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        return run_batch()
    except (OSError, RuntimeError, platform.ConfigError, KeyError, ValueError,
            json.JSONDecodeError, subprocess.CalledProcessError, zipfile.BadZipFile) as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
