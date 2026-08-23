#!/usr/bin/env python3
"""R15-A Gate 0-4 analytic/pre-run calculations; no JoSIM invocation."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[2]
PHI0 = 2.067833848e-15
MODEL = ROOT / "inputs/jjmit.cir"
R1A_ROOT = REPO / "test/exploration/bvm-sfq-receiver-r1a-transfer-20260819/raw/l020-k080"

AREA_VALUES = {"J_SET": 0.08, "J_Q": 0.50, "B_DET": 0.50, "J_OUT": 3.0}
L_BASE_PH = 0.20
L_S_PH = 50.0
L_RET_PH = 5.0
L_Q_PH = 4.0
L_LOOP_PH = L_S_PH + L_RET_PH + L_Q_PH
K_IN = -0.80
K_QF = 0.90
K_FO = 0.90
I_SET_UA = 5.6
I_OUT_UA = 275.0
R_Q_OHM = 2.0
R_SH_OUT_OHM = 3.0
R_SRC_OHM = 0.75
L_INJ_PH = 2.0
WINDOW = (94.0, 130.0)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def load_primary(case: str) -> list[tuple[float, float]]:
    path = R1A_ROOT / case / "run-01.csv"
    with path.open(newline="") as f:
        rows = list(csv.DictReader(f))
    return [
        (float(row["time"]) * 1e12, float(row["I(L_TX|XTRIG)"]) * 1e6)
        for row in rows
        if WINDOW[0] <= float(row["time"]) * 1e12 < WINDOW[1]
    ]


def parse_model() -> dict[str, float]:
    text = MODEL.read_text()
    match = re.search(
        r"\.model\s+jjmit\s+jj\([^)]*?CAP\s*=\s*([0-9.]+)p,\s*"
        r"r0\s*=\s*([0-9.]+),\s*rn\s*=\s*([0-9.]+),\s*"
        r"icrit\s*=\s*([0-9.]+)m",
        text,
        re.IGNORECASE,
    )
    if not match:
        raise ValueError("could not parse jjmit model constants")
    cap_pf, r0, rn, icrit_ma = map(float, match.groups())
    return {
        "Ic0_A": icrit_ma * 1e-3,
        "C0_F": cap_pf * 1e-12,
        "RN0_ohm": rn,
        "R0_ohm": r0,
    }


def jj_params(area: float, base: dict[str, float]) -> dict[str, float]:
    ic = base["Ic0_A"] * area
    cap = base["C0_F"] * area
    rn = base["RN0_ohm"] / area
    r0 = base["R0_ohm"] / area
    beta_intrinsic = 2.0 * math.pi * ic * rn * rn * cap / PHI0
    return {
        "area": area,
        "Ic_A": ic,
        "C_F": cap,
        "RN_ohm": rn,
        "R0_ohm": r0,
        "beta_c_intrinsic": beta_intrinsic,
    }


def extrema(values: list[tuple[float, float]]) -> dict[str, float]:
    lo = min(values, key=lambda x: x[1])
    hi = max(values, key=lambda x: x[1])
    return {
        "min_uA": lo[1],
        "min_time_ps": lo[0],
        "max_uA": hi[1],
        "max_time_ps": hi[0],
        "abs_peak_uA": max(abs(lo[1]), abs(hi[1])),
    }


def main() -> None:
    model_text = MODEL.read_text()
    base = parse_model()

    source = {case: extrema(load_primary(case)) for case in ("read1", "read0")}
    jj = {name: jj_params(area, base) for name, area in AREA_VALUES.items()}
    r_out_eff = 1.0 / (1.0 / jj["J_OUT"]["RN_ohm"] + 1.0 / R_SH_OUT_OHM)
    beta_out_shunted = (
        2.0 * math.pi * jj["J_OUT"]["Ic_A"] * jj["J_OUT"]["C_F"] * r_out_eff**2 / PHI0
    )

    m_ph = abs(K_IN) * math.sqrt(L_BASE_PH * L_S_PH)
    coupling_ratio = m_ph / L_S_PH
    read1 = source["read1"]
    read0 = source["read0"]
    read1_favorable = I_SET_UA + coupling_ratio * read1["max_uA"]
    read0_worst = I_SET_UA + coupling_ratio * abs(read0["min_uA"])
    read1_flux = m_ph * 1e-12 * read1["abs_peak_uA"] * 1e-6 / PHI0
    read0_flux = m_ph * 1e-12 * read0["abs_peak_uA"] * 1e-6 / PHI0

    def zmag(t_ps: float, l_ph: float) -> float:
        return 2.0 * math.pi * l_ph * 1e-12 / (t_ps * 1e-12)

    output_brackets = {}
    for t_ps in (10.0, 20.0):
        x_inj = zmag(t_ps, L_INJ_PH)
        x_d_min = zmag(t_ps, 1.672)
        x_d_max = zmag(t_ps, 1.672 + 3.901)
        z_min = math.hypot(R_SRC_OHM, x_inj + x_d_min)
        z_max = math.hypot(R_SRC_OHM, x_inj + x_d_max)
        i_min = I_OUT_UA * R_SH_OUT_OHM / (R_SH_OUT_OHM + z_max)
        i_max = I_OUT_UA * R_SH_OUT_OHM / (R_SH_OUT_OHM + z_min)
        output_brackets[str(int(t_ps))] = {
            "duration_ps": t_ps,
            "DCSFQ_input_current_min_uA": i_min,
            "DCSFQ_input_current_max_uA": i_max,
            "DCSFQ_input_voltage_min_uV": i_min * 1e-6 * x_d_min * 1e6,
            "DCSFQ_input_voltage_max_uV": i_max * 1e-6 * x_d_max * 1e6,
            "source_impedance_R_ohm": R_SRC_OHM,
            "source_impedance_X_LINJ_ohm": x_inj,
        }

    # The three coupled inductors form a single constitutive magnetic block.
    # There is no L_Q--L_CTL mutual in the nominal netlist, so the normalized
    # block is [[1,k_qf,0],[k_qf,1,k_fo],[0,k_fo,1]].  A passive inductance
    # matrix must be positive definite; this check is prior to any JoSIM run.
    coupling_normalized = [
        [1.0, K_QF, 0.0],
        [K_QF, 1.0, K_FO],
        [0.0, K_FO, 1.0],
    ]
    mutual_qf_ph = K_QF * math.sqrt(L_Q_PH * 20.0)
    mutual_fo_ph = K_FO * math.sqrt(20.0 * 4.0)
    coupling_det = 1.0 - K_QF * K_QF - K_FO * K_FO
    coupling_min_eigenvalue = 1.0 - math.sqrt(K_QF * K_QF + K_FO * K_FO)
    coupling_matrix_ph = [
        [L_Q_PH, mutual_qf_ph, 0.0],
        [mutual_qf_ph, 20.0, mutual_fo_ph],
        [0.0, mutual_fo_ph, 4.0],
    ]
    coupling_matrix_det_ph3 = (
        L_Q_PH * 20.0 * 4.0
        - mutual_qf_ph * mutual_qf_ph * 4.0
        - mutual_fo_ph * mutual_fo_ph * L_Q_PH
    )
    gate0_matrix_valid = coupling_det > 0.0 and coupling_min_eigenvalue > 0.0
    for values in jj.values():
        values["tau_RN_C_ps"] = values["RN_ohm"] * values["C_F"] * 1e12
        values["tau_R0_C_ps"] = values["R0_ohm"] * values["C_F"] * 1e12

    payload = {
        "experiment": "R15-A",
        "type": "analytic_precheck_no_josim",
        "model_path": str(MODEL.relative_to(REPO)),
        "model_sha256": sha256(MODEL),
        "jjmit_base_constants": base,
        "windows_ps": {"activity": list(WINDOW)},
        "jjmit_parameters": jj,
        "external_damping": {
            "J_OUT_R_shunt_ohm": R_SH_OUT_OHM,
            "J_OUT_R_eff_ohm": r_out_eff,
            "J_OUT_beta_c_with_external_shunt": beta_out_shunted,
            "loop_tau_Q_ps": (L_LOOP_PH * 1e-12 / R_Q_OHM) * 1e12,
            "bridge_tau_F_ps": (20e-12 / 10.0) * 1e12,
        },
        "gate0_topology": {
            "status": "FAIL_INVALID_MUTUAL_INDUCTANCE_MATRIX",
            "node_closure_status": "PASS_ANALYTIC",
            "J_SET": "N_S2 to N_QMODE",
            "J_Q": "N_QJ to ground",
            "R_Q": "N_QMODE to ground, parallel to L_Q->J_Q series branch only at N_QMODE",
            "L_Q": "N_QMODE to N_QJ",
            "L_F_R_F": "both N_F to ground, L_F magnetically coupled to L_Q and L_CTL",
            "J_OUT": "N_OUTJ to ground, with R_OUT_SH parallel; N_DRV reaches N_OUTJ through L_CTL",
            "output_KCL": "I_OUT enters N_DRV and divides between L_CTL/J_OUT path and R_SRC/L_INJ/DCSFQ.a path",
            "DCSFQ_return": "DCSFQ.a -> L1 -> node1 -> L2 -> ground plus AFQ R_SRC/L_INJ path",
            "mutual_polarity": "K_IN=-.80, K_QF=+.90, K_FO=+.90",
            "floating_nodes": [],
            "magnetic_block_order": ["L_Q", "L_F", "L_CTL"],
            "normalized_mutual_matrix": coupling_normalized,
            "mutual_matrix_pH": coupling_matrix_ph,
            "mutual_matrix_determinant_pH3": coupling_matrix_det_ph3,
            "normalized_determinant": coupling_det,
            "minimum_normalized_eigenvalue": coupling_min_eigenvalue,
            "positive_definite": gate0_matrix_valid,
            "failure_reason": (
                "K_QF^2 + K_FO^2 = 1.62 > 1; the nominal three-coil "
                "inductance matrix has a negative eigenvalue. The netlist "
                "has no L_Q-L_CTL mutual to repair this block."
            ),
        },
        "gate1_actual_jjmit": {
            "status": "PASS_MODEL_RECONSTRUCTION",
            "base_constants": base,
            "area_scaled": jj,
            "area_invariant_intrinsic_beta_c": next(iter(jj.values()))["beta_c_intrinsic"],
            "area_invariant_RN_times_C_ps": next(iter(jj.values()))["tau_RN_C_ps"],
            "area_invariant_R0_times_C_ps": next(iter(jj.values()))["tau_R0_C_ps"],
            "loop_L_over_RQ_ps": (L_LOOP_PH * 1e-12 / R_Q_OHM) * 1e12,
        },
        "gate2_no_input_analytic": {
            "status": "NOT_RUN_GATE0_FAILED",
            "bias_over_Ic": {
                "B_DET": 15.0e-6 / jj["B_DET"]["Ic_A"],
                "J_SET": I_SET_UA * 1e-6 / jj["J_SET"]["Ic_A"],
                "J_Q": I_SET_UA * 1e-6 / jj["J_Q"]["Ic_A"],
                "J_OUT": I_OUT_UA * 1e-6 / jj["J_OUT"]["Ic_A"],
                "DCSFQ_B1_B2_bias_over_Ic": 100.0 / 80.0,
                "DCSFQ_B3_bias_over_Ic": 175.0 / 250.0,
            },
            "risk": "J_OUT is near critical; logical1-read0-control is the first no-input/startup hard check.",
        },
        "gate3_discrimination": {
            "M_pH": m_ph,
            "M_over_LS": coupling_ratio,
            "read1_primary_extrema_uA": read1,
            "read0_primary_extrema_uA": read0,
            "read1_favorable_JSET_current_uA": read1_favorable,
            "read0_worst_abs_JSET_current_uA": read0_worst,
            "read1_read0_margin_uA": read1_favorable - read0_worst,
            "read1_abs_flux_turns": read1_flux,
            "read0_abs_flux_turns": read0_flux,
            "polarity": "K_IN=-.80 declares the positive read1 primary lobe as favorable; actual branch sign is an execution probe, not an event claim.",
            "reflected_impedance_ohm_at_2ps": 0.34,
            "reflected_impedance_ohm_at_10ps": 0.068,
        },
        "gate4_active_output_scale": {
            "status": "PASS_SCALE_ONLY",
            "R1A_passive_uA": 5.564,
            "R12_68p4_no_event_uA": 68.4,
            "R13_actual_subthreshold_uA": 110.2,
            "R12_300_one_event_reference_uA": 300.0,
            "brackets": output_brackets,
            "interpretation": "Independent I_OUT and nonlinear current steering give >100uA first-order loaded bracket; duration and DCSFQ nonlinear response remain unknown.",
        },
        "decision": "PRECHECK_NO_GO",
        "execution": {
            "josim_started_for_scientific_cases": False,
            "reason": "Gate 0 failed before a valid constitutive magnetic network was established.",
            "matched_cases": [],
        },
    }
    out = ROOT / "analysis/r15a-precheck-metrics.json"
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
