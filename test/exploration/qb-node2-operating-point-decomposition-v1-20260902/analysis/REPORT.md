# QB_NODE2_OPERATING_POINT_DECOMPOSITION_V1：分析报告

## 1. 范围、权限与问题

本报告对应 `QB_NODE2_OPERATING_POINT_DECOMPOSITION_V1`，日期目录为 `qb-node2-operating-point-decomposition-v1-20260902`。它是 Exploration 级、`EXISTING_RAW_ONLY`、analysis-only 工作：不运行新 JoSIM，不修改电路或参数，不改写历史 raw。

问题限定为：在 13 ps、12×320 µA、`logical1/read`、scaled QB 条件下，比较 grounded source G、ideal current replay I0 与 physical BVM→12×320 JSL→QB P0，观察 QB 输入、node2、node3、node4 的轨迹差异最先出现在哪里。Q45/Q68 只作为历史 supporting scalar reference。

上一轮 `BVM_QB_LIN_REMOVAL_MATCHED_PAIR_QUICK_V1` 已由用户 review，结果为 `QUICK_NO_EFFECT`；用户只授权本次 existing-raw 分析，没有授权 BJs、bias、sweep、promotion、Formal Gate 或 magnetic coupling continuation。

## 2. 数据与 provenance

### 2.1 主要 raw

| case | 物理含义 | raw SHA-256 |
|---|---|---|
| G | BVM→12×320 JSL→ground source reference | `b92056235a06f86fdbc55b670656aecab834ab728d4fc44ba128ca0a30a809de` |
| I0 | G 的冻结源波形 replay 到 scaled QB | `be7e0403586b8819a9f4d7e4f4400af90e640b281b7a3ae4e1331d351c866d4c` |
| P0 | BVM→12×320 JSL→scaled QB physical connection | `9aecc3f626148737bbd14e8cdb42a546002d7b2f268cc39badc430647c877d66` |

路径、deck、sidecar 和 SHA-256 的完整记录在 [provenance.json](provenance.json)。G/I0/P0 各有 13,599 个样本，时间范围 `0–169.9875 ps`；实际 CSV 网格非均匀，`dt_min≈0.0125 ps`、`dt_max=0.025 ps`。I0/P0 的比较使用共同 exact grid，不插值。

### 2.2 supporting Q45/Q68

Q45 raw SHA-256 为 `cc702632dad106f324004dd429dd94e9a4ad38d0cda300671c29b4ea76865517`，Q68 为 `0b3fab3ba7357d2475ffadb174f0d48ad33b7e7c934962a687074d4739468bdb`。两者的 manifest、deck input semantics、35 µA bias、10 Ω load、scaled QB/JJ model 和 raw hash registration 均通过检查；但 authority 固定为 `HISTORICAL_SUPPORTING_REFERENCE`。原因是它们来自 standalone、0.1 ps 历史 fixture，并使用未冻结的局部诊断规则。本报告不做 Q45/Q68 与 G/I0/P0 的 pointwise 对齐、插值或阈值拟合。

旧的 `qb-ideal-physical-internal-trajectory-audit-v1-20260825` 只作为历史动机，不作为本报告 authority；其边界包括 `D12 RUN_INPUT_HASH_MISMATCH` 和 replay-source semantic limitation。

### 2.3 模型与运行边界

- 原 V1 分析基线 HEAD：`853a722feaa047bafdc82eb6b6f3c0faa0c432e4`；本 corrective patch 的 `HEAD BEFORE PATCH` 为 `c5fe0d4`（完整提交哈希见交付说明）。
- 记录的 solver：`build/josim-cli` v`2.7.2837d13`，hash `48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2`；本次没有调用。
- QB snapshot 的原始 hash 为 `5ee4e8f054a9a49aea7e48493b20ef3d794db01b2902f15a439b0ea31f2276a2`，语义 netlist hash 为 `b026981dbed5b8772ba3f928597d1b0750f133246763ba997caff3094c613063`。
- `bvm_cell.cir` hash 为 `ea7346546bef091dc2efa39ab6f0abcfa54f833aeeabb909dcf3815cdaea42a4`；`jjmit.cir` hash 为 `19862d1fd1f1f44dfa1523848d7d3b5e2594a6c5da8fdd80144b449e5312a336`。
- 指标规范 `docs/research/METRIC_SPEC_V2.md` hash 为 `f88a36f4d310b2572efdc7408d734640f25dd5aea2246b74fbb8b7bb7f0be470`。

## 3. QB 拓扑、方向与 KCL

范围修正：本报告的 QB KCL 结论只针对 I0 和 P0；G 仅作为 grounded-source reference，不作为 QB KCL case。

实际 QB snapshot 的 branch orientation 是：

```text
Lin  IN -> 1       BJs  1 -> 2       BJL1 2 -> 0       RJ1 2 -> 0
L1   2 -> 3        RB   IB -> 3      L2   3 -> 4       BJL2 4 -> 0
RJ2  4 -> 0        L0   4 -> OUT
```

所以使用：

```text
input: I(Lin) - I(BJs) = 0
node2: I(BJs) - I(BJL1) - I(RJ1) - I(L1) = 0
node3: I(L1) + I(RB) - I(L2) = 0
node4: I(L2) - I(BJL2) - I(RJ2) - I(L0) = 0
```

电流单位为 µA。I0 和 P0 满足 QB input/node2/node3/node4 KCL；G 仅用于 grounded-source reference，不作为 QB KCL case。KCL 检查阈值为 `0.001 µA`，对 I0/P0 的 W2 `[80,90) ps`、W3 `[95,110) ps`、W4 `[110,130) ps` 报告 max absolute、p95 absolute 和 RMS residual。结果全部 `KCL_CONSISTENT`；input node 最大残差为 0（P0 局部最高 `1×10^-9 µA`），其余节点最大残差也只有约 `10^-5–5×10^-5 µA`。

代表性残差如下，完整值见 `metrics.json`：

| case/window | node2 max/p95/RMS (µA) | node3 max/p95/RMS (µA) | node4 max/p95/RMS (µA) |
|---|---:|---:|---:|
| I0/W2 | 9.591e-6 / 7.554e-6 / 4.107e-6 | 6.776e-15 / 6.776e-15 / 3.382e-15 | 9.642e-6 / 7.661e-6 / 3.919e-6 |
| I0/W3 | 1.000e-5 / 8.000e-6 / 3.901e-6 | 5.000e-5 / 5.000e-6 / 7.093e-6 | 6.000e-5 / 1.000e-5 / 8.500e-6 |
| I0/W4 | 1.000e-5 / 7.000e-6 / 3.648e-6 | 5.000e-6 / 4.000e-6 / 1.793e-6 | 1.000e-5 / 7.905e-6 / 4.110e-6 |
| P0/W2 | 9.479e-6 / 7.576e-6 / 4.030e-6 | 6.776e-15 / 6.776e-15 / 3.517e-15 | 9.485e-6 / 7.573e-6 / 4.000e-6 |
| P0/W3 | 1.000e-5 / 9.000e-6 / 4.524e-6 | 5.000e-6 / 4.000e-6 / 1.958e-6 | 1.200e-5 / 8.000e-6 / 4.287e-6 |
| P0/W4 | 1.000e-5 / 8.000e-6 / 3.994e-6 | 5.000e-6 / 4.000e-6 / 1.248e-6 | 1.000e-5 / 7.900e-6 / 4.040e-6 |

说明：旧版本此处的“每个 case”是历史文字；corrective metrics 已按要求只对 I0/P0 计算 QB KCL，G 不参与 QB KCL 判定。

## 4. W2 operating point：read 前稳定状态

W2 的代表性均值（µA）如下；median 同时保存在 `metrics.json`。

| branch | I0 mean | P0 mean |
|---|---:|---:|
| BJs | +0.000929 | −0.000640 |
| BJL1 | 15.120332 | 15.121542 |
| RJ1 | +0.000595 | −0.000453 |
| L1 | −15.119998 | −15.121729 |
| RB | 35.000000 | 35.000000 |
| L2 | 19.880002 | 19.878271 |
| BJL2 | 19.878611 | 19.878043 |
| RJ2 | +0.000534 | +0.000019 |
| L0 | +0.000857 | +0.000209 |

node2 以 BJs mean 为分母会接近零，因此 I0/P0 的 node2 fractions 均标记为 `NOT_DEFINED_NEAR_ZERO_DENOMINATOR`，没有强行归一化。node3 则稳定满足：

| case | L1/L2 | RB/L2 | signed sum | 描述 |
|---|---:|---:|---:|---|
| I0 | −0.760563 | 1.760563 | 1.000000 | `L1_opposes_RB` |
| P0 | −0.760717 | 1.760717 | 1.000000 | `L1_opposes_RB` |

这说明固定 bias branch `RB≈35 µA`，而按实际方向 L1 是 node3 中抵消 RB 的项；这只是 operating-point decomposition，不是机制唯一性证明。

## 5. W3：BJs 与 node2 分支

W3 为 `[95,110) ps`。以下电流单位为 µA，signed integral 和正/负面积单位为 µA·ps；min/max 是当前窗口中的最大 excursion。

### I0

| branch | mean / median | RMS | min / max | p2p | signed area | + / − area | zero crossings |
|---|---:|---:|---:|---:|---:|---:|---:|
| BJs | 47.556 / 48.601 | 50.614 | 0.002 / 79.067 | 79.065 | 713.088 | 713.088 / 0 | 0 |
| BJL1 | 21.350 / 23.292 | 30.461 | −53.362 / 51.926 | 105.288 | 319.960 | 361.846 / −41.886 | 4 |
| RJ1 | 5.213 / 4.391 | 8.231 | −8.102 / 22.533 | 30.636 | 78.251 | 87.092 / −8.841 | 7 |
| L1 | 20.992 / 17.539 | 29.879 | −15.130 / 77.707 | 92.837 | 314.876 | 333.493 / −18.617 | 3 |

I0 的 L1 正/负 occupancy 为 `0.809/0.191`。RJ1 的均方电流对应的 33 Ω 支路耗散 proxy 为 mean power `2.236×10^-9 W`、energy `3.3525×10^-5 fJ`；这不是 QB 总功率。

### P0

| branch | mean / median | RMS | min / max | p2p | signed area | + / − area | zero crossings |
|---|---:|---:|---:|---:|---:|---:|---:|
| BJs | 30.945 / 36.555 | 36.887 | −10.382 / 68.145 | 78.528 | 464.125 | 471.940 / −7.816 | 6 |
| BJL1 | 29.370 / 29.144 | 31.303 | 4.048 / 49.856 | 45.807 | 440.301 | 440.301 / 0 | 0 |
| RJ1 | −0.027 / 1.300 | 4.201 | −14.243 / 6.517 | 20.760 | −0.412 | 25.067 / −25.478 | 10 |
| L1 | 1.603 / 3.643 | 12.979 | −22.888 / 24.327 | 47.215 | 24.236 | 96.829 / −72.594 | 6 |

P0 的 L1 正/负 occupancy 为 `0.590/0.410`。RJ1 耗散 proxy 为 mean power `5.823×10^-10 W`、energy `8.7346×10^-6 fJ`。

### 相位与 node2 signature

phase 原始输出是 JoSIM radians；报告中的 turns 来自连续 unwrap 后的 phase difference `/ (2π)`。W3 phase p2p/endpoint（turns）为：

| signal | I0 p2p / endpoint | P0 p2p / endpoint |
|---|---:|---:|
| P(BJs) | 8.394370 / 8.394369 | 2.776583 / 2.776583 |
| P(BJL1) | 1.287247 / 1.248792 | 0.278799 / −0.006563 |
| P(BJL2) | 1.131939 / 1.131936 | 0.133621 / −0.001117 |

因此，P0 的 BJs 支路仍然局部 active，但其 node2 BJL1/L1 partition 轨迹与 I0 不同；不把这些 phase turns 直接解释为 SFQ counts。

I0 与 P0 的 W3 exact-grid difference 摘要：BJs current RMS difference `28.473 µA`、max `84.594 µA`；BJL1 `25.423/93.762 µA`；L1 `28.375/69.788 µA`；BJL2 `25.161/92.444 µA`。RB 的差异为 0，相关系数为 1。

## 6. node3：稳定 bias 与下游响应

node3 的 KCL 在 I0/P0 中都成立，RB 在 W2/W3 均为 35 µA。I0↔P0 W3 exact-grid 差异为：

| signal | RMS diff (µA) | p95 abs diff (µA) | max abs diff (µA) | correlation |
|---|---:|---:|---:|---:|
| I(L1) | 28.375 | 56.859 | 69.788 | 0.3446 |
| I(RB) | 0 | 0 | 0 | 1.0000 |
| I(L2) | 28.375 | 56.859 | 69.788 | 0.3446 |

按 `I(L1)+I(RB)-I(L2)=0`，L2 的改变是 L1 改变在固定 RB 下的直接 node3 balance 响应。这个观察支持“node2 partition → node3 trajectory follows”的描述，但不说明 node2 是唯一物理根因。

## 7. node4 与 strict local anchor

### 7.1 node4 current summary

下表为 mean / RMS / p2p（µA）：

| window/case | BJL2 | L2 | RJ2 | L0 |
|---|---:|---:|---:|---:|
| W3 I0 | 36.624 / 37.867 / 34.836 | 36.603 / 38.803 / 47.215 | −0.007 / 2.629 / 11.939 | −0.014 / 5.658 / 25.362 |
| W3 P0 | 33.375 / 42.167 / 118.230 | 55.992 / 59.893 / 92.837 | 7.094 / 12.581 / 44.469 | 15.523 / 27.460 / 95.911 |
| W4 I0 | 25.195 / 26.468 / 30.603 | 23.295 / 24.762 / 42.781 | −0.611 / 2.344 / 9.169 | −1.289 / 5.033 / 19.910 |
| W4 P0 | 17.503 / 17.809 / 16.658 | 17.471 / 18.211 / 24.369 | −0.015 / 1.302 / 5.843 | −0.017 / 2.728 / 12.291 |

### 7.2 严格 local arithmetic

严格窗口为 activity `[95,115) ps`、post `[115,130) ps`、tail `[125,130) ps`，phase/area 只针对同一 `BJL2`、同一 run、同一方向。I0 锚点结果：

- segment：`103.0375–110.175 ps`。
- phase difference：`1.0160289228944646 turns`。
- `∫Vdt/Φ0`：`1.0160368344325381 Φ0`。
- residual：`7.91×10^-6 turns`；post phase range `0.06553 turns`，tail p2p `0.01944 turns`。
- local compatibility：`CLEAN_ONE_SFQ_CANDIDATE`。

P0 最大局部 segment 为约 `106.525–109.6875 ps`，phase `−0.1221278 turns`、area `−0.1221310 Φ0`，因此为 `SUBTHRESHOLD`；post phase range `0.03649 turns`，tail p2p `0.01307 turns`。

这组严格结果的 claim ceiling 是 same-JJ local phase/area compatibility。它不表示 event count、SFQ delivery、JTL reception、system Gate 或 hardware behavior。

## 8. I0/P0 first-divergence：corrective reanalysis

旧的 result-dependent 10% 规则保留在 `metrics.json` 的 `legacy_relative_final_amplitude_onset`，仅作 sensitivity view。它不能建立 temporal order，因为 current threshold 使用了 READ 结果自身的 final amplitude。主方法为 `PRE_NOISE_REFERENCED_ONSET`：W2 `[80,90) ps` 是唯一 threshold reference；current threshold=`max(current floor, 5×PRE W2 p99(abs(I0−P0)))`，phase threshold 同理，partition 使用固定 `0.10` absolute fraction，并在除法前应用 `5 µA` denominator floor。ACTIVE/READ 响应不参与阈值估计。

时间网格非均匀，`dt_min≈0.0125 ps`、`dt_max≈0.025 ps`；`0.0125 ps` 只标作 `MINIMUM_OBSERVED_SAMPLE_SPACING`，不是 universal resolution。主 persistence 采用“实际采样跨度至少 `0.025 ps` 或 3 个连续样本”，每个 crossing 在 `metrics.json` 中记录实际跨度；另列 1-sample、3-sample 和 `0.0125/0.025 ps` tie sensitivity。

主配置（current floor `1 µA`、phase floor `0.05 turns`、time-aware persistence、tie `0.025 ps`）的首层为 input/BJs `95.075 ps`，node2 `95.0875 ps`；三者在 `0.025 ps` tie tolerance 下同属首组。因此主配置的 implied ordering 是 `COUPLED_INPUT_BJS_NODE2`，不是 node2-only。

固定 robustness matrix 共 24 个配置；下表逐项列出 first time/layer、首个 tie group 和 implied classification。`C`=`COUPLED_INPUT_BJS_NODE2`，`I`=`INPUT_BJS_LIMITATION_SUPPORTED`。

| current floor | phase floor | persistence | tie (ps) | first time/layer | first tie group | implied |
|---:|---:|---|---:|---|---|---|
| 1 | 0.05 | 1 sample | 0.0125 | 95.075 / L0,L1 | L0,L1,L2 | C |
| 1 | 0.05 | 1 sample | 0.025 | 95.075 / L0,L1 | L0,L1,L2 | C |
| 1 | 0.05 | 3 samples | 0.0125 | 95.075 / L0,L1 | L0,L1,L2 | C |
| 1 | 0.05 | 3 samples | 0.025 | 95.075 / L0,L1 | L0,L1,L2 | C |
| 1 | 0.05 | time-aware primary | 0.0125 | 95.075 / L0,L1 | L0,L1,L2 | C |
| 1 | 0.05 | time-aware primary | 0.025 | 95.075 / L0,L1 | L0,L1,L2 | C |
| 1 | 0.10 | 1 sample | 0.0125 | 95.075 / L0,L1 | L0,L1,L2 | C |
| 1 | 0.10 | 1 sample | 0.025 | 95.075 / L0,L1 | L0,L1,L2 | C |
| 1 | 0.10 | 3 samples | 0.0125 | 95.075 / L0,L1 | L0,L1,L2 | C |
| 1 | 0.10 | 3 samples | 0.025 | 95.075 / L0,L1 | L0,L1,L2 | C |
| 1 | 0.10 | time-aware primary | 0.0125 | 95.075 / L0,L1 | L0,L1,L2 | C |
| 1 | 0.10 | time-aware primary | 0.025 | 95.075 / L0,L1 | L0,L1,L2 | C |
| 2 | 0.05 | 1 sample | 0.0125 | 95.25 / L0,L1 | L0,L1 | I |
| 2 | 0.05 | 1 sample | 0.025 | 95.25 / L0,L1 | L0,L1 | I |
| 2 | 0.05 | 3 samples | 0.0125 | 95.25 / L0,L1 | L0,L1 | I |
| 2 | 0.05 | 3 samples | 0.025 | 95.25 / L0,L1 | L0,L1 | I |
| 2 | 0.05 | time-aware primary | 0.0125 | 95.25 / L0,L1 | L0,L1 | I |
| 2 | 0.05 | time-aware primary | 0.025 | 95.25 / L0,L1 | L0,L1 | I |
| 2 | 0.10 | 1 sample | 0.0125 | 95.25 / L0,L1 | L0,L1 | I |
| 2 | 0.10 | 1 sample | 0.025 | 95.25 / L0,L1 | L0,L1 | I |
| 2 | 0.10 | 3 samples | 0.0125 | 95.25 / L0,L1 | L0,L1 | I |
| 2 | 0.10 | 3 samples | 0.025 | 95.25 / L0,L1 | L0,L1 | I |
| 2 | 0.10 | time-aware primary | 0.0125 | 95.25 / L0,L1 | L0,L1 | I |
| 2 | 0.10 | time-aware primary | 0.025 | 95.25 / L0,L1 | L0,L1 | I |

因此 robustness summary=`MIXED`（12 C、12 I），不能把“node2 是稳健最早层”作为结论。该 ordering 仍是 descriptive only，不是 causal proof。

## 9. G→I0 replay closure

G 的源 branch（`I(B_LD1)`/`I(B_LD12)`/`I(L_SL)`）与 I0 的 replay input `I(I_REPLAY)` 在 full exact grid 上一致：max difference `5.094×10^-20 A`、RMS `4.368×10^-22 A`，W3 差异为 0。该结果验证 replay wrapper 的数值重放关系，不等于物理接收或 system closure。

## 10. Q45/Q68 scalar supporting reference

Q45/Q68 每个 pulse 独立计算 scalar；不和 G/I0/P0 做 pointwise comparison。以 110 ps pulse 为例：

| scalar | Q45 | Q68 |
|---|---:|---:|
| BJL1 phase endpoint/p2p (turns) | ≈0 | ≈+1.000 |
| BJL2 phase endpoint/p2p (turns) | ≈0 | ≈+1.000 |
| L1 mean / RMS (µA) | −9.543 / 14.248 | −0.902 / 27.710 |
| L2 mean / RMS (µA) | 25.457 / 27.567 | 34.098 / 43.929 |
| RB mean (µA) | 35 | 35 |
| BJL2 largest local raw segment phase / area (turns) | −0.09215 / −0.09234 | +1.09601 / +1.09652 |

两者都标记为局部诊断 `INCONCLUSIVE`，且只保留 `HISTORICAL_SUPPORTING_REFERENCE` authority。这里展示的是历史 scalar signature，不是 universal threshold，也不是对 P0/I0 的插值参照。

## 11. 结果分类与边界

允许的分类中，旧结果为 `NODE2_REDISTRIBUTION_SUPPORTED`；corrective reanalysis 后为：

`COUPLED_INPUT_BJS_NODE2`

理由是：BJs 在 P0 中有局部活动，node2/downstream difference observation 成立，但 PRE-noise robustness matrix 同时出现 input/BJs 首组和 input/BJs+node2 tie，summary=`MIXED`。因此只能保留 coupled exploratory description，`mechanism_disposition=EXPLORATORY`，`causal_order=NOT_PROVEN`，不是 accepted scientific authority。

独立强观察：`NODE2_REDISTRIBUTION_DIFFERENCE_OBSERVED=true`。BJL1 current/phase、L1 separation、稳定 RB、L2 downstream separation 以及 I0 clean/P0 subthreshold 的 BJL2 local contrast 均成立；这不依赖 first-divergence 顺序。

### Observed

原始 current/phase/voltage 轨迹、KCL residual、G→I0 replay exact-grid closure、I0/P0 exact-grid differences 和 Q45/Q68 scalar。

### Derived

由实际 netlist branch orientation 得到的 KCL；非均匀网格上的 trapezoidal signed/positive/negative integrals；phase unwrap 后的 turns；strict local same-JJ phase/area arithmetic；PRE-noise threshold 与 persistence matrix 的 first-divergence 时间。

### Inference

本组条件下，RB 保持 35 µA，node3 随 L1/L2 改变；node2/downstream difference 是明确观察，但 onset robustness MIXED，不能将 node2 写成稳健的最早层或唯一原因。

### Unknown

唯一根因、BJs limitation 的必要性、最佳 bias/Ic、真正 SFQ event count、JTL downstream reception、timestep convergence、硬件行为以及论文拓扑是否完全对应。

## 12. 不声明与停止

本报告不证明：唯一 root cause、最佳参数、论文 Fig.7 topology、Formal BVM→QB Gate、JTL/T1 delivery、hardware behavior、universal impossibility 或 SFQ count。

本 corrective patch 不执行 follow-up。当前状态为 `AWAITING_USER_REVIEW / STOP`。
