---
name: josim-exploration-visualization
description: Create and maintain JoSIM Exploration result visualizations, netlist-derived topology SVGs, and the linked flow/visualization indexes. Use when an Exploration gains new raw plots, needs missing operating-point comparisons, or needs a structure diagram.
---

# JoSIM Exploration visualization

Use this skill for the documentation layer around an Exploration. It does not
run JoSIM, change a scientific circuit, or turn a plot into an event/Gate
verdict.

## Required outputs

For each affected Exploration:

1. Inspect the actual CSV headers, raw/run directories, report, and selected
   `.cir` fixture.
2. Put result plots under that Exploration's `plots/` directory. Use the
   repository plotting conventions; phase is radians in raw CSV and only
   `combined`/`sep_comb` layouts may display normalized `rad/2π` phase through
   `josim-plot2.py`.
3. Put a netlist-validated schematic package under `topology/`:
   `schematic.svg`, `schematic.png`, `schematic.pdf`, `schematic.json`,
   `schematic-validation.json`, and a short `README.md` naming the source
   deck, included subcircuits, representative variants, and any elements
   intentionally omitted from the drawing. The schematic is a publication
   electrical schematic with deterministic semantic placement, not a graph
   layout. `connectivity-debug.svg/.dot` may be retained as provenance only.
4. Update both `docs/VISUALIZATION_INDEX.md/.html` and
   `docs/EXPLORATION_FLOW_INDEX.md/.html`. Each affected node should expose
   separate result-plot and topology links.

## Scientific display boundary

- Plot only signals that exist in the CSV header; never invent wildcard probe
  names.
- A phase turn, voltage peak, derivative spike, or `I > Ic` is activity, not
  an SFQ event. Keep report verdicts and visualization descriptions separate.
- If a result compares several K/bias/AREA/L points, show the complete
  registered matrix, not only the representative point. Label controls and
  operating points explicitly.
- A topology drawing is a structural aid. It must not add components inferred
  from a paper figure but absent from the chosen netlist.

## Schematic/topology workflow

The publication schematic pipeline is:

`.cir` → netlist/include parser → semantic schematic description →
deterministic manual layout → schematic renderer → endpoint validator.

The selected `.cir` deck and resolved includes are the only connectivity
authority. Use project-local symbols for inductors, resistors, Josephson
junctions, grounds, current arrows, ports, nodes, and mutual windings. The
layout grammar is left-to-right signal flow, top bias, bottom return, and
explicit branch placement. Every displayed endpoint must be validated against
the selected netlist before the schematic is accepted.

The historical Graphviz helpers may still produce a connectivity-debug graph
for provenance, but they must not be presented as the canonical structure
figure and must not be cosmetically tuned into a schematic.

## Matrix plot workflow

Use `scripts/plot_case_matrix.py` with a JSON manifest for multi-operating-point
plots. A manifest must name every CSV, exact column, panel meaning, phase-unit
conversion, and control/variant label. The script writes a standalone Plotly
HTML and does not rerun simulation.

## Batch workflow for a completed Exploration set

Only run a whole-project refresh after explicit user authorization. The old
Graphviz topology helper is debug/provenance-only; it is not a replacement for
the semantic schematic pipeline. For a prototype, work on one selected
Exploration and stop for visual review before extending the renderer.

1. `scripts/generate_classic_overviews.py --root test/exploration` adds one
   descriptive `plots/overview.html` only to directories that have raw CSVs
   but no existing HTML plot. It preserves all available raw cases and uses
   exact headers.
2. Do not call the old Graphviz topology generator to create canonical
   schematics. A future batch schematic driver must parse the selected deck,
   consume an explicit semantic layout, run endpoint validation, and write
   `schematic.*`; directories without an independent deck must use an
   explicitly recorded inherited frozen fixture.
3. `scripts/update_indexes.py --repo-root .` adds result-overview, topology,
   reference-image, and matrix links to both Markdown and HTML indexes.

These helpers are documentation-only: they read existing raw/netlist/report
artifacts and never invoke JoSIM. Re-run the skill validator after changing the
skill itself, then validate all local links and generated SVG/XML before the
checkpoint commit.

## Index workflow

Read the existing indexes before editing them. Preserve direct links to the
original report and raw-derived plot. Keep a node's text in the four layers
`Observed`, `Derived`, `Inference`, and `Unknown` when adding a new scientific
summary. Validate every local HTML/Markdown/SVG link, check non-zero files,
run `git diff --check`, and commit the visualization/topology/index update as
one documentation checkpoint.

For detailed schematic labels and the generated-artifact contract, read
`references/topology-format.md` when changing the generator.
