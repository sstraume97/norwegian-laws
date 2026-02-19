"""Structured data models for parsed Norwegian law data.

These models define the snapshot format — the contract between lovdata-loader
and lovdata-publisher. The loader produces these; the publisher consumes them
(via JSON serialization, not direct import).
"""
from dataclasses import dataclass, field, asdict
import json


@dataclass
class ListItem:
    """A single list item inside a legal paragraph (e.g. 'a) some text')."""
    identifier: str       # e.g. "a)", "1.", "-"
    text: str


@dataclass
class Paragraph:
    """A legal paragraph (ledd) within an article."""
    text: str
    list_items: list[ListItem] = field(default_factory=list)


@dataclass
class Article:
    """A legal article (§/paragraf) within a section or at the top level."""
    name: str             # e.g. "§ 1-1"
    header_text: str      # e.g. "§ 1-1. Lovens virkeområde"
    paragraphs: list[Paragraph] = field(default_factory=list)


@dataclass
class Section:
    """A section (kapittel/del/avsnitt) containing articles."""
    heading: str
    articles: list[Article] = field(default_factory=list)


@dataclass
class LawData:
    """A fully parsed consolidated law."""
    refid: str
    title: str
    short_title: str
    ministry: str
    date_in_force: str
    last_amended: str
    last_amended_in_force: str
    legal_area: str
    sections: list[Section] = field(default_factory=list)
    top_level_articles: list[Article] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self, indent: int = 1) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

    @classmethod
    def from_dict(cls, d: dict) -> "LawData":
        sections = [
            Section(
                heading=s["heading"],
                articles=[
                    Article(
                        name=a["name"],
                        header_text=a["header_text"],
                        paragraphs=[
                            Paragraph(
                                text=p["text"],
                                list_items=[ListItem(**li) for li in p.get("list_items", [])],
                            )
                            for p in a.get("paragraphs", [])
                        ],
                    )
                    for a in s.get("articles", [])
                ],
            )
            for s in d.get("sections", [])
        ]
        top_level = [
            Article(
                name=a["name"],
                header_text=a["header_text"],
                paragraphs=[
                    Paragraph(
                        text=p["text"],
                        list_items=[ListItem(**li) for li in p.get("list_items", [])],
                    )
                    for p in a.get("paragraphs", [])
                ],
            )
            for a in d.get("top_level_articles", [])
        ]
        return cls(
            refid=d["refid"],
            title=d["title"],
            short_title=d.get("short_title", ""),
            ministry=d.get("ministry", ""),
            date_in_force=d.get("date_in_force", ""),
            last_amended=d.get("last_amended", ""),
            last_amended_in_force=d.get("last_amended_in_force", ""),
            legal_area=d.get("legal_area", ""),
            sections=sections,
            top_level_articles=top_level,
        )


@dataclass
class Amendment:
    """A single amendment instruction within an amendment act."""
    change_type: str      # change | repeal | add | move | unknown
    target: str           # e.g. lov/1999-07-02-64/§21
    instruction: str      # e.g. "§ 21 skal lyde:"
    new_text: str


@dataclass
class AmendmentActData:
    """A parsed Lovtidend amendment act."""
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


@dataclass
class Manifest:
    """Metadata about a snapshot."""
    version: int
    created_at: str
    loader_version: str
    gjeldende_archive: str
    lovtidend_archives: list[str]
    law_count: int
    amendment_act_count: int
    amendment_count: int

    def to_json(self, indent: int = 1) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, indent=indent)

    @classmethod
    def from_dict(cls, d: dict) -> "Manifest":
        return cls(**d)
