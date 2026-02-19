"""Tests for lovdata_pipeline."""
import os
import re
import pytest
from pathlib import Path
from bs4 import BeautifulSoup

from lovdata_pipeline.pipeline import (
    parse_effective_date,
    parse_publication_date,
    parse_law_metadata,
    extract_header_field,
    extract_last_changed_by,
    legal_article_to_markdown,
    law_to_markdown,
    refid_to_filepath,
    format_commit_message,
    date_to_git_timestamp,
    parse_lovtidend_file,
    AmendmentAct,
    Amendment,
)
from lovdata_pipeline.quarto import split_departments, parse_frontmatter, group_laws_by_area

FIXTURES = Path(__file__).parent


# ─── parse_effective_date ───────────────────────────────────────────────────

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

    def test_kongen_fastsetter(self):
        date, deferred = parse_effective_date("Kongen fastsetter", "2023-06-20 14:30")
        assert date == "2023-06-20"
        assert deferred is True

    def test_kongen_fastset(self):
        date, deferred = parse_effective_date("Kongen fastset", "2023-06-20")
        assert date == "2023-06-20"
        assert deferred is True

    def test_iso_date_with_trailing_text(self):
        date, deferred = parse_effective_date("2024-01-01 some extra text", "2023-12-15")
        assert date == "2024-01-01"
        assert deferred is False

    def test_empty_string_falls_back(self):
        date, deferred = parse_effective_date("", "2023-06-20")
        assert date == "2023-06-20"
        assert deferred is True

    def test_garbage_falls_back(self):
        date, deferred = parse_effective_date("Straks", "2023-06-20")
        assert date == "2023-06-20"
        assert deferred is True

    def test_straks_with_date(self):
        date, deferred = parse_effective_date("Straks, med virkning fra 2020-01-01", "2019-12-20")
        assert date == "2019-12-20"
        assert deferred is True


class TestParsePublicationDate:
    def test_iso_datetime(self):
        assert parse_publication_date("2023-06-20 14:30") == "2023-06-20"

    def test_iso_date(self):
        assert parse_publication_date("2023-06-20") == "2023-06-20"

    def test_norwegian_datetime(self):
        assert parse_publication_date("20.06.2023 14:30") == "2023-06-20"

    def test_norwegian_date(self):
        assert parse_publication_date("20.06.2023") == "2023-06-20"

    def test_fallback(self):
        assert parse_publication_date("nonsense") == "2000-01-01"

    def test_whitespace(self):
        assert parse_publication_date("  2023-06-20  ") == "2023-06-20"


# ─── extract_last_changed_by ───────────────────────────────────────────────

class TestExtractLastChangedBy:
    def test_anchor_with_fra(self):
        html = '<header><dd class="lastChangedBy"><a href="lov/2023-06-16-40">lov/2023-06-16-40</a> fra 2023-07-01</dd></header>'
        soup = BeautifulSoup(html, "html.parser")
        header = soup.find("header")
        refid, in_force = extract_last_changed_by(header)
        assert refid == "lov/2023-06-16-40"
        assert in_force == "2023-07-01"

    def test_forskrift_anchor(self):
        html = '<header><dd class="lastChangedBy"><a href="forskrift/2024-06-07-928">forskrift/2024-06-07-928</a> fra 2024-05-21</dd></header>'
        soup = BeautifulSoup(html, "html.parser")
        header = soup.find("header")
        refid, in_force = extract_last_changed_by(header)
        assert refid == "forskrift/2024-06-07-928"
        assert in_force == "2024-05-21"

    def test_no_element(self):
        html = '<header><dd class="title">Some title</dd></header>'
        soup = BeautifulSoup(html, "html.parser")
        header = soup.find("header")
        refid, in_force = extract_last_changed_by(header)
        assert refid == ""
        assert in_force == ""

    def test_plain_text_no_anchor(self):
        html = '<header><dd class="sistEndret">lov/2020-01-01-5</dd></header>'
        soup = BeautifulSoup(html, "html.parser")
        header = soup.find("header")
        refid, in_force = extract_last_changed_by(header)
        assert refid == "lov/2020-01-01-5"
        assert in_force == ""


# ─── split_departments ──────────────────────────────────────────────────────

class TestSplitDepartments:
    def test_single_department(self):
        assert split_departments("Finansdepartementet") == ["Finansdepartementet"]

    def test_concatenated_departments(self):
        result = split_departments("Klima- og miljødepartementetLandbruks- og matdepartementet")
        assert result == ["Klima- og miljødepartementet", "Landbruks- og matdepartementet"]

    def test_unknown_department(self):
        assert split_departments("Ukjent departement") == ["Ukjent departement"]

    def test_empty_string(self):
        assert split_departments("") == [""]

    def test_triple_concatenation(self):
        result = split_departments(
            "FinansdepartementetJustis- og beredskapsdepartementetKunnskapsdepartementet"
        )
        assert len(result) == 3
        assert "Finansdepartementet" in result
        assert "Justis- og beredskapsdepartementet" in result
        assert "Kunnskapsdepartementet" in result


# ─── refid_to_filepath ──────────────────────────────────────────────────────

class TestRefidToFilepath:
    def test_standard(self):
        assert refid_to_filepath("lov/1998-07-17-56") == "lover/lov-1998-07-17-56.md"

    def test_nested_slashes(self):
        assert refid_to_filepath("lov/2024-06-21-41") == "lover/lov-2024-06-21-41.md"


# ─── date_to_git_timestamp ─────────────────────────────────────────────────

class TestDateToGitTimestamp:
    def test_valid_date(self):
        ts = date_to_git_timestamp("2024-01-01")
        assert "+0100" in ts
        assert ts.startswith("1704")

    def test_invalid_date(self):
        ts = date_to_git_timestamp("not-a-date")
        assert "+0100" in ts


# ─── Fixture-based: parse_law_metadata ──────────────────────────────────────

class TestParseLawMetadataFixtures:
    @pytest.fixture
    def grunnloven_soup(self):
        path = FIXTURES / "fixture_grunnloven.xml"
        if not path.exists():
            pytest.skip("fixture not available")
        with open(path, encoding="utf-8") as f:
            return BeautifulSoup(f.read(), "html.parser")

    @pytest.fixture
    def norske_lov_soup(self):
        path = FIXTURES / "fixture_norske_lov.xml"
        if not path.exists():
            pytest.skip("fixture not available")
        with open(path, encoding="utf-8") as f:
            return BeautifulSoup(f.read(), "html.parser")

    def test_grunnloven_refid(self, grunnloven_soup):
        meta = parse_law_metadata(grunnloven_soup)
        assert meta.refid == "lov/1814-05-17"

    def test_grunnloven_title(self, grunnloven_soup):
        meta = parse_law_metadata(grunnloven_soup)
        assert "Grunnlov" in meta.title

    def test_grunnloven_last_amended_clean(self, grunnloven_soup):
        meta = parse_law_metadata(grunnloven_soup)
        assert "fra " not in meta.last_amended
        assert meta.last_amended.startswith("forskrift/") or meta.last_amended.startswith("lov/")

    def test_grunnloven_last_amended_in_force(self, grunnloven_soup):
        meta = parse_law_metadata(grunnloven_soup)
        assert re.match(r"\d{4}-\d{2}-\d{2}", meta.last_amended_in_force)

    def test_grunnloven_empty_ikrafttredelse(self, grunnloven_soup):
        meta = parse_law_metadata(grunnloven_soup)
        assert meta.date_in_force == ""

    def test_norske_lov_refid(self, norske_lov_soup):
        meta = parse_law_metadata(norske_lov_soup)
        assert meta.refid == "lov/1687-04-15"

    def test_norske_lov_department(self, norske_lov_soup):
        meta = parse_law_metadata(norske_lov_soup)
        assert meta.ministry == "Justis- og beredskapsdepartementet"


# ─── Fixture-based: parse_lovtidend_file ────────────────────────────────────

class TestParseLovtidendFixture:
    @pytest.fixture
    def lovtidend_act(self):
        path = FIXTURES / "fixture_lovtidend.xml"
        if not path.exists():
            pytest.skip("fixture not available")
        with open(path, "rb") as f:
            content = f.read()
        act = parse_lovtidend_file(content, "fixture_lovtidend.xml")
        if act is None:
            pytest.skip("fixture parsed to None")
        return act

    def test_has_refid(self, lovtidend_act):
        assert lovtidend_act.refid

    def test_has_title(self, lovtidend_act):
        assert lovtidend_act.title

    def test_has_amendments(self, lovtidend_act):
        assert len(lovtidend_act.amendments) > 0

    def test_has_changes_to(self, lovtidend_act):
        assert len(lovtidend_act.changes_to) > 0

    def test_amendment_has_type(self, lovtidend_act):
        for a in lovtidend_act.amendments:
            assert a.change_type in ("change", "repeal", "add", "move", "unknown")

    def test_amendment_has_target(self, lovtidend_act):
        typed = [a for a in lovtidend_act.amendments if a.change_type != "unknown"]
        assert all(a.target for a in typed)


# ─── format_commit_message ──────────────────────────────────────────────────

class TestFormatCommitMessage:
    def test_basic_format(self):
        act = AmendmentAct(
            refid="lov/2024-01-01-1",
            filename="test.xml",
            title="Testlov",
            short_title="Testlov",
            date_in_force="2024-06-01",
            date_published="2024-01-15",
            ministry="Testdepartementet",
            changes_to=["lov/2020-01-01-5"],
            amendments=[
                Amendment(change_type="change", target="lov/2020-01-01-5/§1", instruction="§ 1 skal lyde:", new_text="Ny tekst"),
            ],
            misc_info="",
            journal_number="2024-0001",
        )
        msg = format_commit_message(act)
        assert msg.startswith("Testlov")
        assert "lov/2024-01-01-1" in msg
        assert "2024-06-01" in msg
        assert "2024-0001" in msg
        assert "endret" in msg

    def test_long_title_truncated(self):
        act = AmendmentAct(
            refid="lov/2024-01-01-1",
            filename="test.xml",
            title="A" * 100,
            short_title="A" * 100,
            date_in_force="2024-01-01",
            date_published="2024-01-01",
            ministry="",
            changes_to=[],
            amendments=[],
            misc_info="",
            journal_number="",
        )
        msg = format_commit_message(act)
        first_line = msg.split("\n")[0]
        assert len(first_line) <= 72

    def test_deferred_date_noted(self):
        act = AmendmentAct(
            refid="lov/2024-01-01-1",
            filename="test.xml",
            title="Testlov",
            short_title="Testlov",
            date_in_force="Kongen bestemmer",
            date_published="2024-01-15",
            ministry="",
            changes_to=[],
            amendments=[],
            misc_info="",
            journal_number="",
        )
        msg = format_commit_message(act)
        assert "kunngjøringsdato" in msg


# ─── End-to-end: law_to_markdown from fixture ──────────────────────────────

class TestLawToMarkdownEndToEnd:
    def test_grunnloven_metadata(self):
        fixture = FIXTURES / "fixture_grunnloven.xml"
        if not fixture.exists():
            pytest.skip("fixture not available")
        with open(fixture, encoding="utf-8") as f:
            soup = BeautifulSoup(f.read(), "html.parser")
        meta = parse_law_metadata(soup)
        assert meta.refid == "lov/1814-05-17"
        assert meta.last_amended == "forskrift/2024-06-07-928"
        assert meta.last_amended_in_force == "2024-05-21"
        assert "fra " not in meta.last_amended

    def test_full_law_roundtrip(self, tmp_path):
        html = """<html><header>
        <dd class="refid">lov/2024-01-01-1</dd>
        <dd class="title">Testlov om testing</dd>
        <dd class="titleShort">Testloven</dd>
        <dd class="ministry">Testdepartementet</dd>
        <dd class="dateInForce">2024-06-01</dd>
        <dd class="lastChangedBy"><a href="lov/2024-06-01-5">lov/2024-06-01-5</a> fra 2024-07-01</dd>
        <dd class="legalArea">Test</dd>
        </header><body>
        <section><h2>Kapittel 1</h2>
        <article class="legalArticle" data-name="§1">
        <h3 class="legalArticleHeader"><span class="legalArticleValue">§ 1</span></h3>
        <article class="legalP">Første ledd.</article>
        </article>
        </section>
        </body></html>"""
        soup = BeautifulSoup(html, "html.parser")
        md = law_to_markdown(soup)
        assert 'refid: "lov/2024-01-01-1"' in md
        assert 'sist-endret: "lov/2024-06-01-5"' in md
        assert 'sist-endret-ikrafttredelse: "2024-07-01"' in md
        assert "Første ledd." in md
        assert "## Kapittel 1" in md


# ─── parse_frontmatter (quarto.py) ─────────────────────────────────────────

class TestParseFrontmatter:
    def test_reads_real_law_file(self, tmp_path):
        f = tmp_path / "test.md"
        f.write_text('---\ntittel: "Testlov"\nrefid: "lov/2024-01-01-1"\n---\n\n# Testlov\n')
        meta = parse_frontmatter(str(f))
        assert meta["tittel"] == "Testlov"
        assert meta["refid"] == "lov/2024-01-01-1"

    def test_no_frontmatter(self, tmp_path):
        f = tmp_path / "test.md"
        f.write_text("# Just a heading\n")
        meta = parse_frontmatter(str(f))
        assert meta == {}
