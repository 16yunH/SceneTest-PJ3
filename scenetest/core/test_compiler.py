"""Compile a scene contract into executable graphics unit tests."""

from __future__ import annotations

from typing import Dict, List

from .contract_schema import SceneContract


def compile_tests(contract: SceneContract) -> List[Dict[str, object]]:
    tests: List[Dict[str, object]] = []
    for obj in contract.required_objects():
        tests.append({"type": "exists", "object": obj.id})
        if obj.material:
            tests.append({"type": "material", "object": obj.id, "material": obj.material})
        if obj.color:
            tests.append({"type": "color", "object": obj.id, "color": obj.color})
    for relation in contract.relations:
        tests.append(
            {
                "type": "relation",
                "subject": relation.subject,
                "relation": relation.relation,
                "object": relation.object,
                "margin": relation.margin,
            }
        )
    lighting = contract.style.get("lighting")
    if lighting:
        tests.append({"type": "lighting", "style": lighting})
    for object_id in contract.camera.visible_objects:
        tests.append({"type": "visible", "object": object_id})
    return tests
