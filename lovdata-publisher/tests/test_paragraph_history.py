"""Tests for paragraph_history.py."""
import sqlite3
from pathlib import Path

from lovdata_publisher.paragraph_history import (
    _normalize_paragraph,
    _paragraph_slug,
    generate_paragraph_history_pages,
)


def test_normalize_paragraph_basic():
    assert _normalize_paragraph("§ 7-25") == "§ 7-25"
    assert _normalize_paragraph("§ 3-3a") == "§ 3-3a"
    assert _normalize_paragraph("§ 1-2a") == "§ 1-2a"


def test_normalize_paragraph_falls_back_to_instruction():
    assert _normalize_paragraph("kapittel 9", "§ 9-1 skal lyde:") == "§ 9-1"
    assert _normalize_paragraph("", "§ 3-1 første ledd skal lyde:") == "§ 3-1"


def test_normalize_paragraph_strips_first_letter_suffix_only():
    """'§ 3-1 første' must NOT match as '§ 3-1f'."""
    assert _normalize_paragraph("§ 3-1 første ledd") == "§ 3-1"


def test_paragraph_slug():
    assert _paragraph_slug("§ 7-25") == "para-7-25"
    assert _paragraph_slug("§ 3-3a") == "para-3-3a"
    assert _paragraph_slug("§ 1-2") == "para-1-2"


def test_generate_paragraph_history_writes_pages(tmp_path, monkeypatch):
    db = tmp_path / "amendments.db"
    conn = sqlite3.connect(db)
    conn.execute("""
        CREATE TABLE amendment_acts (
            refid TEXT, filename TEXT, title TEXT, short_title TEXT,
            date_in_force TEXT, date_in_force_resolved TEXT,
            date_published TEXT, ministry TEXT, changes_to TEXT,
            journal_number TEXT, misc_info TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE amendments (
            id INTEGER, act_refid TEXT, change_type TEXT,
            target TEXT, target_law TEXT, instruction TEXT, new_text TEXT
        )
    """)
    conn.executemany(
        "INSERT INTO amendment_acts VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        [
            ('lov/2024-06-21-42', 'a.xml', 'Endr. regnskapsloven', 'Bærekraft',
             '2024-11-01', '2024-11-01', '2024-06-21', 'FIN', 'lov/1998-07-17-56',
             '2024-0042', ''),
            ('lov/2023-01-01-1', 'b.xml', 'Older endr.', 'Older',
             '2023-01-01', '2023-01-01', '2023-01-01', 'FIN', 'lov/1998-07-17-56',
             '2023-0001', ''),
        ],
    )
    conn.executemany(
        "INSERT INTO amendments VALUES (?,?,?,?,?,?,?)",
        [
            (1, 'lov/2024-06-21-42', 'change', '§ 7-25', 'lov/1998-07-17-56',
             '§ 7-25 skal lyde:', 'Egenkapital ...'),
            (2, 'lov/2023-01-01-1', 'change', '§ 7-25', 'lov/1998-07-17-56',
             '§ 7-25 første ledd skal lyde:', 'Egenkapital ...'),
            (3, 'lov/2024-06-21-42', 'change', '§ 1-2a', 'lov/1998-07-17-56',
             '§ 1-2a skal lyde:', 'Plikt ...'),
        ],
    )
    conn.commit()
    conn.close()

    # Need a stub markdown file so title lookup works
    monkeypatch.chdir(tmp_path)
    lover = Path("lover")
    lover.mkdir()
    (lover / "lov-1998-07-17-56.md").write_text(
        '---\nrefid: "lov/1998-07-17-56"\nkorttittel: "Regnskapsloven – rskl"\ntittel: "Lov om årsregnskap"\n---\n',
        encoding="utf-8",
    )

    out = tmp_path / "out"
    n, amended = generate_paragraph_history_pages(
        db_path=str(db),
        output_dir=str(out),
    )

    # Two distinct paragraphs (§ 7-25, § 1-2a) → 2 pages
    assert n == 2

    # amended map should reflect what's now available as history pages
    assert amended == {"lov/1998-07-17-56": {"§ 7-25", "§ 1-2a"}}

    page_725 = out / "lov-1998-07-17-56" / "para-7-25.html"
    assert page_725.exists()
    text = page_725.read_text(encoding="utf-8")
    assert "§ 7-25" in text
    assert "Regnskapsloven" in text
    # Both amendments to § 7-25 should be listed
    assert "2024-06-21" in text
    assert "2023-01-01" in text
    # Newest first
    assert text.index("2024-06-21") < text.index("2023-01-01")

    page_12a = out / "lov-1998-07-17-56" / "para-1-2a.html"
    assert page_12a.exists()


def test_generate_paragraph_history_handles_missing_db(tmp_path):
    n, amended = generate_paragraph_history_pages(
        db_path=str(tmp_path / "nope.db"),
        output_dir=str(tmp_path / "out"),
    )
    assert n == 0


def test_generate_paragraph_history_handles_missing_amendments_table(tmp_path):
    db = tmp_path / "amendments.db"
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE amendment_acts (refid TEXT)")
    conn.close()
    n, amended = generate_paragraph_history_pages(
        db_path=str(db),
        output_dir=str(tmp_path / "out"),
    )
    assert n == 0


def test_normalize_paragraph_handles_prefixed_target():
    """Targets sometimes carry the law refid prefix, e.g. 'lov/1915-08-13-5/§217a'.
    The regex must still extract '§ 217a' (or the X-Y form when present)."""
    assert _normalize_paragraph("lov/1998-07-17-56/§1-2a") == "§ 1-2a"
    assert _normalize_paragraph("forskrift/2024-01-01-1/§2-3") == "§ 2-3"


def test_new_text_renders_in_collapsible_block(tmp_path, monkeypatch):
    """When an amendment row has new_text, the rendered page should include
    a <details>/Ny tekst block with that text."""
    db = tmp_path / "amendments.db"
    conn = sqlite3.connect(db)
    conn.execute("""
        CREATE TABLE amendment_acts (
            refid TEXT, filename TEXT, title TEXT, short_title TEXT,
            date_in_force TEXT, date_in_force_resolved TEXT,
            date_published TEXT, ministry TEXT, changes_to TEXT,
            journal_number TEXT, misc_info TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE amendments (
            id INTEGER, act_refid TEXT, change_type TEXT,
            target TEXT, target_law TEXT, instruction TEXT, new_text TEXT
        )
    """)
    conn.execute(
        "INSERT INTO amendment_acts VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        ('lov/2024-06-21-42', 'a.xml', 'Endr. regnskapsloven', 'Bærekraft',
         '2024-11-01', '2024-11-01', '2024-06-21', 'FIN', 'lov/1998-07-17-56',
         '2024-0042', ''),
    )
    conn.execute(
        "INSERT INTO amendments VALUES (?,?,?,?,?,?,?)",
        (1, 'lov/2024-06-21-42', 'change', '§ 7-25', 'lov/1998-07-17-56',
         '§ 7-25 skal lyde:',
         'Egenkapital består av innskutt egenkapital og opptjent egenkapital.'),
    )
    conn.commit()
    conn.close()

    monkeypatch.chdir(tmp_path)
    lover = Path("lover")
    lover.mkdir()
    (lover / "lov-1998-07-17-56.md").write_text(
        '---\nrefid: "lov/1998-07-17-56"\nkorttittel: "Regnskapsloven"\ntittel: "Lov om årsregnskap"\n---\n',
        encoding="utf-8",
    )

    out = tmp_path / "out"
    n, _ = generate_paragraph_history_pages(db_path=str(db), output_dir=str(out))
    assert n == 1

    page = (out / "lov-1998-07-17-56" / "para-7-25.html").read_text(encoding="utf-8")
    assert "<summary>Ny tekst</summary>" in page
    assert "Egenkapital består av innskutt egenkapital" in page
    # new_text block should not appear for amendments without new_text
    # (sanity check the optional-block path is genuinely conditional)


def test_no_new_text_block_when_missing(tmp_path, monkeypatch):
    db = tmp_path / "amendments.db"
    conn = sqlite3.connect(db)
    conn.execute("""
        CREATE TABLE amendment_acts (
            refid TEXT, filename TEXT, title TEXT, short_title TEXT,
            date_in_force TEXT, date_in_force_resolved TEXT,
            date_published TEXT, ministry TEXT, changes_to TEXT,
            journal_number TEXT, misc_info TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE amendments (
            id INTEGER, act_refid TEXT, change_type TEXT,
            target TEXT, target_law TEXT, instruction TEXT, new_text TEXT
        )
    """)
    conn.execute(
        "INSERT INTO amendment_acts VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        ('lov/2024-06-21-42', 'a.xml', 'Endr.', 'X',
         '2024-11-01', '2024-11-01', '2024-06-21', 'FIN', 'lov/1998-07-17-56',
         '2024-0042', ''),
    )
    conn.execute(
        "INSERT INTO amendments VALUES (?,?,?,?,?,?,?)",
        (1, 'lov/2024-06-21-42', 'change', '§ 7-25', 'lov/1998-07-17-56',
         '§ 7-25 skal oppheves.', ''),  # empty new_text
    )
    conn.commit()
    conn.close()

    monkeypatch.chdir(tmp_path)
    lover = Path("lover")
    lover.mkdir()
    (lover / "lov-1998-07-17-56.md").write_text(
        '---\nrefid: "lov/1998-07-17-56"\nkorttittel: "X"\ntittel: "Y"\n---\n',
        encoding="utf-8",
    )

    out = tmp_path / "out"
    generate_paragraph_history_pages(db_path=str(db), output_dir=str(out))
    page = (out / "lov-1998-07-17-56" / "para-7-25.html").read_text(encoding="utf-8")
    assert "<summary>Ny tekst</summary>" not in page


def test_current_paragraph_text_renders_from_markdown(tmp_path, monkeypatch):
    """The history page should include a 'Gjeldende tekst' section showing
    the current paragraph text extracted from the law markdown."""
    db = tmp_path / "amendments.db"
    conn = sqlite3.connect(db)
    conn.execute("""
        CREATE TABLE amendment_acts (
            refid TEXT, filename TEXT, title TEXT, short_title TEXT,
            date_in_force TEXT, date_in_force_resolved TEXT,
            date_published TEXT, ministry TEXT, changes_to TEXT,
            journal_number TEXT, misc_info TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE amendments (
            id INTEGER, act_refid TEXT, change_type TEXT,
            target TEXT, target_law TEXT, instruction TEXT, new_text TEXT
        )
    """)
    conn.execute(
        "INSERT INTO amendment_acts VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        ('lov/2024-06-21-42', 'a.xml', 'Endr.', 'X',
         '2024-11-01', '2024-11-01', '2024-06-21', 'FIN', 'lov/1998-07-17-56',
         '2024-0042', ''),
    )
    conn.execute(
        "INSERT INTO amendments VALUES (?,?,?,?,?,?,?)",
        (1, 'lov/2024-06-21-42', 'change', '§ 7-25', 'lov/1998-07-17-56',
         '§ 7-25 skal lyde:', 'Egenkapital ...'),
    )
    conn.commit()
    conn.close()

    monkeypatch.chdir(tmp_path)
    lover = Path("lover")
    lover.mkdir()
    (lover / "lov-1998-07-17-56.md").write_text(
        '---\n'
        'refid: "lov/1998-07-17-56"\n'
        'korttittel: "Regnskapsloven"\n'
        'tittel: "Lov om årsregnskap"\n'
        '---\n'
        '\n'
        '# Regnskapsloven\n'
        '\n'
        '##### § 7-25. Egenkapital\n'
        '\n'
        '(1) Opptjent egenkapital skal spesifiseres.\n'
        '\n'
        '(2) Det skal opplyses om endringer.\n'
        '\n'
        '##### § 7-26. Neste paragraf\n'
        '\n'
        '(1) Skal ikke vises på § 7-25 history page.\n',
        encoding="utf-8",
    )

    out = tmp_path / "out"
    generate_paragraph_history_pages(db_path=str(db), output_dir=str(out))
    page = (out / "lov-1998-07-17-56" / "para-7-25.html").read_text(encoding="utf-8")

    # Current text section present
    assert '<section class="current-text">' in page
    assert "Gjeldende tekst" in page
    assert "§ 7-25. Egenkapital" in page
    assert "Opptjent egenkapital skal spesifiseres" in page
    assert "Det skal opplyses om endringer" in page
    # Adjacent paragraph's text must NOT leak in
    assert "Skal ikke vises" not in page
    assert "§ 7-26" not in page.split("<section class=\"current-text\">")[1].split("</section>")[0]


def test_current_text_skipped_when_law_markdown_missing(tmp_path, monkeypatch):
    """If the law markdown is unavailable, history page renders without the
    current-text block instead of erroring."""
    db = tmp_path / "amendments.db"
    conn = sqlite3.connect(db)
    conn.execute("""
        CREATE TABLE amendment_acts (
            refid TEXT, filename TEXT, title TEXT, short_title TEXT,
            date_in_force TEXT, date_in_force_resolved TEXT,
            date_published TEXT, ministry TEXT, changes_to TEXT,
            journal_number TEXT, misc_info TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE amendments (
            id INTEGER, act_refid TEXT, change_type TEXT,
            target TEXT, target_law TEXT, instruction TEXT, new_text TEXT
        )
    """)
    conn.execute(
        "INSERT INTO amendment_acts VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        ('lov/2024-06-21-42', 'a.xml', 'Endr.', 'X',
         '2024-11-01', '2024-11-01', '2024-06-21', 'FIN', 'lov/9999-12-31-99',
         '2024-0042', ''),
    )
    conn.execute(
        "INSERT INTO amendments VALUES (?,?,?,?,?,?,?)",
        (1, 'lov/2024-06-21-42', 'change', '§ 1-1', 'lov/9999-12-31-99',
         '§ 1-1 skal lyde:', ''),
    )
    conn.commit()
    conn.close()

    monkeypatch.chdir(tmp_path)
    # NO markdown file for lov/9999-12-31-99
    out = tmp_path / "out"
    n, _ = generate_paragraph_history_pages(db_path=str(db), output_dir=str(out))
    assert n == 1
    page = (out / "lov-9999-12-31-99" / "para-1-1.html").read_text(encoding="utf-8")
    # No current-text section
    assert '<section class="current-text">' not in page
    # But the amendments section is still there
    assert "Endringer" in page
