# Norges Lover

All Norwegian laws and central regulations as searchable, diffable Markdown — updated weekly from [Lovdata's open API](https://api.lovdata.no/).

**[Browse the site →](https://sondreskarsten.github.io/norwegian-laws/)**

## What you can do

**Browse** — [4,200+ laws and regulations](https://sondreskarsten.github.io/norwegian-laws/) organized by ministry and legal area, with full-text search and cross-references between laws.

**Diff** — [Compare any law across time periods](https://sondreskarsten.github.io/norwegian-laws/book/diff.html). Select two versions and see exactly what changed, word by word.

**Search** — [Find laws by title, abbreviation, or keyword](https://sondreskarsten.github.io/norwegian-laws/book/sok.html). Supports common abbreviations like `aml` (arbeidsmiljøloven), `asl` (aksjeloven), `pbl` (plan- og bygningsloven).

**Git log as legislative history** — Every amendment act is a backdated commit on the [`law-history`](https://github.com/sondreskarsten/norwegian-laws/tree/law-history) branch. Run `git log` to see when and how a law changed:

```bash
git clone -b law-history https://github.com/sondreskarsten/norwegian-laws.git
cd norwegian-laws

# Legislative history of regnskapsloven
git log --oneline -- lover/lov-1998-07-17-56.md

# What changed in Norwegian law between 2023 and 2024
git diff v2023 v2024 --stat

# State of all laws as of January 2020
git checkout v2020
```

**Subscribe** — [Atom feed](https://sondreskarsten.github.io/norwegian-laws/feed.xml) for recent changes.

## Corpus

| | Count | Updated |
|---|---|---|
| Formal laws (gjeldende lover) | ~783 | Weekly |
| Central regulations (sentrale forskrifter) | ~3,421 | Weekly |
| Amendment commits on `law-history` | 16,000+ | Weekly |
| Yearly version tags | `v2000` – `v2027` | Weekly |

## File format

Each law is a Markdown file with YAML frontmatter:

```yaml
---
tittel: "Lov om årsregnskap m.v. (regnskapsloven)"
korttittel: "Regnskapsloven – rskl"
refid: "lov/1998-07-17-56"
eli: "/eli/lov/1998/07/17/56"
departement: "Finansdepartementet"
rettsomrade: "Bank, finans og regnskapsrett>Regnskap"
ikrafttredelse: "1999-01-01"
sist-endret: "lov/2025-06-20-106"
sist-endret-ikrafttredelse: "2026-01-01"
---
```

The body preserves Lovdata's full structure: chapters, sections, paragraphs, list items, and amendment footnotes.

A machine-readable [`laws.json`](https://sondreskarsten.github.io/norwegian-laws/laws.json) index covers all 4,200+ documents with metadata, common abbreviations, and links.

## For developers

The pipeline has two packages:

- **lovdata-loader** — downloads Lovdata XML archives and parses them into structured JSON + SQLite
- **lovdata-publisher** — formats JSON → Markdown, generates the Quarto site, and builds the backdated git history via `git fast-import`

```bash
pip install -e lovdata-loader/ -e lovdata-publisher/

lovdata-load --download --output snapshot
lovdata-publish --snapshot snapshot --output . --quarto
```

The `law-history` branch uses git-LFS. Install `git-lfs` before cloning that branch.

Weekly automation runs via GitHub Actions: download → parse → format → render → deploy.

## Data source and license

Contains data under the [Norwegian Licence for Open Government Data (NLOD) 2.0](https://data.norge.no/nlod/no/2.0) from [Lovdata](https://lovdata.no). Source code is [MIT licensed](LICENSE).

This is an unofficial project. For authoritative legal text, see [lovdata.no](https://lovdata.no).
