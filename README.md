# tdad-fullstack

> Multi-language test impact analysis. Fork of [tdad](https://github.com/pepealonso95/tdad) with tree-sitter support for **JavaScript / TypeScript / Vue / Go** alongside the original Python.

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Upstream: tdad](https://img.shields.io/badge/upstream-tdad-0.1.0-green.svg)](https://github.com/pepealonso95/tdad)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)]()

## What it does

Build a unified code-test dependency graph across a polyglot repo. When you change source files, answer **"which tests do I need to re-run?"** in one command — across pytest, vitest, jest, and go test.

```bash
# Build the graph (one-time per repo)
tdad-fullstack index .

# You changed a Python + a Vue file — what's affected?
tdad-fullstack impact . --files src/utils.py src/components/Button.vue

# Output:
#   [python] tests/test_utils.py
#   [vitest] tests/components/Button.spec.ts

# Auto-detect from git diff (last commit)
tdad-fullstack impact . --changed HEAD~1

# Run the impacted tests directly
tdad-fullstack run-tests . --tests tests/test_utils.py tests/components/Button.spec.ts
```

## Why fork?

The upstream [tdad](https://github.com/pepealonso95/tdad) ([paper](https://github.com/pepealonso95/tdad/blob/main/paper.pdf)) ships Python-only parsing via stdlib `ast`. This fork adds tree-sitter parsing for JS/TS/Vue/Go while keeping the upstream graph model, test linker, and runner dispatch logic intact.

| Feature | Upstream tdad | tdad-fullstack |
|---|---|---|
| Python (.py)            | ✅ stdlib `ast` | ✅ unchanged |
| JavaScript (.js, .mjs)  | ❌ | ✅ tree-sitter-javascript |
| TypeScript (.ts, .tsx)  | ❌ | ✅ tree-sitter-typescript |
| Vue (.vue, SFC)         | ❌ | ✅ @vue/compiler-sfc + JS parser |
| Go (.go)                | ❌ | ✅ tree-sitter-go |
| Multi-lang graph merge  | n/a | ✅ unified `graph.pkl` |
| Test dispatch           | pytest | pytest + vitest + jest + go test |

## Install

```bash
# As a pip package
pip install tdad-fullstack

# As an Agent Skill (npx)
npx skills add ZhenSiRong/tdad-fullstack
```

## License

MIT — same as upstream. Copyright (c) 2026 Rafael Alonso (upstream) + ZhenSiRong (this fork). See [LICENSE](LICENSE).
