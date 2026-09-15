# BVM -> QB receiver-boundary R20 shunt — PREFLIGHT

This experiment is governed by docs/EXPERIMENT_CONTRACT.md.

- Experiment: bvm-qb-qbin-shunt-r20-v1-20260914
- Generated at: 2026-09-15T10:51:56+08:00
- Registration HEAD: ff3e9195fe095cffc66dedbd9ca97701c29afc67
- Remote bvm/master at registration: ff3e9195fe095cffc66dedbd9ca97701c29afc67
- Worktree status at registration is recorded in provenance.json; no tracked source is changed by this experiment.
- Preflight status: PASS; no solver has been invoked.
- Solver: JoSIM: Josephson Junction Superconductive SPICE Circuit Simulator
Copyright (C) 2020 by Johannes Delport (jdelport@sun.ac.za)
v2.7.2837d13 compiled on May 30 2026 at 20:37:57; SHA-256 48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2.

## Scientific scope

This is an EXPLORATORY two-case receiver-boundary intervention. The only
candidate change is the top-level resistor R_QBIN_SHUNT QBIN 0 20. No QB
parameter, BVM/JSL source, JTL source, model, bias, stimulus, timing, terminal
load, or read mask outside 0011 and 0111 is authorized. The experiment has
no SCIENTIFIC_REVIEW_AUTHORIZED token; execution produces evidence and
registered arithmetic, not a physical verdict.

## Candidate source closure

- global_jjmit_model: circuits/models/jjmit.cir; SHA-256 19862d1fd1f1f44dfa1523848d7d3b5e2594a6c5da8fdd80144b449e5312a336; global BVM/JSL model closure; required before subcircuits.
- canonical_qb: circuits/qb/bq_parameterized_v1.cir; SHA-256 f676ba1ecb9b2607631a5cfc2f99b7d67e09b9e821457015fba375b8a39f13b0; canonical QB source; no candidate parameter override.
- bvm_jm2_connected: test/exploration/bvm-population-scaling-rj2p12-l1p14-l2p20-ib260-rj32-bjs400-v1-20260910/inputs/bvm_jm2_connected.cir; SHA-256 0093a45cc3910448b484d8bd004c6df8c22358bacc8b3ed5e23912dcab805d54; latest 4x1 historical JM2-connected BVM source.
- jtl2_source: test/exploration/bvm-population-scaling-rj2p12-l1p14-l2p20-ib260-rj32-bjs400-v1-20260910/inputs/jtl2.cir; SHA-256 ffd31f8eda2a86ca0133342be1ce678831b7237a53911eda046d2bff8454855a; latest standard JTL source instantiated six times.
- josim_solver: build/josim-cli; SHA-256 48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2; recorded physical solver.
- plotter: scripts/josim-plot2.py; SHA-256 0aaf0b4bfd148e073d318c9a0762ec13995045abd88cad28336fb8128c33a1d6; standard descriptive renderer.

The global jjmit model is included before BVM/JSL devices. The QB source is
the exact canonical circuits/qb/bq_parameterized_v1.cir text. The QB internal
IB source is fixed by that source; JoSIM's hierarchical I(IB|XBQ) probe is
not reliable and is intentionally not fabricated.

## Read-only baseline and passive references

- baseline_0011_raw: test/exploration/bvm-full-closed-loop-qb-parameter-screening-v1-20260911/references/baseline_rj2p12/ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_0011/raw.csv; SHA-256 3da7b754c990316ff8e5981692afa958d8056a61020a1912548bf6f2b7e0249c; read-only baseline raw; not copied.
- baseline_0011_deck: test/exploration/bvm-full-closed-loop-qb-parameter-screening-v1-20260911/references/baseline_rj2p12/ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_0011/deck.cir; SHA-256 8699459443fb2a1664de711951455298bf296c6365d9194195b478217b8909e3; read-only baseline deck provenance; not copied.
- passive_0011_raw: test/exploration/bvm-population-passive-source-replay-rj2p12-l1p14-l2p20-ib260-rj32-bjs400-v1-20260911/runs/PASSIVE_N2_0011/raw.csv; SHA-256 90fd0c3ebeb8f03f2a941bf6bfd576b6af50c14c732df4a098274ddbdc9f7123; read-only passive counterfactual; not copied.
- baseline_0111_raw: test/exploration/bvm-full-closed-loop-qb-parameter-screening-v1-20260911/references/baseline_rj2p12/ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_0111/raw.csv; SHA-256 1ca15a938b23d4ed08eb964713f91476256c4caf0677d1bfd3dc43020271ec75; read-only baseline raw; not copied.
- baseline_0111_deck: test/exploration/bvm-full-closed-loop-qb-parameter-screening-v1-20260911/references/baseline_rj2p12/ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_0111/deck.cir; SHA-256 98953fc7e14b107b255f6ce6ca4a4a0b0e56aa1b13292f372fb7df6b7cd73914; read-only baseline deck provenance; not copied.
- passive_0111_raw: test/exploration/bvm-population-passive-source-replay-rj2p12-l1p14-l2p20-ib260-rj32-bjs400-v1-20260911/runs/PASSIVE_N3_0111/raw.csv; SHA-256 55589ac102aba281f5c61f99d587a07c50f5d058308f956d0b52c9c5d9666dbc; read-only passive counterfactual; not copied.

Baseline raw files are not copied or modified. Baseline decks are provenance
only; their derived BQ include is semantically parameter-equivalent to the
canonical QB values used by the candidate. Passive references are a
counterfactual BVM/JSL topology and are not a matched full-closure baseline.

## Exact topology, protocol and parameters

- Topology: four historical JM2-connected BVMs -> COMMON_SL -> B_JSL1..8 -> QBIN -> canonical QB -> six existing JTL stages -> R_TERM=10 ohm.
- Candidate intervention: exactly one line, R_QBIN_SHUNT QBIN 0 20 (positive current QBIN -> 0).
- QB parameters: Lin=1.5pH, L1=1.4pH, L2=2.0pH, RJ1=32ohm, RJ2=12ohm, IB=260uA, BJS area=4, BJ1 area=0.9, BJ2 area=2, L3=1.3pH.
- JSL junction area: 5.0; terminal load: 10ohm.
- History: IDLE 0-50; WRITE0 50-61; IDLE 61-70; zero-state read control 70-81; IDLE 81-90; WRITE1 90-101; settle 101-110; final read 110-121; tail 121-200 ps.
- Stimulus: 100uA, 1 ps rise/fall, 9 ps plateau; bit order b3b2b1b0=BVM1/BVM2/BVM3/BVM4.
- Timing: .tran 0.1p 200p; expected stored time range 0..199.9 ps.

Registered decks:

- 0011: test/exploration/bvm-qb-qbin-shunt-r20-v1-20260914/runs/0011/deck.cir; SHA-256 f3811f88eda341d317cb3f0aa8e3258dddd5f04f71f749bd8eb283f81179c213; 6342 bytes.
- 0111: test/exploration/bvm-qb-qbin-shunt-r20-v1-20260914/runs/0111/deck.cir; SHA-256 f2f94a603aac1935515d0fcc0c98bd2ec94baa44a0b8d72286a310da0086ea41; 6358 bytes.

## Exact solve matrix

- Physical solves: exactly 0011, then 0111.
- Maximum/authorized solve count: 2.
- No automatic sweep, retry, parameter change, timing change, mask change or follow-up solve.
- A solver/tool failure is preserved in its run log and stops the matrix.

## Probes and arithmetic

- Every BVM has P/V/I for B_JM1, B_JM2, B_JS1, B_JS2; I/V for L_M1, L_M2, L_M3, L_S1, L_S2, L_S3, L_PSL, L_SL; and local source currents I(I_WLn), I(I_BLn), I(I_SEn).
- Shared boundary has V(COMMON_SL), P/V/I for every JSL JJ, V(QBIN), I(B_JSL8), I(R_QBIN_SHUNT), and I(LIN|XBQ).
- QB has P/V/I for BJS, BJ1, BJ2; I/V for LIN, L1, L2, L3; I/V for RJ1, RJ2; and V(QBOUT).
- Every JTL stage has P/V/I for B01 and B02, stage output voltage, and final I(R_TERM).
- Boundary directions: I(B_JSL8) is JSL_NODE7 -> QBIN; I(R_QBIN_SHUNT) is QBIN -> 0; I(LIN|XBQ) is QBIN -> BQ internal node 1. Registered residual: I(B_JSL8) - I(R_QBIN_SHUNT) - I(LIN|XBQ).
- Windows are half-open [start,end) ps and use actual stored timestamps. Phase is raw radians; turns are only unwrap(rad)/(2*pi) for navigation. Voltage-area arithmetic uses actual-grid trapezoids and is not an event count.

## Visualization and interpretation ceiling

- Each run receives seven standalone full-window HTML pages: 01_bvm_phase, 02_bvm_currents, 03_common_jsl, 04_qbin_boundary, 05_qb, 06_jtl, 07_terminal.
- Four full-window comparison HTML pages are generated after standalone QA. No focused/cropped HTML, PNG, PDF, derived plot CSV, or giant dashboard is generated.
- 04_qbin_boundary explicitly includes V(COMMON_SL), V(QBIN), I(B_JSL8), I(R_QBIN_SHUNT), and I(LIN|XBQ) with direction notes.
- Scientific labels such as mechanism support, functional success, overdamping, no effect, pathology, SFQ count, and Gate status remain unassigned.

After mechanical QA, visualization QA, package QA and commit, stop at
EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW. No raw is overwritten, silently corrected, or deleted.
