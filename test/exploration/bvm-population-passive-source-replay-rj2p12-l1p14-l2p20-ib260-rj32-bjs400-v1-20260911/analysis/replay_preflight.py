#!/usr/bin/env python3
"""Verify exact PWL fidelity and the isolated current RJ2=12 receiver."""

from __future__ import annotations

import csv
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
PAIR_RE = re.compile(r"([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)[pP]\s+([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)")
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


def source_pairs(path: Path) -> list[tuple[Decimal, Decimal]]:
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    return [(Decimal(row["time_s"]), Decimal(row["current_A"])) for row in rows]


def deck_pairs(path: Path) -> list[tuple[Decimal, Decimal]]:
    body = path.read_text(encoding="utf-8")
    start = body.index("pwl(") + len("pwl(")
    end = body.index(")", start)
    return [(Decimal(time) * Decimal("1e-12"), Decimal(current)) for time, current in PAIR_RE.findall(body[start:end])]


def active_lines(path: Path) -> list[str]:
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip() and not line.lstrip().startswith(("*", ".", "+"))]


def check_case(passive: str, replay: str, manifest: dict[str, Any]) -> dict[str, Any]:
    deck = EXP / "runs" / replay / "deck.cir"
    snapshot = EXP / "data" / f"{passive}_JSL8_source.csv"
    body = deck.read_text(encoding="utf-8")
    lines = active_lines(deck)
    expected = source_pairs(snapshot)
    actual = deck_pairs(deck)
    failures: list[str] = []
    if len(actual) != len(expected):
        failures.append(f"PWL pair count {len(actual)} != {len(expected)}")
    elif any(left != right for left, right in zip(actual, expected)):
        failures.append("PWL timestamp/current pair mismatch")
    if body.count("I_REPLAY 0 QBIN pwl(") != 1:
        failures.append("replay source/orientation line count mismatch")
    if sum(line == "XBQ1 QBIN QBOUT BQ" for line in lines) != 1:
        failures.append("QB instance count mismatch")
    if sum(line.startswith("XJTL1_") and line.endswith(" jtl") for line in lines) != 6:
        failures.append("six-stage JTL count mismatch")
    if sum(line == "R_TERM JTL6_OUT 0 10" for line in lines) != 1:
        failures.append("termination mismatch")
    if any("BVM" in line or "B_JSL" in line for line in lines):
        failures.append("replay active netlist contains BVM/JSL")
    if any(line.startswith("I_WL") or line.startswith("I_BL") or line.startswith("I_SE") for line in lines):
        failures.append("replay active netlist contains BVM controls")
    if [line for line in body.splitlines() if line.lower().startswith(".tran")] != [".tran 0.1p 200p"]:
        failures.append("tran mismatch")
    for line in (".param L1_VALUE=1.4p", ".param IB_VALUE=260u", ".param RJ1_VALUE=32", ".param RJ2_VALUE=12"):
        if body.count(line) != 1:
            failures.append(f"missing frozen receiver parameter: {line}")
    for include in (".include ../../inputs/BQ_parameterized_bjs400_rj2.cir", ".include ../../inputs/jtl2.cir"):
        if body.count(include) != 1:
            failures.append(f"missing current receiver include: {include}")
    if "BJs 1 2 jjmit area=4" not in (EXP / "inputs/BQ_parameterized_bjs400_rj2.cir").read_text(encoding="utf-8"):
        failures.append("current BJS400 receiver source does not expose area=4")
    return {
        "status": "PASS" if not failures else "FAIL",
        "passive_case": passive,
        "replay_case": replay,
        "source_snapshot_sha256": manifest["source_records"][passive]["snapshot"]["sha256"],
        "source_raw_sha256": manifest["source_records"][passive]["raw"]["sha256"],
        "deck_sha256": sha256(deck),
        "pwl_pairs_expected": len(expected),
        "pwl_pairs_actual": len(actual),
        "exact_timestamp_value_fidelity": not failures and len(actual) == len(expected),
        "orientation": "I_REPLAY 0 QBIN; direct positive orientation; sign_change=false",
        "transformations": [],
        "failures": failures,
    }


def main() -> int:
    execution = json.loads((EXP / "qa/execution_summary.json").read_text(encoding="utf-8"))
    manifest = json.loads((EXP / "analysis/replay_source_manifest.json").read_text(encoding="utf-8"))
    current_head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()
    if execution.get("status") != "PASS" or execution.get("exact_physical_solve_count") != 3:
        raise RuntimeError("passive execution must PASS before replay preflight")
    cases = {replay: check_case(passive, replay, manifest) for passive, replay in CASES}
    failures = [f"{case}: {message}" for case, item in cases.items() for message in item["failures"]]
    record: dict[str, Any] = {
        "schema": "bvm-population-passive-source-replay-preflight-v1",
        "experiment_id": EXP.name,
        "created_at_local": now(),
        "status": "PASS" if not failures else "FAIL",
        "head_at_replay_preflight": current_head,
        "passive_execution_head": execution.get("head"),
        "physical_solve_count_before_replay": 3,
        "authorized_replay_solve_count": 3,
        "source_signal": "I(B_JSL8)",
        "orientation_status": "PASS: direct JSL7-to-QBIN convention; no sign inversion",
        "source_to_replay_transformations": [],
        "cases": cases,
        "common_receiver": {"qb_include": "inputs/BQ_parameterized_bjs400_rj2.cir", "jtl_include": "inputs/jtl2.cir", "RJ2_ohm": 12.0, "L1_pH": 1.4, "L2_pH": 2.0, "RJ1_ohm": 32.0, "IBias_uA": 260.0, "BJS_area": 4, "jtl_stages": 6, "termination_ohm": 10.0, "contains_bvm": False, "contains_jsls": False},
        "failures": failures,
    }
    qa_path = EXP / "qa/replay_fidelity_qa.json"
    if qa_path.exists():
        raise RuntimeError(f"refusing to overwrite replay fidelity QA: {qa_path}")
    qa_path.write_text(json.dumps({"schema": "bvm-population-passive-source-replay-fidelity-qa-v1", "status": record["status"], "created_at_local": record["created_at_local"], "cases": cases, "transformations": [], "raw_immutable": True, "scientific_analysis_performed": False, "failures": failures}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    preflight_path = EXP / "qa/replay_preflight.json"
    if preflight_path.exists():
        raise RuntimeError(f"refusing to overwrite replay preflight: {preflight_path}")
    preflight_path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    markdown = "\n".join([
        "# REPLAY_PREFLIGHT — exact passive JSL8 current replay", "",
        f"- Status: **{record['status']}**",
        f"- HEAD: `{current_head}`",
        "- Source: passive raw `I(B_JSL8)` snapshots; direct exact stored pairs; no waveform transformation.", "",
        "| replay case | source | expected pairs | actual pairs | fidelity | result |",
        "|---|---|---:|---:|---|---|",
        *[f"| `{replay}` | `{item['passive_case']}` | {item['pwl_pairs_expected']} | {item['pwl_pairs_actual']} | `{item['exact_timestamp_value_fidelity']}` | `{item['status']}` |" for replay, item in cases.items()],
        "",
        "All replay decks contain only the current RJ2=12 QB, six-stage JTL, 10 ohm termination and `I_REPLAY 0 QBIN`. No BVM/JSL active element or sign change is present. The replay is ideal forcing and is not a circuit-equivalent source reconstruction.", "",
        "Machine records: `qa/replay_preflight.json`, `qa/replay_fidelity_qa.json`.", "",
    ])
    (EXP / "analysis/REPLAY_PREFLIGHT.md").write_text(markdown, encoding="utf-8")
    print(json.dumps({"status": record["status"], "head": current_head, "replay_cases": list(cases), "physical_solve_count_before_replay": 3, "scientific_analysis_performed": False}, ensure_ascii=False, indent=2))
    return 0 if record["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
