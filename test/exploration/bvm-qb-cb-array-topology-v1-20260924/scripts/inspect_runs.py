#!/usr/bin/env python3
"""Show configuration and immutable-run artifact status without interpretation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from config import USER_CASE_KEYS, load_env, validate_user_case

SERIES = Path(__file__).resolve().parents[1]


def inspect_platform(run_id: str | None = None) -> dict[str, Any]:
    config = validate_user_case(load_env(SERIES / "USER_CASE.env", USER_CASE_KEYS))
    runs_root = SERIES / "runs"
    paths = sorted(path for path in runs_root.glob("A*_T*_M*") if path.is_dir()) if runs_root.exists() else []
    if run_id:
        paths = [path for path in paths if path.name == run_id]
        if not paths:
            raise FileNotFoundError(f"run ID does not exist: {run_id}")
    runs = []
    for path in paths:
        result_path = path / "result.json"
        result = json.loads(result_path.read_text(encoding="utf-8")) if result_path.is_file() else {}
        runs.append({
            "run_id": path.name,
            "result_status": result.get("status", "INCOMPLETE_OR_FAILED_ATTEMPT"),
            "artifact_status": result.get("artifact_status", "UNKNOWN"),
            "physical_solve_count": result.get("physical_solve_count", 0),
            "scientific_interpretation_performed": result.get("scientific_interpretation_performed", False),
        })
    return {
        "schema": "bvm-qb-cb-array-inspect-v1",
        "array_size": config["ARRAY_SIZE"],
        "configured_masks": config["MASKS"],
        "topology": {key: config[key] for key in ("QB_CB", "SJTL_COUNT", "POST_SJTL_CB")},
        "runs": runs,
        "scientific_interpretation_performed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect array config and run artifact status")
    parser.add_argument("--run-id")
    args = parser.parse_args()
    try:
        print(json.dumps(inspect_platform(args.run_id), ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
