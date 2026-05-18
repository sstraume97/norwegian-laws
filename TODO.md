# norwegian-laws: Task List

## Current state (2026-05-18)

**Production:**
- Repo: github.com/sondreskarsten/norwegian-laws (public, MIT + NLOD 2.0)
- 783 laws + 3,421 central forskrifter, weekly refresh from Lovdata API
- `law-history` branch: 16K+ per-act commits, LFS-backed, v2000..v2027 yearly tags
- Live site: 4,277 HTML pages on gh-pages — per-law/per-forskrift pages,
  dept chapters (17 lover + 16 forskrifter), topic chapters (35), Atom feed
- 44 passing tests
- 4 GitHub Actions workflows (deploy weekly + on push; law-history weekly;
  release on tag; tests on push). Lovdata archives cached weekly via
  `actions/cache@v4` with YYYY-WW keys.

**Per-law pages include:**
- Cross-reference linking to related laws/forskrifter
- Section-level `<h4 id="...">` anchors on every § for deep-linking
- Version banner pointing at git history and version table
- Rettsområde row in metadata (one-to-many via parser fix)
- Lovdata.no source link
- Full body text indexed in search.json

**Atom feed:** Top 100 most-recent amendments, autodiscovered via
`<link rel="alternate" type="application/atom+xml">` in every book page head.

---

## Remaining items

### P4 (low priority, not blocking)

#### Diff visualization in book/diff.qmd
Currently links to GitHub's compare view. A client-side diff (e.g. diff2html
loading two yearly tag versions of a file) would render the diff inline.
Requires fetching raw file blobs from GitHub Pages of the law-history
branch, which is LFS-pointer text — needs LFS resolution from gh-pages
side, which is non-trivial.

#### PDF export
Quarto can produce PDF if TinyTeX is installed. Adds ~2 min to CI for
limited utility.

#### Workflow dedup
deploy.yml and law-history.yml both run `lovdata-load`. Could be
deduplicated but saves only ~2 min on Mondays.

#### PAT rotation
The GitHub PAT is in project context. Deferred per project policy.

#### Per-version pages
Lovdata shows "Du leser versjon X gjeldende fra YYYY-MM-DD til YYYY-MM-DD"
on each version of a law. To do this here we'd need to render each law at
each yearly tag (~783 laws × 26 tags = 20K extra pages). Not worth the build
time. Current version banner already points users at versjoner.html and git log.
