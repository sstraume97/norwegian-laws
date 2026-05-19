# Python consumer example

Minimal scripts showing how to ingest the JSONL manifests and validate
each row against the published JSON Schema.

## Files

- `validate_amendments.py` — stream `amendments.jsonl.gz`, validate each
  row against `amendments.schema.json`, print a summary
- `query_amendments.py` — pull all amendments to a specific law +
  paragraph in a date range
- `requirements.txt` — `jsonschema>=4.0` (Draft 2020-12 support)

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
