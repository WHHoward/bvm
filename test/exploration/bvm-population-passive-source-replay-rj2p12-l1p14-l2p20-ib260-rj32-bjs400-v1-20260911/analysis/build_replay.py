#!/usr/bin/env python3
"""Freeze passive JSL8 samples and build the three exact replay decks."""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal, localcontext
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
SOURCE_SIGNAL = "I(B_JSL8)"
CASES = (
    ("PASSIVE_N2_0011", "REPLAY_N2_0011_RJ2P12"),
    ("PASSIVE_N3_0111", "REPLAY_N3_0111_RJ2P12"),
    ("PASSIVE_N4_1111", "REPLAY_N4_1111_RJ2P12"),
)


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def write_once(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_text(encoding="utf-8") != text:
            raise RuntimeError(f"refusing to overwrite existing artifact: {path}")
        return
    path.write_text(text, encoding="utf-8")


def read_source(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.reader(stream)
        header = next(reader)
        if header.count("time") != 1 or header.count(SOURCE_SIGNAL) != 1:
            raise RuntimeError(f"source columns are not unique in {path}")
        time_index = header.index("time")
        current_index = header.index(SOURCE_SIGNAL)
        rows = [{"time_s": row[time_index], "current_A": row[current_index]} for row in reader]
    if len(rows) < 2:
        raise RuntimeError(f"too few source rows: {path}")
    times = [Decimal(row["time_s"]) for row in rows]
    values = [Decimal(row["current_A"]) for row in rows]
    if any(not value.is_finite() for value in (*times, *values)):
        raise RuntimeError(f"non-finite source value: {path}")
    if any(right <= left for left, right in zip(times, times[1:])):
        raise RuntimeError(f"source time is not strictly increasing: {path}")
    return header, rows


def fmt_time_ps(time_s: str) -> str:
    with localcontext() as context:
        context.prec = 60
        value = Decimal(time_s) * Decimal("1e12")
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def pwl_lines(rows: list[dict[str, str]]) -> list[str]:
    pairs = [f"{fmt_time_ps(row['time_s'])}p {row['current_A']}" for row in rows]
    lines: list[str] = []
    for start in range(0, len(pairs), 18):
        last = start + 18 >= len(pairs)
        prefix = "I_REPLAY 0 QBIN pwl(" if start == 0 else "+ "
        lines.append(prefix + " ".join(pairs[start : start + 18]) + (")" if last else ""))
    return lines


def replay_probes() -> list[str]:
    lines = [
        ".print V(QBIN) V(QBOUT)",
        ".print I(I_REPLAY)",
        ".print I(LIN|XBQ1) V(LIN|XBQ1) I(L1|XBQ1) V(L1|XBQ1) I(L2|XBQ1) V(L2|XBQ1) I(L3|XBQ1) V(L3|XBQ1)",
        ".print I(RJ1|XBQ1) V(RJ1|XBQ1) I(RJ2|XBQ1) V(RJ2|XBQ1) I(IB|XBQ1) V(IB|XBQ1)",
    ]
    for junction in ("BJS", "BJ1", "BJ2"):
        lines.append(f".print P({junction}|XBQ1) V({junction}|XBQ1) I({junction}|XBQ1)")
    for stage in range(1, 7):
        handle = f"XJTL1_{stage}"
        lines.append(f".print P(B01|{handle}) V(B01|{handle}) I(B01|{handle}) P(B02|{handle}) V(B02|{handle}) I(B02|{handle})")
        lines.append(f".print V(JTL{stage}_OUT)")
    lines.append(".print I(R_TERM)")
    return lines


def replay_deck(passive: str, snapshot: Path, rows: list[dict[str, str]]) -> str:
    lines = [
        f"* GENERATED {passive} EXACT CURRENT REPLAY DECK",
        "* source_class=PASSIVE_CAPTURE_COUNTERFACTUAL",
        f"* source_snapshot={snapshot.relative_to(REPO).as_posix()}",
        f"* source_signal={SOURCE_SIGNAL}; sample_count={len(rows)}",
        "* transformation_registry=[]; timestamps and current values are retained exactly",
        "* orientation=I_REPLAY 0 QBIN; positive source current injects QBIN",
        "",
        ".param L1_VALUE=1.4p",
        ".param IB_VALUE=260u",
        ".param RJ1_VALUE=32",
        ".param RJ2_VALUE=12",
        ".include ../../inputs/jjmit.cir",
        ".include ../../inputs/BQ_parameterized_bjs400_rj2.cir",
        ".include ../../inputs/jtl2.cir",
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
    ]
    lines.extend(pwl_lines(rows))
    lines.extend(["", ".tran 0.1p 200p", ""])
    lines.extend(replay_probes())
    lines.extend([".end", ""])
    return "\n".join(lines)


def snapshot_record(path: Path, rows: list[dict[str, str]], raw: Path) -> dict[str, Any]:
    return {
        "path": path.relative_to(REPO).as_posix(),
        "sha256": sha256(path),
        "bytes": path.stat().st_size,
        "raw_path": raw.relative_to(REPO).as_posix(),
        "raw_sha256": sha256(raw),
        "source_signal": SOURCE_SIGNAL,
        "sample_count": len(rows),
        "time_start_ps": float(Decimal(rows[0]["time_s"]) * Decimal("1e12")),
        "time_end_ps": float(Decimal(rows[-1]["time_s"]) * Decimal("1e12")),
        "transformations": [],
    }


def main() -> int:
    execution = json.loads((EXP / "qa/execution_summary.json").read_text(encoding="utf-8"))
    if execution.get("status") != "PASS" or execution.get("exact_physical_solve_count") != 3 or execution.get("solver_solve_invocations") != 3:
        raise RuntimeError("three passive captures are not a PASS execution prefix")
    source_records: dict[str, Any] = {}
    deck_records: dict[str, Any] = {}
    for passive, replay in CASES:
        raw = EXP / "runs" / passive / "raw.csv"
        if not raw.is_file():
            raise RuntimeError(f"missing passive raw: {raw}")
        _, rows = read_source(raw)
        snapshot = EXP / "data" / f"{passive}_JSL8_source.csv"
        snapshot_text = "time_s,current_A\n" + "\n".join(f"{row['time_s']},{row['current_A']}" for row in rows) + "\n"
        write_once(snapshot, snapshot_text)
        source_records[passive] = {
            "raw": {"path": raw.relative_to(REPO).as_posix(), "sha256": sha256(raw), "bytes": raw.stat().st_size},
            "snapshot": snapshot_record(snapshot, rows, raw),
            "orientation": {"passive_branch": "B_JSL8 JSL_NODE7 0", "closed_loop_reference_branch": "B_JSL8 JSL_NODE7 QBIN", "replay_source": "I_REPLAY 0 QBIN", "positive_direction": "toward downstream endpoint/QBIN", "sign_change": False},
        }
        deck = EXP / "runs" / replay / "deck.cir"
        write_once(deck, replay_deck(passive, snapshot, rows))
        deck_records[replay] = {"path": deck.relative_to(REPO).as_posix(), "sha256": sha256(deck), "bytes": deck.stat().st_size, "source_case": passive, "pwl_pairs": len(rows)}
    manifest = {
        "schema": "bvm-population-passive-source-replay-source-snapshot-manifest-v1",
        "experiment_id": EXP.name,
        "created_at_local": now(),
        "source_signal": SOURCE_SIGNAL,
        "source_records": source_records,
        "replay_decks": deck_records,
        "orientation_qa": "PASS: direct branch orientation; no sign inversion",
        "transformations": [],
        "raw_authority": True,
    }
    write_once(EXP / "analysis/replay_source_manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"status": "PASS", "source_snapshots": list(source_records), "replay_decks": list(deck_records), "physical_solve_count": 3, "scientific_analysis_performed": False}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
