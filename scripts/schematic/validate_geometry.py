#!/usr/bin/env python3
"""Validate geometric endpoint continuity of a deterministic schematic."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def distance(a: list[float], b: list[float]) -> float:
    return max(abs(float(a[0]) - float(b[0])), abs(float(a[1]) - float(b[1])))


def matching(point: list[float], candidates: list[dict], tolerance: float) -> list[dict]:
    return [item for item in candidates if distance(point, item["point"]) <= tolerance]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--geometry", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    data = json.loads(args.geometry.read_text(encoding="utf-8"))
    tolerance = float(data.get("coordinate_tolerance", 1e-9))
    fixed = list(data.get("fixed_points", []))
    components = list(data.get("components", []))
    wires = list(data.get("wires", []))

    invalid_wire_endpoints: list[dict] = []
    wire_endpoint_points: list[list[float]] = []
    for wire in wires:
        for side in ("start", "end"):
            point = wire[side]
            wire_endpoint_points.append(point)
            if not matching(point, fixed, tolerance):
                invalid_wire_endpoints.append({
                    "wire": wire["name"], "side": side, "point": point,
                })

    unconnected_terminals: list[dict] = []
    for component in components:
        for terminal, point in component["terminals"].items():
            if not matching(point, [
                {"point": other} for other in wire_endpoint_points
            ], tolerance):
                # A direct terminal-to-terminal or terminal-to-anchor connection
                # is also valid even when no explicit zero-length wire is drawn.
                peers = [item for item in fixed if item["name"] != f"{component['name']}:{terminal}"]
                if not matching(point, peers, tolerance):
                    unconnected_terminals.append({
                        "component": component["name"],
                        "terminal": terminal,
                        "point": point,
                    })

    duplicate_fixed_points: list[dict] = []
    for index, first in enumerate(fixed):
        for second in fixed[index + 1:]:
            if first["name"] == second["name"]:
                continue
            if distance(first["point"], second["point"]) <= tolerance:
                duplicate_fixed_points.append({
                    "first": first["name"], "second": second["name"],
                    "point": first["point"],
                })

    errors = invalid_wire_endpoints + unconnected_terminals
    result = {
        "status": "PASS" if not errors else "FAIL",
        "geometry": str(args.geometry),
        "coordinate_tolerance": tolerance,
        "components": len(components),
        "wires": len(wires),
        "anchors": len(data.get("anchors", [])),
        "checks": {
            "wire_endpoints_on_fixed_geometry": not invalid_wire_endpoints,
            "component_terminals_connected": not unconnected_terminals,
            "duplicate_fixed_points_are_allowed_junctions": True,
        },
        "invalid_wire_endpoints": invalid_wire_endpoints,
        "unconnected_terminals": unconnected_terminals,
        "coincident_junction_points": duplicate_fixed_points,
    }
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n",
                           encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    raise SystemExit(0 if not errors else 1)


if __name__ == "__main__":
    main()
