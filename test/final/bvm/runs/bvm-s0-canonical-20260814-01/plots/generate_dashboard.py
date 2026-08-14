#!/usr/bin/env python3
"""generate_dashboard -- DEPRECATED: superseded by generate_story.py.

Kept as the raw-data explorer generator (and for provenance); the guided
narrative is bvm-s0-story.html.  Unit schema: t_s (seconds, raw) / t_ps
(picoseconds, the ONLY axis the HTML consumes); traces use SVG scatter.
Regenerated bvm-s0-dashboard.html remains a working inspection tool.

Reads ONLY frozen evidence:
  - 12 raw CSVs: test/final/bvm/runs/bvm-s0-canonical-20260814-01/raw/<case>/<step>/run-01.csv
  - deterministic corrected data: .../S0-004/attempts/A01/corrected-analysis.json
  - local plotly.min.js (embedded, no CDN)
Emits plots/bvm-s0-dashboard.html -- a single self-contained file with all
data embedded.  No JoSIM run, no hand-filled values, no verdict change.

Usage: python3 generate_dashboard.py  (from repo root)
"""
from __future__ import annotations

import csv
import json
import pathlib

REPO = pathlib.Path('/home/howard/JoSIM')
RUN = REPO / 'test/final/bvm/runs/bvm-s0-canonical-20260814-01'
CORRECTED = (REPO / 'research/tasks/JH-20260814-BVM-S0-004/attempts/A01'
             / 'corrected-analysis.json')
PLOTLY_JS = pathlib.Path(
    '/home/howard/anaconda3/lib/python3.13/site-packages/plotly/package_data'
    '/plotly.min.js')
OUT = RUN / 'plots' / 'bvm-s0-dashboard.html'

CASES = ('init_positive_read', 'init_positive_control',
         'init_negative_read', 'init_negative_control')
STEPS = ('0.1ps', '0.05ps', '0.025ps')

TRACKS = [  # (key, label, unit, scale, color)
    ('I_WL1', 'I(I_WL1) stimulus', 'uA', 1e6, '#7a7a7a'),
    ('I_SE1', 'I(I_SE1) stimulus', 'uA', 1e6, '#9a9a9a'),
    ('P_JM1', 'P(B_JM1|XBVM1)', 'rad', 1.0, '#1f6fb2'),
    ('P_JM2', 'P(B_JM2|XBVM1)', 'rad', 1.0, '#e07b00'),
    ('V_JM1', 'V(B_JM1|XBVM1)', 'mV', 1e3, '#3b8fd4'),
    ('V_JM2', 'V(B_JM2|XBVM1)', 'mV', 1e3, '#f0a040'),
    ('V_SL1', 'V(SL1)', 'mV', 1e3, '#d1495b'),
    ('I_LSL', 'I(L_SL|XBVM1)', 'uA', 1e6, '#b5457f'),
]
COL_MAP = {
    'I_WL1': 'I(I_WL1)', 'I_SE1': 'I(I_SE1)',
    'P_JM1': 'P(B_JM1|XBVM1)', 'P_JM2': 'P(B_JM2|XBVM1)',
    'V_JM1': 'V(B_JM1|XBVM1)', 'V_JM2': 'V(B_JM2|XBVM1)',
    'V_SL1': 'V(SL1)', 'I_LSL': 'I(L_SL|XBVM1)',
}

# registered windows (ps) for background bands
BANDS = [
    ('initialization', 10, 21, '#e8f4ec'),
    ('settling', 21, 95, '#f7f7f7'),
    ('PRE', 80, 90, '#eef4fb'),
    ('READ', 96, 106, '#fdf0ef'),
    ('POST', 140, 150, '#f3eef7'),
]


from _viz_data import COL_MAP, load_all_datasets


def main() -> int:
    data = load_all_datasets(CASES, STEPS)

    corr = json.loads(CORRECTED.read_text(encoding='utf-8'))['cases']
    # summary values for every case/step
    summary = {}
    for case in CASES:
        for step in STEPS:
            c = corr[case][step]
            src = c['source']
            summary[f'{case}/{step}'] = {
                'v_peak': src['V_SL1']['peak_baseline_subtracted'],
                'v_lat': src['V_SL1']['latency_from_96ps_s'],
                'i_peak': src['I_LSL']['peak_baseline_subtracted'],
                'i_lat': src['I_LSL']['latency_from_96ps_s'],
                'pre': c['platform']['pre'],
                'post': c['platform']['post'],
                'phase_area': c['phase_area'],
            }

    plotly_js = PLOTLY_JS.read_text(encoding='utf-8')
    data_json = json.dumps(data, separators=(',', ':'))
    sum_json = json.dumps(summary, separators=(',', ':'))

    html = HTML_TEMPLATE.replace('__PLOTLY_JS__', plotly_js) \
                         .replace('__DATA_JSON__', data_json) \
                         .replace('__SUMMARY_JSON__', sum_json)
    OUT.write_text(html, encoding='utf-8')
    print(f'dashboard written: {OUT} ({OUT.stat().st_size / 1e6:.1f} MB)')
    return 0


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>BVM-S0 interactive dashboard</title>
<script>__PLOTLY_JS__</script>
<style>
  :root { --ink:#222; --mut:#666; --line:#ddd; --bg:#fff; --panel:#fafafa;
          --acc:#1f6fb2; --warn:#b5457f; --ok:#2e7d32; }
  * { box-sizing: border-box; }
  body { font-family: -apple-system, "Segoe UI", Roboto, sans-serif;
         margin: 0; padding: 18px 22px; color: var(--ink); background: var(--bg); }
  h1 { font-size: 20px; margin: 0 0 4px; }
  h2 { font-size: 14px; margin: 0 0 8px; }
  .sub { color: var(--mut); font-size: 12px; margin-bottom: 14px; }
  .badges { display: flex; gap: 8px; margin: 6px 0 14px; flex-wrap: wrap; }
  .badge { padding: 4px 12px; border-radius: 12px; font-size: 12px; color: #fff; }
  .badge.ok { background: var(--ok); }
  .badge.warn { background: var(--warn); }
  .badge.info { background: var(--acc); }
  .panel { background: var(--panel); border: 1px solid var(--line);
           border-radius: 8px; padding: 12px 14px; margin-bottom: 16px; }
  .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
  @media (max-width: 1100px) { .grid { grid-template-columns: 1fr; } }
  table { border-collapse: collapse; font-size: 12px; width: 100%; }
  th, td { border: 1px solid var(--line); padding: 4px 8px; text-align: left; }
  th { background: #f0f0f0; }
  .ctrl { display: flex; gap: 14px; align-items: center; flex-wrap: wrap;
          font-size: 13px; margin-bottom: 10px; }
  .ctrl label { margin-right: 4px; }
  select, button { font-size: 13px; padding: 3px 8px; }
  button { cursor: pointer; border: 1px solid var(--line); border-radius: 4px;
           background: #fff; }
  button:hover { background: #eef; }
  .note { font-size: 12px; color: var(--mut); margin-top: 6px; }
  .warn-note { color: var(--warn); font-weight: 600; }
  .claim { font-size: 12.5px; line-height: 1.55; }
  .claim b.ok { color: var(--ok); }
  .claim b.no { color: var(--warn); }
  .mono { font-family: ui-monospace, Menlo, Consolas, monospace; font-size: 11.5px; }
  #topology { width: 100%; }
  .tick { font-size: 11px; color: var(--mut); }
</style>
</head>
<body>

<h1>BVM-S0 canonical source experiment — interactive dashboard</h1>
<div class="sub">
  Data: frozen 12-run raw CSVs + S0-004 deterministic corrected analysis
  (both byte-verified). No new JoSIM run; scientific verdict unchanged.
  Generator: <span class="mono">plots/generate_dashboard.py</span>.
</div>
<div class="badges">
  <span class="badge ok">artifact VALID</span>
  <span class="badge warn">scientific disposition INCONCLUSIVE</span>
  <span class="badge info">bounded fixed-fixture observations only</span>
</div>

<!-- ================= EXPERIMENT CONFIG ================= -->
<div class="panel">
<h2>Experiment configuration (frozen, S0-001 design)</h2>
<table>
<tr><th>item</th><th>definition</th></tr>
<tr><td><b>positive initialization</b> (write-like state preparation)</td>
    <td>WL+BL ramp 0 → <b>+100 µA</b> over 10–11 ps, hold through 20 ps, return to 0 by 21 ps</td></tr>
<tr><td><b>negative initialization</b> (write-like state preparation)</td>
    <td>WL+BL ramp 0 → <b>−100 µA</b> over 10–11 ps, hold through 20 ps, return to 0 by 21 ps</td></tr>
<tr><td><b>read</b></td><td>WL+SE <b>+100 µA</b> at 96–105 ps (1 ps edges); BL is 0 during read</td></tr>
<tr><td><b>matched zero-read control</b></td><td>identical netlist/model/load/timestep/stop/PWL knots; only the two read-pulse amplitudes are zero</td></tr>
<tr><td><b>load</b></td><td>R_LD SL1 0 12 (12 Ω) — the only load</td></tr>
<tr><td><b>windows</b> (half-open, actual CSV time)</td>
    <td>PRE [80,90) ps · activity [94,108) ps · source [94,130) ps · POST [140,150) ps</td></tr>
<tr><td><b>grid</b></td><td>0.1 / 0.05 / 0.025 ps × 170 ps; 4 cases × 3 timesteps = 12 runs</td></tr>
</table>
<div class="note warn-note">
  "initialization" is labeled <b>write-like state preparation</b> only. The
  repository has NOT established a logical write-0/write-1 mapping for these
  procedures; they are operational names from D0.
</div>
</div>

<!-- ================= CONTROLS ================= -->
<div class="panel">
<h2>Controls</h2>
<div class="ctrl">
  <span><label>init sign</label>
    <select id="selSign"><option value="positive">positive</option>
    <option value="negative">negative</option></select></span>
  <span><label>read/control</label>
    <select id="selKind"><option value="read">read</option>
    <option value="control">matched zero-read control</option></select></span>
  <span><label>timestep</label>
    <select id="selStep">
      <option value="0.1ps">0.1 ps</option>
      <option value="0.05ps">0.05 ps</option>
      <option value="0.025ps">0.025 ps</option>
    </select></span>
  <span><label><input type="checkbox" id="chkOverlay">pos vs neg overlay (same step)</label></span>
  <span><label><input type="checkbox" id="chkStepOverlay">timestep overlay (same case)</label></span>
  <button id="btnPre">⏪ PRE [80,90)</button>
  <button id="btnRead">▶ READ [96,106)</button>
  <button id="btnPost">⏩ POST [140,150)</button>
  <button id="btnAll">⤢ full range</button>
</div>
<div id="wave" style="width:100%;"></div>
<div class="note">
  All tracks share one time axis: synchronized zoom / pan / hover. Background
  bands: <span style="background:#e8f4ec">initialization 10–21 ps</span>,
  <span style="background:#f7f7f7">settling 21–95 ps</span>,
  <span style="background:#eef4fb">PRE 80–90 ps</span>,
  <span style="background:#fdf0ef">READ 96–106 ps</span>,
  <span style="background:#f3eef7">POST 140–150 ps</span>.
</div>
</div>

<!-- ================= SUMMARY ================= -->
<div class="grid">
<div class="panel">
<h2>Summary — current selection</h2>
<table id="sumTab"><tbody></tbody></table>
<div class="note">Derived from corrected-analysis.json (reconstruction_matches_frozen_json = true).</div>
</div>

<!-- ================= TOPOLOGY ================= -->
<div class="panel">
<h2>BVM topology (netlist-derived schematic)</h2>
<svg id="topology" viewBox="0 0 460 300" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <marker id="arrow" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="6" markerHeight="6" orient="auto">
      <path d="M0,0 L8,4 L0,8 z" fill="#888"/>
    </marker>
  </defs>
  <style>
    .node { fill:#fff; stroke:#444; stroke-width:1.4; }
    .wire { stroke:#666; stroke-width:1.2; fill:none; }
    .sloop { stroke:#1f6fb2; stroke-width:1.6; fill:none; }
    .rloop { stroke:#888; stroke-width:1.4; fill:none; }
    .lbl { font-size:9px; fill:#333; }
    .lblb { font-size:9px; fill:#1f6fb2; font-weight:bold; }
    .lblr { font-size:9px; fill:#666; }
    .box { fill:none; stroke-dasharray:4 3; }
  </style>
  <!-- WL/BL/SE -->
  <text x="10" y="60" class="lbl" font-weight="bold">WL</text>
  <text x="10" y="105" class="lbl" font-weight="bold">BL</text>
  <text x="40" y="30" class="lbl" font-weight="bold">SE</text>
  <line x1="28" y1="57" x2="70" y2="57" class="wire"/>
  <line x1="28" y1="102" x2="70" y2="102" class="wire"/>
  <line x1="50" y1="32" x2="80" y2="62" class="wire"/>
  <circle cx="70" cy="57" r="3.2" class="node"/><circle cx="70" cy="102" r="3.2" class="node"/>
  <circle cx="84" cy="62" r="3.2" class="node"/>
  <text x="76" y="52" class="lblr">R_WL+L_PWL</text>
  <text x="76" y="97" class="lblr">R_BL+L_PBL</text>
  <text x="86" y="48" class="lblr">R_SE+L_PSE</text>
  <!-- N1 -->
  <circle cx="112" cy="80" r="3.6" class="node"/>
  <text x="106" y="95" class="lbl">N1</text>
  <!-- S-loop: JM1/LM1 to gnd ; LM2/JM2 -->
  <path d="M112 80 L150 58 L150 120 L112 80" class="sloop"/>
  <path d="M112 80 L112 200" class="sloop"/>
  <text x="142" y="52" class="lblb">B_JM1</text>
  <text x="118" y="66" class="lblb">L_M1→GND</text>
  <circle cx="150" cy="58" r="3.4" class="node"/><circle cx="150" cy="120" r="3.4" class="node"/>
  <text x="156" y="124" class="lblb">B_JM2 (L_M2 above)</text>
  <text x="150" y="140" class="lbl">N2</text>
  <!-- L_M3 to N5 -->
  <path d="M150 128 L150 170 L210 170" class="sloop"/>
  <text x="158" y="162" class="lblb">L_M3</text>
  <text x="214" y="176" class="lbl">N5</text>
  <circle cx="210" cy="170" r="3.4" class="node"/>
  <!-- LPM to gnd -->
  <path d="M210 170 L210 205" class="sloop"/>
  <text x="196" y="196" class="lblb">L_PM→GND</text>
  <!-- R-loop: N2-LS1-JS1-N3 ; N3-RS-N6 ; N6-LS2-JS2-N5 -->
  <path d="M150 128 L200 128 L200 230 L240 230 L240 170" class="rloop"/>
  <text x="192" y="140" class="lblr">L_S1</text>
  <text x="196" y="214" class="lblr">B_JS1</text>
  <circle cx="200" cy="128" r="3.2" class="node"/>
  <circle cx="200" cy="230" r="3.2" class="node"/>
  <text x="188" y="244" class="lblr">N3</text>
  <text x="244" y="244" class="lblr">N6</text>
  <path d="M200 230 L280 230 L280 170" class="rloop"/>
  <text x="252" y="222" class="lblr">R_S</text>
  <text x="256" y="204" class="lblr">B_JS2 (L_S2)</text>
  <circle cx="280" cy="230" r="3.2" class="node"/>
  <!-- S-loop box, R-loop box, coupling -->
  <rect x="90" y="40" width="150" height="180" class="box" stroke="#1f6fb2"/>
  <text x="96" y="232" class="lblb">S-Loop (storage)</text>
  <rect x="140" y="110" width="170" height="140" class="box" stroke="#888"/>
  <text x="196" y="262" class="lblr">R-Loop (readout)</text>
  <!-- coupling annotation -->
  <line x1="210" y1="170" x2="240" y2="170" stroke="#b5457f" stroke-width="1.8" marker-end="url(#arrow)"/>
  <text x="220" y="162" class="lbl" fill="#b5457f" font-size="8.5">N2–LM3–N5 coupling</text>
  <!-- SE into N3 -->
  <path d="M84 62 L200 230" stroke="#b5457f" stroke-width="1.1" stroke-dasharray="3 2" fill="none"/>
  <!-- output chain -->
  <path d="M280 230 L330 230 L360 195" class="wire"/>
  <circle cx="330" cy="230" r="3.2" class="node"/>
  <circle cx="360" cy="195" r="3.2" class="node"/>
  <text x="320" y="222" class="lblr">L_PSL</text>
  <text x="352" y="188" class="lblr">R_SL→N8</text>
  <text x="360" y="180" class="lbl" font-weight="bold">SL out (12 Ω)</text>
  <text x="240" y="282" class="lbl" fill="#888">direct probes: P/V(B_JM1|XBVM1), P/V(B_JM2|XBVM1), V(SL1), I(L_SL|XBVM1)</text>
</svg>
<div class="note">Element connectivity from <span class="mono">bvm_cell.cir</span> v6; loop roles are netlist-comment based. Schematic only — no current/phase claim.</div>
</div>
</div>

<!-- ================= CONVERGENCE ================= -->
<div class="panel">
<h2>Numerical-convergence status (registered rule, frozen)</h2>
<table>
<tr><th>adjacent pair</th><th>result</th></tr>
<tr><td>0.1 → 0.05 ps</td><td><b>FAIL</b>: matched-control source-peak latency −0.70 ps vs +0.15 ps = <b>0.85 ps &gt; 0.5 ps</b> task-local band</td></tr>
<tr><td>0.05 → 0.025 ps</td><td>PASS (applicable registered comparisons)</td></tr>
</table>
<div class="note warn-note">
  → artifact <b>VALID</b>, scientific disposition <b>INCONCLUSIVE</b> (C02).
  The 0.85 ps &gt; 0.5 ps control-latency comparison is the sole registered
  blocker. No fourth timestep or band change is permitted; the verdict is not
  altered by this dashboard. INCONCLUSIVE is not an experiment failure.
</div>
</div>

<!-- ================= CLAIM BOUNDARY ================= -->
<div class="panel">
<h2>Claim boundary — what these observations do and do not establish</h2>
<div class="claim">
<b class="ok">Established (bounded, fixed-fixture):</b>
state-conditioned source-port V(SL1)/I(L_SL|XBVM1) response and direct
JM1/JM2 P/V observables in the named windows, at each named timestep;
matched zero-read controls are noise-level (15–18 nV / 1.3–1.5 nA);
activity-window phase changes are all far below ±1 turn; no gross
pre/post signature inversion. Provenance/raw validity is sealed (59
entries) and the corrected report is deterministic.
<br><br>
<b class="no">NOT established (do not claim from these data):</b>
logical read0/read1 (write-0/write-1) mapping · SFQ/fluxoid counts ·
nondestructive logical read / state preservation · receiver/JTL
reception · resolution-independent source baseline · candidate verdict ·
INTERFACE_GATE_V1 · published or hardware reproduction.
</div>
</div>

<div class="panel">
<h2>Experiment/status flow</h2>
<table>
<tr><td>M1–M12 measurement repair</td><td>→ ACCEPTED (2026-08-13); METRIC_SPEC_V2 frozen</td></tr>
<tr><td>D0 initialization readiness</td><td>→ 75 ps bound (VALID, tested grid)</td></tr>
<tr><td>BVM-S0 12-run source characterization</td><td>→ artifact VALID, convergence INCONCLUSIVE (C02, 2026-08-14)</td></tr>
<tr><td>next week (suggestion, not executed)</td><td>new preregistered source convergence/characterization task; receiver work only later</td></tr>
</table>
</div>

<script>
'use strict';
const DATA = __DATA_JSON__;
const SUM  = __SUMMARY_JSON__;

const CASES = ['init_positive_read','init_positive_control',
               'init_negative_read','init_negative_control'];
const STEPS = ['0.1ps','0.05ps','0.025ps'];
const TRACKS = [
  {k:'I_WL1', l:'I(I_WL1) stimulus', u:'µA', s:1e6, c:'#7a7a7a'},
  {k:'I_SE1', l:'I(I_SE1) stimulus', u:'µA', s:1e6, c:'#9a9a9a'},
  {k:'P_JM1', l:'P(B_JM1|XBVM1)', u:'rad', s:1, c:'#1f6fb2'},
  {k:'P_JM2', l:'P(B_JM2|XBVM1)', u:'rad', s:1, c:'#e07b00'},
  {k:'V_JM1', l:'V(B_JM1|XBVM1)', u:'mV', s:1e3, c:'#3b8fd4'},
  {k:'V_JM2', l:'V(B_JM2|XBVM1)', u:'mV', s:1e3, c:'#f0a040'},
  {k:'V_SL1', l:'V(SL1)', u:'mV', s:1e3, c:'#d1495b'},
  {k:'I_LSL', l:'I(L_SL|XBVM1)', u:'µA', s:1e6, c:'#b5457f'},
];
const BANDS = [
  {n:'initialization', a:10, b:21, c:'#e8f4ec'},
  {n:'settling', a:21, b:95, c:'#f7f7f7'},
  {n:'PRE', a:80, b:90, c:'#eef4fb'},
  {n:'READ', a:96, b:106, c:'#fdf0ef'},
  {n:'POST', a:140, b:150, c:'#f3eef7'},
];

function selCase(){ const s=document.getElementById('selSign').value;
  const k=document.getElementById('selKind').value; return 'init_'+s+'_'+k; }
function selStep(){ return document.getElementById('selStep').value; }
function keyOf(cs, st){ return cs+'/'+st; }

function buildFig(){
  const traces = [];
  const n = TRACKS.length;
  const dom = (i)=>[1-(i+1)/n, 1/n];
  TRACKS.forEach((tr, i)=>{
    traces.push({
      type:'scatter', mode:'lines', name:tr.l, legendgroup:'main',
      x:[], y:[], line:{color:tr.c, width:1.2},
      xaxis:'x', yaxis:'y'+(i+1),
      hovertemplate: tr.l+': %{y:.6g}'+tr.u+'<extra></extra>'
    });
  });
  const shapes = [];
  BANDS.forEach(b=>{
    shapes.push({type:'rect', xref:'x', yref:'paper',
      x0:b.a, x1:b.b, y0:0, y1:1, fillcolor:b.c, opacity:0.55,
      line:{width:0}, layer:'below'});
  });
  const layout = {
    title:{text:'BVM-S0 waveforms — synchronized time axis',
           font:{size:13}},
    hovermode:'x unified',
    margin:{l:60, r:20, t:46, b:44},
    xaxis:{domain:[0,1], title:'time (ps)', range:[20,160]},
    shapes:shapes,
    legend:{orientation:'h', y:1.06, font:{size:10}},
  };
  TRACKS.forEach((tr,i)=>{
    layout['yaxis'+(i+1)]={domain:dom(i), title:{text:tr.l+' ('+tr.u+')',
                             font:{size:10}}, tickfont:{size:9}};
  });
  return {traces, layout};
}

let fig = buildFig();
Plotly.newPlot('wave', fig.traces, fig.layout, {responsive:true, displaylogo:false});

function updateWave(){
  const cs = selCase(), st = selStep();
  const base = DATA[keyOf(cs, st)];
  const overSign = document.getElementById('chkOverlay').checked;
  const overStep = document.getElementById('chkStepOverlay').checked;
  const upd = {};
  const n = TRACKS.length;
  TRACKS.forEach((tr, i)=>{
    const x = base.t_ps;
    const y = base.c[tr.k].map(v=>v*tr.s);
    let y2=null;
    if (overSign){
      const other = (cs.indexOf('positive')>=0)
        ? cs.replace('positive','negative') : cs.replace('negative','positive');
      y2 = DATA[keyOf(other, st)].c[tr.k].map(v=>v*tr.s);
    }
    upd['x'+(i+1)] = [x];
    upd['y'+(i+1)] = [y];
  });
  // overlay as extra traces (source tracks only, dashed)
  const extra = [];
  const srcIdx = [6,7]; // V_SL1, I_LSL
  if (overSign){
    const other = (cs.indexOf('positive')>=0)
      ? cs.replace('positive','negative') : cs.replace('negative','positive');
    srcIdx.forEach(i=>{
      const tr=TRACKS[i];
      extra.push({type:'scatter', mode:'lines',
        name:(cs.indexOf('positive')>=0?'neg':'pos')+' read '+tr.l,
        x:DATA[keyOf(other, st)].t_ps,
        y:DATA[keyOf(other, st)].c[tr.k].map(v=>v*tr.s),
        line:{color:'#555', width:1.2, dash:'dot'},
        xaxis:'x', yaxis:'y'+(i+1),
        hovertemplate:'overlay: %{y:.6g}'+tr.u+'<extra></extra>'});
    });
  }
  if (overStep){
    STEPS.forEach(stp=>{
      srcIdx.forEach(i=>{
        const tr=TRACKS[i];
        extra.push({type:'scatter', mode:'lines', name:stp+' '+tr.l,
          x:DATA[keyOf(cs, stp)].t_ps,
          y:DATA[keyOf(cs, stp)].c[tr.k].map(v=>v*tr.s),
          line:{color:'#999', width:1.0, dash:'dot'},
          xaxis:'x', yaxis:'y'+(i+1),
          hovertemplate:stp+': %{y:.6g}'+tr.u+'<extra></extra>'});
      });
    });
  }
  Plotly.react('wave', fig.traces.concat(extra), fig.layout, {responsive:true});
  renderSummary(cs, st);
}

function renderSummary(cs, st){
  const s = SUM[keyOf(cs, st)];
  const rows = [
    ['case', cs], ['timestep', st],
    ['V(SL1) baseline-subtracted peak', (s.v_peak*1e3).toFixed(3)+' mV'],
    ['V(SL1) latency from 96 ps', (s.v_lat*1e12).toFixed(1)+' ps'],
    ['I(L_SL) baseline-subtracted peak', (s.i_peak*1e6).toFixed(2)+' µA'],
    ['I(L_SL) latency from 96 ps', (s.i_lat*1e12).toFixed(1)+' ps'],
    ['pre JM1 mean', s.pre.JM1.toFixed(6)+' rad'],
    ['pre JM2 mean', s.pre.JM2.toFixed(6)+' rad'],
    ['post JM1 mean', s.post.JM1.toFixed(6)+' rad'],
    ['post JM2 mean', s.post.JM2.toFixed(6)+' rad'],
    ['JM1 phase_delta turns [94,108)', s.phase_area.JM1.phase_delta_turns.toFixed(6)],
    ['JM2 phase_delta turns [94,108)', s.phase_area.JM2.phase_delta_turns.toFixed(6)],
    ['JM1 area turns [94,108)', s.phase_area.JM1.area_turns.toFixed(6)],
    ['JM2 area turns [94,108)', s.phase_area.JM2.area_turns.toFixed(6)],
  ];
  document.querySelector('#sumTab tbody').innerHTML =
    rows.map(r=>'<tr><td>'+r[0]+'</td><td class="mono">'+r[1]+'</td></tr>').join('');
}

function setRange(a, b){
  Plotly.relayout('wave', {'xaxis.range': [a, b]});
}

document.getElementById('selSign').onchange = updateWave;
document.getElementById('selKind').onchange = updateWave;
document.getElementById('selStep').onchange = updateWave;
document.getElementById('chkOverlay').onchange = updateWave;
document.getElementById('chkStepOverlay').onchange = updateWave;
document.getElementById('btnPre').onclick = ()=>setRange(75, 95);
document.getElementById('btnRead').onclick = ()=>setRange(92, 112);
document.getElementById('btnPost').onclick = ()=>setRange(135, 155);
document.getElementById('btnAll').onclick = ()=>setRange(20, 160);

updateWave();
</script>
</body>
</html>
"""

if __name__ == '__main__':
    raise SystemExit(main())
