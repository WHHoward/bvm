# Publication schematic artifact format

Each schematic package is a descriptive, human-readable view of one selected
JoSIM deck. It is not a scientific verdict and it must not invent components
from a paper figure.

## Required README fields

- source deck path relative to the repository;
- include/subcircuit provenance;
- whether the deck is a representative logical1/read case or a control;
- parameter-only variants represented by the same drawing;
- topology-changing variants that need another drawing;
- note that the diagram is not a scientific verdict.

## Required artifact boundary

The canonical user-facing files are:

- `schematic.svg`: scalable vector schematic;
- `schematic.png`: preview raster;
- `schematic.pdf`: paper/meeting output;
- `schematic.json`: selected deck and semantic placement;
- `schematic-validation.json`: endpoint/provenance validation result;
- `README.md`: source, includes, omissions, and renderer boundary.

The old `topology.svg/.dot` names are reserved for retained
`connectivity-debug.svg/.dot` provenance artifacts and are not canonical
schematics.

## Visual conventions

- inductors are coil symbols;
- resistors are zig-zag symbols;
- Josephson junctions use the project JJ/cross symbol;
- grounds, current arrows, ports, wires, and junction dots are real schematic
  symbols;
- signal flow is left-to-right; bias is above; return/ground is below;
- colors are restrained and carry functional grouping only, such as BVM
  S-Loop blue and R-Loop red;
- source paths, flattened node names, graph ellipses, primitive rectangles,
  and edge labels are not the primary visual language.

## Validation contract

For every displayed component, the semantic description records its scope,
name, type, and endpoint pair. The validator must confirm that the element
exists in the selected deck or resolved subcircuit, that endpoint connectivity
matches, and that no critical path element is silently omitted. Any omitted
simulation/helper element must be listed as `OMITTED FROM DISPLAY, NOT OMITTED
FROM SIMULATION` in the README and semantic manifest.
