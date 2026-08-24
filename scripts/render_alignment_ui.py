#!/usr/bin/env python3
"""Shared human-facing HTML renderer for the alignment indexes.

The alignment manifest remains the authority.  This module only controls the
presentation: the older project UI used a sticky utility bar, stage navigation
and readable evidence cards.  Keeping that presentation in one renderer also
prevents the flow and visualization pages from drifting apart again.
"""
from __future__ import annotations

import html
from collections import OrderedDict
from typing import Any


CSS = r"""
:root{color-scheme:light;--ink:#172033;--muted:#5b667a;--line:#d8dee9;--panel:#f6f8fb;--panel2:#edf2f8;--link:#0759a8;--link-hover:#0b78d0;--accent:#1d6f9f;--green:#0d6b4d;--amber:#8a5b00;--red:#9b2638;--gray:#586274;--purple:#6b4ca3}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:#fff;color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif;line-height:1.65}.page{width:min(1540px,calc(100% - 36px));margin:auto;padding:28px 0 64px}.utility{position:sticky;top:0;z-index:20;display:flex;flex-wrap:wrap;gap:10px 22px;align-items:center;margin:-28px 0 24px;padding:11px 16px;border-bottom:1px solid var(--line);background:rgba(255,255,255,.96);backdrop-filter:blur(8px);color:var(--muted);font-size:.92rem}.utility a{font-weight:700}a{color:var(--link);text-decoration-thickness:1px;text-underline-offset:2px}a:hover{color:var(--link-hover)}h1{margin:0 0 8px;color:#102c4e;font-size:clamp(1.9rem,3vw,2.7rem);line-height:1.2}h2{margin:44px 0 14px;padding-bottom:8px;border-bottom:2px solid var(--accent);color:#123e69;font-size:1.55rem}h3{margin:4px 0 8px;color:#18567d;font-size:1.12rem}p{max-width:1180px}.lede{font-size:1.08rem;max-width:1160px}.note{padding:14px 18px;border-left:4px solid var(--accent);background:var(--panel);margin:18px 0}.note.warning{border-left-color:#c18100;background:#fff9e8}.legend{display:flex;flex-wrap:wrap;gap:8px 14px;margin:15px 0}.badge{display:inline-block;border-radius:999px;padding:2px 9px;font-size:.77rem;font-weight:700;white-space:nowrap}.badge-result{background:#e8f1fb;color:#174a7b}.badge-comparison{background:#e9f5ef;color:#0d6b4d}.badge-control{background:#fff4d8;color:#805800}.badge-reference{background:#f0ecf8;color:#644692}.badge-status{background:#edf0f5;color:#485467}.badge-pass{background:#e4f4ec;color:#0d6b4d}.badge-warn{background:#fff4d8;color:#805800}.badge-fail{background:#fae9ed;color:#9b2638}.badge-neutral{background:#edf0f5;color:#586274}.flow{display:grid;grid-template-columns:repeat(9,minmax(105px,1fr));gap:8px;margin:22px 0 34px}.flow a{display:block;min-height:74px;padding:10px 11px;border:1px solid var(--line);border-radius:8px;background:var(--panel);text-decoration:none;color:var(--ink);transition:.15s ease}.flow a:hover{border-color:var(--link);background:#f0f6fc;transform:translateY(-1px)}.flow .num{display:block;color:var(--accent);font-size:.75rem;font-weight:800;letter-spacing:.04em}.flow .label{display:block;font-size:.88rem;font-weight:700;line-height:1.25}.stage{scroll-margin-top:72px}.stage-title{display:flex;align-items:baseline;gap:12px}.stage-title .stage-no{font-size:.85rem;color:var(--accent);font-weight:800;letter-spacing:.08em}.cards{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px;margin:0 0 28px}.card{border:1px solid var(--line);border-left:5px solid #aeb8c6;border-radius:9px;background:#fff;box-shadow:0 2px 6px rgba(20,42,70,.055);padding:17px 19px 16px;min-width:0}.card.status-pass{border-left-color:var(--green)}.card.status-warn{border-left-color:#c18100}.card.status-fail{border-left-color:var(--red)}.card.status-neutral{border-left-color:#718097}.card-header{display:flex;justify-content:space-between;gap:12px;align-items:flex-start}.card-title{margin:0;color:#173e63;font-size:1.12rem;line-height:1.35}.card-id{display:block;margin-top:3px;color:var(--muted);font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:.74rem;word-break:break-all}.status-stack{display:flex;flex-wrap:wrap;justify-content:flex-end;gap:5px;min-width:150px}.card dl{display:grid;grid-template-columns:6.2rem 1fr;gap:5px 12px;margin:13px 0 10px}.card dt{color:var(--muted);font-size:.86rem;font-weight:700}.card dd{margin:0;min-width:0}.card .question,.card .result{font-size:.94rem}.card .boundary{color:#536077;font-size:.87rem}.link-groups{display:flex;flex-wrap:wrap;gap:7px 14px;margin-top:11px;padding-top:10px;border-top:1px solid #edf0f4}.link-groups a{font-size:.88rem}.link-groups .group{display:flex;flex-wrap:wrap;gap:4px 10px;align-items:center}.link-groups .label{color:var(--muted);font-weight:700;font-size:.79rem}.stage-count{color:var(--muted);font-size:.9rem;font-weight:400}.topology-note{margin-top:10px;padding:9px 11px;border-radius:6px;background:#f5f7fa;font-size:.85rem}.topology-note a{margin-right:12px}.search{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin:16px 0 4px}.search input{width:min(480px,100%);padding:9px 12px;border:1px solid var(--line);border-radius:6px;font:inherit}.search small{color:var(--muted)}.summary-table{width:100%;border-collapse:collapse;margin:16px 0 28px;font-size:.9rem}.summary-table th,.summary-table td{border:1px solid var(--line);padding:8px 10px;text-align:left;vertical-align:top}.summary-table th{background:var(--panel2);color:#234b70}.schematic-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}.schematic-card{border:1px solid var(--line);border-radius:9px;padding:16px;background:#fff}.schematic-card h3{margin-top:0}.footer{margin-top:42px;padding-top:14px;border-top:1px solid var(--line);color:var(--muted);font-size:.84rem}@media(max-width:1050px){.flow{grid-template-columns:repeat(5,minmax(120px,1fr))}}@media(max-width:760px){.page{width:min(100% - 22px,1540px);padding-top:18px}.utility{margin:-18px 0 18px}.cards,.schematic-grid{grid-template-columns:1fr}.flow{grid-template-columns:repeat(2,minmax(0,1fr))}.card-header{display:block}.status-stack{justify-content:flex-start;margin-top:8px}.card dl{grid-template-columns:5.2rem 1fr}}
"""

# Keep the compact claim/inventory components from the previous project UI;
# they are intentionally presentation-only and are populated from the same
# manifest as the cards below.
CSS += ".claim-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin:20px 0 24px}.claim{padding:14px 15px;border:1px solid var(--line);border-radius:9px;background:#fff}.claim h3{margin-top:0;font-size:1rem}.claim.observed{border-top:4px solid #3c83b5}.claim.derived{border-top:4px solid #6b9f58}.claim.inference{border-top:4px solid #bd8d2c}.claim.unknown{border-top:4px solid #a65a67}.claim ul{margin:5px 0;padding-left:1.15rem}.small{color:var(--muted);font-size:.88rem}.inventory{width:100%;border-collapse:collapse;font-size:.87rem;margin:16px 0 34px}.inventory th,.inventory td{padding:8px 9px;border:1px solid var(--line);vertical-align:top;text-align:left}.inventory th{background:var(--panel2);color:#173a5d}.inventory tr:nth-child(even){background:#fbfcfe}@media(max-width:1050px){.claim-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:650px){.claim-grid{grid-template-columns:1fr}}"


ROLE_LABELS = {
    "COMPARISON": "关键对比图",
    "RESULT": "结果图",
    "POSITIVE_CONTROL": "正向对照",
    "NEGATIVE_CONTROL": "负向对照",
    "ZERO_CONTROL": "零输入对照",
    "SOURCE_REFERENCE": "源波形参考",
    "HISTORICAL_REFERENCE": "历史参考",
    "SUPERSEDED_REFERENCE": "已废止参考",
}


def _esc(value: Any) -> str:
    return html.escape(str(value))


def _href(path: str | None) -> str | None:
    if not path:
        return None
    return "../" + path


def _status_class(status: str) -> str:
    low = status.lower()
    if any(x in low for x in ("pass", "accepted", "valid", "preserved", "gain")):
        return "status-pass"
    if any(x in low for x in ("inconclusive", "subthreshold", "partial", "bounded", "near", "insufficient", "debug")):
        return "status-warn"
    if any(x in low for x in ("failure", "fail", "nonselective", "no_trigger", "no_event")):
        return "status-fail"
    return "status-neutral"


def _role_badge(role: str) -> str:
    if role in {"COMPARISON"}:
        cls = "badge-comparison"
    elif role in {"RESULT"}:
        cls = "badge-result"
    elif role in {"POSITIVE_CONTROL", "NEGATIVE_CONTROL", "ZERO_CONTROL"}:
        cls = "badge-control"
    else:
        cls = "badge-reference"
    return f'<span class="badge {cls}">{_esc(ROLE_LABELS.get(role, role))}</span>'


def _status_badge(status: str) -> str:
    cls = "badge-pass" if _status_class(status) == "status-pass" else ("badge-warn" if _status_class(status) == "status-warn" else ("badge-fail" if _status_class(status) == "status-fail" else "badge-neutral"))
    return f'<span class="badge {cls}">{_esc(status)}</span>'


def _plot_links(entry: dict[str, Any]) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = OrderedDict()
    for plot in entry.get("plots", []):
        path = plot.get("path")
        if not path:
            continue
        role = plot.get("role", "RESULT")
        groups.setdefault(role, []).append(f'<a href="{_esc(_href(path))}">{_esc(PathLabel(path))}</a>')
    return groups


def PathLabel(path: str) -> str:
    # Keep the human label compact while retaining the file identity in the
    # title attribute generated by the browser's link target.
    return path.rsplit("/", 1)[-1].replace(".html", "")


def _topology_links(entry: dict[str, Any], topology_map: dict[str, dict[str, Any]]) -> str:
    topo = topology_map.get(entry.get("topology_id"))
    if not topo:
        return '<div class="topology-note">未登记 representative topology</div>'
    links: list[str] = []
    for label, key in (("论文级电路图", "publication_schematic"), ("实验注释图", "annotated_schematic"), ("连接调试图", "connectivity_debug")):
        target = topo.get(key)
        if target:
            links.append(f'<a href="{_esc(_href(target))}">{_esc(label)}</a>')
        else:
            links.append(f'<span title="尚未生成">{_esc(label)}（待补）</span>')
    chunks = ['<div class="topology-note"><b>电路：</b>' + " ".join(links) + "</div>"]
    variants = entry.get("topology_variants", [])
    if variants:
        variant_rows = []
        for variant in variants:
            label = variant.get("title_cn", variant.get("topology_id", "variant"))
            variant_links = []
            for name, key in (("论文级电路图", "publication_schematic"), ("实验注释图", "annotated_schematic"), ("连接调试图", "connectivity_debug")):
                target = variant.get(key)
                if target:
                    variant_links.append(f'<a href="{_esc(_href(target))}">{_esc(name)}</a>')
                else:
                    variant_links.append(f'<span>{_esc(name)}（待补）</span>')
            variant_rows.append(f'<div><b>{_esc(label)}</b>：{" ".join(variant_links)}</div>')
        chunks.append('<div class="topology-note"><b>真实 topology 变体：</b>' + "".join(variant_rows) + '</div>')
    return "".join(chunks)


def _card(entry: dict[str, Any], topology_map: dict[str, dict[str, Any]]) -> str:
    status = entry.get("scientific_status", "UNKNOWN")
    links = _plot_links(entry)
    groups: list[str] = []
    for role, items in links.items():
        label = ROLE_LABELS.get(role, role)
        groups.append(f'<div class="group"><span class="label">{_esc(label)}</span>{" ".join(items)}</div>')
    report = entry.get("report")
    if report:
        groups.append(f'<div class="group"><span class="label">正式报告</span><a href="{_esc(_href(report))}">打开报告</a></div>')
    sequence = entry.get("sequence", "")
    stage = entry.get("stage_title", "")
    title = entry.get("title_cn", entry.get("experiment_id", ""))
    note = entry.get("notes") or "正式结论以 report 为准；可视化不改变 scientific verdict。"
    return f'''<article class="card {_status_class(status)}" data-search="{_esc(" ".join(str(entry.get(k, "")) for k in ("experiment_id", "title_cn", "scientific_question", "formal_result", "scientific_status")))}">
  <div class="card-header"><div><h3 class="card-title">{_esc(title)}</h3><span class="card-id">{_esc(sequence)} · {_esc(stage)} · {_esc(entry.get("experiment_id", ""))}</span></div><div class="status-stack">{_status_badge(status)} <span class="badge badge-status">{_esc(entry.get("current_status", ""))}</span></div></div>
  <dl><dt>做了什么</dt><dd class="question">{_esc(entry.get("scientific_question", ""))}</dd><dt>关键结果</dt><dd class="result">{_esc(entry.get("formal_result", ""))}</dd><dt>结论边界</dt><dd class="boundary">{_esc(note)}</dd></dl>
  <div class="link-groups">{"".join(groups)}</div>
  {_topology_links(entry, topology_map)}
</article>'''


def _stage_data(entries: list[dict[str, Any]]) -> list[tuple[str, str, list[dict[str, Any]]]]:
    grouped: OrderedDict[str, tuple[str, list[dict[str, Any]]]] = OrderedDict()
    for entry in entries:
        sid = str(entry.get("stage_id", "stage-unknown"))
        title = str(entry.get("stage_title", sid))
        if sid not in grouped:
            grouped[sid] = (title, [])
        grouped[sid][1].append(entry)
    return [(sid, title, rows) for sid, (title, rows) in grouped.items()]


def _flow_nav(stages: list[tuple[str, str, list[dict[str, Any]]]]) -> str:
    return '<nav class="flow" aria-label="实验阶段导航">' + "".join(
        f'<a href="#{_esc(sid)}"><span class="num">{index:02d}</span><span class="label">{_esc(title)}</span><small>{len(rows)} 个实验</small></a>'
        for index, (sid, title, rows) in enumerate(stages, 1)
    ) + "</nav>"


def _summary_table(entries: list[dict[str, Any]]) -> str:
    return '<table class="summary-table"><thead><tr><th>顺序</th><th>实验</th><th>正式状态</th><th>图/电路入口</th></tr></thead><tbody>' + "".join(
        f'<tr><td>{_esc(e.get("sequence", ""))}</td><td>{_esc(e.get("title_cn", e.get("experiment_id", "")))}</td><td>{_status_badge(str(e.get("scientific_status", "UNKNOWN")))}</td><td><a href="#{_esc(e.get("anchor", ""))}">跳到实验卡片</a></td></tr>'
        for e in entries
    ) + "</tbody></table>"


def _legend() -> str:
    return '<div class="legend"><span class="badge badge-result">结果图</span><span class="badge badge-comparison">关键对比</span><span class="badge badge-control">controls</span><span class="badge badge-reference">source / historical reference</span><span class="badge badge-status">论文级 schematic 与 debug graph 分层</span></div>'


def _claim_grid() -> str:
    return '''<div class="claim-grid">
  <div class="claim observed"><h3>Observed</h3><ul><li>canonical BVM 的 read1/read0 与 READ=0 source/storage evidence 已登记。</li><li>R0–R15、QB、paper-JSL 和 JTL/load-boundary 结果按原 report 保留。</li><li>每个 phase 图均标注 continuous phase semantics；local phase turn 不自动等于 SFQ。</li></ul></div>
  <div class="claim derived"><h3>Derived</h3><ul><li>comparison/factorial/load/polarity/convergence 只在所需 cases 全部有图时进入核心入口。</li><li>相同 topology 的参数点共享 clean schematic；改变输出边界或连接关系则分开画图。</li></ul></div>
  <div class="claim inference"><h3>Inference</h3><ul><li>索引只表达 provenance 和阅读顺序，不替代 raw、accepted analysis 或 formal report。</li><li>电路图用于解释连接关系，不表达超出 netlist 的 PASS/FAIL 结论。</li></ul></div>
  <div class="claim unknown"><h3>Unknown / boundary</h3><ul><li>各负结果仍限定于对应 fixture、model、window 和 parameter point。</li><li>完整的 canonical BVM→exactly-one local event→JTL/T1 chain 不能由索引或图形单独推出。</li></ul></div>
</div>'''


def render_index(entries: list[dict[str, Any]], topology: dict[str, Any], *, title: str, flow: bool, head: str) -> str:
    entries = sorted(entries, key=lambda e: (int(e.get("sequence", 10**9)) if str(e.get("sequence", "")).isdigit() else 10**9, e.get("experiment_id", "")))
    for idx, entry in enumerate(entries, 1):
        entry["anchor"] = f"exp-{idx:03d}"
    topology_map = {t.get("topology_id"): t for t in topology.get("topologies", [])}
    stages = _stage_data(entries)
    stage_html = []
    for sid, stage_title, rows in stages:
        cards = "".join(_card(e, topology_map) for e in rows)
        stage_html.append(f'<section class="stage" id="{_esc(sid)}"><div class="stage-title"><span class="stage-no">{_esc(sid.upper())}</span><h2>{_esc(stage_title)} <span class="stage-count">{len(rows)} 个实验</span></h2></div><div class="cards">{cards}</div></section>')
    description = "科研流程导航：按 Exploration 实际执行顺序阅读，每张卡同时提供结果、控制、报告和电路入口。" if flow else "结果图导航：按 Exploration 实际执行顺序阅读，严格区分核心结果、comparison、controls 与 source/reference。"
    nav_links = '<a href="EXPLORATION_FLOW_INDEX.md">Markdown 源索引</a><a href="VISUALIZATION_INDEX.html">可视化总索引</a><a href="CIRCUIT_SCHEMATIC_INDEX.html">电路结构索引</a><a href="VISUALIZATION_READING_GUIDE.md">看图指南</a><a href="HANDOVER.md">项目 handover</a>'
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="description" content="{_esc(description)}"><title>{_esc(title)}</title><style>{CSS}</style></head><body><div class="page"><nav class="utility">{nav_links}<span>manifest 驱动</span><span>记录基线 HEAD：<code>{_esc(head)}</code></span></nav><main><h1>{_esc(title)}</h1><p class="lede">{_esc(description)} 每个节点同时展示结果、controls、报告和真实 topology 的论文级入口。</p><div class="note"><b>阅读原则：</b>索引不创造科学结论；正式 report 是结论 authority。source/reference 不作为 current result，连续相位图也不等于 SFQ 计数。论文级 schematic、annotated schematic 与 connectivity debug graph 分开列出。</div>{_legend()}{_claim_grid()}<div class="search"><input id="exp-filter" type="search" placeholder="筛选实验名称、科学问题或结论…"><small>共 {len(entries)} 个已登记 Exploration · 按实际执行顺序排列</small></div>{_flow_nav(stages)}{_summary_table(entries)}{''.join(stage_html)}<footer class="footer">由 <code>docs/VISUALIZATION_ALIGNMENT_MANIFEST.yaml</code> 生成；当前页面只负责导航和 provenance 展示。</footer></main></div><script>const q=document.getElementById('exp-filter');q.addEventListener('input',()=>{{const s=q.value.trim().toLowerCase();document.querySelectorAll('.card').forEach(c=>c.style.display=(!s||c.dataset.search.toLowerCase().includes(s))?'':'none')}});</script></body></html>\n'''


def render_topology_index(topology: dict[str, Any], *, title: str, head: str) -> str:
    rows = topology.get("topologies", [])
    stages = OrderedDict()
    for topo in rows:
        sid = topo.get("stage_id", "stage-topology")
        stages.setdefault(sid, (topo.get("stage_title", "拓扑导航"), []))[1].append(topo)
    stage_nav = '<nav class="flow" aria-label="拓扑阶段导航">' + "".join(
        f'<a href="#{_esc(sid)}"><span class="num">{i:02d}</span><span class="label">{_esc(title)}</span><small>{len(items)} 个拓扑</small></a>' for i, (sid, (title, items)) in enumerate(stages.items(), 1)
    ) + "</nav>"
    chunks = []
    for sid, (stage_title, items) in stages.items():
        cards = []
        for topo in items:
            links = []
            for label, key in (("论文级电路图", "publication_schematic"), ("实验注释图", "annotated_schematic"), ("连接调试图", "connectivity_debug")):
                target = topo.get(key)
                links.append(f'<a href="{_esc(_href(target))}">{_esc(label)}</a>' if target else f'<span>{_esc(label)}（待补）</span>')
            shared = "、".join(topo.get("shared_by_experiments", []))
            cards.append(f'<article class="schematic-card {_status_class(str(topo.get("status", "")))}"><div class="card-header"><div><h3>{_esc(topo.get("title_cn", topo.get("topology_id", "")))}</h3><span class="card-id">{_esc(topo.get("topology_id", ""))}</span></div>{_status_badge(str(topo.get("status", "")))}</div><p><b>代表 deck：</b><code>{_esc(topo.get("representative_deck") or "未记录")}</code></p><p><b>共享实验：</b>{_esc(shared or "未记录")}</p><div class="link-groups"><div class="group">{" ".join(links)}</div></div></article>')
        chunks.append(f'<section class="stage" id="{_esc(sid)}"><div class="stage-title"><span class="stage-no">{_esc(sid.upper())}</span><h2>{_esc(stage_title)} <span class="stage-count">{len(items)} 个拓扑</span></h2></div><div class="schematic-grid">{"".join(cards)}</div></section>')
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{_esc(title)}</title><style>{CSS}</style></head><body><div class="page"><nav class="utility"><a href="EXPLORATION_FLOW_INDEX.html">流程索引</a><a href="VISUALIZATION_INDEX.html">可视化索引</a><a href="CIRCUIT_SCHEMATIC_INDEX.md">Markdown 版</a><span>记录基线 HEAD：<code>{_esc(head)}</code></span></nav><main><h1>{_esc(title)}</h1><p class="lede">按实验流程组织真实代表 topology；publication schematic、annotated schematic、debug graph 分层显示。相同 topology 的参数点共享 clean schematic。</p>{stage_nav}{''.join(chunks)}<footer class="footer">拓扑来源与 signature 见 <code>docs/TOPOLOGY_ALIGNMENT_MANIFEST.yaml</code>。</footer></main></div></body></html>\n'''
