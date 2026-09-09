# V2.1 system-chain presentation revision

V2.1 is a versioned read-only extension of the committed V2 visualization. It
does not replace V2 files and does not change the five source raw files.

Every subsystem page is ordered as:

`INPUT BOUNDARY -> INTERNAL STATE -> OUTPUT BOUNDARY`

The five fixed main categories are:

1. `01_SIGNAL_TIMING`
2. `02_BVM_STATE`
3. `03_JSL_CHAIN`
4. `04_QB_STATE`
5. `05_JTL_CHAIN`

Every standalone main category now has an `OVERVIEW_0_200ps` page in addition
to its focused windows. Family comparisons preserve overview, system-critical
and final-read windows, with the registered QB/JTL `110_130ps` views.

V2.1 uses only exact stored-row slices and independent phase unwrap for display.
`P(...)` remains raw radians; `rad/(2*pi)` display is not an SFQ count. The
JSL boundary overlap is intentional: `I(B_JSL1)` and `I(B_JSL8)` are shown both
as semantic boundary context and within the internal JSL chain using distinct
display labels, while their exact raw source labels remain in the manifest.

The parent V2 manifest and raw reference hashes are recorded in
`raw_reference.json`; V2.1 QA is in `visualization_qa.json` and enforces the
three semantic completeness gates.
