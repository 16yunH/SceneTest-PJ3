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
    "fabric": (0.48, 0.54, 0.64, 1.0),
    "plastic": (0.16, 0.18, 0.22, 1.0),
    "paper": (0.88, 0.84, 0.74, 1.0),
    "leafy": (0.23, 0.58, 0.34, 1.0),
    "matte": (0.45, 0.55, 0.70, 1.0),
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


def part_name(obj: dict, suffix: str) -> str:
    return f"{obj['id']}_{suffix}"


def reset_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()


def add_box(name: str, loc, size, mat: bpy.types.Material) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc)
    bobj = bpy.context.object
    bobj.name = name
    bobj.dimensions = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bobj.data.materials.append(mat)
    return bobj


def add_cylinder(name: str, loc, size, mat: bpy.types.Material, vertices: int = 32) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=0.5, depth=1.0, location=loc)
    bobj = bpy.context.object
    bobj.name = name
    bobj.dimensions = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bobj.data.materials.append(mat)
    return bobj


def add_sphere(name: str, loc, size, mat: bpy.types.Material) -> bpy.types.Object:
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=0.5, location=loc)
    bobj = bpy.context.object
    bobj.name = name
    bobj.dimensions = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bobj.data.materials.append(mat)
    return bobj


def add_cone(name: str, loc, size, mat: bpy.types.Material) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cone_add(vertices=32, radius1=0.5, depth=1.0, location=loc)
    bobj = bpy.context.object
    bobj.name = name
    bobj.dimensions = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bobj.data.materials.append(mat)
    return bobj


def add_object(obj: dict) -> list[bpy.types.Object]:
    loc = tuple(obj["location"])
    size = tuple(obj["size"])
    obj_type = obj.get("type", "")
    shape = obj.get("shape", "box")
    mat = material_for(obj)
    x, y, z = loc
    sx, sy, sz = size

    if obj_type == "laptop":
        base_z = z - sz * 0.15
        screen_z = z + sz * 1.65
        dark = make_material("laptop_dark", (0.08, 0.10, 0.13, 1.0))
        screen = make_material("screen_blue", (0.13, 0.25, 0.38, 1.0))
        return [
            add_box(part_name(obj, "base"), (x, y, base_z), (sx, sy, max(0.06, sz * 0.55)), dark),
            add_box(part_name(obj, "screen"), (x, y + sy * 0.38, screen_z), (sx, 0.06, max(0.55, sx * 0.55)), screen),
        ]

    if obj_type == "lamp":
        metal = make_material("lamp_metal", (0.52, 0.56, 0.60, 1.0))
        shade = make_material("lamp_warm_shade", (1.0, 0.78, 0.34, 1.0))
        bottom = z - sz / 2
        return [
            add_cylinder(part_name(obj, "base"), (x, y, bottom + 0.035), (sx * 0.95, sy * 0.95, 0.07), metal),
            add_cylinder(part_name(obj, "pole"), (x, y, bottom + sz * 0.48), (sx * 0.18, sy * 0.18, sz * 0.78), metal),
            add_cone(part_name(obj, "shade"), (x, y, bottom + sz * 0.88), (sx * 1.25, sy * 1.25, sz * 0.24), shade),
        ]

    if obj_type == "plant":
        pot = make_material("plant_pot", (0.50, 0.28, 0.18, 1.0))
        leaf = make_material("plant_leaf", (0.18, 0.55, 0.28, 1.0))
        bottom = z - sz / 2
        return [
            add_cylinder(part_name(obj, "pot"), (x, y, bottom + sz * 0.22), (sx * 0.75, sy * 0.75, sz * 0.44), pot),
            add_sphere(part_name(obj, "leaf_a"), (x, y, bottom + sz * 0.70), (sx * 0.92, sy * 0.92, sz * 0.46), leaf),
            add_sphere(part_name(obj, "leaf_b"), (x - sx * 0.18, y + sy * 0.12, bottom + sz * 0.83), (sx * 0.55, sy * 0.55, sz * 0.32), leaf),
            add_sphere(part_name(obj, "leaf_c"), (x + sx * 0.18, y - sy * 0.10, bottom + sz * 0.82), (sx * 0.55, sy * 0.55, sz * 0.32), leaf),
        ]

    if obj_type == "cup":
        ceramic = mat
        bottom = z - sz / 2
        cup = add_cylinder(part_name(obj, "body"), (x, y, bottom + sz * 0.50), (sx, sy, sz), ceramic)
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

    if obj_type == "chair":
        fabric = mat
        bottom = z - sz / 2
        return [
            add_box(part_name(obj, "seat"), (x, y, bottom + sz * 0.42), (sx, sy, sz * 0.18), fabric),
            add_box(part_name(obj, "back"), (x, y + sy * 0.42, bottom + sz * 0.72), (sx, sy * 0.16, sz * 0.55), fabric),
            add_box(part_name(obj, "leg_fl"), (x - sx * 0.35, y - sy * 0.35, bottom + sz * 0.20), (0.07, 0.07, sz * 0.40), fabric),
            add_box(part_name(obj, "leg_fr"), (x + sx * 0.35, y - sy * 0.35, bottom + sz * 0.20), (0.07, 0.07, sz * 0.40), fabric),
        ]

    if obj_type == "sofa":
        fabric = mat
        bottom = z - sz / 2
        return [
            add_box(part_name(obj, "seat"), (x, y, bottom + sz * 0.38), (sx, sy, sz * 0.35), fabric),
            add_box(part_name(obj, "back"), (x, y + sy * 0.45, bottom + sz * 0.68), (sx, sy * 0.18, sz * 0.55), fabric),
            add_box(part_name(obj, "left_arm"), (x - sx * 0.48, y, bottom + sz * 0.55), (sx * 0.08, sy, sz * 0.48), fabric),
            add_box(part_name(obj, "right_arm"), (x + sx * 0.48, y, bottom + sz * 0.55), (sx * 0.08, sy, sz * 0.48), fabric),
        ]

    if obj_type == "bed":
        fabric = mat
        bottom = z - sz / 2
        return [
            add_box(part_name(obj, "frame"), (x, y, bottom + sz * 0.28), (sx, sy, sz * 0.35), make_material("bed_frame", (0.42, 0.28, 0.20, 1.0))),
            add_box(part_name(obj, "mattress"), (x, y, bottom + sz * 0.58), (sx * 0.94, sy * 0.92, sz * 0.24), fabric),
            add_box(part_name(obj, "pillow"), (x, y + sy * 0.32, bottom + sz * 0.78), (sx * 0.42, sy * 0.20, sz * 0.16), make_material("pillow", (0.92, 0.90, 0.84, 1.0))),
        ]

    if obj_type == "shelf":
        wood = mat
        parts = [add_box(part_name(obj, "frame"), loc, size, wood)]
        for i in range(3):
            parts.append(add_box(part_name(obj, f"slot_{i}"), (x, y - sy * 0.03, z - sz * 0.28 + i * sz * 0.28), (sx * 0.86, sy * 0.12, 0.045), make_material("shelf_shadow", (0.25, 0.18, 0.13, 1.0))))
        return parts

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


def setup_render(output: Path, resolution: str, engine: str) -> None:
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
    floor.data.materials.append(make_material("floor_warm_gray", (0.70, 0.68, 0.62, 1.0)))


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
    setup_render(output, args.resolution, args.engine)
    bpy.ops.render.render(write_still=True)
    print(f"SceneTest Blender render written to {output}")


if __name__ == "__main__":
    main()
