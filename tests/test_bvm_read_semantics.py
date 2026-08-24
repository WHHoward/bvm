from pathlib import Path

from scripts.verify_bvm_read_semantics import parse_deck, validate_pair


def _deck(tmp_path: Path, name: str, wl: str, bl: str, se: str, load: str = "R_LD SL1 0 12") -> Path:
    path = tmp_path / name
    path.write_text(
        "\n".join([
            "XBVM1 WL1 BL1 SE1 SL1 BVM",
            load,
            f"I_WL1 0 WL1 pwl(0p 0 10p 0 11p {wl} 20p {wl} 21p 0 95p 0 96p {wl if wl.startswith('+') else '+100U'} 105p {wl if wl.startswith('+') else '+100U'} 106p 0 170p 0)",
            f"I_BL1 0 BL1 pwl(0p 0 10p 0 11p {bl} 20p {bl} 21p 0 170p 0)",
            f"I_SE1 0 SE1 pwl(0p 0 95p 0 96p {se} 105p {se} 106p 0 170p 0)",
        ]) + "\n",
        encoding="utf-8",
    )
    return path


def test_wl_only_negative_read_is_not_canonical(tmp_path: Path):
    logical1 = _deck(tmp_path, "l1.cir", "+100U", "+100U", "+100U")
    logical0 = _deck(tmp_path, "l0.cir", "-100U", "-100U", "0")
    p1 = parse_deck(logical1, role_hint="logical1_read")
    p0 = parse_deck(logical0, role_hint="logical0_read")
    assert p0["case_role"] == "WL_ONLY_NEGATIVE_STATE_DIAGNOSTIC"
    assert "logical0" in " ".join(validate_pair(p1, p0)).lower()


def test_canonical_logical_pair_matches(tmp_path: Path):
    logical1 = _deck(tmp_path, "l1.cir", "+100U", "+100U", "+100U")
    logical0 = _deck(tmp_path, "l0.cir", "-100U", "-100U", "+100U")
    p1 = parse_deck(logical1, role_hint="logical1_read")
    p0 = parse_deck(logical0, role_hint="logical0_read")
    assert p1["case_role"] == "logical1_read"
    assert p0["case_role"] == "logical0_read"
    assert validate_pair(p1, p0) == []


def test_load_mismatch_fails_matched_pair(tmp_path: Path):
    logical1 = _deck(tmp_path, "l1.cir", "+100U", "+100U", "+100U", "R_LD SL1 0 12")
    logical0 = _deck(tmp_path, "l0.cir", "-100U", "-100U", "+100U", "R_LD SL1 0 10")
    p1 = parse_deck(logical1, role_hint="logical1_read")
    p0 = parse_deck(logical0, role_hint="logical0_read")
    assert any("load_topology" in error for error in validate_pair(p1, p0))


def test_negative_initialization_polarity_reversal_is_superseded(tmp_path: Path):
    path = tmp_path / "negative-reversal.cir"
    path.write_text(
        "\n".join([
            "XBVM1 WL1 BL1 SE1 SL1 BVM",
            "R_LD SL1 0 12",
            "I_WL1 0 WL1 pwl(0p 0 10p 0 11p -100U 20p +100U 21p 0 95p 0 96p +100U 105p +100U 106p 0 170p 0)",
            "I_BL1 0 BL1 pwl(0p 0 10p 0 11p -100U 20p +100U 21p 0 170p 0)",
            "I_SE1 0 SE1 pwl(0p 0 95p 0 96p +100U 105p +100U 106p 0 170p 0)",
        ]) + "\n",
        encoding="utf-8",
    )
    parsed = parse_deck(path, role_hint="logical0_read")
    assert parsed["classification"] == "INITIALIZATION_PROTOCOL_MISMATCH"
    assert parsed["case_role"] == "SUPERSEDED_INVALID_INIT_FIXTURE"
    assert parsed["current_validity"] == "SUPERSEDED_INVALID_INIT_FIXTURE"
    assert parsed["initialization_protocol"]["sign_reversal"] is True
