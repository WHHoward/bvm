---
name: evidence-provenance-review
description: Trace scientific evidence from task and code/config through raw data, derived data, metrics, figures, and claims. Use when RESULT relies on artifacts, CSVs, plots, generated reports, or frozen evidence.
---

# Evidence Provenance Review

A correct calculation on the wrong artifact is still wrong.

## Reconstruct the chain

For each important claim, trace:

```text
TASK parameters
→ code/config
→ execution
→ raw artifact
→ preprocessing
→ derived artifact
→ metric
→ figure/table
→ RESULT claim
```

## Look for broken links

Common problems:

- RESULT points to a file from another run;
- figure and table use different parameter sets;
- derived CSV is older than the implementation;
- analysis script reads a default file instead of the claimed file;
- test uses fixture data instead of current run output;
- preprocessing silently filters important samples;
- filename suggests one case while metadata/config indicates another;
- the same output filename is overwritten by multiple runs;
- current RESULT summarizes an old artifact.

## Freshness

Do not trust timestamps alone.

Stronger evidence:

- rerun a targeted non-destructive verification;
- regenerate into a temporary/ignored location;
- confirm embedded metadata/config;
- compare raw content against current parameters.

Do not overwrite frozen evidence merely to prove freshness.

## Parameter identity

Check high-impact parameters such as:

```text
input amplitude
time range
timestep
window
threshold
node/signal selection
solver configuration
seed/config
```

## Figure integrity

If a figure supports a claim:

- confirm the underlying data match;
- check axes/units/labels;
- ensure cropping or smoothing does not hide contradictory evidence;
- verify the plotted series is the intended signal.

## Output

Report:

```text
provenance complete
provenance partially verified
provenance broken
```

and identify the first broken link.
