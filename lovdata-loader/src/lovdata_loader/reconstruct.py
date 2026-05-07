"""Reconstruct historical law text from amendment timeline.

Given the current consolidated law (from gjeldende-lover) and the amendment
database (from Lovtidend), produce the law text at each historical version.

Full replacements (§ X-Y skal lyde:) give exact historical text.
Partial amendments modify individual ledd within the working copy.
"""
import re
import sqlite3
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class ArticleVersion:
    date: str
    article: str
    scope: str
    new_text: str
    instruction: str


def parse_article_and_scope(instr: str) -> tuple[str, str]:
    text = instr.strip()
    is_new = bool(re.match(r"Ny[ets]?\s", text))

    m = re.search(r"§\s*(\d+-\d+)", text)
    if not m:
        return "", "unknown"

    nr = m.group(1)
    after = text[m.end():]

    suffix = ""
    sm = re.match(r"\s?([a-e])(?:\s|$)", after)
    if sm:
        suffix = sm.group(1)
        after = after[sm.end():]
    else:
        after = after.lstrip()

    art = f"§ {nr}{suffix}"
    rest = after.strip()

    if is_new:
        return art, "new"
    if not rest or rest.startswith("skal lyde"):
        return art, "full"
    if re.match(r"oppheves\.?\s*$", rest):
        return art, "repeal"
    return art, "partial"


def load_amendment_timeline(
    db_path: str, target_law: str
) -> list[ArticleVersion]:
    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        """
        SELECT a.date_in_force_resolved, am.instruction, am.new_text, am.change_type
        FROM amendments am
        JOIN amendment_acts a ON am.act_refid = a.refid
        WHERE am.target_law = ?
        AND am.change_type IN ('change', 'add', 'repeal')
        ORDER BY a.date_in_force_resolved ASC
        """,
        (target_law,),
    ).fetchall()
    conn.close()

    versions = []
    for date, instr, text, ctype in rows:
        art, scope = parse_article_and_scope(instr)
        if not art:
            continue
        versions.append(ArticleVersion(
            date=date, article=art, scope=scope,
            new_text=text, instruction=instr,
        ))
    return versions


def reconstruct_law_versions(
    db_path: str,
    target_law: str,
    current_articles: dict[str, str],
) -> list[tuple[str, dict[str, str]]]:
    """Produce law article text at each amendment date.

    Returns [(date, {article_name: text}), ...] sorted chronologically.
    Between dates, the text is stable (use the most recent snapshot).
    """
    timeline = load_amendment_timeline(db_path, target_law)
    if not timeline:
        return []

    dates = sorted(set(v.date for v in timeline))

    fulls_by_art = defaultdict(list)
    for v in timeline:
        if v.scope in ("full", "new"):
            fulls_by_art[v.article].append(v)

    initial = dict(current_articles)
    for art, versions in fulls_by_art.items():
        if art in initial:
            initial[art] = f"[Originaltekst før {versions[0].date}]"

    state = dict(initial)
    snapshots = []

    for date in dates:
        day_events = [v for v in timeline if v.date == date]
        changed = False
        for v in day_events:
            if v.scope in ("full", "new"):
                state[v.article] = v.new_text
                changed = True
            elif v.scope == "repeal":
                if v.article in state:
                    state[v.article] = "(Opphevet)"
                    changed = True
        if changed:
            snapshots.append((date, dict(state)))

    return snapshots
