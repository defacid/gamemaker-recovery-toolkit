"""Format-driven discovery and batch recovery orchestration."""

from __future__ import annotations

import hashlib
import json
import re
import sys
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from .core import (
    SOURCE_SUFFIXES,
    STUDIO_DATA_SUFFIXES,
    Workspace,
    audit_workspace,
    extract_artifact,
    inspect_artifact,
    render_report,
)


CANDIDATE_SUFFIXES = set(SOURCE_SUFFIXES) | STUDIO_DATA_SUFFIXES | {".exe", ".zip", ".7z", ".rar"}
DEFAULT_SECONDS = {"inspect": 0.2, "extract": 2.0, "audit": 0.5, "report": 0.2}


@dataclass(frozen=True)
class SweepCandidate:
    path: Path
    kind: str

    @property
    def key(self) -> str:
        digest = hashlib.sha256(str(self.path).encode("utf-8")).hexdigest()[:10]
        stem = re.sub(r"[^A-Za-z0-9._-]+", "-", self.path.stem).strip("-.") or "game"
        return f"{stem}-{digest}"


def _zip_looks_relevant(path: Path) -> bool:
    try:
        with zipfile.ZipFile(path) as archive:
            names = [name.lower() for name in archive.namelist()]
    except (OSError, zipfile.BadZipFile):
        return False
    source_suffixes = tuple(SOURCE_SUFFIXES) + (".yyp", ".project.gmx", "data.win", "game.ios")
    return any(name.endswith(source_suffixes) for name in names)


def _project_kind(path: Path) -> str | None:
    names = {child.name.lower() for child in path.iterdir()} if path.is_dir() else set()
    if any(child.is_file() and child.suffix.lower() == ".yyp" for child in path.iterdir()):
        return "modern-gamemaker-source"
    if any(name.endswith(".project.gmx") for name in names):
        return "studio-gmx-source"
    if {"sprites", "objects", "rooms"}.issubset(names):
        return "source-resource-tree"
    return None


def discover_candidates(root: Path) -> list[SweepCandidate]:
    """Find GameMaker candidates by format, pruning inside recognized projects."""
    root = root.resolve()
    if not root.exists():
        raise FileNotFoundError(root)
    if root.is_file():
        suffix = root.suffix.lower()
        if suffix not in CANDIDATE_SUFFIXES or (suffix == ".zip" and not _zip_looks_relevant(root)):
            return []
        return [SweepCandidate(root, "artifact")]

    found: list[SweepCandidate] = []
    stack = [root]
    while stack:
        directory = stack.pop()
        kind = _project_kind(directory)
        if kind:
            found.append(SweepCandidate(directory, kind))
            continue
        for child in sorted(directory.iterdir(), key=lambda item: item.name.casefold(), reverse=True):
            if child.name in {".git", ".gmrecover", "node_modules", "build", "dist"}:
                continue
            if child.is_dir():
                stack.append(child)
                continue
            suffix = child.suffix.lower()
            if suffix not in CANDIDATE_SUFFIXES:
                continue
            if suffix == ".zip" and not _zip_looks_relevant(child):
                continue
            found.append(SweepCandidate(child, "artifact"))
    return sorted(found, key=lambda item: str(item.path).casefold())


def _clock(seconds: float) -> str:
    seconds = max(0, round(seconds))
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours}:{minutes:02d}:{seconds:02d}" if hours else f"{minutes:02d}:{seconds:02d}"


def _load_timings(path: Path) -> dict[str, float]:
    try:
        return {key: float(value) for key, value in json.loads(path.read_text()).items()}
    except (FileNotFoundError, OSError, ValueError, TypeError):
        return dict(DEFAULT_SECONDS)


def _save_timings(path: Path, timings: dict[str, float]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(timings, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_sweep(
    source_root: Path,
    workspace_root: Path,
    *,
    list_only: bool = False,
    continue_on_error: bool = False,
    progress: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    candidates = discover_candidates(source_root)
    if list_only:
        return {"candidate_count": len(candidates), "candidates": [str(item.path) for item in candidates]}

    workspace_root = workspace_root.resolve()
    workspace_root.mkdir(parents=True, exist_ok=True)
    timing_path = workspace_root / ".gmrecover-sweep-timings.json"
    timings = _load_timings(timing_path)
    stages = ("inspect", "extract", "audit", "report")
    total_units = len(candidates) * len(stages)
    total_estimate = len(candidates) * sum(timings.get(stage, DEFAULT_SECONDS[stage]) for stage in stages)
    started = time.monotonic()
    completed_units = 0
    results: list[dict[str, Any]] = []
    blocked = failed = 0

    def update(candidate: SweepCandidate, stage: str, status: str = "running") -> None:
        if progress is None:
            return
        elapsed = time.monotonic() - started
        average = elapsed / completed_units if completed_units else 0
        remaining_units = total_units - completed_units
        eta = average * remaining_units if average else total_estimate
        percent = 100 * completed_units / max(total_units, 1)
        progress(
            f"[{completed_units}/{total_units}] {percent:5.1f}% | {candidate.path.name} · {stage} "
            f"{status} | elapsed {_clock(elapsed)} | ETA {_clock(eta)}"
        )

    for candidate in candidates:
        workspace = Workspace(workspace_root / candidate.key)
        workspace.ensure()
        entry: dict[str, Any] = {"input": str(candidate.path), "workspace": str(workspace.root), "status": "complete"}
        try:
            for stage in stages:
                update(candidate, stage)
                stage_started = time.monotonic()
                if stage == "inspect":
                    inspection = inspect_artifact(candidate.path, workspace)
                    entry["kind"] = inspection["kind"]
                elif stage == "extract":
                    extraction = extract_artifact(workspace)
                    entry["adapter"] = extraction.get("adapter")
                    if extraction.get("adapter") is None:
                        entry["status"] = "blocked"
                        entry["requirement"] = extraction.get("requirement")
                        blocked += 1
                elif stage == "audit":
                    extracted = workspace.load().get("stages", {}).get("extract", {})
                    output = extracted.get("output")
                    if output and Path(output).is_dir():
                        audit_workspace(workspace, Path(output))
                    else:
                        workspace.stage("audit", "blocked", requirement="A source tree is required for static GML audit.")
                else:
                    markdown, html = render_report(workspace)
                    entry["reports"] = [str(markdown), str(html)]
                duration = time.monotonic() - stage_started
                prior = timings.get(stage, DEFAULT_SECONDS[stage])
                timings[stage] = round(prior * 0.7 + duration * 0.3, 3)
                completed_units += 1
                update(candidate, stage, "complete")
            results.append(entry)
        except (FileNotFoundError, RuntimeError, ValueError, OSError) as error:
            failed += 1
            entry.update(status="failed", error=str(error))
            results.append(entry)
            if not continue_on_error:
                break
    _save_timings(timing_path, timings)
    return {
        "source_root": str(source_root.resolve()),
        "workspace_root": str(workspace_root),
        "candidate_count": len(candidates),
        "processed_count": len(results),
        "blocked_count": blocked,
        "failed_count": failed,
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "results": results,
    }


def stderr_progress(message: str) -> None:
    print(message, file=sys.stderr, flush=True)
