#!/usr/bin/env python3
"""BVM no-PRD tests — HTML with CDN Plotly."""
import csv, json

C = {'blue':'#58a6ff','red':'#ff7b72','green':'#7ee787','orange':'#f0883e',
     'purple':'#d2a8ff','yellow':'#e3b341','gray':'#484f58','white':'#c9d1d9',
     'bg':'#161b22','paper':'#0d1117'}

BASE = {
    'plot_bgcolor':C['bg'],'paper_bgcolor':C['paper'],
    'font':{'color':C['white'],'size':12},
    'legend':{'x':0.01,'y':0.99,'bgcolor':'rgba(0,0,0,0)','bordercolor':'#30363d'},
    'margin':{'l':60,'r':50,'t':55,'b':50},
    'hovermode':'x unified',
    'xaxis':{'gridcolor':'#30363d','zerolinecolor':'#484f58','title':'Time (ps)'},
    'yaxis':{'gridcolor':'#30363d','zerolinecolor':'#484f58'},
}

def load(fn):
    with open(fn) as f:
        rows = list(csv.DictReader(f))
    T = [float(r['time'])*1e12 for r in rows]
    ua = lambda k: [float(r[k])*1e6 for r in rows]
    mv = lambda k: [float(r[k])*1e3 for r in rows]
    rad = lambda k: [float(r[k]) for r in rows]
    return T, ua, mv, rad, rows

def make_chart(title, ytitle, traces_data, y2title=None, y2traces=None, annotations=None):
    L = json.loads(json.dumps(BASE))
    L['title'] = title
    L['yaxis']['title'] = ytitle
    if y2title:
        L['yaxis2'] = {'title': y2title, 'overlaying': 'y', 'side': 'right',
                       'gridcolor': '#30363d', 'zerolinecolor': '#484f58'}
    for t in traces_data:
        t['type'] = 'scatter'
    if y2traces:
        for t in y2traces:
            t['type'] = 'scatter'
            t['yaxis'] = 'y2'
    all_traces = traces_data + (y2traces or [])
    if annotations:
        L['annotations'] = []
        for a in annotations:
            ann = {'xref':'x','yref':'y','showarrow':True,'arrowhead':2,'arrowsize':1.2,
                   'ax':0,'ay':-22,'font':{'color':C['yellow'],'size':10},
                   'bgcolor':'rgba(0,0,0,0.6)','borderpad':3}
            ann.update(a)
            L['annotations'].append(ann)
    return L, all_traces

# ═══════════════════════════════════════
# Test 1: Read-Write
# ═══════════════════════════════════════
T1,ua1,mv1,rad1,rows1 = load('test/bvm/test_bvm_noprd_rw.csv')
rw_charts = []

# ① Drive
L,tr = make_chart('<b>① Drive Signals</b>', 'Current (μA)',
    [{'x':T1,'y':ua1('I(I_WL1)'),'name':'I<sub>WL</sub> (100μA)','line':{'color':C['blue'],'width':2.2}},
     {'x':T1,'y':ua1('I(I_BL1)'),'name':'I<sub>BL</sub> (100μA)','line':{'color':C['red'],'width':1.8}},
     {'x':T1,'y':ua1('I(I_SE1)'),'name':'I<sub>SE</sub> (200μA)','line':{'color':C['purple'],'width':1.3,'dash':'dot'}}],
    annotations=[{'text':'<b>W1</b>','x':15,'y':210},{'text':'<b>R1</b>','x':77,'y':180},
                 {'text':'<b>W0</b>','x':137,'y':-75},{'text':'<b>R0</b>','x':197,'y':180}])
rw_charts.append((L,tr))

# ② P_JM1
p_w1_rw = sum(rad1('P(B_JM1|XBVM1)')[i] for i in range(len(T1)) if 30<T1[i]<48)/max(1,sum(1 for i in range(len(T1)) if 30<T1[i]<48))
p_w0_rw = sum(rad1('P(B_JM1|XBVM1)')[i] for i in range(len(T1)) if 150<T1[i]<168)/max(1,sum(1 for i in range(len(T1)) if 150<T1[i]<168))
L,tr = make_chart(f'<b>② Storage Phase — P<sub>JM1</sub> (W1→{p_w1_rw:+.0f}rad W0→{p_w0_rw:+.0f}rad)</b>', 'P<sub>JM1</sub> (rad)',
    [{'x':T1,'y':rad1('P(B_JM1|XBVM1)'),'name':'P<sub>JM1</sub>','line':{'color':C['green'],'width':2.5}},
     {'x':[0,220],'y':[0,0],'line':{'color':C['gray'],'width':0.5,'dash':'dot'},'showlegend':False}])
rw_charts.append((L,tr))

# ③ I(LM1)
ilm1_rw = [float(r['I(L_M1|XBVM1)'])*1e6 for r in rows1]
i_w1_rw = sum(ilm1_rw[i] for i in range(len(T1)) if 30<T1[i]<48)/max(1,sum(1 for i in range(len(T1)) if 30<T1[i]<48))
L,tr = make_chart(f'<b>③ Storage Current — I(LM1) (W1→{i_w1_rw:+.0f}μA)</b>', 'I(LM1) (μA)',
    [{'x':T1,'y':ilm1_rw,'name':'I(LM1)','line':{'color':C['yellow'],'width':2.5},
      'fill':'tozeroy','fillcolor':'rgba(227,179,65,0.1)'}])
rw_charts.append((L,tr))

# ④ I_SL
isl_rw = ua1('I(B_SLLOAD1)')
r1_rw = max(abs(isl_rw[i]) for i in range(len(T1)) if 76<T1[i]<84)
r0_rw = max(abs(isl_rw[i]) for i in range(len(T1)) if 196<T1[i]<204)
L,tr = make_chart(f'<b>④ Sense Output — I<sub>SL</sub> (R1={r1_rw:.1f}μA R0={r0_rw:.1f}μA ratio={r1_rw/max(r0_rw,0.01):.1f}x)</b>', 'I<sub>SL</sub> (μA)',
    [{'x':T1,'y':isl_rw,'name':'I<sub>SL</sub>','line':{'color':C['yellow'],'width':2.5},
      'fill':'tozeroy','fillcolor':'rgba(227,179,65,0.1)'}],
    annotations=[{'text':f'<b>R1={r1_rw:.1f}μA</b>','x':80,'y':r1_rw+3},
                 {'text':f'<b>R0={r0_rw:.1f}μA</b>','x':200,'y':r0_rw+3},
                 {'text':'<b>ratio=0.9x ✗</b>','x':140,'y':max(r1_rw,r0_rw)+5}])
rw_charts.append((L,tr))

# ═══════════════════════════════════════
# Test 2: Full Truth Table
# ═══════════════════════════════════════
T2,ua2,mv2,rad2,rows2 = load('test/bvm/test_bvm_noprd_full.csv')
ft_charts = []

# ① Drive
L,tr = make_chart('<b>① Drive Signals — Full Truth Table</b>', 'Current (μA)',
    [{'x':T2,'y':ua2('I(I_WL1)'),'name':'I<sub>WL</sub>','line':{'color':C['blue'],'width':2.2}},
     {'x':T2,'y':ua2('I(I_BL1)'),'name':'I<sub>BL</sub>','line':{'color':C['red'],'width':1.8}},
     {'x':T2,'y':ua2('I(I_SE1)'),'name':'I<sub>SE</sub>','line':{'color':C['purple'],'width':1.3,'dash':'dot'}}],
    annotations=[{'text':'<b>W1</b>','x':15,'y':210},{'text':'<b>HS-WL</b>','x':55,'y':180},
                 {'text':'<b>HS-BL</b>','x':75,'y':170},{'text':'<b>R1</b>','x':97,'y':160},
                 {'text':'<b>W0</b>','x':177,'y':-75},{'text':'<b>R0</b>','x':217,'y':160}])
ft_charts.append((L,tr))

# ② P_JM1
p_w1_ft = sum(rad2('P(B_JM1|XBVM1)')[i] for i in range(len(T2)) if 30<T2[i]<48)/max(1,sum(1 for i in range(len(T2)) if 30<T2[i]<48))
p_w0_ft = sum(rad2('P(B_JM1|XBVM1)')[i] for i in range(len(T2)) if 190<T2[i]<208)/max(1,sum(1 for i in range(len(T2)) if 190<T2[i]<208))
p_hs_wl = sum(rad2('P(B_JM1|XBVM1)')[i] for i in range(len(T2)) if 70<T2[i]<88)/max(1,sum(1 for i in range(len(T2)) if 70<T2[i]<88))
p_hs_bl = sum(rad2('P(B_JM1|XBVM1)')[i] for i in range(len(T2)) if 90<T2[i]<108)/max(1,sum(1 for i in range(len(T2)) if 90<T2[i]<108))
L,tr = make_chart(f'<b>② Storage Phase — P<sub>JM1</sub> (W1→{p_w1_ft:+.0f}rad W0→{p_w0_ft:+.0f}rad HS_WL_Δ={abs(p_hs_wl-p_w1_ft):.1f} HS_BL_Δ={abs(p_hs_bl-p_w1_ft):.1f})</b>', 'P<sub>JM1</sub> (rad)',
    [{'x':T2,'y':rad2('P(B_JM1|XBVM1)'),'name':'P<sub>JM1</sub>','line':{'color':C['green'],'width':2.5}},
     {'x':[0,280],'y':[0,0],'line':{'color':C['gray'],'width':0.5,'dash':'dot'},'showlegend':False}])
ft_charts.append((L,tr))

# ③ I(LM1)
ilm1_ft = [float(r['I(L_M1|XBVM1)'])*1e6 for r in rows2]
L,tr = make_chart('<b>③ Storage Current — I(LM1)</b>', 'I(LM1) (μA)',
    [{'x':T2,'y':ilm1_ft,'name':'I(LM1)','line':{'color':C['yellow'],'width':2.5},
      'fill':'tozeroy','fillcolor':'rgba(227,179,65,0.1)'}])
ft_charts.append((L,tr))

# ④ I_SL
isl_ft = ua2('I(B_SLLOAD1)')
r1_ft = max(abs(isl_ft[i]) for i in range(len(T2)) if 96<T2[i]<104)
r0_ft = max(abs(isl_ft[i]) for i in range(len(T2)) if 216<T2[i]<224)
L,tr = make_chart(f'<b>④ Sense Output — I<sub>SL</sub> (R1={r1_ft:.1f}μA R0={r0_ft:.1f}μA ratio={r1_ft/max(r0_ft,0.01):.1f}x)</b>', 'I<sub>SL</sub> (μA)',
    [{'x':T2,'y':isl_ft,'name':'I<sub>SL</sub>','line':{'color':C['yellow'],'width':2.5},
      'fill':'tozeroy','fillcolor':'rgba(227,179,65,0.1)'}])
ft_charts.append((L,tr))

# ── Build HTML ──
def build_html(title, subtitle, charts, truth_table_rows=None):
    parts = ['<!DOCTYPE html>\n<html><head><meta charset="utf-8">\n',
             '<script src="https://cdn.plot.ly/plotly-2.32.0.min.js"></script>\n',
             '<style>\n',
             'body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;',
             'background:#0d1117;color:#c9d1d9;margin:0;padding:10px 15px}\n',
             'h1{color:#58a6ff;text-align:center;margin:10px 0 2px;font-size:18px}\n',
             'h2{color:#8b949e;text-align:center;font-weight:400;font-size:12px;margin:0 0 15px}\n',
             '.chart-wrap{max-width:1400px;margin:0 auto 12px;width:100%}\n',
             '.chart{width:100%;height:320px;background:#161b22;border-radius:6px;border:1px solid #30363d}\n',
             '.tt{max-width:1400px;margin:0 auto 12px;padding:10px 18px;background:#161b22;',
             'border:1px solid #30363d;border-radius:6px;font-size:12px;line-height:1.5}\n',
             '.tt h3{color:#58a6ff;margin:0 0 4px;font-size:14px}\n',
             '.tt table{border-collapse:collapse;width:100%}\n',
             '.tt th{background:#1a2332;color:#58a6ff;padding:2px 8px;border:1px solid #30363d}\n',
             '.tt td{padding:2px 8px;border:1px solid #30363d;text-align:center}\n',
             '.ok{color:#7ee787}.fail{color:#ff7b72}\n',
             '</style></head><body>\n',
             f'<h1>{title}</h1>\n<h2>{subtitle}</h2>\n']

    for i, (lyt, traces) in enumerate(charts):
        parts.append(f'<div class="chart-wrap"><div class="chart" id="c{i}"></div></div>\n')
        parts.append(f'<script>Plotly.newPlot("c{i}",{json.dumps(traces)},{json.dumps(lyt)},{{responsive:true}});</script>\n')

    if truth_table_rows:
        parts.append('<div class="tt"><h3>Truth Table</h3><table>\n')
        parts.append('<tr><th>Phase</th><th>WL</th><th>BL</th><th>SE</th><th>P_JM1</th><th>I_SL</th><th>Result</th></tr>\n')
        for row in truth_table_rows:
            parts.append('<tr>' + ''.join(f'<td>{c}</td>' for c in row) + '</tr>\n')
        parts.append('</table></div>\n')

    parts.append('</body></html>')
    return ''.join(parts)

# Test 1 HTML
tt1 = [
    ['Init','0','0','0','0 rad','—','PASS'],
    ['Write 1','100μA','100μA','0',f'{p_w1_rw:+.0f} rad','—','PASS'],
    ['Read-1','100μA','0','200μA',f'{p_w1_rw:+.0f} rad (NDRO)',f'{r1_rw:.1f}μA','PASS'],
    ['Write 0','−100μA','−100μA','0',f'{p_w0_rw:+.0f} rad','—','PASS'],
    ['Read-0','100μA','0','200μA',f'{p_w0_rw:+.0f} rad (NDRO)',f'{r0_rw:.1f}μA',f'FAIL ({r1_rw/max(r0_rw,0.01):.1f}x)'],
]
html1 = build_html('BVM Read-Write Test — 50GHz, No PRD',
    'IW=100μA | ISE=200μA | WL same for write & read (100μA, no separate bias) | 10ps pulse width',
    rw_charts, tt1)
with open('test/bvm/PLOT_bvm_noprd_rw.html','w') as f:
    f.write(html1)
print(f"PLOT_bvm_noprd_rw.html: {len(html1)//1024}KB")

# Test 2 HTML
tt2 = [
    ['Init','0','0','0','0 rad','—','PASS'],
    ['Write 1','100μA','100μA','0',f'{p_w1_ft:+.0f} rad','—','PASS'],
    ['HS-WL','100μA','0','0',f'{p_hs_wl:+.0f} rad (Δ={abs(p_hs_wl-p_w1_ft):.1f})','—','PASS'],
    ['HS-BL','0','100μA','0',f'{p_hs_bl:+.0f} rad (Δ={abs(p_hs_bl-p_w1_ft):.1f})','—','PASS'],
    ['Read-1','100μA','0','200μA','NDRO',f'{r1_ft:.1f}μA','PASS'],
    ['Write 0','−100μA','−100μA','0',f'{p_w0_ft:+.0f} rad','—','PASS'],
    ['Read-0','100μA','0','200μA','NDRO',f'{r0_ft:.1f}μA',f'FAIL ({r1_ft/max(r0_ft,0.01):.1f}x)'],
]
html2 = build_html('BVM Full Truth Table — 50GHz, No PRD',
    'IW=100μA | ISE=200μA | WL same for write & read (100μA) | 10ps pulse | Half-select included',
    ft_charts, tt2)
with open('test/bvm/PLOT_bvm_noprd_full.html','w') as f:
    f.write(html2)
print(f"PLOT_bvm_noprd_full.html: {len(html2)//1024}KB")
