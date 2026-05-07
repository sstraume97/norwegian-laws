"""Reconstruct historical law text from amendment timeline.

Given a current consolidated law (LawData) and a chronological list of
amendments, produce the law text as it read at any historical date.
"""
import copy
import re
from dataclasses import dataclass


_ORDINALS = {
    "første": 1, "andre": 2, "annet": 2, "tredje": 3, "fjerde": 4,
    "femte": 5, "sjette": 6, "syvende": 7, "sjuende": 7, "åttende": 8,
    "niende": 9, "tiende": 10, "ellevte": 11, "tolvte": 12,
    "trettende": 13, "fjortende": 14, "femtende": 15, "sekstende": 16,
    "siste": -1,
}

_LEDD_NUMBER_RE = re.compile(r"^\(\d+\)\s*")


@dataclass
class InstructionSpec:
    paragraph: str
    scope: str
    ledd_start: int | None = None
    ledd_end: int | None = None
    is_new: bool = False
    sub_target: str = ""


def parse_instruction(instruction: str) -> InstructionSpec:
    m = re.match(
        r"(?:Ny(?:tt?)?\s+)?(§\s*\d+[\w-]*(?:\s+[a-z])?)(?:\s+)(.*?)(?:skal lyde|oppheves|$)",
        instruction, re.I,
    )
    if not m:
        if re.match(r"(?:Ny(?:tt?)?\s+)?§\s*\d+[\w-]*(?:\s+[a-z])?\s*$", instruction):
            para_m = re.match(r"(?:Ny(?:tt?)?\s+)?(§\s*\d+[\w-]*(?:\s+[a-z])?)", instruction)
            return InstructionSpec(
                paragraph=para_m.group(1).strip() if para_m else "",
                scope="full",
                is_new=instruction.lower().startswith("ny"),
            )
        return InstructionSpec(paragraph="", scope="unknown")

    para = m.group(1).strip()
    spec_text = m.group(2).strip().rstrip(":").strip()
    is_new = instruction.lower().startswith("ny")

    if not spec_text:
        return InstructionSpec(paragraph=para, scope="full", is_new=is_new)

    if "paragrafoverskrift" in spec_text.lower():
        return InstructionSpec(paragraph=para, scope="heading")

    ledd_m = re.match(
        r"(?:nye?(?:tt?)?\s+)?(\w+)(?:\s+(?:til|og)\s+(\w+))?\s+ledd",
        spec_text,
    )
    if ledd_m:
        start_word = ledd_m.group(1).lower()
        end_word = ledd_m.group(2).lower() if ledd_m.group(2) else None
        start = _ORDINALS.get(start_word)
        end = _ORDINALS.get(end_word) if end_word else start
        is_new_ledd = bool(re.match(r"nye?(?:tt?)?\s", spec_text, re.I))
        remainder = spec_text[ledd_m.end():].strip()
        return InstructionSpec(
            paragraph=para, scope="ledd",
            ledd_start=start, ledd_end=end,
            is_new=is_new_ledd, sub_target=remainder,
        )

    if re.match(r"nr\.", spec_text):
        return InstructionSpec(paragraph=para, scope="item", sub_target=spec_text)

    return InstructionSpec(paragraph=para, scope="partial", sub_target=spec_text)


def _split_new_text_to_ledd(new_text: str) -> list[str]:
    lines = [l for l in new_text.split("\n") if l.strip()]
    return lines if lines else [new_text]


def _strip_ledd_number(text: str) -> str:
    return _LEDD_NUMBER_RE.sub("", text)


def _split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=\.)\s+(?=[A-ZÆØÅ])", text)
    return [p for p in parts if p.strip()]


def _replace_sentence(ledd_text: str, sentence_num: int, new_sentence: str) -> str:
    sentences = _split_sentences(ledd_text)
    if not sentences:
        return new_sentence
    idx = sentence_num - 1
    if idx == -2:
        idx = len(sentences) - 1
    if 0 <= idx < len(sentences):
        sentences[idx] = new_sentence.strip().rstrip(".")
        if not sentences[idx].endswith("."):
            sentences[idx] += "."
        return " ".join(sentences)
    if idx >= len(sentences):
        sentences.append(new_sentence.strip())
        return " ".join(sentences)
    return new_sentence


def _find_article(law_dict: dict, para_name: str) -> tuple[dict | None, list, int]:
    normalized = re.sub(r"\s+", "", para_name)

    def search(sections):
        for section in sections:
            for i, art in enumerate(section.get("articles", [])):
                art_name = re.sub(r"\s+", "", art.get("name", ""))
                if art_name == normalized:
                    return art, section["articles"], i
            found = search(section.get("subsections", []))
            if found[0]:
                return found
        return None, [], -1

    art, parent_list, idx = search(law_dict.get("sections", []))
    if art:
        return art, parent_list, idx
    for i, art in enumerate(law_dict.get("top_level_articles", [])):
        art_name = re.sub(r"\s+", "", art.get("name", ""))
        if art_name == normalized:
            return art, law_dict["top_level_articles"], i
    return None, [], -1


def _parse_punktum_target(sub_target: str) -> int | None:
    m = re.match(r"(\w+)\s+punktum", sub_target)
    if m:
        return _ORDINALS.get(m.group(1).lower())
    return None


def apply_amendment(law_dict: dict, instruction: str, new_text: str,
                    change_type: str = "change") -> bool:
    spec = parse_instruction(instruction)
    if not spec.paragraph:
        return False

    if change_type == "repeal":
        art, parent_list, idx = _find_article(law_dict, spec.paragraph)
        if art:
            art["paragraphs"] = [{"text": "(Opphevet)", "list_items": []}]
            art["trailing_text"] = ""
            return True
        return False

    if spec.is_new and spec.scope == "full":
        ledd_texts = _split_new_text_to_ledd(new_text)
        heading_text = ""
        hm = re.match(r"(§\s*[\d\w-]+\s*[a-z]?\.\s*[^\n]+)", ledd_texts[0])
        if hm:
            heading_text = hm.group(1)
            first_text = ledd_texts[0][len(heading_text):].strip()
            ledd_texts[0] = first_text

        new_art = {
            "name": spec.paragraph.replace(" ", ""),
            "header_text": heading_text,
            "paragraphs": [{"text": t, "list_items": []} for t in ledd_texts if t],
            "trailing_text": "",
        }
        _, parent_list, idx = _find_article(law_dict, spec.paragraph)
        if parent_list:
            parent_list.insert(idx + 1, new_art)
        return True

    art, parent_list, idx = _find_article(law_dict, spec.paragraph)
    if not art:
        return False

    if spec.scope == "full":
        ledd_texts = _split_new_text_to_ledd(new_text)
        hm = re.match(r"(§\s*[\d\w-]+\s*[a-z]?\.\s*[^\n]+)", ledd_texts[0])
        if hm:
            art["header_text"] = hm.group(1)
            first_text = ledd_texts[0][len(hm.group(1)):].strip()
            ledd_texts[0] = first_text

        art["paragraphs"] = [{"text": t, "list_items": []} for t in ledd_texts if t]
        art["trailing_text"] = ""
        return True

    if spec.scope == "heading":
        art["header_text"] = new_text.strip()
        return True

    if spec.scope == "ledd" and spec.ledd_start is not None:
        paragraphs = art.get("paragraphs", [])
        ledd_texts = _split_new_text_to_ledd(new_text)
        new_ledd = [{"text": t, "list_items": []} for t in ledd_texts if t]
        li = spec.ledd_start - 1
        le = (spec.ledd_end or spec.ledd_start) - 1

        if li == -2:
            li = len(paragraphs) - 1
            le = li
        if li < 0:
            return False

        punktum = _parse_punktum_target(spec.sub_target) if spec.sub_target else None

        if spec.is_new:
            insert_at = min(li, len(paragraphs))
            for j, nl in enumerate(new_ledd):
                paragraphs.insert(insert_at + j, nl)
        elif punktum is not None and li < len(paragraphs):
            existing_text = _strip_ledd_number(paragraphs[li].get("text", ""))
            replaced = _replace_sentence(existing_text, punktum, new_text.strip())
            paragraphs[li] = {"text": replaced, "list_items": paragraphs[li].get("list_items", [])}
        elif not spec.sub_target:
            if li <= len(paragraphs):
                paragraphs[li:le + 1] = new_ledd
            else:
                paragraphs.extend(new_ledd)
        else:
            if li < len(paragraphs):
                existing_text = _strip_ledd_number(paragraphs[li].get("text", ""))
                replaced = existing_text.rstrip() + " " + new_text.strip()
                paragraphs[li] = {"text": replaced, "list_items": paragraphs[li].get("list_items", [])}
            else:
                return False
        art["paragraphs"] = paragraphs
        return True

    return False


def strip_trailing_text(law_dict: dict) -> None:
    for section in law_dict.get("sections", []):
        _strip_section_trailing(section)
    for art in law_dict.get("top_level_articles", []):
        art["trailing_text"] = ""


def _strip_section_trailing(section: dict) -> None:
    for art in section.get("articles", []):
        art["trailing_text"] = ""
    for sub in section.get("subsections", []):
        _strip_section_trailing(sub)


def build_paragraph_timeline(amendments: list[dict]) -> dict[str, list[dict]]:
    timeline = {}
    for a in sorted(amendments, key=lambda x: x["date"]):
        spec = parse_instruction(a["instruction"])
        para = spec.paragraph
        if not para:
            continue
        if para not in timeline:
            timeline[para] = []
        timeline[para].append({
            "date": a["date"],
            "spec": spec,
            "change_type": a["change_type"],
            "new_text": a["new_text"],
            "instruction": a["instruction"],
        })
    return timeline
