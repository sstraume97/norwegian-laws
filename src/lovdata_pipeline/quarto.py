"""Generate Quarto book structure from law markdown files."""
import os
import re
import yaml
from pathlib import Path
from collections import defaultdict


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


def group_laws_by_area(lover_dir: str) -> dict[str, list[dict]]:
    groups = defaultdict(list)
    for f in sorted(Path(lover_dir).glob("*.md")):
        meta = parse_frontmatter(str(f))
        if not meta.get("tittel"):
            continue
        area = meta.get("departement", "Annet")
        if not area:
            area = "Annet"
        groups[area].append({
            "file": f.name,
            "path": str(f),
            "tittel": meta.get("tittel", f.stem),
            "korttittel": meta.get("korttittel", ""),
            "refid": meta.get("refid", ""),
            "ikrafttredelse": meta.get("ikrafttredelse", ""),
        })
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
        lines.append("| Lov | Korttittel | Ikrafttredelse |")
        lines.append("|-----|-----------|----------------|")
        for law in sorted(laws, key=lambda x: x["tittel"]):
            refid = law["refid"].replace("/", "-")
            link = f"[{law['tittel'][:80]}](../lover/{law['file']})"
            kort = law["korttittel"] or ""
            ikraft = law["ikrafttredelse"] or ""
            lines.append(f"| {link} | {kort} | {ikraft} |")
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
            "repo-url": "https://github.com/sondreskarsten/norwegian-laws",
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

    index_lines = [
        "# Forord {.unnumbered}\n",
        "Dette er en uoffisiell samling av Norges gjeldende formelle lover,",
        "generert fra [Lovdata API](https://api.lovdata.no/) sine åpne data",
        "under [NLOD 2.0](https://data.norge.no/nlod/no/2.0)-lisensen.\n",
        f"Samlingen inneholder **{sum(len(v) for v in groups.values())} lover**",
        f"fordelt på **{len(groups)} departementer**.\n",
        "## Bruk\n",
        "- Bla gjennom lover etter departement i sidemenyen",
        "- Bruk søkefeltet for å finne spesifikke lover",
        "- Se [git-historikken](https://github.com/sondreskarsten/norwegian-laws/commits/main)",
        "  for endringshistorikk per lov\n",
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
        "[github.com/sondreskarsten/norwegian-laws](https://github.com/sondreskarsten/norwegian-laws)\n",
    ]
    with open(os.path.join(book_dir, "about.qmd"), "w", encoding="utf-8") as f:
        f.write("\n".join(about_lines))

    total = sum(len(v) for v in groups.values())
    print(f"  Generated Quarto config: {total} laws in {len(groups)} departments")
    return config


if __name__ == "__main__":
    import sys
    repo = sys.argv[1] if len(sys.argv) > 1 else "."
    generate_quarto_config(repo)
