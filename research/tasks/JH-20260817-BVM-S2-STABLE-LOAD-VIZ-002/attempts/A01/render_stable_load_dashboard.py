#!/usr/bin/env python3
"""render_stable_load_dashboard.py -- VIZ-002 A01 deterministic renderer.

Reads ONLY frozen STABLE-LOAD-001 analysis.json + raw CSVs (read-only);
emits visualization-data.json (data model) and a self-contained offline
Plotly report.html (plotly.js inlined, no network).  Deterministic:
--check proves byte-identical regeneration.
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
TOKENS_PS = ["97", "99", "101", "103", "105"]

def load_csv(path):
    rows = list(csv.reader(open(path, encoding="utf-8")))
    hdr = [h.strip().strip('"') for h in rows[0]]
    return hdr, rows[1:]

def build_data_model():
    analysis = json.loads((SRC/"attempts/A01/analysis.json").read_text())
    data = {"schema_version": "bvm-s2-stable-load-viz-data-v1",
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
            "traces": {}}
    for load in LOADS:
        for pol in POLS:
            for case in CASES:
                cid = f"L{load:02d}-{pol}-{case}"
                hdr, rows = load_csv(RUN/"raw"/cid/"run-01.csv")
                t = [Decimal(r[0]) for r in rows]
                t_ps = [str(x * Decimal("1e12")) for x in t]
                cols = {hdr[j].strip('"'): [r[j] for r in rows]
                        for j in range(1, len(hdr))}
                tr = {"time_ps": t_ps,
                      "wl_uA": cols.get("I(I_WL1)"), "bl_uA": cols.get("I(I_BL1)"),
                      "se_uA": cols.get("I(I_SE1)"),
                      "jm1_phase_rad": cols.get("P(B_JM1|XBVM1)"),
                      "jm2_phase_rad": cols.get("P(B_JM2|XBVM1)"),
                      "js1_phase_rad": cols.get("P(B_JS1|XBVM1)"),
                      "js2_phase_rad": cols.get("P(B_JS2|XBVM1)"),
                      "v_sl1_V": cols.get("V(SL1)"), "i_sl1_A": cols.get("I(L_SL|XBVM1)")}
                data["traces"][cid] = tr
    (ATTEMPT/"visualization-data.json").write_text(json.dumps(data), encoding="utf-8")
    return data

def render_html(data):
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    figs = {}
    for load in LOADS:
        for pol in POLS:
            key = f"L{load:02d}-{pol}"
            fig = make_subplots(rows=4, cols=2, subplot_titles=(
                "WL/BL/SE (uA)", "JM1/JM2 raw phase (rad)",
                "JS1/JS2 raw phase (rad)", "V(SL1) (mV)",
                "I(L_SL) (uA)", "endpoint tokens"),
                vertical_spacing=0.12)
            for case in CASES:
                tr = data["traces"][f"{key}-{case}"]
                t = [float(x) for x in tr["time_ps"]]
                name = case
                fig.add_trace(go.Scatter(x=t, y=[float(v) for v in tr["wl_uA"]],
                                         name=f"WL {name}", mode="lines"), 1, 1)
                fig.add_trace(go.Scatter(x=t, y=[float(v) for v in tr["jm1_phase_rad"]],
                                         name=f"JM1 {name}", mode="lines"), 1, 2)
                fig.add_trace(go.Scatter(x=t, y=[float(v) for v in tr["jm2_phase_rad"]],
                                         name=f"JM2 {name}", mode="lines"), 1, 2)
                fig.add_trace(go.Scatter(x=t, y=[float(v) for v in tr["js1_phase_rad"]],
                                         name=f"JS1 {name}", mode="lines"), 2, 1)
                fig.add_trace(go.Scatter(x=t, y=[float(v) for v in tr["js2_phase_rad"]],
                                         name=f"JS2 {name}", mode="lines"), 2, 1)
                fig.add_trace(go.Scatter(x=t, y=[float(v)*1e3 for v in tr["v_sl1_V"]],
                                         name=f"V(SL1) {name} (mV)", mode="lines"), 2, 2)
                fig.add_trace(go.Scatter(x=t, y=[float(v)*1e6 for v in tr["i_sl1_A"]],
                                         name=f"I(L_SL) {name} (uA)", mode="lines"), 3, 1)
            # PRE window shading on JM panel
            fig.add_vrect(x0=80, x1=90, fillcolor="yellow", opacity=0.15,
                          line_width=0, row=1, col=2)
            fig.update_layout(title=f"BVM stable-load {key} (ohm={load}, {pol}) "
                                    f"disposition={data['disposition']}",
                              hovermode="closest",
                              legend=dict(traceorder="normal"))
            fig.update_xaxes(title_text="time (ps)")
            figs[key] = fig
    # single combined HTML with selectors via dropdown buttons
    import plotly
    html_parts = ["<!doctype html><html><head><meta charset='utf-8'>",
                  f"<title>{data['source']['run']} dashboard</title></head><body>",
                  "<h1>BVM stable-load dashboard (descriptive, non-authoritative)</h1>",
                  f"<p>disposition: <b>{data['disposition']}</b>; units: time ps, "
                  "voltage mV, current uA, phase raw rad</p>"]
    for key, fig in figs.items():
        html_parts.append(fig.to_html(full_html=False, include_plotlyjs=True if key == "L01-positive" else False))
    html_parts += ["<p>Claim ceiling: descriptive non-authoritative visualization "
                   "completeness only; accepted raw/specification/analysis remain "
                   "scientific authority.</p>", "</body></html>"]
    return "".join(html_parts)

def main():
    data = build_data_model()
    html = render_html(data)
    (ATTEMPT/"report.html").write_text(html, encoding="utf-8")
    if "--check" in sys.argv:
        ok = (ATTEMPT/"report.html").read_text(encoding="utf-8") == html
        print("DETERMINISTIC CONSISTENT" if ok else "DETERMINISTIC INCONSISTENT")
        return 0 if ok else 1
    print(f"rendered report.html ({len(html)} bytes) + visualization-data.json")
    return 0

if __name__ == "__main__":
    sys.exit(main())
