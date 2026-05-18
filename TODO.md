# norwegian-laws: Task List

## Current state (2026-05-18)

**Production:**
- Repo: github.com/sondreskarsten/norwegian-laws (public, MIT + NLOD 2.0)
- 783 laws + 3,421 central forskrifter, weekly refresh from Lovdata API
- `law-history` branch: 16K+ per-act commits, LFS-backed, v2000..v2027 yearly tags
- Live site: 4,200+ HTML pages on gh-pages — per-law/per-forskrift pages,
  dept chapters (17 lover + 16 forskrifter), topic chapters (35), Atom feed
- 47 passing tests
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

**Diff page (book/diff.qmd):** Pick any law or forskrift, pick two yearly
tag versions, click "Sammenlign tekst" to render a side-by-side diff
inline. Uses diff2html-ui + jsdiff loaded from jsdelivr; fetches raw text
from `raw.githubusercontent.com` (LFS resolved server-side, CORS *).
Falls back to GitHub compare and endringslogg buttons.

`laws.json` (used by the diff page and dept search index) now contains
both lover and forskrifter entries with `kind`, `path`, and `tags` fields.

---

## Remaining items

### Deferred (not worth doing)

- **PDF export.** A single PDF of all laws+forskrifter is unusable. Per-law
  PDFs are duplicative of the per-law HTML pages.
- **Workflow dedup.** deploy.yml and law-history.yml both run `lovdata-load`.
  Saves ~2 min on Mondays, adds coordination complexity.
- **PAT rotation.** The GitHub PAT is in project context. Deferred per
  project policy.
- **Per-version pages.** Lovdata renders each historical version as its own
  page. Doing it here would require rendering each law at each yearly
  tag (~20K extra pages × LFS smudge cost). The diff page covers the
  "what changed between version X and Y" workflow without this expense.
