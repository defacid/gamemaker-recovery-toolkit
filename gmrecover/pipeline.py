"""Declarative, resumable external-stage runner."""

from __future__ import annotations

import os
import subprocess
import tomllib
from pathlib import Path
from typing import Any

from .core import Workspace, utc_now

PIPELINE_STAGES = ("normalize", "generate", "repair", "build", "exercise", "compare")


def load_pipeline(path: Path) -> dict[str, Any]:
    with path.open("rb") as handle:
        config = tomllib.load(handle)
    unknown = set(config.get("stages", {})) - set(PIPELINE_STAGES)
    if unknown:
        raise ValueError(f"unknown pipeline stages: {', '.join(sorted(unknown))}")
    return config


def expand(value: str, values: dict[str, str]) -> str:
    try:
        return value.format_map(values)
    except KeyError as error:
        raise ValueError(f"unknown pipeline placeholder: {error.args[0]}") from error


def run_pipeline(
    workspace: Workspace,
    config_path: Path,
    *,
    force: bool = False,
    start_at: str | None = None,
) -> dict[str, Any]:
    config_path = config_path.resolve()
    config = load_pipeline(config_path)
    manifest = workspace.load()
    inspected = manifest.get("stages", {}).get("inspect", {})
    values = {
        "workspace": str(workspace.root),
        "input": str(inspected.get("input", "")),
        "extracted": str(workspace.root / "extracted"),
        "normalized": str(workspace.root / "normalized"),
        "modern": str(workspace.root / "modern"),
        "build": str(workspace.root / "build"),
        "reports": str(workspace.root / "reports"),
        "screenshots": str(workspace.root / "screenshots"),
        "config_dir": str(config_path.parent),
    }
    if start_at and start_at not in PIPELINE_STAGES:
        raise ValueError(f"unknown start stage: {start_at}")
    started = start_at is None
    results: dict[str, Any] = {}

    for name in PIPELINE_STAGES:
        if name == start_at:
            started = True
        definition = config.get("stages", {}).get(name)
        if not definition or not started:
            continue
        previous = workspace.load().get("stages", {}).get(name, {})
        if previous.get("status") == "complete" and not force:
            results[name] = {"status": "complete", "resumed": True}
            continue
        command = definition.get("command")
        if not isinstance(command, list) or not command or not all(isinstance(item, str) for item in command):
            raise ValueError(f"stages.{name}.command must be a non-empty string array")
        argv = [expand(item, values) for item in command]
        cwd = Path(expand(str(definition.get("cwd", "{workspace}")), values)).resolve()
        if not cwd.is_dir():
            raise ValueError(f"working directory for {name} does not exist: {cwd}")
        environment = os.environ.copy()
        for key, value in definition.get("environment", {}).items():
            environment[str(key)] = expand(str(value), values)
        log_path = workspace.root / "reports" / f"{name}.log"
        workspace.stage(name, "running", command=argv, cwd=str(cwd), started_at=utc_now())
        completed = subprocess.run(argv, cwd=cwd, env=environment, text=True, capture_output=True, check=False)
        log_path.write_text(
            f"$ {' '.join(argv)}\n\n[stdout]\n{completed.stdout}\n[stderr]\n{completed.stderr}",
            encoding="utf-8",
        )
        status = "complete" if completed.returncode == 0 else "failed"
        details = {"returncode": completed.returncode, "log": str(log_path), "command": argv, "cwd": str(cwd)}
        workspace.stage(name, status, **details)
        results[name] = {"status": status, **details}
        if completed.returncode != 0:
            break
    return results
