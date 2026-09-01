#!/usr/bin/env python3
"""Generate the classic JoSIM waveform views for this exploration.

The renderer follows the repository's established scheme: raw CSVs are used
directly for independent case pages, while focused comparison pages are built
from temporary merged CSVs. Every final HTML page is rendered by
``scripts/josim-plot2.py`` with the standard ``sep_comb``/dark/``-j 2pi``
settings. No JoSIM simulation is run here and no raw evidence is modified.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[2]
PLOTTER = REPO / "scripts" / "josim-plot2.py"
PLOT_DIR = ROOT / "plots"
WIDTHS = (9, 13)
LOADS = {
    "12x320": {"count": 12, "ic_uA": 320},
    "8x500": {"count": 8, "ic_uA": 500},
}
ROLES = (
    "logical1_read",
    "logical0_read",
    "logical1_no_read_control",
    "logical0_no_read_control",
)
ROLE_LABELS = {
    "logical1_read": "logical1 READ",
    "logical0_read": "logical0 READ",
    "logical1_no_read_control": "logical1 READ=0",
    "logical0_no_read_control": "logical0 READ=0",
}
ROLE_CLASS = {
    "logical1_read": "RESULT",
    "logical0_read": "NEGATIVE_CONTROL",
    "logical1_no_read_control": "ZERO_CONTROL",
    "logical0_no_read_control": "ZERO_CONTROL",
}


def repo_relative(path: Path) -> str:
    return path.relative_to(REPO).as_posix()


def plot_relative(path: Path) -> str:
    return path.relative_to(PLOT_DIR).as_posix()


def raw_path(kind: str, width_ps: int, load_name: str, role: str) -> Path:
    return ROOT / "raw" / kind / f"{width_ps}ps" / load_name / role / "run-01.csv"


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    frame = pd.read_csv(path)
    frame.columns = [str(column).strip('"') for column in frame.columns]
    if frame.empty or frame.columns[0] != "time":
        raise ValueError(f"missing time column or empty CSV: {path}")
    return frame


def verify_columns(frame: pd.DataFrame, columns: Iterable[str], source: Path) -> None:
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        raise KeyError(f"{source}: missing columns {missing}")


def series_by_exact_name(frame: pd.DataFrame, name: str, source: Path) -> pd.Series:
    """Return the first exact raw column when JoSIM emitted duplicate headers."""
    matches = [index for index, column in enumerate(frame.columns) if column == name]
    if not matches:
        folded = name.casefold()
        matches = [
            index for index, column in enumerate(frame.columns)
            if str(column).casefold() == folded
        ]
    if not matches:
        raise KeyError(f"{source}: missing column {name}")
    return frame.iloc[:, matches[0]]


def run_plotter(command: list[str]) -> None:
    subprocess.run(command, cwd=REPO, check=True)


def metadata_base(output: Path, title: str, *, phase: bool) -> dict[str, Any]:
    plot_id = output.stem
    if output.parent.name in {"source", "replay", "physical"}:
        plot_id = f"{output.parent.name}-{plot_id}"
    return {
        "schema_version": "CLASSIC_JOSIM_PLOT_V1",
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "experiment_id": repo_relative(ROOT),
        "plot_id": plot_id,
        "plot_path": plot_relative(output),
        "output_path": repo_relative(output),
        "title": title,
        "generated_from": "scripts/josim-plot2.py",
        "plot_type": "sep_comb",
        "color": "dark",
        "phase_semantics": "continuous_absolute" if phase else None,
        "phase_display": (
            "continuous phase phi/2pi (turns); not an SFQ counter"
            if phase else
            "raw JoSIM current/voltage units; no phase normalization"
        ),
        "scientific_authority": (
            "raw evidence and analysis report; visualization is descriptive and "
            "is not event/Gate authority"
        ),
    }


def write_metadata(output: Path, payload: dict[str, Any]) -> dict[str, Any]:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.with_suffix(".metadata.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return payload


def direct_plot(
    source: Path,
    output: Path,
    title: str,
    columns: list[str],
    *,
    phase: bool,
    page_class: str,
    case_role: str,
) -> dict[str, Any]:
    frame = read_csv(source)
    verify_columns(frame, columns, source)
    output.parent.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable, str(PLOTTER), str(source),
        "-t", "sep_comb", "-c", "dark",
        "-j", "2pi" if phase else "rad",
        "-s", *columns, "-x", str(output), "-w", title,
    ]
    run_plotter(command)
    payload = metadata_base(output, title, phase=phase)
    payload.update({
        "page_class": page_class,
        "plot_input_kind": "raw_csv",
        "source_paths": [repo_relative(source)],
        "columns": columns,
        "case_roles": {case_role: ROLE_CLASS.get(case_role, case_role)},
        "case_role_labels": {case_role: ROLE_LABELS.get(case_role, case_role)},
    })
    return write_metadata(output, payload)


def merged_plot(
    output: Path,
    title: str,
    sources: list[tuple[str, Path, str]],
    signals: list[tuple[str, str, str]],
    *,
    temp_root: Path,
    phase: bool,
    page_class: str,
) -> dict[str, Any]:
    frames = [(label, path, role, read_csv(path)) for label, path, role in sources]
    reference_time = frames[0][3].iloc[:, 0]
    merged = pd.DataFrame({"time": reference_time.to_numpy(copy=True)})
    output_columns: list[str] = []
    for label, path, _role, frame in frames:
        time = frame.iloc[:, 0]
        if len(frame) != len(reference_time) or not time.equals(reference_time):
            raise ValueError(f"time grid mismatch for comparison source: {path}")
        verify_columns(frame, [raw for _kind, raw, _short in signals], path)
        for kind, raw, short in signals:
            name = f"{kind}({label} · {short})"
            if name in merged.columns:
                raise ValueError(f"duplicate derived plot column: {name}")
            merged[name] = series_by_exact_name(frame, raw, path).to_numpy(copy=True)
            output_columns.append(name)

    derived = temp_root / f"{output.stem}.csv"
    merged.to_csv(derived, index=False)
    output.parent.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable, str(PLOTTER), str(derived),
        "-t", "sep_comb", "-c", "dark",
        "-j", "2pi" if phase else "rad",
        "-s", *output_columns, "-x", str(output), "-w", title,
    ]
    run_plotter(command)
    payload = metadata_base(output, title, phase=phase)
    payload.update({
        "page_class": page_class,
        "plot_input_kind": "derived_comparison_csv",
        "derived_input_not_raw_evidence": True,
        "derived_input_lifetime": "temporary",
        "source_paths": [repo_relative(path) for _label, path, _role in sources],
        "columns": output_columns,
        "raw_columns": [raw for _kind, raw, _short in signals],
        "case_roles": {
            label: ROLE_CLASS.get(role, role)
            for label, _path, role in sources
        },
        "case_role_labels": {
            label: ROLE_LABELS.get(role, role)
            for label, _path, role in sources
        },
    })
    return write_metadata(output, payload)


def source_columns(count: int) -> list[str]:
    middle = max(1, count // 2)
    return [
        "I(I_WL1)", "I(I_SE1)",
        "P(B_JM1|XBVM1)", "V(B_JM1|XBVM1)",
        "P(B_JM2|XBVM1)", "V(B_JM2|XBVM1)",
        "P(B_JS1|XBVM1)", "V(B_JS1|XBVM1)",
        "P(B_JS2|XBVM1)", "V(B_JS2|XBVM1)",
        "V(N6|XBVM1)", "V(SL1)",
        "I(L_PSL|XBVM1)", "I(L_SL|XBVM1)",
        "I(B_LD1)", "P(B_LD1)", "V(B_LD1)",
        f"I(B_LD{middle})", f"I(B_LD{count})",
        f"P(B_LD{count})", f"V(B_LD{count})",
    ]


def qb_columns(*, replay: bool) -> list[str]:
    columns = [
        "P(BJS|XBQ)", "V(BJS|XBQ)", "I(BJS|XBQ)",
        "P(BJL1|XBQ)", "V(BJL1|XBQ)", "I(BJL1|XBQ)",
        "P(BJL2|XBQ)", "V(BJL2|XBQ)", "I(BJL2|XBQ)",
        "V(IN)", "V(OUT)", "I(LIN|XBQ)",
        "I(L0|XBQ)", "I(L1|XBQ)", "I(L2|XBQ)",
        "I(RB|XBQ)", "I(RJ1|XBQ)", "I(RJ2|XBQ)",
        "I(R_LOAD)", "I(I_IBIAS)",
    ]
    if replay:
        columns.append("I(I_REPLAY)")
    return columns


def physical_columns(count: int) -> list[str]:
    return source_columns(count) + qb_columns(replay=False)


def source_focus(count: int) -> list[tuple[str, str, str]]:
    middle = max(1, count // 2)
    return [
        ("I", "I(I_WL1)", "I(WL1)"),
        ("I", "I(I_SE1)", "I(SE1)"),
        ("P", "P(B_JS1|XBVM1)", "JS1 phase"),
        ("V", "V(B_JS1|XBVM1)", "JS1 voltage"),
        ("P", "P(B_JS2|XBVM1)", "JS2 phase"),
        ("V", "V(B_JS2|XBVM1)", "JS2 voltage"),
        ("V", "V(N6|XBVM1)", "V(N6)"),
        ("V", "V(SL1)", "V(SL1)"),
        ("I", "I(L_SL|XBVM1)", "I(L_SL)"),
        ("I", "I(B_LD1)", "JSL1 current"),
        ("I", f"I(B_LD{middle})", f"JSL{middle} current"),
        ("I", f"I(B_LD{count})", f"JSL{count} current"),
        ("P", "P(B_LD1)", "JSL1 phase"),
        ("P", f"P(B_LD{count})", f"JSL{count} phase"),
    ]


def qb_focus(*, include_replay: bool = False) -> list[tuple[str, str, str]]:
    signals = [
        ("P", "P(BJS|XBQ)", "BJs phase"),
        ("P", "P(BJL1|XBQ)", "BJL1 phase"),
        ("P", "P(BJL2|XBQ)", "BJL2 phase"),
        ("V", "V(BJL2|XBQ)", "BJL2 voltage"),
        ("I", "I(BJL2|XBQ)", "BJL2 current"),
        ("V", "V(IN)", "V(IN)"),
        ("V", "V(OUT)", "V(OUT)"),
        ("I", "I(LIN|XBQ)", "I(Lin)"),
        ("I", "I(L0|XBQ)", "I(L0)"),
        ("I", "I(L1|XBQ)", "I(L1)"),
        ("I", "I(L2|XBQ)", "I(L2)"),
        ("I", "I(R_LOAD)", "I(R_LOAD)"),
    ]
    if include_replay:
        signals.append(("I", "I(I_REPLAY)", "I(replay)"))
    return signals


def physical_focus() -> list[tuple[str, str, str]]:
    return [
        ("I", "I(L_SL|XBVM1)", "I(L_SL)"),
        ("V", "V(SL1)", "V(SL1)"),
        ("V", "V(IN)", "V(IN)"),
        ("P", "P(BJS|XBQ)", "BJs phase"),
        ("P", "P(BJL1|XBQ)", "BJL1 phase"),
        ("P", "P(BJL2|XBQ)", "BJL2 phase"),
        ("V", "V(BJL2|XBQ)", "BJL2 voltage"),
        ("I", "I(BJL2|XBQ)", "BJL2 current"),
        ("V", "V(OUT)", "V(OUT)"),
        ("I", "I(R_LOAD)", "I(R_LOAD)"),
    ]


def role_sources(kind: str, width_ps: int, load_name: str) -> list[tuple[str, Path, str]]:
    return [
        (
            f"{width_ps} ps · {load_name} · {ROLE_LABELS[role]}",
            raw_path(kind, width_ps, load_name, role),
            role,
        )
        for role in ROLES
    ]


def matrix_sources(kind: str) -> list[tuple[str, Path, str]]:
    entries: list[tuple[str, Path, str]] = []
    for width_ps in WIDTHS:
        for load_name in LOADS:
            for role in ("logical1_read", "logical0_read"):
                entries.append((
                    f"{width_ps} ps · {load_name} · {ROLE_LABELS[role]}",
                    raw_path(kind, width_ps, load_name, role),
                    role,
                ))
    return entries


def generate() -> list[dict[str, Any]]:
    PLOT_DIR.mkdir(parents=True, exist_ok=True)
    pages: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="josimplot-bvm-load-qb-") as temporary:
        temp_root = Path(temporary)

        # Independent case pages follow the established canonical BVM
        # renderer: source, replay, and physical cases can each be opened
        # directly from their raw CSV.
        for width_ps in WIDTHS:
            for load_name, load in LOADS.items():
                count = int(load["count"])
                for role in ROLES:
                    source_output = PLOT_DIR / "cases" / "source" / (
                        f"{width_ps}ps-{load_name}-{role}.html"
                    )
                    source_title = (
                        f"BVM → {count}×JSL ({load['ic_uA']} µA) → GND source "
                        f"— {width_ps} ps — {ROLE_LABELS[role]}"
                    )
                    pages.append(direct_plot(
                        raw_path("source", width_ps, load_name, role),
                        source_output,
                        source_title,
                        source_columns(count),
                        phase=True,
                        page_class="source_case",
                        case_role=role,
                    ))

                    replay_output = PLOT_DIR / "cases" / "replay" / (
                        f"{width_ps}ps-{load_name}-{role}.html"
                    )
                    replay_title = (
                        f"Ideal source replay → scaled QB "
                        f"— {width_ps} ps — {load_name} — {ROLE_LABELS[role]}"
                    )
                    pages.append(direct_plot(
                        raw_path("replay", width_ps, load_name, role),
                        replay_output,
                        replay_title,
                        qb_columns(replay=True),
                        phase=True,
                        page_class="replay_case",
                        case_role=role,
                    ))

                    output = PLOT_DIR / "cases" / "physical" / (
                        f"{width_ps}ps-{load_name}-{role}.html"
                    )
                    title = (
                        f"Physical BVM → {count}×JSL ({load['ic_uA']} µA) → scaled QB "
                        f"— {width_ps} ps — {ROLE_LABELS[role]}"
                    )
                    pages.append(direct_plot(
                        raw_path("physical", width_ps, load_name, role),
                        output,
                        title,
                        physical_columns(count),
                        phase=True,
                        page_class="physical_case",
                        case_role=role,
                    ))

        # Per-operating-point comparisons retain all four formal roles but
        # expose only the signals needed to answer the corresponding question.
        for width_ps in WIDTHS:
            for load_name, load in LOADS.items():
                count = int(load["count"])
                output = PLOT_DIR / "comparisons" / (
                    f"{width_ps}ps-{load_name}-source-matched.html"
                )
                pages.append(merged_plot(
                    output,
                    f"BVM → {count}×JSL source — {width_ps} ps — matched cases",
                    role_sources("source", width_ps, load_name),
                    source_focus(count),
                    temp_root=temp_root,
                    phase=True,
                    page_class="source_matched_comparison",
                ))

                output = PLOT_DIR / "comparisons" / (
                    f"{width_ps}ps-{load_name}-replay-matched.html"
                )
                pages.append(merged_plot(
                    output,
                    f"Ideal source replay → scaled QB — {width_ps} ps — matched cases",
                    role_sources("replay", width_ps, load_name),
                    qb_focus(include_replay=True),
                    temp_root=temp_root,
                    phase=True,
                    page_class="replay_matched_comparison",
                ))

                output = PLOT_DIR / "comparisons" / (
                    f"{width_ps}ps-{load_name}-physical-matched.html"
                )
                pages.append(merged_plot(
                    output,
                    f"Physical BVM → {count}×JSL → scaled QB — {width_ps} ps / {load_name} — matched cases",
                    role_sources("physical", width_ps, load_name),
                    physical_focus(),
                    temp_root=temp_root,
                    phase=True,
                    page_class="physical_matched_comparison",
                ))

                paired = [
                    (
                        f"physical · {ROLE_LABELS[role]}",
                        raw_path("physical", width_ps, load_name, role),
                        role,
                    )
                    for role in ROLES
                ] + [
                    (
                        f"ideal replay · {ROLE_LABELS[role]}",
                        raw_path("replay", width_ps, load_name, role),
                        role,
                    )
                    for role in ROLES
                ]
                output = PLOT_DIR / "comparisons" / (
                    f"{width_ps}ps-{load_name}-physical-vs-replay-qb.html"
                )
                pages.append(merged_plot(
                    output,
                    f"Physical BVM → {count}×JSL → scaled QB vs ideal replay "
                    f"— {width_ps} ps / {load_name}",
                    paired,
                    qb_focus(),
                    temp_root=temp_root,
                    phase=True,
                    page_class="physical_vs_replay_comparison",
                ))

        pages.append(merged_plot(
            PLOT_DIR / "comparisons" / "matrix-physical-readout-key.html",
            "Physical BVM → JSL → scaled QB — four-point readout key data",
            matrix_sources("physical"),
            [
                ("I", "I(L_SL|XBVM1)", "I(L_SL)"),
                ("P", "P(BJL2|XBQ)", "BJL2 phase"),
                ("V", "V(OUT)", "V(OUT)"),
                ("I", "I(R_LOAD)", "I(R_LOAD)"),
            ],
            temp_root=temp_root,
            phase=True,
            page_class="matrix_key_comparison",
        ))
        pages.append(merged_plot(
            PLOT_DIR / "comparisons" / "matrix-replay-readout-key.html",
            "Ideal source replay → scaled QB — four-point readout key data",
            matrix_sources("replay"),
            [
                ("I", "I(I_REPLAY)", "I(replay)"),
                ("P", "P(BJL2|XBQ)", "BJL2 phase"),
                ("V", "V(OUT)", "V(OUT)"),
                ("I", "I(R_LOAD)", "I(R_LOAD)"),
            ],
            temp_root=temp_root,
            phase=True,
            page_class="matrix_key_comparison",
        ))
    return pages


def write_readme(pages: list[dict[str, Any]]) -> None:
    direct = [page for page in pages if page["page_class"].endswith("_case")]
    comparisons = [page for page in pages if not page["page_class"].endswith("_case")]
    recommended_ids = {"matrix-physical-readout-key", "matrix-replay-readout-key"}
    lines = [
        "# BVM_LOAD_QB_MATRIX_V1 classic 可视化",
        "",
        "本目录严格复用项目既有 classic JoSIM viewer 方案：",
        "`scripts/josim-plot2.py` 直接读取 raw CSV；所有页面使用 "
        "`sep_comb`、dark theme，含相位的页面使用 `-j 2pi`。",
        "",
        "独立 physical case 页面直接使用原始 CSV；比较页面只在生成过程中使用临时 "
        "merged CSV，页面旁的 metadata 记录所有 raw 来源。没有重跑 JoSIM，也没有修改 raw。",
        "",
        "## 建议先看",
        "",
    ]
    for page in pages:
        if page["plot_id"] in recommended_ids:
            lines.append(f"- [{page['title']}]({page['plot_path']})")
    lines += [
        "",
        "## 独立 case 页面（48 个）",
        "",
        "这些页面直接读取 raw CSV，保留四种 formal role；source、replay、physical "
        "分别对应三类 fixture。",
        "",
    ]
    for page_class, heading in (
        ("source_case", "### Source 独立页面（16 个）"),
        ("replay_case", "### Replay 独立页面（16 个）"),
        ("physical_case", "### Physical 独立页面（16 个）"),
    ):
        lines += [heading, ""]
        for page in direct:
            if page["page_class"] == page_class:
                lines.append(f"- [{page['title']}]({page['plot_path']})")
        lines.append("")
    lines += [
        "",
        "## 聚焦 comparison 页面",
        "",
        "每个工作点的 source/replay/physical matched 页只显示回答问题所需的信号；"
        "physical-vs-replay 页用于观察负载后的 QB 轨迹与理想重放的差异。",
        "",
    ]
    for page in comparisons:
        if page["plot_id"] not in recommended_ids:
            lines.append(f"- [{page['title']}]({page['plot_path']})")
    lines += [
        "",
        "## 读图边界",
        "",
        "- 原始 `P(...)` 是 rad；`-j 2pi` 只显示连续相位 φ/2π（turns），不是 SFQ 计数。",
        "- 图形只描述 raw/report 已有证据；事件、receiver 或 Gate 判定回到分析报告。",
        "- source 是末级 JSL 接地；physical 是 `BVM → 12/8 JSL → QB`；replay 是 source 的 "
        "`I(B_LD1)(t)` 原样驱动 QB。",
        "- QB 外部输出负载是 `R_LOAD OUT 0 10`，即 10 Ω 接地。",
        "",
    ]
    (PLOT_DIR / "README.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check-only", action="store_true",
        help="只检查所有 raw CSV 的必要列，不生成 HTML",
    )
    args = parser.parse_args()
    if args.check_only:
        for width_ps in WIDTHS:
            for load_name, load in LOADS.items():
                count = int(load["count"])
                for role in ROLES:
                    verify_columns(read_csv(raw_path("physical", width_ps, load_name, role)), physical_columns(count), raw_path("physical", width_ps, load_name, role))
                    verify_columns(read_csv(raw_path("source", width_ps, load_name, role)), source_columns(count), raw_path("source", width_ps, load_name, role))
                    verify_columns(read_csv(raw_path("replay", width_ps, load_name, role)), qb_columns(replay=True), raw_path("replay", width_ps, load_name, role))
        print("classic raw/header check: PASS")
        return

    pages = generate()
    write_readme(pages)
    (PLOT_DIR / "index.json").write_text(json.dumps({
        "schema_version": "CLASSIC_JOSIM_PLOT_INDEX_V1",
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "renderer": "scripts/josim-plot2.py",
        "plot_type": "sep_comb",
        "color": "dark",
        "plots": pages,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "pages": len(pages)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
