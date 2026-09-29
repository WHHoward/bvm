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
