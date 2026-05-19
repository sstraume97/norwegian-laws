"""Tests for the Atom feed generator."""
import sqlite3
import xml.etree.ElementTree as ET
from pathlib import Path

from lovdata_publisher.feed import _filepath_for, generate_atom_feed


def test_filepath_for_lov():
    assert _filepath_for("lov/1998-07-17-56") == "/lover/lov-1998-07-17-56.html"


def test_filepath_for_forskrift():
    assert _filepath_for("forskrift/2024-06-21-1166") == "/forskrifter/forskrift-2024-06-21-1166.html"


def test_filepath_for_unknown():
    assert _filepath_for("avtale/2024-01-01-1") == ""


def test_generate_atom_feed_writes_valid_xml(tmp_path):
    snap = tmp_path / "snap"
    snap.mkdir()
    db = snap / "amendments.db"
    conn = sqlite3.connect(str(db))
    conn.executescript(
        """
        CREATE TABLE amendment_acts (
          refid TEXT, filename TEXT, title TEXT, short_title TEXT,
          date_in_force TEXT, date_in_force_resolved TEXT, date_published TEXT,
          ministry TEXT, changes_to TEXT, journal_number TEXT, misc_info TEXT
        );
        INSERT INTO amendment_acts VALUES
          ('lov/2026-01-23-1','nl.xml','Lov om endringer','Endringslov',
           'Kongen bestemmer','','2026-01-23','HOD','lov/1999-07-02-64','2026-0032','');
        """
    )
    conn.commit()
    conn.close()

    out = tmp_path / "feed.xml"
    generate_atom_feed(str(snap), str(out))

    # Verifies well-formed XML and feed structure
    tree = ET.parse(out)
    root = tree.getroot()
    assert root.tag.endswith("feed")
    entries = [c for c in root if c.tag.endswith("entry")]
    assert len(entries) == 1


def test_generate_atom_feed_missing_db_is_noop(tmp_path, capsys):
    out = tmp_path / "feed.xml"
    generate_atom_feed(str(tmp_path / "noexist"), str(out))
    assert not out.exists()


def test_master_feed_includes_paragraph_categories(tmp_path):
    """When the amendments table has paragraph-level rows, the master feed's
    entries should include <category term="§ X-Y"> elements."""
    import sqlite3
    snap = tmp_path / "snap"
    snap.mkdir()
    db = sqlite3.connect(str(snap / "amendments.db"))
    db.execute("""
        CREATE TABLE amendment_acts (
            refid TEXT, filename TEXT, title TEXT, short_title TEXT,
            date_in_force TEXT, date_in_force_resolved TEXT,
            date_published TEXT, ministry TEXT, changes_to TEXT,
            journal_number TEXT, misc_info TEXT
        )
    """)
    db.execute("""
        CREATE TABLE amendments (
            id INTEGER, act_refid TEXT, change_type TEXT,
            target TEXT, target_law TEXT, instruction TEXT, new_text TEXT
        )
    """)
    db.execute(
        "INSERT INTO amendment_acts VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        ('lov/2024-06-21-42', 'a.xml', 'Endr. regnskapsloven', 'Bærekraft',
         '2024-11-01', '2024-11-01', '2024-06-21', 'Finansdepartementet',
         'lov/1998-07-17-56', '2024-0042', ''),
    )
    db.executemany(
        "INSERT INTO amendments VALUES (?,?,?,?,?,?,?)",
        [
            (1, 'lov/2024-06-21-42', 'change', '§ 1-2a', 'lov/1998-07-17-56', '§ 1-2a', ''),
            (2, 'lov/2024-06-21-42', 'change', '§ 7-25', 'lov/1998-07-17-56', '§ 7-25', ''),
        ],
    )
    db.commit()
    db.close()

    from lovdata_publisher.feed import generate_atom_feed
    out_path = tmp_path / "feed.xml"
    generate_atom_feed(snapshot_dir=str(snap), output_path=str(out_path))
    feed = out_path.read_text(encoding="utf-8")
    assert '<category term="§ 1-2a"' in feed
    assert '<category term="§ 7-25"' in feed
    assert '<category term="ministry:Finansdepartementet"' in feed
    assert '<category term="kind:lov"' in feed


def test_master_feed_works_without_amendments_table(tmp_path):
    """Older snapshots may not have the amendments table; feed should still
    render, just without paragraph categories."""
    import sqlite3
    snap = tmp_path / "snap"
    snap.mkdir()
    db = sqlite3.connect(str(snap / "amendments.db"))
    db.execute("""
        CREATE TABLE amendment_acts (
            refid TEXT, filename TEXT, title TEXT, short_title TEXT,
            date_in_force TEXT, date_in_force_resolved TEXT,
            date_published TEXT, ministry TEXT, changes_to TEXT,
            journal_number TEXT, misc_info TEXT
        )
    """)
    db.execute(
        "INSERT INTO amendment_acts VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        ('lov/2024-06-21-42', 'a.xml', 'X', 'X', '2024-11-01', '2024-11-01',
         '2024-06-21', 'FIN', 'lov/1998-07-17-56', '2024-0042', ''),
    )
    db.commit()
    db.close()

    from lovdata_publisher.feed import generate_atom_feed
    out_path = tmp_path / "feed.xml"
    generate_atom_feed(snapshot_dir=str(snap), output_path=str(out_path))
    feed = out_path.read_text(encoding="utf-8")
    # No paragraph categories, but kind+ministry still appear
    assert '<category term="kind:lov"' in feed
    assert '<category term="ministry:FIN"' in feed
