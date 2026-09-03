# Execution notes

- `F4_1011` 的首次 `attempt-01` command 写错了实验目录路径并以 exit 255
  结束；该失败 log/command 保留，随后 `attempt-02` 在正确 deck 上 exit 0。
  这不是物理失败。
- `S0-J`、`S1-J` 的首次 raw 保留不动。首次生成的 deck 漏了六级 JTL 的 P/V
  probes；`attempt-02` 只增加这些 probes，使用相同 historical source、参数、
  stimulus、timestep 和 stop time，exit 0，并作为当前可视化/分析 raw。
- `F4_0010` 的早期 log 文件名曾写成 `run-01.csv`；该记录和 raw 保留，
  不影响 raw 内容或分析选择。
- single-BVM original-BQ deck 的执行日志保留了 JoSIM 的 `Missing model: JJMIT`/
  `Using default model` warning；4-BVM historical fixture 自身有可见的顶层 model，
  未出现该 warning。这是各 fixture 的实际历史执行行为；本轮没有用
  `circuits/models/jjmit.cir` 偷换或“修正” single-BVM QB，因此不能把这些结果
  描述成使用 shared jjmit model 的新 QB 结果。
- 因 nominal 16-state stop rule 失败，没有创建或执行 `IB`、`RJ1`、input-alpha
  margin 或 pairwise map。
- selected nominal runs 的 exit code 与 solver-log SHA-256 由
  `analysis/execution_outcomes.json` 和重新生成的 `execution_manifest.json`
  绑定；`F4_1011` 的错误路径 attempt-01 仍作为非物理失败历史保留。
- 所有 selected raw 的 requested timestep 是 `0.1 ps`，但 stored grid 在
  `62.8→63.0 ps` 有一次 `0.2 ps` gap；这不是 uniform-grid 或 timestep-convergence
  证据。分析使用实际时间列。
