"""Code Agent that emits helper-API scene programs."""

from __future__ import annotations

import hashlib
from typing import Dict, List, Optional

from scenetest.core.contract_schema import SceneContract
from scenetest.core.scene_builder import TABLETOP_TYPES


RELATION_PARAM = {
    "left_of": "left_of",
    "right_of": "right_of",
    "behind": "behind",
    "in_front_of": "in_front_of",
    "near": "near",
}

BUILDER_METHOD_TYPES = {
    "table",
    "desk",
    "low_table",
    "laptop",
    "lamp",
    "cup",
    "book",
    "plant",
    "chair",
    "bench",
    "sofa",
    "bed",
    "shelf",
    "cube",
    "sphere",
    "cylinder",
    "cone",
}

FLIP_RELATION = {
    "left_of": "right_of",
    "right_of": "left_of",
    "behind": "in_front_of",
    "in_front_of": "behind",
}


class CodeAgent:
    def generate(self, contract: SceneContract, method: str = "contract_only") -> str:
        seed = int(hashlib.sha1((contract.id + method).encode("utf-8")).hexdigest()[:8], 16)
        omitted = self._omitted_object(contract, method, seed)
        flipped = self._flipped_relation(contract, method, seed)
        lines = [
            "from scenetest.core.scene_builder import SceneBuilder",
            "",
            "scene = SceneBuilder()",
        ]
        for object_id in _ordered_object_ids(contract):
            if object_id == omitted:
                continue
            obj = contract.get_object(object_id)
            if not obj:
                continue
            params = self._params_for(contract, object_id)
            if flipped and flipped["subject"] == object_id:
                relation = flipped["relation"]
                if relation in FLIP_RELATION:
                    target = params.pop(RELATION_PARAM[relation], None)
                    if target:
                        params[RELATION_PARAM[FLIP_RELATION[relation]]] = target
                elif relation == "on":
                    params.pop("on", None)
            material = obj.material
            color = obj.color
            if method in {"single_pass", "contract_only"} and obj.material and seed % 3 == 0:
                material = None
            args = [repr(object_id)]
            kwargs = []
            if material:
                kwargs.append(f"material={material!r}")
            if color:
                kwargs.append(f"color={color!r}")
            for key in ("on", "left_of", "right_of", "behind", "in_front_of", "near"):
                if key in params and params[key] != omitted:
                    kwargs.append(f"{key}={params[key]!r}")
            distance = 0.35 if method != "single_pass" else 0.12
            kwargs.append(f"distance={distance!r}")
            method_name = f"add_{obj.type}"
            if obj.type in BUILDER_METHOD_TYPES:
                lines.append(f"scene.{method_name}({', '.join(args + kwargs)})")
            else:
                lines.append(f"scene.add_object({', '.join(args + [repr(obj.type)] + kwargs)})")
        lighting = str(contract.style.get("lighting", "neutral"))
        if method in {"single_pass", "contract_only"} and seed % 2 == 0:
            lighting = "neutral"
        lines.append(f"scene.set_lighting(style={lighting!r})")
        frame = "default" if method in {"single_pass", "contract_only"} else "auto"
        lines.append(
            "scene.set_camera("
            f"view={contract.camera.view!r}, "
            f"target_objects={contract.camera.visible_objects!r}, "
            f"frame={frame!r})"
        )
        return "\n".join(lines) + "\n"

    def _omitted_object(self, contract: SceneContract, method: str, seed: int) -> Optional[str]:
        if method == "ideal":
            return None
        candidates = [obj.id for obj in contract.objects if obj.type not in {"desk", "table", "low_table"}]
        if not candidates:
            return None
        if method == "single_pass" or seed % 4 == 0:
            return candidates[seed % len(candidates)]
        return None

    def _flipped_relation(self, contract: SceneContract, method: str, seed: int) -> Optional[Dict[str, str]]:
        if method == "ideal" or not contract.relations:
            return None
        flippable = [rel for rel in contract.relations if rel.relation in FLIP_RELATION or rel.relation == "on"]
        if not flippable:
            return None
        rel = flippable[(seed // 7) % len(flippable)]
        return {"subject": rel.subject, "relation": rel.relation, "object": rel.object}

    def _params_for(self, contract: SceneContract, object_id: str) -> Dict[str, str]:
        params: Dict[str, str] = {}
        for relation in contract.relations:
            if relation.subject != object_id:
                continue
            if relation.relation == "on":
                params["on"] = relation.object
            elif relation.relation in RELATION_PARAM:
                params[RELATION_PARAM[relation.relation]] = relation.object
        obj = contract.get_object(object_id)
        if obj and obj.type in TABLETOP_TYPES and "on" not in params:
            support = _inferred_support(contract, object_id)
            if support:
                params["on"] = support
        return params


def _ordered_object_ids(contract: SceneContract) -> List[str]:
    remaining = set(contract.object_ids())
    ordered: List[str] = []
    while remaining:
        progressed = False
        for object_id in list(remaining):
            dependencies = {rel.object for rel in contract.relations if rel.subject == object_id}
            if dependencies.issubset(set(ordered)):
                ordered.append(object_id)
                remaining.remove(object_id)
                progressed = True
        if not progressed:
            ordered.extend(sorted(remaining))
            break
    return ordered


def _inferred_support(contract: SceneContract, object_id: str) -> Optional[str]:
    for relation in contract.relations:
        if relation.subject == object_id and relation.relation == "on":
            return relation.object
    for relation in contract.relations:
        if relation.subject == object_id:
            return _inferred_support(contract, relation.object)
    return None
