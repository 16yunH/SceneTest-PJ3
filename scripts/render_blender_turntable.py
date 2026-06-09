#!/usr/bin/env python3
"""Render a SceneBuilder JSON scene as Blender still + turntable frames.

Run with:
  Blender --background --python scripts/render_blender_turntable.py -- \
    --scene-json ... --frames-dir ... --still-output ...
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from render_blender_scene import (  # noqa: E402
    add_floor,
    add_object,
    bbox_center,
    bbox_extent,
    look_at,
    reset_scene,
    setup_lighting,
    setup_render,
)


def parse_args() -> argparse.Namespace:
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1 :]
    else:
        argv = []
    parser = argparse.ArgumentParser()
    parser.add_argument("--scene-json", required=True)
    parser.add_argument("--frames-dir", required=True)
    parser.add_argument("--still-output")
    parser.add_argument("--frames", type=int, default=16)
    parser.add_argument("--resolution", default="720x540")
    parser.add_argument("--engine", default="BLENDER_WORKBENCH")
    return parser.parse_args(argv)


def setup_scene(scene: dict) -> None:
    reset_scene()
    for obj in scene["objects"]:
        add_object(obj)
    add_floor(scene)
    setup_lighting(scene.get("lighting_style", "neutral"))


def add_turntable_camera(scene: dict) -> bpy.types.Object:
    objects = scene["objects"]
    target = bbox_center(objects)
    extent = bbox_extent(objects)
    radius = extent * 2.25
    height = target.z + extent * 1.22 + 1.1
    bpy.ops.object.camera_add(location=(target.x, target.y - radius, height))
    camera = bpy.context.object
    camera.data.lens = 38
    camera.data.dof.use_dof = False
    bpy.context.scene.camera = camera
    look_at(camera, target)
    return camera


def position_camera(camera: bpy.types.Object, scene: dict, frame_index: int, frame_count: int) -> None:
    target = bbox_center(scene["objects"])
    extent = bbox_extent(scene["objects"])
    radius = extent * 2.25
    height = target.z + extent * 1.22 + 1.1
    theta = (2.0 * math.pi * frame_index) / max(1, frame_count)
    camera.location = Vector(
        (
            target.x + math.sin(theta) * radius,
            target.y - math.cos(theta) * radius,
            height,
        )
    )
    look_at(camera, target)


def render_frame(output: Path, resolution: str, engine: str) -> None:
    setup_render(output, resolution, engine)
    bpy.ops.render.render(write_still=True)


def main() -> None:
    args = parse_args()
    scene = json.loads(Path(args.scene_json).read_text(encoding="utf-8"))
    frames_dir = Path(args.frames_dir).resolve()
    frames_dir.mkdir(parents=True, exist_ok=True)
    setup_scene(scene)
    camera = add_turntable_camera(scene)

    if args.still_output:
        position_camera(camera, scene, 0, args.frames)
        render_frame(Path(args.still_output).resolve(), args.resolution, args.engine)

    for index in range(args.frames):
        position_camera(camera, scene, index, args.frames)
        render_frame(frames_dir / f"frame_{index:03d}.png", args.resolution, args.engine)

    print(f"SceneTest Blender turntable frames written to {frames_dir}")


if __name__ == "__main__":
    main()
