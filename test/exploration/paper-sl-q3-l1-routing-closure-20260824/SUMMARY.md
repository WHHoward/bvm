# PAPER-SL-Q3 summary

## Verdict

`ROUTING_GAIN_WITH_BJL1_SUBTHRESHOLD`

## Observed

- The single physics-informed point was `L1=4.50 pH`; all four source decks
  were copied byte-identically from accepted PAPER-SL-Q2 40-uA input decks.
- All four runs exited normally. The first READ=0 control was bounded, so the
  remaining matched cases were executed.
- Read1 `F_local` changed from `0.218660` to `0.224945`; the complementary
  signed L1 fraction changed from `0.781340` to `0.775055`.
- Read1 control-subtracted `G_local` changed from `0.515185` to `0.526585`.
- The largest read1 BJL1 segment changed from `0.815414` to `0.821070 turn`,
  with same-segment voltage areas `0.815445` and `0.821102 Phi0`; it remained
  below a complete turn. BJL2 likewise remained sub-turn.
- Logical0 and both READ=0 controls had zero complete BJL1/BJL2 events and no
  free-running signature under the registered event test.

## Derived / inference

The point gives a small, state-selective routing increase in this frozen
replay fixture, but no threshold-like nonlinear jump and no local quantized
event. This supports a bounded routing conclusion only; it does not validate a
physical BVM-to-QB interface or downstream SFQ delivery.

## Unknown

This replay fixture has no physical BVM SL/N6/JM/JS probes, so source/back-action
guards are not established by this checkpoint. No L1 sweep, junction-ratio
tuning, physical BVM connection, or JTL test was performed.

## Next / stop

Close the single-point passive L1 routing test. Do not append an L1 sweep from
this result; retain the evidence for the next explicitly authorized internal
QB route decision.
