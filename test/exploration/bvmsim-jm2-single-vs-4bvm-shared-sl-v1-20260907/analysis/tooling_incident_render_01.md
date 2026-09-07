# Tooling incident RENDER-01

- First renderer attempt: `2026-09-07T13:24:xx+08:00`.
- Failure: the HTML QA searched for a literal `/` in Plotly's JSON-escaped axis title and did not decode `\\u002f`.
- Effect: `CONTROL.html` and `BVM_STORAGE.html` were generated; the renderer stopped before the remaining pages and wrote no manifest or viz QA.
- Correction: decode the JSON slash escape before checking the phase-axis label.
- Preservation: the two pages from this failed renderer attempt are retained under `analysis/attempts/RENDER-01/`.
