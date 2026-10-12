# Clock and stimulus quick reference

Both clock edges are **PWL trigger times**, NOT measured SFQ arrival times.

| Event | 1st read | 2nd read |
|---|---|---|
| WL + SE reading pulse begins rising | 110 ps | 310 ps |
| WL + SE reading pulse ends falling | 121 ps | 321 ps |
| PWL → DCSFQ2 rising edge | 210 ps | 410 ps |
| PWL high | 211–213 ps | 411–413 ps |
| PWL low again | 214 ps | 414 ps |
| Approx. SFQ CLK at T1/DFF if +10–15 ps | 220–225 ps | 420–425 ps |
| Recommended exploratory output comparison windows | 200–300 ps | 400–500 ps |

**200 ps spacing = 5 GHz repetition for two probes**, not 20 GHz.

Why not compensate clock delay from 210 to 197 ps immediately?
The supplied 10–15 ps measurement was made in another setup; stage loading and new T1 shunts can shift it. Initial pilot favors direct observation. If actual clock arrival is too late/early, run a separate clock-timing sweep **after** this pilot, don't hide timing changes in the baseline.

Pulse calibration per stage: check volt-seconds of `V(CLK_Dk)` relative to Φ0 only when port definition permits meaningful integration; additionally check internal `P(B03|XDCSFQ_Dk)` and `P(B02|XJTL_IN_Dk)`. Observe T1's `P(B_J2|XT1_Dk)` and Sum/Carry. Analog port waveform area can be load-dependent; it is not itself proof of JJ switching.
