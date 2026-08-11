# REVIEW M12-LITE-PILOT-001 / A01

Review disposition: **PASS**
Recommended risk: CRITICAL
Recommended evidence mode: LITE
Evidence confidence: HIGH
Residual risk: LOW

Reviewed delivery snapshot: `3939b49`（实现内容 snapshot `caa55e4`；两者实现文件字节级一致，`caa55e4..3939b49` 仅补填 RESULT 的 Delivery snapshot 段）

## Scope
PASS

Evidence:
- worktree `/home/howard/JoSIM-m12-lite`，branch `claude/M12-LITE-PILOT-001`，HEAD `3939b49`；
- 执行前 `git status --porcelain=v1 --untracked-files=all`：clean；
- 变更文件（`1994cb8..caa55e4`）：`scripts/josim-plot2.py`、`test/plot/test_josim_plot2.py`、`attempts/A01/RESULT.md`、`attempts/A01/logs/unit-tests.log`——全部在 TASK allowed paths 内；
- 全程未修改 TASK / RESULT / 实现 / 日志 / 协议文件。

## Acceptance criteria
- [x] AC1 五种布局对 P(...) 一致使用 `pfact(args.jump)`；非 phase trace 不被缩放 —— PASS（代码核对 + 独立测试）
- [x] AC2 `-j 2pi` 标签为 turns / rad÷2π，不写 SFQ count —— PASS
- [x] AC3 自动测试覆盖五布局、raw rad 与 2pi，且能区分"仅改标签未缩放"旧错误 —— PASS（断言作用于 trace 数据值）
- [x] AC4 运行测试并记录命令/退出码/日志；不运行 JoSIM —— PASS（unit-tests.log 存在；未运行 JoSIM）
- [x] AC5 RESULT claim 限于绘图实现正确性，无物理 Gate 结论 —— PASS

## Independent checks
- 独立重跑 `python3 test/plot/test_josim_plot2.py` → **5/5 OK**（与 RESULT 一致）
- 数值交叉校验：`pfact(rad)=1.0`、`pfact(0.5pi)=0.6366`、`pfact(pi)=0.3183`、`pfact(2pi)=0.1592=1/(2π)`；`π rad` 在 `-j 2pi` 下 → 0.5 turn，`2π rad` → 1.0 turn，与 `v/2π` 精确一致（np.allclose True）
- 标签输出：`rad`→"Phase (rad)"、`2pi`→"Phase (turns) [rad/2pi]"（无 SFQ 字样）
- 五布局缩放代码核对：grid/square/stacked 本次修复（P 乘 pfact、非 P 不乘）；combined/sep_comb 原有逻辑已正确（combined_layout 的 P 分支乘 pfact，V/I/U 分支不乘；seperate_combined_layout 的 P 组乘 pfact、V/I/U 组不乘）——RESULT 的"combined/sep_comb 原本正确"声明属实
- snapshot 一致性：`git diff caa55e4..3939b49 -- scripts/josim-plot2.py test/plot/test_josim_plot2.py` → 0 行（实现未在 delivery snapshot 阶段变动）

## Hidden-error probes
- "仅改标签、数据未缩放？" → 探针：测试断言 `trace.y` 数据值（非标签）；独立复跑 5/5 PASS；数值交叉校验匹配 → 数据确实缩放 ✅
- "五布局缩放不一致？" → 探针：逐布局读 combined_layout / seperate_combined_layout 代码 + 全布局测试 → 一致 ✅
- "非 P trace 被错误缩放？" → 探针：`NonPhaseScalingTests.test_voltage_traces_unaffected_by_jump`（V 在 rad/2pi 下相同）+ 代码核对（`plots[i][0]=='P'` 分支）→ V 不受影响 ✅
- "测试 oracle 与实现同错？" → 探针：测试硬编码 `TAU=2π` 计算期望值，**未调用实现的 `pfact`**；旧实现（未缩放）会因数据断言失败 → oracle 独立 ✅
- "`-j 2pi` 被误写成 SFQ 计数？" → 探针：`assertNotIn("SFQ"/"sfq")` + 独立调用 `y_axis_title` 输出 → 无 SFQ 字样，含 "turns" ✅

## Claim ceiling
PASS — RESULT claim（"五种布局 -j 相位缩放与回归测试验证完成；无 SFQ/事件/通量/物理 Gate 结论"）严格位于 TASK claim ceiling 内。

## Findings

### Critical
- None.

### Major
- None.

### Minor
- RESULT Verification 提到 CLI 冒烟（5 布局 × 2 jump 生成 html）但未保留 CLI 日志文件（evidence 仅 unit-tests.log）。AC4 的可复现性对函数级测试已满足；CLI 冒烟缺日志属轻微证据缺口，不影响本次结论（不涉 JoSIM/物理）。
- 缩放判定用列名首字符 `plots[i][0] == 'P'` 启发式：相位列若不以 "P" 开头则不会被缩放。与现有命名约定（`P(...)`/`V(...)`）一致，任务范围内可接受，记录为已知约定。

## Residual uncertainty
- 测试在 plotly 6.3.0 / pandas 2.3.3 / numpy 2.3.5 环境验证；旧版 plotly trace 数据结构未验证（executor 已声明）。
- 未运行 JoSIM / 未涉及任何物理数据（符合 TASK 范围）。

## Codex focus
1. 结论：M12 绘图实现与回归测试在 evidence 层 **PASS**；五布局缩放一致性、非 P 不受影响、oracle 独立、无 SFQ 误标均经独立验证。
2. 可选：补 CLI 冒烟日志以闭合 AC4 的轻微证据缺口（非阻塞）。
3. 可考虑在 REVIEW 后推进 Pilot 2（M5 measurement implementation, CRITICAL+LITE）。
