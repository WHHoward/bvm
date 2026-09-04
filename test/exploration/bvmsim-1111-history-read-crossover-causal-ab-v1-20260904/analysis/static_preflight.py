#!/usr/bin/env python3
"""Mechanical preflight for the two-condition history crossover."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
OLD_PARENT = REPO / "test/exploration/bvmsim-4bvm-jm2-connected-state-position-ab-v1-20260903/runs/1111/deck.cir"
NEW_PARENT = REPO / "test/exploration/bvmsim-4bvm-allone-selective-read-additivity-isolation-v1-20260904/runs/1111/deck.cir"
OLD_RAW = REPO / "test/exploration/bvmsim-4bvm-jm2-connected-state-position-ab-v1-20260903/runs/1111/raw.csv"
NEW_RAW = REPO / "test/exploration/bvmsim-4bvm-allone-selective-read-additivity-isolation-v1-20260904/runs/1111/raw.csv"
SOLVER = REPO / "build/josim-cli"
VARIANT = REPO / "test/exploration/bvmsim-jm2-connected-single-ab-v1-20260903/variants/bvm_jm2_connected.cir"
SHARED_JJMIT = REPO / "circuits/models/jjmit.cir"

OLD_PARENT_SHA256 = "3fcdb8b0d61c91cadcacee77c3c06b3a03f8f9392a8c838e9b8574b8938b4e88"
NEW_PARENT_SHA256 = "5ee085051cfdc2cc6e45deac657230e86c64795d9cd9be100735b13974c3222e"
OLD_RAW_SHA256 = "9563ac09d75770cd9d9c2f2a93de0f418778012e64adb40fbf118ae0561d813f"
NEW_RAW_SHA256 = "b3d421822dd893d17331016b7f954784d24c90c97f58bc362676467c7650998b"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO.resolve()).as_posix()


def active_print_labels(text: str) -> list[str]:
    result: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith(".print"):
            result.extend(stripped.split()[1:])
    return result


def normalized_physics(text: str) -> list[str]:
    result: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("*") or stripped.startswith(".print"):
            continue
        if re.match(r"^I_(WL|BL|SE)[1-4]\s+", stripped):
            continue
        result.append(stripped)
    return result


def parse_scalar(token: str) -> float:
    token = token.strip()
    match = re.fullmatch(r"([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)([fpnumkKMGTP]?)", token)
    if not match:
        raise RuntimeError(f"unsupported numeric PWL token: {token!r}")
    value = float(match.group(1))
    suffix = match.group(2).lower()
    factor = {"": 1.0, "f": 1e-15, "p": 1e-12, "n": 1e-9, "u": 1e-6, "m": 1e-3, "k": 1e3, "g": 1e9, "t": 1e12}.get(suffix)
    if factor is None:
        raise RuntimeError(f"unsupported numeric suffix: {token!r}")
    return value * factor


def source_map(text: str) -> dict[str, tuple[tuple[float, float], ...]]:
    result: dict[str, tuple[tuple[float, float], ...]] = {}
    pattern = re.compile(r"^(I_(?:WL|BL|SE)[1-4])\s+.*?pwl\((.*)\)\s*$", re.I)
    for line in text.splitlines():
        if line.lstrip().startswith("*"):
            continue
        match = pattern.match(line.strip())
        if not match:
            continue
        tokens = match.group(2).split()
        if len(tokens) % 2:
            raise RuntimeError(f"odd PWL token count: {match.group(1)}")
        points = tuple((parse_scalar(tokens[i]), parse_scalar(tokens[i + 1])) for i in range(0, len(tokens), 2))
        result[match.group(1)] = points
    expected = {f"I_{control}{number}" for number in range(1, 5) for control in ("WL", "BL", "SE")}
    if set(result) != expected:
        raise RuntimeError(f"PWL source set mismatch: missing={sorted(expected - set(result))}")
    return result


def pwl_value(points: tuple[tuple[float, float], ...], time_s: float) -> float:
    if time_s <= points[0][0]:
        return points[0][1]
    if time_s >= points[-1][0]:
        return points[-1][1]
    for left, right in zip(points, points[1:]):
        if left[0] <= time_s <= right[0]:
            fraction = (time_s - left[0]) / (right[0] - left[0])
            return left[1] + fraction * (right[1] - left[1])
    raise RuntimeError("PWL point lookup failed")


def source_diff(a: tuple[tuple[float, float], ...], b: tuple[tuple[float, float], ...], start_ps: float, end_ps: float) -> float:
    start_s, end_s = start_ps * 1e-12, end_ps * 1e-12
    times = {start_s, end_s}
    times.update(point[0] for point in a if start_s <= point[0] <= end_s)
    times.update(point[0] for point in b if start_s <= point[0] <= end_s)
    return max(abs(pwl_value(a, time) - pwl_value(b, time)) for time in sorted(times))


def pair_source_diff(a: dict[str, tuple[tuple[float, float], ...]], b: dict[str, tuple[tuple[float, float], ...]], start_ps: float, end_ps: float, names: list[str] | None = None) -> dict[str, float]:
    selected = names or sorted(a)
    return {name: source_diff(a[name], b[name], start_ps, end_ps) for name in selected}


def noncomment_physics_diff(a: list[str], b: list[str]) -> dict[str, object]:
    if a == b:
        return {"count": 0, "only_a": [], "only_b": [], "equal": True}
    return {"count": sum(left != right for left, right in zip(a, b)) + abs(len(a) - len(b)), "only_a": [line for line in a if line not in b], "only_b": [line for line in b if line not in a], "equal": False}


def expected_probe_labels() -> list[str]:
    return active_print_labels(NEW_PARENT.read_text(encoding="utf-8"))


def ensure(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def run_checks(require_clean: bool) -> dict[str, object]:
    status = subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=all"], cwd=REPO, text=True).splitlines()
    if require_clean:
        ensure(not status, f"working tree is not clean: {status}")
    for path, expected in ((OLD_PARENT, OLD_PARENT_SHA256), (NEW_PARENT, NEW_PARENT_SHA256), (OLD_RAW, OLD_RAW_SHA256), (NEW_RAW, NEW_RAW_SHA256)):
        ensure(path.is_file() and sha256(path) == expected, f"immutable parent hash mismatch: {path}")
    ensure(SOLVER.is_file() and SOLVER.stat().st_mode & 0o111, f"solver unavailable: {SOLVER}")
    ensure(VARIANT.is_file() and SHARED_JJMIT.is_file(), "required model/variant source missing")
    old_parent_text = OLD_PARENT.read_text(encoding="utf-8")
    new_parent_text = NEW_PARENT.read_text(encoding="utf-8")
    old_deck_path = EXP / "runs/OLD-NO-HISTORY/deck.cir"
    new_deck_path = EXP / "runs/NEW-WITH-HISTORY/deck.cir"
    ensure(old_deck_path.is_file() and new_deck_path.is_file(), "generated deck missing")
    old_text = old_deck_path.read_text(encoding="utf-8")
    new_text = new_deck_path.read_text(encoding="utf-8")
    labels = expected_probe_labels()
    ensure(labels and len(labels) == len(set(labels)), "NEW parent probe schema is empty or duplicated")
    ensure(active_print_labels(old_text) == labels, "O- does not use the complete current probe schema")
    ensure(active_print_labels(new_text) == labels, "N+ does not use the complete current probe schema")
    output_absent: dict[str, bool] = {}
    for condition in ("OLD-NO-HISTORY", "NEW-WITH-HISTORY"):
        for name in ("raw.csv", "run.log", "metadata.json"):
            path = EXP / "runs" / condition / name
            output_absent[f"{condition}/{name}"] = not path.exists()
            ensure(not path.exists(), f"refusing to overwrite existing new artifact: {path}")
    ensure(noncomment_physics_diff(normalized_physics(old_parent_text), normalized_physics(old_text))["equal"], "O- has unclassified physics difference")
    ensure(noncomment_physics_diff(normalized_physics(new_parent_text), normalized_physics(new_text))["equal"], "N+ has unclassified physics difference")
    ensure(noncomment_physics_diff(normalized_physics(old_parent_text), normalized_physics(new_parent_text))["equal"], "OLD/NEW parent physics closure is not identical")
    old_parent_sources = source_map(old_parent_text)
    new_parent_sources = source_map(new_parent_text)
    old_sources = source_map(old_text)
    new_sources = source_map(new_text)
    history_present_old_new = pair_source_diff(old_parent_sources, new_sources, 70, 81, [f"I_{control}{number}" for number in range(1, 5) for control in ("WL", "SE")])
    history_absent_old_new = pair_source_diff(old_sources, new_parent_sources, 70, 81, [f"I_{control}{number}" for number in range(1, 5) for control in ("WL", "SE")])
    ensure(max(history_present_old_new.values()) == 0.0, "N+ history waveform is not exact OLD history")
    ensure(max(history_absent_old_new.values()) == 0.0, "O-/N- absent history semantics differ")
    bl_parity = pair_source_diff(old_parent_sources, new_parent_sources, 0, 200, [f"I_BL{number}" for number in range(1, 5)])
    ensure(max(bl_parity.values()) == 0.0, "BL semantics differ between OLD and NEW contexts")
    write1_parity = pair_source_diff(old_parent_sources, new_parent_sources, 90, 101)
    read1_parity = pair_source_diff(old_parent_sources, new_parent_sources, 110, 121)
    ensure(max(write1_parity.values()) == 0.0, "WRITE1 source semantics differ")
    ensure(max(read1_parity.values()) == 0.0, "final READ1 source semantics differ")
    outside_history_old = pair_source_diff(old_parent_sources, old_sources, 0, 70)
    outside_history_old.update(pair_source_diff(old_parent_sources, old_sources, 81, 200))
    outside_history_new = pair_source_diff(new_parent_sources, new_sources, 0, 70)
    outside_history_new.update(pair_source_diff(new_parent_sources, new_sources, 81, 200))
    ensure(max(outside_history_old.values()) == 0.0 and max(outside_history_new.values()) == 0.0, "source changed outside history window")
    tran_lines = [line.strip() for line in (old_text + "\n" + new_text).splitlines() if line.strip().lower().startswith(".tran ")]
    ensure(tran_lines == [".tran 0.1p 200p 45p", ".tran 0.1p 200p 45p"], "timestep/stop/output-start changed")
    for text, label in ((old_text, "O-"), (new_text, "N+")):
        ensure("bvm_jm2_connected.cir" in text, f"{label}: JM2-connected variant include missing")
        ensure("BVMSim/BQ.cir" in text and "BVMSim/library_josim/jtl2.cir" in text, f"{label}: QB/JTL model closure changed")
        ensure("RBQ1 o6 0 10" in text, f"{label}: termination changed")
        ensure(text.count("XBVM") >= 4 and text.count("xjtl1_") >= 6, f"{label}: topology instance count changed")
    provenance = json.loads((EXP / "provenance.json").read_text(encoding="utf-8"))
    ensure(provenance["parents"]["O+"]["raw_sha256"] == OLD_RAW_SHA256 and provenance["parents"]["N-"]["raw_sha256"] == NEW_RAW_SHA256, "provenance parent raw hashes disagree")
    return {
        "schema": "bvmsim-1111-history-read-crossover-static-preflight-v1",
        "status": "PASS",
        "require_clean": require_clean,
        "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip(),
        "git_status": status,
        "physical_difference_count": {"O-_vs_O+": 0, "N+_vs_N-": 0, "O+_vs_N-": 0},
        "allowed_changes": {"O-": ["70--81 ps history controls", "additional full-schema .print probes"], "N+": ["70--81 ps history controls"]},
        "history_present_max_abs_A": max(history_present_old_new.values()),
        "history_absent_max_abs_A": max(history_absent_old_new.values()),
        "bl_max_abs_A": max(bl_parity.values()),
        "write1_max_abs_A": max(write1_parity.values()),
        "read1_max_abs_A": max(read1_parity.values()),
        "outside_history_max_abs_A": max(max(outside_history_old.values()), max(outside_history_new.values())),
        "probe_count": len(labels),
        "output_absent": output_absent,
        "source_hashes": {"jm2_connected_variant": sha256(VARIANT), "shared_jjmit": sha256(SHARED_JJMIT), "solver": sha256(SOLVER), "old_parent_deck": OLD_PARENT_SHA256, "new_parent_deck": NEW_PARENT_SHA256, "old_parent_raw": OLD_RAW_SHA256, "new_parent_raw": NEW_RAW_SHA256},
        "solver_version": subprocess.run([str(SOLVER), "--version"], cwd=REPO, capture_output=True, text=True, check=False).stdout.strip(),
        "decks": {"O-": {"path": rel(old_deck_path), "sha256": sha256(old_deck_path)}, "N+": {"path": rel(new_deck_path), "sha256": sha256(new_deck_path)}},
        "history_source_comparison": {"O+_vs_N+_present": history_present_old_new, "O-_vs_N-_absent": history_absent_old_new},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--require-clean", action="store_true")
    parser.add_argument("--write-report", action="store_true")
    args = parser.parse_args()
    result = run_checks(args.require_clean)
    if args.write_report:
        path = EXP / "analysis/static_preflight.json"
        if path.exists():
            raise RuntimeError(f"refusing to overwrite preflight report: {path}")
        path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"STATIC_PREFLIGHT_FAIL: {exc}", file=__import__("sys").stderr)
        raise SystemExit(1)
