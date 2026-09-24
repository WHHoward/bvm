#!/usr/bin/env python3
"""Render-only preview and future immutable one-mask JoSIM run entry point."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shlex
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from config import ConfigError, USER_CASE_KEYS, load_env, validate_user_case
from probes import generate_probes, validate_probe_lines
from stimulus import load_stimulus, render_stimulus, validate_stimulus
from topology import SOURCE_FILES, parse_subcircuits, render_topology


SERIES = Path(__file__).resolve().parents[1]
REPO = next(path for path in (SERIES, *SERIES.parents) if (path / ".git").exists())
SCRIPTS = SERIES / "scripts"
TEMPLATE = SERIES / "templates" / "base.cir"
RUN_ID_RE = re.compile(r"^A\d{3,}_T\d{3,}_M[01]+$")
ROLE_FILENAMES = {
    "BVM": "bvm_cell_0923.cir", "QB": "BQ_0923.cir",
    "CB": "CB_0923.cir", "SJTL": "sJTL_0923.cir",
}


def sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def json_text(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def stable_env(values: dict[str, str]) -> str:
    return "".join(f"{key}={values[key]}\n" for key in sorted(values))


def topology_signature(params: dict[str, object]) -> str:
    key = {name: params[name] for name in
           ("ARRAY_SIZE", "QB_CB", "SJTL_COUNT", "POST_SJTL_CB")}
    return hashlib.sha256(json.dumps(key, sort_keys=True).encode()).hexdigest()


def validate_run_id(run_id: str, mask: str) -> None:
    if not RUN_ID_RE.fullmatch(run_id):
        raise ConfigError(f"invalid run ID {run_id!r}; expected Axxx_Txxx_M<mask>")
    if not run_id.endswith(f"_M{mask}"):
        raise ConfigError(f"run ID mask does not match requested mask {mask}")


def require_new_run_dir(runs_root: Path, run_id: str) -> Path:
    target = runs_root / run_id
    if target.exists():
        raise ConfigError(f"refusing to overwrite immutable run directory: {target}")
    return target


def allocate_run_id(runs_root: Path, mask: str, signature: str) -> str:
    existing: list[tuple[str, dict[str, Any] | None]] = []
    for path in runs_root.iterdir() if runs_root.exists() else ():
        if not path.is_dir():
            continue
        try:
            manifest = json.loads((path / "topology_manifest.json").read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            manifest = None
        existing.append((path.name, manifest))
    attempt_numbers = [int(match.group(1)) for name, _ in existing
                       if (match := re.match(r"^A(\d+)_", name))]
    topology_ids: list[int] = []
    matching_ids: list[int] = []
    for name, manifest in existing:
        match = re.match(r"^A\d+_T(\d+)_", name)
        if not match:
            continue
        number = int(match.group(1))
        topology_ids.append(number)
        if manifest and manifest.get("topology_signature") == signature:
            matching_ids.append(number)
    topology_id = min(matching_ids) if matching_ids else max(topology_ids, default=0) + 1
    attempt = max(attempt_numbers, default=0) + 1
    return f"A{attempt:03d}_T{topology_id:03d}_M{mask}"


def snapshot_sources(output_dir: Path) -> tuple[dict[str, Path], list[dict[str, object]]]:
    destination = output_dir / "snapshot" / "sources"
    destination.mkdir(parents=True, exist_ok=True)
    sources: dict[str, Path] = {}
    records: list[dict[str, object]] = []
    for role, relative in SOURCE_FILES.items():
        original = REPO / relative
        if not original.is_file():
            raise ConfigError(f"component source is missing: {relative}")
        snapshot = destination / ROLE_FILENAMES[role]
        shutil.copyfile(original, snapshot)
        sources[role] = snapshot
        records.append({
            "role": role,
            "source_path": relative.as_posix(),
            "snapshot_path": snapshot.relative_to(output_dir).as_posix(),
            "sha256": sha256(snapshot),
            "bytes": snapshot.stat().st_size,
        })
    # Validate subcircuit definitions from the byte-for-byte snapshots used by the deck.
    parse_subcircuits(sources)
    return sources, records


def render_deck(
    params: dict[str, object], topology_lines: list[str], probe_lines: list[str],
    *, fixture_only: bool,
) -> str:
    include_lines = [
        f'.include "snapshot/sources/{ROLE_FILENAMES[role]}"'
        for role in ("BVM", "QB", "CB", "SJTL")
    ]
    template = TEMPLATE.read_text(encoding="utf-8")
    replacements = {
        "{{SOURCE_INCLUDES}}": "\n".join(include_lines),
        "{{STIMULUS_INCLUDE}}": '.include "stimulus.inc"',
        "{{TOPOLOGY_BLOCK}}": "\n".join(topology_lines),
        "{{TERM_R}}": str(params["TERM_R"]),
        "{{PROBE_BLOCK}}": "\n".join(probe_lines),
        "{{DT}}": str(params["DT"]),
        "{{STOP}}": str(params["STOP"]),
    }
    for marker, value in replacements.items():
        template = template.replace(marker, value)
    if "{{" in template or "}}" in template:
        raise ConfigError("unresolved marker in templates/base.cir")
    if fixture_only:
        template = "* RENDER_FIXTURE_ONLY — not JoSIM experiment evidence\n" + template
    return template


def render_case(
    user_values: dict[str, str], stimulus_values: dict[str, str], mask: str,
    output_dir: str | Path, *, fixture_only: bool,
    user_snapshot_text: str | None = None,
    stimulus_snapshot_text: str | None = None,
) -> dict[str, object]:
    params = validate_user_case(user_values)
    if mask not in params["MASKS"]:
        raise ConfigError(f"mask {mask!r} is not listed in USER_CASE.env MASKS")
    params["MASK"] = mask
    params["RENDER_FIXTURE_ONLY"] = fixture_only
    stimulus_qa = validate_stimulus(stimulus_values, params["STOP_SECONDS"])

    case_dir = Path(output_dir)
    case_dir.mkdir(parents=True, exist_ok=True)
    sources, source_records = snapshot_sources(case_dir)
    topology_lines, topology_manifest = render_topology(params, sources)
    probe_lines, probe_manifest = generate_probes(topology_manifest, sources)
    validate_probe_lines(probe_lines, probe_manifest)
    deck = render_deck(params, topology_lines, probe_lines, fixture_only=fixture_only)
    stimulus = render_stimulus(stimulus_values, params, mask)
    if fixture_only:
        stimulus = "* RENDER_FIXTURE_ONLY — not JoSIM experiment evidence\n" + stimulus

    signature = topology_signature(params)
    topology_manifest["topology_signature"] = signature
    topology_manifest["render_status"] = "RENDER_FIXTURE_ONLY" if fixture_only else "STATIC_RENDER"
    user_snapshot_text = user_snapshot_text or stable_env(user_values)
    stimulus_snapshot_text = stimulus_snapshot_text or stable_env(stimulus_values)
    source_manifest = {
        "schema": "bvm-qb-cb-array-source-manifest-v1",
        "render_status": "RENDER_FIXTURE_ONLY" if fixture_only else "STATIC_RENDER",
        "sources": source_records,
        "user_case_sha256": hashlib.sha256(user_snapshot_text.encode()).hexdigest(),
        "stimulus_sha256": hashlib.sha256(stimulus_snapshot_text.encode()).hexdigest(),
        "topology_signature": signature,
    }
    output = {
        "USER_CASE.snapshot.env": user_snapshot_text,
        "STIMULUS.snapshot.env": stimulus_snapshot_text,
        "topology_manifest.json": json_text(topology_manifest),
        "source_manifest.json": json_text(source_manifest),
        "probe_manifest.json": json_text(probe_manifest),
        "stimulus.inc": stimulus,
        "actual_deck.cir": deck,
    }
    for name, content in output.items():
        (case_dir / name).write_text(content, encoding="utf-8")
    return {
        "status": "RENDER_FIXTURE_ONLY" if fixture_only else "STATIC_RENDER",
        "output_dir": str(case_dir),
        "mask": mask,
        "physical_solve_count": 0,
        "stimulus_qa": stimulus_qa,
        "topology_manifest": topology_manifest,
        "source_manifest": source_manifest,
        "probe_manifest": probe_manifest,
    }


def render_fixture(
    user_values: dict[str, str], stimulus_values: dict[str, str], mask: str,
    fixture_name: str,
) -> dict[str, object]:
    fixtures_root = SERIES / "tests" / "fixtures" / "rendered"
    if not re.fullmatch(r"[A-Za-z0-9_-]+", fixture_name):
        raise ConfigError(f"invalid fixture name: {fixture_name!r}")
    return render_case(user_values, stimulus_values, mask, fixtures_root / fixture_name,
                       fixture_only=True)


def _save_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8")


def _update_latest_run(run_id: str, status: str) -> None:
    _save_json(SERIES / "analysis" / "LATEST_RUN.json", {
        "schema": "bvm-qb-cb-array-latest-run-v1",
        "run_id": run_id,
        "run_path": (Path("runs") / run_id).as_posix(),
        "status": status,
    })


def _write_run_preflight(run_dir: Path, run_id: str, params: dict[str, object],
                         topology: dict[str, Any], probes: dict[str, Any],
                         sources: dict[str, Any], solver: dict[str, Any], head: str) -> None:
    probe_labels = [str(item["label"]) for item in probes["signals"]]
    source_rows = [f"- `{item['source_path']}` → `{item['snapshot_path']}` SHA-256 `{item['sha256']}`"
                   for item in sources["sources"]]
    lines = [
        "# Physical run preflight", "",
        "This experiment is governed by docs/EXPERIMENT_CONTRACT.md.", "",
        "This PRE-FLIGHT is generated from frozen USER_CASE/STIMULUS snapshots. The exact",
        "run is the single mask below; no other mask, sweep, or follow-up is authorized.", "",
        f"- run_id: `{run_id}`",
        f"- parent HEAD: `{head}`",
        f"- solver path: `{solver.get('path')}`",
        f"- solver SHA-256: `{solver.get('sha256')}`",
        f"- solver version: `{solver.get('version_stdout')}`",
        f"- ARRAY_SIZE: `{params['ARRAY_SIZE']}`",
        f"- FINAL READ MASK: `{params['MASK']}` (leftmost bit is BVM1)",
        f"- topology: `{json.dumps(topology['topology'], sort_keys=True)}`",
        f"- DT: `{params['DT']}`; STOP: `{params['STOP']}`",
        f"- run matrix: exactly `{run_id}` / mask `{params['MASK']}`",
        f"- expected raw: `{(run_dir / 'raw.csv').relative_to(SERIES).as_posix()}`",
        "- interpretation ceiling: mechanical QA and requested descriptive plots only",
        "- follow-up solves, sweeps, T1, repeated-read, and rewrite-read: prohibited",
        "", "## Source snapshots", "", *source_rows,
        "", "## Registered probes", "", *[f"- `{label}`" for label in probe_labels],
        "", "## Required output artifacts", "",
        "`actual_deck.cir`, `stimulus.inc`, `topology_manifest.json`, `source_manifest.json`,",
        "`probe_manifest.json`, `raw.csv`, stdout/stderr, mechanical raw QA/metrics, and",
        "the five requested plot pages. A failed attempt remains in this run directory.", "",
    ]
    (run_dir / "PREFLIGHT.md").write_text("\n".join(lines), encoding="utf-8")


def execute_run(
    user_values: dict[str, str], stimulus_values: dict[str, str], mask: str,
    *, run_id: str | None = None, solver: Path | None = None,
    user_snapshot_text: str | None = None,
    stimulus_snapshot_text: str | None = None,
) -> int:
    """Execute exactly one future-authorized run; never called by render-only."""
    params = validate_user_case(user_values)
    if mask not in params["MASKS"]:
        raise ConfigError(f"mask {mask!r} is not listed in USER_CASE.env MASKS")
    # Full topology/stimulus/source/probe validation occurs before a solver process is possible.
    validate_stimulus(stimulus_values, params["STOP_SECONDS"])
    signature = topology_signature(params)
    run_id = run_id or allocate_run_id(SERIES / "runs", mask, signature)
    validate_run_id(run_id, mask)
    run_dir = require_new_run_dir(SERIES / "runs", run_id)
    solver_path = (solver or (REPO / "build" / "josim-cli")).resolve()
    if not solver_path.is_file():
        raise ConfigError(f"JoSIM executable is missing: {solver_path}")
    sys.path.insert(0, str(REPO / "scripts"))
    from bvmtools.provenance import git_snapshot, solver_provenance

    parent = git_snapshot(REPO)
    run_dir.mkdir(parents=True, exist_ok=False)
    render_result = render_case(
        user_values, stimulus_values, mask, run_dir, fixture_only=False,
        user_snapshot_text=user_snapshot_text,
        stimulus_snapshot_text=stimulus_snapshot_text,
    )
    topology_manifest = render_result["topology_manifest"]
    topology_manifest["run_id"] = run_id
    topology_manifest["topology_signature"] = signature
    topology_manifest["render_status"] = "RUN"
    _save_json(run_dir / "topology_manifest.json", topology_manifest)
    source_manifest = json.loads((run_dir / "source_manifest.json").read_text(encoding="utf-8"))
    source_manifest["run_id"] = run_id
    source_manifest["parent"] = parent
    source_manifest["render_status"] = "RUN"
    _save_json(run_dir / "source_manifest.json", source_manifest)
    probe_manifest = json.loads((run_dir / "probe_manifest.json").read_text(encoding="utf-8"))
    probe_manifest["run_id"] = run_id
    probe_manifest["render_status"] = "RUN"
    _save_json(run_dir / "probe_manifest.json", probe_manifest)
    solver_info = solver_provenance(solver_path, cwd=run_dir)
    if not solver_info.get("sha256") or solver_info.get("version_returncode") != 0:
        raise ConfigError("solver identity/version preflight failed; no physical solve was started")
    _write_run_preflight(run_dir, run_id, params, topology_manifest, probe_manifest,
                         render_result["source_manifest"], solver_info, str(parent["head"]))
    command = [str(solver_path), "-a", "1", "-o", str(run_dir / "raw.csv"),
               str(run_dir / "actual_deck.cir")]
    started = datetime.now().astimezone().isoformat(timespec="seconds")
    completed = subprocess.run(command, cwd=run_dir, capture_output=True, text=True, check=False)
    (run_dir / "stdout.txt").write_text(completed.stdout, encoding="utf-8")
    (run_dir / "stderr.txt").write_text(completed.stderr, encoding="utf-8")
    (run_dir / "run.log").write_text(
        f"run_id={run_id}\nstarted_at={started}\ncommand={shlex.join(command)}\n"
        f"exit_code={completed.returncode}\n", encoding="utf-8")
    provenance = {
        "schema": "bvm-qb-cb-array-provenance-v1", "run_id": run_id,
        "parent": parent, "solver": solver_info, "command": command,
        "started_at": started,
        "actual_deck": {"path": "actual_deck.cir", "sha256": sha256(run_dir / "actual_deck.cir")},
        "stimulus": {"path": "stimulus.inc", "sha256": sha256(run_dir / "stimulus.inc")},
        "topology_manifest": {"path": "topology_manifest.json",
                              "sha256": sha256(run_dir / "topology_manifest.json")},
        "source_manifest": {"path": "source_manifest.json",
                             "sha256": sha256(run_dir / "source_manifest.json")},
        "probe_manifest": {"path": "probe_manifest.json",
                            "sha256": sha256(run_dir / "probe_manifest.json")},
        "scientific_interpretation_performed": False, "automatic_follow_up": False,
        "physical_solve_count": 1,
    }
    _save_json(run_dir / "provenance.json", provenance)
    if completed.returncode != 0 or not (run_dir / "raw.csv").is_file():
        _save_json(run_dir / "result.json", {
            "run_id": run_id, "status": "SOLVER_FAIL", "artifact_status": "INVALID",
            "physical_solve_count": 1, "scientific_interpretation_performed": False,
            "automatic_follow_up": False,
        })
        _update_latest_run(run_id, "SOLVER_FAIL")
        return completed.returncode or 2

    sys.path.insert(0, str(REPO / "scripts"))
    from bvmtools.raw import read_csv

    raw_path = run_dir / "raw.csv"
    raw_hash_before = sha256(raw_path)
    try:
        trace = read_csv(raw_path)
    except Exception as exc:
        _save_json(run_dir / "analysis" / "raw_qa.json", {
            "status": "INVALID", "path": "raw.csv", "sha256": raw_hash_before,
            "error": f"{type(exc).__name__}: {exc}", "raw_immutable": True,
        })
        provenance["raw"] = {"path": "raw.csv", "sha256": raw_hash_before,
                             "bytes": raw_path.stat().st_size}
        provenance["finished_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
        _save_json(run_dir / "provenance.json", provenance)
        _save_json(run_dir / "result.json", {
            "run_id": run_id, "status": "RAW_QA_FAIL", "artifact_status": "INVALID",
            "physical_solve_count": 1, "scientific_interpretation_performed": False,
            "automatic_follow_up": False,
        })
        _update_latest_run(run_id, "RAW_QA_FAIL")
        return 2
    raw_qa = {**trace.qa(), "path": "raw.csv", "sha256": raw_hash_before,
              "raw_immutable": True}
    _save_json(run_dir / "analysis" / "raw_qa.json", raw_qa)
    mechanical = {
        "schema": "bvm-qb-cb-array-mechanical-metrics-v1",
        "sample_count": trace.sample_count,
        "time_start_s": trace.time[0], "time_end_s": trace.time[-1],
        "dt_min_s": min(trace.dt), "dt_max_s": max(trace.dt),
        "uniform_time_grid": trace.qa()["uniform_time_grid"],
        "scientific_interpretation_performed": False,
    }
    _save_json(run_dir / "analysis" / "mechanical_metrics.json", mechanical)
    plot_status: dict[str, object]
    try:
        from plot_run import render_run
        plot_status = render_run(run_dir)
    except Exception as exc:  # preserve valid raw if a plot-only step fails
        plot_status = {"status": "FAIL", "error": f"{type(exc).__name__}: {exc}",
                       "raw_reuse_required": True}
    raw_hash_after = sha256(raw_path)
    raw_qa["raw_immutable"] = raw_hash_before == raw_hash_after
    raw_qa["sha256_after_plot"] = raw_hash_after
    raw_qa["status"] = "PASS" if raw_qa["raw_immutable"] else "FAIL"
    _save_json(run_dir / "analysis" / "raw_qa.json", raw_qa)
    artifact_status = "VALID" if raw_qa["status"] == "PASS" else "INVALID"
    result = {
        "schema": "bvm-qb-cb-array-result-v1", "run_id": run_id,
        "status": "MECHANICAL_QA_PASS_AWAITING_USER_REVIEW"
        if artifact_status == "VALID" and plot_status.get("status") == "PASS"
        else "MECHANICAL_QA_FAIL_AWAITING_USER_REVIEW",
        "mask": mask, "topology": topology_manifest["topology"],
        "solver_exit_code": completed.returncode,
        "artifact_status": artifact_status,
        "raw_sha256": raw_hash_after, "raw_qa": raw_qa,
        "plot_qa": plot_status, "mechanical_metrics": mechanical,
        "physical_solve_count": 1,
        "scientific_interpretation_performed": False,
        "automatic_follow_up": False,
    }
    _save_json(run_dir / "result.json", result)
    provenance["finished_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
    provenance["raw"] = {"path": "raw.csv", "sha256": raw_hash_after,
                         "bytes": raw_path.stat().st_size,
                         "sample_count": trace.sample_count}
    _save_json(run_dir / "provenance.json", provenance)
    _update_latest_run(run_id, result["status"])
    brief = [
        f"# {run_id}", "", f"- mask: `{mask}`",
        f"- topology: `{json.dumps(topology_manifest['topology'], sort_keys=True)}`",
        f"- solver exit: `{completed.returncode}`",
        f"- raw QA: `{raw_qa['status']}`; SHA-256 `{raw_hash_after}`",
        f"- plot QA: `{plot_status.get('status')}`",
        f"- sample count: `{trace.sample_count}`; time range `{trace.time[0]}..{trace.time[-1]} s`",
        "- scientific_interpretation_performed: `false`",
        "- automatic_follow_up: `false`", "",
    ]
    (run_dir / "RESULT_BRIEF.md").write_text("\n".join(brief), encoding="utf-8")
    return 0 if artifact_status == "VALID" and plot_status.get("status") == "PASS" else 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render one array case or run exactly one mask")
    parser.add_argument("--user-case", default=str(SERIES / "USER_CASE.env"))
    parser.add_argument("--stimulus", default=str(SERIES / "STIMULUS.env"))
    parser.add_argument("--mask", required=True)
    parser.add_argument("--render-only", action="store_true")
    parser.add_argument("--output-dir")
    parser.add_argument("--run-id")
    parser.add_argument("--solver")
    args = parser.parse_args(argv)
    try:
        user_path, stimulus_path = Path(args.user_case).resolve(), Path(args.stimulus).resolve()
        user_snapshot_text = user_path.read_text(encoding="utf-8")
        stimulus_snapshot_text = stimulus_path.read_text(encoding="utf-8")
        user_values = load_env(user_path, USER_CASE_KEYS)
        stimulus_values = load_stimulus(stimulus_path)
        params = validate_user_case(user_values)
        if len(args.mask) != int(params["ARRAY_SIZE"]) or any(bit not in "01" for bit in args.mask):
            raise ConfigError("MASK length/content does not match ARRAY_SIZE")
        if args.render_only:
            destination = (Path(args.output_dir).resolve() if args.output_dir else
                           SERIES / "tests" / "fixtures" / "rendered" /
                           f"{params['ARRAY_SIZE']}x1_M{args.mask}")
            fixture_root = (SERIES / "tests" / "fixtures").resolve()
            if destination != fixture_root and fixture_root not in destination.parents:
                raise ConfigError("render-only output must stay under tests/fixtures")
            result = render_case(user_values, stimulus_values, args.mask, destination,
                                 fixture_only=True,
                                 user_snapshot_text=user_snapshot_text,
                                 stimulus_snapshot_text=stimulus_snapshot_text)
            print(json.dumps({"status": result["status"], "output_dir": str(destination),
                              "physical_solve_count": 0, "josim_invoked": False}, indent=2))
            return 0
        if args.output_dir:
            raise ConfigError("--output-dir is only valid with --render-only")
        return execute_run(user_values, stimulus_values, args.mask,
                           run_id=args.run_id,
                           solver=Path(args.solver) if args.solver else None,
                           user_snapshot_text=user_snapshot_text,
                           stimulus_snapshot_text=stimulus_snapshot_text)
    except (ConfigError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
