"""Tests for readme_updater.py."""
import sqlite3
from pathlib import Path

import pytest

from lovdata_publisher.readme_updater import (
    build_recent_block,
    update_readme,
    START_MARKER,
    END_MARKER,
)


def _make_db(tmp_path):
    db_path = tmp_path / "amendments.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("""
        CREATE TABLE amendment_acts (
            refid TEXT, filename TEXT, title TEXT, short_title TEXT,
            date_in_force TEXT, date_in_force_resolved TEXT,
            date_published TEXT, ministry TEXT, changes_to TEXT,
            journal_number TEXT, misc_info TEXT
        )
    """)
    conn.executemany(
        "INSERT INTO amendment_acts VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        [
            ('lov/2026-05-15-1', 'nl.xml', 'Newest Amendment', 'Newest',
             '2026-06-01', '2026-06-01', '2026-05-15', 'FIN',
             'lov/1998-07-17-56', '2026-0500', ''),
            ('lov/2026-04-10-1', 'nl.xml', 'Older Amendment', 'Older',
             '2026-05-01', '2026-05-01', '2026-04-10', 'FIN',
             'lov/1997-06-13-44,lov/1998-07-17-56', '2026-0400', ''),
            ('lov/2026-03-01-1', 'nl.xml', 'Oldest', 'Oldest',
             '2026-04-01', '2026-04-01', '2026-03-01', 'JD',
             'lov/2005-06-17-62', '2026-0300', ''),
        ],
    )
    conn.commit()
    conn.close()
    return db_path


def test_build_recent_block_returns_table(tmp_path):
    db = _make_db(tmp_path)
    block = build_recent_block(str(db), limit=2)
    assert "| Date | Amendment | Targets |" in block
    assert "Newest" in block
    assert "Older" in block
    # Limit honored
    assert "Oldest" not in block


def test_build_recent_block_orders_newest_first(tmp_path):
    db = _make_db(tmp_path)
    block = build_recent_block(str(db), limit=3)
    lines = block.splitlines()
    # First data row should be 2026-05-15 (Newest)
    assert "2026-05-15" in lines[2]
    assert "Newest" in lines[2]


def test_build_recent_block_truncates_long_titles(tmp_path):
    db_path = tmp_path / "amendments.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("""
        CREATE TABLE amendment_acts (
            refid TEXT, filename TEXT, title TEXT, short_title TEXT,
            date_in_force TEXT, date_in_force_resolved TEXT,
            date_published TEXT, ministry TEXT, changes_to TEXT,
            journal_number TEXT, misc_info TEXT
        )
    """)
    long_title = "A" * 100
    conn.execute(
        "INSERT INTO amendment_acts VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        ('lov/2026-01-01-1', 'nl.xml', long_title, '',
         '2026-01-01', '2026-01-01', '2026-01-01', 'FIN',
         'lov/1998-07-17-56', '2026-0001', ''),
    )
    conn.commit()
    conn.close()
    block = build_recent_block(str(db_path))
    assert "…" in block
    # No raw 100-char title in the block
    assert "A" * 80 not in block


def test_update_readme_replaces_block(tmp_path):
    db = _make_db(tmp_path)
    readme = tmp_path / "README.md"
    readme.write_text(
        f"# Title\n\nIntro text.\n\n"
        f"{START_MARKER}\nold content\n{END_MARKER}\n\n"
        f"Footer.\n",
        encoding="utf-8",
    )
    changed = update_readme(str(readme), str(db))
    assert changed
    text = readme.read_text(encoding="utf-8")
    assert "old content" not in text
    assert "Newest" in text
    assert "# Title" in text
    assert "Footer." in text
    # Markers preserved
    assert START_MARKER in text
    assert END_MARKER in text


def test_update_readme_no_change_returns_false(tmp_path):
    db = _make_db(tmp_path)
    readme = tmp_path / "README.md"
    readme.write_text(
        f"# Title\n{START_MARKER}\n{END_MARKER}\n",
        encoding="utf-8",
    )
    # First call: changes
    assert update_readme(str(readme), str(db))
    # Second call: no change
    assert not update_readme(str(readme), str(db))


def test_update_readme_skips_missing_markers(tmp_path):
    db = _make_db(tmp_path)
    readme = tmp_path / "README.md"
    readme.write_text("# Just a plain README without markers\n", encoding="utf-8")
    assert not update_readme(str(readme), str(db))
    # File unchanged
    assert readme.read_text(encoding="utf-8") == "# Just a plain README without markers\n"


def test_update_readme_handles_missing_db(tmp_path):
    readme = tmp_path / "README.md"
    readme.write_text(f"{START_MARKER}\nold\n{END_MARKER}", encoding="utf-8")
    assert not update_readme(str(readme), str(tmp_path / "no-db.db"))


def test_update_readme_handles_missing_readme(tmp_path):
    db = _make_db(tmp_path)
    assert not update_readme(str(tmp_path / "no-readme.md"), str(db))
