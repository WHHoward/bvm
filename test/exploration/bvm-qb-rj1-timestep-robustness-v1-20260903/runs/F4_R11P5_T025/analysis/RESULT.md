# F4_R11P5_T025

- family: `four_bvm`; RJ1: `11.5 ohm`; timestep: `0.025 ps`; state: `collective`
- effective raw: `test/exploration/bvm-qb-rj1-timestep-robustness-v1-20260903/runs/F4_R11P5_T025/attempt-03/raw/run-01.csv` (`attempt-03`)
- artifact status: **VALID**

## Observed / derived key data

- actual grid: `0.025000 ps`, saved `45.000..199.975 ps`, interpolation: none
- BJ2 READ1 net trajectory: `4.999000 turn`; complete segments: `1`; clean separated events: `0`
- BJ2 continuous multi-turn status in READ1: `True`
- BJ2 settling tail: mean V `0.000022 mV`, RMS V `0.000196 mV`, phase p2p `0.000411 turn`, tail complete segments `0`
- four-BVM branch observation: `CONTINUOUS_MULTI_TURN_BRANCH`; BJ1 net `5.002935 turn`; BJ2 net `4.999000 turn`
- BJ2 principal same-segment phase/area: phase `4.023387 turn`, area `4.023413 Phi0`, onset `110.625 ps`, continuous segment `True`
- late complete segments after principal: `0`; JTL1/JTL6 B02 READ1 net trajectories: `5.000153` / `5.000000` turn

## Interpretation boundary

- **Observed:** values above are derived from the immutable raw using exact stored samples and same-JJ phase/area segments.
- **Not claimed:** a net four/five-turn trajectory is not four/five SFQ events; local phase is not automatically transported reception; this run does not prove canonical BVM compatibility or convergence.
