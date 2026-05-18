# norwegian-laws: Task List

## Current state (2026-05-18)

**Working in production:**
- Repo: github.com/sondreskarsten/norwegian-laws (public, MIT + NLOD 2.0)
- ~735 laws + ~3,400 central forskrifter parsed to Markdown in `lover/` and `forskrifter/`
- Per-law Quarto book + per-law HTML pages live at sondreskarsten.github.io/norwegian-laws
- `law-history` branch: 16K+ per-act commits with rich metadata, LFS-backed,
  spanning v2000..v2027 yearly tags
- 4 GitHub Actions workflows (deploy weekly, law-history weekly, release on tag, tests on push)
- 33 passing tests covering parser, formatter, per-law pages, forskrift routing,
  preamble extraction for both lov and forskrift

**Coverage:**
- Parser: 99.5% article coverage, 98.9% word coverage on consolidated lover XML
- Lovtidend: 25,948 nl- amendment acts + ~14,000 sf- amendment acts (2001-2025),
  86.6% target_law attribution
- Reconstruction: full replacements (~26% of amendments) produce correct historical
  text. Partial amendments work post-baseline.
- Per-law pages: 783 lover/*.html + 3,421 forskrifter/*.html on gh-pages, all
  styled to match Quarto book theme, with cross-reference linking between laws.
- Search: full body text indexed (~4,200 entries in search.json)

---

## Outstanding work

### P2: Quality and polish

#### 1. Pre-1820 laws missing ikrafttredelse (28 documents)
Pre-1820 historic laws (`lov-1687-04-15.md`, `lov-1741-02-17.md`, etc.) have
`ikrafttredelse: ""` because the source XML lacks a parseable date. Either
document this as expected or substitute the `date_in_force` if available in
another XML field. Low priority — these are statutes nobody is amending.

#### 2. Diff visualization in the Quarto book
The `book/diff.qmd` page exists but currently links to GitHub's compare view.
Render a real side-by-side or unified diff in the page itself. Requires a JS
diff library (e.g. diff2html) loading the two yearly tag versions of a file
client-side.

#### 3. Topic tags / legal area classification
The XML has `legalArea` metadata. Currently extracted but not used in Quarto.
Could add a second grouping axis (by topic, not just department).

#### 4. RSS/Atom feed of changes
Generate a feed from `amendments.db` so users can subscribe to law changes.
Straightforward from the SQLite data.

#### 5. PDF export
Removed due to missing TinyTeX in CI. Re-enable with:
```yaml
- name: Install TinyTeX
  run: quarto install tinytex
```
Adds ~2 min to CI. Generates a full PDF of the law index.

#### 6. Pre-2001 history coverage
Lovdata Pro has full historical versions. The public API only has amendments
since 2001. For laws amended before 2001, the history will be incomplete.
Document this limitation in the about page.

### P3: CI / infra

#### 7. Cache the consolidated archive too
Currently `gjeldende-lover.tar.bz2` (5MB) and `gjeldende-sentrale-forskrifter.tar.bz2`
(20MB) are downloaded fresh on every deploy run. Add an actions/cache step with
a short TTL (e.g. monthly) — these only change weekly at most.

#### 8. Deploy and law-history workflows share the parse phase
The law-history workflow runs the same `lovdata-load` step as the deploy
workflow. Could be deduplicated by having law-history depend on a successful
deploy commit and pulling the SQLite + JSON from the main branch.

#### 9. Rotate the GitHub PAT
The PAT `ghp_d7p…` has been in conversation context and project files.
(Deferred per project policy.)

### P4: Future / nice-to-have

#### 10. Section-level deep linking
Per-law pages render the full law in one HTML file. Could add anchors at each
§ heading and surface them in the table-of-contents on the right side.

#### 11. Lovdata-style version banner
Show on each per-law page: "Du leser versjon X som var gjeldende fra YYYY-MM-DD
til YYYY-MM-DD" with prev/next links to other versions via the yearly tags.
