# Versioned GameMaker manual index

The manual index supplies evidence to future version-aware GML lexers, parsers,
and compatibility analysis. It is not itself a converter and must not be used
to justify blind textual replacements.

## Legal and provenance boundary

- `gmrecover` does not redistribute GameMaker manual prose.
- Public web manuals are cached locally under an ignored directory.
- Historical manuals may be imported only from copies the user is authorized
  to access.
- Every cached document is recorded with its source URL or local path, byte
  size, SHA-256 digest, retrieval time, and release label.
- Derived indexes contain facts and citations only: identifiers, signatures,
  keywords, categories, compatibility status, and source-manifest digest.
- A public URL does not imply an open-content license. Do not commit raw caches.

## Release labels

Release labels are stable user-facing identifiers, not inferred compatibility.
The built-in registry currently contains `current-lts` and `current-monthly`.
Use explicit labels such as `gm6`, `gm81`, `gms14`, `gms22`, and `gms23` when
importing authenticated historical copies. Do not combine manuals from distinct
eras under one label.

`manuals sources` also lists historical eras whose source copies still need to
be authenticated. Third-party preservation mirrors are recorded as leads but
are never fetched automatically or represented as official hosting. This keeps
provenance uncertainty visible instead of quietly blending mirrors into the
official corpus.

## Parser use

The facts database can answer which identifiers and signatures are documented
for a release and cite the supporting page. Grammar and semantic transformations
still require reviewed rules and artifact-free compiler/runtime fixtures.
Absence from a partial index is unknown, not proof that a construct did not
exist. Check the manifest's `truncated` field and document count before drawing
version conclusions.

## Commands

```sh
gmrecover manuals sources
gmrecover manuals fetch current-lts --cache manual-cache --max-pages 5000
gmrecover manuals import gm81 /path/to/html --cache manual-cache
gmrecover manuals index gm81 --cache manual-cache --output gm81-facts.json
```

Fetching respects a published `robots.txt`, stays within the registered release
host and language/compatibility paths, identifies itself with a dedicated user
agent, rate-limits requests, and records failed pages. When `robots.txt` itself
returns a 4xx response, it is treated as unavailable according to the robots
standard rather than as an implicit ban. Use `--delay` and `--max-pages` to
further limit a run.
