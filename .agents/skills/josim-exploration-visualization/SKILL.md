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
   `schematic.svg`, `schematic.png`, `schematic.pdf`, and, when an annotated
   view is useful, `schematic-annotated.svg/.png/.pdf`; retain
   `schematic.json`, `schematic-validation.json`, a geometry ledger and
   geometric validation result, and a short `README.md` naming the source
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
deterministic manual layout → schematic renderer → endpoint validator →
geometric endpoint validator.

The selected `.cir` deck and resolved includes are the only connectivity
authority. Use project-local symbols for inductors, resistors, Josephson
junctions, grounds, current arrows, ports, nodes, and mutual windings. The
layout grammar is left-to-right signal flow, top bias, bottom return, and
explicit branch placement. Every displayed endpoint must be validated against
the selected netlist before the schematic is accepted. The renderer must also
emit a coordinate ledger and prove that every wire endpoint coincides with a
component terminal, junction anchor, port, ground, or current-arrow terminal;
semantic agreement alone does not certify visual continuity.

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

1. `scripts/generate_classic_overviews.py --root test/exploration --force
   --output-name alignment-overview.html` may add a case-complete descriptive
   overview for an explicitly authorized completed set. It preserves all
   available raw cases, uses exact headers, and records metadata; never infer
   completeness from the presence of `overview.html`.
2. Do not call the old Graphviz topology generator to create canonical
   schematics. A future batch schematic driver must parse the selected deck,
   consume an explicit semantic layout, run endpoint validation, and write
   `schematic.*`; directories without an independent deck must use an
   explicitly recorded inherited frozen fixture.
3. `scripts/build_visualization_alignment.py` writes the V2 manifest, topology
   manifest, audit, reading guide, schematic index, and both indexes from one
   source. The historical `scripts/update_indexes.py` is not a V2 index
   generator and must not be used as the final mapping source.

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

## Alignment V2: permanent provenance rules

The machine-readable source for the two result indexes is
`docs/VISUALIZATION_ALIGNMENT_MANIFEST.yaml`. Do not maintain an independent
experiment-to-plot mapping in `EXPLORATION_FLOW_INDEX` or
`VISUALIZATION_INDEX`; both pages must be generated from that manifest.

1. HTML existence is not visualization completeness. Completeness means that
   every registered `required_case` has a plot provenance entry, or an explicit
   documented visualization exemption.
2. A comparison claim requires a comparison plot covering every registered
   comparison case. A single operating-point HTML is never a substitute for a
   matrix comparison.
3. `RESULT`, `COMPARISON`, `POSITIVE_CONTROL`, `NEGATIVE_CONTROL`,
   `ZERO_CONTROL`, `SOURCE_REFERENCE`, `HISTORICAL_REFERENCE`, and
   `SUPERSEDED_REFERENCE` are semantic roles, not filename conventions.
   Source/reference/control plots must not become a current result's primary
   evidence by alphabetical ordering.
4. Every phase plot declares one of `continuous_absolute`,
   `relative_to_baseline`, `event_delta`, or `settled_well`. Raw JoSIM
   `P(...) / (2*pi)` is labelled continuous phase φ/2π (turns), is not
   automatically an SFQ count, and must not be called a phase jump without a
   registered delta calculation.
5. The manifest is the only index authority. The alignment verifier must
   check raw provenance, required-case coverage, plot role, report
   classification, comparison completeness, polarity/convergence completeness,
   topology links, and MD/HTML index agreement.
6. Superseded and historical evidence remains reachable for provenance but
   cannot be the current core result. In particular, a paper-original QB plot
   cannot support a scaled-QB exactly-one claim.
7. Publication schematic, experiment-annotated schematic, and Graphviz
   connectivity-debug graph are different artifact classes. Graphviz is debug
   only; it must never be the default publication schematic link.
8. A topology signature is based on resolved electrical connectivity and
   external boundary, not on a directory name. Parameter-only variants may
   share a clean schematic; load/interface/mutual/source-boundary changes need
   a distinct topology declaration or a validated abstraction.
9. Visualization describes existing raw/report evidence and never changes a
   scientific verdict, event count, or Gate disposition.
10. Run `scripts/verify_visualization_alignment.py` and its regression tests
    before an alignment checkpoint. A result is acceptable only when the
    verifier reports `result_alignment`, `topology_alignment`,
    `schematic_alignment`, `index_alignment`, and `phase_semantics` all
    `PASS`.

The legacy `update_indexes.py` and Graphviz topology helpers are not allowed
to become the final V2 renderer. Use them only for historical/debug
provenance, or replace them with the manifest-driven builders.

For detailed schematic labels and the generated-artifact contract, read
`references/topology-format.md` when changing the generator.
