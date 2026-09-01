---
name: tdad-fullstack
description: >-
  Test impact analysis for fullstack repos (Python + JS/TS/Vue/Go).
  Fork of tdad with tree-sitter multi-language support. Use when you need to
  find which tests are affected by code changes in a polyglot project — e.g.
  changed a Python utility, want to know which pytest + vitest + jest files
  need to re-run. Activate when you see a `.tdad-fullstack/` directory or a
  polyglot repo with `package.json` alongside `pyproject.toml`. Replaces
  ad-hoc `git diff | xargs jest --findRelatedTests` workflows with one graph.
license: MIT
metadata:
  author: ZhenSiRong
  upstream: tdad (pepealonso95) — MIT, Copyright (c) 2026 Rafael Alonso
  fork-of: https://github.com/pepealonso95/tdad
---

# TDAD Fullstack

**Multi-language test impact analysis.** Fork of [tdad](https://github.com/pepealonso95/tdad) that extends the original Python-only AST analyzer to JS / TS / Vue / Go via tree-sitter, producing a unified code-test graph for polyglot repos.

## When this skill activates

- A `.tdad-fullstack/` directory exists in the repo
- A polyglot project with both `pyproject.toml` and `package.json` (or `tsconfig.json`, `vue.config.js`, `go.mod`)
- The user asks which tests to run after changing source files across languages

## Setup (one-time per repo)

```bash
# Install CLI (comes with this skill — bin/tdad-fullstack in PATH after install)
pip install -e .

# Build the multi-language code-test graph
tdad-fullstack index .
```

This walks the repo, parses Python via stdlib `ast`, JS/TS/Vue via tree-sitter, and persists to `graph.pkl` (networkx) or Neo4j if `NEO4J_URI` is set.

## Bug Fix / Feature Workflow

### 1. Make the change

Edit source files normally.

### 2. Find impacted tests

```bash
# Option A: list which test files are affected (no run)
tdad-fullstack impact . --files src/utils.py src/components/Button.vue

# Option B: auto-detect from git diff
tdad-fullstack impact . --changed HEAD~1

# Option C: full automation — git diff → affected tests → run them
tdad-fullstack impact . --changed HEAD~1 --run
```

Output (text mode): one line per impacted test file, prefixed with language tag:

```
[python] tests/test_utils.py
[vitest]  tests/components/Button.spec.ts
[jest]    tests/api/handler.test.js
```

### 3. Run only the impacted tests

```bash
tdad-fullstack run-tests . --tests tests/test_utils.py tests/components/Button.spec.ts
```

This dispatches to `pytest` (Python files), `vitest related` (Vue files), `jest --findRelatedTests` (JS/TS), or `go test` (Go files) based on the test file's language.

### 4. (Optional) WebUI

This skill does not yet ship a WebUI. For a Vitest-native UI run `vitest --ui` separately (see https://vitest.dev/guide/ui). Roadmap: a thin Flask + Cytoscape.js viewer over `graph.pkl` is tracked in the build plan.

## Languages supported

| Language   | Parser                | Test runner dispatch    |
|------------|-----------------------|-------------------------|
| Python     | stdlib `ast`          | `pytest`                |
| JavaScript | tree-sitter-javascript| `jest` / `vitest related` |
| TypeScript | tree-sitter-typescript| `jest` / `vitest related` |
| Vue (SFC)  | @vue/compiler-sfc + tree-sitter-javascript | `vitest related` |
| Go         | tree-sitter-go        | `go test`               |

Other languages (Java, Rust, Dart) — see upstream `tdad` roadmap.

## Where to read more

- `references/upstream-design.md` — what we kept from tdad
- `references/multi-language-design.md` — parser dispatch strategy
- `references/cli-reference.md` — full CLI options

## Local conventions

- Tests live in `tests/` (pytest) and `tests/` or `__tests__/` (jest/vitest) — discovered automatically
- Configurable via `tdad-fullstack.toml` at repo root (see `references/config.md`)
- Stale graph cache: re-run `tdad-fullstack index .` after major refactors
