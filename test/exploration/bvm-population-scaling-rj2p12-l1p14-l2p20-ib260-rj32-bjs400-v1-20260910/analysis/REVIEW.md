# Independent population numerical/adversarial review

Review status: `PASS`.

The reviewer read raw CSV files directly and independently recomputed cumulative phase landmarks, adaptive stored-sample voltage clusters, terminal valley segmentation and ordered QBOUT→JTL1→...→JTL6 progression. It did not import the primary population analyzer or oracle.

- Cases checked: 7; new physical solver invocations checked: 5; exact reuse cases: 2.
- Post-hoc selected-mask comparison: `SELECTED_MASK_EXPECTED_SCALING_NOT_OBSERVED`.
- Adversarial probes: `{'mask_semantics_b3b2b1b0': True, 'generalized_detector_no_hamming_weight_input': True, '0001_single_not_false_two_response': True, '0011_two_response_not_false_single': True, 'three_input_masks_classified': True, 'four_input_mask_classified': True, 'terminal_clusters_and_jtl_order_checked': True}`.
- Hamming weight is inspected only after the detector produces response classifications.
- Phase landmarks, voltage areas, terminal pulse areas and response candidates are not SFQ counts.
