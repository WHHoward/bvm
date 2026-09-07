#!/usr/bin/env python3
"""Render and QA the internal-time-aligned evidence pages.

The renderer only reads raw/derived CSV inputs and calls the repository's
classic JoSIM plotter.  It never invokes JoSIM and never edits raw evidence.
"""

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
MANIFEST_PATH = EXP / "analysis/internal_time_aligned_v2_plot_manifest.json"
RAW_QA_PATH = EXP / "analysis/internal_time_aligned_v2_qa.json"
VIZ_QA_OUTPUT = EXP / "analysis/internal_time_aligned_v2_viz_qa.json"


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


def csv_grid(path: Path) -> dict[str, object]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        header = next(reader)
        times = [float(row[0]) for row in reader if row and any(cell.strip() for cell in row)]
    if len(times) < 2 or any(right <= left for left, right in zip(times, times[1:])):
        raise RuntimeError(f"plot input time grid is not strictly increasing: {path}")
    dt = [right - left for left, right in zip(times, times[1:])]
    return {
        "sample_count": len(times),
        "time_start_ps": times[0] * 1.0e12,
        "time_end_ps": times[-1] * 1.0e12,
        "dt_min_ps": min(dt) * 1.0e12,
        "dt_max_ps": max(dt) * 1.0e12,
        "strictly_increasing": True,
        "header_count": len(header),
    }


def qa_html(html: str, labels: list[str], title: str, *, phase_page: bool) -> list[str]:
    visible = html.replace("\\u002f", "/")
    failures: list[str] = []
    missing = [label for label in labels if label not in visible]
    if missing:
        failures.append(f"missing HTML labels: {missing[:8]}" + (" ..." if len(missing) > 8 else ""))
    if title not in visible:
        failures.append("HTML does not contain the registered page title")
    if '"text":"Unknown"' in visible or '"title":{"text":"Unknown"' in visible:
        failures.append("HTML contains Unknown axis/label")
    lower = html.lower()
    if "sfq count" in lower or "event count" in lower:
        failures.append("HTML contains prohibited count wording")
    if phase_page and "Phase (turns) [rad/2pi]" not in visible:
        failures.append("phase page lacks explicit rad/(2*pi) axis label")
    return failures


def page_source_hash(spec: dict[str, object]) -> str:
    path = REPO / str(spec["input"])
    return sha256(path)


def main() -> int:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    raw_qa = json.loads(RAW_QA_PATH.read_text(encoding="utf-8"))
    raw_paths = {
        case: REPO / record["path"]
        for case, record in raw_qa["cases"].items()
    }
    raw_before = {case: sha256(path) for case, path in raw_paths.items()}
    failures: list[str] = []
    pages: dict[str, object] = {}
    output_dir = EXP / "plots/deep_dive/internal_time_aligned_v2"

    for name, spec in manifest["pages"].items():
        input_path = REPO / str(spec["input"])
        labels = list(spec["labels"])
        try:
            header = csv_headers(input_path)
            grid = csv_grid(input_path)
        except Exception as exc:  # pragma: no cover - recorded as QA
            failures.append(f"{name}: {exc}")
            continue
        absent = [label for label in labels if label not in header[1:]]
        if absent:
            failures.append(f"{name}: requested labels absent from input: {absent[:8]}" + (" ..." if len(absent) > 8 else ""))
        output_path = output_dir / f"{name}.html"
        title = str(spec["title"])
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
            title,
            "-s",
            *labels,
        ]
        reused = output_path.exists()
        completed = subprocess.CompletedProcess(command, 0, "", "")
        if not reused and not absent:
            completed = subprocess.run(command, cwd=REPO, text=True, capture_output=True)
            if completed.returncode != 0:
                failures.append(f"{name}: plotter exit {completed.returncode}: {completed.stderr[-1200:]}")
        if not output_path.is_file() or output_path.stat().st_size == 0:
            failures.append(f"{name}: missing or empty HTML")
            continue
        html = output_path.read_text(encoding="utf-8", errors="replace")
        page_failures = qa_html(html, labels, title, phase_page=any(label.startswith("P(") for label in labels))
        failures.extend(f"{name}: {item}" for item in page_failures)
        pages[name] = {
            "input": rel(input_path),
            "input_sha256": page_source_hash(spec),
            "source_kind": spec["source_kind"],
            "case": spec["case"],
            "window_ps": spec["window_ps"],
            "output": rel(output_path),
            "output_sha256": sha256(output_path),
            "output_bytes": output_path.stat().st_size,
            "labels": labels,
            "phase_axis_conversion": "P raw rad -> -j 2pi display turns" if any(label.startswith("P(") for label in labels) else None,
            "command": command,
            "returncode": completed.returncode,
            "reused_existing_html": reused,
            "input_grid": grid,
            "qa": "PASS" if not page_failures else "FAIL",
        }

    # Coverage checks are performed against the machine-readable input/header,
    # not inferred from how many traces happen to be visible in a screenshot.
    coverage = {}
    for page_name, required in manifest["required_signal_coverage"].items():
        coverage[page_name] = {}
        for name, spec in manifest["pages"].items():
            if page_name == "QB_full_internal" and "QB_FULL_INTERNAL" not in name and "N3_VS_N4_QB_FULL_INTERNAL" not in name:
                continue
            if page_name == "JTL_full_chain" and "JTL_FULL_CHAIN" not in name:
                continue
            input_path = REPO / str(spec["input"])
            try:
                header = csv_headers(input_path)
            except Exception:
                continue
            if "N3_VS_N4" in name or "EVENT" in name:
                missing_tracks = {
                    case: [
                        label
                        for label in required
                        if not any(label in candidate and case in candidate for candidate in header[1:])
                    ]
                    for case in ("N3_REPLAY", "N4_REPLAY")
                }
                missing_delta = [label for label in required if not any(label in candidate and "derived" in candidate and "delta" in candidate for candidate in header[1:])]
                coverage[page_name][name] = {
                    "N3_missing": missing_tracks["N3_REPLAY"],
                    "N4_missing": missing_tracks["N4_REPLAY"],
                    "delta_missing": missing_delta,
                    "pass": not any(missing_tracks.values()) and not missing_delta,
                }
            else:
                missing = [label for label in required if label not in header[1:]]
                coverage[page_name][name] = {"missing": missing, "pass": not missing}
    for group, records in coverage.items():
        for name, record in records.items():
            if not record["pass"]:
                failures.append(f"coverage {group}/{name}: {record}")

    raw_after = {case: sha256(path) for case, path in raw_paths.items()}
    if raw_before != raw_after:
        failures.append("raw hash changed during internal-time-aligned rendering")
    if raw_before != raw_qa["raw_hashes_before"]:
        failures.append("raw hash before rendering differs from analysis QA")
    for case, record in raw_qa["cases"].items():
        if raw_after[case] != record["sha256"]:
            failures.append(f"raw hash differs from recorded QA for {case}")

    record = {
        "schema": "jm2-n3-n4-internal-time-aligned-visualization-qa-v1",
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
        "coverage": coverage,
        "standalone_pages_pass": all(pages.get(name, {}).get("qa") == "PASS" for name in manifest["standalone_pages"]),
        "comparison_pages_show_both_tracks": all(
            any("| N3_REPLAY |" in label for label in pages.get(name, {}).get("labels", []))
            and any("| N4_REPLAY |" in label for label in pages.get(name, {}).get("labels", []))
            for name in manifest["comparison_pages"]
        ),
        "critical_zoom_present": all(pages.get(name, {}).get("qa") == "PASS" for name in manifest["zoom_pages"]),
        "phase_rule": "P raw radians; each case independently unwrapped before comparison delta; -j 2pi displays turns; no count semantics",
        "visualization_is_descriptive": True,
        "failures": failures,
    }
    write_once(VIZ_QA_OUTPUT, json.dumps(record, indent=2, ensure_ascii=False) + "\n")
    print(
        json.dumps(
            {
                "status": record["status"],
                "page_count": len(pages),
                "raw_unchanged": record["raw_unchanged"],
                "standalone_pages_pass": record["standalone_pages_pass"],
                "critical_zoom_present": record["critical_zoom_present"],
                "failures": failures,
            },
            ensure_ascii=False,
        )
    )
    return 0 if record["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
