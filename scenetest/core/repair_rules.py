"""Deterministic failure-guided repair rules."""

from __future__ import annotations

from typing import Dict, Iterable, List, Optional

from .contract_schema import SceneContract
from .scene_builder import SceneBuilder, TABLETOP_TYPES
from .test_runner import TestResult, run_tests


def repair_scene(
    scene: SceneBuilder,
    contract: SceneContract,
    failures: Iterable[TestResult],
) -> List[Dict[str, object]]:
    actions: List[Dict[str, object]] = []
    for failure in failures:
        hint = failure.repair_hint or {}
        action = str(hint.get("action", ""))
        if action == "create_object":
            object_id = str(hint["object"])
            if object_id not in scene.objects:
                created = _create_contract_object(scene, contract, object_id)
                if created:
                    actions.append({"action": "create_object", "object": object_id})
        elif action == "move_relation":
            subject_id = str(hint["subject"])
            target_id = str(hint["object"])
            relation = str(hint["relation"])
            if subject_id not in scene.objects:
                _create_contract_object(scene, contract, subject_id)
            if target_id not in scene.objects:
                _create_contract_object(scene, contract, target_id)
            if subject_id in scene.objects and target_id in scene.objects:
                scene.place_relation(subject_id, relation, target_id, float(hint.get("margin", 0.35)))
                actions.append({"action": "move_relation", "subject": subject_id, "relation": relation, "object": target_id})
        elif action == "set_material":
            object_id = str(hint["object"])
            if object_id in scene.objects:
                scene.set_material(object_id, material=str(hint["material"]))
                actions.append({"action": "set_material", "object": object_id, "material": str(hint["material"])})
        elif action == "set_color":
            object_id = str(hint["object"])
            if object_id in scene.objects:
                scene.set_material(object_id, color=str(hint["color"]))
                actions.append({"action": "set_color", "object": object_id, "color": str(hint["color"])})
        elif action == "set_lighting":
            scene.set_lighting(str(hint["style"]))
            actions.append({"action": "set_lighting", "style": str(hint["style"])})
        elif action == "auto_frame_camera":
            visible = contract.camera.visible_objects or contract.object_ids()
            scene.set_camera(contract.camera.view, visible, frame="auto")
            actions.append({"action": "auto_frame_camera", "objects": visible})
    _enforce_all_relations(scene, contract, actions)
    _enforce_style(scene, contract, actions)
    scene.repair_log.extend(actions)
    return actions


def repair_loop(
    scene: SceneBuilder,
    contract: SceneContract,
    tests: List[Dict[str, object]],
    max_iterations: int = 3,
) -> Dict[str, object]:
    history: List[Dict[str, object]] = []
    for iteration in range(max_iterations):
        results = run_tests(scene, tests)
        failures = [result for result in results if not result.passed]
        history.append(
            {
                "iteration": iteration,
                "failures": [failure.to_dict() for failure in failures],
            }
        )
        if not failures:
            break
        actions = repair_scene(scene, contract, failures)
        history[-1]["actions"] = actions
    final_results = run_tests(scene, tests)
    return {
        "scene": scene,
        "history": history,
        "final_results": final_results,
        "iterations": len([entry for entry in history if entry.get("actions")]),
    }


def _create_contract_object(scene: SceneBuilder, contract: SceneContract, object_id: str) -> bool:
    obj = contract.get_object(object_id)
    if not obj:
        return False
    kwargs: Dict[str, object] = {}
    if obj.material:
        kwargs["material"] = obj.material
    if obj.color:
        kwargs["color"] = obj.color
    relation = _primary_relation_for(contract, object_id)
    support = _support_for(contract, object_id)
    if support:
        kwargs["on"] = support
    if relation and relation["relation"] != "on":
        kwargs[relation["relation"]] = relation["object"]
    method_name = f"add_{obj.type}"
    if hasattr(scene, method_name):
        getattr(scene, method_name)(object_id, **kwargs)
    else:
        scene.add_object(object_id, obj.type, **kwargs)
    return True


def _primary_relation_for(contract: SceneContract, object_id: str) -> Optional[Dict[str, str]]:
    for relation in contract.relations:
        if relation.subject == object_id and relation.relation != "on":
            return {"relation": relation.relation, "object": relation.object}
    for relation in contract.relations:
        if relation.subject == object_id:
            return {"relation": relation.relation, "object": relation.object}
    return None


def _support_for(contract: SceneContract, object_id: str) -> Optional[str]:
    for relation in contract.relations:
        if relation.subject == object_id and relation.relation == "on":
            return relation.object
    obj = contract.get_object(object_id)
    if not obj or obj.type not in TABLETOP_TYPES:
        return None
    primary = _primary_relation_for(contract, object_id)
    if not primary:
        return None
    target_support = _support_for(contract, primary["object"])
    return target_support


def _enforce_all_relations(scene: SceneBuilder, contract: SceneContract, actions: List[Dict[str, object]]) -> None:
    for relation in contract.relations:
        if relation.subject not in scene.objects:
            _create_contract_object(scene, contract, relation.subject)
        if relation.object not in scene.objects:
            _create_contract_object(scene, contract, relation.object)
        if relation.subject in scene.objects and relation.object in scene.objects:
            scene.place_relation(relation.subject, relation.relation, relation.object, max(0.35, relation.margin))
            action = {
                "action": "enforce_relation",
                "subject": relation.subject,
                "relation": relation.relation,
                "object": relation.object,
            }
            if action not in actions:
                actions.append(action)


def _enforce_style(scene: SceneBuilder, contract: SceneContract, actions: List[Dict[str, object]]) -> None:
    for obj in contract.objects:
        if obj.id not in scene.objects:
            continue
        if obj.material and (scene.objects[obj.id].material or "").lower().find(obj.material.lower()) < 0:
            scene.set_material(obj.id, material=obj.material)
            actions.append({"action": "enforce_material", "object": obj.id, "material": obj.material})
        if obj.color and scene.objects[obj.id].color != obj.color:
            scene.set_material(obj.id, color=obj.color)
            actions.append({"action": "enforce_color", "object": obj.id, "color": obj.color})
    lighting = contract.style.get("lighting")
    if lighting and lighting.lower() not in scene.lighting_style.lower():
        scene.set_lighting(lighting)
        actions.append({"action": "enforce_lighting", "style": lighting})
    visible = contract.camera.visible_objects or contract.object_ids()
    scene.set_camera(contract.camera.view, visible, frame="auto")
