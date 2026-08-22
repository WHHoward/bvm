# R11-A：canonical BVM → standard JTL direct compatibility screening

日期：2026-08-23  
模式：`EXPLORATORY` / compatibility control  
唯一研究问题：

> canonical BVM SL 的 logical-1 read transient，经过最小 galvanic direct connection，能否被仓库标准两-cell JTL 接收并形成可逐级传播的 local JTL events，同时 logical-0 与两个 READ=0 controls 不产生完整 propagated event？

## 冻结内容

- canonical BVM topology、JJ model、logical write/read PWL：不变；
- `circuits/standard/JTL.cir`：原样使用；
- 两个 `THmitll_JTL` instances：不改 JJ AREA、L1–L4、bias、bias tee、阻尼或端口；
- direct interface：`SL1 -> XJTL1.a`，`XJTL1.q -> XJTL2.a`；
- output termination：`R_TERM JTL_OUT 0 1`；
- timestep：`0.0125 ps`；stop time：`170 ps`；
- 不接 QB、T1 或其他 receiver；不 sweep JTL/bias/AREA/L；不修改 R10 或既有 raw。

## 先行 positive control

在任何 BVM run 前运行 `positive-control.cir`。它使用同一两-cell chain 和仓库 `test/standard/test_jtl.cir` 的单次 1.5 mV、11–13 ps source stimulus。positive control 必须显示：

1. `XJTL1` 的 B1/B2 各有至少一个完整单调相位段；
2. `XJTL2` 的 B1/B2 也各有对应完整段；
3. 每颗 JJ 的同段 phase change 与同一 JJ 直接 voltage-area 相容；
4. 输出端有对应 transient，事件后回到 bounded/retrapped state，无持续 free-running。

若 positive control 不满足，停止本实验，不评价 BVM compatibility。

## matched BVM cases

| case | write state | READ | 目的 |
|---|---|---|---|
| `read1` | logical 1：WL+BL `+100 µA` | canonical `+100 µA` WL+SE | primary |
| `read0` | logical 0：WL+BL `-100 µA` | canonical `+100 µA` WL+SE | state selectivity |
| `logical1-read0-control` | logical 1：WL+BL `+100 µA` | `READ=0` | no-read control |
| `logical0-read0-control` | logical 0：WL+BL `-100 µA` | `READ=0` | no-read control |

除对应 PWL 激励外，四个网表、步长、仿真终点、JTL chain、输出负载和 probes 完全相同。

## registered measurements

对 `XJTL1`、`XJTL2` 的每颗 `B1/B2` 直接记录 `P`、`V`、`I`，电压方向为 JoSIM 该 JJ 两端的元件方向；同时记录节点电压用于 input/output timing 和每级 inductor/bias current。BVM guard 记录：

- `V(SL1)`、`V(N6|XBVM1)`、`I(L_SL|XBVM1)`；
- `P/V(B_JM1|XBVM1)`、`P/V(B_JM2|XBVM1)`；
- `P/V(B_JS1|XBVM1)`、`P/V(B_JS2|XBVM1)`。

事件判定只使用同一 JJ、同一方向、同一时间段的 continuous/unwrapped phase、最大单调 phase segment、直接 `V(JJ)` 的 `∫Vdt/Φ0` 及事件后 retrap。`I>Ic`、voltage peak、过阈值样本或 phase range alone 不是 event 证据。

建议稳定窗：positive control bias/pre `[8,10) ps`、activity `[10,35) ps`、post `[35,60) ps`；BVM 四 cases pre `[85,94) ps`、activity `[94,130) ps`、post `[130,165) ps`。这些窗由已冻结的 95–106 ps canonical READ 和 positive source 的 11–13 ps stimulus 预先确定；不因结果移动。

## 预注册判定

- `DIRECT_JTL_SELECTIVE_PASS`：read1 在两级四颗 JJ 上各出现且仅出现一个因果传播 event，read0/两个 controls 为零，且 BVM guards 相对 canonical source 可接受；
- `DIRECT_JTL_MULTIPULSE`：read1 进入并传播，但 full tested chain 出现多于一个 propagated event；
- `DIRECT_JTL_NONSELECTIVE`：read0 或 controls 也出现完整 propagated event；
- `FIRST_STAGE_ONLY`：第一 cell 有完整 event，第二 cell 没有对应传播；
- `NO_JTL_TRIGGER`：read1 第一颗 JTL JJ 无完整 event；
- `SOURCE_BACK_ACTION_FAILURE`：JTL loading 使 BVM source/storage guard 相对 canonical baseline 出现显著破坏；
- `INCONCLUSIVE`：artifact、方向映射、稳定窗或 phase/area 双证据不完整。

这些是本次 fixed model/stimulus/load/dt 的 bounded Exploration verdict，不是对 direct-JTL architecture family 的普遍定理。无论结果如何，本轮停止，不接 T1，不同时重做 QB/temporal conditioner。
