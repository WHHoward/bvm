#!/usr/bin/env python3
"""Build exact current replays of the canonical 12-JSL source waveforms."""
from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[2]
INPUT = ROOT / "inputs/replay"
SOURCE_MANIFEST = ROOT / "reference/source-manifest.json"


def load_current(path: Path) -> tuple[list[tuple[float, float]], dict[str, float]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        header = next(reader)
        rows = [row for row in reader if row]
    time_i = header.index("time")
    current_i = header.index("I(B_LD1)")
    samples = [(float(row[time_i]) * 1e12, float(row[current_i])) for row in rows]
    if not samples:
        raise ValueError(f"empty source: {path}")
    return samples, {
        "samples": len(samples),
        "start_ps": samples[0][0],
        "end_ps": samples[-1][0],
        "min_A": min(v for _, v in samples),
        "max_A": max(v for _, v in samples),
    }


def fmt(value: float) -> str:
    return f"{value:.17g}"


def repo_rel(path: Path) -> str:
    return path.resolve().relative_to(REPO.resolve()).as_posix()


def write_pwl(samples: list[tuple[float, float]]) -> list[str]:
    pairs = [f"{fmt(t)}p {fmt(v)}" for t, v in samples]
    chunks = [pairs[i:i + 18] for i in range(0, len(pairs), 18)]
    lines = ["I_REPLAY 0 IN pwl(" + " ".join(chunks[0])]
    lines.extend("+ " + " ".join(chunk) for chunk in chunks[1:])
    lines[-1] += ")"
    return lines


def write_deck(path: Path, label: str, source_rel: str, samples: list[tuple[float, float]]) -> None:
    lines = [
        f"* BVM_READ_SEMANTICS_AUDIT_AND_JSL_WIDTH_BRACKET_V1: {label}",
        f"* exact I(B_LD1) replay from {source_rel}; no reshape/hold/scale/resample",
        ".include ../../bq_cell.cir",
        ".include ../../qb-jjmit.cir",
        "XBQ IN OUT IBIAS BQ",
        *write_pwl(samples),
        "R_LOAD OUT 0 10",
        "I_IBIAS 0 IBIAS pwl(0p 0 1p 35u 2p 35u 170p 35u)",
        ".tran 0.0125p 170p",
        ".print P(BJs|XBQ) V(BJs|XBQ) I(BJs|XBQ)",
        ".print P(BJL1|XBQ) V(BJL1|XBQ) I(BJL1|XBQ)",
        ".print P(BJL2|XBQ) V(BJL2|XBQ) I(BJL2|XBQ)",
        ".print I(I_REPLAY) I(I_IBIAS) V(IN) V(OUT) I(R_LOAD)",
        ".print I(Lin|XBQ) I(L0|XBQ) I(L1|XBQ) I(L2|XBQ) I(RB|XBQ) I(RJ1|XBQ) I(RJ2|XBQ)",
        ".end",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_text(encoding="utf-8") != "\n".join(lines) + "\n":
        raise SystemExit(f"refusing to overwrite replay deck: {path}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    old = REPO / "test/exploration/bvm-jsl-read-width-to-qb-sfq-v1-20260824/raw/phase-b/12jsl-12ps/logical1-read/run-01.csv"
    controls = {
        "logical1_no_read_control": REPO / "test/exploration/paper-sl-l0-20260824/raw/logical1-read0-control/run-01.csv",
        "logical0_no_read_control": REPO / "test/exploration/paper-sl-l0-20260824/raw/logical0-read0-control/run-01.csv",
    }
    sources: dict[str, Path] = {"12ps/logical1_read": old}
    for width in (12, 13, 14, 15):
        if width == 12:
            sources["12ps/logical0_read"] = ROOT / "raw/12ps-canonical/logical0-read/run-01.csv"
        else:
            sources[f"{width}ps/logical1_read"] = ROOT / f"raw/{width}ps/logical1-read/run-01.csv"
            sources[f"{width}ps/logical0_read"] = ROOT / f"raw/{width}ps/logical0-read/run-01.csv"
        sources[f"{width}ps/logical1_no_read_control"] = controls["logical1_no_read_control"]
        sources[f"{width}ps/logical0_no_read_control"] = controls["logical0_no_read_control"]
    manifest: dict[str, dict[str, object]] = {}
    for case_id, source in sources.items():
        if not source.exists():
            print(f"skip unavailable source until its physical gate completes: {source}")
            continue
        samples, stats = load_current(source)
        width, role = case_id.split("/", 1)
        snapshot = ROOT / "reference/replay_sources" / f"{width}-{role}.csv"
        snapshot.parent.mkdir(parents=True, exist_ok=True)
        if snapshot.exists() and snapshot.read_text(encoding="utf-8") != "time_ps,I_JSL_A\n" + "\n".join(f"{fmt(t)},{fmt(v)}" for t, v in samples) + "\n":
            raise SystemExit(f"existing snapshot differs: {snapshot}")
        snapshot.write_text("time_ps,I_JSL_A\n" + "\n".join(f"{fmt(t)},{fmt(v)}" for t, v in samples) + "\n", encoding="utf-8")
        deck = INPUT / width / f"{role}.cir"
        write_deck(deck, f"{width} {role}", source.as_posix(), samples)
        manifest[case_id] = {"source_raw": repo_rel(source), "snapshot": repo_rel(snapshot), "deck": repo_rel(deck), **stats}
    SOURCE_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    SOURCE_MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
