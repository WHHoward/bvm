#!/usr/bin/env python3
"""Build only the preregistered canonical BVM -> 12-JSL physical decks."""
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "inputs"


def read_line(state: str, width: int) -> tuple[str, str, str]:
    init = "+100U" if state == "logical1" else "-100U"
    return (
        f"I_WL1 0 WL1 pwl(0p 0 10p 0 11p {init} 20p {init} 21p 0 95p 0 96p +100U {96+width}p +100U {97+width}p 0 170p 0)",
        f"I_BL1 0 BL1 pwl(0p 0 10p 0 11p {init} 20p {init} 21p 0 170p 0)",
        f"I_SE1 0 SE1 pwl(0p 0 95p 0 96p +100U {96+width}p +100U {97+width}p 0 170p 0)",
    )


def deck(state: str, width: int) -> str:
    wl, bl, se = read_line(state, width)
    lines = [
        f"* BVM_READ_SEMANTICS_AUDIT_AND_JSL_WIDTH_BRACKET_V1: canonical {state}_read, width={width}ps",
        "* negative init is used only for logical0; READ is always WL+SE +100uA",
        ".include ../jjmit.cir",
        ".include ../bvm_cell.cir",
        "XBVM1 WL1 BL1 SE1 SL1 BVM",
        "B_LD1  SL1  njsl1  jjmit area=3.2",
        "B_LD2  njsl1 njsl2 jjmit area=3.2",
        "B_LD3  njsl2 njsl3 jjmit area=3.2",
        "B_LD4  njsl3 njsl4 jjmit area=3.2",
        "B_LD5  njsl4 njsl5 jjmit area=3.2",
        "B_LD6  njsl5 njsl6 jjmit area=3.2",
        "B_LD7  njsl6 njsl7 jjmit area=3.2",
        "B_LD8  njsl7 njsl8 jjmit area=3.2",
        "B_LD9  njsl8 njsl9 jjmit area=3.2",
        "B_LD10 njsl9 njsl10 jjmit area=3.2",
        "B_LD11 njsl10 njsl11 jjmit area=3.2",
        "B_LD12 njsl11 0      jjmit area=3.2",
        wl, bl, se,
        ".tran 0.0125p 170p",
        ".print P(B_JM1|XBVM1) V(B_JM1|XBVM1) P(B_JM2|XBVM1) V(B_JM2|XBVM1)",
        ".print P(B_JS1|XBVM1) V(B_JS1|XBVM1) P(B_JS2|XBVM1) V(B_JS2|XBVM1)",
        ".print V(N6|XBVM1) V(SL1) V(njsl11)",
        ".print I(L_PSL|XBVM1) I(L_SL|XBVM1) I(B_LD1) I(B_LD12)",
        ".print P(B_LD1) V(B_LD1) I(B_LD1) P(B_LD2) V(B_LD2) I(B_LD2)",
        ".print P(B_LD3) V(B_LD3) I(B_LD3) P(B_LD4) V(B_LD4) I(B_LD4)",
        ".print P(B_LD5) V(B_LD5) I(B_LD5) P(B_LD6) V(B_LD6) I(B_LD6)",
        ".print P(B_LD7) V(B_LD7) I(B_LD7) P(B_LD8) V(B_LD8) I(B_LD8)",
        ".print P(B_LD9) V(B_LD9) I(B_LD9) P(B_LD10) V(B_LD10) I(B_LD10)",
        ".print P(B_LD11) V(B_LD11) I(B_LD11) P(B_LD12) V(B_LD12) I(B_LD12)",
        ".print I(I_WL1) I(I_BL1) I(I_SE1)",
        ".end",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    targets = [(12, "logical0", "12ps-canonical"), (13, "logical1", "13ps"), (13, "logical0", "13ps"),
               (14, "logical1", "14ps"), (14, "logical0", "14ps"), (15, "logical1", "15ps"), (15, "logical0", "15ps")]
    for width, state, directory in targets:
        destination = INPUT / directory / f"{state}-read.cir"
        expected = deck(state, width)
        if destination.exists() and destination.read_text(encoding="utf-8") != expected:
            raise SystemExit(f"refusing to overwrite non-identical fixture: {destination}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(expected, encoding="utf-8")
    print("built canonical physical fixtures: 12ps correction plus 13/14/15ps pairs")


if __name__ == "__main__":
    main()
