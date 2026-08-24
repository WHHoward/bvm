#!/usr/bin/env python3
"""Render the accepted scaled Q0 QB fixture as a publication schematic.

This is deliberately a hand-authored semantic layout, not a graph layout.
The selected deck and the semantic manifest are validated separately by
``validate_schematic.py`` before this output is accepted.
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
from symbols import (  # noqa: E402
    BLACK,
    GRAY,
    LIGHT_GRAY,
    draw_current_arrow,
    draw_ground,
    draw_inductor,
    draw_josephson_junction,
    draw_node,
    draw_port,
    draw_resistor,
    draw_wire,
    label,
)


def draw_parallel_ground_branch(ax, x: float, y_node: float, *, jj_name: str,
                                jj_ic: str, r_name: str, r_value: str) -> None:
    """Draw a JJ and its real parallel damping resistor to ground."""
    y_split = y_node - 42
    y_join = 145
    left = x - 26
    right = x + 26
    draw_wire(ax, x, y_node, x, y_split)
    draw_wire(ax, left, y_split, right, y_split)
    draw_wire(ax, left, y_split, left, y_join + 55)
    draw_wire(ax, right, y_split, right, y_join + 55)
    draw_josephson_junction(ax, left, y_join + 30, size=13, lw=2.2)
    draw_resistor(ax, right, y_join + 55, right, y_join + 5,
                  color=GRAY, lw=2.0, width=7.0)
    draw_wire(ax, left, y_join + 5, right, y_join + 5)
    draw_ground(ax, x, y_join - 15)
    label(ax, left - 12, y_join + 82, jj_name, size=17, ha="right")
    label(ax, left - 12, y_join + 61, jj_ic, size=13, color=GRAY, ha="right")
    label(ax, right + 12, y_join + 78, r_name, size=16, color=GRAY, ha="left")
    label(ax, right + 12, y_join + 58, r_value, size=13, color=GRAY, ha="left")


def draw_scene(ax) -> None:
    ax.set_xlim(0, 1600)
    ax.set_ylim(0, 650)
    ax.axis("off")
    ax.set_facecolor("white")

    label(ax, 58, 615, "Scaled QB / Q0 standalone", size=27, ha="left", weight="bold")
    label(ax, 58, 585, "publication schematic · input = 68.4 µA",
          size=16, ha="left", color=GRAY)

    y = 325
    # Main signal path: In -> Lin -> Js -> L1 -> L2 -> L0 -> Out.
    draw_port(ax, 55, y, "In", side="left")
    draw_wire(ax, 83, y, 118, y)
    draw_inductor(ax, 118, y, 238, y)
    label(ax, 178, y + 50, "Lin", size=20, weight="bold")
    draw_wire(ax, 238, y, 276, y)
    draw_josephson_junction(ax, 294, y, size=15)
    label(ax, 294, y + 50, "Js", size=20, weight="bold")
    draw_wire(ax, 312, y, 365, y)
    draw_node(ax, 365, y)
    draw_inductor(ax, 385, y, 505, y)
    label(ax, 445, y + 50, "L1", size=20, weight="bold")
    draw_wire(ax, 505, y, 548, y)
    draw_node(ax, 548, y)
    draw_inductor(ax, 568, y, 688, y)
    label(ax, 628, y + 50, "L2", size=20, weight="bold")
    draw_wire(ax, 688, y, 728, y)
    draw_node(ax, 728, y)
    draw_inductor(ax, 748, y, 868, y)
    label(ax, 808, y + 50, "L0", size=20, weight="bold")
    load_x = 1030
    draw_wire(ax, 868, y, load_x, y)
    draw_port(ax, load_x, y, "Out", side="right")

    # Bias branch from the actual node between L1 and L2.
    draw_wire(ax, 548, y, 548, 427)
    draw_resistor(ax, 548, 427, 548, 505, width=8.0)
    label(ax, 580, 466, "RB", size=20, ha="left", weight="bold")
    label(ax, 580, 442, "6 Ω", size=14, ha="left", color=GRAY)
    draw_wire(ax, 548, 505, 548, 545)
    draw_current_arrow(ax, 548, 545, 602, label="I_Bias = 35 µA", label_dx=72)

    # Real local damping branches present in bq_cell.cir.
    draw_parallel_ground_branch(ax, 365, y, jj_name="JL1", jj_ic="Ic≈36 µA",
                                r_name="RJ1", r_value="33 Ω")
    draw_parallel_ground_branch(ax, 728, y, jj_name="JL2", jj_ic="Ic≈54 µA",
                                r_name="RJ2", r_value="22 Ω")

    # Top-level fixture load is shown softly so the load boundary is explicit.
    draw_wire(ax, load_x, y, load_x, 263, color=LIGHT_GRAY, lw=1.8,
              linestyle=(0, (5, 3)))
    draw_resistor(ax, load_x, 263, load_x, 198, color=LIGHT_GRAY, lw=1.8,
                  width=7.0)
    draw_ground(ax, load_x, 150, color=LIGHT_GRAY, lw=1.8)
    label(ax, load_x + 20, 238, "R_LOAD", size=16, color=GRAY, ha="left")
    label(ax, load_x + 20, 216, "10 Ω fixture", size=13, color=GRAY, ha="left")

    # Compact figure note, matching the reference-figure convention.
    ax.plot([58, 1542], [86, 86], color="#d5d8dc", lw=1.0)
    label(ax, 58, 60,
          "Q0 scaled: Lin=0.8 pH · L1=L2=3.91 pH · L0=1.323 pH · "
          "Js Ic≈50 µA · JL1 Ic≈36 µA · JL2 Ic≈54 µA · RB=6 Ω",
          size=15, color=BLACK, ha="left")
    label(ax, 58, 32,
          "Black = QB core; gray dashed branch = retained top-level 10 Ω output-load boundary.",
          size=13, color=GRAY, ha="left")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    matplotlib.rcParams["svg.hashsalt"] = "josim-qb-q0-schematic-v1"
    fig = plt.figure(figsize=(16, 6.5), dpi=160, facecolor="white")
    ax = fig.add_axes([0, 0, 1, 1])
    draw_scene(ax)
    metadata = {
        "Title": "Scaled QB Q0 standalone publication schematic",
        "Author": "JoSIM schematic renderer",
        "Subject": "Netlist-validated semantic schematic; not a scientific verdict",
    }
    svg_path = args.output_dir / "schematic.svg"
    fig.savefig(svg_path, format="svg", metadata={"Title": metadata["Title"]})
    # Matplotlib intentionally aligns SVG path data across multiple lines;
    # strip only trailing whitespace so repository diff checks remain clean.
    svg_text = svg_path.read_text(encoding="utf-8")
    svg_path.write_text(
        "\n".join(line.rstrip() for line in svg_text.splitlines()) + "\n",
        encoding="utf-8",
    )
    fig.savefig(args.output_dir / "schematic.png", format="png", dpi=180,
                metadata=metadata)
    fig.savefig(args.output_dir / "schematic.pdf", format="pdf", metadata=metadata)
    plt.close(fig)
    print(f"wrote {args.output_dir / 'schematic.svg'}")
    print(f"wrote {args.output_dir / 'schematic.png'}")
    print(f"wrote {args.output_dir / 'schematic.pdf'}")


if __name__ == "__main__":
    main()
