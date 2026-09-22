#!/usr/bin/env python3
"""Render or execute the isolated CONTROL_ONLY receiver fixture.

The fixture uses the normal BVM/QB/JTL topology and parameters but ends all
external sources after CONTROL.  It is intentionally separate from normal
protocol terminal metrics so WRITE1 cannot contaminate Control causality.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import shlex
import shutil
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
import fan_in  # noqa: E402
import run_candidate as legacy  # noqa: E402
import try_candidate as platform  # noqa: E402

USER_CONFIG = SERIES / "USER_CASE.env"
REFERENCE_CONFIG = SERIES / "config" / "canonical_reference.env"
CONTROL_STOP = "120p"


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def control_stimulus(array_size: int) -> str:
    lines = [
        f"* CONTROL_ONLY; ARRAY_SIZE={array_size}; {fan_in.bit_order(array_size)}",
        "* IDLE [0,50); WRITE0 [50,61); settle [61,70); CONTROL [70,81); zero [81,120).",
        "* NO WRITE1 and NO FINAL READ.",
    ]
    points = ((0, 0), (50, 0), (51, -100), (60, -100), (61, 0), (70, 0), (71, 100), (80, 100), (81, 0), (120, 0))
    for index in range(1, array_size + 1):
        for signal in ("WL", "BL", "SE"):
            values = []
            for time_ps, current_ua in points:
                if signal == "SE":
                    current_ua = 0 if time_ps < 70 or time_ps >= 81 else 100
                elif signal == "BL":
                    current_ua = -100 if 51 <= time_ps < 61 else 0
                else:
                    current_ua = -100 if 51 <= time_ps < 61 else (100 if 71 <= time_ps < 81 else 0)
                values.extend(("0" if time_ps == 0 else f"{time_ps:g}p", "0" if current_ua == 0 else f"{current_ua:+g}u"))
            lines.append(f"I_{signal}{index} 0 {signal}{index} pwl(" + " ".join(values) + ")")
    return "\n".join(lines) + "\n"


def make_params(config_path: Path) -> tuple[dict[str, Any], dict[str, str]]:
    values = platform.load_env(config_path)
    array_size = fan_in.parse_array_size(values.get("ARRAY_SIZE", "4"))
    values.update({"MODE": "closed", "ARRAY_SIZE": str(array_size), "MASKS": "0" * array_size, "STOP": "200p", "SWEEP_ENABLED": "no", "SWEEP_KEY": "NONE", "SWEEP_VALUES": ""})
    params = platform.validate(values, platform.load_env(REFERENCE_CONFIG))
    params.update({
        "ARRAY_SIZE": array_size,
        "MASKS": ["0" * array_size],
        "STOP": CONTROL_STOP,
        "RECOVERY_END": CONTROL_STOP,
        "TAIL_START": "81p",
        "BIT_ORDER": fan_in.bit_order(array_size),
        "CONTROL_ONLY": True,
        "windows": {
            "idle_0_50": [0.0, 50.0],
            "write0_50_61": [50.0, 61.0],
            "settle0_61_70": [61.0, 70.0],
            "control_70_81": [70.0, 81.0],
            "control_observation_70_120": [70.0, 120.0],
            "whole_0_120": [0.0, 120.0],
        },
    })
    return params, values


def render_validation(config_path: Path) -> dict[str, Any]:
    params, values = make_params(config_path)
    array_size = params["ARRAY_SIZE"]
    with tempfile.TemporaryDirectory(prefix="bvm_control_only_") as temp:
        root = Path(temp) / "case"
        root.mkdir()
        sources = platform.render_case_sources(root, params)
        run_dir = root / "cases" / ("CONTROL_ONLY_N0_" + "0" * array_size)
        run_dir.mkdir(parents=True)
        stimulus = run_dir / "stimulus.inc"
        stimulus_text = control_stimulus(array_size)
        stimulus.write_text(stimulus_text, encoding="utf-8")
        deck = legacy.render_deck("closed", params, sources, stimulus, run_dir)
    instances = [line.strip() for line in deck.splitlines() if re.match(r"^XBVM\d+\s", line.strip())]
    stimulus_lines = [line for line in stimulus_text.splitlines() if line.startswith("I_")]
    forbidden = [token for token in ("91p", "100p", "111p") if token in stimulus_text]
    expected_signals = legacy.requested_signals("closed", params)
    return {
        "array_size": array_size,
        "mask": "0" * array_size,
        "bvm_instance_count": len(instances),
        "stimulus_source_group_count": len(stimulus_lines),
        "expected_stimulus_source_group_count": 3 * array_size,
        "forbidden_write1_or_final_markers": forbidden,
        "requested_signal_count": len(expected_signals),
        "deck_has_qb_jtl_terminal": all(token in deck for token in ("XBQ1 QBIN QBOUT BQ", "XJTL1_6 JTL5_OUT JTL6_OUT jtl", "R_TERM JTL6_OUT 0 10")),
        "status": "PASS" if len(instances) == array_size and len(stimulus_lines) == 3 * array_size and not forbidden else "FAIL",
        "array_size_recorded": params["ARRAY_SIZE"],
        "bit_order": params["BIT_ORDER"],
    }


def run_case(config_path: Path) -> int:
    params, values = make_params(config_path)
    case_id = f"{platform.next_case_id()}_CONTROL_ONLY_ARRAY{params['ARRAY_SIZE']}"
    case_root = SERIES / "runs" / case_id
    if case_root.exists():
        raise RuntimeError(f"refusing to overwrite {case_root}")
    parent = legacy.git_snapshot()
    case_root.mkdir(parents=True)
    (case_root / "config_snapshot.env").write_text(config_path.read_text(encoding="utf-8"), encoding="utf-8")
    sources = platform.render_case_sources(case_root, params)
    run_id = f"CONTROL_ONLY_N0_{'0' * params['ARRAY_SIZE']}"
    run_dir = case_root / "cases" / run_id
    run_dir.mkdir(parents=True)
    stimulus = run_dir / "stimulus.inc"
    stimulus.write_text(control_stimulus(params["ARRAY_SIZE"]), encoding="utf-8")
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
    (run_dir / "run.log").write_text(f"fixture=CONTROL_ONLY\ncommand={shlex.join(command)}\nstarted_at={started}\nfinished_at={finished}\nexit_code={completed.returncode}\nruntime_seconds={runtime:.6f}\n", encoding="utf-8")
    if completed.returncode != 0 or not raw.is_file():
        raise RuntimeError(f"CONTROL_ONLY solver failed; artifacts preserved at {run_dir}")
    headers = legacy.read_header(raw)
    manifest = legacy.write_signal_manifest(run_dir, "closed", params, headers)
    metadata = {"run_id": run_id, "mode": "closed", "array_size": params["ARRAY_SIZE"], "mask": "0" * params["ARRAY_SIZE"], "fixture_mode": "CONTROL_ONLY", "parameters": params, "command": command, "execution_status": "RUN_PASS", "raw": {"path": legacy.repo_rel(raw), "sha256": legacy.sha256(raw)}, "deck": {"path": legacy.repo_rel(deck), "sha256": legacy.sha256(deck)}, "stimulus": {"path": legacy.repo_rel(stimulus), "sha256": legacy.sha256(stimulus)}, "signal_manifest": manifest}
    write_json(run_dir / "metadata.json", metadata)
    case_manifest = {"schema": "bvm-rloop-control-only-case-v2", "case_id": case_id, "array_size": params["ARRAY_SIZE"], "fixture_mode": "CONTROL_ONLY", "parameters": params, "parent": parent, "run_order": [run_id], "physical_solve_count": 1, "scientific_interpretation_performed": False, "automatic_follow_up": False}
    write_json(case_root / "case_manifest.json", case_manifest)
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
