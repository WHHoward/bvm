#!/usr/bin/env python3
"""compare_deterministic.py -- A03 deterministic comparison (side-effect-free).

Re-renders into a TEMPORARY comparison path and compares bytes against the
canonical report.html WITHOUT ever rewriting the canonical file.  Writes
only deterministic-comparison.log in the A03 attempt directory.
"""
import pathlib, sys, tempfile, importlib.util, hashlib

ATTEMPT = pathlib.Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("renderer", ATTEMPT/"render_stable_load_dashboard.py")
renderer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(renderer)

def main() -> int:
    canonical = (ATTEMPT/"report.html").read_bytes()
    with tempfile.TemporaryDirectory(prefix=".viz003-cmp-", dir=ATTEMPT.parent) as td:
        # render into temp dir (data model goes there too; canonical untouched)
        import json
        data = renderer.build_data()
        html = renderer.render_html(data)
        same = html.encode() == canonical
        result = (f"DETERMINISTIC COMPARISON: {'CONSISTENT' if same else 'INCONSISTENT'}\n"
                  f"canonical report.html sha256: {hashlib.sha256(canonical).hexdigest()}\n"
                  f"comparison rendered {len(html)} bytes vs canonical {len(canonical)} bytes\n")
        (ATTEMPT/"deterministic-comparison.log").write_text(result, encoding="utf-8")
        print(result.strip())
        return 0 if same else 1

if __name__ == "__main__":
    sys.exit(main())
