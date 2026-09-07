# VIZ-01 — superseded visualization QA record

- Status: **SUPERSEDED**
- The five HTML pages were rendered successfully, but the first QA pass treated Plotly's bundled JavaScript text `Unknown encoding` as an axis error and did not decode Plotly's `\\u002f` JSON slash escape before checking visible labels.
- The HTML files remain in `plots/` and are reused after correcting the QA checks; no raw data or plot-input CSV was changed.
