# Norges Lover (norwegian-laws)

Norwegian law texts and central regulations as git history, with a [Quarto book](https://sondreskarsten.github.io/norwegian-laws/) for browsing.

## What this is

Every current Norwegian formal law (`gjeldende formelle lover`, ~735 documents) and every central regulation (`gjeldende sentrale forskrifter`, ~3,400 documents) parsed from [Lovdata's public API](https://api.lovdata.no/) into Markdown files, committed to git with amendment history. Each amendment act from [Norsk Lovtidend](https://lovdata.no/register/lovtidend) becomes a backdated git commit, so `git log -- lover/lov-1998-07-17-56.md` shows the legislative history of regnskapsloven. Forskrift amendments are tracked the same way: `git log -- forskrifter/forskrift-2024-06-21-1166.md`.

The [Quarto book](https://sondreskarsten.github.io/norwegian-laws/) organizes laws and forskrifter by responsible ministry and is rebuilt weekly via GitHub Actions.

## Branches

| Branch | Purpose |
|--------|---------|
| `main` | Pipeline code, law files, Quarto source. Updated weekly. |
| `gh-pages` | Rendered Quarto book. Auto-deployed from `main`. |
| `law-history` | Orphan branch with backdated git commits per amendment act. Rebuilt weekly. |

Browse the `law-history` branch to see `git log` with real legislative dates:

```bash
git clone -b law-history https://github.com/sondreskarsten/norwegian-laws.git
git log --oneline -- lover/lov-1998-07-17-56.md
```

## Quick start

```bash
pip install -e lovdata-loader/ -e lovdata-publisher/

# Download archives, parse to snapshot
lovdata-load --download --output snapshot

# Format to Markdown + generate Quarto book chapters
lovdata-publish --snapshot snapshot --output . --quarto

# After `quarto render`, generate per-law HTML pages and full-text search index
lovdata-publish --post-render --output . --site-dir _site

# Build the full backdated git history (per-act commits, LFS-backed)
sudo apt-get install -y git-lfs
lovdata-publish --snapshot snapshot --build-history \
    --history-mode act --use-lfs --repo-path /tmp/law-repo
```

The `law-history` branch lives in git-LFS — install `git-lfs` before cloning.

## Architecture

The pipeline is split into two packages connected by a snapshot directory:

**lovdata-loader** downloads Lovdata archives and parses XML into structured JSON + SQLite:

```
lovdata-loader/
  src/lovdata_loader/
    download.py        # Lovdata API downloader
    parser.py          # XML → dataclasses (Section, Article, Paragraph)
    models.py          # Snapshot schema (LawData, AmendmentActData)
    store.py           # Write snapshot/ (JSON per law + amendments.db)
    cli.py             # lovdata-load CLI
```

**lovdata-publisher** reads a snapshot and produces all outputs:

```
lovdata-publisher/
  src/lovdata_publisher/
    formatter.py       # JSON → Markdown with YAML frontmatter
    git_export.py      # Backdated git fast-import from amendment timeline
    quarto.py          # Quarto book chapters, search, diff, version pages
    search_index.py    # Merge law metadata into Quarto search.json
    releases.py        # Monthly release tags on law-history branch
    cli.py             # lovdata-publish CLI
```

The snapshot is the contract between the two:

```
snapshot/
  manifest.json                 # Metadata (version, archive names, counts)
  laws/lov-1998-07-17-56.json   # One structured JSON per law
  amendments.db                 # SQLite: amendment acts + individual amendments
```

## Other files

```
lover/                  # 735 Markdown law files (one per law)
book/                   # Quarto chapter files (auto-generated per department)
_quarto.yml             # Quarto book config
laws.json               # Law metadata for client-side search + diff tools
src/lovdata_pipeline/   # Deprecated monolithic pipeline (kept for reference)
.github/workflows/
  deploy.yml            # Weekly: update laws + deploy Quarto book
  law-history.yml       # Weekly: rebuild backdated commit history
  test.yml              # CI: run loader + publisher tests
  release.yml           # On tag: create GitHub release
  gcs-sync.yml          # Sync repo to GCS bucket
```

## How it works

1. **Download** `gjeldende-lover.tar.bz2` and `lovtidend-avd1-*.tar.bz2` from Lovdata API
2. **Parse** consolidated law XML → structured JSON snapshot (one file per law)
3. **Parse** Lovtidend amendment XML → structured amendment records (SQLite)
4. **Format** JSON → Markdown with YAML frontmatter, preserving all content including nested sub-chapters, amendment notes, and footnotes
5. **Commit** each amendment act as a backdated git commit via `git fast-import`, with yearly version tags (`v2001`–`v2026`)
6. **Generate** Quarto book chapters grouped by ministry, with full-text search and cross-version diff tools
7. **Deploy** rendered book to GitHub Pages

## Data source and license

Contains data under the [Norwegian Licence for Open Government Data (NLOD) 2.0](https://data.norge.no/nlod/no/2.0) distributed by [Lovdata](https://lovdata.no).

Source code is [MIT licensed](LICENSE).

**This is an unofficial project.** For authoritative legal text, see [lovdata.no](https://lovdata.no).
