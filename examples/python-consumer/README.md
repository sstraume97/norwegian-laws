# Python consumer example

Minimal scripts showing how to ingest the JSONL manifests and validate
each row against the published JSON Schema. All three scripts use
only-stdlib + one library dependency, so they should drop into any
existing data pipeline without conflicts.

## Files

- `validate_amendments.py` — stream `amendments.jsonl.gz`, validate each
  row against `amendments.schema.json`, print a summary. Catches schema
  drift before it propagates downstream.
- `query_amendments.py` — pull all amendments to a specific law +
  paragraph in a date range. Demonstrates the urllib + jsonlines
  pattern.
- `duckdb_example.py` — load the manifest directly into DuckDB and run
  three analytical queries (top-amended laws, ministry leaderboard,
  regnskapsloven change history). Shortest path from manifest to
  interactive SQL.
- `requirements.txt` — `jsonschema>=4.0` (Draft 2020-12 support),
  `duckdb>=0.9.0`

## Setup

```bash
pip install -r requirements.txt
```

## Validate

```bash
python validate_amendments.py
# → Validated 91,234 rows: 91,234 valid, 0 invalid
```

If validation ever produces invalid rows, the schema or the manifest
has drifted — open an issue at
<https://github.com/sondreskarsten/norwegian-laws/issues> with the
output.

## Query example

```bash
python query_amendments.py lov/1998-07-17-56 "§ 7-25" 2001-01-01
# → 1 amendment(s) to lov/1998-07-17-56 § 7-25 since 2001-01-01
#     2005-06-10  lov/2005-06-10-46  (change)
#       new_text: Opptjent egenkapital skal spesifiseres...
```

## DuckDB example

```bash
python duckdb_example.py
# → Top 10 most-amended laws in the last 5 years:
#     39 acts /  322 para-level changes  lov/1997-02-28-19   (folketrygdloven)
#     26 acts /  124 para-level changes  lov/2008-05-15-35   (utlendingsloven)
#     ...
```

DuckDB reads `read_json_auto('https://.../amendments.jsonl.gz')` natively
over HTTPS via the `httpfs` extension. Useful for ad-hoc analytics
without setting up a local pipeline.
