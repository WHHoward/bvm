---
name: josim-viz
description: Visualize JoSIM CSV or DAT traces and inspect superconducting circuit waveforms with correct phase units. Use for plotting, waveform comparison, signal selection, HTML/image output, or visual inspection of standard cells, BVM, BQ, DCSFQ, JTL, and T1 results; plotting alone must not be used to certify SFQ events or system Gates.
---

# JoSIM 波形可视化

## 工作流程

1. 确认输入 CSV/DAT、对应网表和研究问题；只画图时不要擅自重跑仿真。
2. 读取 CSV 表头，使用其中的精确列名；不要使用 `P(Bn|X*)` 之类的伪通配符。
3. 选择最少但足以回答问题的信号：输入、状态、待审计 JJ 的 `P(...)`/`V(...)`、输出及加载后的 JTL。
4. 默认生成可交互 HTML；研究运行的图放在相应 run 的 `plots/`，标准单元临时图也不得成为唯一证据。
5. 生成后检查文件存在、大小非零、标题/轴标签和所选信号正确。
6. 仅报告图中可直接观察的现象；需要 SFQ/Gate 判定时调用 `josim-evidence-audit`。

## 相位单位硬规则

- JoSIM `P(...)` 原始数据是 phase rad。
- `-j 2pi` 只是把绘图值除以 (2\pi)，应称为 `phase turns (rad/2π)`，不能标成 `SFQ count`。
- 绝对相位 1 圈、净相位约 1 圈或一条陡边都不自动证明下游收到一个 SFQ。
- 比较事件时使用声明的事件前/后稳定窗或匹配控制，不用任意端点。

### 当前绘图脚本限制

`scripts/josim-plot2.py` 的历史布局问题已由数据级回归覆盖：当前 `grid`、
`stacked`、`combined`、`square`、`sep_comb` 都在 `-j 2pi` 下对相位数据真实除以
`2*pi`。回归位置为 `test/plot/test_josim_plot2.py`；若未来修改 backend，必须先
修复并通过该回归，不能只改轴标签。

新实验默认使用 `visualization.mode: compact` 和 `CLASSIC_LOCKED`：只选 2–5 条
关键波形，固定 `sep_comb` / `dark` / `-j 2pi`。`full` 只在用户或配置明确
opt-in 时增加信号；alternative visual style 需要用户明确授权。

## 推荐命令

先从 CSV 表头复制精确列名，再逐个引用：

```bash
python3 scripts/josim-plot2.py path/to/run/raw.csv \
  -s 'I(INPUT)' 'P(B1|XCELL)' 'V(B1|XCELL)' 'P(B1|XLOAD)' \
  -t sep_comb -j 2pi -c dark \
  -x path/to/run/plots/overview.html \
  -w 'Run ID — input, local junction, and loaded JTL'
```

若不能确认 `V(B1|XCELL)` 与 `P(B1|XCELL)` 是同一 JJ、同方向，图中保留原标签，不做相位—面积结论。

`RESULT_BRIEF.md` 解释科学意义，`plots/RESULT_OVERVIEW.html` 负责让用户直接
看到 classic waveform；图本身不产生 SFQ 或 system Gate 结论。

## 仿真边界

只有用户要求生成或刷新数据时才运行 `build/josim-cli`。原始输出写入唯一、不可覆盖的研究目录，并遵循 `josim-experiment`；不要把 `/tmp` 中的缓存当成研究证据。目前不得用 `scripts/run_exp.sh` 生成物理 Gate，因为它仍调用失效的 v1 指标。

## 报告格式

报告输入文件、输出文件、布局、相位显示单位和信号列表。把“观察”与“解释”分开，例如：

- 观察：事件后 B1 的相位平台比事件前高约一圈。
- 尚不能推出：下游已接收一个合格 SFQ；还需同 JJ 电压面积、对照、加载 JTL 和收敛证据。
