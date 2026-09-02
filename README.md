# tdad-fullstack

> Test impact analysis for fullstack repos. Fork of [tdad v0.2.0](https://github.com/pepealonso95/tdad) with **Vue SFC support** + CLI enhancements.

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Upstream: tdad v0.2.0](https://img.shields.io/badge/upstream-tdad-0.2.0-green.svg)](https://github.com/pepealonso95/tdad)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)]()

## Why this fork exists

[tdad v0.2.0](https://github.com/pepealonso95/tdad) ships multi-language support for **Python / JavaScript / TypeScript / Go / Java / Rust / Dart** — but **not Vue**.

`tdad-fullstack` fills that gap. The fork is deliberately **narrow**:

| Capability | Upstream v0.2.0 | This fork |
|---|---|---|
| Python, JS, TS, Go, Java, Rust, Dart parsing | ✅ | ✅ (inherited, unchanged) |
| **Vue SFC** (`.vue`) parsing | ❌ | ✅ |
| `impact --changed [REF]` (Vitest-style git auto-discovery) | ❌ | ✅ |
| Per-language tag in impact report (`[python]` / `[vitest]` / `[jest]` / `[go]`) | ❌ | ✅ |
| `run-tests --runner=auto` (per-file language dispatch) | partial | ✅ (handles mixed-language test lists) |

Everything else — the parsers, the graph DB, the test linker, the networkx/Neo4j backends, the `tree-sitter-*` extras — is **unchanged from upstream v0.2.0**.

## Install

```bash
# As a pip package
pip install -e ".[vue]"

# As an Agent Skill (npx)
npx skills add ZhenSiRong/tdad-fullstack
```

## Quick start

```bash
# Build the code-test graph (auto-detects languages)
tdad-fullstack index .

# You changed a Python file + a Vue component — what's affected?
tdad-fullstack impact . --changed

# Output (note the Language column):
# | 0.88 | test_greet    | src/test_utils.py              | [python] | Directly tests changed code |
# | 0.72 | Button.spec   | src/components/Button.spec.vue | [vitest] | Imports changed code         |

# Run the impacted tests (auto-dispatches per language)
tdad-fullstack run-tests . \
  --tests src/test_utils.py src/components/Button.spec.vue \
  --runner=auto
```

## How Vue parsing works (this fork's only addition)

```
.vue file                 Plugin                 Output
─────────────────────────────────────────────────────────────────
<script setup>            ┌──────────────┐       FileInfo with
  import { ref }          │ VuePlugin    │       • language="vue"
  from "vue"              │ (this fork)  │       • imports: ["vue", ...]
  ...                     └──────┬───────┘       • is_test_file: True/False
</script>                      │
                               │ regex split SFC, take <script> body
                               ▼
                        ┌──────────────────┐
                        │ JavaScriptPlugin │       (inherited from
                        │ (upstream)       │       upstream v0.2.0)
                        └──────────────────┘
```

No `@vue/compiler-sfc` dependency — just regex-split the `<script>` block and hand it to upstream's JavaScriptPlugin. About 100 lines of code total.

## License

MIT — same as upstream tdad. Copyright (c) 2026 Rafael Alonso (upstream) + ZhenSiRong (this fork). See [LICENSE](LICENSE).
