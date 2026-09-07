# Visualization regeneration

The pages in `single/`, `array/`, and `comparison/` are descriptive outputs.
They were rendered with:

```text
scripts/josim-plot2.py -t sep_comb -c dark -j 2pi
```

The raw CSVs under `runs/` are immutable. `analysis/analyze.py` creates derived
CSV inputs from those raw files; phase inputs remain continuous radians and
`-j 2pi` performs the display conversion to turns. `comparison/` pages contain
SINGLE original, ARRAY target original, and ARRAY minus SINGLE traces together.

Regeneration must be performed in a new analysis/render attempt if an existing
artifact would otherwise be overwritten. `analysis/plot_inputs.json`,
`plot_manifest.json`, and `analysis/viz_qa.json` record the inputs and hashes.
