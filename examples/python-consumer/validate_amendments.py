"""Stream amendments.jsonl.gz and validate each row against the schema.

Run: python validate_amendments.py
"""
from __future__ import annotations

import gzip
import json
import sys
import urllib.request

import jsonschema

SITE = "https://sondreskarsten.github.io/norwegian-laws"
JSONL_URL = f"{SITE}/amendments.jsonl.gz"
SCHEMA_URL = f"{SITE}/schemas/amendments.schema.json"


def main() -> int:
    print(f"Fetching schema from {SCHEMA_URL}")
    schema = json.loads(urllib.request.urlopen(SCHEMA_URL).read())
    validator = jsonschema.Draft202012Validator(schema)

    print(f"Streaming {JSONL_URL}")
    resp = urllib.request.urlopen(JSONL_URL)
    total = ok = invalid = 0
    failures: list[tuple[int, str]] = []
    with gzip.open(resp, mode="rt", encoding="utf-8") as fh:
        for total, line in enumerate(fh, start=1):
            obj = json.loads(line)
            try:
                validator.validate(obj)
                ok += 1
            except jsonschema.ValidationError as e:
                invalid += 1
                if len(failures) < 10:
                    failures.append((total, e.message))

    print(f"Validated {total:,} rows: {ok:,} valid, {invalid:,} invalid")
    if failures:
        print(f"First {len(failures)} failures:")
        for line_no, msg in failures:
            print(f"  line {line_no}: {msg[:120]}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
