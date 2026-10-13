"""Command-line interface for the GameMaker recovery pipeline."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .core import Workspace, audit_workspace, extract_artifact, inspect_artifact, render_report
from .pipeline import PIPELINE_STAGES, run_pipeline
from .manuals import fetch_manual, import_manual, index_manual, source_catalog
from .sweep import run_sweep, stderr_progress


def emit(value: object) -> None:
    print(json.dumps(value, indent=2, sort_keys=True))


def workspace_for(args: argparse.Namespace) -> Workspace:
    return Workspace(args.workspace)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="gmrecover", description=__doc__)
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)

    inspect = commands.add_parser("inspect", help="Classify and hash an artifact without executing it.")
    inspect.add_argument("input", type=Path)
    inspect.add_argument("--workspace", type=Path, required=True)

    extract = commands.add_parser("extract", help="Extract a previously inspected artifact.")
    extract.add_argument("--workspace", type=Path, required=True)
    extract.add_argument("--reference-source", action="store_true", help="Reference a source directory instead of copying it.")

    audit = commands.add_parser("audit", help="Inventory compatibility-sensitive GML operations.")
    audit.add_argument("--workspace", type=Path, required=True)
    audit.add_argument("--root", type=Path, help="GML tree to scan; defaults to WORKSPACE/modern.")

    report = commands.add_parser("report", help="Generate Markdown and HTML workspace reports.")
    report.add_argument("--workspace", type=Path, required=True)

    pipeline = commands.add_parser("pipeline", help="Run configured conversion, build, and browser stages.")
    pipeline.add_argument("config", type=Path)
    pipeline.add_argument("--workspace", type=Path, required=True)
    pipeline.add_argument("--force", action="store_true", help="Rerun stages already marked complete.")
    pipeline.add_argument("--from", dest="start_at", choices=PIPELINE_STAGES, help="Begin at this configured stage.")

    convert = commands.add_parser("convert", help="Run safe available stages and report adapter blockers.")
    convert.add_argument("input", type=Path)
    convert.add_argument("--workspace", type=Path, required=True)

    sweep = commands.add_parser("sweep", help="Discover GameMaker artifacts by format and run safe recovery passes.")
    sweep.add_argument("root", type=Path, help="Artifact or directory tree to scan.")
    sweep.add_argument("--workspace-root", type=Path, required=True, help="Parent directory for isolated candidate workspaces.")
    sweep.add_argument("--list", action="store_true", help="List candidates without processing them.")
    sweep.add_argument("--continue-on-error", action="store_true", help="Continue after a candidate fails.")

    manuals = commands.add_parser("manuals", help="Fetch or index versioned GameMaker manual evidence.")
    manual_commands = manuals.add_subparsers(dest="manual_command", required=True)
    manual_commands.add_parser("sources", help="List registered official manual sources.")
    manual_fetch = manual_commands.add_parser("fetch", help="Cache a registered public manual locally.")
    manual_fetch.add_argument("release")
    manual_fetch.add_argument("--cache", type=Path, required=True)
    manual_fetch.add_argument("--max-pages", type=int, default=5000)
    manual_fetch.add_argument("--delay", type=float, default=0.1)
    manual_import = manual_commands.add_parser("import", help="Cache an authorized local HTML/text manual.")
    manual_import.add_argument("release")
    manual_import.add_argument("source", type=Path)
    manual_import.add_argument("--cache", type=Path, required=True)
    manual_index = manual_commands.add_parser("index", help="Create a prose-free symbol/grammar facts index.")
    manual_index.add_argument("release")
    manual_index.add_argument("--cache", type=Path, required=True)
    manual_index.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    workspace = None
    if args.command not in {"sweep", "manuals"}:
        workspace = workspace_for(args)
        workspace.ensure()
    try:
        if args.command == "inspect":
            emit(inspect_artifact(args.input, workspace))
        elif args.command == "extract":
            emit(extract_artifact(workspace, copy_source=not args.reference_source))
        elif args.command == "audit":
            emit(audit_workspace(workspace, args.root))
        elif args.command == "report":
            markdown, html = render_report(workspace)
            emit({"markdown": str(markdown), "html": str(html)})
        elif args.command == "pipeline":
            results = run_pipeline(workspace, args.config, force=args.force, start_at=args.start_at)
            emit(results)
            return 1 if any(result.get("status") == "failed" for result in results.values()) else 0
        elif args.command == "convert":
            inspection = inspect_artifact(args.input, workspace)
            extraction = extract_artifact(workspace)
            markdown, html = render_report(workspace)
            emit({"inspect": inspection, "extract": extraction, "reports": [str(markdown), str(html)]})
            return 2 if extraction.get("adapter") is None else 0
        elif args.command == "sweep":
            result = run_sweep(
                args.root, args.workspace_root, list_only=args.list,
                continue_on_error=args.continue_on_error, progress=stderr_progress,
            )
            emit(result)
            return 1 if result.get("failed_count", 0) else (2 if result.get("blocked_count", 0) else 0)
        elif args.command == "manuals":
            if args.manual_command == "sources":
                emit(source_catalog())
            elif args.manual_command == "fetch":
                emit(fetch_manual(args.release, args.cache, max_pages=args.max_pages, delay=args.delay,
                                  progress=lambda value: print(value, file=sys.stderr, flush=True)))
            elif args.manual_command == "import":
                emit(import_manual(args.release, args.source, args.cache))
            elif args.manual_command == "index":
                emit(index_manual(args.release, args.cache, args.output))
    except (FileNotFoundError, RuntimeError, ValueError) as error:
        print(f"gmrecover: {error}", file=sys.stderr)
        return 1
    return 0
