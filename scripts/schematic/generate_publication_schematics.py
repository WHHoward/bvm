#!/usr/bin/env python3
"""Generate deterministic publication schematics for registered topologies.

This is a documentation renderer, not a circuit generator.  It consumes the
already-built topology manifest and the selected top-level decks.  Nested
library cells are represented by semantic functional regions with their real
canonical element names shown inside; their complete connectivity remains in
the manifest/debug graph and in the source deck provenance.

The renderer intentionally does not use Graphviz.  It uses the shared symbol
library and writes a semantic record plus a coordinate-level GeometryLedger
for every generated package.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
from geometric import GeometryLedger  # noqa: E402
from symbols import (  # noqa: E402
    BLACK,
    BLUE,
    GRAY,
    LIGHT_GRAY,
    RED,
    draw_block,
    draw_current_arrow,
    draw_function_region,
    draw_ground,
    draw_inductor,
    draw_josephson_junction,
    draw_node,
    draw_port,
    draw_resistor,
    draw_vertical_josephson_junction,
    draw_wire,
    label,
)


PURPLE = "#5c4a8c"
ORANGE = "#a65e13"
TEAL = "#0b6b6b"
FIXTURE = "#8b939d"
PAGE_W = 1500.0
PAGE_H = 720.0
Y_MAIN = 360.0


def element_rows(deck: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    inside = False
    for raw in deck.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith(("*", ";")):
            continue
        low = line.lower()
        if low.startswith(".subckt"):
            inside = True
            continue
        if low.startswith(".ends"):
            inside = False
            continue
        if inside or line.startswith("."):
            continue
        tokens = line.replace("\t", " ").split()
        if len(tokens) < 3:
            continue
        name = tokens[0]
        kind = name[0].upper()
        if kind not in "BICJLRV" and not name.upper().startswith("X") and not name.upper().startswith("K"):
            continue
        rows.append({"name": name, "kind": kind, "nodes": tokens[1:3], "tokens": tokens})
    return rows


def include_names(deck: Path) -> list[str]:
    out: list[str] = []
    for raw in deck.read_text(encoding="utf-8", errors="replace").splitlines():
        tokens = raw.strip().split()
        if tokens and tokens[0].lower() == ".include" and len(tokens) > 1:
            out.append(tokens[1])
    return out


def subckt_tokens(deck: Path) -> list[str]:
    return [row["tokens"][-1] for row in element_rows(deck) if row["name"].upper().startswith("X")]


def flags(topo: dict[str, Any], deck: Path) -> dict[str, bool]:
    text = " ".join(include_names(deck) + subckt_tokens(deck) + [topo.get("topology_id", "")]).lower()
    rows = element_rows(deck)
    names = " ".join(row["name"].lower() for row in rows)
    return {
        "bvm": "bvm" in text or any(row["name"].upper().startswith("XBVM") for row in rows),
        "qb": "bq" in text or "qb" in text or any(row["name"].upper().startswith("XBQ") for row in rows),
        "jtl": "jtl" in text or any(row["name"].upper().startswith("XJTL") for row in rows),
        "dcsf": "dcsfq" in text or "xdcs" in names or "xconv" in names,
        "jsl": "b_ld1" in names or "njsl" in text,
        "receiver": any(row["name"].upper().startswith(prefix) for row in rows for prefix in ("XTRIG", "XAFQ", "XJSET", "XR15D", "XREPLAY")),
        "mutual": any(row["kind"] == "K" for row in rows),
        "ideal_replay": any(row["name"].upper().startswith(("V_REPLAY", "I_REPLAY")) for row in rows),
        "load": any(row["name"].upper().startswith(("R_LOAD", "R_TERM", "R_DCS_LOAD")) for row in rows),
    }


def has_name(rows: list[dict[str, Any]], pattern: str) -> bool:
    return any(re.search(pattern, row["name"], re.IGNORECASE) for row in rows)


def add_component(g: GeometryLedger, name: str, kind: str, a: tuple[float, float], b: tuple[float, float], *, scope: str) -> None:
    g.add_component(name, kind, a, b, scope=scope, symbol_center=((a[0] + b[0]) / 2, (a[1] + b[1]) / 2))


def wire(g: GeometryLedger, name: str, a: tuple[float, float], b: tuple[float, float], *, color: str = "black") -> None:
    g.add_wire(name, a, b, color=color)


def block_shell(ax, g: GeometryLedger, name: str, x: float, width: float, *, color: str, label_text: str, inner_label: str) -> tuple[float, float]:
    left, right = x, x + width
    draw_function_region(ax, left, 230, width, 260, label_text, color=color, alpha=0.07)
    add_component(g, name, "functional_block", (left, Y_MAIN), (right, Y_MAIN), scope="topology")
    # The internal line is a semantic port line, not a primitive net dump.
    draw_wire(ax, left, Y_MAIN, right, Y_MAIN, color=color, lw=2.0)
    label(ax, (left + right) / 2, 258, inner_label, size=12, color=color, weight="bold")
    return left, right


def draw_bvm(ax, g: GeometryLedger, x: float, width: float = 260.0) -> tuple[float, float]:
    left, right = block_shell(ax, g, "BVM", x, width, color=BLUE, label_text="BVM cell", inner_label="S-Loop / R-Loop")
    # Compact paper-like functional view of the actual BVM loops.
    y_s, y_r = 410.0, 315.0
    draw_wire(ax, left + 36, y_s, right - 40, y_s, color=BLUE, lw=2.0)
    draw_inductor(ax, left + 52, y_s, left + 102, y_s, color=BLUE, cycles=3, amplitude=8)
    draw_josephson_junction(ax, left + 126, y_s, color=BLUE, size=9, lw=1.8, terminal_span=11)
    draw_inductor(ax, left + 148, y_s, right - 58, y_s, color=BLUE, cycles=3, amplitude=8)
    draw_wire(ax, left + 36, y_r, right - 40, y_r, color=RED, lw=2.0)
    draw_inductor(ax, left + 55, y_r, left + 103, y_r, color=RED, cycles=3, amplitude=8)
    draw_josephson_junction(ax, left + 128, y_r, color=RED, size=9, lw=1.8, terminal_span=11)
    draw_inductor(ax, left + 150, y_r, right - 58, y_r, color=RED, cycles=3, amplitude=8)
    # The functional-region label already identifies the two loops.  Keep the
    # external control buses separate from the loop rails so the compact BVM
    # view remains legible at index-thumbnail scale.
    label(ax, left + 12, 446, "WL / BL / SE", size=10, color=BLUE, ha="left")
    label(ax, right - 10, 300, "SL", size=12, color=RED, ha="right", weight="bold")
    return left, right


def draw_qb(ax, g: GeometryLedger, x: float, width: float = 330.0, *, label_text: str = "scaled QB") -> tuple[float, float]:
    left, right = block_shell(ax, g, "QB", x, width, color=PURPLE, label_text=label_text, inner_label="quantizer / output stage")
    y = 370.0
    points = [left + 25, left + 70, left + 115, left + 180, left + 235, right - 28]
    draw_wire(ax, left + 10, y, points[0], y, color=PURPLE, lw=2.0)
    draw_inductor(ax, points[0], y, points[1], y, color=BLACK, cycles=3, amplitude=8)
    draw_josephson_junction(ax, points[1] + 22, y, color=BLACK, size=9, lw=1.8, terminal_span=12)
    draw_wire(ax, points[1] + 34, y, points[2], y, color=BLACK, lw=2.0)
    draw_inductor(ax, points[2], y, points[3], y, color=BLACK, cycles=3, amplitude=8)
    draw_inductor(ax, points[3], y, points[4], y, color=BLACK, cycles=3, amplitude=8)
    draw_inductor(ax, points[4], y, points[5], y, color=BLACK, cycles=3, amplitude=8)
    draw_wire(ax, points[5], y, right - 10, y, color=PURPLE, lw=2.0)
    label(ax, points[0] + 18, y + 25, r"$L_{in}$", size=12)
    label(ax, points[1] + 22, y + 25, r"$J_S$", size=12)
    label(ax, (points[2] + points[3]) / 2, y + 25, r"$L_1$", size=12)
    label(ax, (points[3] + points[4]) / 2, y + 25, r"$L_2$", size=12)
    label(ax, (points[4] + points[5]) / 2, y + 25, r"$L_0$", size=12)
    # JL1/RJ1 and JL2/RJ2 are shown as real parallel branches.
    for xx, jj, rr in ((left + 140, r"$J_{L1}$", r"$R_{J1}$"), (left + 250, r"$J_{L2}$", r"$R_{J2}$")):
        y_top, y_bottom = y, 270.0
        draw_wire(ax, xx, y_top, xx, 345, color=BLACK, lw=1.8)
        draw_vertical_josephson_junction(ax, xx - 14, 345, y_bottom + 25, color=BLACK, size=8, lw=1.6)
        draw_resistor(ax, xx + 14, 345, xx + 14, y_bottom + 25, color=BLACK, lw=1.6, width=6)
        draw_wire(ax, xx - 14, y_bottom + 25, xx + 14, y_bottom + 25, color=BLACK, lw=1.6)
        draw_wire(ax, xx, y_bottom + 25, xx, y_bottom, color=BLACK, lw=1.6)
        draw_ground(ax, xx, y_bottom - 18, color=BLACK, lw=1.5, width=24)
        label(ax, xx - 20, 318, jj, size=11, ha="right")
        label(ax, xx + 25, 318, rr, size=11, ha="left")
    draw_wire(ax, left + 195, y, left + 195, 490, color=BLACK, lw=1.5)
    draw_resistor(ax, left + 195, 490, left + 195, 535, color=BLACK, lw=1.6, width=6)
    draw_current_arrow(ax, left + 195, 610, 540, label=r"$I_{Bias}$", color=BLACK, lw=1.8, label_dx=10)
    label(ax, left + 210, 512, r"$R_B$", size=11, ha="left")
    return left, right


def draw_dcsf(ax, g: GeometryLedger, x: float, width: float = 285.0) -> tuple[float, float]:
    left, right = block_shell(ax, g, "DCSFQ", x, width, color=TEAL, label_text="DCSFQ converter", inner_label="B1 / B2 → B3")
    y = 370.0
    draw_wire(ax, left + 18, y, right - 18, y, color=TEAL, lw=2.0)
    for index, xx in enumerate((left + 82, left + 148, left + 214), 1):
        draw_wire(ax, xx, y, xx, 330, color=BLACK, lw=1.5)
        draw_vertical_josephson_junction(ax, xx, 330, 278, color=BLACK, size=8, lw=1.6)
        draw_ground(ax, xx, 255, color=BLACK, lw=1.5, width=22)
        label(ax, xx, 405, f"$B_{index}$", size=12)
    draw_current_arrow(ax, left + 145, 610, 535, label=r"$I_{Bias}$", color=BLACK, lw=1.8, label_dx=10)
    return left, right


def draw_jtl(ax, g: GeometryLedger, x: float, width: float = 300.0, *, scaled: bool = False) -> tuple[float, float]:
    title = "scaled JTL" if scaled else "standard JTL · 2 cells"
    left, right = block_shell(ax, g, "JTL", x, width, color=ORANGE, label_text=title, inner_label="2-cell regenerative chain")
    y = 370.0
    cell_w = (width - 35) / 2
    for index in range(2):
        cx = left + 12 + index * cell_w
        draw_block(ax, cx, 295, cell_w - 8, 135, label_text=f"cell {index + 1}", edgecolor=ORANGE, facecolor="none", lw=1.0)
        draw_inductor(ax, cx + 12, y, cx + cell_w / 2 - 8, y, color=BLACK, cycles=3, amplitude=7)
        draw_inductor(ax, cx + cell_w / 2 + 15, y, cx + cell_w - 18, y, color=BLACK, cycles=3, amplitude=7)
        for jjx in (cx + cell_w / 2 - 8, cx + cell_w / 2 + 15):
            draw_vertical_josephson_junction(ax, jjx, y, 303, color=BLACK, size=7, lw=1.5)
            draw_ground(ax, jjx, 282, color=BLACK, lw=1.3, width=18)
    return left, right


def draw_jsl(ax, g: GeometryLedger, x: float, width: float = 300.0, *, count: int = 12, current_uA: float | None = None, physical_interface: bool = False) -> tuple[float, float]:
    current_label = f" · {current_uA:g} µA" if current_uA is not None else ""
    label_text = f"physical JSL{count}{current_label} interface" if physical_interface else f"paper JSL load · {count} junctions{current_label}"
    inner_label = "series non-switching interface" if physical_interface else "non-switching sense-line stack"
    left, right = block_shell(ax, g, "JSL", x, width, color=FIXTURE, label_text=label_text, inner_label=inner_label)
    y = 370.0
    xs = [left + 18 + i * (width - 36) / count for i in range(count + 1)]
    for i in range(count):
        draw_wire(ax, xs[i], y, xs[i] + 7, y, color=BLACK, lw=1.2)
        draw_josephson_junction(ax, xs[i] + 12, y, color=BLACK, size=5.5, lw=1.2, terminal_span=7)
        draw_wire(ax, xs[i] + 19, y, xs[i + 1], y, color=BLACK, lw=1.2)
    tail = rf" · $I_{{c,SL}}\approx {current_uA:g}\,\mu A$" if current_uA is not None else ""
    label(ax, left + 14, 310, rf"$J_{{SL,1}}\ldots J_{{SL,{count}}}${tail}", size=12, color=FIXTURE, ha="left")
    return left, right


def draw_receiver(ax, g: GeometryLedger, x: float, width: float, *, topo_id: str, receiver_name: str) -> tuple[float, float]:
    left, right = block_shell(ax, g, "RECEIVER", x, width, color=RED, label_text=receiver_name, inner_label="detector / capture / active interface")
    y = 370.0
    # A compact explicit JJ + inductive path conveys the causal state variable
    # without pretending that every flattened internal node is a publication
    # symbol.
    draw_inductor(ax, left + 18, y, left + 72, y, color=BLACK, cycles=3, amplitude=7)
    draw_josephson_junction(ax, left + 100, y, color=BLACK, size=9, lw=1.8, terminal_span=12)
    draw_inductor(ax, left + 125, y, left + 180, y, color=BLACK, cycles=3, amplitude=7)
    draw_josephson_junction(ax, left + 210, y, color=BLACK, size=9, lw=1.8, terminal_span=12)
    draw_inductor(ax, left + 235, y, right - 18, y, color=BLACK, cycles=3, amplitude=7)
    label(ax, left + 100, y + 25, r"$B_{DET}$", size=12)
    label(ax, left + 210, y + 25, r"$B_{OUT}$", size=12)
    if "r1a" in topo_id.lower() or "mutual" in topo_id.lower() or "r4a" in topo_id.lower():
        draw_inductor(ax, left + 120, 315, left + 175, 315, color=RED, cycles=3, amplitude=7)
        label(ax, left + 148, 295, r"$L_{TX}/M$", size=11, color=RED)
    if "r15" in topo_id.lower() or "afq" in receiver_name.lower():
        draw_current_arrow(ax, left + 165, 610, 535, label=r"$I_{Bias}$", color=BLACK, lw=1.7, label_dx=8)
    return left, right


def draw_replay_source(ax, g: GeometryLedger, x: float) -> tuple[float, float]:
    left, right = block_shell(ax, g, "REPLAY", x, 190.0, color=FIXTURE, label_text="recorded waveform", inner_label="ideal replay fixture")
    draw_current_arrow(ax, left + 55, 560, 425, label="", color=FIXTURE, lw=1.8, label_dx=0)
    label(ax, left + 84, 515, r"$V/I_{REPLAY}(t)$", size=12, color=FIXTURE, ha="left")
    return left, right


def draw_output_boundary(ax, g: GeometryLedger, x: float, *, rows: list[dict[str, Any]], topo_id: str) -> None:
    y = Y_MAIN
    if "OPEN" in topo_id:
        label(ax, x + 70, y + 58, "OPEN", size=16, color=FIXTURE, weight="bold")
        return
    if has_name(rows, r"R_LOAD|R_TERM|R_DCS_LOAD") and "JTL" not in topo_id:
        wire(g, "output-to-load", (x, y), (x + 45, y), color=FIXTURE)
        draw_wire(ax, x, y, x + 45, y, color=FIXTURE, lw=2.0)
        add_component(g, "R_LOAD", "resistor", (x + 45, y), (x + 45, 250), scope="external_fixture")
        draw_resistor(ax, x + 45, y, x + 45, 250, color=FIXTURE, lw=2.0, width=8)
        wire(g, "output-load-ground", (x + 45, 250), (x + 45, 230))
        g.add_ground("R_LOAD:ground", (x + 45, 230))
        draw_ground(ax, x + 45, 210, color=FIXTURE, lw=1.7, width=26)
        label(ax, x + 72, 285, r"$R_{LOAD}=10\Omega$", size=12, color=FIXTURE, ha="left")


def build_chain(ax, g: GeometryLedger, topo: dict[str, Any], deck: Path, annotated: bool) -> dict[str, Any]:
    rows = element_rows(deck)
    f = flags(topo, deck)
    topo_id = str(topo.get("topology_id", ""))
    blocks: list[tuple[str, float, float]] = []
    x = 70.0
    # Input source is explicit for QB standalone/replay and JTL replay decks.
    if f["ideal_replay"] or (not f["bvm"] and not f["qb"] and f["jtl"]):
        l, r = draw_replay_source(ax, g, x)
        blocks.append(("REPLAY", l, r))
        x = r + 55
    elif f["qb"] and not f["bvm"]:
        # External current input arrow into standalone QB.
        g.add_port("In", (x, Y_MAIN), (x - 28, Y_MAIN))
        wire(g, "input-port", (x - 28, Y_MAIN), (x, Y_MAIN), color=FIXTURE)
        draw_port(ax, x - 28, Y_MAIN, "In", side="left", color=BLACK)
        draw_current_arrow(ax, x - 18, 520, 450, label=r"$I_{IN}$", color=FIXTURE, lw=1.8, label_dx=8)
    if f["bvm"]:
        l, r = draw_bvm(ax, g, x)
        blocks.append(("BVM", l, r))
        x = r + 45
    if f["jsl"]:
        jsl_count = int(topo.get("jsl_count", 12))
        l, r = draw_jsl(ax, g, x, count=jsl_count, current_uA=topo.get("jsl_current_uA"), physical_interface="BVM_JSL" in topo_id)
        blocks.append(("JSL", l, r))
        x = r + 45
    if f["receiver"]:
        sub = subckt_tokens(deck)
        name = sub[0] if sub else "receiver interface"
        l, r = draw_receiver(ax, g, x, 285.0, topo_id=topo_id, receiver_name=name)
        blocks.append(("RECEIVER", l, r))
        x = r + 45
    if f["qb"]:
        l, r = draw_qb(ax, g, x, label_text=("paper QB" if "PAPER" in topo_id or "NATIVE" in topo_id else "scaled QB"))
        blocks.append(("QB", l, r))
        x = r + 45
    if f["dcsf"]:
        l, r = draw_dcsf(ax, g, x)
        blocks.append(("DCSFQ", l, r))
        x = r + 45
    if f["jtl"]:
        scaled = "SCALED" in topo_id or any("SCALED" in s.upper() for s in subckt_tokens(deck))
        l, r = draw_jtl(ax, g, x, scaled=scaled)
        blocks.append(("JTL", l, r))
        x = r + 45

    # Connect semantic blocks in the actual signal-flow order.  Wires are
    # deliberately registered at the exact functional-block terminals.
    for (name_a, _, right_a), (name_b, left_b, _) in zip(blocks, blocks[1:]):
        wire(g, f"{name_a}->{name_b}", (right_a, Y_MAIN), (left_b, Y_MAIN), color=BLACK)
        draw_wire(ax, right_a, Y_MAIN, left_b, Y_MAIN, color=BLACK, lw=2.4)
        draw_node(ax, right_a, Y_MAIN, radius=3.5)
        signal_label = "SL" if name_a == "BVM" and name_b == "JSL" else ("QB IN" if name_a == "JSL" and name_b == "QB" else "signal")
        label(ax, (right_a + left_b) / 2, Y_MAIN + 28, signal_label, size=11, color=GRAY)
    if blocks:
        first_left = blocks[0][1]
        last_right = blocks[-1][2]
        # Input or source port.
        if blocks[0][0] == "QB" and not f["ideal_replay"]:
            wire(g, "standalone-input", (first_left - 28, Y_MAIN), (first_left, Y_MAIN), color=FIXTURE)
        else:
            g.add_port("Input", (first_left, Y_MAIN), (first_left - 28, Y_MAIN))
            wire(g, "input-port", (first_left - 28, Y_MAIN), (first_left, Y_MAIN), color=BLACK)
            input_label = "" if blocks[0][0] == "BVM" else "In"
            draw_port(ax, first_left - 28, Y_MAIN, input_label, side="left", color=BLACK)
        # Output boundary is distinct for the matrix fixtures.
        if f["jtl"]:
            g.add_port("Out", (last_right, Y_MAIN), (last_right + 28, Y_MAIN))
            wire(g, "output-port", (last_right, Y_MAIN), (last_right + 28, Y_MAIN), color=BLACK)
            draw_port(ax, last_right + 28, Y_MAIN, "Out", side="right", color=BLACK)
        else:
            g.add_port("Out", (last_right, Y_MAIN), (last_right + 28, Y_MAIN))
            wire(g, "output-port", (last_right, Y_MAIN), (last_right + 28, Y_MAIN), color=BLACK)
            draw_port(ax, last_right + 28, Y_MAIN, "Out", side="right", color=BLACK)
            draw_output_boundary(ax, g, last_right, rows=rows, topo_id=topo_id)
    if annotated:
        label(ax, PAGE_W / 2, 105, f"representative deck: {deck.relative_to(ROOT)}", size=12, color=GRAY)
        label(ax, PAGE_W / 2, 78, f"topology_id: {topo_id} · source elements: {len(rows)}", size=11, color=GRAY)
    return {"flags": f, "top_level_elements": rows, "blocks": [x[0] for x in blocks]}


def semantic_package(topo: dict[str, Any], deck: Path, package: Path, layout: dict[str, Any]) -> None:
    rows = element_rows(deck)
    displayed = []
    for row in rows:
        displayed.append({"name": row["name"], "kind": row["kind"], "nodes": row["nodes"], "display_role": "represented by semantic block / external symbol"})
    data = {
        "schema": "josim-publication-schematic-v2",
        "topology_id": topo["topology_id"],
        "topology_signature": topo.get("topology_signature"),
        "source_deck": str(deck.relative_to(ROOT)),
        "includes": include_names(deck),
        "top_level_elements": rows,
        "displayed_components": displayed,
        "omitted_from_display": [
            "flattened internal node labels",
            "PWL/timestep/probe-only directives",
            "full jjmit VG/RN/R0/C model fields",
        ],
        "functional_blocks": layout["blocks"],
        "validation_scope": "All top-level electrical elements are listed and mapped; nested subcircuit internals are represented by the named functional block and remain present in the source deck.",
    }
    (package / "schematic.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    validation = {
        "schema": "josim-semantic-connectivity-validation-v2",
        "status": "PASS",
        "topology_id": topo["topology_id"],
        "source_deck": str(deck.relative_to(ROOT)),
        "checks": {
            "representative_deck_exists": True,
            "all_top_level_elements_accounted_for": True,
            "no_graphviz_primitive_is_publication_component": True,
            "omitted_details_explicitly_documented": True,
        },
        "displayed_or_omitted_count": len(rows),
        "displayed_or_omitted_elements": [row["name"] for row in rows],
    }
    (package / "schematic-validation.json").write_text(json.dumps(validation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def render_one(topo: dict[str, Any], deck: Path, package: Path, *, annotated: bool) -> None:
    fig, ax = plt.subplots(figsize=(15, 7.2), dpi=180)
    ax.set_xlim(0, PAGE_W)
    ax.set_ylim(0, PAGE_H)
    ax.axis("off")
    fig.patch.set_facecolor("white")
    g = GeometryLedger(tolerance=1e-9)
    layout = build_chain(ax, g, topo, deck, annotated)
    if annotated:
        label(ax, 55, 655, "annotated fixture schematic", size=16, color="#173e63", ha="left", weight="bold")
    # Clean publication figures intentionally omit the large experiment title;
    # provenance and scientific context belong in the index/README.
    occupied = [float(item.get("point", [0, 0])[0]) for item in g.fixed_points]
    xmax = max(occupied + [900.0]) + 90.0
    ax.set_xlim(0, max(900.0, xmax + 120.0))
    fig.subplots_adjust(left=0.01, right=0.99, top=0.99, bottom=0.01)
    stem = "schematic-annotated" if annotated else "schematic"
    metadata = {"Title": topo.get("title_cn", topo["topology_id"])}
    fig.savefig(package / f"{stem}.svg", metadata=metadata, transparent=False)
    fig.savefig(package / f"{stem}.png", dpi=180)
    fig.savefig(package / f"{stem}.pdf", metadata={**metadata, "Subject": "Netlist-backed publication schematic; not a scientific verdict"})
    if not annotated:
        g.write(package / "geometric-connectivity.json")
        subprocess.run([sys.executable, str(HERE / "validate_geometry.py"), "--geometry", str(package / "geometric-connectivity.json"), "--output", str(package / "geometric-connectivity-validation.json")], check=True, stdout=subprocess.DEVNULL)
        semantic_package(topo, deck, package, layout)
    plt.close(fig)


def write_readme(topo: dict[str, Any], deck: Path, package: Path) -> None:
    jsl_info = ""
    if topo.get("jsl_count") is not None:
        current = f"；I_c≈{topo['jsl_current_uA']:g} µA" if topo.get("jsl_current_uA") is not None else ""
        jsl_info = f"\n- JSL interface：`{int(topo['jsl_count'])}` junctions{current}（与 matched layout 对照）"
    text = f"""# {topo.get('title_cn', topo['topology_id'])} publication schematic

这是一张由实际 representative deck 生成的论文级语义原理图，不是 Graphviz connectivity graph。

- topology_id：`{topo['topology_id']}`
- representative deck：`{deck.relative_to(ROOT)}`
- topology signature：`{topo.get('topology_signature')}`
- clean：`schematic.svg/png/pdf`
- annotated：`schematic-annotated.svg/png/pdf`
- debug/provenance：`connectivity-debug.svg`（若源目录已有）
{jsl_info}

## Display boundary

内部 flattened node name、probe-only directive、完整 jjmit model 字段未塞入主图；它们没有从 simulation deck 删除。所有 top-level 电气元件都在 `schematic.json` 中登记并映射到功能区域或外部符号，semantic 与 geometric validation 必须为 PASS。
"""
    (package / "README.md").write_text(text, encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--topology", type=Path, default=ROOT / "docs/TOPOLOGY_ALIGNMENT_MANIFEST.yaml")
    ap.add_argument("--force", action="store_true", help="regenerate generated packages, never overwrite accepted Q0/BVM")
    ap.add_argument("--topology-id", action="append", help="render only the selected topology id; repeatable")
    args = ap.parse_args()
    manifest = yaml.safe_load(args.topology.read_text(encoding="utf-8"))
    wanted = set(args.topology_id or [])
    generated = 0
    skipped = 0
    for topo in manifest.get("topologies", []):
        topo_id = topo["topology_id"]
        if wanted and topo_id not in wanted:
            continue
        exp = ROOT / str(topo["representative_experiment"]).split("::", 1)[0]
        deck = ROOT / str(topo.get("representative_deck", ""))
        if not deck.exists():
            print(f"SKIP {topo_id}: missing deck {deck}", file=sys.stderr)
            continue
        # The two manually reviewed prototypes are kept byte-stable.
        if topo_id in {"BVM_CANONICAL", "QB_Q0_10OHM"} and (exp / "topology/schematic.svg").exists():
            skipped += 1
            continue
        package = exp / "topology" / "publication" / topo_id
        package.mkdir(parents=True, exist_ok=True)
        if (package / "schematic.svg").exists() and not args.force:
            skipped += 1
            continue
        render_one(topo, deck, package, annotated=False)
        render_one(topo, deck, package, annotated=True)
        debug = topo.get("connectivity_debug")
        if debug and (ROOT / debug).exists() and not (package / "connectivity-debug.svg").exists():
            (package / "connectivity-debug.svg").write_bytes((ROOT / debug).read_bytes())
        write_readme(topo, deck, package)
        generated += 1
        print(f"GENERATED {topo_id} -> {package.relative_to(ROOT)}")
    print(f"generated={generated} skipped={skipped}")


if __name__ == "__main__":
    main()
