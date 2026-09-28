# Fidelity checklist

## Before conversion

- Hash the artifact and retain its original filename and provenance.
- Identify GameMaker generation, runner type, bytecode version, and editable
  source availability.
- Record room size, view size, output port, room speed, interpolation flags,
  and room order.

## Resource fidelity

- Preserve full sprite canvas dimensions and `TargetX`/`TargetY` padding.
- Preserve origins, bounding boxes, collision kinds, and separate masks.
- Preserve embedded bitmap-font atlases and glyph advances; do not silently
  substitute a system font.
- Preserve background tiling, transparency, alpha, and texture filtering.
- Stage every referenced audio derivative and fail on HTTP 404s.

## Behavior fidelity

- Verify negative `image_xscale` visually and against collision geometry.
- Resolve collision event targets by object identity, not decompiler filenames.
- Preserve room FPS before initializing alarms and speed-dependent state.
- Check draw order for backgrounds, particles, surfaces, HUD, and primitives.
- Explicitly clear newly created surfaces and test browser-context behavior.
- Replace removed tile APIs with persistent draw objects when the tiles carry
  gameplay-visible state such as blood, debris, or damage.

## Browser release gate

- Disable the browser cache.
- Capture runtime exceptions and console errors.
- Fail on same-origin HTTP 4xx/5xx responses.
- Exercise actual input and room transitions.
- Review a gameplay frame, not only a loading or title frame.
- Ensure the capture is newer than the staged runtime.
- Test native resolution and any CSS/iframe scaling separately.
