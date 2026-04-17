from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from bs4 import BeautifulSoup

from mfr_phase1.config import CHUNK_OVERLAP_CHARS, MAX_CHUNK_CHARS, MIN_CHUNK_CHARS
from mfr_phase1.registry import SourceRecord


@dataclass(frozen=True)
class TextChunk:
    text: str
    chunk_index: int
    section_title: str
    content_hash: str


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _flatten_tables(soup: BeautifulSoup) -> str:
    lines: list[str] = []
    for table in soup.find_all("table"):
        for row in table.find_all("tr"):
            cells = [c.get_text(" ", strip=True) for c in row.find_all(["th", "td"])]
            cells = [c for c in cells if c]
            if cells:
                if len(cells) >= 2:
                    lines.append(f"{cells[0]}: {' | '.join(cells[1:])}")
                else:
                    lines.append(cells[0])
    return "\n".join(lines)


def html_to_document_text(html: str) -> tuple[str, str]:
    """Return (plain text, page_title)."""
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    title_tag = soup.find("title")
    page_title = title_tag.get_text(strip=True) if title_tag else ""

    table_text = _flatten_tables(soup)
    for table in soup.find_all("table"):
        table.decompose()

    main = soup.find("main") or soup.find("article") or soup.body
    if main is None:
        body_text = ""
    else:
        body_text = main.get_text("\n", strip=True)

    parts = [p for p in (body_text, table_text) if p]
    full = "\n\n".join(parts)
    full = re.sub(r"\n{3,}", "\n\n", full).strip()
    return full, page_title


def _split_sections(html: str) -> list[tuple[str, str]]:
    """Split into (section_title, section_text) using h2/h3 when possible."""
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    body = soup.body or soup
    headings = body.find_all(["h2", "h3"])
    if not headings:
        text, _ = html_to_document_text(html)
        return [("", text)]

    sections: list[tuple[str, str]] = []
    for h in headings:
        title = h.get_text(" ", strip=True)
        chunks_text: list[str] = []
        for sib in h.find_next_siblings():
            if sib.name in ("h2", "h3"):
                break
            if getattr(sib, "name", None) == "table":
                for row in sib.find_all("tr"):
                    cells = [c.get_text(" ", strip=True) for c in row.find_all(["th", "td"])]
                    cells = [c for c in cells if c]
                    if len(cells) >= 2:
                        chunks_text.append(f"{cells[0]}: {' | '.join(cells[1:])}")
                    elif cells:
                        chunks_text.append(cells[0])
            else:
                t = sib.get_text("\n", strip=True) if hasattr(sib, "get_text") else ""
                if t:
                    chunks_text.append(t)
        section_body = "\n".join(chunks_text).strip()
        if title or section_body:
            sections.append((title, section_body))

    if not sections:
        text, _ = html_to_document_text(html)
        return [("", text)]
    return sections


def _char_chunks(text: str, section_title: str, start_index: int) -> list[TextChunk]:
    text = text.strip()
    if len(text) < MIN_CHUNK_CHARS:
        if not text:
            return []
        h = _hash_text(text)
        return [TextChunk(text=text, chunk_index=start_index, section_title=section_title, content_hash=h)]

    out: list[TextChunk] = []
    i = 0
    idx = start_index
    while i < len(text):
        end = min(len(text), i + MAX_CHUNK_CHARS)
        if end < len(text):
            window = text[i:end]
            break_at = max(window.rfind("\n"), window.rfind(". "), window.rfind(" "))
            if break_at > MIN_CHUNK_CHARS:
                end = i + break_at + 1
        piece = text[i:end].strip()
        if len(piece) >= MIN_CHUNK_CHARS or (not out and piece):
            h = _hash_text(piece)
            out.append(TextChunk(text=piece, chunk_index=idx, section_title=section_title, content_hash=h))
            idx += 1
        if end >= len(text):
            break
        i = max(i + 1, end - CHUNK_OVERLAP_CHARS)
    return out


def chunk_source_html(html: str, source: SourceRecord) -> list[TextChunk]:
    """Produce overlapping text chunks with section hints (per ragChunkingEmbeddingVectorDb.md)."""
    sections = _split_sections(html)
    pieces: list[TextChunk] = []
    for sec_title, sec_body in sections:
        merged_title = sec_title or source.scheme_name
        pieces.extend(_char_chunks(sec_body, merged_title, start_index=0))

    if not pieces:
        text, _ = html_to_document_text(html)
        pieces = _char_chunks(text, source.scheme_name, start_index=0)

    return [
        TextChunk(
            text=c.text,
            chunk_index=i,
            section_title=c.section_title,
            content_hash=c.content_hash,
        )
        for i, c in enumerate(pieces)
    ]


def stable_chunk_id(source_url: str, chunk: TextChunk) -> str:
    raw = f"{source_url}|{chunk.chunk_index}|{chunk.content_hash}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
