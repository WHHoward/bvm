# Stage A review record

## Review disposition

- artifact status: `VALID`
- M0 migration equivalence: `PASS`
- S1 raw and required observables: `VALID`
- primary exploratory classification: `CONTINUOUS_MULTI_TURN_RUNNING_STATE`
- physical/system Gate: not issued; this is exploratory evidence only
- review state: `AWAITING_USER_REVIEW`

`BVMSim/bvm_cell.cir` remains historical/exploratory and is not canonical BVM
authority.  Its `R_JM1=8 Ω` was preserved; canonical
`circuits/bvm/bvm_cell.cir` has `R_JM1=6 Ω` and was not used in the fixture.

## Strongest bounded claim under review

The migrated active BVMSim QB is electrically equivalent to the historical
active QB on the overlapping M0 grid, and the existing four-BVM plus six-JTL
fixture can be strictly described.  The S1 data do **not** support the stronger
claim of four separated SFQ events: BJ2 has one same-JJ monotonic segment of
`+4.0234702725 turns` from `110.625 ps` to `130.25 ps`, with same-segment
voltage-area `+4.0234965237 turns` and residual `-2.6251162e-05 turns`.  This
is classified as a continuous multi-turn running segment, not four events.

## Numerical and evidence review

| Check | Probe and evidence | Status |
|---|---|---|
| Artifact validity | M0/S1 CSVs parse with `bvmtools.raw`; no NaN/Inf; M0 1549 samples, S1 7999 samples; JoSIM exits 0 for both runs | PASS |
| Migration time grid | Historical and M0 grids have exact length/token identity: 1549/1549; interpolation mode `none` | PASS |
| Migration values | Selected shared columns: max errors 0 for currents/phases, `1.0e-13 V` for `V(QBIN)`/`V(QBOUT)`, smaller for `O1/O3/O4/O5/O6`; all below tight preregistered numerical ceilings | PASS |
| Duplicate-column handling | Historical `V(O2)` occurs twice; it was never selected for M0 acceptance, and the occurrence-preserving reader reported both occurrences | PASS |
| Phase units | Raw `P(...)` was kept in radians; turns came from continuous unwrap divided by `2π`; plot uses `-j 2pi` and does not label turns as SFQ count | PASS |
| Same-JJ phase/area | Independent raw recomputation of the BJ2 largest segment agrees with the recorded `+4.0234702725` phase turns and `+4.0234965237` area turns | PASS |
| Event semantics | Complete segment count is based on shared `bvmtools.sfq` phase/area records; clean separation additionally requires a bounded retrap; the single BJ2 `+4.023` segment is not split into four events | PASS |
| Window boundary | Full-trace segmentation was done before onset association; no complete BJ2/JTL candidate crossed a registered boundary. The BJ2 candidate is wholly within READ1 | PASS |
| KCL | Shared `bvmtools.kcl` evaluated the declared signed equations. Independent raw recomputation maxima: node 2 `1.20e-04 µA`, bias node `5.00e-05 µA`, node 4 `1.40e-04 µA`; residuals are at CSV output-rounding scale | PASS |
| Timestep convergence | S1 is one `0.025 ps` diagnostic only; no ladder or convergence proof was authorized | UNKNOWN |
| Matched controls/repeat reads | READ0 is an association window in the existing fixture, not an independently generated no-input control; no extra control/repeat run was authorized | UNKNOWN |
| Canonical-BVM compatibility | Not tested and explicitly out of scope | UNKNOWN |

## Adversarial probes

| Hidden-error hypothesis | Probe | Result |
|---|---|---|
| Wrong/no-op QB branch | Inspect migrated deck includes, instance, active subcircuit, external bias, preserved BVM/JTL references, and M0 differential output | New `BQ_BVMSIM_V1` is used; no canonical BVM substitution; M0 matches shared signals at numerical precision |
| Weak oracle caused by duplicate CSV labels | Parse historical CSV with `bvmtools.raw` and refuse unqualified duplicate selection | `V(O2)` duplicate is explicit and excluded from acceptance |
| Phase-only overcount | Recompute BJ2 same-segment phase and voltage area from raw; inspect segment endpoints | One `+4.023` segment, not four one-turn segments |
| Boundary truncation manufacturing events | Segment the full trace first and record windows touched by each candidate | BJ2 complete candidate stays `110.625–130.25 ps` in READ1; no boundary split used |
| Stale/cached result | Check raw hashes, distinct M0/S1 paths, command log, and solver hash | M0/S1 raw are separate; hashes and commands are recorded; solver is `build/josim-cli` |
| Overclaim from downstream activity | Require cell-minimum of B01/B02 for table and compare onset ordering; preserve per-junction counts | JTL local activity is uneven (`JTL6.B02` has five clean local candidates while BJ2 has zero clean events); no strong transport label issued |

以上六项对抗性探针均为 `PASS`；它们用于排除导入分支、重复列、阶段边界、缓存结果和下游过度解释等高价值错误路径，不把探索性结果升级为物理 Gate。

The first repeat-determinism probe was intentionally recorded as `1` because
the command log was appended after that analyzer invocation and is included
in provenance.  After the command log was finalized, a second analyzer
invocation returned 0 and the hashes of metrics, strict evidence, migration
comparison, provenance, and brief were unchanged.  This is a provenance-log
coupling note, not a physical rerun or a raw mutation.

## Residual uncertainty

The result is limited to this BVMSim historical fixture, its fixed 250-uA QB
bias, and one S1 numerical resolution.  The observed local JTL phase activity
does not establish causal preservation of a discrete QB event because BJ2 is
already in a continuous running state and no matched no-input control or
repeat-read matrix was run.  No phase turn is promoted to a closed-loop
fluxoid count, hardware SFQ count, or system Gate.
