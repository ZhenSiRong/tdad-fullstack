"""Multi-language parser dispatch.

Each language has its own parser module exporting a `parse_file(path, repo_root) -> FileInfo`
function. The dispatcher (see `dispatcher.py`) routes files by extension.
"""
from .base import LanguageParser, get_parser_for_path
from .dispatcher import (
    EXTENSION_LANGUAGE_MAP,
    get_parser_registry,
    language_for_path,
    parse_file_for_language,
)

__all__ = [
    "EXTENSION_LANGUAGE_MAP",
    "LanguageParser",
    "get_parser_for_path",
    "get_parser_registry",
    "language_for_path",
    "parse_file_for_language",
]
