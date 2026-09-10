# Selected-mask population scaling handoff

Evidence-only handoff at the frozen RJ2=12ohm candidate working point.

- Existing masks `0001` and `0011` are exact immutable 0.1ps references.
- New physical solves are exactly `0110`, `1100`, `1110`, `0111` and `1111`.
- The generalized oracle derives up to four complete response candidates from
  common-baseline phase landmarks, direct stored-sample voltage clusters,
  ordered JTL progression and valley-segmented terminal pulses.
- Hamming weight is used only for the final population comparison, never by the
  detector itself.
- Canonical timestep remains `.tran=0.1p`; no finer timestep is run here.

Phase values are raw radians. Phase landmarks, pulse areas and response
candidates are mechanical/derived evidence, not SFQ counts or hardware claims.
