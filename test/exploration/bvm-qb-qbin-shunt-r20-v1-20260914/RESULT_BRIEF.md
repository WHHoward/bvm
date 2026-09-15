# BVM -> QB receiver-boundary R20 shunt (bvm-qb-qbin-shunt-r20-v1-20260914)

- Status: EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW
- Artifact status after raw parsing: VALID
- Authorized/completed physical solves: 2/2 (0011, 0111).
- Scientific interpretation: NOT_PERFORMED; scientific questions remain SCIENTIFIC_REVIEW_REQUIRED.
- Intervention: exactly R_QBIN_SHUNT QBIN 0 20; no other circuit or protocol change.

## Registered numeric observations

These values are registered raw observations or mechanical arithmetic only;
they are not physical classifications.

| case | V(QBIN) peak abs, [113,117) ps (mV) | I(R_QBIN_SHUNT) peak abs, [113,117) ps (uA) | KCL max abs, [0,200) ps (A) |
|---|---:|---:|---:|
| 0011 | 0.5225798 | 26.12899 | 1e-11 |
| 0111 | 0.7395659 | 36.97829 | 9.2e-11 |

## Registered review questions

1. Does R20 reduce the N3 V(QBIN) high-voltage excursion? — SCIENTIFIC_REVIEW_REQUIRED
2. When does the registered shunt branch current become nonzero or large on the actual grid? — SCIENTIFIC_REVIEW_REQUIRED
3. Does the QBIN boundary KCL residual satisfy the registered arithmetic check? — SCIENTIFIC_REVIEW_REQUIRED
4. Are the first and second QB response windows retained in N2? — SCIENTIFIC_REVIEW_REQUIRED
5. Do N3 BVM JS1/JS2 traces move between the registered navigation windows? — SCIENTIFIC_REVIEW_REQUIRED
6. After the first BJ2 handoff window, what is the signed I(B_JSL8) trajectory? — SCIENTIFIC_REVIEW_REQUIRED
7. Are BVM JM1/JM2 storage traces unchanged in the registered tail comparison? — SCIENTIFIC_REVIEW_REQUIRED
8. Is active-cell position symmetry present on the registered tail window? — SCIENTIFIC_REVIEW_REQUIRED
9. What is the N2 final registered phase/current state? — SCIENTIFIC_REVIEW_REQUIRED
10. What is the N3 final registered phase/current state? — SCIENTIFIC_REVIEW_REQUIRED
11. Which scientific label applies: mechanism support, functional success, overdamping, no effect, or new pathology? — SCIENTIFIC_REVIEW_REQUIRED

## Evidence boundary

P(...) remains raw phase in radians. Displayed phase turns use
unwrap(rad)/(2*pi) only for navigation; they are not SFQ counts or
closed-loop fluxoid counts. KCL residuals are registered arithmetic and
do not certify switching, SFQ delivery, a Gate, or a mechanism.

Baseline and passive raw files are referenced by path and SHA-256 only;
no historical raw was copied or changed. No focused plots or unregistered
follow-up solves were generated.

Stop marker: EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW
