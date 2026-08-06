# circuits — 电路元件目录索引

> **维护规则 (2026-08-06)**: 新元件目录需在此登记；标准库元件冻结不改。

| 目录/文件 | 内容 | 状态 |
|-----------|------|------|
| `standard/` | ColdFlux 35 元件库（INDEX.md 详细索引） | 🟢 冻结，8/8 核心验证 |
| `interface/` | **DCSFQ_BVM**（H7 主路线接口元件，Phase 0 已建） | 🟢 当前主线 |
| `bvm/` | BVM 磁通涡旋存储器（v6, jjmit） | 🟢 使用中 |
| `qb/` | BQ 量化缓冲器（v2/v4） | ⏸️ BQ 路线已排除，保留参考 |
| `models/` | JJ 模型（jjmit.cir = 冻结口径） | 🟢 冻结 |
| `t1/` | T1 全加器 | 🔴 未验证 |
| `sfq_gen.cir` `sfq_gen_clk.cir` `sfq_gen_i.cir` | 单结 SFQ 发生器 | ⏸️ 已放弃，**测试引用保留在根目录**（勿移） |

**冻结口径**: jjmit (Ic×RN=1.6mV)；新元件必须自含（不 .include 标准库再修改）；RB/LRB 用 ColdFlux 公式 (6.86/area)。
