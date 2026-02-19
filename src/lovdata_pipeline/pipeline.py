"""
Norwegian Law-as-Git Pipeline
Parses Lovdata public XML archives into a git repository with backdated commits.

Data sources:
  - gjeldende-lover.tar.bz2: Current consolidated law texts (775 laws)
  - lovtidend-avd1-{year}.tar.bz2: Published amendment acts (Norsk Lovtidend)

Pipeline:
  1. parse_consolidated() → Markdown files for each current law
  2. parse_lovtidend()    → Structured amendment records from Lovtidend XML
  3. build_repo()         → Git repository with initial import + amendment commits
"""

import tarfile
import sqlite3
import re
import os
import subprocess
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from dataclasses import dataclass, field
from bs4 import BeautifulSoup, Tag


# ─── Dataclasses ─────────────────────────────────────────────────────────────

@dataclass
class LawMetadata:
    refid: str
    title: str
    short_title: str
    ministry: str
    date_in_force: str
    last_amended: str
    last_amended_in_force: str
    legal_area: str

@dataclass
class Amendment:
    change_type: str   # change | repeal | add | move
    target: str        # e.g. lov/1999-07-02-64/§21
    instruction: str   # e.g. "§ 21 skal lyde:"
    new_text: str      # the replacement text (empty for repeals)

@dataclass
class AmendmentAct:
    refid: str
    filename: str
    title: str
    short_title: str
    date_in_force: str
    date_published: str
    ministry: str
    changes_to: list[str]
    amendments: list[Amendment]
    misc_info: str
    journal_number: str


# ─── Consolidated Law Parser ────────────────────────────────────────────────

def refid_to_filepath(refid: str) -> str:
    return f"lover/{refid.replace('/', '-')}.md"


def extract_header_field(header: Tag, css_class: str) -> str:
    dd = header.find("dd", class_=css_class)
    if not dd:
        return ""
    return dd.get_text(strip=True)


def extract_header_list(header: Tag, css_class: str) -> list[str]:
    dd = header.find("dd", class_=css_class)
    if not dd:
        return []
    items = dd.find_all("li")
    if items:
        return [li.get_text(strip=True) for li in items]
    return [dd.get_text(strip=True)]


def extract_last_changed_by(header: Tag) -> tuple[str, str]:
    for css_class in ["lastChangedBy", "sistEndret", "lastAmended"]:
        dd = header.find("dd", class_=css_class)
        if not dd:
            continue
        anchor = dd.find("a")
        if anchor:
            refid = anchor.get_text(strip=True)
            rest = ""
            for sibling in anchor.next_siblings:
                t = str(sibling).strip()
                if t:
                    rest += t
            in_force = ""
            m = re.search(r"fra\s*(\d{4}-\d{2}-\d{2})", rest)
            if m:
                in_force = m.group(1)
            return refid, in_force
        return dd.get_text(strip=True), ""
    return "", ""


def parse_law_metadata(soup: BeautifulSoup) -> LawMetadata:
    header = soup.find("header")
    last_amended, last_amended_in_force = extract_last_changed_by(header)
    return LawMetadata(
        refid=extract_header_field(header, "refid"),
        title=extract_header_field(header, "title"),
        short_title=extract_header_field(header, "titleShort"),
        ministry=extract_header_field(header, "ministry"),
        date_in_force=extract_header_field(header, "dateInForce"),
        last_amended=last_amended,
        last_amended_in_force=last_amended_in_force,
        legal_area=extract_header_field(header, "legalArea"),
    )


def legal_article_to_markdown(article: Tag, depth: int = 0) -> str:
    lines = []
    name = article.get("data-name", "")

    article_header = (
        article.find(["h3", "h4", "h5", "span"], class_="legalArticleHeader")
        or article.find("span", class_="futureLegalArticleHeader")
    )
    if article_header:
        value = article_header.find("span", class_="legalArticleValue")
        title_span = article_header.find("span", class_="legalArticleTitle")
        header_text = value.get_text(strip=True) if value else ""
        if title_span:
            header_text += f". {title_span.get_text(strip=True)}"
        lines.append(f"{'#' * min(depth + 3, 6)} {header_text}")
        lines.append("")

    for ledd in article.find_all("article", class_=lambda c: c and ("legalP" in c or "numberedLegalP" in c) if c else False, recursive=False):
        ledd_id = ledd.get("id", "")
        text_parts = []
        for child in ledd.children:
            if isinstance(child, Tag) and child.name == "ul":
                if text_parts:
                    lines.append(" ".join(text_parts))
                    text_parts = []
                    lines.append("")
                for li in child.find_all("li", recursive=False):
                    identifier = li.get("data-li-identifier", "-")
                    li_text = li.get_text(strip=True)
                    lines.append(f"- {identifier} {li_text}")
                lines.append("")
            elif isinstance(child, Tag):
                text_parts.append(child.get_text(strip=True))
            else:
                t = str(child).strip()
                if t:
                    text_parts.append(t)
        if text_parts:
            lines.append(" ".join(text_parts))
            lines.append("")

    return "\n".join(lines)


def section_to_markdown(section: Tag) -> str:
    lines = []
    name = section.get("data-name", "")
    heading = section.find(["h2", "h3", "h4"])
    if heading:
        lines.append(f"## {heading.get_text(strip=True)}")
        lines.append("")

    for child in section.children:
        if not isinstance(child, Tag):
            continue
        if "legalArticle" in child.get("class", []):
            lines.append(legal_article_to_markdown(child, depth=1))
        elif child.name == "article" and "legalP" in child.get("class", []):
            lines.append(child.get_text(strip=True))
            lines.append("")

    return "\n".join(lines)


def law_to_markdown(soup: BeautifulSoup) -> str:
    meta = parse_law_metadata(soup)
    lines = []

    lines.append("---")
    lines.append(f"tittel: \"{meta.title}\"")
    if meta.short_title:
        lines.append(f"korttittel: \"{meta.short_title}\"")
    lines.append(f"refid: \"{meta.refid}\"")
    lines.append(f"departement: \"{meta.ministry}\"")
    lines.append(f"ikrafttredelse: \"{meta.date_in_force}\"")
    if meta.last_amended:
        lines.append(f"sist-endret: \"{meta.last_amended}\"")
    if meta.last_amended_in_force:
        lines.append(f"sist-endret-ikrafttredelse: \"{meta.last_amended_in_force}\"")
    lines.append("---")
    lines.append("")
    lines.append(f"# {meta.title}")
    lines.append("")

    body = soup.find("main", class_="documentBody")
    if not body:
        body = soup.find("body")

    for section in body.find_all("section", recursive=False):
        lines.append(section_to_markdown(section))

    for article in body.find_all("article", class_="legalArticle", recursive=False):
        lines.append(legal_article_to_markdown(article, depth=0))

    return "\n".join(lines)


def parse_consolidated_archive(archive_path: str, output_dir: str) -> dict[str, str]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    results = {}

    with tarfile.open(archive_path, "r:bz2") as tar:
        members = [m for m in tar.getmembers() if m.name.endswith(".xml")]
        for i, member in enumerate(members):
            f = tar.extractfile(member)
            if not f:
                continue
            content = f.read()
            soup = BeautifulSoup(content, "html.parser")
            meta = parse_law_metadata(soup)

            if not meta.refid:
                continue

            md = law_to_markdown(soup)
            filepath = refid_to_filepath(meta.refid)
            full_path = output / filepath
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(md, encoding="utf-8")
            results[meta.refid] = str(filepath)

            if (i + 1) % 100 == 0:
                print(f"  Parsed {i + 1}/{len(members)} laws...")

    return results


# ─── Lovtidend Amendment Parser ─────────────────────────────────────────────

def parse_amendment(change_el: Tag) -> Amendment:
    change_type = "unknown"
    target = ""

    if change_el.get("data-change-part"):
        change_type = "change"
        target = change_el["data-change-part"]
    elif change_el.get("data-repeal-part"):
        change_type = "repeal"
        target = change_el["data-repeal-part"]
    elif change_el.get("data-add-new-part"):
        change_type = "add"
        target = change_el["data-add-new-part"]
    elif change_el.get("data-move-part"):
        change_type = "move"
        target = change_el["data-move-part"]

    instruction_el = change_el.find("article", class_="defaultP")
    instruction = instruction_el.get_text(strip=True) if instruction_el else ""

    new_text_parts = []
    for future in change_el.find_all(["article", "span"], class_=lambda c: c and "future" in c.lower() if c else False):
        new_text_parts.append(future.get_text(strip=True))
    for ledd in change_el.find_all("article", class_="legalP"):
        if ledd.find_parent(class_=lambda c: c and "future" in c.lower() if c else False):
            continue
        if ledd.find_parent("article", class_="defaultP"):
            continue
        new_text_parts.append(ledd.get_text(strip=True))

    new_text = "\n".join(new_text_parts)

    return Amendment(
        change_type=change_type,
        target=target,
        instruction=instruction,
        new_text=new_text,
    )


def parse_lovtidend_file(content: bytes, filename: str) -> AmendmentAct | None:
    soup = BeautifulSoup(content, "html.parser")
    header = soup.find("header")
    if not header:
        return None

    refid = extract_header_field(header, "refid")
    if not refid:
        return None

    date_in_force = extract_header_field(header, "dateInForce")
    date_published = extract_header_field(header, "dateOfPublication")
    changes_to = extract_header_list(header, "changesToDocuments")

    amendments = []
    for change_el in soup.find_all("article", class_="change"):
        amendments.append(parse_amendment(change_el))

    return AmendmentAct(
        refid=refid,
        filename=filename,
        title=extract_header_field(header, "title") or soup.find("title").get_text(strip=True) if soup.find("title") else "",
        short_title=extract_header_field(header, "titleShort"),
        date_in_force=date_in_force,
        date_published=date_published,
        ministry=extract_header_field(header, "ministry"),
        changes_to=changes_to,
        amendments=amendments,
        misc_info=extract_header_field(header, "miscInformation"),
        journal_number=extract_header_field(header, "journalNumber"),
    )


def parse_lovtidend_archive(archive_path: str, prefix_filter: str = "nl-") -> list[AmendmentAct]:
    acts = []
    with tarfile.open(archive_path, "r:bz2") as tar:
        members = [m for m in tar.getmembers()
                    if m.name.endswith(".xml") and os.path.basename(m.name).startswith(prefix_filter)]
        for member in members:
            f = tar.extractfile(member)
            if not f:
                continue
            content = f.read()
            act = parse_lovtidend_file(content, os.path.basename(member.name))
            if act:
                acts.append(act)
    return acts


# ─── Date Parsing ────────────────────────────────────────────────────────────

DEFERRED_PATTERNS = ["Kongen bestemmer", "Kongen fastsetter", "Kongen fastset"]

def parse_effective_date(date_str: str, fallback_published: str) -> tuple[str, bool]:
    if any(p in date_str for p in DEFERRED_PATTERNS):
        pub = parse_publication_date(fallback_published)
        return pub, True

    date_str = date_str.strip()
    for fmt in ["%Y-%m-%d", "%d.%m.%Y"]:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime("%Y-%m-%d"), False
        except ValueError:
            continue

    if re.match(r"^\d{4}-\d{2}-\d{2}", date_str):
        return date_str[:10], False

    pub = parse_publication_date(fallback_published)
    return pub, True


def parse_publication_date(date_str: str) -> str:
    date_str = date_str.strip()
    for fmt in ["%Y-%m-%d %H:%M", "%Y-%m-%d", "%d.%m.%Y %H:%M", "%d.%m.%Y"]:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    m = re.match(r"(\d{4}-\d{2}-\d{2})", date_str)
    if m:
        return m.group(1)
    return "2000-01-01"


# ─── SQLite Storage ──────────────────────────────────────────────────────────

def init_db(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS amendment_acts (
            refid TEXT PRIMARY KEY,
            filename TEXT,
            title TEXT,
            short_title TEXT,
            date_in_force TEXT,
            date_in_force_resolved TEXT,
            is_deferred INTEGER,
            date_published TEXT,
            ministry TEXT,
            changes_to TEXT,
            misc_info TEXT,
            journal_number TEXT,
            amendment_count INTEGER
        );
        CREATE TABLE IF NOT EXISTS amendments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            act_refid TEXT REFERENCES amendment_acts(refid),
            change_type TEXT,
            target TEXT,
            instruction TEXT,
            new_text TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_amendments_act ON amendments(act_refid);
        CREATE INDEX IF NOT EXISTS idx_acts_date ON amendment_acts(date_in_force_resolved);
    """)
    return conn


def store_amendment_act(conn: sqlite3.Connection, act: AmendmentAct):
    effective_date, is_deferred = parse_effective_date(act.date_in_force, act.date_published)
    pub_date = parse_publication_date(act.date_published)

    conn.execute("""
        INSERT OR REPLACE INTO amendment_acts
        (refid, filename, title, short_title, date_in_force, date_in_force_resolved,
         is_deferred, date_published, ministry, changes_to, misc_info, journal_number,
         amendment_count)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        act.refid, act.filename, act.title, act.short_title,
        act.date_in_force, effective_date, int(is_deferred),
        pub_date, act.ministry,
        ",".join(act.changes_to), act.misc_info, act.journal_number,
        len(act.amendments),
    ))

    for a in act.amendments:
        conn.execute("""
            INSERT INTO amendments (act_refid, change_type, target, instruction, new_text)
            VALUES (?, ?, ?, ?, ?)
        """, (act.refid, a.change_type, a.target, a.instruction, a.new_text))


# ─── Commit Message Formatting ──────────────────────────────────────────────

CHANGE_TYPE_LABELS = {
    "change": "endret",
    "repeal": "opphevet",
    "add": "tilføyd",
    "move": "flyttet",
}

def format_commit_message(act: AmendmentAct) -> str:
    effective_date, is_deferred = parse_effective_date(act.date_in_force, act.date_published)
    pub_date = parse_publication_date(act.date_published)

    lines = []
    summary = act.short_title or act.title
    if len(summary) > 72:
        summary = summary[:69] + "..."
    lines.append(summary)
    lines.append("")

    lines.append(f"Endringslov: {act.refid}")
    if is_deferred:
        lines.append(f"Ikrafttredelse: {act.date_in_force} (bruker kunngjøringsdato)")
    else:
        lines.append(f"Ikrafttredelse: {effective_date}")
    lines.append(f"Kunngjort: {pub_date}")

    if act.journal_number:
        lines.append(f"Journalnummer: {act.journal_number}")
    if act.misc_info:
        short_misc = act.misc_info[:200]
        lines.append(f"Stortingsvedtak: {short_misc}")

    if act.amendments:
        lines.append("")
        lines.append("Endringer:")
        for a in act.amendments:
            label = CHANGE_TYPE_LABELS.get(a.change_type, a.change_type)
            target_short = a.target.split("/", 2)[-1] if "/" in a.target else a.target
            lines.append(f"  - {target_short}: {label}")

    return "\n".join(lines)


# ─── Git Fast-Import Stream ─────────────────────────────────────────────────

def date_to_git_timestamp(date_str: str) -> str:
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        dt = dt.replace(hour=12, minute=0, second=0, tzinfo=timezone.utc)
        return f"{int(dt.timestamp())} +0100"
    except ValueError:
        return f"{int(datetime(2000, 1, 1, 12, tzinfo=timezone.utc).timestamp())} +0100"


class FastImportStream:
    def __init__(self, repo_path: str, committer_name: str = "Lovtidend", committer_email: str = "lovtidend@lovdata.no"):
        self.repo_path = repo_path
        self.committer_name = committer_name
        self.committer_email = committer_email
        self.mark_counter = 0
        self.commands = []

    def _next_mark(self) -> int:
        self.mark_counter += 1
        return self.mark_counter

    def add_initial_commit(self, files: dict[str, str], timestamp: str, message: str = "Initial import av gjeldende lover"):
        mark = self._next_mark()
        ts = date_to_git_timestamp(timestamp)

        self.commands.append(f"commit refs/heads/main")
        self.commands.append(f"mark :{mark}")
        self.commands.append(f"author {self.committer_name} <{self.committer_email}> {ts}")
        self.commands.append(f"committer {self.committer_name} <{self.committer_email}> {ts}")

        msg_bytes = message.encode("utf-8")
        self.commands.append(f"data {len(msg_bytes)}")
        self.commands.append(message)

        for filepath, content in sorted(files.items()):
            content_bytes = content.encode("utf-8")
            self.commands.append(f"M 100644 inline {filepath}")
            self.commands.append(f"data {len(content_bytes)}")
            self.commands.append(content)

        self.commands.append("")

    def add_amendment_commit(self, act: AmendmentAct, affected_files: dict[str, str | None]):
        effective_date, is_deferred = parse_effective_date(act.date_in_force, act.date_published)
        pub_date = parse_publication_date(act.date_published)
        mark = self._next_mark()

        author_ts = date_to_git_timestamp(effective_date)
        committer_ts = date_to_git_timestamp(pub_date)
        message = format_commit_message(act)
        msg_bytes = message.encode("utf-8")

        self.commands.append(f"commit refs/heads/main")
        self.commands.append(f"mark :{mark}")
        self.commands.append(f"author Stortinget <stortinget@stortinget.no> {author_ts}")
        self.commands.append(f"committer {self.committer_name} <{self.committer_email}> {committer_ts}")
        self.commands.append(f"data {len(msg_bytes)}")
        self.commands.append(message)

        for filepath, content in sorted(affected_files.items()):
            if content is None:
                self.commands.append(f"D {filepath}")
            else:
                content_bytes = content.encode("utf-8")
                self.commands.append(f"M 100644 inline {filepath}")
                self.commands.append(f"data {len(content_bytes)}")
                self.commands.append(content)

        self.commands.append("")

    def write_stream(self, output_path: str):
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(self.commands))
            f.write("\n")

    def execute(self):
        stream = "\n".join(self.commands) + "\n"
        proc = subprocess.run(
            ["git", "fast-import", "--quiet"],
            input=stream.encode("utf-8"),
            cwd=self.repo_path,
            capture_output=True,
        )
        if proc.returncode != 0:
            raise RuntimeError(f"git fast-import failed: {proc.stderr.decode()}")
        subprocess.run(["git", "checkout", "main"], cwd=self.repo_path, capture_output=True)


# ─── Yearly Tags ─────────────────────────────────────────────────────────────

def create_yearly_tags(repo_path: str) -> dict[str, str]:
    log = subprocess.run(
        ["git", "log", "--format=%H %aI", "--reverse"],
        cwd=repo_path, capture_output=True, text=True,
    )
    year_commits = {}
    for line in log.stdout.strip().split("\n"):
        if not line.strip():
            continue
        sha, date = line.split(" ", 1)
        year = date[:4]
        year_commits[year] = sha

    tags = {}
    for year in sorted(year_commits):
        tag_name = f"v{year}"
        subprocess.run(
            ["git", "tag", "-f", tag_name, year_commits[year]],
            cwd=repo_path, capture_output=True,
        )
        tags[tag_name] = year_commits[year]

    return tags


# ─── Full Pipeline ───────────────────────────────────────────────────────────

def run_pipeline(
    gjeldende_archive: str = "gjeldende-lover.tar.bz2",
    lovtidend_archives: list[str] = None,
    output_dir: str = "norwegian-laws",
    db_path: str = "amendments.db",
):
    if lovtidend_archives is None:
        lovtidend_archives = []

    repo_path = Path(output_dir)

    # Step 1: Parse consolidated laws into markdown
    print("=" * 60)
    print("STEP 1: Parsing consolidated laws")
    print("=" * 60)
    law_files = parse_consolidated_archive(gjeldende_archive, str(repo_path))
    print(f"  Parsed {len(law_files)} laws into Markdown")

    # Read all generated files
    all_files = {}
    for refid, filepath in law_files.items():
        full_path = repo_path / filepath
        all_files[filepath] = full_path.read_text(encoding="utf-8")

    # Step 2: Parse lovtidend amendments
    print()
    print("=" * 60)
    print("STEP 2: Parsing Lovtidend amendments")
    print("=" * 60)
    all_acts = []
    for archive in lovtidend_archives:
        print(f"  Processing {archive}...")
        acts = parse_lovtidend_archive(archive, prefix_filter="nl-")
        print(f"    Found {len(acts)} law amendment acts")
        all_acts.extend(acts)

    # Store in SQLite
    conn = init_db(db_path)
    for act in all_acts:
        store_amendment_act(conn, act)
    conn.commit()

    total_amendments = conn.execute("SELECT SUM(amendment_count) FROM amendment_acts").fetchone()[0] or 0
    deferred = conn.execute("SELECT COUNT(*) FROM amendment_acts WHERE is_deferred = 1").fetchone()[0]
    print(f"  Total: {len(all_acts)} acts, {total_amendments} individual amendments")
    print(f"  Deferred (Kongen bestemmer): {deferred}")

    # Step 3: Initialize git repo and create commits
    print()
    print("=" * 60)
    print("STEP 3: Building git repository")
    print("=" * 60)

    subprocess.run(["git", "init", "--initial-branch=main", str(repo_path)], capture_output=True)
    subprocess.run(["git", "config", "user.name", "Lovtidend"], cwd=str(repo_path), capture_output=True)
    subprocess.run(["git", "config", "user.email", "lovtidend@lovdata.no"], cwd=str(repo_path), capture_output=True)

    stream = FastImportStream(str(repo_path))

    # Initial commit with all current laws
    today = datetime.now().strftime("%Y-%m-%d")
    stream.add_initial_commit(
        all_files,
        timestamp=today,
        message=f"Import av {len(all_files)} gjeldende lover\n\nKilde: Lovdata API (gjeldende-lover.tar.bz2)\nDato: {today}\nLisens: NLOD 2.0 (https://data.norge.no/nlod/no/2.0)",
    )
    print(f"  Initial commit: {len(all_files)} law files")

    # Amendment commits sorted by effective date
    rows = conn.execute("""
        SELECT refid, date_in_force_resolved, date_published
        FROM amendment_acts
        ORDER BY date_in_force_resolved ASC, date_published ASC
    """).fetchall()

    for refid, eff_date, pub_date in rows:
        act = next(a for a in all_acts if a.refid == refid)

        affected = {}
        for law_refid in act.changes_to:
            filepath = refid_to_filepath(law_refid)
            if filepath in all_files:
                content = all_files[filepath]
                if "sist-endret:" in content:
                    content = re.sub(
                        r'sist-endret: ".*?"',
                        f'sist-endret: "{act.refid}"',
                        content,
                        count=1,
                    )
                else:
                    content = content.replace(
                        "\n---\n\n",
                        f'\nsist-endret: "{act.refid}"\n---\n\n',
                        1,
                    )
                affected[filepath] = content
                all_files[filepath] = content
            else:
                affected[filepath] = f"---\nrefid: \"{law_refid}\"\nsist-endret: \"{act.refid}\"\n---\n\n# {law_refid}\n\n(Lov ikke i gjeldende-lover arkiv)\n"

        if affected:
            stream.add_amendment_commit(act, affected)

    print(f"  Generated {stream.mark_counter} commits (1 initial + {stream.mark_counter - 1} amendments)")

    # Execute fast-import
    print("  Running git fast-import...")
    stream.execute()

    # Verify
    log = subprocess.run(
        ["git", "log", "--oneline", "--no-walk", "--all"],
        cwd=str(repo_path), capture_output=True, text=True
    )
    total_commits = subprocess.run(
        ["git", "rev-list", "--count", "HEAD"],
        cwd=str(repo_path), capture_output=True, text=True
    )

    print(f"  Repository created: {total_commits.stdout.strip()} commits")

    conn.close()

    # Summary stats
    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    repo_size = sum(f.stat().st_size for f in repo_path.rglob("*") if f.is_file()) / (1024 * 1024)
    git_size = sum(f.stat().st_size for f in (repo_path / ".git").rglob("*") if f.is_file()) / (1024 * 1024)
    print(f"  Laws:      {len(all_files)}")
    print(f"  Commits:   {total_commits.stdout.strip()}")
    print(f"  Repo size: {repo_size:.1f} MB (git: {git_size:.1f} MB)")
    print(f"  Path:      {repo_path.absolute()}")

    return str(repo_path)


if __name__ == "__main__":
    import sys

    lovtidend = []
    if os.path.exists("lovtidend-2026.tar.bz2"):
        lovtidend.append("lovtidend-2026.tar.bz2")

    run_pipeline(
        gjeldende_archive="gjeldende-lover.tar.bz2",
        lovtidend_archives=lovtidend,
        output_dir="norwegian-laws",
        db_path="amendments.db",
    )
