# PREFLIGHT — SE375 90 ps timing contrast (8 cases)

This experiment is governed by docs/EXPERIMENT_CONTRACT.md.

- experiment_id: `SE375_90PS_8CASE`
- experiment_risk_level: `NORMAL`
- parent HEAD: `23a3567b68c1b22b89e7c2d7f2000e79b84f20cb`
- platform: `test/exploration/sfq_clock_two_read_v1/`
- protocol/topology: existing `V9_SHARED_ROW_SE_BL`; no topology or model changes
- authorized physical solves: exactly one for each of the eight rows in `SE375_90PS_8CASE_INDEX.csv`
- old FULL256 raw/decks/manifests/ZIPs: immutable; no overwrite or cleanup
- scientific interpretation: `NOT_ANALYZED`; the supplied anomaly labels and expected products are user/ChatGPT context only, not mechanical acceptance criteria
- automatic retries/follow-up/parameter changes: prohibited

## Changed and frozen configuration

Only `CASE_NAME`, `A`, and `B` vary among cases. Shared values for all eight:

```ini
PROTOCOL=V9_SHARED_ROW_SE_BL
ROUNDS=3
READ_INTERVAL_PS=90
CLOCK_PERIOD_PS=90
SE_CLOCK_DELAY_PS=78
WRITE_START_PS=50
FIRST_READ_PS=110
DT_PS=0.01
STOP_PS=450
WL_WRITE_AMPLITUDE=400u
BL_WRITE_AMPLITUDE=400u
BL_READ_AMPLITUDE=400u
SE_READ_AMPLITUDE=375u
PROBE_PROFILE=OUTPUTS
CUSTOM_PROBES_FILE=
```

Expected generated starts, to be checked by each `./try.sh --dry-run`:

- READ: `110 / 200 / 290 ps`
- clock PWL: `188 / 278 / 368 ps`
- probes: exactly the eight default output voltages; no custom probes

Frozen circuit/source closure is the active V9 `template/source_manifest.json` closure, validated by the platform before each solve. HEAD-pinned source-manifest SHA-256: `3e1d6ba694aad927c4797e9282163c8a4d65e5f0527f3c01d99a77eb2b0346d4`. Deck-template SHA-256: `2ea1cee249ad8939003b1108fda41a65dda81e12afd43d53fefaecb4c529392b`. Platform SHA-256 at registration: `eb597d0e8d63913c0059445ca8e13107e44a82b8deed2ab983d900c8cb724233`.

Recorded solver identity: `/home/howard/JoSIM/build/josim-cli`, `v2.7.2837d13 compiled on May 30 2026 at 20:37:57`, SHA-256 `48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2`.

## Exact run set and evidence boundary

The eight `(A,B)` pairs are exactly those in the index. `EXPECTED_PRODUCT=A*B` is descriptive arithmetic metadata only. It is not used in preflight, raw QA, or a functional verdict.

Each case will use `./try.sh --dry-run`, then exactly one `./try.sh --run-local`. The platform must preserve immutable raw, rendered deck/stimulus/config snapshot, source snapshots, manifest, log, and standalone `res.html`. The default platform archive function will create one self-contained ZIP per run under `/mnt/d/BVM_Backages`, without deleting raw. After Drive list/metadata readback, Drive File ID and metadata-only verification are recorded in the batch index; Drive content SHA is not assumed available. Archive receipts retain the platform's ZIP/member/CRC QA.

Mechanical acceptance only: solver exit 0; platform status `ARTIFACT_QA_PASS`; exact eight output probes; raw integrity/time monotonicity/SHA recorded by the platform; immutable source closure; and archive identity/receipt. No waveform or product correctness analysis is performed. Failure of a mechanical gate stops the remaining cases and preserves all completed/failed artifacts.

After the eight cases, `USER_CASE.env` will be restored byte-for-byte to its pre-run SHA-256 `5e4b92281e3a9191b07619eaa7f0cbc08bfeb598b2ac4336d6a7716637961561`. Existing FULL256 index and historical evidence remain untouched.

The final handoff is limited to run IDs, solver/artifact QA, raw and archive hashes, Git commits, Drive metadata status, and this index. Scientific status remains `NOT_ANALYZED`; stop after commit/push and archive verification.
