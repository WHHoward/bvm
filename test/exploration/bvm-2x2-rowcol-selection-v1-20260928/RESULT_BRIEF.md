# 2×2 shared-row/column A/B/C batch — executor result

Status: `EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW`  
Physical solve count: **3** (A010, A011, A012), serially allocated.  
Scientific interpretation / event-count classification: **NOT PERFORMED**.

## Artifact status

| Run | Registered condition | Artifact | Raw rows / range | Raw SHA-256 |
|---|---|---|---|---|
| A010_SHARED_R11_C10 | A: same-column pair; second read R1C1 | VALID; raw, static, stimulus, plot, provenance, mechanical QA PASS | 24,999 / 0–249.99 ps | `a9687368e8cf89ff18dc99c353cc4e001a241cc2d5780335f57fcc7786bdfadf` |
| A011_SHARED_R11_C11 | B: all four cells; one read | VALID; raw, static, stimulus, plot, provenance, mechanical QA PASS | 24,999 / 0–249.99 ps | `b737b260d9854bb0e9a60dcce4d11024673c40a236b641667b0e5d4243241a44` |
| A012_SHARED_R11_C11 | C: sequential shared-bus write, then four-cell read | VALID; raw, static, stimulus, plot, provenance, mechanical QA PASS | 29,999 / 0–299.99 ps | `f20ca4a01bd79bc12e521c5171858c7a10b0f8009abe87270cbf1a4a59d2d9be` |

Canonical source SHA values are unchanged from experiment.yaml. No A001–A009 run or raw was modified. Each new run has its own deck, effective config snapshots, full stdout/stderr/log, raw, manifests and ten classic plot pages. Actual stored intervals ranged from 0.01 to 0.02 ps in these runs; no timestep convergence was run.

## OBSERVED raw and DERIVED arithmetic

All values below are simulator output/arithmetic, not hardware measurements. VOUT peak time and signed area use the registered actual-grid response windows. Full per-cell current and phase/voltage tables are in analysis/independent_batch_arithmetic_v2.json.

| Run / response window | Cell(s) | VOUT positive maximum | Time | Signed VOUT area |
|---|---|---:|---:|---:|
| A010 first [110,170) ps | R1C1, R2C1 | 0.4554572 mV | 125.500 ps | 2.067570575e−15 V·s (each) |
| A010 first [110,170) ps | R1C2, R2C2 | 0.1527231 µV | 124.140 ps | about −1.23885e−20 V·s (each) |
| A010 second [170,250) ps | R1C1 | 0.4555050 mV | 185.500 ps | 2.068078154e−15 V·s |
| A011 [110,250) ps | all four | 0.4554060 mV | 125.520 ps (all) | 2.067821461763–2.067821461764e−15 V·s |
| A012 [170,300) ps | R1C1, R2C2 | 0.4554493 mV | 185.400 ps | 2.067833826e−15 / 2.067833878e−15 V·s |
| A012 [170,300) ps | R1C2, R2C1 | 0.7763825 µV | 184.420 ps | about 8.851e−23 V·s (each) |

For A010's two first-read maxima, the derived peak-time difference is 0.000 ps. The A009/A010 comparison used `[110,170)` ps and 6,000 exact common stored timestamps: A009 R1C1/R1C2 maxima were 0.4554825 mV at 125.570 ps; A010 R1C1/R2C1 were 0.4554572 mV at 125.500 ps. This is a numeric comparison only.

Actual branch-current extrema are retained per cell and stage. Examples: during A010 FINAL_READ, R1C1/R2C1 WL-branch maxima were about 109.13 µA and SE maxima 100 µA; the two WL-only cells had WL maxima about 111.01 µA and SE=0 setpoint. During A010's second-read window, R1C1 measured WL max 107.63 µA and SE max 100 µA; its measured BL resistor current ranged approximately −21.75 to +28.11 µA although the BL source was programmed to zero. For A011 FINAL_READ, each cell's WL and SE branch maxima were 100 µA; BL branch extrema were below 0.05 fA in magnitude.

In C, during the first selective write the R1C1 target's WL/BL maxima were about 101.12/101.12 µA. The same-row R1C2 WL-only branch reached 120.16 µA, while the same-column R2C1 BL-only branch reached 120.16 µA; branch currents on the nominally unselected R2C2 were also nonzero. During the second selective write, the analogous WL-only/BL-only paths were R2C1/R1C2. The complete signed min/max values for all branches and both write windows are retained in the arithmetic audit. These are current observations; no storage-state verdict is assigned here.

Independent Decimal-time integration cross-checks against runner arithmetic found zero VOUT peak-time mismatches. Maximum absolute runner-vs-independent differences were 4.25e−34 V·s (A010), 2.62e−31 V·s (A011), and 9.76e−32 V·s (A012); maximum same-JJ phase-delta discrepancies were below 4.8e−13 rad. The largest same-JJ phase-minus-area arithmetic residuals were 7.93e−7, 5.90e−7, and 1.59e−7 turns respectively; no pass/fail tolerance was registered for that residual.

## Visualization and remaining boundary

- Per-run full-range and response-window pages: classic `josim-plot2.py`, under each run's plots/.
- Comparison pages: plots/comparison/A009_vs_A010_first_read_response.html and plots/comparison/A010_A011_A012_full_read_outputs.html. The comparison CSVs use exact shared timestamps only; no interpolation/resampling. Both comparison QA records are PASS.
- The first arithmetic-audit serialization omitted a redundant explicit cell field on output rows; analysis/independent_batch_arithmetic_v2.json supersedes it. Raw hashes remained unchanged.
- No pulse/SFQ count classifier or threshold was registered. Whether these waveforms represent one quantized event per cell, whether cells are logically stored 0/1, and any mechanism explanation remain for scientific review. Timestep convergence is UNKNOWN. No follow-up solve is authorized.

## Package/push

The repository submit workflow creates the per-run and metadata DELTA ZIPs for
this revision. Exact package/mirror SHA-256 values are authoritative in the
detached PACKAGE_QA sidecars and submit record. Generated HTML stays local and
is excluded from ZIP members; the mirror target is /mnt/d/BVM_Backages.

## Authorized two-column two-level MERGE batch — 2026-10-08

Status: `EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW`
Physical solve count: **6** (T0–T5, serial A013–A018).
Scientific interpretation, event-count classification, and mechanism verdict: **NOT PERFORMED**.

All six runs used the same SHARED/CELL/CROSSPOINT preparation and canonical
sources, with `QB_CB=0,0`, `SJTL_COUNT=1,1`, `POST_SJTL_CB=1,1`, four separate
BVM SL/QB branches, two electrically separate two-level column chains, and
one 2 Ω output termination per column. No T1 or cross-column path was added.
Their exact instantiated nodes and source hashes are in each immutable run
deck/provenance/topology manifest. A013–A018 each contain 24,999 raw samples;
observed stored intervals range from about 0.01 to 0.02 ps, so all arithmetic
uses the actual raw timestamp sequence. Timestep convergence is UNKNOWN.

| Run | ROW/COL | Active FINAL READ cells | Raw SHA-256 | Raw bytes | Artifact / mechanical QA |
|---|---|---|---|---:|---|
| A013_SHARED_R00_C00 | 00/00 | none | `2e9f8f9fcc322f2d95a49f91f4d5d2136dcff8f7dc3880b9b237e6ed9a84654e` | 95,267,778 | VALID / PASS |
| A014_SHARED_R10_C10 | 10/10 | R1C1 | `079a6f731c4ececb625665f2aed8a20aa202f8764a9c85d8fb2ea56a681b99dd` | 95,346,875 | VALID / PASS |
| A015_SHARED_R01_C10 | 01/10 | R2C1 | `12865d0e7a5046f9c62a9b48f893bb5da74fef3ae839d8a38b51d9262cbd79b7` | 95,351,167 | VALID / PASS |
| A016_SHARED_R11_C10 | 11/10 | R1C1, R2C1 | `3a23533a3d8286bfd138e7a517ecb17fb7352c12e1aedd1c7c43741a0eb1fe66` | 95,355,420 | VALID / PASS |
| A017_SHARED_R10_C11 | 10/11 | R1C1, R1C2 | `35bac0500aef70973c043db2d419ae580ccfc5b20548e235fad503b2f0e83a07` | 95,363,027 | VALID / PASS |
| A018_SHARED_R11_C11 | 11/11 | all four | `5ce1430420117479ba3581b8f2f0234b00e545770ad9348b0bba81c07846dfe7` | 95,388,793 | VALID / PASS |

For every run, static, stimulus, raw, provenance, plot, and mechanical QA passed;
raw SHA before/after plot generation matched. Each run has 284 probes, all five
classic per-run HTML pages, deck/stimulus/config snapshots, solver logs, and
current/phase/output arithmetic. Solver output logs contain no warning/error
matches. Canonical SHA-256 values are identical to the frozen values in
experiment.yaml: BVM `ddf90076…3456b7`, QB `82e6f6c7…eed988a`, sJTL
`3cbc6889…1040688`, post-CB `70a6af05…d6d370`, JJMIT
`19862d1f…312a336`. Solver is `build/josim-cli v2.7.2837d13`, SHA-256
`48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2`.

### Derived output arithmetic

Peak is the positive maximum sample; signed area is trapezoidal integration over
`[110,250)` ps on each run's actual stored grid. These are voltage arithmetic,
not event counts.

| Run | VOUT_C1 peak / time / signed area | VOUT_C2 peak / time / signed area |
|---|---|---|
| A013 | 0.033082 µV / 111.780 ps / −2.20137e−20 V·s | 0.033082 µV / 111.780 ps / −2.20137e−20 V·s |
| A014 | 465.457 µV / 130.630 ps / 2.067812e−15 V·s | 0.040753 µV / 112.040 ps / −2.20137e−20 V·s |
| A015 | 452.045 µV / 123.310 ps / 2.067812e−15 V·s | 0.099019 µV / 124.320 ps / −2.20137e−20 V·s |
| A016 | 512.381 µV / 130.270 ps / 4.135646e−15 V·s | 0.134142 µV / 124.220 ps / −2.20137e−20 V·s |
| A017 | 465.457 µV / 130.670 ps / 2.067812e−15 V·s | 465.457 µV / 130.670 ps / 2.067812e−15 V·s |
| A018 | 512.194 µV / 130.290 ps / 4.135646e−15 V·s | 512.194 µV / 130.290 ps / 4.135646e−15 V·s |

For the T3/A016 double input, the recorded absolute-current maxima into the
second merge were: local QB branch `I(L3|XBQ_R2C1)` 326.679 µA at 120.400 ps;
previous-CB carry `I(L4|XCB_C1_L1)` 276.551 µA at 125.960 ps. The first-level
local QB branch `I(L3|XBQ_R1C1)` peaked at 233.940 µA at 122.930 ps. T5/A018
corresponding values were 327.133 µA at 120.400 ps, 276.542 µA at 125.980 ps,
and 234.276 µA at 122.950 ps for each column. These identify sampled branch
current extrema only; they do not classify reception or events.

Actual input branch currents were not assumed equal to source setpoints. For
example, during T3 FINAL READ, selected-cell WL branch maxima were 109.096 and
109.171 µA and SE maxima were 100 µA; WL-only cells reached 110.966 and
111.200 µA with SE source set to zero. During T5, each cell WL/SE branch maximum
was 100 µA; BL resistor branches showed nonzero extrema up to 5.706 µA even
though FINAL READ BL sources were set to zero. Full signed per-cell/stage
current tables are in each `analysis/cell_metrics.json`.

The maximum absolute same-JJ phase-delta/(2π) minus voltage-area/Φ0 arithmetic
residual across the `[110,250)` phase/voltage comparisons was 7.41e−7 for A013,
7.40e−7 for A014, 7.41e−7 for A015, 7.42e−7 for A016, 7.27e−7 for A017, and
6.41e−7 for A018. No acceptance tolerance was registered for this residual;
phase is stored in radians, and these arithmetic values are not event counts.

### Historical context, not a single-variable causal comparison

Exact-common-grid output arithmetic was checked over the corresponding raw
windows: A009 versus T4/A017 and A010 versus T3/A016 on `[110,170)` ps (6,000
common timestamps each), and A011 versus T5/A018 on `[110,250)` ps (14,000
common timestamps). A009's independent per-cell outputs peaked at 0.455483 mV
at 125.570 ps; T4's two column outputs peaked at 0.465457 mV at 130.670 ps.
A010's two selected independent outputs peaked at 0.455457 mV at 125.500 ps;
T3's merged C1 output peaked at 0.512381 mV at 130.270 ps. A011's four
independent outputs peaked at 0.455406 mV at 125.520 ps; T5's two merged
column outputs peaked at 0.512194 mV at 130.290 ps. The topologies and
downstream loading differ (four independent one-level outputs versus two
two-level merged outputs), so these figures are not strict causal contrasts.
A012 used sequential mixed-state writes and a 170 ps final-read start; it is
not a matched timing/preparation comparator for this batch. Its raw and prior
report remain unchanged.

T0–T5 comparison QA passed for both VOUT traces using 24,999 exact common raw
timestamps over `[0,250)` ps with no interpolation/resampling. Its classic
comparison HTML and CSV are under `plots/comparison/`; generated HTML remains
local and excluded from packages. No scientific verdict, event count, or
mechanism interpretation is made here.
