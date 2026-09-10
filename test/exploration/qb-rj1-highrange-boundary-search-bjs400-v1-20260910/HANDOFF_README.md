# High-range RJ1 boundary search under frozen BJS400 D working point

This is an evidence-only handoff. Scientific interpretation is NOT_PERFORMED.

The fixed working point is L1=1.6pH, IBias=260uA, BJS area=4/Ic=400uA.
The new physical RJ1 values are 20/24/32/48ohm. Historical RJ1 values
10/12/14/16ohm for masks 0001 and 0011 are copied as immutable read-only
references from the preceding RJ1 characterization experiment.

All runs preserve the unchanged history:
WRITE0 -> ZERO_STATE_READ_CONTROL -> WRITE1 -> SETTLE -> mask-selective FINAL
READ -> TAIL. Only masks 0001 and 0011 are used.

Each new run has exactly three raw-direct whole-run HTML pages. Exactly two
full-trend comparison pages cover RJ1=10/12/14/16/20/24/32/48ohm. Comparison
temporary CSV files are created under /tmp and deleted after rendering. No
focused-window, event/SFQ, mechanism, ranking, tuning or follow-up artifact is
authorized.

