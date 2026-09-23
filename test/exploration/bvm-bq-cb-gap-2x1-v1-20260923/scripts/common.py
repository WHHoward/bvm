#!/usr/bin/env python3
"""Shared fixed-protocol helpers for the four-case BVM/BQ/CB/GAP experiment."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
REPO = next(path for path in (ROOT, *ROOT.parents) if (path / ".git").exists())
SOLVER = REPO / "build" / "josim-cli"
PLOTTER = REPO / "scripts" / "josim-plot2.py"
MATRIX = ROOT / "REGRESSION_MATRIX.json"
TEMPLATE = ROOT / "circuits" / "top_template.cir"
PHI0 = 2.067833848e-15
SOURCE_PATHS = {
    "BVM_0923": REPO / "circuits" / "bvm" / "bvm_cell_0923.cir",
    "BQ_0923": REPO / "circuits" / "qb" / "BQ_0923.cir",
    "CB_0923": REPO / "circuits" / "CB" / "CB_0923.cir",
    "sJTL_0923": REPO / "circuits" / "sJTL_0923.cir",
}
SOURCE_SNAPSHOT_NAMES = {
    "BVM_0923": "bvm_cell_0923.cir",
    "BQ_0923": "BQ_0923.cir",
    "CB_0923": "CB_0923.cir",
    "sJTL_0923": "sJTL_0923.cir",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def repo_rel(path: Path) -> str:
    return path.resolve().relative_to(REPO.resolve()).as_posix()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def current_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()


def git_status() -> str:
    return subprocess.check_output(["git", "status", "--short", "--untracked-files=all"], cwd=REPO, text=True)


def solver_identity() -> dict[str, str]:
    version = subprocess.check_output([str(SOLVER), "--version"], cwd=REPO, text=True,
                                      stderr=subprocess.STDOUT)
    return {"path": repo_rel(SOLVER), "sha256": sha256(SOLVER), "version": version.strip()}


def cases() -> list[dict[str, Any]]:
    return list(read_json(MATRIX)["cases"])


def run_dir(run_id: str) -> Path:
    if not re.fullmatch(r"N[012]_(?:00|01|10|11)", run_id):
        raise ValueError(f"invalid registered run ID: {run_id}")
    return ROOT / "runs" / run_id


def probe_signals() -> list[str]:
    signals: list[str] = []

    def add(value: str) -> None:
        if value in signals:
            raise ValueError(f"duplicate required probe: {value}")
        signals.append(value)

    for bvm in (1, 2):
        for jj in ("B_JM1", "B_JM2", "B_JS1", "B_JS2"):
            for q in ("P", "V", "I"):
                add(f"{q}({jj}|XBVM{bvm})")
        for branch in ("L_M1", "L_M2", "L_M3", "L_PM", "L_S1", "L_S2", "L_S3", "L_PSL", "L_SL"):
            for q in ("I", "V"):
                add(f"{q}({branch}|XBVM{bvm})")
        add(f"V(BVM{bvm}_SL)")

    for bq in (1, 2):
        for jj in ("BJ1", "BJ2", "BJ3"):
            for q in ("P", "V", "I"):
                add(f"{q}({jj}|XBQ{bq})")
        for branch in ("Lin", "L1", "L2", "L3"):
            for q in ("I", "V"):
                add(f"{q}({branch}|XBQ{bq})")
        add(f"V(QB{bq}_OUT)")

    for cb in (1, 2):
        for jj in ("BJ1", "BJ2"):
            for q in ("P", "V", "I"):
                add(f"{q}({jj}|XCB{cb})")
        for branch in ("L1", "L2", "L3", "L4"):
            for q in ("I", "V"):
                add(f"{q}({branch}|XCB{cb})")
        add(f"V(CB{cb}_OUT)")

    for acc in (1, 2):
        for q in ("P", "V", "I"):
            add(f"{q}(BJ1|XACC{acc})")
        for branch in ("L1", "L2"):
            for q in ("I", "V"):
                add(f"{q}({branch}|XACC{acc})")
        if acc == 1:
            add("V(ACC1_OUT)")

    for q in ("P", "V", "I"):
        add(f"{q}(BJ1|XGAP1)")
    for branch in ("L1", "L2"):
        for q in ("I", "V"):
            add(f"{q}({branch}|XGAP1)")
    add("V(GAP2_IN)")

    for q in ("P", "V", "I"):
        add(f"{q}(BJ1|XGAP2)")
    for branch in ("L1", "L2"):
        for q in ("I", "V"):
            add(f"{q}({branch}|XGAP2)")
    add("V(FINAL_OUT)")
    add("V(R_TERM)")
    add("I(R_TERM)")

    for source in ("I_WL1", "I_BL1", "I_SE1", "I_WL2", "I_BL2", "I_SE2"):
        add(f"I({source})")
    return signals


def pulse_points(start_ps: int, amplitude: str) -> list[tuple[str, str]]:
    return [(f"{start_ps}p", "0"), (f"{start_ps + 1}p", amplitude),
            (f"{start_ps + 10}p", amplitude), (f"{start_ps + 11}p", "0")]


def source_pwl(source: str, pulses: list[tuple[int, str]]) -> str:
    points: list[tuple[str, str]] = [("0", "0")]
    for start, amplitude in pulses:
        points.extend(pulse_points(start, amplitude))
    points.append(("200p", "0"))
    body = " ".join(f"{time} {value}" for time, value in points)
    return f"{source} 0 {source[2:]} pwl({body})"


def stimulus_text(mask: str) -> str:
    if mask not in {"00", "01", "10", "11"}:
        raise ValueError(f"unsupported mask: {mask}")
    lines = ["* frozen WRITE0 all -> CONTROL all -> WRITE1 all -> masked final READ"]
    for bvm, bit in ((1, mask[0]), (2, mask[1])):
        wl = [(50, "-100u"), (70, "100u"), (90, "100u")]
        bl = [(50, "-100u"), (90, "100u")]
        se = [(70, "100u")]
        if bit == "1":
            wl.append((110, "100u"))
            se.append((110, "100u"))
        lines.extend((source_pwl(f"I_WL{bvm}", wl),
                      source_pwl(f"I_BL{bvm}", bl),
                      source_pwl(f"I_SE{bvm}", se)))
    return "\n".join(lines) + "\n"


def render_deck(stimulus_rel: str) -> str:
    template = TEMPLATE.read_text(encoding="utf-8")
    if template.count("{{PRINTS}}") != 1:
        raise ValueError("top_template.cir must contain exactly one {{PRINTS}} marker")
    prints = "\n".join(f".print {signal}" for signal in probe_signals())
    text = template.replace("{{PRINTS}}", prints).replace('.include stimulus.inc', f'.include {stimulus_rel}')
    if "{{" in text or "}}" in text:
        raise ValueError("unresolved deck template marker")
    return text + ("" if text.endswith("\n") else "\n")


def source_records() -> list[dict[str, str]]:
    records = []
    for role, path in SOURCE_PATHS.items():
        if not path.is_file():
            raise FileNotFoundError(f"missing canonical input {role}: {path}")
        records.append({"role": role, "path": repo_rel(path), "sha256": sha256(path),
                        "snapshot_name": SOURCE_SNAPSHOT_NAMES[role]})
    return records
