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
