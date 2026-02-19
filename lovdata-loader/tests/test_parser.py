"""Tests for lovdata_loader.parser."""
import re
import pytest
from pathlib import Path
from bs4 import BeautifulSoup

from lovdata_loader.parser import (
    parse_effective_date,
    parse_publication_date,
    extract_last_changed_by,
    _parse_law_metadata,
    parse_article,
    parse_law,
)
from lovdata_loader.models import LawData

FIXTURES = Path(__file__).parent / "fixtures"


# ─── parse_effective_date ────────────────────────────────────────────────────

class TestParseEffectiveDate:
    def test_iso_date(self):
        date, deferred = parse_effective_date("2024-01-01", "2023-12-15")
        assert date == "2024-01-01"
        assert deferred is False

    def test_norwegian_date(self):
        date, deferred = parse_effective_date("01.01.2024", "2023-12-15")
        assert date == "2024-01-01"
        assert deferred is False

    def test_kongen_bestemmer(self):
        date, deferred = parse_effective_date("Kongen bestemmer", "2023-12-15")
        assert date == "2023-12-15"
        assert deferred is True

    def test_empty_string_falls_back(self):
        date, deferred = parse_effective_date("", "2023-06-20")
        assert date == "2023-06-20"
        assert deferred is True


# ─── parse_publication_date ──────────────────────────────────────────────────

class TestParsePublicationDate:
    def test_iso_datetime(self):
        assert parse_publication_date("2023-06-20 14:30") == "2023-06-20"

    def test_norwegian_date(self):
        assert parse_publication_date("20.06.2023") == "2023-06-20"

    def test_fallback(self):
        assert parse_publication_date("nonsense") == "2000-01-01"


# ─── extract_last_changed_by ────────────────────────────────────────────────

class TestExtractLastChangedBy:
    def test_anchor_with_fra(self):
        html = '<header><dd class="lastChangedBy"><a href="lov/2023-06-16-40">lov/2023-06-16-40</a> fra 2023-07-01</dd></header>'
        soup = BeautifulSoup(html, "html.parser")
        refid, in_force = extract_last_changed_by(soup.find("header"))
        assert refid == "lov/2023-06-16-40"
        assert in_force == "2023-07-01"

    def test_no_element(self):
        html = '<header><dd class="title">Some title</dd></header>'
        soup = BeautifulSoup(html, "html.parser")
        refid, in_force = extract_last_changed_by(soup.find("header"))
        assert refid == ""
        assert in_force == ""


# ─── Fixture-based: parse_law ────────────────────────────────────────────────

class TestParseLawFixtures:
    def test_grunnloven(self):
        path = FIXTURES / "fixture_grunnloven.xml"
        if not path.exists():
            pytest.skip("fixture not available")
        law = parse_law(path.read_bytes())
        assert law is not None
        assert law.refid == "lov/1814-05-17"
        assert "Grunnlov" in law.title

    def test_norske_lov(self):
        path = FIXTURES / "fixture_norske_lov.xml"
        if not path.exists():
            pytest.skip("fixture not available")
        law = parse_law(path.read_bytes())
        assert law is not None
        assert law.refid == "lov/1687-04-15"
        assert law.ministry == "Justis- og beredskapsdepartementet"


# ─── LawData round-trip ─────────────────────────────────────────────────────

class TestLawDataSerialization:
    def test_to_json_and_back(self):
        law = LawData(
            refid="lov/2024-01-01-1",
            title="Testlov",
            short_title="Testloven",
            ministry="Testdepartementet",
            date_in_force="2024-06-01",
            last_amended="",
            last_amended_in_force="",
            legal_area="Test",
            sections=[],
            top_level_articles=[],
        )
        d = law.to_dict()
        restored = LawData.from_dict(d)
        assert restored.refid == law.refid
        assert restored.title == law.title
        assert restored.ministry == law.ministry
