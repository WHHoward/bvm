# Topology artifact format

Each topology package is a descriptive view of one selected JoSIM deck.

## Required README fields

- source deck path relative to the repository;
- include/subcircuit provenance;
- whether the deck is a representative logical1/read case or a control;
- parameter-only variants represented by the same drawing;
- topology-changing variants that need another drawing;
- note that the diagram is not a scientific verdict.

## SVG conventions

- primitive components are rectangular nodes with name, type, and value;
- electrical nets are ellipses labelled with the exact flattened net name;
- mutual coupling is a diamond/edge object, not a hidden connection;
- hierarchy clusters use BVM/source, receiver/detector, QB/DCSFQ, JTL, and
  load/bias colors only when the netlist hierarchy supports that grouping;
- `dot` output is preferred over hand-positioned artwork so labels and edges
  remain non-overlapping at different display sizes;
- include a small legend and source-deck footer in the SVG.
