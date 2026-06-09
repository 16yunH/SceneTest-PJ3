"""Small local web demo for presentation-time SceneTest runs."""

from __future__ import annotations

import html
import json
import mimetypes
import re
import subprocess
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[2]
RUN_ROOT = ROOT / "experiments" / "runs" / "demo_live"
DEFAULT_PROMPT = (
    "Create a cozy desk scene with a wooden desk, a laptop on the desk, "
    "a warm lamp to the left of the laptop, a ceramic coffee cup to the right "
    "of the laptop, and a green plant behind the laptop. Use warm lighting "
    "and make every object visible."
)


def run_demo_server(host: str = "127.0.0.1", port: int = 7860) -> None:
    RUN_ROOT.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer((host, port), DemoHandler)
    url = f"http://{host}:{port}"
    print(f"SceneTest demo running at {url}")
    print("Press Ctrl-C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping SceneTest demo.")
    finally:
        server.server_close()


class DemoHandler(BaseHTTPRequestHandler):
    server_version = "SceneTestDemo/1.0"

    def log_message(self, fmt: str, *args: object) -> None:
        print(f"[demo] {self.address_string()} - {fmt % args}")

    def do_GET(self) -> None:
        if self.path == "/" or self.path.startswith("/?"):
            self._send_html(_index_html())
            return
        if self.path.startswith("/artifact/"):
            self._send_artifact(self.path.removeprefix("/artifact/"))
            return
        self.send_error(404)

    def do_POST(self) -> None:
        if self.path != "/api/run":
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            result = _run_scene(payload)
            self._send_json(result)
        except Exception as exc:  # pragma: no cover - surfaced in browser demo
            self._send_json({"ok": False, "error": f"{type(exc).__name__}: {exc}"}, status=500)

    def _send_html(self, body: str) -> None:
        data = body.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_json(self, payload: Dict[str, Any], status: int = 200) -> None:
        data = json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_artifact(self, raw_path: str) -> None:
        rel = Path(unquote(raw_path))
        if rel.is_absolute() or ".." in rel.parts:
            self.send_error(400)
            return
        path = (RUN_ROOT / rel).resolve()
        if not str(path).startswith(str(RUN_ROOT.resolve())) or not path.is_file():
            self.send_error(404)
            return
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def _run_scene(payload: Dict[str, Any]) -> Dict[str, Any]:
    prompt = str(payload.get("prompt") or DEFAULT_PROMPT).strip()
    backend = str(payload.get("backend") or "deepseek")
    render_blender = bool(payload.get("render_blender", True))
    if backend not in {"deepseek", "deterministic"}:
        raise ValueError("backend must be deepseek or deterministic")

    scene_id = _safe_id(payload.get("scene_id") or f"demo_{int(time.time())}")
    out_dir = RUN_ROOT / scene_id
    out_dir.mkdir(parents=True, exist_ok=True)
    prompt_file = out_dir / "prompt.txt"
    prompt_file.write_text(prompt + "\n", encoding="utf-8")

    run_cmd = [
        sys.executable,
        str(ROOT / "main.py"),
        "run",
        "--contract-backend",
        backend,
        "--scene-id",
        scene_id,
        "--out-dir",
        str(out_dir),
        "--prompt-file",
        str(prompt_file),
    ]
    if backend == "deepseek":
        run_cmd.append("--no-llm-fallback")
    started = time.time()
    run_proc = subprocess.run(run_cmd, cwd=ROOT, text=True, capture_output=True, timeout=180)
    elapsed = time.time() - started
    if run_proc.returncode != 0:
        return {
            "ok": False,
            "scene_id": scene_id,
            "backend": backend,
            "elapsed_sec": round(elapsed, 2),
            "stdout": run_proc.stdout,
            "stderr": run_proc.stderr,
        }

    blender_result: Dict[str, Any] | None = None
    if render_blender:
        blender_output = out_dir / "scenetest" / "render_blender.png"
        blender_cmd = [
            sys.executable,
            str(ROOT / "main.py"),
            "render-blender",
            "--scene-json",
            str(out_dir / "scenetest" / "scene.json"),
            "--output",
            str(blender_output),
            "--resolution",
            "1024x768",
        ]
        bstart = time.time()
        blender_proc = subprocess.run(blender_cmd, cwd=ROOT, text=True, capture_output=True, timeout=180)
        blender_result = {
            "ok": blender_proc.returncode == 0,
            "elapsed_sec": round(time.time() - bstart, 2),
            "stdout": blender_proc.stdout,
            "stderr": blender_proc.stderr,
            "url": _artifact_url(scene_id, "scenetest/render_blender.png") if blender_output.exists() else None,
        }

    return {
        "ok": True,
        "scene_id": scene_id,
        "backend": backend,
        "elapsed_sec": round(elapsed, 2),
        "stdout": run_proc.stdout,
        "stderr": run_proc.stderr,
        "contract": _read_json(out_dir / "contract.json"),
        "tests": _read_json(out_dir / "tests.json"),
        "methods": {
            method: _method_summary(out_dir, scene_id, method)
            for method in ("single_pass", "contract_only", "scenetest")
        },
        "repair_history": _read_json(out_dir / "scenetest" / "repair_history.json"),
        "blender": blender_result,
    }


def _method_summary(out_dir: Path, scene_id: str, method: str) -> Dict[str, Any]:
    results = _read_json(out_dir / method / "test_results.json")
    passed = sum(1 for item in results if item.get("status") == "pass")
    total = len(results)
    failures = [item for item in results if item.get("status") != "pass"]
    return {
        "passed": passed,
        "total": total,
        "pass_rate": passed / total if total else 0.0,
        "failures": failures,
        "render_url": _artifact_url(scene_id, f"{method}/render.png"),
        "scene_url": _artifact_url(scene_id, f"{method}/scene.json"),
        "test_results_url": _artifact_url(scene_id, f"{method}/test_results.json"),
    }


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _artifact_url(scene_id: str, rel: str) -> str:
    return f"/artifact/{scene_id}/{rel}"


def _safe_id(value: object) -> str:
    text = re.sub(r"[^a-zA-Z0-9_-]+", "_", str(value).strip())[:64].strip("_")
    return text or f"demo_{int(time.time())}"


def _index_html() -> str:
    prompt = html.escape(DEFAULT_PROMPT)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>SceneTest Live Demo</title>
  <style>
    :root {{
      --bg: #f4f0e8;
      --ink: #18212b;
      --muted: #617083;
      --panel: #ffffff;
      --line: #d7dde5;
      --blue: #2f6fad;
      --green: #2f8d62;
      --amber: #c47c21;
      --red: #bd4a4a;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font-family: Arial, Helvetica, sans-serif;
    }}
    header {{
      display: flex;
      justify-content: space-between;
      align-items: flex-end;
      gap: 24px;
      padding: 28px 36px 18px;
      border-top: 8px solid #243447;
      border-bottom: 1px solid var(--line);
    }}
    h1 {{ margin: 0; font-size: 30px; letter-spacing: 0; }}
    .repo {{ color: var(--muted); font-size: 14px; }}
    main {{ padding: 24px 36px 40px; max-width: 1480px; margin: 0 auto; }}
    .control {{
      display: grid;
      grid-template-columns: minmax(420px, 1fr) 320px;
      gap: 18px;
      align-items: stretch;
    }}
    textarea {{
      width: 100%;
      height: 138px;
      resize: vertical;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 14px;
      font-size: 16px;
      line-height: 1.45;
      color: var(--ink);
      background: white;
    }}
    .side {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 16px;
      display: grid;
      grid-template-columns: 1fr;
      gap: 12px;
    }}
    label {{ display: block; font-size: 13px; color: var(--muted); margin-bottom: 6px; }}
    select {{
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 10px;
      font-size: 15px;
      background: white;
    }}
    .checkline {{ display: flex; align-items: center; gap: 8px; color: var(--ink); font-size: 15px; }}
    button {{
      border: 0;
      border-radius: 6px;
      background: var(--blue);
      color: white;
      padding: 12px 16px;
      font-size: 16px;
      font-weight: 700;
      cursor: pointer;
    }}
    button:disabled {{ opacity: 0.55; cursor: default; }}
    #status {{ min-height: 24px; margin: 18px 0; color: var(--muted); font-size: 15px; }}
    .metrics {{
      display: grid;
      grid-template-columns: repeat(4, minmax(160px, 1fr));
      gap: 12px;
      margin-bottom: 18px;
    }}
    .metric {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 14px 16px;
    }}
    .metric b {{ display: block; font-size: 24px; margin-bottom: 4px; }}
    .metric span {{ color: var(--muted); font-size: 13px; }}
    .renders {{
      display: grid;
      grid-template-columns: repeat(4, minmax(220px, 1fr));
      gap: 14px;
      margin-bottom: 18px;
    }}
    figure {{
      margin: 0;
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 10px;
    }}
    figure img {{
      width: 100%;
      aspect-ratio: 4 / 3;
      object-fit: contain;
      background: #eef1f4;
      border-radius: 4px;
      display: block;
    }}
    figcaption {{
      margin-top: 8px;
      font-size: 13px;
      color: var(--muted);
      display: flex;
      justify-content: space-between;
      gap: 8px;
    }}
    .details {{
      display: grid;
      grid-template-columns: repeat(3, minmax(260px, 1fr));
      gap: 14px;
    }}
    section.panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 14px;
      min-width: 0;
    }}
    h2 {{ margin: 0 0 10px; font-size: 17px; }}
    pre {{
      margin: 0;
      max-height: 360px;
      overflow: auto;
      border-radius: 4px;
      background: #111827;
      color: #e5e7eb;
      padding: 12px;
      font-size: 12px;
      line-height: 1.42;
      white-space: pre-wrap;
      word-break: break-word;
    }}
    .ok {{ color: var(--green); }}
    .bad {{ color: var(--red); }}
    @media (max-width: 980px) {{
      .control, .details {{ grid-template-columns: 1fr; }}
      .metrics, .renders {{ grid-template-columns: repeat(2, minmax(160px, 1fr)); }}
    }}
  </style>
</head>
<body>
  <header>
    <div>
      <h1>SceneTest Live Demo</h1>
      <div class="repo">Local SceneTest Demo</div>
    </div>
    <div class="repo">Contract -> Tests -> Repair -> Blender Render</div>
  </header>
  <main>
    <div class="control">
      <textarea id="prompt">{prompt}</textarea>
      <div class="side">
        <div>
          <label for="backend">Backend</label>
          <select id="backend">
            <option value="deepseek" selected>DeepSeek from local config</option>
            <option value="deterministic">Deterministic offline</option>
          </select>
        </div>
        <label class="checkline"><input type="checkbox" id="blender" checked /> Blender render</label>
        <button id="run">Run SceneTest</button>
      </div>
    </div>
    <div id="status">Ready.</div>
    <div id="output"></div>
  </main>
  <script>
    const runButton = document.getElementById("run");
    const statusEl = document.getElementById("status");
    const output = document.getElementById("output");

    runButton.addEventListener("click", async () => {{
      runButton.disabled = true;
      output.innerHTML = "";
      statusEl.textContent = "Running SceneTest...";
      try {{
        const response = await fetch("/api/run", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify({{
            prompt: document.getElementById("prompt").value,
            backend: document.getElementById("backend").value,
            render_blender: document.getElementById("blender").checked
          }})
        }});
        const data = await response.json();
        if (!data.ok) {{
          statusEl.innerHTML = "<span class='bad'>Run failed.</span>";
          output.innerHTML = panel("Error", data.error || data.stderr || JSON.stringify(data, null, 2));
          return;
        }}
        statusEl.innerHTML = `<span class="ok">Completed ${{data.scene_id}}</span> in ${{data.elapsed_sec}}s`;
        output.innerHTML = render(data);
      }} catch (error) {{
        statusEl.innerHTML = "<span class='bad'>Run failed.</span>";
        output.innerHTML = panel("Error", String(error));
      }} finally {{
        runButton.disabled = false;
      }}
    }});

    function render(data) {{
      const methods = data.methods;
      const final = methods.scenetest;
      const failures0 = methods.contract_only.failures.length;
      const blenderUrl = data.blender && data.blender.url;
      return `
        <div class="metrics">
          <div class="metric"><b>${{data.backend}}</b><span>contract backend</span></div>
          <div class="metric"><b>${{methods.single_pass.passed}}/${{methods.single_pass.total}}</b><span>single-pass tests</span></div>
          <div class="metric"><b>${{methods.contract_only.passed}}/${{methods.contract_only.total}}</b><span>contract-only tests</span></div>
          <div class="metric"><b>${{final.passed}}/${{final.total}}</b><span>SceneTest tests</span></div>
        </div>
        <div class="renders">
          ${{figure(methods.single_pass.render_url, "Single-pass", pct(methods.single_pass.pass_rate))}}
          ${{figure(methods.contract_only.render_url, "Contract-only", pct(methods.contract_only.pass_rate))}}
          ${{figure(methods.scenetest.render_url, "SceneTest repaired", pct(methods.scenetest.pass_rate))}}
          ${{blenderUrl ? figure(blenderUrl, "Blender final", data.blender.ok ? "rendered" : "failed") : ""}}
        </div>
        <div class="details">
          ${{panel("Scene Contract", JSON.stringify(data.contract, null, 2))}}
          ${{panel("Contract-only Failures", failures0 ? JSON.stringify(methods.contract_only.failures, null, 2) : "No failures")}}
          ${{panel("Repair History", JSON.stringify(data.repair_history, null, 2))}}
        </div>
      `;
    }}

    function pct(value) {{
      return `${{Math.round(value * 100)}}%`;
    }}

    function figure(src, title, meta) {{
      return `<figure><img src="${{src}}" alt="${{title}}"><figcaption><b>${{title}}</b><span>${{meta}}</span></figcaption></figure>`;
    }}

    function panel(title, value) {{
      return `<section class="panel"><h2>${{title}}</h2><pre>${{escapeHtml(value)}}</pre></section>`;
    }}

    function escapeHtml(value) {{
      return String(value).replace(/[&<>"']/g, (c) => ({{ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }}[c]));
    }}
  </script>
</body>
</html>"""
