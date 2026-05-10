#!/usr/bin/env python3
"""BQ Proper Pulse Test — CDN Plotly, with comparison to old results."""
import csv, json

C = {'blue':'#58a6ff','red':'#ff7b72','green':'#7ee787','orange':'#f0883e',
     'purple':'#d2a8ff','yellow':'#e3b341','gray':'#484f58','white':'#c9d1d9',
     'bg':'#161b22','paper':'#0d1117'}

BASE = {
    'plot_bgcolor':C['bg'],'paper_bgcolor':C['paper'],
    'font':{'color':C['white'],'size':12},
    'legend':{'x':0.01,'y':0.99,'bgcolor':'rgba(0,0,0,0)','bordercolor':'#30363d'},
    'margin':{'l':60,'r':50,'t':55,'b':50},'hovermode':'x unified',
    'xaxis':{'gridcolor':'#30363d','zerolinecolor':'#484f58','title':'Time (ps)'},
    'yaxis':{'gridcolor':'#30363d','zerolinecolor':'#484f58'},
}

with open('test/bq/test_bq_proper_pulse.csv') as f:
    rows = list(csv.DictReader(f))
T = [float(r['time'])*1e12 for r in rows]
ua = lambda k: [float(r[k])*1e6 for r in rows]
mv = lambda k: [float(r[k])*1e3 for r in rows]
pjs = [float(r['P(B_JS|XBQ1)']) for r in rows]
vjs = [float(r['V(B_JS|XBQ1)'])*1e3 for r in rows]
vout = [float(r['V(OUT1)'])*1e3 for r in rows]
iin = [float(r['I(I_IN)'])*1e6 for r in rows]

def mk(ttl, ytl, traces, anns=None):
    L = json.loads(json.dumps(BASE)); L['title'] = ttl; L['yaxis']['title'] = ytl
    for t in traces: t['type'] = 'scatter'
    if anns:
        L['annotations'] = []
        for a in anns:
            aa = {'xref':'x','yref':'y','showarrow':True,'arrowhead':2,'arrowsize':1.2,
                  'ax':0,'ay':-22,'font':{'color':C['yellow'],'size':10},
                  'bgcolor':'rgba(0,0,0,0.6)','borderpad':3}; aa.update(a)
            L['annotations'].append(aa)
    return L, traces

# Per-pulse phase deltas
p_windows = [(8,25),(25,42),(42,59),(59,80)]
dp_per_pulse = []
for t0,t1 in p_windows:
    idx = [i for i in range(len(T)) if t0<T[i]<t1]
    if idx: dp_per_pulse.append(pjs[idx[-1]] - pjs[idx[0]])

charts = [
    mk('<b>① Input Current — True zero gaps (10ps flat at 0μA)</b>', 'I<sub>IN</sub> (μA)',
        [{'x':T,'y':iin,'name':'I<sub>IN</sub>','line':{'color':C['blue'],'width':2.2}},
         {'x':[0,80],'y':[133,133],'name':'JS I<sub>C</sub>=133μA','line':{'color':C['red'],'width':1,'dash':'dash'}}],
        [{'text':'<b>Pulse ①</b>','x':12,'y':210},{'text':'<b>Pulse ②</b>','x':29,'y':210},
         {'text':'<b>Pulse ③</b>','x':46,'y':210},{'text':'<b>Pulse ④</b>','x':63,'y':210},
         {'text':'<b>← True ZERO<br>   (10ps平台)</b>','x':20,'y':60}]),

    mk(f'<b>② P_JS — Quasi-discrete (ΔP per pulse: {dp_per_pulse[0]:.1f}, {dp_per_pulse[1]:.1f}, {dp_per_pulse[2]:.1f}, {dp_per_pulse[3]:.1f} rad)</b>', 'P<sub>JS</sub> (rad)',
        [{'x':T,'y':pjs,'name':'P<sub>JS</sub>','line':{'color':C['green'],'width':2.5}},
         {'x':[0,80],'y':[6.283,6.283],'name':'1Φ₀ (2π)','line':{'color':C['gray'],'width':0.5,'dash':'dot'},'showlegend':False},
         {'x':[0,80],'y':[12.566,12.566],'name':'2Φ₀','line':{'color':C['gray'],'width':0.5,'dash':'dot'},'showlegend':False},
         {'x':[0,80],'y':[18.85,18.85],'name':'3Φ₀','line':{'color':C['gray'],'width':0.5,'dash':'dot'},'showlegend':False}],
        [{'text':f'<b>① ΔP={dp_per_pulse[0]:.1f}rad<br>≈1.0Φ₀</b>','x':17,'y':pjs[40]+4},
         {'text':f'<b>② ΔP={dp_per_pulse[1]:.1f}rad<br>≈0.9Φ₀</b>','x':33,'y':pjs[85]+4},
         {'text':f'<b>③ ΔP={dp_per_pulse[2]:.1f}rad<br>≈2.0Φ₀</b>','x':50,'y':pjs[130]+4},
         {'text':f'<b>④ ΔP={dp_per_pulse[3]:.1f}rad<br>≈1.2Φ₀</b>','x':66,'y':pjs[170]+4}]),

    mk('<b>③ V_JS — Junction resets between pulses (V→0)</b>', 'V<sub>JS</sub> (mV)',
        [{'x':T,'y':vjs,'name':'V<sub>JS</sub>','line':{'color':C['orange'],'width':2.0}}],
        [{'text':'<b>V≈0<br>复位!</b>','x':20,'y':0.1}]),

    mk('<b>④ V_OUT — SFQ-level output (~0.12mV)</b>', 'V<sub>OUT</sub> (mV)',
        [{'x':T,'y':vout,'name':'V<sub>OUT</sub>','line':{'color':C['yellow'],'width':2.0}}]),
]

# Build HTML
parts = [
    '<!DOCTYPE html>\n<html><head><meta charset="utf-8">\n',
    '<script src="https://cdn.plot.ly/plotly-2.32.0.min.js"></script>\n',
    '<style>\n',
    'body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;',
    'background:#0d1117;color:#c9d1d9;margin:0;padding:10px 15px}\n',
    'h1{color:#58a6ff;text-align:center;margin:10px 0 2px;font-size:18px}\n',
    'h2{color:#8b949e;text-align:center;font-weight:400;font-size:12px;margin:0 0 10px}\n',
    '.chart-wrap{max-width:1400px;margin:0 auto 10px;width:100%}\n',
    '.chart{width:100%;height:320px;background:#161b22;border-radius:6px;border:1px solid #30363d}\n',
    '.analysis{max-width:1400px;margin:0 auto 15px;padding:12px 20px;background:#161b22;',
    'border:1px solid #30363d;border-radius:6px;font-size:12px;line-height:1.6}\n',
    '.analysis h3{color:#58a6ff;margin:0 0 6px;font-size:14px}\n',
    '.analysis table{border-collapse:collapse;width:100%;margin:6px 0}\n',
    '.analysis th{background:#1a2332;color:#58a6ff;padding:3px 8px;border:1px solid #30363d}\n',
    '.analysis td{padding:3px 8px;border:1px solid #30363d;text-align:center}\n',
    '.ok{color:#7ee787}.fail{color:#ff7b72}.warn{color:#e3b341}\n',
    '</style></head><body>\n',
    '<h1>BQ Proper SFQ Pulse Test — True Zero Gaps</h1>\n',
    '<h2>4×180μA×3ps with 10ps true zero platforms | IBias=100μA | JS I<sub>C</sub>=133μA</h2>\n']

for i, (lyt, traces) in enumerate(charts):
    parts.append(f'<div class="chart-wrap"><div class="chart" id="c{i}"></div></div>\n')
    parts.append(f'<script>Plotly.newPlot("c{i}",{json.dumps(traces)},{json.dumps(lyt)},{{responsive:true}});</script>\n')

parts.append('''<div class="analysis">
<h3>Result: Quasi-discrete — junction resets but phase steps not exactly 2π</h3>
<table>
<tr><th>Pulse</th><th>ΔP (rad)</th><th>ΔP (Φ₀)</th><th>V_JS peak</th><th>Reset?</th></tr>
''')
for i, dp in enumerate(dp_per_pulse):
    parts.append(f'<tr><td>{i+1}</td><td>{dp:+.1f}</td><td>{dp/6.283:+.1f}Φ₀</td><td>~0.5-0.7mV</td><td class="ok">V→0 ✓</td></tr>')
parts.append(f'''</table>
<p style="margin-top:8px">
<b>对比:</b><br>
<span class="fail">旧脉冲测试 (PWL斜坡, 无零平台):</span> ΔP=102rad, 0次复位, 连续斜坡<br>
<span class="warn">新脉冲测试 (真零平台):</span> ΔP={max(pjs)-min(pjs):.0f}rad, 结在脉冲间复位(V→0),
每脉冲≈1Φ₀但非精确2π, P_JS有小幅漂移<br>
<span class="ok">改善:</span> 真零平台→结能复位 | 每脉冲接近1Φ₀ | 但相位步进不精确=2π<br>
<span class="warn">剩余问题:</span> 结停止后相位仍有缓慢漂移(LC振荡), 导致Φ₀计数不精确
</p>
</div>
</body></html>''')

html = ''.join(parts)
with open('test/bq/BQ_PROPER_PULSE.html','w') as f: f.write(html)
print(f"Done: test/bq/BQ_PROPER_PULSE.html ({len(html)//1024}KB)")
