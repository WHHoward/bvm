#!/usr/bin/env python3
"""Create PAPER-SL-Q2 decks by changing only IBIAS in the Q1 replay decks."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
Q1 = ROOT.parent / "paper-sl-q1-20260824"
INPUTS = ROOT / "inputs"
REPLAYS = ROOT / "replay_sources"
BIAS_POINTS = (37.5, 40.0)
CASES = (
    "paper-j1-logical1-read0-control",
    "paper-j0-logical0-read0-control",
    "paper-j0-logical0-read",
    "paper-j1-logical1-read",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def bias_token(value: float) -> str:
    return f"{value:g}u"


def main() -> None:
    INPUTS.mkdir(exist_ok=True)
    REPLAYS.mkdir(exist_ok=True)
    source_manifest: dict[str, str] = {}
    for source in sorted((Q1 / "replay_sources").glob("*.csv")):
        target = REPLAYS / source.name
        if target.exists() and target.read_bytes() != source.read_bytes():
            raise FileExistsError(f"refusing to replace non-identical replay {target}")
        if not target.exists():
            shutil.copyfile(source, target)
        source_manifest[source.name] = sha256(target)

    deck_manifest: dict[str, str] = {}
    needle = "I_IBIAS 0 IBIAS pwl(0p 0 1p 35u 2p 35u 170p 35u)"
    for bias in BIAS_POINTS:
        bias_dir = INPUTS / bias_token(bias).replace(".", "p")
        bias_dir.mkdir(exist_ok=True)
        for dependency in ("bq_cell.cir", "jjmit.cir"):
            dependency_source = INPUTS / dependency
            dependency_target = bias_dir / dependency
            if dependency_target.exists() and dependency_target.read_bytes() != dependency_source.read_bytes():
                raise FileExistsError(f"refusing to replace dependency {dependency_target}")
            if not dependency_target.exists():
                shutil.copyfile(dependency_source, dependency_target)
        replacement = f"I_IBIAS 0 IBIAS pwl(0p 0 1p {bias_token(bias)} 2p {bias_token(bias)} 170p {bias_token(bias)})"
        for case in CASES:
            source = Q1 / "inputs" / f"{case}.cir"
            text = source.read_text()
            if text.count(needle) != 1:
                raise ValueError(f"expected exactly one frozen 35u bias line in {source}")
            generated = text.replace(needle, replacement)
            generated = generated.replace("* PAPER-SL-Q1", "* PAPER-SL-Q2")
            target = bias_dir / f"{case}.cir"
            if target.exists() and target.read_text() != generated:
                raise FileExistsError(f"refusing to replace {target}")
            if not target.exists():
                target.write_text(generated)
            deck_manifest[f"{bias_token(bias)}/{case}.cir"] = sha256(target)

    (REPLAYS / "q1-replay-hashes.json").write_text(json.dumps(source_manifest, indent=2) + "\n")
    (INPUTS / "deck-hashes.json").write_text(json.dumps(deck_manifest, indent=2) + "\n")
    print("built", len(BIAS_POINTS), "bias points and", len(CASES), "cases per point")
    for bias in BIAS_POINTS:
        bias_dir_name = bias_token(bias).replace(".", "p")
        print(bias_dir_name, [f"{bias_dir_name}/{case}.cir" for case in CASES])


if __name__ == "__main__":
    main()
