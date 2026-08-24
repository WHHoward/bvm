#!/usr/bin/env python3
"""Validate displayed semantic endpoints against the selected Q0 netlist."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


PRIMITIVE_PREFIXES = set("RLCBIV")


def clean_lines(path: Path) -> list[str]:
    lines = []
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.split("*", 1)[0].strip()
        if line:
            lines.append(line)
    return lines


def parse_section(path: Path, subckt: str | None = None) -> dict[str, tuple[str, str, str]]:
    lines = clean_lines(path)
    selected: list[str] = []
    if subckt is None:
        in_sub = False
        for line in lines:
            low = line.lower()
            if low.startswith(".subckt"):
                in_sub = True
            elif low.startswith(".ends"):
                in_sub = False
            elif not in_sub:
                selected.append(line)
    else:
        in_sub = False
        wanted = False
        for line in lines:
            toks = line.split()
            low = line.lower()
            if low.startswith(".subckt"):
                in_sub = True
                wanted = len(toks) >= 2 and toks[1].lower() == subckt.lower()
                continue
            if low.startswith(".ends"):
                if wanted:
                    break
                in_sub = False
                wanted = False
                continue
            if in_sub and wanted:
                selected.append(line)
    result: dict[str, tuple[str, str, str]] = {}
    for line in selected:
        toks = line.split()
        if len(toks) < 3 or toks[0][0].upper() not in PRIMITIVE_PREFIXES:
            continue
        result[toks[0]] = (toks[1], toks[2], " ".join(toks[3:]))
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    repo = args.repo_root.resolve()
    source = repo / manifest["source_deck"]
    cell = repo / manifest["subcircuit_deck"]
    top = parse_section(source)
    internal = parse_section(cell, manifest["subcircuit"])

    errors: list[str] = []
    checked = []
    for item in manifest["displayed_components"]:
        scope = item["scope"]
        table = internal if scope == "BQ" else top
        actual = table.get(item["name"])
        expected = tuple(item["nodes"])
        if actual is None:
            errors.append(f"missing element {scope}/{item['name']}")
            continue
        if actual[:2] != expected:
            errors.append(
                f"endpoint mismatch {scope}/{item['name']}: "
                f"semantic={expected!r}, netlist={actual[:2]!r}"
            )
            continue
        checked.append({"scope": scope, "name": item["name"], "nodes": list(expected)})

    for name in manifest["required_internal_components"]:
        if not any(x["scope"] == "BQ" and x["name"] == name
                   for x in manifest["displayed_components"]):
            errors.append(f"critical internal element not displayed: BQ/{name}")
        if name not in internal:
            errors.append(f"critical internal element absent from deck: BQ/{name}")

    omitted = []
    for item in manifest.get("omitted_from_display", []):
        name = item["name"]
        scope = item["scope"]
        table = internal if scope == "BQ" else top
        if name not in table:
            errors.append(f"declared omitted element absent from deck: {scope}/{name}")
        omitted.append({"scope": scope, "name": name, "reason": item["reason"]})

    result = {
        "status": "PASS" if not errors else "FAIL",
        "source_deck": manifest["source_deck"],
        "subcircuit_deck": manifest["subcircuit_deck"],
        "subcircuit": manifest["subcircuit"],
        "checked_displayed_components": checked,
        "omitted_from_display": omitted,
        "errors": errors,
        "checks": {
            "element_exists": not any(x.startswith("missing element") for x in errors),
            "endpoint_connectivity": not any(x.startswith("endpoint mismatch") for x in errors),
            "critical_path_displayed": not any("critical internal element not displayed" in x for x in errors),
            "no_invented_element": not bool(errors),
        },
    }
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n",
                           encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    raise SystemExit(0 if not errors else 1)


if __name__ == "__main__":
    main()
