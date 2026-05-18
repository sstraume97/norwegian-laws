"""Tests for quarto topic splitting."""
from lovdata_publisher.quarto import _split_topics


def test_split_topics_single():
    assert _split_topics("Bank, finans og regnskapsrett>Regnskap") == [
        "Bank, finans og regnskapsrett"
    ]


def test_split_topics_multi():
    text = "Bank, finans og regnskapsrett>Regnskap\nForvaltnings- og kommunalrett>Statistikk"
    assert _split_topics(text) == [
        "Bank, finans og regnskapsrett",
        "Forvaltnings- og kommunalrett",
    ]


def test_split_topics_empty():
    assert _split_topics("") == []
    assert _split_topics(None or "") == []


def test_split_topics_no_subtopic():
    assert _split_topics("Arbeidsrett") == ["Arbeidsrett"]


def test_split_topics_dedup():
    text = "Helse- og omsorgsrett>Helsepersonell\nHelse- og omsorgsrett>Pasientrettigheter"
    assert _split_topics(text) == ["Helse- og omsorgsrett"]


def test_split_topics_yaml_escaped_newline():
    """Frontmatter parser returns embedded \\n as literal two-char escape; verify split."""
    text = "Arbeidsrett>Arbeidsforhold\\nHelse- og omsorgsrett>Helsepersonell"
    assert _split_topics(text) == ["Arbeidsrett", "Helse- og omsorgsrett"]
