#!/usr/bin/env python3
"""Generate the one literal P0-current replay deck.

This is a preflight generator, not a simulator.  It consumes every timestamp
and current sample from the already accepted P0 raw and emits one ideal source
with the declared 0 -> IN orientation.  It refuses to overwrite the deck.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[4]
ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "experiment.yaml"
sys.path.insert(0, str(REPO / "scripts"))

from bvmtools.provenance import file_snapshot, sha256_file  # noqa: E402
from bvmtools.raw import read_csv  # noqa: E402


def resolve(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (ROOT / path).resolve()


def compact_netlist_line(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip())


def require_line(path: Path, expected_prefix: tuple[str, ...]) -> str:
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = compact_netlist_line(raw)
        if line.startswith("*") or not line or line.startswith("."):
            continue
        fields = line.split()
        if tuple(fields[: len(expected_prefix)]) == expected_prefix:
            return line
    raise RuntimeError(f"missing netlist line {expected_prefix} in {path}")


def fmt(value: float) -> str:
    return f"{float(value):.17g}"


def pwl_lines(times_s: tuple[float, ...], values_a: tuple[float, ...]) -> list[str]:
    if len(times_s) != len(values_a) or len(times_s) < 2:
        raise RuntimeError("P0 replay needs at least two aligned samples")
    pairs = [f"{fmt(time * 1.0e12)}p {fmt(value)}" for time, value in zip(times_s, values_a)]
    lines = []
    for start in range(0, len(pairs), 18):
        chunk = pairs[start : start + 18]
        prefix = "I_REPLAY 0 IN pwl(" if start == 0 else "+ "
        suffix = ")" if start + 18 >= len(pairs) else ""
        lines.append(prefix + " ".join(chunk) + suffix)
    return lines


def main() -> int:
    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    output = ROOT / config["candidate"]["deck"]
    if output.exists():
        raise RuntimeError(f"refusing to overwrite generated deck: {output}")

    p0_raw = resolve(config["candidate"]["source_raw"])
    p0_deck = resolve(config["references"]["P0"]["deck"])
    qb_snapshot = ROOT / config["references"]["qb_snapshot"]["path"]
    jj_snapshot = ROOT / config["references"]["jj_snapshot"]["path"]
    if sha256_file(p0_raw) != config["references"]["P0"]["raw_sha256"]:
        raise RuntimeError("P0 raw hash differs from frozen preregistration")
    if sha256_file(p0_deck) != config["references"]["P0"]["deck_sha256"]:
        raise RuntimeError("P0 deck hash differs from frozen preregistration")
    if sha256_file(qb_snapshot) != config["references"]["qb_snapshot"]["sha256"]:
        raise RuntimeError("QB snapshot hash differs from frozen preregistration")
    if sha256_file(jj_snapshot) != config["references"]["jj_snapshot"]["sha256"]:
        raise RuntimeError("JJ snapshot hash differs from frozen preregistration")

    p0_line = require_line(p0_deck, ("B_LD12", "njsl11", "IN"))
    lin_line = require_line(qb_snapshot, ("Lin", "IN", "1"))
    trace = read_csv(p0_raw)
    source_signal = config["candidate"]["source_signal"]
    values = trace.column(source_signal, occurrence=config["candidate"]["source_occurrence"])
    if not isinstance(values, tuple) or (values and isinstance(values[0], tuple)):
        raise RuntimeError("source signal selection was not a single exact column")

    output.parent.mkdir(parents=True, exist_ok=True)
    header = [
        "* BVM_QB_P0_CURRENT_REPLAY_FIXTURE_QUICK_V1: literal P0 current replay",
        f"* source raw: {p0_raw.relative_to(REPO).as_posix()}",
        f"* source signal: {source_signal}, occurrence {config['candidate']['source_occurrence']}",
        "* every P0 timestamp/current pair is retained; no fit, scale, hold, resample, or interpolation",
        f"* verified P0 final JSL orientation: {p0_line}",
        f"* verified frozen QB input orientation: {lin_line}",
        ".include jjmit.cir",
        ".include bq_cell.cir",
        "XBQ IN OUT IBIAS BQ",
    ]
    body = pwl_lines(trace.time, tuple(float(item) for item in values))
    tail = [
        "R_LOAD OUT 0 10",
        "I_IBIAS 0 IBIAS pwl(0p 0 1p 35u 2p 35u 170p 35u)",
        ".tran 0.0125p 170p",
        ".print P(BJs|XBQ) V(BJs|XBQ) I(BJs|XBQ)",
        ".print P(BJL1|XBQ) V(BJL1|XBQ) I(BJL1|XBQ)",
        ".print P(BJL2|XBQ) V(BJL2|XBQ) I(BJL2|XBQ)",
        ".print V(IN) V(OUT) I(Lin|XBQ) I(L0|XBQ) I(L1|XBQ) I(L2|XBQ)",
        ".print I(RB|XBQ) I(RJ1|XBQ) I(RJ2|XBQ) I(R_LOAD) I(I_IBIAS)",
        ".print I(I_REPLAY)",
        ".end",
    ]
    output.write_text("\n".join(header + body + tail) + "\n", encoding="utf-8")
    result = {
        "status": "PASS",
        "deck": file_snapshot(output, relative_to=REPO),
        "source_raw": file_snapshot(p0_raw, relative_to=REPO),
        "source_signal": source_signal,
        "source_occurrence": config["candidate"]["source_occurrence"],
        "sample_count": trace.sample_count,
        "time_start_ps": trace.time[0] * 1.0e12,
        "time_end_ps": trace.time[-1] * 1.0e12,
        "pwl_pairs": len(values),
        "orientation": {
            "source": "I_REPLAY 0 IN",
            "positive_direction": "into QB IN",
            "p0_final_jsl": p0_line,
            "qb_lin": lin_line,
        },
        "transformations": [],
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
