"""Hierarchical probe-label factories for historical BVM/QB/JTL fixtures."""

from __future__ import annotations

from collections import OrderedDict
from typing import Mapping


def _instance_number(instance: int) -> int:
    if isinstance(instance, bool) or not isinstance(instance, int) or instance < 1:
        raise ValueError("instance must be a positive integer")
    return instance


def _branch(prefix: str, hierarchy: str, *, current: bool = True) -> dict[str, str]:
    result = OrderedDict(
        (
            ("phase", f"P({prefix}|{hierarchy})"),
            ("voltage", f"V({prefix}|{hierarchy})"),
        )
    )
    if current:
        result["current"] = f"I({prefix}|{hierarchy})"
    return result


def historical_bvm_probes(
    instance: int,
    *,
    include_sensing_current: bool = True,
) -> OrderedDict[str, object]:
    """Return the complete P/V/I map for one historical ``BVM`` instance."""

    number = _instance_number(instance)
    hierarchy = f"XBVM{number}"
    result: OrderedDict[str, object] = OrderedDict()
    for name in ("JM1", "JM2", "JS1", "JS2"):
        result[name] = _branch(f"B_{name}", hierarchy)
    for name in ("L_M1", "L_M2", "L_M3", "L_PM", "L_PSL"):
        result[name] = {"current": f"I({name}|{hierarchy})"}
    sensing = OrderedDict((("voltage", f"V(SL{number})"),))
    if include_sensing_current:
        sensing["current"] = f"I(L_SL|{hierarchy})"
    result["SL"] = sensing
    return result


def historical_bvm_array_probes(
    count: int = 4,
    *,
    include_terminal: bool = True,
) -> OrderedDict[str, object]:
    """Return deterministic probe maps for ``BVM1..BVM<count>``.

    The optional terminal group covers the last historical sensing section and
    the top-level ``BVMout`` branch; it does not silently substitute for the
    per-BVM internal observables.
    """

    if isinstance(count, bool) or not isinstance(count, int) or count < 1:
        raise ValueError("count must be a positive integer")
    result: OrderedDict[str, object] = OrderedDict(
        (f"BVM{index}", historical_bvm_probes(index))
        for index in range(1, count + 1)
    )
    if include_terminal:
        result["TERMINAL"] = OrderedDict(
            (
                (
                    "B_LD4_01",
                    {
                        "phase": "P(B_LD4_01)",
                        "voltage": "V(B_LD4_01)",
                        "current": "I(B_LD4_01)",
                    },
                ),
                (
                    "B_LD4_11",
                    {
                        "phase": "P(B_LD4_11)",
                        "voltage": "V(B_LD4_11)",
                        "current": "I(B_LD4_11)",
                    },
                ),
                (
                    "BVMout",
                    {
                        "phase": "P(BVMOUT)",
                        "voltage": "V(BVMOUT)",
                        "current": "I(BVMOUT)",
                    },
                ),
            )
        )
    return result


def original_bvmsim_qb_probes() -> OrderedDict[str, object]:
    """Return the active original ``BQ`` observable map."""

    return OrderedDict(
        (
            ("QBIN", {"voltage": "V(QBIN)"}),
            ("QBOUT", {"voltage": "V(QBOUT)"}),
            ("Lin", {"current": "I(LIN|XBQ1)"}),
            ("BJs", _branch("BJS", "XBQ1")),
            ("BJ1", _branch("BJ1", "XBQ1")),
            ("RJ1", {"current": "I(RJ1|XBQ1)"}),
            ("L1", {"current": "I(L1|XBQ1)"}),
            ("IB", {"current": "I(IB|XBQ1)"}),
            ("L2", {"current": "I(L2|XBQ1)"}),
            ("BJ2", _branch("BJ2", "XBQ1")),
            ("RJ2", {"current": "I(RJ2|XBQ1)"}),
            ("L3", {"current": "I(L3|XBQ1)"}),
        )
    )


def historical_jtl_probes(stages: int = 6) -> OrderedDict[str, object]:
    """Return P/V labels for both junctions in every historical JTL stage."""

    if isinstance(stages, bool) or not isinstance(stages, int) or stages < 1:
        raise ValueError("stages must be a positive integer")
    return OrderedDict(
        (
            (
                f"JTL{stage}",
                OrderedDict(
                    (
                        ("B01", _branch("B01", f"XJTL1_{stage}", current=False)),
                        ("B02", _branch("B02", f"XJTL1_{stage}", current=False)),
                    )
                ),
            )
            for stage in range(1, stages + 1)
        )
    )


def flatten_probe_labels(probes: Mapping[str, object]) -> tuple[str, ...]:
    """Flatten a nested probe map in insertion order without duplicates."""

    labels: list[str] = []

    def visit(value: object) -> None:
        if isinstance(value, Mapping):
            semantic = ("phase", "voltage", "current")
            if any(key in value for key in semantic):
                for key in semantic:
                    label = value.get(key)
                    if isinstance(label, str) and label not in labels:
                        labels.append(label)
                return
            for nested in value.values():
                visit(nested)

    visit(probes)
    return tuple(labels)
