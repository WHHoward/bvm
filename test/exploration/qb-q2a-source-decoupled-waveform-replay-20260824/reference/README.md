# QB-Q2A source provenance

The replay source snapshots are generated from committed raw CSV files; the selected voltage columns are copied without shape, polarity, normalization or resampling changes.

- `B-q1-loaded-vsl.csv`: `QB-Q1/raw/logical1-read.csv`, `V(SL1)`; loaded direct-galvanic waveform.
- `B-q1-loaded-ilin.csv`: same QB-Q1 raw, `I(Lin|XBQ)`; diagnostic current companion, not the replay variable.
- `C-canonical-logical1-vsl.csv`: QB-Q1 copied canonical no-receiver reference, `V(SL1)`.
- `C-canonical-logical1-isls.csv`: same reference, `I(L_SL|XBVM1)`; diagnostic source current companion.
- `C0-canonical-logical0-vsl.csv`: QB-Q1 copied canonical no-receiver reference, `V(SL1)`.
- `C0-canonical-logical0-isls.csv`: same reference, `I(L_SL|XBVM1)`; diagnostic source current companion.

The B/C/C0 replay is an ideal voltage-source counterfactual. It is not evidence that a physical zero-impedance source or conditioner exists.
