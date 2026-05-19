"""Tests for manifests.py — JSONL programmatic-consumption files."""
import json
import sqlite3
from pathlib import Path

import pytest

from lovdata_publisher.manifests import (
    generate_amendment_acts_jsonl,
    generate_amendments_jsonl,
    generate_manifests,
)


def _make_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "amendments.db"
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE amendment_acts (
            refid TEXT, filename TEXT, title TEXT, short_title TEXT,
            date_in_force TEXT, date_in_force_resolved TEXT,
            is_deferred INTEGER, date_published TEXT, ministry TEXT,
            changes_to TEXT, misc_info TEXT, journal_number TEXT,
            amendment_count INTEGER
        )
    """)
    conn.execute("""
        CREATE TABLE amendments (
            id INTEGER, act_refid TEXT, change_type TEXT,
            target TEXT, target_law TEXT, instruction TEXT, new_text TEXT
        )
    """)
    conn.executemany(
        "INSERT INTO amendment_acts VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        [
            ('lov/2024-06-21-42', 'a.xml', 'Endr i regnskapsloven', 'Bærekraft',
             '2024-11-01', '2024-11-01', 0, '2024-06-21', 'FIN',
             'lov/1998-07-17-56', '', '2024-0042', 2),
            ('lov/2023-01-01-1', 'b.xml', 'Eldre endring', 'Eldre',
             '2023-01-01', '2023-01-01', 0, '2023-01-01', 'FIN',
             'lov/1998-07-17-56', '', '2023-0001', 1),
        ],
    )
    conn.executemany(
        "INSERT INTO amendments VALUES (?,?,?,?,?,?,?)",
        [
            (1, 'lov/2024-06-21-42', 'change', '§ 1-2a', 'lov/1998-07-17-56',
             '§ 1-2a skal lyde:', 'Bestemmelsene ...'),
            (2, 'lov/2024-06-21-42', 'change', '§ 2-3', 'lov/1998-07-17-56',
             '§ 2-3 skal lyde:', 'Store foretak ...'),
            (3, 'lov/2023-01-01-1', 'change', 'kapittel 9', 'lov/1998-07-17-56',
             '§ 9-1 skal lyde:', ''),
        ],
    )
    conn.commit()
    conn.close()
    return db_path


def test_amendment_acts_jsonl_newest_first(tmp_path):
    db = _make_db(tmp_path)
    out = tmp_path / "acts.jsonl"
    n = generate_amendment_acts_jsonl(str(db), str(out))
    assert n == 2
    lines = out.read_text(encoding="utf-8").strip().split("\n")
    rows = [json.loads(line) for line in lines]
    assert rows[0]["refid"] == "lov/2024-06-21-42"
    assert rows[0]["date_published"] == "2024-06-21"
    assert rows[0]["amendment_count"] == 2
    assert rows[0]["targets"] == ["lov/1998-07-17-56"]
    assert rows[1]["refid"] == "lov/2023-01-01-1"


def test_amendments_jsonl_includes_paragraph_and_joined_dates(tmp_path):
    db = _make_db(tmp_path)
    out = tmp_path / "amendments.jsonl"
    n = generate_amendments_jsonl(str(db), str(out))
    assert n == 3
    lines = out.read_text(encoding="utf-8").strip().split("\n")
    rows = [json.loads(line) for line in lines]
    # All should have act-level date filled in
    for r in rows:
        assert r["date_published"] is not None
        assert r["target_law"] == "lov/1998-07-17-56"
    # Paragraph extraction worked
    paragraphs = {r["paragraph"] for r in rows}
    assert "§ 1-2a" in paragraphs
    assert "§ 2-3" in paragraphs
    assert "§ 9-1" in paragraphs  # extracted from instruction
    # Newest first
    assert rows[0]["date_published"] == "2024-06-21"


def test_amendments_jsonl_handles_missing_table(tmp_path):
    """Older snapshots may lack the amendments table."""
    db = tmp_path / "amendments.db"
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE amendment_acts (refid TEXT, date_published TEXT, title TEXT, short_title TEXT, date_in_force TEXT, date_in_force_resolved TEXT, is_deferred INTEGER, ministry TEXT, changes_to TEXT, misc_info TEXT, journal_number TEXT, amendment_count INTEGER, filename TEXT)")
    conn.commit()
    conn.close()
    out = tmp_path / "amendments.jsonl"
    n = generate_amendments_jsonl(str(db), str(out))
    assert n == 0


def test_generate_manifests_writes_both(tmp_path):
    db = _make_db(tmp_path)
    out = tmp_path / "out"
    acts_n, amendments_n = generate_manifests(str(db), str(out))
    assert acts_n == 2
    assert amendments_n == 3
    assert (out / "amendment-acts.jsonl").exists()
    assert (out / "amendments.jsonl").exists()


def test_jsonl_lines_are_valid_json(tmp_path):
    """Every line must round-trip through json.loads."""
    db = _make_db(tmp_path)
    out = tmp_path / "acts.jsonl"
    generate_amendment_acts_jsonl(str(db), str(out))
    for line in out.read_text(encoding="utf-8").strip().split("\n"):
        json.loads(line)  # raises if invalid


def test_manifests_also_write_gz(tmp_path):
    """Each .jsonl file should have a sibling .jsonl.gz with identical content."""
    import gzip
    db = _make_db(tmp_path)
    out = tmp_path / "acts.jsonl"
    generate_amendment_acts_jsonl(str(db), str(out))
    gz_path = tmp_path / "acts.jsonl.gz"
    assert gz_path.exists()
    plain_content = out.read_text(encoding="utf-8")
    with gzip.open(gz_path, "rt", encoding="utf-8") as f:
        gz_content = f.read()
    assert plain_content == gz_content
    # And gz must be smaller (compression actually working)
    assert gz_path.stat().st_size < out.stat().st_size
