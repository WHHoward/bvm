#!/usr/bin/env python3
"""Add only missing historical SL endpoint probes to copied PHASE-B decks."""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
PARENT_ROOT = EXP / "runs"
OUTPUT_ROOT = EXP / "runs_sl_endpoints"
STATES = ("0000", "1000", "0100", "0010", "0001", "1111")

sys.path.insert(0, str(REPO / "scripts"))
from bvmtools.probes import flatten_probe_labels  # noqa: E402
from bvmtools.sl_probes import (  # noqa: E402
    HISTORICAL_SL_ENDPOINT_JUNCTIONS,
    historical_sensing_line_endpoint_probes,
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def endpoint_labels() -> tuple[str, ...]:
    return flatten_probe_labels(historical_sensing_line_endpoint_probes())


def added_endpoint_labels() -> tuple[str, ...]:
    """Return BVM1--BVM3 labels; BVM4 endpoints are already in the parent deck."""

    labels: list[str] = []
    for _, first, last in HISTORICAL_SL_ENDPOINT_JUNCTIONS[:3]:
        for junction in (first, last):
            labels.extend(f"{kind}({junction})" for kind in ("P", "V", "I"))
    return tuple(labels)


def extension_block() -> str:
    labels = " ".join(added_endpoint_labels())
    return "* visualization-only: missing BVM1-BVM3 SL endpoint P/V/I probes\n" f".print {labels}\n"


def make_deck(parent: Path) -> str:
    source = parent.read_text(encoding="utf-8")
    end = source.rfind("\n.end")
    if end < 0:
        raise RuntimeError(f"{parent}: .end not found")
    block = extension_block()
    if block in source:
        raise RuntimeError(f"{parent}: endpoint extension already present")
    content = source[:end] + block + source[end:]
    if content.replace(block, "", 1) != source:
        raise RuntimeError(f"{parent}: extension changed more than the print block")
    for label in endpoint_labels():
        if label not in content:
            raise RuntimeError(f"{parent}: missing endpoint probe {label}")
    return content


def write_once(path: Path, content: str) -> None:
    if path.exists():
        if path.read_text(encoding="utf-8") == content:
            return
        raise RuntimeError(f"refusing to overwrite immutable endpoint deck: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()

    generated: list[tuple[str, Path, str]] = []
    for state in STATES:
        parent = PARENT_ROOT / state / "deck.cir"
        if not parent.is_file():
            raise RuntimeError(f"missing parent PHASE-B deck: {parent}")
        content = make_deck(parent)
        generated.append((state, parent, content))

    if args.check_only:
        print(f"SL endpoint deck check PASS ({len(generated)} states; no files written)")
        return 0

    for state, _, content in generated:
        write_once(OUTPUT_ROOT / state / "deck.cir", content)
    print(f"generated {len(generated)} SL endpoint decks")
    print(f"added_probe_count={len(added_endpoint_labels())}")
    print(f"parent_deck_sha256={digest(generated[0][1])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
