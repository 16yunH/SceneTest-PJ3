"""Execute generated scene code and evaluate graphics unit tests."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

from .scene_builder import SceneBuilder


@dataclass
class TestResult:
    name: str
    status: str
    reason: str = ""
    repair_hint: Optional[Dict[str, object]] = None

    @property
    def passed(self) -> bool:
        return self.status == "pass"

    def to_dict(self) -> Dict[str, object]:
        data: Dict[str, object] = {"name": self.name, "status": self.status}
        if self.reason:
            data["reason"] = self.reason
        if self.repair_hint:
            data["repair_hint"] = self.repair_hint
        return data


def execute_scene_code(code: str) -> Tuple[Optional[SceneBuilder], Optional[str]]:
    namespace: Dict[str, object] = {"SceneBuilder": SceneBuilder}
    try:
        exec(compile(code, "<generated_scene>", "exec"), namespace)
    except Exception as exc:  # pragma: no cover - included in execution metric
        return None, f"{type(exc).__name__}: {exc}"
    scene = namespace.get("scene")
    if not isinstance(scene, SceneBuilder):
        return None, "generated code did not define a SceneBuilder named `scene`"
    return scene, None


def run_tests(scene: Optional[SceneBuilder], tests: Iterable[Dict[str, object]], execution_error: Optional[str] = None) -> List[TestResult]:
    results: List[TestResult] = []
    if execution_error:
        results.append(
            TestResult(
                name="execution",
                status="fail",
                reason=execution_error,
                repair_hint={"action": "regenerate_scene_code"},
            )
        )
        return results
    if scene is None:
        results.append(
            TestResult(
                name="execution",
                status="fail",
                reason="scene is None",
                repair_hint={"action": "regenerate_scene_code"},
            )
        )
        return results
    results.append(TestResult(name="execution", status="pass"))
    for test in tests:
        results.append(_run_one(scene, test))
    return results


def _run_one(scene: SceneBuilder, test: Dict[str, object]) -> TestResult:
    test_type = str(test["type"])
    if test_type == "exists":
        object_id = str(test["object"])
        if object_id in scene.objects:
            return TestResult(f"exists:{object_id}", "pass")
        return TestResult(
            f"exists:{object_id}",
            "fail",
            reason=f"{object_id} is missing from scene registry",
            repair_hint={"action": "create_object", "object": object_id},
        )
    if test_type == "material":
        object_id = str(test["object"])
        expected = str(test["material"])
        obj = scene.objects.get(object_id)
        if obj and obj.material and expected.lower() in obj.material.lower():
            return TestResult(f"material:{object_id}:{expected}", "pass")
        actual = obj.material if obj else None
        return TestResult(
            f"material:{object_id}:{expected}",
            "fail",
            reason=f"expected material containing {expected!r}, got {actual!r}",
            repair_hint={"action": "set_material", "object": object_id, "material": expected},
        )
    if test_type == "color":
        object_id = str(test["object"])
        expected = str(test["color"])
        obj = scene.objects.get(object_id)
        if obj and obj.color == expected:
            return TestResult(f"color:{object_id}:{expected}", "pass")
        actual = obj.color if obj else None
        return TestResult(
            f"color:{object_id}:{expected}",
            "fail",
            reason=f"expected color {expected!r}, got {actual!r}",
            repair_hint={"action": "set_color", "object": object_id, "color": expected},
        )
    if test_type == "relation":
        return _run_relation(scene, test)
    if test_type == "lighting":
        expected = str(test["style"])
        if expected.lower() in scene.lighting_style.lower():
            return TestResult(f"lighting:{expected}", "pass")
        return TestResult(
            f"lighting:{expected}",
            "fail",
            reason=f"expected {expected!r} lighting, got {scene.lighting_style!r}",
            repair_hint={"action": "set_lighting", "style": expected},
        )
    if test_type == "visible":
        object_id = str(test["object"])
        if scene.is_visible(object_id):
            return TestResult(f"visible:{object_id}", "pass")
        return TestResult(
            f"visible:{object_id}",
            "fail",
            reason=f"{object_id} has insufficient projected area in camera frame",
            repair_hint={"action": "auto_frame_camera", "object": object_id},
        )
    return TestResult(f"unknown:{test_type}", "fail", reason=f"unknown test type {test_type!r}")


def _run_relation(scene: SceneBuilder, test: Dict[str, object]) -> TestResult:
    subject_id = str(test["subject"])
    target_id = str(test["object"])
    relation = str(test["relation"])
    margin = float(test.get("margin", 0.2))
    name = f"relation:{subject_id}:{relation}:{target_id}"
    subject = scene.objects.get(subject_id)
    target = scene.objects.get(target_id)
    if not subject or not target:
        missing = subject_id if not subject else target_id
        return TestResult(
            name,
            "fail",
            reason=f"{missing} is missing",
            repair_hint={"action": "create_object", "object": missing},
        )
    sb = subject.bbox
    tb = target.bbox
    if relation == "left_of":
        ok = sb.center_x < tb.center_x - margin
        reason = f"{subject_id}.center_x={sb.center_x:.2f} should be < {target_id}.center_x-margin={tb.center_x - margin:.2f}"
    elif relation == "right_of":
        ok = sb.center_x > tb.center_x + margin
        reason = f"{subject_id}.center_x={sb.center_x:.2f} should be > {target_id}.center_x+margin={tb.center_x + margin:.2f}"
    elif relation == "behind":
        ok = sb.center_y > tb.center_y + margin
        reason = f"{subject_id}.center_y={sb.center_y:.2f} should be > {target_id}.center_y+margin={tb.center_y + margin:.2f}"
    elif relation == "in_front_of":
        ok = sb.center_y < tb.center_y - margin
        reason = f"{subject_id}.center_y={sb.center_y:.2f} should be < {target_id}.center_y-margin={tb.center_y - margin:.2f}"
    elif relation == "on":
        vertical_ok = abs(sb.min_z - tb.max_z) <= 0.08
        horizontal_ok = sb.xy_overlap_fraction(tb) >= 0.2
        ok = vertical_ok and horizontal_ok
        reason = (
            f"vertical={abs(sb.min_z - tb.max_z):.2f}, "
            f"xy_overlap={sb.xy_overlap_fraction(tb):.2f}; expected on-support relation"
        )
    elif relation == "near":
        dx = abs(sb.center_x - tb.center_x)
        dy = abs(sb.center_y - tb.center_y)
        ok = max(dx, dy) <= max(1.2, margin * 3.0)
        reason = f"distance proxy max(dx,dy)={max(dx, dy):.2f} is too large"
    else:
        return TestResult(name, "fail", reason=f"unsupported relation {relation!r}")
    if ok:
        return TestResult(name, "pass")
    return TestResult(
        name,
        "fail",
        reason=reason,
        repair_hint={
            "action": "move_relation",
            "subject": subject_id,
            "relation": relation,
            "object": target_id,
            "margin": max(0.35, margin),
        },
    )


def summarize_results(results: Iterable[TestResult]) -> Dict[str, object]:
    results = list(results)
    total = len(results)
    passed = sum(1 for result in results if result.passed)
    by_prefix: Dict[str, List[TestResult]] = {}
    for result in results:
        prefix = result.name.split(":", 1)[0]
        by_prefix.setdefault(prefix, []).append(result)
    return {
        "passed": passed,
        "total": total,
        "pass_rate": passed / total if total else 0.0,
        "by_type": {
            prefix: {
                "passed": sum(1 for item in items if item.passed),
                "total": len(items),
                "pass_rate": sum(1 for item in items if item.passed) / len(items),
            }
            for prefix, items in sorted(by_prefix.items())
        },
    }
