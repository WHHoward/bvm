# Topology precheck

## M1: ideal waveform replay

The accepted Q0 `V(OUT)` samples are converted to one ideal source:

```spice
V_REPLAY JTL_IN 0 pwl(<accepted Q0 V(OUT,t)> )
XJTL1 JTL_IN JTL_MID THmitll_JTL
XJTL2 JTL_MID JTL_OUT THmitll_JTL
R_TERM JTL_OUT 0 1
```

This is a counterfactual waveform-compatibility fixture, not a physical
QB-to-JTL port. It contains no QB and therefore no QB back-action path.

## M2: retained Q0 load plus finite series isolation

```text
Q0 OUT ── R_ISO=10 Ω ── JTL input a
  │                         │
 R_LOAD=10 Ω              standard JTL bias/network
  │                         │
 GND                       JTL output ─ R_TERM=1 Ω ─ GND
```

`R_ISO` has finite DC and transient impedance. The original Q0 `R_LOAD` is
kept, so this tests an isolated coupling branch without silently changing the
accepted Q0 retrap boundary.

## M3: series topology control

```text
Q0 OUT ── R_SER=10 Ω ── JTL input a
```

The original `R_LOAD` is removed exactly as preregistered. This is not an
isolated version of the accepted Q0 boundary; it is a causal control for
series-vs-shunt output topology.

## M4: retained Q0 load plus series inductance

```text
Q0 OUT ── L_ISO=10 pH ── JTL input a
  │                         │
 R_LOAD=10 Ω              standard JTL bias/network
```

The inductor is a superconducting DC path, while its finite edge reactance
changes the transient boundary. It is not a transformer and no mutual element
is added.

## M5: coherent scaled JTL

M5 uses a separately emitted two-cell subcircuit with the same port topology
as `THmitll_JTL`, but one coherent scale `s=0.216`:

- JJ area `2.50*s=0.54` for both JTL junctions;
- bias fraction `0.7` unchanged;
- all cell inductances multiplied by `1/s`;
- resistance-like damping and termination multiplied by `1/s`;
- input positive-control source topology unchanged.

The Q0 coupling fixture retains the original 10 Ω Q0 load and attaches the
scaled cell chain directly to `OUT`. This keeps the Q0 local-event boundary
fixed while testing only the JTL current class.

All JTL output paths terminate at a declared resistor. No floating output,
undefined DC return, transformer common-mode path, or hidden JTL parameter
change is introduced.
