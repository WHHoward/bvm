#!/usr/bin/env python3
"""Generate the three focused strict-event plots with the canonical plot2 viewer."""
from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import pandas as pd


HERE = Path(__file__).resolve()
TARGET = HERE.parents[1]
REPO = TARGET.parents[2]
MATRIX = REPO / "test/exploration/bvm-load-qb-matrix-v1-20260901"
RAW = MATRIX / "raw"
PLOTTER = REPO / "scripts/josim-plot2.py"
PLOTS = TARGET / "plots"
DETAILS = TARGET / "analysis/strict-event-details.json"
RECORDED_AT = "2026-09-01T14:56:16+08:00"
WIDTHS = (9, 13)
LOADS = ("12x320", "8x500")
ROLES = ("logical1_read", "logical0_read", "logical1_no_read_control", "logical0_no_read_control")
ROLE_LABELS = {
    "logical1_read": "logical1 READ",
    "logical0_read": "logical0 READ",
    "logical1_no_read_control": "logical1 READ=0",
    "logical0_no_read_control": "logical0 READ=0",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(REPO).as_posix()


def raw_path(fixture: str, width: int, load: str, role: str) -> Path:
    return RAW / fixture / f"{width}ps" / load / role / "run-01.csv"


def read_csv(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    frame.columns = [str(value).strip('"') for value in frame.columns]
    if frame.empty or frame.columns[0] != "time":
        raise ValueError(f"invalid CSV: {path}")
    return frame


def exact_series(frame: pd.DataFrame, name: str, path: Path) -> pd.Series:
    indexes = [index for index, column in enumerate(frame.columns) if column == name]
    if not indexes:
        raise KeyError(f"missing {name!r}: {path}")
    return frame.iloc[:, indexes[0]]


def check_columns(frame: pd.DataFrame, columns: list[str], path: Path) -> None:
    missing = [name for name in columns if name not in frame.columns]
    if missing:
        raise KeyError(f"{path}: missing {missing}")


def run_plot(input_csv: Path, output: Path, title: str, columns: list[str]) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable, str(PLOTTER), str(input_csv),
        "-t", "sep_comb", "-c", "dark", "-j", "2pi",
        "-s", *columns, "-x", str(output), "-w", title,
    ]
    subprocess.run(command, cwd=REPO, check=True)


def detail_index(details: dict[str, Any]) -> dict[tuple[str, int, str, str], dict[str, Any]]:
    return {
        (item["fixture"], item["width_ps"], item["jsl_load"], item["role"]): item
        for item in details["qb_cases"]
    }


def metadata(
    output: Path,
    title: str,
    source_paths: list[Path],
    columns: list[str],
    details: list[dict[str, Any]],
    *,
    input_kind: str,
    derived_sha256: str | None = None,
    derived_annotation_columns: list[str] | None = None,
) -> dict[str, Any]:
    payload = {
        "schema_version": "STRICT_EVENT_JOSIM_PLOT_V1",
        "generated_at": RECORDED_AT,
        "experiment_id": rel(TARGET),
        "plot_id": output.stem,
        "plot_path": rel(output),
        "title": title,
        "generated_from": "scripts/josim-plot2.py",
        "plot_type": "sep_comb",
        "color": "dark",
        "phase_display": "continuous unwrapped P(BJL2|XBQ)/(2pi) in turns; not an SFQ counter",
        "raw_columns": columns,
        "source_paths": [rel(path) for path in source_paths],
        "source_sha256": {rel(path): sha256(path) for path in source_paths},
        "plot_input_kind": input_kind,
        "strict_annotation_source": rel(DETAILS),
        "strict_annotations": [
            {
                "fixture": item["fixture"],
                "width_ps": item["width_ps"],
                "jsl_load": item["jsl_load"],
                "role": item["role"],
                "classification": item["strict_classification"],
                "window_ps": item.get("activity", {}).get("window_ps"),
                "window_phase_delta_turns": item.get("window_phase_displacement", {}).get("delta_turns"),
                "window_first_time_ps": item.get("window_phase_displacement", {}).get("first_time_ps"),
                "window_last_time_ps": item.get("window_phase_displacement", {}).get("last_time_ps"),
                "largest_segment_start_ps": (item.get("largest_monotonic_segment") or {}).get("start_ps"),
                "largest_segment_end_ps": (item.get("largest_monotonic_segment") or {}).get("end_ps"),
                "largest_segment_turns": (item.get("largest_monotonic_segment") or {}).get("delta_turns"),
                "same_segment_area_turns": (item.get("largest_monotonic_segment") or {}).get("area_turns"),
                "complete_segment_count": item.get("activity", {}).get("complete_segment_count"),
                "post_bounded": item.get("post_bounded"),
            }
            for item in details
        ],
        "scientific_authority": "raw evidence and strict-event analysis; visualization is descriptive only",
    }
    if derived_sha256 is not None:
        payload["derived_input_sha256"] = derived_sha256
        payload["derived_input_lifetime"] = "temporary; regenerate from listed raw paths with generate_strict_plots.py"
    if derived_annotation_columns:
        payload["derived_annotation_columns"] = derived_annotation_columns
    payload["output_sha256"] = sha256(output)
    return payload


def add_boundary_annotations(
    frame: pd.DataFrame,
    item: dict[str, Any],
    temp_path: Path,
) -> tuple[Path, list[str]]:
    """Add sparse phase-only guide traces without changing raw samples."""
    base_columns = ["time", "P(BJL2|XBQ)", "V(BJL2|XBQ)", "V(IN)", "V(OUT)", "I(I_REPLAY)", "I(R_LOAD)"]
    check_columns(frame, base_columns, temp_path)
    overlay = pd.DataFrame({name: exact_series(frame, name, temp_path).to_numpy(copy=True) for name in base_columns})
    phase = overlay["P(BJL2|XBQ)"].to_numpy(copy=True)
    time_s = overlay["time"].to_numpy(copy=True)
    phase_min = float(phase.min())
    phase_max = float(phase.max())
    annotation_columns: list[str] = []
    largest = item.get("largest_monotonic_segment") or {}
    boundaries = [
        ("window start", float(item["window_phase_displacement"]["first_time_ps"])),
        ("largest segment start", float(largest.get("start_ps", item["window_phase_displacement"]["first_time_ps"]))),
        ("largest segment end", float(largest.get("end_ps", item["window_phase_displacement"]["last_time_ps"]))),
        ("window end", float(item["window_phase_displacement"]["last_time_ps"])),
    ]
    for label, time_ps in boundaries:
        column = f"P(STRICT marker: {label} {time_ps:.6f} ps)"
        values = pd.Series(float("nan"), index=overlay.index, dtype=float)
        index = int((abs(time_s - time_ps * 1e-12)).argmin())
        if label in {"window start", "largest segment start"}:
            indexes = [index, min(index + 1, len(values) - 1)]
        else:
            indexes = [max(index - 1, 0), index]
        values.iloc[indexes[0]] = phase_min
        values.iloc[indexes[1]] = phase_max
        overlay[column] = values
        annotation_columns.append(column)
    overlay.to_csv(temp_path, index=False)
    return temp_path, annotation_columns


def direct_event_plot(
    details_index: dict[tuple[str, int, str, str], dict[str, Any]],
    width: int,
    load: str,
    output_name: str,
) -> dict[str, Any]:
    fixture = "replay"
    role = "logical1_read"
    source = raw_path(fixture, width, load, role)
    item = details_index[(fixture, width, load, role)]
    largest = item.get("largest_monotonic_segment") or {}
    title = (
        f"Ideal replay → scaled QB — {width} ps / {load} / logical1 READ — "
        f"BJL2 strict trajectory; segment {largest.get('start_ps', float('nan')):.4g}–{largest.get('end_ps', float('nan')):.4g} ps"
    )
    columns = ["P(BJL2|XBQ)", "V(BJL2|XBQ)", "V(IN)", "V(OUT)", "I(I_REPLAY)", "I(R_LOAD)"]
    frame = read_csv(source)
    check_columns(frame, columns, source)
    output = PLOTS / output_name
    with tempfile.TemporaryDirectory(prefix="strict-event-overlay-") as temp_dir:
        derived = Path(temp_dir) / "event-overlay.csv"
        _derived, annotation_columns = add_boundary_annotations(frame, item, derived)
        derived_hash = sha256(derived)
        plot_columns = columns + annotation_columns
        run_plot(derived, output, title, plot_columns)
    return metadata(
        output,
        title,
        [source],
        columns,
        [item],
        input_kind="temporary_derived_event_overlay_csv",
        derived_sha256=derived_hash,
        derived_annotation_columns=annotation_columns,
    )


def matrix_plot(details_index: dict[tuple[str, int, str, str], dict[str, Any]]) -> dict[str, Any]:
    cases: list[tuple[str, Path, dict[str, Any]]] = []
    for fixture in ("replay", "physical"):
        for width in WIDTHS:
            for load in LOADS:
                role = "logical1_read"
                path = raw_path(fixture, width, load, role)
                label = f"{fixture} · {width} ps · {load}"
                cases.append((label, path, details_index[(fixture, width, load, role)]))

    raw_columns = ["P(BJL2|XBQ)", "V(BJL2|XBQ)", "V(OUT)"]
    frames = [(label, path, item, read_csv(path)) for label, path, item in cases]
    reference_time = frames[0][3].iloc[:, 0]
    merged = pd.DataFrame({"time": reference_time.to_numpy(copy=True)})
    output_columns: list[str] = []
    for label, path, _item, frame in frames:
        if not frame.iloc[:, 0].equals(reference_time):
            raise ValueError(f"time grid mismatch: {path}")
        check_columns(frame, raw_columns, path)
        for raw_name in raw_columns:
            kind = raw_name[0]
            short = {"P(BJL2|XBQ)": "BJL2 phase", "V(BJL2|XBQ)": "BJL2 voltage", "V(OUT)": "VOUT"}[raw_name]
            derived_name = f"{kind}({label} · {short})"
            merged[derived_name] = exact_series(frame, raw_name, path).to_numpy(copy=True)
            output_columns.append(derived_name)
    with tempfile.TemporaryDirectory(prefix="strict-event-plot-") as temp_dir:
        derived = Path(temp_dir) / "strict-event-matrix.csv"
        merged.to_csv(derived, index=False)
        derived_hash = sha256(derived)
        output = PLOTS / "strict-event-matrix.html"
        title = "BJL2 strict-event matrix — logical1 READ; ideal replay and physical four-point raw trajectories"
        run_plot(derived, output, title, output_columns)
    return metadata(
        output,
        title,
        [path for _label, path, _item in cases],
        raw_columns,
        [item for _label, _path, item in cases],
        input_kind="temporary_derived_comparison_csv",
        derived_sha256=derived_hash,
    )


def main() -> None:
    details = json.loads(DETAILS.read_text(encoding="utf-8"))
    index = detail_index(details)
    PLOTS.mkdir(parents=True, exist_ok=True)
    pages = [
        direct_event_plot(index, 9, "12x320", "9ps-12x320-replay-bjl2-strict-event.html"),
        direct_event_plot(index, 13, "12x320", "13ps-12x320-replay-bjl2-strict-event.html"),
        matrix_plot(index),
    ]
    for page in pages:
        output = REPO / page["plot_path"]
        page["output_sha256"] = sha256(output)
        metadata_path = output.with_suffix(".metadata.json")
        metadata_path.write_text(json.dumps(page, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (TARGET / "analysis" / "plot-hashes.json").write_text(json.dumps({
        "document_type": "strict_event_plot_hashes",
        "generated_at": RECORDED_AT,
        "renderer": "scripts/josim-plot2.py",
        "plots": [
            {"path": page["plot_path"], "sha256": page["output_sha256"], "input_kind": page["plot_input_kind"], "derived_input_sha256": page.get("derived_input_sha256")}
            for page in pages
        ],
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (PLOTS / "README.md").write_text("\n".join([
        "# Strict BJL2 event plots",
        "",
        "三张图均由 `scripts/josim-plot2.py` 生成，使用 `sep_comb`、dark theme、`-j 2pi`；相位轴是连续相位 turns，不是 SFQ 计数。",
        "",
        "- [9 ps / 12x320 ideal replay BJL2 strict event](9ps-12x320-replay-bjl2-strict-event.html)",
        "- [13 ps / 12x320 ideal replay BJL2 strict event](13ps-12x320-replay-bjl2-strict-event.html)",
        "- [Strict-event matrix: four ideal replay + four physical logical1 READ](strict-event-matrix.html)",
        "",
        "前两张直接读取对应 raw CSV，并在 metadata 中记录 window displacement、最大单调段的 start/end、同段面积和分类。矩阵图只显示八个 logical1 READ case 的 BJL2 phase/voltage 与 VOUT 关键轨迹；四种 role 的完整 strict 数值仍以 `analysis/strict-event-summary.csv` 为准。",
        "",
        "图是描述性证据，不替代同段 phase/area、控制和 post boundedness 审计。",
        "",
    ]), encoding="utf-8")
    print(json.dumps({"status": "PASS", "pages": [page["plot_path"] for page in pages]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
