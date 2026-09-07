#!/usr/bin/env python3
"""Freeze exact N2-N4 passive JSL8 snapshots and generate replay decks."""

from __future__ import annotations

import csv
import hashlib
import json
from decimal import Decimal, localcontext
from datetime import datetime, timezone
from pathlib import Path


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
SOURCE_SIGNAL = "I(B_JSL8)"
READ_COUNTS = (2, 3, 4)
QB = REPO / "BVMSim/BQ.cir"
JTL = REPO / "BVMSim/library_josim/jtl2.cir"
JJMIT = REPO / "circuits/models/jjmit.cir"
SOLVER = REPO / "build/josim-cli"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def now_local() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def write_once(path: Path, content: str) -> None:
    if path.exists():
        if path.read_text(encoding="utf-8") == content:
            return
        raise RuntimeError(f"refusing to overwrite existing artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def read_source(raw_path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with raw_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        header = next(reader)
        if "time" not in header or SOURCE_SIGNAL not in header:
            raise RuntimeError(f"source columns missing in {raw_path}")
        if header.count(SOURCE_SIGNAL) != 1:
            raise RuntimeError(f"source signal is not a unique column in {raw_path}")
        time_index = header.index("time")
        signal_index = header.index(SOURCE_SIGNAL)
        rows = [{"time_s": row[time_index], "current_A": row[signal_index]} for row in reader]
    if len(rows) < 2:
        raise RuntimeError(f"source has too few rows: {raw_path}")
    times = [Decimal(row["time_s"]) for row in rows]
    currents = [Decimal(row["current_A"]) for row in rows]
    if any(right <= left for left, right in zip(times, times[1:])):
        raise RuntimeError(f"source time is not strictly increasing: {raw_path}")
    if any(not value.is_finite() for value in (*times, *currents)):
        raise RuntimeError(f"source contains non-finite value: {raw_path}")
    return header, rows


def fmt_time_ps(time_s: str) -> str:
    with localcontext() as context:
        context.prec = 50
        value = Decimal(time_s) * Decimal("1e12")
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def pwl_lines(rows: list[dict[str, str]]) -> list[str]:
    pairs = [f"{fmt_time_ps(row['time_s'])}p {row['current_A']}" for row in rows]
    lines: list[str] = []
    for start in range(0, len(pairs), 18):
        chunk = pairs[start : start + 18]
        prefix = "I_REPLAY 0 QBIN pwl(" if start == 0 else "+ "
        suffix = ")" if start + 18 >= len(pairs) else ""
        lines.append(prefix + " ".join(chunk) + suffix)
    return lines


def replay_probes() -> str:
    lines = [
        ".print V(QBIN) V(QBOUT)",
        ".print I(I_REPLAY)",
        ".print I(LIN|XBQ1) V(LIN|XBQ1) I(L1|XBQ1) V(L1|XBQ1) I(L2|XBQ1) V(L2|XBQ1) I(L3|XBQ1) V(L3|XBQ1)",
        ".print I(RJ1|XBQ1) V(RJ1|XBQ1) I(RJ2|XBQ1) V(RJ2|XBQ1) I(IB|XBQ1) V(IB|XBQ1)",
    ]
    for jj in ("BJS", "BJ1", "BJ2"):
        lines.append(f".print P({jj}|XBQ1) V({jj}|XBQ1) I({jj}|XBQ1)")
    for stage in range(1, 7):
        handle = f"XJTL1_{stage}"
        lines.append(f".print P(B01|{handle}) V(B01|{handle}) I(B01|{handle}) P(B02|{handle}) V(B02|{handle}) I(B02|{handle})")
        lines.append(f".print V(JTL{stage}_OUT)")
    lines.append(".print I(R_TERM)")
    return "\n".join(lines)


def replay_deck(read_count: int, source_path: Path, rows: list[dict[str, str]]) -> str:
    return "\n".join(
        [
            f"* GENERATED N{read_count}_REPLAY DECK: exact passive I(JSL8) current replay",
            "* source_class=PASSIVE_CAPTURE_COUNTERFACTUAL",
            f"* source raw snapshot: {source_path.relative_to(REPO).as_posix()}",
            f"* source signal: {SOURCE_SIGNAL}; all {len(rows)} timestamp/current pairs retained",
            "* transformation: none (no interpolation, smoothing, fitting, scaling, shifting, rectification or truncation)",
            "* orientation: I_REPLAY 0 QBIN; positive current injects QBIN in the JSL8 -> QBIN sense",
            "",
            ".include ../../../../../circuits/models/jjmit.cir",
            ".include ../../../../../BVMSim/BQ.cir",
            ".include ../../../../../BVMSim/library_josim/jtl2.cir",
            "",
            "XBQ1 QBIN QBOUT BQ",
            "XJTL1_1 QBOUT JTL1_OUT jtl",
            "XJTL1_2 JTL1_OUT JTL2_OUT jtl",
            "XJTL1_3 JTL2_OUT JTL3_OUT jtl",
            "XJTL1_4 JTL3_OUT JTL4_OUT jtl",
            "XJTL1_5 JTL4_OUT JTL5_OUT jtl",
            "XJTL1_6 JTL5_OUT JTL6_OUT jtl",
            "R_TERM JTL6_OUT 0 10",
            "",
            *pwl_lines(rows),
            "",
            ".tran 0.1p 200p",
            "",
            replay_probes(),
            ".end",
            "",
        ]
    )


def snapshot_record(path: Path, rows: list[dict[str, str]]) -> dict[str, object]:
    return {
        "path": path.relative_to(REPO).as_posix(),
        "sha256": sha256(path),
        "bytes": path.stat().st_size,
        "source_signal": SOURCE_SIGNAL,
        "sample_count": len(rows),
        "time_start_ps": float(Decimal(rows[0]["time_s"]) * Decimal("1e12")),
        "time_end_ps": float(Decimal(rows[-1]["time_s"]) * Decimal("1e12")),
        "transformations": [],
    }


def main() -> int:
    source_records: dict[str, object] = {}
    deck_records: dict[str, object] = {}
    for read_count in READ_COUNTS:
        passive_case = f"n{read_count}_passive"
        replay_case = f"n{read_count}_replay"
        raw_path = EXP / "runs" / passive_case / "raw.csv"
        if not raw_path.is_file():
            raise RuntimeError(f"missing passive raw: {raw_path}")
        _, rows = read_source(raw_path)
        snapshot_path = EXP / "data" / f"n{read_count}_passive_JSL8_source.csv"
        snapshot = "time_s,current_A\n" + "\n".join(f"{row['time_s']},{row['current_A']}" for row in rows) + "\n"
        write_once(snapshot_path, snapshot)
        source_records[f"N{read_count}_PASSIVE"] = {
            "raw": {"path": raw_path.relative_to(REPO).as_posix(), "sha256": sha256(raw_path), "bytes": raw_path.stat().st_size},
            "snapshot": snapshot_record(snapshot_path, rows),
            "orientation": {
                "passive_branch": "B_JSL8 JSL_NODE7 0",
                "replay_source": "I_REPLAY 0 QBIN",
                "positive_direction": "from JSL_NODE7 toward the passive load / into QBIN",
                "sign_change": False,
            },
        }
        deck_path = EXP / "runs" / replay_case / "deck.cir"
        deck = replay_deck(read_count, snapshot_path, rows)
        write_once(deck_path, deck)
        deck_records[f"N{read_count}_REPLAY"] = {
            "path": deck_path.relative_to(REPO).as_posix(),
            "sha256": sha256(deck_path),
            "bytes": deck_path.stat().st_size,
            "pwl_pairs": len(rows),
            "source_case": f"N{read_count}_PASSIVE",
        }
    manifest = {
        "schema": "jm2-read-count-passive-replay-source-snapshot-manifest-v1",
        "experiment_id": EXP.name,
        "created_at_local": now_local(),
        "source_signal": SOURCE_SIGNAL,
        "raw_hashes": {name: record["raw"]["sha256"] for name, record in source_records.items()},
        "sources": source_records,
        "replay_decks": deck_records,
        "orientation_qa": "registered positive JSL8 branch current maps directly to I_REPLAY 0 QBIN; no sign change",
        "transformations": [],
    }
    write_once(EXP / "analysis/replay_source_manifest.json", json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"status": "PASS", "replay_decks": deck_records, "manifest": "analysis/replay_source_manifest.json"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
