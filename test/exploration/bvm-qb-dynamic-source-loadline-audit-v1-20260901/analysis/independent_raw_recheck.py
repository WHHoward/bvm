#!/usr/bin/env python3
"""Independent raw-only recheck for the dynamic source-loadline audit.

This intentionally does not import ``run_analysis.py``.  It re-reads a small,
high-value subset of the registered raw CSVs and recomputes source difference,
back-action, scalar-fit, and QB KCL numbers through separate helpers.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import subprocess
from pathlib import Path
from typing import Any

import numpy as np


REPO = Path(__file__).resolve().parents[4]
TARGET = REPO / "test/exploration/bvm-qb-dynamic-source-loadline-audit-v1-20260901"
MATRIX = REPO / "test/exploration/bvm-load-qb-matrix-v1-20260901"
OUT = TARGET / "analysis/independent-raw-recheck.json"
PARENT_HEAD = "b761ba948d0cf64affdc0b9fb623fab05197cf21"
PRE = (80.0, 94.0)
ACTIVE = (94.0, 130.0)
ABS_TOL_A = 1.0e-12
REL_TOL = 1.0e-6
TWO_PI = 2.0 * math.pi


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def relative(path: Path) -> str:
    return path.relative_to(REPO).as_posix()


def raw_path(fixture: str, width: int, load: str) -> Path:
    return MATRIX / "raw" / fixture / f"{width}ps" / load / "logical1_read" / "run-01.csv"


def read_csv(path: Path) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        header = next(reader)
        rows = list(reader)
    matrix = np.asarray([[float(value) for value in row] for row in rows], dtype=float)
    if matrix.ndim != 2 or matrix.shape[1] != len(header):
        raise ValueError(f"invalid shape for {path}")
    if header[0] != "time" or not np.all(np.diff(matrix[:, 0]) > 0.0):
        raise ValueError(f"invalid time axis for {path}")
    columns: dict[str, list[np.ndarray]] = {}
    for index, name in enumerate(header[1:], start=1):
        columns.setdefault(name, []).append(matrix[:, index])
    # The selected BVM source files contain two ``I(B_LD1)`` columns.  The
    # primary audit's occurrence-0 convention is the terminal branch current;
    # keep that convention explicit here rather than silently choosing by name.
    return matrix[:, 0], {name: values[0] for name, values in columns.items()}


def mask(time_s: np.ndarray, bounds: tuple[float, float]) -> np.ndarray:
    return (time_s >= bounds[0] * 1e-12) & (time_s < bounds[1] * 1e-12)


def integrate(time_s: np.ndarray, values: np.ndarray) -> float:
    return float(np.trapezoid(values, time_s) if hasattr(np, "trapezoid") else np.trapz(values, time_s))


def scalar_fit(time_s: np.ndarray, grounded: np.ndarray, physical: np.ndarray, baseline_corrected: bool) -> dict[str, Any]:
    active = mask(time_s, ACTIVE)
    pre = mask(time_s, PRE)
    g = grounded[active].copy()
    p = physical[active].copy()
    if baseline_corrected:
        g -= float(np.median(grounded[pre]))
        p -= float(np.median(physical[pre]))
    k = float(np.dot(g, p) / np.dot(g, g))
    residual = p - k * g
    norm = float(np.linalg.norm(residual) / np.linalg.norm(p))
    correlation = float(np.corrcoef(g, p)[0, 1])
    return {
        "k": k,
        "normalized_residual": norm,
        "correlation": correlation,
        "max_abs_residual_A": float(np.max(np.abs(residual))),
        "max_abs_residual_time_ps": float(time_s[active][np.argmax(np.abs(residual))] * 1e12),
        "grounded_signed_area_uA_ps": integrate(time_s[active], g) * 1e18,
        "physical_signed_area_uA_ps": integrate(time_s[active], p) * 1e18,
    }


def kcl(time_s: np.ndarray, columns: dict[str, np.ndarray]) -> dict[str, Any]:
    currents = {name: columns[name] for name in (
        "I(LIN|XBQ)", "I(BJS|XBQ)", "I(BJL1|XBQ)", "I(RJ1|XBQ)", "I(L1|XBQ)",
        "I(RB|XBQ)", "I(L2|XBQ)", "I(L0|XBQ)", "I(BJL2|XBQ)", "I(RJ2|XBQ)",
    )}
    equations = {
        "node1": (currents["I(LIN|XBQ)"] - currents["I(BJS|XBQ)"], ["I(LIN|XBQ)", "I(BJS|XBQ)"]),
        "node2": (currents["I(BJS|XBQ)"] - currents["I(BJL1|XBQ)"] - currents["I(RJ1|XBQ)"] - currents["I(L1|XBQ)"], ["I(BJS|XBQ)", "I(BJL1|XBQ)", "I(RJ1|XBQ)", "I(L1|XBQ)"]),
        "node3": (currents["I(L1|XBQ)"] + currents["I(RB|XBQ)"] - currents["I(L2|XBQ)"], ["I(L1|XBQ)", "I(RB|XBQ)", "I(L2|XBQ)"]),
        "node4": (currents["I(L2|XBQ)"] - currents["I(L0|XBQ)"] - currents["I(BJL2|XBQ)"] - currents["I(RJ2|XBQ)"], ["I(L2|XBQ)", "I(L0|XBQ)", "I(BJL2|XBQ)", "I(RJ2|XBQ)"]),
    }
    active = mask(time_s, ACTIVE)
    output: dict[str, Any] = {}
    for node, (residual, terms) in equations.items():
        scale = float(np.max(np.sum(np.vstack([np.abs(currents[name][active]) for name in terms]), axis=0)))
        bound = max(ABS_TOL_A, REL_TOL * scale)
        maximum = float(np.max(np.abs(residual[active])))
        output[node] = {"max_abs_A": maximum, "bound_A": bound, "ratio": maximum / bound, "passed": bool(maximum <= bound)}
    output["overall_passed"] = all(item["passed"] for item in output.values() if isinstance(item, dict))
    return output


def source_metrics(time_s: np.ndarray, values: np.ndarray) -> dict[str, float]:
    active = mask(time_s, ACTIVE)
    local_t = time_s[active]
    local = values[active]
    positive = np.maximum(local, 0.0)
    negative = np.minimum(local, 0.0)
    return {
        "positive_peak_A": float(np.max(local)),
        "positive_peak_time_ps": float(local_t[np.argmax(local)] * 1e12),
        "signed_area_uA_ps": integrate(local_t, local) * 1e18,
        "positive_area_uA_ps": integrate(local_t, positive) * 1e18,
        "negative_area_uA_ps": integrate(local_t, negative) * 1e18,
    }


def main() -> None:
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, check=True, capture_output=True, text=True).stdout.strip()
    if head != PARENT_HEAD:
        raise RuntimeError(f"HEAD changed after preregistration: expected {PARENT_HEAD}, got {head}")

    selected = {
        "A_source_9ps_12x320": raw_path("source", 9, "12x320"),
        "B_source_13ps_12x320": raw_path("source", 13, "12x320"),
        "B_replay_13ps_12x320": raw_path("replay", 13, "12x320"),
        "C_physical_13ps_12x320": raw_path("physical", 13, "12x320"),
        "D_replay_13ps_8x500": raw_path("replay", 13, "8x500"),
    }
    loaded = {name: read_csv(path) for name, path in selected.items()}
    time_a, source_a = loaded["A_source_9ps_12x320"]
    time_b, source_b = loaded["B_source_13ps_12x320"]
    time_replay, replay = loaded["B_replay_13ps_12x320"]
    time_c, physical = loaded["C_physical_13ps_12x320"]
    time_d, replay8 = loaded["D_replay_13ps_8x500"]
    for other in (time_b, time_replay, time_c, time_d):
        if not np.array_equal(time_a, other):
            raise ValueError("selected raw files do not share an exact time grid")

    difference = source_b["I(B_LD1)"] - source_a["I(B_LD1)"]
    windows = {
        "94_105ps": (94.0, 105.0),
        "105_106ps": (105.0, 106.0),
        "106_109ps": (106.0, 109.0),
        "109_110ps": (109.0, 110.0),
        "110_130ps": (110.0, 130.0),
    }
    decomposition: dict[str, Any] = {}
    for name, bounds in windows.items():
        selected_mask = mask(time_a, bounds)
        local_time = time_a[selected_mask]
        local_delta = difference[selected_mask]
        decomposition[name] = {
            "absolute_area_uA_ps": integrate(local_time, np.abs(local_delta)) * 1e18,
            "signed_area_uA_ps": integrate(local_time, local_delta) * 1e18,
            "max_abs_A": float(np.max(np.abs(local_delta))),
        }
    absolute_total = sum(item["absolute_area_uA_ps"] for item in decomposition.values())
    extension = sum(decomposition[name]["absolute_area_uA_ps"] for name in ("105_106ps", "106_109ps", "109_110ps"))
    source_record = {
        "A": source_metrics(time_a, source_a["I(B_LD1)"]),
        "B": source_metrics(time_b, source_b["I(B_LD1)"]),
        "difference_decomposition": decomposition,
        "extension_105_110_share": extension / absolute_total if absolute_total else None,
        "outside_105_110_share": (absolute_total - extension) / absolute_total if absolute_total else None,
    }

    delta_i = source_b["I(B_LD1)"] - physical["I(B_LD1)"]
    active = mask(time_b, ACTIVE)
    backaction = {
        "max_abs_A": float(np.max(np.abs(delta_i[active]))),
        "rms_A": float(np.sqrt(np.mean(delta_i[active] ** 2))),
        "signed_area_uA_ps": integrate(time_b[active], delta_i[active]) * 1e18,
        "max_abs_time_ps": float(time_b[active][np.argmax(np.abs(delta_i[active]))] * 1e12),
    }

    scalar_record = {
        "raw_origin": scalar_fit(time_b, source_b["I(B_LD1)"], physical["I(B_LD1)"], False),
        "baseline_corrected": scalar_fit(time_b, source_b["I(B_LD1)"], physical["I(B_LD1)"], True),
    }
    kcl_record = {
        "B_replay_13ps_12x320": kcl(time_replay, replay),
        "C_physical_13ps_12x320": kcl(time_c, physical),
    }

    primary_path = TARGET / "analysis/audit-details.json"
    primary = json.loads(primary_path.read_text(encoding="utf-8")) if primary_path.exists() else {}
    comparisons = {
        "source_A_peak": [source_record["A"]["positive_peak_A"], primary.get("source_results", {}).get("12x320", {}).get("signals", {}).get("I(B_LD1)", {}).get("a", {}).get("positive_peak")],
        "source_B_signed_area": [source_record["B"]["signed_area_uA_ps"], primary.get("source_results", {}).get("12x320", {}).get("signals", {}).get("I(B_LD1)", {}).get("b", {}).get("signed_integral_uA_ps")],
        "delta_i_max": [backaction["max_abs_A"], primary.get("backaction", {}).get("delta_i", {}).get("max_abs")],
        "scalar_raw_residual": [scalar_record["raw_origin"]["normalized_residual"], primary.get("scalar", {}).get("fits", {}).get("raw_origin", {}).get("normalized_residual")],
    }
    matches: dict[str, bool] = {}
    for name, (direct, reported) in comparisons.items():
        matches[name] = reported is not None and math.isclose(float(direct), float(reported), rel_tol=1e-10, abs_tol=1e-15)

    payload = {
        "document_type": "independent_raw_recheck",
        "status": "PASS" if all(matches.values()) else "INCONCLUSIVE",
        "parent_head": PARENT_HEAD,
        "method": "raw-only direct CSV parser; no import of primary analysis helpers",
        "selected_raw": {name: {"path": relative(path), "sha256": sha256(path)} for name, path in selected.items()},
        "recomputed": {
            "source": source_record,
            "backaction": backaction,
            "scalar": scalar_record,
            "kcl": kcl_record,
        },
        "comparison_to_primary": {name: {"direct": direct, "primary": reported, "match": matches[name]} for name, (direct, reported) in comparisons.items()},
        "matches_primary_key_values": matches,
        "limitations": [
            "This is a mechanical consistency check, not an independent scientific authority.",
            "It rechecks selected raw metrics and does not replace the frozen strict BJL2 evidence.",
        ],
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(payload["status"])
    print(json.dumps(matches, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
