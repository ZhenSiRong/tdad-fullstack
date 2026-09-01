"""Vue SFC parser.

Strategy: split the SFC into <script>, <template>, <style> blocks with a
small regex (Vue 3 SFC grammar is simple enough for this). Feed the
<script> block to the JavaScript parser. The template/style blocks are
ignored for impact-analysis purposes — only the script's imports,
functions, and classes matter for "find impacted tests".

This avoids pulling in @vue/compiler-sfc (a Node.js dependency).
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import List

from ..ast_parser import FileInfo
from .base import LanguageParser
from .js_parser import JavaScriptParser


_SCRIPT_RE = re.compile(
    r"<script(?P<attrs>[^>]*)>(?P<body>.*?)</script>",
    re.DOTALL | re.IGNORECASE,
)


def _extract_script_blocks(source: str) -> List[str]:
    """Return the inner content of every <script> block in the SFC."""
    return [m.group("body") for m in _SCRIPT_RE.finditer(source)]


class VueParser(LanguageParser):
    """Parses .vue Single File Components by extracting the <script> block.

    Note: this is a *language-id* of `vue` rather than `javascript` so that
    downstream test-runner dispatch can route Vitest with the right config.
    """
    language_id = "vue"
    extensions = (".vue",)

    def __init__(self):
        self._js_parser = JavaScriptParser()

    def parse_file(self, path: Path, repo_root: Path) -> FileInfo:
        source = path.read_text(encoding="utf-8")
        script_blocks = _extract_script_blocks(source)

        if not script_blocks:
            # No <script> block — Vue SFC with template-only or pure-style file.
            # Return an empty FileInfo; impact analysis will skip it.
            from ..ast_parser import FileInfo
            import hashlib
            return FileInfo(
                path=str(path),
                relative_path=path.name,
                name=path.name,
                content_hash=hashlib.md5(source.encode()).hexdigest(),
                is_test_file=path.name.endswith(".spec.vue") or path.name.endswith(".test.vue"),
            )

        # Concatenate all <script> blocks and parse as a JS buffer.
        combined = "\n;\n".join(script_blocks)
        combined_bytes = combined.encode("utf-8")

        # Reuse the JavaScript parser's pipeline by faking a path the JS parser
        # can read. We can't reuse the public `parse_file` because that re-reads
        # from disk. So we re-implement minimally: pass the JS language + spec
        # directly via the tree-sitter helper.
        from ._ts_helpers import NodeSpec, parse_with_tree_sitter
        import tree_sitter_javascript
        from ._ts_helpers import make_language

        # Inline JS node spec — matches what JavaScriptParser uses.
        spec = NodeSpec(
            import_node_types=["import_statement"],
            function_node_types=[
                "function_declaration",
                "method_definition",
                "generator_function_declaration",
            ],
            class_node_types=["class_declaration"],
        )

        info = parse_with_tree_sitter(
            make_language(tree_sitter_javascript.language()),
            combined_bytes,
            str(path),
            repo_root,
            spec,
        )
        info.is_test_file = path.name.endswith(".spec.vue") or path.name.endswith(".test.vue")
        return info
