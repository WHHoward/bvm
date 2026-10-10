# Carry CB + canonical sJTL batch — mechanical evidence brief

- Status: `PASS / AWAITING_SCIENTIFIC_REVIEW`; physical solves: 4; scientific interpretation: `NOT_PERFORMED`.
- D1-D6 topology: previous T1 Carry → canonical CB_0928 → one canonical sJTL_0923 → JOIN with array DOUT → T1 input.
- `V(DOUT_Dk)` shares the sensed zero-volt boundary with JOIN; no DOUT voltage area is presented as an array-only pulse/event count.
- Raw phase remains radians. Phase/area values and descriptive extrema are registered actual-grid arithmetic, not SFQ or bit counts.

| Run | Reference | Raw bytes | Raw SHA-256 | QA |
|---|---|---:|---|---|
| A030_CARRY_POST_CB_SJTL_ALL_200 | A027_FULL_CB_CHAIN_ALL_CLOCK | 91827970 | `027bb32757c1b426b2876ad2d694b6560cea58e6d54a733fd821408538ae166b` | PASS |
| A031_CARRY_POST_CB_SJTL_ALL_210 | A027_FULL_CB_CHAIN_ALL_CLOCK | 91858915 | `c796e9b13024720fc1f5e3268e4174b4064343ab83a57bed3967ac4ed2c3dddf` | PASS |
| A032_CARRY_POST_CB_SJTL_PAPER_210 | A028_FULL_CB_CHAIN_PAPER_CLOCK | 91897687 | `439e9444964adf59043d11b39808c33fcd4f29d63d45835af4fa8cb5333546b5` | PASS |
| A033_CARRY_POST_CB_SJTL_3X3_210 | A029_FULL_CB_CHAIN_3X3_CLOCK | 92022445 | `d4ed238cf7f7b113bb2e32c94b904d027ad5cf2c443502ae5183f3c4d3b1383c` | PASS |

Mechanical detail:

- [Stage boundaries](</home/howard/JoSIM/test/exploration/bvm-4x4-diagonal-array-v1-20261009/analysis/carry-post-cb-sjtl-20261010/CARRY_POST_CB_SJTL_STAGE_METRICS.csv>)
- [Same-JJ phase/area](</home/howard/JoSIM/test/exploration/bvm-4x4-diagonal-array-v1-20261009/analysis/carry-post-cb-sjtl-20261010/CARRY_POST_CB_SJTL_SAME_JJ_PHASE_AREA.csv>)
- [Waveform/current metrics](</home/howard/JoSIM/test/exploration/bvm-4x4-diagonal-array-v1-20261009/analysis/carry-post-cb-sjtl-20261010/CARRY_POST_CB_SJTL_SIGNAL_METRICS.csv>)
- [Matched arithmetic deltas](</home/howard/JoSIM/test/exploration/bvm-4x4-diagonal-array-v1-20261009/analysis/carry-post-cb-sjtl-20261010/CARRY_POST_CB_SJTL_COMPARISON.csv>)
- HTML files remain local under `plots/`; no physical interpretation or follow-up is authorized.
