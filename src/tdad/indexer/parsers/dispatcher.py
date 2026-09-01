"""Language parser registry + dispatch.

Use `get_parser_registry()` once at startup to build the dict; call
`parse_file_for_language(path, repo_root, registry)` per file.

Files with unsupported extensions return None so callers can skip them.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

from ..ast_parser import FileInfo
from .base import LanguageParser
from .go_parser import GoParser
from .js_parser import JavaScriptParser, TypeScriptParser
from .python_parser import PythonParser
from .vue_parser import VueParser


EXTENSION_LANGUAGE_MAP: Dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".vue": "vue",
    ".go": "go",
}


def get_parser_registry() -> Dict[str, LanguageParser]:
    """Build the parser registry. Cheap; safe to call repeatedly."""
    return {
        "python": PythonParser(),
        "javascript": JavaScriptParser(),
        "typescript": TypeScriptParser(),
        "vue": VueParser(),
        "go": GoParser(),
    }


def parse_file_for_language(
    path: Path,
    repo_root: Path,
    registry: Dict[str, LanguageParser],
) -> Optional[FileInfo]:
    """Dispatch to the right parser based on file suffix.

    Returns None if no parser handles this file. Callers should skip None.
    """
    from .base import get_parser_for_path

    parser = get_parser_for_path(path, registry)
    if parser is None:
        return None
    return parser.parse_file(path, repo_root)


def language_for_path(path: Path) -> Optional[str]:
    """Return the language id for a path, or None if unsupported."""
    return EXTENSION_LANGUAGE_MAP.get(path.suffix.lower())
