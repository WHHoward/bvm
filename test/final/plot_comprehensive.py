#!/usr/bin/env python3
"""Comprehensive 4-BVM + QB Test Comparison — CDN Plotly."""
import csv, json, os
os.chdir('/home/howard/JoSIM/test/final')

C = {'blue':'#58a6ff','red':'#ff7b72','green':'#7ee787','orange':'#f0883e',
     'purple':'#d2a8ff','yellow':'#e3b341','gray':'#484f58','white':'#c9d1d9',
     'bg':'#161b22','paper':'#0d1117','cyan':'#39d2c0','pink':'#f778ba'}

BASE = {
    'plot_bgcolor':C['bg'],'paper_bgcolor':C['paper'],
    'font':{'color':C['white'],'size':11},
    'legend':{'x':0.01,'y':0.99,'bgcolor':'rgba(0,0,0,0)','bordercolor':'#30363d'},
    'margin':{'l':55,'r':40,'t':50,'b':45},'hovermode':'x unified',
    'xaxis':{'gridcolor':'#30363d','zerolinecolor':'#484f58'},
    'yaxis':{'gridcolor':'#30363d','zerolinecolor':'#484f58'},
}

def mk(ttl, ytl, traces, xtitle='Time (ps)'):
    L = json.loads(json.dumps(BASE)); L['title'] = ttl; L['yaxis']['title'] = ytl
    L['xaxis']['title'] = xtitle
    for t in traces: t['type'] = 'scatter'
    return L, traces

def load(fname):
    with open(fname) as f:
        rows = list(csv.DictReader(f))
    T = [float(r['time'])*1e12 for r in rows]
    cols = list(rows[0].keys())
    def g(k,m=1): return [float(r[k])*m for r in rows] if k in cols else None
    return T, cols, g

def peak(t0,t1,arr,T):
    idx=[i for i in range(len(T)) if t0<T[i]<t1]
    return max(arr[i] for i in idx) if idx else 0

# ============================================================
# Load all data
# ============================================================
T_iso18, cols18, g18 = load('isolate_js18.csv')
T_iso25, cols25, g25 = load('isolate_js25.csv')
T_bl,   cols_bl,  g_bl  = load('final_4bvm_series.csv')
T_js25, cols_js25,g_js25= load('series_js25.csv')
T_r7,   cols_r7,  g_r7  = load('series_r7.csv')
T_r12,  cols_r12, g_r12 = load('series_r12.csv')
T_r15,  cols_r15, g_r15 = load('series_r15.csv')

# ============================================================
# Chart 1: Isolation comparison — I_SL
# ============================================================
charts = []

# Chart 1: Isolation I_SL
isl18 = g18('I(B_LD1)', 1e6)
isl25 = g25('I(B_LD1)', 1e6)
pjs18 = g18('P(B_JS_Q)')
pjs25 = g25('P(B_JS_Q)')

charts.append(mk('<b>① Isolation: Single BVM + jj320 + QB — I_SL</b>', 'Current (μA)',
    [{'x':T_iso18,'y':isl18,'name':'JS=18μA','line':{'color':C['red'],'width':2}},
     {'x':T_iso25,'y':isl25,'name':'JS=25μA','line':{'color':C['green'],'width':2}},
     {'x':[0,110],'y':[32,32],'name':'12×jj320 ref (32μA)','line':{'color':C['gray'],'width':1,'dash':'dash'}}]))

charts.append(mk('<b>② Isolation: Single BVM + jj320 + QB — P_JS Phase</b>', 'Phase (rad)',
    [{'x':T_iso18,'y':pjs18,'name':'JS=18μA (0.23Φ₀)','line':{'color':C['red'],'width':2}},
     {'x':T_iso25,'y':pjs25,'name':'JS=25μA (0.18Φ₀)','line':{'color':C['green'],'width':2}},
     {'x':[0,110],'y':[6.283,6.283],'name':'1Φ₀','line':{'color':C['gray'],'width':0.5,'dash':'dot'},'showlegend':False}]))

# ============================================================
# 4-BVM overlays: I_SL comparison across configs
# ============================================================
isl_bl   = g_bl('I(B_LD1)', 1e6)
isl_js25 = g_js25('I(B_LD1)', 1e6)
isl_r7   = g_r7('I(B_LD1)', 1e6)
isl_r12  = g_r12('I(B_LD1)', 1e6)
isl_r15  = g_r15('I(B_LD1)', 1e6)

pjs_bl   = g_bl('P(B_JS_Q)')
pjs_js25 = g_js25('P(B_JS_Q)')
pjs_r7   = g_r7('P(B_JS_Q)')
pjs_r12  = g_r12('P(B_JS_Q)')
pjs_r15  = g_r15('P(B_JS_Q)')

# Chart 3: I_SL — JS comparison (JS=18 vs JS=25)
charts.append(mk('<b>③ 4-BVM I_SL: JS=18μA vs JS=25μA (R=10Ω)</b>', 'I_SL (μA)',
    [{'x':T_bl,'y':isl_bl,'name':'JS=18μA','line':{'color':C['red'],'width':2}},
     {'x':T_js25,'y':isl_js25,'name':'JS=25μA','line':{'color':C['green'],'width':2}}]))

# Chart 4: P_JS — JS comparison
charts.append(mk('<b>④ 4-BVM P_JS: JS=18μA vs JS=25μA (R=10Ω)</b>', 'Phase (rad)',
    [{'x':T_bl,'y':pjs_bl,'name':'JS=18μA (max 1.55Φ₀)','line':{'color':C['red'],'width':2}},
     {'x':T_js25,'y':pjs_js25,'name':'JS=25μA (max 0.87Φ₀)','line':{'color':C['green'],'width':2}},
     {'x':[0,230],'y':[6.283,6.283],'name':'1Φ₀','line':{'color':C['gray'],'width':0.5,'dash':'dot'},'showlegend':False}]))

# Chart 5: I_SL — R_shunt sweep
charts.append(mk('<b>⑤ R_shunt Sweep: I_SL (JS=25μA)</b>', 'I_SL (μA)',
    [{'x':T_r7,'y':isl_r7,'name':'R=7Ω','line':{'color':C['blue'],'width':1.8}},
     {'x':T_js25,'y':isl_js25,'name':'R=10Ω','line':{'color':C['yellow'],'width':1.8}},
     {'x':T_r12,'y':isl_r12,'name':'R=12Ω','line':{'color':C['orange'],'width':1.8}},
     {'x':T_r15,'y':isl_r15,'name':'R=15Ω','line':{'color':C['purple'],'width':1.8}}]))

# Chart 6: P_JS — R_shunt sweep
charts.append(mk('<b>⑥ R_shunt Sweep: P_JS Phase (JS=25μA)</b>', 'Phase (rad)',
    [{'x':T_r7,'y':pjs_r7,'name':'R=7Ω (0.80Φ₀)','line':{'color':C['blue'],'width':1.8}},
     {'x':T_js25,'y':pjs_js25,'name':'R=10Ω (0.87Φ₀)','line':{'color':C['yellow'],'width':1.8}},
     {'x':T_r12,'y':pjs_r12,'name':'R=12Ω (0.92Φ₀)','line':{'color':C['orange'],'width':1.8}},
     {'x':T_r15,'y':pjs_r15,'name':'R=15Ω (1.00Φ₀)','line':{'color':C['purple'],'width':1.8}},
     {'x':[0,230],'y':[6.283,6.283],'name':'1Φ₀','line':{'color':C['gray'],'width':0.5,'dash':'dot'},'showlegend':False}]))

# Chart 7: Phase reset quality — JS=18 vs JS=25 best
charts.append(mk('<b>⑦ Phase Reset Quality: JS=18μA (poor) vs JS=25μA R=7Ω (best)</b>', 'Phase (rad)',
    [{'x':T_bl,'y':pjs_bl,'name':'JS=18μA — poor reset (3.3rad残留)','line':{'color':C['red'],'width':2}},
     {'x':T_r7,'y':pjs_r7,'name':'JS=25μA R=7Ω — clean reset (0.24rad残留)','line':{'color':C['cyan'],'width':2.5}},
     {'x':[0,230],'y':[6.283,6.283],'name':'1Φ₀','line':{'color':C['gray'],'width':0.5,'dash':'dot'},'showlegend':False}]))

# ============================================================
# Summary table data
# ============================================================
reads = [(110,125),(140,155),(170,185),(200,215)]
def extract(rows, T, g):
    isl = g('I(B_LD1)', 1e6)
    pjs = g('P(B_JS_Q)')
    ijs = g('I(B_JS_Q)', 1e6)
    vjs = g('V(B_JS_Q)', 1e3)
    r_isl = [peak(t0,t1,isl,T) for t0,t1 in reads]
    r_pjs = [peak(t0,t1,pjs,T) for t0,t1 in reads]
    r_ijs = [peak(t0,t1,ijs,T) for t0,t1 in reads]
    r_vjs = [peak(t0,t1,vjs,T) for t0,t1 in reads]
    # Phase reset: min phase between Read3 end and Read4 start
    btwn = [i for i in range(len(T)) if 185<T[i]<200]
    p_min = min(pjs[i] for i in btwn) if btwn else 0
    return r_isl, r_pjs, r_ijs, r_vjs, p_min

with open('final_4bvm_series.csv') as f: rows_bl = list(csv.DictReader(f))
with open('series_js25.csv') as f: rows_js25 = list(csv.DictReader(f))
with open('series_r7.csv') as f: rows_r7 = list(csv.DictReader(f))
with open('series_r12.csv') as f: rows_r12 = list(csv.DictReader(f))
with open('series_r15.csv') as f: rows_r15 = list(csv.DictReader(f))

d_bl   = extract(rows_bl, T_bl, g_bl)
d_js25 = extract(rows_js25, T_js25, g_js25)
d_r7   = extract(rows_r7, T_r7, g_r7)
d_r12  = extract(rows_r12, T_r12, g_r12)
d_r15  = extract(rows_r15, T_r15, g_r15)

# Isolation data
r_iso18 = (peak(90,105,isl18,T_iso18), peak(90,105,pjs18,T_iso18),
           peak(90,105,g18('I(B_JS_Q)',1e6),T_iso18), peak(90,105,g18('V(B_JS_Q)',1e3),T_iso18))
r_iso25 = (peak(90,105,isl25,T_iso25), peak(90,105,pjs25,T_iso25),
           peak(90,105,g25('I(B_JS_Q)',1e6),T_iso25), peak(90,105,g25('V(B_JS_Q)',1e3),T_iso25))

# ============================================================
# Build HTML
# ============================================================
html_parts = [
    '<!DOCTYPE html>\n<html><head><meta charset="utf-8">\n',
    '<script src="https://cdn.plot.ly/plotly-2.32.0.min.js"></script>\n',
    '<style>\n',
    'body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;',
    'background:#0d1117;color:#c9d1d9;margin:0;padding:10px 15px}\n',
    'h1{color:#58a6ff;text-align:center;margin:12px 0 2px;font-size:18px}\n',
    'h2{color:#8b949e;text-align:center;font-weight:400;font-size:12px;margin:0 0 12px}\n',
    '.chart-wrap{max-width:1400px;margin:0 auto 8px;width:100%}\n',
    '.chart{width:100%;height:280px;background:#161b22;border-radius:6px;border:1px solid #30363d}\n',
    '.sum{max-width:1400px;margin:10px auto;padding:12px 20px;background:#161b22;',
    'border:1px solid #30363d;border-radius:6px;font-size:12px;line-height:1.6}\n',
    '.sum h3{color:#58a6ff;margin:0 0 6px;font-size:14px}\n',
    '.ok{color:#7ee787}.warn{color:#e3b341}.bad{color:#ff7b72}\n',
    'table{border-collapse:collapse;width:100%;margin:8px 0;font-size:11px}\n',
    'th{background:#1a2332;color:#58a6ff;padding:5px 8px;border:1px solid #30363d}\n',
    'td{padding:5px 8px;border:1px solid #30363d;text-align:center}\n',
    'tr.sep td{border-top:2px solid #58a6ff}\n',
    '</style></head><body>\n',
    '<h1>4-BVM Array + QB — Comprehensive Test Results</h1>\n',
    '<h2>Isolation tests + JS IC comparison + R_shunt sweep | Series topology SL→jj320→QB</h2>\n']

for i, (lyt, traces) in enumerate(charts):
    html_parts.append(f'<div class="chart-wrap"><div class="chart" id="c{i}"></div></div>\n')
    html_parts.append(f'<script>Plotly.newPlot("c{i}",{json.dumps(traces)},{json.dumps(lyt)},{{responsive:true}});</script>\n')

# Summary tables
def row(label, d, fmt_isl='{:.1f}', fmt_pjs='{:.1f}rad ({:.2f}Φ₀)'):
    return (f'<tr><td>{label}</td>'
            f'<td class="ok">{fmt_isl.format(d[0][0])}</td>'
            f'<td class="ok">{fmt_isl.format(d[0][1])}</td>'
            f'<td class="ok">{fmt_isl.format(d[0][2])}</td>'
            f'<td class="ok">{fmt_isl.format(d[0][3])}</td>'
            f'<td>{fmt_pjs.format(d[1][0], d[1][0]/6.283)}</td>'
            f'<td>{fmt_pjs.format(d[1][3], d[1][3]/6.283)}</td>'
            f'<td>{d[4]:.2f}rad</td></tr>\n')

html_parts.append(f'''<div class="sum">
<h3>A. Isolation Test — Single BVM + 1×jj320 + QB</h3>
<table>
<tr><th>JS IC</th><th>I_SL peak</th><th>I_JS peak</th><th>P_JS peak</th><th>V_JS peak</th><th>V_OUT peak</th><th>BVM Write</th><th>NDRO</th></tr>
<tr><td>18 μA</td><td class="ok">{r_iso18[0]:.1f} μA</td><td>{r_iso18[2]:.1f} μA</td><td>{r_iso18[1]:.1f} rad ({r_iso18[1]/6.283:.2f}Φ₀)</td><td>{r_iso18[3]:.3f} mV</td><td>~0 mV</td><td>13.4 rad</td><td class="ok">OK</td></tr>
<tr><td>25 μA</td><td class="ok">{r_iso25[0]:.1f} μA</td><td>{r_iso25[2]:.1f} μA</td><td>{r_iso25[1]:.1f} rad ({r_iso25[1]/6.283:.2f}Φ₀)</td><td>{r_iso25[3]:.3f} mV</td><td>~0 mV</td><td>13.4 rad</td><td class="ok">OK</td></tr>
</table>
<p><b>Key:</b> Single BVM I_SL = {r_iso18[0]:.0f}-{r_iso25[0]:.0f}μA → close to 12×jj320 ref (32μA).<br>
<span class="ok">Conclusion: Load impedance change alone costs only ~2-3μA.</span> The 32→17μA drop in 4-BVM is from <b>multi-BVM leakage</b> (~12-15μA loss into non-reading BVM R-loops).</p>

<h3>B. 4-BVM Array — All Configurations</h3>
<table>
<tr><th>Config</th><th>Read1 I_SL</th><th>Read2 I_SL</th><th>Read3 I_SL</th><th>Read4 I_SL</th><th>Read1 P_JS</th><th>Read4 P_JS</th><th>Phase Reset R3→R4</th></tr>
''' +
row('JS=18μA R=10Ω (基线)', d_bl) +
row('JS=25μA R=10Ω', d_js25) +
row('JS=25μA R=7Ω', d_r7) +
row('JS=25μA R=12Ω', d_r12) +
row('JS=25μA R=15Ω', d_r15) +
'''</table>

<h3>C. R_shunt Sweep Trends (JS=25μA)</h3>
<table>
<tr><th>R_shunt</th><th>R_eff (RN||R)</th><th>βc_eff</th><th>Read4 I_SL</th><th>Read4 P_JS</th><th>Phase Reset</th><th>Assessment</th></tr>
<tr><td>7Ω</td><td>4.1Ω</td><td>0.20</td><td class="ok">73.3 μA</td><td>0.80Φ₀</td><td class="ok">0.24 rad</td><td>Highest I_SL, best reset, lowest phase</td></tr>
<tr><td>10Ω</td><td>5.0Ω</td><td>0.30</td><td class="ok">67.1 μA</td><td>0.87Φ₀</td><td class="ok">0.31 rad</td><td>Balanced</td></tr>
<tr><td>12Ω</td><td>5.5Ω</td><td>0.36</td><td>64.1 μA</td><td>0.92Φ₀</td><td class="ok">0.39 rad</td><td>Higher phase, slightly lower I_SL</td></tr>
<tr><td>15Ω</td><td>6.0Ω</td><td>0.43</td><td>59.6 μA</td><td class="ok">1.00Φ₀</td><td>0.71 rad</td><td>Best phase (1.00Φ₀), worst reset</td></tr>
</table>

<h3>D. Key Findings</h3>
<table>
<tr><th>Question</th><th>Answer</th></tr>
<tr><td>Why I_SL drops from 32μA→17μA in 4-BVM?</td>
  <td><b>80% from multi-BVM leakage</b> (~12μA lost into 3 non-reading BVM R-loops), <b>20% from load impedance</b> (~3μA: 12×jj320→1×jj320+QB). Isolation test proves single BVM+QB still pulls 29-31μA.</td></tr>
<tr><td>How many SFQ pulses does QB output?</td>
  <td class="bad"><b>Zero discrete pulses.</b> Phase is continuous. Max accumulated: 1.00-1.55Φ₀ (with 4 cells). No 2π resets. The 10ps BVM pulse is too short for the QB junction to complete a full SFQ transition.</td></tr>
<tr><td>JS=18μA vs JS=25μA?</td>
  <td>JS=25μA gives <b>higher I_SL</b> (+11% at Read4), <b>much better phase reset</b> (0.31 vs 3.31 rad残留), but <b>lower phase accumulation</b> (0.87 vs 1.55Φ₀). JS=25μA is preferred for clean multi-read operation.</td></tr>
<tr><td>Best R_shunt?</td>
  <td>R=7Ω: highest I_SL, cleanest reset. R=15Ω: highest phase (1.00Φ₀). <b>Trade-off: no configuration achieves discrete 2π SFQ.</b></td></tr>
<tr><td>Does V_OUT show any output?</td>
  <td class="bad"><b>No.</b> V_OUT < 0.03mV in all tests. The QB output junction (JL2) never triggers.</td></tr>
</table>

<h3>E. Fundamental Limitation</h3>
<p>
The BVM read current pulse is <b>~10ps wide (FWHM)</b> during single-cell read, dropping to <b>~3-4ps during multi-cell reads</b>.
To generate one SFQ pulse (Φ₀ = 2.07 mV·ps), the QB junction needs to sustain V_JS above ~0.2mV for ~10ps.
Currently V_JS peaks at only 0.3mV and the pulse is too short.<br><br>

<span class="warn">Bottom line:</span> The QB circuit in its current form <b>does NOT convert BVM analog current levels into discrete SFQ pulse counts.</b>
The phase accumulation is continuous and doesn't reach clean 2π multiples.
This is the "modification" the MVM paper alludes to but doesn't detail — our results suggest a <b>non-trivial redesign</b> of the QB front-end is needed for BVM interfacing.
</p>
</div></body></html>''')

with open('COMPREHENSIVE_RESULTS.html','w') as f: f.write(''.join(html_parts))
print(f"Done: COMPREHENSIVE_RESULTS.html ({len(''.join(html_parts))//1024}KB)")
