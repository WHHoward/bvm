#!/usr/bin/env python3
"""BQ multi-current comparison — P_JS vs I_IN at 5 levels."""
import csv, json, os

C = {'blue':'#58a6ff','orange':'#f0883e','green':'#7ee787',
     'red':'#ff7b72','purple':'#d2a8ff','yellow':'#e3b341',
     'gray':'#484f58','white':'#c9d1d9'}
LEVELS = [80, 133, 150, 180, 200]
COLORS = ['#484f58','#e3b341','#f0883e','#ff7b72','#ff4444']
DASHES = ['dot','dash','solid','solid','solid']
WIDTHS = [1.5, 2, 2.2, 2.5, 3]

data = []
for iin, color, dash, width in zip(LEVELS, COLORS, DASHES, WIDTHS):
    with open(f'test/bq/test_bq_{iin}uA.csv') as f:
        rows = list(csv.DictReader(f))
    T = [float(r['time'])*1e12 for r in rows]
    pjs = [float(r['P(B_JS|XBQ1)']) for r in rows]
    vout = [float(r['V(OUT1)'])*1e3 for r in rows]
    iin_vals = [float(r['I(I_IN)'])*1e6 for r in rows]

    label = f'{iin}μA' if iin != 133 else f'{iin}μA (IC)'

    # P_JS traces
    data.append({'x':T, 'y':pjs,
        'name':f'I<sub>IN</sub>={label}', 'type':'scatter',
        'line':{'color':color,'width':width,'dash':dash}, 'xaxis':'x','yaxis':'y'})

    # V_OUT traces
    data.append({'x':T, 'y':vout,
        'name':f'I<sub>IN</sub>={label}', 'type':'scatter',
        'line':{'color':color,'width':width,'dash':dash}, 'xaxis':'x3','yaxis':'y3',
        'showlegend':False})

# Φ₀ reference lines
for n in [1,2,3,5,8,10,12,15]:
    data.append({'x':[0,150],'y':[n*6.283,n*6.283],
        'type':'scatter','line':{'color':C['gray'],'width':0.4,'dash':'dot'},
        'xaxis':'x','yaxis':'y','showlegend':False,'hoverinfo':'skip'})

# Input window shapes
shapes = [
    {'type':'rect','xref':'x','yref':'paper','x0':25,'x1':55,'y0':0,'y1':1,
     'fillcolor':'rgba(88,166,255,0.08)','line':{'width':0},'layer':'below'},
    {'type':'rect','xref':'x','yref':'paper','x0':85,'x1':115,'y0':0,'y1':1,
     'fillcolor':'rgba(255,123,114,0.08)','line':{'width':0},'layer':'below'},
]

# Summary metrics as a table-like annotation
summary_text = (
    '<b>测试结果汇总</b><br>'
    'I<sub>IN</sub>  |  超出IC  |  P<sub>JS</sub>累积  |  Φ₀数  |  V<sub>JS</sub>峰值  |  V<sub>OUT</sub>峰值<br>'
    '80μA   |  −53μA  |    1.7rad  |  0.3Φ₀  |  —  |  — (未触发)<br>'
    '133μA  |    0μA  |  53.1rad  |  8.4Φ₀  |  0.82mV  |  0.56mV<br>'
    '150μA  |  +17μA  |  66.4rad  |  10.6Φ₀ |  0.91mV  |  0.61mV<br>'
    '180μA  |  +47μA  |  84.9rad  |  13.5Φ₀ |  1.07mV  |  0.70mV<br>'
    '200μA  |  +67μA  |  96.9rad  |  15.4Φ₀ |  1.17mV  |  0.73mV'
)

layout = {
    'plot_bgcolor':'#161b22','paper_bgcolor':'#0d1117',
    'font':{'color':C['white'],'size':12},
    'legend':{'x':0.01,'y':0.99,'bgcolor':'rgba(0,0,0,0)','bordercolor':'#30363d','font':{'size':10}},
    'margin':{'l':70,'r':70,'t':80,'b':50},
    'hovermode':'x unified',
    'height':750,
    'shapes':shapes,
    'grid':{'rows':2,'columns':1,'pattern':'independent','roworder':'top to bottom'},
    'title':{'text':(
        '<b>BQ 多电流级别对比 — 磁通累积 & SFQ输出</b><br>'
        '<sub>I<sub>BIAS</sub>=100μA泄放 | 5级输入电流 (80→200μA) | 蓝色/红色区=±输入阶跃</sub>'),
        'font':{'color':C['blue'],'size':15}},

    # Panel 1: P_JS comparison
    'xaxis':{'anchor':'y','domain':[0.45,1.0],'gridcolor':'#30363d','zerolinecolor':'#484f58'},
    'yaxis':{'title':'P<sub>JS</sub> 磁通累积相位 (rad)','domain':[0.45,1.0],
             'gridcolor':'#30363d','zerolinecolor':'#484f58'},
    # Panel 2: V_OUT comparison
    'xaxis3':{'anchor':'y3','domain':[0.02,0.43],'gridcolor':'#30363d','zerolinecolor':'#484f58',
              'title':'Time (ps)'},
    'yaxis3':{'title':'V<sub>OUT</sub> SFQ输出 (mV)','domain':[0.02,0.43],
              'gridcolor':'#30363d','zerolinecolor':'#484f58'},

    'annotations':[
        {'text':'<b>① 磁通累积对比 — 电流越大, 相位累积越多</b>',
         'xref':'paper','yref':'paper','x':0.003,'y':0.99,'showarrow':False,
         'font':{'color':C['white'],'size':14}},
        {'text':'<b>② SFQ输出电压对比</b>',
         'xref':'paper','yref':'paper','x':0.003,'y':0.42,'showarrow':False,
         'font':{'color':C['white'],'size':14}},
        # Summary table
        {'text':summary_text,'xref':'paper','yref':'paper','x':0.55,'y':0.38,
         'showarrow':False,'font':{'color':C['white'],'size':10,'family':'monospace'},
         'bgcolor':'rgba(22,27,34,0.9)','borderpad':8,'align':'left',
         'bordercolor':C['gray']},
        # Key insight
        {'text':'<b>Φ₀ ∝ (I<sub>IN</sub>−I<sub>C</sub>) × Δt</b><br>磁通累积与超出电流成正比',
         'xref':'paper','yref':'paper','x':0.55,'y':0.15,'showarrow':False,
         'font':{'color':C['yellow'],'size':11},'bgcolor':'rgba(0,0,0,0.6)','borderpad':6},
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
.analysis{{max-width:1500px;margin:8px auto;padding:14px 20px;
           background:#161b22;border:1px solid #30363d;border-radius:6px;
           font-size:13px;line-height:1.65}}
.analysis h3{{color:#58a6ff;margin:0 0 6px;font-size:14px}}
.analysis table{{border-collapse:collapse;margin:6px 0;font-size:12px;width:100%}}
.analysis th{{background:#1a2332;color:#58a6ff;padding:4px 10px;text-align:left;border:1px solid #30363d}}
.analysis td{{padding:4px 10px;border:1px solid #30363d}}
.analysis .kv{{color:#7ee787}} .ko{{color:#f0883e}} .ky{{color:#e3b341}} .kr{{color:#ff7b72}}
</style></head><body>

<div class="analysis">
<h3>多电流级别测试 & BVM↔BQ 信号链规划</h3>

<p><b class="k">测试设计：</b>5级输入电流(80/133/150/180/200μA)，每级±30ps阶跃，监控P<sub>JS</sub>磁通累积和V<sub>OUT</sub>输出。</p>

<table>
<tr><th>I<sub>IN</sub></th><th>超出IC</th><th>预期脉冲数</th><th>实际Φ₀累积</th><th>V<sub>OUT</sub>峰值</th><th>开关模式</th></tr>
<tr><td>80μA</td><td class="kr">−53μA</td><td>0</td><td>0.3Φ₀</td><td>—</td><td>未触发 ✓</td></tr>
<tr><td>133μA</td><td class="ky">0μA</td><td>~8</td><td>8.4Φ₀</td><td>0.56mV</td><td>阈值连续</td></tr>
<tr><td>150μA</td><td class="ko">+17μA</td><td>~11</td><td>10.6Φ₀</td><td>0.61mV</td><td>连续电压态</td></tr>
<tr><td>180μA</td><td class="ko">+47μA</td><td>~14</td><td>13.5Φ₀</td><td>0.70mV</td><td>连续电压态</td></tr>
<tr><td>200μA</td><td class="ko">+67μA</td><td>~15</td><td>15.4Φ₀</td><td>0.73mV</td><td>连续电压态</td></tr>
</table>

<p><b class="ky">关键发现：</b>相位累积量(Φ₀)与超出电流成正比，验证了 dφ/dt ∝ V<sub>JS</sub> ∝ (I<sub>IN</sub>−I<sub>C</sub>)。
但相位跃变是<b class="ko">连续的小步进(~1-2rad)</b>而非离散2π阶跃——因为DC阶跃输入使JS持续处于电压态无法复位。
要产生离散SFQ脉冲，需要<b>脉冲式输入</b>（电流超过IC后快速回落到IC以下）。</p>
</div>

<div class="analysis" style="margin-top:8px">
<h3>BVM ↔ BQ 完整复现的输入输出规划</h3>

<table>
<tr><th>层级</th><th>元件</th><th>输入信号</th><th>阈值/范围</th><th>输出信号</th><th>输出特征</th></tr>
<tr>
  <td><b>1</b></td><td><b>BVM 写</b></td>
  <td>WL+BL电流脉冲</td>
  <td>>JM1 IC=120μA</td>
  <td>S-Loop磁通态</td>
  <td>±Φ₀锁存 (非易失)</td>
</tr>
<tr>
  <td><b>2</b></td><td><b>BVM 读</b></td>
  <td>SE脉冲+WL偏置</td>
  <td>SE=100-200μA, WL=33-67μA</td>
  <td>I<sub>SL</sub>读出电流</td>
  <td class="ko">0-60μA缓变 (非SFQ!)</td>
</tr>
<tr style="background:#1a2332">
  <td><b>⚡</b></td><td><b>接口层</b></td>
  <td colspan="4"><b class="ky">需要 JTL缓冲 或 SFQ脉冲发生器 — BVM的缓变I<sub>SL</sub>无法直接驱动BQ的133μA阈值</b></td>
</tr>
<tr>
  <td><b>3</b></td><td><b>BQ 量化</b></td>
  <td>SFQ脉冲序列 (>IC)</td>
  <td>>JS IC=133μA</td>
  <td>SFQ脉冲输出</td>
  <td class="kv">~0.6mV×N个脉冲</td>
</tr>
<tr>
  <td><b>4</b></td><td><b>T1 乘法</b></td>
  <td>SFQ脉冲序列</td>
  <td>待定</td>
  <td>加权SFQ输出</td>
  <td>待仿真</td>
</tr>
</table>

<p style="margin-top:8px"><b class="ky">论文中的解决方案：</b>Razmkhah 2024 Fig.5 显示 BVM 通过 <b>JJ-Synapse</b>（含SQUID加权+电流差分）连接到 BQ。
Synapse将BVM的缓变读出转换为SFQ脉冲序列，BQ再将其量化为等比例脉冲输出。
如果我们跳过Synapse直接连接BVM→BQ，需要：</p>
<p><b class="ko">方案A（推荐）：</b>在BVM SL输出端加JTL缓冲级 — JTL将0-60μA缓变电流整形为SFQ脉冲(>133μA, ~2ps宽)，再驱动BQ。</p>
<p><b class="ky">方案B：</b>降低BQ的JS IC到~60μA以匹配BVM输出 — 偏离论文参数，但可验证功能。</p>
<p><b class="kv">方案C：</b>直接用BVM内部SFQ信号(V_JS1/V_JS2的~0.5mV脉冲)作为BQ输入 — 信号已是SFQ级别，但需修改端口。</p>
</div>

<div id="chart" style="width:98vw;height:78vh;max-width:1500px;margin:0 auto"></div>
<script>{plotly_js}</script>
<script>
Plotly.newPlot("chart", {json.dumps(data)}, {json.dumps(layout)}, {{responsive:true}});
</script>
</body></html>'''

with open('test/bq/PLOT_bq_compare.html', 'w') as f:
    f.write(html)
print(f"Done: test/bq/PLOT_bq_compare.html ({len(html)//1024}KB)")
