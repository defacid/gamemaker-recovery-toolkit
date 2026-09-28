# Legacy GameMaker Conversion Notes

**Status:** Living implementation notebook  
**Last updated:** 2026-09-25  
**Scope:** Recovering owner-created GameMaker 6/7/8 projects and producing reviewed HTML5 derivatives

This document records the practical knowledge learned while converting the DEFACID archive. It complements the higher-level [`GAMEMAKER_BROWSER_PORTING_PLAN.md`](../GAMEMAKER_BROWSER_PORTING_PLAN.md). Update this file whenever a conversion reveals a new compatibility rule, repair, build requirement, or test failure.

The long-term goal is to turn the repeatable parts of this process into a tool. Until that exists, this is the human-readable specification for that tool.

## Preservation rules

- Never modify the original `.gm6`, `.gmk`, `.gm81`, archive, or executable.
- Hash every input before processing and retain its original relative path.
- Work only from copied source in `input/`, `split/`, `recovered/`, and `modern/`.
- Treat executable decompilation as reconstruction, not lossless source recovery.
- Do not execute an unknown archived game executable on the host. Use an isolated Windows VM when behavioral comparison is necessary.
- Keep the modern GameMaker project and published HTML5 output separate from the preservation original.
- Record every automatic rewrite and every hand-authored compatibility repair.

## Workspace layout

| Path | Purpose |
| --- | --- |
| `input/64digits/` | Working copies of archived inputs |
| `recovered/source-original/` | Source extracted from archives without modernization |
| `recovered/executable-original/` | Preserved executable-only candidates |
| `split/` | Gmk-Splitter XML and extracted resource trees |
| `modern/<project>/` | Generated current-format GameMaker projects |
| `cache/<project>/` | Per-project GameMaker/Igor build cache |
| `generated/` | Deterministically composed intermediate assets |
| `html5/` | Shared local GameMaker HTML5 export staging area |
| `../defacid-site/public/legacy-normalized/<slug>/` | Reviewed site-ready browser build |

Do not assume `html5/` contains a self-contained build for only one game. Igor currently writes each export into this shared directory and replaces `index.html` while leaving assets from prior builds in place.

## Pinned recovery tools

| Tool | Version or artifact | SHA-256 / location | Role |
| --- | --- | --- | --- |
| Gmk-Splitter | 0.21 | `4418aede1315057828b5102e7e1345ef60fb65b370beb6650db9fcf70e675fe9` | Split legacy project source into XML/resources |
| GM8Decompiler | 2.2.0 Windows x64 | `a68a4cdbd455a2164885c8d854e5f7891324043cddad19b80bf1d9c4d958a860` | Recover supported GM8 executables when source is absent |
| GM Decompiler | 2.1 (`gm567-decompiler-2.1.zip`) | `25fea4747a4f4e816cf3b1b89d7a028ea6d5ae644f5f204c4072c9382f4437bc` | Recover owned GM5/GM6/GM7 executables when editable source is absent |
| UndertaleModTool CLI | 0.9.2.0 Ubuntu | `d182f00c0e5ced8d9252aa1f796374cfee077a3889a658e70b68685f9cd559c7` | Statically inspect and export GMS1/GMS2 VM `data.win` resources without launching the game |
| Eclipse Temurin JRE | 17 | `bc21a93923103cdaac93ee337b0ae4365e739fde36df823dd456bc67c8a9d352` | Run Java-based recovery tooling where required |
| LateralGM | 1.8.234 | `1838f0620fd8c7f0a5a72104854dfe541cbde5dfd12dd29ae49e04e2e466ec3a` | Read GM6 projects and write a GM8-compatible working copy |
| Eclipse Temurin JDK | 17.0.20.1+1 | `e53a79c3c3d86865bd7e787903884331068e71321714ffd44f145785affc7cb0` | Compile the small headless LateralGM conversion bridge |
| GameMaker LTS runtime | `runtime-2024.14.4.268`, nested under `runtime-2026.0.0.23` | Local licensed GameMaker installation | Compile the generated `.yyp` projects for HTML5 |
| Rez font reference | `rez.ttf`, Faizal Reza (1997) | `89fb99b0639ece70c81dfea98f0104695328b10d6088758d4917636ebc9f23a7` | Archived comparison reference; the reviewed Organism browser port deliberately uses Arial |

Record hashes again if any pinned archive is replaced. Do not silently upgrade a recovery tool or GameMaker runtime: generated JavaScript, texture pages, and compatibility behavior can change.

## Current conversion pipeline

### HTML5 compatibility repairs added 2026-09-23

- Preserve a room's authored clear colour when it is known; do not apply the generic gray fallback to intentionally white rooms (Quilder).
- Legacy dialogue arrays may begin at index `1`. Normalize their counters before an HTML5 build so the first panel is not created with an undefined string (Hydra/Gaemmem pattern).
- `variable_local_exists` is not implemented by the current HTML5 runner. Replace only proven legacy fallbacks with supported state assumptions or `variable_instance_exists`; Hydra's message fields are assigned before their first draw.
- Avoid legacy instance variables named `draw` in current GML: the HTML5 compiler treats that name as a callable symbol. Hydra's dialogue animation now uses `message_draw`.
- Do not rely on blocking desktop file dialogs (`get_string`, `show_question`, `get_open_filename`) in browser builds. For Organism v8, editor save/load uses one browser-local `.odf` slot instead; its name button assigns `Custom Organism`.
- Embedded canvas key-up events can be lost during focus changes. Interface prototypes such as VS Action Menu should use a press-to-toggle control instead of depending on a transient key hold.

### 1. Inventory and classify

Run from this directory:

```sh
python3 inventory.py
```

The inventory process hashes artifacts, identifies recognized GameMaker source, extracts source-bearing archives, and copies executable-only candidates without executing them. Classify each input as one of:

- direct source;
- source-bearing archive;
- executable-only recovery candidate;
- data-only;
- duplicate;
- corrupt; or
- out of scope.

### 2. Split the legacy source

Use the pinned Gmk-Splitter against a working copy. The expected result is a resource tree containing directories such as `Sprites`, `Objects`, `Rooms`, `Fonts`, `Backgrounds`, `Sounds`, `Paths`, `Scripts`, and `Time Lines`.

Important checks after splitting:

- Count resources and compare names with the original project inventory.
- Confirm that event XML exists beside each object resource.
- Confirm sprite frame PNGs and background PNGs were emitted.
- Inspect room dimensions, views, instance order, room creation code, tiles, and background definitions.
- Preserve the split output even after a modern project has been generated; it is the auditable intermediate representation.

#### Studio VM builds (`data.win`)

GameMaker Studio VM builds need a separate route from GM5–GM8 executables. Use the pinned UndertaleModTool CLI against a copied `data.win`; do not launch the associated game executable.

- Run the CLI with `DOTNET_SYSTEM_GLOBALIZATION_INVARIANT=1` on the current Linux host because ICU is not installed.
- Dump code entries, strings, embedded textures, and decoded sprite frames into `recovered/studio/<project>/`.
- Run [`export_studio_metadata.csx`](export_studio_metadata.csx) to create deterministic sprite, object/event, room/view, script, sound, and font metadata.
- Run [`export_studio_audio.csx`](export_studio_audio.csx) to export audio embedded directly in `data.win`. External audio groups must be copied from the preserved package and recorded separately.
- Generate the modern project with [`convert_studio_dump.py`](convert_studio_dump.py). The converter is currently proven against the POLYFACED VM dump; collision event subtype mapping and non-default audio groups still need explicit support before treating it as general-purpose.
- Compare resource counts and event bodies against any owner source that later becomes available. Prefer owner source for publication and retain the VM dump as an independent recovery audit.

#### POLYFACED renderer recovery

POLYFACED's archived `obj_mob` uses the default sprite draw and has no serialized hit-flash state. The Studio converter therefore adds an explicit mob Draw event for this project: it always draws in white, uses a four-frame red tint after an attack connects, and restores white/opaque draw state afterward. Keep this as a named converter rule rather than a hand edit to `modern/polyfaced/`, since the generated project is replaced on every recovery run.

When the owner-provided POLYFACED source checkout is available, compile it directly for publication instead of publishing the VM-dump reconstruction. The owner project preserves more resources (including the original object and audio set); the reconstruction remains useful only as an audit and fallback path.

### 3. Generate a modern GameMaker project

The current prototype converter is [`convert_lar_inventory.py`](convert_lar_inventory.py). Despite its historical filename, it now has configurations for:

- `lar_inventory_ex`
- `tembo`
- `64jam` (published as Priorities)
- `unfinishedwaspgame`
- `hydra`
- `gaemmem`
- `zombieinfection`
- `char_test`, `ex_char_select`, `lego`, and `vs_actionmenu`
- `fireworks_v1_2`, `rpsx`, and `rps2`
- `organism_v03`, `organism_v04`, and `organism_v05`

Example:

```sh
python3 convert_lar_inventory.py hydra
```

The converter creates resources in `modern/<project>/`. It translates sprite metadata, object events, GML, rooms, views, fonts, and project resource references. Project-specific behavior is currently declared in the `CONFIGS` table. A future tool should replace those Python literals with a versioned conversion manifest.

### 4. Compile with GameMaker's Igor worker

On the current Windows installation, the functional compiler is the nested runtime, not the outer `runtime-2026.0.0.23` wrapper:

```text
C:/ProgramData/GameMakerStudio2-LTS2026/Cache/runtimes/
  runtime-2026.0.0.23/runtime-2024.14.4.268/
```

The command shape that produced the reviewed builds is:

```sh
IGOR='/mnt/c/Program Files path/to/runtime-2024.14.4.268/bin/igor/windows/x64/Igor.exe'

"$IGOR" -v -j=8 \
  --runtimePath="C:/.../runtime-2024.14.4.268" \
  --project="C:/.../gamemaker-recovery/modern/<project>/<project>.yyp" \
  --cache="C:/.../gamemaker-recovery/cache/<project>" \
  --temp="C:/Users/<user>/AppData/Local/Temp/<project>-html5" \
  --user="C:/Users/<user>/AppData/Roaming/GameMakerStudio2-LTS2026/<account>" \
  --runtime=VM \
  --of="C:/.../gamemaker-recovery/html5/<project>" \
  html5 folder
```

Use forward slashes in interpolated Windows paths. Backslash-plus-shell-variable combinations caused malformed paths such as `modern$project$project`.

Known Igor behavior in this setup:

- The asset compiler writes the usable output to the shared `html5/` directory, even when `--of` names a project subdirectory.
- The `folder` command may finish compilation and then throw `System.ArgumentException: The value cannot be an empty string` during its final copy/package step.
- Do not treat the mere presence of an old JavaScript file as proof of a successful rebuild.
- Require the current build log to contain `Saving HTML5 file...` and verify that the expected output modification time or hash changed before publishing it.
- Use a separate cache and temporary directory for every project.

A conversion tool should wrap Igor, detect this partial-success condition, isolate staging directories, and refuse to publish stale artifacts.

### 5. Stage the browser build

Copy only the freshly generated files belonging to the project:

- `index.html`
- `favicon.ico`
- `html5game/<project>.js`
- all generated `<project>_texture_*.png` files;
- `html5game/splash.png` if referenced;
- runtime particle, audio-worklet, and other support directories when referenced by the generated JavaScript.

Publish them under:

```text
defacid-site/public/legacy-normalized/<public-slug>/
```

Do not copy the entire shared `html5/` directory: it may contain assets from unrelated projects. Conversely, do not omit runtime support files. Test with an HTTP server and treat every unexpected `404` as a release failure.

### 6. Refresh the site manifest and build

From `defacid-site/`:

```sh
npm run build
```

This regenerates `PUBLIC_ASSET_MANIFEST.csv`, runs Astro diagnostics, builds the static site, and runs smoke checks. A port is not ready if the build, diagnostics, smoke checks, browser console, or network log reports a failure.

## Automatic GML compatibility rewrites

The converter currently performs these transformations:

| Legacy construct | Current rewrite or handling |
| --- | --- |
| `image_single` | `image_index` |
| `view_xview`, `view_yview` | Camera view getters |
| `view_wview`, `view_hview` | Camera width/height getters |
| Three-argument `instance_create(x, y, object)` | `instance_create_depth(x, y, 0, object)` |
| Legacy two-dimensional `obj[a,b]` access | `obj[a][b]` |
| Legacy single-quoted strings | Double-quoted strings |
| `#` inside classic strings | `\n` line break |
| Obsolete background alpha/speed array assignments | Removed when the modern background implementation replaces them |
| Invalid `if move_towards_point(...)` pattern | Converted to the callable statement used by the recovered projects |

These are compatibility rules, not universally safe text substitutions. A future converter should parse GML or at minimum attach each rewrite to a source span, emit a diagnostic, and support project-level opt-outs.

## Resource conversion notes

### Sprites and masks

- Preserve frame order, origin, collision mask, bounding box, transparency, and playback speed.
- A visually correct sprite with the wrong origin can make the game appear mechanically broken.
- Chroma-key cleanup may be necessary for old opaque sprite sheets. [`chroma_key_sprite.mjs`](chroma_key_sprite.mjs) exists for controlled bitmap cleanup; retain the original frames.
- Background images imported as sprites must use the intended room origin and must not inherit an accidental collision role.

### Room backgrounds and tiles

- Legacy rooms may combine a base background with background tiles. Importing only the base image produces an incomplete scene.
- [`compose_room_background.mjs`](compose_room_background.mjs) creates a deterministic flattened image from the room color, base background, and tile placement manifest.
- Zombie Infection uses this path to produce `generated/zombieinfection-rm_game.png`.
- Store enough metadata to regenerate the composed image; never make the flattened bitmap the only retained representation.
- Preserve `tileHorizontally`, `tileVertically`, layer order, offsets, and per-step speed for every visible background definition. A single `draw_self()` is not equivalent to a classic room background. The shared background object now uses tiled drawing; RPS Xtreme also restores its scrolling base layer and second repeated overlay.

### Draw order

- Legacy instance order and depth need explicit modern layers.
- Full-room background objects belong on a dedicated deepest layer, currently depth `1000000`.
- Drawing the background from a gameplay object is fragile because visibility, destruction, or event order can expose an unpainted frame.
- Hydra and Gaemmem use a dedicated `obj_room_background` to draw the static star field and animated star overlays before gameplay objects.

### Frame clearing and flicker

- Every generated room must set `viewSettings.clearDisplayBuffer` to `true`.
- Leaving it `false` exposed undefined back-buffer frames in the HTML5 runtime. This first appeared as white flicker and later as black flicker depending on the canvas/page background.
- A background object is still useful for fidelity, but it does not replace clearing the display buffer.
- Changing the surrounding CSS from white to black only changes the symptom; it does not fix the renderer.
- Validate at multiple capture times and during active play, because a single screenshot may miss alternating-frame defects.

### Fonts and text drawing

Legacy font names frequently differ from installed modern fonts. The current mappings are:

| Legacy face | Atlas source |
| --- | --- |
| Arial Black | `ariblk.ttf` |
| Arial | `arialbd.ttf` |
| Terminal | `consolab.ttf` |
| Small Fonts | `arial.ttf` |
| Eurostile | `GOTHICB.TTF` |
| Futura Bk | `GOTHICB.TTF`, exposed as Century Gothic |
| Century Gothic | `GOTHICB.TTF` |

[`generate_font_atlas.ps1`](generate_font_atlas.ps1) renders the glyph atlas and produces metrics used by the modern font resource. Text must be tested visually for:

- glyphs appearing as solid rectangles;
- wrong baseline or line height;
- missing punctuation/digits;
- different width causing menu or HUD overflow;
- classic `#` line breaks;
- antialiasing changes at the game's native resolution.

Do not rely only on the font family name. Pin the actual font file used to generate the atlas, and document redistribution constraints before publishing it.

### Views, native resolution, and embedding

- Preserve the room and view dimensions from source.
- Let the site scale the iframe/canvas as one unit while retaining the game's internal resolution and aspect ratio.
- Do not enlarge the room or add canvas area to make the embed look larger; that creates unused black space and changes input coordinates.
- Pixel-art ports should use nearest-neighbor presentation where appropriate.
- The page background around a canvas should visually match the site's game presentation, but should never be used to hide missing frame drawing.
- Treat legacy `view_xport`, `view_yport`, `view_wport`, `view_hport`, and related names as arrays. Using a bare view array in arithmetic compiles but throws a type-conversion exception at runtime; the POLYFACED canonical source needed `[0]` in its GUI draw event.

### Browser-only failures that compilation does not catch

- Asset references and filenames must match case exactly. Windows can load a case-mismatched build that fails on a Linux host. Site smoke checks now compare every HTML path component against the actual directory entry.

### September 2026 browser regression pass

Use a real Chromium session plus [`browser_smoke.mjs`](browser_smoke.mjs), not only the static smoke script, after publishing a runtime. The 2007-to-2026 catalog pass exercised every entry marked `play_in_browser`: it includes both Run Boy Run, RPS, and Hydra revisions, and uses project-specific input scenarios where available. The focused renderer pass also verified Fireworks draw ordering, Snowstorm's repeated background and debris rendering, Zombie Infection's active playfield, Hydra's non-black starfield, and Organism's editor route. Minijam #1 was started three consecutive times to guard against its historical intermittent viewport initialization issue.
- A successful GameMaker compile does not prove that every runtime function exists on HTML5. The Organism editor used `variable_local_get/set` with string-built array indices; these are rewritten to direct array access.
- Stage every generated audio derivative referenced by the JavaScript. Fireworks initially omitted its five generated `.ogg`/`.mp3` files, producing `EncodingError` exceptions when the server returned non-audio responses. Site smoke checks now scan GameMaker JavaScript sound names and require a staged audio file.
- Gameplay smoke scenarios fail the run on `Runtime.exceptionThrown`; merely capturing a screenshot is not sufficient.

## Restoration debugging flow learned from Cannonauts

Use this sequence when a recovered build reaches its first room but menus or later rooms appear blank:

1. **Keep the repair inside GameMaker.** Do not add HTML controls, title cards, or replacement menus around the canvas. The site wrapper may launch and size the game only.
2. **Separate state/input from visibility.** Confirm whether hidden menu input still changes state. If it does, preserve that event and investigate draw ordering rather than rebuilding navigation.
3. **Test Draw GUI explicitly.** Add a temporary primitive in Draw GUI. If it appears while normal-Draw text does not, a surface/application-surface pass is covering normal Draw. Remove the diagnostic primitive and redraw the recovered menu state in Draw GUI.
4. **Inspect both room order structures.** Modern `.yy` rooms have layer instance arrays and `instanceCreationOrder`. Runtime Create order follows `instanceCreationOrder`; sorting only layer members does not initialize dependencies sooner.
5. **Allocate legacy arrays.** GM8/GMS1 code often creates arrays through first indexed assignment. Recovered modern projects should initialize global and instance arrays with `array_create` before any read, especially player, ready, result, spawn, and menu arrays.
6. **Reserve keyboard slot zero.** If keyboard control shares player/gamepad slot zero, loops must use at least one slot even when `gamepad_get_device_count()` returns zero.
7. **Exercise the entire route.** A title screenshot is insufficient. Script every confirmation and required countdown through the first active room. Hold synthetic keys for multiple frames; instantaneous key-down/key-up pairs can be missed by GameMaker.
8. **Read runtime exceptions before interpreting black frames.** A black screenshot after input may be a hidden intermediate menu or an exception repeated every Draw frame, not a failed `room_goto`.
9. **Stage dependencies from generated output.** Copy root-level generated audio derivatives as well as support directories, then distinguish expected autoplay/decode restrictions from HTTP 404 responses.
10. **Capture evidence at each milestone.** Cannonauts retains captures for the initial menu, Launch menu, player setup, and active arena so later changes can be checked against each stage.

For a Windows Chrome instance launched from WSL, the Windows portable Node binary can run `browser_smoke.mjs` against Chrome's localhost DevTools port when the Linux process cannot cross the Windows debugging-port firewall. This allows real key input, intermediate screenshots, and `Runtime.exceptionThrown` collection without weakening browser networking settings.

## Collision-mask fidelity pass

The first generator emitted every sprite with a full-frame bounding box and precise collision kind. That is not equivalent to legacy GameMaker metadata and caused visible early collisions:

- LOWG's 16×16 `spr_agent` has an authored manual mask of left 4, right 12, top 0, bottom 16 (clamped to the modern frame edge at 15). The incorrect full 0–15 width made the player contact walls several pixels early.
- QuilDER's `spr_bullet` frames are 64×64 for rotation/origin layout, but their visible projectile is only a 2×2 alpha region at x 28–29, y 30–31. A full-frame mask caused enemy collision and blood creation long before the projectile graphic arrived.
- QuilDER marks the projectile mask `separate=true`; this maps to modern precise-per-frame collision rather than one shared precise mask.
- QuilDER's crab uses a full rectangular 16×16 mask and must remain rectangular rather than being changed to alpha-precise collision.

The converter now maps legacy mask metadata as follows:

- `MANUAL` → modern manual bounding box, preserving coordinates and clamping malformed edge-inclusive values to image bounds.
- `AUTO` → union of nonzero-alpha pixels across generated frames, computed after transparency/chroma conversion.
- `FULL` → complete image bounds.
- `RECTANGLE`, `PRECISE`, `ELLIPSE`, and `DIAMOND` → corresponding modern collision kinds.
- `PRECISE` plus `separate=true` → precise-per-frame collision.

LOWG and QuilDER were regenerated only after their previous deployed builds were copied aside. Both repaired candidates built successfully and completed active keyboard/mouse smoke scenarios without runtime exceptions before replacing the staged versions. Future collision reports should begin with split-XML versus generated-YY mask comparison, not movement-code rewrites.

## Project-specific notes

| Project | Source route | Important repairs and observations |
| --- | --- | --- |
| FightBoyFight | Owner-provided `fightboyfight.gmk` extracted from `fbf.zip` | Split with GMK Splitter and rebuilt with the pinned HTML5 runtime. Replaced the original FMOD extension calls with native WebAudio playback for `bgm_game`. Its browser scenario enters the title screen, starts a game, moves, aims, and fires before capturing gameplay; retain the capture as a freshness check for future builds. |
| POLYFACED | Canonical modern source from `github.com/defacid/POLYFACED`; independently validated against the recovered `data.win` | Prefer the source project for publication. The VM recovery recovered 15 sprites, 8 objects, 2 rooms, 2 sounds, one font, and 21 code entries; the later canonical repository contains 19 sprites, 9 objects, and 4 sounds. This demonstrates why executable recovery should be reconciled with owner source before publishing. The canonical source compiled directly with the pinned HTML5 runtime. |
| Cannonauts | Owner-uploaded Studio VM `data.win` plus external `bgm_stevenogangsta.ogg` | Reconstructed 28 character/effect sprites, 13 objects, 8 rooms, 10 staged sounds, and 4 fonts. A second UTMT background pass recovered `bkg_arena`, `bkg_arenaOld`, `bkg_ground`, and `tiles_arena`; preserved screenshots establish that bright `bkg_arenaOld` is the correct randomized grass source. Modernization replaces `instance_create`, scalar view variables, legacy blend calls, missing Direct3D fog calls, and the unavailable blur shader. The reconstructed splash room clears to black, but the browser build starts in `rm_menu` because the recovered splash transition stalls in HTML5. Studio's surface composition hid normal-Draw bitmap menu text, so the same menu state is redrawn in GameMaker Draw GUI while recovered Draw remains responsible for input and transitions. Explicit modern arrays replace legacy auto-created indexed variables. `instanceCreationOrder` (not merely layer array order) puts `obj_controller` before `obj_camera`, ensuring globals exist during camera creation. Keyboard/mouse slot zero is retained when HTML5 reports zero physical gamepads. Automated input verifies Press Start → Launch → Survival → player join → countdown → `rm_arenaSmall`, with an active player, bots, camera, boundaries, and effects. Root-level `.ogg`/`.mp3` derivatives are staged explicitly. Igor's final `folder` packaging exception remains a known post-compile copy-step failure after valid output is generated. |
| LAR Inventory Example | Direct `lar_inventory_ex.gmk` split | Small pilot for sprite, object, room, and basic GML modernization. |
| BASKET | Original GameMaker: Studio 1 `basket.gmx` framework package | Normalize the GMX resources with `normalize_gmx_project.py`, then generate `modern/basket/` through the shared converter. The original enabled view exactly matched its 1280×720 room; disabling that redundant view during normalization prevents an enabled-camera/no-active-view black canvas. |
| TEMBO | Source recovered from `tembo.zip` | Native game area is compact; site scaling must preserve its aspect ratio. Added an explicit gray frame clear for the intended undefined/default room background. Rebuilt font atlases for title and score text. |
| Priorities | `ACID_64JAM.zip`, internal project `64jam` | Published title differs from internal build name. Uses `bkg_game` and `fnt_hud`; retain the mapping `64jam` -> `priorities`. |
| Unfinished Wasp Game | Direct `unfinishedwaspgame.gmk` split | Mouse-led prototype. Restored the room background as a dedicated full-room background object/layer. |
| Hydra | Direct `hydra.gmk` split | Dedicated star-field background object; animated tiled star overlays; corrected alpha initialization; restored font atlases; display-buffer clear must remain enabled. |
| Gaemmem | Direct `gaemmem.gmk` split | Closely related to Hydra, but the archive does not establish which version came first. Uses the same star-field and font repairs. Preserve it as a distinct prototype. |
| Zombie Infection | Direct `zombieinfection.gmk` split | Room scene is reconstructed from background plus tiles. Uses a dedicated full-room background object and several font atlases. |

Do not infer historical chronology from implementation similarity alone. Relationship claims belong in catalog metadata only when supported by archive evidence.

## Browser validation checklist

Serve the output over HTTP; do not validate only through `file://`.

- The first rendered frame is intentional, not black, white, or transparent.
- No white or black alternating-frame flicker occurs during at least 30 seconds of active play.
- Every texture, particle image, audio worklet, sound, and included file returns HTTP 200.
- The browser console has no uncaught exceptions.
- Text glyphs are recognizable and aligned.
- Background, tiles, sprites, and HUD draw in the expected order.
- Keyboard focus reaches the game after launch and returns to the site after exit.
- Mouse coordinates remain correct after scaling.
- The native aspect ratio is preserved with no unexplained canvas area.
- Audio starts after a user gesture and does not block startup.
- Reload and relaunch start from a clean state.
- Chrome/Edge and Firefox are checked; Safari is checked when available.
- The site labels the correct control set: Mouse only, Keyboard and Mouse, Keyboard only, and/or Gamepad support.

Automated screenshots are useful regression evidence but do not replace active-play testing. Capture more than one point in time to detect frame-buffer and animation defects.

## Failure patterns seen so far

| Symptom | Likely cause | Correct response |
| --- | --- | --- |
| Icons render as squares | Font atlas/glyph metrics mismatch or icon sprites omitted | Inspect whether the original used font glyphs or sprites; repair the corresponding resource rather than substituting generic boxes. |
| Text is missing, clipped, or has wrong spacing | Incorrect font file, range, atlas metrics, or classic line-break semantics | Regenerate the atlas from a pinned font and compare HUD/menu layouts visually. |
| White or black flicker | Display buffer is not deterministically cleared | Set `clearDisplayBuffer: true`, retain the intended background draw, rebuild, and test multiple frames. |
| Large black region below/around game | Room/view/canvas dimensions or embed scaling do not match | Correct the native dimensions and wrapper scale; do not crop blindly. |
| Background is incomplete | Legacy room tiles or background layers were not migrated | Compose/import all room background elements and preserve layer order. |
| Build seems successful but site still has old behavior | Igor left stale shared output or failed after/before asset compilation | Parse logs for `Saving HTML5 file`, verify hashes/timestamps, and stage immediately after each isolated build. |
| Generated game requests missing particle/audio files | Runtime support directories were not staged | Copy only the referenced support files and make network-404 checks part of the release gate. |
| A converted game works directly but not in the site modal | Iframe sizing, focus, sandbox, or launch lifecycle differs | Test through the real catalog launch path, including close/reopen and responsive scaling. |
| Projectiles appear at the top edge or never collide | Regex conversion of `instance_create` broke nested X/Y expressions and misplaced Y as depth | Parse balanced call arguments and emit `instance_create_depth(x, y, 0, object)`; exercise a call containing nested `lengthdir_*` functions. |
| Actors render but walls/scenery are missing | Legacy room tiles were omitted even though instances and the base background were converted | Composite each room's tiled background at its original depth/order and add an active-play screenshot of the room. |
| A menu accepts keys but its text is absent | A recovered surface is composited after normal Draw, hiding font/menu rendering | Keep input and transitions in the recovered event, but redraw the same state in GameMaker Draw GUI after surface composition. Never substitute an HTML overlay. |
| Entering a later menu state produces a black frame and `trying to index variable which is not an array` | Legacy indexed instance/global variables were never explicitly allocated, or their initializer ran after a dependent instance | Allocate arrays with `array_create`, inspect `instanceCreationOrder`, and ensure the controller initializes before camera/menu objects. Reordering only a room layer's `instances` list is insufficient. |
| Keyboard navigation works until the player-join screen | Browser reports zero physical gamepads, so a loop over `gamepad_get_device_count()` never processes keyboard slot zero | Use `max(1, gamepad_get_device_count())` where slot zero doubles as keyboard/mouse; allocate at least four controller slots when the original design assumes four players. |
| Menu works but the next room is black | Do not assume room transition failure; a hidden setup/countdown state or per-frame exception can look identical | Script the complete input sequence with held key events, capture each intermediate state, and fail on `Runtime.exceptionThrown` before changing room order or inventing replacement UI. |
| Player stops before a visible wall, or impact effects appear before a projectile reaches an enemy | Converter replaced authored collision masks with each sprite's full rectangular frame; transparent padding becomes collision area | Preserve `MANUAL`, `AUTO`, and `FULL` bounds, collision shape, and per-frame/separate-mask semantics. Compute AUTO bounds from frame alpha and compare generated `.yy` masks to split XML before rebuilding. |

## Requirements for a reusable conversion tool

The first useful version should be a pipeline coordinator rather than an attempted universal decompiler. It should:

1. Inventory inputs and produce SHA-256 provenance records.
2. Detect `.gm6`, `.gmk`, `.gm81`, archives, and candidate GameMaker executables.
3. Invoke a pinned, format-appropriate extractor without executing the game.
4. Normalize split output into a versioned intermediate manifest.
5. Report unsupported actions, APIs, extensions, DLLs, and ambiguous rewrites before generation.
6. Generate current GameMaker resources without overwriting preservation originals.
7. Make project-specific transforms declarative and auditable.
8. Generate font atlases reproducibly from pinned font files.
9. Reconstruct room layers, tiles, views, draw order, and deterministic clearing.
10. Invoke Igor with isolated cache/temp/output paths and parse partial failures correctly.
11. Discover output dependencies from HTML/JavaScript and refuse a build containing local 404s.
12. Launch browser tests at the native resolution and through the final site embed.
13. Capture console logs, network failures, screenshots at multiple times, and basic input tests. The catalog cover must be a native-canvas crop captured 3–10 seconds after scripted game-start input, not an iframe/modal screenshot or an idle loading frame.
14. Emit a per-project `PORTING.md` plus a machine-readable ledger entry.
15. Stage a release only after explicit review; never publish automatically from raw conversion output.
16. Never remove or downgrade an existing playable build merely because a restoration defect is found. Keep the deployed build intact while repairing and testing a separate generated candidate; replace it only after the candidate passes the relevant route and regression checks.

Suggested manifest fields:

```yaml
project_id: hydra
public_slug: hydra
input:
  path: input/64digits/hydra.gmk
  sha256: ...
  format: gmk
tools:
  splitter: Gmk-Splitter 0.21
  generator_revision: ...
  gamemaker_runtime: 2024.14.4.268
transforms:
  - legacy-gml-modernization
  - font-atlas
  - dedicated-room-background
  - deterministic-display-clear
controls:
  - keyboard
tests:
  network_404s: 0
  console_errors: 0
  timed_screenshots: [1s, 5s, 15s]
review:
  status: pending
  known_deviations: []
```

## Open engineering work

- Replace regex-only GML rewrites with token-aware transformations.
- Define and version the intermediate project manifest.
- Add an isolated Igor wrapper that produces one clean output directory per project.
- Replace the current static dependency scanner with manifest-driven dependency enumeration for every runtime and version.
- Expand the existing browser automation/freshness gate from selected high-risk games to every playable catalog path and version.
- Add visual-difference baselines against trustworthy screenshots or isolated native behavior captures.
- Generate per-project provenance and deviation reports from the same manifest used for conversion.
- Research executable-version detection and safe GM8Decompiler orchestration without conflating decompiled output with original source.

## Studio YYC native recovery boundary

A Studio YYC build has no GML bytecode for UndertaleModTool to decompile, but
that alone is not proof that behavior is unrecoverable. BLEED v0.3 retains named
`gml_Object_*` event strings, instance-variable names, runner-call names, and
native x86 event bodies. Preserve the executable, locate each event-name virtual
address and its code reference, dump the containing function without executing
the binary, and reconstruct GML from the native assignments, branches, and
runner calls. Treat the result as reconstructed source and require isolated
reference-play comparison before publication.

Before beginning native reconstruction, audit every platform download from the
owner's release record. BLEED's Windows package was YYC, while the separately
preserved GM48 macOS package contained a complete Studio 1 VM `game.ios` with
all 22 decompilable event bodies. Platform exports from the same release may use
different compilation modes; the least-lossy surviving one is canonical for
behavior recovery.

BLEED's controller Draw event declared a local display offset but only assigned
it for macOS and `os_unknown`. Current HTML5 can report another OS value, so the
ported event initializes the offset to zero before applying the original
half-pixel override. Browser smoke must fail on undefined-value Draw exceptions
even when the underlying arena appears visible.

The same port exposed removed runtime `tile_add` behavior after the first combat
hit. Translate dynamic decorative tiles to draw-only GameMaker instances which
retain the original background-atlas crop, position, and depth. BLEED's
`obj_blood` is the regression case; its smoke scenario must survive combat long
enough to execute the recovered bleeding branch.

Studio 1's `d3d_set_fog` maps directly to current `gpu_set_fog`. BLEED uses it
to force red damage flashes and a white impact silhouette; leaving the old name
creates an undefined dynamic call in HTML5 and removing it loses authored hit
feedback.

## GM6 import boundary and implemented bridge

Gmk-Splitter 0.21 accepts `.gmk`/`.gm81` but rejects `.gm6`. The implemented
path uses LateralGM 1.8.234 through `tools/GM6ToGMK.java`: load LateralGM's
bundled action libraries, read the GM6 resource tree, set the output project
version to GM8/800, and write a derived `.gmk` under `converted-gm8/`. Gmk-
Splitter can then create the auditable XML/resource tree under `split/`.

Loading action libraries with `LibManager.autoLoad` is required before reading;
without it, action-bearing objects fail during import. The original `.gm6` is
never overwritten, and the derived GMK must not be described as original
source. The bridge successfully imported Fireworks, RPSX/RPS2, both character
tests, LEGO, Organism v03/v04/v05, and the VS action-menu experiment.

One additional GM6 draw incompatibility was found in Organism v03–v05. Those
builds use a solid-white background as the texture for a primitive while
submitting plain vertices with no UV coordinates. Modern HTML5 rendered the
playfield black. The deterministic repair emits an untextured primitive, which
is visually equivalent for the white source texture. A post-start screenshot
of the live ecosystem is the regression check.

## Catalog version-family policy

Multiple archived iterations of the same game are one catalog project, not
separate projects. The project record owns a `versions` list containing a stable
ID, a human-readable label, the staged HTML path, and the native canvas size.
The site presents these as radio buttons directly below the game view and swaps
the iframe and aspect ratio without leaving the project. Preserve and offer each
original source separately. When chronology is not established by dated source
evidence, say so instead of guessing.

Hydra/Gaemmem, RPSX/RPS2, and Organism v03/v04/v05/v08 now use this model.

## Gameplay-cover capture policy

`browser_smoke.mjs` opens the staged build, sends project-specific start and
play input, waits 3–10 seconds, reads the canvas bounding rectangle, and captures
only that rectangle at native resolution. Every playable catalog record needs a
reviewed frame with visible game state. A title/editor frame is acceptable only
for an explicitly archival build whose original source has no playable mode;
the main family cover must use a playable revision. Preserve per-game scenarios
so control changes or black/white draw regressions are caught by later runs.

## Newly exercised resource classes

The Quilder and Snowstorm v2 ports expanded the generator beyond the first
single-room conversions:

- Quilder exercises projectile combat, mouse aiming, weapon switching, and a
  480x240 room.
- Snowstorm v2 exercises ordered multi-room generation, room views, converted
  legacy scripts, a bitmap font, a sound resource, and a tiled background.
- Legacy `sound_play(name)` becomes `audio_play_sound(name, 0, false)`.
- Legacy script bodies are emitted as named modern functions with inferred
  `argument0...argumentN` parameters.
- Runtime `particles` and `sound/worklets` directories must accompany every
  staged GameMaker HTML5 build that requests them.
- Current HTML5 exports also declare the shared `FONT_builtin` atlas. Stage
  `html5game/builtinfonts/FONT_builtin.png` and `FONT_builtin.yy` beside every
  generated build that contains `FONT_builtin`; missing them can present as
  incorrect or absent text even when the JavaScript file itself loads.
- Static link checking is not a gameplay pass. A revised runtime must have a
  newer browser-driven gameplay capture before publication; the static smoke
  gate intentionally fails when that evidence is missing.
- Organism v8's preserved music source is MIDI. GameMaker's HTML5 compiler
  cannot transcode it directly, so the conversion pipeline renders it to WAV
  with pinned `spessasynth_core` and the Windows General MIDI `gm.dls` bank.
  The original MIDI remains unchanged in the preserved GMK. Record the
  renderer version and sound-bank hash because a different bank can sound
  materially different.

Current pinned audio inputs:

- `spessasynth_core` 4.3.22 (locked by `midi-render/package-lock.json`)
- Windows `gm.dls` SHA-256:
  `3229b09b9d7d9f3f4793b0d9b34fe6abc75cfa4a2503c0c90f43ff651ba7f2c0`

## GM5/GM6/GM7 executable recovery

Older executable-only uploads require GM Decompiler 2.1 rather than the GM8
decompiler. `tools/GM567Headless.java` drives its Java UI without launching the
archived game. Always work on a copied executable, record the selected runner
version and UI log, and label the result as reconstructed source rather than an
original project. This route recovered Ghosts Are Scary, both Run Boy Run
uploads, SNG v0.2, and Standaround. The first four yielded GM6 projects;
Standaround yielded a GM7 `.gmk`. The GM6 results then use the documented
LateralGM bridge before splitting.

MiniJam #1 followed a different, lossless route: its `.gmz` is a 7-Zip archive
containing the editable GMX tree and the creator's original HTML5 export. Prefer
that preserved export over recompilation whenever it passes browser testing.

## Cross-game draw-state and room-clear rules

Three shared compatibility defects can make many otherwise-correct ports look
broken:

- A legacy `image_single = n` assignment both selects a subimage and freezes
  animation. Convert it to `image_index = n; image_speed = 0;`. Snowstorm's box
  fragments are the regression case.
- Particle draw events can leave alpha, colour, or blend state behind. Generated
  ordinary sprite draws and explicit Draw events begin from alpha 1, white, and
  `bm_normal`, so unrelated sprites no longer flicker or inherit particle opacity.
- Preserve every room's `backgroundColor` with a Draw Begin clear object. Do not
  rely on the runner's default canvas clear, which produced the recurring
  yellow-white field. Fireworks' dark navy rooms and RPS2/Snowstorm's gray rooms
  are the regression cases.
- Record font substitutions explicitly. Organism declares `rez`, but visual
  review rejected that recovered face for the browser presentation. The port
  deliberately maps its 7px UI and 32px title to Arial, regular or bold according
  to each source font resource. The pinned Rez TTF remains a comparison reference.
- Preserve each legacy object's `depth` by assigning it during Create. Flattening
  all instances onto one modern layer changes draw order: in Organism, swimming
  organisms then overpaint the title and make its letters appear to flicker.
- Fireworks overrides `obj_flame` from legacy depth 1 to depth 0. Equal depth with
  `obj_hill` is unstable in the modern runner; the override keeps rocket exhaust
  above the mountain alongside particles and streams.

After changing any of these rules, regenerate and browser-test every converted
project—not only the game that exposed the bug. Capture multiple live frames for
particle-heavy games to detect intermittent state leakage.

The legacy HTML5 runner's stale/uninitialized card background is exactly
`rgb(255,255,247)`. The site smoke test scans lossless PNG cover masters and
fails when that colour occupies more than one percent of a cover. Treat a hit as
a broken or stale game capture, rebuild the underlying port, exercise gameplay,
and only then replace the cover; never recolour the screenshot cosmetically.

## Untitled S4D Forest Runner repair

1. **Visible symptom:** the candidate reached the forest and scrolled, but the
   black runner was absent or indistinguishable in active-play captures.
2. **Cause:** the converted room mapped the three legacy background slots in
   reverse order, discarded their `-8/0/+8` vertical offsets, used invalid
   assignments to camera getter results, and allowed modern room-layer ordering
   to cover the player draw pass. Repeated checks were initially misleading
   because Chromium reused the prior staged JavaScript.
3. **Repair:** draw the legacy slots as `background2`, `background1`, then
   `background0` with their preserved offsets and corresponding parallax
   variables; use `camera_set_view_pos`; draw the unchanged runner and prompt in
   the final GUI pass at the original 640×240 coordinates; add a subdued local
   backdrop to separate coincident black pixels. Browser validation now disables
   its cache before navigation.
4. **Regression test:** the `s4d` scenario waits through all three original
   splash phases, begins with the required X input, rapidly alternates X/Z, and
   captures during the run. The reviewed uncached frame must show the runner,
   prompt, reordered forest layers, and active noise treatment with no runtime
   exception or same-origin HTTP failure.

## SA-08 Studio VM recovery

1. **Visible symptom:** the catalog offered only the Windows installer, while
   an earlier grid-only screenshot was not backed by any surviving browser
   project or reproducible recovery record.
2. **Cause:** the installer cabinet separated a recoverable Studio 1 VM
   `data.win` from four external Ogg files. The generic Studio converter did not
   yet preserve legacy backgrounds, room tiles, instance creation code, object
   depths, scalar view reads, or `image_single` behavior.
3. **Repair:** statically extract and hash the cabinet; dump the VM data with
   pinned UndertaleModTool; reconstruct backgrounds and static title-room glass,
   attach instance creation code, synthesize missing depth initialization,
   modernize camera/instance/texture functions, translate `image_single`, bind
   numeric music playback to `bgm_theme`, and stage all eight sounds.
4. **Regression test:** the cache-disabled `sa-08` browser scenario breaks the
   opening pod, moves and jumps in the recovered 320×180 room, and captures the
   player, HUD, room artwork, objects, exit, and noise pass while failing on any
   runtime exception or same-origin HTTP error.

## Radiant Meltdown renderer recovery

1. **Visible symptom:** the staged candidate could produce a plausible still,
   but fresh validation found an exception every frame. Once guarded, the raw
   build exposed a white field of oversized pale disks and an absent HUD.
2. **Cause:** current HTML5 rejects dereferencing the legacy `noone` camera
   target during its delayed spawn; the room had no deterministic clear; HUD
   work was not retained in source; and recovered radius/fade arithmetic scaled
   the procedural particles far beyond the preserved gameplay evidence.
3. **Repair:** guard the camera target, add a dark Draw Begin clear, render title,
   survival time, and audio state in Draw GUI, and use a weighted compact radius
   distribution with bounded drift and concentric alpha passes. The Studio
   converter reapplies all repairs when regenerating the project.
4. **Regression test:** the `radiant-meltdown` scenario waits for the procedural
   field, toggles M, and captures the dark active simulation. It fails on runtime
   exceptions or same-origin HTTP errors and must show stable HUD text, chasers,
   tiny colored stars, and occasional radiant points.

## Maintenance rule

When a future conversion needs a manual repair, record all four items here before considering it complete:

1. the visible symptom;
2. the underlying legacy-to-modern incompatibility;
3. the deterministic transformation or project-specific repair; and
4. the regression test that proves the repair remains effective.

## Catalog-wide sampling and persistent-surface fidelity

1. **Visible symptom:** scaled and rotated pixel art looked blurred in many
   otherwise functional ports. Persistent blood, grass, glow, debris, and pause
   surfaces could also begin uncleared or disappear after an HTML5 context loss.
2. **Cause:** generated projects inherited the current runner's texture-filter
   default instead of the archived project's `interpolateColors` setting. The
   Studio metadata exporter likewise omitted its `InterpolatePixels` flag.
   Classic projects also assumed newly allocated surfaces were transparent and
   permanently resident, assumptions the browser runner does not guarantee.
3. **Repair:** read and apply each Classic project's archived interpolation
   setting before room drawing; export and apply Studio's compiled interpolation
   flag; never impose nearest-neighbor filtering on projects that deliberately
   enabled interpolation. Explicitly clear persistent surfaces and recreate
   Quilder and FightBoyFight surfaces before their first draw. Do not use
   `surface_exists` in this pinned HTML5 runtime: it compiles but dispatches as
   an undefined callable; browser context-loss recovery needs a different hook.
4. **Regression test:** `texture-interpolation-audit-2026-09-27.tsv` records the
   source setting and application result. The collision mask reassessment must
   remain at zero mismatches. Browser routes exercise scaled/rotated sprites,
   tiled backgrounds, particles, collisions, Organism primitives, Snowstorm
   debris, and FightBoyFight/Quilder persistent-surface gameplay without runtime
   exceptions or missing runtime assets.

### Catalog pass follow-up findings

- FightBoyFight's bitmap font files survived extraction, but its special
  no-regeneration font path omitted them from the `.yyp` resource list. That
  made `draw_set_font` receive `undefined` and halted the title at a black
  frame. Keep recovered prebuilt fonts in `existing_fonts`, include those
  references in every regenerated manifest, and exercise the title-to-game
  transition after rebuilding.
- Replace FightBoyFight's FMOD lifecycle semantically: Game Start initializes
  the native audio asset/instance state, Room Start stops the previous room's
  audio and starts the loop, and Game End stops all native audio. Merely
  replacing FMOD calls one-for-one can read an uninitialized instance during
  the first Room Start.
- The HTML5 compiler writes shared encoded audio beside the most recent build;
  the staging script must copy each project's declared media. Polyfaced needs
  `bgm_main_menu` and `bgm_the_vein`; a successful JavaScript compile is not a
  successful deployment when either request is missing.
- `gameplay-fidelity-audit-2026-09-27.tsv` inventories collision queries/events,
  explicit transforms, extended/tiled draws, primitives, particle calls, and
  surface users. `collision-mask-audit-2026-09-27.txt` is the corresponding
  exact mask comparison and currently reports zero mismatches.

## BLEED and SA-08 trimmed-frame placement and collision recovery

1. **Visible symptom:** horizontally flipped actors and their shadows jumped to
   the wrong side of their intended pivot in both games. BLEED also allowed the
   player, enemies, attacks, and sushi to overlap without damage or pickup.
   SA-08 could show a second, offset copy of the player while moving. BLEED's
   movement and timers also ran at twice their authored speed.
2. **Cause:** the Studio sprite export discarded texture-page `TargetX` and
   `TargetY` padding, moving every trimmed image to the upper-left of its full
   frame while retaining its original origin. Collision events were emitted
   with legacy numeric filenames and subtypes rather than modern target-object
   names and `collisionObjectId` data. BLEED applied its separate facing sign
   only in Draw, leaving the built-in `image_xscale` and collision transform
   unflipped, and its Studio room's 30 FPS rate was omitted from the modern
   project. SA-08 additionally drew its player from both Step and Draw.
3. **Repair:** export Studio sprite frames with their transparent placement
   padding, preserve the authored origin mode and coordinates, resolve collision
   targets through the recovered object table, emit target-named collision GML
   with modern event metadata, make BLEED's `image_xscale` follow its facing
   sign for both rendering and collision geometry, apply the recovered 30 FPS
   rate before initializing alarms, and remove SA-08's duplicate Step render.
   These transformations live in the exporter/converter and survive regeneration.
   Keep BLEED's recovered `face` sign authoritative in `draw_sprite_ext`, while
   copying it to `image_xscale` only for the collision transform. Using the
   built-in scale as the Draw input can appear stuck after the HTML5 runner
   refreshes that property during animated sprite-resource changes.
   Preserve BLEED's 320×180 logical room as its browser output size rather than
   carrying the archived 640×360 presentation port forward as a new logical
   resolution. The catalog iframe likewise declares 320×180 and may scale that
   whole pixel surface to fit its modal.
   Exempt BLEED's blood `tile_add` calls from the generic removed-tile rewrite,
   convert both player and enemy trails to persistent `obj_blood` decals, and
   place them at depth 999999: immediately in front of the reconstructed bamboo
   background at 1000000, but behind actors at gameplay depth.
4. **Regression test:** `bleed`, `bleed-extended`, and `bleed-collision` exercise
   movement, attacks, debug-spawned enemies/sushi, and contact damage; the last
   reaches BLEED's death state through active collisions. `sa-08` and
   `sa-08-flip` break the pod, move, jump, reverse facing, and capture the room.
   All scenarios fail on runtime exceptions or same-origin HTTP errors.
   `bleed-facing-right` and `bleed-facing-left` additionally capture the same
   idle pose before and after X; the sword and silhouette must visibly mirror.
   `bleed-blood-trail` toggles the recovered debug wound state, moves across the
   room, and must capture a persistent red trail on the 320×180 surface.
   Projects whose recovered setting disables texture filtering must also stage
   their HTML canvas with `image-rendering: pixelated`; GPU texture filtering
   alone does not control browser compositing when a native canvas is enlarged.
   BLEED's health bar uses one shared integer shake offset for its portrait,
   fill, and outline, with the outline exactly one pixel outside the fill.
   Separate random/subpixel offsets create false gaps even with filtering off.

### Studio embedded bitmap-font recovery

1. **Visible symptom:** BLEED's title and HUD text rendered in ordinary Arial,
   losing the narrow, tall lettering visible in the submitted build.
2. **Cause:** the first Studio metadata pass retained only each font's resource
   name and point size. The converter cloned a generic generated Arial atlas,
   even though `data.win` still contained four complete Haettenschweiler bitmap
   regions and the original per-character metrics.
3. **Repair:** `export_studio_fonts.csx` exports each font texture-page item as
   its own padded PNG. `export_studio_metadata.csx` now records the display
   name, character range, glyph rectangle, offset, advance, ascender, and line
   height. `convert_studio_dump.py` builds a non-regenerating modern `GMFont`
   around that atlas and metric table, so the host does not need the original
   typeface installed. BLEED restores `fnt_title` (144), `fnt_die` (80),
   `fnt_text` (18), and `fnt_tiny` (12) as embedded Haettenschweiler resources.
   Older Studio dumps without exported glyph data keep the explicit fallback
   until their atlases are recovered rather than failing regeneration.
4. **Regression test:** capture both BLEED's opening title and active gameplay.
   The title must use the tall condensed `BLEED` lettering, the byline must use
   the same family, and browser loading must not request a system font or throw
   a missing-resource/runtime error.

## Do You Love Us legacy D3D recovery

1. **Visible symptom:** the recovered project compiled, but its browser build
   showed a blank frame and then raised invalid-resource exceptions instead of
   drawing the first-person cavern.
2. **Cause:** current GameMaker HTML5 does not provide the legacy `d3d_*`
   immediate-mode API. The two old background resources were also converted to
   sprites while draw code still addressed their former background names.
3. **Repair:** generate a project-local compatibility script that maps the old
   projection, fog, hidden-surface, floor, and wall calls to modern matrices,
   GPU state, and textured vertex batches. Deterministically rewrite
   `bkg_floor` and `tex_stalagmite` to the generated `spr_bkg_floor` and
   `spr_tex_stalagmite` assets; preserve the dense repeated floor, ceiling,
   pillars, stalagmites, and runner billboards.
4. **Regression test:** the cache-disabled `doyouloveus` scenario alternates Z
   and X to stride, turns, looks, crouches, interacts, and captures the live
   320×240 cavern. It fails on any runtime exception or same-origin HTTP error;
   the reviewed frame must contain textured floor and ceiling, fog, and the
   recovered 3D geometry rather than a blank canvas.
# Historical field notes

These artifact-free notes come from a long-running preservation effort. Local
project names and paths are retained where they clarify a concrete failure,
but the corresponding games, screenshots, fonts, and binaries are deliberately
not included in this repository.
