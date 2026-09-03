# PHASE A — shared tooling golden parity

- Status: `INFRA_REGRESSION_PASS`
- Simulation invoked: `false`
- Golden inputs: corrected single-BVM S0-J/S1-J and historical 4-BVM 1111
- Checks: `94` total, `0` failed

本报告只记录 measurement implementation parity；不产生新的物理 verdict。
旧实验 raw、deck、metrics、plots、reports 和 analysis outputs 未被修改。

## Passed scope

- same-JJ phase/area arithmetic and explicit consistency
- waveform window and peak timing summaries
- strict event-list anchor fields for historical 1111
- caller-declared WL+BL WRITE / WL+SE READ plateau validation
- hierarchical probe coverage and static deck/header QA
- shared KCL residual arithmetic anchor

结论：`INFRA_REGRESSION_PASS`，现在才允许进入 PHASE B。
