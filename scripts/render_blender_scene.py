#!/usr/bin/env python3
"""Render a SceneBuilder JSON scene inside Blender.

Run with:
  Blender --background --python scripts/render_blender_scene.py -- --scene-json ... --output ...
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector


MATERIAL_COLORS = {
    "wood": (0.55, 0.32, 0.16, 1.0),
    "metal": (0.56, 0.58, 0.62, 1.0),
    "ceramic": (0.92, 0.90, 0.84, 1.0),
    "glass": (0.70, 0.88, 0.95, 0.62),
    "fabric": (0.48, 0.54, 0.64, 1.0),
    "plastic": (0.16, 0.18, 0.22, 1.0),
    "paper": (0.88, 0.84, 0.74, 1.0),
    "stone": (0.50, 0.49, 0.46, 1.0),
    "marble": (0.82, 0.80, 0.76, 1.0),
    "leather": (0.35, 0.18, 0.10, 1.0),
    "bronze": (0.62, 0.37, 0.18, 1.0),
    "clay": (0.58, 0.31, 0.20, 1.0),
    "leafy": (0.23, 0.58, 0.34, 1.0),
    "matte": (0.45, 0.55, 0.70, 1.0),
    "cardboard": (0.64, 0.45, 0.25, 1.0),
    "rubber": (0.04, 0.045, 0.05, 1.0),
}

NAMED_COLORS = {
    "red": (0.85, 0.18, 0.18, 1.0),
    "blue": (0.16, 0.34, 0.80, 1.0),
    "green": (0.20, 0.58, 0.30, 1.0),
    "yellow": (0.95, 0.72, 0.14, 1.0),
    "purple": (0.50, 0.24, 0.73, 1.0),
    "black": (0.03, 0.04, 0.05, 1.0),
    "white": (0.92, 0.92, 0.88, 1.0),
    "gray": (0.55, 0.58, 0.62, 1.0),
    "orange": (0.90, 0.45, 0.16, 1.0),
    "pink": (0.90, 0.42, 0.62, 1.0),
}


def parse_args() -> argparse.Namespace:
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1 :]
    else:
        argv = []
    parser = argparse.ArgumentParser()
    parser.add_argument("--scene-json", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--resolution", default="1024x768")
    parser.add_argument("--engine", default="BLENDER_WORKBENCH")
    return parser.parse_args(argv)


def make_material(name: str, color: tuple[float, float, float, float]) -> bpy.types.Material:
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.diffuse_color = color
    return mat


def material_for(obj: dict) -> bpy.types.Material:
    color_name = obj.get("color")
    if color_name in NAMED_COLORS:
        return make_material(f"color_{color_name}", NAMED_COLORS[color_name])
    material = (obj.get("material") or "matte").split()[0]
    return make_material(material, MATERIAL_COLORS.get(material, MATERIAL_COLORS["matte"]))


SEMANTIC_KIND_BY_ID = (
    ("star_map", "map"),
    ("map", "map"),
    ("passport", "paper_card"),
    ("ticket", "paper_card"),
    ("clipboard", "clipboard"),
    ("menu_card", "paper_card"),
    ("plaque", "plaque"),
    ("clay_tablet", "tablet"),
    ("chess_board", "chess_board"),
    ("cutting_board", "cutting_board"),
    ("compass", "compass"),
    ("sensor_module", "sensor_module"),
    ("battery_pack", "battery_pack"),
    ("toolbox", "toolbox"),
    ("telescope", "telescope"),
    ("robot_arm", "robot_arm"),
    ("microscope", "microscope"),
    ("test_tube_rack", "test_tube_rack"),
    ("beaker", "beaker"),
    ("tripod", "tripod"),
    ("light_stand", "light_stand"),
    ("reflector", "reflector"),
    ("violin", "violin"),
    ("paint_palette", "paint_palette"),
    ("palette", "paint_palette"),
    ("clay_sculpture", "sculpture"),
    ("sculpture", "sculpture"),
    ("statue", "statue"),
    ("wrench", "tool"),
    ("drill", "drill"),
    ("safety_helmet", "helmet"),
    ("helmet", "helmet"),
    ("spray_bottle", "spray_bottle"),
    ("seed_tray", "seed_tray"),
    ("watering_can", "watering_can"),
    ("fabric_roll", "roll"),
    ("needle_box", "small_box"),
    ("scissors", "scissors"),
    ("scissor", "scissors"),
    ("sandwich", "sandwich"),
    ("basket", "basket"),
    ("white_king", "chess_piece"),
    ("black_queen", "chess_piece"),
    ("king", "chess_piece"),
    ("queen", "chess_piece"),
    ("cardboard_box", "cardboard_box"),
    ("barcode_scanner", "scanner"),
    ("tape_roll", "tape_roll"),
    ("label_printer", "printer"),
    ("toy_car", "toy_car"),
    ("block_tower", "block_tower"),
    ("robot_toy", "robot_toy"),
    ("teapot", "teapot"),
    ("bamboo_tray", "tray"),
    ("suitcase", "suitcase"),
    ("drone", "drone"),
    ("screwdriver", "screwdriver"),
    ("fish_statue", "fish_statue"),
    ("coral_model", "coral"),
    ("cake", "cake"),
    ("rolling_pin", "roll"),
    ("stone_artifact", "artifact"),
    ("artifact", "artifact"),
    ("radio", "radio"),
    ("soap_dispenser", "soap_dispenser"),
    ("brush", "brush"),
    ("jewelry_box", "small_box"),
    ("shoe_rack", "shoe_rack"),
    ("umbrella_stand", "umbrella_stand"),
    ("backpack", "backpack"),
    ("key_bowl", "bowl"),
    ("stethoscope", "stethoscope"),
    ("pill_bottle", "pill_bottle"),
    ("water_bottle", "bottle"),
    ("bottle", "bottle"),
    ("towel", "towel"),
    ("perfume_bottle", "bottle"),
    ("monitor", "monitor"),
    ("keyboard", "keyboard"),
    ("mouse", "mouse"),
    ("phone", "phone"),
    ("speaker", "speaker"),
    ("camera", "camera"),
    ("microphone", "microphone"),
    ("printer", "printer"),
    ("vase", "vase"),
    ("bowl", "bowl"),
    ("plate", "plate"),
    ("clock", "clock"),
    ("magnifying_glass", "magnifying_glass"),
    ("globe", "globe"),
    ("mirror", "mirror"),
    ("piano", "piano"),
    ("easel", "easel"),
    ("canvas", "canvas"),
    ("rug", "rug"),
)


VISUAL_SIZE_BY_KIND = {
    "map": (0.95, 0.65, 0.05),
    "paper_card": (0.55, 0.32, 0.05),
    "clipboard": (0.78, 0.52, 0.06),
    "plaque": (0.58, 0.32, 0.06),
    "tablet": (0.62, 0.42, 0.09),
    "chess_board": (0.86, 0.86, 0.08),
    "cutting_board": (0.85, 0.50, 0.07),
    "compass": (0.42, 0.42, 0.10),
    "magnifying_glass": (0.60, 0.34, 0.10),
    "globe": (0.58, 0.58, 0.78),
    "monitor": (1.10, 0.22, 0.82),
    "keyboard": (1.00, 0.32, 0.08),
    "mouse": (0.32, 0.22, 0.12),
    "phone": (0.38, 0.68, 0.06),
    "sensor_module": (0.50, 0.36, 0.20),
    "battery_pack": (0.62, 0.38, 0.30),
    "toolbox": (0.95, 0.45, 0.42),
    "telescope": (0.95, 0.35, 0.35),
    "robot_arm": (0.55, 0.55, 1.20),
    "camera": (0.55, 0.35, 0.35),
    "scanner": (0.55, 0.26, 0.22),
    "radio": (0.62, 0.32, 0.42),
    "printer": (0.70, 0.48, 0.32),
    "speaker": (0.45, 0.35, 0.70),
    "microscope": (0.62, 0.46, 0.86),
    "test_tube_rack": (0.75, 0.32, 0.42),
    "tripod": (0.70, 0.70, 1.05),
    "light_stand": (0.70, 0.70, 1.20),
    "reflector": (0.72, 0.18, 0.72),
    "bottle": (0.32, 0.32, 0.80),
    "spray_bottle": (0.36, 0.30, 0.72),
    "pill_bottle": (0.28, 0.28, 0.50),
    "soap_dispenser": (0.32, 0.26, 0.62),
    "vase": (0.42, 0.42, 0.90),
    "toy_car": (0.70, 0.34, 0.28),
    "drone": (0.78, 0.78, 0.20),
    "robot_toy": (0.42, 0.34, 0.70),
    "block_tower": (0.55, 0.55, 0.95),
    "teapot": (0.62, 0.46, 0.42),
    "watering_can": (0.75, 0.45, 0.48),
    "tray": (0.82, 0.48, 0.10),
    "seed_tray": (0.85, 0.48, 0.14),
    "paint_palette": (0.55, 0.42, 0.06),
    "helmet": (0.62, 0.48, 0.38),
    "basket": (0.72, 0.52, 0.42),
    "tool": (0.72, 0.18, 0.10),
    "drill": (0.70, 0.38, 0.44),
    "scissors": (0.62, 0.30, 0.08),
    "screwdriver": (0.70, 0.14, 0.12),
    "brush": (0.62, 0.16, 0.10),
    "roll": (0.78, 0.18, 0.18),
    "sandwich": (0.58, 0.42, 0.20),
    "cake": (0.62, 0.62, 0.36),
    "chess_piece": (0.24, 0.24, 0.55),
    "sculpture": (0.46, 0.46, 0.72),
    "statue": (0.52, 0.52, 0.90),
    "artifact": (0.46, 0.36, 0.32),
    "fish_statue": (0.55, 0.35, 0.34),
    "coral": (0.46, 0.42, 0.58),
    "piano": (2.20, 0.85, 0.95),
    "rug": (2.20, 1.35, 0.04),
    "towel": (0.86, 0.42, 0.05),
    "violin": (0.95, 0.34, 0.22),
    "easel": (0.85, 0.35, 1.60),
    "microphone": (0.28, 0.28, 0.75),
    "umbrella_stand": (0.45, 0.45, 0.95),
    "stethoscope": (0.62, 0.46, 0.16),
    "small_box": (0.42, 0.32, 0.24),
    "cardboard_box": (0.68, 0.52, 0.42),
    "suitcase": (0.82, 0.45, 0.58),
    "backpack": (0.55, 0.32, 0.62),
}


def semantic_kind(obj: dict) -> str:
    object_id = str(obj.get("id", "")).lower().replace("-", "_")
    object_type = str(obj.get("type", "")).lower().replace("-", "_")
    haystack = f"{object_id} {object_type}"
    for needle, kind in SEMANTIC_KIND_BY_ID:
        if needle in haystack:
            return kind
    return object_type


def part_name(obj: dict, suffix: str) -> str:
    return f"{obj['id']}_{suffix}"


def soften(bobj: bpy.types.Object, amount: float = 0.015) -> bpy.types.Object:
    if amount <= 0:
        return bobj
    try:
        bevel = bobj.modifiers.new("soft_edges", "BEVEL")
        bevel.width = amount
        bevel.segments = 2
        bobj.modifiers.new("weighted_normals", "WEIGHTED_NORMAL")
    except RuntimeError:
        pass
    return bobj


def reset_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()


def add_box(name: str, loc, size, mat: bpy.types.Material, rotation=(0.0, 0.0, 0.0), bevel: float = 0.015) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc, rotation=rotation)
    bobj = bpy.context.object
    bobj.name = name
    bobj.dimensions = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bobj.data.materials.append(mat)
    return soften(bobj, bevel)


def add_cylinder(
    name: str,
    loc,
    size,
    mat: bpy.types.Material,
    vertices: int = 32,
    rotation=(0.0, 0.0, 0.0),
    bevel: float = 0.01,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=0.5, depth=1.0, location=loc, rotation=rotation)
    bobj = bpy.context.object
    bobj.name = name
    bobj.dimensions = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bobj.data.materials.append(mat)
    return soften(bobj, bevel)


def add_sphere(name: str, loc, size, mat: bpy.types.Material) -> bpy.types.Object:
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=0.5, location=loc)
    bobj = bpy.context.object
    bobj.name = name
    bobj.dimensions = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bobj.data.materials.append(mat)
    return bobj


def add_cone(name: str, loc, size, mat: bpy.types.Material, rotation=(0.0, 0.0, 0.0)) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cone_add(vertices=32, radius1=0.5, depth=1.0, location=loc, rotation=rotation)
    bobj = bpy.context.object
    bobj.name = name
    bobj.dimensions = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bobj.data.materials.append(mat)
    return soften(bobj, 0.01)


def add_torus(name: str, loc, major_radius: float, minor_radius: float, mat: bpy.types.Material, rotation=(0.0, 0.0, 0.0)) -> bpy.types.Object:
    bpy.ops.mesh.primitive_torus_add(
        major_radius=major_radius,
        minor_radius=minor_radius,
        major_segments=32,
        minor_segments=8,
        location=loc,
        rotation=rotation,
    )
    bobj = bpy.context.object
    bobj.name = name
    bobj.data.materials.append(mat)
    return bobj


def add_object(obj: dict) -> list[bpy.types.Object]:
    loc = tuple(obj["location"])
    size = tuple(obj["size"])
    obj_type = obj.get("type", "")
    shape = obj.get("shape", "box")
    kind = semantic_kind(obj)
    mat = material_for(obj)
    x, y, z = loc
    sx, sy, sz = size
    if kind in VISUAL_SIZE_BY_KIND and kind != obj_type:
        old_bottom = z - sz / 2
        sx, sy, sz = VISUAL_SIZE_BY_KIND[kind]
        z = old_bottom + sz / 2
        loc = (x, y, z)

    if kind in {"table", "desk", "low_table"}:
        wood = mat
        edge = make_material("table_edge", (0.34, 0.22, 0.13, 1.0))
        return [
            add_box(part_name(obj, "top"), loc, size, wood, bevel=0.025),
            add_box(part_name(obj, "front_edge"), (x, y - sy * 0.48, z + sz * 0.08), (sx, 0.045, sz * 0.28), edge, bevel=0.008),
            add_box(part_name(obj, "back_edge"), (x, y + sy * 0.48, z + sz * 0.08), (sx, 0.045, sz * 0.28), edge, bevel=0.008),
        ]

    if kind == "laptop":
        base_z = z - sz * 0.15
        screen_z = z + sz * 1.65
        dark = make_material("laptop_dark", (0.08, 0.10, 0.13, 1.0))
        screen = make_material("screen_blue", (0.13, 0.25, 0.38, 1.0))
        return [
            add_box(part_name(obj, "base"), (x, y, base_z), (sx, sy, max(0.06, sz * 0.55)), dark),
            add_box(part_name(obj, "screen"), (x, y + sy * 0.38, screen_z), (sx, 0.06, max(0.55, sx * 0.55)), screen),
        ]

    if kind == "monitor":
        dark = make_material("monitor_dark", (0.07, 0.08, 0.10, 1.0))
        screen = make_material("monitor_screen", (0.09, 0.20, 0.34, 1.0))
        metal = make_material("monitor_stand", (0.45, 0.47, 0.50, 1.0))
        bottom = z - sz / 2
        return [
            add_box(part_name(obj, "panel"), (x, y, z + sz * 0.16), (sx, max(0.055, sy * 0.24), sz * 0.92), dark),
            add_box(part_name(obj, "screen"), (x, y - sy * 0.13, z + sz * 0.16), (sx * 0.84, 0.035, sz * 0.68), screen, bevel=0.006),
            add_cylinder(part_name(obj, "neck"), (x, y, bottom + sz * 0.24), (sx * 0.10, sy * 0.10, sz * 0.44), metal),
            add_box(part_name(obj, "foot"), (x, y, bottom + sz * 0.06), (sx * 0.52, sy * 0.55, sz * 0.10), metal),
        ]

    if kind == "lamp":
        metal = make_material("lamp_metal", (0.52, 0.56, 0.60, 1.0))
        shade = make_material("lamp_warm_shade", (1.0, 0.78, 0.34, 1.0))
        bottom = z - sz / 2
        return [
            add_cylinder(part_name(obj, "base"), (x, y, bottom + 0.035), (sx * 0.95, sy * 0.95, 0.07), metal),
            add_cylinder(part_name(obj, "pole"), (x, y, bottom + sz * 0.48), (sx * 0.18, sy * 0.18, sz * 0.78), metal),
            add_cone(part_name(obj, "shade"), (x, y, bottom + sz * 0.88), (sx * 1.25, sy * 1.25, sz * 0.24), shade),
        ]

    if kind == "plant":
        pot = make_material("plant_pot", (0.50, 0.28, 0.18, 1.0))
        leaf = make_material("plant_leaf", (0.18, 0.55, 0.28, 1.0))
        bottom = z - sz / 2
        return [
            add_cylinder(part_name(obj, "pot"), (x, y, bottom + sz * 0.22), (sx * 0.75, sy * 0.75, sz * 0.44), pot),
            add_sphere(part_name(obj, "leaf_a"), (x, y, bottom + sz * 0.70), (sx * 0.92, sy * 0.92, sz * 0.46), leaf),
            add_sphere(part_name(obj, "leaf_b"), (x - sx * 0.18, y + sy * 0.12, bottom + sz * 0.83), (sx * 0.55, sy * 0.55, sz * 0.32), leaf),
            add_sphere(part_name(obj, "leaf_c"), (x + sx * 0.18, y - sy * 0.10, bottom + sz * 0.82), (sx * 0.55, sy * 0.55, sz * 0.32), leaf),
        ]

    if kind in {"cup", "beaker"}:
        ceramic = mat
        bottom = z - sz / 2
        cup = add_cylinder(part_name(obj, "body"), (x, y, bottom + sz * 0.50), (sx, sy, sz), ceramic)
        if kind == "beaker":
            lip = add_torus(part_name(obj, "rim"), (x, y, bottom + sz * 0.98), sx * 0.28, sx * 0.025, ceramic)
            return [cup, lip]
        bpy.ops.mesh.primitive_torus_add(
            major_radius=max(0.055, sx * 0.22),
            minor_radius=max(0.015, sx * 0.045),
            major_segments=24,
            minor_segments=8,
            location=(x + sx * 0.47, y, z + sz * 0.03),
            rotation=(math.pi / 2, 0, 0),
        )
        handle = bpy.context.object
        handle.name = part_name(obj, "handle")
        handle.scale.y = 0.72
        handle.data.materials.append(ceramic)
        return [cup, handle]

    if kind in {"book", "paper_card", "map", "clipboard", "tablet", "canvas", "cutting_board", "plaque"}:
        paper = mat if kind in {"book", "cutting_board", "tablet"} else make_material("paper_item", (0.90, 0.86, 0.70, 1.0))
        if kind == "plaque":
            paper = make_material("bronze_plaque", MATERIAL_COLORS["bronze"])
        accent = make_material("paper_lines", (0.20, 0.26, 0.32, 1.0))
        thin_z = max(0.035, sz * 0.38)
        parts = [add_box(part_name(obj, "body"), (x, y, z), (sx, sy, thin_z), paper, bevel=0.006)]
        if kind == "book":
            parts.append(add_box(part_name(obj, "spine"), (x - sx * 0.45, y, z + thin_z * 0.08), (sx * 0.05, sy, thin_z * 1.15), accent, bevel=0.003))
        elif kind == "map":
            parts.append(add_box(part_name(obj, "fold_x"), (x, y, z + thin_z * 0.55), (0.018, sy * 0.92, 0.012), accent, bevel=0.001))
            parts.append(add_box(part_name(obj, "fold_y"), (x, y, z + thin_z * 0.58), (sx * 0.92, 0.018, 0.012), accent, bevel=0.001))
        elif kind == "clipboard":
            parts.append(add_box(part_name(obj, "clip"), (x, y + sy * 0.42, z + thin_z * 0.70), (sx * 0.32, sy * 0.08, thin_z * 0.25), make_material("clip_metal", (0.55, 0.57, 0.60, 1.0)), bevel=0.003))
        elif kind == "plaque":
            parts.append(add_box(part_name(obj, "engraving"), (x, y, z + thin_z * 0.58), (sx * 0.68, sy * 0.08, 0.012), accent, bevel=0.001))
        return parts

    if kind == "chess_board":
        base = add_box(part_name(obj, "base"), loc, (sx, sy, max(0.04, sz * 0.35)), make_material("chess_dark", (0.10, 0.08, 0.06, 1.0)), bevel=0.006)
        parts = [base]
        tile_mat = make_material("chess_light", (0.86, 0.80, 0.64, 1.0))
        for ix in range(4):
            for iy in range(4):
                tx = x - sx * 0.36 + ix * sx * 0.24
                ty = y - sy * 0.36 + iy * sy * 0.24
                parts.append(add_box(part_name(obj, f"tile_{ix}_{iy}"), (tx, ty, z + sz * 0.24), (sx * 0.12, sy * 0.12, 0.01), tile_mat, bevel=0.001))
        return parts

    if kind in {"keyboard", "phone", "mouse"}:
        dark = make_material("small_device_dark", (0.06, 0.07, 0.08, 1.0))
        accent = make_material("small_device_accent", (0.22, 0.30, 0.38, 1.0))
        if kind == "keyboard":
            parts = [add_box(part_name(obj, "base"), loc, size, dark, bevel=0.008)]
            for i in range(5):
                parts.append(add_box(part_name(obj, f"key_{i}"), (x - sx * 0.32 + i * sx * 0.16, y - sy * 0.10, z + sz * 0.58), (sx * 0.10, sy * 0.16, sz * 0.12), accent, bevel=0.002))
            return parts
        if kind == "phone":
            return [
                add_box(part_name(obj, "body"), loc, size, dark, bevel=0.018),
                add_box(part_name(obj, "screen"), (x, y - sy * 0.02, z + sz * 0.54), (sx * 0.78, sy * 0.82, max(0.012, sz * 0.12)), accent, bevel=0.005),
            ]
        return [
            add_sphere(part_name(obj, "body"), (x, y, z), (sx, sy, sz * 0.82), dark),
            add_box(part_name(obj, "split"), (x, y - sy * 0.12, z + sz * 0.36), (sx * 0.06, sy * 0.44, sz * 0.04), accent, bevel=0.001),
        ]

    if kind in {"sensor_module", "microphone", "umbrella_stand", "stethoscope"}:
        metal = make_material("instrument_metal", (0.58, 0.60, 0.62, 1.0))
        dark = make_material("instrument_dark", (0.06, 0.07, 0.08, 1.0))
        if kind == "sensor_module":
            return [
                add_box(part_name(obj, "board"), loc, (sx, sy, sz * 0.32), make_material("sensor_board", (0.08, 0.34, 0.22, 1.0)), bevel=0.008),
                add_cylinder(part_name(obj, "lens"), (x, y - sy * 0.26, z + sz * 0.08), (sx * 0.36, sx * 0.36, sy * 0.18), dark, rotation=(math.pi / 2, 0, 0)),
                add_box(part_name(obj, "chip"), (x + sx * 0.24, y + sy * 0.12, z + sz * 0.18), (sx * 0.24, sy * 0.20, sz * 0.12), dark, bevel=0.003),
            ]
        if kind == "microphone":
            bottom = z - sz / 2
            return [
                add_cylinder(part_name(obj, "stand"), (x, y, bottom + sz * 0.40), (sx * 0.16, sy * 0.16, sz * 0.62), metal),
                add_sphere(part_name(obj, "head"), (x, y, bottom + sz * 0.78), (sx * 0.54, sy * 0.54, sz * 0.34), dark),
                add_cylinder(part_name(obj, "base"), (x, y, bottom + sz * 0.08), (sx * 0.70, sy * 0.70, sz * 0.12), metal),
            ]
        if kind == "umbrella_stand":
            bottom = z - sz / 2
            return [
                add_cylinder(part_name(obj, "stand"), (x, y, bottom + sz * 0.35), (sx * 0.72, sy * 0.72, sz * 0.70), metal),
                add_cone(part_name(obj, "umbrella_a"), (x - sx * 0.12, y, bottom + sz * 0.82), (sx * 0.22, sy * 0.22, sz * 0.60), make_material("umbrella_blue", NAMED_COLORS["blue"]), rotation=(0, math.radians(8), 0)),
                add_cone(part_name(obj, "umbrella_b"), (x + sx * 0.12, y, bottom + sz * 0.76), (sx * 0.22, sy * 0.22, sz * 0.50), make_material("umbrella_red", NAMED_COLORS["red"]), rotation=(0, math.radians(-8), 0)),
            ]
        return [
            add_torus(part_name(obj, "tube"), (x, y, z + sz * 0.08), sx * 0.32, sx * 0.018, dark, rotation=(math.pi / 2, 0, 0)),
            add_cylinder(part_name(obj, "chestpiece"), (x + sx * 0.22, y - sy * 0.25, z - sz * 0.18), (sx * 0.22, sx * 0.22, sz * 0.08), metal),
            add_cylinder(part_name(obj, "earpiece"), (x - sx * 0.28, y + sy * 0.18, z + sz * 0.20), (sx * 0.10, sx * 0.10, sz * 0.28), metal),
        ]

    if kind in {"violin", "easel"}:
        wood = make_material("warm_wood", (0.50, 0.28, 0.12, 1.0))
        dark = make_material("string_dark", (0.06, 0.05, 0.04, 1.0))
        if kind == "violin":
            return [
                add_sphere(part_name(obj, "lower_body"), (x - sx * 0.10, y, z), (sx * 0.46, sy * 0.34, sz * 0.32), wood),
                add_sphere(part_name(obj, "upper_body"), (x + sx * 0.14, y, z + sz * 0.03), (sx * 0.34, sy * 0.28, sz * 0.25), wood),
                add_box(part_name(obj, "neck"), (x + sx * 0.44, y, z + sz * 0.08), (sx * 0.42, sy * 0.08, sz * 0.08), dark, rotation=(0, 0, math.radians(5)), bevel=0.003),
                add_box(part_name(obj, "strings"), (x + sx * 0.12, y - sy * 0.03, z + sz * 0.20), (sx * 0.82, sy * 0.025, sz * 0.035), dark, bevel=0.001),
            ]
        bottom = z - sz / 2
        return [
            add_box(part_name(obj, "left_leg"), (x - sx * 0.22, y, bottom + sz * 0.48), (sx * 0.08, sy * 0.08, sz * 0.95), wood, rotation=(0, math.radians(-10), 0), bevel=0.003),
            add_box(part_name(obj, "right_leg"), (x + sx * 0.22, y, bottom + sz * 0.48), (sx * 0.08, sy * 0.08, sz * 0.95), wood, rotation=(0, math.radians(10), 0), bevel=0.003),
            add_box(part_name(obj, "crossbar"), (x, y, bottom + sz * 0.52), (sx * 0.78, sy * 0.08, sz * 0.08), wood, bevel=0.003),
        ]

    if kind == "chair":
        fabric = mat
        bottom = z - sz / 2
        return [
            add_box(part_name(obj, "seat"), (x, y, bottom + sz * 0.42), (sx, sy, sz * 0.18), fabric),
            add_box(part_name(obj, "back"), (x, y + sy * 0.42, bottom + sz * 0.72), (sx, sy * 0.16, sz * 0.55), fabric),
            add_box(part_name(obj, "leg_fl"), (x - sx * 0.35, y - sy * 0.35, bottom + sz * 0.20), (0.07, 0.07, sz * 0.40), fabric),
            add_box(part_name(obj, "leg_fr"), (x + sx * 0.35, y - sy * 0.35, bottom + sz * 0.20), (0.07, 0.07, sz * 0.40), fabric),
        ]

    if kind == "sofa":
        fabric = mat
        bottom = z - sz / 2
        return [
            add_box(part_name(obj, "seat"), (x, y, bottom + sz * 0.38), (sx, sy, sz * 0.35), fabric),
            add_box(part_name(obj, "back"), (x, y + sy * 0.45, bottom + sz * 0.68), (sx, sy * 0.18, sz * 0.55), fabric),
            add_box(part_name(obj, "left_arm"), (x - sx * 0.48, y, bottom + sz * 0.55), (sx * 0.08, sy, sz * 0.48), fabric),
            add_box(part_name(obj, "right_arm"), (x + sx * 0.48, y, bottom + sz * 0.55), (sx * 0.08, sy, sz * 0.48), fabric),
        ]

    if kind == "bed":
        fabric = mat
        bottom = z - sz / 2
        return [
            add_box(part_name(obj, "frame"), (x, y, bottom + sz * 0.28), (sx, sy, sz * 0.35), make_material("bed_frame", (0.42, 0.28, 0.20, 1.0))),
            add_box(part_name(obj, "mattress"), (x, y, bottom + sz * 0.58), (sx * 0.94, sy * 0.92, sz * 0.24), fabric),
            add_box(part_name(obj, "pillow"), (x, y + sy * 0.32, bottom + sz * 0.78), (sx * 0.42, sy * 0.20, sz * 0.16), make_material("pillow", (0.92, 0.90, 0.84, 1.0))),
        ]

    if kind in {"shelf", "test_tube_rack", "shoe_rack"}:
        wood = mat
        parts = [add_box(part_name(obj, "frame"), loc, size, wood)]
        for i in range(3):
            parts.append(add_box(part_name(obj, f"slot_{i}"), (x, y - sy * 0.03, z - sz * 0.28 + i * sz * 0.28), (sx * 0.86, sy * 0.12, 0.045), make_material("shelf_shadow", (0.25, 0.18, 0.13, 1.0))))
        if kind == "test_tube_rack":
            glass = make_material("test_tube_glass", MATERIAL_COLORS["glass"])
            for i in range(3):
                parts.append(add_cylinder(part_name(obj, f"tube_{i}"), (x - sx * 0.26 + i * sx * 0.26, y - sy * 0.20, z + sz * 0.18), (sx * 0.10, sx * 0.10, sz * 0.62), glass, vertices=18))
        return parts

    if kind == "compass":
        metal = make_material("compass_metal", (0.62, 0.62, 0.58, 1.0))
        needle = make_material("compass_needle", (0.85, 0.12, 0.10, 1.0))
        return [
            add_cylinder(part_name(obj, "disc"), loc, (sx, sy, max(0.05, sz * 0.22)), metal, vertices=48),
            add_box(part_name(obj, "needle"), (x, y, z + sz * 0.15), (sx * 0.78, sy * 0.06, max(0.02, sz * 0.12)), needle, rotation=(0, 0, math.radians(25)), bevel=0.003),
        ]

    if kind in {"battery_pack", "small_box", "cardboard_box", "suitcase", "backpack"}:
        body_mat = make_material("cardboard", MATERIAL_COLORS["cardboard"]) if kind == "cardboard_box" else mat
        parts = [add_box(part_name(obj, "body"), loc, size, body_mat, bevel=0.025)]
        detail = make_material("detail_dark", (0.08, 0.09, 0.10, 1.0))
        if kind == "battery_pack":
            parts.append(add_box(part_name(obj, "terminal_pos"), (x + sx * 0.24, y + sy * 0.48, z + sz * 0.20), (sx * 0.16, sy * 0.08, sz * 0.22), detail, bevel=0.003))
            parts.append(add_box(part_name(obj, "terminal_neg"), (x - sx * 0.24, y + sy * 0.48, z + sz * 0.20), (sx * 0.16, sy * 0.08, sz * 0.22), detail, bevel=0.003))
        elif kind in {"suitcase", "backpack"}:
            parts.append(add_torus(part_name(obj, "handle"), (x, y + sy * 0.42, z + sz * 0.35), sx * 0.22, sx * 0.025, detail, rotation=(math.pi / 2, 0, 0)))
        else:
            parts.append(add_box(part_name(obj, "lid"), (x, y, z + sz * 0.28), (sx * 0.92, sy * 0.92, sz * 0.10), detail, bevel=0.004))
        return parts

    if kind == "toolbox":
        red = make_material("toolbox_red", (0.70, 0.12, 0.10, 1.0))
        dark = make_material("toolbox_handle", (0.08, 0.08, 0.08, 1.0))
        return [
            add_box(part_name(obj, "body"), loc, size, red, bevel=0.025),
            add_box(part_name(obj, "handle"), (x, y, z + sz * 0.58), (sx * 0.55, sy * 0.12, sz * 0.16), dark, bevel=0.01),
            add_box(part_name(obj, "latch"), (x, y - sy * 0.52, z + sz * 0.08), (sx * 0.22, sy * 0.05, sz * 0.16), make_material("latch_metal", (0.70, 0.72, 0.72, 1.0)), bevel=0.003),
        ]

    if kind in {"telescope", "roll", "screwdriver", "brush"}:
        body = mat
        parts = [add_cylinder(part_name(obj, "body"), loc, (sx, max(0.08, sy * 0.34), max(0.08, sz * 0.34)), body, rotation=(0, math.pi / 2, 0))]
        if kind == "telescope":
            metal = make_material("telescope_metal", (0.60, 0.58, 0.54, 1.0))
            parts.append(add_cylinder(part_name(obj, "lens"), (x + sx * 0.47, y, z), (sx * 0.18, sy * 0.55, sz * 0.55), metal, rotation=(0, math.pi / 2, 0)))
            parts.append(add_cylinder(part_name(obj, "tripod"), (x, y, z - sz * 0.46), (sx * 0.08, sy * 0.08, sz * 0.80), metal))
        elif kind in {"screwdriver", "brush"}:
            tip = make_material("tool_tip", (0.72, 0.74, 0.76, 1.0))
            parts.append(add_cone(part_name(obj, "tip"), (x + sx * 0.48, y, z), (sx * 0.16, sy * 0.18, sz * 0.18), tip, rotation=(0, math.pi / 2, 0)))
        return parts

    if kind == "robot_arm":
        metal = make_material("robot_arm_metal", (0.56, 0.60, 0.63, 1.0))
        joint = make_material("robot_joint", (0.12, 0.15, 0.18, 1.0))
        bottom = z - sz / 2
        return [
            add_cylinder(part_name(obj, "base"), (x, y, bottom + sz * 0.12), (sx * 0.95, sy * 0.95, sz * 0.24), metal),
            add_cylinder(part_name(obj, "lower_arm"), (x, y, bottom + sz * 0.48), (sx * 0.22, sy * 0.22, sz * 0.62), metal),
            add_sphere(part_name(obj, "joint"), (x, y, bottom + sz * 0.78), (sx * 0.38, sy * 0.38, sz * 0.22), joint),
            add_cylinder(part_name(obj, "forearm"), (x + sx * 0.25, y, bottom + sz * 0.86), (sx * 0.58, sy * 0.16, sz * 0.16), metal, rotation=(0, math.pi / 2, 0)),
            add_box(part_name(obj, "gripper"), (x + sx * 0.58, y, bottom + sz * 0.86), (sx * 0.18, sy * 0.34, sz * 0.10), joint, bevel=0.004),
        ]

    if kind in {"camera", "scanner", "radio", "printer", "speaker"}:
        dark = make_material("device_dark", (0.08, 0.09, 0.10, 1.0))
        parts = [add_box(part_name(obj, "body"), loc, size, mat, bevel=0.025)]
        if kind == "camera":
            parts.append(add_cylinder(part_name(obj, "lens"), (x, y - sy * 0.54, z + sz * 0.03), (sx * 0.34, sx * 0.34, sy * 0.28), dark, rotation=(math.pi / 2, 0, 0)))
            parts.append(add_box(part_name(obj, "viewfinder"), (x + sx * 0.25, y, z + sz * 0.56), (sx * 0.24, sy * 0.32, sz * 0.14), dark, bevel=0.004))
        elif kind in {"speaker", "radio"}:
            parts.append(add_cylinder(part_name(obj, "driver"), (x, y - sy * 0.53, z + sz * 0.10), (sx * 0.42, sx * 0.42, sy * 0.08), dark, rotation=(math.pi / 2, 0, 0)))
            if kind == "radio":
                parts.append(add_box(part_name(obj, "antenna"), (x + sx * 0.42, y, z + sz * 0.62), (sx * 0.05, sy * 0.05, sz * 0.62), dark, rotation=(0, math.radians(18), 0), bevel=0.002))
        elif kind == "scanner":
            parts.append(add_cylinder(part_name(obj, "nose"), (x + sx * 0.36, y, z), (sx * 0.42, sy * 0.35, sz * 0.28), dark, rotation=(0, math.pi / 2, 0)))
        else:
            parts.append(add_box(part_name(obj, "paper_slot"), (x, y - sy * 0.52, z + sz * 0.05), (sx * 0.72, sy * 0.06, sz * 0.12), dark, bevel=0.002))
        return parts

    if kind == "microscope":
        metal = make_material("microscope_metal", (0.42, 0.46, 0.50, 1.0))
        dark = make_material("microscope_lens", (0.04, 0.05, 0.06, 1.0))
        bottom = z - sz / 2
        return [
            add_box(part_name(obj, "base"), (x, y, bottom + sz * 0.08), (sx, sy * 0.72, sz * 0.16), metal, bevel=0.018),
            add_cylinder(part_name(obj, "pillar"), (x - sx * 0.22, y, bottom + sz * 0.48), (sx * 0.16, sy * 0.16, sz * 0.70), metal),
            add_cylinder(part_name(obj, "tube"), (x + sx * 0.12, y, bottom + sz * 0.76), (sx * 0.18, sy * 0.18, sz * 0.62), dark, rotation=(0, math.radians(24), 0)),
            add_box(part_name(obj, "stage"), (x + sx * 0.12, y, bottom + sz * 0.38), (sx * 0.52, sy * 0.44, sz * 0.08), dark, bevel=0.004),
        ]

    if kind in {"tripod", "light_stand"}:
        metal = make_material("stand_metal", (0.55, 0.57, 0.60, 1.0))
        head = make_material("stand_head", (1.0, 0.78, 0.45, 1.0)) if kind == "light_stand" else metal
        bottom = z - sz / 2
        return [
            add_cylinder(part_name(obj, "pole"), (x, y, bottom + sz * 0.52), (sx * 0.10, sy * 0.10, sz * 0.88), metal),
            add_box(part_name(obj, "leg_a"), (x, y - sy * 0.25, bottom + sz * 0.15), (sx * 0.08, sy * 0.62, sz * 0.08), metal, rotation=(math.radians(15), 0, 0), bevel=0.003),
            add_box(part_name(obj, "leg_b"), (x - sx * 0.25, y + sy * 0.16, bottom + sz * 0.15), (sx * 0.08, sy * 0.58, sz * 0.08), metal, rotation=(math.radians(-12), 0, math.radians(32)), bevel=0.003),
            add_box(part_name(obj, "leg_c"), (x + sx * 0.25, y + sy * 0.16, bottom + sz * 0.15), (sx * 0.08, sy * 0.58, sz * 0.08), metal, rotation=(math.radians(-12), 0, math.radians(-32)), bevel=0.003),
            add_cylinder(part_name(obj, "head"), (x, y, bottom + sz * 0.95), (sx * 0.42, sy * 0.42, sz * 0.12), head),
        ]

    if kind in {"reflector", "mirror", "clock", "plate"}:
        disc_mat = make_material("reflective_light", (0.78, 0.80, 0.78, 1.0)) if kind in {"reflector", "mirror"} else mat
        parts = [add_cylinder(part_name(obj, "disc"), loc, (sx, sy, max(0.04, sz * 0.18)), disc_mat, vertices=48)]
        if kind == "clock":
            parts.append(add_box(part_name(obj, "hand_h"), (x, y, z + sz * 0.14), (sx * 0.40, sy * 0.025, 0.012), make_material("clock_hands", (0.05, 0.05, 0.05, 1.0)), bevel=0.001))
            parts.append(add_box(part_name(obj, "hand_v"), (x, y, z + sz * 0.15), (sx * 0.025, sy * 0.34, 0.012), make_material("clock_hands", (0.05, 0.05, 0.05, 1.0)), bevel=0.001))
        return parts

    if kind in {"magnifying_glass", "globe"}:
        metal = make_material("instrument_metal", (0.58, 0.60, 0.62, 1.0))
        if kind == "magnifying_glass":
            glass = make_material("lens_glass", MATERIAL_COLORS["glass"])
            return [
                add_torus(part_name(obj, "rim"), (x - sx * 0.12, y, z + sz * 0.12), sx * 0.20, sx * 0.018, metal),
                add_cylinder(part_name(obj, "lens"), (x - sx * 0.12, y, z + sz * 0.12), (sx * 0.35, sx * 0.35, max(0.018, sz * 0.08)), glass, vertices=48),
                add_box(part_name(obj, "handle"), (x + sx * 0.22, y, z - sz * 0.08), (sx * 0.48, sy * 0.08, sz * 0.08), metal, rotation=(0, 0, math.radians(-28)), bevel=0.003),
            ]
        ocean = make_material("globe_ocean", (0.18, 0.42, 0.72, 1.0))
        land = make_material("globe_land", (0.22, 0.55, 0.28, 1.0))
        return [
            add_sphere(part_name(obj, "sphere"), (x, y, z + sz * 0.10), (sx * 0.72, sy * 0.72, sz * 0.72), ocean),
            add_box(part_name(obj, "land_band"), (x, y, z + sz * 0.18), (sx * 0.58, sy * 0.08, sz * 0.08), land, rotation=(0, 0, math.radians(22)), bevel=0.002),
            add_cylinder(part_name(obj, "stand"), (x, y, z - sz * 0.34), (sx * 0.18, sy * 0.18, sz * 0.40), metal),
            add_cylinder(part_name(obj, "base"), (x, y, z - sz * 0.52), (sx * 0.58, sy * 0.58, sz * 0.10), metal),
        ]

    if kind in {"bottle", "spray_bottle", "pill_bottle", "soap_dispenser", "vase"}:
        body = mat
        parts = [
            add_cylinder(part_name(obj, "body"), (x, y, z - sz * 0.06), (sx * 0.72, sy * 0.72, sz * 0.76), body),
            add_cylinder(part_name(obj, "neck"), (x, y, z + sz * 0.34), (sx * 0.34, sy * 0.34, sz * 0.28), body),
        ]
        if kind in {"spray_bottle", "soap_dispenser"}:
            parts.append(add_box(part_name(obj, "pump"), (x + sx * 0.18, y, z + sz * 0.53), (sx * 0.48, sy * 0.18, sz * 0.12), make_material("pump_dark", (0.08, 0.09, 0.10, 1.0)), bevel=0.004))
        return parts

    if kind == "bowl":
        ceramic = mat
        return [
            add_cylinder(part_name(obj, "outer"), loc, (sx, sy, sz), ceramic, vertices=48),
            add_cylinder(part_name(obj, "inner_shadow"), (x, y, z + sz * 0.12), (sx * 0.72, sy * 0.72, sz * 0.30), make_material("bowl_inner", (0.18, 0.18, 0.17, 1.0)), vertices=48),
        ]

    if kind == "toy_car":
        body = make_material("toy_car_body", (0.78, 0.12, 0.10, 1.0))
        wheel = make_material("rubber", MATERIAL_COLORS["rubber"])
        bottom = z - sz / 2
        return [
            add_box(part_name(obj, "body"), (x, y, bottom + sz * 0.42), (sx, sy * 0.62, sz * 0.34), body, bevel=0.025),
            add_box(part_name(obj, "cab"), (x + sx * 0.12, y, bottom + sz * 0.68), (sx * 0.42, sy * 0.50, sz * 0.30), body, bevel=0.02),
            add_cylinder(part_name(obj, "wheel_l"), (x - sx * 0.28, y - sy * 0.34, bottom + sz * 0.20), (sx * 0.20, sx * 0.20, sy * 0.12), wheel, rotation=(math.pi / 2, 0, 0)),
            add_cylinder(part_name(obj, "wheel_r"), (x + sx * 0.28, y - sy * 0.34, bottom + sz * 0.20), (sx * 0.20, sx * 0.20, sy * 0.12), wheel, rotation=(math.pi / 2, 0, 0)),
        ]

    if kind == "drone":
        dark = make_material("drone_dark", (0.10, 0.12, 0.14, 1.0))
        rotor = make_material("drone_rotor", (0.04, 0.04, 0.05, 1.0))
        parts = [add_box(part_name(obj, "body"), loc, (sx * 0.44, sy * 0.44, sz * 0.30), dark, bevel=0.02)]
        for dx, dy, suffix in ((-1, -1, "fl"), (1, -1, "fr"), (-1, 1, "bl"), (1, 1, "br")):
            parts.append(add_box(part_name(obj, f"arm_{suffix}"), (x + dx * sx * 0.25, y + dy * sy * 0.25, z), (sx * 0.55, sy * 0.07, sz * 0.08), dark, rotation=(0, 0, math.atan2(dy, dx)), bevel=0.003))
            parts.append(add_torus(part_name(obj, f"rotor_{suffix}"), (x + dx * sx * 0.45, y + dy * sy * 0.45, z + sz * 0.07), sx * 0.12, sx * 0.012, rotor))
        return parts

    if kind == "robot_toy":
        body = make_material("robot_body", (0.50, 0.56, 0.62, 1.0))
        dark = make_material("robot_detail", (0.08, 0.10, 0.12, 1.0))
        bottom = z - sz / 2
        return [
            add_box(part_name(obj, "body"), (x, y, bottom + sz * 0.42), (sx * 0.60, sy * 0.42, sz * 0.46), body, bevel=0.018),
            add_box(part_name(obj, "head"), (x, y, bottom + sz * 0.78), (sx * 0.46, sy * 0.38, sz * 0.26), body, bevel=0.015),
            add_cylinder(part_name(obj, "eye_l"), (x - sx * 0.10, y - sy * 0.21, bottom + sz * 0.80), (sx * 0.07, sx * 0.07, sy * 0.04), dark, rotation=(math.pi / 2, 0, 0)),
            add_cylinder(part_name(obj, "eye_r"), (x + sx * 0.10, y - sy * 0.21, bottom + sz * 0.80), (sx * 0.07, sx * 0.07, sy * 0.04), dark, rotation=(math.pi / 2, 0, 0)),
        ]

    if kind == "block_tower":
        colors = [make_material("block_red", NAMED_COLORS["red"]), make_material("block_blue", NAMED_COLORS["blue"]), make_material("block_yellow", NAMED_COLORS["yellow"])]
        parts = []
        for i in range(3):
            parts.append(add_box(part_name(obj, f"block_{i}"), (x, y, z - sz * 0.30 + i * sz * 0.30), (sx * (0.72 - i * 0.08), sy * (0.72 - i * 0.08), sz * 0.26), colors[i], bevel=0.012))
        return parts

    if kind in {"teapot", "watering_can"}:
        body = mat if kind == "teapot" else make_material("watering_can", (0.36, 0.55, 0.60, 1.0))
        return [
            add_sphere(part_name(obj, "body"), (x, y, z), (sx * 0.78, sy * 0.78, sz * 0.62), body),
            add_cylinder(part_name(obj, "lid"), (x, y, z + sz * 0.38), (sx * 0.34, sy * 0.34, sz * 0.12), body),
            add_cone(part_name(obj, "spout"), (x + sx * 0.45, y, z + sz * 0.08), (sx * 0.44, sy * 0.18, sz * 0.18), body, rotation=(0, math.pi / 2, 0)),
            add_torus(part_name(obj, "handle"), (x - sx * 0.42, y, z + sz * 0.02), sx * 0.19, sx * 0.025, body, rotation=(math.pi / 2, 0, 0)),
        ]

    if kind in {"tray", "seed_tray"}:
        tray = mat
        parts = [add_box(part_name(obj, "base"), loc, (sx, sy, max(0.05, sz * 0.34)), tray, bevel=0.012)]
        for i in range(3):
            parts.append(add_box(part_name(obj, f"ridge_{i}"), (x - sx * 0.30 + i * sx * 0.30, y, z + sz * 0.22), (sx * 0.035, sy * 0.88, sz * 0.14), make_material("tray_ridges", (0.22, 0.20, 0.16, 1.0)), bevel=0.002))
        return parts

    if kind in {"paint_palette", "helmet", "basket"}:
        if kind == "paint_palette":
            parts = [add_cylinder(part_name(obj, "disc"), loc, (sx, sy, max(0.04, sz * 0.20)), make_material("palette_wood", (0.72, 0.52, 0.30, 1.0)), vertices=48)]
            for i, color in enumerate(("red", "blue", "yellow")):
                parts.append(add_sphere(part_name(obj, f"paint_{color}"), (x - sx * 0.20 + i * sx * 0.18, y + sy * 0.15, z + sz * 0.18), (sx * 0.12, sy * 0.12, sz * 0.08), make_material(f"paint_{color}", NAMED_COLORS[color])))
            return parts
        if kind == "helmet":
            return [
                add_sphere(part_name(obj, "dome"), (x, y, z + sz * 0.05), (sx, sy, sz * 0.72), mat),
                add_box(part_name(obj, "brim"), (x, y - sy * 0.36, z - sz * 0.18), (sx * 0.86, sy * 0.28, sz * 0.12), mat, bevel=0.01),
            ]
        return [
            add_box(part_name(obj, "body"), loc, (sx, sy, sz * 0.62), make_material("basket_wicker", (0.62, 0.42, 0.22, 1.0)), bevel=0.02),
            add_torus(part_name(obj, "handle"), (x, y, z + sz * 0.36), sx * 0.30, sx * 0.025, make_material("basket_wicker", (0.62, 0.42, 0.22, 1.0)), rotation=(math.pi / 2, 0, 0)),
        ]

    if kind in {"tool", "drill", "scissors"}:
        metal = make_material("tool_metal", (0.70, 0.72, 0.72, 1.0))
        handle = make_material("tool_handle", (0.08, 0.10, 0.12, 1.0))
        if kind == "drill":
            return [
                add_box(part_name(obj, "body"), (x, y, z + sz * 0.10), (sx * 0.62, sy * 0.42, sz * 0.42), handle, bevel=0.02),
                add_cylinder(part_name(obj, "bit"), (x + sx * 0.42, y, z + sz * 0.12), (sx * 0.34, sy * 0.10, sz * 0.10), metal, rotation=(0, math.pi / 2, 0)),
                add_box(part_name(obj, "grip"), (x - sx * 0.12, y, z - sz * 0.24), (sx * 0.18, sy * 0.24, sz * 0.50), handle, bevel=0.012),
            ]
        if kind == "scissors":
            return [
                add_box(part_name(obj, "blade_a"), (x + sx * 0.14, y, z + sz * 0.04), (sx * 0.55, sy * 0.05, sz * 0.06), metal, rotation=(0, 0, math.radians(16)), bevel=0.002),
                add_box(part_name(obj, "blade_b"), (x + sx * 0.14, y, z - sz * 0.04), (sx * 0.55, sy * 0.05, sz * 0.06), metal, rotation=(0, 0, math.radians(-16)), bevel=0.002),
                add_torus(part_name(obj, "handle_a"), (x - sx * 0.28, y + sy * 0.10, z), sx * 0.10, sx * 0.015, handle),
                add_torus(part_name(obj, "handle_b"), (x - sx * 0.28, y - sy * 0.10, z), sx * 0.10, sx * 0.015, handle),
            ]
        return [
            add_box(part_name(obj, "shaft"), loc, (sx * 0.72, sy * 0.10, sz * 0.10), metal, rotation=(0, 0, math.radians(12)), bevel=0.003),
            add_cylinder(part_name(obj, "handle"), (x - sx * 0.35, y, z), (sx * 0.18, sy * 0.18, sz * 0.18), handle, rotation=(0, math.pi / 2, 0)),
        ]

    if kind in {"sandwich", "cake"}:
        if kind == "cake":
            cream = make_material("cake_cream", (0.95, 0.80, 0.72, 1.0))
            return [
                add_cylinder(part_name(obj, "base"), (x, y, z - sz * 0.08), (sx, sy, sz * 0.64), cream, vertices=48),
                add_cylinder(part_name(obj, "icing"), (x, y, z + sz * 0.30), (sx * 0.92, sy * 0.92, sz * 0.12), make_material("cake_icing", (0.92, 0.92, 0.86, 1.0)), vertices=48),
                add_sphere(part_name(obj, "berry"), (x, y, z + sz * 0.43), (sx * 0.16, sy * 0.16, sz * 0.12), make_material("berry_red", NAMED_COLORS["red"])),
            ]
        bread = make_material("sandwich_bread", (0.78, 0.58, 0.34, 1.0))
        filling = make_material("sandwich_filling", (0.28, 0.58, 0.24, 1.0))
        return [
            add_box(part_name(obj, "bread_top"), (x, y, z + sz * 0.16), (sx, sy, sz * 0.24), bread, rotation=(0, 0, math.radians(4)), bevel=0.012),
            add_box(part_name(obj, "filling"), (x, y, z), (sx * 0.95, sy * 0.95, sz * 0.12), filling, bevel=0.004),
            add_box(part_name(obj, "bread_bottom"), (x, y, z - sz * 0.16), (sx, sy, sz * 0.24), bread, rotation=(0, 0, math.radians(-4)), bevel=0.012),
        ]

    if kind in {"chess_piece", "sculpture", "statue", "artifact", "fish_statue", "coral"}:
        stone = mat
        if kind == "coral":
            coral = make_material("coral", (0.90, 0.36, 0.28, 1.0))
            return [
                add_cylinder(part_name(obj, "stem"), (x, y, z - sz * 0.10), (sx * 0.18, sy * 0.18, sz * 0.72), coral),
                add_cylinder(part_name(obj, "branch_a"), (x + sx * 0.18, y, z + sz * 0.12), (sx * 0.12, sy * 0.12, sz * 0.42), coral, rotation=(0, math.radians(32), 0)),
                add_cylinder(part_name(obj, "branch_b"), (x - sx * 0.16, y, z + sz * 0.18), (sx * 0.12, sy * 0.12, sz * 0.38), coral, rotation=(0, math.radians(-32), 0)),
            ]
        if kind == "fish_statue":
            return [
                add_sphere(part_name(obj, "body"), (x, y, z), (sx * 0.72, sy * 0.42, sz * 0.42), stone),
                add_cone(part_name(obj, "tail"), (x - sx * 0.42, y, z), (sx * 0.32, sy * 0.36, sz * 0.36), stone, rotation=(0, -math.pi / 2, 0)),
                add_cylinder(part_name(obj, "base"), (x, y, z - sz * 0.36), (sx * 0.70, sy * 0.50, sz * 0.12), stone),
            ]
        return [
            add_cylinder(part_name(obj, "base"), (x, y, z - sz * 0.38), (sx * 0.70, sy * 0.70, sz * 0.18), stone),
            add_sphere(part_name(obj, "body"), (x, y, z - sz * 0.04), (sx * 0.46, sy * 0.46, sz * 0.52), stone),
            add_cone(part_name(obj, "top"), (x, y, z + sz * 0.34), (sx * 0.34, sy * 0.34, sz * 0.26), stone),
        ]

    if kind == "piano":
        dark = make_material("piano_dark", (0.05, 0.04, 0.035, 1.0))
        ivory = make_material("piano_keys", (0.92, 0.90, 0.84, 1.0))
        return [
            add_box(part_name(obj, "body"), loc, size, dark, bevel=0.025),
            add_box(part_name(obj, "keys"), (x, y - sy * 0.50, z + sz * 0.05), (sx * 0.82, sy * 0.14, sz * 0.12), ivory, bevel=0.003),
        ]

    if kind in {"rug", "towel"}:
        fabric = mat
        return [
            add_box(part_name(obj, "cloth"), loc, (sx, sy, max(0.025, sz * 0.50)), fabric, bevel=0.004),
            add_box(part_name(obj, "stripe"), (x, y, z + max(0.02, sz * 0.30)), (sx * 0.82, sy * 0.08, 0.01), make_material("cloth_stripe", (0.86, 0.86, 0.80, 1.0)), bevel=0.001),
        ]

    if shape == "sphere":
        return [add_sphere(obj["id"], loc, size, mat)]
    elif shape == "cone":
        return [add_cone(obj["id"], loc, size, mat)]
    elif shape == "cylinder":
        return [add_cylinder(obj["id"], loc, size, mat)]
    else:
        return [add_box(obj["id"], loc, size, mat)]


def bbox_center(objects: list[dict]) -> Vector:
    if not objects:
        return Vector((0.0, 0.0, 0.0))
    return Vector(
        (
            sum(obj["location"][0] for obj in objects) / len(objects),
            sum(obj["location"][1] for obj in objects) / len(objects),
            sum(obj["location"][2] for obj in objects) / len(objects),
        )
    )


def bbox_extent(objects: list[dict]) -> float:
    if not objects:
        return 4.0
    min_x = min(obj["location"][0] - obj["size"][0] / 2 for obj in objects)
    max_x = max(obj["location"][0] + obj["size"][0] / 2 for obj in objects)
    min_y = min(obj["location"][1] - obj["size"][1] / 2 for obj in objects)
    max_y = max(obj["location"][1] + obj["size"][1] / 2 for obj in objects)
    return max(4.0, max_x - min_x, max_y - min_y)


def look_at(obj: bpy.types.Object, target: Vector) -> None:
    direction = target - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def setup_camera(scene: dict) -> None:
    objects = scene["objects"]
    target = bbox_center(objects)
    extent = bbox_extent(objects)
    camera_location = Vector((target.x, target.y - extent * 2.2, target.z + extent * 1.35 + 1.2))
    bpy.ops.object.camera_add(location=camera_location)
    camera = bpy.context.object
    look_at(camera, target)
    camera.data.lens = 35
    camera.data.dof.use_dof = False
    bpy.context.scene.camera = camera


def setup_lighting(style: str) -> None:
    if style == "cyberpunk":
        colors = [(0.2, 0.8, 1.0), (1.0, 0.2, 0.8)]
    elif style in {"warm", "medieval"}:
        colors = [(1.0, 0.72, 0.38), (1.0, 0.86, 0.62)]
    else:
        colors = [(1.0, 1.0, 1.0), (0.72, 0.82, 1.0)]
    bpy.ops.object.light_add(type="AREA", location=(-3.0, -4.0, 6.0))
    key = bpy.context.object
    key.name = "SceneTest_Key_Light"
    key.data.energy = 650
    key.data.size = 5
    key.data.color = colors[0]
    bpy.ops.object.light_add(type="POINT", location=(3.0, 2.0, 3.0))
    fill = bpy.context.object
    fill.name = "SceneTest_Fill_Light"
    fill.data.energy = 95
    fill.data.color = colors[1]


def setup_render(output: Path, resolution: str, engine: str, style: str = "neutral") -> None:
    width, height = [int(x) for x in resolution.lower().split("x", 1)]
    bpy.context.scene.render.resolution_x = width
    bpy.context.scene.render.resolution_y = height
    bpy.context.scene.render.image_settings.file_format = "PNG"
    bpy.context.scene.render.filepath = str(output)
    try:
        bpy.context.scene.render.engine = engine
    except TypeError:
        bpy.context.scene.render.engine = "BLENDER_WORKBENCH"
    bpy.context.scene.view_settings.view_transform = "Standard"
    bpy.context.scene.view_settings.look = "Medium High Contrast"
    if style == "cyberpunk":
        bpy.context.scene.world.color = (0.035, 0.04, 0.065)
    elif style in {"warm", "medieval"}:
        bpy.context.scene.world.color = (0.74, 0.68, 0.58)
    else:
        bpy.context.scene.world.color = (0.78, 0.80, 0.82)


def add_floor(scene: dict) -> None:
    objects = scene["objects"]
    center = bbox_center(objects)
    extent = bbox_extent(objects) * 1.8
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(center.x, center.y, -0.035))
    floor = bpy.context.object
    floor.name = "SceneTest_Floor"
    floor.dimensions = (extent, extent, 0.04)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    style = scene.get("lighting_style", "neutral")
    if style == "cyberpunk":
        color = (0.08, 0.085, 0.105, 1.0)
    elif style in {"warm", "medieval"}:
        color = (0.68, 0.58, 0.45, 1.0)
    else:
        color = (0.70, 0.68, 0.62, 1.0)
    floor.data.materials.append(make_material("floor_warm_gray", color))


def main() -> None:
    args = parse_args()
    scene = json.loads(Path(args.scene_json).read_text(encoding="utf-8"))
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    reset_scene()
    for obj in scene["objects"]:
        add_object(obj)
    add_floor(scene)
    setup_lighting(scene.get("lighting_style", "neutral"))
    setup_camera(scene)
    setup_render(output, args.resolution, args.engine, scene.get("lighting_style", "neutral"))
    bpy.ops.render.render(write_still=True)
    print(f"SceneTest Blender render written to {output}")


if __name__ == "__main__":
    main()
