#!/usr/bin/env node
import { spawnSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const python = process.env.PYTHON || path.join(root, ".venv", "bin", "python");
const script = path.join(root, "scripts", "build_presentation.py");

const result = spawnSync(python, [script], {
  cwd: root,
  stdio: "inherit",
});

process.exit(result.status ?? 1);
