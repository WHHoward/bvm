# R14-A summary

- **Verdict:** `PRECHECK_NO_GO`
- **JoSIM:** not run; no raw CSV was generated.
- **Empirical scale:** R1a secondary `5.564 µA / 66.768 µV`; R13 DCSFQ
  `I(L1)` read1 peak `110.200 µA`; R12 controlled references `68.4 µA` no event
  and `300 µA` one local B3 event.
- **Optimistic loaded estimate:** with `T=1.5375 ps`, `L1=1.672 pH`,
  `X_L1≈6.83 Ω`, estimated DCSFQ branch `≈9.77 µA`; retained 12 Ω termination
  branch `≈5.56 µA`; parallel total `≈15.34 µA`.
- **Termination:** `R_SEC_LOAD=12 Ω` is retained by topology provenance. It is
  R1a's physical passive return/termination, not an observation-only dummy. With
  DCSFQ.a connected, it becomes intentional parallel double-loading.
- **Interpretation:** B_DET activity does not establish active current gain into
  DCSFQ. The proposed point does not clear the local scale precheck, so running
  it would not be a causal test of the intended regenerative interface.
- **No changes:** canonical BVM, R0b/R1a/R12/R13 artifacts and parameters remain
  unchanged; no sweep, JTL or T1.

Detailed result: [`R14A_ANALYTIC_PRECHECK.md`](analysis/R14A_ANALYTIC_PRECHECK.md)
