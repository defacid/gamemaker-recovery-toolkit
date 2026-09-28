# Second-pass collision audit — 2026-09-24

## Policy

No deployed game was removed or downgraded. Existing modern sprite trees and staged browser builds were archived before changes. Candidates replaced staged builds only after successful compilation and browser smoke testing.

Backups:

- `collision-pass-backup/modern-sprites-before-2026-09-24.tar.gz`
- `collision-pass-backup/staged-builds-before-2026-09-24.tar.gz`
- `collision-pass-backup/aliased-staged-builds-before-2026-09-24.tar.gz`

## Scope

The audit compared every collision-relevant sprite referenced by objects in all projects represented by the shared legacy conversion manifest. It compared preserved split XML against modern `.yy` data for:

- bounding-box mode (`AUTO`, `MANUAL`, or `FULL`);
- left, right, top, and bottom bounds;
- rectangle, precise, ellipse, and diamond shape;
- shared versus precise-per-frame masks.

Original browser exports and canonical modern-source projects whose collision resources were never passed through this legacy sprite generator were not rewritten. Cannonauts uses a separate Studio VM reconstruction path and was not changed by this pass.

## Findings

The old generator had left 100 collision-relevant sprites mismatched across 31 converted projects. Most retained the correct broad collision kind but incorrectly used complete image dimensions for legacy AUTO masks. Transparent animation padding therefore became active collision area. Other sprites lost FULL rectangle semantics, authored MANUAL bounds, or precise-per-frame behavior.

The most visible confirmed failures were:

- LOWG `spr_agent`: authored horizontal bounds 4–12 were replaced with 0–15.
- QuilDER `spr_bullet`: the visible 2×2 projectile at x 28–29/y 30–31 was treated as a 64×64 collision area.

## Repairs

`convert_lar_inventory.py` now preserves authored mask metadata and computes AUTO bounds from generated frame alpha. `sprite_alpha_bounds.mjs` and `sprite_alpha_bounds_batch.mjs` provide reproducible single-resource and audit calculations. `audit_collision_masks.py` reports drift and can apply mask-only repairs without regenerating object code or other resources.

Mask-only repairs were applied to the existing modern projects, preserving prior hand-authored compatibility fixes.

## Build and runtime verification

All 31 affected projects compiled successfully. Twenty-five direct staged project IDs and six aliased public builds completed browser smoke scenarios without GameMaker runtime exceptions:

- 64JAM/Priorities
- BASKET
- Character Test
- Defwar
- Do You Love Us candidate
- Character Select Example
- FightBoyFight
- Fireworks
- Gaemmem
- Ghosts Are Scary
- Hydra
- LAR Inventory Example
- LEGO
- Monster
- Organism v04, v05, and v08
- Persistence
- RPS2 and RPSX
- both Run Boy Run revisions
- S4D candidate
- SNG v0.2
- Snowstorm v2
- Standaround
- Unfinished Wasp Game
- Versus
- VS Action Menu
- WEST
- Zombie Infection

LOWG and QuilDER additionally completed active movement/fire scenarios after their focused fixes. The smoke ledger is `collision-smoke-summary-2026-09-24.tsv`; build output is `collision-build-pass-2026-09-24.log`.

The final static postcheck reports **0 mismatched collision-relevant sprites across 0 projects** in `collision-mask-postcheck-2026-09-24.tsv`.

## Limits

A passing automated route establishes that the corrected masks compile, load, and survive representative input without exceptions. It does not prove every contact edge in every room visually. Future gameplay reports should be checked against preserved mask metadata first, and any replacement must continue to follow the backup → candidate → active test → staged replacement sequence.
