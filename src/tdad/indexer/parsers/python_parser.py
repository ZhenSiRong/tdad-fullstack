"""Python parser — thin wrapper around the upstream stdlib-ast parser.

Kept separate so callers can introspect `language_id == "python"` and so the
dispatcher stays symmetric across languages.
"""
from pathlib import Path

from ..ast_parser import FileInfo, parse_file as _upstream_parse_file
from .base import LanguageParser


class PythonParser(LanguageParser):
    language_id = "python"
    extensions = (".py",)

    def parse_file(self, path: Path, repo_root: Path) -> FileInfo:
        return _upstream_parse_file(path, repo_root)
