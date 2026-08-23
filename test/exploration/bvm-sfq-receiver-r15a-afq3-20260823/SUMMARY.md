# R15-A summary

- **Tier:** Exploration
- **Baseline HEAD:** `3113a4640c74e515cc6fe991f1c37752b168e8c2`
- **Nominal point:** AFQ-3, unchanged from preregistration
- **Verdict:** `PRECHECK_NO_GO`
- **Stop location:** Gate 0, invalid shared three-coil mutual-inductance matrix
- **Scientific cases completed:** 0/4
- **Raw CSV produced:** none
- **Canonical BVM modified:** no
- **DCSFQ backend modified:** no

The nominal block `[L_Q,L_F,L_CTL]` has normalized matrix
`[[1,.9,0],[.9,1,.9],[0,.9,1]]`, determinant `-0.62`, and minimum eigenvalue
`-0.2727922`. The failed point is not interpretable as a physical detector,
active-gain, or DCSFQ result.

See `analysis/GATE0_4_PRECHECK.md` and `analysis/R15A_REPORT.md` for the
complete Gate 0–4 boundary and the retained diagnostic log.
