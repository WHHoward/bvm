#!/usr/bin/env python3
"""Render compact PHASE-B plots with the repository's classic plot2 renderer."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Iterable


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
RENDERER = REPO / "scripts/josim-plot2.py"
STATES = ("0000", "1000", "0100", "0010", "0001", "1111")
WEIGHT_ONE_STATES = ("1000", "0100", "0010", "0001")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_once(path: Path, content: str) -> None:
    if path.exists():
        if path.read_text(encoding="utf-8") == content:
            return
        raise RuntimeError(f"refusing to overwrite plot data/index: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def raw_path(state: str) -> Path:
    return EXP / "runs" / state / "raw.csv"


def headers(path: Path) -> list[str]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return next(csv.reader(handle))


def write_derived(path: Path, labels: list[tuple[str, str]], state_list: Iterable[str]) -> None:
    states = list(state_list)
    times: list[str] | None = None
    rows_by_state: dict[str, list[list[str]]] = {}
    for state in states:
        source = raw_path(state)
        with source.open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.reader(handle)
            header = next(reader)
            positions = {name: index for index, name in enumerate(header)}
            for _, source_label in labels:
                if source_label not in positions:
                    raise RuntimeError(f"{source}: missing plot source label {source_label}")
            state_rows = list(reader)
        state_times = [row[0] for row in state_rows]
        if times is None:
            times = state_times
        elif state_times != times:
            raise RuntimeError(f"time grid mismatch for comparison source {state}")
        rows_by_state[state] = state_rows

    output_labels = [name for name, _ in labels]
    output_lines = ["time," + ",".join(output_labels)]
    for row_index in range(len(times or [])):
        values: list[str] = []
        for state in states:
            row = rows_by_state[state][row_index]
            header = headers(raw_path(state))
            positions = {name: index for index, name in enumerate(header)}
            values.extend(row[positions[source_label]] for _, source_label in labels if f"[{state}]" in _)
        # The state marker is encoded in each output label; the loop above
        # selects the matching state-specific source series in order.
        output_lines.append(",".join([times[row_index], *values]))
    write_once(path, "\n".join(output_lines) + "\n")


def write_comparison_csv(path: Path, series_by_state: list[tuple[str, list[tuple[str, str]]]]) -> list[str]:
    """Create a derived aligned CSV and return its output labels."""

    if not series_by_state:
        raise ValueError("comparison needs at least one state")
    source_states = [state for state, _ in series_by_state]
    source_rows: dict[str, tuple[list[str], list[list[str]], dict[str, int]]] = {}
    common_times: list[str] | None = None
    output: list[tuple[str, str, str]] = []
    for state, series in series_by_state:
        path_source = raw_path(state)
        with path_source.open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.reader(handle)
            header = next(reader)
            rows = list(reader)
        positions = {name: index for index, name in enumerate(header)}
        if any(source_label not in positions for _, source_label in series):
            missing = [source_label for _, source_label in series if source_label not in positions]
            raise RuntimeError(f"{path_source}: missing comparison labels {missing}")
        times = [row[0] for row in rows]
        if common_times is None:
            common_times = times
        elif times != common_times:
            raise RuntimeError(f"comparison time grid mismatch at state {state}")
        source_rows[state] = (times, rows, positions)
        output.extend((f"{kind} [{state}]", kind, source_label) for kind, source_label in series)

    lines = ["time," + ",".join(name for name, _, _ in output)]
    for row_index, time in enumerate(common_times or []):
        values = [
            source_rows[state][1][row_index][source_rows[state][2][source_label]]
            for state in source_states
            for name, kind, source_label in output
            if f"[{state}]" in name
        ]
        lines.append(",".join([time, *values]))
    write_once(path, "\n".join(lines) + "\n")
    return [name for name, _, _ in output]


def check_labels(path: Path, labels: Iterable[str]) -> None:
    available = set(headers(path))
    missing = [label for label in labels if label not in available]
    if missing:
        raise RuntimeError(f"{path}: missing labels {missing}")


def run_plot(input_path: Path, output_path: Path, title: str, labels: list[str]) -> dict[str, object]:
    check_labels(input_path, labels)
    command = [
        sys.executable,
        str(RENDERER),
        str(input_path),
        "-x",
        str(output_path),
        "-t",
        "sep_comb",
        "-c",
        "dark",
        "-j",
        "2pi",
        "-s",
        *labels,
        "-w",
        title,
    ]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not output_path.exists():
        completed = subprocess.run(command, cwd=REPO, text=True, capture_output=True)
        if completed.returncode != 0:
            raise RuntimeError(
                f"plot2 failed for {output_path}: exit={completed.returncode}\n"
                f"stdout={completed.stdout}\nstderr={completed.stderr}"
            )
    html = output_path.read_text(encoding="utf-8", errors="replace")
    if "<html" not in html.lower():
        raise RuntimeError(f"plot output is not HTML: {output_path}")
    if re.search(r'"title":\{"text":"Unknown"', html):
        raise RuntimeError(f"plot has an Unknown axis label: {output_path}")
    phase_check = any(label.startswith("P") for label in labels)
    # Plotly JSON escapes the slash as ``\\u002f`` in some versions, so use
    # the stable unit tokens rather than one literal serialization.
    phase_units_ok = ("Phase (turns)" in html and "2pi" in html) if phase_check else True
    if not phase_units_ok:
        raise RuntimeError(f"phase plot lacks rad/2pi unit label: {output_path}")
    return {
        "path": str(output_path.relative_to(REPO)),
        "sha256": digest(output_path),
        "input": str(input_path.relative_to(REPO)),
        "title": title,
        "labels": labels,
        "command": command,
        "phase_unit_check": "PASS" if phase_units_ok else "FAIL",
    }


def individual_specs() -> list[tuple[str, list[str], str]]:
    controls = [
        f"I(I_{control}{number})"
        for number in range(1, 5)
        for control in ("WL", "BL", "SE")
    ]
    bvm_state = [
        *(f"P(B_JM1|XBVM{number})" for number in range(1, 5)),
        *(f"P(B_JS1|XBVM{number})" for number in range(1, 5)),
        *(f"V(SL{number})" for number in range(1, 5)),
        *(f"I(L_SL|XBVM{number})" for number in range(1, 5)),
    ]
    bvm_pvi = [
        f"{kind}(B_JM1|XBVM{number})"
        for number in range(1, 5)
        for kind in ("P", "V", "I")
    ] + [
        f"{kind}(B_JS1|XBVM{number})"
        for number in range(1, 5)
        for kind in ("P", "V", "I")
    ]
    terminal = [
        "P(B_LD4_01)", "V(B_LD4_01)", "I(B_LD4_01)",
        "P(B_LD4_11)", "V(B_LD4_11)", "I(B_LD4_11)",
        "P(BVMOUT)", "V(BVMOUT)", "I(BVMOUT)",
        "V(QBIN)", "V(QBOUT)", "I(LIN|XBQ1)",
    ]
    qb = [
        "P(BJS|XBQ1)", "V(BJS|XBQ1)", "I(BJS|XBQ1)",
        "P(BJ1|XBQ1)", "V(BJ1|XBQ1)", "I(BJ1|XBQ1)",
        "P(BJ2|XBQ1)", "V(BJ2|XBQ1)", "I(BJ2|XBQ1)",
        "I(L1|XBQ1)", "I(IB|XBQ1)", "I(L2|XBQ1)", "I(L3|XBQ1)",
    ]
    jtl = [
        f"{kind}(B02|XJTL1_{stage})"
        for stage in range(1, 7)
        for kind in ("P", "V")
    ] + [
        f"{kind}(B01|XJTL1_{stage})"
        for stage in range(1, 7)
        for kind in ("P", "V")
    ]
    return [
        ("CONTROL_TIMING", controls, "control timing"),
        ("BVM_STATE", bvm_state, "BVM state and sensing-line observables"),
        ("BVM_INTERNAL_PVI", bvm_pvi, "BVM internal JM1/JS1 P/V/I observables"),
        ("BVMOUT_QB_INPUT", terminal, "BVMout and QB input/output"),
        ("QB_INTERNAL", qb, "QB internal observables"),
        ("JTL_TRANSPORT", jtl, "six-stage JTL P/V observables"),
    ]


def write_index(plot_records: list[dict[str, object]]) -> None:
    links = []
    for record in plot_records:
        path = str(record["path"])
        label = str(record["title"])
        links.append(f'<li><a href="{path.removeprefix(str(EXP.relative_to(REPO)) + "/plots/")}">{label}</a></li>')
    content = "<!doctype html>\n<html><head><meta charset=\"utf-8\"><title>PHASE B plots</title></head><body>\n"
    content += "<h1>PHASE B — six-state position closure plots</h1>\n<ul>\n"
    content += "\n".join(links)
    content += "\n</ul>\n<p>Phase panels use JoSIM rad/(2*pi) turns. Plots are descriptive; metrics.json is the analysis record.</p>\n</body></html>\n"
    write_once(EXP / "plots/INDEX.html", content)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default=str(EXP / "analysis/plot_manifest.json"))
    args = parser.parse_args()
    before = {state: digest(raw_path(state)) for state in STATES}
    records: list[dict[str, object]] = []
    for state in STATES:
        for name, labels, description in individual_specs():
            output = EXP / "plots/runs" / state / f"{name}.html"
            records.append(run_plot(raw_path(state), output, f"PHASE B {state} — {description}", labels))

    comparison_specs = [
        (
            "WEIGHT1_BVM_STATE_CLOSURE",
            [
                (state, [(f"P(B_JM1|XBVM{number})", f"P(B_JM1|XBVM{number})") for number in range(1, 5)])
                for state in WEIGHT_ONE_STATES
            ],
            "PHASE B weight-1 states — BVM JM1 state closure",
        ),
        (
            "WEIGHT1_BVMOUT_LIN",
            [
                (state, [("I(BVMOUT)", "I(BVMOUT)"), ("I(LIN|XBQ1)", "I(LIN|XBQ1)")])
                for state in WEIGHT_ONE_STATES
            ],
            "PHASE B weight-1 states — BVMout to QB input current",
        ),
        (
            "WEIGHT1_QBIN_QB_RESPONSE",
            [
                (state, [("V(QBIN)", "V(QBIN)"), ("P(BJ2|XBQ1)", "P(BJ2|XBQ1)"), ("V(BJ2|XBQ1)", "V(BJ2|XBQ1)")])
                for state in WEIGHT_ONE_STATES
            ],
            "PHASE B weight-1 states — QB input and BJ2 response",
        ),
        (
            "ALL_STATES_BJ2_JTL6",
            [
                (state, [("P(BJ2|XBQ1)", "P(BJ2|XBQ1)"), ("P(B02|XJTL1_6)", "P(B02|XJTL1_6)")])
                for state in STATES
            ],
            "PHASE B all selected states — QB to JTL6 phase",
        ),
    ]
    for name, state_series, title in comparison_specs:
        derived = EXP / "plots/comparison" / f"{name}.csv"
        labels = write_comparison_csv(derived, state_series)
        records.append(run_plot(derived, EXP / "plots/comparison" / f"{name}.html", title, labels))

    after = {state: digest(raw_path(state)) for state in STATES}
    if before != after:
        raise RuntimeError("raw hash changed during visualization")
    manifest = {
        "schema": "bvmsim-4bvm-six-state-plot-manifest-v1",
        "renderer": str(RENDERER.relative_to(REPO)),
        "renderer_sha256": digest(RENDERER),
        "layout": "sep_comb",
        "color": "dark",
        "phase_jump": "2pi",
        "individual_before_comparison": True,
        "raw_sha256_before": before,
        "raw_sha256_after": after,
        "raw_unchanged": before == after,
        "plots": records,
    }
    write_once(Path(args.manifest), json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    write_index(records)
    print(json.dumps({"plots": len(records), "raw_unchanged": before == after}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
