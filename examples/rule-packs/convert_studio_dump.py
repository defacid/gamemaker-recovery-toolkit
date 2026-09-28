#!/usr/bin/env python3
"""Rebuild a current GameMaker project from a deterministic UTMT Studio dump."""

from __future__ import annotations

import json
import re
import shutil
import sys
import uuid
import struct
import zlib
from pathlib import Path

_arguments = sys.argv[:]
sys.argv = [sys.argv[0]]
import convert_lar_inventory as legacy
sys.argv = _arguments

ROOT = Path(__file__).resolve().parent
PROJECT = sys.argv[1] if len(sys.argv) > 1 else "polyfaced"
SOURCE = ROOT / "recovered" / "studio" / PROJECT
DEST = ROOT / "modern" / PROJECT
META = json.loads((SOURCE / "metadata.json").read_text(encoding="utf-8"))


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def ref(kind: str, name: str) -> dict[str, str]:
    return {"name": name, "path": f"{kind}/{name}/{name}.yy"}


def configure_legacy_helpers() -> None:
    legacy.PROJECT = PROJECT
    legacy.SOURCE = SOURCE
    legacy.DEST = DEST
    legacy.CONFIG = {"fonts": tuple(font["name"] for font in META["fonts"])}


def transparent_png(path: Path, width: int, height: int) -> None:
    """Write a deterministic transparent RGBA PNG for an empty legacy sprite."""
    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff)
    rows = b"".join(b"\0" + b"\0\0\0\0" * width for _ in range(height))
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b""))


def sprite_resource(sprite: dict) -> None:
    name = sprite["name"]
    # Resource names may be prefixes of other sprite names (for example,
    # ``spr_player`` and ``spr_player_fall``).  Match only this resource's
    # numeric frame suffix; a glob alone incorrectly merges those animations.
    frame_pattern = re.compile(rf"^{re.escape(name)}_(\d+)\.png$")
    images = sorted(
        (path for path in (SOURCE / "Sprites").glob(f"{name}_*.png")
         if frame_pattern.match(path.name)),
        key=lambda path: int(frame_pattern.match(path.name).group(1)),
    )
    if not images and sprite["frameCount"] == 0:
        # Studio dumps can retain an empty placeholder sprite. Current
        # GameMaker requires one image, so preserve its non-rendering role.
        placeholder = DEST / "generated" / f"{name}_0.png"
        placeholder.parent.mkdir(parents=True, exist_ok=True)
        transparent_png(placeholder, sprite["width"], sprite["height"])
        images = [placeholder]
    elif len(images) != sprite["frameCount"]:
        raise ValueError(f"{name}: expected {sprite['frameCount']} frames, found {len(images)}")
    legacy.sprite(name, images)
    yy_path = DEST / "sprites" / name / f"{name}.yy"
    data = json.loads(yy_path.read_text(encoding="utf-8"))
    data.update({
        "bboxMode": sprite["bboxMode"],
        "bbox_left": sprite["bboxLeft"],
        "bbox_right": sprite["bboxRight"],
        "bbox_top": sprite["bboxTop"],
        "bbox_bottom": sprite["bboxBottom"],
    })
    origin_positions = {
        (0, 0): 0,
        (sprite["width"] // 2, 0): 1,
        (sprite["width"] - 1, 0): 2,
        (0, sprite["height"] // 2): 3,
        (sprite["width"] // 2, sprite["height"] // 2): 4,
        (sprite["width"] - 1, sprite["height"] // 2): 5,
        (0, sprite["height"] - 1): 6,
        (sprite["width"] // 2, sprite["height"] - 1): 7,
        (sprite["width"] - 1, sprite["height"] - 1): 8,
    }
    data["origin"] = origin_positions.get((sprite["originX"], sprite["originY"]), 9)
    data["sequence"]["xorigin"] = sprite["originX"]
    data["sequence"]["yorigin"] = sprite["originY"]
    write_json(yy_path, data)


EVENT_NAMES = {
    0: "Create", 1: "Destroy", 2: "Alarm", 3: "Step", 4: "Collision",
    5: "Keyboard", 6: "Mouse", 7: "Other", 8: "Draw",
    9: "KeyPress", 10: "KeyRelease", 11: "Trigger", 12: "CleanUp",
    13: "Gesture", 14: "PreCreate",
}


def polyfaced_mob_render_fix(target: Path, events: list[dict]) -> None:
    """Give recovered POLYFACED mobs an explicit, state-safe draw path.

    The original object relies on GameMaker's default sprite draw.  In a modern
    HTML5 build that inherits whatever colour/alpha state a previous draw left
    behind, and it contains no recorded hit-flash state.  Draw each mob with a
    known tint and reset the state afterwards; the short timer restores the
    original red hit feedback without affecting its sprite animation.
    """
    events.append({
        "$GMEvent": "v1", "%Name": "", "collisionObjectId": None,
        "eventNum": 0, "eventType": 8, "isDnD": False, "name": "",
        "resourceType": "GMEvent", "resourceVersion": "2.0",
    })
    (target / "Draw_0.gml").write_text(
        "var _tint = hitFlash > 0 ? c_red : c_white;\n"
        "draw_set_alpha(1);\n"
        "draw_sprite_ext(sprite_index, image_index, x, y, image_xscale, image_yscale, image_angle, _tint, image_alpha);\n"
        "draw_set_color(c_white);\n"
        "draw_set_alpha(1);\n",
        encoding="utf-8",
    )


def modernize_studio_code(code: str) -> str:
    # Port the old global view arrays to the camera API used by current runtimes.
    replacements = {
        "view_xview[0]": "camera_get_view_x(view_camera[0])",
        "view_yview[0]": "camera_get_view_y(view_camera[0])",
        "view_wview[0]": "camera_get_view_width(view_camera[0])",
        "view_hview[0]": "camera_get_view_height(view_camera[0])",
        "view_xport[0]": "0", "view_yport[0]": "0",
        "view_wport[0]": "camera_get_view_width(view_camera[0])",
        "view_hport[0]": "camera_get_view_height(view_camera[0])",
        "view_xview": "camera_get_view_x(view_camera[0])",
        "view_yview": "camera_get_view_y(view_camera[0])",
        "view_wview": "camera_get_view_width(view_camera[0])",
        "view_hview": "camera_get_view_height(view_camera[0])",
        "view_xport": "0", "view_yport": "0",
        "view_wport": "camera_get_view_width(view_camera[0])",
        "view_hport": "camera_get_view_height(view_camera[0])",
    }
    for old, new in replacements.items():
        code = code.replace(old, new)
    code = code.replace("d3d_set_fog(", "gpu_set_fog(")
    code = re.sub(r"\binstance_create\(([^,]+),\s*([^,]+),\s*([^\)]+)\)", r"instance_create_depth(\1, \2, 0, \3)", code)
    code = re.sub(
        r"\bimage_single\s*=\s*([^;]+);",
        r"image_index = \1; image_speed = 0;",
        code,
    )
    code = code.replace("background_get_texture(", "sprite_get_texture(")
    code = re.sub(r"sprite_get_texture\((bkg_[A-Za-z0-9_]+)\)", r"sprite_get_texture(\1, 0)", code)
    # BLEED's tiles are persistent blood trails and receive a project-specific
    # object conversion below. Other recovered uses are broken-glass remnants
    # whose visible shards are already spawned as objects.
    if PROJECT != "bleed":
        code = re.sub(r"\btile_add\([^;]+;", "// Removed legacy dynamic tile; object shards preserve the effect.", code)
    if PROJECT == "sa-08":
        code = code.replace("audio_play_music(3, 1);", "audio_play_sound(bgm_theme, 1, true);")
    elif PROJECT == "radiantMeltdown":
        code = code.replace(
            "x += ((target.x - x) / 10);\ny += ((target.y - y) / 10);",
            "if (instance_exists(target))\n{\n    x += ((target.x - x) / 10);\n    y += ((target.y - y) / 10);\n}",
        )
    return code


def background_resource(background: dict) -> None:
    """Represent a Studio 1 background as a one-frame modern sprite."""
    name = background["name"]
    image = SOURCE / "Backgrounds" / f"{name}.png"
    if not image.exists():
        raise FileNotFoundError(f"Missing recovered background: {image}")
    legacy.sprite(name, [image])


def script_resource(name: str) -> None:
    """Emit a modern script from a Studio dump's standalone code entry."""
    code = modernize_studio_code((SOURCE / "CodeEntries" / f"gml_Script_{name}.gml").read_text(encoding="utf-8"))
    argument_numbers = [int(number) for number in re.findall(r"\bargument(\d+)\b", code)]
    parameters = ", ".join(f"argument{index}" for index in range(max(argument_numbers, default=-1) + 1))
    target = DEST / "scripts" / name
    target.mkdir(parents=True, exist_ok=True)
    (target / f"{name}.gml").write_text(f"function {name}({parameters}) {{\n{code.rstrip()}\n}}\n", encoding="utf-8")
    write_json(target / f"{name}.yy", {
        "$GMScript": "v1", "%Name": name, "isCompatibility": False,
        "isDnD": False, "name": name,
        "parent": {"name": PROJECT, "path": f"{PROJECT}.yyp"},
        "resourceType": "GMScript", "resourceVersion": "2.0",
    })


def object_resource(obj: dict) -> None:
    name = obj["name"]
    object_names = [item["name"] for item in META["objects"]]
    target = DEST / "objects" / name
    target.mkdir(parents=True, exist_ok=True)
    events = []
    has_create = any(event["eventType"] == 0 for event in obj["events"])
    for event in obj["events"]:
        event_type = event["eventType"]
        subtype = event["eventSubtype"]
        collision = None
        if event_type == 4:
            # UTMT reports a collision event subtype as the legacy object
            # resource index. Resolve it through the deterministically dumped
            # object table rather than dropping the event.
            if not 0 <= subtype < len(object_names):
                raise ValueError(f"{name}: unknown collision object index {subtype}")
            collision = ref("objects", object_names[subtype])
        events.append({
            "$GMEvent": "v1", "%Name": "", "collisionObjectId": collision,
            "eventNum": 0 if event_type == 4 else subtype,
            "eventType": event_type, "isDnD": False,
            "name": "", "resourceType": "GMEvent", "resourceVersion": "2.0",
        })
        code_entries = [entry for entry in event["code"] if entry]
        if not code_entries:
            # Some UTMT builds leave Action.CodeId unresolved when metadata is
            # exported in a separate pass. The decompiled entries themselves
            # retain this stable, lossless event-derived name.
            inferred = f"gml_Object_{name}_{EVENT_NAMES[event_type]}_{subtype}"
            inferred_path = SOURCE / "CodeEntries" / f"{inferred}.gml"
            if not inferred_path.exists():
                raise ValueError(f"{name}: missing code entry for event {event_type}:{subtype}")
            code_entries = [inferred]
        code = "\n".join(
            (SOURCE / "CodeEntries" / f"{entry}.gml").read_text(encoding="utf-8")
            for entry in code_entries
        )
        code = modernize_studio_code(code)
        if event_type == 0:
            code = f"depth = {obj['depth']};\n" + code
        if PROJECT == "polyfaced" and name == "obj_mob":
            if event_type == 0:
                code += "\n// HTML5 recovery: render hit feedback independently of global draw state.\nhitFlash = 0;\n"
            elif event_type == 3:
                code = code.replace(
                    "var _dir = point_direction(x, y, target.x, target.y);",
                    "hitFlash = max(hitFlash - 1, 0);\n\nvar _dir = point_direction(x, y, target.x, target.y);",
                ).replace(
                    "hp[type] -= _nearestAttack.dmg;",
                    "hp[type] -= _nearestAttack.dmg;\n        hitFlash = 4;",
                )
        event_name = EVENT_NAMES[event_type]
        event_suffix = object_names[subtype] if event_type == 4 else str(subtype)
        (target / f"{event_name}_{event_suffix}.gml").write_text(code.rstrip() + "\n", encoding="utf-8")

    if not has_create:
        events.append({
            "$GMEvent": "v1", "%Name": "", "collisionObjectId": None,
            "eventNum": 0, "eventType": 0, "isDnD": False, "name": "",
            "resourceType": "GMEvent", "resourceVersion": "2.0",
        })
        (target / "Create_0.gml").write_text(f"depth = {obj['depth']};\n", encoding="utf-8")

    if PROJECT == "polyfaced" and name == "obj_mob":
        polyfaced_mob_render_fix(target, events)

    data = {
        "$GMObject": "", "%Name": name, "eventList": events, "managed": True,
        "name": name, "overriddenProperties": [],
        "parent": {"name": PROJECT, "path": f"{PROJECT}.yyp"},
        "parentObjectId": ref("objects", obj["parent"]) if obj["parent"] else None,
        "persistent": obj["persistent"], "physicsAngularDamping": 0.1,
        "physicsDensity": 0.5, "physicsFriction": 0.2, "physicsGroup": 1,
        "physicsKinematic": False, "physicsLinearDamping": 0.1,
        "physicsObject": False, "physicsRestitution": 0.1,
        "physicsSensor": False, "physicsShape": 1, "physicsShapePoints": [],
        "physicsStartAwake": True, "properties": [], "resourceType": "GMObject",
        "resourceVersion": "2.0", "solid": obj["solid"],
        "spriteId": ref("sprites", obj["sprite"]) if obj["sprite"] else None,
        "spriteMaskId": ref("sprites", obj["mask"]) if obj["mask"] else None,
        "visible": obj["visible"],
    }
    write_json(target / f"{name}.yy", data)


def sound_resource(sound: dict) -> None:
    name = sound["name"]
    matches = list((SOURCE / "Sounds").glob(f"{name}.*"))
    if not matches:
        # Non-embedded Studio sounds are distributed beside data.win instead
        # of inside its AUDO chunk. Preserve those creator-uploaded files.
        package_root = ROOT / "recovered" / "package-audit"
        matches = [path for path in package_root.rglob(f"{name}.*") if path.is_file()]
    if len(matches) != 1:
        raise FileNotFoundError(f"Expected one recovered sound for {name}, found {len(matches)}")
    source = matches[0]
    target = DEST / "sounds" / name
    target.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target / source.name)
    write_json(target / f"{name}.yy", {
        "$GMSound": "", "%Name": name,
        "audioGroupId": {"name": "audiogroup_default", "path": "audiogroups/audiogroup_default"},
        "bitDepth": 1, "bitRate": 128, "compression": 0, "conversionMode": 0,
        "duration": 0.0, "name": name,
        "parent": {"name": PROJECT, "path": f"{PROJECT}.yyp"},
        "preload": True, "resourceType": "GMSound", "resourceVersion": "2.0",
        "sampleRate": 44100, "soundFile": source.name, "type": 0,
        "volume": sound["volume"],
    })


def font_resource(font: dict) -> None:
    """Create a modern font resource around the recovered embedded bitmap atlas."""
    name = font["name"]
    source_dir = ROOT / "modern" / "rps2" / "fonts" / "fnt_name"
    target = DEST / "fonts" / name
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(source_dir, target)
    source_yy = target / "fnt_name.yy"
    data = json.loads(source_yy.read_text(encoding="utf-8"))
    source_yy.unlink()
    data["%Name"] = name
    data["name"] = name
    data["size"] = font["size"]
    data["bold"] = font["bold"]
    data["italic"] = font["italic"]
    data["styleName"] = "Bold" if font["bold"] else "Regular"
    data["parent"] = {"name": PROJECT, "path": f"{PROJECT}.yyp"}
    old_png = target / "fnt_name.png"
    recovered_png = SOURCE / "Fonts" / f"{name}.png"
    if recovered_png.exists() and font.get("glyphs"):
        data["fontName"] = font["displayName"]
        data["first"] = font.get("rangeStart", 32)
        data["last"] = font.get("rangeEnd", 127)
        data["ranges"] = [{"lower": data["first"], "upper": data["last"]}]
        data["ascender"] = font.get("ascender", 0)
        data["ascenderOffset"] = font.get("ascenderOffset", 0)
        data["lineHeight"] = font.get("lineHeight") or max(
            glyph["h"] for glyph in font["glyphs"]
        )
        data["glyphs"] = {
            str(glyph["character"]): glyph for glyph in font["glyphs"]
        }
        data["canGenerateBitmap"] = False
        data["maintainGms1Font"] = True
        shutil.copy2(recovered_png, target / f"{name}.png")
        old_png.unlink(missing_ok=True)
    else:
        # Older dumps made before glyph export retain the previous safe
        # generated fallback until their embedded atlas is exported.
        data["fontName"] = "Arial"
        old_png.rename(target / f"{name}.png")
    write_json(target / f"{name}.yy", data)


def room_resource(room: dict) -> None:
    name = room["name"]
    instances = []
    order = []
    for old in room["instances"]:
        instance_name = f"inst_{old['id']:08X}"
        creation_code = old.get("creationCode")
        instances.append({
            "$GMRInstance": "v4", "%Name": instance_name, "colour": 4294967295,
            "frozen": False, "hasCreationCode": bool(creation_code), "ignore": False,
            "imageIndex": old["imageIndex"], "imageSpeed": old["imageSpeed"],
            "inheritCode": False, "inheritedItemId": None,
            "inheritItemSettings": False, "isDnd": False, "name": instance_name,
            "objectId": ref("objects", old["object"]), "properties": [],
            "resourceType": "GMRInstance", "resourceVersion": "2.0",
            "rotation": old["rotation"], "scaleX": old["scaleX"],
            "scaleY": old["scaleY"], "x": old["x"], "y": old["y"],
        })
        if creation_code:
            source = SOURCE / "CodeEntries" / f"{creation_code}.gml"
            code = modernize_studio_code(source.read_text(encoding="utf-8"))
            target = DEST / "rooms" / name / f"InstanceCreationCode_{instance_name}.gml"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(code.rstrip() + "\n", encoding="utf-8")
        order.append({"name": instance_name, "path": f"rooms/{name}/{name}.yy"})

    renderer_name = f"obj_render_{name}"
    render_target = DEST / "objects" / renderer_name
    render_target.mkdir(parents=True, exist_ok=True)
    render_lines = []
    if "interpolatePixels" in META:
        render_lines.append(f"gpu_set_texfilter({'true' if META['interpolatePixels'] else 'false'});")
    render_lines.extend(["draw_set_alpha(1);", "draw_set_color(c_white);"])
    for background in room.get("backgrounds", []):
        if not background["enabled"] or not background["background"]:
            continue
        resource = background["background"]
        x, y = background["x"], background["y"]
        if background["stretch"]:
            render_lines.append(f"draw_sprite_stretched({resource}, 0, 0, 0, room_width, room_height);")
        elif background["tileX"] or background["tileY"]:
            render_lines.append(f"draw_sprite_tiled({resource}, 0, {x}, {y});")
        else:
            render_lines.append(f"draw_sprite({resource}, 0, {x}, {y});")
    for tile in room.get("tiles", []):
        render_lines.append(
            f"draw_sprite_part_ext({tile['background']}, 0, {tile['sourceX']}, {tile['sourceY']}, "
            f"{tile['width']}, {tile['height']}, {tile['x']}, {tile['y']}, {tile['scaleX']}, {tile['scaleY']}, c_white, 1);"
        )
    (render_target / "Draw_0.gml").write_text("\n".join(render_lines) + "\n", encoding="utf-8")
    write_json(render_target / f"{renderer_name}.yy", {
        "$GMObject": "", "%Name": renderer_name,
        "eventList": [{"$GMEvent": "v1", "%Name": "", "collisionObjectId": None,
            "eventNum": 0, "eventType": 8, "isDnD": False, "name": "",
            "resourceType": "GMEvent", "resourceVersion": "2.0"}],
        "managed": True, "name": renderer_name, "overriddenProperties": [],
        "parent": {"name": PROJECT, "path": f"{PROJECT}.yyp"}, "parentObjectId": None,
        "persistent": False, "physicsAngularDamping": 0.1, "physicsDensity": 0.5,
        "physicsFriction": 0.2, "physicsGroup": 1, "physicsKinematic": False,
        "physicsLinearDamping": 0.1, "physicsObject": False, "physicsRestitution": 0.1,
        "physicsSensor": False, "physicsShape": 1, "physicsShapePoints": [],
        "physicsStartAwake": True, "properties": [], "resourceType": "GMObject",
        "resourceVersion": "2.0", "solid": False, "spriteId": None,
        "spriteMaskId": None, "visible": True,
    })
    render_instance = {
        "$GMRInstance": "v4", "%Name": "inst_ROOM_RENDER", "colour": 4294967295,
        "frozen": False, "hasCreationCode": False, "ignore": False, "imageIndex": 0,
        "imageSpeed": 0.0, "inheritCode": False, "inheritedItemId": None,
        "inheritItemSettings": False, "isDnd": False, "name": "inst_ROOM_RENDER",
        "objectId": ref("objects", renderer_name), "properties": [], "resourceType": "GMRInstance",
        "resourceVersion": "2.0", "rotation": 0.0, "scaleX": 1.0, "scaleY": 1.0,
        "x": 0.0, "y": 0.0,
    }
    order.insert(0, {"name": "inst_ROOM_RENDER", "path": f"rooms/{name}/{name}.yy"})
    layers = [{
        "$GMRInstanceLayer": "", "%Name": "Recovered Background", "depth": 1000000,
        "effectEnabled": True, "effectType": None, "gridX": 16, "gridY": 16,
        "hierarchyFrozen": False, "inheritLayerDepth": False, "inheritLayerSettings": False,
        "inheritSubLayers": True, "inheritVisibility": True, "instances": [render_instance],
        "layers": [], "name": "Recovered Background", "properties": [],
        "resourceType": "GMRInstanceLayer", "resourceVersion": "2.0",
        "userdefinedDepth": True, "visible": True,
    }, {
        "$GMRInstanceLayer": "", "%Name": "Instances", "depth": 0,
        "effectEnabled": True, "effectType": None, "gridX": 16, "gridY": 16,
        "hierarchyFrozen": False, "inheritLayerDepth": False,
        "inheritLayerSettings": False, "inheritSubLayers": True,
        "inheritVisibility": True, "instances": instances, "layers": [],
        "name": "Instances", "properties": [], "resourceType": "GMRInstanceLayer",
        "resourceVersion": "2.0", "userdefinedDepth": False, "visible": True,
    }]
    views = [{
        "hborder": view["borderX"], "hport": view["height"] if PROJECT == "bleed" else view["portHeight"],
        "hspeed": view["speedX"], "hview": view["height"], "inherit": False,
        "objectId": ref("objects", view["object"]) if view["object"] else None,
        "vborder": view["borderY"], "visible": view["enabled"],
        "vspeed": view["speedY"], "wport": view["width"] if PROJECT == "bleed" else view["portWidth"],
        "wview": view["width"], "xport": view["portX"], "xview": view["x"],
        "yport": view["portY"], "yview": view["y"],
    } for view in room["views"]]
    write_json(DEST / "rooms" / name / f"{name}.yy", {
        "$GMRoom": "v1", "%Name": name, "creationCodeFile": "",
        "inheritCode": False, "inheritCreationOrder": False, "inheritLayers": False,
        "instanceCreationOrder": order, "isDnd": False, "layers": layers,
        "name": name, "parent": {"name": PROJECT, "path": f"{PROJECT}.yyp"},
        "parentRoom": None, "physicsSettings": {"inheritPhysicsSettings": False,
            "PhysicsWorld": False, "PhysicsWorldGravityX": 0.0,
            "PhysicsWorldGravityY": 10.0, "PhysicsWorldPixToMetres": 0.1},
        "resourceType": "GMRoom", "resourceVersion": "2.0",
        "roomSettings": {"Height": room["height"], "inheritRoomSettings": False,
            "persistent": room["persistent"], "Width": room["width"]},
        "sequenceId": None, "views": views,
        "viewSettings": {"clearDisplayBuffer": True, "clearViewBackground": False,
            "enableViews": any(view["enabled"] for view in room["views"]),
            "inheritViewSettings": False}, "volume": 1.0,
    })


def alternare_render_resources() -> list[dict]:
    """Restore Alternare's Studio backgrounds and removed legacy tile fields."""
    if PROJECT != "acidF4D_2014_debug":
        return []
    values = []
    for name, filename in (("bkg_basic", "bkg_basic.png"), ("bkg_tiles", "bkg_tiles_0.png")):
        image = SOURCE / "Backgrounds" / filename
        if not image.exists():
            raise FileNotFoundError(f"Alternare background export missing: {image}")
        sprite_name = f"spr_{name}"
        legacy.sprite(sprite_name, [image])
        values.append({"name": sprite_name})
    return values


def alternare_render_fix() -> None:
    if PROJECT != "acidF4D_2014_debug":
        return
    controller = DEST / "objects" / "obj_controller"
    (controller / "Create_0.gml").write_text("""depth = 10000;
world_color = make_color_rgb(random(255), random(255), random(255));
fade = 1;
max_tiles = 200 + random(300);
tile_color = make_color_rgb(random(255), random(255), random(255));
for (i = 0; i < max_tiles; i++) {
    tile_x[i] = random(room_width); tile_y[i] = random(room_height);
    tile_xscale[i] = 1 + random(2); tile_yscale[i] = 1 + random(2);
}
max_flowers = random(100);
flower_color = make_color_rgb(random(255), random(255), random(255));
for (i = 0; i < max_flowers; i++) {
    flower_x[i] = random(room_width); flower_y[i] = random(room_height);
    flower_scale[i] = 0.1 + random(0.25);
}
max_plants = random(150);
plant_color = make_color_rgb(random(255), random(255), random(255));
plant_type = round(random(sprite_get_number(spr_trees) - 1));
leaf_type = round(random(sprite_get_number(spr_leaves) - 1));
leaf_color = make_color_rgb(random(255), random(255), random(255));
for (i = 0; i < max_plants; i++) {
    var plant_id = instance_create_depth((room_width / 2) + lengthdir_x(60 + random(room_width / 2), random(360)), (room_height / 2) + lengthdir_y(60 + random(room_height / 2), random(360)), 0, obj_plant);
    plant_id.image_index = plant_type; plant_id.image_speed = 0;
    plant_id.image_blend = plant_color;
    plant_id.image_xscale = 0.5 + random(0.5); plant_id.image_yscale = 0.5 + random(1);
    plant_id.leaf_type = leaf_type; plant_id.leaf_color = leaf_color;
}
""", encoding="utf-8")
    (controller / "Draw_0.gml").write_text("""draw_clear(c_black);
draw_sprite_tiled_ext(spr_bkg_basic, 0, 0, 0, 1, 1, world_color, 1);
for (i = 0; i < max_tiles; i++)
    draw_sprite_ext(spr_bkg_tiles, 0, tile_x[i], tile_y[i], tile_xscale[i], tile_yscale[i], 0, tile_color, 0.15);
for (i = 0; i < max_flowers; i++)
    draw_sprite_ext(spr_bkg_tiles, 0, flower_x[i], flower_y[i], flower_scale[i], flower_scale[i], 0, flower_color, 1);
if (fade > 0) fade -= 0.01;
draw_set_color(c_black); draw_set_alpha(fade);
draw_rectangle(camera_get_view_x(view_camera[0]) - 8, camera_get_view_y(view_camera[0]) - 8, camera_get_view_x(view_camera[0]) + camera_get_view_width(view_camera[0]) + 8, camera_get_view_y(view_camera[0]) + camera_get_view_height(view_camera[0]) + 8, false);
draw_set_alpha(1); draw_set_color(c_white);
""", encoding="utf-8")
    menu_draw = DEST / "objects" / "obj_menu_controller" / "Draw_0.gml"
    menu_draw.write_text("draw_clear(c_black);\n" + menu_draw.read_text(encoding="utf-8"), encoding="utf-8")


def radiant_render_fix() -> None:
    """Preserve the reviewed compact dark-field presentation."""
    if PROJECT != "radiantMeltdown":
        return
    camera = DEST / "objects" / "obj_camera"
    create = camera / "Create_0.gml"
    create.write_text(create.read_text(encoding="utf-8").replace(
        "random_set_seed(current_day * current_hour * current_minute * current_second);",
        "random_set_seed(current_day * current_hour * current_minute * current_second);\n"
        "depth = -10000;\nsurvival_frames = 0;",
    ), encoding="utf-8")
    draw = camera / "Draw_0.gml"
    draw.write_text(draw.read_text(encoding="utf-8").replace(
        "audio_master_gain(global.gain);",
        "audio_master_gain(global.gain);\nsurvival_frames += 1;",
    ), encoding="utf-8")
    (camera / "Draw_64.gml").write_text(
        "draw_set_alpha(1); draw_set_color(c_white);\n"
        "draw_text(8, 6, \"RADIANT - MELTDOWN\");\n"
        "draw_text(8, 18, \"SURVIVAL \" + string_format(survival_frames / room_speed, 1, 1));\n"
        "draw_text(8, 30, \"AUDIO FLAG \" + (global.volume > 0 ? \"ON\" : \"OFF\"));\n",
        encoding="utf-8",
    )
    (camera / "Draw_72.gml").write_text("draw_clear(make_color_rgb(10, 3, 24));\n", encoding="utf-8")
    camera_yy = camera / "obj_camera.yy"
    data = json.loads(camera_yy.read_text(encoding="utf-8"))
    data["eventList"].extend([{
        "$GMEvent": "v1", "%Name": "", "collisionObjectId": None,
        "eventNum": 64, "eventType": 8, "isDnD": False, "name": "",
        "resourceType": "GMEvent", "resourceVersion": "2.0",
    }, {
        "$GMEvent": "v1", "%Name": "", "collisionObjectId": None,
        "eventNum": 72, "eventType": 8, "isDnD": False, "name": "",
        "resourceType": "GMEvent", "resourceVersion": "2.0",
    }])
    write_json(camera_yy, data)

    orb_create = DEST / "objects" / "obj_orb" / "Create_0.gml"
    orb_create.write_text(orb_create.read_text(encoding="utf-8")
        .replace("height = 64;", "height = 8 + random(24);")
        .replace("radius = 64 + random(128);", "radius = 1 + random(2);\nif (random(1) < 0.02) radius = 7 + random(5);"), encoding="utf-8")
    orb_draw = DEST / "objects" / "obj_orb" / "Draw_0.gml"
    orb_draw.write_text(orb_draw.read_text(encoding="utf-8")
        .replace("alpha = (1 - alpha) / 20;", "alpha += (1 - alpha) / 20;")
        .replace("radius += (6 - random(12));", "radius += (0.4 - random(0.8));")
        .replace("draw_set_alpha(alpha);\ndraw_set_color(_color);\ndraw_circle(_x, _y - height, rad * _scale, 0);",
            "draw_set_color(_color);\n"
            "draw_set_alpha(alpha * 0.08); draw_circle(_x, _y - height, rad * _scale * 2.2, false);\n"
            "draw_set_alpha(alpha * 0.18); draw_circle(_x, _y - height, rad * _scale * 1.5, false);\n"
            "draw_set_alpha(alpha * 0.65); draw_circle(_x, _y - height, max(0.75, rad * _scale * 0.45), false);\n"
            "draw_set_alpha(1); draw_set_color(c_white);"), encoding="utf-8")
    chaser_draw = DEST / "objects" / "obj_chaser" / "Draw_0.gml"
    chaser_draw.write_text(chaser_draw.read_text(encoding="utf-8").replace(
        "draw_set_alpha(alpha);\ndraw_set_color(c_white);\ndraw_circle(x, y, 8, 0);",
        "draw_set_alpha(alpha * 0.12); draw_set_color(c_aqua); draw_circle(x, y, 15, false);\n"
        "draw_set_alpha(alpha * 0.8); draw_set_color(c_white); draw_circle(x, y, 8, false);\n"
        "draw_set_alpha(1); draw_set_color(c_white);",
    ), encoding="utf-8")


def bleed_recovery_fixes() -> None:
    """Replace YYC-era numeric sprite IDs with stable resource references."""
    if PROJECT != "bleed":
        return
    for object_name in ("obj_controller", "obj_player", "obj_enemy", "obj_sushi"):
        draw_path = DEST / "objects" / object_name / "Draw_0.gml"
        code = draw_path.read_text(encoding="utf-8")
        code = code.replace("var displayOffset;", "var displayOffset = 0;")
        draw_path.write_text(code, encoding="utf-8")
    controller_draw = DEST / "objects" / "obj_controller" / "Draw_0.gml"
    code = controller_draw.read_text(encoding="utf-8")
    code = code.replace("spr = 4;", "spr = spr_ninja_injured;")
    code = code.replace("spr = 5;", "spr = spr_ninja_die;")
    code = code.replace("spr = 0;", "spr = spr_ninja_stand;")
    bar_start = code.index("draw_set_alpha(1 - titleAlpha);")
    bar_end = code.index("draw_set_halign(fa_center);")
    code = code[:bar_start] + """var hudShakeX = round(random(shake));
var hudShakeY = round(random(shake));
var barLeft = camera_get_view_x(view_camera[0]) + 28 + hudShakeX;
var barTop = camera_get_view_y(view_camera[0]) + camera_get_view_height(view_camera[0]) - 20 + vOff + hudShakeY;
var barRight = barLeft + (camera_get_view_width(view_camera[0]) * 0.75 * obj_player.maxHp);
var barBottom = barTop + 8;
draw_set_alpha(1 - titleAlpha);
draw_set_color(c_black);
draw_rectangle(barLeft, barTop, barRight, barBottom, false);
if (obj_player.hp > 0)
{
    draw_set_color(obj_player.healthColor);
    draw_rectangle(barLeft, barTop, barLeft + (camera_get_view_width(view_camera[0]) * 0.75 * obj_player.hp), barBottom, false);
}
draw_set_color(c_white);
draw_rectangle(barLeft - 1, barTop - 1, barRight + 1, barBottom + 1, true);
if (obj_player.hp > 0)
    obj_player.hudSpeed += (0.2 - (0.15 * obj_player.hurt));
else
    obj_player.hudSpeed = obj_player.attackCount;
var spr;
if (obj_player.hurt)
    spr = obj_player.hp > 0 ? spr_ninja_injured : spr_ninja_die;
else
    spr = spr_ninja_stand;
draw_sprite_ext(spr, obj_player.hudSpeed, camera_get_view_x(view_camera[0]) + 24 + hudShakeX, camera_get_view_y(view_camera[0]) + camera_get_view_height(view_camera[0]) - 32 + vOff + hudShakeY, 3 * obj_player.face, 3, obj_player.image_angle, obj_player.image_blend, 1 - titleAlpha);
""" + code[bar_end:]
    controller_draw.write_text(code, encoding="utf-8")

    # Studio 1 stored the room rate on the room. Current GameMaker uses a
    # project-wide rate and otherwise runs this reconstruction at 60 FPS,
    # doubling every per-step movement and timer from the authored 30 FPS.
    controller_create = DEST / "objects" / "obj_controller" / "Create_0.gml"
    code = controller_create.read_text(encoding="utf-8")
    room_speed = META["rooms"][0]["speed"]
    controller_create.write_text(
        f"game_set_speed({room_speed}, gamespeed_fps);\n" + code,
        encoding="utf-8",
    )

    # Keep the recovered `face` sign authoritative for drawing, and mirror the
    # built-in transform separately for collision geometry. Current HTML5 can
    # refresh image_xscale while changing animated sprite resources; drawing
    # directly with `face` guarantees that the X-key turn is visible while the
    # matching built-in scale keeps the collision mask on the same origin.
    for object_name in ("obj_player", "obj_enemy"):
        step_path = DEST / "objects" / object_name / "Step_0.gml"
        step_code = step_path.read_text(encoding="utf-8")
        step_path.write_text(step_code.rstrip() + "\nimage_xscale = face;\n", encoding="utf-8")

        draw_path = DEST / "objects" / object_name / "Draw_0.gml"
        draw_code = draw_path.read_text(encoding="utf-8")
        draw_code = draw_code.replace("image_xscale * face", "face")
        draw_path.write_text(draw_code, encoding="utf-8")

    # Current GameMaker removed the classic dynamic tile API. Preserve each
    # blood decal as a tiny persistent draw-only instance using the same atlas
    # source rectangle and depth as the recovered tile_add call.
    blood_target = DEST / "objects" / "obj_blood"
    blood_target.mkdir(parents=True, exist_ok=True)
    template = json.loads((DEST / "objects" / "obj_flash" / "obj_flash.yy").read_text(encoding="utf-8"))
    template["%Name"] = "obj_blood"
    template["name"] = "obj_blood"
    template["eventList"] = [{
        "$GMEvent": "v1", "%Name": "", "collisionObjectId": None,
        "eventNum": 0, "eventType": 8, "isDnD": False, "name": "",
        "resourceType": "GMEvent", "resourceVersion": "2.0",
    }]
    write_json(blood_target / "obj_blood.yy", template)
    (blood_target / "Draw_0.gml").write_text(
        "draw_set_alpha(1); draw_set_color(c_white);\n"
        "draw_sprite_part(bkg_blood, 0, source_x, source_y, 16, 16, x, y);\n",
        encoding="utf-8",
    )
    for actor_name in ("obj_player", "obj_enemy"):
        actor_step = DEST / "objects" / actor_name / "Step_0.gml"
        code = actor_step.read_text(encoding="utf-8")
        code = code.replace(
            "tile_add(bkg_blood, irandom(3) * 16, irandom(1) * 16, 16, 16, (x - 8) + (pool * (1 - random(2))), (y - 3) + ((pool * (1 - random(2))) / 2), 1000001);",
            "var _blood = instance_create_depth((x - 8) + (pool * (1 - random(2))), (y - 3) + ((pool * (1 - random(2))) / 2), 999999, obj_blood);\n"
            "        _blood.source_x = irandom(3) * 16;\n"
            "        _blood.source_y = irandom(1) * 16;",
        )
        actor_step.write_text(code, encoding="utf-8")


def sa08_render_fixes() -> None:
    """Keep player rendering in Draw and preserve every authored sprite origin."""
    if PROJECT != "sa-08":
        return
    player_step = DEST / "objects" / "obj_player" / "Step_0.gml"
    code = player_step.read_text(encoding="utf-8")
    code = code.replace(
        "draw_sprite_ext(sprite_index, img, x, y, 1 * face, 1, 0, c_white, 1);\n",
        "",
    )
    player_step.write_text(code, encoding="utf-8")


def main() -> None:
    configure_legacy_helpers()
    if DEST.exists():
        shutil.rmtree(DEST)
    DEST.mkdir(parents=True)
    template = json.loads((ROOT / "modern" / "tembo" / "tembo.yyp").read_text(encoding="utf-8"))
    template["%Name"] = PROJECT
    template["name"] = PROJECT
    template["resources"] = []
    template["RoomOrderNodes"] = []

    for resource in META["sprites"]:
        sprite_resource(resource)
    for resource in META.get("backgrounds", []):
        background_resource(resource)
    extra_sprites = alternare_render_resources()
    # The metadata format does not enumerate Studio scripts, but their dumped
    # code entries are named deterministically.  Omitting them leaves calls as
    # unresolved dynamic functions that fail only after the loader completes.
    script_names = sorted(
        path.stem.removeprefix("gml_Script_")
        for path in (SOURCE / "CodeEntries").glob("gml_Script_*.gml")
        if not path.stem.startswith("gml_Script_gmw")
    )
    for name in script_names:
        script_resource(name)
    for resource in META["objects"]:
        object_resource(resource)
    for resource in META["fonts"]:
        font_resource(resource)
    for resource in META["sounds"]:
        sound_resource(resource)
    for resource in META["rooms"]:
        room_resource(resource)
    alternare_render_fix()
    radiant_render_fix()
    bleed_recovery_fixes()
    sa08_render_fixes()

    resources = []
    for kind, values in (
        ("sprites", META["sprites"] + META.get("backgrounds", [])), ("scripts", [{"name": name} for name in script_names]),
        ("objects", META["objects"]), ("fonts", META["fonts"]),
        ("sounds", META["sounds"]), ("rooms", META["rooms"]),
    ):
        resources.extend({"id": ref(kind, item["name"])} for item in values)
    resources.extend({"id": ref("sprites", item["name"])} for item in extra_sprites)
    resources.extend({"id": ref("objects", f"obj_render_{room['name']}")} for room in META["rooms"])
    if PROJECT == "bleed":
        resources.append({"id": ref("objects", "obj_blood")})
    template["resources"] = resources
    template["RoomOrderNodes"] = [
        {"roomId": ref("rooms", room["name"])} for room in META["rooms"]
    ]
    write_json(DEST / f"{PROJECT}.yyp", template)
    print(f"Generated Studio recovery project: {DEST / f'{PROJECT}.yyp'}")


if __name__ == "__main__":
    main()
