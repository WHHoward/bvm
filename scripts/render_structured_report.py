#!/usr/bin/env python3
"""render_structured_report -- deterministic report renderer.

Renders a markdown report from a structured analysis JSON.  Deterministic:
same structured input -> byte-identical output.  Every number in the report
comes from the structured JSON (values are rendered as their literal decimal
tokens); NO template may carry manually duplicated authority numbers.

Usage:
  python3 render_structured_report.py structured.json report.md [--check]
--check mode re-renders and compares against the existing report file
(report-consistency verification); exit 1 on any headline mismatch.
"""
from __future__ import annotations

import json
import pathlib
import sys


def render(structured: dict) -> str:
    L = []
    A = L.append
    meta = structured.get('metadata', {})
    A(f'# {meta.get("title", "structured analysis report")}')
    A('')
    A(f'- run_id: {meta.get("run_id", "?")}')
    A(f'- spec_id: {meta.get("spec_id", "?")}')
    A(f'- generated deterministically by render_structured_report.py')
    A('')
    metrics = structured.get('metrics', {})
    if metrics:
        A('## Metrics')
        A('')
        A('| id | value |')
        A('|---|---|')
        for k in sorted(metrics):
            v = metrics[k]
            A(f'| {k} | {v:.9e} |')
        A('')
    windows = structured.get('windows', {})
    if windows:
        A('## Windows (ps, half-open)')
        A('')
        for k in sorted(windows):
            A(f'- {k}: {windows[k][0]} .. {windows[k][1]}')
        A('')
    notes = structured.get('notes', [])
    for n in notes:
        A(f'- {n}')
    return '\n'.join(L) + '\n'


def main() -> None:
    if len(sys.argv) not in (3, 4):
        print('usage: render_structured_report.py structured.json report.md '
              '[--check]')
        sys.exit(2)
    struct_path = pathlib.Path(sys.argv[1])
    report_path = pathlib.Path(sys.argv[2])
    check = len(sys.argv) == 4 and sys.argv[3] == '--check'
    structured = json.load(open(struct_path, encoding='utf-8'))
    text = render(structured)
    if check:
        existing = report_path.read_text(encoding='utf-8')
        if existing != text:
            print(f'REPORT-CONSISTENCY FAIL: {report_path} differs from '
                  f'deterministic render')
            sys.exit(1)
        print(f'REPORT-CONSISTENCY PASS: {report_path} == deterministic render')
    else:
        report_path.write_text(text, encoding='utf-8')
        print(f'rendered {report_path} ({len(text)} bytes)')


if __name__ == '__main__':
    main()
