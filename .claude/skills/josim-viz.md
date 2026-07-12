---
name: josim-viz
description: >
  JoSIM 仿真结果可视化。适用于 standard 标准元件库测试的可视化需求。
  触发词：可视化、画图、看图、出图、plot、图表、分析波形。
  仅在本项目 (JoSIM) 生效。
---

# JoSIM 可视化

## 触发条件

当用户提到以下任一关键词时调用本 skill：
- 可视化、画图、看图、出图、plot、图表、波形
- "看一下 xxx 的结果"、"帮我看 xxx 的波形"
- 需要分析某个标准元件的测试结果

## 项目约定

- 测试文件位置：`test/standard/test_<cell>.cir`
- 电路文件位置：`circuits/standard/<CELL>.cir`
- 模型文件：`circuits/models/jjmit.cir`
- 仿真工具：`./build/josim-cli`
- 绘图工具：`scripts/josim-plot2.py`
- CSV 缓存：`/tmp/test_<cell>.csv`
- HTML 输出：`test/standard/<cell>.html`

## 工作流程

### 1. 确定元件

从用户输入中识别元件名（小写）：`jtl`, `split`, `merge`, `dff`, `xor`, `and2`, `ndro`

### 2. 运行仿真（如需要）

如果 `/tmp/test_<cell>.csv` 不存在，或测试 `.cir` 文件有更新，先运行：

```bash
./build/josim-cli -o /tmp/test_<cell>.csv test/standard/test_<cell>.cir
```

### 3. 确定信号范围

根据用户需求选择信号模式：

| 用户说法 | 模式 | 信号范围 |
|---------|------|---------|
| "只看输入输出"、"io"、"输入输出就行" | `io` | 仅 V(SFQ_*) I/O 电压 + Load JTL 相位 |
| "看结的相位"、"jj翻转"、"约瑟夫森结" | `jj` | 所有 P(Bn\|X*) 结相位 + I/O 信号 |
| "所有元件"、"完整"、"全部"、"详细" | `full` | 全部 .print 信号（结+电感+偏置+I/O） |

**默认**：如果用户没有明确指定范围，用 `io` 模式（只看输入输出）。

### 4. 确定布局

| 用户说法 | 布局参数 |
|---------|---------|
| "分组显示"、"分组"、"按类型分" | `-t sep_comb` |
| "独立窗格"、"一个个"、"分开看" | `-t grid` |
| "叠加"、"放一起"、"合在一起" | `-t combined` |
| 未指定 | `-t sep_comb`（默认分组） |

### 5. 生成 HTML

```bash
python3 scripts/josim-plot2.py /tmp/test_<cell>.csv \
  -s <信号列表> \
  -t <布局> \
  -j 2pi \
  -c dark \
  -x test/standard/<cell>.html
```

固定参数：
- `-j 2pi`：相位以磁通量子 (Φ₀) 为单位，1.0 = 1 SFQ
- `-c dark`：暗色主题

### 6. 报告结果

生成后告诉用户：
- HTML 文件路径和大小
- 包含哪些信号
- 如果结果中有明显的 SFQ 翻转，简要说明输入输出关系（如 "CLK@35ps 有 1 个 SFQ 输出"）

## 各元件 I/O 信号对照

| 元件 | 输入信号 | 输出信号 | Load 相位 |
|------|---------|---------|----------|
| JTL | V(SFQ_IN), V(SFQ_MID) | — | P(B1\|XLOAD), P(B2\|XLOAD) |
| SPLIT | V(SFQ_IN) | V(Q0), V(Q1) | P(B1\|XJTL0), P(B2\|XJTL0), P(B1\|XJTL1), P(B2\|XJTL1) |
| MERGE | V(SFQ_A), V(SFQ_B) | V(SFQ_Q), V(SFQ_OUT) | P(B1\|XLOAD), P(B2\|XLOAD) |
| DFF | V(SFQ_D), V(SFQ_CLK) | V(SFQ_Q) | P(B1\|XLOAD), P(B2\|XLOAD) |
| XOR | V(SFQ_A), V(SFQ_B), V(SFQ_CLK) | V(SFQ_Q) | P(B1\|XLOAD), P(B2\|XLOAD) |
| AND2 | V(SFQ_A), V(SFQ_B), V(SFQ_CLK) | V(SFQ_Q) | P(B1\|XLOAD), P(B2\|XLOAD) |
| NDRO | V(SFQ_D), V(SFQ_R), V(SFQ_CLK) | V(SFQ_Q) | P(B1\|XLOAD), P(B2\|XLOAD) |

## 使用示例

```
用户: 可视化 and2，只看输入输出，分组显示
→ 生成 io 模式 + sep_comb 布局

用户: 帮我看看 xor 的波形，所有元件都要
→ 生成 full 模式 + sep_comb 布局

用户: 画一下 dff 结的相位，独立窗格
→ 生成 jj 模式 + grid 布局

用户: plot jtl
→ 默认 io 模式 + sep_comb 布局
```
