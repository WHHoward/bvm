#!/usr/bin/env python3
"""S2-001 canonical input generator — immutable 16-netlist package.

Frozen per JH-20260817-BVM-S2-001 request + design/preregistration.yaml:
- closure: active circuits/bvm/bvm_cell.cir + circuits/models/jjmit.cir copied
  byte-identical into inputs/; XBVM1 WL1 BL1 SE1 SL1 BVM; internal R_SL fixed
  (inside bvm_cell); only variable is R_LD SL1 0 <1|12|25|50>.
- init PWL: 0 at 0-9 ps, +/-100 uA at 10-20 ps, 0 at 21 ps (WL+BL).
- read PWL: WL+SE 0 at 95 ps, +100 uA at 96-105 ps, 0 at 106 ps.  Matched
  control: identical source names and knot times; only the 96-105 ps WL/SE
  amplitudes are 0 uA.
- .tran 0.0125p 170p (single registered working timestep).
- probes (preregistration.yaml): V(SL1) SL1->0; I(L_SL|XBVM1) N8->SL1;
  I(I_WL1) 0->WL1; I(I_BL1) 0->BL1; I(I_SE1) 0->SE1;
  P/V(B_JM1|XBVM1) N1->n_jm1o vts=+1 rd=+1;
  P/V(B_JM2|XBVM1) n_jm2i->N2 vts=+1 rd=+1;
  P/V(B_JS1|XBVM1) n_js1p->N3 vts=+1 rd=+1;
  P/V(B_JS2|XBVM1) n_js2p->N6 vts=+1 rd=+1.
No interpolation/sweep/added cases; nothing here is a scientific claim.
"""
import pathlib
import shutil

REPO = pathlib.Path('/home/howard/JoSIM')
ROOT = pathlib.Path(__file__).parent
INP = ROOT / 'inputs'

LOADS = [1, 12, 25, 50]
CASES = ['init_positive_read', 'init_positive_control',
         'init_negative_read', 'init_negative_control']


def pwl(knots: list[tuple[str, str]]) -> str:
    return ' '.join(f'{t}p {a}' for t, a in knots)


def netlist(case: str, load: int) -> str:
    pos = '100U' if 'positive' in case else '-100U'
    read = '100U' if 'read' in case else '0'
    init = [(0, 0), (9, 0), (10, pos), (20, pos), (21, 0), (170, 0)]
    wl = [(0, 0), (9, 0), (10, pos), (20, pos), (21, 0),
          (95, 0), (96, read), (105, read), (106, 0), (170, 0)]
    se = [(0, 0), (95, 0), (96, read), (105, read), (106, 0), (170, 0)]
    probe_dir = ('* Direct probes (preregistration.yaml):\n'
                 '*   V(SL1) SL1->0; I(L_SL|XBVM1) N8->SL1\n'
                 '*   I(I_WL1) 0->WL1; I(I_BL1) 0->BL1; I(I_SE1) 0->SE1\n'
                 '*   P/V(B_JM1|XBVM1) N1->n_jm1o vts=+1 rd=+1\n'
                 '*   P/V(B_JM2|XBVM1) n_jm2i->N2 vts=+1 rd=+1\n'
                 '*   P/V(B_JS1|XBVM1) n_js1p->N3 vts=+1 rd=+1\n'
                 '*   P/V(B_JS2|XBVM1) n_js2p->N6 vts=+1 rd=+1\n')
    return (
        f'* S2 {case} R_LD={load}ohm at 0.0125ps -- BVM-S2 load characterization (frozen)\n'
        f'* Closure: copied jjmit + bvm_cell; XBVM1 WL1 BL1 SE1 SL1 BVM; '
        f'only variable is R_LD SL1 0 {load}\n'
        f'* Init: WL/BL ramp to {pos} over 10-20 ps, return to 0 by 21 ps.\n'
        f'* Read: WL+SE +100 uA 96-105 ps'
        + (' (matched zero-read control: knots identical, amplitudes 0)'
           if 'control' in case else '')
        + f'\n'
        f'.include jjmit.cir\n.include bvm_cell.cir\n\n'
        f'XBVM1 WL1 BL1 SE1 SL1 BVM\n\n'
        f'R_LD SL1 0 {load}\n\n'
        f'I_WL1 0 WL1 pwl({pwl(wl)})\n'
        f'I_BL1 0 BL1 pwl({pwl(init)})\n'
        f'I_SE1 0 SE1 pwl({pwl(se)})\n\n'
        f'.tran 0.0125p 170p\n\n'
        f'{probe_dir}'
        f'.print P(B_JM1|XBVM1) V(B_JM1|XBVM1)\n'
        f'.print P(B_JM2|XBVM1) V(B_JM2|XBVM1)\n'
        f'.print P(B_JS1|XBVM1) V(B_JS1|XBVM1)\n'
        f'.print P(B_JS2|XBVM1) V(B_JS2|XBVM1)\n'
        f'.print V(SL1) I(L_SL|XBVM1)\n'
        f'.print I(I_WL1) I(I_BL1) I(I_SE1)\n'
        f'.end\n')


def main() -> None:
    assert not (ROOT / 'raw').exists(), 'raw root must not exist (immutable)'
    INP.mkdir(exist_ok=True)
    for src, dst in [('circuits/bvm/bvm_cell.cir', INP / 'bvm_cell.cir'),
                     ('circuits/models/jjmit.cir', INP / 'jjmit.cir')]:
        shutil.copy2(REPO / src, dst)
        assert (REPO / src).read_bytes() == dst.read_bytes(), f'{src} copy mismatch'
    n = 0
    for case in CASES:
        for load in LOADS:
            (INP / f'{case}_{load}ohm.cir').write_text(
                netlist(case, load), encoding='utf-8')
            n += 1
    assert n == 16, f'expected 16 netlists, wrote {n}'
    print(f'wrote {n} netlists + 2 closure copies into {INP}')


if __name__ == '__main__':
    main()
