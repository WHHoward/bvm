#!/usr/bin/env python3
"""Register the authorized Stage B N3 source/deck without solving."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
SOURCE_EXP = REPO / "test/exploration/bvm-population-scaling-rj2p12-l1p14-l2p20-ib260-rj32-bjs400-v1-20260910"
SOURCE_RUN = "ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_0111"
SOURCE_DIR = SOURCE_EXP / "runs" / SOURCE_RUN
REF_DIR = EXP / "references/closed_loop_rj2p12" / SOURCE_RUN
SOLVER_SHA256 = "48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2"
AUTH_PATH = Path("/home/howard/.codex/attachments/4165b042-06a5-403a-bcdc-f8571e14e6c7/pasted-text.txt")
AUTH_SHA256 = "441a7707ec2d4c53322601e543c650f98ee8d80023349950c2c1149ee1104c3c"

sys.path.insert(0, str(EXP / "analysis"))
from prepare_stage_a import deck_check, read_source, replay_deck, sha256, write_once  # noqa: E402


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()


def remote_head() -> str | None:
    try:
        return subprocess.check_output(["git", "ls-remote", "bvm", "refs/heads/master"], cwd=REPO, text=True).split()[0]
    except (OSError, subprocess.CalledProcessError, IndexError):
        return None


def record(path: Path, role: str, origin: Path | None = None) -> dict[str, Any]:
    value: dict[str, Any] = {"path": path.relative_to(REPO).as_posix(), "sha256": sha256(path), "bytes": path.stat().st_size, "role": role}
    if origin is not None:
        value["origin_path"] = origin.relative_to(REPO).as_posix()
        value["origin_sha256"] = sha256(origin)
    return value


def stage_b_preflight_markdown(value: dict[str, Any]) -> str:
    deck = value["stage_b"]["deck"]
    return "\n".join([
        "# Closed-boundary current replay — Stage B PREFLIGHT", "", "This experiment is governed by docs/EXPERIMENT_CONTRACT.md.", "",
        f"- Experiment: `{EXP.name}`",
        f"- Stage A scientific review attachment SHA-256: `{value['authorization']['attachment_sha256']}`",
        f"- Stage B preflight HEAD: `{value['head_at_preflight']}`",
        f"- Remote `bvm/master`: `{value.get('remote_master_at_preflight')}`",
        f"- Status: **{value['status']}**",
        "- Stage A consumed: `1` physical solve; Stage B authorized: exactly `1` additional solve; total maximum: `2`.", "",
        "## Authorization", "",
        "The current user supplied a completed direct raw review and explicitly recorded `STAGE_A_SCIENTIFIC_GATE = PASS` and `STAGE_B_AUTHORIZED = TRUE`, with scope restricted to the N3 replay. The attachment is hash-bound in `analysis/stage_b_authorization.json`.", "",
        "## Stage B N3", "",
        "The source is the existing current RJ2=12/0111 full closed-loop raw and is not rerun. The replay deck contains only `I_REPLAY 0 QBIN`, the current RJ2=12 QB, six-stage JTL and 10 ohm termination. No BVM, COMMON_SL or JSL source element is present in the active replay netlist.", "",
        f"- Case: `CLOSED_CURRENT_REPLAY_N3_0111_RJ2P12`",
        f"- Source raw SHA-256: `{value['stage_b']['source_raw_sha256']}`",
        f"- Source samples/PWL pairs: `{value['stage_b']['source_sample_count']}` / `{deck['pwl_pair_count']}`",
        f"- Deck QA: `{deck['status']}`",
        "- Orientation: direct positive JSL7→QBIN to 0→QBIN; no sign change.", "",
        "## Evidence ceiling", "",
        "P values remain raw radians. Phase displays use `rad/(2*pi)` and are `PHASE_NAVIGATION_ONLY`. Raw cumulative phase, voltage area, terminal area and activity tracks are not standalone SFQ counts. The recorded-current replay includes history formed under closed-loop interaction and is not evidence that back-action was irrelevant.", "",
        "Machine record: `analysis/preflight_stage_b.json`.", "",
    ])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh-head", action="store_true")
    args = parser.parse_args()
    if not AUTH_PATH.is_file() or sha256(AUTH_PATH) != AUTH_SHA256:
        raise RuntimeError("Stage B authorization attachment hash changed")
    stage_a_execution = json.loads((EXP / "qa/execution_summary.json").read_text(encoding="utf-8"))
    stage_a_qa = json.loads((EXP / "qa/stage_a_response_qa.json").read_text(encoding="utf-8"))
    if stage_a_execution.get("status") != "PASS" or stage_a_execution.get("solver_solve_invocations") != 1 or stage_a_execution.get("stage_b_started") is not False:
        raise RuntimeError("Stage A is not a PASS one-solve prefix")
    if stage_a_qa.get("status") != "PASS":
        raise RuntimeError("Stage A response QA is not PASS")
    for name in ("raw.csv", "deck.cir", "metadata.json", "run.log"):
        local, origin = REF_DIR / name, SOURCE_DIR / name
        if not local.is_file() or not origin.is_file() or sha256(local) != sha256(origin):
            raise RuntimeError(f"N3 immutable source copy mismatch: {name}")
    _, rows = read_source(REF_DIR / "raw.csv")
    snapshot = EXP / "data/CLOSED_LOOP_N3_I_BJSL8_source.csv"
    write_once(snapshot, "time_s,current_A\n" + "\n".join(f"{row['time_s']},{row['current_A']}" for row in rows) + "\n")
    deck_path = EXP / "runs/CLOSED_CURRENT_REPLAY_N3_0111_RJ2P12/deck.cir"
    write_once(deck_path, replay_deck(snapshot, rows))
    deck = deck_check(deck_path, len(rows))
    auth_path = EXP / "analysis/stage_b_authorization.json"
    if auth_path.is_file():
        auth = json.loads(auth_path.read_text(encoding="utf-8"))
    else:
        auth = {"schema": "bvm-closed-boundary-current-replay-stage-b-authorization-v1", "experiment_id": EXP.name, "created_at_local": now(), "status": "PASS", "attachment_path": str(AUTH_PATH), "attachment_sha256": AUTH_SHA256, "stage_a_scientific_gate": "PASS", "stage_b_authorized": True, "scope": "exactly one N3 closed-boundary current replay; no other solve", "source_case": SOURCE_RUN, "scientific_analysis_performed": True}
        auth_path.write_text(json.dumps(auth, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    base_manifest = json.loads((EXP / "SOURCE_MANIFEST.json").read_text(encoding="utf-8"))
    stage_manifest = {"schema": "bvm-closed-boundary-current-replay-stage-b-source-manifest-v1", "experiment_id": EXP.name, "created_at_local": now(), "base_source_manifest_sha256": sha256(EXP / "SOURCE_MANIFEST.json"), "source_case": SOURCE_RUN, "source_raw_signal": "I(B_JSL8)", "source_artifacts": {name: record(REF_DIR / name, "immutable current RJ2=12 N3 closed-loop source artifact", SOURCE_DIR / name) for name in ("raw.csv", "deck.cir", "metadata.json", "run.log")}, "receiver_sources": base_manifest.get("local_receiver_sources", []), "solver_sha256": SOLVER_SHA256, "authorization_sha256": AUTH_SHA256, "transformations": []}
    stage_manifest_path = EXP / "SOURCE_MANIFEST_STAGE_B.json"
    if stage_manifest_path.is_file():
        stage_manifest = json.loads(stage_manifest_path.read_text(encoding="utf-8"))
    else:
        stage_manifest_path.write_text(json.dumps(stage_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    current = head()
    failures = list(deck["failures"])
    value: dict[str, Any] = {"schema": "bvm-closed-boundary-current-replay-stage-b-preflight-v1", "experiment_id": EXP.name, "created_at_local": now(), "status": "PASS" if not failures else "FAIL", "head_at_preflight": current, "head_refresh": args.refresh_head, "remote_master_at_preflight": remote_head(), "authorization": auth, "stage_a": {"status": "PASS", "physical_solve_count": 1, "scientific_gate": "PASS", "source_unchanged": True}, "stage_b": {"case": "CLOSED_CURRENT_REPLAY_N3_0111_RJ2P12", "source_run": SOURCE_RUN, "source_raw_sha256": sha256(REF_DIR / "raw.csv"), "source_snapshot_sha256": sha256(snapshot), "source_sample_count": len(rows), "deck": deck, "authorized_additional_physical_solve_count": 1, "physical_solve_count_before": 1, "expected_total_physical_solve_count": 2, "no_third_solve": True}, "orientation_status": "PASS: direct positive JSL7->QBIN to 0->QBIN", "transformations": [], "scientific_analysis_performed": True, "failures": failures}
    (EXP / "analysis/preflight_stage_b.json").write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (EXP / "analysis/STAGE_B_PREFLIGHT.md").write_text(stage_b_preflight_markdown(value), encoding="utf-8")
    main_preflight = "\n".join([
        "# Closed-boundary current replay — PREFLIGHT", "", "This experiment is governed by docs/EXPERIMENT_CONTRACT.md.", "",
        f"- Experiment: `{EXP.name}`", f"- Stage A sealed evidence: `1` physical solve; scientific gate: `PASS` (user review attachment hash-bound).", f"- Stage B sealed preflight HEAD: `{current}`", f"- Remote `bvm/master`: `{value.get('remote_master_at_preflight')}`", f"- Status: **{value['status']}**", "- Total authorized solve count: exactly `2`; no third solve.", "",
        "## Stage A", "", "N2 closed-boundary current replay is preserved unchanged in the Stage A package and raw artifacts. The current user has completed direct raw review and explicitly authorized the preregistered Stage B N3 replay.", "",
        "## Stage B", "", "Run exactly `CLOSED_CURRENT_REPLAY_N3_0111_RJ2P12` from the immutable RJ2=12/0111 `I(B_JSL8)` source. The replay contains only the current RJ2=12 QB, six-stage JTL, 10 ohm load and `I_REPLAY 0 QBIN`; no BVM/COMMON_SL/JSL source network. `.tran 0.1p 200p` remains frozen.", "",
        f"- Source raw SHA-256: `{value['stage_b']['source_raw_sha256']}`", f"- PWL pairs: `{deck['pwl_pair_count']}`", f"- Deck QA: `{deck['status']}`", "- No N4/passive/RJ2/timestep/sweep solve is authorized.", "",
        "## Evidence ceiling", "", "Raw is authoritative. Phase is radians; `rad/(2*pi)` turns are navigation only. A closed-loop current replay retains interaction history encoded in the recorded waveform and cannot prove back-action irrelevant. Final scientific outcome remains bounded to the tested replay abstraction.", "", "Machine records: `analysis/preflight_stage_b.json`, `analysis/stage_b_authorization.json`.", "",
    ])
    (EXP / "PREFLIGHT.md").write_text(main_preflight, encoding="utf-8")
    (EXP / "analysis/STAGE_B_AUTHORIZATION.md").write_text("\n".join(["# Stage B authorization", "", "The current user supplied a completed direct raw review and explicitly authorized Stage B N3 only.", "", f"- Attachment SHA-256: `{AUTH_SHA256}`", "- Stage A gate: `PASS`", "- Stage B scope: exactly one `CLOSED_CURRENT_REPLAY_N3_0111_RJ2P12` solve", "- Third solve: forbidden", "- N3 source: immutable current RJ2=12/0111 raw; source case is not rerun.", ""]), encoding="utf-8")
    print(json.dumps({"status": value["status"], "stage_a_gate": "PASS", "stage_b_authorized": True, "source_sample_count": len(rows), "pwl_pair_count": deck["pwl_pair_count"], "physical_solve_count_before": 1, "authorized_additional_physical_solve_count": 1, "scientific_analysis_performed": True}, ensure_ascii=False, indent=2))
    return 0 if value["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
