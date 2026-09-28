#!/usr/bin/env python3
"""Normalize a Studio 1 GMX project for the legacy-to-modern converter."""

from __future__ import annotations

import argparse
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

EVENTS = {0: "CREATE", 1: "DESTROY", 2: "ALARM", 3: "STEP", 4: "COLLISION", 5: "KEYBOARD", 6: "MOUSE", 7: "OTHER", 8: "DRAW", 9: "KEYPRESS", 10: "KEYRELEASE"}
SOURCE: Path
DEST: Path


def write_xml(path: Path, root: ET.Element) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ET.indent(root, space="  ")
    ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)


def text(parent: ET.Element, tag: str, value: object) -> ET.Element:
    item = ET.SubElement(parent, tag)
    item.text = str(value)
    return item


def normalize_sprites() -> None:
    for source in sorted((SOURCE / "sprites").glob("*.sprite.gmx")):
        name = source.name.removesuffix(".sprite.gmx")
        old = ET.parse(source).getroot()
        root = ET.Element("sprite", {"id": "0"})
        ET.SubElement(root, "origin", {"x": old.findtext("xorig", "0"), "y": old.findtext("yorigin", "0")})
        text(root, "preload", "true")
        text(root, "smoothEdges", "false")
        text(root, "transparent", "false")
        write_xml(DEST / "Sprites" / f"{name}.xml", root)
        images = DEST / "Sprites" / f"{name}.images"
        images.mkdir(parents=True, exist_ok=True)
        for index, frame in enumerate(old.findall("./frames/frame")):
            relative = (frame.text or "").replace("\\", "/")
            shutil.copy2(SOURCE / "sprites" / relative, images / f"image {index}.png")


def normalize_objects() -> None:
    for source in sorted((SOURCE / "objects").glob("*.object.gmx")):
        name = source.name.removesuffix(".object.gmx")
        old = ET.parse(source).getroot()
        root = ET.Element("object", {"id": "0"})
        sprite = old.findtext("spriteName", "").replace("<undefined>", "")
        parent = old.findtext("parentName", "").replace("<undefined>", "")
        mask = old.findtext("maskName", "").replace("<undefined>", "")
        text(root, "sprite", sprite)
        text(root, "solid", str(old.findtext("solid", "0") != "0").lower())
        text(root, "visible", str(old.findtext("visible", "0") != "0").lower())
        text(root, "depth", old.findtext("depth", "0"))
        text(root, "persistent", str(old.findtext("persistent", "0") != "0").lower())
        text(root, "parent", parent)
        text(root, "mask", mask)
        write_xml(DEST / "Objects" / f"{name}.xml", root)
        event_dir = DEST / "Objects" / f"{name}.events"
        for number, event in enumerate(old.findall("./events/event")):
            event_type = int(event.attrib["eventtype"])
            category = EVENTS[event_type]
            event_num = int(event.attrib.get("enumb", "0"))
            normalized = ET.Element("event", {"category": category, "id": str(event_num)})
            actions = ET.SubElement(normalized, "actions")
            for old_action in event.findall("action"):
                action = ET.SubElement(actions, "action")
                text(action, "kind", "CODE")
                arguments = ET.SubElement(action, "arguments")
                code = old_action.findtext("./arguments/argument/string", "")
                text(arguments, "argument", code).set("kind", "STRING")
            write_xml(event_dir / f"{category.title()} {event_num}-{number}.xml", normalized)


def normalize_scripts() -> None:
    target = DEST / "Scripts"
    target.mkdir(parents=True, exist_ok=True)
    for source in (SOURCE / "scripts").glob("*.gml"):
        shutil.copy2(source, target / source.name)


def normalize_rooms() -> None:
    for source in sorted((SOURCE / "rooms").glob("*.room.gmx")):
        name = source.name.removesuffix(".room.gmx")
        old = ET.parse(source).getroot()
        root = ET.Element("room", {"id": "0"})
        ET.SubElement(root, "size", {"width": old.findtext("width", "640"), "height": old.findtext("height", "480")})
        text(root, "speed", old.findtext("speed", "60"))
        text(root, "persistent", str(old.findtext("persistent", "0") != "0").lower())
        text(root, "creationCode", old.findtext("code", ""))
        colour = int(old.findtext("colour", "12632256"))
        text(root, "backgroundColor", f"{colour & 255:02X}{(colour >> 8) & 255:02X}{(colour >> 16) & 255:02X}")
        # This minimal interchange format does not normalize legacy cameras.
        # Projects that depend on views should restore them in their rule pack.
        text(root, "enableViews", "false")
        instances = ET.SubElement(root, "instances")
        for index, instance in enumerate(old.findall("./instances/instance")):
            item = ET.SubElement(instances, "instance", {"id": str(100000 + index)})
            text(item, "object", instance.attrib["objName"])
            ET.SubElement(item, "position", {"x": instance.attrib["x"], "y": instance.attrib["y"]})
            text(item, "creationCode", instance.attrib.get("code", ""))
        write_xml(DEST / "Rooms" / f"{name}.xml", root)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Studio 1 GMX project directory.")
    parser.add_argument("destination", type=Path, help="Output directory for normalized resources.")
    args = parser.parse_args()

    global SOURCE, DEST
    SOURCE = args.source.resolve()
    DEST = args.destination.resolve()
    if not SOURCE.is_dir():
        parser.error(f"source does not exist or is not a directory: {SOURCE}")
    if SOURCE == DEST or SOURCE in DEST.parents:
        parser.error("destination must not be the source directory or one of its children")

    DEST.mkdir(parents=True, exist_ok=True)
    normalize_sprites()
    normalize_objects()
    normalize_scripts()
    normalize_rooms()
    print(f"Normalized GMX project: {SOURCE} -> {DEST}")


if __name__ == "__main__":
    main()
