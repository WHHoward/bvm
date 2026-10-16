#!/usr/bin/env python3
"""Bounded V9 4x4 multiplier migration and four-case execution entry point.

The historical V9_analysis deck is used only as a hash-pinned topology/source
reference. New runs own copied source closure, generated stimulus, immutable
deck/raw, and task-local mechanical evidence. The legacy diagonal runner is not
rewritten by this module.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

SERIES = Path(__file__).resolve().parents[1]
REPO = SERIES.parents[2]
if str(SERIES / "scripts") not in sys.path:
    sys.path.insert(0, str(SERIES / "scripts"))
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
import diagonal_platform as platform  # noqa: E402

_STIMULUS_SPEC = importlib.util.spec_from_file_location("bvm_stimulus_v9", REPO / "scripts/bvm_stimulus.py")
if _STIMULUS_SPEC is None or _STIMULUS_SPEC.loader is None:
    raise RuntimeError("cannot load the shared bvm_stimulus.py helper")
bvm_stimulus = importlib.util.module_from_spec(_STIMULUS_SPEC)
_STIMULUS_SPEC.loader.exec_module(bvm_stimulus)

RUNS = SERIES / "runs"
PLOTS = SERIES / "plots"
USER_CASE = SERIES / "USER_CASE.env"
MANIFEST = SERIES / "experiment_manifest.json"
ANALYSIS = SERIES / "analysis" / "bvm4x4-v9-multiply-20261016"
HANDOFF = SERIES / "handoff"
V9_REFERENCE = REPO / "test/exploration/sfq_clock_two_read_v1/final_runs/V9_analysis"
REFERENCE_DECK = V9_REFERENCE / "deck.cir"
REFERENCE_STIMULUS = V9_REFERENCE / "stimulus.inc"
REFERENCE_RAW = V9_REFERENCE / "raw.csv"
SOLVER = REPO / "build/josim-cli"
PLOTTER = REPO / "scripts/josim-plot2.py"
PLOTLY = REPO / "assets/vendor/plotly.min.js"
PHI0 = 2.067833848e-15
MAX_RAW_BYTES = 100_000_000
BATCH_ID = "BVM4X4_V9_MULTIPLY_80P68_20261016"
EXPERIMENT_ID = "bvm4x4-v9-multiply-80p68-20261016"
REFERENCE_DECK_SHA256 = "474a254f4511fb46bea6afd36500aa28111323f23f1be66b720170ee297ccb70"
REFERENCE_STIMULUS_SHA256 = "a0152b6ea7dbae508cc4f31855d937f5fed70b087af15baac4f28eed802b8331"
REFERENCE_RAW_SHA256 = "6dddd8cb074b40c1dca694867a03db9bd307ebd23f1263ca6c10a6de662fdf4c"
BVM_SHA256 = "76b7b90b4e58cc45d55adc24d1bc6e626957461a2abe21ca4a33319d58ac6489"

DIAGONALS = {
    "D0": ("R1C4",),
    "D1": ("R1C3", "R2C4"),
    "D2": ("R1C2", "R2C3", "R3C4"),
    "D3": ("R1C1", "R2C2", "R3C3", "R4C4"),
    "D4": ("R2C1", "R3C2", "R4C3"),
    "D5": ("R3C1", "R4C2"),
    "D6": ("R4C1",),
}
CELLS = tuple(f"R{row}C{col}" for row in range(1, 5) for col in range(1, 5))
CHANNELS = tuple(f"D{index}" for index in range(7)) + ("DFF",)
CARRY_SJTL_COUNTS = {1: 1, 2: 1, 3: 5, 4: 2, 5: 1, 6: 1}
RUN_MATRIX = (
    ("V9_A0_B0_80P68", 0, 0, 0, "00000000"),
    ("V9_A1_B1_80P68", 1, 1, 1, "00000001"),
    ("V9_A11_B13_80P68", 11, 13, 143, "10001111"),
    ("V9_A15_B15_80P68", 15, 15, 225, "11100001"),
)

SOURCE_SPECS = (
    ("00_jjmit.cir", "JJMIT", "19862d1fd1f1f44dfa1523848d7d3b5e2594a6c5da8fdd80144b449e5312a336"),
    ("01_bvm_cell_0923.cir", "BVM", BVM_SHA256),
    ("02_BQ_0928.cir", "QB", "82e6f6c7a95856c6d7bcdd28a56c009a815fc77e237a76af08fbebe45eed988a"),
    ("03_sJTL_0923.cir", "SJTL", "3cbc6889f9b4cd6b7764efa4a591f9d4dcdb0b2b86ded1f265dadabda1040688"),
    ("04_CB_0928.cir", "ARRAY_CB_AND_CARRY_CB", "70a6af05acccb7c354799d5b1b7542c86c677970681473f559bbf0f7e4d6d370"),
    ("05_MERGE.cir", "UNUSED_LEGACY_MERGE_INCLUDE", "79b0d219db60ca41a03d732eaac82b436114b02436cf4dc8719e9b25d58940e0"),
    ("06_dcsfq2.cir", "DCSFQ2_CLOCK_SHAPER", "76e9866ef32a73ac8bda2a4698ba1d39dc8e1c83312da168ba0aab8eee5fc280"),
    ("07_jtl2.cir", "JTL2_CLOCK_AND_SUM_CHAIN", "9ec481453c5aa519dec18c07efc2c377b11f3ca0345c6e7971bd6806036455aa"),
    ("08_t1_cell_tunable.cir", "V9_T1_SOURCE_SNAPSHOT", "da7f1c5065081caccbd6cbd698630a9cf94019840e39e3beb0839b99e5e7bcdb"),
    ("09_DFF.cir", "V9_DFF_SOURCE_SNAPSHOT", "e63473b890b67bd968ee9891518e7b4f9b52560cb49e20fa18fa50f03b6bc6f0"),
    ("10_d0_jtl_tunable.cir", "V9_D0_JTL_SOURCE_SNAPSHOT", "b242741e4630a54411db48de649361e8daedfd6a083358d675d2fdf657314039"),
)

V9_KEYS = (
    "V9_PROTOCOL", "V9_A", "V9_B", "V9_READ_COUNT", "V9_WRITE_START_PS",
    "V9_FIRST_READ_PS", "V9_READ_INTERVAL_PS", "V9_CLOCK_PERIOD_PS",
    "V9_SE_CLOCK_DELAY_PS", "V9_WL_WRITE_AMPLITUDE", "V9_BL_WRITE_AMPLITUDE",
    "V9_BL_READ_AMPLITUDE", "V9_SE_READ_AMPLITUDE", "V9_IO_RISE_PS",
    "V9_IO_HOLD_PS", "V9_IO_FALL_PS", "V9_CLOCK_AMPLITUDE",
    "V9_CLOCK_RISE_PS", "V9_CLOCK_HOLD_PS", "V9_CLOCK_FALL_PS",
    "V9_DT_PS", "V9_STOP_PS", "V9_PROBE_PROFILE",
)


class V9ConfigError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".writing")
    if temp.exists():
        raise V9ConfigError(f"stale temporary output exists: {temp}")
    try:
        temp.write_text(value, encoding="utf-8", newline="\n")
        temp.replace(path)
    finally:
        if temp.exists():
            temp.unlink()


def atomic_json(path: Path, value: Any) -> None:
    atomic_text(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def set_if_same(path: Path, value: str) -> None:
    if path.exists():
        if path.read_text(encoding="utf-8") != value:
            raise V9ConfigError(f"refusing to overwrite existing task artifact: {path}")
        return
    atomic_text(path, value)


def load_config(assignments: list[str]) -> dict[str, str]:
    values = platform.parse_env(USER_CASE)
    for assignment in assignments:
        if "=" not in assignment:
            raise V9ConfigError(f"--set expects KEY=VALUE, got {assignment!r}")
        key, value = assignment.split("=", 1)
        if key not in V9_KEYS:
            raise V9ConfigError(f"V9 --set key is not configurable here: {key}")
        values[key] = value
    missing = [key for key in V9_KEYS if key not in values]
    if missing:
        raise V9ConfigError(f"USER_CASE.env lacks V9 settings: {missing}")
    if values["V9_PROTOCOL"] != "V9_SHARED_ROW_SE_BL":
        raise V9ConfigError("V9_PROTOCOL must be V9_SHARED_ROW_SE_BL")
    if values["V9_PROBE_PROFILE"] != "v9_focus":
        raise V9ConfigError("V9_PROBE_PROFILE must be v9_focus for this registered work unit")
    for key in ("V9_A", "V9_B"):
        try:
            item = int(values[key], 10)
        except ValueError as exc:
            raise V9ConfigError(f"{key} must be an integer from 0 to 15") from exc
        if not 0 <= item <= 15:
            raise V9ConfigError(f"{key} must be an integer from 0 to 15")
    try:
        read_count = int(values["V9_READ_COUNT"], 10)
        timing = {key: Decimal(values[key]) for key in (
            "V9_WRITE_START_PS", "V9_FIRST_READ_PS", "V9_READ_INTERVAL_PS",
            "V9_CLOCK_PERIOD_PS", "V9_SE_CLOCK_DELAY_PS", "V9_IO_RISE_PS",
            "V9_IO_HOLD_PS", "V9_IO_FALL_PS", "V9_CLOCK_RISE_PS",
            "V9_CLOCK_HOLD_PS", "V9_CLOCK_FALL_PS", "V9_DT_PS", "V9_STOP_PS")}
    except (ValueError, InvalidOperation) as exc:
        raise V9ConfigError("V9 timing/count settings must be finite numeric values") from exc
    if read_count != 3:
        raise V9ConfigError("this registered matrix requires V9_READ_COUNT=3")
    if any(not value.is_finite() for value in timing.values()):
        raise V9ConfigError("V9 timing values must be finite")
    if any(timing[key] <= 0 for key in (
            "V9_READ_INTERVAL_PS", "V9_CLOCK_PERIOD_PS", "V9_IO_RISE_PS",
            "V9_IO_HOLD_PS", "V9_IO_FALL_PS", "V9_CLOCK_RISE_PS",
            "V9_CLOCK_HOLD_PS", "V9_CLOCK_FALL_PS", "V9_DT_PS", "V9_STOP_PS")):
        raise V9ConfigError("V9 intervals, pulse widths, DT, and STOP must be positive")
    if timing["V9_SE_CLOCK_DELAY_PS"] < 0 or timing["V9_WRITE_START_PS"] < 0 or timing["V9_FIRST_READ_PS"] < 0:
        raise V9ConfigError("V9 write/read/delay times cannot be negative")
    for key in ("V9_WL_WRITE_AMPLITUDE", "V9_BL_WRITE_AMPLITUDE",
                "V9_BL_READ_AMPLITUDE", "V9_SE_READ_AMPLITUDE", "V9_CLOCK_AMPLITUDE"):
        match = re.fullmatch(r"(\d+(?:\.\d*)?|\.\d+)(u|m)", values[key], re.I)
        if not match:
            raise V9ConfigError(f"{key} must be a positive JoSIM current/voltage token")
        scale = 1e-6 if match.group(2).lower() == "u" else 1e-3
        if float(match.group(1)) * scale <= 0:
            raise V9ConfigError(f"{key} must be positive")
    io_duration = sum(timing[key] for key in ("V9_IO_RISE_PS", "V9_IO_HOLD_PS", "V9_IO_FALL_PS"))
    clock_duration = sum(timing[key] for key in ("V9_CLOCK_RISE_PS", "V9_CLOCK_HOLD_PS", "V9_CLOCK_FALL_PS"))
    if timing["V9_READ_INTERVAL_PS"] <= io_duration:
        raise V9ConfigError("V9_READ_INTERVAL_PS is too short for the registered IO pulse")
    if timing["V9_CLOCK_PERIOD_PS"] <= clock_duration:
        raise V9ConfigError("V9_CLOCK_PERIOD_PS is too short for the registered clock pulse")
    if timing["V9_FIRST_READ_PS"] <= timing["V9_WRITE_START_PS"] + sum(
            timing[key] for key in ("V9_IO_RISE_PS", "V9_IO_HOLD_PS", "V9_IO_FALL_PS")):
        raise V9ConfigError("first V9 read must start after WRITE1 has returned to zero")
    if timing["V9_FIRST_READ_PS"] + timing["V9_SE_CLOCK_DELAY_PS"] <= (
            timing["V9_WRITE_START_PS"] + io_duration):
        raise V9ConfigError("first V9 clock PWL must not overlap WRITE1")
    reads = [timing["V9_FIRST_READ_PS"] + i * timing["V9_READ_INTERVAL_PS"] for i in range(read_count)]
    clocks = [timing["V9_FIRST_READ_PS"] + timing["V9_SE_CLOCK_DELAY_PS"] +
              i * timing["V9_CLOCK_PERIOD_PS"] for i in range(read_count)]
    last_end = max(
        reads[-1] + sum(timing[key] for key in ("V9_IO_RISE_PS", "V9_IO_HOLD_PS", "V9_IO_FALL_PS")),
        clocks[-1] + sum(timing[key] for key in ("V9_CLOCK_RISE_PS", "V9_CLOCK_HOLD_PS", "V9_CLOCK_FALL_PS")),
    )
    if timing["V9_STOP_PS"] < last_end + Decimal("1"):
        raise V9ConfigError("V9_STOP_PS must include a post-third-clock observation tail")
    return values


def registered_values_ok(config: dict[str, str]) -> None:
    required = {
        "V9_READ_COUNT": "3", "V9_WRITE_START_PS": "50", "V9_FIRST_READ_PS": "110",
        "V9_READ_INTERVAL_PS": "80", "V9_CLOCK_PERIOD_PS": "80",
        "V9_SE_CLOCK_DELAY_PS": "68", "V9_WL_WRITE_AMPLITUDE": "400u",
        "V9_BL_WRITE_AMPLITUDE": "400u", "V9_BL_READ_AMPLITUDE": "400u",
        "V9_SE_READ_AMPLITUDE": "360u", "V9_IO_RISE_PS": "1", "V9_IO_HOLD_PS": "9",
        "V9_IO_FALL_PS": "1", "V9_CLOCK_AMPLITUDE": "1.2m",
        "V9_CLOCK_RISE_PS": "1", "V9_CLOCK_HOLD_PS": "2", "V9_CLOCK_FALL_PS": "1",
        "V9_DT_PS": "0.01", "V9_STOP_PS": "400",
    }
    mismatches = {key: {"expected": expected, "actual": config.get(key)}
                  for key, expected in required.items() if config.get(key) != expected}
    if mismatches:
        raise V9ConfigError(f"V9 registered 80/68 experiment config mismatch: {mismatches}")


def scenario_config(config: dict[str, str], a: int, b: int) -> dict[str, Any]:
    read_count = int(config["V9_READ_COUNT"])
    first = Decimal(config["V9_FIRST_READ_PS"])
    read_period = Decimal(config["V9_READ_INTERVAL_PS"])
    clock_period = Decimal(config["V9_CLOCK_PERIOD_PS"])
    delay = Decimal(config["V9_SE_CLOCK_DELAY_PS"])
    reads = [first + i * read_period for i in range(read_count)]
    clocks = [first + delay + i * clock_period for i in range(read_count)]
    row_bits = "".join(str((a >> bit) & 1) for bit in range(4))
    col_bits = "".join(str((b >> (3 - bit)) & 1) for bit in range(4))
    product = a * b
    return {
        "case_id": f"V9_A{a}_B{b}_80P68", "a": a, "b": b,
        "expected_product": product, "expected_bits_msb_first": format(product, "08b"),
        "expected_bits_lsb_to_msb": [str((product >> bit) & 1) for bit in range(8)],
        "bit_order": {
            "bits_lsb_to_msb": [*(f"S_D{bit}_OUT" for bit in range(7)), "DFF_O"],
            "binary_msb_first": ["DFF_O", *(f"S_D{bit}_OUT" for bit in range(6, -1, -1))],
        },
        "row_bits_R1_lsb": row_bits, "column_bits_C1_msb": col_bits,
        "selected_se_rows": [f"SE_R{row}" for row in range(1, 5) if row_bits[row - 1] == "1"],
        "selected_bl_columns": [f"BL_C{col}" for col in range(1, 5) if col_bits[col - 1] == "1"],
        "read_times_ps": [float(item) for item in reads],
        "clock_pwl_starts_ps": [float(item) for item in clocks],
        "write_start_ps": float(config["V9_WRITE_START_PS"]),
        "read_interval_ps": float(read_period), "clock_period_ps": float(clock_period),
        "se_clock_delay_ps": float(delay), "dt_ps": float(config["V9_DT_PS"]),
        "stop_ps": float(config["V9_STOP_PS"]), "probe_profile": config["V9_PROBE_PROFILE"],
        "source_amplitudes": {key: config[key] for key in (
            "V9_WL_WRITE_AMPLITUDE", "V9_BL_WRITE_AMPLITUDE", "V9_BL_READ_AMPLITUDE",
            "V9_SE_READ_AMPLITUDE", "V9_CLOCK_AMPLITUDE")},
        "pulse_edges_ps": {
            "io": [config["V9_IO_RISE_PS"], config["V9_IO_HOLD_PS"], config["V9_IO_FALL_PS"]],
            "clock": [config["V9_CLOCK_RISE_PS"], config["V9_CLOCK_HOLD_PS"], config["V9_CLOCK_FALL_PS"]],
        },
    }


def stimulus_parameters(config: dict[str, str], scenario: dict[str, Any]) -> dict[str, Any]:
    return {
        "a": scenario["a"], "b": scenario["b"],
        "write_start_ps": scenario["write_start_ps"],
        "read_times_ps": scenario["read_times_ps"],
        "clock_times_ps": scenario["clock_pwl_starts_ps"], "stop_ps": scenario["stop_ps"],
        "wl_write_amplitude": config["V9_WL_WRITE_AMPLITUDE"],
        "bl_write_amplitude": config["V9_BL_WRITE_AMPLITUDE"],
        "bl_read_amplitude": config["V9_BL_READ_AMPLITUDE"],
        "se_read_amplitude": config["V9_SE_READ_AMPLITUDE"],
        "io_rise_ps": float(config["V9_IO_RISE_PS"]),
        "io_hold_ps": float(config["V9_IO_HOLD_PS"]),
        "io_fall_ps": float(config["V9_IO_FALL_PS"]),
        "clock_amplitude": config["V9_CLOCK_AMPLITUDE"],
        "clock_rise_ps": float(config["V9_CLOCK_RISE_PS"]),
        "clock_hold_ps": float(config["V9_CLOCK_HOLD_PS"]),
        "clock_fall_ps": float(config["V9_CLOCK_FALL_PS"]),
    }


def make_probe_manifest(scenario: dict[str, Any]) -> dict[str, Any]:
    signals: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add(label: str, group: str, unit: str, **meta: Any) -> None:
        if label in seen:
            return
        seen.add(label)
        signals.append({"label": label, "group": group, "unit": unit, **meta})

    for index in range(7):
        add(f"V(S_D{index}_OUT)", "product_output", "V", bit=index)
    add("V(DFF_O)", "product_output", "V", bit=7)
    for row in range(1, 5):
        add(f"I(I_WL_R{row})", "write_excitation", "A", source=f"I_WL_R{row}")
    for col in range(1, 5):
        add(f"I(I_BL_C{col})", "write_read_excitation", "A", source=f"I_BL_C{col}")
    for row in range(1, 5):
        add(f"I(I_SE_R{row})", "read_excitation", "A", source=f"I_SE_R{row}")
    for channel in CHANNELS:
        add(f"V(CLK_{channel})", "actual_clock_input", "V", channel=channel,
            semantics="loaded internal CLK node waveform; peak time is a descriptive proxy, not a threshold-defined edge")
    for index in range(7):
        add(f"V(T1_I_D{index})", "t1_data_input", "V", stage=f"D{index}")
        add(f"V(S_D{index})", "t1_sum_boundary", "V", stage=f"D{index}")
    for index in range(6):
        add(f"V(C_D{index})", "t1_carry_boundary", "V", stage=f"D{index}")
    add("V(DFF_IN)", "dff_data_input", "V", bit=7)

    # Hash-bound cell-to-QB and QB-to-diagonal boundaries for every array cell.
    for cell in CELLS:
        row, col = int(cell[1]), int(cell[3])
        diagonal = next(name for name, members in DIAGONALS.items() if cell in members)
        level = DIAGONALS[diagonal].index(cell) + 1
        add(f"V(SL_{cell})", "bvm_to_qb_boundary", "V", cell=cell)
        add(f"V(MERGE_{diagonal}_L{level})", "qb_to_array_boundary", "V",
            cell=cell, diagonal=diagonal, level=level)

    # Same-JJ P/V for loaded T1 input, SUM, and Carry paths at every stage.
    for index in range(7):
        instance = f"XT1_D{index}"
        for jj, role in (("B_J9", "sum"), ("B_J11", "carry")):
            add(f"P({jj}|{instance})", f"t1_{role}_jj", "rad", instance=instance,
                element=jj, stage=f"D{index}")
            add(f"V({jj}|{instance})", f"t1_{role}_jj", "V", instance=instance,
                element=jj, stage=f"D{index}")

    # Last array CB per diagonal and the physical CB-only Carry branch.
    for diagonal, members in DIAGONALS.items():
        instance = f"XCB_{diagonal}_L{len(members)}"
        add(f"P(BJ1|{instance})", "array_last_cb_jj", "rad", instance=instance, element="BJ1")
        add(f"V(BJ1|{instance})", "array_last_cb_jj", "V", instance=instance, element="BJ1")
    for stage, count in CARRY_SJTL_COUNTS.items():
        instance = f"XCB_CARRY_D{stage}"
        add(f"V(CARRY_CB_IN_D{stage})", "carry_cb_input", "V", stage=f"D{stage}")
        add(f"P(BJ1|{instance})", "carry_cb_jj", "rad", instance=instance, element="BJ1", stage=f"D{stage}")
        add(f"V(BJ1|{instance})", "carry_cb_jj", "V", instance=instance, element="BJ1", stage=f"D{stage}")
        for serial in range(1, count + 1):
            sname = f"XSJTL_CARRY_D{stage}" + (f"_S{serial}" if count > 1 and serial > 1 else "")
            add(f"P(BJ1|{sname})", "carry_sjtl_jj", "rad", instance=sname,
                element="BJ1", stage=f"D{stage}", serial=serial)
            add(f"V(BJ1|{sname})", "carry_sjtl_jj", "V", instance=sname,
                element="BJ1", stage=f"D{stage}", serial=serial)
            if serial < count:
                add(f"V(CARRY_SJTL_MID_D{stage}_S{serial})", "carry_sjtl_boundary", "V",
                    stage=f"D{stage}", serial=serial)

    return {
        "schema": "bvm4x4-v9-probe-manifest-v1", "profile": "v9_focus",
        "signal_count": len(signals), "raw_phase_unit": "P(...) radians",
        "display_phase_unit": "turns=rad/(2*pi), navigation only; not event count",
        "signals": signals, "scientific_interpretation_performed": False,
        "event_classifier": None, "event_count_semantics": "UNKNOWN unless independently reviewable criteria are later authorized",
    }


def source_records() -> list[dict[str, str]]:
    records = []
    for filename, role, expected in SOURCE_SPECS:
        if filename == "01_bvm_cell_0923.cir":
            origin = REPO / "circuits/bvm/bvm_cell_0923_v9_bse.cir"
        else:
            origin = V9_REFERENCE / "sources_frozen" / filename
        if not origin.is_file() or origin.is_symlink():
            raise V9ConfigError(f"required V9 source is missing or symlinked: {origin}")
        actual = sha256(origin)
        if actual != expected:
            raise V9ConfigError(f"V9 source SHA mismatch for {filename}: expected {expected}, got {actual}")
        records.append({"filename": filename, "role": role,
                        "origin": origin.relative_to(REPO).as_posix(),
                        "sha256": actual, "expected_sha256": expected,
                        "source_class": "canonical BVM" if role == "BVM" else "hash-pinned V9 reference snapshot"})
    return records


def _active_sources(stimulus: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in stimulus.splitlines():
        if re.match(r"^(?:I_|V_TRIG_CLK_)", line):
            name = line.split()[0]
            if name in result:
                raise V9ConfigError(f"duplicate stimulus source name: {name}")
            result[name] = line
    return result


def _pwl_value_at(line: str, time_ps: float) -> str:
    match = re.search(r"PWL\((.*)\)", line, re.I)
    if not match:
        raise V9ConfigError(f"stimulus source is not PWL: {line}")
    tokens = match.group(1).split()
    if len(tokens) % 2:
        raise V9ConfigError("malformed PWL token pairs")
    points: list[tuple[float, str]] = []
    for token_time, value in zip(tokens[0::2], tokens[1::2], strict=True):
        number = token_time[:-1] if token_time.lower().endswith("p") else token_time
        points.append((float(number), value))
    current = points[0][1]
    for point_time, point_value in points:
        if point_time > time_ps:
            break
        current = point_value
    return current


def _validate_pulse_encoding(config: dict[str, str], scenario: dict[str, Any], stimulus: str) -> None:
    sources = _active_sources(stimulus)
    if len(sources) != 20:
        raise V9ConfigError(f"V9 stimulus source count must be 20, got {len(sources)}")
    expected_names = {*(f"I_WL_R{r}" for r in range(1, 5)),
                      *(f"I_BL_C{c}" for c in range(1, 5)),
                      *(f"I_SE_R{r}" for r in range(1, 5)),
                      *(f"V_TRIG_CLK_{channel}" for channel in CHANNELS)}
    if set(sources) != expected_names:
        raise V9ConfigError(f"V9 stimulus source set mismatch: {sorted(set(sources) ^ expected_names)}")
    rise = float(config["V9_IO_RISE_PS"])
    write_check = scenario["write_start_ps"] + rise
    for row in range(1, 5):
        if _pwl_value_at(sources[f"I_WL_R{row}"], write_check) != config["V9_WL_WRITE_AMPLITUDE"]:
            raise V9ConfigError(f"V9 WRITE1 WL_R{row} amplitude mismatch")
        for read_time in scenario["read_times_ps"]:
            if _pwl_value_at(sources[f"I_WL_R{row}"], read_time + rise) != "0":
                raise V9ConfigError(f"V9 READ must keep WL_R{row} silent")
    for col in range(1, 5):
        selected = (scenario["b"] >> (4 - col)) & 1
        line = sources[f"I_BL_C{col}"]
        if _pwl_value_at(line, write_check) != config["V9_BL_WRITE_AMPLITUDE"]:
            raise V9ConfigError(f"V9 WRITE1 BL_C{col} amplitude mismatch")
        for read_time in scenario["read_times_ps"]:
            actual = _pwl_value_at(line, read_time + rise)
            expected = config["V9_BL_READ_AMPLITUDE"] if selected else "0"
            if actual != expected:
                raise V9ConfigError(f"V9 READ BL_C{col} selection mismatch: expected {expected}, got {actual}")
    for row in range(1, 5):
        selected = (scenario["a"] >> (row - 1)) & 1
        line = sources[f"I_SE_R{row}"]
        if _pwl_value_at(line, write_check) != "0":
            raise V9ConfigError(f"V9 WRITE1 must keep SE_R{row} silent")
        for read_time in scenario["read_times_ps"]:
            actual = _pwl_value_at(line, read_time + rise)
            expected = config["V9_SE_READ_AMPLITUDE"] if selected else "0"
            if actual != expected:
                raise V9ConfigError(f"V9 READ SE_R{row} selection mismatch: expected {expected}, got {actual}")
    clock_rise = float(config["V9_CLOCK_RISE_PS"])
    for index, channel in enumerate(CHANNELS):
        line = sources[f"V_TRIG_CLK_{channel}"]
        for clock_time in scenario["clock_pwl_starts_ps"]:
            if _pwl_value_at(line, clock_time + clock_rise) != config["V9_CLOCK_AMPLITUDE"]:
                raise V9ConfigError(f"V9 clock PWL level mismatch for {channel}")


def render_deck(reference_text: str, config: dict[str, str], probes: dict[str, Any]) -> str:
    lines: list[str] = []
    tran_count = 0
    end_count = 0
    for line in reference_text.splitlines():
        if re.match(r"^\s*\.print\b", line, re.I):
            continue
        if re.match(r"^\s*\.tran\b", line, re.I):
            tran_count += 1
            lines.append(f".tran {config['V9_DT_PS']}p {config['V9_STOP_PS']}p")
            continue
        if line.strip().lower() == ".end":
            end_count += 1
            lines.extend(f".print {item['label']}" for item in probes["signals"])
        lines.append(line)
    if tran_count != 1 or end_count != 1:
        raise V9ConfigError(f"V9 template requires exactly one .tran and .end; got {tran_count}/{end_count}")
    return "\n".join(lines) + "\n"


def _deck_without_probe_and_time(deck: str) -> list[str]:
    return [line for line in deck.splitlines()
            if not re.match(r"^\s*\.print\b", line, re.I)
            and not re.match(r"^\s*\.tran\b", line, re.I)]


def _subckt_elements(text: str, name: str) -> set[str]:
    inside = False
    found: set[str] = set()
    matches = 0
    for line in text.splitlines():
        fields = line.strip().split()
        if len(fields) >= 2 and fields[0].lower() == ".subckt" and fields[1].lower() == name.lower():
            inside = True
            matches += 1
            continue
        if inside and fields and fields[0].lower() == ".ends":
            inside = False
            continue
        if inside and fields and not fields[0].startswith("*"):
            found.add(fields[0].upper())
    if matches != 1:
        raise V9ConfigError(f"source closure must contain exactly one .subckt {name}; found {matches}")
    return found


def _subckt_pins(text: str, name: str) -> tuple[str, ...]:
    records = [tuple(line.strip().split()[2:]) for line in text.splitlines()
               if len(line.strip().split()) >= 2 and line.strip().split()[0].lower() == ".subckt"
               and line.strip().split()[1].lower() == name.lower()]
    if len(records) != 1:
        raise V9ConfigError(f"source closure must define one .subckt {name}")
    return records[0]


def validate_rendered(config: dict[str, str], scenarios: list[dict[str, Any]],
                      rendered: list[dict[str, Any]], reference_text: str,
                      source_recs: list[dict[str, str]]) -> dict[str, Any]:
    if len(rendered) != len(scenarios):
        raise V9ConfigError("rendered case count differs from registered scenario count")
    if _deck_without_probe_and_time(rendered[0]["deck"]) != _deck_without_probe_and_time(reference_text):
        raise V9ConfigError("generated V9 deck changed circuit/include topology beyond probes and .tran")
    source_by_name = {item["filename"]: item for item in source_recs}
    source_texts = {name: (REPO / item["origin"]).read_text(encoding="utf-8")
                    for name, item in source_by_name.items()}
    reference_includes = re.findall(r"^\s*\.include\s+sources_frozen/([^\s]+)", reference_text,
                                    flags=re.M | re.I)
    if set(reference_includes) != set(source_by_name) or len(reference_includes) != len(source_by_name):
        raise V9ConfigError("V9 deck include list does not match the pinned 11-file source closure")
    if _subckt_pins(source_texts["01_bvm_cell_0923.cir"], "BVM") != ("WL", "BL", "SE", "SL"):
        raise V9ConfigError("V9 BVM source ports are not WL, BL, SE, SL")
    bvm_text = source_texts["01_bvm_cell_0923.cir"]
    if not re.search(r"^\s*B_SE\s+SE\s+SE_IN\s+jjmit", bvm_text, re.M | re.I):
        raise V9ConfigError("V9 BVM source does not contain active B_SE")
    if not re.search(r"^\s*R_BSE\s+SE\s+SE_IN\s+", bvm_text, re.M | re.I):
        raise V9ConfigError("V9 BVM source does not contain active R_BSE")
    if _subckt_pins(source_texts["08_t1_cell_tunable.cir"], "T1") != (
            "I", "CLK", "S", "C", "N_BIAS1", "N_BIAS2", "N_BIAS3"):
        raise V9ConfigError("V9 T1 port order differs from the reference")

    base_lines = rendered[0]["deck"].splitlines()
    x_lines = [line for line in base_lines if line.startswith("X")]
    by_name = {line.split()[0]: line.split() for line in x_lines}
    if len(by_name) != len(x_lines):
        raise V9ConfigError("duplicate top-level instance names in V9 deck")
    if len([line for line in x_lines if line.startswith("XBVM_")]) != 16:
        raise V9ConfigError("V9 deck must instantiate exactly 16 BVMs")
    if len([line for line in x_lines if line.startswith("XBQ_")]) != 16:
        raise V9ConfigError("V9 deck must instantiate exactly 16 QBs")
    if len([line for line in x_lines if line.startswith("XT1_D")]) != 7:
        raise V9ConfigError("V9 deck must instantiate exactly seven T1 cells")
    if sum(line.startswith("XDFF ") for line in x_lines) != 1:
        raise V9ConfigError("V9 deck must instantiate exactly one DFF")
    if len([line for line in x_lines if re.match(r"^XCB_D[0-6]_L", line)]) != 16:
        raise V9ConfigError("V9 array must retain 16 one-input CB stages")
    if len([line for line in x_lines if re.match(r"^XCB_CARRY_D[1-6] ", line)]) != 6:
        raise V9ConfigError("V9 carry path must retain six canonical CB stages")
    if len([line for line in x_lines if line.startswith("XSJTL_CARRY_D")]) != sum(CARRY_SJTL_COUNTS.values()):
        raise V9ConfigError("V9 carry sJTL instance count differs from D1..D6 = 1,1,5,2,1,1")
    for diagonal, cells in DIAGONALS.items():
        for level, cell in enumerate(cells, start=1):
            row, col = int(cell[1]), int(cell[3])
            expected = [f"XBVM_{cell}", f"WL_R{row}", f"BL_C{col}", f"SE_R{row}", f"SL_{cell}", "BVM"]
            if by_name.get(f"XBVM_{cell}") != expected:
                raise V9ConfigError(f"V9 BVM port map mismatch for {cell}: {by_name.get(f'XBVM_{cell}')}")
            expected_qb = [f"XBQ_{cell}", f"SL_{cell}", f"MERGE_{diagonal}_L{level}", "BQ"]
            if by_name.get(f"XBQ_{cell}") != expected_qb:
                raise V9ConfigError(f"V9 QB diagonal map mismatch for {cell}")
    for index in range(1, 7):
        for serial in range(1, CARRY_SJTL_COUNTS[index] + 1):
            name = f"XSJTL_CARRY_D{index}" + (f"_S{serial}" if CARRY_SJTL_COUNTS[index] > 1 and serial > 1 else "")
            if name not in by_name or by_name[name][-1] != "sJTL":
                raise V9ConfigError(f"V9 carry sJTL instance missing or wrong model: {name}")
        if by_name[f"XCB_CARRY_D{index}"][-1] != "CB":
            raise V9ConfigError(f"V9 carry CB model mismatch at D{index}")
        if by_name[f"XT1_D{index}"][1] != f"T1_I_D{index}":
            raise V9ConfigError(f"V9 T1 input node mismatch at D{index}")
    if by_name["XT1_D6"][4] != "DFF_IN":
        raise V9ConfigError("V9 final T1 carry must connect directly to DFF_IN")
    if any(line.startswith("R_TERM_D") for line in base_lines):
        raise V9ConfigError("V9 T1 chain must not restore DOUT terminal loads")
    if any(line.startswith("XMERGE_D") for line in x_lines):
        raise V9ConfigError("V9 carry path uses CB-only direct shared input nodes, not THmitll_MERGE")
    for diagonal in range(7):
        if sum(line.startswith(f"XJTL_S_D{diagonal}_") for line in x_lines) != 2:
            raise V9ConfigError(f"V9 Sum output D{diagonal} must have two JTL2 stages")
    for channel in CHANNELS:
        if not any(line.startswith(f"XDCSFQ_{channel} ") for line in x_lines):
            raise V9ConfigError(f"V9 clock path lacks DCSFQ2 for {channel}")
        if not any(line.startswith(f"XJTL_IN_{channel} ") for line in x_lines):
            raise V9ConfigError(f"V9 clock path lacks JTL2 for {channel}")

    expected_probes = {item["label"] for item in rendered[0]["probes"]["signals"]}
    actual_prints = [line.split(None, 1)[1] for line in base_lines if re.match(r"^\.print\s+", line)]
    if len(actual_prints) != len(set(actual_prints)) or set(actual_prints) != expected_probes:
        raise V9ConfigError("V9 print/probe manifest mismatch or duplicate .print labels")
    instances = {name: fields[-1] for name, fields in by_name.items()}
    internal_elements = {
        "BVM": _subckt_elements(source_texts["01_bvm_cell_0923.cir"], "BVM"),
        "BQ": _subckt_elements(source_texts["02_BQ_0928.cir"], "BQ"),
        "sJTL": _subckt_elements(source_texts["03_sJTL_0923.cir"], "sJTL"),
        "CB": _subckt_elements(source_texts["04_CB_0928.cir"], "CB"),
        "T1": _subckt_elements(source_texts["08_t1_cell_tunable.cir"], "T1"),
        "THmitll_DFF": _subckt_elements(source_texts["09_DFF.cir"], "THmitll_DFF"),
        "D0_JTL": _subckt_elements(source_texts["10_d0_jtl_tunable.cir"], "D0_JTL"),
    }
    subckt_pins: dict[str, tuple[str, ...]] = {}
    for text in source_texts.values():
        for line in text.splitlines():
            fields = line.strip().split()
            if len(fields) >= 2 and fields[0].lower() == ".subckt":
                subckt_pins[fields[1]] = tuple(fields[2:])
    top_nodes: set[str] = set()
    top_elements: set[str] = set()
    for line in base_lines:
        fields = line.strip().split()
        if not fields or fields[0].startswith(("*", ".")):
            continue
        name = fields[0]
        top_elements.add(name.upper())
        if name.upper().startswith("X"):
            pins = subckt_pins.get(fields[-1])
            if pins is None:
                raise V9ConfigError(f"top-level instance references unknown source model: {line}")
            top_nodes.update(fields[1:1 + len(pins)])
        elif len(fields) >= 3:
            top_nodes.update(fields[1:3])
    stimulus_elements = set(_active_sources(rendered[0]["stimulus_text"]))
    for item in rendered[0]["probes"]["signals"]:
        match = re.fullmatch(r"[PVI]\(([^|)]+)\|([^|)]+)\)", item["label"])
        if match:
            element, instance = match.groups()
            model = instances.get(instance)
            if model is None or element.upper() not in internal_elements.get(model, set()):
                raise V9ConfigError(f"unresolved hierarchical probe: {item['label']}")
        else:
            voltage_match = re.fullmatch(r"V\(([^()]+)\)", item["label"])
            if voltage_match and voltage_match.group(1) not in top_nodes:
                raise V9ConfigError(f"unresolved top-level node probe: {item['label']}")
            source_match = re.fullmatch(r"I\(([^()]+)\)", item["label"])
            if source_match and source_match.group(1) not in top_elements | stimulus_elements:
                raise V9ConfigError(f"unresolved stimulus current probe: {item['label']}")

    if len(scenarios) == 4 and [item["expected_product"] for item in scenarios] != [0, 1, 143, 225]:
        raise V9ConfigError("registered product oracle differs from 0,1,143,225")
    return {
        "schema": "bvm4x4-v9-static-qa-v1", "status": "PASS",
        "parent_head": platform._git_output("rev-parse", "HEAD"),
        "solver_path": SOLVER.relative_to(REPO).as_posix(),
        "solver_binary_sha256": sha256(SOLVER) if SOLVER.is_file() else None,
        "solver_version_query_performed": False,
        "classic_plotter_sha256": sha256(PLOTTER) if PLOTTER.is_file() else None,
        "plotly_asset_sha256": sha256(PLOTLY) if PLOTLY.is_file() else None,
        "reference_deck_sha256": sha256(REFERENCE_DECK),
        "reference_stimulus_sha256": sha256(REFERENCE_STIMULUS),
        "reference_raw_sha256_recorded_not_used_as_oracle": sha256(REFERENCE_RAW),
        "reference_historical_manifests_used_as_authority": False,
        "reference_source_manifest_note": "Current V9_analysis RUN/SOURCE/PACKAGE manifests are stale relative to current deck/stimulus/source bytes; this work unit hashes current files directly.",
        "source_closure": source_recs,
        "bvm_count": 16, "qb_count": 16, "wl_source_count": 4, "bl_source_count": 4,
        "shared_row_se_source_count": 4, "clock_source_count": 8,
        "total_signal_source_count": 20, "array_cb_count": 16, "carry_cb_count": 6,
        "carry_sjtl_count_by_stage": {f"D{k}": CARRY_SJTL_COUNTS[k] for k in range(1, 7)},
        "t1_count": 7, "sum_jtl2_count": 14, "clock_dcsfq2_count": 8,
        "clock_jtl2_count": 8, "dff_count": 1,
        "v9_template_topology_equal_except_registered_print_and_tran": True,
        "all_256_operand_mappings_validated": True,
        "registered_run_matrix": scenarios,
        "probe_count": rendered[0]["probes"]["signal_count"],
        "raw_estimate_bytes": rendered[0]["raw_estimate_bytes"],
        "raw_estimate_guard_status": "PASS" if rendered[0]["raw_estimate_bytes"] < MAX_RAW_BYTES else "FAIL",
        "legacy_platform_mode_untouched": True,
        "solver_invoked": False, "physical_solve_count": 0,
        "scientific_interpretation_performed": False,
    }


def _source_origin(filename: str) -> Path:
    if filename == "01_bvm_cell_0923.cir":
        return REPO / "circuits/bvm/bvm_cell_0923_v9_bse.cir"
    return V9_REFERENCE / "sources_frozen" / filename


def _check_reference_files() -> tuple[str, str, list[dict[str, str]]]:
    checks = ((REFERENCE_DECK, REFERENCE_DECK_SHA256),
              (REFERENCE_STIMULUS, REFERENCE_STIMULUS_SHA256),
              (REFERENCE_RAW, REFERENCE_RAW_SHA256))
    for path, expected in checks:
        if not path.is_file() or path.is_symlink() or sha256(path) != expected:
            raise V9ConfigError(f"V9 reference file missing, symlinked, or changed: {path}")
    sources = source_records()
    if len(sources) != 11:
        raise V9ConfigError("V9 reference source closure must contain 11 files")
    return sha256(REFERENCE_DECK), sha256(REFERENCE_STIMULUS), sources


def _expected_sources_from_reference(stimulus: str, config: dict[str, str],
                                     scenario: dict[str, Any]) -> bool:
    reference = _active_sources(REFERENCE_STIMULUS.read_text(encoding="utf-8"))
    candidate = _active_sources(stimulus)
    return candidate == reference


def _build_cases(config: dict[str, str], batch: bool) -> list[dict[str, Any]]:
    if batch:
        rows = []
        for label, a, b, product, bits in RUN_MATRIX:
            scenario = scenario_config(config, a, b)
            if scenario["expected_product"] != product or scenario["expected_bits_msb_first"] != bits:
                raise V9ConfigError(f"registered arithmetic mapping failed for {label}")
            rows.append(scenario)
        return rows
    return [scenario_config(config, int(config["V9_A"]), int(config["V9_B"]))]


def _rounds_for_stimulus(config: dict[str, str], scenario: dict[str, Any]) -> dict[str, Any]:
    return {"read_count": int(config["V9_READ_COUNT"]),
            "read_times_ps": scenario["read_times_ps"],
            "clock_pwl_starts_ps": scenario["clock_pwl_starts_ps"],
            "round_windows_ps_half_open": [
                [scenario["read_times_ps"][i],
                 scenario["read_times_ps"][i + 1] if i + 1 < len(scenario["read_times_ps"])
                 else scenario["stop_ps"]]
                for i in range(len(scenario["read_times_ps"]))],
            "clock_search_windows_ps_half_open": [
                [scenario["clock_pwl_starts_ps"][i],
                 scenario["clock_pwl_starts_ps"][i + 1] if i + 1 < len(scenario["clock_pwl_starts_ps"])
                 else scenario["stop_ps"]]
                for i in range(len(scenario["clock_pwl_starts_ps"]))],
            "boundary_rule": "[start,end); stored raw timestamps only; no interpolation"}


def _raw_size_estimate(probe_count: int, config: dict[str, str]) -> dict[str, Any]:
    # Reference raw is used only to estimate CSV storage, never as a result oracle.
    with REFERENCE_RAW.open("rb") as stream:
        sample_count = sum(1 for _ in stream) - 1
    with REFERENCE_RAW.open("rb") as stream:
        header_count = len(stream.readline().rstrip(b"\r\n").split(b","))
    if sample_count <= 0 or header_count <= 1:
        raise V9ConfigError("cannot estimate raw size from the reference CSV header/row count")
    stop_ps = float(config["V9_STOP_PS"])
    expected_samples = int(round(stop_ps / float(config["V9_DT_PS"]))) + 1
    raw_estimate = math.ceil(REFERENCE_RAW.stat().st_size *
                             ((probe_count + 1) / header_count) *
                             (expected_samples / sample_count) * 1.05)
    return {"reference_bytes": REFERENCE_RAW.stat().st_size,
            "reference_header_columns_including_time": header_count,
            "reference_sample_count": sample_count,
            "projected_sample_count": expected_samples,
            "projected_signal_count": probe_count,
            "safety_factor": 1.05,
            "estimated_raw_bytes": raw_estimate,
            "guard_bytes": MAX_RAW_BYTES,
            "guard_status": "PASS" if raw_estimate < MAX_RAW_BYTES else "FAIL",
            "reference_raw_scientific_use": "none; storage-size calibration only"}


def _case_render(config: dict[str, str], scenario: dict[str, Any], reference_text: str,
                 source_recs: list[dict[str, str]], estimate: dict[str, Any]) -> dict[str, Any]:
    stimulus_text, drivers = bvm_stimulus.make_v9_stimulus(stimulus_parameters(config, scenario))
    probes = make_probe_manifest(scenario)
    deck = render_deck(reference_text, config, probes)
    _validate_pulse_encoding(config, scenario, stimulus_text)
    return {"scenario": scenario, "stimulus_text": stimulus_text, "drivers": drivers,
            "probes": probes, "deck": deck, "source_records": source_recs,
            "raw_estimate_bytes": estimate["estimated_raw_bytes"]}


def _static_256_mapping_audit(config: dict[str, str], reference_text: str,
                              source_recs: list[dict[str, str]], estimate: dict[str, Any]) -> dict[str, Any]:
    products = 0
    first_example = None
    for a in range(16):
        for b in range(16):
            scenario = scenario_config(config, a, b)
            generated = _case_render(config, scenario, reference_text, source_recs, estimate)
            _validate_pulse_encoding(config, scenario, generated["stimulus_text"])
            products += 1
            if (a, b) == (11, 13):
                first_example = {
                    "A": a, "B": b, "product": 143,
                    "row_bits_R1_lsb": scenario["row_bits_R1_lsb"],
                    "column_bits_C1_msb": scenario["column_bits_C1_msb"],
                    "selected_se_rows": scenario["selected_se_rows"],
                    "selected_bl_columns": scenario["selected_bl_columns"],
                }
    if products != 256 or first_example != {
            "A": 11, "B": 13, "product": 143,
            "row_bits_R1_lsb": "1101", "column_bits_C1_msb": "1101",
            "selected_se_rows": ["SE_R1", "SE_R2", "SE_R4"],
            "selected_bl_columns": ["BL_C1", "BL_C2", "BL_C4"]}:
        raise V9ConfigError("V9 256-case mapping audit failed or 11x13 mapping is incorrect")
    return {"status": "PASS", "case_count": products, "example_11x13": first_example,
            "physical_solve_count": 0}


def _run_ids(scenarios: list[dict[str, Any]]) -> list[str]:
    first = platform.next_run_number()
    if first + len(scenarios) - 1 > 999:
        raise V9ConfigError("three-digit A run ID space exhausted")
    ids = [f"A{first + i:03d}_{scenario['case_id']}" for i, scenario in enumerate(scenarios)]
    occupied = platform._allocated_run_ids()
    conflicts = [run_id for run_id in ids if run_id in occupied or (RUNS / run_id).exists()]
    if conflicts:
        raise V9ConfigError(f"V9 run IDs already reserved; refusing overwrite: {conflicts}")
    return ids


def _case_payloads(config: dict[str, str], scenarios: list[dict[str, Any]],
                   reference_text: str, sources: list[dict[str, str]]) -> list[dict[str, Any]]:
    estimate = _raw_size_estimate(make_probe_manifest(scenarios[0])["signal_count"], config)
    payloads = [_case_render(config, scenario, reference_text, sources, estimate)
                for scenario in scenarios]
    for item in payloads:
        item["raw_estimate"] = estimate
    return payloads


def _write_task_definition(config: dict[str, str], scenarios: list[dict[str, Any]],
                           run_ids: list[str], static_qa: dict[str, Any]) -> None:
    spec = {
        "experiment_id": EXPERIMENT_ID, "experiment_risk_level": "NORMAL",
        "study_phase": "EXPLORATORY",
        "question": "Under the fixed V9 shared-row-SE/shared-column-BL topology, preserve raw evidence for four registered products and three 80 ps reads; describe loaded output and internal clock waveforms without asserting an unfrozen SFQ decoder or multiplication Gate.",
        "source_class": "V9 reference topology with hash-pinned local source closure",
        "authority_boundary": {
            "evidence": ["immutable raw", "same-JJ P/V arithmetic", "actual-grid terminal voltage integrals", "stage-boundary waveforms"],
            "not_proven": ["SFQ event count where no frozen classifier applies", "system multiplication PASS/Gate", "convergence", "hardware behavior", "mechanism"]},
        "run_set": [{"run_id": run_id, "condition": scenario["case_id"],
                     "A": scenario["a"], "B": scenario["b"],
                     "expected_product": scenario["expected_product"],
                     "expected_bits_msb_first": scenario["expected_bits_msb_first"],
                     "reads": scenario["read_times_ps"],
                     "clock_pwl_starts": scenario["clock_pwl_starts_ps"]}
                    for run_id, scenario in zip(run_ids, scenarios, strict=True)],
        "changed": ["V9 shared row-SE/column-BL stimuli are generated from USER_CASE.env", "V9 DCSFQ2/JTL2 clock path and reference carry topology are used"],
        "frozen": ["BVM/QB/sJTL/CB/T1/DFF/JJ source SHA", "V9 circuit topology", "device parameters", "A/B batch matrix", "three-read timing", "solver timestep"],
        "topology": "16 BVM + 16 QB, four shared WL rows, four shared BL columns, four shared SE rows; seven diagonal chains; V9 direct carry CB branches; seven T1; final DFF",
        "stimulus": {key: config[key] for key in V9_KEYS if key not in {"V9_PROTOCOL", "V9_A", "V9_B", "V9_PROBE_PROFILE"}},
        "time_windows": {scenario["case_id"]: _rounds_for_stimulus(config, scenario) for scenario in scenarios},
        "probe_manifest_sha256_by_case": {scenario["case_id"]: hashlib.sha256(
            (json.dumps(item["probes"], ensure_ascii=False, indent=2) + "\n").encode()).hexdigest()
            for scenario, item in zip(scenarios, _case_payloads(config, scenarios,
                                                                REFERENCE_DECK.read_text(encoding="utf-8"),
                                                                source_records()), strict=True)},
        "expected_qa": ["static exact-topology check", "20 source names and 256 mapping checks", "raw SHA/time/probe integrity", "actual-grid output integral and same-JJ P/V arithmetic", "classic responsive plot QA", "package member/SHA QA"],
        "interpretation_ceiling": "Mechanical observations only. event_count and observed_bits are UNKNOWN unless an independently authorized classifier later supports them; arithmetic_status and timing_status default INCONCLUSIVE.",
        "prohibited_followups": ["256-case sweep", "parameter/timing search", "timestep convergence", "topology changes", "extra physical solves"],
        "scientific_review_authorization": "NOT_GRANTED",
        "package": {"zip": f"handoff/{SERIES.name}_delta_V9_MUL_80P68_20261016.zip", "commit_by_default": True, "html_included": False},
        "human_gate": {"state": "AWAITING_SCIENTIFIC_REVIEW", "automatic_next_experiment": False},
        "static_qa_sha256": sha256(ANALYSIS / "STATIC_QA.json"),
        "physical_solve_count_authorized": 4,
        "scientific_interpretation_performed": False,
    }
    # The JSON-compatible subset is valid YAML and avoids an extra YAML dependency.
    experiment_path = ANALYSIS / "experiment.yaml"
    experiment_text = json.dumps(spec, ensure_ascii=False, indent=2) + "\n"
    if experiment_path.exists() and experiment_path.read_text(encoding="utf-8") != experiment_text:
        if any((RUNS / run_id).exists() for run_id in run_ids):
            raise V9ConfigError("refusing to revise experiment.yaml after any registered run directory exists")
        atomic_text(experiment_path, experiment_text)
    elif not experiment_path.exists():
        atomic_text(experiment_path, experiment_text)


def _preflight_text(config: dict[str, str], scenarios: list[dict[str, Any]], run_ids: list[str],
                    source_recs: list[dict[str, str]], static_qa: dict[str, Any],
                    payloads: list[dict[str, Any]],
                    solver_info: dict[str, Any] | None = None,
                    revision_note: str | None = None) -> str:
    head = platform._git_output("rev-parse", "HEAD")
    source_lines = "\n".join(f"- `{item['origin']}` SHA-256 `{item['sha256']}` ({item['role']})"
                              for item in source_recs)
    probe_lines = "\n".join(f"- `{item['label']}` — {item['unit']} — {item['group']}"
                             for item in payloads[0]["probes"]["signals"])
    run_lines = "\n".join(
        f"- `{run_id}`: A={scenario['a']}, B={scenario['b']}, expected={scenario['expected_product']} ({scenario['expected_bits_msb_first']}); reads={scenario['read_times_ps']} ps; clock PWL={scenario['clock_pwl_starts_ps']} ps; deck SHA `{sha256_from_text(payload['deck'])}`, stimulus SHA `{sha256_from_text(payload['stimulus_text'])}`"
        for run_id, scenario, payload in zip(run_ids, scenarios, payloads, strict=True))
    windows = _rounds_for_stimulus(config, scenarios[0])
    solver_line = (f"`{SOLVER}`; version `{solver_info['version'].replace(chr(10), '; ')}`; binary SHA-256 `{solver_info['sha256']}`"
                   if solver_info else
                   f"`{SOLVER}`; executable SHA-256 `{sha256(SOLVER)}`; version not queried during dry-run")
    preflight_state = "LOCKED_BEFORE_PHYSICAL_SOLVE" if solver_info else "DRAFT_NOT_EXECUTABLE"
    revision_line = f"\n- Preflight revision note: {revision_note}." if revision_note else ""
    return f"""# PREFLIGHT — {EXPERIMENT_ID}

This experiment is governed by docs/EXPERIMENT_CONTRACT.md.

Preflight state: `{preflight_state}`.
{revision_line}

- `experiment_risk_level`: NORMAL; `study_phase`: EXPLORATORY.
- Parent HEAD: `{head}` (branch `master`; local/remote alignment was verified before implementation).
- Static gate: `{static_qa['status']}`; physical solves completed before execution: 0; authorized matrix size: 4.
- V9 topology reference deck SHA-256: `{REFERENCE_DECK_SHA256}`. Current V9 historical manifests/package metadata are stale and are not used as run provenance.
- V9 historical stimulus SHA-256: `{REFERENCE_STIMULUS_SHA256}`; current historical raw SHA-256 recorded only to protect/reference its identity: `{REFERENCE_RAW_SHA256}`. The existing V9 raw is not an output oracle and is never modified.
- BVM source SHA-256: `{BVM_SHA256}`.
- Solver: {solver_line}.
- USER_CASE.env SHA-256: `{sha256(USER_CASE)}`; V9 runner SHA-256: `{sha256(Path(__file__).resolve())}`; shared stimulus builder SHA-256: `{sha256(REPO / 'scripts/bvm_stimulus.py')}`.
- Classic plotter/Plotly asset SHA-256: `{sha256(PLOTTER)}` / `{sha256(PLOTLY)}`.
- DT/STOP: `{config['V9_DT_PS']} / {config['V9_STOP_PS']} ps`. Shared bus source setpoints are not per-cell branch-current claims.
- Source-stimulus semantics: one WRITE1 initializes all cells at {config['V9_WRITE_START_PS']} ps, WL/BL active and SE quiet; each of three reads has all WL quiet, selected BL columns and selected SE rows active; 8 independent clock PWLs use the matching 68 ps configured offset.
- Bit order: LSB→MSB `[S_D0_OUT,…,S_D6_OUT,DFF_O]`; displayed binary is MSB-first `[DFF_O,S_D6_OUT,…,S_D0_OUT]`.
- Exact candidate attribution windows: `{json.dumps(windows['round_windows_ps_half_open'])} ps`, half-open; read drive windows are `[read_start, read_start+11 ps)`; clock waveform search windows are `{json.dumps(windows['clock_search_windows_ps_half_open'])} ps`, half-open.
- Timing arithmetic is stored-grid peak-time navigation only: positive/negative extrema and peak-time differences are descriptive, not threshold-defined event edges or setup margins.
- Event classifier: NONE. `event_count_per_bit=UNKNOWN`, `observed_bits=UNKNOWN`, and arithmetic/timing status default to INCONCLUSIVE; terminal area/Φ0 is navigation arithmetic, not an event count.
- Interpolation, resampling, smoothing, scaling, time shifting, and raw mutation are prohibited. Integrals use actual stored timestamps and registered half-open windows.
- Raw storage estimate: {payloads[0]['raw_estimate']['estimated_raw_bytes']} bytes including 5% headroom; limit `{MAX_RAW_BYTES}` bytes; estimate PASS is required before launch.
- Output paths: `runs/{run_ids[0]}…runs/{run_ids[-1]}/`; every run gets its own deck, stimulus, copied source closure, logs, raw, QA, provenance, and standalone classic plots.

## Hash-pinned V9 source closure

{source_lines}

## Exact authorized run matrix

{run_lines}

## Frozen probes

{probe_lines}

## Limits

- Exactly four JoSIM solves; stop at the first solver or artifact hard failure.
- No 256-case physical sweep, no parameter/timing changes, no retries after physical/model failure, and no follow-up.
- Scientific interpretation is NOT PERFORMED; awaiting user + ChatGPT raw review.
"""


def sha256_from_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _case_names(config: dict[str, str], scenarios: list[dict[str, Any]], first: int) -> list[str]:
    return [f"A{first + index:03d}_{scenario['case_id']}" for index, scenario in enumerate(scenarios)]


def _write_reference_inputs(source_recs: list[dict[str, str]]) -> None:
    record = {
        "schema": "bvm4x4-v9-reference-inputs-v1",
        "reference_role": "static historical topology/source reference only",
        "current_files": {
            "deck": {"path": REFERENCE_DECK.relative_to(REPO).as_posix(), "sha256": sha256(REFERENCE_DECK)},
            "stimulus": {"path": REFERENCE_STIMULUS.relative_to(REPO).as_posix(), "sha256": sha256(REFERENCE_STIMULUS)},
            "raw": {"path": REFERENCE_RAW.relative_to(REPO).as_posix(), "sha256": sha256(REFERENCE_RAW),
                    "use": "identity preservation only; not a data oracle"},
        },
        "historical_run_source_manifest_used": False,
        "historical_run_manifest_used": False,
        "historical_package_qa_used": False,
        "note": "Current V9_analysis deck/stimulus/source bytes do not match all historic manifest/package hashes; actual bytes are independently SHA-bound here. No historical reference file is modified.",
        "sources": source_recs,
    }
    atomic_json(ANALYSIS / "REFERENCE_INPUTS.json", record)


def _static_preflight(assignments: list[str], *, batch: bool) -> tuple[dict[str, str], list[dict[str, Any]], list[str], list[dict[str, Any]], dict[str, Any]]:
    config = load_config(assignments)
    if batch:
        registered_values_ok(config)
    _check_reference_files()
    sources = source_records()
    reference_text = REFERENCE_DECK.read_text(encoding="utf-8")
    scenarios = _build_cases(config, batch)
    run_ids = _run_ids(scenarios)
    estimate = _raw_size_estimate(make_probe_manifest(scenarios[0])["signal_count"], config)
    payloads = [_case_render(config, scenario, reference_text, sources, estimate) for scenario in scenarios]
    if batch and not _expected_sources_from_reference(
            _case_render(config, scenario_config(config, 11, 13), reference_text, sources, estimate)["stimulus_text"],
            config, scenario_config(config, 11, 13)):
        raise V9ConfigError("generated 11x13 active PWL sources differ from the current V9 reference")
    if batch:
        if any(payload["deck"] != payloads[0]["deck"] for payload in payloads):
            raise V9ConfigError("all four registered cases must share the exact circuit/probe deck")
        if len(payloads) != 4:
            raise V9ConfigError("registered V9 batch must contain exactly four cases")
    mapping = _static_256_mapping_audit(config, reference_text, sources, estimate)
    static_qa = validate_rendered(config, scenarios, payloads, reference_text, sources)
    static_qa["mapping_audit"] = mapping
    static_qa["raw_estimate"] = estimate
    if estimate["guard_status"] != "PASS":
        static_qa["status"] = "FAIL"
        raise V9ConfigError(f"V9 raw estimate exceeds {MAX_RAW_BYTES} byte guard: {estimate['estimated_raw_bytes']}")
    if any((RUNS / run_id).exists() for run_id in run_ids):
        raise V9ConfigError("one or more planned V9 run directories already exist; no overwrite is allowed")
    for payload in payloads:
        payload["static_qa"] = static_qa
    return config, scenarios, run_ids, payloads, static_qa


def _static_report(static_qa: dict[str, Any], run_ids: list[str]) -> str:
    return f"""# BVM4X4 V9 Static QA

Status: **{static_qa['status']}**; `solver_invoked=false`; `physical_solve_count=0`.

- Parent HEAD: `{static_qa['parent_head']}`
- V9 template topology equivalence (excluding only `.print`/`.tran`): `{static_qa['v9_template_topology_equal_except_registered_print_and_tran']}`
- BVM/QB: {static_qa['bvm_count']}/{static_qa['qb_count']}; shared buses: WL={static_qa['wl_source_count']}, BL={static_qa['bl_source_count']}, row-SE={static_qa['shared_row_se_source_count']}; clock sources={static_qa['clock_source_count']}; total stimulus sources={static_qa['total_signal_source_count']}.
- Physical chain: array CB={static_qa['array_cb_count']}; carry CB={static_qa['carry_cb_count']}; carry sJTL counts `{json.dumps(static_qa['carry_sjtl_count_by_stage'], sort_keys=True)}`; T1={static_qa['t1_count']}; Sum JTL2={static_qa['sum_jtl2_count']}; DCSFQ2/JTL2 clock branches={static_qa['clock_dcsfq2_count']}/{static_qa['clock_jtl2_count']}; DFF={static_qa['dff_count']}.
- V9 256 input encodings: `{static_qa['mapping_audit']['status']}` ({static_qa['mapping_audit']['case_count']} configs generated; no solves); 11×13 mapping: SE `{static_qa['mapping_audit']['example_11x13']['selected_se_rows']}`, BL `{static_qa['mapping_audit']['example_11x13']['selected_bl_columns']}`.
- Focus probes: {static_qa['probe_count']}; conservative raw estimate including 5% margin: {static_qa['raw_estimate_bytes']} bytes / {static_qa['raw_estimate_guard_status']} against {MAX_RAW_BYTES}.
- New run IDs: `{', '.join(run_ids)}`; all verified absent before launch.
- V9 historical RUN/SOURCE/PACKAGE manifests are explicitly not treated as current hash authority.
- Protected V9 reference raw/deck/stimulus SHA checks: PASS; no reference files changed.
- Legacy runner source/profile behavior is not replaced; this task uses explicit `--v9-multiply-batch` mode.
"""


def _write_preflight_artifacts(config: dict[str, str], scenarios: list[dict[str, Any]],
                               run_ids: list[str], payloads: list[dict[str, Any]],
                               static_qa: dict[str, Any], sources: list[dict[str, str]]) -> None:
    ANALYSIS.mkdir(parents=True, exist_ok=True)
    _write_reference_inputs(sources)
    atomic_json(ANALYSIS / "STATIC_QA.json", static_qa)
    atomic_text(ANALYSIS / "BVM4X4_V9_STATIC_QA.md", _static_report(static_qa, run_ids))
    exp_path = ANALYSIS / "experiment.yaml"
    if not exp_path.exists():
        _write_task_definition(config, scenarios, run_ids, static_qa)
    preflight = _preflight_text(config, scenarios, run_ids, sources, static_qa, payloads)
    preflight_path = ANALYSIS / "PREFLIGHT.md"
    if preflight_path.exists():
        old = preflight_path.read_text(encoding="utf-8")
        if "Preflight state: `DRAFT_NOT_EXECUTABLE`." not in old:
            raise V9ConfigError("refusing to replace a non-draft locked PREFLIGHT.md")
        if old != preflight:
            revision_path = ANALYSIS / "PREFLIGHT_REVISIONS.json"
            revisions = json.loads(revision_path.read_text(encoding="utf-8")) if revision_path.is_file() else {
                "schema": "bvm4x4-v9-preflight-revisions-v1", "revisions": []}
            revisions["revisions"].append({"status": "DRAFT_SUPERSEDED_BEFORE_ANY_SOLVE",
                                             "sha256": sha256(preflight_path),
                                             "reason": "static implementation/config/probe draft refreshed before final solver identity lock",
                                             "physical_solve_count_completed": 0})
            atomic_json(revision_path, revisions)
            atomic_text(preflight_path, preflight)
    else:
        atomic_text(preflight_path, preflight)
    probe_registry = {scenario["case_id"]: payload["probes"]
                      for scenario, payload in zip(scenarios, payloads, strict=True)}
    atomic_json(ANALYSIS / "PROBE_MANIFESTS.json", {
        "schema": "bvm4x4-v9-probe-registry-v1", "probe_manifests_by_case": probe_registry,
        "scientific_interpretation_performed": False})


def _print_dry_run(config: dict[str, str], scenarios: list[dict[str, Any]], run_ids: list[str],
                   static_qa: dict[str, Any]) -> int:
    print("V9 STATIC DRY RUN PASS — solver_invoked=false; physical_solve_count=0")
    print(f"Mode: {config['V9_PROTOCOL']} | topology source: current hash-pinned V9_analysis deck")
    print(f"Runs: {', '.join(run_ids)}")
    for run_id, scenario in zip(run_ids, scenarios, strict=True):
        print(f"  {run_id}: A={scenario['a']} × B={scenario['b']} -> {scenario['expected_product']} ({scenario['expected_bits_msb_first']})")
    print(f"Reads={scenarios[0]['read_times_ps']} ps | CLK PWL={scenarios[0]['clock_pwl_starts_ps']} ps | DT={scenarios[0]['dt_ps']} ps | STOP={scenarios[0]['stop_ps']} ps")
    print(f"Sources: 4 WL + 4 BL + 4 shared-row SE + 8 CLK = {static_qa['total_signal_source_count']}")
    print(f"Probes={static_qa['probe_count']} | raw_estimate={static_qa['raw_estimate_bytes']} bytes | QA={static_qa['status']}")
    print("Output classification: no frozen event classifier; count/bit labels remain UNKNOWN/INCONCLUSIVE.")
    print("No run directory or experiment_manifest change was made.")
    return 0


def _write_env_snapshot(path: Path, config: dict[str, str]) -> None:
    text = "".join(f"{key}={config[key]}\n" for key in V9_KEYS)
    atomic_text(path, text)


def _copy_source_closure(run_dir: Path, sources: list[dict[str, str]]) -> list[dict[str, Any]]:
    frozen = run_dir / "sources_frozen"
    frozen.mkdir(parents=True, exist_ok=False)
    copied = []
    for record in sources:
        origin = REPO / record["origin"]
        if sha256(origin) != record["sha256"]:
            raise V9ConfigError(f"source changed after static preflight: {record['origin']}")
        target = frozen / record["filename"]
        shutil.copyfile(origin, target)
        digest = sha256(target)
        if digest != record["sha256"]:
            raise V9ConfigError(f"copied source SHA mismatch: {record['filename']}")
        copied.append({**record, "snapshot": f"sources_frozen/{record['filename']}",
                       "snapshot_sha256": digest})
    return copied


def _write_case_artifacts(run_dir: Path, config: dict[str, str], payload: dict[str, Any],
                          run_id: str, batch_id: str, source_recs: list[dict[str, str]],
                          solver_info: dict[str, Any]) -> dict[str, str]:
    source_snapshots = _copy_source_closure(run_dir, source_recs)
    scenario = payload["scenario"]
    atomic_text(run_dir / "deck.cir", payload["deck"])
    atomic_text(run_dir / "stimulus.inc", payload["stimulus_text"])
    atomic_text(run_dir / "USER_CASE.snapshot.env", USER_CASE.read_text(encoding="utf-8"))
    _write_env_snapshot(run_dir / "V9_CONFIG.snapshot.env", config)
    atomic_json(run_dir / "CASE_CONFIG.json", {**scenario, "run_id": run_id,
                                                "batch_id": batch_id,
                                                "protocol": config["V9_PROTOCOL"],
                                                "scientific_interpretation_performed": False})
    atomic_json(run_dir / "source_manifest.json", {
        "schema": "bvm4x4-v9-source-manifest-v1", "parent_head": solver_info["parent_head"],
        "reference_deck_path": REFERENCE_DECK.relative_to(REPO).as_posix(),
        "reference_deck_sha256": sha256(REFERENCE_DECK),
        "sources": source_snapshots,
        "source_closure_is_run_local": True,
        "scientific_interpretation_performed": False})
    atomic_json(run_dir / "stimulus_manifest.json", {
        "schema": "bvm4x4-v9-stimulus-manifest-v1", "scenario": scenario,
        "sources": payload["drivers"],
        "source_count": len(payload["drivers"]),
        "source_classes": {"WL": 4, "BL": 4, "shared_row_SE": 4, "CLK": 8},
        "read_semantics": "all WL quiet; selected BL columns and selected SE rows active",
        "clock_path": "PWL -> 2 ohm -> DCSFQ2 -> JTL2 -> T1/DFF",
        "scientific_interpretation_performed": False})
    atomic_json(run_dir / "probe_manifest.json", payload["probes"])
    atomic_json(run_dir / "topology_manifest.json", {
        "schema": "bvm4x4-v9-topology-manifest-v1", "reference_deck_sha256": sha256(REFERENCE_DECK),
        "rows": 4, "columns": 4,
        "cell_map": [{"cell": cell,
                      "bvm_instance": f"XBVM_{cell}", "qb_instance": f"XBQ_{cell}",
                      "wl_node": f"WL_R{cell[1]}", "bl_node": f"BL_C{cell[3]}",
                      "se_node": f"SE_R{cell[1]}", "sl_node": f"SL_{cell}"}
                     for cell in CELLS],
        "diagonals": {name: list(cells) for name, cells in DIAGONALS.items()},
        "carry_sjtl_count_by_stage": {f"D{stage}": count for stage, count in CARRY_SJTL_COUNTS.items()},
        "t1_count": 7, "dff_count": 1, "sum_jtl2_per_stage": 2,
        "clock_path": "PWL -> 2 ohm -> DCSFQ2 -> JTL2 -> T1/DFF",
        "array_last_cb_and_carry_cb_share_each_T1_input_directly": True,
        "scientific_interpretation_performed": False})
    atomic_json(run_dir / "static_qa.json", payload["case_static_qa"])
    return {"deck_sha256": sha256(run_dir / "deck.cir"),
            "stimulus_sha256": sha256(run_dir / "stimulus.inc"),
            "stimulus_manifest_sha256": sha256(run_dir / "stimulus_manifest.json"),
            "source_manifest_sha256": sha256(run_dir / "source_manifest.json"),
            "probe_manifest_sha256": sha256(run_dir / "probe_manifest.json"),
            "topology_manifest_sha256": sha256(run_dir / "topology_manifest.json")}


def _array_area(values: Any, times: list[float], indices: list[int]) -> float:
    return platform._trapz(times, values, indices)


def _positive_negative_area(values: Any, times: list[float], indices: list[int]) -> tuple[float, float]:
    positive = [max(0.0, float(value)) for value in values]
    negative = [min(0.0, float(value)) for value in values]
    return platform._trapz(times, positive, indices), platform._trapz(times, negative, indices)


def analyze_v9_raw(run_dir: Path, scenario: dict[str, Any], probes: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    raw = run_dir / "raw.csv"
    before = sha256(raw)
    required = {item["label"] for item in probes["signals"]}
    times, columns, header = platform.read_raw(raw, required, exact_header=True)
    after = sha256(raw)
    if before != after:
        raise V9ConfigError("immutable raw SHA changed while reading")
    if len(times) < 2 or any(not math.isfinite(value) for value in times):
        raise V9ConfigError("raw time column is empty or non-finite")
    dt = [right - left for left, right in zip(times, times[1:])]
    if any(step <= 0 or not math.isfinite(step) for step in dt):
        raise V9ConfigError("raw time is not strictly monotonic")
    time_ps = [value * 1e12 for value in times]
    stop = scenario["stop_ps"]
    round_windows = _rounds_for_stimulus_from_scenario(scenario)

    def indices(start_ps: float, end_ps: float) -> list[int]:
        return [i for i, time in enumerate(time_ps) if start_ps <= time < end_ps]

    windows: dict[str, Any] = {}
    window_indices: dict[str, list[int]] = {}
    for name, interval in round_windows.items():
        selected = indices(interval[0], interval[1])
        if len(selected) < 2:
            raise V9ConfigError(f"raw has fewer than two stored samples in registered window {name}")
        window_indices[name] = selected
        windows[name] = {"start_ps": interval[0], "end_ps": interval[1],
                         "boundary_rule": "[start,end)", "sample_count": len(selected),
                         "first_stored_ps": time_ps[selected[0]],
                         "last_stored_ps": time_ps[selected[-1]],
                         "integration": "trapezoid on actual stored timestamps; no interpolation"}

    output_rows: list[dict[str, Any]] = []
    waveform_metrics: list[dict[str, Any]] = []
    for bit, signal in enumerate([*(f"V(S_D{i}_OUT)" for i in range(7)), "V(DFF_O)"]):
        for read_index, window_name in enumerate(("ROUND_1", "ROUND_2", "ROUND_3"), start=1):
            ids = window_indices[window_name]
            values = columns[signal]
            pos_idx = max(ids, key=lambda idx: values[idx])
            neg_idx = min(ids, key=lambda idx: values[idx])
            signed_area = _array_area(values, times, ids)
            pos_area, neg_area = _positive_negative_area(values, times, ids)
            morphology = platform._voltage_lobe_candidates(times, values, ids)
            first, last = ids[0], ids[-1]
            if bit < 7:
                t1_jj = f"P(B_J9|XT1_D{bit})"
                t1_v = f"V(B_J9|XT1_D{bit})"
                phase = platform._unwrap(columns[t1_jj])
                delta_rad = phase[last] - phase[first]
                jj_area = _array_area(columns[t1_v], times, ids)
                same_jj_status = "DERIVED_SAME_JJ_PV"
            else:
                # The preregistered focus set has the DFF input/output and clock,
                # but intentionally no DFF-internal P/V. Do not infer bit7 phase.
                t1_jj = None
                t1_v = None
                delta_rad = None
                jj_area = None
                same_jj_status = "UNKNOWN_REQUIRED_DFF_PV_NOT_PROBED"
            row = {
                "run_id": run_dir.name, "source_sha": BVM_SHA256,
                "topology_version": "V9_SHARED_ROW_SE_BL", "A": scenario["a"], "B": scenario["b"],
                "expected_product": scenario["expected_product"],
                "expected_bits_msb_first": scenario["expected_bits_msb_first"],
                "read_index": read_index, "read_window_ps": f"{windows[window_name]['start_ps']}:{windows[window_name]['end_ps']} [start,end)",
                "bit_index_lsb0": bit, "output_signal": signal,
                "expected_bit": scenario["expected_bits_lsb_to_msb"][bit],
                "event_count_per_bit": "UNKNOWN", "observed_bits": "UNKNOWN",
                "output_signed_area_v_s": signed_area,
                "output_signed_area_phi0_navigation": signed_area / PHI0,
                "output_positive_area_phi0_navigation": pos_area / PHI0,
                "output_negative_area_phi0_navigation": neg_area / PHI0,
                "output_positive_peak_v": float(values[pos_idx]),
                "output_positive_peak_time_ps": time_ps[pos_idx],
                "output_negative_peak_v": float(values[neg_idx]),
                "output_negative_peak_time_ps": time_ps[neg_idx],
                "descriptive_lobe_candidate_count_not_event_count": len(morphology.get("candidates", [])),
                "same_jj_status": same_jj_status,
                "same_jj_phase_signal": t1_jj or "UNKNOWN",
                "same_jj_voltage_signal": t1_v or "UNKNOWN",
                "same_jj_phase_delta_rad": delta_rad,
                "same_jj_phase_delta_rad_over_2pi_navigation": delta_rad / (2 * math.pi) if delta_rad is not None else None,
                "same_jj_voltage_area_v_s": jj_area,
                "same_jj_voltage_area_phi0_navigation": jj_area / PHI0 if jj_area is not None else None,
                "same_jj_phase_minus_area_navigation": delta_rad / (2 * math.pi) - jj_area / PHI0
                if delta_rad is not None and jj_area is not None else None,
                "data_arrival_time": "UNKNOWN",
                "actual_clock_arrival_time": "UNKNOWN",
                "measured_timing_difference": "UNKNOWN",
                "arithmetic_status": "INCONCLUSIVE",
                "timing_status": "INCONCLUSIVE",
                "raw_path": (run_dir / "raw.csv").relative_to(REPO).as_posix(),
                "raw_sha256": before,
                "qa_notes": ("No frozen output event classifier/Gate; output area and lobe candidates are descriptive navigation only."
                             if bit < 7 else
                             "No frozen output event classifier/Gate; DFF internal P/V is absent from the preregistered probe set, so bit7 same-JJ cross-check is UNKNOWN."),
            }
            output_rows.append(row)
            waveform_metrics.append({"signal": signal, "window": window_name,
                                     "signed_area_v_s": signed_area,
                                     "signed_area_phi0_navigation": signed_area / PHI0,
                                     "positive_area_phi0_navigation": pos_area / PHI0,
                                     "negative_area_phi0_navigation": neg_area / PHI0,
                                     "positive_peak_v": float(values[pos_idx]),
                                     "positive_peak_time_ps": time_ps[pos_idx],
                                     "negative_peak_v": float(values[neg_idx]),
                                     "negative_peak_time_ps": time_ps[neg_idx],
                                     "descriptive_lobe_candidates": morphology})

    timing_rows: list[dict[str, Any]] = []
    for read_index in range(3):
        round_name = f"ROUND_{read_index + 1}"
        read_window = round_windows[round_name]
        clock_window = round_windows[f"CLOCK_{read_index + 1}"]
        data_indices = window_indices[round_name]
        clock_indices = indices(clock_window[0], clock_window[1])
        if len(clock_indices) < 2:
            raise V9ConfigError(f"raw has fewer than two stored samples in CLOCK_{read_index + 1}")
        for channel in CHANNELS:
            is_dff = channel == "DFF"
            data_signal = "V(DFF_IN)" if is_dff else f"V(T1_I_{channel})"
            clock_signal = f"V(CLK_{channel})"
            data_values = columns[data_signal]
            clock_values = columns[clock_signal]
            data_index = max(data_indices, key=lambda idx: abs(data_values[idx]))
            clock_index = max(clock_indices, key=lambda idx: abs(clock_values[idx]))
            data_peak_ps = time_ps[data_index]
            clock_peak_ps = time_ps[clock_index]
            timing_rows.append({
                "run_id": run_dir.name, "read_index": read_index + 1,
                "stage": channel, "data_signal": data_signal, "clock_signal": clock_signal,
                "read_window_start_ps": read_window[0], "read_window_end_ps": read_window[1],
                "clock_pwl_start_ps": scenario["clock_pwl_starts_ps"][read_index],
                "data_peak_time_ps_navigation_only": data_peak_ps,
                "data_peak_value_v": float(data_values[data_index]),
                "clock_peak_time_ps_navigation_only": clock_peak_ps,
                "clock_peak_value_v": float(clock_values[clock_index]),
                "clock_minus_data_peak_time_ps_navigation_only": clock_peak_ps - data_peak_ps,
                "timing_status": "INCONCLUSIVE",
                "timing_note": "stored-sample absolute peak-time difference only; not an event edge, setup/hold margin, or SFQ timing classification",
            })

    timing_by_read_stage = {(int(item["read_index"]), item["stage"]): item for item in timing_rows}
    for row in output_rows:
        stage = f"D{row['bit_index_lsb0']}" if row["bit_index_lsb0"] < 7 else "DFF"
        timing = timing_by_read_stage[(int(row["read_index"]), stage)]
        row["data_arrival_time"] = timing["data_peak_time_ps_navigation_only"]
        row["actual_clock_arrival_time"] = timing["clock_peak_time_ps_navigation_only"]
        row["measured_timing_difference"] = timing["clock_minus_data_peak_time_ps_navigation_only"]

    raw_after = sha256(raw)
    if before != raw_after:
        raise V9ConfigError("raw SHA changed during analysis")
    raw_qa = {
        "schema": "bvm4x4-v9-raw-qa-v1", "status": "PASS",
        "raw_sha256_before": before, "raw_sha256_after_analysis": raw_after,
        "raw_immutable": True, "sample_count": len(times), "header_count": len(header),
        "probe_count": len(required), "time_start_s": times[0], "time_end_s": times[-1],
        "time_range_ps": [time_ps[0], time_ps[-1]], "dt_min_s": min(dt), "dt_max_s": max(dt),
        "uniform_time_grid": max(dt) - min(dt) <= max(dt) * 1e-6,
        "finite_values": True, "time_monotonic": True, "windows": windows,
        "integration_grid": "actual stored timestamps", "interpolation_or_resampling": False,
    }
    metrics = {
        "schema": "bvm4x4-v9-mechanical-metrics-v1", "status": "DERIVED_ARITHMETIC_ONLY",
        "raw_sha256": before, "windows": windows, "outputs": waveform_metrics,
        "same_jj_phase_voltage": _same_jj_records(times, columns, window_indices),
        "timing_peak_descriptors": timing_rows,
        "event_classifier": None, "observed_bits": "UNKNOWN",
        "arithmetic_status": "INCONCLUSIVE", "timing_status": "INCONCLUSIVE",
        "phase_raw_unit": "radians", "phase_navigation": "independent unwrap then delta/(2*pi)",
        "area_navigation": "trapezoid on actual stored timestamps / Phi0",
        "scientific_interpretation_performed": False,
    }
    return metrics, raw_qa, output_rows, timing_rows


def _same_jj_records(times: list[float], columns: dict[str, Any],
                     window_indices: dict[str, list[int]]) -> list[dict[str, Any]]:
    records = []
    labels = []
    for stage in range(7):
        instance = f"XT1_D{stage}"
        for jj in ("B_J9", "B_J11"):
            labels.append((f"P({jj}|{instance})", f"V({jj}|{instance})"))
    for diagonal, members in DIAGONALS.items():
        instance = f"XCB_{diagonal}_L{len(members)}"
        labels.append((f"P(BJ1|{instance})", f"V(BJ1|{instance})"))
    for stage in range(1, 7):
        labels.append((f"P(BJ1|XCB_CARRY_D{stage})", f"V(BJ1|XCB_CARRY_D{stage})"))
        count = CARRY_SJTL_COUNTS[stage]
        for serial in range(1, count + 1):
            name = f"XSJTL_CARRY_D{stage}" + (f"_S{serial}" if count > 1 and serial > 1 else "")
            labels.append((f"P(BJ1|{name})", f"V(BJ1|{name})"))
    for phase_label, voltage_label in labels:
        phase = platform._unwrap(columns[phase_label])
        for window, ids in window_indices.items():
            first, last = ids[0], ids[-1]
            delta = phase[last] - phase[first]
            area = platform._trapz(times, columns[voltage_label], ids)
            records.append({"phase_signal": phase_label, "voltage_signal": voltage_label,
                            "window": window, "sample_count": len(ids),
                            "phase_delta_rad": delta,
                            "phase_delta_rad_over_2pi_navigation": delta / (2 * math.pi),
                            "voltage_area_v_s_same_jj_same_rows": area,
                            "voltage_area_phi0_navigation": area / PHI0,
                            "phase_minus_area_navigation": delta / (2 * math.pi) - area / PHI0,
                            "interpolation_or_resampling": False})
    return records


def _rounds_for_stimulus_from_scenario(scenario: dict[str, Any]) -> dict[str, tuple[float, float]]:
    reads = scenario["read_times_ps"]
    clocks = scenario["clock_pwl_starts_ps"]
    result: dict[str, tuple[float, float]] = {}
    for index, start in enumerate(reads):
        end = reads[index + 1] if index + 1 < len(reads) else scenario["stop_ps"]
        result[f"ROUND_{index + 1}"] = (start, end)
    for index, start in enumerate(clocks):
        end = clocks[index + 1] if index + 1 < len(clocks) else scenario["stop_ps"]
        result[f"CLOCK_{index + 1}"] = (start, end)
    return result


def _csv_write(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = list(rows[0]) if rows else []
    temp = path.with_name(path.name + ".writing")
    if temp.exists():
        raise V9ConfigError(f"stale temporary CSV exists: {temp}")
    try:
        with temp.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fieldnames, extrasaction="raise")
            writer.writeheader()
            writer.writerows(rows)
        temp.replace(path)
    finally:
        if temp.exists():
            temp.unlink()


def _write_result_brief(run_dir: Path, scenario: dict[str, Any], result: dict[str, Any],
                        metrics: dict[str, Any]) -> None:
    atomic_text(run_dir / "RESULT_BRIEF.md", f"""# {run_dir.name}

- A × B: {scenario['a']} × {scenario['b']} = {scenario['expected_product']} (expected MSB-first `{scenario['expected_bits_msb_first']}`).
- Reads: `{scenario['read_times_ps']}` ps; clock PWL starts: `{scenario['clock_pwl_starts_ps']}` ps; DT/STOP: {scenario['dt_ps']}/{scenario['stop_ps']} ps.
- Artifact status: `{result['artifact_status']}`; mechanical QA: `{result['qa_status']}`.
- Event count and observed bits: `UNKNOWN`; arithmetic status: `INCONCLUSIVE` (no frozen classifier/Gate).
- Timing status: `INCONCLUSIVE`; peak-time differences are navigation only.
- Scientific interpretation: NOT PERFORMED; no follow-up authorized.
- Raw SHA-256: `{result['raw_sha256']}`.
""")


def _run_manifest_row(run_id: str, scenario: dict[str, Any], batch_id: str,
                      result: dict[str, Any]) -> dict[str, Any]:
    return {
        "run_id": run_id, "case": scenario["case_id"], "batch_id": batch_id,
        "A": scenario["a"], "B": scenario["b"],
        "row_bits": scenario["row_bits_R1_lsb"], "column_bits": scenario["column_bits_C1_msb"],
        "topology_version": "V9_SHARED_ROW_SE_BL",
        "status": result["status"], "artifact_status": result["artifact_status"],
        "physical_solve_count": 1, "raw_sha256": result.get("raw_sha256"),
        "raw_bytes": result.get("raw_bytes"), "deck_sha256": result.get("deck_sha256"),
        "stimulus_sha256": result.get("stimulus_sha256"),
        "probe_count": result.get("probe_count"), "qa_status": result.get("qa_status"),
        "source_sha256": result.get("source_sha256", {}),
        "scientific_interpretation_performed": False, "automatic_follow_up": False,
    }


def _append_run_to_manifest(run_record: dict[str, Any], run_id: str, batch_id: str) -> None:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if any(item.get("run_id") == run_id for item in data.get("runs", [])):
        raise V9ConfigError(f"run ID already exists in experiment_manifest: {run_id}")
    data["runs"].append(run_record)
    data["physical_solve_count"] = sum(int(item.get("physical_solve_count", 0)) for item in data["runs"])
    for batch in data.get("authorization_batches", []):
        if batch.get("batch_id") == batch_id:
            batch.setdefault("completed_run_ids", []).append(run_id)
            batch["physical_solve_count_completed"] = len(batch["completed_run_ids"])
            break
    else:
        raise V9ConfigError(f"reserved authorization batch not found: {batch_id}")
    atomic_json(MANIFEST, data)


def repair_existing_postprocess(run_id: str) -> dict[str, Any]:
    """Re-QA a valid solver raw after a registered analysis-tool failure; never calls JoSIM."""
    if run_id != "A109_V9_A0_B0_80P68":
        raise V9ConfigError("this recovery is scoped only to the A109 postprocess failure")
    run_dir = RUNS / run_id
    result_path = run_dir / "result.json"
    raw_path = run_dir / "raw.csv"
    if not run_dir.is_dir() or not result_path.is_file() or not raw_path.is_file():
        raise V9ConfigError("A109 run/raw/result artifact is incomplete")
    old_result = json.loads(result_path.read_text(encoding="utf-8"))
    if (old_result.get("status") != "POSTPROCESS_FAILURE_RAW_PRESERVED" or
            old_result.get("artifact_status") != "ARTIFACT_INVALID" or
            old_result.get("solver_exit_code") != 0):
        raise V9ConfigError("A109 is not the expected solver-valid/postprocess-invalid attempt")
    raw_sha_before = sha256(raw_path)
    if raw_sha_before != old_result.get("raw_sha256"):
        raise V9ConfigError("A109 raw SHA differs from the preserved initial result")
    old_run_manifest_path = run_dir / "RUN_MANIFEST.json"
    if not old_run_manifest_path.is_file():
        raise V9ConfigError("A109 failed attempt lacks RUN_MANIFEST.json")
    old_run_manifest = json.loads(old_run_manifest_path.read_text(encoding="utf-8"))
    if old_run_manifest.get("hashes", {}).get("raw_sha256") != raw_sha_before:
        raise V9ConfigError("A109 raw SHA differs from the failed-attempt RUN_MANIFEST")
    attempt_dir = run_dir / "postprocess_attempts" / "001"
    if attempt_dir.exists():
        raise V9ConfigError("A109 postprocess repair attempt 001 already exists; refusing overwrite")
    attempt_dir.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(result_path, attempt_dir / "initial_result.json")
    shutil.copyfile(old_run_manifest_path, attempt_dir / "initial_RUN_MANIFEST.json")
    atomic_text(attempt_dir / "RECOVERY_NOTE.md", f"""# A109 postprocess recovery attempt 001

- Initial solver exit code: 0; initial raw SHA-256: `{raw_sha_before}`.
- Initial artifact status: `ARTIFACT_INVALID` because the analyzer requested absent probe `P(B7|XDFF)`.
- Repair: bit7 same-JJ P/V fields are `UNKNOWN` when the DFF internal probe is not registered; the raw/deck/stimulus/probe set is unchanged.
- JoSIM invocation in this recovery: 0. Raw mutation: prohibited and checked.
""")

    scenario = json.loads((run_dir / "CASE_CONFIG.json").read_text(encoding="utf-8"))
    probes = json.loads((run_dir / "probe_manifest.json").read_text(encoding="utf-8"))
    source_manifest = json.loads((run_dir / "source_manifest.json").read_text(encoding="utf-8"))
    original_preflight = (ANALYSIS / "PREFLIGHT.md").read_text(encoding="utf-8")
    runner_match = re.search(r"V9 runner SHA-256: `([0-9a-f]{64})`", original_preflight)
    if not runner_match:
        raise V9ConfigError("original locked preflight lacks the solver-execution runner SHA")
    execution_runner_sha = runner_match.group(1)
    payload = {"scenario": scenario, "probes": probes,
               "source_records": source_manifest["sources"]}
    solver_info = old_run_manifest["solver"]
    hashes = old_run_manifest["hashes"]
    metrics, raw_qa, output_rows, timing_rows = analyze_v9_raw(run_dir, scenario, probes)
    if raw_qa["raw_sha256_before"] != raw_sha_before or sha256(raw_path) != raw_sha_before:
        raise V9ConfigError("A109 raw changed while repairing postprocess artifacts")
    atomic_json(run_dir / "metrics.json", metrics)
    atomic_json(run_dir / "raw_qa.json", raw_qa)
    _csv_write(run_dir / "functional_results.csv", output_rows)
    _csv_write(run_dir / "clock_timing.csv", timing_rows)
    chain_qa = {"schema": "bvm4x4-v9-stage-qa-v1", "status": "PASS",
                "raw_sha256": raw_sha_before, "source_count": 20,
                "stage_timing_rows": len(timing_rows), "output_measurement_rows": len(output_rows),
                "event_classifier": None, "scientific_interpretation_performed": False}
    atomic_json(run_dir / "chain_qa.json", chain_qa)
    plot_root = PLOTS / "v9-multiply-20261016" / run_id
    plot_qa = platform.render_plots(run_dir, probes, plot_root_override=plot_root)
    if sha256(raw_path) != raw_sha_before:
        raise V9ConfigError("A109 raw SHA changed during classic visualization regeneration")
    qa = {"schema": "bvm4x4-v9-run-qa-v1", "status": "PASS", "artifact_status": "VALID",
          "physical_solve_count": 1, "solver_exit_code": 0, "static_qa_status": "PASS",
          "raw_qa_status": raw_qa["status"], "chain_qa_status": chain_qa["status"],
          "plot_qa_status": plot_qa["status"], "raw_sha256_before_analysis": raw_sha_before,
          "raw_sha256_after_analysis": raw_sha_before, "raw_bytes": raw_path.stat().st_size,
          "sample_count": raw_qa["sample_count"], "time_range_ps": raw_qa["time_range_ps"],
          "probe_count": probes["signal_count"], "all_required_probes_present": True,
          "arithmetic_status": "INCONCLUSIVE", "timing_status": "INCONCLUSIVE",
          "postprocess_revision": 2, "scientific_interpretation_performed": False}
    provenance = _provenance(run_dir, scenario, solver_info, hashes, raw_sha_before, plot_qa, qa)
    provenance["postprocess_revision"] = 2
    provenance["solver_execution_runner_sha256"] = execution_runner_sha
    provenance["postprocess_runner_sha256"] = sha256(Path(__file__).resolve())
    provenance["prior_postprocess_failure_sha256"] = sha256(attempt_dir / "initial_result.json")
    atomic_json(run_dir / "provenance.json", provenance)
    config = platform.parse_env(run_dir / "V9_CONFIG.snapshot.env")
    result = {
        "schema": "bvm4x4-v9-result-v1", "run_id": run_id, "batch_id": BATCH_ID,
        "case": scenario["case_id"], "A": scenario["a"], "B": scenario["b"],
        "expected_product": scenario["expected_product"],
        "expected_bits_msb_first": scenario["expected_bits_msb_first"],
        "bit_order": scenario["bit_order"], "status": "MECHANICAL_QA_PASS_AWAITING_USER_REVIEW",
        "artifact_status": "VALID", "physical_solve_count": 1, "solver_exit_code": 0,
        "raw_sha256": raw_sha_before, "raw_bytes": raw_path.stat().st_size,
        "deck_sha256": hashes["deck_sha256"], "stimulus_sha256": hashes["stimulus_sha256"],
        "source_sha256": {item["filename"]: item["sha256"] for item in source_manifest["sources"]},
        "probe_count": probes["signal_count"], "qa_status": "PASS",
        "arithmetic_status": "INCONCLUSIVE", "timing_status": "INCONCLUSIVE",
        "event_count_per_bit": "UNKNOWN", "observed_bits": "UNKNOWN",
        "postprocess_revision": 2,
        "solver_execution_runner_sha256": execution_runner_sha,
        "postprocess_runner_sha256": sha256(Path(__file__).resolve()),
        "prior_postprocess_failure": "KeyError: P(B7|XDFF); raw preserved, no re-solve",
        "scientific_interpretation_performed": False, "automatic_follow_up": False,
    }
    atomic_json(run_dir / "qa.json", qa)
    atomic_json(run_dir / "result.json", result)
    atomic_json(run_dir / "metadata.json", {
        "schema": "bvm4x4-v9-metadata-v1", "run_id": run_id, "batch_id": BATCH_ID,
        "effective_scenario": scenario, "effective_v9_config": {key: config[key] for key in V9_KEYS},
        "solver": solver_info, "command": [str(SOLVER), "-a", "1", "-o", "raw.csv", "deck.cir"],
        "exit_code": 0, "deck_sha256": hashes["deck_sha256"],
        "stimulus_sha256": hashes["stimulus_sha256"], "raw_sha256": raw_sha_before,
        "raw_bytes": raw_path.stat().st_size,
        "source_manifest_sha256": sha256(run_dir / "source_manifest.json"),
        "probe_manifest_sha256": sha256(run_dir / "probe_manifest.json"),
        "topology_manifest_sha256": sha256(run_dir / "topology_manifest.json"),
        "risk_level": "NORMAL", "study_phase": "EXPLORATORY",
        "artifact_status": "VALID", "qa_status": "PASS", "postprocess_revision": 2,
        "solver_execution_runner_sha256": execution_runner_sha,
        "postprocess_runner_sha256": sha256(Path(__file__).resolve()),
        "scientific_interpretation_performed": False, "automatic_follow_up": False,
    })
    _write_result_brief(run_dir, scenario, result, metrics)
    run_manifest = {**old_run_manifest, "artifact_status": "VALID", "mechanical_qa_status": "PASS",
                    "postprocess_revision": 2, "raw_sha256_verified_after_reanalysis": raw_sha_before,
                    "solver_execution_runner_sha256": execution_runner_sha,
                    "postprocess_runner_sha256": sha256(Path(__file__).resolve()),
                    "result_sha256": sha256(run_dir / "result.json"),
                    "provenance_sha256": sha256(run_dir / "provenance.json"),
                    "qa_sha256": sha256(run_dir / "qa.json")}
    atomic_json(run_dir / "RUN_MANIFEST.json", run_manifest)
    atomic_json(run_dir / "postprocess_attempts/001/RECOVERY_QA.json", {
        "status": "PASS", "raw_sha256_before": raw_sha_before,
        "raw_sha256_after": sha256(raw_path), "solver_invoked": False,
        "artifact_status": "VALID_AFTER_ANALYSIS_REPAIR", "postprocess_revision": 2})
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    rows = {item.get("run_id"): item for item in data.get("runs", [])}
    row = rows.get(run_id)
    if row is None or row.get("raw_sha256") != raw_sha_before:
        raise V9ConfigError("A109 experiment_manifest raw identity is missing or inconsistent")
    row.update({"status": result["status"], "artifact_status": "VALID", "qa_status": "PASS",
                "raw_bytes": raw_path.stat().st_size, "postprocess_revision": 2,
                "prior_postprocess_failure": "KeyError: P(B7|XDFF); same immutable raw reanalyzed"})
    atomic_json(MANIFEST, data)
    return result


def _reserve_batch(batch_id: str, scenarios: list[dict[str, Any]], run_ids: list[str],
                   static_qa: dict[str, Any], preflight_sha: str) -> None:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if any(item.get("batch_id") == batch_id for item in data.get("authorization_batches", [])):
        raise V9ConfigError(f"authorization batch ID already exists: {batch_id}")
    known = {item.get("run_id") for item in data.get("runs", [])}
    known.update(run_id for item in data.get("authorization_batches", [])
                 for run_id in item.get("run_ids", []))
    if known.intersection(run_ids):
        raise V9ConfigError("one or more V9 run IDs are already in manifest history")
    data.setdefault("authorization_batches", []).append({
        "batch_id": batch_id, "risk_level": "NORMAL", "study_phase": "EXPLORATORY",
        "authorized_cases": [item["case_id"] for item in scenarios],
        "run_ids": run_ids, "authorized_physical_solve_count": len(run_ids),
        "physical_solve_count_completed": 0, "completed_run_ids": [],
        "parent_head_at_preflight": platform._git_output("rev-parse", "HEAD"),
        "preflight_sha256": preflight_sha,
        "static_qa_sha256": sha256(ANALYSIS / "STATIC_QA.json"),
        "raw_analysis_scope": "mechanical observations only; event count unknown; arithmetic/timing inconclusive without classifier",
        "scientific_interpretation_performed": False, "automatic_follow_up": False,
    })
    data.setdefault("authorized_physical_solves", [])
    for item in scenarios:
        if item["case_id"] not in data["authorized_physical_solves"]:
            data["authorized_physical_solves"].append(item["case_id"])
    data["maximum_physical_solve_count"] = int(data.get("maximum_physical_solve_count", 0)) + len(run_ids)
    atomic_json(MANIFEST, data)


def _registered_batch_run_ids(scenarios: list[dict[str, Any]]) -> tuple[list[str], dict[str, Any]]:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    matches = [item for item in data.get("authorization_batches", [])
               if item.get("batch_id") == BATCH_ID]
    if len(matches) != 1:
        raise V9ConfigError(f"expected one existing authorization record for {BATCH_ID}; found {len(matches)}")
    batch = matches[0]
    run_ids = batch.get("run_ids", [])
    if len(run_ids) != 4 or [rid.split("_", 1)[1] for rid in run_ids] != [item["case_id"] for item in scenarios]:
        raise V9ConfigError("existing V9 authorization IDs/cases differ from the exact registered four-case matrix")
    return run_ids, batch


def _revise_preflight_for_resume(config: dict[str, str], scenarios: list[dict[str, Any]],
                                 run_ids: list[str], payloads: list[dict[str, Any]],
                                 static_qa: dict[str, Any], sources: list[dict[str, str]],
                                 solver_info: dict[str, Any]) -> str:
    preflight_path = ANALYSIS / "PREFLIGHT.md"
    if not preflight_path.is_file():
        raise V9ConfigError("resume requires the previous locked PREFLIGHT.md")
    old_text = preflight_path.read_text(encoding="utf-8")
    if "Preflight state: `LOCKED_BEFORE_PHYSICAL_SOLVE`." not in old_text:
        raise V9ConfigError("resume requires a locked preflight from the original solve attempt")
    old_sha = sha256(preflight_path)
    revision_dir = ANALYSIS / "preflight_revisions"
    revision_dir.mkdir(parents=True, exist_ok=True)
    archived = revision_dir / "001_PREFLIGHT.md"
    if archived.exists():
        if sha256(archived) != old_sha:
            raise V9ConfigError("preflight revision archive already exists with a different SHA")
    else:
        shutil.copyfile(preflight_path, archived)
    note = ("A109 raw is unchanged and is reprocessed after correcting only the analyzer's request for absent DFF B7 P/V; "
            "no circuit, stimulus, probe, parameter, window, or additional-solve change. Continue only A110-A112.")
    revised = _preflight_text(config, scenarios, run_ids, sources, static_qa,
                               payloads, solver_info=solver_info, revision_note=note)
    new_sha = sha256_from_text(revised)
    atomic_text(preflight_path, revised)
    revision_path = ANALYSIS / "PREFLIGHT_REVISIONS.json"
    revisions = json.loads(revision_path.read_text(encoding="utf-8")) if revision_path.is_file() else {
        "schema": "bvm4x4-v9-preflight-revisions-v1", "revisions": []}
    revisions["revisions"].append({"status": "PREPROCESSOR_REPAIR_AND_REMAINING_RUNS_LOCKED",
                                    "superseded_preflight_sha256": old_sha,
                                    "preflight_archive_path": archived.relative_to(ANALYSIS).as_posix(),
                                    "new_preflight_sha256": new_sha,
                                    "reason": note,
                                    "solver_version": solver_info["version"],
                                    "solver_sha256": solver_info["sha256"],
                                    "physical_solve_count_in_revision": 0,
                                    "existing_raw_reanalysis_run_ids": ["A109_V9_A0_B0_80P68"],
                                    "remaining_authorized_run_ids": run_ids[1:]})
    atomic_json(revision_path, revisions)
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    batch = next(item for item in data["authorization_batches"] if item.get("batch_id") == BATCH_ID)
    batch.setdefault("preflight_revisions", []).append({"superseded_sha256": old_sha,
                                                          "current_sha256": new_sha,
                                                          "physical_solve_count": 0,
                                                          "reason": note})
    batch["preflight_sha256"] = new_sha
    batch["preflight_revision"] = len(batch["preflight_revisions"]) + 1
    atomic_json(MANIFEST, data)
    return new_sha


def _provenance(run_dir: Path, scenario: dict[str, Any], solver_info: dict[str, Any],
                hashes: dict[str, str], raw_sha: str, plot_qa: dict[str, Any],
                qa: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "bvm4x4-v9-provenance-v1", "run_id": run_dir.name,
        "batch_id": BATCH_ID, "parent_head": solver_info["parent_head"],
        "solver": solver_info, "scenario": scenario,
        "hashes": {**hashes, "raw_sha256": raw_sha,
                   "user_case_sha256": sha256(USER_CASE),
                   "runner_sha256": sha256(Path(__file__).resolve()),
                   "stimulus_generator_sha256": sha256(REPO / "scripts/bvm_stimulus.py"),
                   "plotter_sha256": sha256(PLOTTER), "plotly_sha256": sha256(PLOTLY),
                   "contract_sha256": sha256(REPO / "docs/EXPERIMENT_CONTRACT.md"),
                   "workflow_sha256": sha256(REPO / "docs/research/EXPERIMENT_WORKFLOW_V1.md"),
                   "preflight_sha256": sha256(ANALYSIS / "PREFLIGHT.md"),
                   "experiment_yaml_sha256": sha256(ANALYSIS / "experiment.yaml")},
        "plot_pages": plot_qa["pages"], "qa_status": qa["status"],
        "raw_integrity_before_after": True, "interpretation_ceiling": "mechanical observation only",
        "scientific_interpretation_performed": False, "automatic_follow_up": False,
    }


def run_one(config: dict[str, str], scenario: dict[str, Any], run_id: str, payload: dict[str, Any],
            solver_info: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    run_dir = RUNS / run_id
    if run_dir.exists():
        raise V9ConfigError(f"refusing to overwrite existing run directory: {run_dir}")
    run_dir.mkdir(parents=True, exist_ok=False)
    hashes = _write_case_artifacts(run_dir, config, payload, run_id, BATCH_ID,
                                   payload["source_records"], solver_info)
    raw_path = run_dir / "raw.csv"
    log_path = run_dir / "run.log"
    if raw_path.exists() or log_path.exists():
        raise V9ConfigError(f"raw/log already exists in new run directory: {run_dir}")
    command = [str(SOLVER), "-a", "1", "-o", "raw.csv", "deck.cir"]
    started = datetime.now(timezone.utc).isoformat()
    completed = subprocess.run(command, cwd=run_dir, capture_output=True, text=True, check=False)
    finished = datetime.now(timezone.utc).isoformat()
    atomic_text(run_dir / "stdout.txt", completed.stdout)
    atomic_text(run_dir / "stderr.txt", completed.stderr)
    raw_sha = sha256(raw_path) if raw_path.is_file() else None
    run_log = (f"run_id={run_id}\nbatch_id={BATCH_ID}\nstarted_at_utc={started}\nfinished_at_utc={finished}\n"
               f"command={' '.join(command)}\nsolver_version={solver_info['version']}\n"
               f"solver_sha256={solver_info['sha256']}\nsolver_exit_code={completed.returncode}\n"
               f"deck_sha256={hashes['deck_sha256']}\nstimulus_sha256={hashes['stimulus_sha256']}\n"
               f"raw_sha256={raw_sha or 'MISSING'}\n")
    atomic_text(log_path, run_log)
    if completed.returncode != 0 or not raw_path.is_file() or raw_path.stat().st_size == 0:
        result = {"run_id": run_id, "case": scenario["case_id"], "batch_id": BATCH_ID,
                  "status": "SOLVER_FAILURE", "artifact_status": "ARTIFACT_INVALID",
                  "physical_solve_count": 1, "solver_exit_code": completed.returncode,
                  "raw_sha256": raw_sha, "deck_sha256": hashes["deck_sha256"],
                  "stimulus_sha256": hashes["stimulus_sha256"], "probe_count": payload["probes"]["signal_count"],
                  "source_sha256": {item["filename"]: item["sha256"] for item in payload["source_records"]},
                  "scientific_interpretation_performed": False, "automatic_follow_up": False}
        atomic_json(run_dir / "result.json", result)
        atomic_json(run_dir / "RUN_MANIFEST.json", {
            "schema": "bvm4x4-v9-run-manifest-v1", "run_id": run_id, "batch_id": BATCH_ID,
            "parent_head": solver_info["parent_head"], "solver": solver_info, "command": command,
            "exit_code": completed.returncode, "paths": {"deck": "deck.cir", "stimulus": "stimulus.inc",
                                                           "raw": "raw.csv", "log": "run.log"},
            "hashes": {**hashes, "raw_sha256": raw_sha},
            "artifact_status": "ARTIFACT_INVALID", "physical_solve_count": 1})
        _append_run_to_manifest(_run_manifest_row(run_id, scenario, BATCH_ID, result), run_id, BATCH_ID)
        return 2, result
    if raw_path.stat().st_size >= MAX_RAW_BYTES:
        result = {"run_id": run_id, "case": scenario["case_id"], "batch_id": BATCH_ID,
                  "status": "RAW_EXCEEDS_SINGLE_FILE_GUARD", "artifact_status": "ARTIFACT_INVALID",
                  "physical_solve_count": 1, "solver_exit_code": completed.returncode,
                  "raw_sha256": raw_sha, "raw_bytes": raw_path.stat().st_size,
                  "deck_sha256": hashes["deck_sha256"], "stimulus_sha256": hashes["stimulus_sha256"],
                  "probe_count": payload["probes"]["signal_count"],
                  "source_sha256": {item["filename"]: item["sha256"] for item in payload["source_records"]},
                  "automatic_follow_up": False}
        atomic_json(run_dir / "result.json", result)
        atomic_json(run_dir / "RUN_MANIFEST.json", {
            "schema": "bvm4x4-v9-run-manifest-v1", "run_id": run_id, "batch_id": BATCH_ID,
            "parent_head": solver_info["parent_head"], "solver": solver_info, "command": command,
            "exit_code": completed.returncode, "paths": {"deck": "deck.cir", "stimulus": "stimulus.inc",
                                                           "raw": "raw.csv", "log": "run.log"},
            "hashes": {**hashes, "raw_sha256": raw_sha},
            "artifact_status": "ARTIFACT_INVALID", "physical_solve_count": 1})
        _append_run_to_manifest(_run_manifest_row(run_id, scenario, BATCH_ID, result), run_id, BATCH_ID)
        return 2, result
    try:
        metrics, raw_qa, output_rows, timing_rows = analyze_v9_raw(run_dir, scenario, payload["probes"])
        atomic_json(run_dir / "metrics.json", metrics)
        atomic_json(run_dir / "raw_qa.json", raw_qa)
        _csv_write(run_dir / "functional_results.csv", output_rows)
        _csv_write(run_dir / "clock_timing.csv", timing_rows)
        chain_qa = {"schema": "bvm4x4-v9-stage-qa-v1", "status": "PASS",
                    "raw_sha256": raw_sha, "source_count": 20,
                    "stage_timing_rows": len(timing_rows), "output_measurement_rows": len(output_rows),
                    "event_classifier": None, "scientific_interpretation_performed": False}
        atomic_json(run_dir / "chain_qa.json", chain_qa)
        plot_root = PLOTS / "v9-multiply-20261016" / run_id
        plot_qa = platform.render_plots(run_dir, payload["probes"], plot_root_override=plot_root)
        raw_sha_after = sha256(raw_path)
        if raw_sha_after != raw_sha:
            raise V9ConfigError("immutable raw SHA changed after analysis/visualization")
        qa = {
            "schema": "bvm4x4-v9-run-qa-v1", "status": "PASS",
            "artifact_status": "VALID", "physical_solve_count": 1,
            "solver_exit_code": completed.returncode, "static_qa_status": "PASS",
            "raw_qa_status": raw_qa["status"], "chain_qa_status": chain_qa["status"],
            "plot_qa_status": plot_qa["status"], "raw_sha256_before_analysis": raw_sha,
            "raw_sha256_after_analysis": raw_sha_after, "raw_bytes": raw_path.stat().st_size,
            "sample_count": raw_qa["sample_count"], "time_range_ps": raw_qa["time_range_ps"],
            "probe_count": payload["probes"]["signal_count"], "all_required_probes_present": True,
            "arithmetic_status": "INCONCLUSIVE", "timing_status": "INCONCLUSIVE",
            "scientific_interpretation_performed": False,
        }
        atomic_json(run_dir / "plot_manifest.json", json.loads((run_dir / "plot_manifest.json").read_text(encoding="utf-8")))
        atomic_json(run_dir / "plot_qa.json", json.loads((run_dir / "plot_qa.json").read_text(encoding="utf-8")))
        provenance = _provenance(run_dir, scenario, solver_info, hashes, raw_sha, plot_qa, qa)
        atomic_json(run_dir / "provenance.json", provenance)
        result = {
            "schema": "bvm4x4-v9-result-v1", "run_id": run_id, "batch_id": BATCH_ID,
            "case": scenario["case_id"], "A": scenario["a"], "B": scenario["b"],
            "expected_product": scenario["expected_product"],
            "expected_bits_msb_first": scenario["expected_bits_msb_first"],
            "bit_order": scenario["bit_order"], "status": "MECHANICAL_QA_PASS_AWAITING_USER_REVIEW",
            "artifact_status": "VALID", "physical_solve_count": 1,
            "solver_exit_code": completed.returncode, "raw_sha256": raw_sha,
            "raw_bytes": raw_path.stat().st_size, "deck_sha256": hashes["deck_sha256"],
            "stimulus_sha256": hashes["stimulus_sha256"], "source_sha256": {
                item["filename"]: item["sha256"] for item in payload["source_records"]},
            "probe_count": payload["probes"]["signal_count"], "qa_status": qa["status"],
            "arithmetic_status": "INCONCLUSIVE", "timing_status": "INCONCLUSIVE",
            "event_count_per_bit": "UNKNOWN", "observed_bits": "UNKNOWN",
            "scientific_interpretation_performed": False, "automatic_follow_up": False,
        }
        atomic_json(run_dir / "qa.json", qa)
        atomic_json(run_dir / "result.json", result)
        atomic_json(run_dir / "metadata.json", {
            "schema": "bvm4x4-v9-metadata-v1", "run_id": run_id,
            "batch_id": BATCH_ID, "effective_scenario": scenario,
            "effective_v9_config": {key: config[key] for key in V9_KEYS},
            "solver": solver_info, "command": command, "exit_code": completed.returncode,
            "deck_sha256": hashes["deck_sha256"], "stimulus_sha256": hashes["stimulus_sha256"],
            "raw_sha256": raw_sha, "raw_bytes": raw_path.stat().st_size,
            "source_manifest_sha256": hashes["source_manifest_sha256"],
            "probe_manifest_sha256": hashes["probe_manifest_sha256"],
            "topology_manifest_sha256": hashes["topology_manifest_sha256"],
            "risk_level": "NORMAL", "study_phase": "EXPLORATORY",
            "artifact_status": "VALID", "qa_status": "PASS",
            "scientific_interpretation_performed": False, "automatic_follow_up": False,
        })
        atomic_json(run_dir / "RUN_MANIFEST.json", {
            "schema": "bvm4x4-v9-run-manifest-v1", "run_id": run_id, "batch_id": BATCH_ID,
            "parent_head": solver_info["parent_head"], "solver": solver_info, "command": command,
            "exit_code": completed.returncode, "paths": {"deck": "deck.cir", "stimulus": "stimulus.inc",
                                                           "raw": "raw.csv", "log": "run.log"},
            "hashes": {**hashes, "raw_sha256": raw_sha,
                       "source_manifest_sha256": hashes["source_manifest_sha256"],
                       "probe_manifest_sha256": hashes["probe_manifest_sha256"],
                       "topology_manifest_sha256": hashes["topology_manifest_sha256"]},
            "artifact_status": "VALID", "mechanical_qa_status": "PASS",
            "physical_solve_count": 1, "scientific_interpretation_performed": False,
        })
        _write_result_brief(run_dir, scenario, result, metrics)
        _append_run_to_manifest(_run_manifest_row(run_id, scenario, BATCH_ID, result), run_id, BATCH_ID)
        return 0, result
    except Exception as exc:
        result = {"run_id": run_id, "case": scenario["case_id"], "batch_id": BATCH_ID,
                  "status": "POSTPROCESS_FAILURE_RAW_PRESERVED", "artifact_status": "ARTIFACT_INVALID",
                  "physical_solve_count": 1, "solver_exit_code": completed.returncode,
                  "raw_sha256": sha256(raw_path), "error": f"{type(exc).__name__}: {exc}",
                  "deck_sha256": hashes["deck_sha256"], "stimulus_sha256": hashes["stimulus_sha256"],
                  "source_sha256": {item["filename"]: item["sha256"] for item in payload["source_records"]},
                  "probe_count": payload["probes"]["signal_count"],
                  "scientific_interpretation_performed": False, "automatic_follow_up": False}
        atomic_json(run_dir / "result.json", result)
        atomic_json(run_dir / "RUN_MANIFEST.json", {
            "schema": "bvm4x4-v9-run-manifest-v1", "run_id": run_id, "batch_id": BATCH_ID,
            "parent_head": solver_info["parent_head"], "solver": solver_info, "command": command,
            "exit_code": completed.returncode, "paths": {"deck": "deck.cir", "stimulus": "stimulus.inc",
                                                           "raw": "raw.csv", "log": "run.log"},
            "hashes": {**hashes, "raw_sha256": result["raw_sha256"]},
            "artifact_status": "ARTIFACT_INVALID", "physical_solve_count": 1})
        _append_run_to_manifest(_run_manifest_row(run_id, scenario, BATCH_ID, result), run_id, BATCH_ID)
        return 2, result


def _write_batch_outputs(config: dict[str, str], scenarios: list[dict[str, Any]], run_ids: list[str]) -> None:
    all_outputs = []
    all_timing = []
    for run_id in run_ids:
        run_dir = RUNS / run_id
        result = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
        if result.get("artifact_status") != "VALID" or result.get("qa_status") != "PASS":
            continue
        with (run_dir / "functional_results.csv").open("r", encoding="utf-8", newline="") as stream:
            all_outputs.extend(csv.DictReader(stream))
        with (run_dir / "clock_timing.csv").open("r", encoding="utf-8", newline="") as stream:
            all_timing.extend(csv.DictReader(stream))
    if all_outputs:
        _csv_write(ANALYSIS / "BVM4X4_V9_FUNCTIONAL_RESULTS.csv", all_outputs)
    if all_timing:
        _csv_write(ANALYSIS / "BVM4X4_V9_CLOCK_TIMING.csv", all_timing)
        rows = [
            f"| {row['run_id']} | {row['read_index']} | {row['stage']} | {float(row['data_peak_time_ps_navigation_only']):.6f} | {float(row['clock_pwl_start_ps']):.6f} | {float(row['clock_peak_time_ps_navigation_only']):.6f} | {float(row['clock_minus_data_peak_time_ps_navigation_only']):.6f} | INCONCLUSIVE |"
            for row in all_timing]
        atomic_text(ANALYSIS / "BVM4X4_V9_CLOCK_TIMING.md", """# V9 actual-clock / data timing observations

All times are derived from actual stored raw timestamps. `CLK` and data values use the maximum-absolute stored sample in the registered half-open search windows. These are descriptive peak-time proxies only; no event-edge threshold or setup/hold criterion is frozen, so timing status remains `INCONCLUSIVE`.

| Run | Read | Stage | Data peak proxy (ps) | Clock PWL start (ps) | Internal CLK peak proxy (ps) | Clock minus data peak (ps) | Status |
|---|---:|---|---:|---:|---:|---:|---|
""" + "\n".join(rows) + "\n")
    rows_by_id = {run_id: json.loads((RUNS / run_id / "result.json").read_text(encoding="utf-8"))
                  for run_id in run_ids if (RUNS / run_id / "result.json").is_file()}
    all_pass_mechanical = len(rows_by_id) == len(run_ids) and all(
        record.get("artifact_status") == "VALID" and record.get("qa_status") == "PASS"
        for record in rows_by_id.values())
    atomic_text(ANALYSIS / "BVM4X4_V9_MIGRATION.md", f"""# BVM4X4 V9 topology migration — 80/68 ps, three reads

## Execution state

- Experiment: `{EXPERIMENT_ID}`; batch: `{BATCH_ID}`.
- Registered cases: `{', '.join(run_ids)}`.
- Physical solves completed: `{len([item for item in rows_by_id.values() if item.get('physical_solve_count') == 1])}/4`.
- Artifact/mechanical batch status: `{'PASS' if all_pass_mechanical else 'INCOMPLETE_OR_INVALID'}`.
- Arithmetic status: `INCONCLUSIVE` unless a future separately authorized review supplies an accepted classifier; this work unit does not claim multiplication PASS/Gate.
- Event counts and observed bits: `UNKNOWN`; output integrals and same-JJ phase/area are preserved as navigation/mechanical quantities.
- Scientific interpretation: NOT PERFORMED; unauthorized follow-up: none.

## Frozen topology

The new runs render the current hash-pinned V9 reference deck with only registered `.print` and `.tran` changes. Per-cell BVM→QB and D0–D6 carry/CB/T1/DFF connectivity is checked against that actual deck. All eight clocks use the existing PWL→2 Ω→DCSFQ2→JTL2 path. The 11-file source closure is copied into each run and SHA-verified. No reference V9_analysis file is modified or used as a data oracle.

## Interpretation limits

The terminal voltage area divided by Φ0 is navigation arithmetic, not an event count. Phase differences are raw radians divided by 2π only for navigation and cross-checked against the same JJ/same rows/same window voltage integral. Peak-time deltas are not a timing margin. Timestep convergence, parameter sensitivity, system Gate, and hardware behavior remain UNKNOWN.

See `BVM4X4_V9_STATIC_QA.md`, `BVM4X4_V9_FUNCTIONAL_RESULTS.csv`, `BVM4X4_V9_CLOCK_TIMING.md`, and each immutable run's `raw.csv`, QA, provenance, and plots.
""")
    run_manifests = []
    plot_pages = []
    for run_id in run_ids:
        run_dir = RUNS / run_id
        result = rows_by_id.get(run_id)
        if result is None:
            continue
        run_manifest = json.loads((run_dir / "RUN_MANIFEST.json").read_text(encoding="utf-8"))
        source_manifest = json.loads((run_dir / "source_manifest.json").read_text(encoding="utf-8"))
        plot_manifest = json.loads((run_dir / "plot_manifest.json").read_text(encoding="utf-8"))
        run_manifests.append({"run_id": run_id, "raw_path": f"runs/{run_id}/raw.csv",
                              "raw_sha256": result["raw_sha256"],
                              "deck_path": f"runs/{run_id}/deck.cir",
                              "deck_sha256": result["deck_sha256"],
                              "stimulus_path": f"runs/{run_id}/stimulus.inc",
                              "stimulus_sha256": result["stimulus_sha256"],
                              "source_manifest_sha256": sha256(run_dir / "source_manifest.json"),
                              "run_manifest_sha256": sha256(run_dir / "RUN_MANIFEST.json"),
                              "solver": run_manifest["solver"],
                              "sources": source_manifest["sources"]})
        plot_pages.extend(plot_manifest["pages"])
    atomic_json(ANALYSIS / "SOURCE_MANIFEST.json", {
        "schema": "bvm4x4-v9-work-unit-source-manifest-v1",
        "reference_deck_sha256": REFERENCE_DECK_SHA256,
        "source_sha256_by_filename": {item["filename"]: item["sha256"] for item in source_records()},
        "runs": run_manifests, "scientific_interpretation_performed": False})
    raw_manifest = {
        "schema": "bvm4x4-v9-raw-analysis-handoff-v1", "experiment_id": EXPERIMENT_ID,
        "batch_id": BATCH_ID, "analysis_scope": "mechanical raw QA and registered output/timing arithmetic only",
        "authorized_run_ids": run_ids, "runs": run_manifests,
        "window_specification": _rounds_for_stimulus(config, scenarios[0]),
        "event_classifier": None, "event_count_label": "UNKNOWN",
        "arithmetic_status": "INCONCLUSIVE", "timing_status": "INCONCLUSIVE",
        "raw_mutation": False, "interpolation_or_resampling": False,
        "scientific_interpretation_performed": False, "automatic_follow_up": False,
    }
    atomic_json(ANALYSIS / "RAW_ANALYSIS_HANDOFF_MANIFEST.json", raw_manifest)
    atomic_json(ANALYSIS / "visualization_manifest.json", {
        "schema": "bvm4x4-v9-visualization-manifest-v1", "renderer": "scripts/josim-plot2.py",
        "layout": "sep_comb", "theme": "dark", "phase_display": "rad/(2*pi) turns for navigation only",
        "pages": plot_pages, "html_included_in_zip": False})
    atomic_json(ANALYSIS / "visualization_qa.json", {
        "schema": "bvm4x4-v9-visualization-qa-v1",
        "status": "PASS" if len(plot_pages) == 3 * len(rows_by_id) else "INCOMPLETE",
        "run_count": len(rows_by_id), "page_count": len(plot_pages),
        "required_pages_per_run": 3, "html_location": "local plots/; excluded from package",
        "raw_sha256_bound": True, "responsive_external_plotly": True,
        "scientific_interpretation_performed": False})
    atomic_text(ANALYSIS / "EVIDENCE_MANIFEST.md", "# V9 Evidence Manifest\n\n" +
                "Four registered runs, each bound to immutable raw/deck/stimulus/source hashes and local classic visualization. "
                "Raw CSV is stored once per case in the case raw package; generated HTML remains local. Event counts are UNKNOWN and arithmetic/timing status is INCONCLUSIVE.\n\n" +
                "| Run | Raw SHA-256 | Deck SHA-256 | Stimulus SHA-256 | Status |\n|---|---|---|---|---|\n" +
                "\n".join(f"| {item['run_id']} | `{item['raw_sha256']}` | `{item['deck_sha256']}` | `{item['stimulus_sha256']}` | {rows_by_id[item['run_id']]['artifact_status']} |"
                        for item in run_manifests) + "\n")


def _save_reference_hashes_for_postcheck() -> dict[str, str]:
    return {path.name: sha256(path) for path in
            (REFERENCE_DECK, REFERENCE_STIMULUS, REFERENCE_RAW,
             V9_REFERENCE / "sources_frozen/01_bvm_cell_0923.cir")}


def _check_reference_postcheck(before: dict[str, str]) -> None:
    after = _save_reference_hashes_for_postcheck()
    if before != after:
        raise V9ConfigError(f"protected V9 reference files changed during task: before={before}, after={after}")


def _reserve_and_execute(config: dict[str, str], scenarios: list[dict[str, Any]], run_ids: list[str],
                         payloads: list[dict[str, Any]], static_qa: dict[str, Any],
                         sources: list[dict[str, str]], *, resume: bool = False) -> int:
    preflight_path = ANALYSIS / "PREFLIGHT.md"
    static_path = ANALYSIS / "STATIC_QA.json"
    if not preflight_path.is_file() or not static_path.is_file():
        raise V9ConfigError("V9 static dry-run must create PREFLIGHT.md and STATIC_QA.json before solving")
    if json.loads(static_path.read_text(encoding="utf-8")) != static_qa:
        raise V9ConfigError("V9 static QA identity mismatch")
    solver_info = platform._solver_info()
    if not SOLVER.is_file():
        raise V9ConfigError(f"recorded solver missing: {SOLVER}")
    if resume:
        _revise_preflight_for_resume(config, scenarios, run_ids, payloads,
                                     static_qa, sources, solver_info)
        manifest_before = json.loads(MANIFEST.read_text(encoding="utf-8"))
        batch_before = next(item for item in manifest_before["authorization_batches"]
                            if item.get("batch_id") == BATCH_ID)
        if batch_before.get("run_ids") != run_ids:
            raise V9ConfigError("resume run IDs differ from the existing authorized matrix")
        completed_ids = set(batch_before.get("completed_run_ids", []))
        rows_before = {item.get("run_id"): item for item in manifest_before.get("runs", [])}
        for completed_id in completed_ids:
            result_path = RUNS / completed_id / "result.json"
            qa_path = RUNS / completed_id / "qa.json"
            if (not result_path.is_file() or not qa_path.is_file() or
                    json.loads(result_path.read_text(encoding="utf-8")).get("artifact_status") != "VALID" or
                    json.loads(qa_path.read_text(encoding="utf-8")).get("status") != "PASS" or
                    rows_before.get(completed_id, {}).get("raw_sha256") != sha256(RUNS / completed_id / "raw.csv")):
                raise V9ConfigError(f"completed run is not artifact-valid and hash-bound; refusing resume: {completed_id}")
        pending_pairs = [(run_id, payload) for run_id, payload in zip(run_ids, payloads, strict=True)
                         if run_id not in completed_ids]
    else:
        final_preflight = _preflight_text(config, scenarios, run_ids, sources, static_qa,
                                          payloads, solver_info=solver_info)
        old_preflight = preflight_path.read_text(encoding="utf-8")
        if "Preflight state: `DRAFT_NOT_EXECUTABLE`." not in old_preflight:
            raise V9ConfigError("physical launch requires a draft preflight to finalize before the first solve")
        revision_path = ANALYSIS / "PREFLIGHT_REVISIONS.json"
        revisions = json.loads(revision_path.read_text(encoding="utf-8")) if revision_path.is_file() else {
            "schema": "bvm4x4-v9-preflight-revisions-v1", "revisions": []}
        revisions["revisions"].append({"status": "FINAL_SOLVER_IDENTITY_LOCKED_BEFORE_SOLVE",
                                         "draft_sha256": sha256(preflight_path),
                                         "final_sha256": sha256_from_text(final_preflight),
                                         "solver_version": solver_info["version"],
                                         "solver_sha256": solver_info["sha256"],
                                         "physical_solve_count_completed": 0})
        atomic_json(revision_path, revisions)
        atomic_text(preflight_path, final_preflight)
        _reserve_batch(BATCH_ID, scenarios, run_ids, static_qa, sha256(preflight_path))
        pending_pairs = list(zip(run_ids, payloads, strict=True))
    reference_before = _save_reference_hashes_for_postcheck()
    completed_this_invocation = 0
    for run_id, payload in pending_pairs:
        code, result = run_one(config, payload["scenario"], run_id, payload, solver_info)
        completed_this_invocation += int(result.get("physical_solve_count", 0))
        print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
        if code != 0:
            _check_reference_postcheck(reference_before)
            return code
    _write_batch_outputs(config, scenarios, run_ids)
    _check_reference_postcheck(reference_before)
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for batch in manifest.get("authorization_batches", []):
        if batch.get("batch_id") == BATCH_ID:
            batch["execution_status"] = "BATCH_COMPLETE_AWAITING_USER_CHATGPT_REVIEW"
            batch["mechanical_analysis_status"] = "MECHANICAL_QA_PASS"
            batch["physical_solve_count_completed"] = len(batch.get("completed_run_ids", []))
            batch["scientific_interpretation_performed"] = False
            batch["automatic_follow_up"] = False
    atomic_json(MANIFEST, manifest)
    completed_total = len(next(item for item in manifest["authorization_batches"]
                               if item.get("batch_id") == BATCH_ID).get("completed_run_ids", []))
    print(json.dumps({"status": "BATCH_COMPLETE_AWAITING_USER_CHATGPT_REVIEW",
                      "batch_id": BATCH_ID, "run_ids": run_ids,
                      "physical_solve_count": completed_total,
                      "physical_solve_count_this_invocation": completed_this_invocation,
                      "artifact_status": "VALID" if completed_total == 4 else "INCOMPLETE",
                      "arithmetic_status": "INCONCLUSIVE", "timing_status": "INCONCLUSIVE",
                      "scientific_interpretation_performed": False,
                      "automatic_follow_up": False}, ensure_ascii=False, indent=2), flush=True)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--v9-multiply-batch", action="store_true",
                      help="dry-run or execute exactly four registered product cases")
    mode.add_argument("--resume-v9-multiply-batch", action="store_true",
                      help="repair A109 postprocess from the same raw, then execute only remaining registered cases")
    mode.add_argument("--v9-case", action="store_true",
                      help="preview/execute the one A/B case in USER_CASE.env; not part of the registered four-run batch")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--set", action="append", default=[], metavar="KEY=VALUE")
    args = parser.parse_args(argv)
    try:
        if not SOLVER.is_file() or not PLOTTER.is_file() or not PLOTLY.is_file():
            raise V9ConfigError("recorded solver, classic plotter, or shared Plotly asset is missing")
        config = load_config(args.set)
        resume = bool(args.resume_v9_multiply_batch)
        batch = bool(args.v9_multiply_batch or resume)
        if batch:
            registered_values_ok(config)
        _, _, sources = _check_reference_files()
        reference_text = REFERENCE_DECK.read_text(encoding="utf-8")
        scenarios = _build_cases(config, batch)
        if resume:
            run_ids, _existing_batch = _registered_batch_run_ids(scenarios)
        else:
            if batch:
                manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
                if any(item.get("batch_id") == BATCH_ID for item in manifest.get("authorization_batches", [])):
                    raise V9ConfigError("the registered V9 batch already exists; use --resume-v9-multiply-batch")
            run_ids = _run_ids(scenarios)
        payloads = _case_payloads(config, scenarios, reference_text, sources)
        mapping_qa = _static_256_mapping_audit(
            config, reference_text, sources, payloads[0]["raw_estimate"])
        static_qa = validate_rendered(config, scenarios, payloads, reference_text, sources)
        static_qa["mapping_audit"] = mapping_qa
        static_qa["raw_estimate"] = payloads[0]["raw_estimate"]
        if static_qa["raw_estimate_guard_status"] != "PASS":
            raise V9ConfigError(f"raw estimate exceeds single-file guard: {static_qa['raw_estimate_bytes']}")
        for scenario, payload in zip(scenarios, payloads, strict=True):
            payload["case_static_qa"] = {**static_qa, "case_id": scenario["case_id"]}
        if not batch:
            if not args.dry_run:
                raise V9ConfigError("single-case physical solves are outside this task's four-run authorization")
            print("V9 SINGLE-CASE PREVIEW PASS — solver_invoked=false; no run ID reserved")
            print(f"A={scenarios[0]['a']} B={scenarios[0]['b']} -> {scenarios[0]['expected_product']} ({scenarios[0]['expected_bits_msb_first']})")
            print(f"SE={scenarios[0]['selected_se_rows']} BL={scenarios[0]['selected_bl_columns']} reads={scenarios[0]['read_times_ps']} CLK PWL={scenarios[0]['clock_pwl_starts_ps']}")
            return 0
        if resume:
            if args.dry_run:
                batch_record = _registered_batch_run_ids(scenarios)[1]
                completed = list(batch_record.get("completed_run_ids", []))
                pending = [run_id for run_id in run_ids if run_id not in completed]
                print(json.dumps({"status": "RESUME_DRY_RUN_PASS", "solver_invoked": False,
                                  "existing_batch": BATCH_ID, "registered_run_ids": run_ids,
                                  "completed_run_ids": completed, "pending_run_ids": pending,
                                  "physical_solve_count_new": 0,
                                  "raw_sha256_A109": sha256(RUNS / run_ids[0] / "raw.csv")},
                                 ensure_ascii=False, indent=2))
                return 0
            batch_record = _registered_batch_run_ids(scenarios)[1]
            for completed_id in batch_record.get("completed_run_ids", []):
                current = json.loads((RUNS / completed_id / "result.json").read_text(encoding="utf-8"))
                if current.get("artifact_status") == "VALID" and current.get("qa_status") == "PASS":
                    continue
                if (completed_id == "A109_V9_A0_B0_80P68" and
                        current.get("status") == "POSTPROCESS_FAILURE_RAW_PRESERVED" and
                        current.get("solver_exit_code") == 0):
                    repaired = repair_existing_postprocess(completed_id)
                    print(json.dumps({"postprocess_repair": repaired}, ensure_ascii=False, indent=2), flush=True)
                    continue
                raise V9ConfigError(f"completed batch run is not repairable without new physical authority: {completed_id}")
            return _reserve_and_execute(config, scenarios, run_ids, payloads, static_qa, sources, resume=True)
        _write_preflight_artifacts(config, scenarios, run_ids, payloads, static_qa, sources)
        if args.dry_run:
            return _print_dry_run(config, scenarios, run_ids, static_qa)
        return _reserve_and_execute(config, scenarios, run_ids, payloads, static_qa, sources)
    except (OSError, ValueError, KeyError, V9ConfigError, json.JSONDecodeError) as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
