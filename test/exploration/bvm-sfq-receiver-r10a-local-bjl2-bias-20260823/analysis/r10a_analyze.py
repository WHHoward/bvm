#!/usr/bin/env python3
"""Independent R10-A raw analysis.

The script preserves JoSIM P values in radians, uses the actual CSV time axis
for windows and same-JJ voltage integration, and computes control-subtracted
RMS routing metrics plus the local bias-current split for the single feed point.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path
from statistics import fmean, median


RUN = Path(__file__).resolve().parents[1]
REPO = RUN.parents[2]
RAW = RUN / "raw"
OUT = RUN / "analysis"
R9A = REPO / "test/exploration/bvm-sfq-receiver-r9a-l2-routing-20260823"
CANONICAL = REPO / "test/exploration/bvm-internal-readout-20260819/raw"
RUN_FILE = "run-01.csv"

PHI0 = 2.067833848e-15
TWO_PI = 2.0 * math.pi
WINDOWS = {
    "pre": (80.0, 90.0),
    "activity": (94.0, 130.0),
    "post": (150.0, 170.0),
    "read_state": (20.0, 90.0),
}

JUNCTIONS = {
    "BJs": ("P(BJs|XBQ)", "V(BJs|XBQ)", "I(BJs|XBQ)"),
    "BJL1": ("P(BJL1|XBQ)", "V(BJL1|XBQ)", "I(BJL1|XBQ)"),
    "BJL2": ("P(BJL2|XBQ)", "V(BJL2|XBQ)", "I(BJL2|XBQ)"),
}
BRANCHES = {
    "Lin": "I(Lin|XBQ)",
    "L1": "I(L1|XBQ)",
    "L2": "I(L2|XBQ)",
    "L0": "I(L0|XBQ)",
    "RB": "I(RB|XBQ)",
    "RJ1": "I(RJ1|XBQ)",
    "RJ2": "I(RJ2|XBQ)",
    "R_PRI": "I(R_PRI)",
    "L_PRI": "I(L_PRI)",
    "L_SEC": "I(L_SEC)",
    "R_LOCAL_BJL2": "I(R_LOCAL_BJL2|XBQ)",
    "L_LOCAL_BJL2": "I(L_LOCAL_BJL2|XBQ)",
    "V_BJL2_BIAS": "I(V_BJL2_BIAS)",
}
LOCAL_VOLTAGE_KEYS = ["V(BIAS)", "V(N_LOCAL_BJL2|XBQ)"]
SOURCE_KEYS = ["V(SL1)", "V(N6|XBVM1)", "I(L_SL|XBVM1)"]
STATE_KEYS = [
    "P(B_JM1|XBVM1)",
    "P(B_JM2|XBVM1)",
    "P(B_JS1|XBVM1)",
    "P(B_JS2|XBVM1)",
]

REQUIRED = {
    "time",
    *[key for triple in JUNCTIONS.values() for key in triple],
    *BRANCHES.values(),
    *LOCAL_VOLTAGE_KEYS,
    *SOURCE_KEYS,
    "V(QB_IN)",
    "V(OUT_Q)",
    "V(L_PRI)",
    "V(L_SEC)",
    *STATE_KEYS,
}


def load_csv(path: Path):
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        fields = set(reader.fieldnames or [])
        lookup = {field.casefold(): field for field in fields}
        missing = sorted(key for key in REQUIRED if key.casefold() not in lookup)
        rows = []
        conversion_error = None
        for number, raw in enumerate(reader, start=2):
            try:
                rows.append(
                    {
                        key: float(raw[lookup[key.casefold()]])
                        for key in REQUIRED
                        if key.casefold() in lookup
                    }
                )
            except (TypeError, ValueError) as exc:
                conversion_error = f"row {number}: {exc}"
                break
    times = [row.get("time", float("nan")) for row in rows]
    finite = bool(rows) and all(math.isfinite(value) for row in rows for value in row.values())
    increasing = bool(rows) and all(a < b for a, b in zip(times, times[1:]))
    dts = [(b - a) * 1.0e12 for a, b in zip(times, times[1:])]
    return {
        "path": path,
        "fields": fields,
        "rows": rows,
        "missing": missing,
        "conversion_error": conversion_error,
        "finite": finite,
        "increasing": increasing,
        "dt_ps": {
            "min": min(dts) if dts else None,
            "max": max(dts) if dts else None,
            "median": median(dts) if dts else None,
        },
    }


def load_source_csv(path: Path):
    """Load canonical BVM source/storage columns without QB-only columns."""
    required = {"time", *SOURCE_KEYS, *STATE_KEYS}
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        fields = set(reader.fieldnames or [])
        lookup = {field.casefold(): field for field in fields}
        missing = sorted(key for key in required if key.casefold() not in lookup)
        rows = []
        conversion_error = None
        for number, raw in enumerate(reader, start=2):
            try:
                rows.append(
                    {
                        key: float(raw[lookup[key.casefold()]])
                        for key in required
                        if key.casefold() in lookup
                    }
                )
            except (TypeError, ValueError) as exc:
                conversion_error = f"row {number}: {exc}"
                break
    times = [row.get("time", float("nan")) for row in rows]
    finite = bool(rows) and all(math.isfinite(value) for row in rows for value in row.values())
    increasing = bool(rows) and all(a < b for a, b in zip(times, times[1:]))
    dts = [(b - a) * 1.0e12 for a, b in zip(times, times[1:])]
    return {
        "path": path,
        "fields": fields,
        "rows": rows,
        "missing": missing,
        "conversion_error": conversion_error,
        "finite": finite,
        "increasing": increasing,
        "dt_ps": {
            "min": min(dts) if dts else None,
            "max": max(dts) if dts else None,
            "median": median(dts) if dts else None,
        },
    }


def in_window(row, window):
    t_ps = row["time"] * 1.0e12
    return window[0] <= t_ps < window[1]


def indices(rows, window):
    return [index for index, row in enumerate(rows) if in_window(row, window)]


def values(rows, key, window):
    return [rows[index][key] for index in indices(rows, window)]


def median_value(rows, key, window):
    data = values(rows, key, window)
    return median(data) if data else float("nan")


def extrema(rows, key, window):
    data = values(rows, key, window)
    return {
        "min": min(data) if data else float("nan"),
        "max": max(data) if data else float("nan"),
        "p2p": max(data) - min(data) if data else float("nan"),
        "peak_abs": max((abs(value) for value in data), default=float("nan")),
    }


def trapezoid(rows, key, first, last):
    total = 0.0
    for left, right in zip(rows[first:last], rows[first + 1 : last + 1]):
        total += 0.5 * (left[key] + right[key]) * (right["time"] - left["time"])
    return total


def continuous_phase(rows, key):
    if not rows:
        return []
    result = [rows[0][key]]
    for row, previous in zip(rows[1:], rows):
        delta = row[key] - previous[key]
        while delta > math.pi:
            delta -= TWO_PI
        while delta < -math.pi:
            delta += TWO_PI
        result.append(result[-1] + delta)
    return result


def monotonic_segments(rows, phase_key, voltage_key, window):
    phase = continuous_phase(rows, phase_key)
    active = indices(rows, window)
    if len(active) < 3:
        return []
    # Match the accepted R7-A descriptive segment algorithm so the direct
    # L2 comparison does not change the segmentation rule.
    half = 5
    prominence = 0.005 * TWO_PI
    candidates = []
    for position in range(half, len(active) - half):
        index = active[position]
        value = phase[index]
        left = [phase[active[item]] for item in range(position - half, position)]
        right = [phase[active[item]] for item in range(position + 1, position + half + 1)]
        kind = None
        if value >= max(left + right):
            kind = "max"
        elif value <= min(left + right):
            kind = "min"
        if kind is None:
            continue
        candidate = {"position": position, "index": index, "kind": kind, "value": value}
        if candidates and candidates[-1]["kind"] == kind:
            better = value > candidates[-1]["value"] if kind == "max" else value < candidates[-1]["value"]
            if better:
                candidates[-1] = candidate
            continue
        if candidates and abs(value - candidates[-1]["value"]) < prominence:
            continue
        candidates.append(candidate)
    extrema_indices = [active[0]] + [item["index"] for item in candidates]
    if extrema_indices[-1] != active[-1]:
        extrema_indices.append(active[-1])
    extrema_indices = sorted(set(extrema_indices))
    segments = []
    for first, last in zip(extrema_indices, extrema_indices[1:]):
        delta_rad = phase[last] - phase[first]
        area_turns = trapezoid(rows, voltage_key, first, last) / PHI0
        segments.append(
            {
                "start_ps": rows[first]["time"] * 1.0e12,
                "end_ps": rows[last]["time"] * 1.0e12,
                "phase_delta_rad": delta_rad,
                "phase_delta_turns": delta_rad / TWO_PI,
                "area_turns": area_turns,
                "residual_turns": delta_rad / TWO_PI - area_turns,
                "area_consistent": abs(delta_rad / TWO_PI - area_turns) <= 0.05,
            }
        )
    return sorted(segments, key=lambda item: abs(item["phase_delta_turns"]), reverse=True)


def junction_result(rows, name):
    phase_key, voltage_key, current_key = JUNCTIONS[name]
    phase = continuous_phase(rows, phase_key)
    active = indices(rows, WINDOWS["activity"])
    post = indices(rows, WINDOWS["post"])
    segments = monotonic_segments(rows, phase_key, voltage_key, WINDOWS["activity"])
    qualifying = [
        segment
        for segment in segments
        if abs(segment["phase_delta_turns"]) >= 1.0 and segment["area_consistent"]
    ]
    return {
        "phase_column": phase_key,
        "voltage_column": voltage_key,
        "current_column": current_key,
        "pre_median_rad": median_value(rows, phase_key, WINDOWS["pre"]),
        "pre_current_uA": median_value(rows, current_key, WINDOWS["pre"]) * 1.0e6,
        "post_phase_p2p_turn": (
            (max(phase[index] for index in post) - min(phase[index] for index in post)) / TWO_PI
            if post
            else float("nan")
        ),
        "activity_range_turn": (
            (max(phase[index] for index in active) - min(phase[index] for index in active)) / TWO_PI
            if active
            else float("nan")
        ),
        "activity_current": {key: value * 1.0e6 for key, value in extrema(rows, current_key, WINDOWS["activity"]).items()},
        "activity_voltage": {key: value * 1.0e6 for key, value in extrema(rows, voltage_key, WINDOWS["activity"]).items()},
        "largest_segment": segments[0] if segments else None,
        "qualifying_complete_segment_count": len(qualifying),
    }


def case_result(info):
    rows = info["rows"]
    try:
        raw_path = str(info["path"].relative_to(RUN))
    except ValueError:
        raw_path = str(info["path"].relative_to(REPO))
    result = {
        "case": info["path"].parent.name,
        "raw_path": raw_path,
        "artifact": {
            "row_count": len(rows),
            "field_count": len(info["fields"]),
            "missing_required_columns": info["missing"],
            "conversion_error": info["conversion_error"],
            "finite": info["finite"],
            "time_strictly_increasing": info["increasing"],
            "first_ps": rows[0]["time"] * 1.0e12 if rows else None,
            "last_ps": rows[-1]["time"] * 1.0e12 if rows else None,
            "dt_ps": info["dt_ps"],
            "valid": bool(rows and not info["missing"] and not info["conversion_error"] and info["finite"] and info["increasing"]),
        },
        "junctions": {},
        "branches": {},
        "local_voltage": {},
        "source": {},
        "storage": {},
    }
    if not result["artifact"]["valid"]:
        return result
    for name in JUNCTIONS:
        result["junctions"][name] = junction_result(rows, name)
    for name, key in BRANCHES.items():
        activity = extrema(rows, key, WINDOWS["activity"])
        result["branches"][name] = {
            "activity": {item: value * 1.0e6 for item, value in activity.items()},
            "pre_uA": median_value(rows, key, WINDOWS["pre"]) * 1.0e6,
            "post_uA": median_value(rows, key, WINDOWS["post"]) * 1.0e6,
        }
    for key in LOCAL_VOLTAGE_KEYS:
        result["local_voltage"][key] = {
            "activity_uV": {item: value * 1.0e6 for item, value in extrema(rows, key, WINDOWS["activity"]).items()},
            "pre_uV": median_value(rows, key, WINDOWS["pre"]) * 1.0e6,
            "post_uV": median_value(rows, key, WINDOWS["post"]) * 1.0e6,
        }
    for key in SOURCE_KEYS:
        result["source"][key] = {
            "activity": {item: value * (1.0e6 if key.startswith("I(") else 1.0e6) for item, value in extrema(rows, key, WINDOWS["activity"]).items()},
            "post": {item: value * (1.0e6 if key.startswith("I(") else 1.0e6) for item, value in extrema(rows, key, WINDOWS["post"]).items()},
        }
    for key in STATE_KEYS:
        pre = median_value(rows, key, WINDOWS["pre"])
        post = median_value(rows, key, WINDOWS["post"])
        post_values = values(rows, key, WINDOWS["post"])
        result["storage"][key] = {
            "pre_rad": pre,
            "post_rad": post,
            "drift_rad": post - pre,
            "drift_turn": (post - pre) / TWO_PI,
            "post_p2p_rad": max(post_values) - min(post_values) if post_values else float("nan"),
            "post_p2p_turn": (max(post_values) - min(post_values)) / TWO_PI if post_values else float("nan"),
        }
    return result


def source_result(info):
    """Summarize source/storage guards for a source-only canonical CSV."""
    rows = info["rows"]
    try:
        raw_path = str(info["path"].relative_to(REPO))
    except ValueError:
        raw_path = str(info["path"])
    valid = bool(rows and not info["missing"] and not info["conversion_error"] and info["finite"] and info["increasing"])
    result = {
        "raw_path": raw_path,
        "artifact": {
            "row_count": len(rows),
            "field_count": len(info["fields"]),
            "missing_required_columns": info["missing"],
            "conversion_error": info["conversion_error"],
            "finite": info["finite"],
            "time_strictly_increasing": info["increasing"],
            "first_ps": rows[0]["time"] * 1.0e12 if rows else None,
            "last_ps": rows[-1]["time"] * 1.0e12 if rows else None,
            "dt_ps": info["dt_ps"],
            "valid": valid,
        },
        "source": {},
        "storage": {},
    }
    if not valid:
        return result
    for key in SOURCE_KEYS:
        result["source"][key] = {
            "activity": {item: value * 1.0e6 for item, value in extrema(rows, key, WINDOWS["activity"]).items()},
            "post": {item: value * 1.0e6 for item, value in extrema(rows, key, WINDOWS["post"]).items()},
        }
    for key in STATE_KEYS:
        pre = median_value(rows, key, WINDOWS["pre"])
        post = median_value(rows, key, WINDOWS["post"])
        post_values = values(rows, key, WINDOWS["post"])
        result["storage"][key] = {
            "pre_rad": pre,
            "post_rad": post,
            "drift_rad": post - pre,
            "drift_turn": (post - pre) / TWO_PI,
            "post_p2p_rad": max(post_values) - min(post_values) if post_values else float("nan"),
            "post_p2p_turn": (max(post_values) - min(post_values)) / TWO_PI if post_values else float("nan"),
        }
    return result


def rms(values_):
    return math.sqrt(fmean(value * value for value in values_)) if values_ else float("nan")


def routing(read_info, control_info):
    read = read_info["rows"]
    control = control_info["rows"]
    active = [
        index
        for index, row in enumerate(read)
        if WINDOWS["activity"][0] <= row["time"] * 1.0e12 < WINDOWS["activity"][1]
    ]
    if len(read) != len(control) or any(abs(read[i]["time"] - control[i]["time"]) > 1e-24 for i in active):
        return {"aligned": False}
    deltas = {}
    for name, key in (("Lin", BRANCHES["Lin"]), ("L2", BRANCHES["L2"]), ("BJL2", JUNCTIONS["BJL2"][2]), ("BJL1", JUNCTIONS["BJL1"][2]), ("RJ1", BRANCHES["RJ1"])):
        values_ = [(read[i][key] - control[i][key]) * 1.0e6 for i in active]
        deltas[name] = {"rms_uA": rms(values_), "min_uA": min(values_), "max_uA": max(values_), "p2p_uA": max(values_) - min(values_)}
    denom = deltas["Lin"]["rms_uA"]
    deltas["G_L2"] = deltas["L2"]["rms_uA"] / denom if denom else float("nan")
    deltas["G_BJL2"] = deltas["BJL2"]["rms_uA"] / denom if denom else float("nan")
    return {"aligned": True, "window_ps": WINDOWS["activity"], "delta": deltas}


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_case(directory, case, filename=RUN_FILE):
    return load_csv(directory / "raw" / case / filename)


def main():
    cases = ["read1", "read0", "logical1-read0-control", "logical0-read0-control"]
    infos = {case: load_case(RUN, case) for case in cases}
    results = {case: case_result(infos[case]) for case in cases}
    routing_results = {
        "read1": routing(infos["read1"], infos["logical1-read0-control"]),
        "read0": routing(infos["read0"], infos["logical0-read0-control"]),
    }

    r9a_infos = {case: load_case(R9A, case, "run-02.csv") for case in cases}
    r9a_routing = {
        "read1": routing(r9a_infos["read1"], r9a_infos["logical1-read0-control"]),
        "read0": routing(r9a_infos["read0"], r9a_infos["logical0-read0-control"]),
    }

    canonical_paths = {
        "read1": CANONICAL / "pos-read-single/run-01.csv",
        "read0": CANONICAL / "neg-init-pos-read/run-01.csv",
    }
    canonical_results = {}
    for case, path in canonical_paths.items():
        if path.exists():
            canonical_results[case] = source_result(load_source_csv(path))

    # This is a descriptive failure classification, not a new universal
    # threshold: every matched case has multi-turn BJL2 activity in the
    # preregistered activity and post windows, including both READ=0 controls.
    control_free_running = all(
        results[case]["junctions"]["BJL2"]["activity_range_turn"] > 1.0
        and results[case]["junctions"]["BJL2"]["post_phase_p2p_turn"] > 1.0
        for case in ("logical1-read0-control", "logical0-read0-control")
    )
    all_cases_free_running = all(
        results[case]["junctions"]["BJL2"]["activity_range_turn"] > 1.0
        and results[case]["junctions"]["BJL2"]["post_phase_p2p_turn"] > 1.0
        for case in cases
    )
    verdict = "BACK_ACTION_OR_NONSELECTIVE_FAILURE" if control_free_running else "PENDING_REVIEW"

    raw_paths = [RAW / case / RUN_FILE for case in cases]
    output = {
        "analysis": {
            "script": str(Path(__file__).relative_to(RUN)),
            "phi0_Wb": PHI0,
            "windows_ps": WINDOWS,
            "activity_routing_definition": "read minus matching READ=0 control",
            "event_threshold_turn": 1.0,
            "same_jj_area_tolerance_turn": 0.05,
            "R9A_reference_routing": r9a_routing,
            "raw_sha256": {
                str(path.relative_to(RUN)): sha256(path)
                for path in raw_paths
            },
        },
        "cases": results,
        "routing": routing_results,
        "canonical_cases": canonical_results,
        "artifact_status": "VALID" if all(result["artifact"]["valid"] for result in results.values()) else "INVALID",
        "verdict": verdict,
        "local_native_qb_pass": False,
        "static_operating_point_shift": True,
        "settled_operating_point_established": False,
        "control_free_running_observed": control_free_running,
        "all_cases_free_running_observed": all_cases_free_running,
    }
    output_path = OUT / "r10a-summary.json"
    output_path.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
