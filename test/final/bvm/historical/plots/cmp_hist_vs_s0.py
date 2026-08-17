#!/usr/bin/env python3
"""cmp_hist_vs_s0 -- BVM historical-vs-current comparison figures (matplotlib).

Native viewers: scripts/josim-plot2.py HTMLs in this same directory (old-school
JoSIM look, seconds axis as the tool renders). This script produces the
ALIGNED comparison figures the HTMLs cannot: absolute-ps axes, matched windows,
shared y-scales, old/current labeled.

DATA
====
- historical: hist_test_bvm_final.csv (DERIVED from the Jul-17 viz HTML; the
  decoder stores phase in TRUE rad after a documented turns->rad correction;
  time in seconds; 0.5 ps grid, 0-159.5 ps)
- current   : frozen BVM-S0 canonical 0.025ps CSVs via plots/_viz_data.py
  (init_positive_read / init_negative_read; no new JoSIM run)

CONVENTIONS (README-figure-index.md)
- positive init/read = #d1495b (warm), negative = #4f86c6 (blue), historical = #888
- time axis: absolute ps everywhere; read pulse spans shaded
- phase shown raw rad AND turns (=rad/2pi); labels never claim SFQ count
- observation-only figures: no scientific verdict is attached here

Outputs (PNG, 160 dpi, dark bg matching the native viewers):
  cmp-1-inputs-full.png      I(WL)/I(BL)/I(SE), 0-170 ps
  cmp-2-jm1-phase-raw.png    P(JM1) rad, 0-170 ps
  cmp-3-jm1-phase-turns.png  P(JM1) turns, 0-170 ps
  cmp-4-lsl-full.png         I(L_SL), 0-170 ps
  cmp-5-read-aligned-pos.png R1 [28,68] vs cur-pos [94,134]: P(JM1) + I(L_SL)
  cmp-6-read-aligned-neg.png R0 [78,118] vs cur-neg [94,134]: P(JM1) + I(L_SL)
  cmp-7-hist-js-phases.png   JS1/JS2 rad+turns (historical-only probes)
  cmp-8-current-extra.png    V(SL1)/V(JM1)/V(JM2)/P(JM2) (current-only probes)
"""
from __future__ import annotations

import csv
import math
import pathlib
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

REPO = pathlib.Path('/home/howard/JoSIM')
HIST = REPO / 'test/final/bvm/historical'
OUT = HIST / 'plots'
CUR = REPO / 'test/final/bvm/runs/bvm-s0-canonical-20260814-01/plots'
sys.path.insert(0, str(CUR))
from _viz_data import load_dataset  # noqa: E402

C_POS, C_NEG, C_HIST = '#d1495b', '#4f86c6', '#8a8a8a'
TAU = 2 * math.pi
DPI = 160
BG = '#141414'


def load_hist() -> dict:
    """historical derived CSV -> {name: [(t_ps, value), ...]} (phase in rad)."""
    rows = list(csv.reader(open(HIST / 'hist_test_bvm_final.csv', encoding='utf-8')))
    hdr = rows[0]
    out = {}
    for j, nm in enumerate(hdr[1:], start=1):
        out[nm] = [(float(r[0]) * 1e12, float(r[j])) for r in rows[1:]]
    return out


def style_ax(ax, title: str):
    ax.set_facecolor(BG)
    ax.tick_params(colors='#cccccc', labelsize=8)
    for s in ax.spines.values():
        s.set_color('#555555')
    ax.set_title(title, color='#eeeeee', fontsize=10, pad=4)
    ax.grid(True, color='#2a2a2a', linewidth=0.5)
    ax.set_xlabel('time (ps)', color='#cccccc', fontsize=8)


def panel(fig, n, rows, cols, i, title, xlabel=True, ylabel=True):
    ax = fig.add_subplot(rows, cols, i)
    style_ax(ax, title)
    if not xlabel:
        ax.set_xlabel('')
    if not ylabel:
        ax.set_ylabel('')
    return ax


def shade_read(ax, lo, hi, color):
    ax.axvspan(lo, hi, color=color, alpha=0.08, zorder=0)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    h = load_hist()
    pos = load_dataset('init_positive_read', '0.025ps')
    neg = load_dataset('init_negative_read', '0.025ps')
    t_pos, c_pos = pos['t_ps'], pos['c']
    t_neg, c_neg = neg['t_ps'], neg['c']
    fig_ctx = dict(facecolor=BG)
    plt.rcParams['figure.facecolor'] = BG
    plt.rcParams['savefig.facecolor'] = BG

    # ---- cmp-1: inputs, full range ----
    fig = plt.figure(figsize=(11, 7), **fig_ctx)
    for i, (nm, title) in enumerate([
            ('I(I_WL1)', 'I(WL1) — word-line write/read current'),
            ('I(I_BL1)', 'I(BL1) — bit-line write current (current S0 has no BL probe)'),
            ('I(I_SE1)', 'I(SE1) — sense-line read current')], start=1):
        ax = panel(fig, None, 3, 1, i, title, xlabel=(i == 3))
        ax.plot([p[0] for p in h[nm]], [p[1] * 1e6 for p in h[nm]],
                color=C_HIST, lw=1.2, label='historical (12-JJ load, 0.5ps)')
        ax.plot(t_pos, [v * 1e6 for v in c_pos['I_WL1' if nm == 'I(I_WL1)' else 'I_SE1']],
                color=C_POS, lw=0.8, label='S0 positive-read (12-ohm)')
        if nm == 'I(I_WL1)':
            ax.plot(t_neg, [v * 1e6 for v in c_neg['I_WL1']],
                    color=C_NEG, lw=0.8, label='S0 negative-read')
        ax.set_ylabel('µA', color='#cccccc', fontsize=8)
        ax.legend(fontsize=7, loc='upper right', framealpha=0.3)
        if nm == 'I(I_WL1)':
            shade_read(ax, 10, 21, '#7f7f7f')
            shade_read(ax, 96, 105, '#d1495b')
    fig.suptitle('BVM inputs: historical 6-event sequence vs current init+read protocol',
                 color='#eeeeee', fontsize=11)
    fig.tight_layout()
    fig.savefig(OUT / 'cmp-1-inputs-full.png', dpi=DPI)
    plt.close(fig)

    # ---- cmp-2/3: P(JM1) raw rad + turns, full range ----
    for unit, div in [('raw', 1.0), ('turns', TAU)]:
        fig = plt.figure(figsize=(11, 4.5), **fig_ctx)
        ax = panel(fig, None, 1, 1, 1,
                   f'P(JM1) — phase in {"raw rad" if unit == "raw" else "turns (rad/2π)"}, full run')
        for nm, col, lab in [(h['P(B_JM1|XBVM1)'], C_HIST, 'historical'),
                             (list(zip(t_pos, c_pos['P_JM1'])), C_POS, 'S0 positive-init'),
                             (list(zip(t_neg, c_neg['P_JM1'])), C_NEG, 'S0 negative-init')]:
            ax.plot([p[0] for p in nm], [p[1] / div for p in nm], color=col, lw=1.0, label=lab)
        ax.set_ylabel('rad' if unit == 'raw' else 'turns', color='#cccccc', fontsize=8)
        ax.legend(fontsize=8, loc='upper left', framealpha=0.3)
        for lo, hi, lab in [(30, 40, 'R1'), (80, 90, 'R0'), (110, 120, 'HS_WL'),
                            (96, 105, 'S0 read')]:
            shade_read(ax, lo, hi, '#7f7f7f' if lo < 96 else '#d1495b')
        fig.suptitle('JM1 phase state: historical ±0.94-turn plateau (embedded-turns corrected) '
                     '== S0 ±0.94 turns', color='#eeeeee', fontsize=10)
        fig.tight_layout()
        fig.savefig(OUT / f'cmp-{2 if unit == "raw" else 3}-jm1-phase-{unit}.png', dpi=DPI)
        plt.close(fig)

    # ---- cmp-4: I(L_SL) full range ----
    fig = plt.figure(figsize=(11, 4.5), **fig_ctx)
    ax = panel(fig, None, 1, 1, 1, 'I(L_SL) — SL load current, full run')
    for nm, col, lab in [(h['I(L_SL|XBVM1)'], C_HIST, 'historical (12-JJ stack load)'),
                         (list(zip(t_pos, c_pos['I_LSL'])), C_POS, 'S0 positive-init (12 Ω)'),
                         (list(zip(t_neg, c_neg['I_LSL'])), C_NEG, 'S0 negative-init (12 Ω)')]:
        ax.plot([p[0] for p in nm], [p[1] * 1e6 for p in nm], color=col, lw=1.0, label=lab)
    ax.set_ylabel('µA', color='#cccccc', fontsize=8)
    ax.legend(fontsize=8, loc='upper right', framealpha=0.3)
    for lo, hi in [(30, 40), (80, 90), (110, 120), (140, 150), (96, 105)]:
        shade_read(ax, lo, hi, '#7f7f7f' if lo < 96 else '#d1495b')
    fig.suptitle('SL read response: positive-state read ≈+75 µA in BOTH eras (75.7 hist / 75.3 S0); '
                 'negative-state read: early small-positive then −23 µA (hist R0) / −26 µA (S0)',
                 color='#eeeeee', fontsize=10)
    fig.tight_layout()
    fig.savefig(OUT / 'cmp-4-lsl-full.png', dpi=DPI)
    plt.close(fig)

    # ---- cmp-5/6: read-aligned windows, P(JM1) + I(L_SL), shared y-scales ----
    def aligned(hist_win, hist_label, cur, cur_label, cur_col, fname, suptitle):
        hlo, hhi = hist_win
        clo, chi = 94, 134
        t, c = cur['t_ps'], cur['c']
        fig = plt.figure(figsize=(11, 7), **fig_ctx)
        for i, (title, pick, ylab) in enumerate([
                (f'P(JM1) rad — {hist_label} vs {cur_label}',
                 lambda d: d['P_JM1'], 'rad'),
                (f'I(L_SL) µA — {hist_label} vs {cur_label}',
                 lambda d: d['I_LSL'], 'µA')], start=1):
            ax = panel(fig, None, 2, 1, i, title, xlabel=(i == 2))
            ax.set_xlim(0, 40)
            hpts = [(p[0] - hlo, p[1]) for p in h['P(B_JM1|XBVM1)'] if hlo <= p[0] <= hhi]
            lpts = [(p[0] - hlo, p[1]) for p in h['I(L_SL|XBVM1)'] if hlo <= p[0] <= hhi]
            cpts = [(t[j] - clo, pick(c)[j]) for j in range(len(t)) if clo <= t[j] <= chi]
            if i == 1:
                ax.plot([p[0] for p in hpts], [p[1] for p in hpts],
                        color=C_HIST, lw=1.4, label=hist_label)
                ax.plot([p[0] for p in cpts], [p[1] for p in cpts],
                        color=cur_col, lw=1.0, label=cur_label)
            else:
                ax.plot([p[0] for p in lpts], [p[1] * 1e6 for p in lpts],
                        color=C_HIST, lw=1.4, label=hist_label)
                ax.plot([p[0] for p in cpts], [p[1] * 1e6 for p in cpts],
                        color=cur_col, lw=1.0, label=cur_label)
            shade_read(ax, 2, 11, '#d1495b')
            ax.set_ylabel(ylab, color='#cccccc', fontsize=8)
            ax.set_xlabel('time from read-pulse onset (ps)', color='#cccccc', fontsize=8)
            ax.legend(fontsize=8, loc='upper right', framealpha=0.3)
        fig.suptitle(suptitle, color='#eeeeee', fontsize=10)
        fig.tight_layout()
        fig.savefig(OUT / fname, dpi=DPI)
        plt.close(fig)

    aligned((28, 68), 'historical R1 (read of +0.94-turn state)',
            pos, 'S0 positive-init read', C_POS, 'cmp-5-read-aligned-pos.png',
            'Read of the POSITIVE state: historical R1 vs S0 — same +100 µA WL+SE pulse, '
            'same ≈+75 µA load-current peak')
    aligned((78, 118), 'historical R0 (read of −0.94-turn state)',
            neg, 'S0 negative-init read', C_NEG, 'cmp-6-read-aligned-neg.png',
            'Read of the NEGATIVE state: JM1 dips to ≈−4.96 rad in BOTH eras; load current '
            'early-positive then −23 µA (hist 12-JJ stack) vs −26 µA (S0 12 Ω)')

    # ---- cmp-7: historical JS1/JS2 (current has no JS probes) ----
    fig = plt.figure(figsize=(11, 7), **fig_ctx)
    for i, nm in enumerate(['P(B_JS1|XBVM1)', 'P(B_JS2|XBVM1)'], start=1):
        ax = panel(fig, None, 2, 2, i, f'{nm} — raw rad (historical-only probe)')
        ax.plot([p[0] for p in h[nm]], [p[1] for p in h[nm]], color=C_HIST, lw=1.2)
        ax.set_ylabel('rad', color='#cccccc', fontsize=8)
        ax2 = panel(fig, None, 2, 2, i + 2, f'{nm} — turns (rad/2π)')
        ax2.plot([p[0] for p in h[nm]], [p[1] / TAU for p in h[nm]], color=C_HIST, lw=1.2)
        ax2.set_ylabel('turns', color='#cccccc', fontsize=8)
    fig.suptitle('Historical JS1/JS2 phases — probes absent from current S0 runs (channel gap)',
                 color='#eeeeee', fontsize=10)
    fig.tight_layout()
    fig.savefig(OUT / 'cmp-7-hist-js-phases.png', dpi=DPI)
    plt.close(fig)

    # ---- cmp-8: current-only probes ----
    fig = plt.figure(figsize=(11, 7), **fig_ctx)
    rows = [(t_pos, c_pos), (t_neg, c_neg)]
    for i, (nm, title) in enumerate([
            ('V_SL1', 'V(SL1) — read output voltage (historical had no V probe)'),
            ('V_JM1', 'V(JM1) — JM1 junction voltage'),
            ('V_JM2', 'V(JM2) — JM2 stabilizer voltage'),
            ('P_JM2', 'P(JM2) — JM2 phase, rad')], start=1):
        ax = panel(fig, None, 4, 1, i, title, xlabel=(i == 4))
        for (t, c), col in [(rows[0], C_POS), (rows[1], C_NEG)]:
            ax.plot(t, [v * (1e3 if 'V' in nm else 1) for v in c[nm]],
                    color=col, lw=0.8, label='positive-init' if col == C_POS else 'negative-init')
        ax.set_ylabel('mV' if 'V' in nm else 'rad', color='#cccccc', fontsize=8)
        if i == 1:
            ax.legend(fontsize=7, framealpha=0.3)
    fig.suptitle('Current-only probes (channel gap on the historical side) — '
                 'V(SL1)=0.90 mV / −0.32 mV at read', color='#eeeeee', fontsize=10)
    fig.tight_layout()
    fig.savefig(OUT / 'cmp-8-current-extra.png', dpi=DPI)
    plt.close(fig)

    print('wrote:')
    for p in sorted(OUT.glob('cmp-*.png')):
        print(f'  {p.name}  ({p.stat().st_size} bytes)')


if __name__ == '__main__':
    main()
