#!/usr/bin/env python3
"""Switch only the Q0 index entry to the new schematic/debug split."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SLUG = "qb-q0-standalone-current-quantized-event-20260824"
REL = f"../test/exploration/{SLUG}/topology"


def update_markdown(path: Path) -> None:
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    hits = 0
    old = f"[主图]({REL}/topology.svg)"
    new = (
        f"[论文级电路图]({REL}/schematic.svg)；"
        f"[annotated schematic]({REL}/schematic-annotated.svg)；"
        f"[debug graph]({REL}/connectivity-debug.svg)"
    )
    for index, line in enumerate(lines):
        if f"| `{SLUG}` |" not in line:
            continue
        current = (
            f"[论文级电路图]({REL}/schematic.svg)；"
            f"[debug graph]({REL}/connectivity-debug.svg)"
        )
        if current in line:
            lines[index] = line.replace(current, new)
            hits += 1
        elif old in line:
            lines[index] = line.replace(old, new)
            hits += 1
    if hits > 1:
        raise RuntimeError(f"expected at most one Q0 markdown row in {path}, found {hits}")
    text = "".join(lines)
    text = text.replace(
        "结构图均从实际 netlist 展平并由 Graphviz 生成；",
        "结构入口区分 publication schematic 与 legacy Graphviz connectivity-debug；",
    )
    path.write_text(text, encoding="utf-8")


def update_html(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    old = f'<a href="{REL}/topology.svg">主结构图</a>、<a href="{REL}/README.md">'
    new = (
        f'<a href="{REL}/schematic.svg">论文级电路图</a>、'
        f'<a href="{REL}/schematic-annotated.svg">annotated schematic</a>、'
        f'<a href="{REL}/connectivity-debug.svg">debug graph</a>、'
        f'<a href="{REL}/README.md">'
    )
    count = text.count(old)
    if count > 1:
        raise RuntimeError(f"expected at most one Q0 HTML row in {path}, found {count}")
    if count == 1:
        text = text.replace(old, new)
    current = (
        f'<a href="{REL}/schematic.svg">论文级电路图</a>、'
        f'<a href="{REL}/connectivity-debug.svg">debug graph</a>、'
    )
    current_new = (
        f'<a href="{REL}/schematic.svg">论文级电路图</a>、'
        f'<a href="{REL}/schematic-annotated.svg">annotated schematic</a>、'
        f'<a href="{REL}/connectivity-debug.svg">debug graph</a>、'
    )
    if current in text:
        text = text.replace(current, current_new)
    for old_label, new_label in (("结构图", "论文级电路图"), ("主结构图", "论文级电路图")):
        old_card = f'<a href="{REL}/topology.svg">{old_label}</a>'
        new_card = (
            f'<a href="{REL}/schematic.svg">{new_label}</a>'
            f'<a href="{REL}/schematic-annotated.svg">annotated schematic</a>'
            f'<a href="{REL}/connectivity-debug.svg">debug graph</a>'
        )
        if old_card in text:
            text = text.replace(old_card, new_card)
        current_card = (
            f'<a href="{REL}/schematic.svg">{new_label}</a>'
            f'<a href="{REL}/connectivity-debug.svg">debug graph</a>'
        )
        if current_card in text:
            text = text.replace(current_card, new_card)
    text = text.replace(
        "以下结构图由各实验实际 netlist 展平并由 Graphviz 生成；",
        "结构入口区分 publication schematic 与 legacy Graphviz connectivity-debug；",
    )
    path.write_text(text, encoding="utf-8")


def main() -> None:
    for name in ("VISUALIZATION_INDEX.md", "EXPLORATION_FLOW_INDEX.md"):
        update_markdown(ROOT / "docs" / name)
    for name in ("VISUALIZATION_INDEX.html", "EXPLORATION_FLOW_INDEX.html"):
        update_html(ROOT / "docs" / name)
    print("updated Q0 schematic/debug links in four indexes")


if __name__ == "__main__":
    main()
