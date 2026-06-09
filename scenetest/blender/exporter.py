"""Export a serialized SceneBuilder scene to Blender Python."""

from __future__ import annotations

from pathlib import Path

from scenetest.core.scene_builder import SceneBuilder


def export_blender_script(scene: SceneBuilder, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(to_blender_python(scene), encoding="utf-8")


def to_blender_python(scene: SceneBuilder) -> str:
    lines = [
        "import bpy",
        "from mathutils import Vector",
        "",
        "bpy.ops.object.select_all(action='SELECT')",
        "bpy.ops.object.delete()",
        "",
        "def make_mat(name, color):",
        "    mat = bpy.data.materials.new(name)",
        "    mat.diffuse_color = color",
        "    return mat",
        "",
        "MATS = {",
        "    'wood': make_mat('wood', (0.55, 0.32, 0.16, 1.0)),",
        "    'metal': make_mat('metal', (0.55, 0.57, 0.60, 1.0)),",
        "    'ceramic': make_mat('ceramic', (0.92, 0.90, 0.84, 1.0)),",
        "    'fabric': make_mat('fabric', (0.48, 0.54, 0.64, 1.0)),",
        "    'matte': make_mat('matte', (0.45, 0.55, 0.70, 1.0)),",
        "    'leafy': make_mat('leafy', (0.25, 0.60, 0.35, 1.0)),",
        "}",
        "",
        "def add_box(obj):",
        "    bpy.ops.mesh.primitive_cube_add(size=1, location=obj['location'])",
        "    bobj = bpy.context.object",
        "    bobj.name = obj['id']",
        "    bobj.dimensions = obj['size']",
        "    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)",
        "    mat_key = (obj.get('material') or 'matte').split()[0]",
        "    bobj.data.materials.append(MATS.get(mat_key, MATS['matte']))",
        "    return bobj",
        "",
        "def add_round(obj, primitive):",
        "    if primitive == 'sphere':",
        "        bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, location=obj['location'])",
        "    elif primitive == 'cone':",
        "        bpy.ops.mesh.primitive_cone_add(vertices=32, radius1=0.5, depth=1.0, location=obj['location'])",
        "    else:",
        "        bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=0.5, depth=1.0, location=obj['location'])",
        "    bobj = bpy.context.object",
        "    bobj.name = obj['id']",
        "    bobj.scale = (obj['size'][0], obj['size'][1], obj['size'][2])",
        "    mat_key = (obj.get('material') or 'matte').split()[0]",
        "    bobj.data.materials.append(MATS.get(mat_key, MATS['matte']))",
        "    return bobj",
        "",
        f"SCENE = {scene.to_dict()!r}",
        "for obj in SCENE['objects']:",
        "    if obj.get('shape') in ('sphere', 'cylinder', 'cone'):",
        "        add_round(obj, obj.get('shape'))",
        "    else:",
        "        add_box(obj)",
        "",
        "style = SCENE.get('lighting_style', 'neutral')",
        "light_color = (1.0, 0.78, 0.45) if style == 'warm' else (0.7, 0.9, 1.0) if style == 'cyberpunk' else (1.0, 1.0, 1.0)",
        "bpy.ops.object.light_add(type='AREA', location=(0, -4, 6))",
        "light = bpy.context.object",
        "light.name = 'SceneTest_Key_Light'",
        "light.data.energy = 600",
        "light.data.size = 5",
        "light.data.color = light_color",
        "",
        "bbox = [obj['location'] for obj in SCENE['objects']]",
        "cx = sum(p[0] for p in bbox) / max(1, len(bbox))",
        "cy = sum(p[1] for p in bbox) / max(1, len(bbox))",
        "bpy.ops.object.camera_add(location=(cx, cy - 6.5, 4.2), rotation=(1.1, 0, 0))",
        "bpy.context.scene.camera = bpy.context.object",
        "bpy.context.scene.render.resolution_x = 1024",
        "bpy.context.scene.render.resolution_y = 768",
        "bpy.context.scene.eevee.taa_render_samples = 32 if hasattr(bpy.context.scene, 'eevee') else 16",
    ]
    return "\n".join(lines) + "\n"
