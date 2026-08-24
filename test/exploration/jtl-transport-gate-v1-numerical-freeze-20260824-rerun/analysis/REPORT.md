# JTL_TRANSPORT_GATE_V1 strict numerical replay

parent accepted HEAD: `8bb86f61c3243655467d61f00680977349b41cf3`  
严格 successor 分析记录 `9` 个 timestep baseline raw，并对每个 raw 做独立 3×3 pre/post window robustness check。
raw `P(...)` 直接作为连续 phase；未使用 legacy `fast_events`，未修改 JTL topology 或 physical parameters。

## 1. Artifact QA

| fixture | dt | rows | actual dt min/median/max (ps) | raw sha256 prefix |
|---|---:|---:|---:|---|
| r11 | 0p025 | 6799 | 0.025/0.025/0.05 | `54d97fc51af07ab2…` |
| r11 | 0p0125 | 13599 | 0.0125/0.0125/0.025 | `28c1b2f4c2a6adec…` |
| r11 | 0p00625 | 27199 | 0.0062/0.00625/0.0125 | `70ae1cdafbbc3028…` |
| pulse5-original | 0p025 | 11999 | 0.025/0.025/0.05 | `25d447af66602bfb…` |
| pulse5-original | 0p0125 | 23999 | 0.0125/0.0125/0.025 | `f1000cffbee1d915…` |
| pulse5-original | 0p00625 | 47999 | 0.0062/0.00625/0.0125 | `420d4b1f4fe72b31…` |
| pulse5-reverse | 0p025 | 11999 | 0.025/0.025/0.05 | `e488cbd2eab83d83…` |
| pulse5-reverse | 0p0125 | 23999 | 0.0125/0.0125/0.025 | `c91f87e870bad83f…` |
| pulse5-reverse | 0p00625 | 47999 | 0.0062/0.00625/0.0125 | `18750121e361e8aa…` |

## 2. Fixture disposition

| fixture | timestep transport | timestep strict local vector | window robustness | final fixture class |
|---|---|---|---|---|
| r11 | `[True, True, True]` | `[[1, 0, 0, 0], [1, 0, 0, 0], [1, 0, 0, 0]]` | `True` | **POSITIVE_FOUR_STAGE_PLUS_ONE** |
| pulse5-original | `[True, True, True]` | `[[1, 0, 0, 0], [1, 0, 0, 0], [1, 0, 0, 0]]` | `False` | **NUMERICAL_GATE_NOT_CLOSED** |
| pulse5-reverse | `[False, False, False]` | `[[0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]]` | `True` | **REVERSE_NON_TRANSPORT** |

## 3. W0 strict local and settled transport evidence

Strict local segments and settled wells are separate. A settled transport vector does not relabel downstream sub-turn segments as local events.

| fixture | dt | JJ | largest strict turns/area | pre→post mean/median | full phase/area/residual | pre/post p2p | t50 | tail extra | vector stage |
|---|---|---|---:|---:|---:|---:|---:|---:|---|
| r11 | 0p025 | `P(B1|XJTL1)` | 1.02714/1.02737 | 1.00406/1.00421 | 1.00487/1.00487/-2.52e-06 | 0.00293359/0.0044113 | 12.7456 | 0 | Y |
| r11 | 0p025 | `P(B2|XJTL1)` | 0.927155/0.927335 | 1.0027/1.00279 | 1.00401/1.00401/-2.002e-06 | 0.00277692/0.00409092 | 14.3931 | 0 | Y |
| r11 | 0p025 | `P(B1|XJTL2)` | 0.92361/0.923769 | 1.0048/1.00505 | 1.00272/1.00272/-3.644e-07 | 0.00272481/0.0070582 | 16.2124 | 0 | Y |
| r11 | 0p025 | `P(B2|XJTL2)` | 0.86957/0.869684 | 1.0135/1.01469 | 1.00436/1.00436/2.668e-06 | 0.00621752/0.00810321 | 18.5078 | 0 | Y |
| r11 | 0p0125 | `P(B1|XJTL1)` | 1.02733/1.02739 | 1.00405/1.00421 | 1.00488/1.00488/-7.06e-07 | 0.00295864/0.00443708 | 12.7458 | 0 | Y |
| r11 | 0p0125 | `P(B2|XJTL1)` | 0.92721/0.927254 | 1.0027/1.00281 | 1.00371/1.00371/-2.929e-07 | 0.00277444/0.00411829 | 14.393 | 0 | Y |
| r11 | 0p0125 | `P(B1|XJTL2)` | 0.923721/0.923761 | 1.0048/1.00505 | 1.00319/1.00319/-2.857e-07 | 0.00271372/0.00705518 | 16.2123 | 0 | Y |
| r11 | 0p0125 | `P(B2|XJTL2)` | 0.869682/0.86971 | 1.01348/1.01466 | 1.00413/1.00413/7.233e-07 | 0.00626138/0.0081056 | 18.5079 | 0 | Y |
| r11 | 0p00625 | `P(B1|XJTL1)` | 1.02736/1.02737 | 1.00404/1.00421 | 1.00488/1.00488/-2.006e-07 | 0.00297013/0.00444058 | 12.7458 | 0 | Y |
| r11 | 0p00625 | `P(B2|XJTL1)` | 0.927205/0.927216 | 1.0027/1.00281 | 1.00361/1.00361/-1.431e-07 | 0.00277331/0.00412179 | 14.393 | 0 | Y |
| r11 | 0p00625 | `P(B1|XJTL2)` | 0.923736/0.923746 | 1.0048/1.00505 | 1.00335/1.00335/-7.156e-08 | 0.00271063/0.00704961 | 16.2123 | 0 | Y |
| r11 | 0p00625 | `P(B2|XJTL2)` | 0.86972/0.869727 | 1.01348/1.01465 | 1.00405/1.00405/1.986e-07 | 0.0062813/0.00810258 | 18.5079 | 0 | Y |
| pulse5-original | 0p025 | `P(B1|XJTL1)` | 1.07598/1.07626 | 1.00005/1.00002 | 0.992449/0.992437/1.144e-05 | 0/0.0177111 | 215.895 | 0 | Y |
| pulse5-original | 0p025 | `P(B2|XJTL1)` | 0.92742/0.927578 | 0.999956/0.999955 | 1.0126/1.01262/-1.807e-05 | 0/0.0240362 | 217.558 | 0 | Y |
| pulse5-original | 0p025 | `P(B1|XJTL2)` | 0.921716/0.92188 | 0.999517/0.999897 | 0.985627/0.985613/1.36e-05 | 0/0.0218311 | 219.422 | 0 | Y |
| pulse5-original | 0p025 | `P(B2|XJTL2)` | 0.859279/0.859396 | 0.998375/0.999749 | 0.98312/0.983113/7.158e-06 | 0/0.017433 | 221.718 | 0 | Y |
| pulse5-original | 0p0125 | `P(B1|XJTL1)` | 1.07619/1.07626 | 1.00006/1.00001 | 0.99294/0.992938/2.605e-06 | 0/0.0178815 | 215.895 | 0 | Y |
| pulse5-original | 0p0125 | `P(B2|XJTL1)` | 0.927474/0.927512 | 0.99994/0.999964 | 1.01275/1.01275/-4.565e-06 | 0/0.0237481 | 217.558 | 0 | Y |
| pulse5-original | 0p0125 | `P(B1|XJTL2)` | 0.921813/0.921853 | 0.999528/0.999898 | 0.985742/0.985739/3.407e-06 | 0/0.0216389 | 219.421 | 0 | Y |
| pulse5-original | 0p0125 | `P(B2|XJTL2)` | 0.859426/0.859455 | 0.998385/0.999744 | 0.983071/0.983069/1.786e-06 | 0/0.0174377 | 221.718 | 0 | Y |
| pulse5-original | 0p00625 | `P(B1|XJTL1)` | 1.07624/1.07626 | 1.00006/1.00001 | 0.993142/0.993142/2.333e-07 | 0/0.0179097 | 215.895 | 0 | Y |
| pulse5-original | 0p00625 | `P(B2|XJTL1)` | 0.927473/0.927482 | 0.999936/0.999965 | 1.01277/1.01277/1.865e-06 | 0/0.0236577 | 217.558 | 0 | Y |
| pulse5-original | 0p00625 | `P(B1|XJTL2)` | 0.921823/0.921833 | 0.999532/0.999898 | 0.985805/0.985803/2.111e-06 | 0/0.0215733 | 219.421 | 0 | Y |
| pulse5-original | 0p00625 | `P(B2|XJTL2)` | 0.859453/0.85946 | 0.998389/0.999743 | 0.983083/0.983083/6.598e-07 | 0/0.01743 | 221.718 | 0 | Y |
| pulse5-reverse | 0p025 | `P(B1|XJTL1)` | -0.876668/-0.876721 | -0.847/-0.846988 | -0.845492/-0.845491/-1.187e-06 | 0/0.00277646 | 217.188 | 0 | N |
| pulse5-reverse | 0p025 | `P(B2|XJTL1)` | -0.164726/-0.164736 | -0.161462/-0.161461 | -0.161088/-0.161088/-2.001e-07 | 0/0.000670186 | — | 0 | N |
| pulse5-reverse | 0p025 | `P(B1|XJTL2)` | -0.0425929/-0.0425951 | -0.0434034/-0.0434039 | -0.0432207/-0.0432206/-1.281e-07 | 0/0.000310909 | — | 0 | N |
| pulse5-reverse | 0p025 | `P(B2|XJTL2)` | -0.0112311/-0.0112313 | -0.0145683/-0.014583 | -0.0145614/-0.0145614/7.763e-08 | 0/0.000456218 | — | 0 | N |
| pulse5-reverse | 0p0125 | `P(B1|XJTL1)` | -0.876683/-0.876697 | -0.847001/-0.846988 | -0.845557/-0.845557/-2.112e-07 | 0/0.0027346 | 217.188 | 0 | N |
| pulse5-reverse | 0p0125 | `P(B2|XJTL1)` | -0.16474/-0.164743 | -0.161462/-0.161461 | -0.161104/-0.161104/-4.53e-08 | 0/0.000661973 | — | 0 | N |
| pulse5-reverse | 0p0125 | `P(B1|XJTL2)` | -0.0426023/-0.0426028 | -0.0434035/-0.0434037 | -0.0432411/-0.043241/-3.488e-08 | 0/0.000294071 | — | 0 | N |
| pulse5-reverse | 0p0125 | `P(B2|XJTL2)` | -0.0112327/-0.0112328 | -0.0145683/-0.014583 | -0.0145345/-0.0145345/1.588e-08 | 0/0.000455072 | — | 0 | N |
| pulse5-reverse | 0p00625 | `P(B1|XJTL1)` | -0.876686/-0.87669 | -0.847002/-0.846988 | -0.845582/-0.845582/4.755e-07 | 0/0.00272346 | 217.188 | 0 | N |
| pulse5-reverse | 0p00625 | `P(B2|XJTL1)` | -0.164744/-0.164745 | -0.161462/-0.161461 | -0.16111/-0.16111/1.526e-07 | 0/0.000659936 | — | 0 | N |
| pulse5-reverse | 0p00625 | `P(B1|XJTL2)` | -0.0426046/-0.0426047 | -0.0434036/-0.0434037 | -0.043248/-0.043248/-8.642e-09 | 0/0.00028971 | — | 0 | N |
| pulse5-reverse | 0p00625 | `P(B2|XJTL2)` | -0.0112333/-0.0112333 | -0.0145683/-0.014583 | -0.0145256/-0.0145257/5.278e-08 | 0/0.000454451 | — | 0 | N |

## 4. Onset order and reverse signed oracle

| fixture | dt | onset order (ps) | causal order | final settled delta (turn) | transport |
|---|---|---|---|---:|---|
| r11 | 0p025 | `12.7456, 14.3931, 16.2124, 18.5078` | Y | 1.0135 | Y |
| r11 | 0p0125 | `12.7458, 14.393, 16.2123, 18.5079` | Y | 1.01348 | Y |
| r11 | 0p00625 | `12.7458, 14.393, 16.2123, 18.5079` | Y | 1.01348 | Y |
| pulse5-original | 0p025 | `215.895, 217.558, 219.422, 221.718` | Y | 0.998375 | Y |
| pulse5-original | 0p0125 | `215.895, 217.558, 219.421, 221.718` | Y | 0.998385 | Y |
| pulse5-original | 0p00625 | `215.895, 217.558, 219.421, 221.718` | Y | 0.998389 | Y |
| pulse5-reverse | 0p025 | `217.188, —, —, —` | N | -0.0145683 | N |
| pulse5-reverse | 0p0125 | `217.188, —, —, —` | N | -0.0145683 | N |
| pulse5-reverse | 0p00625 | `217.188, —, —, —` | N | -0.0145683 | N |

## 5. Adjacent timestep convergence

The registered local bands are evaluated on every JJ for each adjacent pair; the detailed diffs are in `metrics.json`.

| fixture | 0.025→0.0125 | 0.0125→0.00625 | convergence |
|---|---|---|---|
| r11 | `0p025→0p0125` | `0p0125→0p00625` | **PASS** |
| pulse5-original | `0p025→0p0125` | `0p0125→0p00625` | **PASS** |
| pulse5-reverse | `0p025→0p0125` | `0p0125→0p00625` | **PASS** |

## 6. Independent window robustness

The 3×3 grid treats pre and post perturbations independently while leaving the activity interval fixed. All nine combinations are checked per raw.

| fixture | timestep cases | passing window cases | result |
|---|---:|---:|---|
| r11 | 27 | 27 | **PASS** |
| pulse5-original | 27 | 18 | **FAIL** |
| pulse5-reverse | 27 | 27 | **PASS** |

## 7. Observed

- R11 and pulse-5 original retain four-stage `+1` settled-well vectors across the timestep ladder, while strict local vectors remain separately visible.
- Reverse replay is evaluated in both signed directions and does not form a four-stage one-well chain in the registered raw set.
- Interpolated `t50` values preserve causal stage order; the tail guard covers the full remaining simulation interval rather than only the short post well window.

## 8. Derived

- The numerical classification is stable only within the declared fixture, source, model, load, timestep, window and task-local tolerance scope.
- The positive replay remains an ideal voltage replay and is not physical QB→JTL reception evidence.

## 9. Inference

- A fixture-level numerical methodology freeze is justified only if all three fixture classes, adjacent-step bands, independent window grid and tail guards pass together.
- This result does not establish a universal JTL tolerance, a physical BVM interface, or downstream SFQ delivery from any local JJ phase slip.

## 10. Unknown / limits

- Only the three registered fixtures were tested; no additional source impedance, load, JTL topology or T1 was tested.
- Task-local numerical bands are not device specifications.

## 11. Final disposition

`JTL_TRANSPORT_GATE_V1_STRICT_REPLAY_INCONCLUSIVE`

停止；不进行 JTL/QB/interface 参数优化，不接 T1。
