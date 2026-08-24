"""Geometry ledger used to validate deterministic schematic drawings."""

from __future__ import annotations

from pathlib import Path
import json
from typing import Iterable


Point = tuple[float, float]


def _point(point: Iterable[float]) -> list[float]:
    values = [float(value) for value in point]
    if len(values) != 2:
        raise ValueError(f"point must have two coordinates: {point!r}")
    return values


class GeometryLedger:
    """Record the endpoint geometry used by the renderer.

    The ledger is deliberately coordinate-level rather than a second semantic
    netlist.  The validator checks that every drawn wire terminates on a real
    component terminal, anchor, port, ground or current-arrow terminal, and
    that every component terminal is incident to one of those connections.
    """

    def __init__(self, *, tolerance: float = 1e-9) -> None:
        self.tolerance = tolerance
        self.components: list[dict] = []
        self.wires: list[dict] = []
        self.anchors: list[dict] = []
        self.fixed_points: list[dict] = []

    def add_component(self, name: str, kind: str, start: Point, end: Point,
                      *, scope: str = "schematic", symbol_center: Point | None = None) -> None:
        item = {
            "name": name,
            "kind": kind,
            "scope": scope,
            "terminals": {"a": _point(start), "b": _point(end)},
        }
        if symbol_center is not None:
            item["symbol_center"] = _point(symbol_center)
        self.components.append(item)
        self.fixed_points.extend([
            {"name": f"{name}:a", "kind": "component_terminal", "point": _point(start)},
            {"name": f"{name}:b", "kind": "component_terminal", "point": _point(end)},
        ])

    def add_wire(self, name: str, start: Point, end: Point, *, color: str = "black") -> None:
        item = {"name": name, "start": _point(start), "end": _point(end), "color": color}
        self.wires.append(item)

    def add_anchor(self, name: str, point: Point) -> None:
        p = _point(point)
        self.anchors.append({"name": name, "point": p})
        self.fixed_points.append({"name": name, "kind": "anchor", "point": p})

    def add_fixed(self, name: str, point: Point, *, kind: str) -> None:
        p = _point(point)
        self.fixed_points.append({"name": name, "kind": kind, "point": p})

    def add_port(self, name: str, terminal: Point, outer: Point) -> None:
        self.add_fixed(name, terminal, kind="port_terminal")
        self.add_fixed(f"{name}:outer", outer, kind="port_outer")

    def add_ground(self, name: str, terminal: Point) -> None:
        self.add_fixed(name, terminal, kind="ground_terminal")

    def add_current_arrow(self, name: str, start: Point, end: Point) -> None:
        self.add_fixed(f"{name}:start", start, kind="current_terminal")
        self.add_fixed(f"{name}:end", end, kind="current_terminal")

    def as_dict(self) -> dict:
        return {
            "schema": "josim-geometric-connectivity-v1",
            "coordinate_tolerance": self.tolerance,
            "components": self.components,
            "wires": self.wires,
            "anchors": self.anchors,
            "fixed_points": self.fixed_points,
        }

    def write(self, path: Path) -> None:
        path.write_text(json.dumps(self.as_dict(), indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8")
