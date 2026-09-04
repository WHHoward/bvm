# HISTORICAL BVMSIM JM2-connected common-SL topology causality Quick

实验目录：`bvmsim-4bvm-paperlike-common-sl-accumulation-isolation-v1-20260904`。这是 Exploration/Quick 结果，不是论文机制证明。分析生成时间：`2026-09-04T16:54:33+08:00`。

## 1. 实验边界

固定 historical JM2-connected BVM、内部 `R_SL=12Ω`、原 BVM 参数、原 no-history stimulus、`dt=0.1 ps`；只把四个 BVM 的输出端接到共同 `COMMON_SL`，并使用一条共享的 12×500µA JJ load。没有 QB、JTL、10Ω termination，也没有调参。

`P(...)` 原始单位是 rad；本报告中的 phase turns 只表示 `continuous_unwrap(rad)/(2π)`。它们不是 SFQ event count。

## 2. Artifact / protocol

- raw artifact QA: `ARTIFACT_VALID`；十个 mask 均独立保存，所有 mask exact grid identity=`True`，无插值。
- stimulus protocol: `PROTOCOL_VALID`；每个 mask 都先 WRITE0、all-four WRITE1，再执行一次 final selective READ。
- shared-load strict local diagnostic: `VALID_DIAGNOSTIC`。

## 3. 关键观察

1. one-hot 的直接 shared-load current `I(B_COL_LOAD01)` 在四个位置的 READ RMS 范围为 `17.3836–17.3836 uA`，位置 spread 为 `0 uA`。这只描述位置依赖，不预设其是否足够小。
2. inactive BVM 相对于同一 stored-1111 的 `0000` 控制出现的最大 READ 差分：RSL `20.4954 uA`，LSL `20.4954 uA`，RS `5.24037 uA`，LS3 `10.9206 uA`，JS1 phase `0.122569 turns`，JS2 phase `0.107618 turns`。这是当前 common-SL fixture 中的 observed cross-coupling/back-action evidence。
3. common current 的 multi-active superposition residual（最大 READ residual across forward/reverse masks）为 `104.687 uA`；没有预设 5%/10% threshold。
4. shared 12-JJ load 的 strict local event diagnostic 未发现 complete event；`assumption_violated=False`。因此当前报告。

## 4. 受限物理含义

在本固定网络和本十个 mask 内，active BVM 对 common SL 的响应、inactive BVM 的 back-action 和多 active 的非加性应分别作为 topology-caused observed evidence 报告；它们不能被提升为独立 unit-current、普适 RSL isolation 或论文机制身份。

旧 distributed fixture 只作为 read-only context；由于旧网络没有 `I(B_COL_LOAD01)` 这一直接 shared-load authority，old/new 对照不被写成同一测量量的等价替换。

## 5. 不证明什么

本轮不证明 canonical BVM、QB/JTL 接收、SFQ 传输、硬件行为、工艺裕量、参数最优性、timestep convergence、论文机制身份或任意其它未测 mask。相位累计、voltage area、I>Ic 或局部 activity 都没有被用作 SFQ 计数。

## 6. 当前状态

`COMMON_SL_TOPOLOGY_QUICK_ANALYSIS_COMPLETE`；primary interpretation 保持 bounded/descriptive，等待用户审阅。shared-load assumption 若违反则本报告只保留原始和诊断结果，不解释 linear accumulation。

## 7. 下一步选项（不自动执行）

1. 用户审阅本轮 topology evidence；2. 若确有必要，另行授权针对 load switching 的独立诊断；3. 另行授权才讨论 QB/JTL 接入。
