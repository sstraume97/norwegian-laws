# How to subscribe to regulatory changes

This repo publishes 2,700+ Atom feeds covering every Norwegian law and central regulation. This document shows how to wire them into common tools.

## Interactive: paste a law name, get the feed URL

[**Try the subscribe page →**](https://sondreskarsten.github.io/norwegian-laws/book/abonner.html) — type any law name or abbreviation (regnskapsloven, aml, pbl, …) and instantly see the feed URL with a copy button.

## Finding your feed URL

Every law gets a feed at a predictable URL. The pattern is:

```
https://sondreskarsten.github.io/norwegian-laws/feeds/lov-{YYYY-MM-DD-NN}.xml
https://sondreskarsten.github.io/norwegian-laws/feeds/forskrift-{YYYY-MM-DD-NN}.xml
```

Common laws:

| Law | Feed URL |
|---|---|
| Regnskapsloven (rskl) | `feeds/lov-1998-07-17-56.xml` |
| Aksjeloven (asl) | `feeds/lov-1997-06-13-44.xml` |
| Allmennaksjeloven (asal) | `feeds/lov-1997-06-13-45.xml` |
| Arbeidsmiljøloven (aml) | `feeds/lov-2005-06-17-62.xml` |
| Skatteloven (sktl) | `feeds/lov-1999-03-26-14.xml` |
| Konkursloven (kkl) | `feeds/lov-1984-06-08-58.xml` |
| Verdipapirhandelloven | `feeds/lov-2007-06-29-75.xml` |
| Finansforetaksloven | `feeds/lov-2015-04-10-17.xml` |
| Hvitvaskingsloven | `feeds/lov-2018-06-01-23.xml` |
| Personopplysningsloven (popplyl) | `feeds/lov-2018-06-15-38.xml` |

For other laws, browse the [feed index](https://sondreskarsten.github.io/norwegian-laws/feeds/) or use [`laws.json`](https://sondreskarsten.github.io/norwegian-laws/laws.json) to look up a `refid` programmatically.

You can also subscribe by topic or ministry:

```
feeds/topic-skatte--og-avgiftsrett.xml
feeds/topic-bank-finans-og-regnskapsrett.xml
feeds/topic-arbeidsrett.xml
feeds/dept-finansdepartementet.xml
feeds/dept-justis--og-beredskapsdepartementet.xml
```

## RSS / Atom readers

Most modern feed readers accept Atom 1.0. Paste the feed URL into:

- **Feedly** — Add Content → enter URL
- **Inoreader** — Add Subscription → Feed URL
- **NetNewsWire** (macOS/iOS, free) — File → New Feed
- **Thunderbird** — Account Settings → Add → Feeds
- **Microsoft Outlook** — RSS Feeds → Add a new RSS Feed
- **NewsBlur** — Add a Site

## GitHub Actions

React to law changes from inside your own GitHub repository.

**The easiest path: copy the [reusable workflow template](https://github.com/sondreskarsten/norwegian-laws/blob/main/examples/github-action-watcher/.github/workflows/watch-norwegian-laws.yml)** and edit the `feeds:` matrix. It polls Atom feeds every weekday morning, opens a GitHub Issue when amendments are found (with affected paragraphs broken out as `<category>` elements), and persists state so it never refires for the same amendment.

```yaml
matrix:
  feed:
    - name: "Regnskapsloven"
      url: "https://sondreskarsten.github.io/norwegian-laws/feeds/lov-1998-07-17-56.xml"
    - name: "Skatteloven"
      url: "https://sondreskarsten.github.io/norwegian-laws/feeds/lov-1999-03-26-14.xml"
    # … as many as you like
```

See [examples/github-action-watcher/](https://github.com/sondreskarsten/norwegian-laws/tree/main/examples/github-action-watcher) for the full workflow file and per-feed setup guide.

For ad-hoc one-off checks (e.g. notify Slack instead of opening an issue), the inline approach still works:

```yaml
- name: Fetch and diff feed
  run: |
    curl -s https://sondreskarsten.github.io/norwegian-laws/feeds/lov-1998-07-17-56.xml > feed.xml
    LATEST=$(xmllint --xpath '//*[local-name()="entry"][1]/*[local-name()="updated"]/text()' feed.xml)
    if [ "$LATEST" != "$(cat .last-amendment 2>/dev/null)" ]; then
      echo "$LATEST" > .last-amendment
      echo "CHANGED=true" >> $GITHUB_ENV
    fi

- name: Notify Slack
  if: env.CHANGED == 'true'
  uses: rtCamp/action-slack-notify@v2
  env:
    SLACK_WEBHOOK: ${{ secrets.SLACK_WEBHOOK }}
    SLACK_MESSAGE: "Regnskapsloven was amended. Check the feed."
```

## Watch a file in this repo (GitHub UI)

If you'd rather use GitHub's built-in notification:

1. Visit [github.com/sondreskarsten/norwegian-laws](https://github.com/sondreskarsten/norwegian-laws)
2. Click **Watch → Custom**
3. Subscribe to **Pushes only**

You'll get an email for every weekly commit. Not as granular as per-law feeds, but works without any infrastructure.

## Slack — direct from RSS

Slack has built-in RSS support. In any channel:

```
/feed subscribe https://sondreskarsten.github.io/norwegian-laws/feeds/lov-1998-07-17-56.xml
```

New entries post as messages in that channel.

## Microsoft Teams

Power Automate (formerly Flow) has an RSS connector:

1. Create a flow with trigger **"When a feed item is published"**
2. Feed URL: `https://sondreskarsten.github.io/norwegian-laws/feeds/lov-1998-07-17-56.xml`
3. Action: Post a message in Teams channel

## n8n / Zapier / Make.com

Use any of these tools' built-in RSS triggers. They poll feeds on a schedule and fire workflows on new entries — without you needing to host anything.

## Python — poll and dedupe

```python
import feedparser
import json
import pathlib

URL = "https://sondreskarsten.github.io/norwegian-laws/feeds/lov-1998-07-17-56.xml"
state_file = pathlib.Path(".seen_amendments.json")
seen = json.loads(state_file.read_text()) if state_file.exists() else []

feed = feedparser.parse(URL)
new = [e for e in feed.entries if e.id not in seen]

for entry in new:
    print(f"New amendment: {entry.title}")
    print(f"  Date: {entry.updated}")
    print(f"  Link: {entry.link}")
    print(f"  Summary: {entry.summary}")
    seen.append(entry.id)

state_file.write_text(json.dumps(seen))
```

## Raw curl

```bash
curl -s https://sondreskarsten.github.io/norwegian-laws/feeds/lov-1998-07-17-56.xml | xmllint --format -
```

## API for batch lookup

To find the feed URL for any law programmatically:

```bash
curl -s https://sondreskarsten.github.io/norwegian-laws/laws.json | \
  jq '.[] | select(.korttittel | test("Regnskapsloven")) | "feeds/\(.path | sub("\\.md$"; ".xml") | sub("^lover/"; "") | sub("^forskrifter/"; ""))"'
```

Or use the feed manifest at `feeds/index.json`:

```bash
curl -s https://sondreskarsten.github.io/norwegian-laws/feeds/index.json | jq '.laws | keys' | head
```

## Feed format

Each feed is Atom 1.0. Each `<entry>` represents one amendment act:

```xml
<entry>
  <id>https://sondreskarsten.github.io/norwegian-laws/feeds/lov/1998-07-17-56/lov/2024-06-21-42</id>
  <title>Endringer i regnskapsloven (bærekraftsrapportering)</title>
  <link href="https://sondreskarsten.github.io/norwegian-laws/lover/lov-1998-07-17-56.html"/>
  <updated>2024-06-21T00:00:00Z</updated>
  <category term="§ 1-2a" label="§ 1-2a"/>
  <category term="§ 2-3" label="§ 2-3"/>
  <summary>Ikrafttredelse: 2024-11-01
Departement: Finansdepartementet
Endrer: lov/1998-07-17-56
Lovtidend: 2024-0042
Berørte paragrafer: § 1-2a, § 2-3</summary>
</entry>
```

The `<id>` includes both the *target* law refid and the *amendment act* refid, so consumers can deduplicate cleanly across multiple feeds.

The `<category>` elements list the specific paragraphs the amendment modifies. Feed readers and automation tools can filter on these — so a tax-advisor subscribed to regnskapsloven who only cares about § 7-25 (egenkapital) can ignore amendments that don't touch it. Filtering syntax depends on the reader:

- **Feedly**: rule-based filters on `category`
- **Inoreader**: built-in tag/category filters
- **Python feedparser**: `entry.tags[i].term`
- **xmllint**: `xpath '//atom:entry[atom:category/@term="§ 7-25"]'`

## Update cadence

Feeds are regenerated every Monday at 06:00 UTC from the latest Lovdata data. Norsk Lovtidend typically publishes amendment acts within days of Stortinget's vedtak. Expect lag from royal assent → Lovdata publication of 1–5 business days.

## Limits

- 50 most recent entries per feed (most laws are amended <50 times; this is rarely a constraint)
- For paragraph-level "what changed" view (the actual amendment instruction and new text), see the [endringshistorikk pages](https://sondreskarsten.github.io/norwegian-laws/historie/) — one per law, since 2001. Or filter feed entries by their `<category>` tags as shown above.

## Bulk download: JSONL manifests for programmatic consumption

For downstream automation that needs all amendments at once (data warehouses, compliance dashboards, internal CDC pipelines), download the JSON Lines manifests instead of scraping 2,627 XML feeds:

- **[amendment-acts.jsonl.gz](https://sondreskarsten.github.io/norwegian-laws/amendment-acts.jsonl.gz)** — one row per amendment act (~38,000 rows, ~3 MB compressed). Matches Atom feed entries 1:1.
- **[amendments.jsonl.gz](https://sondreskarsten.github.io/norwegian-laws/amendments.jsonl.gz)** — one row per (act, target_law, paragraph) triple (~90,000 rows, ~5 MB compressed). Finer-grained; suitable for paragraph-level queries.

Both are sorted newest-first, regenerated weekly, and identical in content to what you'd build by parsing every Atom feed. The `.gz` versions are 5–10× smaller; uncompressed `.jsonl` versions are also available at the same paths (drop `.gz`).

```bash
# Download both manifests
curl -sL https://sondreskarsten.github.io/norwegian-laws/amendments.jsonl.gz | gunzip > amendments.jsonl

# Find every amendment to regnskapsloven § 7-25 in the last 2 years
jq -c 'select(.target_law == "lov/1998-07-17-56"
            and .paragraph == "§ 7-25"
            and .date_published >= "2024-01-01")' amendments.jsonl

# Group amendments by ministry, 2026 only
jq -c 'select(.date_published >= "2026-01-01") | .ministry' amendments.jsonl | sort | uniq -c | sort -rn
```

Polars / DuckDB / pandas can read either file directly:

```python
import duckdb
duckdb.sql("""
    SELECT target_law, paragraph, COUNT(*) AS n
    FROM read_json_auto('amendments.jsonl')
    WHERE date_published >= '2024-01-01'
    GROUP BY 1, 2 ORDER BY n DESC LIMIT 20
""").show()
```
