from pathlib import Path
from typing import Iterator

from knowledge_assistant.ingestion.errors import UnsupportedFileTypeError

SUPPORTED_EXTENSIONS = frozenset({".pdf", ".docx", ".html", ".htm", ".txt", ".md"})


def discover_files(source: str | Path) -> Iterator[Path]:
    """Yield supported files in stable order from a file or directory."""
    path = Path(source).expanduser()
    if not path.exists():
        raise FileNotFoundError(f"Ingestion source does not exist: {path}")
    if path.is_file():
        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            raise UnsupportedFileTypeError(
                f"Unsupported file type {path.suffix or '(no extension)'}: {path}"
            )
        yield path
        return
    if not path.is_dir():
        raise ValueError(f"Ingestion source is not a regular file or directory: {path}")

    for candidate in sorted(path.rglob("*")):
        if candidate.is_file() and candidate.suffix.lower() in SUPPORTED_EXTENSIONS:
            yield candidate
