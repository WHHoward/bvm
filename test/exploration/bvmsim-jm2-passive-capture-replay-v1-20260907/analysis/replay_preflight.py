#!/usr/bin/env python3
"""Verify replay deck topology and exact PWL source fidelity before replay runs."""

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
HEAD_AT_SETUP = "510cb59ebaa237268980133435aa2ff32468c935"
PAIR_RE = re.compile(r"([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)[pP]\s+([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


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
    start = body.index("pwl(") + len("pwl(")
    end = body.index(")", start)
    matches = PAIR_RE.findall(body[start:end])
    return [(Decimal(time) * Decimal("1e-12"), Decimal(current)) for time, current in matches]


def lines(path: Path) -> list[str]:
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith(("*", ".", "+"))
    ]


def check_case(replay: str, passive: str, source_record: dict[str, object]) -> dict[str, object]:
    deck = EXP / "runs" / replay / "deck.cir"
    snapshot = EXP / "data" / f"{passive}_JSL8_source.csv"
    text = deck.read_text(encoding="utf-8")
    netlist = lines(deck)
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
    if any("BVM" in line or "B_JSL" in line for line in netlist):
        failures.append("replay contains BVM/JSL element")
    tran = [line for line in text.splitlines() if line.lower().startswith(".tran")]
    if tran != [".tran 0.1p 200p"]:
        failures.append(f"timing line mismatch: {tran}")
    return {
        "status": "PASS" if not failures else "FAIL",
        "path": deck.relative_to(REPO).as_posix(),
        "deck_sha256": sha256(deck),
        "source_case": passive.upper(),
        "source_snapshot_sha256": source_record["snapshot"]["sha256"],
        "pwl_pairs_expected": len(expected),
        "pwl_pairs_actual": len(actual),
        "pwl_exact_timestamp_value_fidelity": not failures and len(actual) == len(expected),
        "positive_orientation": "I_REPLAY 0 QBIN; no sign change",
        "failures": failures,
    }


def main() -> int:
    current_head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()
    source_manifest = json.loads(SOURCE_MANIFEST.read_text(encoding="utf-8"))
    replay_manifest = json.loads(REPLAY_MANIFEST.read_text(encoding="utf-8"))
    cases = {
        "replay_single": check_case("replay_single", "single_passive", replay_manifest["sources"]["single_passive"]),
        "replay_array": check_case("replay_array", "array_passive", replay_manifest["sources"]["array_passive"]),
    }
    failures: list[str] = []
    if current_head != HEAD_AT_SETUP:
        failures.append(f"HEAD changed since preregistration: {current_head}")
    if not all("BVMSim/BQ.cir" in (EXP / "runs" / case / "deck.cir").read_text(encoding="utf-8") for case in ("replay_single", "replay_array")):
        failures.append("replay decks do not include the registered QB source")
    if not all("BVMSim/library_josim/jtl2.cir" in (EXP / "runs" / case / "deck.cir").read_text(encoding="utf-8") for case in ("replay_single", "replay_array")):
        failures.append("replay decks do not include the registered JTL source")
    failures.extend(item for case in cases.values() for item in case["failures"])
    record = {
        "schema": "jm2-passive-capture-replay-replay-preflight-v1",
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
    markdown = f"""# REPLAY_PREFLIGHT — exact passive JSL8 current replay\n\n- Status: **{record['status']}**\n- Preflight time: `{record['created_at_local']}`\n- Source: passive raw `I(B_JSL8)` snapshots; no interpolation or waveform transformation.\n\n| replay case | source | PWL pairs | exact timestamp/value fidelity | result |\n|---|---|---:|---|---|\n| `REPLAY_SINGLE` | `SINGLE_PASSIVE` | {cases['replay_single']['pwl_pairs_actual']} | `{cases['replay_single']['pwl_exact_timestamp_value_fidelity']}` | `{cases['replay_single']['status']}` |\n| `REPLAY_ARRAY` | `ARRAY_PASSIVE` | {cases['replay_array']['pwl_pairs_actual']} | `{cases['replay_array']['pwl_exact_timestamp_value_fidelity']}` | `{cases['replay_array']['status']}` |\n\nBoth replay decks contain only `I_REPLAY 0 QBIN`, the exact registered QB, the exact six-stage JTL and one 10 Ω termination. They contain no BVM or JSL. The positive source orientation is the direct `JSL8 -> QBIN` sense; no sign change was applied.\n\nMachine record: `analysis/replay_preflight.json`.\n"""
    write_once(EXP / "analysis/REPLAY_PREFLIGHT.md", markdown)
    print(json.dumps({"status": record["status"], "record": "analysis/replay_preflight.json", "failures": failures}, ensure_ascii=False))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
