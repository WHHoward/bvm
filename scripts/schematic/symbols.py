"""Small, deterministic electrical-schematic symbol library.

The functions in this module intentionally draw a schematic in caller-supplied
coordinates.  They do not infer layout from a graph and do not create a
connectivity graph.  A semantic layout is validated separately against the
selected JoSIM deck.
"""

from __future__ import annotations

import numpy as np
from matplotlib.axes import Axes
from matplotlib.patches import Circle, FancyArrowPatch, Rectangle


BLACK = "#111111"
GRAY = "#73777d"
LIGHT_GRAY = "#a7adb4"
BLUE = "#174ea6"
RED = "#b3261e"


def draw_wire(ax: Axes, x1: float, y1: float, x2: float, y2: float,
              *, color: str = BLACK, lw: float = 2.2,
              linestyle: str = "-") -> None:
    ax.plot([x1, x2], [y1, y2], color=color, lw=lw,
            linestyle=linestyle, solid_capstyle="round", zorder=2)


def draw_node(ax: Axes, x: float, y: float, *, color: str = BLACK,
              radius: float = 4.5) -> None:
    ax.add_patch(Circle((x, y), radius, facecolor=color, edgecolor=color,
                        lw=0, zorder=8))


def _classic_horizontal_coil(start: float, end: float, center: float,
                             amplitude: float, loops: int) -> tuple[np.ndarray, np.ndarray]:
    """Return a paper-style sequence of semicircular coil loops.

    The old prototype used a sinusoid, which reads as a waveform rather than
    an electrical inductor.  The reference QB figure uses compact semicircular
    loops on one side of the wire; this helper reproduces that vocabulary while
    keeping the two electrical terminals exactly at ``start`` and ``end``.
    """
    direction = 1.0 if end >= start else -1.0
    lo, hi = (start, end) if direction > 0 else (end, start)
    width = (hi - lo) / max(loops, 1)
    xs: list[float] = []
    ys: list[float] = []
    for index in range(max(loops, 1)):
        x0 = lo + index * width
        theta = np.linspace(0.0, np.pi, 32)
        x = x0 + width * theta / np.pi
        y = center + amplitude * np.sin(theta)
        if direction < 0:
            x = x[::-1]
            y = y[::-1]
        if xs:
            # Keep adjacent semicircles joined at their common baseline point.
            xs.extend(x[1:].tolist())
            ys.extend(y[1:].tolist())
        else:
            xs.extend(x.tolist())
            ys.extend(y.tolist())
    return np.asarray(xs), np.asarray(ys)


def _classic_vertical_coil(start: float, end: float, center: float,
                           amplitude: float, loops: int) -> tuple[np.ndarray, np.ndarray]:
    direction = 1.0 if end >= start else -1.0
    lo, hi = (start, end) if direction > 0 else (end, start)
    width = (hi - lo) / max(loops, 1)
    xs: list[float] = []
    ys: list[float] = []
    for index in range(max(loops, 1)):
        y0 = lo + index * width
        theta = np.linspace(0.0, np.pi, 32)
        y = y0 + width * theta / np.pi
        x = center + amplitude * np.sin(theta)
        if direction < 0:
            y = y[::-1]
            x = x[::-1]
        if xs:
            xs.extend(x[1:].tolist())
            ys.extend(y[1:].tolist())
        else:
            xs.extend(x.tolist())
            ys.extend(y.tolist())
    return np.asarray(xs), np.asarray(ys)


def draw_inductor(ax: Axes, x1: float, y1: float, x2: float, y2: float,
                  *, color: str = BLACK, lw: float = 2.2,
                  cycles: int = 4, amplitude: float = 13.0) -> None:
    """Draw a horizontal or vertical coil between two endpoints."""
    if abs(y2 - y1) < abs(x2 - x1):
        lead = min(20.0, abs(x2 - x1) * 0.18)
        sign = 1.0 if x2 >= x1 else -1.0
        draw_wire(ax, x1, y1, x1 + sign * lead, y1, color=color, lw=lw)
        draw_wire(ax, x2 - sign * lead, y2, x2, y2, color=color, lw=lw)
        xs, ys = _classic_horizontal_coil(x1 + sign * lead, x2 - sign * lead,
                                           y1, amplitude, cycles)
        ax.plot(xs, ys, color=color, lw=lw, solid_capstyle="round", zorder=3)
    else:
        lead = min(20.0, abs(y2 - y1) * 0.18)
        sign = 1.0 if y2 >= y1 else -1.0
        draw_wire(ax, x1, y1, x1, y1 + sign * lead, color=color, lw=lw)
        draw_wire(ax, x2, y2 - sign * lead, x2, y2, color=color, lw=lw)
        xs, ys = _classic_vertical_coil(y1 + sign * lead, y2 - sign * lead,
                                         x1, amplitude, cycles)
        ax.plot(xs, ys, color=color, lw=lw, solid_capstyle="round", zorder=3)


def _zigzag(start: float, end: float, center: float, width: float = 9.0,
            teeth: int = 6) -> tuple[np.ndarray, np.ndarray]:
    xs = np.linspace(start, end, teeth * 2 + 1)
    ys = np.full_like(xs, center)
    ys[1:-1:2] += width
    ys[2:-1:2] -= width
    return xs, ys


def draw_resistor(ax: Axes, x1: float, y1: float, x2: float, y2: float,
                  *, color: str = BLACK, lw: float = 2.2,
                  teeth: int = 6, width: float = 9.0) -> None:
    """Draw a standard zig-zag resistor, horizontal or vertical."""
    if abs(y2 - y1) < abs(x2 - x1):
        lead = min(18.0, abs(x2 - x1) * 0.18)
        sign = 1.0 if x2 >= x1 else -1.0
        draw_wire(ax, x1, y1, x1 + sign * lead, y1, color=color, lw=lw)
        draw_wire(ax, x2 - sign * lead, y2, x2, y2, color=color, lw=lw)
        xs, ys = _zigzag(x1 + sign * lead, x2 - sign * lead, y1,
                         width=width, teeth=teeth)
        ax.plot(xs, ys, color=color, lw=lw, solid_joinstyle="miter", zorder=3)
    else:
        lead = min(18.0, abs(y2 - y1) * 0.18)
        sign = 1.0 if y2 >= y1 else -1.0
        draw_wire(ax, x1, y1, x1, y1 + sign * lead, color=color, lw=lw)
        draw_wire(ax, x2, y2 - sign * lead, x2, y2, color=color, lw=lw)
        ys, xs = _zigzag(y1 + sign * lead, y2 - sign * lead, x1,
                         width=width, teeth=teeth)
        ax.plot(xs, ys, color=color, lw=lw, solid_joinstyle="miter", zorder=3)


def draw_josephson_junction(ax: Axes, x: float, y: float, *, color: str = BLACK,
                            size: float = 16.0, lw: float = 2.4,
                            terminal_span: float | None = None) -> None:
    """Draw a connected horizontal JJ cross with explicit terminal leads."""
    span = terminal_span if terminal_span is not None else size + 3.0
    draw_wire(ax, x - span, y, x, y, color=color, lw=lw)
    draw_wire(ax, x, y, x + span, y, color=color, lw=lw)
    ax.plot([x - size, x + size], [y - size, y + size], color=color, lw=lw,
            solid_capstyle="round", zorder=5)
    ax.plot([x - size, x + size], [y + size, y - size], color=color, lw=lw,
            solid_capstyle="round", zorder=5)
    ax.add_patch(Circle((x, y), 2.2, facecolor=color, edgecolor=color,
                        lw=0, zorder=6))


def draw_vertical_josephson_junction(ax: Axes, x: float, y_top: float,
                                     y_bottom: float, *, color: str = BLACK,
                                     size: float = 13.0, lw: float = 2.2) -> None:
    """Draw a vertically oriented, electrically continuous JJ cross."""
    y = (y_top + y_bottom) / 2.0
    draw_wire(ax, x, y_top, x, y, color=color, lw=lw)
    draw_wire(ax, x, y, x, y_bottom, color=color, lw=lw)
    draw_josephson_junction(ax, x, y, color=color, size=size, lw=lw,
                            terminal_span=0.0)


def draw_ground(ax: Axes, x: float, y: float, *, color: str = BLACK,
                lw: float = 2.0, width: float = 34.0) -> None:
    """Draw a conventional three-bar ground symbol."""
    draw_wire(ax, x, y + 20, x, y, color=color, lw=lw)
    for offset, span in ((0.0, width), (7.0, width * 0.68), (13.0, width * 0.38)):
        ax.plot([x - span / 2, x + span / 2], [y - offset, y - offset],
                color=color, lw=lw, solid_capstyle="butt", zorder=4)


def draw_current_arrow(ax: Axes, x: float, y1: float, y2: float,
                       *, label: str = "I_Bias", color: str = BLACK,
                       lw: float = 2.4, label_dx: float = 17.0) -> None:
    arrow = FancyArrowPatch((x, y1), (x, y2), arrowstyle="-|>", mutation_scale=20,
                            linewidth=lw, color=color, zorder=5)
    ax.add_patch(arrow)
    ax.text(x + label_dx, (y1 + y2) / 2, label, ha="left", va="center",
            fontsize=19, color=color)


def draw_port(ax: Axes, x: float, y: float, label: str, *, side: str = "left",
              color: str = BLACK) -> None:
    direction = 1 if side == "left" else -1
    draw_wire(ax, x, y, x + direction * 28, y, color=color, lw=3.0)
    tri_x = x + direction * 28
    ax.plot([tri_x, tri_x + direction * 12, tri_x],
            [y - 8, y, y + 8], color=color, lw=2.0, zorder=4)
    if side == "left":
        text_x, ha = x - 14, "right"
    else:
        text_x, ha = x + 14, "left"
    ax.text(text_x, y + 1, label, ha=ha, va="center",
            fontsize=25, color=color)


def draw_mutual_inductor(ax: Axes, x1: float, y1: float, x2: float, y2: float,
                         *, label_text: str = "M / k", color: str = BLACK,
                         lw: float = 2.0) -> None:
    """Draw two explicit parallel coil symbols and a coupling annotation."""
    if abs(y2 - y1) < abs(x2 - x1):
        draw_inductor(ax, x1, y1, x2, y1, color=color, lw=lw)
        draw_inductor(ax, x1, y2, x2, y2, color=color, lw=lw)
        ax.plot([x1, x1], [y1, y2], color=color, lw=1.2,
                linestyle=(0, (4, 3)), zorder=1)
        ax.plot([x2, x2], [y1, y2], color=color, lw=1.2,
                linestyle=(0, (4, 3)), zorder=1)
        ax.text((x1 + x2) / 2, max(y1, y2) + 28, label_text,
                ha="center", va="bottom", fontsize=15, color=color)
    else:
        draw_inductor(ax, x1, y1, x1, y2, color=color, lw=lw)
        draw_inductor(ax, x2, y1, x2, y2, color=color, lw=lw)
        ax.plot([x1, x2], [y1, y1], color=color, lw=1.2,
                linestyle=(0, (4, 3)), zorder=1)
        ax.plot([x1, x2], [y2, y2], color=color, lw=1.2,
                linestyle=(0, (4, 3)), zorder=1)
        ax.text(max(x1, x2) + 28, (y1 + y2) / 2, label_text,
                ha="left", va="center", fontsize=15, color=color)


def draw_block(ax: Axes, x: float, y: float, width: float, height: float,
               *, label_text: str = "", edgecolor: str = LIGHT_GRAY,
               facecolor: str = "none", alpha: float = 1.0,
               linestyle: str = "-", lw: float = 1.2) -> None:
    """Draw a functional/enclosure region, never a primitive component box."""
    ax.add_patch(Rectangle((x, y), width, height, facecolor=facecolor,
                           edgecolor=edgecolor, alpha=alpha, lw=lw,
                           linestyle=linestyle, zorder=0))
    if label_text:
        ax.text(x + 14, y + height - 14, label_text, ha="left", va="top",
                fontsize=16, color=edgecolor)


def draw_function_region(ax: Axes, x: float, y: float, width: float,
                         height: float, label_text: str, *, color: str,
                         alpha: float = 0.12) -> None:
    """Draw a restrained colored functional region, e.g. BVM S/R-Loop."""
    draw_block(ax, x, y, width, height, label_text=label_text,
               edgecolor=color, facecolor=color, alpha=alpha, lw=1.0)


def label(ax: Axes, x: float, y: float, text: str, *, size: float = 19,
          color: str = BLACK, ha: str = "center", va: str = "center",
          weight: str = "normal", style: str = "normal") -> None:
    ax.text(x, y, text, ha=ha, va=va, fontsize=size, color=color,
            fontweight=weight, fontstyle=style)
