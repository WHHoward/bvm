# BVM -> QB 50 GHz repeated-read and MERGE prototype

This is a new append-only exploration experiment. It consumes the current
candidate netlist templates only through rendered per-run snapshots and does
not modify historical experiments or `circuits/standard/MERGE.cir`.

Run order:

```text
A repeated-read -> B rewrite/read -> C standalone MERGE gate
                                      -> D conditional 4-BVM integration
```

The runner writes raw/provenance/QA evidence only. Phase and response-candidate
columns are descriptive/mechanical artifacts; they are not scientific review.
