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
PRESET_CASES = REGISTERED_CASES + BUS400_CASES
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


class ConfigError(ValueError):
    pass


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


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
    if case.get("OUTPUT_MODE") != "DIAGONAL_TERMINAL" or case.get("T1_MODE") != "OFF":
        raise ConfigError("only DIAGONAL_TERMINAL with T1_MODE=OFF is implemented; future T1 modes fail closed")
    if case.get("CBU_MODE") != "OFF":
        raise ConfigError("CBU/JTL/DFF carry modes are reserved and not implemented in this experiment")
    if case.get("CARRY_MODE", "NONE") != "NONE":
        raise ConfigError("future carry-mode interfaces are reserved and fail closed")
    if _profile(case) not in {"compact", "focus", "debug"}:
        raise ConfigError("PROBE_PROFILE must be compact, focus, or debug")
    if case.get("FOCUS_DIAGONAL") not in DIAGONALS:
        raise ConfigError("FOCUS_DIAGONAL must be D0..D6")
    for key in ("ROW_BITS", "COL_BITS"):
        if not re.fullmatch(r"[01]{4}", case.get(key, "")):
            raise ConfigError(f"{key} must contain exactly four binary digits")
    _mask_rows(case.get("SE_ENABLE_MASK", ""))
    for diagonal in DIAGONALS:
        _sjtl_counts(case, diagonal)
    if case.get("OUTPUT_MODE") == "DIAGONAL_T1_CHAIN" and case.get("CARRY_MODE") not in {None, "OFF", "NONE"}:
        raise ConfigError("T1_CHAIN is reserved; no CBU/DFF implementation is available")
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
    if _time_ps(case.get("STOP", "0p")) < Decimal("250"):
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
    if not {"T1_BIAS1", "T1_CLK_MODE", "T1_J1_AREA", "T1_L1", "T1_RB1"} <= set(t1_params):
        raise ConfigError("T1_PARAMS.env is incomplete")


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


def _source_manifest(sources: dict[str, dict[str, str]]) -> dict[str, Any]:
    return {"schema": "bvm-4x4-diagonal-source-manifest-v1",
            "canonical_sources_modified": False, "sources": sources,
            "scientific_interpretation_performed": False}


def topology_manifest(sources: dict[str, dict[str, str]], case: dict[str, str]) -> dict[str, Any]:
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
            "output_node": f"DOUT_{name}", "termination_ohm": 2,
        }
    return {"schema": "bvm-4x4-diagonal-topology-v2", "rows": 4, "columns": 4,
            "drive_mode": "SHARED", "se_topology": "CELL", "se_gate_mode": "CROSSPOINT",
            "cells": cells,
            "diagonals": diagonal_records,
            "source_sha256": {role: item["sha256"] for role, item in sources.items()},
            "output_mode": "DIAGONAL_TERMINAL", "t1_mode": "OFF", "cbu_mode": "OFF",
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


def _spice_include(run_dir: Path, relpath: str) -> str:
    return Path(os.path.relpath(REPO / relpath, run_dir)).as_posix()


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


def make_probe_manifest(case: dict[str, str], topology: dict[str, Any]) -> dict[str, Any]:
    signals: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add(label: str, group: str, unit: str, **meta: Any) -> None:
        if label not in seen:
            seen.add(label)
            signals.append({"label": label, "group": group, "unit": unit, **meta})

    profile = _profile(case)
    focus_diagonal = case["FOCUS_DIAGONAL"]
    focus_cells = DIAGONALS[focus_diagonal]

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
    topo = topology_manifest(sources, case)
    stimulus_text, drivers = render_stimulus(case, stimulus)
    probes = make_probe_manifest(case, topo)
    lines = [
        "* BVM 4x4 diagonal collection; canonical BVM/QB/sJTL/CB; T1_MODE=OFF.",
        "* Cell WL/BL are physically shared buses; SE is cell-local.",
        ".include " + _spice_include(run_dir, SOURCE_PATHS["JJMIT"]),
        ".include " + _spice_include(run_dir, SOURCE_PATHS["BVM"]),
        ".include " + _spice_include(run_dir, SOURCE_PATHS["QB"]),
        ".include " + _spice_include(run_dir, SOURCE_PATHS["SJTL"]),
        ".include " + _spice_include(run_dir, SOURCE_PATHS["CB"]),
        ".include stimulus.inc", "",
    ]
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
        lines.append(f"R_TERM_{name} DOUT_{name} 0 2")
    lines.extend(("", "* Registered probes; P is raw radians."))
    lines.extend(f".print {entry['label']}" for entry in probes["signals"])
    lines.extend((f".tran {case['DT']} {case['STOP']}", ".end"))
    deck = "\n".join(lines) + "\n"
    qa = static_validate(case, stimulus, t1_params, deck, stimulus_text, drivers, topo, probes)
    return {"deck": deck, "stimulus_text": stimulus_text, "drivers": drivers,
            "topology": topo, "probes": probes, "sources": sources, "static_qa": qa}


def static_validate(case: dict[str, str], stimulus: dict[str, str], t1_params: dict[str, str],
                    deck: str, stimulus_text: str, drivers: list[dict[str, Any]],
                    topo: dict[str, Any], probes: dict[str, Any]) -> dict[str, Any]:
    lines = deck.splitlines()
    stimulus_lines = [line for line in stimulus_text.splitlines() if line.startswith("I_")]
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
    cb = [line for line in lines if line.startswith("XCB_")]
    terms = [line for line in lines if line.startswith("R_TERM_")]
    expected_sjtl_count = sum(sum(_sjtl_counts(case, name)) for name in DIAGONALS)
    if (len(bvm), len(qb), len(sjtl), len(cb), len(terms)) != (16, 16, expected_sjtl_count, 16, 7):
        raise ConfigError(f"expected 16 BVM, 16 QB, {expected_sjtl_count} configured sJTL, 16 CB and 7 terminal loads")
    if len(set(DIAGONALS)) != 7 or sorted(cell for group in DIAGONALS.values() for cell in group) != sorted(CELLS):
        raise ConfigError("diagonal mapping has duplicate or missing cells")
    if any(any(token in line for token in ("XT1 ", "XCBU", "XDFF", "V_BIAS", "R_CLK")) for line in lines):
        raise ConfigError("T1/CBU/DFF/clock hardware must not appear in terminal mode")
    if any("t1_cell.cir" in line for line in lines):
        raise ConfigError("T1_MODE=OFF forbids the canonical T1 include")
    model_include = next((i for i, line in enumerate(lines)
                          if line.lower().endswith("circuits/models/jjmit.cir")), None)
    component_includes = [i for i, line in enumerate(lines)
                          if any(line.lower().endswith(SOURCE_PATHS[key].lower())
                                 for key in ("BVM", "QB", "SJTL", "CB"))]
    if model_include is None or len(component_includes) != 4 or model_include > min(component_includes):
        raise ConfigError("shared jjmit model must precede all four direct canonical includes")
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
        expected_terms.add(f"R_TERM_{name} DOUT_{name} 0 2")
    if set(qb) != expected_qb or set(sjtl) != expected_sjtl or set(cb) != expected_cb:
        raise ConfigError("QB/serial-MERGE/sJTL/CB wiring differs from the registered diagonal map")
    if set(terms) != expected_terms or len({line.split()[1] for line in terms}) != 7:
        raise ConfigError("each DOUT must have its own 2-ohm terminal")
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
    return {"schema": "bvm-4x4-diagonal-static-qa-v2", "status": "PASS",
            "physical_solve_count": 0, "bvm_count": 16, "qb_count": 16,
            "sjtl_count": expected_sjtl_count,
            "sjtl_count_by_diagonal": {name: list(_sjtl_counts(case, name)) for name in DIAGONALS},
            "cb_count": 16, "terminal_count": 7,
            "input_driver_count": 24, "driver_count_by_branch": {"WL": 4, "BL": 4, "SE": 16},
            "diagonal_mapping_exact": True, "unique_outputs": True,
            "active_final_crosspoints": expected_active,
            "canonical_source_hashes_match": {role: item["sha256"] == SOURCE_SHA256[role]
                                                for role, item in source_shas.items()},
            "component_pin_orders": {key: list(value) for key, value in actual_pin_orders.items()},
            "t1_mode_off_no_t1_cbu_dff": True,
            "stimulus_source_count": len(stimulus_lines),
            "stimulus_source_lines": stimulus_lines,
            "probe_count": probes["signal_count"],
            "raw_estimate_bytes": raw_estimate,
            "storage_guard": "REVIEW_REQUIRED" if raw_estimate >= MAX_RAW_BYTES else "PASS",
            "scientific_interpretation_performed": False}


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
    print(f"Case: {case['CASE']} | OUTPUT_MODE={case['OUTPUT_MODE']} | T1_MODE={case['T1_MODE']}")
    print(f"ROW_BITS={case['ROW_BITS']} | COL_BITS={case['COL_BITS']} | SE_ENABLE_MASK={case['SE_ENABLE_MASK']}")
    print("Active FINAL_READ crosspoints: " + (", ".join(static["active_final_crosspoints"]) or "none"))
    print("Diagonal lengths: " + ", ".join(f"{name}={len(cells)}" for name, cells in DIAGONALS.items()))
    print(f"Drivers: 4 WL + 4 BL + 16 independent SE = {len(rendered['drivers'])}")
    print(f"Sources SHA verified: {len(rendered['sources'])}; T1 instance=0; CBU=0; DFF=0")
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


def build_bus400_comparison(run_ids: list[str]) -> dict[str, Any]:
    import pandas as pd
    plotter = _plotter_module()
    target = PLOTS / "comparison" / "BUS400_D3_matched.html"
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
        fig.update_layout(title=f"{run_id} — matched BUS400 signals", title_font_size=18,
                          template="plotly_dark")
        sections.append(f"<section><h2>{html.escape(run_id)}</h2>" +
                        fig.to_html(full_html=False, include_plotlyjs=False) + "</section>")
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
            f"<script src=\"{html.escape(asset_ref)}\"></script></head><body>"
            "<h1>BUS400 D3 matched comparison</h1>"
            "<p>Classic josim-plot2 sep_comb/dark/-j 2pi; native stored grids, no interpolation. "
            "Descriptive only; phase turns are navigation arithmetic, not event counts.</p>" +
            "\n".join(sections) + "</body></html>\n")
    target.write_text(page, encoding="utf-8")
    qa = {"schema": "bvm-4x4-bus400-comparison-qa-v1", "status": "PASS",
          "path": target.relative_to(SERIES).as_posix(), "sha256": sha256(target),
          "runs": run_records, "signals": signals,
          "raws_immutable": all(item["raw_sha256_before"] == item["raw_sha256_after"] for item in run_records),
          "interpolation_or_resampling": False, "plotter_sha256": sha256(PLOTTER),
          "plotly_asset_sha256": sha256(PLOTLY_ASSET),
          "scientific_interpretation_performed": False}
    _json(SERIES / "analysis" / "BUS400_comparison_qa.json", qa)
    return qa


def write_bus400_handoff_manifests(run_ids: list[str]) -> None:
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
    write_bus400_handoff_manifests(run_ids)
    return 0


def allocate_run_id(case_name: str) -> str:
    existing = [int(match.group(1)) for path in RUNS.glob("A[0-9][0-9][0-9]_*")
                if (match := re.match(r"A(\d{3})_", path.name))]
    return f"A{max(existing, default=0) + 1:03d}_{case_name}"


def _write_env(path: Path, values: dict[str, str]) -> None:
    path.write_text("".join(f"{key}={value}\n" for key, value in values.items()), encoding="utf-8")


def read_raw(raw_path: Path, required: set[str] | None = None) -> tuple[list[float], dict[str, array.array], list[str]]:
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
        if unexpected:
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
    times, columns, header = read_raw(raw, required)
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


def render_plots(run_dir: Path, probes: dict[str, Any]) -> dict[str, Any]:
    import pandas as pd
    raw = run_dir / "raw.csv"
    before = sha256(raw)
    required = {item["label"] for item in probes["signals"]}
    times, columns, _ = read_raw(raw, required)
    frame = pd.DataFrame({"time": times, **{key: list(value) for key, value in columns.items()}})
    plotter = _plotter_module()
    plot_root = PLOTS / "runs" / run_dir.name
    asset_ref = Path(os.path.relpath(PLOTLY_ASSET, plot_root)).as_posix()
    page_records = []
    for page in plot_signals(probes):
        target = plot_root / page["file"]
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            raise FileExistsError(f"refusing to overwrite plot {target}")
        fig = plotter.seperate_combined_layout(frame, SimpleNamespace(subset=page["signals"], jump="2pi"))
        fig.update_layout(title=f"{run_dir.name} — {page['title']}", title_font_size=20, template="plotly_dark")
        body = fig.to_html(full_html=False, include_plotlyjs=False)
        content = ("<!doctype html><html><head><meta charset=\"utf-8\">"
                   f"<script src=\"{html.escape(asset_ref)}\"></script></head><body>"
                   f"<h1>{html.escape(run_dir.name)} — {html.escape(page['title'])}</h1>"
                   "<p>Classic josim-plot2 sep_comb/dark/-j 2pi; full stored time range; "
                   "P is radians and displayed turns are rad/(2*pi), not event counts.</p>"
                   f"{body}</body></html>\n")
        target.write_text(content, encoding="utf-8")
        page_records.append({"path": target.relative_to(SERIES).as_posix(), "sha256": sha256(target),
                             "status": "PASS", "trace_count": len(page["signals"]),
                             "sample_count": len(times), "full_stored_time_range": True,
                             "signals": page["signals"], "shared_plotly_asset_count": 1})
    after = sha256(raw)
    if before != after:
        raise ConfigError("raw changed during plot generation")
    qa = {"schema": "bvm-4x4-diagonal-plot-qa-v1", "status": "PASS",
          "raw_sha256_before": before, "raw_sha256_after": after,
          "raw_immutable": True, "plotter_path": PLOTTER.relative_to(REPO).as_posix(),
          "plotter_sha256": sha256(PLOTTER), "plotly_asset_path": PLOTLY_ASSET.relative_to(REPO).as_posix(),
          "plotly_asset_sha256": sha256(PLOTLY_ASSET), "layout": "josim-plot2 sep_comb dark -j 2pi",
          "pages": page_records, "page_count": len(page_records),
          "scientific_interpretation_performed": False}
    _json(run_dir / "plot_manifest.json", {"schema": "bvm-4x4-diagonal-plot-manifest-v1",
                                          "raw_sha256": before, "pages": page_records,
                                          "plotter_sha256": qa["plotter_sha256"],
                                          "plotly_asset_sha256": qa["plotly_asset_sha256"]})
    _json(run_dir / "plot_qa.json", qa)
    return qa


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
            solver_info: dict[str, Any], *, batch_id: str | None = None) -> tuple[int, dict[str, Any]]:
    run_id = allocate_run_id(case["CASE"])
    run_dir = RUNS / run_id
    rendered = render(case, stimulus, t1_params, run_dir)
    if rendered["static_qa"]["raw_estimate_bytes"] >= MAX_RAW_BYTES:
        raise ConfigError("pre-solve storage guard: estimated raw exceeds ordinary single-file limit; no solver invoked")
    run_dir.mkdir(parents=True, exist_ok=False)
    case_snapshot = run_dir / "USER_CASE.snapshot.env"
    stimulus_snapshot = run_dir / "STIMULUS.snapshot.env"
    t1_snapshot = run_dir / "T1_PARAMS.snapshot.env"
    _write_env(case_snapshot, case)
    _write_env(stimulus_snapshot, stimulus)
    _write_env(t1_snapshot, t1_params)
    (run_dir / "deck.cir").write_text(rendered["deck"], encoding="utf-8")
    (run_dir / "stimulus.inc").write_text(rendered["stimulus_text"], encoding="utf-8")
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
                                             "stimulus": stimulus, "t1_params": t1_params,
                                             "effective_topology": {
                                                 "sjtl_count_by_diagonal": {
                                                     name: list(_sjtl_counts(case, name)) for name in DIAGONALS},
                                                 "sjtl_total": sum(sum(_sjtl_counts(case, name)) for name in DIAGONALS),
                                                 "cb_total": 16, "terminal_total": 7,
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
        metrics, raw_qa = analyze_raw(run_dir, rendered["probes"])
        _json(run_dir / "metrics.json", metrics)
        _json(run_dir / "raw_qa.json", raw_qa)
        plot_qa = render_plots(run_dir, rendered["probes"])
        raw_hash_after = sha256(raw)
        if raw_hash_after != raw_hash:
            raise ConfigError("raw changed after post-processing")
        metric_spec_path = (SERIES / "analysis" / "BUS400_metric_spec.json"
                            if batch_id == BUS400_BATCH_ID else SERIES / "analysis" / "metric_spec.json")
        provenance = {"schema": "bvm-4x4-diagonal-provenance-v2", "run_id": run_id,
                      "parent_head": solver_info["parent_head"], "solver": solver_info,
                      "deck_sha256": deck_hash, "stimulus_sha256": stimulus_hash,
                      "raw_sha256": raw_hash, "source_sha256": source_hashes,
                      "user_case_sha256": sha256(case_snapshot),
                      "stimulus_config_sha256": sha256(stimulus_snapshot),
                      "stimulus_manifest_sha256": sha256(run_dir / "stimulus_manifest.json"),
                      "t1_params_sha256_reference_only": sha256(t1_snapshot),
                      "probe_manifest_sha256": sha256(run_dir / "probe_manifest.json"),
                      "topology_manifest_sha256": sha256(run_dir / "topology_manifest.json"),
                      "preflight_sha256": sha256(SERIES / "PREFLIGHT.md"),
                      "metric_spec_path": metric_spec_path.relative_to(REPO).as_posix(),
                      "metric_spec_sha256": sha256(metric_spec_path),
                      "runner_sha256": sha256(Path(__file__).resolve()),
                      "experiment_contract_sha256": sha256(REPO / "docs/EXPERIMENT_CONTRACT.md"),
                      "experiment_workflow_sha256": sha256(REPO / "docs/research/EXPERIMENT_WORKFLOW_V1.md"),
                      "risk_level": "NORMAL",
                      "metrics_sha256": sha256(run_dir / "metrics.json"),
                      "plots": plot_qa["pages"],
                      "t1_mode": "OFF", "t1_params_affect_deck": False,
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
              "scientific_interpretation_performed": False}
        _json(run_dir / "qa.json", qa)
        result = {"schema": "bvm-4x4-diagonal-result-v1", "run_id": run_id,
                  "case": case["CASE"], "row_bits": case["ROW_BITS"],
                  "column_bits": case["COL_BITS"], "se_enable_mask": case["SE_ENABLE_MASK"],
                  "batch_id": batch_id,
                  "sjtl_count_by_diagonal": {name: list(_sjtl_counts(case, name)) for name in DIAGONALS},
                  "active_final_crosspoints": _active_cells(case),
                  "status": "MECHANICAL_QA_PASS_AWAITING_USER_REVIEW",
                  "artifact_status": "VALID", "physical_solve_count": 1,
                  "solver_exit_code": completed.returncode, "raw_sha256": raw_hash,
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
            "batch_id": batch_id,
            "t1_mode": "OFF", "t1_parameters_are_reference_only": True,
            "solver": solver_info, "physical_solve_count": 1,
            "deck_sha256": deck_hash, "stimulus_sha256": stimulus_hash,
            "raw_sha256": raw_hash, "source_sha256": source_hashes,
            "probe_count": rendered["probes"]["signal_count"],
            "batch_id": "BVM4X4_BUS400_20261009" if case["CASE"] in BUS400_CASES else "BVM4X4_INITIAL_20261009",
            "risk_level": "NORMAL" if case["CASE"] in BUS400_CASES else "historical registration unchanged",
            "artifact_status": "VALID", "qa_status": "PASS",
            "scientific_interpretation_performed": False,
            "automatic_follow_up": False})
        _write_experiment_manifest({"run_id": run_id, "case": case["CASE"],
                                    "batch_id": batch_id,
                                    "row_bits": case["ROW_BITS"], "column_bits": case["COL_BITS"],
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="BVM 4x4 diagonal-array render/run helper")
    parser.add_argument("--preset", choices=PRESET_CASES)
    parser.add_argument("--set", action="append", default=[], metavar="KEY=VALUE")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--registered-matrix", action="store_true")
    parser.add_argument("--registered-batch", action="store_true")
    parser.add_argument("--bus400-batch", action="store_true",
                        help="run only BUS400_D3_N0 then BUS400_D3_N1, or add --dry-run for its static gate")
    parser.add_argument("--postprocess", metavar="RUN_ID")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.postprocess:
            return repair_existing(args.postprocess)
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
