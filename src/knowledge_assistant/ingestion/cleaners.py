import re
import unicodedata


_CONTROL_CHARACTERS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_MULTIPLE_SPACES = re.compile(r"[ \t]+")
_EXCESSIVE_NEWLINES = re.compile(r"\n{3,}")


def clean_text(text: str) -> str:
    """Normalize extracted text while preserving paragraph and line boundaries."""
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _CONTROL_CHARACTERS.sub("", text)
    lines = (_MULTIPLE_SPACES.sub(" ", line).strip() for line in text.split("\n"))
    return _EXCESSIVE_NEWLINES.sub("\n\n", "\n".join(lines)).strip()
