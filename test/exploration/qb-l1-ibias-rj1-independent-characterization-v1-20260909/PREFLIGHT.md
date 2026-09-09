# PREFLIGHT — qb-l1-ibias-rj1-independent-characterization-v1-20260909

This experiment is governed by docs/EXPERIMENT_CONTRACT.md.

- Role: `Experimental Operator + Evidence Packager`
- Workflow: `PRE-REGISTER -> PREFLIGHT -> 12 PHYSICAL SOLVES -> MECHANICAL QA -> V2.1 VISUALIZATION -> EVIDENCE PACKAGE -> COMMIT -> STOP`
- HEAD at this preflight: `f61bcc97d5bd82f499f9e957d2850e39889bda12`
- Exact new physical solves: `12`
- Reused physical solves: `0` (five unique historical references, hash matched)
- Combination interventions: `FORBIDDEN`
- Scientific analysis: `NOT PERFORMED`
- Scientific authorization: `NOT_GRANTED`
- Solver invocation during preparation: `0`
- Raw mutation during preparation: `0`

## Registered families

- L1: `1.2, 1.4, 1.6, 1.8 pH`; reuse `1.9, 2.0, 2.1 pH`
- IBias: `230, 240, 260, 270 uA`; reuse `250 uA`
- RJ1: `8, 10, 14, 16 ohm`; reuse `12, 12.5, 13 ohm`

## Reuse gate

Historical deck/raw/source hashes, topology, stimulus, timing, solver identity,
non-target parameters and probe coverage were checked by `analysis/prepare_experiment.py`.
The copied reference bytes are not new physical solves.

## Stop rules

No retry, tuning, range shrink, extra point, combination run, ranking, winner,
mechanism interpretation or automatic follow-up is authorized. Final state is
`EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW`.
