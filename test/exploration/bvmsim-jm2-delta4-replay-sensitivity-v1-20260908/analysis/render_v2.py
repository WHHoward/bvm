#!/usr/bin/env python3
"""Build the per-run delta4_v2 visualization package.

This renderer reads immutable raw/source data and derived CSVs, creates
windowed and pairwise CSVs, then calls josim-plot2.py. It never invokes
build/josim-cli and never modifies raw evidence.
"""

from __future__ import annotations

import csv
import hashlib
import html
import json
import math
import subprocess
import sys
from decimal import Decimal
from pathlib import Path


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
OLD = REPO / "test/exploration/bvmsim-jm2-read-count-passive-replay-v1-20260907"
PLOTTER = REPO / "scripts/josim-plot2.py"
V2_ROOT = EXP / "plots/delta4_v2"
V1_ROOT = EXP / "plots/delta4_v1"
RUNS = (
    "DELTA4_DELAY_3PS",
    "DELTA4_DELAY_6PS",
    "DELTA4_GAIN_1P25",
    "DELTA4_GAIN_1P50",
)
PAIR_CASES = ("N4_REPLAY",) + RUNS
RAW_PATHS = {
    "N3_REPLAY": OLD / "runs/n3_replay/raw.csv",
    "N4_REPLAY": OLD / "runs/n4_replay/raw.csv",
    **{run_id: EXP / "runs" / run_id / "raw.csv" for run_id in RUNS},
}
SOURCE_RAW_PATHS = {
    "N3_PASSIVE": OLD / "runs/n3_passive/raw.csv",
    "N4_PASSIVE": OLD / "runs/n4_passive/raw.csv",
}
SOURCE_DERIVED_PATHS = {
    run_id: EXP / "data" / f"{run_id}_source.csv"
    for run_id in RUNS
}
EXPECTED_RAW_HASHES = {
    "N3_REPLAY": "555e850fde892da7fd2328d2ac34081b45459ab48e8181a8e95d7cd531e7c225",
    "N4_REPLAY": "5cac782aa9dfa5d467d81e2988e772f1978abfe8313d7896089d5dfa84517b28",
    "N3_PASSIVE": "f966077641779f90c5043bf7f5d9a4beaba9b13214977cc26cb399e1f6d90273",
    "N4_PASSIVE": "ea9e1e123c80dfc38a0d3b061d8eb68f9ed76133db07490da616cb3bf5b70ba0",
}
WINDOWS = {
    "FINAL_READ_RESPONSE": (Decimal("110.0"), Decimal("200.0")),
    "QB_INTERNAL_CRITICAL": (Decimal("118.0"), Decimal("140.0")),
    "DOWNSTREAM_ZOOM": (Decimal("118.0"), Decimal("180.0")),
}
SOURCE_KIND_BVM = "IMMUTABLE_PASSIVE_SOURCE_REFERENCE / NOT REPLAY-RUN RAW"
SOURCE_KIND_INPUT = "DERIVED_INPUT_COMPONENT / NOT REPLAY-RUN RAW"
SOURCE_KIND_WINDOWED = "RAW_RUN_WINDOWED_STANDALONE"
SOURCE_KIND_PAIRWISE = "N4_REPLAY_VS_INTERVENTION_RAW_AND_DERIVED_DELTA"

QB_FULL = (
    "I(I_REPLAY)",
    "V(QBIN)",
    "I(LIN|XBQ1)",
    "V(LIN|XBQ1)",
    "P(BJS|XBQ1)",
    "V(BJS|XBQ1)",
    "I(BJS|XBQ1)",
    "I(L1|XBQ1)",
    "V(L1|XBQ1)",
    "P(BJ1|XBQ1)",
    "V(BJ1|XBQ1)",
    "I(BJ1|XBQ1)",
    "I(RJ1|XBQ1)",
    "V(RJ1|XBQ1)",
    "I(L2|XBQ1)",
    "V(L2|XBQ1)",
    "I(IB|XBQ1)",
    "P(BJ2|XBQ1)",
    "V(BJ2|XBQ1)",
    "I(BJ2|XBQ1)",
    "I(RJ2|XBQ1)",
    "V(RJ2|XBQ1)",
    "I(L3|XBQ1)",
    "V(L3|XBQ1)",
    "V(QBOUT)",
)
JTL_FULL = tuple(
    label
    for stage in range(1, 7)
    for label in (
        f"P(B01|XJTL1_{stage})",
        f"V(B01|XJTL1_{stage})",
        f"I(B01|XJTL1_{stage})",
        f"P(B02|XJTL1_{stage})",
        f"V(B02|XJTL1_{stage})",
        f"I(B02|XJTL1_{stage})",
        f"V(JTL{stage}_OUT)",
    )
) + ("I(R_TERM)",)

CONTROL_INPUTS = tuple(
    f"I(I_{kind}{index})"
    for index in range(1, 5)
    for kind in ("WL", "BL", "SE")
)
BVM_CORE = tuple(
    f"{quantity}(B_{element}|XBVM{bvm})"
    for bvm in range(1, 5)
    for element in ("JM1", "JM2", "JS1", "JS2")
    for quantity in ("P", "V", "I")
)
BVM_BRANCHES = tuple(
    f"{quantity}({element}|XBVM{bvm})"
    for bvm in range(1, 5)
    for element in (
        "L_M1",
        "L_M2",
        "L_M3",
        "L_PM",
        "R_JM1",
        "L_S1",
        "L_S2",
        "R_S",
        "L_S3",
        "R_SE",
        "L_PSE",
        "L_PSL",
        "R_SL",
        "L_SL",
    )
    for quantity in ("I", "V")
)
JSL_SOURCE = tuple(
    f"{quantity}(B_JSL{stage})"
    for stage in range(1, 9)
    for quantity in ("P", "V", "I")
)
BVM_SOURCE_LABELS = CONTROL_INPUTS + BVM_CORE + BVM_BRANCHES + (
    "V(COMMON_SL)",
) + JSL_SOURCE


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def write_once(path: Path, content: str) -> None:
    if path.exists():
        if path.read_text(encoding="utf-8") != content:
            raise RuntimeError(f"refusing to overwrite existing artifact: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def rel(path: Path) -> str:
    return path.relative_to(REPO).as_posix()


def unit(label: str) -> str:
    if label.startswith("P("):
        return "rad"
    if label.startswith("V("):
        return "V"
    return "A"


def load_raw(path: Path) -> tuple[list[str], list[dict[str, str]], dict[Decimal, dict[str, str]], dict[Decimal, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        fields = list(reader.fieldnames or [])
        rows = list(reader)
    if not fields or fields[0] != "time":
        raise RuntimeError(f"raw input must begin with time: {path}")
    by_time: dict[Decimal, dict[str, str]] = {}
    time_tokens: dict[Decimal, str] = {}
    for row in rows:
        time_ps = Decimal(row["time"]) * Decimal("1e12")
        if time_ps in by_time:
            raise RuntimeError(f"duplicate timestamp in {path}: {time_ps}")
        by_time[time_ps] = row
        time_tokens[time_ps] = row["time"]
    return fields, rows, by_time, time_tokens


def raw_hashes() -> dict[str, str]:
    return {case: sha256(path) for case, path in RAW_PATHS.items()}


def phase_unwrap(values: list[float]) -> list[float]:
    output = [float(values[0])]
    previous = float(values[0])
    tau = 2.0 * math.pi
    for value in values[1:]:
        current = float(value)
        delta = current - previous
        while delta > math.pi:
            delta -= tau
        while delta < -math.pi:
            delta += tau
        output.append(output[-1] + delta)
        previous = current
    return output


def decimal_token(value: Decimal) -> str:
    if value == 0:
        return "0.000000e+00"
    return format(value, "E").replace("E", "e")


def float_token(value: float) -> str:
    return f"{value:.17e}"


def write_csv(path: Path, header: list[str], rows: list[list[str]]) -> None:
    lines = [",".join(header)]
    lines.extend(",".join(row) for row in rows)
    write_once(path, "\n".join(lines) + "\n")


def track_label(base: str, role: str, kind: str, page_kind: str) -> str:
    return f"{base} | {role} | {kind} | {unit(base)} | {page_kind}"


def create_bvm_source_csv(run_id: str) -> dict[str, object]:
    loaded = {
        case: load_raw(path)
        for case, path in SOURCE_RAW_PATHS.items()
    }
    for case, (fields, _, _, _) in loaded.items():
        missing = [label for label in BVM_SOURCE_LABELS if label not in fields[1:]]
        if missing:
            raise RuntimeError(f"{case}: missing BVM source labels {missing[:10]}")
    common_times = set(loaded["N3_PASSIVE"][2])
    common_times &= set(loaded["N4_PASSIVE"][2])
    times = sorted(common_times)
    header = ["time"]
    for case in ("N3_PASSIVE", "N4_PASSIVE"):
        header.extend(
            track_label(label, case, "raw", SOURCE_KIND_BVM)
            for label in BVM_SOURCE_LABELS
        )
    rows: list[list[str]] = []
    for time_ps in times:
        row = [loaded["N3_PASSIVE"][3][time_ps]]
        for case in ("N3_PASSIVE", "N4_PASSIVE"):
            values = loaded[case][2][time_ps]
            row.extend(values[label] for label in BVM_SOURCE_LABELS)
        rows.append(row)
    path = V2_ROOT / run_id / "data/BVM_SOURCE_REFERENCE.csv"
    write_csv(path, header, rows)
    return {
        "path": rel(path),
        "sha256": sha256(path),
        "sample_count": len(rows),
        "time_start_ps": str(times[0]),
        "time_last_sample_ps": str(times[-1]),
        "source_kind": SOURCE_KIND_BVM,
        "source_raw_paths": {
            case: rel(SOURCE_RAW_PATHS[case])
            for case in ("N3_PASSIVE", "N4_PASSIVE")
        },
        "source_raw_hashes": {
            case: sha256(SOURCE_RAW_PATHS[case])
            for case in ("N3_PASSIVE", "N4_PASSIVE")
        },
        "labels": list(BVM_SOURCE_LABELS),
        "plot_labels": header[1:],
        "note": "BVM/JSL tracks are immutable passive source references and do not belong to the intervention replay raw.",
    }


def create_input_csv(run_id: str) -> dict[str, object]:
    source_path = SOURCE_DERIVED_PATHS[run_id]
    with source_path.open(newline="", encoding="utf-8") as handle:
        source_rows = list(csv.DictReader(handle))
    n4_fields, _, n4_by_time, _ = load_raw(SOURCE_RAW_PATHS["N4_PASSIVE"])
    if not source_rows:
        raise RuntimeError(f"empty derived source: {source_path}")
    n4_source_label = "I(B_JSL8)"
    if n4_source_label not in n4_fields:
        raise RuntimeError("N4 passive source is missing I(B_JSL8)")
    n4_source_map = {
        time_ps: row[n4_source_label]
        for time_ps, row in n4_by_time.items()
    }
    last_n4 = n4_source_map[max(n4_source_map)]
    base_labels = (
        "I(I_N3_BACKGROUND)",
        "I(I_N4_PASSIVE_REFERENCE)",
        "I(delta_I4_BASE)",
        f"I(delta_I4_COMPONENT_{run_id})",
        f"I(I_REPLAY_{run_id})",
    )
    header = [
        track_label(label, run_id, "derived", SOURCE_KIND_INPUT)
        for label in base_labels
    ]
    rows: list[list[str]] = []
    for source_row in source_rows:
        time_ps = Decimal(source_row["time_ps"])
        n4_value = n4_source_map.get(time_ps, last_n4)
        values = [
            source_row["I_N3_BACKGROUND_A"],
            n4_value,
            source_row["delta_I4_BASE_AT_LOOKUP_A"],
            source_row["delta_I4_COMPONENT_A"],
            source_row["I_REPLAY_A"],
        ]
        rows.append([f"{time_ps * Decimal('1e-12'):.12e}", *values])
    path = V2_ROOT / run_id / "data/INPUT_COMPONENTS.csv"
    write_csv(path, ["time", *header], rows)
    return {
        "path": rel(path),
        "sha256": sha256(path),
        "sample_count": len(rows),
        "time_start_ps": source_rows[0]["time_ps"],
        "time_last_sample_ps": source_rows[-1]["time_ps"],
        "source_kind": SOURCE_KIND_INPUT,
        "source_derived_path": rel(source_path),
        "source_derived_sha256": sha256(source_path),
        "labels": list(base_labels),
        "plot_labels": header,
    }


def create_windowed_csv(
    run_id: str,
    page_stem: str,
    labels: tuple[str, ...],
    window_name: str,
    source_kind: str,
) -> dict[str, object]:
    fields, _, by_time, time_tokens = load_raw(RAW_PATHS[run_id])
    missing = [label for label in labels if label not in fields[1:]]
    if missing:
        raise RuntimeError(f"{run_id}/{page_stem}: missing raw labels {missing}")
    start, end = WINDOWS[window_name]
    times = sorted(time for time in by_time if start <= time < end)
    if len(times) < 2:
        raise RuntimeError(f"{run_id}/{page_stem}: too few samples in {window_name}")
    header = [
        track_label(label, run_id, "raw", source_kind)
        for label in labels
    ]
    rows = [
        [time_tokens[time], *(by_time[time][label] for label in labels)]
        for time in times
    ]
    path = V2_ROOT / run_id / "data" / f"{page_stem}.csv"
    write_csv(path, ["time", *header], rows)
    return {
        "path": rel(path),
        "sha256": sha256(path),
        "input_raw": rel(RAW_PATHS[run_id]),
        "input_raw_sha256": sha256(RAW_PATHS[run_id]),
        "run_id": run_id,
        "source_kind": source_kind,
        "window_name": window_name,
        "declared_window_ps": [str(start), str(end)],
        "window_semantics": "half-open [start,end)",
        "actual_time_start_ps": str(times[0]),
        "actual_time_last_sample_ps": str(times[-1]),
        "actual_sample_count": len(times),
        "labels": list(labels),
        "plot_labels": header,
        "uses_full_raw_as_plot_input": False,
    }


def create_pairwise_csv(
    run_id: str,
    page_stem: str,
    labels: tuple[str, ...],
    window_name: str,
) -> dict[str, object]:
    n4_fields, n4_rows, n4_by_time, n4_tokens = load_raw(RAW_PATHS["N4_REPLAY"])
    run_fields, run_rows, run_by_time, _ = load_raw(RAW_PATHS[run_id])
    for case, fields in (("N4_REPLAY", n4_fields), (run_id, run_fields)):
        missing = [label for label in labels if label not in fields[1:]]
        if missing:
            raise RuntimeError(f"{page_stem}/{case}: missing labels {missing}")
    n4_times = [Decimal(row["time"]) * Decimal("1e12") for row in n4_rows]
    run_times = [Decimal(row["time"]) * Decimal("1e12") for row in run_rows]
    phase_maps: dict[str, dict[Decimal, float]] = {}
    for case, rows, times in (
        ("N4_REPLAY", n4_rows, n4_times),
        (run_id, run_rows, run_times),
    ):
        phase_maps[case] = {}
        for label in labels:
            if not label.startswith("P("):
                continue
            unwrapped = phase_unwrap([float(row[label]) for row in rows])
            phase_maps[case].update(
                {(label, time): value for time, value in zip(times, unwrapped)}
            )
    common_times = sorted(set(n4_by_time) & set(run_by_time))
    start, end = WINDOWS[window_name]
    times = [time for time in common_times if start <= time < end]
    if len(times) < 2:
        raise RuntimeError(f"{page_stem}: too few pairwise common-grid samples")
    header = ["time"]
    derived_phase_labels: list[str] = []
    for label in labels:
        header.append(track_label(label, "N4_REPLAY", "raw", SOURCE_KIND_PAIRWISE))
        header.append(track_label(label, run_id, "raw", SOURCE_KIND_PAIRWISE))
        derived_kind = "derived delta"
        derived_label = track_label(
            label,
            f"{run_id}_MINUS_N4",
            derived_kind,
            "independently unwrapped per case before subtraction"
            if label.startswith("P(")
            else SOURCE_KIND_PAIRWISE,
        )
        header.append(derived_label)
        if label.startswith("P("):
            derived_phase_labels.append(derived_label)
    rows: list[list[str]] = []
    for time_ps in times:
        row = [n4_tokens[time_ps]]
        for label in labels:
            n4_value = n4_by_time[time_ps][label]
            run_value = run_by_time[time_ps][label]
            row.extend([n4_value, run_value])
            if label.startswith("P("):
                delta_value = phase_maps[run_id][(label, time_ps)] - phase_maps["N4_REPLAY"][(label, time_ps)]
                row.append(float_token(delta_value))
            else:
                delta_value = Decimal(run_value) - Decimal(n4_value)
                row.append(decimal_token(delta_value))
        rows.append(row)
    path = V2_ROOT / run_id / "data" / f"{page_stem}.csv"
    write_csv(path, header, rows)
    return {
        "path": rel(path),
        "sha256": sha256(path),
        "input_control_raw": rel(RAW_PATHS["N4_REPLAY"]),
        "input_control_raw_sha256": sha256(RAW_PATHS["N4_REPLAY"]),
        "input_intervention_raw": rel(RAW_PATHS[run_id]),
        "input_intervention_raw_sha256": sha256(RAW_PATHS[run_id]),
        "run_id": run_id,
        "control": "N4_REPLAY",
        "source_kind": SOURCE_KIND_PAIRWISE,
        "window_name": window_name,
        "declared_window_ps": [str(start), str(end)],
        "window_semantics": "half-open [start,end)",
        "actual_time_start_ps": str(times[0]),
        "actual_time_last_sample_ps": str(times[-1]),
        "actual_sample_count": len(times),
        "labels": list(labels),
        "plot_labels": header[1:],
        "phase_delta_labels": derived_phase_labels,
        "phase_delta_provenance": {
            "method": "independently unwrap complete N4_REPLAY and intervention raw phase traces, then subtract",
            "expression": "unwrapped(intervention) - unwrapped(N4_REPLAY)",
            "raw_phase_unit": "rad",
            "display_conversion": "rad/(2*pi) only via josim-plot2.py -j 2pi",
            "wrapped_phase_subtraction": False,
        },
        "uses_full_raw_as_plot_input": False,
    }


def render_page(
    run_id: str,
    name: str,
    input_path: Path,
    plot_labels: list[str],
    base_labels: list[str],
    title: str,
    source_kind: str,
    declared_window_ps: list[str] | list[float],
    metadata: dict[str, object],
) -> dict[str, object]:
    output_path = V2_ROOT / run_id / f"{name}.html"
    if output_path.exists():
        raise RuntimeError(f"refusing to overwrite visualization: {output_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable,
        str(PLOTTER),
        str(input_path),
        "-x",
        str(output_path),
        "-t",
        "sep_comb",
        "-c",
        "dark",
        "-j",
        "2pi",
        "-w",
        title,
        "-s",
        *plot_labels,
    ]
    completed = subprocess.run(command, cwd=REPO, text=True, capture_output=True)
    if completed.returncode != 0:
        raise RuntimeError(f"{run_id}/{name}: plotter failed: {completed.stderr[-1200:]}")
    if not output_path.is_file() or output_path.stat().st_size == 0:
        raise RuntimeError(f"{run_id}/{name}: empty plot output")
    record = {
        "run_id": run_id,
        "name": name,
        "output": rel(output_path),
        "output_sha256": sha256(output_path),
        "output_bytes": output_path.stat().st_size,
        "input": rel(input_path),
        "input_sha256": sha256(input_path),
        "labels": base_labels,
        "plot_labels": plot_labels,
        "title": title,
        "source_kind": source_kind,
        "declared_window_ps": declared_window_ps,
        "command": command,
        "returncode": completed.returncode,
        "phase_rule": "P raw radians; -j 2pi displays rad/(2*pi) turns only",
    }
    record.update(metadata)
    return record


def page_visible_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace").replace("\\u002f", "/")


def page_qa(page: dict[str, object]) -> list[str]:
    text = page_visible_text(REPO / str(page["output"]))
    failures: list[str] = []
    for label in page["plot_labels"]:
        if str(label) not in text:
            failures.append(f"missing plot label: {label}")
    if str(page["title"]) not in text:
        failures.append("missing title")
    if '"text":"Unknown"' in text or '"title":{"text":"Unknown"' in text:
        failures.append("Unknown axis/label present")
    lower = text.lower()
    if "sfq count" in lower or "event count" in lower:
        failures.append("prohibited count wording present")
    if any(str(label).startswith("P(") for label in page["plot_labels"]):
        if "Phase (turns) [rad/2pi]" not in text:
            failures.append("phase axis lacks rad/(2*pi) label")
    return failures


def qa_window_input(metadata: dict[str, object]) -> list[str]:
    path = REPO / str(metadata["path"])
    _, rows, by_time, _ = load_raw(path)
    declared = [Decimal(item) for item in metadata["declared_window_ps"]]
    actual_times = sorted(by_time)
    failures: list[str] = []
    if metadata["uses_full_raw_as_plot_input"]:
        failures.append("window page uses full raw input")
    if not actual_times:
        return ["window CSV is empty"]
    if str(actual_times[0]) != str(Decimal(metadata["actual_time_start_ps"])):
        failures.append("recorded window start differs from CSV")
    if str(actual_times[-1]) != str(Decimal(metadata["actual_time_last_sample_ps"])):
        failures.append("recorded window last sample differs from CSV")
    if len(rows) != int(metadata["actual_sample_count"]):
        failures.append("recorded window sample count differs from CSV")
    if actual_times[0] < declared[0] or actual_times[-1] >= declared[1]:
        failures.append("CSV samples violate half-open declared window")
    if any(time < declared[0] or time >= declared[1] for time in actual_times):
        failures.append("CSV contains sample outside declared window")
    return failures


def write_run_index(run_id: str, page_names: list[str]) -> dict[str, object]:
    links = "\n".join(
        f'<li><a href="{html.escape(name)}.html">{html.escape(name)}</a></li>'
        for name in page_names
    )
    content = (
        "<!doctype html><meta charset=\"utf-8\">"
        f"<title>{html.escape(run_id)} delta4_v2 evidence</title>"
        f"<h1>{html.escape(run_id)}</h1>"
        "<p>Per-run visualization package. BVM source pages are "
        f"<strong>{html.escape(SOURCE_KIND_BVM)}</strong>.</p>"
        f"<ul>{links}</ul>"
    )
    path = V2_ROOT / run_id / "index.html"
    write_once(path, content + "\n")
    return {"path": rel(path), "sha256": sha256(path), "run_id": run_id}


def write_root_index(run_indexes: list[dict[str, object]]) -> dict[str, object]:
    links = "\n".join(
        f'<li><a href="{html.escape(run_id)}/index.html">{html.escape(run_id)}</a></li>'
        for run_id in RUNS
    )
    content = (
        "<!doctype html><meta charset=\"utf-8\">"
        "<title>delta4_v2 per-run visualization index</title>"
        "<h1>delta4_v2 per-run visualization index</h1>"
        "<p>Each run directory contains source, input, QB, JTL, zoom and "
        "N4 pairwise raw/delta pages.</p>"
        f"<ul>{links}</ul>"
    )
    path = V2_ROOT / "index.html"
    write_once(path, content + "\n")
    return {"path": rel(path), "sha256": sha256(path), "run_count": len(run_indexes)}


def v1_hash_snapshot() -> dict[str, str]:
    return {
        rel(path): sha256(path)
        for path in sorted(V1_ROOT.rglob("*"))
        if path.is_file()
    }


def main() -> int:
    metrics = json.loads((EXP / "analysis/metrics.json").read_text(encoding="utf-8"))
    execution = json.loads((EXP / "analysis/execution_summary.json").read_text(encoding="utf-8"))
    if metrics.get("status") != "PASS" or execution.get("physical_run_count") != 4:
        raise RuntimeError("existing analysis/execution package is not PASS")
    v1_before = v1_hash_snapshot()
    raw_before = raw_hashes()
    pages: list[dict[str, object]] = []
    run_records: dict[str, object] = {}
    for run_id in RUNS:
        run_pages: list[str] = []
        bvm_data = create_bvm_source_csv(run_id)
        bvm_page = render_page(
            run_id,
            "BVM_SOURCE_REFERENCE",
            REPO / bvm_data["path"],
            list(bvm_data["plot_labels"]),
            list(bvm_data["labels"]),
            f"{run_id} | {SOURCE_KIND_BVM} | N3/N4 passive BVM/JSL source context",
            SOURCE_KIND_BVM,
            ["0.0", "199.9"],
            {
                "source_raw_hashes": bvm_data["source_raw_hashes"],
                "source_data": bvm_data,
            },
        )
        pages.append(bvm_page)
        run_pages.append("BVM_SOURCE_REFERENCE")

        input_data = create_input_csv(run_id)
        input_page = render_page(
            run_id,
            "INPUT_COMPONENTS",
            REPO / input_data["path"],
            list(input_data["plot_labels"]),
            list(input_data["labels"]),
            f"{run_id} | input components | N3 background, N4 reference, signed delta4 and I_REPLAY",
            SOURCE_KIND_INPUT,
            ["0.0", "205.9"],
            {"source_data": input_data},
        )
        pages.append(input_page)
        run_pages.append("INPUT_COMPONENTS")

        qb_page = render_page(
            run_id,
            "QB_FULL_INTERNAL",
            RAW_PATHS[run_id],
            list(QB_FULL),
            list(QB_FULL),
            f"{run_id} standalone | QB full internal | raw | FINAL_READ_RESPONSE 110-200 ps",
            "RAW_RUN_DIRECT_STANDALONE",
            ["110.0", "200.0"],
            {"input_raw_direct": True},
        )
        pages.append(qb_page)
        run_pages.append("QB_FULL_INTERNAL")

        jtl_page = render_page(
            run_id,
            "JTL_FULL_CHAIN",
            RAW_PATHS[run_id],
            list(JTL_FULL),
            list(JTL_FULL),
            f"{run_id} standalone | JTL1-JTL6 full chain | raw | DOWNSTREAM_ZOOM 118-180 ps",
            "RAW_RUN_DIRECT_STANDALONE",
            ["118.0", "180.0"],
            {"input_raw_direct": True},
        )
        pages.append(jtl_page)
        run_pages.append("JTL_FULL_CHAIN")

        qb_window = create_windowed_csv(
            run_id,
            "QB_INTERNAL_CRITICAL_ZOOM",
            QB_FULL,
            "QB_INTERNAL_CRITICAL",
            SOURCE_KIND_WINDOWED,
        )
        qb_zoom = render_page(
            run_id,
            "QB_INTERNAL_CRITICAL_ZOOM",
            REPO / qb_window["path"],
            list(qb_window["plot_labels"]),
            list(qb_window["labels"]),
            f"{run_id} | QB_INTERNAL_CRITICAL_ZOOM | complete QB internal raw | 118-140 ps",
            SOURCE_KIND_WINDOWED,
            qb_window["declared_window_ps"],
            {"window_data": qb_window},
        )
        pages.append(qb_zoom)
        run_pages.append("QB_INTERNAL_CRITICAL_ZOOM")

        jtl_window = create_windowed_csv(
            run_id,
            "JTL_DOWNSTREAM_ZOOM",
            JTL_FULL,
            "DOWNSTREAM_ZOOM",
            SOURCE_KIND_WINDOWED,
        )
        jtl_zoom = render_page(
            run_id,
            "JTL_DOWNSTREAM_ZOOM",
            REPO / jtl_window["path"],
            list(jtl_window["plot_labels"]),
            list(jtl_window["labels"]),
            f"{run_id} | JTL_DOWNSTREAM_ZOOM | JTL1-JTL6 full chain raw | 118-180 ps",
            SOURCE_KIND_WINDOWED,
            jtl_window["declared_window_ps"],
            {"window_data": jtl_window},
        )
        pages.append(jtl_zoom)
        run_pages.append("JTL_DOWNSTREAM_ZOOM")

        qb_pair = create_pairwise_csv(
            run_id,
            "N4_VS_RUN_QB_RAW_DELTA",
            QB_FULL,
            "FINAL_READ_RESPONSE",
        )
        qb_pair_page = render_page(
            run_id,
            "N4_VS_RUN_QB_RAW_DELTA",
            REPO / qb_pair["path"],
            list(qb_pair["plot_labels"]),
            list(qb_pair["labels"]),
            f"N4_REPLAY vs {run_id} | QB raw + intervention-minus-N4 delta | FINAL_READ_RESPONSE 110-200 ps",
            SOURCE_KIND_PAIRWISE,
            qb_pair["declared_window_ps"],
            {
                "pairwise_data": qb_pair,
                "phase_delta_provenance": qb_pair["phase_delta_provenance"],
            },
        )
        pages.append(qb_pair_page)
        run_pages.append("N4_VS_RUN_QB_RAW_DELTA")

        jtl_pair = create_pairwise_csv(
            run_id,
            "N4_VS_RUN_JTL_RAW_DELTA",
            JTL_FULL,
            "FINAL_READ_RESPONSE",
        )
        jtl_pair_page = render_page(
            run_id,
            "N4_VS_RUN_JTL_RAW_DELTA",
            REPO / jtl_pair["path"],
            list(jtl_pair["plot_labels"]),
            list(jtl_pair["labels"]),
            f"N4_REPLAY vs {run_id} | JTL1-JTL6 raw + intervention-minus-N4 delta | FINAL_READ_RESPONSE 110-200 ps",
            SOURCE_KIND_PAIRWISE,
            jtl_pair["declared_window_ps"],
            {
                "pairwise_data": jtl_pair,
                "phase_delta_provenance": jtl_pair["phase_delta_provenance"],
            },
        )
        pages.append(jtl_pair_page)
        run_pages.append("N4_VS_RUN_JTL_RAW_DELTA")
        run_records[run_id] = {
            "directory": rel(V2_ROOT / run_id),
            "index": write_run_index(run_id, run_pages),
            "pages": run_pages,
            "raw_path": rel(RAW_PATHS[run_id]),
            "raw_sha256": sha256(RAW_PATHS[run_id]),
        }

    root_index = write_root_index([record["index"] for record in run_records.values()])
    failures: dict[str, list[str]] = {}
    for page in pages:
        page_failures = page_qa(page)
        if page_failures:
            failures[str(page["name"])] = page_failures
        if "window_data" in page:
            window_failures = qa_window_input(page["window_data"])
            if window_failures:
                failures[str(page["name"]) + "_window"] = window_failures
        if "pairwise_data" in page:
            pair = page["pairwise_data"]
            if str(pair["control"]) != "N4_REPLAY":
                failures[str(page["name"]) + "_control"] = ["pairwise control is not N4_REPLAY"]
            for label in pair["labels"]:
                required = (
                    f"{label} | N4_REPLAY | raw |",
                    f"{label} | {page['run_id']} | raw |",
                    f"{label} | {page['run_id']}_MINUS_N4 | derived delta |",
                )
                missing = [
                    item
                    for item in required
                    if not any(item in plot_label for plot_label in page["plot_labels"])
                ]
                if missing:
                    failures.setdefault(str(page["name"]) + "_tracks", []).extend(missing)
            if any(str(label).startswith("P(") for label in pair["labels"]):
                provenance = pair["phase_delta_provenance"]
                if not provenance["wrapped_phase_subtraction"] and "independently unwrap" in provenance["method"]:
                    pass
                else:
                    failures[str(page["name"]) + "_phase"] = ["independent unwrap provenance missing or wrapped subtraction enabled"]
    raw_after = raw_hashes()
    v1_after = v1_hash_snapshot()
    if raw_before != raw_after:
        failures["raw_hash"] = ["raw hash changed during visualization rework"]
    if v1_before != v1_after:
        failures["delta4_v1"] = ["existing delta4_v1 file hash changed"]
    expected_run_pages = {
        "BVM_SOURCE_REFERENCE",
        "INPUT_COMPONENTS",
        "QB_FULL_INTERNAL",
        "JTL_FULL_CHAIN",
        "QB_INTERNAL_CRITICAL_ZOOM",
        "JTL_DOWNSTREAM_ZOOM",
        "N4_VS_RUN_QB_RAW_DELTA",
        "N4_VS_RUN_JTL_RAW_DELTA",
    }
    run_directory_failures = []
    for run_id, record in run_records.items():
        if set(record["pages"]) != expected_run_pages:
            run_directory_failures.append({"run_id": run_id, "pages": record["pages"]})
    if run_directory_failures:
        failures["run_directories"] = run_directory_failures

    window_fidelity = {}
    for page in pages:
        if "window_data" in page:
            fidelity_key = f"{page['run_id']}/{page['name']}"
            window_fidelity[fidelity_key] = {
                "declared_window_ps": page["window_data"]["declared_window_ps"],
                "actual_time_start_ps": page["window_data"]["actual_time_start_ps"],
                "actual_time_last_sample_ps": page["window_data"]["actual_time_last_sample_ps"],
                "actual_sample_count": page["window_data"]["actual_sample_count"],
                "uses_full_raw_as_plot_input": page["window_data"]["uses_full_raw_as_plot_input"],
                "pass": not qa_window_input(page["window_data"]),
            }
    coverage = {
        "four_run_directories": len(run_records) == 4 and not run_directory_failures,
        "pairwise_qb_per_run": all("N4_VS_RUN_QB_RAW_DELTA" in record["pages"] for record in run_records.values()),
        "pairwise_jtl_per_run": all("N4_VS_RUN_JTL_RAW_DELTA" in record["pages"] for record in run_records.values()),
        "critical_window_fidelity": all(
            item["pass"] and item["declared_window_ps"] == ["118.0", "140.0"]
            for name, item in window_fidelity.items()
            if name.endswith("/QB_INTERNAL_CRITICAL_ZOOM")
        ),
        "downstream_window_fidelity": all(
            item["pass"] and item["declared_window_ps"] == ["118.0", "180.0"]
            for name, item in window_fidelity.items()
            if name.endswith("/JTL_DOWNSTREAM_ZOOM")
        ),
        "complete_qb_internal_coverage": all(
            set(page["labels"]) == set(QB_FULL)
            for page in pages
            if page["name"] == "QB_INTERNAL_CRITICAL_ZOOM"
        ),
        "jtl1_to_jtl6_coverage": all(
            all(f"V(JTL{stage}_OUT)" in page["labels"] for stage in range(1, 7))
            and all(f"P(B01|XJTL1_{stage})" in page["labels"] for stage in range(1, 7))
            for page in pages
            if page["name"] in {"JTL_FULL_CHAIN", "JTL_DOWNSTREAM_ZOOM"}
        ),
        "independent_unwrapped_phase_delta_provenance": all(
            "independently unwrap" in page.get("phase_delta_provenance", {}).get("method", "")
            and page.get("phase_delta_provenance", {}).get("wrapped_phase_subtraction") is False
            for page in pages
            if page["name"] in {"N4_VS_RUN_QB_RAW_DELTA", "N4_VS_RUN_JTL_RAW_DELTA"}
        ),
        "source_kind_marker": all(
            SOURCE_KIND_BVM in page["title"]
            and page["source_kind"] == SOURCE_KIND_BVM
            and page["source_raw_hashes"]["N3_PASSIVE"] == EXPECTED_RAW_HASHES["N3_PASSIVE"]
            and page["source_raw_hashes"]["N4_PASSIVE"] == EXPECTED_RAW_HASHES["N4_PASSIVE"]
            for page in pages
            if page["name"] == "BVM_SOURCE_REFERENCE"
        ),
        "raw_hashes_unchanged": raw_before == raw_after,
        "delta4_v1_unchanged": v1_before == v1_after,
        "no_solver_command": all(
            "build/josim-cli" not in " ".join(str(item) for item in page["command"])
            for page in pages
        ),
    }
    if not all(coverage.values()):
        failures["coverage"] = [name for name, passed in coverage.items() if not passed]
    qa = {
        "schema": "jm2-delta4-visualization-qa-v2",
        "experiment_id": EXP.name,
        "head_at_visualization": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip(),
        "status": "PASS" if not failures else "FAIL",
        "plotter": {
            "path": rel(PLOTTER),
            "sha256": sha256(PLOTTER),
            "options": ["sep_comb", "dark", "-j", "2pi"],
        },
        "page_count": len(pages),
        "run_directory_count": len(run_records),
        "run_directories": run_records,
        "root_index": root_index,
        "pages": pages,
        "window_fidelity": window_fidelity,
        "coverage": coverage,
        "raw_hashes_before": raw_before,
        "raw_hashes_after": raw_after,
        "raw_hashes_unchanged": raw_before == raw_after,
        "delta4_v1_hashes_before": v1_before,
        "delta4_v1_hashes_after": v1_after,
        "delta4_v1_unchanged": v1_before == v1_after,
        "failures": failures,
    }
    manifest = {
        "schema": "jm2-delta4-visualization-manifest-v2",
        "experiment_id": EXP.name,
        "head_at_visualization": qa["head_at_visualization"],
        "v1_preserved": True,
        "root_index": root_index,
        "run_directories": run_records,
        "pages": pages,
        "qa": "analysis/viz_qa_v2.json",
    }
    write_once(EXP / "analysis/viz_qa_v2.json", json.dumps(qa, indent=2, ensure_ascii=False) + "\n")
    write_once(EXP / "analysis/visualization_manifest_v2.json", json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    print(
        json.dumps(
            {
                "status": qa["status"],
                "page_count": qa["page_count"],
                "run_directory_count": qa["run_directory_count"],
                "coverage": coverage,
                "raw_hashes_unchanged": qa["raw_hashes_unchanged"],
                "delta4_v1_unchanged": qa["delta4_v1_unchanged"],
                "failures": failures,
            },
            ensure_ascii=False,
        )
    )
    return 0 if qa["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
