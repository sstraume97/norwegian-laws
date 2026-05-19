"""Tests for stats_page.py — the aktivitet leaderboard."""
import sqlite3
from pathlib import Path

import pytest

from lovdata_publisher.stats_page import (
    _ministry_slug,
    _refid_to_stem,
    generate_stats_page,
)


def test_refid_to_stem():
    assert _refid_to_stem("lov/1998-07-17-56") == "lov-1998-07-17-56"
    assert _refid_to_stem("forskrift/2024-01-01-1") == "forskrift-2024-01-01-1"


def test_ministry_slug():
    assert _ministry_slug("Finansdepartementet") == "finansdepartementet"
    assert _ministry_slug("Klima- og miljødepartementet") == "klima--og-miljodepartementet"
    assert _ministry_slug("Næringsdepartementet") == "naeringsdepartementet"


def test_generate_stats_page_writes_html(tmp_path):
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
            ('lov/2024-06-21-42', 'a.xml', 'Endr. regnskapsloven', 'X',
             '2024-11-01', '2024-11-01', '2024-06-21', 'Finansdepartementet',
             'lov/1998-07-17-56', '2024-0042', ''),
            ('lov/2023-01-01-1', 'b.xml', 'Older endr.', 'Y',
             '2023-01-01', '2023-01-01', '2023-01-01', 'Justis- og beredskapsdepartementet',
             'lov/1998-07-17-56', '2023-0001', ''),
        ],
    )
    conn.executemany(
        "INSERT INTO amendments VALUES (?,?,?,?,?,?,?)",
        [
            (1, 'lov/2024-06-21-42', 'change', '§ 7-25', 'lov/1998-07-17-56', '§ 7-25', ''),
            (2, 'lov/2023-01-01-1', 'change', '§ 1-2', 'lov/1998-07-17-56', '§ 1-2', ''),
        ],
    )
    conn.commit()
    conn.close()

    lover = tmp_path / "lover"
    lover.mkdir()
    (lover / "lov-1998-07-17-56.md").write_text(
        '---\nrefid: "lov/1998-07-17-56"\ntittel: "Regnskapsloven"\nkorttittel: "Regnskapsloven"\n---\n',
        encoding="utf-8",
    )

    out = tmp_path / "aktivitet.html"
    ok = generate_stats_page(
        db_path=str(db),
        output_path=str(out),
        lover_dir=str(lover),
        forskrifter_dir=str(tmp_path / "forskrifter"),  # doesn't exist
    )
    assert ok is True
    page = out.read_text(encoding="utf-8")
    assert "<h1>Aktivitet" in page
    assert "Regnskapsloven" in page
    assert "2" in page  # Two amending acts
    assert "Finansdepartementet" in page
    assert "lover/lov-1998-07-17-56.html" in page
    assert "feeds/lov-1998-07-17-56.xml" in page
    assert "historie/lov-1998-07-17-56.html" in page


def test_generate_stats_page_missing_db_returns_false(tmp_path):
    ok = generate_stats_page(
        db_path=str(tmp_path / "nope.db"),
        output_path=str(tmp_path / "out.html"),
    )
    assert ok is False
    assert not (tmp_path / "out.html").exists()
