# Preserved rendering QA failure

This is a preserved non-physics visualization QA attempt. The first version
of the renderer did not account for JSON slash escaping and reported false
missing-label and phase-axis failures. Its generated HTML and CSV files were
moved to a recoverable temporary archive outside the repository; the failed
viz_qa.json and visualization_manifest.json remain here. The corrected
visualization QA is at analysis/viz_qa.json.
