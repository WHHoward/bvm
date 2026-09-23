#!/usr/bin/env python3
"""Single-parameter sweep adapter; every point reuses run_case.py."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

from common import CIRCUIT_KEYS, ROOT, load_env, parse_overrides, resolve_params

TIME_SWEEP_KEYS = {
    "READ_START_PS", "READ_PERIOD_PS", "READ_WIDTH_PS", "READ_RISE_PS", "READ_FALL_PS",
    "RECOVERY_TAIL_PS", "WRITE_WIDTH_PS", "WRITE_RISE_PS", "WRITE_FALL_PS",
    "CONTROL_WIDTH_PS", "CONTROL_RISE_PS", "CONTROL_FALL_PS", "STATE_INTERVAL_PS",
    "RESET_TO_WRITE_DELAY_PS", "WRITE_TO_READ_DELAY_PS", "READ_TO_NEXT_RESET_DELAY_PS",
    "TAIL_MARGIN_MIN_PS", "BJ2_CANDIDATE_THRESHOLD_UV", "BJ2_CANDIDATE_GAP_PS",
    "TERMINAL_CANDIDATE_THRESHOLD_UV", "TERMINAL_CANDIDATE_GAP_PS", "LATENCY_MIN_PS", "LATENCY_MAX_PS",
}
SWEEP_KEYS = CIRCUIT_KEYS + tuple(sorted(TIME_SWEEP_KEYS)) + (
    "READ_AMP_UA", "WRITE_AMP_UA", "CONTROL_WL_AMP_UA", "CONTROL_BL_AMP_UA", "CONTROL_SE_AMP_UA")


def slug(value: str) -> str:
    result = re.sub(r"[^A-Za-z0-9]+", "_", value.strip()).strip("_")
    return result or "value"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a one-key series via immutable run_case instances")
    parser.add_argument("--key")
    parser.add_argument("--values", help="comma-separated values")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    user = load_env(ROOT / "USER_CASE.env")
    if not args.dry_run and user.get("EXECUTION_SCOPE", "REGRESSION_MATRIX") != "MANUAL":
        raise ValueError("physical sweeps are disabled in REGRESSION_MATRIX scope; set EXECUTION_SCOPE=MANUAL only for a separately authorized future sweep")
    key = args.key or user.get("SWEEP_KEY")
    raw_values = args.values if args.values is not None else user.get("SWEEP_VALUES", "")
    if not args.dry_run and not (args.key and args.values is not None) and user.get("SWEEP_ENABLED", "no").lower() != "yes":
        raise ValueError("set SWEEP_ENABLED=yes or pass both --key and --values to explicitly request a sweep")
    if key not in SWEEP_KEYS:
        raise ValueError(f"SWEEP_KEY must be a numeric circuit/stimulus parameter, got {key!r}")
    values = [item.strip() for item in raw_values.split(",") if item.strip()]
    if len(values) < 2 or len(values) != len(set(values)):
        raise ValueError("sweep requires at least two unique comma-separated values")
    base = {k: v for k, v in user.items() if v.upper() != "AUTO"}
    plans = []
    for value in values:
        name = f"{user.get('NAME','SWEEP')}_{key.lower()}_{slug(value)}"
        overrides = {**base, key: value, "NAME": name}
        params, plan = resolve_params(overrides)
        plans.append({"name": name, "value": value, "params": params, "stop_ps": plan["stop_ps"],
                      "read_starts_ps": plan["read_starts_ps"]})
    if args.dry_run:
        for point in plans:
            print(f"{key}={point['value']} -> {point['name']} (STOP={point['stop_ps']:g} ps; no solve)")
        return 0
    for point in plans:
        command = [sys.executable, str(ROOT / "scripts" / "run_case.py"),
                   "--set", f"{key}={point['value']}", "--set", f"NAME={point['name']}"]
        completed = subprocess.run(command, cwd=ROOT.parents[2], check=False)
        if completed.returncode:
            print("Stopped on the first failed sweep point; no retry or later point.", file=sys.stderr)
            return completed.returncode
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
