---
title: 三方协作讨论总结 — 现有流程 + Copilot/Claude/Codex 三方建议
document_type: review_summary
status: FOR_USER_REVIEW
date: 2026-08-11
sources:
  - research/WORKFLOW.md
  - research/WORKFLOW-copilot-review-proposal.md（Copilot 提案）
  - research/mailbox/from-claude/claude-20260811-142632.md（Claude 审阅意见）
  - research/mailbox/from-codex/codex-20260811-142613.md（Codex 协议建议）
  - research/mailbox/from-claude/*、from-codex/*（M4 执行记录）
  - research/tasks/JH-20260811-M4-003/audits/C01/verdict.yaml（M4 审计结论）
---

# 三方协作讨论总结：现有流程与三方建议

> 本文档供**用户审查**使用。汇总当前协议（`josim-handoff/v1`）、M4 执行实录，以及 Copilot、Claude、Codex 三方对「Copilot 介入复核」这一改动的各自建议；并列出需要用户拍板的决策点。本文档不修改任何协议条款。

## 一、现有流程（as-is，`research/WORKFLOW.md`）

### 1.1 一句话模型

```text
用户给出研究方向和最终授权
   → Codex 把下一项工作冻结成带 SHA-256 哈希的任务合同
   → Claude 先 ACK，再在限定路径内实现/运行并交付 receipt
   → Codex 独立审计（审合同、diff、原始数据）
   → 用户对路线改变、指标冻结和论文主张作最终裁决
```

### 1.2 核心不变量（本讨论中三方都未质疑的部分）

- **四维结果分离**：`execution_status`（执行是否完成）/ `artifact_status`（产物是否有效）/ `physical_verdict`（物理 PASS/FAIL/INCONCLUSIVE）/ `audit_disposition`（是否接受）。
- **哈希密封**：request 签发后字节级不可变，`request.sha256` 绑定；attempt/receipt/audit 全部 append-only。
- **`claim_ceiling`**：合同声明本次允许的最强主张，防止实现任务越界宣判物理 Gate。
- **读写边界**：Claude 只写 `scope.write_paths`；禁止 `git add -A` / `reset --hard` / `clean` / 覆盖原始产物。
- **停止条件**：预检不符、范围冲突、连续两次同根因失败 → `BLOCKED`/`DEVIATED`，不得自行扩大范围。

### 1.3 标准流程状态机

```text
DRAFT → ISSUED → ACKED → RUNNING → DELIVERED → AUDITED → CLOSED
                                        ├─ REWORK（新 attempt）
                                        └─ REJECTED / BLOCKED / DEVIATED
```

### 1.4 M4 执行实录（验证流程实际怎么走的）

| 合同 | 结果 | 说明 |
|---|---|---|
| `M4-001`（08-09） | REJECTED | 因 stand-in 记录问题被 Codex 抓回重签 |
| `M4-002`（08-11） | A01 BLOCKED | worktree HEAD=7913a96 与 baseline= d4e91d3 不符；Claude 按停止条件正确停止；Codex 承认是**自己签发时遗漏更新基线** |
| `M4-003`（08-11） | **C01 ACCEPTED** | 基线匹配后重新签发；Claude A01 完成：15/15 测试通过、CLI 冒烟断言通过、verify-task VERIFIED；Codex 独立审计 C01 接受，范围严格限于计量实现基础 |

**todo 现状**：M4 已 🟢（2026-08-11）；M5、M6、M7…M12 未开始；`METRIC_SPEC_V2` 未冻结。

## 二、Copilot 的提案（`WORKFLOW-copilot-review-proposal.md`）

### 2.1 核心主张

把审计动作拆给第三人，形成三方制衡：**Codex 规划 + 最终采纳；Claude 执行；Copilot 独立复核**。

```text
Codex 签发 → Claude ACK+执行+receipt → Copilot 复核(review.yaml) → Codex 轻量采纳审阅 → verdict
打回时：Copilot 给具体清单 → Claude 新 attempt 修复 → Copilot 再复核
```

### 2.2 复核清单

1. 机械层：schema、哈希链、scope 合规、产物 SHA-256；
2. 独立重算：从原始 CSV 重算关键数字（$\Delta\phi/(2\pi)$ 圈数、电压面积交叉校验）；
3. 证据层：artifact 有效性、activity vs event、local vs downstream、claim-ceiling 检查；
4. 输出：简短 review 记录，`PASS` 或具体可执行打回清单。

### 2.3 信任边界（已与用户确认）

- 复核证明「产物自洽、可复现、证据支持结论，到 claim ceiling 为止」；
- 不证明「Claude 确实执行了某命令」（共享文件系统的固有限制）；
- Codex 保留最终采纳权。

### 2.4 简化项

- Codex 深度独立复核 → 轻量采纳审阅；
- 模型路由表移出协议正文（降级为注释/环境配置）；
- 不新增快速通道（按用户意见）。

### 2.5 已知需要修正的过时事实（Claude 指出，属实）

- 提案称「M4-003 仍 DRAFT」→ **已过时**：M4-003 已 ACCEPTED，M4 完成；
- 提案把 M4 三次重签当「流程摩擦证据」→ **叙事需修正**（见下节 Claude 意见）；
- 因此「用 M4 当试点」的建议**自动失效**。

## 三、Claude 的审阅意见（claude-20260811-142632）

### 3.1 事实修正

1. M4-003 已于 14:06 经 C01 ACCEPTED，M4 完成并归档；提案第 9 节试点建议需另选对象。
2. **M4 三次重签应解读为协议的正面样本，不是缺陷**：
   `REJECTED`（抓 stand-in 重签）→ `BLOCKED`（抓基线不符）→ 干净合同通过，恰好证明协议在起作用。

### 3.2 动机修正

「Codex 独立审计独立性打折」的论证**不成立**——独立性 = 不参与执行 + 从原始证据复核（C01 已记录 `INDEPENDENT / codex_modified_execution_artifacts: false`）。
真实动机应定位为：**Codex 带宽释放 + 第二双眼睛（peer review）**。

### 3.3 风险

1. **结构性矛盾**：提案第 7 节「不新增流程环节」 vs 第 8 节新增 `review.yaml`——新文件类型必然要 schema/机械校验/绑定链，且与 `verdict.yaml` 的 checks/evidence 结构重叠。**建议不发明新类型**：Copilot 复核直接产出 `audits/Cxx/` 预审记录或复用 verdict 结构。
2. **Codex 轻量采纳的深度下限未定义**：物理任务（相位/SFQ/JTL/结论）Codex 必须亲自深度复核；「轻量采纳」仅限纯实现任务。并入前必须写死。
3. **身份边界**：Copilot 与 Claude 同为桌面 AI 助手，定位应为 **peer review 而非「独立审计」**，避免稀释协议中「独立」的语义。

### 3.4 建议路径（渐进式）

- 第一步：Copilot 以**只读机械预审员**身份试点下一个实现任务（跑 verify-task + 哈希重算 + 打回清单，不落协议文件）；
- 2–3 个任务验证价值后，再由 Codex 决定是否正式并入 WORKFLOW.md（并定义物理深度下限）；
- 模型路由移出协议正文——**支持**。

## 四、Codex 的协议建议（codex-20260811-142613）

方向可取（Claude receipt 后 Copilot 做只读、独立证据复核，Codex 保留最终采纳），但**不建议按草案直接落地**：

1. **试点对象**：M4 已 ACCEPTED 不能再当 DRAFT 试点；优先考虑 **M12 或 M5 的纯计量实现部分**。
2. **review 文件形式**：新增 review.yaml 就必须有 schema 与机械校验；建议单设 **evidence-review 记录**（如 R01），而非复用最终 audit verdict。
3. **review 必须绑定**：request/ACK/receipt 的 SHA-256、审查 Git HEAD、范围、命令/退出码/日志哈希、逐条验收证据、未知项、claim-ceiling 检查。
4. **结果维度分开**：review 的 PASS/REWORK 与物理 PASS/FAIL/INCONCLUSIVE 必须分开；**INCONCLUSIVE 可以是有效研究结果**。
5. **Codex 深度下限写死**：路线、物理 Gate、指标冻结、论文主张、证据冲突、单位/窗口/收敛争议，Codex 仍须从 raw 亲自复核，不能只读 review 摘要。
6. **「独立」定义**：未参与实现、只读、固定快照复核；共享文件系统不提供身份或命令历史证明。
7. **顺带修复 verify-task 历史语义**：审计后正常更新 HANDOVER/todo 会使 live frozen-file 比较**误报旧任务失效**——应区分「执行时快照验证」与「当前漂移检查」。

### Codex 建议的流程

```text
Claude receipt → Copilot R01 evidence review → Codex C01 audit verdict（绑定 R01 hash）→ 上推状态
```

（该消息仅供讨论，不构成任务授权或协议修订。）

## 五、三方共识与分歧

### 5.1 共识（三方一致）

- ✅ 三方分离方向正确：Codex 规划+最终采纳，Claude 执行，Copilot 做 receipt 后的只读复核。
- ✅ 复核证明的是「证据层可信到 claim ceiling」，不提供身份/命令历史证明。
- ✅ Codex 保留最终采纳权与论文级主张决定权。
- ✅ 物理 Gate/路线/指标冻结等，Codex 必须亲自复核（深度下限需写死）。
- ✅ 模型路由应从协议正文移除（Claude 明确支持；Copilot 提案一致）。

### 5.2 分歧 / 待定

| 议题 | Copilot 提案 | Claude 意见 | Codex 建议 |
|---|---|---|---|
| 角色定位措辞 | 「独立复核」 | **peer review**，避免稀释「独立」语义 | 「独立」= 未参与实现+只读+固定快照 |
| review 记录形式 | 新增 `review.yaml` | 不发明新类型，复用 `audits/Cxx/` 预审或 verdict 结构 | 单设 evidence-review 记录（R01），需 schema+机械校验 |
| Codex 采纳深度 | 轻量采纳审阅 | 物理任务必须深度复核，轻量仅限纯实现 | 同左，写死 |
| 试点对象 | M4（已失效） | 另选 | M12 或 M5 纯计量部分 |
| 额外项 | — | — | 顺带修复 verify-task 的 live 误报语义 |
| 落地方式 | 直接并入 | 渐进：先只读预审试点 2–3 个任务 | 渐进，先试点再并入 |

## 六、需要用户拍板的决策点

1. **角色定位措辞**：对外称「peer review（同行复核）」还是「独立复核」？（Claude/Codex 倾向前者或严格定义「独立」）
2. **review 记录形式**：新增独立 `review.yaml`（需配套 schema + 机械校验）还是复用 `audits/Cxx/` 预审记录？或采用 Codex 的 R01 evidence-review 命名？
3. **Codex 深度下限**：确认「物理任务 Codex 必须亲自从 raw 复核；轻量采纳仅限纯实现任务」并写入协议。
4. **试点对象**：选 M12（`josim-plot2.py -j` 布局修复，独立于计量接口，可并行）还是 M5（事件窗口/零输入控制，紧贴计量语义）的纯实现部分？
5. **渐进式路径**：是否接受「Copilot 先以只读机械预审员身份试点 2–3 个任务（不落协议文件），验证价值后再正式并入 WORKFLOW.md」？
6. **verify-task 修复**：是否把「区分执行时快照验证与当前漂移检查」纳入本次修订范围？
7. **提案文档处置**：`WORKFLOW-copilot-review-proposal.md` 的过时事实（M4 状态、试点建议、摩擦叙事）是否需要先修订，还是以本文档取代之？

## 七、下一步（建议顺序）

1. 用户对上述决策点作出选择；
2. 按选择修订/合并提案文档（Copilot 可协助起草 diff，正式并入由 Codex 负责）；
3. 选定试点任务并签发；
4. 试点完成后，再评估是否正式并入 `WORKFLOW.md`。
