# TASK M12-LITE-PILOT-001

Risk: CRITICAL
Evidence mode: LITE
Task revision commit: resolve as the Git commit that first adds this TASK.md.
Execution baseline commit: same resolved Task revision commit.
Delivery snapshot owner: CODEX

## Goal

修复 `scripts/josim-plot2.py -j` 在 grid、stacked、square、combined、sep_comb 五种布局中的 phase 缩放一致性，并加入自动回归测试；`-j 2pi` 必须显示 phase turns，而非 SFQ 计数。

## Allowed paths

- `scripts/josim-plot2.py`
- `test/plot/**`
- `research/tasks/M12-LITE-PILOT-001/attempts/**`

## Acceptance criteria

- [ ] 五种布局对 `P(...)` trace 一致使用 `pfact(args.jump)`；非 phase trace 不被错误缩放。
- [ ] `-j 2pi` 的 phase 标签为 turns/rad÷2π，不写 SFQ count。
- [ ] 自动测试覆盖五种布局、raw rad 与 2pi，且能区分“仅改标签未缩放”的旧错误。
- [ ] 运行相关测试并记录命令、退出码和日志；不运行 JoSIM、不生成或解释物理证据。
- [ ] RESULT claim 限于绘图实现正确性，不形成 SFQ/JTL/物理 Gate 结论。

## Stop conditions

- baseline 不一致、初始 worktree 不干净、需要改 allowed paths 外文件、缺少可运行的测试依赖，或发现缩放语义需改 metric/物理规则时停止并报告 BLOCKED。

## Claim ceiling

Plotting implementation and regression tests verified only. No physical conclusion, event count, fluxoid count, or system Gate claim.
