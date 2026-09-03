#!/usr/bin/env python3
"""Render one compact classic plot for each timestep-matrix member.

The raw CSV files are read only.  ``josim-plot2.py`` receives an explicit
subset so each page contains the small set of observables needed to inspect
the BVM -> QB -> JTL path, rather than the complete raw trace.
"""

from __future__ import annotations

import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
PLOTTER = REPO / "scripts/josim-plot2.py"


@dataclass(frozen=True)
class Run:
    run_id: str
    raw: Path
    timestep_ps: float
    output_start: str
    attempt: str


RUNS = (
    Run("T100", EXP / "runs/T100/attempt-02/raw.csv", 0.1, "45 ps", "attempt-02"),
    Run("T050", EXP / "runs/T050/attempt-01/raw.csv", 0.05, "0 ps", "attempt-01"),
    Run("T025", EXP / "runs/T025/attempt-01/raw.csv", 0.025, "0 ps", "attempt-01"),
    Run("T0125", EXP / "runs/T0125/attempt-01/raw.csv", 0.0125, "0 ps", "attempt-01"),
    Run("T100_FULL", EXP / "runs/T100_FULL/attempt-01/raw.csv", 0.1, "0 ps", "attempt-01"),
)

# Keep this list deliberately small: source current, QB output junction, and
# the first and last JTL stages.  P traces are converted by josim-plot2's
# ``-j 2pi`` option and are labelled there as rad/(2*pi) turns.
SIGNALS = (
    "I(BVMOUT)",
    "P(BJ2|XBQ1)",
    "V(BJ2|XBQ1)",
    "P(B01|XJTL1_1)",
    "V(B01|XJTL1_1)",
    "P(B02|XJTL1_6)",
    "V(B02|XJTL1_6)",
)

sys.path.insert(0, str(REPO / "scripts"))
from bvmtools.raw import read_csv  # noqa: E402


def validate_raw(run: Run):
    trace = read_csv(run.raw)
    duplicated = sorted(name for name in SIGNALS if name in trace.duplicate_columns)
    if duplicated:
        raise RuntimeError(
            f"{run.run_id}: selected labels are duplicated and cannot be passed "
            f"to josim-plot2 safely: {duplicated}"
        )
    missing = [name for name in SIGNALS if name not in trace.headers]
    if missing:
        raise RuntimeError(f"{run.run_id}: missing selected labels: {missing}")
    return trace


def normalize_html(path: Path) -> None:
    """Remove generator-only line-end whitespace without changing HTML data."""

    content = path.read_text(encoding="utf-8")
    normalized = "\n".join(line.rstrip() for line in content.splitlines()) + "\n"
    if normalized != content:
        path.write_text(normalized, encoding="utf-8")


def render(run: Run) -> Path:
    validate_raw(run)
    output = EXP / "plots" / f"RESULT_{run.run_id}.html"
    output.parent.mkdir(parents=True, exist_ok=True)
    title = (
        "BVMSim Stage-A timestep Quick — "
        f"{run.run_id} (dt={run.timestep_ps:g} ps; output from {run.output_start}) — "
        "key BVM/QB/JTL observables"
    )
    command = [
        sys.executable,
        str(PLOTTER),
        str(run.raw),
        "-s",
        *SIGNALS,
        "-t",
        "sep_comb",
        "-c",
        "dark",
        "-j",
        "2pi",
        "-x",
        str(output),
        "-w",
        title,
    ]
    completed = subprocess.run(command, cwd=REPO, capture_output=True, text=True, check=False)
    if completed.returncode != 0 or not output.is_file() or output.stat().st_size == 0:
        raise RuntimeError(
            f"{run.run_id}: plot failed with exit code {completed.returncode}\n"
            f"stdout: {completed.stdout}\n"
            f"stderr: {completed.stderr}"
        )
    normalize_html(output)
    print(f"{run.run_id}: exit_code=0 samples={validate_raw(run).sample_count}")
    print("  " + shlex.join(command))
    print(f"  output={output} bytes={output.stat().st_size}")
    return output


def main() -> int:
    for run in RUNS:
        render(run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
