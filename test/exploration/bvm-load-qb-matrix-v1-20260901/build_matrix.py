#!/usr/bin/env python3
"""Build the preregistered BVM/JSL/QB experiment matrix.

The builder only creates immutable input snapshots and fixtures. It never
overwrites a non-identical file and never runs JoSIM. Replay fixtures are
created only after their source CSVs exist.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
INPUTS = ROOT / "inputs"
RAW = ROOT / "raw"
LOGS = ROOT / "logs"
PROVENANCE = ROOT / "provenance"
MANIFEST = ROOT / "manifest.yaml"
METRIC_SPEC = REPO / "docs/research/METRIC_SPEC_V2.md"
SNAPSHOT_SOURCE = REPO / "test/exploration/bvm-read-semantics-audit-and-jsl-width-bracket-v1-20260824/inputs"
SOLVER = REPO / "build/josim-cli"

ROLES = (
    "logical1_read",
    "logical0_read",
    "logical1_no_read_control",
    "logical0_no_read_control",
)
WIDTHS = (9, 13)
LOADS: dict[str, dict[str, Any]] = {
    "12x320": {"count": 12, "area": 3.2, "ic_uA": 320.0},
    "8x500": {"count": 8, "area": 5.0, "ic_uA": 500.0},
}
SNAPSHOTS = ("jjmit.cir", "bvm_cell.cir", "bq_cell.cir")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_exact(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_text(encoding="utf-8") != text:
            raise SystemExit(f"refusing to overwrite non-identical file: {path}")
        return
    path.write_text(text, encoding="utf-8")


def copy_exact(source: Path, target: Path) -> None:
    data = source.read_bytes()
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        if target.read_bytes() != data:
            raise SystemExit(f"refusing to overwrite non-identical snapshot: {target}")
        return
    target.write_bytes(data)


def git_snapshot() -> dict[str, Any]:
    status = subprocess.run(
        ["git", "status", "--short"], cwd=REPO, text=True,
        capture_output=True, check=True,
    ).stdout
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=REPO, text=True,
        capture_output=True, check=True,
    ).stdout.strip()
    return {"head": head, "dirty": bool(status.strip()), "status": status}


def ensure_snapshots() -> dict[str, dict[str, str]]:
    snapshots: dict[str, dict[str, str]] = {}
    for name in SNAPSHOTS:
        source = SNAPSHOT_SOURCE / name
        target = INPUTS / name
        if not source.exists():
            raise SystemExit(f"missing model snapshot source: {source}")
        copy_exact(source, target)
        snapshots[name] = {
            "source": source.relative_to(REPO).as_posix(),
            "path": target.relative_to(ROOT).as_posix(),
            "sha256": sha256(target),
        }
    return snapshots


def source_lines(state: str, width_ps: int) -> list[str]:
    init = "+100U" if state == "logical1" else "-100U"
    read_end = 96 + width_ps
    fall = read_end + 1
    return [
        f"I_WL1 0 WL1 pwl(0p 0 10p 0 11p {init} 20p {init} 21p 0 95p 0 96p +100U {read_end}p +100U {fall}p 0 170p 0)",
        f"I_BL1 0 BL1 pwl(0p 0 10p 0 11p {init} 20p {init} 21p 0 170p 0)",
        f"I_SE1 0 SE1 pwl(0p 0 95p 0 96p +100U {read_end}p +100U {fall}p 0 170p 0)",
    ]


def no_read_lines(state: str, width_ps: int) -> list[str]:
    init = "+100U" if state == "logical1" else "-100U"
    read_end = 96 + width_ps
    fall = read_end + 1
    return [
        f"I_WL1 0 WL1 pwl(0p 0 10p 0 11p {init} 20p {init} 21p 0 95p 0 96p 0 {read_end}p 0 {fall}p 0 170p 0)",
        f"I_BL1 0 BL1 pwl(0p 0 10p 0 11p {init} 20p {init} 21p 0 170p 0)",
        f"I_SE1 0 SE1 pwl(0p 0 95p 0 96p 0 {read_end}p 0 {fall}p 0 170p 0)",
    ]


def stimulus(state: str, width_ps: int, read: bool) -> list[str]:
    return source_lines(state, width_ps) if read else no_read_lines(state, width_ps)


def jsl_lines(count: int, area: float, endpoint: str) -> list[str]:
    lines: list[str] = []
    for index in range(1, count + 1):
        left = "SL1" if index == 1 else f"njsl{index - 1}"
        right = endpoint if index == count else f"njsl{index}"
        lines.append(f"B_LD{index:<2} {left:<7} {right:<7} jjmit area={area:g}")
    return lines


def bvm_prints(count: int) -> list[str]:
    lines = [
        ".print P(B_JM1|XBVM1) V(B_JM1|XBVM1) P(B_JM2|XBVM1) V(B_JM2|XBVM1)",
        ".print P(B_JS1|XBVM1) V(B_JS1|XBVM1) P(B_JS2|XBVM1) V(B_JS2|XBVM1)",
        f".print V(N6|XBVM1) V(SL1) V(njsl{count - 1})",
        f".print I(L_PSL|XBVM1) I(L_SL|XBVM1) I(B_LD1) I(B_LD{count})",
    ]
    for index in range(1, count + 1):
        lines.append(f".print P(B_LD{index}) V(B_LD{index}) I(B_LD{index})")
    lines.append(".print I(I_WL1) I(I_BL1) I(I_SE1)")
    return lines


def qb_prints() -> list[str]:
    return [
        ".print P(BJs|XBQ) V(BJs|XBQ) I(BJs|XBQ)",
        ".print P(BJL1|XBQ) V(BJL1|XBQ) I(BJL1|XBQ)",
        ".print P(BJL2|XBQ) V(BJL2|XBQ) I(BJL2|XBQ)",
        ".print V(IN) V(OUT) I(Lin|XBQ) I(L0|XBQ) I(L1|XBQ) I(L2|XBQ)",
        ".print I(RB|XBQ) I(RJ1|XBQ) I(RJ2|XBQ) I(R_LOAD) I(I_IBIAS)",
    ]


def role_parts(role: str) -> tuple[str, bool]:
    state = "logical1" if role.startswith("logical1") else "logical0"
    read = role.endswith("_read")
    return state, read


def fixture_deck(kind: str, width_ps: int, load_name: str, role: str) -> str:
    load = LOADS[load_name]
    state, read = role_parts(role)
    include = "../../../"
    lines = [
        f"* BVM_LOAD_QB_MATRIX_V1: {kind} {width_ps}ps {load_name} {role}",
        "* canonical BVM -> series JSL -> QB; no magnetic coupling, JTL, or T1",
        f".include {include}jjmit.cir",
        f".include {include}bvm_cell.cir",
        "XBVM1 WL1 BL1 SE1 SL1 BVM",
    ]
    endpoint = "0" if kind == "source" else "IN"
    lines += jsl_lines(int(load["count"]), float(load["area"]), endpoint)
    if kind == "physical":
        lines += [
            f".include {include}bq_cell.cir",
            "XBQ IN OUT IBIAS BQ",
            "R_LOAD OUT 0 10",
            "I_IBIAS 0 IBIAS pwl(0p 0 1p 35u 2p 35u 170p 35u)",
        ]
    lines += stimulus(state, width_ps, read)
    lines += [".tran 0.0125p 170p", *bvm_prints(int(load["count"]))]
    if kind == "physical":
        lines += qb_prints()
    lines += [".end"]
    return "\n".join(lines) + "\n"


def load_csv_current(path: Path) -> list[tuple[float, float]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        header = [item.strip().strip('"') for item in next(reader)]
        if "time" not in header or "I(B_LD1)" not in header:
            raise ValueError(f"source CSV lacks time/I(B_LD1): {path}")
        time_index = header.index("time")
        current_index = header.index("I(B_LD1)")
        samples: list[tuple[float, float]] = []
        previous = -float("inf")
        for row in reader:
            if not row:
                continue
            time_ps = float(row[time_index]) * 1e12
            current = float(row[current_index])
            if time_ps <= previous:
                raise ValueError(f"non-increasing source time: {path}")
            samples.append((time_ps, current))
            previous = time_ps
    if len(samples) < 2:
        raise ValueError(f"source CSV is empty: {path}")
    return samples


def fmt(value: float) -> str:
    return f"{value:.17g}"


def replay_lines(samples: list[tuple[float, float]]) -> list[str]:
    pairs = [f"{fmt(time_ps)}p {fmt(current)}" for time_ps, current in samples]
    chunks = [pairs[index:index + 18] for index in range(0, len(pairs), 18)]
    lines = ["I_REPLAY 0 IN pwl(" + " ".join(chunks[0])]
    for chunk in chunks[1:]:
        lines.append("+ " + " ".join(chunk))
    lines[-1] += ")"
    return lines


def replay_deck(width_ps: int, load_name: str, role: str, source_path: Path) -> str:
    samples = load_csv_current(source_path)
    source_rel = source_path.relative_to(ROOT).as_posix()
    lines = [
        f"* BVM_LOAD_QB_MATRIX_V1: ideal replay {width_ps}ps {load_name} {role}",
        f"* exact I(B_LD1)(t) from {source_rel}; no reshape/hold/scale/resample",
        ".include ../../../jjmit.cir",
        ".include ../../../bq_cell.cir",
        "XBQ IN OUT IBIAS BQ",
        *replay_lines(samples),
        "R_LOAD OUT 0 10",
        "I_IBIAS 0 IBIAS pwl(0p 0 1p 35u 2p 35u 170p 35u)",
        ".tran 0.0125p 170p",
        *qb_prints(),
        ".print I(I_REPLAY)",
        ".end",
    ]
    return "\n".join(lines) + "\n"


def case_record(kind: str, width_ps: int, load_name: str, role: str) -> dict[str, Any]:
    deck = ROOT / "inputs" / kind / f"{width_ps}ps" / load_name / f"{role}.cir"
    raw = ROOT / "raw" / kind / f"{width_ps}ps" / load_name / role / "run-01.csv"
    return {
        "kind": kind,
        "width_ps": width_ps,
        "load": load_name,
        "role": role,
        "deck": deck.relative_to(ROOT).as_posix(),
        "raw": raw.relative_to(ROOT).as_posix(),
    }


def initial_manifest(snapshot_info: dict[str, dict[str, str]], git: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "BVM_LOAD_QB_MATRIX_V1",
        "recorded_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "mode": "exploratory",
        "parent_head": git["head"],
        "git_dirty_before_build": git["dirty"],
        "metric_spec": {
            "path": METRIC_SPEC.relative_to(REPO).as_posix(),
            "version": "2.0.0",
            "sha256": sha256(METRIC_SPEC),
        },
        "solver": {
            "path": SOLVER.relative_to(REPO).as_posix(),
            "version": "v2.7.2837d13",
            "sha256": sha256(SOLVER),
        },
        "research_question": "在9/13 ps与12x320/8x500 JSL条件下，真实BVM源波形是否能经JSL传递并在scaled QB输出端形成有状态差异？",
        "hypotheses": {
            "primary": "不同JSL负载会改变BVM源端和QB输入/输出轨迹，至少一个点可能有state-selective QB output activity。",
            "alternatives": [
                "JSL load-line改变BVM source waveform或storage state",
                "QB input有state-dependent activity但内部transfer或R_LOAD输出不足",
                "read0或no-read control出现非零活动/自由运行",
                "结果随时间步改变而不可判定",
            ],
        },
        "topology": {
            "source": "BVM SL -> N series JSL -> GND",
            "replay": "I_REPLAY exact source I(B_LD1)(t) -> QB IN",
            "physical": "BVM SL -> N series JSL -> QB IN -> scaled QB -> R_LOAD",
            "magnetic_coupling": False,
            "jsl_bypass": False,
        },
        "loads": LOADS,
        "stimulus": {
            "initialization": "logical1=+100uA WL+BL; logical0=-100uA WL+BL",
            "read": "positive +100uA WL+SE",
            "start_ps": 96.0,
            "widths_ps": list(WIDTHS),
            "stop_ps": 170.0,
        },
        "simulation": {
            "requested_timestep_ps": 0.0125,
            "stop_time_ps": 170.0,
            "repetitions": 1,
            "qb": {
                "BJs_area": 0.5, "BJL1_area": 0.36, "BJL2_area": 0.54,
                "Lin_pH": 0.8, "L0_pH": 1.323, "L1_pH": 3.91, "L2_pH": 3.91,
                "RJ1_ohm": 33.0, "RJ2_ohm": 22.0, "RB_ohm": 6.0,
                "IBIAS_uA": 35.0, "RLOAD_ohm": 10.0,
            },
        },
        "windows_ps": {"pre": [80.0, 94.0], "activity": [94.0, 130.0], "post": [140.0, 170.0]},
        "roles": list(ROLES),
        "snapshots": snapshot_info,
        "cases": [],
        "artifacts": {"raw_sha256": [], "log_files": []},
        "status": "PRE_REGISTERED",
        "claim_ceiling": "exploratory simulation observations; no hardware or downstream JTL claim",
    }


def write_manifest(manifest: dict[str, Any]) -> None:
    text = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    if MANIFEST.exists():
        existing = json.loads(MANIFEST.read_text(encoding="utf-8"))
        if existing.get("schema_version") != manifest.get("schema_version"):
            raise SystemExit(f"refusing to update manifest with a different schema: {MANIFEST}")
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(text, encoding="utf-8")


def build_initial() -> None:
    git = git_snapshot()
    INPUTS.mkdir(parents=True, exist_ok=True)
    RAW.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    PROVENANCE.mkdir(parents=True, exist_ok=True)
    write_exact(PROVENANCE / "git_status_before_build.txt", git["status"])
    snapshot_info = ensure_snapshots()
    manifest = initial_manifest(snapshot_info, git)
    for kind in ("source", "physical"):
        for width_ps in WIDTHS:
            for load_name in LOADS:
                for role in ROLES:
                    deck_path = ROOT / "inputs" / kind / f"{width_ps}ps" / load_name / f"{role}.cir"
                    write_exact(deck_path, fixture_deck(kind, width_ps, load_name, role))
                    manifest["cases"].append(case_record(kind, width_ps, load_name, role))
    manifest["execution"] = {"planned_runs": len(manifest["cases"]), "source_and_physical": "planned"}
    write_manifest(manifest)
    print(json.dumps({"status": "PASS", "phase": "initial", "planned_runs": len(manifest["cases"])}, ensure_ascii=False))


def build_replay() -> None:
    if not MANIFEST.exists():
        raise SystemExit("run the initial build before replay build")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    existing = {(item["kind"], item["width_ps"], item["load"], item["role"]) for item in manifest.get("cases", [])}
    added = 0
    for width_ps in WIDTHS:
        for load_name in LOADS:
            for role in ROLES:
                source_path = ROOT / "raw" / "source" / f"{width_ps}ps" / load_name / role / "run-01.csv"
                if not source_path.exists():
                    raise SystemExit(f"missing source raw; cannot build replay: {source_path}")
                deck_path = ROOT / "inputs" / "replay" / f"{width_ps}ps" / load_name / f"{role}.cir"
                write_exact(deck_path, replay_deck(width_ps, load_name, role, source_path))
                key = ("replay", width_ps, load_name, role)
                if key not in existing:
                    manifest["cases"].append(case_record(*key))
                    added += 1
    manifest["execution"]["planned_runs"] = len(manifest["cases"])
    manifest["execution"]["replay_built_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
    write_manifest(manifest)
    print(json.dumps({"status": "PASS", "phase": "replay", "added_runs": added, "planned_runs": len(manifest["cases"])}, ensure_ascii=False))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=("initial", "replay"), required=True)
    args = parser.parse_args()
    if args.phase == "initial":
        build_initial()
    else:
        build_replay()


if __name__ == "__main__":
    main()
