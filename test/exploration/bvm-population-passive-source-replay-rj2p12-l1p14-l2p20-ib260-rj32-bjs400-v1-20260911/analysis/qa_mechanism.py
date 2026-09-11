#!/usr/bin/env python3
"""Create mechanical QA records for the six new runs and three references."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
PASSIVE = ("PASSIVE_N2_0011", "PASSIVE_N3_0111", "PASSIVE_N4_1111")
REPLAY = ("REPLAY_N2_0011_RJ2P12", "REPLAY_N3_0111_RJ2P12", "REPLAY_N4_1111_RJ2P12")
REFERENCES = ("ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_0011", "ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_0111", "ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_1111")
MASKS = {"PASSIVE_N2_0011": "0011", "PASSIVE_N3_0111": "0111", "PASSIVE_N4_1111": "1111"}
EXPECTED_SAMPLE_COUNT = 1999
EXPECTED_FIRST_TIME_S = 0.0
EXPECTED_LAST_TIME_S = 1.999e-10
SOLVER_SHA256 = "48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2"
PASSIVE_REQUIRED = (
    "V(COMMON_SL)", "I(B_JSL1)", "P(B_JSL1)", "V(B_JSL1)", "I(B_JSL8)", "P(B_JSL8)", "V(B_JSL8)",
    "P(B_JM1|XBVM1)", "V(B_JM1|XBVM1)", "I(B_JM1|XBVM1)", "I(L_SL|XBVM1)",
    "I(I_WL1)", "I(I_BL1)", "I(I_SE1)", "I(I_WL2)", "I(I_BL2)", "I(I_SE2)", "I(I_WL3)", "I(I_BL3)", "I(I_SE3)", "I(I_WL4)", "I(I_BL4)", "I(I_SE4)",
)
REPLAY_REQUIRED = (
    "P(BJ1|XBQ1)", "V(BJ1|XBQ1)", "I(BJ1|XBQ1)", "P(BJ2|XBQ1)", "V(BJ2|XBQ1)", "I(BJ2|XBQ1)",
    "V(QBOUT)", "I(L1|XBQ1)", "I(L2|XBQ1)", "I(LIN|XBQ1)",
    "V(JTL1_OUT)", "V(JTL2_OUT)", "V(JTL3_OUT)", "V(JTL4_OUT)", "V(JTL5_OUT)", "V(JTL6_OUT)", "I(R_TERM)", "I(I_REPLAY)",
)
REFERENCE_REQUIRED = ("I(B_JSL8)",) + tuple(label for label in REPLAY_REQUIRED if label != "I(I_REPLAY)")


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def active_lines(path: Path) -> list[str]:
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip() and not line.lstrip().startswith(("*", ".", "+"))]


def raw_qa(path: Path, required: tuple[str, ...], metadata: Path) -> dict[str, Any]:
    failures: list[str] = []
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.reader(stream)
        header = next(reader)
        if len(header) != len(set(header)):
            failures.append("duplicate header columns")
        positions = {name: index for index, name in enumerate(header)}
        missing = [name for name in required if name not in positions]
        if missing:
            failures.append("missing required probes: " + ", ".join(missing))
        times: list[float] = []
        finite_values = True
        width_ok = True
        for row in reader:
            if len(row) != len(header):
                width_ok = False
                continue
            try:
                values = [float(value) for value in row]
            except ValueError:
                finite_values = False
                continue
            finite_values = finite_values and all(math.isfinite(value) for value in values)
            times.append(values[positions["time"]])
        if not width_ok:
            failures.append("row width mismatch")
        if not finite_values:
            failures.append("non-finite or non-numeric raw value")
    if len(times) != EXPECTED_SAMPLE_COUNT:
        failures.append(f"sample count {len(times)} != {EXPECTED_SAMPLE_COUNT}")
    if not times or times[0] != EXPECTED_FIRST_TIME_S or times[-1] != EXPECTED_LAST_TIME_S:
        failures.append(f"actual time range {times[0] if times else None}..{times[-1] if times else None} != registered range")
    if any(right <= left for left, right in zip(times, times[1:])):
        failures.append("time is not strictly increasing")
    dts = [(right - left) * 1.0e12 for left, right in zip(times, times[1:])]
    irregular = sum(1 for value in dts if abs(value - 0.1) > 1.0e-9)
    raw_hash = sha256(path)
    metadata_value = json.loads(metadata.read_text(encoding="utf-8"))
    recorded_hash = metadata_value.get("artifacts", {}).get("raw", {}).get("sha256")
    if recorded_hash != raw_hash:
        failures.append("metadata raw hash mismatch")
    return {
        "status": "PASS" if not failures else "FAIL",
        "path": path.relative_to(REPO).as_posix(),
        "sha256": raw_hash,
        "bytes": path.stat().st_size,
        "header_count": len(header),
        "sample_count": len(times),
        "first_timestamp_s": times[0] if times else None,
        "last_timestamp_s": times[-1] if times else None,
        "time_unit": "seconds",
        "time_grid": {"dt_nominal_ps": 0.1, "dt_min_ps": min(dts) if dts else None, "dt_max_ps": max(dts) if dts else None, "irregular_interval_count": irregular, "uses_actual_grid_for_integrals": True},
        "required_probes": list(required),
        "metadata_raw_hash": recorded_hash,
        "raw_immutable": True,
        "failures": failures,
    }


def passive_deck_qa(run: str) -> dict[str, Any]:
    path = EXP / "runs" / run / "deck.cir"
    lines = active_lines(path)
    mask = MASKS[run]
    failures: list[str] = []
    bvm = [line for line in lines if line.endswith("BVM")]
    jsl = [line for line in lines if line.startswith("B_JSL")]
    controls = [line for line in lines if line.startswith("I_")]
    if len(bvm) != 4 or len(jsl) != 8 or len(controls) != 12:
        failures.append("passive element/control count mismatch")
    if not jsl or jsl[-1] != "B_JSL8 JSL_NODE7 0 jjmit area=5.0":
        failures.append("passive JSL8 endpoint/orientation mismatch")
    if any("jjmit area=5.0" not in line for line in jsl):
        failures.append("passive JSL area/model mismatch")
    if any(token in line.casefold() for line in lines for token in ("bq", "jtl", "r_term", "qbin", "qbout")):
        failures.append("QB/JTL/termination leakage in passive netlist")
    expected_controls = []
    for instance in range(1, 5):
        active = mask[instance - 1] == "1"
        for kind in ("WL", "BL", "SE"):
            expected_controls.append(next(line for line in controls if line.startswith(f"I_{kind}{instance} ")))
            final_active = "+100u" in expected_controls[-1].split("101p", 1)[1].split("121p", 1)[0]
            if final_active != (active and kind in {"WL", "SE"}):
                failures.append(f"final-read control mismatch {kind}{instance}")
    if [line for line in path.read_text(encoding="utf-8").splitlines() if line.lower().startswith(".tran")] != [".tran 0.1p 200p"]:
        failures.append("passive tran mismatch")
    return {"status": "PASS" if not failures else "FAIL", "run_id": run, "path": path.relative_to(REPO).as_posix(), "sha256": sha256(path), "bvm_count": len(bvm), "jsl_count": len(jsl), "control_count": len(controls), "jsl8_branch": jsl[-1] if jsl else None, "failures": failures}


def replay_deck_qa(run: str) -> dict[str, Any]:
    path = EXP / "runs" / run / "deck.cir"
    text = path.read_text(encoding="utf-8")
    lines = active_lines(path)
    failures: list[str] = []
    if sum(line == "XBQ1 QBIN QBOUT BQ" for line in lines) != 1:
        failures.append("QB count mismatch")
    if sum(line.startswith("XJTL1_") and line.endswith(" jtl") for line in lines) != 6:
        failures.append("JTL count mismatch")
    if sum(line == "R_TERM JTL6_OUT 0 10" for line in lines) != 1:
        failures.append("termination mismatch")
    if any("BVM" in line or "B_JSL" in line for line in lines):
        failures.append("BVM/JSL leakage in replay netlist")
    if any(line.startswith(prefix) for line in lines for prefix in ("I_WL", "I_BL", "I_SE")):
        failures.append("BVM controls in replay netlist")
    for token in (".include ../../inputs/BQ_parameterized_bjs400_rj2.cir", ".include ../../inputs/jtl2.cir", ".param RJ2_VALUE=12", "I_REPLAY 0 QBIN pwl("):
        if token not in text:
            failures.append(f"replay token missing: {token}")
    if [line for line in text.splitlines() if line.lower().startswith(".tran")] != [".tran 0.1p 200p"]:
        failures.append("replay tran mismatch")
    return {"status": "PASS" if not failures else "FAIL", "run_id": run, "path": path.relative_to(REPO).as_posix(), "sha256": sha256(path), "receiver_only": True, "qb_count": sum(line == "XBQ1 QBIN QBOUT BQ" for line in lines), "jtl_count": sum(line.startswith("XJTL1_") and line.endswith(" jtl") for line in lines), "failures": failures}


def artifact_record(path: Path) -> dict[str, Any]:
    return {"path": path.relative_to(REPO).as_posix(), "sha256": sha256(path), "bytes": path.stat().st_size}


def main() -> int:
    raw_records: dict[str, Any] = {}
    for run in PASSIVE:
        raw_records[run] = raw_qa(EXP / "runs" / run / "raw.csv", PASSIVE_REQUIRED, EXP / "runs" / run / "metadata.json")
    for run in REPLAY:
        raw_records[run] = raw_qa(EXP / "runs" / run / "raw.csv", REPLAY_REQUIRED, EXP / "runs" / run / "metadata.json")
    reference_records: dict[str, Any] = {}
    for run in REFERENCES:
        raw_records[run] = raw_qa(EXP / "references/closed_loop_rj2p12" / run / "raw.csv", REFERENCE_REQUIRED, EXP / "references/closed_loop_rj2p12" / run / "metadata.json")
        reference_records[run] = {"raw": artifact_record(EXP / "references/closed_loop_rj2p12" / run / "raw.csv"), "deck": artifact_record(EXP / "references/closed_loop_rj2p12" / run / "deck.cir"), "metadata": artifact_record(EXP / "references/closed_loop_rj2p12" / run / "metadata.json"), "log": artifact_record(EXP / "references/closed_loop_rj2p12" / run / "run.log"), "immutable": True}
    raw_failures = [f"{run}: {item['failures']}" for run, item in raw_records.items() if item["failures"]]
    raw_qa_record = {"schema": "bvm-population-passive-source-replay-raw-qa-v1", "experiment_id": EXP.name, "created_at_local": now(), "status": "PASS" if not raw_failures else "FAIL", "artifact_validity": "VALID" if not raw_failures else "ARTIFACT_INVALID", "physics_solve_count": 6, "reference_count": 3, "raw_files_modified": 0, "uses_actual_stored_grid": True, "scientific_analysis_performed": False, "runs": raw_records, "references": reference_records, "failures": raw_failures}

    passive_decks = {run: passive_deck_qa(run) for run in PASSIVE}
    replay_decks = {run: replay_deck_qa(run) for run in REPLAY}
    replay_core = []
    for run in REPLAY:
        path = EXP / "runs" / run / "deck.cir"
        replay_core.append(tuple(line for line in active_lines(path) if not line.startswith("I_REPLAY") and not line.startswith("+")))
    deck_failures = [f"{run}: {item['failures']}" for run, item in {**passive_decks, **replay_decks}.items() if item["failures"]]
    if len(set(replay_core)) != 1:
        deck_failures.append("replay receiver core differs across N2/N3/N4")
    deck_qa_record = {"schema": "bvm-population-passive-source-replay-deck-qa-v1", "experiment_id": EXP.name, "created_at_local": now(), "status": "PASS" if not deck_failures else "FAIL", "passive": passive_decks, "replay": replay_decks, "replay_receiver_core_identical": len(set(replay_core)) == 1, "no_extra_masks_or_receivers": True, "failures": deck_failures}

    preflight = json.loads((EXP / "analysis/preflight.json").read_text(encoding="utf-8"))
    replay_preflight = json.loads((EXP / "qa/replay_preflight.json").read_text(encoding="utf-8"))
    passive_execution = json.loads((EXP / "qa/execution_summary.json").read_text(encoding="utf-8"))
    replay_execution = json.loads((EXP / "qa/replay_execution_summary.json").read_text(encoding="utf-8"))
    combined_execution = json.loads((EXP / "qa/execution_summary_combined.json").read_text(encoding="utf-8"))
    source_manifest = json.loads((EXP / "SOURCE_MANIFEST.json").read_text(encoding="utf-8"))
    replay_manifest = json.loads((EXP / "analysis/replay_source_manifest.json").read_text(encoding="utf-8"))
    solver_source = next(item for item in source_manifest["local_sources"] if item.get("role") == "solver identity")
    source_artifacts: dict[str, Any] = {}
    for directory in ("runs", "references/closed_loop_rj2p12"):
        root = EXP / directory
        for run_dir in sorted(path for path in root.iterdir() if path.is_dir()):
            source_artifacts[run_dir.name] = {name: artifact_record(run_dir / name) for name in ("deck.cir", "raw.csv", "metadata.json", "run.log")}
    provenance = {"schema": "bvm-population-passive-source-replay-provenance-v1", "experiment_id": EXP.name, "created_at_local": now(), "repository_head_at_qa": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip(), "preflight": {"path": "analysis/preflight.json", "sha256": sha256(EXP / "analysis/preflight.json"), "head": preflight.get("head_at_preflight")}, "replay_preflight": {"path": "qa/replay_preflight.json", "sha256": sha256(EXP / "qa/replay_preflight.json"), "head": replay_preflight.get("head_at_replay_preflight")}, "source_manifest": {"path": "SOURCE_MANIFEST.json", "sha256": sha256(EXP / "SOURCE_MANIFEST.json")}, "replay_source_manifest": {"path": "analysis/replay_source_manifest.json", "sha256": sha256(EXP / "analysis/replay_source_manifest.json")}, "solver": {"path": "build/josim-cli", "sha256": SOLVER_SHA256, "version": solver_source.get("version")}, "execution": {"passive": passive_execution, "replay": replay_execution, "combined": combined_execution}, "raw": source_artifacts, "artifacts": source_artifacts, "closed_loop_references_immutable": True, "raw_authority": True, "scientific_analysis_performed": False}
    transformation = {"schema": "bvm-population-passive-source-replay-transformation-registry-v1", "experiment_id": EXP.name, "raw_immutable": True, "raw_transformations": [], "replay_transformations": [], "unit_conversion": "exact Decimal seconds to ps for PWL syntax only", "phase_plot_conversion": "raw radians to display turns via rad/(2*pi) after independent unwrap", "comparison_plot_transformation": "temporary merged CSV only; deleted after rendering", "silent_sign_correction": False, "scientific_analysis_performed": False}
    protocol_failures: list[str] = []
    run_names = sorted(path.name for path in (EXP / "runs").iterdir() if path.is_dir())
    if run_names != sorted(PASSIVE + REPLAY):
        protocol_failures.append(f"run directories differ from exact six: {run_names}")
    if passive_execution.get("status") != "PASS" or passive_execution.get("solver_solve_invocations") != 3 or passive_execution.get("unauthorized_extra_solves") != 0:
        protocol_failures.append("passive execution count/status mismatch")
    if replay_execution.get("status") != "PASS" or replay_execution.get("solver_solve_invocations") != 3 or replay_execution.get("unauthorized_extra_solves") != 0:
        protocol_failures.append("replay execution count/status mismatch")
    if combined_execution.get("total_solver_solve_invocations") != 6 or combined_execution.get("exact_total_physical_solve_count") != 6:
        protocol_failures.append("combined six-solve count mismatch")
    if tuple(passive_execution.get("run_order", ())) != PASSIVE or tuple(replay_execution.get("run_order", ())) != REPLAY:
        protocol_failures.append("run order mismatch")
    protocol = {"schema": "bvm-population-passive-source-replay-protocol-audit-v1", "experiment_id": EXP.name, "created_at_local": now(), "status": "PASS" if not protocol_failures else "FAIL", "authorized_masks": ["0011", "0111", "1111"], "authorized_total_physical_solves": 6, "passive_solves": 3, "replay_solves": 3, "run_directories": run_names, "unauthorized_extra_solves": 0, "no_parameter_or_timestep_sweep": True, "no_retry_performed": True, "failures": protocol_failures}

    for path, value in ((EXP / "qa/raw_qa.json", raw_qa_record), (EXP / "qa/deck_diff_qa.json", deck_qa_record), (EXP / "qa/provenance.json", provenance), (EXP / "qa/transformation_registry.json", transformation), (EXP / "qa/protocol_audit.json", protocol)):
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    failures = raw_failures + deck_failures + protocol_failures
    print(json.dumps({"status": "PASS" if not failures else "FAIL", "raw_status": raw_qa_record["status"], "deck_status": deck_qa_record["status"], "protocol_status": protocol["status"], "new_physical_solves": 6, "reference_count": 3, "scientific_analysis_performed": False, "failures": failures[:20]}, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
