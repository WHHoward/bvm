# 2×2 BVM row/column platform static preflight

This experiment is governed by docs/EXPERIMENT_CONTRACT.md.

- Parent HEAD: `a155b7f820efbad4447c8d1985a66e4192b7e614`.
- Scope of this task: platform implementation, static topology/stimulus QA,
  regression tests, and dry-runs only. `physical_solves_authorized_in_this_task=0`.
- No canonical BVM, QB, CB, sJTL, or JJ model is copied, edited, or rendered
  with altered internal parameters.
- Four separate BVM→BQ→one sJTL→one post-CB→2 Ω termination chains; four
  separate VOUT nodes; no merge, diagonal combine, or T1.
- INDEPENDENT uses 12 cell-level PWL current drivers. SHARED uses exactly two
  row-WL, two column-BL, and two column-SE PWL drivers on six distinct nodes.
- Row and column bit order is left-to-right: `10/10` activates R1C1; row-only
  and column-only half-selected cells are recorded separately.
- All four cells receive WRITE0, READ0, and WRITE1. ROW_BITS/COL_BITS affect
  FINAL READ only; FINAL READ has zero BL drive.
- `./try.sh --dry-run` must not create a run directory or invoke JoSIM.
- A later manual `./try.sh` invocation, initiated by the user, allocates one
  immutable run ID and invokes the solver once for the current config only.
- No physical result, equivalence claim, or scientific interpretation is
  produced by this static-platform task.

## Incremental CELL-SE platform extension

- Compatibility base: `3d12e5c5252f02748f880f09027e70c8d0cfc3d8`.
- This extension changes only the existing runner/configuration/tests/docs.
  A001–A003 raw, run manifests, QA, and existing ZIP archives remain immutable.
- Missing `SE_TOPOLOGY`/`SE_GATE_MODE` defaults to
  `SHARED_COLUMN/COLUMN`; the existing A/B/C presets explicitly retain the
  legacy generated deck and stimulus behavior.
- `SHARED + CELL` uses two shared row-WL, two shared column-BL, and four
  electrically independent cell-SE sources. D0 gates final SE by column;
  D1 gates it by row AND column. Both retain the four canonical load chains.
- Scope remains static topology/stimulus/probe QA, regression tests, and
  dry-runs only. No JoSIM invocation, experiment run raw, or physical claim.
  One legacy mock-runner test in an earlier full test pass wrote a synthetic
  CSV only inside an automatically cleaned `TemporaryDirectory`; it did not
  enter this experiment's `runs/` tree or Git.

## Optional half-selected repeat-read extension

- Compatibility base: `f554cbc7aff90e9eb3a9cd8a07d99444ac1ea503`.
- A001–A006 raw, manifests, QA, plots, and existing handoff packages remain
  immutable; their complete run/archive file-set fingerprint is unchanged.
- SECOND_READ defaults off. E0/E1 enable only the user-registered
  170–181 ps second read, with R2C1 as the fixed CELL_CROSSPOINT SE target and
  STOP=300 ps.
- E0 first-read PWL is byte/grid-equivalent to A005 through 170 ps; E1 matches
  A006. Comparisons exclude the added second stage and STOP endpoint.
- Static tests and dry-runs only; no E0/E1 solve, synthetic raw, or physical
  result is produced by this platform update.

## Optional SECOND_READ platform extension

- Parent HEAD: `f554cbc7aff90e9eb3a9cd8a07d99444ac1ea503`.
- `SECOND_READ_ENABLE` defaults off; legacy USER_CASE/preset snapshots without
  the new fields render no SECOND_READ PWL stage.
- E0/E1 retain the existing eight sources and four independent load chains.
  Only the second read's cell-local SE gate is fixed to
  `SECOND_ROW_BITS AND SECOND_COL_BITS`; it does not inherit the first-read
  `SE_GATE_MODE`.
- The registered first-read, recovery, second-read, and post-second-read metric
  windows are half-open and use actual stored raw rows. Focused plots use the
  existing classic `josim-plot2.py` renderer on those stored rows.
- Static/dry-run validation only; no JoSIM, no generated raw, and no E0/E1
  physical result is authorized in this task.

## Authorized A/B/C shared-selection batch (2026-09-29)

This experiment is governed by docs/EXPERIMENT_CONTRACT.md.

- Parent HEAD: 5447f08ebbe367dd9d4f2ff2f072fa17c2cc1aac (master, synced to bvm/master).
- Recorded solver: build/josim-cli v2.7.2837d13, binary SHA-256 48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2.
- Frozen executor SHA-256: scripts/run_platform.py 4d2cea3de007c0211989b32976f38cda9be079c865d211b26b510dc75be7ea93; comparison builder SHA-256: scripts/build_batch_comparison.py 6e81c0848a8b32b333969b56408f709e1580c5c51cf968b7389452f65b834fcf.
- User authorization: current task dated 2026-09-29; exactly three independent physical solves, serially allocated, no follow-up.
- Historical evidence A001–A009 is immutable and hash-verified; A009 is the same-row ROW_BITS=10, COL_BITS=11 comparison. No historical run is re-solved or rewritten.
- Expected new run IDs in order: A010_SHARED_R11_C10, A011_SHARED_R11_C11, A012_SHARED_R11_C11.
- Canonical sources remain direct includes with the SHA-256 values registered in experiment.yaml; do not edit BVM, QB, CB, sJTL, or JJ model sources.
- Every case uses SHARED + CELL + CROSSPOINT; two row-WL sources, two column-BL sources, four independent cell-SE sources; 200 µA write WL/BL, 200 µA read WL, 100 µA read SE; DT=0.01 ps. Four independent BVM→QB→1 sJTL→1 CB→2 Ω VOUT chains; no merge and no T1.

### Exact run matrix

1. A — same-column dual read (A_SAME_COLUMN_DUAL_CROSSPOINT): ROW_BITS=11, COL_BITS=10, SECOND_READ_ENABLE=1, SECOND_ROW_BITS=10, SECOND_COL_BITS=10, original WRITE0/READ0/WRITE1/FINAL_READ times, SECOND_READ 170–181 ps, STOP=250 ps. At first read, only R1C1/R2C1 receive cell SE; both rows receive WL; second read gates R1C1 only. Compare its first response with A009 on exact common stored timestamps [110,170); no interpolation.
2. B — four-cell read (B_ALL_CELL_CROSSPOINT): ROW_BITS=11, COL_BITS=11, SECOND_READ_ENABLE=0, original four stage timing, STOP=250 ps. All four cell-SE sources are active during FINAL_READ.
3. C — mixed-store preparation/read (C_MIXED_STORAGE_SEQUENTIAL_WRITE): WRITE0 all shared lines at 50–61 ps; READ0 explicitly omitted; selective WRITE1 R1C1 via WL_R1+BL_C1 at 90–101 ps, then R2C2 via WL_R2+BL_C2 at 120–131 ps; ROW_BITS=11/COL_BITS=11 final read at 170–181 ps; STOP=300 ps. No independent WL/BL topology is permitted. For each write, record target, same-row WL-only, same-column BL-only, and unselected cells, plus every cell's actual WL/BL/SE branch current.

### Registered windows and arithmetic

- A first trigger [110,121), first response [110,170), second trigger [170,181), second response [170,250); responses are separately summarized, never combined across both reads.
- B trigger [110,121), full read response [110,250).
- C target-write windows [90,101) and [120,131); gaps [101,120) and [131,170); final trigger [170,181); full read response [170,300).
- Per cell: actual WL/BL/SE branch current extrema and charge on stored rows; BVM JM1/JM2/JS1/JS2 P/V, SL; QB, sJTL and CB JJ P/V; QB_OUT, SJTL_OUT and VOUT.
- Output arithmetic per read-response window: signed min/max/p2p, timestamp of positive maximum/negative minimum/max-absolute sample, and signed voltage-time area for BVM_SL, QB_OUT, SJTL_OUT, VOUT.
- Same-JJ phase-radian endpoint delta versus voltage integral/Phi0 arithmetic uses identical run, JJ, direction and actual stored timestamps. No phase turns or voltage area will be called an event count.
- No pulse/SFQ event detector or threshold is registered. SCIENTIFIC_REVIEW_AUTHORIZED was not supplied; event-count classification, physical Gate verdict, mechanism interpretation, or winner selection is NOT PERFORMED. Timestep convergence is UNKNOWN.
- A009 raw QA records actual intervals from 0.01 to 0.02 ps despite nominal DT=0.01p. Comparison plots use only exact common stored timestamps in their registered windows: A009/A010 orientation [110,170) ps, and the A010/A011/A012 VOUT overlay [0,250) ps (C's full standalone range remains through 300 ps). Interpolation/resampling is prohibited. Per-run plots use classic josim-plot2.py, full raw ranges plus the registered read-response windows.
- Artifact outcomes distinguish solver/artifact invalidity from physical behavior. If a raw is valid but post-processing fails, preserve that raw and repair only its analysis/plots; never rerun solely to repair analysis.

No additional masks, amplitude points, parameter sweep, altered topology, canonical source changes, or T1/4×4 work are authorized.

## Authorized two-column two-level MERGE batch (2026-10-08)

This experiment is governed by docs/EXPERIMENT_CONTRACT.md.

- Parent HEAD: 511f19b637c4e7f42712b0545f41ef0cb7d3909d; fetched bvm/master is identical; initial worktree was clean.
- Exactly six physical solves are authorized, serially: T0/A013, T1/A014, T2/A015, T3/A016, T4/A017, T5/A018. Each run gets a fresh immutable directory; no parallel ID allocation.
- No existing A001–A012 evidence is modified or re-solved. At preflight, all 12 manifest/raw/result hashes agree. All 17 handoff ZIPs have PASS QA and matching copies in /mnt/d/BVM_Backages.
- Frozen canonical sources are the active BVM 0923, QB 0928, sJTL 0923, CB 0928 and jjmit files with SHA values in experiment.yaml. No component parameter or source changes are allowed.
- The existing reference generator test/exploration/bvm-qb-cb-array-topology-v1-20260924/scripts/topology.py is called for each 2×1 column. Its SHA-256 is 81bebf3e15eb575554227f8fc13a1174fee234adc42485c75d785eeefe7d5275. Registered topology flags are QB_CB=0,0; SJTL_COUNT=1,1; POST_SJTL_CB=1,1.
- Exact topology per column: row-1 QB output -> MERGE_Cn_L1 -> sJTL_Cn_L1 -> CB_Cn_L1 -> MERGE_Cn_L2; row-2 QB output also lands on MERGE_Cn_L2; then sJTL_Cn_L2 -> CB_Cn_L2 -> VOUT_Cn -> one 2 Ω termination. MERGE labels are electrical nodes, not components. C1/C2 merge nodes and terminal outputs are disjoint. No QB-side CB, inter-column connection, T1 or other element is present.
- Shared excitation: WL_R1/R2 each connect to their two row cells; BL_C1/C2 each connect to their two column cells; SE_R1C1, SE_R1C2, SE_R2C1, SE_R2C2 are four separate sources/nodes. Only ROW_BITS AND COL_BITS crosspoints receive active FINAL_READ SE. Passive shared-line/merge-coupled currents are retained as measurements, not assumed zero.
- All six cases preserve WRITE0 [50,61) ps, READ0 [70,81) ps, WRITE1 [90,101) ps and FINAL_READ [110,121) ps, 200 µA WL/BL writes, 200 µA WL read, 100 µA per-cell SE read, SECOND_READ_ENABLE=0, DT=0.01 ps, STOP=250 ps and two independent 2 Ω terminal loads.
- Mask map: T0=00/00; T1=10/10; T2=01/10; T3=11/10; T4=10/11; T5=11/11 (row bits / column bits; leftmost bit is index 1).
- Static acceptance requires four unique BVM SL nodes, four QB instances, exactly two isolated two-level chains, exactly four sJTL plus four post-sJTL CB instances, two termination resistors, the expected MERGE1/MERGE2 endpoint pins and no cross-column path. Six preset dry-runs and A001–A012 deck/stimulus regressions pass before solving.
- Core acquisition is expanded only for COLUMN_MERGE to preserve BVM input branch currents and P/V state, full QB JJ/passive I/V, each sJTL/CB stage, MERGE voltages, QB/previous-CB currents into MERGE2, and VOUT_C1/C2. Probe count is 284. A011 raw row-width scaling predicts about 95,187,175 bytes per 250 ps raw (<100,000,000-byte Git hard limit); actual sizes must be checked. No LFS/storage-policy change is authorized.
- Solver: build/josim-cli v2.7.2837d13, compiled 2026-05-30; binary SHA-256 48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2.
- Registered metric windows: FINAL_READ [110,121) ps; terminal response [110,250) ps. Per-run figures are 01_overview, 02_bvm, 03_qb, 04_column1, 05_column2, classic josim-plot2 sep_comb/dark/-j 2pi. The six-run comparison overlay uses exact common stored timestamps only; interpolation/resampling is prohibited.
- Required arithmetic: per-cell actual WL/BL/SE branch currents; BVM SL; QB input/output; MERGE1/MERGE2 values and both merge-input branch currents; every sJTL/CB JJ phase/P/V; VOUT_C1/C2 peak time and signed area over actual raw rows. Same-JJ phase-radian delta and voltage integral/Phi0 arithmetic are recorded. No pulse/SFQ threshold/count classifier is registered; event count, functional Gate and mechanism conclusions remain NOT PERFORMED. Timestep convergence is UNKNOWN.
- Stop after these six solves, per-run QA, classic plots, comparison QA, raw/package SHA audit, delta package, GitHub push and mirror. No additional mask, topology, parameter, timing or T1 experiment is authorized.
- Final frozen executor SHA-256: `scripts/run_platform.py` `d79293236cc688a5d9c7addf3a81408e6e86d030676c841aad5e7067b5ea91f4`.
- Registered T0–T5 exact-grid comparison builder SHA-256: `scripts/build_merge_batch_comparison.py` `14b64503167b63b7983e32e0978057f7de926cd13703f04b77cae00490ad1f61`. It overlays VOUT_C1/C2 on exact common raw timestamps only and retains the source raw hashes; no interpolation/resampling.
- Solver reverified before execution: `build/josim-cli v2.7.2837d13`, binary SHA-256 `48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2`.
- Acceptance completed before any solve: all six actual `./try.sh --preset M_T* --dry-run` commands returned `DRY RUN PASS`, static QA PASS, 284 probes, and no run directory creation; 34 platform regression tests passed; `py_compile` and `git diff --check` passed. Historical A001–A012 deck/stimulus byte-regression and evidence-hash checks passed.
- Exactly six physical solves remain authorized; execute serially in the registered order. No run exists for A013–A018 at this freeze point.

### Execution receipt — 2026-10-08

- Exactly the authorized six solves completed serially: A013–A018. No retry or follow-up solve was run.
- All six returned `MECHANICAL_QA_PASS_AWAITING_USER_REVIEW`, `artifact_status=VALID`, and PASS static/stimulus/raw/provenance/plot/mechanical QA. Raw SHA before/after plotting is identical for each run.
- Each raw contains 24,999 samples and 284 probes. Raw sizes are 95,267,778–95,388,793 bytes; all are below 100,000,000 bytes. Observed stored dt range is approximately 0.01–0.02 ps; timestep convergence remains UNKNOWN.
- The registered exact-grid T0–T5 output comparison passed with 24,999 common timestamps in `[0,250)` ps, no interpolation/resampling, and immutable source raw hashes.
- All per-run classic plot pages and arithmetic are present. Scientific interpretation, SFQ/event classification, mechanism claims, and functional Gate judgment were not performed.
- Packaging checkpoint was reviewed per the user's instruction not to repeat full historical ZIP decompression/member verification: the prior full snapshot and 16 delta ZIP identities match their previously PASSed QA sidecars; delta manifests have consistent base/file-hash closure and ancestry. Current delta base is `bvm-2x2-rowcol-selection-v1-20260928_snapshot_bvm2x2-rowcol-a001.zip` (SHA-256 `90b174f0f7ea71c6d41bcf85db1d999af9c173c0b0ecbb8de31f1c96bb4e3f50`, base commit `4035a3d6adcc841f4bd4269fbc32b9a3c897746a`), with prior checkpoint head `1e74b4df60a4490e8dd85dc6a84671eaa4b46d0e`; current source HEAD before submission is its descendant `511f19b637c4e7f42712b0545f41ef0cb7d3909d`.
- Fast delta inventory: 172 new files, 8 modified files, no non-HTML deletions, 12 referenced existing raw files, and 126 generated HTML files excluded from the new archive (left local). Seven package groups are planned (A013–A018 plus metadata); the largest uncompressed group is 98,281,550 bytes, below 100,000,000 bytes. Each new package will still receive full ZIP CRC and included-member SHA verification before commit/push/mirror.

## Authorized T1_C1 receiver integration batch — 2026-10-08

This experiment is governed by docs/EXPERIMENT_CONTRACT.md.

- Parent HEAD: `7eb7983c8091a3933e871246754a47d199cabd67`; fetched `bvm/master` matched. Initial worktree was clean.
- Exactly eight physical solves are authorized, serially and once each: Q0–Q3 then P0–P3; expected immutable run IDs A019–A026. Stop after eight, or at the first solver/raw/provenance/plot QA failure; never retry or tune.
- A001–A018 and the historical A035/A041 T1 evidence are read-only controls. The corresponding terminal-reference map is Q0/P0→A013, Q1/P1→A014, Q2/P2→A015, Q3/P3→A016. The old C1 2 Ω load and new T1 input are different loads, so these comparisons are descriptive, not matched-load causal contrasts.
- Frozen front-end topology remains `OUTPUT_TOPOLOGY=COLUMN_MERGE`, `QB_CB=0,0`, `SJTL_COUNT=1,1`, `POST_SJTL_CB=1,1`; SHARED row WL, column BL, four independent cell SE, CELL+CROSSPOINT. Only C1 is linked to T1. C2 remains isolated with its 2 Ω terminal.
- `OUTPUT_MODE=TERMINAL` remains the default. `OUTPUT_MODE=T1_C1` removes only `R_TERM_C1` and adds `V_T1_LINK VOUT_C1 T1_I 0` plus exactly one `XT1 T1_I CLK S C N_BIAS1 N_BIAS2 N_BIAS3 T1`. No C1 parallel 2 Ω, no C2-T1 short, and no canonical component modification.
- T1 source: `circuits/t1/t1_cell.cir`, SHA-256 `828b873132b32af4fd3cebcbfa42a90fd50f15e75fdb976f1d13e07c3f1fe237`; JJMIT model SHA-256 `19862d1fd1f1f44dfa1523848d7d3b5e2594a6c5da8fdd80144b449e5312a336`. All BVM/QB/sJTL/CB source hashes remain as registered above.
- Frozen Bias B: 1.8m/1.8m/1.8m V sources, BIAS3 source VOLTAGE, R_S=12 Ω, R_C=12 Ω. QUIET is `R_CLK_QUIET CLK 0 5` only. PULSE is `V_TRIG_CLK CLK_RAW 0 PULSE(0 1.2m 170p 1p 1p 2p 50p)` plus `R_TRIG_CLK CLK_RAW CLK 2`, with no quiet shunt.
- All cases preserve WRITE0/READ0/WRITE1/FINAL_READ source and timing conditions, `DT=0.01p`, `STOP=250p`, and `SECOND_READ_ENABLE=0`. Masks: 00/00, 10/10, 01/10, 11/10, each under QUIET and PULSE.
- `PROBE_PROFILE=t1_focus`: all 11 T1 JJs P/V, currents of L1/L3/L11/L14/L17, T1_I/link current, clock, S/C/load currents, C1 full frontend critical chain, all BVM input branches and BVM state, plus C2 BVM/input/output control. Expected count is 151 QUIET / 152 PULSE. A018 scaling plus 15% field-width margin estimates 58,324,873 / 58,711,131 bytes per run; actual size is checked after every solve and must remain below 100,000,000 bytes to commit to ordinary Git.
- Registered half-open analysis windows are `[110,170)`, `[170,220)`, `[220,250)` ps; all integrations use actual stored timestamps. Phase is radians. `Δphase/(2π)` and voltage-area/Φ0 are arithmetic only; no SFQ count or threshold is registered.
- Per-run visualization: four classic pages `01_overview`, `02_frontend_c1`, `03_t1`, `04_t1_output`; the output page contains the three registered window views and references shared Plotly JS once. Two comparison pages cover matched QUIET/PULSE pairs and the pre-clock A013–A016 terminal references using exact common timestamps only. Generated HTML remains local and is excluded from packages.
- Packaging plan: estimated 58.3 MB × 4 QUIET plus 58.7 MB × 4 PULSE = 468,144,016 bytes of raw before manifests; this exceeds the existing generic DELTA packer's 100 MB uncompressed per-group limit. Use its allowed per-run DELTA ZIPs plus one metadata ZIP, not a duplicate aggregate archive. Exclude all HTML. Preserve checkpoint ancestry and raw SHA references; new ZIPs receive CRC and member-hash verification. Upload to the existing Drive `BVM_Backages` folder and record the verified Drive folder/file URLs in BATCH_SUMMARY.
- Interpretation ceiling: artifact validity and registered numeric arithmetic only. T1 truth table, SFQ reception, mechanism, bias/clock optimization, timing/frequency sensitivity, and timestep convergence remain unclaimed/UNKNOWN. No extra masks, T1 columns, clocks, or solver runs are authorized.

### Frozen static acceptance receipt — 2026-10-08

- Preflight render manifest: `analysis/t1_preflight_manifest.json`,
  SHA-256 `3bd2350583c43e0b4e1a256dc2f362227fa64b8ba1390e77af34a4cb740e2fc4`;
  parent HEAD `7eb7983c8091a3933e871246754a47d199cabd67`.
- Solver: `/home/howard/JoSIM/build/josim-cli`, `v2.7.2837d13`, SHA-256
  `48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2`.
- Frozen runner SHA-256 `0bd448b2c78573a52a8b75d30bcaff5127d355781f8eacfa3531bec7e348676b`;
  raw audit `172ba73d02d42dbacbe1ba574de1700dcf68c8d7cfa4b5349a33f4239a42b8d4`;
  comparison builder `e9ebb8ae66bafcdd89719ce11fe72e411e2f87dd7d91c7eb5f0c6710f6b44a3c`;
  arithmetic spec `73937eba48626d2cfa0017ea9d2ce5da6d61553782ff4805309ad4e492b06fbf`.
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q
  test/exploration/bvm-2x2-rowcol-selection-v1-20260928/tests`: **40 passed**;
  Python compile, `bash -n try.sh`, and `git diff --check`: PASS.
- All eight `./try.sh --preset T1_C1_{Q0..Q3,P0..P3} --dry-run` invocations:
  static QA PASS, 151 QUIET / 152 PULSE probes, four planned classic pages,
  estimated raw 58,324,873 / 58,711,131 bytes per run. Each reports zero
  physical solves; no preview run directory was created.
- Historical A001–A018 byte-render regressions and exact A013–A016 stimulus
  equivalence tests passed. New physical-solve count at freeze: **0**.

### Post-run audit-script correction — 2026-10-08

- The first two independent-audit launches stopped before opening raw or writing
  report files: the run-ID format was undefined, then the run-ID tuple shadowed
  the runs-directory path. These were audit-code defects only; all eight solver
  results and raw hashes remained intact.
- Corrected `scripts/audit_t1_batch.py` SHA-256:
  `0230243a55a919655377d43ce63f3ca6f5f77de71894deb0d370e0c49529fbe2`;
  added regression `test_t1_independent_audit_run_matrix_keeps_path_and_ids_distinct`.
- Updated regression suite: **41 passed**. Corrected actual-grid audit: 8/8
  PASS, zero arithmetic/artifact errors; comparison QA PASS; raw hashes
  unchanged. Details and before/after script hashes are in
  `analysis/t1_audit_patch_record.json`.
- No solver invocation was made during this repair, no raw/plot/run evidence
  was overwritten, and no physical interpretation was performed.
