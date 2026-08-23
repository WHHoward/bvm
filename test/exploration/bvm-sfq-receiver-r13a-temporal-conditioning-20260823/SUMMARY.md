# R13-A summary

- **Verdict:** `TEMPORAL_CONDITIONING_INSUFFICIENT`
- **Scope:** R12 actual DCSFQ_BVM input replay; no BVM/DCSFQ parameter change, no
  JTL/T1, no amplitude or duration sweep.
- **Input:** `I(L1|XCONV)`, positive `a→node1` direction is favorable; read1
  `+110.200/−44.274 µA`, signed area `517.106 µA·ps`; read0
  `+29.777/−32.544 µA`, signed area approximately zero.
- **Raw replay:** read1 B3 largest segment `−0.030817 turn`, read0 `0.008367
  turn`, controls `~4.1e−7 turn`; qualitative replay validity passed.
- **C1 rectification:** read1 B3 `0.023616 turn`, read0 `0.006164 turn`.
- **C2 20 ps hold:** read1 B3 `0.024492 turn`, read0 `0.007929 turn`.
- **C3 rectification + hold:** read1 B3 `0.023616 turn`, read0 `0.005241
  turn`.
- **Event evidence:** all same-JJ segment voltage areas agree with their sub-turn
  phase changes, but no read1 segment reaches `1 turn`; no read0/control complete
  event and no free-running.
- **Interpretation:** polarity cancellation and dwell are not sufficient by
  themselves at this frozen amplitude; a future physical conditioner likely needs
  active/regenerative gain or equivalent energy holding. This is a bounded
  requirements result, not a universal impossibility claim.
- **JTL:** not run because no qualifying B3 local event occurred.

Detailed evidence is in [`R13A_REPORT.md`](analysis/R13A_REPORT.md), structured
metrics in `analysis/r13a-metrics.json` and source/transform metrics in
`analysis/input-waveform-metrics.json`.
