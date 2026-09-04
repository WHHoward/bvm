#!/usr/bin/env python3
"""Mechanical QA for the compact JoSIM HTML visualization set."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]


def main() -> int:
    manifest_path = EXP / "plots/plot_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    failures: list[str] = []
    standalone_count = 0
    comparison_count = 0
    phase_page_count = 0
    axis_unknown_count = 0

    for mask, pages in manifest.get("standalone", {}).items():
        for name, record in pages.items():
            standalone_count += 1
            path = EXP / record["html"]
            if not path.is_file() or path.stat().st_size == 0:
                failures.append(f"missing standalone page: {record['html']}")
            else:
                text = path.read_text(encoding="utf-8", errors="replace")
                if '"title":{"text":"Unknown"}' in text:
                    axis_unknown_count += 1
                    failures.append(f"Unknown axis title: {record['html']}")
                if any(label.startswith("P(") for label in record.get("labels", [])):
                    phase_page_count += 1
                    if "Phase (turns) [rad\\u002f2pi]" not in text:
                        failures.append(f"phase unit label missing: {record['html']}")

    for name, record in manifest.get("comparison", {}).items():
        comparison_count += 1
        path = EXP / record["html"]
        data = EXP / record["data"]
        if not path.is_file() or path.stat().st_size == 0:
            failures.append(f"missing comparison page: {record['html']}")
        if not data.is_file() or data.stat().st_size == 0:
            failures.append(f"missing comparison data: {record['data']}")
        if path.is_file():
            text = path.read_text(encoding="utf-8", errors="replace")
            if '"title":{"text":"Unknown"}' in text:
                axis_unknown_count += 1
                failures.append(f"Unknown axis title: {record['html']}")
            if any(label.startswith("P(") for label in record.get("labels", [])):
                phase_page_count += 1
                if "Phase (turns) [rad\\u002f2pi]" not in text:
                    failures.append(f"phase unit label missing: {record['html']}")

    expected_standalone = 90
    expected_comparison = 15
    if standalone_count != expected_standalone:
        failures.append(f"standalone count {standalone_count} != {expected_standalone}")
    if comparison_count != expected_comparison:
        failures.append(f"comparison count {comparison_count} != {expected_comparison}")

    output = {
        "schema": "bvmsim-common-sl-12jsl-qb-viz-qa-v1",
        "created_at_local": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "renderer": manifest.get("renderer"),
        "renderer_options": manifest.get("renderer_options"),
        "standalone_pages": standalone_count,
        "comparison_pages": comparison_count,
        "phase_pages_checked": phase_page_count,
        "axis_unknown_pages": axis_unknown_count,
        "status": "PASS" if not failures else "FAIL",
        "failures": failures,
    }
    target = EXP / "analysis/viz_qa.json"
    if target.exists():
        raise RuntimeError(f"refusing to overwrite visualization QA: {target}")
    target.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": output["status"], "standalone": standalone_count, "comparison": comparison_count, "phase_pages": phase_page_count, "unknown_axes": axis_unknown_count}, ensure_ascii=False))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
