#!/usr/bin/env python3
"""Build focused HTML views for the BVM/JSL/QB matrix.

The raw CSV files remain the evidence source.  Each derived CSV contains only
the small set of selected traces needed for one case page, and every page has
an adjacent provenance metadata file.
"""
from __future__ import annotations

import csv
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[2]
RAW = ROOT / "raw"
PLOTS = ROOT / "plots"
DERIVED = ROOT / "analysis" / "derived_inputs"
PLOTTER = REPO / "scripts" / "josim-plot2.py"
ROLES = (
    "logical1_read",
    "logical0_read",
    "logical1_no_read_control",
    "logical0_no_read_control",
)
ROLE_SHORT = {
    "logical1_read": "read1",
    "logical0_read": "read0",
    "logical1_no_read_control": "read1_no_read",
    "logical0_no_read_control": "read0_no_read",
}


def write_exact(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_text(encoding="utf-8") != text:
            if PLOTS in path.parents or DERIVED in path.parents:
                path.write_text(text, encoding="utf-8")
                return
            raise SystemExit(f"refusing to overwrite non-identical visualization artifact: {path}")
        return
    path.write_text(text, encoding="utf-8")


def read_selected(path: Path, wanted: list[str]) -> tuple[list[str], list[list[float]], dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        header = [item.strip() for item in next(reader)]
        selected_indices: dict[str, int] = {}
        actual_names: dict[str, str] = {}
        for name in wanted:
            exact = [index for index, candidate in enumerate(header) if candidate == name]
            if not exact:
                folded = name.casefold()
                exact = [
                    index for index, candidate in enumerate(header)
                    if candidate.casefold() == folded
                ]
            if not exact:
                raise KeyError(f"missing plot column {name!r} in {path}")
            selected_indices[name] = exact[0]
            actual_names[name] = header[exact[0]]
        rows: list[list[float]] = []
        for row in reader:
            if row:
                rows.append(
                    [float(row[0])]
                    + [float(row[selected_indices[name]]) for name in wanted]
                )
    if not rows:
        raise ValueError(f"empty plot source: {path}")
    return header, rows, actual_names


def selected_series(
    raw_paths: dict[str, Path],
    specs: list[tuple[str, str]],
) -> tuple[list[float], list[str], dict[str, dict[str, str]]]:
    wanted = [wanted_name for _, wanted_name in specs]
    output_names = [output_name for output_name, _ in specs]
    output: list[list[float]] | None = None
    provenance: dict[str, dict[str, str]] = {}
    for role in ROLES:
        _, rows, actual = read_selected(raw_paths[role], wanted)
        if output is None:
            output = [[row[0]] for row in rows]
        if len(output) != len(rows):
            raise ValueError(f"different sample count for plot role {role}")
        for row_index, row in enumerate(rows):
            for output_name, wanted_name in specs:
                column_index = wanted.index(wanted_name) + 1
                output[row_index].append(row[column_index])
                provenance[f"{output_name}_{ROLE_SHORT[role]}"] = {
                    "raw": raw_paths[role].relative_to(ROOT).as_posix(),
                    "requested_column": wanted_name,
                    "actual_column": actual[wanted_name],
                }
    # The initial implementation above appends the same provenance key for
    # each row; its final value is intentional.  Rename the generated columns
    # below in the same order as the row data.
    columns = ["time"]
    for output_name, _ in specs:
        for role in ROLES:
            columns.append(f"{output_name}_{ROLE_SHORT[role]}")
    return [row[0] for row in output or []], [columns] + (output or []), provenance


def write_derived(
    path: Path,
    time_and_rows: list[list[float]],
) -> None:
    from io import StringIO

    buffer = StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(time_and_rows[0])
    for row in time_and_rows[1:]:
        writer.writerow([f"{value:.17g}" for value in row])
    write_exact(path, buffer.getvalue())


def run_plot(derived: Path, html: Path, title: str) -> None:
    command = [
        sys.executable,
        str(PLOTTER),
        str(derived),
        "-x", str(html),
        "-t", "sep_comb",
        "-c", "light",
        "-j", "2pi",
        "-w", title,
    ]
    result = subprocess.run(command, cwd=REPO, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        raise SystemExit(
            f"plotter failed for {derived}: returncode={result.returncode}\n"
            f"stdout={result.stdout}\nstderr={result.stderr}"
        )


def specs_for(kind: str, count: int) -> list[tuple[str, str]]:
    if kind == "source":
        return [
            ("I(SL_current)", "I(L_SL|XBVM1)"),
            ("I(JSL_first)", "I(B_LD1)"),
            ("I(JSL_last)", f"I(B_LD{count})"),
            ("I(READ_WL)", "I(I_WL1)"),
            ("I(READ_SE)", "I(I_SE1)"),
            ("V(SL1)", "V(SL1)"),
            ("V(BVM_node)", "V(N6|XBVM1)"),
            ("P(storage_JM1)", "P(B_JM1|XBVM1)"),
            ("P(storage_JS1)", "P(B_JS1|XBVM1)"),
            ("P(JSL_last)", f"P(B_LD{count})"),
        ]
    if kind in {"physical", "replay"}:
        input_current = "I(Lin|XBQ)" if kind == "physical" else "I(I_REPLAY)"
        specs = [
            ("I(QB_input)", input_current),
            ("V(QB_IN)", "V(IN)"),
            ("P(BJs)", "P(BJs|XBQ)"),
            ("P(BJL1)", "P(BJL1|XBQ)"),
            ("P(BJL2)", "P(BJL2|XBQ)"),
            ("I(BJs)", "I(BJs|XBQ)"),
            ("I(BJL1)", "I(BJL1|XBQ)"),
            ("I(BJL2)", "I(BJL2|XBQ)"),
            ("I(QB_L0)", "I(L0|XBQ)"),
            ("I(QB_L1)", "I(L1|XBQ)"),
            ("I(QB_L2)", "I(L2|XBQ)"),
            ("I(QB_RB)", "I(RB|XBQ)"),
            ("I(QB_RJ1)", "I(RJ1|XBQ)"),
            ("I(QB_RJ2)", "I(RJ2|XBQ)"),
            ("V(QB_OUT)", "V(OUT)"),
            ("I(R_LOAD)", "I(R_LOAD)"),
        ]
        if kind == "physical":
            specs[1:1] = [
                ("I(JSL_first)", "I(B_LD1)"),
                ("I(JSL_last)", "I(B_LD12)" if count == 12 else "I(B_LD8)"),
                ("I(READ_WL)", "I(I_WL1)"),
                ("I(READ_SE)", "I(I_SE1)"),
                ("I(SL_current)", "I(L_SL|XBVM1)"),
                ("V(SL1)", "V(SL1)"),
                ("V(BVM_node)", "V(N6|XBVM1)"),
                ("P(storage_JM1)", "P(B_JM1|XBVM1)"),
                ("P(storage_JS1)", "P(B_JS1|XBVM1)"),
            ]
        return specs
    raise ValueError(kind)


def page_readme_entry(page: str, title: str, kind: str, derived: str) -> str:
    return f"- [{title}]({page}) — `{kind}`；精简关键轨迹，输入文件 `{derived}`。"


def main() -> None:
    manifest = json.loads((ROOT / "manifest.yaml").read_text(encoding="utf-8"))
    PLOTS.mkdir(parents=True, exist_ok=True)
    DERIVED.mkdir(parents=True, exist_ok=True)
    entries: list[str] = []
    metadata_index: list[dict[str, Any]] = []
    for width_ps in (9, 13):
        for load_name, load in manifest["loads"].items():
            count = int(load["count"])
            for kind in ("source", "physical", "replay"):
                raw_paths = {
                    role: RAW / kind / f"{width_ps}ps" / load_name / role / "run-01.csv"
                    for role in ROLES
                }
                specs = specs_for(kind, count)
                _, rows, provenance = selected_series(raw_paths, specs)
                slug = f"{width_ps}ps-{load_name}-{kind}-key"
                derived = DERIVED / f"{slug}.csv"
                html = PLOTS / f"{slug}.html"
                metadata_path = PLOTS / f"{slug}.metadata.json"
                write_derived(derived, rows)
                title = f"BVM/JSL/QB {kind} | {width_ps} ps | {load_name}"
                run_plot(derived, html, title)
                metadata = {
                    "schema_version": "BVM_LOAD_QB_MATRIX_PLOT_V1",
                    "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
                    "plot_id": slug,
                    "kind": kind,
                    "width_ps": width_ps,
                    "load": load_name,
                    "roles": list(ROLES),
                    "renderer": "scripts/josim-plot2.py",
                    "plot_type": "sep_comb",
                    "phase_semantics": "continuous_absolute",
                    "fixture_role": {
                        "source": "SOURCE_REFERENCE",
                        "physical": "RESULT",
                        "replay": "IDEAL_REPLAY_REFERENCE",
                    }[kind],
                    "phase_display": "P columns are displayed as P/(2*pi) continuous phase turns; not an SFQ counter",
                    "raw_evidence": False,
                    "raw_sources": {
                        role: raw_paths[role].relative_to(ROOT).as_posix() for role in ROLES
                    },
                    "derived_input": derived.relative_to(ROOT).as_posix(),
                    "requested_columns": {
                        output_name: requested for output_name, requested in specs
                    },
                    "column_provenance": provenance,
                }
                write_exact(metadata_path, json.dumps(metadata, ensure_ascii=False, indent=2) + "\n")
                entries.append(page_readme_entry(
                    html.relative_to(ROOT).as_posix(), title, kind,
                    derived.relative_to(ROOT).as_posix(),
                ))
                metadata_index.append(metadata)
    readme = "\n".join([
        "# BVM_LOAD_QB_MATRIX_V1 关键可视化",
        "",
        "这些页面是描述性可视化，不是物理 Gate。原始 CSV 位于 `raw/`；",
        "每个页面旁边的 `.metadata.json` 记录原始输入和选取的列。",
        "",
        "## 12 个聚焦页面",
        "",
        *entries,
        "",
        "## 读图说明",
        "",
        "- source 页：看 BVM SL 电流、首末 JSL 电流、BVM 节点和末级 JSL 相位。",
        "- physical 页：看 QB 输入、BJs→BJL1→BJL2 相位轨迹和 `V(OUT)`/`I(R_LOAD)`。",
        "- replay 页：看同一源波形直接驱动 QB 时的对应输入和输出。",
        "- P 图只把原始 rad 乘以 `1/(2*pi)` 显示为 continuous phase turns；不能直接当作 SFQ 事件数。",
        "- 需要定量结论时回到 `analysis/metrics.json` 和原始 CSV，不从图形单独判定事件。",
        "",
    ])
    write_exact(PLOTS / "README.md", readme)
    write_exact(PLOTS / "index.json", json.dumps({
        "schema_version": "BVM_LOAD_QB_MATRIX_PLOT_INDEX_V1",
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "plots": metadata_index,
    }, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({
        "status": "PASS",
        "pages": len(metadata_index),
        "readme": "plots/README.md",
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
