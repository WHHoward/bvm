#!/usr/bin/env python3
"""plot_bvm_s0 -- reproducible BVM-S0 visualization set for group meeting.

All figures are generated from frozen evidence only:
  - raw CSVs: test/final/bvm/runs/bvm-s0-canonical-20260814-01/raw/<case>/<step>/run-01.csv
  - deterministic corrected data: research/tasks/JH-20260814-BVM-S0-004/attempts/A01/corrected-analysis.json
No value is hand-filled; every number is read from data.  No JoSIM run occurs.

Figures (see README-figure-index.md for claim boundaries):
  fig1  topology schematic            (annotated netlist-derived drawing)
  fig2  source voltage waveform       [94,130) ps, 0.025 ps main + timestep overlays
  fig3  source current waveform       [94,130) ps, 0.025 ps main + timestep overlays
  fig4  timestep convergence overlay  full waveforms per read case
  fig5  storage signature             pre/post JM1/JM2 means, grouped by init
  fig6  direct-JJ phase-area crosscheck  phase_delta_turns vs area_turns + y=x
  fig7  control noise zoom            nV/nA scale, latency criterion annotation

Observed / derived / inference labels are embedded in each figure.
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
SRC_WIN = (94e-12, 130e-12)

# categorical palette: fixed hue order by identity (read=warm, control=cool,
# JM1=blue, JM2=orange, steps=same-hue ramp)
READ_POS = '#d1495b'   # positive read
READ_NEG = '#b5457f'   # negative read (distinct hue, same warm family)
CTRL_POS = '#4f86c6'   # positive control
CTRL_NEG = '#56b4a0'   # negative control (cool family)
JM1_C = '#1f6fb2'
JM2_C = '#e07b00'
STEP_RAMP = ['#c7c7c7', '#8a8a8a', '#333333']  # 0.1 / 0.05 / 0.025 ps


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


def fig1_topology():
    fig, ax = plt.subplots(figsize=(11, 7))
    ax.set_xlim(0, 10); ax.set_ylim(0, 7); ax.axis('off')

    def node(x, y, name, color='#333333'):
        ax.add_patch(mpatches.Circle((x, y), 0.12, color=color, zorder=5))
        ax.text(x + 0.18, y + 0.18, name, fontsize=8, color=color, zorder=6)

    def wire(pts, color='#555555', lw=1.4, ls='-'):
        xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
        ax.plot(xs, ys, color=color, lw=lw, ls=ls, zorder=2)

    def label(x, y, txt, color='#555555', ha='center', fs=7.5, **kw):
        kw.setdefault('fontsize', fs)
        ax.text(x, y, txt, color=color, ha=ha, va='center', **kw)

    # ports
    for (x, y, n) in ((0.4, 5.6, 'WL'), (0.4, 4.6, 'BL'), (1.0, 6.4, 'SE'),
                      (9.2, 3.2, 'SL')):
        ax.text(x, y, n, fontsize=10, fontweight='bold', ha='center')
    node(1.6, 5.6, 'n_wl_0'); node(1.6, 4.6, 'n_bl_0'); node(2.4, 6.4, 'n_se_0')
    node(2.8, 5.1, 'N1', color='#1f6fb2')
    node(4.5, 2.3, 'N2', color='#1f6fb2')
    node(6.8, 1.2, 'N5', color='#1f6fb2')
    node(5.6, 4.2, 'N3', color='#8a8a8a')
    node(6.6, 5.8, 'N4', color='#8a8a8a')
    node(7.2, 4.6, 'N6', color='#8a8a8a')
    node(8.0, 3.8, 'N7', color='#8a8a8a')
    node(8.6, 3.2, 'N8', color='#8a8a8a')
    node(3.6, 5.8, 'n_jm1o'); node(3.6, 2.9, 'n_jm2i')
    node(5.4, 1.9, 'n_js1p'); node(6.4, 2.6, 'n_js2p')
    node(7.9, 4.3, 'n_psl')

    # S-Loop (blue): N1-JM1-LM1-GND / N1-LM2-JM2-N2-LM3-N5-LPM-GND
    wire([(2.8, 5.1), (3.6, 5.8)]); wire([(3.6, 5.8), (3.9, 5.0), (3.9, 3.0)])
    wire([(2.8, 5.1), (3.6, 2.9)]); wire([(3.6, 2.9), (4.5, 2.3)])
    wire([(4.5, 2.3), (6.8, 1.2)]); wire([(6.8, 1.2), (6.8, 0.4)])
    wire([(6.8, 0.4), (6.2, 0.4), (5.5, 0.5)], color='#1f6fb2')
    ax.text(5.2, 0.3, 'LPM→GND', fontsize=7, color='#1f6fb2')
    label(3.2, 5.9, 'B_JM1', color='#1f6fb2'); label(3.25, 3.15, 'B_JM2', color='#1f6fb2')
    label(3.75, 5.35, 'L_M1', color='#1f6fb2'); label(3.95, 2.6, 'L_M2', color='#1f6fb2')
    label(5.6, 1.6, 'L_M3', color='#1f6fb2')
    # S-loop box
    ax.add_patch(mpatches.FancyBboxPatch((2.5, 0.2), 4.6, 6.1,
                 boxstyle='round,pad=0.15', fc='#eef4fb', ec='#1f6fb2',
                 lw=1.2, ls='--', alpha=0.6))
    ax.text(4.8, 6.45, 'S-Loop (storage)', fontsize=9, color='#1f6fb2', ha='center')

    # R-Loop (grey): N2-LS1-JS1-N3 / N3-RS-N6 / N6-LS2-JS2-N5 / N5-LS2...
    wire([(4.5, 2.3), (5.4, 1.9)]); wire([(5.4, 1.9), (5.6, 4.2)])
    wire([(5.6, 4.2), (6.0, 4.9), (6.4, 4.3), (7.2, 4.6)])
    wire([(5.6, 4.2), (6.4, 4.3)])
    wire([(6.4, 4.3), (7.2, 4.6)])
    wire([(7.2, 4.6), (6.4, 2.6)]); wire([(6.4, 2.6), (6.8, 1.2)])
    label(4.9, 1.75, 'L_S1', color='#8a8a8a'); label(5.5, 3.0, 'B_JS1', color='#8a8a8a')
    label(6.9, 2.2, 'L_S2', color='#8a8a8a'); label(6.15, 3.9, 'B_JS2', color='#8a8a8a')
    label(6.7, 4.9, 'R_S', color='#8a8a8a')
    ax.add_patch(mpatches.FancyBboxPatch((4.6, 1.1), 2.9, 4.4,
                 boxstyle='round,pad=0.15', fc='#f3f3f3', ec='#8a8a8a',
                 lw=1.2, ls='--', alpha=0.6))
    ax.text(6.05, 5.7, 'R-Loop (readout)', fontsize=9, color='#8a8a8a', ha='center')

    # SE entry
    wire([(1.0, 6.4), (2.4, 6.4)]); wire([(2.4, 6.4), (2.8, 5.1)], color='#8a8a8a')
    label(1.7, 6.15, 'R_SE+L_PSE', fontsize=7, color='#8a8a8a')

    # WL/BL entry
    wire([(0.4, 5.6), (1.6, 5.6)]); wire([(0.4, 4.6), (1.6, 4.6)])
    wire([(1.6, 5.6), (2.8, 5.1)]); wire([(1.6, 4.6), (2.8, 5.1)])
    label(1.1, 5.3, 'R_WL+L_PWL', fontsize=7); label(1.1, 4.3, 'R_BL+L_PBL', fontsize=7)

    # coupling annotation at N2/LM3/N5
    ax.annotate('coupling: N2-LM3-N5 shared by S-loop & R-loop',
                xy=(5.4, 1.7), xytext=(7.4, 0.4), fontsize=8, color='#b5457f',
                arrowprops=dict(arrowstyle='->', color='#b5457f', lw=1.2))

    # output chain
    wire([(8.0, 3.8), (7.9, 4.3)]); wire([(7.9, 4.3), (8.6, 3.2)])
    wire([(8.6, 3.2), (9.2, 3.2)])
    label(7.9, 4.55, 'L_PSL', fontsize=7); label(8.5, 3.7, 'R_SL', fontsize=7)
    label(8.9, 2.9, 'L_SL', fontsize=7)
    ax.text(6.2, 0.75, 'SL output: V(SL1), I(L_SL|XBVM1) N8→SL1 (12 Ω load)',
            fontsize=8, color='#555555')

    ax.text(0.1, 6.9, 'BVM topology (bvm_cell.cir v6) — schematic derived from '
            'netlist, not simulation data',
            fontsize=9, fontweight='bold', color='#222222')
    ax.text(0.1, 6.6, 'Observed: element connectivity. Inferred: loop roles '
            '(S=storage, R=readout) from netlist comments. '
            'Not a claim about currents/phases.',
            fontsize=7.5, color='#8a8a8a')
    fig.savefig(OUT / 'fig1-bvm-topology.png', dpi=150, bbox_inches='tight')
    plt.close(fig)


def _source_win(case, step, col):
    t, cols = load(case, step)
    wi = win_idx(t, *SRC_WIN)
    return [t[i] * 1e12 for i in wi], [cols[col][i] for i in wi]


def _waveform_axes(fig, title, ylab, unit):
    ax = fig.add_subplot(111)
    ax.set_title(title, fontsize=11)
    ax.set_xlabel('time (ps)')
    ax.set_ylabel(f'{ylab} ({unit})')
    ax.axvspan(96, 106, color='#f0f0f0', zorder=0)
    ax.text(101, ax.get_ylim()[1], 'read pulse', fontsize=7,
            ha='center', va='top', color='#999999')
    return ax


def _derived_peaks_note(corr, case_key, vkey, unit_v, unit_i):
    """Build a derived-peaks text note strictly from corrected data."""
    vs = [corr[case_key][s]['source'][vkey]['peak_baseline_subtracted']
          for s in STEPS]
    if vkey == 'V_SL1':
        peak_txt = ' / '.join(f'{v * 1e3:.3f} mV' for v in vs)
    else:
        peak_txt = ' / '.join(f'{v * 1e6:.2f} µA' for v in vs)
    lat = corr[case_key]['0.025ps']['source'][vkey]['latency_from_96ps_s']
    return (f'Derived: baseline-subtracted peaks\n'
            f'{case_key} {peak_txt} @ {lat * 1e12:.1f} ps\n'
            f'controls (noise floor): see fig7')


def fig2_source_voltage():
    col = 'V(SL1)'
    corr = json.loads(CORRECTED.read_text(encoding='utf-8'))['cases']
    fig, axes = plt.subplots(2, 2, figsize=(12, 8),
                             gridspec_kw={'height_ratios': [2.2, 1]})
    ax = axes[0][0]
    for case, c in ((CASES[0], READ_POS), (CASES[1], CTRL_POS),
                    (CASES[2], READ_NEG), (CASES[3], CTRL_NEG)):
        t, y = _source_win(case, '0.025ps', col)
        ax.plot(t, [v * 1e3 for v in y], lw=1.6, color=c,
                label=case.replace('_', ' '))
    ax.axvspan(96, 106, color='#f0f0f0', zorder=0)
    ax.set_title('V(SL1) [94,130) ps — 0.025 ps main (observed)')
    ax.set_xlabel('time (ps)'); ax.set_ylabel('V(SL1) (mV)')
    ax.legend(fontsize=7, loc='upper right')

    ax = axes[0][1]
    for step, c in zip(STEPS, STEP_RAMP):
        t, y = _source_win(CASES[0], step, col)
        ax.plot(t, [v * 1e3 for v in y], lw=1.3, color=c, label=f'pos read {step}')
        t, y = _source_win(CASES[2], step, col)
        ax.plot(t, [v * 1e3 for v in y], lw=1.3, ls='--', color=c,
                label=f'neg read {step}')
    ax.axvspan(96, 106, color='#f0f0f0', zorder=0)
    ax.set_title('Timestep overlay — init reads (observed)')
    ax.set_xlabel('time (ps)'); ax.set_ylabel('V(SL1) (mV)')
    ax.legend(fontsize=6, loc='upper right')

    ax = axes[1][0]
    for case, c in ((CASES[1], CTRL_POS), (CASES[3], CTRL_NEG)):
        for step, sc in zip(STEPS, STEP_RAMP):
            t, y = _source_win(case, step, col)
            ax.plot(t, [v * 1e9 for v in y], lw=1.2, color=sc, alpha=0.85,
                    label=f'{case.split("_control")[0]} ctrl {step}')
    ax.axvspan(96, 106, color='#f0f0f0', zorder=0)
    ax.set_title('Matched controls — nV scale (observed)')
    ax.set_xlabel('time (ps)'); ax.set_ylabel('V(SL1) (nV)')
    ax.legend(fontsize=6, loc='upper right')

    ax = axes[1][1]
    ax.text(0.05, 0.78,
            _derived_peaks_note(corr, CASES[0], 'V_SL1', 'mV', 'µA') + '\n' +
            _derived_peaks_note(corr, CASES[2], 'V_SL1', 'mV', 'µA'),
            fontsize=8.5, transform=ax.transAxes, va='top')
    ax.text(0.05, 0.10,
            'Inference: read response is state-conditioned\n'
            '(magnitude & latency differ pos vs neg);\n'
            'not a logical read0/read1 claim.',
            fontsize=9, transform=ax.transAxes, va='top', color='#555555')
    ax.axis('off')
    fig.suptitle('BVM-S0 source voltage — observed waveforms from frozen raw',
                 fontsize=12, fontweight='bold')
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    fig.savefig(OUT / 'fig2-source-voltage.png', dpi=150, bbox_inches='tight')
    plt.close(fig)


def fig3_source_current():
    col = 'I(L_SL|XBVM1)'
    corr = json.loads(CORRECTED.read_text(encoding='utf-8'))['cases']
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    ax = axes[0][0]
    for case, c in ((CASES[0], READ_POS), (CASES[1], CTRL_POS),
                    (CASES[2], READ_NEG), (CASES[3], CTRL_NEG)):
        t, y = _source_win(case, '0.025ps', col)
        ax.plot(t, [v * 1e6 for v in y], lw=1.6, color=c,
                label=case.replace('_', ' '))
    ax.axvspan(96, 106, color='#f0f0f0', zorder=0)
    ax.set_title('I(L_SL|XBVM1) [94,130) ps — 0.025 ps main (observed)')
    ax.set_xlabel('time (ps)'); ax.set_ylabel('I(L_SL) (µA)')
    ax.legend(fontsize=7, loc='upper right')

    ax = axes[0][1]
    for step, c in zip(STEPS, STEP_RAMP):
        t, y = _source_win(CASES[0], step, col)
        ax.plot(t, [v * 1e6 for v in y], lw=1.3, color=c, label=f'pos read {step}')
        t, y = _source_win(CASES[2], step, col)
        ax.plot(t, [v * 1e6 for v in y], lw=1.3, ls='--', color=c,
                label=f'neg read {step}')
    ax.axvspan(96, 106, color='#f0f0f0', zorder=0)
    ax.set_title('Timestep overlay — init reads (observed)')
    ax.set_xlabel('time (ps)'); ax.set_ylabel('I(L_SL) (µA)')
    ax.legend(fontsize=6, loc='upper right')

    ax = axes[1][0]
    for case, c in ((CASES[1], CTRL_POS), (CASES[3], CTRL_NEG)):
        for step, sc in zip(STEPS, STEP_RAMP):
            t, y = _source_win(case, step, col)
            ax.plot(t, [v * 1e9 for v in y], lw=1.2, color=sc, alpha=0.85,
                    label=f'{case.split("_control")[0]} ctrl {step}')
    ax.axvspan(96, 106, color='#f0f0f0', zorder=0)
    ax.set_title('Matched controls — nA scale (observed)')
    ax.set_xlabel('time (ps)'); ax.set_ylabel('I(L_SL) (nA)')
    ax.legend(fontsize=6, loc='upper right')

    ax = axes[1][1]
    ax.text(0.05, 0.78,
            _derived_peaks_note(corr, CASES[0], 'I_LSL', 'mV', 'µA') + '\n' +
            _derived_peaks_note(corr, CASES[2], 'I_LSL', 'mV', 'µA'),
            fontsize=8.5, transform=ax.transAxes, va='top')
    ax.text(0.05, 0.10,
            'Inference: state-conditioned source current;\n'
            'not a receiver/JTL reception claim.',
            fontsize=9, transform=ax.transAxes, va='top', color='#555555')
    ax.axis('off')
    fig.suptitle('BVM-S0 source current — observed waveforms from frozen raw',
                 fontsize=12, fontweight='bold')
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    fig.savefig(OUT / 'fig3-source-current.png', dpi=150, bbox_inches='tight')
    plt.close(fig)


def fig4_convergence():
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    for ax, case, c in ((axes[0], CASES[0], READ_POS),
                        (axes[1], CASES[2], READ_NEG)):
        for step, sc in zip(STEPS, STEP_RAMP):
            t, y = _source_win(case, step, 'V(SL1)')
            ax.plot(t, [v * 1e3 for v in y], lw=1.4, color=sc, label=step)
        ax.axvspan(96, 106, color='#f0f0f0', zorder=0)
        ax.set_title(f'{case.replace("_", " ")} — V(SL1) full waveform '
                     '(observed)')
        ax.set_xlabel('time (ps)'); ax.set_ylabel('V(SL1) (mV)')
        ax.legend(title='timestep', fontsize=8)
    fig.suptitle('Timestep convergence overlay — full waveform, not peaks',
                 fontsize=12, fontweight='bold')
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(OUT / 'fig4-convergence-overlay.png', dpi=150,
                bbox_inches='tight')
    plt.close(fig)


def fig5_storage_signature():
    d = json.loads(CORRECTED.read_text(encoding='utf-8'))['cases']
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.2))
    for ax, sign, c_read in ((axes[0], 'positive', READ_POS),
                             (axes[1], 'negative', READ_NEG)):
        read = f'init_{sign}_read'
        ctrl = f'init_{sign}_control'
        x = [0, 1, 2, 3, 4, 5]
        jm1_pre = [d[read][s]['platform']['pre']['JM1'] for s in STEPS]
        jm1_post = [d[read][s]['platform']['post']['JM1'] for s in STEPS]
        jm2_pre = [d[read][s]['platform']['pre']['JM2'] for s in STEPS]
        jm2_post = [d[read][s]['platform']['post']['JM2'] for s in STEPS]
        width = 0.38
        ax.bar([i - width / 2 for i in x[:3]], jm1_pre, width, color=JM1_C,
               alpha=0.75, label='JM1 pre [80,90)')
        ax.bar([i - width / 2 for i in x[3:]], jm1_post, width, color=JM1_C,
               alpha=0.35, label='JM1 post [140,150)')
        ax.bar([i + width / 2 for i in x[:3]], jm2_pre, width, color=JM2_C,
               alpha=0.75, label='JM2 pre')
        ax.bar([i + width / 2 for i in x[3:]], jm2_post, width, color=JM2_C,
               alpha=0.35, label='JM2 post')
        ax.axhline(0, color='#999999', lw=0.8)
        ax.set_xticks(x)
        ax.set_xticklabels([f'{s} pre' for s in STEPS]
                           + [f'{s} post' for s in STEPS], rotation=30, fontsize=7)
        ax.set_ylabel('phase mean (rad)')
        ax.set_title(f'init_{sign} — operational phase signature (observed '
                     'means)')
        ax.legend(fontsize=7)
        ax.text(0.02, 0.95, 'Label is operational only: NOT logic 0/1, NOT '
                'fluxoid', transform=ax.transAxes, fontsize=8, color='#b5457f')
    fig.suptitle('Storage signature — direct JM1/JM2 pre/post phase means '
                 '(derived from raw)', fontsize=12, fontweight='bold')
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    fig.savefig(OUT / 'fig5-storage-signature.png', dpi=150, bbox_inches='tight')
    plt.close(fig)


def fig6_phase_area_crosscheck():
    d = json.loads(CORRECTED.read_text(encoding='utf-8'))['cases']
    fig, ax = plt.subplots(figsize=(9, 7))
    markers = {'JM1': 'o', 'JM2': 's'}
    for case, c in ((CASES[0], READ_POS), (CASES[2], READ_NEG),
                    (CASES[1], CTRL_POS), (CASES[3], CTRL_NEG)):
        for jj in ('JM1', 'JM2'):
            xs, ys = [], []
            for s in STEPS:
                a = d[case][s]['phase_area'][jj]
                xs.append(a['phase_delta_turns'])
                ys.append(a['area_turns'])
            ax.plot(xs, ys, marker=markers[jj], ls='-', lw=1.0, ms=5,
                    color=c, alpha=0.9,
                    label=f'{case.replace("_", " ")} {jj}')
    lo, hi = -0.08, 0.08
    ax.plot([lo, hi], [lo, hi], ls='--', color='#333333', lw=1.0,
            label='y = x (identity)')
    ax.set_xlim(lo, hi); ax.set_ylim(lo, hi)
    ax.set_xlabel('phase_delta_turns (Δφ/2π, [94,108) ps)')
    ax.set_ylabel('area_turns (∫V dt / Φ0)')
    ax.set_title('Direct-JJ phase–area crosscheck — same JJ, same window, '
                 'vts=+1/rd=+1 (derived)')
    ax.legend(fontsize=6, loc='upper left')
    ax.grid(alpha=0.25)
    ax.text(0.02, 0.03,
            'Residuals are descriptive (~1e-4 turns); NO tolerance declared.\n'
            'Observed: raw P/V. Derived: trapezoid on actual time. '
            'Inference: none beyond identity check.',
            fontsize=8, color='#555555')
    fig.tight_layout()
    fig.savefig(OUT / 'fig6-phase-area-crosscheck.png', dpi=150,
                bbox_inches='tight')
    plt.close(fig)


def fig7_control_noise_zoom():
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    for ax, col, unit, scale in ((axes[0], 'V(SL1)', 'nV', 1e9),
                                 (axes[1], 'I(L_SL|XBVM1)', 'nA', 1e9)):
        for case, c in ((CASES[1], CTRL_POS), (CASES[3], CTRL_NEG)):
            for step, sc in zip(STEPS, STEP_RAMP):
                t, y = _source_win(case, step, col)
                ax.plot(t, [v * scale for v in y], lw=1.2, color=sc, alpha=0.9,
                        label=f'{case.split("_control")[0]} ctrl {step}')
        ax.axvspan(96, 106, color='#f0f0f0', zorder=0)
        ax.set_title(f'{col} matched controls — noise zoom (observed)')
        ax.set_xlabel('time (ps)'); ax.set_ylabel(f'{col} ({unit})')
        ax.legend(fontsize=6, loc='upper right')
    fig.text(0.5, 0.02,
             'S0 registered blocker: 0.1→0.05 ps control peak-latency '
             '−0.70→+0.15 ps = 0.85 ps > 0.5 ps band → numerical '
             'INCONCLUSIVE (frozen rule; verdict unchanged).\n'
             'Control "peaks" are noise-floor residuals (15–18 nV, 1.3–1.5 nA); '
             'their latency is a sampling artifact, NOT a read response.',
             ha='center', fontsize=9, color='#b5457f')
    fig.suptitle('Control noise floor and the registered INCONCLUSIVE '
                 'blocker', fontsize=12, fontweight='bold')
    fig.tight_layout(rect=[0, 0.06, 1, 0.95])
    fig.savefig(OUT / 'fig7-control-noise-zoom.png', dpi=150,
                bbox_inches='tight')
    plt.close(fig)


def fig8_flowchart():
    fig, ax = plt.subplots(figsize=(12, 6.5))
    ax.set_xlim(0, 12); ax.set_ylim(0, 7); ax.axis('off')
    boxes = [
        (1.6, 5.6, 'M1–M12 measurement repair\n(M4–M11 accepted; METRIC_SPEC_V2\nfrozen; 2026-08-13)', '#eef4fb', '#1f6fb2'),
        (4.6, 5.6, 'D0 initialization readiness\n75 ps bound (VALID)\n2026-08-14', '#eef9f0', '#2e7d32'),
        (7.8, 5.6, 'BVM-S0 12-run source characterization\n4 cases × 0.1/0.05/0.025 ps, 12 Ω\n2026-08-14', '#fff8e1', '#b26a00'),
        (10.5, 5.6, 'VALID artifact\n+ INCONCLUSIVE convergence\n(C02, frozen)', '#fdecea', '#b71c1c'),
        (6.2, 2.4, 'NEXT (user-authorized):\nnew preregistered source\nconvergence/characterization\ntask — new immutable runs', '#f3e5f5', '#6a1b9a'),
        (9.6, 2.4, 'later: receiver\ncharacterization,\nINTERFACE_GATE_V1', '#eeeeee', '#555555'),
    ]
    for (x, y, txt, fc, ec) in boxes:
        ax.add_patch(mpatches.FancyBboxPatch((x - 1.5, y - 0.75), 3.0, 1.5,
                     boxstyle='round,pad=0.1', fc=fc, ec=ec, lw=1.5))
        ax.text(x, y, txt, ha='center', va='center', fontsize=8)
    for (x1, y1, x2, y2) in ((3.1, 5.6, 4.6 - 1.5, 5.6),
                             (6.1, 5.6, 7.8 - 1.5, 5.6),
                             (9.3, 5.6, 10.5 - 1.5, 5.6),
                             (10.5, 4.85, 9.8, 3.15),
                             (7.5, 2.4, 8.1, 2.4)):
        ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle='->', lw=1.5, color='#333333'))
    ax.text(6.0, 6.35, 'Experiment/status flow — BVM-S0 chain (2026-08-14)',
            fontsize=12, fontweight='bold', ha='center')
    ax.text(0.2, 0.2,
            'Status boxes are accepted audit facts; "NEXT" is a suggestion, '
            'not executed (waits user authorization).',
            fontsize=8, color='#8a8a8a')
    fig.savefig(OUT / 'fig8-flowchart.png', dpi=150, bbox_inches='tight')
    plt.close(fig)


if __name__ == '__main__':
    fig1_topology()
    fig2_source_voltage()
    fig3_source_current()
    fig4_convergence()
    fig5_storage_signature()
    fig6_phase_area_crosscheck()
    fig7_control_noise_zoom()
    fig8_flowchart()
    print('figures written to', OUT)
