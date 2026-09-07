#!/usr/bin/env python3
"""Independent raw-file and replay-contract check.

This checker intentionally uses only the standard library.  It does not
import ``analysis/analyze.py`` or any of its derived JSON.  Its purpose is to
re-read the four raw files, validate immutable hashes and source fidelity,
recompute a small set of numerical checks, and record adversarial limitations.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import re
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
RAW = {
    "SINGLE_PASSIVE": EXP / "runs/single_passive/raw.csv",
    "ARRAY_PASSIVE": EXP / "runs/array_passive/raw.csv",
    "REPLAY_SINGLE": EXP / "runs/replay_single/raw.csv",
    "REPLAY_ARRAY": EXP / "runs/replay_array/raw.csv",
}
EXPECTED_RAW_HASHES = {
    "SINGLE_PASSIVE": "2553796d8c4c0e4edc5784ad184bf2ceb93a2ebd2cdd948c458891d59cfc4672",
    "ARRAY_PASSIVE": "6ba17bbf2d8a31d59067da930bf8cb3be53f06695c166ce68b6630ea89a1eef6",
    "REPLAY_SINGLE": "edeb1c692bf3fa1da43cc50df5eb516615a7a7df729afe5d099243c01cb17bfa",
    "REPLAY_ARRAY": "11bce2601a6f3b63dff33a32771bb7c406e0b6e64236facabbfd25676220151e",
}
DIRECT_RAW_HASHES = {
    "SINGLE": "26a70e75afced6e91a7f75e9048b2700839051f38bcd2844d3f153b04ef0939a",
    "ARRAY": "8543abc6d7a7d276c0bfa3159a4d3d37d569200e5fa30082466e66df8ab24dc2",
}
PAIR_RE = re.compile(
    r"([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)[pP]\s+"
    r"([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)"
)
TAU = Decimal("6.2831853071795864769252867665590057683943387987502")
FINAL_START_PS = Decimal("110")
FINAL_END_PS = Decimal("121")


def now_local() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def write_once(path: Path, content: str) -> None:
    if path.exists():
        if path.read_text(encoding="utf-8") == content:
            return
        raise RuntimeError(f"refusing to overwrite existing artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def read_raw(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise RuntimeError(f"missing header: {path}")
        headers = list(reader.fieldnames)
        rows = list(reader)
    if headers.count("time") != 1:
        raise RuntimeError(f"time column is not unique: {path}")
    times = [Decimal(row["time"]) for row in rows]
    if len(times) < 2 or any(right <= left for left, right in zip(times, times[1:])):
        raise RuntimeError(f"time grid is not strictly increasing: {path}")
    return headers, rows


def value(row: dict[str, str], label: str) -> Decimal:
    return Decimal(row[label])


def final_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    selected = []
    for row in rows:
        time_ps = Decimal(row["time"]) * Decimal("1e12")
        if FINAL_START_PS <= time_ps < FINAL_END_PS:
            selected.append(row)
    if len(selected) < 2:
        raise RuntimeError(f"final-read window has too few samples: {len(selected)}")
    return selected


def max_abs(values: list[Decimal]) -> Decimal:
    return max((abs(item) for item in values), default=Decimal("0"))


def rms(values: list[Decimal]) -> Decimal:
    if not values:
        return Decimal("0")
    return (sum(item * item for item in values) / Decimal(len(values))).sqrt()


def trapezoid_area(rows: list[dict[str, str]], label: str) -> Decimal:
    total = Decimal("0")
    for left, right in zip(rows, rows[1:]):
        dt = Decimal(right["time"]) - Decimal(left["time"])
        total += (value(left, label) + value(right, label)) * dt / Decimal("2")
    # A*s -> uA*ps.
    return total * Decimal("1e18")


def source_snapshot_check(
    passive_name: str, raw_rows: list[dict[str, str]], snapshot_path: Path
) -> dict[str, object]:
    with snapshot_path.open(newline="", encoding="utf-8") as handle:
        snapshot_rows = list(csv.DictReader(handle))
    raw_pairs = [(row["time"], row["I(B_JSL8)"]) for row in raw_rows]
    snapshot_pairs = [(row["time_s"], row["current_A"]) for row in snapshot_rows]
    return {
        "passive_case": passive_name,
        "snapshot": snapshot_path.relative_to(REPO).as_posix(),
        "raw_sample_count": len(raw_pairs),
        "snapshot_sample_count": len(snapshot_pairs),
        "exact_raw_token_pairs": raw_pairs == snapshot_pairs,
        "raw_signal": "I(B_JSL8)",
    }


def replay_deck_pairs(path: Path) -> list[tuple[Decimal, Decimal]]:
    body = path.read_text(encoding="utf-8")
    start = body.index("pwl(") + len("pwl(")
    end = body.index(")", start)
    return [
        (Decimal(time) * Decimal("1e-12"), Decimal(current))
        for time, current in PAIR_RE.findall(body[start:end])
    ]


def replay_contract_check(
    replay_name: str,
    passive_name: str,
    passive_rows: list[dict[str, str]],
    replay_rows: list[dict[str, str]],
) -> dict[str, object]:
    snapshot_path = EXP / "data" / f"{passive_name.lower()}_JSL8_source.csv"
    with snapshot_path.open(newline="", encoding="utf-8") as handle:
        snapshot_rows = list(csv.DictReader(handle))
    source_pairs = [
        (Decimal(row["time_s"]), Decimal(row["current_A"])) for row in snapshot_rows
    ]
    deck_pairs = replay_deck_pairs(EXP / "runs" / replay_name.lower() / "deck.cir")
    replay_grid = [(Decimal(row["time"]), value(row, "I(I_REPLAY)")) for row in replay_rows]
    lin_grid = [value(row, "I(LIN|XBQ1)") for row in replay_rows]
    source_grid = [(Decimal(row["time"]), value(row, "I(B_JSL8)")) for row in passive_rows]
    failures: list[str] = []
    if deck_pairs != source_pairs:
        failures.append("deck PWL pairs differ from source snapshot")
    if replay_grid != source_grid:
        failures.append("replay I_REPLAY grid differs from passive source grid")
    if any(left != right for (_, left), right in zip(replay_grid, lin_grid)):
        failures.append("I(I_REPLAY) and I(LIN|XBQ1) differ")
    if len(replay_grid) != len(lin_grid):
        failures.append("replay source and LIN lengths differ")
    deck_text = (EXP / "runs" / replay_name.lower() / "deck.cir").read_text(encoding="utf-8")
    jtl_instances = re.findall(r"^XJTL1_\d+\s+\S+\s+\S+\s+jtl$", deck_text, flags=re.MULTILINE)
    if len(jtl_instances) != 6:
        failures.append("deck does not contain six JTL instances")
    if "I_REPLAY 0 QBIN pwl(" not in deck_text:
        failures.append("registered positive source orientation is absent")
    return {
        "replay_case": replay_name,
        "source_case": passive_name,
        "source_snapshot_pair_count": len(source_pairs),
        "deck_pwl_pair_count": len(deck_pairs),
        "replay_sample_count": len(replay_grid),
        "deck_pwl_exact_numeric_fidelity": deck_pairs == source_pairs,
        "replay_input_exact_numeric_fidelity": replay_grid == source_grid,
        "replay_input_matches_QB_LIN": len(replay_grid) == len(lin_grid)
        and all(left == right for (_, left), right in zip(replay_grid, lin_grid)),
        "orientation": "I_REPLAY 0 QBIN; positive source maps directly from JSL8 into QBIN",
        "transformations": [],
        "failures": failures,
    }


def compare_number(
    name: str, actual: Decimal, expected: object, failures: list[str], tolerance: float = 1e-7
) -> dict[str, object]:
    expected_decimal = Decimal(str(expected))
    difference = actual - expected_decimal
    passed = math.isclose(float(actual), float(expected_decimal), rel_tol=1e-9, abs_tol=tolerance)
    if not passed:
        failures.append(f"{name}: independent={actual} production={expected_decimal}")
    return {
        "name": name,
        "independent": float(actual),
        "production": float(expected_decimal),
        "difference": float(difference),
        "pass": passed,
    }


def main() -> int:
    failures: list[str] = []
    headers: dict[str, list[str]] = {}
    rows: dict[str, list[dict[str, str]]] = {}
    hash_before: dict[str, str] = {}
    for name, path in RAW.items():
        headers[name], rows[name] = read_raw(path)
        hash_before[name] = sha256(path)
        if hash_before[name] != EXPECTED_RAW_HASHES[name]:
            failures.append(f"{name}: raw hash changed or unexpected")
        if len(rows[name]) != 1999:
            failures.append(f"{name}: sample count {len(rows[name])} != 1999")

    source_checks = {
        "SINGLE_PASSIVE": source_snapshot_check(
            "SINGLE_PASSIVE", rows["SINGLE_PASSIVE"], EXP / "data/single_passive_JSL8_source.csv"
        ),
        "ARRAY_PASSIVE": source_snapshot_check(
            "ARRAY_PASSIVE", rows["ARRAY_PASSIVE"], EXP / "data/array_passive_JSL8_source.csv"
        ),
    }
    for record in source_checks.values():
        if not record["exact_raw_token_pairs"]:
            failures.append(f"{record['passive_case']}: source snapshot token mismatch")

    replay_checks = {
        "REPLAY_SINGLE": replay_contract_check(
            "REPLAY_SINGLE", "SINGLE_PASSIVE", rows["SINGLE_PASSIVE"], rows["REPLAY_SINGLE"]
        ),
        "REPLAY_ARRAY": replay_contract_check(
            "REPLAY_ARRAY", "ARRAY_PASSIVE", rows["ARRAY_PASSIVE"], rows["REPLAY_ARRAY"]
        ),
    }
    for record in replay_checks.values():
        failures.extend(f"{record['replay_case']}: {item}" for item in record["failures"])

    array_rows = final_rows(rows["ARRAY_PASSIVE"])
    kcl_residual = [
        sum(value(row, f"I(L_SL|XBVM{i})") for i in range(1, 5)) - value(row, "I(B_JSL1)")
        for row in array_rows
    ]
    passive_delta = {
        label: [
            value(array_row, label) - value(single_row, label)
            for single_row, array_row in zip(final_rows(rows["SINGLE_PASSIVE"]), array_rows)
        ]
        for label in ("I(B_JSL1)", "I(B_JSL8)")
    }
    independent_metrics: dict[str, object] = {
        "window": "FINAL_READ [110 ps, 121 ps)",
        "array_kcl_residual_max_abs_uA": float(max_abs(kcl_residual) * Decimal("1e6")),
        "array_kcl_residual_rms_uA": float(rms(kcl_residual) * Decimal("1e6")),
        "passive_delta_max_abs_uA": {
            label: float(max_abs(values) * Decimal("1e6")) for label, values in passive_delta.items()
        },
        "replay": {},
    }
    for case in ("REPLAY_SINGLE", "REPLAY_ARRAY"):
        selected = final_rows(rows[case])
        qbin = [value(row, "V(QBIN)") for row in selected]
        replay_current = [value(row, "I(I_REPLAY)") for row in selected]
        bj1 = [value(row, "P(BJ1|XBQ1)") for row in selected]
        jtl1 = [value(row, "P(B01|XJTL1_1)") for row in selected]
        jtl6 = [value(row, "P(B01|XJTL1_6)") for row in selected]
        term = [value(row, "I(R_TERM)") for row in selected]
        independent_metrics["replay"][case] = {
            "I_REPLAY_max_abs_uA": float(max_abs(replay_current) * Decimal("1e6")),
            "I_REPLAY_signed_area_uA_ps": float(trapezoid_area(selected, "I(I_REPLAY)")),
            "V_QBIN_max_abs_mV": float(max_abs(qbin) * Decimal("1e3")),
            "BJ1_endpoint_change_rad": float(bj1[-1] - bj1[0]),
            "BJ1_endpoint_change_turns": float((bj1[-1] - bj1[0]) / TAU),
            "JTL1_B01_endpoint_change_rad": float(jtl1[-1] - jtl1[0]),
            "JTL6_B01_endpoint_change_rad": float(jtl6[-1] - jtl6[0]),
            "R_TERM_max_abs_uA": float(max_abs(term) * Decimal("1e6")),
        }

    # Compare independent values with only the production summary fields that
    # do not require importing the production analyzer.
    metrics_path = EXP / "analysis/metrics.json"
    production = json.loads(metrics_path.read_text(encoding="utf-8"))
    comparisons = []
    comparisons.append(
        compare_number(
            "JSL1 final-read max abs delta [uA]",
            max_abs(passive_delta["I(B_JSL1)"]) * Decimal("1e6"),
            production["passive_source_comparison"]["JSL1_I"]["windows"]["FINAL_READ"]["max_abs_delta"],
            failures,
        )
    )
    comparisons.append(
        compare_number(
            "JSL8 final-read max abs delta [uA]",
            max_abs(passive_delta["I(B_JSL8)"]) * Decimal("1e6"),
            production["passive_source_comparison"]["JSL8_I"]["windows"]["FINAL_READ"]["max_abs_delta"],
            failures,
        )
    )
    comparisons.append(
        compare_number(
            "array KCL final-read max abs residual [uA]",
            max_abs(kcl_residual) * Decimal("1e6"),
            production["array_current_balance"]["kcl_residual"]["FINAL_READ"]["max_abs_uA"],
            failures,
        )
    )
    for case in ("REPLAY_SINGLE", "REPLAY_ARRAY"):
        prod = production["case_key_signal_summaries"][case]["key_signals"]
        independent = independent_metrics["replay"][case]
        comparisons.append(
            compare_number(
                f"{case} final-read I_REPLAY max abs [uA]",
                Decimal(str(independent["I_REPLAY_max_abs_uA"])),
                prod["I(I_REPLAY)"]["FINAL_READ"]["max_abs"],
                failures,
            )
        )
        comparisons.append(
            compare_number(
                f"{case} final-read V(QBIN) max abs [mV]",
                Decimal(str(independent["V_QBIN_max_abs_mV"])),
                prod["V(QBIN)"]["FINAL_READ"]["max_abs"],
                failures,
            )
        )

    hash_after = {name: sha256(path) for name, path in RAW.items()}
    if hash_before != hash_after:
        failures.append("raw hash changed while performing independent check")
    direct_hashes = {
        "SINGLE": sha256(DIRECT_RAW := REPO / "test/exploration/bvmsim-jm2-single-vs-4bvm-shared-sl-v1-20260907/runs/single/raw.csv"),
        "ARRAY": sha256(REPO / "test/exploration/bvmsim-jm2-single-vs-4bvm-shared-sl-v1-20260907/runs/array/raw.csv"),
    }
    if direct_hashes != DIRECT_RAW_HASHES:
        failures.append("contextual direct raw hash changed")

    replay_preflight = json.loads((EXP / "analysis/replay_preflight.json").read_text(encoding="utf-8"))
    if replay_preflight.get("status") != "PASS":
        failures.append("registered replay preflight is not PASS")

    record = {
        "schema": "jm2-passive-capture-replay-independent-check-v1",
        "experiment_id": EXP.name,
        "created_at_local": now_local(),
        "status": "PASS" if not failures else "FAIL",
        "method": "standard-library independent CSV/hash/PWL re-read; no solver call",
        "raw_hashes_before": hash_before,
        "raw_hashes_after": hash_after,
        "raw_hashes_unchanged": hash_before == hash_after,
        "raw_expected_hashes": EXPECTED_RAW_HASHES,
        "sample_counts": {name: len(items) for name, items in rows.items()},
        "source_snapshot_checks": source_checks,
        "replay_contract_checks": replay_checks,
        "independent_metrics": independent_metrics,
        "production_metric_comparisons": comparisons,
        "contextual_direct_hashes": direct_hashes,
        "contextual_direct_hashes_expected": DIRECT_RAW_HASHES,
        "replay_preflight_status": replay_preflight.get("status"),
        "limitations": [
            "No timestep convergence or parameter sensitivity run was performed.",
            "The optional V(IB|XBQ1) probe is absent from the emitted JoSIM raw schema.",
            "Phase values are raw radians; turns are only rad/(2*pi) derived values.",
            "No phase trajectory, derivative activity, voltage area, or local junction change is counted as an SFQ event.",
            "Direct historical raw is contextual only and was not rerun.",
        ],
        "failures": failures,
    }
    output_path = EXP / "analysis/independent_check.json"
    write_once(output_path, json.dumps(record, indent=2, ensure_ascii=False) + "\n")

    review = f"""# REVIEW — passive capture / replay exploration

- Status: **{record['status']}**
- Independent method: standard-library CSV, SHA-256, exact Decimal source/PWL comparison, and actual-grid trapezoid/KCL checks. No solver call was made.
- Physical runs checked: exactly four new runs (`SINGLE_PASSIVE`, `ARRAY_PASSIVE`, `REPLAY_SINGLE`, `REPLAY_ARRAY`).

## Numerical review

| check | result |
|---|---:|
| raw hashes unchanged during check | `{record['raw_hashes_unchanged']}` |
| passive source snapshot token fidelity | `{all(item['exact_raw_token_pairs'] for item in source_checks.values())}` |
| replay PWL exact numeric fidelity | `{all(item['deck_pwl_exact_numeric_fidelity'] for item in replay_checks.values())}` |
| replay input matches QB LIN branch | `{all(item['replay_input_matches_QB_LIN'] for item in replay_checks.values())}` |
| ARRAY final-read KCL max residual | `{independent_metrics['array_kcl_residual_max_abs_uA']:.9g} uA` |
| SINGLE replay final-read I_REPLAY max abs | `{independent_metrics['replay']['REPLAY_SINGLE']['I_REPLAY_max_abs_uA']:.9g} uA` |
| ARRAY replay final-read I_REPLAY max abs | `{independent_metrics['replay']['REPLAY_ARRAY']['I_REPLAY_max_abs_uA']:.9g} uA` |

All phase quantities remain descriptive raw-radian trajectories; any turns shown in the machine record use `rad/(2*pi)`. The replay current signed areas use the actual recorded time grid.

## Adversarial checks and limits

- Raw hashes are pinned to the four captured files and were re-read before and after this check.
- Historical direct raw hashes were checked and are unchanged; those files are contextual and were not rerun.
- The replay deck was independently parsed for its exact PWL pairs, positive `I_REPLAY 0 QBIN` orientation, and six JTL instances.
- The first derived analysis pass with the wrong KCL sign is preserved under `analysis/attempts/ANALYSIS-01/` and is excluded from this review.
- `V(IB|XBQ1)` is an optional missing output column in this JoSIM raw schema.
- Convergence and sensitivity remain **UNKNOWN**; this exploration does not establish hardware behavior, an exactly-one event, an SFQ count, or a mechanism claim.

Machine record: `analysis/independent_check.json`.
"""
    write_once(EXP / "analysis/REVIEW.md", review)
    print(json.dumps({"status": record["status"], "record": "analysis/independent_check.json", "review": "analysis/REVIEW.md", "failures": failures}, ensure_ascii=False))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
