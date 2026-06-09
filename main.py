#!/usr/bin/env python3
"""SceneTest command-line entry point."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scenetest.agents.code_agent import CodeAgent
from scenetest.agents.contract_agent import ContractAgent
from scenetest.agents.deepseek_contract_agent import DeepSeekContractAgent
from scenetest.agents.repair_agent import RepairAgent
from scenetest.blender.exporter import export_blender_script
from scenetest.core.contract_schema import SceneContract
from scenetest.core.metrics import aggregate, write_summary_csv
from scenetest.core.test_compiler import compile_tests
from scenetest.core.test_runner import execute_scene_code, run_tests, summarize_results
from scenetest.rendering.topdown import render_scene


def cmd_run(args: argparse.Namespace) -> None:
    prompt = args.prompt or Path(args.prompt_file).read_text(encoding="utf-8").strip()
    contract = _contract_agent(args).parse(prompt, scene_id=args.scene_id)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    _run_contract(contract, out_dir, render=not args.no_render)
    print(f"Wrote run artifacts to {out_dir}")


def cmd_batch(args: argparse.Namespace) -> None:
    prompt_path = Path(args.prompts)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    rows: List[Dict[str, object]] = []
    for index, line in enumerate(prompt_path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        item = json.loads(line)
        prompt = item["prompt"]
        scene_id = item.get("id", f"scene_{index:02d}")
        contract = _contract_agent(args).parse(prompt, scene_id=scene_id)
        scene_dir = out_dir / scene_id
        method_rows = _run_contract(contract, scene_dir, render=not args.no_render)
        rows.extend(method_rows)
    summary = aggregate(rows)
    (out_dir / "raw_results.json").write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    write_summary_csv(summary, out_dir / "results.csv")
    print(f"Evaluated {len(rows)} method runs from {prompt_path}")
    print(f"Wrote summary to {out_dir / 'results.csv'}")


def cmd_render_blender(args: argparse.Namespace) -> None:
    config = _load_project_config()
    blender = _resolve_blender(args.blender or config.get("blender_path"))
    scene_json = Path(args.scene_json).resolve()
    output = Path(args.output).resolve()
    script = ROOT / "scripts" / "render_blender_scene.py"
    cmd = [
        blender,
        "--background",
        "--python",
        str(script),
        "--",
        "--scene-json",
        str(scene_json),
        "--output",
        str(output),
        "--resolution",
        args.resolution,
        "--engine",
        args.engine,
    ]
    subprocess.run(cmd, check=True)
    print(f"Wrote Blender render to {output}")


def cmd_self_check(args: argparse.Namespace) -> None:
    subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", str(ROOT / "tests")], check=True)


def cmd_demo(args: argparse.Namespace) -> None:
    from scenetest.demo.server import run_demo_server

    run_demo_server(host=args.host, port=args.port)


def _run_contract(contract: SceneContract, out_dir: Path, render: bool = True) -> List[Dict[str, object]]:
    out_dir.mkdir(parents=True, exist_ok=True)
    tests = compile_tests(contract)
    code_agent = CodeAgent()
    repair_agent = RepairAgent()
    (out_dir / "contract.json").write_text(json.dumps(contract.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
    (out_dir / "tests.json").write_text(json.dumps(tests, indent=2, ensure_ascii=False), encoding="utf-8")
    method_rows: List[Dict[str, object]] = []
    for method in ("single_pass", "contract_only"):
        code = code_agent.generate(contract, method=method)
        method_dir = out_dir / method
        method_dir.mkdir(parents=True, exist_ok=True)
        (method_dir / "scene.py").write_text(code, encoding="utf-8")
        scene, error = execute_scene_code(code)
        results = run_tests(scene, tests, error)
        summary = summarize_results(results)
        (method_dir / "test_results.json").write_text(
            json.dumps([result.to_dict() for result in results], indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        if scene:
            (method_dir / "scene.json").write_text(json.dumps(scene.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
            export_blender_script(scene, method_dir / "scene.blender.py")
            if render:
                render_scene(scene, method_dir / "render.png", title=f"{contract.id} / {method}")
        method_rows.append({"scene_id": contract.id, "method": method, "summary": summary})
    initial_code = code_agent.generate(contract, method="contract_only")
    initial_scene, error = execute_scene_code(initial_code)
    scenetest_dir = out_dir / "scenetest"
    scenetest_dir.mkdir(parents=True, exist_ok=True)
    if initial_scene is None:
        raise RuntimeError(error or "contract-only generation failed")
    repair = repair_agent.repair(initial_scene, contract, tests, max_iterations=3)
    final_scene = repair["scene"]
    final_results = repair["final_results"]
    final_summary = summarize_results(final_results)
    (scenetest_dir / "initial_scene.py").write_text(initial_code, encoding="utf-8")
    (scenetest_dir / "repaired_scene.py").write_text(final_scene.to_python(), encoding="utf-8")
    (scenetest_dir / "repair_history.json").write_text(json.dumps(repair["history"], indent=2, ensure_ascii=False), encoding="utf-8")
    (scenetest_dir / "test_results.json").write_text(
        json.dumps([result.to_dict() for result in final_results], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (scenetest_dir / "scene.json").write_text(json.dumps(final_scene.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
    export_blender_script(final_scene, scenetest_dir / "scene.blender.py")
    if render:
        render_scene(final_scene, scenetest_dir / "render.png", title=f"{contract.id} / SceneTest repaired")
    method_rows.append(
        {
            "scene_id": contract.id,
            "method": "scenetest",
            "summary": final_summary,
            "repair_iterations": repair["iterations"],
        }
    )
    return method_rows


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="SceneTest: contract-driven graphics unit tests")
    sub = parser.add_subparsers(required=True)
    run = sub.add_parser("run", help="run one prompt through SceneTest")
    run.add_argument("--prompt", help="prompt text")
    run.add_argument("--prompt-file", help="file containing prompt text")
    run.add_argument("--scene-id", default="demo_scene")
    run.add_argument("--out-dir", default=str(ROOT / "experiments" / "runs" / "demo_scene"))
    run.add_argument("--no-render", action="store_true")
    _add_contract_args(run)
    run.set_defaults(func=cmd_run)
    batch = sub.add_parser("batch", help="run a JSONL prompt set")
    batch.add_argument("--prompts", default=str(ROOT / "experiments" / "prompts.jsonl"))
    batch.add_argument("--out-dir", default=str(ROOT / "experiments" / "runs" / "batch"))
    batch.add_argument("--no-render", action="store_true")
    _add_contract_args(batch)
    batch.set_defaults(func=cmd_batch)
    render_blender = sub.add_parser("render-blender", help="render a scene.json through Blender")
    render_blender.add_argument("--scene-json", required=True)
    render_blender.add_argument("--output", required=True)
    render_blender.add_argument("--resolution", default="1024x768")
    render_blender.add_argument("--engine", default="BLENDER_WORKBENCH")
    render_blender.add_argument("--blender", default=None, help="path to Blender executable")
    render_blender.set_defaults(func=cmd_render_blender)
    self_check = sub.add_parser("self-check", help="run unit tests for the core pipeline")
    self_check.set_defaults(func=cmd_self_check)
    demo = sub.add_parser("demo", help="launch a local browser demo UI")
    demo.add_argument("--host", default="127.0.0.1")
    demo.add_argument("--port", default=7860, type=int)
    demo.set_defaults(func=cmd_demo)
    return parser


def _add_contract_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--contract-backend",
        choices=("deterministic", "deepseek"),
        default=None,
        help="contract extraction backend; defaults to config.json or deterministic",
    )
    parser.add_argument("--deepseek-model", default=None)
    parser.add_argument("--deepseek-base-url", default=None)
    parser.add_argument(
        "--no-llm-fallback",
        action="store_true",
        help="fail instead of falling back to deterministic parsing if DeepSeek is unavailable",
    )


def _contract_agent(args: argparse.Namespace):
    config = _load_project_config()
    backend = getattr(args, "contract_backend", None) or config.get("contract_backend", "deterministic")
    if backend == "deepseek":
        api_key = os.environ.get("DEEPSEEK_API_KEY") or config.get("deepseek_api_key")
        return DeepSeekContractAgent(
            api_key=api_key,
            model=args.deepseek_model or config.get("deepseek_model", "deepseek-v4-pro"),
            base_url=args.deepseek_base_url or config.get("deepseek_base_url", "https://api.deepseek.com"),
            fallback=not args.no_llm_fallback,
        )
    return ContractAgent()


def _load_project_config() -> Dict[str, Any]:
    path = ROOT / "config.json"
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {path}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def _resolve_blender(path: str | None) -> str:
    candidates = [
        path,
        shutil.which("blender"),
        "/Applications/Blender.app/Contents/MacOS/Blender",
        str(Path.home() / "Applications" / "Blender.app" / "Contents" / "MacOS" / "Blender"),
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return str(candidate)
    raise FileNotFoundError("Could not find Blender. Pass --blender /path/to/Blender.")


def main(argv: List[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "func", None) == cmd_run and not args.prompt and not args.prompt_file:
        parser.error("run requires --prompt or --prompt-file")
    args.func(args)


if __name__ == "__main__":
    main()
