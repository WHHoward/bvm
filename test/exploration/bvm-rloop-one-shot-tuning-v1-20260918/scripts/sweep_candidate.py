#!/usr/bin/env python3
"""Generic multi-mask, one-dimensional sweep orchestration."""

from __future__ import annotations

import csv
import html
import json
import math
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import analyze as engine
import try_candidate as platform

SERIES = platform.SERIES
REPO = platform.REPO
SWEEP_ALLOWED = platform.CIRCUIT_KEYS | platform.STIMULUS_KEYS


def run_id(mode: str, mask: str) -> str:
    return f"{mode.upper()}_N{mask.count('1')}_{mask}"


def sweep_numeric(token: str) -> float:
    return platform.parse_number(str(token), "SWEEP_VALUE")


def norm_line(line: str) -> str:
    return " ".join(line.strip().lower().split())


def netlist_body(text: str) -> list[str]:
    return [norm_line(line) for line in text.splitlines() if line.strip() and not line.lstrip().startswith("*")]


def stimulus_body(text: str) -> list[str]:
    return [norm_line(line) for line in text.splitlines() if line.strip() and not line.lstrip().startswith("*")]


def equal_value(left: str, right: str) -> bool:
    if left.upper() == right.upper() == "OPEN":
        return True
    try:
        lv = platform.parse_number(left, "compare")
        rv = platform.parse_number(right, "compare")
        return abs(lv - rv) <= 1e-18 * max(1.0, abs(rv))
    except RuntimeError:
        return left.strip().lower() == right.strip().lower()


def raw_qa_for(case_root: Path, rid: str) -> dict[str, Any] | None:
    for path in (case_root / "qa" / "raw_qa.json", SERIES / "qa" / "raw_qa.json"):
        if not path.is_file():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        for row in data.get("rows", []):
            if row.get("run_id") == rid and row.get("case_id") in {None, case_root.name}:
                return row
    return None


def source_role_hash(source_manifest: dict[str, Any], role: str) -> str | None:
    for item in source_manifest.get("sources", []):
        if item.get("role") == role:
            return item.get("sha256")
    return None


def verify_existing(case_root: Path, params: dict[str, Any], value: str) -> dict[str, Any]:
    """Verify a complete point across every requested mask."""
    result = {"case_id": case_root.name, "value": value, "status": "REUSE_REJECTED", "source_type": "EXISTING_REJECTED", "reasons": [], "runs": {}}
    manifest_path = case_root / "case_manifest.json"
    source_path = case_root / "source_manifest.json"
    if not manifest_path.is_file() or not source_path.is_file():
        result["reasons"].append("missing case_manifest.json or source_manifest.json")
        return result
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        source_manifest = json.loads(source_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        result["reasons"].append(f"manifest parse failure: {exc}")
        return result
    case_params = manifest.get("parameters", {})
    if str(case_params.get("MODE", "")).lower() != params["MODE"]:
        result["reasons"].append("MODE mismatch")
    requested_masks = list(params["MASKS"])
    requested_runs = [run_id(params["MODE"], mask) for mask in requested_masks]
    missing = [rid for rid in requested_runs if rid not in manifest.get("run_order", [])]
    if missing:
        result["reasons"].append("requested masks missing: " + ", ".join(missing))
    if params["MODE"] == "closed":
        qb_keys = platform.QB_AREA_KEYS + platform.QB_RESISTANCE_KEYS + platform.QB_INDUCTANCE_KEYS + platform.QB_CURRENT_KEYS
        for key in qb_keys:
            if key not in case_params:
                result["reasons"].append(f"QB parameter fingerprint missing: {key}")
            elif not equal_value(str(case_params[key]), str(params[key])):
                result["reasons"].append(f"QB parameter mismatch: {key}")
        if not source_manifest.get("qb_rendered_snapshot"):
            result["reasons"].append("QB rendered snapshot/fingerprint missing")
    canonical = source_manifest.get("canonical_bvm_source") or source_manifest.get("canonical_bvm_reference")
    if not canonical or canonical.get("sha256") != platform.sha256(platform.CANONICAL_BVM):
        result["reasons"].append("canonical BVM source hash mismatch or missing")
    for role, source in (("JJ_MODEL", platform.legacy.JJ_SOURCE), ("JTL", platform.legacy.JTL_SOURCE)):
        if source_role_hash(source_manifest, role) != platform.sha256(source):
            result["reasons"].append(f"{role} hash mismatch")
    snapshots = {item.get("role"): REPO / item["path"] for item in source_manifest.get("sources", []) if item.get("role") in {"BVM", "QB"}}
    expected_bvm = netlist_body(platform.legacy.render_bvm(params))
    if not snapshots.get("BVM") or not snapshots["BVM"].is_file() or netlist_body(snapshots["BVM"].read_text(encoding="utf-8")) != expected_bvm:
        result["reasons"].append("rendered BVM/source snapshot mismatch")
    if params["MODE"] == "closed":
        expected_qb = netlist_body(platform.legacy.render_qb(params))
        if not snapshots.get("QB") or not snapshots["QB"].is_file() or netlist_body(snapshots["QB"].read_text(encoding="utf-8")) != expected_qb:
            result["reasons"].append("rendered QB/source snapshot mismatch")
        elif source_role_hash(source_manifest, "QB") != platform.sha256(snapshots["QB"]):
            result["reasons"].append("QB snapshot hash does not match source manifest")
    config_snapshot = case_root / "config_snapshot.env"
    if not config_snapshot.is_file():
        result["reasons"].append("config snapshot missing")
    else:
        snapshot_values = platform.load_env(config_snapshot)
        for key in platform.CIRCUIT_KEYS | platform.STIMULUS_KEYS:
            if key not in snapshot_values:
                result["reasons"].append(f"config snapshot missing: {key}")
            elif not equal_value(snapshot_values[key], str(params[key])):
                result["reasons"].append(f"config snapshot mismatch: {key}")
    for mask in requested_masks:
        rid = run_id(params["MODE"], mask)
        run_dir = case_root / "cases" / rid
        raw_path = run_dir / "raw.csv"
        metadata_path = run_dir / "metadata.json"
        stimulus_path = run_dir / "stimulus.inc"
        if not raw_path.is_file() or not metadata_path.is_file() or not stimulus_path.is_file():
            result["reasons"].append(f"run artifact missing: {rid}")
            continue
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if metadata.get("execution_status") != "RUN_PASS":
            result["reasons"].append(f"metadata execution is not RUN_PASS: {rid}")
        actual_hash = platform.sha256(raw_path)
        if metadata.get("raw", {}).get("sha256") != actual_hash:
            result["reasons"].append(f"raw hash differs from metadata: {rid}")
        qa = raw_qa_for(case_root, rid)
        if not qa or qa.get("status") != "PASS":
            result["reasons"].append(f"raw QA missing or not PASS: {rid}")
        if stimulus_body(stimulus_path.read_text(encoding="utf-8")) != stimulus_body(platform.stimulus_text(params, mask)):
            result["reasons"].append(f"stored stimulus mismatch: {rid}")
        deck_path = run_dir / "actual_deck.cir"
        deck_text = deck_path.read_text(encoding="utf-8") if deck_path.is_file() else ""
        if f".tran {params['DT']} {params['STOP']}".lower() not in norm_line(deck_text):
            result["reasons"].append(f"deck timing mismatch: {rid}")
        result["runs"][mask] = {"run_id": rid, "raw_path": platform.repo_rel(raw_path), "raw_sha256": actual_hash, "grid_status": qa.get("grid_status") if qa else None}
    if not result["reasons"] and len(result["runs"]) == len(requested_masks):
        result["status"] = "REUSE"
        result["source_type"] = "REUSED_EXISTING"
    return result


def find_reuse(params: dict[str, Any], value: str) -> dict[str, Any]:
    candidates = []
    for path in sorted((SERIES / "runs").iterdir()):
        if path.is_dir() and (path.name.startswith("A") or path.name.startswith("U")):
            check = verify_existing(path, params, value)
            if check["status"] == "REUSE":
                return check
            candidates.append(check)
    return {"value": value, "status": "REUSE_REJECTED", "source_type": "NEW_REQUIRED", "reasons": ["no existing case passed strict reuse verification"], "candidate_checks": candidates, "runs": {}}


def sweep_setup(values: dict[str, str], reference: dict[str, str]) -> tuple[dict[str, Any], list[dict[str, Any]], list[str]]:
    key = values.get("SWEEP_KEY", "NONE").strip()
    if key not in SWEEP_ALLOWED or key in {"DT", "STOP"}:
        raise RuntimeError(f"SWEEP_KEY must be one real circuit/stimulus parameter (not {key!r})")
    raw_values = [item.strip() for item in values.get("SWEEP_VALUES", "").split(",") if item.strip()]
    if not raw_values or len(set(raw_values)) != len(raw_values):
        raise RuntimeError("SWEEP_VALUES must be a non-empty list of unique values")
    base = dict(values)
    base.update({"SWEEP_ENABLED": "no", "SWEEP_KEY": "NONE", "SWEEP_VALUES": ""})
    points = []
    for value in raw_values:
        point_values = dict(base)
        point_values[key] = value
        params = platform.validate(point_values, reference)
        params["config_changes"] = platform.change_rows(point_values, reference)
        reuse = find_reuse(params, value) if values.get("SWEEP_REUSE_EXISTING", "yes").lower() == "yes" else {"value": value, "status": "REUSE_DISABLED", "source_type": "NEW_REQUIRED", "reasons": [], "runs": {}}
        points.append({"value": value, "params": params, "reuse": reuse})
    return {"key": key, "values": raw_values, "name": values.get("NAME", "sweep"), "mode": values.get("MODE", "passive"), "masks": platform.resolve_masks(values.get("MASKS", "full")), "reuse_enabled": values.get("SWEEP_REUSE_EXISTING", "yes").lower() == "yes"}, points, raw_values


def write_temp_config(values: dict[str, str], path: Path, name: str, masks: list[str]) -> None:
    data = dict(values)
    data.update({"NAME": name, "MASKS": ",".join(masks), "SWEEP_ENABLED": "no", "SWEEP_KEY": "NONE", "SWEEP_VALUES": "", "SWEEP_REUSE_EXISTING": "yes"})
    path.write_text("\n".join(f"{key}={value}" for key, value in data.items() if key not in {"windows", "time_ps", "config_changes"}) + "\n", encoding="utf-8")


def render_svg_chart(rows: list[dict[str, Any]], x_key: str, y_keys: list[tuple[str, str]], title: str, width: int = 980, height: int = 240) -> str:
    xs = [float(row[x_key]) for row in rows if row.get(x_key) not in (None, "", "NONE")]
    if not xs:
        return ""
    x_min, x_max = min(xs), max(xs)
    if x_max == x_min:
        x_max = x_min + 1.0
    colors = ("#66ccff", "#ffcc66", "#66ff99", "#ff7799", "#bb99ff")
    vals = [float(row[key]) for key, _ in y_keys for row in rows if row.get(key) not in (None, "", "NONE")]
    if not vals:
        vals = [0.0]
    y_min, y_max = min(vals), max(vals)
    if y_min == y_max:
        y_min -= 1.0
        y_max += 1.0
    body = [f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 {width} {height}' style='width:100%;background:#111'><rect width='100%' height='100%' fill='#111'/><text x='50' y='18' fill='#fff' font-size='13'>{html.escape(title)}</text>"]
    for idx, (key, label) in enumerate(y_keys):
        pts = []
        for row in rows:
            value = row.get(key)
            if value in (None, "", "NONE"):
                continue
            x = 50 + (float(row[x_key]) - x_min) / (x_max - x_min) * (width - 80)
            y = height - 35 - (float(value) - y_min) / (y_max - y_min) * (height - 70)
            pts.append(f"{x:.2f},{y:.2f}")
        if pts:
            body.append(f"<polyline fill='none' stroke='{colors[idx % len(colors)]}' stroke-width='2' points='{' '.join(pts)}'/>")
            body.append(f"<text x='{60 + idx * 170}' y='{height - 8}' fill='{colors[idx % len(colors)]}' font-size='11'>{html.escape(label)}</text>")
    body.append(f"<line x1='50' x2='{width - 30}' y1='{height - 30}' y2='{height - 30}' stroke='#777'/><text x='50' y='{height - 15}' fill='#aaa' font-size='10'>{x_min:g}</text><text x='{width - 30}' y='{height - 15}' fill='#aaa' font-size='10' text-anchor='end'>{x_max:g}</text></svg>")
    return "".join(body)


def load_point_metrics(point: dict[str, Any], sweep: dict[str, Any], mask: str) -> dict[str, Any]:
    case_path = Path(point["case_path"])
    case_root = case_path if case_path.is_absolute() else (REPO / case_path if case_path.parts and case_path.parts[0] == "test" else SERIES / "runs" / case_path)
    params = point["params"]
    rid = run_id(params["MODE"], mask)
    run_dir = case_root / "cases" / rid
    with (run_dir / "raw.csv").open("r", encoding="utf-8", newline="") as stream:
        reader = csv.reader(stream)
        headers = next(reader)
        rows = [[float(x) for x in row] for row in reader]
    times = [row[0] * 1e12 for row in rows]
    windows = params["windows"]
    engine.WINDOWS = {name: (float(bounds[0]), float(bounds[1])) for name, bounds in windows.items()}
    engine.R_WINDOW = "final_read_110_121"
    engine.R_RECOVERY = "recovery_121_130"
    read_start, read_end = engine.WINDOWS["final_read_110_121"]
    recovery_end = engine.WINDOWS["recovery_121_130"][1]
    control_start = engine.WINDOWS["zero_read_control_70_81"][0]
    control_end = engine.WINDOWS["settle1_81_90"][1]
    bvm_index = max([index + 1 for index, bit in enumerate(mask) if bit == "1"] or [1])

    def values_for(signal: str, start: float, end: float) -> tuple[list[float], list[float]]:
        if signal not in headers:
            return [], []
        column = headers.index(signal)
        selected = [(time, row[column]) for time, row in zip(times, rows) if start <= time < end]
        return [item[0] for item in selected], [item[1] for item in selected]

    def metric(signal: str, start: float, end: float) -> dict[str, Any]:
        ts, vals = values_for(signal, start, end)
        return {"min": min(vals) if vals else None, "max": max(vals) if vals else None, "rms": engine.rms(vals), "integral_si": engine.trapezoid(ts, vals), "p2p": engine.p2p(vals), "values": vals, "times": ts}

    def waveform(signal: str, start: float, end: float) -> dict[str, Any]:
        item = metric(signal, start, end)
        ts, vals = item["times"], item["values"]
        positive = [(value, time) for value, time in zip(vals, ts) if value > 0]
        negative = [(value, time) for value, time in zip(vals, ts) if value < 0]
        return {"positive_peak": max(positive, default=(0.0, None))[0], "negative_peak": min(negative, default=(0.0, None))[0], "signed_area": engine.trapezoid(ts, vals), "absolute_area": engine.trapezoid(ts, [abs(value) for value in vals]), "rms": engine.rms(vals)}

    def phase(signal: str, start: float, end: float) -> dict[str, Any]:
        ts, vals = values_for(signal, start, end)
        unwrapped = engine.unwrap(vals) if vals else []
        origin = unwrapped[0] if unwrapped else 0.0
        crossing = {str(threshold): next((ts[index] for index, value in enumerate(unwrapped) if abs((value - origin) / (2 * math.pi)) >= threshold), None) for threshold in (0.5, 1.0, 1.5, 2.0)}
        return {"net": (unwrapped[-1] - origin) / (2 * math.pi) if unwrapped else None, "p2p": (max(unwrapped) - min(unwrapped)) / (2 * math.pi) if unwrapped else None, "crossing": crossing}

    def forward(signal: str, start: float, end: float) -> dict[str, Any]:
        ts, vals = values_for(signal, start, end)
        unwrapped = engine.unwrap(vals) if vals else []
        relative = [(value - unwrapped[0]) / (2 * math.pi) for value in unwrapped] if unwrapped else []
        crossing = {str(threshold): next((ts[index] for index, value in enumerate(relative) if value >= threshold), None) for threshold in (0.5, 1.5)}
        return {"max": max(relative, default=None), "min": min(relative, default=None), "net": relative[-1] if relative else None, "p2p": max(relative) - min(relative) if relative else None, "t0p5": crossing["0.5"], "t1p5": crossing["1.5"]}

    def zero_up(signal: str, start: float, end: float) -> float | None:
        ts, vals = values_for(signal, start, end)
        return next((time for left, right, time in zip(vals, vals[1:], ts[1:]) if left <= 0 < right), None)

    def terminal(start: float, end: float) -> dict[str, Any]:
        ts, vals = values_for("I(R_TERM)", start, end)
        candidates = [(ts[index], vals[index]) for index in range(1, len(vals) - 1) if vals[index] >= 50e-6 and vals[index] >= vals[index - 1] and vals[index] >= vals[index + 1]]
        selected: list[tuple[float, float]] = []
        for candidate in candidates:
            if not selected or candidate[0] - selected[-1][0] >= 2.5:
                selected.append(candidate)
            elif candidate[1] > selected[-1][1]:
                selected[-1] = candidate
        return {"count": len(selected), "first": selected[0][0] if selected else None, "max": max((value for _, value in selected), default=None)}

    js: dict[str, dict[str, Any]] = {}
    for index in (1, 2):
        prefix = f"B_JS{index}|XBVM{bvm_index}"
        p = phase(f"P({prefix})", read_start, read_end)
        pr = phase(f"P({prefix})", read_start, recovery_end)
        p200 = phase(f"P({prefix})", read_start, engine.WINDOWS["whole_0_200"][1])
        v = metric(f"V({prefix})", read_start, read_end)
        js[f"JS{index}"] = {"net": p["net"], "p2p": p["p2p"], "net_130": pr["net"], "net_200": p200["net"], "cross": p["crossing"], "vmin": v["min"], "vmax": v["max"], "vrms": v["rms"], "varea": v["integral_si"] / 2.067833848e-15}
    final_output = waveform("I(B_JSL8)", read_start, read_end)
    control_output = waveform("I(B_JSL8)", control_start, control_end)
    l1 = metric("I(L1|XBQ1)", read_start, recovery_end)
    l2 = metric("I(L2|XBQ1)", read_start, recovery_end)
    bj1 = forward("P(BJ1|XBQ1)", read_start, recovery_end)
    bj2 = forward("P(BJ2|XBQ1)", read_start, recovery_end)
    cbj1 = forward("P(BJ1|XBQ1)", control_start, control_end)
    cbj2 = forward("P(BJ2|XBQ1)", control_start, control_end)
    cl1 = metric("I(L1|XBQ1)", control_start, control_end)
    term = terminal(read_start, engine.WINDOWS["whole_0_200"][1])
    cterm = terminal(control_start, control_end)
    row: dict[str, Any] = {"SWEEP_VALUE_RAW": str(point["value"]), "SWEEP_VALUE_SI": sweep_numeric(str(point["value"])), "MASK": mask, "POPULATION": f"N{mask.count('1')}", "RUN_ID": rid, "source_type": point["source_type"], "source_case": point.get("source_case", point.get("case_path")), "physical_solve_new": point.get("physical_solve_new", False), "raw_sha256": point.get("runs", {}).get(mask, {}).get("raw_sha256", point.get("raw_sha256")), "raw_qa_status": point.get("runs", {}).get(mask, {}).get("raw_qa_status", point.get("raw_qa_status", "PASS")), "grid_status": point.get("runs", {}).get(mask, {}).get("grid_status", point.get("grid_status"))}
    for index in (1, 2):
        item = js[f"JS{index}"]
        row.update({f"JS{index}_read_net": item["net"], f"JS{index}_read_recovery_net": item["net_130"], f"JS{index}_to_200_net": item["net_200"], f"JS{index}_p2p": item["p2p"], f"JS{index}_Vmin": item["vmin"], f"JS{index}_Vmax": item["vmax"], f"JS{index}_VRMS": item["vrms"], f"JS{index}_Varea_phi0": item["varea"]})
        for threshold, crossing in item["cross"].items():
            row[f"JS{index}_t_minus_{threshold.replace('.', 'p')}"] = crossing - read_start if crossing is not None else None
    row.update({"FINAL_JSL8_peak_positive": final_output["positive_peak"], "FINAL_JSL8_signed_area": final_output["signed_area"] / 2.067833848e-15, "FINAL_JSL8_absolute_area": final_output["absolute_area"] / 2.067833848e-15, "CONTROL_JSL8_peak_positive": control_output["positive_peak"], "CONTROL_JSL8_signed_area": control_output["signed_area"] / 2.067833848e-15, "QB_L1_I_min": l1["min"], "QB_L1_I_max": l1["max"], "QB_L1_zero_cross_up_ps": zero_up("I(L1|XBQ1)", read_start, recovery_end), "QB_L2_I_min": l2["min"], "QB_L2_I_max": l2["max"], "BJ1_forward_max_turn": bj1["max"], "BJ1_forward_min_turn": bj1["min"], "BJ1_net_turn": bj1["net"], "BJ1_p2p_turn": bj1["p2p"], "BJ1_t_plus_0p5_ps": bj1["t0p5"], "BJ1_t_plus_1p5_ps": bj1["t1p5"], "BJ2_forward_max_turn": bj2["max"], "BJ2_forward_min_turn": bj2["min"], "BJ2_net_turn": bj2["net"], "BJ2_p2p_turn": bj2["p2p"], "BJ2_t_plus_0p5_ps": bj2["t0p5"], "BJ2_t_plus_1p5_ps": bj2["t1p5"], "CONTROL_BJ1_forward_max_turn": cbj1["max"], "CONTROL_BJ2_forward_max_turn": cbj2["max"], "CONTROL_L1_I_max": cl1["max"], "CONTROL_L1_I_min": cl1["min"], "terminal_candidate_count": term["count"], "terminal_first_peak_ps": term["first"], "terminal_max_peak_A": term["max"], "control_terminal_candidate_count": cterm["count"], "control_terminal_first_peak_ps": cterm["first"], "control_terminal_max_peak_A": cterm["max"]})
    return row


def write_batch_review(batch_root: Path, sweep: dict[str, Any], rows: list[dict[str, Any]], reused: list[dict[str, Any]], new_cases: list[str], failed: list[dict[str, Any]]) -> None:
    body = ["<!doctype html><html><head><meta charset='utf-8'><title>" + html.escape(batch_root.name) + "</title><style>body{font-family:Arial;background:#111;color:#eee;margin:20px}a{color:#8ecbff}section{border:1px solid #444;padding:12px;margin:16px 0}table{border-collapse:collapse;width:100%;font-size:11px}td,th{border:1px solid #555;padding:4px}th{background:#292929}</style></head><body>", f"<h1>{html.escape(batch_root.name)}</h1><p>Sweep key: <code>{html.escape(sweep['key'])}</code> · values: {', '.join(html.escape(v) for v in sweep['values'])} · masks: {', '.join(sweep['masks'])}</p>", f"<p>Logical parameter points: {len(sweep['values'])} · logical runs: {len(sweep['values']) * len(sweep['masks'])} · reused points: {len(reused)} · new cases: {len(new_cases)} · failed points: {len(failed)}</p>"]
    for mask in sweep["masks"]:
        subset = [row for row in rows if row.get("MASK") == mask]
        label = f"N{mask.count('1')} / {mask}"
        body.extend([f"<section><h2>{label}</h2>", render_svg_chart(subset, "SWEEP_VALUE_SI", [("QB_L1_I_max", "I(L1) max"), ("BJ1_forward_max_turn", "BJ1 forward max"), ("BJ2_forward_max_turn", "BJ2 forward max"), ("terminal_candidate_count", "terminal candidates")], f"{label} QB sweep"), render_svg_chart(subset, "SWEEP_VALUE_SI", [("CONTROL_BJ1_forward_max_turn", "control BJ1 forward max"), ("control_terminal_candidate_count", "control terminal candidates")], f"{label} control")])
        table = ["<table><tr><th>SWEEP_VALUE</th><th>MASK</th><th>RUN_ID</th><th>source</th><th>raw QA</th><th>I(L1) max</th><th>BJ1 fwd max</th><th>BJ2 fwd max</th><th>terminal candidates</th><th>control terminal</th></tr>"]
        for row in subset:
            table.append(f"<tr><td>{html.escape(str(row['SWEEP_VALUE_RAW']))}</td><td>{row['MASK']}</td><td>{row['RUN_ID']}</td><td>{html.escape(str(row['source_type']))}</td><td>{row['raw_qa_status']}</td><td>{row['QB_L1_I_max']}</td><td>{row['BJ1_forward_max_turn']}</td><td>{row['BJ2_forward_max_turn']}</td><td>{row['terminal_candidate_count']}</td><td>{row['control_terminal_candidate_count']}</td></tr>")
        body.extend(table + ["</table></section>"])
    body.append("<p>No scientific interpretation performed. Phase turns and terminal locators are navigation/mechanical metrics, not SFQ counts.</p></body></html>")
    (batch_root / "BATCH_REVIEW.html").write_text("\n".join(body), encoding="utf-8")


def execute_sweep(values: dict[str, str], reference: dict[str, str], args: Any) -> int:
    sweep, points, _ = sweep_setup(values, reference)
    existing_batches = list((SERIES / "batches").iterdir()) if (SERIES / "batches").is_dir() else []
    batch_numbers = [int(match.group(1)) for path in existing_batches if (match := re.match(r"^B(\d{3})_", path.name))]
    batch_name = f"B{max(batch_numbers, default=0) + 1:03d}_{sweep['name']}"
    logical_points = len(points)
    logical_runs = logical_points * len(sweep["masks"])
    if args.dry_run:
        print("BATCH PREVIEW\n\nNAME\n" + sweep["name"] + "\n\nSWEEP\n" + sweep["key"] + "\n\nVALUES\n" + "\n".join(sweep["values"]) + "\n\nMASKS\n" + "\n".join(f"N{mask.count('1')} / {mask}" for mask in sweep["masks"]) + f"\n\nLOGICAL PARAMETER POINTS\n{logical_points}\n\nLOGICAL RUNS\n{logical_runs}\n\nREUSE CANDIDATES")
        for point in points:
            reuse = point["reuse"]
            print(f"{point['value']} -> {reuse.get('case_id', 'NONE')} : {reuse['status']}" if reuse.get("case_id") else f"{point['value']} -> {reuse['status']}")
        new = [point for point in points if point["reuse"]["status"] != "REUSE"]
        print(f"\nNEW PHYSICAL SOLVES IF RUN\n{len(new) * len(sweep['masks'])}\n\nNo solve executed.")
        return 0
    batch_root = SERIES / "batches" / batch_name
    batch_root.mkdir(parents=True, exist_ok=False)
    manifest = {"schema": "bvm-rloop-sweep-batch-v2", "batch_id": batch_name, "sweep_key": sweep["key"], "values": sweep["values"], "mode": sweep["mode"], "requested_masks": sweep["masks"], "logical_parameter_points": logical_points, "logical_run_count": logical_runs, "reuse_enabled": sweep["reuse_enabled"], "points": []}
    platform.write_json(batch_root / "BATCH_MANIFEST.json", manifest)
    point_records: list[dict[str, Any]] = []
    new_cases: list[str] = []
    failed: list[dict[str, Any]] = []
    reused_points = reused_runs = new_physical = 0
    for point in points:
        reuse = point["reuse"]
        record = {"value": point["value"], "source_type": reuse.get("source_type"), "source_case": reuse.get("case_id"), "case_path": reuse.get("case_id"), "physical_solve_new": False, "reuse_rejected_reason": reuse.get("reasons", []), "runs": {}}
        if reuse["status"] == "REUSE":
            record["source_type"] = "REUSED_EXISTING"
            record["runs"] = reuse.get("runs", {})
            reused_points += 1
            reused_runs += len(sweep["masks"])
        else:
            point_values = dict(values)
            point_values[sweep["key"]] = point["value"]
            point_values["NAME"] = f"{sweep['name']}_{sweep['key'].lower()}_{point['value'].replace('.', 'p')}"
            with tempfile.NamedTemporaryFile(prefix="bvm_sweep_", suffix=".env", delete=False, dir="/tmp", mode="w", encoding="utf-8") as handle:
                temp_path = Path(handle.name)
                write_temp_config(point_values, temp_path, point_values["NAME"], sweep["masks"])
            before = {path.name for path in (SERIES / "runs").iterdir() if path.is_dir()}
            completed = subprocess.run([sys.executable, str(SERIES / "scripts" / "try_candidate.py"), "--config", str(temp_path)], cwd=REPO, text=True, capture_output=True, check=False)
            temp_path.unlink(missing_ok=True)
            created = sorted({path.name for path in (SERIES / "runs").iterdir() if path.is_dir()} - before)
            if completed.returncode != 0 or len(created) != 1:
                failed.append({"value": point["value"], "reason": completed.stderr[-2000:], "created_cases": created})
                record.update({"source_type": "NEW_FAILED", "physical_solve_new": True, "status": "FAILED"})
                point_records.append(record)
                continue
            case_name = created[0]
            case_root = SERIES / "runs" / case_name
            qa = json.loads((case_root / "qa" / "raw_qa.json").read_text(encoding="utf-8"))
            rows_by_mask = {row["run_id"].split("_", 2)[-1]: row for row in qa.get("rows", [])}
            record.update({"source_type": "NEW_PHYSICAL", "source_case": case_name, "case_path": case_name, "physical_solve_new": True, "runs": {mask: {"run_id": run_id(sweep["mode"], mask), "raw_path": rows_by_mask.get(mask, {}).get("path"), "raw_sha256": rows_by_mask.get(mask, {}).get("sha256"), "grid_status": rows_by_mask.get(mask, {}).get("grid_status"), "raw_qa_status": rows_by_mask.get(mask, {}).get("status")} for mask in sweep["masks"]}})
            new_cases.append(case_name)
            new_physical += int(json.loads((case_root / "case_manifest.json").read_text(encoding="utf-8")).get("physical_solve_count", len(sweep["masks"])))
        point_records.append(record)
    flat: list[dict[str, Any]] = []
    for point, record in zip(points, point_records):
        if record.get("status") == "FAILED":
            continue
        for mask in sweep["masks"]:
            run_info = record.get("runs", {}).get(mask, {})
            if run_info.get("raw_qa_status", "PASS") != "PASS":
                continue
            row = load_point_metrics({**record, "params": point["params"], "value": point["value"]}, sweep, mask)
            case_name = record.get("case_path")
            row["case_review_path"] = f"../../plots/{case_name}/review.html" if case_name else None
            row["raw_path"] = run_info.get("raw_path") or (f"../../runs/{case_name}/cases/{row['RUN_ID']}/raw.csv" if case_name else None)
            row["config_path"] = f"../../runs/{case_name}/config_snapshot.env" if case_name else None
            flat.append(row)
    fields = sorted({key for row in flat for key in row})
    with (batch_root / "BATCH_SUMMARY.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(flat)
    write_batch_review(batch_root, sweep, flat, [record for record in point_records if record.get("source_type") == "REUSED_EXISTING"], new_cases, failed)
    qa = {"schema": "bvm-rloop-sweep-batch-qa-v2", "status": "PASS" if len(flat) == logical_runs and not failed and all(row.get("raw_qa_status") == "PASS" for row in flat) else "FAIL", "logical_parameter_points": logical_points, "logical_run_count": logical_runs, "requested_masks": sweep["masks"], "reused_parameter_points": reused_points, "reused_run_count": reused_runs, "new_case_count": len(new_cases), "new_physical_solve_count": new_physical, "failed_parameter_points": failed, "raw_hashes_rechecked": not failed}
    platform.write_json(batch_root / "BATCH_QA.json", qa)
    platform.write_json(batch_root / "BATCH_MANIFEST.json", {**manifest, "points": point_records, "qa": qa, "status": "BATCH_COMPLETE_AWAITING_SCIENTIFIC_REVIEW"})
    (SERIES / "LATEST_BATCH_REVIEW.html").write_text(f"<!doctype html><html><head><meta http-equiv='refresh' content='0; url=batches/{batch_name}/BATCH_REVIEW.html'></head><body><a href='batches/{batch_name}/BATCH_REVIEW.html'>{batch_name}</a></body></html>\n", encoding="utf-8")
    print(json.dumps({"status": qa["status"], "batch_id": batch_name, "logical_parameter_points": logical_points, "logical_run_count": logical_runs, "reused_parameter_points": reused_points, "reused_run_count": reused_runs, "new_case_count": len(new_cases), "new_physical_solve_count": new_physical, "failed_parameter_points": len(failed)}, ensure_ascii=False, indent=2))
    return 0 if qa["status"] == "PASS" else 2
