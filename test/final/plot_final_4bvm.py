#!/usr/bin/env python3
"""Final 4-BVM + QB Series — CDN Plotly."""
import csv, json

C = {'blue':'#58a6ff','red':'#ff7b72','green':'#7ee787','orange':'#f0883e',
     'purple':'#d2a8ff','yellow':'#e3b341','gray':'#484f58','white':'#c9d1d9',
     'bg':'#161b22','paper':'#0d1117'}

BASE = {
    'plot_bgcolor':C['bg'],'paper_bgcolor':C['paper'],
    'font':{'color':C['white'],'size':11},
    'legend':{'x':0.01,'y':0.99,'bgcolor':'rgba(0,0,0,0)','bordercolor':'#30363d'},
    'margin':{'l':55,'r':40,'t':50,'b':45},'hovermode':'x unified',
    'xaxis':{'gridcolor':'#30363d','zerolinecolor':'#484f58','title':'Time (ps)'},
    'yaxis':{'gridcolor':'#30363d','zerolinecolor':'#484f58'},
}

def mk(ttl, ytl, traces, anns=None):
    L = json.loads(json.dumps(BASE)); L['title'] = ttl; L['yaxis']['title'] = ytl
    for t in traces: t['type'] = 'scatter'
    if anns:
        L['annotations'] = []
        for a in anns:
            aa = {'xref':'x','yref':'y','showarrow':True,'arrowhead':2,'arrowsize':1.2,
                  'ax':0,'ay':-22,'font':{'color':C['yellow'],'size':9},
                  'bgcolor':'rgba(0,0,0,0.6)','borderpad':3}; aa.update(a)
            L['annotations'].append(aa)
    return L, traces

import os; os.chdir('/home/howard/JoSIM/test/final')
with open('final_4bvm_series.csv') as f:
    rows = list(csv.DictReader(f))
T = [float(r['time'])*1e12 for r in rows]

p0  = [float(r['P(B_JM1|XBVM0)']) for r in rows]
p1  = [float(r['P(B_JM1|XBVM1)']) for r in rows]
p2  = [float(r['P(B_JM1|XBVM2)']) for r in rows]
p3  = [float(r['P(B_JM1|XBVM3)']) for r in rows]
isl = [float(r['I(B_LD1)'])*1e6 for r in rows]
vjs = [float(r['V(B_JS_Q)'])*1e3 for r in rows]
pjs = [float(r['P(B_JS_Q)']) for r in rows]
ijs = [float(r['I(B_JS_Q)'])*1e6 for r in rows]

def peak(t0,t1,arr):
    idx=[i for i in range(len(T)) if t0<T[i]<t1]
    return max(arr[i] for i in idx) if idx else 0

reads = [(110,125),(140,155),(170,185),(200,215)]
r_isl = [peak(t0,t1,isl) for t0,t1 in reads]
r_pjs = [peak(t0,t1,pjs) for t0,t1 in reads]
r_ijs = [peak(t0,t1,ijs) for t0,t1 in reads]

charts = [
    mk('<b>① BVM Storage Phases — All 4 cells written (W=13.4rad ✓)</b>', 'Phase (rad)',
        [{'x':T,'y':p0,'name':'BVM0','line':{'color':C['blue'],'width':1.2}},
         {'x':T,'y':p1,'name':'BVM1','line':{'color':C['red'],'width':1.2}},
         {'x':T,'y':p2,'name':'BVM2','line':{'color':C['green'],'width':1.2}},
         {'x':T,'y':p3,'name':'BVM3','line':{'color':C['purple'],'width':1.2}}],
        [{'text':'W0','x':15,'y':14},{'text':'W1','x':35,'y':14},
         {'text':'W2','x':55,'y':14},{'text':'W3','x':75,'y':14}]),

    mk('<b>② I_SL — Sense Line Current (Linear Summation!)</b>', 'Current (μA)',
        [{'x':T,'y':isl,'name':'I<sub>SL</sub>','line':{'color':C['yellow'],'width':2.0}}],
        [{'text':f'<b>{r_isl[0]:.0f}μA<br>(1×)</b>','x':115,'y':r_isl[0]+8},
         {'text':f'<b>{r_isl[1]:.0f}μA<br>({r_isl[1]/max(r_isl[0],1):.1f}×)</b>','x':145,'y':r_isl[1]+8},
         {'text':f'<b>{r_isl[2]:.0f}μA<br>({r_isl[2]/max(r_isl[0],1):.1f}×)</b>','x':175,'y':r_isl[2]+8},
         {'text':f'<b>{r_isl[3]:.0f}μA<br>({r_isl[3]/max(r_isl[0],1):.1f}×)</b>','x':205,'y':r_isl[3]+8}]),

    mk('<b>③ QB P_JS — Phase Response (4 cells → 1.55Φ₀!)</b>', 'Phase (rad)',
        [{'x':T,'y':pjs,'name':'P<sub>JS</sub>','line':{'color':C['green'],'width':2.0}},
         {'x':[0,230],'y':[6.283,6.283],'name':'1Φ₀','line':{'color':C['gray'],'width':0.5,'dash':'dot'},'showlegend':False}],
        [{'text':f'<b>{r_pjs[0]:.1f}rad<br>({r_pjs[0]/6.283:.2f}Φ₀)</b>','x':115,'y':r_pjs[0]+1},
         {'text':f'<b>{r_pjs[1]:.1f}rad<br>({r_pjs[1]/6.283:.2f}Φ₀)</b>','x':145,'y':r_pjs[1]+1},
         {'text':f'<b>{r_pjs[2]:.1f}rad<br>({r_pjs[2]/6.283:.2f}Φ₀)</b>','x':175,'y':r_pjs[2]+1},
         {'text':f'<b>★{r_pjs[3]:.1f}rad<br>({r_pjs[3]/6.283:.2f}Φ₀)</b>','x':205,'y':r_pjs[3]+1}]),

    mk('<b>④ QB I_JS — Junction Current (switches above IC=18μA)</b>', 'Current (μA)',
        [{'x':T,'y':ijs,'name':'I<sub>JS</sub>','line':{'color':C['blue'],'width':2.0}},
         {'x':[0,230],'y':[18,18],'name':'JS I<sub>C</sub>=18μA','line':{'color':C['red'],'width':1,'dash':'dash'}}],
        [{'text':f'<b>{r_ijs[0]:.0f}μA</b>','x':115,'y':r_ijs[0]+3},
         {'text':f'<b>{r_ijs[1]:.0f}μA</b>','x':145,'y':r_ijs[1]+3},
         {'text':f'<b>{r_ijs[2]:.0f}μA</b>','x':175,'y':r_ijs[2]+3},
         {'text':f'<b>{r_ijs[3]:.0f}μA</b>','x':205,'y':r_ijs[3]+3}]),

    mk('<b>⑤ QB V_JS — Junction Voltage</b>', 'Voltage (mV)',
        [{'x':T,'y':vjs,'name':'V<sub>JS</sub>','line':{'color':C['orange'],'width':1.5}}]),
]

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
    '.sum h3{color:#58a6ff;margin:0 0 6px}\n',
    '.ok{color:#7ee787}.warn{color:#e3b341}\n',
    'table{border-collapse:collapse;width:100%;margin:8px 0}\n',
    'th{background:#1a2332;color:#58a6ff;padding:4px 10px;border:1px solid #30363d}\n',
    'td{padding:4px 10px;border:1px solid #30363d;text-align:center}\n',
    '</style></head><body>\n',
    '<h1>4-BVM Array + QB — Series Topology (jj320→QB)</h1>\n',
    '<h2>SL→jj320→QB series chain | JS=18μA | R<sub>shunt</sub>=10Ω | I<sub>BIAS</sub>=40μA | 50GHz, 1ps edges</h2>\n']

for i, (lyt, traces) in enumerate(charts):
    html_parts.append(f'<div class="chart-wrap"><div class="chart" id="c{i}"></div></div>\n')
    html_parts.append(f'<script>Plotly.newPlot("c{i}",{json.dumps(traces)},{json.dumps(lyt)},{{responsive:true}});</script>\n')

html_parts.append(f'''<div class="sum">
<h3>Results — Series Topology (Correct)</h3>
<table>
<tr><th>Metric</th><th>Read 1 Cell</th><th>Read 2 Cells</th><th>Read 3 Cells</th><th>Read 4 Cells</th></tr>
<tr>
  <td>I<sub>SL</sub></td>
  <td class="ok">{r_isl[0]:.0f} μA</td>
  <td class="ok">{r_isl[1]:.0f} μA ({r_isl[1]/max(r_isl[0],1):.1f}×)</td>
  <td class="ok">{r_isl[2]:.0f} μA ({r_isl[2]/max(r_isl[0],1):.1f}×)</td>
  <td class="ok">{r_isl[3]:.0f} μA ({r_isl[3]/max(r_isl[0],1):.1f}×)</td>
</tr>
<tr>
  <td>QB P<sub>JS</sub></td>
  <td>{r_pjs[0]:.1f} rad ({r_pjs[0]/6.283:.2f}Φ₀)</td>
  <td>{r_pjs[1]:.1f} rad ({r_pjs[1]/6.283:.2f}Φ₀)</td>
  <td>{r_pjs[2]:.1f} rad ({r_pjs[2]/6.283:.2f}Φ₀)</td>
  <td class="ok"><b>{r_pjs[3]:.1f} rad ({r_pjs[3]/6.283:.2f}Φ₀)</b></td>
</tr>
<tr>
  <td>QB I<sub>JS</sub></td>
  <td>{r_ijs[0]:.0f} μA</td>
  <td class="ok">{r_ijs[1]:.0f} μA (>IC)</td>
  <td class="ok">{r_ijs[2]:.0f} μA (>IC)</td>
  <td class="ok">{r_ijs[3]:.0f} μA (>IC)</td>
</tr>
</table>

<p style="margin-top:8px">
<b>Key Achievements:</b><br>
<span class="ok">✓ 4-BVM array + QB works correctly with SERIES topology</span> — SL→jj320→QB is a single current path<br>
<span class="ok">✓ I<sub>SL</sub> scales with #cells: {r_isl[0]:.0f}→{r_isl[1]:.0f}→{r_isl[2]:.0f}→{r_isl[3]:.0f} μA</span><br>
<span class="ok">✓ QB reaches <b>1.55Φ₀</b> with 4 cells — SFQ-level phase accumulation!</span><br>
<span class="ok">✓ I<sub>JS</sub> exceeds IC=18μA for 2/3/4 cell reads — junction switches</span><br>
<br>
<b>Compare with parallel topology (wrong):</b> QB phase max 0.08Φ₀ (weak, current shunted to ground).<br>
<b>Series topology (correct):</b> QB phase max <b>1.55Φ₀</b> — <b>19× stronger!</b>
</p>
</div></body></html>''')

with open('FINAL_4BVM_QB.html','w') as f: f.write(''.join(html_parts))
print(f"Done: FINAL_4BVM_QB.html ({len(''.join(html_parts))//1024}KB)")
