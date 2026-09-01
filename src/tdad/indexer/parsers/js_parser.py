"""JavaScript / TypeScript family parsers via tree-sitter."""
from pathlib import Path

import tree_sitter_javascript
import tree_sitter_typescript

from ..ast_parser import FileInfo
from ._ts_helpers import NodeSpec, make_language, parse_with_tree_sitter
from .base import LanguageParser


_JS_LANGUAGE = make_language(tree_sitter_javascript.language())

_JS_SPEC = NodeSpec(
    import_node_types=["import_statement"],
    function_node_types=[
        "function_declaration",
        "method_definition",
        "generator_function_declaration",
    ],
    class_node_types=["class_declaration"],
)


class JavaScriptParser(LanguageParser):
    language_id = "javascript"
    extensions = (".js", ".mjs", ".cjs", ".jsx")

    def parse_file(self, path: Path, repo_root: Path) -> FileInfo:
        source = path.read_bytes()
        info = parse_with_tree_sitter(_JS_LANGUAGE, source, str(path), repo_root, _JS_SPEC)
        # JS test detection: *.test.js / *.spec.js / __tests__/ or under tests/
        name = path.name
        info.is_test_file = (
            name.endswith(".test.js")
            or name.endswith(".spec.js")
            or name.endswith(".test.jsx")
            or name.endswith(".spec.jsx")
            or "__tests__" in str(path)
            or "/tests/" in str(path)
        )
        return info


# --- TypeScript -----------------------------------------------------------

_TS_LANGUAGE = make_language(tree_sitter_typescript.language_typescript())

_TS_SPEC = NodeSpec(
    import_node_types=["import_statement"],
    function_node_types=[
        "function_declaration",
        "method_definition",
        "generator_function_declaration",
    ],
    class_node_types=["class_declaration", "interface_declaration", "type_alias_declaration"],
)


class TypeScriptParser(LanguageParser):
    language_id = "typescript"
    extensions = (".ts", ".tsx")

    def parse_file(self, path: Path, repo_root: Path) -> FileInfo:
        source = path.read_bytes()
        info = parse_with_tree_sitter(_TS_LANGUAGE, source, str(path), repo_root, _TS_SPEC)
        # TS test detection: *.test.ts / *.spec.ts / *.test.tsx / *.spec.tsx
        # or under __tests__/ or tests/
        name = path.name
        info.is_test_file = (
            name.endswith(".test.ts")
            or name.endswith(".spec.ts")
            or name.endswith(".test.tsx")
            or name.endswith(".spec.tsx")
            or "__tests__" in str(path)
            or "/tests/" in str(path)
        )
        return info
