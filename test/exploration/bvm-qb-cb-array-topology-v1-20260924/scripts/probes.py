"""Manifest-driven raw probes, checked against the real component sources."""

from __future__ import annotations

import re
from collections import OrderedDict
from pathlib import Path
from typing import Any

from config import ConfigError
from topology import Subcircuit, parse_subcircuits


def generate_probes(
    topology: dict[str, Any], source_paths: dict[str, str | Path]
) -> tuple[list[str], dict[str, object]]:
    subcircuits = parse_subcircuits(source_paths)
    instances = {item["instance"].casefold(): item for item in topology["instances"]}
    nodes: set[str] = {"FINAL_OUT"}
    top_level_elements = {"R_TERM"}
    for index in range(1, int(topology["array_size"]) + 1):
        top_level_elements.update({f"I_WL{index}", f"I_BL{index}", f"I_SE{index}"})
    for item in topology["instances"]:
        nodes.update(str(pin) for pin in item["pins"])
    node_labels = {node.casefold() for node in nodes}
    available_by_role: dict[str, Subcircuit] = {
        "BVM": subcircuits["BVM"], "BQ": subcircuits["QB"],
        "CB": subcircuits["CB"], "sJTL": subcircuits["SJTL"],
    }
    specs: OrderedDict[str, dict[str, Any]] = OrderedDict()
    component_roles: dict[str, str] = {}

    def add(label: str, group: str, *, instance: str | None = None,
            element: str | None = None, node: str | None = None) -> None:
        if label in specs:
            return
        if instance is not None and element is not None:
            record = instances.get(instance.casefold())
            if record is None:
                raise ConfigError(f"probe references absent instance {instance}")
            role = str(record["subcircuit"])
            actual = available_by_role[role]
            if element.casefold() not in {name.casefold() for name in actual.elements}:
                raise ConfigError(f"probe references absent element {element} in {role} ({instance})")
        elif element is not None and element.casefold() not in {
            name.casefold() for name in top_level_elements
        }:
            raise ConfigError(f"probe references absent top-level element {element}")
        if node is not None and node.casefold() not in node_labels:
            raise ConfigError(f"probe references absent node {node}")
        specs[label] = {"label": label, "group": group, "instance": instance,
                        "element": element, "node": node}

    size = int(topology["array_size"])
    mask = str(topology["mask"])
    for index in range(1, size + 1):
        for branch in ("WL", "BL", "SE"):
            source = f"I_{branch}{index}"
            add(f"I({source})", "stimulus", element=source)
        bvm = f"XBVM{index}"
        for element in ("B_JM1", "B_JM2", "B_JS1", "B_JS2"):
            for quantity in ("P", "V", "I"):
                add(f"{quantity}({element}|{bvm})", f"bvm{index}", instance=bvm, element=element)
        for element in ("L_M1", "L_M2", "L_M3", "L_PM", "L_SL"):
            for quantity in ("I", "V"):
                add(f"{quantity}({element}|{bvm})", f"bvm{index}", instance=bvm, element=element)
        for quantity in ("I", "V"):
            add(f"{quantity}(R_SL|{bvm})", f"bvm{index}", instance=bvm, element="R_SL")
        add(f"V(BVM{index}_SL)", f"bvm{index}", node=f"BVM{index}_SL")

        qb = f"XBQ{index}"
        qb_output = str(topology["levels"][index - 1]["qb_raw_node"] or
                        topology["levels"][index - 1]["merge_node"])
        for element in ("BJ1", "BJ2", "BJ3"):
            for quantity in ("P", "V", "I"):
                add(f"{quantity}({element}|{qb})", f"qb{index}", instance=qb, element=element)
        for element in ("LIN", "L1", "L2", "L3"):
            for quantity in ("I", "V"):
                add(f"{quantity}({element}|{qb})", f"qb{index}", instance=qb, element=element)
        add(f"V({topology['levels'][index - 1]['bvm_output_node']})", f"qb{index}",
            node=str(topology["levels"][index - 1]["bvm_output_node"]))
        add(f"V({qb_output})", f"qb{index}", node=qb_output)

    for level in topology["levels"]:
        instances_to_plot: list[tuple[str, str]] = []
        if level["qb_side_cb"]:
            instances_to_plot.append((str(level["qb_side_cb"]), f"Level {level['level']} QB-side CB"))
        if level["post_sjtl_cb"]:
            instances_to_plot.append((str(level["post_sjtl_cb"]), f"Level {level['level']} post-sJTL CB"))
        for instance, title_role in instances_to_plot:
            component_roles[instance] = title_role
            group = f"cb:{instance}"
            for element in ("BJ1", "BJ2"):
                for quantity in ("P", "V", "I"):
                    add(f"{quantity}({element}|{instance})", group,
                        instance=instance, element=element)
            for element in ("L1", "L2", "L3", "L4"):
                for quantity in ("I", "V"):
                    add(f"{quantity}({element}|{instance})", group,
                        instance=instance, element=element)
            add(f"V({level['merge_node']})", group, node=str(level["merge_node"]))
            add(f"V({level['carry_node']})", group, node=str(level["carry_node"]))

        for instance in level["sjtl_instances"]:
            group = f"sjtl:{instance}"
            for quantity in ("P", "V", "I"):
                add(f"{quantity}(BJ1|{instance})", group, instance=instance, element="BJ1")
            for element in ("L1", "L2"):
                for quantity in ("I", "V"):
                    add(f"{quantity}({element}|{instance})", group,
                        instance=instance, element=element)
            pins = instances[instance.casefold()]["pins"]
            add(f"V({pins[0]})", group, node=str(pins[0]))
            add(f"V({pins[1]})", group, node=str(pins[1]))

        for field in ("local_output", "upstream_output", "carry_output"):
            contribution = level.get(field, {})
            signal = contribution.get("signal")
            if signal:
                add(str(signal), f"merge:{level['level']}",
                    instance=str(contribution["instance"]), element=str(contribution["element"]))

    for node in sorted({str(level["merge_node"]) for level in topology["levels"]} |
                       {str(level["carry_node"]) for level in topology["levels"]}):
        add(f"V({node})", "acc_gap", node=node)
    add("V(FINAL_OUT)", "terminal", node="FINAL_OUT")
    add("V(R_TERM)", "terminal", element="R_TERM")
    add("I(R_TERM)", "terminal", element="R_TERM")

    lines = [f".print {label}" for label in specs]
    manifest: dict[str, object] = {
        "schema": "bvm-qb-cb-array-probes-v1",
        "render_status": topology.get("render_status", "STATIC_RENDER"),
        "mask": mask,
        "signals": list(specs.values()),
        "component_roles": component_roles,
        "unavailable_merge_inputs": [
            {"level": level["level"], "input": "upstream",
             "reason": level["upstream_output"].get("reason")}
            for level in topology["levels"]
            if level["upstream_output"]["status"] == "UNAVAILABLE"
        ],
        "scientific_classification_performed": False,
    }
    return lines, manifest


def validate_probe_lines(lines: list[str], manifest: dict[str, object]) -> None:
    """Check uniqueness and resolution against instances/elements already resolved."""
    labels = [str(item["label"]) for item in manifest["signals"]]
    if len(labels) != len(set(labels)):
        raise ConfigError("probe manifest contains duplicate labels")
    expected = [f".print {label}" for label in labels]
    if lines != expected:
        raise ConfigError("rendered .print lines do not match probe manifest")
    for line in lines:
        if not re.fullmatch(r"\.print [PVI]\([^()]+\)", line):
            raise ConfigError(f"unsupported generated probe syntax: {line}")
