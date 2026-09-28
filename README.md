# GameMaker Recovery Toolkit

Field-tested notes, exporters, audits, and reference transformations for
preserving authorized GameMaker projects and rebuilding them for current
GameMaker HTML5 runtimes.

This repository focuses on the difficult part of preservation: behavioral
fidelity. A project compiling is not enough. Collision masks, trimmed sprite
origins, negative scaling, room speed, texture interpolation, surfaces, legacy
tiles, bitmap fonts, draw order, audio staging, and browser scaling all need to
match the preserved build.

## Scope and ethics

Use these tools only with software you created, own, or have permission to
preserve. The repository intentionally contains no recovered games, executable
payloads, proprietary artwork, audio, fonts, or GameMaker runtime files.

Never execute an unknown archived binary merely to inspect it. Hash it, unpack
it statically, work on copies, and retain an immutable preservation original.

## What is included

- `scripts/utmt/` — UndertaleModTool scripts for exporting Studio VM code,
  metadata, sprites with trim padding, backgrounds, audio, and embedded bitmap
  fonts.
- `scripts/classic/` — GMX normalization and static YYC event discovery.
- `scripts/audit/` — collision-mask and gameplay-fidelity inventory helpers.
- `examples/rule-packs/` — the real conversion rule packs that produced the
  documented findings. They are examples to extract into a generic pipeline,
  not one-command converters for arbitrary games.
- `docs/FIELD_NOTES.md` — the complete living notebook: symptoms, causes,
  repairs, build behavior, and browser regression lessons.
- `docs/COLLISION_AUDIT.md` and `docs/PROCESS_AUDIT.md` — focused review
  checklists.
- `docs/AUTOMATION_ROADMAP.md` — a staged design for turning the conversion
  process into a resumable `gmrecover` command-line tool.

## Recovery workflow

1. Preserve and hash the original artifact.
2. Classify it as editable source, source-bearing archive, Classic executable,
   Studio VM data, or Studio YYC/native data.
3. Prefer original source whenever it exists.
4. Export resources without losing sprite canvas padding, origins, glyph
   metrics, room/view settings, or interpolation flags.
5. Generate a modern project deterministically; keep manual fixes in a rule
   pack so regeneration cannot erase them.
6. Audit collision masks, transforms, tiled draws, surfaces, primitives, fonts,
   room speed, and staged audio.
7. Compile with a pinned GameMaker runtime.
8. Validate in a real browser with automated input, runtime-exception capture,
   network-error capture, and reviewed gameplay screenshots.
9. Record every repair as: visible symptom, underlying incompatibility,
   deterministic transformation, and regression test.

## Studio VM extraction

The `.csx` files are intended for UndertaleModTool/UndertaleModCli. Each output
location is supplied through an environment variable so scripts never hardcode
a preservation workspace:

```sh
export DEFACID_CODE_OUT="$PWD/recovered/CodeEntries"
export DEFACID_SPRITES_OUT="$PWD/recovered/Sprites"
export DEFACID_BACKGROUNDS_OUT="$PWD/recovered/Backgrounds"
export DEFACID_AUDIO_OUT="$PWD/recovered/Audio"
export DEFACID_FONTS_OUT="$PWD/recovered/Fonts"
export DEFACID_METADATA_OUT="$PWD/recovered/metadata.json"

UndertaleModCli load game.ios -s scripts/utmt/export_studio_code.csx
UndertaleModCli load game.ios -s scripts/utmt/export_studio_sprites.csx
UndertaleModCli load game.ios -s scripts/utmt/export_studio_backgrounds.csx
UndertaleModCli load game.ios -s scripts/utmt/export_studio_audio.csx
UndertaleModCli load game.ios -s scripts/utmt/export_studio_fonts.csx
UndertaleModCli load game.ios -s scripts/utmt/export_studio_metadata.csx
```

Important: padded sprite export is deliberate. Exporting only the trimmed
texture-page rectangle moves pixels to `(0,0)` and breaks origins, flips,
shadows, and collision placement.

## Development checks

```sh
npm install
npm run check

python scripts/audit/audit_gameplay_fidelity.py /path/to/modern-projects
python scripts/audit/audit_collision_masks.py \
  /path/to/conversion-workspace /path/to/rule-pack.py
```

## `gmrecover` CLI

Install the local command in an isolated environment:

```sh
python3 -m venv .venv
.venv/bin/pip install -e .
```

Run the safe end-to-end stages against an authorized artifact:

```sh
gmrecover convert path/to/game.zip --workspace work/game
```

Or run stages individually:

```sh
gmrecover inspect path/to/game.exe --workspace work/game
gmrecover extract --workspace work/game
gmrecover audit --workspace work/game --root work/game/modern
gmrecover report --workspace work/game
```

`convert` never executes an input binary. Known source trees and ZIP archives
are copied or safely extracted. Formats requiring UndertaleModTool, a Classic
decompiler, or YYC analysis are recorded as blocked with a specific adapter
requirement, while still producing a manifest and report.

After extraction, define project-specific commands in a TOML file and run the
remaining stages locally:

```sh
gmrecover pipeline recovery.toml --workspace work/game
```

See [`examples/pipeline.toml`](examples/pipeline.toml) for normalize, generate,
repair, GameMaker build, Playwright exercise, and screenshot-comparison stages.
Commands are executed directly without a shell, logged separately, recorded in
the manifest, stopped on failure, and skipped on later runs once complete. Use
`--force` or `--from STAGE` when deliberately rerunning work. Pipeline files
are executable configuration and should only be used from trusted sources.

GameMaker compilation is intentionally not wrapped as a universal command:
runtime paths, licenses, user profiles, targets, and output layouts vary. Pin
the runtime in your own build adapter and reject stale shared compiler output.

## Status

This is an initial extraction of a working preservation workspace. The field
notes are mature; the rule packs are being generalized. Contributions should
include a reproducible fixture or an artifact-free regression description.

## License

Released under the [MIT License](LICENSE).
