#!/usr/bin/env python3
"""render_source_report.py -- BVM_SOURCE_SPEC_V1 report (A01, deterministic)."""
import json, pathlib, sys
ATTEMPT = pathlib.Path(__file__).resolve().parent

def main() -> int:
    spec = __import__("yaml").safe_load((ATTEMPT/"bvm-source-spec-v1.yaml").read_text())
    family = json.loads((ATTEMPT/"waveform-family.json").read_text())
    L = [f"# BVM_SOURCE_SPEC_V1 — accepted BVM terminal waveform family",
         "", f"- run: {spec['run_id']}",
         f"- family size: {len(family['waves'])} (4 loads x 2 polarities x read/control)",
         f"- preconditions: {spec['accepted_preconditions']['readiness']}; "
         f"{spec['accepted_preconditions']['source_disposition']}; "
         f"{spec['accepted_preconditions']['endpoint_vi']}",
         f"- windows (ps): {spec['windows_ps']}",
         f"- timestamp: {spec['timestamp']}",
         "", "## Sources",
         "", "| case | load (ohm) | polarity | type | samples | csv sha256 |",
         "|---|---|---|---|---|---|"]
    for s in spec["sources"]:
        L.append(f"| {s['case']} | {s['load_ohm']} | {s['polarity']} | "
                 f"{s['case_type']} | {s['samples']} | {s['csv_sha256'][:12]}... |")
    L += ["", "## Claim ceiling",
          "", "- Hash-bound source-observation specification only; accepted "
          "STABLE-LOAD-001 remains the sole scientific authority.",
          "- No Thevenin/Norton/affine source model, BQ/receiver/cascade/"
          "interface/SFQ/fluxoid/mechanism/hardware claim."]
    (ATTEMPT/"report.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("report.md written")
    return 0

if __name__ == "__main__":
    sys.exit(main())
