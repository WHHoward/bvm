#!/usr/bin/env python3
"""Render and QA the four-run delta4 visualization evidence pack."""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
from decimal import Decimal
from pathlib import Path


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
PLOTTER = REPO / "scripts/josim-plot2.py"
RUNS = (
    "DELTA4_DELAY_3PS",
    "DELTA4_DELAY_6PS",
    "DELTA4_GAIN_1P25",
    "DELTA4_GAIN_1P50",
)
CASES = ("N3_REPLAY", "N4_REPLAY") + RUNS
OLD = REPO / "test/exploration/bvmsim-jm2-read-count-passive-replay-v1-20260907"
RAW_PATHS = {
    "N3_REPLAY": OLD / "runs/n3_replay/raw.csv",
    "N4_REPLAY": OLD / "runs/n4_replay/raw.csv",
    **{run_id: EXP / "runs" / run_id / "raw.csv" for run_id in RUNS},
}
PLOT_DIR = EXP / "plots/delta4_v1"
DATA_DIR = PLOT_DIR / "data"
MANIFEST_PATH = EXP / "analysis/visualization_manifest.json"
QA_PATH = EXP / "analysis/viz_qa.json"
SOURCE_RECON_PATH = EXP / "analysis/source_reconstruction.json"

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
QB_COMPARISON = (
    "I(I_REPLAY)",
    "V(QBIN)",
    "V(BJS|XBQ1)",
    "V(BJ1|XBQ1)",
    "V(BJ2|XBQ1)",
    "V(QBOUT)",
    "P(BJ1|XBQ1)",
    "P(BJ2|XBQ1)",
)
JTL_COMPARISON = tuple(f"V(JTL{stage}_OUT)" for stage in range(1, 7)) + (
    "I(R_TERM)",
    "P(B01|XJTL1_1)",
    "P(B01|XJTL1_6)",
)
QB_ZOOM = (
    "I(I_REPLAY)",
    "V(QBIN)",
    "V(BJS|XBQ1)",
    "V(BJ1|XBQ1)",
    "V(BJ2|XBQ1)",
    "V(QBOUT)",
    "P(BJ1|XBQ1)",
    "P(BJ2|XBQ1)",
)
JTL_ZOOM = ("V(QBOUT)",) + tuple(f"V(JTL{stage}_OUT)" for stage in range(1, 7)) + ("I(R_TERM)",)


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


def load_raw(path: Path) -> tuple[list[str], dict[Decimal, dict[str, str]], dict[Decimal, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        fields = list(reader.fieldnames or [])
        rows = list(reader)
    if not fields or fields[0] != "time":
        raise RuntimeError(f"raw input must start with time: {path}")
    by_time: dict[Decimal, dict[str, str]] = {}
    time_tokens: dict[Decimal, str] = {}
    for row in rows:
        time_ps = Decimal(row["time"]) * Decimal("1e12")
        if time_ps in by_time:
            raise RuntimeError(f"duplicate raw timestamp: {path} {time_ps}")
        by_time[time_ps] = row
        time_tokens[time_ps] = row["time"]
    return fields, by_time, time_tokens


def label_unit(label: str) -> str:
    if label.startswith("P("):
        return "raw rad"
    if label.startswith("V("):
        return "V"
    return "A"


def label_display(label: str) -> str:
    if label.startswith("P("):
        return label + " [raw rad]"
    return label


def merged_csv(
    name: str,
    labels: tuple[str, ...],
    cases: tuple[str, ...],
    bounds_ps: tuple[float, float],
    *,
    source_kind: str,
) -> dict[str, object]:
    loaded = {case: load_raw(RAW_PATHS[case]) for case in cases}
    fields = {
        case: loaded[case][0]
        for case in cases
    }
    missing = {
        case: [label for label in labels if label not in fields[case][1:]]
        for case in cases
    }
    if any(missing.values()):
        raise RuntimeError(f"{name}: missing comparison labels {missing}")
    common_times = set(loaded[cases[0]][1])
    for case in cases[1:]:
        common_times &= set(loaded[case][1])
    start = Decimal(str(bounds_ps[0]))
    end = Decimal(str(bounds_ps[1]))
    times = sorted(time for time in common_times if start <= time < end)
    if len(times) < 2:
        raise RuntimeError(f"{name}: fewer than two exact common-grid samples")
    header = ["time"]
    for case in cases:
        for label in labels:
            header.append(
                f"{label} | {case} | raw | {label_unit(label)} | {source_kind}"
            )
    rows: list[list[str]] = []
    for time_ps in times:
        row = [loaded[cases[0]][2][time_ps]]
        for case in cases:
            values = loaded[case][1][time_ps]
            for label in labels:
                row.append(values[label])
        rows.append(row)
    path = DATA_DIR / f"{name}.csv"
    content_lines = [",".join(header)]
    content_lines.extend(",".join(row) for row in rows)
    write_once(path, "\n".join(content_lines) + "\n")
    return {
        "path": path.relative_to(REPO).as_posix(),
        "sha256": sha256(path),
        "cases": list(cases),
        "labels": list(labels),
        "plot_labels": header[1:],
        "window_ps": list(bounds_ps),
        "sample_count": len(rows),
        "time_grid_policy": "exact timestamp intersection; no interpolation or resampling",
        "source_kind": source_kind,
    }


def source_component_csv() -> dict[str, object]:
    return source_component_csv_fixed()


def source_component_csv_fixed() -> dict[str, object]:
    paths = {run_id: EXP / "data" / f"{run_id}_source.csv" for run_id in RUNS}
    loaded = {}
    for run_id, path in paths.items():
        with path.open(newline="", encoding="utf-8") as handle:
            loaded[run_id] = list(csv.DictReader(handle))
    header_specs: list[tuple[str, str, str, str]] = [
        ("I(I_N3_BACKGROUND)", "N3 background", "I_N3_BACKGROUND_A", RUNS[0]),
        ("I(delta_I4_BASE)", "base delta at lookup", "delta_I4_BASE_AT_LOOKUP_A", RUNS[0]),
    ]
    for run_id in RUNS:
        header_specs.extend(
            [
                (f"I(delta_I4_COMPONENT_{run_id})", run_id + " delta component", "delta_I4_COMPONENT_A", run_id),
                (f"I(I_REPLAY_{run_id})", run_id + " replay input", "I_REPLAY_A", run_id),
            ]
        )
    header = ["time"] + [
        f"{label} | {case} | derived | A | DELTA4_SOURCE_COMPONENTS"
        for label, case, _, _ in header_specs
    ]
    rows: list[list[str]] = []
    for index in range(len(loaded[RUNS[0]])):
        time_ps = loaded[RUNS[0]][index]["time_ps"]
        row = [f"{Decimal(time_ps) * Decimal('1e-12'):.12e}"]
        for _, _, key, source_run in header_specs:
            row.append(loaded[source_run][index][key])
        rows.append(row)
    path = DATA_DIR / "DELTA4_SOURCE_COMPONENTS.csv"
    content_lines = [",".join(header)]
    content_lines.extend(",".join(row) for row in rows)
    write_once(path, "\n".join(content_lines) + "\n")
    return {
        "path": path.relative_to(REPO).as_posix(),
        "sha256": sha256(path),
        "labels": header[1:],
        "window_ps": [0.0, 206.0],
        "sample_count": len(rows),
        "source_kind": "derived source/transformation component",
    }


def render_page(name: str, input_path: Path, labels: tuple[str, ...], title: str, source_kind: str, window_ps: tuple[float, float]) -> dict[str, object]:
    output_path = PLOT_DIR / f"{name}.html"
    if output_path.exists():
        raise RuntimeError(f"refusing to overwrite existing visualization: {output_path}")
    PLOT_DIR.mkdir(parents=True, exist_ok=True)
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
        *labels,
    ]
    completed = subprocess.run(command, cwd=REPO, text=True, capture_output=True)
    if completed.returncode != 0:
        raise RuntimeError(f"{name}: plotter failed: {completed.stderr[-1200:]}")
    if not output_path.is_file() or output_path.stat().st_size == 0:
        raise RuntimeError(f"{name}: plotter produced no HTML")
    return {
        "name": name,
        "output": output_path.relative_to(REPO).as_posix(),
        "output_sha256": sha256(output_path),
        "output_bytes": output_path.stat().st_size,
        "input": input_path.relative_to(REPO).as_posix(),
        "input_sha256": sha256(input_path),
        "labels": list(labels),
        "title": title,
        "source_kind": source_kind,
        "window_ps": list(window_ps),
        "command": command,
        "returncode": completed.returncode,
        "phase_rule": "P raw radians; -j 2pi displays turns only",
    }


def qa_html(page: dict[str, object]) -> list[str]:
    path = REPO / str(page["output"])
    text = path.read_text(encoding="utf-8", errors="replace")
    visible = text.replace("\\u002f", "/")
    failures: list[str] = []
    for label in page["labels"]:
        rendered = str(label)
        if rendered not in visible and str(label) not in visible:
            failures.append(f"missing label {rendered}")
    if str(page["title"]) not in visible:
        failures.append("missing title")
    if '"text":"Unknown"' in visible or '"title":{"text":"Unknown"' in visible:
        failures.append("Unknown axis/label present")
    lower = visible.lower()
    if "sfq count" in lower or "event count" in lower:
        failures.append("prohibited count wording present")
    if any(str(label).startswith("P(") for label in page["labels"]) and "Phase (turns) [rad/2pi]" not in visible:
        failures.append("phase page lacks rad/(2*pi) display label")
    return failures


def main() -> int:
    metrics_path = EXP / "analysis/metrics.json"
    execution_path = EXP / "analysis/execution_summary.json"
    if not metrics_path.is_file() or not execution_path.is_file():
        raise RuntimeError("metrics and execution summary are required before rendering")
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    execution = json.loads(execution_path.read_text(encoding="utf-8"))
    if metrics.get("status") != "PASS" or execution.get("physical_run_count") != 4:
        raise RuntimeError("analysis/execution status is not ready for visualization")
    raw_before = {case: sha256(path) for case, path in RAW_PATHS.items()}
    pages: list[dict[str, object]] = []
    standalone_qb: dict[str, str] = {}
    standalone_jtl: dict[str, str] = {}
    for run_id in RUNS:
        qb_name = f"{run_id}_QB_FULL_INTERNAL"
        jtl_name = f"{run_id}_JTL_FULL_CHAIN"
        standalone_qb[run_id] = qb_name
        standalone_jtl[run_id] = jtl_name
        pages.append(
            render_page(
                qb_name,
                RAW_PATHS[run_id],
                QB_FULL,
                f"{run_id} standalone | QB full internal | raw | FINAL_READ_RESPONSE 110-200 ps",
                "raw direct standalone",
                (110.0, 200.0),
            )
        )
        pages.append(
            render_page(
                jtl_name,
                RAW_PATHS[run_id],
                JTL_FULL,
                f"{run_id} standalone | JTL1-JTL6 full chain | raw | DOWNSTREAM_ZOOM 118-180 ps",
                "raw direct standalone",
                (118.0, 180.0),
            )
        )

    source_page_data = source_component_csv_fixed()
    pages.append(
        render_page(
            "DELTA4_SOURCE_COMPONENTS",
            REPO / source_page_data["path"],
            tuple(source_page_data["labels"]),
            "DELTA4 source components | N3 background, N4 background, signed delta4 and four registered transforms",
            "derived source/transformation component",
            (0.0, 206.0),
        )
    )
    qb_comparison = merged_csv(
        "CONTROLS_VS_INTERVENTIONS_QB",
        QB_COMPARISON,
        CASES,
        (110.0, 200.0),
        source_kind="control/intervention raw comparison",
    )
    jtl_comparison = merged_csv(
        "CONTROLS_VS_INTERVENTIONS_JTL",
        JTL_COMPARISON,
        CASES,
        (110.0, 200.0),
        source_kind="control/intervention raw comparison",
    )
    critical = merged_csv(
        "QB_INTERNAL_CRITICAL_ZOOM_118_140",
        QB_ZOOM,
        CASES,
        (118.0, 140.0),
        source_kind="QB internal critical raw comparison",
    )
    downstream = merged_csv(
        "JTL_DOWNSTREAM_ZOOM_118_180",
        JTL_ZOOM,
        CASES,
        (118.0, 180.0),
        source_kind="JTL downstream raw comparison",
    )
    pages.extend(
        [
            render_page(
                "CONTROLS_VS_INTERVENTIONS_QB",
                REPO / qb_comparison["path"],
                tuple(qb_comparison["plot_labels"]),
                "N3/N4 controls vs DELTA4 delay/gain interventions | QB raw comparison | FINAL_READ_RESPONSE 110-200 ps",
                "control/intervention raw comparison",
                (110.0, 200.0),
            ),
            render_page(
                "CONTROLS_VS_INTERVENTIONS_JTL",
                REPO / jtl_comparison["path"],
                tuple(jtl_comparison["plot_labels"]),
                "N3/N4 controls vs DELTA4 delay/gain interventions | JTL1-JTL6 raw comparison | FINAL_READ_RESPONSE 110-200 ps",
                "control/intervention raw comparison",
                (110.0, 200.0),
            ),
            render_page(
                "QB_INTERNAL_CRITICAL_ZOOM_118_140",
                REPO / critical["path"],
                tuple(critical["plot_labels"]),
                "DELTA4 QB internal critical zoom | controls and four interventions | 118-140 ps",
                "QB internal critical raw comparison",
                (118.0, 140.0),
            ),
            render_page(
                "JTL_DOWNSTREAM_ZOOM_118_180",
                REPO / downstream["path"],
                tuple(downstream["plot_labels"]),
                "DELTA4 JTL downstream zoom | controls and four interventions | 118-180 ps",
                "JTL downstream raw comparison",
                (118.0, 180.0),
            ),
        ]
    )
    page_failures: dict[str, list[str]] = {}
    for page in pages:
        failures = qa_html(page)
        if failures:
            page_failures[str(page["name"])] = failures
    raw_after = {case: sha256(path) for case, path in RAW_PATHS.items()}
    if raw_before != raw_after:
        page_failures["raw_hash"] = ["raw hash changed during rendering"]
    coverage = {
        "standalone_qb_per_run": all(name in {page["name"] for page in pages} for name in standalone_qb.values()),
        "standalone_jtl_per_run": all(name in {page["name"] for page in pages} for name in standalone_jtl.values()),
        "qb_full_internal_labels": all(
            all(label in page["labels"] for label in QB_FULL)
            for page in pages
            if str(page["name"]).endswith("_QB_FULL_INTERNAL")
        ),
        "jtl_full_chain_all_stages": all(
            all(f"V(JTL{stage}_OUT)" in page["labels"] for stage in range(1, 7))
            and all(f"P(B01|XJTL1_{stage})" in page["labels"] for stage in range(1, 7))
            for page in pages
            if str(page["name"]).endswith("_JTL_FULL_CHAIN")
        ),
        "comparison_contains_all_cases": all(
            all(any(f"| {case} |" in label for label in page["labels"]) for case in CASES)
            for page in pages
            if str(page["name"]).startswith("CONTROLS_VS_INTERVENTIONS")
        ),
    }
    failures = list(page_failures)
    if not all(coverage.values()):
        failures.append("visualization coverage check failed")
    record = {
        "schema": "jm2-delta4-visualization-qa-v1",
        "experiment_id": EXP.name,
        "status": "PASS" if not failures else "FAIL",
        "renderer": {
            "path": PLOTTER.relative_to(REPO).as_posix(),
            "sha256": sha256(PLOTTER),
            "plot_type": "sep_comb",
            "color": "dark",
            "phase_jump": "2pi",
        },
        "raw_hashes_before": raw_before,
        "raw_hashes_after": raw_after,
        "raw_unchanged": raw_before == raw_after,
        "pages": pages,
        "source_component_data": source_page_data,
        "comparison_data": {
            "QB": qb_comparison,
            "JTL": jtl_comparison,
            "QB_INTERNAL_CRITICAL": critical,
            "JTL_DOWNSTREAM": downstream,
        },
        "coverage": coverage,
        "standalone_pages_pass": not any(
            name.endswith("_QB_FULL_INTERNAL") or name.endswith("_JTL_FULL_CHAIN")
            for name in page_failures
        ),
        "page_count": len(pages),
        "critical_zoom_present": "QB_INTERNAL_CRITICAL_ZOOM_118_140" not in page_failures,
        "jtl_zoom_present": "JTL_DOWNSTREAM_ZOOM_118_180" not in page_failures,
        "phase_rule": "P raw radians; each raw case remains independently represented; -j 2pi displays turns; no SFQ count semantics",
        "visualization_is_descriptive": True,
        "failures": page_failures,
        "source_reconstruction_reference": {
            "path": SOURCE_RECON_PATH.relative_to(REPO).as_posix(),
            "sha256": sha256(SOURCE_RECON_PATH),
        },
    }
    write_once(QA_PATH, json.dumps(record, indent=2, ensure_ascii=False) + "\n")
    manifest = {
        "schema": "jm2-delta4-visualization-manifest-v1",
        "experiment_id": EXP.name,
        "head": metrics["head"],
        "controls": ["N3_REPLAY", "N4_REPLAY"],
        "interventions": list(RUNS),
        "pages": pages,
        "data": [source_page_data, qb_comparison, jtl_comparison, critical, downstream],
        "qa": QA_PATH.relative_to(REPO).as_posix(),
    }
    write_once(MANIFEST_PATH, json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    print(
        json.dumps(
            {
                "status": record["status"],
                "page_count": len(pages),
                "standalone_pages_pass": record["standalone_pages_pass"],
                "critical_zoom_present": record["critical_zoom_present"],
                "jtl_zoom_present": record["jtl_zoom_present"],
                "raw_unchanged": record["raw_unchanged"],
                "failures": page_failures,
            },
            ensure_ascii=False,
        )
    )
    return 0 if record["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
