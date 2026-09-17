#!/usr/bin/env python3
"""Build immutable attempts for one JoSIM experiment series.

This is a small series-local helper, not a repository-wide experiment
manager. A concrete series may replace it when its topology or stimulus needs
more specific assembly logic.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any


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


def resolve(series: Path, value: str) -> Path | None:
    if not value:
        return None
    path = Path(value)
    return path.resolve() if path.is_absolute() else (series / path).resolve()


def git_snapshot(series: Path) -> dict[str, Any]:
    repo = next((candidate for candidate in (series, *series.parents) if (candidate / ".git").exists()), None)
    if repo is None:
        return {"available": False, "working_tree_dirty": None, "head": None}
    try:
        status = subprocess.run(["git", "status", "--short", "--untracked-files=all"], cwd=repo, capture_output=True, text=True, check=True).stdout
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return {"available": False, "working_tree_dirty": None, "head": None, "repo": str(repo)}
    return {"available": True, "repo": str(repo), "head": head, "working_tree_dirty": bool(status), "status_porcelain": status}


def solver_snapshot(path_value: str) -> dict[str, Any]:
    path = Path(path_value).expanduser().resolve() if path_value else None
    record: dict[str, Any] = {"path": str(path) if path else "", "exists": bool(path and path.is_file())}
    if not path or not path.is_file():
        return record
    record["sha256"] = sha256(path)
    version = subprocess.run([str(path), "--version"], capture_output=True, text=True, check=False)
    record.update({"version_returncode": version.returncode, "version_stdout": version.stdout.strip(), "version_stderr": version.stderr.strip()})
    return record


def display_selector(value: str) -> str:
    return value if value else "INLINE_IN_TOP"


def placeholder(path: Path) -> bool:
    text = path.read_text(encoding="utf-8", errors="replace")
    return any(token in text for token in ("TEMPLATE_PLACEHOLDER", "EDIT_ME", "{{"))


def require_number(label: str, value: str) -> float:
    if value == "":
        raise RuntimeError(f"{label} must be filled before generated stimulus can run")
    try:
        return float(value)
    except ValueError as exc:
        raise RuntimeError(f"{label} is not numeric: {value!r}") from exc


def time_token(value: float) -> str:
    return f"{value:.12g}p"


def amplitude_token(value_ua: float) -> str:
    return f"{value_ua:.12g}u"


def pulse(name: str, node: str, amplitude_ua: float, start_ps: float, rise_ps: float, fall_ps: float, width_ps: float) -> str:
    high_start = start_ps + rise_ps
    high_end = high_start + width_ps
    end = high_end + fall_ps
    points = " ".join([
        "0 0",
        f"{time_token(start_ps)} 0",
        f"{time_token(high_start)} {amplitude_token(amplitude_ua)}",
        f"{time_token(high_end)} {amplitude_token(amplitude_ua)}",
        f"{time_token(end)} 0",
    ])
    return f"I_{name} 0 {node} PWL({points})"


def generated_stimulus(args: argparse.Namespace, mask: str) -> str:
    lines = [f"* Generated stimulus for mask {mask}; series-specific values are from run.sh."]
    if int(args.write_enable):
        start = require_number("WRITE_START_PS", args.write_start_ps)
        rise = require_number("WRITE_RISE_PS", args.write_rise_ps)
        fall = require_number("WRITE_FALL_PS", args.write_fall_ps)
        width = require_number("WRITE_WIDTH_PS", args.write_width_ps)
        wl = require_number("WL_AMPLITUDE_UA", args.wl_amplitude_ua)
        bl = require_number("BL_AMPLITUDE_UA", args.bl_amplitude_ua)
        lines.extend([pulse("WRITE_WL", "WL", wl, start, rise, fall, width), pulse("WRITE_BL", "BL", bl, start, rise, fall, width)])
    if int(args.read_enable):
        start = require_number("READ_START_PS", args.read_start_ps)
        rise = require_number("READ_RISE_PS", args.read_rise_ps)
        fall = require_number("READ_FALL_PS", args.read_fall_ps)
        width = require_number("READ_WIDTH_PS", args.read_width_ps)
        se = require_number("SE_AMPLITUDE_UA", args.se_amplitude_ua)
        lines.append(pulse("READ_SE", "SE", se, start, rise, fall, width))
    if not int(args.write_enable) and not int(args.read_enable):
        lines.append("* No generated sources enabled; add series-specific sources in this helper if required.")
    return "\n".join(lines) + "\n"


def selected_cases(args: argparse.Namespace) -> list[str]:
    if args.only and args.case:
        raise RuntimeError("--only and --case are mutually exclusive")
    if args.case:
        return [args.case]
    if args.only:
        return [args.only]
    return list(args.masks)


def next_attempt(runs: Path) -> str:
    numbers = [int(match.group(1)) for path in runs.iterdir() if (match := re.fullmatch(r"A(\d+)", path.name)) and path.is_dir()]
    return f"A{(max(numbers, default=0) + 1):03d}"


def source_record(role: str, source: Path, snapshot: Path, series: Path) -> dict[str, Any]:
    return {"role": role, "source_path": str(source), "snapshot_path": str(snapshot.relative_to(series)), "sha256": sha256(source), "bytes": source.stat().st_size}


def make_source_snapshot(args: argparse.Namespace, attempt: Path, cases: list[str]) -> tuple[dict[str, Any], dict[str, Path]]:
    series = Path(args.series_dir).resolve()
    snapshot = attempt / "snapshot"
    snapshot.mkdir(parents=True, exist_ok=False)
    records: dict[str, Any] = {"sources": [], "module_roles": {}, "stimulus_mode": args.stimulus_mode}
    selected: dict[str, Path] = {}
    top = resolve(series, args.top_deck)
    if top is None or not top.is_file():
        raise RuntimeError(f"TOP_DECK is missing: {args.top_deck!r}")
    top_snapshot = snapshot / "top.cir"
    shutil.copy2(top, top_snapshot)
    records["sources"].append(source_record("TOP_DECK", top, top_snapshot, series))
    selected["TOP_DECK"] = top_snapshot
    for role, value in (("BVM", args.bvm_circuit), ("QB", args.qb_circuit), ("JTL", args.jtl_circuit), ("COMMON_SL", args.common_sl_circuit), ("JSL", args.jsl_circuit)):
        source = resolve(series, value)
        records["module_roles"][role] = display_selector(value)
        if source is None:
            continue
        if not source.is_file():
            raise RuntimeError(f"{role} source is missing: {value}")
        target = snapshot / f"{role.lower()}_{source.name}"
        shutil.copy2(source, target)
        records["sources"].append(source_record(role, source, target, series))
        selected[role] = target
    for helper in (series / "run.sh", series / "analyze.sh", series / "plot.sh", Path(__file__), series / "scripts" / "analyze.py", series / "scripts" / "render_plots.py"):
        if helper.is_file():
            target = snapshot / "workflow" / helper.name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(helper, target)
            records["sources"].append(source_record(f"WORKFLOW:{helper.name}", helper, target, series))
    return records, selected


def stimulus_for_case(args: argparse.Namespace, case: str, attempt: Path) -> tuple[str, dict[str, Any], Path]:
    case_dir = attempt / "cases" / case
    case_dir.mkdir(parents=True, exist_ok=False)
    if args.stimulus_mode == "generated":
        text = generated_stimulus(args, case)
        stimulus = case_dir / "stimulus.inc"
        stimulus.write_text(text, encoding="utf-8")
        snap = attempt / "snapshot" / f"stimulus_{case}.inc"
        snap.write_text(text, encoding="utf-8")
        return text, {"mode": "generated", "path": str(stimulus.relative_to(Path(args.series_dir).resolve())), "sha256": sha256(stimulus), "bytes": stimulus.stat().st_size, "snapshot_path": str(snap.relative_to(Path(args.series_dir).resolve()))}, stimulus
    if args.stimulus_mode != "manual":
        raise RuntimeError(f"STIMULUS_MODE must be generated or manual, got {args.stimulus_mode!r}")
    source = resolve(Path(args.series_dir).resolve(), args.manual_stimulus)
    if source is None or not source.is_file():
        raise RuntimeError(f"MANUAL_STIMULUS is missing: {args.manual_stimulus!r}")
    if placeholder(source):
        raise RuntimeError(f"TEMPLATE_PLACEHOLDER remains in manual stimulus: {source}")
    stimulus = case_dir / "stimulus.inc"
    shutil.copy2(source, stimulus)
    snap = attempt / "snapshot" / "stimulus.inc"
    if not snap.exists():
        shutil.copy2(source, snap)
    return stimulus.read_text(encoding="utf-8", errors="replace"), {"mode": "manual", "source_path": str(source), "path": str(stimulus.relative_to(Path(args.series_dir).resolve())), "sha256": sha256(stimulus), "bytes": stimulus.stat().st_size, "snapshot_path": str(snap.relative_to(Path(args.series_dir).resolve()))}, stimulus


def build_deck(args: argparse.Namespace, case: str, attempt: Path, selected: dict[str, Path], stimulus: Path) -> tuple[str, list[dict[str, Any]]]:
    series = Path(args.series_dir).resolve()
    top_source = resolve(series, args.top_deck)
    assert top_source is not None
    text = top_source.read_text(encoding="utf-8")
    case_dir = stimulus.parent
    replacements = {
        "{{BVM_INCLUDE}}": f".include {os.path.relpath(selected['BVM'], case_dir).replace(os.sep, '/') }" if "BVM" in selected else "* BVM: INLINE_IN_TOP",
        "{{QB_INCLUDE}}": f".include {os.path.relpath(selected['QB'], case_dir).replace(os.sep, '/') }" if "QB" in selected else "* QB: INLINE_IN_TOP",
        "{{JTL_INCLUDE}}": f".include {os.path.relpath(selected['JTL'], case_dir).replace(os.sep, '/') }" if "JTL" in selected else "* JTL: INLINE_IN_TOP",
        "{{COMMON_SL_INCLUDE}}": f".include {os.path.relpath(selected['COMMON_SL'], case_dir).replace(os.sep, '/') }" if "COMMON_SL" in selected else "* COMMON_SL: INLINE_IN_TOP",
        "{{JSL_INCLUDE}}": f".include {os.path.relpath(selected['JSL'], case_dir).replace(os.sep, '/') }" if "JSL" in selected else "* JSL: INLINE_IN_TOP",
        "{{STIMULUS_INCLUDE}}": f".include {os.path.relpath(stimulus, case_dir).replace(os.sep, '/') }",
        "{{MASK}}": case,
        "{{DT}}": args.dt,
        "{{STOP_TIME}}": args.stop_time,
    }
    for marker, replacement in replacements.items():
        text = text.replace(marker, replacement)
    unresolved = sorted(set(re.findall(r"\{\{[^}]+\}\}|TEMPLATE_PLACEHOLDER|EDIT_ME", text)))
    if unresolved:
        raise RuntimeError(f"unresolved template markers in actual deck for {case}: {', '.join(unresolved)}")
    extra: list[dict[str, Any]] = []
    for line in text.splitlines():
        match = re.match(r"\s*\.include\s+(.+?)\s*$", line, flags=re.IGNORECASE)
        if not match or "snapshot/" in match.group(1) or "../snapshot/" in match.group(1):
            continue
        token = match.group(1).strip('<>\"')
        candidate = (top_source.parent / token).resolve()
        if candidate.is_file() and candidate not in [Path(value).resolve() for value in selected.values()]:
            target = attempt / "snapshot" / "extra_includes" / f"{len(extra):02d}_{candidate.name}"
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(candidate, target)
            text = text.replace(line, f".include {os.path.relpath(target, case_dir).replace(os.sep, '/')}")
            extra.append(source_record("TOP_DIRECT_INCLUDE", candidate, target, series))
    if args.dt == "" or args.stop_time == "":
        raise RuntimeError("DT and STOP_TIME must be filled before a physical run")
    if ".tran" not in text.lower():
        raise RuntimeError("actual deck has no .tran statement")
    return text + ("" if text.endswith("\n") else "\n"), extra


def print_dry_run(args: argparse.Namespace) -> None:
    series = Path(args.series_dir).resolve()
    attempt = next_attempt(series / "runs")
    cases = selected_cases(args)
    print("EXPERIMENT")
    print(f"  SERIES: {series.name}")
    print(f"  ATTEMPT would be: {attempt}")
    print("CIRCUITS")
    print(f"  TOP: {display_selector(args.top_deck)}")
    print(f"  BVM: {display_selector(args.bvm_circuit)}")
    print(f"  QB: {display_selector(args.qb_circuit)}")
    print(f"  JTL: {display_selector(args.jtl_circuit)}")
    print(f"  COMMON_SL: {display_selector(args.common_sl_circuit)}")
    print(f"  JSL: {display_selector(args.jsl_circuit)}")
    print("STIMULUS")
    print(f"  mode: {args.stimulus_mode}")
    print(f"  mask(s): {' '.join(args.masks)}")
    print(f"  write: enable={args.write_enable} start={args.write_start_ps} rise={args.write_rise_ps} fall={args.write_fall_ps} width={args.write_width_ps}")
    print(f"  read: enable={args.read_enable} start={args.read_start_ps} rise={args.read_rise_ps} fall={args.read_fall_ps} width={args.read_width_ps}")
    print(f"  amplitudes: WL={args.wl_amplitude_ua}uA BL={args.bl_amplitude_ua}uA SE={args.se_amplitude_ua}uA")
    print("EXPERIMENT PARAMETERS")
    print("  series-specific parameters: edit run.sh")
    print("SOLVER")
    print(f"  JoSIM: {args.josim_bin or '<set JOSIM_BIN>'}")
    print(f"  dt: {args.dt or '<set DT>'}")
    print(f"  stop: {args.stop_time or '<set STOP_TIME>'}")
    print("CASES")
    for case in cases:
        raw = series / "runs" / attempt / "cases" / case / "raw.csv"
        deck = series / "runs" / attempt / "cases" / case / "actual_deck.cir"
        command = [args.josim_bin or "<set JOSIM_BIN>", "-a", "1", "-o", str(raw), str(deck)]
        print(f"  case: {case}")
        print(f"    actual_deck: {deck}")
        print(f"    raw: {raw}")
        print(f"    exact JoSIM CLI: {shlex.join(command)}")
    print("TOTAL SOLVES")
    print(f"  {len(cases)}")
    print("DRY_RUN: no attempt created; JoSIM not invoked")


def actual_run(args: argparse.Namespace) -> int:
    series = Path(args.series_dir).resolve()
    cases = selected_cases(args)
    top = resolve(series, args.top_deck)
    if top is None or not top.is_file():
        raise RuntimeError(f"TOP_DECK is missing: {args.top_deck!r}")
    for value, label in ((args.bvm_circuit, "BVM"), (args.qb_circuit, "QB"), (args.jtl_circuit, "JTL"), (args.common_sl_circuit, "COMMON_SL"), (args.jsl_circuit, "JSL")):
        source = resolve(series, value)
        if source and not source.is_file():
            raise RuntimeError(f"{label} source is missing: {value}")
        if source and placeholder(source):
            raise RuntimeError(f"TEMPLATE_PLACEHOLDER remains in selected {label} source: {source}")
    if placeholder(top):
        raise RuntimeError(f"TEMPLATE_PLACEHOLDER remains in TOP_DECK: {top}")
    if not args.josim_bin:
        raise RuntimeError("JOSIM_BIN must be filled before a physical run")
    solver = Path(args.josim_bin).expanduser().resolve()
    if not solver.is_file():
        raise RuntimeError(f"JOSIM_BIN is missing: {solver}")
    if args.stimulus_mode not in {"generated", "manual"}:
        raise RuntimeError("STIMULUS_MODE must be generated or manual")
    runs = series / "runs"
    runs.mkdir(parents=True, exist_ok=True)
    attempt_id = next_attempt(runs)
    attempt = runs / attempt_id
    attempt.mkdir(exist_ok=False)
    source_manifest, selected = make_source_snapshot(args, attempt, cases)
    source_manifest["attempt"] = attempt_id
    source_manifest["git"] = git_snapshot(series)
    source_manifest["run_sh_sha256"] = sha256(series / "run.sh")
    write_json(attempt / "snapshot" / "source_manifest.json", source_manifest)
    attempt_meta: dict[str, Any] = {"schema": "josim-experiment-series-attempt-v1", "series": series.name, "attempt": attempt_id, "created_at": now(), "status": "PREPARING", "git": git_snapshot(series), "python": sys.version, "solver": solver_snapshot(str(solver)), "parameters": vars(args), "cases": {}, "source_manifest_path": str((attempt / "snapshot" / "source_manifest.json").relative_to(series))}
    write_json(attempt / "metadata.json", attempt_meta)
    extra_sources: list[dict[str, Any]] = []
    for case in cases:
        stimulus_text, stimulus_meta, stimulus_path = stimulus_for_case(args, case, attempt)
        source_manifest.setdefault("stimuli", {})[case] = stimulus_meta
        deck_text, extra = build_deck(args, case, attempt, selected, stimulus_path)
        extra_sources.extend(extra)
        deck_path = stimulus_path.parent / "actual_deck.cir"
        deck_path.write_text(deck_text, encoding="utf-8")
        raw_path = stimulus_path.parent / "raw.csv"
        stdout_path = stimulus_path.parent / "stdout.txt"
        stderr_path = stimulus_path.parent / "stderr.txt"
        log_path = stimulus_path.parent / "run.log"
        command = [str(solver), "-a", "1", "-o", str(raw_path), str(deck_path)]
        started = now()
        clock = time.monotonic()
        completed = subprocess.run(command, cwd=stimulus_path.parent, capture_output=True, text=True, check=False)
        runtime = time.monotonic() - clock
        finished = now()
        stdout_path.write_text(completed.stdout, encoding="utf-8")
        stderr_path.write_text(completed.stderr, encoding="utf-8")
        log_path.write_text("\n".join([f"attempt={attempt_id}", f"case={case}", f"started_at={started}", f"finished_at={finished}", f"runtime_seconds={runtime:.6f}", f"command={shlex.join(command)}", f"exit_code={completed.returncode}", ""]), encoding="utf-8")
        case_meta: dict[str, Any] = {"case": case, "status": "RUN_PASS" if completed.returncode == 0 and raw_path.is_file() and raw_path.stat().st_size else "SOLVER_FAIL", "command": command, "started_at": started, "finished_at": finished, "runtime_seconds": runtime, "stimulus": stimulus_meta, "actual_deck": {"path": str(deck_path.relative_to(series)), "sha256": sha256(deck_path), "bytes": deck_path.stat().st_size}, "raw": {"path": str(raw_path.relative_to(series)), "exists": raw_path.is_file(), "sha256": sha256(raw_path) if raw_path.is_file() else None, "bytes": raw_path.stat().st_size if raw_path.is_file() else None}, "stdout": {"path": str(stdout_path.relative_to(series)), "sha256": sha256(stdout_path), "bytes": stdout_path.stat().st_size}, "stderr": {"path": str(stderr_path.relative_to(series)), "sha256": sha256(stderr_path), "bytes": stderr_path.stat().st_size}, "run_log": {"path": str(log_path.relative_to(series)), "sha256": sha256(log_path), "bytes": log_path.stat().st_size}, "solver_sha256": sha256(solver)}
        write_json(stimulus_path.parent / "metadata.json", case_meta)
        attempt_meta["cases"][case] = case_meta
        attempt_meta["status"] = "SOLVER_FAIL" if case_meta["status"] != "RUN_PASS" else "RUNNING"
        write_json(attempt / "metadata.json", attempt_meta)
        if case_meta["status"] != "RUN_PASS":
            raise RuntimeError(f"JoSIM failed for {case}; attempt preserved at {attempt}")
    source_manifest["sources"].extend(extra_sources)
    source_manifest["attempt"] = attempt_id
    source_manifest["git"] = attempt_meta["git"]
    source_manifest["solver"] = attempt_meta["solver"]
    source_manifest["run_sh_sha256"] = sha256(series / "run.sh")
    write_json(attempt / "snapshot" / "source_manifest.json", source_manifest)
    attempt_meta["status"] = "SOLVE_COMPLETE"
    attempt_meta["source_manifest_sha256"] = sha256(attempt / "snapshot" / "source_manifest.json")
    attempt_meta["run_order"] = cases
    write_json(attempt / "metadata.json", attempt_meta)
    if not args.no_analysis:
        subprocess.run([str(series / "analyze.sh"), attempt_id], cwd=series, check=True)
    if not args.no_plots:
        subprocess.run([str(series / "plot.sh"), attempt_id], cwd=series, check=True)
    attempt_meta["status"] = "COMPLETE"
    write_json(attempt / "metadata.json", attempt_meta)
    print(json.dumps({"status": "COMPLETE", "attempt": attempt_id, "cases": cases, "physical_solve_count": len(cases)}, ensure_ascii=False, indent=2))
    return 0


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Build a new immutable attempt for this experiment series")
    result.add_argument("--series-dir", required=True)
    result.add_argument("--top-deck", required=True)
    result.add_argument("--bvm-circuit", default="")
    result.add_argument("--qb-circuit", default="")
    result.add_argument("--jtl-circuit", default="")
    result.add_argument("--common-sl-circuit", default="")
    result.add_argument("--jsl-circuit", default="")
    result.add_argument("--stimulus-mode", required=True)
    result.add_argument("--manual-stimulus", default="")
    result.add_argument("--masks", nargs="+", required=True)
    result.add_argument("--write-enable", type=int, default=0)
    result.add_argument("--write-start-ps", default="")
    result.add_argument("--write-rise-ps", default="")
    result.add_argument("--write-fall-ps", default="")
    result.add_argument("--write-width-ps", default="")
    result.add_argument("--read-enable", type=int, default=0)
    result.add_argument("--read-start-ps", default="")
    result.add_argument("--read-rise-ps", default="")
    result.add_argument("--read-fall-ps", default="")
    result.add_argument("--read-width-ps", default="")
    result.add_argument("--wl-amplitude-ua", default="")
    result.add_argument("--bl-amplitude-ua", default="")
    result.add_argument("--se-amplitude-ua", default="")
    result.add_argument("--josim-bin", default="")
    result.add_argument("--dt", default="")
    result.add_argument("--stop-time", default="")
    result.add_argument("--only")
    result.add_argument("--case")
    result.add_argument("--dry-run", action="store_true")
    result.add_argument("--no-analysis", action="store_true")
    result.add_argument("--no-plots", action="store_true")
    return result


def main() -> int:
    args = parser().parse_args()
    if args.dry_run:
        print_dry_run(args)
        return 0
    return actual_run(args)


if __name__ == "__main__":
    raise SystemExit(main())
