# User-platform refactor record

This is a read-only platform change. It is governed by
`docs/EXPERIMENT_CONTRACT.md`.

- Physical solve count in this refactor: `0`
- Existing A000–A003 raw/deck/metadata/config snapshots: preserved
- Existing A000–A003 raw hashes: rechecked and unchanged
- New daily control surface: `USER_CASE.env`
- New daily entry point: `try.sh`
- New stable review entry point: `LATEST_REVIEW.html`
- Future generated namespace: `U001_NAME`, `U002_NAME`, …
- `MASKS=quick`: `0001,0011,0111`
- `MASKS=full`: `0000,0001,0011,0111,1111`
- `P(...)` remains raw radians; turns are navigation only.
- This refactor does not select a winner, classify a one-shot candidate, or
  interpret any physical mechanism.

The future `try.sh` path snapshots the complete user config, stimulus, actual
deck, source hashes, raw data, metadata, signal manifest, dynamic windows,
analysis, and compact visualization inside the generated U case. Existing
legacy Stage-A artifacts remain the immutable reference set.

