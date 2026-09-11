# Evidence handoff — passive source replay diagnostic

Scientific interpretation is `NOT_PERFORMED`.

This handoff contains exactly six new physical solves:

- passive source capture: N2 `0011`, N3 `0111`, N4 `1111`;
- exact current replay: N2, N3 and N4 into the current isolated RJ2=12
  QB/JTL receiver.

The closed-loop RJ2=12 N2/N3/N4 files under
`references/closed_loop_rj2p12/` are immutable comparison evidence and were
not rerun in this experiment. The passive waveform is a
`PASSIVE_CAPTURE_COUNTERFACTUAL`; the replay is an ideal current-forcing
waveform-sufficiency fixture, not a source-impedance or circuit-equivalent
reconstruction.

Read in this order:

1. `PREFLIGHT.md`, `analysis/preflight.json` and `experiment.yaml`;
2. `qa/execution_summary.json`, passive/replay fidelity QA and raw hashes;
3. `qa/raw_qa.json`, `mechanical_summary.json` and
   `analysis/MECHANISM_REVIEW.md`;
4. `visualization/manifest.json` and the per-run navigation pages;
5. `handoff/PACKAGE_QA.json` and the canonical ZIP.

`RESULT_BRIEF.md` records the evidence boundary and the final review state.
The canonical evidence ZIP is
`handoff/bvm-population-passive-source-replay-rj2p12-l1p14-l2p20-ib260-rj32-bjs400-v1-20260911_corrected-v2_raw_handoff.zip`.
