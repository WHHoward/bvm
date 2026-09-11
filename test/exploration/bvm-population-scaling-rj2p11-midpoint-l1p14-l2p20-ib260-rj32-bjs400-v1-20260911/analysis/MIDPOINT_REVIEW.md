# RJ2=11 midpoint raw-oriented review

Scientific interpretation: `NOT_PERFORMED`.

Recorded bounded outcome category: `BOUNDED_RESULT_REQUIRES_RAW_SCIENTIFIC_REVIEW`.

| mask | RJ2=11 response candidates | RJ2=12 reference candidates | RJ2=11 control | terminal segmentation |
|:---:|---:|---:|:---|:---|
| 0001 | 1 | 1 | CLEAN | ONE_RESPONSE_CLUSTER |
| 0011 | 2 | 2 | CLEAN | 2_SEPARATED_PULSES |
| 0111 | 0 | 0 | CLEAN | 4_SEPARATED_PULSES |
| 1111 | 0 | 0 | CLEAN | 4_SEPARATED_PULSES |

The 0011 case has dedicated second-response timing and the 0111 case has dedicated first/second/third/fourth and [121,130)ps post-READ records in `mechanical_summary.json`.

All phase values remain raw radians in the source CSV. Phase navigation, voltage clusters, current/voltage areas, L1 crossings, terminal pulse-local areas and response candidates are supporting evidence and are not SFQ counts. Raw waveform review remains authoritative over any mechanical category.
