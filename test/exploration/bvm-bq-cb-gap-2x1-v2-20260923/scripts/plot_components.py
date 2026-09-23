#!/usr/bin/env python3
"""Add full-run, component-family plots from the immutable four-case raw set."""

from __future__ import annotations

import argparse
import csv
import html
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

from common import ROOT, cases, current_head, read_json, run_dir, sha256, write_json
from plot_run import PLOT_ROOT, headers_and_rows, render_one

MANIFEST_PATH = ROOT / "analysis" / "component_plot_manifest_v1.json"
QA_PATH = ROOT / "qa" / "component_plot_qa_v1.json"
INDEX_PATH = PLOT_ROOT / "component_views" / "index.html"
COMPONENTS = ("BVM", "QB", "CB", "ACC", "GAP")


def add_junctions(signals: list[str], instance: str, junctions: tuple[str, ...]) -> None:
    for junction in junctions:
        signals.extend(f"{quantity}({junction}|{instance})" for quantity in ("P", "V", "I"))


def component_signals() -> dict[str, list[str]]:
    """Use selected internal device probes plus their registered boundary nodes."""
    bvm = [f"I({source})" for source in
           ("I_WL1", "I_BL1", "I_SE1", "I_WL2", "I_BL2", "I_SE2")]
    for number in (1, 2):
        instance = f"XBVM{number}"
        add_junctions(bvm, instance, ("B_JM1", "B_JM2", "B_JS1", "B_JS2"))
        bvm.extend(f"I({branch}|{instance})" for branch in
                   ("L_M1", "L_M2", "L_M3", "L_PM"))
        bvm.append(f"V(BVM{number}_SL)")

    qb: list[str] = []
    cb: list[str] = []
    acc: list[str] = []
    gap: list[str] = []
    for number in (1, 2):
        q = f"XBQ{number}"
        add_junctions(qb, q, ("BJ1", "BJ2", "BJ3"))
        qb.extend(f"I({branch}|{q})" for branch in ("Lin", "L1", "L2", "L3"))
        qb.extend(f"I({branch}|{q})" for branch in ("RJ1", "RJ2", "RJ3"))
        qb.append(f"I(IB2|{q})")
        qb.extend((f"V(BVM{number}_SL)", f"V(QB{number}_OUT)"))

        c = f"XCB{number}"
        add_junctions(cb, c, ("BJ1", "BJ2"))
        cb.extend(f"I({branch}|{c})" for branch in ("L1", "L2", "L3", "L4", "RJ1"))
        cb.append(f"I(IB1|{c})")
        cb.extend((f"V(QB{number}_OUT)", f"V(CB{number}_OUT)"))

        a = f"XACC{number}"
        add_junctions(acc, a, ("BJ1",))
        acc.extend(f"I({branch}|{a})" for branch in ("L1", "L2", "RJ1"))
        acc.append(f"I(IB1|{a})")
        acc.append(f"V(CB{number}_OUT)")
        acc.append("V(ACC1_OUT)" if number == 1 else "V(GAP2_IN)")

        g = f"XGAP{number}"
        add_junctions(gap, g, ("BJ1",))
        gap.extend(f"I({branch}|{g})" for branch in ("L1", "L2", "RJ1"))
        gap.append(f"I(IB1|{g})")

    gap.extend(("V(ACC1_OUT)", "V(GAP2_IN)", "V(FINAL_OUT)", "V(R_TERM)", "I(R_TERM)"))
    result = {"BVM": bvm, "QB": qb, "CB": cb, "ACC": acc, "GAP": gap}
    for name, signals in result.items():
        if len(signals) != len(set(signal.casefold() for signal in signals)):
            raise ValueError(f"duplicate signal requested in {name}: {signals}")
    return result


def verify_header(raw: Path, signals: list[str]) -> dict[str, Any]:
    with raw.open("r", encoding="utf-8", newline="") as stream:
        fields = next(csv.reader(stream), [])
    if not fields or fields[0].casefold() != "time":
        raise ValueError(f"raw has no leading time column: {raw}")
    folded = [field.casefold() for field in fields]
    if len(folded) != len(set(folded)):
        raise ValueError(f"raw headers collide under case normalization: {raw}")
    available = set(folded)
    missing = [signal for signal in signals if signal.casefold() not in available]
    if missing:
        raise ValueError(f"raw lacks component-view probes in {raw}: {missing}")
    return {signal: fields[folded.index(signal.casefold())]
            for signal in signals if signal != fields[folded.index(signal.casefold())]}


def output_paths(run_ids: list[str], specs: dict[str, list[str]]) -> list[Path]:
    paths = [MANIFEST_PATH, QA_PATH, INDEX_PATH]
    paths.extend(PLOT_ROOT / run_id / f"component_{name}__full.html"
                 for run_id in run_ids for name in COMPONENTS if name in specs)
    return paths


def write_index(entries: list[dict[str, Any]], mask_by_run: dict[str, str]) -> None:
    entry_by_pair = {(item["run_id"], item["component"]): item for item in entries}
    rows = []
    for run_id in mask_by_run:
        links = []
        for component in COMPONENTS:
            item = entry_by_pair[(run_id, component)]
            rel = os.path.relpath(ROOT / item["path"], INDEX_PATH.parent)
            links.append(f"<a href='{html.escape(rel)}'>{component}</a>")
        rows.append(
            "<tr><th>" + html.escape(run_id) + "</th><td>" + html.escape(mask_by_run[run_id]) +
            "</td>" + "".join(f"<td>{link}</td>" for link in links) + "</tr>"
        )
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    INDEX_PATH.write_text(
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<title>Full-run component views</title>"
        "<style>body{font:16px Arial,sans-serif;background:#111;color:#eee;margin:28px}"
        "a{color:#8ecbff}table{border-collapse:collapse}th,td{padding:10px;border:1px solid #555}"
        "</style></head><body><h1>BVM → BQ → CB → ACC → GAP — full-run component views</h1>"
        "<p>Each link shows the complete stored run (0–199.99 ps; no stage cropping,"
        " interpolation, or resampling). All waveform figures are rendered by the classic"
        " josim-plot2.py with sep_comb / dark / -j 2pi. Raw P is radians; phase turns are"
        " navigation only, not SFQ counts. Descriptive visualization only.</p>"
        "<table><thead><tr><th>Run</th><th>READ mask</th>" +
        "".join(f"<th>{name}</th>" for name in COMPONENTS) +
        "</tr></thead><tbody>" + "\n".join(rows) + "</tbody></table></body></html>\n",
        encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Render full-run component-family classic plots")
    parser.add_argument("--dry-run", action="store_true", help="validate probes and destinations only")
    parser.add_argument("--run", action="append", dest="run_ids", help="registered run ID; repeatable")
    args = parser.parse_args()

    registered = cases()
    selected = set(args.run_ids or [item["run_id"] for item in registered])
    unknown = selected - {item["run_id"] for item in registered}
    if unknown:
        raise ValueError(f"unregistered run IDs: {sorted(unknown)}")
    run_ids = [item["run_id"] for item in registered if item["run_id"] in selected]
    specs = component_signals()
    if set(specs) != set(COMPONENTS):
        raise ValueError("component family definitions are incomplete")

    mask_by_run: dict[str, str] = {}
    raw_hashes: dict[str, str] = {}
    sample_counts: dict[str, int] = {}
    aliases: dict[str, dict[str, dict[str, str]]] = {}
    for run_id in run_ids:
        directory = run_dir(run_id)
        raw = directory / "raw.csv"
        metadata = read_json(directory / "metadata.json")
        raw_qa = read_json(directory / "analysis" / "raw_qa.json")
        actual_hash = sha256(raw)
        if metadata.get("raw", {}).get("sha256") != actual_hash:
            raise ValueError(f"metadata raw hash mismatch: {run_id}")
        if raw_qa.get("status") != "PASS" or raw_qa.get("raw_sha256_after") != actual_hash:
            raise ValueError(f"existing raw QA/hash is not PASS: {run_id}")
        if (raw_qa.get("sample_count", 0) < 2 or raw_qa.get("time_start_ps") != 0 or
                raw_qa.get("time_end_ps", 0) < 199.99):
            raise ValueError(f"raw does not cover the complete registered stored run: {run_id}")
        raw_hashes[run_id] = actual_hash
        sample_counts[run_id] = int(raw_qa["sample_count"])
        mask_by_run[run_id] = str(metadata["parameters"]["MASK"])
        aliases[run_id] = {name: verify_header(raw, signals) for name, signals in specs.items()}

    targets = output_paths(run_ids, specs)
    collisions = [path.as_posix() for path in targets if path.exists()]
    if collisions:
        raise FileExistsError(f"refusing to overwrite existing component-view artifacts: {collisions}")
    if args.dry_run:
        print(json.dumps({"status": "DRY_RUN_PASS", "runs": run_ids,
                          "signal_count_per_component": {name: len(specs[name]) for name in COMPONENTS},
                          "only_window": "full stored run [0, 200 ps)",
                          "expected_html_count": len(run_ids) * len(COMPONENTS),
                          "outputs": [path.relative_to(ROOT).as_posix() for path in targets]},
                         ensure_ascii=False, indent=2))
        return 0

    package_qa = read_json(ROOT / "handoff" / "PACKAGE_QA.json")
    if package_qa.get("status") != "PASS":
        raise ValueError("parent canonical PACKAGE_QA is not PASS")
    entries: list[dict[str, Any]] = []
    run_records = []
    for run_id in run_ids:
        before = sha256(run_dir(run_id) / "raw.csv")
        run_entries = []
        for component in COMPONENTS:
            entry = render_one(run_id, run_dir(run_id) / "raw.csv", before,
                               f"component_{component}", specs[component], "full", None)
            entry["component"] = component
            entry["instances_grouped"] = {
                "BVM": ["XBVM1", "XBVM2"], "QB": ["XBQ1", "XBQ2"],
                "CB": ["XCB1", "XCB2"], "ACC": ["XACC1", "XACC2"],
                "GAP": ["XGAP1", "XGAP2"],
            }[component]
            entry["excitation_and_component_boundaries_same_classic_plot"] = True
            entry["stored_time_coverage_ps"] = [entry["actual_first_sample_ps"],
                                                 entry["actual_last_sample_ps"]]
            entry["only_full_run_view"] = True
            run_entries.append(entry)
        after = sha256(run_dir(run_id) / "raw.csv")
        if after != before:
            raise RuntimeError(f"raw changed while plotting {run_id}")
        for item in run_entries:
            page = ROOT / item["path"]
            content = page.read_text(encoding="utf-8", errors="replace")
            if any(token in content for token in ("plotly.js v", "var Plotly=", "cdn.plot.ly")):
                raise RuntimeError(f"classic Plotly runtime not externalized: {page}")
            if "unknown" in content.casefold():
                raise RuntimeError(f"Unknown axis/label in component plot: {page}")
            if item["sample_count"] != sample_counts[run_id] or item["raw_sha256"] != after:
                raise RuntimeError(f"component plot is not full-run/raw-bound: {page}")
            if item["window"] != "full" or item["window_ps"] != [0, 200]:
                raise RuntimeError(f"unexpected cropped view: {page}")
        entries.extend(run_entries)
        run_records.append({"run_id": run_id, "mask": mask_by_run[run_id],
                            "raw_sha256_before_after": before,
                            "sample_count": sample_counts[run_id], "component_plot_count": len(run_entries),
                            "header_aliases": aliases[run_id]})

    write_index(entries, mask_by_run)
    qa = {"schema": "bvm-bq-cb-gap-component-plot-qa-v1", "status": "PASS",
          "source_head": current_head(),
          "parent_package_sha256": package_qa["package_sha256"],
          "runs": run_records, "plot_count": len(entries),
          "components": list(COMPONENTS), "only_full_run_views": True,
          "full_raw_sample_count_per_run": {run_id: sample_counts[run_id] for run_id in run_ids},
          "renderer": "scripts/josim-plot2.py", "plot_type": "sep_comb",
          "theme": "dark", "phase_display": "raw P radians; -j 2pi navigation only",
          "raw_unchanged": True, "interpolation": False, "resampling": False,
          "scientific_interpretation_performed": False,
          "index_path": INDEX_PATH.relative_to(ROOT).as_posix()}
    manifest = {"schema": "bvm-bq-cb-gap-component-plot-manifest-v1",
                "source_head": current_head(),
                "parent_package_sha256": package_qa["package_sha256"],
                "renderer": "scripts/josim-plot2.py", "style": "sep_comb/dark/-j 2pi",
                "raw_unchanged": True, "interpolation": False, "resampling": False,
                "only_full_run_views": True, "index_path": qa["index_path"],
                "entries": entries}
    write_json(MANIFEST_PATH, manifest)
    write_json(QA_PATH, qa)
    print(json.dumps(qa, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
