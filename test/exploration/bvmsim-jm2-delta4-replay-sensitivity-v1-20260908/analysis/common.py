#!/usr/bin/env python3
"""Shared constants and exact Decimal source/deck helpers for delta4 replay."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import subprocess
from decimal import Decimal, localcontext
from pathlib import Path
from typing import Iterable


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
OLD_EXP = REPO / "test/exploration/bvmsim-jm2-read-count-passive-replay-v1-20260907"
SOLVER = REPO / "build/josim-cli"
HEAD = "2a3e3caeaefd511aa6e555dff18e596bd968f3a2"

SOURCE_SNAPSHOTS = {
    "N3_PASSIVE": OLD_EXP / "data/n3_passive_JSL8_source.csv",
    "N4_PASSIVE": OLD_EXP / "data/n4_passive_JSL8_source.csv",
}
SOURCE_RAWS = {
    "N3_PASSIVE": OLD_EXP / "runs/n3_passive/raw.csv",
    "N4_PASSIVE": OLD_EXP / "runs/n4_passive/raw.csv",
}
CONTROL_RAWS = {
    "N3_REPLAY": OLD_EXP / "runs/n3_replay/raw.csv",
    "N4_REPLAY": OLD_EXP / "runs/n4_replay/raw.csv",
}
MODEL_PATHS = {
    "qb": REPO / "BVMSim/BQ.cir",
    "jtl": REPO / "BVMSim/library_josim/jtl2.cir",
    "jjmit": REPO / "circuits/models/jjmit.cir",
}
EXPECTED_HASHES = {
    "N3_PASSIVE_raw": "f966077641779f90c5043bf7f5d9a4beaba9b13214977cc26cb399e1f6d90273",
    "N4_PASSIVE_raw": "ea9e1e123c80dfc38a0d3b061d8eb68f9ed76133db07490da616cb3bf5b70ba0",
    "N3_PASSIVE_snapshot": "93e41cf604bd373ad63f8fce2eadfd88d735b481fffc2e5e6434b0ff4ce7b586",
    "N4_PASSIVE_snapshot": "f917c119fb9920a167188c45bd31f93895720f71e5ebe35f753181307860e2e6",
    "N3_REPLAY_raw": "555e850fde892da7fd2328d2ac34081b45459ab48e8181a8e95d7cd531e7c225",
    "N4_REPLAY_raw": "5cac782aa9dfa5d467d81e2988e772f1978abfe8313d7896089d5dfa84517b28",
    "qb": "f3dcbf5f9bb3898faf5194b5f7c4771df3fa1ed16150496de4b52cb6f7256dfd",
    "jtl": "ffd31f8eda2a86ca0133342be1ce678831b7237a53911eda046d2bff8454855a",
}

RUNS = (
    "DELTA4_DELAY_3PS",
    "DELTA4_DELAY_6PS",
    "DELTA4_GAIN_1P25",
    "DELTA4_GAIN_1P50",
)
TRANSFORMS = {
    "DELTA4_DELAY_3PS": {"kind": "exact_timestamp_shift", "delay_ps": Decimal("3.0")},
    "DELTA4_DELAY_6PS": {"kind": "exact_timestamp_shift", "delay_ps": Decimal("6.0")},
    "DELTA4_GAIN_1P25": {"kind": "signed_gain", "gain": Decimal("1.25")},
    "DELTA4_GAIN_1P50": {"kind": "signed_gain", "gain": Decimal("1.50")},
}
SOURCE_START_PS = Decimal("0.0")
SOURCE_END_PS = Decimal("199.9")
OUTPUT_END_PS = Decimal("205.9")
TSTOP_PS = Decimal("206.0")
TAIL_WINDOW_PS = (Decimal("190.0"), Decimal("199.9"))
FINAL_READ_RESPONSE_PS = (Decimal("110.0"), Decimal("200.0"))
QB_INTERNAL_CRITICAL_PS = (Decimal("118.0"), Decimal("140.0"))
FOURTH_INTERNAL_SEARCH_PS = (Decimal("120.0"), Decimal("140.0"))
DOWNSTREAM_ZOOM_PS = (Decimal("118.0"), Decimal("180.0"))
TAIL_COMPLETENESS_PS = (Decimal("190.0"), Decimal("206.0"))
SOURCE_RECON_TOL_A = Decimal("1e-21")
QUIET_ABS_LAST_UA_MAX = Decimal("1.0")
QUIET_P2P_UA_MAX = Decimal("1.0")
QUIET_MAX_STEP_UA_MAX = Decimal("0.1")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def now_local() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def current_head() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=REPO, text=True
    ).strip()


def write_once(path: Path, content: str) -> None:
    if path.exists():
        if path.read_text(encoding="utf-8") != content:
            raise RuntimeError(f"refusing to overwrite existing artifact: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def read_snapshot(path: Path) -> list[tuple[str, Decimal, Decimal]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != ["time_s", "current_A"]:
            raise RuntimeError(f"unexpected source snapshot header in {path}: {reader.fieldnames}")
        rows = []
        for row in reader:
            rows.append(
                (
                    row["time_s"],
                    Decimal(row["time_s"]) * Decimal("1e12"),
                    Decimal(row["current_A"]),
                )
            )
    if len(rows) < 2:
        raise RuntimeError(f"source snapshot has too few rows: {path}")
    times = [row[1] for row in rows]
    if any(right <= left for left, right in zip(times, times[1:])):
        raise RuntimeError(f"source snapshot time is not increasing: {path}")
    if any(not item.is_finite() for row in rows for item in row[1:]):
        raise RuntimeError(f"source snapshot has non-finite Decimal values: {path}")
    return rows


def source_grid(rows: list[tuple[str, Decimal, Decimal]]) -> list[Decimal]:
    return [row[1] for row in rows]


def extended_grid(rows: list[tuple[str, Decimal, Decimal]]) -> list[Decimal]:
    output = source_grid(rows)
    value = SOURCE_END_PS + Decimal("0.1")
    while value <= OUTPUT_END_PS:
        output.append(value)
        value += Decimal("0.1")
    return output


def fmt_ps(value: Decimal) -> str:
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def fmt_decimal(value: Decimal) -> str:
    if value == 0:
        return "0.000000e+00"
    with localcontext() as context:
        context.prec = 60
        text = format(value, "E")
    return text.replace("E", "e")


def tail_summary(rows: list[tuple[str, Decimal, Decimal]]) -> dict[str, object]:
    selected = [row for row in rows if TAIL_WINDOW_PS[0] <= row[1] <= TAIL_WINDOW_PS[1]]
    values_ua = [row[2] * Decimal("1e6") for row in selected]
    steps_ua = [
        abs(right - left)
        for left, right in zip(values_ua, values_ua[1:])
    ]
    last = values_ua[-1]
    p2p = max(values_ua) - min(values_ua)
    max_step = max(steps_ua)
    passed = (
        abs(last) <= QUIET_ABS_LAST_UA_MAX
        and p2p <= QUIET_P2P_UA_MAX
        and max_step <= QUIET_MAX_STEP_UA_MAX
    )
    return {
        "window_ps": [str(item) for item in TAIL_WINDOW_PS],
        "sample_count": len(selected),
        "last_value_uA": str(last),
        "p2p_uA": str(p2p),
        "max_adjacent_step_uA": str(max_step),
        "criterion": {
            "abs_last_uA_max": str(QUIET_ABS_LAST_UA_MAX),
            "p2p_uA_max": str(QUIET_P2P_UA_MAX),
            "max_adjacent_step_uA_max": str(QUIET_MAX_STEP_UA_MAX),
        },
        "status": "PASS" if passed else "FAIL",
        "interpretation": "bounded quiet-tail criterion; not exact equilibrium",
    }


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
        lines.append(
            f".print P(B01|{handle}) V(B01|{handle}) I(B01|{handle}) "
            f"P(B02|{handle}) V(B02|{handle}) I(B02|{handle})"
        )
        lines.append(f".print V(JTL{stage}_OUT)")
    lines.append(".print I(R_TERM)")
    return "\n".join(lines)


def pwl_lines(points: Iterable[tuple[Decimal, Decimal]]) -> list[str]:
    pairs = [f"{fmt_ps(time_ps)}p {fmt_decimal(value)}" for time_ps, value in points]
    lines: list[str] = []
    for start in range(0, len(pairs), 18):
        chunk = pairs[start : start + 18]
        prefix = "I_REPLAY 0 QBIN pwl(" if start == 0 else "+ "
        suffix = ")" if start + 18 >= len(pairs) else ""
        lines.append(prefix + " ".join(chunk) + suffix)
    return lines


def replay_deck(
    run_id: str,
    source_path: Path,
    points: list[tuple[Decimal, Decimal]],
    transform_description: str,
) -> str:
    return "\n".join(
        [
            f"* GENERATED {run_id} DECK: delta4 exact-current ideal replay",
            "* source_class=PASSIVE_CAPTURE_MARGINAL_COUNTERFACTUAL",
            f"* source construction: {source_path.relative_to(REPO).as_posix()}",
            "* source signal: I(B_JSL8); N3 background plus registered signed delta4 component",
            f"* transformation: {transform_description}",
            "* exact source-grid timestamp lookup; no interpolation, smoothing, resampling, fitting or pulse reconstruction",
            "* out-of-range or missing exact delta timestamp: zero",
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
            *pwl_lines(points),
            "",
            ".tran 0.1p 206p",
            "",
            replay_probes(),
            ".end",
            "",
        ]
    )


def json_text(data: object) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def finite(value: Decimal) -> bool:
    return value.is_finite() and math.isfinite(float(value))
