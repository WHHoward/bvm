# RESULT M12-LITE-PILOT-001 / A01

execution_status: COMPLETED
executor_artifact_assessment: VALID
proposed_physical_verdict: NOT_APPLICABLE

## Preflight
Task revision commit: 1994cb812d7ece38063e357d150d1385f91103c4
Execution baseline commit: 1994cb812d7ece38063e357d150d1385f91103c4
Observed HEAD: 1994cb812d7ece38063e357d150d1385f91103c4
Branch/worktree: claude/M12-LITE-PILOT-001 / /home/howard/JoSIM-m12-lite
Git status:
  （clean，0 个未跟踪/修改文件）
Allowed paths: understood（scripts/josim-plot2.py、test/plot/**、attempts/**）
Risk: CRITICAL
Evidence mode: LITE
Claim ceiling: understood（绘图实现正确性；无物理结论）
Ambiguity: none
Preflight result: PASS

## Summary
修复 `josim-plot2.py -j` 相位缩放一致性：grid / stacked / square 三种布局的
P(...) trace 此前只改 Y 轴标签而未缩放数据（combined / sep_comb 已正确）；
现统一按 `pfact(args.jump)` 缩放。`-j 2pi` 标签改为 "Phase (turns) [rad/2pi]"
（不含 SFQ count 字样）。

## Changes
- scripts/josim-plot2.py：grid_layout / square_layout / stacked_layout 的
  P trace 数据乘 pfact(args.jump)；y_axis_title 的 2pi 分支标签含 turns。
- test/plot/test_josim_plot2.py（新增）：5 个测试类覆盖五种布局 ×
  rad/2pi 的 P trace 数值缩放、V trace 不被缩放、标签语义。

## Verification
- python3 test/plot/test_josim_plot2.py → exit 0，5/5 PASS（日志见 logs/unit-tests.log）
- CLI 冒烟：5 布局 × 2 jump 全部成功生成 html（无 JoSIM 运行）

## Evidence
- research/tasks/M12-LITE-PILOT-001/attempts/A01/logs/unit-tests.log
- 合成 CSV（time/P(B01)/V(N1)）驱动函数级与 CLI 级验证；无物理数据

## Changed files
- scripts/josim-plot2.py
- test/plot/test_josim_plot2.py
- research/tasks/M12-LITE-PILOT-001/attempts/A01/RESULT.md（本文件）
- research/tasks/M12-LITE-PILOT-001/attempts/A01/logs/unit-tests.log

## Limitations / anomalies
- 测试在 plotly 6.3.0 / pandas 2.3.3 / numpy 2.3.5 环境下运行；旧版 plotly 的
  trace 数据结构未验证（脚本依赖未声明版本上限）。
- 未运行 JoSIM；未生成或解释任何物理证据。

## Claim
josim-plot2.py 五种布局的 -j 相位缩放与回归测试验证完成。
无 SFQ/事件/通量/物理 Gate 结论。

---

## Delivery snapshot（由授权 owner 追加）
Delivery snapshot commit: caa55e4d5ce862b95c6378e1a6a6894be29ee165
Snapshot owner: CODEX
Snapshot scope check: PASS (allowed paths only)
