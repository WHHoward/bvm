# JM2-connected Quick — numerical and adversarial review

## Numerical checks

- artifact/preflight status: `PASS`
- every A/B pair exact time grid, no interpolation: `PASS`
- phase unit: `P(...)` retained as rad; derived turns use `continuous_unwrap(rad)/(2*pi)`: `PASS`
- same-JJ phase/voltage-area pairing: direct P/V labels and identical windows: `PASS`
- voltage-area integration: trapezoid on each raw's actual stored time column: `PASS`
- QB KCL: shared `bvmtools.kcl` residuals recorded before current-partition interpretation: `PASS`
- independent CSV recheck: 4 connected raws have 1999 samples; all four A/B grids are exact; JM2 READ/RESPONSE phase-area residuals reproduce `metrics.json` to machine precision: `PASS`
- independent S1-J full-window KCL recheck: maximum absolute residual is 0.000110 µA across the four declared equations: `PASS`

## Adversarial checks

- stale or wrong-branch raw: each new raw is tied to its copied deck, command, hash and post-run probe QA.
- no-op topology change: variant diff is required to be exactly one `L_M2` node change; setup QA is retained.
- hidden A-side rerun: A references are immutable corrected baseline paths; no A-side command is issued by this task.
- missing A-side L_M probes: explicitly reported as unavailable; no zeros, interpolation or fabricated comparison.
- phase overclaim: no phase displacement, voltage peak, or onset sample count is called an SFQ count.
- convergence overclaim: `.tran 0.1p 200p` is a fixed Quick only; no timestep convergence is claimed.
- execution wrapper: the first `run.sh` returned 1 only because preflight indexed a nonexistent `compare_stimuli` field; all four solver commands returned 0, the preflight code was corrected without rerunning raw, and corrected preflight returned 0.
- scientific status: exploratory characterization only; user review remains required.
