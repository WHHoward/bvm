# M5-Q0 attempt 01 — execution path error

该尝试没有启动 JoSIM，也没有生成 raw scientific data。

- command working directory：`test/exploration/parallel-qb-jtl-interface-mechanism-20260824`
- command 使用了相对路径 `./build/josim-cli`；该 binary 实际位于 repository root 的 `build/josim-cli`；
- shell exit：`127`；
- stderr：`./build/josim-cli: No such file or directory`；
- 后续使用 repository-root working directory 重跑同一 frozen deck，见
  `logs-v2/M5-q0-scaled/` 与最终 `raw-v2/M5-q0-scaled/run.csv`。

该 attempt 不属于 physical failure，且没有覆盖任何 raw result。
