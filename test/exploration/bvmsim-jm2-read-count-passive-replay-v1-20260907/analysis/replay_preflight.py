#!/usr/bin/env python3
"""Verify N2-N4 replay topology and exact PWL source fidelity."""

from __future__ import annotations

import csv
import hashlib
import json
import re
import subprocess
from decimal import Decimal
from datetime import datetime, timezone
from pathlib import Path


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
SOURCE_MANIFEST = EXP / "source/source_manifest.json"
REPLAY_MANIFEST = EXP / "analysis/replay_source_manifest.json"
HEAD_AT_SETUP = "217305580f1c9cec17839896730fbe9b1016c837"
READ_COUNTS = (2, 3, 4)
PAIR_RE = re.compile(r"([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)[pP]\s+([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)")


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


def source_pairs(path: Path) -> list[tuple[Decimal, Decimal]]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    return [(Decimal(row["time_s"]), Decimal(row["current_A"])) for row in rows]


def deck_pairs(path: Path) -> list[tuple[Decimal, Decimal]]:
    body = path.read_text(encoding="utf-8")
    start = body.lower().index("pwl(") + len("pwl(")
    end = body.index(")", start)
    matches = PAIR_RE.findall(body[start:end])
    return [(Decimal(time) * Decimal("1e-12"), Decimal(current)) for time, current in matches]


def netlist_lines(path: Path) -> list[str]:
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith(("*", ".", "+"))
    ]


def check_case(read_count: int, source_record: dict[str, object]) -> dict[str, object]:
    replay = f"n{read_count}_replay"
    passive = f"n{read_count}_passive"
    deck = EXP / "runs" / replay / "deck.cir"
    snapshot = EXP / "data" / f"n{read_count}_passive_JSL8_source.csv"
    text = deck.read_text(encoding="utf-8")
    netlist = netlist_lines(deck)
    expected = source_pairs(snapshot)
    actual = deck_pairs(deck)
    failures: list[str] = []
    if len(actual) != len(expected):
        failures.append(f"PWL pair count {len(actual)} != {len(expected)}")
    elif any(left != right for left, right in zip(actual, expected)):
        failures.append("PWL timestamp/current pair mismatch")
    if "I_REPLAY 0 QBIN pwl(" not in text:
        failures.append("replay source orientation line missing")
    if sum(line.startswith("XBQ1 QBIN QBOUT BQ") for line in netlist) != 1:
        failures.append("QB instance count mismatch")
    if sum(line.startswith("XJTL1_") and line.endswith(" jtl") for line in netlist) != 6:
        failures.append("JTL stage count mismatch")
    if sum(line == "R_TERM JTL6_OUT 0 10" for line in netlist) != 1:
        failures.append("10 ohm termination mismatch")
    if any("BVM" in line or "B_JSL" in line or "COMMON_SL" in line for line in netlist):
        failures.append("replay contains passive BVM/JSL element")
    tran = [line for line in text.splitlines() if line.lower().startswith(".tran")]
    if tran != [".tran 0.1p 200p"]:
        failures.append(f"timing line mismatch: {tran}")
    for include in ("BVMSim/BQ.cir", "BVMSim/library_josim/jtl2.cir", "circuits/models/jjmit.cir"):
        if include not in text:
            failures.append(f"missing exact include: {include}")
    return {
        "status": "PASS" if not failures else "FAIL",
        "path": deck.relative_to(REPO).as_posix(),
        "deck_sha256": sha256(deck),
        "source_case": f"N{read_count}_PASSIVE",
        "source_snapshot_sha256": source_record["snapshot"]["sha256"],
        "pwl_pairs_expected": len(expected),
        "pwl_pairs_actual": len(actual),
        "pwl_exact_timestamp_value_fidelity": not failures and len(actual) == len(expected),
        "positive_orientation": "I_REPLAY 0 QBIN; no sign change",
        "transformations": [],
        "failures": failures,
    }


def main() -> int:
    current_head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()
    source_manifest = json.loads(SOURCE_MANIFEST.read_text(encoding="utf-8"))
    replay_manifest = json.loads(REPLAY_MANIFEST.read_text(encoding="utf-8"))
    cases: dict[str, object] = {}
    for read_count in READ_COUNTS:
        key = f"N{read_count}_PASSIVE"
        cases[f"N{read_count}_REPLAY"] = check_case(read_count, replay_manifest["sources"][key])
    failures: list[str] = []
    if current_head != HEAD_AT_SETUP:
        failures.append(f"HEAD changed since preregistration: {current_head}")
    failures.extend(item for case in cases.values() for item in case["failures"])
    record = {
        "schema": "jm2-read-count-passive-replay-replay-preflight-v1",
        "experiment_id": EXP.name,
        "created_at_local": now_local(),
        "status": "PASS" if not failures else "FAIL",
        "head_at_setup": HEAD_AT_SETUP,
        "head_at_replay_preflight": current_head,
        "source_signal": "I(B_JSL8)",
        "source_to_replay_transformations": [],
        "cases": cases,
        "common_receiver": {
            "qb_source": source_manifest["sources"]["qb"],
            "jtl_source": source_manifest["sources"]["jtl"],
            "termination_ohm": 10.0,
            "contains_bvm": False,
            "contains_jsls": False,
        },
        "failures": failures,
    }
    write_once(EXP / "analysis/replay_preflight.json", json.dumps(record, indent=2, ensure_ascii=False) + "\n")
    rows = []
    for read_count in READ_COUNTS:
        item = cases[f"N{read_count}_REPLAY"]
        rows.append(f"| `N{read_count}_REPLAY` | `N{read_count}_PASSIVE` | {item['pwl_pairs_actual']} | `{item['pwl_exact_timestamp_value_fidelity']}` | `{item['status']}` |")
    markdown = f"""# REPLAY_PREFLIGHT — exact read-count passive JSL8 replay

- Status: **{record['status']}**
- Preflight time: `{record['created_at_local']}`
- Source: N2/N3/N4 passive raw `I(B_JSL8)` snapshots; no interpolation or waveform transformation.

| replay case | source | PWL pairs | exact timestamp/value fidelity | result |
|---|---|---:|---|---|
{chr(10).join(rows)}

Each replay deck contains only `I_REPLAY 0 QBIN`, the exact registered QB, the exact six-stage JTL and one 10 ohm termination. It contains no BVM, COMMON_SL or JSL element. Positive source orientation is direct JSL8 -> QBIN; no sign change was applied.

Machine record: `analysis/replay_preflight.json`.
"""
    write_once(EXP / "analysis/REPLAY_PREFLIGHT.md", markdown)
    print(json.dumps({"status": record["status"], "record": "analysis/replay_preflight.json", "failures": failures}, ensure_ascii=False))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
