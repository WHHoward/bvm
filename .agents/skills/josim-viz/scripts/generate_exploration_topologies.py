#!/usr/bin/env python3
"""Create one netlist-derived topology package for every Exploration directory.

The driver deliberately chooses a representative simulation deck and records
the variant boundary.  If an Exploration contains more than one structural
netlist, each distinct structure gets an additional diagram under
``topology/variants``.  Analysis-only directories may inherit a frozen parent
deck, but that fact is written into the README rather than hidden.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from generate_topology_svgs import (  # noqa: E402
    Mutual,
    Primitive,
    build_dot,
    flatten,
    parse_subckts,
    split_main,
)


# Analysis-only nodes have no independent circuit deck.  The source is an
# accepted, already-frozen fixture used by the analysis and is intentionally
# labelled as inherited in the generated README.
INHERITED = {
    "bvm-sfq-receiver-r14a-dcsfq-detector-20260823":
        "bvm-sfq-receiver-r12a-dcsfq-bvm-reaudit-20260823/inputs/phase-b-read1.cir",
    "jtl-transport-gate-v1-methodology-20260824":
        "jtl-transport-gate-polarity-replay-20260824/inputs/original/main.cir",
    "paper-sl-q3-pre-20260824":
        "paper-sl-q2-20260824/inputs/40u/paper-j1-logical1-read.cir",
    "q3-l1-routing-closure-20260824":
        "paper-sl-q3-l1-routing-closure-20260824/inputs/l1-4p5/paper-j1-logical1-read.cir",
    "qb-to-jtl-load-backaction-causal-audit-v1-20260824":
        "qb-load-boundary-matrix-20260824/inputs/C-q0-10ohm-parallel-jtl/scaled-iin-68p4u.cir",
}


PREFERRED = {
    "bvm-sfq-receiver-r2a-coupling-20260821":
        "inputs/diff-a010-b007-k080-read1.cir",
    "qb-load-boundary-matrix-20260824":
        "inputs/A-q0-open/scaled-iin-68p4u.cir",
}


def is_simulation_deck(path: Path) -> bool:
    try:
        text = path.read_text(encoding="utf-8", errors="replace").lower()
    except OSError:
        return False
    return ".tran" in text or ".print" in text


def candidate_score(path: Path) -> int:
    s = str(path).lower()
    name = path.name.lower()
    score = 0
    if "read1" in name or "logical1-read" in name:
        score += 100
    if "positive-control" in name or name == "positive-control.cir":
        score += 95
    if name == "main.cir":
        score += 80
    if "scaled-iin-68p4u" in name or "paper-j1" in name:
        score += 75
    if "read" in name:
        score += 15
    if "logical0" in name or "read0" in name:
        score -= 20
    if "control" in name:
        score -= 5
    if "reference/invalid" in s:
        score -= 500
    for utility in ("jjmit.cir", "bvm_cell.cir", "bq_cell.cir", "bq_cell_paper.cir",
                    "dcsfq_bvm.cir", "afq3.cir", "jtl.cir"):
        if name == utility:
            score -= 500
    # Prefer a deck directly under inputs over an archived/reference copy.
    score -= s.count("/reference/") * 20
    return score


def choose_deck(exploration: Path, repo_root: Path) -> tuple[Path | None, bool]:
    preferred = PREFERRED.get(exploration.name)
    if preferred:
        path = exploration / preferred
        if path.exists():
            return path, False
    inherited = INHERITED.get(exploration.name)
    if inherited:
        path = repo_root / "test/exploration" / inherited
        return (path if path.exists() else None), True
    candidates = [p for p in sorted(exploration.rglob("*.cir")) if is_simulation_deck(p)]
    if not candidates:
        return None, False
    return max(candidates, key=lambda p: (candidate_score(p), -len(str(p)))), False


def structural_signature(deck: Path) -> tuple[tuple, tuple] | None:
    try:
        main, subs = split_main(deck)
        primitives: list[Primitive] = []
        mutuals: list[Mutual] = []
        flatten(main, subs, {}, "", primitives, mutuals)
    except Exception as exc:  # pragma: no cover - kept as a per-deck guard
        print(f"WARN: cannot parse {deck}: {exc}", file=sys.stderr)
        return None
    if not primitives:
        return None
    p_sig = tuple(sorted((p.name, p.kind, p.a, p.b) for p in primitives))
    k_sig = tuple(sorted((k.name, k.left, k.right) for k in mutuals))
    return p_sig, k_sig


def slug(path: Path) -> str:
    value = re.sub(r"[^A-Za-z0-9]+", "-", path.stem).strip("-").lower()
    return value or "variant"


def rel_repo(path: Path, repo_root: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return str(path)


def includes_and_subckts(deck: Path) -> tuple[list[str], list[str]]:
    includes = []
    for raw in deck.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if line.lower().startswith(".include "):
            includes.append(line)
    try:
        subckts = sorted(x.name for x in parse_subckts(deck).values())
    except Exception:
        subckts = []
    return includes, subckts


def render(deck: Path, output_dir: Path, title: str, display_source: Path | None = None) -> dict:
    main, subs = split_main(deck)
    primitives: list[Primitive] = []
    mutuals: list[Mutual] = []
    flatten(main, subs, {}, "", primitives, mutuals)
    if not primitives:
        raise RuntimeError(f"no primitive elements found in {deck}")
    output_dir.mkdir(parents=True, exist_ok=True)
    dot = build_dot(primitives, mutuals, display_source or deck, title)
    (output_dir / "topology.dot").write_text(dot, encoding="utf-8")
    subprocess.run(
        ["dot", "-Tsvg", str(output_dir / "topology.dot"), "-o", str(output_dir / "topology.svg")],
        check=True,
    )
    return {"deck": str(deck), "primitives": len(primitives), "mutuals": len(mutuals)}


def write_readme(exploration: Path, repo_root: Path, chosen: Path, inherited: bool,
                 variants: list[dict], canonical: dict) -> None:
    includes, subckts = includes_and_subckts(chosen)
    variant_lines = []
    for item in variants:
        variant_lines.append(
            f"- `{item['label']}`：[`topology.svg`](variants/{item['slug']}/topology.svg)，"
            f"source `{item['source']}`；{item['primitives']} primitives / {item['mutuals']} mutuals。"
        )
    if not variant_lines:
        variant_lines = ["- 本目录没有检测到结构不同的额外 netlist；参数/输入波形变体共用主图。"]
    inherit_note = (
        "这是 analysis-only 目录；目录本身没有独立 simulation deck。主图继承已接受的"
        " frozen fixture，仅用于说明分析所消费的拓扑。"
        if inherited else
        "主图来自本 Exploration 内的代表性 simulation deck。"
    )
    lines = [
        f"# {exploration.name} topology",
        "",
        "这是从实际 JoSIM netlist 展平并由 Graphviz 生成的结构图，不是 scientific verdict。",
        inherit_note,
        "",
        "## 主图来源",
        "",
        f"- source deck：`{rel_repo(chosen, repo_root)}`",
        f"- topology.svg：{canonical['primitives']} primitives，{canonical['mutuals']} mutuals。",
        "- 各输入 case 如果只改变 PWL、bias 数值或其他参数而未改变元件/连接结构，则共用此图。",
        "",
        "## include / subcircuit provenance",
        "",
    ]
    lines.extend(f"- `{x}`" for x in includes or ["（source deck 未写 .include；请以 source deck 为准）"])
    lines.append("")
    lines.extend(f"- subcircuit：`{x}`" for x in subckts or ["（未解析到本地 subcircuit）"])
    lines += [
        "",
        "## 结构变体",
        "",
        *variant_lines,
        "",
        "## 绘图边界",
        "",
        "- 矩形为 netlist 中的 primitive，椭圆为展平后的精确 net，菱形为 mutual coupling。",
        "- `.tran`、`.print`、PWL 时间点和分析脚本不是电路元件，因此不画成元件；其余已解析 primitive 与 K mutual 均保留。",
        "- 图中分组只用于阅读：BVM/source、receiver/interface、QB/regenerator、standard JTL 和 top-level bias。",
        "- 附件中的 BVM/BQ 图片仅用于配色/版式参考；本图的节点和元件必须回到 source deck 核对。",
    ]
    (exploration / "topology" / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", type=Path, default=Path("."))
    ap.add_argument("--root", type=Path, default=Path("test/exploration"))
    args = ap.parse_args()
    repo_root = args.repo_root.resolve()
    root = (repo_root / args.root).resolve()
    results = []
    for exploration in sorted(p for p in root.iterdir() if p.is_dir()):
        chosen, inherited = choose_deck(exploration, repo_root)
        if chosen is None:
            topology = exploration / "topology"
            topology.mkdir(parents=True, exist_ok=True)
            (topology / "README.md").write_text(
                f"# {exploration.name} topology\n\n"
                "本目录是 analysis-only / documentation-only 节点，没有独立 netlist，"
                "因此没有伪造结构图。请从流程索引进入相邻 accepted fixture 的 topology。\n",
                encoding="utf-8",
            )
            results.append({"exploration": exploration.name, "status": "no-independent-deck"})
            continue

        # Group all runnable decks by connectivity/component structure.  Values,
        # PWLs and operating points are intentionally ignored for this grouping.
        grouped: dict[tuple, list[Path]] = {}
        all_candidates = [p for p in sorted(exploration.rglob("*.cir")) if is_simulation_deck(p)]
        for deck in all_candidates:
            sig = structural_signature(deck)
            if sig is not None:
                grouped.setdefault(sig, []).append(deck)
        chosen_sig = structural_signature(chosen)
        if chosen_sig is None:
            raise RuntimeError(f"selected deck cannot be parsed: {chosen}")
        ordered_groups = sorted(grouped.items(), key=lambda kv: min(str(x) for x in kv[1]))
        topology = exploration / "topology"
        topology.mkdir(parents=True, exist_ok=True)
        canonical = render(
            chosen,
            topology,
            f"{exploration.name} — representative topology",
            Path(rel_repo(chosen, repo_root)),
        )
        variants = []
        used_slugs: set[str] = set()
        for sig, decks in ordered_groups:
            if sig == chosen_sig:
                continue
            source = max(decks, key=lambda p: (candidate_score(p), -len(str(p))))
            base = slug(source)
            variant_slug = base
            n = 2
            while variant_slug in used_slugs:
                variant_slug = f"{base}-{n}"
                n += 1
            used_slugs.add(variant_slug)
            info = render(
                source,
                topology / "variants" / variant_slug,
                f"{exploration.name} — structural variant {variant_slug}",
                Path(rel_repo(source, repo_root)),
            )
            variants.append({
                "slug": variant_slug,
                "label": variant_slug,
                "source": rel_repo(source, repo_root),
                "primitives": info["primitives"],
                "mutuals": info["mutuals"],
            })
        write_readme(exploration, repo_root, chosen, inherited, variants, canonical)
        manifest = {
            "exploration": exploration.name,
            "source_deck": rel_repo(chosen, repo_root),
            "inherited": inherited,
            "canonical": canonical,
            "variants": variants,
        }
        (topology / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        results.append({"exploration": exploration.name, "status": "ok", "variants": len(variants)})
        print(f"{exploration.name}: {len(variants)} structural variants; {rel_repo(chosen, repo_root)}")
    print(json.dumps({"count": len(results), "results": results}, indent=2))


if __name__ == "__main__":
    main()
