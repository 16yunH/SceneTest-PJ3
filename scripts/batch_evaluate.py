#!/usr/bin/env python3
"""Convenience wrapper for the default SceneTest experiment."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from main import main


if __name__ == "__main__":
    main(
        [
            "batch",
            "--prompts",
            str(ROOT / "experiments" / "prompts.jsonl"),
            "--out-dir",
            str(ROOT / "experiments" / "runs" / "batch"),
        ]
    )
