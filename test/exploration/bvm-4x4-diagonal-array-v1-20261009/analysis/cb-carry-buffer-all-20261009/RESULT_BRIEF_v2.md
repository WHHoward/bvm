# A027-A029 full CB-only carry chain — mechanical evidence

- Batch: `BVM4X4_CB_CARRY_BUFFER_ALL_20261009`; status: `PASS`; solves: 3; scientific interpretation: `NOT PERFORMED`.
- Each D1-D6 input uses two measured branches, with only the previous T1 Carry passing through the added canonical CB_0928; JOIN connects directly to the current T1 input.
- Artifact, raw, mechanical QA and classic plot QA passed for all three cases.
- Theory vectors in the tables are references only. No bit decode, event count, or success verdict is assigned.
- Same-JJ phase/voltage records use actual timestamps, exact half-open windows, and raw phase in radians.
- Clock comparison uses the measured V(CLK_Dk)/V(CLK_DFF) peak and descriptive last-input lobe candidates only.
- Time-step convergence: `UNKNOWN`; no new settings or follow-up solves authorized.
- Post-process incident `ANALYSIS_INCIDENT_001` records two corrected summary-key defects; repair revision 2 reread the same raw only, with no extra solver calls. Earlier partial CSV/HTML outputs are retained as unaccepted revision-1 artifacts.

| Run | Product reference | Raw bytes | Raw SHA-256 | samples | QA |
|---|---:|---:|---|---:|---|
| A027_FULL_CB_CHAIN_ALL_CLOCK | 225 | 93401769 | `939e6024928be84df809532ecd8b716b815a9b96ea498324fc5c30b712100e46` | 29999 | PASS |
| A028_FULL_CB_CHAIN_PAPER_CLOCK | 143 | 93431488 | `59ba22b2c31bd04993989c16a7c37d1e5bb904c078ef9db979657de81e604701` | 29999 | PASS |
| A029_FULL_CB_CHAIN_3X3_CLOCK | 9 | 93510947 | `d943765ab3e47c1607ab3c29ff08a1088f2444dfd8a3266e9670a1d75d24ac0f` | 29999 | PASS |

Tables: `FULL_CB_CHAIN_STAGE_METRICS_v2.csv`, `FULL_CB_CHAIN_JJ_PHASE_AREA_v2.csv`, `FULL_CB_CHAIN_TIMING_v2.csv`, `FULL_CB_CHAIN_SIGNAL_METRICS_v2.csv`, `FULL_CB_CHAIN_OUTPUT_METRICS_v2.csv`, `FULL_CB_CHAIN_COMPARISON_v2.csv`.
Plots: eight classic pages per run (full overview, carry propagation, D1-D6 focus) plus A025/A027 and A026/A028 D1 comparisons. HTML is local and excluded from ZIPs.
No CB isolation, SFQ count, bit-decode, or multiplier-success conclusion is made.
