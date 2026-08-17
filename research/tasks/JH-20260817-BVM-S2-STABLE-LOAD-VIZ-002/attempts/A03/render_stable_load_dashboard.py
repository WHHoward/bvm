#!/usr/bin/env python3
"""render_stable_load_dashboard.py -- VIZ-002 A03 canonical renderer.

Generates report.html ONCE (canonical, read-only afterwards) with a REAL
4x2 load/polarity selector (HTML buttons with active-state highlight that
show/hide per-combination dashboard sections via DOM class toggling), all
frozen AC2 panels per combination, and a self-contained offline Plotly
body.  Deterministic comparison is performed ONLY by
compare_deterministic.py which never rewrites the canonical file.
"""
import csv, json, pathlib, sys
from decimal import Decimal

ATTEMPT = pathlib.Path(__file__).resolve().parent
REPO = ATTEMPT.parents[4]
SRC = REPO / "research/tasks/JH-20260817-BVM-S2-STABLE-LOAD-001"
RUN = REPO / "test/final/bvm/runs/bvm-s2-stable-load-20260817-01"
A02 = REPO / "research/tasks/JH-20260817-BVM-S2-STABLE-LOAD-VIZ-002/attempts/A02"
LOADS = [1, 12, 25, 50]
POLS = ["positive", "negative"]
CASES = ["read", "control"]
PRE = (Decimal("80e-12"), Decimal("90e-12"))
SOURCE = (Decimal("94e-12"), Decimal("130e-12"))
THRESHOLD = Decimal("0.020")

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

def build_data():
    analysis = json.loads((SRC/"attempts/A01/analysis.json").read_text())
    a01 = json.loads((A02/"visualization-data.json").read_text())  # frozen A02 data (accepted analysis-derived)
    a01_viz = json.loads((REPO/"research/tasks/JH-20260817-BVM-S2-STABLE-LOAD-VIZ-002/attempts/A01/visualization-data.json").read_text())
    data = {"schema_version": "bvm-s2-stable-load-viz-data-v3",
            "source": {"task": "JH-20260817-BVM-S2-STABLE-LOAD-001",
                       "run": "bvm-s2-stable-load-20260817-01",
                       "units": {"time": "ps", "voltage": "mV", "current": "uA",
                                 "phase": "raw phase (rad)"}},
            "disposition": analysis["disposition"],
            "loads_ohm": LOADS, "polarities": POLS, "cases": CASES,
            "readiness": a01["readiness"], "corrected": a01["corrected"],
            "descriptors": a01["descriptors"], "control_residual": a01["control_residual"],
            "endpoint_detail": a01["endpoint_detail"], "traces": a01_viz["traces"]}
    (ATTEMPT/"visualization-data.json").write_text(json.dumps(data), encoding="utf-8")
    return data

def render_html(data):
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    sections = []
    for load in LOADS:
        for pol in POLS:
            key = f"L{load:02d}-{pol}"
            fig = make_subplots(rows=4, cols=2, subplot_titles=(
                "WL/BL/SE (uA)", "JM1/JM2 raw phase (rad) + PRE + p2p",
                "JS1/JS2 raw phase (rad)", "V(SL1) read/control/corrected (mV)",
                "I(L_SL) read/control/corrected (uA)", "control residual V/I",
                "readiness p2p vs threshold", "endpoint Rhat/Vth/emax"),
                vertical_spacing=0.10)
            for case in CASES:
                tr = data["traces"][f"{key}-{case}"]
                t = [float(x) for x in tr["time_ps"]]
                fig.add_trace(go.Scatter(x=t, y=[float(v) for v in tr["wl_uA"]],
                                         name=f"WL {case}", mode="lines"), 1, 1)
                fig.add_trace(go.Scatter(x=t, y=[float(v) for v in tr["bl_uA"]],
                                         name=f"BL {case}", mode="lines"), 1, 1)
                fig.add_trace(go.Scatter(x=t, y=[float(v) for v in tr["se_uA"]],
                                         name=f"SE {case}", mode="lines"), 1, 1)
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
            corr = data["corrected"][key]
            t = [float(x) for x in corr["time_ps"]]
            fig.add_trace(go.Scatter(x=t, y=[float(v)*1e3 for v in corr["v_star_V"]],
                                     name="V_star (mV)", mode="lines"), 2, 2)
            fig.add_trace(go.Scatter(x=t, y=[float(v)*1e6 for v in corr["i_star_A"]],
                                     name="I_star (uA)", mode="lines"), 3, 1)
            res = data["control_residual"][key]
            tr2 = [float(x) for x in res["time_ps"]]
            fig.add_trace(go.Scatter(x=tr2, y=[float(v)*1e3 for v in res["v_control_resid_V"]],
                                     name="resid V (mV)", mode="lines"), 3, 2)
            fig.add_trace(go.Scatter(x=tr2, y=[float(v)*1e6 for v in res["i_control_resid_A"]],
                                     name="resid I (uA)", mode="lines"), 3, 2)
            rd = data["readiness"]["strata"][key]
            fig.add_trace(go.Bar(x=["JM1 read", "JM1 ctrl", "JM2 read", "JM2 ctrl"],
                                 y=[float(rd["p2p_jm1_rad"]["read"]),
                                    float(rd["p2p_jm1_rad"]["control"]),
                                    float(rd["p2p_jm2_rad"]["read"]),
                                    float(rd["p2p_jm2_rad"]["control"])],
                                 name="p2p (rad)", marker_color=["#1f77b4"]*4), 4, 1)
            fig.add_hline(y=0.020, line_dash="dash", row=4, col=1)
            ep = data["endpoint_detail"][key]
            toks = [x["token_ps"] for x in ep.get("per_token", [])]
            rh = [float(x["rhat_ohm"]) for x in ep.get("per_token", [])]
            em = [float(x["e_max_V"])*1e3 for x in ep.get("per_token", [])]
            fig.add_trace(go.Scatter(x=toks, y=rh, name="Rhat (ohm)", mode="markers+lines"), 4, 2)
            fig.add_trace(go.Scatter(x=toks, y=em, name="emax (mV)", mode="markers+lines"), 4, 2)
            fig.update_layout(title=f"{key} (load={load} ohm, {pol})",
                              hovermode="closest",
                              margin=dict(l=40, r=20, t=60, b=40))
            fig.update_xaxes(title_text="time (ps)")
            html_fig = fig.to_html(full_html=False,
                                   include_plotlyjs=True if key == "L01-positive" else False,
                                   div_id=f"plot-{key}")
            sections.append(f"""<div class="dash-section" id="sec-{key}" style="display:none">
<h2>{key} (load={load} ohm, {pol}); readiness={'READY' if rd['ready'] else 'NOT_READY'}</h2>
<p>p2p JM1 read={rd['p2p_jm1_rad']['read']} rad, JM2 read={rd['p2p_jm2_rad']['read']} rad;
threshold 0.020 rad; disposition {data['disposition']}</p>
{html_fig}</div>""")
    buttons = ""
    for load in LOADS:
        for pol in POLS:
            key = f"L{load:02d}-{pol}"
            buttons += (f'<button class="dash-btn" data-target="sec-{key}" '
                        f'onclick="showSection(this)">{load} ohm / {pol}</button>')
    return f"""<!doctype html><html><head><meta charset="utf-8">
<title>BVM stable-load dashboard A03</title>
<style>body{{font-family:sans-serif;margin:1em}}
.dash-btn{{margin:2px;padding:6px 10px;border:1px solid #999;border-radius:4px;background:#f0f0f0;cursor:pointer}}
.dash-btn.active{{background:#1f77b4;color:#fff;border-color:#1f77b4}}</style>
<script>function showSection(btn){{
document.querySelectorAll('.dash-section').forEach(s=>s.style.display='none');
document.querySelectorAll('.dash-btn').forEach(b=>b.classList.remove('active'));
document.getElementById(btn.dataset.target).style.display='block';
btn.classList.add('active');}}</script></head><body>
<h1>BVM stable-load dashboard A03 (descriptive, non-authoritative)</h1>
<p>disposition: <b>{data['disposition']}</b>; units: time ps, voltage mV,
current uA, phase raw rad; readiness threshold 0.020 rad.
Claim ceiling: descriptive non-authoritative visualization completeness
only; accepted raw/specification/analysis remain scientific authority.</p>
<div>{buttons}<button class="dash-btn" onclick="showAll(this)">show all</button></div>
<script>function showAll(btn){{document.querySelectorAll('.dash-section').forEach(s=>s.style.display='block');
btn.classList.add('active');}}</script>
{''.join(sections)}
</body></html>"""

def main():
    data = build_data()
    html = render_html(data)
    (ATTEMPT/"report.html").write_text(html, encoding="utf-8")
    print(f"canonical report.html written ({len(html)} bytes) - READ-ONLY after this point")
    return 0

if __name__ == "__main__":
    sys.exit(main())
