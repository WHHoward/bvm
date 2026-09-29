#!/usr/bin/env python3
"""Static/dry-run and one-config-at-a-time runner for the 2x2 BVM platform."""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import os
import re
import shlex
import statistics
import subprocess
import sys
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from types import SimpleNamespace
from typing import Any

SERIES = Path(__file__).resolve().parents[1]
REPO = next(path for path in SERIES.parents if (path / ".git").exists())
sys.path.insert(0, str(REPO / "scripts"))
RUNS = SERIES / "runs"
USER_CASE = SERIES / "USER_CASE.env"
STIMULUS = SERIES / "STIMULUS.env"
METRIC_SPEC = SERIES / "analysis" / "metric_spec.json"
PRESETS_DIR = SERIES / "presets"
SOLVER = REPO / "build" / "josim-cli"
PLOTTER = REPO / "scripts" / "josim-plot2.py"
PLOTLY_ASSET = (REPO / "test/exploration/bvm-qb-cb-array-topology-v1-20260924"
                / "plots/assets/plotly.min.js")

SOURCE_PATHS = {
    "JJMIT": "circuits/models/jjmit.cir",
    "BVM": "circuits/bvm/bvm_cell_0923.cir",
    "QB": "circuits/qb/BQ_0928.cir",
    "SJTL": "circuits/sJTL_0923.cir",
    "POST_CB": "circuits/CB/CB_0928.cir",
}
SOURCE_SHA256 = {
    "JJMIT": "19862d1fd1f1f44dfa1523848d7d3b5e2594a6c5da8fdd80144b449e5312a336",
    "BVM": "ddf90076d40c0856f73dfcdcd22adeae6eddb7dd650798957a0d6c73953456b7",
    "QB": "82e6f6c7a95856c6d7bcdd28a56c009a815fc77e237a76af08fbebe45eed988a",
    "SJTL": "3cbc6889f9b4cd6b7764efa4a591f9d4dcdb0b2b86ded1f265dadabda1040688",
    "POST_CB": "70a6af05acccb7c354799d5b1b7542c86c677970681473f559bbf0f7e4d6d370",
}

CASE_KEYS = {
    "NAME", "DRIVE_MODE", "ROW_BITS", "COL_BITS", "ROW_WL_READ_AMPLITUDE",
    "COL_SE_READ_AMPLITUDE", "ROW_WL_WRITE_AMPLITUDE", "COL_BL_WRITE_AMPLITUDE",
    "SE_TOPOLOGY", "SE_GATE_MODE", "SJTL_PER_CELL", "POST_CB_PER_CELL", "TERM_R",
    "DT", "STOP", "PROBE_PROFILE", "SECOND_READ_ENABLE", "SECOND_ROW_BITS",
    "SECOND_COL_BITS", "READ0_ENABLE", "WRITE1_MODE", "WRITE1_TARGET_1",
    "WRITE1_TARGET_2",
}
OPTIONAL_SE_KEYS = {"SE_TOPOLOGY", "SE_GATE_MODE"}
LEGACY_SE_DEFAULTS = {"SE_TOPOLOGY": "SHARED_COLUMN", "SE_GATE_MODE": "COLUMN"}
OPTIONAL_SECOND_CASE_KEYS = {"SECOND_READ_ENABLE", "SECOND_ROW_BITS", "SECOND_COL_BITS"}
OPTIONAL_WRITE_SEQUENCE_KEYS = {
    "READ0_ENABLE", "WRITE1_MODE", "WRITE1_TARGET_1", "WRITE1_TARGET_2",
}
SECOND_READ_DEFAULTS = {
    "SECOND_READ_ENABLE": "0", "SECOND_ROW_BITS": "01", "SECOND_COL_BITS": "10",
}
WRITE_SEQUENCE_DEFAULTS = {
    "READ0_ENABLE": "1", "WRITE1_MODE": "SIMULTANEOUS",
    "WRITE1_TARGET_1": "NONE", "WRITE1_TARGET_2": "NONE",
}
BASE_STIMULUS_KEYS = {
    f"{stage}_{field}"
    for stage in ("WRITE0", "READ0", "WRITE1", "FINAL_READ")
    for field in ("START", "RISE", "HOLD", "FALL")
}
SECOND_READ_STIMULUS_KEYS = {
    f"SECOND_READ_{field}" for field in ("START", "RISE", "HOLD", "FALL")
}
SELECTIVE_WRITE_STIMULUS_KEYS = {"WRITE1_TARGET_1_START", "WRITE1_TARGET_2_START"}
STIMULUS_KEYS = BASE_STIMULUS_KEYS | SECOND_READ_STIMULUS_KEYS | SELECTIVE_WRITE_STIMULUS_KEYS
DEFAULT_PRESET = "A_INDEPENDENT_10_10"
PRESET_NAMES = {
    "A_INDEPENDENT_10_10", "B_SHARED_10_10", "C_SHARED_11_11",
    "D0_CELL_SE_COLUMN_10_10", "D1_CELL_SE_CROSSPOINT_10_10",
    "E0_A005_CROSSPOINT_SECOND_READ", "E1_A006_COLUMN_SECOND_READ",
    "A_SAME_COLUMN_DUAL_CROSSPOINT", "B_ALL_CELL_CROSSPOINT",
    "C_MIXED_STORAGE_SEQUENTIAL_WRITE",
}
ROWS = (1, 2)
COLS = (1, 2)
CELL_JJS = ("B_JM1", "B_JM2", "B_JS1", "B_JS2")
QB_JJS = ("BJ1", "BJ2", "BJ3")
SJTL_JJS = ("BJ1",)
CB_JJS = ("BJ1", "BJ2")
PHI0_VS = 2.067833848e-15
UNIT_SCALE = {
    "": Decimal("1"), "p": Decimal("1e-12"), "n": Decimal("1e-9"),
    "u": Decimal("1e-6"), "m": Decimal("1e-3"), "k": Decimal("1e3"),
}


class ConfigError(ValueError):
    pass


def sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8")


def parse_env(path: str | Path, allowed: set[str], *, required: set[str] | None = None) -> dict[str, str]:
    source = Path(path)
    values: dict[str, str] = {}
    for line_no, raw in enumerate(source.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ConfigError(f"{source}:{line_no}: expected KEY=VALUE")
        key, value = (part.strip() for part in line.split("=", 1))
        if key not in allowed:
            raise ConfigError(f"{source}:{line_no}: unknown key {key!r}")
        if key in values:
            raise ConfigError(f"{source}:{line_no}: duplicate key {key!r}")
        if not value:
            raise ConfigError(f"{source}:{line_no}: empty value for {key}")
        values[key] = value
    missing = sorted((required or set()) - values.keys())
    if missing:
        raise ConfigError(f"{source}: missing required keys: {', '.join(missing)}")
    return values


def quantity(token: str, label: str) -> Decimal:
    match = re.fullmatch(r"\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)\s*([pnumk]?)\s*",
                         token)
    if not match:
        raise ConfigError(f"{label}: invalid scalar {token!r}")
    try:
        value = Decimal(match.group(1)) * UNIT_SCALE[match.group(2)]
    except (InvalidOperation, KeyError) as exc:
        raise ConfigError(f"{label}: invalid scalar {token!r}") from exc
    if not value.is_finite():
        raise ConfigError(f"{label}: value must be finite")
    return value


def fmt_decimal(value: Decimal) -> str:
    normalized = value.normalize()
    rendered = format(normalized, "f")
    if "." in rendered:
        rendered = rendered.rstrip("0").rstrip(".")
    return rendered or "0"


def fmt_time(seconds: Decimal) -> str:
    if seconds == 0:
        return "0"
    return f"{fmt_decimal(seconds / Decimal('1e-12'))}p"


def load_config(preset: str | None = None) -> tuple[dict[str, str], dict[str, str]]:
    optional_case_keys = (OPTIONAL_SE_KEYS | OPTIONAL_SECOND_CASE_KEYS |
                          OPTIONAL_WRITE_SEQUENCE_KEYS)
    case = parse_env(USER_CASE, CASE_KEYS, required=CASE_KEYS - optional_case_keys)
    case = _with_se_defaults(case)
    case = _with_second_read_defaults(case)
    case = _with_write_sequence_defaults(case)
    stimulus_overrides: dict[str, str] = {}
    if preset is not None:
        if preset not in PRESET_NAMES:
            raise ConfigError(f"unknown preset {preset!r}; choose one of {sorted(PRESET_NAMES)}")
        preset_path = PRESETS_DIR / f"{preset}.env"
        preset_fixed_keys = {"NAME", "SJTL_PER_CELL", "POST_CB_PER_CELL", "TERM_R",
                             "PROBE_PROFILE"}
        optional_preset_keys = optional_case_keys | {"DT", "STOP"}
        overrides = parse_env(preset_path, (CASE_KEYS | STIMULUS_KEYS) - preset_fixed_keys,
                              required=CASE_KEYS - preset_fixed_keys - optional_preset_keys)
        case.update({key: value for key, value in overrides.items() if key in CASE_KEYS})
        stimulus_overrides = {key: value for key, value in overrides.items() if key in STIMULUS_KEYS}
        # Legacy A/B/C presets intentionally retain their original SE behavior,
        # even when the editable USER_CASE now selects a new CELL topology.
        for key, value in LEGACY_SE_DEFAULTS.items():
            if key not in overrides:
                case[key] = value
        for key, value in SECOND_READ_DEFAULTS.items():
            if key not in overrides:
                case[key] = value
        for key, value in WRITE_SEQUENCE_DEFAULTS.items():
            if key not in overrides:
                case[key] = value
    stimulus = parse_env(STIMULUS, STIMULUS_KEYS, required=BASE_STIMULUS_KEYS)
    stimulus.update(stimulus_overrides)
    validate_config(case, stimulus)
    verify_sources()
    return case, stimulus


def _with_se_defaults(case: dict[str, str]) -> dict[str, str]:
    effective = dict(case)
    for key, value in LEGACY_SE_DEFAULTS.items():
        effective.setdefault(key, value)
    return effective


def _with_second_read_defaults(case: dict[str, str]) -> dict[str, str]:
    effective = dict(case)
    for key, value in SECOND_READ_DEFAULTS.items():
        effective.setdefault(key, value)
    return effective


def _with_write_sequence_defaults(case: dict[str, str]) -> dict[str, str]:
    effective = dict(case)
    for key, value in WRITE_SEQUENCE_DEFAULTS.items():
        effective.setdefault(key, value)
    return effective


def validate_config(case: dict[str, str], stimulus: dict[str, str]) -> None:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", case["NAME"]):
        raise ConfigError("NAME must contain only letters, digits, underscore, or hyphen")
    if case["DRIVE_MODE"] not in {"INDEPENDENT", "SHARED"}:
        raise ConfigError("DRIVE_MODE must be INDEPENDENT or SHARED")
    if case["SE_TOPOLOGY"] not in {"SHARED_COLUMN", "CELL"}:
        raise ConfigError("SE_TOPOLOGY must be SHARED_COLUMN or CELL")
    if case["SE_GATE_MODE"] not in {"COLUMN", "CROSSPOINT"}:
        raise ConfigError("SE_GATE_MODE must be COLUMN or CROSSPOINT")
    if case["SE_GATE_MODE"] == "CROSSPOINT" and _effective_se_topology(case) != "CELL":
        raise ConfigError("SE_GATE_MODE=CROSSPOINT requires independent per-cell SE nodes")
    if case["SECOND_READ_ENABLE"] not in {"0", "1"}:
        raise ConfigError("SECOND_READ_ENABLE must be 0 or 1")
    if case["READ0_ENABLE"] not in {"0", "1"}:
        raise ConfigError("READ0_ENABLE must be 0 or 1")
    if case["WRITE1_MODE"] not in {"SIMULTANEOUS", "SEQUENTIAL_CROSSPOINT"}:
        raise ConfigError("WRITE1_MODE must be SIMULTANEOUS or SEQUENTIAL_CROSSPOINT")
    for key in ("SECOND_ROW_BITS", "SECOND_COL_BITS"):
        if not re.fullmatch(r"[01]{2}", case[key]):
            raise ConfigError(f"{key} must be exactly two bits; leftmost bit selects index 1")
    second_read_enabled = case["SECOND_READ_ENABLE"] == "1"
    if second_read_enabled and _effective_se_topology(case) != "CELL":
        raise ConfigError("SECOND_READ_ENABLE=1 requires independent per-cell SE nodes")
    for key in ("ROW_BITS", "COL_BITS"):
        if not re.fullmatch(r"[01]{2}", case[key]):
            raise ConfigError(f"{key} must be exactly two bits; leftmost bit selects index 1")
    for key in ("ROW_WL_READ_AMPLITUDE", "COL_SE_READ_AMPLITUDE",
                "ROW_WL_WRITE_AMPLITUDE", "COL_BL_WRITE_AMPLITUDE", "DT", "STOP", "TERM_R"):
        if quantity(case[key], key) <= 0:
            raise ConfigError(f"{key} must be positive")
    if case["PROBE_PROFILE"] not in {"core", "debug"}:
        raise ConfigError("PROBE_PROFILE must be core or debug")
    if case["SJTL_PER_CELL"] != "1" or case["POST_CB_PER_CELL"] != "1":
        raise ConfigError("this platform freezes exactly one sJTL and one post-CB per cell")
    if quantity(case["TERM_R"], "TERM_R") != Decimal("2"):
        raise ConfigError("TERM_R is frozen at 2 ohm for a matched output load")

    if case["WRITE1_MODE"] == "SEQUENTIAL_CROSSPOINT":
        if (case["DRIVE_MODE"] != "SHARED" or case["SE_TOPOLOGY"] != "CELL" or
                case["SE_GATE_MODE"] != "CROSSPOINT"):
            raise ConfigError("SEQUENTIAL_CROSSPOINT requires SHARED + CELL + CROSSPOINT")
        target_pattern = re.compile(r"R[12]C[12]")
        targets = [case["WRITE1_TARGET_1"], case["WRITE1_TARGET_2"]]
        if any(not target_pattern.fullmatch(target) for target in targets):
            raise ConfigError("selective WRITE1 targets must be R1C1/R1C2/R2C1/R2C2")
        if targets[0] == targets[1]:
            raise ConfigError("selective WRITE1 targets must be distinct")
        if case["SECOND_READ_ENABLE"] == "1":
            raise ConfigError("SEQUENTIAL_CROSSPOINT preset forbids SECOND_READ")
        if not SELECTIVE_WRITE_STIMULUS_KEYS.issubset(stimulus):
            raise ConfigError("sequential WRITE1 requires both per-target start times")

    windows: list[tuple[str, Decimal, Decimal]] = []
    for stage in _active_stages(case):
        start, rise, hold, fall = _stage_timing(stage, stimulus)
        if start < 0 or rise <= 0 or hold < 0 or fall <= 0:
            raise ConfigError(f"{stage}: start/hold must be nonnegative; rise/fall must be positive")
        windows.append((stage, start, start + rise + hold + fall))
    for previous, current in zip(windows, windows[1:]):
        if current[1] < previous[2]:
            if previous[0] == "FINAL_READ" and current[0] == "SECOND_READ":
                raise ConfigError("SECOND_READ overlaps FINAL_READ")
            raise ConfigError(f"stimulus stages overlap: {previous[0]} / {current[0]}")
    if windows[-1][2] > quantity(case["STOP"], "STOP"):
        raise ConfigError(f"{windows[-1][0]} ends after STOP")
    provided_second_timing = SECOND_READ_STIMULUS_KEYS & stimulus.keys()
    if second_read_enabled and provided_second_timing != SECOND_READ_STIMULUS_KEYS:
        missing = sorted(SECOND_READ_STIMULUS_KEYS - stimulus.keys())
        raise ConfigError(f"SECOND_READ is enabled but timing fields are missing: {', '.join(missing)}")
    if case["WRITE1_MODE"] == "SEQUENTIAL_CROSSPOINT":
        first = _stage_timing("WRITE1_TARGET_1", stimulus)
        second = _stage_timing("WRITE1_TARGET_2", stimulus)
        if second[0] < first[0] + first[1] + first[2] + first[3]:
            raise ConfigError("selective WRITE1 target pulses must not overlap")


def verify_sources() -> dict[str, dict[str, str]]:
    records: dict[str, dict[str, str]] = {}
    for role, relative in SOURCE_PATHS.items():
        path = REPO / relative
        if not path.is_file():
            raise ConfigError(f"canonical {role} source is missing: {relative}")
        digest = sha256(path)
        if digest != SOURCE_SHA256[role]:
            raise ConfigError(f"canonical {role} source hash changed; human review required: {relative}")
        records[role] = {"path": relative, "sha256": digest,
                         "mode": "DIRECT_CANONICAL_INCLUDE"}
    return records


def parse_subckt(role: str) -> tuple[str, ...]:
    path = REPO / SOURCE_PATHS[role]
    target = {"BVM": "BVM", "QB": "BQ", "SJTL": "sJTL", "POST_CB": "CB"}[role]
    found: list[tuple[str, ...]] = []
    for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if line.casefold().startswith(".subckt"):
            pieces = line.split()
            if len(pieces) < 3:
                raise ConfigError(f"{path}:{line_no}: malformed .subckt declaration")
            if pieces[1].casefold() == target.casefold():
                found.append(tuple(pieces[2:]))
    if len(found) != 1:
        raise ConfigError(f"{path}: expected exactly one .subckt {target}, found {len(found)}")
    expected = ("WL", "BL", "SE", "SL") if role == "BVM" else ("IN", "OUT")
    if tuple(pin.casefold() for pin in found[0]) != tuple(pin.casefold() for pin in expected):
        raise ConfigError(f"{path}: {target} pin order changed: {found[0]}")
    return found[0]


def source_elements(role: str) -> list[str]:
    path = REPO / SOURCE_PATHS[role]
    target = {"BVM": "BVM", "QB": "BQ", "SJTL": "sJTL", "POST_CB": "CB"}[role]
    active = False
    elements: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("*"):
            continue
        if line.casefold().startswith(".subckt"):
            active = line.split()[1].casefold() == target.casefold()
            continue
        if line.casefold().startswith(".ends"):
            active = False
            continue
        if active and not line.startswith("."):
            element = line.split()[0]
            if element not in elements:
                elements.append(element)
    return elements


def cell_id(row: int, col: int) -> str:
    return f"R{row}C{col}"


def cell_selected(case: dict[str, str], row: int, col: int) -> bool:
    return case["ROW_BITS"][row - 1] == "1" and case["COL_BITS"][col - 1] == "1"


def _effective_se_topology(case: dict[str, str]) -> str:
    # INDEPENDENT drive has always provided a separate SE source per cell.
    return "CELL" if case["DRIVE_MODE"] == "INDEPENDENT" else case["SE_TOPOLOGY"]


def _final_read_se_enabled(case: dict[str, str], row: int, col: int) -> bool:
    if case["SE_GATE_MODE"] == "CROSSPOINT":
        return cell_selected(case, row, col)
    return case["COL_BITS"][col - 1] == "1"


def _second_read_enabled(case: dict[str, str]) -> bool:
    return case["SECOND_READ_ENABLE"] == "1"


def _second_read_se_enabled(case: dict[str, str], row: int, col: int) -> bool:
    return (_second_read_enabled(case) and
            case["SECOND_ROW_BITS"][row - 1] == "1" and
            case["SECOND_COL_BITS"][col - 1] == "1")


def _active_stages(case: dict[str, str]) -> tuple[str, ...]:
    base = ["WRITE0"]
    if case["READ0_ENABLE"] == "1":
        base.append("READ0")
    if case["WRITE1_MODE"] == "SEQUENTIAL_CROSSPOINT":
        base.extend(("WRITE1_TARGET_1", "WRITE1_TARGET_2"))
    else:
        base.append("WRITE1")
    base.append("FINAL_READ")
    return tuple(base) + (("SECOND_READ",) if _second_read_enabled(case) else ())


def _stage_timing(stage: str, stimulus: dict[str, str]
                  ) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    if stage.startswith("WRITE1_TARGET_"):
        width_prefix = "WRITE1"
        start_key = f"{stage}_START"
    else:
        width_prefix = stage
        start_key = f"{stage}_START"
    try:
        return (
            quantity(stimulus[start_key], start_key),
            quantity(stimulus[f"{width_prefix}_RISE"], f"{width_prefix}_RISE"),
            quantity(stimulus[f"{width_prefix}_HOLD"], f"{width_prefix}_HOLD"),
            quantity(stimulus[f"{width_prefix}_FALL"], f"{width_prefix}_FALL"),
        )
    except KeyError as exc:
        raise ConfigError(f"missing timing field for stage {stage}: {exc.args[0]}") from exc


def cell_selection_groups(case: dict[str, str]) -> dict[str, list[str]]:
    selected: list[str] = []
    half_selected: list[str] = []
    unselected: list[str] = []
    for row in ROWS:
        for col in COLS:
            row_on = case["ROW_BITS"][row - 1] == "1"
            col_on = case["COL_BITS"][col - 1] == "1"
            name = cell_id(row, col)
            if row_on and col_on:
                selected.append(name)
            elif row_on or col_on:
                half_selected.append(name)
            else:
                unselected.append(name)
    return {"active_crosspoints": selected, "half_selected": half_selected,
            "unselected": unselected}


def _driver_layout(case: dict[str, str]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    shared = case["DRIVE_MODE"] == "SHARED"
    if shared:
        for row in ROWS:
            records.append({"source": f"I_WL_R{row}", "branch": "WL",
                            "line": f"ROW{row}", "node": f"WL_R{row}",
                            "cells": [cell_id(row, col) for col in COLS]})
        for col in COLS:
            records.append({"source": f"I_BL_C{col}", "branch": "BL",
                            "line": f"COL{col}", "node": f"BL_C{col}",
                            "cells": [cell_id(row, col) for row in ROWS]})
        if _effective_se_topology(case) == "SHARED_COLUMN":
            for col in COLS:
                records.append({"source": f"I_SE_C{col}", "branch": "SE",
                                "line": f"COL{col}", "node": f"SE_C{col}",
                                "cells": [cell_id(row, col) for row in ROWS]})
        else:
            for row in ROWS:
                for col in COLS:
                    name = cell_id(row, col)
                    records.append({"source": f"I_SE_{name}", "branch": "SE",
                                    "line": name, "node": f"SE_{name}", "cells": [name]})
    else:
        for row in ROWS:
            for col in COLS:
                name = cell_id(row, col)
                for branch in ("WL", "BL", "SE"):
                    records.append({"source": f"I_{branch}_{name}", "branch": branch,
                                    "line": name, "node": f"{branch}_{name}", "cells": [name]})
    return records


def _branch_amplitude(case: dict[str, str], branch: str, stage: str,
                      row: int | None, col: int | None) -> str:
    if stage.startswith("WRITE1_TARGET_"):
        slot = stage.removeprefix("WRITE1_TARGET_")
        target = case[f"WRITE1_TARGET_{slot}"]
        target_row, target_col = int(target[1]), int(target[3])
        if branch == "WL":
            return case["ROW_WL_WRITE_AMPLITUDE"] if row == target_row else "0"
        if branch == "BL":
            return case["COL_BL_WRITE_AMPLITUDE"] if col == target_col else "0"
        return "0"
    if branch == "WL":
        amplitude = case["ROW_WL_WRITE_AMPLITUDE"] if stage in {"WRITE0", "WRITE1"} \
            else case["ROW_WL_READ_AMPLITUDE"]
        if stage == "FINAL_READ":
            enabled = case["ROW_BITS"][int(row) - 1] == "1"
        elif stage == "SECOND_READ":
            enabled = case["SECOND_ROW_BITS"][int(row) - 1] == "1"
        else:
            enabled = True
    elif branch == "BL":
        if stage not in {"WRITE0", "WRITE1"}:
            return "0"
        amplitude = case["COL_BL_WRITE_AMPLITUDE"]
        enabled = True
    else:
        if stage in {"WRITE0", "WRITE1"}:
            return "0"
        amplitude = case["COL_SE_READ_AMPLITUDE"]
        if stage == "READ0":
            enabled = True
        elif stage == "SECOND_READ":
            if row is None:
                raise ConfigError("SECOND_READ requires independent per-cell SE sources")
            enabled = _second_read_se_enabled(case, int(row), int(col))
        elif case["SE_GATE_MODE"] == "COLUMN":
            enabled = case["COL_BITS"][int(col) - 1] == "1"
        else:
            if row is None:
                raise ConfigError("CROSSPOINT SE driver must identify a single cell row")
            enabled = cell_selected(case, int(row), int(col))
    if not enabled:
        return "0"
    if stage == "WRITE0" and branch in {"WL", "BL"}:
        return f"-{amplitude}"
    return amplitude


def _stimulus_for_driver(case: dict[str, str], stimulus: dict[str, str],
                         driver: dict[str, Any]) -> tuple[list[tuple[Decimal, str]], dict[str, str]]:
    cells = driver["cells"]
    row = int(cells[0][1]) if cells else None
    col = int(cells[0][3]) if cells else None
    # Shared drivers use their row/column identity, not a representative cell's other bit.
    if case["DRIVE_MODE"] == "SHARED":
        if driver["branch"] == "WL":
            row = int(driver["line"][-1])
            col = None
        elif driver["branch"] == "BL" or _effective_se_topology(case) == "SHARED_COLUMN":
            col = int(driver["line"][-1])
            row = None

    points: list[tuple[Decimal, str]] = [(Decimal(0), "0")]
    stage_values: dict[str, str] = {}
    for stage in _active_stages(case):
        start, rise, hold, fall = _stage_timing(stage, stimulus)
        value = _branch_amplitude(case, driver["branch"], stage, row, col)
        stage_values[stage] = value
        for timestamp, signal in ((start, "0"), (start + rise, value),
                                  (start + rise + hold, value),
                                  (start + rise + hold + fall, "0")):
            if points and timestamp < points[-1][0]:
                raise ConfigError(f"nonmonotonic generated PWL for {driver['source']}")
            if points and timestamp == points[-1][0]:
                if points[-1][1] != signal:
                    raise ConfigError(f"conflicting PWL values at {fmt_time(timestamp)} for {driver['source']}")
                continue
            points.append((timestamp, signal))
    stop = quantity(case["STOP"], "STOP")
    if stop < points[-1][0]:
        raise ConfigError(f"STOP precedes final stimulus for {driver['source']}")
    points.append((stop, "0"))
    return points, stage_values


def _source_target(role: str) -> str:
    return {"BVM": "BVM", "QB": "BQ", "SJTL": "sJTL", "POST_CB": "CB"}[role]


def render(case: dict[str, str], stimulus: dict[str, str], run_dir: Path) -> dict[str, Any]:
    sources = verify_sources()
    for role in ("BVM", "QB", "SJTL", "POST_CB"):
        parse_subckt(role)
    drivers = _driver_layout(case)
    driver_points: dict[str, list[tuple[Decimal, str]]] = {}
    driver_stages: dict[str, dict[str, str]] = {}
    drive_lines: list[str] = []
    for driver in drivers:
        points, stages = _stimulus_for_driver(case, stimulus, driver)
        driver_points[driver["source"]] = points
        driver_stages[driver["source"]] = stages
        pwl = " ".join(f"{fmt_time(t)} {v}" for t, v in points)
        drive_lines.append(f"{driver['source']} 0 {driver['node']} PWL({pwl})")
    stimulus_text = "* Exact generated row/column current-source PWLs.\n" + "\n".join(drive_lines) + "\n"

    driver_by_cell_branch: dict[tuple[str, str], dict[str, Any]] = {}
    for driver in drivers:
        for name in driver["cells"]:
            driver_by_cell_branch[(name, driver["branch"])] = driver
    cell_records: list[dict[str, Any]] = []
    instance_lines: list[str] = []
    for row in ROWS:
        for col in COLS:
            name = cell_id(row, col)
            input_nodes = {branch: driver_by_cell_branch[(name, branch)]["node"]
                           for branch in ("WL", "BL", "SE")}
            sl_node = f"SL_{name}"
            qb_node = f"QBOUT_{name}"
            sjtl_node = f"SJTL_OUT_{name}"
            vout = f"VOUT_{name}"
            instances = {"BVM": f"XBVM_{name}", "QB": f"XBQ_{name}",
                         "SJTL": f"XSJTL_{name}", "POST_CB": f"XCB_{name}",
                         "TERMINATION": f"R_TERM_{name}"}
            instance_lines.extend((
                f"{instances['BVM']} {input_nodes['WL']} {input_nodes['BL']} "
                f"{input_nodes['SE']} {sl_node} BVM",
                f"{instances['QB']} {sl_node} {qb_node} BQ",
                f"{instances['SJTL']} {qb_node} {sjtl_node} sJTL",
                f"{instances['POST_CB']} {sjtl_node} {vout} CB",
                f"{instances['TERMINATION']} {vout} 0 {case['TERM_R']}",
            ))
            cell_records.append({
                "cell": name, "row": row, "column": col,
                "row_bit": case["ROW_BITS"][row - 1],
                "column_bit": case["COL_BITS"][col - 1],
                "final_read_wl_enabled": case["ROW_BITS"][row - 1] == "1",
                "final_read_se_enabled": _final_read_se_enabled(case, row, col),
                "final_read_crosspoint_active": cell_selected(case, row, col),
                "second_read_wl_enabled": (_second_read_enabled(case) and
                                           case["SECOND_ROW_BITS"][row - 1] == "1"),
                "second_read_se_enabled": _second_read_se_enabled(case, row, col),
                "second_read_crosspoint_active": _second_read_se_enabled(case, row, col),
                "input_nodes": input_nodes,
                "sl_node": sl_node, "qb_output_node": qb_node,
                "sjtl_output_node": sjtl_node, "output_node": vout,
                "instances": instances,
                "load_chain": [instances["BVM"], instances["QB"], instances["SJTL"],
                               instances["POST_CB"], instances["TERMINATION"]],
                "source_for_each_input": {
                    branch: driver_by_cell_branch[(name, branch)]["source"]
                    for branch in ("WL", "BL", "SE")
                },
            })

    outputs = [record["output_node"] for record in cell_records]
    if len(outputs) != len(set(outputs)):
        raise ConfigError("cell output nodes are not independent")
    if case["DRIVE_MODE"] == "SHARED":
        se_count = 2 if _effective_se_topology(case) == "SHARED_COLUMN" else 4
        expected_count = 4 + se_count
        nodes = [driver["node"] for driver in drivers]
        if len(nodes) != expected_count or len(nodes) != len(set(nodes)):
            raise ConfigError(f"SHARED requires {expected_count} electrically distinct driver nodes")
        if any(len(driver["cells"]) != 2 for driver in drivers if driver["branch"] in {"WL", "BL"}):
            raise ConfigError("SHARED WL/BL sources must each feed exactly their two row/column cells")
        se_drivers = [driver for driver in drivers if driver["branch"] == "SE"]
        expected_se_cells = 2 if _effective_se_topology(case) == "SHARED_COLUMN" else 1
        if len(se_drivers) != se_count or any(len(driver["cells"]) != expected_se_cells for driver in se_drivers):
            raise ConfigError("SHARED SE source cardinality disagrees with SE_TOPOLOGY")
    elif len(drivers) != 12 or any(len(driver["cells"]) != 1 for driver in drivers):
        raise ConfigError("INDEPENDENT must have exactly three independent drivers per cell")

    includes = []
    for role in ("JJMIT", "BVM", "QB", "SJTL", "POST_CB"):
        source_path = REPO / SOURCE_PATHS[role]
        includes.append(f".include {Path(os.path.relpath(source_path, run_dir)).as_posix()}")
    deck_lines = [
        "* 2x2 BVM row/column selection platform; no output merging or T1.",
        "* Canonical component sources are direct includes and remain unchanged.",
        *includes,
        "",
        "* One PWL current driver for each independent input line.",
        ".include stimulus.inc",
        "",
        "* BVM.SL -> BQ -> one sJTL -> one post-CB -> independent VOUT -> R_TERM=2 ohm.",
        "* FINAL READ has zero BL drive.",
        *instance_lines,
    ]
    shared_nodes = {}
    if case["DRIVE_MODE"] == "SHARED":
        shared_nodes = {
            "WL": {f"ROW{row}": f"WL_R{row}" for row in ROWS},
            "BL": {f"COL{col}": f"BL_C{col}" for col in COLS},
        }
        if _effective_se_topology(case) == "SHARED_COLUMN":
            shared_nodes["SE"] = {f"COL{col}": f"SE_C{col}" for col in COLS}
    selective_write_events = []
    if case["WRITE1_MODE"] == "SEQUENTIAL_CROSSPOINT":
        for slot in ("1", "2"):
            target = case[f"WRITE1_TARGET_{slot}"]
            target_row, target_col = int(target[1]), int(target[3])
            target_cell_ids = [cell_id(target_row, target_col)]
            row_only = [cell_id(target_row, col) for col in COLS if col != target_col]
            column_only = [cell_id(row, target_col) for row in ROWS if row != target_row]
            neither = [cell_id(row, col) for row in ROWS for col in COLS
                       if row != target_row and col != target_col]
            start, rise, hold, fall = _stage_timing(f"WRITE1_TARGET_{slot}", stimulus)
            selective_write_events.append({
                "stage": f"WRITE1_TARGET_{slot}", "target_cell": target,
                "start_seconds": str(start), "end_seconds": str(start + rise + hold + fall),
                "row_wl_node": f"WL_R{target_row}", "column_bl_node": f"BL_C{target_col}",
                "target_crosspoint_cells": target_cell_ids,
                "wl_only_cells": row_only, "bl_only_cells": column_only,
                "unselected_cells": neither,
                "driver_topology": "two shared row-WL plus two shared column-BL buses",
            })
    topology = {
        "schema": "bvm-2x2-rowcol-topology-v1",
        "drive_mode": case["DRIVE_MODE"],
        "se_configuration": {
            "configured_topology": case["SE_TOPOLOGY"],
            "effective_topology": _effective_se_topology(case),
            "gate_mode": case["SE_GATE_MODE"],
            "shared_column_nodes": ({f"COL{col}": f"SE_C{col}" for col in COLS}
                                    if case["DRIVE_MODE"] == "SHARED" and
                                    _effective_se_topology(case) == "SHARED_COLUMN" else {}),
            "cell_nodes": {cell["cell"]: cell["input_nodes"]["SE"] for cell in cell_records},
            "final_read_enabled_by_cell": {
                cell["cell"]: cell["final_read_se_enabled"] for cell in cell_records},
        },
        "grid": {"rows": 2, "columns": 2,
                 "row_bits": case["ROW_BITS"], "column_bits": case["COL_BITS"],
                 "row_bit_order": "leftmost bit selects row 1; rightmost selects row 2",
                 "column_bit_order": "leftmost bit selects column 1; rightmost selects column 2"},
        "cell_selection": cell_selection_groups(case),
        "write1_sequence": {
            "mode": case["WRITE1_MODE"],
            "read0_enabled": case["READ0_ENABLE"] == "1",
            "events": selective_write_events,
        },
        "second_read": {
            "enabled": _second_read_enabled(case),
            "row_bits": case["SECOND_ROW_BITS"],
            "column_bits": case["SECOND_COL_BITS"],
            "se_gate_mode": "CELL_CROSSPOINT" if _second_read_enabled(case) else "DISABLED",
            "active_crosspoints": [
                cell["cell"] for cell in cell_records if cell["second_read_crosspoint_active"]],
            "enabled_by_cell": {
                cell["cell"]: cell["second_read_se_enabled"] for cell in cell_records},
        },
        "shared_nodes": shared_nodes,
        "input_lines": drivers,
        "driver_count": len(drivers),
        "driver_count_by_branch": {branch: sum(item["branch"] == branch for item in drivers)
                                   for branch in ("WL", "BL", "SE")},
        "cell_instances": cell_records,
        "output_nodes": outputs,
        "four_outputs_independent": True,
        "output_merge": False,
        "t1_instance_count": 0,
        "uniform_load": {"sJTL_per_cell": 1, "post_cb_per_cell": 1,
                         "termination_ohm": case["TERM_R"]},
        "source_sha256": {role: item["sha256"] for role, item in sources.items()},
    }
    probes = make_probe_manifest(case, topology)
    deck_lines.extend((
        "", "* Registered raw probes.",
        *[f".print {entry['label']}" for entry in probes["signals"]],
        f".tran {case['DT']} {case['STOP']}",
        ".end",
    ))
    static_qa = static_validate(case, topology, deck_lines, drive_lines, probes, driver_stages)
    deck = "\n".join(deck_lines) + "\n"
    return {"deck": deck, "topology": topology, "probes": probes,
            "sources": sources, "drivers": drivers, "driver_points": driver_points,
            "driver_stages": driver_stages, "stimulus_text": stimulus_text,
            "drive_lines": drive_lines, "cell_records": cell_records,
            "static_qa": static_qa}


def make_probe_manifest(case: dict[str, str], topology: dict[str, Any]) -> dict[str, Any]:
    signals: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add(label: str, group: str, unit: str, **meta: Any) -> None:
        if label in seen:
            return
        seen.add(label)
        signals.append({"label": label, "group": group, "unit": unit, **meta})

    for driver in topology["input_lines"]:
        add(f"I({driver['source']})", f"drive:{driver['branch']}", "A",
            element=driver["source"], node=driver["node"], cells=driver["cells"])
        add(f"V({driver['node']})", f"drive:{driver['branch']}", "V",
            node=driver["node"], cells=driver["cells"])

    for cell in topology["cell_instances"]:
        name, inst = cell["cell"], cell["instances"]
        for branch, element in (("WL", "R_WL"), ("BL", "R_BL"), ("SE", "R_SE")):
            add(f"I({element}|{inst['BVM']})", f"cell:{name}:input", "A",
                instance=inst["BVM"], element=element, branch=branch)
        add(f"V({cell['sl_node']})", f"cell:{name}:bvm_output", "V", node=cell["sl_node"])
        add(f"I(L_SL|{inst['BVM']})", f"cell:{name}:bvm_output", "A",
            instance=inst["BVM"], element="L_SL")
        for jj in CELL_JJS:
            for quantity_name, unit in (("P", "rad"), ("V", "V")):
                add(f"{quantity_name}({jj}|{inst['BVM']})", f"cell:{name}:bvm_state", unit,
                    instance=inst["BVM"], element=jj)
        for jj in QB_JJS:
            for quantity_name, unit in (("P", "rad"), ("V", "V")):
                add(f"{quantity_name}({jj}|{inst['QB']})", f"cell:{name}:qb", unit,
                    instance=inst["QB"], element=jj)
        add(f"I(LIN|{inst['QB']})", f"cell:{name}:qb", "A",
            instance=inst["QB"], element="Lin")
        add(f"I(IB2|{inst['QB']})", f"cell:{name}:qb", "A",
            instance=inst["QB"], element="IB2")
        add(f"V({cell['qb_output_node']})", f"cell:{name}:qb_boundary", "V",
            node=cell["qb_output_node"])
        for jj in SJTL_JJS:
            for quantity_name, unit in (("P", "rad"), ("V", "V")):
                add(f"{quantity_name}({jj}|{inst['SJTL']})", f"cell:{name}:sjtl", unit,
                    instance=inst["SJTL"], element=jj)
        add(f"I(IB1|{inst['SJTL']})", f"cell:{name}:sjtl", "A",
            instance=inst["SJTL"], element="IB1")
        add(f"V({cell['sjtl_output_node']})", f"cell:{name}:sjtl_boundary", "V",
            node=cell["sjtl_output_node"])
        for jj in CB_JJS:
            for quantity_name, unit in (("P", "rad"), ("V", "V")):
                add(f"{quantity_name}({jj}|{inst['POST_CB']})", f"cell:{name}:post_cb", unit,
                    instance=inst["POST_CB"], element=jj)
        add(f"I(IB1|{inst['POST_CB']})", f"cell:{name}:post_cb", "A",
            instance=inst["POST_CB"], element="IB1")
        add(f"V({cell['output_node']})", f"cell:{name}:output", "V", node=cell["output_node"])
        add(f"I({inst['TERMINATION']})", f"cell:{name}:output", "A",
            element=inst["TERMINATION"])

        if case["PROBE_PROFILE"] == "debug":
            for role_key in ("BVM", "QB", "SJTL", "POST_CB"):
                instance = inst[role_key]
                role = "POST_CB" if role_key == "POST_CB" else role_key
                for element in source_elements(role):
                    prefix = element[0].upper()
                    if prefix == "B":
                        add(f"I({element}|{instance})", f"cell:{name}:{role_key}:debug", "A",
                            instance=instance, element=element)
                    elif prefix == "I":
                        add(f"I({element}|{instance})", f"cell:{name}:{role_key}:debug", "A",
                            instance=instance, element=element)
                    elif prefix in {"L", "R"}:
                        for quantity_name, unit in (("I", "A"), ("V", "V")):
                            add(f"{quantity_name}({element}|{instance})",
                                f"cell:{name}:{role_key}:debug", unit,
                                instance=instance, element=element)

    return {
        "schema": "bvm-2x2-rowcol-probes-v1",
        "profile": case["PROBE_PROFILE"],
        "drive_mode": case["DRIVE_MODE"],
        "se_topology": case["SE_TOPOLOGY"],
        "effective_se_topology": _effective_se_topology(case),
        "se_gate_mode": case["SE_GATE_MODE"],
        "read0_enabled": case["READ0_ENABLE"],
        "write1_mode": case["WRITE1_MODE"],
        "write1_target_1": case["WRITE1_TARGET_1"],
        "write1_target_2": case["WRITE1_TARGET_2"],
        "second_read_enabled": case["SECOND_READ_ENABLE"],
        "second_row_bits": case["SECOND_ROW_BITS"],
        "second_column_bits": case["SECOND_COL_BITS"],
        "second_read_se_gate_mode": "CELL_CROSSPOINT" if _second_read_enabled(case) else "DISABLED",
        "row_bits": case["ROW_BITS"], "column_bits": case["COL_BITS"],
        "active_crosspoints": topology["cell_selection"]["active_crosspoints"],
        "half_selected": topology["cell_selection"]["half_selected"],
        "unselected": topology["cell_selection"]["unselected"],
        "signals": signals,
        "signal_count": len(signals),
        "raw_phase_unit": "P(...) radians",
        "display_phase_unit": "turns = radians/(2*pi); navigation only, not an SFQ count",
        "scientific_interpretation_performed": False,
    }


def static_validate(case: dict[str, str], topology: dict[str, Any], deck_lines: list[str],
                    drive_lines: list[str], probes: dict[str, Any],
                    driver_stages: dict[str, dict[str, str]]) -> dict[str, Any]:
    cell_records = topology["cell_instances"]
    for role, prefix, count in (("BVM", "XBVM_", 4), ("QB", "XBQ_", 4),
                                ("SJTL", "XSJTL_", 4), ("POST_CB", "XCB_", 4),
                                ("TERMINATION", "R_TERM_", 4)):
        found = [cell["instances"][role] for cell in cell_records
                 if cell["instances"][role].startswith(prefix)]
        if len(found) != count or len(found) != len(set(found)):
            raise ConfigError(f"expected four unique {role} instances, found {found}")
    deck = "\n".join(deck_lines)
    instance_lines = [line for line in deck_lines if line.startswith(("XBVM_", "XBQ_", "XSJTL_", "XCB_"))]
    if len(instance_lines) != 16:
        raise ConfigError(f"expected 16 subcircuit instances, found {len(instance_lines)}")
    if any("MERGE" in line.upper() or "XT1" in line.upper() for line in instance_lines):
        raise ConfigError("output merge or T1 instance is prohibited")
    outputs = [cell["output_node"] for cell in cell_records]
    if len(outputs) != 4 or len(set(outputs)) != 4:
        raise ConfigError("all four cell outputs must be independent")
    drivers = topology["input_lines"]
    expected_by_branch = ({"WL": 2, "BL": 2,
                           "SE": 2 if _effective_se_topology(case) == "SHARED_COLUMN" else 4}
                          if case["DRIVE_MODE"] == "SHARED"
                          else {"WL": 4, "BL": 4, "SE": 4})
    expected_count = sum(expected_by_branch.values())
    if topology["driver_count"] != expected_count:
        raise ConfigError(f"{case['DRIVE_MODE']} needs {expected_count} drivers, got {topology['driver_count']}")
    actual_by_branch = {branch: sum(driver["branch"] == branch for driver in drivers)
                        for branch in ("WL", "BL", "SE")}
    if actual_by_branch != expected_by_branch or topology["driver_count_by_branch"] != expected_by_branch:
        raise ConfigError(f"driver counts {actual_by_branch} do not match expected {expected_by_branch}")
    all_driver_nodes = [driver["node"] for driver in drivers]
    if len(all_driver_nodes) != len(set(all_driver_nodes)):
        raise ConfigError("input current sources must terminate on distinct source nodes")
    if case["DRIVE_MODE"] == "SHARED":
        for branch in ("WL", "BL"):
            branch_drivers = [driver for driver in drivers if driver["branch"] == branch]
            if len(branch_drivers) != 2 or any(len(driver["cells"]) != 2 for driver in branch_drivers):
                raise ConfigError(f"SHARED {branch} must contain exactly two buses with two cells each")
        wl_nodes = {item["node"] for item in drivers if item["branch"] == "WL"}
        bl_nodes = {item["node"] for item in drivers if item["branch"] == "BL"}
        se_nodes = {item["node"] for item in drivers if item["branch"] == "SE"}
        if wl_nodes & bl_nodes or wl_nodes & se_nodes or bl_nodes & se_nodes:
            raise ConfigError("WL, BL, and SE buses must be electrically distinct")
        if _effective_se_topology(case) == "SHARED_COLUMN":
            for col in COLS:
                record = next(item for item in drivers
                              if item["branch"] == "SE" and item["line"] == f"COL{col}")
                if set(record["cells"]) != {cell_id(row, col) for row in ROWS}:
                    raise ConfigError(f"shared column SE{col} does not attach to exactly its two cells")
        else:
            se_by_cell = {driver["cells"][0]: driver for driver in drivers if driver["branch"] == "SE"}
            if set(se_by_cell) != {cell_id(row, col) for row in ROWS for col in COLS}:
                raise ConfigError("CELL SE topology must have one driver and node per BVM")
            if len(se_nodes) != 4 or any(driver["node"] != f"SE_{name}"
                                         for name, driver in se_by_cell.items()):
                raise ConfigError("CELL SE nodes are not four separate cell-specific electrical nodes")
    else:
        if any(len(driver["cells"]) != 1 for driver in drivers):
            raise ConfigError("INDEPENDENT sources may feed only one cell input each")
    source_names = [driver["source"] for driver in drivers]
    if len(source_names) != len(set(source_names)):
        raise ConfigError("driver source names are not unique")
    generated_driver_lines = [line for line in drive_lines if line.startswith("I_")]
    if len(generated_driver_lines) != expected_count:
        raise ConfigError(f"deck contains {len(generated_driver_lines)} driver sources, expected {expected_count}")
    rendered_source_nodes: dict[str, str] = {}
    for line in generated_driver_lines:
        fields = line.split(maxsplit=3)
        if len(fields) != 4 or fields[1] != "0" or not fields[3].startswith("PWL("):
            raise ConfigError(f"malformed generated current source line: {line}")
        if fields[0] in rendered_source_nodes:
            raise ConfigError(f"duplicate generated source {fields[0]}")
        rendered_source_nodes[fields[0]] = fields[2]
    expected_source_nodes = {driver["source"]: driver["node"] for driver in drivers}
    if rendered_source_nodes != expected_source_nodes:
        raise ConfigError("rendered PWL source endpoints do not match topology input_lines")
    source_records = {driver["source"]: driver for driver in drivers}
    for cell in cell_records:
        name, row, col = cell["cell"], cell["row"], cell["column"]
        expected_values = {
            "WL": {"WRITE0": f"-{case['ROW_WL_WRITE_AMPLITUDE']}",
                   "FINAL_READ": case["ROW_WL_READ_AMPLITUDE"] if case["ROW_BITS"][row - 1] == "1" else "0"},
            "BL": {"WRITE0": f"-{case['COL_BL_WRITE_AMPLITUDE']}", "FINAL_READ": "0"},
            "SE": {"WRITE0": "0", "FINAL_READ": case["COL_SE_READ_AMPLITUDE"]
                   if _final_read_se_enabled(case, row, col) else "0"},
        }
        if case["READ0_ENABLE"] == "1":
            expected_values["WL"]["READ0"] = case["ROW_WL_READ_AMPLITUDE"]
            expected_values["BL"]["READ0"] = "0"
            expected_values["SE"]["READ0"] = case["COL_SE_READ_AMPLITUDE"]
        if case["WRITE1_MODE"] == "SIMULTANEOUS":
            expected_values["WL"]["WRITE1"] = case["ROW_WL_WRITE_AMPLITUDE"]
            expected_values["BL"]["WRITE1"] = case["COL_BL_WRITE_AMPLITUDE"]
            expected_values["SE"]["WRITE1"] = "0"
        else:
            for slot in ("1", "2"):
                target = case[f"WRITE1_TARGET_{slot}"]
                target_row, target_col = int(target[1]), int(target[3])
                expected_values["WL"][f"WRITE1_TARGET_{slot}"] = (
                    case["ROW_WL_WRITE_AMPLITUDE"] if row == target_row else "0")
                expected_values["BL"][f"WRITE1_TARGET_{slot}"] = (
                    case["COL_BL_WRITE_AMPLITUDE"] if col == target_col else "0")
                expected_values["SE"][f"WRITE1_TARGET_{slot}"] = "0"
        if _second_read_enabled(case):
            expected_values["WL"]["SECOND_READ"] = (
                case["ROW_WL_READ_AMPLITUDE"]
                if case["SECOND_ROW_BITS"][row - 1] == "1" else "0")
            expected_values["BL"]["SECOND_READ"] = "0"
            expected_values["SE"]["SECOND_READ"] = (
                case["COL_SE_READ_AMPLITUDE"]
                if _second_read_se_enabled(case, row, col) else "0")
        for branch, expected in expected_values.items():
            source = cell["source_for_each_input"][branch]
            if source not in source_records or source not in driver_stages:
                raise ConfigError(f"{name}: {branch} input is not driven by a registered source")
            record = source_records[source]
            if name not in record["cells"] or cell["input_nodes"][branch] != record["node"]:
                raise ConfigError(f"{name}: {branch} connection is not backed by its registered source")
            if driver_stages[source] != expected:
                raise ConfigError(f"{name}: {branch} stage waveform disagrees with row/column mapping")
    second_read_stage_present = all("SECOND_READ" in values for values in driver_stages.values())
    if second_read_stage_present != _second_read_enabled(case):
        raise ConfigError("SECOND_READ PWL presence disagrees with SECOND_READ_ENABLE")
    selective_stages = {"WRITE1_TARGET_1", "WRITE1_TARGET_2"}
    selective_present = all(selective_stages.issubset(values) for values in driver_stages.values())
    if selective_present != (case["WRITE1_MODE"] == "SEQUENTIAL_CROSSPOINT"):
        raise ConfigError("selective WRITE1 PWL stages disagree with WRITE1_MODE")
    read0_present = all("READ0" in values for values in driver_stages.values())
    if read0_present != (case["READ0_ENABLE"] == "1"):
        raise ConfigError("READ0 PWL presence disagrees with READ0_ENABLE")
    if case["DRIVE_MODE"] == "SHARED":
        for row in ROWS:
            record = next(item for item in drivers if item["source"] == f"I_WL_R{row}")
            if set(record["cells"]) != {cell_id(row, col) for col in COLS}:
                raise ConfigError(f"shared row WL{row} does not attach to exactly its two cells")
        for col in COLS:
            record = next(item for item in drivers
                          if item["branch"] == "BL" and item["line"] == f"COL{col}")
            if set(record["cells"]) != {cell_id(row, col) for row in ROWS}:
                raise ConfigError(f"shared column BL{col} does not attach to exactly its two cells")
    probe_labels = [item["label"] for item in probes["signals"]]
    if len(probe_labels) != len(set(probe_labels)) or probes["signal_count"] != len(probe_labels):
        raise ConfigError("probe manifest contains duplicates or inconsistent signal_count")
    required_substrings = (
        "BVM.SL -> BQ -> one sJTL -> one post-CB",
        "FINAL READ has zero BL drive",
    )
    if not all(item in deck for item in required_substrings):
        raise ConfigError("deck is missing its output-load or final-read boundary declaration")
    printed = {line.split(None, 1)[1] for line in deck_lines if line.startswith(".print ")}
    if printed != set(probe_labels):
        raise ConfigError("deck .print probes do not match probe_manifest signals exactly")
    for cell in cell_records:
        expected_instances = (
            f"{cell['instances']['BVM']} {cell['input_nodes']['WL']} {cell['input_nodes']['BL']} "
            f"{cell['input_nodes']['SE']} {cell['sl_node']} BVM",
            f"{cell['instances']['QB']} {cell['sl_node']} {cell['qb_output_node']} BQ",
            f"{cell['instances']['SJTL']} {cell['qb_output_node']} {cell['sjtl_output_node']} sJTL",
            f"{cell['instances']['POST_CB']} {cell['sjtl_output_node']} {cell['output_node']} CB",
            f"{cell['instances']['TERMINATION']} {cell['output_node']} 0 {case['TERM_R']}",
        )
        if any(line not in deck_lines for line in expected_instances):
            raise ConfigError(f"{cell['cell']}: rendered port wiring/load chain differs from topology manifest")
    branch_by_source = {driver["source"]: driver["branch"] for driver in topology["input_lines"]}
    if any(stages.get("FINAL_READ") != "0" for source, stages in driver_stages.items()
           if branch_by_source[source] == "BL"):
        raise ConfigError("BL must be zero during FINAL READ for every independent driver")
    if _second_read_enabled(case) and any(
            stages.get("SECOND_READ") != "0" for source, stages in driver_stages.items()
            if branch_by_source[source] == "BL"):
        raise ConfigError("BL must be zero during SECOND_READ for every independent driver")
    if set(cell["cell"] for cell in cell_records) != {"R1C1", "R1C2", "R2C1", "R2C2"}:
        raise ConfigError("cell grid identity is incomplete")
    return {
        "schema": "bvm-2x2-rowcol-static-qa-v1", "status": "PASS",
        "physical_solve_count": 0,
        "canonical_source_hashes_match": True,
        "source_pin_orders_match": {role: list(parse_subckt(role))
                                    for role in ("BVM", "QB", "SJTL", "POST_CB")},
        "drive_mode": case["DRIVE_MODE"],
        "source_count_by_branch": topology["driver_count_by_branch"],
        "driver_source_node_map_matches": True,
        "four_cell_load_chains_match": True,
        "four_outputs_unique": len(set(outputs)) == 4,
        "row_column_bit_mapping_match": True,
        "se_topology": case["SE_TOPOLOGY"],
        "effective_se_topology": _effective_se_topology(case),
        "se_gate_mode": case["SE_GATE_MODE"],
        "read0_enabled": case["READ0_ENABLE"] == "1",
        "write1_mode": case["WRITE1_MODE"],
        "selective_write_targets": ([case["WRITE1_TARGET_1"], case["WRITE1_TARGET_2"]]
                                     if case["WRITE1_MODE"] == "SEQUENTIAL_CROSSPOINT" else []),
        "selective_write_keeps_shared_wl_bl": case["WRITE1_MODE"] != "SEQUENTIAL_CROSSPOINT" or (
            case["DRIVE_MODE"] == "SHARED" and len([d for d in drivers if d["branch"] == "WL"]) == 2
            and len([d for d in drivers if d["branch"] == "BL"]) == 2),
        "cell_se_nodes_independent": len({cell["input_nodes"]["SE"] for cell in cell_records}) == 4,
        "final_read_bl_zero": True,
        "second_read_enabled": _second_read_enabled(case),
        "second_read_row_bits": case["SECOND_ROW_BITS"],
        "second_read_column_bits": case["SECOND_COL_BITS"],
        "second_read_se_gate_mode": "CELL_CROSSPOINT" if _second_read_enabled(case) else "DISABLED",
        "second_read_crosspoint_gate_exact": (
            not _second_read_enabled(case) or
            topology["second_read"]["enabled_by_cell"] == {
                cell["cell"]: (case["SECOND_ROW_BITS"][cell["row"] - 1] == "1" and
                               case["SECOND_COL_BITS"][cell["column"] - 1] == "1")
                for cell in cell_records}),
        "second_read_bl_zero": (not _second_read_enabled(case) or all(
            values.get("SECOND_READ") == "0" for source, values in driver_stages.items()
            if branch_by_source[source] == "BL")),
        "deck_print_set_matches_probe_manifest": True,
        "t1_count": 0, "output_merge": False,
        "scientific_interpretation_performed": False,
    }


def _stable_env(values: dict[str, str]) -> str:
    return "".join(f"{key}={values[key]}\n" for key in sorted(values))


def next_run_path(case: dict[str, str]) -> tuple[str, Path]:
    existing = []
    for path in RUNS.iterdir() if RUNS.is_dir() else ():
        match = re.match(r"A(\d{3})_", path.name)
        if match:
            existing.append(int(match.group(1)))
    index = max(existing, default=0) + 1
    run_id = f"A{index:03d}_{case['DRIVE_MODE']}_R{case['ROW_BITS']}_C{case['COL_BITS']}"
    return run_id, RUNS / run_id


def source_manifest(records: dict[str, dict[str, str]]) -> dict[str, Any]:
    return {"schema": "bvm-2x2-rowcol-sources-v1", "sources": [
        {"role": role, **records[role]} for role in ("JJMIT", "BVM", "QB", "SJTL", "POST_CB")
    ], "canonical_sources_modified": False, "scientific_interpretation_performed": False}


def parameter_manifest(case: dict[str, str], stimulus: dict[str, str], records: dict[str, dict[str, str]]) -> dict[str, Any]:
    return {
        "schema": "bvm-2x2-rowcol-parameters-v1",
        "drive_mode": case["DRIVE_MODE"],
        "USER_CASE": dict(case), "STIMULUS": dict(stimulus),
        "second_read": {
            "enabled": _second_read_enabled(case),
            "row_bits": case["SECOND_ROW_BITS"],
            "column_bits": case["SECOND_COL_BITS"],
            "se_gate_mode": "CELL_CROSSPOINT" if _second_read_enabled(case) else "DISABLED",
        },
        "component_source_sha256": {role: record["sha256"] for role, record in records.items()},
        "frozen_output_load": {"SJTL_PER_CELL": 1, "POST_CB_PER_CELL": 1,
                               "TERM_R_OHM": case["TERM_R"]},
        "bit_order": {"rows": "leftmost bit is R1", "columns": "leftmost bit is C1"},
        "physical_solve_count": 1,
        "scientific_interpretation_performed": False,
    }


def _run_config_identity(case: dict[str, str]) -> dict[str, str]:
    return {
        "drive_mode": case["DRIVE_MODE"],
        "se_topology": case["SE_TOPOLOGY"],
        "effective_se_topology": _effective_se_topology(case),
        "se_gate_mode": case["SE_GATE_MODE"],
        "read0_enabled": case["READ0_ENABLE"],
        "write1_mode": case["WRITE1_MODE"],
        "write1_target_1": case["WRITE1_TARGET_1"],
        "write1_target_2": case["WRITE1_TARGET_2"],
        "second_read_enabled": case["SECOND_READ_ENABLE"],
        "second_row_bits": case["SECOND_ROW_BITS"],
        "second_column_bits": case["SECOND_COL_BITS"],
        "second_read_se_gate_mode": "CELL_CROSSPOINT" if _second_read_enabled(case) else "DISABLED",
        "row_bits": case["ROW_BITS"],
        "column_bits": case["COL_BITS"],
    }


def write_run_preflight(run_dir: Path, run_id: str, case: dict[str, str],
                        stimulus: dict[str, str], rendered: dict[str, Any],
                        solver_info: dict[str, Any]) -> str:
    lines = [
        "# 2×2 BVM row/column run preflight", "",
        "This experiment is governed by docs/EXPERIMENT_CONTRACT.md.", "",
        f"- Parent HEAD: `{solver_info['parent_head']}`",
        f"- Run ID: `{run_id}`; exactly one solver invocation is planned.",
        f"- Solver: `{solver_info['path']}`; version `{solver_info['version']}`; SHA-256 `{solver_info['sha256']}`.",
        f"- Deck SHA-256: `{sha256(run_dir / 'deck.cir')}`; stimulus.inc SHA-256: `{sha256(run_dir / 'stimulus.inc')}`.",
        f"- Parameter/topology/probe manifest SHA-256: `{sha256(run_dir / 'parameter_manifest.json')}` / "
        f"`{sha256(run_dir / 'topology_manifest.json')}` / `{sha256(run_dir / 'probe_manifest.json')}`.",
        f"- Drive mode: `{case['DRIVE_MODE']}`; ROW_BITS=`{case['ROW_BITS']}`; COL_BITS=`{case['COL_BITS']}`.",
        f"- SE topology: configured `{case['SE_TOPOLOGY']}`, effective `{_effective_se_topology(case)}`; gate `{case['SE_GATE_MODE']}`.",
        "- Leftmost row bit is row 1; leftmost column bit is column 1.",
        f"- Active crosspoints: `{', '.join(rendered['topology']['cell_selection']['active_crosspoints']) or 'none'}`.",
        f"- Half-selected cells: `{', '.join(rendered['topology']['cell_selection']['half_selected']) or 'none'}`.",
        f"- Unselected cells: `{', '.join(rendered['topology']['cell_selection']['unselected']) or 'none'}`.",
        f"- READ0_ENABLE=`{case['READ0_ENABLE']}`; WRITE1_MODE=`{case['WRITE1_MODE']}`.",
        "- Row/column bits gate FINAL READ only; they do not implement mixed storage by themselves.",
        "- FINAL READ BL sources are zero. CELL/CROSSPOINT SE is independently enabled only where both row and column bits are active.",
        "- Load per cell: BVM → canonical QB → one canonical sJTL → one canonical CB → separate VOUT → 2 Ω.",
        "- SHARED drive uses two shared row-WL sources, two shared column-BL sources, and either two shared-column or four cell-local SE sources.",
        "- Shared 200 µA and independent 100 µA are candidate drive settings, not assumed equivalent.",
        f"- SECOND_READ: enabled={_second_read_enabled(case)}; row bits=`{case['SECOND_ROW_BITS']}`; "
        f"column bits=`{case['SECOND_COL_BITS']}`; SE gate is fixed to CELL_CROSSPOINT.",
        f"- DT=`{case['DT']}`, STOP=`{case['STOP']}`; P(...) raw unit is radians.",
        "- Registered half-open windows and read/recovery windows are listed in stimulus_qa.json and cell_metrics.json.",
        "- Branch-current analysis reports raw extrema/actual-grid charge only; no decision threshold is registered.",
        "- Only the registered run is authorized; no sweep, follow-up, T1, output merge, or 4×4 extension.",
        "- Interpretation ceiling: artifact/mechanical QA and registered arithmetic only.",
        "", "## Canonical source hashes", "",
    ]
    if case["WRITE1_MODE"] == "SEQUENTIAL_CROSSPOINT":
        lines.extend((
            f"- Selective WRITE1 targets: `{case['WRITE1_TARGET_1']}` then `{case['WRITE1_TARGET_2']}`.",
            "- Each target pulse drives its shared row WL and shared column BL; all row-only, column-only, and unselected cells remain exposed to those bus waveforms and are probed.",
            "- No per-cell WL/BL sources are introduced; source count remains 8 (2 WL + 2 BL + 4 SE).",
        ))
        for event in rendered["topology"]["write1_sequence"]["events"]:
            lines.append(f"- {event['stage']}: [{fmt_time(Decimal(event['start_seconds']))}, "
                         f"{fmt_time(Decimal(event['end_seconds']))}); target={event['target_cell']}; "
                         f"WL-only={','.join(event['wl_only_cells'])}; "
                         f"BL-only={','.join(event['bl_only_cells'])}; "
                         f"unselected={','.join(event['unselected_cells'])}.")
    if not _second_read_enabled(case):
        windows = _stage_windows(case, stimulus)
        start, end = windows["READ_RESPONSE"]
        lines.append(f"- Full read response window: [{fmt_time(start)}, {fmt_time(end)}) using stored-grid samples.")
    if _second_read_enabled(case):
        for window_name in ("FINAL_READ", "RECOVERY_BEFORE_SECOND_READ", "SECOND_READ",
                            "POST_SECOND_READ"):
            start, end = _stage_windows(case, stimulus)[window_name]
            lines.insert(-2, f"- {window_name}: [{fmt_time(start)}, {fmt_time(end)}) using stored-grid samples.")
    for role, source in rendered["sources"].items():
        lines.append(f"- {role}: `{source['path']}` SHA-256 `{source['sha256']}`")
    lines.extend(("", "## Registered probes", ""))
    lines.extend(f"- `{entry['label']}` — {entry['unit']} — {entry['group']}"
                 for entry in rendered["probes"]["signals"])
    lines.extend(("", "## Required run artifacts", "",
                  "`deck.cir`, `raw.csv`, `run.log`, `stdout.txt`, `stderr.txt`, snapshots, topology/source/probe/parameter manifests,",
                  "static_qa.json, raw_qa.json, stimulus_qa.json, cell_metrics.json, plot_manifest.json, plot_qa.json, RESULT_BRIEF.md.", ""))
    return "\n".join(lines)


def _cell_jj(role: str, cell: dict[str, Any]) -> list[str]:
    instance = cell["instances"][role]
    jjs = {"BVM": CELL_JJS, "QB": QB_JJS, "SJTL": SJTL_JJS, "POST_CB": CB_JJS}[role]
    return [f"{quantity_name}({jj}|{instance})" for jj in jjs for quantity_name in ("P", "V")]


def plot_page_plan(topology: dict[str, Any], probes: dict[str, Any]) -> list[dict[str, Any]]:
    available = {entry["label"] for entry in probes["signals"]}
    drive_labels = [entry["label"] for entry in probes["signals"]
                    if entry["group"].startswith("drive:")
                    or entry["group"].endswith(":input")]
    outputs = [f"V({cell['output_node']})" for cell in topology["cell_instances"]]
    page_plan: list[dict[str, Any]] = [
        {"file": "01_outputs.html", "title": "Four independent cell outputs",
         "signals": outputs + [f"V({cell['qb_output_node']})" for cell in topology["cell_instances"]]},
        {"file": "02_drive_currents.html", "title": "Line drivers and per-cell input branch currents",
         "signals": drive_labels},
    ]
    for cell in topology["cell_instances"]:
        name = cell["cell"]
        signals = [
            f"P(B_JM1|{cell['instances']['BVM']})", f"V(B_JM1|{cell['instances']['BVM']})",
            f"P(B_JM2|{cell['instances']['BVM']})", f"V(B_JM2|{cell['instances']['BVM']})",
            f"P(B_JS1|{cell['instances']['BVM']})", f"V(B_JS1|{cell['instances']['BVM']})",
            f"P(B_JS2|{cell['instances']['BVM']})", f"V(B_JS2|{cell['instances']['BVM']})",
            f"V({cell['sl_node']})", f"V({cell['qb_output_node']})",
            *_cell_jj("QB", cell), *_cell_jj("SJTL", cell), *_cell_jj("POST_CB", cell),
            f"V({cell['output_node']})",
        ]
        page_plan.append({"file": f"cells/{name}.html", "title": f"Cell {name}: BVM → QB → sJTL → CB",
                          "signals": signals})
    def focused_cell_signals(cell: dict[str, Any]) -> list[str]:
        instance = cell["instances"]
        return [
            f"I(R_WL|{instance['BVM']})", f"I(R_BL|{instance['BVM']})",
            f"I(R_SE|{instance['BVM']})",
            *[signal for jj in CELL_JJS
              for signal in (f"P({jj}|{instance['BVM']})", f"V({jj}|{instance['BVM']})")],
            f"V({cell['sl_node']})", f"V({cell['qb_output_node']})",
            *[signal for jj in QB_JJS
              for signal in (f"P({jj}|{instance['QB']})", f"V({jj}|{instance['QB']})")],
            f"V({cell['sjtl_output_node']})",
            *[signal for jj in SJTL_JJS
              for signal in (f"P({jj}|{instance['SJTL']})", f"V({jj}|{instance['SJTL']})")],
            *[signal for jj in CB_JJS
              for signal in (f"P({jj}|{instance['POST_CB']})", f"V({jj}|{instance['POST_CB']})")],
            f"V({cell['output_node']})",
        ]
    first_window = ("FIRST_READ_RESPONSE" if topology["second_read"]["enabled"]
                    else "READ_RESPONSE")
    for cell in topology["cell_instances"]:
        if cell["final_read_crosspoint_active"]:
            name = cell["cell"]
            page_plan.append({
                "file": f"windows/first_read_response_{name}.html",
                "title": f"First read full response — {name}",
                "signals": focused_cell_signals(cell), "window_name": first_window,
            })
        if topology["second_read"]["enabled"] and cell["second_read_crosspoint_active"]:
            name = cell["cell"]
            page_plan.extend((
                {"file": f"windows/recovery_{name}.html",
                 "title": f"Recovery before second read — {name}",
                 "signals": focused_cell_signals(cell),
                 "window_name": "RECOVERY_BEFORE_SECOND_READ"},
                {"file": f"windows/second_read_response_{name}.html",
                 "title": f"Second read full response — {name}",
                 "signals": focused_cell_signals(cell),
                 "window_name": "SECOND_READ_RESPONSE"},
            ))
    for page in page_plan:
        missing = [label for label in page["signals"] if label not in available]
        if missing:
            raise ConfigError(f"plot page {page['file']} uses unregistered probes: {missing}")
        if not page["signals"]:
            raise ConfigError(f"plot page {page['file']} has no signals")
    return page_plan


def dry_run(case: dict[str, str], stimulus: dict[str, str], *, verbose: bool = False) -> int:
    run_id, candidate_path = next_run_path(case)
    rendered = render(case, stimulus, candidate_path)
    plan = plot_page_plan(rendered["topology"], rendered["probes"])
    groups = rendered["topology"]["cell_selection"]
    row_bits, col_bits = case["ROW_BITS"], case["COL_BITS"]
    if case["DRIVE_MODE"] == "SHARED":
        se_count = 2 if _effective_se_topology(case) == "SHARED_COLUMN" else 4
        driver_label = (f"{4 + se_count} sources (WL/BL/SE = 2/2/{se_count}); "
                        "WL/BL are per-line; SE topology shown below")
    else:
        driver_label = "12 cell sources (WL/BL/SE = 4/4/4); amplitudes are per-cell"
    windows = _stage_windows(case, stimulus)
    times = " | ".join(
        f"{stage} {fmt_decimal(start / Decimal('1e-12'))}–{fmt_decimal(end / Decimal('1e-12'))}ps"
        for stage, (start, end) in windows.items()
        if stage in set(_active_stages(case)) | {
            "RECOVERY_BEFORE_SECOND_READ", "FIRST_READ_RESPONSE",
            "SECOND_READ_RESPONSE", "READ_RESPONSE"}
    )
    print("DRY RUN PASS — no solver call; physical_solve_count=0")
    print(f"Case: {case['NAME']} | next run if executed: {run_id}")
    print(f"Topology: {case['DRIVE_MODE']} | ROW_BITS={row_bits} | COL_BITS={col_bits} "
          "(leftmost bit is index 1)")
    print(f"SE: configured={case['SE_TOPOLOGY']} | effective={_effective_se_topology(case)} "
          f"| gate={case['SE_GATE_MODE']}")
    print("FINAL READ: active=" + ",".join(groups["active_crosspoints"] or ["none"])
          + " | half-selected=" + ",".join(groups["half_selected"] or ["none"])
          + " | off=" + ",".join(groups["unselected"] or ["none"]))
    print(f"Drivers: {driver_label}; write WL/BL={case['ROW_WL_WRITE_AMPLITUDE']}/"
          f"{case['COL_BL_WRITE_AMPLITUDE']}, read WL/SE={case['ROW_WL_READ_AMPLITUDE']}/"
          f"{case['COL_SE_READ_AMPLITUDE']}")
    print("FINAL_READ programmed source values per cell (WL, BL, SE; not measured branch currents):")
    for cell in rendered["cell_records"]:
        values = {branch: rendered["driver_stages"][source]["FINAL_READ"]
                  for branch, source in cell["source_for_each_input"].items()}
        print(f"  {cell['cell']}: {values['WL']}, {values['BL']}, {values['SE']}")
    print(f"Stimulus windows: {times}")
    final_se_gate = "column bits" if case["SE_GATE_MODE"] == "COLUMN" else "row AND column bits"
    read0_text = "; READ0 +WL/+SE" if case["READ0_ENABLE"] == "1" else "; READ0 omitted"
    write1_text = (f"; selective WRITE1 {case['WRITE1_TARGET_1']} then {case['WRITE1_TARGET_2']} "
                   "via shared row-WL/column-BL buses"
                   if case["WRITE1_MODE"] == "SEQUENTIAL_CROSSPOINT"
                   else "; WRITE1 +WL/+BL on all shared lines")
    print("PWL phases: WRITE0 −WL/−BL" + read0_text + write1_text +
          f"; FINAL_READ +WL(row bits)/+SE({final_se_gate}), BL=0")
    if case["WRITE1_MODE"] == "SEQUENTIAL_CROSSPOINT":
        print("Selective WRITE1 programmed source values per cell (WL, BL, SE; not measured branch currents):")
        for stage in ("WRITE1_TARGET_1", "WRITE1_TARGET_2"):
            print(f"  {stage} at {fmt_time(_stage_timing(stage, stimulus)[0])}, target="
                  f"{case[stage]}:")
            for cell in rendered["cell_records"]:
                values = {branch: rendered["driver_stages"][source][stage]
                          for branch, source in cell["source_for_each_input"].items()}
                print(f"    {cell['cell']}: {values['WL']}, {values['BL']}, {values['SE']}")
    if _second_read_enabled(case):
        print(f"SECOND_READ: row bits={case['SECOND_ROW_BITS']}; column bits={case['SECOND_COL_BITS']}; "
              "SE gate=CELL_CROSSPOINT; BL=0")
        print("SECOND_READ programmed source values per cell (WL, BL, SE; not measured branch currents):")
        for cell in rendered["cell_records"]:
            values = {branch: rendered["driver_stages"][source]["SECOND_READ"]
                      for branch, source in cell["source_for_each_input"].items()}
            print(f"  {cell['cell']}: {values['WL']}, {values['BL']}, {values['SE']}")
    if case["DRIVE_MODE"] == "SHARED" and _effective_se_topology(case) == "CELL":
        for driver in rendered["drivers"]:
            if driver["branch"] == "SE":
                print(f"  {driver['source']} → {driver['node']} → {','.join(driver['cells'])}")
    if case["WRITE1_MODE"] == "SIMULTANEOUS":
        print("All four cells receive the same configured preparation/write sequence.")
    else:
        print("Selective write targets share row WL and column BL; half-selected cell inputs are explicitly listed above.")
    print("Output/load: 4 independent chains, BVM→QB→1×sJTL→1×CB→VOUT→2Ω")
    print(f"Solver settings: DT={case['DT']}, STOP={case['STOP']}; planned solves if run=1")
    print(f"Probes: {rendered['probes']['signal_count']} ({case['PROBE_PROFILE']}); "
          f"HTML pages if run={len(plan)}; static QA={rendered['static_qa']['status']}")
    if verbose:
        print("\nVERBOSE: effective USER_CASE")
        print(_stable_env(case), end="")
        print("\nVERBOSE: effective STIMULUS")
        print(_stable_env(stimulus), end="")
        print("\nVERBOSE: parameter/topology/source/probe manifests")
        for title, value in (("PARAMETERS", parameter_manifest(case, stimulus, rendered["sources"])),
                             ("TOPOLOGY", rendered["topology"]),
                             ("SOURCES", source_manifest(rendered["sources"])),
                             ("PROBES", rendered["probes"]),
                             ("STATIC QA", rendered["static_qa"])):
            print(f"\n[{title}]\n" + json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))
        print("\nVERBOSE: exact PWL source lines")
        print(rendered["stimulus_text"], end="")
        print("\nVERBOSE: exact actual deck")
        print(rendered["deck"], end="")
    print("No run directory created.")
    return 0


def _solver_info() -> dict[str, Any]:
    if not SOLVER.is_file():
        raise ConfigError(f"JoSIM executable is missing: {SOLVER}")
    completed = subprocess.run([str(SOLVER), "--version"], cwd=REPO,
                               capture_output=True, text=True, check=True)
    return {"path": str(SOLVER), "version": completed.stdout.strip(),
            "sha256": sha256(SOLVER), "parent_head": _git_head()}


def _git_head() -> str:
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True,
                          text=True, check=True).stdout.strip()


def _stage_windows(case: dict[str, str], stimulus: dict[str, str]) -> dict[str, tuple[Decimal, Decimal]]:
    windows: dict[str, tuple[Decimal, Decimal]] = {}
    for stage in _active_stages(case):
        start, rise, hold, fall = _stage_timing(stage, stimulus)
        duration = rise + hold + fall
        windows[stage] = (start, start + duration)
    active = list(_active_stages(case))
    for previous, current in zip(active, active[1:]):
        windows[f"POST_{previous}"] = (windows[previous][1], windows[current][0])
    if "WRITE1" in windows and "FINAL_READ" in windows:
        windows["POST_WRITE1"] = (windows["WRITE1"][1], windows["FINAL_READ"][0])
    if case["WRITE1_MODE"] == "SEQUENTIAL_CROSSPOINT":
        windows["POST_WRITE1"] = (windows["WRITE1_TARGET_2"][1], windows["FINAL_READ"][0])
    if _second_read_enabled(case):
        second_start, _rise, _hold, _fall = _stage_timing("SECOND_READ", stimulus)
        second_end = windows["SECOND_READ"][1]
        final_start = windows["FINAL_READ"][0]
        windows["RECOVERY_BEFORE_SECOND_READ"] = (windows["FINAL_READ"][1], second_start)
        windows["FIRST_READ_RESPONSE"] = (final_start, second_start)
        windows["SECOND_READ_RESPONSE"] = (second_start, quantity(case["STOP"], "STOP"))
        windows["POST_SECOND_READ"] = (second_end, quantity(case["STOP"], "STOP"))
    else:
        windows["READ_RESPONSE"] = (windows["FINAL_READ"][0], quantity(case["STOP"], "STOP"))
        windows["TAIL"] = (windows["FINAL_READ"][1], quantity(case["STOP"], "STOP"))
    return windows


def exact_raw_times(path: Path) -> tuple[Decimal, ...]:
    result: list[Decimal] = []
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.reader(stream)
        header = next(reader, None)
        if not header or header[0] != "time":
            raise ConfigError("raw CSV must have the exact first header 'time'")
        for row_no, row in enumerate(reader, start=2):
            if not row:
                continue
            try:
                value = Decimal(row[0])
            except (InvalidOperation, IndexError) as exc:
                raise ConfigError(f"invalid raw time value at row {row_no}") from exc
            if not value.is_finite():
                raise ConfigError(f"non-finite raw time value at row {row_no}")
            result.append(value)
    return tuple(result)


def _indices(times: tuple[Decimal, ...], window: tuple[Decimal, Decimal]) -> list[int]:
    start, end = window
    return [index for index, stamp in enumerate(times) if start <= stamp < end]


def _trapz(times: tuple[float, ...], values: tuple[float, ...], indices: list[int]) -> float:
    if len(indices) < 2:
        raise ConfigError("analysis window contains fewer than two stored raw samples")
    return sum((values[left] + values[right]) * 0.5 * (times[right] - times[left])
               for left, right in zip(indices, indices[1:]))


def _unwrap(values: tuple[float, ...]) -> list[float]:
    if not values:
        return []
    result = [values[0]]
    for previous, current in zip(values, values[1:]):
        delta = current - previous
        while delta > math.pi:
            delta -= 2 * math.pi
        while delta < -math.pi:
            delta += 2 * math.pi
        result.append(result[-1] + delta)
    return result


def analyze_raw(raw_path: Path, case: dict[str, str], stimulus: dict[str, str],
                topology: dict[str, Any]) -> dict[str, Any]:
    from bvmtools.raw import read_csv

    trace = read_csv(raw_path)
    if trace.duplicate_columns:
        raise ConfigError(f"raw CSV contains duplicate signal labels: {trace.duplicate_columns}")
    probes = json.loads((raw_path.parent / "probe_manifest.json").read_text(encoding="utf-8"))
    required = {entry["label"] for entry in probes["signals"]}
    missing = sorted(required - set(trace.headers))
    if missing:
        raise ConfigError(f"raw CSV is missing required probes: {missing}")
    exact_times = exact_raw_times(raw_path)
    if len(exact_times) != trace.sample_count:
        raise ConfigError("exact raw time row count disagrees with parsed raw trace")
    windows = _stage_windows(case, stimulus)
    window_manifest = {name: {"start_seconds": str(start), "end_seconds": str(end),
                              "boundary_rule": "[start,end)"}
                       for name, (start, end) in windows.items()}
    currents: list[dict[str, Any]] = []
    for driver in topology["input_lines"]:
        source_signal = f"I({driver['source']})"
        source_values = trace.column(source_signal)
        for stage, window in windows.items():
            indexes = _indices(exact_times, window)
            if len(indexes) < 2:
                continue
            selected = [source_values[index] for index in indexes]
            currents.append({"scope": "driver_source", "source": driver["source"],
                             "branch": driver["branch"], "stage": stage,
                             "cells": driver["cells"], "sample_count": len(indexes),
                             "min_a": min(selected), "max_a": max(selected),
                             "peak_to_peak_a": max(selected) - min(selected),
                             "max_abs_a": max(abs(value) for value in selected),
                             "charge_c": _trapz(trace.time, source_values, indexes)})
    for cell in topology["cell_instances"]:
        bvm = cell["instances"]["BVM"]
        for branch, element in (("WL", "R_WL"), ("BL", "R_BL"), ("SE", "R_SE")):
            signal = f"I({element}|{bvm})"
            values = trace.column(signal)
            for stage, window in windows.items():
                indexes = _indices(exact_times, window)
                if len(indexes) < 2:
                    continue
                selected = [values[index] for index in indexes]
                currents.append({"scope": "bvm_input_branch", "cell": cell["cell"],
                                 "branch": branch, "signal": signal, "stage": stage,
                                 "sample_count": len(indexes), "min_a": min(selected),
                                 "max_a": max(selected), "peak_to_peak_a": max(selected) - min(selected),
                                 "max_abs_a": max(abs(value) for value in selected),
                                 "charge_c": _trapz(trace.time, values, indexes)})

    jj_metrics: list[dict[str, Any]] = []
    for cell in topology["cell_instances"]:
        for role, jjs, voltage_suffix in (("BVM", CELL_JJS, ""), ("QB", QB_JJS, ""),
                                          ("SJTL", SJTL_JJS, ""), ("POST_CB", CB_JJS, "")):
            instance = cell["instances"][role]
            for jj in jjs:
                phase_signal = f"P({jj}|{instance})"
                voltage_signal = f"V({jj}|{instance})"
                phase = _unwrap(trace.column(phase_signal))
                voltage = trace.column(voltage_signal)
                jj_windows = ["FINAL_READ"]
                if case["READ0_ENABLE"] == "1":
                    jj_windows.append("POST_READ0")
                if case["WRITE1_MODE"] == "SIMULTANEOUS":
                    jj_windows.append("POST_WRITE1")
                else:
                    jj_windows.extend(("POST_WRITE0", "WRITE1_TARGET_1",
                                       "POST_WRITE1_TARGET_1", "WRITE1_TARGET_2",
                                       "POST_WRITE1_TARGET_2", "POST_WRITE1"))
                if _second_read_enabled(case):
                    jj_windows.extend(("FIRST_READ_RESPONSE", "RECOVERY_BEFORE_SECOND_READ",
                                       "SECOND_READ", "SECOND_READ_RESPONSE", "POST_SECOND_READ"))
                else:
                    jj_windows.extend(("READ_RESPONSE", "TAIL"))
                for window_name in jj_windows:
                    indexes = _indices(exact_times, windows[window_name])
                    if len(indexes) < 2:
                        continue
                    start, end = indexes[0], indexes[-1]
                    delta_rad = phase[end] - phase[start]
                    area = _trapz(trace.time, voltage, indexes)
                    metric = {
                        "cell": cell["cell"], "role": role, "instance": instance,
                        "junction": jj, "window": window_name,
                        "phase_signal": phase_signal, "voltage_signal": voltage_signal,
                        "first_sample_s": trace.time[start], "last_sample_s": trace.time[end],
                        "phase_delta_rad": delta_rad,
                        "phase_delta_turns_rad_over_2pi": delta_rad / (2 * math.pi),
                        "voltage_area_v_s_same_jj_same_rows": area,
                        "voltage_area_phi0_arithmetic": area / PHI0_VS,
                        "phase_minus_area_turns_arithmetic": delta_rad / (2 * math.pi) - area / PHI0_VS,
                        "sample_count": len(indexes),
                        "interpolation_or_resampling": False,
                    }
                    if _second_read_enabled(case):
                        metric["phase_start_rad"] = phase[start]
                        metric["phase_end_rad"] = phase[end]
                        metric["read_cycle"] = (
                            "FIRST_READ" if window_name == "FINAL_READ" else
                            "SECOND_READ" if window_name == "SECOND_READ" else None)
                    jj_metrics.append(metric)
    outputs: list[dict[str, Any]] = []
    for cell in topology["cell_instances"]:
        output_boundaries = [("BVM_SL", cell["sl_node"]),
                             ("QB_OUT", cell["qb_output_node"]),
                                ("SJTL_OUT", cell["sjtl_output_node"]),
                                ("VOUT", cell["output_node"])]
        for node_role, node in output_boundaries:
            signal = f"V({node})"
            values = trace.column(signal)
            output_windows = ["FINAL_READ"]
            if case["READ0_ENABLE"] == "1":
                output_windows.append("POST_READ0")
            if case["WRITE1_MODE"] == "SIMULTANEOUS":
                output_windows.append("POST_WRITE1")
            else:
                output_windows.extend(("POST_WRITE0", "POST_WRITE1_TARGET_1",
                                       "POST_WRITE1_TARGET_2", "POST_WRITE1"))
            if _second_read_enabled(case):
                output_windows.extend(("FIRST_READ_RESPONSE", "RECOVERY_BEFORE_SECOND_READ",
                                       "SECOND_READ", "SECOND_READ_RESPONSE", "POST_SECOND_READ"))
            else:
                output_windows.extend(("READ_RESPONSE", "TAIL"))
            for window_name in output_windows:
                indexes = _indices(exact_times, windows[window_name])
                if len(indexes) < 2:
                    continue
                selected = [values[index] for index in indexes]
                max_index = max(indexes, key=lambda index: values[index])
                min_index = min(indexes, key=lambda index: values[index])
                max_abs_index = max(indexes, key=lambda index: abs(values[index]))
                metric = {"cell": cell["cell"], "boundary": node_role,
                          "signal": signal, "window": window_name,
                          "sample_count": len(indexes), "min_v": min(selected),
                          "max_v": max(selected), "peak_to_peak_v": max(selected) - min(selected),
                          "area_v_s": _trapz(trace.time, values, indexes),
                          "time_of_max_v_s": str(exact_times[max_index]),
                          "time_of_min_v_s": str(exact_times[min_index]),
                          "time_of_max_abs_v_s": str(exact_times[max_abs_index])}
                if _second_read_enabled(case):
                    metric["first_sample_v"] = values[indexes[0]]
                    metric["last_sample_v"] = values[indexes[-1]]
                    metric["read_cycle"] = (
                        "FIRST_READ" if window_name == "FINAL_READ" else
                        "SECOND_READ" if window_name == "SECOND_READ" else None)
                outputs.append(metric)
    return {
        "schema": "bvm-2x2-rowcol-cell-metrics-v1",
        "status": "DERIVED_ARITHMETIC_ONLY",
        "raw_sha256": sha256(raw_path),
        "sample_count": trace.sample_count,
        "time_range_s": [trace.time[0], trace.time[-1]],
        "dt_min_s": min(trace.dt), "dt_max_s": max(trace.dt),
        "uniform_time_grid": trace.qa()["uniform_time_grid"],
        "windows": window_manifest,
        "current_metrics": currents,
        "junction_metrics": jj_metrics,
        "output_metrics": outputs,
        "phase_raw_units": "radians",
        "phase_turns_definition": "full raw trace unwrapped independently, then delta/(2*pi); not an SFQ count",
        "integration_method": "trapezoid over actual stored raw time rows selected by exact decimal half-open windows",
        "interpolation_or_resampling": False,
        "scientific_interpretation_performed": False,
    }


def _raw_qa(raw_path: Path, probe_manifest: dict[str, Any], before: str, after: str) -> dict[str, Any]:
    from bvmtools.raw import read_csv

    trace = read_csv(raw_path)
    expected = {entry["label"] for entry in probe_manifest["signals"]}
    missing = sorted(expected - set(trace.headers))
    duplicate = trace.duplicate_columns
    return {"schema": "bvm-2x2-rowcol-raw-qa-v1", **trace.qa(),
            "status": "PASS" if before == after and not missing and not duplicate else "FAIL",
            "raw_sha256_before": before, "raw_sha256_after": after,
            "raw_immutable": before == after, "missing_required_probes": missing,
            "probe_count": probe_manifest["signal_count"],
            "scientific_interpretation_performed": False}


def _plotter_module() -> Any:
    spec = importlib.util.spec_from_file_location("josim_plot2_rowcol", PLOTTER)
    if spec is None or spec.loader is None:
        raise ConfigError(f"cannot import classic plotter {PLOTTER}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def render_plots(run_dir: Path, topology: dict[str, Any], probes: dict[str, Any],
                 case: dict[str, str], stimulus: dict[str, str]) -> dict[str, Any]:
    import pandas as pd
    from bvmtools.raw import read_csv

    raw = run_dir / "raw.csv"
    before = sha256(raw)
    trace = read_csv(raw)
    if trace.duplicate_columns:
        raise ConfigError(f"duplicate raw columns prevent plotting: {trace.duplicate_columns}")
    available = set(trace.headers)
    pages = plot_page_plan(topology, probes)
    for page in pages:
        missing = [label for label in page["signals"] if label not in available]
        if missing:
            raise ConfigError(f"plot page {page['file']} has absent raw signals: {missing}")
    if not PLOTLY_ASSET.is_file():
        raise ConfigError(f"shared Plotly asset missing: {PLOTLY_ASSET}")
    frame = pd.read_csv(raw)
    exact_times = exact_raw_times(raw)
    if len(frame) != len(exact_times):
        raise ConfigError("plot frame row count disagrees with exact raw time rows")
    windows = _stage_windows(case, stimulus)
    plotter = _plotter_module()
    plot_root = run_dir / "plots"
    qa_pages: list[dict[str, Any]] = []
    for page in pages:
        target = plot_root / page["file"]
        target.parent.mkdir(parents=True, exist_ok=True)
        asset_ref = Path(os.path.relpath(PLOTLY_ASSET, target.parent)).as_posix()
        page_frame = frame
        window_qa = None
        if page.get("window_name"):
            window_name = page["window_name"]
            if window_name not in windows:
                raise ConfigError(f"plot page names an unregistered analysis window: {window_name}")
            indices = _indices(exact_times, windows[window_name])
            if len(indices) < 2:
                raise ConfigError(f"plot window {window_name} has fewer than two actual stored rows")
            page_frame = frame.iloc[indices]
            window_qa = {
                "name": window_name,
                "start_seconds": str(windows[window_name][0]),
                "end_seconds": str(windows[window_name][1]),
                "boundary_rule": "[start,end)",
                "first_stored_time_seconds": str(exact_times[indices[0]]),
                "last_stored_time_seconds": str(exact_times[indices[-1]]),
            }
        fig = plotter.seperate_combined_layout(
            page_frame, SimpleNamespace(subset=page["signals"], jump="2pi"))
        fig.update_layout(title=f"{run_dir.name} — {page['title']}",
                          title_font_size=22, template="plotly_dark")
        fig.write_html(target, include_plotlyjs=asset_ref, full_html=True, auto_open=False)
        if asset_ref not in target.read_text(encoding="utf-8"):
            raise ConfigError(f"classic plot page does not reference shared asset: {target}")
        page_qa = {"path": target.relative_to(run_dir).as_posix(),
                   "sha256": sha256(target), "status": "PASS",
                   "trace_count": len(page["signals"]),
                   "sample_count": len(page_frame),
                   "full_stored_time_range": window_qa is None}
        if window_qa is not None:
            page_qa["window"] = window_qa
        qa_pages.append(page_qa)
    after = sha256(raw)
    qa = {"schema": "bvm-2x2-rowcol-plot-qa-v1",
          "status": "PASS" if before == after and len(qa_pages) == len(pages) else "FAIL",
          "raw_sha256_before": before, "raw_sha256_after": after,
          "raw_immutable": before == after,
          "plotter_path": PLOTTER.relative_to(REPO).as_posix(),
          "plotter_sha256": sha256(PLOTTER),
          "plotly_asset_path": PLOTLY_ASSET.relative_to(REPO).as_posix(),
          "plotly_asset_sha256": sha256(PLOTLY_ASSET),
          "layout": "josim-plot2.py sep_comb dark -j 2pi",
          "pages": qa_pages, "page_count": len(qa_pages),
          "scientific_interpretation_performed": False}
    _json(run_dir / "analysis" / "plot_manifest.json",
          {"schema": "bvm-2x2-rowcol-plot-manifest-v1", "raw_sha256": before,
           "pages": pages, "plotter_sha256": qa["plotter_sha256"],
           "plotly_asset_sha256": qa["plotly_asset_sha256"]})
    _json(run_dir / "analysis" / "plot_qa.json", qa)
    return qa


def _write_root_manifest(run_id: str, run_dir: Path, result: dict[str, Any]) -> None:
    manifest_path = SERIES / "experiment_manifest.json"
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    else:
        manifest = {"schema": "bvm-2x2-rowcol-experiment-manifest-v1",
                    "experiment_id": SERIES.name, "runs": [],
                    "scientific_interpretation_performed": False}
    rows = [item for item in manifest["runs"] if item.get("run_id") != run_id]
    rows.append({"run_id": run_id, "path": str(run_dir.relative_to(SERIES)),
                 "physical_solve_count": 1,
                 **{key: result[key] for key in ("drive_mode", "se_topology",
                                                   "effective_se_topology", "se_gate_mode",
                                                   "read0_enabled", "write1_mode",
                                                   "write1_target_1", "write1_target_2",
                                                   "second_read_enabled", "second_row_bits",
                                                   "second_column_bits", "second_read_se_gate_mode",
                                                   "row_bits", "column_bits")},
                 "status": result.get("status"), "artifact_status": result.get("artifact_status"),
                 "raw_sha256": result.get("raw_sha256")})
    manifest["runs"] = rows
    manifest["authorized_manual_run_policy"] = "one current config per invocation; no automatic preset batch"
    _json(manifest_path, manifest)


def _execute(case: dict[str, str], stimulus: dict[str, str]) -> int:
    run_id, run_dir = next_run_path(case)
    rendered = render(case, stimulus, run_dir)
    deck = rendered["deck"]
    solver = _solver_info()
    RUNS.mkdir(parents=True, exist_ok=True)
    try:
        run_dir.mkdir(parents=True, exist_ok=False)
    except FileExistsError as exc:
        raise ConfigError(f"refusing to overwrite run directory {run_dir}") from exc
    (run_dir / "analysis").mkdir()
    (run_dir / "analysis" / "metric_spec.json").write_bytes(METRIC_SPEC.read_bytes())
    (run_dir / "USER_CASE.snapshot.env").write_text(_stable_env(case), encoding="utf-8")
    (run_dir / "STIMULUS.snapshot.env").write_text(_stable_env(stimulus), encoding="utf-8")
    (run_dir / "deck.cir").write_text(deck, encoding="utf-8")
    (run_dir / "actual_deck.cir").write_text(deck, encoding="utf-8")
    _json(run_dir / "topology_manifest.json", rendered["topology"])
    _json(run_dir / "probe_manifest.json", rendered["probes"])
    _json(run_dir / "parameter_manifest.json",
          parameter_manifest(case, stimulus, rendered["sources"]))
    _json(run_dir / "source_manifest.json", source_manifest(rendered["sources"]))
    _json(run_dir / "analysis" / "static_qa.json", rendered["static_qa"])
    timing_windows = {}
    for stage in _active_stages(case):
        start, rise, hold, fall = _stage_timing(stage, stimulus)
        timing_windows[stage] = {
            "start": fmt_time(start), "rise": fmt_time(rise),
            "hold": fmt_time(hold), "fall": fmt_time(fall),
            "width_source": ("WRITE1_RISE/HOLD/FALL" if stage.startswith("WRITE1_TARGET_")
                             else stage),
        }
    _json(run_dir / "stimulus_manifest.json", {
        "schema": "bvm-2x2-rowcol-stimulus-v1",
        **_run_config_identity(case),
        "timing_windows": timing_windows,
        "analysis_windows": {
            name: {"start_seconds": str(start), "end_seconds": str(end),
                   "boundary_rule": "[start,end)"}
            for name, (start, end) in _stage_windows(case, stimulus).items()},
        "line_sources": rendered["drivers"],
        "source_stage_values": rendered["driver_stages"],
        "final_read_se_enabled_by_cell": {
            cell["cell"]: cell["final_read_se_enabled"]
            for cell in rendered["topology"]["cell_instances"]},
        "second_read_se_enabled_by_cell": {
            cell["cell"]: cell["second_read_se_enabled"]
            for cell in rendered["topology"]["cell_instances"]},
        "final_read_bl_zero": True,
    })
    (run_dir / "analysis" / "metric_spec.json").write_bytes(
        METRIC_SPEC.read_bytes())
    (run_dir / "stimulus.inc").write_text(rendered["stimulus_text"], encoding="utf-8")
    preflight_text = write_run_preflight(run_dir, run_id, case, stimulus, rendered, solver)
    (run_dir / "PREFLIGHT.md").write_text(preflight_text, encoding="utf-8")
    command = [str(SOLVER), "-a", "1", "-o", str(run_dir / "raw.csv"), str(run_dir / "deck.cir")]
    provenance = {
        "schema": "bvm-2x2-rowcol-provenance-v1", "experiment_id": SERIES.name,
        "run_id": run_id, "parent_head": solver["parent_head"],
        "physical_solve_count": 1, "automatic_follow_up": False,
        "scientific_interpretation_performed": False,
        "solver": solver, "command": command,
        "user_case": {"path": "USER_CASE.snapshot.env", "sha256": sha256(run_dir / "USER_CASE.snapshot.env")},
        "stimulus": {"path": "STIMULUS.snapshot.env", "sha256": sha256(run_dir / "STIMULUS.snapshot.env")},
        "deck": {"path": "deck.cir", "sha256": sha256(run_dir / "deck.cir")},
        "stimulus_manifest": {"path": "stimulus_manifest.json", "sha256": sha256(run_dir / "stimulus_manifest.json")},
        "stimulus_include": {"path": "stimulus.inc", "sha256": sha256(run_dir / "stimulus.inc")},
        "source_manifest": {"path": "source_manifest.json", "sha256": sha256(run_dir / "source_manifest.json")},
        "topology_manifest": {"path": "topology_manifest.json", "sha256": sha256(run_dir / "topology_manifest.json")},
        "probe_manifest": {"path": "probe_manifest.json", "sha256": sha256(run_dir / "probe_manifest.json")},
        "parameter_manifest": {"path": "parameter_manifest.json", "sha256": sha256(run_dir / "parameter_manifest.json")},
        "metric_spec": {"path": "analysis/metric_spec.json", "sha256": sha256(run_dir / "analysis" / "metric_spec.json")},
        "static_qa": {"path": "analysis/static_qa.json", "sha256": sha256(run_dir / "analysis" / "static_qa.json")},
        "preflight": {"path": "PREFLIGHT.md", "sha256": sha256(run_dir / "PREFLIGHT.md")},
        "executor_sha256": sha256(Path(__file__)),
        "sources": {role: item for role, item in rendered["sources"].items()},
    }
    _json(run_dir / "provenance.json", provenance)
    (run_dir / "run.log").write_text(
        f"run_id={run_id}\nstarted_at_utc={datetime.now(timezone.utc).isoformat()}\n"
        f"command={shlex.join(command)}\nsolver_sha256={solver['sha256']}\n",
        encoding="utf-8")
    completed = subprocess.run(command, cwd=run_dir, capture_output=True, text=True, check=False)
    (run_dir / "stdout.txt").write_text(completed.stdout, encoding="utf-8")
    (run_dir / "stderr.txt").write_text(completed.stderr, encoding="utf-8")
    with (run_dir / "run.log").open("a", encoding="utf-8") as stream:
        stream.write(f"solver_exit_code={completed.returncode}\n")
    verify_sources()
    if completed.returncode != 0 or not (run_dir / "raw.csv").is_file():
        result = {"schema": "bvm-2x2-rowcol-result-v1", "run_id": run_id,
                  **_run_config_identity(case),
                  "status": "SOLVER_FAILURE", "artifact_status": "INVALID",
                  "solver_exit_code": completed.returncode, "physical_solve_count": 1,
                  "automatic_follow_up": False, "scientific_interpretation_performed": False}
        _json(run_dir / "result.json", result)
        _write_root_manifest(run_id, run_dir, result)
        return completed.returncode or 2

    raw_hash_before = sha256(run_dir / "raw.csv")
    provenance["started_at_utc"] = datetime.now(timezone.utc).isoformat()
    provenance["raw"] = {"path": "raw.csv", "sha256": raw_hash_before,
                          "bytes": (run_dir / "raw.csv").stat().st_size}
    _json(run_dir / "provenance.json", provenance)
    try:
        raw_qa = _raw_qa(run_dir / "raw.csv", rendered["probes"], raw_hash_before, raw_hash_before)
        _json(run_dir / "analysis" / "raw_qa.json", raw_qa)
        stage_metrics = analyze_raw(run_dir / "raw.csv", case, stimulus, rendered["topology"])
        _json(run_dir / "analysis" / "cell_metrics.json", stage_metrics)
        driver_stages = rendered["driver_stages"]
        second_read_stage_ok = (
            not _second_read_enabled(case) or
            (all("SECOND_READ" in values for values in driver_stages.values())
             and all(values.get("SECOND_READ") == "0" for source, values in driver_stages.items()
                     if source.startswith("I_BL_"))))
        second_read_gate_ok = rendered["static_qa"]["second_read_crosspoint_gate_exact"]
        selective_write_ok = (
            case["WRITE1_MODE"] != "SEQUENTIAL_CROSSPOINT" or
            (rendered["static_qa"]["selective_write_keeps_shared_wl_bl"]
             and all({"WRITE1_TARGET_1", "WRITE1_TARGET_2"}.issubset(values)
                     for values in driver_stages.values())))
        read0_stage_ok = all("READ0" in values for values in driver_stages.values()) == (
            case["READ0_ENABLE"] == "1")
        stimulus_qa = {
            "schema": "bvm-2x2-rowcol-stimulus-qa-v1",
            "status": "PASS" if (len(rendered["drivers"]) == rendered["topology"]["driver_count"]
                                     and all("FINAL_READ" in item for item in driver_stages.values())
                                     and second_read_stage_ok
                                     and second_read_gate_ok
                                     and selective_write_ok and read0_stage_ok
                                     and all(driver["source"] in rendered["stimulus_text"]
                                             for driver in rendered["drivers"])
                                     and "stimulus.inc" in deck
                                     and all(driver["node"] in deck for driver in rendered["drivers"])) else "FAIL",
            **_run_config_identity(case),
            "driver_count": len(rendered["drivers"]),
            "source_count_by_branch": rendered["topology"]["driver_count_by_branch"],
            "drivers": rendered["drivers"], "stage_values": driver_stages,
            "final_read_se_enabled_by_cell": {
                cell["cell"]: cell["final_read_se_enabled"]
                for cell in rendered["topology"]["cell_instances"]},
            "second_read_se_enabled_by_cell": {
                cell["cell"]: cell["second_read_se_enabled"]
                for cell in rendered["topology"]["cell_instances"]},
            "second_read_crosspoint_gate_exact": second_read_gate_ok,
            "second_read_bl_zero": second_read_stage_ok,
            "selective_write_stage_values_exact": selective_write_ok,
            "read0_enable_matches_pwl_presence": read0_stage_ok,
            "pwl_source_count": len(rendered["drive_lines"]),
            "final_read_bl_zero": all(item["FINAL_READ"] == "0" for source, item in driver_stages.items()
                                       if source.startswith("I_BL_")),
            "actual_crosspoints": rendered["topology"]["cell_selection"],
            "deck_sha256": sha256(run_dir / "deck.cir"),
            "stimulus_include_sha256": sha256(run_dir / "stimulus.inc"),
            "physical_solve_count": 1, "scientific_interpretation_performed": False,
        }
        _json(run_dir / "analysis" / "stimulus_qa.json", stimulus_qa)
        plot_qa = render_plots(run_dir, rendered["topology"], rendered["probes"], case, stimulus)
        raw_hash_after = sha256(run_dir / "raw.csv")
        raw_qa = _raw_qa(run_dir / "raw.csv", rendered["probes"], raw_hash_before, raw_hash_after)
        _json(run_dir / "analysis" / "raw_qa.json", raw_qa)
        qa_pass = (raw_qa["status"] == "PASS" and stimulus_qa["status"] == "PASS"
                   and plot_qa["status"] == "PASS")
        mechanical_qa = {
            "schema": "bvm-2x2-rowcol-mechanical-qa-v1",
            "status": "PASS" if qa_pass else "FAIL",
            "physical_solve_count": 1, "solver_exit_code": completed.returncode,
            "raw_sha256_before": raw_hash_before, "raw_sha256_after_plots": raw_hash_after,
            "raw_immutable": raw_hash_before == raw_hash_after,
            "raw_qa_status": raw_qa["status"], "stimulus_qa_status": stimulus_qa["status"],
            "plot_qa_status": plot_qa["status"],
            "sample_count": raw_qa["sample_count"],
            "time_start_s": raw_qa["time_start"], "time_end_s": raw_qa["time_end"],
            "dt_min_s": raw_qa["dt_min"], "dt_max_s": raw_qa["dt_max"],
            "uniform_time_grid": raw_qa["uniform_time_grid"],
            "probe_count": rendered["probes"]["signal_count"],
            "static_qa_status": rendered["static_qa"]["status"],
            "scientific_interpretation_performed": False,
        }
        _json(run_dir / "analysis" / "mechanical_qa.json", mechanical_qa)
        for key, relative in (("cell_metrics", "analysis/cell_metrics.json"),
                              ("raw_qa", "analysis/raw_qa.json"),
                              ("stimulus_qa", "analysis/stimulus_qa.json"),
                              ("plot_qa", "analysis/plot_qa.json"),
                              ("mechanical_qa", "analysis/mechanical_qa.json")):
            provenance[key] = {"path": relative, "sha256": sha256(run_dir / relative)}
        _json(run_dir / "provenance.json", provenance)
        provenance_checks = {
            role: sha256(REPO / item["path"]) == item["sha256"]
            for role, item in rendered["sources"].items()
        }
        provenance_qa = {
            "schema": "bvm-2x2-rowcol-provenance-qa-v1",
            "status": "PASS" if all(provenance_checks.values())
            and provenance["deck"]["sha256"] == sha256(run_dir / "deck.cir")
            and provenance["source_manifest"]["sha256"] == sha256(run_dir / "source_manifest.json")
            and provenance["parameter_manifest"]["sha256"] == sha256(run_dir / "parameter_manifest.json")
            and provenance["topology_manifest"]["sha256"] == sha256(run_dir / "topology_manifest.json")
            and provenance["probe_manifest"]["sha256"] == sha256(run_dir / "probe_manifest.json")
            and provenance["user_case"]["sha256"] == sha256(run_dir / "USER_CASE.snapshot.env")
            and provenance["stimulus"]["sha256"] == sha256(run_dir / "STIMULUS.snapshot.env")
            and provenance["stimulus_include"]["sha256"] == sha256(run_dir / "stimulus.inc")
            and provenance["stimulus_manifest"]["sha256"] == sha256(run_dir / "stimulus_manifest.json")
            and provenance["preflight"]["sha256"] == sha256(run_dir / "PREFLIGHT.md")
            and provenance["metric_spec"]["sha256"] == sha256(run_dir / "analysis" / "metric_spec.json")
            and provenance["static_qa"]["sha256"] == sha256(run_dir / "analysis" / "static_qa.json")
            and provenance["raw"]["sha256"] == raw_hash_after
            else "FAIL",
            "source_hashes_match": provenance_checks,
            "deck_sha256": sha256(run_dir / "deck.cir"),
            "raw_sha256": raw_hash_after,
            "static_qa_status": rendered["static_qa"]["status"],
            "scientific_interpretation_performed": False,
        }
        _json(run_dir / "analysis" / "provenance_qa.json", provenance_qa)
        qa_pass = qa_pass and provenance_qa["status"] == "PASS"
        mechanical_qa["status"] = "PASS" if qa_pass else "FAIL"
        mechanical_qa["provenance_qa_status"] = provenance_qa["status"]
        _json(run_dir / "analysis" / "mechanical_qa.json", mechanical_qa)
        provenance["mechanical_qa"] = {"path": "analysis/mechanical_qa.json",
                                       "sha256": sha256(run_dir / "analysis" / "mechanical_qa.json")}
        provenance["provenance_qa"] = {"path": "analysis/provenance_qa.json",
                                       "sha256": sha256(run_dir / "analysis" / "provenance_qa.json")}
        _json(run_dir / "provenance.json", provenance)
        result = {
            "schema": "bvm-2x2-rowcol-result-v1", "run_id": run_id,
            **_run_config_identity(case),
            "status": "MECHANICAL_QA_PASS_AWAITING_USER_REVIEW" if qa_pass else "ARTIFACT_INVALID",
            "artifact_status": "VALID" if qa_pass else "INVALID",
            "solver_exit_code": 0, "physical_solve_count": 1,
            "raw_sha256": raw_hash_after, "sample_count": raw_qa["sample_count"],
            "time_range_s": [raw_qa["time_start"], raw_qa["time_end"]],
            "raw_qa_status": raw_qa["status"], "stimulus_qa_status": stimulus_qa["status"],
            "plot_qa_status": plot_qa["status"],
            "mechanical_qa_status": mechanical_qa["status"],
            "provenance_qa_status": provenance_qa["status"],
            "scientific_interpretation_performed": False, "automatic_follow_up": False,
        }
        _json(run_dir / "result.json", result)
        brief = [f"# {run_id}", "",
                 f"- DRIVE_MODE: `{case['DRIVE_MODE']}`; ROW_BITS=`{case['ROW_BITS']}`; COL_BITS=`{case['COL_BITS']}`.",
                 f"- SE_TOPOLOGY: `{case['SE_TOPOLOGY']}`; SE_GATE_MODE: `{case['SE_GATE_MODE']}`.",
                 f"- READ0_ENABLE: `{case['READ0_ENABLE']}`; WRITE1_MODE: `{case['WRITE1_MODE']}`; "
                 f"selective targets: `{case['WRITE1_TARGET_1']}`, `{case['WRITE1_TARGET_2']}`.",
                 f"- SECOND_READ_ENABLE: `{case['SECOND_READ_ENABLE']}`; bits=`{case['SECOND_ROW_BITS']}/"
                 f"{case['SECOND_COL_BITS']}`; second-read SE gate is CELL_CROSSPOINT.",
                 f"- Active crosspoints: `{', '.join(rendered['topology']['cell_selection']['active_crosspoints']) or 'none'}`.",
                 f"- Analysis windows: `{', '.join(_stage_windows(case, stimulus))}` (half-open; actual stored rows).",
                 f"- Half-selected: `{', '.join(rendered['topology']['cell_selection']['half_selected']) or 'none'}`; unselected: `{', '.join(rendered['topology']['cell_selection']['unselected']) or 'none'}`.",
                 f"- physical_solve_count: `1`; artifact status: `{result['artifact_status']}`.",
                 f"- raw SHA-256: `{raw_hash_after}`; samples: `{raw_qa['sample_count']}`.",
                 f"- raw/stimulus/plot QA: `{raw_qa['status']}` / `{stimulus_qa['status']}` / `{plot_qa['status']}`.",
                 "- Scientific interpretation: `NOT_PERFORMED`; phase turns are not SFQ counts.", ""]
        (run_dir / "RESULT_BRIEF.md").write_text("\n".join(brief), encoding="utf-8")
        _write_root_manifest(run_id, run_dir, result)
        return 0 if qa_pass else 2
    except Exception as exc:
        result = {"schema": "bvm-2x2-rowcol-result-v1", "run_id": run_id,
                  **_run_config_identity(case),
                  "status": "POSTPROCESS_FAILURE_RAW_PRESERVED", "artifact_status": "INVALID",
                  "solver_exit_code": 0, "physical_solve_count": 1,
                  "raw_sha256": sha256(run_dir / "raw.csv"),
                  "error": f"{type(exc).__name__}: {exc}",
                  "scientific_interpretation_performed": False}
        _json(run_dir / "result.json", result)
        _write_root_manifest(run_id, run_dir, result)
        print(f"POSTPROCESS_FAILURE: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render or run one 2x2 row/column BVM configuration")
    parser.add_argument("--dry-run", action="store_true", help="render and validate only; never invoke JoSIM")
    parser.add_argument("--preset", choices=sorted(PRESET_NAMES), default=None)
    parser.add_argument("--verbose", action="store_true",
                        help="with --dry-run, also print every manifest, probe, PWL line, and full deck")
    args = parser.parse_args(argv)
    try:
        case, stimulus = load_config(args.preset)
        if args.dry_run:
            return dry_run(case, stimulus, verbose=args.verbose)
        if args.verbose:
            raise ConfigError("--verbose is only valid together with --dry-run")
        return _execute(case, stimulus)
    except (OSError, ConfigError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
