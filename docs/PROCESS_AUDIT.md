# GameMaker conversion process audit — 2026-09-25

## Outcome

The preservation, recovery, conversion, and browser-validation guidance is now consolidated in `skills/gamemaker-recovery/SKILL.md`. The skill routes future work to the living conversion notes and makes source fidelity, dependency completeness, active-play evidence, and clean release gates explicit requirements.

## Corrections made

- Verified all four pinned recovery archives against their on-disk SHA-256 values and corrected the GM8Decompiler hash in `CONVERSION_NOTES.md`.
- Updated the living notebook date and reconciled its Cannonauts entry with the current project and `PORTING.md`.
- Updated the Cannonauts static freshness gate to follow the current unversioned staged runtime instead of a removed historical bundle.
- Added same-origin HTTP error collection to `browser_smoke.mjs`; an otherwise clean screenshot now fails when a runtime request returns HTTP 4xx/5xx.
- Added and validated a reusable GameMaker recovery skill.
- Syntax-checked the Python converters/auditors and all first-party Node `.mjs` scripts.

## Strengths retained

- preservation originals are immutable and hashed;
- source-bearing inputs are preferred over reconstruction;
- executable recovery is static and version-specific;
- shared converter repairs are deterministic and documented;
- collision metadata has a reproducible audit path;
- Igor partial-success handling requires current log and artifact evidence;
- static staging checks include case-sensitive paths and GameMaker support assets;
- project-specific browser scenarios exercise representative input;
- deployment is separated from candidate repair and review.

## Release blockers found and resolved

These were correctly treated as failures rather than downgraded to warnings, and were resolved on 2026-09-25:

1. Radiant Meltdown's builtin-font, audio-worklet, and particle support assets were staged from the generated GameMaker output.
2. Generated audio derivatives were staged for FightBoyFight, Fireworks, Organism, and Snowstorm.
3. FightBoyFight, BASKET, and Cannonauts active-play evidence was refreshed against the exact current runtimes. The strengthened browser harness reported no runtime exceptions or same-origin HTTP failures.
4. The site was rebuilt, including Alternare at its correct game path. The stale smoke expectation for the former project path was corrected.

## Recommended next automation

Replace the four-entry hard-coded browser freshness list with a versioned machine-readable conversion manifest covering every playable `legacyPath` and every version-family path. Each entry should name its runtime, scenario, capture, native size, controls, mobile status, source hash, tool versions, transforms, and known deviations. The site smoke gate should then derive completeness and freshness requirements from that manifest.

Until that manifest exists, a successful static site build does not establish that every playable catalog entry has current behavioral evidence. Continue using the dated browser/collision ledgers for the wider catalog pass.
