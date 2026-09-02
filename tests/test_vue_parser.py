"""Tests for the Vue SFC language plugin (tdad-fullstack's delta over upstream v0.2.0)."""

import pytest
from pathlib import Path

# Skip all tests if tree-sitter is not installed
ts = pytest.importorskip("tree_sitter", reason="tree-sitter not installed")
pytest.importorskip("tree_sitter_javascript", reason="tree-sitter-javascript not installed")

from tdad.languages.vue import VuePlugin
from tdad.languages import get_plugin, EXTENSION_MAP


@pytest.fixture
def vue_plugin():
    return VuePlugin()


@pytest.fixture
def vue_repo():
    return Path(__file__).parent / "fixtures" / "sample_vue_repo"


@pytest.fixture
def button_vue(vue_repo):
    return vue_repo / "src" / "components" / "Button.vue"


@pytest.fixture
def button_spec_vue(vue_repo):
    return vue_repo / "src" / "components" / "Button.spec.vue"


def test_vue_extension_registered():
    """tdad-fullstack extends EXTENSION_MAP with .vue."""
    assert EXTENSION_MAP[".vue"] == "vue"


def test_vue_plugin_registered():
    """get_plugin('vue') returns a VuePlugin instance."""
    plugin = get_plugin("vue")
    assert plugin.name == "vue"
    assert ".vue" in plugin.file_extensions


def test_vue_plugin_extensions(vue_plugin):
    assert vue_plugin.file_extensions == {".vue"}


def test_parse_button_vue_extracts_script_imports(vue_plugin, button_vue, vue_repo):
    """The .vue file's <script> block imports `vue` and `greet` from utils — both must surface."""
    info = vue_plugin.parse_file(button_vue, vue_repo)
    assert info.language == "vue"
    assert info.is_test_file is False
    # Should extract imports from the <script> block
    imports_str = " ".join(info.imports)
    assert "vue" in imports_str
    assert "utils" in imports_str  # path resolves to "../../src/utils"


def test_parse_button_spec_vue_marked_as_test(vue_plugin, button_spec_vue, vue_repo):
    """*.spec.vue should be marked as a test file."""
    info = vue_plugin.parse_file(button_spec_vue, vue_repo)
    assert info.is_test_file is True


def test_parse_vue_file_preserves_relative_path(vue_plugin, button_vue, vue_repo):
    """The FileInfo must reflect the original .vue path, not a synthetic .js path."""
    info = vue_plugin.parse_file(button_vue, vue_repo)
    assert info.path.endswith("Button.vue")
    assert info.name == "Button.vue"
    assert "Button.vue" in info.relative_path


def test_parse_template_only_vue_returns_empty_fileinfo(vue_plugin, tmp_path):
    """A .vue file with no <script> block should return an empty FileInfo (no crash)."""
    sfc = tmp_path / "TemplateOnly.vue"
    sfc.write_text("<template><div /></template>")
    info = vue_plugin.parse_file(sfc, tmp_path)
    assert info.language == "vue"
    assert info.is_test_file is False
    assert info.functions == []
    assert info.classes == []


def test_vue_test_detection_via_directory(vue_plugin, tmp_path):
    """Vue test detection: files under __tests__/ should also be marked as tests."""
    test_dir = tmp_path / "src" / "__tests__"
    test_dir.mkdir(parents=True)
    sfc = test_dir / "Widget.vue"
    sfc.write_text("<script>export default {}</script>")
    info = vue_plugin.parse_file(sfc, tmp_path)
    assert info.is_test_file is True
