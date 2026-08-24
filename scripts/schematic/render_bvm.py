#!/usr/bin/env python3
"""Render the canonical BVM cell as a semantic publication schematic.

The actual connectivity comes from ``circuits/bvm/bvm_cell.cir`` (the selected
Exploration copy is hash-identical).  The layout is intentionally authored in
the visual grammar of the paper figures: external buses are separated from a
light-gray cell boundary, and the shared storage/read structures are grouped
into restrained S-Loop and R-Loop regions.
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
    draw_vertical_josephson_junction,
    draw_node,
    draw_port,
    draw_resistor,
    draw_wire,
    label,
)


Y_N2 = 650.0
Y_N5 = 360.0
N1 = (480.0, Y_N2)
N2 = (840.0, Y_N2)
N3 = (1160.0, Y_N2)
N5 = (840.0, Y_N5)
N6 = (1160.0, Y_N5)
N8 = (1580.0, Y_N5)
SL_PORT = (1700.0, Y_N5)


def _wire(geometry: GeometryLedger | None, name: str,
          start: tuple[float, float], end: tuple[float, float], *,
          color: str = "black") -> None:
    if geometry is not None:
        geometry.add_wire(name, start, end, color=color)


def _component(geometry: GeometryLedger | None, name: str, kind: str,
               start: tuple[float, float], end: tuple[float, float], *,
               center: tuple[float, float] | None = None,
               scope: str = "BVM") -> None:
    if geometry is not None:
        geometry.add_component(name, kind, start, end, scope=scope,
                               symbol_center=center)


def _anchor(geometry: GeometryLedger | None, name: str,
            point: tuple[float, float]) -> None:
    if geometry is not None:
        geometry.add_anchor(name, point)


def _fixed(geometry: GeometryLedger | None, name: str,
           point: tuple[float, float], *, kind: str) -> None:
    if geometry is not None:
        geometry.add_fixed(name, point, kind=kind)


def _label_component(ax, x: float, y: float, name: str, value: str | None,
                     *, annotated: bool, ha: str = "center", color: str = BLACK,
                     size: float = 15.0) -> None:
    label(ax, x, y, name, size=size, ha=ha, color=color)
    if annotated and value:
        label(ax, x, y - 23, value, size=11.0, ha=ha, color=GRAY)


def _draw_bus(ax, geometry: GeometryLedger | None, *, name: str, label_text: str,
              y: float, branch_x: float, color: str, port_x: float = 80.0) -> None:
    """Draw a labeled left port and its horizontal external bus."""
    terminal_x = port_x + 28.0
    if geometry is not None:
        geometry.add_port(name, (terminal_x, y), (port_x, y))
        _wire(geometry, f"{name}:port", (port_x, y), (terminal_x, y), color=color)
        _wire(geometry, f"{name}:bus", (terminal_x, y), (branch_x, y), color=color)
        _fixed(geometry, f"{name}:branch", (branch_x, y), kind="bus_terminal")
    draw_port(ax, port_x, y, label_text, side="left", color=color)
    draw_wire(ax, terminal_x, y, branch_x, y, color=color, lw=2.5)


def _draw_parallel_jj_resistor(ax, geometry: GeometryLedger | None, *,
                               node_name: str, x: float, y_top: float,
                               y_bottom: float, jj_name: str, jj_label: str,
                               jj_value: str, r_name: str, r_label: str,
                               r_value: str, annotated: bool) -> None:
    """Draw the actual B_JM1 || R_JM1 branch before the shared L_M1."""
    left = x - 28.0
    right = x + 28.0
    center_y = (y_top + y_bottom) / 2.0
    _anchor(geometry, node_name, (x, y_top))
    _anchor(geometry, f"{node_name}:lower", (x, y_bottom))
    _component(geometry, jj_name, "josephson_junction",
               (left, y_top), (left, y_bottom), center=(left, center_y))
    _component(geometry, r_name, "resistor", (right, y_top), (right, y_bottom))
    _wire(geometry, f"{node_name}:top-left", (x, y_top), (left, y_top))
    _wire(geometry, f"{node_name}:top-right", (x, y_top), (right, y_top))
    _wire(geometry, f"{node_name}:bottom-left", (left, y_bottom), (x, y_bottom))
    _wire(geometry, f"{node_name}:bottom-right", (x, y_bottom), (right, y_bottom))

    draw_wire(ax, left, y_top, x, y_top)
    draw_wire(ax, x, y_top, right, y_top)
    draw_vertical_josephson_junction(ax, left, y_top, y_bottom,
                                     size=13.0, lw=2.2)
    draw_resistor(ax, right, y_top, right, y_bottom, width=7.0, lw=2.0)
    draw_wire(ax, left, y_bottom, x, y_bottom)
    draw_wire(ax, x, y_bottom, right, y_bottom)

    _label_component(ax, left - 13, center_y + 15, jj_label, jj_value,
                     annotated=annotated, ha="right", size=14.5)
    _label_component(ax, right + 13, center_y + 15, r_label, r_value,
                     annotated=annotated, ha="left", color=GRAY, size=13.5)


def draw_scene(ax, *, annotated: bool,
               geometry: GeometryLedger | None = None) -> None:
    ax.set_xlim(0, 1800)
    ax.set_ylim(25, 1140)
    ax.axis("off")
    ax.set_facecolor("white")

    # Functional enclosure and restrained regions are behind all electrical
    # symbols; they are not netlist components.
    draw_block(ax, 190, 135, 1480, 800, edgecolor="#b8bec6",
               facecolor="#f7f8fa", alpha=1.0, linestyle="-", lw=1.3)
    draw_function_region(ax, 235, 190, 730, 610, "S-Loop", color=BLUE, alpha=0.09)
    draw_function_region(ax, 760, 250, 650, 550, "R-Loop", color=RED, alpha=0.08)

    if annotated:
        label(ax, 58, 1110, "Canonical BVM / internal readout", size=27,
              ha="left", weight="bold")
        label(ax, 58, 1080,
              r"representative logical-1 + canonical READ deck · "
              r"$+100\,\mu\mathrm{A}$ source PWL",
              size=15, ha="left", color=GRAY)

    # External control buses. Their names are the BVM subcircuit ports; the
    # selected top-level deck uses WL1/BL1/SE1/SL1 aliases.
    _draw_bus(ax, geometry, name="WL", label_text="WL", y=1015,
              branch_x=300, color=BLUE)
    _draw_bus(ax, geometry, name="BL", label_text="BL", y=1060,
              branch_x=420, color=RED)
    _draw_bus(ax, geometry, name="SE", label_text="SE", y=965,
              branch_x=1160, color=BLUE, port_x=680)

    # WL and BL input paths merge at N1: R_* followed by L_P*.
    _component(geometry, "R_WL", "resistor", (300, 1015), (300, 900))
    _component(geometry, "L_PWL", "inductor", (300, 900), (300, Y_N2))
    _wire(geometry, "R_WL_to_L_PWL", (300, 900), (300, 900))
    _wire(geometry, "L_PWL_to_N1", (300, Y_N2), (480, Y_N2))
    draw_resistor(ax, 300, 1015, 300, 900, width=7.0)
    draw_inductor(ax, 300, 900, 300, Y_N2)
    draw_wire(ax, 300, Y_N2, 480, Y_N2)
    _label_component(ax, 265, 952, r"$R_{WL}$", r"$20\,\Omega$",
                     annotated=annotated, ha="right")
    _label_component(ax, 265, 755, r"$L_{PWL}$", r"$0.5\,\mathrm{pH}$",
                     annotated=annotated, ha="right")

    _component(geometry, "R_BL", "resistor", (420, 1060), (420, 930))
    _component(geometry, "L_PBL", "inductor", (420, 930), (420, Y_N2))
    _wire(geometry, "L_PBL_to_N1", (420, Y_N2), (480, Y_N2))
    draw_resistor(ax, 420, 1060, 420, 930, width=7.0)
    draw_inductor(ax, 420, 930, 420, Y_N2)
    draw_wire(ax, 420, Y_N2, 480, Y_N2)
    _label_component(ax, 455, 990, r"$R_{BL}$", r"$20\,\Omega$",
                     annotated=annotated, ha="left")
    _label_component(ax, 455, 775, r"$L_{PBL}$", r"$0.5\,\mathrm{pH}$",
                     annotated=annotated, ha="left")

    # Main S-loop branch: N1 -> (JM1 || RJM1) -> LM1 -> GND.
    _draw_parallel_jj_resistor(
        ax, geometry, node_name="N1", x=480, y_top=Y_N2, y_bottom=530,
        jj_name="B_JM1", jj_label=r"$J_{M1}$", jj_value=r"$A=1.2$",
        r_name="R_JM1", r_label=r"$R_{JM1}$", r_value=r"$6\,\Omega$",
        annotated=annotated,
    )
    _component(geometry, "L_M1", "inductor", (480, 530), (480, 300))
    _wire(geometry, "N1_branch_to_L_M1", (480, 530), (480, 530))
    _wire(geometry, "L_M1_to_ground", (480, 300), (480, 270))
    _fixed(geometry, "L_M1:ground", (480, 270), kind="ground_terminal")
    draw_inductor(ax, 480, 530, 480, 300)
    draw_wire(ax, 480, 300, 480, 270)
    draw_ground(ax, 480, 250)
    _label_component(ax, 510, 410, r"$L_{M1}$", r"$12.5\,\mathrm{pH}$",
                     annotated=annotated, ha="left")

    # N1 -> LM2 -> JM2 -> N2.
    _wire(geometry, "N1_to_L_M2", (480, Y_N2), (525, Y_N2))
    _component(geometry, "L_M2", "inductor", (525, Y_N2), (665, Y_N2))
    _wire(geometry, "L_M2_to_B_JM2", (665, Y_N2), (700, Y_N2))
    _component(geometry, "B_JM2", "josephson_junction",
               (700, Y_N2), (740, Y_N2), center=(720, Y_N2))
    _wire(geometry, "B_JM2_to_N2", (740, Y_N2), (840, Y_N2))
    draw_wire(ax, 480, Y_N2, 525, Y_N2)
    draw_inductor(ax, 525, Y_N2, 665, Y_N2)
    draw_wire(ax, 665, Y_N2, 700, Y_N2)
    draw_josephson_junction(ax, 720, Y_N2, size=14, terminal_span=20)
    draw_wire(ax, 740, Y_N2, 840, Y_N2)
    _label_component(ax, 595, 700, r"$L_{M2}$", r"$24.5\,\mathrm{pH}$",
                     annotated=annotated)
    _label_component(ax, 720, 700, r"$J_{M2}$", r"$A=1.4$",
                     annotated=annotated)

    # Shared N2 -> LM3 -> N5 path and the S-loop closure LPM -> GND.
    _anchor(geometry, "N2", N2)
    _anchor(geometry, "N5", N5)
    _component(geometry, "L_M3", "inductor", N2, N5)
    _component(geometry, "L_PM", "inductor", (840, Y_N5), (840, 250))
    _wire(geometry, "L_PM_to_ground", (840, 250), (840, 220))
    _fixed(geometry, "L_PM:ground", (840, 220), kind="ground_terminal")
    draw_inductor(ax, 840, Y_N2, 840, Y_N5)
    draw_inductor(ax, 840, Y_N5, 840, 250)
    draw_wire(ax, 840, 250, 840, 220)
    draw_ground(ax, 840, 200)
    _label_component(ax, 805, 505, r"$L_{M3}$", r"$8.5\,\mathrm{pH}$",
                     annotated=annotated, ha="right")
    _label_component(ax, 875, 285, r"$L_{PM}$", r"$0.5\,\mathrm{pH}$",
                     annotated=annotated, ha="left")

    # R-loop upper branch: N2 -> LS1 -> JS1 -> N3.
    _wire(geometry, "N2_to_L_S1", (840, Y_N2), (880, Y_N2))
    _component(geometry, "L_S1", "inductor", (880, Y_N2), (1000, Y_N2))
    _wire(geometry, "L_S1_to_B_JS1", (1000, Y_N2), (1030, Y_N2))
    _component(geometry, "B_JS1", "josephson_junction",
               (1030, Y_N2), (1070, Y_N2), center=(1050, Y_N2))
    _wire(geometry, "B_JS1_to_N3", (1070, Y_N2), (1160, Y_N2))
    draw_wire(ax, 840, Y_N2, 880, Y_N2)
    draw_inductor(ax, 880, Y_N2, 1000, Y_N2)
    draw_wire(ax, 1000, Y_N2, 1030, Y_N2)
    draw_josephson_junction(ax, 1050, Y_N2, size=14, terminal_span=20)
    draw_wire(ax, 1070, Y_N2, 1160, Y_N2)
    _label_component(ax, 940, 700, r"$L_{S1}$", r"$0.5\,\mathrm{pH}$",
                     annotated=annotated)
    _label_component(ax, 1050, 700, r"$J_{S1}$", r"$A=0.74$",
                     annotated=annotated)

    # SE input path enters N3 via RSE and LPSE.
    _component(geometry, "R_SE", "resistor", (1160, 965), (1160, 850))
    _component(geometry, "L_PSE", "inductor", (1160, 850), (1160, Y_N2))
    _wire(geometry, "R_SE_to_L_PSE", (1160, 850), (1160, 850))
    draw_resistor(ax, 1160, 965, 1160, 850, width=7.0)
    draw_inductor(ax, 1160, 850, 1160, Y_N2)
    _label_component(ax, 1195, 915, r"$R_{SE}$", r"$20\,\Omega$",
                     annotated=annotated, ha="left")
    _label_component(ax, 1195, 775, r"$L_{PSE}$", r"$0.5\,\mathrm{pH}$",
                     annotated=annotated, ha="left")

    # R-loop lower branch: N5 -> LS2 -> JS2 -> N6.
    _wire(geometry, "N5_to_L_S2", (840, Y_N5), (880, Y_N5))
    _component(geometry, "L_S2", "inductor", (880, Y_N5), (1000, Y_N5))
    _wire(geometry, "L_S2_to_B_JS2", (1000, Y_N5), (1030, Y_N5))
    _component(geometry, "B_JS2", "josephson_junction",
               (1030, Y_N5), (1070, Y_N5), center=(1050, Y_N5))
    _wire(geometry, "B_JS2_to_N6", (1070, Y_N5), (1160, Y_N5))
    draw_wire(ax, 840, Y_N5, 880, Y_N5)
    draw_inductor(ax, 880, Y_N5, 1000, Y_N5)
    draw_wire(ax, 1000, Y_N5, 1030, Y_N5)
    draw_josephson_junction(ax, 1050, Y_N5, size=14, terminal_span=20)
    draw_wire(ax, 1070, Y_N5, 1160, Y_N5)
    _label_component(ax, 940, 410, r"$L_{S2}$", r"$0.5\,\mathrm{pH}$",
                     annotated=annotated)
    _label_component(ax, 1050, 410, r"$J_{S2}$", r"$A=0.74$",
                     annotated=annotated)

    # R_S || L_S3 are the actual N3-to-N6 bridge branches.
    _anchor(geometry, "N3", N3)
    _anchor(geometry, "N6", N6)
    _component(geometry, "R_S", "resistor", (1080, Y_N2), (1080, Y_N5))
    _component(geometry, "L_S3", "inductor", (1230, Y_N2), (1230, Y_N5))
    for suffix, start, end in (
        ("left", (1080, Y_N2), N3),
        ("right", N3, (1230, Y_N2)),
        ("bottom-left", (1080, Y_N5), N6),
        ("bottom-right", N6, (1230, Y_N5)),
    ):
        _wire(geometry, f"N3_N6_bridge:{suffix}", start, end)
    draw_wire(ax, 1080, Y_N2, 1160, Y_N2)
    draw_wire(ax, 1160, Y_N2, 1230, Y_N2)
    draw_resistor(ax, 1080, Y_N2, 1080, Y_N5, width=7.0)
    draw_inductor(ax, 1230, Y_N2, 1230, Y_N5)
    draw_wire(ax, 1080, Y_N5, 1160, Y_N5)
    draw_wire(ax, 1160, Y_N5, 1230, Y_N5)
    _label_component(ax, 1050, 505, r"$R_S$", r"$3\,\Omega$",
                     annotated=annotated, ha="right", color=RED)
    _label_component(ax, 1270, 505, r"$L_{S3}$", r"$0.5\,\mathrm{pH}$",
                     annotated=annotated, ha="left", color=RED)

    # Output chain: N6 -> LPSL -> RSL -> N8 -> LSL -> SL.
    _wire(geometry, "N6_to_L_PSL", N6, (1180, Y_N5))
    _component(geometry, "L_PSL", "inductor", (1180, Y_N5), (1280, Y_N5))
    _wire(geometry, "L_PSL_to_R_SL", (1280, Y_N5), (1320, Y_N5))
    _component(geometry, "R_SL", "resistor", (1320, Y_N5), (1430, Y_N5))
    _wire(geometry, "R_SL_to_L_SL", (1430, Y_N5), (1460, Y_N5))
    _component(geometry, "L_SL", "inductor", (1460, Y_N5), N8)
    _wire(geometry, "L_SL_to_SL", N8, SL_PORT, color="red")
    _anchor(geometry, "N8", N8)
    if geometry is not None:
        geometry.add_port("SL", SL_PORT, (1672, Y_N5))
        _wire(geometry, "SL:port", SL_PORT, (1672, Y_N5), color="red")
    draw_wire(ax, 1160, Y_N5, 1180, Y_N5)
    draw_inductor(ax, 1180, Y_N5, 1280, Y_N5)
    draw_wire(ax, 1280, Y_N5, 1320, Y_N5)
    draw_resistor(ax, 1320, Y_N5, 1430, Y_N5, width=7.0)
    draw_wire(ax, 1430, Y_N5, 1460, Y_N5)
    draw_inductor(ax, 1460, Y_N5, 1580, Y_N5)
    draw_wire(ax, 1580, Y_N5, 1700, Y_N5, color=RED)
    draw_port(ax, 1700, Y_N5, "SL", side="right", color=RED)
    label(ax, 1660, 300, "Data Out", size=15, color=RED, ha="right")
    _label_component(ax, 1230, 410, r"$L_{PSL}$", r"$0.5\,\mathrm{pH}$",
                     annotated=annotated)
    _label_component(ax, 1375, 410, r"$R_{SL}$", r"$12\,\Omega$",
                     annotated=annotated)
    _label_component(ax, 1520, 410, r"$L_{SL}$", r"$0.4\,\mathrm{pH}$",
                     annotated=annotated)

    # Representative top-level SL load is an external gray fixture, not part
    # of the BVM subcircuit.
    _component(geometry, "R_LD", "resistor", (1700, 360), (1700, 220),
               scope="top-level")
    _wire(geometry, "SL_to_R_LD", (1700, 360), (1700, 360), color="light-gray")
    _wire(geometry, "R_LD_to_ground", (1700, 220), (1700, 170), color="light-gray")
    _fixed(geometry, "R_LD:ground", (1700, 170), kind="ground_terminal")
    draw_wire(ax, 1700, 360, 1700, 220, color=LIGHT_GRAY, lw=1.8,
              linestyle=(0, (5, 3)))
    draw_resistor(ax, 1700, 220, 1700, 170, color=LIGHT_GRAY, lw=1.8, width=7.0)
    draw_ground(ax, 1700, 150, color=LIGHT_GRAY, lw=1.8)
    if annotated:
        label(ax, 1730, 260, r"$R_{LD}=12\,\Omega$", size=13,
              color=GRAY, ha="left")
    else:
        label(ax, 1730, 260, r"$R_{LD}$", size=14, color=GRAY, ha="left")

    # Junction dots at the principal shared nodes only; internal node names
    # remain hidden to preserve the paper-figure information density.
    for x, y in (N1, N2, N3, N5, N6, N8):
        draw_node(ax, x, y)

    if annotated:
        ax.plot([58, 1742], [92, 92], color="#d5d8dc", lw=1.0)
        label(ax, 58, 72,
              r"BVM v6 · $R_{WL}=R_{BL}=R_{SE}=20\,\Omega$ · "
              r"$L_{PWL}=L_{PBL}=L_{PSE}=L_{PSL}=0.5\,\mathrm{pH}$ · "
              r"$R_S=3\,\Omega$ · $R_{SL}=12\,\Omega$ · $L_{SL}=0.4\,\mathrm{pH}$",
              size=12.5, ha="left", color=BLACK)
        label(ax, 58, 47,
              r"$J_{M1}/J_{M2}/J_{S1}/J_{S2}$ areas $=1.2/1.4/0.74/0.74$; "
              "blue = S-Loop, red = R-Loop, gray = external load boundary.",
              size=12.5, ha="left", color=GRAY)


def save_figure(output_dir: Path, stem: str, *, annotated: bool) -> None:
    fig = plt.figure(figsize=(17.5, 10.5), dpi=150, facecolor="white")
    ax = fig.add_axes([0, 0, 1, 1])
    draw_scene(ax, annotated=annotated)
    title = ("Canonical BVM annotated schematic" if annotated
             else "Canonical BVM publication schematic")
    metadata = {
        "Title": title,
        "Author": "JoSIM schematic renderer",
        "Subject": "Netlist-validated semantic schematic; not a scientific verdict",
    }
    svg = output_dir / f"{stem}.svg"
    fig.savefig(svg, format="svg", metadata={"Title": title})
    svg.write_text("\n".join(line.rstrip() for line in svg.read_text(encoding="utf-8").splitlines()) + "\n",
                   encoding="utf-8")
    fig.savefig(output_dir / f"{stem}.png", format="png", dpi=180, metadata=metadata)
    fig.savefig(output_dir / f"{stem}.pdf", format="pdf", metadata=metadata)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    matplotlib.rcParams["svg.hashsalt"] = "josim-bvm-schematic-v1"

    geometry = GeometryLedger()
    fig = plt.figure(figsize=(17.5, 10.5), dpi=150, facecolor="white")
    ax = fig.add_axes([0, 0, 1, 1])
    draw_scene(ax, annotated=False, geometry=geometry)
    title = "Canonical BVM publication schematic"
    metadata = {
        "Title": title,
        "Author": "JoSIM schematic renderer",
        "Subject": "Netlist-validated semantic schematic; not a scientific verdict",
    }
    svg = args.output_dir / "schematic.svg"
    fig.savefig(svg, format="svg", metadata={"Title": title})
    svg.write_text("\n".join(line.rstrip() for line in svg.read_text(encoding="utf-8").splitlines()) + "\n",
                   encoding="utf-8")
    fig.savefig(args.output_dir / "schematic.png", format="png", dpi=180, metadata=metadata)
    fig.savefig(args.output_dir / "schematic.pdf", format="pdf", metadata=metadata)
    plt.close(fig)

    geometry.write(args.output_dir / "geometric-connectivity.json")
    save_figure(args.output_dir, "schematic-annotated", annotated=True)
    print(f"wrote {args.output_dir / 'schematic.svg'}")
    print(f"wrote {args.output_dir / 'schematic-annotated.svg'}")
    print(f"wrote {args.output_dir / 'geometric-connectivity.json'}")


if __name__ == "__main__":
    main()
