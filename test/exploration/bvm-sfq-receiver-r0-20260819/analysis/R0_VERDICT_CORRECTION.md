# R0 verdict correction and supersession

**Correction created:** 2026-08-19T04:37:19+08:00
**Applies to:** commit `c760c13c685d16bcbe3977e1df535e48bf45711b`
**Raw-data status:** all raw CSV files from that commit are retained byte-for-byte

The original `R0 PASS` in the c760c13 report overclaimed the trigger-level
evidence. Direct reinspection of `P(B_TRIG|XTRIG)` and the same-junction
`V(B_TRIG|XTRIG)` shows that the read1 activity range is only

```text
3.672452 rad = 0.584488889 turns < 2*pi
```

The read1 activity-window endpoint phase delta is only about `0.0123121 turns`,
and the same-JJ voltage area is about `0.0123145 turns`. No monotonic segment
in the preserved raw trajectory reaches a complete `2*pi` phase evolution.
Therefore the trace must not be called a complete switching/phase-transition
success. It also must not be called SFQ delivery.

## Current split verdict

- **R0-A threshold discrimination: PASS.** The canonical SL route with the
  matched receiver preserves the loaded logical1/read1 versus logical0/read0
  separation; the two READ=0 controls remain bias-only; and the bounded
  storage/back-action checks remain positive.
- **R0-B complete trigger switching: NOT_YET.** The preserved read1 trigger
  trace does not contain a monotonic segment of at least `2*pi`.
- **Overall current R0 verdict: PARTIAL.**

This correction changes interpretation only. It does not modify canonical BVM,
the receiver raw data, or the historical c760c13 commit. The independent
follow-up is `test/exploration/bvm-sfq-receiver-r0b-20260819/`, which tests only
the complete-trigger criterion and does not add self-quench, an output JJ, or a
JTL.

## Additional numerical erratum

Recomputing the actual AREA=0.50 model values gives

```text
beta_c = 2*pi*Ic*RN^2*C/Phi0 = 5.4450545
```

The `0.0544` value printed in the historical c760c13 report was an arithmetic
error. The corrected report now records `5.4451`; this is a derived-parameter
correction and does not change any raw artifact or the split verdict above.
