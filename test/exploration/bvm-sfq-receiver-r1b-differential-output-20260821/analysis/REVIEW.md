# R1b differential-output numerical/adversarial review

## Disposition

结论为 **artifact-valid / R1b FAIL**。失败的必要条件是 read1 `B_OUT`
没有一个完整 2π 单调段；不是把 artifact 标成 INVALID，也不是把 R0b 或
R1a 前端判为失败。

## Numerical review

1. 事件判据直接读取同一 junction 的 `P(B_OUT|XTRIG)` 与
   `V(B_OUT|XTRIG)`。read1 最大段为 `0.0220583499` turn，area
   `0.0220676540` turn；read0 为 `0.0051599306` / `0.0051622416`。
   因而 phase 与 voltage area 一致地支持“subturn transient”，不支持
   complete switching。
2. phase 数据以 raw radians 保存；turns 使用 `delta/(2*pi)`。segment
   endpoints、方向和 actual CSV timestamps 来自结构化分析；没有用
   derivative sample count、peak voltage 或 `I > Ic` 计 event。
3. 四个 correction CSV 每个 13,599 行，时间严格增加且 finite；requested
   `dt=.0125 ps`，实际 observed `dt_min≈.0125 ps`、`dt_max=.025 ps`。
   所有 voltage-area 计算使用这组非均匀时间戳，而不是把样本间隔强制成
   常数。
4. `analysis/independent-crosscheck.json` 以独立 raw reader 复算四 case 的
   SHA、BTRIG/BOUT phase、same-JJ area、complete flags、secondary 和
   storage pre/post medians，`all_comparisons_pass=true`。
5. 实际 model semantics 已记录：output `AREA=.10` 对应
   `Ic=10 uA`, `RN=160 ohm`, `R0=1600 ohm`, `C=7 fF`；`100 ohm` 是
   外部 parallel damping。没有按旧 beta 值或只按 Ic 解释 AREA。

## Adversarial review

### Common-mode trap

旧 R1b topology 的失败被指出为 `V(N_OUT)` 跟随 `V(N_SEC)`、
`V(B_OUT)=0`。本轮 correction 不再使用 `B_OUT=N_OUT-N_SEC`：
`B_OUT` 直接为 `N_SEC` 到 ground，且 `L_SEC` 通过 `R_SEC_LOAD` 串联
返回。初始点的 KCL 分流（约 `6.599 uA` 进入 zero-voltage LSEC branch，
约 `0.401 uA` 到 BOUT）和 correction 后约 `7 uA` pre-bias 均由 branch
probes 检查。因此最终的 `B_OUT` transient 不是 numerical-zero common-mode
伪影；它是真实但 subcritical 的 differential local activity。

### Threshold shortcut

read1 的 `I(B_OUT)` peak 约 `8.240 uA`，小于 nominal `Ic=10 uA`；即使
存在 over-threshold sample，本 review 也不会仅凭该事实宣称 event。最终
判断只由 continuous/unwrapped phase、monotonic segment 和 same-JJ area
共同决定。

### Matrix and controls

使用完全相同 receiver 的 `read1`、`read0`、logical1+READ=0、
logical0+READ=0 四 case。controls 的 BOUT phase 仅约 `1.75e-7` 和
`2.55e-7` turn，secondary 仅 sub-nV/pA 量级；没有 free-running output。

### Back-action and stale evidence

R1a raw baseline 与 loaded correction 由独立脚本比较；BTRIG complete/read0
guard 和 SL/N6 state separation 保留。JM1/JM2 logical signs 保留，但
JM2 的定量 drift 相对 R1a 改变，因此 review 明确不把“sign guard pass”
升级成完整 storage-preservation claim。

### Invalid first invocation

初始 direct point 的第一次 invocation 因 subckt 名称错误没有 raw output；该
artifact 的 stdout/stderr/analysis 被保留并与 valid `run-02` 分开。它不参与
最终 physical metrics，也没有覆盖任何 raw。四个 correction run 的 solver
stderr 为空且 CSV QA 通过，所以最终 disposition 是 FAIL，不是 INVALID。

## Remaining uncertainty

本轮是 bounded Exploration：没有做三步 timestep convergence、没有长窗口
重复、没有 output-JTL/downstream receiver，也没有探索 output operating
window。因此只能支持“此 topology/point 在此 matched matrix 下未激活
`B_OUT`”，不能支持普遍不可能性或路线级否定。

## Review conclusion

`B_TRIG` 前端 guard：PASS；secondary differential extraction：PASS；
read0/control suppression：PASS；read1 B_OUT complete activation：FAIL；
整体 R1b：**FAIL**。不启动 R1c，不做 JTL，不升级 Candidate。
