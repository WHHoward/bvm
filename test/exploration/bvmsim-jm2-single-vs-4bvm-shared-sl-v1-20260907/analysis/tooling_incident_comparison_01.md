# Tooling incident COMPARISON-01

- First complete renderer QA: `2026-09-07T13:xx:xx+08:00`.
- Finding: the initial comparison-input builder emitted only `ARRAY - SINGLE` columns. The renderer generated all pages, but `viz_qa.json` correctly failed the required RAW + RAW + DELTA structure.
- Effect: no raw, deck, log, metadata, or physical result was changed.
- Correction: comparison inputs now emit, for every observable, SINGLE original, ARRAY target original, and ARRAY minus SINGLE delta; phase columns remain continuous unwrapped radians.
- Preservation: the failed comparison CSVs, HTML pages, manifest, and viz QA are retained under `analysis/attempts/COMPARISON-01/` and `analysis/attempts/RENDER-04/`.
