#!/usr/bin/env python3
"""Statically extract named GameMaker YYC event functions from a PE executable."""

from __future__ import annotations

import argparse
import json
import re
import struct
import subprocess
from pathlib import Path


EVENT_RE = re.compile(rb"\??gml_Object_[A-Za-z0-9_]+(?:_\d+)?\x00")
PROLOGUES = (b"\x55\x89\xe5", b"\x55\x8b\xec")


def section_info(executable: Path, name: str) -> tuple[int, int, int]:
    output = subprocess.check_output(["objdump", "-h", str(executable)], text=True)
    pattern = re.compile(
        rf"^\s*\d+\s+{re.escape(name)}\s+([0-9a-fA-F]+)\s+([0-9a-fA-F]+)\s+"
        rf"[0-9a-fA-F]+\s+([0-9a-fA-F]+)",
        re.MULTILINE,
    )
    match = pattern.search(output)
    if not match:
        raise SystemExit(f"section {name!r} not found")
    return tuple(int(value, 16) for value in match.groups())


def preceding_prologue(blob: bytes, offset: int, lower_bound: int) -> int:
    candidates = [blob.rfind(marker, lower_bound, offset + 1) for marker in PROLOGUES]
    start = max(candidates)
    if start < lower_bound:
        raise ValueError(f"no function prologue before file offset 0x{offset:x}")
    return start


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("executable", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    blob = args.executable.read_bytes()
    text_size, text_vma, text_offset = section_info(args.executable, ".text")
    rdata_size, rdata_vma, rdata_offset = section_info(args.executable, ".rdata")
    text_end = text_offset + text_size
    events: list[dict[str, int | str]] = []

    for match in EVENT_RE.finditer(blob, rdata_offset, rdata_offset + rdata_size):
        raw_name = match.group(0)[:-1].decode("ascii")
        name = raw_name.removeprefix("?")
        string_vma = rdata_vma + match.start() - rdata_offset
        # Some YYC names have a one-byte RTTI/sentinel prefix while generated
        # code references the printable `gml_` portion.
        referenced_string_vma = string_vma + (1 if raw_name.startswith("?") else 0)
        needle = struct.pack("<I", referenced_string_vma)
        references = []
        cursor = text_offset
        while True:
            found = blob.find(needle, cursor, text_end)
            if found < 0:
                break
            references.append(found)
            cursor = found + 1
        if not references:
            continue
        reference = references[0]
        start_offset = preceding_prologue(blob, reference, max(text_offset, reference - 0x100))
        start_vma = text_vma + start_offset - text_offset
        events.append(
            {
                "name": name,
                "string_vma": referenced_string_vma,
                "reference_vma": text_vma + reference - text_offset,
                "start_vma": start_vma,
            }
        )

    events.sort(key=lambda event: int(event["start_vma"]))
    args.output.mkdir(parents=True, exist_ok=True)
    for index, event in enumerate(events):
        start = int(event["start_vma"])
        stop = int(events[index + 1]["start_vma"]) if index + 1 < len(events) else start + 0x4000
        assembly = subprocess.check_output(
            [
                "objdump",
                "-d",
                "-M",
                "intel",
                f"--start-address=0x{start:x}",
                f"--stop-address=0x{stop:x}",
                str(args.executable),
            ],
            text=True,
        )
        (args.output / f"{event['name']}.asm").write_text(assembly, encoding="utf-8")
        event["stop_vma"] = stop

    manifest = {
        "source": str(args.executable),
        "method": "static named-event x86 extraction; executable was not run",
        "events": events,
    }
    (args.output / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(f"extracted {len(events)} named YYC events to {args.output}")


if __name__ == "__main__":
    main()
