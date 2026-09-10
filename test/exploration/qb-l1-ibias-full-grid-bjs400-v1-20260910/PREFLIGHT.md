# BJS400 ARRAY L1 x IBias complete coarse grid — PREFLIGHT

This experiment is governed by docs/EXPERIMENT_CONTRACT.md.

## Identity and authority

- Experiment: `qb-l1-ibias-full-grid-bjs400-v1-20260910`
- Preflight HEAD: `017a36c3735d34f4e11acb1d1ea69582204aa962`
- Preregistration HEAD: `59d60367b1572994bda195624b90286531d962cd`
- Physical/stimulus authority: `test/exploration/qb-bjs400-array-population-single-matched-v1-20260909`
- Historical interaction reuse authority: `test/exploration/qb-l1-ibias-interaction-bjs400-v1-20260909`
- Solver: `build/josim-cli`; SHA-256 `48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2`
- BJS source: `inputs/BQ_parameterized_bjs400.cir`; area=4; Ic=400uA.
- The older no-history stimulus is not used.

## Exact registered grid

- L1: 1.2, 1.4, 1.6, 2.0pH.
- IBias: 250, 260, 270uA.
- Final-read masks only: 0001 and 0011; b3b2b1b0 = BVM1/BVM2/BVM3/BVM4.
- Logical cases: exactly 4 x 3 x 2 = 24.
- Historical immutable reuse: exactly 14.
- New physical solves: exactly 10, with only these settings: L1P12_IB260, L1P12_IB270, L1P14_IB260, L1P14_IB270, L1P16_IB270, each mask pair.
- Unauthorized extra solves: 0; no other masks, SINGLE, sweep, retry or follow-up.

## Frozen fixture and history

- ARRAY: four BVMs -> COMMON_SL -> eight-JJ JSL -> QB -> six-stage JTL -> 10ohm terminal.
- RJ1=12ohm; all BVM, COMMON_SL, JSL, QB, BJ1, L2, BJ2, RJ2, L3, JTL, load, models and solver values frozen.
- History: WRITE0 -> ZERO_STATE_READ_CONTROL -> WRITE1 -> SETTLE -> mask-selective FINAL READ -> TAIL.
- 0–50ps idle; WRITE0 50–61ps; idle 61–70ps; zero-state read 70–81ps; idle 81–90ps; WRITE1 90–101ps; SETTLE 101–110ps; FINAL READ 110–121ps; TAIL 121–200ps.
- Controls: 100uA amplitude; 1ps rise/fall; 9ps plateau; `.tran 0.1p 200p`; expected stored timestamps 0–199.9ps.

## Registered mechanical metrics

- Raw P values remain radians. Continuous unwrap followed by division by 2π is display/diagnostic only; it is not an SFQ count or event classifier.
- BJ1/BJ2: first +0.5-turn timing diagnostic, max continuous relative phase and final continuous relative phase; baseline [101,110)ps, post-read [110,200)ps.
- Currents: extrema for I(L1), I(L2), I(RJ1), I(B_JSL8); signed actual-grid areas for I(B_JSL8) and I(LIN) in [110,121)ps and [121,200)ps.
- Optional V(QBIN) and V(COMMON_SL) extrema; missing V(IB|XBQ1) remains UNKNOWN if absent.
- BJ1 voltage positive/negative area and RJ1 dissipated energy use actual stored-grid trapezoids in FINAL READ [110,121)ps.
- 0011/0001 ratios: I(B_JSL8) max-absolute peak, EARLY_READ signed area and I(LIN) EARLY_READ signed area. Denominator tolerance is 1e-12A for peak and 1e-18A·s or <1% of absolute area for signed areas; otherwise UNKNOWN.
- Pre-switch navigation proxy: 0011/0001 signed-area ratio in [110,114.5)ps for I(B_JSL8) and I(LIN), labeled MECHANICAL_PRE_SWITCH_PROXY; not population scaling proof.

## Output and interpretation ceiling

- New raw outputs: `runs/<run_id>/raw.csv`; decks, metadata and logs remain immutable.
- Mechanical QA: `qa/raw_qa.json`, `qa/deck_diff_qa.json`, `qa/provenance.json`, `qa/execution_summary.json`, `qa/transformation_registry.json`, `mechanical_summary.json`.
- Visualization: exactly 30 standalone whole-run pages and exactly two full-grid comparison pages; no focused pages, heatmaps, dashboards or permanent comparison CSV.
- Package: `handoff/qb-l1-ibias-full-grid-bjs400-v1-20260910_raw_handoff.zip`; detached PACKAGE_QA remains outside ZIP.
- Scientific interpretation: NOT_PERFORMED. No optimum, regime, mechanism, event/SFQ count, Gate, ranking, or follow-up is authorized.

## Automatic preflight result: `PASS`

- Historical reuse comparability: `PASS`.
- New deck checks: `PASS`.
- Physical execution has not started at this preflight record.
