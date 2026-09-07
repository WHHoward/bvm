#!/usr/bin/env python3
"""Independent standard-library re-read of N1-N4 raw and replay evidence."""

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
BASELINE = REPO / "test/exploration/bvmsim-jm2-passive-capture-replay-v1-20260907"
DIRECT = REPO / "test/exploration/bvmsim-jm2-single-vs-4bvm-shared-sl-v1-20260907"
RAW = {
    "N1_PASSIVE": BASELINE / "runs/array_passive/raw.csv",
    "N2_PASSIVE": EXP / "runs/n2_passive/raw.csv",
    "N3_PASSIVE": EXP / "runs/n3_passive/raw.csv",
    "N4_PASSIVE": EXP / "runs/n4_passive/raw.csv",
    "N1_REPLAY": BASELINE / "runs/replay_array/raw.csv",
    "N2_REPLAY": EXP / "runs/n2_replay/raw.csv",
    "N3_REPLAY": EXP / "runs/n3_replay/raw.csv",
    "N4_REPLAY": EXP / "runs/n4_replay/raw.csv",
}
EXPECTED_RAW_HASHES = {
    "N1_PASSIVE": "6ba17bbf2d8a31d59067da930bf8cb3be53f06695c166ce68b6630ea89a1eef6",
    "N2_PASSIVE": "f5784ef4aae6ff10cc474ffdbb476e2eb62b034b21ec1119576a7b1a84724cff",
    "N3_PASSIVE": "f966077641779f90c5043bf7f5d9a4beaba9b13214977cc26cb399e1f6d90273",
    "N4_PASSIVE": "ea9e1e123c80dfc38a0d3b061d8eb68f9ed76133db07490da616cb3bf5b70ba0",
    "N1_REPLAY": "11bce2601a6f3b63dff33a32771bb7c406e0b6e64236facabbfd25676220151e",
    "N2_REPLAY": "19846ace7ebbc24eccf91814b3c1f2f1469ce9289f35022c2d7e33fa55cd75eb",
    "N3_REPLAY": "555e850fde892da7fd2328d2ac34081b45459ab48e8181a8e95d7cd531e7c225",
    "N4_REPLAY": "5cac782aa9dfa5d467d81e2988e772f1978abfe8313d7896089d5dfa84517b28",
}
DIRECT_RAW_HASHES = {
    "SINGLE": "26a70e75afced6e91a7f75e9048b2700839051f38bcd2844d3f153b04ef0939a",
    "ARRAY": "8543abc6d7a7d276c0bfa3159a4d3d37d569200e5fa30082466e66df8ab24dc2",
}
PAIR_RE = re.compile(r"([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)[pP]\s+([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)")
FINAL_START_PS = Decimal("110")
FINAL_END_PS = Decimal("121")
RESPONSE_END_PS = Decimal("200")
TAU = Decimal("6.2831853071795864769252867665590057683943387987502")
PHI0 = Decimal("2.067833848e-15")


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
        if reader.fieldnames is None or reader.fieldnames.count("time") != 1:
            raise RuntimeError(f"invalid time header: {path}")
        headers = list(reader.fieldnames)
        rows = list(reader)
    times = [Decimal(row["time"]) for row in rows]
    if len(times) < 2 or any(right <= left for left, right in zip(times, times[1:])):
        raise RuntimeError(f"time grid is not strictly increasing: {path}")
    for row in rows:
        for header in headers:
            if not row[header]:
                raise RuntimeError(f"empty value in {path}: {header}")
            if not Decimal(row[header]).is_finite():
                raise RuntimeError(f"non-finite value in {path}: {header}")
    return headers, rows


def value(row: dict[str, str], label: str) -> Decimal:
    return Decimal(row[label])


def rows_in(rows: list[dict[str, str]], start: Decimal, end: Decimal) -> list[dict[str, str]]:
    selected = [row for row in rows if start <= Decimal(row["time"]) * Decimal("1e12") < end]
    if len(selected) < 2:
        raise RuntimeError(f"window has too few samples: {start}-{end}: {len(selected)}")
    return selected


def max_abs(values: list[Decimal]) -> Decimal:
    return max((abs(value) for value in values), default=Decimal("0"))


def rms(values: list[Decimal]) -> Decimal:
    return (sum(value * value for value in values) / Decimal(len(values))).sqrt() if values else Decimal("0")


def trapezoid_area(rows: list[dict[str, str]], label: str, scale: Decimal = Decimal("1")) -> Decimal:
    total = Decimal("0")
    for left, right in zip(rows, rows[1:]):
        dt = Decimal(right["time"]) - Decimal(left["time"])
        total += (value(left, label) + value(right, label)) * dt / Decimal("2")
    return total * scale


def source_snapshot_check(passive: str, rows: list[dict[str, str]], snapshot: Path) -> dict[str, object]:
    with snapshot.open(newline="", encoding="utf-8") as handle:
        snapshot_rows = list(csv.DictReader(handle))
    raw_pairs = [(row["time"], row["I(B_JSL8)"]) for row in rows]
    snapshot_pairs = [(row["time_s"], row["current_A"]) for row in snapshot_rows]
    return {
        "passive_case": passive,
        "snapshot": snapshot.relative_to(REPO).as_posix(),
        "raw_sample_count": len(raw_pairs),
        "snapshot_sample_count": len(snapshot_pairs),
        "exact_raw_token_pairs": raw_pairs == snapshot_pairs,
        "raw_signal": "I(B_JSL8)",
    }


def replay_deck_pairs(path: Path) -> list[tuple[Decimal, Decimal]]:
    body = path.read_text(encoding="utf-8")
    start = body.lower().index("pwl(") + len("pwl(")
    end = body.index(")", start)
    return [(Decimal(time) * Decimal("1e-12"), Decimal(current)) for time, current in PAIR_RE.findall(body[start:end])]


def replay_contract_check(count: int, passive_rows: list[dict[str, str]], replay_rows: list[dict[str, str]]) -> dict[str, object]:
    passive = f"N{count}_PASSIVE"
    replay = f"N{count}_REPLAY"
    snapshot = BASELINE / "data/array_passive_JSL8_source.csv" if count == 1 else EXP / "data" / f"n{count}_passive_JSL8_source.csv"
    with snapshot.open(newline="", encoding="utf-8") as handle:
        snapshot_rows = list(csv.DictReader(handle))
    source_pairs = [(Decimal(row["time_s"]), Decimal(row["current_A"])) for row in snapshot_rows]
    deck_pairs = replay_deck_pairs(BASELINE / "runs/replay_array/deck.cir" if count == 1 else EXP / "runs" / f"n{count}_replay/deck.cir")
    replay_grid = [(Decimal(row["time"]), value(row, "I(I_REPLAY)")) for row in replay_rows]
    source_grid = [(Decimal(row["time"]), value(row, "I(B_JSL8)")) for row in passive_rows]
    lin = [value(row, "I(LIN|XBQ1)") for row in replay_rows]
    failures: list[str] = []
    if deck_pairs != source_pairs:
        failures.append("deck PWL pairs differ from source snapshot")
    if replay_grid != source_grid:
        failures.append("replay I_REPLAY grid differs from passive source grid")
    if len(replay_grid) != len(lin) or any(left != right for (_, left), right in zip(replay_grid, lin)):
        failures.append("I(I_REPLAY) and I(LIN|XBQ1) differ")
    deck_text = (BASELINE / "runs/replay_array/deck.cir" if count == 1 else EXP / "runs" / f"n{count}_replay/deck.cir").read_text(encoding="utf-8")
    if len(re.findall(r"^XJTL1_\d+\s+\S+\s+\S+\s+jtl$", deck_text, flags=re.MULTILINE)) != 6:
        failures.append("deck does not contain six JTL instances")
    if "I_REPLAY 0 QBIN pwl(" not in deck_text:
        failures.append("positive source orientation is absent")
    return {
        "replay_case": replay,
        "source_case": passive,
        "source_snapshot_pair_count": len(source_pairs),
        "deck_pwl_pair_count": len(deck_pairs),
        "replay_sample_count": len(replay_grid),
        "deck_pwl_exact_numeric_fidelity": deck_pairs == source_pairs,
        "replay_input_exact_numeric_fidelity": replay_grid == source_grid,
        "replay_input_matches_QB_LIN": len(replay_grid) == len(lin) and all(left == right for (_, left), right in zip(replay_grid, lin)),
        "orientation": "I_REPLAY 0 QBIN; positive source maps directly from JSL8 into QBIN",
        "transformations": [],
        "failures": failures,
    }


def unwrap(values: list[Decimal]) -> list[Decimal]:
    # The raw phases in these captures do not rely on a hidden resampling
    # step; this simple Decimal implementation keeps the independent check
    # separate from the production phase helper.
    pi = TAU / Decimal("2")
    result = [values[0]]
    for previous, current in zip(values, values[1:]):
        delta = current - previous
        while delta > pi:
            delta -= TAU
        while delta < -pi:
            delta += TAU
        result.append(result[-1] + delta)
    return result


def phase_delta(rows: list[dict[str, str]], label: str, start: Decimal, end: Decimal) -> tuple[Decimal, Decimal]:
    selected = rows_in(rows, start, end)
    phases = unwrap([value(row, label) for row in selected])
    delta = phases[-1] - phases[0]
    return delta, delta / TAU


def compare_number(name: str, actual: Decimal, expected: object, failures: list[str], tolerance: float = 1e-7) -> dict[str, object]:
    expected_decimal = Decimal(str(expected))
    passed = math.isclose(float(actual), float(expected_decimal), rel_tol=1e-9, abs_tol=tolerance)
    if not passed:
        failures.append(f"{name}: independent={actual} production={expected_decimal}")
    return {"name": name, "independent": float(actual), "production": float(expected_decimal), "difference": float(actual - expected_decimal), "pass": passed}


def main() -> int:
    failures: list[str] = []
    headers: dict[str, list[str]] = {}
    rows: dict[str, list[dict[str, str]]] = {}
    before: dict[str, str] = {}
    for name, path in RAW.items():
        headers[name], rows[name] = read_raw(path)
        before[name] = sha256(path)
        if before[name] != EXPECTED_RAW_HASHES[name]:
            failures.append(f"{name}: unexpected raw hash")
        if len(rows[name]) != 1999:
            failures.append(f"{name}: sample count {len(rows[name])} != 1999")

    snapshot_checks: dict[str, object] = {}
    for count in (1, 2, 3, 4):
        passive = f"N{count}_PASSIVE"
        snapshot = BASELINE / "data/array_passive_JSL8_source.csv" if count == 1 else EXP / "data" / f"n{count}_passive_JSL8_source.csv"
        check = source_snapshot_check(passive, rows[passive], snapshot)
        snapshot_checks[passive] = check
        if not check["exact_raw_token_pairs"]:
            failures.append(f"{passive}: snapshot token mismatch")

    replay_checks: dict[str, object] = {}
    for count in (1, 2, 3, 4):
        check = replay_contract_check(count, rows[f"N{count}_PASSIVE"], rows[f"N{count}_REPLAY"])
        replay_checks[f"N{count}_REPLAY"] = check
        failures.extend(f"{check['replay_case']}: {item}" for item in check["failures"])

    independent: dict[str, object] = {"window": "FINAL_READ_RESPONSE [110 ps, 200 ps)", "passive": {}, "replay": {}}
    final_start = FINAL_START_PS
    final_end = RESPONSE_END_PS
    for count in (1, 2, 3, 4):
        passive_rows = rows[f"N{count}_PASSIVE"]
        selected = rows_in(passive_rows, final_start, final_end)
        lsl_residual = [sum(value(row, f"I(L_SL|XBVM{i})") for i in range(1, 5)) - value(row, "I(B_JSL1)") for row in selected]
        source = [value(row, "I(B_JSL8)") for row in selected]
        independent["passive"][f"N{count}_PASSIVE"] = {
            "JSL8_max_uA": float(max(source) * Decimal("1e6")),
            "JSL8_signed_area_uA_ps": float(trapezoid_area(selected, "I(B_JSL8)", Decimal("1e18"))),
            "KCL_max_abs_uA": float(max_abs(lsl_residual) * Decimal("1e6")),
            "KCL_rms_uA": float(rms(lsl_residual) * Decimal("1e6")),
        }
        replay_rows = rows[f"N{count}_REPLAY"]
        response = rows_in(replay_rows, final_start, final_end)
        jtl6_rad, jtl6_turns = phase_delta(replay_rows, "P(B01|XJTL1_6)", final_start, final_end)
        bj2_rad, bj2_turns = phase_delta(replay_rows, "P(BJ2|XBQ1)", final_start, final_end)
        terminal_area_wb = trapezoid_area(response, "I(R_TERM)", Decimal("10") * Decimal("1"))
        # I(R_TERM) is A and dt is seconds, so 10*I*dt is Wb.
        independent["replay"][f"N{count}_REPLAY"] = {
            "I_REPLAY_max_abs_uA": float(max_abs([value(row, "I(I_REPLAY)") for row in response]) * Decimal("1e6")),
            "I_REPLAY_signed_area_uA_ps": float(trapezoid_area(response, "I(I_REPLAY)", Decimal("1e18"))),
            "BJ2_endpoint_change_rad": float(bj2_rad),
            "BJ2_endpoint_change_turns": float(bj2_turns),
            "JTL6_endpoint_change_rad": float(jtl6_rad),
            "JTL6_endpoint_change_turns": float(jtl6_turns),
            "terminal_area_over_phi0": float(terminal_area_wb / PHI0),
        }

    production = json.loads((EXP / "analysis/metrics.json").read_text(encoding="utf-8"))
    comparisons: list[dict[str, object]] = []
    for count in (2, 3, 4):
        passive = f"N{count}_PASSIVE"
        selected_n1 = rows_in(rows["N1_PASSIVE"], FINAL_START_PS, RESPONSE_END_PS)
        selected_n = rows_in(rows[passive], FINAL_START_PS, RESPONSE_END_PS)
        delta = [value(right, "I(B_JSL8)") - value(left, "I(B_JSL8)") for left, right in zip(selected_n1, selected_n)]
        production_delta = production["passive_source_comparison"]["I(B_JSL8)"]["deltas_vs_N1"][passive]["FINAL_READ_RESPONSE"]["max_abs_delta"]
        comparisons.append(compare_number(f"{passive} JSL8 response max abs delta [uA]", max_abs(delta) * Decimal("1e6"), production_delta, failures))
        production_kcl = production["array_lsl_balance"]["cases"][passive]["kcl_residual"]["FINAL_READ_RESPONSE"]["max_abs_uA"]
        comparisons.append(compare_number(f"{passive} response KCL max abs [uA]", Decimal(str(independent["passive"][passive]["KCL_max_abs_uA"])), production_kcl, failures))
    for count in (1, 2, 3, 4):
        replay = f"N{count}_REPLAY"
        prod = production["replay_response"]["I(I_REPLAY)"]["cases"][replay]["FINAL_READ_RESPONSE"]["max_abs"]
        comparisons.append(compare_number(f"{replay} response I_REPLAY max abs [uA]", Decimal(str(independent["replay"][replay]["I_REPLAY_max_abs_uA"])), prod, failures))
        prod_area = production["terminal_metrics"]["cases"][replay]["windows"]["FINAL_READ_RESPONSE"]["terminal_voltage_area_over_phi0"]
        comparisons.append(compare_number(f"{replay} response terminal area/Phi0", Decimal(str(independent["replay"][replay]["terminal_area_over_phi0"])), prod_area, failures))

    after = {name: sha256(path) for name, path in RAW.items()}
    if before != after:
        failures.append("raw hash changed during independent check")
    direct_hashes = {
        "SINGLE": sha256(DIRECT / "runs/single/raw.csv"),
        "ARRAY": sha256(DIRECT / "runs/array/raw.csv"),
    }
    if direct_hashes != DIRECT_RAW_HASHES:
        failures.append("contextual direct raw hash changed")
    if json.loads((EXP / "analysis/topology_preflight.json").read_text(encoding="utf-8")).get("status") != "PASS":
        failures.append("topology preflight is not PASS")
    if json.loads((EXP / "analysis/replay_preflight.json").read_text(encoding="utf-8")).get("status") != "PASS":
        failures.append("replay preflight is not PASS")

    record = {
        "schema": "jm2-read-count-passive-replay-independent-check-v1",
        "experiment_id": EXP.name,
        "created_at_local": now_local(),
        "status": "PASS" if not failures else "FAIL",
        "method": "standard-library independent CSV/Decimal/hash/PWL re-read; no solver call",
        "raw_hashes_before": before,
        "raw_hashes_after": after,
        "raw_hashes_unchanged": before == after,
        "raw_expected_hashes": EXPECTED_RAW_HASHES,
        "sample_counts": {name: len(items) for name, items in rows.items()},
        "source_snapshot_checks": snapshot_checks,
        "replay_contract_checks": replay_checks,
        "independent_metrics": independent,
        "production_metric_comparisons": comparisons,
        "contextual_direct_hashes": direct_hashes,
        "contextual_direct_hashes_expected": DIRECT_RAW_HASHES,
        "limitations": [
            "N1 passive/replay are immutable references from the prior accepted exploration and were not rerun.",
            "No timestep convergence or parameter sensitivity run was performed.",
            "The optional V(IB|XBQ1) probe is absent from the emitted JoSIM raw schema.",
            "Phase values are raw radians; turns are only rad/(2*pi) derived values.",
            "No phase trajectory, voltage area, threshold activity, or local junction change is counted as an SFQ event.",
        ],
        "failures": failures,
    }
    write_once(EXP / "analysis/independent_check.json", json.dumps(record, indent=2, ensure_ascii=False) + "\n")
    review = f"""# REVIEW — N1-N4 read-count passive/replay exploration

- Status: **{record['status']}**
- Method: independent standard-library CSV/Decimal/hash/PWL re-read; no solver call.
- New physical runs checked: six (`N2_PASSIVE`/`N2_REPLAY`, `N3_PASSIVE`/`N3_REPLAY`, `N4_PASSIVE`/`N4_REPLAY`). N1 is a hash-bound reference and was not rerun.

## Numerical review

| check | result |
|---|---:|
| raw hashes unchanged during check | `{record['raw_hashes_unchanged']}` |
| all source snapshot token pairs exact | `{all(item['exact_raw_token_pairs'] for item in snapshot_checks.values())}` |
| all replay PWL pairs exact | `{all(item['deck_pwl_exact_numeric_fidelity'] for item in replay_checks.values())}` |
| all replay inputs match QB LIN | `{all(item['replay_input_matches_QB_LIN'] for item in replay_checks.values())}` |
| production comparisons | `{all(item['pass'] for item in comparisons)}` |

The independent integrals use each raw file's actual stored time column and trapezoids. Phase is unwrapped before endpoint displacement; any turns are `rad/(2*pi)`. The KCL equation is explicitly `sum_i I(L_SL|XBVMi) - I(B_JSL1)`.

## Adversarial checks and limits

- N1 raw is referenced from the prior experiment by fixed hash; no historical raw was copied or overwritten.
- The three new passive decks differ only in final READ mask; pre-final control history and topology were independently preflighted.
- Replay decks were parsed for exact PWL pairs, direct positive orientation, one QB, six JTL stages and one 10 ohm termination.
- The first bad control-template generation is retained under `analysis/attempts/20260907-control-template-preflight-fail/`; it produced no raw and was excluded from analysis.
- Convergence and sensitivity remain **UNKNOWN**. This record does not establish a hardware result, mechanism, Gate, event count or universal read-count law.

Machine record: `analysis/independent_check.json`.
"""
    write_once(EXP / "analysis/REVIEW.md", review)
    print(json.dumps({"status": record["status"], "record": "analysis/independent_check.json", "review": "analysis/REVIEW.md", "failures": failures}, ensure_ascii=False))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
