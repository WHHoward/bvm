#!/usr/bin/env python3
"""verify_maintenance_evidence -- recursive seal of the 001 package (AC4).

Recursively hashes every 001 deliverable (docs/schemas/tools/tests/logs)
with original paths; records 001 as HISTORICAL_PROTOCOL_SCOPE_DEFECT;
revalidates the written inventory.  Read-only on all 001 files.
"""
from __future__ import annotations

import hashlib
import pathlib
import sys

REPO = pathlib.Path('/home/howard/JoSIM')
OUT = pathlib.Path(__file__).parent / 'evidence-inventory.yaml'

FILES = [
    'research/schemas/quantitative-analysis-spec.schema.json',
    'scripts/quantitative_analysis_verifier.py',
    'scripts/render_structured_report.py',
    'scripts/build_evidence_bundle.py',
    'test/workflow/test_quantitative_analysis_verifier.py',
    'test/workflow/test_evidence_bundle.py',
    '.agents/skills/josim-handoff/scripts/handoff.py',
    '.agents/skills/josim-handoff/scripts/test_handoff.py',
    'research/WORKFLOW.md',
    'research/CLAUDE_EXECUTOR.md',
]
PROTO = [
    'research/tasks/JH-20260817-WORKFLOW-MAINT-001/request.yaml',
    'research/tasks/JH-20260817-WORKFLOW-MAINT-001/attempts/A01/ack.yaml',
    'research/tasks/JH-20260817-WORKFLOW-MAINT-001/attempts/A01/receipt.yaml',
]


def sha(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> None:
    missing = [f for f in FILES + PROTO if not (REPO / f).is_file()]
    if missing:
        print('MISSING:', *missing, sep='\n  ')
        sys.exit(1)
    lines = [
        '# WORKFLOW-MAINT-001 package seal (002/A01; AC4)',
        '# 001 recorded as HISTORICAL_PROTOCOL_SCOPE_DEFECT (superseded by',
        '#  002 for the scope.hash_paths repair); no 001 file modified.',
        'entries:',
    ]
    for f in sorted(FILES):
        p = REPO / f
        lines.append(f'  - {{path: {f}, sha256: "{sha(p)}", bytes: '
                     f'{p.stat().st_size}, tag: IMPLEMENTATION_PACKAGE}}')
    for f in PROTO:
        p = REPO / f
        lines.append(f'  - {{path: {f}, sha256: "{sha(p)}", bytes: '
                     f'{p.stat().st_size}, '
                     f'tag: HISTORICAL_PROTOCOL_SCOPE_DEFECT}}')
    OUT.write_text('\n'.join(lines) + '\n', encoding='utf-8')

    import yaml
    back = yaml.safe_load(OUT.read_text())
    fails = []
    for it in back['entries']:
        p = REPO / it['path']
        if sha(p) != it['sha256'] or p.stat().st_size != it['bytes']:
            fails.append(it['path'])
    if fails:
        print('POST-WRITE FAIL:', *fails, sep='\n  ')
        sys.exit(1)
    hist = sum(1 for i in back['entries']
               if i['tag'] == 'HISTORICAL_PROTOCOL_SCOPE_DEFECT')
    print(f'SEAL OK: {len(back["entries"])} entries '
          f'({hist} HISTORICAL_PROTOCOL_SCOPE_DEFECT); post-write OK')


if __name__ == '__main__':
    main()
