"""Parameterized top-level topology renderer and source-backed manifest."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from config import ConfigError


SOURCE_FILES = {
    "BVM": Path("circuits/bvm/bvm_cell_0923.cir"),
    "QB": Path("circuits/qb/BQ_0923.cir"),
    "CB": Path("circuits/CB/CB_0923.cir"),
    "SJTL": Path("circuits/sJTL_0923.cir"),
}
EXPECTED_PINS = {
    "BVM": ("WL", "BL", "SE", "SL"),
    "QB": ("IN", "OUT"),
    "CB": ("IN", "OUT"),
    "SJTL": ("IN", "OUT"),
}
REQUIRED_ELEMENTS = {
    "BVM": ("B_JM1", "B_JM2", "B_JS1", "B_JS2", "L_M1", "L_M2", "L_M3", "L_PM", "L_SL"),
    "QB": ("BJ1", "BJ2", "BJ3", "Lin", "L1", "L2", "L3"),
    "CB": ("BJ1", "BJ2", "L1", "L2", "L3", "L4"),
    "SJTL": ("BJ1", "L1", "L2"),
}


@dataclass(frozen=True)
class Subcircuit:
    name: str
    pins: tuple[str, ...]
    elements: frozenset[str]
    path: Path


def parse_subcircuits(paths: dict[str, str | Path]) -> dict[str, Subcircuit]:
    """Read actual subcircuit headers/elements; never infer probes from memory."""
    result: dict[str, Subcircuit] = {}
    for role, path_value in paths.items():
        path = Path(path_value)
        active_name: str | None = None
        active_pins: tuple[str, ...] = ()
        elements: set[str] = set()
        found: list[Subcircuit] = []
        for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            line = raw.strip()
            if not line or line.startswith("*"):
                continue
            if line.casefold().startswith(".subckt"):
                if active_name is not None:
                    raise ConfigError(f"{path}:{line_no}: nested .subckt is not supported")
                tokens = line.split()
                if len(tokens) < 3:
                    raise ConfigError(f"{path}:{line_no}: malformed .subckt header")
                active_name = tokens[1]
                active_pins = tuple(tokens[2:])
                elements = set()
                continue
            if line.casefold().startswith(".ends"):
                if active_name is None:
                    raise ConfigError(f"{path}:{line_no}: .ends without .subckt")
                found.append(Subcircuit(active_name, active_pins, frozenset(elements), path))
                active_name = None
                active_pins = ()
                elements = set()
                continue
            if active_name is not None and not line.startswith("."):
                element = line.split()[0]
                if element.casefold() not in {item.casefold() for item in elements}:
                    elements.add(element)
        if active_name is not None:
            raise ConfigError(f"{path}: unterminated .subckt {active_name}")
        target_name = {"BVM": "BVM", "QB": "BQ", "CB": "CB", "SJTL": "sJTL"}[role]
        matches = [item for item in found if item.name.casefold() == target_name.casefold()]
        if len(matches) != 1:
            raise ConfigError(f"{path}: expected exactly one .subckt {target_name}, found {len(matches)}")
        subckt = matches[0]
        if tuple(pin.casefold() for pin in subckt.pins) != tuple(pin.casefold() for pin in EXPECTED_PINS[role]):
            raise ConfigError(f"{path}: {target_name} pin order changed: {subckt.pins}")
        missing = [name for name in REQUIRED_ELEMENTS[role]
                   if name.casefold() not in {item.casefold() for item in subckt.elements}]
        if missing:
            raise ConfigError(f"{path}: {target_name} is missing required elements: {missing}")
        result[role] = subckt
    return result


class _UnionFind:
    def __init__(self, items: Iterable[str]) -> None:
        self.parent = {item: item for item in items}

    def find(self, item: str) -> str:
        parent = self.parent[item]
        if parent != item:
            self.parent[item] = self.find(parent)
        return self.parent[item]

    def union(self, left: str, right: str) -> None:
        a, b = self.find(left), self.find(right)
        if a != b:
            self.parent[b] = a


def _physical_merge_aliases(params: dict[str, object]) -> dict[str, str]:
    size = int(params["ARRAY_SIZE"])
    labels = [f"MERGE{i}" for i in range(1, size + 1)] + ["FINAL_OUT"]
    uf = _UnionFind(labels)
    counts = params["SJTL_COUNT"]
    post = params["POST_SJTL_CB"]
    assert isinstance(counts, list) and isinstance(post, list)
    for index in range(size - 1):
        if counts[index] == 0 and post[index] == 0:
            uf.union(f"MERGE{index + 1}", f"MERGE{index + 2}")
    if counts[-1] == 0 and post[-1] == 0:
        uf.union(f"MERGE{size}", "FINAL_OUT")

    groups: dict[str, list[str]] = {}
    for label in labels:
        groups.setdefault(uf.find(label), []).append(label)
    aliases: dict[str, str] = {}
    for members in groups.values():
        canonical = "FINAL_OUT" if "FINAL_OUT" in members else min(
            members, key=lambda label: int(label[5:])
        )
        for label in members:
            aliases[label] = canonical
    return aliases


def _branch_signal(instance: str, element: str) -> str:
    return f"I({element.upper()}|{instance.upper()})"


def _source_record(status: str, *, instance: str | None = None, element: str | None = None,
                   reason: str | None = None) -> dict[str, object]:
    if instance is None or element is None:
        return {"status": status, "instance": None, "element": None, "signal": None, "reason": reason}
    return {"status": status, "instance": instance, "element": element,
            "signal": _branch_signal(instance, element), "reason": reason}


def render_topology(params: dict[str, object], sources: dict[str, str | Path]) -> tuple[list[str], dict[str, object]]:
    """Return deterministic top-level instances and source-verified manifest."""
    size = int(params["ARRAY_SIZE"])
    mask = str(params["MASK"])
    qb_flags = params["QB_CB"]
    counts = params["SJTL_COUNT"]
    post_flags = params["POST_SJTL_CB"]
    assert isinstance(qb_flags, list) and isinstance(counts, list) and isinstance(post_flags, list)
    if not (len(qb_flags) == len(counts) == len(post_flags) == size):
        raise ConfigError("topology arrays must all equal ARRAY_SIZE")
    parsed = parse_subcircuits(sources)
    aliases = _physical_merge_aliases(params)
    lines: list[str] = []
    instances: list[dict[str, object]] = []
    levels: list[dict[str, object]] = []

    def add_instance(name: str, subckt_role: str, pins: list[str], subckt_name: str) -> None:
        if name.casefold() in {str(item["instance"]).casefold() for item in instances}:
            raise ConfigError(f"duplicate generated instance name {name}")
        if len(pins) != len(parsed[subckt_role].pins):
            raise ConfigError(f"{name}: generated pin count does not match source subcircuit")
        lines.append(f"{name} {' '.join(pins)} {subckt_name}")
        instances.append({"instance": name, "subcircuit": subckt_name, "pins": pins})

    for index in range(1, size + 1):
        merge_label = f"MERGE{index}"
        merge_node = aliases[merge_label]
        bvm = f"XBVM{index}"
        qb = f"XBQ{index}"
        bvm_out = f"BVM{index}_SL"
        qb_raw = f"QB{index}_RAW"
        qbc_instance = f"XQBCB{index}" if qb_flags[index - 1] else None
        add_instance(bvm, "BVM", [f"WL{index}", f"BL{index}", f"SE{index}", bvm_out], "BVM")
        qb_out = qb_raw if qbc_instance else merge_node
        add_instance(qb, "QB", [bvm_out, qb_out], "BQ")
        if qbc_instance:
            add_instance(qbc_instance, "CB", [qb_raw, merge_node], "CB")

        local_last = (qbc_instance, "L4") if qbc_instance else (qb, "L3")
        upstream: dict[str, object]
        if index == 1:
            upstream = _source_record("NOT_APPLICABLE", reason="level 1 has no previous carry")
        elif post_flags[index - 2]:
            upstream = _source_record("AVAILABLE", instance=f"XPOSTCB{index - 1}", element="L4")
        elif counts[index - 2] > 0:
            upstream = _source_record(
                "AVAILABLE", instance=f"XSJTL{index - 1}_{counts[index - 2]:02d}", element="L2"
            )
        else:
            upstream = _source_record(
                "UNAVAILABLE", reason="previous carry is a direct wire with no distinct branch element"
            )

        carry_node = aliases[f"MERGE{index + 1}"] if index < size else aliases["FINAL_OUT"]
        sjtl_instances: list[str] = []
        current = merge_node
        count = counts[index - 1]
        for stage in range(1, count + 1):
            instance = f"XSJTL{index}_{stage:02d}"
            sjtl_instances.append(instance)
            needs_internal_out = stage < count or bool(post_flags[index - 1])
            if needs_internal_out:
                out_node = f"L{index}_{stage:02d}"
            else:
                out_node = carry_node
            add_instance(instance, "SJTL", [current, out_node], "sJTL")
            current = out_node

        post_instance = f"XPOSTCB{index}" if post_flags[index - 1] else None
        carry_output: dict[str, object]
        if post_instance:
            add_instance(post_instance, "CB", [current, carry_node], "CB")
            carry_output = _source_record("AVAILABLE", instance=post_instance, element="L4")
        elif count > 0:
            carry_output = _source_record(
                "AVAILABLE", instance=f"XSJTL{index}_{count:02d}", element="L2"
            )
        else:
            carry_output = _source_record(
                "UNAVAILABLE", reason="zero sJTL and no post-CB: carry has no distinct branch element"
            )

        levels.append({
            "level": index,
            "bvm": bvm,
            "bvm_output_node": bvm_out,
            "qb": qb,
            "qb_raw_node": qb_raw if qbc_instance else None,
            "qb_side_cb": qbc_instance,
            "logical_merge_node": merge_label,
            "merge_node": merge_node,
            "local_output": {
                "instance": local_last[0], "element": local_last[1],
                "signal": _branch_signal(str(local_last[0]), str(local_last[1])),
                "status": "AVAILABLE",
            },
            "upstream_output": upstream,
            "merge_inputs": {"local_signal": _branch_signal(str(local_last[0]), str(local_last[1])),
                             "upstream_signal": upstream.get("signal"),
                             "upstream_status": upstream["status"]},
            "sjtl_instances": sjtl_instances,
            "post_sjtl_cb": post_instance,
            "carry_label": f"CARRY{index}",
            "carry_node": carry_node,
            "carry_output": carry_output,
        })

    alias_map = {label: node for label, node in aliases.items() if label != node}
    manifest: dict[str, object] = {
        "schema": "bvm-qb-cb-array-topology-v1",
        "render_status": "RENDER_FIXTURE_ONLY" if params.get("RENDER_FIXTURE_ONLY") else "STATIC_RENDER",
        "array_size": size,
        "mask": mask,
        "topology": {"QB_CB": qb_flags, "SJTL_COUNT": counts, "POST_SJTL_CB": post_flags},
        "levels": levels,
        "logical_node_aliases": alias_map,
        "carry_aliases": {level["carry_label"]: level["carry_node"] for level in levels},
        "instances": instances,
        "terminal": {"output_node": aliases["FINAL_OUT"], "resistor": "R_TERM", "resistance": params["TERM_R"]},
        "solver": {"analysis": "transient", "dt": params["DT"], "stop": params["STOP"]},
        "scientific_interpretation_performed": False,
        "automatic_follow_up": False,
    }
    return lines, manifest
