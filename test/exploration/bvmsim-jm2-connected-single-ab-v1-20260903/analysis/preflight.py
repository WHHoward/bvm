#!/usr/bin/env python3
"""Post-run artifact, protocol, probe, and topology QA for JM2-connected runs."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from collections import OrderedDict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "scripts"))
from bvmtools.compare import exact_time_grid_identity  # noqa: E402
from bvmtools.deckqa import deck_qa  # noqa: E402
from bvmtools.raw import RawTrace, read_csv  # noqa: E402
from bvmtools.stimulus import compare_stimuli, validate_bvm_write_read_protocol  # noqa: E402


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
VARIANT = EXP / "variants/bvm_jm2_connected.cir"
HISTORICAL = REPO / "BVMSim/bvm_cell.cir"
RUNS = OrderedDict(
    (
        ("S0-R-JM2C", ("direct_10ohm", 0, False)),
        ("S1-R-JM2C", ("direct_10ohm", 1, False)),
        ("S0-J-JM2C", ("six_stage_jtl_plus_10ohm", 0, True)),
        ("S1-J-JM2C", ("six_stage_jtl_plus_10ohm", 1, True)),
    )
)
WINDOWS = {
    "write_plateau": (51.0e-12, 60.0e-12),
    "read_plateau": (71.0e-12, 80.0e-12),
}
STIMULUS = ("I(I_WL1)", "I(I_BL1)", "I(I_SE1)")
BVM_INTERNAL = tuple(
    f"{kind}(B_{junction}|XBVM1)"
    for junction in ("JM1", "JM2", "JS1", "JS2")
    for kind in ("P", "V", "I")
)
STORAGE = ("I(L_M1|XBVM1)", "I(L_M2|XBVM1)", "I(L_M3|XBVM1)", "I(L_PM|XBVM1)")
BVM_BOUNDARY = ("V(SL1)", "I(L_PSL|XBVM1)", "I(L_SL|XBVM1)")
TERMINAL = (
    "P(B_LD4_01)", "V(B_LD4_01)", "I(B_LD4_01)",
    "P(B_LD4_11)", "V(B_LD4_11)", "I(B_LD4_11)",
    "P(BVMOUT)", "V(BVMOUT)", "I(BVMOUT)",
)
QB = (
    "V(QBIN)", "V(QBOUT)", "I(LIN|XBQ1)",
    "P(BJS|XBQ1)", "V(BJS|XBQ1)", "I(BJS|XBQ1)",
    "P(BJ1|XBQ1)", "V(BJ1|XBQ1)", "I(BJ1|XBQ1)", "I(RJ1|XBQ1)",
    "P(BJ2|XBQ1)", "V(BJ2|XBQ1)", "I(BJ2|XBQ1)", "I(RJ2|XBQ1)",
    "I(L1|XBQ1)", "I(L2|XBQ1)", "I(L3|XBQ1)", "I(IB|XBQ1)",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO.resolve()).as_posix()


def sig(trace: RawTrace, label: str) -> tuple[float, ...]:
    return trace.column(label)  # type: ignore[return-value]


def all_required(is_jtl: bool) -> list[str]:
    result = list(STIMULUS) + list(BVM_INTERNAL) + list(STORAGE) + list(BVM_BOUNDARY) + list(TERMINAL) + list(QB)
    if is_jtl:
        for stage in range(1, 7):
            result.extend(
                (
                    f"P(B01|XJTL1_{stage})", f"V(B01|XJTL1_{stage})",
                    f"P(B02|XJTL1_{stage})", f"V(B02|XJTL1_{stage})",
                )
            )
    return result


def variant_diff() -> dict[str, object]:
    left = HISTORICAL.read_text(encoding="utf-8").splitlines()
    right = VARIANT.read_text(encoding="utf-8").splitlines()
    changes = [
        {"line": i + 1, "historical": a, "connected": b}
        for i, (a, b) in enumerate(zip(left, right))
        if a != b
    ]
    expected = {
        "line": 37,
        "historical": "L_M2    2       4       24.5P",
        "connected": "L_M2    2       3       24.5P",
    }
    return {
        "status": "PASS" if len(left) == len(right) and changes == [expected] else "FAIL",
        "difference_count": len(changes),
        "differences": changes,
        "historical_sha256": sha256(HISTORICAL),
        "connected_sha256": sha256(VARIANT),
    }


def protocol(trace: RawTrace, state: int) -> dict[str, object]:
    write = -100.0e-6 if state == 0 else 100.0e-6
    return validate_bvm_write_read_protocol(
        trace,
        trace.time,
        write_window_s=WINDOWS["write_plateau"],
        read_window_s=WINDOWS["read_plateau"],
        expected_write={
            "I(I_WL1)": write,
            "I(I_BL1)": write,
            "I(I_SE1)": 0.0,
        },
        expected_read={
            "I(I_WL1)": 100.0e-6,
            "I(I_BL1)": 0.0,
            "I(I_SE1)": 100.0e-6,
        },
        tolerance=1.0e-10,
        unit="A",
    )


def run_qa(condition: str, load: str, state: int, is_jtl: bool) -> tuple[dict[str, object], RawTrace]:
    run_dir = EXP / "runs" / condition
    raw = run_dir / "raw/run-01.csv"
    deck = run_dir / "deck.cir"
    log = run_dir / "logs/run-01.log"
    trace = read_csv(raw)
    required = all_required(is_jtl)
    deck_result = deck_qa(
        deck,
        log_text=log.read_text(encoding="utf-8"),
        expected_includes=(
            "../../../../circuits/models/jjmit.cir",
            "../variants/bvm_jm2_connected.cir",
            "../../../../BVMSim/BQ.cir",
            *( ("../../../../BVMSim/library_josim/jtl2.cir",) if is_jtl else () ),
        ),
        expected_bvm_instances=1,
        expected_terminal_sensing_jj_count=12,
        expected_jtl_stages=6 if is_jtl else 0,
        expected_termination_ohm=10.0,
        expected_tran_timestep_ps=0.1,
        required_probes=required,
        raw_headers=trace.headers,
    )
    text = deck.read_text(encoding="utf-8")
    topology_only = {
        "variant_include_active": "../variants/bvm_jm2_connected.cir" in text,
        "historical_bvm_include_absent": "../../../../BVMSim/bvm_cell.cir" not in text,
        "canonical_bvm_absent": "circuits/bvm/bvm_cell.cir" not in text,
        "jm2_connected_source_line_present": "L_M2    2       3       24.5P" in VARIANT.read_text(encoding="utf-8"),
    }
    protocol_result = protocol(trace, state)
    artifact_ok = (
        deck_result["status"] == "ARTIFACT_VALID"
        and protocol_result["status"] == "PROTOCOL_VALID"
        and all(topology_only.values())
        and not trace.duplicate_columns
    )
    record = {
        "condition": condition,
        "load": load,
        "logical_state": state,
        "raw": {
            "path": rel(raw),
            "sha256": sha256(raw),
            "qa": trace.qa(),
        },
        "deck": {
            "path": rel(deck),
            "sha256": sha256(deck),
            "qa": deck_result,
            "topology_only": topology_only,
        },
        "log": {
            "path": rel(log),
            "sha256": sha256(log),
            "solver_exit_code": 0,
            "model_warning_absent": not bool(re.search(r"Missing model:|Using default model", log.read_text(encoding="utf-8"), re.I)),
        },
        "stimulus_protocol": protocol_result,
        "artifact_status": "ARTIFACT_VALID" if artifact_ok else "ARTIFACT_INVALID",
    }
    return record, trace


def main() -> int:
    records: OrderedDict[str, dict[str, object]] = OrderedDict()
    traces: OrderedDict[str, RawTrace] = OrderedDict()
    for condition, (load, state, is_jtl) in RUNS.items():
        record, trace = run_qa(condition, load, state, is_jtl)
        records[condition] = record
        traces[condition] = trace

    s0 = traces["S0-R-JM2C"]
    s1 = traces["S1-R-JM2C"]
    read_stimulus_match = compare_stimuli(
        s0.time,
        {label: sig(s0, label) for label in STIMULUS},
        s1.time,
        {label: sig(s1, label) for label in STIMULUS},
        WINDOWS["read_plateau"],
        unit="A",
    )
    all_artifact_valid = all(item["artifact_status"] == "ARTIFACT_VALID" for item in records.values())
    report = {
        "schema": "jm2-connected-post-run-preflight-v1",
        "experiment": "bvmsim-jm2-connected-single-ab-v1-20260903",
        "variant_diff": variant_diff(),
        "runs": records,
        "shared_s0_s1_read_stimulus": {
            "time_grid_exact": exact_time_grid_identity(s0.time, s1.time),
            "comparison": read_stimulus_match,
            "status": "PASS" if read_stimulus_match["status"] == "VALID" and read_stimulus_match["time_grid_exact"] else "FAIL",
        },
        "all_artifact_valid": all_artifact_valid,
        "status": "ARTIFACT_VALID" if all_artifact_valid else "ARTIFACT_INVALID",
    }
    out = EXP / "analysis/post_run_preflight.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "runs": len(records), "read_protocol": report["shared_s0_s1_read_stimulus"]["status"]}, ensure_ascii=False))
    return 0 if all_artifact_valid and report["shared_s0_s1_read_stimulus"]["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
