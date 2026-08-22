# R10-A 结果报告：output-side local BJL2 bias routing
日期：2026-08-23（Asia/Shanghai）
父基线：R9-A，`333945981332f9b37b4228e71d82201427b782cd`
实验目录：`test/exploration/bvm-sfq-receiver-r10a-local-bjl2-bias-20260823/`

## Verdict
**`BACK_ACTION_OR_NONSELECTIVE_FAILURE`**
四个 matched case 都在 local feed ramp 后进入 BJL2 multi-turn running；两个 READ=0 control 也出现同等级完整连续 phase activity。 因此 read1/read0 selective local event、retrap 和 source guard 均未成立。这个结论只否定本实验的 `214 µA / 21.4 mV / 100 Ω / 10 pH` 单点，不把整个 local-bias family 说成普遍不可能。

## 1. Topology and frozen boundary
local feed 注入 native QB node 4（BJL2 上端）：`BIAS → R_LOCAL_BJL2=100 Ω → L_LOCAL_BJL2=10 pH → node4`，独立电压源 `V(BIAS)=21.4 mV` ramp 到 DC，负端回地。 这不是直接跨 BJL2 的 passive damping shunt；它是一个具有有限 DC/AC 源阻抗的主动 bias branch。 在 1.5 ps，`Z≈100+j41.89 Ω`，`|Z|≈108.42 Ω`。
R9-A 的 `L1=L2=2.50 pH`、`IB=90 µA`、三颗 JJ AREA、`RJ1/RJ2`、R6-B transformer、canonical BVM、`OUT=10 Ω` 和 `dt=0.0125 ps` 全部保持。

## 2. Artifact QA
四个 raw 均 `VALID`：每个 13599 rows / 44 fields，时间 `0–169.9875 ps` 严格递增，dt 为约 `0.0125/0.025 ps`，JoSIM stderr 为空；binary 为 `v2.7.2837d13`。分析使用实际 CSV 时间轴和直接同 JJ `P/V`。

## 3. Analytic selection versus actual dynamic behavior
R10-A analytic precheck 的 calibrated static continuation 给出正向 coupled fold `216.223788 µA`，并选择 feed `214.0 µA`。预估静态 split 是 `I(BJL2)=187.97 µA`、`I(L2)=-26.03 µA`、`I(L1)=-116.03 µA`、`I(BJs)=-53.14 µA`、`I(BJL1)=62.89 µA`。这只用于选点。
实际仿真没有形成这个 settled operating point：local source ramp 后就开始 running。 `[80,90) ps` 的数值只是 running waveform 的 window median，不应称 settled OP。

| case | nominal `[80,90)` P(BJs) rad | P(BJL1) rad | P(BJL2) rad | I(BJs) µA | I(BJL1) µA | I(BJL2) µA | I(L1) µA | I(L2) µA | I(RB) µA | local feed µA |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| read1 | -197.12720 | 196.20130 | 195.72875 | -25.222 | 40.380 | 87.923 | -96.807 | -6.807 | 90.000 | 205.899 |
| read0 | -197.12625 | 196.20040 | 195.72835 | -25.240 | 40.324 | 87.845 | -96.851 | -6.851 | 90.000 | 205.900 |
| logical1-read0-control | -197.12720 | 196.20130 | 195.72875 | -25.222 | 40.380 | 87.923 | -96.807 | -6.807 | 90.000 | 205.899 |
| logical0-read0-control | -197.12625 | 196.20040 | 195.72835 | -25.240 | 40.324 | 87.845 | -96.851 | -6.851 | 90.000 | 205.900 |
这些 running-window medians 与 analytic static split 明显不同；local branch 实际约 `205.9 µA`，且 `I(V_BJL2_BIAS)` 约为 `-205.9 µA`（JoSIM voltage-source branch sign）。不能把它们当作稳定 load-line。

## 4. BJL2 phase / same-JJ voltage-area evidence
以下均为同一 BJL2、同一方向、同一 `[94,130) ps` activity window。`qualifying segment count` 是满足 phase/area 一致性的连续 segments 数，不是 event count；由于轨迹已 free-run，不能把它解释为多个合法 output events。
| case | activity range turn | largest monotonic segment turn | same-segment V-area turn | residual turn | qualifying segments | post p2p turn |
|---|---:|---:|---:|---:|---:|---:|
| read1 | 14.262288 | 2.180741 | 2.180801 | -0.00006032 | 7 | 8.067469 |
| read0 | 14.281737 | 2.181203 | 2.181258 | -0.00005545 | 7 | 8.071416 |
| logical1-read0-control | 14.279923 | 2.179977 | 2.180023 | -0.00004602 | 7 | 8.071018 |
| logical0-read0-control | 14.279859 | 2.179977 | 2.180026 | -0.00004853 | 7 | 8.071018 |
read1 的最大 segment 约 `2.180741 turn`、同段面积约 `2.180801 turn`；read0 约 `2.181203/2.181258 turn`；两个 READ=0 control 约 `2.179977/2.180023 turn` 和 `2.179977/2.180026 turn`。 phase/area consistency 证实的是连续 running 轨迹中的同 JJ 活动，不是 exactly-one。

BJL2 的 `[94,130) ps` activity range 与 `[150,170) ps` post p2p 都约 8–14 turns，四个 case 都没有 retrap 到 bounded superconducting state；这是 free-running，而不是 one-shot。

## 5. BJs/BJL1 and complete bias split
| case | BJs activity range turn | BJL1 activity range turn | BJL2 activity range turn | local-feed p2p µA | RJ1 p2p µA | RJ2 p2p µA |
|---|---:|---:|---:|---:|---:|---:|
| read1 | 15.189063 | 14.861188 | 14.262288 | 25.9767 | 50.1458 | 121.4962 |
| read0 | 15.209547 | 14.896584 | 14.281737 | 25.9134 | 49.9107 | 121.2229 |
| logical1-read0-control | 15.207430 | 14.893099 | 14.279923 | 25.8604 | 49.6181 | 120.9712 |
| logical0-read0-control | 15.207478 | 14.893099 | 14.279859 | 25.8605 | 49.6176 | 120.9715 |
BJs/BJL1 也随同一 running state 出现多圈 activity；这不是只在 BJL2 输出侧发生的受控 nonlinear gain。 `RB` 的 DC current 仍显示为 90 µA，但 L1/L2/JJ branches 动态 redistributing。

## 6. Read discrimination and canonical BVM guard
输出侧没有保持 read discrimination：BJL2 activity range 为 read1 `14.262288 turn`、read0 `14.281737 turn`、logical1 control `14.279923 turn`、logical0 control `14.279859 turn`；最大 segment 也都约 `2.18 turn`。 controls 与 read cases 同等级，故判 nonselective/free-running。
相对 R9-A matched controls 的 post-window source disturbance：
| metric | R9-A logical1 READ=0 | R10-A logical1 READ=0 | R9-A logical0 READ=0 | R10-A logical0 READ=0 |
|---|---:|---:|---:|---:|
| V(SL1) post p2p | 0.001428 | 200.512750 | 0.001428 | 200.327500 |
| V(N6|XBVM1) post p2p | 0.002868 | 84.613230 | 0.002867 | 84.793870 |
| I(L_SL|XBVM1) post p2p | 0.000119 | 15.016214 | 0.000119 | 15.020299 |
R10-A controls 的 `V(SL1)`/`V(N6)`/`I(L_SL)` post p2p 约 `200.5 µV / 84.6 µV / 15.0 µA`，而 R9-A controls 约 `0.0014 µV / 0.0029 µV / 0.000119 µA`。这直接显示 local-bias point 的 receiver-induced source loading。
R10-A read1 的绝对 JS1/JS2 phase drift 仍不能单独用作 receiver back-action，因为 canonical read1 本身约有 -3-turn running；但 R10-A controls 的 JS1/JS2 post p2p 约 `0.0171/0.0207 turn`，远高于 R9-A controls 的约 `6.6e-6/7.3e-7 turn`，与 source guard failure 一致。

## 7. Observed / Derived / Inference / Unknown
### Observed
- 四个 raw artifact 有效；local branch、source、native QB、BVM storage probes 全部存在。
- local feed ramp 后约 2–10 ps 已出现 BJL2 activity；在 read 尚未发生前，两个 READ=0 controls 也进入 running。
- `[94,130) ps` BJL2 最大同段 phase/area 约 2.18 turn，`[150,170) ps` 仍有约 8.07–8.07 turn 级 post p2p。
- read1、read0、两个 controls 的输出活动几乎相同；source/N6/SL post-window disturbance 相对 R9-A controls 显著增大。
### Derived
- `continuous phase + same-JJ voltage area` 的一致性存在，但它描述的是 repeated running segments；不支持 exactly-one output event。
- `[80,90) ps` 不能作为 settled OP：BJL2 在该窗仍有约 4.03 turn phase range。
- `RB=90 µA` 没有改变，但 local branch、L1/L2、BJs/BJL1/BJL2 的实际动态分流远离 analytic static split。
### Inference
- 该单点的主要失败模式是 **dynamic nonselective/free-running onset**，不是 read1 signal 不存在。
- 静态 coupled-fold 作为选点依据不足以保证动态稳定；startup ramp、有限源阻抗、JJ 电容/阻尼和完整 loop load-line 的瞬态共同把实际网络带入 running。具体单项因果贡献未被本单点分离。
- 该结果只 falsify 当前 `214 µA` local-feed instance；不把所有 output-side bias-routing 拓扑普遍否定。按 preregistration，不追加 local-bias sweep。
### Unknown
- 没有在本轮测试更低 feed、不同 ramp 或不同 source impedance，因此不知道是否存在 selective local-bias window。
- 没有 timestep refinement；没有 JTL/T1；没有 downstream SFQ delivery 证据。

## 8. Final disposition
Artifact status：`VALID`。Physical R10-A verdict：**`BACK_ACTION_OR_NONSELECTIVE_FAILURE`**。
当前 point 不满足 read1-only output activity、read0/control zero、retrap 或 canonical BVM source guard。停止该 local-bias single-point branch；下一设计边界按任务要求转向显式 `temporal rectification / hold` 的 BVM-specific QB redesign，不接 JTL/T1，也不做本点的追加 sweep。
