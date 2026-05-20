"""Update the 'Recent amendments' section of README.md from amendments.db.

Replaces content between two HTML comment markers with the N most recent
amendment acts. Designed to be run by the weekly workflow after the snapshot
is rebuilt, so README.md always reflects the latest legislative activity.

The README must contain these markers:
    <!-- RECENT_AMENDMENTS_START -->
    ...replaced content...
    <!-- RECENT_AMENDMENTS_END -->
"""
from __future__ import annotations

import re
import sqlite3
from pathlib import Path

START_MARKER = "<!-- RECENT_AMENDMENTS_START -->"
END_MARKER = "<!-- RECENT_AMENDMENTS_END -->"


def _law_url(refid: str) -> str:
    base = "https://sondreskarsten.github.io/norwegian-laws"
    if refid.startswith("forskrift/"):
        return f"{base}/forskrifter/forskrift-{refid.split('/', 1)[1]}.html"
    if refid.startswith("lov/"):
        return f"{base}/lover/lov-{refid.split('/', 1)[1]}.html"
    return base


def build_recent_block(db_path: str, limit_lover: int = 5, limit_forskrift: int = 5) -> str:
    """Return Markdown block of recent amendment acts, split lover vs forskrifter.

    Tax advisors, auditors, and compliance teams generally care more about
    formal lover than forskrifter, so we surface the most recent lover first
    and follow with the most recent forskrifter.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    def fetch(kind_prefix: str, limit: int) -> list:
        return conn.execute(
            """
            SELECT refid, title, short_title, date_published,
                   date_in_force, date_in_force_resolved, ministry, changes_to
            FROM amendment_acts
            WHERE date_published IS NOT NULL AND date_published != ''
                  AND refid LIKE ?
                  AND changes_to LIKE ?
            ORDER BY date_published DESC, date_in_force_resolved DESC
            LIMIT ?
            """,
            (f"{kind_prefix}/%", f"{kind_prefix}/%", limit),
        ).fetchall()

    lover_rows = fetch("lov", limit_lover)
    forskrift_rows = fetch("forskrift", limit_forskrift)
    conn.close()

    def render_table(rows) -> list[str]:
        lines = ["| Date | Amendment | Targets |", "|---|---|---|"]
        for row in rows:
            date = row["date_published"][:10] if row["date_published"] else "—"
            title = row["short_title"] or row["title"] or row["refid"]
            if len(title) > 70:
                title = title[:67] + "…"
            title_md = title.replace("|", "\\|")
            targets = (row["changes_to"] or "").split(",")
            target_links = []
            seen = set()
            for t in targets[:3]:
                t = t.strip()
                if not t or t in seen:
                    continue
                seen.add(t)
                target_links.append(f"[`{t}`]({_law_url(t)})")
            if len([t for t in targets if t.strip()]) > 3:
                target_links.append("…")
            targets_md = " ".join(target_links) if target_links else "—"
            lines.append(f"| {date} | {title_md} | {targets_md} |")
        return lines

    sections = []
    if lover_rows:
        sections.append("**Lover (endringslover):**")
        sections.append("")
        sections.extend(render_table(lover_rows))
        sections.append("")
    if forskrift_rows:
        sections.append("**Forskrifter:**")
        sections.append("")
        sections.extend(render_table(forskrift_rows))

    return "\n".join(sections)


def update_readme(readme_path: str, db_path: str, limit_lover: int = 5, limit_forskrift: int = 5) -> bool:
    """Replace content between markers in README.md. Returns True if changed.

    Also refreshes the dated_amendments shield badge URL and the
    'Backdated git history' row in the feature table, both of which carry a
    hardcoded amendment count that grows over time.
    """
    path = Path(readme_path)
    if not path.exists():
        print(f"  {path} not found")
        return False
    if not Path(db_path).exists():
        print(f"  {db_path} not found")
        return False

    original = path.read_text(encoding="utf-8")
    if START_MARKER not in original or END_MARKER not in original:
        print(f"  Markers not found in {path}, skipping")
        return False

    block = build_recent_block(db_path, limit_lover=limit_lover, limit_forskrift=limit_forskrift)
    replacement = f"{START_MARKER}\n{block}\n{END_MARKER}"
    pattern = re.escape(START_MARKER) + r".*?" + re.escape(END_MARKER)
    new_text = re.sub(pattern, replacement, original, flags=re.DOTALL)

    # Refresh the dated_amendments badge + feature-table row. The badge URL
    # uses URL-encoded comma '%2C'; the table row uses a plain comma. Both
    # carry the same number which is the count of amendment acts in the DB.
    conn = sqlite3.connect(db_path)
    try:
        n_acts = conn.execute("SELECT COUNT(*) FROM amendment_acts").fetchone()[0]
    finally:
        conn.close()
    badge_pattern = r'dated_amendments-[\d%C]+-ba0c2f'
    new_text = re.sub(
        badge_pattern,
        f"dated_amendments-{n_acts:,}".replace(",", "%2C") + "-ba0c2f",
        new_text,
    )
    # Feature-table row: "31,459 amendment acts as backdated commits"
    new_text = re.sub(
        r"\d{1,3}(?:,\d{3})* amendment acts as backdated commits",
        f"{n_acts:,} amendment acts as backdated commits",
        new_text,
    )

    if new_text == original:
        return False

    path.write_text(new_text, encoding="utf-8")
    return True


if __name__ == "__main__":
    import sys
    readme = sys.argv[1] if len(sys.argv) > 1 else "README.md"
    db = sys.argv[2] if len(sys.argv) > 2 else "snapshot/amendments.db"
    changed = update_readme(readme, db)
    print(f"  README updated: {changed}")
