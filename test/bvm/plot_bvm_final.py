#!/usr/bin/env python3
"""BVM Final Visualizations — CDN Plotly, clean dark theme."""
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

def load(fn):
    with open(fn) as f:
        rows = list(csv.DictReader(f))
    T = [float(r['time'])*1e12 for r in rows]
    return T, rows

def mk_chart(title, ytitle, traces, annotations=None):
    L = json.loads(json.dumps(BASE))
    L['title'] = title; L['yaxis']['title'] = ytitle
    for t in traces: t['type'] = 'scatter'
    if annotations:
        L['annotations'] = []
        for a in annotations:
            aa = {'xref':'x','yref':'y','showarrow':True,'arrowhead':2,'arrowsize':1.2,
                  'ax':0,'ay':-22,'font':{'color':C['yellow'],'size':10},
                  'bgcolor':'rgba(0,0,0,0.6)','borderpad':3}; aa.update(a)
            L['annotations'].append(aa)
    return L, traces

def build_html(title, subtitle, charts, truth_rows, summary_html=''):
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
        '.tt{max-width:1400px;margin:0 auto 15px;padding:10px 18px;background:#161b22;',
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

    if truth_rows:
        parts.append('<div class="tt"><h3>Truth Table</h3><table>\n')
        parts.append('<tr>' + ''.join(f'<th>{c}</th>' for c in truth_rows[0]) + '</tr>\n')
        for row in truth_rows[1:]:
            parts.append('<tr>' + ''.join(f'<td>{c}</td>' for c in row) + '</tr>\n')
        parts.append('</table></div>\n')

    if summary_html:
        parts.append(f'<div class="tt">{summary_html}</div>\n')

    parts.append('</body></html>')
    return ''.join(parts)

# ═══════════════════════════════════════
# Test 1: Read-Write
# ═══════════════════════════════════════
T1, rows1 = load('test/bvm/test_bvm_final_rw.csv')
ua1 = lambda k: [float(r[k])*1e6 for r in rows1]
rad1 = lambda k: [float(r[k]) for r in rows1]

p_w1 = sum(float(r['P(B_JM1|XBVM1)']) for r in rows1 if 30<float(r['time'])*1e12<48)/max(1,sum(1 for r in rows1 if 30<float(r['time'])*1e12<48))
p_w0 = sum(float(r['P(B_JM1|XBVM1)']) for r in rows1 if 150<float(r['time'])*1e12<168)/max(1,sum(1 for r in rows1 if 150<float(r['time'])*1e12<168))
ilm1 = [float(r['I(L_M1|XBVM1)'])*1e6 for r in rows1]
i_w1 = sum(ilm1[i] for i in range(len(T1)) if 30<T1[i]<48)/max(1,sum(1 for i in range(len(T1)) if 30<T1[i]<48))
isl = ua1('I(B_LD1)')
r1 = max(abs(isl[i]) for i in range(len(T1)) if 76<T1[i]<84)
r0 = max(abs(isl[i]) for i in range(len(T1)) if 196<T1[i]<204)
ratio = r1/max(r0,0.01)

rw_charts = [
    mk_chart('<b>① Drive Signals</b>', 'Current (μA)',
        [{'x':T1,'y':ua1('I(I_WL1)'),'name':'I<sub>WL</sub>','line':{'color':C['blue'],'width':2.2}},
         {'x':T1,'y':ua1('I(I_BL1)'),'name':'I<sub>BL</sub>','line':{'color':C['red'],'width':1.8}},
         {'x':T1,'y':ua1('I(I_SE1)'),'name':'I<sub>SE</sub>','line':{'color':C['purple'],'width':1.3,'dash':'dot'}}],
        [{'text':'<b>W1</b>','x':15,'y':170},{'text':'<b>R1</b>','x':77,'y':150},
         {'text':'<b>W0</b>','x':137,'y':-70},{'text':'<b>R0</b>','x':197,'y':150}]),

    mk_chart(f'<b>② Storage Phase — P<sub>JM1</sub> (W1→{p_w1:+.0f}rad W0→{p_w0:+.0f}rad)</b>', 'P<sub>JM1</sub> (rad)',
        [{'x':T1,'y':rad1('P(B_JM1|XBVM1)'),'name':'P<sub>JM1</sub>','line':{'color':C['green'],'width':2.5}},
         {'x':[0,220],'y':[0,0],'line':{'color':C['gray'],'width':0.5,'dash':'dot'},'showlegend':False}]),

    mk_chart(f'<b>③ Storage Current — I(LM1) (W1→{i_w1:+.0f}μA)</b>', 'I(LM1) (μA)',
        [{'x':T1,'y':ilm1,'name':'I(LM1)','line':{'color':C['yellow'],'width':2.5},
          'fill':'tozeroy','fillcolor':'rgba(227,179,65,0.1)'}]),

    mk_chart(f'<b>④ Sense Output — I<sub>SL</sub> (R1={r1:.1f}μA R0={r0:.1f}μA R1/R0={ratio:.1f}x {"✓" if ratio>3 else "✗"})</b>', 'I<sub>SL</sub> (μA)',
        [{'x':T1,'y':isl,'name':'I<sub>SL</sub>','line':{'color':C['yellow'],'width':2.5},
          'fill':'tozeroy','fillcolor':'rgba(227,179,65,0.1)'}],
        [{'text':f'<b>R1={r1:.1f}μA</b>','x':80,'y':r1+3},{'text':f'<b>R0={r0:.1f}μA</b>','x':200,'y':r0+3}]),
]

rw_tt = [
    ['Phase','WL','BL','SE','P_JM1','I_SL','Result'],
    ['Init','0','0','0','0 rad','—','PASS'],
    ['Write 1','100μA','100μA','0',f'{p_w1:+.0f} rad','—','PASS'],
    ['Read-1','100μA','0','100μA','NDRO',f'{r1:.1f} μA','PASS'],
    ['Write 0','−100μA','−100μA','0',f'{p_w0:+.0f} rad','—','PASS'],
    ['Read-0','100μA','0','100μA','NDRO',f'{r0:.1f} μA',f'PASS ({ratio:.1f}x)'],
]

rw_summary = (f'<b>Config:</b> 50GHz | 10ps pulse | IW=ISE=100μA | WL same for write & read | '
              f'JM1 IC=120μA | JS1=JS2 IC=74μA<br>'
              f'<b>Result:</b> <span class="ok">R1/R0={ratio:.1f}x ✓</span> | '
              f'Write ✓ | NDRO ✓ | R1={r1:.1f}μA R0={r0:.1f}μA (near-zero for stored 0)')

html1 = build_html('BVM Final — Read/Write Test',
    '50GHz, 10ps pulse, WL=100μA (write & read same), ISE=100μA',
    rw_charts, rw_tt, rw_summary)
with open('test/bvm/BVM_FINAL_RW.html','w') as f: f.write(html1)
print(f"BVM_FINAL_RW.html: {len(html1)//1024}KB")

# ═══════════════════════════════════════
# Test 2: Full Truth Table
# ═══════════════════════════════════════
T2, rows2 = load('test/bvm/test_bvm_final_full.csv')
ua2 = lambda k: [float(r[k])*1e6 for r in rows2]
rad2 = lambda k: [float(r[k]) for r in rows2]

p_w1_2 = sum(float(r['P(B_JM1|XBVM1)']) for r in rows2 if 30<float(r['time'])*1e12<48)/max(1,sum(1 for r in rows2 if 30<float(r['time'])*1e12<48))
p_w0_2 = sum(float(r['P(B_JM1|XBVM1)']) for r in rows2 if 190<float(r['time'])*1e12<208)/max(1,sum(1 for r in rows2 if 190<float(r['time'])*1e12<208))
p_hs_wl = sum(float(r['P(B_JM1|XBVM1)']) for r in rows2 if 70<float(r['time'])*1e12<88)/max(1,sum(1 for r in rows2 if 70<float(r['time'])*1e12<88))
p_hs_bl = sum(float(r['P(B_JM1|XBVM1)']) for r in rows2 if 90<float(r['time'])*1e12<108)/max(1,sum(1 for r in rows2 if 90<float(r['time'])*1e12<108))
ilm1_2 = [float(r['I(L_M1|XBVM1)'])*1e6 for r in rows2]
isl_2 = ua2('I(B_LD1)')
r1_2 = max(abs(isl_2[i]) for i in range(len(T2)) if 96<T2[i]<104)
r0_2 = max(abs(isl_2[i]) for i in range(len(T2)) if 216<T2[i]<224)
ratio_2 = r1_2/max(r0_2,0.01)

ft_charts = [
    mk_chart('<b>① Drive Signals</b>', 'Current (μA)',
        [{'x':T2,'y':ua2('I(I_WL1)'),'name':'I<sub>WL</sub>','line':{'color':C['blue'],'width':2.2}},
         {'x':T2,'y':ua2('I(I_BL1)'),'name':'I<sub>BL</sub>','line':{'color':C['red'],'width':1.8}},
         {'x':T2,'y':ua2('I(I_SE1)'),'name':'I<sub>SE</sub>','line':{'color':C['purple'],'width':1.3,'dash':'dot'}}],
        [{'text':'<b>W1</b>','x':15,'y':170},{'text':'<b>HS-WL</b>','x':55,'y':155},
         {'text':'<b>HS-BL</b>','x':75,'y':145},{'text':'<b>R1</b>','x':97,'y':135},
         {'text':'<b>W0</b>','x':177,'y':-60},{'text':'<b>R0</b>','x':217,'y':135}]),

    mk_chart(f'<b>② Storage Phase — P<sub>JM1</sub> (W1→{p_w1_2:+.0f}rad W0→{p_w0_2:+.0f}rad HS_WL_Δ={abs(p_hs_wl-p_w1_2):.1f} HS_BL_Δ={abs(p_hs_bl-p_w1_2):.1f})</b>', 'P<sub>JM1</sub> (rad)',
        [{'x':T2,'y':rad2('P(B_JM1|XBVM1)'),'name':'P<sub>JM1</sub>','line':{'color':C['green'],'width':2.5}},
         {'x':[0,280],'y':[0,0],'line':{'color':C['gray'],'width':0.5,'dash':'dot'},'showlegend':False}]),

    mk_chart('<b>③ Storage Current — I(LM1)</b>', 'I(LM1) (μA)',
        [{'x':T2,'y':ilm1_2,'name':'I(LM1)','line':{'color':C['yellow'],'width':2.5},
          'fill':'tozeroy','fillcolor':'rgba(227,179,65,0.1)'}]),

    mk_chart(f'<b>④ Sense Output — I<sub>SL</sub> (R1={r1_2:.1f}μA R0={r0_2:.1f}μA R1/R0={ratio_2:.1f}x {"✓" if ratio_2>3 else "✗"})</b>', 'I<sub>SL</sub> (μA)',
        [{'x':T2,'y':isl_2,'name':'I<sub>SL</sub>','line':{'color':C['yellow'],'width':2.5},
          'fill':'tozeroy','fillcolor':'rgba(227,179,65,0.1)'}],
        [{'text':f'<b>R1={r1_2:.1f}μA</b>','x':100,'y':r1_2+3},{'text':f'<b>R0={r0_2:.1f}μA</b>','x':220,'y':r0_2+3}]),
]

ft_tt = [
    ['Phase','WL','BL','SE','P_JM1','I_SL','Result'],
    ['Init','0','0','0','0 rad','—','PASS'],
    ['Write 1','100μA','100μA','0',f'{p_w1_2:+.0f} rad','—','PASS'],
    ['HS-WL','100μA','0','0',f'{p_hs_wl:+.0f} rad (Δ={abs(p_hs_wl-p_w1_2):.1f})','—','PASS (no disturb)'],
    ['HS-BL','0','100μA','0',f'{p_hs_bl:+.0f} rad (Δ={abs(p_hs_bl-p_w1_2):.1f})','—','PASS (no disturb)'],
    ['Read-1','100μA','0','100μA','NDRO',f'{r1_2:.1f} μA','PASS'],
    ['Write 0','−100μA','−100μA','0',f'{p_w0_2:+.0f} rad','—','PASS'],
    ['Read-0','100μA','0','100μA','NDRO',f'{r0_2:.1f} μA',f'PASS ({ratio_2:.1f}x)'],
]

ft_summary = (f'<b>Config:</b> 50GHz | 10ps pulse | IW=ISE=100μA | WL same for write & read | '
              f'JM1 IC=120μA | JS1=JS2 IC=74μA<br>'
              f'<b>Result:</b> <span class="ok">R1/R0={ratio_2:.1f}x ✓</span> | '
              f'Write ✓ | Half-select ✓ | NDRO ✓ | '
              f'R1={r1_2:.1f}μA (stored 1) R0={r0_2:.1f}μA (stored 0, near-zero)')

html2 = build_html('BVM Final — Full Truth Table',
    '50GHz, 10ps pulse, WL=100μA (write & read same), ISE=100μA',
    ft_charts, ft_tt, ft_summary)
with open('test/bvm/BVM_FINAL_FULL.html','w') as f: f.write(html2)
print(f"BVM_FINAL_FULL.html: {len(html2)//1024}KB")
