# Exploration prune result — 2026-10-15

## Outcome: blocked before deletion

The requested freeze tag was created and verified on the remote before any pruning:

- Branch/commit frozen: `master` / `e290f69c8259ff389a7dc1d457b869ee06891d26`
- Tag: `exploration-precleanup-20261015`
- Remote annotated tag object: `4344348d4e0d138baf6aaf44acdc841e82e6fe40`
- Remote peeled commit: `e290f69c8259ff389a7dc1d457b869ee06891d26`

The dependency check found that the protected 4×4 platform directly requires a tracked Plotly asset stored inside one of the proposed retirement directories. Deleting that directory would break static validation and visualization in the protected platform. This meets the task's explicit stop condition. Therefore **no retirement directory or file was removed**, and no cleanup was attempted after discovery.

| Measure | Result |
|---|---:|
| Non-protected direct experiment directories identified | 156 |
| Tracked files in those targets | 25,640 |
| Tracked logical / allocated bytes in targets | 37,828,372,223 / 37,891,248,128 B (potential only) |
| Ignored files in those targets | 5,599 |
| Ignored logical / allocated bytes in targets | 8,358,765,900 / 8,371,056,640 B (not tagged; not deleted) |
| Actual tracked / ignored files removed | 0 / 0 |
| Actual worktree space reclaimed | 0 B |
| JoSIM runs | 0 |
| Git history rewritten / Drive or D: changed | No / No |

The three protected direct experiment directories were excluded from every retirement target. The exact path inventory and disposition are in [EXPLORATION_PRUNE_PATHS.csv](EXPLORATION_PRUNE_PATHS.csv). Because the stop condition applies to the retirement operation, all 156 tracked target directories remain in place. Ignored/untracked content also remains untouched; the tag does not preserve it.

## Required follow-up before pruning

Provide a repository-root or otherwise protected Plotly JS dependency and explicitly authorize the minimal platform-path change, or authorize preserving the single dependency-bearing file/directory. Until then, the 4×4 platform's static/plot path is not closed under the proposed retirement. The protected platform files were not modified in this task.

The separate 4×4 internal review is planning only. No A-run, manual batch, HTML, raw, or ZIP was removed; see [BVM4X4_PRUNE_REVIEW.md](BVM4X4_PRUNE_REVIEW.md) and [BVM4X4_PRUNE_CANDIDATES.csv](BVM4X4_PRUNE_CANDIDATES.csv).
