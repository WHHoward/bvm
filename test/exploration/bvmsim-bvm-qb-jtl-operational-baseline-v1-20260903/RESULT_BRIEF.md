# Historical BVMSim operational baseline V1

> 初始 setup 文件。完成运行后，本文件按预注册顺序更新；raw、deck 和失败
> attempt 不覆盖。

## 1. What changed

建立 historical BVMSim operational profile，并在本实验目录中准备 original
QB 的 single-BVM、4-BVM 16-state baseline 与后续 working-margin 的 task-local
fixture。`RJ1=12 ohm` 保持 nominal。

## 2. What did not change

没有修改 `BVMSim/` 下的 historical source，没有切换 canonical BVM，没有改
RJ2、JJ area、L/C、JTL bias、timestep 或 T1。

## 3--9. Results

待 baseline 和 margin run 完成后填写：historical anchor、isolated single-BVM、
16-state transfer、IB margin、RJ1 shunt margin、physical-input margin、
pairwise interaction。

## 10. INFERENCE

待 evidence audit 后填写；不会把 local phase turns 自动解释为 SFQ count。

## 11. UNKNOWN

本 setup 本身不提供 canonical compatibility、timestep convergence、process
margin、T1 compatibility 或 paper mechanism identity。

## 12. Reasonable next options

1. 用户审阅本轮 raw、关键图和 margin 结果。
2. 若确有必要，另行授权 canonical-BVM 对照。
3. 若确有必要，另行授权 T1 integration。

## Current gate

`AWAITING_USER_REVIEW`；`user_reviewed=false`；`next_step_authorized=false`；
`automatic_next_experiment=false`。

