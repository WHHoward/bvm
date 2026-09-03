"""Static deck and raw-header QA for JoSIM experiments.

Only artifact/topology/model/probe checks belong here. Scientific functional
verdicts remain in each experiment's analyzer.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable, Sequence


def _include_tokens(text: str) -> tuple[str, ...]:
    return tuple(
        match.group(1).strip().strip('"')
        for match in re.finditer(r"(?mi)^\s*\.include\s+([^\s]+)", text)
    )


def _include_matches(tokens: Sequence[str], expected: str | Path) -> bool:
    suffix = Path(str(expected)).as_posix().lstrip("./")
    return any(
        token.replace("\\", "/").lstrip("./").endswith(suffix)
        for token in tokens
    )


def _tran_step_ps(text: str) -> float | None:
    match = re.search(r"(?mi)^\s*\.tran\s+([0-9.eE+-]+)p\b", text)
    return None if match is None else float(match.group(1))


def deck_qa(
    deck_path: str | Path,
    *,
    log_text: str = "",
    expected_includes: Iterable[str | Path] = (),
    expected_bvm_instances: int | None = None,
    expected_terminal_sensing_jj_count: int | None = None,
    expected_jtl_stages: int | None = None,
    expected_termination_ohm: float | None = None,
    expected_tran_timestep_ps: float | None = None,
    required_probes: Iterable[str] = (),
    raw_headers: Sequence[str] | None = None,
) -> dict[str, object]:
    """Return structured static QA without assigning a physical verdict."""

    path = Path(deck_path)
    text = path.read_text(encoding="utf-8")
    tokens = _include_tokens(text)
    bvm_instances = sorted(
        {
            int(match.group(1))
            for match in re.finditer(r"(?mi)^\s*XBVM(\d+)\s+", text)
        }
    )
    terminal_lines = re.findall(r"(?mi)^\s*B_LD4_\d{2}\s+", text)
    bvmout_lines = re.findall(r"(?mi)^\s*BVMout\s+", text)
    terminal_count = len(terminal_lines) + len(bvmout_lines)
    jtl_stages = sorted(
        {
            int(match.group(1))
            for match in re.finditer(r"(?mi)^\s*xjtl1_(\d+)\s+", text)
        }
    )
    qb_match = re.search(
        r"(?mi)^\s*xBQ1\s+QBin\s+QBout\s+(\S+)\s*$", text
    )
    termination_match = re.search(
        r"(?mi)^\s*RBQ1\s+\S+\s+0\s+([0-9.eE+-]+)\s*$", text
    )
    warning = bool(re.search(r"Missing model:|Using default model", log_text, re.I))
    tran_step = _tran_step_ps(text)
    missing_includes = [
        str(expected)
        for expected in expected_includes
        if not _include_matches(tokens, expected)
    ]
    missing_probes = [probe for probe in required_probes if probe not in text]
    raw_missing: list[str] = []
    duplicate_headers: dict[str, int] = {}
    if raw_headers is not None:
        for probe in required_probes:
            if probe not in raw_headers:
                raw_missing.append(probe)
        for header in set(raw_headers):
            count = raw_headers.count(header)
            if count > 1:
                duplicate_headers[header] = count

    topology_issues: list[str] = []
    if expected_bvm_instances is not None and len(bvm_instances) != expected_bvm_instances:
        topology_issues.append("BVM_INSTANCE_COUNT")
    if (
        expected_terminal_sensing_jj_count is not None
        and terminal_count != expected_terminal_sensing_jj_count
    ):
        topology_issues.append("TERMINAL_SENSING_JJ_COUNT")
    if (
        expected_jtl_stages is not None
        and jtl_stages != list(range(1, expected_jtl_stages + 1))
    ):
        topology_issues.append("JTL_STAGE_COUNT")
    if expected_termination_ohm is not None:
        if termination_match is None or float(termination_match.group(1)) != float(expected_termination_ohm):
            topology_issues.append("TERMINATION")
    timestep_issue = (
        expected_tran_timestep_ps is not None
        and (tran_step is None or tran_step != float(expected_tran_timestep_ps))
    )

    if warning or missing_includes:
        status = "MODEL_CLOSURE_FAIL"
    elif topology_issues:
        status = "TOPOLOGY_MISMATCH"
    elif timestep_issue:
        status = "TIMESTEP_MISMATCH"
    elif missing_probes:
        status = "MISSING_PROBE"
    elif raw_missing or duplicate_headers:
        status = "RAW_HEADER_MISMATCH"
    else:
        status = "ARTIFACT_VALID"

    return {
        "status": status,
        "deck_path": str(path),
        "include_tokens": list(tokens),
        "missing_includes": missing_includes,
        "model_warning_detected": warning,
        "bvm_instances": bvm_instances,
        "terminal_device_line_count": len(terminal_lines),
        "terminal_bvmout_line_count": len(bvmout_lines),
        "terminal_sensing_jj_count": terminal_count,
        "jtl_stages": jtl_stages,
        "qb_subcircuit": qb_match.group(1) if qb_match else None,
        "termination_ohm": float(termination_match.group(1)) if termination_match else None,
        "requested_tran_timestep_ps": tran_step,
        "topology_issues": topology_issues,
        "missing_probes": missing_probes,
        "raw_missing_probes": raw_missing,
        "raw_duplicate_columns": duplicate_headers,
    }
