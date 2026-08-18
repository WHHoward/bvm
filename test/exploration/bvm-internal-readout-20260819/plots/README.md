# BVM 2×2 state/READ readout — visual index

生成：2026-08-19 | 工具：`scripts/josim-plot2.py`（josim-viz skill 成熟默认：
interactive HTML / Plotly / sep_comb / `-j 2pi` / dark）| 不重跑 JoSIM，
直接消费 `raw/**` 已有 CSV。四图 signal set、layout、theme、phase unit、
title 命名完全一致，可并排比较。

## Files

| 文件 | source raw | state/read | 语义 |
|---|---|---|---|
| `logical1-canonical-read.html` | `raw/pos-read-single/run-01.csv` | logical 1（+init）+ canonical +READ | 正式 read1 |
| `logical0-canonical-read.html` | `raw/neg-init-pos-read/run-01.csv` | logical 0（−init）+ canonical +READ | 正式 read0 |
| `stateA-negative-read-diagnostic.html` | `raw/pos-init-neg-read/run-01.csv` | state A（+init）+ −READ | polarity diagnostic only |
| `stateB-negative-read-diagnostic.html` | `raw/neg-read-single-corr/run-01.csv` | state B（−init）+ −READ | polarity diagnostic only |

（state/read 命名与 `BVM_LOGICAL_SEMANTICS_V1.md` 一致；state A/B 为
operational states，logical 1/0 为冻结语义。）

## 每图 signal set（14，与 CSV header 逐字一致）

`I(I_WL1)` `I(I_SE1)` `P(B_JS1|XBVM1)` `V(B_JS1|XBVM1)` `P(B_JS2|XBVM1)`
`V(B_JS2|XBVM1)` `V(N6|XBVM1)` `V(SL1)` `I(L_S1|XBVM1)` `I(L_S2|XBVM1)`
`I(L_S3|XBVM1)` `I(L_M3|XBVM1)` `I(L_PSL|XBVM1)` `I(L_SL|XBVM1)`

分组：Sources（I_WL1/I_SE1）→ JS1/JS2 phase+voltage → Nodes（N6/SL）→
R-loop/output currents（L_S1/S2/S3/M3/PSL/SL）。

## 可直接观察什么

- **logical1 vs logical0（canonical +READ）**：
  - JS1/JS2 phase running vs no-running（~3 turns 持续旋转 vs 平坦+边沿小响应）；
  - V(B_JS1/JS2) 持续振荡 vs 边沿尖峰；
  - V(N6)/V(SL1) 幅度差（约 2.8–2.9×）；
  - I(L_S1/S2/S3) running 电流 vs 静态小电流；
  - I(L_PSL)/I(L_SL) 输出链幅度差。
- **diagnostic 图（−READ）**：与 canonical 图对比可见 matched/mismatched
  对 running 的调制（mismatched → no running）。

## Claim ceiling

- **phase turns ≠ SFQ count**；`-j 2pi` 仅显示 `phase (rad/2π)`，图中
  相位轴为 turns，不是事件数。
- 本 visualization 只作 descriptive convenience，**不产生新的 scientific
  authority**；SFQ/Gate/receiver 判定需独立预注册实验与审计
  （docs/HANDOVER.md 可视化边界约定）。
- 数值以 `raw/**` CSV 与 `analysis-v3.json` / `state-matrix-2x2.json` 为准；
  图不做 smoothing / resample / 重算。
