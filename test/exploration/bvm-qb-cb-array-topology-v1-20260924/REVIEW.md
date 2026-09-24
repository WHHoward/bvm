# Static implementation adversarial review

Scope: USER_CASE component rendering, user preview/batch flow, and submit closure.
No JoSIM process, real batch/run, raw, waveform HTML, package ZIP, mirror, or
Drive operation was performed.

| Hidden-error hypothesis | Probe | Result |
|---|---|---|
| Default renderer is a no-op with stale or guessed defaults | Render each default component and compare byte-for-byte to its hash-bound canonical 0923 source | PASS; all four snapshots are byte-identical; all canonical hashes remain unchanged. |
| A QB override silently changes another component or source field | Set only `QB_BJ3_AREA=2.2`; diff rendered QB against canonical and compare BVM/CB/sJTL | PASS; the only changed line is BJ3 area. |
| OPEN becomes a large resistor, or reopening does not reactivate the branch | Render BVM/CB OPEN defaults and numeric overrides; render with `BVM_RSL=OPEN` and validate probes | PASS; OPEN branches are comments, numeric values reactivate them, and absent RSL probes are omitted. |
| Stale canonical input is silently accepted | Alter a temporary copy while retaining the reference hash and call the source verifier | PASS; it hard-stops with `REFERENCE_SOURCE_CHANGED`. |
| Dry-run reaches the solver or leaves a batch/run/snapshot behind | Invoke `./try.sh --dry-run`, `--set` variants, and mask subset; compare config and runs/batches before/after; process call patched to fail in unit test | PASS; 4/2 planned solves are shown, override diff is explicit, no persistent preview artifact or solver call. |
| A partial mask batch or plot failure is accepted by submit | Synthetic batch with mask 10 absent, then with one plot QA FAIL; invoke mechanical validation with subprocess patched to fail | PASS; both are rejected as `BATCH_INCOMPLETE`; no solver retry. |
| A physical failure silently retries or continues to later masks | Stub the first requested mask as solver failure and inspect the batch/run records | PASS; the failed run is preserved, remaining masks stop, and no retry occurs. |
| Repaired plots require rerunning physics or leave stale batch metadata | Change only synthetic same-raw plot QA to PASS, refresh batch closure, and run submit validation | PASS; batch becomes `COMPLETE_MECHANICAL` and validates without invoking JoSIM. |
| Actual run preflight loses the selected mask after render-only validation | Execute the runner with provenance stubbed and intercept the solver call; inspect generated PREFLIGHT | PASS after fix; PREFLIGHT includes the requested mask, and the solver stub prevents any physical invocation. |
| User-edited USER_CASE values make canonical-default tests fail spuriously | Run the suite with the user's changed QB/CB values and bind default-render assertions to `component_reference.env` | PASS after test isolation; user configuration remains untouched. |
| JoSIM treats quotes in `.include` as filename characters | Compare U002 stderr's requested path with the existing unquoted deck syntax; assert generated include directives are unquoted | PASS after fix; the deck renderer emits relative unquoted includes. |
| JoSIM rejects `.title` as an unknown control after input parsing | U003 stderr identifies the control; assert rendered decks contain no `.title` directive | PASS after fix; the descriptive title is an SPICE comment. |
| Submit dry-run creates a package while validating a complete batch | Mock package creator to fail; execute submit dry-run over a complete synthetic batch | PASS; preview is allowed, package/mirror/commit/push are not performed. |

All platform unit tests pass. Static 2×1, 3×1 and 4×1 topology fixtures remain
`RENDER_FIXTURE_ONLY`; automated tests render into temporary directories and
do not rewrite checked-in fixtures.

Residual uncertainty: actual JoSIM parsing/include resolution, the solver's
handling of repeated `.model jjmit` cards, and real-raw classic plot rendering
remain UNKNOWN because the user explicitly prohibited physical solves and raw
generation in this task.
