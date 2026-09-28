# Static implementation review

Scope: platform construction only. No JoSIM invocation or physical run occurred.

## Adversarial checks

- **No-op / source count:** the generated INDEPENDENT deck has 12 cell-level
  current sources (four each for WL/BL/SE); SHARED has exactly six sources
  (two each). A static test checks the rendered source count and nodes.
- **Wrong topology / accidental short:** SHARED connects each row WL to its
  two cells and each column BL/SE to its two cells. WL, BL, and SE node sets
  are pairwise disjoint; BL_C1 is not SE_C1. Four outputs each terminate in
  their own 2 Ω resistor and are not merged.
- **Wrong bit order / wrong branch:** leftmost ROW bit means R1 and leftmost
  COL bit means C1. For 10/10 the renderer reports R1C1 active, R1C2/R2C1
  half-selected, R2C2 unselected; for 11/11 it reports all four active.
  Tests compare each generated final WL/SE PWL to the corresponding row/column
  bit and require every final BL source to be zero.
- **Initial-state leakage:** tests verify WRITE0, READ0, and WRITE1 are present
  on all four cells independent of row/column selection; the bit strings gate
  FINAL READ only.
- **Stale component / pin mapping:** all five direct-include source hashes
  match the registered SHA-256 values. BVM pin order is `WL BL SE SL`; QB,
  sJTL, and CB are each `IN OUT`. The four generated chains use the same
  topology and fixed load.
- **Weak plot oracle:** a mocked raw fixture exercises the real classic
  `josim-plot2.py` page generator and raw/plot QA without invoking JoSIM.
- **Overclaim:** the platform reports arithmetic and QA only. There are no raw
  results from this build pass and no scientific interpretation.

## Remaining unverified items

- JoSIM has not parsed or solved these rendered decks in this task, by design.
- The 100 µA independent and 200 µA shared settings are candidate source
  amplitudes. Their loaded branch-current distributions and physical responses
  remain unmeasured until a user manually runs a chosen preset.
- Timestep sensitivity, model behavior under shared loads, and the array's
  functional read/write behavior are not established by static tests.

## Acceptance execution

- `python3 -m unittest discover -s tests -v`: 10/10 passed.
- `./try.sh --dry-run`: INDEPENDENT 10/10 passed; 12 cell-level sources,
  active R1C1, half-select R1C2/R2C1, unselected R2C2.
- `./try.sh --preset B_SHARED_10_10 --dry-run`: SHARED 10/10 passed; exactly
  six distinct line sources, one per row-WL/column-BL/column-SE line, same
  active/half-select/unselected mapping.
- `./try.sh --preset C_SHARED_11_11 --dry-run`: SHARED 11/11 passed; the four
  row/column intersections are listed active.
- All three previews reported `solver_invoked=false`, this-dry-run solve count
  0, static QA PASS, and left `runs/` absent.
- A separate mocked-runner test exercised artifact closure and the classic
  plot renderer on synthetic temporary data. It did not invoke JoSIM or create
  repository run evidence.
- Python compile, `bash -n try.sh`, and `git diff --check`: PASS.
- Physical solve count for this platform-build task: **0**.
