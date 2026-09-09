#!/usr/bin/env python3
"""Independent visualization QA for the registered plot stages."""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
RUNS = {"NOMINAL": "nominal", "L1_DOWN": "l1_down", "L1_UP": "l1_up", "RJ1_UP_05": "rj1_up_05", "RJ1_UP_10": "rj1_up_10"}
WINDOWS = {"110_116ps": (110.0, 116.0), "110_121ps": (110.0, 121.0)}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def fail(message: str, failures: list[str]) -> None:
    failures.append(message)


def raw_for(run_id: str) -> Path:
    return EXP / "runs" / RUNS[run_id] / "raw.csv"


def check_entry(entry: dict[str, object], failures: list[str]) -> None:
    output = Path(str(entry["output_path"]))
    input_path = Path(str(entry["input_path"]))
    if not output.is_file():
        fail(f"missing output: {output}", failures)
        return
    if sha256(output) != entry["output_sha256"]:
        fail(f"output hash mismatch: {output}", failures)
    if not input_path.is_file():
        fail(f"missing input: {input_path}", failures)
    elif sha256(input_path) != entry["input_sha256"]:
        fail(f"input hash mismatch: {input_path}", failures)
    source_paths = [Path(path) for path in entry["source_raw_paths"]]
    source_hashes = entry["source_raw_sha256"]
    for source, expected in zip(source_paths, source_hashes):
        if not source.is_file() or sha256(source) != expected:
            fail(f"source raw hash mismatch: {source}", failures)
    if entry["transformation_registry"] is None or not str(entry["transformation_registry"]):
        fail(f"missing transformation registry: {output}", failures)
    if entry["phase_convention"] is None:
        fail(f"missing phase convention: {output}", failures)


def check_zoom_csv(entry: dict[str, object], failures: list[str]) -> None:
    window = entry.get("window_ps")
    if not window:
        return
    start, end = float(window[0]), float(window[1])
    path = Path(str(entry["input_path"]))
    if not path.is_file():
        return
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.reader(stream)
        header = next(reader)
        rows = list(reader)
    if not rows:
        fail(f"empty zoom CSV: {path}", failures)
        return
    times = [float(row[0]) * 1e12 for row in rows]
    if min(times) < start or max(times) >= end:
        fail(f"zoom window fidelity mismatch: {path}", failures)
    if any(right <= left for left, right in zip(times, times[1:])):
        fail(f"zoom time is not strictly increasing: {path}", failures)
    raw = raw_for(entry["run_ids"][0])
    with raw.open(newline="", encoding="utf-8-sig") as stream:
        raw_reader = csv.reader(stream)
        raw_header = next(raw_reader)
        raw_rows = list(raw_reader)
    raw_time_tokens = {row[0] for row in raw_rows if start <= float(row[0]) * 1e12 < end}
    if set(row[0] for row in rows) != raw_time_tokens:
        fail(f"zoom CSV does not contain exactly the registered raw time tokens: {path}", failures)
    if "I_quiet_total" in header:
        positions = {name: index for index, name in enumerate(header)}
        for row in rows:
            expected = sum(float(row[positions[f"I(L_SL|XBVM{i})"]]) for i in range(2, 5))
            if abs(float(row[positions["I_quiet_total"]]) - expected) > 1e-18:
                fail(f"derived quiet total mismatch: {path}", failures)


def main() -> int:
    requested_stage = sys.argv[1] if len(sys.argv) > 1 else "auto"
    if requested_stage == "auto":
        requested_stage = "final" if (EXP / "analysis/visualization_manifest.json").is_file() else "standalone"
    failures: list[str] = []
    if requested_stage == "standalone":
        manifest_path = EXP / "analysis/standalone_visualization_manifest.json"
        output_path = EXP / "analysis/visualization_qa_standalone.json"
    elif requested_stage == "final":
        manifest_path = EXP / "analysis/visualization_manifest.json"
        output_path = EXP / "analysis/visualization_qa.json"
    else:
        raise SystemExit("usage: visualization_qa.py [standalone|final]")
    if not manifest_path.is_file():
        raise RuntimeError(f"manifest missing: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    entries = manifest.get("entries", []) if requested_stage == "standalone" else manifest.get("standalone_entries", []) + manifest.get("comparison_entries", [])
    for entry in entries:
        check_entry(entry, failures)
        if entry.get("kind") == "critical_zoom":
            check_zoom_csv(entry, failures)
    if requested_stage == "standalone":
        expected_kinds = {"source_interface", "qb_trigger", "regeneration", "downstream", "critical_zoom"}
        if len(entries) != 30:
            fail(f"standalone entry count {len(entries)} != 30", failures)
        if {entry.get("kind") for entry in entries} != expected_kinds:
            fail("standalone kinds incomplete", failures)
        for run_id in RUNS:
            run_entries = [entry for entry in entries if entry.get("run_ids") == [run_id]]
            if len(run_entries) != 6:
                fail(f"standalone entry count for {run_id} is {len(run_entries)}", failures)
    else:
        expected_kinds = {"source_interface", "qb_trigger", "regeneration", "downstream", "critical_zoom", "l1_family", "l1_family_html", "rj1_family", "rj1_family_html", "bj1_phase_plane_l1", "bj1_phase_plane_l1_html", "bj1_phase_plane_rj1", "bj1_phase_plane_rj1_html", "array_source_decomposition", "array_source_decomposition_html"}
        if {entry.get("kind") for entry in entries} != expected_kinds:
            fail("final visualization kinds incomplete", failures)
        if len(manifest.get("standalone_entries", [])) != 30 or len(manifest.get("comparison_entries", [])) != 10:
            fail("final standalone/comparison entry counts mismatch", failures)
    record = {
        "schema": "qb-rj1-l1-local-sensitivity-visualization-qa-v1",
        "experiment_id": EXP.name,
        "created_at_local": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "stage": requested_stage,
        "manifest_path": str(manifest_path),
        "entry_count": len(entries),
        "source_hashes_checked": True,
        "window_fidelity_checked": requested_stage in {"standalone", "final"},
        "raw_unchanged_by_visualization": True,
        "transformations": "none except registered exact window slices, samplewise I_quiet_total and independent phase display unwrap/rad-to-turn",
        "status": "PASS" if not failures else "FAIL",
        "failures": failures,
    }
    output_path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": record["status"], "stage": requested_stage, "entry_count": len(entries), "failures": failures}, ensure_ascii=False))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
