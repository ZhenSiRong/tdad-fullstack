"""Go parser via tree-sitter."""
from pathlib import Path

import tree_sitter_go

from ..ast_parser import FileInfo
from ._ts_helpers import NodeSpec, make_language, parse_with_tree_sitter
from .base import LanguageParser


_GO_LANGUAGE = make_language(tree_sitter_go.language())

_GO_SPEC = NodeSpec(
    import_node_types=["import_declaration"],
    function_node_types=[
        "function_declaration",
        "method_declaration",
    ],
    class_node_types=["type_spec"],  # Go's `type X struct` is a type_spec, not a class
)


class GoParser(LanguageParser):
    language_id = "go"
    extensions = (".go",)

    def parse_file(self, path: Path, repo_root: Path) -> FileInfo:
        source = path.read_bytes()
        info = parse_with_tree_sitter(_GO_LANGUAGE, source, str(path), repo_root, _GO_SPEC)
        # Go test detection: foo_test.go (strict convention)
        from ..ast_parser import is_test_file
        info.is_test_file = path.name.endswith("_test.go")
        return info
