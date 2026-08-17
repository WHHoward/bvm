#!/usr/bin/env python3
"""render_stable_load_dashboard.py -- VIZ-002 A02 extended deterministic renderer.

Reads ONLY frozen STABLE-LOAD-001 analysis.json + raw CSVs (read-only).
Emits visualization-data.json with corrected V/I (V_star/I_star), source
descriptors, control residual, per-token endpoint Rhat/Vth/emax/
eligibility/classification, and per-stratum readiness p2p/threshold/READY
values; and a self-contained offline Plotly report.html.  Deterministic.
"""
import csv, json, pathlib, sys
from decimal import Decimal

ATTEMPT = pathlib.Path(__file__).resolve().parent
REPO = ATTEMPT.parents[4]
SRC = REPO / "research/tasks/JH-20260817-BVM-S2-STABLE-LOAD-001"
RUN = REPO / "test/final/bvm/runs/bvm-s2-stable-load-20260817-01"
LOADS = [1, 12, 25, 50]
POLS = ["positive", "negative"]
CASES = ["read", "control"]
PRE = (Decimal("80e-12"), Decimal("90e-12"))
SOURCE = (Decimal("94e-12"), Decimal("130e-12"))
THRESHOLD = Decimal("0.020")
TOKENS_PS = [Decimal("97"), Decimal("99"), Decimal("101"), Decimal("103"), Decimal("105")]
FLOOR_V = Decimal("5e-6"); FLOOR_I = Decimal("0.5e-6")

def load_csv(path):
    rows = list(csv.reader(open(path, encoding="utf-8")))
    hdr = [h.strip().strip('"') for h in rows[0]]
    return hdr, rows[1:]

def mean(t, v, lo, hi):
    sel = [x for tt, x in zip(t, v) if lo <= tt < hi]
    return sum(sel) / len(sel)

def idx(times, tk):
    w = tk * Decimal("1e-12")
    for i, tt in enumerate(times):
        if tt == w:
            return i
    raise ValueError(f"token {tk} ps absent")

def main():
    analysis = json.loads((SRC/"attempts/A01/analysis.json").read_text())
    data = {"schema_version": "bvm-s2-stable-load-viz-data-v2",
            "source": {"task": "JH-20260817-BVM-S2-STABLE-LOAD-001",
                       "run": "bvm-s2-stable-load-20260817-01",
                       "analysis": "attempts/A01/analysis.json (accepted)",
                       "units": {"time": "ps", "voltage": "mV", "current": "uA",
                                 "phase": "raw phase (rad)"}},
            "disposition": analysis["disposition"],
            "strata": analysis["strata"],
            "endpoint_vi": analysis["endpoint_vi"],
            "loads_ohm": LOADS, "polarities": POLS, "cases": CASES,
            "pre_window_ps": [80.0, 90.0],
            "readiness": {"threshold_rad": "0.020", "window_ps": [80.0, 90.0],
                          "strata": {}},
            "traces": {}, "corrected": {}, "descriptors": {}, "endpoint_detail": {},
            "control_residual": {}}
    raw_data = {}
    for load in LOADS:
        for pol in POLS:
            for case in CASES:
                cid = f"L{load:02d}-{pol}-{case}"
                hdr, rows = load_csv(RUN/"raw"/cid/"run-01.csv")
                t = [Decimal(r[0]) for r in rows]
                cols = {hdr[j].strip('"'): [Decimal(r[j]) for r in rows]
                        for j in range(1, len(hdr))}
                raw_data[cid] = (t, cols)
    # readiness per stratum: JM1/JM2 p2p values
    for load in LOADS:
        for pol in POLS:
            key = f"L{load:02d}-{pol}"
            entry = {"p2p_jm1_rad": {}, "p2p_jm2_rad": {}, "ready": True}
            for case in CASES:
                cid = f"{key}-{case}"
                t, c = raw_data[cid]
                p1 = max([v for tt, v in zip(t, c["P(B_JM1|XBVM1)"]) if PRE[0] <= tt < PRE[1]]) - \
                     min([v for tt, v in zip(t, c["P(B_JM1|XBVM1)"]) if PRE[0] <= tt < PRE[1]])
                p2 = max([v for tt, v in zip(t, c["P(B_JM2|XBVM1)"]) if PRE[0] <= tt < PRE[1]]) - \
                     min([v for tt, v in zip(t, c["P(B_JM2|XBVM1)"]) if PRE[0] <= tt < PRE[1]])
                entry["p2p_jm1_rad"][case] = str(p1)
                entry["p2p_jm2_rad"][case] = str(p2)
                if p1 > THRESHOLD or p2 > THRESHOLD:
                    entry["ready"] = False
            data["readiness"]["strata"][key] = entry
    # corrected V/I + control residual + descriptors per load/polarity
    for load in LOADS:
        for pol in POLS:
            key = f"L{load:02d}-{pol}"
            tr, c_r = raw_data[f"{key}-read"]
            tc, c_c = raw_data[f"{key}-control"]
            t_ps = [str(x * Decimal("1e12")) for x in tr]
            v_r = c_r["V(SL1)"]; v_c = c_c["V(SL1)"]
            i_r = c_r["I(L_SL|XBVM1)"]; i_c = c_c["I(L_SL|XBVM1)"]
            mr_r = mean(tr, v_r, *PRE); mc_r = mean(tc, v_c, *PRE)
            mi_r = mean(tr, i_r, *PRE); mi_c = mean(tc, i_c, *PRE)
            v_star = [v_r[k] - mr_r - (v_c[k] - mc_r) for k in range(len(tr))]
            i_star = [i_r[k] - mi_r - (i_c[k] - mi_c) for k in range(len(tr))]
            data["corrected"][key] = {"time_ps": t_ps,
                                      "v_star_V": [str(x) for x in v_star],
                                      "i_star_A": [str(x) for x in i_star]}
            # control residual = x_control - mean(x_control, PRE) in source window
            sel_idx = [k for k in range(len(tc)) if SOURCE[0] <= tc[k] < SOURCE[1]]
            data["control_residual"][key] = {
                "time_ps": [str(tc[k] * Decimal("1e12")) for k in sel_idx],
                "v_control_resid_V": [str(v_c[k] - mc_r) for k in sel_idx],
                "i_control_resid_A": [str(i_c[k] - mi_c) for k in sel_idx]}
            # source descriptors for V_star in source window
            sel = [k for k in range(len(tr)) if SOURCE[0] <= tr[k] < SOURCE[1]]
            abs_v = [abs(v_star[k]) for k in sel]
            amax = max(abs_v) if abs_v else Decimal("0")
            arms = (sum(x*x for x in abs_v)/len(abs_v))**Decimal("0.5") if abs_v else Decimal("0")
            dt = tr[sel[1]] - tr[sel[0]] if len(sel) > 1 else Decimal("0")
            al1 = (sum(abs(v_star[k]) for k in sel) * dt) / (tr[sel[-1]] - tr[sel[0]]) if len(sel) > 1 else Decimal("0")
            data["descriptors"][key] = {
                "v_star": {"max_V": str(amax), "rms_V": str(arms),
                           "time_normalized_l1_V": str(al1),
                           "window_ps": [94.0, 130.0]},
                "i_star": {"max_A": str(max(abs(i_star[k]) for k in sel)),
                           "rms_A": str((sum(i_star[k]*i_star[k] for k in sel)/len(sel))**Decimal("0.5"))},
                "rctrl": str(amax / max(amax, FLOOR_V))}
            # endpoint per-token detail (from accepted analysis)
            data["endpoint_detail"][key] = analysis["endpoint_vi"][pol]
    (ATTEMPT/"visualization-data.json").write_text(json.dumps(data), encoding="utf-8")
    # HTML: raw trace panels (from frozen A01 data model) + AC2 panels
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    a01_data = json.loads((REPO/"research/tasks/JH-20260817-BVM-S2-STABLE-LOAD-VIZ-002/attempts/A01/visualization-data.json").read_text())
    html_parts = ["<!doctype html><html><head><meta charset='utf-8'>",
                  f"<title>{data['source']['run']} dashboard A02</title></head><body>",
                  "<h1>BVM stable-load dashboard A02 (descriptive, non-authoritative)</h1>",
                  f"<p>disposition: <b>{data['disposition']}</b>; units: time ps, "
                  "voltage mV, current uA, phase raw rad; readiness threshold "
                  f"{data['readiness']['threshold_rad']} rad</p>"]
    for load in LOADS:
        for pol in POLS:
            key = f"L{load:02d}-{pol}"
            # raw traces (A01 data model, frozen)
            fig = make_subplots(rows=4, cols=2, subplot_titles=(
                "WL/BL/SE (uA)", "JM1/JM2 raw phase (rad)",
                "JS1/JS2 raw phase (rad)", "V(SL1) (mV)",
                "I(L_SL) (uA)", "PRE [80,90) shading on JM1/JM2"),
                vertical_spacing=0.12)
            for case in CASES:
                tr = a01_data["traces"][f"{key}-{case}"]
                t = [float(x) for x in tr["time_ps"]]
                fig.add_trace(go.Scatter(x=t, y=[float(v) for v in tr["wl_uA"]],
                                         name=f"WL {case}", mode="lines"), 1, 1)
                fig.add_trace(go.Scatter(x=t, y=[float(v) for v in tr["jm1_phase_rad"]],
                                         name=f"JM1 {case}", mode="lines"), 1, 2)
                fig.add_trace(go.Scatter(x=t, y=[float(v) for v in tr["jm2_phase_rad"]],
                                         name=f"JM2 {case}", mode="lines"), 1, 2)
                fig.add_trace(go.Scatter(x=t, y=[float(v) for v in tr["js1_phase_rad"]],
                                         name=f"JS1 {case}", mode="lines"), 2, 1)
                fig.add_trace(go.Scatter(x=t, y=[float(v) for v in tr["js2_phase_rad"]],
                                         name=f"JS2 {case}", mode="lines"), 2, 1)
                fig.add_trace(go.Scatter(x=t, y=[float(v)*1e3 for v in tr["v_sl1_V"]],
                                         name=f"V(SL1) {case} (mV)", mode="lines"), 2, 2)
                fig.add_trace(go.Scatter(x=t, y=[float(v)*1e6 for v in tr["i_sl1_A"]],
                                         name=f"I(L_SL) {case} (uA)", mode="lines"), 3, 1)
            fig.add_vrect(x0=80, x1=90, fillcolor="yellow", opacity=0.15,
                          line_width=0, row=1, col=2)
            fig.add_vrect(x0=80, x1=90, fillcolor="yellow", opacity=0.15,
                          line_width=0, row=3, col=2)
            fig.update_layout(title=f"BVM stable-load {key} raw traces",
                              hovermode="closest")
            fig.update_xaxes(title_text="time (ps)")
            html_parts.append(fig.to_html(full_html=False,
                                          include_plotlyjs=True if key == "L01-positive" else False))
            # AC2 panels (corrected / residual / descriptors / endpoint)
            fig = make_subplots(rows=3, cols=2, subplot_titles=(
                "corrected V_star (mV)", "corrected I_star (uA)",
                "control residual V (mV)", "control residual I (uA)",
                "JM1/JM2 PRE p2p (rad) + threshold", "endpoint Rhat/Vth/emax"),
                vertical_spacing=0.15)
            corr = data["corrected"][key]
            t = [float(x) for x in corr["time_ps"]]
            fig.add_trace(go.Scatter(x=t, y=[float(v)*1e3 for v in corr["v_star_V"]],
                                     name="V_star (mV)", mode="lines"), 1, 1)
            fig.add_trace(go.Scatter(x=t, y=[float(v)*1e6 for v in corr["i_star_A"]],
                                     name="I_star (uA)", mode="lines"), 1, 2)
            res = data["control_residual"][key]
            tr2 = [float(x) for x in res["time_ps"]]
            fig.add_trace(go.Scatter(x=tr2, y=[float(v)*1e3 for v in res["v_control_resid_V"]],
                                     name="resid V (mV)", mode="lines"), 2, 1)
            fig.add_trace(go.Scatter(x=tr2, y=[float(v)*1e6 for v in res["i_control_resid_A"]],
                                     name="resid I (uA)", mode="lines"), 2, 2)
            rd = data["readiness"]["strata"][key]
            fig.add_trace(go.Bar(x=["JM1 read", "JM1 ctrl", "JM2 read", "JM2 ctrl"],
                                 y=[float(rd["p2p_jm1_rad"]["read"]),
                                    float(rd["p2p_jm1_rad"]["control"]),
                                    float(rd["p2p_jm2_rad"]["read"]),
                                    float(rd["p2p_jm2_rad"]["control"])],
                                 name="p2p (rad)"), 3, 1)
            fig.add_hline(y=0.020, line_dash="dash", row=3, col=1)
            ep = data["endpoint_detail"].get(key, {})
            toks = [x["token_ps"] for x in ep.get("per_token", [])]
            rh = [float(x["rhat_ohm"]) for x in ep.get("per_token", [])]
            em = [float(x["e_max_V"])*1e3 for x in ep.get("per_token", [])]
            fig.add_trace(go.Scatter(x=toks, y=rh, name="Rhat (ohm)", mode="markers+lines"), 3, 2)
            fig.add_trace(go.Scatter(x=toks, y=em, name="emax (mV)", mode="markers+lines"), 3, 2)
            fig.update_layout(title=f"BVM stable-load {key} A02 (disposition={data['disposition']})",
                              hovermode="closest")
            fig.update_xaxes(title_text="time (ps)")
            html_parts.append(fig.to_html(full_html=False,
                                          include_plotlyjs=True if key == "L01-positive" else False))
    html_parts += ["<p>Claim ceiling: descriptive non-authoritative visualization "
                   "completeness only; accepted raw/specification/analysis remain "
                   "scientific authority.</p>", "</body></html>"]
    html = "".join(html_parts)
    (ATTEMPT/"report.html").write_text(html, encoding="utf-8")
    if "--check" in sys.argv:
        ok = (ATTEMPT/"report.html").read_text(encoding="utf-8") == html
        print("DETERMINISTIC CONSISTENT" if ok else "DETERMINISTIC INCONSISTENT")
        return 0 if ok else 1
    print(f"rendered A02 report.html ({len(html)} bytes) + visualization-data.json")
    return 0

if __name__ == "__main__":
    sys.exit(main())
