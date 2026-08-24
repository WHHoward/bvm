# BVM_READ_SEMANTICS_AUDIT_AND_JSL_WIDTH_BRACKET_V1

## Parent and scope

- parent HEAD: `576ca9d32b15c99f8c35c4271336ffa079664b64`
- tier: lightweight Exploration
- solver: `build/josim-cli` `v2.7.2837d13`
- canonical BVM: unchanged; no QB/JTL/T1 parameter changes
- timestep: `0.0125 ps`; stop time: `170 ps`

This Exploration first corrects the repository-wide READ terminology and source
lineage.  It then tests only the registered local JSL plateau bracket after the
corrected canonical logical0 source is established.  Existing raw data are
never overwritten.

## Frozen READ protocol

The four formal roles are:

1. `logical1_read`: positive WL+BL initialization plus canonical POS-READ;
2. `logical0_read`: negative WL+BL initialization plus exactly the same
   canonical POS-READ;
3. `logical1_no_read_control`;
4. `logical0_no_read_control`.

Canonical POS-READ is WL=`+100 uA` and SE=`+100 uA`, with identical onset,
plateau, rise and fall for both stored states.  The registered JSL topology is
the external series `B_LD1...B_LD12`, each `jjmit AREA=3.2`, from `SL1` to
ground.  The frozen scaled QB is the accepted Q0/Q1 scaled cell with
`BJs/BJL1/BJL2 AREA=.50/.36/.54`, `IBIAS=35 uA`, `Lin/L0/L1/L2=.80/1.323/3.91/3.91 pH`,
`RJ1/RJ2=33/22 ohm`, `RB=6 ohm`, and `R_LOAD=10 ohm`.

## Gate order

1. Audit all declared READ fixtures and source lineage.
2. Reuse the already accepted canonical 12 ps logical1 JSL raw.
3. Run a new 12 ps **canonical logical0** JSL deck (`negative init + WL+SE`).
4. Replay the actual `I(B_LD1)(t)` into the frozen QB.  If corrected logical0
   remains zero and controls remain zero, continue with 13/14/15 ps.
5. At each width, record physical canonical logical1/logical0 JSL source and
   replay both unchanged into the frozen QB.  No rectification, hold,
   rescaling, interpolation, or polarity change is allowed.
6. Stop at the first width with read1 exactly-one, canonical logical0 zero,
   and both no-read controls zero.  If 15 ps remains subthreshold, stop with
   `WIDTH_MARGIN_GAIN_BUT_NO_CLOSURE`.

The no-read controls are reused only from the byte-identical external-12-JSL
topology and same initialization/timestep/stop protocol; their provenance is
recorded in `reference/control-provenance.yaml`.

## Event evidence

An exactly-one QB event requires the same BJL2 continuous monotonic segment to
reach at least one turn, direct same-segment `integral(V dt)/Phi0` agreement,
bounded post behavior/retrap, and no second complete event.  Total phase range,
current above Ic, and voltage peak alone are not event evidence.  Phase plots
use `continuous_absolute`: raw JoSIM `P(t)/(2*pi)` continuous phase in turns,
not an SFQ counter.

## Stop rules

- corrected 12 ps logical0 complete event or nonselective control: stop;
- any width control complete event, free-running or multifire: stop;
- solver/artifact invalidity: stop the affected gate;
- no automatic physical `BVM -> JSL12 -> QB` connection;
- no extra width, amplitude, bias, AREA, timestep or waveform sweep.
