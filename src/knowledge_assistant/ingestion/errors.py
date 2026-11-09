class IngestionError(Exception):
    """Base error for document ingestion failures."""


class UnsupportedFileTypeError(IngestionError):
    """Raised when a source file uses an unsupported format."""


class MissingParserDependencyError(IngestionError):
    """Raised when parsing a format requires an unavailable dependency."""


class DocumentParseError(IngestionError):
    """Raised when a supported source cannot be parsed."""
