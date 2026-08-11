# REVIEW M5-LITE-PILOT-001 / A02

Review disposition: **PASS**
Recommended risk: CRITICAL
Recommended evidence mode: LITE
Evidence confidence: HIGH
Residual risk: LOW

Reviewed delivery snapshot: `9ba6d40`（代码/RESULT `70938b3`，证据 `4c4975a`，snapshot metadata `9ba6d40`；不可变链完整）

## Scope
PASS

Evidence:
- worktree `/home/howard/JoSIM-m5-lite`，branch `claude/M5-LITE-PILOT-001`，HEAD `9ba6d40`；执行前 `git status` clean；
- A01 及其 REVIEW/CODEX-AUDIT 未修改（历史记录保留）；
- 变更仅限 allowed paths：`scripts/sfq_metrics_v2.py`（A02 增量 +35/−21）、`test/metrics/test_sfq_metrics_v2_m5.py`（25→29）、`attempts/A02/**`；
- 本次审查仅新增本 REVIEW.md。

## A01 Major 闭环（Codex 指定的核心核验）

- [x] **activity 完整未舍入统计且与聚类结构分离**：`namespace()` 现对 pre/activity/post 三窗均调用 `_window_stats`；activity 输出含 9 字段统计块（requested bounds、selected first/last time、sample_count、mean_rad、min/max/p2p_rad）；聚类独立为 `activity_clusters` 列表 + `over_threshold_sample_count`，与统计分离、无事件语义
- [x] **activity 0 和 1 样本可靠拒绝、CLI 非零**：独立实测——零宽窗口 `[8.5,8.5)` 与单样本窗口 `[8.5,8.6)` 均触发 `ValueError: fewer than two finite samples`（与 pre/post 一致）；CLI 路径返回码 2
- [x] **signal/control 两个命名空间均覆盖**：`output.json` 中 `signal` 与 `zero_input_control` 的 activity `sample_count` 均为 409，统计字段齐备
- [x] **AC6 activity=409 已断言**：测试断言 signal（L521）与 control（L549）的 activity sample_count==409；新增 `test_activity_window_stats_complete`（首性原理均值 272.5/60）与 `test_activity_stats_separate_from_clustering`
- [x] **29 M5 + 15 M4 测试独立通过**：独立复跑 29/29 OK、15/15 OK
- [x] **方向 / delta-of-deltas / 严格阈值 / 无事件语义 / raw 重算 / claim ceiling 无回归**（见下）

## Independent checks
- 独立复跑 M5 29/29、M4 15/15 ✅
- AC6 独立重算（raw CSV 第一性原理，plan 与 A01 逐字节一致 87eb68d1）：B1/B2/B3 turns = 0.9999999829418391 / 1.0000000625193106 / 1.0000000147728276，与 TASK 冻结常数及 output.json 逐项一致 ✅
- 样本数 pre/activity/post = 30/409/900（signal 与 control）✅
- activity 0/1 样本拒绝独立实测（见上）✅
- output.json 无禁止字段：event_count / fast_events / pulse_count / sfq_count 均 absent；"fluxoid" 仅出现在 disclaimer 文本（"never ... fluxoids"，即声明无 fluxoid 语义），不在任何输出键中 → 无 AC4 违规 ✅
- 冻结哈希：7 个未修改冻结输入全部匹配（hashes.log 复验 + 本次独立核验）✅
- A01 非材料更正：`.param IIN` 第 6 行（独立 grep 确认）、CSV 1999 数据行 + 1 表头（独立解析确认）✅
- 只读边界：审查前 clean，审查后仅新增 `attempts/A02/REVIEW.md` ✅

## Hidden-error probes
- "activity 统计是否只是表面字段、实为复制 pre/post？" → 独立读 output.json：activity mean_rad=-1.496…（与 pre/post 不同）、sample_count=409 → 独立计算 ✅
- "activity 0/1 样本是否真的拒绝？" → 零宽 + 单样本窗口独立实测均 ValueError ✅
- "A02 是否回归 A01 正确行为？" → AC6 重算、聚类 1/0/1 vs 0/0/0、方向、delta-of-deltas、严格阈值、无事件术语全部保持 ✅
- "oracle 是否新引入同错？" → 新测试期望为首性原理常数（60 样本均值 272.5/60、精确二进制窗口界 2.0625），不调用生产 helper ✅

## Claim ceiling
PASS — A02 RESULT claim 严格限于实现与确定性回归；无物理结论；LITE 不追溯 FROZEN 声明正确。

## Findings

### Critical
- None.

### Major
- None（A01 Major 已闭环）。

### Minor
- None 实质项。备注：output.json 的 disclaimer 文本含 "fluxoids" 一词，属"never events/pulses/SFQs/fluxoids"的否定声明，非语义违规；如需极致规避可改为"fluxoid counting"，非阻塞。

## Residual uncertainty
- 未在旧版依赖环境验证（不涉本任务数值）。
- activity 统计块的"未舍入"在 JSON 序列化中保留浮点原值；数值精度已验证（AC6 ≤1.6e-14 rad）。

## Codex focus
1. A02 已闭环 A01 Major：activity 统计/校验/分离/409 断言全部独立验证通过，无回归。
2. 建议按序推进后续 Pilot 步骤；M5 物理解释 / M6 应转 CRITICAL+FROZEN（如 TASK Explicit remainder 规划）。
3. 可选：disclaimer 措辞（"fluxoid counting"）非阻塞优化。
