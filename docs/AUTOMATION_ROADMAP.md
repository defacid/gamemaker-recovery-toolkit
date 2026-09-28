# Automation roadmap

The long-term interface should be one local command that accepts an authorized
GameMaker artifact and produces a conversion workspace, validation report, and
reviewable browser build. The pipeline must remain deterministic: every repair
belongs in configuration or code rather than an unrecorded editor change.

## Proposed command

```sh
gmrecover convert path/to/game.exe --target html5 --open-report
```

The command should create a workspace containing an immutable input manifest,
extracted resources, normalized intermediate data, generated GameMaker source,
compiled output, screenshots, machine-readable audit results, and a human
report.

## Pipeline stages

1. **Inspect** — hash the artifact and identify GM6, GM7, GM8, Studio VM, Studio
   YYC, or editable source without executing unknown binaries.
2. **Extract** — select an appropriate adapter and preserve sprites, origins,
   masks, rooms, code, fonts, audio, and metadata.
3. **Normalize** — convert version-specific data into a documented intermediate
   representation without silently inventing missing values.
4. **Generate** — produce a modern GameMaker project from the intermediate data.
5. **Repair** — apply a versioned rule pack containing project-specific fixes.
6. **Build** — invoke a pinned local GameMaker runtime through a configurable
   adapter and reject stale compiler output.
7. **Exercise** — launch the browser build, inject declared controls, capture
   exceptions and network failures, and take screenshots at staged times.
8. **Audit** — check collision masks, sprite origins, scaling, rotation, tiled
   drawing, surfaces, interpolation, fonts, audio, room speed, and canvas size.
9. **Compare** — compare screenshots and event traces with approved references,
   while reporting uncertainty instead of declaring visual similarity perfect.
10. **Report** — emit JSON for automation and HTML/Markdown for human review.

## What can be automated well

- Artifact classification and hashing
- Known-format resource extraction
- Project generation and repeatable rule packs
- Compiler invocation and cache isolation
- Static compatibility audits
- Browser startup and scripted input
- Runtime error, console, and missing-resource collection
- Timed screenshots and perceptual diffs
- Regression reports and conversion manifests

## What still requires judgment

- Reconstructing behavior absent from every surviving artifact
- Deciding whether a visual difference is intentional
- Inferring controls or game rules that are not represented in code
- Approving recovered third-party material for redistribution
- Creating a new compatibility repair for an undocumented runtime difference

The tool should stop with a precise diagnostic at those boundaries. Once a new
repair is understood, it becomes a fixture and rule so subsequent projects do
not require another manual investigation.

## Recommended implementation

Use a Python CLI for orchestration because the existing conversion and audit
tools are already Python-based. Keep extractors and builders behind adapters,
store project configuration in TOML, and emit a stable JSON report. Use
Playwright for browser exercises and screenshots. Package the CLI only after a
small fixture suite covers each supported source family.

Suggested phases:

1. Wrap the existing scripts in a `gmrecover` command with `inspect`, `extract`,
   `audit`, and `report` subcommands.
2. Define the workspace manifest and TOML rule-pack schema.
3. Add pinned GameMaker build adapters and isolated build directories.
4. Add Playwright scenarios, screenshot capture, and runtime-error collection.
5. Turn every repaired game incompatibility into an artifact-free regression
   fixture.
6. Add `convert` as the end-to-end command after the individual stages are
   reliable and resumable.
