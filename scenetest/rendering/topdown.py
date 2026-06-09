"""Top-down visualization renderer.

This is not a replacement for Blender. It exists so that experiments, reports,
and slides are reproducible even on machines where Blender is unavailable.
"""

from __future__ import annotations

import html
from pathlib import Path
from typing import Dict, Tuple

from scenetest.core.scene_builder import SceneBuilder, SceneObject


COLOR_MAP: Dict[str, Tuple[int, int, int]] = {
    "red": (218, 77, 77),
    "blue": (70, 118, 210),
    "green": (65, 145, 87),
    "yellow": (232, 191, 67),
    "white": (235, 235, 232),
    "black": (36, 38, 41),
    "purple": (137, 87, 181),
    "orange": (221, 132, 53),
    "pink": (225, 119, 165),
    "gray": (138, 145, 153),
}

TYPE_COLORS: Dict[str, Tuple[int, int, int]] = {
    "generic": (176, 181, 190),
    "desk": (142, 91, 53),
    "table": (154, 104, 65),
    "low_table": (159, 111, 71),
    "laptop": (55, 63, 77),
    "lamp": (218, 181, 78),
    "cup": (235, 236, 225),
    "plant": (69, 148, 92),
    "book": (77, 115, 179),
    "chair": (151, 120, 97),
    "bench": (145, 105, 72),
    "sofa": (121, 134, 155),
    "bed": (172, 179, 196),
    "shelf": (126, 89, 61),
    "cube": (125, 155, 200),
    "sphere": (95, 169, 128),
    "cylinder": (105, 130, 190),
    "cone": (221, 174, 72),
    "monitor": (47, 55, 70),
    "keyboard": (62, 69, 82),
    "mouse": (80, 87, 98),
    "phone": (42, 47, 58),
    "vase": (188, 152, 112),
    "bottle": (90, 150, 160),
    "bowl": (218, 205, 185),
    "plate": (230, 224, 208),
    "clock": (196, 180, 130),
    "speaker": (70, 74, 84),
    "camera": (45, 50, 58),
    "microphone": (95, 95, 105),
    "telescope": (95, 110, 130),
    "robot_arm": (150, 150, 160),
    "printer": (185, 190, 196),
    "toolbox": (190, 75, 65),
    "easel": (150, 105, 70),
    "canvas": (230, 222, 205),
    "mirror": (176, 204, 220),
    "piano": (45, 38, 35),
    "rug": (170, 120, 90),
}


def render_scene(scene: SceneBuilder, output_path: Path, title: str = "SceneTest") -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.suffix.lower() == ".svg":
        output_path.write_text(render_svg(scene, title), encoding="utf-8")
        return
    try:
        _render_png(scene, output_path, title)
    except Exception:
        svg_path = output_path.with_suffix(".svg")
        svg_path.write_text(render_svg(scene, title), encoding="utf-8")


def render_svg(scene: SceneBuilder, title: str = "SceneTest", width: int = 1100, height: int = 780) -> str:
    transform = _transform(scene, width, height)
    bg = _background(scene.lighting_style)
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        f'<rect width="{width}" height="{height}" fill="{bg}"/>',
        '<rect x="40" y="70" width="1020" height="660" rx="18" fill="#f7f4ed" stroke="#d2c7b6"/>',
        f'<text x="55" y="42" font-family="Arial" font-size="26" font-weight="700" fill="#242832">{html.escape(title)}</text>',
        f'<text x="860" y="42" font-family="Arial" font-size="16" fill="#5d6470">lighting: {html.escape(scene.lighting_style)}</text>',
    ]
    cam = scene.camera
    x0, y0 = transform(cam.x_min, cam.y_min)
    x1, y1 = transform(cam.x_max, cam.y_max)
    lines.append(
        f'<rect x="{min(x0,x1):.1f}" y="{min(y0,y1):.1f}" width="{abs(x1-x0):.1f}" height="{abs(y1-y0):.1f}" '
        'fill="none" stroke="#3f6fb5" stroke-width="3" stroke-dasharray="10 8"/>'
    )
    for obj in sorted(scene.objects.values(), key=lambda item: item.bbox.min_z):
        lines.extend(_svg_object(obj, transform))
    lines.append("</svg>")
    return "\n".join(lines)


def _render_png(scene: SceneBuilder, output_path: Path, title: str) -> None:
    from PIL import Image, ImageDraw, ImageFont

    width, height = 1100, 780
    image = Image.new("RGB", (width, height), _background_rgb(scene.lighting_style))
    draw = ImageDraw.Draw(image)
    transform = _transform(scene, width, height)
    draw.rounded_rectangle((40, 70, 1060, 730), radius=18, fill=(247, 244, 237), outline=(210, 199, 182), width=2)
    try:
        font_title = ImageFont.truetype("Arial.ttf", 26)
        font_label = ImageFont.truetype("Arial.ttf", 15)
    except Exception:
        font_title = ImageFont.load_default()
        font_label = ImageFont.load_default()
    draw.text((55, 22), title, fill=(36, 40, 50), font=font_title)
    draw.text((860, 24), f"lighting: {scene.lighting_style}", fill=(93, 100, 112), font=font_label)
    cam = scene.camera
    x0, y0 = transform(cam.x_min, cam.y_min)
    x1, y1 = transform(cam.x_max, cam.y_max)
    draw.rectangle((min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)), outline=(63, 111, 181), width=3)
    for obj in sorted(scene.objects.values(), key=lambda item: item.bbox.min_z):
        bbox = obj.bbox
        ox0, oy0 = transform(bbox.min_x, bbox.min_y)
        ox1, oy1 = transform(bbox.max_x, bbox.max_y)
        fill = _object_rgb(obj)
        outline = (50, 54, 60)
        box = (min(ox0, ox1), min(oy0, oy1), max(ox0, ox1), max(oy0, oy1))
        if obj.shape == "sphere":
            draw.ellipse(box, fill=fill, outline=outline, width=2)
        elif obj.shape in {"cylinder", "cone"}:
            draw.rounded_rectangle(box, radius=12, fill=fill, outline=outline, width=2)
        else:
            draw.rounded_rectangle(box, radius=8, fill=fill, outline=outline, width=2)
        cx = (box[0] + box[2]) / 2
        cy = (box[1] + box[3]) / 2
        label = obj.id.replace("_", " ")
        draw.text((cx, cy), label, anchor="mm", fill=(24, 27, 31), font=font_label)
    image.save(output_path)


def _svg_object(obj: SceneObject, transform) -> list[str]:
    bbox = obj.bbox
    x0, y0 = transform(bbox.min_x, bbox.min_y)
    x1, y1 = transform(bbox.max_x, bbox.max_y)
    x = min(x0, x1)
    y = min(y0, y1)
    width = abs(x1 - x0)
    height = abs(y1 - y0)
    fill = _object_hex(obj)
    label = html.escape(obj.id.replace("_", " "))
    shape = obj.shape
    if shape == "sphere":
        body = f'<ellipse cx="{x + width/2:.1f}" cy="{y + height/2:.1f}" rx="{width/2:.1f}" ry="{height/2:.1f}" fill="{fill}" stroke="#32363c" stroke-width="2"/>'
    elif shape in {"cylinder", "cone"}:
        body = f'<rect x="{x:.1f}" y="{y:.1f}" width="{width:.1f}" height="{height:.1f}" rx="14" fill="{fill}" stroke="#32363c" stroke-width="2"/>'
    else:
        body = f'<rect x="{x:.1f}" y="{y:.1f}" width="{width:.1f}" height="{height:.1f}" rx="8" fill="{fill}" stroke="#32363c" stroke-width="2"/>'
    return [
        body,
        f'<text x="{x + width/2:.1f}" y="{y + height/2 + 5:.1f}" text-anchor="middle" font-family="Arial" font-size="15" font-weight="700" fill="#181b1f">{label}</text>',
    ]


def _transform(scene: SceneBuilder, width: int, height: int):
    scene_box = scene.scene_bbox()
    cam = scene.camera.bounds
    min_x = min(scene_box.min_x, cam.min_x) - 0.4
    max_x = max(scene_box.max_x, cam.max_x) + 0.4
    min_y = min(scene_box.min_y, cam.min_y) - 0.4
    max_y = max(scene_box.max_y, cam.max_y) + 0.4
    pad_left, pad_top = 70, 95
    draw_w, draw_h = width - 120, height - 130
    sx = draw_w / max(1e-6, max_x - min_x)
    sy = draw_h / max(1e-6, max_y - min_y)
    scale = min(sx, sy)
    offset_x = pad_left + (draw_w - (max_x - min_x) * scale) / 2
    offset_y = pad_top + (draw_h - (max_y - min_y) * scale) / 2

    def apply(x: float, y: float) -> Tuple[float, float]:
        px = offset_x + (x - min_x) * scale
        py = offset_y + (max_y - y) * scale
        return px, py

    return apply


def _object_rgb(obj: SceneObject) -> Tuple[int, int, int]:
    if obj.color in COLOR_MAP:
        return COLOR_MAP[obj.color]
    return TYPE_COLORS.get(obj.type, (180, 185, 190))


def _object_hex(obj: SceneObject) -> str:
    r, g, b = _object_rgb(obj)
    return f"#{r:02x}{g:02x}{b:02x}"


def _background(style: str) -> str:
    return {
        "warm": "#f2dfc3",
        "cyberpunk": "#151522",
        "minimal": "#e7e6e1",
        "medieval": "#dcc7a2",
        "futuristic": "#eaf2f8",
    }.get(style, "#e8eaed")


def _background_rgb(style: str) -> Tuple[int, int, int]:
    bg = _background(style).lstrip("#")
    return tuple(int(bg[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]
