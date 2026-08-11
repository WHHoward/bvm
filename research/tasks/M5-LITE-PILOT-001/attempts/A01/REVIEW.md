# REVIEW M5-LITE-PILOT-001 / A01

Review disposition: **REWORK**
Recommended risk: CRITICAL
Recommended evidence mode: LITE
Evidence confidence: HIGH
Residual risk: MEDIUM

Reviewed delivery snapshot: `5489338`（delivery evidence `abcc917`，code snapshot `75a6bbc`；三者构成不可变链）

## Scope
PASS

Evidence:
- worktree `/home/howard/JoSIM-m5-lite`，branch `claude/M5-LITE-PILOT-001`，HEAD `5489338`；执行前 `git status` clean；
- 变更仅限 allowed paths：`scripts/sfq_metrics_v2.py`（+322/−2）、新增 `test/metrics/test_sfq_metrics_v2_m5.py`、`attempts/A01/**`（scope-diff.log 证实，无越界路径）；
- 未修改 TASK/RESULT/实现/raw/plan/output/log（本次审查仅新增本 REVIEW.md）。

## Acceptance criteria
- [x] AC1 M4 保留 —— 独立复跑 M4 回归 **15/15 PASS**；raw rad 保留、显式 /(2π)、activity 术语、M4 limitations 均在
- [x] AC2 校验 —— 大部分 PASS（plan/非单调时间/非有限值/缺列/控制不对齐均拒绝），**但 activity 窗口 <2 样本未被拒绝（见 Findings Major）**
- [x] AC3 算术与溯源 —— PASS（pre/post 窗口统计、raw signal/control delta、directed corrected delta、相减后 turns、路径+SHA-256、control_applied、CSV 对齐无法证明网表控制关系的声明均有）
- [x] AC4 聚类 —— PASS（严格阈值、窗内增量、activity_clusters + over_threshold_sample_count；output.json 与 TerminologyTests 均无 event/pulse/sfq/fluxoid 语义）
- [x] AC5 合成测试 —— PASS（25 测试独立 oracle；AC5 要求的 10 类场景全覆盖）
- [x] AC6 冻结重放 —— PASS（独立重算精确复现，见 Independent checks）
- [x] AC7 证据闭包 —— PASS（plan/output/4 logs 存在并记录 SHA-256；RESULT 三状态字段齐全，proposed_physical_verdict=NOT_APPLICABLE）
- [x] Claim ceiling —— PASS（RESULT claim 严格限于实现与确定性回归，无物理结论）

## Independent checks
- M5 测试独立复跑：`python3 test/metrics/test_sfq_metrics_v2_m5.py` → **25/25 OK**
- M4 回归独立复跑：`python3 test/metrics/test_sfq_metrics_v2.py` → **15/15 OK**
- **AC6 从 raw CSV 独立重算**（不调用生产代码，用 csv/mean 第一性原理）：
  - B1: corr_rad=6.2831852, turns=0.9999999829418391, sig/ctl 聚类 1/0 ✅
  - B2: corr_rad=6.283185700000001, turns=1.0000000625193106, 聚类 0/0 ✅
  - B3: corr_rad=6.2831854, turns=1.0000000147728276, 聚类 1/0 ✅
  - 样本数 pre 30 / activity 409 / post 900 ✅；与 TASK AC6 常数误差 ≤1.6e-14 rad
  - 与 `output.json` 数值逐项一致（raw 重算 = executor 输出，非自证）
- 冻结输入哈希独立重算：7/8 匹配（`sfq_metrics_v2.py` 为交付物新哈希，属预期）
- bump netlist diff：仅 `.param IIN=0u` vs `.param IIN=300u` 一行（第 6 行）
- 控制对齐：header 逐字一致、时间数组逐元素相等、严格单调（2000 行含表头=1999 数据行）
- replay.log：确认为 raw CSV 的 CLI 调用（`--measurement-plan` + `--control-csv` + `--json`），exit 0

## Hidden-error probes
- 半开窗口/端点 off-by-one → 未发现。`[start,end)`、增量两端点均在窗内、边界样本数（pre 30/post 900/activity 409）独立复核一致
- 严格阈值相等 → 未发现。`abs>threshold` 严格；合成测试用精确 0.25 增量验证相等不激活
- 方向推断/绝对值 → 未发现。direction 严格 ±1 校验，`corrected=dir*(signal−control)`，无 abs；AC6 数值验证方向向量 B1=−1/B2=+1/B3=+1
- delta-of-deltas 退化为末点差 → 未发现。`post_mean − pre_mean`（窗口均值差），独立重算匹配
- 时间插值/最近匹配 → 未发现。header 列表相等 + 时间数组逐元素相等，无插值路径
- 测试 oracle 复用生产逻辑 → 未发现。期望值为首性原理常数（0.25=2^-2、0.5×10、TASK 冻结常数），不调用生产 helper
- 活动样本/簇误称事件 → 未发现。输出与代码均无事件术语
- 冻结重放来自 executor JSON 而非 raw → 未发现。replay.log 显示 CLI 从 raw CSV 运行；我的独立重算与 output.json 一致
- **activity 窗口统计与校验** → **发现缺口（见 Findings Major）**

## Claim ceiling
PASS — RESULT 未越界；LITE 不追溯 FROZEN 的声明正确。

## Findings

### Critical
- None.

### Major
- **Activity 窗口缺失 TASK 要求的统计块与 <2 样本校验。**
  - 观察：TASK "Fixed measurement semantics" 要求"**每个窗口**（pre/activity/post）计算未舍入算术均值并报告请求边界、首/末时间、样本数、min/max、峰峰"，且"**pre、activity、post 每窗至少两个有限样本**"；AC2 要求拒绝"missing or undersampled windows"。实现只对 pre/post 调用 `_window_stats`；activity 窗口输出仅有 `activity_clusters` + `over_threshold_sample_count`（无 mean_rad/sample_count/bounds/min/max/p2p）。
  - 可复现证据：对合法 plan 设 activity 窗为 0 样本（pre=[0,2)、activity=[8.0,8.5)、post=[10,12)，t=i×0.1 网格）→ `windowed_analyze` **不报错**，静默返回空聚类（已实测复现）。
  - 为何重要：AC2 校验语义对 activity 窗口不成立，未来 undersampled activity 窗会产生"看起来有效"的空聚类输出；TASK 明确要求每窗统计报告，属合同语义缺口。
  - 所需修正（二选一）：(a) 为 activity 窗口补 `_window_stats`（mean/sample_count/bounds/min/max/p2p）并对 <2 样本抛错；(b) 若判定 activity 统计非必需，需 Codex 显式接受偏差并记录。**不影响已交付的 AC6 数值与聚类语义**（delta 只依赖 pre/post 均值）。

### Minor
- M1：RESULT Preflight 称 bump netlist diff 在"第 3 行"，实际在**第 6 行**（`.param IIN`）；实质（仅该行不同）正确。
- M2：RESULT Preflight 称"各 2000 行"，实际为 2000 行**含表头 = 1999 数据行**；样本数（30/409/900）正确。
- M3：`FrozenReplayTests` 断言 pre 30 / post 900，但**未断言 activity 409**（我独立复核为 409）；建议补断言。

## Residual uncertainty
- 未在旧版 pandas/numpy/plotly 环境验证（不涉本任务数值）。
- activity 统计缺口是否修正或接受偏差，属 Codex/用户决定。
- 本任务为 LITE，未做 FROZEN 冻结；任何超出 AC6 算术检查的物理解释不在本 REVIEW 范围。

## Codex focus
1. **裁决 Major**：activity 窗口统计块 + <2 样本校验——要求补实现（新 attempt A02）或显式接受偏差；AC6 数值与聚类语义不受影响，修正面窄。
2. 若采纳修正：确认新增/更新测试覆盖 undersampled activity 拒绝与 activity 统计输出。
3. Minor M1/M2/M3 为文档/测试精度问题，可随 A02 一并修正。
4. 独立 CRITICAL 审计建议：按 TASK 要求从 raw CSV 重算三个 corrected deltas（我已复现，供对照）。
