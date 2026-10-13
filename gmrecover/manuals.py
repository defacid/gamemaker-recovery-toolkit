"""Fetch and index public GameMaker manuals without redistributing their prose."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import time
import urllib.parse
import urllib.request
import urllib.error
import urllib.robotparser
from collections import deque
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Callable, Iterable


SCHEMA_VERSION = 1
USER_AGENT = "gmrecover-manual-indexer/0.3 (+https://github.com/defacid/gamemaker-recovery-toolkit)"
OFFICIAL_SOURCES = {
    "current-lts": {
        "url": "https://manual.gamemaker.io/lts/en/Content.htm",
        "publisher": "YoYo Games",
        "scope": "/lts/en/",
        "index_paths": ["/lts/en/GameMaker_Language/", "/lts/en/Additional_Information/"],
        "note": "Official LTS web manual; cache locally, do not redistribute its prose.",
    },
    "current-monthly": {
        "url": "https://manual.gamemaker.io/monthly/en/Content.htm",
        "publisher": "YoYo Games",
        "scope": "/monthly/en/",
        "index_paths": ["/monthly/en/GameMaker_Language/", "/monthly/en/Additional_Information/"],
        "note": "Official monthly web manual; cache locally, do not redistribute its prose.",
    },
}
HISTORICAL_SOURCES = {
    "gm6": {"status": "source-needed", "automatic_fetch": False, "note": "Import an authenticated installed/manual copy."},
    "gm81": {"status": "source-needed", "automatic_fetch": False, "note": "Import an authenticated installed/manual copy."},
    "gms14": {
        "status": "public-third-party-archive", "automatic_fetch": False,
        "url": "https://www.hitscan.org/dadiospice/", "publisher": "YoYo Games",
        "host": "Hitscan", "note": "Reported as extracted from the original installed 1.4 CHM; review provenance locally before import.",
    },
    "gms22": {"status": "source-needed", "automatic_fetch": False, "note": "Import an authenticated offline/manual copy."},
    "gms23": {"status": "source-needed", "automatic_fetch": False, "note": "Import an authenticated offline/manual copy."},
}
TEXT_SUFFIXES = {".htm", ".html", ".txt"}
SYMBOL = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(([^()\n]{0,300})\)")
PAGE_SYMBOL = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
KEYWORDS = {
    "if", "then", "else", "while", "do", "until", "for", "repeat", "with",
    "switch", "case", "default", "break", "continue", "exit", "return", "var",
    "globalvar", "enum", "function", "constructor", "new", "static", "try", "catch",
    "finally", "throw", "delete", "undefined", "true", "false", "noone", "self", "other",
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


class ManualHTML(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[str] = []
        self._capture: str | None = None
        self._buffer: list[str] = []
        self.code: list[str] = []
        self.headings: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "a" and values.get("href"):
            self.links.append(values["href"] or "")
        is_code_paragraph = tag == "p" and "code" in (values.get("class") or "").split()
        if tag in {"code", "pre", "h1", "h2", "h3"} or is_code_paragraph:
            self._capture = "p-code" if is_code_paragraph else tag
            self._buffer = []

    def handle_data(self, data: str) -> None:
        if self._capture:
            self._buffer.append(data)

    def handle_endtag(self, tag: str) -> None:
        expected = "p" if self._capture == "p-code" else self._capture
        if tag != expected:
            return
        value = " ".join("".join(self._buffer).split())
        if value:
            (self.code if tag in {"code", "pre"} or self._capture == "p-code" else self.headings).append(value)
        self._capture = None
        self._buffer = []


def source_catalog() -> dict[str, Any]:
    return {"schema_version": SCHEMA_VERSION, "official_sources": OFFICIAL_SOURCES,
            "historical_sources": HISTORICAL_SOURCES}


def _cache_path(cache: Path, release: str, url: str) -> Path:
    parsed = urllib.parse.urlparse(url)
    relative = parsed.path.lstrip("/") or "index.html"
    if relative.endswith("/"):
        relative += "index.html"
    return cache / release / "raw" / relative


def _canonical_url(url: str) -> str:
    parts = urllib.parse.urlsplit(urllib.parse.urldefrag(url).url)
    path = urllib.parse.quote(urllib.parse.unquote(parts.path), safe="/%:@")
    return urllib.parse.urlunsplit((parts.scheme, parts.netloc, path, parts.query, ""))


def fetch_manual(
    release: str,
    cache: Path,
    *,
    max_pages: int = 5000,
    delay: float = 0.1,
    progress: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    if release not in OFFICIAL_SOURCES:
        raise ValueError(f"unknown official manual release: {release}")
    definition = OFFICIAL_SOURCES[release]
    seed = definition["url"]
    seed_parts = urllib.parse.urlparse(seed)
    robots_url = urllib.parse.urlunparse((seed_parts.scheme, seed_parts.netloc, "/robots.txt", "", "", ""))
    robots = urllib.robotparser.RobotFileParser(robots_url)
    robots_available = False
    try:
        request = urllib.request.Request(robots_url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(request, timeout=30) as response:
            robots.parse(response.read().decode("utf-8", errors="replace").splitlines())
            robots_available = True
    except (OSError, urllib.error.URLError):
        # RFC 9309 treats most 4xx responses as "unavailable", not a blanket
        # prohibition. Keep the fetch scoped/rate-limited when no policy is
        # published for this client.
        robots_available = False
    queue = deque([seed])
    seen: set[str] = set()
    documents: list[dict[str, Any]] = []
    while queue and len(documents) < max_pages:
        url = _canonical_url(queue.popleft())
        if url in seen:
            continue
        seen.add(url)
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in {"http", "https"} or parsed.netloc != seed_parts.netloc:
            continue
        allowed_paths = definition.get("index_paths", [definition["scope"]])
        if url != seed and not any(parsed.path.startswith(prefix) for prefix in allowed_paths):
            continue
        if robots_available and not robots.can_fetch(USER_AGENT, url):
            continue
        target = _cache_path(cache.resolve(), release, url)
        reused = target.is_file()
        if reused:
            data = target.read_bytes()
        else:
            request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            try:
                with urllib.request.urlopen(request, timeout=30) as response:
                    content_type = response.headers.get_content_type()
                    data = response.read()
            except (OSError, urllib.error.URLError, ValueError) as error:
                documents.append({"url": url, "status": "failed", "error": str(error)})
                continue
            if content_type not in {"text/html", "application/xhtml+xml"}:
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        documents.append({
            "url": url, "path": str(target.relative_to(cache.resolve())), "status": "cached",
            "size": len(data), "sha256": sha256_bytes(data),
        })
        parser = ManualHTML()
        parser.feed(data.decode("utf-8", errors="replace"))
        for link in parser.links:
            absolute = urllib.parse.urljoin(url, link)
            link_parts = urllib.parse.urlparse(absolute)
            if (link_parts.path.lower().endswith((".htm", ".html"))
                    and any(link_parts.path.startswith(prefix) for prefix in allowed_paths)):
                queue.append(absolute)
        if progress:
            action = "reused" if reused else "cached"
            progress(f"[{len(documents)}/{max_pages}] {action} {url} | queued {len(queue)}")
        if delay and not reused:
            time.sleep(delay)
    manifest = {
        "schema_version": SCHEMA_VERSION, "release": release, "source": definition,
        "retrieved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "documents": documents, "truncated": bool(queue),
    }
    manifest_path = cache.resolve() / release / "manifest.json"
    write_json(manifest_path, manifest)
    return {"manifest": str(manifest_path), "documents": len(documents), "truncated": bool(queue)}


def import_manual(release: str, source: Path, cache: Path) -> dict[str, Any]:
    """Copy an authorized local HTML/text manual into the private cache."""
    source = source.resolve()
    if not source.exists():
        raise FileNotFoundError(source)
    paths = [source] if source.is_file() else sorted(path for path in source.rglob("*") if path.is_file())
    supported = [path for path in paths if path.suffix.lower() in TEXT_SUFFIXES]
    if not supported:
        raise ValueError("no indexable HTML or text files found; CHM/PDF requires an external text extraction adapter")
    raw = cache.resolve() / release / "raw-local"
    documents = []
    for path in supported:
        relative = Path(path.name) if source.is_file() else path.relative_to(source)
        target = raw / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        data = target.read_bytes()
        documents.append({
            "source_path": str(path), "path": str(target.relative_to(cache.resolve())),
            "status": "cached", "size": len(data), "sha256": sha256_bytes(data),
        })
    manifest = {
        "schema_version": SCHEMA_VERSION, "release": release,
        "source": {"kind": "local", "path": str(source)},
        "retrieved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "documents": documents, "truncated": False,
    }
    manifest_path = cache.resolve() / release / "manifest.json"
    write_json(manifest_path, manifest)
    return {"manifest": str(manifest_path), "documents": len(documents), "truncated": False}


def _document_paths(cache: Path, manifest: dict[str, Any]) -> Iterable[tuple[Path, dict[str, Any]]]:
    for record in manifest.get("documents", []):
        relative = record.get("path")
        if relative and record.get("status") == "cached":
            path = cache / relative
            if path.is_file():
                yield path, record


def index_manual(release: str, cache: Path, output: Path) -> dict[str, Any]:
    cache = cache.resolve()
    manifest_path = cache / release / "manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    symbols: dict[str, dict[str, Any]] = {}
    found_keywords: set[str] = set()
    indexed = 0
    for path, record in _document_paths(cache, manifest):
        text = path.read_text(encoding="utf-8", errors="replace")
        parser = ManualHTML()
        if path.suffix.lower() in {".htm", ".html"}:
            parser.feed(text)
            searchable = parser.code + parser.headings
        else:
            searchable = text.splitlines()
        citation = record.get("url") or f"local:{path.relative_to(cache)}"
        category = "/".join(path.parts[-3:-1])
        status = "obsolete" if "obsolete" in path.as_posix().lower() else "documented"
        page_name = path.stem
        touched: set[str] = set()
        canonical_seen: set[str] = set()
        is_reference_page = "GML_Reference" in path.parts and PAGE_SYMBOL.fullmatch(page_name)
        if is_reference_page:
            symbols.setdefault(page_name, {"name": page_name, "kind": "reference-page", "signatures": [], "citations": [], "categories": [], "status": status})
            touched.add(page_name)
        for fragment in searchable:
            lower_words = set(re.findall(r"\b[a-z]+\b", fragment.lower()))
            found_keywords.update(KEYWORDS & lower_words)
            for match in SYMBOL.finditer(fragment):
                name = match.group(1)
                if name.lower() in KEYWORDS:
                    continue
                is_canonical = name.casefold() == page_name.casefold()
                is_compatibility_list = "Additional_Information" in path.parts
                if not is_canonical and not is_compatibility_list:
                    continue
                signature = f"{name}({match.group(2).strip()})"
                entry = symbols.setdefault(name, {"name": name, "kind": "function", "signatures": [], "citations": [], "categories": [], "status": status})
                if is_canonical:
                    entry["kind"] = "function"
                    # Reference pages put canonical syntax before examples.
                    # Retaining the first self-named call avoids treating the
                    # page's usage examples as additional declarations.
                    if name in canonical_seen:
                        continue
                    canonical_seen.add(name)
                touched.add(name)
                if signature not in entry["signatures"]:
                    entry["signatures"].append(signature)
                if status == "obsolete":
                    entry["status"] = status
        for name in touched:
            entry = symbols[name]
            if citation not in entry["citations"]:
                entry["citations"].append(citation)
            if category and category not in entry["categories"]:
                entry["categories"].append(category)
        indexed += 1
    value = {
        "schema_version": SCHEMA_VERSION, "release": release,
        "source_manifest_sha256": sha256_bytes(manifest_path.read_bytes()),
        "documents_indexed": indexed, "keywords": sorted(found_keywords),
        "symbols": sorted(symbols.values(), key=lambda item: item["name"].casefold()),
        "notice": "Derived facts and citations only; manual prose is not included.",
    }
    write_json(output.resolve(), value)
    return {"output": str(output.resolve()), "documents": indexed, "symbols": len(symbols), "keywords": len(found_keywords)}
