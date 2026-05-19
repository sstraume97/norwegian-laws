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
