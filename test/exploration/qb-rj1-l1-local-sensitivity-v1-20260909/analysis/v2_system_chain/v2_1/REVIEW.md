# V2.1 presentation review

| hidden-error probe | result | evidence |
|---|---|---|
| stale raw | PASS | all five V2.1 raw hashes equal the pre-V2.1 reference |
| historical overwrite | PASS | parent V2 manifest/reference hashes and the pre-V2 snapshot remain unchanged |
| missing semantic boundary | PASS | gates A/B declare and verify input/output boundaries for all five categories |
| missing full overview | PASS | gate C finds `OVERVIEW_0_200ps` in every standalone run/category |
| duplicate display column | PASS | display labels are unique; intentional JSL boundary overlap uses explicit aliases |
| fictitious BVM output probe | PASS | BVM output is only `I/V(L_SL|XBVM1)` plus `V(COMMON_SL)`; no BVMOUT signal is created |
| absent optional probe | UNKNOWN | `V(IB|XBQ1)` is recorded as absent and is not replaced |
| wrong phase handling | PASS | phase pages independently unwrap raw radians before `rad/(2*pi)` display |
| comparison grid mismatch | PASS | all comparison inputs require exact stored time-token identity |
| overclaim | PASS | V2.1 adds no event count, SFQ classification, mechanism plot or new physical conclusion |
| unexpected solver use | PASS | V2.1 `physics_solve_count=0`; original execution count remains five |

Final disposition: V2.1 is a valid read-only presentation revision and remains
`AWAITING_USER_REVIEW`.
