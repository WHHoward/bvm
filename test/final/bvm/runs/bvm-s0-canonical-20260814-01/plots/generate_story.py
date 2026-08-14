#!/usr/bin/env python3
"""generate_story -- BVM-S0 guided visual story generator (presentation-layer
refactor of the dashboard; no data/window/tolerance/disposition change).

Reads ONLY frozen evidence (12 raw CSVs + S0-004 corrected-analysis.json),
embeds local plotly.min.js, emits a single self-contained
plots/bvm-s0-story.html organized as a guided narrative:

  status card      question / design / artifact VALID / disposition
                   INCONCLUSIVE / reason / no-claims
  Act 1            what did we do?  (timing diagram + conceptual topology,
                   detailed topology collapsed)
  Act 2            what did we observe?  (V(SL1), I(L_SL) pos-vs-neg core,
                   controls inset; 3-block explainer cards)
  Act 3            what happened inside? (JM1/JM2 diagnostics, collapsed)
  Act 4            why INCONCLUSIVE?  (3-step decision + overlay + noise zoom)
  boundary         known / unknown / next
  appendix         Explore raw traces (advanced inspector, kept)

Every main visualization carries: What this shows / Why it matters /
What it does NOT prove.  Numeric/claim boundaries follow S0-004/C02 only.
No JoSIM run; no hand-filled values.
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
OUT = RUN / 'plots' / 'bvm-s0-story.html'

CASES = ('init_positive_read', 'init_positive_control',
         'init_negative_read', 'init_negative_control')
STEPS = ('0.1ps', '0.05ps', '0.025ps')
COL_MAP = {
    'I_WL1': 'I(I_WL1)', 'I_SE1': 'I(I_SE1)',
    'P_JM1': 'P(B_JM1|XBVM1)', 'P_JM2': 'P(B_JM2|XBVM1)',
    'V_JM1': 'V(B_JM1|XBVM1)', 'V_JM2': 'V(B_JM2|XBVM1)',
    'V_SL1': 'V(SL1)', 'I_LSL': 'I(L_SL|XBVM1)',
}


def load_csv(case: str, step: str) -> dict:
    with open(RUN / 'raw' / case / step / 'run-01.csv', encoding='utf-8') as f:
        rows = list(csv.reader(f))
    hdr = [h.strip().strip('"') for h in rows[0]]
    idx = {h: i for i, h in enumerate(hdr)}
    cols: dict[str, list] = {}
    t: list[float] = []
    for r in rows[1:]:
        t.append(round(float(r[0]), 15))
        for key, col in COL_MAP.items():
            cols.setdefault(key, []).append(round(float(r[idx[col]]), 9))
    return {'t': t, 'c': cols}


def main() -> int:
    data = {}
    for case in CASES:
        for step in STEPS:
            data[f'{case}/{step}'] = load_csv(case, step)
    corr = json.loads(CORRECTED.read_text(encoding='utf-8'))['cases']
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
    html = TEMPLATE.replace('__PLOTLY_JS__', plotly_js) \
                   .replace('__DATA_JSON__', data_json) \
                   .replace('__SUMMARY_JSON__', sum_json)
    OUT.write_text(html, encoding='utf-8')
    print(f'story written: {OUT} ({OUT.stat().st_size / 1e6:.1f} MB)')
    return 0


TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>BVM-S0 guided visual story</title>
<script>__PLOTLY_JS__</script>
<style>
  :root { --ink:#222; --mut:#666; --line:#ddd; --bg:#fff; --panel:#fafafa;
          --acc:#1f6fb2; --warn:#b26a00; --bad:#b5457f; --ok:#2e7d32;
          --pos:#d1495b; --neg:#4f86c6; }
  * { box-sizing:border-box; }
  body { font-family:-apple-system,"Segoe UI",Roboto,"Noto Sans SC",sans-serif;
         margin:0; padding:0 22px 40px; color:var(--ink); background:var(--bg); }
  .wrap { max-width:1100px; margin:0 auto; }
  h1 { font-size:22px; margin:18px 0 4px; }
  h2 { font-size:17px; margin:0 0 10px; }
  h3 { font-size:14px; margin:0 0 8px; }
  .sub { color:var(--mut); font-size:12.5px; margin-bottom:14px; }
  .mono { font-family:ui-monospace,Menlo,Consolas,monospace; font-size:11.5px; }
  /* status card */
  .status { display:grid; grid-template-columns:repeat(auto-fit,minmax(230px,1fr));
            gap:10px; margin:14px 0 20px; }
  .scard { border:1px solid var(--line); border-radius:8px; padding:10px 12px;
           background:var(--panel); }
  .scard .k { font-size:11px; color:var(--mut); text-transform:uppercase;
              letter-spacing:.04em; }
  .scard .v { font-size:13.5px; margin-top:3px; line-height:1.4; }
  .pill { display:inline-block; padding:2px 10px; border-radius:11px;
          font-size:12px; color:#fff; margin-right:6px; }
  .pill.ok { background:var(--ok); }
  .pill.warn { background:var(--warn); }
  .pill.acc { background:var(--acc); }
  .noarea { margin-top:10px; font-size:12px; color:var(--bad); font-weight:600; }
  /* acts */
  .act { margin:30px 0; }
  .acthead { border-bottom:2px solid var(--acc); padding-bottom:6px;
             margin-bottom:14px; }
  .acthead .q { font-size:16px; font-weight:700; color:var(--acc); }
  .acthead .why { font-size:12px; color:var(--mut); margin-top:3px; }
  .card3 { display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr));
           gap:10px; margin:10px 0 16px; }
  .card3 div { border-left:3px solid var(--acc); background:var(--panel);
               padding:8px 10px; font-size:12px; }
  .card3 .h { font-weight:700; color:var(--acc); font-size:11px;
              text-transform:uppercase; letter-spacing:.03em; }
  .card3 div.no { border-left-color:var(--bad); }
  .card3 div.no .h { color:var(--bad); }
  .concl { background:#eef7ee; border:1px solid #b7ddb7; border-radius:8px;
           padding:10px 14px; font-size:13px; margin:12px 0; }
  .concl b { color:var(--ok); }
  /* timing diagram */
  .timeline { overflow-x:auto; }
  .trow { display:flex; height:26px; margin:2px 0; font-size:11px; }
  .tlab { width:170px; flex:0 0 170px; line-height:26px; color:var(--mut);
          padding-right:8px; text-align:right; font-size:11.5px; }
  .track { position:relative; flex:1; min-width:640px; background:#f5f5f5;
           border-radius:3px; }
  .seg { position:absolute; top:3px; bottom:3px; border-radius:3px; }
  .tmark { position:absolute; top:-14px; font-size:9.5px; color:var(--mut);
           transform:translateX(-50%); white-space:nowrap; }
  /* conceptual topology */
  .ctop { display:flex; align-items:center; gap:8px; flex-wrap:wrap;
          font-size:12.5px; margin:8px 0 4px; }
  .cbox { border:1.5px solid var(--acc); border-radius:8px; padding:8px 12px;
          background:#f3f8fd; text-align:center; }
  .cbox .n { font-weight:700; font-size:13px; }
  .cbox .d { font-size:10.5px; color:var(--mut); margin-top:2px; }
  .carrow { color:var(--acc); font-size:16px; }
  .obsbox { border:1.5px dashed var(--bad); border-radius:8px; padding:6px 12px;
            background:#fdf6f5; text-align:center; font-size:11.5px;
            color:var(--bad); }
  details { border:1px solid var(--line); border-radius:8px; padding:10px 14px;
            margin:10px 0; background:var(--panel); }
  summary { cursor:pointer; font-weight:600; font-size:13px; }
  .foldnote { font-size:12px; color:var(--mut); margin-top:6px; }
  table { border-collapse:collapse; font-size:12px; width:100%; }
  th, td { border:1px solid var(--line); padding:4px 8px; text-align:left; }
  th { background:#f0f0f0; }
  .stepflow { counter-reset:st; margin:10px 0; }
  .stepflow .s { position:relative; padding:10px 14px 10px 44px; margin:6px 0;
                 background:var(--panel); border:1px solid var(--line);
                 border-radius:8px; font-size:13px; }
  .stepflow .s::before { counter-increment:st; content:counter(st);
                 position:absolute; left:12px; top:9px; width:22px; height:22px;
                 border-radius:50%; background:var(--acc); color:#fff;
                 text-align:center; line-height:22px; font-size:12px; }
  .stepflow .s.fail { border-left:4px solid var(--bad); }
  .stepflow .s.okline { border-left:4px solid var(--ok); }
  .stepflow .s.final { border-left:4px solid var(--warn); background:#fdf6ec; }
  .rulecard { background:#fdf6ec; border:1px solid #e5c98a; border-radius:8px;
              padding:10px 14px; font-size:12.5px; margin:12px 0; }
  .inconcl { background:var(--panel); border:1px solid var(--line);
             border-radius:8px; padding:12px 16px; font-size:13.5px;
             margin:14px 0; line-height:1.6; }
  .ctrl { display:flex; gap:12px; align-items:center; flex-wrap:wrap;
          font-size:12.5px; margin-bottom:8px; }
  .note { font-size:11.5px; color:var(--mut); margin-top:5px; }
  .warn-note { color:var(--bad); font-weight:600; }
  .appendix { border-top:2px solid var(--line); margin-top:34px; padding-top:18px; }
</style>
</head>
<body>
<div class="wrap">

<h1>BVM-S0 canonical source experiment — guided visual story</h1>
<div class="sub">
  数据：frozen 12-run raw CSVs + S0-004 deterministic corrected analysis（字节级校验）。
  无新 JoSIM 运行；科学裁决不变（C02）。生成器：<span class="mono">plots/generate_story.py</span>。
  中文叙事；原始信号名、单位、窗口与 hash 保留。
</div>

<!-- ============ STATUS CARD ============ -->
<div class="status">
  <div class="scard">
    <div class="k">Question</div>
    <div class="v">固定 12 Ω fixture 下，经两种 operational initialization 后，单次 read 相对 matched control 在 source port 出现什么波形？</div>
  </div>
  <div class="scard">
    <div class="k">Design</div>
    <div class="v">positive / negative initialization × read / zero-input control × 0.1 / 0.05 / 0.025 ps = <b>12 runs</b>，170 ps。</div>
  </div>
  <div class="scard">
    <div class="k">Artifact status</div>
    <div class="v"><span class="pill acc">artifact VALID</span></div>
  </div>
  <div class="scard">
    <div class="k">Scientific disposition</div>
    <div class="v"><span class="pill warn">INCONCLUSIVE</span>
      <div class="note">主波形视觉上接近，但预注册的全相邻 timestep 收敛规则在 <b>control-latency</b> 指标上未满足（0.85 ps &gt; 0.5 ps band）。</div></div>
  </div>
</div>
<div class="noarea">
  ⛔ 禁区：不是 logical read0/read1 · 不是 fluxoid/SFQ 计数 · 不是 receiver/Gate 结论 ·
  不是 resolution-independent source baseline。
</div>

<!-- ============ ACT 1 ============ -->
<div class="act">
<div class="acthead">
  <div class="q">1 · What did we do?</div>
  <div class="why">实验如何初始化、read 与 control 如何匹配——先看时序，再看结构。</div>
</div>

<h3>Experiment timing diagram（registered before execution）</h3>
<div class="timeline">
  <div class="trow"><div class="tlab">Initialization<br>positive</div>
    <div class="track"><span class="tmark" style="left:6%">10–11 ps ramp</span>
      <div class="seg" style="left:7%;width:9%;background:#d1495b"></div>
      <div class="seg" style="left:16%;width:7%;background:#d1495b;opacity:.55"></div>
      <div class="seg" style="left:23%;width:2%;background:#a33"></div>
    </div></div>
  <div class="trow"><div class="tlab">Initialization<br>negative</div>
    <div class="track"><span class="tmark" style="left:6%">10–11 ps ramp</span>
      <div class="seg" style="left:7%;width:9%;background:#4f86c6"></div>
      <div class="seg" style="left:16%;width:7%;background:#4f86c6;opacity:.55"></div>
      <div class="seg" style="left:23%;width:2%;background:#357"></div>
    </div></div>
  <div class="trow"><div class="tlab">Settling</div>
    <div class="track"><div class="seg" style="left:24%;width:48%;background:#e8e8e8"></div>
      <span class="tmark" style="left:49%">21–95 ps quiescent</span></div></div>
  <div class="trow"><div class="tlab">Pre window</div>
    <div class="track"><div class="seg" style="left:49%;width:7%;background:#eef4fb;border:1px solid #1f6fb2"></div>
      <span class="tmark" style="left:52.5%">[80,90) ps</span></div></div>
  <div class="trow"><div class="tlab">Read stimulus<br>(both states, identical)</div>
    <div class="track"><div class="seg" style="left:61%;width:8%;background:#b5457f"></div>
      <span class="tmark" style="left:65%">WL+SE +100 µA @ 96–105 ps</span></div></div>
  <div class="trow"><div class="tlab">Matched zero-read<br>control</div>
    <div class="track"><div class="seg" style="left:61%;width:8%;background:#ccc"></div>
      <span class="tmark" style="left:65%">same fixture; read amplitudes = 0</span></div></div>
  <div class="trow"><div class="tlab">Registered windows</div>
    <div class="track">
      <div class="seg" style="left:59%;width:11%;background:#f3eef7;border:1px solid #8a6bb5"></div>
      <div class="seg" style="left:59%;width:25%;background:transparent;border:1px dashed #8a6bb5"></div>
      <div class="seg" style="left:84%;width:7%;background:#f3eef7;border:1px solid #8a6bb5"></div>
      <span class="tmark" style="left:64%">activity [94,108)</span>
      <span class="tmark" style="left:71%">source [94,130)</span>
      <span class="tmark" style="left:87%">post [140,150)</span>
    </div></div>
</div>
<div class="note warn-note">
  positive / negative 是本任务的 <b>operational initialization labels</b>（write-like state
  preparation），不等同于逻辑 1/0，也不单独证明永久存储态。窗口均在执行前注册，不是事后挑选。
</div>

<h3>Conceptual topology</h3>
<div class="ctop">
  <div class="cbox"><div class="n">Initialization</div><div class="d">WL / BL ±100 µA<br>write-like</div></div>
  <div class="carrow">→</div>
  <div class="cbox"><div class="n">BVM storage region</div><div class="d">S-loop ↔ R-loop</div></div>
  <div class="carrow">↔</div>
  <div class="cbox"><div class="n">read / coupling path</div><div class="d">WL+SE +100 µA</div></div>
  <div class="carrow">→</div>
  <div class="cbox"><div class="n">SL1 + 12 Ω load</div><div class="d">source port</div></div>
</div>
<div class="obsbox">↑ source-port V/I observed here: V(SL1), I(L_SL|XBVM1)</div>

<details>
  <summary>查看 detailed topology（netlist-derived，技术参考）</summary>
  <svg viewBox="0 0 460 300" style="width:100%;" xmlns="http://www.w3.org/2000/svg">
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
    <!-- WL/BL -> N1 (correct) -->
    <text x="10" y="60" class="lbl" font-weight="bold">WL</text>
    <text x="10" y="105" class="lbl" font-weight="bold">BL</text>
    <line x1="28" y1="57" x2="70" y2="57" class="wire"/>
    <line x1="28" y1="102" x2="70" y2="102" class="wire"/>
    <circle cx="70" cy="57" r="3.2" class="node"/><circle cx="70" cy="102" r="3.2" class="node"/>
    <text x="76" y="52" class="lblr">R_WL+L_PWL</text>
    <text x="76" y="97" class="lblr">R_BL+L_PBL</text>
    <circle cx="112" cy="80" r="3.6" class="node"/>
    <text x="106" y="95" class="lbl">N1</text>
    <!-- S-loop -->
    <path d="M112 80 L150 58 L150 120 L112 80" class="sloop"/>
    <path d="M112 80 L112 200" class="sloop"/>
    <text x="142" y="52" class="lblb">B_JM1</text>
    <text x="118" y="66" class="lblb">L_M1→GND</text>
    <circle cx="150" cy="58" r="3.4" class="node"/><circle cx="150" cy="120" r="3.4" class="node"/>
    <text x="156" y="124" class="lblb">B_JM2 (L_M2 above)</text>
    <text x="150" y="140" class="lbl">N2</text>
    <path d="M150 128 L150 170 L210 170" class="sloop"/>
    <text x="158" y="162" class="lblb">L_M3</text>
    <text x="214" y="176" class="lbl">N5</text>
    <circle cx="210" cy="170" r="3.4" class="node"/>
    <path d="M210 170 L210 205" class="sloop"/>
    <text x="196" y="196" class="lblb">L_PM→GND</text>
    <!-- R-loop: N2-LS1-JS1-N3 ; N3-(R_S//L_S3)-N6 ; N6-LS2-JS2-N5 -->
    <path d="M150 128 L200 128 L200 230 L240 230 L240 170" class="rloop"/>
    <text x="192" y="140" class="lblr">L_S1</text>
    <text x="196" y="214" class="lblr">B_JS1</text>
    <circle cx="200" cy="128" r="3.2" class="node"/>
    <circle cx="200" cy="230" r="3.2" class="node"/>
    <text x="188" y="244" class="lblr">N3</text>
    <text x="244" y="244" class="lblr">N6</text>
    <path d="M200 230 L280 230 L280 170" class="rloop"/>
    <text x="252" y="222" class="lblr">R_S // L_S3</text>
    <text x="256" y="204" class="lblr">B_JS2 (L_S2)</text>
    <circle cx="280" cy="230" r="3.2" class="node"/>
    <!-- SE -> N3 (correct) -->
    <text x="40" y="30" class="lbl" font-weight="bold">SE</text>
    <line x1="50" y1="32" x2="80" y2="62" class="wire"/>
    <circle cx="84" cy="62" r="3.2" class="node"/>
    <text x="86" y="48" class="lblr">R_SE+L_PSE</text>
    <path d="M84 62 L200 230" stroke="#b5457f" stroke-width="1.1" stroke-dasharray="3 2" fill="none"/>
    <!-- boxes and coupling -->
    <rect x="90" y="40" width="150" height="180" class="box" stroke="#1f6fb2"/>
    <text x="96" y="232" class="lblb">S-Loop (storage)</text>
    <rect x="140" y="110" width="170" height="140" class="box" stroke="#888"/>
    <text x="196" y="262" class="lblr">R-Loop (readout)</text>
    <line x1="210" y1="170" x2="240" y2="170" stroke="#b5457f" stroke-width="1.8"/>
    <text x="220" y="162" class="lbl" fill="#b5457f" font-size="8.5">N2–LM3–N5 coupling</text>
    <!-- output chain -->
    <path d="M280 230 L330 230 L360 195" class="wire"/>
    <circle cx="330" cy="230" r="3.2" class="node"/>
    <circle cx="360" cy="195" r="3.2" class="node"/>
    <text x="320" y="222" class="lblr">L_PSL</text>
    <text x="352" y="188" class="lblr">R_SL→N8</text>
    <text x="360" y="180" class="lbl" font-weight="bold">SL out (12 Ω)</text>
  </svg>
  <div class="foldnote">Element connectivity from the <b>ACTIVE uncommented</b> <span class="mono">bvm_cell.cir</span> v6：WL/BL→N1，SE→N3（R_SE+L_PSE），N3–N6 经 R_S//L_S3，无 N4/N7（历史注释路径已排除）。仅结构示意，不构成电流/相位结论。</div>
</details>
</div>

<!-- ============ ACT 2 ============ -->
<div class="act">
<div class="acthead">
  <div class="q">2 · What did we observe?</div>
  <div class="why">source port 最关键的观察：同一 read 刺激，两种 initialization 的响应差异。</div>
</div>

<div id="act2-v" style="width:100%;"></div>
<div class="card3">
  <div><div class="h">What this shows</div>
    V(SL1)（source 电压）正/负 initialization 的 read 响应：正读 ≈ +0.89–0.90 mV @ ~5 ps，
    负读 ≈ −0.31 mV @ ~10 ps（0.1/0.05/0.025 ps，baseline-subtracted）。controls 为噪声级（15–18 nV）。
    主曲线为 0.025 ps（最高分辨率，仅用于方向性观察）。I(L_SL) 与 V(SL1) 经 12 Ω KCL/Ohm 直接相关，见 appendix。</div>
  <div><div class="h">Why it matters</div>
    固定 fixture 中，positive/negative preparation 对 source-port response 有<b>可见且状态相关</b>的差异
    （幅度与 latency 均不同），且都远高于 matched zero-read control。</div>
  <div class="no"><div class="h">What it does NOT prove</div>
    不证明 logical bit、state preservation、SFQ/fluxoid、下游接收或接口成功。</div>
</div>

<div class="note">I(L_SL|XBVM1) 与 V(SL1) 在固定 12 Ω 负载下经 KCL/Ohm 直接相关：I_load ≈ V(SL1)/12 Ω（同信息，见 appendix figA2）。Fig3 不再作为独立第二份证据。</div>
<div class="card3">
  <div><div class="h">What this shows</div>
    I(L_SL|XBVM1)（source 电流）同场景：正读 ≈ +74–75 µA @ ~5 ps，负读 ≈ −25.6–26.4 µA @ ~10 ps；
    controls ≈ 1.3–1.5 nA。</div>
  <div><div class="h">Why it matters</div>
    电流幅度差异（约 3×）与 latency 差异（2×）共同构成 state-conditioned source response 的核心证据。</div>
  <div class="no"><div class="h">What it does NOT prove</div>
    不证明 JTL/SFQ 接收、非破坏性读或 logical read 结果。</div>
</div>

<div class="concl"><b>Bounded conclusion：</b>
  same read stimulus → <b>strongly state-conditioned source response</b>
  （固定 fixture、命名窗口、逐 timestep 观察；C02 已接受为有界仿真事实）。</div>
</div>

<!-- ============ ACT 3 ============ -->
<div class="act">
<div class="acthead">
  <div class="q">3 · What happened inside?</div>
  <div class="why">内部 JJ 动力学是支持性证据，不是主结论——默认折叠。</div>
</div>

<details>
  <summary>Local junction diagnostics（JM1/JM2）</summary>
  <div class="foldnote">
    Local same-JJ P/V observations were recorded; these are not downstream-event
    or fluxoid claims. <span class="mono">P(...)</span> = raw phase (rad)；
    显示 turns 时统一为 Δφ/(2π)。一个相位转不等于"一个 SFQ 已被接收"。
  </div>
  <div id="act3-ji" style="width:100%;margin-top:10px;"></div>
  <div class="card3">
    <div><div class="h">What this shows</div>
      JM1/JM2 的 P/V 波形（[80,150) ps）与 pre/post phase 均值；activity 窗 phase
      delta 均远小于 ±1 turn；pre/post 无 gross inversion。</div>
    <div><div class="h">Why it matters</div>
      直接 JJ 探针（同 JJ、同方向、实际时间梯形）提供内部机制的可审计证据，
      与 source-port 观察互补。</div>
    <div class="no"><div class="h">What it does NOT prove</div>
      不证明逻辑态、fluxoid 数、SFQ 事件或下游接收。</div>
  </div>
  <div id="act3-sig" style="width:100%;margin-top:10px;"></div>
</details>
</div>

<!-- ============ ACT 4 ============ -->
<div class="act">
<div class="acthead">
  <div class="q">4 · Why INCONCLUSIVE?</div>
  <div class="why">为什么主信号"看起来稳定"，结论仍是 INCONCLUSIVE。</div>
</div>

<div class="stepflow">
  <div class="s okline">波形视觉上接近（正/负 read 响应可复现，三 timestep 主信号几乎重合）。</div>
  <div class="s">但视觉相似不是预注册通过条件——按注册规则比较相邻 refinement 的全部适用标量。</div>
  <div class="s fail">0.1 → 0.05 ps：matched-control source-peak latency −0.70 ps vs +0.15 ps = <b>0.85 ps</b>；
    registered band = <b>0.5 ps</b> → 该相邻 refinement <b>FAIL</b>。</div>
  <div class="s">0.05 → 0.025 ps 即使通过，也不能覆盖前一对失败。</div>
  <div class="s final"><b>Scientific disposition = INCONCLUSIVE</b>
    （artifact 仍 VALID；阶梯不可扩展、band 不可改）。</div>
</div>

<h3>配套证据：为什么"看起来稳定" vs 正式失败点</h3>
<div id="act4-overlay" style="width:100%;"></div>
<div class="card3">
  <div><div class="h">What this shows</div>
    pos/neg read 的 V(SL1) 完整波形在 0.1/0.05/0.025 ps 下几乎重合（主信号稳定）。</div>
  <div><div class="h">Why it matters</div>
    解释"视觉接近"——主信号本身没有发散或缺失。</div>
  <div class="no"><div class="h">What it does NOT prove</div>
    视觉接近 ≠ 满足全部预注册判定条件；正式结论以注册规则为准。</div>
</div>

<div id="act4-noise" style="width:100%;"></div>
<div class="card3">
  <div><div class="h">What this shows</div>
    matched controls 处于噪声级（15–18 nV / 1.3–1.5 nA）；其峰值 latency 在 0.1→0.05 ps 间从
    −0.70 ps 变到 +0.15 ps（0.85 ps 差）。</div>
  <div><div class="h">Why it matters</div>
    正式失败发生在低幅 control-latency diagnostic，而非 read waveform 本身。</div>
  <div class="no"><div class="h">What it does NOT prove</div>
    不说明 read 信号有问题；也不授权修改注册规则来取得 PASS。</div>
</div>

<div class="rulecard">
  <b>Rule card（预注册 stop rule）：</b>不能事后增加第四个 timestep、修改 tolerance 或移动窗口来取得
  PASS。INCONCLUSIVE does not mean the waveform is absent or the artifact failed.
  It means this registered numerical procedure did not establish
  resolution-independent source evidence for the requested claim level.
</div>
</div>

<!-- ============ BOUNDARY ============ -->
<div class="act">
<div class="acthead">
  <div class="q">结论边界 · Known / Unknown / Next</div>
</div>
<table>
  <tr><th>Known（已建立，有界）</th><th>Unknown（未建立）</th></tr>
  <tr><td>fixed-fixture source-side observations（V/I、latency、controls 噪声级）</td>
      <td>resolution-independent source baseline</td></tr>
  <tr><td>raw/provenance validity（59 项 seal；corrected report 确定性）</td>
      <td>logical read0/read1、write-0/write-1 mapping</td></tr>
  <tr><td>两种 operational initialization 的 state-conditioned source response</td>
      <td>state preservation、SFQ/fluxoid 数、receiver/JTL 接收</td></tr>
  <tr><td>D0 75 ps operational readiness（测试网格内）</td>
      <td>candidate 判定、INTERFACE_GATE_V1、published/hardware reproduction</td></tr>
</table>
<div class="inconcl">
  <b>Next（建议，未执行）：</b>新建独立 preregistered source convergence/characterization task，
  重新设计 zero-control noise-floor waveform metric 的 applicability（低于最小 abs-peak 阈值的
  latency/FWHM 比较标记 NOT_APPLICABLE），考虑预注册可扩展 timestep ladder。等待用户授权。
</div>
</div>

<!-- ============ APPENDIX: EXPLORER ============ -->
<div class="appendix">
<h2>Appendix · Explore raw traces（inspection layer, not a scientific verdict layer）</h2>
<div class="ctrl">
  <span><label>init sign</label>
    <select id="selSign"><option value="positive">positive</option>
    <option value="negative">negative</option></select></span>
  <span><label>read/control</label>
    <select id="selKind"><option value="read">read</option>
    <option value="control">zero-read control</option></select></span>
  <span><label>timestep</label>
    <select id="selStep">
      <option value="0.1ps">0.1 ps</option>
      <option value="0.05ps">0.05 ps</option>
      <option value="0.025ps">0.025 ps</option>
    </select></span>
  <span><label><input type="checkbox" id="chkOverlay">pos vs neg overlay</label></span>
  <span><label><input type="checkbox" id="chkStepOverlay">timestep overlay</label></span>
  <button id="btnPre">⏪ PRE</button>
  <button id="btnRead">▶ READ</button>
  <button id="btnPost">⏩ POST</button>
  <button id="btnAll">⤢ full</button>
</div>
<div id="explorer" style="width:100%;"></div>
<div class="note">
  全部 8 轨（WL/SE stimulus、P/V JM1/JM2、V(SL1)、I(L_SL)）同步 zoom/pan/hover；
  I(L_SL) 轨道与 V(SL1) 为 Ohm/KCL 相关（I≈V/12Ω），属同一 source 信息；
  背景区间：initialization 10–21、settling 21–95、PRE 80–90、READ 96–106、POST 140–150 ps。
  此层用于证据检查，不产生科学裁决。
</div>
<div id="sumTab" style="margin-top:10px;"></div>
</div>

<script>
'use strict';
const DATA = __DATA_JSON__;
const SUM  = __SUMMARY_JSON__;
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
const baseLayout = {
  hovermode:'x unified', margin:{l:60,r:16,t:40,b:40},
  xaxis:{range:[20,160], title:'time (ps)'},
  legend:{orientation:'h', y:1.12, font:{size:10}},
  shapes: BANDS.map(b=>({type:'rect', xref:'x', yref:'paper',
    x0:b.a, x1:b.b, y0:0, y1:1, fillcolor:b.c, opacity:.55,
    line:{width:0}, layer:'below'})),
};
function selCase(){ const s=document.getElementById('selSign').value;
  const k=document.getElementById('selKind').value; return 'init_'+s+'_'+k; }
function selStep(){ return document.getElementById('selStep').value; }

/* ---- Act 2: core pos-vs-neg source figures ---- */
function act2Fig(id, key, unit){
  const traces = [];
  const cases = [['init_positive_read','#d1495b','positive read'],
                 ['init_negative_read','#4f86c6','negative read'],
                 ['init_positive_control','#d9a0aa','positive control'],
                 ['init_negative_control','#a9c3dd','negative control']];
  cases.forEach(([c,color,lab])=>{
    traces.push({type:'scattergl', mode:'lines', name:lab, x:DATA[c+'/0.025ps'].t,
      y:DATA[c+'/0.025ps'].c[key].map(v=>v*(key==='V_SL1'?1e3:1e6)),
      line:{color, width: lab.indexOf('control')>=0 ? 1.1 : 2.0,
            dash: lab.indexOf('control')>=0 ? 'dot' : 'solid'},
      hovertemplate:lab+': %{y:.4g} '+unit+'<extra></extra>'});
  });
  Plotly.newPlot(id, traces, {
    ...baseLayout,
    title:{text:(key==='V_SL1'?'V(SL1)':'I(L_SL|XBVM1)')+
      ' — positive vs negative read (0.025 ps) · controls as dotted inset',
      font:{size:13}},
    yaxis:{title:(key==='V_SL1'?'mV':'µA'), tickfont:{size:10}},
  }, {responsive:true, displaylogo:false});
}
act2Fig('act2-v', 'V_SL1', 'mV');


/* ---- Act 3: JM1/JM2 diagnostics ---- */
(function(){
  const traces = [];
  const cases = [['init_positive_read','#d1495b','pos read'],
                 ['init_negative_read','#4f86c6','neg read']];
  cases.forEach(([c,color,lab])=>{
    ['P_JM1','P_JM2'].forEach((k,i)=>{
      traces.push({type:'scattergl', mode:'lines',
        name:lab+' '+(k==='P_JM1'?'P(JM1)':'P(JM2)'),
        x:DATA[c+'/0.025ps'].t, y:DATA[c+'/0.025ps'].c[k],
        line:{color: i===0?color:'#e07b00', width:1.3, dash: i===1?'dot':'solid'},
        hovertemplate:lab+' %{y:.5g} rad<extra></extra>'});
    });
  });
  Plotly.newPlot('act3-ji', traces, {
    ...baseLayout,
    title:{text:'JM1/JM2 phase (raw rad) — pos vs neg read (0.025 ps)',
           font:{size:13}},
    yaxis:{title:'phase (rad)', tickfont:{size:10}},
  }, {responsive:true, displaylogo:false});
  // pre/post signature bars
  const cs=['init_positive_read','init_negative_read'];
  const xs=[], ys=[]; const cols=[];
  cs.forEach((c,ci)=>{
    STEPS.forEach((s,si)=>{
      const pre=SUM[c+'/'+s].pre, post=SUM[c+'/'+s].post;
      ['JM1','JM2'].forEach((jj)=>{
        xs.push((ci*6+si*2+(jj==='JM1'?0:1))+0.5);
        ys.push(pre[jj], post[jj]);
        cols.push(jj==='JM1'?'#1f6fb2':'#e07b00');
      });
    });
  });
  const bx=[], by=[], bt=[];
  cs.forEach((c,ci)=>{
    STEPS.forEach((s,si)=>{
      const pre=SUM[c+'/'+s].pre, post=SUM[c+'/'+s].post;
      ['JM1','JM2'].forEach((jj)=>{
        bx.push(ci*6+si*2+(jj==='JM1'?0:1), ci*6+si*2+(jj==='JM1'?0:1));
        by.push(pre[jj], post[jj]);
        bt.push(c.split('_')[1]+' '+s+' '+(jj==='JM1'?'pre':'post'));
      });
    });
  });
  Plotly.newPlot('act3-sig', [{
    type:'bar', x:bx, y:by, marker:{color:cols}, hovertemplate:'%{y:.6g} rad<extra></extra>',
    text:bt, textposition:'none'}], {
    title:{text:'Pre [80,90) / post [140,150) JM1/JM2 phase means (operational signature)',
           font:{size:13}},
    xaxis:{tickangle:0, showticklabels:false}, yaxis:{title:'phase (rad)'},
    margin:{l:60,r:16,t:44,b:40},
  }, {responsive:true, displaylogo:false});
})();

/* ---- Act 4: overlay + noise zoom ---- */
(function(){
  const traces=[];
  STEPS.forEach((st,i)=>{
    traces.push({type:'scattergl', mode:'lines', name:st+' pos read',
      x:DATA['init_positive_read/'+st].t,
      y:DATA['init_positive_read/'+st].c.V_SL1.map(v=>v*1e3),
      line:{color:['#c7c7c7','#8a8a8a','#333333'][i], width:1.3},
      hovertemplate:st+': %{y:.4g} mV<extra></extra>'});
    traces.push({type:'scattergl', mode:'lines', name:st+' neg read',
      x:DATA['init_negative_read/'+st].t,
      y:DATA['init_negative_read/'+st].c.V_SL1.map(v=>v*1e3),
      line:{color:['#c7c7c7','#8a8a8a','#333333'][i], width:1.3, dash:'dot'},
      hovertemplate:st+': %{y:.4g} mV<extra></extra>'});
  });
  Plotly.newPlot('act4-overlay', traces, {
    ...baseLayout, yaxis:{title:'V(SL1) (mV)'},
    title:{text:'Timestep overlay — read waveforms look stable',
           font:{size:13}},
  }, {responsive:true, displaylogo:false});

  const ntraces=[];
  ['init_positive_control','init_negative_control'].forEach((c)=>{
    STEPS.forEach((st,i)=>{
      ntraces.push({type:'scattergl', mode:'lines',
        name:c.split('_')[1]+' ctrl '+st,
        x:DATA[c+'/'+st].t, y:DATA[c+'/'+st].c.V_SL1.map(v=>v*1e9),
        line:{color:['#c7c7c7','#8a8a8a','#333333'][i], width:1.1},
        hovertemplate:'%{y:.3g} nV<extra></extra>'});
    });
  });
  Plotly.newPlot('act4-noise', ntraces, {
    ...baseLayout, yaxis:{title:'V(SL1) (nV)'},
    title:{text:'Matched-control residual — low-amplitude; latency diagnostic shows grid sensitivity (0.85 ps > 0.5 ps band)',
           font:{size:13}},
  }, {responsive:true, displaylogo:false});
})();

/* ---- Appendix explorer ---- */
(function(){
  const n=TRACKS.length;
  const dom=(i)=>[1-(i+1)/n, 1/n];
  const traces=TRACKS.map((tr,i)=>({
    type:'scattergl', mode:'lines', name:tr.l, x:[], y:[],
    line:{color:tr.c, width:1.2}, xaxis:'x', yaxis:'y'+(i+1),
    hovertemplate:tr.l+': %{y:.6g}'+tr.u+'<extra></extra>'}));
  const layout={...baseLayout, hovermode:'x unified'};
  TRACKS.forEach((tr,i)=>{
    layout['yaxis'+(i+1)]={domain:dom(i), title:{text:tr.l+' ('+tr.u+')',
      font:{size:10}}, tickfont:{size:9}};
  });
  Plotly.newPlot('explorer', traces, layout, {responsive:true, displaylogo:false});

  function updateExplorer(){
    const cs=selCase(), st=selStep();
    const upd={};
    TRACKS.forEach((tr,i)=>{
      upd['x'+(i+1)]=[DATA[keyOf(cs,st)].t];
      upd['y'+(i+1)]=[DATA[keyOf(cs,st)].c[tr.k].map(v=>v*tr.s)];
    });
    const extra=[];
    const srcIdx=[6,7];
    if (document.getElementById('chkOverlay').checked){
      const other=(cs.indexOf('positive')>=0)?cs.replace('positive','negative')
        :cs.replace('negative','positive');
      srcIdx.forEach(i=>{const tr=TRACKS[i];
        extra.push({type:'scattergl', mode:'lines', name:'overlay '+tr.l,
          x:DATA[keyOf(other,st)].t, y:DATA[keyOf(other,st)].c[tr.k].map(v=>v*tr.s),
          line:{color:'#555',width:1.1,dash:'dot'}, xaxis:'x', yaxis:'y'+(i+1)});});
    }
    if (document.getElementById('chkStepOverlay').checked){
      STEPS.forEach(stp=>{srcIdx.forEach(i=>{const tr=TRACKS[i];
        extra.push({type:'scattergl', mode:'lines', name:stp+' '+tr.l,
          x:DATA[keyOf(cs,stp)].t, y:DATA[keyOf(cs,stp)].c[tr.k].map(v=>v*tr.s),
          line:{color:'#999',width:1.0,dash:'dot'}, xaxis:'x', yaxis:'y'+(i+1)});});});
    }
    Plotly.react('explorer', traces.concat(extra), layout, {responsive:true});
    const s=SUM[keyOf(cs,st)];
    document.getElementById('sumTab').innerHTML=
      '<table><tr><th>case</th><th>'+cs+'</th></tr>'+
      '<tr><td>timestep</td><td>'+st+'</td></tr>'+
      '<tr><td>V(SL1) peak (baseline-subtracted)</td><td>'+(s.v_peak*1e3).toFixed(3)+' mV</td></tr>'+
      '<tr><td>V(SL1) latency from 96 ps</td><td>'+(s.v_lat*1e12).toFixed(1)+' ps</td></tr>'+
      '<tr><td>I(L_SL) peak</td><td>'+(s.i_peak*1e6).toFixed(2)+' µA</td></tr>'+
      '<tr><td>I(L_SL) latency</td><td>'+(s.i_lat*1e12).toFixed(1)+' ps</td></tr>'+
      '<tr><td>pre JM1/JM2</td><td>'+s.pre.JM1.toFixed(6)+' / '+s.pre.JM2.toFixed(6)+' rad</td></tr>'+
      '<tr><td>post JM1/JM2</td><td>'+s.post.JM1.toFixed(6)+' / '+s.post.JM2.toFixed(6)+' rad</td></tr>'+
      '<tr><td>JM1/JM2 phase_delta turns [94,108)</td><td>'
      +s.phase_area.JM1.phase_delta_turns.toFixed(6)+' / '
      +s.phase_area.JM2.phase_delta_turns.toFixed(6)+'</td></tr></table>';
  }
  function keyOf(cs,st){return cs+'/'+st;}
  function setRange(a,b){Plotly.relayout('explorer',{'xaxis.range':[a,b]});}
  document.getElementById('selSign').onchange=updateExplorer;
  document.getElementById('selKind').onchange=updateExplorer;
  document.getElementById('selStep').onchange=updateExplorer;
  document.getElementById('chkOverlay').onchange=updateExplorer;
  document.getElementById('chkStepOverlay').onchange=updateExplorer;
  document.getElementById('btnPre').onclick=()=>setRange(75,95);
  document.getElementById('btnRead').onclick=()=>setRange(92,112);
  document.getElementById('btnPost').onclick=()=>setRange(135,155);
  document.getElementById('btnAll').onclick=()=>setRange(20,160);
  updateExplorer();
})();
</script>
</div>
</body>
</html>
"""

if __name__ == '__main__':
    raise SystemExit(main())
