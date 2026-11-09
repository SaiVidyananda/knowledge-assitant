from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ParsedPage:
    text: str
    page_number: int | None = None
    section: str | None = None


@dataclass(frozen=True, slots=True)
class DocumentMetadata:
    document_id: str
    document_name: str
    document_version: str
    source_path: str
    source_type: str
    content_hash: str
    ingestion_timestamp: str


@dataclass(frozen=True, slots=True)
class DocumentChunk:
    chunk_id: str
    text: str
    metadata: DocumentMetadata
    page_number: int | None
    section: str | None
