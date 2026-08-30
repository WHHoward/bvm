# BVM 9ps/13ps read-width → QB — visual index

生成：2026-08-30 | 工具：`scripts/josim-plot2.py`（josim-viz 经典方案：
interactive HTML / Plotly / sep_comb / `-j 2pi` / dark）| 不重跑 JoSIM，
直接消费既有 raw。6 张图为独立文件，可分别打开并排比较。

## Files

| 文件 | source raw | 语义 |
|---|---|---|
| `9ps-bvm-logical1-read.html` | `test/exploration/bvm-internal-readout-20260819/raw/pos-read-single/run-01.csv` | 9ps READ（canonical 96–105p）+ logical 1，BVM source-only |
| `13ps-bvm-logical1-read.html` | `test/exploration/bvm-read-semantics-audit-and-jsl-width-bracket-v1-20260824/raw/13ps/logical1-read/run-01.csv` | 13ps READ（96–109p）+ logical 1，BVM source-only（12-JSL load） |
| `9ps-ideal-replay-to-qb.html` | `test/exploration/qb-q2a-source-decoupled-waveform-replay-20260824/raw/C-canonical-logical1-vsl-replay.csv` | 9ps BVM 输出 V(SL1) 理想源重放 → frozen scaled QB |
| `13ps-ideal-replay-to-qb.html` | `test/exploration/bvm-read-semantics-audit-and-jsl-width-bracket-v1-20260824/raw/replay/13ps/logical1_read/run-01.csv` | 13ps BVM 输出理想源重放 → QB |
| `9ps-physical-bvm-to-qb.html` | `test/exploration/qb-q1-canonical-bvm-scaled-qb-compatibility-20260824/raw/logical1-read.csv` | 9ps BVM galvanic 真实接入 QB（QB_SOURCE_BACKACTION_FAILURE） |
| `13ps-physical-bvm-to-qb.html` | `test/exploration/physical-bvm-jsl12-qb-sfq-closure-v1-20260824/raw/13/logical1_read/run-01.csv` | 13ps BVM→12-JSL→QB 真实级联（PHYSICAL_BACKACTION_PREVENTS_CLOSURE） |

## 信号集

- **BVM source-only 图**：JM1/JM2 + JS1/JS2 相位与同一结电压、V(N6)、V(SL)、
  I(L_SL)（+L_S1/S2/S3 或 L_PSL）
- **IDEAL replay 图**：BJs/BJL1/BJL2 相位与电压、V(IN)、V(OUT)、I(LIN)、
  I(L0)、I(R_LOAD)、replay 源电流
- **PHYSICAL 级联图**：BVM 侧（JS1/JS2、V(N6)、V(SL)、I(L_SL)）+ QB 侧
  （BJs/BJL2、V(IN)/V(SL1)、V(OUT)、I(R_LOAD)）
- 全部从 CSV header 读取确认，无猜测 probe name。

## 可直接观察什么

- **9ps vs 13ps BVM**：read plateau 加宽如何改变 JS1/JS2 running 圈数与
  N6/SL 幅度（9ps ≈3-turn running；13ps 仍有强 activity）
- **ideal replay 到 QB**：BJL2 的最大同向段 9ps（accepted Q1 comparator
  0.893 turn）/ 13ps（1.016 turn CLEAN_ONE_SFQ_CANDIDATE）——理想源下
  BJL2 可达 ~1 turn
- **physical 接入**：同一信号在真实级联下 BJL2 只有反向 sub-turn
  （−0.122 turn @13ps / −0.098 turn @9ps），方向反转 + 幅度衰减 →
  BACKACTION 阻止 closure 的直观证据

## Claim ceiling

- phase turns ≠ SFQ count；（`-j 2pi` 仅显示 rad/2π turns）
- visualization 只作 descriptive convenience，不产生新 scientific
  authority；verdict 以各实验 REPORT.md（QB_SOURCE_BACKACTION_FAILURE /
  PHYSICAL_BACKACTION_PREVENTS_CLOSURE 等）为准。
- 不重算 data，不做 smoothing/resample。
