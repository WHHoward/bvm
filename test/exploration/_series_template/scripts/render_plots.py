#!/usr/bin/env python3
"""Render descriptive HTML with the repository's josim-plot2.py renderer."""

from __future__ import annotations

import argparse
import csv
import difflib
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


GROUPS = ("SIGNAL_PATH", "BVM_STATE", "BVM_OUTPUT", "JSL_CHAIN", "QB_STATE", "JTL_CHAIN")


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def attempt_dir(series: Path, value: str) -> Path:
    if value == "latest":
        candidates = sorted(path for path in (series / "runs").glob("A*") if path.is_dir())
        if not candidates:
            raise RuntimeError(f"no attempts found under {series / 'runs'}")
        return candidates[-1]
    path = series / "runs" / value
    if not path.is_dir():
        raise RuntimeError(f"attempt does not exist: {path}")
    return path


def raw_header(path: Path) -> list[str]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        row = next(csv.reader(stream), None)
    if not row:
        raise RuntimeError(f"empty raw CSV: {path}")
    duplicates = sorted(name for name, count in Counter(row).items() if count > 1)
    if duplicates:
        raise RuntimeError(f"duplicate raw headers require explicit occurrence handling: {', '.join(duplicates)}")
    return row


def signal_kind(signal: str) -> str:
    if signal.startswith("V("):
        return "voltage"
    if signal.startswith("I("):
        return "current"
    if signal.startswith("P("):
        return "phase"
    return "other"


def list_signals(path: Path) -> None:
    headers = raw_header(path)
    print(f"RAW: {path}")
    print(f"RAW_SHA256: {sha256(path)}")
    print("SIGNALS")
    for kind in ("voltage", "current", "phase", "other"):
        print(f"  {kind}:")
        for signal in headers:
            if signal not in {"time", "time_s", "time_ps"} and signal_kind(signal) == kind:
                print(f"    {signal}")
    print("PHASE_SEMANTICS: P(...) raw radians; display turns only as rad/(2*pi) navigation")


def validate_signals(path: Path, requested: list[str]) -> None:
    headers = raw_header(path)
    missing = [signal for signal in requested if signal not in headers]
    if not missing:
        return
    print(f"missing signal(s) in {path}:", file=sys.stderr)
    for signal in missing:
        matches = difflib.get_close_matches(signal, headers, n=5, cutoff=0.2)
        print(f"  {signal}", file=sys.stderr)
        print(f"    close matches: {', '.join(matches) if matches else '(none)'}", file=sys.stderr)
    print("run ./plot.sh <attempt> --list-signals", file=sys.stderr)
    raise RuntimeError("requested signal is absent from raw header")


def time_ps(value: str, header: str) -> float:
    number = float(value)
    return number * 1.0e12 if header in {"time", "time_s"} and abs(number) < 1.0 else number


def crop_raw(path: Path, start: float, end: float) -> Path:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        rows = list(csv.reader(stream))
    if not rows:
        raise RuntimeError(f"empty raw CSV: {path}")
    headers = rows[0]
    time_index = next((index for index, name in enumerate(headers) if name in {"time", "time_s", "time_ps"}), 0)
    selected = [row for row in rows[1:] if len(row) > time_index and start <= time_ps(row[time_index], headers[time_index]) < end]
    handle = tempfile.NamedTemporaryFile(prefix="josim_series_crop_", suffix=".csv", delete=False)
    temporary = Path(handle.name)
    handle.close()
    with temporary.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(headers)
        writer.writerows(selected)
    return temporary


def repo_root(series: Path) -> Path | None:
    return next((candidate for candidate in (series, *series.parents) if (candidate / ".git").exists()), None)


def render_one(series: Path, attempt: Path, case_dir: Path, group: str, signals: list[str], window: tuple[float, float] | None, static: bool) -> dict[str, Any]:
    raw = case_dir / "raw.csv"
    validate_signals(raw, signals)
    plot_dir = case_dir / "plots"
    if group == "ADHOC" or window is not None:
        destination = plot_dir / "adhoc"
        stem = group if group != "ADHOC" else "signals_" + hashlib.sha256("\0".join(signals).encode()).hexdigest()[:12]
        if window is not None:
            stem += f"_{window[0]:g}_{window[1]:g}ps"
    else:
        destination = plot_dir
        stem = group
    html = destination / f"{stem}.html"
    input_path = raw
    temporary: Path | None = None
    if window is not None:
        temporary = crop_raw(raw, *window)
        input_path = temporary
    root = repo_root(series)
    plotter_value = os.environ.get("JOSIM_PLOTTER", str(root / "scripts" / "josim-plot2.py") if root else "")
    plotter = Path(plotter_value)
    if not plotter.is_file():
        raise RuntimeError(f"scripts/josim-plot2.py not found: {plotter}")
    command = [sys.executable, str(plotter), str(input_path), "-x", str(html), "-t", "sep_comb", "-c", "dark", "-j", "2pi", "-w", f"{series.name} {attempt.name} {case_dir.name} {group}", "-s", *signals]
    static_path = None
    if static:
        static_path = destination / f"{stem}.svg"
        command.extend(["-o", str(static_path)])
    try:
        completed = subprocess.run(command, cwd=series, capture_output=True, text=True, check=False)
        if completed.returncode != 0:
            raise RuntimeError(f"josim-plot2.py failed: {completed.stderr[-1000:]}")
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    if not html.is_file():
        raise RuntimeError(f"plotter did not create HTML: {html}")
    record = {"attempt": attempt.name, "case": case_dir.name, "source_raw_path": str(raw.relative_to(series)), "raw_sha256": sha256(raw), "signals": signals, "group": group, "renderer": str(plotter.relative_to(root)) if root and plotter.is_relative_to(root) else str(plotter), "renderer_arguments": command, "time_unit": "ps", "phase_conversion": "-j 2pi; raw P(...) radians, displayed turns navigation only", "output_html": str(html.relative_to(series)), "html_sha256": sha256(html), "window_ps": list(window) if window is not None else [0.0, 200.0], "static_output": str(static_path.relative_to(series)) if static_path and static_path.is_file() else None, "static_sha256": sha256(static_path) if static_path and static_path.is_file() else None, "descriptive_only": True}
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description="Render descriptive plots for one JoSIM attempt")
    parser.add_argument("--series-dir", required=True)
    parser.add_argument("--attempt")
    parser.add_argument("--raw")
    parser.add_argument("--list-signals", action="store_true")
    parser.add_argument("--group")
    parser.add_argument("--adhoc", action="store_true")
    parser.add_argument("--signals", nargs="+")
    parser.add_argument("--window", nargs=2, type=float)
    parser.add_argument("--static", action="store_true")
    args = parser.parse_args()
    series = Path(args.series_dir).resolve()
    if args.list_signals:
        raw = Path(args.raw).expanduser().resolve() if args.raw else None
        if raw is None:
            if not args.attempt:
                raise RuntimeError("--list-signals requires ATTEMPT or --raw /path/to/raw.csv")
            attempt = attempt_dir(series, args.attempt)
            cases = sorted(path for path in (attempt / "cases").iterdir() if path.is_dir() and (path / "raw.csv").is_file())
            if not cases:
                raise RuntimeError(f"no raw.csv found under {attempt / 'cases'}")
            raw = cases[0] / "raw.csv"
        list_signals(raw)
        return 0
    if args.raw:
        raise RuntimeError("--raw is only valid with --list-signals")
    if not args.attempt:
        raise RuntimeError("plotting requires ATTEMPT such as A001")
    if not args.signals:
        raise RuntimeError("plotting requires exact --signals; edit plot.sh signal groups or use --list-signals")
    attempt = attempt_dir(series, args.attempt)
    cases = sorted(path for path in (attempt / "cases").iterdir() if path.is_dir() and (path / "raw.csv").is_file())
    if not cases:
        raise RuntimeError(f"no raw.csv found under {attempt / 'cases'}")
    group = "ADHOC" if args.adhoc else (args.group or "UNNAMED_GROUP")
    if not args.adhoc and group not in GROUPS:
        raise RuntimeError(f"unknown group: {group}")
    window = tuple(args.window) if args.window else None
    entries = [render_one(series, attempt, case, group, args.signals, window, args.static) for case in cases]
    manifest_path = attempt / "plots" / "plot_manifest.json"
    existing = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.is_file() else {"schema": "josim-experiment-series-plot-manifest-v1", "attempt": attempt.name, "entries": []}
    existing_entries = [item for item in existing.get("entries", []) if not any(item.get("output_html") == entry["output_html"] for entry in entries)]
    existing.update({"generated_at": now(), "attempt": attempt.name, "entries": existing_entries + entries, "renderer": "scripts/josim-plot2.py", "default_layout": "sep_comb", "default_color": "dark", "raw_direct": True, "descriptive_only": True})
    write_json(manifest_path, existing)
    print(json.dumps({"status": "PASS", "attempt": attempt.name, "group": group, "cases": [item["case"] for item in entries], "plot_manifest": str(manifest_path)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
