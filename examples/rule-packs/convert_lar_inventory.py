#!/usr/bin/env python3
"""Build a current GameMaker project from the recovered LAR inventory example."""

from __future__ import annotations

import json
import re
import shutil
import struct
import subprocess
import sys
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONFIGS = {
    "lowg": {
        "source": "split/root_LOWG_fix_lowg",
        "sprites": ("spr_agent", "spr_block", "sprite2", "spr_fin", "spr_title", "sprite5"),
        "objects": ("obj_agent", "obj_block", "obj_fin", "object3"),
        "fonts": (), "background": "background0", "extra_backgrounds": ("bkg_tileset",),
        "compose_room_tiles": ("room0",), "background_object": True, "rooms": ("room0",),
    },
    "west": {
        "source": "split/root_WEST_Acid's_WEST_West",
        "sprites": ("spr_people", "spr_revolver", "spr_cloud", "spr_draw", "spr_title"),
        "objects": ("obj_control", "obj_cloud", "obj_textbox", "obj_draw", "obj_fire", "obj_sheriffwin", "ob_title"),
        "fonts": ("fnt_textbox",), "scripts": ("draw_textbox",),
        "background": "background0", "background_object": True, "rooms": ("rm_title", "rm_game", "rm_win"),
    },
    "s4d": {
        "source": "split/root_acid_s4d_s4d_s4d",
        "sprites": ("spr_noise", "spr_player_stand", "spr_player_walk", "spr_player_jog", "spr_player_fall", "spr_player_run", "spr_splash"),
        "objects": ("object0",), "fonts": ("fnt_hud",), "sounds": ("snd_noise",),
        "background": "background0", "extra_backgrounds": ("background1", "background2"),
        "background_object": True, "rooms": ("room0",),
    },
    "brick": {
        "source": "split/root_brick_brick", "sprites": ("spr_title",), "objects": ("obj_title",),
        "fonts": (), "background": "bkg_game", "background_object": True, "rooms": ("room0", "room1"),
    },
    "defwar": {
        "source": "split/root_defwar_defwar",
        "sprites": ("spr_child", "spr_units", "spr_base", "spr_e_base", "msk_base", "spr_wall", "spr_actions", "spr_button", "msk_bullet", "spr_icons"),
        "objects": ("obj_controller", "obj_lose", "obj_title", "obj_win", "par_enemy", "par_friendly", "obj_b_gunner", "obj_b_heavy", "obj_b_infantry", "obj_b_kidnap", "obj_b_worker", "obj_e_base", "obj_e_bullet", "obj_e_gunner", "obj_e_heavy", "obj_e_infantry", "obj_e_kidnapper", "obj_e_worker", "obj_base", "obj_bullet", "obj_gunner", "obj_heavy", "obj_infantry", "obj_kidnapper", "obj_wall", "obj_worker"),
        "fonts": ("fnt_hud", "fnt_endgame"), "background": "bkg_game", "background_object": True,
        "rooms": ("rm_title", "rm_game", "rm_win", "rm_lose"),
    },
    "doyouloveus": {
        "source": "split/root_doyouloveus_doyouloveus_doyouloveus_source",
        "sprites": ("spr_player", "spr_runner", "spr_love"), "objects": ("obj_player", "obj_runner"),
        "fonts": (), "background": "bkg_floor", "extra_backgrounds": ("tex_stalagmite",),
        "background_object": True, "rooms": ("room0",),
        "custom_scripts": ("dylu_d3d_compat",),
    },
    "persistence": {
        "source": "split/root_decompiled_persistence-f4demo",
        "sprites": ("msk_player", "msk_tree", "sprite1", "spr_attack", "spr_cursor", "spr_items", "spr_player_b", "spr_player_f", "spr_stamina", "spr_tree", "spr_weapons"),
        "objects": ("obj_attack", "obj_camera", "obj_player", "obj_tree", "par_solid"),
        "fonts": ("fnt_hud",), "background": "background0", "background_object": True,
        "rooms": ("room0",),
    },
    "versus": {
        "source": "split/root_decompiled_versus",
        "sprites": ("msk_player", "spr_flame", "spr_player"),
        "objects": ("obj_controller", "obj_flame", "obj_player", "obj_player_2"),
        "fonts": ("fnt_hud",), "rooms": ("room0",),
    },
    "monster": {
        "source": "split/root_monster_monster_monster",
        "sprites": ("a_light", "sprite22", "sprite6", "spr_lamp", "spr_light", "spr_s4d", "msk_player", "sprite4", "spr_aura", "spr_him", "spr_particle", "spr_player_stand", "spr_player_stand_b", "spr_player_test", "spr_player_walk", "spr_player_walk_b", "spr_portal", "spr_reaper_stand", "spr_reaper_suck", "spr_reaper_walk", "spr_template"),
        "objects": ("par_wall", "obj_player", "obj_basicwall", "obj_light", "obj_controller", "obj_aura", "obj_particle", "obj_him", "obj_portal"),
        "fonts": ("fnt_title", "fnt_hud"), "sounds": ("snd_step", "snd_step2", "snd_step3"),
        "scripts": ("draw_message", "draw_speech"), "background": "bkg_room", "extra_backgrounds": ("background1",),
        "background_object": True, "rooms": ("room0", "rm_hall"),
    },
    "basket": {
        "source": "split/gmx_basket",
        "sprites": ("spr_limbs", "spr_body", "spr_neck", "spr_head", "spr_hand", "spr_foot"),
        "objects": ("obj_controller", "obj_body"),
        "fonts": (),
        "scripts": ("draw_limb", "get_angle_diff"),
        "rooms": ("rm_test",),
    },
    "lar_inventory_ex": {
        "source": "split/input_64digits_lar_inventory_ex",
        "sprites": ("spr_items", "spr_player"),
        "objects": ("obj_item", "obj_player"),
        "fonts": (),
        "room": "rm_game",
    },
    "tembo": {
        "source": "split/recovered_source-original_tembo_TEMBO_data_tembo",
        "sprites": ("spr_objects", "spr_player", "sprite2"),
        "objects": ("obj_player",),
        "fonts": ("fnt_title", "fnt_highscore"),
        "room": "room0",
    },
    "64jam": {
        "source": "split/recovered_source-original_acid_64JAM_FIXED_64jam",
        "sprites": ("spr_blood", "spr_fire", "spr_rocket", "spr_ship", "spr_walking", "sprite4"),
        "objects": ("obj_controller", "obj_fire", "obj_person", "obj_player", "obj_rocket"),
        "fonts": ("fnt_hud",),
        "background": "bkg_game",
        "room": "room0",
    },
    "unfinishedwaspgame": {
        "source": "split/input_64digits_unfinishedwaspgame",
        "sprites": ("msk_bowl", "msk_window", "spr_bowl", "spr_cereal", "spr_cursor", "spr_nest", "spr_wasp", "spr_window"),
        "objects": ("obj_bowl", "obj_nest", "obj_wasp", "obj_window"),
        "fonts": (),
        "background": "background0",
        "room": "room0",
    },
    "hydra": {
        "source": "split/input_64digits_hydra",
        "sprites": ("alpha_laser", "ico_controller", "ico_danger", "ico_message", "sprite8", "spr_button", "spr_danger", "spr_images", "spr_laser", "spr_player", "spr_title", "spr_trail"),
        "objects": ("obj_controller", "obj_danger", "obj_message", "obj_player", "obj_trail"),
        "fonts": ("fnt_hud", "fnt_score"),
        "background": "bkg_stars",
        "extra_backgrounds": ("bkg_starsmove",),
        "background_object": True,
        # The recovered scripts populate dialogue starting at slot 1.  The
        # original runner tolerated the -1 counter; current HTML5 does not.
        "message_index_base": 1,
        "room": "room0",
    },
    "gaemmem": {
        "source": "split/input_64digits_gaemmem",
        "sprites": ("ico_controller", "ico_danger", "ico_message", "sprite8", "spr_danger", "spr_images", "spr_player", "spr_title", "spr_trail"),
        "objects": ("obj_controller", "obj_danger", "obj_message", "obj_player", "obj_trail"),
        "fonts": ("fnt_hud", "fnt_score"),
        "background": "bkg_stars",
        "extra_backgrounds": ("bkg_starsmove",),
        "background_object": True,
        "room": "room0",
    },
    "zombieinfection": {
        "source": "split/input_64digits_zombieinfection",
        "sprites": ("msk_bullet", "spr_blood", "spr_bullet", "spr_camera", "spr_controls", "spr_cursor", "spr_gore", "spr_hud", "spr_legs", "spr_playerarms", "spr_playerarmsrun", "spr_playerrest", "spr_playerrun", "spr_playerstand", "spr_weapon", "spr_zombie"),
        "objects": ("obj_blood", "obj_bullet", "obj_camera", "obj_controls", "obj_gameover", "obj_gore", "obj_player", "obj_weapon", "obj_zombie"),
        "fonts": ("fnt_gameover", "fnt_hud", "fnt_score"),
        "background": "room_scene",
        "background_draw_object": "obj_camera",
        "compose_tiles": True,
        "background_object": True,
        "room": "rm_game",
    },
    "quilder": {
        "source": "split/input_64digits_quilder",
        "sprites": ("spr_blood", "spr_bullet", "spr_crab", "spr_cursor", "spr_player", "spr_playerrun", "spr_weapons", "sprite6"),
        "objects": ("obj_bullet", "obj_controller", "obj_crab", "obj_player", "obj_weapon", "par_enemy"),
        "fonts": (),
        # Quilder was authored against a white room surface, not the generic
        # neutral gray fallback used by blank legacy rooms.
        "clear_colours": {"room0": "FFFFFF"},
        "room": "room0",
    },
    "snowstorm_v2": {
        "source": "split/input_64digits_snowstorm_v2",
        "sprites": ("msk_body", "msk_bullet", "msk_wall", "msk_weapons", "spr_blood", "spr_box", "spr_box_parts", "spr_burst", "spr_enemy1", "spr_enemy1_body", "spr_grenade", "spr_grenadeicon", "spr_healthpad", "spr_infobox", "spr_player", "spr_player_legs", "spr_weaponicons", "spr_weapons"),
        "objects": ("obj_blood", "obj_box", "obj_box_parts", "obj_bullet", "obj_burst", "obj_enemy", "obj_grenade", "obj_healthpack", "obj_particle", "obj_pgrenade", "obj_player", "obj_shell", "obj_snowmobile", "obj_title", "obj_wall", "obj_weapon", "par_enemy", "par_hit", "par_vehical"),
        "fonts": ("fnt_hud",),
        "sounds": ("snd_button",),
        "scripts": ("controls", "draw_hpbar", "draw_player"),
        "background": "bkg_snow",
        "compose_room_tiles": ("rm_test",),
        "background_object": True,
        "rooms": ("rm_title", "rm_options", "rm_test"),
    },
    "organism_v8": {
        "source": "split/recovered_source-original_Organism_Final_fix_Organism_v8_organismtest_v08",
        "sprites": ("msk_organism", "spr_button", "spr_ctrlbuttons", "spr_cursor", "spr_editorbuttons", "spr_editorhud", "spr_gamehud", "spr_opt_back", "spr_opt_check", "spr_opt_graphic", "spr_opt_volume", "spr_opt_window", "spr_pointnumb", "sprite1"),
        "objects": ("obj_add", "obj_bubble", "obj_clear", "obj_controller", "obj_cursor", "obj_delete", "obj_editor", "obj_editorexit", "obj_editorload", "obj_editorname", "obj_editorsave", "obj_goptions", "obj_help", "obj_load", "obj_menu", "obj_music", "obj_options", "obj_organism", "obj_prey", "obj_save", "obj_stealinfo", "obj_title"),
        "fonts": ("fnt_button", "fnt_text", "fnt_title"),
        "sounds": ("bgm_game",),
        "scripts": ("addorg", "reproduce", "room_wrap", "set_name"),
        "background": "bkg_water",
        "extra_backgrounds": ("bkg_hud", "tex_organism"),
        "background_object": True,
        "rooms": ("rm_title", "rm_play", "rm_editor", "rm_options", "rm_help"),
    },
    "organism_v03": {
        "source": "split/gm6_organismtest_v03",
        "sprites": ("sprite1", "spr_editorbuttons", "spr_hudback", "spr_pointnumb"),
        "objects": ("obj_controller", "obj_editor", "obj_editorexit", "obj_editorload", "obj_editorname", "obj_editorsave", "obj_organism", "obj_stealinfo", "obj_title"),
        "fonts": ("fnt_text",),
        "scripts": ("room_wrap",),
        "background": "bkg_water",
        "extra_backgrounds": ("bkg_hud", "tex_organism"),
        "background_object": True,
        "rooms": ("rm_title", "rm_editor"),
    },
    "organism_v04": {
        "source": "split/gm6_organismtest_v04",
        "sprites": ("msk_organism", "sprite1", "spr_editorbuttons", "spr_editorhud", "spr_gamehud", "spr_pointnumb"),
        "objects": ("obj_controller", "obj_editor", "obj_editorexit", "obj_editorload", "obj_editorname", "obj_editorsave", "obj_organism", "obj_prey", "obj_stealinfo", "obj_title"),
        "fonts": ("fnt_text",),
        "scripts": ("reproduce", "room_wrap"),
        "background": "bkg_water",
        "extra_backgrounds": ("bkg_hud", "tex_organism"),
        "background_object": True,
        "rooms": ("rm_title", "rm_play", "rm_editor"),
    },
    "organism_v05": {
        "source": "split/gm6_organismtest_v05",
        "sprites": ("msk_organism", "sprite1", "spr_cursor", "spr_editorbuttons", "spr_editorhud", "spr_gamehud", "spr_pointnumb"),
        "objects": ("obj_bubble", "obj_controller", "obj_editor", "obj_editorexit", "obj_editorload", "obj_editorname", "obj_editorsave", "obj_help", "obj_organism", "obj_prey", "obj_stealinfo", "obj_title"),
        "fonts": ("fnt_text",),
        "scripts": ("reproduce", "rnd", "room_wrap", "set_name"),
        "background": "bkg_water",
        "extra_backgrounds": ("bkg_hud", "tex_organism"),
        "background_object": True,
        "rooms": ("rm_title", "rm_play", "rm_editor", "rm_help"),
    },
    "char_test": {
        "source": "split/gm6_char_test",
        "sprites": ("spr_attacking", "spr_box", "spr_crouching", "spr_jumping", "spr_spritesheet", "spr_standing", "spr_walking"),
        "objects": ("obj_box", "obj_player"),
        "fonts": (),
        "rooms": ("room0",),
    },
    "ex_char_select": {
        "source": "split/gm6_ex_char_select",
        "sprites": ("spr_cover", "spr_portraits", "spr_selector", "spr_skins"),
        "objects": ("obj_char1", "obj_char2", "obj_char3", "obj_char4", "obj_cover", "obj_player", "obj_selector"),
        "fonts": ("font0",),
        "rooms": ("rm_char", "rm_game"),
    },
    "lego": {
        "source": "split/gm6_lego",
        "sprites": ("spr_block", "spr_wall"),
        "objects": ("obj_block", "obj_goal", "obj_wall"),
        "fonts": (),
        "rooms": ("room0", "room1", "room2"),
    },
    "vs_actionmenu": {
        "source": "split/gm6_vs_actionmenu",
        "sprites": ("spr_arrows", "spr_playerh", "spr_playermarker", "spr_playerv"),
        "objects": ("obj_player",),
        "fonts": ("fnt_actionmenu",),
        "rooms": ("room0",),
    },
    "rpsx": {
        "source": "split/gm6_RPSX",
        "sprites": ("spr_buttons", "spr_keys"),
        "objects": ("obj_controller",),
        "fonts": ("fnt_icon", "fnt_name", "fnt_txt"),
        "background": "bkg_game",
        "extra_backgrounds": ("frg_game",),
        "background_object": True,
        "rooms": ("room0",),
    },
    "rps2": {
        "source": "split/gm6_rps2",
        "sprites": ("spr_buttons", "spr_icons"),
        "objects": ("obj_controller",),
        "fonts": ("fnt_icon", "fnt_name"),
        "background": "bkg_game",
        "extra_backgrounds": ("bkg_gamemaker",),
        "background_object": True,
        "rooms": ("room0",),
    },
    "fireworks_v1_2": {
        "source": "split/gm6_Fireworks_v1.2",
        "sprites": ("msk_goal", "spr_arrow", "spr_hill", "spr_rocket"),
        "objects": ("obj_addtext", "obj_controller", "obj_cpu_rocket", "obj_fireworks", "obj_flame", "obj_goal", "obj_hill", "obj_options", "obj_particle", "obj_rocket", "obj_rocket2", "obj_special", "obj_stream", "obj_title"),
        "fonts": ("fnt_text",),
        "sounds": ("snd_button", "snd_explosion1", "snd_explosion2", "snd_explosion3", "snd_explosion4"),
        "depth_overrides": {"obj_flame": 0},
        "rooms": ("rm_title", "rm_single", "rm_multi", "rm_special", "rm_options"),
    },
    "ghosts_are_scary": {
        "source": "split/exe_ghosts-are-scary",
        "sprites": ("msk_give", "msk_hit", "spr_ghost", "spr_give", "spr_pumpkin", "spr_punch", "spr_stand"),
        "objects": ("obj_ghost", "obj_give", "obj_gotonextroom", "obj_player", "obj_pumpkin", "obj_punch", "obj_textbox"),
        "fonts": ("fnt_textbox",), "scripts": ("textbox",),
        "background": "bkg_game", "extra_backgrounds": ("bkg_ghost", "bkg_intro", "bkg_pumpkin"),
        "room_backgrounds": {"rm_game": "bkg_game", "rm_intro": "bkg_intro", "rm_lose_ghost": "bkg_ghost", "rm_lose_pumpkin": "bkg_pumpkin"},
        "background_object": True,
        "rooms": ("rm_intro", "rm_game", "rm_lose_ghost", "rm_lose_pumpkin"),
    },
    "runboyrun": {
        "source": "split/exe_runboyrun",
        "sprites": ("sprite5", "sprite6", "spr_legs", "spr_playerrest", "spr_playerrun", "spr_playerstand", "spr_zombie"),
        "objects": ("obj_gameover", "obj_player", "obj_zombie"),
        "fonts": ("fnt_gameover", "fnt_hud", "fnt_run", "fnt_score"),
        "background": "bkg_grass", "extra_backgrounds": ("tileset_dirt", "tileset_holes"),
        "compose_room_tiles": ("rm_game",), "background_object": True,
        "rooms": ("rm_game", "rm_gameover"),
    },
    "runboyrun_fix": {
        "source": "split/exe_runboyrun-fix",
        "sprites": ("sprite5", "sprite6", "spr_legs", "spr_playerrest", "spr_playerrun", "spr_playerstand", "spr_zombie"),
        "objects": ("obj_gameover", "obj_player", "obj_zombie"),
        "fonts": ("fnt_gameover", "fnt_hud", "fnt_run", "fnt_score"),
        "background": "bkg_grass", "extra_backgrounds": ("tileset_dirt", "tileset_holes"),
        "compose_room_tiles": ("rm_game",), "background_object": True,
        "rooms": ("rm_game", "rm_gameover"),
    },
    "sng_v02": {
        "source": "split/exe_sng-v0.2",
        "sprites": ("msk_ninja", "msk_talk", "msk_textbox", "msk_wall", "msk_warp", "sprite3", "spr_hold", "spr_mash", "spr_ninja", "spr_ninja_glide", "spr_ninja_run", "spr_ninja_sleep", "spr_zzz"),
        "objects": ("obj_main", "obj_player", "obj_scene1_player", "obj_scene2_player", "obj_talk", "obj_textbox", "obj_wall", "obj_warp", "obj_zzz"),
        "fonts": ("fnt_text", "fnt_title"), "scripts": ("draw_textbox",),
        "background": "bkg_grass", "extra_backgrounds": ("background4", "background5", "background6", "background7", "bkg_house", "bkg_house_inside", "bkg_office"),
        "room_backgrounds": {"rm_house": "bkg_house_inside", "rm_map": "bkg_grass", "rm_office_1": "background4", "rm_office_2": "background4"},
        "background_object": True,
        "rooms": ("rm_setglobalvar", "rm_house", "rm_map", "rm_office_1", "rm_office_2"),
    },
    "standaround": {
        "source": "split/exe_standaround",
        "sprites": ("sprite0",), "objects": ("obj_gameover", "obj_player"),
        "fonts": ("fnt_game",), "background": "background0",
        "room_backgrounds": {"room0": "background0"},
        "background_object": True, "tile_background": True, "rooms": ("room0", "rm_gameover"),
    },
    "fightboyfight": {
        "source": "split/input_fightboyfight",
        "sprites": ("spr_human", "spr_zombie", "spr_zombie_t", "spr_tank", "spr_fatboy", "spr_weapons", "msk_bullet", "spr_bullet", "spr_grass", "spr_blood", "spr_title", "spr_controls", "spr_cursor"),
        "objects": ("obj_title", "obj_title_effect", "obj_soundcontroller", "obj_controller", "obj_player", "obj_weapon", "obj_bullet", "obj_zombie"),
        # Generated separately: the old bitmap font range can stall the Windows
        # atlas helper, but must not block resource/room recovery.
        "fonts": (), "existing_fonts": ("fnt_dead", "fnt_hud", "fnt_title"),
        "sounds": ("bgm_game",),
        "rooms": ("rm_title", "rm_game"),
    },
}
PROJECT = sys.argv[1] if len(sys.argv) > 1 else "lar_inventory_ex"
CONFIG = CONFIGS[PROJECT]
SOURCE = ROOT / CONFIG["source"]
DEST = ROOT / "modern" / PROJECT


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def png_size(path: Path) -> tuple[int, int]:
    with path.open("rb") as stream:
        stream.read(16)
        return struct.unpack(">II", stream.read(8))


def ref(kind: str, name: str) -> dict[str, str]:
    return {"name": name, "path": f"{kind}/{name}/{name}.yy"}


def windows_path(path: Path) -> str:
    return subprocess.run(["wslpath", "-w", str(path)], check=True,
                          capture_output=True, text=True).stdout.strip()


def source_resource(kind: str, name: str) -> Path:
    matches = list((SOURCE / kind).rglob(f"{name}.xml"))
    if len(matches) != 1:
        raise FileNotFoundError(f"Expected one {kind}/{name}.xml, found {len(matches)}")
    return matches[0]


def compose_room_background(room_name: str | None = None) -> Path:
    room_name = room_name or CONFIG["room"]
    room_xml = ET.parse(source_resource("Rooms", room_name)).getroot()
    width = int(room_xml.find("size").attrib["width"])
    height = int(room_xml.find("size").attrib["height"])
    colour = room_xml.findtext("backgroundColor", "000000")
    first_background = next(item for item in room_xml.findall("./backgrounds/backgroundDef")
                            if item.findtext("visibleOnRoomStart") == "true" and item.findtext("backgroundImage"))
    base_name = first_background.findtext("backgroundImage")
    tiles = []
    for tile in room_xml.findall("./tiles/tile"):
        source_pos = tile.find("backgroundPosition")
        room_pos = tile.find("roomPosition")
        size = tile.find("size")
        tiles.append({"source": str(source_resource("Backgrounds", tile.findtext("background")).with_suffix(".png")),
                      "sourceX": int(source_pos.attrib["x"]), "sourceY": int(source_pos.attrib["y"]),
                      "left": int(room_pos.attrib["x"]), "top": int(room_pos.attrib["y"]),
                      "width": int(size.attrib["width"]), "height": int(size.attrib["height"])})
    generated = ROOT / "generated" / f"{PROJECT}-{room_name}.png"
    generated.parent.mkdir(parents=True, exist_ok=True)
    if generated.exists():
        return generated
    manifest = generated.with_suffix(".json")
    write_json(manifest, {"width": width, "height": height,
        "colour": {"r": int(colour[0:2], 16), "g": int(colour[2:4], 16),
                   "b": int(colour[4:6], 16), "alpha": 1},
        "base": str(source_resource("Backgrounds", base_name).with_suffix(".png")), "tiles": tiles})
    subprocess.run(["node", str(ROOT / "compose_room_background.mjs"), str(manifest), str(generated)], check=True)
    manifest.unlink()
    return generated


def sprite(name: str, images: list[Path] | None = None) -> None:
    xml_path = source_resource("Sprites", name) if images is None else None
    xml = ET.parse(xml_path).getroot() if xml_path is not None else None
    images = sorted(xml_path.with_suffix(".images").glob("*.png")) if xml_path is not None else images
    width, height = png_size(images[0])
    layer_id = str(uuid.uuid4())
    frame_ids = [str(uuid.uuid4()) for _ in images]
    target = DEST / f"sprites/{name}"
    target.mkdir(parents=True, exist_ok=True)
    transparent = xml is not None and xml.findtext("transparent") == "true"
    for image, frame_id in zip(images, frame_ids):
        frame_target = target / f"{frame_id}.png"
        if PROJECT == "monster" and name == "spr_light":
            mask = source_resource("Sprites", "a_light").with_suffix(".images") / "image 0.png"
            subprocess.run(["node", str(ROOT / "apply_alpha_mask.mjs"), str(image), str(mask), str(frame_target)], check=True)
        elif transparent:
            subprocess.run(["node", str(ROOT / "chroma_key_sprite.mjs"), str(image), str(frame_target)], check=True)
        else:
            shutil.copy2(image, frame_target)
        layer_target = target / "layers" / frame_id
        layer_target.mkdir(parents=True, exist_ok=True)
        shutil.copy2(frame_target, layer_target / f"{layer_id}.png")
    origin = xml.find("origin") if xml is not None else None
    xorigin = int(origin.attrib["x"]) if origin is not None else 0
    yorigin = int(origin.attrib["y"]) if origin is not None else 0

    # Preserve the authored collision mask. The previous full-frame default
    # made padded sprites collide early (notably LOWG's player and QuilDER's
    # 64x64 bullet frames).
    bounds = xml.find("./mask/bounds") if xml is not None else None
    bounds_mode = bounds.attrib.get("mode", "AUTO") if bounds is not None else "FULL"
    if bounds_mode == "MANUAL":
        bbox_left = max(0, min(width - 1, int(bounds.findtext("left", "0"))))
        bbox_right = max(bbox_left, min(width - 1, int(bounds.findtext("right", str(width - 1)))))
        bbox_top = max(0, min(height - 1, int(bounds.findtext("top", "0"))))
        bbox_bottom = max(bbox_top, min(height - 1, int(bounds.findtext("bottom", str(height - 1)))))
        bbox_mode = 2
    elif bounds_mode == "AUTO":
        result = subprocess.run(
            ["node", str(ROOT / "sprite_alpha_bounds.mjs"),
             *[str(target / f"{frame_id}.png") for frame_id in frame_ids]],
            check=True, capture_output=True, text=True)
        auto = json.loads(result.stdout)
        bbox_left, bbox_right = auto["left"], auto["right"]
        bbox_top, bbox_bottom = auto["top"], auto["bottom"]
        bbox_mode = 0
    else:
        bbox_left, bbox_right, bbox_top, bbox_bottom = 0, width - 1, 0, height - 1
        bbox_mode = 1
    shape = xml.findtext("./mask/shape", "PRECISE") if xml is not None else "RECTANGLE"
    separate = xml.findtext("./mask/separate", "false") == "true" if xml is not None else False
    collision_kind = {"RECTANGLE": 0, "PRECISE": 4 if separate else 1,
                      "ELLIPSE": 2, "DIAMOND": 3}.get(shape, 1)

    frames = [
        {"$GMSpriteFrame": "v1", "%Name": frame_id, "name": frame_id,
         "resourceType": "GMSpriteFrame", "resourceVersion": "2.0"}
        for frame_id in frame_ids
    ]
    keys = [
        {"$Keyframe<SpriteFrameKeyframe>": "", "Channels": {"0": {
            "$SpriteFrameKeyframe": "", "Id": ref("sprites", name) | {"name": frame_id},
            "resourceType": "SpriteFrameKeyframe", "resourceVersion": "2.0"}},
         "Disabled": False, "id": str(uuid.uuid4()), "IsCreationKey": False,
         "Key": float(index), "Length": 1.0, "resourceType": "Keyframe<SpriteFrameKeyframe>",
         "resourceVersion": "2.0", "Stretch": False}
        for index, frame_id in enumerate(frame_ids)
    ]
    data = {
        "$GMSprite": "v2", "%Name": name, "bboxMode": bbox_mode, "bbox_bottom": bbox_bottom,
        "bbox_left": bbox_left, "bbox_right": bbox_right, "bbox_top": bbox_top,
        "collisionKind": collision_kind,
        "collisionTolerance": 0, "DynamicTexturePage": False, "edgeFiltering": False,
        "For3D": False, "frames": frames, "gridX": 0, "gridY": 0, "height": height,
        "HTile": False, "layers": [{"$GMImageLayer": "", "%Name": layer_id,
            "blendMode": 0, "displayName": "default", "isLocked": False, "name": layer_id,
            "opacity": 100.0, "resourceType": "GMImageLayer", "resourceVersion": "2.0",
            "visible": True}], "name": name, "nineSlice": None, "origin": 4,
        "parent": {"name": PROJECT, "path": f"{PROJECT}.yyp"},
        "preMultiplyAlpha": False, "resourceType": "GMSprite", "resourceVersion": "2.0",
        "sequence": {"$GMSequence": "v1", "%Name": name, "autoRecord": True,
            "backdropHeight": 768, "backdropImageOpacity": 0.5, "backdropImagePath": "",
            "backdropWidth": 1366, "backdropXOffset": 0.0, "backdropYOffset": 0.0,
            "events": {"$KeyframeStore<MessageEventKeyframe>": "", "Keyframes": [],
                "resourceType": "KeyframeStore<MessageEventKeyframe>", "resourceVersion": "2.0"},
            "eventStubScript": None, "eventToFunction": {}, "length": float(len(images)),
            "lockOrigin": False, "moments": {"$KeyframeStore<MomentsEventKeyframe>": "",
                "Keyframes": [], "resourceType": "KeyframeStore<MomentsEventKeyframe>",
                "resourceVersion": "2.0"}, "name": name, "playback": 1,
            "playbackSpeed": 30.0, "playbackSpeedType": 0, "resourceType": "GMSequence",
            "resourceVersion": "2.0", "showBackdrop": True, "showBackdropImage": False,
            "timeUnits": 1, "tracks": [{"$GMSpriteFramesTrack": "", "builtinName": 0,
                "events": [], "inheritsTrackColour": True, "interpolation": 1,
                "isCreationTrack": False, "keyframes": {"$KeyframeStore<SpriteFrameKeyframe>": "",
                    "Keyframes": keys, "resourceType": "KeyframeStore<SpriteFrameKeyframe>",
                    "resourceVersion": "2.0"}, "modifiers": [], "name": "frames",
                "resourceType": "GMSpriteFramesTrack", "resourceVersion": "2.0",
                "spriteId": None, "trackColour": 0, "tracks": [], "traits": 0}],
            "visibleRange": None, "volume": 1.0, "xorigin": xorigin, "yorigin": yorigin},
        "swatchColours": None, "swfPrecision": 0.5,
        "textureGroupId": {"name": "Default", "path": "texturegroups/Default"},
        "type": 0, "VTile": False, "width": width,
    }
    write_json(target / f"{name}.yy", data)


EVENT_TYPES = {"CREATE": 0, "DESTROY": 1, "ALARM": 2, "STEP": 3, "COLLISION": 4,
               "KEYBOARD": 5, "MOUSE": 6, "OTHER": 7, "DRAW": 8,
               "KEYPRESS": 9, "KEYRELEASE": 10}


def rewrite_instance_create(code: str) -> str:
    """Rewrite legacy instance_create calls without breaking nested arguments."""
    needle = "instance_create("
    output: list[str] = []
    cursor = 0
    while True:
        start = code.find(needle, cursor)
        if start < 0:
            output.append(code[cursor:])
            break
        output.append(code[cursor:start])
        position = start + len(needle)
        depth = 0
        quote = ""
        escaped = False
        arguments: list[str] = []
        argument_start = position
        while position < len(code):
            character = code[position]
            if quote:
                if escaped:
                    escaped = False
                elif character == "\\":
                    escaped = True
                elif character == quote:
                    quote = ""
            elif character in "\"'":
                quote = character
            elif character == "(":
                depth += 1
            elif character == ")":
                if depth == 0:
                    arguments.append(code[argument_start:position].strip())
                    break
                depth -= 1
            elif character == "," and depth == 0:
                arguments.append(code[argument_start:position].strip())
                argument_start = position + 1
            position += 1
        if position >= len(code) or len(arguments) != 3:
            output.append(code[start:start + len(needle)])
            cursor = start + len(needle)
            continue
        output.append(
            f"instance_create_depth({arguments[0]}, {arguments[1]}, 0, {arguments[2]})"
        )
        cursor = position + 1
    return "".join(output)


def modernize_code(code: str) -> str:
    # GM5/6 image_single selects one subimage and freezes it. Merely renaming it
    # to image_index leaves the modern sprite animation running.
    code = re.sub(
        r"\bimage_s(?:ingle|inge)\s*=\s*([^;\n]+);?",
        r"image_index=\1; image_speed=0;",
        code,
    )
    code = code.replace("view_xview", "camera_get_view_x(view_camera[0])")
    code = code.replace("view_yview", "camera_get_view_y(view_camera[0])")
    code = code.replace("view_wview", "camera_get_view_width(view_camera[0])")
    code = code.replace("view_hview", "camera_get_view_height(view_camera[0])")
    if "fnt_hud" not in CONFIG["fonts"]:
        code = code.replace("fnt_hud", "-1")
    code = code.replace("if move_towards_point", "move_towards_point")
    code = rewrite_instance_create(code)
    code = re.sub(r"\bsound_play\(([^\)\n]+)\)", r"audio_play_sound(\1, 0, false)", code)
    code = re.sub(r"\bsound_loop\(([^\)\n]+)\)", r"audio_play_sound(\1, 0, true)", code)
    code = re.sub(r"\bmake_color\(", "make_color_rgb(", code)
    code = re.sub(r"\bsound_stop\(([^\)\n]+)\)", r"audio_stop_sound(\1)", code)
    code = re.sub(r"\bsound_volume\(([^,\n]+),\s*([^\)\n]+)\)", r"audio_sound_gain(\1, \2, 0)", code)
    # Classic projects sometimes addressed local array cells through a string.
    # variable_local_get/set are not callable in the current HTML5 runtime.
    code = re.sub(
        r'variable_local_set\("([A-Za-z_]\w*)\["\+string\(([^)]+)\)\+"\]",\s*([^;]+)\)',
        r'\1[\2]=\3',
        code,
    )
    code = re.sub(
        r'variable_local_get\("([A-Za-z_]\w*)\["\+string\(([^)]+)\)\+"\]"\)',
        r'\1[\2]',
        code,
    )
    # These GM6 projects use a solid-white background as a primitive texture
    # while supplying plain (non-UV) vertices. Modern HTML5 renders that legacy
    # combination incorrectly; an untextured primitive is visually equivalent.
    code = re.sub(
        r"draw_primitive_begin_texture\(([^,]+),\s*([A-Za-z_]\w*)\)",
        r"draw_primitive_begin(\1)",
        code,
    )
    code = re.sub(r"(?m)^background_(?:alpha|[hv]speed)(?:\[[^\]]+\])?\s*[+\-]?=.*?;\s*$", "", code)
    if PROJECT in {"hydra", "gaemmem"}:
        code = code.replace("start_alpha[0] = 1;", "start_alpha[0] = 0;")
    code = re.sub(r"obj\[([^,\]\n]+),\s*([^\]\n]+)\]", r"obj[\1][\2]", code)
    code = re.sub(r"'([^'\n]*)'", r'"\1"', code)
    code = re.sub(
        r'variable_local_set\("([A-Za-z_]\w*)\["\+string\(([^)]+)\)\+"\]",\s*([^;]+)\)',
        r'\1[\2]=\3',
        code,
    )
    code = re.sub(
        r'variable_local_get\("([A-Za-z_]\w*)\["\+string\(([^)]+)\)\+"\]"\)',
        r'\1[\2]',
        code,
    )
    # Classic GameMaker treated # inside a string as a line break.
    code = re.sub(r'"([^"\n]*)#([^"\n]*)"', r'"\1\\n\2"', code)
    return re.sub(r";\s*\)", ")", code)


def font_resource(name: str) -> None:
    xml = ET.parse(source_resource("Fonts", name)).getroot()
    size = float(xml.findtext("size", "12"))
    first = int(xml.findtext("rangeMin", "32"))
    last = int(xml.findtext("rangeMax", "127"))
    font_name = xml.findtext("fontName", "Arial")
    font_files = {"Arial Black": "ariblk.ttf", "Arial": "arialbd.ttf",
                  "Terminal": "consolab.ttf", "Small Fonts": "arial.ttf",
                  "Eurostile": "GOTHICB.TTF", "Futura Bk": "GOTHICB.TTF",
                  "Century Gothic": "GOTHICB.TTF"}
    font_file = font_files.get(font_name, "arialbd.ttf")
    if font_name.lower() == "rez":
        font_file = "arialbd.ttf" if xml.findtext("bold") == "true" else "arial.ttf"
        display_font_name = "Arial"
    else:
        display_font_name = "Century Gothic" if font_name == "Futura Bk" else font_name
    font_path = rf"C:\Windows\Fonts\{font_file}"
    target = DEST / f"fonts/{name}"
    target.mkdir(parents=True, exist_ok=True)
    metrics_path = target / "font-metrics.json"
    subprocess.run([
        "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
        windows_path(ROOT / "generate_font_atlas.ps1"), "-OutputPng", windows_path(target / f"{name}.png"),
        "-OutputJson", windows_path(metrics_path), "-PixelSize", str(size), "-First", str(first),
        "-Last", str(last), "-FontFile", font_path,
    ], check=True)
    metrics = json.loads(metrics_path.read_text(encoding="utf-8-sig"))
    metrics_path.unlink()
    data = {"$GMFont": "", "%Name": name, "AntiAlias": 1, "applyKerning": 0,
            "ascender": 0, "ascenderOffset": 0, "bold": xml.findtext("bold") == "true",
            "canGenerateBitmap": True, "charset": 0, "first": first, "fontName": display_font_name,
            "glyphOperations": 0, "glyphs": metrics["glyphs"], "hinting": 0, "includeTTF": False,
            "interpreter": 0, "italic": xml.findtext("italic") == "true", "kerningPairs": [],
            "last": last, "lineHeight": metrics["lineHeight"], "maintainGms1Font": False, "name": name,
            "parent": {"name": PROJECT, "path": f"{PROJECT}.yyp"}, "pointRounding": 0,
            "ranges": [{"lower": first, "upper": last}], "regenerateBitmap": False,
            "resourceType": "GMFont", "resourceVersion": "2.0", "sampleText": "TEMBO! 0123456789",
            "sdfSpread": 8, "size": size, "styleName": "Bold" if xml.findtext("bold") == "true" else "Regular",
            "textureGroupId": {"name": "Default", "path": "texturegroups/Default"},
            "TTFName": "", "usesSDF": False}
    write_json(DEST / f"fonts/{name}/{name}.yy", data)


def object_resource(name: str) -> None:
    xml_path = source_resource("Objects", name)
    xml = ET.parse(xml_path).getroot()
    (DEST / f"objects/{name}").mkdir(parents=True, exist_ok=True)
    events = []
    event_dir = xml_path.with_suffix(".events")
    for event_file in sorted(event_dir.glob("*.xml")):
        event = ET.parse(event_file).getroot()
        category = event.attrib["category"]
        collision = event.attrib.get("with")
        event_num = int(event.attrib.get("id", 0))
        entry = {"$GMEvent": "v1", "%Name": "",
                 "collisionObjectId": ref("objects", collision) if collision else None,
                 "eventNum": event_num, "eventType": EVENT_TYPES[category], "isDnD": False,
                 "name": "", "resourceType": "GMEvent", "resourceVersion": "2.0"}
        events.append(entry)
        codes = [arg.text or "" for arg in event.findall(".//action[kind='CODE']/arguments/argument")]
        if len(codes) != len(event.findall(".//action")):
            raise ValueError(f"{event_file} contains unsupported drag-and-drop actions")
        event_name = {0: "Create", 1: "Destroy", 2: "Alarm", 3: "Step", 4: "Collision",
                      5: "Keyboard", 6: "Mouse", 7: "Other", 8: "Draw", 9: "KeyPress",
                      10: "KeyRelease"}[EVENT_TYPES[category]]
        suffix = collision if collision else str(event_num)
        event_code = modernize_code("\n".join(codes))
        if PROJECT == "doyouloveus":
            event_code = event_code.replace("background_get_texture(", "sprite_get_texture(")
            event_code = re.sub(r"\bbkg_floor\b", "spr_bkg_floor", event_code)
            event_code = re.sub(r"\btex_stalagmite\b", "spr_tex_stalagmite", event_code)
            event_code = re.sub(r"sprite_get_texture\(([^,\)]+)\)", r"sprite_get_texture(\1, 0)", event_code)
            event_code = event_code.replace("texture_set_interpolation(false);", "gpu_set_texfilter(false);")
            if name == "obj_player" and category == "DRAW":
                event_code = event_code.replace(
                    "// draw floor\n",
                    "// draw floor\ndylu_batch_begin(sprite_get_texture(spr_bkg_floor, 0));\n",
                ).replace(
                    "  \n  \n  //Floor Stalagmites",
                    "\ndylu_batch_end();\ndylu_batch_begin(sprite_get_texture(spr_tex_stalagmite, 0));\n\n  //Floor Stalagmites",
                )
                event_code += "\ndylu_batch_end();\n"
        if PROJECT == "monster" and name == "obj_light" and category == "CREATE":
            event_code = event_code.replace(
                "sprite_set_alpha_from_sprite(spr_light, a_light);",
                "sprite_index = spr_light;",
            )
        if PROJECT == "basket":
            # Studio 1 treated every # inside a string as a line break. The
            # generic single-pass string rewrite can leave later separators.
            event_code = event_code.replace("#", "\\n")
        if PROJECT == "rpsx" and name == "obj_controller":
            if category == "CREATE":
                event_code = event_code.replace("show_info();", "")
            if category == "DRAW":
                event_code = re.sub(
                    r"var xx, yy, x1, x2, y1, txt;(?s:.*?)txt\[3\]=\"ROCK\";",
                    ('var xx, yy, x1, x2, y1;\n'
                     'var txt = ["", "PAPER", "SCISSORS", "ROCK"];\n'
                     'x1=room_width/5;\nx2=room_width/5*4-28;\n'
                     'xx=room_width/2;\ny1=room_height/4;\nyy=room_height-12;'),
                    event_code,
                )
                event_code = event_code.replace(
                    'if keyboard_check_pressed(vk_space) select=1; enemy=choose(1,2,3); alarm[0]=120;}',
                    'if keyboard_check_pressed(vk_space) {select=1; enemy=choose(1,2,3); alarm[0]=120;}}',
                )
        if PROJECT in {"hydra", "gaemmem"} and name == "obj_controller" and category == "CREATE":
            # The messages are stored in slots 1..n. Starting at -1 produces
            # an undefined first message in modern HTML5, leaving only the
            # dark dialogue panel visible.
            event_code = event_code.replace("msgnum = -1;", "msgnum = 0;")
        if PROJECT in {"hydra", "gaemmem"} and name == "obj_message":
            # `draw` was a harmless instance variable in the classic runner.
            # It collides with a callable HTML5 symbol in current GML once the
            # dialogue panel is activated, so use an unambiguous counter.
            event_code = re.sub(r"\bdraw\b", "message_draw", event_code)
            if category == "DRAW":
                # variable_local_exists is absent from the current HTML5
                # runtime. The controller always assigns both fields before
                # this object is first drawn, so the old fallback is needless.
                event_code = re.sub(r'if \(!variable_local_exists\("speaker"\)\) speaker = 0;\n', "", event_code)
                event_code = re.sub(r'if \(!variable_local_exists\("message"\)\) message = "[^"]*";\n', "", event_code)
        if PROJECT == "vs_actionmenu" and name == "obj_player" and category == "STEP":
            # A key-up can be lost when an embedded HTML5 canvas gains focus.
            # Make Shift deliberately toggle the menu so it remains usable.
            event_code = re.sub(
                r"if \(keyboard_check_pressed\(vk_shift\)\)\n\{.*?\n\}\nelse if \(keyboard_check_released\(vk_shift\)\) move = 1;",
                "if (keyboard_check_pressed(vk_shift))\n{\n    move = !move;\n    if (!move) { select = -2; alarm[0] = room_speed/2; }\n    else select = -1;\n}",
                event_code,
                flags=re.S,
            )
        if PROJECT == "organism_v8" and category == "MOUSE" and event_num == 4:
            # The original editor used blocking desktop file/name dialogs.
            # Those APIs are not available in the web runner. Keep a durable,
            # browser-local design slot instead so the editor remains useful.
            if name == "obj_editorname":
                event_code = ('if obj_editor.play=0 {\n'
                              '    obj_editor.name = "Custom Organism";\n'
                              '    obj_editor.save_status = 120;\n'
                              '}')
            elif name == "obj_editorsave":
                event_code = ('if obj_editor.play=0 {\n'
                              '    ini_open("organism-web-slot.odf");\n'
                              '    ini_write_string("Info", "Name", obj_editor.name);\n'
                              '    for (i=0; i<=obj_editor.pmax; i+=1) ini_write_real("Lengths", "pl["+string(i)+"]", round(obj_editor.pl[i]));\n'
                              '    for (i=1; i<=3; i+=1) ini_write_real("Info", "Color["+string(i)+"]", obj_editor.col[i]);\n'
                              '    ini_close();\n'
                              '    obj_editor.save_status = 120;\n'
                              '}')
            elif name == "obj_editorload":
                event_code = ('if obj_editor.play=0 && file_exists("organism-web-slot.odf") {\n'
                              '    ini_open("organism-web-slot.odf");\n'
                              '    obj_editor.name = ini_read_string("Info", "Name", obj_editor.name);\n'
                              '    for (i=0; i<=obj_editor.pmax; i+=1) obj_editor.pl[i] = round(ini_read_real("Lengths", "pl["+string(i)+"]", obj_editor.pl[i]));\n'
                              '    for (i=1; i<=3; i+=1) obj_editor.col[i] = ini_read_real("Info", "Color["+string(i)+"]", obj_editor.col[i]);\n'
                              '    ini_close();\n'
                              '    obj_editor.save_status = 120;\n'
                              '}')
        if category == "DRAW" and event_num == 0:
            # Legacy projects commonly rely on the implicit sprite draw being
            # isolated from alpha/colour state left behind by particle objects.
            event_code = ("draw_set_alpha(1);\ndraw_set_color(c_white);\n"
                          "gpu_set_blendmode(bm_normal);\n" + event_code)
        if PROJECT == "tembo" and category == "DRAW" and event_num == 0:
            event_code = "draw_clear(make_color_rgb(192, 192, 192));\n" + event_code
        if PROJECT in {"hydra", "gaemmem"} and name == "obj_controller" and category == "CREATE":
            event_code += "\nbackground_scroll = 0;\n"
        (DEST / f"objects/{name}/{event_name}_{suffix}.gml").write_text(
            event_code, encoding="utf-8")
    legacy_depth = CONFIG.get("depth_overrides", {}).get(name, int(xml.findtext("depth", "0")))
    create_path = DEST / f"objects/{name}/Create_0.gml"
    create_event = next((event for event in events
                         if event["eventType"] == EVENT_TYPES["CREATE"] and event["eventNum"] == 0), None)
    if create_event:
        create_path.write_text(f"depth = {legacy_depth};\n" + create_path.read_text(encoding="utf-8"),
                               encoding="utf-8")
    elif legacy_depth != 0:
        events.append({"$GMEvent": "v1", "%Name": "", "collisionObjectId": None,
                       "eventNum": 0, "eventType": EVENT_TYPES["CREATE"], "isDnD": False,
                       "name": "", "resourceType": "GMEvent", "resourceVersion": "2.0"})
        create_path.write_text(f"depth = {legacy_depth};\n", encoding="utf-8")
    background = CONFIG.get("background")
    if background and not CONFIG.get("background_object") and name == CONFIG.get("background_draw_object", CONFIG["objects"][0]):
        events.append({"$GMEvent": "v1", "%Name": "", "collisionObjectId": None,
                       "eventNum": 72, "eventType": EVENT_TYPES["DRAW"], "isDnD": False,
                       "name": "", "resourceType": "GMEvent", "resourceVersion": "2.0"})
        background_code = f"draw_sprite(spr_{background}, 0, 0, 0);\n"
        if PROJECT in {"hydra", "gaemmem"}:
            background_code += ("background_scroll = (background_scroll + 2) mod room_height;\n"
                "var star_y = background_scroll;\n"
                "draw_set_alpha(0.1);\n"
                "draw_sprite(spr_bkg_starsmove, 0, 0, star_y - room_height);\n"
                "draw_sprite(spr_bkg_starsmove, 0, 0, star_y);\n"
                "draw_set_alpha(0.25);\n"
                "draw_sprite(spr_bkg_starsmove, 0, 40, star_y - room_height);\n"
                "draw_sprite(spr_bkg_starsmove, 0, 40, star_y);\n"
                "draw_set_alpha(1);\n")
        (DEST / f"objects/{name}/Draw_72.gml").write_text(background_code, encoding="utf-8")
    sprite_name = xml.findtext("sprite") or None
    if sprite_name and not any(event["eventType"] == EVENT_TYPES["DRAW"] and event["eventNum"] == 0
                               for event in events):
        events.append({"$GMEvent": "v1", "%Name": "", "collisionObjectId": None,
                       "eventNum": 0, "eventType": EVENT_TYPES["DRAW"], "isDnD": False,
                       "name": "", "resourceType": "GMEvent", "resourceVersion": "2.0"})
        (DEST / f"objects/{name}/Draw_0.gml").write_text(
            "draw_set_alpha(1);\ndraw_set_color(c_white);\ngpu_set_blendmode(bm_normal);\ndraw_self();\n",
            encoding="utf-8")
    parent_name = xml.findtext("parent") or None
    mask_name = xml.findtext("mask") or None
    data = {"$GMObject": "", "%Name": name, "eventList": events, "managed": True,
            "name": name, "overriddenProperties": [],
            "parent": {"name": PROJECT, "path": f"{PROJECT}.yyp"},
            "parentObjectId": ref("objects", parent_name) if parent_name else None,
            "persistent": xml.findtext("persistent") == "true",
            "physicsAngularDamping": 0.1, "physicsDensity": 0.5, "physicsFriction": 0.2,
            "physicsGroup": 1, "physicsKinematic": False, "physicsLinearDamping": 0.1,
            "physicsObject": False, "physicsRestitution": 0.1, "physicsSensor": False,
            "physicsShape": 1, "physicsShapePoints": [], "physicsStartAwake": True,
            "properties": [], "resourceType": "GMObject", "resourceVersion": "2.0",
            "solid": xml.findtext("solid") == "true",
            "spriteId": ref("sprites", sprite_name) if sprite_name else None,
            "spriteMaskId": ref("sprites", mask_name) if mask_name else None,
            "visible": xml.findtext("visible") == "true"}
    write_json(DEST / f"objects/{name}/{name}.yy", data)


def flat_background_object() -> None:
    name = "obj_room_background"
    events = [{"$GMEvent": "v1", "%Name": "", "collisionObjectId": None,
        "eventNum": 0, "eventType": EVENT_TYPES["DRAW"], "isDnD": False, "name": "",
        "resourceType": "GMEvent", "resourceVersion": "2.0"}]
    data = {"$GMObject": "", "%Name": name, "eventList": events, "managed": True,
        "name": name, "overriddenProperties": [],
        "parent": {"name": PROJECT, "path": f"{PROJECT}.yyp"}, "parentObjectId": None,
        "persistent": False, "physicsAngularDamping": 0.1, "physicsDensity": 0.5,
        "physicsFriction": 0.2, "physicsGroup": 1, "physicsKinematic": False,
        "physicsLinearDamping": 0.1, "physicsObject": False, "physicsRestitution": 0.1,
        "physicsSensor": False, "physicsShape": 1, "physicsShapePoints": [],
        "physicsStartAwake": True, "properties": [], "resourceType": "GMObject",
        "resourceVersion": "2.0", "solid": False,
        "spriteId": None if CONFIG.get("compose_room_tiles") or CONFIG.get("room_backgrounds") else ref("sprites", f"spr_{CONFIG['background']}"), "spriteMaskId": None,
        "visible": True}
    write_json(DEST / f"objects/{name}/{name}.yy", data)
    code = "draw_set_alpha(1);\ndraw_set_color(c_white);\n"
    if CONFIG.get("room_backgrounds"):
        for index, (room_name, background_name) in enumerate(CONFIG["room_backgrounds"].items()):
            prefix = "if" if index == 0 else "else if"
            code += f"{prefix} (room == {room_name}) draw_sprite_tiled(spr_{background_name}, 0, 0, 0);\n"
    elif CONFIG.get("compose_room_tiles"):
        for index, room_name in enumerate(CONFIG["compose_room_tiles"]):
            prefix = "if" if index == 0 else "else if"
            code += f"{prefix} (room == {room_name}) draw_sprite(spr_room_{room_name}, 0, 0, 0);\n"
        code += f"else draw_sprite_tiled(spr_{CONFIG['background']}, 0, 0, 0);\n"
    else:
        # Every visible legacy background currently in this recovery set has
        # horizontal and vertical tiling enabled. Drawing the background
        # object's sprite once loses the repeated pattern in larger rooms.
        code += f"draw_sprite_tiled(spr_{CONFIG['background']}, 0, 0, 0);\n"
        if PROJECT == "rpsx":
            # RPS Xtreme has a second visible tiled layer in the same room.
            # Its base layer scrolls -1,+1 pixels per legacy step.
            code = ("draw_set_alpha(1);\ndraw_set_color(c_white);\n"
                "var bg_step = current_time / (1000 / room_speed);\n"
                "draw_sprite_tiled(spr_bkg_game, 0, -bg_step, bg_step);\n"
                "draw_sprite_tiled(spr_frg_game, 0, 0, 0);\n")
    if PROJECT in {"hydra", "gaemmem"}:
        code += ("background_scroll = (background_scroll + 2) mod room_height;\n"
            "var star_y = background_scroll;\n"
            "draw_set_alpha(0.1);\n"
            "draw_sprite_tiled(spr_bkg_starsmove, 0, 0, star_y);\n"
            "draw_set_alpha(0.25);\n"
            "draw_sprite_tiled(spr_bkg_starsmove, 0, 40, star_y);\n"
            "draw_set_alpha(1);\n")
    (DEST / f"objects/{name}/Draw_0.gml").write_text(code, encoding="utf-8")
    if PROJECT in {"hydra", "gaemmem"}:
        data["eventList"].append({"$GMEvent": "v1", "%Name": "", "collisionObjectId": None,
            "eventNum": 0, "eventType": EVENT_TYPES["CREATE"], "isDnD": False, "name": "",
            "resourceType": "GMEvent", "resourceVersion": "2.0"})
        write_json(DEST / f"objects/{name}/{name}.yy", data)
        (DEST / f"objects/{name}/Create_0.gml").write_text("background_scroll = 0;\n", encoding="utf-8")


def room_clear_object(room_names: tuple[str, ...]) -> None:
    """Restore each classic room's defined clear colour before anything draws."""
    name = "obj_room_clear"
    events = [{"$GMEvent": "v1", "%Name": "", "collisionObjectId": None,
        "eventNum": 72, "eventType": EVENT_TYPES["DRAW"], "isDnD": False, "name": "",
        "resourceType": "GMEvent", "resourceVersion": "2.0"}]
    data = {"$GMObject": "", "%Name": name, "eventList": events, "managed": True,
        "name": name, "overriddenProperties": [],
        "parent": {"name": PROJECT, "path": f"{PROJECT}.yyp"}, "parentObjectId": None,
        "persistent": False, "physicsAngularDamping": 0.1, "physicsDensity": 0.5,
        "physicsFriction": 0.2, "physicsGroup": 1, "physicsKinematic": False,
        "physicsLinearDamping": 0.1, "physicsObject": False, "physicsRestitution": 0.1,
        "physicsSensor": False, "physicsShape": 1, "physicsShapePoints": [],
        "physicsStartAwake": True, "properties": [], "resourceType": "GMObject",
        "resourceVersion": "2.0", "solid": False, "spriteId": None, "spriteMaskId": None,
        "visible": True}
    write_json(DEST / f"objects/{name}/{name}.yy", data)
    clauses = []
    for room_name in room_names:
        xml = ET.parse(source_resource("Rooms", room_name)).getroot()
        has_explicit_colour = room_name in CONFIG.get("clear_colours", {})
        colour = CONFIG.get("clear_colours", {}).get(
            room_name, xml.findtext("backgroundColor", "C0C0C0").zfill(6)
        )
        visible_background = any(item.findtext("visibleOnRoomStart") == "true" and
                                 (item.findtext("backgroundImage") or "").strip()
                                 for item in xml.findall("./backgrounds/backgroundDef"))
        if colour.upper() == "FFFFFF" and not visible_background and not has_explicit_colour:
            colour = "C0C0C0"
        red, green, blue = (int(colour[index:index + 2], 16) for index in (0, 2, 4))
        clauses.append((room_name, red, green, blue))
    settings_path = SOURCE / "Global Game Settings.xml"
    interpolate = False
    if settings_path.exists():
        settings = ET.parse(settings_path).getroot()
        interpolate = settings.findtext("./graphics/interpolateColors", "false").lower() == "true"
    # GameMaker's current HTML5 runner otherwise inherits its modern default.
    # Reapply the archived project's texture sampling mode before any room draw
    # so scaled sprites, rotated sprites, surfaces, and tiled edges agree.
    code = (f"gpu_set_texfilter({'true' if interpolate else 'false'});\n"
            "draw_set_alpha(1);\ngpu_set_blendmode(bm_normal);\n")
    for index, (room_name, red, green, blue) in enumerate(clauses):
        prefix = "if" if index == 0 else "else if"
        code += f"{prefix} (room == {room_name}) draw_clear(make_color_rgb({red}, {green}, {blue}));\n"
    (DEST / f"objects/{name}/Draw_72.gml").write_text(code, encoding="utf-8")


def persistent_surface_fixes() -> None:
    """Clear and recreate long-lived surfaces that HTML5 may discard."""
    if PROJECT == "quilder":
        create = DEST / "objects/obj_player/Create_0.gml"
        create.write_text(create.read_text(encoding="utf-8").replace(
            "sur_blood = surface_create(room_width, room_height);",
            "sur_blood = surface_create(room_width, room_height);\n"
            "surface_set_target(sur_blood); draw_clear_alpha(c_black, 0); surface_reset_target();",
        ), encoding="utf-8")
    elif PROJECT == "fightboyfight":
        create = DEST / "objects/obj_controller/Create_0.gml"
        create.write_text(create.read_text(encoding="utf-8").replace(
            "draw_clear_alpha(-1, 0);", "draw_clear_alpha(c_black, 0);"
        ), encoding="utf-8")
        sound = DEST / "objects/obj_soundcontroller"
        (sound / "Step_2.gml").write_text("// FMOD maintenance is unnecessary with GameMaker audio.\n", encoding="utf-8")
        (sound / "Other_2.gml").write_text(
            "global.bgm_asset = bgm_game;\n"
            "global.bgm = -1;\n", encoding="utf-8")
        (sound / "Other_3.gml").write_text(
            "audio_stop_all();\n", encoding="utf-8")
        (sound / "Other_4.gml").write_text(
            "audio_stop_all();\n"
            "global.bgm = audio_play_sound(global.bgm_asset, 0, true);\n"
            "audio_sound_gain(global.bgm, 0.05, 0);\n",
            encoding="utf-8")


def sound_resource(name: str) -> None:
    xml = ET.parse(source_resource("Sounds", name)).getroot()
    source = next(path for path in (SOURCE / "Sounds").glob(f"{name}.*") if path.suffix.lower() != ".xml")
    target = DEST / f"sounds/{name}"
    target.mkdir(parents=True, exist_ok=True)
    if source.suffix.lower() == ".mid":
        sound_file = f"{name}.wav"
        sound_bank = Path("/mnt/c/Windows/System32/drivers/gm.dls")
        if not sound_bank.exists():
            raise FileNotFoundError("MIDI conversion requires a pinned DLS/SF2 bank; Windows gm.dls was not found")
        subprocess.run([
            "node", str(ROOT / "midi-render/render.mjs"), str(sound_bank),
            str(source), str(target / sound_file),
        ], check=True)
    else:
        sound_file = f"{name}{source.suffix.lower()}"
        shutil.copy2(source, target / sound_file)
    data = {"$GMSound": "", "%Name": name,
        "audioGroupId": {"name": "audiogroup_default", "path": "audiogroups/audiogroup_default"},
        "bitDepth": 1, "bitRate": 128, "compression": 0, "conversionMode": 0,
        "duration": 0.0, "name": name,
        "parent": {"name": PROJECT, "path": f"{PROJECT}.yyp"},
        "preload": xml.findtext("preload") == "true", "resourceType": "GMSound",
        "resourceVersion": "2.0", "sampleRate": 44100, "soundFile": sound_file,
        "type": 0, "volume": float(xml.findtext("volume", "1"))}
    write_json(target / f"{name}.yy", data)


def script_resource(name: str) -> None:
    source = SOURCE / f"Scripts/{name}.gml"
    code = re.sub(r"^/\*\s*!scriptId=\d+\s*\*/\s*", "", source.read_text(encoding="utf-8"))
    code = modernize_code(code)
    argument_numbers = [int(number) for number in re.findall(r"\bargument(\d+)\b", code)]
    parameters = ", ".join(f"argument{index}" for index in range(max(argument_numbers, default=-1) + 1))
    target = DEST / f"scripts/{name}"
    target.mkdir(parents=True, exist_ok=True)
    (target / f"{name}.gml").write_text(f"function {name}({parameters}) {{\n{code.rstrip()}\n}}\n", encoding="utf-8")
    data = {"$GMScript": "v1", "%Name": name, "isCompatibility": False,
        "isDnD": False, "name": name, "parent": {"name": PROJECT, "path": f"{PROJECT}.yyp"},
        "resourceType": "GMScript", "resourceVersion": "2.0"}
    write_json(target / f"{name}.yy", data)


def room(name: str) -> None:
    xml = ET.parse(source_resource("Rooms", name)).getroot()
    instances = []
    order = []
    for old in xml.findall("./instances/instance"):
        instance_name = f"inst_{int(old.attrib['id']):08X}"
        object_name = old.findtext("object")
        position = old.find("position")
        instance = {"$GMRInstance": "v4", "%Name": instance_name, "colour": 4294967295,
                    "frozen": False, "hasCreationCode": False, "ignore": False,
                    "imageIndex": 0, "imageSpeed": 1.0, "inheritCode": False,
                    "inheritedItemId": None, "inheritItemSettings": False, "isDnd": False,
                    "name": instance_name, "objectId": ref("objects", object_name),
                    "properties": [], "resourceType": "GMRInstance", "resourceVersion": "2.0",
                    "rotation": 0.0, "scaleX": 1.0, "scaleY": 1.0,
                    "x": float(position.attrib["x"]), "y": float(position.attrib["y"])}
        instances.append(instance)
        order.append({"name": instance_name, "path": f"rooms/{name}/{name}.yy"})
    width = int(xml.find("size").attrib["width"])
    height = int(xml.find("size").attrib["height"])
    layers = [{"$GMRInstanceLayer": "", "%Name": "Instances",
        "depth": 0, "effectEnabled": True, "effectType": None, "gridX": 16, "gridY": 16,
        "hierarchyFrozen": False, "inheritLayerDepth": False, "inheritLayerSettings": False,
        "inheritSubLayers": True, "inheritVisibility": True, "instances": instances,
        "layers": [], "name": "Instances", "properties": [],
        "resourceType": "GMRInstanceLayer", "resourceVersion": "2.0",
        "userdefinedDepth": False, "visible": True}]
    clear_instance_name = "inst_ROOM_CLEAR"
    clear_instance = {"$GMRInstance": "v4", "%Name": clear_instance_name,
        "colour": 4294967295, "frozen": False, "hasCreationCode": False, "ignore": False,
        "imageIndex": 0, "imageSpeed": 0.0, "inheritCode": False, "inheritedItemId": None,
        "inheritItemSettings": False, "isDnd": False, "name": clear_instance_name,
        "objectId": ref("objects", "obj_room_clear"), "properties": [],
        "resourceType": "GMRInstance", "resourceVersion": "2.0", "rotation": 0.0,
        "scaleX": 1.0, "scaleY": 1.0, "x": 0.0, "y": 0.0}
    order.insert(0, {"name": clear_instance_name, "path": f"rooms/{name}/{name}.yy"})
    layers.insert(0, {"$GMRInstanceLayer": "", "%Name": "Room Clear", "depth": 2000000,
        "effectEnabled": True, "effectType": None, "gridX": 16, "gridY": 16,
        "hierarchyFrozen": False, "inheritLayerDepth": False, "inheritLayerSettings": False,
        "inheritSubLayers": True, "inheritVisibility": True, "instances": [clear_instance],
        "layers": [], "name": "Room Clear", "properties": [],
        "resourceType": "GMRInstanceLayer", "resourceVersion": "2.0",
        "userdefinedDepth": True, "visible": True})
    if CONFIG.get("background_object"):
        background_instance_name = "inst_ROOM_BACKGROUND"
        background_instance = {"$GMRInstance": "v4", "%Name": background_instance_name,
            "colour": 4294967295, "frozen": False, "hasCreationCode": False, "ignore": False,
            "imageIndex": 0, "imageSpeed": 0.0, "inheritCode": False, "inheritedItemId": None,
            "inheritItemSettings": False, "isDnd": False, "name": background_instance_name,
            "objectId": ref("objects", "obj_room_background"), "properties": [],
            "resourceType": "GMRInstance", "resourceVersion": "2.0", "rotation": 0.0,
            "scaleX": 1.0, "scaleY": 1.0, "x": 0.0, "y": 0.0}
        order.insert(0, {"name": background_instance_name, "path": f"rooms/{name}/{name}.yy"})
        layers.insert(0, {"$GMRInstanceLayer": "", "%Name": "Room Background",
            "depth": 1000000, "effectEnabled": True, "effectType": None, "gridX": 16,
            "gridY": 16, "hierarchyFrozen": False, "inheritLayerDepth": False,
            "inheritLayerSettings": False, "inheritSubLayers": True, "inheritVisibility": True,
            "instances": [background_instance], "layers": [], "name": "Room Background",
            "properties": [], "resourceType": "GMRInstanceLayer", "resourceVersion": "2.0",
            "userdefinedDepth": True, "visible": True})
    views = []
    old_views = xml.findall("./views/view")
    for old_view in old_views:
        view = old_view.find("viewInRoom")
        port = old_view.find("portOnScreen")
        following = old_view.find("objectFollowing")
        followed_name = (following.text or "").strip() if following is not None else ""
        views.append({"hborder": int(following.attrib["hBorder"]) if following is not None else 32,
            "hport": int(port.attrib["height"]), "hspeed": int(following.attrib["hSpeed"]) if following is not None else -1,
            "hview": int(view.attrib["height"]), "inherit": False,
            "objectId": ref("objects", followed_name) if followed_name else None,
            "vborder": int(following.attrib["vBorder"]) if following is not None else 32,
            "visible": old_view.findtext("visibleOnRoomStart") == "true",
            "vspeed": int(following.attrib["vSpeed"]) if following is not None else -1,
            "wport": int(port.attrib["width"]), "wview": int(view.attrib["width"]),
            "xport": int(port.attrib["x"]), "xview": int(view.attrib["x"]),
            "yport": int(port.attrib["y"]), "yview": int(view.attrib["y"])})
    if not views:
        views = [{"hborder": 32, "hport": height, "hspeed": -1, "hview": height,
                  "inherit": False, "objectId": None, "vborder": 32, "visible": False,
                  "vspeed": -1, "wport": width, "wview": width, "xport": 0, "xview": 0,
                  "yport": 0, "yview": 0} for _ in range(8)]
    creation_code = modernize_code(xml.findtext("creationCode", "")).strip()
    creation_file = f"rooms/{name}/RoomCreationCode.gml" if creation_code else ""
    if creation_code:
        code_path = DEST / creation_file
        code_path.parent.mkdir(parents=True, exist_ok=True)
        code_path.write_text(creation_code + "\n", encoding="utf-8")
    data = {"$GMRoom": "v1", "%Name": name, "creationCodeFile": creation_file, "inheritCode": False,
            "inheritCreationOrder": False, "inheritLayers": False, "instanceCreationOrder": order,
            "isDnd": False, "layers": layers, "name": name,
            "parent": {"name": PROJECT, "path": f"{PROJECT}.yyp"},
            "parentRoom": None, "physicsSettings": {"inheritPhysicsSettings": False,
                "PhysicsWorld": False, "PhysicsWorldGravityX": 0.0, "PhysicsWorldGravityY": 10.0,
                "PhysicsWorldPixToMetres": 0.1}, "resourceType": "GMRoom",
            "resourceVersion": "2.0", "roomSettings": {"Height": height,
                "inheritRoomSettings": False, "persistent": False, "Width": width},
            "sequenceId": None, "views": views, "viewSettings": {"clearDisplayBuffer": True,
                "clearViewBackground": False, "enableViews": xml.findtext("enableViews") == "true", "inheritViewSettings": False},
            "volume": 1.0}
    write_json(DEST / f"rooms/{name}/{name}.yy", data)


def custom_script_resource(name: str) -> None:
    if name != "dylu_d3d_compat":
        raise ValueError(f"Unknown custom script: {name}")
    target = DEST / "scripts" / name
    target.mkdir(parents=True, exist_ok=True)
    write_json(target / f"{name}.yy", {
        "$GMScript": "v1", "%Name": name, "isCompatibility": False,
        "isDnD": False, "name": name,
        "parent": {"name": PROJECT, "path": f"{PROJECT}.yyp"},
        "resourceType": "GMScript", "resourceVersion": "2.0",
    })
    (target / f"{name}.gml").write_text(r'''function dylu_batch_begin(_texture) {
    if (global.__dylu_batch_active) dylu_batch_end();
    vertex_format_begin();
    vertex_format_add_position_3d();
    vertex_format_add_color();
    vertex_format_add_texcoord();
    global.__dylu_format = vertex_format_end();
    global.__dylu_buffer = vertex_create_buffer();
    global.__dylu_texture = _texture;
    global.__dylu_uv = texture_get_uvs(_texture);
    vertex_begin(global.__dylu_buffer, global.__dylu_format);
    global.__dylu_batch_active = true;
}

function dylu_vertex(_x, _y, _z, _u, _v) {
    vertex_position_3d(global.__dylu_buffer, _x, _y, _z);
    vertex_color(global.__dylu_buffer, c_white, 1);
    vertex_texcoord(global.__dylu_buffer, _u, _v);
}

function dylu_quad(_x1, _y1, _z1, _x2, _y2, _z2, _x3, _y3, _z3, _x4, _y4, _z4, _flip_u, _flip_v) {
    var _uv = global.__dylu_uv;
    var _u0 = _flip_u ? _uv[2] : _uv[0];
    var _u1 = _flip_u ? _uv[0] : _uv[2];
    var _v0 = _flip_v ? _uv[3] : _uv[1];
    var _v1 = _flip_v ? _uv[1] : _uv[3];
    dylu_vertex(_x1,_y1,_z1,_u0,_v0); dylu_vertex(_x2,_y2,_z2,_u1,_v0); dylu_vertex(_x3,_y3,_z3,_u1,_v1);
    dylu_vertex(_x1,_y1,_z1,_u0,_v0); dylu_vertex(_x3,_y3,_z3,_u1,_v1); dylu_vertex(_x4,_y4,_z4,_u0,_v1);
}

function dylu_batch_end() {
    if (!global.__dylu_batch_active) return;
    vertex_end(global.__dylu_buffer);
    vertex_submit(global.__dylu_buffer, pr_trianglelist, global.__dylu_texture);
    vertex_delete_buffer(global.__dylu_buffer);
    vertex_format_delete(global.__dylu_format);
    global.__dylu_batch_active = false;
}

function d3d_start() {
    global.__dylu_batch_active = false;
    gpu_set_ztestenable(true);
    gpu_set_zwriteenable(true);
}
function d3d_set_hidden(_enabled) { gpu_set_ztestenable(_enabled); gpu_set_zwriteenable(_enabled); }
function d3d_set_lighting(_enabled) { }
function d3d_set_culling(_enabled) { }
function d3d_set_fog(_enabled, _color, _start, _end) { gpu_set_fog(_enabled, _color, _start, _end); }
function d3d_set_projection(_ex,_ey,_ez,_tx,_ty,_tz,_ux,_uy,_uz) {
    matrix_set(matrix_view, matrix_build_lookat(_ex,_ey,_ez,_tx,_ty,_tz,_ux,_uy,_uz));
    matrix_set(matrix_projection, matrix_build_projection_perspective_fov(60, 320/240, 1, 2048));
}

function d3d_draw_floor(_x1,_y1,_z1,_x2,_y2,_z2,_texture,_hrepeat,_vrepeat) {
    var _own = !global.__dylu_batch_active;
    if (_own) dylu_batch_begin(_texture);
    var _hc = max(1, ceil(abs(_hrepeat))), _vc = max(1, ceil(abs(_vrepeat)));
    for (var _yy=0; _yy<_vc; _yy++) for (var _xx=0; _xx<_hc; _xx++) {
        var _ax=lerp(_x1,_x2,_xx/_hc), _bx=lerp(_x1,_x2,(_xx+1)/_hc);
        var _ay=lerp(_y1,_y2,_yy/_vc), _by=lerp(_y1,_y2,(_yy+1)/_vc);
        var _az=lerp(_z1,_z2,(_xx+_yy)/(_hc+_vc)), _bz=lerp(_z1,_z2,(_xx+1+_yy)/(_hc+_vc));
        var _cz=lerp(_z1,_z2,(_xx+1+_yy+1)/(_hc+_vc)), _dz=lerp(_z1,_z2,(_xx+_yy+1)/(_hc+_vc));
        dylu_quad(_ax,_ay,_az,_bx,_ay,_bz,_bx,_by,_cz,_ax,_by,_dz,_hrepeat<0,_vrepeat<0);
    }
    if (_own) dylu_batch_end();
}

function d3d_draw_wall(_x1,_y1,_z1,_x2,_y2,_z2,_texture,_hrepeat,_vrepeat) {
    var _own = !global.__dylu_batch_active;
    if (_own) dylu_batch_begin(_texture);
    var _hc=max(1,ceil(abs(_hrepeat))), _vc=max(1,ceil(abs(_vrepeat)));
    for (var _yy=0; _yy<_vc; _yy++) for (var _xx=0; _xx<_hc; _xx++) {
        var _u0=_xx/_hc, _u1=(_xx+1)/_hc, _v0=_yy/_vc, _v1=(_yy+1)/_vc;
        var _ax=lerp(_x1,_x2,_u0), _ay=lerp(_y1,_y2,_u0), _bx=lerp(_x1,_x2,_u1), _by=lerp(_y1,_y2,_u1);
        var _za=lerp(_z1,_z2,_v0), _zb=lerp(_z1,_z2,_v1);
        dylu_quad(_ax,_ay,_za,_bx,_by,_za,_bx,_by,_zb,_ax,_ay,_zb,_hrepeat<0,_vrepeat<0);
    }
    if (_own) dylu_batch_end();
}
''', encoding="utf-8")


def main() -> None:
    project_file = DEST / f"{PROJECT}.yyp"
    if not project_file.exists():
        DEST.mkdir(parents=True, exist_ok=True)
        template = json.loads((ROOT / "modern/tembo/tembo.yyp").read_text(encoding="utf-8"))
        template["%Name"] = PROJECT
        template["name"] = PROJECT
        template["resources"] = []
        template["RoomOrderNodes"] = []
        write_json(project_file, template)
    for name in CONFIG["sprites"]:
        sprite(name)
    background = CONFIG.get("background")
    if background:
        background_image = compose_room_background() if CONFIG.get("compose_tiles") else SOURCE / f"Backgrounds/{background}.png"
        sprite(f"spr_{background}", [background_image])
    for room_name in CONFIG.get("compose_room_tiles", ()):
        sprite(f"spr_room_{room_name}", [compose_room_background(room_name)])
    for extra_background in CONFIG.get("extra_backgrounds", ()):
        sprite(f"spr_{extra_background}", [SOURCE / f"Backgrounds/{extra_background}.png"])
    for name in CONFIG["objects"]:
        object_resource(name)
    persistent_surface_fixes()
    if CONFIG.get("background_object"):
        flat_background_object()
    for name in CONFIG["fonts"]:
        font_resource(name)
    for name in CONFIG.get("sounds", ()):
        sound_resource(name)
    for name in CONFIG.get("scripts", ()):
        script_resource(name)
    for name in CONFIG.get("custom_scripts", ()):
        custom_script_resource(name)
    room_names = CONFIG.get("rooms", (CONFIG.get("room"),))
    room_clear_object(room_names)
    for name in room_names:
        room(name)
    project_text = project_file.read_text(encoding="utf-8")
    project = json.loads(re.sub(r",(?=\s*[}\]])", "", project_text))
    resource_refs = ([ref("sprites", name) for name in CONFIG["sprites"]] +
                     ([ref("sprites", f"spr_{background}")] if background else []) +
                     [ref("sprites", f"spr_room_{name}") for name in CONFIG.get("compose_room_tiles", ())] +
                     [ref("sprites", f"spr_{name}") for name in CONFIG.get("extra_backgrounds", ())] +
                     [ref("objects", name) for name in CONFIG["objects"]] +
                     ([ref("objects", "obj_room_background")] if CONFIG.get("background_object") else []) +
                     [ref("objects", "obj_room_clear")] +
                     [ref("fonts", name) for name in CONFIG["fonts"]] +
                     [ref("fonts", name) for name in CONFIG.get("existing_fonts", ())] +
                     [ref("sounds", name) for name in CONFIG.get("sounds", ())] +
                     [ref("scripts", name) for name in CONFIG.get("scripts", ())] +
                     [ref("scripts", name) for name in CONFIG.get("custom_scripts", ())] +
                     [ref("rooms", name) for name in room_names])
    project["resources"] = [{"id": resource} for resource in resource_refs]
    project["RoomOrderNodes"] = [{"roomId": ref("rooms", name)} for name in room_names]
    write_json(project_file, project)
    print(f"Generated pilot project: {project_file}")


if __name__ == "__main__":
    main()
