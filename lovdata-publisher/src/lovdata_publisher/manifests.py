"""Generate JSON Lines manifests for programmatic consumption.

Two files at the deployed site root:

- amendment-acts.jsonl(.gz) — one row per amendment act (~38,672 rows). Coarser
  grain; matches Atom feed entries 1:1.
- amendments.jsonl(.gz) — one row per (act, target_law, paragraph) triple
  (~90,000 rows). Finer grain; suitable for "did any amendment touch §7-25
  in regnskapsloven since 2023?" queries.

Both are sorted newest-first by date_published. Any downstream pipeline can
ingest these without parsing 2,627 XML files.

Files are written to the deployed site (_site/), NOT committed to git, since
the uncompressed sizes (~30MB and ~40MB) would bloat the repo on every
regeneration. The .gz versions (~3-5MB each) are the recommended download.
"""
from __future__ import annotations

import gzip
import json
import re
import sqlite3
from pathlib import Path


def _normalize_paragraph_ref(target: str, instruction: str) -> str:
    """Extract canonical paragraph ref. Mirrors feeds._normalize_paragraph_ref."""
    para_re = re.compile(r'§§?\s*(\d+\s*[-–]\s*\d+(?:[a-z](?=$|[^a-zæøåA-ZÆØÅ]))?)')
    text = (target or "").strip()
    if not text or text.lower().startswith("kapittel") or text.lower().startswith("del "):
        m = para_re.search(instruction or "")
        if m:
            return f"§ {re.sub(r'\\s+', '-', m.group(1).strip())}"
        return ""
    m = para_re.match(text)
    if m:
        return f"§ {re.sub(r'\\s+', '-', m.group(1).strip())}"
    return ""


def _open_pair(out_path: Path):
    """Open uncompressed + gzipped file handles for parallel writing."""
    plain = out_path.open("w", encoding="utf-8")
    gz = gzip.open(str(out_path) + ".gz", "wt", encoding="utf-8")
    return plain, gz


def _close_pair(plain, gz):
    plain.close()
    gz.close()


def generate_amendment_acts_jsonl(db_path: str, output_path: str) -> int:
    """Write JSON Lines of amendment acts, newest first. Writes both .jsonl and .jsonl.gz."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        SELECT refid, title, short_title, date_in_force, date_in_force_resolved,
               date_published, ministry, changes_to, journal_number, misc_info,
               is_deferred, amendment_count
        FROM amendment_acts
        WHERE date_published IS NOT NULL AND date_published != ''
        ORDER BY date_published DESC, date_in_force_resolved DESC, refid DESC
        """
    ).fetchall()
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    plain, gz = _open_pair(out)
    try:
        for r in rows:
            targets = [t.strip() for t in (r["changes_to"] or "").split(",") if t.strip()]
            obj = {
                "refid": r["refid"],
                "title": r["title"],
                "short_title": r["short_title"] or None,
                "ministry": r["ministry"] or None,
                "date_published": r["date_published"][:10] if r["date_published"] else None,
                "date_in_force": r["date_in_force"] or None,
                "date_in_force_resolved": r["date_in_force_resolved"] or None,
                "is_deferred": bool(r["is_deferred"]),
                "journal_number": r["journal_number"] or None,
                "amendment_count": r["amendment_count"],
                "targets": targets,
                "misc_info": r["misc_info"][:500] if r["misc_info"] else None,
            }
            line = json.dumps(obj, ensure_ascii=False) + "\n"
            plain.write(line)
            gz.write(line)
    finally:
        _close_pair(plain, gz)
    conn.close()
    return len(rows)


def generate_amendments_jsonl(db_path: str, output_path: str) -> int:
    """Write JSON Lines of paragraph-level amendments, newest first.

    Joined with amendment_acts so each row has the publish/in-force dates
    needed to filter by time without a second lookup.

    Writes both .jsonl and .jsonl.gz.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # amendments table may not exist on older snapshots
    if not conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='amendments'"
    ).fetchone():
        print("  amendments table missing, skipping amendments.jsonl")
        conn.close()
        return 0

    rows = conn.execute(
        """
        SELECT a.id, a.act_refid, a.change_type, a.target, a.target_law, a.instruction,
               ac.title AS act_title, ac.short_title AS act_short_title,
               ac.ministry, ac.date_published, ac.date_in_force,
               ac.date_in_force_resolved, ac.journal_number
        FROM amendments a
        LEFT JOIN amendment_acts ac ON a.act_refid = ac.refid
        WHERE a.target_law IS NOT NULL AND a.target_law != ''
        ORDER BY ac.date_published DESC, a.act_refid DESC, a.id ASC
        """
    ).fetchall()
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    plain, gz = _open_pair(out)
    n = 0
    try:
        for r in rows:
            paragraph = _normalize_paragraph_ref(r["target"] or "", r["instruction"] or "")
            obj = {
                "act_refid": r["act_refid"],
                "act_title": r["act_short_title"] or r["act_title"],
                "target_law": r["target_law"],
                "target": r["target"] or None,
                "paragraph": paragraph or None,
                "change_type": r["change_type"] or None,
                "instruction": (r["instruction"] or "")[:200] or None,
                "ministry": r["ministry"] or None,
                "date_published": r["date_published"][:10] if r["date_published"] else None,
                "date_in_force": r["date_in_force"] or None,
                "date_in_force_resolved": r["date_in_force_resolved"] or None,
                "journal_number": r["journal_number"] or None,
            }
            line = json.dumps(obj, ensure_ascii=False) + "\n"
            plain.write(line)
            gz.write(line)
            n += 1
    finally:
        _close_pair(plain, gz)
    conn.close()
    return n


def generate_manifests(db_path: str, output_dir: str) -> tuple[int, int]:
    """Generate both manifests. Returns (acts_count, amendments_count)."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    acts_n = generate_amendment_acts_jsonl(db_path, str(out / "amendment-acts.jsonl"))
    print(f"  Wrote amendment-acts.jsonl with {acts_n} rows")
    amendments_n = generate_amendments_jsonl(db_path, str(out / "amendments.jsonl"))
    print(f"  Wrote amendments.jsonl with {amendments_n} rows")
    return acts_n, amendments_n


if __name__ == "__main__":
    import sys
    db = sys.argv[1] if len(sys.argv) > 1 else "snapshot/amendments.db"
    out = sys.argv[2] if len(sys.argv) > 2 else "."
    generate_manifests(db, out)
