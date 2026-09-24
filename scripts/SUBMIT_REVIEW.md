# Global submit workflow — adversarial review

Scope: `scripts/submit.py` and the 2026-09-24 scoped commit/package run. No JoSIM execution or raw modification was performed.

## Highest-risk probes

| Hidden-error hypothesis | Probe | Result |
|---|---|---|
| Paths with spaces are parsed/truncated, especially `snapshot (2).zip` | `test_porcelain_parser_preserves_spaces_in_paths` and the N1_10 snapshot bundle plan | PASS; the path remains intact and both attachments are explicitly listed. |
| An experiment `handoff/*.zip` is mistakenly packed as source or recursively included | `test_package_filter_does_not_drop_run_snapshots`; explicit source/package path inventory | PASS; handoff ZIPs are package artifacts, while `runs/N1_10/snapshot*.zip` remain source inputs. |
| A stale prebuilt source ZIP is reused based only on its filename | `verify_existing_bundle` reopens the ZIP, checks CRC, exact member set, every member SHA-256, package bytes, and package SHA against detached QA | PASS for all three source bundles. |
| Component plots are bound to stale or altered raw | `component_bundle_specs` checks all 20 plot hashes and each run's current raw SHA against both plot manifest and canonical raw PACKAGE_QA | PASS for N0_00, N1_01, N1_10, N2_11. |
| A package can silently exceed ordinary Git's 100 MB object limit | Dry-run uncompressed per-family sizes; writer enforces both source and final ZIP size below 100,000,000 bytes | PASS in the plan; actual compressed size is checked before finalizing each ZIP. No LFS fallback is present. |
| Dry-run stages, writes, retires, or mirrors files | `--dry-run` output plus before/after `git status` | PASS; dry-run is read-only. |
| The old 160,457,019-byte generated aggregate is overwritten or retired without replacements | Exact path/hash/QA/type/size checks; retirement is gated by `--retire-overlimit-generated` and occurs only after split bundle QA | PASS by design; it is not tracked and will only be retired after all replacements pass. |

## Residual uncertainty

The three `2x1-bvm-qb-c-sim1*` source bundles preserve the supplied decks, `data_tran.csv`, `111.html`, source snapshots, and run helper exactly. Their package QA certifies archive/member integrity only; it does not independently certify solver identity, run provenance, raw semantics, or scientific validity. The bundles must not be treated as accepted physical conclusions.

The current submit run uses `bvm/master` as push upstream. Any GitHub rejection leaves local commits and QA-passed archives intact and the Drive mirror pending; the script does not force-push or silently switch to LFS.
