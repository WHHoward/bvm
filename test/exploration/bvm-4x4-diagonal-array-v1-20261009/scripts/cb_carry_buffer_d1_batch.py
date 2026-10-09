#!/usr/bin/env python3
"""Static preflight and exactly-two-solve runner for the D1 carry-side CB study."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

SERIES = Path(__file__).resolve().parents[1]
REPO = SERIES.parents[2]
RUNS = SERIES / "runs"
TASK = SERIES / "analysis" / "cb-carry-buffer-d1-20261009"
BATCH_ID = "BVM4X4_CB_CARRY_BUFFER_D1_20261009"
RUN_MATRIX = (
    ("A025_CARRY_CB_D1_ALL_CLOCK", "CARRY_CB_D1_ALL_CLOCK", "1111", "1111",
     "A021_CHAIN_ALL_GLOBAL_CLOCK", "A023_CB_DIRECT_D1_ALL_CLOCK"),
    ("A026_CARRY_CB_D1_PAPER_CLOCK", "CARRY_CB_D1_PAPER_CLOCK", "1101", "1101",
     "A022_CHAIN_PAPER_GLOBAL_CLOCK", "A024_CB_DIRECT_D1_PAPER_CLOCK"),
)
BASELINE_RAW_SHA256 = {
    "A021_CHAIN_ALL_GLOBAL_CLOCK": "85ffd3a00a6815115307d917c9b35d3b06dd7ac240c61ca8bfd47b957e975e9e",
    "A022_CHAIN_PAPER_GLOBAL_CLOCK": "2095fc87f129e844abfe21a0ccafb21e9ef2c72b67e7b6c34c8ca8f50935d9cb",
    "A023_CB_DIRECT_D1_ALL_CLOCK": "c56ed579b684cdb1fe122488ce1de85e544e9797710ff7443e8dd1c6097b280a",
    "A024_CB_DIRECT_D1_PAPER_CLOCK": "20cb27683ab2455df6e424dcc74ab09446902389c62fb310b3cc2f4146ee86ed",
}
STATIC_SUBCKTS = ("THmitll_MERGE", "THmitll_DFF", "D0_JTL", "T1", "BVM", "BQ", "sJTL", "CB")
PREFLIGHT = TASK / "PREFLIGHT.md"
STATIC_QA = TASK / "STATIC_QA.json"
PROBE_REGISTRY = TASK / "PROBE_MANIFEST.json"
WORK_UNIT = TASK / "WORK_UNIT.json"
BATCH_MANIFEST = TASK / "BATCH_MANIFEST.json"
EXPERIMENT_MANIFEST = SERIES / "experiment_manifest.json"

sys.path.insert(0, str(SERIES / "scripts"))
import diagonal_platform as platform  # noqa: E402
import analyze_cb_carry_buffer_d1 as analysis  # noqa: E402


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def json_read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def json_new(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def json_replace(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True,
                          text=True, check=True).stdout.strip()


def _assert_run_unoccupied(run_id: str) -> None:
    if (RUNS / run_id).exists():
        raise RuntimeError(f"immutable run directory already exists; refusing overwrite: {run_id}")
    manifest = json_read(EXPERIMENT_MANIFEST)
    if any(item.get("run_id") == run_id for item in manifest.get("runs", [])):
        raise RuntimeError(f"run ID already exists in experiment_manifest.json: {run_id}")


def _verified_baseline(run_id: str) -> dict[str, Any]:
    run_dir = RUNS / run_id
    raw = run_dir / "raw.csv"
    result = json_read(run_dir / "result.json")
    qa = json_read(run_dir / "qa.json")
    chain_qa = json_read(run_dir / "chain_qa.json")
    expected = BASELINE_RAW_SHA256[run_id]
    digest = sha(raw)
    if (digest != expected or result.get("raw_sha256") != expected or
            result.get("artifact_status") != "VALID" or result.get("physical_solve_count") != 1 or
            qa.get("status") != "PASS" or chain_qa.get("status") != "PASS" or
            chain_qa.get("raw_sha256_after_analysis") != expected):
        raise RuntimeError(f"baseline identity/raw QA mismatch: {run_id}")
    return {"run_id": run_id, "raw_path": raw.relative_to(SERIES).as_posix(),
            "raw_sha256": digest, "raw_bytes": raw.stat().st_size,
            "deck_sha256": result.get("deck_sha256"),
            "stimulus_sha256": result.get("stimulus_sha256"),
            "artifact_status": "VALID", "qa_status": "PASS"}


def _normalized_deck(deck: str) -> list[str]:
    d1_prefixes = ("V_CBU_A_D1 ", "V_CBU_B_D1 ", "V_CARRY_IN_D1 ",
                   "XCBU_D1 ", "XCB_CARRY_D1 ", "V_T1_LINK_D1 ")
    return [line for line in deck.splitlines()
            if line and not line.startswith(("*", ".print ")) and not line.startswith(d1_prefixes)]


def _matrix(*, run_josim_sanity: bool = True) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if not platform.SOLVER.is_file() or not platform.PLOTTER.is_file() or not platform.PLOTLY_ASSET.is_file():
        raise RuntimeError("recorded JoSIM solver, classic plotter, or shared Plotly asset is missing")
    if platform.allocate_run_id("unused").split("_", 1)[0] != "A025":
        raise RuntimeError(f"next run number is not A025; found {platform.allocate_run_id('unused')}")
    for run_id, *_ in RUN_MATRIX:
        _assert_run_unoccupied(run_id)

    source_records = platform.verify_sources()
    if set(source_records) != set(platform.SOURCE_SHA256):
        raise RuntimeError("canonical source closure does not match the pinned platform roles")
    cb_path = REPO / platform.SOURCE_PATHS["CB"]
    cb_pins = platform.subckt_pins(cb_path, "CB")
    if cb_pins != ("IN", "OUT") or sha(cb_path) != platform.SOURCE_SHA256["CB"]:
        raise RuntimeError("canonical CB_0928 port order/SHA does not match the registered source")

    rendered_cases: list[dict[str, Any]] = []
    historical_regression: dict[str, Any] = {}
    static_deck_records = []
    for run_id, preset, rows, cols, baseline_id, direct_id in RUN_MATRIX:
        baseline = _verified_baseline(baseline_id)
        direct = _verified_baseline(direct_id)
        baseline_case = json_read(RUNS / baseline_id / "case_manifest.json")["case"]
        direct_case_manifest = json_read(RUNS / direct_id / "case_manifest.json")
        case, stimulus, params = platform.load_config(preset)
        if (case.get("ROW_BITS"), case.get("COL_BITS"), case.get("SE_ENABLE_MASK")) != (rows, cols, "ALL"):
            raise RuntimeError(f"registered input mask does not match {preset}")
        if case.get("CBU_OVERRIDE_D1") != "CB_CARRY_BUFFER" or case.get("FOCUS_STAGE") != "D1":
            raise RuntimeError(f"registered D1 carry-buffer preset mismatch: {preset}")
        allowed_case_differences = {"CASE", "CBU_OVERRIDE_D1", "FOCUS_STAGE"}
        base_case = dict(baseline_case)
        base_case.setdefault("CBU_OVERRIDE_D1", "NONE")
        diffs = {key for key in set(base_case) | set(case) if base_case.get(key) != case.get(key)}
        if diffs != allowed_case_differences:
            raise RuntimeError(f"case parameters differ from matched baseline outside registered fields: {preset}: {sorted(diffs)}")
        base_stimulus = json_read(RUNS / baseline_id / "case_manifest.json")["stimulus"]
        if stimulus != base_stimulus:
            raise RuntimeError(f"effective stimulus differs from {baseline_id}")
        params_baseline = {}
        for snapshot in ("T1_PARAMS.snapshot.env", "CBU_PARAMS.snapshot.env",
                         "DFF_PARAMS.snapshot.env", "D0_JTL_PARAMS.snapshot.env"):
            params_baseline.update(platform.parse_env(RUNS / baseline_id / snapshot))
        if params != params_baseline:
            raise RuntimeError(f"device/clock parameters differ from {baseline_id}")
        if _verified_baseline(direct_id)["raw_sha256"] != direct["raw_sha256"]:
            raise RuntimeError(f"direct-CB comparison baseline changed: {direct_id}")

        historical_preset = ("CHAIN_ALL_GLOBAL_CLOCK" if rows == "1111"
                             else "CHAIN_PAPER_GLOBAL_CLOCK")
        old_case, old_stimulus, old_params = platform.load_config(historical_preset)
        old_render = platform.render(old_case, old_stimulus, old_params, RUNS / baseline_id)
        old_deck_path = RUNS / baseline_id / "deck.cir"
        if old_render["deck"] != old_deck_path.read_text(encoding="utf-8"):
            raise RuntimeError(f"default MERGE render-only regression differs from immutable {baseline_id}")
        historical_regression[historical_preset] = {
            "status": "PASS", "deck_sha256": sha(old_deck_path), "byte_identical": True}

        direct_preset = "CB_DIRECT_D1_ALL_CLOCK" if rows == "1111" else "CB_DIRECT_D1_PAPER_CLOCK"
        direct_case, direct_stimulus, direct_params = platform.load_config(direct_preset)
        direct_render = platform.render(direct_case, direct_stimulus, direct_params, RUNS / direct_id)
        direct_deck_path = RUNS / direct_id / "deck.cir"
        if direct_render["deck"] != direct_deck_path.read_text(encoding="utf-8"):
            raise RuntimeError(f"CB_DIRECT render-only regression differs from immutable {direct_id}")
        historical_regression[direct_preset] = {
            "status": "PASS", "deck_sha256": sha(direct_deck_path), "byte_identical": True}
        if direct_case_manifest.get("case", {}).get("CBU_OVERRIDE_D1") != "CB_DIRECT":
            raise RuntimeError(f"comparison case is not the recorded CB_DIRECT D1 topology: {direct_id}")

        rendered = platform.render(case, stimulus, params, RUNS / run_id)
        if rendered["static_qa"].get("status") != "PASS":
            raise RuntimeError(f"platform static topology QA failed: {preset}")
        if rendered["static_qa"]["raw_estimate_bytes"] >= platform.MAX_RAW_BYTES:
            raise RuntimeError(f"raw estimate exceeds 100 MB single-file storage guard: {preset}")
        common = set(analysis.COMMON_SIGNALS)
        for reference_id in (baseline_id, direct_id):
            reference_probe = json_read(RUNS / reference_id / "probe_manifest.json")
            missing = sorted(common - {signal["label"] for signal in reference_probe["signals"]})
            if missing:
                raise RuntimeError(f"registered common comparison probes missing from {reference_id}: {missing}")
        missing_candidate = sorted(common - {signal["label"] for signal in rendered["probes"]["signals"]})
        if missing_candidate:
            raise RuntimeError(f"registered common comparison probes missing from {run_id}: {missing_candidate}")
        deck_lines = rendered["deck"].splitlines()
        exact_d1 = {
            "V_CBU_A_D1 DOUT_D1 CBU_JOIN_D1 0",
            "V_CARRY_IN_D1 C_D0 CARRY_CB_IN_D1 0",
            "XCB_CARRY_D1 CARRY_CB_IN_D1 CARRY_CB_OUT_D1 CB",
            "V_CBU_B_D1 CARRY_CB_OUT_D1 CBU_JOIN_D1 0",
            "V_T1_LINK_D1 CBU_JOIN_D1 T1_I_D1 0",
        }
        if not exact_d1.issubset(set(deck_lines)) or any(line.startswith("XCBU_D1 ") for line in deck_lines):
            raise RuntimeError(f"D1 carry-buffer actual deck mismatch: {preset}")
        if sum("CBU_JOIN_D1" in line for line in deck_lines
               if not line.startswith(("*", ".print"))) != 3:
            raise RuntimeError(f"D1 JOIN has unexpected connection count: {preset}")
        if any(line.startswith(("R_TERM_D", "R_C_D", "XSJTL_CBU_D1", "XJTL_CBU_D1"))
               for line in deck_lines):
            raise RuntimeError(f"unexpected terminal, carry load, or added isolator found: {preset}")
        baseline_deck = old_deck_path.read_text(encoding="utf-8")
        if _normalized_deck(rendered["deck"]) != _normalized_deck(baseline_deck):
            raise RuntimeError(f"non-D1 physical network differs from A021/A022: {preset}")
        if rendered["stimulus_text"] != (RUNS / baseline_id / "stimulus.inc").read_text(encoding="utf-8"):
            raise RuntimeError(f"stimulus.inc is not byte-identical to matched baseline: {preset}")

        item = {"run_id": run_id, "preset": preset, "case": case, "stimulus": stimulus,
                "params": params, "rendered": rendered, "baseline": baseline,
                "direct_candidate": direct, "deck_sha256": hashlib.sha256(rendered["deck"].encode()).hexdigest(),
                "stimulus_sha256": hashlib.sha256(rendered["stimulus_text"].encode()).hexdigest(),
                "probe_sha256": hashlib.sha256((json.dumps(rendered["probes"], ensure_ascii=False, indent=2)+"\n").encode()).hexdigest()}
        rendered_cases.append(item)

        if run_josim_sanity:
            with tempfile.TemporaryDirectory(prefix=".cb-carry-buffer-static-", dir=RUNS) as temp_name:
                temp = Path(temp_name)
                (temp / "deck.cir").write_text(rendered["deck"], encoding="utf-8")
                (temp / "stimulus.inc").write_text(rendered["stimulus_text"], encoding="utf-8")
                (temp / "sources" / "t1_cell_tunable.cir").parent.mkdir(parents=True, exist_ok=True)
                (temp / "sources" / "t1_cell_tunable.cir").write_text(rendered["t1_source_text"], encoding="utf-8")
                for relpath, text in rendered["chain_source_texts"].items():
                    target = temp / relpath
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text(text, encoding="utf-8")
                command = [str(platform.SOLVER)]
                for subckt in STATIC_SUBCKTS:
                    command.extend(("-s", subckt))
                command.append(str(temp / "deck.cir"))
                completed = subprocess.run(command, cwd=temp, capture_output=True, text=True,
                                           check=False, timeout=120)
                stdout_bytes = completed.stdout.encode("utf-8")
                stderr_bytes = completed.stderr.encode("utf-8")
                syntax = {"run_id": run_id, "argv": command, "exit_code": completed.returncode,
                          "physical_solve_count": 0,
                          "stdout_sha256": hashlib.sha256(stdout_bytes).hexdigest(),
                          "stdout_bytes": len(stdout_bytes), "stdout_line_count": len(completed.stdout.splitlines()),
                          "stdout_tail": completed.stdout.splitlines()[-8:],
                          "stderr_sha256": hashlib.sha256(stderr_bytes).hexdigest(),
                          "stderr_bytes": len(stderr_bytes), "stderr_tail": completed.stderr.splitlines()[-8:]}
                static_deck_records.append(syntax)
                if completed.returncode != 0:
                    raise RuntimeError(f"JoSIM -s static syntax check failed for {preset}: {syntax}")

    return rendered_cases, {"sources": source_records, "historical_render_regression": historical_regression,
                            "josim_static_sanity": static_deck_records}


def _preflight_text(qa: dict[str, Any], cases: list[dict[str, Any]]) -> str:
    rows = [
        "# A025/A026 D1 carry-side CB_0928 preflight", "",
        "This experiment is governed by docs/EXPERIMENT_CONTRACT.md.", "",
        f"- Batch: `{BATCH_ID}`; risk: `NORMAL`; physical solves authorized: `2`.",
        f"- Preflight HEAD: `{qa['parent_head']}`; solver: `{qa['solver']['path']}`; SHA-256: `{qa['solver']['sha256']}`.",
        "- Source closure is pinned in `STATIC_QA.json`; canonical CB_0928 ports are `IN OUT` and its SHA is verified.",
        "- Topology change is only the D1 carry branch: `C_D0 -> V_CARRY_IN_D1 -> XCB_CARRY_D1 (CB_0928) -> V_CBU_B_D1 -> CBU_JOIN_D1`; `DOUT_D1 -> V_CBU_A_D1 -> CBU_JOIN_D1`; `V_T1_LINK_D1 -> T1_D1.I`.",
        "- No CB/JTL/sJTL/other component is added after JOIN. D1 has no `THmitll_MERGE`; D2-D6 remain `THmitll_MERGE`.",
        "- All array BVM/QB/CB/sJTL, T1/DFF, biases, loads, clock, and stimulus otherwise match A021/A022; D0 uses the original single entrance sJTL.",
        "- Frozen timing: DT=0.01 ps; STOP=300 ps; global single clock at 200 ps, 1.2 mV, 1/2/1 ps, series R=2 ohm.",
        "- Windows are half-open and use actual stored timestamps: ARRAY_FINAL_READ [110,121), PRE_CLOCK [121,200), CLOCK_EDGE [200,205), POST_CLOCK [205,300), TOTAL [0,300) ps.",
        "- P is raw radians. Per-JJ phase is independently unwrapped; phase delta/(2π) is navigation arithmetic only. V area is same-JJ, same direction, same raw rows; no event classifier is defined.",
        "- Interpretation ceiling: artifact validity and registered arithmetic only. SFQ event classification, mechanism, isolation, and full multiplier function are not determined.",
        "- If static/solver/raw/mechanical artifact QA hard-fails, stop and preserve the attempt. Do not retry physics, tune parameters, add sJTL, or expand beyond A025/A026.",
        "", "## Locked run matrix", "",
        "| Run | ROW/COL | Override | Clock | DT / STOP | Probes / estimate | Baseline |", "|---|---|---|---|---|---|---|"]
    for item in cases:
        qa_run = item["rendered"]["static_qa"]
        baseline = RUN_MATRIX[[entry[0] for entry in RUN_MATRIX].index(item["run_id"])][4]
        rows.append(f"| {item['run_id']} | {item['case']['ROW_BITS']}/{item['case']['COL_BITS']} | CB_CARRY_BUFFER | GLOBAL_ONESHOT@200 ps | 0.01 / 300 ps | {item['rendered']['probes']['signal_count']} / {qa_run['raw_estimate_bytes']} B | {baseline} |")
    rows.extend(["", "## Frozen checks", "",
                 "- All three modes (`NONE`, `CB_DIRECT`, `CB_CARRY_BUFFER`) render; historical A021/A022 and A023/A024 decks remain byte-identical to their stored render.",
                 "- Candidate deck differs from its A021/A022 base only in the D1 carry topology and `.print` probe directives; `stimulus.inc` is byte-identical.",
                 "- JoSIM `-s` syntax/model check PASS; this is static validation and `physical_solve_count=0`.",
                 "- Static QA and per-run probe manifest are hash-bound in `WORK_UNIT.json`.", ""])
    return "\n".join(rows)


def prepare_preflight() -> int:
    cases, extras = _matrix(run_josim_sanity=True)
    task_paths = (PREFLIGHT, STATIC_QA, PROBE_REGISTRY, WORK_UNIT, BATCH_MANIFEST)
    if any(path.exists() for path in task_paths):
        raise RuntimeError("carry-buffer preflight outputs already exist; refusing overwrite")
    cb_source = extras["sources"]["CB"]
    qa = {"schema": "bvm-4x4-cb-carry-buffer-d1-static-qa-v1", "status": "PASS",
          "batch_id": BATCH_ID, "parent_head": git("rev-parse", "HEAD"),
          "risk_level": "NORMAL", "physical_solve_count": 0, "solver": platform._solver_info(),
          "runner_sha256": sha(Path(platform.__file__).resolve()),
          "batch_runner_sha256": sha(Path(__file__).resolve()),
          "analysis_runner_sha256": sha(SERIES / "scripts" / "analyze_cb_carry_buffer_d1.py"),
          "plotter_sha256": sha(platform.PLOTTER), "plotly_asset_sha256": sha(platform.PLOTLY_ASSET),
          "config_sha256": {path.relative_to(SERIES).as_posix(): sha(path) for path in
                            (platform.USER_CASE, platform.STIMULUS, platform.T1_PARAMS,
                             platform.CBU_PARAMS, platform.DFF_PARAMS, platform.D0_JTL_PARAMS)},
          "canonical_source_sha256": {role: item["sha256"] for role, item in extras["sources"].items()},
          "canonical_cb_0928": {"path": cb_source["path"], "sha256": cb_source["sha256"],
                                "ports": list(platform.subckt_pins(REPO / cb_source["path"], "CB")),
                                "parameters_from_source_only": True},
          "historical_render_regression": extras["historical_render_regression"],
          "josim_static_sanity": extras["josim_static_sanity"],
          "circuit_checks": {"D1_one_added_canonical_CB_on_C_D0_branch": True,
                             "D1_existing_array_final_CB_not_duplicated": True,
                             "D1_DOUT_and_buffered_carry_join_directly": True,
                             "D1_T1_link_direct_from_join": True,
                             "D1_no_THmitll_MERGE_or_direct_mode_instance": True,
                             "D1_no_added_sJTL_or_JTL": True,
                             "D2_D6_remain_THmitll_MERGE": True,
                             "D0_entry_JTL_unchanged": True,
                             "seven_T1_and_DFF_unchanged": True,
                             "global_clock_unchanged": True,
                             "no_DOUT_2ohm_or_Carry_output_parallel_load": True,
                             "actual_grid_not_resampled": True},
          "runs": [{"run_id": item["run_id"], "preset": item["preset"],
                    "baseline_run_id": RUN_MATRIX[index][4],
                    "direct_candidate_run_id": RUN_MATRIX[index][5],
                    "deck_sha256": item["deck_sha256"], "stimulus_sha256": item["stimulus_sha256"],
                    "probe_sha256": item["probe_sha256"],
                    "probe_count": item["rendered"]["probes"]["signal_count"],
                    "raw_estimate_bytes": item["rendered"]["static_qa"]["raw_estimate_bytes"],
                    "static_qa_status": item["rendered"]["static_qa"]["status"],
                    "output_sha": item["rendered"]["sources"]["CBU_D1_CARRY_BUFFER"]["sha256"]}
                   for index, item in enumerate(cases)],
          "raw_storage_guard": "PASS", "scientific_interpretation_performed": False}
    probe_manifest = {"schema": "bvm-4x4-cb-carry-buffer-d1-probe-registry-v1",
                      "manifests_by_run_id": {item["run_id"]: item["rendered"]["probes"] for item in cases}}
    PREFLIGHT.parent.mkdir(parents=True, exist_ok=True)
    json_new(STATIC_QA, qa)
    json_new(PROBE_REGISTRY, probe_manifest)
    PREFLIGHT.write_text(_preflight_text(qa, cases), encoding="utf-8", newline="\n")
    gate = TASK / "human-gate.yaml"
    manifest = json_read(EXPERIMENT_MANIFEST)
    auth = manifest.setdefault("authorization_batches", [])
    if any(item.get("batch_id") == BATCH_ID for item in auth):
        raise RuntimeError(f"authorization already registered: {BATCH_ID}")
    auth.append({"batch_id": BATCH_ID, "risk_level": "NORMAL",
                 "authorized_cases": [item[1] for item in RUN_MATRIX],
                 "run_ids": [item[0] for item in RUN_MATRIX],
                 "authorized_physical_solve_count": 2, "physical_solve_count_completed": 0,
                 "preflight_parent_head": qa["parent_head"],
                 "preflight_path": PREFLIGHT.relative_to(SERIES).as_posix(),
                 "preflight_sha256": sha(PREFLIGHT), "static_qa_sha256": sha(STATIC_QA),
                 "scientific_interpretation_performed": False, "automatic_follow_up": False})
    authorized = manifest.setdefault("authorized_physical_solves", [])
    for _run_id, preset, *_ in RUN_MATRIX:
        if preset not in authorized:
            authorized.append(preset)
    manifest["maximum_physical_solve_count"] = max(int(manifest.get("maximum_physical_solve_count", 0)),
                                                    int(manifest.get("physical_solve_count", 0)) + 2)
    json_replace(EXPERIMENT_MANIFEST, manifest)
    work_unit = {"schema": "bvm-4x4-cb-carry-buffer-d1-work-unit-v1",
                 "batch_id": BATCH_ID, "experiment_risk_level": "NORMAL",
                 "parent_head_at_preflight": qa["parent_head"],
                 "authorized_run_ids": [item[0] for item in RUN_MATRIX],
                 "physical_solve_count_authorized": 2, "physical_solve_count_completed_at_registration": 0,
                 "preflight_sha256": sha(PREFLIGHT), "static_qa_sha256": sha(STATIC_QA),
                 "probe_manifest_sha256": sha(PROBE_REGISTRY),
                 "experiment_yaml_sha256": sha(TASK / "experiment.yaml"),
                 "metric_spec_sha256": sha(TASK / "METRIC_SPEC.json"),
                 "human_gate_sha256": sha(gate), "experiment_manifest_sha256": sha(EXPERIMENT_MANIFEST),
                 "runner_sha256": sha(Path(platform.__file__).resolve()),
                 "batch_runner_sha256": sha(Path(__file__).resolve()),
                 "analysis_runner_sha256": sha(SERIES / "scripts" / "analyze_cb_carry_buffer_d1.py"),
                 "source_sha256": {role: item["sha256"] for role, item in extras["sources"].items()},
                 "baseline_raw_sha256": {run_id: BASELINE_RAW_SHA256[run_id]
                                         for run_id in BASELINE_RAW_SHA256},
                 "scientific_interpretation_performed": False, "automatic_follow_up": False,
                 "next_action": "COMMIT_PREFLIGHT_THEN_RUN_EXACT_TWO_CASE_BATCH_AND_STOP"}
    json_new(WORK_UNIT, work_unit)
    batch = {"schema": "bvm-4x4-cb-carry-buffer-d1-batch-v1", "batch_id": BATCH_ID,
             "status": "PREFLIGHT_PASS_READY", "preflight_parent_head": qa["parent_head"],
             "preflight_path": PREFLIGHT.relative_to(SERIES).as_posix(),
             "preflight_sha256": sha(PREFLIGHT), "static_qa_path": STATIC_QA.relative_to(SERIES).as_posix(),
             "static_qa_sha256": sha(STATIC_QA), "metric_spec_path": (TASK / "METRIC_SPEC.json").relative_to(SERIES).as_posix(),
             "metric_spec_sha256": sha(TASK / "METRIC_SPEC.json"),
             "authorized_run_ids": [item[0] for item in RUN_MATRIX], "runs": [],
             "physical_solve_count_authorized": 2, "physical_solve_count_completed": 0,
             "scientific_interpretation_performed": False, "automatic_follow_up": False}
    json_new(BATCH_MANIFEST, batch)
    print(f"STATIC PREFLIGHT PASS: {BATCH_ID}; parent={qa['parent_head']}")
    print(f"JoSIM -s syntax/model checks: PASS; canonical CB SHA={cb_source['sha256']}")
    for item in cases:
        static_run = next(row for row in qa["runs"] if row["run_id"] == item["run_id"])
        print(f"{item['run_id']} {item['preset']}: probes={static_run['probe_count']} "
              f"estimated_raw={static_run['raw_estimate_bytes']}B deck={static_run['deck_sha256'][:12]} PASS")
    print("A021/A022 MERGE and A023/A024 CB_DIRECT render-only regression: PASS")
    print("physical_solve_count=0; no run/raw directories created by preflight.")
    return 0


def _update_authorization_completed(count: int, *, execution_head: str | None = None) -> None:
    data = json_read(EXPERIMENT_MANIFEST)
    records = [item for item in data.get("authorization_batches", []) if item.get("batch_id") == BATCH_ID]
    if len(records) != 1:
        raise RuntimeError("expected one authorization record for carry-buffer batch")
    record = records[0]
    if execution_head is not None:
        record["parent_head_at_execution"] = execution_head
    record["physical_solve_count_completed"] = count
    json_replace(EXPERIMENT_MANIFEST, data)


def run_batch() -> int:
    if git("status", "--porcelain"):
        raise RuntimeError("physical solve requires the preflight/source commit and a clean worktree")
    if not all(path.is_file() for path in (PREFLIGHT, STATIC_QA, PROBE_REGISTRY, WORK_UNIT, BATCH_MANIFEST)):
        raise RuntimeError("locked carry-buffer preflight/work-unit is missing")
    qa, unit, batch = json_read(STATIC_QA), json_read(WORK_UNIT), json_read(BATCH_MANIFEST)
    if (qa.get("status") != "PASS" or batch.get("status") != "PREFLIGHT_PASS_READY" or
            batch.get("physical_solve_count_completed") != 0 or
            unit.get("physical_solve_count_authorized") != 2 or
            unit.get("authorized_run_ids") != [item[0] for item in RUN_MATRIX]):
        raise RuntimeError("locked preflight does not authorize exactly A025/A026")
    if (unit.get("preflight_sha256") != sha(PREFLIGHT) or
            unit.get("static_qa_sha256") != sha(STATIC_QA) or
            unit.get("probe_manifest_sha256") != sha(PROBE_REGISTRY) or
            unit.get("metric_spec_sha256") != sha(TASK / "METRIC_SPEC.json") or
            unit.get("experiment_yaml_sha256") != sha(TASK / "experiment.yaml") or
            unit.get("human_gate_sha256") != sha(TASK / "human-gate.yaml") or
            unit.get("analysis_runner_sha256") != sha(SERIES / "scripts" / "analyze_cb_carry_buffer_d1.py") or
            unit.get("experiment_manifest_sha256") != sha(EXPERIMENT_MANIFEST)):
        raise RuntimeError("preflight-bound task input hash changed; refusing solve")
    if (qa.get("runner_sha256") != sha(Path(platform.__file__).resolve()) or
            qa.get("batch_runner_sha256") != sha(Path(__file__).resolve()) or
            qa.get("analysis_runner_sha256") != sha(SERIES / "scripts" / "analyze_cb_carry_buffer_d1.py") or
            qa.get("plotter_sha256") != sha(platform.PLOTTER) or
            qa.get("plotly_asset_sha256") != sha(platform.PLOTLY_ASSET)):
        raise RuntimeError("runner or visualization tool identity differs from locked preflight")
    current_config_sha = {path.relative_to(SERIES).as_posix(): sha(path) for path in
                          (platform.USER_CASE, platform.STIMULUS, platform.T1_PARAMS,
                           platform.CBU_PARAMS, platform.DFF_PARAMS, platform.D0_JTL_PARAMS)}
    if qa.get("config_sha256") != current_config_sha:
        raise RuntimeError("platform config changed after preflight")
    cases, extras = _matrix(run_josim_sanity=False)
    locked_runs = {item["run_id"]: item for item in qa["runs"]}
    for item in cases:
        lock = locked_runs[item["run_id"]]
        if (lock.get("deck_sha256") != item["deck_sha256"] or
                lock.get("stimulus_sha256") != item["stimulus_sha256"] or
                lock.get("probe_sha256") != item["probe_sha256"]):
            raise RuntimeError(f"render differs from frozen preflight: {item['run_id']}")
    solver = platform._solver_info()
    if (solver["path"], solver["version"], solver["sha256"]) != (
            qa["solver"]["path"], qa["solver"]["version"], qa["solver"]["sha256"]):
        raise RuntimeError("JoSIM binary identity differs from preflight")
    if BATCH_MANIFEST.exists() is False:
        raise RuntimeError("batch manifest disappeared after preflight")

    batch.update({"status": "RUNNING", "execution_head": solver["parent_head"], "runs": []})
    json_replace(BATCH_MANIFEST, batch)
    _update_authorization_completed(0, execution_head=solver["parent_head"])
    for item in cases:
        print(f"START {item['run_id']}: {item['preset']} ROW/COL="
              f"{item['case']['ROW_BITS']}/{item['case']['COL_BITS']} CBU_OVERRIDE_D1=CB_CARRY_BUFFER",
              flush=True)
        code, result = platform.run_one(
            item["case"], item["stimulus"], item["params"], solver,
            batch_id=BATCH_ID, run_id_override=item["run_id"],
            rendered_override=item["rendered"], preflight_path=PREFLIGHT,
            metric_spec_path_override=TASK / "METRIC_SPEC.json",
            expected_deck_sha256=locked_runs[item["run_id"]]["deck_sha256"])
        record = {"run_id": item["run_id"], "preset": item["preset"],
                  "status": result.get("status"), "artifact_status": result.get("artifact_status"),
                  "physical_solve_count": result.get("physical_solve_count", 1),
                  "qa_status": result.get("qa_status"), "raw_sha256": result.get("raw_sha256"),
                  "raw_bytes": result.get("raw_bytes"), "deck_sha256": result.get("deck_sha256")}
        batch["runs"].append(record)
        batch["physical_solve_count_completed"] += int(result.get("physical_solve_count", 1))
        batch["status"] = "RUNNING" if code == 0 else "STOPPED_AFTER_ARTIFACT_FAILURE"
        json_replace(BATCH_MANIFEST, batch)
        _update_authorization_completed(batch["physical_solve_count_completed"])
        print(json.dumps(result, ensure_ascii=False), flush=True)
        if code != 0:
            print("STOP: hard solver/raw/mechanical failure; preserve files; no retry/follow-up.",
                  file=sys.stderr, flush=True)
            return code

    analyzer = SERIES / "scripts" / "analyze_cb_carry_buffer_d1.py"
    completed = subprocess.run([sys.executable, str(analyzer), "--write"], cwd=REPO,
                               check=False, timeout=600)
    if completed.returncode != 0:
        batch["status"] = "POSTPROCESS_FAILURE_RAW_PRESERVED"
        json_replace(BATCH_MANIFEST, batch)
        return completed.returncode
    analysis = json_read(TASK / "BATCH_ANALYSIS.json")
    if analysis.get("status") != "PASS":
        batch["status"] = "POSTPROCESS_FAILURE_RAW_PRESERVED"
        json_replace(BATCH_MANIFEST, batch)
        return 2
    batch.update({"status": "MECHANICAL_QA_PASS_AWAITING_USER_REVIEW",
                  "analysis_path": (TASK / "BATCH_ANALYSIS.json").relative_to(SERIES).as_posix(),
                  "analysis_sha256": sha(TASK / "BATCH_ANALYSIS.json"),
                  "scientific_interpretation_performed": False,
                  "automatic_follow_up": False})
    json_replace(BATCH_MANIFEST, batch)
    print(json.dumps({"status": batch["status"], "batch_id": BATCH_ID,
                      "run_ids": [item[0] for item in RUN_MATRIX],
                      "physical_solve_count": batch["physical_solve_count_completed"],
                      "raw_sha256_by_run": {item["run_id"]: item["raw_sha256"] for item in batch["runs"]},
                      "scientific_interpretation_performed": False,
                      "automatic_follow_up": False}, ensure_ascii=False, indent=2), flush=True)
    return 0


def main() -> int:
    if sys.argv[1:] == ["--prepare-preflight"]:
        try:
            return prepare_preflight()
        except Exception as exc:
            print(f"PREFLIGHT_FAIL: {type(exc).__name__}: {exc}", file=sys.stderr)
            return 2
    if sys.argv[1:] == ["--run-batch"]:
        try:
            return run_batch()
        except Exception as exc:
            print(f"BATCH_STOP: {type(exc).__name__}: {exc}", file=sys.stderr)
            return 2
    print("usage: cb_carry_buffer_d1_batch.py --prepare-preflight | --run-batch", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
