#!/usr/bin/env python3
"""One-shot, immutable runner for the isolated Scheme-B T1 CLK-only test."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

EXPERIMENT = Path(__file__).resolve().parents[1]
REPO = Path(__file__).resolve().parents[4]
PLATFORM = REPO / "test/exploration/bvm-qb-cb-array-topology-v1-20260924"
PLATFORM_SCRIPTS = PLATFORM / "scripts"
RUN_ID = "A001_T1_CLK_ONLY"
RUNS = EXPERIMENT / "runs"
CONFIG_PATH = EXPERIMENT / "USER_CASE.env"
METRIC_SPEC = EXPERIMENT / "analysis" / "metric_spec.json"
T1_SOURCE = REPO / "circuits/t1/t1_cell.cir"
JJMIT_SOURCE = REPO / "circuits/models/jjmit.cir"
SOLVER = REPO / "build/josim-cli"

sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(PLATFORM_SCRIPTS))

from bvmtools.raw import read_csv  # noqa: E402
from components import load_reference, verify_reference_sources  # noqa: E402
from config import (ConfigError, T1_BIAS_KEYS, T1_PULSE_KEYS,
                    load_env, parse_quantity, validate_t1_clock)  # noqa: E402
from topology import T1_EXPECTED_PINS, parse_subcircuits  # noqa: E402


CONFIG_KEYS = (T1_BIAS_KEYS | {"T1_R_S", "T1_R_C"} | T1_PULSE_KEYS
               | {"EXPERIMENT_ID", "PROBE_PROFILE", "T1_BIAS3_SOURCE", "T1_CLK_MODE",
                  "DT", "STOP"})
JJ_ORDER = tuple(f"B_J{index}" for index in range(1, 12))
REQUIRED_JJ_SET = {"B_J2", "B_J3", "B_J7", "B_J9", "B_J11"}
REGISTERED_VALUES = {
    "T1_BIAS1": "1.8m", "T1_BIAS2": "1.8m", "T1_BIAS3": "1.8m",
    "T1_BIAS3_SOURCE": "VOLTAGE", "T1_R_S": "12", "T1_R_C": "12",
    "T1_CLK_MODE": "PULSE", "T1_CLK_START": "170p", "T1_CLK_PERIOD": "50p",
    "T1_CLK_AMPLITUDE": "1.2m", "T1_CLK_RISE": "1p", "T1_CLK_WIDTH": "2p",
    "T1_CLK_FALL": "1p", "T1_CLK_R_SERIES": "5", "DT": "0.01p", "STOP": "370p",
}


def sha256(path: str | Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8")


def git_head() -> str:
    result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, check=True,
                            capture_output=True, text=True)
    return result.stdout.strip()


def stable_env(values: dict[str, str]) -> str:
    return "".join(f"{key}={values[key]}\n" for key in sorted(values))


def load_config() -> tuple[dict[str, str], dict[str, Any], list[str]]:
    values = load_env(CONFIG_PATH, CONFIG_KEYS)
    if values["EXPERIMENT_ID"] != EXPERIMENT.name:
        raise ConfigError("EXPERIMENT_ID must match the standalone directory name")
    if values["PROBE_PROFILE"] != "debug":
        raise ConfigError("the CLK-only fixture requires PROBE_PROFILE=debug")
    for key, expected in REGISTERED_VALUES.items():
        if values[key] != expected:
            raise ConfigError(f"{key} must equal the single preregistered value {expected}")
    dt = parse_quantity(values["DT"], label="DT")
    stop = parse_quantity(values["STOP"], label="STOP")
    if dt <= 0 or stop <= 0:
        raise ConfigError("DT and STOP must be positive")
    clock = validate_t1_clock(values, stop)
    if values["T1_CLK_MODE"] != "PULSE":
        raise ConfigError("the standalone experiment requires T1_CLK_MODE=PULSE")
    verify_reference_sources(load_reference(), roles=("T1",))
    subckt = parse_subcircuits({"T1": T1_SOURCE})["T1"]
    if tuple(pin.casefold() for pin in subckt.pins) != tuple(
            pin.casefold() for pin in T1_EXPECTED_PINS):
        raise ConfigError(f"T1 pin order changed: {subckt.pins}")
    if not REQUIRED_JJ_SET.issubset(subckt.elements):
        raise ConfigError("T1 source is missing one or more registered junction probes")
    source_text = T1_SOURCE.read_text(encoding="utf-8")
    if re.search(r"(?mi)^\s*R_J4\s+N8\s+N10\s+4(?:\s|$)", source_text) is None:
        raise ConfigError("T1 source no longer contains the frozen R_J4=4 ohm element")
    junctions = sorted((name for name in subckt.elements if re.fullmatch(r"B_J\d+", name)),
                       key=lambda name: int(re.search(r"\d+", name).group(0)))
    inductors = sorted((name for name in subckt.elements if re.fullmatch(r"L\d+", name)),
                       key=lambda name: int(re.search(r"\d+", name).group(0)))
    resistors = sorted(name for name in subckt.elements if re.fullmatch(r"R[A-Z]?\w*", name))
    labels = ["V(CLK_RAW)", "V(CLK)", "I(R_TRIG_CLK)", "V(S)", "V(C)",
              "I(R_S)", "I(R_C)", "V(N_BIAS1)", "V(N_BIAS2)", "V(N_BIAS3)"]
    for junction in junctions:
        labels.extend((f"P({junction}|XT1)", f"V({junction}|XT1)", f"I({junction}|XT1)"))
    for inductor in inductors:
        labels.extend((f"I({inductor}|XT1)", f"V({inductor}|XT1)"))
    for resistor in resistors:
        labels.extend((f"I({resistor}|XT1)", f"V({resistor}|XT1)"))
    if len(labels) != len(set(labels)):
        raise ConfigError("generated CLK-only probe list contains duplicate labels")
    return values, {"subcircuit": subckt, "junctions": junctions,
                    "inductors": inductors, "resistors": resistors,
                    "probe_labels": labels, "clock": clock}, labels


def render_deck(values: dict[str, str], structure: dict[str, Any], run_dir: Path) -> str:
    include_model = Path(os.path.relpath(JJMIT_SOURCE, run_dir)).as_posix()
    include_t1 = Path(os.path.relpath(T1_SOURCE, run_dir)).as_posix()
    lines = [
        "* T1 periodic CLK-only fixture; data input I is tied to ground.",
        "* Scheme B external bias. This ideal voltage pulse is not an SFQ clock claim.",
        f".include {include_model}",
        f".include {include_t1}",
        f"V_BIAS1 N_BIAS1 0 DC {values['T1_BIAS1']}",
        f"V_BIAS2 N_BIAS2 0 DC {values['T1_BIAS2']}",
        f"V_BIAS3 N_BIAS3 0 DC {values['T1_BIAS3']}",
        f"R_S S 0 {values['T1_R_S']}",
        f"R_C C 0 {values['T1_R_C']}",
        "V_TRIG_CLK CLK_RAW 0 "
        f"PULSE(0 {values['T1_CLK_AMPLITUDE']} {values['T1_CLK_START']} "
        f"{values['T1_CLK_RISE']} {values['T1_CLK_FALL']} "
        f"{values['T1_CLK_WIDTH']} {values['T1_CLK_PERIOD']})",
        f"R_TRIG_CLK CLK_RAW CLK {values['T1_CLK_R_SERIES']}",
        "XT1 0 CLK S C N_BIAS1 N_BIAS2 N_BIAS3 T1",
        *[f".print {label}" for label in structure["probe_labels"]],
        f".tran {values['DT']} {values['STOP']}",
        ".end",
    ]
    return "\n".join(lines) + "\n"


def solver_identity() -> dict[str, Any]:
    if not SOLVER.is_file():
        raise ConfigError(f"JoSIM executable is missing: {SOLVER}")
    version = subprocess.run([str(SOLVER), "--version"], cwd=REPO,
                             capture_output=True, text=True, check=True)
    return {"path": SOLVER.relative_to(REPO).as_posix(), "sha256": sha256(SOLVER),
            "version": version.stdout.strip(), "version_exit": version.returncode}


def source_manifest() -> dict[str, Any]:
    return {
        "schema": "t1-clock-only-source-manifest-v1",
        "sources": [
            {"role": "JJMIT_MODEL", "path": JJMIT_SOURCE.relative_to(REPO).as_posix(),
             "sha256": sha256(JJMIT_SOURCE), "mode": "DIRECT_CANONICAL_INCLUDE"},
            {"role": "T1", "path": T1_SOURCE.relative_to(REPO).as_posix(),
             "sha256": sha256(T1_SOURCE), "mode": "DIRECT_CANONICAL_INCLUDE"},
        ],
        "t1_internal_source_modified": False,
        "scientific_interpretation_performed": False,
    }


def write_preflight(values: dict[str, str], structure: dict[str, Any],
                    solver: dict[str, Any]) -> Path:
    target = EXPERIMENT / "PREFLIGHT.md"
    if target.exists():
        raise ConfigError(f"refusing to overwrite preflight: {target}")
    head = git_head()
    definition = (EXPERIMENT / "experiment.yaml").read_text(encoding="utf-8")
    definition_head = re.search(r"(?m)^parent_head:\s*([0-9a-f]{40})\s*$", definition)
    if definition_head is None or definition_head.group(1) != head:
        raise ConfigError("experiment.yaml parent_head must match the current committed HEAD")
    probe_labels = structure["probe_labels"]
    source = source_manifest()
    pulse_end = (float(structure["clock"]["start_s"])
                 + float(structure["clock"]["rise_s"])
                 + float(structure["clock"]["width_s"])
                 + float(structure["clock"]["fall_s"]))
    lines = [
        "# T1 Scheme-B 20 GHz periodic clock-only preflight", "",
        "This experiment is governed by docs/EXPERIMENT_CONTRACT.md.", "",
        f"- experiment_id: `{EXPERIMENT.name}`",
        f"- parent HEAD: `{head}`",
        f"- solver: `{solver['path']}`; SHA-256 `{solver['sha256']}`",
        f"- solver version: `{solver['version']}`",
        f"- T1 source: `{source['sources'][1]['path']}` SHA-256 `{source['sources'][1]['sha256']}`",
        f"- jjmit model: `{source['sources'][0]['path']}` SHA-256 `{source['sources'][0]['sha256']}`",
        "- exact topology: one XT1 T1 instance; I pin connected to ground; no BVM/QB/CB/sJTL.",
        "- T1 internal netlist is source-verified and unchanged; R_J4 remains 4 ohm.",
        "- Scheme-B biases: V_BIAS1=1.8m, V_BIAS2=1.8m, V_BIAS3=1.8m.",
        "- output loads: R_S=12 ohm, R_C=12 ohm.",
        f"- clock source: `V_TRIG_CLK CLK_RAW 0 PULSE(0 {values['T1_CLK_AMPLITUDE']} "
        f"{values['T1_CLK_START']} {values['T1_CLK_RISE']} {values['T1_CLK_FALL']} "
        f"{values['T1_CLK_WIDTH']} {values['T1_CLK_PERIOD']})`.",
        f"- clock series path: `R_TRIG_CLK CLK_RAW CLK {values['T1_CLK_R_SERIES']}`; "
        "R_CLK_QUIET is absent.",
        "- scheduled triggers: 170p, 220p, 270p, 320p; pulse falls by "
        f"{pulse_end * 1e12:g} ps.",
        f"- solver transient settings: DT=`{values['DT']}`, STOP=`{values['STOP']}`.",
        f"- exact authorized run matrix: one solve `{RUN_ID}`; raw `runs/{RUN_ID}/raw.csv`.",
        f"- USER_CASE SHA-256: `{sha256(CONFIG_PATH)}`; metric spec SHA-256: `{sha256(METRIC_SPEC)}`.",
        f"- probe profile: DEBUG; exactly {len(probe_labels)} probes (registered below).",
        "- phase raw units: radians. Turn conversion is arithmetic only; not an SFQ count.",
        "- voltage integrals use trapezoids on actual stored time rows; no interpolation or resampling.",
        "- clock arrival uses the preregistered half-peak stored-sample bracket; no interpolated crossing.",
        "- pre-clock window: [150p,170p); cycles: [170p,220p), [220p,270p), "
        "[270p,320p), [320p,370p).",
        "- inter-pulse tail for each cycle: [cycle_start+4p,cycle_end).",
        "- exact stored-grid integration endpoints use first/last rows inside each half-open window.",
        "- timestep, parameter, and solver sensitivity are UNKNOWN; no convergence or sensitivity run is authorized.",
        "- interpretation ceiling: mechanical QA and registered arithmetic only; no SFQ-event, "
        "logic, truth-table, or system-throughput claim.",
        "- prohibited: integrated array solve, other masks/runs, sweeps, retry, parameter changes, "
        "or T1 internal netlist changes.",
        "", "## Registered probes", "", *[f"- `{label}`" for label in probe_labels], "",
        "## Required output artifacts", "",
        "`actual_deck.cir`, `raw.csv`, `run.log`, `stdout.txt`, `stderr.txt`, `metadata.json`,",
        "`provenance.json`, `source_manifest.json`, `probe_manifest.json`, `analysis/raw_qa.json`,",
        "`analysis/clock_cycle_metrics.json`, `analysis/clock_cycle_metrics.csv`, `analysis/plot_manifest.json`,",
        "`analysis/plot_qa.json`, and the registered classic full-run and per-cycle HTML pages.", "",
    ]
    target.write_text("\n".join(lines), encoding="utf-8")
    return target


def _write_run_preflight(run_dir: Path) -> None:
    (run_dir / "PREFLIGHT.md").write_bytes((EXPERIMENT / "PREFLIGHT.md").read_bytes())


def _save_initial_artifacts(run_dir: Path, values: dict[str, str],
                            structure: dict[str, Any], solver: dict[str, Any],
                            command: list[str]) -> dict[str, Any]:
    run_dir.mkdir(parents=True, exist_ok=False)
    (run_dir / "analysis").mkdir(parents=True, exist_ok=True)
    dt = parse_quantity(values["DT"], label="DT")
    stop = parse_quantity(values["STOP"], label="STOP")
    clock = structure["clock"]
    cycle_starts = [float(clock["start_s"]) + index * float(clock["period_s"])
                    for index in range(4)]
    snapshot = {**values, "cycle_starts_s": cycle_starts,
                "T1_CLK_PERIOD_S": float(clock["period_s"]),
                "dt_seconds": float(dt), "stop_seconds": float(stop)}
    (run_dir / "USER_CASE.snapshot.env").write_text(stable_env(values), encoding="utf-8")
    write_json(run_dir / "USER_CASE.snapshot.json", snapshot)
    (run_dir / "analysis/metric_spec.json").write_bytes(METRIC_SPEC.read_bytes())
    sources = source_manifest()
    write_json(run_dir / "source_manifest.json", sources)
    probe_manifest = {
        "schema": "t1-clock-only-probes-v1", "run_id": RUN_ID,
        "profile": "debug", "output_mode": "T1_CLK_ONLY",
        "signals": [{"label": label} for label in structure["probe_labels"]],
        "signal_count": len(structure["probe_labels"]),
        "scientific_interpretation_performed": False,
    }
    write_json(run_dir / "probe_manifest.json", probe_manifest)
    write_json(run_dir / "parameter_manifest.json", {
        "schema": "t1-clock-only-parameters-v1", "parameters": dict(values),
        "solver": {"DT": values["DT"], "STOP": values["STOP"]},
        "physical_solve_count": 1, "scientific_interpretation_performed": False,
    })
    write_json(run_dir / "topology_manifest.json", {
        "schema": "t1-clock-only-topology-v1", "instance": "XT1", "subcircuit": "T1",
        "source_pin_order": list(structure["subcircuit"].pins),
        "connections": {"I": "0", "CLK": "CLK", "S": "S", "C": "C",
                        "N_BIAS1": "N_BIAS1", "N_BIAS2": "N_BIAS2",
                        "N_BIAS3": "N_BIAS3"},
        "clock": {"mode": "PULSE", "source": "V_TRIG_CLK",
                  "source_node": "CLK_RAW", "series_resistor": "R_TRIG_CLK",
                  "t1_input_node": "CLK", "quiet_shunt_present": False},
        "data_input": {"signal": "I", "node": "0", "status": "GROUNDED"},
        "scientific_interpretation_performed": False,
    })
    deck = render_deck(values, structure, run_dir)
    (run_dir / "actual_deck.cir").write_text(deck, encoding="utf-8")
    _write_run_preflight(run_dir)
    (run_dir / "run.log").write_text(
        f"run_id={RUN_ID}\ncommand={shlex.join(command)}\nsolver_sha256={solver['sha256']}\n",
        encoding="utf-8")
    provenance = {
        "schema": "t1-clock-only-provenance-v1", "experiment_id": EXPERIMENT.name,
        "run_id": RUN_ID, "parent_head": git_head(),
        "physical_solve_count": 1, "scientific_interpretation_performed": False,
        "automatic_follow_up": False,
        "solver": solver, "command": command,
        "user_case": {"path": "USER_CASE.snapshot.env",
                      "sha256": sha256(run_dir / "USER_CASE.snapshot.env"),
                      "parameters": dict(values)},
        "experiment_definition": {"path": "../../experiment.yaml",
                                  "sha256": sha256(EXPERIMENT / "experiment.yaml")},
        "executor_sources": {
            name: sha256(EXPERIMENT / "scripts" / name)
            for name in ("run_clock_only.py", "clock_metrics.py", "plot_clock_only.py")
        },
        "metric_spec": {"path": "../../analysis/metric_spec.json",
                        "sha256": sha256(METRIC_SPEC)},
        "source_manifest": {"path": "source_manifest.json",
                             "sha256": sha256(run_dir / "source_manifest.json")},
        "actual_deck": {"path": "actual_deck.cir", "sha256": sha256(run_dir / "actual_deck.cir")},
        "parameter_manifest": {"path": "parameter_manifest.json",
                               "sha256": sha256(run_dir / "parameter_manifest.json")},
        "topology_manifest": {"path": "topology_manifest.json",
                              "sha256": sha256(run_dir / "topology_manifest.json")},
        "probe_manifest": {"path": "probe_manifest.json",
                           "sha256": sha256(run_dir / "probe_manifest.json")},
        "preflight": {"path": "PREFLIGHT.md", "sha256": sha256(run_dir / "PREFLIGHT.md")},
    }
    write_json(run_dir / "provenance.json", provenance)
    write_json(run_dir / "metadata.json", {
        "schema": "t1-clock-only-run-metadata-v1", "run_id": RUN_ID,
        "experiment_id": EXPERIMENT.name, "probe_profile": "debug",
        "output_mode": "T1_CLK_ONLY", "parent_head": provenance["parent_head"],
        "solver": solver, "actual_deck_sha256": provenance["actual_deck"]["sha256"],
        "parameter_manifest_sha256": provenance["parameter_manifest"]["sha256"],
        "topology_manifest_sha256": provenance["topology_manifest"]["sha256"],
        "source_manifest_sha256": provenance["source_manifest"]["sha256"],
        "probe_manifest_sha256": provenance["probe_manifest"]["sha256"],
        "user_case_sha256": provenance["user_case"]["sha256"],
        "preflight_sha256": provenance["preflight"]["sha256"],
        "physical_solve_count": 1, "scientific_interpretation_performed": False,
    })
    return provenance


def _finalize_experiment_manifest(run_dir: Path, status: str) -> None:
    raw_path = run_dir / "raw.csv"
    result_path = run_dir / "result.json"
    result = json.loads(result_path.read_text(encoding="utf-8")) if result_path.is_file() else {}
    write_json(EXPERIMENT / "experiment_manifest.json", {
        "schema": "t1-clock-only-experiment-manifest-v1",
        "experiment_id": EXPERIMENT.name, "status": status,
        "authorized_solve_count": 1,
        "runs": [{
            "run_id": RUN_ID, "path": f"runs/{RUN_ID}",
            "physical_solve_count": 1,
            "artifact_status": result.get("artifact_status", "INVALID"),
            "solver_exit_code": result.get("solver_exit_code"),
            "raw_sha256": sha256(raw_path) if raw_path.is_file() else None,
        }],
        "scientific_interpretation_performed": False,
        "automatic_follow_up": False,
    })


def _refresh_same_raw_qa(run_dir: Path, raw_sha_before: str,
                         analysis: dict[str, Any]) -> bool:
    """Refresh every derived hash/QA link after a no-solve analysis repair."""
    raw_path = run_dir / "raw.csv"
    raw_sha_after = sha256(raw_path)
    raw_qa_path = run_dir / "analysis/raw_qa.json"
    raw_qa = json.loads(raw_qa_path.read_text(encoding="utf-8"))
    raw_qa["sha256_after_plot"] = raw_sha_after
    raw_qa["raw_immutable"] = raw_sha_before == raw_sha_after
    raw_qa["status"] = "PASS" if raw_qa["raw_immutable"] else "FAIL"
    write_json(raw_qa_path, raw_qa)

    plot_qa = json.loads((run_dir / "analysis/plot_qa.json").read_text(encoding="utf-8"))
    metrics_path = run_dir / "analysis/clock_cycle_metrics.json"
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    result_path = run_dir / "result.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    provenance_path = run_dir / "provenance.json"
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    source_manifest_path = run_dir / "source_manifest.json"
    source_manifest = json.loads(source_manifest_path.read_text(encoding="utf-8"))
    source_hashes = {item["role"]: item["sha256"] for item in source_manifest["sources"]}

    mechanical_qa = {
        "schema": "t1-clock-only-mechanical-qa-v1",
        "status": "PASS" if (
            raw_sha_before == raw_sha_after and raw_qa.get("status") == "PASS"
            and plot_qa.get("status") == "PASS"
            and result.get("solver_exit_code") == 0
            and len(metrics.get("cycles", [])) == 4
        ) else "FAIL",
        "physical_solve_count": 1, "solver_exit_code": result.get("solver_exit_code"),
        "raw_sha256_before": raw_sha_before, "raw_sha256_after_plot": raw_sha_after,
        "raw_immutable": raw_sha_before == raw_sha_after,
        "sample_count": analysis["raw_qa"]["sample_count"],
        "time_start_s": analysis["raw_qa"]["time_start"],
        "time_end_s": analysis["raw_qa"]["time_end"],
        "dt_min_s": analysis["raw_qa"]["dt_min"],
        "dt_max_s": analysis["raw_qa"]["dt_max"],
        "uniform_time_grid": analysis["raw_qa"]["uniform_time_grid"],
        "probe_count": len(json.loads((run_dir / "probe_manifest.json").read_text(
            encoding="utf-8"))["signals"]),
        "cycle_count": len(metrics.get("cycles", [])),
        "raw_qa_status": raw_qa.get("status"), "plot_qa_status": plot_qa.get("status"),
        "scientific_interpretation_performed": False,
    }
    mechanical_qa_path = run_dir / "analysis/mechanical_qa.json"
    write_json(mechanical_qa_path, mechanical_qa)

    executor_hashes = {
        name: sha256(EXPERIMENT / "scripts" / name)
        for name in ("clock_metrics.py", "plot_clock_only.py")
    }
    revision = {
        "revision_id": "exact-decimal-half-open-time-windows-v1",
        "reason": "Use exact decimal raw-time tokens so a sample exactly at a cycle boundary belongs only to the next half-open cycle.",
        "raw_sha256": raw_sha_after, "physical_solve_count": 0,
        "executor_sources": executor_hashes,
        "scientific_interpretation_performed": False,
    }
    revisions = [item for item in provenance.get("analysis_revisions", [])
                 if item.get("revision_id") != revision["revision_id"]]
    revisions.append(revision)
    provenance["analysis_revisions"] = revisions
    provenance_qa = {
        "schema": "t1-clock-only-provenance-qa-v1",
        "parent_head": provenance.get("parent_head"),
        "t1_source_sha256": sha256(T1_SOURCE), "jjmit_sha256": sha256(JJMIT_SOURCE),
        "source_manifest_sha256": sha256(source_manifest_path),
        "source_hashes_match": source_hashes.get("T1") == sha256(T1_SOURCE)
        and source_hashes.get("JJMIT_MODEL") == sha256(JJMIT_SOURCE),
        "deck_sha256": sha256(run_dir / "actual_deck.cir"),
        "parameter_manifest_sha256": sha256(run_dir / "parameter_manifest.json"),
        "topology_manifest_sha256": sha256(run_dir / "topology_manifest.json"),
        "user_case_sha256": sha256(run_dir / "USER_CASE.snapshot.env"),
        "preflight_sha256": sha256(run_dir / "PREFLIGHT.md"),
        "metric_spec_sha256": sha256(METRIC_SPEC),
        "analysis_revision_executor_hashes_match": executor_hashes == revision["executor_sources"],
        "scientific_interpretation_performed": False,
    }
    provenance_qa["status"] = "PASS" if (
        provenance.get("source_manifest", {}).get("sha256")
        == provenance_qa["source_manifest_sha256"]
        and provenance_qa["source_hashes_match"]
        and provenance.get("actual_deck", {}).get("sha256") == provenance_qa["deck_sha256"]
        and provenance.get("parameter_manifest", {}).get("sha256")
        == provenance_qa["parameter_manifest_sha256"]
        and provenance.get("topology_manifest", {}).get("sha256")
        == provenance_qa["topology_manifest_sha256"]
        and provenance.get("user_case", {}).get("sha256") == provenance_qa["user_case_sha256"]
        and provenance.get("preflight", {}).get("sha256") == provenance_qa["preflight_sha256"]
        and provenance.get("metric_spec", {}).get("sha256") == provenance_qa["metric_spec_sha256"]
        and provenance_qa["analysis_revision_executor_hashes_match"]
        and revision["raw_sha256"] == raw_sha_after
    ) else "FAIL"
    provenance_qa_path = run_dir / "analysis/provenance_qa.json"
    write_json(provenance_qa_path, provenance_qa)

    analysis_paths = {
        "mechanical_metrics": metrics_path,
        "raw_qa": raw_qa_path,
        "plot_qa": run_dir / "analysis/plot_qa.json",
        "mechanical_qa": mechanical_qa_path,
        "provenance_qa": provenance_qa_path,
        "transformation_registry": run_dir / "analysis/transformation_registry.json",
    }
    for key, path in analysis_paths.items():
        provenance[key] = {"path": str(path.relative_to(run_dir)), "sha256": sha256(path)}
    write_json(provenance_path, provenance)

    qa_pass = mechanical_qa["status"] == "PASS" and provenance_qa["status"] == "PASS"
    result.update({
        "status": "MECHANICAL_QA_PASS_AWAITING_USER_REVIEW" if qa_pass
        else "MECHANICAL_QA_FAIL_AWAITING_USER_REVIEW",
        "artifact_status": "VALID" if raw_sha_before == raw_sha_after else "INVALID",
        "physical_solve_count": 1, "raw_sha256": raw_sha_after,
        "sample_count": analysis["raw_qa"]["sample_count"],
        "time_range_s": [analysis["raw_qa"]["time_start"], analysis["raw_qa"]["time_end"]],
        "raw_qa_status": raw_qa["status"], "plot_qa_status": plot_qa.get("status"),
        "mechanical_qa_status": mechanical_qa["status"],
        "provenance_qa_status": provenance_qa["status"],
        "scientific_interpretation_performed": False, "automatic_follow_up": False,
    })
    write_json(result_path, result)
    metadata_path = run_dir / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata.update({"raw_sha256": raw_sha_after,
                     "sample_count": analysis["raw_qa"]["sample_count"],
                     "plot_qa_status": plot_qa.get("status"),
                     "mechanical_qa_status": mechanical_qa["status"],
                     "provenance_qa_status": provenance_qa["status"],
                     "analysis_revision_id": revision["revision_id"]})
    write_json(metadata_path, metadata)
    (run_dir / "RESULT_BRIEF.md").write_text(
        f"# {EXPERIMENT.name} / {RUN_ID}\n\n"
        f"- status: `{result['status']}`\n- physical_solve_count: `1`\n"
        f"- artifact_status: `{result['artifact_status']}`\n"
        f"- raw SHA-256: `{raw_sha_after}`; samples: `{analysis['raw_qa']['sample_count']}`\n"
        f"- raw / plot / mechanical / provenance QA: `{raw_qa['status']}` / "
        f"`{plot_qa.get('status')}` / `{mechanical_qa['status']}` / "
        f"`{provenance_qa['status']}`\n"
        "- analysis repair: exact-decimal half-open window membership; physical solve count `0`.\n"
        "- derived phase/voltage arithmetic only; no SFQ-event, truth-table, or throughput interpretation.\n"
        "- scientific interpretation: `NOT_PERFORMED`; automatic follow-up: `false`.\n",
        encoding="utf-8")
    _finalize_experiment_manifest(
        run_dir, "COMPLETE_MECHANICAL" if qa_pass else "ARTIFACT_INVALID")
    return qa_pass


def run_once(values: dict[str, str], structure: dict[str, Any], solver: dict[str, Any]) -> int:
    run_dir = RUNS / RUN_ID
    if run_dir.exists():
        raise ConfigError(f"refusing to overwrite existing immutable run directory: {run_dir}")
    if (EXPERIMENT / "experiment_manifest.json").exists():
        raise ConfigError("experiment_manifest.json already exists; this one-shot experiment cannot run again")
    preflight = (EXPERIMENT / "PREFLIGHT.md").read_text(encoding="utf-8")
    if "This experiment is governed by docs/EXPERIMENT_CONTRACT.md." not in preflight:
        raise ConfigError("PREFLIGHT contract statement is missing")
    preflight_head = re.search(r"(?m)^- parent HEAD: `([0-9a-f]{40})`$", preflight)
    if preflight_head is None or preflight_head.group(1) != git_head():
        raise ConfigError("PREFLIGHT parent HEAD differs from the current committed HEAD")
    definition_head = re.search(r"(?m)^parent_head:\s*([0-9a-f]{40})\s*$",
                                (EXPERIMENT / "experiment.yaml").read_text(encoding="utf-8"))
    if definition_head is None or definition_head.group(1) != git_head():
        raise ConfigError("experiment.yaml parent_head differs from current HEAD")
    if f"USER_CASE SHA-256: `{sha256(CONFIG_PATH)}`" not in preflight:
        raise ConfigError("PREFLIGHT USER_CASE hash does not match the live standalone config")
    if f"metric spec SHA-256: `{sha256(METRIC_SPEC)}`" not in preflight:
        raise ConfigError("PREFLIGHT metric-spec hash does not match the registered metric spec")
    if sha256(T1_SOURCE) not in preflight or sha256(JJMIT_SOURCE) not in preflight:
        raise ConfigError("PREFLIGHT source hashes do not match current canonical inputs")
    command = [str(SOLVER), "-a", "1", "-o", str(run_dir / "raw.csv"),
               str(run_dir / "actual_deck.cir")]
    provenance = _save_initial_artifacts(run_dir, values, structure, solver, command)
    started = datetime.now(timezone.utc).isoformat()
    completed = subprocess.run(command, cwd=run_dir, capture_output=True, text=True, check=False)
    (run_dir / "stdout.txt").write_text(completed.stdout, encoding="utf-8")
    (run_dir / "stderr.txt").write_text(completed.stderr, encoding="utf-8")
    (run_dir / "run.log").write_text(
        f"run_id={RUN_ID}\nstarted_at={started}\ncommand={shlex.join(command)}\n"
        f"exit_code={completed.returncode}\n", encoding="utf-8")
    if completed.returncode != 0 or not (run_dir / "raw.csv").is_file():
        write_json(run_dir / "result.json", {
            "schema": "t1-clock-only-result-v1", "run_id": RUN_ID,
            "status": "SOLVER_FAILURE", "artifact_status": "INVALID",
            "solver_exit_code": completed.returncode, "physical_solve_count": 1,
            "scientific_interpretation_performed": False,
        })
        _finalize_experiment_manifest(run_dir, "SOLVER_FAILURE")
        return completed.returncode or 2
    raw_hash = sha256(run_dir / "raw.csv")
    provenance["started_at_utc"] = started
    provenance["raw"] = {"path": "raw.csv", "sha256": raw_hash,
                         "bytes": (run_dir / "raw.csv").stat().st_size}
    write_json(run_dir / "provenance.json", provenance)
    try:
        from clock_metrics import write_analysis
        analysis = write_analysis(run_dir)
        plot = subprocess.run([sys.executable, str(EXPERIMENT / "scripts/plot_clock_only.py"),
                               str(run_dir)], cwd=REPO, capture_output=True, text=True, check=False)
        (run_dir / "plot_stdout.txt").write_text(plot.stdout, encoding="utf-8")
        (run_dir / "plot_stderr.txt").write_text(plot.stderr, encoding="utf-8")
        if plot.returncode != 0:
            raise RuntimeError(f"classic plot QA failed: {plot.stderr.strip()}")
        raw_hash_after = sha256(run_dir / "raw.csv")
        if raw_hash_after != raw_hash or analysis["raw_sha256"] != raw_hash:
            raise RuntimeError("raw SHA changed during analysis or visualization")
        raw_qa_path = run_dir / "analysis/raw_qa.json"
        raw_qa_data = json.loads(raw_qa_path.read_text(encoding="utf-8"))
        raw_qa_data["sha256_after_plot"] = raw_hash_after
        raw_qa_data["raw_immutable"] = raw_hash_after == raw_hash
        raw_qa_data["status"] = "PASS" if raw_hash_after == raw_hash else "FAIL"
        write_json(raw_qa_path, raw_qa_data)
        plot_qa = json.loads((run_dir / "analysis/plot_qa.json").read_text(encoding="utf-8"))
        source_manifest_data = json.loads(
            (run_dir / "source_manifest.json").read_text(encoding="utf-8"))
        source_hashes = {source["role"]: source["sha256"]
                         for source in source_manifest_data["sources"]}
        metric_path = run_dir / "analysis/clock_cycle_metrics.json"
        transformation_path = run_dir / "analysis/transformation_registry.json"
        mechanical_qa = {
            "schema": "t1-clock-only-mechanical-qa-v1",
            "status": "PASS" if completed.returncode == 0 and raw_hash_after == raw_hash
            and raw_qa_data["status"] == "PASS" and plot_qa["status"] == "PASS" else "FAIL",
            "physical_solve_count": 1, "solver_exit_code": completed.returncode,
            "raw_sha256_before": raw_hash, "raw_sha256_after_plot": raw_hash_after,
            "raw_immutable": raw_hash_after == raw_hash,
            "sample_count": analysis["raw_qa"]["sample_count"],
            "time_start_s": analysis["raw_qa"]["time_start"],
            "time_end_s": analysis["raw_qa"]["time_end"],
            "dt_min_s": analysis["raw_qa"]["dt_min"],
            "dt_max_s": analysis["raw_qa"]["dt_max"],
            "uniform_time_grid": analysis["raw_qa"]["uniform_time_grid"],
            "probe_count": len(structure["probe_labels"]),
            "cycle_count": len(json.loads(metric_path.read_text(encoding="utf-8"))["cycles"]),
            "raw_qa_status": raw_qa_data["status"], "plot_qa_status": plot_qa["status"],
            "scientific_interpretation_performed": False,
        }
        write_json(run_dir / "analysis/mechanical_qa.json", mechanical_qa)
        provenance_qa = {
            "schema": "t1-clock-only-provenance-qa-v1",
            "status": "PASS" if sha256(run_dir / "actual_deck.cir")
            == provenance["actual_deck"]["sha256"]
            and sha256(run_dir / "source_manifest.json")
            == provenance["source_manifest"]["sha256"]
            and sha256(run_dir / "USER_CASE.snapshot.env")
            == provenance["user_case"]["sha256"]
            and sha256(run_dir / "PREFLIGHT.md") == provenance["preflight"]["sha256"]
            and sha256(METRIC_SPEC) == provenance["metric_spec"]["sha256"] else "FAIL",
            "parent_head": provenance["parent_head"],
            "t1_source_sha256": sha256(T1_SOURCE), "jjmit_sha256": sha256(JJMIT_SOURCE),
            "source_manifest_sha256": sha256(run_dir / "source_manifest.json"),
            "source_hashes_match": source_hashes.get("T1") == sha256(T1_SOURCE)
            and source_hashes.get("JJMIT_MODEL") == sha256(JJMIT_SOURCE),
            "deck_sha256": sha256(run_dir / "actual_deck.cir"),
            "parameter_manifest_sha256": sha256(run_dir / "parameter_manifest.json"),
            "topology_manifest_sha256": sha256(run_dir / "topology_manifest.json"),
            "user_case_sha256": sha256(run_dir / "USER_CASE.snapshot.env"),
            "preflight_sha256": sha256(run_dir / "PREFLIGHT.md"),
            "metric_spec_sha256": sha256(METRIC_SPEC),
            "scientific_interpretation_performed": False,
        }
        provenance_qa["status"] = "PASS" if (
            provenance["source_manifest"]["sha256"] == provenance_qa["source_manifest_sha256"]
            and provenance_qa["source_hashes_match"]
            and provenance["actual_deck"]["sha256"] == provenance_qa["deck_sha256"]
            and provenance["parameter_manifest"]["sha256"]
            == provenance_qa["parameter_manifest_sha256"]
            and provenance["topology_manifest"]["sha256"]
            == provenance_qa["topology_manifest_sha256"]
            and provenance["user_case"]["sha256"] == provenance_qa["user_case_sha256"]
            and provenance["preflight"]["sha256"] == provenance_qa["preflight_sha256"]
            and provenance["metric_spec"]["sha256"] == provenance_qa["metric_spec_sha256"]
        ) else "FAIL"
        write_json(run_dir / "analysis/provenance_qa.json", provenance_qa)
        qa_pass = (mechanical_qa["status"] == "PASS"
                   and provenance_qa["status"] == "PASS")
        write_json(run_dir / "result.json", {
            "schema": "t1-clock-only-result-v1", "run_id": RUN_ID,
            "status": ("MECHANICAL_QA_PASS_AWAITING_USER_REVIEW" if qa_pass
                       else "MECHANICAL_QA_FAIL_AWAITING_USER_REVIEW"),
            "artifact_status": "VALID", "solver_exit_code": 0,
            "physical_solve_count": 1, "raw_sha256": raw_hash,
            "sample_count": analysis["raw_qa"]["sample_count"],
            "time_range_s": [analysis["raw_qa"]["time_start"], analysis["raw_qa"]["time_end"]],
            "raw_qa_status": analysis["raw_qa"]["status"],
            "plot_qa_status": plot_qa["status"],
            "mechanical_qa_status": mechanical_qa["status"],
            "provenance_qa_status": provenance_qa["status"],
            "scientific_interpretation_performed": False,
            "automatic_follow_up": False,
        })
        metadata = json.loads((run_dir / "metadata.json").read_text(encoding="utf-8"))
        metadata.update({"solver_exit_code": 0, "artifact_status": "VALID",
                         "raw_sha256": raw_hash,
                         "sample_count": analysis["raw_qa"]["sample_count"],
                         "plot_qa_status": plot_qa["status"],
                         "mechanical_qa_status": mechanical_qa["status"],
                         "provenance_qa_status": provenance_qa["status"]})
        write_json(run_dir / "metadata.json", metadata)
        provenance["raw"]["sample_count"] = analysis["raw_qa"]["sample_count"]
        provenance["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
        provenance["mechanical_metrics"] = {
            "path": "analysis/clock_cycle_metrics.json",
            "sha256": sha256(run_dir / "analysis/clock_cycle_metrics.json"),
        }
        provenance["raw_qa"] = {"path": "analysis/raw_qa.json",
                                "sha256": sha256(run_dir / "analysis/raw_qa.json")}
        provenance["plot_qa"] = {"path": "analysis/plot_qa.json",
                                  "sha256": sha256(run_dir / "analysis/plot_qa.json")}
        provenance["mechanical_qa"] = {"path": "analysis/mechanical_qa.json",
                                       "sha256": sha256(run_dir / "analysis/mechanical_qa.json")}
        provenance["provenance_qa"] = {"path": "analysis/provenance_qa.json",
                                       "sha256": sha256(run_dir / "analysis/provenance_qa.json")}
        provenance["transformation_registry"] = {
            "path": "analysis/transformation_registry.json",
            "sha256": sha256(run_dir / "analysis/transformation_registry.json"),
        }
        provenance["mechanical_qa"] = {"path": "analysis/mechanical_qa.json",
                                       "sha256": sha256(run_dir / "analysis/mechanical_qa.json")}
        provenance["provenance_qa"] = {"path": "analysis/provenance_qa.json",
                                       "sha256": sha256(run_dir / "analysis/provenance_qa.json")}
        provenance["transformation_registry"] = {
            "path": "analysis/transformation_registry.json",
            "sha256": sha256(transformation_path),
        }
        write_json(run_dir / "provenance.json", provenance)
        metrics = json.loads((run_dir / "analysis/clock_cycle_metrics.json").read_text(encoding="utf-8"))
        brief = [
            f"# {EXPERIMENT.name} / {RUN_ID}", "",
            f"- status: `{('MECHANICAL_QA_PASS_AWAITING_USER_REVIEW' if qa_pass else 'MECHANICAL_QA_FAIL_AWAITING_USER_REVIEW')}`",
            "- physical_solve_count: `1`", "- artifact_status: `VALID`",
            f"- solver exit: `{completed.returncode}`; version `{solver['version']}`",
            f"- raw SHA-256: `{raw_hash}`; sample_count `{analysis['raw_qa']['sample_count']}`",
            f"- stored time range: `{analysis['raw_qa']['time_start']}` to `{analysis['raw_qa']['time_end']}` seconds",
            f"- raw QA: `{analysis['raw_qa']['status']}`; plot QA: `{plot_qa['status']}`",
            f"- mechanical/provenance QA: `{mechanical_qa['status']}` / `{provenance_qa['status']}`",
            f"- registered clock cycles measured: `{len(metrics['cycles'])}`",
            "- all phase/voltage metrics are raw-grid arithmetic; no SFQ event count or truth-table interpretation.",
            "- scientific interpretation: `NOT_PERFORMED`; unauthorized follow-up: `none`.", "",
        ]
        (run_dir / "RESULT_BRIEF.md").write_text("\n".join(brief), encoding="utf-8")
        _finalize_experiment_manifest(run_dir,
                                      "COMPLETE_MECHANICAL" if qa_pass else "ARTIFACT_INVALID")
        return 0 if qa_pass else 2
    except Exception as exc:
        write_json(run_dir / "result.json", {
            "schema": "t1-clock-only-result-v1", "run_id": RUN_ID,
            "status": "POSTPROCESS_FAILURE_RAW_PRESERVED", "artifact_status": "INVALID",
            "solver_exit_code": 0, "physical_solve_count": 1,
            "raw_sha256": raw_hash,
            "error": f"{type(exc).__name__}: {exc}",
            "scientific_interpretation_performed": False,
        })
        _finalize_experiment_manifest(run_dir, "POSTPROCESS_FAILURE")
        print(f"POSTPROCESS_FAILURE: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run exactly one standalone T1 CLK-only case")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write-preflight", action="store_true")
    group.add_argument("--dry-run", action="store_true")
    group.add_argument("--run", action="store_true")
    group.add_argument("--repair", metavar="RUN_DIR")
    args = parser.parse_args(argv)
    try:
        values, structure, _ = load_config()
        solver = solver_identity()
        if args.write_preflight:
            preflight = write_preflight(values, structure, solver)
            print(json.dumps({"status": "PREFLIGHT_WRITTEN", "path": str(preflight),
                              "parent_head": git_head(), "physical_solve_count": 0}, indent=2))
            return 0
        if args.dry_run:
            with tempfile.TemporaryDirectory(prefix="t1-clock-only-dry-run-") as temp:
                deck = render_deck(values, structure, Path(temp))
            required_lines = (
                "V_TRIG_CLK CLK_RAW 0 PULSE(0 1.2m 170p 1p 1p 2p 50p)",
                "R_TRIG_CLK CLK_RAW CLK 5",
                "V_BIAS1 N_BIAS1 0 DC 1.8m",
                "V_BIAS2 N_BIAS2 0 DC 1.8m",
                "V_BIAS3 N_BIAS3 0 DC 1.8m",
                "XT1 0 CLK S C N_BIAS1 N_BIAS2 N_BIAS3 T1",
                ".tran 0.01p 370p",
            )
            for line in required_lines:
                if line not in deck:
                    raise ConfigError(f"dry-run rendered deck is missing registered line: {line}")
            if "R_CLK_QUIET" in deck or "XBVM" in deck:
                raise ConfigError("dry-run deck contains a quiet shunt or integrated BVM topology")
            print(json.dumps({
                "status": "DRY_RUN_PASS", "experiment_id": EXPERIMENT.name,
                "run_id": RUN_ID, "probe_profile": "debug",
                "probe_count": len(structure["probe_labels"]),
                "t1_source_sha256": sha256(T1_SOURCE), "jjmit_sha256": sha256(JJMIT_SOURCE),
                "masks": [], "physical_solve_count": 0, "solver_invoked": False,
                "rendered_pulse_lines": [line for line in deck.splitlines()
                                          if line.startswith(("V_TRIG_CLK ", "R_TRIG_CLK "))],
            }, ensure_ascii=False, indent=2))
            return 0
        if args.repair:
            run_dir = (EXPERIMENT / args.repair).resolve()
            if not run_dir.is_dir() or run_dir.parent.resolve() != RUNS.resolve():
                raise ConfigError("repair target must be this experiment's existing runs/<run-id>")
            before = sha256(run_dir / "raw.csv")
            from clock_metrics import write_analysis
            analysis = write_analysis(run_dir)
            plotted = subprocess.run([sys.executable, str(EXPERIMENT / "scripts/plot_clock_only.py"),
                                      str(run_dir)], cwd=REPO, capture_output=True, text=True,
                                     check=False)
            (run_dir / "plot_stdout.txt").write_text(plotted.stdout, encoding="utf-8")
            (run_dir / "plot_stderr.txt").write_text(plotted.stderr, encoding="utf-8")
            after = sha256(run_dir / "raw.csv")
            if plotted.returncode != 0 or before != after:
                raise ConfigError("same-raw repair failed; original raw was preserved")
            qa_pass = _refresh_same_raw_qa(run_dir, before, analysis)
            print(json.dumps({"status": "SAME_RAW_REPAIR_PASS" if qa_pass
                              else "SAME_RAW_REPAIR_QA_FAIL", "raw_sha256": after,
                              "physical_solve_count": 0, "solver_invoked": False}, indent=2))
            return 0 if qa_pass else 2
        return run_once(values, structure, solver)
    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
