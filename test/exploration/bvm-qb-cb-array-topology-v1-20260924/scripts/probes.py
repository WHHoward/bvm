"""Manifest-driven raw probes, checked against the real component sources."""

from __future__ import annotations

import re
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Any

from config import ConfigError
from topology import (
    T1_CORE_INDUCTORS, T1_CORE_JUNCTIONS, Subcircuit, parse_subcircuits,
)


PROBE_PROFILES = {"core", "debug"}


def generate_probes(
    topology: dict[str, Any], source_paths: dict[str, str | Path],
    profile: str | None = None,
) -> tuple[list[str], dict[str, object]]:
    """Render either compact acquisition probes or the historical detailed set."""
    profile = profile or str(topology.get("probe_profile", "core"))
    if profile not in PROBE_PROFILES:
        raise ConfigError(f"unknown probe profile {profile!r}; expected core or debug")
    output_mode = str(topology.get("output_mode", "TERMINAL"))
    if output_mode not in {"TERMINAL", "T1"}:
        raise ConfigError(f"unknown output mode {output_mode!r}; expected TERMINAL or T1")

    subcircuits = parse_subcircuits(source_paths)
    instances = {item["instance"].casefold(): item for item in topology["instances"]}
    nodes: set[str] = {"FINAL_OUT"}
    top_level_elements = {"R_TERM"}
    if output_mode == "T1":
        receiver = topology.get("receiver", {})
        bias3 = "I_BIAS3" if receiver.get("bias3_source") == "CURRENT" else "V_BIAS3"
        top_level_elements.update({"R_S", "R_C", "V_T1_LINK", "V_BIAS1", "V_BIAS2", bias3})
        if receiver.get("clock_mode") == "PULSE":
            nodes.add("CLK_RAW")
            top_level_elements.update({"V_TRIG_CLK", "R_TRIG_CLK"})
        else:
            top_level_elements.add("R_CLK_QUIET")
    for index in range(1, int(topology["array_size"]) + 1):
        top_level_elements.update({f"I_WL{index}", f"I_BL{index}", f"I_SE{index}"})
    for item in topology["instances"]:
        nodes.update(str(pin) for pin in item["pins"])
    node_labels = {node.casefold() for node in nodes}
    available_by_role: dict[str, Subcircuit] = {
        "BVM": subcircuits["BVM"], "BQ": subcircuits["QB"],
        "CB": subcircuits["CB"], "sJTL": subcircuits["SJTL"],
    }
    if output_mode == "T1":
        if "T1" not in subcircuits:
            raise ConfigError("OUTPUT_MODE=T1 requires the source-verified T1 subcircuit")
        available_by_role["T1"] = subcircuits["T1"]
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
        if profile == "debug":
            junction_quantities = ("P", "V", "I")
            inductor_quantities = ("I", "V")
        else:
            junction_quantities = ("P", "V")
            inductor_quantities = ("I",)
        for element in ("B_JM1", "B_JM2", "B_JS1", "B_JS2"):
            for quantity in junction_quantities:
                add(f"{quantity}({element}|{bvm})", f"bvm{index}",
                    instance=bvm, element=element)
        for element in ("L_M1", "L_M2", "L_M3", "L_PM", "L_SL"):
            for quantity in inductor_quantities:
                add(f"{quantity}({element}|{bvm})", f"bvm{index}",
                    instance=bvm, element=element)
        if profile == "debug" and "R_SL".casefold() in {
            name.casefold() for name in subcircuits["BVM"].elements
        }:
            for quantity in ("I", "V"):
                add(f"{quantity}(R_SL|{bvm})", f"bvm{index}",
                    instance=bvm, element="R_SL")
        add(f"V(BVM{index}_SL)", f"bvm{index}", node=f"BVM{index}_SL")

        qb = f"XBQ{index}"
        level = topology["levels"][index - 1]
        qb_output = str(level["qb_raw_node"] or level["merge_node"])
        for element in ("BJ1", "BJ2", "BJ3"):
            for quantity in junction_quantities:
                add(f"{quantity}({element}|{qb})", f"qb{index}",
                    instance=qb, element=element)
        for element in ("LIN", "L1", "L2", "L3"):
            for quantity in inductor_quantities:
                add(f"{quantity}({element}|{qb})", f"qb{index}",
                    instance=qb, element=element)
        add(f"V({level['bvm_output_node']})", f"qb{index}",
            node=str(level["bvm_output_node"]))
        add(f"V({qb_output})", f"qb{index}", node=qb_output)

    # The subsystem pages use the same manifest, but CORE records only the
    # compact CB/sJTL state needed for junction, branch-current, and boundaries.
    for level in topology["levels"]:
        cb_instances: list[tuple[str, str]] = []
        if level["qb_side_cb"]:
            cb_instances.append((str(level["qb_side_cb"]), f"Level {level['level']} QB-side CB"))
        if level["post_sjtl_cb"]:
            cb_instances.append((str(level["post_sjtl_cb"]), f"Level {level['level']} post-sJTL CB"))
        for instance, role in cb_instances:
            component_roles[instance] = role
            group = f"cb:{instance}"
            elements = ("BJ1", "BJ2")
            for element in elements:
                for quantity in junction_quantities:
                    add(f"{quantity}({element}|{instance})", group,
                        instance=instance, element=element)
            inductors = ("L1", "L2", "L3", "L4") if profile == "debug" else ("L1", "L4")
            for element in inductors:
                for quantity in inductor_quantities:
                    add(f"{quantity}({element}|{instance})", group,
                        instance=instance, element=element)
            pins = instances[instance.casefold()]["pins"]
            add(f"V({pins[0]})", group, node=str(pins[0]))
            add(f"V({pins[1]})", group, node=str(pins[1]))

        for instance in level["sjtl_instances"]:
            group = f"sjtl:{instance}"
            for quantity in junction_quantities:
                add(f"{quantity}(BJ1|{instance})", group,
                    instance=instance, element="BJ1")
            sjtl_inductors = ("L1", "L2") if profile == "debug" else ("L2",)
            for element in sjtl_inductors:
                for quantity in inductor_quantities:
                    add(f"{quantity}({element}|{instance})", group,
                        instance=instance, element=element)
            pins = instances[instance.casefold()]["pins"]
            if profile == "debug":
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
    if output_mode == "T1":
        receiver = topology.get("receiver", {})
        t1 = instances.get("xt1")
        if (not isinstance(receiver, dict) or t1 is None
                or str(t1.get("subcircuit", "")).casefold() != "t1"):
            raise ConfigError("T1 probe generation requires the XT1 topology manifest instance")
        if (receiver.get("instance") != t1["instance"]
                or receiver.get("input_node") != t1["pins"][0]):
            raise ConfigError("T1 receiver manifest disagrees with actual XT1 pins")
        component_roles[str(t1["instance"])] = "T1 receiver"
        for node in ("T1_I", "CLK", "S", "C"):
            add(f"V({node})", "t1_boundary", node=node)
        clock_mode = str(receiver.get("clock_mode", "QUIET"))
        if clock_mode == "PULSE":
            add("V(CLK_RAW)", "t1_clock", node="CLK_RAW")
            add("I(R_TRIG_CLK)", "t1_clock", element="R_TRIG_CLK")
        if profile == "debug":
            for element in ("R_S", "R_C"):
                add(f"I({element})", "t1_load", element=element)

        t1_elements = subcircuits["T1"].elements
        def numbered(prefix: str) -> list[str]:
            matches = [name for name in t1_elements
                       if name.casefold().startswith(prefix.casefold())
                       and name[len(prefix):].isdigit()]
            return sorted(matches, key=lambda name: int(name[len(prefix):]))

        junctions = numbered("B_J") if profile == "debug" else list(T1_CORE_JUNCTIONS)
        inductors = numbered("L") if profile == "debug" else list(T1_CORE_INDUCTORS)
        junction_quantities = ("P", "V", "I") if profile == "debug" else ("P", "V")
        inductor_quantities = ("I", "V") if profile == "debug" else ("I",)
        for element in junctions:
            for quantity in junction_quantities:
                add(f"{quantity}({element}|XT1)", "t1", instance="XT1", element=element)
        if clock_mode == "PULSE" and profile != "debug":
            for element in ("B_J2", "B_J3"):
                for quantity in ("P", "V"):
                    add(f"{quantity}({element}|XT1)", "t1_clock", instance="XT1",
                        element=element)
        for element in inductors:
            for quantity in inductor_quantities:
                add(f"{quantity}({element}|XT1)", "t1", instance="XT1", element=element)
        add("V(FINAL_OUT)", "t1_boundary", node="FINAL_OUT")
    else:
        add("V(FINAL_OUT)", "terminal", node="FINAL_OUT")
        if profile == "debug":
            add("V(R_TERM)", "terminal", element="R_TERM")
        add("I(R_TERM)", "terminal", element="R_TERM")

    lines = [f".print {label}" for label in specs]
    counts = Counter(str(item["group"]) for item in specs.values())
    manifest: dict[str, object] = {
        "schema": "bvm-qb-cb-array-probes-v1",
        "render_status": topology.get("render_status", "STATIC_RENDER"),
        "mask": mask,
        "profile": profile,
        "signal_count": len(specs),
        "counts_by_group": dict(sorted(counts.items())),
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
    if output_mode == "T1":
        manifest["output_mode"] = "T1"
        manifest["clock_mode"] = str(topology.get("receiver", {}).get("clock_mode", "QUIET"))
    return lines, manifest


def validate_probe_lines(lines: list[str], manifest: dict[str, object]) -> None:
    """Check uniqueness and resolution against instances/elements already resolved."""
    labels = [str(item["label"]) for item in manifest["signals"]]
    if len(labels) != len(set(labels)):
        raise ConfigError("probe manifest contains duplicate labels")
    if manifest.get("signal_count") != len(labels):
        raise ConfigError("probe manifest signal_count disagrees with signals")
    if manifest.get("profile") not in PROBE_PROFILES:
        raise ConfigError("probe manifest has an invalid profile")
    expected = [f".print {label}" for label in labels]
    if lines != expected:
        raise ConfigError("rendered .print lines do not match probe manifest")
    for line in lines:
        if not re.fullmatch(r"\.print [PVI]\([^()]+\)", line):
            raise ConfigError(f"unsupported generated probe syntax: {line}")
