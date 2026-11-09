from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
from pathlib import Path

from knowledge_assistant.ingestion.chunkers import ChunkingConfig, chunk_document
from knowledge_assistant.ingestion.cleaners import clean_text
from knowledge_assistant.ingestion.errors import IngestionError
from knowledge_assistant.ingestion.loaders import discover_files
from knowledge_assistant.ingestion.models import DocumentChunk, DocumentMetadata, ParsedPage
from knowledge_assistant.ingestion.parsers import parse_file


@dataclass(frozen=True, slots=True)
class DocumentFailure:
    source_path: str
    error_type: str
    message: str


@dataclass(frozen=True, slots=True)
class IngestionResult:
    chunks: list[DocumentChunk]
    failures: list[DocumentFailure]


def ingest_path(
    source: str | Path,
    *,
    chunking: ChunkingConfig | None = None,
    continue_on_error: bool = False,
) -> IngestionResult:
    """Load, parse, clean, and chunk supported files from a source path."""
    root = Path(source).expanduser()
    files = discover_files(root)
    chunks: list[DocumentChunk] = []
    failures: list[DocumentFailure] = []

    for path in files:
        try:
            metadata = _build_metadata(path, root)
            parsed_pages = parse_file(path)
            cleaned_pages = [
                ParsedPage(
                    text=clean_text(page.text),
                    page_number=page.page_number,
                    section=page.section,
                )
                for page in parsed_pages
            ]
            chunks.extend(chunk_document(cleaned_pages, metadata, chunking))
        except (IngestionError, OSError) as exc:
            if not continue_on_error:
                raise
            failures.append(
                DocumentFailure(
                    source_path=_relative_path(path, root),
                    error_type=type(exc).__name__,
                    message=str(exc),
                )
            )

    return IngestionResult(chunks=chunks, failures=failures)


def _build_metadata(path: Path, root: Path) -> DocumentMetadata:
    content_hash = hashlib.sha256(path.read_bytes()).hexdigest()
    source_path = _relative_path(path, root)
    document_id = hashlib.sha256(source_path.encode("utf-8")).hexdigest()[:16]
    return DocumentMetadata(
        document_id=document_id,
        document_name=path.name,
        document_version=content_hash,
        source_path=source_path,
        source_type=path.suffix.lower().lstrip("."),
        content_hash=content_hash,
        ingestion_timestamp=datetime.now(UTC).isoformat(),
    )


def _relative_path(path: Path, root: Path) -> str:
    if root.is_dir():
        return path.relative_to(root).as_posix()
    return path.name
