# CARRY5: 11×13 Two-Read / All-SFQ Clock (Design Review Draft)

**Status: NOT SIMULATED.** These are complete netlist and stimulus drafts, not a verified working circuit.

## Location / dependencies

Extract this directory into the repository at:
`test/exploration/bvm-4x4-diagonal-array-v1-20261009/sfq_clock_two_read_11x13_v1/`

The deck includes canonical repository components using `../../../../circuits/...`, local `library_josim/{dcsfq2,jtl2}.cir`, `sources/t1_cell_tunable.cir`, `sources/d0_jtl_tunable.cir`, and the **repository's canonical** `../../../../circuits/standard/DFF.cir` (source matches A107's DFF snapshot SHA). No independent `cbu_tunable` is required: the actual CARRY5 deck uses canonical `CB_0928` in the carry branches, not a `THmitll_MERGE` instance.

Both local clock library files were compared against `BVMSim/library_josim` on GitHub; the `dcsfq2` cell has **two** ports (`a q`), the `jtl2.cir` cell is named **`jtl`** internally. The original uploaded `dcsfq.cir` with three ports (`IN OUT VBIAS`) is NOT used.

## Unchanged from CARRY5

- 16 BVM / QB crosspoints and common WL/BL, cell-local SE.
- Physical D0 JTL, six Carry branches with stage sJTL counts `1,1,5,1,1,1`, CB-before-JOIN.
- D3 array internal sJTL counts `1,2,2,1`.
- T1 values are **taken exactly from the user's modified `t1_cell_tunable.cir`**. Unlike A107, this places 3-ohm shunts across J1 and J2 in **all** seven T1 cells. This is a separate physical change from the clock format.
- DFF core remains the canonical `THmitll_DFF` (only its clock drive changes).

## Clock generation, eight independent copies

Each of D0–D6 and DFF has its own one-shot/two-shot upstream PWL generator, 2-ohm trigger resistor, DCSFQ2 and JTL2:
`V_TRIG → R_TRIG(2Ω) → XDCSFQ[dcsfq2] → XJTL[jtl] → CLK_{stage}`.

Source rising edges: 210 and 410 ps, 1-ps rise, 2-ps hold, 1-ps fall, peak 1.2 mV.
User reports 10–15 ps additional delay from local experiments. **Predicted** SFQ arrival is approximately 220–225 and 420–425 ps, but this is not guaranteed and may differ per stage or DFF load. Since A107's original PWL started at 210 ps, this first pilot intentionally does NOT pre-compensate the DCSFQ/JTL delay.

## BVM stimulus

| Stage | Time (ps) | Drive |
|---|---|---|
| Write0 (preserved) | 50–61 | WL/BL = -400 µA; SE 0 |
| READ0 setup (preserved, prior to WRITE1) | 70–81 | WL +400 µA, all SE +100 µA, BL 0 |
| Write1 (preserved) | 90–101 | WL/BL +400 µA; SE 0 |
| Post-WRITE1 read #1 | 110–121 | WL +400 µA only R1/R2/R4; SE +100 µA only nine selected crosspoints; BL 0 |
| Post-WRITE1 read #2 | 310–321 | Identical to read #1, without an intervening write |
| PWL clock triggers | 210–214, 410–414 | eight separate DCSFQ2→JTL2→T1/DFF chains |
| Simulation window | 0–550 | DT=0.01 ps, STOP=550 ps |

Thus these are two **post-write1** reads. The earlier READ0 from the established baseline is preserved so that initialization is comparable; it is not one of the two measured readouts.

## Mandatory scientific analysis before claim of success

- Confirm 2 separate SFQ clock events per D0..D6 and DFF at the **CLK pins**, not just at PWL input; use full pulse-integrated voltage (Φ0) and local JJ phases.
- Confirm the nine selected BVM crosspoints generate two sets of read responses; compare BVM internal phases/states before/between/after reads to check nondestructive readout.
- Confirm the data stream has settled before each clock edge, including D3/D4/D5 Carry.
- Decode each read **in separate windows** (e.g. [200,300) and [400,500) ps after checking actual timing) for Sum S0..S6 and DFF.O. Expect 143 (`10001111` in MSB-first notation) **in each window**, not 286 from an aggregate two-read integral.
- Check DFF behavior across both captures; the output may be stateful and per-window voltage response must be examined.
- Compare against a new-clock single-read trial using the same T1 shunts. If failure occurs, separate the SFQ clock effect from the J1/J2 3Ω changes with controlled ablations.
- Mechanical probe existence/static correctness alone never equals a functional PASS.

## Preflight / use

- Read the clock circuit models and check whether `.model jj0` and `.model jmitll` are accepted locally and repeated subckt instances are well scoped.
- Ensure the main JoSIM runner supports an experimental standalone deck (the existing registered `try.sh` does not support this new clock scheme as-is). Do not run the stock `try.sh` with modified `deck.cir` expecting it to persist.
- When staging for JoSIM, run from the deck directory or otherwise resolve `.include` paths. A static/preprocessor sanity check should precede a *user-approved* one-solve pilot.
- Baseline A107 and every earlier run are immutable.

## Structural/static validation done by file builder

- 16 BVM + 16 QB, 7 T1 + 1 DFF, all eight DCSFQ2→JTL2 paths, exact CARRY5 chain.
- No JoSIM solve, no simulation correctness claim.
