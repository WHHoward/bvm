#!/usr/bin/env python3
"""Strict one-dimensional sweep orchestration for USER_CASE.env."""

from __future__ import annotations

import csv
import html
import json
import math
import os
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
MASK = "1111"
SWEEP_ALLOWED = platform.CIRCUIT_KEYS | platform.STIMULUS_KEYS


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
        return abs(platform.parse_number(left, "compare") - platform.parse_number(right, "compare")) <= 1e-18 * max(1.0, abs(platform.parse_number(right, "compare")))
    except RuntimeError:
        return left.strip().lower() == right.strip().lower()


def raw_qa_for(case_root: Path, run_id: str) -> dict[str, Any] | None:
    candidates = [case_root / "qa" / "raw_qa.json", SERIES / "qa" / "raw_qa.json"]
    for path in candidates:
        if not path.is_file():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        for row in data.get("rows", []):
            if row.get("run_id") == run_id and (row.get("case_id") in {None, case_root.name}):
                return row
    return None


def source_role_hash(source_manifest: dict[str, Any], role: str) -> str | None:
    for item in source_manifest.get("sources", []):
        if item.get("role") == role:
            return item.get("sha256")
    return None


def verify_existing(case_root: Path, params: dict[str, Any], value: str) -> dict[str, Any]:
    result = {"case_id": case_root.name, "value": value, "status": "REUSE_REJECTED", "source_type": "EXISTING_REJECTED", "reasons": []}
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
    if str(manifest.get("parameters", {}).get("MODE", "")).lower() != params["MODE"]:
        result["reasons"].append("MODE mismatch")
    expected_run_id = f"{params['MODE'].upper()}_N4_{MASK}"
    if expected_run_id not in manifest.get("run_order", []):
        result["reasons"].append("requested mask 1111 is absent")
    canonical = source_manifest.get("canonical_bvm_source") or source_manifest.get("canonical_bvm_reference")
    if not canonical or canonical.get("sha256") != platform.sha256(platform.CANONICAL_BVM):
        result["reasons"].append("canonical BVM source hash mismatch or missing")
    if source_role_hash(source_manifest, "JJ_MODEL") != platform.sha256(platform.legacy.JJ_SOURCE):
        result["reasons"].append("JJ model hash mismatch")
    run_dir = case_root / "cases" / f"PASSIVE_N4_{MASK}"
    raw_path = run_dir / "raw.csv"
    metadata_path = run_dir / "metadata.json"
    if not raw_path.is_file() or not metadata_path.is_file():
        result["reasons"].append("requested raw or metadata missing")
        return result
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if metadata.get("execution_status") != "RUN_PASS":
        result["reasons"].append("metadata execution is not RUN_PASS")
    actual_hash = platform.sha256(raw_path)
    if metadata.get("raw", {}).get("sha256") != actual_hash:
        result["reasons"].append("raw hash differs from metadata")
    qa = raw_qa_for(case_root, metadata.get("run_id", ""))
    if not qa or qa.get("status") != "PASS":
        result["reasons"].append("raw QA missing or not PASS")
    snapshot_bvm = None
    for item in source_manifest.get("sources", []):
        if item.get("role") == "BVM":
            snapshot_bvm = REPO / item["path"]
    expected_params = dict(params)
    expected_bvm = netlist_body(platform.legacy.render_bvm(expected_params))
    if not snapshot_bvm or not snapshot_bvm.is_file() or netlist_body(snapshot_bvm.read_text(encoding="utf-8")) != expected_bvm:
        result["reasons"].append("rendered BVM/source snapshot does not exactly match target parameters")
    stimulus_path = run_dir / "stimulus.inc"
    expected_stimulus = stimulus_body(platform.stimulus_text(expected_params, MASK))
    if not stimulus_path.is_file() or stimulus_body(stimulus_path.read_text(encoding="utf-8")) != expected_stimulus:
        result["reasons"].append("stored stimulus waveform does not exactly match target stimulus")
    deck_path = run_dir / "actual_deck.cir"
    deck_text = deck_path.read_text(encoding="utf-8") if deck_path.is_file() else ""
    if f".tran {params['DT']} {params['STOP']}".lower() not in norm_line(deck_text):
        result["reasons"].append("deck timing does not match target DT/STOP")
    config_snapshot = case_root / "config_snapshot.env"
    if config_snapshot.is_file():
        snapshot_values = platform.load_env(config_snapshot)
        for key in platform.CIRCUIT_KEYS | platform.STIMULUS_KEYS:
            if key in snapshot_values and key in expected_params and not equal_value(snapshot_values[key], expected_params[key]):
                result["reasons"].append(f"config snapshot mismatch: {key}")
    result.update({"raw_path": platform.repo_rel(raw_path), "raw_sha256": actual_hash, "run_id": metadata.get("run_id"), "grid_status": qa.get("grid_status") if qa else None})
    if not result["reasons"]:
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
    return {"value": value, "status": "REUSE_REJECTED", "source_type": "NEW_REQUIRED", "reasons": ["no existing case passed strict reuse verification"], "candidate_checks": candidates}


def sweep_setup(values: dict[str, str], reference: dict[str, str]) -> tuple[dict[str, Any], list[dict[str, Any]], list[str]]:
    key = values.get("SWEEP_KEY", "NONE").strip()
    if key not in SWEEP_ALLOWED or key in {"DT", "STOP"}:
        raise RuntimeError(f"SWEEP_KEY must be one real circuit/stimulus parameter (not {key!r})")
    raw_values = [item.strip() for item in values.get("SWEEP_VALUES", "").split(",") if item.strip()]
    if not raw_values or len(set(raw_values)) != len(raw_values):
        raise RuntimeError("SWEEP_VALUES must be a non-empty list of unique values")
    base = dict(values)
    base["SWEEP_ENABLED"] = "no"
    base["SWEEP_KEY"] = "NONE"
    base["SWEEP_VALUES"] = ""
    base["SWEEP_REUSE_EXISTING"] = values.get("SWEEP_REUSE_EXISTING", "yes")
    points = []
    for value in raw_values:
        point_values = dict(base); point_values[key] = value
        params = platform.validate(point_values, reference)
        params["config_changes"] = platform.change_rows(point_values, reference)
        points.append({"value": value, "params": params, "reuse": find_reuse(params, value) if values.get("SWEEP_REUSE_EXISTING", "yes").lower() == "yes" else {"value": value, "status": "REUSE_DISABLED", "source_type": "NEW_REQUIRED", "reasons": []}})
    return {"key": key, "values": raw_values, "name": values.get("NAME", "sweep"), "mode": values.get("MODE", "passive"), "masks": platform.resolve_masks(values.get("MASKS", "full")), "reuse_enabled": values.get("SWEEP_REUSE_EXISTING", "yes").lower() == "yes"}, points, raw_values


def write_temp_config(values: dict[str, str], path: Path, name: str) -> None:
    data = dict(values)
    data.update({"NAME": name, "SWEEP_ENABLED": "no", "SWEEP_KEY": "NONE", "SWEEP_VALUES": "", "SWEEP_REUSE_EXISTING": "yes", "MASKS": MASK})
    path.write_text("\n".join(f"{key}={value}" for key, value in data.items() if key not in {"windows", "time_ps", "config_changes"}) + "\n", encoding="utf-8")


def render_svg_chart(rows: list[dict[str, Any]], x_key: str, y_keys: list[tuple[str, str]], title: str, width: int = 980, height: int = 240) -> str:
    xs = [float(row[x_key]) for row in rows]
    if not xs:
        return ""
    x_min, x_max = min(xs), max(xs)
    if x_max == x_min: x_max = x_min + 1.0
    colors = ("#66ccff", "#ffcc66", "#66ff99", "#ff7799", "#bb99ff")
    values = []
    for key, _label in y_keys:
        values.extend(float(row[key]) for row in rows if row.get(key) not in (None, "", "NONE"))
    if not values: values = [0.0]
    y_min, y_max = min(values), max(values)
    if y_min == y_max: y_min -= 1.0; y_max += 1.0
    body = [f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 {width} {height}' style='width:100%;background:#111'><rect width='100%' height='100%' fill='#111'/><text x='50' y='18' fill='#fff' font-size='13'>{html.escape(title)}</text>"]
    for idx, (key, label) in enumerate(y_keys):
        pts=[]
        for row in rows:
            value=row.get(key)
            if value in (None,"","NONE"): continue
            x=50+(float(row[x_key])-x_min)/(x_max-x_min)*(width-80)
            y=height-35-(float(value)-y_min)/(y_max-y_min)*(height-70)
            pts.append(f"{x:.2f},{y:.2f}")
        if pts:
            body.append(f"<polyline fill='none' stroke='{colors[idx%len(colors)]}' stroke-width='2' points='{' '.join(pts)}'/>")
            body.append(f"<text x='{60+idx*170}' y='{height-8}' fill='{colors[idx%len(colors)]}' font-size='11'>{html.escape(label)}</text>")
    body.append(f"<line x1='50' x2='{width-30}' y1='{height-30}' y2='{height-30}' stroke='#777'/><text x='50' y='{height-15}' fill='#aaa' font-size='10'>{x_min:g}</text><text x='{width-30}' y='{height-15}' fill='#aaa' font-size='10' text-anchor='end'>{x_max:g}</text></svg>")
    return "".join(body)


def load_point_metrics(point: dict[str, Any], sweep: dict[str, Any]) -> dict[str, Any]:
    case_root = REPO / point["case_path"]
    run_dir = case_root / "cases" / "PASSIVE_N4_1111"
    raw = run_dir / "raw.csv"
    with raw.open("r", encoding="utf-8", newline="") as stream:
        reader=csv.reader(stream); headers=next(reader); rows=[[float(x) for x in row] for row in reader]
    times=[row[0]*1e12 for row in rows]
    params=point["params"]
    windows=params["windows"]
    engine.WINDOWS={name:(float(bounds[0]),float(bounds[1])) for name,bounds in windows.items()}
    engine.STATE_WINDOWS=tuple(name for name in ("write0_50_61","zero_read_control_70_81","write1_90_101","settle_101_110","final_read_110_121","recovery_121_130","tail_150_200") if name in engine.WINDOWS)
    engine.R_WINDOW="final_read_110_121"; engine.R_RECOVERY="recovery_121_130"
    def phase_range(prefix: str, start: float, end: float) -> dict[str, Any]:
        name=f"P({prefix})"; vals=[row[headers.index(name)] for row,t in zip(rows,times) if start<=t<end]; ts=[t for t in times if start<=t<end]
        un=engine.unwrap(vals) if vals else []
        origin=un[0] if un else 0.0
        crossings={str(thr): next((ts[i] for i,v in enumerate(un) if abs((v-origin)/(2*math.pi))>=thr), None) for thr in (0.5,1.0,1.5,2.0)}
        return {"net_turns":(un[-1]-un[0])/(2*math.pi) if len(un)>=2 else None,"p2p_turns":(max(un)-min(un))/(2*math.pi) if un else None,"crossings_abs_ps":crossings,"crossings_rel_ps":{key:(value-start if value is not None else None) for key,value in crossings.items()}}
    def scalar(signal: str, start: float, end: float) -> dict[str, Any]:
        return engine.signal_metric(headers, rows, times, signal, "custom") if False else custom_metric(signal,start,end)
    def custom_metric(signal: str,start: float,end: float) -> dict[str,Any]:
        vals=[row[headers.index(signal)] for row,t in zip(rows,times) if start<=t<end]; ts=[t for t in times if start<=t<end]
        return {"min":min(vals) if vals else None,"max":max(vals) if vals else None,"rms":engine.rms(vals),"integral_si":engine.trapezoid(ts,vals),"value_start":vals[0] if vals else None,"value_end":vals[-1] if vals else None,"p2p":engine.p2p(vals)}
    def waveform_descriptor(signal: str, start: float, end: float) -> dict[str, Any]:
        values=[row[headers.index(signal)] for row,t in zip(rows,times) if start<=t<end]
        ts=[t for t in times if start<=t<end]
        signed=engine.trapezoid(ts, values)
        absolute=engine.trapezoid(ts, [abs(value) for value in values])
        positive_time=sum(right-left for left,right,value in zip(ts,ts[1:],values) if value>0)
        negative_time=sum(right-left for left,right,value in zip(ts,ts[1:],values) if value<0)
        positive=[(value,time) for value,time in zip(values,ts) if value>0]
        negative=[(value,time) for value,time in zip(values,ts) if value<0]
        zero_cross=next((time for left,right,time in zip(values,values[1:],ts[1:]) if (left<=0<right) or (left>=0>right)), None)
        return {"positive_peak":max((value for value,_ in positive),default=0.0),"positive_peak_time":max(positive,default=(0.0,None))[1],"negative_peak":min((value for value,_ in negative),default=0.0),"negative_peak_time":min(negative,default=(0.0,None))[1],"signed_area":signed,"absolute_area":absolute,"rms":engine.rms(values),"positive_support_ps":positive_time,"negative_support_ps":negative_time,"zero_cross":zero_cross}
    read_start, read_end=windows["final_read_110_121"]; recovery_end=windows["recovery_121_130"][1]; stop=windows["whole_0_200"][1]; control_start,control_end=windows["zero_read_control_70_81"]
    js={}
    for j in (1,2):
        prefix=f"B_JS{j}|XBVM4"; v=custom_metric(f"V(B_JS{j}|XBVM4)",read_start,read_end); r=phase_range(prefix,read_start,read_end); r.update({"net_turns_110_130":phase_range(prefix,read_start,recovery_end)["net_turns"],"p2p_turns_110_130":phase_range(prefix,read_start,recovery_end)["p2p_turns"],"net_turns_110_200":phase_range(prefix,read_start,stop)["net_turns"],"p2p_turns_110_200":phase_range(prefix,read_start,stop)["p2p_turns"],"voltage_min":v["min"],"voltage_max":v["max"],"voltage_rms":v["rms"],"voltage_area_phi0":v["integral_si"]/2.067833848e-15,"first_major_voltage_activity":None})
        activity=engine.activity_clusters([t for t in times if read_start<=t<read_end],[row[headers.index(f"V(B_JS{j}|XBVM4)")] for row,t in zip(rows,times) if read_start<=t<read_end]); r["first_major_voltage_activity"]=activity.get("first_activity_ps"); r["mechanical_label"]="MULTI_PROGRESSION" if r["crossings_abs_ps"].get("1.5") is not None else "SINGLE_PROGRESSION_CANDIDATE" if (r["net_turns_110_130"] is not None and r["net_turns_110_130"]<=-0.75 and r["crossings_abs_ps"].get("1.0") is not None) else "INCOMPLETE_OR_DELAYED" if (r["net_turns_110_200"] is None or r["net_turns_110_200"]>-0.75) else "AMBIGUOUS"; js[f"JS{j}"]=r
    output_final=custom_metric("I(B_JSL8)",read_start,read_end); output_control=custom_metric("I(B_JSL8)",control_start,control_end); output_control90=custom_metric("I(B_JSL8)",control_start,windows["settle1_81_90"][1]); output_final_desc=waveform_descriptor("I(B_JSL8)",read_start,read_end); output_control_desc=waveform_descriptor("I(B_JSL8)",control_start,control_end)
    ls3i=custom_metric("I(L_S3|XBVM4)",read_start,recovery_end); ls3v=custom_metric("V(L_S3|XBVM4)",read_start,recovery_end); rs=custom_metric("I(R_S|XBVM4)",read_start,recovery_end); ls3i_desc=waveform_descriptor("I(L_S3|XBVM4)",read_start,recovery_end)
    state={}
    for j in (1,2):
        for label,window in (("JM1", "B_JM1"),("JM2","B_JM2")):
            pass
    for name in ("write0_50_61","zero_read_control_70_81","write1_90_101","settle_101_110","final_read_110_121","recovery_121_130","tail_150_200"):
        start,end=windows[name]; state[name]={"JM1":phase_range("B_JM1|XBVM4",start,end)["net_turns"],"JM2":phase_range("B_JM2|XBVM4",start,end)["net_turns"]}
    return {"JS1_AREA":params[sweep["key"]],"source_type":point["source_type"],"source_case":point.get("source_case",point.get("case_path")),"physical_solve_new":point.get("physical_solve_new",False),"raw_sha256":point["raw_sha256"],"raw_qa_status":point["raw_qa_status"],"grid_status":point.get("grid_status"),"JS1_read_net":js["JS1"]["net_turns"],"JS1_read_recovery_net":js["JS1"]["net_turns_110_130"],"JS1_to_200_net":js["JS1"]["net_turns_110_200"],"JS1_p2p":js["JS1"]["p2p_turns"],"JS1_t_minus_0p5":js["JS1"]["crossings_rel_ps"]["0.5"],"JS1_t_minus_1":js["JS1"]["crossings_rel_ps"]["1.0"],"JS1_t_minus_1p5":js["JS1"]["crossings_rel_ps"]["1.5"],"JS1_t_minus_2":js["JS1"]["crossings_rel_ps"]["2.0"],"JS2_read_net":js["JS2"]["net_turns"],"JS2_read_recovery_net":js["JS2"]["net_turns_110_130"],"JS2_to_200_net":js["JS2"]["net_turns_110_200"],"JS2_p2p":js["JS2"]["p2p_turns"],"JS2_t_minus_0p5":js["JS2"]["crossings_rel_ps"]["0.5"],"JS2_t_minus_1":js["JS2"]["crossings_rel_ps"]["1.0"],"JS2_t_minus_1p5":js["JS2"]["crossings_rel_ps"]["1.5"],"JS2_t_minus_2":js["JS2"]["crossings_rel_ps"]["2.0"],"JS1_Vmin":js["JS1"]["voltage_min"],"JS2_Vmin":js["JS2"]["voltage_min"],"LS3_positive_peak":ls3i_desc["positive_peak"],"LS3_positive_peak_time":ls3i_desc["positive_peak_time"],"LS3_zero_cross":ls3i_desc["zero_cross"],"LS3_negative_trough":ls3i_desc["negative_peak"],"LS3_negative_trough_time":ls3i_desc["negative_peak_time"],"FINAL_JSL8_peak_positive":output_final_desc["positive_peak"],"FINAL_JSL8_peak_time":output_final_desc["positive_peak_time"],"FINAL_JSL8_signed_area":output_final_desc["signed_area"]/2.067833848e-15,"FINAL_JSL8_absolute_area":output_final_desc["absolute_area"]/2.067833848e-15,"FINAL_JSL8_RMS":output_final_desc["rms"],"FINAL_JSL8_positive_duration_ps":output_final_desc["positive_support_ps"],"FINAL_JSL8_negative_duration_ps":output_final_desc["negative_support_ps"],"CONTROL_JSL8_peak_positive":output_control_desc["positive_peak"],"CONTROL_JSL8_peak_negative":output_control_desc["negative_peak"],"CONTROL_JSL8_signed_area":output_control_desc["signed_area"]/2.067833848e-15,"CONTROL_JSL8_absolute_area":output_control_desc["absolute_area"]/2.067833848e-15,"CONTROL_JSL8_RMS":output_control_desc["rms"],"CONTROL_JSL8_positive_duration_ps":output_control_desc["positive_support_ps"],"CONTROL_JSL8_negative_duration_ps":output_control_desc["negative_support_ps"],"CONTROL90_JSL8_peak_positive":max(0.0,output_control90["max"] or 0.0),"peak_discrimination_ratio":(output_final_desc["positive_peak"]/max(1e-30,output_control_desc["positive_peak"])),"area_discrimination_ratio":(abs(output_final_desc["signed_area"])/max(1e-30,abs(output_control_desc["signed_area"]))),"JM1_WRITE0_net":state["write0_50_61"]["JM1"],"JM1_WRITE1_net":state["write1_90_101"]["JM1"],"JM1_PRE_READ":state["settle_101_110"]["JM1"],"JM1_TAIL":state["tail_150_200"]["JM1"],"JM2_WRITE0_net":state["write0_50_61"]["JM2"],"JM2_WRITE1_net":state["write1_90_101"]["JM2"],"JM2_PRE_READ":state["settle_101_110"]["JM2"],"JM2_TAIL":state["tail_150_200"]["JM2"],"mechanical_progression_label":js["JS1"]["mechanical_label"],"JS1_mechanical_label":js["JS1"]["mechanical_label"],"JS2_mechanical_label":js["JS2"]["mechanical_label"],"JS1_activity":js["JS1"].get("first_major_voltage_activity"),"JS2_activity":js["JS2"].get("first_major_voltage_activity")}


def write_batch_review(batch_root: Path, sweep: dict[str, Any], rows: list[dict[str, Any]], reused: list[dict[str, Any]], new_cases: list[str], failed: list[dict[str, Any]]) -> None:
    def chart(title: str, keys: list[tuple[str,str]]) -> str:
        return render_svg_chart(rows, "JS1_AREA", keys, title)
    body=["<!doctype html><html><head><meta charset='utf-8'><title>"+html.escape(batch_root.name)+"</title><style>body{font-family:Arial;background:#111;color:#eee;margin:20px}a{color:#8ecbff}section{border:1px solid #444;padding:12px;margin:16px 0}table{border-collapse:collapse;width:100%;font-size:11px}td,th{border:1px solid #555;padding:4px}th{background:#292929}</style></head><body>",f"<h1>{html.escape(batch_root.name)}</h1><p>Sweep key: <code>{html.escape(sweep['key'])}</code> · values: {', '.join(html.escape(v) for v in sweep['values'])} · mode: {html.escape(sweep['mode'])} · mask: N4/1111</p>",f"<p>Reused points: {len(reused)} · new physical solves: {len(new_cases)} · failed points: {len(failed)}</p>"]
    body += ["<section><h2>Plot A — phase progression</h2>",chart("JS1/JS2 phase progression; turns are navigation only",[("JS1_read_net","JS1 110→121"),("JS1_read_recovery_net","JS1 110→130"),("JS2_read_net","JS2 110→121"),("JS2_read_recovery_net","JS2 110→130")]),"</section>","<section><h2>Plot B — crossing timing relative to final read start [ps]</h2>",chart("Crossing timing",[("JS1_t_minus_0p5","JS1 -0.5"),("JS1_t_minus_1","JS1 -1"),("JS2_t_minus_0p5","JS2 -0.5"),("JS2_t_minus_1","JS2 -1")]),"</section>","<section><h2>Plot C — final output</h2>",chart("Final JSL8 output",[("FINAL_JSL8_peak_positive","peak positive"),("FINAL_JSL8_signed_area","signed area"),("FINAL_JSL8_absolute_area","absolute area")]),"</section>","<section><h2>Plot D/E — control feedthrough and discrimination</h2>",chart("Control positive/negative and discrimination",[("CONTROL_JSL8_peak_positive","control +peak"),("CONTROL_JSL8_peak_negative","control -peak"),("peak_discrimination_ratio","final/control peak"),("area_discrimination_ratio","final/control area")]),"</section>","<section><h2>Plot F/G — LS3 and S-loop sanity</h2>",chart("LS3 / S-loop descriptors",[("LS3_positive_peak","LS3 +peak"),("LS3_negative_trough","LS3 trough"),("JM1_WRITE0_net","JM1 WRITE0"),("JM1_WRITE1_net","JM1 WRITE1")]),"</section>"]
    point_rows=[]
    for r in rows:
        links="—"
        if r.get("case_review_path"):
            links=f"<a href='{html.escape(r['case_review_path'])}'>review</a> · <a href='{html.escape(r['raw_path'])}'>raw</a> · <a href='{html.escape(r['config_path'])}'>config</a>"
        point_rows.append(f"<tr><td>{r['JS1_AREA']}</td><td>{html.escape(str(r['source_type']))}</td><td>{html.escape(str(r['raw_qa_status']))}</td><td>{r['JS1_read_net']}</td><td>{r['JS1_read_recovery_net']}</td><td>{html.escape(str(r['mechanical_progression_label']))}</td><td>{r['FINAL_JSL8_peak_positive']}</td><td>{r['CONTROL_JSL8_peak_positive']}</td><td>{links}</td></tr>")
    body.append("<section><h2>Point table</h2><table><tr><th>JS1_AREA</th><th>source</th><th>raw QA</th><th>JS1 read</th><th>JS1 read+recovery</th><th>JS1 label</th><th>final peak</th><th>control peak</th><th>links</th></tr>"+"".join(point_rows)+"</table></section><p>No scientific interpretation performed. Phase turns are navigation only, not formal SFQ counts.</p></body></html>")
    (batch_root/"BATCH_REVIEW.html").write_text("\n".join(body),encoding="utf-8")


def execute_sweep(values: dict[str, str], reference: dict[str, str], args: Any) -> int:
    sweep, points, _ = sweep_setup(values, reference)
    existing_batches = list((SERIES / "batches").iterdir()) if (SERIES / "batches").is_dir() else []
    batch_id = f"B{max([int(m.group(1)) for p in existing_batches if (m:=re.match(r'^B(\d{{3}})_', p.name))] or [0])+1:03d}"
    batch_name=f"{batch_id}_{sweep['name']}"
    if args.dry_run:
        print("BATCH PREVIEW\n\nNAME\n"+sweep["name"]+"\n\nSWEEP\n"+sweep["key"]+"\n\nVALUES\n"+"\n".join(sweep["values"])+"\n\nFIXED CIRCUIT\n"+"\n".join(f"{k} = {values[k]}" for k in sorted(platform.CIRCUIT_KEYS-{sweep['key']}))+"\n\nMODE\n"+sweep["mode"].upper()+"\n\nMASKS\nN4 / 1111\n\nLOGICAL POINTS\n"+str(len(points))+"\n\nREUSE CANDIDATES")
        for point in points:
            reuse=point["reuse"]; print(f"{point['value']} -> {reuse.get('case_id', 'NONE')} : {reuse['status']}" if reuse.get('case_id') else f"{point['value']} -> {reuse['status']}")
        new=[p for p in points if p['reuse']['status']!='REUSE']
        print("\nNEW PHYSICAL SOLVES\n"+"\n".join(p['value'] for p in new)+f"\n\nExpected new physical solve count: {len(new)}\n\nSTIMULUS CHANGES\nnone\n\nNo solve executed.")
        return 0
    batch_root=SERIES/'batches'/batch_name; batch_root.mkdir(parents=True,exist_ok=False)
    manifest={"schema":"bvm-rloop-sweep-batch-v1","batch_id":batch_name,"sweep_key":sweep['key'],"values":sweep['values'],"mode":sweep['mode'],"target_mask":MASK,"fixed_parameters":{k:values[k] for k in sorted(platform.CIRCUIT_KEYS|platform.STIMULUS_KEYS) if k!=sweep['key']},"reuse_enabled":sweep['reuse_enabled'],"physical_solve_count_authorized":sum(1 for p in points if p['reuse']['status']!='REUSE'),"points":[]}
    write_json(batch_root/'BATCH_MANIFEST.json',manifest)
    point_records=[]; new_cases=[]; failed=[]
    for point in points:
        reuse=point['reuse']; record={"value":point['value'],"source_type":reuse.get('source_type'),"source_case":reuse.get('case_id'),"physical_solve_new":False,"reuse_rejected_reason":reuse.get('reasons',[])}
        if reuse['status']=='REUSE':
            record['case_path']=reuse['case_id']; record['run_id']=reuse['run_id']; record['raw_sha256']=reuse['raw_sha256']; record['raw_qa_status']='PASS'; record['grid_status']=reuse.get('grid_status')
        else:
            point_values=dict(values); point_values[sweep['key']]=point['value']; point_values['NAME']=f"{sweep['name']}_{sweep['key'].lower()}_{point['value'].replace('.','p')}"; point_values['MASKS']=MASK; point_values['SWEEP_ENABLED']='no'; point_values['SWEEP_KEY']='NONE'; point_values['SWEEP_VALUES']=''; point_values['SWEEP_REUSE_EXISTING']='yes'
            with tempfile.NamedTemporaryFile(prefix='bvm_sweep_',suffix='.env',delete=False,dir='/tmp',mode='w',encoding='utf-8') as handle:
                temp_path=Path(handle.name); handle.write("\n".join(f"{k}={v}" for k,v in point_values.items())+"\n")
            before={p.name for p in (SERIES/'runs').iterdir() if p.is_dir()}
            completed=subprocess.run([sys.executable,str(SERIES/'scripts'/'try_candidate.py'),'--config',str(temp_path)],cwd=REPO,text=True,capture_output=True,check=False); temp_path.unlink(missing_ok=True)
            after={p.name for p in (SERIES/'runs').iterdir() if p.is_dir()}; created=sorted(after-before)
            if completed.returncode!=0 or not created:
                failed.append({"value":point['value'],"reason":completed.stderr[-2000:]}); record.update({"source_type":"NEW_FAILED","physical_solve_new":True,"status":"FAILED"}); point_records.append(record); continue
            case_name=created[-1]; new_cases.append(case_name); record.update({"source_type":"NEW_PHYSICAL","source_case":case_name,"case_path":case_name,"run_id":"PASSIVE_N4_1111","physical_solve_new":True})
            case_root=SERIES/'runs'/case_name; qa=json.loads((case_root/'qa'/'raw_qa.json').read_text()); row=qa['rows'][0]; record.update({"raw_sha256":row.get('sha256'),"raw_qa_status":row.get('status'),"grid_status":row.get('grid_status')})
        point_records.append(record)
    metric_rows=[]
    for record in point_records:
        if record.get('raw_qa_status')!='PASS':
            continue
        params=dict(values); params[sweep['key']]=str(record['value']); params['MASKS']=[MASK]; params=platform.validate(params,reference)
        metric_rows.append({"point":record,"params":params})
    flat=[]
    for item in metric_rows:
        row=load_point_metrics({**item['point'],"params":item['params']},sweep)
        case_name=item['point'].get('case_path')
        row['case_review_path']=f"../../plots/{case_name}/review.html" if case_name else None
        row['raw_path']=f"../../runs/{case_name}/cases/PASSIVE_N4_1111/raw.csv" if case_name else None
        row['config_path']=f"../../runs/{case_name}/config_snapshot.env" if case_name else None
        flat.append(row)
    fields=sorted({key for row in flat for key in row})
    with (batch_root/'BATCH_SUMMARY.csv').open('w',newline='',encoding='utf-8') as stream:
        writer=csv.DictWriter(stream,fieldnames=fields); writer.writeheader(); writer.writerows(flat)
    write_batch_review(batch_root,sweep,flat,[r for r in point_records if r.get('source_type')=='REUSED_EXISTING'],new_cases,failed)
    qa={"schema":"bvm-rloop-sweep-batch-qa-v1","status":"PASS" if len(flat)==len(points) and not failed and all(r.get('raw_qa_status')=='PASS' for r in point_records) else "FAIL","logical_points":len(points),"reused_points":sum(r.get('source_type')=='REUSED_EXISTING' for r in point_records),"new_physical_solve_count":len(new_cases),"failed_points":failed,"raw_hashes_rechecked":all(r.get('raw_qa_status')=='PASS' for r in point_records)}
    write_json(batch_root/'BATCH_QA.json',qa); write_json(batch_root/'BATCH_MANIFEST.json',{**manifest,"points":point_records,"qa":qa})
    (SERIES/'LATEST_BATCH_REVIEW.html').write_text(f"<!doctype html><html><head><meta http-equiv='refresh' content='0; url=batches/{batch_name}/BATCH_REVIEW.html'></head><body><a href='batches/{batch_name}/BATCH_REVIEW.html'>{batch_name}</a></body></html>\n",encoding='utf-8')
    print(json.dumps({"status":qa['status'],"batch_id":batch_name,"logical_points":len(points),"reused_points":qa['reused_points'],"new_physical_solve_count":len(new_cases),"failed_points":len(failed)},ensure_ascii=False,indent=2))
    return 0 if qa['status']=='PASS' else 2
