# F4_R11_T100

- family: `four_bvm`; RJ1: `11.0 ohm`; timestep: `0.1 ps`; state: `collective`
- effective raw: `test/exploration/bvm-qb-rj1-timestep-robustness-v1-20260903/runs/F4_R11_T100/attempt-03/raw/run-01.csv` (`attempt-03`)
- artifact status: **VALID**

## Observed / derived key data

- actual grid: `0.100000 ps`, saved `45.000..199.900 ps`, interpolation: none
- BJ2 READ1 net trajectory: `3.999584 turn`; complete segments: `1`; clean separated events: `0`
- BJ2 continuous multi-turn status in READ1: `True`
- BJ2 settling tail: mean V `-0.000002 mV`, RMS V `0.000147 mV`, phase p2p `0.000166 turn`, tail complete segments `0`
- four-BVM branch observation: `CONTINUOUS_MULTI_TURN_BRANCH`; BJ1 net `4.000865 turn`; BJ2 net `3.999584 turn`
- BJ2 principal same-segment phase/area: phase `3.983402 turn`, area `3.983964 Phi0`, onset `110.600 ps`, continuous segment `True`
- late complete segments after principal: `0`; JTL1/JTL6 B02 READ1 net trajectories: `4.000085` / `4.000000` turn

## Interpretation boundary

- **Observed:** values above are derived from the immutable raw using exact stored samples and same-JJ phase/area segments.
- **Not claimed:** a net four/five-turn trajectory is not four/five SFQ events; local phase is not automatically transported reception; this run does not prove canonical BVM compatibility or convergence.
