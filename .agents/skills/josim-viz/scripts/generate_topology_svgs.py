#!/usr/bin/env python3
"""Flatten local JoSIM subcircuits and render a complete Graphviz topology SVG.

This is a structural renderer. It does not simulate, simplify away components,
or infer paper-only parts. It resolves .include and X/.subckt instances, then
draws primitive elements, exact nets, and K mutual couplings.
"""
from __future__ import annotations

import argparse
import html
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Primitive:
    name: str
    kind: str
    a: str
    b: str
    value: str
    hierarchy: str


@dataclass
class Mutual:
    name: str
    left: str
    right: str
    value: str
    hierarchy: str


@dataclass
class Subckt:
    name: str
    ports: list[str]
    lines: list[str]
    source: Path


def clean_lines(path: Path) -> list[str]:
    out = []
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        raw = raw.strip()
        if not raw or raw.startswith("*") or raw.startswith("+"):
            continue
        out.append(raw)
    return out


def parse_subckts(path: Path, seen: set[Path] | None = None) -> dict[str, Subckt]:
    seen = set() if seen is None else seen
    path = path.resolve()
    if path in seen or not path.exists():
        return {}
    seen.add(path)
    result: dict[str, Subckt] = {}
    current: Subckt | None = None
    for line in clean_lines(path):
        toks = line.split()
        low = toks[0].lower()
        if low == ".include" and len(toks) > 1:
            result.update(parse_subckts((path.parent / toks[1]).resolve(), seen))
        elif low == ".subckt" and len(toks) >= 2:
            current = Subckt(toks[1], toks[2:], [], path)
            result[current.name.lower()] = current
        elif low == ".ends":
            current = None
        elif current is not None:
            current.lines.append(line)
    return result


def split_main(path: Path) -> tuple[list[str], dict[str, Subckt]]:
    subs = parse_subckts(path, seen=set())
    main: list[str] = []
    for line in clean_lines(path):
        toks = line.split()
        low = toks[0].lower()
        if low == ".include" and len(toks) > 1:
            subs.update(parse_subckts((path.parent / toks[1]).resolve(), seen=set()))
        elif not low.startswith("."):
            main.append(line)
    return main, subs


def map_node(node: str, node_map: dict[str, str], hierarchy: str) -> str:
    """Resolve a node in the current instance without inventing top-level nets."""
    if node in node_map:
        return node_map[node]
    return f"{hierarchy}/{node}" if hierarchy else node


def primitive(line: str, hierarchy: str) -> Primitive | Mutual | None:
    toks = line.split()
    if not toks:
        return None
    name = toks[0]
    first = name[0].upper()
    if first == "K" and len(toks) >= 4:
        return Mutual(name, toks[1], toks[2], " ".join(toks[3:]), hierarchy)
    if first not in "RLCBIVEXGFP" or len(toks) < 3:
        return None
    return Primitive(name, first, toks[1], toks[2], " ".join(toks[3:]), hierarchy)


def flatten(lines: list[str], subs: dict[str, Subckt], node_map: dict[str, str], hierarchy: str,
            out_p: list[Primitive], out_k: list[Mutual]) -> None:
    local_elements: dict[str, str] = {}
    for line in lines:
        toks = line.split()
        if not toks:
            continue
        if toks[0].lower().startswith("x") and len(toks) >= 3 and toks[-1].lower() in subs:
            sub = subs[toks[-1].lower()]
            actual = toks[1:-1]
            ports = {p: map_node(a, node_map, hierarchy) for p, a in zip(sub.ports, actual)}
            child_h = f"{hierarchy}/{toks[0]}" if hierarchy else toks[0]
            flatten(sub.lines, subs, ports, child_h, out_p, out_k)
            continue
        item = primitive(line, hierarchy)
        if item is None:
            continue
        if isinstance(item, Mutual):
            item.left = local_elements.get(item.left, f"{hierarchy}/{item.left}")
            item.right = local_elements.get(item.right, f"{hierarchy}/{item.right}")
            out_k.append(item)
            continue
        item.name = f"{hierarchy}/{item.name}" if hierarchy else item.name
        item.a = map_node(item.a, node_map, hierarchy)
        item.b = map_node(item.b, node_map, hierarchy)
        out_p.append(item)
        local_elements[toks[0]] = item.name


def group_for(h: str) -> tuple[str, str]:
    u = h.upper()
    if any(x in u for x in ("BVM", "XBVM", "JM", "JS")):
        return "BVM / source", "#dcecff"
    if any(x in u for x in ("JTL", "XJTL", "THMITLL")):
        return "standard JTL", "#ffe7c2"
    if any(x in u for x in ("BQ", "BJL", "BJS", "DCSFQ", "XBQ")):
        return "QB / regenerator", "#eadcff"
    if any(x in u for x in ("TRIG", "RECEIVER", "SET", "QMODE", "QJ", "OUT", "TX", "SEC", "AFQ")):
        return "receiver / interface", "#d9f3ee"
    return "bias / top-level", "#f1f3f5"


def esc(value: str) -> str:
    return html.escape(value.replace('"', '\\"'))


def compact_label(value: str, limit: int = 180) -> str:
    """Keep long PWL/source expressions from exceeding Graphviz quoted strings."""
    if len(value) <= limit:
        return value
    head = max(40, limit - 55)
    return value[:head] + " ... [value shortened for diagram; source deck is exact] ... " + value[-35:]


def build_dot(primitives: list[Primitive], mutuals: list[Mutual], source: Path, title: str) -> str:
    nets = sorted({x for p in primitives for x in (p.a, p.b)})
    groups: dict[str, list[Primitive]] = {}
    for p in primitives:
        groups.setdefault(p.hierarchy.split("/")[0] if p.hierarchy else "top-level", []).append(p)
    lines = ["digraph topology {", 'graph [rankdir=LR, splines=polyline, overlap=false, nodesep=0.32, ranksep=1.0, pad=0.3, bgcolor="white"];', 'node [fontname="DejaVu Sans", fontsize=9, margin="0.08,0.05"];', 'edge [fontname="DejaVu Sans", fontsize=8, color="#65758b"];']
    lines.append(f'label="{esc(title)}\\nsource: {esc(str(source))}"; labelloc=t; fontsize=16; fontname="DejaVu Sans";')
    for gname, group_items in groups.items():
        label, fill = group_for(gname)
        lines += [f'subgraph "cluster_{esc(gname)}" {{', f'label="{esc(label)}\\n({esc(gname)})";', f'color="{fill}"; style="rounded,filled"; fillcolor="{fill}55";']
        for p in group_items:
            pid = "e_" + re.sub(r"[^A-Za-z0-9_]", "_", p.name)
            label = p.name + chr(92) + chr(110) + "[" + p.kind + "] " + compact_label(p.value)
            lines.append(f'"{pid}" [shape=box, style="rounded,filled", fillcolor="white", label="{esc(label)}"];')
        lines.append("}")
    for net in nets:
        nid = "n_" + re.sub(r"[^A-Za-z0-9_]", "_", net)
        lines.append(f'"{nid}" [shape=ellipse, style=filled, fillcolor="#fffdf2", label="{esc(net)}"];')
    for p in primitives:
        pid = "e_" + re.sub(r"[^A-Za-z0-9_]", "_", p.name)
        for net, port in ((p.a, "a"), (p.b, "b")):
            nid = "n_" + re.sub(r"[^A-Za-z0-9_]", "_", net)
            lines.append(f'"{pid}" -> "{nid}" [dir=none, label="{port}"];')
    for i, k in enumerate(mutuals):
        kid = f"k_{i}_{re.sub(r'[^A-Za-z0-9_]', '_', k.name)}"
        left = "e_" + re.sub(r"[^A-Za-z0-9_]", "_", k.left)
        right = "e_" + re.sub(r"[^A-Za-z0-9_]", "_", k.right)
        k_label = k.name + chr(92) + chr(110) + "K=" + compact_label(k.value)
        lines.append(f'"{kid}" [shape=diamond, style=filled, fillcolor="#f5d6ff", label="{esc(k_label)}"];')
        lines.append(f'"{kid}" -> "{left}" [dir=none, style=dashed];')
        lines.append(f'"{kid}" -> "{right}" [dir=none, style=dashed];')
    lines += [f'legend [shape=note, label="Legend\\nboxes: primitive elements\\nellipses: exact nets\\ndiamonds: mutual coupling\\nsource: {esc(str(source))}", color="#8c98a8"];', "}"]
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("deck", type=Path)
    ap.add_argument("--output-dir", type=Path, required=True)
    ap.add_argument("--title", default="JoSIM Exploration topology")
    args = ap.parse_args()
    main_lines, subs = split_main(args.deck)
    primitives: list[Primitive] = []
    mutuals: list[Mutual] = []
    flatten(main_lines, subs, {}, "", primitives, mutuals)
    if not primitives:
        raise SystemExit(f"no primitive elements found in {args.deck}")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    dot = build_dot(primitives, mutuals, args.deck, args.title)
    (args.output_dir / "topology.dot").write_text(dot, encoding="utf-8")
    subprocess.run(["dot", "-Tsvg", str(args.output_dir / "topology.dot"), "-o", str(args.output_dir / "topology.svg")], check=True)
    print(f"{args.deck}: {len(primitives)} primitives, {len(mutuals)} mutuals -> {args.output_dir / 'topology.svg'}")


if __name__ == "__main__":
    main()
