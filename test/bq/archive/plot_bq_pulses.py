#!/usr/bin/env python3
"""BQ SFQ Pulse Test — BVM-style visualization."""
import csv, json, os

with open('test/bq/test_bq_sfq_pulses.csv') as f:
    rows = list(csv.DictReader(f))

T  = [float(r['time'])*1e12 for r in rows]
mv = lambda k: [float(r[k])*1e3 for r in rows]
ua = lambda k: [float(r[k])*1e6 for r in rows]
rad = lambda k: [float(r[k]) for r in rows]

C = {'blue':'#58a6ff','orange':'#f0883e','green':'#7ee787',
     'red':'#ff7b72','purple':'#d2a8ff','yellow':'#e3b341',
     'gray':'#484f58','white':'#c9d1d9'}

shapes = [
    {'type':'rect','xref':'x','yref':'paper','x0':12,'x1':18,'y0':0,'y1':1,
     'fillcolor':'rgba(88,166,255,0.10)','line':{'width':0},'layer':'below'},
    {'type':'rect','xref':'x','yref':'paper','x0':30,'x1':36,'y0':0,'y1':1,
     'fillcolor':'rgba(88,166,255,0.10)','line':{'width':0},'layer':'below'},
    {'type':'rect','xref':'x','yref':'paper','x0':48,'x1':54,'y0':0,'y1':1,
     'fillcolor':'rgba(88,166,255,0.10)','line':{'width':0},'layer':'below'},
    {'type':'rect','xref':'x','yref':'paper','x0':66,'x1':72,'y0':0,'y1':1,
     'fillcolor':'rgba(88,166,255,0.10)','line':{'width':0},'layer':'below'},
]

data = [
    # Panel 1: I_IN + V_OUT
    {'x':T,'y':ua('I(I_IN)'),'name':'I<sub>IN</sub> (μA) — 4 SFQ pulses',
     'type':'scatter','line':{'color':C['blue'],'width':2.2},'xaxis':'x','yaxis':'y'},
    {'x':[0,100],'y':[133,133],'name':'JS I<sub>C</sub>=133μA',
     'type':'scatter','line':{'color':C['gray'],'width':1,'dash':'dot'},'xaxis':'x','yaxis':'y'},
    {'x':T,'y':mv('V(OUT1)'),'name':'V<sub>OUT</sub> (mV) — SFQ output',
     'type':'scatter','line':{'color':C['orange'],'width':2},'xaxis':'x','yaxis':'y2'},

    # Panel 2: P_JS — flux integration
    {'x':T,'y':rad('P(B_JS|XBQ1)'),'name':'P<sub>JS</sub> (rad) — 磁通累积',
     'type':'scatter','line':{'color':C['green'],'width':2.5},'xaxis':'x3','yaxis':'y3'},
    {'x':[0,100],'y':[6.283,6.283],'name':'1Φ₀','type':'scatter',
     'line':{'color':C['gray'],'width':0.6,'dash':'dot'},'xaxis':'x3','yaxis':'y3','showlegend':False},
    {'x':[0,100],'y':[12.566,12.566],'name':'2Φ₀','type':'scatter',
     'line':{'color':C['gray'],'width':0.3,'dash':'dot'},'xaxis':'x3','yaxis':'y3','showlegend':False},

    # Panel 3: V_JS
    {'x':T,'y':mv('V(B_JS|XBQ1)'),'name':'V<sub>JS</sub> (mV) — JS结电压',
     'type':'scatter','line':{'color':C['orange'],'width':1.8},'xaxis':'x5','yaxis':'y5'},
]

layout = {
    'plot_bgcolor':'#161b22','paper_bgcolor':'#0d1117',
    'font':{'color':C['white'],'size':12},
    'legend':{'x':0.01,'y':0.99,'bgcolor':'rgba(0,0,0,0)','bordercolor':'#30363d','font':{'size':10}},
    'margin':{'l':70,'r':70,'t':75,'b':45},
    'hovermode':'x unified','height':750,
    'shapes':shapes,
    'grid':{'rows':3,'columns':1,'pattern':'independent','roworder':'top to bottom'},
    'title':{'text':(
        '<b>BQ SFQ脉冲输入测试 — 4×180μA×3ps pulses, 12ps spacing</b><br>'
        '<sub>I<sub>BIAS</sub>=100μA (N<sub>MID</sub>→IBias)  |  蓝色区=SFQ脉冲输入  |  '
        '预期: 4个输入→4次2π跃变  |  实际: 无离散2π跃变</sub>'),
        'font':{'color':C['blue'],'size':15}},

    'xaxis': {'anchor':'y','domain':[0.68,1.0],'gridcolor':'#30363d','zerolinecolor':'#484f58'},
    'yaxis': {'title':'I<sub>IN</sub> (μA)','domain':[0.68,1.0],'gridcolor':'#30363d','zerolinecolor':'#484f58'},
    'yaxis2':{'title':'V<sub>OUT</sub> (mV)','domain':[0.68,1.0],'overlaying':'y','side':'right',
              'gridcolor':'#30363d','zerolinecolor':'#484f58'},

    'xaxis3':{'anchor':'y3','domain':[0.35,0.66],'gridcolor':'#30363d','zerolinecolor':'#484f58'},
    'yaxis3':{'title':'P<sub>JS</sub> (rad)','domain':[0.35,0.66],'gridcolor':'#30363d','zerolinecolor':'#484f58'},

    'xaxis5':{'anchor':'y5','domain':[0.02,0.33],'gridcolor':'#30363d','zerolinecolor':'#484f58'},
    'yaxis5':{'title':'V<sub>JS</sub> (mV)','domain':[0.02,0.33],'gridcolor':'#30363d','zerolinecolor':'#484f58'},

    'annotations':[
        {'text':'<b>① SFQ脉冲输入 & 输出电压</b>','xref':'paper','yref':'paper',
         'x':0.003,'y':0.99,'showarrow':False,'font':{'color':C['white'],'size':13}},
        {'text':'<b>② JS结相位 — 连续斜坡, 无2π平台 (非离散SFQ)</b>','xref':'paper','yref':'paper',
         'x':0.003,'y':0.645,'showarrow':False,'font':{'color':C['white'],'size':13}},
        {'text':'<b>③ JS结电压 — 脉冲期间V≈0.9mV</b>','xref':'paper','yref':'paper',
         'x':0.003,'y':0.315,'showarrow':False,'font':{'color':C['white'],'size':13}},

        # Key annotations
        {'text':'<b>脉冲①</b>','xref':'x','yref':'y','x':15,'y':210,'showarrow':True,'arrowhead':2,
         'ax':0,'ay':-25,'font':{'color':C['yellow'],'size':10},'bgcolor':'rgba(0,0,0,0.7)','borderpad':3},
        {'text':'<b>脉冲②</b>','xref':'x','yref':'y','x':33,'y':210,'showarrow':True,'arrowhead':2,
         'ax':0,'ay':-25,'font':{'color':C['yellow'],'size':10},'bgcolor':'rgba(0,0,0,0.7)','borderpad':3},
        {'text':'<b>脉冲③</b>','xref':'x','yref':'y','x':51,'y':210,'showarrow':True,'arrowhead':2,
         'ax':0,'ay':-25,'font':{'color':C['yellow'],'size':10},'bgcolor':'rgba(0,0,0,0.7)','borderpad':3},
        {'text':'<b>脉冲④</b>','xref':'x','yref':'y','x':69,'y':210,'showarrow':True,'arrowhead':2,
         'ax':0,'ay':-25,'font':{'color':C['yellow'],'size':10},'bgcolor':'rgba(0,0,0,0.7)','borderpad':3},

        {'text':'<b>← 4脉冲累积<br>   P=0→102rad<br>   无离散2π平台</b>',
         'xref':'x3','yref':'y3','x':45,'y':60,'showarrow':True,'arrowhead':2,
         'ax':50,'ay':-20,'font':{'color':C['green'],'size':10},'bgcolor':'rgba(0,0,0,0.7)','borderpad':4},
    ]
}

import plotly as py
with open(os.path.join(os.path.dirname(py.__file__), 'package_data', 'plotly.min.js')) as f:
    plotly_js = f.read()

html = f'''<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
     background:#0d1117;color:#c9d1d9;margin:0;padding:8px}}
.note{{max-width:1500px;margin:8px auto;padding:12px 18px;
       background:#161b22;border:1px solid #30363d;border-radius:6px;font-size:13px;line-height:1.6}}
.note b{{color:#58a6ff}} .kw{{color:#e3b341}} .ko{{color:#f0883e}} .kg{{color:#7ee787}}
</style></head><body>
<div class="note">
<b>▸ 测试:</b> 4个SFQ脉冲 (180μA×3ps, 间距12ps) → 验证BQ离散量化功能<br>
<b>▸ <span class="kw">预期:</span></b> 每个脉冲→JS开关→P<sub>JS</sub>跃变2π(6.28rad)→V<sub>OUT</sub>输出1个SFQ脉冲<br>
<b>▸ <span class="ko">实际:</span></b> P<sub>JS</sub>连续斜坡0→102rad(16.2Φ₀), 无离散2π平台, V<sub>OUT</sub>振荡非脉冲<br>
<b>▸ <span class="ko">结论:</span></b> BQ(MITLL SFQ5ee参数+JoSIM)表现为模拟磁通积分器, 非离散SFQ量化器<br>
<b>▸ <span class="kw">BVM论文→JoSIM ✓</span> | <span class="ko">BQ论文→JSIM ✗ (不同仿真器)</span></b>
</div>
<div id="chart" style="width:98vw;height:82vh;max-width:1500px;margin:0 auto"></div>
<script>{plotly_js}</script>
<script>
Plotly.newPlot("chart", {json.dumps(data)}, {json.dumps(layout)}, {{responsive:true}});
</script>
</body></html>'''

with open('test/bq/PLOT_bq_pulses.html', 'w') as f:
    f.write(html)
print(f"Done: test/bq/PLOT_bq_pulses.html ({len(html)//1024}KB)")
