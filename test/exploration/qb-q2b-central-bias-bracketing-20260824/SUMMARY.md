# QB-Q2B central-bias bracketing — summary

## Verdict

`BIAS_BRACKET_NO_BJL1_EVENT`

在冻结的 canonical source-isolated replay 下，`IBIAS=30 µA` 与 `40 µA` 两个局部点都没有产生合格的 read1 BJL1 完整 transition。READ=0 controls 和 logical0 replay 保持 bounded，也没有发现 free-running 或 nonselective complete event。

本结论只适用于本次两点 bracket、冻结的 scaled QB 与冻结 replay；不把它升级为所有 central-bias 的普遍不可能性。

## Frozen experiment

- parent: `58d35f96ab5a998fdb6697984a6e713332f94c4e`（QB-Q2A accepted checkpoint）
- only changed variable: `IBIAS`, tested `30 µA` and `40 µA`
- accepted `35 µA` QB-Q2A C/C0 result retained as baseline and not rerun
- BJs/BJL1/BJL2 areas: `.50/.36/.54`
- `Lin=.8 pH`, `L0=1.323 pH`, `L1=L2=3.91 pH`
- `RJ1=33 Ω`, `RJ2=22 Ω`, `RB=6 Ω`, output load `10 Ω`
- canonical logical1/logical0 voltage replay and matched READ=0 replay held byte-identical to QB-Q2A snapshots
- no physical BVM, transformer, DCSFQ, JTL or T1 was connected

## Event evidence

The event decision used raw continuous unwrapped phase and the direct voltage integral over the same JJ and same monotonic segment. A complete event required at least one full turn, same-segment voltage-area consistency, and bounded post behavior. Current peaks, `I/Ic`, voltage peaks, and sub-turn phase activity were not counted as events.

| IBIAS | case | BJL1 largest monotonic segment | BJL1 same-segment area | BJL1 complete events |
|---:|---|---:|---:|---:|
| 30 µA | logical1 + READ | `+0.320614 turn` | `+0.320657 Φ0` | 0 |
| 30 µA | logical0 + READ | `−0.0592331 turn` | `−0.0592432 Φ0` | 0 |
| 30 µA | logical1 + READ=0 | `+3.18e−8 turn` | `+1.68e−8 Φ0` | 0 |
| 30 µA | logical0 + READ=0 | `−2.07e−7 turn` | `−1.99e−7 Φ0` | 0 |
| 40 µA | logical1 + READ | `−0.414649 turn` | `−0.414710 Φ0` | 0 |
| 40 µA | logical0 + READ | `−0.0595289 turn` | `−0.0595391 Φ0` | 0 |
| 40 µA | logical1 + READ=0 | `+6.37e−8 turn` | `+6.04e−8 Φ0` | 0 |
| 40 µA | logical0 + READ=0 | `−3.18e−7 turn` | `−3.12e−7 Φ0` | 0 |

At both points BJs retained a read1 local complete phase/area response, consistent with the previously established Q2A upstream activity, while BJL1 remained sub-turn. This is not downstream SFQ delivery evidence.

## Settled bias observation

The measured settled `I(RB)` values were approximately `29.91 µA` and `39.88 µA`. In the frozen node3 load-line, raising IBIAS moved the settled BJL1 current from roughly `10.18/4.72 µA` (logical1/logical0 at 30 µA) to `12.63/7.25 µA` (40 µA), but did not create a threshold-like BJL1 transition. The detailed branch-current table is in [QB_Q2B_REPORT.md](analysis/QB_Q2B_REPORT.md).

## Interpretation and stop

Observed evidence supports a bounded negative result for this local bias bracket: central-bias movement alone did not close the BJs→BJL1 dynamic gap under the frozen canonical replay. It does not distinguish all possible BJL1 area/ratio/load-line redesigns, and no such redesign was attempted here.

The prescribed stop rule is satisfied: do not append another bias point, change AREA/L/R/load, or reconnect physical BVM in this Exploration. The raw data, failed fixture attempts, commands, analysis, and hashes are retained in this directory.

## Evidence links

- [analytic precheck](QB_Q2B_ANALYTIC_PRECHECK.md)
- [preregistration](PREREGISTRATION.md)
- [full phase/area report](analysis/QB_Q2B_REPORT.md)
- [case metrics](analysis/qb-q2b-case-summary.csv)
- [raw/fixture QA](logs/QA.md)
- [artifact hash list](analysis/SHA256SUMS.txt)
