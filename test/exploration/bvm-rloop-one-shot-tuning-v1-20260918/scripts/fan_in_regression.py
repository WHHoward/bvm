#!/usr/bin/env python3
"""Run and mechanically compare the registered ARRAY_SIZE=4 regression."""

from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

SERIES = Path(__file__).resolve().parents[1]
REPO = next(path for path in (SERIES, *SERIES.parents) if (path / ".git").exists())
sys.path.insert(0, str(SERIES / "scripts"))
import try_candidate as platform  # noqa: E402

REFERENCE_CASE = SERIES / "runs" / "U136_QB_BJ1_screen_qb_bj1_area_0p75" / "config_snapshot.env"
REFERENCE_ROOT = SERIES / "runs" / "U136_QB_BJ1_screen_qb_bj1_area_0p75"
REGRESSION_ROOT = SERIES / "batches" / "ARRAY_SIZE_PLATFORM_REGRESSION"
MASKS = ("0000", "0001", "0011")
SIGNALS = (
    "V(COMMON_SL)", "I(B_JSL8)", "V(B_JSL8)",
    "V(QBIN)", "I(LIN|XBQ1)", "V(LIN|XBQ1)",
    "I(L1|XBQ1)", "V(L1|XBQ1)", "P(BJ1|XBQ1)", "P(BJ2|XBQ1)",
    "I(R_TERM)", "V(R_TERM)",
)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_raw(path: Path) -> tuple[list[str], list[list[float]]]:
    with path.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.reader(stream)
        headers = next(reader)
        return headers, [[float(value) for value in row] for row in reader if row]


def compare(old: Path, new: Path) -> dict[str, Any]:
    old_headers, old_rows = load_raw(old)
    new_headers, new_rows = load_raw(new)
    result: dict[str, Any] = {
        "old_raw": platform.repo_rel(old),
        "new_raw": platform.repo_rel(new),
        "old_sha256": platform.sha256(old),
        "new_sha256": platform.sha256(new),
        "raw_hash_equal": platform.sha256(old) == platform.sha256(new),
        "header_equal": old_headers == new_headers,
        "sample_count_equal": len(old_rows) == len(new_rows),
        "signals": {},
    }
    if old_rows and new_rows:
        time_diffs = [abs(left[0] - right[0]) for left, right in zip(old_rows, new_rows)]
        result["time_grid_max_abs_s"] = max(time_diffs) if time_diffs else None
    for signal in SIGNALS:
        item: dict[str, Any] = {"present_in_both": signal in old_headers and signal in new_headers}
        if item["present_in_both"] and len(old_rows) == len(new_rows):
            oi, ni = old_headers.index(signal), new_headers.index(signal)
            diffs = [left[oi] - right[ni] for left, right in zip(old_rows, new_rows)]
            item.update({"max_abs": max((abs(value) for value in diffs), default=0.0), "rms": (sum(value * value for value in diffs) / len(diffs)) ** 0.5 if diffs else 0.0})
        result["signals"][signal] = item
    result["status"] = "PASS" if result["raw_hash_equal"] and result["header_equal"] and result["sample_count_equal"] else "REVIEW_REQUIRED"
    return result


def main() -> int:
    if not REFERENCE_CASE.is_file():
        raise RuntimeError(f"reference config missing: {REFERENCE_CASE}")
    if not (REGRESSION_ROOT / "PREFLIGHT.md").is_file():
        raise RuntimeError(f"preflight missing: {REGRESSION_ROOT / 'PREFLIGHT.md'}")
    values = platform.load_env(REFERENCE_CASE)
    values.update({
        "NAME": "ARRAY_SIZE_4_reference_regression",
        "MODE": "closed",
        "ARRAY_SIZE": "4",
        "MASKS": ",".join(MASKS),
        "SWEEP_ENABLED": "no",
        "SWEEP_KEY": "NONE",
        "SWEEP_VALUES": "",
        "SWEEP_REUSE_EXISTING": "yes",
    })
    before = {path.name for path in (SERIES / "runs").iterdir() if path.is_dir()}
    with tempfile.NamedTemporaryFile(prefix="array4_regression_", suffix=".env", dir="/tmp", mode="w", encoding="utf-8", delete=False) as handle:
        config_path = Path(handle.name)
        handle.write("\n".join(f"{key}={value}" for key, value in values.items()) + "\n")
    try:
        completed = subprocess.run([sys.executable, str(SERIES / "scripts" / "try_candidate.py"), "--config", str(config_path)], cwd=REPO, capture_output=True, text=True, check=False)
    finally:
        config_path.unlink(missing_ok=True)
    (REGRESSION_ROOT / "regression_runner.stdout").write_text(completed.stdout, encoding="utf-8")
    (REGRESSION_ROOT / "regression_runner.stderr").write_text(completed.stderr, encoding="utf-8")
    created = sorted({path.name for path in (SERIES / "runs").iterdir() if path.is_dir()} - before)
    if completed.returncode != 0 or len(created) != 1:
        raise RuntimeError(f"ARRAY_SIZE=4 regression runner failed: exit={completed.returncode}, created={created}, stderr={completed.stderr[-2000:]}")
    case_id = created[0]
    case_root = SERIES / "runs" / case_id
    comparisons = []
    for mask in MASKS:
        run_id = f"CLOSED_N{mask.count('1')}_{mask}"
        comparisons.append({"mask": mask, "run_id": run_id, **compare(REFERENCE_ROOT / "cases" / run_id / "raw.csv", case_root / "cases" / run_id / "raw.csv")})
    output = {"schema": "bvm-rloop-array-size-4-regression-v1", "status": "PASS" if all(item["status"] == "PASS" for item in comparisons) else "REVIEW_REQUIRED", "reference_case": REFERENCE_ROOT.name, "candidate_case": case_id, "array_size": 4, "masks": list(MASKS), "comparisons": comparisons, "scientific_interpretation_performed": False, "automatic_follow_up": False}
    write_json(REGRESSION_ROOT / "REGRESSION_COMPARISON.json", output)
    write_json(REGRESSION_ROOT / "REGRESSION_QA.json", {"schema": "bvm-rloop-array-size-regression-qa-v1", "status": output["status"], "physical_solve_count": 3, "case_id": case_id, "raw_immutable": True, "scientific_interpretation_performed": False})
    print(json.dumps({"status": output["status"], "case_id": case_id, "physical_solve_count": 3, "masks": list(MASKS)}, ensure_ascii=False, indent=2))
    return 0 if output["status"] == "PASS" else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
