# REVIEW M7-LITE-001 / A01

Review disposition: **PASS**
Recommended risk: CRITICAL
Recommended evidence mode: LITE
Evidence confidence: HIGH
Residual risk: LOW

Reviewed delivery snapshot: `936df75`（evidence commit `936df75`，metadata commit `2f63907`；实现/测试/raw/manifest 均已纳入快照）

## Scope
PASS

Evidence:
- worktree `/home/howard/JoSIM-m7-lite`，branch `claude/M7-LITE-001`，HEAD `2f63907`；执行前 `git status` clean；
- 变更仅限 allowed paths：`test/metrics/test_sfq_metrics_v2_m7.py`（新增）、`test/metrics/m7_canonical_jtl.cir`（新增）、`attempts/**`（scope-diff.log 证实，无越界路径）；
- `scripts/sfq_metrics_v2.py` 未修改（冻结哈希 `6be62ed0…` 一致）；
- 本次审查仅新增本 REVIEW.md。

## Acceptance criteria
- [x] AC1 保留 —— 独立复跑 M4 15 / M5 29 / M6 21 / M7 18 = **83/83 PASS**，未改动任何既有测试
- [x] AC2 M7A 合成 ground truth —— oracle 为字面常量/初等算术（`_trapezoid`/`_half_open_indices`/`_nearest_index` 独立实现，未调用生产 helper）；覆盖 rad→turns 含符号、非均匀梯形积分、方向符号、控制相减、半开端点、严格阈值、聚类分离、畸形输入
- [x] AC3 M7B canonical JTL —— 网表 diff 仅 .print 块（直接同 JJ `V(B1|B2|XDUT)`+`P(B1|B2|XDUT)`）；唯一 run 溯源完整；独立重算与生产输出在浮点精度内一致；raw signed residual 仅报告不判定
- [x] AC4 M7C 历史回归 —— DCSFQ 与 bq_v4 常量独立重算精确复现（见 Independent checks）；bq_v4 明确声明为周期历史相位平台回归常量、非事件计数、非接口 Gate
- [x] AC5 证据闭包 —— RESULT 含不可变 Preflight、三状态字段、AC 映射、命令/退出码/哈希、scope diff、manifest；failed attempts 无（A01 一次成功）

## Independent checks
- 独立复跑：M7 18 + M4 15 + M5 29 + M6 21 = **83/83 OK**（与 RESULT 一致）
- **M7C-1 DCSFQ 独立重算**（raw CSV 第一性原理）：B1/B2/B3 turns = 0.9999999829418391 / 1.0000000625193106 / 1.0000000147728276，与 TASK AC4 常数一致；pre/activity/post = 30/409/900
- **M7C-2 bq_v4 独立重算**（实际时间最近行）：6 个常量 1.0133756508381797 / 2.0133738512446557 / 3.013374598130222 / 4.0133737534663565 / 5.013374500351922 / 6.013373655688058 **全部精确复现（err=0.00）**；参考行 5.0 ps 精确、各目标行时间精确（偏移在行号不在时间值，nearest-time 方法正确）
- **M7B 独立重算**（run CSV，[6e-12,50e-12) 实际时间轴）：B1 residual=−1.412755e-04、B2=+1.412931e-03 turns，与 RESULT/测试输出一致
- 冻结哈希 14/14 独立核验匹配（含 `sfq_metrics_v2.py` 未改动、历史 CSV/网表/模型未变）
- M7B run：exit 0、无 solver 警告、4 个直接同 JJ V/P 列齐备、窗口 439 样本

## Hidden-error probes
- "测试 oracle 复用生产逻辑？" → 探针：读测试源码——oracle 全部为字面常量与独立初等算术；生产函数仅在 M7B 一致性比较处调用 → 排除 ✅
- "rad/turn 混淆？" → 探针：M7A 符号测试（+2π→1、−2π→−1、−π→−0.5）+ 独立重算 → 排除 ✅
- "只测合成的 M7A？" → 探针：M7B 真实 JTL transient run + M7C 冻结历史 CSV 均存在并独立验证 → 排除 ✅
- "M7B 非直接 JJ V 映射/方向/端点错误？" → 探针：网表 diff 仅 .print；manifest orientation=1；独立重算同 JJ 同窗口端点匹配 → 排除 ✅
- "固定 dt 假设？" → 探针：M7A 非均匀梯形测试 + M7B/bq_v4 均用实际 CSV 时间轴/最近行 → 排除 ✅
- "周期回归误称单输入物理事件？" → 探针：RESULT 显式声明"周期历史相位平台回归常量，非事件计数、非接口 Gate"；无事件术语（grep=0）→ 排除 ✅
- "stale 历史文件？" → 探针：14 冻结哈希全部匹配 → 排除 ✅
- "超出 CALIBRATION 的主张？" → 探针：RESULT Claim 与 Limitations 显式边界 → 排除 ✅

## Claim ceiling
PASS — RESULT claim 严格限于 M7A/B/C 校准实现与确定性回归；无物理事件/路线/容差/Gate/论文主张；LITE 不追溯 FROZEN。

## Findings

### Critical
- None.

### Major
- None.

### Minor
- 无实质项。备注：bq_v4 时间网格"偏移"实际在行号索引（行号 ≠ 时间×10），时间值本身精确（独立重算确认各目标行时间为精确 ps 整数）；nearest-time 方法与测试 0.11 ps 断言均为稳健做法，建议在 M7C 文档中保留该表述以防未来误解。

## Residual uncertainty
- M7B 残差（~1e-4/1e-3 turns）为管线原始值，接受/拒绝判定归 M9（容差冻结），本任务不判定——符合 TASK。
- 未运行 M8 收敛（属后续任务）。

## Codex focus
1. 结论：M7-LITE-001 A01 证据层 **PASS / AUDIT_READY**——83 测试独立复跑全绿、M7C 两个组件与 M7B 残差均独立重算精确匹配、冻结哈希 14/14、scope/claim ceiling 合规。
2. 建议 Codex 按 TASK Required review 独立复核 M7B/M7C 关键 raw 数值（我复现的结果可对照）。
3. M7B 残差不判定、bq_v4 为周期回归常量，均不应被后续任务升级为事件或 Gate 语义。
