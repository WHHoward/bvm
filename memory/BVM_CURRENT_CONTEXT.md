# Current BVM Experiment Context

This file records current engineering semantics only; it is not a scientific
history or approval to implement the next platform. Verify the live circuit and
experiment config before using these details.

## Role split

User + ChatGPT:

- experiment design;
- physical interpretation and scientific judgment;
- choosing the next experiment.

Codex/Luna:

- implement and render the user-directed change;
- run only authorized JoSIM cases;
- preserve evidence and perform mechanical QA;
- generate requested visualization;
- submit/package only when requested;
- stop for user review.

## Current component family

The current family is:

- `circuits/bvm/bvm_cell_0923.cir`
- `circuits/qb/BQ_0923.cir`
- `circuits/CB/CB_0923.cir`
- `circuits/sJTL_0923.cir`

Do not assume the older shared-QB / COMMON_SL architecture is the current
default topology.

## Planned topology abstraction (context only)

This describes a possible next-stage platform; it does not authorize generator,
deck, or experiment implementation here.

- `QB_CB[i]`: whether a CB immediately follows layer `QB_i`.
- `SJTL_COUNT[i]`: number of sJTL stages after that layer's merge.
- `POST_SJTL_CB[i]`: whether a CB follows the sJTL chain.

Conceptual path:

```text
BVM_i → QB_i → optional QB-side CB → MERGE_i
      → sJTL × K_i → optional post-sJTL CB → carry_i
```

`MERGE_i` may also receive the previous layer's carry. This is a design
abstraction only, not a claim that a generator or deck currently exists.

## Stimulus and mask semantics

`MASK` remains the FINAL READ mask. All BVMs still execute the normal pre-final
sequence:

```text
WRITE0 → CONTROL / READ0 → WRITE1 → FINAL READ
```

For a 2×1 mask, the leftmost bit is BVM1 and the rightmost bit is BVM2. Thus
`MASK=01` leaves BVM1 inactive only during final read and activates final read
for BVM2. A zero bit suppresses `WL`, `BL`, and `SE` only in the FINAL READ
window; it does not suppress the full-run write/control waveforms. A one bit
uses the active READ waveform. Do not rename this variable to `ACTIVE_MASK`.

Current platform v1 does not include repeated-read or rewrite-read stimulus.
