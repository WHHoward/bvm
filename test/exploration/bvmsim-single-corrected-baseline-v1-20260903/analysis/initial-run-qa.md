# 初次 corrected run 的观测完整性记录

本文件记录首次执行 `run.sh` 后发现的观测层问题。四个 raw、deck 和
log 均保留，不覆盖、不删除。

## 结果

- `S0-R-CORRECTED`、`S1-R-CORRECTED`：控制信号、模型闭合、12-JJ terminal
  拓扑和 direct-load 所需探针均已生成。
- `S0-J-CORRECTED`、`S1-J-CORRECTED`：控制信号、模型闭合、12-JJ terminal
  拓扑和 JTL 物理运行均已生成，但初次 deck 没有加入
  `P/V(B01|XJTL1_n)`、`P/V(B02|XJTL1_n)` 打印行。

## 状态边界

初次 JTL raw 可用于确认该次仿真完成且模型没有 fallback，但不能作为
六级 JTL 逐级传输计数的完整证据，状态记为 `OBSERVABILITY_INCOMPLETE`。
后续只增加 JTL 探针并建立新的不可覆盖 rerun；不修改本文件所指向的
初次 raw/deck/log。
