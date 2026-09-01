#!/usr/bin/env python3
"""Minimal config-driven JoSIM Quick workflow.

The command intentionally has a small surface:

    python3 scripts/bvm-exp.py quick path/to/experiment.yaml

Cases are explicit.  A normal Quick run invokes only the registered decks,
never overwrites an existing run directory, performs shared raw QA/metrics,
creates a compact classic ``josim-plot2.py`` view, and stops at
``AWAITING_USER_REVIEW``.  A ``tooling_smoke_test_only`` config may consume
existing raw CSVs without invoking JoSIM; it cannot create new science data.
"""

from __future__ import annotations

import argparse
import json
import math
import re
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
from bvmtools.raw import DuplicateColumnError, RawTraceError, read_csv
from bvmtools.sfq import StrictLocalEventSpec, strict_event_summary
from bvmtools.waveform import waveform_metrics


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
        meaning = "共享 raw reader、strict-event 实现、结果摘要和经典 compact 后端已用既有 raw 做工具链重放；这些输出不产生新的 physics conclusion。"
        not_prove = [
            "不证明任何新的电路行为、SFQ delivery、下游接收或 system Gate。",
            "不替代历史 raw、既有报告或 METRIC_SPEC_V2 的科学权威边界。",
            "未运行 JoSIM，也未改变历史输入或 raw。",
        ]
    else:
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
        f"- Baseline: `{baseline['deck']}`",
        f"- Candidate: `{candidate['deck']}`",
        f"- Changed variables: {', '.join(str(item) for item in changed)}",
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
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_quick(config_path: str | Path) -> int:
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Config-driven JoSIM Quick workflow")
    subparsers = parser.add_subparsers(dest="command", required=True)
    quick = subparsers.add_parser("quick", help="run explicit Quick cases and stop for user review")
    quick.add_argument("experiment", help="path to experiment.yaml")
    args = parser.parse_args(argv)
    try:
        return run_quick(args.experiment)
    except (ConfigError, RawTraceError, OSError, RuntimeError, subprocess.SubprocessError) as exc:
        sys.stderr.write(f"bvm-exp error: {exc}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
