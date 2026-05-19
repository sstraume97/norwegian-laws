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


def build_recent_block(db_path: str, limit: int = 8) -> str:
    """Return Markdown block of the N most recent amendment acts."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        SELECT refid, title, short_title, date_published,
               date_in_force, date_in_force_resolved, ministry, changes_to
        FROM amendment_acts
        WHERE date_published IS NOT NULL AND date_published != ''
        ORDER BY date_published DESC, date_in_force_resolved DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    conn.close()

    lines = ["| Date | Amendment | Targets |", "|---|---|---|"]
    for row in rows:
        date = row["date_published"][:10] if row["date_published"] else "—"
        title = row["short_title"] or row["title"] or row["refid"]
        # Truncate long titles
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
            stem = t.replace("/", "-")
            target_links.append(f"[`{t}`]({_law_url(t)})")
        if len(targets) > 3:
            target_links.append("…")
        targets_md = " ".join(target_links) if target_links else "—"

        lines.append(f"| {date} | {title_md} | {targets_md} |")

    return "\n".join(lines)


def update_readme(readme_path: str, db_path: str, limit: int = 8) -> bool:
    """Replace content between markers in README.md. Returns True if changed."""
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

    block = build_recent_block(db_path, limit=limit)
    replacement = f"{START_MARKER}\n{block}\n{END_MARKER}"
    pattern = re.escape(START_MARKER) + r".*?" + re.escape(END_MARKER)
    new_text = re.sub(pattern, replacement, original, flags=re.DOTALL)

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
