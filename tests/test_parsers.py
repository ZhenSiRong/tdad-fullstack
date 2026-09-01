"""Tests for the multi-language parser dispatch."""
from pathlib import Path

import pytest

from tdad.indexer.parsers import (
    EXTENSION_LANGUAGE_MAP,
    get_parser_registry,
    language_for_path,
    parse_file_for_language,
)


REPO = Path(__file__).parent / "fixtures" / "fullstack"


def test_extension_language_map_covers_documented_languages():
    """Spot-check that all advertised languages have at least one extension."""
    assert "python" in EXTENSION_LANGUAGE_MAP.values()
    assert "javascript" in EXTENSION_LANGUAGE_MAP.values()
    assert "typescript" in EXTENSION_LANGUAGE_MAP.values()
    assert "vue" in EXTENSION_LANGUAGE_MAP.values()
    assert "go" in EXTENSION_LANGUAGE_MAP.values()


def test_language_for_path():
    assert language_for_path(Path("foo.py")) == "python"
    assert language_for_path(Path("foo.js")) == "javascript"
    assert language_for_path(Path("foo.ts")) == "typescript"
    assert language_for_path(Path("foo.tsx")) == "typescript"
    assert language_for_path(Path("foo.vue")) == "vue"
    assert language_for_path(Path("foo.go")) == "go"
    assert language_for_path(Path("foo.txt")) is None


def test_parse_python_file():
    registry = get_parser_registry()
    info = parse_file_for_language(REPO / "src" / "utils.py", REPO, registry)
    assert info is not None
    assert info.is_test_file is False
    func_names = {f.name for f in info.functions}
    assert "greet" in func_names


def test_parse_python_test_file_marked():
    registry = get_parser_registry()
    info = parse_file_for_language(REPO / "src" / "test_utils.py", REPO, registry)
    assert info is not None
    assert info.is_test_file is True


def test_parse_javascript_file():
    registry = get_parser_registry()
    info = parse_file_for_language(
        REPO / "frontend" / "__tests__" / "api.test.js", REPO, registry
    )
    assert info is not None
    assert info.is_test_file is True
    func_names = {f.name for f in info.functions}
    # Jest's test() global creates a function_declaration? Actually no — it's
    # a call_expression. So we may not extract "test" as a function name. The
    # important things are: imports parsed, file identified as a test.
    assert any("greet" in imp or "../../src/utils" in imp for imp in info.imports)


def test_parse_typescript_file():
    registry = get_parser_registry()
    info = parse_file_for_language(
        REPO / "frontend" / "test" / "sum.test.ts", REPO, registry
    )
    assert info is not None
    assert info.is_test_file is True


def test_parse_typescript_source_file_extracts_function():
    registry = get_parser_registry()
    info = parse_file_for_language(
        REPO / "frontend" / "test" / "sum.ts", REPO, registry
    )
    assert info is not None
    func_names = {f.name for f in info.functions}
    assert "sum" in func_names


def test_parse_vue_file_extracts_script_block():
    registry = get_parser_registry()
    info = parse_file_for_language(
        REPO / "frontend" / "components" / "Button.vue", REPO, registry
    )
    assert info is not None
    assert info.is_test_file is False
    imports = info.imports
    # Should pick up `import { ref } from "vue"` and `import { greet } from "../../src/utils"`
    joined = " ".join(imports)
    assert "vue" in joined
    assert "src/utils" in joined


def test_parse_vue_spec_file_marked_as_test():
    registry = get_parser_registry()
    info = parse_file_for_language(
        REPO / "frontend" / "components" / "Button.spec.vue", REPO, registry
    )
    assert info is not None
    assert info.is_test_file is True


def test_parse_go_file():
    registry = get_parser_registry()
    info = parse_file_for_language(
        REPO / "pkg" / "calc.go", REPO, registry
    )
    assert info is not None
    assert info.is_test_file is False
    func_names = {f.name for f in info.functions}
    assert "Add" in func_names


def test_parse_go_test_file_marked():
    registry = get_parser_registry()
    info = parse_file_for_language(
        REPO / "pkg" / "calc_test.go", REPO, registry
    )
    assert info is not None
    assert info.is_test_file is True


def test_unsupported_extension_returns_none():
    registry = get_parser_registry()
    info = parse_file_for_language(Path("/tmp/foo.txt"), REPO, registry)
    assert info is None


def test_cli_changed_flag_invokes_git(monkeypatch, tmp_path):
    """Verify --changed invokes git diff to discover files."""
    from tdad.cli import _resolve_changed_files
    import subprocess

    # Set up a fake repo
    (tmp_path / "a.py").write_text("print(1)")

    # Mock subprocess.run so we don't actually need a real git repo
    captured = {}
    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        from unittest.mock import MagicMock
        m = MagicMock()
        m.returncode = 0
        m.stdout = "a.py\n"
        m.stderr = ""
        return m
    monkeypatch.setattr(subprocess, "run", fake_run)
    files = _resolve_changed_files(tmp_path, None)
    assert files == [str((tmp_path / "a.py").resolve())]
    assert "git" in captured["cmd"]
    assert "diff" in captured["cmd"]


def test_cli_changed_flag_handles_git_failure(monkeypatch, tmp_path):
    from tdad.cli import _resolve_changed_files
    import subprocess
    from unittest.mock import MagicMock

    def fake_run(cmd, **kwargs):
        m = MagicMock()
        m.returncode = 128
        m.stderr = "fatal: not a git repository"
        return m
    monkeypatch.setattr(subprocess, "run", fake_run)
    with pytest.raises(RuntimeError, match="git diff failed"):
        _resolve_changed_files(tmp_path, "HEAD~1")
