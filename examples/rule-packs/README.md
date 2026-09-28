# Reference rule packs

These are preserved examples of deterministic conversion logic from a real
recovery effort. They demonstrate how project-specific knowledge can be kept
in code instead of being lost in hand edits.

They are not portable one-command converters. Their project names, source
paths, runtime locations, Windows font paths, and resource selections describe
the workspace in which they were developed. Copy the relevant patterns into a
new rule pack and replace those assumptions for your own authorized material.

Useful patterns include:

- mapping legacy resources to generated modern projects;
- applying repeatable object, room, font, and sprite corrections;
- preserving repair logic across regeneration;
- separating source extraction from compatibility fixes;
- treating a rebuild as data plus declared transformations.

Do not add recovered assets, executables, licensed fonts, runtime files, or
third-party game data to this directory.
