#!/usr/bin/env python3
"""Add reproducible registered stimulus plots without touching raw solver output."""

from __future__ import annotations

import csv
import hashlib
import html
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = next(path for path in (ROOT, *ROOT.parents) if (path / ".git").exists())
PLOTTER = REPO / "scripts" / "josim-plot2.py"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def parse_value(token: str) -> float:
    match = re.fullmatch(r"([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)([munpfk]?)", token.strip(), re.I)
    if not match:
        raise ValueError(token)
    scale = {"": 1.0, "m": 1e-3, "u": 1e-6, "n": 1e-9, "p": 1e-12, "f": 1e-15, "k": 1e3}
    return float(match.group(1)) * scale[match.group(2).lower()]


def parse_pwl(path: Path) -> dict[str, list[tuple[float, float]]]:
    result: dict[str, list[tuple[float, float]]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^(I_[A-Za-z0-9_]+|V_[A-Za-z0-9_]+)\s+[^ ]+\s+[^ ]+\s+pwl\((.*)\)\s*$", line.strip(), re.I)
        if not match:
            continue
        source = match.group(1)
        tokens = match.group(2).split()
        if len(tokens) % 2:
            continue
        points = [(parse_value(tokens[i]), parse_value(tokens[i + 1])) for i in range(0, len(tokens), 2)]
        result[source] = points
    return result


def derived_trace(stimulus: Path, output: Path) -> tuple[list[str], str]:
    parsed = parse_pwl(stimulus)
    if not parsed:
        raise RuntimeError(f"no PWL sources found in {stimulus}")
    times = sorted({time for points in parsed.values() for time, _value in points})
    sources = sorted(parsed)
    output.parent.mkdir(parents=True, exist_ok=True)
    headers = ["time"] + [(f"V({name[2:]})" if name.startswith("V_") else f"I({name})") for name in sources]
    with output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(headers)
        for time in times:
            row = [f"{time:.16e}"]
            for source in sources:
                value = 0.0
                for point_time, point_value in parsed[source]:
                    if point_time <= time:
                        value = point_value
                    else:
                        break
                row.append(f"{value:.16e}")
            writer.writerow(row)
    return sources, sha256(output)


def raw_headers(raw: Path) -> list[str]:
    with raw.open("r", encoding="utf-8", newline="") as stream:
        return next(csv.reader(stream))


def plot(input_path: Path, output: Path, title: str, signals: list[str]) -> dict:
    output.parent.mkdir(parents=True, exist_ok=True)
    command = [sys.executable, str(PLOTTER), str(input_path), "-x", str(output), "-t", "sep_comb", "-c", "dark", "-j", "2pi", "-w", title, "-s", *signals]
    completed = subprocess.run(command, cwd=REPO, capture_output=True, text=True, check=False)
    (output.parent / (output.stem + ".stdout.txt")).write_text(completed.stdout, encoding="utf-8")
    (output.parent / (output.stem + ".stderr.txt")).write_text(completed.stderr, encoding="utf-8")
    return {"status": "PASS" if completed.returncode == 0 and output.is_file() else "FAIL", "input": str(input_path.relative_to(ROOT)), "output": str(output.relative_to(ROOT)), "signals": signals, "input_sha256": sha256(input_path), "command": command}


def run_one(run_dir: Path) -> dict:
    stimulus = run_dir / "stimulus.inc"
    raw = run_dir / "raw.csv"
    out_dir = run_dir / "plots" / "stimulus"
    entries = []
    source_hash = sha256(stimulus) if stimulus.is_file() else None
    direct_headers = raw_headers(raw) if raw.is_file() else []
    groups = {group: sorted([header for header in direct_headers if re.fullmatch(rf'I\(I_{group}\d+\)', header)], key=lambda item: int(re.search(r"(\d+)", item).group(1))) for group in ("WL", "BL", "SE")}
    if raw.is_file():
        for group, signals in groups.items():
            if signals:
                entries.append(plot(raw, out_dir / f"stimulus_{group}.html", f"Registered stimulus {group} — {run_dir.name}", signals) | {"origin": "raw.csv", "label": f"I(I_{group}*) direct solver output"})
    if not all(groups.values()):
        trace = out_dir / "stimulus_definition.csv"
        sources, trace_hash = derived_trace(stimulus, trace)
        for group, signals in (("WL", [f"I(I_WL{name[4:]})" for name in sources if name.startswith("I_WL")]), ("BL", [f"I(I_BL{name[4:]})" for name in sources if name.startswith("I_BL")]), ("SE", [f"I(I_SE{name[4:]})" for name in sources if name.startswith("I_SE")]), ("MERGE_INPUT", [f"V({name[2:]})" for name in sources if name.startswith("V_IN")])):
            signals = [signal for signal in signals if signal in raw_headers(trace)]
            if signals:
                entries.append(plot(trace, out_dir / f"stimulus_definition_{group}.html", f"Registered PWL stimulus definition {group} — {run_dir.name}", signals) | {"origin": "stimulus.inc PWL definition", "label": "source definition; not solver raw", "stimulus_sha256": source_hash, "derived_trace_sha256": trace_hash})
    qa = {"schema": "bvm-qb-50ghz-stimulus-plot-qa-v1", "status": "PASS" if entries and all(item["status"] == "PASS" for item in entries) else "FAIL", "run_id": run_dir.name, "source_stimulus": str(stimulus.relative_to(ROOT)), "source_stimulus_sha256": source_hash, "raw_sha256": sha256(raw) if raw.is_file() else None, "entries": entries, "raw_untouched": True, "descriptive_only": True}
    (run_dir / "qa" / "stimulus_plot_qa.json").parent.mkdir(parents=True, exist_ok=True)
    (run_dir / "qa" / "stimulus_plot_qa.json").write_text(json.dumps(qa, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (run_dir / "analysis" / "stimulus_plot_manifest.json").parent.mkdir(parents=True, exist_ok=True)
    (run_dir / "analysis" / "stimulus_plot_manifest.json").write_text(json.dumps({"schema": "bvm-qb-50ghz-stimulus-plot-manifest-v1", "run_id": run_dir.name, "entries": entries, "origin_note": "Raw source-current plots are direct CSV tracks. MERGE input plots are exact registered PWL definitions because INA/INB were not requested in raw probes."}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return qa


def main() -> int:
    run_dirs = []
    for phase in ("phase_a_repeated_read", "phase_b_rewrite_read", "phase_c_merge_collision", "phase_d_4bvm_merge_integration"):
        root = ROOT / phase
        if root.is_dir():
            run_dirs.extend(path for path in sorted((root / "runs").glob("*")) if path.is_dir() and (path / "stimulus.inc").is_file())
    results = [run_one(run_dir) for run_dir in run_dirs]
    summary = {"schema": "bvm-qb-50ghz-stimulus-viz-summary-v1", "status": "PASS" if results and all(item["status"] == "PASS" for item in results) else "FAIL", "run_count": len(results), "stimulus_plots_added": sum(len(item["entries"]) for item in results), "scientific_interpretation_performed": False, "raw_immutable": True, "runs": results}
    (ROOT / "analysis" / "STIMULUS_VIZ_QA.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    index_dir = ROOT / "plots"
    index_dir.mkdir(parents=True, exist_ok=True)
    rows = ["<!doctype html><html><head><meta charset='utf-8'><title>Stimulus visualization index</title><style>body{font-family:sans-serif}table{border-collapse:collapse}td,th{border:1px solid #bbb;padding:4px}code{white-space:nowrap}</style></head><body>", f"<h1>{html.escape(ROOT.name)} — registered stimulus plots</h1>", "<p>Raw source-current plots are direct CSV tracks. MERGE input plots are exact PWL source definitions because INA/INB were not requested in raw probes. Descriptive only.</p>", "<table><tr><th>phase</th><th>run</th><th>origin</th><th>signals</th><th>plot</th></tr>"]
    for result in results:
        for entry in result["entries"]:
            target = Path(entry["output"])
            href = Path("..").joinpath(target).as_posix()
            rows.append(f"<tr><td>{html.escape(result['run_id'].split('/')[0])}</td><td><code>{html.escape(result['run_id'])}</code></td><td>{html.escape(entry.get('origin',''))}</td><td>{html.escape(', '.join(entry.get('signals', [])))}</td><td><a href='{html.escape(href)}'>open</a></td></tr>")
    rows.extend(["</table></body></html>", ""])
    (index_dir / "STIMULUS_INDEX.html").write_text("\n".join(rows), encoding="utf-8")
    print(json.dumps({"status": summary["status"], "run_count": summary["run_count"], "stimulus_plots_added": summary["stimulus_plots_added"]}, ensure_ascii=False, indent=2))
    return 0 if summary["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
