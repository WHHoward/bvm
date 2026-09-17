# Physical LS3 mutual-RL loop — bvm-rloop-ls3-mutual-rl-v1-20260917

This experiment is governed by docs/EXPERIMENT_CONTRACT.md.

- Parent HEAD: `1348140f17f0d9467dc42238eaa1e252e877e07a`; remote `bvm/master`: `1348140f17f0d9467dc42238eaa1e252e877e07a`.
- Study phase: `EXPLORATORY`; role: `Experimental Operator + Evidence Packager`.
- Scientific review authorization: `false`; only mechanical evidence and candidate labels are recorded.
- Question: can a simple passive reciprocal magnetic load directly coupled to physical `L_S3` modify the N3 fourth-regeneration record while preserving the N2 record?
- Physical canonical bridge is retained exactly: `R_S=3 ohm`, `L_S3=0.5 pH`; the canonical BVM/QB files are not modified.
- Added only inside an experimental BVM clone: `L_AUX=10 pH`, `R_AUX=20 ohm`, and `K_AUX L_S3 L_AUX K`, with `M=K*sqrt(0.5*10) pH`.
- Fixed M values are exactly `0.00`, `0.25`, `0.50`, and `0.75 pH`; K is derived and recorded exactly. No negative M, M>0.75, other L/R/C, JJ, source, bias, resonator, PTL, split-LS3 or timestep case.
- M=0.00 is the no-op gate and is solved first. Positive M cases are materialized only after that gate passes. N1/N4 are materialized only for the smallest positive M whose fixed pair mechanically gives N2=2 and N3=3.
- `.tran 0.1p 200p`; actual stored grid only. P(...) is raw radians; rad/(2*pi) turns are navigation only and not literal SFQ counts.

## Authorized cases

1. `LS3_MUTUAL_M0P00_0011`
2. `LS3_MUTUAL_M0P00_0111`
3. `LS3_MUTUAL_M0P25_0011`
4. `LS3_MUTUAL_M0P25_0111`
5. `LS3_MUTUAL_M0P50_0011`
6. `LS3_MUTUAL_M0P50_0111`
7. `LS3_MUTUAL_M0P75_0011`
8. `LS3_MUTUAL_M0P75_0111`
9–10. Conditional smallest-positive-M pair × `0001`,`1111` only after the registered mechanical selective gate.

Maximum new physical solves: 10. The M=0 pair must reproduce the canonical N2=2/N3=4 mapping and be auxiliary-quiet before positive cases run.

Canonical bridge audit: `{"0011": "PASS", "0111": "PASS"}`.

Final state: `EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW`; no scientific mechanism or winner conclusion is assigned.
