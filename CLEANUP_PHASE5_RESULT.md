# Cleanup Phase 5 Result

- **HEAD:** `9822b49f6b120f9c260dd3cdea86789163464021` before and after.
- **Worktree:** clean before the audit outputs were added; no experiment or circuit files changed.
- **Actual reclaim:** 355 exact ignored/untracked HTML files; 8,059,925,226 logical bytes and 8,060,649,472 allocated bytes. Immediate `df` free-space delta measured 8,041,865,216 bytes.
- **Execution:** 355 deleted, 0 skipped, 0 failed. One completed unlink was reconciled after a ledger-script field-name error; its path, SHA, raw SHA, and replacements were independently checked. No directory recursion.
- **Retained:** all raw CSVs, decks, stimuli, logs, models, manifests, tracked HTML, and unique review pages. V0–V9 remain untouched; V9_analysis file hashes match the pre-cleanup snapshot.
- **Not performed:** JoSIM, Drive/D writes or deletes, sparse-checkout, Git GC/LFS prune, history rewrite, topology/config edits.
- **Reports:** `CLEANUP_PHASE5_REPORT.md`, `CLEANUP_PHASE5_ACTIONS.csv`, `HISTORICAL_COLD_ARCHIVE_PLAN.md`, and this result file.
- **Cold archive:** no raw or experiment directory moved or removed. Candidate order is 4×4 runs → QB-CB runs → R-loop runs → narrowly scoped 2×2 verified run files, each only after the closure steps in the plan and separate authorization.

## Audit checks

- Adversarial scope check: every Phase 5 unlink path is present in the preapproved 355-row ledger; no path outside the exact whitelist was unlinked.
- Evidence integrity check: linked raw hashes and the V9_analysis SHA snapshot are unchanged; generated HTML is not treated as raw or as physical-event evidence.
- Numerical accounting: logical byte sum, allocated-block sum, experiment-root snapshot, and immediate free-space delta are reported separately; the small filesystem accounting difference is disclosed rather than hidden.
- No physical or scientific conclusion was made from page counts, file hashes, or storage state.

The four report files are local deliverables and have not been committed or pushed. No further cleanup is authorized or performed.
