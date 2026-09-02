"""Vue SFC language plugin.

Vue Single File Components contain three blocks: <template>, <script>,
<style>. For impact-analysis purposes only the <script> block matters
(it holds imports, functions, classes that can affect tests). We extract
the <script> block(s) with a small regex and feed them to the
JavaScriptPlugin — no need to pull in @vue/compiler-sfc.

Why a dedicated plugin (not just registering .vue under JavaScriptPlugin)?
- Test detection for Vue uses `*.spec.vue` / `*.test.vue` conventions
- File identity (relative_path, name) reflects the .vue path, not a
  synthesized JS path
- Future expansion: extract <template> bindings for component-graph
  analysis (planned but not implemented here)
"""

import logging
import re
from pathlib import Path
from typing import List, Set

from .base import FileInfo, FunctionInfo, ClassInfo
from .javascript import JavaScriptPlugin

logger = logging.getLogger(__name__)


# Match <script ...>...</script> — non-greedy, DOTALL. Captures attributes
# (so we can detect <script setup>, lang="ts", etc. in future) and body.
_SCRIPT_RE = re.compile(
    r"<script(?P<attrs>[^>]*)>(?P<body>.*?)</script>",
    re.DOTALL | re.IGNORECASE,
)


# Vue test file conventions
_TEST_FILE_PATTERNS = [
    "*.spec.vue",
    "*.test.vue",
]


def _extract_script_blocks(source: str) -> List[str]:
    """Return the inner content of every <script> block in the SFC."""
    return [m.group("body") for m in _SCRIPT_RE.finditer(source)]


def _is_test_file(path: Path, repo_root: Path) -> bool:
    """Vue test detection: *.spec.vue / *.test.vue, or files under __tests__/ or tests/.

    Uses repo_root-relative path parts (not absolute) to avoid false positives
    when the repo root itself contains "tests" (e.g. `tests/fixtures/sample_repo/...`
    would otherwise be detected as a test file).
    """
    name = path.name
    if any(name.endswith(suffix) for suffix in (".spec.vue", ".test.vue")):
        return True
    try:
        rel = path.resolve().relative_to(repo_root.resolve())
    except ValueError:
        rel = path
    return any(part in ("__tests__", "tests") for part in rel.parts)


class VuePlugin:
    """Language plugin for Vue Single File Components (.vue).

    Internally delegates to JavaScriptPlugin for parsing — the <script>
    block is plain JavaScript (or TypeScript with lang="ts").
    """

    def __init__(self):
        # Reuse the JS plugin for parsing the <script> block
        self._js_plugin = JavaScriptPlugin("javascript")

    @property
    def name(self) -> str:
        return "vue"

    @property
    def file_extensions(self) -> Set[str]:
        return {".vue"}

    def parse_file(self, path: Path, repo_root: Path) -> FileInfo:
        try:
            source = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            logger.warning("Could not read %s: %s", path, exc)
            return FileInfo(
                path=str(path),
                relative_path=path.name,
                name=path.name,
                content_hash="",
                language="vue",
            )

        script_blocks = _extract_script_blocks(source)
        is_test = _is_test_file(path, repo_root)

        if not script_blocks:
            # Template-only or style-only SFC — no logic to analyze.
            import hashlib
            return FileInfo(
                path=str(path),
                relative_path=path.name,
                name=path.name,
                content_hash=hashlib.md5(source.encode()).hexdigest(),
                language="vue",
                is_test_file=is_test,
            )

        # Concatenate all <script> blocks with a separator so the JS parser
        # treats them as separate statements.
        combined = "\n;\n".join(script_blocks)

        # We can't pass the combined buffer directly to JavaScriptPlugin.parse_file
        # (which re-reads from disk). Instead, write to a temp path in memory.
        # Trick: monkey-patch path.read_text via a temp file.
        import tempfile
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".vue.js", delete=False, encoding="utf-8"
        ) as tmp:
            tmp.write(combined)
            tmp_path = Path(tmp.name)
        try:
            # Parse as a virtual .js path; then override identity fields.
            info = self._js_plugin.parse_file(tmp_path, repo_root)
        finally:
            tmp_path.unlink(missing_ok=True)

        # Override identity so the FileInfo reflects the original .vue path
        try:
            relative_path = str(path.resolve().relative_to(repo_root.resolve()))
        except ValueError:
            relative_path = path.name
        info.path = str(path)
        info.relative_path = relative_path
        info.name = path.name
        info.language = "vue"
        info.is_test_file = is_test

        return info
