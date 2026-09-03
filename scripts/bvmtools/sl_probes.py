"""Probe-label factories for the historical multi-BVM sensing line."""

from __future__ import annotations

from collections import OrderedDict


# The first/last junctions of each historical sensing-line section.  BVM4 has
# eleven section junctions because BVMout is a separate top-level junction.
HISTORICAL_SL_ENDPOINT_JUNCTIONS = (
    ("BVM1", "B_LD01", "B_LD12"),
    ("BVM2", "B_LD2_01", "B_LD2_12"),
    ("BVM3", "B_LD3_01", "B_LD3_12"),
    ("BVM4", "B_LD4_01", "B_LD4_11"),
)


def _junction_probe(name: str) -> OrderedDict[str, str]:
    return OrderedDict(
        (
            ("phase", f"P({name})"),
            ("voltage", f"V({name})"),
            ("current", f"I({name})"),
        )
    )


def historical_sensing_line_endpoint_probes() -> OrderedDict[str, object]:
    """Return first/last P/V/I probes for every historical BVM SL section."""

    return OrderedDict(
        (
            (
                bvm,
                OrderedDict(
                    (
                        ("first", _junction_probe(first)),
                        ("last", _junction_probe(last)),
                    )
                ),
            )
            for bvm, first, last in HISTORICAL_SL_ENDPOINT_JUNCTIONS
        )
    )
