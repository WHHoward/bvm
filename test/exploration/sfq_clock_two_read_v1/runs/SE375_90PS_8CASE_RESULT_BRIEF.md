# SE375 90 ps / 78 ps eight-case execution brief

Status: `EXECUTION_COMPLETE / AWAITING_SCIENTIFIC_REVIEW`

- Registration base HEAD: `23a3567b68c1b22b89e7c2d7f2000e79b84f20cb`
- Registered preflight/index commit: `84c5065af2368c1f44924650dd524ae0ea241c2e`
- Solver calls authorized and completed: 8; one per case
- Solver exit code: 0 for all eight
- Platform artifact QA: `ARTIFACT_QA_PASS` for all eight
- Archive QA: one ZIP per run, CRC and member SHA checks passed; each run has a detached `PACKAGE_QA.json`
- Drive: each File ID and exact name/size/parent was read back from the target folder; metadata API did not expose content SHA-256
- `SCIENTIFIC_STATUS`: `NOT_ANALYZED` for all cases
- No multiplication, SFQ-event, or timing-margin conclusion is made here.

## Exact run mapping

| Case | A×B | RUN_ID | Raw SHA-256 |
|---|---:|---|---|
| SE375_T90_D78_A5_B13 | 5×13 | V9R257_SE375_T90_D78_A5_B13 | `3f9456a3093d68a7cd4087d5037e3ef71322022394d4fa2d37f7e67414d56025` |
| SE375_T90_D78_A11_B3 | 11×3 | V9R258_SE375_T90_D78_A11_B3 | `c1b30ecfbf6eeed11ad2cbd2ec47a4b9e4047c4ea7ae5fa8d2484c60a6c15526` |
| SE375_T90_D78_A11_B6 | 11×6 | V9R259_SE375_T90_D78_A11_B6 | `d28e31abf6c7516ad014710893581dd1ab90f8aa51dcfda8f0f9a3d99cee5071` |
| SE375_T90_D78_A13_B5 | 13×5 | V9R260_SE375_T90_D78_A13_B5 | `7f3697aad7b01dbc21ef34f2c2fe58fe658cf7e0fa74f570aad332f2e988132b` |
| SE375_T90_D78_A13_B10 | 13×10 | V9R261_SE375_T90_D78_A13_B10 | `71bee8a299fe7a1b12b9ff8193c3de149f9414ec877761e558d378a479575bc1` |
| SE375_T90_D78_A13_B15 | 13×15 | V9R262_SE375_T90_D78_A13_B15 | `09fcb3ba81e1a052fcf5d691ddd3476fcdbf48d2524a0f5c162508b5b545e545` |
| SE375_T90_D78_A15_B9 | 15×9 | V9R263_SE375_T90_D78_A15_B9 | `c5e32335d5da552886643ec665ccfadae8b1d25e01f70b89ae413bf6df358ffa` |
| SE375_T90_D78_A15_B13 | 15×13 | V9R264_SE375_T90_D78_A15_B13 | `52dac632f938a54bb0b9d4b06b7521bd1a324ff1065f76294fdd9b952796bd8f` |

Full configuration, Git commit identity, ZIP SHA, Drive File ID and cloud metadata status are in `SE375_90PS_8CASE_INDEX.csv`. Raw files are directly readable at `runs/<RUN_ID>/raw.csv`; the standalone eight-output page is `runs/<RUN_ID>/res.html`.

The temporary `USER_CASE.env` edits were restored byte-for-byte to the pre-run default (`V9_A15_B15_80P68`, A=15, B=15; SHA-256 `5e4b92281e3a9191b07619eaa7f0cbc08bfeb598b2ac4336d6a7716637961561`). The V9 template, source closure, platform runner, `try.sh`, and `archive.sh` were not modified.
