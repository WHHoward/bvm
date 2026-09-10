# Selected-mask population scaling — PREFLIGHT

This experiment is governed by docs/EXPERIMENT_CONTRACT.md.

- Experiment: `bvm-population-scaling-rj2p12-l1p14-l2p20-ib260-rj32-bjs400-v1-20260910`
- Preflight HEAD: `1acdfe30fedce2e24706d8721ccf5919fd16b2f0`
- Frozen candidate: RJ2=12ohm; canonical `.tran=0.1p 200p`.
- Generalized oracle regression: required before new runs; code SHA-256 `4d39bc457e0ea010ac9f312dbc1c40b6e65dea123865608f4ad066a05773e860`.
- Only the FINAL READ BVM mask changes. L1/L2/RJ1/IBias/BJS/BJ1/BJ2/L3/load/JTL/history/timing remain unchanged.

## Exact matrix

- Immutable reuse: masks `0001` and `0011` from the latest RJ2=12 timestep candidate.
- New physical solves: exactly masks `0110`, `1100`, `1110`, `0111`, `1111`.
- Total: 7 logical population cases, 2 reuse cases and exactly 5 new solves; no other masks and no finer timestep.

## Frozen protocol

- IDLE 0–50ps; WRITE0 50–61ps; IDLE 61–70ps; ZERO_STATE_READ_CONTROL 70–81ps; IDLE 81–90ps; WRITE1 90–101ps; SETTLE 101–110ps; mask-selective FINAL READ 110–121ps; TAIL 121–200ps.
- Amplitude 100uA, 1ps rise/fall, 9ps plateau; `.tran 0.1p 200p`.
- Bit order b3b2b1b0=BVM1/BVM2/BVM3/BVM4.

## Evidence ceiling

- Generalized response multiplicity requires cumulative baseline phase landmarks, direct stored-sample voltage clusters, ordered JTL progression and valley-segmented terminal pulses for each response.
- Hamming weight is used only after oracle classification; it is never passed to the response detector as an expected count.
- No phase, pulse area, terminal area, current peak or L1 crossing is an SFQ count.

- Exact reuse: `PASS`; deck checks: `PASS`.
- Physical execution has not started at preflight.
