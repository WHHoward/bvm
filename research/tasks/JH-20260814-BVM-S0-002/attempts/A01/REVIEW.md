# REVIEW JH-20260814-BVM-S0-002 / A01

Review disposition: **REWORK**
Recommended risk: CRITICAL
Recommended evidence mode: LITE
Evidence confidence: HIGH（封存本身）
Residual risk: MEDIUM

Reviewed delivery: `research/tasks/JH-20260814-BVM-S0-002/attempts/A01/`（源仓库，master HEAD `727eac4`；无独立 worktree）

## Scope
PASS

Evidence:
- 任务在源仓库执行；本次审查 read-only，仅新增本 REVIEW.md；
- 变更路径（git status）：全部为 S0-001/S0-002 任务包与 `test/final/bvm/runs/bvm-s0-canonical-20260814-01/**` 的**未跟踪新产物**，未触碰任何已提交/冻结文件；
- request `write_paths` = attempts/** + mailbox；源包在 `frozen_paths`；`run_josim=false`、`commit=false`、`delete_or_overwrite=false`——与执行一致。

## Acceptance criteria
- [x] AC1 封存清单精确 —— 独立核验 59 项（12 CSV + 12 stdout + 12 stderr + 14 inputs + 4 root + 5 predecessor），每项含 SHA-256；封存源目录遍历 **0 未覆盖**、0 缺失
- [x] AC2 seal_check 独立可复现 —— 独立运行 `seal_check.py` → **PASS（exit 0）**；代码核验非恒真（独立推导 case×step 集/计数/路径集/逐项哈希）
- [x] AC3 RESEALED_ONLY —— evidence-seal `conclusion: RESEALED_ONLY`；receipt interpretations 明确"科学内容未评估"；`proposed_physical_verdict: NOT_APPLICABLE`；无数值/物理/S0 判定
- [x] AC4 chronology —— predecessor created_at(20:05) vs mtime(19:54:03) 偏差已记录为 **source UNKNOWN**，未改元数据；host `date -Iseconds` 已记录
- [ ] AC5 机械闭环证据 —— **FAIL（见 Major）**：交付的 verify-task 日志与 receipt 声明矛盾

## Independent checks
- 59/59 项 SHA-256 独立重算 = 封存记录（0 mismatch）
- 封存源目录文件全覆盖（0 uncovered / 0 missing）
- 独立运行 `seal_check.py` → PASS exit 0
- **独立重跑 `handoff.py verify-task research/tasks/JH-20260814-BVM-S0-002` → VERIFIED exit 0**（当前状态真实通过）
- request/deliverable/acceptance 逐条比对通过（除 AC5 证据问题）

## Hidden-error probes
- "封存清单是否缺/增？" → 独立遍历源目录 + 计数比对 → 无缺/增 ✅
- "哈希是否对得上磁盘？" → 59/59 独立重算一致 ✅
- "是否真的没改源 evidence？" → 源包为未跟踪新产物且全部被 seal 覆盖；本任务 write_paths 不含源包；request frozen ✅
- "是否藏了科学结论？" → evidence-seal/receipt 全文无 PASS/FAIL/SFQ/读态等结论，均 RESEALED_ONLY ✅
- "verify-task 是否真的 VERIFIED？" → **当前状态独立重跑确实 VERIFIED exit 0**；但交付日志矛盾（见 Major）
- "seal_check 是否恒真？" → 源码核验：独立推导标识集/计数/路径集/哈希，缺项与篡改会 exit 1 ✅

## Claim ceiling
PASS — 无数值/物理/S0 结论；RESEALED_ONLY 成立。

## Findings

### Critical
- None.

### Major
- **verify-task 证据闭环内部矛盾（AC5/AC2 的"PASS log 已保留/最终 verify 成功"证据不成立）。**
  - 观察 A：交付的 `logs/verify-task.log`（mtime 20:33）内容为 **ERROR**：
    `task verification failed: ... receipt.yaml: acceptance_results[2] evidence is not a hashed artifact: receipt.yaml`（AC3 与 AC5 的 evidence 曾指向 receipt 自身）。
  - 观察 B：`receipt.yaml` 的 commands 将 verify-task 记录为 `exit_code: 0, log_path: logs/seal-check.log, log_sha256: 14b4ee9e…`，但 seal-check.log 内容**只有** seal_check 的 PASS 一行，**不含任何 verify-task 输出**——日志归属错误（verify-task 与 seal_check 被错误地指向同一文件）。
  - 观察 C：当前状态独立重跑 verify-task **确实 VERIFIED（exit 0）**——说明该 ERROR 是早期 receipt 版本（AC3/AC5 evidence 含自引用）的**过期失败日志**，成功运行的输出未被单独保留。
  - 为何重要：本任务唯一目的是**机械证据闭环**（AC2 要求 "PASS log is retained"、AC3 要求 "final verify-task succeeds"）。交付物中保留了一个显示 FAILURE 的 verify-task 日志 + 一个指向错误日志的 receipt，自相矛盾——审计者无法从保留证据重建"最终 verify 成功"。底层封存本身（59 哈希）完全正确，问题在闭环证据的保留与归属。
  - 最小修正（新 attempt 或 correction note）：
    1. 重新运行 verify-task 并把**成功输出**保存为独立日志（含时间戳）；
    2. 修正 receipt 的 commands 日志映射（verify-task → 其自身日志，seal_check → seal-check.log）；
    3. 对过期失败的 verify-task.log 显式标记 superseded（或记录其失败原因=早期 receipt 自引用证据，已被修正）。

### Minor
- `seal_check.py` 头部 docstring 写 "Pure stdlib" 但顶部 `import yaml`（非 stdlib）——文档小误差，非材料。
- 无其他。

## Residual uncertainty
- 未验证 seal_check.py 的"负向毒化"声明（删项/篡改被拒）——我未改动任何文件去复测（保持只读）；但代码逻辑核验支持该行为，且 seal 与磁盘一致。
- verify-task 当前状态通过已独立确认；Major 是证据保留/归属问题，非当前状态失败。

## Codex focus
1. **裁决 Major**：S0-002 A01 的 verify-task 证据闭环矛盾（保留失败日志 + receipt 日志归属错误），建议要求 A02（或 correction note）重跑 verify-task 并正确保留/归属成功日志。
2. 封存本体（59 项 SHA-256、覆盖率、RESEALED_ONLY、chronology）已独立验证通过，不受该 Major 影响。
3. 可顺手修正 seal_check.py 的 "Pure stdlib" 表述（Minor）。
