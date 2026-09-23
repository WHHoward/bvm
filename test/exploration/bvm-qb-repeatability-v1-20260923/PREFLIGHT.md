# BVM-QB repeatability platform — preflight

This experiment is governed by docs/EXPERIMENT_CONTRACT.md.

Status: `PLATFORM BUILD / AWAITING MACHINE PREFLIGHT`
Parent HEAD: `01ea983cbf56d10083124c834a8c99097f41aa25`
Study phase: `EXPLORATORY`
Frozen A–E matrix SHA-256: `54595542217bb15d5107c3367b11a393afb1cb35510d214478fba84a59574156`

## Question and scope

Build a reusable environment-driven runner for the existing BVM array →
COMMON_SL/JSL1…JSL8 → QB → JTL1…JTL6 → R_TERM path. This turn authorizes only
the exact A–E smoke/regression matrix in `REGRESSION_MATRIX.json` (five solves
total), and no frequency sweep, parameter optimization, topology extension,
or automatic follow-up.

The A/B/C checks are descriptive compatibility against the named, hash-bound
Phase A raw references over the exact shared stored-grid prefix `[0,240)` ps;
the historical files' final sample is 239.9 ps. The last READ pulse ends at
201 ps and the remainder of the historical raw tail is also compared. They are
not scientific acceptance limits. D checks
that a single read is followed by a 100 ps zero-input recovery trace; it does
not define recovery or re-arm success. E checks that all three registered
rewrite/read states are stimulated and covered by the computed STOP.

## Frozen topology and sources

- BVM netlist rendering and source inventory reuse the one-shot tuning
  platform helpers; experiment-local BVM/QB/top templates and each rendered
  run snapshot are hashed.
- The BVM→JSL→QB→six-cell-JTL→10 Ω R_TERM chain is unchanged.
- Candidate values are independently declared for QB_1X1, QB_2X1 and
  QB_3X1 in `candidate_profiles.json`; each run snapshot expands every value.
- JJ model: `circuits/models/jjmit.cir`, SHA-256
  `19862d1fd1f1f44dfa1523847d8d3b5e2594a6c5da8fdd80144b449e5312a336`.
- JTL model: `test/exploration/bvm-qb-l1-l3-bj2-targeted-closure-v1-20260914/inputs/jtl2.cir`,
  SHA-256 `ffd31f8eda2a86ca0133342be1ce678831b7237a53911eda046d2bff8454855a`.
- Reused BVM/QB renderer: one-shot `scripts/run_candidate.py`, SHA-256
  `d46c485f7c952a615e014c47323194b3d2a7415de4e37ae8d23c1b3c527b0737`.
- Reused array/mask helper: one-shot `scripts/fan_in.py`, SHA-256
  `d4b48b40626aa613e1a9197f6aaa3093b3210c586689d0ef8e77c1dd243a1cf4`.
- Plotter: `scripts/josim-plot2.py`, SHA-256
  `0aaf0b4bfd148e073d318c9a0762ec13995045abd88cad28336fb8128c33a1d6`.
- Solver: `build/josim-cli`, SHA-256
  `48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2`,
  version `v2.7.2837d13 compiled on May 30 2026 at 20:37:57`.

## Stimulus and time bounds

- REPEAT_READ: legacy WRITE0 (50–61 ps), CONTROL (70–81 ps), WRITE1 (90–101
  ps); READ starts 110, 130, 150, 170, 190 ps for A/B/C. Five 11 ps reads,
  1 ps rise/fall, 100 µA, no rewrite after WRITE1.
- RECOVERY_PROBE: same prefix, one READ at 110 ps ending at 121 ps; all sources
  remain zero thereafter; exact recovery tail 100 ps; STOP=221 ps.
- REWRITE_READ: sequence 00,01,11; each state resets all cells, writes the
  target state, then reads it. Reset starts at 50, 120, 190 ps; READ starts at
  95, 165, 235 ps and ends at 106, 176, 246 ps. The actual READ cadence is
  70 ps, so the automatic tail is max(40, 2×70)=140 ps; STOP=386 ps.
- DT=`0.1p`; repeated-read STOP is computed from the final pulse endpoint plus
  `max(40 ps, 2×READ_PERIOD)`; preflight rejects any plan where STOP does not
  extend strictly past the last stimulus point or last terminal search bound.
- Cycle regions are `[READ_i, READ_(i+1))`; the last region ends at actual
  simulation STOP. PRE/READ/POST/NEXT_PRE windows are recorded and validated
  non-overlapping using the actual read schedule.
- BJ2/terminal voltage candidates use explicit navigation-only thresholds
  from USER_CASE.env; both clustering gaps initially use the historical
  0.5 ps navigation setting; candidate search latency is `[0,25] ps`. The
  25 ps upper bound contains the approximately 17.5 ps first-candidate peak spacing measured
  descriptively on the three hash-bound historical Phase-A references. It is
  not a physical event criterion.

## Exact authorized matrix

1. `REG_A_QB2X1_N1`: QB_2X1, 2 BVM, MASK=01, REPEAT_READ, 20 ps, 5 reads.
2. `REG_B_QB2X1_N2`: QB_2X1, 2 BVM, MASK=11, REPEAT_READ, 20 ps, 5 reads.
3. `REG_C_QB3X1_N3`: QB_3X1, 3 BVM, MASK=111, REPEAT_READ, 20 ps, 5 reads.
4. `REG_D_QB2X1_RECOVERY`: QB_2X1, MASK=11, RECOVERY_PROBE, one read,
   100 ps recovery tail.
5. `REG_E_QB2X1_REWRITE_SMOKE`: QB_2X1, MASK=11, REWRITE_READ,
   STATE_SEQUENCE=00,01,11, STATE_INTERVAL=70 ps.

## Required evidence and interpretation ceiling

Each run records expanded config, exact stimulus, rendered deck/source
snapshots, Git HEAD/dirty status, solver identity, raw SHA-256, and analysis
and plot provenance. Raw analysis uses actual stored times only. BJ1/BJ2 phase
and voltage-area values use the same junction, direction, stored-grid
endpoints, and half-open cycle region.

Candidate attribution is a navigation report only. It must be chronological,
one-to-one, never assign a terminal candidate twice, and emit `AMBIGUOUS`
where uniqueness is absent. Phase turns and candidate matches are not SFQ
counts. For each unique BJ2→terminal candidate pair, the platform also records
the ordered B01/B02 voltage-candidate path through all six JTL stages; missing,
shared, or competing stage candidates remain incomplete/ambiguous. No physical mechanism, recovery threshold, state-retention success,
maximum frequency, or candidate ranking is authorized by these runs.

Visualization follows the one-shot platform: per-run `plots/review.html`,
classic `josim-plot2.py` (`sep_comb`, dark, `-j 2pi`) grouped plots, exact-grid
READ-window subsets with provenance sidecars, a run index, and a compact
regression comparison page. All raw files remain immutable.

## Machine gate

`scripts/preflight.py` must pass the exact five-case matrix, resolved candidate
parameters, generated stimulus/decks, required probes, complete computed STOP,
and current solver/source hashes before the first solve. Only after PASS will
the runner execute A–E once each. No retry or extra case is automatic.

Software-only numerical semantics are recorded in
`analysis/PLATFORM_NUMERICAL_QA.json`; those checks use no physical solve and do
not establish timestep convergence or physical thresholds.
