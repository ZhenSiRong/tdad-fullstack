"""Tree-sitter generic helper.

Given a tree-sitter Language + a source buffer, walk the AST and extract:
  - imports   (string list of module specifiers)
  - functions (FunctionInfo list)
  - classes   (ClassInfo list)

Strategy: language-agnostic node-type filtering driven by a `NodeSpec` dataclass
that says "this node type is an import / function / class". This keeps each
language parser a thin configuration over the same walker.

For now we use coarse extraction — enough to support tdad's "find impacted
tests" use case. We don't try to build a full call graph; we capture function
names + signatures + line ranges. That's enough for static-analysis test
linking (test_linker._link_by_static_analysis).
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import tree_sitter
from tree_sitter import Language, Node, Parser

from ..ast_parser import ClassInfo, FileInfo, FunctionInfo


@dataclass
class NodeSpec:
    """Tree-sitter node-type spec for one language.

    `*_node_types` are lists because languages use multiple node names for
    the same concept (e.g. JS has `function_declaration`, `method_definition`,
    and arrow functions assigned to variables).
    """
    import_node_types: List[str]
    function_node_types: List[str]
    class_node_types: List[str]
    # Optional: extra nodes that should appear as functions (e.g. TS `interface`?)
    # Reserved for future use.
    extra_function_node_types: List[str] = field(default_factory=list)


def _node_text(node: Node, source: bytes) -> str:
    return source[node.start_byte:node.end_byte].decode("utf-8", errors="replace")


def _function_name(node: Node, source: bytes) -> Optional[str]:
    """Pull the function name out of common shapes."""
    # function_declaration / function_definition → `name` field
    name_node = node.child_by_field_name("name")
    if name_node is not None:
        return _node_text(name_node, source).strip()
    # method_definition → `name` field (in classes)
    name_node = node.child_by_field_name("name")
    if name_node is not None:
        return _node_text(name_node, source).strip()
    # arrow function / anonymous — try parent assignment (handled by caller)
    return None


def _class_name(node: Node, source: bytes) -> Optional[str]:
    name_node = node.child_by_field_name("name")
    if name_node is not None:
        return _node_text(name_node, source).strip()
    return None


def _extract_imports(root: Node, source: bytes, spec: NodeSpec) -> List[str]:
    imports: List[str] = []
    # iterative DFS starting from root — do NOT skip root's other children
    # (a previous version used cursor.goto_first_child() which dropped siblings).
    stack = [root]
    while stack:
        n = stack.pop()
        if n.type in spec.import_node_types:
            # Most "import" nodes have a `source` child (string literal with the module path)
            src = n.child_by_field_name("source")
            if src is not None:
                text = _node_text(src, source).strip().strip("'\"`")
                if text:
                    imports.append(text)
            else:
                # Fallback: capture the whole node text minus keywords
                text = _node_text(n, source)
                if text:
                    imports.append(text)
        for child in n.children:
            stack.append(child)
    return imports


def _extract_functions(root: Node, source: bytes, spec: NodeSpec, file_path: str) -> List[FunctionInfo]:
    functions: List[FunctionInfo] = []
    stack = [root]
    while stack:
        n = stack.pop()
        if n.type in spec.function_node_types:
            name = _function_name(n, source)
            # Try to extract a signature (first line of the node)
            sig_text = _node_text(n, source).splitlines()[0] if _node_text(n, source) else ""
            functions.append(
                FunctionInfo(
                    name=name or "<anonymous>",
                    file_path=file_path,
                    start_line=n.start_point[0] + 1,
                    end_line=n.end_point[0] + 1,
                    signature=sig_text.strip()[:200],
                    docstring=None,  # Tree-sitter doesn't extract docstrings uniformly
                    calls=[],         # Static call extraction is a future enhancement
                    is_test=False,    # test-name detection is language-specific; done downstream
                )
            )
        for child in n.children:
            stack.append(child)
    return functions


def _extract_classes(root: Node, source: bytes, spec: NodeSpec, file_path: str) -> List[ClassInfo]:
    classes: List[ClassInfo] = []
    stack = [root]
    while stack:
        n = stack.pop()
        if n.type in spec.class_node_types:
            name = _class_name(n, source)
            classes.append(
                ClassInfo(
                    name=name or "<anonymous>",
                    file_path=file_path,
                    start_line=n.start_point[0] + 1,
                    end_line=n.end_point[0] + 1,
                    docstring=None,
                    methods=[],
                    bases=[],
                )
            )
        for child in n.children:
            stack.append(child)
    return classes


def parse_with_tree_sitter(
    language: Language,
    source_bytes: bytes,
    file_path_str: str,
    repo_root: Path,
    spec: NodeSpec,
) -> FileInfo:
    """Parse a source buffer with a tree-sitter Language and return FileInfo."""
    parser = Parser(language)
    tree = parser.parse(source_bytes)

    relative_path = file_path_str
    try:
        relative_path = str(Path(file_path_str).resolve().relative_to(repo_root.resolve()))
    except (ValueError, OSError):
        relative_path = Path(file_path_str).name

    return FileInfo(
        path=file_path_str,
        relative_path=relative_path,
        name=Path(file_path_str).name,
        content_hash=hashlib.md5(source_bytes).hexdigest(),
        imports=_extract_imports(tree.root_node, source_bytes, spec),
        functions=_extract_functions(tree.root_node, source_bytes, spec, file_path_str),
        classes=_extract_classes(tree.root_node, source_bytes, spec, file_path_str),
        is_test_file=False,  # test detection handled by is_test_file() in dispatcher
    )


def make_language(capsule) -> Language:
    """Wrap a PyCapsule from tree-sitter-* binding in a tree_sitter.Language."""
    return Language(capsule)
