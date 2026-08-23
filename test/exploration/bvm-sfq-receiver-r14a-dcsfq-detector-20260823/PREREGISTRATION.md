# R14-A：B_DET → isolated frozen DCSFQ_BVM feasibility

日期：2026-08-23

模式：`EXPLORATORY`，conditional single-point Exploration

基线：R13-A `abad1d46e5f50b0f0796f00e84f1cdd3bb12bca6`

## Primary question

在保留 R0b/R1a 低电流有源 detector 和 isolation pickup 的条件下，能否把
`B_DET` 的 state-dependent transient 送入完全冻结的 `DCSFQ_BVM` input，
使其产生一个 bounded read1 B3 local regenerative event，而 read0 和两个
READ=0 controls 不产生完整 B3 event？

本轮首先进行 analytic interface precheck。若 loaded DCSFQ input branch
仍只有 single-digit µA 量级且没有证据支持 active current gain，则停止为
`PRECHECK_NO_GO`，不运行 JoSIM。

## Frozen topology if precheck passes

```text
canonical BVM SL
  → R_IN=12 Ω → L_PRI=0.20 pH → B_DET to ground
                                      B_DET AREA=.50, bias=+15 µA

L_PRI -- K=±0.80 -- L_SEC=2.0 pH
                         │
                         ├─ R_SEC_LOAD=12 Ω → ground
                         └─ DCSFQ_BVM port a

DCSFQ_BVM port q → 10 Ω → ground
```

`DCSFQ_BVM.cir` 内部 topology、JJ AREA、IB、L/R、model 和 q load 全部冻结。
不接 JTL/T1，不 sweep K、L、bias 或 load。

## Required precheck

1. 将 R1a secondary `I(R_SEC_LOAD)≈5.56 µA` 与 R13 actual DCSFQ
   `I(L1)` read1 peak `≈110.2 µA`、R12 `68.4 µA` no-event 和 `300 µA`
   controlled one-shot 并列。
2. 使用 R1a measured secondary voltage and lobe timescale，估算并联
   `R_SEC_LOAD` 与 DCSFQ `a` input branch 的 current split。该 estimate
   只作 local scale diagnostic，不是 universal threshold。
3. 审计 `R_SEC_LOAD` 的 provenance 和 KCL。它是 R1a physical termination/
   return，不因连接 DCSFQ 就自动删除；DCSFQ input 是新增 dynamic parallel
   branch，造成 intentional double-loading，必须显式记录。
4. 若 DCSFQ branch 估计仍为 single-digit µA，且没有 active gain evidence，
   verdict=`PRECHECK_NO_GO`，不执行四 case。

## Matched cases if executed

- logical1 + canonical READ
- logical0 + canonical READ
- logical1 + READ=0
- logical0 + READ=0

dt=`0.0125 ps`，stop=`170 ps`；窗口继承 R12/R13 约定：PRE `[80,90) ps`、
activity `[94,130) ps`、POST `[150,170) ps`，canonical READ=`96–105 ps`。

## Event criteria if executed

- B_DET read1 至少一个完整 continuous monotonic phase transition；read0/
  controls zero complete B_DET transition。B_DET multi-turn 只称 detector
  activity，不称 SFQ。
- B3 read1 exactly one complete `≥1 turn` monotonic segment；同一 JJ、同一
  direction、同一 segment 的 phase change 与 direct same-JJ voltage area
  一致；event 后 retrap、无第二完整段、无 free-running。
- B3 read0/control zero complete segment。
- BVM SL/N6/I(L_SL)、JM1/JM2、JS1/JS2 只按 canonical no-receiver
  baseline 比较额外 post-window disturbance；不能把 canonical read1 自身
  的约 −3-turn JS running 当 receiver back-action。

## Stop rules

首个命中即停止且不调参：`PRECHECK_NO_GO`、DCSFQ loading 破坏 B_DET、
`INTERSTAGE_NO_TRIGGER`、`MULTIFIRE`、`NONSELECTIVE_TRIGGER`、
`BACK_ACTION_FAILURE` 或 phase/area evidence `INCONCLUSIVE`。
