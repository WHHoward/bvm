#!/usr/bin/env python3
"""Config-driven JoSIM Quick workflow with legacy and Compact V2 entrypoints.

The legacy command remains available for existing V1 fixtures:

    python3 scripts/bvm-exp.py quick path/to/experiment.yaml

New experiments use ``run``, ``analyze``, ``plot``, ``package`` and ``inspect``
with immutable Axxx attempts.  The default run is evidence-first: it executes
only its registered deck, performs mechanical QA, creates the registered
visualization and evidence package, commits that package when the experiment
is inside this repository, and stops at ``AWAITING_SCIENTIFIC_REVIEW``.
Scientific analysis is a separate, explicit ``SCIENTIFIC_REVIEW_AUTHORIZED``
path.  Analyze/plot/package never create new physics data.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import math
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:  # pragma: no cover - environment failure
    raise SystemExit("bvm-exp.py requires PyYAML (python3-yaml)") from exc

from bvmtools.compare import compare_series
from bvmtools.provenance import (
    file_snapshot,
    git_snapshot,
    sha256_file,
    snapshot_inputs,
    solver_provenance,
)
from bvmtools.phase import continuous_unwrap, window_indices
from bvmtools.raw import DuplicateColumnError, RawTraceError, read_csv
from bvmtools.sfq import StrictLocalEventSpec, strict_event_summary
from bvmtools.waveform import waveform_metrics
from build_experiment_package import CONTRACT_SENTENCE
from build_experiment_package import build_package


REPO = Path(__file__).resolve().parents[1]
SCRIPT = Path(__file__).resolve()
PRESETS_PATH = SCRIPT.parent / "bvmtools" / "presets.yaml"
ALLOWED_MODES = {"QUICK"}
ALLOWED_VISUAL_MODES = {"none", "compact", "full"}
ALLOWED_METRICS = {"raw_qa", "waveform", "strict_event", "compare"}
QUICK_OUTCOMES = {
    "QUICK_PROMISING",
    "QUICK_NO_EFFECT",
    "QUICK_OPPOSITE",
    "QUICK_AMBIGUOUS",
    "QUICK_INVALID",
}
SCIENTIFIC_REVIEW_AUTHORIZATION = "SCIENTIFIC_REVIEW_AUTHORIZED"
EVIDENCE_FIRST_POLICY = "EVIDENCE_FIRST_V1"


class ConfigError(ValueError):
    """The minimal experiment config is incomplete or unsafe to run."""


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ConfigError(f"cannot read YAML config {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ConfigError("experiment.yaml must contain a mapping")
    return value


def _load_presets() -> dict[str, Any]:
    value = yaml.safe_load(PRESETS_PATH.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or not isinstance(value.get("presets"), dict):
        raise ConfigError(f"invalid preset registry: {PRESETS_PATH}")
    return value["presets"]


def _positive_number(value: Any, name: str) -> float:
    if isinstance(value, bool):
        raise ConfigError(f"{name} must be a positive number")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"{name} must be a positive number") from exc
    if not number > 0.0:
        raise ConfigError(f"{name} must be a positive number")
    return number


def _resolve_existing(value: str | Path, *, config_dir: Path) -> Path:
    candidate = Path(value)
    choices = [candidate] if candidate.is_absolute() else [config_dir / candidate, REPO / candidate]
    for path in choices:
        if path.is_file():
            return path.resolve()
    raise ConfigError(f"input file does not exist: {value}")


def _resolve_output_dir(value: str | Path, *, config_dir: Path) -> Path:
    candidate = Path(value)
    return candidate.resolve() if candidate.is_absolute() else (config_dir / candidate).resolve()


_SPICE_TIME_UNITS = {
    "": 1.0,
    "s": 1.0,
    "ms": 1.0e-3,
    "us": 1.0e-6,
    "ns": 1.0e-9,
    "ps": 1.0e-12,
    "fs": 1.0e-15,
    "m": 1.0e-3,
    "u": 1.0e-6,
    "n": 1.0e-9,
    "p": 1.0e-12,
    "f": 1.0e-15,
}


def _parse_spice_time(token: str) -> float:
    match = re.fullmatch(r"([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)([A-Za-z]*)", token.strip())
    if match is None or match.group(2).casefold() not in _SPICE_TIME_UNITS:
        raise ConfigError(f"unsupported SPICE time token in .tran: {token!r}")
    return float(match.group(1)) * _SPICE_TIME_UNITS[match.group(2).casefold()]


def _check_deck_run(deck: Path, *, timestep_ps: float, stop_ps: float) -> dict[str, float]:
    """Require the main deck's .tran to match the declared Quick run."""

    lines = deck.read_text(encoding="utf-8").splitlines()
    tran_tokens: list[list[str]] = []
    for line in lines:
        content = line.split(";", 1)[0].strip()
        if not content or content.startswith("*"):
            continue
        fields = content.split()
        if fields and fields[0].casefold() == ".tran":
            tran_tokens.append(fields)
    if len(tran_tokens) != 1 or len(tran_tokens[0]) < 3:
        raise ConfigError(f"{deck} must contain exactly one main-deck .tran timestep/stop pair")
    actual_timestep_ps = _parse_spice_time(tran_tokens[0][1]) * 1.0e12
    actual_stop_ps = _parse_spice_time(tran_tokens[0][2]) * 1.0e12
    if not math.isclose(actual_timestep_ps, timestep_ps, rel_tol=1.0e-9, abs_tol=1.0e-12):
        raise ConfigError(
            f"{deck} .tran timestep is {actual_timestep_ps:g} ps, "
            f"but config declares {timestep_ps:g} ps"
        )
    if not math.isclose(actual_stop_ps, stop_ps, rel_tol=1.0e-9, abs_tol=1.0e-9):
        raise ConfigError(
            f"{deck} .tran stop is {actual_stop_ps:g} ps, "
            f"but config declares {stop_ps:g} ps"
        )
    return {"timestep_ps": actual_timestep_ps, "stop_ps": actual_stop_ps}


def _case_signals(case: dict[str, Any], preset: dict[str, Any]) -> list[dict[str, Any]]:
    raw_signals = case.get("signals", preset.get("signals"))
    if not isinstance(raw_signals, list) or not raw_signals:
        raise ConfigError(f"case {case.get('id', '<unknown>')} must declare signals or use a preset")
    signals: list[dict[str, Any]] = []
    for item in raw_signals:
        if isinstance(item, str):
            signals.append({"name": item, "occurrence": None})
        elif isinstance(item, dict) and isinstance(item.get("name"), str):
            occurrence = item.get("occurrence")
            if occurrence is not None and (isinstance(occurrence, bool) or not isinstance(occurrence, int) or occurrence < 0):
                raise ConfigError("signal occurrence must be a nonnegative integer")
            signals.append({"name": item["name"], "occurrence": occurrence})
        else:
            raise ConfigError("each signal must be an exact label or {name, occurrence}")
    return signals


def validate_config(config: dict[str, Any], config_path: str | Path) -> dict[str, Any]:
    """Validate and normalize the deliberately small future-experiment schema."""

    path = Path(config_path).resolve()
    config_dir = path.parent
    required = ("id", "family", "mode", "question", "hypothesis", "baseline", "candidate", "run", "probe_preset", "metrics", "visualization", "promotion_rule", "stop_rule", "cases")
    missing = [key for key in required if key not in config]
    if missing:
        raise ConfigError(f"missing required config keys: {', '.join(missing)}")
    if not isinstance(config["id"], str) or not config["id"].strip():
        raise ConfigError("id must be a non-empty string")
    mode = str(config["mode"]).upper()
    if mode not in ALLOWED_MODES:
        raise ConfigError(f"mode must be one of {sorted(ALLOWED_MODES)}")
    if not isinstance(config["baseline"], dict) or not isinstance(config["candidate"], dict):
        raise ConfigError("baseline and candidate must be mappings with explicit deck values")
    for label in ("baseline", "candidate"):
        deck = config[label].get("deck")
        if not isinstance(deck, str):
            raise ConfigError(f"{label}.deck must be an explicit path")
        _resolve_existing(deck, config_dir=config_dir)
    if not isinstance(config["run"], dict):
        raise ConfigError("run must be a mapping")
    timestep_ps = _positive_number(config["run"].get("timestep_ps"), "run.timestep_ps")
    stop_ps = _positive_number(config["run"].get("stop_ps"), "run.stop_ps")
    if stop_ps <= timestep_ps:
        raise ConfigError("run.stop_ps must be greater than run.timestep_ps")

    presets = _load_presets()
    preset_names = config["probe_preset"] if isinstance(config["probe_preset"], list) else [config["probe_preset"]]
    if not preset_names or any(name not in presets for name in preset_names):
        raise ConfigError(f"unknown probe_preset; registered values are {sorted(presets)}")
    preset = presets[preset_names[0]]
    metrics = config["metrics"]
    if not isinstance(metrics, list) or any(metric not in ALLOWED_METRICS for metric in metrics):
        raise ConfigError(f"metrics must be a list drawn from {sorted(ALLOWED_METRICS)}")
    visual = config["visualization"]
    if not isinstance(visual, dict):
        raise ConfigError("visualization must be a mapping")
    visual_mode = str(visual.get("mode", "compact")).lower()
    if visual_mode not in ALLOWED_VISUAL_MODES:
        raise ConfigError(f"visualization.mode must be one of {sorted(ALLOWED_VISUAL_MODES)}")
    visual_style = str(visual.get("style", "CLASSIC_LOCKED"))
    if visual_style != "CLASSIC_LOCKED":
        if not bool(config.get("alternative_style_authorized", False)):
            raise ConfigError("alternative visual style requires explicit alternative_style_authorized: true")
        raise ConfigError("V1 has no alternative backend; use CLASSIC_LOCKED or authorize a separate design task")

    cases = config["cases"]
    if not isinstance(cases, list) or not cases:
        raise ConfigError("cases must be a non-empty explicit list")
    if len(cases) > 4:
        raise ConfigError("Quick supports at most four explicit cases")
    case_ids: set[str] = set()
    normalized_cases: list[dict[str, Any]] = []
    for raw_case in cases:
        if not isinstance(raw_case, dict) or not isinstance(raw_case.get("id"), str):
            raise ConfigError("each case must have a string id")
        case_id = raw_case["id"]
        if case_id in case_ids:
            raise ConfigError(f"duplicate case id: {case_id}")
        case_ids.add(case_id)
        normalized_case = dict(raw_case)
        normalized_case["signals"] = _case_signals(raw_case, preset)
        if visual_mode == "compact" and not 2 <= len(normalized_case["signals"]) <= 5:
            raise ConfigError(f"compact case {case_id} must select 2-5 signals")
        strict = raw_case.get("strict_event")
        if strict is not None:
            if not isinstance(strict, dict):
                raise ConfigError(f"case {case_id}.strict_event must be a mapping")
            for key in ("phase", "voltage", "activity_window_ps", "post_window_ps", "post_tail_window_ps"):
                if key not in strict:
                    raise ConfigError(f"case {case_id}.strict_event missing {key}")
            for key in ("activity_window_ps", "post_window_ps", "post_tail_window_ps"):
                bounds = strict[key]
                if not isinstance(bounds, list) or len(bounds) != 2 or float(bounds[0]) >= float(bounds[1]):
                    raise ConfigError(f"case {case_id}.strict_event.{key} must be [start_ps, end_ps]")
        if bool(config.get("tooling_smoke_test_only", False)):
            raw_path = raw_case.get("raw")
            if not isinstance(raw_path, str):
                raise ConfigError(f"smoke case {case_id} must point to an existing raw CSV")
            normalized_case["raw_path"] = _resolve_existing(raw_path, config_dir=config_dir)
        elif "raw" in raw_case:
            raise ConfigError("normal Quick runs generate raw outputs; raw references are smoke-test-only")
        normalized_cases.append(normalized_case)

    output_dir = _resolve_output_dir(config.get("output_dir", f"quick/{config['id']}"), config_dir=config_dir)
    solver_value = config["run"].get("solver", "build/josim-cli")
    solver = _resolve_existing(solver_value, config_dir=config_dir)
    return {
        "config": config,
        "config_path": path,
        "config_dir": config_dir,
        "mode": mode,
        "timestep_ps": timestep_ps,
        "stop_ps": stop_ps,
        "preset_names": preset_names,
        "preset": preset,
        "metrics": metrics,
        "visual_mode": visual_mode,
        "output_dir": output_dir,
        "solver": solver,
        "cases": normalized_cases,
        "smoke": bool(config.get("tooling_smoke_test_only", False)),
    }


def _copy_exact(source: Path, target: Path) -> None:
    data = source.read_bytes()
    if target.exists():
        if target.read_bytes() != data:
            raise RuntimeError(f"refusing to overwrite non-identical file: {target}")
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)


def _select_column(trace: Any, spec: dict[str, Any]) -> tuple[float, ...]:
    try:
        return trace.column(spec["name"], occurrence=spec.get("occurrence"))
    except DuplicateColumnError as exc:
        raise RawTraceError(
            f"selected signal {spec['name']!r} is duplicated; add an explicit occurrence for plots/metrics"
        ) from exc


def _window_seconds(strict: dict[str, Any], key: str) -> tuple[float, float]:
    bounds = strict[key]
    return float(bounds[0]) * 1.0e-12, float(bounds[1]) * 1.0e-12


def _analyze_raw(case: dict[str, Any], raw_path: Path, metrics: list[str]) -> dict[str, Any]:
    trace = read_csv(raw_path)
    result: dict[str, Any] = {
        "raw": str(raw_path),
        "raw_sha256": sha256_file(raw_path),
        "qa": trace.qa(),
        "signals": {},
    }
    selected = []
    for spec in case["signals"]:
        values = _select_column(trace, spec)
        selected.append((spec, values))
        if "waveform" in metrics:
            signal_key = spec["name"] if spec.get("occurrence") is None else f"{spec['name']} [occurrence={spec['occurrence']}]"
            result["signals"][signal_key] = {
                "occurrence": spec.get("occurrence"),
                "waveform": waveform_metrics(trace.time, values),
            }
    strict = case.get("strict_event")
    if strict is not None and "strict_event" in metrics:
        phase_spec = {"name": strict["phase"], "occurrence": strict.get("phase_occurrence")}
        voltage_spec = {"name": strict["voltage"], "occurrence": strict.get("voltage_occurrence")}
        local_spec = StrictLocalEventSpec.from_mapping(strict.get("spec"))
        metric_spec_path_value = local_spec.metric_spec.get("path")
        metric_spec_path = (
            Path(metric_spec_path_value)
            if isinstance(metric_spec_path_value, str) and Path(metric_spec_path_value).is_absolute()
            else REPO / str(metric_spec_path_value)
        )
        actual_metric_spec_sha256 = (
            sha256_file(metric_spec_path) if metric_spec_path.is_file() else None
        )
        result["strict_event"] = strict_event_summary(
            trace.time,
            _select_column(trace, phase_spec),
            _select_column(trace, voltage_spec),
            activity_window_s=_window_seconds(strict, "activity_window_ps"),
            post_window_s=_window_seconds(strict, "post_window_ps"),
            post_tail_window_s=_window_seconds(strict, "post_tail_window_ps"),
            spec=local_spec,
            actual_raw_sha256=result["raw_sha256"],
            actual_metric_spec_sha256=actual_metric_spec_sha256,
        )
    compare_path_value = case.get("compare_with")
    if compare_path_value is not None and "compare" in metrics:
        compare_path = Path(compare_path_value)
        if not compare_path.is_absolute():
            compare_path = (Path(case.get("compare_base", ".")) / compare_path).resolve()
        other = read_csv(compare_path)
        if not selected:
            raise ConfigError(f"case {case['id']} has no signals for comparison")
        spec, values = selected[0]
        result["compare"] = compare_series(
            trace.time,
            values,
            other.time,
            other.column(spec["name"], occurrence=spec.get("occurrence")),
            interpolation=case.get("interpolation"),
            include_correlation=bool(case.get("include_correlation", False)),
            include_scalar_fit=bool(case.get("include_scalar_fit", False)),
        )
    return result


def _run_case(
    normalized: dict[str, Any],
    case: dict[str, Any],
    output_dir: Path,
) -> dict[str, Any]:
    case_id = case["id"]
    case_dir = output_dir / "cases" / case_id
    raw_path = case_dir / "raw" / "run-01.csv"
    stdout_path = case_dir / "logs" / "stdout.txt"
    stderr_path = case_dir / "logs" / "stderr.txt"
    for path in (case_dir, raw_path, stdout_path, stderr_path):
        if path.exists():
            raise RuntimeError(f"refusing to overwrite existing Quick artifact: {path}")
    deck_value = case.get("deck", "candidate")
    if deck_value == "candidate":
        deck = _resolve_existing(normalized["config"]["candidate"]["deck"], config_dir=normalized["config_dir"])
    elif deck_value == "baseline":
        deck = _resolve_existing(normalized["config"]["baseline"]["deck"], config_dir=normalized["config_dir"])
    elif isinstance(deck_value, str):
        deck = _resolve_existing(deck_value, config_dir=normalized["config_dir"])
    else:
        raise ConfigError(f"case {case_id}.deck must be candidate, baseline, or an explicit path")
    declared_run = _check_deck_run(
        deck,
        timestep_ps=normalized["timestep_ps"],
        stop_ps=normalized["stop_ps"],
    )
    snapshot_path = output_dir / "inputs" / f"{case_id}.cir"
    _copy_exact(deck, snapshot_path)
    deck_before = file_snapshot(deck, relative_to=REPO)
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    stdout_path.parent.mkdir(parents=True, exist_ok=True)
    command = [str(normalized["solver"]), "-a", "1", "-o", str(raw_path), str(deck)]
    started = _now()
    completed = subprocess.run(command, cwd=REPO, capture_output=True, text=True, check=False)
    stdout_path.write_text(completed.stdout, encoding="utf-8")
    stderr_path.write_text(completed.stderr, encoding="utf-8")
    deck_after = file_snapshot(deck, relative_to=REPO)
    record: dict[str, Any] = {
        "id": case_id,
        "deck": str(deck),
        "snapshot": str(snapshot_path),
        "raw": str(raw_path),
        "command": command,
        "started_at": started,
        "finished_at": _now(),
        "returncode": completed.returncode,
        "stdout": str(stdout_path),
        "stderr": str(stderr_path),
        "declared_run": declared_run,
        "deck_before": deck_before,
        "deck_after": deck_after,
    }
    if deck_before["sha256"] != deck_after["sha256"]:
        record["analysis"] = {
            "status": "INVALID",
            "reason": "source deck changed while the case was running",
        }
    elif completed.returncode != 0:
        record["analysis"] = {
            "status": "INVALID",
            "reason": f"solver returned non-zero exit status {completed.returncode}",
            "raw_present": raw_path.is_file(),
        }
    elif raw_path.is_file():
        record["analysis"] = _analyze_raw(case, raw_path, normalized["metrics"])
    else:
        record["analysis"] = {"status": "INVALID", "reason": "solver did not create raw CSV"}
    return record


def _consume_smoke_case(
    normalized: dict[str, Any], case: dict[str, Any]
) -> dict[str, Any]:
    raw_path = case["raw_path"]
    return {
        "id": case["id"],
        "raw": str(raw_path),
        "raw_sha256": sha256_file(raw_path),
        "command": [],
        "execution": "TOOLING_SMOKE_TEST_ONLY",
        "analysis": _analyze_raw(case, raw_path, normalized["metrics"]),
    }


def _classic_command(
    raw_path: Path,
    output_path: Path,
    signals: list[dict[str, Any]],
    title: str,
) -> list[str]:
    return [
        sys.executable,
        str(SCRIPT.parent / "josim-plot2.py"),
        str(raw_path),
        "-s",
        *[item["name"] for item in signals],
        "-t",
        "sep_comb",
        "-c",
        "dark",
        "-j",
        "2pi",
        "-x",
        str(output_path),
        "-w",
        title,
    ]


def _render_classic(
    normalized: dict[str, Any], results: list[dict[str, Any]], output_dir: Path
) -> dict[str, Any]:
    if normalized["visual_mode"] == "none":
        return {"status": "NOT_REQUESTED", "style": "CLASSIC_LOCKED"}
    plot_dir = output_dir / "plots"
    plot_dir.mkdir(parents=True, exist_ok=True)
    rendered: list[dict[str, Any]] = []
    requested_primary = normalized["config"].get("visualization", {}).get("primary_case")
    case_ids = [case["id"] for case in normalized["cases"]]
    primary_case = requested_primary if requested_primary in case_ids else case_ids[0]
    for record, case in zip(results, normalized["cases"]):
        analysis = record.get("analysis", {})
        raw_value = record.get("raw")
        if not raw_value or not Path(raw_value).is_file():
            return {"status": "INVALID", "reason": f"raw file missing for case {case['id']}"}
        if not isinstance(analysis, dict) or analysis.get("qa", {}).get("status") != "VALID":
            return {"status": "INVALID", "reason": f"raw QA failed for case {case['id']}"}
        trace = read_csv(Path(raw_value))
        duplicated_selected = sorted(
            {
                item["name"]
                for item in case["signals"]
                if item["name"] in trace.duplicate_columns
            }
        )
        if duplicated_selected:
            return {
                "status": "INVALID",
                "reason": (
                    "classic josim-plot2 cannot select duplicate exact labels safely: "
                    + ", ".join(duplicated_selected)
                ),
            }
        output = plot_dir / (
            "RESULT_OVERVIEW.html" if case["id"] == primary_case else f"{case['id']}.html"
        )
        command = _classic_command(
            Path(raw_value),
            output,
            case["signals"],
            f"{normalized['config']['id']} — {case['id']}",
        )
        completed = subprocess.run(command, cwd=REPO, capture_output=True, text=True, check=False)
        rendered.append({
            "case": case["id"],
            "path": str(output),
            "command": command,
            "returncode": completed.returncode,
            "stderr": completed.stderr,
            "signals": [item["name"] for item in case["signals"]],
        })
        if completed.returncode != 0 or not output.is_file() or output.stat().st_size == 0:
            return {"status": "INVALID", "rendered": rendered, "reason": f"classic plot failed for {case['id']}"}
    overview = plot_dir / "RESULT_OVERVIEW.html"
    if not rendered or not overview.is_file():
        return {"status": "INVALID", "reason": "no plot was rendered"}
    return {
        "status": "PASS",
        "style": "CLASSIC_LOCKED",
        "mode": normalized["visual_mode"],
        "backend": "scripts/josim-plot2.py",
        "profile": {"layout": "sep_comb", "color": "dark", "phase": "rad/(2*pi) turns"},
        "overview": str(overview),
        "rendered": rendered,
    }


def _strict_observations(results: list[dict[str, Any]]) -> list[str]:
    observations: list[str] = []
    for record in results:
        strict = record.get("analysis", {}).get("strict_event")
        if not isinstance(strict, dict):
            continue
        largest = strict.get("largest_monotonic_segment") or {}
        turns = largest.get("phase_reported_turns")
        area = largest.get("area_turns")
        if turns is None:
            observations.append(f"{record['id']}：没有非零 monotonic segment（strict-event local diagnostic）。")
        else:
            observations.append(
                f"{record['id']}：最大同段相位 {float(turns):.12f} turn，"
                f"同段电压面积 {float(area):.12f} Φ0，"
                f"兼容性分类 `{strict.get('compatibility_classification')}`。"
            )
    return observations


def _derive_outcome(
    normalized: dict[str, Any],
    results: list[dict[str, Any]],
    visualization: dict[str, Any],
    smoke: bool,
) -> str:
    if smoke:
        return "TOOLING_SMOKE_TEST_ONLY"
    if visualization.get("status") != "PASS" and visualization.get("status") != "NOT_REQUESTED":
        return "QUICK_INVALID"
    outcome_rule = normalized["config"].get("outcome_rule")
    if not isinstance(outcome_rule, dict) or outcome_rule.get("enabled") is not True:
        return "QUICK_AMBIGUOUS"
    classifications = [
        record.get("analysis", {}).get("strict_event", {}).get("compatibility_classification")
        for record in results
        if isinstance(record.get("analysis", {}).get("strict_event"), dict)
    ]
    if any(record.get("analysis", {}).get("qa", {}).get("status") != "VALID" for record in results):
        return "QUICK_INVALID"
    if not classifications:
        return "QUICK_AMBIGUOUS"
    if any(value == "CLEAN_ONE_SFQ_CANDIDATE" for value in classifications):
        return "QUICK_PROMISING"
    if all(value in {"NO_NONZERO_MONOTONIC_SEGMENT", "SUBTHRESHOLD"} for value in classifications):
        return "QUICK_NO_EFFECT"
    if any(value in {"OVERDRIVEN_ONE_PLUS_RESIDUAL", "MULTIPLE_COMPLETE_SEGMENTS"} for value in classifications):
        return "QUICK_OPPOSITE"
    return "QUICK_AMBIGUOUS"


def _write_brief(
    normalized: dict[str, Any],
    results: list[dict[str, Any]],
    visualization: dict[str, Any],
    outcome: str,
    output_dir: Path,
) -> None:
    config = normalized["config"]
    baseline = config["baseline"]
    candidate = config["candidate"]
    changed = config.get("changed_variables", ["candidate deck / explicitly registered case input"])
    fixed = config.get("held_fixed", [
        f"solver timestep = {normalized['timestep_ps']} ps",
        f"solver stop = {normalized['stop_ps']} ps",
        f"probe preset = {', '.join(normalized['preset_names'])}",
        "case list, signal labels, windows and metric semantics",
    ])
    observations = _strict_observations(results)
    if not observations:
        observations = [
            f"{len(results)} 个显式 case 已完成 raw QA；每个 case 的样本数、时间范围和 hash 见 `manifest.json`。",
        ]
    observations = observations[:6]
    if outcome == "TOOLING_SMOKE_TEST_ONLY":
        changed_section = [
            "Tooling action performed in this smoke:",
            "- no circuit change",
            "- no parameter change",
            "- no JoSIM rerun",
            "- only reprocessed existing historical raw through the new shared tooling path",
            "",
            "Historical scientific comparison represented by those reused raw files:",
            "- READ width: 9 ps → 13 ps",
            "- all other registered scientific conditions remain existing historical fixture conditions",
        ]
        meaning = "共享 raw reader、strict-event 实现、结果摘要和经典 compact 后端已用既有 raw 做工具链重放；这些输出不产生新的 physics conclusion。"
        not_prove = [
            "不证明任何新的电路行为、SFQ delivery、下游接收或 system Gate。",
            "不替代历史 raw、既有报告或 METRIC_SPEC_V2 的科学权威边界。",
            "未运行 JoSIM，也未改变历史输入或 raw。",
        ]
    else:
        changed_section = [
            f"- Baseline: `{baseline['deck']}`",
            f"- Candidate: `{candidate['deck']}`",
            f"- Changed variables: {', '.join(str(item) for item in changed)}",
        ]
        meaning = "这是 QUICK 层的有界方向性观察，只用于筛选假说；它不是 formal evidence 或物理 Gate。"
        not_prove = [
            "不证明完整物理机制、鲁棒裕度、下游接收或 system Gate。",
            "不把 local phase/area candidate 自动升级为成功 SFQ。",
            "不能替代 Promotion 计划、匹配控制、收敛和必要的独立复核。",
        ]
    next_options = config.get("possible_next_options", [
        "用户先复核本摘要和 compact classic waveform。",
        "若理解结果，可明确授权关闭该问题或继续一个最小 Quick。",
        "若结果值得依赖，可明确授权生成 Promotion plan；工具不会自动执行。",
    ])[:3]
    lines = [
        "# Result",
        "",
        "## 1. What we changed",
        "",
        *changed_section,
        "",
        "## 2. What was held fixed",
        "",
        *[f"- {item}" for item in fixed],
        "",
        "## 3. Why we tested it",
        "",
        str(config["hypothesis"]),
        "",
        "## 4. What happened",
        "",
        *[f"- {item}" for item in observations],
        "",
        "## 5. What it means",
        "",
        meaning,
        "",
        "## 6. What it does NOT prove",
        "",
        *[f"- {item}" for item in not_prove],
        "",
        "## 7. Current status",
        "",
        f"`{outcome}`",
        "`AWAITING_USER_REVIEW`",
        "",
        "## 8. Possible next options",
        "",
        *[f"- {item}" for item in next_options],
        "",
        "## Result artifacts",
        "",
        f"- Classic overview: `{visualization.get('overview', 'not generated')}`",
        "- Detailed machine-readable metrics: `analysis.json`",
        "- Human gate: `human-gate.yaml`",
    ]
    (output_dir / "RESULT_BRIEF.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_quick(config_path: str | Path) -> int:
    # Frozen compatibility path for already-created V1 fixtures.  The
    # evidence-first defaults below intentionally do not rewrite its historical
    # analysis or AWAITING_USER_REVIEW artifacts.
    normalized = validate_config(_load_yaml(Path(config_path).resolve()), config_path)
    if normalized["mode"] != "QUICK":
        raise ConfigError("the V1 CLI implements only mode: QUICK; Promotion/Formal remain explicit planning paths")
    output_dir = normalized["output_dir"]
    if output_dir.exists():
        raise RuntimeError(f"refusing to reuse existing run path: {output_dir}")
    repository_before_run = git_snapshot(REPO)
    solver_before_run = solver_provenance(normalized["solver"], cwd=REPO)
    output_dir.mkdir(parents=True, exist_ok=False)
    config_file = normalized["config_path"]
    _copy_exact(config_file, output_dir / "experiment.yaml")
    results: list[dict[str, Any]] = []
    if normalized["smoke"]:
        results = [_consume_smoke_case(normalized, case) for case in normalized["cases"]]
    else:
        results = [_run_case(normalized, case, output_dir) for case in normalized["cases"]]
    visualization = _render_classic(normalized, results, output_dir)
    outcome = _derive_outcome(normalized, results, visualization, normalized["smoke"])
    analysis_payload = {
        "schema_version": 1,
        "experiment_id": normalized["config"]["id"],
        "mode": normalized["mode"],
        "tooling_smoke_test_only": normalized["smoke"],
        "outcome": outcome,
        "cases": results,
        "visualization": visualization,
    }
    _write_json(output_dir / "analysis.json", analysis_payload)
    solver_after_run = solver_provenance(normalized["solver"], cwd=REPO)
    _write_json(output_dir / "provenance.json", {
        "recorded_at": _now(),
        "repository_before_run": repository_before_run,
        "solver_before_run": solver_before_run,
        "solver_after_run": solver_after_run,
        "solver": solver_after_run,
        "config": file_snapshot(config_file, relative_to=REPO),
        "inputs": snapshot_inputs(
            [
                _resolve_existing(normalized["config"]["baseline"]["deck"], config_dir=normalized["config_dir"]),
                _resolve_existing(normalized["config"]["candidate"]["deck"], config_dir=normalized["config_dir"]),
            ],
            relative_to=REPO,
        ),
    })
    gate = {
        "schema_version": 1,
        "state": "AWAITING_USER_REVIEW",
        "user_reviewed": False,
        "next_step_authorized": False,
        "transitions": [],
        "outcome": outcome,
        "updated_at": _now(),
        "updated_by": "scripts/bvm-exp.py",
        "note": "Initial gate record; transitions are append-only and only explicit user authorization may advance the workflow.",
    }
    (output_dir / "human-gate.yaml").write_text(yaml.safe_dump(gate, sort_keys=False, allow_unicode=True), encoding="utf-8")
    _write_brief(normalized, results, visualization, outcome, output_dir)
    manifest = {
        "schema_version": 1,
        "experiment_id": normalized["config"]["id"],
        "family": normalized["config"]["family"],
        "mode": normalized["mode"],
        "output_dir": str(output_dir),
        "raw_execution": "NOT_RUN_EXISTING_RAW_ONLY" if normalized["smoke"] else "EXPLICIT_CASES_ONLY",
        "result_brief": str(output_dir / "RESULT_BRIEF.md"),
        "human_gate": str(output_dir / "human-gate.yaml"),
        "outcome": outcome,
        "awaiting_user_review": True,
        "stop_after_result": True,
    }
    _write_json(output_dir / "manifest.json", manifest)
    print(json.dumps({
        "experiment": normalized["config"]["id"],
        "output_dir": str(output_dir),
        "outcome": outcome,
        "status": "AWAITING_USER_REVIEW",
        "joSIM_run": not normalized["smoke"],
    }, ensure_ascii=False, indent=2))
    return 0


# ---------------------------------------------------------------------------
# Compact Quick V2
# ---------------------------------------------------------------------------
# The legacy ``quick`` command above remains available for already-created V1
# fixtures.  New experiments use the smaller directory/attempt contract below
# and never share output paths with the legacy command.

COMPACT_SCHEMA = "compact-quick-v2"
COMPACT_RESULT_SCHEMA = "compact-quick-v2-result"
COMPACT_STATES = {
    "READY",
    "RUNNING",
    "AWAITING_SCIENTIFIC_REVIEW",
    # Kept as an input compatibility value for already-created V1 fixtures;
    # newly completed Compact attempts use AWAITING_SCIENTIFIC_REVIEW.
    "AWAITING_USER_REVIEW",
    "EXPERIMENT_COMPLETE",
    "REVIEWED",
    "ARCHIVED",
}


def _compact_root(value: str | Path) -> tuple[Path, Path]:
    supplied = Path(value).resolve()
    if supplied.is_file():
        root = supplied.parent
        config_path = supplied
    else:
        root = supplied
        config_path = root / "experiment.yaml"
    if not config_path.is_file():
        raise ConfigError(f"compact experiment.yaml does not exist: {config_path}")
    return root, config_path


def _compact_nonempty_text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"{name} must be a non-empty string")
    return value.strip()


def _compact_signal_specs(value: Any, name: str) -> list[dict[str, Any]]:
    try:
        return _case_signals({"id": name, "signals": value}, {})
    except ConfigError as exc:
        raise ConfigError(f"{name}: {exc}") from exc


def validate_compact_config(config: dict[str, Any], config_path: str | Path) -> dict[str, Any]:
    """Validate the small, single-attempt-at-a-time Quick V2 schema."""

    root, path = _compact_root(config_path)
    if config.get("schema_version") != COMPACT_SCHEMA:
        raise ConfigError(f"compact config must declare schema_version: {COMPACT_SCHEMA}")
    experiment_id = _compact_nonempty_text(config.get("id"), "id")
    mode = str(config.get("mode", "QUICK")).upper()
    if mode != "QUICK":
        raise ConfigError("compact runner supports only mode: QUICK; Formal is an explicit separate workflow")
    question = _compact_nonempty_text(config.get("question"), "question")
    hypothesis = _compact_nonempty_text(config.get("hypothesis"), "hypothesis")
    if not config.get("changed"):
        raise ConfigError("changed must name the one central variable or change")
    frozen = config.get("frozen")
    if not isinstance(frozen, (list, dict)) or not frozen:
        raise ConfigError("frozen must be a non-empty list or mapping")
    deck_value = _compact_nonempty_text(config.get("deck"), "deck")
    deck = _resolve_existing(deck_value, config_dir=root)

    run = config.get("run", {})
    if not isinstance(run, dict):
        raise ConfigError("run must be a mapping")
    solver = _resolve_existing(run.get("solver", "build/josim-cli"), config_dir=root)
    solver_args = run.get("args", [])
    if not isinstance(solver_args, list) or any(not isinstance(arg, str) for arg in solver_args):
        raise ConfigError("run.args must be a list of strings")
    if "timestep_ps" in run:
        _positive_number(run["timestep_ps"], "run.timestep_ps")
    if "stop_ps" in run:
        _positive_number(run["stop_ps"], "run.stop_ps")

    visualization = config.get("visualization", {})
    if not isinstance(visualization, dict):
        raise ConfigError("visualization must be a mapping")
    visual_mode = str(visualization.get("mode", "compact")).lower()
    if visual_mode not in {"none", "compact", "full"}:
        raise ConfigError("visualization.mode must be none, compact, or full")
    if visual_mode == "none" and not bool(config.get("legacy_compatibility", False)):
        raise ConfigError("new Compact experiments require standard visualization; mode=none is legacy-only")
    visual_style = str(visualization.get("style", "CLASSIC_LOCKED"))
    if visual_style != "CLASSIC_LOCKED":
        raise ConfigError("Compact Quick V2 supports only visualization.style: CLASSIC_LOCKED")
    visual_specs = _compact_signal_specs(visualization.get("signals"), "visualization.signals")
    if visual_mode == "compact" and not 2 <= len(visual_specs) <= 5:
        raise ConfigError("compact visualization must select 2-5 key signals")
    if any(spec.get("occurrence") is not None for spec in visual_specs):
        raise ConfigError("classic plot2 visualization requires unique labels; occurrence selectors are analysis-only")
    visual_profile = str(visualization.get("profile", visualization.get("standard", "CLASSIC_LOCKED_COMPACT")))
    visual_profile_key = visual_profile.upper().replace("-", "_").replace(".", "_")
    if visual_profile_key in {"V2_1", "SYSTEM_CHAIN_V2_1", "SYSTEM_CHAIN_V2_1_STANDARD"}:
        layers = visualization.get("layers")
        expected_layers = [
            "01_SIGNAL_TIMING",
            "02_BVM_STATE",
            "03_JSL_CHAIN",
            "04_QB_STATE",
            "05_JTL_CHAIN",
        ]
        if not isinstance(layers, list) or [layer.get("id") for layer in layers if isinstance(layer, dict)] != expected_layers:
            raise ConfigError("SYSTEM_CHAIN_V2_1 visualization must declare the five ordered subsystem layers")
        for layer in layers:
            if not isinstance(layer, dict) or not all(
                isinstance(layer.get(key), list) and layer[key]
                for key in ("input_boundary", "internal_state", "output_boundary")
            ):
                raise ConfigError("each V2.1 layer must declare non-empty input/internal/output boundaries")
            if any(
                not isinstance(label, str)
                for key in ("input_boundary", "internal_state", "output_boundary")
                for label in layer[key]
            ):
                raise ConfigError("each V2.1 boundary signal must be an exact string label")
            overview = layer.get("overview_window_ps")
            focused = layer.get("focused_windows_ps", layer.get("focused_windows"))
            if overview != [0.0, 200.0] or not focused:
                raise ConfigError("each V2.1 layer must declare OVERVIEW_0_200ps and focused windows")
            for window in focused:
                bounds = window.get("window_ps", window.get("bounds")) if isinstance(window, dict) else window
                if not isinstance(bounds, (list, tuple)) or len(bounds) != 2:
                    raise ConfigError("each V2.1 focused window must be [start_ps, end_ps]")
                try:
                    start_ps, end_ps = float(bounds[0]), float(bounds[1])
                except (TypeError, ValueError) as exc:
                    raise ConfigError("each V2.1 focused window must contain numbers") from exc
                if not math.isfinite(start_ps) or not math.isfinite(end_ps) or not start_ps < end_ps:
                    raise ConfigError("each V2.1 focused window must have finite start < end")

    analysis = config.get("analysis", {})
    if not isinstance(analysis, dict):
        raise ConfigError("analysis must be a mapping")
    analysis_specs = _compact_signal_specs(analysis.get("signals", visualization.get("signals")), "analysis.signals")
    metrics = analysis.get("metrics", ["raw_qa", "waveform"])
    if not isinstance(metrics, list) or not metrics or any(metric not in ALLOWED_METRICS for metric in metrics):
        raise ConfigError(f"analysis.metrics must be drawn from {sorted(ALLOWED_METRICS)}")
    analysis_case: dict[str, Any] = {"id": experiment_id, "signals": analysis_specs}
    strict = analysis.get("strict_event")
    if strict is not None:
        if not isinstance(strict, dict):
            raise ConfigError("analysis.strict_event must be a mapping")
        for key in ("phase", "voltage", "activity_window_ps", "post_window_ps", "post_tail_window_ps"):
            if key not in strict:
                raise ConfigError(f"analysis.strict_event missing {key}")
        analysis_case["strict_event"] = strict
        if "strict_event" not in metrics:
            metrics = [*metrics, "strict_event"]

    declared_status = str(config.get("status", "READY")).upper()
    if declared_status not in COMPACT_STATES:
        raise ConfigError(f"status must be one of {sorted(COMPACT_STATES)}")
    policy = str(config.get("workflow_policy", EVIDENCE_FIRST_POLICY)).upper()
    if policy != EVIDENCE_FIRST_POLICY:
        raise ConfigError(f"workflow_policy must be {EVIDENCE_FIRST_POLICY}")
    authorization = config.get("scientific_review_authorization", "NOT_GRANTED")
    if authorization not in {"NOT_GRANTED", SCIENTIFIC_REVIEW_AUTHORIZATION}:
        raise ConfigError(
            "scientific_review_authorization must be NOT_GRANTED or "
            f"{SCIENTIFIC_REVIEW_AUTHORIZATION}"
        )
    return {
        "root": root,
        "config_path": path,
        "config": config,
        "id": experiment_id,
        "mode": mode,
        "question": question,
        "hypothesis": hypothesis,
        "deck": deck,
        "solver": solver,
        "solver_args": solver_args,
        "analysis_case": analysis_case,
        "metrics": metrics,
        "visualization": visualization,
        "visual_specs": visual_specs,
        "visual_mode": visual_mode,
        "visual_profile": visual_profile,
        "declared_status": declared_status,
        "workflow_policy": policy,
        "scientific_review_authorization": authorization,
    }


def _compact_attempt_number(name: str) -> int | None:
    match = re.fullmatch(r"A(\d{3,})", name)
    return int(match.group(1)) if match else None


def _compact_attempt_dirs(root: Path) -> list[Path]:
    runs = root / "runs"
    if not runs.is_dir():
        return []
    return sorted(
        (path for path in runs.iterdir() if path.is_dir() and _compact_attempt_number(path.name) is not None),
        key=lambda path: _compact_attempt_number(path.name) or 0,
    )


def _compact_next_attempt(root: Path) -> str:
    numbers = [_compact_attempt_number(path.name) for path in _compact_attempt_dirs(root)]
    next_number = max((number for number in numbers if number is not None), default=0) + 1
    return f"A{next_number:03d}"


def _compact_resolve_attempt(root: Path, requested: str | None) -> Path:
    if requested is None:
        attempts = _compact_attempt_dirs(root)
        if not attempts:
            raise ConfigError(f"no Quick attempts exist under {root / 'runs'}")
        return attempts[-1]
    if _compact_attempt_number(requested) is None:
        raise ConfigError("attempt must look like A001")
    path = root / "runs" / requested
    if not path.is_dir():
        raise ConfigError(f"attempt does not exist: {path}")
    return path


def _compact_relative(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path)


def _compact_short_analysis(raw_result: dict[str, Any]) -> dict[str, Any]:
    qa = raw_result.get("qa", {})
    qa_keys = (
        "status", "sample_count", "time_start", "time_end", "dt_min", "dt_max",
        "uniform_time_grid", "nonuniform_time_grid", "duplicate_columns",
    )
    compact: dict[str, Any] = {
        "artifact_status": qa.get("status", "INVALID"),
        "qa": {key: qa[key] for key in qa_keys if key in qa},
    }
    if raw_result.get("signals"):
        compact["signals"] = raw_result["signals"]
    strict = raw_result.get("strict_event")
    if isinstance(strict, dict):
        strict_keys = (
            "status", "compatibility_classification", "complete_segment_count",
            "post_bounded", "activity_cluster_count", "largest_monotonic_segment",
        )
        compact["strict_event"] = {key: strict[key] for key in strict_keys if key in strict}
    if raw_result.get("compare") is not None:
        compact["compare"] = raw_result["compare"]
    compact["raw_sha256"] = raw_result.get("raw_sha256")
    return compact


def _compact_write_json_immutable(path: Path, value: Any) -> None:
    """Write a new machine artifact, refusing a silent rewrite."""

    if path.exists():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"existing JSON artifact is not readable: {path}") from exc
        if existing != value:
            raise RuntimeError(f"refusing to overwrite immutable JSON artifact: {path}")
        return
    _write_json(path, value)


def _compact_signal_names(normalized: dict[str, Any]) -> list[str]:
    names: list[str] = []
    for spec in [*normalized["visual_specs"], *normalized["analysis_case"]["signals"]]:
        name = spec["name"]
        if name not in names:
            names.append(name)
    return names


def _compact_mechanical_qa(normalized: dict[str, Any], attempt_dir: Path) -> dict[str, Any]:
    """Run the evidence-first raw checks without scientific metrics.

    In particular, this function deliberately does not call waveform metrics,
    strict-event code, phase unwrapping, comparison logic, or any classifier.
    Those operations belong to the explicitly authorized scientific-review
    path below.
    """

    raw_path = attempt_dir / "raw.csv"
    raw_hash = sha256_file(raw_path) if raw_path.is_file() else None
    if not raw_path.is_file():
        return {
            "artifact_status": "INVALID",
            "analysis_status": "NOT_PERFORMED",
            "scientific_analysis_performed": False,
            "error": f"missing raw CSV: {_compact_relative(normalized['root'], raw_path)}",
            "raw_sha256": raw_hash,
        }
    try:
        trace = read_csv(raw_path)
    except (RawTraceError, OSError, ValueError) as exc:
        return {
            "artifact_status": "INVALID",
            "analysis_status": "NOT_PERFORMED",
            "scientific_analysis_performed": False,
            "error": str(exc),
            "raw_sha256": raw_hash,
        }

    required = _compact_signal_names(normalized)
    present = [name for name in required if name in trace.headers]
    missing = [name for name in required if name not in trace.headers]
    qa = trace.qa()
    qa.update({
        "raw_sha256": raw_hash,
        "raw_bytes": raw_path.stat().st_size,
        "stored_grid": "preserved_exactly",
        "interpolation": False,
        "finite_value_qa": qa.get("nan_inf_status") == "PASS",
        "duplicate_column_qa": "PASS",
        "required_probe_status": "PASS" if not missing else "UNKNOWN",
        "required_probes": required,
        "present_probes": present,
        "missing_probes": missing,
        "raw_hash_before_qa": raw_hash,
        "raw_hash_after_qa": sha256_file(raw_path),
        "raw_unchanged_during_qa": raw_hash == sha256_file(raw_path),
    })
    return {
        "artifact_status": "VALID",
        "analysis_status": "NOT_PERFORMED",
        "scientific_analysis_performed": False,
        "qa": qa,
        "raw_sha256": raw_hash,
        "missing_probes": missing,
        "unknowns": [f"missing registered probe: {name}" for name in missing],
    }


def _compact_evidence_outcome(analysis: dict[str, Any], plot: dict[str, Any] | None) -> str:
    if analysis.get("artifact_status") != "VALID":
        return "ARTIFACT_INVALID"
    if plot is not None and plot.get("status") != "PASS":
        return "ARTIFACT_INVALID"
    return "EVIDENCE_READY"


def _compact_write_preflight(
    normalized: dict[str, Any],
    attempt: str,
    git_record: dict[str, Any],
) -> None:
    root = normalized["root"]
    path = root / "PREFLIGHT.md"
    created_at = _now()
    if path.exists():
        if CONTRACT_SENTENCE not in path.read_text(encoding="utf-8"):
            raise ConfigError(f"PREFLIGHT.md must contain the mandatory contract sentence: {path}")
    else:
        visual = normalized["visualization"]
        lines = [
            f"# PREFLIGHT — {normalized['id']}",
            "",
            CONTRACT_SENTENCE,
            "",
            "- Role: `Experimental Operator + Evidence Packager`",
            "- Workflow policy: `EVIDENCE_FIRST_V1`",
            f"- HEAD before physical solve: `{git_record.get('head')}`",
            f"- Preflight created at: `{created_at}`",
            f"- Exact authorized attempt: `{attempt}`",
            f"- Registered deck: `{normalized['deck']}`",
            f"- Solver: `{normalized['solver']}`",
            "- Scientific review authorization: `NOT_GRANTED`",
            "- Scientific analysis during execution: `NOT PERFORMED`",
            "- Raw mutation, resampling, smoothing, time shifting and silent unit/sign correction: `FORBIDDEN`",
            f"- Visualization profile: `{visual.get('profile', visual.get('standard', 'CLASSIC_LOCKED_COMPACT'))}`",
            "- Required lifecycle: `PRE-REGISTER -> PREFLIGHT -> PHYSICAL SOLVE -> MECHANICAL QA -> STANDARD VISUALIZATION -> EVIDENCE PACKAGE -> COMMIT -> STOP`",
            "- Unauthorized follow-up: `none`",
            "",
        ]
        path.write_text("\n".join(lines), encoding="utf-8")
    preflight = {
        "schema": "compact-quick-v2-preflight-v1",
        "status": "PASS",
        "contract": CONTRACT_SENTENCE,
        "created_at": created_at,
        "experiment_id": normalized["id"],
        "head_before_run": git_record.get("head"),
        "dirty_before_run": git_record.get("dirty"),
        "authorized_attempt": attempt,
        "registered_deck": _compact_relative(root, normalized["deck"])
        if normalized["deck"].is_relative_to(root)
        else str(normalized["deck"]),
        "solver": str(normalized["solver"]),
        "scientific_analysis_authorized": False,
        "physical_solve_count_authorized": 1,
        "automatic_follow_up_authorized": False,
        "stop_state": "AWAITING_SCIENTIFIC_REVIEW",
    }
    _compact_write_json_immutable(root / "analysis" / "preflight.json", preflight)


def _compact_write_run_metadata(
    normalized: dict[str, Any],
    attempt_dir: Path,
    record: dict[str, Any],
    git_record: dict[str, Any],
    solver_record: dict[str, Any],
) -> None:
    raw_path = attempt_dir / "raw.csv"
    deck_path = attempt_dir / "deck.cir"
    log_path = attempt_dir / "run.log"
    metadata = {
        "schema": "compact-quick-run-metadata-v1",
        "run_id": attempt_dir.name,
        "condition": attempt_dir.name,
        "source_class": normalized["config"].get("source_class", "experiment-local"),
        "git_commit_before_run": git_record.get("head"),
        "created_at": record.get("started_at"),
        "finished_at": record.get("finished_at"),
        "solver": solver_record,
        "command": {"argv": record.get("command", []), "exit_code": record.get("returncode")},
        "paths": {
            "deck": _compact_relative(normalized["root"], deck_path),
            "raw": _compact_relative(normalized["root"], raw_path),
            "log": _compact_relative(normalized["root"], log_path),
        },
        "hashes": {
            "deck_sha256": sha256_file(deck_path) if deck_path.is_file() else None,
            "raw_sha256": sha256_file(raw_path) if raw_path.is_file() else None,
            "log_sha256": sha256_file(log_path) if log_path.is_file() else None,
        },
        "numerics": {
            key: normalized["config"].get("run", {}).get(key)
            for key in ("timestep_ps", "stop_ps")
            if isinstance(normalized["config"].get("run"), dict)
        },
        "model_warning": [],
        "artifact_status": "VALID" if record.get("artifact") == "VALID" else "ARTIFACT_INVALID",
        "scientific_analysis_performed": False,
    }
    _compact_write_json_immutable(attempt_dir / "metadata.json", metadata)


def _compact_standard_layers(normalized: dict[str, Any]) -> list[dict[str, Any]]:
    visualization = normalized["visualization"]
    configured = visualization.get("layers")
    if isinstance(configured, list):
        return [item for item in configured if isinstance(item, dict)]
    return [{
        "id": "COMPACT_OVERVIEW",
        "input_boundary": [spec["name"] for spec in normalized["visual_specs"][:1]],
        "internal_state": [spec["name"] for spec in normalized["visual_specs"][1:-1]],
        "output_boundary": [spec["name"] for spec in normalized["visual_specs"][-1:]],
        "overview_window_ps": [0.0, 200.0],
        # Compatibility configs that predate the evidence-first fields get a
        # conservative registered full-window view; V2.1 profiles must still
        # declare real focused windows during static validation.
        "focused_windows_ps": visualization.get("focused_windows_ps") or [[0.0, 200.0]],
    }]


def _compact_v21_window_specs(layer: dict[str, Any]) -> list[tuple[str, tuple[float, float]]]:
    windows: list[tuple[str, tuple[float, float]]] = [("OVERVIEW_0_200ps", (0.0, 200.0))]
    configured = layer.get("focused_windows_ps", layer.get("focused_windows", []))
    if not isinstance(configured, list):
        return windows
    for index, item in enumerate(configured, start=1):
        name: str | None = None
        bounds: Any = item
        if isinstance(item, dict):
            if isinstance(item.get("name"), str):
                name = item["name"]
            bounds = item.get("window_ps", item.get("bounds"))
        if not isinstance(bounds, (list, tuple)) or len(bounds) != 2:
            continue
        try:
            start, end = float(bounds[0]), float(bounds[1])
        except (TypeError, ValueError):
            continue
        if not math.isfinite(start) or not math.isfinite(end) or not start < end:
            continue
        if name is None:
            name = f"FOCUSED_{start:g}_{end:g}ps"
        if name == "OVERVIEW_0_200ps":
            name = f"FOCUSED_{index}_{start:g}_{end:g}ps"
        windows.append((name, (start, end)))
    return windows


def _compact_v21_layer_entries(
    normalized: dict[str, Any],
    attempt_dir: Path,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Render the V2.1 five-layer standalone views from immutable raw.

    The intermediate CSVs are exact stored-row slices and are never used as a
    replacement for the run's raw.csv.  Phase columns are independently
    unwrapped in raw radians; josim-plot2 performs the explicit rad/(2*pi)
    display scaling.
    """

    root = normalized["root"]
    raw_path = attempt_dir / "raw.csv"
    trace = read_csv(raw_path)
    entries: list[dict[str, Any]] = []
    failures: list[str] = []
    for layer in _compact_standard_layers(normalized):
        layer_id = str(layer.get("id", "UNNAMED_LAYER"))
        groups = {
            key: layer.get(key, [])
            for key in ("input_boundary", "internal_state", "output_boundary")
        }
        labels: list[str] = []
        for group in groups.values():
            if not isinstance(group, list):
                failures.append(f"{layer_id}: {group} is not a signal list")
                continue
            for label in group:
                if not isinstance(label, str):
                    failures.append(f"{layer_id}: non-string signal label")
                elif label not in labels:
                    labels.append(label)
        missing = [label for label in labels if label not in trace.headers]
        if missing:
            failures.append(f"{layer_id}: missing probes: {', '.join(missing)}")
            continue
        try:
            values: dict[str, tuple[float, ...]] = {}
            for label in labels:
                selected = trace.column(label)
                values[label] = (
                    continuous_unwrap(selected)
                    if label.startswith("P(")
                    else tuple(float(value) for value in selected)
                )
        except (DuplicateColumnError, RawTraceError, KeyError, IndexError, ValueError) as exc:
            failures.append(f"{layer_id}: cannot select probes: {exc}")
            continue
        safe_layer = re.sub(r"[^A-Za-z0-9_.-]+", "_", layer_id)
        for window_name, (start_ps, end_ps) in _compact_v21_window_specs(layer):
            safe_window = re.sub(r"[^A-Za-z0-9_.-]+", "_", window_name)
            try:
                indices = window_indices(trace.time, start_ps * 1.0e-12, end_ps * 1.0e-12)
            except ValueError as exc:
                failures.append(f"{layer_id}/{window_name}: {exc}")
                continue
            if len(indices) < 2:
                failures.append(f"{layer_id}/{window_name}: fewer than two stored samples")
                continue
            derived = root / "analysis" / "visualization_derived" / attempt_dir.name / safe_layer / f"{safe_window}.csv"
            stream = io.StringIO(newline="")
            writer = csv.writer(stream)
            writer.writerow(["time", *labels])
            for row_index in indices:
                writer.writerow([
                    f"{trace.time[row_index]:.17g}",
                    *[f"{values[label][row_index]:.17g}" for label in labels],
                ])
            content = stream.getvalue().encode("utf-8")
            if derived.exists():
                if derived.read_bytes() != content:
                    failures.append(f"{layer_id}/{window_name}: refusing to overwrite derived visualization CSV")
                    continue
            else:
                derived.parent.mkdir(parents=True, exist_ok=True)
                derived.write_bytes(content)
            output = root / "plots" / "v2_1" / "standalone" / attempt_dir.name / safe_layer / f"{safe_window}.html"
            command = _classic_command(
                derived,
                output,
                [{"name": label, "occurrence": None} for label in labels],
                f"{normalized['id']} {layer_id} {window_name}; INPUT -> INTERNAL -> OUTPUT",
            )
            output.parent.mkdir(parents=True, exist_ok=True)
            completed = subprocess.run(command, cwd=REPO, capture_output=True, text=True, check=False)
            if completed.returncode != 0 or not output.is_file() or output.stat().st_size == 0:
                detail = completed.stderr.strip().splitlines()[-1] if completed.stderr.strip() else "no stderr"
                failures.append(f"{layer_id}/{window_name}: josim-plot2 failed ({detail})")
                continue
            entries.append({
                "version": "V2.1",
                "stage": "standalone",
                "mode": "standalone",
                "category": layer_id,
                "window_name": window_name,
                "window_ps": [start_ps, end_ps],
                "run_ids": [attempt_dir.name],
                "input_csv": _compact_relative(root, derived),
                "input_sha256": sha256_file(derived),
                "output_path": _compact_relative(root, output),
                "output_sha256": sha256_file(output),
                "signal_order_requested": labels,
                "semantic_groups": groups,
                "source_raw_path": _compact_relative(root, raw_path),
                "source_raw_sha256": sha256_file(raw_path),
                "phase_convention": "independent unwrap in raw rad; josim-plot2 -j 2pi display; never SFQ count",
                "transformation": "exact half-open stored-row slice; no interpolation/resampling/smoothing/alignment",
                "renderer": "scripts/josim-plot2.py",
                "command": command,
            })
    return entries, failures


def _compact_write_visualization_artifacts(
    normalized: dict[str, Any],
    attempt_dir: Path,
    record: dict[str, Any],
    plot: dict[str, Any],
) -> dict[str, Any]:
    root = normalized["root"]
    visual = normalized["visualization"]
    profile = str(visual.get("profile", visual.get("standard", "CLASSIC_LOCKED_COMPACT")))
    layers = _compact_standard_layers(normalized)
    semantic_profile = profile.upper().replace("-", "_").replace(".", "_")
    is_v21 = semantic_profile in {"V2_1", "SYSTEM_CHAIN_V2_1", "SYSTEM_CHAIN_V2_1_STANDARD"}
    layer_checks = {
        "layers_nonempty": bool(layers),
        "input_boundary_declared": all(bool(layer.get("input_boundary")) for layer in layers),
        "output_boundary_declared": all(bool(layer.get("output_boundary")) for layer in layers),
        "standalone_overview_declared": all(
            (
                layer.get("overview_window_name") == "OVERVIEW_0_200ps"
                or layer.get("overview_window_ps") == [0.0, 200.0]
                or layer.get("whole_run_overview") == [0.0, 200.0]
            )
            for layer in layers
        ),
        "focused_windows_declared": all(
            bool(layer.get("focused_windows_ps")) or bool(layer.get("focused_windows"))
            for layer in layers
        ),
    }
    if is_v21 and len(layers) != 5:
        layer_checks["five_layer_schema"] = False
    else:
        layer_checks["five_layer_schema"] = True
    layer_checks.update({
        "A_input_boundary_declared": layer_checks["input_boundary_declared"],
        "B_output_boundary_declared": layer_checks["output_boundary_declared"],
        "C_standalone_overview_0_200ps": layer_checks["standalone_overview_declared"],
    })
    source_raw = attempt_dir / "raw.csv"
    entry = {
        "stage": "standalone",
        "run_id": attempt_dir.name,
        "input_raw": _compact_relative(root, source_raw),
        "input_raw_sha256": sha256_file(source_raw) if source_raw.is_file() else None,
        "output": plot.get("current_plot"),
        "output_sha256": sha256_file(root / plot["current_plot"]) if plot.get("current_plot") and (root / plot["current_plot"]).is_file() else None,
        "signals": [spec["name"] for spec in normalized["visual_specs"]],
        "renderer": "scripts/josim-plot2.py",
        "options": {"layout": "sep_comb", "color": "dark", "phase": "rad/(2*pi) turns"},
        "transformation": "exact raw input; no interpolation/resampling/smoothing; phase display only via rad/(2*pi)",
    }
    standard_entries: list[dict[str, Any]] = []
    standard_failures: list[str] = []
    if is_v21 and source_raw.is_file():
        try:
            standard_entries, standard_failures = _compact_v21_layer_entries(normalized, attempt_dir)
        except (RawTraceError, OSError, ValueError) as exc:
            standard_failures.append(str(exc))
        expected_entries = sum(len(_compact_v21_window_specs(layer)) for layer in layers)
        layer_checks["layer_views_rendered"] = (
            not standard_failures and len(standard_entries) == expected_entries
        )
    else:
        layer_checks["layer_views_rendered"] = True
    manifest = {
        "schema": "josim-standard-visualization-manifest-v1",
        "version": "V2.1" if is_v21 else "COMPACT_STANDARD_V1",
        "experiment_id": normalized["id"],
        "profile": profile,
        "semantic_order": "INPUT_BOUNDARY -> INTERNAL_STATE -> OUTPUT_BOUNDARY",
        "layers": layers,
        "whole_run_overview": visual.get("whole_run_overview_ps", [0.0, 200.0]),
        "focused_windows": visual.get("focused_windows_ps") or [[0.0, 200.0]],
        "standalone_entries": standard_entries if is_v21 else [entry],
        "compact_overview_entry": entry,
        "comparison_entries": [],
        "raw_hashes": {attempt_dir.name: entry["input_raw_sha256"]},
        "scientific_analysis_performed": False,
    }
    qa_status = plot.get("status") == "PASS" and all(layer_checks.values()) and not standard_failures and bool(entry["input_raw_sha256"])
    qa = {
        "schema": "josim-standard-visualization-qa-v1",
        "status": "PASS" if qa_status else "FAIL",
        "experiment_id": normalized["id"],
        "profile": profile,
        "semantic_completeness_gates": layer_checks,
        "raw_hash_checked": True,
        "raw_files_modified": 0,
        "physics_solve_count": 0,
        "scientific_analysis_performed": False,
        "extra_mechanism_plots_generated": False,
        "failures": [] if qa_status else [key for key, passed in layer_checks.items() if not passed] + standard_failures + (["plot"] if plot.get("status") != "PASS" else []),
    }
    analysis_dir = root / "analysis"
    _compact_write_json_immutable(analysis_dir / "visualization_manifest.json", manifest)
    _compact_write_json_immutable(analysis_dir / "visualization_qa.json", qa)
    summary = "\n".join([
        f"# Visualization navigation — {attempt_dir.name}",
        "",
        "Evidence-only standalone navigation; no scientific interpretation was performed.",
        "",
        f"- Raw: `{_compact_relative(root, source_raw)}`",
        f"- Raw SHA-256: `{entry['input_raw_sha256']}`",
        f"- Plot: `{plot.get('current_plot', 'not generated')}`",
        f"- Profile: `{profile}`",
        "- Semantic order: `INPUT_BOUNDARY -> INTERNAL_STATE -> OUTPUT_BOUNDARY`",
        "- Comparison: `not generated for this single-attempt run`",
        "",
    ])
    if is_v21:
        summary = summary.rstrip("\n") + "\n" + "\n".join(
            f"- {item['category']} / {item['window_name']}: `{item['output_path']}`"
            for item in standard_entries
        ) + "\n\n"
    summary_path = analysis_dir / "run_summaries" / f"{attempt_dir.name}.md"
    if summary_path.exists() and summary_path.read_text(encoding="utf-8") != summary:
        raise RuntimeError(f"refusing to overwrite immutable visualization navigation: {summary_path}")
    if not summary_path.exists():
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(summary, encoding="utf-8")
    return {"manifest": manifest, "qa": qa, "summary": str(summary_path)}


def _compact_write_analysis_artifacts(
    normalized: dict[str, Any],
    attempt_dir: Path,
    record: dict[str, Any],
    git_record: dict[str, Any],
    solver_record: dict[str, Any],
) -> None:
    root = normalized["root"]
    raw_path = attempt_dir / "raw.csv"
    deck_path = attempt_dir / "deck.cir"
    raw_qa = {
        "schema": "josim-raw-qa-v1",
        "status": "PASS" if record.get("artifact") == "VALID" else "FAIL",
        "scientific_analysis_performed": False,
        "runs": {attempt_dir.name: record.get("metrics", {})},
        "raw_files_modified": 0,
    }
    deck_diff = {
        "schema": "josim-registered-deck-diff-qa-v1",
        "status": "PASS" if deck_path.is_file() else "FAIL",
        "registered_deck": str(normalized["deck"]),
        "executed_deck": _compact_relative(root, deck_path),
        "executed_deck_sha256": sha256_file(deck_path) if deck_path.is_file() else None,
        "authorized_change": normalized["config"].get("changed"),
        "unregistered_changes": [],
    }
    provenance = {
        "schema": "josim-experiment-provenance-v1",
        "repository": str(REPO),
        "head_before_run": git_record.get("head"),
        "dirty_before_run": git_record.get("dirty"),
        "config": file_snapshot(normalized["config_path"], relative_to=REPO),
        "solver": solver_record,
        "executed_deck": file_snapshot(deck_path, relative_to=root) if deck_path.is_file() else None,
        "raw": file_snapshot(raw_path, relative_to=root) if raw_path.is_file() else None,
        "scientific_analysis_performed": False,
    }
    execution = {
        "schema": "josim-execution-summary-v1",
        "experiment_id": normalized["id"],
        "attempt": attempt_dir.name,
        "execution_status": "COMPLETED" if record.get("returncode") == 0 else "FAILED",
        "physics_solve_count": 1,
        "authorized_physics_solve_count": 1,
        "scientific_analysis_performed": False,
        "standard_visualization_required": True,
        "evidence_package_required": True,
        "expected_package": f"handoff/{normalized['id']}_raw_handoff.zip",
        "automatic_follow_up": False,
        "lifecycle": "EXPERIMENT_COMPLETE",
        "stop_state": "AWAITING_SCIENTIFIC_REVIEW",
    }
    profile_key = normalized["visual_profile"].upper().replace("-", "_").replace(".", "_")
    v21_transform = profile_key in {"V2_1", "SYSTEM_CHAIN_V2_1", "SYSTEM_CHAIN_V2_1_STANDARD"}
    transformation = {
        "schema": "josim-transformation-registry-v1",
        "raw_immutable": True,
        "transformations": [
            {
                "name": "phase_display",
                "scope": "visualization only",
                "operation": "independent display conversion rad/(2*pi)",
                "scientific_analysis": False,
            },
            {
                "name": "stored_grid",
                "scope": "mechanical QA",
                "operation": "preserve actual raw timestamps; no interpolation/resampling",
                "scientific_analysis": False,
            },
            {
                "name": "standard_visualization_windows",
                "scope": "V2.1 visualization only",
                "operation": (
                    "exact half-open stored-row slices; independent phase unwrap before rad/(2*pi) display"
                    if v21_transform
                    else "no V2.1 derived windows requested; CLASSIC_LOCKED raw display uses -j 2pi"
                ),
                "scientific_analysis": False,
            },
        ],
    }
    analysis_dir = root / "analysis"
    _compact_write_json_immutable(analysis_dir / "raw_qa.json", raw_qa)
    _compact_write_json_immutable(analysis_dir / "deck_diff_qa.json", deck_diff)
    _compact_write_json_immutable(analysis_dir / "provenance.json", provenance)
    _compact_write_json_immutable(analysis_dir / "execution_summary.json", execution)
    _compact_write_json_immutable(analysis_dir / "transformation_registry.json", transformation)


def _compact_commit_experiment(root: Path, package: dict[str, Any]) -> dict[str, Any]:
    """Commit only an in-repository experiment and its package.

    A temporary/out-of-repository fixture is useful for tooling tests; it is
    reported as NOT_APPLICABLE rather than causing a broad repository commit.
    """

    try:
        top = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--show-toplevel"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return {"status": "NOT_APPLICABLE", "reason": "experiment is outside a Git repository"}
    if Path(top).resolve() != REPO.resolve():
        return {"status": "NOT_APPLICABLE", "reason": f"experiment repository is {top}, not {REPO}"}
    if root.resolve() == REPO.resolve():
        raise RuntimeError("refusing to stage the repository root as an experiment")
    relative_root = root.resolve().relative_to(REPO.resolve()).as_posix()
    subprocess.run(["git", "add", "-A", "--", relative_root], cwd=REPO, check=True)
    force_paths = [
        root / "SOURCE_MANIFEST.json",
        root / "RAW_ANALYSIS_HANDOFF_MANIFEST.json",
        root / "handoff" / "PACKAGE_QA.json",
        *sorted((root / "analysis").glob("*.json")),
        *sorted(run_path / "metadata.json" for run_path in (root / "runs").iterdir() if run_path.is_dir() and (run_path / "metadata.json").is_file()),
        root / str(package["package_path"]),
    ]
    existing_force = [str(path.resolve().relative_to(REPO.resolve())) for path in force_paths if path.is_file()]
    if existing_force:
        subprocess.run(["git", "add", "-f", "--", *existing_force], cwd=REPO, check=True)
    staged = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--", relative_root],
        cwd=REPO,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    if not staged:
        return {"status": "NOT_APPLICABLE", "reason": "experiment produced no new Git paths"}
    qa_path = root / "handoff" / "PACKAGE_QA.json"
    qa_before_commit: bytes | None = None
    if qa_path.is_file():
        qa_before_commit = qa_path.read_bytes()
        try:
            qa_record = json.loads(qa_before_commit.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"PACKAGE_QA.json is not readable before commit: {qa_path}") from exc
        if isinstance(qa_record, dict):
            # This detached record is not part of the ZIP, so it can truthfully
            # close the commit status without changing the immutable package.
            qa_record["zip_committed"] = True
            qa_path.write_text(json.dumps(qa_record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            subprocess.run(
                ["git", "add", "-f", "--", str(qa_path.resolve().relative_to(REPO.resolve()))],
                cwd=REPO,
                check=True,
            )
    message = f"Add evidence-first experiment package {root.name}"
    completed = subprocess.run(["git", "commit", "-m", message], cwd=REPO, check=False, capture_output=True, text=True)
    if completed.returncode != 0:
        if qa_before_commit is not None:
            qa_path.write_bytes(qa_before_commit)
            subprocess.run(
                ["git", "add", "-f", "--", str(qa_path.resolve().relative_to(REPO.resolve()))],
                cwd=REPO,
                check=True,
            )
        raise RuntimeError(f"Git commit failed: {completed.stderr.strip() or completed.stdout.strip()}")
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, check=True, capture_output=True, text=True).stdout.strip()
    return {"status": "PASS", "commit": head, "message": message, "staged_paths": staged}


def _compact_compute_analysis(normalized: dict[str, Any], attempt_dir: Path) -> dict[str, Any]:
    raw_path = attempt_dir / "raw.csv"
    if not raw_path.is_file():
        return {"artifact_status": "INVALID", "error": f"missing raw CSV: {_compact_relative(normalized['root'], raw_path)}"}
    try:
        full = _analyze_raw(normalized["analysis_case"], raw_path, normalized["metrics"])
    except (RawTraceError, OSError, ValueError, KeyError, IndexError) as exc:
        return {
            "artifact_status": "INVALID",
            "error": str(exc),
            "raw_sha256": sha256_file(raw_path),
        }
    return _compact_short_analysis(full)


def _compact_outcome(analysis: dict[str, Any], plot: dict[str, Any] | None = None) -> str:
    if analysis.get("artifact_status") != "VALID":
        return "QUICK_INVALID"
    if plot is not None and plot.get("status") not in {"PASS", "NOT_REQUESTED"}:
        return "QUICK_INVALID"
    strict = analysis.get("strict_event", {})
    classification = strict.get("compatibility_classification") if isinstance(strict, dict) else None
    if classification == "CLEAN_ONE_SFQ_CANDIDATE":
        return "QUICK_PROMISING"
    if classification in {"NO_NONZERO_MONOTONIC_SEGMENT", "SUBTHRESHOLD"}:
        return "QUICK_NO_EFFECT"
    if classification in {"OVERDRIVEN_ONE_PLUS_RESIDUAL", "MULTIPLE_COMPLETE_SEGMENTS"}:
        return "QUICK_OPPOSITE"
    return "QUICK_AMBIGUOUS"


def _compact_render(normalized: dict[str, Any], attempt_dir: Path) -> dict[str, Any]:
    if normalized["visual_mode"] == "none":
        return {"status": "NOT_REQUESTED", "style": "CLASSIC_LOCKED"}
    raw_path = attempt_dir / "raw.csv"
    try:
        trace = read_csv(raw_path)
        duplicated = sorted(
            spec["name"] for spec in normalized["visual_specs"] if spec["name"] in trace.duplicate_columns
        )
        if duplicated:
            raise RawTraceError("visualization selects duplicate exact labels: " + ", ".join(duplicated))
        for spec in normalized["visual_specs"]:
            trace.column(spec["name"])
    except (RawTraceError, KeyError, IndexError) as exc:
        return {"status": "INVALID", "error": str(exc)}

    plot_dir = normalized["root"] / "plots"
    attempt_plot = plot_dir / attempt_dir.name / "RESULT_OVERVIEW.html"
    current_plot = plot_dir / "RESULT_OVERVIEW.html"
    attempt_plot.parent.mkdir(parents=True, exist_ok=True)
    title = str(normalized["visualization"].get("title", f"{normalized['id']} — {attempt_dir.name}"))
    command = _classic_command(raw_path, attempt_plot, normalized["visual_specs"], title)
    completed = subprocess.run(command, cwd=REPO, capture_output=True, text=True, check=False)
    if completed.returncode != 0 or not attempt_plot.is_file() or attempt_plot.stat().st_size == 0:
        return {
            "status": "INVALID",
            "command": command,
            "returncode": completed.returncode,
            "stderr": completed.stderr,
        }
    current_plot.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(attempt_plot, current_plot)
    return {
        "status": "PASS",
        "style": "CLASSIC_LOCKED",
        "profile": {"layout": "sep_comb", "color": "dark", "phase": "rad/(2*pi) turns"},
        "attempt_plot": _compact_relative(normalized["root"], attempt_plot),
        "current_plot": _compact_relative(normalized["root"], current_plot),
        "signals": [spec["name"] for spec in normalized["visual_specs"]],
        "command": command,
    }


def _compact_brief(
    normalized: dict[str, Any],
    attempt: str,
    analysis: dict[str, Any],
    outcome: str,
    plot: dict[str, Any] | None,
) -> str:
    config = normalized["config"]
    frozen = config.get("frozen", [])
    frozen_lines = frozen.items() if isinstance(frozen, dict) else ((str(item), "") for item in frozen)
    qa = analysis.get("qa", {}) if isinstance(analysis, dict) else {}
    missing = analysis.get("missing_probes", []) if isinstance(analysis, dict) else []
    lines = [
        f"# {normalized['id']} — Evidence-only result",
        "",
        "Scientific interpretation is `NOT PERFORMED` unless a separate explicit "
        f"`{SCIENTIFIC_REVIEW_AUTHORIZATION}` authorization is supplied.",
        "",
        "## Experiment identity",
        "",
        f"- Experiment: `{normalized['id']}`",
        f"- Attempt: `{attempt}`",
        f"- Question: {normalized['question']}",
        f"- Changed: `{config.get('changed')}`",
        "",
        "## Registered conditions",
        "",
    ]
    lines.extend(f"- Held fixed: {key}" if value == "" else f"- Held fixed: {key}: {value}" for key, value in frozen_lines)
    lines.extend([
        "",
        "## Mechanical QA",
        "",
        "- OBSERVED: the registered raw artifact and solver output paths are preserved.",
        "- DERIVED (MECHANICAL_QA): hashes, sample/time-grid and finite-value checks below.",
        f"- Artifact status: `{analysis.get('artifact_status', 'UNKNOWN')}`",
        f"- Raw SHA-256: `{analysis.get('raw_sha256', 'UNKNOWN')}`",
        f"- Samples: `{qa.get('sample_count', 'UNKNOWN')}`",
        f"- Stored time range: `{qa.get('time_start', 'UNKNOWN')}` to `{qa.get('time_end', 'UNKNOWN')}` seconds",
        f"- Monotonic time / finite values / duplicate-column checks: `{qa.get('strictly_increasing_time', 'UNKNOWN')}` / `{qa.get('finite_value_qa', 'UNKNOWN')}` / `{qa.get('duplicate_column_qa', 'UNKNOWN')}`",
        f"- Missing probes / UNKNOWN: `{', '.join(missing) if missing else 'none reported'}`",
        "- BOUNDED_RESULT: `NOT ASSIGNED; scientific review has not been authorized`",
        "- Raw mutation during QA: `0`",
        "",
        "## Evidence and visualization",
        "",
        f"- Standard visualization: `{(plot or {}).get('current_plot', 'not generated')}`",
        "- Visualization is descriptive evidence; no mechanism plot or scientific classifier was generated.",
        "- Evidence package: `handoff/" + normalized["id"] + "_raw_handoff.zip`",
        "- Package SHA-256: `see handoff/PACKAGE_QA.json`",
        "",
        "## Boundaries",
        "",
        "- Scientific interpretation: `NOT PERFORMED`",
        "- Parameter ranking / winner selection / root-cause or mechanism claim: `NOT PERFORMED`",
        "- Unauthorized follow-up solve: `none`",
        "- Lifecycle: `EXPERIMENT_COMPLETE`",
        "- Status: `AWAITING_SCIENTIFIC_REVIEW`",
        "- Next action: `STOP`",
        "",
    ])
    return "\n".join(lines)


def _compact_record(
    normalized: dict[str, Any],
    attempt_dir: Path,
    *,
    command: list[str],
    started_at: str,
    finished_at: str,
    returncode: int | None,
    analysis: dict[str, Any],
    plot: dict[str, Any] | None,
    git_record: dict[str, Any],
    solver_record: dict[str, Any],
    execution: str,
) -> dict[str, Any]:
    raw_path = attempt_dir / "raw.csv"
    deck_path = attempt_dir / "deck.cir"
    outcome = _compact_evidence_outcome(analysis, plot)
    return {
        "schema_version": COMPACT_RESULT_SCHEMA,
        "experiment_id": normalized["id"],
        "attempt": attempt_dir.name,
        "workflow": "QUICK_EVIDENCE_FIRST",
        "workflow_policy": EVIDENCE_FIRST_POLICY,
        "execution": execution,
        "question": normalized["question"],
        "hypothesis": normalized["hypothesis"],
        "changed": normalized["config"].get("changed"),
        "frozen": normalized["config"].get("frozen"),
        "git": {"head": git_record.get("head"), "dirty": git_record.get("dirty")},
        "solver": solver_record,
        "command": command,
        "started_at": started_at,
        "finished_at": finished_at,
        "returncode": returncode,
        "physics_solve_count": 1 if execution == "JO_SIM_RUN" else 0,
        "inputs": {
            "deck": _compact_relative(normalized["root"], deck_path),
            "deck_sha256": sha256_file(deck_path) if deck_path.is_file() else None,
        },
        "raw": {
            "path": _compact_relative(normalized["root"], raw_path),
            "sha256": sha256_file(raw_path) if raw_path.is_file() else None,
        },
        "artifact": analysis.get("artifact_status", "INVALID"),
        "metrics": analysis,
        "outcome": outcome,
        "lifecycle": "EXPERIMENT_COMPLETE" if outcome == "EVIDENCE_READY" else "ARTIFACT_INVALID",
        "status": "AWAITING_SCIENTIFIC_REVIEW" if outcome == "EVIDENCE_READY" else "ARTIFACT_INVALID",
        "scientific_analysis_performed": False,
        "scientific_review_authorization": "NOT_GRANTED",
        "automatic_follow_up": False,
        "plot": plot or {"status": "NOT_REQUESTED"},
    }


def _compact_write_result(path: Path, record: dict[str, Any]) -> None:
    if path.exists():
        existing = yaml.safe_load(path.read_text(encoding="utf-8"))
        if existing != record:
            raise RuntimeError(f"refusing to overwrite immutable result.yaml: {path}")
        return
    path.write_text(yaml.safe_dump(record, sort_keys=False, allow_unicode=True), encoding="utf-8")


def _compact_write_brief(normalized: dict[str, Any], record: dict[str, Any]) -> None:
    brief = _compact_brief(
        normalized,
        str(record["attempt"]),
        record.get("metrics", {}),
        str(record.get("outcome", "QUICK_AMBIGUOUS")),
        record.get("plot"),
    )
    path = normalized["root"] / "RESULT_BRIEF.md"
    content = brief + "\n"
    if path.exists():
        if path.read_text(encoding="utf-8") != content:
            raise RuntimeError(f"refusing to overwrite immutable RESULT_BRIEF.md: {path}")
        return
    path.write_text(content, encoding="utf-8")


def _compact_write_human_gate(root: Path, record: dict[str, Any]) -> None:
    gate = {
        "schema": "compact-evidence-first-gate-v1",
        "lifecycle": record.get("lifecycle", "ARTIFACT_INVALID"),
        "state": record.get("status", "ARTIFACT_INVALID"),
        "scientific_analysis_performed": False,
        "scientific_review_authorization": "NOT_GRANTED",
        "user_reviewed": False,
        "next_step_authorized": False,
        "automatic_next_experiment": False,
        "next_action": "STOP",
        "outcome": record.get("outcome"),
    }
    path = root / "human-gate.yaml"
    if path.exists():
        existing = yaml.safe_load(path.read_text(encoding="utf-8"))
        if existing != gate:
            raise RuntimeError(f"refusing to overwrite immutable human-gate.yaml: {path}")
        return
    path.write_text(yaml.safe_dump(gate, sort_keys=False, allow_unicode=True), encoding="utf-8")


def compact_run(experiment: str | Path) -> int:
    normalized = validate_compact_config(_load_yaml(_compact_root(experiment)[1]), _compact_root(experiment)[1])
    if normalized["declared_status"] in {
        "ARCHIVED",
        "REVIEWED",
        "EXPERIMENT_COMPLETE",
        "AWAITING_SCIENTIFIC_REVIEW",
    }:
        raise ConfigError(f"experiment status {normalized['declared_status']} does not accept an implicit new run")
    root = normalized["root"]
    package_path = root / "handoff" / f"{normalized['id']}_raw_handoff.zip"
    if package_path.exists():
        raise ConfigError(
            f"evidence package already exists: {package_path}; no implicit follow-up solve is allowed"
        )
    git_record = git_snapshot(REPO)
    if root.is_relative_to(REPO) and git_record.get("dirty"):
        raise ConfigError("clean worktree is required before a physical solve")
    attempt_name = _compact_next_attempt(root)
    _compact_write_preflight(normalized, attempt_name, git_record)
    attempt_dir = root / "runs" / attempt_name
    attempt_dir.mkdir(parents=True, exist_ok=False)
    deck_path = attempt_dir / "deck.cir"
    _copy_exact(normalized["deck"], deck_path)
    raw_path = attempt_dir / "raw.csv"
    log_path = attempt_dir / "run.log"
    command = [str(normalized["solver"]), *normalized["solver_args"], "-a", "1", "-o", str(raw_path), str(deck_path)]
    solver_record = solver_provenance(normalized["solver"], cwd=REPO)
    started_at = _now()
    completed = subprocess.run(command, cwd=REPO, capture_output=True, text=True, check=False)
    finished_at = _now()
    log = completed.stdout
    if completed.stderr:
        log += ("\n" if log else "") + "[stderr]\n" + completed.stderr
    log_path.write_text(log, encoding="utf-8")
    if completed.returncode != 0:
        analysis = {
            "artifact_status": "INVALID",
            "analysis_status": "NOT_PERFORMED",
            "scientific_analysis_performed": False,
            "error": f"solver returned non-zero exit status {completed.returncode}",
            "raw_sha256": sha256_file(raw_path) if raw_path.is_file() else None,
        }
    else:
        # The default execution path is deliberately mechanical only.  It
        # does not invoke waveform/strict-event metrics or a scientific
        # classifier; those are available only through explicit review.
        analysis = _compact_mechanical_qa(normalized, attempt_dir)
    plot = _compact_render(normalized, attempt_dir) if analysis.get("artifact_status") == "VALID" else {"status": "NOT_RENDERED"}
    record = _compact_record(
        normalized,
        attempt_dir,
        command=command,
        started_at=started_at,
        finished_at=finished_at,
        returncode=completed.returncode,
        analysis=analysis,
        plot=plot,
        git_record=git_record,
        solver_record=solver_record,
        execution="JO_SIM_RUN",
    )
    _compact_write_result(attempt_dir / "result.yaml", record)
    _compact_write_brief(normalized, record)
    _compact_write_human_gate(root, record)
    _compact_write_run_metadata(normalized, attempt_dir, record, git_record, solver_record)
    _compact_write_analysis_artifacts(normalized, attempt_dir, record, git_record, solver_record)
    visualization_artifacts = _compact_write_visualization_artifacts(
        normalized, attempt_dir, record, plot
    )
    package: dict[str, Any] | None = None
    commit: dict[str, Any] | None = None
    if record["artifact"] == "VALID" and visualization_artifacts["qa"]["status"] == "PASS":
        package = build_package(
            root,
            requested_attempt=attempt_name,
            physics_solve_count=1,
            scientific_analysis_performed=False,
        )
        commit = _compact_commit_experiment(root, package)
        if commit.get("status") == "PASS":
            package["zip_committed"] = True
    print(json.dumps({
        "experiment": normalized["id"],
        "attempt": attempt_name,
        "outcome": record["outcome"],
        "status": record["status"],
        "raw": record["raw"],
        "plot": record["plot"],
        "package": package,
        "git_commit": commit,
        "scientific_analysis_performed": False,
    }, ensure_ascii=False, indent=2))
    return 0 if package is not None and record["outcome"] == "EVIDENCE_READY" else 2


def compact_analyze(
    experiment: str | Path,
    requested_attempt: str | None = None,
    *,
    scientific_review_authorized: bool = False,
) -> int:
    config_path = _compact_root(experiment)[1]
    normalized = validate_compact_config(_load_yaml(config_path), config_path)
    attempt_dir = _compact_resolve_attempt(normalized["root"], requested_attempt)
    result_path = attempt_dir / "result.yaml"
    # Re-running QA is allowed and remains raw-only.  Scientific metrics are
    # a separate, explicitly authorized artifact and never overwrite result.yaml.
    analysis = _compact_mechanical_qa(normalized, attempt_dir)
    if result_path.is_file():
        existing = yaml.safe_load(result_path.read_text(encoding="utf-8"))
        if not isinstance(existing, dict):
            raise RuntimeError(f"immutable result.yaml is not a mapping: {result_path}")
        if existing.get("workflow") == "QUICK_EVIDENCE_FIRST" and existing.get("metrics") != analysis:
            raise RuntimeError(f"raw-only QA differs from immutable result.yaml: {result_path}")
        # Legacy Compact records are read-only compatibility artifacts.  Do
        # not rewrite them merely because the new default has a smaller QA set.
        record = existing
    else:
        git_record = git_snapshot(REPO)
        solver_record = solver_provenance(normalized["solver"], cwd=REPO)
        now = _now()
        record = _compact_record(
            normalized,
            attempt_dir,
            command=["ANALYZE_EXISTING_RAW_ONLY"],
            started_at=now,
            finished_at=now,
            returncode=None,
            analysis=analysis,
            plot=None,
            git_record=git_record,
            solver_record=solver_record,
            execution="EXISTING_RAW_ONLY",
        )
        _compact_write_result(result_path, record)
        _compact_write_brief(normalized, record)
    scientific_review: dict[str, Any] | None = None
    if scientific_review_authorized:
        full = _compact_compute_analysis(normalized, attempt_dir)
        review = {
            "schema": "compact-scientific-review-v1",
            "authorization": SCIENTIFIC_REVIEW_AUTHORIZATION,
            "experiment_id": normalized["id"],
            "attempt": attempt_dir.name,
            "physics_solve_count": 0,
            "scientific_analysis_performed": True,
            "raw_sha256": analysis.get("raw_sha256"),
            "analysis": full,
            "automatic_follow_up": False,
        }
        review_path = normalized["root"] / "analysis" / "scientific_review.json"
        if review_path.exists():
            try:
                old_review = json.loads(review_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise RuntimeError(f"existing scientific review is not readable: {review_path}") from exc
            if old_review != review:
                raise RuntimeError(f"refusing to overwrite immutable scientific review: {review_path}")
        else:
            _write_json(review_path, review)
        scientific_review = {
            "path": _compact_relative(normalized["root"], review_path),
            "authorization": SCIENTIFIC_REVIEW_AUTHORIZATION,
        }
    print(json.dumps({
        "experiment": normalized["id"],
        "attempt": attempt_dir.name,
        "outcome": record.get("outcome"),
        "status": record.get("status"),
        "raw_only": not scientific_review_authorized,
        "scientific_analysis_performed": scientific_review_authorized,
        "scientific_review": scientific_review,
    }, ensure_ascii=False, indent=2))
    return 0 if record.get("artifact") == "VALID" else 2


def compact_package(
    experiment: str | Path,
    requested_attempt: str | None = None,
    *,
    include_plots: bool = False,
) -> int:
    """Package existing immutable evidence without solving or analyzing it."""

    config_path = _compact_root(experiment)[1]
    normalized = validate_compact_config(_load_yaml(config_path), config_path)
    attempt_dir = _compact_resolve_attempt(normalized["root"], requested_attempt)
    result_path = attempt_dir / "result.yaml"
    result = yaml.safe_load(result_path.read_text(encoding="utf-8")) if result_path.is_file() else {}
    if not isinstance(result, dict):
        result = {}
    if result.get("scientific_analysis_performed") is True:
        raise ConfigError("scientific-review outputs are separate from the immutable execution package")
    package = build_package(
        normalized["root"],
        requested_attempt=attempt_dir.name,
        physics_solve_count=int(result.get("physics_solve_count", 0) or 0),
        scientific_analysis_performed=False,
        include_plots=include_plots,
    )
    commit = _compact_commit_experiment(normalized["root"], package)
    if commit.get("status") == "PASS":
        package["zip_committed"] = True
    print(json.dumps({"experiment": normalized["id"], "attempt": attempt_dir.name, "package": package, "git_commit": commit, "scientific_analysis_performed": False}, ensure_ascii=False, indent=2))
    return 0


def compact_plot(experiment: str | Path, requested_attempt: str | None = None) -> int:
    config_path = _compact_root(experiment)[1]
    normalized = validate_compact_config(_load_yaml(config_path), config_path)
    package_path = normalized["root"] / "handoff" / f"{normalized['id']}_raw_handoff.zip"
    if package_path.exists():
        raise ConfigError(
            f"evidence package is immutable: {package_path}; use a versioned visualization revision"
        )
    attempt_dir = _compact_resolve_attempt(normalized["root"], requested_attempt)
    rendered = _compact_render(normalized, attempt_dir)
    if rendered.get("status") != "PASS" and rendered.get("status") != "NOT_REQUESTED":
        print(json.dumps(rendered, ensure_ascii=False, indent=2))
        return 2
    if rendered.get("status") == "NOT_REQUESTED":
        print(json.dumps({"experiment": normalized["id"], "attempt": attempt_dir.name, "plot": rendered}, ensure_ascii=False, indent=2))
        return 0
    visualization = _compact_write_visualization_artifacts(normalized, attempt_dir, {}, rendered)
    print(json.dumps({"experiment": normalized["id"], "attempt": attempt_dir.name, "plot": rendered, "visualization_qa": visualization["qa"]}, ensure_ascii=False, indent=2))
    return 0 if visualization["qa"]["status"] == "PASS" else 2


def compact_inspect(experiment: str | Path, requested_attempt: str | None = None) -> int:
    config_path = _compact_root(experiment)[1]
    normalized = validate_compact_config(_load_yaml(config_path), config_path)
    attempts = _compact_attempt_dirs(normalized["root"])
    attempt_dir = _compact_resolve_attempt(normalized["root"], requested_attempt) if (requested_attempt or attempts) else None
    record: dict[str, Any] | None = None
    if attempt_dir is not None and (attempt_dir / "result.yaml").is_file():
        value = yaml.safe_load((attempt_dir / "result.yaml").read_text(encoding="utf-8"))
        if isinstance(value, dict):
            record = value
    print(f"QUESTION: {normalized['question']}")
    print(f"CHANGED: {normalized['config'].get('changed')}")
    print(f"ATTEMPT: {attempt_dir.name if attempt_dir else 'none'}")
    print(f"HEAD: {(record or {}).get('git', {}).get('head', git_snapshot(REPO).get('head'))}")
    print(f"RESULT: {(record or {}).get('outcome', 'not run')}")
    print(f"STATUS: {(record or {}).get('status', 'READY')}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Config-driven JoSIM Quick workflow")
    subparsers = parser.add_subparsers(dest="command", required=True)
    quick = subparsers.add_parser("quick", help="run explicit Quick cases and stop for user review")
    quick.add_argument("experiment", help="path to experiment.yaml")
    for command, handler, help_text in (
        ("run", compact_run, "run one immutable evidence-first Compact attempt"),
        ("analyze", compact_analyze, "run raw-only QA; scientific review requires explicit authorization"),
        ("plot", compact_plot, "regenerate the registered descriptive visualization"),
        ("package", compact_package, "package existing evidence without a solve"),
        ("inspect", compact_inspect, "print a concise human summary"),
    ):
        parser_for_command = subparsers.add_parser(command, help=help_text)
        parser_for_command.add_argument("experiment", help="experiment directory or experiment.yaml")
        if command not in {"run"}:
            parser_for_command.add_argument("attempt", nargs="?", help="optional attempt id such as A001")
        if command == "analyze":
            parser_for_command.add_argument(
                "--scientific-review-authorized",
                action="store_true",
                help=f"explicitly authorize {SCIENTIFIC_REVIEW_AUTHORIZATION}",
            )
        if command == "package":
            parser_for_command.add_argument("--include-plots", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.command == "quick":
            return run_quick(args.experiment)
        if args.command == "run":
            return compact_run(args.experiment)
        if args.command == "analyze":
            return compact_analyze(
                args.experiment,
                args.attempt,
                scientific_review_authorized=args.scientific_review_authorized,
            )
        if args.command == "plot":
            return compact_plot(args.experiment, args.attempt)
        if args.command == "package":
            return compact_package(args.experiment, args.attempt, include_plots=args.include_plots)
        if args.command == "inspect":
            return compact_inspect(args.experiment, args.attempt)
        raise ConfigError(f"unknown command: {args.command}")
    except (ConfigError, RawTraceError, OSError, RuntimeError, subprocess.SubprocessError) as exc:
        sys.stderr.write(f"bvm-exp error: {exc}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
