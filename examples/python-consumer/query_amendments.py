"""Stream amendments.jsonl.gz and print all matching rows.

Run: python query_amendments.py <target_law> <paragraph> [from_date]

Example:
    python query_amendments.py lov/1998-07-17-56 "§ 7-25" 2020-01-01
"""
from __future__ import annotations

import gzip
import json
import sys
import urllib.request

JSONL_URL = "https://sondreskarsten.github.io/norwegian-laws/amendments.jsonl.gz"


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print("usage: query_amendments.py <target_law> <paragraph> [from_date]",
              file=sys.stderr)
        return 2
    target_law = argv[1]
    paragraph = argv[2]
    from_date = argv[3] if len(argv) > 3 else "2001-01-01"

    resp = urllib.request.urlopen(JSONL_URL)
    matches: list[dict] = []
    with gzip.open(resp, mode="rt", encoding="utf-8") as fh:
        for line in fh:
            obj = json.loads(line)
            if (obj.get("target_law") == target_law
                    and obj.get("paragraph") == paragraph
                    and (obj.get("date_published") or "") >= from_date):
                matches.append(obj)

    print(f"{len(matches)} amendment(s) to {target_law} {paragraph} since {from_date}\n")
    for m in matches:
        print(f"  {m['date_published']}  {m['act_refid']}  ({m['change_type']})")
        if m.get("new_text"):
            preview = m["new_text"][:120].replace("\n", " ")
            print(f"    new_text: {preview}...")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
