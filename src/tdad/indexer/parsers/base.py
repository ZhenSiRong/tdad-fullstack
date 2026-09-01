"""Language parser abstract base.

Every language parser implements `parse_file(path, repo_root) -> FileInfo`,
producing the same shape as the original `tdad.indexer.ast_parser.parse_file`.
This keeps the upstream graph builder / linker code unchanged.
"""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from ..ast_parser import FileInfo


class LanguageParser(ABC):
    """Abstract base for all language parsers."""

    language_id: str = "unknown"  # e.g. "python", "javascript", "typescript", "vue", "go"

    @abstractmethod
    def parse_file(self, path: Path, repo_root: Path) -> FileInfo:
        """Parse a single file and return extracted information."""

    def supports(self, path: Path) -> bool:
        """Default extension-based check; override for richer rules (e.g. .vue)."""
        return path.suffix.lower() in self.extensions

    extensions: tuple = ()


def get_parser_for_path(path: Path, parsers: dict) -> Optional[LanguageParser]:
    """Pick the right parser by suffix.

    `parsers` is a dict like `{"python": PythonParser(), "javascript": JSParser(), ...}`.
    Returns None if no parser handles the file extension.
    """
    suffix = path.suffix.lower()
    # Vue files are special-cased
    if suffix == ".vue":
        return parsers.get("vue")
    # Map suffix -> language id
    ext_map = {
        ".py": "python",
        ".js": "javascript",
        ".mjs": "javascript",
        ".cjs": "javascript",
        ".jsx": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".go": "go",
    }
    lang_id = ext_map.get(suffix)
    if lang_id is None:
        return None
    return parsers.get(lang_id)
