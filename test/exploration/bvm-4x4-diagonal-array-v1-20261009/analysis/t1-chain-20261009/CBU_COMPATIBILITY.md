# T1 chain candidate-cell compatibility record

Status is limited to static source inspection, default-body equivalence checks,
and JoSIM netlist sanity. It does not establish physical logic behavior.

## CBU candidate

Selected candidate: `circuits/standard/MERGE.cir`, subcircuit
`THmitll_MERGE a b q`, SHA-256
`2fdc5c24798c619eee97dee07d1dcb02b2e49e3b96bfa868f86ec978dca6f96e`.
It contains seven JJ devices B1..B7, four internal PWL bias sources IB1..IB4,
input branches from `a` and `b`, and output `q`. The shared model in this
platform is `circuits/models/jjmit.cir`, SHA-256
`19862d1fd1f1f44dfa1523848d7d3b5e2594a6c5da8fdd80144b449e5312a336`; the
candidate comments name the same jjmit family and the run deck includes that
model before the cell definitions.

The canonical candidate has an illegal Unicode right single quotation mark on
its active `.param BiasCoef=0.7’` line (source line 29). The experiment-local
rendered copy changes only that token to ASCII `0.7`; it does not edit the
canonical source. Defaults for active JJ areas, bias current values, active
signal inductors, and shunt inductors are rendered from `config/CBU_PARAMS.env`.
The candidate's declared `.param L1..L8` values do not match the numeric values
in the actual L1..L8 device statements and are not referenced by those device
statements. To preserve the default active circuit, the local renderer exposes
the values from the active element lines; it does not substitute the unused
parameter declarations. The local copy's default active body is equivalent to
the candidate after only the registered quote correction.

The six actual ports are distinct: `CBU_A_Dk` is driven from `DOUT_Dk`,
`CBU_B_Dk` from `C_D(k-1)`, and `CBU_OUT_Dk` feeds `T1_I_Dk` through a zero-volt
measurement link. These links are branch-current sensors; they do not replace
the physical CBU or T1.

This is distinct from `circuits/CB/CB_0928.cir`, SHA-256
`70a6af05acccb7c354799d5b1b7542c86c677970681473f559bbf0f7e4d6d370`, whose
port list is `.subckt CB IN OUT` and which remains the single-input array CB.
The CB is preserved in every diagonal array level and is never aliased as a
two-input CBU.

## D0 entrance JTL

The selected D0 stage is one experiment-local copy of canonical
`circuits/sJTL_0923.cir`, SHA-256
`3cbc6889f9b4cd6b7764efa4a591f9d4dcdb0b2b86ded1f265dadabda1040688`. Its
default active values are JJ area 2.5, bias 190u, L1=L2=2.5p, and RJ1=4 Ω.
The local renderer renames only the subcircuit to `D0_JTL`, applies those
separately configurable values, and omits the duplicate `.model jjmit` line so
the deck reuses the shared model. Default active values match the source.
Array `SJTL_COUNT_D0..D6` values are unchanged; this is an additional D0-only
entrance stage.

## DFF candidate and loads

Selected candidate: `circuits/standard/DFF.cir`, subcircuit
`THmitll_DFF a clk q`, SHA-256
`e63473b890b67bd968ee9891518e7b4f9b52560cb49e20fa18fa50f03b6bc6f0`. It has
seven JJs and four internal PWL bias sources. Its run-local tunable copy has
the default body unchanged; values are exposed via `config/DFF_PARAMS.env`.
C6 is connected to `a`; the independent DFF clock branch connects to `clk`;
`q` is `DFF_O`. The initial external DFF.O measurement load is 12 Ω, matching
the T1 Sum load reference. This is a registered candidate load, not a validated
optimum. DFF clock capture and loaded output remain physical unknowns until the
authorized raw runs are reviewed.

## Static compatibility limits

The registered static gate checks source topology, pin order, unique top-level
names, all 7 T1/6 CBU/one-or-configured-count D0 JTL/one DFF instances, C0-C5
carry routing, C6-to-DFF routing, eight independent clock branches, required
probe targets, source hashes, and JoSIM `-s` sanity. It does not verify CBU
collision behavior, T1 arithmetic, DFF capture, or a multiplier truth table.
