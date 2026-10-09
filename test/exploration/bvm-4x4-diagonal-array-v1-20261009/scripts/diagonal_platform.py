#!/usr/bin/env python3
"""Small render/run/analyze entry point for the registered BVM 4x4 diagonal array."""

from __future__ import annotations

import argparse
import array
import csv
import hashlib
import html
import importlib.util
import json
import math
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from typing import Any

SERIES = Path(__file__).resolve().parents[1]
REPO = SERIES.parents[2]
RUNS = SERIES / "runs"
PLOTS = SERIES / "plots"
USER_CASE = SERIES / "USER_CASE.env"
STIMULUS = SERIES / "STIMULUS.env"
T1_PARAMS = SERIES / "config" / "T1_PARAMS.env"
CBU_PARAMS = SERIES / "config" / "CBU_PARAMS.env"
DFF_PARAMS = SERIES / "config" / "DFF_PARAMS.env"
D0_JTL_PARAMS = SERIES / "config" / "D0_JTL_PARAMS.env"
SOLVER = REPO / "build" / "josim-cli"
PLOTTER = REPO / "scripts" / "josim-plot2.py"
PLOTLY_ASSET = (REPO / "test/exploration/bvm-qb-cb-array-topology-v1-20260924"
                / "plots/assets/plotly.min.js")
EXPERIMENT_MANIFEST = SERIES / "experiment_manifest.json"
PHI0 = 2.067833848e-15
MAX_RAW_BYTES = 100_000_000

SOURCE_PATHS = {
    "JJMIT": "circuits/models/jjmit.cir",
    "BVM": "circuits/bvm/bvm_cell_0923.cir",
    "QB": "circuits/qb/BQ_0928.cir",
    "SJTL": "circuits/sJTL_0923.cir",
    "CB": "circuits/CB/CB_0928.cir",
    "T1_REFERENCE": "circuits/t1/t1_cell.cir",
}
SOURCE_SHA256 = {
    "JJMIT": "19862d1fd1f1f44dfa1523848d7d3b5e2594a6c5da8fdd80144b449e5312a336",
    "BVM": "ddf90076d40c0856f73dfcdcd22adeae6eddb7dd650798957a0d6c73953456b7",
    "QB": "82e6f6c7a95856c6d7bcdd28a56c009a815fc77e237a76af08fbebe45eed988a",
    "SJTL": "3cbc6889f9b4cd6b7764efa4a591f9d4dcdb0b2b86ded1f265dadabda1040688",
    "CB": "70a6af05acccb7c354799d5b1b7542c86c677970681473f559bbf0f7e4d6d370",
    "T1_REFERENCE": "828b873132b32af4fd3cebcbfa42a90fd50f15e75fdb976f1d13e07c3f1fe237",
}
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
REGISTERED_CASES = ("D3_N0", "D3_N1", "D3_N2", "D3_N3", "D3_N4",
                    "PAPER_1101_1101")
BUS400_CASES = ("BUS400_D3_N0", "BUS400_D3_N1")
BUS400_RUN_IDS = ("A007_BUS400_D3_N0", "A008_BUS400_D3_N1")
PRESET_CASES = REGISTERED_CASES + BUS400_CASES
CHAIN_PRESET_CASES = ("CHAIN_ALL_QUIET", "CHAIN_ALL_GLOBAL_CLOCK", "CHAIN_PAPER_GLOBAL_CLOCK")
PRESET_CASES = PRESET_CASES + CHAIN_PRESET_CASES
CB_DIRECT_D1_PRESET_CASES = ("CB_DIRECT_D1_ALL_CLOCK", "CB_DIRECT_D1_PAPER_CLOCK")
PRESET_CASES = PRESET_CASES + CB_DIRECT_D1_PRESET_CASES
CB_CARRY_BUFFER_D1_PRESET_CASES = (
    "CARRY_CB_D1_ALL_CLOCK", "CARRY_CB_D1_PAPER_CLOCK")
PRESET_CASES = PRESET_CASES + CB_CARRY_BUFFER_D1_PRESET_CASES
BUS400_BATCH_ID = "BVM4X4_BUS400_20261009"
BUS400_PARENT_HEAD = "3de08ba0fd5997b253269849dbc1a535786c8fd6"
STIMULUS_STAGES = ("WRITE0", "READ0", "WRITE1", "FINAL_READ")
WINDOWS_PS = {
    "WRITE0": (50.0, 61.0),
    "READ0": (70.0, 81.0),
    "WRITE1": (90.0, 101.0),
    "FINAL_READ": (110.0, 121.0),
    "POST_FINAL_READ": (121.0, 250.0),
    "FINAL_READ_RESPONSE": (110.0, 250.0),
}
PROBE_PROFILE_ALIASES = {"diagonal_core": "compact", "diagonal_focus": "focus"}
T1_ARRAY_BATCH_ID = "BVM4X4_T1_ALL_20261009"
T1_ARRAY_ANALYSIS = SERIES / "analysis" / "t1-array-20261009"
T1_ARRAY_PREFLIGHT = T1_ARRAY_ANALYSIS / "PREFLIGHT.md"
T1_ARRAY_METRIC_SPEC = T1_ARRAY_ANALYSIS / "METRIC_SPEC.json"
T1_ARRAY_SCOPE = T1_ARRAY_ANALYSIS / "WORK_UNIT.json"
T1_ARRAY_STATIC_QA = T1_ARRAY_ANALYSIS / "STATIC_QA.json"
T1_ARRAY_BATCH_MANIFEST = T1_ARRAY_ANALYSIS / "BATCH_MANIFEST.json"
T1_ARRAY_RESULTS = T1_ARRAY_ANALYSIS / "T1_ARRAY_RESULTS.json"
T1_ARRAY_TABLE = T1_ARRAY_ANALYSIS / "T1_ARRAY_TABLE.csv"
T1_CHAIN_BATCH_ID = "BVM4X4_T1_CHAIN_GLOBAL_20261009"
CB_DIRECT_D1_BATCH_ID = "BVM4X4_CB_DIRECT_D1_20261009"
CB_DIRECT_D1_ANALYSIS = SERIES / "analysis" / "cb-direct-d1-20261009"
CB_DIRECT_D1_RUN_IDS = ("A023_CB_DIRECT_D1_ALL_CLOCK", "A024_CB_DIRECT_D1_PAPER_CLOCK")
T1_CHAIN_ANALYSIS = SERIES / "analysis" / "t1-chain-20261009"
T1_CHAIN_PREFLIGHT = T1_CHAIN_ANALYSIS / "PREFLIGHT.md"
T1_CHAIN_SCOPE = T1_CHAIN_ANALYSIS / "WORK_UNIT.json"
T1_CHAIN_METRIC_SPEC = T1_CHAIN_ANALYSIS / "METRIC_SPEC.json"
T1_CHAIN_STATIC_QA = T1_CHAIN_ANALYSIS / "STATIC_QA.json"
T1_CHAIN_PROBE_MANIFEST = T1_CHAIN_ANALYSIS / "PROBE_MANIFEST.json"
T1_CHAIN_BATCH_MANIFEST = T1_CHAIN_ANALYSIS / "BATCH_MANIFEST.json"
T1_CHAIN_RESULTS = T1_CHAIN_ANALYSIS / "T1_CHAIN_RESULTS.json"
T1_CHAIN_TABLE = T1_CHAIN_ANALYSIS / "T1_CHAIN_TABLE.csv"
T1_CHAIN_METRICS_REPAIR = T1_CHAIN_ANALYSIS / "CHAIN_METRICS_REPAIR.json"
T1_CHAIN_RUN_MATRIX = (
    ("A020_CHAIN_ALL_QUIET", "CHAIN_ALL_QUIET", "1111", "1111", "QUIET", [1, 2, 3, 4, 3, 2, 1]),
    ("A021_CHAIN_ALL_GLOBAL_CLOCK", "CHAIN_ALL_GLOBAL_CLOCK", "1111", "1111", "GLOBAL_ONESHOT", [1, 2, 3, 4, 3, 2, 1]),
    ("A022_CHAIN_PAPER_GLOBAL_CLOCK", "CHAIN_PAPER_GLOBAL_CLOCK", "1101", "1101", "GLOBAL_ONESHOT", [1, 1, 1, 3, 1, 1, 1]),
)
CHAIN_WINDOWS_PS = {
    "ARRAY_FINAL_READ": (110.0, 121.0),
    "PRE_CLOCK": (121.0, 200.0),
    "BEFORE_CLOCK": (0.0, 200.0),
    "CLOCK_EDGE": (200.0, 205.0),
    "POST_CLOCK": (205.0, 300.0),
    "TOTAL": (0.0, 300.0),
}
CBU_SOURCE_PATH = "circuits/standard/MERGE.cir"
DFF_SOURCE_PATH = "circuits/standard/DFF.cir"
D0_JTL_BASE_SOURCE_PATH = "circuits/sJTL_0923.cir"
CHAIN_SOURCE_CONFIG_GROUPS = {
    "CBU_PARAMS.snapshot.env": "CBU_",
    "DFF_PARAMS.snapshot.env": "DFF_",
    "D0_JTL_PARAMS.snapshot.env": "D0_JTL_",
}
T1_ARRAY_RUN_MATRIX = (
    ("A013_T1_ALL_QUIET", "T1_ALL_QUIET", "1111", "1111", "QUIET", [1, 2, 3, 4, 3, 2, 1]),
    ("A014_T1_ALL_CLOCK", "T1_ALL_CLOCK", "1111", "1111", "PULSE", [1, 2, 3, 4, 3, 2, 1]),
    ("A015_T1_PAPER_QUIET", "T1_PAPER_QUIET", "1101", "1101", "QUIET", [1, 1, 1, 3, 1, 1, 1]),
    ("A016_T1_PAPER_CLOCK", "T1_PAPER_CLOCK", "1101", "1101", "PULSE", [1, 1, 1, 3, 1, 1, 1]),
)
T1_INTERNAL_PARAM_KEYS = (
    tuple(f"T1_J{index}_AREA" for index in range(1, 12)) +
    tuple(f"T1_RB{index}" for index in range(1, 4)) +
    tuple(f"T1_RJ{index}" for index in range(3, 12)) +
    tuple(f"T1_L{index}" for index in range(1, 18))
)
T1_JJ_COMPONENTS = tuple(f"B_J{index}" for index in range(1, 12))
T1_CRITICAL_JJS = ("B_J1", "B_J2", "B_J9", "B_J10", "B_J11")
CBU_PARAM_MAP = {
    "Phi0": "CBU_PHI0", "B0": "CBU_B0", "Ic0": "CBU_IC0", "IcRs": "CBU_ICRS", "Rsheet": "CBU_RSHEET",
    "Lsheet": "CBU_LSHEET", "LP": "CBU_LP", "IC": "CBU_IC", "LB": "CBU_LB",
    "BiasCoef": "CBU_BIASCOEF",
    **{f"B{index}": f"CBU_B{index}" for index in range(1, 8)},
    **{f"IB{index}": f"CBU_IB{index}" for index in range(1, 5)},
}
CBU_ACTIVE_ELEMENT_MAP = {
    **{f"L{index}": f"CBU_L{index}" for index in range(1, 9)},
    **{f"LP{index}": f"CBU_LP{index}" for index in (1, 2, 4, 5, 7)},
}
DFF_PARAM_MAP = {
    "Phi0": "DFF_PHI0", "B0": "DFF_B0", "Ic0": "DFF_IC0", "IcRs": "DFF_ICRS", "Rsheet": "DFF_RSHEET",
    "Lsheet": "DFF_LSHEET", "LP": "DFF_LP", "IC": "DFF_IC", "LB": "DFF_LB",
    "BiasCoef": "DFF_BIASCOEF",
    **{f"B{index}": f"DFF_B{index}" for index in range(1, 8)},
    **{f"IB{index}": f"DFF_IB{index}" for index in range(1, 5)},
}
DFF_ACTIVE_ELEMENT_MAP = {
    **{f"L{index}": f"DFF_L{index}" for index in range(1, 8)},
    **{f"LP{index}": f"DFF_LP{index}" for index in (1, 3, 4, 5, 7)},
}
T1_WINDOWS_PS = {
    "PRE_CLOCK": (110.0, 170.0),
    "CLOCK_1": (170.0, 220.0),
    "CLOCK_2": (220.0, 250.0),
    "TOTAL": (110.0, 250.0),
}
T1_CANDIDATE_MORPHOLOGY_SPEC = {
    "method": "local_voltage_extrema_relative_threshold",
    "relative_threshold": 0.25,
    "minimum_peak_separation_ps": 1.0,
    "meaning": "descriptive waveform-lobe candidates only; not event or SFQ counts",
}


class ConfigError(ValueError):
    pass


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _git_output(*args: str) -> str:
    completed = subprocess.run(["git", *args], cwd=REPO, capture_output=True,
                               text=True, check=True)
    return completed.stdout.strip()


def _json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parse_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ConfigError(f"{path}:{line_no}: expected KEY=VALUE")
        key, value = (part.strip() for part in line.split("=", 1))
        if not key or key in values:
            raise ConfigError(f"{path}:{line_no}: empty or duplicate key {key!r}")
        values[key] = value
    return values


def _merge_env(base: dict[str, str], overlay: dict[str, str], *, allow_new: bool) -> dict[str, str]:
    result = dict(base)
    unknown = set(overlay) - set(base)
    if unknown and not allow_new:
        raise ConfigError(f"unknown configuration keys: {sorted(unknown)}")
    result.update(overlay)
    return result


def _time_ps(token: str) -> Decimal:
    text = token.strip().lower()
    match = re.fullmatch(r"([+-]?(?:\d+(?:\.\d*)?|\.\d+))(p|ps)", text)
    if not match:
        raise ConfigError(f"expected picosecond time, got {token!r}")
    value = Decimal(match.group(1))
    if not value.is_finite() or value < 0:
        raise ConfigError(f"time must be finite and nonnegative: {token!r}")
    return value


def _fmt_ps(value: Decimal) -> str:
    normalized = value.normalize()
    return f"{format(normalized, 'f')}p"


def _mask_rows(value: str) -> tuple[str, ...]:
    text = value.strip().upper()
    if text == "ALL":
        return ("1111",) * 4
    rows = tuple(text.split("/"))
    if len(rows) != 4 or any(not re.fullmatch(r"[01]{4}", row) for row in rows):
        raise ConfigError("SE_ENABLE_MASK must be ALL or four row-major 4-bit rows separated by '/'")
    return rows


def _mask_active(case: dict[str, str], cell: str) -> bool:
    row, col = int(cell[1]) - 1, int(cell[3]) - 1
    mask = _mask_rows(case["SE_ENABLE_MASK"])
    return (case["ROW_BITS"][row] == "1" and case["COL_BITS"][col] == "1"
            and mask[row][col] == "1")


def _active_cells(case: dict[str, str]) -> list[str]:
    return [cell for cell in CELLS if _mask_active(case, cell)]


def _profile(case: dict[str, str]) -> str:
    value = case.get("PROBE_PROFILE", "")
    return PROBE_PROFILE_ALIASES.get(value, value)


def _spice_quantity(value: str) -> Decimal:
    match = re.fullmatch(r"\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)\s*([A-Za-z]*)\s*", value)
    if not match:
        raise ConfigError(f"invalid SPICE numeric value: {value!r}")
    suffix = match.group(2).lower()
    scales = {"": Decimal(1), "t": Decimal("1e12"), "g": Decimal("1e9"),
              "meg": Decimal("1e6"), "k": Decimal("1e3"), "m": Decimal("1e-3"),
              "u": Decimal("1e-6"), "n": Decimal("1e-9"), "p": Decimal("1e-12"),
              "f": Decimal("1e-15")}
    if suffix not in scales:
        raise ConfigError(f"unsupported SPICE suffix in {value!r}")
    result = Decimal(match.group(1)) * scales[suffix]
    if not result.is_finite():
        raise ConfigError(f"non-finite SPICE value: {value!r}")
    return result


def validate_t1_params(t1_params: dict[str, str]) -> None:
    required = set(T1_INTERNAL_PARAM_KEYS) | {
        "T1_BIAS1", "T1_BIAS2", "T1_BIAS3", "T1_BIAS3_SOURCE",
        "T1_CLK_MODE", "T1_CLK_START", "T1_CLK_PERIOD", "T1_CLK_AMPLITUDE",
        "T1_CLK_RISE", "T1_CLK_WIDTH", "T1_CLK_FALL", "T1_CLK_SERIES_R",
        "T1_CLK_QUIET_R", "T1_R_S", "T1_R_C",
    }
    missing = sorted(required - set(t1_params))
    if missing:
        raise ConfigError(f"T1_PARAMS.env missing keys: {missing}")
    if t1_params["T1_CLK_MODE"] not in {"QUIET", "PULSE"}:
        raise ConfigError("T1_CLK_MODE must be QUIET or PULSE")
    if t1_params["T1_BIAS3_SOURCE"] not in {"VOLTAGE", "CURRENT"}:
        raise ConfigError("T1_BIAS3_SOURCE must be VOLTAGE or CURRENT")
    positive_keys = set(T1_INTERNAL_PARAM_KEYS) | {
        "T1_BIAS1", "T1_BIAS2", "T1_BIAS3", "T1_CLK_AMPLITUDE",
        "T1_CLK_PERIOD", "T1_CLK_RISE", "T1_CLK_WIDTH", "T1_CLK_FALL",
        "T1_CLK_SERIES_R", "T1_CLK_QUIET_R", "T1_R_S", "T1_R_C",
    }
    for key in sorted(positive_keys):
        try:
            value = _spice_quantity(t1_params[key])
        except ConfigError as exc:
            raise ConfigError(f"{key}: {exc}") from exc
        if value <= 0:
            raise ConfigError(f"{key} must be positive")
    start = _time_ps(t1_params["T1_CLK_START"])
    period = _time_ps(t1_params["T1_CLK_PERIOD"])
    rise = _time_ps(t1_params["T1_CLK_RISE"])
    width = _time_ps(t1_params["T1_CLK_WIDTH"])
    fall = _time_ps(t1_params["T1_CLK_FALL"])
    if start < 0 or rise + width + fall >= period:
        raise ConfigError("T1 pulse start must be nonnegative and rise+width+fall must be shorter than period")


def _positive_parameter(params: dict[str, str], key: str) -> Decimal:
    if key not in params:
        raise ConfigError(f"missing physical parameter {key}")
    value = _spice_quantity(params[key])
    if value <= 0:
        raise ConfigError(f"{key} must be positive")
    return value


def validate_chain_parameters(case: dict[str, str], params: dict[str, str]) -> None:
    if case.get("CBU_TYPE") != "THmitll_MERGE":
        raise ConfigError("CBU_TYPE currently supports only the inspected THmitll_MERGE candidate")
    if case.get("DFF_TYPE") != "THmitll_DFF":
        raise ConfigError("DFF_TYPE currently supports only the inspected THmitll_DFF candidate")
    if case.get("D0_JTL_TYPE") != "D0_SJTL":
        raise ConfigError("D0_JTL_TYPE currently supports only the canonical-derived D0_SJTL candidate")
    if case.get("CBU_OVERRIDE_D1", "NONE") not in {
            "NONE", "CB_DIRECT", "CB_CARRY_BUFFER"}:
        raise ConfigError("CBU_OVERRIDE_D1 must be NONE, CB_DIRECT, or CB_CARRY_BUFFER")
    count = case.get("D0_JTL_COUNT", "")
    if not re.fullmatch(r"[1-9][0-9]*", count):
        raise ConfigError("D0_JTL_COUNT must be a positive integer")
    if case.get("T1_CHAIN_CLOCK_MODE") not in {"QUIET", "GLOBAL_ONESHOT"}:
        raise ConfigError("T1_CHAIN_CLOCK_MODE must be QUIET or GLOBAL_ONESHOT")
    start = _time_ps(case.get("T1_CHAIN_CLK_START", ""))
    if start <= Decimal("121"):
        raise ConfigError("T1_CHAIN_CLK_START must be after the fixed 121 ps FINAL_READ end")
    if start >= _time_ps(case["STOP"]):
        raise ConfigError("T1_CHAIN_CLK_START must occur before STOP")
    if _time_ps(case["STOP"]) < Decimal("300"):
        raise ConfigError("T1 chain STOP must be at least 300 ps")
    positive_keys = (
        "CBU_PHI0", "CBU_B0", "CBU_IC0", "CBU_RSHEET", "CBU_LSHEET", "CBU_LP", "CBU_IC",
        "CBU_BIASCOEF", "CBU_B1", "CBU_B2", "CBU_B3", "CBU_B4", "CBU_B5", "CBU_B6", "CBU_B7",
        "CBU_IB1", "CBU_IB2", "CBU_IB3", "CBU_IB4", "CBU_L1", "CBU_L2", "CBU_L3", "CBU_L4",
        "CBU_L5", "CBU_L6", "CBU_L7", "CBU_L8", "CBU_LP1", "CBU_LP2", "CBU_LP4", "CBU_LP5",
        "CBU_LP7", "CBU_LB", "DFF_B1", "DFF_B2", "DFF_B3", "DFF_B4", "DFF_B5", "DFF_B6",
        "DFF_PHI0", "DFF_B0", "DFF_IC0", "DFF_RSHEET", "DFF_LSHEET", "DFF_LP", "DFF_IC",
        "DFF_BIASCOEF", "DFF_B7", "DFF_IB1", "DFF_IB2", "DFF_IB3", "DFF_IB4", "DFF_L1", "DFF_L2", "DFF_L3",
        "DFF_L4", "DFF_L5", "DFF_L6", "DFF_L7", "DFF_LP1", "DFF_LP3", "DFF_LP4", "DFF_LP5",
        "DFF_LP7", "DFF_LB", "DFF_R_OUT", "DFF_CLK_QUIET_R", "D0_JTL_AREA", "D0_JTL_IB",
        "D0_JTL_L1", "D0_JTL_L2", "D0_JTL_RJ", "T1_CLK_AMPLITUDE", "T1_CLK_RISE", "T1_CLK_WIDTH",
        "T1_CLK_FALL", "T1_CLK_SERIES_R", "T1_CLK_QUIET_R", "T1_R_S", "T1_R_C",
    )
    for key in positive_keys:
        _positive_parameter(params, key)
    if _spice_quantity(params["CBU_BIASCOEF"]) > 1:
        raise ConfigError("CBU_BIASCOEF must be in (0,1]")
    if _spice_quantity(params["DFF_BIASCOEF"]) > 1:
        raise ConfigError("DFF_BIASCOEF must be in (0,1]")
    pulse_duration = sum((_time_ps(params[f"T1_CLK_{suffix}"])
                          for suffix in ("RISE", "WIDTH", "FALL")), Decimal(0))
    if pulse_duration <= 0 or start + pulse_duration + Decimal("0.02") > _time_ps(case["STOP"]):
        raise ConfigError("global one-shot clock pulse must fit completely before STOP")


def _sjtl_counts(case: dict[str, str], diagonal: str) -> tuple[int, ...]:
    key = f"SJTL_COUNT_{diagonal}"
    text = case.get(key, "")
    parts = [part.strip() for part in text.split(",")]
    if len(parts) != len(DIAGONALS[diagonal]) or any(not re.fullmatch(r"\d+", part) for part in parts):
        raise ConfigError(f"{key} must contain {len(DIAGONALS[diagonal])} comma-separated nonnegative integers")
    return tuple(int(part) for part in parts)


def _sjtl_plan(case: dict[str, str], diagonal: str) -> list[dict[str, Any]]:
    plan: list[dict[str, Any]] = []
    counts = _sjtl_counts(case, diagonal)
    for level, count in enumerate(counts, start=1):
        previous = f"MERGE_{diagonal}_L{level}"
        for stage_index in range(1, count + 1):
            # Keep the historical singleton instance and node names byte-for-byte.
            if count == 1:
                instance = f"XSJTL_{diagonal}_L{level}"
            else:
                instance = f"XSJTL_{diagonal}_L{level}_S{stage_index}"
            output = (f"SJTL_OUT_{diagonal}_L{level}" if stage_index == count else
                      f"SJTL_MID_{diagonal}_L{level}_S{stage_index}")
            plan.append({"instance": instance, "diagonal": diagonal, "level": level,
                         "stage_index": stage_index, "stage_count": count,
                         "input_node": previous, "output_node": output})
            previous = output
    return plan


def _cb_input_node(case: dict[str, str], diagonal: str, level: int) -> str:
    count = _sjtl_counts(case, diagonal)[level - 1]
    return f"SJTL_OUT_{diagonal}_L{level}" if count else f"MERGE_{diagonal}_L{level}"


def load_config(preset: str | None = None, sets: list[str] | None = None
                ) -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
    case = parse_env(USER_CASE)
    stimulus = parse_env(STIMULUS)
    t1_params = parse_env(T1_PARAMS)
    if preset:
        preset_path = SERIES / "presets" / f"{preset}.env"
        if not preset_path.is_file():
            raise ConfigError(f"unknown preset {preset!r}; choose from {', '.join(PRESET_CASES)}")
        case = _merge_env(case, parse_env(preset_path), allow_new=False)
    if case.get("OUTPUT_MODE") == "DIAGONAL_T1_CHAIN":
        for path in (CBU_PARAMS, DFF_PARAMS, D0_JTL_PARAMS):
            t1_params.update(parse_env(path))
    for assignment in sets or []:
        if "=" not in assignment:
            raise ConfigError(f"--set expects KEY=VALUE, got {assignment!r}")
        key, value = assignment.split("=", 1)
        if key in case:
            case[key] = value
        elif key in stimulus:
            stimulus[key] = value
        elif key in t1_params:
            t1_params[key] = value
        else:
            raise ConfigError(f"unknown --set key {key!r}")
    if "T1_CLK_MODE" in case:
        t1_params["T1_CLK_MODE"] = case["T1_CLK_MODE"]
    validate_config(case, stimulus, t1_params)
    return case, stimulus, t1_params


def validate_config(case: dict[str, str], stimulus: dict[str, str],
                    t1_params: dict[str, str]) -> None:
    if case.get("DRIVE_MODE") != "SHARED" or case.get("SE_TOPOLOGY") != "CELL":
        raise ConfigError("this platform requires DRIVE_MODE=SHARED and SE_TOPOLOGY=CELL")
    if case.get("SE_GATE_MODE") != "CROSSPOINT":
        raise ConfigError("this registered platform requires SE_GATE_MODE=CROSSPOINT")
    if case.get("OUTPUT_MODE") not in {"DIAGONAL_TERMINAL", "DIAGONAL_T1_INDEPENDENT", "DIAGONAL_T1_CHAIN"}:
        raise ConfigError("unknown OUTPUT_MODE")
    output_mode, t1_mode = case.get("OUTPUT_MODE"), case.get("T1_MODE")
    if not ((output_mode == "DIAGONAL_TERMINAL" and t1_mode == "OFF") or
            (output_mode == "DIAGONAL_T1_INDEPENDENT" and t1_mode == "ALL_INDEPENDENT") or
            (output_mode == "DIAGONAL_T1_CHAIN" and t1_mode == "CHAIN")):
        raise ConfigError("pair DIAGONAL_TERMINAL/OFF, DIAGONAL_T1_INDEPENDENT/ALL_INDEPENDENT, or DIAGONAL_T1_CHAIN/CHAIN")
    if ("T1_CLK_MODE" in case and
            case["T1_CLK_MODE"] != t1_params.get("T1_CLK_MODE")):
        raise ConfigError("USER_CASE.env T1_CLK_MODE and effective T1 clock mode disagree")
    if output_mode == "DIAGONAL_T1_CHAIN":
        if case.get("CBU_MODE") != "PHYSICAL_TWO_INPUT" or case.get("CARRY_MODE") != "RIPPLE":
            raise ConfigError("DIAGONAL_T1_CHAIN requires CBU_MODE=PHYSICAL_TWO_INPUT and CARRY_MODE=RIPPLE")
        if case.get("CBU_OVERRIDE_D1", "NONE") not in {
                "NONE", "CB_DIRECT", "CB_CARRY_BUFFER"}:
            raise ConfigError("CBU_OVERRIDE_D1 must be NONE, CB_DIRECT, or CB_CARRY_BUFFER")
    elif case.get("CBU_MODE") != "OFF" or case.get("CARRY_MODE", "NONE") != "NONE":
        raise ConfigError("terminal and independent-T1 modes require CBU_MODE=OFF and CARRY_MODE=NONE")
    elif case.get("CBU_OVERRIDE_D1", "NONE") != "NONE":
        raise ConfigError("CBU_OVERRIDE_D1 is supported only in DIAGONAL_T1_CHAIN mode")
    if output_mode == "DIAGONAL_T1_INDEPENDENT":
        if _profile(case) != "t1_array_focus":
            raise ConfigError("DIAGONAL_T1_INDEPENDENT requires PROBE_PROFILE=t1_array_focus; "
                              "standard focus probes request R_TERM loads and do not capture T1 outputs")
        allowed_profiles = {"t1_array_focus"}
    elif output_mode == "DIAGONAL_T1_CHAIN":
        if _profile(case) != "t1_chain_focus":
            raise ConfigError("DIAGONAL_T1_CHAIN requires PROBE_PROFILE=t1_chain_focus")
        allowed_profiles = {"t1_chain_focus"}
    else:
        allowed_profiles = {"compact", "focus", "debug"}
    if _profile(case) not in allowed_profiles:
        raise ConfigError(f"PROBE_PROFILE must be one of {sorted(allowed_profiles)}")
    if case.get("FOCUS_DIAGONAL") not in DIAGONALS:
        raise ConfigError("FOCUS_DIAGONAL must be D0..D6")
    if case.get("OUTPUT_MODE") == "DIAGONAL_T1_CHAIN" and case.get("FOCUS_STAGE") not in DIAGONALS:
        raise ConfigError("FOCUS_STAGE must be D0..D6 in chain mode")
    for key in ("ROW_BITS", "COL_BITS"):
        if not re.fullmatch(r"[01]{4}", case.get(key, "")):
            raise ConfigError(f"{key} must contain exactly four binary digits")
    _mask_rows(case.get("SE_ENABLE_MASK", ""))
    for diagonal in DIAGONALS:
        _sjtl_counts(case, diagonal)
    if float(case.get("ROW_WL_WRITE_AMPLITUDE", "0").removesuffix("u")) <= 0:
        raise ConfigError("ROW_WL_WRITE_AMPLITUDE must be positive")
    if float(case.get("COL_BL_WRITE_AMPLITUDE", "0").removesuffix("u")) <= 0:
        raise ConfigError("COL_BL_WRITE_AMPLITUDE must be positive")
    if float(case.get("ROW_WL_READ_AMPLITUDE", "0").removesuffix("u")) <= 0:
        raise ConfigError("ROW_WL_READ_AMPLITUDE must be positive")
    if float(case.get("COL_SE_READ_AMPLITUDE", "0").removesuffix("u")) <= 0:
        raise ConfigError("COL_SE_READ_AMPLITUDE must be positive")
    dt = case.get("DT", "")
    if not re.fullmatch(r"(?:\d+(?:\.\d*)?|\.\d+)p", dt):
        raise ConfigError("DT must be a positive ps value such as 0.01p")
    if output_mode != "DIAGONAL_T1_CHAIN" and _time_ps(case.get("STOP", "0p")) < Decimal("250"):
        raise ConfigError("STOP must cover the preregistered final-read response through 250 ps")
    for stage in STIMULUS_STAGES:
        for suffix in ("START", "RISE", "HOLD", "FALL"):
            key = f"{stage}_{suffix}"
            if key not in stimulus:
                raise ConfigError(f"missing stimulus key {key}")
            _time_ps(stimulus[key])
    schedule = []
    for stage in STIMULUS_STAGES:
        start = _time_ps(stimulus[f"{stage}_START"])
        rise = _time_ps(stimulus[f"{stage}_RISE"])
        hold = _time_ps(stimulus[f"{stage}_HOLD"])
        fall = _time_ps(stimulus[f"{stage}_FALL"])
        if rise <= 0 or hold <= 0 or fall <= 0:
            raise ConfigError(f"{stage} rise/hold/fall must be positive")
        end = start + rise + hold + fall
        if end > _time_ps(case["STOP"]):
            raise ConfigError(f"{stage} ends after STOP")
        schedule.append((stage, start, end))
    for (_, _, prev_end), (stage, start, _) in zip(schedule, schedule[1:]):
        if start < prev_end:
            raise ConfigError(f"stimulus overlap before {stage}")
    validate_t1_params(t1_params)
    if output_mode == "DIAGONAL_T1_CHAIN":
        validate_chain_parameters(case, t1_params)


def verify_sources() -> dict[str, dict[str, str]]:
    records = {}
    for role, rel in SOURCE_PATHS.items():
        path = REPO / rel
        digest = sha256(path)
        if digest != SOURCE_SHA256[role]:
            raise ConfigError(f"canonical source SHA mismatch for {role}: {digest}")
        records[role] = {"path": rel, "sha256": digest,
                         "mode": "REFERENCE_ONLY" if role == "T1_REFERENCE" else "DIRECT_CANONICAL_INCLUDE"}
    return records


def render_t1_source(t1_params: dict[str, str]) -> tuple[str, dict[str, Any]]:
    """Build a run-local T1 source from the canonical body and effective T1_PARAMS."""
    canonical_path = REPO / SOURCE_PATHS["T1_REFERENCE"]
    canonical_text = canonical_path.read_text(encoding="utf-8")
    rendered_lines = []
    used: set[str] = set()
    for raw_line in canonical_text.splitlines():
        stripped = raw_line.strip()
        parts = stripped.split()
        if not parts or stripped.startswith("*"):
            rendered_lines.append(raw_line)
            continue
        element = parts[0].upper()
        key = None
        if re.fullmatch(r"L\d+", element):
            key = f"T1_{element}"
            if key in t1_params:
                parts[-1] = t1_params[key]
        elif re.fullmatch(r"B_J\d+", element):
            key = f"T1_{element[2:]}_AREA"
            if key in t1_params:
                parts[-1] = f"area={t1_params[key]}"
        elif re.fullmatch(r"RB\d+", element):
            key = f"T1_{element}"
            if key in t1_params:
                parts[-1] = t1_params[key]
        elif re.fullmatch(r"R_J\d+", element):
            key = f"T1_RJ{element[3:]}"
            if key in t1_params:
                parts[-1] = t1_params[key]
        if key and key in t1_params:
            used.add(key)
            rendered_lines.append(" ".join(parts))
        else:
            rendered_lines.append(raw_line)
    if used != set(T1_INTERNAL_PARAM_KEYS):
        raise ConfigError("T1 tunable renderer did not consume the complete internal parameter set: "
                          f"missing={sorted(set(T1_INTERNAL_PARAM_KEYS) - used)}")
    rendered_text = "\n".join(rendered_lines) + "\n"

    def subckt_body(text: str, *, topology_only: bool = False) -> list[str]:
        body = []
        inside = False
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("*"):
                continue
            parts = stripped.split()
            if parts[0].lower() == ".subckt" and len(parts) > 1 and parts[1].upper() == "T1":
                inside = True
            if inside:
                if topology_only and parts[0].upper() not in {".SUBCKT", ".ENDS"} and re.match(r"^[A-Z_]+\d+$", parts[0].upper()):
                    parts[-1] = "<VALUE>"
                body.append(" ".join(parts).upper())
            if inside and parts[0].lower() == ".ends":
                break
        return body

    if subckt_body(canonical_text, topology_only=True) != subckt_body(rendered_text, topology_only=True):
        raise ConfigError("rendered T1 changed canonical nodes, device names, or pin order")
    rendered_sha = hashlib.sha256(rendered_text.encode("utf-8")).hexdigest()
    return rendered_text, {
        "path": "sources/t1_cell_tunable.cir",
        "canonical_path": SOURCE_PATHS["T1_REFERENCE"],
        "canonical_sha256": sha256(canonical_path),
        "rendered_sha256": rendered_sha,
        "topology_equivalent": True,
        "default_body_equivalent_to_canonical": subckt_body(canonical_text) == subckt_body(rendered_text),
        "parameters_consumed": sorted(used),
    }


def _normalized_subckt_body(text: str, subckt_name: str) -> list[str]:
    body = []
    inside = False
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("*"):
            continue
        parts = stripped.split()
        if parts[0].lower() == ".subckt" and len(parts) > 1 and parts[1].casefold() == subckt_name.casefold():
            inside = True
        if inside:
            body.append(" ".join(parts))
        if inside and parts[0].lower() == ".ends":
            break
    return body


def _render_parametric_coldflux_source(path: Path, subckt: str, params: dict[str, str],
                                       param_map: dict[str, str],
                                       element_map: dict[str, str], *,
                                       output_path: str,
                                       syntax_replacements: tuple[tuple[str, str], ...] = ()) -> tuple[str, dict[str, Any]]:
    """Render only declared .param values and active L/LP element values."""
    original = path.read_text(encoding="utf-8")
    original_for_compare = original
    for before, after in syntax_replacements:
        original_for_compare = original_for_compare.replace(before, after)
    rendered_lines = []
    consumed: set[str] = set()
    inside = False
    normalized_param_map = {key.casefold(): value for key, value in param_map.items()}
    for raw_line in original.splitlines():
        stripped = raw_line.strip()
        if stripped.lower().startswith(".subckt "):
            inside = stripped.split()[1].casefold() == subckt.casefold()
        if not inside or not stripped or stripped.startswith("*"):
            rendered_lines.append(raw_line)
            continue
        parts = stripped.split()
        if parts[0].lower() == ".param" and len(parts) >= 2 and "=" in parts[1]:
            name, _value = parts[1].split("=", 1)
            config_key = normalized_param_map.get(name.casefold())
            if config_key:
                if config_key not in params:
                    raise ConfigError(f"missing rendered source parameter {config_key}")
                parts[1] = f"{name}={params[config_key]}"
                consumed.add(config_key)
                rendered_lines.append(" ".join(parts))
            else:
                rendered_lines.append(raw_line.replace("0.7’", "0.7"))
            continue
        element = parts[0].upper()
        config_key = element_map.get(element)
        if config_key:
            if config_key not in params:
                raise ConfigError(f"missing active device value {config_key}")
            parts[-1] = params[config_key]
            consumed.add(config_key)
            rendered_lines.append(" ".join(parts))
        else:
            rendered_lines.append(raw_line.replace("0.7’", "0.7"))
        if stripped.lower().startswith(".ends"):
            inside = False
    rendered = "\n".join(rendered_lines) + "\n"
    required = set(param_map.values()) | set(element_map.values())
    if consumed != required:
        raise ConfigError(f"source renderer parameter coverage mismatch for {subckt}: "
                          f"missing={sorted(required-consumed)} extra={sorted(consumed-required)}")
    if "’" in "\n".join(line for line in rendered.splitlines() if line.strip() and not line.lstrip().startswith("*")):
        raise ConfigError(f"non-ASCII quote remains in active {subckt} source")
    canonical_body = _normalized_subckt_body(original_for_compare, subckt)
    rendered_body = _normalized_subckt_body(rendered, subckt)
    canonical_topology = []
    rendered_topology = []
    for body, target in ((canonical_body, canonical_topology), (rendered_body, rendered_topology)):
        for item in body:
            parts = item.split()
            if parts[0].lower() == ".param":
                target.append((parts[0] + " " + parts[1].split("=", 1)[0]).upper())
            elif parts[0].lower() in {".subckt", ".ends"}:
                target.append(item.upper())
            else:
                target.append(" ".join(parts[:-1]).upper() + " <VALUE>")
    if canonical_topology != rendered_topology:
        raise ConfigError(f"local {subckt} render changed device topology, nodes, or port order")
    equivalence = rendered_body == canonical_body
    return rendered, {
        "path": output_path,
        "canonical_path": path.relative_to(REPO).as_posix(),
        "canonical_sha256": sha256(path),
        "rendered_sha256": hashlib.sha256(rendered.encode("utf-8")).hexdigest(),
        "subcircuit": subckt,
        "ports": list(_normalized_subckt_body(rendered, subckt)[0].split()[2:]),
        "parameters_consumed": sorted(consumed),
        "device_topology_equivalent": canonical_topology == rendered_topology,
        "default_body_equivalent_after_registered_syntax_fix": equivalence,
        "syntax_replacements": [{"before": before, "after": after, "scope": "experiment-local source only"}
                                 for before, after in syntax_replacements],
    }


def render_cbu_source(params: dict[str, str]) -> tuple[str, dict[str, Any]]:
    return _render_parametric_coldflux_source(
        REPO / CBU_SOURCE_PATH, "THmitll_MERGE", params, CBU_PARAM_MAP,
        CBU_ACTIVE_ELEMENT_MAP, output_path="sources/cbu_tunable.cir",
        syntax_replacements=(("BiasCoef=0.7’", "BiasCoef=0.7"),))


def render_dff_source(params: dict[str, str]) -> tuple[str, dict[str, Any]]:
    return _render_parametric_coldflux_source(
        REPO / DFF_SOURCE_PATH, "THmitll_DFF", params, DFF_PARAM_MAP,
        DFF_ACTIVE_ELEMENT_MAP, output_path="sources/dff_tunable.cir")


def render_d0_jtl_source(params: dict[str, str]) -> tuple[str, dict[str, Any]]:
    path = REPO / D0_JTL_BASE_SOURCE_PATH
    original = path.read_text(encoding="utf-8")
    rendered_lines = []
    consumed = set()
    inside = False
    for raw_line in original.splitlines():
        stripped = raw_line.strip()
        if stripped.lower().startswith(".model jjmit"):
            continue
        if stripped.lower().startswith(".subckt "):
            inside = stripped.split()[1].casefold() == "sjtl"
            if inside:
                rendered_lines.append(".subckt D0_JTL IN OUT")
                continue
        if inside and stripped.lower().startswith(".model "):
            continue
        if inside and stripped and not stripped.startswith("*"):
            parts = stripped.split()
            key = {"BJ1": "D0_JTL_AREA", "RJ1": "D0_JTL_RJ", "L1": "D0_JTL_L1",
                   "L2": "D0_JTL_L2", "IB1": "D0_JTL_IB"}.get(parts[0].upper())
            if key:
                value = params.get(key)
                if value is None:
                    raise ConfigError(f"missing D0 JTL parameter {key}")
                if parts[0].upper() == "BJ1":
                    parts[-1] = f"area={value}"
                elif parts[0].upper() == "IB1":
                    parts[-1] = parts[-1].replace("190u)", f"{value})")
                else:
                    parts[-1] = value
                consumed.add(key)
                rendered_lines.append(" ".join(parts))
                continue
            if stripped.lower().startswith(".ends"):
                rendered_lines.append(".ends D0_JTL")
                inside = False
                continue
        rendered_lines.append(raw_line)
    rendered = "\n".join(rendered_lines) + "\n"
    required = {"D0_JTL_AREA", "D0_JTL_RJ", "D0_JTL_L1", "D0_JTL_L2", "D0_JTL_IB"}
    if consumed != required:
        raise ConfigError(f"D0 JTL parameter coverage mismatch: missing={sorted(required-consumed)}")
    if ".model jjmit" in rendered.lower():
        raise ConfigError("experiment-local D0 JTL must reuse the single shared jjmit model")
    return rendered, {"path": "sources/d0_jtl_tunable.cir",
                      "canonical_path": D0_JTL_BASE_SOURCE_PATH,
                      "canonical_sha256": sha256(path),
                      "rendered_sha256": hashlib.sha256(rendered.encode("utf-8")).hexdigest(),
                      "subcircuit": "D0_JTL", "ports": ["IN", "OUT"],
                      "parameters_consumed": sorted(consumed),
                      "canonical_sJTL_defaults_match": all(params[key] == expected for key, expected in (
                          ("D0_JTL_AREA", "2.5"), ("D0_JTL_IB", "190u"),
                          ("D0_JTL_L1", "2.5p"), ("D0_JTL_L2", "2.5p"), ("D0_JTL_RJ", "4"))),
                      "shared_jjmit_model": True}


def _source_manifest(sources: dict[str, dict[str, str]]) -> dict[str, Any]:
    return {"schema": "bvm-4x4-diagonal-source-manifest-v1",
            "canonical_sources_modified": False, "sources": sources,
            "scientific_interpretation_performed": False}


def topology_manifest(sources: dict[str, dict[str, str]], case: dict[str, str],
                      t1_params: dict[str, str] | None = None) -> dict[str, Any]:
    chain_active = case["OUTPUT_MODE"] == "DIAGONAL_T1_CHAIN"
    t1_active = case["OUTPUT_MODE"] in {"DIAGONAL_T1_INDEPENDENT", "DIAGONAL_T1_CHAIN"}
    cells = []
    for cell in CELLS:
        row, col = int(cell[1]), int(cell[3])
        diagonal = next(name for name, items in DIAGONALS.items() if cell in items)
        level = DIAGONALS[diagonal].index(cell) + 1
        cells.append({"cell": cell, "row": row, "column": col,
                      "bvm_instance": f"XBVM_{cell}", "qb_instance": f"XBQ_{cell}",
                      "wl_node": f"WL_R{row}", "bl_node": f"BL_C{col}",
                      "se_node": f"SE_{cell}", "sl_node": f"SL_{cell}",
                      "diagonal": diagonal, "level": level,
                      "qb_output_node": f"MERGE_{diagonal}_L{level}"})
    diagonal_records = {}
    for name, cells_in_diagonal in DIAGONALS.items():
        counts = _sjtl_counts(case, name)
        diagonal_records[name] = {
            "cells": list(cells_in_diagonal), "levels": len(cells_in_diagonal),
            "sjtl_count_by_level": list(counts), "sjtl_count": sum(counts),
            "post_cb_count": len(cells_in_diagonal),
            "sjtl_instances": _sjtl_plan(case, name),
            "cb_instances": [f"XCB_{name}_L{level}" for level in range(1, len(cells_in_diagonal) + 1)],
            "output_node": f"DOUT_{name}",
            "termination_ohm": None if t1_active else 2,
        }
    result = {"schema": "bvm-4x4-diagonal-topology-v2", "rows": 4, "columns": 4,
              "drive_mode": "SHARED", "se_topology": "CELL", "se_gate_mode": "CROSSPOINT",
              "cells": cells,
              "diagonals": diagonal_records,
              "source_sha256": {role: item["sha256"] for role, item in sources.items()},
              "output_mode": case["OUTPUT_MODE"], "t1_mode": case["T1_MODE"],
              "cbu_mode": case.get("CBU_MODE", "OFF"),
              "merge_semantics": "serial shared electrical nodes; no MERGE subcircuit",
              "sJTL_parameter_semantics": "SJTL_COUNT_Dn lists serial sJTL instances after each MERGE level and before its single CB; zero connects MERGE directly to CB",
              "effective_sjtl_counts": {name: list(_sjtl_counts(case, name)) for name in DIAGONALS},
              "effective_bus_source_setpoints": {
                  "ROW_WL_WRITE_AMPLITUDE": case["ROW_WL_WRITE_AMPLITUDE"],
                  "COL_BL_WRITE_AMPLITUDE": case["COL_BL_WRITE_AMPLITUDE"],
                  "ROW_WL_READ_AMPLITUDE": case["ROW_WL_READ_AMPLITUDE"],
                  "COL_SE_READ_AMPLITUDE": case["COL_SE_READ_AMPLITUDE"],
                  "semantics": "shared bus source total setpoints; per-cell branch currents are measured from raw",
              },
              "probe_profile": _profile(case),
              "scientific_interpretation_performed": False}
    if t1_active:
        result["t1_channels"] = {name: {
            "instance": f"XT1_{name}", "input_node": f"T1_I_{name}",
            "link_element": f"V_T1_LINK_{name}", "clock_node": f"CLK_{name}",
            "sum_node": f"S_{name}", "carry_node": f"C_{name}",
            "independent_bias_nodes": [f"N_BIAS{index}_{name}" for index in range(1, 4)],
            "parallel_terminal_ohm": None,
            "input_path": ("DOUT_D0 -> physical D0 JTL -> T1_D0" if chain_active and name == "D0"
                           else f"DOUT_{name} + C_D{int(name[1])-1} -> physical CBU_{name} -> T1_{name}"
                           if chain_active else f"DOUT_{name} -> T1_{name}"),
        } for name in DIAGONALS}
        result["t1_channel_count"] = 7
        result["t1_clock_mode"] = (case.get("T1_CHAIN_CLOCK_MODE") if chain_active else
                                   (t1_params or {}).get("T1_CLK_MODE", "UNKNOWN"))
        result["t1_biases"] = {key: (t1_params or {}).get(key) for key in
                               ("T1_BIAS1", "T1_BIAS2", "T1_BIAS3", "T1_BIAS3_SOURCE")}
        result["t1_output_loads_ohm"] = {
            "S": (t1_params or {}).get("T1_R_S"), "C": (t1_params or {}).get("T1_R_C")}
        result["t1_clock_parameters"] = {key: (t1_params or {}).get(key) for key in (
            "T1_CLK_START", "T1_CLK_PERIOD", "T1_CLK_AMPLITUDE", "T1_CLK_RISE",
            "T1_CLK_WIDTH", "T1_CLK_FALL", "T1_CLK_SERIES_R", "T1_CLK_QUIET_R")}
        if chain_active:
            result["t1_clock_parameters"].update({
                "T1_CHAIN_CLOCK_MODE": case["T1_CHAIN_CLOCK_MODE"],
                "T1_CHAIN_CLK_START": case["T1_CHAIN_CLK_START"],
                "clock_scope": "seven independent T1 drivers plus one independent DFF driver",
                "pulse_repeat": False,
            })
    if chain_active:
        result.update({
            "carry_mode": case["CARRY_MODE"],
            "cbu_type": case["CBU_TYPE"],
            "cbu_override_d1": case.get("CBU_OVERRIDE_D1", "NONE"),
            "cbu_count": 6,
            "cbu_instances": ([f"XCBU_D{index}" for index in range(1, 7)]
                              if case.get("CBU_OVERRIDE_D1", "NONE") != "CB_CARRY_BUFFER"
                              else [f"XCBU_D{index}" for index in range(2, 7)] + ["XCB_CARRY_D1"]),
            "cbu_type_by_stage": {f"D{index}": (
                                      "CB" if index == 1 and case.get("CBU_OVERRIDE_D1") == "CB_DIRECT"
                                      else "CB_CARRY_BUFFER" if index == 1 and
                                      case.get("CBU_OVERRIDE_D1") == "CB_CARRY_BUFFER"
                                      else case["CBU_TYPE"])
                                  for index in range(1, 7)},
            "cbu_input_nodes": {
                f"D{index}": ({"A": "DOUT_D1", "B": "C_D0",
                               "A_SENSOR": "V_CBU_A_D1", "B_SENSOR": "V_CARRY_IN_D1",
                               "B_CB_INPUT": "CARRY_CB_IN_D1", "B_CB_OUTPUT": "CARRY_CB_OUT_D1",
                               "B_OUTPUT_SENSOR": "V_CBU_B_D1", "JOIN": "CBU_JOIN_D1",
                               "T1_INPUT": "T1_I_D1",
                               "input_semantics": "C_D0 passes through one canonical CB; DOUT_D1 and CB output share the T1 input node"}
                              if index == 1 and case.get("CBU_OVERRIDE_D1", "NONE") == "CB_CARRY_BUFFER"
                              else {"A": "DOUT_D1", "B": "C_D0",
                                    "JOIN": "CBU_JOIN_D1", "IN": "CBU_JOIN_D1",
                                    "OUT": "CBU_OUT_D1", "input_semantics": "two sensed branches share one physical CB input node"}
                              if index == 1 and case.get("CBU_OVERRIDE_D1", "NONE") == "CB_DIRECT"
                              else {"A": f"DOUT_D{index}", "B": f"C_D{index-1}",
                                    "OUT": f"CBU_OUT_D{index}"})
                for index in range(1, 7)},
            "cbu_d1_canonical_cb": ({"instance": "XCBU_D1", "source_path": SOURCE_PATHS["CB"],
                                     "source_sha256": sources["CBU_D1_DIRECT"]["sha256"], "ports": ["IN", "OUT"],
                                     "intermediate_jtl_or_sjtl": False,
                                     "physical_input_node": "CBU_JOIN_D1"}
                                    if case.get("CBU_OVERRIDE_D1", "NONE") == "CB_DIRECT" else None),
            "cbu_d1_carry_buffer": ({"instance": "XCB_CARRY_D1", "source_path": SOURCE_PATHS["CB"],
                                     "source_sha256": sources["CBU_D1_CARRY_BUFFER"]["sha256"],
                                     "ports": ["IN", "OUT"], "input_node": "CARRY_CB_IN_D1",
                                     "output_node": "CARRY_CB_OUT_D1", "join_node": "CBU_JOIN_D1",
                                     "dout_branch": "DOUT_D1 -> V_CBU_A_D1 -> CBU_JOIN_D1",
                                     "carry_branch": "C_D0 -> V_CARRY_IN_D1 -> XCB_CARRY_D1 -> V_CBU_B_D1 -> CBU_JOIN_D1",
                                     "intermediate_jtl_or_sjtl": False}
                                    if case.get("CBU_OVERRIDE_D1", "NONE") == "CB_CARRY_BUFFER" else None),
            "d0_jtl_type": case["D0_JTL_TYPE"],
            "d0_jtl_count": int(case["D0_JTL_COUNT"]),
            "d0_jtl_instances": [f"XJTL_D0_{index}" for index in range(1, int(case["D0_JTL_COUNT"])+1)],
            "dff_type": case["DFF_TYPE"],
            "dff_instance": "XDFF",
            "dff_data_node": "DFF_IN",
            "dff_output_node": "DFF_O",
            "sum_load_ohm": (t1_params or {}).get("T1_R_S"),
            "carry_loads_ohm": {f"C_D{index}": None for index in range(7)},
            "dff_output_load_ohm": (t1_params or {}).get("DFF_R_OUT"),
            "carry_bit_map": {f"S_D{index}": f"product_bit_{index}" for index in range(7)} |
                             {"DFF_O": "product_bit_7"},
            "carry_links": {f"C_D{index}": ("V_CARRY_IN_D1 -> XCB_CARRY_D1 -> V_CBU_B_D1 -> CBU_JOIN_D1"
                                               if index == 0 and case.get("CBU_OVERRIDE_D1", "NONE") == "CB_CARRY_BUFFER"
                                                else "V_CBU_B_D1 -> CBU_JOIN_D1" if index == 0 and
                                                case.get("CBU_OVERRIDE_D1", "NONE") == "CB_DIRECT"
                                                else f"CBU_D{index+1}.B") for index in range(6)} |
                            {"C_D6": "DFF_IN"},
            "clock_drivers": [*(f"CLK_D{index}" for index in range(7)), "CLK_DFF"],
            "clock_repeat": False,
        })
    return result


def _spice_include(run_dir: Path, relpath: str) -> str:
    return Path(os.path.relpath(REPO / relpath, run_dir)).as_posix()


def _global_clock_points(case: dict[str, str], params: dict[str, str]) -> list[tuple[str, str]]:
    start = _time_ps(case["T1_CHAIN_CLK_START"])
    rise = _time_ps(params["T1_CLK_RISE"])
    width = _time_ps(params["T1_CLK_WIDTH"])
    fall = _time_ps(params["T1_CLK_FALL"])
    return [("0p", "0"), (_fmt_ps(start), "0"), (_fmt_ps(start + rise), params["T1_CLK_AMPLITUDE"]),
            (_fmt_ps(start + rise + width), params["T1_CLK_AMPLITUDE"]),
            (_fmt_ps(start + rise + width + fall), "0")]


def _render_chain_network(case: dict[str, str], params: dict[str, str]) -> list[str]:
    lines = ["", "* Physical ripple chain: D0-JTL -> T1_D0; Dk + C(k-1) -> CBU_Dk -> T1_Dk."]
    for diagonal in DIAGONALS:
        for index in (1, 2):
            lines.append(f"V_BIAS{index}_{diagonal} N_BIAS{index}_{diagonal} 0 DC {params[f'T1_BIAS{index}']}")
        if params["T1_BIAS3_SOURCE"] == "VOLTAGE":
            lines.append(f"V_BIAS3_{diagonal} N_BIAS3_{diagonal} 0 DC {params['T1_BIAS3']}")
        else:
            lines.append(f"I_BIAS3_{diagonal} 0 N_BIAS3_{diagonal} DC {params['T1_BIAS3']}")
        lines.append(f"R_S_{diagonal} S_{diagonal} 0 {params['T1_R_S']}")
        if case["T1_CHAIN_CLOCK_MODE"] == "GLOBAL_ONESHOT":
            points = _global_clock_points(case, params)
            pwl = " ".join(f"{time} {value}" for time, value in points)
            lines.append(f"V_TRIG_CLK_{diagonal} CLK_RAW_{diagonal} 0 PWL({pwl})")
            lines.append(f"R_TRIG_CLK_{diagonal} CLK_RAW_{diagonal} CLK_{diagonal} {params['T1_CLK_SERIES_R']}")
        else:
            lines.append(f"R_CLK_QUIET_{diagonal} CLK_{diagonal} 0 {params['T1_CLK_QUIET_R']}")
        lines.append(f"XT1_{diagonal} T1_I_{diagonal} CLK_{diagonal} S_{diagonal} C_{diagonal} "
                     f"N_BIAS1_{diagonal} N_BIAS2_{diagonal} N_BIAS3_{diagonal} T1")

    lines.extend(("", "* D0 physical entrance JTL; every stage has series 0-V branch-current sensors."))
    count = int(case["D0_JTL_COUNT"])
    for stage in range(1, count + 1):
        upstream = "DOUT_D0" if stage == 1 else f"D0_JTL_NODE_{stage-1}"
        input_node = f"D0_JTL_IN_{stage}"
        output_node = f"D0_JTL_OUT_{stage}"
        downstream = "T1_I_D0" if stage == count else f"D0_JTL_NODE_{stage}"
        output_link = "V_T1_LINK_D0" if stage == count else f"V_D0_JTL_OUT_{stage}"
        lines.append(f"V_D0_JTL_IN_{stage} {upstream} {input_node} 0")
        lines.append(f"XJTL_D0_{stage} {input_node} {output_node} D0_JTL")
        lines.append(f"{output_link} {output_node} {downstream} 0")

    if case.get("CBU_OVERRIDE_D1", "NONE") == "CB_DIRECT":
        lines.extend(("", "* D1 shared-node CB_0928 candidate; D2-D6 remain configured THmitll_MERGE."))
    elif case.get("CBU_OVERRIDE_D1", "NONE") == "CB_CARRY_BUFFER":
        lines.extend(("", "* D1 carry-side CB_0928 buffer; DOUT_D1 and buffered C_D0 outputs join directly."))
    else:
        lines.extend(("", "* Two-input physical CBU candidate is distinct from array XCB_* single-input CB."))
    for index in range(1, 7):
        if index == 1 and case.get("CBU_OVERRIDE_D1", "NONE") == "CB_CARRY_BUFFER":
            lines.extend((
                "V_CBU_A_D1 DOUT_D1 CBU_JOIN_D1 0",
                "V_CARRY_IN_D1 C_D0 CARRY_CB_IN_D1 0",
                "XCB_CARRY_D1 CARRY_CB_IN_D1 CARRY_CB_OUT_D1 CB",
                "V_CBU_B_D1 CARRY_CB_OUT_D1 CBU_JOIN_D1 0",
                "V_T1_LINK_D1 CBU_JOIN_D1 T1_I_D1 0",
            ))
            continue
        if index == 1 and case.get("CBU_OVERRIDE_D1", "NONE") == "CB_DIRECT":
            lines.extend((
                "V_CBU_A_D1 DOUT_D1 CBU_JOIN_D1 0",
                "V_CBU_B_D1 C_D0 CBU_JOIN_D1 0",
                "XCBU_D1 CBU_JOIN_D1 CBU_OUT_D1 CB",
                "V_T1_LINK_D1 CBU_OUT_D1 T1_I_D1 0",
            ))
            continue
        lines.append(f"V_CBU_A_D{index} DOUT_D{index} CBU_A_D{index} 0")
        lines.append(f"V_CBU_B_D{index} C_D{index-1} CBU_B_D{index} 0")
        lines.append(f"XCBU_D{index} CBU_A_D{index} CBU_B_D{index} CBU_OUT_D{index} {case['CBU_TYPE']}")
        lines.append(f"V_T1_LINK_D{index} CBU_OUT_D{index} T1_I_D{index} 0")

    lines.extend(("", "* C0-C5 directly drive the next CBU; C6 directly drives the DFF data input."))
    lines.append("V_DFF_DATA C_D6 DFF_IN 0")
    lines.append(f"R_DFF_OUT DFF_O 0 {params['DFF_R_OUT']}")
    lines.append(f"XDFF DFF_IN CLK_DFF DFF_O {case['DFF_TYPE']}")
    if case["T1_CHAIN_CLOCK_MODE"] == "GLOBAL_ONESHOT":
        points = _global_clock_points(case, params)
        pwl = " ".join(f"{time} {value}" for time, value in points)
        lines.append(f"V_TRIG_CLK_DFF CLK_RAW_DFF 0 PWL({pwl})")
        lines.append(f"R_TRIG_CLK_DFF CLK_RAW_DFF CLK_DFF {params['T1_CLK_SERIES_R']}")
    else:
        lines.append(f"R_CLK_QUIET_DFF CLK_DFF 0 {params['DFF_CLK_QUIET_R']}")
    return lines


def subckt_pins(path: Path, name: str) -> tuple[str, ...]:
    found = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.lower().startswith(".subckt "):
            fields = stripped.split()
            if len(fields) > 1 and fields[1].casefold() == name.casefold():
                found.append(tuple(fields[2:]))
    if len(found) != 1:
        raise ConfigError(f"expected exactly one .subckt {name} in {path}; found {len(found)}")
    return found[0]


def _stage_levels(case: dict[str, str], stimulus: dict[str, str], cell: str,
                  branch: str) -> dict[str, str]:
    row, col = int(cell[1]) - 1, int(cell[3]) - 1
    selected_row = case["ROW_BITS"][row] == "1"
    selected_col = case["COL_BITS"][col] == "1"
    mask = _mask_rows(case["SE_ENABLE_MASK"])[row][col] == "1"
    if branch == "WL":
        return {"WRITE0": "-" + case["ROW_WL_WRITE_AMPLITUDE"],
                "READ0": case["ROW_WL_READ_AMPLITUDE"],
                "WRITE1": case["ROW_WL_WRITE_AMPLITUDE"],
                "FINAL_READ": case["ROW_WL_READ_AMPLITUDE"] if selected_row else "0"}
    if branch == "BL":
        return {"WRITE0": "-" + case["COL_BL_WRITE_AMPLITUDE"], "READ0": "0",
                "WRITE1": case["COL_BL_WRITE_AMPLITUDE"], "FINAL_READ": "0"}
    if branch == "SE":
        return {"WRITE0": "0", "READ0": case["COL_SE_READ_AMPLITUDE"], "WRITE1": "0",
                "FINAL_READ": case["COL_SE_READ_AMPLITUDE"]
                if selected_row and selected_col and mask else "0"}
    raise ConfigError(f"unknown input branch {branch}")


def _pwl_points(levels: dict[str, str], stimulus: dict[str, str], stop: str) -> list[tuple[str, str]]:
    points: list[tuple[Decimal, str, str]] = [(Decimal("0"), "0", "0")]
    for stage in STIMULUS_STAGES:
        start = _time_ps(stimulus[f"{stage}_START"])
        rise = _time_ps(stimulus[f"{stage}_RISE"])
        hold = _time_ps(stimulus[f"{stage}_HOLD"])
        fall = _time_ps(stimulus[f"{stage}_FALL"])
        value = levels[stage]
        points.extend(((start, _fmt_ps(start), "0"),
                       (start + rise, _fmt_ps(start + rise), value),
                       (start + rise + hold, _fmt_ps(start + rise + hold), value),
                       (start + rise + hold + fall, _fmt_ps(start + rise + hold + fall), "0")))
    points.append((_time_ps(stop), stop, "0"))
    points.sort(key=lambda item: item[0])
    unique: list[tuple[str, str]] = []
    seen = set()
    for time_value, time_token, value in points:
        if time_value in seen:
            if unique and unique[-1][1] == value:
                continue
            raise ConfigError(f"overlapping PWL points at {time_token}")
        seen.add(time_value)
        unique.append((time_token, value))
    return unique


def render_stimulus(case: dict[str, str], stimulus: dict[str, str]) -> tuple[str, list[dict[str, Any]]]:
    lines = ["* 4x4 shared row/column current sources; SE source is cell-local."]
    drivers = []
    for row in range(1, 5):
        source, node = f"I_WL_R{row}", f"WL_R{row}"
        points = _pwl_points(_stage_levels(case, stimulus, f"R{row}C1", "WL"), stimulus, case["STOP"])
        lines.append(f"{source} 0 {node} PWL(" + " ".join(f"{t} {v}" for t, v in points) + ")")
        drivers.append({"source": source, "node": node, "branch": "WL", "cells": [f"R{row}C{c}" for c in range(1,5)]})
    for col in range(1, 5):
        source, node = f"I_BL_C{col}", f"BL_C{col}"
        points = _pwl_points(_stage_levels(case, stimulus, f"R1C{col}", "BL"), stimulus, case["STOP"])
        lines.append(f"{source} 0 {node} PWL(" + " ".join(f"{t} {v}" for t, v in points) + ")")
        drivers.append({"source": source, "node": node, "branch": "BL", "cells": [f"R{r}C{col}" for r in range(1,5)]})
    for cell in CELLS:
        source, node = f"I_SE_{cell}", f"SE_{cell}"
        points = _pwl_points(_stage_levels(case, stimulus, cell, "SE"), stimulus, case["STOP"])
        lines.append(f"{source} 0 {node} PWL(" + " ".join(f"{t} {v}" for t, v in points) + ")")
        drivers.append({"source": source, "node": node, "branch": "SE", "cells": [cell]})
    return "\n".join(lines) + "\n", drivers


def make_chain_probe_manifest(case: dict[str, str]) -> dict[str, Any]:
    signals: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add(label: str, group: str, unit: str, **meta: Any) -> None:
        if label not in seen:
            seen.add(label)
            signals.append({"label": label, "group": group, "unit": unit, **meta})

    for diagonal, cells in DIAGONALS.items():
        last_cb = f"XCB_{diagonal}_L{len(cells)}"
        add(f"V(DOUT_{diagonal})", f"chain_input:{diagonal}:upstream", "V", node=f"DOUT_{diagonal}")
        for jj in ("BJ1",):
            add(f"P({jj}|{last_cb})", f"chain_input:{diagonal}:last_cb", "rad", instance=last_cb, element=jj)
            add(f"V({jj}|{last_cb})", f"chain_input:{diagonal}:last_cb", "V", instance=last_cb, element=jj)
        if diagonal == "D1" and case.get("CBU_OVERRIDE_D1", "NONE") == "CB_CARRY_BUFFER":
            for jj in ("BJ2",):
                add(f"P({jj}|{last_cb})", "chain_input:D1:last_cb", "rad", instance=last_cb, element=jj)
                add(f"V({jj}|{last_cb})", "chain_input:D1:last_cb", "V", instance=last_cb, element=jj)
        for node, group in ((f"T1_I_{diagonal}", "input"), (f"CLK_{diagonal}", "clock"),
                            (f"S_{diagonal}", "sum"), (f"C_{diagonal}", "carry")):
            add(f"V({node})", f"chain_t1:{diagonal}:{group}", "V", node=node, diagonal=diagonal)
        add(f"I(V_T1_LINK_{diagonal})", f"chain_t1:{diagonal}:input_link_current", "A",
            element=f"V_T1_LINK_{diagonal}", direction="upstream output toward T1 input")
        add(f"I(R_S_{diagonal})", f"chain_t1:{diagonal}:sum_load_current", "A",
            element=f"R_S_{diagonal}", direction="S node to ground")
        # Preserve one measured external T1 bias branch per stage. The other
        # two independent bias source values remain in the deck/config snapshot.
        for index in (1,):
            source = (f"I_BIAS{index}" if index == 3 and case.get("T1_BIAS3_SOURCE") == "CURRENT"
                      else f"V_BIAS{index}")
            add(f"I({source}_{diagonal})", f"chain_bias:t1:{diagonal}", "A", element=f"{source}_{diagonal}")
        clock_element = (f"R_TRIG_CLK_{diagonal}" if case["T1_CHAIN_CLOCK_MODE"] == "GLOBAL_ONESHOT"
                         else f"R_CLK_QUIET_{diagonal}")
        add(f"I({clock_element})", f"chain_clock:{diagonal}:branch_current", "A", element=clock_element)
        t1 = f"XT1_{diagonal}"
        # The carry-buffer comparison is registered around D0/D1 and the D2+
        # chain boundaries; keep later T1 internal JJ columns out of these
        # already-large raws while retaining all D0/D1 same-JJ P/V evidence.
        critical_jjs = (T1_CRITICAL_JJS if case.get("CBU_OVERRIDE_D1", "NONE") != "CB_CARRY_BUFFER"
                        or diagonal in {"D0", "D1"} else ())
        for jj in critical_jjs:
            add(f"P({jj}|{t1})", f"chain_t1_jj:{diagonal}", "rad", instance=t1, element=jj)
            add(f"V({jj}|{t1})", f"chain_t1_jj:{diagonal}", "V", instance=t1, element=jj)

    for index in range(1, 7):
        instance = f"XCBU_D{index}"
        direct_cb_d1 = index == 1 and case.get("CBU_OVERRIDE_D1", "NONE") == "CB_DIRECT"
        carry_buffer_d1 = index == 1 and case.get("CBU_OVERRIDE_D1", "NONE") == "CB_CARRY_BUFFER"
        if carry_buffer_d1:
            instance = "XCB_CARRY_D1"
        nodes = ({"JOIN": "CBU_JOIN_D1", "CARRY_CB_IN": "CARRY_CB_IN_D1",
                  "CARRY_CB_OUT": "CARRY_CB_OUT_D1"} if carry_buffer_d1 else
                 {"JOIN": "CBU_JOIN_D1", "OUT": "CBU_OUT_D1"} if direct_cb_d1 else
                 {"A": f"CBU_A_D{index}", "B": f"CBU_B_D{index}", "OUT": f"CBU_OUT_D{index}"})
        for port, node in nodes.items():
            add(f"V({node})", f"chain_cbu:D{index}:{port.lower()}", "V", instance=instance,
                port=port, node=node)
        if carry_buffer_d1:
            for element, port, direction in (
                    ("V_CBU_A_D1", "A", "DOUT_D1 -> CBU_JOIN_D1"),
                    ("V_CARRY_IN_D1", "CARRY_INPUT", "C_D0 -> CARRY_CB_IN_D1"),
                    ("V_CBU_B_D1", "B_BUFFER_OUTPUT", "CARRY_CB_OUT_D1 -> CBU_JOIN_D1")):
                add(f"I({element})", f"chain_cbu:D1:{port.lower()}_current", "A",
                    instance="XCB_CARRY_D1", port=port, element=element, direction=direction)
        else:
            for port in ("A", "B"):
                element = f"V_CBU_{port}_D{index}"
                add(f"I({element})", f"chain_cbu:D{index}:{port.lower()}_current", "A",
                    instance=instance, port=port, element=element,
                    direction=(f"{'DOUT_D1' if port == 'A' else 'C_D0'} -> CBU_JOIN_D1"
                               if direct_cb_d1 else
                               f"{'DOUT_D' + str(index) if port == 'A' else 'C_D' + str(index-1)} -> CBU_{port}_D{index}"))
        add(f"I(V_T1_LINK_D{index})", f"chain_cbu:D{index}:output_current", "A",
            instance=instance, port="OUT", element=f"V_T1_LINK_D{index}")
        jj_names = ("BJ1", "BJ2") if direct_cb_d1 or carry_buffer_d1 else ("B1", "B4", "B7")
        for jj in jj_names:
            group = ("chain_cbu_cb_carry_buffer:D1" if carry_buffer_d1 else
                     "chain_cbu_cb_direct:D1" if direct_cb_d1 else f"chain_cbu_jj:D{index}")
            add(f"P({jj}|{instance})", group, "rad", instance=instance, element=jj)
            add(f"V({jj}|{instance})", group, "V", instance=instance, element=jj)
        add(f"I(IB1|{instance})", f"chain_bias:cbu:D{index}", "A", instance=instance,
            element="IB1", note=("canonical CB_0928 internal bias branch" if direct_cb_d1 or carry_buffer_d1 else
                                  "representative internal MERGE bias-source branch; values pinned in CBU_PARAMS"))

    for stage in range(1, int(case["D0_JTL_COUNT"]) + 1):
        instance = f"XJTL_D0_{stage}"
        input_node = f"D0_JTL_IN_{stage}"
        output_node = f"D0_JTL_OUT_{stage}"
        for node, role in ((input_node, "input"), (output_node, "output")):
            add(f"V({node})", f"chain_d0_jtl:{stage}:{role}", "V", instance=instance, node=node)
        add(f"I(IB1|{instance})", f"chain_bias:d0_jtl:{stage}", "A", instance=instance, element="IB1")
        for jj in ("BJ1",):
            add(f"P({jj}|{instance})", f"chain_d0_jtl_jj:{stage}", "rad", instance=instance, element=jj)
            add(f"V({jj}|{instance})", f"chain_d0_jtl_jj:{stage}", "V", instance=instance, element=jj)
        link_in = f"V_D0_JTL_IN_{stage}"
        link_out = f"V_T1_LINK_D0" if stage == int(case["D0_JTL_COUNT"]) else f"V_D0_JTL_OUT_{stage}"
        add(f"I({link_in})", f"chain_d0_jtl:{stage}:input_current", "A", element=link_in)
        add(f"I({link_out})", f"chain_d0_jtl:{stage}:output_current", "A", element=link_out)

    for node, role in (("DFF_IN", "data"), ("CLK_DFF", "clock"), ("DFF_O", "output")):
        add(f"V({node})", f"chain_dff:{role}", "V", node=node)
    add("I(V_DFF_DATA)", "chain_dff:data_link_current", "A", element="V_DFF_DATA")
    add("I(R_DFF_OUT)", "chain_dff:output_load_current", "A", element="R_DFF_OUT")
    for jj in ("B1", "B2", "B7"):
        add(f"P({jj}|XDFF)", "chain_dff_jj", "rad", instance="XDFF", element=jj)
        add(f"V({jj}|XDFF)", "chain_dff_jj", "V", instance="XDFF", element=jj)
    add("I(IB1|XDFF)", "chain_bias:dff", "A", instance="XDFF", element="IB1",
        note="representative internal DFF bias-source branch; all bias values pinned in DFF_PARAMS")
    if case["T1_CHAIN_CLOCK_MODE"] == "GLOBAL_ONESHOT":
        add("I(R_TRIG_CLK_DFF)", "chain_clock:DFF:branch_current", "A", element="R_TRIG_CLK_DFF")
    else:
        add("I(R_CLK_QUIET_DFF)", "chain_clock:DFF:quiet_current", "A", element="R_CLK_QUIET_DFF")

    return {"schema": "bvm-4x4-t1-chain-probe-manifest-v1", "profile": "t1_chain_focus",
            "focus_stage": case["FOCUS_STAGE"], "d0_jtl_count": int(case["D0_JTL_COUNT"]),
            "cbu_override_d1": case.get("CBU_OVERRIDE_D1", "NONE"),
            "signal_count": len(signals),
            "raw_phase_unit": "P(...) radians",
            "display_phase_unit": "turns=rad/(2*pi), navigation only; not event count",
            "signals": signals, "scientific_interpretation_performed": False}


def make_probe_manifest(case: dict[str, str], topology: dict[str, Any]) -> dict[str, Any]:
    if case["OUTPUT_MODE"] == "DIAGONAL_T1_CHAIN":
        return make_chain_probe_manifest(case)
    signals: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add(label: str, group: str, unit: str, **meta: Any) -> None:
        if label not in seen:
            seen.add(label)
            signals.append({"label": label, "group": group, "unit": unit, **meta})

    profile = _profile(case)
    focus_diagonal = case["FOCUS_DIAGONAL"]
    focus_cells = DIAGONALS[focus_diagonal]

    if profile == "t1_array_focus":
        clock_mode = topology.get("t1_clock_mode")
        for diagonal in DIAGONALS:
            t1 = f"XT1_{diagonal}"
            add(f"V(DOUT_{diagonal})", f"t1_input:{diagonal}:upstream", "V",
                node=f"DOUT_{diagonal}", diagonal=diagonal)
            add(f"V(T1_I_{diagonal})", f"t1_input:{diagonal}:loaded_input", "V",
                node=f"T1_I_{diagonal}", diagonal=diagonal)
            add(f"I(V_T1_LINK_{diagonal})", f"t1_input:{diagonal}:link_current", "A",
                element=f"V_T1_LINK_{diagonal}", diagonal=diagonal,
                direction=f"DOUT_{diagonal} to T1_I_{diagonal}")
            add(f"V(S_{diagonal})", f"t1_output:{diagonal}:sum", "V",
                node=f"S_{diagonal}", diagonal=diagonal)
            add(f"I(R_S_{diagonal})", f"t1_load:{diagonal}:sum", "A",
                element=f"R_S_{diagonal}", diagonal=diagonal, direction="S node to ground")
            add(f"V(C_{diagonal})", f"t1_output:{diagonal}:carry", "V",
                node=f"C_{diagonal}", diagonal=diagonal)
            add(f"I(R_C_{diagonal})", f"t1_load:{diagonal}:carry", "A",
                element=f"R_C_{diagonal}", diagonal=diagonal, direction="C node to ground")
            add(f"V(CLK_{diagonal})", f"t1_clock:{diagonal}:loaded", "V",
                node=f"CLK_{diagonal}", diagonal=diagonal)
            if clock_mode == "PULSE":
                add(f"V(CLK_RAW_{diagonal})", f"t1_clock:{diagonal}:source", "V",
                    node=f"CLK_RAW_{diagonal}", diagonal=diagonal)
                add(f"I(R_TRIG_CLK_{diagonal})", f"t1_clock:{diagonal}:branch_current", "A",
                    element=f"R_TRIG_CLK_{diagonal}", diagonal=diagonal)
            elif clock_mode == "QUIET":
                add(f"I(R_CLK_QUIET_{diagonal})", f"t1_clock:{diagonal}:quiet_branch", "A",
                    element=f"R_CLK_QUIET_{diagonal}", diagonal=diagonal)
            else:
                raise ConfigError(f"unknown T1 clock mode in topology manifest: {clock_mode!r}")
            for index in range(1, 4):
                source = ("I_BIAS3" if index == 3 and
                          topology.get("t1_biases", {}).get("T1_BIAS3_SOURCE") == "CURRENT"
                          else f"V_BIAS{index}")
                add(f"I({source}_{diagonal})", f"t1_bias:{diagonal}", "A",
                    element=f"{source}_{diagonal}", diagonal=diagonal)
            cb = f"XCB_{diagonal}_L{len(DIAGONALS[diagonal])}"
            for jj in ("BJ1", "BJ2"):
                add(f"P({jj}|{cb})", f"t1_upstream_cb:{diagonal}", "rad",
                    instance=cb, element=jj, diagonal=diagonal)
                add(f"V({jj}|{cb})", f"t1_upstream_cb:{diagonal}", "V",
                    instance=cb, element=jj, diagonal=diagonal)
            for jj in T1_CRITICAL_JJS:
                add(f"P({jj}|{t1})", f"t1_internal:{diagonal}", "rad",
                    instance=t1, element=jj, diagonal=diagonal)
                add(f"V({jj}|{t1})", f"t1_internal:{diagonal}", "V",
                    instance=t1, element=jj, diagonal=diagonal)
        return {"schema": "bvm-4x4-t1-array-probe-manifest-v1",
                "profile": profile, "focus_diagonal": focus_diagonal,
                "signal_count": len(signals), "raw_phase_unit": "P(...) radians",
                "display_phase_unit": "turns=rad/(2*pi), navigation only; not event count",
                "signals": signals, "scientific_interpretation_performed": False}

    if profile == "compact":
        # Shared source-current totals plus cell-local SE source currents.
        for row in range(1, 5):
            add(f"I(I_WL_R{row})", "input_source:WL", "A", source=f"I_WL_R{row}", row=row,
                direction="JoSIM source reference direction")
        for col in range(1, 5):
            add(f"I(I_BL_C{col})", "input_source:BL", "A", source=f"I_BL_C{col}", column=col,
                direction="JoSIM source reference direction")
        for cell in CELLS:
            add(f"I(I_SE_{cell})", "input_source:SE", "A", source=f"I_SE_{cell}", cell=cell,
                direction="JoSIM source reference direction")
        for cell in CELLS:
            add(f"V(SL_{cell})", f"bvm_output:{cell}", "V", node=f"SL_{cell}", cell=cell)
        for name, cells in DIAGONALS.items():
            for level in range(1, len(cells) + 1):
                add(f"V(MERGE_{name}_L{level})", f"merge:{name}", "V",
                    node=f"MERGE_{name}_L{level}", diagonal=name, level=level)
            add(f"V(DOUT_{name})", f"diagonal_output:{name}", "V", node=f"DOUT_{name}", diagonal=name)
            add(f"I(R_TERM_{name})", f"terminal_current:{name}", "A",
                element=f"R_TERM_{name}", diagonal=name)
            cb = f"XCB_{name}_L{len(cells)}"
            for jj in ("BJ1", "BJ2"):
                add(f"P({jj}|{cb})", f"terminal_junction:{name}", "rad", instance=cb, element=jj, diagonal=name)
                add(f"V({jj}|{cb})", f"terminal_junction:{name}", "V", instance=cb, element=jj, diagonal=name)

    if profile == "focus":
        name = focus_diagonal
        # Preserve every per-cell WL/BL/SE branch current so bus sharing is measured,
        # rather than inferred from ideal-source setpoints.
        for cell in CELLS:
            inst = f"XBVM_{cell}"
            for branch, element in (("WL", "R_WL"), ("BL", "R_BL"), ("SE", "R_SE")):
                add(f"I({element}|{inst})", f"input:{cell}:{branch}", "A",
                    instance=inst, element=element, cell=cell, branch=branch,
                    direction="canonical BVM element reference direction")
        for cell in focus_cells:
            add(f"V(SL_{cell})", f"focus:{name}:bvm_output", "V", node=f"SL_{cell}", cell=cell)
            add(f"I(L_SL|XBVM_{cell})", f"focus:{name}:bvm_output_current", "A",
                instance=f"XBVM_{cell}", element="L_SL", cell=cell,
                direction="canonical BVM element reference direction")
            for jj in ("B_JM1", "B_JM2"):
                add(f"P({jj}|XBVM_{cell})", f"focus:{name}:bvm_storage", "rad",
                    instance=f"XBVM_{cell}", element=jj, cell=cell)
                add(f"V({jj}|XBVM_{cell})", f"focus:{name}:bvm_storage", "V",
                    instance=f"XBVM_{cell}", element=jj, cell=cell)
        for level, cell in enumerate(focus_cells, start=1):
            add(f"V(MERGE_{name}_L{level})", f"focus:{name}:qb_output", "V",
                node=f"MERGE_{name}_L{level}", level=level, cell=cell)
        # The first selected cell is the explicit QB internal focus; all four QB
        # output boundaries above remain visible independently.
        qb = f"XBQ_{focus_cells[0]}"
        for jj in ("BJ1", "BJ2", "BJ3"):
            add(f"P({jj}|{qb})", f"focus:{name}:qb_internal", "rad", instance=qb, element=jj,
                cell=focus_cells[0])
            add(f"V({jj}|{qb})", f"focus:{name}:qb_internal", "V", instance=qb, element=jj,
                cell=focus_cells[0])
        for stage in _sjtl_plan(case, name):
            instance = stage["instance"]
            level = stage["level"]
            add(f"V({stage['output_node']})", f"focus:{name}:sjtl_output", "V",
                node=stage["output_node"], level=level, stage_index=stage["stage_index"])
            add(f"P(BJ1|{instance})", f"focus:{name}:sjtl", "rad", instance=instance,
                element="BJ1", level=level, stage_index=stage["stage_index"])
            add(f"V(BJ1|{instance})", f"focus:{name}:sjtl", "V", instance=instance,
                element="BJ1", level=level, stage_index=stage["stage_index"])
        for level in range(1, len(focus_cells) + 1):
            cb = f"XCB_{name}_L{level}"
            for jj in ("BJ1", "BJ2"):
                add(f"P({jj}|{cb})", f"focus:{name}:cb", "rad", instance=cb,
                    element=jj, level=level)
                add(f"V({jj}|{cb})", f"focus:{name}:cb", "V", instance=cb,
                    element=jj, level=level)
        for diagonal in DIAGONALS:
            add(f"V(DOUT_{diagonal})", "diagonal_output", "V",
                node=f"DOUT_{diagonal}", diagonal=diagonal)
            add(f"I(R_TERM_{diagonal})", "terminal_current", "A",
                element=f"R_TERM_{diagonal}", diagonal=diagonal)

    if profile == "debug":
        # Full internal debug is intentionally opt-in. It begins with the compact
        # boundary set and adds internal state/current probes for every cell/stage.
        if not signals:
            compact_case = {**case, "PROBE_PROFILE": "compact"}
            compact_manifest = make_probe_manifest(compact_case, topology)
            for item in compact_manifest["signals"]:
                metadata = {key: value for key, value in item.items()
                            if key not in {"label", "group", "unit"}}
                add(item["label"], item["group"], item["unit"], **metadata)
        for cell in CELLS:
            bvm, qb = f"XBVM_{cell}", f"XBQ_{cell}"
            for jj in ("B_JM1", "B_JM2", "B_JS1", "B_JS2"):
                add(f"P({jj}|{bvm})", "debug:bvm_junction", "rad", instance=bvm, element=jj, cell=cell)
                add(f"V({jj}|{bvm})", "debug:bvm_junction", "V", instance=bvm, element=jj, cell=cell)
            for element in ("L_PBL", "L_PWL", "L_M1", "L_M2", "L_M3", "L_PM", "L_S1",
                            "L_PSE", "L_S3", "L_S2", "L_PSL", "L_SL", "R_JM1", "R_S", "R_SL"):
                add(f"I({element}|{bvm})", "debug:bvm_branch_current", "A",
                    instance=bvm, element=element, cell=cell)
            for jj in ("BJ1", "BJ2", "BJ3"):
                add(f"P({jj}|{qb})", "debug:qb_junction", "rad", instance=qb, element=jj, cell=cell)
                add(f"V({jj}|{qb})", "debug:qb_junction", "V", instance=qb, element=jj, cell=cell)
            for element in ("LIN", "L1", "L2", "L3", "RJ1", "RJ2", "RJ3", "IB2"):
                add(f"I({element}|{qb})", "debug:qb_branch_current", "A",
                    instance=qb, element=element, cell=cell)
        for diagonal in DIAGONALS:
            for stage in _sjtl_plan(case, diagonal):
                instance = stage["instance"]
                for label, unit, element in ((f"P(BJ1|{instance})", "rad", "BJ1"),
                                             (f"V(BJ1|{instance})", "V", "BJ1")):
                    add(label, "debug:sjtl_junction", unit, instance=instance, element=element,
                        level=stage["level"], stage_index=stage["stage_index"])
                for element in ("L1", "L2", "RJ1"):
                    add(f"I({element}|{instance})", "debug:sjtl_branch_current", "A",
                        instance=instance, element=element, level=stage["level"],
                        stage_index=stage["stage_index"])
            for level in range(1, len(DIAGONALS[diagonal]) + 1):
                cb = f"XCB_{diagonal}_L{level}"
                for jj in ("BJ1", "BJ2"):
                    add(f"P({jj}|{cb})", "debug:cb_junction", "rad", instance=cb,
                        element=jj, level=level)
                    add(f"V({jj}|{cb})", "debug:cb_junction", "V", instance=cb,
                        element=jj, level=level)
                for element in ("L1", "L2", "L3", "L4", "RJ1", "RJ2", "IB1"):
                    add(f"I({element}|{cb})", "debug:cb_branch_current", "A",
                        instance=cb, element=element, level=level)

    return {"schema": "bvm-4x4-diagonal-probe-manifest-v2",
            "profile": profile, "focus_diagonal": focus_diagonal if profile == "focus" else None,
            "signal_count": len(signals), "raw_phase_unit": "P(...) radians",
            "display_phase_unit": "turns=rad/(2*pi), navigation only; not event count",
            "signals": signals, "scientific_interpretation_performed": False}


def render(case: dict[str, str], stimulus: dict[str, str], t1_params: dict[str, str],
           run_dir: Path) -> dict[str, Any]:
    sources = verify_sources()
    chain_active = case["OUTPUT_MODE"] == "DIAGONAL_T1_CHAIN"
    t1_active = case["OUTPUT_MODE"] in {"DIAGONAL_T1_INDEPENDENT", "DIAGONAL_T1_CHAIN"}
    if chain_active and case.get("CBU_OVERRIDE_D1", "NONE") == "CB_DIRECT":
        cb_path = REPO / SOURCE_PATHS["CB"]
        sources["CBU_D1_DIRECT"] = {"path": SOURCE_PATHS["CB"], "sha256": sha256(cb_path),
                                    "mode": "CANONICAL_CB_0928_DIRECT_SHARED_NODE",
                                    "subcircuit": "CB", "ports": ["IN", "OUT"]}
    if chain_active and case.get("CBU_OVERRIDE_D1", "NONE") == "CB_CARRY_BUFFER":
        cb_path = REPO / SOURCE_PATHS["CB"]
        sources["CBU_D1_CARRY_BUFFER"] = {
            "path": SOURCE_PATHS["CB"], "sha256": sha256(cb_path),
            "mode": "CANONICAL_CB_0928_ON_D0_CARRY_BRANCH",
            "subcircuit": "CB", "ports": ["IN", "OUT"]}
    t1_source_text = None
    t1_source_info = None
    chain_source_texts: dict[str, str] = {}
    chain_source_info: dict[str, dict[str, Any]] = {}
    if t1_active:
        t1_source_text, t1_source_info = render_t1_source(t1_params)
        sources["T1_REFERENCE"]["mode"] = "CANONICAL_BASE_FOR_TUNABLE_RENDER"
        sources["T1_RENDERED"] = {"path": t1_source_info["path"],
                                  "sha256": t1_source_info["rendered_sha256"],
                                  "mode": "RUN_LOCAL_TUNABLE_COPY"}
    if chain_active:
        renderers = (("CBU_RENDERED", render_cbu_source, "sources/cbu_tunable.cir", CBU_SOURCE_PATH),
                     ("DFF_RENDERED", render_dff_source, "sources/dff_tunable.cir", DFF_SOURCE_PATH),
                     ("D0_JTL_RENDERED", render_d0_jtl_source, "sources/d0_jtl_tunable.cir", D0_JTL_BASE_SOURCE_PATH))
        for role, renderer, output_path, canonical_path in renderers:
            text, info = renderer(t1_params)
            chain_source_texts[output_path] = text
            chain_source_info[role] = info
            sources[role] = {"path": output_path, "sha256": info["rendered_sha256"],
                             "canonical_path": canonical_path, "canonical_sha256": info["canonical_sha256"],
                             "mode": "RUN_LOCAL_TUNABLE_CANDIDATE"}
    topo = topology_manifest(sources, case, t1_params)
    stimulus_text, drivers = render_stimulus(case, stimulus)
    probes = make_probe_manifest(case, topo)
    lines = [
        ("* BVM 4x4 diagonal collection; canonical BVM/QB/sJTL/CB; T1_MODE=OFF."
         if not t1_active else
         "* BVM 4x4 diagonal collection; physical seven-stage T1/CBU chain." if chain_active else
         "* BVM 4x4 diagonal collection; seven independent canonical-topology T1 channels."),
        "* Cell WL/BL are physically shared buses; SE is cell-local.",
        ".include " + _spice_include(run_dir, SOURCE_PATHS["JJMIT"]),
        ".include " + _spice_include(run_dir, SOURCE_PATHS["BVM"]),
        ".include " + _spice_include(run_dir, SOURCE_PATHS["QB"]),
        ".include " + _spice_include(run_dir, SOURCE_PATHS["SJTL"]),
        ".include " + _spice_include(run_dir, SOURCE_PATHS["CB"]),
        ".include stimulus.inc", "",
    ]
    if t1_active:
        lines.append(".include sources/t1_cell_tunable.cir")
        lines.append("")
    if chain_active:
        lines.extend(f".include {relative}" for relative in chain_source_texts)
        lines.append("")
    for cell in CELLS:
        row, col = int(cell[1]), int(cell[3])
        diag = next(name for name, members in DIAGONALS.items() if cell in members)
        level = DIAGONALS[diag].index(cell) + 1
        lines.append(f"XBVM_{cell} WL_R{row} BL_C{col} SE_{cell} SL_{cell} BVM")
        lines.append(f"XBQ_{cell} SL_{cell} MERGE_{diag}_L{level} BQ")
    for name, cells in DIAGONALS.items():
        for level, _cell in enumerate(cells, start=1):
            for stage in (item for item in _sjtl_plan(case, name) if item["level"] == level):
                lines.append(f"{stage['instance']} {stage['input_node']} {stage['output_node']} sJTL")
            next_node = (f"MERGE_{name}_L{level + 1}" if level < len(cells)
                         else f"DOUT_{name}")
            lines.append(f"XCB_{name}_L{level} {_cb_input_node(case, name, level)} {next_node} CB")
        if not t1_active:
            lines.append(f"R_TERM_{name} DOUT_{name} 0 2")
    if case["OUTPUT_MODE"] == "DIAGONAL_T1_INDEPENDENT":
        lines.extend(("", "* Seven isolated bias/clock/output networks; DOUT loads only its paired T1."))
        for diagonal in DIAGONALS:
            for index in (1, 2):
                lines.append(f"V_BIAS{index}_{diagonal} N_BIAS{index}_{diagonal} 0 DC {t1_params[f'T1_BIAS{index}']}")
            bias3_source = t1_params["T1_BIAS3_SOURCE"]
            if bias3_source == "VOLTAGE":
                lines.append(f"V_BIAS3_{diagonal} N_BIAS3_{diagonal} 0 DC {t1_params['T1_BIAS3']}")
            else:
                lines.append(f"I_BIAS3_{diagonal} 0 N_BIAS3_{diagonal} DC {t1_params['T1_BIAS3']}")
            lines.append(f"R_S_{diagonal} S_{diagonal} 0 {t1_params['T1_R_S']}")
            lines.append(f"R_C_{diagonal} C_{diagonal} 0 {t1_params['T1_R_C']}")
            if t1_params["T1_CLK_MODE"] == "QUIET":
                lines.append(f"R_CLK_QUIET_{diagonal} CLK_{diagonal} 0 {t1_params['T1_CLK_QUIET_R']}")
            else:
                lines.append(f"V_TRIG_CLK_{diagonal} CLK_RAW_{diagonal} 0 PULSE(0 {t1_params['T1_CLK_AMPLITUDE']} {t1_params['T1_CLK_START']} {t1_params['T1_CLK_RISE']} {t1_params['T1_CLK_FALL']} {t1_params['T1_CLK_WIDTH']} {t1_params['T1_CLK_PERIOD']})")
                lines.append(f"R_TRIG_CLK_{diagonal} CLK_RAW_{diagonal} CLK_{diagonal} {t1_params['T1_CLK_SERIES_R']}")
            lines.append(f"V_T1_LINK_{diagonal} DOUT_{diagonal} T1_I_{diagonal} 0")
            lines.append(f"XT1_{diagonal} T1_I_{diagonal} CLK_{diagonal} S_{diagonal} C_{diagonal} N_BIAS1_{diagonal} N_BIAS2_{diagonal} N_BIAS3_{diagonal} T1")
    elif chain_active:
        lines.extend(_render_chain_network(case, t1_params))
    lines.extend(("", "* Registered probes; P is raw radians."))
    lines.extend(f".print {entry['label']}" for entry in probes["signals"])
    lines.extend((f".tran {case['DT']} {case['STOP']}", ".end"))
    deck = "\n".join(lines) + "\n"
    qa = static_validate(case, stimulus, t1_params, deck, stimulus_text, drivers, topo, probes,
                         t1_source_text=t1_source_text, t1_source_info=t1_source_info,
                         chain_source_texts=chain_source_texts, chain_source_info=chain_source_info)
    return {"deck": deck, "stimulus_text": stimulus_text, "drivers": drivers,
            "topology": topo, "probes": probes, "sources": sources, "static_qa": qa,
            "t1_source_text": t1_source_text, "t1_source_info": t1_source_info,
            "chain_source_texts": chain_source_texts, "chain_source_info": chain_source_info}


def _pins_from_source_text(text: str, subckt: str) -> tuple[str, ...]:
    matches = []
    for line in text.splitlines():
        parts = line.strip().split()
        if len(parts) >= 2 and parts[0].casefold() == ".subckt" and parts[1].casefold() == subckt.casefold():
            matches.append(tuple(parts[2:]))
    if len(matches) != 1:
        raise ConfigError(f"expected exactly one .subckt {subckt} in rendered source; found {len(matches)}")
    return matches[0]


def _source_element_names(text: str, subckt: str) -> set[str]:
    names = set()
    inside = False
    for line in text.splitlines():
        stripped = line.strip()
        parts = stripped.split()
        if len(parts) >= 2 and parts[0].casefold() == ".subckt" and parts[1].casefold() == subckt.casefold():
            inside = True
            continue
        if inside and parts and parts[0].casefold() == ".ends":
            break
        if inside and parts and not parts[0].startswith("*") and not parts[0].startswith("."):
            names.add(parts[0].upper())
    return names


def _validate_chain_topology(case: dict[str, str], params: dict[str, str], lines: list[str],
                             probes: dict[str, Any], t1_source_info: dict[str, Any] | None,
                             t1_source_text: str | None,
                             chain_source_texts: dict[str, str] | None,
                             chain_source_info: dict[str, dict[str, Any]] | None) -> dict[str, Any]:
    chain_source_texts = chain_source_texts or {}
    chain_source_info = chain_source_info or {}
    required_source_paths = {"sources/cbu_tunable.cir", "sources/dff_tunable.cir", "sources/d0_jtl_tunable.cir"}
    if set(chain_source_texts) != required_source_paths:
        raise ConfigError(f"chain source closure incomplete: {sorted(chain_source_texts)}")
    if not t1_source_info or not t1_source_info.get("topology_equivalent") or not t1_source_text:
        raise ConfigError("chain requires a topology-equivalent rendered T1 source")
    direct_cb_d1 = case.get("CBU_OVERRIDE_D1", "NONE") == "CB_DIRECT"
    carry_buffer_d1 = case.get("CBU_OVERRIDE_D1", "NONE") == "CB_CARRY_BUFFER"
    cbu_text = chain_source_texts["sources/cbu_tunable.cir"]
    dff_text = chain_source_texts["sources/dff_tunable.cir"]
    jtl_text = chain_source_texts["sources/d0_jtl_tunable.cir"]
    if tuple(pin.casefold() for pin in _pins_from_source_text(cbu_text, case["CBU_TYPE"])) != ("a", "b", "q"):
        raise ConfigError("CBU physical candidate must expose distinct a,b,q pins")
    if tuple(pin.casefold() for pin in _pins_from_source_text(dff_text, case["DFF_TYPE"])) != ("a", "clk", "q"):
        raise ConfigError("DFF physical candidate must expose a,clk,q pins")
    if tuple(pin.casefold() for pin in _pins_from_source_text(jtl_text, "D0_JTL")) != ("in", "out"):
        raise ConfigError("D0 physical entrance JTL must expose IN,OUT pins")
    if set(chain_source_info) != {"CBU_RENDERED", "DFF_RENDERED", "D0_JTL_RENDERED"}:
        raise ConfigError("chain source provenance is incomplete")
    if any(not item.get("device_topology_equivalent") for item in
           (chain_source_info["CBU_RENDERED"], chain_source_info["DFF_RENDERED"])):
        raise ConfigError("rendered CBU/DFF candidate changed its canonical device topology")

    t1_lines = {line for line in lines if line.startswith("XT1_D")}
    expected_t1 = {f"XT1_{name} T1_I_{name} CLK_{name} S_{name} C_{name} "
                   f"N_BIAS1_{name} N_BIAS2_{name} N_BIAS3_{name} T1" for name in DIAGONALS}
    if t1_lines != expected_t1 or len(t1_lines) != 7:
        raise ConfigError("chain requires exactly seven correctly pinned T1 instances")
    cbu_lines = {line for line in lines if line.startswith("XCBU_D")}
    expected_cbu = ({f"XCBU_D{index} CBU_A_D{index} CBU_B_D{index} CBU_OUT_D{index} {case['CBU_TYPE']}"
                     for index in range(2, 7)} if carry_buffer_d1 else {
        ("XCBU_D1 CBU_JOIN_D1 CBU_OUT_D1 CB" if index == 1 and direct_cb_d1 else
         f"XCBU_D{index} CBU_A_D{index} CBU_B_D{index} CBU_OUT_D{index} {case['CBU_TYPE']}")
        for index in range(1, 7)})
    if cbu_lines != expected_cbu or len(cbu_lines) != (5 if carry_buffer_d1 else 6):
        raise ConfigError("chain requires exactly six stage CBU instances with the registered D1 override")
    cbu_output_nodes = {line.split()[2] if line.split()[-1] == "CB" else line.split()[3]
                        for line in cbu_lines}
    if carry_buffer_d1:
        cbu_output_nodes.add("CBU_JOIN_D1")
    if len(cbu_output_nodes) != 6:
        raise ConfigError("CBU output nodes are not unique by stage")
    if direct_cb_d1 or carry_buffer_d1:
        if tuple(pin.casefold() for pin in subckt_pins(REPO / SOURCE_PATHS["CB"], "CB")) != ("in", "out"):
            raise ConfigError("D1 canonical CB_0928 candidate requires ports IN,OUT in that order")
        if sha256(REPO / SOURCE_PATHS["CB"]) != SOURCE_SHA256["CB"]:
            raise ConfigError("D1 canonical CB_0928 SHA differs from the pinned source")
    if direct_cb_d1:
        direct_lines = {
            "V_CBU_A_D1 DOUT_D1 CBU_JOIN_D1 0",
            "V_CBU_B_D1 C_D0 CBU_JOIN_D1 0",
            "XCBU_D1 CBU_JOIN_D1 CBU_OUT_D1 CB",
            "V_T1_LINK_D1 CBU_OUT_D1 T1_I_D1 0",
        }
        if any(line.startswith(("V_CBU_A_D1 ", "V_CBU_B_D1 ", "XCBU_D1 ", "V_T1_LINK_D1 "))
               and line not in direct_lines for line in lines):
            raise ConfigError("D1 CB_DIRECT has an unexpected branch, instance, or output connection")
        if any(any(node in line.split()[1:] for node in ("CBU_A_D1", "CBU_B_D1"))
               for line in lines if line and not line.startswith(("*", "."))):
            raise ConfigError("CBU_DIRECT D1 must use only the physical common node CBU_JOIN_D1")
        if sum("CBU_JOIN_D1" in line for line in lines if not line.startswith(("*", ".print"))) != 3:
            raise ConfigError("CBU_JOIN_D1 must occur only on the two input sensors and CB input")
    if carry_buffer_d1:
        carry_lines = {
            "V_CBU_A_D1 DOUT_D1 CBU_JOIN_D1 0",
            "V_CARRY_IN_D1 C_D0 CARRY_CB_IN_D1 0",
            "XCB_CARRY_D1 CARRY_CB_IN_D1 CARRY_CB_OUT_D1 CB",
            "V_CBU_B_D1 CARRY_CB_OUT_D1 CBU_JOIN_D1 0",
            "V_T1_LINK_D1 CBU_JOIN_D1 T1_I_D1 0",
        }
        prefixes = ("V_CBU_A_D1 ", "V_CARRY_IN_D1 ", "XCB_CARRY_D1 ",
                    "V_CBU_B_D1 ", "V_T1_LINK_D1 ", "XCBU_D1 ")
        actual_carry_lines = {line for line in lines if line.startswith(prefixes)}
        if actual_carry_lines != carry_lines:
            raise ConfigError(f"D1 CB_CARRY_BUFFER branch wiring differs from the registered topology: {actual_carry_lines}")
        if sum("CBU_JOIN_D1" in line for line in lines if not line.startswith(("*", ".print"))) != 3:
            raise ConfigError("CBU_JOIN_D1 must connect only DOUT sensor, carry-CB output sensor, and T1 link")
    if any(line.startswith("R_TERM_D") for line in lines):
        raise ConfigError("chain mode forbids legacy 2-ohm DOUT terminations")
    if any(line.startswith("R_C_D") for line in lines):
        raise ConfigError("C0-C6 must not retain independent T1 Carry loads in chain mode")
    expected_s_loads = {f"R_S_{name} S_{name} 0 {params['T1_R_S']}" for name in DIAGONALS}
    if {line for line in lines if line.startswith("R_S_D")} != expected_s_loads:
        raise ConfigError("each Sum output must retain exactly one configured measurement load")
    if f"R_DFF_OUT DFF_O 0 {params['DFF_R_OUT']}" not in lines:
        raise ConfigError("DFF output load is missing or differs from DFF_PARAMS")

    count = int(case["D0_JTL_COUNT"])
    expected_jtl = set()
    for stage in range(1, count + 1):
        upstream = "DOUT_D0" if stage == 1 else f"D0_JTL_NODE_{stage-1}"
        input_node = f"D0_JTL_IN_{stage}"
        output_node = f"D0_JTL_OUT_{stage}"
        downstream = "T1_I_D0" if stage == count else f"D0_JTL_NODE_{stage}"
        output_link = "V_T1_LINK_D0" if stage == count else f"V_D0_JTL_OUT_{stage}"
        expected_jtl.update({f"V_D0_JTL_IN_{stage} {upstream} {input_node} 0",
                             f"XJTL_D0_{stage} {input_node} {output_node} D0_JTL",
                             f"{output_link} {output_node} {downstream} 0"})
    actual_jtl = {line for line in lines if line.startswith(("V_D0_JTL_IN_", "V_D0_JTL_OUT_", "XJTL_D0_", "V_T1_LINK_D0"))}
    if actual_jtl != expected_jtl or len([line for line in lines if line.startswith("XJTL_D0_")]) != count:
        raise ConfigError("D0 physical JTL chain wiring/count is inconsistent")

    for index in range(1, 7):
        if index == 1 and carry_buffer_d1:
            expected = {
                "V_CBU_A_D1 DOUT_D1 CBU_JOIN_D1 0",
                "V_CARRY_IN_D1 C_D0 CARRY_CB_IN_D1 0",
                "XCB_CARRY_D1 CARRY_CB_IN_D1 CARRY_CB_OUT_D1 CB",
                "V_CBU_B_D1 CARRY_CB_OUT_D1 CBU_JOIN_D1 0",
                "V_T1_LINK_D1 CBU_JOIN_D1 T1_I_D1 0",
            }
            actual = {line for line in lines if line.startswith(("V_CBU_A_D1 ", "V_CARRY_IN_D1 ",
                                                                  "XCB_CARRY_D1 ", "V_CBU_B_D1 ",
                                                                  "V_T1_LINK_D1 "))}
        elif index == 1 and direct_cb_d1:
            expected = {
                "V_CBU_A_D1 DOUT_D1 CBU_JOIN_D1 0",
                "V_CBU_B_D1 C_D0 CBU_JOIN_D1 0",
                "XCBU_D1 CBU_JOIN_D1 CBU_OUT_D1 CB",
                "V_T1_LINK_D1 CBU_OUT_D1 T1_I_D1 0",
            }
        else:
            expected = {
                f"V_CBU_A_D{index} DOUT_D{index} CBU_A_D{index} 0",
                f"V_CBU_B_D{index} C_D{index-1} CBU_B_D{index} 0",
                f"XCBU_D{index} CBU_A_D{index} CBU_B_D{index} CBU_OUT_D{index} {case['CBU_TYPE']}",
                f"V_T1_LINK_D{index} CBU_OUT_D{index} T1_I_D{index} 0",
            }
        if not (index == 1 and carry_buffer_d1):
            actual = {line for line in lines if line.startswith((f"V_CBU_A_D{index} ", f"V_CBU_B_D{index} ",
                                                                  f"XCBU_D{index} ", f"V_T1_LINK_D{index} "))}
        if actual != expected:
            raise ConfigError(f"D{index} CBU and sensed input/output paths differ from the registered topology")
    if "V_DFF_DATA C_D6 DFF_IN 0" not in lines or f"XDFF DFF_IN CLK_DFF DFF_O {case['DFF_TYPE']}" not in lines:
        raise ConfigError("C6 must feed the DFF data input and DFF.O must be the bit7 node")
    if any(line.startswith("R_C_") for line in lines):
        raise ConfigError("no C output may be paralleled with a carry resistor load")

    if case["T1_CHAIN_CLOCK_MODE"] == "GLOBAL_ONESHOT":
        points = _global_clock_points(case, params)
        expected_pwl = "PWL(" + " ".join(f"{time} {value}" for time, value in points) + ")"
        source_lines = {line for line in lines if line.startswith("V_TRIG_CLK_")}
        expected_sources = {f"V_TRIG_CLK_{name} CLK_RAW_{name} 0 {expected_pwl}"
                            for name in (*DIAGONALS.keys(), "DFF")}
        series = {f"R_TRIG_CLK_{name} CLK_RAW_{name} CLK_{name} {params['T1_CLK_SERIES_R']}"
                  for name in DIAGONALS}
        series.add(f"R_TRIG_CLK_DFF CLK_RAW_DFF CLK_DFF {params['T1_CLK_SERIES_R']}")
        if source_lines != expected_sources or {line for line in lines if line.startswith("R_TRIG_CLK_")} != series:
            raise ConfigError("GLOBAL_ONESHOT must have eight identical, independently driven one-shot PWL clocks")
        if any("PULSE(" in line for line in source_lines) or any("R_CLK_QUIET_" in line for line in lines):
            raise ConfigError("GLOBAL_ONESHOT must not repeat and must not add quiet-clock shunts")
        if len(points) != 5 or len({point[0] for point in points}) != 5:
            raise ConfigError("GLOBAL_ONESHOT PWL must contain one unique rise/hold/fall pulse")
        quiet_count = 0
        pulse_count = 8
    else:
        expected_quiet = {f"R_CLK_QUIET_{name} CLK_{name} 0 {params['T1_CLK_QUIET_R']}" for name in DIAGONALS}
        expected_quiet.add(f"R_CLK_QUIET_DFF CLK_DFF 0 {params['DFF_CLK_QUIET_R']}")
        if {line for line in lines if line.startswith("R_CLK_QUIET_")} != expected_quiet:
            raise ConfigError("QUIET chain requires eight independent non-floating clock clamps")
        if any(line.startswith("V_TRIG_CLK_") or line.startswith("R_TRIG_CLK_") for line in lines):
            raise ConfigError("QUIET chain must not instantiate clock pulse sources")
        quiet_count = 8
        pulse_count = 0

    expected_bias = set()
    for index in (1, 2, 3):
        for name in DIAGONALS:
            node = f"N_BIAS{index}_{name}"
            if index != 3 or params["T1_BIAS3_SOURCE"] == "VOLTAGE":
                expected_bias.add(f"V_BIAS{index}_{name} {node} 0 DC {params[f'T1_BIAS{index}']}")
            else:
                expected_bias.add(f"I_BIAS3_{name} 0 {node} DC {params['T1_BIAS3']}")
    actual_bias = {line for line in lines if line.startswith(("V_BIAS", "I_BIAS3_"))}
    if actual_bias != expected_bias:
        raise ConfigError("chain T1 Bias sources are not seven independent configured sets")

    instances = {line.split()[0]: line.split()[-1] for line in lines if line.startswith("X")}
    internal_elements = {"T1": _source_element_names(t1_source_text, "T1")}
    internal_elements[case["CBU_TYPE"]] = _source_element_names(cbu_text, case["CBU_TYPE"])
    internal_elements[case["DFF_TYPE"]] = _source_element_names(dff_text, case["DFF_TYPE"])
    internal_elements["D0_JTL"] = _source_element_names(jtl_text, "D0_JTL")
    internal_elements["CB"] = _source_element_names((REPO / SOURCE_PATHS["CB"]).read_text(encoding="utf-8"), "CB")
    # All top-level and hierarchical probe references must resolve to declared nodes/elements.
    top_elements = {line.split()[0].upper() for line in lines
                    if line and not line.startswith(("*", "."))}
    top_nodes = set()
    pin_counts = {"BVM": 4, "BQ": 2, "sJTL": 2, "CB": 2, "T1": 7,
                  case["CBU_TYPE"]: 3, case["DFF_TYPE"]: 3, "D0_JTL": 2}
    for line in lines:
        parts = line.split()
        if not parts or parts[0].startswith(("*", ".")):
            continue
        name = parts[0].upper()
        if name.startswith("X"):
            pin_count = pin_counts.get(parts[-1])
            if pin_count is None:
                raise ConfigError(f"unknown subcircuit instance in chain deck: {line}")
            top_nodes.update(parts[1:1+pin_count])
        elif len(parts) >= 3:
            top_nodes.update(parts[1:3])
    for item in probes["signals"]:
        label = item["label"]
        match = re.fullmatch(r"[PVI]\(([^|)]+)\|([^|)]+)\)", label)
        if match:
            element, instance = match.groups()
            subckt = instances.get(instance)
            if subckt is None or element.upper() not in internal_elements.get(subckt, set()):
                raise ConfigError(f"probe target does not exist in rendered subcircuit: {label}")
        else:
            match = re.fullmatch(r"[VI]\(([^()]+)\)", label)
            if match:
                target = match.group(1).upper()
                if label.startswith("I(") and target not in top_elements:
                    raise ConfigError(f"probe target element does not exist at top level: {label}")
                if label.startswith("V(") and target not in {node.upper() for node in top_nodes}:
                    raise ConfigError(f"probe target node does not exist at top level: {label}")
    return {"t1_count": 7, "cbu_count": 6,
            "cbu_type_by_stage": {f"D{index}": ("CB_CARRY_BUFFER" if index == 1 and carry_buffer_d1
                                                  else "CB" if index == 1 and direct_cb_d1
                                                  else case["CBU_TYPE"])
                                  for index in range(1, 7)},
            "cbu_direct_d1": direct_cb_d1, "cbu_carry_buffer_d1": carry_buffer_d1,
            "d0_jtl_count": count, "dff_count": 1,
            "clock_mode": case["T1_CHAIN_CLOCK_MODE"], "clock_driver_count": 8,
            "pulse_clock_count": pulse_count, "quiet_clock_count": quiet_count,
            "carry_load_count": 0, "sum_load_count": 7, "dff_output_load_ohm": params["DFF_R_OUT"],
            "topology_status": "PASS"}


def static_validate(case: dict[str, str], stimulus: dict[str, str], t1_params: dict[str, str],
                    deck: str, stimulus_text: str, drivers: list[dict[str, Any]],
                    topo: dict[str, Any], probes: dict[str, Any], *,
                    t1_source_text: str | None = None,
                    t1_source_info: dict[str, Any] | None = None,
                    chain_source_texts: dict[str, str] | None = None,
                    chain_source_info: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
    lines = deck.splitlines()
    stimulus_lines = [line for line in stimulus_text.splitlines() if line.startswith("I_")]
    chain_active = case["OUTPUT_MODE"] == "DIAGONAL_T1_CHAIN"
    t1_active = case["OUTPUT_MODE"] in {"DIAGONAL_T1_INDEPENDENT", "DIAGONAL_T1_CHAIN"}
    if case["OUTPUT_MODE"] == "DIAGONAL_T1_INDEPENDENT" and _profile(case) != "t1_array_focus":
        raise ConfigError("T1 topology requires its dedicated t1_array_focus probe set")
    if chain_active and _profile(case) != "t1_chain_focus":
        raise ConfigError("chain topology requires its dedicated t1_chain_focus probe set")
    expected_pin_orders = {
        "BVM": ("WL", "BL", "SE", "SL"),
        "QB": ("IN", "OUT"),
        "SJTL": ("IN", "OUT"),
        "CB": ("IN", "OUT"),
    }
    actual_pin_orders = {
        "BVM": subckt_pins(REPO / SOURCE_PATHS["BVM"], "BVM"),
        "QB": subckt_pins(REPO / SOURCE_PATHS["QB"], "BQ"),
        "SJTL": subckt_pins(REPO / SOURCE_PATHS["SJTL"], "sJTL"),
        "CB": subckt_pins(REPO / SOURCE_PATHS["CB"], "CB"),
    }
    if actual_pin_orders != expected_pin_orders:
        raise ConfigError(f"canonical component pin order mismatch: {actual_pin_orders}")
    if subckt_pins(REPO / SOURCE_PATHS["T1_REFERENCE"], "T1") != (
            "I", "CLK", "S", "C", "N_BIAS1", "N_BIAS2", "N_BIAS3"):
        raise ConfigError("T1 reference subcircuit pin order drifted")
    if sum(1 for line in (REPO / SOURCE_PATHS["JJMIT"]).read_text().splitlines()
           if line.strip().lower().startswith(".model jjmit")) != 1:
        raise ConfigError("shared jjmit include must contain exactly one jjmit model")
    bvm = [line for line in lines if line.startswith("XBVM_")]
    qb = [line for line in lines if line.startswith("XBQ_")]
    sjtl = [line for line in lines if line.startswith("XSJTL_")]
    cb = [line for line in lines if re.match(r"XCB_D[0-6]_L[1-4]\s", line)]
    terms = [line for line in lines if line.startswith("R_TERM_")]
    expected_sjtl_count = sum(sum(_sjtl_counts(case, name)) for name in DIAGONALS)
    expected_terminal_count = 0 if t1_active else 7
    if (len(bvm), len(qb), len(sjtl), len(cb), len(terms)) != (
            16, 16, expected_sjtl_count, 16, expected_terminal_count):
        raise ConfigError(f"expected 16 BVM, 16 QB, {expected_sjtl_count} configured sJTL, 16 CB and {expected_terminal_count} terminals")
    if len(set(DIAGONALS)) != 7 or sorted(cell for group in DIAGONALS.values() for cell in group) != sorted(CELLS):
        raise ConfigError("diagonal mapping has duplicate or missing cells")
    if not t1_active:
        if any(any(token in line for token in ("XT1 ", "XCBU", "XDFF", "V_BIAS", "R_CLK")) for line in lines):
            raise ConfigError("T1/CBU/DFF/clock hardware must not appear in terminal mode")
        if any("t1_cell" in line.lower() for line in lines):
            raise ConfigError("T1_MODE=OFF forbids a T1 include")
    model_include = next((i for i, line in enumerate(lines)
                          if line.lower().endswith("circuits/models/jjmit.cir")), None)
    component_includes = [i for i, line in enumerate(lines)
                          if any(line.lower().endswith(SOURCE_PATHS[key].lower())
                                 for key in ("BVM", "QB", "SJTL", "CB"))]
    if model_include is None or len(component_includes) != 4 or model_include > min(component_includes):
        raise ConfigError("shared jjmit model must precede all four direct canonical includes")
    if t1_active:
        t1_include_indices = [i for i, line in enumerate(lines)
                              if line.strip().lower() == ".include sources/t1_cell_tunable.cir"]
        if (len(t1_include_indices) != 1 or t1_include_indices[0] <= model_include or
                t1_source_text is None or not t1_source_info or not t1_source_info.get("topology_equivalent")):
            raise ConfigError("seven-T1 mode needs one model-ordered tunable-source snapshot include")
    if chain_active:
        for relpath in ("sources/cbu_tunable.cir", "sources/dff_tunable.cir", "sources/d0_jtl_tunable.cir"):
            if sum(line.strip().lower() == f".include {relpath}" for line in lines) != 1:
                raise ConfigError(f"chain requires exactly one include for {relpath}")
    expected_bvm = {f"XBVM_{cell} WL_R{cell[1]} BL_C{cell[3]} SE_{cell} SL_{cell} BVM" for cell in CELLS}
    if set(bvm) != expected_bvm:
        raise ConfigError("BVM port map or shared WL/BL/cell-SE node is wrong")
    expected_qb = set()
    expected_sjtl = set()
    expected_cb = set()
    expected_terms = set()
    for name, cells in DIAGONALS.items():
        for level, cell in enumerate(cells, start=1):
            expected_qb.add(f"XBQ_{cell} SL_{cell} MERGE_{name}_L{level} BQ")
            next_node = f"MERGE_{name}_L{level + 1}" if level < len(cells) else f"DOUT_{name}"
            for stage in (item for item in _sjtl_plan(case, name) if item["level"] == level):
                expected_sjtl.add(f"{stage['instance']} {stage['input_node']} {stage['output_node']} sJTL")
            expected_cb.add(f"XCB_{name}_L{level} {_cb_input_node(case, name, level)} {next_node} CB")
    if set(qb) != expected_qb or set(sjtl) != expected_sjtl or set(cb) != expected_cb:
        raise ConfigError("QB/serial-MERGE/sJTL/CB wiring differs from the registered diagonal map")
    if not t1_active:
        expected_terms = {f"R_TERM_{name} DOUT_{name} 0 2" for name in DIAGONALS}
        if set(terms) != expected_terms or len({line.split()[1] for line in terms}) != 7:
            raise ConfigError("each DOUT must have its own 2-ohm terminal")
    elif chain_active:
        chain_qa = _validate_chain_topology(case, t1_params, lines, probes, t1_source_info,
                                            t1_source_text, chain_source_texts, chain_source_info)
    else:
        if terms:
            raise ConfigError("T1 load mode forbids parallel 2-ohm DOUT terminal loads")
        if any(any(token in line for token in ("XCBU", "XDFF", "XJTL_")) for line in lines):
            raise ConfigError("T1 independent mode does not allow CBU, DFF, or additional JTL instances")
        t1_lines = [line for line in lines if line.startswith("XT1_D")]
        expected_t1_lines = {
            f"XT1_{name} T1_I_{name} CLK_{name} S_{name} C_{name} "
            f"N_BIAS1_{name} N_BIAS2_{name} N_BIAS3_{name} T1" for name in DIAGONALS}
        if len(t1_lines) != 7 or set(t1_lines) != expected_t1_lines:
            raise ConfigError("expected exactly seven independently pinned T1 instances")
        expected_links = {f"V_T1_LINK_{name} DOUT_{name} T1_I_{name} 0" for name in DIAGONALS}
        links = {line for line in lines if line.startswith("V_T1_LINK_")}
        if links != expected_links:
            raise ConfigError("each DOUT must feed only its matching T1_I through a zero-volt link")
        expected_s_loads = {f"R_S_{name} S_{name} 0 {t1_params['T1_R_S']}" for name in DIAGONALS}
        expected_c_loads = {f"R_C_{name} C_{name} 0 {t1_params['T1_R_C']}" for name in DIAGONALS}
        if {line for line in lines if line.startswith("R_S_D")} != expected_s_loads:
            raise ConfigError("each T1 Sum must have exactly one configured independent S load")
        if {line for line in lines if line.startswith("R_C_D")} != expected_c_loads:
            raise ConfigError("each T1 Carry must have exactly one configured independent C load")
        for index in (1, 2, 3):
            prefix = "V_BIAS" if index != 3 or t1_params["T1_BIAS3_SOURCE"] == "VOLTAGE" else "I_BIAS"
            expected_bias = set()
            for name in DIAGONALS:
                node = f"N_BIAS{index}_{name}"
                value = t1_params[f"T1_BIAS{index}"]
                if prefix.startswith("V"):
                    expected_bias.add(f"V_BIAS{index}_{name} {node} 0 DC {value}")
                else:
                    expected_bias.add(f"I_BIAS{index}_{name} 0 {node} DC {value}")
            actual_bias = {line for line in lines
                           if line.startswith((f"V_BIAS{index}_D", f"I_BIAS{index}_D"))}
            if actual_bias != expected_bias:
                raise ConfigError(f"bias source set {index} is not seven independent configured sources")
        clock_mode = t1_params["T1_CLK_MODE"]
        if clock_mode == "QUIET":
            expected_clock = {f"R_CLK_QUIET_{name} CLK_{name} 0 {t1_params['T1_CLK_QUIET_R']}" for name in DIAGONALS}
            actual_clock = {line for line in lines if line.startswith("R_CLK_QUIET_")}
            if actual_clock != expected_clock or any("TRIG_CLK" in line for line in lines):
                raise ConfigError("QUIET mode needs seven independent 5-ohm clock clamps and no pulse sources")
        else:
            expected_sources = {f"V_TRIG_CLK_{name} CLK_RAW_{name} 0 PULSE(0 {t1_params['T1_CLK_AMPLITUDE']} {t1_params['T1_CLK_START']} {t1_params['T1_CLK_RISE']} {t1_params['T1_CLK_FALL']} {t1_params['T1_CLK_WIDTH']} {t1_params['T1_CLK_PERIOD']})" for name in DIAGONALS}
            expected_series = {f"R_TRIG_CLK_{name} CLK_RAW_{name} CLK_{name} {t1_params['T1_CLK_SERIES_R']}" for name in DIAGONALS}
            if ({line for line in lines if line.startswith("V_TRIG_CLK_")} != expected_sources or
                    {line for line in lines if line.startswith("R_TRIG_CLK_")} != expected_series or
                    any("R_CLK_QUIET" in line for line in lines)):
                raise ConfigError("PULSE mode needs seven independent identical trigger/series branches and no quiet shunts")
        node_sets = {
            "T1_I": {f"T1_I_{name}" for name in DIAGONALS},
            "CLK": {f"CLK_{name}" for name in DIAGONALS},
            "S": {f"S_{name}" for name in DIAGONALS},
            "C": {f"C_{name}" for name in DIAGONALS},
            "BIAS": {f"N_BIAS{index}_{name}" for index in (1, 2, 3) for name in DIAGONALS},
        }
        if any(len(nodes) != (21 if key == "BIAS" else 7) for key, nodes in node_sets.items()):
            raise ConfigError("external T1 inputs, clocks, outputs, and bias nodes must be independent")
    if {line.split()[0] for line in stimulus_lines if line.startswith("I_WL_R")} != {f"I_WL_R{r}" for r in range(1,5)}:
        raise ConfigError("shared WL source count must be four")
    if {line.split()[0] for line in stimulus_lines if line.startswith("I_BL_C")} != {f"I_BL_C{c}" for c in range(1,5)}:
        raise ConfigError("shared BL source count must be four")
    se_lines = [line for line in stimulus_text.splitlines() if line.startswith("I_SE_")]
    if len(se_lines) != 16 or {line.split()[0] for line in se_lines} != {f"I_SE_{cell}" for cell in CELLS}:
        raise ConfigError("SE must have exactly one independent driver per BVM")
    if len({line.split()[2] for line in se_lines}) != 16:
        raise ConfigError("SE nodes must be electrically independent")
    expected_sources = {f"I_WL_R{r}" for r in range(1,5)} | {f"I_BL_C{c}" for c in range(1,5)} | {f"I_SE_{cell}" for cell in CELLS}
    if len(drivers) != 24 or {item["source"] for item in drivers} != expected_sources:
        raise ConfigError("expected 4 WL + 4 BL + 16 SE sources")
    deck_element_names = [line.split()[0].upper() for line in lines
                          if line and not line.startswith(("*", "."))]
    all_top_names = deck_element_names + [line.split()[0].upper() for line in stimulus_lines]
    if len(all_top_names) != len(set(all_top_names)):
        duplicates = sorted(name for name in set(all_top_names) if all_top_names.count(name) > 1)
        raise ConfigError(f"duplicate top-level device/source names: {duplicates}")
    printed = {line.split(None, 1)[1] for line in lines if line.startswith(".print ")}
    expected_prints = {item["label"] for item in probes["signals"]}
    if printed != expected_prints or len(printed) != probes["signal_count"]:
        raise ConfigError(".print directives do not exactly match the probe manifest")
    if len(stimulus_lines) != 24 or len({line.split()[0] for line in stimulus_lines}) != 24:
        raise ConfigError("stimulus must contain exactly 4 WL + 4 BL + 16 cell-SE PWL sources")
    if not all("PWL(" in line and line.endswith(")") for line in stimulus_lines):
        raise ConfigError("all shared and cell-local inputs must be PWL current sources")
    raw_estimate = estimate_raw_bytes(probes["signal_count"])
    if raw_estimate >= MAX_RAW_BYTES and probes["profile"] != "debug":
        raise ConfigError(f"raw size estimate exceeds ordinary Git single-file limit: {raw_estimate}")
    expected_active = _active_cells(case)
    if probes["profile"] == "focus" and probes["focus_diagonal"] not in DIAGONALS:
        raise ConfigError("focus diagonal must be D0..D6")
    source_shas = verify_sources()
    result = {"schema": "bvm-4x4-diagonal-static-qa-v2", "status": "PASS",
            "physical_solve_count": 0, "bvm_count": 16, "qb_count": 16,
            "sjtl_count": expected_sjtl_count,
            "sjtl_count_by_diagonal": {name: list(_sjtl_counts(case, name)) for name in DIAGONALS},
            "cb_count": 16, "terminal_count": expected_terminal_count,
            "input_driver_count": 24, "driver_count_by_branch": {"WL": 4, "BL": 4, "SE": 16},
            "diagonal_mapping_exact": True, "unique_outputs": True,
            "active_final_crosspoints": expected_active,
            "canonical_source_hashes_match": {role: item["sha256"] == SOURCE_SHA256[role]
                                                for role, item in source_shas.items()},
            "component_pin_orders": {key: list(value) for key, value in actual_pin_orders.items()},
            "stimulus_source_count": len(stimulus_lines),
            "stimulus_source_lines": stimulus_lines,
            "probe_count": probes["signal_count"],
            "raw_estimate_bytes": raw_estimate,
            "storage_guard": "REVIEW_REQUIRED" if raw_estimate >= MAX_RAW_BYTES else "PASS",
            "scientific_interpretation_performed": False}
    if case["OUTPUT_MODE"] == "DIAGONAL_T1_INDEPENDENT":
        result.update({"t1_count": 7, "independent_t1_links": 7,
                       "independent_sum_loads": 7, "independent_carry_loads": 7,
                       "independent_bias_sets": 7, "independent_clock_branches": 7,
                       "terminal_count": 0, "t1_clock_mode": t1_params["T1_CLK_MODE"],
                       "t1_tunable_source": t1_source_info,
                       "t1_source_default_body_equivalent": t1_source_info["default_body_equivalent_to_canonical"]})
    elif chain_active:
        result.update(chain_qa)
        result.update({"t1_tunable_source": t1_source_info,
                       "t1_source_default_body_equivalent": t1_source_info["default_body_equivalent_to_canonical"],
                       "chain_source_info": chain_source_info,
                       "t1_clock_start": case["T1_CHAIN_CLK_START"],
                       "t1_clock_parameters": {key: t1_params[key] for key in
                           ("T1_CLK_AMPLITUDE", "T1_CLK_RISE", "T1_CLK_WIDTH", "T1_CLK_FALL", "T1_CLK_SERIES_R")}})
    else:
        result["t1_mode_off_no_t1_cbu_dff"] = True
    return result


def estimate_raw_bytes(probe_count: int) -> int:
    reference_bytes = 95_388_793
    reference_probes = 284
    return math.ceil(reference_bytes * probe_count / reference_probes * 1.15)


def _solver_info() -> dict[str, Any]:
    if not SOLVER.is_file():
        raise ConfigError(f"JoSIM binary not found: {SOLVER}")
    version = subprocess.run([str(SOLVER), "--version"], cwd=REPO,
                             capture_output=True, text=True, check=True).stdout.strip()
    return {"path": str(SOLVER), "version": version, "sha256": sha256(SOLVER),
            "parent_head": subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO,
                                          capture_output=True, text=True, check=True).stdout.strip()}


def registered_cases() -> list[tuple[str, dict[str, str]]]:
    return [(name, {"CASE": name, **parse_env(SERIES / "presets" / f"{name}.env")})
            for name in REGISTERED_CASES]


def dry_run(case: dict[str, str], stimulus: dict[str, str], t1_params: dict[str, str],
            *, verbose: bool = False) -> int:
    preview = RUNS / "_PREVIEW_ONLY"
    rendered = render(case, stimulus, t1_params, preview)
    static = rendered["static_qa"]
    print("DRY RUN PASS — solver_invoked=false; physical_solve_count=0")
    if case["OUTPUT_MODE"] == "DIAGONAL_T1_CHAIN":
        active = ", ".join(static["active_final_crosspoints"])
        print(f"Case: {case['CASE']} | ROW/COL={case['ROW_BITS']}/{case['COL_BITS']} | SE mask={case['SE_ENABLE_MASK']}")
        print(f"Topology: 16 BVM→QB; 7 diagonal CB chains; D0→{case['D0_JTL_COUNT']} sJTL→T1_D0; "
              "D1..D6 + prior Carry→6 physical CBU→T1; C6→DFF.O")
        if case.get("CBU_OVERRIDE_D1", "NONE") == "CB_DIRECT":
            print("D1 override: CB_DIRECT — DOUT_D1 and C_D0 share CBU_JOIN_D1 via two 0V sensors; "
                  "one canonical CB_0928 feeds T1_D1; D2-D6 remain THmitll_MERGE; no added sJTL")
        elif case.get("CBU_OVERRIDE_D1", "NONE") == "CB_CARRY_BUFFER":
            print("D1 override: CB_CARRY_BUFFER — C_D0 passes through one canonical CB_0928; its output "
                  "joins DOUT_D1 at CBU_JOIN_D1 and directly feeds T1_D1; no added sJTL")
        else:
            print(f"D1 override: NONE — all six CBU stages use {case['CBU_TYPE']}")
        print(f"Independent stages: T1=7 | CBU=6 | D0 JTL={case['D0_JTL_COUNT']} | DFF=1; "
              f"DOUT terminals=0; C0-C6 loads=0; Sum loads={t1_params['T1_R_S']}Ω; "
              f"DFF.O load={t1_params['DFF_R_OUT']}Ω")
        print(f"Clock: {case['T1_CHAIN_CLOCK_MODE']} | start={case['T1_CHAIN_CLK_START']} | "
              f"amp={t1_params['T1_CLK_AMPLITUDE']} | rise/width/fall="
              f"{t1_params['T1_CLK_RISE']}/{t1_params['T1_CLK_WIDTH']}/{t1_params['T1_CLK_FALL']} | "
              f"series R={t1_params['T1_CLK_SERIES_R']}Ω; independent T1+DFF branches=8")
        print(f"Active FINAL_READ crosspoints: {active}")
        print(f"sJTL={static['sjtl_count']} | probes={static['probe_count']} | "
              f"estimated raw={static['raw_estimate_bytes']/1e6:.1f} MB/run | storage guard={static['storage_guard']}")
        print(f"Solver: {SOLVER} (not invoked); DT={case['DT']}; STOP={case['STOP']}; static QA={static['status']}")
        if verbose:
            print("\nPWL stimulus:\n" + rendered["stimulus_text"], end="")
            print("\nRendered deck:\n" + rendered["deck"], end="")
            print("\nProbe labels:\n" + "\n".join(x["label"] for x in rendered["probes"]["signals"]))
        print("No run directory created.")
        return 0
    print(f"Case: {case['CASE']} | OUTPUT_MODE={case['OUTPUT_MODE']} | T1_MODE={case['T1_MODE']}")
    print(f"ROW_BITS={case['ROW_BITS']} | COL_BITS={case['COL_BITS']} | SE_ENABLE_MASK={case['SE_ENABLE_MASK']}")
    print("Active FINAL_READ crosspoints: " + (", ".join(static["active_final_crosspoints"]) or "none"))
    print("Diagonal lengths: " + ", ".join(f"{name}={len(cells)}" for name, cells in DIAGONALS.items()))
    print(f"Drivers: 4 WL + 4 BL + 16 independent SE = {len(rendered['drivers'])}")
    print(f"Sources SHA verified: {len(rendered['sources'])}; "
          f"T1 instances={static.get('t1_count', 0)}; CBU=0; DFF=0")
    if case["OUTPUT_MODE"] == "DIAGONAL_T1_INDEPENDENT":
        print(f"T1 clock mode: {t1_params['T1_CLK_MODE']} (USER_CASE.env override)")
    print(f"Probes: {rendered['probes']['signal_count']} ({case['PROBE_PROFILE']}); "
          f"raw estimate ~{static['raw_estimate_bytes']/1e6:.1f} MB/run")
    print(f"Solver: {SOLVER} (not invoked); DT={case['DT']}; STOP={case['STOP']}; static QA={static['status']}")
    print("FINAL_READ programmed amplitudes: WL by row; BL=0; SE by row AND column AND SE mask.")
    if verbose:
        print("\nPWL stimulus:\n" + rendered["stimulus_text"], end="")
        print("\nRendered deck:\n" + rendered["deck"], end="")
        print("\nProbe labels:\n" + "\n".join(x["label"] for x in rendered["probes"]["signals"]))
    print("No run directory created.")
    return 0


def validate_registered_matrix() -> list[dict[str, Any]]:
    if not SOLVER.is_file() or not PLOTTER.is_file() or not PLOTLY_ASSET.is_file():
        raise ConfigError("solver, classic plotter, or shared Plotly asset is missing")
    source_records = verify_sources()
    results = []
    for name in REGISTERED_CASES:
        case, stimulus, t1_params = load_config(name)
        rendered = render(case, stimulus, t1_params, RUNS / "_PREVIEW_ONLY")
        if rendered["static_qa"]["status"] != "PASS":
            raise ConfigError(f"static validation failed for {name}")
        pages = plot_signals(rendered["probes"])
        if len(pages) != 2:
            raise ConfigError(f"{name}: expected exactly two registered standalone plot pages")
        results.append({"case": name, "case_config": case, "stimulus": stimulus,
                        "t1_params_sha256": hashlib.sha256(
                            (SERIES / "config" / "T1_PARAMS.env").read_bytes()).hexdigest(),
                        "deck_sha256": hashlib.sha256(rendered["deck"].encode()).hexdigest(),
                        "stimulus_sha256": hashlib.sha256(rendered["stimulus_text"].encode()).hexdigest(),
                        "probe_count": rendered["probes"]["signal_count"],
                        "plot_pages": [page["file"] for page in pages],
                        "static_qa": rendered["static_qa"]})
    if source_records.keys() != SOURCE_SHA256.keys():
        raise ConfigError("canonical source closure is incomplete")
    return results


def validate_bus400_matrix() -> list[dict[str, Any]]:
    """Static gate for exactly the two authorized 400u cases; invokes no transient solve."""
    source_records = verify_sources()
    rendered_cases = []
    for name in BUS400_CASES:
        case, stimulus, t1_params = load_config(name)
        if case["CASE"] != name:
            raise ConfigError(f"{name}: CASE identity does not match preset name")
        expected = {
            "ROW_BITS": "1111", "COL_BITS": "1111",
            "ROW_WL_WRITE_AMPLITUDE": "400u", "COL_BL_WRITE_AMPLITUDE": "400u",
            "ROW_WL_READ_AMPLITUDE": "400u", "COL_SE_READ_AMPLITUDE": "100u",
            "DT": "0.01p", "STOP": "250p", "PROBE_PROFILE": "focus",
            "T1_MODE": "OFF", "CBU_MODE": "OFF", "OUTPUT_MODE": "DIAGONAL_TERMINAL",
        }
        for key, value in expected.items():
            if case.get(key) != value:
                raise ConfigError(f"{name}: expected {key}={value}, found {case.get(key)}")
        expected_mask = ("0000/0000/0000/0000" if name == "BUS400_D3_N0"
                         else "1000/0000/0000/0000")
        if case["SE_ENABLE_MASK"] != expected_mask:
            raise ConfigError(f"{name}: expected SE mask {expected_mask}")
        if {d: _sjtl_counts(case, d) for d in DIAGONALS} != {
                "D0": (1,), "D1": (1, 1), "D2": (1, 1, 1), "D3": (1, 1, 1, 1),
                "D4": (1, 1, 1), "D5": (1, 1), "D6": (1,)}:
            raise ConfigError(f"{name}: this batch requires the default one-sJTL-per-level topology")
        rendered = render(case, stimulus, t1_params, RUNS / "_PREVIEW_ONLY")
        if rendered["static_qa"]["status"] != "PASS":
            raise ConfigError(f"{name}: static netlist QA failed")
        if rendered["probes"]["signal_count"] != 124:
            raise ConfigError(f"{name}: registered focus profile changed unexpectedly: {rendered['probes']['signal_count']} probes")
        rendered_cases.append({"case": case, "stimulus": stimulus, "t1_params": t1_params,
                               "rendered": rendered, "next_run_id": allocate_run_id(name)})

    existing_ids = [int(match.group(1)) for path in RUNS.glob("A[0-9][0-9][0-9]_*")
                    if (match := re.match(r"A(\d{3})_", path.name))]
    next_number = max(existing_ids, default=0) + 1
    for offset, item in enumerate(rendered_cases):
        item["next_run_id"] = f"A{next_number + offset:03d}_{item['case']['CASE']}"

    first, second = rendered_cases
    changed_case_keys = {key for key in first["case"]
                         if first["case"].get(key) != second["case"].get(key)}
    if changed_case_keys != {"CASE", "SE_ENABLE_MASK"}:
        raise ConfigError(f"BUS400 cases differ beyond their registered SE mask: {sorted(changed_case_keys)}")
    if first["rendered"]["deck"] != second["rendered"]["deck"]:
        raise ConfigError("BUS400 rendered circuit deck differs between matched cases")
    source_lines = []
    source_maps = []
    for item in rendered_cases:
        lines = {line.split(None, 1)[0]: line for line in item["rendered"]["stimulus_text"].splitlines()
                 if line.startswith("I_")}
        if len(lines) != 24:
            raise ConfigError(f"{item['case']['CASE']}: expected 24 shared/cell-local PWL sources")
        source_maps.append(lines)
    for index, item in enumerate(rendered_cases):
        case, lines = item["case"], source_maps[index]

        def values_at(source: str) -> dict[str, str]:
            tokens = lines[source].split("PWL(", 1)[1].removesuffix(")").split()
            return dict(zip(tokens[0::2], tokens[1::2], strict=True))

        for row in range(1, 5):
            pwl = values_at(f"I_WL_R{row}")
            expected_wl = {"51p": "-400u", "60p": "-400u", "71p": "400u", "80p": "400u",
                           "91p": "400u", "100p": "400u", "111p": "400u", "120p": "400u", "121p": "0"}
            if any(pwl.get(time) != value for time, value in expected_wl.items()):
                raise ConfigError(f"{case['CASE']}: WL row R{row} PWL levels do not match the registered four phases")
        for col in range(1, 5):
            pwl = values_at(f"I_BL_C{col}")
            expected_bl = {"51p": "-400u", "60p": "-400u", "71p": "0", "80p": "0",
                           "91p": "400u", "100p": "400u", "111p": "0", "120p": "0", "121p": "0"}
            if any(pwl.get(time) != value for time, value in expected_bl.items()):
                raise ConfigError(f"{case['CASE']}: BL column C{col} PWL levels do not match the registered four phases")
        for cell in CELLS:
            pwl = values_at(f"I_SE_{cell}")
            expected_final = "100u" if case["CASE"] == "BUS400_D3_N1" and cell == "R1C1" else "0"
            if pwl.get("71p") != "100u" or pwl.get("80p") != "100u" or pwl.get("111p") != expected_final:
                raise ConfigError(f"{case['CASE']}: SE PWL mismatch for {cell}; READ0 must be all-cell and FINAL_READ mask-gated")
    differing_sources = {source for source in source_maps[0]
                         if source_maps[0][source] != source_maps[1].get(source)}
    if differing_sources != {"I_SE_R1C1"}:
        raise ConfigError(f"BUS400 PWL differs outside the target FINAL_READ SE source: {sorted(differing_sources)}")
    for item, expected_final in zip(rendered_cases, ("0", "100u"), strict=True):
        line = source_maps[0 if expected_final == "0" else 1]["I_SE_R1C1"]
        points = line.split("PWL(", 1)[1].removesuffix(")").split()
        pairs = dict(zip(points[0::2], points[1::2], strict=True))
        if pairs.get("111p") != expected_final:
            raise ConfigError(f"{item['case']['CASE']}: target SE FINAL_READ PWL is not {expected_final} at 111p")
    expected_ids = ["A007_BUS400_D3_N0", "A008_BUS400_D3_N1"]
    if [item["next_run_id"] for item in rendered_cases] != expected_ids:
        raise ConfigError("new batch run allocation is not the expected non-overwriting A007/A008 pair")
    if any((RUNS / run_id).exists() for run_id in expected_ids):
        raise ConfigError("BUS400 output directory already exists; refusing to overwrite")
    if source_records.keys() != SOURCE_SHA256.keys():
        raise ConfigError("canonical source closure is incomplete")
    return rendered_cases


def _register_bus400_batch(cases: list[dict[str, Any]], solver_info: dict[str, Any]) -> None:
    data = json.loads(EXPERIMENT_MANIFEST.read_text(encoding="utf-8"))
    batches = data.setdefault("authorization_batches", [])
    if any(item.get("batch_id") == BUS400_BATCH_ID for item in batches):
        raise ConfigError(f"authorization batch already registered: {BUS400_BATCH_ID}")
    batches.append({"batch_id": BUS400_BATCH_ID, "risk_level": "NORMAL",
                    "authorized_cases": list(BUS400_CASES),
                    "run_ids": [item["next_run_id"] for item in cases],
                    "parent_head": BUS400_PARENT_HEAD,
                    "execution_source_head": solver_info["parent_head"],
                    "authorized_physical_solve_count": 2,
                    "probe_profile": "focus", "automatic_follow_up": False,
                    "scientific_interpretation_performed": False})
    data["maximum_physical_solve_count"] = max(int(data.get("maximum_physical_solve_count", 0)), 8)
    _json(EXPERIMENT_MANIFEST, data)


def build_bus400_comparison(run_ids: list[str], *, version_suffix: str = "") -> dict[str, Any]:
    import pandas as pd
    plotter = _plotter_module()
    suffix = f"_{version_suffix}" if version_suffix else ""
    target = PLOTS / "comparison" / f"BUS400_D3_matched{suffix}.html"
    if not PLOTLY_ASSET.is_file():
        raise ConfigError(f"shared Plotly JS asset is missing: {PLOTLY_ASSET}")
    if target.exists():
        raise FileExistsError(f"refusing to overwrite BUS400 comparison plot {target}")
    signals = ["I(R_SE|XBVM_R1C1)", "V(DOUT_D3)"]
    sections = []
    run_records = []
    for run_id in run_ids:
        run_dir = RUNS / run_id
        raw = run_dir / "raw.csv"
        before = sha256(raw)
        times, columns, _header = read_raw(raw, set(signals))
        frame = pd.DataFrame({"time": times, **{key: list(columns[key]) for key in signals}})
        fig = plotter.seperate_combined_layout(frame, SimpleNamespace(subset=signals, jump="2pi"))
        layout = plot_layout_metrics(signals)
        fig.update_layout(title=f"{run_id} — matched BUS400 signals", title_font_size=18,
                          template="plotly_dark", autosize=True, width=None,
                          height=layout["height_px"])
        sections.append(f"<section><h2>{html.escape(run_id)}</h2>" +
                        fig.to_html(full_html=False, include_plotlyjs=False,
                                    config={"responsive": True}) + "</section>")
        after = sha256(raw)
        if before != after:
            raise ConfigError(f"raw changed during paired visualization: {run_id}")
        run_records.append({"run_id": run_id, "raw_sha256_before": before,
                            "raw_sha256_after": after, "sample_count": len(times),
                            "signals": signals, "alignment": "independent native stored grids",
                            "interpolation_or_resampling": False})
    target.parent.mkdir(parents=True, exist_ok=True)
    asset_ref = Path(os.path.relpath(PLOTLY_ASSET, target.parent)).as_posix()
    page = ("<!doctype html><html><head><meta charset=\"utf-8\">"
            "<style>html,body,main{width:100%;margin:0;padding:0;}"
            "body{background:#111;overflow-x:hidden;}main{max-width:none;}</style>"
            f"<script src=\"{html.escape(asset_ref)}\"></script></head><body>"
            "<main style=\"width:100%;max-width:none;\">"
            "<h1>BUS400 D3 matched comparison</h1>"
            "<p>Classic josim-plot2 sep_comb/dark/-j 2pi; native stored grids, no interpolation. "
            "Descriptive only; phase turns are navigation arithmetic, not event counts.</p>" +
            "\n".join(sections) + "</main></body></html>\n")
    if "Plotly.newPlot" not in page or '"responsive": true' not in page or asset_ref not in page or "staticPlot" in page:
        raise ConfigError("responsive interactive Plotly comparison HTML QA failed")
    target.write_text(page, encoding="utf-8")
    qa = {"schema": "bvm-4x4-bus400-comparison-qa-v2", "status": "PASS",
          "path": target.relative_to(SERIES).as_posix(), "sha256": sha256(target),
          "runs": run_records, "signals": signals,
          "raws_immutable": all(item["raw_sha256_before"] == item["raw_sha256_after"] for item in run_records),
          "interpolation_or_resampling": False, "plotter_sha256": sha256(PLOTTER),
          "layout": plot_layout_metrics(signals), "responsive": True,
          "zoom_hover_legend_interactive": True, "version_suffix": version_suffix or None,
          "comparison_generator_path": Path(__file__).resolve().relative_to(REPO).as_posix(),
          "comparison_generator_sha256": sha256(Path(__file__).resolve()),
          "plotly_asset_sha256": sha256(PLOTLY_ASSET),
          "scientific_interpretation_performed": False}
    _json(SERIES / "analysis" / f"BUS400_comparison_qa{suffix}.json", qa)
    return qa


def write_bus400_handoff_manifests(run_ids: list[str], comparison_qa: dict[str, Any]) -> None:
    run_records = []
    for run_id in run_ids:
        run_dir = RUNS / run_id
        result = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
        metadata = json.loads((run_dir / "metadata.json").read_text(encoding="utf-8"))
        metrics = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))
        qa = json.loads((run_dir / "qa.json").read_text(encoding="utf-8"))
        run_records.append({"run_id": run_id, "case": result["case"],
                            "raw_path": (run_dir / "raw.csv").relative_to(SERIES).as_posix(),
                            "raw_sha256": result["raw_sha256"], "raw_bytes": result["raw_bytes"],
                            "deck_sha256": metadata["deck_sha256"],
                            "probe_manifest_sha256": metadata["probe_manifest_sha256"]
                            if "probe_manifest_sha256" in metadata else sha256(run_dir / "probe_manifest.json"),
                            "metric_spec_sha256": json.loads((run_dir / "provenance.json").read_text())["metric_spec_sha256"],
                            "probe_count": result["probe_count"], "windows": metrics["windows"],
                            "qa_status": qa["status"], "artifact_status": result["artifact_status"]})
    if any(item["qa_status"] != "PASS" or item["artifact_status"] != "VALID" for item in run_records):
        raise ConfigError("handoff manifest cannot be written unless both run QA records pass")
    evidence = ["# BUS400 evidence manifest", "",
                f"- Batch: `{BUS400_BATCH_ID}`; risk level: `NORMAL`.",
                f"- Parent HEAD: `{BUS400_PARENT_HEAD}`; authorized/actual solves: `2/2`.",
                "- Scientific interpretation: `NOT_PERFORMED`; automatic follow-up: `false`.",
                "- Raw CSVs are complete immutable solver outputs. HTML remains local and is excluded from the delta package.",
                f"- Paired visualization QA: `{comparison_qa['status']}` at `{comparison_qa['path']}`; SHA-256 `{comparison_qa['sha256']}`.",
                "", "| Run | Case | Raw bytes | Raw SHA-256 | Probes | QA |", "|---|---|---:|---|---:|---|"]
    for item in run_records:
        evidence.append(f"| {item['run_id']} | {item['case']} | {item['raw_bytes']} | "
                        f"`{item['raw_sha256']}` | {item['probe_count']} | VALID / PASS |")
    evidence.extend(["", "Deck/config/source/probe/topology hashes, actual-grid metrics, and phase/area arithmetic are in each run's metadata, provenance, and metrics files.",
                     "No event classifier, physical verdict, or mechanism conclusion is registered."])
    (SERIES / "EVIDENCE_MANIFEST.md").write_text("\n".join(evidence) + "\n", encoding="utf-8")
    _json(SERIES / "RAW_ANALYSIS_HANDOFF_MANIFEST.json", {
        "schema": "bvm-4x4-raw-analysis-handoff-v1", "batch_id": BUS400_BATCH_ID,
        "risk_level": "NORMAL", "runs": run_records,
        "registered_windows": ["WRITE0", "READ0", "WRITE1", "FINAL_READ",
                               "POST_FINAL_READ", "FINAL_READ_RESPONSE"],
        "paired_visualization": comparison_qa,
        "permitted_default_operations": ["raw integrity and actual-grid QA",
                                         "per-BVM input branch current arithmetic",
                                         "same-JJ phase/voltage arithmetic",
                                         "DOUT waveform extrema and signed area"],
        "prohibited_without_scientific_review_authorization": [
            "SFQ/event count classification", "mechanism interpretation", "parameter ranking",
            "follow-up solve or sweep"],
        "transformation_registry": {"interpolation": False, "resampling": False,
                                    "smoothing": False, "scaling": False,
                                    "time_shift": False},
        "scientific_interpretation_performed": False, "automatic_follow_up": False})
    _json(SERIES / "analysis" / "BUS400_transformation_registry.json", {
        "schema": "bvm-4x4-bus400-transformation-registry-v1", "runs": run_ids,
        "raw_transformed": False, "interpolation": False, "resampling": False,
        "smoothing": False, "scaling": False, "time_shift": False,
        "analysis_uses_actual_stored_timestamps": True})


def run_bus400_batch() -> int:
    cases = validate_bus400_matrix()
    if not (REPO / "build/josim-cli").is_file():
        raise ConfigError("recorded JoSIM binary is missing")
    if not (REPO / "docs/EXPERIMENT_CONTRACT.md").is_file():
        raise ConfigError("active experiment contract is missing")
    if not (SERIES / "analysis" / "BUS400_PREREGISTRATION.yaml").is_file():
        raise ConfigError("BUS400 preregistration artifact is missing")
    current = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO,
                              capture_output=True, text=True, check=True).stdout.strip()
    if current == BUS400_PARENT_HEAD or subprocess.run(
            ["git", "merge-base", "--is-ancestor", BUS400_PARENT_HEAD, current],
            cwd=REPO, capture_output=True, check=False).returncode != 0:
        raise ConfigError("current source HEAD is not descended from the registered parent")
    dirty = subprocess.run(["git", "status", "--porcelain=v1", "--untracked-files=all"],
                           cwd=REPO, capture_output=True, text=True, check=True).stdout.strip()
    if dirty:
        raise ConfigError("source/preflight worktree must be clean and committed before the physical batch")
    solver_info = _solver_info()
    run_ids = [item["next_run_id"] for item in cases]
    if len(set(run_ids)) != 2:
        raise ConfigError("BUS400 run IDs are not unique")
    _register_bus400_batch(cases, solver_info)
    _json(SERIES / "analysis" / "source_manifest.json", _source_manifest(verify_sources()))
    _json(SERIES / "analysis" / "topology_manifest.json",
          topology_manifest(verify_sources(), cases[0]["case"]))
    print(f"STATIC PREFLIGHT PASS: {BUS400_BATCH_ID}; parent={BUS400_PARENT_HEAD}; source_head={current}")
    print("Bus setpoints: WL WRITE=400u, BL WRITE=400u, WL READ=400u (shared source totals); cell SE=100u.")
    print("Measured per-BVM branch currents: I(R_WL|XBVM_*), I(R_BL|XBVM_*), I(R_SE|XBVM_*) from each raw.")
    print(f"D3 sJTL counts={','.join(map(str, _sjtl_counts(cases[0]['case'], 'D3')))}; "
          f"total sJTL={cases[0]['rendered']['static_qa']['sjtl_count']}; CB=16; terminals=7.")
    for item in cases:
        case = item["case"]
        print(f"{item['next_run_id']} {case['CASE']}: mask={case['SE_ENABLE_MASK']}; "
              f"probes={item['rendered']['probes']['signal_count']}; "
              f"raw_estimate={item['rendered']['static_qa']['raw_estimate_bytes']} bytes; "
              f"static={item['rendered']['static_qa']['status']}")
    print("Actual PWL gate difference: only I_SE_R1C1 at FINAL_READ; all earlier stages and all other sources match.")
    print(f"Authorized physical solves={len(BUS400_CASES)}; serial execution; failure on run 1 stops run 2.", flush=True)
    for item in cases:
        case, stimulus, t1_params = item["case"], item["stimulus"], item["t1_params"]
        print(f"START {case['CASE']}: {allocate_run_id(case['CASE'])}", flush=True)
        code, result = run_one(case, stimulus, t1_params, solver_info, batch_id=BUS400_BATCH_ID)
        print(json.dumps(result, ensure_ascii=False), flush=True)
        if code != 0:
            print("STOP: first solver/raw/mechanical/standalone-plot failure; no retry or second solve.",
                  file=sys.stderr)
            return code
    built = build_bus400_comparison(run_ids)
    print(f"Paired comparison QA: {built['status']} ({built['path']})")
    write_bus400_handoff_manifests(run_ids, built)
    return 0


def allocate_run_id(case_name: str) -> str:
    existing = [int(match.group(1)) for path in RUNS.glob("A[0-9][0-9][0-9]_*")
                if (match := re.match(r"A(\d{3})_", path.name))]
    return f"A{max(existing, default=0) + 1:03d}_{case_name}"


def _write_env(path: Path, values: dict[str, str]) -> None:
    path.write_text("".join(f"{key}={value}\n" for key, value in values.items()), encoding="utf-8")


def _prefixed_params(params: dict[str, str], prefix: str) -> dict[str, str]:
    return {key: value for key, value in params.items() if key.startswith(prefix)}


def read_raw(raw_path: Path, required: set[str] | None = None, *,
             exact_header: bool = False) -> tuple[list[float], dict[str, array.array], list[str]]:
    required = required or set()
    times: list[float] = []
    columns: dict[str, array.array] = {}
    with raw_path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.reader(stream)
        header = next(reader, None)
        if not header or header[0] != "time" or len(header) != len(set(header)):
            raise ConfigError("raw header is empty, not time-first, or has duplicate columns")
        missing = sorted(required - set(header))
        if missing:
            raise ConfigError(f"raw is missing required probes: {missing[:10]}")
        unexpected = sorted(set(header) - (required | {"time"}))
        if exact_header and unexpected:
            raise ConfigError(f"raw contains undeclared probes: {unexpected[:10]}")
        indexes = {label: header.index(label) for label in required}
        columns = {label: array.array("d") for label in required}
        previous = -math.inf
        for row_no, row in enumerate(reader, start=2):
            if len(row) != len(header):
                raise ConfigError(f"ragged raw row {row_no}")
            try:
                time_value = float(row[0])
                values = {label: float(row[index]) for label, index in indexes.items()}
            except ValueError as exc:
                raise ConfigError(f"non-numeric raw token at line {row_no}") from exc
            if not math.isfinite(time_value) or time_value <= previous or any(
                    not math.isfinite(value) for value in values.values()):
                raise ConfigError(f"non-finite or non-monotone raw data at line {row_no}")
            previous = time_value
            times.append(time_value)
            for label, value in values.items():
                columns[label].append(value)
    if len(times) < 2:
        raise ConfigError("raw contains fewer than two samples")
    return times, columns, header


def _windows_for_run(run_dir: Path) -> dict[str, tuple[float, float]]:
    case_snapshot = run_dir / "USER_CASE.snapshot.env"
    stimulus_snapshot = run_dir / "STIMULUS.snapshot.env"
    case = parse_env(case_snapshot if case_snapshot.is_file() else USER_CASE)
    stimulus = parse_env(stimulus_snapshot if stimulus_snapshot.is_file() else STIMULUS)
    windows: dict[str, tuple[float, float]] = {}
    for stage in STIMULUS_STAGES:
        start = _time_ps(stimulus[f"{stage}_START"])
        end = start + _time_ps(stimulus[f"{stage}_RISE"]) + _time_ps(stimulus[f"{stage}_HOLD"]) + _time_ps(stimulus[f"{stage}_FALL"])
        windows[stage] = (float(start), float(end))
    final_start = _time_ps(stimulus["FINAL_READ_START"])
    final_end = sum((_time_ps(stimulus[f"FINAL_READ_{suffix}"]) for suffix in ("START", "RISE", "HOLD", "FALL")), Decimal(0))
    stop = _time_ps(case["STOP"])
    windows["POST_FINAL_READ"] = (float(final_end), float(stop))
    windows["FINAL_READ_RESPONSE"] = (float(final_start), float(stop))
    return windows


def _window_indices(times: list[float], name: str,
                    windows_ps: dict[str, tuple[float, float]] | None = None) -> list[int]:
    start_ps, end_ps = (windows_ps or WINDOWS_PS)[name]
    start, end = start_ps * 1e-12, end_ps * 1e-12
    return [i for i, value in enumerate(times) if start <= value < end]


def _trapz(times: list[float], values: array.array, indices: list[int]) -> float:
    if len(indices) < 2:
        raise ConfigError("registered interval contains fewer than two stored samples")
    return sum((values[left] + values[right]) * 0.5 * (times[right] - times[left])
               for left, right in zip(indices, indices[1:]))


def _unwrap(values: array.array) -> list[float]:
    if not values:
        return []
    out = [values[0]]
    for prev, current in zip(values, values[1:]):
        delta = current - prev
        while delta > math.pi:
            delta -= 2 * math.pi
        while delta < -math.pi:
            delta += 2 * math.pi
        out.append(out[-1] + delta)
    return out


def analyze_raw(run_dir: Path, probe_manifest: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    raw = run_dir / "raw.csv"
    raw_before = sha256(raw)
    required = {item["label"] for item in probe_manifest["signals"]}
    times, columns, header = read_raw(raw, required, exact_header=True)
    raw_after = sha256(raw)
    if raw_before != raw_after:
        raise ConfigError("raw SHA changed during analysis")
    dt = [right - left for left, right in zip(times, times[1:])]
    windows_ps = _windows_for_run(run_dir)
    window_records = {}
    output_metrics = []
    for name, (start_ps, end_ps) in windows_ps.items():
        idx = _window_indices(times, name, windows_ps)
        if len(idx) < 2:
            raise ConfigError(f"window {name} has fewer than two samples")
        window_records[name] = {"start_s": start_ps * 1e-12,
                                "end_s": end_ps * 1e-12,
                                "boundary_rule": "[start,end)",
                                "sample_count": len(idx),
                                "first_stored_s": times[idx[0]],
                                "last_stored_s": times[idx[-1]]}
        for diagonal in DIAGONALS:
            signal = f"V(DOUT_{diagonal})"
            values = columns[signal]
            positive = max(idx, key=lambda i: values[i])
            negative = min(idx, key=lambda i: values[i])
            output_metrics.append({"signal": signal, "diagonal": diagonal, "window": name,
                                   "sample_count": len(idx), "min_v": values[negative],
                                   "max_v": values[positive],
                                   "peak_to_peak_v": values[positive] - values[negative],
                                   "time_of_positive_max_s": times[positive],
                                   "time_of_negative_min_s": times[negative],
                                   "signed_area_v_s": _trapz(times, values, idx),
                                   "interpolation_or_resampling": False})

    junction_metrics = []
    paired_phase = {item["label"] for item in probe_manifest["signals"] if item["label"].startswith("P(")}
    for phase_signal in sorted(paired_phase):
        voltage_signal = "V(" + phase_signal[2:]
        if voltage_signal not in columns:
            continue
        phase = _unwrap(columns[phase_signal])
        voltage = columns[voltage_signal]
        for name in windows_ps:
            idx = _window_indices(times, name, windows_ps)
            first, last = idx[0], idx[-1]
            delta = phase[last] - phase[first]
            area = _trapz(times, voltage, idx)
            junction_metrics.append({"phase_signal": phase_signal,
                                     "voltage_signal": voltage_signal,
                                     "window": name, "sample_count": len(idx),
                                     "phase_delta_rad": delta,
                                     "phase_delta_rad_over_2pi_navigation": delta / (2 * math.pi),
                                     "voltage_area_v_s_same_jj_same_rows": area,
                                     "voltage_area_phi0_arithmetic": area / PHI0,
                                     "phase_minus_area_turn_arithmetic": delta / (2 * math.pi) - area / PHI0,
                                     "interpolation_or_resampling": False})

    input_metrics = []
    for item in probe_manifest["signals"]:
        if not item["label"].startswith("I(R_") or not item.get("group", "").startswith("input:"):
            continue
        values = columns[item["label"]]
        for name in windows_ps:
            idx = _window_indices(times, name, windows_ps)
            vals = [values[i] for i in idx]
            input_metrics.append({"signal": item["label"], "cell": item.get("cell"),
                                  "branch": item.get("branch"), "window": name,
                                  "min_a": min(vals), "max_a": max(vals),
                                  "mean_sample_a": sum(vals) / len(vals),
                                  "peak_to_peak_a": max(vals)-min(vals),
                                  "charge_c": _trapz(times, values, idx),
                                  "direction": item.get("direction", "JoSIM element-reference direction"),
                                  "time_grid": "actual stored timestamps; [start,end); no interpolation"})

    raw_qa = {"schema": "bvm-4x4-diagonal-raw-qa-v1", "status": "PASS",
              "raw_sha256_before": raw_before, "raw_sha256_after_analysis": raw_after,
              "raw_immutable": True, "sample_count": len(times),
              "time_start_s": times[0], "time_end_s": times[-1],
              "dt_min_s": min(dt), "dt_max_s": max(dt),
              "uniform_time_grid": max(dt)-min(dt) <= max(dt)*1e-6,
              "probe_count": len(required), "header_count": len(header),
              "missing_probes": [], "duplicate_columns": [],
              "finite_values": True, "time_monotonic": True}
    metrics = {"schema": "bvm-4x4-diagonal-mechanical-metrics-v2",
               "status": "DERIVED_ARITHMETIC_ONLY", "raw_sha256": raw_before,
               "windows": window_records, "outputs": output_metrics,
               "junctions": junction_metrics, "input_branch_currents": input_metrics,
               "input_current_semantics": "actual per-BVM R_WL/R_BL/R_SE branch currents; bus setpoints are not treated as per-cell currents",
               "phase_raw_units": "radians",
               "phase_turns_definition": "unwrapped independently; delta/(2*pi), navigation only",
               "integration": "trapezoid on actual stored timestamps and same JJ/output samples",
               "interpolation_or_resampling": False,
               "event_classifier": None, "scientific_interpretation_performed": False}
    return metrics, raw_qa


def _voltage_lobe_candidates(times: list[float], values: array.array,
                             indices: list[int]) -> dict[str, Any]:
    """Describe prominent signed waveform extrema; this is not an event classifier."""
    max_positive = max((values[index] for index in indices), default=0.0)
    min_negative = min((values[index] for index in indices), default=0.0)
    separated_ps = T1_CANDIDATE_MORPHOLOGY_SPEC["minimum_peak_separation_ps"]
    candidates = []
    for polarity, threshold in (("positive", max_positive * 0.25),
                                ("negative", abs(min_negative) * 0.25)):
        if (polarity == "positive" and max_positive <= 0) or (polarity == "negative" and min_negative >= 0):
            continue
        points = []
        for position in range(1, len(indices) - 1):
            index = indices[position]
            before, after = values[indices[position - 1]], values[indices[position + 1]]
            value = values[index]
            is_peak = value >= before and value > after if polarity == "positive" else value <= before and value < after
            meets = (value >= threshold and value > 0) if polarity == "positive" else (abs(value) >= threshold and value < 0)
            if is_peak and meets and value != 0.0:
                points.append({"polarity": polarity, "time_s": times[index], "voltage_v": value})
        selected = []
        for point in sorted(points, key=lambda item: abs(item["voltage_v"]), reverse=True):
            if all(abs(point["time_s"] - other["time_s"]) >= separated_ps * 1e-12 for other in selected):
                selected.append(point)
        candidates.extend(sorted(selected, key=lambda item: item["time_s"]))
    return {"candidate_count": len(candidates),
            "positive_candidate_count": sum(item["polarity"] == "positive" for item in candidates),
            "negative_candidate_count": sum(item["polarity"] == "negative" for item in candidates),
            "candidates": [{**item, "time_ps": item["time_s"] * 1e12} for item in candidates],
            "method": dict(T1_CANDIDATE_MORPHOLOGY_SPEC),
            "classification_boundary": "descriptive waveform lobes only; not SFQ/event count"}


def analyze_t1_array_raw(run_dir: Path, probe_manifest: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    raw = run_dir / "raw.csv"
    raw_before = sha256(raw)
    required = {item["label"] for item in probe_manifest["signals"]}
    times, columns, header = read_raw(raw, required, exact_header=True)
    raw_after = sha256(raw)
    if raw_before != raw_after:
        raise ConfigError("raw SHA changed during T1-array analysis")
    dt = [right - left for left, right in zip(times, times[1:])]
    windows = {}
    window_indices = {}
    for name, (start_ps, end_ps) in T1_WINDOWS_PS.items():
        indices = _window_indices(times, name, T1_WINDOWS_PS)
        if len(indices) < 2:
            raise ConfigError(f"T1 window {name} has fewer than two stored samples")
        window_indices[name] = indices
        windows[name] = {"start_ps": start_ps, "end_ps": end_ps,
                         "boundary_rule": "[start,end)", "sample_count": len(indices),
                         "first_stored_s": times[indices[0]], "last_stored_s": times[indices[-1]],
                         "integration": "actual stored timestamp trapezoid; no interpolation"}

    waveforms = []
    junctions = []
    currents = []
    for item in probe_manifest["signals"]:
        label = item["label"]
        if label.startswith("V("):
            values = columns[label]
            for window, indices in window_indices.items():
                positive = max(indices, key=lambda index: values[index])
                negative = min(indices, key=lambda index: values[index])
                record = {"signal": label, "group": item["group"], "window": window,
                          "unit": "V", "min_v": values[negative], "max_v": values[positive],
                          "peak_to_peak_v": values[positive] - values[negative],
                          "time_of_max_s": times[positive], "time_of_min_s": times[negative],
                          "signed_area_v_s": _trapz(times, values, indices),
                          "interpolation_or_resampling": False}
                if item["group"].startswith("t1_output:"):
                    record["waveform_lobe_candidates"] = _voltage_lobe_candidates(times, values, indices)
                waveforms.append(record)
        elif label.startswith("I("):
            values = columns[label]
            for window, indices in window_indices.items():
                selected = [values[index] for index in indices]
                currents.append({"signal": label, "group": item["group"], "window": window,
                                 "unit": "A", "min_a": min(selected), "max_a": max(selected),
                                 "peak_to_peak_a": max(selected) - min(selected),
                                 "charge_c": _trapz(times, values, indices),
                                 "direction": item.get("direction", "JoSIM element-reference direction")})
        elif label.startswith("P("):
            voltage_label = "V(" + label[2:]
            if voltage_label not in columns:
                raise ConfigError(f"same-JJ voltage cross-check probe missing: {voltage_label}")
            phase = _unwrap(columns[label])
            voltage = columns[voltage_label]
            for window, indices in window_indices.items():
                first, last = indices[0], indices[-1]
                delta = phase[last] - phase[first]
                area = _trapz(times, voltage, indices)
                junctions.append({"phase_signal": label, "voltage_signal": voltage_label,
                                  "window": window, "sample_count": len(indices),
                                  "phase_delta_rad": delta,
                                  "phase_delta_rad_over_2pi_navigation": delta / (2 * math.pi),
                                  "voltage_area_v_s_same_jj_same_rows": area,
                                  "voltage_area_phi0_arithmetic": area / PHI0,
                                  "phase_minus_area_turn_arithmetic": delta / (2 * math.pi) - area / PHI0,
                                  "interpolation_or_resampling": False})
    qa = {"schema": "bvm-4x4-t1-array-raw-qa-v1", "status": "PASS",
          "raw_sha256_before": raw_before, "raw_sha256_after_analysis": raw_after,
          "raw_immutable": True, "sample_count": len(times), "header_count": len(header),
          "probe_count": len(required), "time_start_s": times[0], "time_end_s": times[-1],
          "dt_min_s": min(dt), "dt_max_s": max(dt),
          "uniform_time_grid": max(dt) - min(dt) <= max(dt) * 1e-6,
          "finite_values": True, "time_monotonic": True,
          "windows": windows, "interpolation_or_resampling": False}
    metrics = {"schema": "bvm-4x4-t1-array-mechanical-metrics-v1",
               "status": "DERIVED_ARITHMETIC_ONLY", "raw_sha256": raw_before,
               "windows": windows, "waveforms": waveforms, "currents": currents,
               "same_jj_phase_voltage": junctions,
               "phase_raw_units": "radians",
               "phase_turns_definition": "unwrapped independently; delta/(2*pi), navigation only",
               "integration": "trapezoid on actual stored timestamp rows; half-open windows",
               "candidate_morphology": dict(T1_CANDIDATE_MORPHOLOGY_SPEC),
               "event_classifier": None, "scientific_interpretation_performed": False}
    return metrics, qa


def analyze_t1_chain_raw(run_dir: Path, probe_manifest: dict[str, Any],
                         case: dict[str, str]) -> tuple[dict[str, Any], dict[str, Any]]:
    raw = run_dir / "raw.csv"
    raw_before = sha256(raw)
    required = {item["label"] for item in probe_manifest["signals"]}
    times, columns, header = read_raw(raw, required, exact_header=True)
    raw_after = sha256(raw)
    if raw_before != raw_after:
        raise ConfigError("chain raw SHA changed during analysis")
    dt = [right-left for left, right in zip(times, times[1:])]
    stimulus_snapshot = parse_env(run_dir / "STIMULUS.snapshot.env")
    params_snapshot = parse_env(run_dir / "T1_PARAMS.snapshot.env")
    read_start = _time_ps(stimulus_snapshot["FINAL_READ_START"])
    read_end = sum((_time_ps(stimulus_snapshot[f"FINAL_READ_{suffix}"])
                    for suffix in ("START", "RISE", "HOLD", "FALL")), Decimal(0))
    clock_start = _time_ps(case["T1_CHAIN_CLK_START"])
    pulse_duration = sum((_time_ps(params_snapshot[f"T1_CLK_{suffix}"])
                          for suffix in ("RISE", "WIDTH", "FALL")), Decimal(0))
    clock_edge_end = clock_start + pulse_duration + Decimal(1)
    stop = _time_ps(case["STOP"])
    windows_ps = {
        "ARRAY_FINAL_READ": (float(read_start), float(read_end)),
        "PRE_CLOCK": (float(read_end), float(clock_start)),
        "BEFORE_CLOCK": (0.0, float(clock_start)),
        "CLOCK_EDGE": (float(clock_start), float(clock_edge_end)),
        "POST_CLOCK": (float(clock_edge_end), float(stop)),
        "TOTAL": (0.0, float(stop)),
    }
    windows = {}
    window_indices = {}
    for name, (start_ps, end_ps) in windows_ps.items():
        indices = _window_indices(times, name, windows_ps)
        if len(indices) < 2:
            raise ConfigError(f"chain window {name} has fewer than two actual stored samples")
        window_indices[name] = indices
        windows[name] = {"start_ps": start_ps, "end_ps": end_ps,
                         "boundary_rule": "[start,end)", "sample_count": len(indices),
                         "first_stored_s": times[indices[0]], "last_stored_s": times[indices[-1]],
                         "integration": "trapezoid over actual stored timestamps; no interpolation"}

    waveforms = []
    currents = []
    junctions = []
    for item in probe_manifest["signals"]:
        label = item["label"]
        if label.startswith("V("):
            values = columns[label]
            for window, indices in window_indices.items():
                high = max(indices, key=lambda idx: values[idx])
                low = min(indices, key=lambda idx: values[idx])
                record = {"signal": label, "group": item["group"], "window": window,
                          "unit": "V", "min_v": values[low], "max_v": values[high],
                          "peak_to_peak_v": values[high]-values[low],
                          "time_of_max_s": times[high], "time_of_min_s": times[low],
                          "signed_area_v_s": _trapz(times, values, indices),
                          "signed_area_phi0_arithmetic": _trapz(times, values, indices)/PHI0,
                          "interpolation_or_resampling": False}
                if label in {f"V(DOUT_{name})" for name in DIAGONALS} or "chain_cbu" in item["group"] or item["group"].startswith("chain_t1:"):
                    record["descriptive_lobe_candidates"] = _voltage_lobe_candidates(times, values, indices)
                waveforms.append(record)
        elif label.startswith("I("):
            values = columns[label]
            for window, indices in window_indices.items():
                selected = [values[idx] for idx in indices]
                currents.append({"signal": label, "group": item["group"], "window": window,
                                 "unit": "A", "min_a": min(selected), "max_a": max(selected),
                                 "peak_to_peak_a": max(selected)-min(selected),
                                 "charge_c": _trapz(times, values, indices),
                                 "direction": item.get("direction", "JoSIM element-reference direction")})
        elif label.startswith("P("):
            voltage_label = "V(" + label[2:]
            if voltage_label not in columns:
                raise ConfigError(f"same-JJ voltage cross-check probe missing: {voltage_label}")
            phase = _unwrap(columns[label])
            voltage = columns[voltage_label]
            for window, indices in window_indices.items():
                first, last = indices[0], indices[-1]
                delta = phase[last]-phase[first]
                area = _trapz(times, voltage, indices)
                junctions.append({"phase_signal": label, "voltage_signal": voltage_label,
                                  "window": window, "sample_count": len(indices),
                                  "phase_delta_rad": delta,
                                  "phase_delta_rad_over_2pi_navigation": delta/(2*math.pi),
                                  "voltage_area_v_s_same_jj_same_rows": area,
                                  "voltage_area_phi0_arithmetic": area/PHI0,
                                  "phase_minus_area_turn_arithmetic": delta/(2*math.pi)-area/PHI0,
                                  "interpolation_or_resampling": False})

    waveform_index = {(item["signal"], item["window"]): item for item in waveforms}
    timing = []
    clock_ps = float(clock_start)

    def last_candidate(signal: str) -> float | None:
        record = waveform_index.get((signal, "BEFORE_CLOCK"))
        if not record:
            return None
        candidates = record.get("descriptive_lobe_candidates", {}).get("candidates", [])
        if not candidates:
            return None
        return max(item["time_ps"] for item in candidates)

    for index, diagonal in enumerate(DIAGONALS):
        stage_inputs = [("D_INPUT", f"V(DOUT_{diagonal})")]
        if index > 0:
            stage_inputs.append(("PREVIOUS_CARRY", f"V(C_D{index-1})"))
            if index == 1 and case.get("CBU_OVERRIDE_D1", "NONE") == "CB_CARRY_BUFFER":
                stage_inputs.append(("BUFFERED_CARRY", "V(CARRY_CB_OUT_D1)"))
                stage_inputs.append(("JOIN", "V(CBU_JOIN_D1)"))
            else:
                stage_inputs.append(("CBU_OUTPUT", f"V(CBU_OUT_{diagonal})"))
        else:
            stage_inputs.append(("D0_JTL_OUTPUT", "V(T1_I_D0)"))
        stage_inputs.append(("T1_INPUT", f"V(T1_I_{diagonal})"))
        candidates = [{"boundary": role, "signal": signal, "last_descriptive_lobe_candidate_ps": last_candidate(signal)}
                      for role, signal in stage_inputs]
        valid = [item["last_descriptive_lobe_candidate_ps"] for item in candidates
                 if item["last_descriptive_lobe_candidate_ps"] is not None]
        last_input = max(valid) if valid else None
        actual_clock_peak_s = (waveform_index.get((f"V(CLK_{diagonal})", "CLOCK_EDGE"), {}).get("time_of_max_s")
                               if case["T1_CHAIN_CLOCK_MODE"] == "GLOBAL_ONESHOT" else None)
        timing.append({"stage": diagonal, "boundaries": candidates,
                       "last_descriptive_input_candidate_ps": last_input,
                       "configured_clock_mode": case["T1_CHAIN_CLOCK_MODE"],
                       "configured_clock_start_ps": clock_ps if case["T1_CHAIN_CLOCK_MODE"] == "GLOBAL_ONESHOT" else None,
                       "candidate_time_to_clock_margin_ps": (clock_ps-last_input)
                       if last_input is not None and case["T1_CHAIN_CLOCK_MODE"] == "GLOBAL_ONESHOT" else None,
                       "actual_clock_peak_time_ps": actual_clock_peak_s*1e12 if actual_clock_peak_s is not None else None,
                       "timing_label": "descriptive lobe-candidate navigation only; not event timing/count"})

    raw_qa = {"schema": "bvm-4x4-t1-chain-raw-qa-v1", "status": "PASS",
              "raw_sha256_before": raw_before, "raw_sha256_after_analysis": raw_after,
              "raw_immutable": True, "sample_count": len(times), "header_count": len(header),
              "probe_count": len(required), "time_start_s": times[0], "time_end_s": times[-1],
              "dt_min_s": min(dt), "dt_max_s": max(dt),
              "uniform_time_grid": max(dt)-min(dt) <= max(dt)*1e-6,
              "finite_values": True, "time_monotonic": True,
              "windows": windows, "interpolation_or_resampling": False}
    metrics = {"schema": "bvm-4x4-t1-chain-mechanical-metrics-v1",
               "status": "DERIVED_ARITHMETIC_ONLY", "raw_sha256": raw_before,
               "windows": windows, "waveforms": waveforms, "currents": currents,
               "same_jj_phase_voltage": junctions, "stage_timing_descriptors": timing,
               "phase_raw_units": "radians",
               "phase_turns_definition": "independently unwrapped; delta/(2*pi), navigation only",
               "integration": "trapezoid on actual stored timestamp rows; half-open windows",
               "lobe_candidate_method": dict(T1_CANDIDATE_MORPHOLOGY_SPEC),
               "lobe_candidates_are_event_counts": False,
               "event_classifier": None, "actual_product_bit_decoding": "NOT_PERFORMED; no decode threshold preregistered",
               "interpolation_or_resampling": False, "scientific_interpretation_performed": False}
    return metrics, raw_qa


def _metric_record(index: dict[tuple[str, str], dict[str, Any]], signal: str,
                   window: str) -> dict[str, Any]:
    try:
        return index[(signal, window)]
    except KeyError as exc:
        raise ConfigError(f"T1 summary metric missing: {signal} / {window}") from exc


def _validate_t1_run_identity(run_id: str, result: dict[str, Any], qa: dict[str, Any],
                              t1_qa: dict[str, Any], metrics: dict[str, Any],
                              raw_hash: str) -> None:
    if (result.get("artifact_status") != "VALID" or qa.get("status") != "PASS" or
            t1_qa.get("status") != "PASS" or raw_hash != result.get("raw_sha256") or
            t1_qa.get("raw_sha256_after_analysis") != raw_hash):
        raise ConfigError(f"run QA/raw identity is not valid for T1-array summary: {run_id}")
    if (result.get("physical_solve_count") != 1 or
            metrics.get("t1_array", {}).get("raw_sha256") != raw_hash):
        raise ConfigError(f"run/metric solve or raw identity mismatch: {run_id}")


def build_t1_array_summary(run_ids: list[str]) -> dict[str, Any]:
    if run_ids != [item[0] for item in T1_ARRAY_RUN_MATRIX]:
        raise ConfigError(f"T1 summary run order/closure mismatch: {run_ids}")
    if T1_ARRAY_RESULTS.exists() or T1_ARRAY_TABLE.exists():
        raise FileExistsError("refusing to overwrite prior T1-array summary artifacts")
    runs: dict[str, dict[str, Any]] = {}
    run_metrics: dict[str, dict[str, Any]] = {}
    run_cases: dict[str, dict[str, Any]] = {}
    for run_id in run_ids:
        run_dir = RUNS / run_id
        result = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
        qa = json.loads((run_dir / "qa.json").read_text(encoding="utf-8"))
        t1_qa = json.loads((run_dir / "t1_array_qa.json").read_text(encoding="utf-8"))
        case_manifest = json.loads((run_dir / "case_manifest.json").read_text(encoding="utf-8"))
        metrics = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))
        raw = run_dir / "raw.csv"
        raw_hash = sha256(raw)
        _validate_t1_run_identity(run_id, result, qa, t1_qa, metrics, raw_hash)
        case = case_manifest["case"]
        run_cases[run_id] = {"case": case, "t1_params": case_manifest["t1_params"],
                             "stimulus": case_manifest["stimulus"]}
        runs[run_id] = {"run_id": run_id, "case": case["CASE"],
                        "population": "ALL" if case["ROW_BITS"] == "1111" else "PAPER",
                        "row_bits": case["ROW_BITS"], "column_bits": case["COL_BITS"],
                        "t1_clk_mode": result["t1_clk_mode"],
                        "configured_input_cells_by_diagonal": {
                            name: [cell for cell in cells if cell in result["active_final_crosspoints"]]
                            for name, cells in DIAGONALS.items()},
                        "physical_solve_count": 1, "artifact_status": result["artifact_status"],
                        "qa_status": qa["status"], "t1_array_qa_status": t1_qa["status"],
                        "raw_path": (raw.relative_to(SERIES).as_posix()), "raw_sha256": raw_hash,
                        "raw_bytes": raw.stat().st_size, "sample_count": t1_qa["sample_count"],
                        "time_range_s": [t1_qa["time_start_s"], t1_qa["time_end_s"]],
                        "dt_min_s": t1_qa["dt_min_s"], "dt_max_s": t1_qa["dt_max_s"],
                        "probe_count": t1_qa["probe_count"],
                        "deck_sha256": result.get("deck_sha256")}
        wave_index = {(item["signal"], item["window"]): item
                      for item in metrics["t1_array"]["waveforms"]}
        run_metrics[run_id] = {"wave": wave_index,
                               "junctions": metrics["t1_array"]["same_jj_phase_voltage"],
                               "currents": metrics["t1_array"]["currents"],
                               "metric_sha256": sha256(run_dir / "metrics.json")}

    pairs = {}
    for population in ("ALL", "PAPER"):
        selected = [record for record in runs.values() if record["population"] == population]
        by_mode = {record["t1_clk_mode"]: record for record in selected}
        if set(by_mode) != {"QUIET", "PULSE"}:
            raise ConfigError(f"matched QUIET/PULSE pair incomplete for {population}")
        quiet_id, pulse_id = by_mode["QUIET"]["run_id"], by_mode["PULSE"]["run_id"]
        quiet_case = run_cases[quiet_id]
        pulse_case = run_cases[pulse_id]
        if (quiet_case["stimulus"] != pulse_case["stimulus"] or
                {key: value for key, value in quiet_case["case"].items()
                 if key not in {"CASE", "T1_CLK_MODE"}} !=
                {key: value for key, value in pulse_case["case"].items()
                 if key not in {"CASE", "T1_CLK_MODE"}} or
                {key: value for key, value in quiet_case["t1_params"].items() if key != "T1_CLK_MODE"} !=
                {key: value for key, value in pulse_case["t1_params"].items() if key != "T1_CLK_MODE"}):
            raise ConfigError(f"saved QUIET/PULSE run snapshots differ beyond T1_CLK_MODE for {population}")
        pairs[population] = {"quiet_run_id": quiet_id, "pulse_run_id": pulse_id,
                             "same_row_col_bits": by_mode["QUIET"]["row_bits"] == by_mode["PULSE"]["row_bits"] and
                                                 by_mode["QUIET"]["column_bits"] == by_mode["PULSE"]["column_bits"],
                             "only_registered_circuit_condition_difference": "T1_CLK_MODE"}

    rows = []
    for population, pair in pairs.items():
        quiet, pulse = pair["quiet_run_id"], pair["pulse_run_id"]
        for diagonal in DIAGONALS:
            configured = runs[quiet]["configured_input_cells_by_diagonal"][diagonal]
            for kind, signal_template in (("INPUT", "V(T1_I_{d})"),
                                          ("SUM", "V(S_{d})"),
                                          ("CARRY", "V(C_{d})")):
                signal = signal_template.format(d=diagonal)
                q_index, p_index = run_metrics[quiet]["wave"], run_metrics[pulse]["wave"]
                total_q = _metric_record(q_index, signal, "TOTAL")
                total_p = _metric_record(p_index, signal, "TOTAL")
                row = {"population": population, "diagonal": diagonal,
                       "configured_input_cell_count": len(configured),
                       "configured_input_cells": ",".join(configured),
                       "kind": kind, "signal": signal,
                       "quiet_run_id": quiet, "quiet_raw_sha256": runs[quiet]["raw_sha256"],
                       "pulse_run_id": pulse, "pulse_raw_sha256": runs[pulse]["raw_sha256"],
                       "quiet_total_signed_area_v_s": total_q["signed_area_v_s"],
                       "pulse_total_signed_area_v_s": total_p["signed_area_v_s"],
                       "quiet_total_min_v": total_q["min_v"], "quiet_total_max_v": total_q["max_v"],
                       "pulse_total_min_v": total_p["min_v"], "pulse_total_max_v": total_p["max_v"],
                       "quiet_total_max_time_ps": total_q["time_of_max_s"] * 1e12,
                       "pulse_total_max_time_ps": total_p["time_of_max_s"] * 1e12,
                       "quiet_total_waveform_lobes": total_q.get("waveform_lobe_candidates"),
                       "pulse_total_waveform_lobes": total_p.get("waveform_lobe_candidates")}
                for window in ("PRE_CLOCK", "CLOCK_1", "CLOCK_2"):
                    q_item = _metric_record(q_index, signal, window)
                    p_item = _metric_record(p_index, signal, window)
                    row[f"quiet_{window.lower()}_signed_area_v_s"] = q_item["signed_area_v_s"]
                    row[f"pulse_{window.lower()}_signed_area_v_s"] = p_item["signed_area_v_s"]
                    if kind in {"SUM", "CARRY"}:
                        row[f"quiet_{window.lower()}_waveform_lobes"] = q_item.get("waveform_lobe_candidates")
                        row[f"pulse_{window.lower()}_waveform_lobes"] = p_item.get("waveform_lobe_candidates")
                rows.append(row)

    fieldnames = list(dict.fromkeys(key for row in rows for key in row))
    with T1_ARRAY_TABLE.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows({key: json.dumps(value, ensure_ascii=False, separators=(",", ":"))
                          if isinstance(value, (dict, list)) else value
                          for key, value in row.items()} for row in rows)

    jj_rows = []
    for run_id in run_ids:
        for item in run_metrics[run_id]["junctions"]:
            jj_rows.append({"run_id": run_id, **item})
    jj_table = T1_ARRAY_ANALYSIS / "T1_ARRAY_JJ_PHASE_AREA.csv"
    if jj_table.exists():
        raise FileExistsError(f"refusing to overwrite T1 JJ table: {jj_table}")
    jj_fields = list(jj_rows[0]) if jj_rows else []
    with jj_table.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=jj_fields)
        writer.writeheader()
        writer.writerows(jj_rows)

    summary = {"schema": "bvm-4x4-t1-array-results-v1", "batch_id": T1_ARRAY_BATCH_ID,
               "status": "MECHANICAL_QA_PASS_AWAITING_USER_REVIEW",
               "physical_solve_count": 4, "runs": list(runs.values()), "matched_pairs": pairs,
               "input_population_counts_reference_only": {
                   "ALL": [1, 2, 3, 4, 3, 2, 1], "PAPER": [1, 1, 1, 3, 1, 1, 1]},
               "registered_windows_ps": {key: list(value) for key, value in T1_WINDOWS_PS.items()},
               "table_path": T1_ARRAY_TABLE.relative_to(SERIES).as_posix(),
               "jj_phase_area_path": jj_table.relative_to(SERIES).as_posix(),
               "table_rows": rows,
               "waveform_lobe_candidate_spec": dict(T1_CANDIDATE_MORPHOLOGY_SPEC),
               "waveform_lobe_candidates_are_not_event_counts": True,
               "interpolation_or_resampling": False,
               "timestep_convergence": "UNKNOWN_NOT_AUTHORIZED",
               "scientific_interpretation_performed": False,
               "automatic_follow_up": False}
    if T1_ARRAY_RESULTS.exists():
        raise FileExistsError(f"refusing to overwrite T1 result summary: {T1_ARRAY_RESULTS}")
    _json(T1_ARRAY_RESULTS, summary)
    brief_path = T1_ARRAY_ANALYSIS / "RESULT_BRIEF.md"
    if brief_path.exists():
        raise FileExistsError(f"refusing to overwrite T1 result brief: {brief_path}")
    lines = ["# 4×4 BVM → seven independent T1 arrays", "",
             f"- Batch: `{T1_ARRAY_BATCH_ID}`; mechanical QA: `PASS`; physical solves: 4.",
             "- Interpretation: `NOT_PERFORMED`; all areas and phase deltas are registered arithmetic, not SFQ counts.",
             "- The configured input-cell population is a topology reference, not a measured pulse/event count.",
             "- QUIET/PULSE are paired at fixed BVM topology and parameters; no pass/fail threshold is defined for Sum/Carry behavior.",
             "- Waveform lobe candidates use the preregistered relative-extrema rule and are descriptive only.",
             "- Timestep convergence: `UNKNOWN`; no additional solve authorized.", "",
             "| Population | D | Configured cells | Signal | Q total area (V·s) | P total area (V·s) | Q pre / clk1 / clk2 (V·s) | P pre / clk1 / clk2 (V·s) | Q/P lobe candidates |",
             "|---|---|---|---|---:|---:|---|---|---|"]
    for row in rows:
        qlobes = row.get("quiet_total_waveform_lobes")
        plobes = row.get("pulse_total_waveform_lobes")
        qcount = "—" if qlobes is None else str(qlobes["candidate_count"])
        pcount = "—" if plobes is None else str(plobes["candidate_count"])
        qareas = " / ".join(f"{row[f'quiet_{window}_signed_area_v_s']:.4g}" for window in
                             ("pre_clock", "clock_1", "clock_2"))
        pareas = " / ".join(f"{row[f'pulse_{window}_signed_area_v_s']:.4g}" for window in
                             ("pre_clock", "clock_1", "clock_2"))
        lines.append(f"| {row['population']} | {row['diagonal']} | {row['configured_input_cell_count']} | {row['kind']} | "
                     f"{row['quiet_total_signed_area_v_s']:.4g} | {row['pulse_total_signed_area_v_s']:.4g} | "
                     f"{qareas} | {pareas} | {qcount} / {pcount} |")
    lines.extend(["", f"- Full arithmetic table: `{T1_ARRAY_TABLE.relative_to(SERIES).as_posix()}`.",
                  f"- Same-JJ phase/voltage-area records: `{jj_table.relative_to(SERIES).as_posix()}`.",
                  "- Per-run raw, deck, probes, source snapshot and QA are in `runs/A013`–`runs/A016`."])
    brief_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary


def finalize_t1_array_batch() -> int:
    if not T1_ARRAY_BATCH_MANIFEST.is_file():
        raise ConfigError("T1-array batch manifest is missing; there is no completed batch to finalize")
    batch = json.loads(T1_ARRAY_BATCH_MANIFEST.read_text(encoding="utf-8"))
    expected_ids = [item[0] for item in T1_ARRAY_RUN_MATRIX]
    records = batch.get("runs", [])
    if (batch.get("batch_id") != T1_ARRAY_BATCH_ID or
            [item.get("run_id") for item in records] != expected_ids or
            batch.get("physical_solve_count_completed") != 4 or
            any(item.get("status") != "MECHANICAL_QA_PASS_AWAITING_USER_REVIEW" or
                item.get("artifact_status") != "VALID" or
                item.get("physical_solve_count") != 1 or not item.get("raw_sha256")
                for item in records)):
        raise ConfigError("T1-array batch does not contain four valid, QA-passed authorized runs")
    summary = build_t1_array_summary(expected_ids)
    batch["status"] = "MECHANICAL_QA_PASS_AWAITING_USER_REVIEW"
    batch["summary_path"] = T1_ARRAY_RESULTS.relative_to(SERIES).as_posix()
    batch["summary_sha256"] = sha256(T1_ARRAY_RESULTS)
    batch["table_path"] = T1_ARRAY_TABLE.relative_to(SERIES).as_posix()
    batch["jj_phase_area_path"] = (T1_ARRAY_ANALYSIS / "T1_ARRAY_JJ_PHASE_AREA.csv").relative_to(SERIES).as_posix()
    _json(T1_ARRAY_BATCH_MANIFEST, batch)
    print(json.dumps({"status": batch["status"], "batch_id": T1_ARRAY_BATCH_ID,
                      "run_ids": expected_ids, "physical_solve_count": 4,
                      "summary": summary["schema"],
                      "raw_sha256_by_run": {item["run_id"]: item["raw_sha256"] for item in batch["runs"]},
                      "scientific_interpretation_performed": False,
                      "automatic_follow_up": False}, ensure_ascii=False, indent=2), flush=True)
    return 0


def _plotter_module() -> Any:
    spec = importlib.util.spec_from_file_location("josim_plot2_bvm4x4", PLOTTER)
    if spec is None or spec.loader is None:
        raise ConfigError(f"cannot import classic plotter {PLOTTER}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def plot_signals(probes: dict[str, Any]) -> list[dict[str, Any]]:
    labels = {item["label"]: item for item in probes["signals"]}
    profile = probes["profile"]
    if profile == "t1_chain_focus":
        overview = [f"V(DOUT_{name})" for name in DIAGONALS]
        overview.extend(f"V(S_{name})" for name in DIAGONALS)
        overview.extend(f"V(C_{name})" for name in DIAGONALS)
        overview.extend(("V(DFF_O)", *(f"V(CLK_{name})" for name in DIAGONALS), "V(CLK_DFF)"))
        propagation = []
        for index in range(1, 7):
            if index == 1 and probes.get("cbu_override_d1") == "CB_CARRY_BUFFER":
                propagation.extend(("V(CBU_JOIN_D1)", "V(CARRY_CB_IN_D1)",
                                    "V(CARRY_CB_OUT_D1)", "V(T1_I_D1)", "V(C_D1)"))
            elif index == 1 and probes.get("cbu_override_d1") == "CB_DIRECT":
                propagation.append("V(CBU_JOIN_D1)")
                propagation.extend(("V(CBU_OUT_D1)", "V(T1_I_D1)", "V(C_D1)"))
            else:
                propagation.extend((f"V(CBU_A_D{index})", f"V(CBU_B_D{index})",
                                    f"V(CBU_OUT_D{index})", f"V(T1_I_D{index})", f"V(C_D{index})"))
        propagation.extend((f"V(DOUT_D0)", "V(T1_I_D0)", "V(C_D0)"))
        propagation.extend(f"V(CLK_{name})" for name in DIAGONALS)
        propagation.append("V(CLK_DFF)")
        stage = probes.get("focus_stage", "D3")
        index = int(stage[1])
        focus = [f"V(DOUT_{stage})"]
        if index:
            if index == 1 and probes.get("cbu_override_d1") == "CB_CARRY_BUFFER":
                focus.extend(("P(BJ1|XCB_D1_L2)", "V(BJ1|XCB_D1_L2)",
                              "P(BJ2|XCB_D1_L2)", "V(BJ2|XCB_D1_L2)", "V(C_D0)",
                              "V(CARRY_CB_IN_D1)", "I(V_CARRY_IN_D1)",
                              "P(BJ1|XCB_CARRY_D1)", "V(BJ1|XCB_CARRY_D1)",
                              "P(BJ2|XCB_CARRY_D1)", "V(BJ2|XCB_CARRY_D1)",
                              "I(IB1|XCB_CARRY_D1)", "V(CARRY_CB_OUT_D1)",
                              "I(V_CBU_B_D1)", "V(CBU_JOIN_D1)", "I(V_CBU_A_D1)",
                              "I(V_T1_LINK_D1)"))
            elif index == 1 and probes.get("cbu_override_d1") == "CB_DIRECT":
                focus.extend(("P(BJ1|XCB_D1_L2)", "V(BJ1|XCB_D1_L2)", "V(C_D0)",
                              "V(CBU_JOIN_D1)", "I(V_CBU_A_D1)", "I(V_CBU_B_D1)",
                              "V(CBU_OUT_D1)", "I(V_T1_LINK_D1)"))
                for jj in ("BJ1", "BJ2"):
                    focus.extend((f"P({jj}|XCBU_D1)", f"V({jj}|XCBU_D1)"))
            else:
                focus.extend((f"V(C_D{index-1})", f"V(CBU_A_{stage})", f"V(CBU_B_{stage})",
                              f"V(CBU_OUT_{stage})"))
                cbu = f"XCBU_{stage}"
                for jj in ("B1", "B4", "B7"):
                    focus.extend((f"P({jj}|{cbu})", f"V({jj}|{cbu})"))
        else:
            for instance in range(1, int(probes.get("d0_jtl_count", 1)) + 1):
                jtl = f"XJTL_D0_{instance}"
                focus.extend((f"P(BJ1|{jtl})", f"V(BJ1|{jtl})"))
        t1 = f"XT1_{stage}"
        for jj in T1_CRITICAL_JJS:
            for signal in (f"P({jj}|{t1})", f"V({jj}|{t1})"):
                if signal in labels:
                    focus.append(signal)
        focus.extend((f"V(T1_I_{stage})", f"V(CLK_{stage})", f"V(S_{stage})", f"V(C_{stage})"))
        pages = [
            {"file": "01_full_chain_overview.html", "title": "Seven D inputs, Sum/Carry outputs, DFF.O and all global clocks", "signals": overview},
            {"file": "02_carry_propagation.html", "title": "D/Carry CBU inputs, CBU outputs, T1 inputs and clocks", "signals": propagation},
            {"file": "03_stage_focus.html", "title": f"{stage} CBU/JTL and T1 internal JJ focus", "signals": focus},
        ]
        for page in pages:
            missing = [signal for signal in page["signals"] if signal not in labels]
            if missing:
                raise ConfigError(f"chain plot page {page['file']} requests missing probes: {missing}")
        return pages
    if profile == "t1_array_focus":
        input_output = [f"V(T1_I_{name})" for name in DIAGONALS]
        input_output.extend(label for name in DIAGONALS for label in (f"V(S_{name})", f"V(C_{name})"))
        clocks = [f"V(CLK_{name})" for name in DIAGONALS]
        if any(f"V(CLK_RAW_{name})" in labels for name in DIAGONALS):
            clocks.extend(f"V(CLK_RAW_{name})" for name in DIAGONALS)
        clocks.extend(label for name in DIAGONALS for label in (f"V(S_{name})", f"V(C_{name})"))
        focus_diagonal = probes.get("focus_diagonal", "D3")
        focus_t1 = f"XT1_{focus_diagonal}"
        focus = [f"P({jj}|{focus_t1})" for jj in T1_CRITICAL_JJS]
        focus.extend(f"V({jj}|{focus_t1})" for jj in T1_CRITICAL_JJS)
        focus.extend((f"V(T1_I_{focus_diagonal})", f"V(CLK_{focus_diagonal})",
                      f"V(S_{focus_diagonal})", f"V(C_{focus_diagonal})"))
        result = [
            {"file": "01_t1_overview.html", "title": "Seven T1 inputs and fourteen S/C outputs",
             "signals": input_output},
            {"file": "02_t1_clock_compare.html", "title": "Seven independent clocks and S/C outputs",
             "signals": clocks},
            {"file": "03_t1_focus.html", "title": f"{focus_diagonal} T1 internal JJ focus",
             "signals": focus},
        ]
        for page in result:
            missing = [signal for signal in page["signals"] if signal not in labels]
            if missing:
                raise ConfigError(f"T1 plot page {page['file']} requests missing probes: {missing}")
        return result
    focus_diagonal = probes.get("focus_diagonal") or "D3"
    focus_cells = DIAGONALS[focus_diagonal]
    target = focus_cells[0]
    overview = [item["label"] for item in probes["signals"]
                if item.get("group", "").startswith("input:") and item.get("cell") == target]
    if profile == "compact":
        overview = [item["label"] for item in probes["signals"]
                    if item.get("group", "").startswith("input_source:")]
    overview.extend(f"V(DOUT_{name})" for name in DIAGONALS)
    if profile == "compact":
        detail = [item["label"] for item in probes["signals"]
                  if item.get("group", "").startswith(("bvm_output:", "merge:", "terminal_junction:"))]
        detail.extend(f"V(DOUT_{name})" for name in DIAGONALS)
        detail.extend(f"I(R_TERM_{name})" for name in DIAGONALS)
        detail = list(dict.fromkeys(detail))
        detail_title = "Compact BVM/diagonal boundaries and terminal JJ P/V"
    else:
        detail = [item["label"] for item in probes["signals"]
                  if item.get("group", "").startswith(f"focus:{focus_diagonal}:")]
        detail.extend(f"V(MERGE_{focus_diagonal}_L{level})"
                      for level in range(1, len(focus_cells) + 1))
        if profile == "debug":
            detail = [item["label"] for item in probes["signals"]
                      if item.get("group", "").startswith("debug:")]
        detail = list(dict.fromkeys(label for label in detail if label in labels))
        detail_title = f"{profile.title()} internal focus: {focus_diagonal} BVM/QB/sJTL/CB"
    plan = [
        {"file": "01_overview.html", "title": "Target-cell input branch currents and seven diagonal DOUTs", "signals": list(dict.fromkeys(overview))},
        {"file": "02_focus.html", "title": detail_title, "signals": detail},
    ]
    for page in plan:
        missing = [sig for sig in page["signals"] if sig not in labels]
        if missing:
            raise ConfigError(f"plot page {page['file']} requests missing probes: {missing}")
    return plan


def plot_layout_metrics(signals: list[str]) -> dict[str, Any]:
    counts = {kind: sum(label.startswith(f"{kind}(") for label in signals)
              for kind in ("V", "P", "I")}
    counts["U"] = sum(not label.startswith(("V(", "P(", "I(")) for label in signals)
    group_count = sum(value > 0 for value in counts.values())
    return {"group_counts": counts, "group_count": group_count,
            "height_px": None, "height_mode": "classic_plotly_default",
            "width_mode": "responsive_full_width"}


def render_plots(run_dir: Path, probes: dict[str, Any], *,
                 version_suffix: str = "", plot_root_override: Path | None = None,
                 write_run_manifests: bool = True) -> dict[str, Any]:
    import pandas as pd
    raw = run_dir / "raw.csv"
    before = sha256(raw)
    required = {item["label"] for item in probes["signals"]}
    times, columns, _ = read_raw(raw, required, exact_header=True)
    frame = pd.DataFrame({"time": times, **{key: list(value) for key, value in columns.items()}})
    plotter = _plotter_module()
    plot_root = plot_root_override or (PLOTS / "runs" / run_dir.name)
    asset_ref = Path(os.path.relpath(PLOTLY_ASSET, plot_root)).as_posix()
    if not PLOTLY_ASSET.is_file():
        raise ConfigError(f"shared Plotly JS asset is missing: {PLOTLY_ASSET}")
    page_records = []
    for page in plot_signals(probes):
        page_path = Path(page["file"])
        suffix = f"_{version_suffix}" if version_suffix else ""
        target = plot_root / f"{page_path.stem}{suffix}{page_path.suffix}"
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            raise FileExistsError(f"refusing to overwrite plot {target}")
        fig = plotter.seperate_combined_layout(frame, SimpleNamespace(subset=page["signals"], jump="2pi"))
        layout = plot_layout_metrics(page["signals"])
        fig.update_layout(title=f"{run_dir.name} — {page['title']}", title_font_size=22,
                          template="plotly_dark")
        fig.write_html(target, include_plotlyjs=asset_ref, full_html=True, auto_open=False)
        page_html = target.read_text(encoding="utf-8")
        graph_div = re.search(r'<div[^>]*class="plotly-graph-div"[^>]*>', page_html)
        if ("Plotly.newPlot" not in page_html or '"responsive": true' not in page_html or
                page_html.count(asset_ref) != 1 or "staticPlot" in page_html or
                graph_div is None or "height:100%" not in graph_div.group(0) or
                "width:100%" not in graph_div.group(0)):
            raise ConfigError(f"responsive interactive Plotly HTML QA failed: {target}")
        page_records.append({"path": target.relative_to(SERIES).as_posix(), "sha256": sha256(target),
                             "status": "PASS", "trace_count": len(page["signals"]),
                             "sample_count": len(times), "full_stored_time_range": True,
                             "signals": page["signals"], "shared_plotly_asset_count": 1,
                             **layout, "responsive": True, "zoom_hover_legend_interactive": True})
    after = sha256(raw)
    if before != after:
        raise ConfigError("raw changed during plot generation")
    qa = {"schema": "bvm-4x4-diagonal-plot-qa-v2", "status": "PASS",
          "raw_sha256_before": before, "raw_sha256_after": after,
          "raw_immutable": True, "plotter_path": PLOTTER.relative_to(REPO).as_posix(),
          "plotter_sha256": sha256(PLOTTER), "plotly_asset_path": PLOTLY_ASSET.relative_to(REPO).as_posix(),
          "plotly_asset_sha256": sha256(PLOTLY_ASSET), "layout": "josim-plot2 sep_comb dark -j 2pi",
          "version_suffix": version_suffix or None,
          "responsive": True, "html_uses_external_shared_plotly_js": True,
          "pages": page_records, "page_count": len(page_records),
          "scientific_interpretation_performed": False}
    suffix = f"_{version_suffix}" if version_suffix else ""
    if write_run_manifests:
        _json(run_dir / f"plot_manifest{suffix}.json", {"schema": "bvm-4x4-diagonal-plot-manifest-v2",
                                                        "raw_sha256": before, "pages": page_records,
                                                        "plotter_sha256": qa["plotter_sha256"],
                                                        "plotly_asset_sha256": qa["plotly_asset_sha256"],
                                                        "responsive": True})
        _json(run_dir / f"plot_qa{suffix}.json", qa)
    return qa


def repair_t1_classic_plots() -> int:
    """Regenerate A013-A016 HTML with the historical Plotly canvas defaults only."""
    run_ids = [item[0] for item in T1_ARRAY_RUN_MATRIX]
    repair_path = T1_ARRAY_ANALYSIS / "VISUALIZATION_REPAIR_CLASSIC.json"
    output_root = PLOTS / "t1-classic-v1"
    if repair_path.exists():
        raise ConfigError(f"refusing to overwrite visualization repair record: {repair_path}")
    runs = []
    for run_id in run_ids:
        run_dir = RUNS / run_id
        raw = run_dir / "raw.csv"
        result = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
        qa = json.loads((run_dir / "qa.json").read_text(encoding="utf-8"))
        t1_qa = json.loads((run_dir / "t1_array_qa.json").read_text(encoding="utf-8"))
        probe = json.loads((run_dir / "probe_manifest.json").read_text(encoding="utf-8"))
        original_plot_qa = json.loads((run_dir / "plot_qa.json").read_text(encoding="utf-8"))
        raw_before = sha256(raw)
        if (result.get("artifact_status") != "VALID" or qa.get("status") != "PASS" or
                t1_qa.get("status") != "PASS" or result.get("raw_sha256") != raw_before or
                t1_qa.get("raw_sha256_after_analysis") != raw_before or
                probe.get("profile") != "t1_array_focus"):
            raise ConfigError(f"cannot regenerate classic T1 plots from an invalid/non-T1 run: {run_id}")
        original_pages = original_plot_qa.get("pages", [])
        for page in original_pages:
            old_path = SERIES / page["path"]
            if not old_path.is_file() or sha256(old_path) != page.get("sha256"):
                raise ConfigError(f"original plot identity mismatch; refusing repair: {old_path}")
        regenerated = render_plots(run_dir, probe, plot_root_override=output_root / run_id,
                                   write_run_manifests=False)
        raw_after = sha256(raw)
        if raw_after != raw_before or regenerated["raw_sha256_after"] != raw_before:
            raise ConfigError(f"raw changed during T1 HTML-only repair: {run_id}")
        if regenerated["page_count"] != 3:
            raise ConfigError(f"T1 classic plot repair did not produce exactly three pages: {run_id}")
        for page in original_pages:
            old_path = SERIES / page["path"]
            if sha256(old_path) != page["sha256"]:
                raise ConfigError(f"original plot changed during repair: {old_path}")
        runs.append({"run_id": run_id, "raw_sha256": raw_before,
                     "physical_solve_count": 0,
                     "original_pages_unchanged": True,
                     "original_pages": original_pages,
                     "regenerated_plot_qa": regenerated})

    repair = {"schema": "bvm-4x4-t1-classic-visualization-repair-v1",
              "status": "PASS", "renderer": PLOTTER.relative_to(REPO).as_posix(),
              "layout": "historical josim-plot2 sep_comb/dark/-j 2pi; no forced height or width",
              "shared_plotly_asset": PLOTLY_ASSET.relative_to(REPO).as_posix(),
              "output_root": output_root.relative_to(SERIES).as_posix(),
              "physical_solve_count": 0, "raw_modified": False,
              "original_html_overwritten": False, "html_in_package": False,
              "runs": runs, "scientific_interpretation_performed": False}
    _json(repair_path, repair)
    print(json.dumps({"status": repair["status"], "physical_solve_count": 0,
                      "output_root": repair["output_root"],
                      "runs": [{"run_id": item["run_id"],
                                "pages": [page["path"] for page in item["regenerated_plot_qa"]["pages"]],
                                "raw_sha256": item["raw_sha256"]}
                               for item in runs]}, ensure_ascii=False, indent=2))
    return 0


def repair_bus400_run_html(run_id: str) -> dict[str, Any]:
    if run_id not in BUS400_RUN_IDS:
        raise ConfigError(f"HTML-only repair is scoped to {BUS400_RUN_IDS}; got {run_id}")
    run_dir = RUNS / run_id
    raw = run_dir / "raw.csv"
    result = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
    old_manifest_path = run_dir / "plot_manifest.json"
    repair_path = run_dir / "visualization_repair_responsive_v2.json"
    if not raw.is_file() or not old_manifest_path.is_file() or repair_path.exists():
        raise ConfigError(f"missing source evidence or refusing to overwrite prior visualization repair: {run_id}")
    raw_before = sha256(raw)
    if raw_before != result.get("raw_sha256"):
        raise ConfigError(f"immutable raw identity mismatch; refusing HTML repair: {run_id}")
    old_manifest = json.loads(old_manifest_path.read_text(encoding="utf-8"))
    probe = json.loads((run_dir / "probe_manifest.json").read_text(encoding="utf-8"))
    plot_qa = render_plots(run_dir, probe, version_suffix="responsive_v2")
    raw_after = sha256(raw)
    if raw_after != raw_before or plot_qa["raw_sha256_before"] != raw_before:
        raise ConfigError(f"raw changed during visualization repair: {run_id}")
    record = {"schema": "bvm-4x4-html-repair-v1", "run_id": run_id,
              "solver_invoked": False, "physical_solve_count": 0,
              "raw_sha256_before": raw_before, "raw_sha256_after": raw_after,
              "old_plot_manifest_sha256": sha256(old_manifest_path),
              "old_pages": old_manifest.get("pages", []),
              "new_manifest_path": (run_dir / "plot_manifest_responsive_v2.json").relative_to(SERIES).as_posix(),
              "new_qa_path": (run_dir / "plot_qa_responsive_v2.json").relative_to(SERIES).as_posix(),
              "new_plot_qa": plot_qa, "scientific_interpretation_performed": False}
    _json(repair_path, record)
    return record


def repair_bus400_html_batch() -> int:
    summary_path = SERIES / "analysis" / "BUS400_html_repair_summary.json"
    if summary_path.exists():
        raise FileExistsError(f"refusing to overwrite HTML repair summary: {summary_path}")
    for run_id in BUS400_RUN_IDS:
        run_dir = RUNS / run_id
        repair_path = run_dir / "visualization_repair_responsive_v2.json"
        page_paths = [PLOTS / "runs" / run_id / f"{Path(page['file']).stem}_responsive_v2.html"
                      for page in plot_signals(json.loads((run_dir / "probe_manifest.json").read_text(encoding="utf-8")))]
        if repair_path.exists() or any(path.exists() for path in page_paths):
            raise FileExistsError(f"refusing to overwrite existing responsive-v2 visualization for {run_id}")
    compare_path = PLOTS / "comparison" / "BUS400_D3_matched_responsive_v2.html"
    compare_qa_path = SERIES / "analysis" / "BUS400_comparison_qa_responsive_v2.json"
    if compare_path.exists() or compare_qa_path.exists():
        raise FileExistsError("refusing to overwrite existing responsive-v2 comparison artifacts")
    run_records = [repair_bus400_run_html(run_id) for run_id in BUS400_RUN_IDS]
    comparison = build_bus400_comparison(list(BUS400_RUN_IDS), version_suffix="responsive_v2")
    if comparison["status"] != "PASS" or not comparison["raws_immutable"]:
        raise ConfigError("versioned BUS400 comparison visualization QA failed")
    _json(summary_path, {"schema": "bvm-4x4-html-repair-summary-v1",
                         "batch_id": BUS400_BATCH_ID, "physical_solve_count": 0,
                         "runs": run_records, "comparison_qa": comparison,
                         "plotter": "scripts/josim-plot2.py", "layout": "sep_comb/dark/-j 2pi",
                         "responsive_width": True, "dynamic_height": True,
                         "shared_plotly_js_external": True,
                         "scientific_interpretation_performed": False})
    print(json.dumps({"status": "HTML_REPAIR_PASS", "physical_solve_count": 0,
                      "runs": [{"run_id": item["run_id"],
                                "pages": [page["path"] for page in item["new_plot_qa"]["pages"]],
                                "raw_sha256": item["raw_sha256_after"]}
                               for item in run_records],
                      "comparison": comparison["path"],
                      "summary": summary_path.relative_to(SERIES).as_posix(),
                      "shared_plotly_js": PLOTLY_ASSET.relative_to(REPO).as_posix()},
                     ensure_ascii=False, indent=2))
    return 0


def _write_experiment_manifest(run_record: dict[str, Any] | None = None) -> None:
    path = SERIES / "experiment_manifest.json"
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
    else:
        data = {"schema": "bvm-4x4-diagonal-experiment-manifest-v1",
                "experiment_id": "bvm-4x4-diagonal-array-v1-20261009",
                "registered_parent_head": "df0249419c7a91ceb72b1fb0ed1d04981a5f6c1b",
                "authorized_physical_solves": list(REGISTERED_CASES), "runs": [],
                "physical_solve_count": 0, "scientific_interpretation_performed": False}
    data.setdefault("authorization_batches", [])
    if run_record:
        if any(item.get("run_id") == run_record["run_id"] for item in data["runs"]):
            raise ConfigError(f"run ID already exists in experiment manifest: {run_record['run_id']}")
        data["runs"].append(run_record)
        data["physical_solve_count"] = sum(int(item.get("physical_solve_count", 0)) for item in data["runs"])
    _json(path, data)


def run_one(case: dict[str, str], stimulus: dict[str, str], t1_params: dict[str, str],
            solver_info: dict[str, Any], *, batch_id: str | None = None,
            run_id_override: str | None = None,
            rendered_override: dict[str, Any] | None = None,
            preflight_path: Path | None = None,
            metric_spec_path_override: Path | None = None,
            expected_deck_sha256: str | None = None) -> tuple[int, dict[str, Any]]:
    run_id = run_id_override or allocate_run_id(case["CASE"])
    run_dir = RUNS / run_id
    if run_dir.exists():
        raise ConfigError(f"run directory already exists; refusing overwrite: {run_dir}")
    rendered = rendered_override or render(case, stimulus, t1_params, run_dir)
    if rendered["static_qa"]["raw_estimate_bytes"] >= MAX_RAW_BYTES:
        raise ConfigError("pre-solve storage guard: estimated raw exceeds ordinary single-file limit; no solver invoked")
    rendered_deck_sha256 = hashlib.sha256(rendered["deck"].encode("utf-8")).hexdigest()
    if expected_deck_sha256 and rendered_deck_sha256 != expected_deck_sha256:
        raise ConfigError(f"frozen preflight deck SHA mismatch for {run_id}: {rendered_deck_sha256}")
    run_dir.mkdir(parents=True, exist_ok=False)
    case_snapshot = run_dir / "USER_CASE.snapshot.env"
    stimulus_snapshot = run_dir / "STIMULUS.snapshot.env"
    t1_snapshot = run_dir / "T1_PARAMS.snapshot.env"
    _write_env(case_snapshot, case)
    _write_env(stimulus_snapshot, stimulus)
    _write_env(t1_snapshot, _prefixed_params(t1_params, "T1_"))
    if case["OUTPUT_MODE"] == "DIAGONAL_T1_CHAIN":
        for filename, prefix in CHAIN_SOURCE_CONFIG_GROUPS.items():
            _write_env(run_dir / filename, _prefixed_params(t1_params, prefix))
    (run_dir / "deck.cir").write_text(rendered["deck"], encoding="utf-8")
    (run_dir / "stimulus.inc").write_text(rendered["stimulus_text"], encoding="utf-8")
    if rendered.get("t1_source_text") is not None:
        source_snapshot = run_dir / "sources" / "t1_cell_tunable.cir"
        source_snapshot.parent.mkdir(parents=True, exist_ok=True)
        source_snapshot.write_text(rendered["t1_source_text"], encoding="utf-8")
        if sha256(source_snapshot) != rendered["t1_source_info"]["rendered_sha256"]:
            raise ConfigError("run-local tunable T1 source hash does not match its render manifest")
    for relative, source_text in rendered.get("chain_source_texts", {}).items():
        source_snapshot = run_dir / relative
        source_snapshot.parent.mkdir(parents=True, exist_ok=True)
        source_snapshot.write_text(source_text, encoding="utf-8")
        expected = next(item for item in rendered["chain_source_info"].values() if item["path"] == relative)
        if sha256(source_snapshot) != expected["rendered_sha256"]:
            raise ConfigError(f"run-local chain source hash mismatch: {relative}")
    _json(run_dir / "topology_manifest.json", rendered["topology"])
    _json(run_dir / "probe_manifest.json", rendered["probes"])
    _json(run_dir / "static_qa.json", rendered["static_qa"])
    _json(run_dir / "stimulus_manifest.json", {
        "schema": "bvm-4x4-diagonal-stimulus-v2",
        "source_sha256": hashlib.sha256(rendered["stimulus_text"].encode()).hexdigest(),
        "source_count": len(rendered["drivers"]),
        "source_lines": rendered["stimulus_text"].splitlines(),
        "amplitudes": {key: case[key] for key in (
            "ROW_WL_WRITE_AMPLITUDE", "COL_BL_WRITE_AMPLITUDE",
            "ROW_WL_READ_AMPLITUDE", "COL_SE_READ_AMPLITUDE")},
        "amplitude_semantics": "shared WL/BL amplitudes are BUS_SOURCE_TOTAL setpoints; per-BVM branch currents are measured from raw and are not assumed to divide equally",
        "row_bits": case["ROW_BITS"], "column_bits": case["COL_BITS"],
        "se_enable_mask": case["SE_ENABLE_MASK"],
        "final_read_active_cells": _active_cells(case),
        "scientific_interpretation_performed": False})
    source_manifest = _source_manifest(rendered["sources"])
    _json(run_dir / "source_manifest.json", source_manifest)
    _json(run_dir / "case_manifest.json", {"schema": "bvm-4x4-diagonal-case-v2",
                                             "run_id": run_id, "case": case,
                                             "stimulus": stimulus, "t1_params": _prefixed_params(t1_params, "T1_"),
                                             "device_params": {prefix: _prefixed_params(t1_params, prefix)
                                                                for prefix in ("CBU_", "DFF_", "D0_JTL_")},
                                             "effective_topology": {
                                                 "sjtl_count_by_diagonal": {
                                                     name: list(_sjtl_counts(case, name)) for name in DIAGONALS},
                                                 "sjtl_total": sum(sum(_sjtl_counts(case, name)) for name in DIAGONALS),
                                                 "cb_total": 16,
                                                 "terminal_total": 0 if case["OUTPUT_MODE"] in {"DIAGONAL_T1_INDEPENDENT", "DIAGONAL_T1_CHAIN"} else 7,
                                                 "t1_total": 7 if case["OUTPUT_MODE"] in {"DIAGONAL_T1_INDEPENDENT", "DIAGONAL_T1_CHAIN"} else 0,
                                                 "cbu_total": 6 if case["OUTPUT_MODE"] == "DIAGONAL_T1_CHAIN" else 0,
                                                 "d0_jtl_total": int(case["D0_JTL_COUNT"]) if case["OUTPUT_MODE"] == "DIAGONAL_T1_CHAIN" else 0,
                                                 "dff_total": 1 if case["OUTPUT_MODE"] == "DIAGONAL_T1_CHAIN" else 0,
                                                 "merge_semantics": "serial; unchanged"},
                                             "active_final_crosspoints": _active_cells(case),
                                             "diagonal_expected_active_cells": {
                                                 name: [cell for cell in cells if cell in _active_cells(case)]
                                                 for name, cells in DIAGONALS.items()},
                                             "physical_solve_count": 1,
                                             "automatic_follow_up": False,
                                             "scientific_interpretation_performed": False})
    deck_hash = sha256(run_dir / "deck.cir")
    stimulus_hash = sha256(run_dir / "stimulus.inc")
    source_hashes = {role: item["sha256"] for role, item in rendered["sources"].items()}
    start_utc = datetime.now(timezone.utc).isoformat()
    command = [str(SOLVER), "-a", "1", "-o", str(run_dir / "raw.csv"), str(run_dir / "deck.cir")]
    completed = subprocess.run(command, cwd=run_dir, capture_output=True, text=True, check=False)
    (run_dir / "stdout.txt").write_text(completed.stdout, encoding="utf-8")
    (run_dir / "stderr.txt").write_text(completed.stderr, encoding="utf-8")
    finish_utc = datetime.now(timezone.utc).isoformat()
    raw = run_dir / "raw.csv"
    raw_hash = sha256(raw) if raw.is_file() else None
    run_log = (f"run_id={run_id}\nstarted_at_utc={start_utc}\nfinished_at_utc={finish_utc}\n"
               f"command={' '.join(command)}\nsolver_version={solver_info['version']}\n"
               f"solver_sha256={solver_info['sha256']}\nsolver_exit_code={completed.returncode}\n"
               f"deck_sha256={deck_hash}\nstimulus_sha256={stimulus_hash}\nraw_sha256={raw_hash or 'MISSING'}\n")
    (run_dir / "run.log").write_text(run_log, encoding="utf-8")
    if completed.returncode != 0 or not raw.is_file() or raw.stat().st_size == 0:
        result = {"schema": "bvm-4x4-diagonal-result-v1", "run_id": run_id,
                  "status": "SOLVER_FAILURE", "artifact_status": "INVALID",
                  "batch_id": batch_id,
                  "solver_exit_code": completed.returncode, "physical_solve_count": 1,
                  "raw_sha256": raw_hash, "scientific_interpretation_performed": False,
                  "automatic_follow_up": False}
        _json(run_dir / "result.json", result)
        _write_experiment_manifest({"run_id": run_id, "case": case["CASE"],
                                    "batch_id": batch_id,
                                    "status": result["status"], "physical_solve_count": 1,
                                    "raw_sha256": raw_hash})
        return 2, result
    if raw.stat().st_size >= MAX_RAW_BYTES:
        result = {"schema": "bvm-4x4-diagonal-result-v1", "run_id": run_id,
                  "case": case["CASE"], "status": "RAW_EXCEEDS_SINGLE_FILE_LIMIT",
                  "batch_id": batch_id,
                  "artifact_status": "INVALID", "solver_exit_code": completed.returncode,
                  "physical_solve_count": 1, "raw_sha256": raw_hash,
                  "raw_bytes": raw.stat().st_size, "automatic_follow_up": False,
                  "scientific_interpretation_performed": False}
        _json(run_dir / "result.json", result)
        _write_experiment_manifest({"run_id": run_id, "case": case["CASE"],
                                    "batch_id": batch_id,
                                    "status": result["status"], "physical_solve_count": 1,
                                    "raw_sha256": raw_hash, "raw_bytes": raw.stat().st_size})
        print(f"STOP: raw size {raw.stat().st_size} exceeds {MAX_RAW_BYTES}; preserved, no retry/follow-up.",
              file=sys.stderr)
        return 2, result

    try:
        chain_active = case["OUTPUT_MODE"] == "DIAGONAL_T1_CHAIN"
        chain_qa = None
        if chain_active:
            metrics, raw_qa = analyze_t1_chain_raw(run_dir, rendered["probes"], case)
            chain_qa = raw_qa
            _json(run_dir / "chain_qa.json", raw_qa)
        else:
            metrics, raw_qa = analyze_raw(run_dir, rendered["probes"])
        t1_array_qa = None
        if case["OUTPUT_MODE"] == "DIAGONAL_T1_INDEPENDENT":
            t1_array_metrics, t1_array_qa = analyze_t1_array_raw(run_dir, rendered["probes"])
            metrics["t1_array"] = t1_array_metrics
            _json(run_dir / "t1_array_qa.json", t1_array_qa)
        _json(run_dir / "metrics.json", metrics)
        _json(run_dir / "raw_qa.json", raw_qa)
        plot_qa = render_plots(run_dir, rendered["probes"])
        raw_hash_after = sha256(raw)
        if raw_hash_after != raw_hash:
            raise ConfigError("raw changed after post-processing")
        metric_spec_path = (metric_spec_path_override if metric_spec_path_override else
                            T1_CHAIN_METRIC_SPEC if chain_active else
                            SERIES / "analysis" / "BUS400_metric_spec.json"
                            if batch_id == BUS400_BATCH_ID else SERIES / "analysis" / "metric_spec.json")
        preflight_path = preflight_path or (T1_CHAIN_PREFLIGHT if chain_active else SERIES / "PREFLIGHT.md")
        provenance = {"schema": "bvm-4x4-diagonal-provenance-v2", "run_id": run_id,
                      "parent_head": solver_info["parent_head"], "solver": solver_info,
                      "deck_sha256": deck_hash, "stimulus_sha256": stimulus_hash,
                      "raw_sha256": raw_hash, "source_sha256": source_hashes,
                      "user_case_sha256": sha256(case_snapshot),
                      "stimulus_config_sha256": sha256(stimulus_snapshot),
                      "stimulus_manifest_sha256": sha256(run_dir / "stimulus_manifest.json"),
                      "t1_params_sha256": sha256(t1_snapshot),
                      "t1_params_affect_deck": case["OUTPUT_MODE"] in {"DIAGONAL_T1_INDEPENDENT", "DIAGONAL_T1_CHAIN"},
                      "t1_rendered_source": rendered.get("t1_source_info"),
                      "chain_rendered_sources": rendered.get("chain_source_info"),
                      "chain_config_sha256": {name: sha256(run_dir / name)
                                               for name in CHAIN_SOURCE_CONFIG_GROUPS
                                               if (run_dir / name).is_file()},
                      "probe_manifest_sha256": sha256(run_dir / "probe_manifest.json"),
                      "topology_manifest_sha256": sha256(run_dir / "topology_manifest.json"),
                      "preflight_path": preflight_path.relative_to(REPO).as_posix(),
                      "preflight_sha256": sha256(preflight_path),
                      "metric_spec_path": metric_spec_path.relative_to(REPO).as_posix(),
                      "metric_spec_sha256": sha256(metric_spec_path),
                      "runner_sha256": sha256(Path(__file__).resolve()),
                      "experiment_contract_sha256": sha256(REPO / "docs/EXPERIMENT_CONTRACT.md"),
                      "experiment_workflow_sha256": sha256(REPO / "docs/research/EXPERIMENT_WORKFLOW_V1.md"),
                      "risk_level": "NORMAL",
                      "metrics_sha256": sha256(run_dir / "metrics.json"),
                      "t1_array_qa_sha256": sha256(run_dir / "t1_array_qa.json") if t1_array_qa else None,
                      "chain_qa_sha256": sha256(run_dir / "chain_qa.json") if chain_active else None,
                      "plots": plot_qa["pages"],
                      "t1_mode": case["T1_MODE"], "t1_params_affect_deck": case["OUTPUT_MODE"] in {"DIAGONAL_T1_INDEPENDENT", "DIAGONAL_T1_CHAIN"},
                      "scientific_interpretation_performed": False}
        _json(run_dir / "provenance.json", provenance)
        qa = {"schema": "bvm-4x4-diagonal-run-qa-v1", "status": "PASS",
              "artifact_status": "VALID", "physical_solve_count": 1,
              "solver_exit_code": completed.returncode, "static_qa_status": "PASS",
              "raw_qa_status": raw_qa["status"], "plot_qa_status": plot_qa["status"],
              "provenance_qa_status": "PASS", "raw_sha256_before_analysis": raw_hash,
              "raw_sha256_after_analysis": raw_hash_after,
              "raw_bytes": raw.stat().st_size, "sample_count": raw_qa["sample_count"],
              "time_range_s": [raw_qa["time_start_s"], raw_qa["time_end_s"]],
              "dt_min_s": raw_qa["dt_min_s"], "dt_max_s": raw_qa["dt_max_s"],
              "probe_count": rendered["probes"]["signal_count"],
              "all_required_probes_present": True,
              "t1_array_qa_status": t1_array_qa["status"] if t1_array_qa else "NOT_APPLICABLE",
              "t1_chain_qa_status": chain_qa["status"] if chain_qa else "NOT_APPLICABLE",
              "scientific_interpretation_performed": False}
        _json(run_dir / "qa.json", qa)
        result = {"schema": "bvm-4x4-diagonal-result-v1", "run_id": run_id,
                  "case": case["CASE"], "output_mode": case["OUTPUT_MODE"],
                  "t1_mode": case["T1_MODE"], "t1_clk_mode": t1_params["T1_CLK_MODE"],
                  "t1_chain_clock_mode": case.get("T1_CHAIN_CLOCK_MODE"),
                  "t1_chain_clock_start": case.get("T1_CHAIN_CLK_START"),
                  "cbu_override_d1": case.get("CBU_OVERRIDE_D1", "NONE"),
                  "row_bits": case["ROW_BITS"],
                  "column_bits": case["COL_BITS"], "se_enable_mask": case["SE_ENABLE_MASK"],
                  "batch_id": batch_id,
                  "sjtl_count_by_diagonal": {name: list(_sjtl_counts(case, name)) for name in DIAGONALS},
                  "active_final_crosspoints": _active_cells(case),
                  "status": "MECHANICAL_QA_PASS_AWAITING_USER_REVIEW",
                  "artifact_status": "VALID", "physical_solve_count": 1,
                  "solver_exit_code": completed.returncode, "raw_sha256": raw_hash,
                  "deck_sha256": deck_hash, "stimulus_sha256": stimulus_hash,
                  "raw_bytes": raw.stat().st_size, "sample_count": raw_qa["sample_count"],
                  "probe_count": rendered["probes"]["signal_count"],
                  "qa_status": qa["status"], "plot_status": plot_qa["status"],
                  "scientific_interpretation_performed": False,
                  "automatic_follow_up": False}
        _json(run_dir / "result.json", result)
        _write_result_brief(run_dir, result, metrics)
        _json(run_dir / "metadata.json", {
            "schema": "bvm-4x4-diagonal-run-metadata-v1", "run_id": run_id,
            "effective_case": case, "effective_stimulus": stimulus,
            "batch_id": batch_id or (BUS400_BATCH_ID if case["CASE"] in BUS400_CASES else "BVM4X4_INITIAL_20261009"),
            "t1_mode": case["T1_MODE"],
            "t1_parameters_are_reference_only": case["OUTPUT_MODE"] not in {"DIAGONAL_T1_INDEPENDENT", "DIAGONAL_T1_CHAIN"},
            "solver": solver_info, "physical_solve_count": 1,
            "deck_sha256": deck_hash, "stimulus_sha256": stimulus_hash,
            "raw_sha256": raw_hash, "source_sha256": source_hashes,
            "probe_count": rendered["probes"]["signal_count"],
            "risk_level": "NORMAL" if batch_id in {BUS400_BATCH_ID, T1_ARRAY_BATCH_ID, T1_CHAIN_BATCH_ID,
                                                       CB_DIRECT_D1_BATCH_ID}
            else ("NORMAL" if case["CASE"] in BUS400_CASES else "historical registration unchanged"),
            "artifact_status": "VALID", "qa_status": "PASS",
            "scientific_interpretation_performed": False,
            "automatic_follow_up": False})
        _write_experiment_manifest({"run_id": run_id, "case": case["CASE"],
                                    "batch_id": batch_id,
                                    "row_bits": case["ROW_BITS"], "column_bits": case["COL_BITS"],
                                    "output_mode": case["OUTPUT_MODE"], "t1_mode": case["T1_MODE"],
                                    "t1_clk_mode": t1_params["T1_CLK_MODE"],
                                    "t1_chain_clock_mode": case.get("T1_CHAIN_CLOCK_MODE"),
                                    "t1_chain_clock_start": case.get("T1_CHAIN_CLK_START"),
                                    "cbu_override_d1": case.get("CBU_OVERRIDE_D1", "NONE"),
                                    "active_final_crosspoints": _active_cells(case),
                                    "status": result["status"], "physical_solve_count": 1,
                                    "raw_sha256": raw_hash, "raw_bytes": raw.stat().st_size,
                                    "probe_count": rendered["probes"]["signal_count"],
                                    "deck_sha256": deck_hash})
        return 0, result
    except Exception as exc:
        result = {"schema": "bvm-4x4-diagonal-result-v1", "run_id": run_id,
                  "case": case["CASE"], "status": "POSTPROCESS_FAILURE_RAW_PRESERVED",
                  "batch_id": batch_id,
                  "artifact_status": "INVALID", "physical_solve_count": 1,
                  "solver_exit_code": completed.returncode, "raw_sha256": sha256(raw),
                  "error": f"{type(exc).__name__}: {exc}",
                  "scientific_interpretation_performed": False,
                  "automatic_follow_up": False}
        _json(run_dir / "result.json", result)
        _write_experiment_manifest({"run_id": run_id, "case": case["CASE"],
                                    "batch_id": batch_id,
                                    "status": result["status"], "physical_solve_count": 1,
                                    "raw_sha256": result["raw_sha256"]})
        print(f"POSTPROCESS_FAILURE_RAW_PRESERVED: {result['error']}", file=sys.stderr)
        return 2, result


def _write_result_brief(run_dir: Path, result: dict[str, Any], metrics: dict[str, Any]) -> None:
    if result.get("output_mode") == "DIAGONAL_T1_CHAIN":
        by_signal = {(item["signal"], item["window"]): item for item in metrics["waveforms"]}
        def area(signal: str) -> str:
            record = by_signal.get((signal, "TOTAL"))
            return f"{record['signed_area_phi0_arithmetic']:.6g}" if record else "UNKNOWN"
        lines = [f"# {result['run_id']}", "",
                 f"- CASE: `{result['case']}`; ROW/COL=`{result['row_bits']}/{result['column_bits']}`; clock=`{result['t1_chain_clock_mode']}`.",
                 "- Topology: 7 physical T1 + 6 physical CBU + D0 sJTL + DFF; no DOUT/carry termination loads.",
                 "- Artifact/QA: mechanical only; raw/provenance hashes in the run artifacts.",
                 "- Units: signed V·s/Φ0 arithmetic uses actual stored timestamps; P(...) remains radians; turns are navigation only.",
                 "- Descriptive lobe candidates are not event/SFQ counts; actual product-bit decoding is NOT_PERFORMED.",
                 "- Scientific interpretation: `NOT_PERFORMED`; authorized follow-up: none.", "",
                 "| Stage | D input | Previous C | CBU/JTL→T1 input | Sum | Carry |",
                 "|---|---:|---:|---:|---:|---:|"]
        for index, diagonal in enumerate(DIAGONALS):
            d_input = area(f"V(DOUT_{diagonal})")
            carry_in = area(f"V(C_D{index-1})") if index else "—"
            if index == 1 and result.get("cbu_override_d1") == "CB_CARRY_BUFFER":
                stage_output = area("V(CBU_JOIN_D1)")
            else:
                stage_output = area(f"V(CBU_OUT_{diagonal})") if index else area("V(T1_I_D0)")
            lines.append(f"| {diagonal} | {d_input} | {carry_in} | {stage_output} | "
                         f"{area(f'V(S_{diagonal})')} | {area(f'V(C_{diagonal})')} |")
        lines.extend(("", f"- DFF.O signed voltage area: `{area('V(DFF_O)')} Φ0` arithmetic.",
                      "- Stage timings and same-JJ phase/voltage cross-checks: `metrics.json`.",
                      "- Plots: full-chain overview, carry propagation, selected stage focus; raw-backed and descriptive only."))
        (run_dir / "RESULT_BRIEF.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        return
    outputs = [item for item in metrics["outputs"] if item["window"] == "FINAL_READ_RESPONSE"]
    lines = [f"# {result['run_id']}", "",
             f"- CASE: `{result['case']}`; ROW/COL=`{result['row_bits']}/{result['column_bits']}`; "
             f"SE mask=`{result['se_enable_mask']}`.",
             f"- Active final-read crosspoints: `{', '.join(result['active_final_crosspoints']) or 'none'}`.",
             "- Output arithmetic: signed voltage area, extrema, and stored-sample peak times in metrics.json.",
             "- Artifact/QA: `VALID / PASS`; one physical solve; raw SHA and provenance in run files.",
             "- Scientific interpretation: `NOT_PERFORMED`; area/phase arithmetic is not an event count.", "",
             "| Diagonal | Signed area (V·s) | Positive max (V) | Positive max time (ps) |", "|---|---:|---:|---:|"]
    for item in outputs:
        lines.append(f"| {item['diagonal']} | {item['signed_area_v_s']:.9g} | {item['max_v']:.9g} | "
                     f"{item['time_of_positive_max_s']*1e12:.4f} |")
    (run_dir / "RESULT_BRIEF.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_batch_comparison() -> dict[str, Any]:
    import pandas as pd
    plotter = _plotter_module()
    plot_root = PLOTS / "comparison"
    target = plot_root / "01_D3_progression.html"
    if target.exists():
        raise FileExistsError(f"refusing to overwrite batch comparison {target}")
    run_ids = [item["run_id"] for item in json.loads(EXPERIMENT_MANIFEST.read_text())["runs"]
               if item.get("case", "").startswith("D3_N")]
    if run_ids != [f"A{index:03d}_D3_N{index-1}" for index in range(1, 6)]:
        raise ConfigError(f"expected exact D3 progression A001-A005 before comparison; found {run_ids}")
    records = []
    figures = []
    for run_id in run_ids:
        raw = RUNS / run_id / "raw.csv"
        raw_before = sha256(raw)
        times, columns, _ = read_raw(raw, {"V(DOUT_D3)"})
        raw_after = sha256(raw)
        if raw_before != raw_after:
            raise ConfigError(f"raw changed during comparison: {run_id}")
        frame = pd.DataFrame({"time": times, "V(DOUT_D3)": list(columns["V(DOUT_D3)"])})
        fig = plotter.seperate_combined_layout(frame, SimpleNamespace(subset=["V(DOUT_D3)"], jump="2pi"))
        fig.update_layout(title=f"{run_id} — V(DOUT_D3), full stored time range",
                          title_font_size=18, template="plotly_dark")
        figures.append(f"<section><h2>{html.escape(run_id)}</h2>" +
                       fig.to_html(full_html=False, include_plotlyjs=False) + "</section>")
        records.append({"run_id": run_id, "raw_path": (RUNS / run_id / "raw.csv").relative_to(SERIES).as_posix(),
                        "raw_sha256_before": raw_before, "raw_sha256_after": raw_after,
                        "sample_count": len(times), "signal": "V(DOUT_D3)",
                        "alignment": "independent native stored timestamps", "interpolation_or_resampling": False})
    plot_root.mkdir(parents=True, exist_ok=True)
    asset_ref = Path(os.path.relpath(PLOTLY_ASSET, plot_root)).as_posix()
    content = ("<!doctype html><html><head><meta charset=\"utf-8\">"
               f"<script src=\"{html.escape(asset_ref)}\"></script></head><body>"
               "<h1>D3_N0..D3_N4 progression — DOUT_D3</h1>"
               "<p>Classic josim-plot2 sep_comb/dark/-j 2pi; each panel uses the case's full stored grid. "
               "No interpolation/resampling; phase remains radians and is not an event count.</p>"
               + "\n".join(figures) + "</body></html>\n")
    target.write_text(content, encoding="utf-8")
    qa = {"schema": "bvm-4x4-diagonal-comparison-qa-v1", "status": "PASS",
          "path": target.relative_to(SERIES).as_posix(), "sha256": sha256(target),
          "run_count": len(records), "raws_immutable": all(x["raw_sha256_before"] == x["raw_sha256_after"] for x in records),
          "interpolation_or_resampling": False, "plotter_sha256": sha256(PLOTTER),
          "plotly_asset_sha256": sha256(PLOTLY_ASSET)}
    _json(SERIES / "analysis" / "comparison_manifest.json", {"schema": "bvm-4x4-diagonal-comparison-v1",
                                                               "runs": records, "page": qa,
                                                               "scientific_interpretation_performed": False})
    _json(SERIES / "analysis" / "comparison_qa.json", qa)
    return qa


def _print_matrix_preview() -> int:
    source_info = _solver_info()
    print(f"Preflight source parent: {source_info['parent_head']}")
    print(f"Solver: {source_info['path']} {source_info['version'].splitlines()[-1]} sha256={source_info['sha256']}")
    for name in REGISTERED_CASES:
        case, stimulus, t1 = load_config(name)
        rendered = render(case, stimulus, t1, RUNS / "_PREVIEW_ONLY")
        pages = plot_signals(rendered["probes"])
        print(f"{name}: active={','.join(rendered['static_qa']['active_final_crosspoints']) or 'none'}; "
              f"D counts={','.join(str(len([c for c in cells if c in rendered['static_qa']['active_final_crosspoints']])) for cells in DIAGONALS.values())}; "
              f"probes={rendered['probes']['signal_count']}; plots={len(pages)}; "
              f"raw_estimate={rendered['static_qa']['raw_estimate_bytes']} bytes; static=PASS")
    print("registered physical solves=6; this matrix preview solve count=0; no run directory created")
    return 0


def preview_bus400_batch() -> int:
    cases = validate_bus400_matrix()
    print(f"STATIC PREFLIGHT PASS: {BUS400_BATCH_ID}; parent={BUS400_PARENT_HEAD}")
    print("Shared source totals: WL write=400u, BL write=400u, WL read=400u; independent cell SE=100u.")
    for item in cases:
        case = item["case"]
        qa = item["rendered"]["static_qa"]
        print(f"{item['next_run_id']} {case['CASE']}: mask={case['SE_ENABLE_MASK']}; "
              f"active_final={','.join(qa['active_final_crosspoints']) or 'none'}; "
              f"probes={qa['probe_count']}; estimate={qa['raw_estimate_bytes']} bytes; "
              f"sJTL={qa['sjtl_count']}; CB=16; terminals=7; static={qa['status']}")
    print("PWL comparison: only I_SE_R1C1 at FINAL_READ differs; all other source lines and deck bodies match.")
    print("physical_solve_count=0; no run directory created")
    return 0


def run_registered_batch() -> int:
    if RUNS.exists() and any(p.is_dir() for p in RUNS.iterdir()):
        raise ConfigError("registered batch is one-shot and requires an empty runs/ directory")
    matrix = validate_registered_matrix()
    if len(matrix) != 6 or [item["case"] for item in matrix] != list(REGISTERED_CASES):
        raise ConfigError("registered matrix differs from the authorized six cases")
    source_records = verify_sources()
    _json(SERIES / "analysis" / "source_manifest.json", _source_manifest(source_records))
    default_case, _default_stimulus, _default_t1 = load_config()
    _json(SERIES / "analysis" / "topology_manifest.json", topology_manifest(source_records, default_case))
    solver_info = _solver_info()
    for name in REGISTERED_CASES:
        case, stimulus, t1_params = load_config(name)
        print(f"START {name}: next run {allocate_run_id(name)}", flush=True)
        code, result = run_one(case, stimulus, t1_params, solver_info)
        print(json.dumps(result, ensure_ascii=False), flush=True)
        if code != 0:
            print("STOP: registered batch halted at first solver/raw/mechanical failure; no retry/follow-up", file=sys.stderr)
            return code
    build_batch_comparison()
    return 0


def _t1_array_case_matrix() -> list[dict[str, Any]]:
    base_case, stimulus, base_t1 = load_config()
    fixed_case = {
        "ROW_WL_WRITE_AMPLITUDE": "400u", "COL_BL_WRITE_AMPLITUDE": "400u",
        "ROW_WL_READ_AMPLITUDE": "400u", "COL_SE_READ_AMPLITUDE": "100u",
        "SE_ENABLE_MASK": "ALL", "DT": "0.01p", "STOP": "250p",
        "SJTL_COUNT_D0": "1", "SJTL_COUNT_D1": "1,1",
        "SJTL_COUNT_D2": "1,1,1", "SJTL_COUNT_D3": "1,2,2,1",
        "SJTL_COUNT_D4": "1,1,1", "SJTL_COUNT_D5": "1,1", "SJTL_COUNT_D6": "1",
    }
    for key, expected in fixed_case.items():
        if base_case.get(key) != expected:
            raise ConfigError(f"T1-array batch requires fixed BVM baseline {key}={expected}, got {base_case.get(key)!r}")
    expected_stimulus = {
        "WRITE0_START": "50p", "WRITE0_RISE": "1p", "WRITE0_HOLD": "9p", "WRITE0_FALL": "1p",
        "READ0_START": "70p", "READ0_RISE": "1p", "READ0_HOLD": "9p", "READ0_FALL": "1p",
        "WRITE1_START": "90p", "WRITE1_RISE": "1p", "WRITE1_HOLD": "9p", "WRITE1_FALL": "1p",
        "FINAL_READ_START": "110p", "FINAL_READ_RISE": "1p", "FINAL_READ_HOLD": "9p", "FINAL_READ_FALL": "1p",
    }
    for key, expected in expected_stimulus.items():
        if stimulus.get(key) != expected:
            raise ConfigError(f"T1-array batch must retain registered stimulus {key}={expected}")
    expected_t1 = {"T1_BIAS1": "1.8m", "T1_BIAS2": "1.8m", "T1_BIAS3": "1.8m",
                   "T1_BIAS3_SOURCE": "VOLTAGE", "T1_R_S": "12", "T1_R_C": "12",
                   "T1_CLK_START": "170p", "T1_CLK_PERIOD": "50p", "T1_CLK_AMPLITUDE": "1.2m",
                   "T1_CLK_RISE": "1p", "T1_CLK_WIDTH": "2p", "T1_CLK_FALL": "1p",
                   "T1_CLK_SERIES_R": "2", "T1_CLK_QUIET_R": "5"}
    for key, expected in expected_t1.items():
        if base_t1.get(key) != expected:
            raise ConfigError(f"T1-array batch requires {key}={expected}, got {base_t1.get(key)!r}")
    baseline_t1_text, baseline_t1_info = render_t1_source(base_t1)
    if not baseline_t1_info["default_body_equivalent_to_canonical"]:
        raise ConfigError("default T1_PARAMS render is not netlist-body equivalent to canonical T1")
    scope = json.loads(T1_ARRAY_SCOPE.read_text(encoding="utf-8"))
    current_head = _git_output("rev-parse", "HEAD")
    if (scope.get("batch_id") != T1_ARRAY_BATCH_ID or scope.get("parent_head") != current_head or
            scope.get("physical_solve_count_authorized") != 4 or
            scope.get("authorized_run_ids") != [item[0] for item in T1_ARRAY_RUN_MATRIX]):
        raise ConfigError("T1_ARRAY WORK_UNIT.json does not authorize this exact four-run matrix at current HEAD")
    if not T1_ARRAY_PREFLIGHT.is_file() or "This experiment is governed by docs/EXPERIMENT_CONTRACT.md." not in T1_ARRAY_PREFLIGHT.read_text(encoding="utf-8"):
        raise ConfigError("T1-array PREFLIGHT is missing its mandatory experiment-contract statement")
    if not T1_ARRAY_METRIC_SPEC.is_file():
        raise ConfigError("T1-array metric specification is missing")
    spec = json.loads(T1_ARRAY_METRIC_SPEC.read_text(encoding="utf-8"))
    if spec.get("windows_ps") != {key: list(value) for key, value in T1_WINDOWS_PS.items()}:
        raise ConfigError("T1-array metric windows differ from the frozen T1_ARRAY_METRIC_SPEC")

    cases = []
    for run_id, label, row_bits, col_bits, clock_mode, expected_counts in T1_ARRAY_RUN_MATRIX:
        if (RUNS / run_id).exists():
            raise ConfigError(f"authorized run ID already exists; refusing overwrite: {run_id}")
        case = dict(base_case)
        case.update({"CASE": label, "ROW_BITS": row_bits, "COL_BITS": col_bits,
                     "SE_ENABLE_MASK": "ALL", "OUTPUT_MODE": "DIAGONAL_T1_INDEPENDENT",
                     "T1_MODE": "ALL_INDEPENDENT", "CBU_MODE": "OFF", "CARRY_MODE": "NONE",
                     "T1_CLK_MODE": clock_mode,
                     "PROBE_PROFILE": "t1_array_focus", "FOCUS_DIAGONAL": "D3",
                     **fixed_case})
        t1 = dict(base_t1)
        t1["T1_CLK_MODE"] = clock_mode
        validate_config(case, stimulus, t1)
        active = _active_cells(case)
        counts = [sum(cell in active for cell in DIAGONALS[name]) for name in DIAGONALS]
        if counts != expected_counts:
            raise ConfigError(f"{label} active-cell population mismatch: expected={expected_counts}, got={counts}")
        rendered = render(case, stimulus, t1, RUNS / run_id)
        if (rendered["static_qa"].get("status") != "PASS" or
                rendered["static_qa"].get("t1_count") != 7 or
                rendered["static_qa"].get("terminal_count") != 0 or
                rendered["static_qa"].get("raw_estimate_bytes", MAX_RAW_BYTES) >= MAX_RAW_BYTES):
            raise ConfigError(f"T1-array static/raw-size gate failed for {run_id}")
        if not rendered["t1_source_info"].get("default_body_equivalent_to_canonical"):
            raise ConfigError(f"default T1 source equivalence failed for {run_id}")
        cases.append({"run_id": run_id, "label": label, "case": case,
                      "stimulus": dict(stimulus), "t1_params": t1,
                      "expected_input_counts": expected_counts, "rendered": rendered})

    for quiet_index, pulse_index in ((0, 1), (2, 3)):
        quiet, pulse = cases[quiet_index], cases[pulse_index]
        if (quiet["stimulus"] != pulse["stimulus"] or
                {k: v for k, v in quiet["case"].items()
                 if k not in {"CASE", "T1_CLK_MODE"}} !=
                {k: v for k, v in pulse["case"].items()
                 if k not in {"CASE", "T1_CLK_MODE"}} or
                {k: v for k, v in quiet["t1_params"].items() if k != "T1_CLK_MODE"} !=
                {k: v for k, v in pulse["t1_params"].items() if k != "T1_CLK_MODE"}):
            raise ConfigError(f"matched QUIET/PULSE pair differs beyond T1_CLK_MODE: {quiet['label']}/{pulse['label']}")

    baseline_case, baseline_stimulus, baseline_params = load_config()
    if baseline_case["OUTPUT_MODE"] != "DIAGONAL_TERMINAL" or baseline_case["T1_MODE"] != "OFF":
        raise ConfigError("default baseline is no longer DIAGONAL_TERMINAL/T1_MODE=OFF")
    baseline_render = render(baseline_case, baseline_stimulus, baseline_params,
                             RUNS / "_T1_TERMINAL_COMPAT_RENDER")
    a012 = RUNS / "A012_PAPER_1101_1101"
    a012_manifest = next(item for item in json.loads(EXPERIMENT_MANIFEST.read_text(encoding="utf-8"))["runs"]
                         if item["run_id"] == a012.name)
    baseline_hash = hashlib.sha256(baseline_render["deck"].encode("utf-8")).hexdigest()
    expected_a012_deck = a012_manifest.get("deck_sha256")
    if (not expected_a012_deck or baseline_hash != expected_a012_deck or
            sha256(a012 / "deck.cir") != expected_a012_deck):
        raise ConfigError("DIAGONAL_TERMINAL render-only compatibility check differs from immutable A012 deck")
    if T1_ARRAY_STATIC_QA.exists() or T1_ARRAY_BATCH_MANIFEST.exists() or T1_ARRAY_RESULTS.exists():
        raise ConfigError("T1-array batch outputs already exist; refusing to overwrite")
    return cases, baseline_hash, baseline_render["static_qa"], baseline_t1_info


def run_t1_array_batch() -> int:
    cases, baseline_hash, baseline_static_qa, default_t1_info = _t1_array_case_matrix()
    solver_info = _solver_info()
    scope = json.loads(T1_ARRAY_SCOPE.read_text(encoding="utf-8"))
    static_qa = {"schema": "bvm-4x4-t1-array-static-qa-v1", "status": "PASS",
                 "batch_id": T1_ARRAY_BATCH_ID, "parent_head": _git_output("rev-parse", "HEAD"),
                 "physical_solve_count": 0, "baseline_terminal_compatibility": {
                     "status": "PASS", "run_id": "A012_PAPER_1101_1101",
                     "deck_sha256": baseline_hash, "static_qa_status": baseline_static_qa["status"]},
                 "default_t1_body_equivalent_to_canonical": default_t1_info["default_body_equivalent_to_canonical"],
                 "solver": solver_info,
                 "runs": [{"run_id": item["run_id"], "case": item["case"]["CASE"],
                           "row_bits": item["case"]["ROW_BITS"], "column_bits": item["case"]["COL_BITS"],
                           "clock_mode": item["t1_params"]["T1_CLK_MODE"],
                           "configured_input_counts": item["expected_input_counts"],
                           "t1_count": item["rendered"]["static_qa"]["t1_count"],
                           "terminal_count": item["rendered"]["static_qa"]["terminal_count"],
                           "probe_count": item["rendered"]["probes"]["signal_count"],
                           "raw_estimate_bytes": item["rendered"]["static_qa"]["raw_estimate_bytes"],
                           "t1_source_info": item["rendered"]["t1_source_info"],
                           "deck_sha256": hashlib.sha256(item["rendered"]["deck"].encode()).hexdigest()}
                          for item in cases],
                 "scientific_interpretation_performed": False}
    _json(T1_ARRAY_STATIC_QA, static_qa)
    batch = {"schema": "bvm-4x4-t1-array-batch-v1", "batch_id": T1_ARRAY_BATCH_ID,
             "parent_head": _git_output("rev-parse", "HEAD"), "risk_level": "NORMAL",
             "authorized_run_ids": [item["run_id"] for item in cases],
             "physical_solve_count_authorized": 4, "physical_solve_count_completed": 0,
             "status": "PREFLIGHT_PASS_READY", "static_qa_path": T1_ARRAY_STATIC_QA.relative_to(SERIES).as_posix(),
             "preflight_path": T1_ARRAY_PREFLIGHT.relative_to(SERIES).as_posix(),
             "preflight_sha256": sha256(T1_ARRAY_PREFLIGHT),
             "metric_spec_path": T1_ARRAY_METRIC_SPEC.relative_to(SERIES).as_posix(),
             "metric_spec_sha256": sha256(T1_ARRAY_METRIC_SPEC), "runs": [],
             "scientific_interpretation_performed": False, "automatic_follow_up": False}
    _json(T1_ARRAY_BATCH_MANIFEST, batch)
    print(f"T1_ARRAY_STATIC_GATE_PASS: {T1_ARRAY_BATCH_ID}; parent={batch['parent_head']}", flush=True)
    print(f"Baseline DIAGONAL_TERMINAL compatibility PASS: deck_sha256={baseline_hash}", flush=True)
    print(f"Authorized physical solves=4; probes/run={static_qa['runs'][0]['probe_count']}; "
          f"raw estimate/run={static_qa['runs'][0]['raw_estimate_bytes']} bytes; no 2-ohm terminals.", flush=True)
    for item in cases:
        print(f"START {item['run_id']} {item['label']} ROW/COL={item['case']['ROW_BITS']}/"
              f"{item['case']['COL_BITS']} clock={item['t1_params']['T1_CLK_MODE']}", flush=True)
        code, result = run_one(item["case"], item["stimulus"], item["t1_params"], solver_info,
                               batch_id=T1_ARRAY_BATCH_ID, run_id_override=item["run_id"],
                               rendered_override=item["rendered"], preflight_path=T1_ARRAY_PREFLIGHT,
                               metric_spec_path_override=T1_ARRAY_METRIC_SPEC)
        batch["runs"].append({"run_id": item["run_id"], "status": result.get("status"),
                              "artifact_status": result.get("artifact_status"),
                              "physical_solve_count": result.get("physical_solve_count", 1),
                              "raw_sha256": result.get("raw_sha256")})
        batch["physical_solve_count_completed"] += int(result.get("physical_solve_count", 1))
        batch["status"] = "RUNNING" if code == 0 else "STOPPED_AFTER_FAILURE"
        _json(T1_ARRAY_BATCH_MANIFEST, batch)
        print(json.dumps(result, ensure_ascii=False), flush=True)
        if code != 0:
            print("STOP: T1-array batch halted at first solver/artifact failure; no retry or follow-up.",
                  file=sys.stderr, flush=True)
            return code
    return finalize_t1_array_batch()


def preview_t1_array_batch() -> int:
    cases, baseline_hash, baseline_static_qa, _default_t1_info = _t1_array_case_matrix()
    print(json.dumps({"status": "STATIC_PREFLIGHT_PASS", "batch_id": T1_ARRAY_BATCH_ID,
                      "parent_head": _git_output("rev-parse", "HEAD"),
                      "baseline_terminal_deck_sha256": baseline_hash,
                      "baseline_terminal_static_qa": baseline_static_qa["status"],
                      "physical_solve_count": 0,
                      "runs": [{"run_id": item["run_id"], "case": item["label"],
                                "clock_mode": item["t1_params"]["T1_CLK_MODE"],
                                "input_counts": item["expected_input_counts"],
                                "probe_count": item["rendered"]["probes"]["signal_count"],
                                "raw_estimate_bytes": item["rendered"]["static_qa"]["raw_estimate_bytes"],
                                "static_qa": item["rendered"]["static_qa"]["status"]}
                               for item in cases]}, ensure_ascii=False, indent=2))
    return 0


def repair_existing(run_id: str) -> int:
    run_dir = RUNS / run_id
    if not run_dir.is_dir() or not (run_dir / "raw.csv").is_file():
        raise ConfigError(f"run/raw not found: {run_id}")
    probe = json.loads((run_dir / "probe_manifest.json").read_text(encoding="utf-8"))
    metrics, raw_qa = analyze_raw(run_dir, probe)
    _json(run_dir / "metrics.json", metrics)
    _json(run_dir / "raw_qa.json", raw_qa)
    plot_qa = render_plots(run_dir, probe)
    result = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
    if sha256(run_dir / "raw.csv") != result.get("raw_sha256"):
        raise ConfigError("existing raw no longer matches result hash")
    print(f"POSTPROCESS_REPAIR_PASS: {run_id}; no solver invocation; raw unchanged")
    return 0


def validate_t1_chain_matrix(*, write_static_qa: bool = True,
                              run_josim_sanity: bool = True) -> list[dict[str, Any]]:
    """Freeze and statically validate only the three authorized chain cases."""
    if not SOLVER.is_file() or not PLOTTER.is_file() or not PLOTLY_ASSET.is_file():
        raise ConfigError("solver, classic plotter, or shared Plotly asset is missing")
    if not T1_CHAIN_PREFLIGHT.is_file() and not write_static_qa:
        raise ConfigError("chain batch has no locked PREFLIGHT.md")
    existing = [int(match.group(1)) for path in RUNS.glob("A[0-9][0-9][0-9]_*")
                if (match := re.match(r"A(\d{3})_", path.name))]
    first = max(existing, default=0) + 1
    if first != 20:
        raise ConfigError(f"registered chain batch expects next immutable run A020; found A{first:03d}")
    if any((RUNS / run_id).exists() for run_id, *_ in T1_CHAIN_RUN_MATRIX):
        raise ConfigError("one or more A020-A022 run directories already exist; refusing overwrite")
    solver_info = _solver_info()
    source_records = verify_sources()
    rendered_cases = []
    expected_sjtl = {"D0": (1,), "D1": (1, 1), "D2": (1, 2, 1), "D3": (1, 2, 2, 1),
                     "D4": (1, 2, 1), "D5": (1, 1), "D6": (1,)}
    for run_id, preset, rows, cols, clock_mode, counts in T1_CHAIN_RUN_MATRIX:
        case, stimulus, params = load_config(preset)
        expected_case = {"CASE": preset, "ROW_BITS": rows, "COL_BITS": cols,
                         "SE_ENABLE_MASK": "ALL", "OUTPUT_MODE": "DIAGONAL_T1_CHAIN",
                         "T1_MODE": "CHAIN", "CBU_MODE": "PHYSICAL_TWO_INPUT",
                         "CARRY_MODE": "RIPPLE", "T1_CHAIN_CLOCK_MODE": clock_mode,
                         "T1_CHAIN_CLK_START": "200p", "DRIVE_MODE": "SHARED",
                         "SE_TOPOLOGY": "CELL", "SE_GATE_MODE": "CROSSPOINT",
                         "ROW_WL_WRITE_AMPLITUDE": "400u", "COL_BL_WRITE_AMPLITUDE": "400u",
                         "ROW_WL_READ_AMPLITUDE": "400u", "COL_SE_READ_AMPLITUDE": "100u",
                         "DT": "0.01p", "STOP": "300p", "PROBE_PROFILE": "t1_chain_focus",
                         "FOCUS_STAGE": "D3", "CBU_TYPE": "THmitll_MERGE",
                         "DFF_TYPE": "THmitll_DFF", "D0_JTL_TYPE": "D0_SJTL", "D0_JTL_COUNT": "1"}
        for key, value in expected_case.items():
            if case.get(key) != value:
                raise ConfigError(f"{preset}: registered {key}={value}, found {case.get(key)}")
        actual_counts = {name: _sjtl_counts(case, name) for name in DIAGONALS}
        if actual_counts != expected_sjtl:
            raise ConfigError(f"{preset}: A019 sJTL topology changed: {actual_counts}")
        if tuple(len([cell for cell in DIAGONALS[name] if cell in _active_cells(case)]) for name in DIAGONALS) != tuple(counts):
            raise ConfigError(f"{preset}: row/column mask does not map to its preregistered diagonal population")
        expected_params = {"T1_BIAS1": "1.8m", "T1_BIAS2": "1.8m", "T1_BIAS3": "1.8m",
                           "T1_R_S": "12", "T1_R_C": "12", "T1_CLK_AMPLITUDE": "1.2m",
                           "T1_CLK_RISE": "1p", "T1_CLK_WIDTH": "2p", "T1_CLK_FALL": "1p",
                           "T1_CLK_SERIES_R": "2", "DFF_R_OUT": "12",
                           "D0_JTL_AREA": "2.5", "D0_JTL_IB": "190u",
                           "D0_JTL_L1": "2.5p", "D0_JTL_L2": "2.5p", "D0_JTL_RJ": "4"}
        for key, value in expected_params.items():
            if params.get(key) != value:
                raise ConfigError(f"{preset}: preregistered physical candidate {key}={value}, found {params.get(key)}")
        if clock_mode == "GLOBAL_ONESHOT" and params["T1_CLK_SERIES_R"] != "2":
            raise ConfigError(f"{preset}: global clock series resistor must remain 2 ohm")
        run_dir_hint = RUNS / "_CHAIN_RENDER_PREVIEW"
        rendered = render(case, stimulus, params, run_dir_hint)
        if rendered["static_qa"]["status"] != "PASS":
            raise ConfigError(f"{preset}: platform static QA failed")
        if rendered["probes"]["signal_count"] >= MAX_RAW_BYTES:
            raise ConfigError(f"{preset}: probe profile fails raw storage estimate guard")
        pages = plot_signals(rendered["probes"])
        if [item["file"] for item in pages] != ["01_full_chain_overview.html",
                                                 "02_carry_propagation.html",
                                                 "03_stage_focus.html"]:
            raise ConfigError(f"{preset}: chain visualization page set changed")
        rendered_cases.append({"run_id": run_id, "preset": preset, "case": case,
                               "stimulus": stimulus, "params": params, "rendered": rendered,
                               "plot_pages": pages,
                               "deck_sha256": hashlib.sha256(rendered["deck"].encode("utf-8")).hexdigest(),
                               "stimulus_sha256": hashlib.sha256(rendered["stimulus_text"].encode("utf-8")).hexdigest()})

    # The three runs share the same circuit topology; only A020's clock branch differs
    # from the two global-clock cases. A021/A022 differ only in the registered bit masks.
    all_global = rendered_cases[1:]
    if all_global[0]["rendered"]["deck"] != all_global[1]["rendered"]["deck"]:
        raise ConfigError("A021/A022 deck differs beyond the registered row/column stimulus mask")
    if rendered_cases[0]["params"] != all_global[0]["params"]:
        raise ConfigError("QUIET/global matched cases changed physical device parameters")
    def without_clock_mode_lines(deck: str) -> list[str]:
        return [line for line in deck.splitlines()
                if not line.startswith(("V_TRIG_CLK_", "R_TRIG_CLK_", "R_CLK_QUIET_"))
                and not (line.startswith(".print ") and any(token in line for token in
                             ("I(R_TRIG_CLK_", "I(R_CLK_QUIET_")))]
    a020_clock_removed = without_clock_mode_lines(rendered_cases[0]["rendered"]["deck"])
    a021_clock_removed = without_clock_mode_lines(all_global[0]["rendered"]["deck"])
    if a020_clock_removed != a021_clock_removed:
        raise ConfigError("A020/A021 circuit decks differ beyond the registered clock network")

    def source_map(text: str) -> dict[str, str]:
        return {line.split()[0]: line for line in text.splitlines() if line.startswith("I_")}
    a021_sources, a022_sources = source_map(all_global[0]["rendered"]["stimulus_text"]), source_map(all_global[1]["rendered"]["stimulus_text"])
    if set(a021_sources) != set(a022_sources) or len(a021_sources) != 24:
        raise ConfigError("A021/A022 must preserve the same 24 physical array drive sources")
    differing_stimulus_sources = sorted(name for name in a021_sources if a021_sources[name] != a022_sources[name])
    expected_mask_differences = {f"I_SE_{cell}" for cell in CELLS
                                 if (_mask_active(all_global[0]["case"], cell) !=
                                     _mask_active(all_global[1]["case"], cell))}
    if set(differing_stimulus_sources) != expected_mask_differences | {"I_WL_R3"}:
        raise ConfigError(f"A021/A022 stimulus differences do not match ROW/COL masks: {differing_stimulus_sources}")
    for source in differing_stimulus_sources:
        before = a021_sources[source].split("PWL(", 1)[1].removesuffix(")").split()
        after = a022_sources[source].split("PWL(", 1)[1].removesuffix(")").split()
        pairs_a = list(zip(before[0::2], before[1::2], strict=True))
        pairs_b = list(zip(after[0::2], after[1::2], strict=True))
        if len(pairs_a) != len(pairs_b) or any(left[0] != right[0] for left, right in zip(pairs_a, pairs_b, strict=True)):
            raise ConfigError(f"A021/A022 stimulus time knots changed for {source}")
        if any(left[1] != right[1] and left[0] not in {"111p", "120p"}
               for left, right in zip(pairs_a, pairs_b, strict=True)):
            raise ConfigError(f"A021/A022 changed a non-FINAL_READ PWL value for {source}")

    # Render-only compatibility anchors: preserve legacy terminal and independent-T1 paths.
    terminal_case, terminal_stim, terminal_params = load_config("D3_N0")
    terminal_render = render(terminal_case, terminal_stim, terminal_params, run_dir_hint)
    independent_case = dict(terminal_case)
    independent_case.update({"OUTPUT_MODE": "DIAGONAL_T1_INDEPENDENT", "T1_MODE": "ALL_INDEPENDENT",
                             "CBU_MODE": "OFF", "CARRY_MODE": "NONE", "PROBE_PROFILE": "t1_array_focus",
                             "T1_CLK_MODE": "QUIET"})
    independent_params = dict(terminal_params)
    independent_params["T1_CLK_MODE"] = "QUIET"
    validate_config(independent_case, terminal_stim, independent_params)
    independent_render = render(independent_case, terminal_stim, independent_params, run_dir_hint)
    if terminal_render["static_qa"]["status"] != "PASS" or independent_render["static_qa"]["status"] != "PASS":
        raise ConfigError("legacy terminal/independent-T1 render-only regression failed")

    syntax_records = []
    if run_josim_sanity:
        for item in rendered_cases:
            with tempfile.TemporaryDirectory(prefix=".t1-chain-static-", dir=RUNS) as temp_name:
                temp_dir = Path(temp_name)
                actual_render = render(item["case"], item["stimulus"], item["params"], temp_dir)
                if hashlib.sha256(actual_render["deck"].encode()).hexdigest() != item["deck_sha256"]:
                    raise ConfigError(f"temporary JoSIM sanity deck differs from frozen deck for {item['preset']}")
                (temp_dir / "deck.cir").write_text(actual_render["deck"], encoding="utf-8")
                (temp_dir / "stimulus.inc").write_text(actual_render["stimulus_text"], encoding="utf-8")
                for relative, source_text in actual_render["chain_source_texts"].items():
                    target = temp_dir / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text(source_text, encoding="utf-8")
                target = temp_dir / "sources" / "t1_cell_tunable.cir"
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(actual_render["t1_source_text"], encoding="utf-8")
                command = [str(SOLVER)]
                for subckt in ("THmitll_MERGE", "THmitll_DFF", "D0_JTL", "T1", "BVM", "BQ", "sJTL", "CB"):
                    command.extend(("-s", subckt))
                command.append(str(temp_dir / "deck.cir"))
                completed = subprocess.run(command, cwd=temp_dir, capture_output=True, text=True,
                                           check=False, timeout=90)
                stdout_lines = completed.stdout.splitlines()
                stderr_lines = completed.stderr.splitlines()
                syntax_records.append({"case": item["preset"], "command": command,
                                       "exit_code": completed.returncode,
                                       "stdout_sha256": hashlib.sha256(completed.stdout.encode("utf-8")).hexdigest(),
                                       "stdout_bytes": len(completed.stdout.encode("utf-8")),
                                       "stdout_line_count": len(stdout_lines),
                                       "stdout_tail": stdout_lines[-8:],
                                       "stderr_sha256": hashlib.sha256(completed.stderr.encode("utf-8")).hexdigest(),
                                       "stderr_bytes": len(completed.stderr.encode("utf-8")),
                                       "stderr_tail": stderr_lines[-8:],
                                       "deck_sha256": item["deck_sha256"],
                                       "physical_solve_count": 0})
                if completed.returncode != 0:
                    raise ConfigError(f"JoSIM static syntax/sanity check failed for {item['preset']}: "
                                      f"{completed.stderr[-1200:] or completed.stdout[-1200:]}")

    run_records = []
    for item in rendered_cases:
        run_records.append({"run_id": item["run_id"], "case": item["preset"],
                            "row_bits": item["case"]["ROW_BITS"], "column_bits": item["case"]["COL_BITS"],
                            "clock_mode": item["case"]["T1_CHAIN_CLOCK_MODE"],
                            "clock_start": item["case"]["T1_CHAIN_CLK_START"],
                            "expected_diagonal_input_multiplicity": [len([cell for cell in cells
                                if cell in _active_cells(item["case"])]) for cells in DIAGONALS.values()],
                            "deck_sha256": item["deck_sha256"], "stimulus_sha256": item["stimulus_sha256"],
                            "probe_count": item["rendered"]["probes"]["signal_count"],
                            "probe_manifest_sha256": hashlib.sha256(
                                (json.dumps(item["rendered"]["probes"], ensure_ascii=False, indent=2)+"\n").encode("utf-8")).hexdigest(),
                            "raw_estimate_bytes": item["rendered"]["static_qa"]["raw_estimate_bytes"],
                            "static_qa_status": item["rendered"]["static_qa"]["status"],
                            "plot_pages": [page["file"] for page in item["plot_pages"]]})
    if write_static_qa:
        _json(T1_CHAIN_PROBE_MANIFEST, {
            "schema": "bvm-4x4-t1-chain-probe-registry-v1",
            "manifests_by_run_id": {item["run_id"]: item["rendered"]["probes"] for item in rendered_cases}})
    if not T1_CHAIN_PROBE_MANIFEST.is_file():
        raise ConfigError("per-run chain probe manifest registry is missing")
    probe_manifest_sha = sha256(T1_CHAIN_PROBE_MANIFEST)
    static_qa = {"schema": "bvm-4x4-t1-chain-static-qa-v1", "status": "PASS",
                 "batch_id": T1_CHAIN_BATCH_ID, "physical_solve_count": 0,
                 "parent_head": _git_output("rev-parse", "HEAD"), "solver": solver_info,
                 "runner_sha256": sha256(Path(__file__).resolve()),
                 "probe_manifest_path": T1_CHAIN_PROBE_MANIFEST.relative_to(SERIES).as_posix(),
                 "probe_manifest_sha256": probe_manifest_sha,
                 "config_sha256": {str(path.relative_to(SERIES)): sha256(path) for path in
                                   (USER_CASE, STIMULUS, T1_PARAMS, CBU_PARAMS, DFF_PARAMS, D0_JTL_PARAMS)},
                 "plotter_sha256": sha256(PLOTTER), "plotly_asset_sha256": sha256(PLOTLY_ASSET),
                 "registration_sha256": {
                     "experiment.yaml": sha256(T1_CHAIN_ANALYSIS / "experiment.yaml"),
                     "METRIC_SPEC.json": sha256(T1_CHAIN_METRIC_SPEC),
                     "CBU_COMPATIBILITY.md": sha256(T1_CHAIN_ANALYSIS / "CBU_COMPATIBILITY.md")},
                 "canonical_sources": source_records,
                 "candidate_sources": {role: entry for item in rendered_cases
                                       for role, entry in item["rendered"]["chain_source_info"].items()},
                 "source_equivalence": {"CBU_default_body_equivalent_after_syntax_fix":
                                        rendered_cases[0]["rendered"]["chain_source_info"]["CBU_RENDERED"]["default_body_equivalent_after_registered_syntax_fix"],
                                        "DFF_default_body_equivalent":
                                        rendered_cases[0]["rendered"]["chain_source_info"]["DFF_RENDERED"]["default_body_equivalent_after_registered_syntax_fix"],
                                        "D0_JTL_matches_canonical_sJTL_defaults":
                                        rendered_cases[0]["rendered"]["chain_source_info"]["D0_JTL_RENDERED"]["canonical_sJTL_defaults_match"]},
                 "legacy_render_only_regression": {"DIAGONAL_TERMINAL": terminal_render["static_qa"]["status"],
                                                    "DIAGONAL_T1_INDEPENDENT": independent_render["static_qa"]["status"],
                                                    "terminal_deck_sha256": hashlib.sha256(terminal_render["deck"].encode()).hexdigest(),
                                                    "independent_t1_deck_sha256": hashlib.sha256(independent_render["deck"].encode()).hexdigest()},
                 "josim_static_sanity": syntax_records,
                 "runs": run_records,
                 "matches_registered_topology_and_loads": True,
                 "no_duplicate_top_level_names": True,
                 "required_probe_targets_resolve": True,
                 "stimulus_mask_difference_A021_A022": differing_stimulus_sources,
                 "stimulus_non_interpolation": True,
                 "raw_storage_guard": "PASS",
                 "scientific_interpretation_performed": False}
    if write_static_qa:
        T1_CHAIN_ANALYSIS.mkdir(parents=True, exist_ok=True)
        _json(T1_CHAIN_STATIC_QA, static_qa)
    return rendered_cases


def preview_t1_chain_batch() -> int:
    cases = validate_t1_chain_matrix(write_static_qa=True, run_josim_sanity=True)
    qa = json.loads(T1_CHAIN_STATIC_QA.read_text(encoding="utf-8"))
    print(f"STATIC PREFLIGHT PASS: {T1_CHAIN_BATCH_ID}; parent={qa['parent_head']}")
    print(f"JoSIM: {qa['solver']['version'].splitlines()[-1]} sha256={qa['solver']['sha256']}")
    for item in cases:
        rendered = item["rendered"]
        print(f"{item['run_id']} {item['preset']}: ROW/COL={item['case']['ROW_BITS']}/{item['case']['COL_BITS']} "
              f"clock={item['case']['T1_CHAIN_CLOCK_MODE']}@{item['case']['T1_CHAIN_CLK_START']} "
              f"probes={rendered['probes']['signal_count']} estimate={rendered['static_qa']['raw_estimate_bytes']/1e6:.1f}MB "
              f"deck_sha256={item['deck_sha256'][:12]} static=PASS")
    print("Topology: 7 T1 + 6 THmitll_MERGE CBU + D0 sJTL + 1 THmitll_DFF; 8 independent clock branches.")
    print("Legacy TERMINAL and independent-T1 render-only compatibility: PASS.")
    print("JoSIM static syntax/sanity: PASS; physical_solve_count=0; no raw/run directory created.")
    return 0


def _update_experiment_authorization_batch(record: dict[str, Any]) -> None:
    data = json.loads(EXPERIMENT_MANIFEST.read_text(encoding="utf-8"))
    batches = data.setdefault("authorization_batches", [])
    if any(item.get("batch_id") == record["batch_id"] for item in batches):
        raise ConfigError(f"authorization batch already registered: {record['batch_id']}")
    batches.append(record)
    authorized = data.setdefault("authorized_physical_solves", [])
    for _run_id, preset, *_ in T1_CHAIN_RUN_MATRIX:
        if preset not in authorized:
            authorized.append(preset)
    _json(EXPERIMENT_MANIFEST, data)


def repair_t1_chain_existing_analysis() -> int:
    """Repair only the quiet-clock peak-time descriptor from the same immutable raw."""
    if T1_CHAIN_METRICS_REPAIR.exists():
        raise ConfigError("chain analysis repair already exists; refusing to overwrite")
    runs = []
    for run_id, preset, *_ in T1_CHAIN_RUN_MATRIX:
        run_dir = RUNS / run_id
        raw = run_dir / "raw.csv"
        result = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
        raw_before = sha256(raw)
        if raw_before != result.get("raw_sha256"):
            raise ConfigError(f"raw identity mismatch before analysis repair: {run_id}")
        probe = json.loads((run_dir / "probe_manifest.json").read_text(encoding="utf-8"))
        case = parse_env(run_dir / "USER_CASE.snapshot.env")
        old_metrics = run_dir / "metrics.json"
        old_bytes = old_metrics.read_bytes()
        old_sha = hashlib.sha256(old_bytes).hexdigest()
        retained_old = run_dir / "metrics_preclock_peak_v1.json"
        if retained_old.exists():
            raise ConfigError(f"refusing to overwrite retained old metrics: {retained_old}")
        retained_old.write_bytes(old_bytes)
        metrics, chain_qa = analyze_t1_chain_raw(run_dir, probe, case)
        if sha256(raw) != raw_before or metrics.get("raw_sha256") != raw_before:
            raise ConfigError(f"raw changed during analysis repair: {run_id}")
        _json(old_metrics, metrics)
        _json(run_dir / "chain_qa.json", chain_qa)
        _json(run_dir / "raw_qa.json", chain_qa)
        result["metrics_sha256"] = sha256(old_metrics)
        result["analysis_revision"] = 2
        _json(run_dir / "result.json", result)
        qa_path = run_dir / "qa.json"
        qa = json.loads(qa_path.read_text(encoding="utf-8"))
        qa.update({"metrics_sha256": sha256(old_metrics), "chain_qa_status": chain_qa["status"],
                   "analysis_revision": 2, "raw_sha256_after_analysis": sha256(raw),
                   "provenance_qa_status": "PENDING_REPAIR_MANIFEST_BINDING"})
        _json(qa_path, qa)
        _write_result_brief(run_dir, result, metrics)
        runs.append({"run_id": run_id, "case": preset,
                     "raw_sha256_before": raw_before, "raw_sha256_after": sha256(raw),
                     "raw_bytes": raw.stat().st_size,
                     "old_metrics_path": retained_old.relative_to(SERIES).as_posix(),
                     "old_metrics_sha256": old_sha,
                     "new_metrics_sha256": sha256(old_metrics),
                     "repair": "QUIET mode has no clock pulse; actual_clock_peak_time_ps is null for QUIET runs",
                     "solver_invoked": False})
    repair = {"schema": "bvm-4x4-t1-chain-analysis-repair-v1", "status": "PASS",
              "reason": "The original descriptive table reported a numerical quiet-clamp sample maximum as an actual clock peak.",
              "scope": "derived metrics/provenance only; immutable raw, deck, stimulus and circuit unchanged",
              "physical_solve_count": 0, "solver_invoked": False,
              "raw_sha256_unchanged": True, "runs": runs,
              "new_analysis_runner_sha256": sha256(Path(__file__).resolve()),
              "scientific_interpretation_performed": False}
    _json(T1_CHAIN_METRICS_REPAIR, repair)
    repair_sha = sha256(T1_CHAIN_METRICS_REPAIR)
    for item in runs:
        run_dir = RUNS / item["run_id"]
        provenance_path = run_dir / "provenance.json"
        provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
        provenance.update({"metrics_sha256": item["new_metrics_sha256"],
                           "chain_qa_sha256": sha256(run_dir / "chain_qa.json"),
                           "raw_qa_sha256": sha256(run_dir / "raw_qa.json"),
                           "analysis_revision": 2,
                           "analysis_runner_sha256": sha256(Path(__file__).resolve()),
                           "analysis_repair_path": T1_CHAIN_METRICS_REPAIR.relative_to(SERIES).as_posix(),
                           "analysis_repair_sha256": repair_sha,
                           "raw_sha256": item["raw_sha256_before"],
                           "scientific_interpretation_performed": False})
        _json(provenance_path, provenance)
        qa_path = run_dir / "qa.json"
        qa = json.loads(qa_path.read_text(encoding="utf-8"))
        qa.update({"provenance_qa_status": "PASS", "provenance_sha256": sha256(provenance_path),
                   "analysis_repair_sha256": repair_sha})
        _json(qa_path, qa)
    print("CHAIN_ANALYSIS_REPAIR_PASS: same raw only; no JoSIM invocation; old metrics retained.")
    return finalize_t1_chain_batch(version=2)


def finalize_t1_chain_batch(*, version: int = 1) -> int:
    if version < 1:
        raise ConfigError("chain summary version must be >= 1")
    suffix = "" if version == 1 else f"_v{version}"
    results_path = T1_CHAIN_RESULTS.with_name(f"T1_CHAIN_RESULTS{suffix}.json")
    table_path = T1_CHAIN_TABLE.with_name(f"T1_CHAIN_TABLE{suffix}.csv")
    jj_path = (T1_CHAIN_ANALYSIS / f"T1_CHAIN_JJ_PHASE_AREA{suffix}.csv")
    if results_path.exists() or table_path.exists() or jj_path.exists():
        raise ConfigError(f"refusing to overwrite existing T1-chain summary revision {version}")
    if not T1_CHAIN_BATCH_MANIFEST.is_file():
        raise ConfigError("T1-chain batch manifest is missing")
    batch = json.loads(T1_CHAIN_BATCH_MANIFEST.read_text(encoding="utf-8"))
    expected_ids = [item[0] for item in T1_CHAIN_RUN_MATRIX]
    if [item.get("run_id") for item in batch.get("runs", [])] != expected_ids:
        raise ConfigError("T1-chain summary requires exactly A020-A022 in registered order")
    if any(item.get("artifact_status") != "VALID" or item.get("qa_status") != "PASS"
           for item in batch["runs"]):
        raise ConfigError("cannot finalize chain summary with an invalid artifact or failed QA")

    summary_runs = []
    rows = []
    jj_rows = []
    theoretical = {
        "CHAIN_ALL_QUIET": {"operand": "15x15", "product": 225, "lsb_to_msb_bits": [1, 0, 0, 0, 0, 1, 1, 1]},
        "CHAIN_ALL_GLOBAL_CLOCK": {"operand": "15x15", "product": 225, "lsb_to_msb_bits": [1, 0, 0, 0, 0, 1, 1, 1]},
        "CHAIN_PAPER_GLOBAL_CLOCK": {"operand": "11x13", "product": 143, "lsb_to_msb_bits": [1, 1, 1, 1, 0, 0, 0, 1]},
    }
    for batch_run, matrix_item in zip(batch["runs"], T1_CHAIN_RUN_MATRIX, strict=True):
        run_id, preset, *_ = matrix_item
        if batch_run["run_id"] != run_id:
            raise ConfigError("T1-chain run identity order changed")
        run_dir = RUNS / run_id
        result = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
        qa = json.loads((run_dir / "qa.json").read_text(encoding="utf-8"))
        raw_qa = json.loads((run_dir / "chain_qa.json").read_text(encoding="utf-8"))
        metrics = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))
        case_manifest = json.loads((run_dir / "case_manifest.json").read_text(encoding="utf-8"))
        raw = run_dir / "raw.csv"
        raw_hash = sha256(raw)
        if (result.get("raw_sha256") != raw_hash or metrics.get("raw_sha256") != raw_hash or
                raw_qa.get("raw_sha256_after_analysis") != raw_hash or qa.get("status") != "PASS"):
            raise ConfigError(f"raw/metrics/QA identity mismatch for {run_id}")
        if result.get("physical_solve_count") != 1 or qa.get("physical_solve_count") != 1:
            raise ConfigError(f"run solve count mismatch for {run_id}")
        case = case_manifest["case"]
        by_wave = {(item["signal"], item["window"]): item for item in metrics["waveforms"]}
        by_jj = {(item["phase_signal"], item["window"]): item for item in metrics["same_jj_phase_voltage"]}

        def wave(signal: str, window: str = "TOTAL") -> dict[str, Any] | None:
            return by_wave.get((signal, window))

        def add_stage_value(row: dict[str, Any], field: str, signal: str | None) -> None:
            record = wave(signal) if signal else None
            row[field + "_signed_area_v_s"] = record["signed_area_v_s"] if record else None
            row[field + "_signed_area_phi0_arithmetic"] = record["signed_area_phi0_arithmetic"] if record else None
            row[field + "_max_v"] = record["max_v"] if record else None
            row[field + "_time_of_max_ps"] = record["time_of_max_s"]*1e12 if record else None

        for index, diagonal in enumerate(DIAGONALS):
            row = {"run_id": run_id, "case": preset, "stage": diagonal,
                   "row_bits": case["ROW_BITS"], "column_bits": case["COL_BITS"],
                   "clock_mode": case["T1_CHAIN_CLOCK_MODE"],
                   "clock_start_ps": float(_time_ps(case["T1_CHAIN_CLK_START"]))
                   if case["T1_CHAIN_CLOCK_MODE"] == "GLOBAL_ONESHOT" else None,
                   "raw_sha256": raw_hash}
            add_stage_value(row, "D_input", f"V(DOUT_{diagonal})")
            add_stage_value(row, "previous_carry", f"V(C_D{index-1})" if index else None)
            add_stage_value(row, "CBU_or_D0_JTL_output", f"V(CBU_OUT_{diagonal})" if index else "V(T1_I_D0)")
            add_stage_value(row, "T1_input", f"V(T1_I_{diagonal})")
            add_stage_value(row, "sum", f"V(S_{diagonal})")
            add_stage_value(row, "carry", f"V(C_{diagonal})")
            timing = next(item for item in metrics["stage_timing_descriptors"] if item["stage"] == diagonal)
            row["last_descriptive_input_candidate_ps"] = timing["last_descriptive_input_candidate_ps"]
            row["candidate_time_to_clock_margin_ps"] = timing["candidate_time_to_clock_margin_ps"]
            row["actual_clock_peak_time_ps"] = timing["actual_clock_peak_time_ps"]
            row["timing_candidate_only_not_event"] = True
            instance = f"XT1_{diagonal}"
            for jj in T1_CRITICAL_JJS:
                phase = by_jj.get((f"P({jj}|{instance})", "TOTAL"))
                row[f"T1_{jj}_delta_phase_rad_TOTAL"] = phase["phase_delta_rad"] if phase else None
                row[f"T1_{jj}_delta_turns_navigation_TOTAL"] = phase["phase_delta_rad_over_2pi_navigation"] if phase else None
                row[f"T1_{jj}_voltage_area_phi0_TOTAL"] = phase["voltage_area_phi0_arithmetic"] if phase else None
            if index > 0:
                cbu_instance = f"XCBU_{diagonal}"
                for jj in ("B1", "B4", "B7"):
                    phase = by_jj.get((f"P({jj}|{cbu_instance})", "TOTAL"))
                    row[f"CBU_{jj}_delta_phase_rad_TOTAL"] = phase["phase_delta_rad"] if phase else None
                    row[f"CBU_{jj}_voltage_area_phi0_TOTAL"] = phase["voltage_area_phi0_arithmetic"] if phase else None
            else:
                phase = by_jj.get(("P(BJ1|XJTL_D0_1)", "TOTAL"))
                row["D0_JTL_BJ1_delta_phase_rad_TOTAL"] = phase["phase_delta_rad"] if phase else None
                row["D0_JTL_BJ1_voltage_area_phi0_TOTAL"] = phase["voltage_area_phi0_arithmetic"] if phase else None
            rows.append(row)

        for item in metrics["same_jj_phase_voltage"]:
            jj_rows.append({"run_id": run_id, "case": preset, **item})
        dff_output = wave("V(DFF_O)")
        summary_runs.append({"run_id": run_id, "case": preset,
                             "row_bits": case["ROW_BITS"], "column_bits": case["COL_BITS"],
                             "clock_mode": case["T1_CHAIN_CLOCK_MODE"],
                             "clock_start": case["T1_CHAIN_CLK_START"],
                             "raw_path": raw.relative_to(SERIES).as_posix(),
                             "raw_bytes": raw.stat().st_size, "raw_sha256": raw_hash,
                             "deck_sha256": result["deck_sha256"],
                             "stimulus_sha256": result["stimulus_sha256"],
                             "probe_count": raw_qa["probe_count"], "sample_count": raw_qa["sample_count"],
                             "qa_status": qa["status"], "artifact_status": result["artifact_status"],
                             "dff_output_total_signed_area_phi0_arithmetic":
                             dff_output["signed_area_phi0_arithmetic"] if dff_output else None,
                             "theoretical_reference_only": theoretical[preset],
                             "actual_bit_decode": "NOT_PERFORMED; no decoder threshold preregistered",
                             "metrics_path": (run_dir / "metrics.json").relative_to(SERIES).as_posix()})

    if len(summary_runs) != 3 or sum(item["physical_solve_count"] for item in batch["runs"]) != 3:
        raise ConfigError("T1-chain batch must contain exactly three physical solves")
    table_fields = list(dict.fromkeys(key for row in rows for key in row))
    with table_path.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=table_fields)
        writer.writeheader()
        writer.writerows(rows)
    with jj_path.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(jj_rows[0]) if jj_rows else [])
        writer.writeheader()
        writer.writerows(jj_rows)

    result_summary = {"schema": "bvm-4x4-t1-chain-results-v1", "batch_id": T1_CHAIN_BATCH_ID,
                      "analysis_revision": version,
                      "status": "MECHANICAL_QA_PASS_AWAITING_USER_REVIEW",
                      "physical_solve_count": 3, "runs": summary_runs,
                      "stage_table_path": table_path.relative_to(SERIES).as_posix(),
                      "jj_phase_area_path": jj_path.relative_to(SERIES).as_posix(),
                      "stage_rows": rows,
                      "registered_windows_ps": {key: list(value) for key, value in CHAIN_WINDOWS_PS.items()},
                      "descriptive_candidate_spec": dict(T1_CANDIDATE_MORPHOLOGY_SPEC),
                      "descriptive_candidates_are_event_counts": False,
                      "actual_bit_decode": "NOT_PERFORMED; no decoder threshold preregistered",
                      "timestep_convergence": "UNKNOWN_NOT_AUTHORIZED",
                      "scientific_interpretation_performed": False,
                      "automatic_follow_up": False}
    if version > 1:
        result_summary["supersedes"] = {
            "results": T1_CHAIN_RESULTS.relative_to(SERIES).as_posix(),
            "stage_table": T1_CHAIN_TABLE.relative_to(SERIES).as_posix(),
            "jj_phase_area": (T1_CHAIN_ANALYSIS / "T1_CHAIN_JJ_PHASE_AREA.csv").relative_to(SERIES).as_posix(),
            "reason": "quiet clock clamp is not a pulse; actual_clock_peak_time_ps is now null for QUIET runs"}
    _json(results_path, result_summary)
    batch.update({"status": "MECHANICAL_QA_PASS_AWAITING_USER_REVIEW",
                  "physical_solve_count_completed": 3,
                  "summary_revision": version,
                  "summary_path": results_path.relative_to(SERIES).as_posix(),
                  "summary_sha256": sha256(results_path),
                  "stage_table_path": table_path.relative_to(SERIES).as_posix(),
                  "stage_table_sha256": sha256(table_path),
                  "jj_phase_area_path": jj_path.relative_to(SERIES).as_posix(),
                  "jj_phase_area_sha256": sha256(jj_path),
                  "scientific_interpretation_performed": False,
                  "automatic_follow_up": False})
    _json(T1_CHAIN_BATCH_MANIFEST, batch)
    print(json.dumps({"status": result_summary["status"], "batch_id": T1_CHAIN_BATCH_ID,
                      "run_ids": expected_ids, "physical_solve_count": 3,
                      "raw_sha256_by_run": {item["run_id"]: item["raw_sha256"] for item in summary_runs},
                      "scientific_interpretation_performed": False,
                      "automatic_follow_up": False}, ensure_ascii=False, indent=2), flush=True)
    return 0


def run_t1_chain_batch() -> int:
    dirty = _git_output("status", "--porcelain")
    if dirty:
        raise ConfigError("T1-chain physical batch requires a clean worktree after preflight commit")
    if not T1_CHAIN_PREFLIGHT.is_file() or not T1_CHAIN_METRIC_SPEC.is_file():
        raise ConfigError("locked T1-chain PREFLIGHT/METRIC_SPEC is required before physical solve")
    if T1_CHAIN_BATCH_MANIFEST.exists() or T1_CHAIN_RESULTS.exists() or T1_CHAIN_TABLE.exists():
        raise ConfigError("T1-chain run batch was already created; refusing a retry/overwrite")
    preflight = T1_CHAIN_PREFLIGHT.read_text(encoding="utf-8")
    if "This experiment is governed by docs/EXPERIMENT_CONTRACT.md." not in preflight:
        raise ConfigError("PREFLIGHT.md is missing the mandatory experiment-contract statement")
    if not T1_CHAIN_SCOPE.is_file():
        raise ConfigError("machine-readable chain work-unit scope is missing")
    work_unit = json.loads(T1_CHAIN_SCOPE.read_text(encoding="utf-8"))
    if (work_unit.get("preflight_sha256") != sha256(T1_CHAIN_PREFLIGHT) or
            work_unit.get("static_qa_sha256") != sha256(T1_CHAIN_STATIC_QA) or
            work_unit.get("probe_manifest_sha256") != sha256(T1_CHAIN_PROBE_MANIFEST) or
            work_unit.get("authorized_run_ids") != [item[0] for item in T1_CHAIN_RUN_MATRIX] or
            work_unit.get("physical_solve_count_authorized") != 3 or
            work_unit.get("physical_solve_count_completed") != 0):
        raise ConfigError("PREFLIGHT/WORK_UNIT/static QA hashes or exact run authorization do not match")
    cases = validate_t1_chain_matrix(write_static_qa=False, run_josim_sanity=False)
    static_qa = json.loads(T1_CHAIN_STATIC_QA.read_text(encoding="utf-8"))
    if static_qa.get("status") != "PASS" or static_qa.get("batch_id") != T1_CHAIN_BATCH_ID:
        raise ConfigError("registered static QA is not PASS for this chain batch")
    current_config_sha = {str(path.relative_to(SERIES)): sha256(path) for path in
                          (USER_CASE, STIMULUS, T1_PARAMS, CBU_PARAMS, DFF_PARAMS, D0_JTL_PARAMS)}
    current_registration_sha = {
        "experiment.yaml": sha256(T1_CHAIN_ANALYSIS / "experiment.yaml"),
        "METRIC_SPEC.json": sha256(T1_CHAIN_METRIC_SPEC),
        "CBU_COMPATIBILITY.md": sha256(T1_CHAIN_ANALYSIS / "CBU_COMPATIBILITY.md")}
    if (static_qa.get("runner_sha256") != sha256(Path(__file__).resolve()) or
            static_qa.get("config_sha256") != current_config_sha or
            static_qa.get("registration_sha256") != current_registration_sha or
            static_qa.get("probe_manifest_sha256") != sha256(T1_CHAIN_PROBE_MANIFEST) or
            static_qa.get("plotter_sha256") != sha256(PLOTTER) or
            static_qa.get("plotly_asset_sha256") != sha256(PLOTLY_ASSET)):
        raise ConfigError("runner/config/registration/visualization hashes differ from locked static QA")
    locked = {item["run_id"]: item for item in static_qa["runs"]}
    for item in cases:
        record = locked.get(item["run_id"])
        if not record or item["deck_sha256"] != record["deck_sha256"] or item["stimulus_sha256"] != record["stimulus_sha256"]:
            raise ConfigError(f"current rendered inputs do not match locked static preflight for {item['run_id']}")
        probe_bytes = (json.dumps(item["rendered"]["probes"], ensure_ascii=False, indent=2)+"\n").encode("utf-8")
        if hashlib.sha256(probe_bytes).hexdigest() != record.get("probe_manifest_sha256"):
            raise ConfigError(f"probe manifest differs from locked preflight for {item['run_id']}")
    solver_info = _solver_info()
    if (solver_info["path"] != static_qa["solver"]["path"] or
            solver_info["version"] != static_qa["solver"]["version"] or
            solver_info["sha256"] != static_qa["solver"]["sha256"]):
        raise ConfigError("JoSIM binary identity differs from the locked static preflight")

    _update_experiment_authorization_batch({
        "batch_id": T1_CHAIN_BATCH_ID, "risk_level": "NORMAL",
        "authorized_cases": [item[1] for item in T1_CHAIN_RUN_MATRIX],
        "run_ids": [item[0] for item in T1_CHAIN_RUN_MATRIX],
        "authorized_physical_solve_count": 3, "physical_solve_count_completed": 0,
        "parent_head_at_execution": solver_info["parent_head"],
        "preflight_sha256": sha256(T1_CHAIN_PREFLIGHT),
        "static_qa_sha256": sha256(T1_CHAIN_STATIC_QA),
        "scientific_interpretation_performed": False, "automatic_follow_up": False})
    batch = {"schema": "bvm-4x4-t1-chain-batch-manifest-v1", "batch_id": T1_CHAIN_BATCH_ID,
             "status": "RUNNING", "parent_head_at_execution": solver_info["parent_head"],
             "preflight_path": T1_CHAIN_PREFLIGHT.relative_to(SERIES).as_posix(),
             "preflight_sha256": sha256(T1_CHAIN_PREFLIGHT),
             "metric_spec_path": T1_CHAIN_METRIC_SPEC.relative_to(SERIES).as_posix(),
             "metric_spec_sha256": sha256(T1_CHAIN_METRIC_SPEC),
             "static_qa_path": T1_CHAIN_STATIC_QA.relative_to(SERIES).as_posix(),
             "static_qa_sha256": sha256(T1_CHAIN_STATIC_QA),
             "authorized_run_ids": [item[0] for item in T1_CHAIN_RUN_MATRIX],
             "runs": [], "physical_solve_count_completed": 0,
             "scientific_interpretation_performed": False, "automatic_follow_up": False}
    _json(T1_CHAIN_BATCH_MANIFEST, batch)
    for item in cases:
        run_id = item["run_id"]
        case = item["case"]
        print(f"START {run_id}: {case['CASE']} ROW/COL={case['ROW_BITS']}/{case['COL_BITS']} "
              f"clock={case['T1_CHAIN_CLOCK_MODE']}", flush=True)
        code, result = run_one(case, item["stimulus"], item["params"], solver_info,
                               batch_id=T1_CHAIN_BATCH_ID, run_id_override=run_id,
                               rendered_override=item["rendered"], preflight_path=T1_CHAIN_PREFLIGHT,
                               metric_spec_path_override=T1_CHAIN_METRIC_SPEC,
                               expected_deck_sha256=locked[run_id]["deck_sha256"])
        run_record = {"run_id": run_id, "case": case["CASE"], "status": result.get("status"),
                      "artifact_status": result.get("artifact_status"),
                      "physical_solve_count": result.get("physical_solve_count", 1),
                      "qa_status": result.get("qa_status"), "raw_sha256": result.get("raw_sha256"),
                      "raw_bytes": result.get("raw_bytes"), "deck_sha256": result.get("deck_sha256")}
        batch["runs"].append(run_record)
        batch["physical_solve_count_completed"] += int(result.get("physical_solve_count", 1))
        batch["status"] = "RUNNING" if code == 0 else "STOPPED_AFTER_ARTIFACT_FAILURE"
        _json(T1_CHAIN_BATCH_MANIFEST, batch)
        print(json.dumps(result, ensure_ascii=False), flush=True)
        if code != 0:
            print("STOP: chain batch halted at first solver/artifact failure; no retry or later solve.",
                  file=sys.stderr, flush=True)
            return code
    return finalize_t1_chain_batch()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="BVM 4x4 diagonal-array render/run helper")
    parser.add_argument("--preset", choices=PRESET_CASES)
    parser.add_argument("--set", action="append", default=[], metavar="KEY=VALUE")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--registered-matrix", action="store_true")
    parser.add_argument("--registered-batch", action="store_true")
    parser.add_argument("--bus400-batch", action="store_true",
                        help="run only BUS400_D3_N0 then BUS400_D3_N1, or add --dry-run for its static gate")
    parser.add_argument("--t1-array-batch", action="store_true",
                        help="execute exactly the preregistered four-run seven-T1 QUIET/PULSE batch")
    parser.add_argument("--t1-chain-batch", action="store_true",
                        help="execute only the preregistered A020-A022 physical ripple-chain batch")
    parser.add_argument("--finalize-t1-array-batch", action="store_true",
                        help="rebuild the T1-array arithmetic summary from already QA-passed raw; never invokes JoSIM")
    parser.add_argument("--finalize-t1-chain-batch", action="store_true",
                        help="rebuild chain arithmetic tables from already QA-passed A020-A022 raw; no solver")
    parser.add_argument("--repair-t1-chain-analysis", action="store_true",
                        help="repair chain descriptive metrics from the same immutable A020-A022 raw; no solver")
    parser.add_argument("--summary-version", type=int, default=1,
                        help="version for an explicit chain summary rebuild; used with --finalize-t1-chain-batch")
    parser.add_argument("--postprocess", metavar="RUN_ID")
    parser.add_argument("--repair-bus400-html", action="store_true",
                        help="rebuild responsive classic plots from A007/A008 raw only; never invokes JoSIM")
    parser.add_argument("--repair-t1-classic-plots", action="store_true",
                        help="regenerate A013-A016 T1 HTML with classic josim-plot2 canvas defaults; no solver")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.postprocess:
            return repair_existing(args.postprocess)
        if args.repair_bus400_html:
            return repair_bus400_html_batch()
        if args.repair_t1_classic_plots:
            return repair_t1_classic_plots()
        if args.finalize_t1_array_batch:
            return finalize_t1_array_batch()
        if args.finalize_t1_chain_batch:
            return finalize_t1_chain_batch(version=args.summary_version)
        if args.repair_t1_chain_analysis:
            return repair_t1_chain_existing_analysis()
        if args.t1_chain_batch:
            if args.preset or args.set:
                raise ConfigError("--t1-chain-batch owns the frozen A020-A022 matrix; do not combine --preset/--set")
            return preview_t1_chain_batch() if args.dry_run else run_t1_chain_batch()
        if args.t1_array_batch:
            if args.preset or args.set:
                raise ConfigError("--t1-array-batch owns its frozen four-run matrix; do not combine --preset/--set")
            return preview_t1_array_batch() if args.dry_run else run_t1_array_batch()
        if args.registered_batch:
            return run_registered_batch()
        if args.bus400_batch:
            return preview_bus400_batch() if args.dry_run else run_bus400_batch()
        if args.registered_matrix:
            return _print_matrix_preview()
        case, stimulus, t1_params = load_config(args.preset, args.set)
        if args.dry_run:
            return dry_run(case, stimulus, t1_params, verbose=args.verbose)
        solver_info = _solver_info()
        code, _ = run_one(case, stimulus, t1_params, solver_info)
        return code
    except (OSError, ConfigError, KeyError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
