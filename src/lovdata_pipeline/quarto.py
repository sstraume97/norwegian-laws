"""Generate Quarto book structure from law markdown files."""
import os
import re
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
        }
        for dept in depts:
            groups[dept].append(entry)
    return dict(sorted(groups.items()))


def generate_quarto_config(repo_root: str, lover_dir: str = "lover"):
    full_lover = os.path.join(repo_root, lover_dir)
    book_dir = os.path.join(repo_root, "book")
    os.makedirs(book_dir, exist_ok=True)

    groups = group_laws_by_area(full_lover)

    chapters = []
    for dept, laws in groups.items():
        safe_dept = re.sub(r"[^\w\s-]", "", dept).strip().replace(" ", "-").lower()
        dept_file = f"dept-{safe_dept}.qmd"
        dept_path = os.path.join(book_dir, dept_file)

        lines = [f"# {dept}\n"]
        lines.append(f"*{len(laws)} lover*\n")
        lines.append("| Lov | Korttittel | Ikrafttredelse | Historikk |")
        lines.append("|-----|-----------|----------------|-----------|")
        for law in sorted(laws, key=lambda x: x["tittel"]):
            blob = f"{GITHUB_BASE}/blob/main/lover/{law['file']}"
            history = f"{GITHUB_BASE}/commits/{HISTORY_BRANCH}/lover/{law['file']}"
            title = law["tittel"][:80]
            link = f"[{title}]({blob})"
            kort = law["korttittel"] or ""
            ikraft = law["ikrafttredelse"] or ""
            hist_link = f"[git log]({history})"
            lines.append(f"| {link} | {kort} | {ikraft} | {hist_link} |")
        lines.append("")

        with open(dept_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        chapters.append(f"book/{dept_file}")

    config = {
        "project": {
            "type": "book",
            "output-dir": "_site",
        },
        "book": {
            "title": "Norges Lover",
            "subtitle": "Gjeldende formelle lover",
            "author": "Kilde: Lovdata API (NLOD 2.0)",
            "date": "today",
            "chapters": [
                "index.qmd",
                {"part": "Lover etter departement", "chapters": chapters},
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
            },
        },
    }

    with open(os.path.join(repo_root, "_quarto.yml"), "w", encoding="utf-8") as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    total_unique = len({e["file"] for laws in groups.values() for e in laws})
    index_lines = [
        "# Forord {.unnumbered}\n",
        "Dette er en uoffisiell samling av Norges gjeldende formelle lover,",
        "generert fra [Lovdata API](https://api.lovdata.no/) sine åpne data",
        "under [NLOD 2.0](https://data.norge.no/nlod/no/2.0)-lisensen.\n",
        f"Samlingen inneholder **{total_unique} lover**",
        f"fordelt på **{len(groups)} departementer**.\n",
        "## Bruk\n",
        "- Bla gjennom lover etter departement i sidemenyen",
        "- Klikk en lov for å lese lovteksten på GitHub",
        "- Klikk «git log» for å se endringshistorikk for den loven",
        f"- Se [`law-history`-grenen]({GITHUB_BASE}/tree/{HISTORY_BRANCH})",
        "  for komplett git-historikk med backdaterte endringer",
        "- Bruk søkefeltet for å finne spesifikke lover\n",
        "## Ansvarsfraskrivelse\n",
        "Denne samlingen er **uoffisiell** og oppdateres automatisk fra Lovdatas åpne API.",
        "For autoritativ lovtekst, se [lovdata.no](https://lovdata.no).",
        "Innholdet presenteres «som det er» uten garanti for korrekthet eller aktualitet.\n",
    ]
    with open(os.path.join(repo_root, "index.qmd"), "w", encoding="utf-8") as f:
        f.write("\n".join(index_lines))

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
    generate_quarto_config(repo)
