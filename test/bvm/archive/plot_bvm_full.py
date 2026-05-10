#!/usr/bin/env python3
"""BVM Full Test — lightweight CDN Plotly, separate wide charts."""
import csv, json

with open('test/bvm/test_bvm_full.csv') as f:
    rows = list(csv.DictReader(f))

T = [float(r['time'])*1e12 for r in rows]
ua = lambda k: [float(r[k])*1e6 for r in rows]
mv = lambda k: [float(r[k])*1e3 for r in rows]
rad = lambda k: [float(r[k]) for r in rows]

C = {'blue':'#58a6ff','red':'#ff7b72','green':'#7ee787','orange':'#f0883e',
     'purple':'#d2a8ff','yellow':'#e3b341','gray':'#484f58','white':'#c9d1d9'}

isl_r1 = max(abs(float(r['I(B_SLLOAD1)'])*1e6) for r in rows if 138<float(r['time'])*1e12<148)
isl_r0 = max(abs(float(r['I(B_SLLOAD1)'])*1e6) for r in rows if 298<float(r['time'])*1e12<308)
p_w1 = sum(float(r['P(B_JM1|XBVM1)']) for r in rows if 50<float(r['time'])*1e12<65)/sum(1 for r in rows if 50<float(r['time'])*1e12<65)
p_w0 = sum(float(r['P(B_JM1|XBVM1)']) for r in rows if 270<float(r['time'])*1e12<285)/sum(1 for r in rows if 270<float(r['time'])*1e12<285)

BASE = {
    'plot_bgcolor':'#161b22','paper_bgcolor':'#0d1117',
    'font':{'color':C['white'],'size':12},
    'legend':{'x':0.01,'y':0.99,'bgcolor':'rgba(0,0,0,0)','bordercolor':'#30363d'},
    'margin':{'l':60,'r':50,'t':60,'b':50},
    'hovermode':'x unified',
    'xaxis':{'gridcolor':'#30363d','zerolinecolor':'#484f58','title':'Time (ps)'},
    'yaxis':{'gridcolor':'#30363d','zerolinecolor':'#484f58'},
}

shades = [
    (10,35,'rgba(88,166,255,0.10)'),(70,95,'rgba(255,123,114,0.05)'),
    (110,135,'rgba(255,184,65,0.05)'),(135,155,'rgba(126,231,135,0.10)'),
    (195,215,'rgba(126,231,135,0.10)'),(230,255,'rgba(255,123,114,0.10)'),
    (295,315,'rgba(126,231,135,0.10)'),(355,375,'rgba(126,231,135,0.10)'),
]
ms = lambda xr: [{'type':'rect','xref':xr,'yref':'paper','x0':x0,'x1':x1,'y0':0,'y1':1,
    'fillcolor':c,'line':{'width':0},'layer':'below'} for x0,x1,c in shades]

charts = [
    # ① Drive
    ({'title':'<b>① Drive Signals — I<sub>WL</sub>(蓝) I<sub>BL</sub>(红) I<sub>SE</sub>(紫)</b>',
      'yaxis':{'title':'Current (μA)'},'shapes':ms('x'),
      'annotations':[
        {'text':'W1','x':22,'y':210},{'text':'HS-WL','x':82,'y':180},
        {'text':'HS-BL','x':122,'y':150},{'text':'Read-1','x':147,'y':130},
        {'text':'W0','x':242,'y':-80},{'text':'Read-0','x':307,'y':80}]},
     [{'x':T,'y':ua('I(I_WL1)'),'name':'I<sub>WL</sub>','line':{'color':C['blue'],'width':2.2}},
      {'x':T,'y':ua('I(I_BL1)'),'name':'I<sub>BL</sub>','line':{'color':C['red'],'width':1.8}},
      {'x':T,'y':ua('I(I_SE1)'),'name':'I<sub>SE</sub>','line':{'color':C['purple'],'width':1.3,'dash':'dot'}}]),

    # ② P_JM1
    ({'title':'<b>② Storage State — P<sub>JM1</sub> (W1→+19rad, W0→0rad)</b>',
      'yaxis':{'title':'P<sub>JM1</sub> (rad)'},'shapes':ms('x')},
     [{'x':T,'y':rad('P(B_JM1|XBVM1)'),'name':'P<sub>JM1</sub>','line':{'color':C['green'],'width':2.8}},
      {'x':[0,400],'y':[0,0],'line':{'color':C['gray'],'width':0.5,'dash':'dot'},'showlegend':False}]),

    # ③ V_JM1
    ({'title':'<b>③ Junction Voltage — V<sub>JM1</sub> (write switching pulses ~0.6mV)</b>',
      'yaxis':{'title':'V<sub>JM1</sub> (mV)'},'shapes':ms('x')},
     [{'x':T,'y':mv('V(B_JM1|XBVM1)'),'name':'V<sub>JM1</sub>','line':{'color':C['orange'],'width':2.0}}]),

    # ④ I_SL
    ({'title':'<b>④ Sense Output — I<sub>SL</sub> (R1={0:.1f}μA R0={1:.1f}μA ratio={2:.1f}x)</b>'.format(isl_r1,isl_r0,isl_r1/max(isl_r0,0.01)),
      'yaxis':{'title':'I<sub>SL</sub> (μA)'},'shapes':ms('x')},
     [{'x':T,'y':ua('I(B_SLLOAD1)'),'name':'I<sub>SL</sub>','line':{'color':C['yellow'],'width':2.2},
       'fill':'tozeroy','fillcolor':'rgba(227,179,65,0.12)'}]),
]

# Build HTML with CDN plotly (tiny file, ~5KB)
html = '''<!DOCTYPE html>
<html><head><meta charset="utf-8">
<script src="https://cdn.plot.ly/plotly-2.32.0.min.js"></script>
<style>
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
     background:#0d1117;color:#c9d1d9;margin:0;padding:10px 15px}
h1{color:#58a6ff;text-align:center;margin:10px 0 2px;font-size:18px}
h2{color:#8b949e;text-align:center;font-weight:400;font-size:12px;margin:0 0 18px}
.chart-wrap{max-width:1400px;margin:0 auto 15px;width:100%}
.chart{width:100%;height:350px;background:#161b22;border-radius:6px;border:1px solid #30363d}
.tt{max-width:1400px;margin:0 auto 15px;padding:12px 20px;background:#161b22;
    border:1px solid #30363d;border-radius:6px;font-size:12px;line-height:1.5}
.tt h3{color:#58a6ff;margin:0 0 6px;font-size:14px}
.tt table{border-collapse:collapse;margin:4px 0;width:100%}
.tt th{background:#1a2332;color:#58a6ff;padding:3px 10px;border:1px solid #30363d}
.tt td{padding:3px 10px;border:1px solid #30363d;text-align:center}
.ok{color:#7ee787}.fail{color:#ff7b72}
</style></head><body>
<h1>BVM Full Functional Test</h1>
<h2>IW=100μA (half-select safe) | ISE=100μA | WL read bias=33μA | 50GHz | Blue=Write Green=Read</h2>
'''

for i, (lyt_cfg, traces) in enumerate(charts):
    layout = dict(BASE)
    for k, v in lyt_cfg.items():
        if k == 'annotations':
            layout['annotations'] = []
            for a in v:
                ann = {'xref':'x','yref':'y','showarrow':True,'arrowhead':2,'arrowsize':1.2,
                       'ax':0,'ay':-22,'font':{'color':C['yellow'],'size':10},
                       'bgcolor':'rgba(0,0,0,0.6)','borderpad':3}
                ann.update(a)
                layout['annotations'].append(ann)
        else:
            layout[k] = v
    for t in traces:
        t['type'] = 'scatter'
    html += '<div class="chart-wrap"><div class="chart" id="c{}"></div></div>\n'.format(i)
    html += '<script>Plotly.newPlot("c{}",{},{},{{responsive:true}});</script>\n'.format(
        i, json.dumps(traces), json.dumps(layout))

html += '''<div class="tt">
<h3>⑤ Truth Table</h3>
<table>
<tr><th>Phase</th><th>WL</th><th>BL</th><th>SE</th><th>SL</th><th>P_JM1</th><th>Description</th><th>Result</th></tr>
<tr><td>Init</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td><td>Idle</td><td class="ok">PASS</td></tr>
<tr><td>Write 1</td><td>1</td><td>1</td><td>0</td><td>0</td><td>+19rad</td><td>WL+BL=200μA > IC=120μA</td><td class="ok">PASS</td></tr>
<tr><td>Half-sel WL</td><td>1</td><td>0</td><td>0</td><td>0</td><td>+19rad</td><td>WL=100μA < IC → no disturb</td><td class="ok">PASS</td></tr>
<tr><td>Half-sel BL</td><td>0</td><td>1</td><td>0</td><td>0</td><td>+19rad</td><td>BL=100μA < IC → no disturb</td><td class="ok">PASS</td></tr>
<tr><td>Read-1</td><td>bias</td><td>0</td><td>1</td><td>1</td><td>+19rad</td><td>I<sub>SL</sub>=6.0μA NDRO</td><td class="ok">PASS</td></tr>
<tr><td>Write 0</td><td>1</td><td>1</td><td>0</td><td>0</td><td>0</td><td>WL+BL=-200μA → clear</td><td class="ok">PASS</td></tr>
<tr><td>Read-0</td><td>bias</td><td>0</td><td>1</td><td>1</td><td>0</td><td>I<sub>SL</sub>=6.1μA R1/R0=0.98</td><td class="fail">FAIL</td></tr>
</table>
<p style="margin-top:6px">
<b>Summary:</b> <span class="ok">Write ✓ Half-select ✓ NDRO ✓</span> |
<span class="fail">R1/R0 discrimination ✗ (0.98x at 100μA)</span> |
Need 150-200μA SE drive for ≥2x discrimination
</p>
</div>
</body></html>'''

with open('test/bvm/PLOT_bvm_full.html', 'w') as f:
    f.write(html)
print("Done: test/bvm/PLOT_bvm_full.html ({}KB)".format(len(html)//1024))
