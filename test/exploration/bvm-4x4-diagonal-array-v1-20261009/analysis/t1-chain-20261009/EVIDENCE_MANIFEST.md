# T1 chain A020-A022 evidence manifest

State: `MECHANICAL_QA_PASS_AWAITING_USER_REVIEW`  
Physical solves: exactly 3  
Scientific interpretation / output-bit decoding: `NOT_PERFORMED`

The execution HEAD was `f6a89a3d64c3b8be2b7593bae4be01d1c9cbe192`; solver was
`build/josim-cli` v2.7.2837d13, SHA-256
`48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2`.
The pre-solve static gate and its exact run/probe hashes are in
[`PREFLIGHT.md`](PREFLIGHT.md), [`STATIC_QA.json`](STATIC_QA.json), and
[`PROBE_MANIFEST.json`](PROBE_MANIFEST.json). One pre-solver manifest-lock
incident is preserved in [`GATE_INCIDENT.json`](GATE_INCIDENT.json); it created
no raw and consumed zero solves.

The preflight-bound full static-QA JSON had SHA-256
`8046f0b672db77aec8a20655d56801f531a3c456de8534984a879c2a2e50c819` and was
348,892,046 bytes, mainly three repetitive JoSIM static-check stdout logs. Its
exact original bytes are preserved in [`STATIC_QA.json.gz`](STATIC_QA.json.gz);
decompression reproduces that SHA-256 exactly. `STATIC_QA.json` is now a compact
inspection view (SHA-256
`157a7b838920f1db64d7b387ab0b2649e256e7c1ef0628bef62bf959bb89c91e`): it keeps
the QA results and hash bindings, replaces each full stdout with its final
16 KiB, and records the original stdout SHA-256, byte count, and line count.
[`STATIC_QA_COMPACTION.json`](STATIC_QA_COMPACTION.json) binds the original,
compressed, and compact identities. This packaging-only transformation did
not alter any run raw or invoke JoSIM.

| Run | Clock | Raw bytes | Raw SHA-256 | Artifact / QA | Samples / plots |
|---|---|---:|---|---|---|
| A020_CHAIN_ALL_QUIET | QUIET | 95,602,892 | `ab13d65c671065fbfcd628ff7e4ffc0a9dc0506105bcd2a5bdefd91488aa763d` | VALID / PASS | 29,999 / 3 |
| A021_CHAIN_ALL_GLOBAL_CLOCK | GLOBAL_ONESHOT @ 200 ps | 95,684,744 | `85ffd3a00a6815115307d917c9b35d3b06dd7ac240c61ca8bfd47b957e975e9e` | VALID / PASS | 29,999 / 3 |
| A022_CHAIN_PAPER_GLOBAL_CLOCK | GLOBAL_ONESHOT @ 200 ps | 95,786,305 | `2095fc87f129e844abfe21a0ccafb21e9ef2c72b67e7b6c34c8ca8f50935d9cb` | VALID / PASS | 29,999 / 3 |

Each raw spans 0 through 299.99 ps; observed time-step range is approximately
0.01–0.02 ps. The three generated classic `josim-plot2.py` pages per run are
`01_full_chain_overview.html`, `02_carry_propagation.html`, and
`03_stage_focus.html` under `plots/runs/<run_id>/`. HTML and the shared Plotly
asset remain local and are excluded from the DELTA ZIP.

The planned incremental archive is split into one source ZIP, one combined
non-raw run-evidence ZIP, and three per-run immutable raw ZIPs. This keeps each
uncompressed Git package below the single-file limit while referencing, not
recopying, A001-A019 raw.

Mechanical arithmetic, signed voltage areas, stored-sample extrema/times,
descriptive lobe-candidate navigation, and same-JJ P/V cross-checks are in
`runs/<run_id>/metrics.json`; the stage tables are
[`T1_CHAIN_TABLE_v2.csv`](T1_CHAIN_TABLE_v2.csv) and
[`T1_CHAIN_JJ_PHASE_AREA_v2.csv`](T1_CHAIN_JJ_PHASE_AREA_v2.csv). The original
derived `metrics.json` files are preserved beside the corrected files as
`metrics_preclock_peak_v1.json`. `CHAIN_METRICS_REPAIR.json` documents a
same-raw-only correction: QUIET cases have no actual clock pulse, so their
`actual_clock_peak_time_ps` is now null. All three raw SHA-256 values remained
unchanged; no solver was invoked by this repair.

No binary output vector is decoded. The 225/143 bit vectors in the preregistered
experiment definition remain theoretical references only. Phase turns are
`rad/(2π)` navigation arithmetic, not SFQ counts. No mechanism, multiplier
success, or system-rate conclusion is made here.
