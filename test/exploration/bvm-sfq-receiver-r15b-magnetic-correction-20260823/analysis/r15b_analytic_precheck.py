#!/usr/bin/env python3
"""R15-B analytic topology precheck; deliberately does not invoke JoSIM."""

from __future__ import annotations

import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PHI0 = 2.067833848e-15


def eig2(a: float, b: float, c: float) -> list[float]:
    mid = 0.5 * (a + c)
    half = 0.5 * (a - c)
    d = math.sqrt(half * half + b * b)
    return [mid - d, mid + d]


def main() -> None:
    # R15-A accepted source evidence, used only as an input-scale estimate.
    read1_peak_uA = 54.19963
    read0_abs_peak_uA = 22.16104
    l_tx_pH = 0.20
    l_s_pH = 50.0
    k_in = -0.80
    m_in_pH = abs(k_in) * math.sqrt(l_tx_pH * l_s_pH)
    m_over_ls = m_in_pH / l_s_pH
    j_set_bias_uA = 5.6
    j_set_ic_uA = 8.0

    # A: a valid common-core alternative requires a strong direct Q-CTL term.
    a = b = 0.90
    k_qo_a = 0.80
    a_det = 1.0 + 2.0 * a * b * k_qo_a - a * a - b * b - k_qo_a * k_qo_a
    a_norm_eigs = [0.06583359, 0.20, 2.73416641]
    a_m_qf_pH = a * math.sqrt(4.0 * 20.0)
    a_m_fo_pH = b * math.sqrt(20.0 * 4.0)
    a_m_qo_pH = k_qo_a * math.sqrt(4.0 * 4.0)
    a_matrix_pH = [
        [4.0, a_m_qf_pH, a_m_qo_pH],
        [a_m_qf_pH, 20.0, a_m_fo_pH],
        [a_m_qo_pH, a_m_fo_pH, 4.0],
    ]
    # The actual eigenvalues are included from the closed-form symmetric
    # matrix calculation used in the report.
    a_actual_eigs_pH = [0.54013783, 0.8, 26.65986217]

    # B: two independent cores, each winding remains 20 pH so the local
    # mutual numerator is unchanged; scaling RF to 20 ohm preserves L/R=2 ps
    # for the 40 pH series transfer loop.
    l_q = 4.0
    l_fq = l_fo = 20.0
    l_ctl = 4.0
    r_f = 20.0
    k_qfq = 0.90
    k_foctl = -0.90
    m_qfq_pH = k_qfq * math.sqrt(l_q * l_fq)
    m_foctl_pH = abs(k_foctl) * math.sqrt(l_fo * l_ctl)
    b_source_matrix_pH = [
        [0.20, -m_in_pH],
        [-m_in_pH, 50.0],
    ]
    b_q_core_pH = [[l_q, m_qfq_pH], [m_qfq_pH, l_fq]]
    b_o_core_pH = [[l_fo, -m_foctl_pH], [-m_foctl_pH, l_ctl]]
    b_source_det = 0.20 * 50.0 - m_in_pH * m_in_pH
    b_core_det = l_q * l_fq - m_qfq_pH * m_qfq_pH
    b_full_det = b_source_det * 5.0 * b_core_det * b_core_det * 2.0
    b_actual_eigs_pH = [
        *eig2(0.20, -m_in_pH, 50.0),
        5.0,
        *eig2(l_q, m_qfq_pH, l_fq),
        *eig2(l_fo, -m_foctl_pH, l_ctl),
        2.0,
    ]
    b_actual_eigs_pH.sort()

    # The series FQ-FO loop is R_F + j omega (LFQ+LFO).  This is a first-order
    # reflected-load estimate; J_Q/J_OUT/DCSFQ nonlinear impedances are not
    # replaced by these linear proxies.
    reflected = {}
    for t_ps in (2.0, 10.0, 20.0):
        omega = 2.0 * math.pi / (t_ps * 1e-12)
        z_loop = complex(r_f, omega * (l_fq + l_fo) * 1e-12)
        z_q = (omega * m_qfq_pH * 1e-12) ** 2 / z_loop
        reflected[str(int(t_ps))] = {
            "Z_loop_ohm": [z_loop.real, z_loop.imag],
            "Z_Q_reflected_ohm": [z_q.real, z_q.imag],
            "Z_Q_reflected_abs_ohm": abs(z_q),
        }

    output_bracket = {}
    i_out_uA = 275.0
    r_src = 0.75
    l_inj_pH = 2.0
    for t_ps in (10.0, 20.0):
        omega = 2.0 * math.pi / (t_ps * 1e-12)
        x_inj = omega * l_inj_pH * 1e-12
        candidates = []
        for r_ground in (1.92, 3.0):
            for l_dcs_pH in (1.672, 1.672 + 3.901):
                x_dcs = omega * l_dcs_pH * 1e-12
                z_series = math.hypot(r_src, x_inj + x_dcs)
                i_uA = i_out_uA * r_ground / (r_ground + z_series)
                # i_uA [microamp] times x_dcs [ohm] is directly microvolt.
                candidates.append((i_uA, i_uA * x_dcs, r_ground, l_dcs_pH))
        output_bracket[str(int(t_ps))] = {
            "I_DCS_min_uA": min(x[0] for x in candidates),
            "I_DCS_max_uA": max(x[0] for x in candidates),
            "V_DCS_min_uV": min(x[1] for x in candidates),
            "V_DCS_max_uV": max(x[1] for x in candidates),
            "source_impedance_R_ohm": r_src,
            "source_impedance_X_LINJ_ohm": x_inj,
        }

    payload = {
        "experiment": "R15-B",
        "verdict": "R15B_SINGLE_POINT_WORTH_TESTING",
        "josim_invoked": False,
        "selected_topology": "split_winding_two_core_series_damped_transfer",
        "selected_point": {
            "L_FQ_pH": l_fq,
            "L_FO_pH": l_fo,
            "R_F_ohm": r_f,
            "K_QFQ": k_qfq,
            "K_FOCTL": k_foctl,
            "K_QCTL": 0.0,
            "K_FQFO": 0.0,
            "series_loop_tau_ps": (l_fq + l_fo) / r_f,
        },
        "option_A_common_core": {
            "K_QF": a,
            "K_FO": b,
            "selected_comparison_K_QO": k_qo_a,
            "positive_definite_range_K_QO": [0.62, 1.0],
            "normalized_determinant": a_det,
            "normalized_eigenvalues": a_norm_eigs,
            "matrix_pH": a_matrix_pH,
            "actual_eigenvalues_pH": a_actual_eigs_pH,
            "direct_QO_mutual_pH": a_m_qo_pH,
        },
        "option_B_matrix": {
            "source_block_order": ["L_TX", "L_S"],
            "source_block_pH": b_source_matrix_pH,
            "Q_core_order": ["L_Q", "L_FQ"],
            "Q_core_pH": b_q_core_pH,
            "output_core_order": ["L_FO", "L_CTL"],
            "output_core_pH": b_o_core_pH,
            "full_order": ["L_TX", "L_S", "L_RET", "L_Q", "L_FQ", "L_FO", "L_CTL", "L_INJ"],
            "full_determinant_pH8": b_full_det,
            "actual_eigenvalues_pH": b_actual_eigs_pH,
            "normalized_determinant": 0.36 * 0.19 * 0.19,
            "all_cross_core_mutuals_zero": True,
        },
        "jset_discrimination": {
            "M_IN_pH": m_in_pH,
            "M_over_LS": m_over_ls,
            "read1_increment_uA": m_over_ls * read1_peak_uA,
            "read0_worst_increment_uA": m_over_ls * read0_abs_peak_uA,
            "read1_total_uA": j_set_bias_uA + m_over_ls * read1_peak_uA,
            "read0_total_uA": j_set_bias_uA + m_over_ls * read0_abs_peak_uA,
            "read1_read0_margin_uA": m_over_ls * (read1_peak_uA - read0_abs_peak_uA),
            "read1_flux_abs_turns": m_in_pH * 1e-12 * read1_peak_uA * 1e-6 / PHI0,
            "read0_flux_abs_turns": m_in_pH * 1e-12 * read0_abs_peak_uA * 1e-6 / PHI0,
            "Ic_uA": j_set_ic_uA,
        },
        "reflected_loading": reflected,
        "active_output_bracket": output_bracket,
        "empirical_references_uA": {
            "R1a_passive": 5.564,
            "R12_68p4_no_event": 68.4,
            "R13_110p2_subthreshold": 110.2,
            "R12_300_one_event_reference": 300.0,
        },
        "interpretation": {
            "observed": "R15-A nominal point had no valid raw run; only its Gate-3 source-scale evidence is reused.",
            "derived": "Both corrected matrices are positive definite; selected split topology has zero direct Q-CTL mutual and preserves the 2 ps bridge L/R scale.",
            "inference": "Split-winding is preferable because common-core completion requires a strong direct Q-CTL mutual that changes refractory/load-line behavior.",
            "unknown": "Nonlinear refractory, polarity realization, J_OUT startup, DCSFQ response, source guards, and step convergence require the future four-case run.",
        },
    }
    out = ROOT / "analysis/r15b-analytic-metrics.json"
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
