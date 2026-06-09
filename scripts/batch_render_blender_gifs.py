#!/usr/bin/env python3
"""Batch-render Blender stills and turntable GIFs for SceneTest runs."""

from __future__ import annotations

import argparse
import html
import json
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUN_DIR = ROOT / "experiments" / "runs" / "real_api_50_full_after_fix"
DEFAULT_GALLERY_DIR = ROOT / "deliverables" / "blender_gallery"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render all SceneTest final scenes through Blender turntable GIFs.")
    parser.add_argument("--run-dir", default=str(DEFAULT_RUN_DIR))
    parser.add_argument("--gallery-dir", default=str(DEFAULT_GALLERY_DIR))
    parser.add_argument("--blender", default=None)
    parser.add_argument("--resolution", default="720x540")
    parser.add_argument("--frames", type=int, default=16)
    parser.add_argument("--duration-ms", type=int, default=240)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--skip-existing", action="store_true")
    parser.add_argument("--keep-frames", action="store_true")
    parser.add_argument("--engine", default="BLENDER_WORKBENCH")
    return parser.parse_args()


def resolve_blender(explicit: str | None) -> str:
    candidates = [
        explicit,
        shutil.which("blender"),
        "/Applications/Blender.app/Contents/MacOS/Blender",
        str(Path.home() / "Applications" / "Blender.app" / "Contents" / "MacOS" / "Blender"),
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return str(candidate)
    raise FileNotFoundError("Could not find Blender. Pass --blender /path/to/Blender.")


def scene_items(run_dir: Path) -> list[tuple[str, Path]]:
    by_id = {scene_json.parents[1].name: scene_json for scene_json in run_dir.glob("*/scenetest/scene.json")}
    prompt_path = ROOT / "experiments" / "prompts.jsonl"
    ordered = []
    if prompt_path.exists():
        for line in prompt_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            scene_id = json.loads(line)["id"]
            if scene_id in by_id:
                ordered.append((scene_id, by_id.pop(scene_id)))
    ordered.extend((scene_id, by_id[scene_id]) for scene_id in sorted(by_id))
    return ordered


def compose_gif(frames_dir: Path, output: Path, duration_ms: int, label: str) -> None:
    frame_paths = sorted(frames_dir.glob("frame_*.png"))
    if not frame_paths:
        raise FileNotFoundError(f"No rendered frames in {frames_dir}")
    frames = []
    for frame_path in frame_paths:
        image = Image.open(frame_path).convert("RGB")
        frames.append(_label_frame(image, label))
    output.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(
        output,
        save_all=True,
        append_images=frames[1:],
        duration=duration_ms,
        loop=0,
        optimize=True,
    )


def _label_frame(image: Image.Image, label: str) -> Image.Image:
    image = image.copy()
    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.truetype("Arial.ttf", 22)
    except OSError:
        font = ImageFont.load_default()
    pad = 10
    text = label.replace("_", " ")
    bbox = draw.textbbox((0, 0), text, font=font)
    width = bbox[2] - bbox[0] + pad * 2
    height = bbox[3] - bbox[1] + pad * 2
    draw.rounded_rectangle((12, 12, 12 + width, 12 + height), radius=8, fill=(20, 24, 30))
    draw.text((12 + pad, 12 + pad - 1), text, fill=(245, 246, 248), font=font)
    return image


def render_one(
    blender: str,
    scene_id: str,
    scene_json: Path,
    *,
    resolution: str,
    frames: int,
    duration_ms: int,
    engine: str,
    skip_existing: bool,
    keep_frames: bool,
) -> dict[str, str]:
    scene_dir = scene_json.parent
    frames_dir = scene_dir / "blender_turntable_frames"
    still_output = scene_dir / "blender_still.png"
    gif_output = scene_dir / "turntable.gif"
    if skip_existing and still_output.exists() and gif_output.exists():
        return {"scene_id": scene_id, "still": str(still_output), "gif": str(gif_output), "status": "skipped"}
    if frames_dir.exists():
        for old in frames_dir.glob("frame_*.png"):
            old.unlink()
    cmd = [
        blender,
        "--background",
        "--python",
        str(ROOT / "scripts" / "render_blender_turntable.py"),
        "--",
        "--scene-json",
        str(scene_json),
        "--frames-dir",
        str(frames_dir),
        "--still-output",
        str(still_output),
        "--frames",
        str(frames),
        "--resolution",
        resolution,
        "--engine",
        engine,
    ]
    subprocess.run(cmd, cwd=ROOT, check=True)
    compose_gif(frames_dir, gif_output, duration_ms, scene_id)
    if not keep_frames:
        shutil.rmtree(frames_dir, ignore_errors=True)
    return {"scene_id": scene_id, "still": str(still_output), "gif": str(gif_output), "status": "rendered"}


def write_gallery(rows: list[dict[str, str]], gallery_dir: Path) -> None:
    gallery_dir.mkdir(parents=True, exist_ok=True)
    tiles = []
    for row in rows:
        scene_id = row["scene_id"]
        gif_src = Path(row["gif"])
        still_src = Path(row["still"])
        gif_dst = gallery_dir / f"{scene_id}.gif"
        still_dst = gallery_dir / f"{scene_id}.png"
        shutil.copy2(gif_src, gif_dst)
        shutil.copy2(still_src, still_dst)
        tiles.append(
            f"""
      <figure>
        <img src="{html.escape(gif_dst.name)}" alt="{html.escape(scene_id)} turntable" loading="lazy">
        <figcaption>{html.escape(scene_id.replace("_", " "))}</figcaption>
      </figure>"""
        )
    index = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>SceneTest Blender Turntables</title>
  <style>
    body {{ margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: #f5f6f8; color: #16202b; }}
    header {{ padding: 28px 32px 18px; background: #202936; color: white; }}
    h1 {{ margin: 0 0 8px; font-size: 28px; }}
    p {{ margin: 0; color: #c8d1dc; }}
    main {{ padding: 24px; display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 18px; }}
    figure {{ margin: 0; background: white; border: 1px solid #d9dee7; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 5px rgba(20, 28, 38, .08); }}
    img {{ display: block; width: 100%; aspect-ratio: 4 / 3; object-fit: cover; background: #d9dee7; }}
    figcaption {{ padding: 10px 12px; font-weight: 700; font-size: 14px; }}
  </style>
</head>
<body>
  <header>
    <h1>SceneTest Blender Turntables</h1>
    <p>50 text prompts rendered from final SceneTest scene.json outputs.</p>
  </header>
  <main>
{''.join(tiles)}
  </main>
</body>
</html>
"""
    (gallery_dir / "index.html").write_text(index, encoding="utf-8")


def display_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(ROOT))
    except ValueError:
        return resolved.name


def main() -> None:
    args = parse_args()
    run_dir = Path(args.run_dir).resolve()
    gallery_dir = Path(args.gallery_dir).resolve()
    blender = resolve_blender(args.blender)
    items = scene_items(run_dir)
    if args.limit:
        items = items[: args.limit]
    if not items:
        raise FileNotFoundError(f"No scenetest/scene.json files found under {run_dir}")
    rows = []
    for index, (scene_id, scene_json) in enumerate(items, start=1):
        print(f"[{index}/{len(items)}] Rendering {scene_id}")
        rows.append(
            render_one(
                blender,
                scene_id,
                scene_json,
                resolution=args.resolution,
                frames=args.frames,
                duration_ms=args.duration_ms,
                engine=args.engine,
                skip_existing=args.skip_existing,
                keep_frames=args.keep_frames,
            )
        )
    write_gallery(rows, gallery_dir)
    manifest = {
        "run_dir": display_path(run_dir),
        "gallery_dir": display_path(gallery_dir),
        "count": len(rows),
        "frames": args.frames,
        "resolution": args.resolution,
        "rows": [
            {
                **row,
                "still": display_path(Path(row["still"])),
                "gif": display_path(Path(row["gif"])),
            }
            for row in rows
        ],
    }
    (gallery_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Wrote gallery to {gallery_dir / 'index.html'}")


if __name__ == "__main__":
    main()
