"""A testable scene-builder API.

The project can execute generated scene code without Blender by using this
in-memory builder. The same serialized scene can be exported to Blender Python
for visual rendering on machines that have Blender installed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Tuple

from .geometry import BBox, Vec3


@dataclass
class SceneObject:
    id: str
    type: str
    location: Vec3
    size: Vec3
    material: Optional[str] = None
    color: Optional[str] = None
    shape: str = "box"
    support_id: Optional[str] = None

    @property
    def bbox(self) -> BBox:
        return BBox.from_center_size(self.location, self.size)

    def to_dict(self) -> Dict[str, object]:
        return {
            "id": self.id,
            "type": self.type,
            "location": list(self.location),
            "size": list(self.size),
            "material": self.material,
            "color": self.color,
            "shape": self.shape,
            "support_id": self.support_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, object]) -> "SceneObject":
        return cls(
            id=str(data["id"]),
            type=str(data["type"]),
            location=tuple(float(x) for x in data["location"]),  # type: ignore[arg-type]
            size=tuple(float(x) for x in data["size"]),  # type: ignore[arg-type]
            material=data.get("material"),  # type: ignore[arg-type]
            color=data.get("color"),  # type: ignore[arg-type]
            shape=str(data.get("shape", "box")),
            support_id=data.get("support_id"),  # type: ignore[arg-type]
        )


@dataclass
class CameraState:
    view: str = "front_perspective"
    target_objects: List[str] = field(default_factory=list)
    x_min: float = -2.0
    x_max: float = 2.0
    y_min: float = -1.5
    y_max: float = 1.5

    @property
    def bounds(self) -> BBox:
        return BBox(self.x_min, self.x_max, self.y_min, self.y_max, -100.0, 100.0)

    def to_dict(self) -> Dict[str, object]:
        return {
            "view": self.view,
            "target_objects": list(self.target_objects),
            "x_min": self.x_min,
            "x_max": self.x_max,
            "y_min": self.y_min,
            "y_max": self.y_max,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, object]) -> "CameraState":
        return cls(
            view=str(data.get("view", "front_perspective")),
            target_objects=list(data.get("target_objects", [])),  # type: ignore[arg-type]
            x_min=float(data.get("x_min", -2.0)),
            x_max=float(data.get("x_max", 2.0)),
            y_min=float(data.get("y_min", -1.5)),
            y_max=float(data.get("y_max", 1.5)),
        )


CATALOG: Dict[str, Dict[str, object]] = {
    "generic": {"size": (0.65, 0.65, 0.65), "shape": "box", "material": "matte"},
    "table": {"size": (4.0, 2.0, 0.22), "shape": "box", "material": "wood"},
    "desk": {"size": (4.2, 2.0, 0.22), "shape": "box", "material": "wood"},
    "low_table": {"size": (2.6, 1.4, 0.18), "shape": "box", "material": "wood"},
    "laptop": {"size": (1.25, 0.78, 0.12), "shape": "box", "material": "dark plastic"},
    "lamp": {"size": (0.42, 0.42, 1.1), "shape": "cylinder", "material": "metal"},
    "cup": {"size": (0.36, 0.36, 0.48), "shape": "cylinder", "material": "ceramic"},
    "book": {"size": (0.9, 0.55, 0.12), "shape": "box", "material": "paper"},
    "plant": {"size": (0.55, 0.55, 0.72), "shape": "cylinder", "material": "leafy"},
    "chair": {"size": (0.85, 0.85, 1.0), "shape": "box", "material": "fabric"},
    "bench": {"size": (2.0, 0.75, 0.55), "shape": "box", "material": "wood"},
    "sofa": {"size": (2.7, 1.0, 0.9), "shape": "box", "material": "fabric"},
    "bed": {"size": (2.8, 2.1, 0.65), "shape": "box", "material": "fabric"},
    "shelf": {"size": (1.2, 0.45, 2.0), "shape": "box", "material": "wood"},
    "cube": {"size": (0.75, 0.75, 0.75), "shape": "box", "material": "matte"},
    "sphere": {"size": (0.75, 0.75, 0.75), "shape": "sphere", "material": "matte"},
    "cylinder": {"size": (0.75, 0.75, 0.9), "shape": "cylinder", "material": "matte"},
    "cone": {"size": (0.75, 0.75, 0.9), "shape": "cone", "material": "matte"},
    "monitor": {"size": (1.2, 0.18, 0.8), "shape": "box", "material": "dark plastic"},
    "keyboard": {"size": (1.0, 0.32, 0.08), "shape": "box", "material": "plastic"},
    "mouse": {"size": (0.32, 0.22, 0.12), "shape": "box", "material": "plastic"},
    "phone": {"size": (0.38, 0.68, 0.06), "shape": "box", "material": "dark plastic"},
    "vase": {"size": (0.42, 0.42, 0.9), "shape": "cylinder", "material": "ceramic"},
    "bottle": {"size": (0.32, 0.32, 0.8), "shape": "cylinder", "material": "glass"},
    "bowl": {"size": (0.65, 0.65, 0.28), "shape": "cylinder", "material": "ceramic"},
    "plate": {"size": (0.72, 0.72, 0.08), "shape": "cylinder", "material": "ceramic"},
    "clock": {"size": (0.5, 0.16, 0.5), "shape": "cylinder", "material": "metal"},
    "magnifying_glass": {"size": (0.60, 0.34, 0.10), "shape": "cylinder", "material": "metal"},
    "globe": {"size": (0.58, 0.58, 0.78), "shape": "sphere", "material": "plastic"},
    "speaker": {"size": (0.45, 0.35, 0.7), "shape": "box", "material": "plastic"},
    "camera": {"size": (0.55, 0.35, 0.35), "shape": "box", "material": "plastic"},
    "microphone": {"size": (0.28, 0.28, 0.75), "shape": "cylinder", "material": "metal"},
    "telescope": {"size": (0.95, 0.35, 0.35), "shape": "cylinder", "material": "metal"},
    "robot_arm": {"size": (0.55, 0.55, 1.2), "shape": "cylinder", "material": "metal"},
    "printer": {"size": (1.1, 0.75, 0.5), "shape": "box", "material": "plastic"},
    "easel": {"size": (0.85, 0.35, 1.6), "shape": "box", "material": "wood"},
    "canvas": {"size": (1.0, 0.12, 0.78), "shape": "box", "material": "paper"},
    "mirror": {"size": (0.9, 0.12, 1.25), "shape": "box", "material": "glass"},
    "piano": {"size": (2.2, 0.85, 0.95), "shape": "box", "material": "wood"},
    "rug": {"size": (2.2, 1.35, 0.04), "shape": "box", "material": "fabric"},
    "map": {"size": (0.95, 0.65, 0.05), "shape": "box", "material": "paper"},
    "passport": {"size": (0.42, 0.30, 0.05), "shape": "box", "material": "paper"},
    "ticket": {"size": (0.55, 0.22, 0.04), "shape": "box", "material": "paper"},
    "clipboard": {"size": (0.78, 0.52, 0.06), "shape": "box", "material": "paper"},
    "menu_card": {"size": (0.62, 0.42, 0.05), "shape": "box", "material": "paper"},
    "plaque": {"size": (0.58, 0.32, 0.06), "shape": "box", "material": "bronze"},
    "clay_tablet": {"size": (0.62, 0.42, 0.09), "shape": "box", "material": "clay"},
    "chess_board": {"size": (0.86, 0.86, 0.08), "shape": "box", "material": "wood"},
    "cutting_board": {"size": (0.85, 0.50, 0.07), "shape": "box", "material": "wood"},
    "compass": {"size": (0.42, 0.42, 0.10), "shape": "cylinder", "material": "metal"},
    "sensor_module": {"size": (0.50, 0.36, 0.20), "shape": "box", "material": "plastic"},
    "battery_pack": {"size": (0.62, 0.38, 0.30), "shape": "box", "material": "plastic"},
    "toolbox": {"size": (0.95, 0.45, 0.42), "shape": "box", "material": "metal"},
    "violin": {"size": (0.95, 0.34, 0.22), "shape": "box", "material": "wood"},
    "paint_palette": {"size": (0.55, 0.42, 0.06), "shape": "cylinder", "material": "wood"},
    "clay_sculpture": {"size": (0.46, 0.46, 0.72), "shape": "sphere", "material": "clay"},
    "statue": {"size": (0.52, 0.52, 0.90), "shape": "sphere", "material": "stone"},
    "tripod": {"size": (0.70, 0.70, 1.05), "shape": "cylinder", "material": "metal"},
    "light_stand": {"size": (0.70, 0.70, 1.20), "shape": "cylinder", "material": "metal"},
    "reflector": {"size": (0.72, 0.18, 0.72), "shape": "cylinder", "material": "metal"},
    "microscope": {"size": (0.62, 0.46, 0.86), "shape": "cylinder", "material": "metal"},
    "beaker": {"size": (0.36, 0.36, 0.55), "shape": "cylinder", "material": "glass"},
    "test_tube_rack": {"size": (0.75, 0.32, 0.42), "shape": "box", "material": "wood"},
    "wrench": {"size": (0.72, 0.18, 0.10), "shape": "box", "material": "metal"},
    "drill": {"size": (0.70, 0.38, 0.44), "shape": "box", "material": "plastic"},
    "helmet": {"size": (0.62, 0.48, 0.38), "shape": "sphere", "material": "plastic"},
    "spray_bottle": {"size": (0.36, 0.30, 0.72), "shape": "cylinder", "material": "plastic"},
    "seed_tray": {"size": (0.85, 0.48, 0.14), "shape": "box", "material": "plastic"},
    "watering_can": {"size": (0.75, 0.45, 0.48), "shape": "sphere", "material": "metal"},
    "fabric_roll": {"size": (0.78, 0.32, 0.32), "shape": "cylinder", "material": "fabric"},
    "needle_box": {"size": (0.42, 0.30, 0.18), "shape": "box", "material": "plastic"},
    "scissors": {"size": (0.62, 0.30, 0.08), "shape": "box", "material": "metal"},
    "sandwich": {"size": (0.58, 0.42, 0.20), "shape": "box", "material": "paper"},
    "basket": {"size": (0.72, 0.52, 0.42), "shape": "box", "material": "wood"},
    "king": {"size": (0.24, 0.24, 0.55), "shape": "cone", "material": "ceramic"},
    "queen": {"size": (0.24, 0.24, 0.50), "shape": "cone", "material": "ceramic"},
    "cardboard_box": {"size": (0.68, 0.52, 0.42), "shape": "box", "material": "cardboard"},
    "barcode_scanner": {"size": (0.55, 0.26, 0.22), "shape": "box", "material": "plastic"},
    "tape_roll": {"size": (0.38, 0.38, 0.16), "shape": "cylinder", "material": "plastic"},
    "label_printer": {"size": (0.70, 0.48, 0.32), "shape": "box", "material": "plastic"},
    "toy_car": {"size": (0.70, 0.34, 0.28), "shape": "box", "material": "plastic"},
    "robot_toy": {"size": (0.42, 0.34, 0.70), "shape": "box", "material": "metal"},
    "block_tower": {"size": (0.55, 0.55, 0.95), "shape": "box", "material": "plastic"},
    "teapot": {"size": (0.62, 0.46, 0.42), "shape": "sphere", "material": "ceramic"},
    "bamboo_tray": {"size": (0.82, 0.48, 0.10), "shape": "box", "material": "wood"},
    "suitcase": {"size": (0.82, 0.45, 0.58), "shape": "box", "material": "leather"},
    "drone": {"size": (0.78, 0.78, 0.20), "shape": "box", "material": "plastic"},
    "screwdriver": {"size": (0.70, 0.14, 0.12), "shape": "cylinder", "material": "metal"},
    "fish_statue": {"size": (0.55, 0.35, 0.34), "shape": "sphere", "material": "stone"},
    "coral_model": {"size": (0.46, 0.42, 0.58), "shape": "cylinder", "material": "ceramic"},
    "cake": {"size": (0.62, 0.62, 0.36), "shape": "cylinder", "material": "ceramic"},
    "rolling_pin": {"size": (0.78, 0.18, 0.18), "shape": "cylinder", "material": "wood"},
    "stone_artifact": {"size": (0.46, 0.36, 0.32), "shape": "sphere", "material": "stone"},
    "radio": {"size": (0.62, 0.32, 0.42), "shape": "box", "material": "plastic"},
    "soap_dispenser": {"size": (0.32, 0.26, 0.62), "shape": "cylinder", "material": "ceramic"},
    "brush": {"size": (0.62, 0.16, 0.10), "shape": "cylinder", "material": "wood"},
    "jewelry_box": {"size": (0.42, 0.32, 0.24), "shape": "box", "material": "wood"},
    "shoe_rack": {"size": (1.05, 0.38, 0.70), "shape": "box", "material": "wood"},
    "umbrella_stand": {"size": (0.45, 0.45, 0.95), "shape": "cylinder", "material": "metal"},
    "backpack": {"size": (0.55, 0.32, 0.62), "shape": "box", "material": "fabric"},
    "key_bowl": {"size": (0.42, 0.42, 0.18), "shape": "cylinder", "material": "ceramic"},
    "stethoscope": {"size": (0.62, 0.46, 0.16), "shape": "cylinder", "material": "rubber"},
    "pill_bottle": {"size": (0.28, 0.28, 0.50), "shape": "cylinder", "material": "plastic"},
    "towel": {"size": (0.86, 0.42, 0.05), "shape": "box", "material": "fabric"},
}

TABLETOP_TYPES = {
    "generic",
    "laptop",
    "lamp",
    "cup",
    "book",
    "plant",
    "cube",
    "sphere",
    "cylinder",
    "cone",
    "monitor",
    "keyboard",
    "mouse",
    "phone",
    "vase",
    "bottle",
    "bowl",
    "plate",
    "clock",
    "magnifying_glass",
    "globe",
    "speaker",
    "camera",
    "microphone",
    "telescope",
    "robot_arm",
    "printer",
    "toolbox",
    "canvas",
    "mirror",
    "map",
    "passport",
    "ticket",
    "clipboard",
    "menu_card",
    "plaque",
    "clay_tablet",
    "chess_board",
    "cutting_board",
    "compass",
    "sensor_module",
    "battery_pack",
    "violin",
    "paint_palette",
    "clay_sculpture",
    "statue",
    "tripod",
    "light_stand",
    "reflector",
    "microscope",
    "beaker",
    "test_tube_rack",
    "wrench",
    "drill",
    "helmet",
    "spray_bottle",
    "seed_tray",
    "watering_can",
    "fabric_roll",
    "needle_box",
    "scissors",
    "sandwich",
    "basket",
    "king",
    "queen",
    "cardboard_box",
    "barcode_scanner",
    "tape_roll",
    "label_printer",
    "toy_car",
    "robot_toy",
    "block_tower",
    "teapot",
    "bamboo_tray",
    "suitcase",
    "drone",
    "screwdriver",
    "fish_statue",
    "coral_model",
    "cake",
    "rolling_pin",
    "stone_artifact",
    "radio",
    "soap_dispenser",
    "brush",
    "jewelry_box",
    "key_bowl",
    "stethoscope",
    "pill_bottle",
    "towel",
}


class SceneBuilder:
    def __init__(self) -> None:
        self.objects: Dict[str, SceneObject] = {}
        self.lighting_style = "neutral"
        self.camera = CameraState()
        self.repair_log: List[Dict[str, object]] = []

    def add_object(
        self,
        object_id: str,
        object_type: str,
        *,
        location: Optional[Vec3] = None,
        size: Optional[Vec3] = None,
        material: Optional[str] = None,
        color: Optional[str] = None,
        shape: Optional[str] = None,
        on: Optional[str] = None,
        left_of: Optional[str] = None,
        right_of: Optional[str] = None,
        behind: Optional[str] = None,
        in_front_of: Optional[str] = None,
        near: Optional[str] = None,
        distance: float = 0.35,
    ) -> SceneObject:
        spec = CATALOG.get(object_type, CATALOG["cube"])
        obj_size = tuple(float(x) for x in (size or spec["size"]))  # type: ignore[arg-type]
        obj_shape = shape or str(spec.get("shape", "box"))
        obj_material = material or str(spec.get("material", "matte"))
        obj_location, support_id = self._resolve_location(
            object_type,
            obj_size,
            location,
            on=on,
            left_of=left_of,
            right_of=right_of,
            behind=behind,
            in_front_of=in_front_of,
            near=near,
            distance=distance,
        )
        obj = SceneObject(
            id=object_id,
            type=object_type,
            location=obj_location,
            size=obj_size,
            material=obj_material,
            color=color,
            shape=obj_shape,
            support_id=support_id,
        )
        self.objects[object_id] = obj
        return obj

    def add_generic(self, object_id: str, **kwargs: object) -> SceneObject:
        return self.add_object(object_id, "generic", **kwargs)

    def add_table(self, object_id: str, **kwargs: object) -> SceneObject:
        return self.add_object(object_id, "table", **kwargs)

    def add_desk(self, object_id: str, **kwargs: object) -> SceneObject:
        return self.add_object(object_id, "desk", **kwargs)

    def add_low_table(self, object_id: str, **kwargs: object) -> SceneObject:
        return self.add_object(object_id, "low_table", **kwargs)

    def add_laptop(self, object_id: str, **kwargs: object) -> SceneObject:
        return self.add_object(object_id, "laptop", **kwargs)

    def add_lamp(self, object_id: str, **kwargs: object) -> SceneObject:
        return self.add_object(object_id, "lamp", **kwargs)

    def add_cup(self, object_id: str, **kwargs: object) -> SceneObject:
        return self.add_object(object_id, "cup", **kwargs)

    def add_book(self, object_id: str, **kwargs: object) -> SceneObject:
        return self.add_object(object_id, "book", **kwargs)

    def add_plant(self, object_id: str, **kwargs: object) -> SceneObject:
        return self.add_object(object_id, "plant", **kwargs)

    def add_chair(self, object_id: str, **kwargs: object) -> SceneObject:
        return self.add_object(object_id, "chair", **kwargs)

    def add_bench(self, object_id: str, **kwargs: object) -> SceneObject:
        return self.add_object(object_id, "bench", **kwargs)

    def add_sofa(self, object_id: str, **kwargs: object) -> SceneObject:
        return self.add_object(object_id, "sofa", **kwargs)

    def add_bed(self, object_id: str, **kwargs: object) -> SceneObject:
        return self.add_object(object_id, "bed", **kwargs)

    def add_shelf(self, object_id: str, **kwargs: object) -> SceneObject:
        return self.add_object(object_id, "shelf", **kwargs)

    def add_cube(self, object_id: str, **kwargs: object) -> SceneObject:
        return self.add_object(object_id, "cube", **kwargs)

    def add_sphere(self, object_id: str, **kwargs: object) -> SceneObject:
        return self.add_object(object_id, "sphere", **kwargs)

    def add_cylinder(self, object_id: str, **kwargs: object) -> SceneObject:
        return self.add_object(object_id, "cylinder", **kwargs)

    def add_cone(self, object_id: str, **kwargs: object) -> SceneObject:
        return self.add_object(object_id, "cone", **kwargs)

    def set_material(self, object_id: str, material: Optional[str] = None, color: Optional[str] = None) -> None:
        obj = self.objects[object_id]
        if material:
            obj.material = material
        if color:
            obj.color = color

    def set_lighting(self, style: str = "neutral") -> None:
        self.lighting_style = style or "neutral"

    def set_camera(
        self,
        view: str = "front_perspective",
        target_objects: Optional[Iterable[str]] = None,
        frame: str = "auto",
        bounds: Optional[Tuple[float, float, float, float]] = None,
    ) -> None:
        targets = list(target_objects or self.objects.keys())
        self.camera.view = view
        self.camera.target_objects = targets
        if bounds:
            self.camera.x_min, self.camera.x_max, self.camera.y_min, self.camera.y_max = bounds
            return
        if frame == "default":
            self.camera.x_min, self.camera.x_max = -1.7, 1.7
            self.camera.y_min, self.camera.y_max = -1.25, 1.25
            return
        boxes = [self.objects[obj_id].bbox for obj_id in targets if obj_id in self.objects]
        union = BBox.union(boxes)
        pad_x = max(0.45, union.width * 0.18)
        pad_y = max(0.45, union.depth * 0.18)
        self.camera.x_min = union.min_x - pad_x
        self.camera.x_max = union.max_x + pad_x
        self.camera.y_min = union.min_y - pad_y
        self.camera.y_max = union.max_y + pad_y

    def place_relation(self, subject_id: str, relation: str, target_id: str, margin: float = 0.35) -> None:
        subject = self.objects[subject_id]
        target = self.objects[target_id]
        x, y, z = subject.location
        sb = subject.bbox
        tb = target.bbox
        if relation == "left_of":
            x = tb.center_x - tb.width / 2.0 - sb.width / 2.0 - margin
        elif relation == "right_of":
            x = tb.center_x + tb.width / 2.0 + sb.width / 2.0 + margin
        elif relation == "behind":
            y = tb.center_y + tb.depth / 2.0 + sb.depth / 2.0 + margin
        elif relation == "in_front_of":
            y = tb.center_y - tb.depth / 2.0 - sb.depth / 2.0 - margin
        elif relation == "near":
            x = tb.center_x + tb.width / 2.0 + sb.width / 2.0 + max(0.05, margin / 2.0)
            y = tb.center_y
        elif relation == "on":
            x = tb.center_x
            y = tb.center_y
            z = tb.max_z + sb.height / 2.0
            subject.support_id = target_id
        if relation != "on" and subject.support_id in self.objects:
            x, y = _clamp_center_to_support_overlap(x, y, subject.size, self.objects[subject.support_id].bbox)
        subject.location = (x, y, z)

    def is_visible(self, object_id: str, min_overlap: float = 0.08) -> bool:
        if object_id not in self.objects:
            return False
        obj_box = self.objects[object_id].bbox
        cam_box = self.camera.bounds
        overlap = obj_box.xy_overlap_area(cam_box)
        if obj_box.area_xy <= 0:
            return False
        return overlap / obj_box.area_xy >= min_overlap

    def scene_bbox(self) -> BBox:
        return BBox.union(obj.bbox for obj in self.objects.values())

    def to_dict(self) -> Dict[str, object]:
        return {
            "objects": [obj.to_dict() for obj in self.objects.values()],
            "lighting_style": self.lighting_style,
            "camera": self.camera.to_dict(),
            "repair_log": list(self.repair_log),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, object]) -> "SceneBuilder":
        scene = cls()
        for obj_data in data.get("objects", []):  # type: ignore[union-attr]
            obj = SceneObject.from_dict(obj_data)  # type: ignore[arg-type]
            scene.objects[obj.id] = obj
        scene.lighting_style = str(data.get("lighting_style", "neutral"))
        scene.camera = CameraState.from_dict(data.get("camera", {}))  # type: ignore[arg-type]
        scene.repair_log = list(data.get("repair_log", []))  # type: ignore[arg-type]
        return scene

    def to_python(self) -> str:
        lines = [
            "from scenetest.core.scene_builder import SceneBuilder",
            "",
            "scene = SceneBuilder()",
        ]
        for obj in self.objects.values():
            lines.append(
                "scene.add_object("
                f"{obj.id!r}, {obj.type!r}, "
                f"location={_fmt_tuple(obj.location)}, "
                f"size={_fmt_tuple(obj.size)}, "
                f"material={obj.material!r}, "
                f"color={obj.color!r}, "
                f"shape={obj.shape!r})"
            )
        lines.append(f"scene.set_lighting(style={self.lighting_style!r})")
        bounds = (
            self.camera.x_min,
            self.camera.x_max,
            self.camera.y_min,
            self.camera.y_max,
        )
        lines.append(
            "scene.set_camera("
            f"view={self.camera.view!r}, "
            f"target_objects={self.camera.target_objects!r}, "
            f"bounds={_fmt_tuple(bounds)})"
        )
        return "\n".join(lines) + "\n"

    def _resolve_location(
        self,
        object_type: str,
        size: Vec3,
        location: Optional[Vec3],
        *,
        on: Optional[str],
        left_of: Optional[str],
        right_of: Optional[str],
        behind: Optional[str],
        in_front_of: Optional[str],
        near: Optional[str],
        distance: float,
    ) -> Tuple[Vec3, Optional[str]]:
        x, y, z = location if location is not None else (0.0, 0.0, size[2] / 2.0)
        support_id = None
        if on and on in self.objects:
            target_box = self.objects[on].bbox
            x = target_box.center_x
            y = target_box.center_y
            z = target_box.max_z + size[2] / 2.0
            support_id = on
        for relation, target_id in (
            ("left_of", left_of),
            ("right_of", right_of),
            ("behind", behind),
            ("in_front_of", in_front_of),
            ("near", near),
        ):
            if not target_id or target_id not in self.objects:
                continue
            target = self.objects[target_id]
            tb = target.bbox
            sb = BBox.from_center_size((x, y, z), size)
            if support_id is None and object_type in TABLETOP_TYPES and target.support_id in self.objects:
                support = self.objects[target.support_id]
                z = support.bbox.max_z + size[2] / 2.0
                support_id = support.id
            if relation == "left_of":
                x = tb.center_x - tb.width / 2.0 - sb.width / 2.0 - distance
                y = tb.center_y
            elif relation == "right_of":
                x = tb.center_x + tb.width / 2.0 + sb.width / 2.0 + distance
                y = tb.center_y
            elif relation == "behind":
                x = tb.center_x
                y = tb.center_y + tb.depth / 2.0 + sb.depth / 2.0 + distance
            elif relation == "in_front_of":
                x = tb.center_x
                y = tb.center_y - tb.depth / 2.0 - sb.depth / 2.0 - distance
            elif relation == "near":
                x = tb.center_x + tb.width / 2.0 + sb.width / 2.0 + max(0.05, distance / 2.0)
                y = tb.center_y
        if support_id in self.objects:
            x, y = _clamp_center_to_support_overlap(x, y, size, self.objects[support_id].bbox)
        return (float(x), float(y), float(z)), support_id


def _fmt_tuple(values: Iterable[float]) -> str:
    return "(" + ", ".join(f"{float(x):.4f}" for x in values) + ")"


def _clamp_center_to_support_overlap(x: float, y: float, size: Vec3, support: BBox) -> Tuple[float, float]:
    width, depth, _height = size
    min_axis_overlap = 0.25
    x = _clamp_axis_to_support_overlap(x, width, support.min_x, support.max_x, min_axis_overlap)
    y = _clamp_axis_to_support_overlap(y, depth, support.min_y, support.max_y, min_axis_overlap)
    return x, y


def _clamp_axis_to_support_overlap(center: float, extent: float, support_min: float, support_max: float, fraction: float) -> float:
    if extent <= 0:
        return center
    required_overlap = min(extent, max(0.0, support_max - support_min)) * fraction
    lower = support_min + required_overlap - extent / 2.0
    upper = support_max - required_overlap + extent / 2.0
    if lower > upper:
        return (support_min + support_max) / 2.0
    return min(max(center, lower), upper)
