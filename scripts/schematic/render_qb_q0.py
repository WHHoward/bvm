#!/usr/bin/env python3
"""Render the accepted scaled Q0 QB fixture as a publication schematic.

This renderer is intentionally semantic and deterministic. It does not use
Graphviz for layout: the Q0 signal path is placed left-to-right, bias is above,
and returns are below. The same geometry produces a clean paper figure and a
separately annotated experiment figure.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from geometric import GeometryLedger  # noqa: E402
from symbols import (  # noqa: E402
    BLACK,
    GRAY,
    LIGHT_GRAY,
    draw_current_arrow,
    draw_ground,
    draw_inductor,
    draw_josephson_junction,
    draw_vertical_josephson_junction,
    draw_node,
    draw_port,
    draw_resistor,
    draw_wire,
    label,
)


Y_MAIN = 325.0
X_IN_TERMINAL = 83.0
X_LOAD_NODE = 1030.0


def _wire(geometry: GeometryLedger | None, name: str,
          start: tuple[float, float], end: tuple[float, float], *,
          color: str = "black") -> None:
    if geometry is not None:
        geometry.add_wire(name, start, end, color=color)


def _component(geometry: GeometryLedger | None, name: str, kind: str,
               start: tuple[float, float], end: tuple[float, float], *,
               center: tuple[float, float] | None = None,
               scope: str = "BQ") -> None:
    if geometry is not None:
        geometry.add_component(name, kind, start, end, scope=scope,
                               symbol_center=center)


def draw_parallel_ground_branch(
    ax,
    x: float,
    y_node: float,
    *,
    jj_name: str,
    jj_label: str,
    jj_ic: str,
    r_name: str,
    r_label: str,
    r_value: str,
    annotated: bool,
    geometry: GeometryLedger | None,
) -> None:
    """Draw a real JJ || RJ branch from a main-path node to ground."""
    y_split = 260.0
    y_bottom = 175.0
    y_ground_terminal = 150.0
    left = x - 26.0
    right = x + 26.0
    center_y = (y_split + y_bottom) / 2.0

    if geometry is not None:
        geometry.add_anchor(f"{jj_name}:split", (x, y_split))
        geometry.add_anchor(f"{jj_name}:ground_join", (x, y_bottom))
        geometry.add_ground(f"{jj_name}:ground", (x, y_ground_terminal))
        _component(geometry, jj_name, "josephson_junction",
                   (left, y_split), (left, y_bottom),
                   center=(left, center_y))
        _component(geometry, r_name, "resistor",
                   (right, y_split), (right, y_bottom))
        _wire(geometry, f"{jj_name}:drop", (x, y_node), (x, y_split))
        _wire(geometry, f"{jj_name}:top_join",
              (left, y_split), (right, y_split))
        _wire(geometry, f"{jj_name}:bottom_join",
              (left, y_bottom), (right, y_bottom))
        _wire(geometry, f"{jj_name}:ground_return",
              (x, y_bottom), (x, y_ground_terminal))

    draw_wire(ax, x, y_node, x, y_split)
    draw_wire(ax, left, y_split, right, y_split)
    draw_vertical_josephson_junction(ax, left, y_split, y_bottom,
                                     size=13.0, lw=2.2)
    draw_resistor(ax, right, y_split, right, y_bottom,
                  color=BLACK, lw=2.0, width=7.0)
    draw_wire(ax, left, y_bottom, right, y_bottom)
    draw_wire(ax, x, y_bottom, x, y_ground_terminal)
    draw_ground(ax, x, y_ground_terminal - 20.0, color=BLACK, lw=2.0)

    label(ax, left - 12, 230, jj_label, size=17, ha="right", weight="bold")
    if annotated:
        label(ax, left - 12, 204, jj_ic, size=13, color=GRAY, ha="right")
    label(ax, right + 12, 230, r_label, size=16, color=GRAY, ha="left")
    if annotated:
        label(ax, right + 12, 205, r_value, size=13, color=GRAY, ha="left")


def draw_scene(ax, *, annotated: bool,
               geometry: GeometryLedger | None = None) -> None:
    ax.set_xlim(0, 1600)
    ax.set_ylim(20, 630)
    ax.axis("off")
    ax.set_facecolor("white")

    if annotated:
        label(ax, 58, 613, "Scaled QB / Q0 standalone", size=27,
              ha="left", weight="bold")
        label(ax, 58, 585, r"publication schematic · $I_{IN}=68.4\,\mu\mathrm{A}$",
              size=16, ha="left", color=GRAY)

    y = Y_MAIN
    # Main signal path: In -> Lin -> Js -> L1 -> L2 -> L0 -> Out.
    if geometry is not None:
        geometry.add_port("In", (X_IN_TERMINAL, y), (55.0, y))
        _wire(geometry, "port:In", (55.0, y), (X_IN_TERMINAL, y))
    draw_port(ax, 55, y, "In", side="left")

    _component(geometry, "Lin", "inductor", (83.0, y), (238.0, y))
    draw_inductor(ax, 83, y, 238, y)
    label(ax, 160, y + 50, r"$L_{\mathrm{in}}$", size=20, weight="bold")

    _wire(geometry, "Lin_to_BJs", (238.0, y), (276.0, y))
    draw_wire(ax, 238, y, 276, y)
    _component(geometry, "BJs", "josephson_junction",
               (276.0, y), (312.0, y), center=(294.0, y))
    draw_josephson_junction(ax, 294, y, size=15, terminal_span=18)
    label(ax, 294, y + 50, r"$J_S$", size=20, weight="bold")

    _wire(geometry, "BJs_to_node2", (312.0, y), (365.0, y))
    draw_wire(ax, 312, y, 365, y)
    if geometry is not None:
        geometry.add_anchor("node2", (365.0, y))
    draw_node(ax, 365, y)

    _component(geometry, "L1", "inductor", (365.0, y), (505.0, y))
    draw_inductor(ax, 365, y, 505, y)
    label(ax, 435, y + 50, r"$L_1$", size=20, weight="bold")

    _wire(geometry, "L1_to_node3", (505.0, y), (548.0, y))
    draw_wire(ax, 505, y, 548, y)
    if geometry is not None:
        geometry.add_anchor("node3", (548.0, y))
    draw_node(ax, 548, y)

    _component(geometry, "L2", "inductor", (548.0, y), (688.0, y))
    draw_inductor(ax, 548, y, 688, y)
    label(ax, 618, y + 50, r"$L_2$", size=20, weight="bold")

    _wire(geometry, "L2_to_node4", (688.0, y), (728.0, y))
    draw_wire(ax, 688, y, 728, y)
    if geometry is not None:
        geometry.add_anchor("node4", (728.0, y))
    draw_node(ax, 728, y)

    _component(geometry, "L0", "inductor", (728.0, y), (868.0, y))
    draw_inductor(ax, 728, y, 868, y)
    label(ax, 798, y + 50, r"$L_0$", size=20, weight="bold")

    _wire(geometry, "L0_to_OUT", (868.0, y), (X_LOAD_NODE, y))
    if geometry is not None:
        geometry.add_anchor("OUT", (X_LOAD_NODE, y))
        geometry.add_port("Out", (X_LOAD_NODE, y), (1002.0, y))
        _wire(geometry, "port:Out", (X_LOAD_NODE, y), (1002.0, y))
    draw_wire(ax, 868, y, X_LOAD_NODE, y)
    draw_port(ax, X_LOAD_NODE, y, "Out", side="right")

    # Bias branch from the actual node between L1 and L2.
    _wire(geometry, "node3_to_RB", (548.0, y), (548.0, 427.0))
    _component(geometry, "RB", "resistor", (548.0, 427.0), (548.0, 505.0))
    draw_wire(ax, 548, y, 548, 427)
    draw_resistor(ax, 548, 427, 548, 505, width=8.0)
    label(ax, 580, 466, r"$R_B$", size=20, ha="left", weight="bold")
    if annotated:
        label(ax, 580, 442, r"$6\,\Omega$", size=14, ha="left", color=GRAY)
    _wire(geometry, "RB_to_bias_arrow", (548.0, 505.0), (548.0, 545.0))
    if geometry is not None:
        geometry.add_current_arrow("I_Bias", (548.0, 545.0), (548.0, 602.0))
    draw_wire(ax, 548, 505, 548, 545)
    bias_label = (r"$I_{\mathrm{Bias}}=35\,\mu\mathrm{A}$"
                  if annotated else r"$I_{\mathrm{Bias}}$")
    draw_current_arrow(ax, 548, 545, 602, label=bias_label, label_dx=72)

    # Real local damping branches present in bq_cell.cir.
    draw_parallel_ground_branch(
        ax, 365, y, jj_name="BJL1", jj_label=r"$J_{L1}$", jj_ic=r"$I_c\approx36\,\mu\mathrm{A}$",
        r_name="RJ1", r_label=r"$R_{J1}$", r_value=r"$33\,\Omega$",
        annotated=annotated, geometry=geometry,
    )
    draw_parallel_ground_branch(
        ax, 728, y, jj_name="BJL2", jj_label=r"$J_{L2}$", jj_ic=r"$I_c\approx54\,\mu\mathrm{A}$",
        r_name="RJ2", r_label=r"$R_{J2}$", r_value=r"$22\,\Omega$",
        annotated=annotated, geometry=geometry,
    )

    # Top-level fixture load is shown softly so the load boundary is explicit.
    _wire(geometry, "OUT_to_RLOAD", (X_LOAD_NODE, y), (X_LOAD_NODE, 263.0),
          color="light-gray")
    _component(geometry, "R_LOAD", "resistor",
               (X_LOAD_NODE, 263.0), (X_LOAD_NODE, 198.0), scope="top-level")
    _wire(geometry, "RLOAD_to_ground", (X_LOAD_NODE, 198.0),
          (X_LOAD_NODE, 150.0), color="light-gray")
    if geometry is not None:
        geometry.add_ground("R_LOAD:ground", (X_LOAD_NODE, 150.0))
    draw_wire(ax, X_LOAD_NODE, y, X_LOAD_NODE, 263,
              color=LIGHT_GRAY, lw=1.8, linestyle=(0, (5, 3)))
    draw_resistor(ax, X_LOAD_NODE, 263, X_LOAD_NODE, 198,
                  color=LIGHT_GRAY, lw=1.8, width=7.0)
    draw_wire(ax, X_LOAD_NODE, 198, X_LOAD_NODE, 150,
              color=LIGHT_GRAY, lw=1.8, linestyle=(0, (5, 3)))
    draw_ground(ax, X_LOAD_NODE, 130, color=LIGHT_GRAY, lw=1.8)
    label(ax, X_LOAD_NODE + 20, 238, r"$R_{\mathrm{LOAD}}$", size=16,
          color=GRAY, ha="left")
    if annotated:
        label(ax, X_LOAD_NODE + 20, 216, r"$10\,\Omega$ fixture", size=13,
              color=GRAY, ha="left")

    if annotated:
        ax.plot([58, 1542], [96, 96], color="#d5d8dc", lw=1.0)
        label(ax, 58, 76,
              r"$Q0$: $L_{\mathrm{in}}=0.8\,\mathrm{pH}$ · "
              r"$L_1=L_2=3.91\,\mathrm{pH}$ · $L_0=1.323\,\mathrm{pH}$ · "
              r"$R_B=6\,\Omega$ · $R_{J1}=33\,\Omega$ · $R_{J2}=22\,\Omega$",
              size=14, color=BLACK, ha="left")
        label(ax, 58, 52,
              r"$I_c$: $J_S=50\,\mu\mathrm{A}$ · "
              r"$J_{L1}=36\,\mu\mathrm{A}$ · $J_{L2}=54\,\mu\mathrm{A}$; "
              "black = QB core, gray = retained top-level load boundary.",
              size=13, color=GRAY, ha="left")


def save_figure(output_dir: Path, stem: str, *, annotated: bool) -> None:
    fig = plt.figure(figsize=(16, 5.8), dpi=160, facecolor="white")
    ax = fig.add_axes([0, 0, 1, 1])
    draw_scene(ax, annotated=annotated)
    metadata = {
        "Title": ("Scaled QB Q0 annotated experiment schematic" if annotated
                  else "Scaled QB Q0 publication schematic"),
        "Author": "JoSIM schematic renderer",
        "Subject": "Netlist-validated semantic schematic; not a scientific verdict",
    }
    svg_path = output_dir / f"{stem}.svg"
    fig.savefig(svg_path, format="svg", metadata={"Title": metadata["Title"]})
    svg_text = svg_path.read_text(encoding="utf-8")
    svg_path.write_text(
        "\n".join(line.rstrip() for line in svg_text.splitlines()) + "\n",
        encoding="utf-8",
    )
    fig.savefig(output_dir / f"{stem}.png", format="png", dpi=180,
                metadata=metadata)
    fig.savefig(output_dir / f"{stem}.pdf", format="pdf", metadata=metadata)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    matplotlib.rcParams["svg.hashsalt"] = "josim-qb-q0-schematic-v2"

    # Render the clean figure while recording the exact coordinate ledger.
    geometry = GeometryLedger()
    fig = plt.figure(figsize=(16, 5.8), dpi=160, facecolor="white")
    ax = fig.add_axes([0, 0, 1, 1])
    draw_scene(ax, annotated=False, geometry=geometry)
    clean_metadata = {
        "Title": "Scaled QB Q0 publication schematic",
        "Author": "JoSIM schematic renderer",
        "Subject": "Netlist-validated semantic schematic; not a scientific verdict",
    }
    clean_svg = args.output_dir / "schematic.svg"
    fig.savefig(clean_svg, format="svg", metadata={"Title": clean_metadata["Title"]})
    clean_svg.write_text(
        "\n".join(line.rstrip() for line in clean_svg.read_text(encoding="utf-8").splitlines()) + "\n",
        encoding="utf-8",
    )
    fig.savefig(args.output_dir / "schematic.png", format="png", dpi=180,
                metadata=clean_metadata)
    fig.savefig(args.output_dir / "schematic.pdf", format="pdf", metadata=clean_metadata)
    plt.close(fig)

    geometry.write(args.output_dir / "geometric-connectivity.json")
    save_figure(args.output_dir, "schematic-annotated", annotated=True)
    print(f"wrote {args.output_dir / 'schematic.svg'}")
    print(f"wrote {args.output_dir / 'schematic-annotated.svg'}")
    print(f"wrote {args.output_dir / 'geometric-connectivity.json'}")


if __name__ == "__main__":
    main()
