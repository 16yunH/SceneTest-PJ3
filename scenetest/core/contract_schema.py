"""Data model for scene contracts.

The schema is intentionally small and JSON-friendly so it can be shared by
contract parsing, scene generation, graphics unit tests, and repair rules.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional


@dataclass
class ContractObject:
    id: str
    type: str
    required: bool = True
    material: Optional[str] = None
    color: Optional[str] = None
    attributes: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ContractObject":
        return cls(
            id=str(data["id"]),
            type=str(data.get("type", data["id"])),
            required=bool(data.get("required", True)),
            material=data.get("material"),
            color=data.get("color"),
            attributes=dict(data.get("attributes", {})),
        )

    def to_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "id": self.id,
            "type": self.type,
            "required": self.required,
        }
        if self.material:
            data["material"] = self.material
        if self.color:
            data["color"] = self.color
        if self.attributes:
            data["attributes"] = self.attributes
        return data


@dataclass
class Relation:
    subject: str
    relation: str
    object: str
    margin: float = 0.2

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Relation":
        return cls(
            subject=str(data["subject"]),
            relation=str(data["relation"]),
            object=str(data["object"]),
            margin=float(data.get("margin", 0.2)),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "subject": self.subject,
            "relation": self.relation,
            "object": self.object,
            "margin": self.margin,
        }


@dataclass
class CameraSpec:
    view: str = "front_perspective"
    visible_objects: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CameraSpec":
        return cls(
            view=str(data.get("view", "front_perspective")),
            visible_objects=list(data.get("visible_objects", [])),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {"view": self.view, "visible_objects": list(self.visible_objects)}


@dataclass
class SceneContract:
    id: str
    prompt: str
    objects: List[ContractObject]
    relations: List[Relation] = field(default_factory=list)
    style: Dict[str, Any] = field(default_factory=dict)
    camera: CameraSpec = field(default_factory=CameraSpec)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SceneContract":
        return cls(
            id=str(data.get("id", "scene")),
            prompt=str(data.get("prompt", "")),
            objects=[ContractObject.from_dict(x) for x in data.get("objects", [])],
            relations=[Relation.from_dict(x) for x in data.get("relations", [])],
            style=dict(data.get("style", {})),
            camera=CameraSpec.from_dict(data.get("camera", {})),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "prompt": self.prompt,
            "objects": [x.to_dict() for x in self.objects],
            "relations": [x.to_dict() for x in self.relations],
            "style": dict(self.style),
            "camera": self.camera.to_dict(),
        }

    def object_ids(self) -> List[str]:
        return [obj.id for obj in self.objects]

    def get_object(self, object_id: str) -> Optional[ContractObject]:
        for obj in self.objects:
            if obj.id == object_id:
                return obj
        return None

    def required_objects(self) -> Iterable[ContractObject]:
        return (obj for obj in self.objects if obj.required)
