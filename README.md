# SceneTest

SceneTest is a contract-driven prototype for agentic text-to-3D scene generation. It converts a prompt into a structured scene contract, compiles executable graphics unit tests, runs generated scene code, and uses failed tests to guide localized repairs.

The implementation is reproducible without API keys. It uses a deterministic local Contract Agent by default, supports an optional DeepSeek-backed Contract Agent, evaluates all scenes with an in-memory SceneBuilder, writes top-down preview images, and can render `scene.json` artifacts through Blender.

Code: this repository.

## Project Structure

```text
SceneTest/
  main.py
  scenetest/
    agents/          contract, code, and repair agents
    core/            schema, scene builder, tests, metrics, repair rules
    blender/         optional Blender Python exporter
    rendering/       top-down PNG/SVG preview renderer
  experiments/
    prompts.jsonl    50-prompt benchmark
    runs/            generated experiment outputs
  scripts/
    render_blender_scene.py
  tests/
    test_pipeline.py
```

## Quick Start

Set up the local environment with `uv`:

```bash
# from the repository root
uv sync
```

Run the core self-check:

```bash
.venv/bin/python main.py self-check
```

Run the default 50-prompt deterministic experiment:

```bash
.venv/bin/python main.py batch --out-dir experiments/runs/batch --contract-backend deterministic
```

Run the 50-prompt live DeepSeek experiment without deterministic fallback:

```bash
.venv/bin/python main.py batch \
  --out-dir experiments/runs/real_api_50_full_after_fix \
  --contract-backend deepseek \
  --no-llm-fallback
```

Run one custom prompt:

```bash
.venv/bin/python main.py run \
  --scene-id demo \
  --out-dir experiments/runs/demo \
  --prompt "Create a cozy desk scene with a laptop on a wooden desk, a lamp to the left of the laptop, a coffee cup to the right, and a plant behind the laptop. Use warm lighting."
```

## Live Presentation Demo

Launch the local web demo:

```bash
# from the repository root
.venv/bin/python main.py demo --port 7860
```

Open <http://127.0.0.1:7860>. The page accepts a prompt, runs the full SceneTest loop, and displays:

- Scene Contract JSON
- single-pass, contract-only, and repaired SceneTest renders
- test pass counts and failed tests
- repair history
- optional Blender final render

For a live DeepSeek demonstration, keep the local-only `config.json` in this directory and select the DeepSeek backend in the page. The real `config.json` is ignored by Git and is not uploaded.

Each run writes:

- `contract.json`
- `tests.json`
- `single_pass/scene.py`
- `contract_only/scene.py`
- `scenetest/repaired_scene.py`
- `test_results.json`
- `render.png`
- `scene.blender.py`

## Optional DeepSeek Contract Agent

SceneTest does not track real API keys. `config.json` is git-ignored; use `config.example.json` as the tracked template.

For live DeepSeek contract extraction, either export the key in the current shell and select the DeepSeek backend:

```bash
export DEEPSEEK_API_KEY="your_key_here"
.venv/bin/python main.py run \
  --contract-backend deepseek \
  --no-llm-fallback \
  --scene-id deepseek_live \
  --out-dir experiments/runs/deepseek_live \
  --prompt "Create a cozy desk scene with a laptop on a wooden desk, a lamp to the left, a cup to the right, and warm lighting."
```

Without `--no-llm-fallback`, the DeepSeek backend falls back to the deterministic parser if the API is unavailable.

Or create a local-only `config.json`:

```json
{
  "contract_backend": "deepseek",
  "deepseek_api_key": "your_key_here",
  "deepseek_base_url": "https://api.deepseek.com",
  "deepseek_model": "deepseek-v4-pro",
  "blender_path": "/Applications/Blender.app/Contents/MacOS/Blender",
  "code_url": "https://github.com/<your-github-user>/SceneTest-PJ3"
}
```

## Optional Blender Rendering

If Blender is installed, render any generated `scene.json`:

```bash
.venv/bin/python main.py render-blender \
  --scene-json experiments/runs/batch/desk_cozy/scenetest/scene.json \
  --output experiments/runs/batch/desk_cozy/scenetest/render_blender.png \
  --resolution 1024x768
```

The project does not require Blender for automated evaluation; Blender is only used for higher-fidelity final rendering.

To generate Blender still images and 360-degree turntable GIFs for all 50 final SceneTest scenes:

```bash
.venv/bin/python scripts/batch_render_blender_gifs.py \
  --run-dir experiments/runs/real_api_50_full_after_fix \
  --gallery-dir deliverables/blender_gallery \
  --frames 16 \
  --duration-ms 240 \
  --resolution 720x540
```

This writes `blender_still.png` and `turntable.gif` under each `scenetest/` run directory, and also builds a browsable local gallery at `deliverables/blender_gallery/index.html`.

## Verified Closed Loop

The checked live DeepSeek benchmark evaluates 50 prompts across three methods. The real API contracts produced 850 executable tests:

```text
single_pass:   599/850 = 0.7047 overall contract pass rate
contract_only: 683/850 = 0.8035 overall contract pass rate
scenetest:     850/850 = 1.0000 overall contract pass rate
```

For a no-key reproducible local baseline, run the deterministic contract backend:

```text
single_pass:   580/822 = 0.7056 overall contract pass rate
contract_only: 661/822 = 0.8041 overall contract pass rate
scenetest:     822/822 = 1.0000 overall contract pass rate
```

The `desk_cozy` example demonstrates the repair loop clearly: contract-only generation fails the cup-right-of-laptop relation and warm-lighting test, then SceneTest repairs both and reaches a fully passing final `test_results.json`.

## Method

SceneTest uses three explicit intermediate artifacts:

1. `Scene Contract`: objects, relations, style, and camera visibility requirements.
2. `Graphics Unit Tests`: object existence, material/color, spatial relations, lighting, and visibility tests.
3. `Failure-Guided Repair`: deterministic local edits such as creating missing objects, moving objects according to failed relations, replacing materials, and auto-framing the camera.

This avoids whole-scene regeneration after every failure and makes prompt alignment measurable.
