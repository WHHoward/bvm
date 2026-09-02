#!/usr/bin/env python3
"""Build the three compact classic JoSIM visualizations for this Quick."""

from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
PLOTTER = REPO / "scripts/josim-plot2.py"

RAW = {
    "T100": EXP / "runs/T100/attempt-02/raw.csv",
    "T050": EXP / "runs/T050/attempt-01/raw.csv",
    "T025": EXP / "runs/T025/attempt-01/raw.csv",
    "T0125": EXP / "runs/T0125/attempt-01/raw.csv",
    "T100_FULL": EXP / "runs/T100_FULL/attempt-01/raw.csv",
}

sys.path.insert(0, str(REPO / "scripts"))
from bvmtools.raw import RawTrace, read_csv  # noqa: E402


def common_times(traces: dict[str, RawTrace], run_ids: list[str], bounds_ps: tuple[float, float]) -> list[float]:
    common = set(traces[run_ids[0]].time)
    for run_id in run_ids[1:]:
        common.intersection_update(traces[run_id].time)
    return [
        value
        for value in traces[run_ids[0]].time
        if value in common and bounds_ps[0] <= value * 1.0e12 < bounds_ps[1]
    ]


def write_projection(
    traces: dict[str, RawTrace],
    run_ids: list[str],
    signals: list[str],
    bounds_ps: tuple[float, float],
    name: str,
) -> Path:
    times = common_times(traces, run_ids, bounds_ps)
    if not times:
        raise RuntimeError(f"no exact common plot timestamps for {name}")
    indices = {
        run_id: {value: index for index, value in enumerate(traces[run_id].time)}
        for run_id in run_ids
    }
    output = EXP / "analysis/plot_inputs" / f"{name}.csv"
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        header = ["time"] + [f"{signal} [{run_id}]" for signal in signals for run_id in run_ids]
        writer.writerow(header)
        for time in times:
            row: list[float | str] = [time]
            for signal in signals:
                for run_id in run_ids:
                    row.append(traces[run_id].column(signal)[indices[run_id][time]])
            writer.writerow(row)
    print(f"projection {output} samples={len(times)}")
    return output


def render(input_csv: Path, output_html: Path, title: str) -> None:
    command = [
        sys.executable,
        str(PLOTTER),
        str(input_csv),
        "-x",
        str(output_html),
        "-t",
        "sep_comb",
        "-c",
        "dark",
        "-j",
        "2pi",
        "-w",
        title,
    ]
    completed = subprocess.run(command, cwd=REPO, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        raise SystemExit(
            f"plot2 failed ({completed.returncode}) for {output_html}:\n"
            f"{completed.stdout}\n{completed.stderr}"
        )
    print(f"plot {output_html} exit_code={completed.returncode}")


def main() -> int:
    traces = {run_id: read_csv(path) for run_id, path in RAW.items()}
    plots = [
        (
            "RESULT_TIMESTEP_BJ2",
            ["T100", "T050", "T025", "T0125"],
            ["P(BJ2|XBQ1)", "V(BJ2|XBQ1)"],
            (45.0, 200.0),
            "BVMSim Stage-A timestep Quick — BJ2 exact-grid overlay (phase / 2pi turns)",
        ),
        (
            "RESULT_TIMESTEP_JTL1",
            ["T100", "T050", "T025", "T0125"],
            [
                "P(B01|XJTL1_1)",
                "V(B01|XJTL1_1)",
                "P(B02|XJTL1_1)",
                "V(B02|XJTL1_1)",
            ],
            (45.0, 200.0),
            "BVMSim Stage-A timestep Quick — JTL1 B01/B02 4-turn vs 5-turn branch",
        ),
        (
            "RESULT_EVENT5_CANDIDATE_ORDER",
            ["T100", "T025"],
            [
                "P(BJS|XBQ1)",
                "V(BJS|XBQ1)",
                "P(BJ1|XBQ1)",
                "V(BJ1|XBQ1)",
                "P(BJ2|XBQ1)",
                "V(BJ2|XBQ1)",
                "P(B01|XJTL1_1)",
                "V(B01|XJTL1_1)",
                "P(B01|XJTL1_2)",
                "V(B01|XJTL1_2)",
                "P(B01|XJTL1_3)",
                "V(B01|XJTL1_3)",
                "P(B01|XJTL1_4)",
                "V(B01|XJTL1_4)",
                "P(B01|XJTL1_5)",
                "V(B01|XJTL1_5)",
                "P(B01|XJTL1_6)",
                "V(B01|XJTL1_6)",
                "P(B02|XJTL1_6)",
                "V(B02|XJTL1_6)",
            ],
            (120.0, 145.0),
            "BVMSim Stage-A timestep Quick — per-junction event #5 candidate ordering (120–145 ps; no causal origin)",
        ),
    ]
    for name, run_ids, signals, bounds_ps, title in plots:
        projection = write_projection(traces, run_ids, signals, bounds_ps, name)
        render(projection, EXP / "plots" / f"{name}.html", title)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
