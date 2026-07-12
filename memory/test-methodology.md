---
name: test-methodology
description: 标准元件测试方法论 — 文件位置、测试结构、I/O 信号命名、验证标准、可视化工作流
metadata: 
  node_type: memory
  type: project
  originSessionId: c5521155-33ba-4655-a787-c46e6bb6b2b1
---

## 标准元件测试方法论

### 文件约定

```
circuits/standard/<CELL>.cir    ← 电路子电路（端口: a b clk q 等）
circuits/models/jjmit.cir       ← JJ 模型
test/standard/test_<cell>.cir   ← 测试文件
test/standard/<cell>.html       ← 可视化结果
/tmp/test_<cell>.csv            ← 仿真输出（缓存）
```

### 测试文件结构

```spice
.include ../../circuits/models/jjmit.cir
.include ../../circuits/standard/<CELL>.cir
.include ../../circuits/standard/JTL.cir    # 输出负载

* 输入脉冲（2ps 宽度）
V_IA INA 0 pwl(0 0 10p 0 15p 0 16p 1.5m 18p 1.5m 19p 0 100p 0)
R_IA INA N1 3
L_IA N1 SFQ_A 0.5p

* DUT
XCELL SFQ_A SFQ_B SFQ_CLK SFQ_Q THmitll_<CELL>

* Load JTL（验证 SFQ 输出）
XLOAD SFQ_Q SFQ_OUT THmitll_JTL
R_TERM SFQ_OUT 0 1

.tran 0.1p <duration>
.print ...  # 探测信号
.end
```

### I/O 信号命名（josim-plot2 用）

| 元件 | 输入 | 输出 | Load 相位 |
|------|------|------|-----------|
| JTL | V(SFQ_IN), V(SFQ_MID) | — | P(B1\|XLOAD), P(B2\|XLOAD) |
| SPLIT | V(SFQ_IN) | V(Q0), V(Q1) | P(B1\|XJTL0), P(B2\|XJTL0), P(B1\|XJTL1), P(B2\|XJTL1) |
| MERGE | V(SFQ_A), V(SFQ_B) | V(SFQ_Q), V(SFQ_OUT) | P(B1\|XLOAD), P(B2\|XLOAD) |
| DFF | V(SFQ_D), V(SFQ_CLK) | V(SFQ_Q) | P(B1\|XLOAD), P(B2\|XLOAD) |
| XOR | V(SFQ_A), V(SFQ_B), V(SFQ_CLK) | V(SFQ_Q) | P(B1\|XLOAD), P(B2\|XLOAD) |
| AND2 | V(SFQ_A), V(SFQ_B), V(SFQ_CLK) | V(SFQ_Q) | P(B1\|XLOAD), P(B2\|XLOAD) |
| NDRO | V(SFQ_D), V(SFQ_R), V(SFQ_CLK) | V(SFQ_Q) | P(B1\|XLOAD), P(B2\|XLOAD) |

### 验证标准

- **JTL/SPLIT/MERGE**: Load JTL B1 相位跳变 = 预期 SFQ 数量
- **XOR/AND2**: 真值表逐项验证（每个时钟周期检测 SFQ 有无）
- **DFF**: 数据→时钟→输出，1 SFQ
- **NDRO**: 写→读(有输出)→复位→读(无输出)

### 可视化命令

```bash
python3 scripts/josim-plot2.py /tmp/test_<cell>.csv \
  -s <I/O信号列表> \
  -t sep_comb -j 2pi -c dark \
  -x test/standard/<cell>.html
```

固定参数：`-j 2pi`（相位=SFQ 个数）`-c dark`（暗色主题）`-t sep_comb`（电压/相位分组）

[[coldflux-library]] [[sfq-physics]]
