# Norges Lover (norwegian-laws)

Norwegian law texts as git history, with a [Quarto book](https://sondreskarsten.github.io/norwegian-laws/) for browsing.

## What this is

Every current Norwegian formal law (`gjeldende formelle lover`) parsed from [Lovdata's public API](https://api.lovdata.no/) into Markdown files, committed to git with amendment history. Each amendment act from [Norsk Lovtidend](https://lovdata.no/register/lovtidend) becomes a backdated git commit, so `git log -- lover/lov-1998-07-17-56.md` shows the legislative history of regnskapsloven.

The [Quarto book](https://sondreskarsten.github.io/norwegian-laws/) organizes all 774 laws by responsible ministry and is rebuilt weekly via GitHub Actions.

## Quick start

```bash
pip install -e .
lovdata-pipeline --download --output . --db amendments.db
```

## Repository structure

```
lover/              # Markdown law files (one per law)
src/lovdata_pipeline/  # Python package
book/               # Quarto chapter files (auto-generated)
_quarto.yml         # Quarto book config
.github/workflows/  # CI/CD
```

## How it works

1. **Download** `gjeldende-lover.tar.bz2` and `lovtidend-avd1-2026.tar.bz2` from Lovdata API
2. **Parse** consolidated law XML into Markdown with YAML frontmatter
3. **Parse** Lovtidend amendment XML into structured amendment records (SQLite)
4. **Commit** each amendment act as a backdated git commit via `git fast-import`
5. **Generate** Quarto book chapters grouped by ministry
6. **Deploy** rendered book to GitHub Pages

## Data source and license

Contains data under the [Norwegian Licence for Open Government Data (NLOD) 2.0](https://data.norge.no/nlod/no/2.0) distributed by [Lovdata](https://lovdata.no).

Source code is [MIT licensed](LICENSE).

**This is an unofficial project.** For authoritative legal text, see [lovdata.no](https://lovdata.no).
