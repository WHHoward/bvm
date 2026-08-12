# Copilot 对《JoSIM × BVM 研究流程与 Batch 协作整合修改提案》的审阅意见

> 审阅人：Copilot（Reviewer 角色）
> 审阅对象：`workflowdiscuss/archive/proposals/JOSIM_BVM_研究流程与Batch协作整合修改提案.md`
> 日期：2026-08-12
> 状态：三方审阅意见之一；不修改协议、不授权任务

---

## 1. 总体判断

这是目前质量最高的一份提案：真正触及科研方法论，而不只是协作成本。**核心价值是引入 Study Phase 轴（EXPLORATORY / CALIBRATION / CONFIRMATORY）**——补上了当前协议的根本盲区：NORMAL/CRITICAL 只区分"审多深"，但**没有区分一次运行的认识论地位**（探索/校准/确证）。

建议：**科研方法轴（Decision 1）与协作最小扩展（Decision 2）分开推进**，科研计划不转化为更多协作流程。

---

## 2. 最高度认可的部分

| 提案内容 | 为什么对 |
|---|---|
| M9 拆分（METRIC_SPEC vs INTERFACE_GATE） | "测量尺"与"产品验收标准"分离，治本 |
| Reference Reconstruction R0–R3 + 参数 provenance 标签 | 直指项目下一阶段最大风险（优化了错误的参考对象） |
| Source/Receiver 表征先于调参 | 避免"精确优化错误参考系" |
| Operating region 而非 success point + held-out validation | 科研正确性，防偶然成功点 |
| §33 AI 物理主张纪律（MODEL/FORMULA/UNITS/FALSIFICATION TEST） | 防无依据断言 |
| §21 FROZEN input/mutable/output 三段式 | 直接修复 M6-001 暴露的合同缺陷 |
| §37 十条不可妥协原则 | 全部成立 |

---

## 3. 需要警惕/修正的点（按重要性）

### ⚠️ 1. 提案自身存在"过程膨胀"风险——严格按 §41 决策顺序走
43 节、37+ 机制、十几个新文件，全部一次推进会重蹈"复杂化"覆辙。**第一优先级只做两件最便宜最高价值的事：W5B（REFERENCE_PROVENANCE）+ Study Phase 标签。**

### ⚠️ 2. M8 的"继续细化直到稳定"是无界判据
"若 0.025 ps 未稳定则继续"可无限循环。建议预注册停止规则：*最大细化深度 + 定量稳定判据（相邻步关键量变化 < 预注册容差）；达到最大深度仍未稳定 → 声明 INCONCLUSIVE。*

### ⚠️ 3. M7C 防循环显式化
M7C 期望值必须来自**独立人工重算冻结值**（HANDOVER：JM1 −0.9406、BJs +0.9983、DCSFQ 300µA B1/B2/B3 ±1 圈、BQ v4 110–150µA 六圈），测试**不得 import 生产 `analyze` 函数取期望**（M5 oracle 独立性同一条纪律）。

### ⚠️ 4. Held-out 集合必须先于校准冻结
在校准后划 held-out 会退化为事后挑选。建议：*Stage E 开始时即冻结 validation set 定义（load/waveform/bias/state 清单），之后调参不得触碰。*

### ⚠️ 5. 新增产物的任务归属要明确
`BVM_SOURCE_SPEC_V1`、`INTERFACE_GATE_V1`、`REFERENCE_PROVENANCE.md` 归谁建、完成标准是什么？不绑定 M-tasks 或明确 ownership 会成为无主 scope 蔓延。建议每个新 artifact 挂到具体 todo item + 完成标准。

### ⚠️ 6. §36 边界同意，但要防"Phase −1 变长期阻塞"
M11 前允许 characterization、不允许 route verdict——同意。建议给 characterization 加**有界预算**（预注册参数域 + 最大 run 数），确保是有限步骤而非开放探索。

---

## 4. 回答 §40 给 Copilot 的六个问题

### Q1. Blind formal review 的最小 evidence set
- Batch Contract（scope/claim ceiling/escalation）
- SEMANTIC-LOCK.yaml（单一来源）
- Delivery snapshot commit + git diff metadata
- 机器生成 AUDIT-PACKET（文件清单、哈希、退出码、AC 映射）
- 关键 raw evidence 路径 + 哈希
- RESULT 四维字段头

先凭这些构造证伪假设，**之后**才读 LEDGER/预审记录。

### Q2. 防 M7C 循环验证
期望值来自独立人工重算冻结值（HANDOVER 已记录）；测试 oracle 不得调用生产函数（M5 纪律）；对比目标用"人工值 vs 新 pipeline 输出"双端独立。

### Q3. SEMANTIC-LOCK 还缺什么
- 符号约定（direction/sign）显式条目；
- CSV 列头契约与 phase wrap/unwrap 策略（raw rad，不 unwrap，显式声明）；
- 生成 raw 时的 timestep/solver 配置；
- P/V 交叉校验的同一 JJ 端点定义；
- 电压面积积分公式（实际 time 列梯形积分）；
- run-ID 方案；
- "本次 run 冻结项 vs batch 内可变项"的区分——锁不能把所有东西焊死。

### Q4. 审计 parameter provenance
每个运行参数要求可追溯到标签 [PUBLISHED]/[AUTHOR_PROVIDED]/[DERIVED]/[INFERRED]/[DESIGNED]/[TUNED]/[UNKNOWN]；CONFIRMATORY 运行出现 UNKNOWN → BLOCK/INVALID；[TUNED] 参数附调参历史（扫了什么、固定了什么、calibration/validation 划分）；可机械检查：netlist 参数 → provenance 表 → 标签，缺失即标记。

### Q5. 审查 bounded negative vs universal impossibility
检查声明是否含模型/源包络/负载/参数域/指标/收敛/停止判据/已测空间（§15 清单）；红旗词："never"/"不可能"/"can't work"且无域限定；**元变换探针：改变一个"保持固定"的参数（如 bias）是否翻转结论**——若只测过单一 bias，至多有界负结果 → 一般性声明标 INCONCLUSIVE；负结果必须预注册"什么证据会改变结论"，否则不可证伪。

### Q6. Batch 内最可能污染下游但最易被 PRE-REVIEW 漏掉的错误
1. **Semantic Lock 静默漂移**（阈值 0.3→0.31 在"整理"中变化，批内自洽但违反合同）；
2. **方向/符号反转但批内自洽**（绝对值掩盖符号错误）；
3. **共享 helper 的 oracle 同错**（测试与实现共用同一有 bug 函数，M5 教训批内版）；
4. **"足够接近"的控制对齐**（近似时间数组通过精确相等校验但浮点格式微偏）；
5. **旧产物复用**（"看起来差不多"的旧 CSV）；
6. **窗口边界 off-by-one 只在边界样本非平坦时暴露**；
7. **术语漂移**（下游聚合层把 activity_clusters 重标成 events）。

其中 **Semantic Lock 漂移**与**共享 helper 同错**是批内最危险的两种——恰好由本提案的 Semantic Lock + 独立 oracle 纪律覆盖。

---

## 5. 推荐下一步（按 §41 决策顺序，第一优先只拍三个决策）

1. **研究法**：Study Phase 标签 + M7 拆分 + M9 拆分 + W5B provenance（先启动，最便宜最高价值）；
2. **协作最小扩展**：Batch fact layer + Semantic Lock + blind Formal Review + Audit Packet 原型（P0 四项，已有共识）；
3. **FROZEN 修复**：input/mutable/output 三段式。

其余（source spec、receiver map、interface benchmark、verify-batch、Decision Cache）全部排到 M7A/B/C 真实 Pilot 之后。
