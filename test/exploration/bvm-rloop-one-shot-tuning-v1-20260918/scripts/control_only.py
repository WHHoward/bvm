#!/usr/bin/env python3
"""Render or execute the isolated CONTROL_ONLY receiver fixture."""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any

SERIES = Path(__file__).resolve().parents[1]
REPO = next(path for path in (SERIES, *SERIES.parents) if (path / ".git").exists())
sys.path.insert(0, str(SERIES / "scripts"))
import analyze as engine  # noqa: E402
import fan_in  # noqa: E402
import run_candidate as legacy  # noqa: E402
import try_candidate as platform  # noqa: E402

USER_CONFIG = SERIES / "USER_CASE.env"
REFERENCE_CONFIG = SERIES / "config" / "canonical_reference.env"


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def normalize_points(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    result: list[tuple[float, float]] = []
    for point in sorted(points, key=lambda item: item[0]):
        if result and abs(result[-1][0] - point[0]) < 1e-12 and abs(result[-1][1] - point[1]) < 1e-30:
            continue
        result.append(point)
    return result


def stage_points(params: dict[str, Any], start_key: str, end_key: str, amp_key: str, rise_key: str, fall_key: str) -> list[tuple[float, float]]:
    start = platform.time_ps(params[start_key], start_key)
    end = platform.time_ps(params[end_key], end_key)
    rise = platform.time_ps(params[rise_key], rise_key)
    fall = platform.time_ps(params[fall_key], fall_key)
    amp = platform.parse_number(params[amp_key], amp_key)
    return [(start, 0.0), (start + rise, amp), (end - fall, amp), (end, 0.0)]


def effective_parameters(config_path: Path) -> tuple[dict[str, Any], dict[str, str], dict[str, str]]:
    raw = platform.load_env(config_path)
    array_size = fan_in.parse_array_size(raw.get("ARRAY_SIZE", "4"))
    control_stop = raw.get("CONTROL_ONLY_STOP")
    if not control_stop:
        raise RuntimeError("CONTROL_ONLY requires CONTROL_ONLY_STOP in USER_CASE.env")
    control_stop_ps = platform.time_ps(control_stop, "CONTROL_ONLY_STOP")
    control_end_ps = platform.time_ps(raw["CONTROL_READ_END"], "CONTROL_READ_END")
    if control_stop_ps <= control_end_ps:
        raise RuntimeError("CONTROL_ONLY_STOP must be later than CONTROL_READ_END")
    values = dict(raw)
    values.update({"MODE": "closed", "ARRAY_SIZE": str(array_size), "MASKS": "0" * array_size, "SWEEP_ENABLED": "no", "SWEEP_KEY": "NONE", "SWEEP_VALUES": ""})
    params = platform.validate(values, platform.load_env(REFERENCE_CONFIG))
    params.update({
        "ARRAY_SIZE": array_size,
        "MASKS": ["0" * array_size],
        "BIT_ORDER": fan_in.bit_order(array_size),
        "CONTROL_ONLY": True,
        "CONTROL_ONLY_STOP": control_stop,
        "STOP": control_stop,
        "RECOVERY_END": control_stop,
        "TAIL_START": control_stop,
        "time_ps": {**params["time_ps"], "STOP": control_stop_ps, "RECOVERY_END": control_stop_ps, "TAIL_START": control_stop_ps},
        "windows": {
            "idle_0_50": [params["time_ps"]["IDLE_START"], params["time_ps"]["IDLE_END"]],
            "write0": [params["time_ps"]["WRITE0_START"], params["time_ps"]["WRITE0_END"]],
            "settle_before_control": [params["time_ps"]["WRITE0_END"], params["time_ps"]["CONTROL_READ_START"]],
            "control_read": [params["time_ps"]["CONTROL_READ_START"], params["time_ps"]["CONTROL_READ_END"]],
            "control_observation": [params["time_ps"]["CONTROL_READ_START"], control_stop_ps],
            "whole": [params["time_ps"]["IDLE_START"], control_stop_ps],
        },
    })
    effective = dict(raw)
    effective.update({"FIXTURE_MODE": "CONTROL_ONLY", "MODE": "closed", "ARRAY_SIZE": str(array_size), "MASKS": "0" * array_size, "STOP": control_stop, "RECOVERY_END": control_stop, "TAIL_START": control_stop, "CONTROL_ONLY_STOP": control_stop, "SWEEP_ENABLED": "no", "SWEEP_KEY": "NONE", "SWEEP_VALUES": ""})
    params["config_changes"] = platform.change_rows(effective, platform.load_env(REFERENCE_CONFIG))
    return params, raw, effective


def effective_config_text(effective: dict[str, str], params: dict[str, Any], source_config: Path) -> str:
    lines = [
        "# Effective CONTROL_ONLY configuration; deck/stimulus/provenance use this snapshot.",
        "FIXTURE_MODE=CONTROL_ONLY",
        f"SOURCE_CONFIG_PATH={platform.repo_rel(source_config)}",
        f"SOURCE_CONFIG_SHA256={platform.sha256(source_config)}",
        f"EFFECTIVE_ARRAY_SIZE={params['ARRAY_SIZE']}",
        f"EFFECTIVE_BIT_ORDER={params['BIT_ORDER']}",
        f"EFFECTIVE_STOP={params['STOP']}",
    ]
    lines.extend(f"{key}={effective[key]}" for key in sorted(effective) if key != "FIXTURE_MODE")
    return "\n".join(lines) + "\n"


def control_stimulus(params: dict[str, Any]) -> str:
    array_size = int(params["ARRAY_SIZE"])
    stop_ps = platform.time_ps(params["CONTROL_ONLY_STOP"], "CONTROL_ONLY_STOP")
    lines = [
        f"* CONTROL_ONLY; ARRAY_SIZE={array_size}; {params['BIT_ORDER']}",
        f"* WRITE0 [{params['WRITE0_START']},{params['WRITE0_END']}); CONTROL [{params['CONTROL_READ_START']},{params['CONTROL_READ_END']}); zero until {params['CONTROL_ONLY_STOP']}.",
        "* NO WRITE1 and NO FINAL READ; all points derive from USER_CASE stimulus parameters.",
    ]
    for index in range(1, array_size + 1):
        for signal in ("WL", "BL", "SE"):
            points = [(platform.time_ps(params["IDLE_START"], "IDLE_START"), 0.0)]
            points += stage_points(params, "WRITE0_START", "WRITE0_END", f"WRITE0_{signal}_AMP", f"WRITE0_{signal}_RISE", f"WRITE0_{signal}_FALL")
            points += stage_points(params, "CONTROL_READ_START", "CONTROL_READ_END", f"CONTROL_{signal}_AMP", f"CONTROL_{signal}_RISE", f"CONTROL_{signal}_FALL")
            values: list[str] = []
            for time_ps, current_a in normalize_points(points + [(stop_ps, 0.0)]):
                values.extend((platform.format_time(time_ps), platform.format_current(current_a)))
            lines.append(f"I_{signal}{index} 0 {signal}{index} pwl(" + " ".join(values) + ")")
    return "\n".join(lines) + "\n"


def render_validation(config_path: Path) -> dict[str, Any]:
    params, _raw, _effective = effective_parameters(config_path)
    array_size = params["ARRAY_SIZE"]
    stimulus_text = control_stimulus(params)
    inventory = fan_in.stimulus_source_inventory(stimulus_text, array_size)
    with tempfile.TemporaryDirectory(prefix="bvm_control_only_") as temp:
        root = Path(temp) / "case"
        root.mkdir()
        sources = platform.render_case_sources(root, params)
        run_dir = root / "cases" / ("CONTROL_ONLY_N0_" + "0" * array_size)
        run_dir.mkdir(parents=True)
        stimulus = run_dir / "stimulus.inc"
        stimulus.write_text(stimulus_text, encoding="utf-8")
        deck = legacy.render_deck("closed", params, sources, stimulus, run_dir)
    instances = [line.strip() for line in deck.splitlines() if re.match(r"^XBVM\d+\s", line.strip())]
    forbidden_times = [platform.format_time(platform.time_ps(params[key], key)) for key in ("WRITE1_START", "WRITE1_END", "FINAL_READ_START", "FINAL_READ_END")]
    forbidden = [token for token in forbidden_times if token in stimulus_text]
    return {
        "array_size": array_size,
        "mask": "0" * array_size,
        "effective_timing": {key: params["time_ps"][key] for key in ("WRITE0_START", "WRITE0_END", "CONTROL_READ_START", "CONTROL_READ_END", "STOP")},
        "bvm_instance_count": len(instances),
        "stimulus_source_inventory": inventory,
        "forbidden_write1_or_final_times": forbidden,
        "requested_signal_count": len(legacy.requested_signals("closed", params)),
        "deck_has_qb_jtl_terminal": all(token in deck for token in ("XBQ1 QBIN QBOUT BQ", "XJTL1_6 JTL5_OUT JTL6_OUT jtl", "R_TERM JTL6_OUT 0 10")),
        "status": "PASS" if len(instances) == array_size and inventory["status"] == "PASS" and not forbidden else "FAIL",
        "array_size_recorded": params["ARRAY_SIZE"],
        "bit_order": params["BIT_ORDER"],
    }


def run_case(config_path: Path) -> int:
    params, _raw_values, effective = effective_parameters(config_path)
    case_id = f"{platform.next_case_id()}_CONTROL_ONLY_ARRAY{params['ARRAY_SIZE']}"
    case_root = SERIES / "runs" / case_id
    if case_root.exists():
        raise RuntimeError(f"refusing to overwrite {case_root}")
    parent = legacy.git_snapshot()
    case_root.mkdir(parents=True)
    effective_snapshot = case_root / "config_snapshot.env"
    effective_snapshot.write_text(effective_config_text(effective, params, config_path), encoding="utf-8")
    source_snapshot = case_root / "user_case_input.env"
    source_snapshot.write_text(config_path.read_text(encoding="utf-8"), encoding="utf-8")
    (case_root / "stimulus_snapshot.env").write_text(control_stimulus(params), encoding="utf-8")
    sources = platform.render_case_sources(case_root, params)
    records = [legacy.file_record(role, path) for role, path in sources.items()]
    records.extend([
        legacy.file_record("EFFECTIVE_CONFIG", effective_snapshot),
        legacy.file_record("SOURCE_CONFIG", source_snapshot),
        legacy.file_record("REFERENCE_CONFIG", REFERENCE_CONFIG),
        legacy.file_record("CANONICAL_BVM_REFERENCE", platform.CANONICAL_BVM),
    ])
    write_json(case_root / "source_manifest.json", {"schema": "bvm-rloop-control-only-source-manifest-v2", "parent": parent, "fixture_mode": "CONTROL_ONLY", "array_size": params["ARRAY_SIZE"], "bit_order": params["BIT_ORDER"], "effective_timing": {key: params["time_ps"][key] for key in ("WRITE0_START", "WRITE0_END", "CONTROL_READ_START", "CONTROL_READ_END", "STOP")}, "sources": records, "raw_not_copied_from_history": True})
    run_id = f"CONTROL_ONLY_N0_{'0' * params['ARRAY_SIZE']}"
    run_dir = case_root / "cases" / run_id
    run_dir.mkdir(parents=True)
    stimulus = run_dir / "stimulus.inc"
    stimulus.write_text(control_stimulus(params), encoding="utf-8")
    deck = run_dir / "actual_deck.cir"
    deck.write_text(legacy.render_deck("closed", params, sources, stimulus, run_dir), encoding="utf-8")
    (run_dir / "deck.cir").write_text(deck.read_text(encoding="utf-8"), encoding="utf-8")
    raw = run_dir / "raw.csv"
    command = [str(REPO / "build" / "josim-cli"), "-a", "1", "-o", str(raw), str(deck)]
    started = now(); clock = time.monotonic()
    completed = subprocess.run(command, cwd=run_dir, capture_output=True, text=True, check=False)
    finished = now(); runtime = time.monotonic() - clock
    (run_dir / "stdout.txt").write_text(completed.stdout, encoding="utf-8")
    (run_dir / "stderr.txt").write_text(completed.stderr, encoding="utf-8")
    (run_dir / "run.log").write_text(f"fixture=CONTROL_ONLY\narray_size={params['ARRAY_SIZE']}\ncommand={shlex.join(command)}\nstarted_at={started}\nfinished_at={finished}\nexit_code={completed.returncode}\nruntime_seconds={runtime:.6f}\n", encoding="utf-8")
    if completed.returncode != 0 or not raw.is_file():
        raise RuntimeError(f"CONTROL_ONLY solver failed; artifacts preserved at {run_dir}")
    headers = legacy.read_header(raw)
    manifest = legacy.write_signal_manifest(run_dir, "closed", params, headers)
    raw_headers, raw_rows = engine.load_raw(raw)
    raw_qa = engine.raw_qa({"parameters": params, "raw": {"sha256": legacy.sha256(raw)}}, raw, raw_headers, raw_rows)
    source_qa = fan_in.stimulus_source_inventory(stimulus.read_text(encoding="utf-8"), params["ARRAY_SIZE"])
    metadata = {"run_id": run_id, "mode": "closed", "array_size": params["ARRAY_SIZE"], "mask": "0" * params["ARRAY_SIZE"], "fixture_mode": "CONTROL_ONLY", "effective_timing": {key: params["time_ps"][key] for key in ("WRITE0_START", "WRITE0_END", "CONTROL_READ_START", "CONTROL_READ_END", "STOP")}, "parameters": params, "command": command, "execution_status": "RUN_PASS", "raw": {"path": legacy.repo_rel(raw), "sha256": legacy.sha256(raw)}, "deck": {"path": legacy.repo_rel(deck), "sha256": legacy.sha256(deck)}, "stimulus": {"path": legacy.repo_rel(stimulus), "sha256": legacy.sha256(stimulus)}, "signal_manifest": manifest, "stimulus_qa": source_qa, "raw_qa": raw_qa}
    write_json(run_dir / "metadata.json", metadata)
    write_json(case_root / "qa" / "raw_qa.json", {"schema": "bvm-rloop-control-only-raw-qa-v2", "status": "PASS" if raw_qa["status"] == "PASS" and source_qa["status"] == "PASS" else "FAIL", "rows": [raw_qa], "stimulus_qa": source_qa, "raw_immutable": True})
    write_json(case_root / "case_manifest.json", {"schema": "bvm-rloop-control-only-case-v3", "case_id": case_id, "array_size": params["ARRAY_SIZE"], "bit_order": params["BIT_ORDER"], "fixture_mode": "CONTROL_ONLY", "parameters": params, "effective_timing": metadata["effective_timing"], "source_manifest": {"path": legacy.repo_rel(case_root / "source_manifest.json"), "sha256": legacy.sha256(case_root / "source_manifest.json")}, "run_order": [run_id], "physical_solve_count": 1, "scientific_interpretation_performed": False, "automatic_follow_up": False})
    print(json.dumps({"status": "CONTROL_ONLY_CASE_COMPLETE", "case_id": case_id, "array_size": params["ARRAY_SIZE"], "physical_solve_count": 1, "scientific_interpretation": "NOT_PERFORMED"}, ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(USER_CONFIG))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()
    if args.dry_run == args.run:
        raise RuntimeError("choose exactly one of --dry-run or --run")
    config = Path(args.config).resolve()
    if args.dry_run:
        result = render_validation(config)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["status"] == "PASS" else 2
    return run_case(config)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
