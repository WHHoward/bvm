# S1B_R11_T025_S0

- family: `single_bvm_protection`; RJ1: `11.0 ohm`; timestep: `0.025 ps`; state: `S0`
- effective raw: `test/exploration/bvm-qb-rj1-timestep-robustness-v1-20260903/runs/S1B_R11_T025_S0/raw/run-01.csv` (`run-01`)
- artifact status: **VALID**

## Observed / derived key data

- actual grid: `0.025000 ps`, saved `0.000..199.975 ps`, interpolation: none
- BJ2 READ1 net trajectory: `0.000011 turn`; complete segments: `0`; clean separated events: `0`
- BJ2 continuous multi-turn status in READ1: `False`
- BJ2 settling tail: mean V `-0.000000 mV`, RMS V `0.000007 mV`, phase p2p `0.000008 turn`, tail complete segments `0`

## Single-BVM protection

- protection verdict: `S0_NO_STRICT_TRIGGER`; S0 false/extra trigger flag: `False`
- BJ2 principal phase/area: `n/a turn` / `n/a Phi0`; JTL B02 read complete counts: `[0, 0, 0, 0, 0, 0]`

## Interpretation boundary

- **Observed:** values above are derived from the immutable raw using exact stored samples and same-JJ phase/area segments.
- **Not claimed:** a net four/five-turn trajectory is not four/five SFQ events; local phase is not automatically transported reception; this run does not prove canonical BVM compatibility or convergence.
