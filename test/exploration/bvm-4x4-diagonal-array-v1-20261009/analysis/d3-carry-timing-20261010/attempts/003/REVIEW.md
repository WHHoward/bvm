# Adversarial implementation review — A040/A041 preflight

Scope: platform topology/config/probe/preflight/package implementation only. No raw physical interpretation.

| Hidden-error hypothesis | Probe | Result |
|---|---|---|
| PRE-CB count 0/2 could route around the Carry CB, bypass JOIN, or put the second sJTL on the wrong side of the CB. | Explicit D3 deck line-set check in `d3_carry_timing_batch.py`; unit test asserts the exact two-device/interstage topology; JoSIM `-s` syntax check. | PASS: 0 preserves one CB and direct carry input; 2 is sJTL→sensor→sJTL→CB→JOIN. |
| New list/mask/legacy controls could silently override one another or accept a mismatched stage. | `test_per_stage_carry_sjtl_count_rejects_ambiguous_or_mismatched_controls`; explicit A040/A041 effective count/mask assertions. | PASS: mismatches and legacy/new conflicts are rejected. |
| Two serial devices could render but the second JJ or interstage current/node might be absent from raw. | Probe-manifest assertions for both BJ1 P/V pairs, midpoint nodes and link current; deck/probe target validation. | PASS: all registered targets exist in the rendered circuit and exact `.print` set. |
| Adding the optional count key or changing focus selection could perturb historical A027–A039 renderings. | Render-only exact deck, stimulus and ordered probe-label comparison against all 13 immutable run snapshots. | PASS; no historical solve or artifact write. |
| A stale ID, raw, or package checkpoint could cause overwrite or re-copy historical evidence. | Preflight checks A040/A041 paths and manifest IDs; records SHA-256 for A027–A039; DELTA dry-run verifies A001–A039 reference closure and excludes HTML. | IDs free and historical hashes captured. Package QA remains PENDING until the two new raw artifacts exist. |

Attempts 001 and 002 were superseded before any physical solve. Attempt 001 used a net probe-count delta for raw sizing. Attempt 002 corrected sizing but required two preflight commits because ignored JSON artifacts needed explicit staging, which did not satisfy the direct-parent execution lock. Attempt 003 retains the corrected estimate and places the complete machine-readable preflight in one commit.

Residual uncertainty: physical behavior, adaptive stored-grid size for A040/A041, and whether any waveform descriptor corresponds to a switching/event interpretation remain UNKNOWN until raw review. No scientific interpretation, event/SFQ classification, or follow-up is authorized.
