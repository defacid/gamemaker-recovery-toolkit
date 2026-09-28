#!/usr/bin/env python3
"""Inventory collision, transform, tiling, and surface risks in modern ports."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

parser = argparse.ArgumentParser(
    description="Inventory collision, transform, tiling, and surface risks in converted GameMaker projects."
)
parser.add_argument(
    "projects_root",
    type=Path,
    help="Directory whose immediate children are modern GameMaker project directories.",
)
args = parser.parse_args()
MODERN = args.projects_root.resolve()

if not MODERN.is_dir():
    parser.error(f"projects root does not exist or is not a directory: {MODERN}")

PATTERNS = {
    "collision_events": r"/Collision_[^/]+\.gml$",
    "collision_queries": r"\b(?:place_meeting|instance_place|collision_(?:point|rectangle|circle|ellipse|line)|position_meeting)\s*\(",
    "draw_ext": r"\bdraw_sprite_ext\s*\(",
    "draw_part": r"\bdraw_sprite_part(?:_ext)?\s*\(",
    "draw_tiled": r"\bdraw_sprite_tiled(?:_ext)?\s*\(",
    "scale_writes": r"\bimage_[xy]scale\s*[+\-*/]?=",
    "rotation_writes": r"\bimage_angle\s*[+\-*/]?=",
    "surface_calls": r"\bsurface_(?:create|set_target|reset_target|free|get_texture|exists)\s*\(",
    "primitive_calls": r"\b(?:draw_primitive|vertex_(?:begin|position|texcoord|submit))",
}

print("project\t" + "\t".join(PATTERNS) + "\trisks")
for project in sorted(path for path in MODERN.iterdir() if path.is_dir()):
    files = list(project.rglob("*.gml"))
    texts = [(path, path.read_text(encoding="utf-8", errors="ignore")) for path in files]
    joined = "\n".join(text for _, text in texts)
    values = {}
    for name, pattern in PATTERNS.items():
        if name == "collision_events":
            values[name] = sum(bool(re.search(pattern, path.as_posix())) for path, _ in texts)
        else:
            values[name] = len(re.findall(pattern, joined))
    risks = []
    if "image_xscale * face" in joined or "image_xscale*face" in joined:
        risks.append("draw-only-facing")
    if "surface_create(" in joined and "surface_exists(" not in joined:
        risks.append("surface-loss-unhandled")
    if joined.count("surface_set_target(") != joined.count("surface_reset_target("):
        risks.append("surface-target-unbalanced")
    if "draw_sprite_tiled" in joined and "gpu_set_texfilter(false)" not in joined and "gpu_set_texfilter(true)" not in joined:
        risks.append("tiling-filter-implicit")
    if values["rotation_writes"] and not values["draw_ext"]:
        risks.append("implicit-rotated-draw")
    if any(values.values()) or risks:
        print(project.name + "\t" + "\t".join(str(values[name]) for name in PATTERNS) + "\t" + ",".join(risks))
