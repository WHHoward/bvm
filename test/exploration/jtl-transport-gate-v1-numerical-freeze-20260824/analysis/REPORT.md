# JTL_TRANSPORT_GATE_V1 numerical-freeze pilot

# Pilot disposition

`PILOT_INCONCLUSIVE_PENDING_STRICT_REPLAY`

parent accepted HEAD: `8bb86f61c3243655467d61f00680977349b41cf3`  
本报告保存了首轮 3 fixtures × 3 timesteps 结果，并对固定 activity window 做了 W−/W0/W+ pre/post robustness check。
它是数值 pilot，不是最终 Gate freeze：后续严格复核会使用未变换的 raw phase、hash-bound input snapshot、完整 tail guard，以及独立的 pre/post window perturbation。
未修改 JTL topology/physical parameters；未使用 legacy fast_events。

## 1. Numerical artifact QA

| fixture | dt request | rows | actual dt min/median/max (ps) | exit | raw sha256 prefix |
|---|---:|---:|---:|---:|---|
| r11 | 0p025 | 6799 | 0.025/0.025/0.05 | 0 | `54d97fc51af07ab2…` |
| r11 | 0p0125 | 13599 | 0.0125/0.0125/0.025 | 0 | `28c1b2f4c2a6adec…` |
| r11 | 0p00625 | 27199 | 0.0062/0.00625/0.0125 | 0 | `70ae1cdafbbc3028…` |
| pulse5-original | 0p025 | 11999 | 0.025/0.025/0.05 | 0 | `25d447af66602bfb…` |
| pulse5-original | 0p0125 | 23999 | 0.0125/0.0125/0.025 | 0 | `f1000cffbee1d915…` |
| pulse5-original | 0p00625 | 47999 | 0.0062/0.00625/0.0125 | 0 | `420d4b1f4fe72b31…` |
| pulse5-reverse | 0p025 | 11999 | 0.025/0.025/0.05 | 0 | `e488cbd2eab83d83…` |
| pulse5-reverse | 0p0125 | 23999 | 0.0125/0.0125/0.025 | 0 | `c91f87e870bad83f…` |
| pulse5-reverse | 0p00625 | 47999 | 0.0062/0.00625/0.0125 | 0 | `18750121e361e8aa…` |

实际 dt 使用 CSV 时间列重算；JoSIM 自适应/输出采样导致报告 min/median/max，而不是把请求值冒充为每一行固定间隔。

## 2. Fixture-level disposition

| fixture | W− | W0 | W+ | strict local vectors (dt × W0) | fixture verdict |
|---|---|---|---|---|---|
| r11 | `[True, True, True]` | `[True, True, True]` | `[True, True, True]` | `[[1, 0, 0, 0], [1, 0, 0, 0], [1, 0, 0, 0]]` | **NUMERICALLY_STABLE_FOUR_STAGE_PLUS_ONE** |
| pulse5-original | `[True, True, True]` | `[True, True, True]` | `[True, True, True]` | `[[1, 0, 0, 0], [1, 0, 0, 0], [1, 0, 0, 0]]` | **NUMERICALLY_STABLE_FOUR_STAGE_PLUS_ONE** |
| pulse5-reverse | `[False, False, False]` | `[False, False, False]` | `[False, False, False]` | `[[0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]]` | **REVERSE_NON_TRANSPORT_STABLE** |

## 3. W0 per-JJ evidence across timestep ladder

Strict local segment与settled-well transport分开报告。full-window 是注册 activity window；phase/area 为同一 JJ、同一方向和实际 CSV time。

| fixture | dt | JJ | strict largest turn/area | pre→post mean/median | full phase/area/residual | pre p2p | post p2p | t50 ps | post extra | transport |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| r11 | 0p025 | `P(B1|XJTL1)` | 1.02714/1.02737 | 1.00406/1.00421 | 1.00487/1.00487/-2.52e-06 | 0.00293359 | 0.0044113 | 12.75 | 0 | Y |
| r11 | 0p025 | `P(B2|XJTL1)` | 0.927155/0.927335 | 1.0027/1.00279 | 1.00401/1.00401/-2.002e-06 | 0.00277692 | 0.00409092 | 14.4 | 0 | Y |
| r11 | 0p025 | `P(B1|XJTL2)` | 0.92361/0.923769 | 1.0048/1.00505 | 1.00272/1.00272/-3.644e-07 | 0.00272481 | 0.0070582 | 16.225 | 0 | Y |
| r11 | 0p025 | `P(B2|XJTL2)` | 0.86957/0.869684 | 1.0135/1.01469 | 1.00436/1.00436/2.668e-06 | 0.00621752 | 0.00810321 | 18.525 | 0 | Y |
| r11 | 0p0125 | `P(B1|XJTL1)` | 1.02733/1.02739 | 1.00405/1.00421 | 1.00488/1.00488/-7.06e-07 | 0.00295864 | 0.00443708 | 12.75 | 0 | Y |
| r11 | 0p0125 | `P(B2|XJTL1)` | 0.92721/0.927254 | 1.0027/1.00281 | 1.00371/1.00371/-2.929e-07 | 0.00277444 | 0.00411829 | 14.4 | 0 | Y |
| r11 | 0p0125 | `P(B1|XJTL2)` | 0.923721/0.923761 | 1.0048/1.00505 | 1.00319/1.00319/-2.857e-07 | 0.00271372 | 0.00705518 | 16.2125 | 0 | Y |
| r11 | 0p0125 | `P(B2|XJTL2)` | 0.869682/0.86971 | 1.01348/1.01466 | 1.00413/1.00413/7.233e-07 | 0.00626138 | 0.0081056 | 18.5125 | 0 | Y |
| r11 | 0p00625 | `P(B1|XJTL1)` | 1.02736/1.02737 | 1.00404/1.00421 | 1.00488/1.00488/-2.006e-07 | 0.00297013 | 0.00444058 | 12.75 | 0 | Y |
| r11 | 0p00625 | `P(B2|XJTL1)` | 0.927205/0.927216 | 1.0027/1.00281 | 1.00361/1.00361/-1.431e-07 | 0.00277331 | 0.00412179 | 14.3937 | 0 | Y |
| r11 | 0p00625 | `P(B1|XJTL2)` | 0.923736/0.923746 | 1.0048/1.00505 | 1.00335/1.00335/-7.156e-08 | 0.00271063 | 0.00704961 | 16.2125 | 0 | Y |
| r11 | 0p00625 | `P(B2|XJTL2)` | 0.86972/0.869727 | 1.01348/1.01465 | 1.00405/1.00405/1.986e-07 | 0.0062813 | 0.00810258 | 18.5125 | 0 | Y |
| pulse5-original | 0p025 | `P(B1|XJTL1)` | 1.07598/1.07626 | 1.00005/1.00002 | 0.992449/0.992437/1.144e-05 | 0 | 0.0177111 | 215.9 | 0 | Y |
| pulse5-original | 0p025 | `P(B2|XJTL1)` | 0.92742/0.927578 | 0.999956/0.999955 | 1.0126/1.01262/-1.807e-05 | 0 | 0.0240362 | 217.575 | 0 | Y |
| pulse5-original | 0p025 | `P(B1|XJTL2)` | 0.921716/0.92188 | 0.999517/0.999897 | 0.985627/0.985613/1.36e-05 | 0 | 0.0218311 | 219.425 | 0 | Y |
| pulse5-original | 0p025 | `P(B2|XJTL2)` | 0.859279/0.859396 | 0.998375/0.999749 | 0.98312/0.983113/7.158e-06 | 0 | 0.017433 | 221.725 | 0 | Y |
| pulse5-original | 0p0125 | `P(B1|XJTL1)` | 1.07619/1.07626 | 1.00006/1.00001 | 0.99294/0.992938/2.605e-06 | 0 | 0.0178815 | 215.9 | 0 | Y |
| pulse5-original | 0p0125 | `P(B2|XJTL1)` | 0.927474/0.927512 | 0.99994/0.999964 | 1.01275/1.01275/-4.565e-06 | 0 | 0.0237481 | 217.562 | 0 | Y |
| pulse5-original | 0p0125 | `P(B1|XJTL2)` | 0.921813/0.921853 | 0.999528/0.999898 | 0.985742/0.985739/3.407e-06 | 0 | 0.0216389 | 219.425 | 0 | Y |
| pulse5-original | 0p0125 | `P(B2|XJTL2)` | 0.859426/0.859455 | 0.998385/0.999744 | 0.983071/0.983069/1.786e-06 | 0 | 0.0174377 | 221.725 | 0 | Y |
| pulse5-original | 0p00625 | `P(B1|XJTL1)` | 1.07624/1.07626 | 1.00006/1.00001 | 0.993142/0.993142/2.333e-07 | 0 | 0.0179097 | 215.9 | 0 | Y |
| pulse5-original | 0p00625 | `P(B2|XJTL1)` | 0.927473/0.927482 | 0.999936/0.999965 | 1.01277/1.01277/1.865e-06 | 0 | 0.0236577 | 217.562 | 0 | Y |
| pulse5-original | 0p00625 | `P(B1|XJTL2)` | 0.921823/0.921833 | 0.999532/0.999898 | 0.985805/0.985803/2.111e-06 | 0 | 0.0215733 | 219.425 | 0 | Y |
| pulse5-original | 0p00625 | `P(B2|XJTL2)` | 0.859453/0.85946 | 0.998389/0.999743 | 0.983083/0.983083/6.598e-07 | 0 | 0.01743 | 221.719 | 0 | Y |
| pulse5-reverse | 0p025 | `P(B1|XJTL1)` | -0.876668/-0.876721 | -0.847/-0.846988 | -0.845492/-0.845491/-1.187e-06 | 0 | 0.00277646 | — | 0 | N |
| pulse5-reverse | 0p025 | `P(B2|XJTL1)` | -0.164726/-0.164736 | -0.161462/-0.161461 | -0.161088/-0.161088/-2.001e-07 | 0 | 0.000670186 | — | 0 | N |
| pulse5-reverse | 0p025 | `P(B1|XJTL2)` | -0.0425929/-0.0425951 | -0.0434034/-0.0434039 | -0.0432207/-0.0432206/-1.281e-07 | 0 | 0.000310909 | — | 0 | N |
| pulse5-reverse | 0p025 | `P(B2|XJTL2)` | -0.0112311/-0.0112313 | -0.0145683/-0.014583 | -0.0145614/-0.0145614/7.763e-08 | 0 | 0.000456218 | — | 0 | N |
| pulse5-reverse | 0p0125 | `P(B1|XJTL1)` | -0.876683/-0.876697 | -0.847001/-0.846988 | -0.845557/-0.845557/-2.112e-07 | 0 | 0.0027346 | — | 0 | N |
| pulse5-reverse | 0p0125 | `P(B2|XJTL1)` | -0.16474/-0.164743 | -0.161462/-0.161461 | -0.161104/-0.161104/-4.53e-08 | 0 | 0.000661973 | — | 0 | N |
| pulse5-reverse | 0p0125 | `P(B1|XJTL2)` | -0.0426023/-0.0426028 | -0.0434035/-0.0434037 | -0.0432411/-0.043241/-3.488e-08 | 0 | 0.000294071 | — | 0 | N |
| pulse5-reverse | 0p0125 | `P(B2|XJTL2)` | -0.0112327/-0.0112328 | -0.0145683/-0.014583 | -0.0145345/-0.0145345/1.588e-08 | 0 | 0.000455072 | — | 0 | N |
| pulse5-reverse | 0p00625 | `P(B1|XJTL1)` | -0.876686/-0.87669 | -0.847002/-0.846988 | -0.845582/-0.845582/4.755e-07 | 0 | 0.00272346 | — | 0 | N |
| pulse5-reverse | 0p00625 | `P(B2|XJTL1)` | -0.164744/-0.164745 | -0.161462/-0.161461 | -0.16111/-0.16111/1.526e-07 | 0 | 0.000659936 | — | 0 | N |
| pulse5-reverse | 0p00625 | `P(B1|XJTL2)` | -0.0426046/-0.0426047 | -0.0434036/-0.0434037 | -0.043248/-0.043248/-8.642e-09 | 0 | 0.00028971 | — | 0 | N |
| pulse5-reverse | 0p00625 | `P(B2|XJTL2)` | -0.0112333/-0.0112333 | -0.0145683/-0.014583 | -0.0145256/-0.0145257/5.278e-08 | 0 | 0.000454451 | — | 0 | N |

## 4. Causal onset order

| fixture | dt | W0 t50 order (ps) | order |
|---|---|---|---|
| r11 | 0p025 | `12.75, 14.4, 16.225, 18.525` | Y |
| r11 | 0p0125 | `12.75, 14.4, 16.2125, 18.5125` | Y |
| r11 | 0p00625 | `12.75, 14.3937, 16.2125, 18.5125` | Y |
| pulse5-original | 0p025 | `215.9, 217.575, 219.425, 221.725` | Y |
| pulse5-original | 0p0125 | `215.9, 217.562, 219.425, 221.725` | Y |
| pulse5-original | 0p00625 | `215.9, 217.562, 219.425, 221.719` | Y |
| pulse5-reverse | 0p025 | `—, —, —, —` | N |
| pulse5-reverse | 0p0125 | `—, —, —, —` | N |
| pulse5-reverse | 0p00625 | `—, —, —, —` | N |

## 5. Observed

- R11 standard-JTL 在三个 timestep 和三个注册窗口版本中均保留四颗 JJ 的 settled `+1` transport vector；严格 local vector 仍独立报告，未被 settled well 证据覆盖。
- pulse-5 original ideal replay 在相同 ladder/window matrix 中也保留四级 `+1` transport vector；它仍是 ideal voltage replay，不是 physical Q0→JTL coupling。
- pulse-5 reverse 在所有 ladder/window 组合中都没有形成预期的正向四级 one-well transport；它不是 logical0/state-selectivity control。
- 每个 raw 均 exit 0、时间严格递增、包含四颗 JTL JJ 的直接 P/V/I probes；phase/area residual、pre/post p2p、post extra segment 和 t50 均按注册规则重算。

## 6. Derived

- 在本 fixture、源波形、模型、负载、窗口和三档 timestep 定义下，settled-well transport vector 对数值 refinement 与小幅 pre/post 窗口扰动不敏感。
- strict local event vector 与四级 settled transport vector 是不同输出；后者只支持 transport-level evidence，不把后三级的 sub-turn monotonic segment重命名为 local complete event。

## 7. Inference

- 首轮 pilot 在已执行的三档 timestep 和耦合窗口视图中观察到 R11 与 pulse-5 original 的四级 `+1` settled-well transport，reverse 保持 non-transport；但这些结果只支持进入严格 successor，不足以关闭 numerical freeze。
- 即使 successor 通过，fixture-level freeze 也不等于 global JTL tolerance、不等于 physical BVM/QB interface success，也不改变 accepted Q0/QB load-boundary failures。

## 8. Unknown / limits

- 仅验证了三个注册 fixture；没有测试其他 JTL、其他 source impedance、其他 load 或 T1。
- task-local tolerance（well ±0.02 turn、phase/area residual 2e-4 turn、pre/post p2p 和 order slack）不是器件 universal hard spec。
- ideal replay 的 transport compatibility不能替代真实 QB→JTL loaded reception。

## 9. Pilot disposition

首轮结果与预期 transport 方向一致，但不单独关闭 `JTL_TRANSPORT_GATE_V1`。请以同级 successor exploration 的最终报告为准。

停止本 pilot；不进行 JTL/QB/interface 参数优化，不接 T1。
