"""Workspace, inspection, extraction, auditing, and reporting primitives."""

from __future__ import annotations

import hashlib
import html
import json
import shutil
import stat
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

STATE_VERSION = 1
SOURCE_SUFFIXES = {".gm6": "gm6-source", ".gmk": "gm7-gm8-source", ".gm81": "gm81-source", ".gmz": "studio-source-archive"}
STUDIO_DATA_SUFFIXES = {".win", ".ios", ".droid", ".unx"}

AUDIT_PATTERNS = {
    "collision query": ("place_meeting(", "instance_place(", "collision_rectangle(", "collision_point("),
    "sprite transform": ("image_xscale", "image_yscale", "image_angle"),
    "extended draw": ("draw_sprite_ext(", "draw_sprite_part_ext("),
    "tiled draw": ("draw_sprite_tiled(", "draw_sprite_tiled_ext("),
    "surface lifecycle": ("surface_create(", "surface_set_target(", "surface_free("),
    "texture filtering": ("gpu_set_texfilter(",),
    "font draw": ("draw_set_font(", "draw_text(", "draw_text_ext("),
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def iter_files(root: Path) -> Iterable[Path]:
    yield from sorted((p for p in root.rglob("*") if p.is_file()), key=lambda p: p.as_posix().lower())


def sha256_directory(path: Path) -> tuple[str, list[dict[str, Any]]]:
    digest = hashlib.sha256()
    files = []
    for item in iter_files(path):
        relative = item.relative_to(path).as_posix()
        item_hash = sha256_file(item)
        size = item.stat().st_size
        digest.update(relative.encode("utf-8") + b"\0" + item_hash.encode("ascii") + b"\0")
        files.append({"path": relative, "size": size, "sha256": item_hash})
    return digest.hexdigest(), files


def classify(path: Path) -> tuple[str, list[str]]:
    if path.is_dir():
        names = {p.name.lower() for p in path.iterdir()}
        suffixes = {p.suffix.lower() for p in path.iterdir() if p.is_file()}
        if ".yyp" in suffixes:
            return "modern-gamemaker-source", []
        if any(name.endswith(".project.gmx") for name in names):
            return "studio-gmx-source", []
        if {"sprites", "objects", "rooms"}.issubset(names):
            return "source-resource-tree", ["Project descriptor was not found; resource tree detected."]
        return "directory", ["No known GameMaker project descriptor was found."]

    suffix = path.suffix.lower()
    if suffix in SOURCE_SUFFIXES:
        return SOURCE_SUFFIXES[suffix], []
    if suffix in STUDIO_DATA_SUFFIXES:
        return "studio-data", ["Use UndertaleModTool for VM data; YYC/native builds require static analysis."]
    if suffix == ".zip":
        return "zip-archive", []
    if suffix in {".7z", ".rar"}:
        return "external-archive", ["Install a trusted archive extractor and unpack into a new workspace."]
    if suffix == ".exe":
        prefix = path.read_bytes()[:2]
        warnings = ["Executable classification is intentionally static; the input was not run."]
        if prefix != b"MZ":
            warnings.append("The file does not have a DOS/PE MZ header.")
        return "windows-executable", warnings
    return "unknown", ["No extraction adapter is registered for this file type."]


class Workspace:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.state_dir = self.root / ".gmrecover"
        self.manifest_path = self.state_dir / "manifest.json"

    def ensure(self) -> None:
        self.state_dir.mkdir(parents=True, exist_ok=True)
        for name in ("extracted", "normalized", "modern", "build", "reports", "screenshots"):
            (self.root / name).mkdir(exist_ok=True)

    def load(self) -> dict[str, Any]:
        if not self.manifest_path.exists():
            return {"schema_version": STATE_VERSION, "created_at": utc_now(), "stages": {}}
        return json.loads(self.manifest_path.read_text(encoding="utf-8"))

    def save(self, manifest: dict[str, Any]) -> None:
        self.ensure()
        temporary = self.manifest_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        temporary.replace(self.manifest_path)

    def stage(self, name: str, status: str, **details: Any) -> dict[str, Any]:
        manifest = self.load()
        manifest["updated_at"] = utc_now()
        manifest.setdefault("stages", {})[name] = {"status": status, "updated_at": utc_now(), **details}
        self.save(manifest)
        return manifest


def inspect_artifact(input_path: Path, workspace: Workspace) -> dict[str, Any]:
    source = input_path.resolve()
    if not source.exists():
        raise FileNotFoundError(source)
    kind, warnings = classify(source)
    if source.is_dir():
        digest, files = sha256_directory(source)
        size = sum(int(item["size"]) for item in files)
        inventory: dict[str, Any] = {"file_count": len(files), "files": files}
    else:
        digest, size, inventory = sha256_file(source), source.stat().st_size, {}
    details = {
        "input": str(source),
        "kind": kind,
        "sha256": digest,
        "size": size,
        "warnings": warnings,
        **inventory,
    }
    workspace.stage("inspect", "complete", **details)
    return details


def _safe_zip_members(archive: zipfile.ZipFile, destination: Path) -> list[zipfile.ZipInfo]:
    safe = []
    destination = destination.resolve()
    for member in archive.infolist():
        target = (destination / member.filename).resolve()
        if destination != target and destination not in target.parents:
            raise ValueError(f"archive member escapes destination: {member.filename}")
        mode = member.external_attr >> 16
        if stat.S_ISLNK(mode):
            raise ValueError(f"archive contains a symbolic link: {member.filename}")
        safe.append(member)
    return safe


def extract_artifact(workspace: Workspace, *, copy_source: bool = True) -> dict[str, Any]:
    manifest = workspace.load()
    inspected = manifest.get("stages", {}).get("inspect")
    if not inspected or inspected.get("status") != "complete":
        raise RuntimeError("inspect must complete before extract")
    source, kind = Path(inspected["input"]), inspected["kind"]
    destination = workspace.root / "extracted"
    previous = manifest.get("stages", {}).get("extract", {})
    if any(destination.iterdir()):
        if previous.get("status") == "complete":
            return {key: value for key, value in previous.items() if key not in {"status", "updated_at"}}
        raise RuntimeError(f"extraction directory is not empty: {destination}")

    if kind == "zip-archive":
        with zipfile.ZipFile(source) as archive:
            members = _safe_zip_members(archive, destination)
            archive.extractall(destination, members=members)
        details = {"adapter": "zip", "output": str(destination), "members": len(members)}
        workspace.stage("extract", "complete", **details)
        return details
    if source.is_dir():
        if copy_source:
            shutil.copytree(source, destination / source.name, dirs_exist_ok=True)
            output = destination / source.name
        else:
            output = source
        details = {"adapter": "source-tree", "output": str(output), "copied": copy_source}
        workspace.stage("extract", "complete", **details)
        return details
    if kind in set(SOURCE_SUFFIXES.values()) | {"studio-source-archive"}:
        shutil.copy2(source, destination / source.name)
        details = {"adapter": "source-file", "output": str(destination / source.name)}
        workspace.stage("extract", "complete", **details)
        return details

    requirement = {
        "windows-executable": "Register a Classic decompiler or YYC static-analysis adapter.",
        "studio-data": "Run the included UndertaleModTool exporters, then place their output in extracted/.",
        "external-archive": "Extract the archive with a trusted external tool into extracted/.",
    }.get(kind, "No extraction adapter is registered for this artifact.")
    details = {"adapter": None, "requirement": requirement}
    workspace.stage("extract", "blocked", **details)
    return details


def audit_workspace(workspace: Workspace, scan_root: Path | None = None) -> dict[str, Any]:
    root = (scan_root or workspace.root / "modern").resolve()
    if not root.is_dir():
        raise FileNotFoundError(root)
    findings = []
    files_scanned = 0
    for path in sorted(root.rglob("*.gml")):
        files_scanned += 1
        text = path.read_text(encoding="utf-8", errors="replace")
        lowered = text.lower()
        for category, needles in AUDIT_PATTERNS.items():
            count = sum(lowered.count(needle) for needle in needles)
            if count:
                findings.append({"file": str(path.relative_to(root)), "category": category, "occurrences": count})
    summary = {
        "root": str(root),
        "files_scanned": files_scanned,
        "findings": findings,
        "note": "Findings identify review points, not confirmed defects.",
    }
    report_path = workspace.root / "reports" / "audit.json"
    report_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    workspace.stage("audit", "complete", report=str(report_path), files_scanned=files_scanned, finding_count=len(findings))
    return summary


def render_report(workspace: Workspace) -> tuple[Path, Path]:
    manifest = workspace.load()
    audit_path = workspace.root / "reports" / "audit.json"
    audit = json.loads(audit_path.read_text(encoding="utf-8")) if audit_path.exists() else None
    stages = manifest.get("stages", {})
    stages["report"] = {"status": "complete"}
    rows = []
    for name in ("inspect", "extract", "normalize", "generate", "repair", "build", "exercise", "audit", "compare", "report"):
        stage = stages.get(name, {})
        rows.append((name, stage.get("status", "pending"), stage.get("requirement", "")))

    markdown = ["# GameMaker recovery report", "", f"Generated: {utc_now()}", "", "| Stage | Status | Notes |", "|---|---|---|"]
    markdown.extend(f"| {name} | {status} | {note} |" for name, status, note in rows)
    inspected = stages.get("inspect", {})
    if inspected:
        markdown += ["", "## Input", "", f"- Kind: `{inspected.get('kind')}`", f"- SHA-256: `{inspected.get('sha256')}`", f"- Size: {inspected.get('size')} bytes"]
    if audit:
        markdown += ["", "## Static audit", "", f"Scanned {audit['files_scanned']} GML files and identified {len(audit['findings'])} review points."]
    md_path = workspace.root / "reports" / "report.md"
    md_path.write_text("\n".join(markdown) + "\n", encoding="utf-8")

    table = "".join(f"<tr><td>{html.escape(n)}</td><td>{html.escape(s)}</td><td>{html.escape(note)}</td></tr>" for n, s, note in rows)
    body = f"""<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>GameMaker recovery report</title><style>body{{font:16px system-ui;max-width:60rem;margin:3rem auto;padding:0 1rem;background:#f2f3f5;color:#15171c}}table{{border-collapse:collapse;width:100%;background:white}}th,td{{border:1px solid #bbb;padding:.65rem;text-align:left}}code{{overflow-wrap:anywhere}}</style><h1>GameMaker recovery report</h1><p>Generated {html.escape(utc_now())}</p><table><thead><tr><th>Stage</th><th>Status</th><th>Notes</th></tr></thead><tbody>{table}</tbody></table><h2>Input</h2><p>Kind: <code>{html.escape(str(inspected.get('kind', 'unknown')))}</code></p><p>SHA-256: <code>{html.escape(str(inspected.get('sha256', 'unavailable')))}</code></p></html>"""
    html_path = workspace.root / "reports" / "report.html"
    html_path.write_text(body, encoding="utf-8")
    workspace.stage("report", "complete", markdown=str(md_path), html=str(html_path))
    return md_path, html_path
