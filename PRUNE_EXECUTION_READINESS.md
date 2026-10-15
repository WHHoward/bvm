# PRUNE_EXECUTION_READINESS

**Status: READY FOR USER REVIEW; no cleanup is authorized or executed in this task.**

Reference checkout at start: `master` / `bvm/master` = `7c48236745837cf7071a0ac7f440da059b0aaad9`. The worktree changes in this report are uncommitted. No file was deleted, moved, or restored; no Drive operation occurred; no JoSIM executable was invoked.

## Scope for the next local cleanup

The locally accepted deletion set is deliberately limited to:

1. The **99 exact run-directory paths** whose `record_kind=RUN_DIRECTORY` and `revised_category=DELETE_OBSOLETE` in [BVM4X4_REVISED_PRUNE_CANDIDATES.csv](</home/howard/JoSIM/BVM4X4_REVISED_PRUNE_CANDIDATES.csv>): A001–A017, A020–A026, A028–A029, A034–A106. Deleting each directory includes its raw and run metadata; do not separately count or target the child `RAW_FILE` rows.
2. The **591 exact HTML paths** whose `record_kind=HTML_PAGE` and `revised_category=DELETE_GENERATED` in that same CSV.
3. The **138 exact local ZIP paths** whose `record_kind=HANDOFF_ZIP` and `revised_category=DELETE_GENERATED` there.

Do not use directory-wide `rm`, `git clean`, or a wildcard delete. Execute only the rows of those three record kinds and categories, after the user approves the final list and an execution-time existence/size/hash check. Tracked run/ZIP removal by a normal commit reduces the current tree but not Git history; no `git gc`, history rewrite, or LFS prune is included.

The two `manual_batches/` directories and 59 child files are marked as candidates in the earlier revised CSV, but they were **not included in the latest accepted scope bullets**; preserve them pending a separate decision. Also preserve all 138 `PACKAGE_QA.json` sidecars (the accepted target is the 138 ZIP files only), the append-only `experiment_manifest.json`, all three protected experiment roots, and all other Exploration directories. The 337 Drive file IDs remain a separate later task; do not include them in the local cleanup batch.

Expected allocation reclaimed from the accepted local set, based on the revised inventory:

| Target | Count | Allocated bytes |
|---|---:|---:|
| Run directories | 99 | 9,155,002,368 |
| HTML files | 591 | 21,545,263,104 |
| Handoff ZIPs | 138 | 2,669,780,992 |
| **Total** | **828 targets** | **33,370,046,464 bytes** |

That estimate excludes the two manual-batch directories (126,976 bytes). The revised 4×4 directory inventory is 34,650,099,712 allocated bytes; projected remainder for this exact set is 1,280,053,248 bytes. These are not measured post-delete results.

## Compatibility fixes and adversarial probes

| Risk tested | Probe | Result |
|---|---|---|
| Stale deck oracle reads A021/A022 or other retired run files | Replace those test reads with static SHA-256 deck fixtures; search the 4×4 tests for historical `RUNS/.../deck.cir` reads | PASS; tests no longer open any historical run deck. The fixture hashes preserve the old deck identity without relabeling it as V9. |
| Run number is inferred only from remaining directories and reuses old IDs | In a temporary tree containing only eight selected old run directories, load the unchanged 108-run manifest | PASS; allocator returns `A109_POST_PRUNE`; A021 remains reserved even if its directory is absent; explicit reuse is rejected before `run_one` reaches a solver call. Registered batch reservations are also skipped/validated. |
| `try.sh` needs retired run directories or handoff ZIPs for a dry run | Call the platform dry-run with a temporary `runs/` containing only the nine selected directories and no handoff tree | PASS; static QA passes, `solver_invoked=false`, no preview/run directory is written. The real `./try.sh --dry-run` also passes and reports zero solves. |
| `submit.sh`/root `scripts/submit.py` require the old 138 ZIPs as a base | In a temporary Git repository, retain only nine raw files plus the original 108-ID manifest/checkpoint registry; leave `handoff/` empty. Exercise local `submit.sh`, root dispatcher, `--track-packaged-raws`, a synthetic A109 manual run, and a synthetic one-run registered batch | PASS; no pending work returns `NO_PENDING_RUNS`; retained raws return `RAW_ALREADY_TRACKED`; A109 plans a `git_tree` base with nine raw references and no old ZIP; default local and root-dispatched submit return `DRY_RUN_PASS`; the one-run registered route also passes. `handoff/` remains empty. All synthetic bytes were temporary test fixtures, not experiment evidence. |
| Retired one-off submit commands silently process incomplete data | Exercise `--d3-carry-timing` in the empty-handoff sandbox | PASS; it exits with an explicit “legacy submit mode … unavailable for retired inputs” message rather than entering packaging. Other fixed A-series supplement modes have the same missing-input guard. |
| The nine kept pages silently point into a retired experiment directory | Check each current page’s SHA against the candidate CSV, ignored status, single Plotly `<script>` reference, and resolved asset path | PASS for all nine; all resolve to `assets/vendor/plotly.min.js`, SHA-256 `122e3be346d66616944d0b83eaaf7242581508c3c1cfa0995a17af0d83eff770`. |

Validation totals: `tests/test_platform.py` **41 passed**; `tests/test_submit.py` **4 passed**; AST parsing passed for root `scripts/submit.py` and both 4×4 Python modules. The only command that mentions the solver in the dry-run output reports it was not invoked. The manifest SHA-256 before/after test execution remained `f9e195f4c966c69b4ae0886bee0ef5ba55eff1dde29faa579a3231171b4d8a15`; run-directory count remained 108.

## Workflow findings

- `try.sh` is a thin wrapper around `diagonal_platform.py`. New run allocation now uses both current directories and the append-only experiment manifest/authorized batch IDs; `run_one` rejects a previously completed ID before writing evidence or invoking JoSIM. Historical registered A007/A020-style one-shot validators fail closed rather than reusing their old IDs.
- `experiment_manifest.json` retains all 108 historical rows and raw hashes unchanged. The prune does not rewrite them or assert those old circuits were the V9 source.
- The local submitter now treats a fully missing legacy package checkpoint as a request to establish an in-memory Git-tree baseline from the current manifest and retained, hash-verified, tracked raws. It records the Git commit and raw hashes; it does not need to recreate any old ZIP. Partial legacy package loss still stops with an error. After the first new package, the checkpoint registry records the new package checkpoint while preserving prior checkpoint history.
- With no pending new run, the default local or root-dispatched submit path returns `NO_PENDING_RUNS`; it no longer auto-selects a stale historical `BATCH_MANIFEST`. New manual runs and complete new registered batches use the archive-independent path. Explicit historical modes remain tied to their old data and now fail closed if those inputs are absent.
- The root `scripts/submit.py` dispatcher forwards `--mirror-dir` to the scoped experiment submitter; the isolated dispatcher test uses a temporary mirror and performs no copy.
- The local submit file still carries old A001–A108 checkpoint constants and explicit one-off handlers. Normal/default submit and `--delta` no longer select those handlers when there is no new run. Explicit retired flags are guarded and report missing source run/ZIP inputs. `tests/test_submit.py` retains a few old run-path strings only as pure path-allowlist inputs; it does not open those paths.
- The registered-batch submit probe covered one synthetic registered run, not a 256-row scheduling or packaging stress test. No 256-case runner or batch was added or executed here.

## The nine retained HTML pages

They are ignored/untracked generated files. Their persistence is **local-only**: the approved local cleanup leaves these exact paths untouched, but they are not stored in GitHub, the ZIP packages, or Drive. The committed candidate CSV records their exact paths and current SHA-256. The renderer, raw, probe/plot QA, and shared JS remain available to regenerate them, but this task did not regenerate the pages or promise byte-identical reconstruction on another machine. If cross-machine persistence is required, that needs a separate user-approved storage choice.

| Run | Exact local page | Current SHA-256 |
|---|---|---|
| A018 | `plots/runs/A018_T1_ALL_QUIET/01_t1_overview.html` | `1dddf0399a000d6613197e7164fd794d2903256ca0125c942fed32550c18a14e` |
| A019 | `plots/runs/A019_T1_ALL_PLUSE/01_t1_overview.html` | `e1135f547ad250221db37575fde8e959998a7c352704f752fd530062e3fce216` |
| A027 | `plots/runs/A027_FULL_CB_CHAIN_ALL_CLOCK/02_carry_propagation.html` | `b47b862c07212750acf7528daec87773f6d8dccab121ccadfa50bcfd41d3a9b5` |
| A030 | `plots/runs/A030_CARRY_POST_CB_SJTL_ALL_200/02_carry.html` | `cd258692d9289d23222436f976f5385d690d223706d63dac88b0ab621acba803` |
| A031 | `plots/runs/A031_CARRY_POST_CB_SJTL_ALL_210/02_carry.html` | `ce028376dfc31a3bbeebae322ff6a0343c1d516ea0621a718d743cee3950a362` |
| A032 | `plots/runs/A032_CARRY_POST_CB_SJTL_PAPER_210/04_t1.html` | `27c6c5e811f60105753718d94ba6bcf1404f23a9f9bdecfcc15e7b96b8143186` |
| A033 | `plots/runs/A033_CARRY_POST_CB_SJTL_3X3_210/04_t1.html` | `f7643298d86b7861900ba7dcd1b6af577660400de04a112e76ee409c5d76fbd5` |
| A107 | `plots/runs/A107_MANUAL_CARRY5_11x13_210/00_full_chain_overview.html` | `0dd4d7ae96dc61b5f67f2594593119de2033ae8325021819c47119762707873c` |
| A108 | `plots/runs/A108_MANUAL_CARRY5_3x3_210/00_full_chain_overview.html` | `19fd86f202eeb957189125b41c4a37cb3c509fddc943dc05bdefd39c5d1b0e17` |

## Execution boundary

The technical compatibility blockers for the accepted local set are resolved. **Do not execute the deletions yet.** Execution still requires the user/ChatGPT review and explicit authorization. At execution time, recheck each selected path’s type, presence, byte count, and current SHA where listed; skip any mismatch. The exact execution filter is:

- `RUN_DIRECTORY` + `DELETE_OBSOLETE` — 99 directory roots only.
- `HTML_PAGE` + `DELETE_GENERATED` — 591 individual pages only.
- `HANDOFF_ZIP` + `DELETE_GENERATED` — 138 individual `.zip` files only.

Do not select `RAW_FILE` child rows separately, `MANUAL_BATCH_*` rows, `PACKAGE_QA.json`, the nine `KEEP_REFERENCE` pages, or any Drive row. Do not use `git clean`. Git history/LFS and Drive remain separate storage layers and are not reclaimed by this local working-tree operation.
