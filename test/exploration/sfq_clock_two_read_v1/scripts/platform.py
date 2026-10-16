#!/usr/bin/env python3
"""Minimal V9_SHARED_ROW_SE_BL render/run/archive entry point.

This module performs configuration and artifact checks only. It does not
classify SFQ events, evaluate multiplication correctness, or interpret physics.
"""
from __future__ import annotations

import argparse
import csv
import fcntl
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import uuid
import zipfile
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

SERIES = Path(__file__).resolve().parents[1]
REPO = Path(__file__).resolve().parents[4]
TEMPLATE = SERIES / "template" / "deck_v9_shared_row_se_bl.cir"
SOURCE_MANIFEST = SERIES / "template" / "source_manifest.json"
USER_CASE = SERIES / "USER_CASE.env"
RUNS = SERIES / "runs"
PLOTTER = REPO / "scripts" / "josim-plot2.py"
STIMULUS_GENERATOR = REPO / "scripts" / "bvm_stimulus.py"
DRIVE_FOLDER_ID = "1--nlY7Nq5ArVPydJNrnQf-EGmwN-undh"
DRIVE_TARGET = Path(
    "/mnt/g/.shortcut-targets-by-id/"
    "1--nlY7Nq5ArVPydJNrnQf-EGmwN-undh/BVM_Backages"
)
CONTRACT_SENTENCE = "This experiment is governed by docs/EXPERIMENT_CONTRACT.md."
DEFAULT_PROBES = tuple(f"V(S_D{i}_OUT)" for i in range(7)) + ("V(DFF_O)",)
CHANNELS = tuple(f"D{i}" for i in range(7)) + ("DFF",)
CARRY_SJTL_COUNTS = {1: 1, 2: 1, 3: 5, 4: 2, 5: 1, 6: 1}
CONFIG_KEYS = (
    "PROTOCOL", "CASE_NAME", "A", "B", "ROUNDS",
    "READ_INTERVAL_PS", "CLOCK_PERIOD_PS", "SE_CLOCK_DELAY_PS",
    "WRITE_START_PS", "FIRST_READ_PS", "DT_PS", "STOP_PS",
    "WL_WRITE_AMPLITUDE", "BL_WRITE_AMPLITUDE",
    "BL_READ_AMPLITUDE", "SE_READ_AMPLITUDE",
    "PROBE_PROFILE", "CUSTOM_PROBES_FILE",
)
AMPLITUDE_RE = re.compile(r"^(?:\d+(?:\.\d*)?|\.\d+)(?:u|m)$", re.I)
PROBE_RE = re.compile(
    r"^(?:V|I|P)\((?:[A-Za-z0-9_.:+-]+(?:,[A-Za-z0-9_.:+-]+)?|"
    r"[A-Za-z0-9_.:+-]+\|X[A-Za-z0-9_.:+-]+)\)$"
)


class PlatformError(RuntimeError):
    """User-facing preflight, artifact, or archive error."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    data = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    try:
        with temp.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()


def parse_env_text(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line_no, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise PlatformError(f"USER_CASE.env:{line_no}: expected KEY=VALUE")
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip()
        if key not in CONFIG_KEYS:
            raise PlatformError(f"USER_CASE.env:{line_no}: unknown setting {key!r}")
        if key in values:
            raise PlatformError(f"USER_CASE.env:{line_no}: duplicate setting {key!r}")
        values[key] = value
    missing = [key for key in CONFIG_KEYS if key not in values]
    if missing:
        raise PlatformError(f"USER_CASE.env is missing: {', '.join(missing)}")
    return values


def read_config(path: Path = USER_CASE) -> tuple[dict[str, str], bytes]:
    if path.is_symlink() or not path.is_file():
        raise PlatformError(f"configuration is missing or symlinked: {path}")
    raw = path.read_bytes()
    return parse_env_text(raw.decode("utf-8-sig")), raw


def _decimal(values: dict[str, str], key: str) -> Decimal:
    try:
        number = Decimal(values[key])
    except (InvalidOperation, ValueError) as exc:
        raise PlatformError(f"{key} must be a finite decimal number") from exc
    if not number.is_finite():
        raise PlatformError(f"{key} must be finite")
    return number


def _parse_amplitude(values: dict[str, str], key: str) -> None:
    token = values[key]
    if not AMPLITUDE_RE.fullmatch(token):
        raise PlatformError(f"{key} must be a positive JoSIM token such as 400u or 1.2m")
    if Decimal(token[:-1]) <= 0:
        raise PlatformError(f"{key} must be positive")


def validate_config(values: dict[str, str]) -> dict[str, Any]:
    if set(values) != set(CONFIG_KEYS):
        missing = sorted(set(CONFIG_KEYS) - set(values))
        unknown = sorted(set(values) - set(CONFIG_KEYS))
        raise PlatformError(f"configuration key mismatch; missing={missing}, unknown={unknown}")
    if values["PROTOCOL"] != "V9_SHARED_ROW_SE_BL":
        raise PlatformError(
            "PROTOCOL must be V9_SHARED_ROW_SE_BL; legacy WL+SE mode is not available here"
        )
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,47}", values["CASE_NAME"]):
        raise PlatformError("CASE_NAME must be 1..48 letters/digits/_/- and start alphanumeric")
    operands: dict[str, int] = {}
    for key in ("A", "B"):
        try:
            operands[key] = int(values[key], 10)
        except ValueError as exc:
            raise PlatformError(f"{key} must be an integer from 0 to 15") from exc
        if str(operands[key]) != values[key] or not 0 <= operands[key] <= 15:
            raise PlatformError(f"{key} must be an integer from 0 to 15")
    try:
        rounds = int(values["ROUNDS"], 10)
    except ValueError as exc:
        raise PlatformError("ROUNDS must be a positive integer") from exc
    if str(rounds) != values["ROUNDS"] or not 1 <= rounds <= 64:
        raise PlatformError("ROUNDS must be an integer from 1 to 64")
    timing = {key: _decimal(values, key) for key in (
        "READ_INTERVAL_PS", "CLOCK_PERIOD_PS", "SE_CLOCK_DELAY_PS",
        "WRITE_START_PS", "FIRST_READ_PS", "DT_PS", "STOP_PS",
    )}
    for key in ("READ_INTERVAL_PS", "CLOCK_PERIOD_PS", "DT_PS", "STOP_PS"):
        if timing[key] <= 0:
            raise PlatformError(f"{key} must be positive")
    for key in ("SE_CLOCK_DELAY_PS", "WRITE_START_PS", "FIRST_READ_PS"):
        if timing[key] < 0:
            raise PlatformError(f"{key} cannot be negative")
    for key in ("WL_WRITE_AMPLITUDE", "BL_WRITE_AMPLITUDE",
                "BL_READ_AMPLITUDE", "SE_READ_AMPLITUDE"):
        _parse_amplitude(values, key)
    if values["PROBE_PROFILE"] not in {"OUTPUTS", "CUSTOM"}:
        raise PlatformError("PROBE_PROFILE must be OUTPUTS or CUSTOM")
    custom_path = values["CUSTOM_PROBES_FILE"]
    if values["PROBE_PROFILE"] == "OUTPUTS" and custom_path:
        raise PlatformError("CUSTOM_PROBES_FILE must be empty when PROBE_PROFILE=OUTPUTS")
    if values["PROBE_PROFILE"] == "CUSTOM" and not custom_path:
        raise PlatformError("CUSTOM requires a non-empty CUSTOM_PROBES_FILE")

    io_rise, io_hold, io_fall = Decimal(1), Decimal(9), Decimal(1)
    clk_rise, clk_hold, clk_fall = Decimal(1), Decimal(2), Decimal(1)
    if timing["READ_INTERVAL_PS"] <= io_rise + io_hold + io_fall:
        raise PlatformError("READ_INTERVAL_PS must exceed the fixed 11 ps I/O pulse width")
    if timing["CLOCK_PERIOD_PS"] <= clk_rise + clk_hold + clk_fall:
        raise PlatformError("CLOCK_PERIOD_PS must exceed the fixed 4 ps clock pulse width")
    write_end = timing["WRITE_START_PS"] + io_rise + io_hold + io_fall
    if timing["FIRST_READ_PS"] <= write_end:
        raise PlatformError("FIRST_READ_PS must start after WRITE1 has returned to zero")
    reads = [timing["FIRST_READ_PS"] + i * timing["READ_INTERVAL_PS"] for i in range(rounds)]
    clocks = [
        timing["FIRST_READ_PS"] + timing["SE_CLOCK_DELAY_PS"]
        + i * timing["CLOCK_PERIOD_PS"] for i in range(rounds)
    ]
    if clocks[0] <= write_end:
        raise PlatformError("first clock PWL must start after WRITE1 has returned to zero")
    last_required = max(reads[-1] + io_rise + io_hold + io_fall,
                       clocks[-1] + clk_rise + clk_hold + clk_fall)
    if timing["STOP_PS"] < last_required + Decimal(1):
        raise PlatformError(
            f"STOP_PS must be at least 1 ps after the last pulse ends ({last_required} ps)"
        )
    row_bits = "".join(str((operands["A"] >> bit) & 1) for bit in range(4))
    column_bits = "".join(str((operands["B"] >> (3 - bit)) & 1) for bit in range(4))
    return {
        "case_name": values["CASE_NAME"],
        "a": operands["A"],
        "b": operands["B"],
        "rounds": rounds,
        "row_bits_R1_lsb_first": row_bits,
        "column_bits_C1_msb_first": column_bits,
        "read_starts_ps": [str(x) for x in reads],
        "clock_pwl_starts_ps": [str(x) for x in clocks],
        "write_start_ps": str(timing["WRITE_START_PS"]),
        "dt_ps": str(timing["DT_PS"]),
        "stop_ps": str(timing["STOP_PS"]),
        "timing": {key: str(value) for key, value in timing.items()},
        "amplitudes": {key: values[key] for key in (
            "WL_WRITE_AMPLITUDE", "BL_WRITE_AMPLITUDE",
            "BL_READ_AMPLITUDE", "SE_READ_AMPLITUDE")},
        "pulse_shape_ps": {
            "io": {"rise": "1", "hold": "9", "fall": "1"},
            "clock": {"rise": "1", "hold": "2", "fall": "1"},
            "clock_amplitude": "1.2m",
        },
        "probe_profile": values["PROBE_PROFILE"],
        "custom_probes_file": custom_path,
    }


def _custom_probe_path(value: str) -> Path:
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = SERIES / candidate
    try:
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(SERIES.resolve())
    except (OSError, ValueError) as exc:
        raise PlatformError(
            "CUSTOM_PROBES_FILE must resolve to an existing file inside this platform"
        ) from exc
    if candidate.is_symlink() or not resolved.is_file():
        raise PlatformError("CUSTOM_PROBES_FILE must be a regular, non-symlink file")
    return resolved


def load_custom_probes(values: dict[str, str]) -> tuple[list[str], bytes | None, Path | None]:
    if values["PROBE_PROFILE"] == "OUTPUTS":
        return [], None, None
    path = _custom_probe_path(values["CUSTOM_PROBES_FILE"])
    raw = path.read_bytes()
    extras: list[str] = []
    for line_no, raw_line in enumerate(raw.decode("utf-8-sig").splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith(("#", "*")):
            continue
        if line.lower().startswith(".print "):
            raise PlatformError(
                f"{path.name}:{line_no}: write one probe expression, not a .print command"
            )
        if not PROBE_RE.fullmatch(line):
            raise PlatformError(f"{path.name}:{line_no}: unsupported JoSIM probe syntax: {line!r}")
        if line in DEFAULT_PROBES or line in extras:
            raise PlatformError(f"{path.name}:{line_no}: duplicate probe {line!r}")
        extras.append(line)
    if not extras:
        raise PlatformError("CUSTOM_PROBES_FILE contains no probe expressions")
    return extras, raw, path


def _source_closure() -> tuple[dict[str, Any], dict[str, str]]:
    if not SOURCE_MANIFEST.is_file() or SOURCE_MANIFEST.is_symlink():
        raise PlatformError(f"source manifest missing or symlinked: {SOURCE_MANIFEST}")
    manifest = json.loads(SOURCE_MANIFEST.read_text(encoding="utf-8"))
    if sha256_file(TEMPLATE) != manifest["template_sha256"]:
        raise PlatformError("versioned deck template SHA does not match source_manifest.json")
    hashes: dict[str, str] = {}
    for record in manifest["source_closure"]:
        path = TEMPLATE.parent / "sources_frozen" / record["file"]
        if not path.is_file() or path.is_symlink():
            raise PlatformError(f"frozen source missing or symlinked: {path}")
        actual = sha256_file(path)
        if actual != record["sha256"]:
            raise PlatformError(f"frozen source SHA mismatch: {record['file']}")
        hashes[record["file"]] = actual
    return manifest, hashes


def _stimulus_parameters(config: dict[str, str], checked: dict[str, Any]) -> dict[str, Any]:
    return {
        "a": checked["a"],
        "b": checked["b"],
        "write_start_ps": float(checked["write_start_ps"]),
        "read_times_ps": [float(x) for x in checked["read_starts_ps"]],
        "clock_times_ps": [float(x) for x in checked["clock_pwl_starts_ps"]],
        "stop_ps": float(checked["stop_ps"]),
        "wl_write_amplitude": config["WL_WRITE_AMPLITUDE"],
        "bl_write_amplitude": config["BL_WRITE_AMPLITUDE"],
        "bl_read_amplitude": config["BL_READ_AMPLITUDE"],
        "se_read_amplitude": config["SE_READ_AMPLITUDE"],
        "io_rise_ps": 1,
        "io_hold_ps": 9,
        "io_fall_ps": 1,
        "clock_amplitude": "1.2m",
        "clock_rise_ps": 1,
        "clock_hold_ps": 2,
        "clock_fall_ps": 1,
    }


def _generate_stimulus(
    config: dict[str, str], checked: dict[str, Any]
) -> tuple[str, list[dict[str, Any]]]:
    sys.path.insert(0, str(REPO / "scripts"))
    try:
        import bvm_stimulus  # type: ignore[import-not-found]
    except ImportError as exc:
        raise PlatformError("cannot import the shared scripts/bvm_stimulus.py generator") from exc
    text, drivers = bvm_stimulus.make_v9_stimulus(_stimulus_parameters(config, checked))
    # Keep the shared V9 PWL generator but omit its arithmetic-result comment:
    # this runner records inputs and stimulus only; it does not report correctness.
    text = "\n".join(
        line for line in text.splitlines()
        if not (line.startswith("* A=") and "product=" in line)
    ) + "\n"
    return text, drivers


def _source_lines(stimulus: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in stimulus.splitlines():
        if re.match(r"^(?:I_|V_TRIG_CLK_)", line):
            fields = line.split()
            if not fields or fields[0] in result:
                raise PlatformError("duplicate/malformed stimulus source")
            result[fields[0]] = line
    return result


def _pwl_value_at(line: str, time_ps: Decimal) -> str:
    match = re.search(r"\bPWL\((.*)\)\s*$", line, re.I)
    if not match:
        raise PlatformError(f"stimulus source is not PWL: {line}")
    tokens = match.group(1).split()
    if len(tokens) % 2:
        raise PlatformError(f"malformed PWL token pairs: {line}")
    points: list[tuple[Decimal, str]] = []
    for t, value in zip(tokens[0::2], tokens[1::2], strict=True):
        t = t[:-1] if t.lower().endswith("p") else t
        points.append((Decimal(t), value))
    current = points[0][1]
    for point_time, point_value in points:
        if point_time > time_ps:
            break
        current = point_value
    return current


def validate_stimulus(config: dict[str, str], checked: dict[str, Any], stimulus: str) -> dict[str, Any]:
    sources = _source_lines(stimulus)
    expected = {
        *(f"I_WL_R{r}" for r in range(1, 5)),
        *(f"I_BL_C{c}" for c in range(1, 5)),
        *(f"I_SE_R{r}" for r in range(1, 5)),
        *(f"V_TRIG_CLK_{channel}" for channel in CHANNELS),
    }
    if set(sources) != expected or len(sources) != 20:
        raise PlatformError(
            f"V9 stimulus must have exactly 4 WL + 4 BL + 4 shared-row SE + 8 CLK sources; got {len(sources)}"
        )
    io_rise = Decimal(1)
    write_check = Decimal(checked["write_start_ps"]) + io_rise
    reads = [Decimal(x) for x in checked["read_starts_ps"]]
    clocks = [Decimal(x) for x in checked["clock_pwl_starts_ps"]]
    for row in range(1, 5):
        if _pwl_value_at(sources[f"I_WL_R{row}"], write_check) != config["WL_WRITE_AMPLITUDE"]:
            raise PlatformError(f"WRITE1 WL_R{row} does not match USER_CASE.env")
        if any(_pwl_value_at(sources[f"I_WL_R{row}"], read + io_rise) != "0" for read in reads):
            raise PlatformError(f"V9 read must leave WL_R{row} quiet")
        selected = (checked["a"] >> (row - 1)) & 1
        expected_se = config["SE_READ_AMPLITUDE"] if selected else "0"
        for read in reads:
            if _pwl_value_at(sources[f"I_SE_R{row}"], read + io_rise) != expected_se:
                raise PlatformError(f"SE_R{row} read PWL does not match A and SE_READ_AMPLITUDE")
        if _pwl_value_at(sources[f"I_SE_R{row}"], write_check) != "0":
            raise PlatformError(f"WRITE1 must not activate SE_R{row}")
    for col in range(1, 5):
        selected = (checked["b"] >> (4 - col)) & 1
        if _pwl_value_at(sources[f"I_BL_C{col}"], write_check) != config["BL_WRITE_AMPLITUDE"]:
            raise PlatformError(f"WRITE1 BL_C{col} does not match USER_CASE.env")
        expected_read = config["BL_READ_AMPLITUDE"] if selected else "0"
        for read in reads:
            if _pwl_value_at(sources[f"I_BL_C{col}"], read + io_rise) != expected_read:
                raise PlatformError(f"BL_C{col} read PWL does not match B and BL_READ_AMPLITUDE")
    for channel in CHANNELS:
        line = sources[f"V_TRIG_CLK_{channel}"]
        for clock in clocks:
            if _pwl_value_at(line, clock + Decimal(1)) != "1.2m":
                raise PlatformError(f"clock PWL for {channel} does not match its registered schedule")
    return {
        "source_count": len(sources),
        "source_counts": {"WL": 4, "BL": 4, "SE": 4, "CLK": 8},
        "write1_source_event_count": 1,
        "read_starts_ps": checked["read_starts_ps"],
        "clock_pwl_starts_ps": checked["clock_pwl_starts_ps"],
        "configuration_matches_generated_pwl": True,
    }


def render_deck(dt_ps: str, stop_ps: str, extra_probes: list[str]) -> str:
    text = TEMPLATE.read_text(encoding="utf-8")
    if text.count("{{DT_PS}}") != 1 or text.count("{{STOP_PS}}") != 1:
        raise PlatformError("deck template must contain one DT_PS and STOP_PS placeholder")
    rendered = text.replace("{{DT_PS}}", dt_ps).replace("{{STOP_PS}}", stop_ps)
    if extra_probes:
        end = re.search(r"(?im)^\.end\s*$", rendered)
        if not end:
            raise PlatformError("deck template is missing .end")
        additions = "".join(f".print {probe}\n" for probe in extra_probes)
        rendered = rendered[:end.start()] + additions + rendered[end.start():]
    if "{{" in rendered or "}}" in rendered:
        raise PlatformError("unexpanded template placeholder remains in deck")
    return rendered


def _normalized_body(text: str) -> list[str]:
    """Circuit-body view used only to prove template equivalence."""
    return [
        line.strip() for line in text.splitlines()
        if line.strip()
        and not line.lstrip().startswith("*")
        and not re.match(r"(?i)^\s*\.print\b", line)
        and not re.match(r"(?i)^\s*\.tran\b", line)
    ]


def _subcircuits(source_paths: list[Path]) -> tuple[dict[str, set[str]], dict[str, tuple[str, ...]]]:
    elements: dict[str, set[str]] = {}
    pins: dict[str, tuple[str, ...]] = {}
    for path in source_paths:
        current: str | None = None
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith(("*", "$")):
                continue
            fields = line.split()
            if fields[0].lower() == ".subckt" and len(fields) >= 2:
                current = fields[1]
                pins[current] = tuple(fields[2:])
                elements[current] = set()
            elif fields[0].lower() == ".ends":
                current = None
            elif current and not fields[0].startswith(("+", ".")):
                elements[current].add(fields[0].upper())
    return elements, pins


def validate_probes(deck: str, stimulus: str, probes: list[str]) -> None:
    manifest, _ = _source_closure()
    source_paths = [
        TEMPLATE.parent / "sources_frozen" / item["file"]
        for item in manifest["source_closure"]
    ]
    internal_elements, subckt_pins = _subcircuits(source_paths)
    top_nodes: set[str] = set()
    top_elements: set[str] = set()
    instances: dict[str, str] = {}

    def consume_netlist(text: str) -> None:
        for raw in text.splitlines():
            fields = raw.strip().split()
            if not fields or fields[0].startswith(("*", ".", "+")):
                continue
            name = fields[0]
            top_elements.add(name.upper())
            if name.upper().startswith("X"):
                model = fields[-1]
                if model not in subckt_pins:
                    raise PlatformError(f"instance {name} references unknown model {model}")
                pin_count = len(subckt_pins[model])
                if len(fields) < pin_count + 2:
                    raise PlatformError(f"instance line has too few pins: {raw}")
                top_nodes.update(fields[1:1 + pin_count])
                instances[name.upper()] = model
            elif len(fields) >= 3:
                top_nodes.update(fields[1:3])

    consume_netlist(deck)
    consume_netlist(stimulus)
    for probe in probes:
        match = re.fullmatch(r"([VIP])\(([^()]*)\)", probe)
        if not match:
            raise PlatformError(f"unsupported JoSIM .print expression: {probe}")
        kind, arg = match.groups()
        if "|" in arg:
            element, instance = arg.split("|", 1)
            model = instances.get(instance.upper())
            if model is None or element.upper() not in internal_elements.get(model, set()):
                raise PlatformError(f"probe does not resolve to a real internal element: {probe}")
            if kind == "P" and not element.upper().startswith(("B_J", "J")):
                raise PlatformError(f"phase probe must name a junction element: {probe}")
        elif kind in {"V", "P"}:
            nodes = [part.strip() for part in arg.split(",")]
            if any(node not in top_nodes for node in nodes):
                raise PlatformError(f"node probe references an unknown top-level node: {probe}")
        elif kind == "I":
            if arg.upper() not in top_elements:
                raise PlatformError(f"current probe references an unknown top-level element: {probe}")


def validate_topology(config: dict[str, str], checked: dict[str, Any],
                      deck: str, stimulus: str, probes: list[str]) -> dict[str, Any]:
    lines = deck.splitlines()
    xlines = [line.split() for line in lines if line.strip().upper().startswith("X")]
    by_name = {fields[0].upper(): fields for fields in xlines}
    if len(by_name) != len(xlines):
        raise PlatformError("duplicate top-level instance names")
    bvm_lines = [fields for fields in xlines if fields[0].upper().startswith("XBVM_")]
    qb_lines = [fields for fields in xlines if fields[0].upper().startswith("XBQ_")]
    t1_lines = [fields for fields in xlines if fields[0].upper().startswith("XT1_D")]
    if (len(bvm_lines), len(qb_lines), len(t1_lines)) != (16, 16, 7):
        raise PlatformError("V9 topology requires exactly 16 BVM, 16 QB and seven T1 instances")
    for row in range(1, 5):
        for col in range(1, 5):
            cell = f"R{row}C{col}"
            expected = [
                f"XBVM_{cell}", f"WL_R{row}", f"BL_C{col}", f"SE_R{row}",
                f"SL_{cell}", "BVM",
            ]
            if by_name.get(f"XBVM_{cell}") != expected:
                raise PlatformError(f"V9 shared-row-SE/column-BL connection mismatch at {cell}")
    if len([f for f in xlines if re.match(r"^XCB_D[0-6]_L", f[0], re.I)]) != 16:
        raise PlatformError("V9 array chain must contain sixteen array CB stages")
    if len([f for f in xlines if re.match(r"^XCB_CARRY_D[1-6]$", f[0], re.I)]) != 6:
        raise PlatformError("V9 carry path must contain six carry CB stages")
    carry_counts = {}
    for stage, expected_count in CARRY_SJTL_COUNTS.items():
        got = len([
            f for f in xlines
            if re.match(rf"^XSJTL_CARRY_D{stage}(?:_S\d+)?$", f[0], re.I)
        ])
        carry_counts[f"D{stage}"] = got
        if got != expected_count:
            raise PlatformError(f"V9 D{stage} carry sJTL count mismatch: {got}")
    if sum(f[0].upper() == "XDFF" for f in xlines) != 1:
        raise PlatformError("V9 requires exactly one terminal DFF")
    if len([f for f in xlines if f[0].upper().startswith("XDCSFQ_")]) != 8:
        raise PlatformError("V9 clock path must retain eight DCSFQ2 instances")
    if len([f for f in xlines if f[0].upper().startswith("XJTL_IN_")]) != 8:
        raise PlatformError("V9 clock path must retain eight JTL2 input stages")
    if len([f for f in xlines if f[0].upper().startswith("XJTL_S_D")]) != 14:
        raise PlatformError("V9 must retain two Sum-output JTL2 stages on each of seven channels")
    if sum(f[0].upper().startswith("XJTL_D0_") for f in xlines) != 1:
        raise PlatformError("V9 D0 input must retain exactly one entrance JTL")
    for index in range(7):
        t1 = by_name.get(f"XT1_D{index}")
        if not t1 or t1[1] != f"T1_I_D{index}" or t1[2] != f"CLK_D{index}":
            raise PlatformError(f"V9 T1_D{index} input/clock node mismatch")
    if by_name["XT1_D6"][4] != "DFF_IN":
        raise PlatformError("V9 final carry must connect from T1_D6.C to DFF_IN")
    dff = by_name.get("XDFF")
    if not dff or dff[1:4] != ["DFF_IN", "CLK_DFF", "DFF_O"]:
        raise PlatformError("V9 terminal DFF pin map changed")
    if any(f[0].upper().startswith("XMERGE_D") for f in xlines):
        raise PlatformError("V9 topology must not add an active THmitll_MERGE")
    if any(line.upper().startswith("R_TERM_D") for line in lines):
        raise PlatformError("V9 T1 chain must not restore DOUT terminal loads")
    stimulus_qa = validate_stimulus(config, checked, stimulus)
    printed = [line.split(None, 1)[1] for line in lines if re.match(r"(?i)^\s*\.print\s+", line)]
    if printed != probes:
        raise PlatformError("rendered .print list does not exactly match probe manifest order")
    validate_probes(deck, stimulus, probes)
    return {
        "status": "PASS",
        "topology_version": "V9_SHARED_ROW_SE_BL",
        "bvm_count": len(bvm_lines),
        "qb_count": len(qb_lines),
        "wl_source_count": 4,
        "bl_source_count": 4,
        "shared_row_se_source_count": 4,
        "array_cb_count": 16,
        "carry_cb_count": 6,
        "carry_sjtl_count_by_stage": carry_counts,
        "t1_count": len(t1_lines),
        "dff_count": 1,
        "probe_count": len(probes),
        "stimulus": stimulus_qa,
        "solver_invoked": False,
        "physical_solve_count": 0,
    }


def _probe_manifest(profile: str, probes: list[str]) -> dict[str, Any]:
    def describe(signal: str) -> dict[str, Any]:
        kind, arg = signal[0], signal[2:-1]
        if "|" in arg:
            element, instance = arg.split("|", 1)
            endpoint = {"element": element, "instance": instance}
            direction = "element-declared branch orientation"
        elif kind == "V":
            nodes = [part.strip() for part in arg.split(",")]
            endpoint = {"nodes": nodes}
            direction = f"{nodes[0]} relative to ground" if len(nodes) == 1 else f"{nodes[0]} minus {nodes[1]}"
        else:
            endpoint = {"element": arg}
            direction = "JoSIM element branch convention"
        return {
            "label": signal,
            "kind": kind,
            "unit": {"V": "V", "I": "A", "P": "rad"}[kind],
            "endpoint": endpoint,
            "direction": direction,
            "role": "product_output" if signal in DEFAULT_PROBES else "user_custom",
            "missing_probe_consequence": "pre-solve validation fails; no substitute probe is inferred",
        }

    return {
        "schema": "sfq-clock-two-read-probe-manifest-v1",
        "profile": profile,
        "default_output_probe_count": len(DEFAULT_PROBES),
        "signals": [describe(signal) for signal in probes],
        "phase_raw_unit": "radians",
        "plot_policy": "Use all stored raw rows; no resampling or downsampling.",
    }


def build_case(config: dict[str, str]) -> dict[str, Any]:
    checked = validate_config(config)
    extra_probes, custom_bytes, custom_path = load_custom_probes(config)
    probes = list(DEFAULT_PROBES) + extra_probes
    source_manifest, source_hashes = _source_closure()
    stimulus, _ = _generate_stimulus(config, checked)
    deck = render_deck(checked["dt_ps"], checked["stop_ps"], extra_probes)
    topology_qa = validate_topology(config, checked, deck, stimulus, probes)
    return {
        "config": config,
        "checked": checked,
        "deck": deck,
        "stimulus": stimulus,
        "probes": probes,
        "output_probes": list(DEFAULT_PROBES),
        "custom_probes": extra_probes,
        "source_manifest": source_manifest,
        "source_hashes": source_hashes,
        "custom_probe_bytes": custom_bytes,
        "custom_probe_path": custom_path,
        "topology_qa": topology_qa,
    }


def _raw_integrity(raw: Path, expected_probes: list[str]) -> dict[str, Any]:
    if not raw.is_file() or raw.stat().st_size == 0:
        raise PlatformError("JoSIM did not produce a non-empty raw.csv")
    with raw.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.reader(stream)
        try:
            headers = [item.strip() for item in next(reader)]
        except StopIteration as exc:
            raise PlatformError("raw.csv has no header") from exc
        if not headers or headers[0].strip().lower() not in {"time", "time (s)", "time(s)"}:
            raise PlatformError(f"raw.csv first column must be time, got {headers[:1]}")
        if len(headers) != len(set(headers)):
            raise PlatformError("raw.csv contains duplicate column names")
        if headers[1:] != expected_probes:
            raise PlatformError(f"raw.csv probes differ from pre-solve manifest: {headers[1:]}")
        count = 0
        previous: Decimal | None = None
        first: Decimal | None = None
        last: Decimal | None = None
        first_delta: Decimal | None = None
        minimum_delta: Decimal | None = None
        maximum_delta: Decimal | None = None
        nonuniform = False
        for row_no, row in enumerate(reader, start=2):
            if len(row) != len(headers):
                raise PlatformError(
                    f"raw.csv row {row_no} has {len(row)} fields, expected {len(headers)}"
                )
            try:
                t = Decimal(row[0].strip())
                values = [float(x) for x in row[1:]]
            except (InvalidOperation, ValueError) as exc:
                raise PlatformError(f"raw.csv row {row_no} contains non-numeric values") from exc
            if not t.is_finite() or not all(math.isfinite(x) for x in values):
                raise PlatformError(f"raw.csv row {row_no} contains non-finite values")
            if previous is not None:
                delta = t - previous
                if delta <= 0:
                    raise PlatformError(f"raw.csv time is not strictly increasing at row {row_no}")
                minimum_delta = delta if minimum_delta is None else min(minimum_delta, delta)
                maximum_delta = delta if maximum_delta is None else max(maximum_delta, delta)
                if first_delta is None:
                    first_delta = delta
                elif delta != first_delta:
                    nonuniform = True
            if first is None:
                first = t
            last = t
            previous = t
            count += 1
    if count == 0 or first is None or last is None:
        raise PlatformError("raw.csv contains no samples")
    return {
        "status": "PASS",
        "sample_count": count,
        "time_column": headers[0],
        "stored_time_start": str(first),
        "stored_time_end": str(last),
        "time_strictly_increasing": True,
        "stored_grid_nonuniform": nonuniform,
        "stored_dt_min": str(minimum_delta) if minimum_delta is not None else None,
        "stored_dt_max": str(maximum_delta) if maximum_delta is not None else None,
        "probe_count": len(expected_probes),
        "header": headers,
        "raw_bytes": raw.stat().st_size,
        "raw_sha256": sha256_file(raw),
    }


def _plot(run_dir: Path, probes: list[str], output_name: str, log_stream) -> dict[str, Any]:
    command = [
        sys.executable, str(PLOTTER), "raw.csv",
        "-t", "stacked", "-c", "dark", "-j", "2pi",
        "-s", *probes, "-x", output_name,
    ]
    log_stream.write("\n$ " + " ".join(command) + "\n")
    log_stream.flush()
    result = subprocess.run(
        command, cwd=run_dir, stdout=log_stream, stderr=subprocess.STDOUT, check=False,
    )
    html = run_dir / output_name
    if result.returncode != 0 or not html.is_file() or html.stat().st_size == 0:
        raise PlatformError(
            f"josim-plot2.py failed or did not produce {output_name} (exit={result.returncode})"
        )
    body = html.read_text(encoding="utf-8", errors="replace")
    missing = [probe for probe in probes if probe not in body]
    if missing:
        raise PlatformError(f"res.html is missing selected probe labels: {missing}")
    if re.search(r"(?is)<script\b[^>]*\bsrc\s*=", body):
        raise PlatformError("res.html is not standalone/offline; external Plotly JS reference found")
    return {
        "status": "PASS",
        "renderer": str(PLOTTER.relative_to(REPO)),
        "renderer_sha256": sha256_file(PLOTTER),
        "layout": "stacked",
        "theme": "dark",
        "phase_display": "rad/(2*pi)",
        "offline_standalone": True,
        "file": output_name,
        "signal_count": len(probes),
        "html_bytes": html.stat().st_size,
        "html_sha256": sha256_file(html),
    }


def _git_state() -> tuple[str | None, bool | None]:
    try:
        head = subprocess.run(
            ["git", "-C", str(REPO), "rev-parse", "HEAD"],
            check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        ).stdout.strip()
        status = subprocess.run(
            ["git", "-C", str(REPO), "status", "--porcelain=v1"],
            check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        ).stdout
        return head, bool(status.strip())
    except (OSError, subprocess.CalledProcessError):
        return None, None


def _solver_path() -> Path | None:
    bundled = REPO / "build" / "josim-cli"
    if bundled.is_file() and os.access(bundled, os.X_OK):
        return bundled.resolve()
    found = shutil.which("josim-cli")
    return Path(found).resolve() if found else None


def _drive_path_status(target: Path = DRIVE_TARGET) -> dict[str, Any]:
    return {
        "path": str(target),
        "directory_exists": target.is_dir(),
        "writable_by_process": target.is_dir() and os.access(target, os.W_OK),
        "identity": {"provider": "Google DriveFS", "folder_id": DRIVE_FOLDER_ID},
    }


def _drive_write_probe(target: Path = DRIVE_TARGET) -> tuple[bool, str]:
    if not target.is_dir():
        return False, f"archive target directory is not accessible: {target}"
    probe = target / f".bvm-platform-write-test-{uuid.uuid4().hex}.tmp"
    created = False
    try:
        descriptor = os.open(probe, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        created = True
        try:
            os.write(descriptor, b"bvm-drivefs-write-test\n")
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        if probe.read_bytes() != b"bvm-drivefs-write-test\n":
            return False, "DriveFS write-test bytes did not read back identically"
        probe.unlink()
        created = False
        if probe.exists():
            return False, "DriveFS write-test file remained after cleanup"
        return True, "exact target path write/read/unlink test passed"
    except OSError as exc:
        return False, f"DriveFS write test failed: {exc}"
    finally:
        try:
            if created and probe.exists():
                probe.unlink()
        except OSError:
            pass


def _print_dry_run(ctx: dict[str, Any]) -> None:
    checked = ctx["checked"]
    print("DRY RUN PASS — solver_invoked=false; physical_solve_count=0")
    print(f"CASE: {checked['case_name']} | PROTOCOL={ctx['config']['PROTOCOL']}")
    print(f"A={checked['a']} B={checked['b']} ROUNDS={checked['rounds']}")
    print(f"ROW_BITS (R1=LSB): {checked['row_bits_R1_lsb_first']}")
    print(f"COL_BITS (C1=MSB): {checked['column_bits_C1_msb_first']}")
    print(f"READ_STARTS_PS: {','.join(checked['read_starts_ps'])}")
    print(f"CLK_PWL_STARTS_PS: {','.join(checked['clock_pwl_starts_ps'])}")
    print(
        f"WRITE_START_PS={checked['write_start_ps']} DT_PS={checked['dt_ps']} "
        f"STOP_PS={checked['stop_ps']}"
    )
    print(f"AMPLITUDES: {json.dumps(checked['amplitudes'], sort_keys=True)}")
    print("STIMULUS SOURCES: 4 WL + 4 BL + 4 shared-row SE + 8 CLK = 20")
    print(
        f"PROBES: output={len(ctx['output_probes'])}; "
        f"custom_diagnostics={len(ctx['custom_probes'])} "
        f"({ctx['config']['PROBE_PROFILE']})"
    )
    print(f"DECK_SHA256: {sha256_bytes(ctx['deck'].encode('utf-8'))}")
    print(f"STIMULUS_SHA256: {sha256_bytes(ctx['stimulus'].encode('utf-8'))}")
    print(f".tran: .tran {checked['dt_ps']}p {checked['stop_ps']}p")
    print("PROBE_LIST: " + ", ".join(ctx["probes"]))
    print(f"STATIC TOPOLOGY QA: {ctx['topology_qa']['status']}")
    solver = _solver_path()
    print(f"SOLVER: {solver if solver else 'not found (not invoked)'}")
    drive = _drive_path_status()
    state = (
        "ACCESSIBLE" if drive["directory_exists"] and drive["writable_by_process"]
        else "BLOCKED"
    )
    print(f"DRIVE ARCHIVE TARGET: {state} — {drive['path']}")
    print("No run directory or persistent artifact was created.")


def _reserve_run_id(case_name: str, runs_dir: Path = RUNS) -> tuple[str, Path]:
    runs_dir.mkdir(parents=True, exist_ok=True)
    index_path = runs_dir / "run_index.json"
    lock_path = runs_dir / ".run-index.lock"
    with lock_path.open("a+b") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        try:
            index = json.loads(index_path.read_text(encoding="utf-8"))
            next_number = max(1, int(index["next_sequence"]))
            while True:
                run_id = f"V9R{next_number:03d}_{case_name}"
                run_dir = runs_dir / run_id
                if not run_dir.exists():
                    break
                next_number += 1
            index["reserved"].append({
                "run_id": run_id,
                "case_name": case_name,
                "reserved_utc": datetime.now(timezone.utc).isoformat(),
            })
            index["next_sequence"] = next_number + 1
            atomic_json(index_path, index)
            try:
                run_dir.mkdir(exist_ok=False)
            except FileExistsError as exc:
                raise PlatformError(f"run ID collision; reserved ID is not reused: {run_id}") from exc
            return run_id, run_dir
        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def _render_preflight(ctx: dict[str, Any], parent_head: str | None, platform_sha: str,
                      solver_path: Path, solver_version: str | None,
                      solver_sha256: str, run_id: str, run_dir: Path,
                      run_mode: str) -> str:
    config = ctx["config"]
    checked = ctx["checked"]
    source_items = "\n".join(
        f"- {name}: {digest}" for name, digest in ctx["source_hashes"].items()
    )
    probe_manifest = _probe_manifest(config["PROBE_PROFILE"], ctx["probes"])
    probe_items = "\n".join(
        "- {label} [{unit}] endpoint={endpoint}; direction={direction}".format(
            label=signal["label"], unit=signal["unit"],
            endpoint=json.dumps(signal["endpoint"], sort_keys=True),
            direction=signal["direction"],
        )
        for signal in probe_manifest["signals"]
    )
    final_archive_name = f"{run_id}_{config['CASE_NAME']}.zip"
    archive_line = (
        f"- exact archive target: {DRIVE_TARGET / final_archive_name}"
        if run_mode == "ARCHIVE_ON_COMPLETE"
        else "- archive: not requested; local evidence only"
    )
    custom_plot_line = (
        "- custom diagnostic plot: custom.html (only explicitly requested probes)"
        if ctx["custom_probes"] else "- custom diagnostic plot: none"
    )
    return f"""# PREFLIGHT — {config['CASE_NAME']}

{CONTRACT_SENTENCE}

- experiment_risk_level: NORMAL
- parent_head: {parent_head or 'UNKNOWN'}
- run_id: {run_id}
- run directory: {run_dir}
- run mode: {run_mode}
- platform script SHA-256: {platform_sha}
- solver: {solver_path}; version: {solver_version or 'UNKNOWN'}; binary SHA-256: {solver_sha256}
- topology: V9_SHARED_ROW_SE_BL; 16 BVM, 16 QB, seven diagonal T1 channels, six carry CBs, one DFF
- this invocation authorizes one solve only
- scientific interpretation: not performed or authorized by this runner

## Effective inputs

- A={checked['a']}; B={checked['b']}; ROUNDS={checked['rounds']}
- row mapping R1=LSB: {checked['row_bits_R1_lsb_first']}
- column mapping C1=MSB: {checked['column_bits_C1_msb_first']}
- READ starts (ps): {', '.join(checked['read_starts_ps'])}
- CLK PWL starts (ps): {', '.join(checked['clock_pwl_starts_ps'])}
- WRITE1 start={checked['write_start_ps']} ps; DT={checked['dt_ps']} ps; STOP={checked['stop_ps']} ps
- amplitudes: {json.dumps(checked['amplitudes'], sort_keys=True)}
- protocol: {config['PROTOCOL']}; legacy fallback disabled

## Frozen source closure

{source_items}

## Probes

JoSIM P(...) raw values are radians. Probes are descriptive and are not event counts.

{probe_items}

## Artifact scope

- expected raw: raw.csv in this run directory
- expected output page: res.html (eight final output voltages only)
- expected custom page: {"custom.html" if ctx['custom_probes'] else "none"}
{archive_line}
- Drive folder ID (archive mode): {DRIVE_FOLDER_ID if run_mode == 'ARCHIVE_ON_COMPLETE' else 'not used'}
- visualization: standalone res.html using scripts/josim-plot2.py, stacked/dark, phase display rad/(2*pi)
{custom_plot_line}
- no SFQ classifier, arithmetic verdict, timing-margin analysis, or mechanism report
- run artifacts include deck, stimulus, env snapshot, this PREFLIGHT, probe manifest,
  raw/log where produced, per-run manifest, frozen sources, and res.html when raw QA permits
"""


def _write_run_files(run_id: str, run_dir: Path, ctx: dict[str, Any],
                     config_bytes: bytes, solver: Path, solver_version: str | None,
                     parent_head: str | None, worktree_dirty: bool | None,
                     run_mode: str) -> dict[str, Any]:
    config = ctx["config"]
    checked = ctx["checked"]
    snapshot = run_dir / "USER_CASE.snapshot.env"
    snapshot.write_bytes(config_bytes)
    (run_dir / "deck.cir").write_text(ctx["deck"], encoding="utf-8", newline="\n")
    (run_dir / "stimulus.inc").write_text(ctx["stimulus"], encoding="utf-8", newline="\n")
    source_dir = run_dir / "sources_frozen"
    source_dir.mkdir()
    source_records = []
    for record in ctx["source_manifest"]["source_closure"]:
        src = TEMPLATE.parent / "sources_frozen" / record["file"]
        dest = source_dir / record["file"]
        shutil.copyfile(src, dest)
        actual = sha256_file(dest)
        if actual != record["sha256"]:
            raise PlatformError(f"run snapshot source copy hash mismatch: {record['file']}")
        source_records.append({
            "file": record["file"], "role": record["role"],
            "sha256": actual, "bytes": dest.stat().st_size,
        })
    if ctx["custom_probe_bytes"] is not None:
        (run_dir / "CUSTOM_PROBES.snapshot.txt").write_bytes(ctx["custom_probe_bytes"])
    probe_manifest = _probe_manifest(config["PROBE_PROFILE"], ctx["probes"])
    probe_manifest["custom_probe_file_sha256"] = (
        sha256_bytes(ctx["custom_probe_bytes"])
        if ctx["custom_probe_bytes"] is not None else None
    )
    atomic_json(run_dir / "probe_manifest.json", probe_manifest)
    platform_sha = sha256_file(Path(__file__).resolve())
    preflight = _render_preflight(
        ctx, parent_head, platform_sha, solver, solver_version,
        sha256_file(solver), run_id, run_dir, run_mode,
    )
    (run_dir / "PREFLIGHT.md").write_text(preflight, encoding="utf-8", newline="\n")
    manifest = {
        "schema": "sfq-clock-two-read-run-manifest-v1",
        "run_id": run_id,
        "case_name": config["CASE_NAME"],
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PREFLIGHT_READY",
        "run_mode": run_mode,
        "protocol": "V9_SHARED_ROW_SE_BL",
        "operands": {"A": checked["a"], "B": checked["b"]},
        "rounds": checked["rounds"],
        "mapping": {
            "row_bits_R1_lsb_first": checked["row_bits_R1_lsb_first"],
            "column_bits_C1_msb_first": checked["column_bits_C1_msb_first"],
        },
        "effective_config": config,
        "timing_and_amplitudes": checked,
        "stimulus_qa": ctx["topology_qa"]["stimulus"],
        "probe_manifest": probe_manifest,
        "topology_qa": ctx["topology_qa"],
        "source_hashes": {
            "USER_CASE.snapshot.env": sha256_file(snapshot),
            "deck.cir": sha256_file(run_dir / "deck.cir"),
            "stimulus.inc": sha256_file(run_dir / "stimulus.inc"),
            "deck_template": sha256_file(TEMPLATE),
            "platform_script": platform_sha,
            "bvm_stimulus.py": sha256_file(STIMULUS_GENERATOR),
            "josim-plot2.py": sha256_file(PLOTTER),
            "template_source_manifest": sha256_file(SOURCE_MANIFEST),
            "PREFLIGHT.md": sha256_file(run_dir / "PREFLIGHT.md"),
            "probe_manifest.json": sha256_file(run_dir / "probe_manifest.json"),
        },
        "frozen_sources": source_records,
        "execution_environment": {
            "parent_head": parent_head,
            "worktree_dirty_before_run": worktree_dirty,
            "platform": sys.platform,
            "python": sys.version,
            "josim_path": str(solver),
            "josim_version_query": solver_version,
            "josim_binary_sha256": sha256_file(solver),
        },
        "physical_solve_count": 0,
        "solver_exit_code": None,
        "raw_integrity": None,
        "visualization": None,
        "evidence_files": [],
    }
    if ctx["custom_probe_bytes"] is not None:
        manifest["source_hashes"]["CUSTOM_PROBES.snapshot.txt"] = sha256_file(
            run_dir / "CUSTOM_PROBES.snapshot.txt"
        )
    atomic_json(run_dir / "manifest.json", manifest)
    return manifest


def _finalize_manifest(run_dir: Path, manifest: dict[str, Any],
                       status: str, solver_exit_code: int,
                       raw_integrity: dict[str, Any],
                       visualization: dict[str, Any]) -> None:
    manifest["status"] = status
    manifest["solver_exit_code"] = solver_exit_code
    manifest["raw_integrity"] = raw_integrity
    manifest["visualization"] = visualization
    paths = [
        run_dir / name for name in (
            "deck.cir", "stimulus.inc", "USER_CASE.snapshot.env", "PREFLIGHT.md",
            "probe_manifest.json", "run.log", "raw.csv", "res.html",
            "custom.html", "CUSTOM_PROBES.snapshot.txt",
        ) if (run_dir / name).is_file()
    ]
    sources = run_dir / "sources_frozen"
    if sources.is_dir():
        paths.extend(p for p in sorted(sources.iterdir()) if p.is_file() and not p.is_symlink())
    manifest["evidence_files"] = [
        {
            "path": path.relative_to(run_dir).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        for path in sorted(paths, key=lambda p: p.relative_to(run_dir).as_posix())
    ]
    atomic_json(run_dir / "manifest.json", manifest)


def _archive_inputs(run_dir: Path, manifest: dict[str, Any]) -> list[tuple[str, Path]]:
    records = manifest.get("evidence_files")
    if not isinstance(records, list) or not records:
        raise PlatformError("run manifest is not finalized with evidence_files")
    root = run_dir.resolve(strict=True)
    members: list[tuple[str, Path]] = []
    seen: set[str] = set()
    for record in records:
        rel = record.get("path")
        if not isinstance(rel, str) or not rel:
            raise PlatformError("manifest evidence path is malformed")
        relative = Path(rel)
        if relative.is_absolute() or ".." in relative.parts or rel == "archive_receipt.json":
            raise PlatformError(f"unsafe or non-evidence archive member: {rel!r}")
        path = run_dir / relative
        if path.is_symlink() or not path.is_file():
            raise PlatformError(f"evidence file missing or symlinked: {rel}")
        resolved = path.resolve(strict=True)
        if not resolved.is_relative_to(root):
            raise PlatformError(f"evidence path escapes run directory: {rel}")
        if rel in seen:
            raise PlatformError(f"duplicate evidence path in manifest: {rel}")
        if path.stat().st_size != int(record["bytes"]) or sha256_file(path) != record["sha256"]:
            raise PlatformError(f"evidence file changed since manifest freeze: {rel}")
        seen.add(rel)
        members.append((rel, path))
    manifest_path = run_dir / "manifest.json"
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise PlatformError("fixed manifest.json is missing or symlinked")
    members.append(("manifest.json", manifest_path))
    return members


def create_archive(run_dir: Path, target_dir: Path = DRIVE_TARGET,
                   folder_id: str = DRIVE_FOLDER_ID) -> dict[str, Any]:
    """Write one immutable ZIP at the provided exact DriveFS target path."""
    if not target_dir.is_dir() or not os.access(target_dir, os.W_OK):
        raise PlatformError(f"Drive archive target is not accessible/writable: {target_dir}")
    manifest_path = run_dir / "manifest.json"
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes.decode("utf-8"))
    run_id = manifest["run_id"]
    case_name = manifest["case_name"]
    final_name = f"{run_id}_{case_name}.zip"
    final_path = target_dir / final_name
    if final_path.exists():
        raise PlatformError(f"refusing to overwrite existing Drive package: {final_path}")
    temp_path = target_dir / f".{final_name}.{uuid.uuid4().hex}.tmp"
    members = _archive_inputs(run_dir, manifest)
    member_hashes = {
        rel: sha256_file(path) for rel, path in members
    }
    manifest_sha = sha256_bytes(manifest_bytes)
    reserved_fd: int | None = None
    reserved_inode: tuple[int, int] | None = None
    try:
        with zipfile.ZipFile(temp_path, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            for rel, path in members:
                archive.write(path, arcname=f"{run_id}/{rel}")
        with zipfile.ZipFile(temp_path, "r") as archive:
            bad = archive.testzip()
            if bad is not None:
                raise PlatformError(f"ZIP CRC validation failed at {bad}")
            for rel, expected_hash in member_hashes.items():
                digest = hashlib.sha256()
                with archive.open(f"{run_id}/{rel}", "r") as stream:
                    for block in iter(lambda: stream.read(1 << 20), b""):
                        digest.update(block)
                if digest.hexdigest() != expected_hash:
                    raise PlatformError(f"ZIP member SHA mismatch: {rel}")
            zipped_manifest = archive.read(f"{run_id}/manifest.json")
            if zipped_manifest != manifest_bytes:
                raise PlatformError("ZIP manifest bytes differ from the frozen local manifest")
            if sha256_bytes(zipped_manifest) != manifest_sha:
                raise PlatformError("ZIP manifest SHA differs from the frozen local manifest SHA")
            if f"{run_id}/archive_receipt.json" in archive.namelist():
                raise PlatformError("archive_receipt.json must remain outside the ZIP")
        zip_sha = sha256_file(temp_path)
        zip_bytes = temp_path.stat().st_size
        reserved_fd = os.open(final_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        info = os.fstat(reserved_fd)
        reserved_inode = (info.st_dev, info.st_ino)
        os.close(reserved_fd)
        reserved_fd = None
        os.replace(temp_path, final_path)
        if sha256_file(final_path) != zip_sha or final_path.stat().st_size != zip_bytes:
            raise PlatformError("final DriveFS path bytes differ from the verified temporary ZIP")
        return {
            "zip_name": final_name,
            "drive_folder_id": folder_id,
            "drive_path": str(final_path),
            "drive_file_id": None,
            "zip_sha256": zip_sha,
            "zip_bytes": zip_bytes,
            "manifest_sha256": manifest_sha,
            "manifest_bytes_identical_in_zip": True,
            "member_count": len(members),
            "member_sha256_verified": True,
            "crc_verified": True,
            "cloud_sync_status": "UNCONFIRMED",
        }
    except Exception:
        if temp_path.exists():
            temp_path.unlink()
        if reserved_fd is not None:
            os.close(reserved_fd)
        if final_path.exists() and reserved_inode is not None:
            try:
                current = final_path.stat()
                if (current.st_dev, current.st_ino) == reserved_inode and current.st_size == 0:
                    final_path.unlink()
            except OSError:
                pass
        raise


def _write_receipt_no_overwrite(path: Path, receipt: dict[str, Any]) -> None:
    if path.exists():
        raise PlatformError(f"archive receipt already exists; refusing to overwrite: {path}")
    temp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    data = (json.dumps(receipt, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    try:
        with temp.open("xb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temp, path)
        temp.unlink()
    finally:
        if temp.exists():
            temp.unlink()


def archive_completed_run(run_id: str, target_dir: Path = DRIVE_TARGET,
                          runs_dir: Path = RUNS, folder_id: str = DRIVE_FOLDER_ID) -> dict[str, Any]:
    if not re.fullmatch(r"V9R\d{3}_[A-Za-z0-9][A-Za-z0-9_-]{0,47}", run_id):
        raise PlatformError("archive command requires an exact V9R###_CASE run ID")
    run_dir = runs_dir / run_id
    if run_dir.is_symlink() or not run_dir.is_dir():
        raise PlatformError(f"completed run directory missing or symlinked: {run_dir}")
    receipt_path = run_dir / "archive_receipt.json"
    if receipt_path.exists():
        raise PlatformError(f"archive receipt already exists; no second ZIP will be created: {receipt_path}")
    ok, message = _drive_write_probe(target_dir)
    if not ok:
        raise PlatformError(f"{message}; original raw and manifest were left unchanged")
    manifest_bytes_before = (run_dir / "manifest.json").read_bytes()
    manifest = json.loads(manifest_bytes_before.decode("utf-8"))
    if manifest.get("run_id") != run_id or not manifest.get("evidence_files"):
        raise PlatformError("run manifest identity or frozen evidence list is invalid")
    archive_info = create_archive(run_dir, target_dir, folder_id)
    receipt = {
        "schema": "sfq-clock-two-read-archive-receipt-v1",
        "run_id": run_id,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "archive_status": "ZIP_CREATED_AND_LOCAL_BYTES_VERIFIED",
        **archive_info,
        "cloud_sync_status": "UNCONFIRMED",
        "cloud_sync_note": (
            "No Drive API/file-ID readback was performed. Do not describe this ZIP as cloud-upload-confirmed."
        ),
    }
    _write_receipt_no_overwrite(receipt_path, receipt)
    if (run_dir / "manifest.json").read_bytes() != manifest_bytes_before:
        raise PlatformError("archive operation modified the fixed run manifest")
    return receipt

def execute(ctx: dict[str, Any], config_bytes: bytes, run_local: bool = False,
            runs_dir: Path = RUNS, solver_override: Path | None = None,
            drive_target: Path = DRIVE_TARGET) -> int:
    run_mode = "LOCAL_ONLY" if run_local else "ARCHIVE_ON_COMPLETE"
    if run_local:
        message = "run-local selected; DriveFS not checked or used"
    else:
        ok, message = _drive_write_probe(drive_target)
        if not ok:
            print(f"ERROR: {message}; JoSIM was not invoked.")
            return 2

    solver = solver_override or _solver_path()
    if solver is None:
        print("ERROR: josim-cli not found; JoSIM was not invoked.")
        return 2
    version_result = subprocess.run(
        [str(solver), "--version"], text=True, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, check=False, timeout=10,
    )
    solver_version = version_result.stdout.strip() or f"version query exit={version_result.returncode}"
    parent_head, dirty = _git_state()
    run_id, run_dir = _reserve_run_id(ctx["config"]["CASE_NAME"], runs_dir)
    manifest = _write_run_files(
        run_id, run_dir, ctx, config_bytes, solver, solver_version,
        parent_head, dirty, run_mode,
    )
    log_path = run_dir / "run.log"
    with log_path.open("x", encoding="utf-8", newline="\n") as log:
        log.write(f"run_id={run_id}\n")
        log.write(f"run_mode={run_mode}\n")
        log.write(f"solver={solver}\n")
        log.write(f"solver_version_query={solver_version}\n")
        log.write(f"archive_preflight={message}\n")
        log.write(f"command={solver} -o raw.csv deck.cir\n")
        log.flush()
        manifest["status"] = "SOLVER_RUNNING"
        manifest["physical_solve_count"] = 1
        atomic_json(run_dir / "manifest.json", manifest)
        result = subprocess.run(
            [str(solver), "-o", "raw.csv", "deck.cir"],
            cwd=run_dir, stdout=log, stderr=subprocess.STDOUT, check=False,
        )
        log.flush()
        os.fsync(log.fileno())

    raw = run_dir / "raw.csv"
    if raw.exists():
        try:
            raw_integrity = _raw_integrity(raw, ctx["probes"])
        except PlatformError as exc:
            raw_integrity = {"status": "FAIL", "reason": str(exc)}
    else:
        raw_integrity = {"status": "FAIL", "reason": "raw.csv was not produced"}

    visualization: dict[str, Any] = {
        "status": "NOT_GENERATED_RAW_QA_FAILED",
        "res.html": None,
        "custom.html": None,
        "res_probe_labels": list(ctx["output_probes"]),
        "custom_probe_labels": list(ctx["custom_probes"]),
    }
    if raw_integrity.get("status") == "PASS":
        raw_sha_before_plot = raw_integrity["raw_sha256"]
        try:
            with log_path.open("a", encoding="utf-8", newline="\n") as log:
                res_qa = _plot(run_dir, ctx["output_probes"], "res.html", log)
                custom_qa = None
                if ctx["custom_probes"]:
                    custom_qa = _plot(run_dir, ctx["custom_probes"], "custom.html", log)
            raw_sha_after_plot = sha256_file(raw)
            if raw_sha_after_plot != raw_sha_before_plot:
                raise PlatformError("raw.csv SHA changed while rendering HTML")
            raw_integrity["sha256_unchanged_during_plot"] = True
            visualization = {
                "status": "PASS",
                "res.html": res_qa,
                "custom.html": custom_qa,
                "res_probe_labels": list(ctx["output_probes"]),
                "custom_probe_labels": list(ctx["custom_probes"]),
            }
        except (OSError, PlatformError) as exc:
            raw_integrity["sha256_after_plot_attempt"] = sha256_file(raw)
            raw_integrity["sha256_unchanged_during_plot"] = (
                raw_integrity["sha256_after_plot_attempt"] == raw_sha_before_plot
            )
            visualization = {
                "status": "FAIL",
                "reason": str(exc),
                "res.html": (
                    {"sha256": sha256_file(run_dir / "res.html")}
                    if (run_dir / "res.html").is_file() else None
                ),
                "custom.html": (
                    {"sha256": sha256_file(run_dir / "custom.html")}
                    if (run_dir / "custom.html").is_file() else None
                ),
                "res_probe_labels": list(ctx["output_probes"]),
                "custom_probe_labels": list(ctx["custom_probes"]),
            }

    if result.returncode != 0:
        status = "SOLVER_FAILURE_RAW_PRESERVED"
    elif raw_integrity.get("status") != "PASS":
        status = "RAW_ARTIFACT_INVALID"
    elif visualization.get("status") != "PASS":
        status = "POSTPROCESS_FAILURE_RAW_PRESERVED"
    else:
        status = "ARTIFACT_QA_PASS"

    _finalize_manifest(run_dir, manifest, status, result.returncode, raw_integrity, visualization)
    receipt: dict[str, Any] | None = None
    archive_error: str | None = None
    if not run_local:
        try:
            receipt = archive_completed_run(run_id, drive_target, runs_dir)
        except (OSError, PlatformError, zipfile.BadZipFile) as exc:
            archive_error = str(exc)

    summary = {
        "run_id": run_id,
        "run_dir": str(run_dir),
        "status": status,
        "solver_exit_code": result.returncode,
        "raw_sha256": raw_integrity.get("raw_sha256"),
        "run_mode": run_mode,
        "archive_receipt": str(run_dir / "archive_receipt.json") if receipt else None,
        "archive_status": receipt.get("cloud_sync_status") if receipt else (
            "NOT_REQUESTED" if run_local else "FAILED_OR_UNAVAILABLE"
        ),
        "archive_error": archive_error,
        "scientific_analysis_performed": False,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    artifact_ok = (
        result.returncode == 0
        and raw_integrity.get("status") == "PASS"
        and visualization.get("status") == "PASS"
    )
    if not artifact_ok:
        return 3
    if not run_local and receipt is None:
        return 4
    return 0


def _print_archive_receipt(receipt: dict[str, Any]) -> None:
    print(json.dumps({
        "archive_status": receipt["archive_status"],
        "zip_name": receipt["zip_name"],
        "zip_sha256": receipt["zip_sha256"],
        "manifest_sha256": receipt["manifest_sha256"],
        "manifest_bytes_identical_in_zip": receipt["manifest_bytes_identical_in_zip"],
        "drive_path": receipt["drive_path"],
        "drive_file_id": receipt["drive_file_id"],
        "cloud_sync_status": receipt["cloud_sync_status"],
        "scientific_analysis_performed": False,
    }, ensure_ascii=False, indent=2))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="render and mechanically validate only")
    mode.add_argument("--run-local", action="store_true", help="run once without DriveFS archive")
    mode.add_argument("--archive-run", metavar="RUN_ID", help="archive an existing completed run")
    args = parser.parse_args(argv)
    try:
        if args.archive_run:
            receipt = archive_completed_run(args.archive_run)
            _print_archive_receipt(receipt)
            return 0
        config, config_bytes = read_config()
        ctx = build_case(config)
        if args.dry_run:
            _print_dry_run(ctx)
            return 0
        return execute(ctx, config_bytes, run_local=args.run_local)
    except (PlatformError, OSError, ValueError, KeyError, json.JSONDecodeError, zipfile.BadZipFile) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
