---
name: t1-full-adder
description: T1 全加器 — 18 节点、11 结、多结耦合相位累积/量化单元，接收来自阵列的小电流并量化为 SFQ
metadata: 
  node_type: memory
  type: project
  originSessionId: c5521155-33ba-4655-a787-c46e6bb6b2b1
---

## T1 全加器

### 位置

- 电路: `circuits/t1/t1_cell.cir`
- 测试: `test/final/t1/test_t1.cir` 等
- 文档: `arti/T1.md`, `arti/T1_structure.md`, `arti/t1str.md`

### 功能

多结耦合相位累积/量化单元。接收来自阵列或前级的缓慢小电流，通过本地 JJs 量化为 SFQ 脉冲输出。

### 端口

| 端口 | 含义 |
|------|------|
| I | 输入（来自阵列/前级） |
| C | 进位输出 |
| CLK | 时钟 |
| S | 和输出 |

### 规模

- 18 个节点 (N1-N18)
- 11 个约瑟夫森结
- 17 个电感、3 个电阻
- 使用 `jjmit` 模型

### 拓扑三段

1. **顶部行**: CLK 路径
2. **中央耦合网络**: 连接/分配
3. **底部行**: 主 I→C 路径

### 已验证

sfq_gen_clk (4/4), sfq_gen_i (10/10), T1 CLK 隔离 (5/5)

[[jj-model-parameters]] [[coldflux-library]]
