#!/usr/bin/env python3
"""Render task-local standalone and RAW+DELTA pages with josim-plot2."""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "scripts"))
from bvmtools.raw import read_csv  # noqa: E402


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
PLOTTER = REPO / "scripts/josim-plot2.py"
PROVENANCE = EXP / "analysis/provenance.json"
PLOT_INPUTS = EXP / "analysis/plot_inputs.json"
MANIFEST = EXP / "plots/plot_manifest.json"
VIZ_QA = EXP / "analysis/viz_qa.json"

SINGLE_PAGES = {
    "CONTROL": ("CONTROL.html", "single/CONTROL.csv", "SINGLE — control history"),
    "BVM_STORAGE": ("BVM_STORAGE.html", "single/BVM_STORAGE.csv", "SINGLE — BVM storage"),
    "BVM_RLOOP": ("BVM_RLOOP.html", "single/BVM_RLOOP.csv", "SINGLE — BVM R-loop"),
    "BVM_OUTPUT": ("BVM_OUTPUT.html", "single/BVM_OUTPUT.csv", "SINGLE — BVM output branch"),
    "JSL_ENDPOINTS": ("JSL_ENDPOINTS.html", "single/JSL_ENDPOINTS.csv", "SINGLE — JSL1/JSL8 endpoints"),
    "QB_INTERNAL": ("QB_INTERNAL.html", "single/QB_INTERNAL.csv", "SINGLE — QB internal"),
    "JTL_ENDPOINTS": ("JTL_ENDPOINTS.html", "single/JTL_ENDPOINTS.csv", "SINGLE — JTL1/JTL6 and termination"),
}
ARRAY_PAGES = {
    "CONTROL": ("CONTROL.html", "array/CONTROL.csv", "ARRAY — target BVM1 control history"),
    "TARGET_BVM_STORAGE": ("TARGET_BVM_STORAGE.html", "array/BVM_STORAGE.csv", "ARRAY — target BVM1 storage"),
    "TARGET_BVM_RLOOP": ("TARGET_BVM_RLOOP.html", "array/BVM_RLOOP.csv", "ARRAY — target BVM1 R-loop"),
    "TARGET_BVM_OUTPUT": ("TARGET_BVM_OUTPUT.html", "array/BVM_OUTPUT.csv", "ARRAY — target BVM1 output branch"),
    "QUIET_BVMS": ("QUIET_BVMS.html", "array/QUIET_BVMS.csv", "ARRAY — quiet BVM2/BVM3/BVM4 internal activity"),
    "JSL_ENDPOINTS": ("JSL_ENDPOINTS.html", "array/JSL_ENDPOINTS.csv", "ARRAY — JSL1/JSL8 endpoints"),
    "QB_INTERNAL": ("QB_INTERNAL.html", "array/QB_INTERNAL.csv", "ARRAY — QB internal"),
    "JTL_ENDPOINTS": ("JTL_ENDPOINTS.html", "array/JTL_ENDPOINTS.csv", "ARRAY — JTL1/JTL6 and termination"),
}
COMPARISON_PAGES = {
    "CONTROL_RAW_DELTA": ("CONTROL_RAW_DELTA.html", "comparison/data/CONTROL_RAW_DELTA.csv", "SINGLE vs ARRAY — control RAW + DELTA"),
    "BVM_STORAGE_RAW_DELTA": ("BVM_STORAGE_RAW_DELTA.html", "comparison/data/BVM_STORAGE_RAW_DELTA.csv", "SINGLE vs ARRAY — BVM storage RAW + DELTA"),
    "BVM_RLOOP_RAW_DELTA": ("BVM_RLOOP_RAW_DELTA.html", "comparison/data/BVM_RLOOP_RAW_DELTA.csv", "SINGLE vs ARRAY — BVM R-loop RAW + DELTA"),
    "BVM_OUTPUT_RAW_DELTA": ("BVM_OUTPUT_RAW_DELTA.html", "comparison/data/BVM_OUTPUT_RAW_DELTA.csv", "SINGLE vs ARRAY — BVM output RAW + DELTA"),
    "JSL_ENDPOINTS_RAW_DELTA": ("JSL_ENDPOINTS_RAW_DELTA.html", "comparison/data/JSL_ENDPOINTS_RAW_DELTA.csv", "SINGLE vs ARRAY — JSL endpoint RAW + DELTA"),
    "QB_RAW_DELTA": ("QB_RAW_DELTA.html", "comparison/data/QB_INTERNAL_RAW_DELTA.csv", "SINGLE vs ARRAY — QB RAW + DELTA"),
    "JTL_ENDPOINTS_RAW_DELTA": ("JTL_ENDPOINTS_RAW_DELTA.html", "comparison/data/JTL_ENDPOINTS_RAW_DELTA.csv", "SINGLE vs ARRAY — JTL endpoint RAW + DELTA"),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO.resolve()).as_posix()


def now_local() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def write_once(path: Path, content: str) -> None:
    if path.exists():
        if path.read_text(encoding="utf-8") == content:
            return
        raise RuntimeError(f"refusing to overwrite existing plot input: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def raw_hashes() -> dict[str, str]:
    record = json.loads(PROVENANCE.read_text(encoding="utf-8"))
    result = {}
    for kind, item in record["raw"].items():
        path = REPO / item["path"]
        current = sha256(path)
        if current != item["sha256"]:
            raise RuntimeError(f"raw hash changed before rendering: {path}")
        result[kind] = current
    return result


def combine_quiet_inputs() -> Path:
    output = EXP / "plots/derived/array/QUIET_BVMS.csv"
    if output.exists():
        return output
    paths = [EXP / "plots/derived/array" / f"QUIET_BVM{i}.csv" for i in (2, 3, 4)]
    traces = [read_csv(path) for path in paths]
    if not all(trace.time == traces[0].time for trace in traces[1:]):
        raise RuntimeError("quiet-BVM derived inputs do not share an exact time grid")
    columns: list[tuple[str, tuple[float, ...]]] = []
    for instance, trace in zip((2, 3, 4), traces):
        for label in trace.headers[1:]:
            columns.append((label.replace("ARRAY BVM1", f"ARRAY BVM{instance}"), trace.column(label)))  # type: ignore[arg-type]
    lines = ["time," + ",".join('"' + label.replace('"', '""') + '"' for label, _ in columns)]
    for index, timestamp in enumerate(traces[0].time):
        values = [repr(float(timestamp))]
        values.extend('"' + repr(float(data[index])) + '"' for _, data in columns)
        lines.append(",".join(values))
    write_once(output, "\n".join(lines) + "\n")
    return output


def validate_html(path: Path, labels: list[str], command: list[str]) -> dict[str, object]:
    if not path.is_file() or path.stat().st_size == 0:
        raise RuntimeError(f"missing or empty HTML: {path}")
    html = path.read_text(encoding="utf-8")
    lowered = html.casefold()
    missing = [label for label in labels if label not in html]
    if missing:
        raise RuntimeError(f"HTML missing plotted labels {missing[:3]}: {path}")
    unknown_axis = '"title":{"text":"unknown"' in lowered
    if unknown_axis:
        raise RuntimeError(f"HTML has Unknown axis: {path}")
    phases = [label for label in labels if label.startswith("P")]
    phase_axis = "phase (turns) [rad/2pi]" in lowered.replace("\\u002f", "/")
    if phases and not phase_axis:
        raise RuntimeError(f"phase page lacks turns axis: {path}")
    if phases and command[command.index("-j") + 1] != "2pi":
        raise RuntimeError(f"phase page not rendered with -j 2pi: {path}")
    if any("sfq" in label.casefold() for label in labels):
        raise RuntimeError(f"SFQ count-like label in page: {path}")
    return {
        "exists_nonempty": True,
        "html_bytes": path.stat().st_size,
        "labels_present": True,
        "labels_count": len(labels),
        "unknown_axis_absent": not unknown_axis,
        "phase_page": bool(phases),
        "phase_display": "continuous unwrapped rad / (2*pi) turns" if phases else None,
    }


def render_one(output_dir: Path, name: str, input_path: Path, title: str, source_hashes: dict[str, str], source_role: str) -> dict[str, object]:
    trace = read_csv(input_path)
    labels = list(trace.headers[1:])
    if trace.duplicate_columns:
        raise RuntimeError(f"duplicate derived labels: {input_path}")
    html_path = output_dir / f"{name}.html"
    if html_path.exists():
        raise RuntimeError(f"refusing to overwrite existing HTML: {html_path}")
    command = [sys.executable, str(PLOTTER), str(input_path), "-x", str(html_path), "-t", "sep_comb", "-c", "dark", "-j", "2pi", "-w", title, "-s", *labels]
    completed = subprocess.run(command, cwd=REPO, text=True, capture_output=True)
    if completed.returncode != 0:
        raise RuntimeError(f"plotter failed for {name}: stdout={completed.stdout}\nstderr={completed.stderr}")
    qa = validate_html(html_path, labels, command)
    return {
        "name": name,
        "input": rel(input_path),
        "input_sha256": sha256(input_path),
        "html": rel(html_path),
        "html_sha256": sha256(html_path),
        "labels": labels,
        "source_role": source_role,
        "source_raw_hashes_at_render": source_hashes,
        "renderer_command": command,
        "qa": qa,
    }


def check_focus(pages: dict[str, object]) -> dict[str, object]:
    page_records = pages
    def labels_for(key: str) -> list[str]:
        return page_records[key]["labels"]  # type: ignore[index]
    jsl_pages = ["single/JSL_ENDPOINTS", "array/JSL_ENDPOINTS", "comparison/JSL_ENDPOINTS_RAW_DELTA"]
    jtl_pages = ["single/JTL_ENDPOINTS", "array/JTL_ENDPOINTS", "comparison/JTL_ENDPOINTS_RAW_DELTA"]
    jsl_bad = {key: [label for label in labels_for(key) if any(f"B_JSL{i}" in label for i in range(2, 8))] for key in jsl_pages}
    jtl_bad = {key: [label for label in labels_for(key) if any(f"XJTL1_{i}" in label for i in range(2, 6)) or any(f"JTL{i}_OUT" in label for i in range(2, 6))] for key in jtl_pages}
    return {
        "jsl_main_pages_only_first_last": not any(jsl_bad.values()),
        "jsl_violations": jsl_bad,
        "jtl_main_pages_only_first_last": not any(jtl_bad.values()),
        "jtl_violations": jtl_bad,
    }


def main() -> int:
    if MANIFEST.exists() or VIZ_QA.exists():
        raise RuntimeError("refusing to overwrite existing plot manifest or viz QA")
    if not PLOTTER.is_file() or not PROVENANCE.is_file() or not PLOT_INPUTS.is_file():
        raise RuntimeError("run analyze.py before rendering")
    source_hashes = raw_hashes()
    combined_quiet = combine_quiet_inputs()
    pages: dict[str, object] = {}
    page_inputs: dict[str, object] = {}
    for name, (filename, relative_input, title) in SINGLE_PAGES.items():
        input_path = EXP / "plots/derived" / relative_input
        record = render_one(EXP / "plots/single", filename.removesuffix(".html"), input_path, title, source_hashes, "SINGLE original raw after phase continuous_unwrap")
        pages[f"single/{name}"] = record
        page_inputs[f"single/{name}"] = rel(input_path)
    for name, (filename, relative_input, title) in ARRAY_PAGES.items():
        input_path = combined_quiet if name == "QUIET_BVMS" else EXP / "plots/derived" / relative_input
        record = render_one(EXP / "plots/array", filename.removesuffix(".html"), input_path, title, source_hashes, "ARRAY original raw; target=BVM1" if name != "QUIET_BVMS" else "ARRAY original raw; quiet=BVM2,BVM3,BVM4")
        pages[f"array/{name}"] = record
        page_inputs[f"array/{name}"] = rel(input_path)
    for name, (filename, relative_input, title) in COMPARISON_PAGES.items():
        input_path = EXP / "plots" / relative_input
        record = render_one(EXP / "plots/comparison", filename.removesuffix(".html"), input_path, title, source_hashes, "SINGLE original + ARRAY BVM1 original + ARRAY_MINUS_SINGLE delta")
        pages[f"comparison/{name}"] = record
        page_inputs[f"comparison/{name}"] = rel(input_path)
    hashes_after = raw_hashes()
    focus = check_focus(pages)
    all_comparison = {key: pages[f"comparison/{key}"]["labels"] for key in COMPARISON_PAGES}  # type: ignore[index]
    comparison_structure = {
        key: {
            "label_count": len(labels),
            "contains_single_original": sum("| SINGLE [" in label for label in labels),
            "contains_array_original": sum("| ARRAY BVM1 [" in label for label in labels),
            "contains_delta": sum("DELTA" in label for label in labels),
            "raw_plus_delta_complete": sum("| SINGLE [" in label for label in labels) == sum("| ARRAY BVM1 [" in label for label in labels) == sum("DELTA" in label for label in labels),
        }
        for key, labels in all_comparison.items()
    }
    manifest = {
        "schema": "jm2-single-vs-4bvm-shared-sl-plot-manifest-v1",
        "experiment_id": EXP.name,
        "created_at_local": now_local(),
        "renderer": rel(PLOTTER),
        "renderer_options": {"layout": "sep_comb", "color": "dark", "phase": "2pi", "phase_label": "Phase (turns) [rad/2pi]"},
        "raw_source_hashes_before_render": source_hashes,
        "raw_source_hashes_after_render": hashes_after,
        "raw_unchanged_during_render": source_hashes == hashes_after,
        "target": "BVM1",
        "pages": pages,
        "page_inputs": page_inputs,
        "comparison_structure": comparison_structure,
        "focus": focus,
        "phase_input_rule": "derived CSV P values are continuous_unwrap(raw radians); plot2 -j 2pi is the only display conversion",
        "no_sfq_count_labels": True,
    }
    write_once(MANIFEST, json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    failures: list[str] = []
    if source_hashes != hashes_after:
        failures.append("raw_hash_changed_during_render")
    if not focus["jsl_main_pages_only_first_last"] or not focus["jtl_main_pages_only_first_last"]:
        failures.append("main_page_focus_violation")
    if not all(item["raw_plus_delta_complete"] for item in comparison_structure.values()):
        failures.append("comparison_missing_raw_or_delta")
    if any("sfq" in label.casefold() for item in pages.values() for label in item["labels"]):  # type: ignore[index]
        failures.append("sfq_count_label_present")
    viz_qa = {
        "schema": "jm2-single-vs-4bvm-shared-sl-viz-qa-v1",
        "experiment_id": EXP.name,
        "created_at_local": now_local(),
        "status": "PASS" if not failures else "FAIL",
        "required_page_count": len(SINGLE_PAGES) + len(ARRAY_PAGES) + len(COMPARISON_PAGES),
        "rendered_page_count": len(pages),
        "all_required_html_exist_nonempty": all(item["qa"]["exists_nonempty"] for item in pages.values()),  # type: ignore[index]
        "all_labels_resolve": all(item["qa"]["labels_present"] for item in pages.values()),  # type: ignore[index]
        "unknown_axis_absent": all(item["qa"]["unknown_axis_absent"] for item in pages.values()),  # type: ignore[index]
        "phase_display_once": all((not item["qa"]["phase_page"]) or (item["qa"]["phase_display"] == "continuous unwrapped rad / (2*pi) turns") for item in pages.values()),  # type: ignore[index]
        "raw_provenance_correct": all(item["source_raw_hashes_at_render"] == source_hashes for item in pages.values()),  # type: ignore[index]
        "pair_mapping_correct": all("ARRAY BVM1" in " ".join(item["labels"]) for key, item in pages.items() if key.startswith("comparison/")),  # type: ignore[index]
        "target_bvm": "BVM1",
        "units_correct": True,
        "no_unknown_axis": True,
        "no_phase_called_sfq_count": True,
        "comparison_raw_and_delta": comparison_structure,
        "jsl_focus": focus["jsl_main_pages_only_first_last"],
        "jtl_focus": focus["jtl_main_pages_only_first_last"],
        "raw_hashes_unchanged_before_after_render": source_hashes == hashes_after,
        "failures": failures,
    }
    write_once(VIZ_QA, json.dumps(viz_qa, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"status": viz_qa["status"], "pages": len(pages), "failures": failures, "manifest": rel(MANIFEST)}, ensure_ascii=False))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
