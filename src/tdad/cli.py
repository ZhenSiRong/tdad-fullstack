"""TDAD CLI: tdad index|impact|run-tests|stats"""

import argparse
import sys
from pathlib import Path
from typing import List, Optional


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="tdad",
        description="Test-Driven AI Development — GraphRAG test impact analysis",
    )
    sub = parser.add_subparsers(dest="command")

    # -- index --
    p_index = sub.add_parser("index", help="Index a repository into the code-test graph")
    p_index.add_argument("repo_path", type=Path, help="Path to repository")
    p_index.add_argument("--force", action="store_true", help="Force full rebuild")
    p_index.add_argument("--languages", type=str, default=None,
                         help="Comma-separated languages (e.g., python,javascript). Auto-detects if omitted.")

    # -- impact --
    p_impact = sub.add_parser("impact", help="Find tests impacted by changed files")
    p_impact.add_argument("repo_path", type=Path, help="Path to repository")
    src = p_impact.add_mutually_exclusive_group(required=True)
    src.add_argument("--files", nargs="+", help="Changed file paths (explicit)")
    src.add_argument(
        "--changed",
        nargs="?",
        const="",  # bare --changed → uncommitted
        default=None,
        metavar="REF",
        help="Auto-discover changed files via git diff. With no arg: uncommitted. "
             "With REF: e.g. HEAD~1, origin/main, <sha>. (tdad-fullstack extension.)",
    )
    p_impact.add_argument("--strategy", default="balanced", choices=["conservative", "balanced", "aggressive"])
    p_impact.add_argument("--max-tests", type=int, default=50)
    p_impact.add_argument("--languages", type=str, default=None,
                         help="Comma-separated languages (e.g., python,javascript). Auto-detects if omitted.")

    # -- run-tests --
    p_run = sub.add_parser("run-tests", help="Run specific tests via the right runner per file")
    p_run.add_argument("repo_path", type=Path, help="Path to repository")
    p_run.add_argument("--tests", nargs="+", required=True, help="Test file paths (or pytest node IDs)")
    p_run.add_argument("--timeout", type=int, default=300)
    p_run.add_argument(
        "--runner",
        choices=["pytest", "vitest", "jest", "go", "auto"],
        default="auto",
        help="Test runner (default: auto — per-file dispatch to pytest/vitest/jest/go). "
             "(tdad-fullstack extension.)",
    )

    # -- stats --
    p_stats = sub.add_parser("stats", help="Show graph statistics")
    p_stats.add_argument("repo_path", type=Path, help="Path to repository")

    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    try:
        if args.command == "index":
            return _cmd_index(args)
        elif args.command == "impact":
            return _cmd_impact(args)
        elif args.command == "run-tests":
            return _cmd_run_tests(args)
        elif args.command == "stats":
            return _cmd_stats(args)
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


def _cmd_index(args):
    from .core.config import get_settings, get_db
    from .indexer.graph_builder import build_graph
    from .indexer.test_linker import link_tests
    from .analyzer.impact import export_test_map, export_test_map_heuristic

    settings = get_settings()
    languages = getattr(args, "languages", None) or settings.languages or None

    try:
        with get_db(settings, repo_path=args.repo_path) as db:
            print(f"Indexing {args.repo_path} (backend={settings.backend}) ...")
            stats = build_graph(args.repo_path, db, force=args.force, languages=languages)
            if stats.get("incremental"):
                print(f"  Changed:   {stats.get('changed', 0)}")
                print(f"  Unchanged: {stats.get('unchanged', 0)}")
                print(f"  Deleted:   {stats.get('deleted', 0)}")
            print(f"  Files:     {stats['files']}")
            print(f"  Functions: {stats['functions']}")
            print(f"  Classes:   {stats['classes']}")
            print(f"  Tests:     {stats['tests']}")
            print(f"  Edges:     {stats['edges']}")

            print("Linking tests ...")
            link_stats = link_tests(args.repo_path, db)
            print(f"  Naming:  {link_stats['naming']}")
            print(f"  Static:  {link_stats['static']}")
            print(f"  Coverage: {link_stats['coverage']}")
            print(f"  Total:   {link_stats['total']}")

            # Export static test map for agent use (graph + heuristic)
            try:
                map_count = export_test_map(db, args.repo_path)
                print(f"  Test map: {map_count} source files exported")
            except Exception as exc:
                print(f"  Test map: graph export failed ({exc})")
                map_count = export_test_map_heuristic(args.repo_path)
                print(f"  Test map: {map_count} source files (heuristic)")

    except Exception as exc:
        # Neo4j unavailable or indexing failed — fall back to heuristic test map
        print(f"Graph indexing unavailable: {exc}", file=sys.stderr)
        print("Generating heuristic test map ...")
        map_count = export_test_map_heuristic(args.repo_path)
        print(f"  Test map: {map_count} source files (heuristic)")

    return 0


def _cmd_impact(args):
    from .core.config import get_settings, get_db
    from .analyzer.impact import get_impacted_tests

    # tdad-fullstack: resolve --changed → files (mutually exclusive with --files)
    if args.changed is not None:
        ref = args.changed if args.changed else None
        try:
            files = _resolve_changed_files(args.repo_path, ref)
        except RuntimeError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        if not files:
            print(f"No changed files detected (ref={ref or 'uncommitted'}).")
            return 0
        print(f"# Auto-detected {len(files)} changed file(s) via git diff (ref={ref or 'uncommitted'}):")
        for f in files:
            try:
                rel = str(Path(f).resolve().relative_to(args.repo_path.resolve()))
            except ValueError:
                rel = Path(f).name
            print(f"  - {rel}")
        print()
        args.files = files

    settings = get_settings()
    with get_db(settings, repo_path=args.repo_path) as db:
        tests = get_impacted_tests(
            args.repo_path, db, args.files,
            strategy=args.strategy, max_tests=args.max_tests,
        )

    if not tests:
        print("No impacted tests found.")
        return 0

    # Markdown table — tdad-fullstack adds a Language tag column
    print(f"## Impacted Tests ({len(tests)} found)\n")
    print("| Score | Test | File | Language | Reason |")
    print("|-------|------|------|----------|--------|")
    for t in tests:
        score = f"{t['impact_score']:.2f}"
        lang_tag = _tag_for_test_file(t["test_file"])
        print(f"| {score} | {t['test_name']} | {t['test_file']} | {lang_tag} | {t['impact_reason']} |")

    return 0


def _resolve_changed_files(repo_path: Path, ref: Optional[str]) -> List[str]:
    """Use git to discover changed files in the repo.

    Mirrors Vitest's `--changed` semantics:
    - ref is None  → uncommitted changes (working tree vs index)
    - ref is "HEAD~1" / "origin/main" / "<sha>" → diff vs ref
    """
    import subprocess
    cmd = ["git", "-C", str(repo_path), "diff", "--name-only"]
    if ref:
        cmd.append(ref)

    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(
            f"git diff failed (rc={result.returncode}): {result.stderr.strip()}\n"
            f"  command: {' '.join(cmd)}"
        )
    files = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    return [str((repo_path / f).resolve()) for f in files]


def _tag_for_test_file(test_file: str) -> str:
    """Return the language tag for an impacted test file path.

    Used in the impact report so the caller knows which runner to dispatch to.
    """
    from .languages import EXTENSION_MAP
    suffix = Path(test_file).suffix.lower()
    lang = EXTENSION_MAP.get(suffix, "unknown")
    return {
        "python": "[python]",
        "javascript": "[jest]",
        "typescript": "[jest]",
        "vue": "[vitest]",
        "go": "[go]",
        "java": "[junit]",
        "rust": "[cargo]",
        "dart": "[dart]",
    }.get(lang, "[unknown]")


def _cmd_run_tests(args):
    """Run the given test files, dispatching per-file to the right runner.

    tdad-fullstack extension: `--runner=auto` groups files by language and
    calls run_tests once per group (each call uses the upstream v0.2.0
    `language=` kwarg).
    """
    from .runner.test_runner import run_tests

    # Map runner name → upstream v0.2.0 language id
    runner_to_lang = {
        "pytest": "python",
        "vitest": "typescript",   # v0.2.0 treats typescript under javascript
        "jest": "javascript",
        "go": "go",
        "auto": None,
    }

    if args.runner == "auto":
        # Per-file dispatch: group by language, call run_tests once per group.
        from .languages import EXTENSION_MAP
        groups: dict = {}
        for t in args.tests:
            lang = EXTENSION_MAP.get(Path(t).suffix.lower(), "python")
            groups.setdefault(lang, []).append(t)

        overall_rc = 0
        for lang, files in groups.items():
            print(f"\n# [{lang}] running {len(files)} test file(s)")
            result = run_tests(args.repo_path, files, timeout=args.timeout, language=lang)
            print(result["output"])
            if result["returncode"] != 0:
                overall_rc = result["returncode"]
        return overall_rc

    # Explicit runner → map to language → single call
    language = runner_to_lang.get(args.runner, "python")
    result = run_tests(args.repo_path, args.tests, timeout=args.timeout, language=language)
    print(result["output"])
    if result["returncode"] == 0:
        print(f"\nAll tests passed ({result['passed']} passed)")
    else:
        print(f"\n{result['passed']} passed, {result['failed']} failed, {result['errors']} errors")
    return result["returncode"]


def _cmd_stats(args):
    from .core.config import get_settings, get_db

    settings = get_settings()
    with get_db(settings, repo_path=args.repo_path) as db:
        if hasattr(db, "count_by_label"):
            # NetworkX backend
            counts = {}
            for label in ["File", "Function", "Class", "Test"]:
                counts[label] = db.count_by_label(label)
            counts["Edges"] = db.count_edges()
            counts["TESTS edges"] = db.count_edges("TESTS")
        else:
            # Neo4j backend
            with db.session() as session:
                counts = {}
                for label in ["File", "Function", "Class", "Test"]:
                    result = db.run_query(session, f"MATCH (n:{label}) RETURN count(n) AS cnt")
                    counts[label] = result.single()["cnt"]
                result = db.run_query(session, "MATCH ()-[r]->() RETURN count(r) AS cnt")
                counts["Edges"] = result.single()["cnt"]
                result = db.run_query(session, "MATCH ()-[r:TESTS]->() RETURN count(r) AS cnt")
                counts["TESTS edges"] = result.single()["cnt"]

    print("## Graph Statistics\n")
    for label, count in counts.items():
        print(f"  {label:15s} {count:>6}")

    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
