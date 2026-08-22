# R9-A：native-QB output-side L2 load-line single point

日期：2026-08-23（Asia/Shanghai）
Exploration tier；不升级 Candidate，不接 JTL/T1。

## 预注册研究问题

在已接受的 R7-A 输入侧 routing point 恢复后，单独把 native-QB `L2` 从
`3.91 pH` 降到解析预检选出的 `2.50 pH`，是否能增加 node3→node4/BJL2
的动态传输和/或 BJL2 operating margin，同时保持 read0 selectivity 与
canonical BVM source guard？

## 冻结假设与唯一变更

本轮只改变：

```text
L2 = 2.50 pH
```

其余全部继承 R7-A：

```text
BJs AREA=1.33       BJL1 AREA=1.12      BJL2 AREA=1.89
L1=2.50 pH          Lin=0.80 pH          L0=1.323 pH
IB=90 uA            RB=8.5 ohm           RJ1=33 ohm
RJ2=22 ohm           output load=10 ohm
R_PRI=12 ohm        L_PRI=0.20 pH         L_SEC=1.00 pH
K=0.70710678        canonical BVM unchanged
```

预检及点选择见 `analysis/R9A_ANALYTIC_PRECHECK.md`。不运行其余解析候选，
不追加 L2 sweep，不改变 IB/JJ AREA/L1/transformer。

## Matched cases

完全相同的 receiver/source、PWL、timestep 和 stop time，逐一运行：

1. logical1 + canonical READ (`read1`)
2. logical0 + canonical READ (`read0`)
3. logical1 + READ=0 (`logical1-read0-control`)
4. logical0 + READ=0 (`logical0-read0-control`)

每个 case 只执行一个 R9-A run；R7-A `run-02.csv` 作为历史 comparison，
不覆盖或修改。

## 主要观测与窗口

- settled `[80,90) ps`：`P/I(BJs,BJL1,BJL2)`、`I(L1,L2,Lin,RB)`，以及
  `I(RJ1/RJ2)`；用于 static bias redistribution；
- dynamic `[94,130) ps`：同一 CSV 实际时间轴上的 control-subtracted RMS
  \(\delta I_x=I_{read}-I_{matching\ READ=0\ control}\)，特别是
  `G_L2=RMS(delta I_L2)/RMS(delta I_Lin)` 和
  `G_BJL2=RMS(delta I_BJL2)/RMS(delta I_Lin)`；
- BJL2：raw `P/V/I`、continuous unwrapped phase、activity range、largest
  monotonic segment、同一 segment 的 `∫V(BJL2)dt/Φ0`；
- source/storage：`V(SL1)`、`V(N6)`、`I(L_SL)`、`JM1/JM2` drift、`JS1/JS2`
  post-window p2p，并相对于 canonical no-receiver 与 R7-A 比较。

`P(...)` 保持 rad；所有 phase turn 都显式除以 `2π`。不使用 `I>Ic`、
voltage peak 或 activity spike 单独声明 event。

## 预注册判定边界

- `ROUTING_GAIN_WITH_SELECTIVITY_PRESERVED`：L2/BJL2 control-subtracted
  routing 相对 R7-A 有清晰增加，read0/control 仍有 separation，source guard
  保持；不能因此声称 local event。
- `STATIC_OP_SHIFT_WITHOUT_CLEAR_ROUTING_GAIN`：settled KCL/phase 明显改变，
  但 dynamic routing 没有清晰增加。
- `L2_ROUTING_HYPOTHESIS_NOT_SUPPORTED_AT_THIS_POINT`：没有有意义的 routing
  或 nonlinear gain，且无其他 failure。
- `ISOLATED_NATIVE_QB_LOCAL_PASS`：除此之外，read1 BJL2 至少一个完整
  continuous monotonic `>=1 turn`，同段 voltage area 一致，随后 retrap 且
  无第二个完整 event；read0/control 为零。
- `BACK_ACTION_OR_NONSELECTIVE_FAILURE`：source/storage guard 明显恶化、
  read0/control 非选择性 activity 或 free-running。
- `INCONCLUSIVE`：artifact、时间轴、列、窗口或同 JJ 双证据不足。

若没有明显 BJL2 nonlinear gain，本轮结束 passive load-line routing 分支，
下一步仅建议 bias-routing / BVM-specific QB redesign 的单独设计审查，
不继续微调 L2。

## Provenance

- parent accepted baseline: `edf3226df72f913c4c42bd628bd1a9e949fd0b73`
- R7-A comparison: `test/exploration/bvm-sfq-receiver-r7a-l1-routing-20260823/`
- metric semantics: `docs/research/METRIC_SPEC_V2.md` v2.0.0
- JoSIM: `build/josim-cli`, v2.7.2837d13
- requested timestep: `0.0125 ps`; stop time: `170 ps`
