#!/usr/bin/env python3
"""Render the manifest with the repository's classic josim-plot2 renderer."""

from __future__ import annotations

import argparse
import html
import json
import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
PLOTTER = REPO / "scripts/josim-plot2.py"
MANIFEST = EXP / "analysis/plot_manifest.json"


def input_path(value: str) -> Path:
    path = Path(value)
    if path.parts and path.parts[0] == "analysis":
        return EXP / path
    return REPO / path


def output_path(value: str) -> Path:
    return EXP / Path(value)


def render(item: dict[str, object]) -> dict[str, object]:
    source = input_path(str(item["input"]))
    target = output_path(str(item["output"]))
    subset = [str(value) for value in item.get("subset", [])]
    if not source.is_file():
        raise RuntimeError(f"missing plot source: {source}")
    target.parent.mkdir(parents=True, exist_ok=True)
    command = [sys.executable, str(PLOTTER), str(source), "-t", "sep_comb", "-c", "dark", "-j", "2pi", "-x", str(target), "-w", str(item["title"])]
    if subset:
        command.extend(["-s", *subset])
    completed = subprocess.run(command, cwd=REPO, capture_output=True, text=True, check=False)
    if completed.returncode != 0 or not target.is_file() or target.stat().st_size == 0:
        raise RuntimeError(f"plot failed: {item['name']} exit={completed.returncode}\nstdout={completed.stdout}\nstderr={completed.stderr}")
    content = target.read_text(encoding="utf-8", errors="replace")
    if "<html" not in content.lower():
        raise RuntimeError(f"plot output is not HTML: {target}")
    if any(not label or label[0] not in "PVI" for label in subset):
        raise RuntimeError(f"plot subset contains untyped label: {item['name']}")
    return {"name": item["name"], "phase": item["phase"], "input": str(source.relative_to(REPO)), "output": str(target.relative_to(REPO)), "command": command, "exit_code": completed.returncode, "bytes": target.stat().st_size, "contains_phase_turn_label": "Phase (turns)" in content, "subset_labels_typed": all(label and label[0] in "PVI" for label in subset)}


def write_overview(results: list[dict[str, object]]) -> None:
    standalone = [item for item in results if item["phase"] == "standalone"]
    comparison = [item for item in results if item["phase"] == "comparison"]
    def links(items: list[dict[str, object]]) -> str:
        rows: list[str] = []
        for item in items:
            target = Path(str(item["output"]))
            href = (REPO / target).relative_to(EXP / "plots").as_posix()
            rows.append(f'<li><a href="{html.escape(href)}">{html.escape(str(item["name"]))}</a> — {int(item["bytes"])} bytes</li>')
        return "\n".join(rows)
    content = f"""<!doctype html>
<html lang=\"en\"><head><meta charset=\"utf-8\"><title>1111 HISTORY-READ crossover</title>
<style>body {{ font-family: sans-serif; background:#111; color:#eee; max-width:1100px; margin:2rem auto; padding:0 1rem; }} a {{ color:#7ec8ff; }} li {{ margin:.35rem 0; }} .note {{ border-left:4px solid #e99; background:#1d1d1d; padding:.7rem 1rem; }}</style></head>
<body><h1>1111 HISTORY-READ CROSSOVER CAUSAL A/B</h1>
<div class=\"note\">四条件统一比较：O+ OLD-WITH-HISTORY，O- OLD-NO-HISTORY，N- NEW-NO-HISTORY，N+ NEW-WITH-HISTORY。所有页面使用 <code>scripts/josim-plot2.py</code>、<code>sep_comb</code>、<code>dark</code>、<code>-j 2pi</code>；P 原始值是 rad，图中 turns 只表示 rad/(2π)，不是 SFQ count。</div>
<p><a href=\"../analysis/REPORT.md\">中文报告</a> · <a href=\"../analysis/crossover_metrics.json\">crossover metrics</a> · <a href=\"../analysis/metrics.json\">metrics</a></p>
<h2>Standalone QA</h2><ol>{links(standalone)}</ol>
<h2>Four-condition crossover</h2><ol>{links(comparison)}</ol>
</body></html>\n"""
    (EXP / "plots/RESULT_OVERVIEW.html").write_text(content, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=("standalone", "comparison", "all"), default="all")
    args = parser.parse_args()
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    selected = manifest if args.phase == "all" else [item for item in manifest if item["phase"] == args.phase]
    if args.phase == "comparison":
        standalone = [item for item in manifest if item["phase"] == "standalone"]
        missing = [item["name"] for item in standalone if not output_path(str(item["output"])).is_file()]
        if missing:
            raise RuntimeError(f"standalone visual QA incomplete; missing={missing[:5]}")
    results = [render(item) for item in selected]
    result_path = EXP / "analysis/plot_results.json"
    previous: list[dict[str, object]] = []
    if result_path.is_file():
        previous = json.loads(result_path.read_text(encoding="utf-8")).get("plots", [])
    by_name = {str(item["name"]): item for item in previous}
    by_name.update({str(item["name"]): item for item in results})
    ordered = [by_name[str(item["name"])] for item in manifest if str(item["name"]) in by_name]
    result_path.write_text(json.dumps({"schema": "bvmsim-1111-history-read-crossover-plot-results-v1", "renderer": "scripts/josim-plot2.py", "options": {"type": "sep_comb", "color": "dark", "jump": "2pi"}, "simulation_invoked": False, "plots": ordered, "overview": "plots/RESULT_OVERVIEW.html"}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.phase in ("comparison", "all"):
        all_results = ordered
        write_overview(all_results)
    for item in results:
        print(f"{item['name']}: exit={item['exit_code']} bytes={item['bytes']}")
    print(f"rendered={len(results)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
