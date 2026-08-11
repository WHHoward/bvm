---
name: reviewer-adversarial
description: Canonical adversarial review rules — hunt hidden failures that make a result look correct while being wrong. Use when reviewing any non-trivial implementation or result claim; wrapper at .github/skills/adversarial-review.
---

# Adversarial Review（canonical）

> 单一规范源：本文件是 adversarial review 的权威规则。`.github/skills/adversarial-review/` 只是 Copilot wrapper，引用本文件，不复制规则。

## 核心哲学

> **先问"什么隐蔽错误会让结果看起来对、实际错？"，再问"我怎样证明它对？"**

目标不是证明正确，而是**证伪 executor 的最强有界声明**；无法证伪时才用独立证据支持 review PASS。

## 审查流程

1. 识别 executor 的最强有界声明（RESULT 的 Claim 中可检验的核心句）；
2. 生成隐藏错误假设：NORMAL 3–5 个、CRITICAL 5–10 个；
3. 按「影响 × 可能性 × 可测性」排序；
4. 测试最高价值假设（每项：假设 → 探针 → 结果）；
5. 剩余低价值/已覆盖假设停止扩展。

## 标准隐藏错误探针

| 探针 | 找什么 |
|---|---|
| No-op | 实现是否实际改变任何行为（恒等输出、死代码、空循环） |
| Constant-output | 是否对任何输入都返回同一结果（硬编码、忽略输入） |
| Wrong-branch | 是否走了错误分支（条件颠倒、默认分支吞掉主路径） |
| Weak-oracle | 测试判据是否太弱（同错 helper、被测逻辑与断言同源、oracle 与实现共享错误） |
| Boundary | 边界/阈值附近是否翻转（0/2π、窗口边缘、±阈值） |
| Metamorphic | 等价变换下结果是否应不变（重排、缩放、对称） |
| Differential | 与参考实现/独立路径对比是否一致 |
| Stale-artifact | 是否引用了旧产物（缓存、旧 CSV、旧 run、过期哈希） |
| Hidden-state | 是否有跨调用残留状态（全局变量、环境、未复位累加器） |
| Coupling | 是否错误耦合（改 A 影响 B 且未声明、共享可变状态） |
| Overclaim | claim 是否超出实际证据支持（执行成功→物理成立、局部→下游） |

## 纪律

- 假设必须**可测试**：每条假设给出探针命令或证据检查，不能只列怀疑；
- 结果如实记录（假设 → 探针 → 结果），未验证的假设列入 Residual uncertainty；
- 不修改实现/证据；发现即写入 REVIEW.md；
- NORMAL 保持抽样深度，CRITICAL 全部高价值探针执行。
