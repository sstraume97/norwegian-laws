"""Generate Quarto book structure from law markdown files.

Reads the lover/*.md files (already formatted by formatter.py) and
produces Quarto book chapters, search pages, diff tools, and config.
"""
import json
import os
import re
import sqlite3
import yaml
from pathlib import Path
from collections import defaultdict

GITHUB_BASE = "https://github.com/sondreskarsten/norwegian-laws"
HISTORY_BRANCH = "law-history"

KNOWN_DEPARTMENTS = [
    "Arbeids- og inkluderingsdepartementet",
    "Barne- og familiedepartementet",
    "Digitaliserings- og forvaltningsdepartementet",
    "Energidepartementet",
    "Finansdepartementet",
    "Forsvarsdepartementet",
    "Helse- og omsorgsdepartementet",
    "Justis- og beredskapsdepartementet",
    "Klima- og miljødepartementet",
    "Kommunal- og distriktsdepartementet",
    "Kultur- og likestillingsdepartementet",
    "Kunnskapsdepartementet",
    "Landbruks- og matdepartementet",
    "Nærings- og fiskeridepartementet",
    "Samferdselsdepartementet",
    "Statsministerens kontor",
    "Utenriksdepartementet",
]


def parse_frontmatter(filepath: str) -> dict:
    with open(filepath, encoding="utf-8") as f:
        content = f.read()
    m = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not m:
        return {}
    result = {}
    for line in m.group(1).splitlines():
        k, _, v = line.partition(":")
        if v:
            result[k.strip()] = v.strip().strip('"')
    return result


def split_departments(dept_str: str) -> list[str]:
    for known in sorted(KNOWN_DEPARTMENTS, key=len, reverse=True):
        dept_str = dept_str.replace(known, f"|{known}|")
    parts = [p.strip() for p in dept_str.split("|") if p.strip()]
    return parts if parts else [dept_str]


def group_laws_by_area(lover_dir: str) -> dict[str, list[dict]]:
    groups = defaultdict(list)
    for f in sorted(Path(lover_dir).glob("*.md")):
        if f.name == "README.md":
            continue
        meta = parse_frontmatter(str(f))
        if not meta.get("tittel"):
            continue
        raw_dept = meta.get("departement", "Annet") or "Annet"
        depts = split_departments(raw_dept)
        entry = {
            "file": f.name,
            "path": str(f),
            "tittel": meta.get("tittel", f.stem),
            "korttittel": meta.get("korttittel", ""),
            "refid": meta.get("refid", ""),
            "ikrafttredelse": meta.get("ikrafttredelse", ""),
            "sist-endret": meta.get("sist-endret", ""),
            "sist-endret-ikrafttredelse": meta.get("sist-endret-ikrafttredelse", ""),
        }
        for dept in depts:
            groups[dept].append(entry)
    return dict(sorted(groups.items()))


def extract_year_from_refid(refid: str) -> int:
    m = re.search(r"(\d{4})-\d{2}-\d{2}", refid)
    if m:
        return int(m.group(1))
    return 2001


def compute_version_links(refid: str, version_tags: list[str]) -> list[str]:
    enacted_year = extract_year_from_refid(refid)
    first_tag_year = 2001
    start_year = max(enacted_year, first_tag_year)
    all_years = [int(t[1:]) for t in version_tags]
    last_3 = version_tags[-3:]
    last_3_years = {int(t[1:]) for t in last_3}
    sampled = set()
    for y in all_years:
        if y < start_year:
            continue
        if y in last_3_years:
            continue
        if y == start_year or y % 5 == 0:
            sampled.add(y)
    combined = sorted(sampled | last_3_years)
    combined = [y for y in combined if y >= start_year]
    return [f"v{y}" for y in combined]


def get_amendment_stats_by_year(db_path: str) -> dict[str, dict]:
    if not db_path or not os.path.exists(db_path):
        return {}
    conn = sqlite3.connect(db_path)
    rows = conn.execute("""
        SELECT
            substr(date_in_force_resolved, 1, 4) as year,
            COUNT(*) as act_count,
            SUM(amendment_count) as total_amendments
        FROM amendment_acts
        GROUP BY year
        ORDER BY year
    """).fetchall()
    conn.close()
    stats = {}
    for year, act_count, total_amendments in rows:
        stats[year] = {"acts": act_count, "amendments": total_amendments or 0}
    return stats


def generate_laws_json(lover_dir: str, output_path: str, version_tags: list[str] = None) -> list[dict]:
    if version_tags is None:
        version_tags = [f"v{y}" for y in range(2001, 2027)]
    laws = []
    for f in sorted(Path(lover_dir).glob("*.md")):
        if f.name == "README.md":
            continue
        meta = parse_frontmatter(str(f))
        if not meta.get("tittel"):
            continue
        refid = meta.get("refid", "")
        raw_dept = meta.get("departement", "Annet") or "Annet"
        depts = split_departments(raw_dept)
        tags = compute_version_links(refid, version_tags)
        laws.append({
            "file": f.name,
            "refid": refid,
            "tittel": meta.get("tittel", ""),
            "korttittel": meta.get("korttittel", ""),
            "departement": depts,
            "ikrafttredelse": meta.get("ikrafttredelse", ""),
            "sist_endret": meta.get("sist-endret", ""),
            "github": f"{GITHUB_BASE}/blob/main/lover/{f.name}",
            "lovdata": f"https://lovdata.no/dokument/NL/{refid}",
            "log": f"{GITHUB_BASE}/commits/{HISTORY_BRANCH}/lover/{f.name}",
            "tags": tags,
        })
    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(laws, fh, ensure_ascii=False, indent=1)
    return laws


def generate_search_page(book_dir: str):
    lines = [
        '---',
        'title: "Søk i lover"',
        'search: false',
        '---',
        '',
        '<label for="law-search" style="font-weight:600;font-size:1.1em;">Søk etter lov (tittel, korttittel eller refid):</label>',
        '<input type="text" id="law-search" placeholder="f.eks. arbeidsmiljø, straffeloven, lov-2005..."',
        '  style="width:100%;padding:8px 12px;margin:8px 0 16px 0;font-size:1em;border:1px solid #ccc;border-radius:4px;">',
        '<div id="result-count" style="margin-bottom:8px;color:#666;"></div>',
        '<table id="law-results" style="width:100%;display:none;">',
        '<thead><tr><th style="text-align:left;">Lov</th><th style="text-align:left;">Korttittel</th><th style="text-align:left;">Departement</th><th style="text-align:left;">Lenker</th></tr></thead>',
        '<tbody></tbody>',
        '</table>',
        '<div id="no-results" style="display:none;color:#888;padding:20px 0;">Ingen treff.</div>',
        '',
        '```{=html}',
        '<script src="https://cdn.jsdelivr.net/npm/fuse.js@7.0.0/dist/fuse.min.js"></script>',
        '<script>',
        'document.addEventListener("DOMContentLoaded", function() {',
        '  var input = document.getElementById("law-search");',
        '  var table = document.getElementById("law-results");',
        '  var tbody = table.querySelector("tbody");',
        '  var countDiv = document.getElementById("result-count");',
        '  var noResults = document.getElementById("no-results");',
        '  var laws = [];',
        '  var fuse = null;',
        '',
        '  fetch("../laws.json").then(function(r){return r.json()}).then(function(data){',
        '    laws = data;',
        '    fuse = new Fuse(laws, {',
        '      keys: [',
        '        {name: "tittel", weight: 0.4},',
        '        {name: "korttittel", weight: 0.3},',
        '        {name: "refid", weight: 0.2},',
        '        {name: "departement", weight: 0.1}',
        '      ],',
        '      threshold: 0.35,',
        '      distance: 200,',
        '      minMatchCharLength: 2',
        '    });',
        '  });',
        '',
        '  function renderResults(results) {',
        '    tbody.innerHTML = "";',
        '    if (results.length === 0) {',
        '      table.style.display = "none";',
        '      noResults.style.display = "block";',
        '      countDiv.textContent = "";',
        '      return;',
        '    }',
        '    noResults.style.display = "none";',
        '    table.style.display = "table";',
        '    countDiv.textContent = results.length + " treff";',
        '    results.forEach(function(law) {',
        '      var tr = document.createElement("tr");',
        '      var td1 = document.createElement("td");',
        '      td1.innerHTML = \'<a href="\' + law.github + \'">\' + law.tittel.substring(0,70) + (law.tittel.length > 70 ? "…" : "") + "</a>";',
        '      var td2 = document.createElement("td");',
        '      td2.textContent = law.korttittel;',
        '      var td3 = document.createElement("td");',
        '      td3.textContent = law.departement.join(", ");',
        '      var td4 = document.createElement("td");',
        '      td4.innerHTML = \'<a href="\' + law.lovdata + \'">lovdata</a> · <a href="\' + law.log + \'">logg</a>\';',
        '      tr.appendChild(td1);',
        '      tr.appendChild(td2);',
        '      tr.appendChild(td3);',
        '      tr.appendChild(td4);',
        '      tbody.appendChild(tr);',
        '    });',
        '  }',
        '',
        '  input.addEventListener("input", function() {',
        '    var q = input.value.trim();',
        '    if (!fuse || q.length < 2) {',
        '      table.style.display = "none";',
        '      noResults.style.display = "none";',
        '      countDiv.textContent = "";',
        '      return;',
        '    }',
        '    var hits = fuse.search(q, {limit: 50}).map(function(r){return r.item;});',
        '    renderResults(hits);',
        '  });',
        '});',
        '</script>',
        '```',
        '',
    ]
    with open(os.path.join(book_dir, "sok.qmd"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def generate_diff_page(book_dir: str, version_tags: list[str]):
    lines = [
        '---',
        'title: "Sammenlign lovversjon"',
        'search: false',
        '---',
        '',
        'Velg en lov og to årsversjoner for å se endringer på GitHub.',
        '',
        '<div style="display:flex;flex-direction:column;gap:12px;max-width:600px;margin:16px 0;">',
        '<label for="diff-law" style="font-weight:600;">Velg lov:</label>',
        '<input type="text" id="diff-law-search" placeholder="Søk etter lov..."',
        '  style="padding:8px;border:1px solid #ccc;border-radius:4px;">',
        '<select id="diff-law" size="6" style="padding:4px;border:1px solid #ccc;border-radius:4px;"></select>',
        '',
        '<div style="display:flex;gap:16px;">',
        '<div style="flex:1;">',
        '<label for="diff-from" style="font-weight:600;">Fra versjon:</label>',
        '<select id="diff-from" style="width:100%;padding:6px;border:1px solid #ccc;border-radius:4px;"></select>',
        '</div>',
        '<div style="flex:1;">',
        '<label for="diff-to" style="font-weight:600;">Til versjon:</label>',
        '<select id="diff-to" style="width:100%;padding:6px;border:1px solid #ccc;border-radius:4px;"></select>',
        '</div>',
        '</div>',
        '',
        '<div style="display:flex;gap:12px;">',
        '<button id="diff-compare" style="padding:8px 20px;background:#0969da;color:#fff;border:none;border-radius:4px;cursor:pointer;">Sammenlign (full diff)</button>',
        '<button id="diff-log" style="padding:8px 20px;background:#24292f;color:#fff;border:none;border-radius:4px;cursor:pointer;">Se endringslogg</button>',
        '</div>',
        '<div id="diff-info" style="color:#666;font-size:0.9em;"></div>',
        '</div>',
        '',
        '```{=html}',
        '<script src="https://cdn.jsdelivr.net/npm/fuse.js@7.0.0/dist/fuse.min.js"></script>',
        '<script>',
        'document.addEventListener("DOMContentLoaded", function() {',
        '  var lawSearch = document.getElementById("diff-law-search");',
        '  var lawSelect = document.getElementById("diff-law");',
        '  var fromSelect = document.getElementById("diff-from");',
        '  var toSelect = document.getElementById("diff-to");',
        '  var compareBtn = document.getElementById("diff-compare");',
        '  var logBtn = document.getElementById("diff-log");',
        '  var infoDiv = document.getElementById("diff-info");',
        f'  var base = "{GITHUB_BASE}";',
        '  var laws = [];',
        '  var fuse = null;',
        '',
        '  function populateTags(sel, tags) {',
        '    sel.innerHTML = "";',
        '    tags.forEach(function(t) {',
        '      var o = document.createElement("option");',
        '      o.value = t; o.textContent = t;',
        '      sel.appendChild(o);',
        '    });',
        '  }',
        '',
        '  function populateLaws(list) {',
        '    lawSelect.innerHTML = "";',
        '    list.forEach(function(law) {',
        '      var o = document.createElement("option");',
        '      o.value = law.file;',
        '      o.textContent = (law.korttittel || law.tittel).substring(0,80);',
        '      o.dataset.tags = JSON.stringify(law.tags);',
        '      lawSelect.appendChild(o);',
        '    });',
        '    if (list.length > 0) {',
        '      lawSelect.selectedIndex = 0;',
        '      onLawSelect();',
        '    }',
        '  }',
        '',
        '  function onLawSelect() {',
        '    var opt = lawSelect.options[lawSelect.selectedIndex];',
        '    if (!opt) return;',
        '    var tags = JSON.parse(opt.dataset.tags || "[]");',
        '    populateTags(fromSelect, tags);',
        '    populateTags(toSelect, tags);',
        '    if (tags.length >= 2) {',
        '      fromSelect.selectedIndex = Math.max(0, tags.length - 2);',
        '      toSelect.selectedIndex = tags.length - 1;',
        '    }',
        '  }',
        '',
        '  fetch("../laws.json").then(function(r){return r.json()}).then(function(data) {',
        '    laws = data;',
        '    fuse = new Fuse(laws, {',
        '      keys: ["tittel","korttittel","refid"],',
        '      threshold: 0.35',
        '    });',
        '    populateLaws(laws);',
        '  });',
        '',
        '  lawSelect.addEventListener("change", onLawSelect);',
        '',
        '  lawSearch.addEventListener("input", function() {',
        '    var q = lawSearch.value.trim();',
        '    if (!fuse || q.length < 2) { populateLaws(laws); return; }',
        '    var hits = fuse.search(q, {limit:30}).map(function(r){return r.item;});',
        '    populateLaws(hits);',
        '  });',
        '',
        '  compareBtn.addEventListener("click", function() {',
        '    var file = lawSelect.value;',
        '    var from = fromSelect.value;',
        '    var to = toSelect.value;',
        '    if (!file || !from || !to) { infoDiv.textContent = "Velg lov og versjoner."; return; }',
        '    if (from >= to) { infoDiv.textContent = "Fra-versjon må være eldre enn til-versjon."; return; }',
        '    window.open(base + "/compare/" + from + "..." + to, "_blank");',
        '    infoDiv.textContent = "Åpner diff for " + from + "…" + to + ". Finn " + file + " i fillisten.";',
        '  });',
        '',
        '  logBtn.addEventListener("click", function() {',
        '    var file = lawSelect.value;',
        '    if (!file) { infoDiv.textContent = "Velg en lov."; return; }',
        '    window.open(base + "/commits/law-history/lover/" + file, "_blank");',
        '    infoDiv.textContent = "";',
        '  });',
        '});',
        '</script>',
        '```',
        '',
    ]
    with open(os.path.join(book_dir, "diff.qmd"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def generate_quarto_config(repo_root: str, lover_dir: str = "lover", version_tags: list[str] = None, db_path: str = None):
    """Generate the full Quarto book configuration and chapter files."""
    full_lover = os.path.join(repo_root, lover_dir)
    book_dir = os.path.join(repo_root, "book")
    os.makedirs(book_dir, exist_ok=True)

    groups = group_laws_by_area(full_lover)

    if version_tags is None:
        version_tags = [f"v{y}" for y in range(2001, 2027)]

    # Generate laws.json
    laws_json_path = os.path.join(repo_root, "laws.json")
    generate_laws_json(full_lover, laws_json_path, version_tags)

    # Generate search + diff pages
    generate_search_page(book_dir)
    generate_diff_page(book_dir, version_tags)

    # Amendment stats
    year_stats = get_amendment_stats_by_year(db_path) if db_path else {}

    # Department chapters
    chapters = []
    for dept, laws in groups.items():
        safe_dept = re.sub(r"[^\w\s-]", "", dept).strip().replace(" ", "-").lower()
        dept_file = f"dept-{safe_dept}.qmd"
        dept_path = os.path.join(book_dir, dept_file)

        lines = [f"# {dept}\n"]
        lines.append(f"*{len(laws)} lover*\n")
        lines.append("| Lov | Korttittel | Lovdata | Historikk |")
        lines.append("|-----|-----------|---------|-----------|")
        for law in sorted(laws, key=lambda x: x["tittel"]):
            stem = law["file"].rsplit(".", 1)[0]
            page = f"/norwegian-laws/lover/{stem}.html"
            history = f"{GITHUB_BASE}/commits/{HISTORY_BRANCH}/lover/{law['file']}"
            lovdata_url = f"https://lovdata.no/dokument/NL/{law['refid']}"
            title = law["tittel"][:80]
            link = f"[{title}]({page})"
            kort = law["korttittel"] or ""
            lovdata_link = f"[lovdata.no]({lovdata_url})"
            vtags = compute_version_links(law["refid"], version_tags)
            version_links = " · ".join(
                f"[{t}]({GITHUB_BASE}/blob/{t}/lover/{law['file']})"
                for t in vtags
            )
            hist_cell = f"[log]({history}) · {version_links}"
            lines.append(f"| {link} | {kort} | {lovdata_link} | {hist_cell} |")
        lines.append("")

        with open(dept_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        chapters.append(f"book/{dept_file}")

    # Versions page
    ver_lines = [
        "# Stabile versjoner {.unnumbered}\n",
        "Hver årsversjon (`v{årstall}`) er et øyeblikksbilde av alle norske lover",
        f"slik de var ved utgangen av det året, basert på [`{HISTORY_BRANCH}`-grenen]({GITHUB_BASE}/tree/{HISTORY_BRANCH}).\n",
        "## Årlige versjoner\n",
    ]
    if year_stats:
        ver_lines.append("| Versjon | Bla gjennom | Endringer fra forrige | Omfang |")
        ver_lines.append("|---------|-------------|----------------------|--------|")
    else:
        ver_lines.append("| Versjon | Bla gjennom | Endringer fra forrige |")
        ver_lines.append("|---------|-------------|----------------------|")

    for i, tag in enumerate(version_tags):
        year = tag[1:]
        browse = f"[{tag}]({GITHUB_BASE}/tree/{tag}/lover)"
        if i > 0:
            prev = version_tags[i - 1]
            diff = f"[{prev}...{tag}]({GITHUB_BASE}/compare/{prev}...{tag})"
        else:
            diff = "\u2014"
        if year_stats:
            st = year_stats.get(year, {})
            acts = st.get("acts", 0)
            stat_cell = f"{acts} vedtak" if acts else "\u2014"
            ver_lines.append(f"| `{tag}` | {browse} | {diff} | {stat_cell} |")
        else:
            ver_lines.append(f"| `{tag}` | {browse} | {diff} |")

    ver_lines.append("")
    ver_lines.append("## Verktøy\n")
    ver_lines.append("- [Søk i lover](sok.qmd) \u2014 finn lover etter tittel eller korttittel")
    ver_lines.append("- [Sammenlign lovversjon](diff.qmd) \u2014 velg lov og to årstall for å se endringer\n")
    ver_lines.append("## Bruk med git\n")
    ver_lines.append("```bash")
    ver_lines.append("# Klon historikk-grenen")
    ver_lines.append(f"git clone -b {HISTORY_BRANCH} {GITHUB_BASE}.git")
    ver_lines.append("cd norwegian-laws")
    ver_lines.append("")
    ver_lines.append("# Se en lov slik den var i 2020")
    ver_lines.append("git show v2020:lover/lov-1998-07-17-56.md")
    ver_lines.append("")
    ver_lines.append("# Sammenlign to versjoner av en lov")
    ver_lines.append("git diff v2020 v2024 -- lover/lov-1998-07-17-56.md")
    ver_lines.append("")
    ver_lines.append("# Se alle endringer mellom to år")
    ver_lines.append("git diff --stat v2023 v2024")
    ver_lines.append("```\n")

    with open(os.path.join(book_dir, "versjoner.qmd"), "w", encoding="utf-8") as f:
        f.write("\n".join(ver_lines))

    # Quarto config
    config = {
        "project": {"type": "book", "output-dir": "_site"},
        "lang": "nb",
        "book": {
            "title": "Norges Lover",
            "subtitle": "Gjeldende formelle lover",
            "author": "Kilde: Lovdata API (NLOD 2.0)",
            "date": "today",
            "chapters": [
                "index.qmd",
                {"part": "Lover etter departement", "chapters": chapters},
                "book/versjoner.qmd",
                "book/sok.qmd",
                "book/diff.qmd",
                "book/about.qmd",
            ],
            "search": True,
            "repo-url": GITHUB_BASE,
            "repo-actions": ["source", "issue"],
        },
        "format": {
            "html": {
                "theme": "cosmo",
                "toc": True,
                "toc-depth": 3,
                "number-sections": False,
                "code-fold": True,
                "lang": "nb",
            }
        },
    }

    with open(os.path.join(repo_root, "_quarto.yml"), "w", encoding="utf-8") as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    # Landing page
    total_unique = len({e["file"] for laws in groups.values() for e in laws})
    index_lines = [
        "# Forord {.unnumbered}\n",
        "Dette er en uoffisiell samling av Norges gjeldende formelle lover,",
        "generert fra [Lovdata API](https://api.lovdata.no/) sine åpne data",
        "under [NLOD 2.0](https://data.norge.no/nlod/no/2.0)-lisensen.\n",
        f"Samlingen inneholder **{total_unique} lover**",
        f"fordelt på **{len(groups)} departementer**.\n",
        "## Les lover\n",
        "- [Søk etter lov](book/sok.qmd) \u2014 finn lover etter tittel, korttittel eller lovnummer",
        "- Bla gjennom lover etter departement i sidemenyen",
        "- Klikk en lov for å lese lovteksten på GitHub",
        "- For autoritativ lovtekst, se [lovdata.no](https://lovdata.no)\n",
        "## Utforsk historikk\n",
        f"- [`{HISTORY_BRANCH}`-grenen]({GITHUB_BASE}/tree/{HISTORY_BRANCH}) har komplett git-historikk med backdaterte endringer",
        "- [Stabile versjoner](book/versjoner.qmd) \u2014 sammenlign lover mellom år (v2001\u2013v2026)",
        "- [Sammenlign lovversjon](book/diff.qmd) \u2014 velg en lov og to årstall for å se endringer",
        "- Klikk \u00ablog\u00bb i lovtabellene for å se endringshistorikk for en enkelt lov\n",
        "## Ansvarsfraskrivelse\n",
        "Denne samlingen er **uoffisiell** og oppdateres automatisk fra Lovdatas åpne API.",
        "For autoritativ lovtekst, se [lovdata.no](https://lovdata.no).",
        "Innholdet presenteres \u00absom det er\u00bb uten garanti for korrekthet eller aktualitet.\n",
    ]
    with open(os.path.join(repo_root, "index.qmd"), "w", encoding="utf-8") as f:
        f.write("\n".join(index_lines))

    # About page
    about_lines = [
        "# Om dette prosjektet {.unnumbered}\n",
        "## Datakilde\n",
        "Lovtekstene er hentet fra [Lovdata API](https://api.lovdata.no/) sine åpne data.\n",
        "## Lisens\n",
        "Innholdet er tilgjengelig under",
        "[Norsk lisens for offentlige data (NLOD) 2.0](https://data.norge.no/nlod/no/2.0).\n",
        "> Inneholder data under Norsk lisens for offentlige data (NLOD)",
        "> tilgjengeliggjort av Lovdata.\n",
        "Kildekoden for dette prosjektet er lisensiert under MIT.\n",
        "## Kontakt\n",
        "Kildekode og feilrapportering:",
        f"[github.com/sondreskarsten/norwegian-laws]({GITHUB_BASE})\n",
    ]
    with open(os.path.join(book_dir, "about.qmd"), "w", encoding="utf-8") as f:
        f.write("\n".join(about_lines))

    print(f"  Generated Quarto config: {total_unique} laws in {len(groups)} departments")
    return config


if __name__ == "__main__":
    import sys
    repo = sys.argv[1] if len(sys.argv) > 1 else "."
    db = sys.argv[2] if len(sys.argv) > 2 else None
    generate_quarto_config(repo, db_path=db)
