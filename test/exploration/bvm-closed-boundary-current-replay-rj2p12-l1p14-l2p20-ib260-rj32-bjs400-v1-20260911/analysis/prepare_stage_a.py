#!/usr/bin/env python3
"""Register Stage A from an immutable closed-loop raw; never invokes JoSIM."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from decimal import Decimal, localcontext
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
SOURCE_EXP = REPO / "test/exploration/bvm-population-scaling-rj2p12-l1p14-l2p20-ib260-rj32-bjs400-v1-20260910"
SOURCE_RUN = "ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_0011"
SOURCE_DIR = SOURCE_EXP / "references/reused" / SOURCE_RUN
SOLVER = REPO / "build/josim-cli"
SOURCE_PACKAGE = SOURCE_EXP / "handoff/bvm-population-scaling-rj2p12-l1p14-l2p20-ib260-rj32-bjs400-v1-20260910_raw_handoff.zip"
CONTRACT_SENTENCE = "This experiment is governed by docs/EXPERIMENT_CONTRACT.md."
SOURCE_PACKAGE_SHA256 = "3ceba168be95b7e48cbb77ccb13d4f4133893cb39813c025b7d4a3f631a09dff"
SOURCE_PACKAGE_BYTES = 130901740
SOURCE_MANIFEST_SHA256 = "99be7c3d7ad62a4ff03684b7d1b127a98d5262b15bfcdb9e5dfecb598f930502"
SOLVER_SHA256 = "48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2"
SOURCE_SIGNAL = "I(B_JSL8)"
PWL_RE = re.compile(r"([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)[pP]\s+([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)")


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()


def remote_head() -> str | None:
    try:
        return subprocess.check_output(["git", "ls-remote", "bvm", "refs/heads/master"], cwd=REPO, text=True).split()[0]
    except (OSError, subprocess.CalledProcessError, IndexError):
        return None


def write_once(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_text(encoding="utf-8") != content:
            raise RuntimeError(f"refusing to overwrite existing artifact: {path}")
        return
    path.write_text(content, encoding="utf-8")


def write_json_once(path: Path, value: Any) -> None:
    write_once(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def control_values(kind: str, active: bool) -> str:
    if kind == "WL":
        points = "0 0 50p 0 51p -100u 60p -100u 61p 0 70p 0 71p +100u 80p +100u 81p 0 90p 0 91p +100u 100p +100u 101p 0"
    elif kind == "BL":
        points = "0 0 50p 0 51p -100u 60p -100u 61p 0 70p 0 71p 0 80p 0 81p 0 90p 0 91p +100u 100p +100u 101p 0"
    elif kind == "SE":
        points = "0 0 50p 0 51p 0 60p 0 61p 0 70p 0 71p +100u 80p +100u 81p 0 90p 0 91p 0 100p 0 101p 0"
    else:
        raise ValueError(kind)
    final = "+100u" if active and kind in {"WL", "SE"} else "0"
    return f"pwl({points} 110p 0 111p {final} 120p {final} 121p 0 200p 0)"


def read_source(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.reader(stream)
        header = next(reader)
        if header.count("time") != 1 or header.count(SOURCE_SIGNAL) != 1:
            raise RuntimeError(f"source column is missing or duplicated: {path}")
        ti, ii = header.index("time"), header.index(SOURCE_SIGNAL)
        rows = [{"time_s": row[ti], "current_A": row[ii]} for row in reader]
    if len(rows) < 2:
        raise RuntimeError("source raw has too few rows")
    times = [Decimal(row["time_s"]) for row in rows]
    values = [Decimal(row["current_A"]) for row in rows]
    if any(not value.is_finite() for value in (*times, *values)):
        raise RuntimeError("source raw contains non-finite value")
    if any(right <= left for left, right in zip(times, times[1:])):
        raise RuntimeError("source raw time is not strictly increasing")
    return header, rows


def fmt_time_ps(value: str) -> str:
    with localcontext() as context:
        context.prec = 60
        converted = Decimal(value) * Decimal("1e12")
    text = format(converted, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def pwl_lines(rows: list[dict[str, str]]) -> list[str]:
    pairs = [f"{fmt_time_ps(row['time_s'])}p {row['current_A']}" for row in rows]
    output: list[str] = []
    for start in range(0, len(pairs), 18):
        end = start + 18
        prefix = "I_REPLAY 0 QBIN pwl(" if start == 0 else "+ "
        output.append(prefix + " ".join(pairs[start:end]) + (")" if end >= len(pairs) else ""))
    return output


def replay_probes() -> list[str]:
    lines = [
        ".print V(QBIN) V(QBOUT)",
        ".print I(I_REPLAY)",
        ".print I(LIN|XBQ1) V(LIN|XBQ1) I(L1|XBQ1) V(L1|XBQ1) I(L2|XBQ1) V(L2|XBQ1) I(L3|XBQ1) V(L3|XBQ1)",
        ".print I(RJ1|XBQ1) V(RJ1|XBQ1) I(RJ2|XBQ1) V(RJ2|XBQ1) I(IB|XBQ1)",
    ]
    for junction in ("BJS", "BJ1", "BJ2"):
        lines.append(f".print P({junction}|XBQ1) V({junction}|XBQ1) I({junction}|XBQ1)")
    for stage in range(1, 7):
        handle = f"XJTL1_{stage}"
        lines.append(f".print P(B01|{handle}) V(B01|{handle}) I(B01|{handle}) P(B02|{handle}) V(B02|{handle}) I(B02|{handle})")
        lines.append(f".print V(JTL{stage}_OUT)")
    lines.append(".print I(R_TERM)")
    return lines


def replay_deck(snapshot: Path, rows: list[dict[str, str]]) -> str:
    lines = [
        "* GENERATED STAGE A CLOSED-BOUNDARY CURRENT REPLAY DECK",
        "* source_class=CURRENT_BJS400_POPULATION_CLOSED_LOOP_RAW",
        f"* source_snapshot={snapshot.relative_to(REPO).as_posix()}",
        f"* source_signal={SOURCE_SIGNAL}; sample_count={len(rows)}",
        "* transformation_registry=[]; exact stored pairs; no sign change",
        "* orientation=I_REPLAY 0 QBIN; positive current injects QBIN",
        "",
        ".param L1_VALUE=1.4p",
        ".param IB_VALUE=260u",
        ".param RJ1_VALUE=32",
        ".param RJ2_VALUE=12",
        ".include ../../inputs/jjmit.cir",
        ".include ../../inputs/BQ_parameterized_bjs400_rj2.cir",
        ".include ../../inputs/jtl2.cir",
        "",
        "XBQ1 QBIN QBOUT BQ",
        "XJTL1_1 QBOUT JTL1_OUT jtl",
        "XJTL1_2 JTL1_OUT JTL2_OUT jtl",
        "XJTL1_3 JTL2_OUT JTL3_OUT jtl",
        "XJTL1_4 JTL3_OUT JTL4_OUT jtl",
        "XJTL1_5 JTL4_OUT JTL5_OUT jtl",
        "XJTL1_6 JTL5_OUT JTL6_OUT jtl",
        "R_TERM JTL6_OUT 0 10",
        "",
    ]
    lines.extend(pwl_lines(rows))
    lines.extend(["", ".tran 0.1p 200p", ""])
    lines.extend(replay_probes())
    lines.extend([".end", ""])
    return "\n".join(lines)


def active_lines(path: Path) -> list[str]:
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip() and not line.lstrip().startswith(("*", ".", "+"))]


def deck_check(path: Path, pair_count: int) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    lines = active_lines(path)
    start = text.index("pwl(") + 4
    end = text.index(")", start)
    pairs = PWL_RE.findall(text[start:end])
    failures: list[str] = []
    if len(pairs) != pair_count:
        failures.append(f"PWL pair count {len(pairs)} != {pair_count}")
    if sum(line == "XBQ1 QBIN QBOUT BQ" for line in lines) != 1:
        failures.append("QB count mismatch")
    if sum(line.startswith("XJTL1_") and line.endswith(" jtl") for line in lines) != 6:
        failures.append("JTL count mismatch")
    if sum(line == "R_TERM JTL6_OUT 0 10" for line in lines) != 1:
        failures.append("terminal/load mismatch")
    if any(token in line for line in lines for token in ("BVM", "B_JSL", "COMMON_SL")):
        failures.append("source BVM/JSL leakage")
    for token in ("I_REPLAY 0 QBIN pwl(", ".param RJ2_VALUE=12", ".include ../../inputs/BQ_parameterized_bjs400_rj2.cir", ".include ../../inputs/jtl2.cir"):
        if token not in text:
            failures.append(f"missing replay token: {token}")
    if [line for line in text.splitlines() if line.lower().startswith(".tran")] != [".tran 0.1p 200p"]:
        failures.append("tran mismatch")
    return {"status": "PASS" if not failures else "FAIL", "path": path.relative_to(REPO).as_posix(), "sha256": sha256(path), "bytes": path.stat().st_size, "pwl_pair_count": len(pairs), "qb_count": sum(line == "XBQ1 QBIN QBOUT BQ" for line in lines), "jtl_count": sum(line.startswith("XJTL1_") and line.endswith(" jtl") for line in lines), "failures": failures}


def source_record(path: Path, role: str, origin: Path | None = None) -> dict[str, Any]:
    record: dict[str, Any] = {"path": path.relative_to(REPO).as_posix(), "sha256": sha256(path), "bytes": path.stat().st_size, "role": role}
    if origin is not None:
        record["origin_path"] = origin.relative_to(REPO).as_posix()
        record["origin_sha256"] = sha256(origin)
    return record


def build_source_manifest() -> dict[str, Any]:
    if not SOURCE_PACKAGE.is_file() or SOURCE_PACKAGE.stat().st_size != SOURCE_PACKAGE_BYTES or sha256(SOURCE_PACKAGE) != SOURCE_PACKAGE_SHA256:
        raise RuntimeError("current RJ2=12 population source package changed")
    source_manifest = SOURCE_EXP / "SOURCE_MANIFEST.json"
    if not source_manifest.is_file() or sha256(source_manifest) != SOURCE_MANIFEST_SHA256:
        raise RuntimeError("current RJ2=12 population source manifest changed")
    local_sources: list[dict[str, Any]] = []
    for name, role in (("BQ_parameterized_bjs400_rj2.cir", "current RJ2=12 BQ receiver include"), ("jtl2.cir", "current six-stage JTL include"), ("jjmit.cir", "current JJ model include")):
        local = EXP / "inputs" / name
        origin = SOURCE_EXP / "inputs" / name
        if not local.is_file() or sha256(local) != sha256(origin):
            raise RuntimeError(f"receiver input changed: {name}")
        local_sources.append(source_record(local, role, origin))
    if not SOLVER.is_file() or sha256(SOLVER) != SOLVER_SHA256:
        raise RuntimeError("solver identity changed")
    local_sources.append({"path": str(SOLVER.relative_to(REPO)), "sha256": sha256(SOLVER), "bytes": SOLVER.stat().st_size, "role": "solver identity", "version": subprocess.check_output([str(SOLVER), "--version"], cwd=REPO, text=True)})
    source_raw = EXP / "references/closed_loop_rj2p12" / SOURCE_RUN / "raw.csv"
    source_deck = source_raw.with_name("deck.cir")
    source_meta = source_raw.with_name("metadata.json")
    source_log = source_raw.with_name("run.log")
    source_origin_records = {name: source_record(path, "immutable current closed-loop RJ2=12 N2 source artifact", SOURCE_DIR / name) for name, path in (("raw.csv", source_raw), ("deck.cir", source_deck), ("metadata.json", source_meta), ("run.log", source_log))}
    return {"schema": "bvm-closed-boundary-current-replay-source-manifest-v1", "experiment_id": EXP.name, "created_at_local": now(), "repository_head_at_registration": head(), "remote_master_at_registration": remote_head(), "current_population_experiment": str(SOURCE_EXP.relative_to(REPO)), "current_population_source_manifest": source_record(source_manifest, "current population source authority manifest"), "current_population_package": source_record(SOURCE_PACKAGE, "current population evidence package"), "local_receiver_sources": local_sources, "source_reference": {"run_id": SOURCE_RUN, "signal": SOURCE_SIGNAL, "artifacts": source_origin_records, "source_not_rerun": True}, "orientation": {"closed_loop_branch": "B_JSL8 JSL_NODE7 QBIN", "replay_branch": "I_REPLAY 0 QBIN", "sign_change": False, "proof": "same first-to-second downstream convention; source branch was directly inspected"}, "transformations": [], "fixed_receiver": {"L1_pH": 1.4, "L2_pH": 2.0, "RJ1_ohm": 32.0, "RJ2_ohm": 12.0, "IBias_uA": 260.0, "BJS_area": 4, "BJ1_area": 0.9, "BJ2_area": 2, "L3_pH": 1.3, "jtl_stages": 6, "termination_ohm": 10.0}}


def preflight_markdown(record: dict[str, Any]) -> str:
    deck = record["stage_a"]["deck"]
    return "\n".join([
        "# Closed-boundary current replay — PREFLIGHT", "", CONTRACT_SENTENCE, "",
        f"- Experiment: `{EXP.name}`",
        f"- Initial registration HEAD: `{record['preregistration_head']}`",
        f"- Sealed preflight HEAD: `{record['head_at_preflight']}`",
        f"- Remote `bvm/master`: `{record.get('remote_master_at_preflight')}`",
        f"- Status: **{record['status']}**",
        "- Current-turn physical solve budget: exactly one Stage A N2 replay; physical solves before preflight: `0`.", "",
        "## Stage A", "",
        "The only current-turn solver case is `CLOSED_CURRENT_REPLAY_N2_0011_RJ2P12`. Its source is the immutable current RJ2=12 `0011` full closed-loop raw `I(B_JSL8)`. The source case is not rerun. The replay deck has only `I_REPLAY 0 QBIN`, the current RJ2=12 QB, six-stage JTL and 10 ohm termination.", "",
        f"- Replay deck: `{deck['path']}`",
        f"- PWL pairs registered: `{deck['pwl_pair_count']}`",
        f"- Deck QA: `{deck['status']}`",
        "- Orientation: positive `I(B_JSL8)` JSL7→QBIN maps directly to positive `I_REPLAY 0 QBIN`; no sign correction.", "",
        "## Stage B early-stop boundary", "",
        "N3 `CLOSED_CURRENT_REPLAY_N3_0111_RJ2P12` is deferred and has no current-turn source copy, deck or solve. The repository contract requires explicit `SCIENTIFIC_REVIEW_AUTHORIZED` before scientific classification can trigger a successor solve. Therefore this turn stops after Stage A evidence and records Stage B as `DEFERRED_PENDING_SCIENTIFIC_REVIEW_AUTHORIZATION`, even if mechanical navigation is complete.", "",
        "## Evidence ceiling", "",
        "P values remain raw radians; displays use `rad/(2*pi)` turns. Phase landmarks, threshold activity, voltage area and terminal area are navigation evidence only, not SFQ counts. Replay is ideal current forcing and is not a source-impedance or circuit-equivalent reconstruction.", "",
        "Machine record: `analysis/preflight.json`.", "",
    ])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh-head", action="store_true")
    args = parser.parse_args()
    source_manifest_path = EXP / "SOURCE_MANIFEST.json"
    if source_manifest_path.is_file():
        source_manifest = json.loads(source_manifest_path.read_text(encoding="utf-8"))
    else:
        source_manifest = build_source_manifest()
        write_json_once(source_manifest_path, source_manifest)
    raw_origin = SOURCE_DIR / "raw.csv"
    local_raw = EXP / "references/closed_loop_rj2p12" / SOURCE_RUN / "raw.csv"
    for name in ("raw.csv", "deck.cir", "metadata.json", "run.log"):
        local = local_raw.with_name(name)
        origin = SOURCE_DIR / name
        if not local.is_file() or not origin.is_file() or sha256(local) != sha256(origin):
            raise RuntimeError(f"immutable source copy mismatch: {name}")
    _, rows = read_source(local_raw)
    snapshot = EXP / "data/CLOSED_LOOP_N2_I_BJSL8_source.csv"
    snapshot_text = "time_s,current_A\n" + "\n".join(f"{row['time_s']},{row['current_A']}" for row in rows) + "\n"
    write_once(snapshot, snapshot_text)
    deck_path = EXP / "runs/CLOSED_CURRENT_REPLAY_N2_0011_RJ2P12/deck.cir"
    write_once(deck_path, replay_deck(snapshot, rows))
    deck = deck_check(deck_path, len(rows))
    failures = list(deck["failures"])
    base = json.loads((EXP / "analysis/preflight.json").read_text(encoding="utf-8")) if (EXP / "analysis/preflight.json").is_file() else {"preregistration_head": head()}
    record: dict[str, Any] = {"schema": "bvm-closed-boundary-current-replay-preflight-v1", "experiment_id": EXP.name, "created_at_local": now(), "status": "PASS" if not failures else "FAIL", "preregistration_head": base.get("preregistration_head", head()), "head_at_preflight": head(), "head_refresh": args.refresh_head, "remote_master_at_preflight": remote_head(), "authorized_current_turn_runs": ["CLOSED_CURRENT_REPLAY_N2_0011_RJ2P12"], "authorized_current_turn_physical_solve_count": 1, "maximum_task_physical_solve_count": 2, "physical_solve_count_before_preflight": 0, "stage_a": {"case": "CLOSED_CURRENT_REPLAY_N2_0011_RJ2P12", "source_run": SOURCE_RUN, "source_signal": SOURCE_SIGNAL, "source_raw_sha256": sha256(local_raw), "source_snapshot_sha256": sha256(snapshot), "source_sample_count": len(rows), "deck": deck, "pass_rule": "multi-evidence raw review required; response count not operator-defined"}, "stage_b": {"case": "CLOSED_CURRENT_REPLAY_N3_0111_RJ2P12", "status": "DEFERRED_PENDING_SCIENTIFIC_REVIEW_AUTHORIZATION", "execution_gate": "STAGE_A_PASS_AND_SCIENTIFIC_REVIEW_AUTHORIZED", "source_copied": False, "physical_solve_authorized_current_turn": False}, "orientation_status": "PASS: direct JSL_NODE7 -> QBIN source branch and 0 -> QBIN replay branch", "transformations": [], "scientific_analysis_performed": False, "failures": failures, "source_manifest_sha256": sha256(source_manifest_path), "source_authority": source_manifest}
    text = json.dumps(record, ensure_ascii=False, indent=2) + "\n"
    output = EXP / "analysis/preflight.json"
    if args.refresh_head:
        output.write_text(text, encoding="utf-8")
        (EXP / "PREFLIGHT.md").write_text(preflight_markdown(record), encoding="utf-8")
        (EXP / "analysis/STAGE_A_PREFLIGHT.md").write_text(preflight_markdown(record), encoding="utf-8")
    else:
        write_once(output, text)
        write_once(EXP / "PREFLIGHT.md", preflight_markdown(record))
        write_once(EXP / "analysis/STAGE_A_PREFLIGHT.md", preflight_markdown(record))
    print(json.dumps({"status": record["status"], "head": record["head_at_preflight"], "source_sample_count": len(rows), "authorized_current_turn_physical_solve_count": 1, "stage_b": record["stage_b"]["status"], "scientific_analysis_performed": False}, ensure_ascii=False, indent=2))
    return 0 if record["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
