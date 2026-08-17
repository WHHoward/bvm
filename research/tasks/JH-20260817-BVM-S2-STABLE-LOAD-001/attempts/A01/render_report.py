#!/usr/bin/env python3
"""render_report.py -- deterministic report.md + report.html (A01)."""
import json, pathlib, sys
ATTEMPT = pathlib.Path(__file__).resolve().parent

def render_md(a):
    L = [f"# {a['run_id']} — stable-initialization BVM load characterization",
         "", f"- disposition: {a['disposition']}",
         "- frozen spec: bvm-s2-stable-load-preregistration-v1 "
         f"(task JH-20260817-BVM-S2-STABLE-LOAD-001); attempt {a['attempt']}",
         f"- provenance: {a['provenance']['binary']} ({a['provenance']['version']}), "
         f"dt={a['provenance']['timestep_ps']} ps, tstop={a['provenance']['tstop_ps']} ps",
         "", "## Strata readiness (JM1/JM2 PRE [80,90) p2p <= 0.020 rad)",
         "", "| stratum | load (ohm) | polarity | ready |", "|---|---|---|---|"]
    for s in a["strata"]:
        L.append(f"| {s['id']} | {s['load_ohm']} | {s['polarity']} | {s['ready']} |")
    L += ["", "## Endpoint-VI (exact Decimal tokens 97-105 ps)",
          "", "| polarity | eligible | compatible | not_supported | ill_conditioned |",
          "|---|---|---|---|---|"]
    for pol, e in a["endpoint_vi"].items():
        s = e["summaries"]
        L.append(f"| {pol} | {s['eligible']} | {s['compatible']} | "
                 f"{s['not_supported']} | {s['ill_conditioned']} |")
    L += ["", "## Claim ceiling",
          "", "- Bounded fixed-closure fixed-grid per-load terminal observations "
          "and matched-control-corrected endpoint-VI compatibility at registered "
          "exact tokens only.",
          "- No numerical convergence, mechanism, logical-state, preservation, "
          "load-back-action, receiver, BQ, SFQ, fluxoid, interface, route, "
          "hardware, or universal-impedance claim."]
    return "\n".join(L) + "\n"

def render_html(a):
    rows = "".join(f"<tr><td>{s['id']}</td><td>{s['load_ohm']}</td>"
                   f"<td>{s['polarity']}</td><td>{s['ready']}</td></tr>"
                   for s in a["strata"])
    ev = "".join(f"<tr><td>{p}</td><td>{e['summaries']['eligible']}</td>"
                 f"<td>{e['summaries']['compatible']}</td>"
                 f"<td>{e['summaries']['not_supported']}</td>"
                 f"<td>{e['summaries']['ill_conditioned']}</td></tr>"
                 for p, e in a["endpoint_vi"].items())
    return f"""<!doctype html><html><head><meta charset="utf-8">
<title>{a['run_id']}</title></head><body>
<h1>{a['run_id']} — stable-initialization BVM load characterization</h1>
<p>disposition: <b>{a['disposition']}</b> (descriptive, non-authoritative)</p>
<h2>Strata readiness</h2><table border="1"><tr><th>stratum</th><th>load</th>
<th>polarity</th><th>ready</th></tr>{rows}</table>
<h2>Endpoint-VI summary</h2><table border="1"><tr><th>polarity</th>
<th>eligible</th><th>compatible</th><th>not_supported</th>
<th>ill_conditioned</th></tr>{ev}</table>
</body></html>"""

def main():
    a = json.loads((ATTEMPT/"analysis.json").read_text())
    md = render_md(a)
    (ATTEMPT/"report.md").write_text(md)
    (ATTEMPT/"report.html").write_text(render_html(a))
    if "--check" in sys.argv:
        ok = (ATTEMPT/"report.md").read_text() == md
        print("REPORT CONSISTENT" if ok else "REPORT INCONSISTENT")
        return 0 if ok else 1
    print(f"rendered report.md ({len(md)} bytes) + report.html")
    return 0

if __name__ == "__main__":
    sys.exit(main())
