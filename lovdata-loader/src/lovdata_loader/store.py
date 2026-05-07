"""Serialize parsed data into a snapshot directory.

A snapshot is the stable intermediate format between lovdata-loader and
lovdata-publisher. It consists of:
  - laws/<refid>.json   — one JSON file per law (structured, not Markdown)
  - amendments.db       — SQLite database of amendment acts
  - manifest.json       — metadata about this snapshot
"""
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from . import __version__
from .models import AmendmentActData, LawData, Manifest
from .parser import parse_effective_date, parse_publication_date


def init_db(db_path: str) -> sqlite3.Connection:
    """Initialize the amendments SQLite database."""
    conn = sqlite3.connect(db_path)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS amendment_acts (
            refid TEXT PRIMARY KEY,
            filename TEXT,
            title TEXT,
            short_title TEXT,
            date_in_force TEXT,
            date_in_force_resolved TEXT,
            is_deferred INTEGER,
            date_published TEXT,
            ministry TEXT,
            changes_to TEXT,
            misc_info TEXT,
            journal_number TEXT,
            amendment_count INTEGER
        );
        CREATE TABLE IF NOT EXISTS amendments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            act_refid TEXT REFERENCES amendment_acts(refid),
            change_type TEXT,
            target TEXT,
            target_law TEXT,
            instruction TEXT,
            new_text TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_amendments_act ON amendments(act_refid);
        CREATE INDEX IF NOT EXISTS idx_acts_date ON amendment_acts(date_in_force_resolved);
        CREATE INDEX IF NOT EXISTS idx_amendments_law ON amendments(target_law);
    """)
    return conn


def store_amendment_act(conn: sqlite3.Connection, act: AmendmentActData):
    """Store a single amendment act and its amendments in SQLite."""
    effective_date, is_deferred = parse_effective_date(
        act.date_in_force, act.date_published
    )
    pub_date = parse_publication_date(act.date_published)

    # Delete existing amendment rows first to avoid duplicates on re-run.
    # INSERT OR REPLACE on the parent table replaces the act row, but
    # child rows in amendments would otherwise accumulate.
    conn.execute("DELETE FROM amendments WHERE act_refid = ?", (act.refid,))

    conn.execute(
        """
        INSERT OR REPLACE INTO amendment_acts
        (refid, filename, title, short_title, date_in_force, date_in_force_resolved,
         is_deferred, date_published, ministry, changes_to, misc_info, journal_number,
         amendment_count)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            act.refid,
            act.filename,
            act.title,
            act.short_title,
            act.date_in_force,
            effective_date,
            int(is_deferred),
            pub_date,
            act.ministry,
            ",".join(act.changes_to),
            act.misc_info,
            act.journal_number,
            len(act.amendments),
        ),
    )

    for a in act.amendments:
        conn.execute(
            """
            INSERT INTO amendments (act_refid, change_type, target, target_law, instruction, new_text)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (act.refid, a.change_type, a.target, a.target_law, a.instruction, a.new_text),
        )


def write_snapshot(
    output_dir: str,
    laws: list[LawData],
    amendment_acts: list[AmendmentActData],
    gjeldende_archive: str = "",
    lovtidend_archives: list[str] | None = None,
) -> str:
    """Write a snapshot directory from parsed data.

    Creates:
      output_dir/
      ├── manifest.json
      ├── laws/
      │   ├── lov-1814-05-17.json
      │   └── ...
      └── amendments.db

    Returns the snapshot directory path.
    """
    if lovtidend_archives is None:
        lovtidend_archives = []

    root = Path(output_dir)
    laws_dir = root / "laws"
    laws_dir.mkdir(parents=True, exist_ok=True)

    # Purge stale law JSON files so the snapshot is a true point-in-time
    # picture. Without this, laws removed from source data would linger
    # and the publisher would still export them.
    for stale in laws_dir.glob("*.json"):
        stale.unlink()

    # Write law JSON files
    for law in laws:
        safe_name = law.refid.replace("/", "-")
        path = laws_dir / f"{safe_name}.json"
        path.write_text(law.to_json(), encoding="utf-8")

    # Write amendments to SQLite
    db_path = str(root / "amendments.db")
    conn = init_db(db_path)
    total_amendments = 0
    for act in amendment_acts:
        store_amendment_act(conn, act)
        total_amendments += len(act.amendments)
    conn.commit()
    conn.close()

    # Write manifest
    manifest = Manifest(
        version=1,
        created_at=datetime.now(timezone.utc).isoformat(),
        loader_version=__version__,
        gjeldende_archive=gjeldende_archive,
        lovtidend_archives=lovtidend_archives,
        law_count=len(laws),
        amendment_act_count=len(amendment_acts),
        amendment_count=total_amendments,
    )
    (root / "manifest.json").write_text(manifest.to_json(), encoding="utf-8")

    return str(root)


def read_laws_from_snapshot(snapshot_dir: str) -> list[LawData]:
    """Read all law JSON files from a snapshot directory."""
    laws_dir = Path(snapshot_dir) / "laws"
    laws = []
    for path in sorted(laws_dir.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        laws.append(LawData.from_dict(data))
    return laws


def read_manifest(snapshot_dir: str) -> Manifest:
    """Read the manifest from a snapshot directory."""
    path = Path(snapshot_dir) / "manifest.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    return Manifest.from_dict(data)
