#!/usr/bin/env python3
"""Render the task-local exact-grid plot inputs with josim-plot2 only."""

from __future__ import annotations

import html
import json
import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
PLOTTER = REPO / "scripts/josim-plot2.py"
MANIFEST = EXP / "analysis/plot_manifest.json"


def normalize_html(path: Path) -> None:
    content = path.read_text(encoding="utf-8")
    normalized = "\n".join(line.rstrip() for line in content.splitlines()) + "\n"
    if normalized != content:
        path.write_text(normalized, encoding="utf-8")


def render(item: dict[str, object]) -> dict[str, object]:
    input_path = EXP / str(item["input"])
    output_path = EXP / str(item["output"])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not input_path.is_file():
        raise RuntimeError(f"missing derived plot input: {input_path}")
    command = [
        sys.executable,
        str(PLOTTER),
        str(input_path),
        "-t",
        "sep_comb",
        "-c",
        "dark",
        "-j",
        "2pi",
        "-x",
        str(output_path),
        "-w",
        str(item["title"]),
    ]
    completed = subprocess.run(command, cwd=REPO, capture_output=True, text=True, check=False)
    if completed.returncode != 0 or not output_path.is_file() or output_path.stat().st_size == 0:
        raise RuntimeError(
            f"plot failed for {item['name']}: exit={completed.returncode}\n"
            f"stdout={completed.stdout}\nstderr={completed.stderr}"
        )
    normalize_html(output_path)
    return {
        "name": item["name"],
        "input": str(input_path.relative_to(REPO)),
        "output": str(output_path.relative_to(REPO)),
        "exit_code": completed.returncode,
        "bytes": output_path.stat().st_size,
        "command": command,
    }


def write_overview(manifest: list[dict[str, object]], results: list[dict[str, object]]) -> None:
    result_by_name = {str(item["name"]): item for item in results}
    links = []
    for item in manifest:
        name = str(item["name"])
        output = Path(str(item["output"]))
        result = result_by_name[name]
        links.append(
            "<li><a href=\"{}\">{}</a> — {}–{} ps; {} bytes</li>".format(
                html.escape(output.name),
                html.escape(name),
                html.escape(str(item["bounds_ps"][0])),
                html.escape(str(item["bounds_ps"][1])),
                html.escape(str(result["bytes"])),
            )
        )
    content = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>OLD vs NEW 1111 history causal audit</title>
<style>
body {{ font-family: sans-serif; background: #111; color: #eee; max-width: 980px; margin: 2rem auto; padding: 0 1rem; }}
a {{ color: #7ec8ff; }} li {{ margin: .65rem 0; }} code {{ color: #ffd580; }}
.note {{ border-left: 4px solid #e99; padding: .7rem 1rem; background: #1d1d1d; }}
</style></head><body>
<h1>OLD-1111 vs NEW-1111 history-difference causal audit</h1>
<div class="note">All pages use exact stored timestamps, common probes only, <code>sep_comb + dark + -j 2pi</code>. P traces are displayed as continuous-unwrapped radians divided by <code>2π</code>; the figures are descriptive and do not count SFQ events.</div>
<p><a href="../analysis/OLD_VS_NEW_1111_HISTORY_CAUSAL_AUDIT.md">Read the Chinese audit report</a> · <a href="../analysis/history_audit_metrics.json">Metrics JSON</a> · <a href="../analysis/deck_diff_summary.json">Deck diff JSON</a></p>
<ol>
{}
</ol>
</body></html>
""".format("\n".join(links))
    (EXP / "plots/RESULT_OVERVIEW.html").write_text(content, encoding="utf-8")


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    results = [render(item) for item in manifest]
    write_overview(manifest, results)
    plot_results = {
        "renderer": "scripts/josim-plot2.py",
        "options": {"type": "sep_comb", "color": "dark", "jump": "2pi"},
        "simulation_invoked": False,
        "plots": results,
        "overview": "plots/RESULT_OVERVIEW.html",
    }
    (EXP / "analysis/plot_results.json").write_text(
        json.dumps(plot_results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    for item in results:
        print(f"{item['name']}: exit_code={item['exit_code']} bytes={item['bytes']}")
    print(f"overview={EXP / 'plots/RESULT_OVERVIEW.html'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
