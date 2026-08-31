# PAPER-SL-L0 — canonical BVM with 12×320 µA JSL load

## Status

This is a bounded Exploration.  It does not modify the canonical BVM, QB
circuits, or any previously committed raw evidence.  No QB, JTL, or T1 is
connected in this round.

Parent repository HEAD at registration: `5ea93b13add28b78d6366282ad54a632c4c92eb1`.

## Question

Does the paper-motivated twelve-junction sense-line load remain non-switching
under the canonical single-BVM read cases, while preserving the canonical
logical read distinction and storage guards?

The experiment is a load characterization only.  It does not claim that a
local JSL junction phase excursion is an SFQ event or that the load delivers
an SFQ pulse.

## Source and topology review

The local paper copy is
`arti/Karamuftuoglu_2025_Supercond._Sci._Technol._38_015020.pdf`.
Figure 4 describes the read simulation as having a sense-line load of twelve
non-switching junctions with 320 µA critical current each.  Section 2.5 also
states that a stack of non-switching JJs is an alternative replacement for the
sense-line `L_SL`, and that the junction inductance must be included in the
readout dynamics.

Two interpretations were considered:

1. **Internal replacement (not run here):** remove the canonical internal
   `L_SL` and replace it with the twelve-JJ stack.  This is the Section 2.5
   redesign interpretation, but it changes the internal canonical BVM output
   topology and removes the requested direct `I(L_SL)` loaded probe.
2. **External series load (selected):** keep the canonical BVM exactly as
   frozen, connect the twelve-JJ stack to the BVM `SL` port, and terminate the
   far end at ground.  This matches the Figure 4 “load on the sense line”
   characterization and the repository's historical 8-JJ external-stack
   fixture.  The stack's nonlinear junction inductance is still in series with
   the canonical `R_SL/L_SL` output path.

The selected netlist is therefore:

```text
canonical BVM SL1
    -> B_LD1 -> B_LD2 -> ... -> B_LD12 -> ground
```

`L_PSL`, `R_SL`, and `L_SL` remain inside the canonical `BVM` subcircuit.
There is no QB or extra far-end resistor.  The last stack node is ground by
construction; the penultimate node and the last-JJ branch are probed to make
the far-end convention explicit.

The historical fixture used eight `AREA=3.2` JJs from the BVM port to ground.
It is provenance for the external-load connection only; its eight-junction
result is not reused as the paper's twelve-junction condition.

## Frozen model and expected scale

The run includes the repository `jjmit.cir` model at the parent HEAD.  Under
that actual model, `AREA=3.2` gives:

- `Ic = 320 µA`;
- `C = 224 fF`;
- `RN = 5 Ω`;
- `R0 = 50 Ω`.

The zero-current Josephson inductance is approximately
`Phi0/(2*pi*320 µA) = 1.03 pH` per junction, or about `12.4 pH` for twelve
junctions before the current-dependent `1/cos(phi)` correction.  This is an
analytic scale estimate only; the raw phase/current/voltage trajectories are
the evidence for non-switching and load behavior.

## Matched cases

All cases use the same source PWL knots, model, `.tran 0.0125p 170p`, and
probes.  Only the stored logical initialization and the READ=0 versus READ
stimulus differ:

1. `logical1-read`
2. `logical0-read`
3. `logical1-read0-control`
4. `logical0-read0-control`

## Required measurements

For each of `B_LD1` through `B_LD12`, save direct `P`, `V`, and `I`.  Also
save:

- `I(L_SL|XBVM1)` and the BVM-side `V(SL1)`;
- the stack-side terminal `V(njsl11)` immediately before `B_LD12`;
- `V(N6|XBVM1)`;
- `P/V` for `B_JM1`, `B_JM2`, `B_JS1`, and `B_JS2`;
- `I(L_PSL|XBVM1)`, source currents, and the far-end branch current.

The analysis window is `[94,130) ps` for the read activity and `[140,170) ps`
for post behavior.  Startup and the `[80,90) ps` pre-read interval are kept
separately so bias/startup motion is not mislabeled as a read event.

## Evidence rules and verdicts

Every JSL switching claim must use the same JJ's continuous unwrapped phase,
the largest monotonic segment, and the direct same-JJ voltage integral over
that same segment.  A phase range, voltage peak, current peak, or an old
`fast_events` count alone is not an event criterion.  A JSL is considered
non-switching for this Exploration when no JSL has a complete one-turn
monotonic segment and the post window remains bounded.

The result is classified as one of:

- `PAPER_JSL_LOAD_VALID`: all twelve JSLs remain non-switching, the four-case
  read/control distinction remains recognizable, and storage/source guard
  comparison shows no clear semantic collapse;
- `JSL_SWITCHING_FAILURE`: at least one JSL has a complete phase/area-consistent
  transition or unbounded/free-running behavior;
- `SOURCE_SEMANTICS_CHANGED`: the stack causes a clear loss of the canonical
  logical read distinction or a clear storage-guard failure, even if the JSLs
  remain below one turn;
- `INCONCLUSIVE`: artifact or guard evidence is insufficient.

No result is upgraded to a universal statement about all JSL loads or all
receiver interfaces.

