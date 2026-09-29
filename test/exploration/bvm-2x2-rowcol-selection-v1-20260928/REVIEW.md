# Static implementation review

Scope: platform construction only. No JoSIM invocation or physical run occurred.

## Adversarial checks

- **No-op / source count:** the generated INDEPENDENT deck has 12 cell-level
  current sources (four each for WL/BL/SE); SHARED has exactly six sources
  (two each). A static test checks the rendered source count and nodes.
- **Wrong topology / accidental short:** SHARED connects each row WL to its
  two cells and each column BL/SE to its two cells. WL, BL, and SE node sets
  are pairwise disjoint; BL_C1 is not SE_C1. Four outputs each terminate in
  their own 2 Ω resistor and are not merged.
- **Wrong bit order / wrong branch:** leftmost ROW bit means R1 and leftmost
  COL bit means C1. For 10/10 the renderer reports R1C1 active, R1C2/R2C1
  half-selected, R2C2 unselected; for 11/11 it reports all four active.
  Tests compare each generated final WL/SE PWL to the corresponding row/column
  bit and require every final BL source to be zero.
- **Initial-state leakage:** tests verify WRITE0, READ0, and WRITE1 are present
  on all four cells independent of row/column selection; the bit strings gate
  FINAL READ only.
- **Stale component / pin mapping:** all five direct-include source hashes
  match the registered SHA-256 values. BVM pin order is `WL BL SE SL`; QB,
  sJTL, and CB are each `IN OUT`. The four generated chains use the same
  topology and fixed load.
- **Weak plot oracle:** a mocked raw fixture exercises the real classic
  `josim-plot2.py` page generator and raw/plot QA without invoking JoSIM.
- **Overclaim:** the platform reports arithmetic and QA only. There are no raw
  results from this build pass and no scientific interpretation.

## Remaining unverified items

- JoSIM has not parsed or solved these rendered decks in this task, by design.
- The 100 µA independent and 200 µA shared settings are candidate source
  amplitudes. Their loaded branch-current distributions and physical responses
  remain unmeasured until a user manually runs a chosen preset.
- Timestep sensitivity, model behavior under shared loads, and the array's
  functional read/write behavior are not established by static tests.

## Acceptance execution

- `python3 -m unittest discover -s tests -v`: 10/10 passed.
- `./try.sh --dry-run`: INDEPENDENT 10/10 passed; 12 cell-level sources,
  active R1C1, half-select R1C2/R2C1, unselected R2C2.
- `./try.sh --preset B_SHARED_10_10 --dry-run`: SHARED 10/10 passed; exactly
  six distinct line sources, one per row-WL/column-BL/column-SE line, same
  active/half-select/unselected mapping.
- `./try.sh --preset C_SHARED_11_11 --dry-run`: SHARED 11/11 passed; the four
  row/column intersections are listed active.
- All three previews reported `solver_invoked=false`, this-dry-run solve count
  0, static QA PASS, and left `runs/` absent.
- A separate mocked-runner test exercised artifact closure and the classic
  plot renderer on synthetic temporary data. It did not invoke JoSIM or create
  repository run evidence.
- Python compile, `bash -n try.sh`, and `git diff --check`: PASS.
- Physical solve count for this platform-build task: **0**.

## Incremental CELL-SE platform review

Base HEAD: `3d12e5c5252f02748f880f09027e70c8d0cfc3d8`.

### Adversarial probes

- **Wrong-branch/default:** old A/B/C presets omit both new fields. The loader
  supplies `SHARED_COLUMN/COLUMN`, and byte-for-byte rerender checks against
  A001–A003 `actual_deck.cir` and `stimulus.inc` pass.
- **Name-only fake independence:** D0/D1 each render four distinct
  `SE_RxCy` nodes and four source lines; all four exact `XBVM_*` port lines
  connect to the corresponding cell node. Static QA parses the eight source
  endpoints and checks the source/node map against topology metadata.
- **D0/D1 coupling:** their deck and all preparation-stage PWLs are identical.
  The sole PWL delta is the FINAL_READ segment on `I_SE_R2C1`: 100 µA for D0,
  zero for D1. D0 final SE is R1C1+R2C1 by column; D1 is R1C1 only.
- **Stale/raw overwrite:** all three historic manifest raw hashes still match,
  every existing package reopens with valid CRC and matching detached QA SHA,
  and the runner's temporary allocation test advances past existing run IDs
  without touching their directories.
- **Canonical source drift:** all five canonical source SHA-256 values are
  checked against frozen constants for both D presets.

### Residual uncertainty

- Static PWL values are ideal current-source setpoints only. Actual source and
  BVM branch-current sharing requires a future user-authorized physical solve.
- JoSIM parsing/solving was intentionally not performed. No physical outcome
  or selection claim is made.
- The pre-existing mocked-runner test was included once in an earlier full
  suite and generated a zero-filled synthetic CSV inside a disposable
  `TemporaryDirectory`; cleanup removed it. No synthetic file entered
  `runs/`, Git, or the preserved historical evidence. The final 19-test pass
  omitted that mock test per the no-fake-run-artifact boundary.

### Incremental acceptance

- 19 static/regression tests passed after the final code edits; the one excluded
  test is the temporary synthetic-raw mocked-runner test described above.
- D0/D1 dry-runs: topology/probe/static QA PASS; no run directory, solver call,
  or raw created.
- Legacy A/B/C regression and historic run deck/stimulus snapshot checks: PASS.
- Physical solve count for this platform-only extension: **0**.

## Optional half-selected SECOND_READ review

Base HEAD: `f554cbc7aff90e9eb3a9cd8a07d99444ac1ea503`.

### Adversarial probes

- **Legacy no-op/stale artifact:** all A001–A006 run snapshots rerender to the
  exact saved `actual_deck.cir` and `stimulus.inc` with SECOND_READ absent or
  disabled. The A001–A006 plus existing handoff SHA aggregate is unchanged.
- **Wrong SE gate/coupling:** the second-read stage is accepted only with
  effective CELL SE nodes. E0/E1 both route second-read SE exclusively to
  R2C1, independent of the first-read `SE_GATE_MODE`.
- **Wrong row/column order:** `SECOND_ROW_BITS=01` selects R2 and
  `SECOND_COL_BITS=10` selects C1. Tests verify all four per-cell source
  settings and the eight unchanged source/node connections.
- **First-read mismatch/STOP tail:** E0 PWL knots and source nodes before
  170 ps match A005; E1 matches A006. The only E0/E1 PWL difference is
  `I_SE_R2C1` in FINAL_READ. Both have identical second-read PWL and STOP.
- **Window collapse/interpolation:** the analyzer registers FINAL_READ,
  recovery, SECOND_READ, and POST_SECOND_READ separately with half-open
  actual-grid windows; the combined 110–300 ps read area is not emitted.
  Focused classic plots use exact stored row indices without resampling.

### Residual uncertainty

- JoSIM was not invoked. Actual BVM branch-current sharing and the physical
  consequence of the half-select remain unknown.
- No physical interpretation or E0/E1 outcome is asserted.

### Incremental acceptance

- 26 static/history tests passed; the synthetic-raw mock-runner test was
  excluded.
- Default and A/B/C/D0/D1/E0/E1 shell dry-runs: PASS, static QA PASS, and no
  run directory or raw file created.
- Physical solve count for this task: **0**.

## Optional SECOND_READ platform review

Base HEAD: `f554cbc7aff90e9eb3a9cd8a07d99444ac1ea503`.

### Adversarial probes

- **Legacy no-op:** A001–A006 saved decks and `stimulus.inc` rerender byte for
  byte with SECOND_READ defaulted off. No historical raw, run manifest, QA, or
  handoff package was changed.
- **Wrong gate coupling:** E0/E1 second-read source values are derived only from
  SECOND_ROW_BITS AND SECOND_COL_BITS. Their second-read source map is identical
  although first-read SE_GATE_MODE differs.
- **Wrong cell/bit order:** E0/E1 use row bits 01 and column bits 10, enabling
  second-read SE only on R2C1. Tests check all four cell source values and
  source/node assignments; total source count remains eight.
- **Stale or broad window:** E0's PWL prefix through 170 ps matches A005; E1's
  matches A006. Comparisons omit the second stage and STOP endpoint. Metric
  windows are FINAL_READ [110,121), recovery [121,170), SECOND_READ [170,181),
  and POST_SECOND_READ [181,300); no 110–300 aggregate read window is emitted.
- **Raw/probe sufficiency:** all current core probes remain registered;
  R2C1 window pages include actual WL/BL/SE branch currents, BVM state,
  SL/QB_OUT/sJTL_OUT/VOUT, and downstream JJ P/V traces.

### Residual uncertainty

- JoSIM parsing/solving and actual branch-current sharing were not tested.
  E0/E1 source amplitudes are PWL setpoints, not measured currents.
- The second read's physical response is unknown until the user manually runs
  a selected preset. No physical or scientific conclusion is made.

### Incremental acceptance

- Static/history regression and E0/E1 dry-run results are recorded after the
  final implementation; the mocked-runner synthetic-raw test was not run.
- Physical solve count for this platform-only task: **0**.

## Authorized A/B/C batch — implementation adversarial review

Parent HEAD: 5447f08ebbe367dd9d4f2ff2f072fa17c2cc1aac.

### Tested failure hypotheses

- **Legacy no-op/default drift:** rerender saved A001–A009 snapshots after filling only absent compatibility defaults; actual_deck.cir and stimulus.inc remain byte-identical. RESULT: PASS.
- **Wrong cell/bit order:** A's ROW_BITS=11/COL_BITS=10 selects R1C1 and R2C1; SECOND_ROW_BITS=10/SECOND_COL_BITS=10 selects R1C1 only. The source-stage matrix is checked on all eight actual current-source nodes. RESULT: PASS.
- **Fake shared write / hidden independent line:** C still has exactly 2 WL + 2 BL + 4 SE sources on the canonical shared row/column nodes. Target 1 drives only WL_R1 and BL_C1; target 2 only WL_R2 and BL_C2. Per-cell expected WL-only, BL-only, target, and unselected values are statically asserted. RESULT: PASS.
- **Wrong selective timing or overlap:** C's PWL source knots are 90/91/100/101 ps and 120/121/130/131 ps; FINAL_READ is 170–181 ps. Static validation rejects overlaps and STOP truncation. RESULT: PASS.
- **Incomplete output window / stale read metric:** terminal and boundary arithmetic is separately registered for first/second read response; C's full response is 170–300 ps. Peak timestamps and signed areas use actual stored rows; no single combined A read-area is emitted. RESULT: PASS at static-spec level.
- **Weak event oracle / overclaim:** no pulse/SFQ threshold or classifier was registered. Dry-run, local maxima, phase turns, and voltage area will not be called an event count. RESULT: PASS for the interpretation boundary.

### Static residuals before solves

- The measured branch-current distribution and physical effects of row/column half-selection are unknown until the authorized raw runs exist.
- Whether the intended mixed state is physically obtained in C is unknown; only source/topology mapping has passed static validation.
- Pulse/SFQ event classification and timestep convergence are not authorized/registered and remain UNKNOWN.

### Acceptance

- 29 static/history tests passed, excluding the test that writes a temporary synthetic raw CSV.
- Existing A/B/C/D/E and new A/B/C preset dry-runs report static QA PASS and zero solve count.
- A/B/C exact PWL and four BVM shared input-node lines were manually inspected from verbose dry-runs.
- No JoSIM solve was run during this implementation review.

## Authorized A/B/C batch — mechanical and numerical review

- A010, A011, and A012 each report artifact VALID and raw/static/stimulus/plot/provenance/mechanical QA PASS; each has exactly one physical solve and its raw SHA agrees with result.json and experiment_manifest.json.
- A010/A009 first-response overlay used 6,000 exact common stored timestamps over [110,170) ps. A010/A011/A012 output overlay used 24,999 exact common stored timestamps over [0,250) ps. Both comparison QA records PASS; no interpolation/resampling.
- Independent Decimal-time arithmetic audit is analysis/independent_batch_arithmetic_v2.json. It verified raw SHA before/after, per-cell branch currents, response-window output peak times/areas, and same-JJ phase/voltage arithmetic directly from raw.
- Runner-vs-independent audit: zero output peak-time mismatches; maximum VOUT-area arithmetic differences 4.25e-34, 2.62e-31, 9.76e-32 V·s for A010/A011/A012; max same-JJ phase-delta discrepancies below 4.8e-13 rad.
- The initial independent arithmetic serialization lacked an explicit cell key on output rows. The numeric values were unchanged; it is preserved as independent_batch_arithmetic.json and explicitly superseded by v2 with cell identity. All raw hashes remained unchanged.
- C's static and actual PWLs retain exactly shared WL_R1/WL_R2 and BL_C1/BL_C2 buses plus four cell-SE sources. Raw branch-current arithmetic records nonzero current on WL-only, BL-only, and nominally unselected branches during the selective writes; no logical-state classification is made.
- No pulse/SFQ event threshold or classifier was registered, and no SCIENTIFIC_REVIEW_AUTHORIZED token was supplied. Event count, logical storage verdict, physical Gate status, and mechanism interpretation remain NOT PERFORMED; timestep convergence remains UNKNOWN.
- Exactly three registered physical solves were run; no follow-up was performed.
