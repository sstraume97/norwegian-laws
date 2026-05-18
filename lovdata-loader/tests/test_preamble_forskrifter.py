"""Tests for parser._extract_law_refid_from_preamble generalisation to forskrifter."""
from lovdata_loader.parser import _extract_law_refid_from_preamble


def test_preamble_extractor_lov():
    text = "I lov 14. desember 2001 nr. 81 om bla bla gjøres følgende endringer:"
    assert _extract_law_refid_from_preamble(text) == "lov/2001-12-14-81"


def test_preamble_extractor_lov_av():
    text = "I lov av 14. desember 2001 nr. 81 om bla bla gjøres følgende endringer:"
    assert _extract_law_refid_from_preamble(text) == "lov/2001-12-14-81"


def test_preamble_extractor_forskrift():
    text = "I forskrift 14. februar 2023 nr. 193 om utmåling gjøres følgende endringer:"
    assert _extract_law_refid_from_preamble(text) == "forskrift/2023-02-14-193"


def test_preamble_extractor_forskrift_av():
    text = "I forskrift av 14. februar 2023 nr. 193 om utmåling gjøres følgende endringer:"
    assert _extract_law_refid_from_preamble(text) == "forskrift/2023-02-14-193"


def test_preamble_extractor_returns_empty_when_no_match():
    assert _extract_law_refid_from_preamble("noe annet") == ""


def test_preamble_extractor_returns_empty_for_unknown_month():
    text = "I lov 14. xtra 2001 nr. 81 om bla"
    assert _extract_law_refid_from_preamble(text) == ""
