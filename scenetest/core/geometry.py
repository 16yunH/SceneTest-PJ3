"""Small geometry helpers used by the local test backend."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Tuple


Vec3 = Tuple[float, float, float]


@dataclass(frozen=True)
class BBox:
    min_x: float
    max_x: float
    min_y: float
    max_y: float
    min_z: float
    max_z: float

    @property
    def center_x(self) -> float:
        return (self.min_x + self.max_x) / 2.0

    @property
    def center_y(self) -> float:
        return (self.min_y + self.max_y) / 2.0

    @property
    def center_z(self) -> float:
        return (self.min_z + self.max_z) / 2.0

    @property
    def width(self) -> float:
        return self.max_x - self.min_x

    @property
    def depth(self) -> float:
        return self.max_y - self.min_y

    @property
    def height(self) -> float:
        return self.max_z - self.min_z

    @property
    def area_xy(self) -> float:
        return max(0.0, self.width) * max(0.0, self.depth)

    @classmethod
    def from_center_size(cls, center: Vec3, size: Vec3) -> "BBox":
        x, y, z = center
        sx, sy, sz = size
        return cls(
            x - sx / 2.0,
            x + sx / 2.0,
            y - sy / 2.0,
            y + sy / 2.0,
            z - sz / 2.0,
            z + sz / 2.0,
        )

    @classmethod
    def union(cls, boxes: Iterable["BBox"]) -> "BBox":
        boxes = list(boxes)
        if not boxes:
            return cls(-1.0, 1.0, -1.0, 1.0, 0.0, 1.0)
        return cls(
            min(box.min_x for box in boxes),
            max(box.max_x for box in boxes),
            min(box.min_y for box in boxes),
            max(box.max_y for box in boxes),
            min(box.min_z for box in boxes),
            max(box.max_z for box in boxes),
        )

    def xy_overlap_area(self, other: "BBox") -> float:
        x_overlap = max(0.0, min(self.max_x, other.max_x) - max(self.min_x, other.min_x))
        y_overlap = max(0.0, min(self.max_y, other.max_y) - max(self.min_y, other.min_y))
        return x_overlap * y_overlap

    def xy_overlap_fraction(self, other: "BBox") -> float:
        denom = min(self.area_xy, other.area_xy)
        if denom <= 0:
            return 0.0
        return self.xy_overlap_area(other) / denom

    def intersects_xy(self, other: "BBox") -> bool:
        return self.xy_overlap_area(other) > 0.0
