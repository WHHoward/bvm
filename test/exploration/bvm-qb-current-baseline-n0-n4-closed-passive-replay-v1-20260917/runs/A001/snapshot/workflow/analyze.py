#!/usr/bin/env python3
"""Compute exhaustive per-run mechanical tables and registered QA only."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

SERIES = Path(__file__).resolve().parents[1]
REPO = next((path for path in (SERIES, *SERIES.parents) if (path / ".git").exists()), SERIES)
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_cases import CASE_ORDER, FAMILIES, MASKS, WINDOWS, WINDOW_LABELS, probe_lines, read_raw_columns  # noqa: E402

PHASE_SIGNALS = {"P(B_JM1|", "P(B_JM2|", "P(B_JS1|", "P(B_JS2|", "P(BJS|", "P(BJ1|", "P(BJ2|", "P(B01|", "P(B02|"}


def now() -> str:
    from datetime import datetime
    return datetime.now().astimezone().isoformat(timespec="seconds")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"expected JSON object: {path}")
    return value


def attempt_dir(value: str) -> Path:
    path = SERIES / "runs" / value
    if not path.is_dir():
        raise RuntimeError(f"attempt does not exist: {path}")
    return path


def case_id(family: str, mask: str) -> str:
    return f"{family}_N{int(mask, 2)}_{mask}"


def raw_path(attempt: Path, run_id: str) -> Path:
    return attempt / "cases" / run_id / "raw.csv"


def time_ps(value: str) -> float:
    return float(value) * 1.0e12


def load_case(path: Path) -> dict[str, Any]:
    headers, rows = read_raw_columns(path)
    time_index = headers.index("time") if "time" in headers else 0
    times_s = [float(row[time_index]) for row in rows]
    return {"path": path, "headers": headers, "rows": rows, "time_index": time_index, "times_s": times_s, "times_ps": [value * 1.0e12 for value in times_s], "raw_sha256": sha256(path)}


def phase_signal(signal: str) -> bool:
    return signal.startswith("P(")


def unwrap(values: list[float]) -> list[float]:
    if not values:
        return []
    result = [values[0]]
    for value in values[1:]:
        delta = value - values[len(result) - 1]
        while delta > math.pi:
            delta -= 2.0 * math.pi
        while delta < -math.pi:
            delta += 2.0 * math.pi
        result.append(result[-1] + delta)
    return result


def integrate(times: list[float], values: list[float]) -> float:
    return sum(0.5 * (values[index] + values[index + 1]) * (times[index + 1] - times[index]) for index in range(len(values) - 1))


def signal_class(signal: str) -> tuple[str, str, str, str]:
    if signal.startswith("I(I_WL") or signal.startswith("I(I_BL") or signal.startswith("I(I_SE"):
        return "stimulus", signal[2:-1], "current", "A"
    if signal == "I(I_REPLAY)":
        return "replay_source", "top", "current", "A"
    if "|XBVM" in signal:
        instance = signal.split("|", 1)[1].rstrip(")")
        if any(f"{element}|" in signal for element in ("B_JM1", "B_JM2", "B_JS1", "B_JS2")):
            return "BVM", instance, signal[0], {"P": "rad", "V": "V", "I": "A"}[signal[0]]
        return "BVM", instance, signal[0], {"V": "V", "I": "A"}[signal[0]]
    if signal.startswith(("P(B_JSL", "V(B_JSL", "I(B_JSL")):
        return "JSL", "shared", signal[0], {"P": "rad", "V": "V", "I": "A"}[signal[0]]
    if signal.startswith("V(COMMON_SL"):
        return "COMMON_SL", "shared", "voltage", "V"
    if "|XBQ1" in signal or signal in {"V(QBIN)", "V(QBOUT)"}:
        return "QB", "XBQ1", signal[0] if signal[0] in "PVI" else "other", {"P": "rad", "V": "V", "I": "A"}.get(signal[0], "raw")
    if "|XJTL1_" in signal or signal.startswith("V(JTL"):
        instance = signal.split("|", 1)[1].rstrip(")") if "|" in signal else "top"
        return "JTL", instance, signal[0] if signal[0] in "PVI" else "voltage", {"P": "rad", "V": "V", "I": "A"}.get(signal[0], "V")
    if "R_TERM" in signal:
        return "terminal", "R_TERM", signal[0] if signal[0] in "VI" else "other", {"V": "V", "I": "A"}.get(signal[0], "raw")
    return "other", "top", "other", "raw"


def signal_values(case: dict[str, Any], signal: str) -> list[float]:
    index = case["headers"].index(signal)
    return [float(row[index]) for row in case["rows"] if len(row) > index and row[index] != ""]


def window_indices(case: dict[str, Any], window: tuple[int, int]) -> list[int]:
    return [index for index, value in enumerate(case["times_ps"]) if window[0] <= value < window[1]]


def window_metric(case: dict[str, Any], signal: str, window: tuple[int, int], label: str) -> dict[str, Any]:
    if signal not in case["headers"]:
        return {"status": "UNKNOWN", "signal": signal, "window": label, "window_start_ps": window[0], "window_end_ps": window[1]}
    index = case["headers"].index(signal)
    indices = [item for item in window_indices(case, window) if item < len(case["rows"]) and len(case["rows"][item]) > index]
    if not indices:
        return {"status": "UNKNOWN", "signal": signal, "window": label, "window_start_ps": window[0], "window_end_ps": window[1]}
    values = [float(case["rows"][item][index]) for item in indices]
    times = [case["times_s"][item] for item in indices]
    kind, instance, quantity, unit = signal_class(signal)
    minimum_position = min(range(len(values)), key=values.__getitem__)
    maximum_position = max(range(len(values)), key=values.__getitem__)
    result: dict[str, Any] = {"status": "DERIVED", "signal": signal, "window": label, "window_start_ps": window[0], "window_end_ps": window[1], "subsystem": kind, "instance": instance, "quantity": quantity, "unit": unit, "sample_count": len(values), "minimum": min(values), "maximum": max(values), "mean": sum(values) / len(values), "rms": math.sqrt(sum(value * value for value in values) / len(values)), "endpoint": values[-1], "time_of_min_ps": case["times_ps"][indices[minimum_position]], "time_of_max_ps": case["times_ps"][indices[maximum_position]], "actual_grid_trapezoid": True}
    if phase_signal(signal):
        raw = values
        unwrapped = unwrap(signal_values(case, signal))
        selected_unwrapped = [unwrapped[item] for item in indices]
        result.update({"raw_start_rad": raw[0], "raw_end_rad": raw[-1], "unwrapped_start_rad": selected_unwrapped[0], "unwrapped_end_rad": selected_unwrapped[-1], "net_unwrapped_delta_rad": selected_unwrapped[-1] - selected_unwrapped[0], "p2p_unwrapped_excursion_rad": max(selected_unwrapped) - min(selected_unwrapped), "navigation_turns": (selected_unwrapped[-1] - selected_unwrapped[0]) / (2.0 * math.pi), "signed_integral": None, "absolute_integral": None, "phase_semantics": "raw radians; unwrapped rad/(2*pi) navigation only; not an SFQ count"})
    else:
        result.update({"signed_integral": integrate(times, values), "absolute_integral": integrate(times, [abs(value) for value in values]), "phase_semantics": None})
    return result


def expected_signals(family: str) -> set[str]:
    result: set[str] = set()
    for line in probe_lines(family):
        result.update(re.findall(r"[PVI]\([^)]*\)", line))
    return result


def raw_qa(cases: dict[str, dict[str, Any]]) -> dict[str, Any]:
    checks: dict[str, Any] = {}
    failures: list[str] = []
    for run_id, case in cases.items():
        family = run_id.split("_", 1)[0]
        headers = case["headers"]
        numeric_errors: list[str] = []
        for column_index, name in enumerate(headers):
            if name == "time":
                continue
            for row_index, row in enumerate(case["rows"]):
                try:
                    value = float(row[column_index])
                    if not math.isfinite(value):
                        numeric_errors.append(f"{name}@{row_index}:nonfinite")
                except (ValueError, IndexError):
                    numeric_errors.append(f"{name}@{row_index}:non-numeric")
                    break
        missing = sorted(expected_signals(family) - set(headers))
        grid = {"sample_count": len(case["rows"]), "time_start_ps": case["times_ps"][0] if case["times_ps"] else None, "time_end_ps": case["times_ps"][-1] if case["times_ps"] else None, "strictly_increasing": all(right > left for left, right in zip(case["times_s"], case["times_s"][1:])), "expected_sample_count": 1999, "expected_end_ps": 199.9}
        passed = not numeric_errors and not missing and len(headers) == len(set(headers)) and grid["sample_count"] == 1999 and grid["time_start_ps"] == 0.0 and abs(grid["time_end_ps"] - 199.9) < 1.0e-9 and grid["strictly_increasing"]
        if not passed:
            failures.append(run_id)
        checks[run_id] = {"status": "PASS" if passed else "ARTIFACT_INVALID", "raw_path": str(case["path"].relative_to(SERIES)), "raw_sha256": case["raw_sha256"], "header_count": len(headers), "duplicate_headers": sorted(name for name, count in Counter(headers).items() if count > 1), "missing_required_probes": missing, "numeric_errors": numeric_errors[:20], "grid": grid}
    return {"schema": "bvm-qb-current-baseline-raw-qa-v1", "status": "PASS" if not failures else "FAIL", "artifact_status": "VALID" if not failures else "ARTIFACT_INVALID", "runs": checks, "failures": failures, "no_raw_modification": True}


def pre110_identity(cases: dict[str, dict[str, Any]]) -> dict[str, Any]:
    families: dict[str, Any] = {}
    failures: list[str] = []
    for family in FAMILIES:
        run_ids = [case_id(family, mask) for mask in MASKS]
        base = cases[run_ids[0]]
        pre = [index for index, value in enumerate(base["times_ps"]) if value < 110.0]
        signals = set(base["headers"]) - {"time"}
        mismatches: list[dict[str, Any]] = []
        max_abs = 0.0
        grid_equal = True
        for run_id in run_ids[1:]:
            candidate = cases[run_id]
            if base["times_s"] != candidate["times_s"]:
                grid_equal = False
            for signal in sorted(signals & (set(candidate["headers"]) - {"time"})):
                left_index = base["headers"].index(signal)
                right_index = candidate["headers"].index(signal)
                for index in pre:
                    left = base["rows"][index][left_index]
                    right = candidate["rows"][index][right_index]
                    if left != right:
                        difference = abs(float(right) - float(left))
                        max_abs = max(max_abs, difference)
                        if len(mismatches) < 20:
                            mismatches.append({"reference": run_ids[0], "candidate": run_id, "signal": signal, "sample_index": index, "reference_value": left, "candidate_value": right, "abs_difference": difference})
        special = {}
        if family == "REPLAY":
            signal = "I(I_REPLAY)"
            special[signal] = {"status": "PASS" if not any(item["signal"] == signal for item in mismatches) else "FAIL"}
        passed = grid_equal and not mismatches
        if not passed:
            failures.append(family)
        families[family] = {"status": "PASS" if passed else "FAIL", "run_ids": run_ids, "pre_final_read_window": "[0,110) ps", "sample_count": len(pre), "grid_equal": grid_equal, "max_abs_difference": max_abs, "mismatch_count": sum(1 for _ in mismatches), "mismatches": mismatches, "special_checks": special, "mask_only_final_read_registered": True}
    return {"schema": "bvm-qb-current-baseline-pre110-identity-qa-v1", "status": "PASS" if not failures else "FAIL", "families": families, "failures": failures, "window_semantics": "actual stored grid, half-open [0,110) ps"}


def replay_fidelity(cases: dict[str, dict[str, Any]]) -> dict[str, Any]:
    records: dict[str, Any] = {}
    failures: list[str] = []
    for mask in MASKS:
        passive_id = case_id("PASSIVE", mask)
        replay_id = case_id("REPLAY", mask)
        passive = cases[passive_id]
        replay = cases[replay_id]
        source_signal = "I(B_JSL8)"
        replay_signal = "I(I_REPLAY)"
        source_index = passive["headers"].index(source_signal)
        replay_index = replay["headers"].index(replay_signal)
        count_equal = len(passive["rows"]) == len(replay["rows"])
        timestamps_equal = passive["times_s"] == replay["times_s"]
        differences = [float(replay["rows"][index][replay_index]) - float(passive["rows"][index][source_index]) for index in range(min(len(passive["rows"]), len(replay["rows"]))) ]
        max_abs = max((abs(value) for value in differences), default=None)
        rms = math.sqrt(sum(value * value for value in differences) / len(differences)) if differences else None
        exact_strings = count_equal and all(passive["rows"][index][source_index] == replay["rows"][index][replay_index] for index in range(len(differences)))
        passed = count_equal and timestamps_equal and exact_strings
        if not passed:
            failures.append(mask)
        records[mask] = {"status": "PASS" if passed else "FAIL", "passive_run": passive_id, "replay_run": replay_id, "passive_signal": source_signal, "replay_signal": replay_signal, "passive_orientation": "B_JSL8 JSL_NODE7 -> 0", "replay_orientation": "I_REPLAY 0 -> QBIN", "positive_direction_match": True, "sample_count_passive": len(passive["rows"]), "sample_count_replay": len(replay["rows"]), "same_timestamps": timestamps_equal, "max_abs_sample_error_A": max_abs, "rms_sample_error_A": rms, "exact_string_equality": exact_strings, "stored_sample_representation": True, "interpolation": False, "smoothing": False, "resampling": False}
    return {"schema": "bvm-qb-current-baseline-replay-fidelity-qa-v1", "status": "PASS" if not failures else "FAIL", "records": records, "failures": failures}


def control_metrics(cases: dict[str, dict[str, Any]]) -> dict[str, Any]:
    records: dict[str, Any] = {}
    target_signals = ("P(BJS|XBQ1)", "P(BJ1|XBQ1)", "P(BJ2|XBQ1)", "V(QBIN)", "I(I_REPLAY)")
    for run_id, case in cases.items():
        values: dict[str, Any] = {}
        for signal in target_signals:
            metric = window_metric(case, signal, (70, 81), "zero_read_control_70_81")
            values[signal] = metric
        records[run_id] = {"window_ps": [70, 81], "metrics": values, "phase_turns_are_navigation_only": True}
    return {"schema": "bvm-qb-current-baseline-zero-read-control-metrics-v1", "window_semantics": "[70,81) ps actual stored grid", "runs": records, "scientific_interpretation_performed": False}


def write_signal_manifests(cases: dict[str, dict[str, Any]]) -> None:
    for run_id, case in cases.items():
        output = case["path"].parent / "signal_manifest.csv"
        family = run_id.split("_", 1)[0]
        with output.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=["raw_column_index", "exact_raw_column_name", "subsystem", "instance", "physical_quantity", "unit", "plotted", "plot_path", "reason"])
            writer.writeheader()
            for index, signal in enumerate(case["headers"]):
                if signal == "time":
                    continue
                subsystem, instance, quantity, unit = signal_class(signal)
                slug = hashlib.sha256(signal.encode("utf-8")).hexdigest()[:16]
                writer.writerow({"raw_column_index": index, "exact_raw_column_name": signal, "subsystem": subsystem, "instance": instance, "physical_quantity": quantity, "unit": unit, "plotted": "yes", "plot_path": f"visualization/{run_id}/atlas/{slug}/", "reason": ""})


def write_metrics_table(cases: dict[str, dict[str, Any]]) -> Path:
    fields = ["run_id", "family", "mask", "raw_signal", "window", "window_start_ps", "window_end_ps", "status", "subsystem", "instance", "physical_quantity", "unit", "sample_count", "minimum", "maximum", "mean", "rms", "endpoint", "time_of_min_ps", "time_of_max_ps", "signed_integral", "absolute_integral", "raw_start_rad", "raw_end_rad", "unwrapped_start_rad", "unwrapped_end_rad", "net_unwrapped_delta_rad", "p2p_unwrapped_excursion_rad", "navigation_turns", "phase_semantics"]
    rows: list[dict[str, Any]] = []
    for run_id, case in cases.items():
        family = run_id.split("_", 1)[0]
        mask = run_id.rsplit("_", 1)[1]
        for signal in case["headers"]:
            if signal == "time":
                continue
            for window, label in zip(WINDOWS, WINDOW_LABELS):
                metric = window_metric(case, signal, window, label)
                row = {"run_id": run_id, "family": family, "mask": mask, "raw_signal": signal}
                row.update({field: metric.get(field, "") for field in fields if field not in row})
                rows.append(row)
    output = SERIES / "analysis" / "per_run_window_metrics.csv"
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return output


def write_result(cases: dict[str, dict[str, Any]], raw: dict[str, Any], identity: dict[str, Any], fidelity: dict[str, Any], metrics_path: Path) -> None:
    provenance = read_json(SERIES / "provenance.json")
    result = read_json(SERIES / "result.json") if (SERIES / "result.json").is_file() else {}
    result.update({"schema": "bvm-qb-current-baseline-n0-n4-closed-passive-replay-result-v1", "experiment_id": SERIES.name, "generated_at": now(), "status": "ANALYSIS_COMPLETE_AWAITING_SCIENTIFIC_REVIEW", "artifact_status": "VALID" if raw["status"] == "PASS" and identity["status"] == "PASS" and fidelity["status"] == "PASS" else "ARTIFACT_INVALID", "authorized_solve_count": 15, "actual_physical_solve_count": len(cases), "run_order": list(cases), "qa": {"raw_qa": raw["status"], "pre110_identity_qa": identity["status"], "replay_fidelity_qa": fidelity["status"]}, "analysis": {"per_run_window_metrics": str(metrics_path.relative_to(SERIES)), "control_70_81": "analysis/control_70_81_metrics.json"}, "scientific_interpretation_performed": False, "scientific_verdict": "NOT_ASSIGNED_SCIENTIFIC_REVIEW_REQUIRED", "stop": {"final_marker": "EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW", "automatic_follow_up": False}})
    write_json(SERIES / "result.json", result)
    provenance["analysis"] = {"status": "COMPLETE", "raw_qa": raw["status"], "pre110_identity_qa": identity["status"], "replay_fidelity_qa": fidelity["status"], "per_run_window_metrics": str(metrics_path.relative_to(SERIES)), "generated_at": now(), "scientific_interpretation_performed": False}
    provenance["qa"] = {"raw_qa": raw["status"], "pre110_identity_qa": identity["status"], "replay_fidelity_qa": fidelity["status"]}
    for run_id in cases:
        provenance["runs"].setdefault(run_id, {})["signal_manifest"] = str((Path("runs") / "A001" / "cases" / run_id / "signal_manifest.csv").as_posix())
    write_json(SERIES / "provenance.json", provenance)
    brief = ["# Current QB N0-N4 baseline evidence brief", "", f"- Physical solves completed: `{len(cases)}/15`.", f"- Raw QA: `{raw['status']}`; pre-110 identity QA: `{identity['status']}`; replay fidelity QA: `{fidelity['status']}`.", "- Visualization status is set by `plot.sh`; no cross-run comparison plots are generated.", "- Scientific interpretation: `NOT_PERFORMED`; no N0-N4 comparison, mechanism conclusion, winner, or formal SFQ count is assigned.", "", "## Registered evidence", "", f"- Per-run window table: `{metrics_path.relative_to(SERIES)}`", "- Zero-state read-control metrics: `analysis/control_70_81_metrics.json`", "- Per-run signal manifests: `runs/A001/cases/<run_id>/signal_manifest.csv`", "- Phase views retain raw radians, unwrapped radians, and rad/(2*pi) navigation only.", "", "EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW", ""]
    (SERIES / "RESULT_BRIEF.md").write_text("\n".join(brief), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Mechanical analysis for the current QB N0-N4 baseline")
    parser.add_argument("--series-dir", default=str(SERIES))
    parser.add_argument("attempt")
    args = parser.parse_args()
    if Path(args.series_dir).resolve() != SERIES.resolve():
        raise RuntimeError("series-local analyzer must run from its own series directory")
    attempt = attempt_dir(args.attempt)
    provenance = read_json(SERIES / "provenance.json")
    run_ids = list(provenance.get("run_order", []))
    cases = {run_id: load_case(raw_path(attempt, run_id)) for run_id in run_ids}
    write_signal_manifests(cases)
    metrics_path = write_metrics_table(cases)
    raw = raw_qa(cases)
    identity = pre110_identity(cases) if len(cases) == 15 else {"status": "FAIL", "reason": "requires all 15 runs"}
    fidelity = replay_fidelity(cases) if len(cases) == 15 else {"status": "FAIL", "reason": "requires all 15 runs"}
    control = control_metrics(cases)
    write_json(SERIES / "qa" / "raw_qa.json", raw)
    write_json(SERIES / "qa" / "pre110_identity_qa.json", identity)
    write_json(SERIES / "qa" / "replay_fidelity_qa.json", fidelity)
    write_json(SERIES / "analysis" / "control_70_81_metrics.json", control)
    write_result(cases, raw, identity, fidelity, metrics_path)
    print(json.dumps({"status": "PASS" if raw["status"] == "PASS" and identity["status"] == "PASS" and fidelity["status"] == "PASS" else "FAIL", "attempt": attempt.name, "run_count": len(cases), "raw_qa": raw["status"], "pre110_identity_qa": identity["status"], "replay_fidelity_qa": fidelity["status"], "metrics": str(metrics_path)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
