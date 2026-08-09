#!/usr/bin/env bash
# run_exp.sh — 历史 v1 实验运行器（2026-08-09 审计后已失效）
# WARNING: 本脚本会调用单位错误的 sfq_metrics.py，并覆盖同名 CSV/JSON。
# 仅用于明确标注的历史复现；不得用于当前物理 Gate。新实验遵循 josim-experiment skill。
# 用法: scripts/run_exp.sh <netlist.cir> <out_name> "<phase_cols>" ["<peak_cols>"]
#   第 4 个参数直接传峰值列名列表（不要带 --peaks 字样），如 "I(L_SL|XBVM1),V(OUT1)"
#   netlist 用仓库相对路径（如 test/final/interface/test_x.cir，include 基于 .cir 位置解析）
#   产出: <netlist_dir>/data/<out>.csv + <out>.json，并自动做 md5 确定性重跑验证
# 历史口径: build/josim-cli (v2.7.2837d13) / invalid v1 sfq_metrics.py / md5 ×2
set -euo pipefail

NETLIST="$1"
OUT="$2"
COLS="$3"
PEAKS="${4:-}"

[ -f "$NETLIST" ] || { echo "ERROR: netlist not found: $NETLIST"; exit 1; }

DIR=$(dirname "$NETLIST")
DATA="${DIR}/data"
mkdir -p "$DATA"
CSV="${DATA}/${OUT}.csv"
JSON="${DATA}/${OUT}.json"

echo "==> sim: $NETLIST -> $CSV"
build/josim-cli -o "$CSV" "$NETLIST"

echo "==> metrics -> $JSON"
if [ -n "$PEAKS" ]; then
  python3 scripts/sfq_metrics.py "$CSV" "$COLS" --peaks "$PEAKS" > "$JSON"
else
  python3 scripts/sfq_metrics.py "$CSV" "$COLS" > "$JSON"
fi

echo "==> determinism re-run (md5 ×2)"
TMP="/tmp/run_exp_${OUT}.csv"
build/josim-cli -o "$TMP" "$NETLIST"
H1=$(md5sum "$CSV" | cut -d' ' -f1)
H2=$(md5sum "$TMP" | cut -d' ' -f1)
rm -f "$TMP"
if [ "$H1" = "$H2" ]; then
  echo "   md5 OK: $H1"
else
  echo "   md5 MISMATCH: $H1 vs $H2 — determinism broken, STOP"
  exit 1
fi

echo "==> done: $CSV $JSON"
