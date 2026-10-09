# Full CB-only carry chain A027-A029 preflight

This experiment is governed by docs/EXPERIMENT_CONTRACT.md.

- Parent HEAD: `fb5139b8b0f6a084b75fcf6343faaddbfcbee104`; batch: `BVM4X4_CB_CARRY_BUFFER_ALL_20261009`; risk: `NORMAL`.
- Exactly three physical solves are authorized: `A027_FULL_CB_CHAIN_ALL_CLOCK, A028_FULL_CB_CHAIN_PAPER_CLOCK, A029_FULL_CB_CHAIN_3X3_CLOCK`.
- Solver: `/home/howard/JoSIM/build/josim-cli`, v2.7.2837d13 compiled on May 30 2026 at 20:37:57, SHA-256 `48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2`.
- Canonical CB_0928 remains unchanged; SHA-256 `70a6af05acccb7c354799d5b1b7542c86c677970681473f559bbf0f7e4d6d370`, ports `IN OUT`.
- D1-D6 each have independent JOIN nodes; current Carry alone passes through a single canonical CB; array DOUT directly joins and drives its T1 input.
- No `XCBU_D1..D6` MERGE instance, join-output CB, added sJTL/JTL, or terminal Carry/DOUT load.
- Array CB=16, array sJTL=20, T1=7, DFF=1; D0 entrance JTL unchanged.
- Frozen stimulus and parameters: 400u shared WL/BL, 100u cell SE, one global clock at 200 ps, 1.2m, 1/2/1 ps, 2Ω; DT=0.01p, STOP=300p.
- Raw phase is radians; displayed turns are navigation only. Phase/area comparisons use the same JJ and exact half-open raw rows.
- Descriptive waveform-lobe candidates are not event counts. No automatic bit decoder, SFQ classifier, mechanism verdict, or optimization is authorized.
- If a solver/artifact hard failure occurs, stop remaining runs. If solver/QA succeeds but output differs from theory, preserve the negative observation and continue only the remaining registered cases.

## Registered cases

| Run | ROW/COL | Diagonal population reference | Stage inputs reference | Product/bit reference | Probe count / raw estimate |
|---|---|---|---|---|---|
| A027_FULL_CB_CHAIN_ALL_CLOCK | 1111/1111 | [1, 2, 3, 4, 3, 2, 1] | [1, 2, 4, 6, 6, 5, 3] | 225 / 10000111 LSB-first | 232 / 89611726 B |
| A028_FULL_CB_CHAIN_PAPER_CLOCK | 1101/1101 | [1, 1, 1, 3, 1, 1, 1] | [1, 1, 1, 3, 2, 2, 2] | 143 / 11110001 LSB-first | 232 / 89611726 B |
| A029_FULL_CB_CHAIN_3X3_CLOCK | 1100/0011 | [1, 2, 1, 0, 0, 0, 0] | [1, 2, 2, 1, 0, 0, 0] | 9 / 10010000 LSB-first | 232 / 89611726 B |

## Static gate

- A029 current row/column mapping was independently enumerated from `d=r+3-c`; result is R1C3/R1C4/R2C3/R2C4 → [1,2,1,0,0,0,0].
- A025/A026 raw identity and QA checked; legacy A021/A022 MERGE, A023/A024 CB_DIRECT, and A025/A026 single-stage carry-buffer renders were compared byte-for-byte.
- Three candidate decks passed JoSIM `-s` syntax/model checks; physical solve count remains zero until the locked batch is run.
- Full probe list, hashes, source closure, output estimates and static QA are in `PROBE_MANIFEST.json` and `STATIC_QA.json`.
