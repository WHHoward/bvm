#!/usr/bin/env python3
"""Render and QA the N3/N4 deep-dive pages without touching raw data."""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
PLOTTER = REPO / "scripts/josim-plot2.py"
MANIFEST_PATH = EXP / "analysis/deep_dive_plot_manifest.json"
RAW_QA_PATH = EXP / "analysis/n3_n4_raw_qa.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(REPO).as_posix()


def write_once(path: Path, content: str) -> None:
    if path.exists():
        if path.read_text(encoding="utf-8") == content:
            return
        raise RuntimeError(f"refusing to overwrite existing artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def csv_headers(path: Path) -> list[str]:
    with path.open(newline="", encoding="utf-8") as handle:
        header = next(csv.reader(handle))
    if not header or header[0] != "time":
        raise RuntimeError(f"plot input must begin with time: {path}")
    if len(header) != len(set(header)):
        raise RuntimeError(f"plot input has duplicate labels: {path}")
    return header


def qa_html(html: str, labels: list[str], *, phase_page: bool) -> list[str]:
    visible = html.replace("\\u002f", "/")
    failures: list[str] = []
    missing = [label for label in labels if label not in visible]
    if missing:
        failures.append(f"missing HTML labels: {missing}")
    if '"text":"Unknown"' in visible or '"title":{"text":"Unknown"' in visible:
        failures.append("HTML contains Unknown axis/label")
    if any(term in html.lower() for term in ("sfq count", "event count")):
        failures.append("HTML contains prohibited count wording")
    if phase_page and "Phase (turns) [rad/2pi]" not in visible:
        failures.append("phase page lacks explicit rad/(2*pi) axis label")
    return failures


def main() -> int:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    raw_qa = json.loads(RAW_QA_PATH.read_text(encoding="utf-8"))
    raw_paths = {name: REPO / record["path"] for name, record in raw_qa["raw_cases"].items()}
    raw_before = {name: sha256(path) for name, path in raw_paths.items()}
    failures: list[str] = []
    pages: dict[str, object] = {}
    for name, spec in manifest["pages"].items():
        input_path = REPO / spec["input"]
        labels = list(spec["labels"])
        try:
            header = csv_headers(input_path)
        except Exception as exc:  # pragma: no cover - recorded as QA, not hidden
            failures.append(f"{name}: {exc}")
            continue
        absent = [label for label in labels if label not in header[1:]]
        if absent:
            failures.append(f"{name}: requested labels absent from input: {absent}")
        output_path = EXP / "plots/deep_dive" / f"{name}.html"
        command = [
            sys.executable,
            str(PLOTTER),
            str(input_path),
            "-x",
            str(output_path),
            "-t",
            "sep_comb",
            "-c",
            "dark",
            "-j",
            "2pi",
            "-w",
            str(spec["title"]),
            "-s",
            *labels,
        ]
        reused = output_path.exists()
        completed = subprocess.CompletedProcess(command, 0, "", "")
        if not reused and not absent:
            completed = subprocess.run(command, cwd=REPO, text=True, capture_output=True)
            if completed.returncode != 0:
                failures.append(f"{name}: plotter exit {completed.returncode}: {completed.stderr[-1000:]}")
        if not output_path.is_file() or output_path.stat().st_size == 0:
            failures.append(f"{name}: missing or empty HTML")
            continue
        html = output_path.read_text(encoding="utf-8", errors="replace")
        page_failures = qa_html(html, labels, phase_page=any(label.startswith("P(") for label in labels))
        failures.extend(f"{name}: {item}" for item in page_failures)
        if name in manifest["comparison_pages_show_both_tracks"]:
            if not any("| N3_REPLAY" in label for label in labels) or not any("| N4_REPLAY" in label for label in labels):
                failures.append(f"{name}: comparison input does not expose both N3 and N4 tracks")
        pages[name] = {
            "input": rel(input_path),
            "input_sha256": sha256(input_path),
            "source_kind": spec["source_kind"],
            "output": rel(output_path),
            "output_sha256": sha256(output_path),
            "output_bytes": output_path.stat().st_size,
            "labels": labels,
            "phase_axis_conversion": "P raw rad -> -j 2pi display turns" if any(label.startswith("P(") for label in labels) else None,
            "command": command,
            "returncode": completed.returncode,
            "qa": "PASS" if not page_failures else "FAIL",
        }
    raw_after = {name: sha256(path) for name, path in raw_paths.items()}
    if raw_before != raw_after:
        failures.append("raw hash changed during deep-dive rendering")
    if raw_before != raw_qa["raw_hashes_before"]:
        failures.append("raw hash before rendering differs from builder raw QA")
    record = {
        "schema": "jm2-n3-n4-replay-deep-dive-visualization-qa-v1",
        "status": "PASS" if not failures else "FAIL",
        "renderer": {
            "path": rel(PLOTTER),
            "sha256": sha256(PLOTTER),
            "plot_type": "sep_comb",
            "color": "dark",
            "phase_jump": "2pi",
        },
        "raw_hashes_before": raw_before,
        "raw_hashes_after": raw_after,
        "raw_unchanged": raw_before == raw_after,
        "pages": pages,
        "standalone_direct_raw": all(
            pages.get(name, {}).get("source_kind") == "raw_direct_standalone"
            for name in manifest["raw_direct_standalone_pages"]
        ),
        "comparison_pages_show_both_tracks": all(
            any("| N3_REPLAY" in label for label in pages.get(name, {}).get("labels", []))
            and any("| N4_REPLAY" in label for label in pages.get(name, {}).get("labels", []))
            for name in manifest["comparison_pages_show_both_tracks"]
        ),
        "phase_rule": "P(...) values are raw radians; -j 2pi displays rad/(2*pi) as turns; no count semantics",
        "failures": failures,
    }
    write_once(EXP / "analysis/deep_dive_viz_qa.json", json.dumps(record, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"status": record["status"], "page_count": len(pages), "raw_unchanged": record["raw_unchanged"], "failures": failures}, ensure_ascii=False))
    return 0 if record["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
