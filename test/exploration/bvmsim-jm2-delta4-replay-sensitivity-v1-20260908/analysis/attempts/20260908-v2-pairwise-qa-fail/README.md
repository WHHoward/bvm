# Preserved v2 visualization QA utility failure

The first v2 QA pass generated all 32 per-run pages and correctly passed
directory, window, complete-QB, full-JTL, source-kind and immutability
checks. It falsely reported pairwise tracks missing because the checker used
whole-list equality instead of substring matching for conditioned column
names. The failed QA and manifest remain here; the large duplicate derived
HTML/CSV archive was moved to a recoverable temporary directory outside the
repository. The corrected v2 package is under plots/delta4_v2 and is checked
again by independent_viz_v2_check.py.
