---
name: reviewer-numerical
description: Canonical numerical-science review rules — units, sign, integration, windows, thresholds, precision, convergence, sensitivity. Use when reviewing numeric output, metrics, thresholds, or derived data; wrapper at .github/skills/numerical-science-review.
---

# Numerical Science Review（canonical）

> 单一规范源：本文件是数值科学审查的权威规则。`.github/skills/numerical-science-review/` 只是 Copilot wrapper。
> 实验纪律（不可覆盖 raw、run ID、manifest、evidence path）复用 `josim-experiment`。

## 检查清单

### 1. 单位与量纲

- 每个数字的单位是否明确（rad / turns / s / µA / mV）；
- `Δφ/(2π)` 换算是否显式、是否出现漏除或重复除；
- 时间列实际单位（JoSIM CSV 为秒）与打印/绘图单位转换是否一致。

### 2. 符号与方向

- 端点/节点顺序是否与声明方向一致；
- 是否有用绝对值掩盖符号错误；
- 电压参考与结方向是否匹配（相位—面积交叉校验同端点同方向）。

### 3. 积分与采样

- 使用 CSV 实际 time 列梯形积分，不假定固定间隔；
- 非均匀采样是否被正确处理；
- 窗口边界是否排除/包含正确的样本。

### 4. 阈值与容差

- 阈值语义（过阈值**样本/区间** ≠ 事件数）；
- 容差是否预注册（M9 前不得事后移动阈值）；
- 边界值（恰在阈值上）的行为是否被测试。

### 5. 数值健康

- NaN / Inf / 空列 / 损坏时间轴；
- 精度损失（大数减小数、wrap 边界差分）；
- 四舍五入是否影响结论（残差 vs 容差）。

### 6. 收敛与敏感性

- 关键事件结论是否随时间步（0.1/0.05/0.025 ps）稳定；
- 分类是否随步长翻转（翻转 → INCONCLUSIVE 而非 PASS）；
- solver 配置、初始条件敏感性是否声明。

### 7. 复现性（配合 josim-experiment）

- run ID / manifest / 输入闭包 / 版本是否记录；
- 随机性、环境、缓存、工作目录依赖；
- 同一命令是否可重复产生相同结果。

## 输出

- 每条检查给出 PASS/FAIL/UNKNOWN + 证据；
- CRITICAL 任务必须至少一个独立数值 cross-check（从 raw 重算关键数字，不依赖 executor 文本）；
- 发现即写入 REVIEW.md；不修改实现/证据。
