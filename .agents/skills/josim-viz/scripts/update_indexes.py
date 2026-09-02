#!/usr/bin/env python3
"""Add result-overview and topology links to the two repository indexes."""
from __future__ import annotations

import argparse
import html
import re
import subprocess
from pathlib import Path


def rel(repo_root: Path, path: Path) -> str:
    return path.resolve().relative_to(repo_root.resolve()).as_posix()


def href_from_docs(repo_root: Path, path: Path) -> str:
    return "../" + rel(repo_root, path)


def topology_records(repo_root: Path) -> list[dict]:
    root = repo_root / "test/exploration"
    records = []
    for d in sorted(p for p in root.iterdir() if p.is_dir()):
        svg = d / "topology/topology.svg"
        readme = d / "topology/README.md"
        manifest = d / "topology/manifest.json"
        if not svg.exists():
            continue
        variants = sorted(d.glob("topology/variants/*/topology.svg"))
        records.append({
            "name": d.name,
            "svg": href_from_docs(repo_root, svg),
            "readme": href_from_docs(repo_root, readme),
            "manifest": href_from_docs(repo_root, manifest),
            "variants": [(v.parent.name, href_from_docs(repo_root, v)) for v in variants],
        })
    return records


def overview_records(repo_root: Path) -> list[dict]:
    root = repo_root / "test/exploration"
    records = []
    for d in sorted(p for p in root.iterdir() if p.is_dir()):
        plot = d / "plots/overview.html"
        readme = d / "plots/overview-README.md"
        if plot.exists():
            records.append({
                "name": d.name,
                "plot": href_from_docs(repo_root, plot),
                "readme": href_from_docs(repo_root, readme) if readme.exists() else None,
            })
    return records


def topology_html(records: list[dict]) -> str:
    rows = []
    for i, r in enumerate(records, 1):
        variants = "、".join(
            f'<a href="{html.escape(h)}">{html.escape(label)}</a>'
            for label, h in r["variants"]
        ) or '<span class="small">无结构变体</span>'
        rows.append(
            f'<tr><td class="num">{i}</td><td><code>{html.escape(r["name"])}</code></td>'
            f'<td><a href="{html.escape(r["svg"])}">主结构图</a>、'
            f'<a href="{html.escape(r["readme"])}">拓扑说明</a>、'
            f'<a href="{html.escape(r["manifest"])}">manifest</a></td>'
            f'<td>{variants}</td></tr>'
        )
    return (
        '<section id="topology-index"><h2>结构拓扑总览</h2>'
        '<p class="lead">以下结构图由各实验实际 netlist 展平并由 Graphviz 生成；附件参考图：<a href="../arti/BVM.png">BVM.png</a>、<a href="../arti/BVMstructure.png">BVMstructure.png</a>、<a href="../arti/BQstructure.png">BQstructure.png</a>。参数或 PWL-only 变体共用主图，连接结构不同的变体列在右侧。</p>'
        '<table class="inventory"><thead><tr><th>#</th><th>Exploration</th><th>主入口</th><th>结构变体</th></tr></thead><tbody>'
        + "".join(rows)
        + '</tbody></table></section>'
    )


def overview_html(records: list[dict]) -> str:
    rows = []
    for i, r in enumerate(records, 1):
        readme = f'、<a href="{html.escape(r["readme"])}">说明</a>' if r["readme"] else ""
        rows.append(
            f'<tr><td class="num">{i}</td><td><code>{html.escape(r["name"])}</code></td>'
            f'<td><a href="{html.escape(r["plot"])}">classic overview</a>{readme}</td></tr>'
        )
    return (
        '<section id="overview-index"><h2>本次补齐的 raw-case 可视化</h2>'
        '<p class="lead">这些目录原先有 raw CSV 但没有 HTML 结果图；overview 直接读取全部可用 case，按真实 CSV header 绘制 phase/voltage/current，不能替代 report 的 event 判定。</p>'
        '<table class="inventory"><thead><tr><th>#</th><th>Exploration</th><th>结果入口</th></tr></thead><tbody>'
        + "".join(rows)
        + '</tbody></table></section>'
    )


def insert_before(text: str, marker: str, block: str) -> str:
    if block.split(" id=", 1)[0] in text:
        # id-specific blocks are removed by the caller only when needed; this
        # guard mainly prevents duplicate insertion on rerun.
        pass
    pos = text.find(marker)
    if pos < 0:
        raise RuntimeError(f"marker not found: {marker}")
    return text[:pos] + block + text[pos:]


def replace_html_section(text: str, section_id: str, block: str) -> str:
    pattern = re.compile(rf'<section id="{re.escape(section_id)}">.*?</section>', re.S)
    if pattern.search(text):
        return pattern.sub(block, text, count=1)
    return text


def update_flow_html(path: Path, repo_root: Path, records: list[dict], overviews: list[dict], head: str) -> None:
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"parent HEAD：<code>[^<]+</code>", f"parent HEAD：<code>{head}</code>", text)
    text = text.replace(
        "附件 BVM/BQ 图片只作配色/版式参考。参数或 PWL-only 变体共用主图，连接结构不同的变体列在右侧。",
        "参考图：<a href=\"../arti/BVM.png\">BVM.png</a>、<a href=\"../arti/BVMstructure.png\">BVMstructure.png</a>、<a href=\"../arti/BQstructure.png\">BQstructure.png</a>。参数或 PWL-only 变体共用主图，连接结构不同的变体列在右侧。",
    )
    text = text.replace(
        "每个节点说明做了什么、结果是什么、结论能走到哪里，并链接到报告和已有 HTML 图。",
        "每个节点说明做了什么、结果是什么、结论能走到哪里，并链接到报告、结果 HTML 图和 netlist-derived 结构图。",
    )
    rec_by_name = {r["name"]: r for r in records}
    ov_by_name = {r["name"]: r for r in overviews}
    article_re = re.compile(r'(<article\b[^>]*\bid="exp-([^" ]+)"[^>]*>.*?</article>)', re.S)

    def article_update(match: re.Match[str]) -> str:
        block, key = match.group(1), match.group(2)
        name = key
        r = rec_by_name.get(name)
        ov = ov_by_name.get(name)
        links = re.search(r'(<div class="links">)(.*?)(</div>)', block, re.S)
        if not links:
            return block
        additions = []
        if r and "结构图" not in links.group(2):
            additions.append(f'<a href="{html.escape(r["svg"])}">结构图</a><a href="{html.escape(r["readme"])}">拓扑说明</a>')
        if ov and "raw overview" not in links.group(2):
            additions.append(f'<a href="{html.escape(ov["plot"])}">raw overview</a>')
        if name == "bvm-sfq-receiver-r2a-coupling-20260821" and "k-matrix" not in links.group(2):
            additions.append('<a href="../test/exploration/bvm-sfq-receiver-r2a-coupling-20260821/plots/k-matrix-comparison.html">all-K matrix</a>')
        if not additions:
            return block
        new_links = links.group(1) + links.group(2) + "".join(additions) + links.group(3)
        return block[:links.start()] + new_links + block[links.end():]

    text = article_re.sub(article_update, text)
    # Add a topology column to the inventory table, keyed by the card anchor.
    table_match = re.search(r'(<table class="inventory">.*?</table>)', text, re.S)
    if table_match and "结构图" not in table_match.group(1)[:1000]:
        table = table_match.group(1)
        table = table.replace("</tr>", "<th>结构图</th></tr>", 1)

        def row_update(m: re.Match[str]) -> str:
            row = m.group(0)
            anchor = re.search(r'href="#(exp-[^"]+)"', row)
            if not anchor:
                return row
            key = anchor.group(1)[4:]
            r = rec_by_name.get(key)
            if not r:
                cell = '<td><span class="small">无独立图</span></td>'
            else:
                cell = f'<td><a href="{html.escape(r["svg"])}">主结构图</a></td>'
            return row[:-5] + cell + "</tr>" if row.endswith("</tr>") else row

        table = re.sub(r'<tr>.*?</tr>', row_update, table, flags=re.S)
        text = text[:table_match.start()] + table + text[table_match.end():]
    if 'id="topology-index"' in text:
        text = replace_html_section(text, "topology-index", topology_html(records))
    else:
        text = insert_before(text, '<section id="rules">', topology_html(records))
    if 'id="overview-index"' in text:
        text = replace_html_section(text, "overview-index", overview_html(overviews))
    else:
        text = insert_before(text, '<section id="rules">', overview_html(overviews))
    path.write_text(text, encoding="utf-8")


def update_visual_html(path: Path, repo_root: Path, records: list[dict], overviews: list[dict], head: str) -> None:
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"可视化 checkpoint parent HEAD：`[^`]+`", f"可视化 checkpoint parent HEAD：`{head}`", text)
    text = text.replace(
        "附件 BVM/BQ 图片只作配色/版式参考。参数或 PWL-only 变体共用主图，连接结构不同的变体列在右侧。",
        "参考图：<a href=\"../arti/BVM.png\">BVM.png</a>、<a href=\"../arti/BVMstructure.png\">BVMstructure.png</a>、<a href=\"../arti/BQstructure.png\">BQstructure.png</a>。参数或 PWL-only 变体共用主图，连接结构不同的变体列在右侧。",
    )
    old = '<a href="../test/exploration/bvm-sfq-receiver-r2a-coupling-20260821/plots/k080-representative/comparison.html">R2a K=.80 comparison</a>'
    new = old + '、<a href="../test/exploration/bvm-sfq-receiver-r2a-coupling-20260821/plots/k-matrix-comparison.html">R2a complete K matrix</a>'
    duplicate = '<a href="../test/exploration/bvm-sfq-receiver-r2a-coupling-20260821/plots/k-matrix-comparison.html">R2a complete K matrix</a>、<a href="../test/exploration/bvm-sfq-receiver-r2a-coupling-20260821/plots/k-matrix-comparison.html">R2a complete K matrix</a>'
    text = text.replace(duplicate, '<a href="../test/exploration/bvm-sfq-receiver-r2a-coupling-20260821/plots/k-matrix-comparison.html">R2a complete K matrix</a>')
    if "R2a complete K matrix" not in text:
        text = text.replace(old, new)
    marker = '<h2 id="p0-anchorcanonical-bvm-internal-readout">'
    if 'id="topology-index"' in text:
        text = replace_html_section(text, "topology-index", topology_html(records))
    else:
        text = insert_before(text, marker, topology_html(records))
    if 'id="overview-index"' in text:
        text = replace_html_section(text, "overview-index", overview_html(overviews))
    else:
        text = insert_before(text, marker, overview_html(overviews))
    path.write_text(text, encoding="utf-8")


def markdown_topology(records: list[dict]) -> str:
    lines = [
        "## 结构拓扑总览",
        "",
        "结构图均从实际 netlist 展平并由 Graphviz 生成；参考图：[BVM.png](../arti/BVM.png)、[BVMstructure.png](../arti/BVMstructure.png)、[BQstructure.png](../arti/BQstructure.png)。参数或 PWL-only 变体共用主图，结构不同的变体另列。",
        "",
        "| Exploration | 主结构图 | 拓扑说明 | 结构变体 |",
        "|---|---|---|---|",
    ]
    for r in records:
        variants = "、".join(f"[{label}]({href})" for label, href in r["variants"]) or "无"
        lines.append(f"| `{r['name']}` | [主图]({r['svg']}) | [README]({r['readme']}) | {variants} |")
    return "\n".join(lines) + "\n"


def markdown_overviews(overviews: list[dict]) -> str:
    lines = [
        "## 本次补齐的 raw-case 可视化",
        "",
        "以下目录原先有 raw CSV 但没有 HTML 结果图；overview 直接读取全部可用 case，按真实 CSV header 绘制 phase/voltage/current，不能替代 report 的 event 判定。",
        "",
        "| Exploration | overview | 说明 |",
        "|---|---|---|",
    ]
    for r in overviews:
        readme = f"[README]({r['readme']})" if r["readme"] else "—"
        lines.append(f"| `{r['name']}` | [classic overview]({r['plot']}) | {readme} |")
    return "\n".join(lines) + "\n"


def replace_markdown_section(text: str, heading: str, block: str) -> str:
    pattern = re.compile(rf'^{re.escape(heading)}\n.*?(?=^## |\Z)', re.M | re.S)
    if pattern.search(text):
        return pattern.sub(block, text, count=1)
    return text


def update_markdown(path: Path, block_topology: str, block_overviews: str, head: str, marker: str) -> None:
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"更新时间：[^；]+；", f"更新时间：2026-08-24；", text, count=1)
    text = text.replace("可视化 checkpoint parent HEAD：`960f3948f48017747b79d0a7c37a8b0dd302c913`。", f"可视化 checkpoint parent HEAD：`{head}`。")
    text = text.replace(
        "附件 BVM/BQ 图片只作为配色/版式参考。参数或 PWL-only 变体共用主图，结构不同的变体另列。",
        "参考图：[BVM.png](../arti/BVM.png)、[BVMstructure.png](../arti/BVMstructure.png)、[BQstructure.png](../arti/BQstructure.png)。参数或 PWL-only 变体共用主图，结构不同的变体另列。",
    )
    matrix = "../test/exploration/bvm-sfq-receiver-r2a-coupling-20260821/plots/k-matrix-comparison.html"
    old_r2 = "[R2a K=.80 comparison](../test/exploration/bvm-sfq-receiver-r2a-coupling-20260821/plots/k080-representative/comparison.html)"
    new_r2 = old_r2 + f"、[R2a complete K matrix]({matrix})"
    if "R2a complete K matrix" not in text:
        text = text.replace(old_r2, new_r2)
    if "k-matrix-comparison.html" not in text:
        text = text.replace(
            "../test/exploration/bvm-sfq-receiver-r2a-coupling-20260821/plots/k080-representative/comparison.html)",
            "../test/exploration/bvm-sfq-receiver-r2a-coupling-20260821/plots/k080-representative/comparison.html); [all-K matrix](../test/exploration/bvm-sfq-receiver-r2a-coupling-20260821/plots/k-matrix-comparison.html)",
        )
    if "## 结构拓扑总览" in text:
        text = replace_markdown_section(text, "## 结构拓扑总览", block_topology)
        text = replace_markdown_section(text, "## 本次补齐的 raw-case 可视化", block_overviews)
    else:
        pos = text.find(marker)
        if pos < 0:
            raise RuntimeError(f"markdown marker not found: {marker}")
        text = text[:pos] + block_topology + "\n" + block_overviews + "\n" + text[pos:]
    path.write_text(text, encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", type=Path, default=Path("."))
    args = ap.parse_args()
    repo_root = args.repo_root.resolve()
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo_root, text=True).strip()
    records = topology_records(repo_root)
    overviews = overview_records(repo_root)
    update_flow_html(repo_root / "docs/EXPLORATION_FLOW_INDEX.html", repo_root, records, overviews, head)
    update_visual_html(repo_root / "docs/VISUALIZATION_INDEX.html", repo_root, records, overviews, head)
    update_markdown(repo_root / "docs/EXPLORATION_FLOW_INDEX.md", markdown_topology(records), markdown_overviews(overviews), head, "## 统一读图规则")
    update_markdown(repo_root / "docs/VISUALIZATION_INDEX.md", markdown_topology(records), markdown_overviews(overviews), head, "## P0 anchor：canonical BVM internal readout")
    print(f"updated indexes: topologies={len(records)}, overviews={len(overviews)}, parent_head={head}")


if __name__ == "__main__":
    main()
