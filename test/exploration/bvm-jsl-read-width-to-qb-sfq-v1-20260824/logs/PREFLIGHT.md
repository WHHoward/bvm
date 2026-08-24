# Preflight

- Run mode: lightweight Exploration (`preregistration -> execution -> report`).
- Parent HEAD at preregistration: `955a99e9c70489f6e67ee31c7e9a21de7f4e22ff`.
- Canonical BVM was treated as frozen.
- Existing unrelated dirty path preserved: `circuits/t1/t1_cell.cir`.
- No mailbox/ACK/handoff workflow used.
- No JTL or T1 run was authorized.
- Phase A 9 ps accepted raw, Phase B 9 ps accepted raw, and Phase C 9 ps Q1
  comparator raw are explicitly reused with provenance; new raw is only generated
  for registered 12/15/20 ps or W*=12 replay cases.
- The accepted paper-SL-L0 logical0-read provenance anomaly is retained and
  documented in `manifest.yaml` and `REPORT.md`.
