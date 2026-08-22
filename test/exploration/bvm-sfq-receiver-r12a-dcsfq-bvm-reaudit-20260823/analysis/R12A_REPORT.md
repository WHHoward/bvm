# R12-A：historical DCSFQ_BVM re-audit + canonical BVM compatibility

日期：2026-08-23
基线 HEAD：`ca610ce73bf78ddc99edf3f03197be1968bfe8b2`
模式：Exploration；未修改 canonical BVM、`DCSFQ_BVM.cir`、`JTL.cir` 或
`jjmit.cir`。

## 1. Artifact and provenance

- 仿真器：`build/josim-cli` v`2.7.2837d13`，SHA-256
  `48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2`。
- Phase A 三个 raw 均 exit 0，2000 行（header + 1999 samples），`.tran
  0.1p 200p`，median `dt=0.1 ps`。
- Phase B 四个 raw 均 exit 0，13600 行（header + 13599 samples），`.tran
  0.0125p 170p`，median `dt=0.0125 ps`。
- 所有事件判断直接从 raw CSV 的连续 `P(...)`、同一 JJ 的 `V(...)` 和同一
  时间段的 `∫Vdt/Φ0` 得出；没有调用旧 `sfq_metrics.py fast_events`。
- Phase B 使用了与 R11-A 相同的两-cell ColdFlux standard JTL。R11-A 已用同一
  chain 的仓库 standard-SFQ positive control 验证四颗 JTL JJ 的 phase/area
  一致性和级联传播；本轮没有改变该 fixture。

原始文件、输入、日志、分析 JSON 和 SHA-256 清单见本目录的 `raw/`、`inputs/`、
`logs/` 和 `analysis/`。

## 2. Frozen topology and gates

### Phase A

原样使用 `THmitll_DCSFQ_BVM a q`，外接 10 Ω `R_LOAD`。三个受控输入只改变
`IIN`：`0 µA`、历史 `68.4 µA`、强 bump `300 µA`。PWL 为 10–12 ps 上升、
12–40 ps 保持、40–45 ps 下降；bias startup `[0,7) ps`，input window
`[10,45) ps`，post window `[60,180) ps`。

### Phase B

冻结连接为：

```text
canonical BVM SL → THmitll_DCSFQ_BVM.a → q
                 → THmitll_JTL cell 1 → THmitll_JTL cell 2 → 1 Ω
```

BVM 内部 `R_SL/L_SL` 保留；`DCSFQ_BVM` 的 B1/B2/B3、IB1/IB2、L/R 和
`JTL.cir` 全部保留；没有 transformer、amplifier、matching network 或 T1。
实际 DC/transient load 关系见 `PHASE_B_TOPOLOGY_PRECHECK.md`。

## 3. Phase-A historical converter re-audit

表中是 `case − 0 µA` 的 differential continuous phase；零输入运行只用于扣除
共同 bias-startup trajectory。`largest segment` 仍是描述性分段，事件结论还要求
同段面积和 post bounded behavior。

| case | JJ | differential activity range (turn) | largest monotonic segment (turn) | same-JJ V-area (turn) | area residual (turn) | post p2p (turn) |
|---|---|---:|---:|---:|---:|---:|
| 0 µA | B1/B2/B3 | 0 / 0 / 0 | 0 / 0 / 0 | — / — / — | — / — / — | 0 |
| 68.4 µA | B1 | 0.04451 | +0.04417 | +0.04424 | −7.88e−5 | 1.07e−4 |
| 68.4 µA | B2 | 0.03284 | +0.03233 | +0.03240 | −6.43e−5 | 1.31e−4 |
| 68.4 µA | B3 | 0.00935 | +0.00809 | +0.00810 | −4.38e−6 | 1.33e−5 |
| 300 µA | B1 | 1.16712 | −0.61808 | −0.61969 | +1.61e−3 | 4.96e−4 |
| 300 µA | B2 | 1.24344 | +0.93408 | +0.93525 | −1.17e−3 | 6.31e−4 |
| 300 µA | B3 | 1.07739 | **+1.03011** | **+1.03268** | **−2.57e−3** | 7.07e−5 |

### Phase-A interpretation

- `68.4 µA`：B3 最大差分单调段只有 `0.00809 turn`，因此确实没有完整
  converter output event；旧 fast-event 计数不能改变这一结论。
- `300 µA`：B3 从约 `10.0 ps` 到 `28.9 ps` 有一个约 `+1.03011-turn`
  continuous monotonic segment，同一段电压面积 `+1.03268 turn`，两者残差
  约 `−0.00257 turn`。其余 B3 轨迹和 `[60,180) ps` post p2p 均为小幅 bounded
  ringing，没有第二个 >=1-turn B3 segment。
- 因而 Phase A 建立了 **300 µA controlled bump 下的一个 bounded B3 local
  regenerative event**，同时证明历史 `68.4 µA` point 没有完整 event。这个 local
  phase transition 不称为 downstream SFQ delivery。
- 300 µA 强 bump 的 input branch `I(L1)` 达到 300 µA，`I(L2)` 约从 41.6 µA
  动态到 412.4 µA，`I(L3)` 约为 −112.4 到 +56.4 µA；内部 bias `IB1/IB2`
  保持 100/175 µA。这说明 300 µA 是有效的强受控激励，不是 bias-startup
  伪影，但不把该幅值外推成 canonical BVM 的实际 output requirement。

**Phase-A gate：通过（converter effective regenerative behavior established）。**

## 4. Phase-B canonical BVM cascade

### Converter and JTL direct evidence

以下为 `B3` 和两-cell chain 的最大活动/单调段；完整 B1/B2/B3 与四颗 JTL JJ
的 phase、V、current、segment onset、same-segment area、post p2p 均保存于
`analysis/phase-b-metrics.json`。

| case | B3 activity range | B3 largest segment / area (turn) | B3 post p2p | JTL1 B1 / B2 largest (turn) | JTL2 B1 / B2 largest (turn) |
|---|---:|---:|---:|---:|---:|
| read1 | 0.03666 | −0.03654 / −0.03655 | 9.71e−4 | +0.01437 / +0.006663 | −0.003658 / +0.001568 |
| read0 | 0.009525 | +0.009525 / +0.009528 | 3.30e−4 | −0.003675 / +0.001747 | −0.000802 / −0.000421 |
| logical1 READ=0 | 4.46e−7 | 4.46e−7 / 4.32e−7 | 7.96e−8 | 1.59e−7 / −7.96e−8 | 6.37e−8 / 4.77e−8 |
| logical0 READ=0 | 4.30e−7 | −4.30e−7 / −4.18e−7 | 6.37e−8 | 1.59e−7 / +7.96e−8 | 6.37e−8 / +3.18e−8 |

read1 的 B1/B2 前级活动明显高于 read0/control，但 B3 仍只有约 `0.0365 turn`；
四颗 JTL JJ 都远低于完整 2π transition。所有 same-JJ phase/area residual
都与 sub-turn transient 一致，不能由电压 peak 或电流 peak升级为 event。

### Settled/current operating point and dynamic range

`[85,94) ps` settled reference 下四个 case 的 converter operating point 基本相同：

| quantity | settled value |
|---|---:|
| `I(B1|XCONV)` | −41.834 µA |
| `I(B2|XCONV)` | +60.387 µA |
| `I(B3|XCONV)` | +171.791 µA |
| `I(L2|XCONV)` / `I(L3|XCONV)` | +41.834 / −41.834 µA |
| `I(L6|XCONV)` | +0.988 µA |
| `I(IB1|XCONV)` / `I(IB2|XCONV)` | 100 / 175 µA |
| JTL1 B1/B2 current | 175.551 / 175.307 µA |
| JTL2 B1/B2 current | 174.944 / 175.186 µA |

read1 activity 中 `I(B3)` 约为 `140.87–202.54 µA`，read0 为
`163.72–179.63 µA`；这些 current ranges 只说明 dynamic activity，不能替代
phase/event 判据。read1 的 `V(CONV_Q)` p2p 约 `76.99 µV`，但 q、JTL output
的 voltage transient 仍没有对应完整 phase transition。

## 5. Canonical BVM source/storage comparison

比较对象是现有 canonical no-receiver raw，而不是把 read1 本身的约 −3-turn
JS running 错算成 receiver back-action。

| case | `V(SL)` post p2p direct / canonical (µV) | `V(N6)` post p2p direct / canonical (µV) | `I(L_SL)` post p2p direct / canonical (µA) | JS2 post-p2p ratio |
|---|---:|---:|---:|---:|
| read1 | 45.34 / 4.230 | 58.85 / 8.510 | 2.719 / 0.3525 | 7.02× |
| read0 | 8.474 / 1.783 | 12.15 / 3.581 | 0.5103 / 0.1486 | 2.73× |
| logical1 READ=0 | 0.003154 / 0.003639 | 0.005569 / 0.007300 | 0.0003144 / 0.0003033 | 1.05× |
| logical0 READ=0 | 0.003163 / 0.003639 | 0.005587 / 0.007300 | 0.0003155 / 0.0003033 | 1.05× |

read1 的 canonical storage signature 仍保留：`JS1/JS2` pre→post net 约
`−2.9999/−3.0000 turns`；read0 和两个 controls 没有相同的 running sign。
`JM1/JM2` 也没有发生逻辑符号翻转或 post free-running。另一方面，直接把
DCSFQ_BVM 挂到 SL 会引入可测的 bounded source/post ringing，尤其 read1 的
SL/N6 p2p 比 no-receiver 大；因此本点不是 R6-A 那种近乎透明的 source
isolation。它没有在 controls 中自发启动，也没有证据表明 canonical storage
state 被改写，但不能声称“无 loading”。

## 6. Observed / Derived / Inference / Unknown

### Observed

- Phase A 的 68.4 µA B3 differential response 为 sub-turn；300 µA 有一个 phase/
  same-JJ-area 一致的约一圈 B3 segment，post bounded。
- Phase B canonical read1 在 DCSFQ_BVM B1/B2/B3 中有明显 state-dependent
  nonlinear activity，但 B3 最大只有约 `0.0365 turn`；两级 JTL 全部为 sub-turn。
- read0 activity 明显小于 read1；两个 READ=0 controls 只有数值背景量级，
  没有 free-running。
- direct cascade 造成有限的 source/post disturbance，但保留了 canonical read1
  的 JS1/JS2 sign/scale 和 storage logical distinction。

### Derived

- 300 µA controlled bump 可以激活现有 converter 的 B3 local regenerative
  mechanism；历史 68.4 µA 不能。
- canonical BVM SL 在原始 DCSFQ_BVM direct interface 下没有把 converter 推入
  B3 complete-event regime，更没有形成可传播的 standard-JTL event。
- read1/read0 activity separation 存在，但远未达到 local event 或 downstream
  reception 证据。

### Inference

- 本 fixed native DCSFQ_BVM point 的主要限制是 canonical SL transient 相对
  converter 的 regenerative input scale/dwell 不足，而不是 JTL chain 本身；这是
  当前 topology、load、stimulus、model 和 timestep 下的 bounded inference。
- 不能从 Phase A 的 300 µA success 推出 canonical BVM 已满足同一 input scale；
  也不能从这一失败宣称所有 DCSFQ 或所有 direct interfaces 不可行。

### Unknown

- BVM-specific temporal rectification/hold 或统一 scaling 是否能在 source guard
  下把现有 read1 transient送入 B3；本轮未测试。
- time-step convergence、不同 load 和参数族的响应；本轮没有 sweep。
- downstream T1 接收；本轮没有接 T1。

## 7. Verdict

**Phase A：** `REGENERATIVE_LOCAL_BEHAVIOR_ESTABLISHED`（仅对 300 µA controlled
bump；68.4 µA 无完整 event）。

**Phase B 主 verdict：`DCSFQ_BVM_NO_TRIGGER`。**

- `DCSFQ_BVM_SELECTIVE_JTL_PASS`：未满足；read1 没有 B3 complete event，JTL
  也没有 event。
- `DCSFQ_BVM_LOCAL_ONLY`：未满足；canonical read1 连 converter B3 local event
  都没有。
- `DCSFQ_BVM_MULTIPULSE`：未观察到。
- `DCSFQ_BVM_NONSELECTIVE`：未观察到；read0/control 没有 complete event。
- `SOURCE_BACK_ACTION_FAILURE`：不作为本轮主 verdict；controls quiet、storage
  logical signature 保持，但 direct SL loading 的 bounded extra ringing 已明确
  记录，故不能把此 point称为 source-isolated success。

本轮按 gate 停止：不 sweep B1/B2/IB/L，不接 T1，不恢复旧 45–55 µA threshold
assumption。下一 architecture decision 应回到 **BVM-specific temporal
rectification / hold → biased one-shot regenerator**，而不是继续把原始
`DCSFQ_BVM.cir` 当作已兼容 converter。
