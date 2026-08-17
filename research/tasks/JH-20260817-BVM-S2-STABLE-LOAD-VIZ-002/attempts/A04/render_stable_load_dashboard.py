#!/usr/bin/env python3
"""render_stable_load_dashboard.py -- VIZ-002 A04 canonical renderer (FINAL).

Keeps A03 selectors + all waveform content; splits into independent wide
panels (max-width 1320px, 1440px-friendly); actual visible HTML tables for
Endpoint-VI (token/Rhat/Vth/emax/eligible/classification), source
descriptors V*/I*, control residual V/I, provenance/status.  Canonical
report.html generated once, read-only afterwards; deterministic
comparison side-effect-free (temp path, comparison log only).
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
THRESHOLD = Decimal("0.020")

def load_csv(path):
    rows = list(csv.reader(open(path, encoding="utf-8")))
    hdr = [h.strip().strip('"') for h in rows[0]]
    return hdr, rows[1:]

def build_data():
    analysis = json.loads((SRC/"attempts/A01/analysis.json").read_text())
    a02 = json.loads((A02/"visualization-data.json").read_text())
    a01 = json.loads((REPO/"research/tasks/JH-20260817-BVM-S2-STABLE-LOAD-VIZ-002/attempts/A01/visualization-data.json").read_text())
    data = {"schema_version": "bvm-s2-stable-load-viz-data-v4",
            "source": {"task": "JH-20260817-BVM-S2-STABLE-LOAD-001",
                       "run": "bvm-s2-stable-load-20260817-01",
                       "units": {"time": "ps", "voltage": "mV", "current": "uA",
                                 "phase": "raw phase (rad)"}},
            "disposition": analysis["disposition"],
            "loads_ohm": LOADS, "polarities": POLS, "cases": CASES,
            "readiness": a02["readiness"], "corrected": a02["corrected"],
            "descriptors": a02["descriptors"], "control_residual": a02["control_residual"],
            "endpoint_detail": a02["endpoint_detail"], "traces": a01["traces"]}
    (ATTEMPT/"visualization-data.json").write_text(json.dumps(data), encoding="utf-8")
    return data

def esc(v):
    return str(v).replace("&", "&amp;").replace("<", "&lt;")

def render_html(data):
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    sections = []
    for load in LOADS:
        for pol in POLS:
            key = f"L{load:02d}-{pol}"
            fig = make_subplots(rows=3, cols=2, subplot_titles=(
                "WL/BL/SE (uA)", "JM1/JM2 raw phase (rad) + PRE [80,90)",
                "JS1/JS2 raw phase (rad)", "V(SL1) read/control/corrected (mV)",
                "I(L_SL) read/control/corrected (uA)", "endpoint Rhat/emax"),
                vertical_spacing=0.14)
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
            ep = data["endpoint_detail"][key]
            toks = [x["token_ps"] for x in ep.get("per_token", [])]
            rh = [float(x["rhat_ohm"]) for x in ep.get("per_token", [])]
            em = [float(x["e_max_V"])*1e3 for x in ep.get("per_token", [])]
            fig.add_trace(go.Scatter(x=toks, y=rh, name="Rhat (ohm)", mode="markers+lines"), 3, 2)
            fig.add_trace(go.Scatter(x=toks, y=em, name="emax (mV)", mode="markers+lines"), 3, 2)
            fig.update_layout(title=f"{key} (load={load} ohm, {pol})",
                              hovermode="closest",
                              margin=dict(l=40, r=20, t=50, b=40),
                              height=900)
            fig.update_xaxes(title_text="time (ps)")
            html_fig = fig.to_html(full_html=False,
                                   include_plotlyjs=True if key == "L01-positive" else False,
                                   div_id=f"plot-{key}")
            # visible tables
            rows = "".join(
                f"<tr><td>{esc(x['token_ps'])}</td><td>{esc(x['rhat_ohm'])}</td>"
                f"<td>{esc(x['vth_V'])}</td><td>{esc(x['e_max_V'])}</td>"
                f"<td>{'eligible' if x['token_ps'] in ep.get('eligible_tokens', []) else 'ILL_CONDITIONED'}</td>"
                f"<td>{'COMPATIBLE' if x.get('compatible') else 'NOT_SUPPORTED'}</td></tr>"
                for x in ep.get("per_token", []))
            d = data["descriptors"][key]
            res = data["control_residual"][key]
            rvmax = max(abs(float(v)) for v in res["v_control_resid_V"])
            rimax = max(abs(float(v)) for v in res["i_control_resid_A"])
            rd = data["readiness"]["strata"][key]
            section = f"""<div class="dash-section" id="sec-{key}" style="display:none">
<h2>{key} (load={load} ohm, {pol}); readiness={'READY' if rd['ready'] else 'NOT_READY'}</h2>
<p>JM1 p2p read={esc(rd['p2p_jm1_rad']['read'])} rad, JM2 p2p read={esc(rd['p2p_jm2_rad']['read'])} rad; threshold 0.020 rad; disposition {esc(data['disposition'])}</p>
{html_fig}
<h3>Endpoint-VI (tokens 97-105 ps)</h3>
<table class="data" id="tbl-endpoint-{key}"><thead><tr><th>token (ps)</th><th>Rhat (ohm)</th><th>Vth (V)</th><th>emax (V)</th><th>eligible</th><th>classification</th></tr></thead><tbody>{rows}</tbody></table>
<h3>Source descriptors (V*/I*)</h3>
<table class="data" id="tbl-desc-{key}"><thead><tr><th>quantity</th><th>max</th><th>rms</th><th>time-normalized-L1</th><th>rctrl</th></tr></thead><tbody>
<tr><td>V*</td><td>{esc(d['v_star']['max_V'])}</td><td>{esc(d['v_star']['rms_V'])}</td><td>{esc(d['v_star']['time_normalized_l1_V'])}</td><td>{esc(d['rctrl'])}</td></tr>
<tr><td>I*</td><td>{esc(d['i_star']['max_A'])}</td><td>{esc(d['i_star']['rms_A'])}</td><td>-</td><td>-</td></tr></tbody></table>
<h3>Control residual (V/I)</h3>
<table class="data" id="tbl-resid-{key}"><thead><tr><th>window (ps)</th><th>V residual max (V)</th><th>I residual max (A)</th></tr></thead><tbody><tr><td>94-130</td><td>{rvmax:.6e}</td><td>{rimax:.6e}</td></tr></tbody></table>
<h3>Provenance / status</h3>
<table class="data" id="tbl-prov-{key}"><tbody>
<tr><td>source run</td><td>{esc(data['source']['run'])}</td></tr>
<tr><td>disposition</td><td>{esc(data['disposition'])}</td></tr>
<tr><td>readiness</td><td>{'READY' if rd['ready'] else 'NOT_READY'}</td></tr>
<tr><td>claim ceiling</td><td>descriptive non-authoritative; accepted raw/spec/analysis are authority</td></tr>
</tbody></table></div>"""
            sections.append(section)
    buttons = "".join(
        f'<button class="dash-btn" data-target="sec-L{l:02d}-{p}" onclick="showSection(this)">{l} ohm / {p}</button>'
        for l in LOADS for p in POLS)
    return f"""<!doctype html><html><head><meta charset="utf-8">
<title>BVM stable-load dashboard A04</title>
<style>
body{{font-family:sans-serif;margin:1em;background:#fff}}
.dash-btn{{margin:2px;padding:6px 10px;border:1px solid #999;border-radius:4px;background:#f0f0f0;cursor:pointer}}
.dash-btn.active{{background:#1f77b4;color:#fff;border-color:#1f77b4}}
.dash-section{{max-width:1320px;margin:0 auto}}
table.data{{border-collapse:collapse;width:100%;margin:6px 0;background:#fff}}
table.data th,table.data td{{border:1px solid #999;padding:3px 6px;font-size:12px}}
table.data th{{background:#e8e8e8}}
h2,h3{{margin:8px 0}}
</style>
<script>
function showSection(btn){{
document.querySelectorAll('.dash-section').forEach(s=>s.style.display='none');
document.querySelectorAll('.dash-btn').forEach(b=>b.classList.remove('active'));
document.getElementById(btn.dataset.target).style.display='block';
btn.classList.add('active');}}
</script></head><body>
<h1>BVM stable-load dashboard A04 (descriptive, non-authoritative)</h1>
<p>disposition: <b>{esc(data['disposition'])}</b>; units: time ps, voltage mV,
current uA, phase raw rad; readiness threshold 0.020 rad. Claim ceiling:
descriptive non-authoritative visualization completeness only; accepted
raw/specification/analysis remain scientific authority.</p>
<div>{buttons}</div>
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
