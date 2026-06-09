"""Repair Agent wrapper around deterministic rules."""

from __future__ import annotations

from typing import Dict, List

from scenetest.core.contract_schema import SceneContract
from scenetest.core.repair_rules import repair_loop
from scenetest.core.scene_builder import SceneBuilder


class RepairAgent:
    def repair(self, scene: SceneBuilder, contract: SceneContract, tests: List[Dict[str, object]], max_iterations: int = 3) -> Dict[str, object]:
        return repair_loop(scene, contract, tests, max_iterations=max_iterations)
