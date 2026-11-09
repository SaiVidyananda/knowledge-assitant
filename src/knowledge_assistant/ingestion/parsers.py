from html.parser import HTMLParser
from pathlib import Path
import zipfile

from knowledge_assistant.ingestion.errors import (
    DocumentParseError,
    MissingParserDependencyError,
)
from knowledge_assistant.ingestion.models import ParsedPage


class _HTMLTextParser(HTMLParser):
    _BLOCK_TAGS = frozenset(
        {"address", "article", "br", "div", "li", "main", "p", "section", "tr"}
    )
    _IGNORED_TAGS = frozenset({"script", "style", "noscript"})

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[tuple[str, str | None]] = []
        self.section: str | None = None
        self._heading_parts: list[str] | None = None
        self._ignored_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in self._IGNORED_TAGS:
            self._ignored_depth += 1
        elif tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self._heading_parts = []
        elif tag in self._BLOCK_TAGS:
            self._add_boundary()

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in self._IGNORED_TAGS and self._ignored_depth:
            self._ignored_depth -= 1
        elif tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            if self._heading_parts is not None:
                heading = " ".join(" ".join(self._heading_parts).split())
                if heading:
                    self.section = heading
                    self._add_boundary()
                    self.parts.append((heading, self.section))
                    self._add_boundary()
                self._heading_parts = None
        elif tag in self._BLOCK_TAGS:
            self._add_boundary()

    def handle_data(self, data: str) -> None:
        if self._ignored_depth or not data.strip():
            return
        if self._heading_parts is not None:
            self._heading_parts.append(data)
        else:
            self.parts.append((data, self.section))

    def _add_boundary(self) -> None:
        if self.parts and self.parts[-1][0] != "\n":
            self.parts.append(("\n", self.section))


def parse_file(path: str | Path) -> list[ParsedPage]:
    """Extract text and available structure from a supported file."""
    source = Path(path)
    extension = source.suffix.lower()
    try:
        if extension == ".pdf":
            return _parse_pdf(source)
        if extension == ".docx":
            return _parse_docx(source)
        if extension in {".html", ".htm"}:
            return _parse_html(source)
        if extension in {".txt", ".md"}:
            return _parse_text(source)
    except (OSError, UnicodeError, ValueError, zipfile.BadZipFile) as exc:
        raise DocumentParseError(f"Could not parse {source}: {exc}") from exc

    raise DocumentParseError(f"No parser is registered for {source.suffix or source.name}")


def _parse_text(path: Path) -> list[ParsedPage]:
    return [ParsedPage(text=path.read_text(encoding="utf-8-sig"), page_number=1)]


def _parse_html(path: Path) -> list[ParsedPage]:
    parser = _HTMLTextParser()
    parser.feed(path.read_text(encoding="utf-8-sig"))
    parser.close()

    sections: list[tuple[str | None, list[str]]] = []
    for part, section in parser.parts:
        if not sections or sections[-1][0] != section:
            sections.append((section, []))
        sections[-1][1].append(part)

    return [
        ParsedPage(text="".join(parts), page_number=1, section=section)
        for section, parts in sections
        if "".join(parts).strip()
    ]


def _parse_pdf(path: Path) -> list[ParsedPage]:
    try:
        import fitz
    except ImportError as exc:
        raise MissingParserDependencyError(
            "PDF parsing requires PyMuPDF. Install the 'pymupdf' package."
        ) from exc

    try:
        with fitz.open(path) as pdf:
            return [
                ParsedPage(text=page.get_text("text"), page_number=index)
                for index, page in enumerate(pdf, start=1)
            ]
    except (RuntimeError, ValueError) as exc:
        raise DocumentParseError(f"Could not parse PDF {path}: {exc}") from exc


def _parse_docx(path: Path) -> list[ParsedPage]:
    try:
        from docx import Document
    except ImportError as exc:
        raise MissingParserDependencyError(
            "DOCX parsing requires python-docx. Install the 'python-docx' package."
        ) from exc

    document = Document(path)
    sections: list[ParsedPage] = []
    current_section: str | None = None
    current_parts: list[str] = []

    def flush_section() -> None:
        text = "\n".join(part for part in current_parts if part)
        if text.strip():
            sections.append(ParsedPage(text=text, section=current_section))
        current_parts.clear()

    for paragraph in document.paragraphs:
        text = paragraph.text.strip()
        if not text:
            continue
        if paragraph.style and paragraph.style.name.startswith("Heading"):
            flush_section()
            current_section = text
        current_parts.append(text)

    for table in document.tables:
        for row in table.rows:
            cells = [cell.text.strip().replace("\n", " ") for cell in row.cells]
            if any(cells):
                current_parts.append(" | ".join(cells))

    flush_section()
    return sections
