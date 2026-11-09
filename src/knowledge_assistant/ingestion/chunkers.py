from dataclasses import dataclass
import re

from knowledge_assistant.ingestion.cleaners import clean_text
from knowledge_assistant.ingestion.models import DocumentChunk, DocumentMetadata, ParsedPage


@dataclass(frozen=True, slots=True)
class ChunkingConfig:
    chunk_size: int = 512
    chunk_overlap: int = 64

    def __post_init__(self) -> None:
        if self.chunk_size <= 0:
            raise ValueError("chunk_size must be greater than zero")
        if self.chunk_overlap < 0:
            raise ValueError("chunk_overlap cannot be negative")
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("chunk_overlap must be smaller than chunk_size")


def chunk_document(
    pages: list[ParsedPage],
    metadata: DocumentMetadata,
    config: ChunkingConfig | None = None,
) -> list[DocumentChunk]:
    """Create overlapping chunks, preferring paragraph, line, and sentence boundaries."""
    options = config or ChunkingConfig()
    chunks: list[DocumentChunk] = []

    for page in pages:
        text = clean_text(page.text)
        tokens = list(re.finditer(r"\S+", text))
        if not tokens:
            continue

        start = 0
        while start < len(tokens):
            end = min(start + options.chunk_size, len(tokens))
            if end < len(tokens):
                end = _preferred_boundary(text, tokens, start, end)

            chunks.append(
                DocumentChunk(
                    chunk_id=f"{metadata.document_id}-{metadata.document_version[:12]}-{len(chunks) + 1:06d}",
                    text=text[tokens[start].start() : tokens[end - 1].end()],
                    metadata=metadata,
                    page_number=page.page_number,
                    section=page.section,
                )
            )
            if end == len(tokens):
                break
            start = end - options.chunk_overlap

    return chunks


def _preferred_boundary(
    text: str, tokens: list[re.Match[str]], start: int, limit: int
) -> int:
    candidates: dict[str, list[int]] = {"paragraph": [], "line": [], "sentence": []}
    for end in range(start + 1, limit):
        separator = text[tokens[end - 1].end() : tokens[end].start()]
        if "\n\n" in separator:
            candidates["paragraph"].append(end)
        elif "\n" in separator:
            candidates["line"].append(end)
        elif re.search(r"[.!?][\"')\]]?$", tokens[end - 1].group()):
            candidates["sentence"].append(end)

    for boundary_type in ("paragraph", "line", "sentence"):
        if candidates[boundary_type]:
            return candidates[boundary_type][-1]
    return limit
