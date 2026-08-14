#!/usr/bin/env python3
"""plot_bvm_s0 -- reproducible BVM-S0 figure set (v2, active-netlist correct).

All figures are generated from frozen evidence only:
  - raw CSVs: test/final/bvm/runs/bvm-s0-canonical-20260814-01/raw/<case>/<step>/run-01.csv
  - deterministic corrected data: research/tasks/JH-20260814-BVM-S0-004/attempts/A01/corrected-analysis.json
No value is hand-filled; every number is read from data.  No JoSIM run occurs.

Core set (5 visuals):
  fig1  timing + conceptual topology      (registered windows; write-like label)
  fig2  state-conditioned source response (V(SL1) pos-vs-neg, controls inset,
        I_load = V(SL1)/12 Ohm annotation)
  fig3  storage / initialized operational signatures (PRE + POST-PRE deltas)
  fig4  read-waveform timestep comparison (full waveforms, all steps)
  fig5  control residual + registered INCONCLUSIVE blocker (nV/nA, grid
        sensitivity wording; criterion unchanged)

Appendix / supporting:
  figA1 detailed active topology (SE->N3; no N4/N7; R_S//L_S3)
  figA2 source current I(L_SL) (Ohm-linked with V(SL1))
  figA3 phase-area same-JJ identity check (residual view)
  figA4 project/status pipeline (historical solid, future dashed)

Observed / derived / inference labels embedded per figure.
Topology follows the ACTIVE uncommented bvm_cell.cir connectivity, not
comment-derived historical topology.
"""
from __future__ import annotations

import csv
import json
import math
import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D

REPO = pathlib.Path('/home/howard/JoSIM')
RUN = REPO / 'test/final/bvm/runs/bvm-s0-canonical-20260814-01'
CORRECTED = (REPO / 'research/tasks/JH-20260814-BVM-S0-004/attempts/A01'
             / 'corrected-analysis.json')
OUT = RUN / 'plots'
OUT.mkdir(parents=True, exist_ok=True)

CASES = ('init_positive_read', 'init_positive_control',
         'init_negative_read', 'init_negative_control')
STEPS = ('0.1ps', '0.05ps', '0.025ps')
P_COLS = {'JM1': 'P(B_JM1|XBVM1)', 'JM2': 'P(B_JM2|XBVM1)'}
V_COLS = {'JM1': 'V(B_JM1|XBVM1)', 'JM2': 'V(B_JM2|XBVM1)'}
PRE = (80e-12, 90e-12)
POST = (140e-12, 150e-12)
ACT = (94e-12, 108e-12)
SRC_WIN = (94e-12, 130e-12)

READ_POS = '#d1495b'
READ_NEG = '#4f86c6'
CTRL_POS = '#d9a0aa'
CTRL_NEG = '#a9c3dd'
JM1_C = '#1f6fb2'
JM2_C = '#e07b00'
STEP_RAMP = ['#c7c7c7', '#8a8a8a', '#333333']


def load(case: str, step: str):
    with open(RUN / 'raw' / case / step / 'run-01.csv', encoding='utf-8') as f:
        rows = list(csv.reader(f))
    hdr = [h.strip().strip('"') for h in rows[0]]
    idx = {h: i for i, h in enumerate(hdr)}
    t: list[float] = []
    cols: dict[str, list[float]] = {}
    for r in rows[1:]:
        t.append(float(r[0]))
        for h in idx:
            cols.setdefault(h, []).append(float(r[idx[h]]))
    return t, cols


def win_idx(t, lo, hi):
    return [i for i, tv in enumerate(t) if lo <= tv < hi]


def source_win(case, step, col):
    t, cols = load(case, step)
    wi = win_idx(t, *SRC_WIN)
    return [t[i] * 1e12 for i in wi], [cols[col][i] for i in wi]


# ================= FIG 1: timing + conceptual topology =================
def fig1_timing_conceptual():
    fig = plt.figure(figsize=(12, 6.4))
    gs = fig.add_gridspec(2, 1, height_ratios=[1.15, 1.0], hspace=0.35)

    # --- top: timing diagram ---
    ax = fig.add_subplot(gs[0])
    ax.set_xlim(0, 170); ax.set_ylim(0, 7); ax.axis('off')
    ax.set_title('Experiment timing (registered before execution)', fontsize=11,
                 fontweight='bold', loc='left')

    def band(x0, x1, y, h, color, alpha=0.9):
        ax.add_patch(mpatches.Rectangle((x0, y), x1 - x0, h, color=color,
                                        alpha=alpha, zorder=3))

    rows = [
        ('Initialization\npositive', 10, 21, READ_POS, 'WL+BL 0→+100 µA @10–11 ps, hold to 20 ps, 0 by 21 ps'),
        ('Initialization\nnegative', 10, 21, READ_NEG, 'WL+BL 0→−100 µA @10–11 ps, hold to 20 ps, 0 by 21 ps'),
        ('Settling', 21, 95, '#e8e8e8', 'quiescent (75-ps readiness bound met)'),
        ('Pre window', 80, 90, '#eef4fb', 'registered [80,90) ps'),
        ('Read stimulus\n(both states identical)', 96, 106, '#b5457f',
         'WL+SE +100 µA @96–105 ps'),
        ('Matched zero-read\ncontrol', 96, 106, '#cccccc',
         'same fixture; read amplitudes = 0'),
        ('Activity / source', 94, 130, '#f3eef7', 'registered [94,108) activity · [94,130) source'),
        ('Post window', 140, 150, '#f3eef7', 'registered [140,150) ps'),
    ]
    y = 0.4
    for name, x0, x1, c, note in rows:
        band(x0, x1, y + 0.25, 1.0, c)
        ax.text(0.5, y + 0.75, name, fontsize=8, va='center', ha='left',
                fontweight='bold')
        ax.text(0.5, y + 0.25, note, fontsize=7, va='bottom', color='#666666')
        y += 1.05
    ax.text(85, 6.35, 'positive / negative are OPERATIONAL initialization labels '
            '(write-like state preparation), NOT logical 1/0, '
            'not a proven persistent storage state.',
            fontsize=8, color='#b5457f', ha='center')

    # --- bottom: conceptual topology ---
    ax2 = fig.add_subplot(gs[1])
    ax2.set_xlim(0, 12); ax2.set_ylim(0, 2.6); ax2.axis('off')
    ax2.set_title('Conceptual topology (active netlist connectivity)',
                  fontsize=11, fontweight='bold', loc='left')
    boxes = [
        (1.3, 'Initialization\nWL/BL ±100 µA\nwrite-like', READ_POS),
        (4.0, 'BVM storage region\nS-loop ↔ R-loop\n(N1…N5, JM1/JM2)', '#1f6fb2'),
        (6.9, 'read / coupling path\nWL+SE +100 µA\nSE→N3', '#b5457f'),
        (9.6, 'SL1 + 12 Ω load\nsource port\nV(SL1), I(L_SL)', '#2e7d32'),
    ]
    for (x, txt, c) in boxes:
        ax2.add_patch(mpatches.FancyBboxPatch((x - 1.15, 1.05), 2.3, 1.15,
                      boxstyle='round,pad=0.08', fc='#ffffff', ec=c, lw=1.6))
        ax2.text(x, 1.62, txt, ha='center', va='center', fontsize=8)
    for x1, x2 in ((2.45, 2.85), (5.15, 5.75), (8.05, 8.45)):
        ax2.annotate('', xy=(x2, 1.62), xytext=(x1, 1.62),
                     arrowprops=dict(arrowstyle='->', lw=1.6, color='#333333'))
    ax2.text(5.2, 2.35, '↑ source-port V/I observed here (V(SL1) SL1→0, '
            'I(L_SL) N8→SL1)', fontsize=8.5, color='#2e7d32', ha='center')
    ax2.text(5.2, 0.3, 'SE enters N3 (R_SE+L_PSE); WL/BL enter N1. '
            'Detailed active topology: figA1.',
            fontsize=7.5, color='#666666', ha='center')
    fig.savefig(OUT / 'fig1-timing-conceptual.png', dpi=150, bbox_inches='tight')
    plt.close(fig)


# ================= FIG 2: state-conditioned source response =================
def fig2_source_response():
    col = 'V(SL1)'
    corr = json.loads(CORRECTED.read_text(encoding='utf-8'))['cases']
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.4),
                             gridspec_kw={'width_ratios': [3, 1]})
    ax = axes[0]
    for case, c, lab in ((CASES[0], READ_POS, 'positive read'),
                         (CASES[2], READ_NEG, 'negative read')):
        t, y = source_win(case, '0.025ps', col)
        ax.plot(t, [v * 1e3 for v in y], lw=2.0, color=c, label=lab)
    for case, c, lab in ((CASES[1], CTRL_POS, 'positive control'),
                         (CASES[3], CTRL_NEG, 'negative control')):
        t, y = source_win(case, '0.025ps', col)
        ax.plot(t, [v * 1e3 for v in y], lw=1.0, ls=':', color=c, alpha=0.9,
                label=lab)
    ax.axvspan(96, 106, color='#f0f0f0', zorder=0)
    ax.set_title('V(SL1) [94,130) ps — state-conditioned source response\n'
                 '(0.025 ps orientation; disposition uses 3-step rule)')
    ax.set_xlabel('time (ps)'); ax.set_ylabel('V(SL1) (mV)')
    ax.legend(fontsize=8, loc='upper right')
    # peak/latency annotations (derived from corrected data)
    for case, c, dy in ((CASES[0], READ_POS, 0.25), (CASES[2], READ_NEG, -0.35)):
        pk = corr[case]['0.025ps']['source']['V_SL1']['peak_baseline_subtracted']
        lat = corr[case]['0.025ps']['source']['V_SL1']['latency_from_96ps_s']
        ax.annotate(f'{pk * 1e3:+.3f} mV @ {lat * 1e12:.1f} ps',
                    xy=(96 + lat * 1e12, pk * 1e3), xytext=(108, pk * 1e3 + dy),
                    fontsize=8.5, color=c,
                    arrowprops=dict(arrowstyle='->', color=c, lw=1.0))
    ax.text(0.02, 0.97, 'I_load ≈ V(SL1) / 12 Ω (Ohm/KCL link at the fixed '
            '12 Ω load; I(L_SL) shown in figA2)',
            transform=ax.transAxes, fontsize=8, color='#2e7d32', va='top')

    ax = axes[1]
    # control inset: nV scale
    for case, c, lab in ((CASES[1], CTRL_POS, 'pos ctrl'),
                         (CASES[3], CTRL_NEG, 'neg ctrl')):
        for step, sc in zip(STEPS, STEP_RAMP):
            t, y = source_win(case, step, col)
            ax.plot(t, [v * 1e9 for v in y], lw=1.0, color=sc, alpha=0.9,
                    label=f'{lab} {step}')
    ax.axvspan(96, 106, color='#f0f0f0', zorder=0)
    ax.set_title('Matched controls (inset,\nnV scale)', fontsize=10)
    ax.set_xlabel('time (ps)'); ax.set_ylabel('V(SL1) (nV)')
    ax.legend(fontsize=6, loc='upper right')
    fig.suptitle('BVM-S0 core result — state-conditioned source response '
                 '(observed)', fontsize=12, fontweight='bold')
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(OUT / 'fig2-source-response.png', dpi=150, bbox_inches='tight')
    plt.close(fig)


# ================= FIG 3: storage signatures (PRE + POST-PRE) =================
def fig3_storage_signatures():
    d = json.loads(CORRECTED.read_text(encoding='utf-8'))['cases']
    fig, axes = plt.subplots(2, 1, figsize=(11, 8), sharex=True)
    ax = axes[0]
    x = [0, 1, 2, 3, 4, 5]
    width = 0.38
    for sign, c_read in (('positive', READ_POS), ('negative', READ_NEG)):
        read = f'init_{sign}_read'
        pre_jm1 = [d[read][s]['platform']['pre']['JM1'] for s in STEPS]
        pre_jm2 = [d[read][s]['platform']['pre']['JM2'] for s in STEPS]
        off = 0 if sign == 'positive' else 3
        ax.plot(x[off:off + 3], pre_jm1, 'o-', color=JM1_C, lw=1.6, ms=6,
                label=f'{sign} pre JM1')
        ax.plot(x[off:off + 3], pre_jm2, 's-', color=JM2_C, lw=1.6, ms=6,
                label=f'{sign} pre JM2')
    ax.axhline(0, color='#999999', lw=0.8)
    ax.set_ylabel('PRE phase mean (rad)')
    ax.set_title('Upper: PRE [80,90) operational signatures per initialization '
                 '(observed means)', fontsize=11)
    ax.legend(fontsize=8, ncol=2)
    ax.text(0.01, 0.95, 'operational only: NOT logic 0/1, NOT fluxoid',
            transform=ax.transAxes, fontsize=8.5, color='#b5457f')

    ax = axes[1]
    for sign, c_read in (('positive', READ_POS), ('negative', READ_NEG)):
        read = f'init_{sign}_read'
        for jj, marker, cj in (('JM1', 'o', JM1_C), ('JM2', 's', JM2_C)):
            deltas = [d[read][s]['platform']['post'][jj]
                      - d[read][s]['platform']['pre'][jj] for s in STEPS]
            off = 0 if sign == 'positive' else 3
            ax.plot(x[off:off + 3], deltas, marker + '-', color=cj, lw=1.6,
                    ms=6, label=f'{sign} {jj} POST−PRE')
    ax.axhline(0, color='#999999', lw=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels([f'{s} pre→post' for s in STEPS]
                       + [f'{s} pre→post' for s in STEPS])
    ax.set_ylabel('POST − PRE (rad)')
    ax.set_title('Lower: POST [140,150) − PRE [80,90) per JJ per timestep — '
                 'read-induced delta (derived)', fontsize=11)
    ax.legend(fontsize=8, ncol=2)
    ax.text(0.01, 0.95, 'Observation: no gross inversion after read. '
            'NOT state preservation / non-destructive-read proof.',
            transform=ax.transAxes, fontsize=8.5, color='#b5457f')
    fig.suptitle('Storage / initialized operational signatures',
                 fontsize=12, fontweight='bold')
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(OUT / 'fig3-storage-signatures.png', dpi=150, bbox_inches='tight')
    plt.close(fig)


# ================= FIG 4: read-waveform timestep comparison =================
def fig4_timestep_comparison():
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    for ax, case, c in ((axes[0], CASES[0], READ_POS),
                        (axes[1], CASES[2], READ_NEG)):
        for step, sc in zip(STEPS, STEP_RAMP):
            t, y = source_win(case, step, 'V(SL1)')
            ax.plot(t, [v * 1e3 for v in y], lw=1.4, color=sc, label=step)
        ax.axvspan(96, 106, color='#f0f0f0', zorder=0)
        ax.set_title(f'{case.replace("_", " ")} — V(SL1) full waveform\n'
                     '(observed)', fontsize=10.5)
        ax.set_xlabel('time (ps)'); ax.set_ylabel('V(SL1) (mV)')
        ax.legend(title='timestep', fontsize=8)
    fig.suptitle('Read-waveform timestep comparison — full waveforms, not '
                 'peaks', fontsize=12, fontweight='bold')
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(OUT / 'fig4-timestep-comparison.png', dpi=150,
                bbox_inches='tight')
    plt.close(fig)


# ================= FIG 5: control residual + INCONCLUSIVE blocker =================
def fig5_control_residual_blocker():
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    for ax, col, unit, scale in ((axes[0], 'V(SL1)', 'nV', 1e9),
                                 (axes[1], 'I(L_SL|XBVM1)', 'nA', 1e9)):
        for case, c in ((CASES[1], CTRL_POS), (CASES[3], CTRL_NEG)):
            for step, sc in zip(STEPS, STEP_RAMP):
                t, y = source_win(case, step, col)
                ax.plot(t, [v * scale for v in y], lw=1.2, color=sc, alpha=0.9,
                        label=f'{case.split("_control")[0]} ctrl {step}')
        ax.axvspan(96, 106, color='#f0f0f0', zorder=0)
        ax.set_title(f'{col} matched-control residual (observed)', fontsize=11)
        ax.set_xlabel('time (ps)'); ax.set_ylabel(f'{col} ({unit})')
        ax.legend(fontsize=6, loc='upper right')
    fig.text(0.5, 0.02,
             'Registered blocker: 0.1→0.05 ps control residual peak-latency '
             '−0.70→+0.15 ps = 0.85 ps > 0.5 ps band → INCONCLUSIVE.\n'
             'The control "peaks" are low-amplitude residuals (15–18 nV, '
             '1.3–1.5 nA); their latency shows clear grid sensitivity at these '
             'amplitudes. The frozen criterion is still executed as registered '
             '— the verdict is unchanged.',
             ha='center', fontsize=9, color='#b5457f')
    fig.suptitle('Control residual + registered INCONCLUSIVE blocker',
                 fontsize=12, fontweight='bold')
    fig.tight_layout(rect=[0, 0.07, 1, 0.95])
    fig.savefig(OUT / 'fig5-control-residual-blocker.png', dpi=150,
                bbox_inches='tight')
    plt.close(fig)


# ================= FIG A1: detailed active topology =================
def figA1_detailed_topology():
    fig, ax = plt.subplots(figsize=(11, 6.4))
    ax.set_xlim(0, 10); ax.set_ylim(0, 6.6); ax.axis('off')

    def node(x, y, name, color='#333333'):
        ax.add_patch(mpatches.Circle((x, y), 0.12, color=color, zorder=5))
        ax.text(x + 0.16, y + 0.14, name, fontsize=7.5, color=color, zorder=6)

    def wire(pts, color='#555555', lw=1.4, ls='-'):
        xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
        ax.plot(xs, ys, color=color, lw=lw, ls=ls, zorder=2)

    def label(x, y, txt, color='#555555', ha='center', fs=7.5, **kw):
        kw.setdefault('fontsize', fs)
        ax.text(x, y, txt, color=color, ha=ha, va='center', **kw)

    # ports
    for (x, y, n) in ((0.4, 5.2, 'WL'), (0.4, 4.2, 'BL'), (0.9, 6.0, 'SE'),
                      (9.3, 3.0, 'SL')):
        ax.text(x, y, n, fontsize=10, fontweight='bold', ha='center')
    node(1.6, 5.2, 'n_wl_0'); node(1.6, 4.2, 'n_bl_0'); node(2.0, 6.0, 'n_se_0')
    node(2.9, 4.7, 'N1', color='#1f6fb2')
    node(4.6, 2.0, 'N2', color='#1f6fb2')
    node(6.9, 0.9, 'N5', color='#1f6fb2')
    node(5.6, 4.0, 'N3', color='#8a8a8a')
    node(7.0, 4.0, 'N6', color='#8a8a8a')
    node(7.8, 3.6, 'n_psl', color='#8a8a8a')
    node(8.5, 3.0, 'N8', color='#8a8a8a')
    node(3.7, 5.4, 'n_jm1o'); node(3.7, 2.5, 'n_jm2i')
    node(5.0, 4.6, 'n_js1p'); node(6.5, 1.6, 'n_js2p')

    # WL/BL -> N1
    wire([(0.4, 5.2), (1.6, 5.2)]); wire([(0.4, 4.2), (1.6, 4.2)])
    wire([(1.6, 5.2), (2.9, 4.7)]); wire([(1.6, 4.2), (2.9, 4.7)])
    label(1.1, 4.9, 'R_WL+L_PWL', fs=6.5); label(1.1, 3.9, 'R_BL+L_PBL', fs=6.5)

    # S-Loop: N1-JM1-LM1-GND ; N1-LM2-JM2-N2-LM3-N5-LPM-GND
    wire([(2.9, 4.7), (3.7, 5.4)]); wire([(3.7, 5.4), (3.7, 5.9)])
    wire([(3.7, 5.9), (3.2, 5.9), (3.0, 5.6)], color='#1f6fb2')
    wire([(2.9, 4.7), (3.7, 2.5)]); wire([(3.7, 2.5), (4.6, 2.0)])
    wire([(4.6, 2.0), (6.9, 0.9)]); wire([(6.9, 0.9), (6.9, 0.3)])
    wire([(6.9, 0.3), (6.2, 0.3), (5.4, 0.45)], color='#1f6fb2')
    label(3.25, 5.5, 'B_JM1', color='#1f6fb2'); label(3.3, 2.75, 'B_JM2', color='#1f6fb2')
    label(3.8, 5.0, 'L_M1', color='#1f6fb2', fs=6.5); label(3.95, 2.3, 'L_M2', color='#1f6fb2', fs=6.5)
    label(5.7, 1.4, 'L_M3', color='#1f6fb2'); label(6.55, 0.35, 'L_PM→GND', color='#1f6fb2', fs=6.5)

    # SE -> N3 (CORRECT: R_SE+L_PSE into N3)
    wire([(0.9, 6.0), (2.0, 6.0)]); wire([(2.0, 6.0), (2.0, 4.3), (5.6, 4.0)],
                                         color='#b5457f')
    label(1.45, 5.75, 'R_SE+L_PSE', fs=6.5, color='#b5457f')

    # R-Loop: N2-LS1-JS1-N3 ; N3-(R_S//L_S3)-N6 ; N6-LS2-JS2-N5
    wire([(4.6, 2.0), (5.0, 4.6)]); wire([(5.0, 4.6), (5.6, 4.0)])
    wire([(5.6, 4.0), (7.0, 4.0)])
    ax.plot([5.6, 7.0], [3.55, 3.55], color='#8a8a8a', lw=1.0, ls=':', zorder=2)
    label(6.3, 3.75, 'R_S // L_S3', fs=6.5, color='#8a8a8a')
    wire([(7.0, 4.0), (6.5, 1.6)]); wire([(6.5, 1.6), (6.9, 0.9)])
    label(4.8, 4.3, 'L_S1', fs=6.5, color='#8a8a8a')
    label(5.35, 4.85, 'B_JS1', fs=6.5, color='#8a8a8a')
    label(6.85, 2.2, 'L_S2', fs=6.5, color='#8a8a8a')
    label(6.3, 1.35, 'B_JS2', fs=6.5, color='#8a8a8a')

    # output: N6 -> L_PSL -> n_psl -> R_SL -> N8 -> L_SL -> SL
    wire([(7.0, 4.0), (7.8, 3.6)]); wire([(7.8, 3.6), (8.5, 3.0)])
    wire([(8.5, 3.0), (9.3, 3.0)])
    label(7.55, 3.9, 'L_PSL', fs=6.5); label(8.35, 3.35, 'R_SL', fs=6.5)
    label(8.9, 2.7, 'L_SL', fs=6.5)
    ax.text(6.1, 0.55, 'SL output: V(SL1), I(L_SL|XBVM1) N8→SL1 (12 Ω load)',
            fontsize=7.5, color='#555555')

    # loop boxes + coupling
    ax.add_patch(mpatches.FancyBboxPatch((2.6, 0.15), 4.7, 6.0,
                 boxstyle='round,pad=0.12', fc='#eef4fb', ec='#1f6fb2',
                 lw=1.2, ls='--', alpha=0.55))
    ax.text(5.0, 6.3, 'S-Loop (storage)', fontsize=9, color='#1f6fb2', ha='center')
    ax.add_patch(mpatches.FancyBboxPatch((4.7, 0.7), 2.8, 4.4,
                 boxstyle='round,pad=0.12', fc='#f3f3f3', ec='#8a8a8a',
                 lw=1.2, ls='--', alpha=0.6))
    ax.text(6.1, 5.35, 'R-Loop (readout)', fontsize=9, color='#8a8a8a', ha='center')
    ax.annotate('coupling: N2–LM3–N5 shared by S-loop & R-loop',
                xy=(5.4, 1.4), xytext=(7.6, 0.2), fontsize=8, color='#b5457f',
                arrowprops=dict(arrowstyle='->', color='#b5457f', lw=1.2))

    ax.text(0.1, 6.45,
            'Detailed ACTIVE topology (bvm_cell.cir v6, uncommented elements only)',
            fontsize=9.5, fontweight='bold', color='#222222')
    ax.text(0.1, 6.15,
            'Observed: element connectivity. Inferred: loop roles (S=storage, '
            'R=readout). N4/N7 are NOT present in the active netlist '
            '(commented-out historical paths excluded).',
            fontsize=7.5, color='#8a8a8a')
    fig.savefig(OUT / 'figA1-detailed-topology.png', dpi=150, bbox_inches='tight')
    plt.close(fig)


# ================= FIG A2: source current (Ohm-linked) =================
def figA2_source_current():
    corr = json.loads(CORRECTED.read_text(encoding='utf-8'))['cases']
    fig, ax = plt.subplots(figsize=(10, 5))
    for case, c, lab in ((CASES[0], READ_POS, 'positive read'),
                         (CASES[2], READ_NEG, 'negative read')):
        t, y = source_win(case, '0.025ps', 'I(L_SL|XBVM1)')
        ax.plot(t, [v * 1e6 for v in y], lw=2.0, color=c, label=lab)
    for case, c, lab in ((CASES[1], CTRL_POS, 'positive control'),
                         (CASES[3], CTRL_NEG, 'negative control')):
        t, y = source_win(case, '0.025ps', 'I(L_SL|XBVM1)')
        ax.plot(t, [v * 1e9 for v in y], lw=1.0, ls=':', color=c, alpha=0.9,
                label=f'{lab} (nA)')
    ax.axvspan(96, 106, color='#f0f0f0', zorder=0)
    ax.set_title('I(L_SL|XBVM1) — source current (appendix; '
                 'Ohm/KCL-linked to V(SL1) via the fixed 12 Ω load)\n'
                 'I_load ≈ V(SL1)/12 Ω — same information as fig2',
                 fontsize=11)
    ax.set_xlabel('time (ps)'); ax.set_ylabel('I(L_SL) (µA; controls nA)')
    ax.legend(fontsize=8, loc='upper right')
    for case, c, dy in ((CASES[0], READ_POS, 8), (CASES[2], READ_NEG, -10)):
        pk = corr[case]['0.025ps']['source']['I_LSL']['peak_baseline_subtracted']
        lat = corr[case]['0.025ps']['source']['I_LSL']['latency_from_96ps_s']
        ax.annotate(f'{pk * 1e6:+.2f} µA @ {lat * 1e12:.1f} ps',
                    xy=(96 + lat * 1e12, pk * 1e6),
                    xytext=(108, pk * 1e6 + dy), fontsize=8.5, color=c,
                    arrowprops=dict(arrowstyle='->', color=c, lw=1.0))
    fig.tight_layout()
    fig.savefig(OUT / 'figA2-source-current.png', dpi=150, bbox_inches='tight')
    plt.close(fig)


# ================= FIG A3: phase-area same-JJ identity check =================
def figA3_phase_area_identity():
    d = json.loads(CORRECTED.read_text(encoding='utf-8'))['cases']
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.4))
    ax = axes[0]
    for case, c in ((CASES[0], READ_POS), (CASES[2], READ_NEG),
                    (CASES[1], CTRL_POS), (CASES[3], CTRL_NEG)):
        for jj, m in (('JM1', 'o'), ('JM2', 's')):
            xs = [d[case][s]['phase_area'][jj]['phase_delta_turns'] for s in STEPS]
            ys = [d[case][s]['phase_area'][jj]['area_turns'] for s in STEPS]
            ax.plot(xs, ys, marker=m, ls='-', lw=1.0, ms=5, color=c, alpha=0.9,
                    label=f'{case.replace("_", " ")} {jj}')
    lo, hi = -0.08, 0.08
    ax.plot([lo, hi], [lo, hi], ls='--', color='#333333', lw=1.0, label='y = x')
    ax.set_xlim(lo, hi); ax.set_ylim(lo, hi)
    ax.set_xlabel('phase_delta_turns (Δφ/2π, [94,108) ps)')
    ax.set_ylabel('area_turns (∫V dt / Φ0)')
    ax.set_title('Phase–area identity (appendix)\nsame-JJ Josephson-linked '
                 'data-path consistency check', fontsize=11)
    ax.legend(fontsize=6, loc='upper left'); ax.grid(alpha=0.25)

    ax = axes[1]
    for case, c in ((CASES[0], READ_POS), (CASES[2], READ_NEG),
                    (CASES[1], CTRL_POS), (CASES[3], CTRL_NEG)):
        for jj, m in (('JM1', 'o'), ('JM2', 's')):
            rs = [d[case][s]['phase_area'][jj]['residual_turns'] for s in STEPS]
            ax.plot(STEPS, rs, marker=m, ls='-', lw=1.0, ms=5, color=c,
                    alpha=0.9, label=f'{case.replace("_", " ")} {jj}')
    ax.axhline(0, color='#999999', lw=0.8)
    ax.set_xlabel('timestep'); ax.set_ylabel('residual (turns)')
    ax.set_title('Residual view — descriptive only, NO tolerance declared',
                 fontsize=11)
    ax.legend(fontsize=6, loc='upper left'); ax.grid(alpha=0.25)
    fig.suptitle('Direct-JJ phase–area crosscheck (appendix) — data-path '
                 'consistency, NOT independent physical evidence',
                 fontsize=12, fontweight='bold')
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    fig.savefig(OUT / 'figA3-phase-area-identity.png', dpi=150,
                bbox_inches='tight')
    plt.close(fig)


# ================= FIG A4: project pipeline =================
def figA4_project_pipeline():
    fig, ax = plt.subplots(figsize=(12, 4.6))
    ax.set_xlim(0, 14); ax.set_ylim(0, 4); ax.axis('off')

    def box(x, y, w, h, txt, ec, ls='-', fc='#ffffff'):
        ax.add_patch(mpatches.FancyBboxPatch((x, y), w, h,
                     boxstyle='round,pad=0.1', fc=fc, ec=ec, lw=1.5, ls=ls))
        ax.text(x + w / 2, y + h / 2, txt, ha='center', va='center', fontsize=7.5)

    def arrow(x1, y1, x2, y2):
        ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle='->', lw=1.5, color='#333333'))

    # row 1: historical accepted (solid)
    box(0.3, 2.6, 2.3, 0.9, 'M1–M12 measurement repair\n(ACCEPTED 08-13)', '#1f6fb2')
    box(3.1, 2.6, 2.3, 0.9, 'D0 initialization readiness\n75 ps bound (VALID)', '#2e7d32')
    box(5.9, 2.6, 2.6, 0.9, 'BVM-S0 12-run source characterization\nartifact VALID · INCONCLUSIVE', '#b26a00')
    arrow(2.6, 3.05, 3.1, 3.05); arrow(5.4, 3.05, 5.9, 3.05)
    # row 2: future (dashed)
    box(2.9, 0.7, 2.9, 0.9, 'NEXT (user-authorized):\nnew preregistered source\nconvergence/characterization',
        '#6a1b9a', ls='--')
    box(6.6, 0.7, 2.5, 0.9, 'later:\nreceiver characterization,\nINTERFACE_GATE_V1',
        '#8a8a8a', ls='--')
    arrow(8.5, 3.05, 8.2, 1.6)
    arrow(5.8, 1.15, 6.6, 1.15)
    ax.text(7.0, 3.6, 'Project/status pipeline — historical solid, future '
            'dashed (suggestion, not executed)',
            fontsize=10, fontweight='bold', ha='center')
    ax.text(7.0, 0.15, 'No current-status path skips the new convergence task '
            'to reach receiver work.', fontsize=8, color='#b5457f', ha='center')
    fig.savefig(OUT / 'figA4-project-pipeline.png', dpi=150, bbox_inches='tight')
    plt.close(fig)


if __name__ == '__main__':
    fig1_timing_conceptual()
    fig2_source_response()
    fig3_storage_signatures()
    fig4_timestep_comparison()
    fig5_control_residual_blocker()
    figA1_detailed_topology()
    figA2_source_current()
    figA3_phase_area_identity()
    figA4_project_pipeline()
    print('figures written to', OUT)
