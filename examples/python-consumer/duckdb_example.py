"""Load amendments.jsonl.gz directly into DuckDB and run analytical queries.

DuckDB reads JSON Lines (and gzipped JSON Lines) natively, so this is the
shortest path from the published manifest to interactive SQL.

Run:
    python duckdb_example.py
Requires:
    pip install duckdb requests
"""
from __future__ import annotations

import duckdb

SITE = "https://sondreskarsten.github.io/norwegian-laws"

# DuckDB can read remote gzipped JSONL over HTTPS via its httpfs extension.
# Loaded ad-hoc here rather than into a persistent file so the example
# stays self-contained.
con = duckdb.connect()
con.execute("INSTALL httpfs; LOAD httpfs;")

print("Top 10 most-amended laws in the last 5 years:")
top = con.execute(f"""
    SELECT target_law, COUNT(DISTINCT act_refid) AS n_acts, COUNT(*) AS n_changes
    FROM read_json_auto('{SITE}/amendments.jsonl.gz')
    WHERE date_published >= '2021-01-01'
      AND target_law LIKE 'lov/%'
    GROUP BY target_law
    ORDER BY n_acts DESC
    LIMIT 10
""").fetchall()
for refid, n_acts, n_changes in top:
    print(f"  {n_acts:3d} acts / {n_changes:4d} para-level changes  {refid}")

print()
print("Amendments per ministry in 2026:")
per_ministry = con.execute(f"""
    SELECT ministry, COUNT(DISTINCT act_refid) AS n_acts
    FROM read_json_auto('{SITE}/amendments.jsonl.gz')
    WHERE date_published >= '2026-01-01'
    GROUP BY ministry
    ORDER BY n_acts DESC
""").fetchall()
for ministry, n_acts in per_ministry:
    print(f"  {n_acts:4d}  {ministry}")

print()
print("Last 5 amendments to regnskapsloven (with new_text preview):")
rsk = con.execute(f"""
    SELECT date_published, act_refid, paragraph, change_type,
           substr(new_text, 1, 80) AS preview
    FROM read_json_auto('{SITE}/amendments.jsonl.gz')
    WHERE target_law = 'lov/1998-07-17-56'
    ORDER BY date_published DESC
    LIMIT 5
""").fetchall()
for date, act, para, ctype, preview in rsk:
    print(f"  {date}  {act}  {para or '—':12s}  ({ctype})")
    if preview:
        print(f"      {preview}...")
