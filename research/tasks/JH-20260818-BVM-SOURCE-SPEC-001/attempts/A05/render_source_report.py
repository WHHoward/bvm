#!/usr/bin/env python3
"""render_source_report.py -- A05 deterministic report (C04 closure)."""
import json, pathlib, sys, yaml
ATTEMPT = pathlib.Path(__file__).resolve().parent

def main() -> int:
    spec = yaml.safe_load((ATTEMPT/"bvm-source-spec-v1.yaml").read_text())
    family = json.loads((ATTEMPT/"waveform-family.json").read_text())
    L = [f"# BVM_SOURCE_SPEC_V1 A05 (C04 closure)", "",
         f"- family: {len(family['waves'])} raw literal-token waves; "
         f"{len(family['corrected'])} corrected; {len(family['matched_pairs'])} matched pairs",
         f"- decimal context: {family['decimal_context']}",
         f"- windows (ps): {spec['windows_ps']}",
         "- descriptors: trapezoid time-normalized-L1, peak, rms per V*/I*; "
         "lobe statuses NOT_APPLICABLE",
         f"- netlists: {len(spec['source_netlist_sha256'])} source netlist SHA-256 bound",
         "- orientation: L_SL N8 -> SL", "",
         "## Claim ceiling", "",
         "- Hash-bound source-observation specification only; 1/12/25/50 ohm "
         "are load-origin labels, NOT source impedance or receiver/interface "
         "conclusions; accepted STABLE-LOAD-001 remains sole authority."]
    (ATTEMPT/"report.md").write_text("\n".join(L)+"\n")
    print("report.md written")
    return 0

if __name__ == "__main__":
    sys.exit(main())
