# Evidence manifest — V0_15x15_T70

Status: `ARTIFACT_VALID / OUTPUT_AREA_SCREEN_FAIL / SFQ_EVENT_COUNT_INCONCLUSIVE`.
Exactly one JoSIM physical solve was invoked. Scientific interpretation was not
performed. `RUN_MANIFEST.json` records solver identity, command, actual execution
HEAD, raw/log hashes, and the postprocessing-only QA repair.

| Evidence | Repository-relative path | SHA-256 | Package note |
|---|---|---|---|
| Experiment definition | `experiment.yaml` | `4f223714a826619c1afc88ca0ca4f8d4b765a1780f205fd7f862cdf14f9a6f9a` | include |
| Preflight | `PREFLIGHT.md` | `1c50bf1cd056a0bc5e4cd3b800093b7a1d528bbe5e610c0376e708a741609571` | include |
| Effective config | `CASE_CONFIG.json` | `c8f63138523fd743096ea405bce429507f2d7182b7ce5828b4cff92d97fb1e5d` | include |
| Executed deck | `deck.cir` | `71becb54893d02068a1c6068e078a259040d604ae22ce6bb7957ecc603d0b17a` | include |
| Frozen deck template | `deck.template.cir` | `74f7ee648b1be165a531bb808e8854c2c6a76bb472d732ae701598f89a85a7ea` | include |
| Stimulus | `stimulus.inc` | `b1337be290d66f812700403611bb8f242dbc66101dded662eea23acb2eb5f6db` | include |
| Frozen sources and hashes | `SOURCE_MANIFEST.json` | `c43430f3b81889b29e6adadd51aa383020c153ed12daf1824175aae39eceaf96` | include; 11 source snapshots also included |
| Runtime provenance | `RUN_MANIFEST.json` | `0a705b50f8785a534c31d18fe2e3c4ea96a0450893e4ff50727df2028e4a6a01` | include |
| Reusable runner | `run.sh` | `5679fd9226edd6ec39fbfe217923816b23a8e4666920e2b8fc8dc711e2ba8d4a` | include; current QA/check version; solve version is separately hash-recorded in RUN_MANIFEST |
| Immutable raw | `raw.csv` | `b507bb6c82a5a6be33a71a4babd6e352122bdf43184cdaf50c8cff381de945cb` | include; 9,077,198 bytes |
| Solver log | `run.log` | `bb61d6c1149b5520bd1f143045d1122a50bbf4c753ca091b712129435f576c47` | include; 3,614,550 bytes |
| Mechanical output QA | `output_qa.json` | `577cde5604668ad35afcfc280578a9da6fe30716d0f21826c4eda6255c82c7c0` | include |
| Three-round bit table | `THREE_ROUND_BIT_TABLE.md` | `abd9f4919418a784334f7b97688aefc9fce7428bdcb049f4435be4e4223c8982` | include |
| Visualization manifest | `visualization_manifest.json` | `fedf746a61c70bcf1ab47d9507566c28ab337645146f02eb0448f96a35fcf053` | include |
| Visualization QA | `visualization_qa.json` | `3a8819512e91b435090bc0d5e6cbf29b905a30e9250fa8721b35563abb634734` | include |
| Final-output HTML | `res.html` | `8a8c42ade3cdcda1d0660529b2049615acabd4f5c308baf12603d8913bdde4e5` | local/Git only; explicitly excluded from ZIP |
| Result brief | `RESULT_BRIEF.md` | `4111803622c44615d272cfba2fb055ace79395e988d408bd831d92ead5183201` | include |
| Raw analysis handoff | `RAW_ANALYSIS_HANDOFF_MANIFEST.json` | `02a99352f978d9b248cb209a35d32cadd78ae8d7427035a7ec7e307f980453ed` | include |

The raw is byte-identical before and after mechanical QA (`raw_sha256` above).
All voltage-area arithmetic uses actual stored timestamps and is not an SFQ
event count. `res.html` is a classic `josim-plot2.py` view of the eight final
output voltage traces only; it is excluded from the evidence ZIP by default.

`RUN_MANIFEST.json` records the first postprocessor endpoint-check failure and
the successful analysis-only repair. Both used the same raw SHA; the second
attempt invoked no solver.
