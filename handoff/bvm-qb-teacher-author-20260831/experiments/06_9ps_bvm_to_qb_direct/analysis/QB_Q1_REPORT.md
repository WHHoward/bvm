# QB-Q1 canonical BVM → frozen scaled QB compatibility

## Final disposition

`QB_SOURCE_BACKACTION_FAILURE`

read1 BJL2 remains subthreshold (largest same-segment response -0.0980309 turn / -0.0980462 Φ0), while direct QB loading shifts the read1 JS1/JS2 post-state by approximately -2.99727 / -2.99753 turn relative to the canonical no-receiver baseline. The logical1 READ=0 control also changes SL activity from 2.05907e-05 mV p2p to 0.000719063 mV p2p. This is a source/storage back-action failure, not a QB parameter failure claim.

## 主结果

这是直接 galvanic BVM→QB 的 Exploration；没有使用 Q0 的理想电流波形，也没有连接 JTL。

| case | BJs event units | BJL1 event units | BJL2 event units | BJL2 largest Δturn | BJL2 same-segment area (Φ0) | classification |
|---|---:|---:|---:|---:|---:|---|
| logical1-read0-control | 0 | 0 | 0 | -1.65521e-06 | -1.64029e-06 | `QB_BVM_SUBTHRESHOLD` |
| logical1-read | 4 | 0 | 0 | -0.0980309 | -0.0980462 | `QB_BVM_SUBTHRESHOLD` |
| logical0-read | 0 | 0 | 0 | -0.03024 | -0.0302439 | `QB_BVM_SUBTHRESHOLD` |
| logical0-read0-control | 0 | 0 | 0 | 1.70296e-06 | 1.69021e-06 | `QB_BVM_SUBTHRESHOLD` |

## QB input actually received

| case | I(Lin) activity min..max (µA) | V(SL1) activity min..max (mV) | I(Lin) post p2p (µA) |
|---|---:|---:|---:|
| logical1-read0-control | -0.000650966 .. 0.000682605 | -0.00037085 .. 0.000348213 | 0.000112559 |
| logical1-read | -39.1291 .. 60.4884 | -1.03648 .. 1.8663 | 0.707139 |
| logical0-read | -24.8499 .. 19.7584 | -0.36133 .. 0.444301 | 0.133449 |
| logical0-read0-control | -0.00069683 .. 0.000662179 | -0.000356349 .. 0.000379488 | 0.000114828 |

## BJL2 phase/area evidence

| case | activity p2p (turn) | net Δturn | same-segment area (Φ0) | residual (turn) | post p2p (turn) |
|---|---:|---:|---:|---:|---:|
| logical1-read0-control | 1.67113e-06 | -1.65521e-06 | -1.64029e-06 | 1.49189e-08 | 1.43239e-07 |
| logical1-read | 0.165495 | -0.0980309 | -0.0980462 | -1.5259e-05 | 0.000946797 |
| logical0-read | 0.0515585 | -0.03024 | -0.0302439 | -3.91762e-06 | 0.000166269 |
| logical0-read0-control | 1.70296e-06 | 1.70296e-06 | 1.69021e-06 | -1.27499e-08 | 1.43239e-07 |

## BVM source/storage guard differential

The following are loaded minus the copied canonical no-receiver baseline over the same windows. Absolute logical1/read1 JS running is therefore not counted as loading by itself.

| case | signal | activity differential p2p | post differential p2p | post loaded p2p | post baseline p2p |
|---|---|---:|---:|---:|---:|
| logical1-read0-control | SL_V | 0.000698835 | 7.07906e-05 | 7.13623e-05 | 1.42333e-06 |
| logical1-read0-control | N6_V | 0.000683063 | 7.06364e-05 | 7.15171e-05 | 2.85536e-06 |
| logical1-read0-control | SL_I | 0.00171186 | 0.000226386 | 0.000112559 | 0.000118611 |
| logical1-read | SL_V | 3.22884 | 0.331874 | 0.330382 | 0.00163072 |
| logical1-read | N6_V | 3.93671 | 0.336138 | 0.333051 | 0.00327119 |
| logical1-read | SL_I | 120.369 | 0.788536 | 0.707139 | 0.135894 |
| logical0-read | SL_V | 0.62635 | 0.0680925 | 0.0682411 | 0.000330954 |
| logical0-read | N6_V | 0.438672 | 0.0680001 | 0.0683544 | 0.000663966 |
| logical0-read | SL_I | 27.512 | 0.112866 | 0.133449 | 0.0275795 |
| logical0-read0-control | SL_V | 0.000715568 | 7.19681e-05 | 7.25293e-05 | 1.42333e-06 |
| logical0-read0-control | N6_V | 0.000699807 | 7.18342e-05 | 7.26768e-05 | 2.85536e-06 |
| logical0-read0-control | SL_I | 0.00174285 | 0.00022898 | 0.000114828 | 0.000118611 |
| logical1-read0-control | JM1 phase (turn) | 6.52535e-06 | 6.3662e-07 | 2.06901e-06 | 1.90986e-06 |
| logical1-read0-control | JM2 phase (turn) | 9.75142e-05 | 7.78268e-06 | 3.21016e-05 | 3.15127e-05 |
| logical1-read0-control | JS1 phase (turn) | 0.00014047 | 1.73638e-05 | 1.10772e-05 | 6.63676e-06 |
| logical1-read0-control | JS2 phase (turn) | 0.000155542 | 1.72046e-05 | 1.70614e-05 | 7.32113e-07 |
| logical1-read | JM1 phase (turn) | 0.0739709 | 0.00631829 | 0.0037664 | 0.00255221 |
| logical1-read | JM2 phase (turn) | 0.510527 | 0.105924 | 0.0632353 | 0.0426966 |
| logical1-read | JS1 phase (turn) | 3.59405 | 0.086644 | 0.081812 | 0.00891904 |
| logical1-read | JS2 phase (turn) | 3.55503 | 0.0771965 | 0.0763387 | 0.000881718 |
| logical0-read | JM1 phase (turn) | 0.00534379 | 0.000100427 | 0.00038611 | 0.000465369 |
| logical0-read | JM2 phase (turn) | 0.00710652 | 0.001617 | 0.00616181 | 0.00727031 |
| logical0-read | JS1 phase (turn) | 0.0850005 | 0.0160666 | 0.0172622 | 0.00153392 |
| logical0-read | JS2 phase (turn) | 0.125178 | 0.015849 | 0.0160167 | 0.00017811 |
| logical0-read0-control | JM1 phase (turn) | 6.52535e-06 | 6.3662e-07 | 2.06901e-06 | 1.90986e-06 |
| logical0-read0-control | JM2 phase (turn) | 9.70686e-05 | 7.75085e-06 | 3.21811e-05 | 3.15127e-05 |
| logical0-read0-control | JS1 phase (turn) | 0.000144497 | 1.76662e-05 | 1.13637e-05 | 6.63676e-06 |
| logical0-read0-control | JS2 phase (turn) | 0.000159362 | 1.74911e-05 | 1.73479e-05 | 7.32113e-07 |

## Observed

- All four JoSIM artifacts completed with exit code 0; direct BJs/BJL1/BJL2 P/V/I and BVM guard columns are present.
- The requested transient step is 0.0125 ps. Each CSV contains 13,599 samples from 0 to 169.9875 ps and the same deterministic 0.025 ps output interval from 1.8375 to 1.8625 ps; this gap is before the [94,130) ps activity window.
- The QB input is the loaded canonical `SL1` waveform; `I(Lin|XBQ)` is the actual branch current. The deck printed this branch twice, and the duplicate raw columns were verified identical.
- Local event evidence uses raw phase in radians converted to turns and the same JJ/direct V over the same monotonic segment. Peaks and `I>Ic` are not event criteria.

## Derived

- A complete local candidate requires at least one turn, matching phase/area sign, and the explicitly local Q0 residual rule `max(0.05, 0.10|Δturn|)`.
- The four-run matrix used one frozen `.tran 0.0125p` setting; no timestep refinement was authorized. The deterministic output gap is retained as an artifact fact, so this remains an Exploration result rather than a resolution-independent Gate.

## Inference

- `QB_BVM_LOCAL_ONE_SHOT_PASS` is assigned only if read1 has one BJL2 candidate, read0/controls have zero, post is bounded, and guard differentials remain acceptable. Otherwise the more specific bounded disposition is retained.
- A BJL2 local event would still not establish downstream SFQ delivery because no JTL is connected.

## Unknown / stop boundary

- No QB parameter, BVM parameter, source waveform, load, transformer, or bias was optimized.
- If no local one-shot exists, the next diagnosis must separate input coupling, internal JL1 routing, BJL2 threshold, and source back-action; no automatic sweep is implied.
