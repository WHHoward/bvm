#!/usr/bin/env python3
"""render_source_report.py -- A03 deterministic report."""
import json, pathlib, sys, yaml
ATTEMPT = pathlib.Path(__file__).resolve().parent

def main() -> int:
    spec = yaml.safe_load((ATTEMPT/"bvm-source-spec-v1.yaml").read_text())
    family = json.loads((ATTEMPT/"waveform-family.json").read_text())
    L = [f"# BVM_SOURCE_SPEC_V1 A03 (C02 rework, FINAL)", "",
         f"- family: {len(family['waves'])} raw + {len(family['corrected'])} corrected waves",
         f"- windows (ps): {spec['windows_ps']}",
         f"- descriptors: trapezoid time-normalized-L1, peak, rms per V*/I*",
         f"- lobe status: FWHM and dominant opposite lobe NOT_APPLICABLE (no legal bracket/lobe)",
         f"- netlists: 16 source netlist SHA-256 bound",
         f"- timestamp: {spec['timestamp']}", "",
         "## Claim ceiling", "",
         "- Hash-bound source-observation specification only; no affine "
         "source model; accepted STABLE-LOAD-001 remains sole authority."]
    (ATTEMPT/"report.md").write_text("\n".join(L)+"\n")
    print("report.md written")
    return 0

if __name__ == "__main__":
    sys.exit(main())
