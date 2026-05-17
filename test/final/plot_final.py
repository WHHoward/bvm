#!/usr/bin/env python3
"""Final BVM + QB visualization — CDN Plotly."""
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

# === BVM ===
with open('bvm/bvm_final.csv') as f:
    rows = list(csv.DictReader(f))
Tb = [float(r['time'])*1e12 for r in rows]
iwl = [float(r['I(I_WL1)'])*1e6 for r in rows]
ibl = [float(r['I(I_BL1)'])*1e6 for r in rows]
ise = [float(r['I(I_SE1)'])*1e6 for r in rows]
pjm1 = [float(r['P(B_JM1|XBVM1)']) for r in rows]
ilm1 = [float(r['I(L_M1|XBVM1)'])*1e6 for r in rows]
isl_b = [float(r['I(B_LD1)'])*1e6 for r in rows]

charts_bvm = [
    mk('<b>BVM ① Word/Bit/SE Lines (50GHz, 1ps edges)</b>', 'Current (μA)',
        [{'x':Tb,'y':iwl,'name':'WL','line':{'color':C['blue'],'width':1.5}},
         {'x':Tb,'y':ibl,'name':'BL','line':{'color':C['red'],'width':1.5}},
         {'x':Tb,'y':ise,'name':'SE','line':{'color':C['green'],'width':1.5}}]),
    mk('<b>BVM ② P_JM1 — Storage Loop Phase</b>', 'Phase (rad)',
        [{'x':Tb,'y':pjm1,'name':'P<sub>JM1</sub>','line':{'color':C['green'],'width':2.0}},
         {'x':[0,280],'y':[0,0],'name':'Zero','line':{'color':C['gray'],'width':0.5,'dash':'dot'},'showlegend':False}]),
    mk('<b>BVM ③ I(LM1) — Storage Loop Current</b>', 'Current (μA)',
        [{'x':Tb,'y':ilm1,'name':'I(L<sub>M1</sub>)','line':{'color':C['orange'],'width':2.0}}]),
    mk('<b>BVM ④ I_SL — Sense Line Output (Read-1={:.0f}μA, Read-0={:.0f}μA, Ratio={:.1f}x)</b>'.format(
        max([isl_b[i] for i in range(len(Tb)) if 90<Tb[i]<110]),
        max([isl_b[i] for i in range(len(Tb)) if 210<Tb[i]<230]),
        max([isl_b[i] for i in range(len(Tb)) if 90<Tb[i]<110]) / max(max([isl_b[i] for i in range(len(Tb)) if 210<Tb[i]<230]), 1)),
        'Current (μA)',
        [{'x':Tb,'y':isl_b,'name':'I<sub>SL</sub>','line':{'color':C['yellow'],'width':2.0}}]),
]

# === QB ===
with open('qb/qb_final.csv') as f:
    rows = list(csv.DictReader(f))
Tq = [float(r['time'])*1e12 for r in rows]
iin = [float(r['I(I_IN)'])*1e6 for r in rows]
vout = [float(r['V(OUT1)'])*1e3 for r in rows]
vjs = [float(r['V(B_JS1)'])*1e3 for r in rows]
pjs = [float(r['P(B_JS1)']) for r in rows]
vjl1 = [float(r['V(B_JL11)'])*1e3 for r in rows]
vjl2 = [float(r['V(B_JL21)'])*1e3 for r in rows]

# Per-pulse phase
def find_pulses(T, pjs, windows):
    peaks = []
    for t0,t1 in windows:
        idx = [i for i,t in enumerate(T) if t0<t<t1]
        if idx: peaks.append(max(pjs[i] for i in idx))
    return peaks

windows = [(28,52),(52,74),(74,98),(98,120)]
peaks = find_pulses(Tq, pjs, windows)
dp_inc = [peaks[0]]
for i in range(1,len(peaks)):
    dp_inc.append(peaks[i]-peaks[i-1])

charts_qb = [
    mk('<b>QB ① Input — BVM-Matched Currents (0/32/64/96/128μA × 10ps)</b>', 'I<sub>IN</sub> (μA)',
        [{'x':Tq,'y':iin,'name':'I<sub>IN</sub>','line':{'color':C['blue'],'width':2.0}},
         {'x':[0,130],'y':[25,25],'name':'JS I<sub>C</sub>=25μA','line':{'color':C['red'],'width':1,'dash':'dash'}}]),
    mk('<b>QB ② P_JS — Quasi-Discrete (ΔP per level: {:.1f}/{:.1f}/{:.1f}/{:.1f} rad)</b>'.format(*dp_inc),
        'P<sub>JS</sub> (rad)',
        [{'x':Tq,'y':pjs,'name':'P<sub>JS</sub>','line':{'color':C['green'],'width':2.5}},
         {'x':[0,130],'y':[6.283,6.283],'name':'1Φ₀','line':{'color':C['gray'],'width':0.5,'dash':'dot'},'showlegend':False},
         {'x':[0,130],'y':[12.566,12.566],'name':'2Φ₀','line':{'color':C['gray'],'width':0.5,'dash':'dot'},'showlegend':False},
         {'x':[0,130],'y':[18.85,18.85],'name':'3Φ₀','line':{'color':C['gray'],'width':0.5,'dash':'dot'},'showlegend':False}]),
    mk('<b>QB ③ V_JS — Damped Switching + Reset between pulses</b>', 'V<sub>JS</sub> (mV)',
        [{'x':Tq,'y':vjs,'name':'V<sub>JS</sub>','line':{'color':C['orange'],'width':2.0}},
         {'x':[0,130],'y':[0,0],'name':'V=0','line':{'color':C['red'],'width':0.5,'dash':'dot'},'showlegend':False}]),
    mk('<b>QB ④ V_OUT — Output Response</b>', 'V<sub>OUT</sub> (mV)',
        [{'x':Tq,'y':vout,'name':'V<sub>OUT</sub>','line':{'color':C['yellow'],'width':2.0}}]),
    mk('<b>QB ⑤ V_JL1 & V_JL2 — Bias Junctions</b>', 'Voltage (mV)',
        [{'x':Tq,'y':vjl1,'name':'V<sub>JL1</sub>','line':{'color':C['purple'],'width':1.5}},
         {'x':Tq,'y':vjl2,'name':'V<sub>JL2</sub>','line':{'color':C['blue'],'width':1.5}}]),
]

# Build HTML
parts = [
    '<!DOCTYPE html>\n<html><head><meta charset="utf-8">\n',
    '<script src="https://cdn.plot.ly/plotly-2.32.0.min.js"></script>\n',
    '<style>\n',
    'body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;',
    'background:#0d1117;color:#c9d1d9;margin:0;padding:10px 15px}\n',
    'h1{color:#58a6ff;text-align:center;margin:15px 0 2px;font-size:20px}\n',
    'h2{color:#8b949e;text-align:center;font-weight:400;font-size:13px;margin:0 0 15px}\n',
    'h3{color:#58a6ff;margin:30px 0 5px 10px;font-size:16px}\n',
    '.chart-wrap{max-width:1400px;margin:0 auto 10px;width:100%}\n',
    '.chart{width:100%;height:300px;background:#161b22;border-radius:6px;border:1px solid #30363d}\n',
    '</style></head><body>\n',
    '<h1>BVM + QB Final Functional Tests</h1>\n',
    '<h2>BVM: 50GHz/1ps edges, Paper Fig.2(b) | QB: JS=25μA+R<sub>shunt</sub>=10Ω, BVM-Matched 10ps Pulses</h2>\n',
    '<h3>BVM — Memory Cell</h3>\n']

for i, (lyt, traces) in enumerate(charts_bvm):
    parts.append(f'<div class="chart-wrap"><div class="chart" id="bv{i}"></div></div>\n')
    parts.append(f'<script>Plotly.newPlot("bv{i}",{json.dumps(traces)},{json.dumps(lyt)},{{responsive:true}});</script>\n')

parts.append('<h3>QB — Quantizer Buffer</h3>\n')
for i, (lyt, traces) in enumerate(charts_qb):
    parts.append(f'<div class="chart-wrap"><div class="chart" id="qb{i}"></div></div>\n')
    parts.append(f'<script>Plotly.newPlot("qb{i}",{json.dumps(traces)},{json.dumps(lyt)},{{responsive:true}});</script>\n')

html = ''.join(parts)
with open('FINAL_RESULTS.html','w') as f: f.write(html)
print(f"Done: FINAL_RESULTS.html ({len(html)//1024}KB)")
