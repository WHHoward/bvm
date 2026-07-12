# ColdFlux RSFQ Standard Cell Library v3.0

**Source**: IARPA SuperTools/ColdFlux, Stellenbosch University  
**Process**: MIT-LL SFQ5ee  
**Model**: `jjmit` — `jj(rtype=1, vg=2.8m, cap=0.07p, r0=160, rn=16, icrit=0.1m)`  
**Bias**: 2.6mV DC bias line, resistors calculated per junction  
**Parasitic L**: 0.5pH per junction  

## Usage
```
.include circuits/models/jjmit.cir
.include circuits/standard/JTL.cir
X1 in out JTL
```

## Interconnects
| Cell | JJs | Ports | Description |
|------|-----|-------|-------------|
| JTL | 2 | a, q | Josephson Transmission Line |
| SPLIT | 3 | a, q0, q1 | SFQ pulse splitter |
| MERGE | 7 | a, b, q | SFQ pulse merger |
| PTLTX | 2 | a, q | PTL transmitter |
| PTLRX | 3 | a, q | PTL receiver |
| ALWAYS0_ASYNC | 2 | a, q | Always-0 (async) |
| ALWAYS0_ASYNC_NOA | 1 | q | Always-0 no ainput |
| ALWAYS0_SYNC | 3 | a, clk, q | Always-0 (sync) |
| ALWAYS0_SYNC_NOA | 2 | clk, q | Always-0 sync no ainput |

## Logic Gates
| Cell | JJs | Ports | Description |
|------|-----|-------|-------------|
| AND2 | 15 | a, b, clk, q | 2-input AND |
| OR2 | 12 | a, b, clk, q | 2-input OR |
| XOR | 11 | a, b, clk, q | 2-input XOR |
| NOT | 8 | a, clk, q | Inverter |
| XNOR | 19 | a, b, clk, q | 2-input XNOR |

## Buffers & Storage
| Cell | JJs | Ports | Description |
|------|-----|-------|-------------|
| DFF | 7 | a, clk, q | D Flip-Flop |
| NDRO | 11 | a, b, clk, q | Non-Destructive Read-Out |
| BUFF | 4 | a, q | Buffer |

## Interface
| Cell | JJs | Ports | Description |
|------|-----|-------|-------------|
| DCSFQ | 3 | a, q | DC-to-SFQ converter |
| SFQDC | 8 | a, q | SFQ-to-DC converter |

## PTL-Integrated (T-suffix)
| Cell | JJs | Ports | Description |
|------|-----|-------|-------------|
| JTLT | 3 | a, q | JTL with PTL |
| SPLITT | 4 | a, q0, q1 | Splitter with PTL |
| MERGET | 9 | a, b, q | Merger with PTL |
| AND2T | 17 | a, b, clk, q | AND2 with PTL |
| OR2T | 15 | a, b, clk, q | OR2 with PTL |
| XORT | 14 | a, b, clk, q | XOR with PTL |
| NOTT | 10 | a, clk, q | NOT with PTL |
| DFFT | 9 | a, clk, q | DFF with PTL |
| NDROT | 16 | a, b, clk, q | NDRO with PTL |
| BUFFT | 3 | a, q | Buffer with PTL |
| DCSFQ_PTLTX | 4 | a, q | DC/SFQ + PTL TX |
| PTLRX_SFQDC | 10 | a, q | PTL RX + SFQ/DC |
| ALWAYS0T_ASYNC | 0* | a, q | PTL term (async) |
| ALWAYS0T_ASYNC_NOA | 0* | a, q | PTL term no ainput |
| ALWAYS0T_SYNC | 0* | a, q | PTL term (sync) |
| ALWAYS0T_SYNC_NOA | 0* | a, q | PTL term sync no ainput |

*PTL termination cells use resistors/inductors only, no junctions.

## Design Parameters
- Base IC: 100μA (area=1.0)
- Standard JJ size: 1.6-2.5 area (160-250μA IC)
- Input JJ: 160μA, Output JJ: 250μA
- L_JTL = Φ₀/(4×IC) ≈ 2.07pH @ 250μA
- Bias: 70% of total junction IC
- PTL impedance: 5Ω
