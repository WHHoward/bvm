# JTL_TRANSPORT_GATE_V1 — existing-evidence reconciliation

parent accepted HEAD: `edf9b6d6c9a26c999a9f95f8ca604993475c51d4`  
本报告只重算既有 CSV；没有 JoSIM execution、没有 topology/parameter change。
`P(...)` raw unit 是 rad；所有 turns 为同一窗口 `ΔP/(2π)`。未使用 `fast_events`。

## 1. Gate definition

Strict local event 与 settled-well transport evidence 分开。transport gate 要求每颗 JJ 的 pre/post bounded、+1 adjacent-well、activity phase/area 一致、无 +2 或额外 post event，并满足四级因果 onset 顺序。

Provisional retrospective tolerances: one-well `±0.02 turn`; phase/area residual `≤2e-4 turn`; pre p2p `≤0.01`; post p2p `≤0.07`; onset marker `t50` at `+0.5 turn`; onset order slack `0.5 ps`。这些值来自本批 accepted references，但不是 global Authority freeze，详见 `../PREREGISTRATION.md`。

## 2. Case-level disposition

| fixture | strict local vector (B1/B2/B1/B2) | transport vector | onset order (ps) | verdict |
|---|---|---|---|---|
| R11-positive-control | `[1, 0, 0, 0]` | `['1', '1', '1', '1']` | `12.75, 14.4, 16.2125, 18.5125` | **JTL_TRANSPORT_REFERENCE_PASS** |
| M1-ideal-replay | `[1, 0, 0, 0]` | `['1', '1', '1', '1']` | `15.8, 17.4, 19.3, 21.5` | **JTL_TRANSPORT_PASS_COUNTERFACTUAL** |
| M5-positive-control | `[1, 1, 0, 0]` | `['0', '0', '0', '0']` | `12.2, 13.5875, 15.1625, 17.4125` | **MULTI_WELL_TRANSPORT_NOT_ONE_TURN** |
| pulse5-original | `[1, 0, 0, 0]` | `['1', '1', '1', '1']` | `215.9, 217.562, 219.425, 221.725` | **JTL_TRANSPORT_PASS_COUNTERFACTUAL** |
| pulse5-reverse | `[0, 0, 0, 0]` | `['0', '0', '0', '0']` | `—, —, —, —` | **REVERSE_POLARITY_NOT_A_ONE_WELL_TRANSPORT_EVENT** |

## 3. Per-JJ strict and settled-well evidence

`largest segment` 是 strict local candidate；`pre→post`、full-window phase/area 是独立 transport evidence。

| fixture | JJ | largest strict turn / area | full phase / area | pre median / p2p / Vrms | post median / p2p / Vrms | pre→post mean / median | full phase-area residual | post extra events |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| R11-positive-control | `P(B1|XJTL1)` | 1.02733 / 1.02739 | 1.00488 / 1.00488 | 0.119043 / 0.00295864 / 3.69926 | 1.12325 / 0.00443708 / 3.5348 | 1.00405 / 1.00421 (n=1) | -7.06e-07 | 0 |
| R11-positive-control | `P(B2|XJTL1)` | 0.92721 / 0.927254 | 1.00371 / 1.00371 | 0.120675 / 0.00277444 / 7.02042 | 1.12348 / 0.00411829 / 3.50519 | 1.0027 / 1.00281 (n=1) | -2.929e-07 | 0 |
| R11-positive-control | `P(B1|XJTL2)` | 0.923721 / 0.923761 | 1.00319 / 1.00319 | 0.118223 / 0.00271372 / 7.1841 | 1.12327 / 0.00705518 / 5.61473 | 1.0048 / 1.00505 (n=1) | -2.857e-07 | 0 |
| R11-positive-control | `P(B2|XJTL2)` | 0.869682 / 0.86971 | 1.00413 / 1.00413 | 0.108776 / 0.00626138 / 6.93909 | 1.12344 / 0.0081056 / 5.77422 | 1.01348 / 1.01466 (n=1) | 7.233e-07 | 0 |
| M1-ideal-replay | `P(B1|XJTL1)` | 1.07462 / 1.07908 | 1.00184 / 1.00203 | 0.0911453 / 0.000904891 / 1.89716 | 1.09152 / 0.00740946 / 10.8216 | 1.00033 / 1.00038 (n=1) | -0.0001912 | 0 |
| M1-ideal-replay | `P(B2|XJTL1)` | 0.929944 / 0.932699 | 1.0017 / 1.0017 | 0.113477 / 0.00259458 / 5.41551 | 1.11487 / 0.0239622 / 18.7368 | 1.00159 / 1.00139 (n=1) | -2.223e-06 | 0 |
| M1-ideal-replay | `P(B1|XJTL2)` | 0.914721 / 0.917261 | 0.996874 / 0.996852 | 0.116496 / 0.00307721 / 8.23358 | 1.1208 / 0.0213772 / 16.0412 | 1.00374 / 1.0043 (n=1) | 2.263e-05 | 0 |
| M1-ideal-replay | `P(B2|XJTL2)` | 0.867192 / 0.868925 | 1.0002 / 1.0002 | 0.108497 / 0.00545626 / 6.67218 | 1.12244 / 0.0127386 / 7.84779 | 1.01234 / 1.01394 (n=1) | 7.192e-07 | 0 |
| M5-positive-control | `P(B1|XJTL1)` | 1.26042 / 1.26045 | 2.01222 / 2.01222 | 0.101158 / 0.00613969 / 7.06449 | 2.12202 / 0.0379967 / 36.2557 | 2.01739 / 2.02086 (n=2) | -3.755e-06 | 0 |
| M5-positive-control | `P(B2|XJTL1)` | 1.06427 / 1.06434 | 1.97663 / 1.97663 | 0.115751 / 0.00271491 / 7.33428 | 2.12297 / 0.0445554 / 30.8638 | 2.00591 / 2.00722 (n=2) | 7.109e-06 | 0 |
| M5-positive-control | `P(B1|XJTL2)` | 0.985369 / 0.985431 | 2.01169 / 2.0117 | 0.116929 / 0.0027603 / 7.29859 | 2.12288 / 0.0380874 / 34.9097 | 2.00431 / 2.00595 (n=2) | -7.252e-06 | 0 |
| M5-positive-control | `P(B2|XJTL2)` | 0.893874 / 0.893908 | 1.95277 / 1.95276 | 0.10842 / 0.00622708 / 6.90353 | 2.12249 / 0.0657819 / 41.9293 | 2.0082 / 2.01407 (n=2) | 7.315e-06 | 0 |
| pulse5-original | `P(B1|XJTL1)` | 1.07619 / 1.07626 | 0.99294 / 0.992938 | 0.0717653 / 0 / 1.15194e-11 | 1.07177 / 0.0178815 / 21.2575 | 1.00006 / 1.00001 (n=1) | 2.605e-06 | 0 |
| pulse5-original | `P(B2|XJTL1)` | 0.927474 / 0.927512 | 1.01275 / 1.01275 | 0.109491 / 0 / 8.11508e-12 | 1.10946 / 0.0237481 / 16.1998 | 0.99994 / 0.999964 (n=1) | -4.565e-06 | 0 |
| pulse5-original | `P(B1|XJTL2)` | 0.921813 / 0.921853 | 0.985742 / 0.985739 | 0.119398 / 0 / 3.47311e-12 | 1.1193 / 0.0216389 / 14.563 | 0.999528 / 0.999898 (n=1) | 3.407e-06 | 0 |
| pulse5-original | `P(B2|XJTL2)` | 0.859426 / 0.859455 | 0.983071 / 0.983069 | 0.122224 / 0 / 5.43175e-12 | 1.12197 / 0.0174377 / 9.38 | 0.998385 / 0.999744 (n=1) | 1.786e-06 | 0 |
| pulse5-reverse | `P(B1|XJTL1)` | -0.876683 / -0.876697 | -0.845557 / -0.845557 | 0.0717653 / 0 / 1.15194e-11 | -0.775223 / 0.0027346 / 1.77664 | -0.847001 / -0.846988 (n=-1) | -2.112e-07 | 0 |
| pulse5-reverse | `P(B2|XJTL1)` | -0.16474 / -0.164743 | -0.161104 / -0.161104 | 0.109491 / 0 / 8.11508e-12 | -0.05197 / 0.000661973 / 0.464012 | -0.161462 / -0.161461 (n=0) | -4.53e-08 | 0 |
| pulse5-reverse | `P(B1|XJTL2)` | -0.0426023 / -0.0426028 | -0.0432411 / -0.043241 | 0.119398 / 0 / 3.47311e-12 | 0.0759947 / 0.000294071 / 0.30625 | -0.0434035 / -0.0434037 (n=0) | -3.488e-08 | 0 |
| pulse5-reverse | `P(B2|XJTL2)` | -0.0112327 / -0.0112328 | -0.0145345 / -0.0145345 | 0.122224 / 0 / 5.43175e-12 | 0.107641 / 0.000455072 / 0.361871 | -0.0145683 / -0.014583 (n=0) | 1.588e-08 | 0 |

## 4. Explicit transport checks

| fixture | JJ | pre | post | one well | full one well | phase/area | t50 | no post event | JJ transport |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| R11-positive-control | `P(B1|XJTL1)` | Y | Y | Y | Y | Y | Y | Y | Y |
| R11-positive-control | `P(B2|XJTL1)` | Y | Y | Y | Y | Y | Y | Y | Y |
| R11-positive-control | `P(B1|XJTL2)` | Y | Y | Y | Y | Y | Y | Y | Y |
| R11-positive-control | `P(B2|XJTL2)` | Y | Y | Y | Y | Y | Y | Y | Y |
| M1-ideal-replay | `P(B1|XJTL1)` | Y | Y | Y | Y | Y | Y | Y | Y |
| M1-ideal-replay | `P(B2|XJTL1)` | Y | Y | Y | Y | Y | Y | Y | Y |
| M1-ideal-replay | `P(B1|XJTL2)` | Y | Y | Y | Y | Y | Y | Y | Y |
| M1-ideal-replay | `P(B2|XJTL2)` | Y | Y | Y | Y | Y | Y | Y | Y |
| M5-positive-control | `P(B1|XJTL1)` | Y | Y | N | N | Y | Y | Y | N |
| M5-positive-control | `P(B2|XJTL1)` | Y | Y | N | N | Y | Y | Y | N |
| M5-positive-control | `P(B1|XJTL2)` | Y | Y | N | N | Y | Y | Y | N |
| M5-positive-control | `P(B2|XJTL2)` | Y | Y | N | N | Y | Y | Y | N |
| pulse5-original | `P(B1|XJTL1)` | Y | Y | Y | Y | Y | Y | Y | Y |
| pulse5-original | `P(B2|XJTL1)` | Y | Y | Y | Y | Y | Y | Y | Y |
| pulse5-original | `P(B1|XJTL2)` | Y | Y | Y | Y | Y | Y | Y | Y |
| pulse5-original | `P(B2|XJTL2)` | Y | Y | Y | Y | Y | Y | Y | Y |
| pulse5-reverse | `P(B1|XJTL1)` | Y | Y | N | N | Y | N | Y | N |
| pulse5-reverse | `P(B2|XJTL1)` | Y | Y | N | N | Y | N | Y | N |
| pulse5-reverse | `P(B1|XJTL2)` | Y | Y | N | N | Y | N | Y | N |
| pulse5-reverse | `P(B2|XJTL2)` | Y | Y | N | N | Y | N | Y | N |

## 5. Observed

- R11 standard-JTL positive control：四颗 JJ 的 full-window phase/area 与 mean pre→post 都支持 +1 adjacent well；strict largest monotonic segment 只有第一颗超过 1 turn。
- M1 ideal Q0 replay：同样通过四颗 JJ 的 settled-well transport 条件，但它是 ideal voltage replay；strict vector 仍为 `[1,0,0,0]`。
- pulse-5 original：四颗 JJ 的 transport vector 与 R11 相同，onset 顺序为正向逐级延迟；strict vector 仍为 `[1,0,0,0]`。
- pulse-5 reverse：方向相反且下游幅度快速衰减，不能满足预期 +1 one-well transport；它不是 logical0 control。
- M5-PC：四颗 JJ 的 full-window/pre→post 都约为 +2 wells；旧的 `abs(turns)>=0.90` 规则因此不能表达 exactly-one。

## 6. Derived

- R11 与 pulse-5 original 在本批 provisional gate 的离散 transport signature（四颗 +1、bounded、phase/area residual、t50 order）一致；这支持“在 task-local transport-signature 层面落入同一类”，不表示波形或物理接口相同。
- M1 与 pulse-5 original 也通过同一 ideal-replay transport gate，但仍不能据此证明 physical Q0→JTL coupling。
- `full-window≈1 turn` 不会回写或升级 strict local-event vector。

## 7. Inference

- 原极性 Q0 pulse 对冻结 standard JTL 的理想 replay具备可重复的 +1-well、逐级 transport-compatible response；反极性则不具备该方向的 one-well chain response。
- 若后续要解释 physical Q0→JTL failure，下一层问题仍是 impedance/loading isolation；本 checkpoint 本身不选择 transformer 或 matching topology。

## 8. Unknown / boundary

- 没有新的 physical QB→JTL coupling、canonical BVM→JTL、T1 或 timestep convergence run。
- transport gate 是针对当前 frozen standard-JTL/replay fixture 的回顾性 provisional 方法学门，不是所有 underdamped JTL 的 universal acceptance spec。
- reverse polarity 不提供 logical0 的 state-selective evidence。

## 9. Final disposition

`JTL_TRANSPORT_GATE_V1` 回顾性方法学分类完成：保留 strict local 与 settled-well transport 两条证据链；R11 positive、M1 ideal replay、pulse-5 original 落入 provisional one-well transport-signature class，M5-PC 降级为 two-well scaled-JTL control，reverse replay 不通过 one-well positive-polarity 条件。该结果不是 global Authority metric freeze；停止，不运行后续电路实验。
