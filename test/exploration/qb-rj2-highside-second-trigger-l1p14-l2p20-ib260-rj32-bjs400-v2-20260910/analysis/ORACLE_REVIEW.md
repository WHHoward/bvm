# Second-response oracle review

ORACLE_REVIEW_COMPLETE

Review status: `PASS`. No solver was invoked and no raw file was modified.

## Repair

The former checker restarted cumulative phase history at the strongest later positive `I(L1)` segment. That can begin after the second response has already advanced through BJ1/BJ2/JTL. The repaired checker keeps the common FINAL-origin baseline `[101,110) ps` for all cumulative landmarks and independently checks direct voltage clusters.

Voltage clusters use stored samples, an adaptive baseline-MAD/peak threshold, a 2.5 ps peak-gap rule, and a below-threshold valley requirement. Terminal pulse-local areas use the shared stored valley boundary; a waveform that does not meet that rule is left ambiguous rather than force-split.

## Case result

| RJ2 | mask | first response | repaired second response | second phase order | voltage clusters | terminal |
|---:|:---:|:---|:---|:---|:---|:---|
| 10.0 | 0001 | BOUNDED_RESULT | NO_SECOND_COMPLETE_MULTI_EVIDENCE_CANDIDATE | False | False | ONE_RESPONSE_CLUSTER |
| 10.0 | 0011 | BOUNDED_RESULT | NO_SECOND_COMPLETE_MULTI_EVIDENCE_CANDIDATE | False | False | ONE_RESPONSE_CLUSTER |
| 12.0 | 0001 | BOUNDED_RESULT | NO_SECOND_COMPLETE_MULTI_EVIDENCE_CANDIDATE | False | False | ONE_RESPONSE_CLUSTER |
| 12.0 | 0011 | BOUNDED_RESULT | BOUNDED_RESULT | True | True | TWO_SEPARATED_PULSES |
| 14.0 | 0001 | BOUNDED_RESULT | NO_SECOND_COMPLETE_MULTI_EVIDENCE_CANDIDATE | False | False | ONE_RESPONSE_CLUSTER |
| 14.0 | 0011 | BOUNDED_RESULT | BOUNDED_RESULT | True | True | TWO_SEPARATED_PULSES |
| 16.0 | 0001 | BOUNDED_RESULT | NO_SECOND_COMPLETE_MULTI_EVIDENCE_CANDIDATE | False | False | ONE_RESPONSE_CLUSTER |
| 16.0 | 0011 | BOUNDED_RESULT | BOUNDED_RESULT | True | True | TWO_SEPARATED_PULSES |

Repaired second-response cases: `ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_0011, ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P14_0011, ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P16_0011`.
Legacy strongest-L1 reference exposed as false-negative for: `ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_0011, ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P14_0011, ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P16_0011`.

## Adversarial tests

- Known single-response `0001`: `True`; it remains one terminal response and is not classified as a second response.
- Known two-response `RJ2=12 / 0011`: `True`; all phase/voltage/terminal checks are explicitly recorded.
- Legacy false-negative exposure: `True`.

All phase thresholds and voltage-area values remain mechanical/derived evidence. They are not SFQ counts, and no hardware or universal mechanism claim is made.
