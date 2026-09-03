#!/usr/bin/env python3
"""Write the compact, evidence-labelled operational baseline report."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
METRICS = EXP / "analysis/metrics.json"
VIZ = EXP / "analysis/visualization_manifest.json"
ANCHOR = EXP / "analysis/historical_anchor_check.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fmt(value: object, digits: int = 3) -> str:
    if value is None:
        return "—"
    if isinstance(value, bool):
        return "是" if value else "否"
    if isinstance(value, (float, int)):
        return f"{float(value):.{digits}f}"
    return str(value)


def link(path: str) -> str:
    return f"[`{path}`](../{path})" if path.startswith("plots/") else f"`{path}`"


def main() -> int:
    results = json.loads(METRICS.read_text(encoding="utf-8"))["results"]
    viz = json.loads(VIZ.read_text(encoding="utf-8"))
    anchor = json.loads(ANCHOR.read_text(encoding="utf-8"))
    four = results["four"]
    single = results["single"]
    by_state = {item["state"]: item for item in four}
    lines: list[str] = []
    add = lines.append
    add("# Historical BVMSim operational baseline V1 — execution report")
    add("")
    add(f"> 生成时间：{datetime.now(timezone.utc).astimezone().isoformat(timespec='seconds')}。本报告只解释本实验目录中的 historical BVMSim raw。")
    add("")
    add("## 1. Scope and fixed source")
    add("")
    add("- source class：`HISTORICAL_BVMSIM`；BVM=`BVMSim/bvm_cell.cir`，QB=`BVMSim/BQ.cir`，JTL=`BVMSim/library_josim/jtl2.cir`。")
    add("- nominal：`RJ1=12 Ω`、`RJ2=4 Ω`、QB bias=`250 µA`、JTL bias=`280 µA`、terminal=`10 Ω`、`.tran 0.1p 200p 45p`。")
    add("- historical BVM 不等于 canonical BVM：本目录没有使用 `circuits/bvm/bvm_cell.cir`；已知 `R_JM1` 为 `8 Ω` vs canonical `6 Ω`。")
    add("- 16-state 的预期为 `popcount(state)`；state 字序 `b3b2b1b0` 映射 `BVM1..BVM4`。")
    add("- single-BVM original-BQ deck 的日志保留了 `Missing model: JJMIT`/`Using default model` warning；4-BVM historical fixture 的顶层 model 可见、未出现该 warning。本轮未用 shared model 偷换 historical QB，因此结果不应描述为 shared-jjmit QB。")
    add("- 因此四个 single-BVM 记录的 intended-model closure 判为 `ARTIFACT_INVALID`，不把其 raw-derived 0/1 结果当作物理 PASS/FAIL；它们只保留作 historical 2×2 诊断。")
    add("")
    add("## 2. Historical raw anchor check")
    add("")
    add(f"`BVMSim/data_tran.csv` 的 duplicate-safe 读取保留了重复列 `V(O2)`×{anchor['historical_raw']['duplicate_columns'].get('V(O2)', 0)}；与 `F4_1111` 在 {anchor['grid']['historical_samples']} 个共同时间点上逐点比较，time grid exact={anchor['grid']['exact']}，不插值。")
    add("")
    add("| signal | max abs difference | RMS difference |")
    add("|---|---:|---:|")
    for label, value in anchor["signals"].items():
        add(f"| {label} | {value['max_abs_difference']:.3e} | {value['rms_difference']:.3e} |")
    add("")
    add("这只是确认 print 扩展/状态 `1111` 没有改变这些共同电气轨迹，不是物理正确性或收敛证明。详见 `analysis/historical_anchor_check.json`。")
    add("")
    add("## 3. Evidence inventory")
    add("")
    add(f"- nominal runs：{len(single)} 个 single-BVM + {len(four)} 个 4-BVM state = {len(single)+len(four)} 个。")
    add(f"- individual visualizations：{len(viz['individual'])} 个；汇总图：{len(viz['comparisons'])} 个。")
    add("- 所有 individual 图均在 comparison 图之前生成并完成 raw-hash QA；图是描述性证据，不替代事件分析。")
    add("- raw 使用 requested `0.1 ps`；选定 raw 的存储网格 mostly 为 `0.1 ps`，但每个 run 都有一次 `62.8→63.0 ps` 的 `0.2 ps` 间隔，因此不是严格 uniform grid。分析直接使用实际时间列，不插值。")
    add("")
    add("## 4. Single-BVM 2×2 baseline")
    add("")
    add("| run | load | expected | QB burst | QB strict complete/clean | final burst | final strict complete/clean | artifact status |")
    add("|---|---|---:|---:|---:|---:|---:|---|")
    for item in single:
        qb = item["qb"]["READ"]
        final = qb if item["jtl"] is None else item["jtl"]["JTL6"]
        add(
            f"| {item['run_id']} | {item['load']} | {item['expected_count']} | "
            f"{qb['count']} | {item['strict_status']['BJ2_READ_complete_segments']}/"
            f"{item['strict_status']['BJ2_READ_clean_separated_events']} | {final['count']} | "
            f"{final.get('strict_local', {}).get('complete_segment_count', '—')}/"
            f"{final.get('strict_local', {}).get('clean_separated_event_count', '—')} | {item['functional_verdict']} |"
        )
    add("")
    add("观察：两个 logical-1 single-BVM run 的 raw-derived QB/JTL6 burst 为 0，两个 logical-0 control 也为 0；但四个记录均出现历史 original-BQ 的 model-scope warning，故 intended-model closure 为 `ARTIFACT_INVALID`，不据此作 single-BVM 物理结论。")
    add("")
    add("## 5. 4-BVM 16-state baseline")
    add("")
    add("`QB burst` 与 `JTL6 burst` 是同一 READ1 窗口内、同一 JJ 的 phase/voltage-area 一致性得到的 burst-total 量化结果；它们不是仅凭 phase 位移计数。strict 列是独立的 segment/event 结构，且本轮具体阈值属于 post-hoc exploratory diagnostic，详见 `analysis/POST_HOC_DIAGNOSTIC.md`。")
    add("`popcount` 是 commanded state word 的预期，不等于 BVM1–BVM4 的内部状态已经逐颗由 raw 闭合确认；当前 print 对 BVM2–BVM4 的内部 JJ 证据不完整。因此这里判定的是 historical fixture 的端到端 commanded-state mapping，不把 mismatch 唯一归因于 QB。")
    add("")
    add("| state | expected | QB burst | JTL6 burst | QB strict complete/clean | JTL6 strict complete/clean | QB max segment (turns) | QB continuous running | verdict |")
    add("|---|---:|---:|---:|---:|---:|---:|---|---|")
    for item in four:
        q = item["qb"]["READ1"]
        j = item["jtl"]["JTL6"]["B02"]
        add(
            f"| {item['state']} | {item['expected_count']} | {q['count']} | {j['count']} | "
            f"{q['strict_local']['complete_segment_count']}/{q['strict_local']['clean_separated_event_count']} | "
            f"{j['strict_local']['complete_segment_count']}/{j['strict_local']['clean_separated_event_count']} | "
            f"{fmt(q['strict_local']['largest_segment_turns'])} | {fmt(q['strict_local']['continuous_multi_turn_running'])} | "
            f"{item['functional_verdict']} |"
        )
    add("")
    add("关键观察（Observed）：")
    add("- `0000`：QB/JTL6 均为 0，READ0/尾部控制也没有 complete event。")
    add("- `0100`：QB burst 为 1，但 QB strict 段未达到完整 1-turn 门槛；JTL6 出现 1 个 clean separated event。这说明 QB 局部结构与下游可见结构不能混为一谈。")
    add("- `1111`：QB burst=`3.9995`、area/Φ0=`3.9995`，但 QB 是一个约 4-turn continuous running segment；JTL6 最终可分辨 4 个 clean separated events。")
    add("- `0001`、`0010`、`0011`、`0101`、`0110`、`0111`、`1000`、`1001`、`1010`、`1011`、`1100`、`1101`、`1110` 的 QB/JTL6 burst 均高于预期，故 16-state mapping 未通过 hard count gate。")
    add("")
    add("## 6. Strict transport detail for representative state 1111")
    add("")
    item = by_state["1111"]
    add("下表使用 READ1 内相对首个存储样本的 first upward integer phase-displacement crossing 作为时序 marker；它不是 SFQ event count，也不是把 crossing 强行等同于 clean event。")
    add("")
    add("| location | burst total | strict complete | clean separated | polarity | first upward crossings (ps) | first-crossing delta (ps) |")
    add("|---|---:|---:|---:|---:|---|---:|")
    transport_rows = [("QB BJ2", item["qb"]["READ1"])]
    transport_rows.extend((f"{stage} B02", value["B02"]) for stage, value in item["jtl"].items())
    previous_first = None
    for location, b in transport_rows:
        strict = b["strict_local"]
        crossings = b.get("phase_crossing_markers", {}).get("crossing_times_ps", [])
        crossing_text = ", ".join(fmt(v, 2) for v in crossings) or "—"
        first = float(crossings[0]) if crossings else None
        delta = first - previous_first if first is not None and previous_first is not None else None
        add(f"| {location} | {b['count']} | {strict['complete_segment_count']} | {strict['clean_separated_event_count']} | {b.get('polarity') or '—'} | {crossing_text} | {fmt(delta, 2)} |")
        if first is not None:
            previous_first = first
    add("")
    add("Observed：QB BJ2 的四个 upward crossings 约为 118.31、121.68、125.48、133.73 ps；JTL1→JTL6 的首个 crossing 依次向后，末级约为 134.54 ps。它支持该 historical loaded fixture 中存在 forward burst propagation 的有限描述。")
    add("Inference：JTL 后段可能把上游连续 burst dynamics 重塑为更清楚的局部 transitions；这不是已证实的机制。旧表中的 `clean onset` 是 local segment onset，尤其 JTL6 的早期 onset 不能当作因果传输延迟，因此不再用它作 stage latency。")
    add("1111 的 QB `BJ2` 仍是一个约 3.985-turn continuous running segment，不是四个 QB clean events；JTL6 的四个 clean labels 只描述最终输出侧的局部结构，不能反写为 QB 已产生四个独立 SFQ。")
    add("")
    add("## 7. Selectivity and KCL")
    add("")
    add("五个 4-BVM 非 READ1 窗口 `PRE/WRITE0/READ0/WRITE1/TAIL` 的 QB BJ2 与 JTL6 strict complete event 均为 0；因此本轮没有在这些窗口的已存储 raw 中观察到 complete spontaneous/extra event。这个结论不覆盖 4-BVM 未存储的 `0–45 ps` 启动段，也不构成每个状态都匹配的 no-READ selectivity Gate。")
    max_kcl: dict[str, float] = {}
    for item in four:
        for node, value in item["kcl_READ1"].items():
            max_kcl[node] = max(max_kcl.get(node, 0.0), float(value["metrics"]["max_abs_uA"]))
    add("")
    add("QB READ1 KCL residual max over all 16 states（单位 µA）：")
    add("")
    for node, value in max_kcl.items():
        add(f"- `{node}`：{value:.9f} µA")
    add("")
    add("KCL 方程采用 branch current 从 netlist 第一节点流向第二节点：")
    add("- node2：`-I(BJs)+I(BJ1)+I(RJ1)+I(L1)=0`；")
    add("- bias node3：`-I(L1)-I(IB)+I(L2)=0`；")
    add("- node4：`-I(L2)+I(BJ2)+I(RJ2)+I(L3)=0`。")
    add("")
    add("## 8. Decision and margin status")
    add("")
    add("### Derived decision")
    add("")
    add("`BASELINE_FUNCTIONAL_FAIL`：nominal 16-state 没有支持预注册的 `0→0, 1→1, 2→2, 3→3, 4→4` 功能映射；更精确的 evidence descriptor 是 `HISTORICAL_FIXTURE_COUNT_MISMATCH`。按允许的探索性分类保留 `SELECTIVITY_OR_OVERDRIVE_FAILURE`，quick label 为 `QUICK_OPPOSITE`，但这里的 overdrive 只描述 count mismatch/continuous running 观察，不是已经证明的器件机理。")
    add("注意：`0.25 turns` burst display tolerance、strict complete/clean/retrap thresholds 都是运行后诊断参数，不是 preflight 中已冻结的 acceptance threshold；因此具体 strict 数字不应被提升为 Formal Gate。")
    add("")
    add("### Margin axes")
    add("")
    add("本轮不执行 `IB`、`RJ1` 或 physical-input `alpha` 的任何裕度扫描，也不执行 pairwise map。原因是 setup 中已冻结的 stop rule：nominal 16-state baseline 未通过，不能在失败基线之上把 RJ1 结果解释为工作裕度。`RJ1=12 Ω` 继续保持 nominal baseline，不发生替换。")
    add("")
    add("## 9. What this does not prove")
    add("")
    add("- 不证明 canonical BVM compatibility；")
    add("- 不证明 single-BVM compatibility；四个 single 记录因 historical model-scope warning 对 intended model closure 为 artifact INVALID，不能支持普遍兼容或不兼容结论；")
    add("- 不证明 timestep convergence、process margin 或其他参数容差；")
    add("- 不证明 T1 compatibility、论文机制身份或唯一 QB operating mechanism；")
    add("- 不证明 BVM2–BVM4 的 commanded state 已逐颗闭合，也不证明一个 BVM contribution 必然对应一个 QB/JTL downstream SFQ。")
    add("")
    add("## 10. Visualization index")
    add("")
    add("- primary representative overview：[`plots/RESULT_OVERVIEW.html`](../plots/RESULT_OVERVIEW.html)")
    add("- single 2×2 overview：[`plots/SINGLE_2X2_OVERVIEW.html`](../plots/SINGLE_2X2_OVERVIEW.html)")
    add("- 每个 run 的独立图见 `plots/runs/<run_id>/RUN_OVERVIEW.html`；完整命令、labels、raw unchanged QA 和 HTML hashes 见 `analysis/visualization_manifest.json`。")
    add("")
    add("## Current gate")
    add("")
    add("`AWAITING_USER_REVIEW`; `user_reviewed=false`; `next_step_authorized=false`; `automatic_next_experiment=false`。")
    (EXP / "analysis/BASELINE_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    # Preserve a small hash index for selected raw and corrected execution attempts.
    raw_paths = [REPO / item["raw"] for item in records_from_results(results)]
    raw_paths.extend(
        EXP / "runs" / "single" / run / "raw/run-01.csv"
        for run in ("S0-J", "S1-J")
        if (EXP / "runs" / "single" / run / "raw/run-01.csv").is_file()
    )
    seen: set[Path] = set()
    hash_lines: list[str] = []
    for path in raw_paths:
        if path in seen:
            continue
        seen.add(path)
        hash_lines.append(f"{sha256(path)}  {path.relative_to(REPO)}")
    (EXP / "analysis/RAW_SHA256SUMS.txt").write_text("\n".join(sorted(hash_lines)) + "\n", encoding="utf-8")
    print(f"wrote {EXP / 'analysis/BASELINE_REPORT.md'}")
    return 0


def records_from_results(results: dict[str, object]) -> list[dict[str, object]]:
    return list(results["four"]) + list(results["single"])  # type: ignore[arg-type]


if __name__ == "__main__":
    raise SystemExit(main())
