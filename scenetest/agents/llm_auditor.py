"""DeepSeek-backed text auditor for generated scene artifacts.

This auditor does not inspect rendered images. It asks a language model to
review the prompt, contract, scene JSON, test results, and repair history so
the project has a semantic review layer beyond hard-coded unit tests.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from typing import Any, Dict, Iterable, Mapping


DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-v4-pro"

SCORE_FIELDS = (
    "overall_score",
    "prompt_alignment_score",
    "object_semantics_score",
    "relation_plausibility_score",
    "scale_plausibility_score",
    "construction_quality_score",
)


class DeepSeekSceneAuditor:
    def __init__(
        self,
        api_key: str | None = None,
        model: str = DEFAULT_MODEL,
        base_url: str = DEEPSEEK_BASE_URL,
        timeout: int = 120,
        temperature: float = 0.0,
        max_tokens: int = 4096,
    ) -> None:
        self.api_key = api_key or os.environ.get("DEEPSEEK_API_KEY")
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.temperature = temperature
        self.max_tokens = max_tokens

    @classmethod
    def from_config(cls, config: Mapping[str, Any]) -> "DeepSeekSceneAuditor":
        return cls(
            api_key=str(config.get("deepseek_api_key") or ""),
            model=str(config.get("llm_audit_model") or config.get("deepseek_model") or DEFAULT_MODEL),
            base_url=str(config.get("deepseek_base_url") or DEEPSEEK_BASE_URL),
            timeout=int(config.get("llm_audit_timeout", 120)),
            temperature=float(config.get("llm_audit_temperature", 0.0)),
            max_tokens=int(config.get("llm_audit_max_tokens", 4096)),
        )

    def audit_scene(
        self,
        *,
        scene_id: str,
        prompt: str,
        contract: Mapping[str, Any],
        scene: Mapping[str, Any],
        test_results: Iterable[Mapping[str, Any]],
        repair_history: Iterable[Mapping[str, Any]] | None = None,
    ) -> Dict[str, Any]:
        if not self.api_key:
            raise RuntimeError("DeepSeek API key is not set for LLM semantic audit")
        body = self._build_request_body(
            scene_id=scene_id,
            prompt=prompt,
            contract=contract,
            scene=scene,
            test_results=list(test_results),
            repair_history=list(repair_history or []),
        )
        data = self._post(body)
        try:
            payload = _extract_json(_message_content(data))
        except ValueError:
            retry_body = self._build_json_retry_body(body, _message_content(data))
            data = self._post(retry_body)
            payload = _extract_json(_message_content(data))
        audit = normalize_semantic_audit(payload, scene_id=scene_id)
        audit["model"] = self.model
        audit["auditor"] = "deepseek_text_semantic"
        return audit

    def _post(self, body: Mapping[str, Any]) -> Dict[str, Any]:
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"DeepSeek API returned HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"DeepSeek API request failed: {exc}") from exc
        if not isinstance(data, dict):
            raise RuntimeError("DeepSeek API response was not a JSON object")
        return data

    def _build_request_body(
        self,
        *,
        scene_id: str,
        prompt: str,
        contract: Mapping[str, Any],
        scene: Mapping[str, Any],
        test_results: Iterable[Mapping[str, Any]],
        repair_history: Iterable[Mapping[str, Any]],
    ) -> Dict[str, Any]:
        context = {
            "scene_id": scene_id,
            "prompt": prompt,
            "contract_json": contract,
            "final_scene_json": scene,
            "code_test_results": list(test_results),
            "repair_history": list(repair_history),
            "scene_stats": summarize_scene(scene),
            "evaluation_notes": [
                "SceneBuilder coordinates are abstract display units, not strict real-world meters.",
                "Judge scale mainly by relative object ratios, support fit, and obvious impossibilities.",
                "The Blender renderer may add composite primitive details from semantic object type even when scene_json shape is box.",
                "This is a course project prototype focused on testable scene structure, not high-fidelity asset modeling.",
                "If all executable tests pass and semantic object types, supports, and relations are plausible, score the scene as acceptable even when geometry is stylized or low-detail.",
            ],
        }
        return {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": "Audit this generated 3D scene from structured artifacts only:\n"
                    + json.dumps(context, ensure_ascii=False, indent=2),
                },
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "response_format": {"type": "json_object"},
        }

    def _build_json_retry_body(self, original_body: Mapping[str, Any], previous_text: str) -> Dict[str, Any]:
        original_messages = original_body.get("messages", [])
        original_context = ""
        if isinstance(original_messages, list) and len(original_messages) >= 2:
            message = original_messages[1]
            if isinstance(message, Mapping):
                original_context = str(message.get("content", ""))
        return {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "Return only a valid JSON object. Do not include reasoning or markdown."},
                {
                    "role": "user",
                    "content": "The previous response was not a valid audit JSON object. "
                    "Audit the original scene context below and return only the required JSON schema.\n\n"
                    f"Original context:\n{original_context[:12000]}\n\n"
                    f"Previous response tail:\n{previous_text[-3000:]}",
                },
            ],
            "temperature": 0.0,
            "max_tokens": max(self.max_tokens, 4096),
            "response_format": {"type": "json_object"},
        }


def summarize_scene(scene: Mapping[str, Any]) -> Dict[str, Any]:
    objects = [obj for obj in scene.get("objects", []) if isinstance(obj, Mapping)]  # type: ignore[union-attr]
    primitive_types = {"generic", "cube", "sphere", "cylinder", "cone"}
    primitive_like = [
        str(obj.get("id"))
        for obj in objects
        if str(obj.get("type", "")).lower() in primitive_types
        and str(obj.get("id", "")).lower() != str(obj.get("type", "")).lower()
    ]
    return {
        "object_count": len(objects),
        "object_ids": [str(obj.get("id")) for obj in objects],
        "object_types": {str(obj.get("id")): str(obj.get("type")) for obj in objects},
        "primitive_like_named_objects": primitive_like,
        "lighting_style": scene.get("lighting_style"),
        "camera": scene.get("camera"),
    }


def normalize_semantic_audit(payload: Mapping[str, Any], scene_id: str) -> Dict[str, Any]:
    scores: Dict[str, float] = {}
    for field in SCORE_FIELDS:
        scores[field] = _clamp_score(payload.get(field))
    if "overall_score" not in payload:
        detail_scores = [scores[field] for field in SCORE_FIELDS if field != "overall_score"]
        scores["overall_score"] = round(sum(detail_scores) / len(detail_scores), 3) if detail_scores else 0.0

    issues = [_normalize_issue(item) for item in _as_list(payload.get("issues"))]
    issues = [item for item in issues if item]
    major_issue_count = sum(1 for item in issues if item.get("severity") == "major")
    threshold_passed = scores["overall_score"] >= 0.70 and major_issue_count == 0
    passed = threshold_passed

    audit: Dict[str, Any] = {
        "scene_id": scene_id,
        "pass": passed,
        **scores,
        "summary": _short_text(payload.get("summary"), "No summary provided."),
        "strengths": [_short_text(item, "") for item in _as_list(payload.get("strengths")) if _short_text(item, "")],
        "issues": issues,
        "recommendations": [
            _short_text(item, "") for item in _as_list(payload.get("recommendations")) if _short_text(item, "")
        ],
        "confidence": _clamp_score(payload.get("confidence", 0.5)),
        "limitations": "Text-only audit: the model reviewed structured scene artifacts, not rendered images.",
    }
    return audit


def _normalize_issue(value: Any) -> Dict[str, Any]:
    if isinstance(value, str):
        return {"severity": "minor", "category": "semantic", "message": _short_text(value, "")}
    if not isinstance(value, Mapping):
        return {}
    severity = str(value.get("severity", "minor")).lower()
    if severity not in {"minor", "major"}:
        severity = "minor"
    category = _short_text(value.get("category"), "semantic")
    message = _short_text(value.get("message") or value.get("evidence"), "")
    evidence = _short_text(value.get("evidence"), "")
    detail_terms = (
        "detail",
        "fine",
        "generic",
        "proxy",
        "primitive",
        "cube",
        "sphere",
        "cylinder",
        "cone",
        "box",
        "geometry",
        "simple",
        "simplistic",
        "low-detail",
        "polish",
        "texture",
        "curved",
        "articulation",
    )
    if severity == "major":
        category_lower = category.lower()
        combined = f"{message} {evidence}".lower()
        blocking_terms = (
            "missing",
            "absent",
            "not present",
            "wrong semantic type",
            "wrong object",
            "wrong type",
            "floor",
            "support",
            "impossible",
            "contradictory",
            "relation",
        )
        detail_like_categories = {"construction", "object", "semantic"}
        if category_lower in detail_like_categories and not any(term in combined for term in blocking_terms):
            if any(term in combined for term in detail_terms):
                severity = "minor"
    out = {
        "severity": severity,
        "category": category,
        "message": message,
    }
    if value.get("object_id"):
        out["object_id"] = _short_text(value.get("object_id"), "")
    if value.get("evidence") and evidence != out["message"]:
        out["evidence"] = evidence
    return out if out["message"] else {}


def _message_content(data: Mapping[str, Any]) -> str:
    message = data["choices"][0]["message"]  # type: ignore[index]
    chunks = []
    for key in ("content", "reasoning_content"):
        content = message.get(key) if isinstance(message, Mapping) else None
        if isinstance(content, list):
            chunks.append("\n".join(str(item.get("text", "")) if isinstance(item, Mapping) else str(item) for item in content))
        elif content:
            chunks.append(str(content))
    return "\n".join(chunks)


def _extract_json(text: str) -> Dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text).strip()
        text = re.sub(r"```$", "", text).strip()
    decoder = json.JSONDecoder()
    candidates: list[Dict[str, Any]] = []
    for match in re.finditer(r"\{", text):
        try:
            data, _ = decoder.raw_decode(text[match.start() :])
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            candidates.append(data)
    for candidate in reversed(candidates):
        if any(field in candidate for field in SCORE_FIELDS) or "issues" in candidate:
            return candidate
    raise ValueError("LLM audit response did not contain a JSON object")


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _clamp_score(value: Any) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return 0.0
    return round(max(0.0, min(1.0, score)), 3)


def _short_text(value: Any, default: str) -> str:
    text = str(value).strip() if value is not None else default
    return text[:600]


SYSTEM_PROMPT = """You are a text-only semantic auditor for a course project named SceneTest.

You cannot see rendered images. Review only the provided prompt, contract JSON,
final scene JSON, graphics unit-test results, repair history, and scene stats.
Do not claim visual evidence.

The code tests are necessary but not sufficient. Your job is to catch semantic
problems that hard rules may miss:
- required prompt objects missing or represented by a wrong semantic type
- named real objects represented by weak primitive proxies that should be improved
- implausible object scale or support placement
- weak spatial-relation interpretation even when simple numeric tests pass
- scene construction that is so crude that the requested object cannot be understood
- mismatch between prompt style and scene lighting/material choices

Be fair and constructive for a graphics course prototype. Do not demand
photorealism, CAD-level assets, or image-level detail. The goal is to audit
semantic correctness of a generated scene program, not to grade artistic polish.
Accept primitive-based proxy modeling when the semantic object type, dimensions,
support relation, and relative placement make the object understandable.

Important limitation of this project: it is not a high-precision modeling
system. It intentionally uses primitive and composite proxy geometry. Therefore,
do not fail a scene merely because an object lacks fine geometry, texture,
curved surfaces, tiny parts, or artistic detail. If a named prompt object exists
with the correct id, approximate size, support, and relations but is represented
by a cube/sphere/cylinder-style proxy, treat that as a minor modeling limitation
or recommendation, not a major failure. Reserve major issues for semantic
failures such as: wrong object type, required object missing, object placed on
the floor when the prompt implies tabletop support, impossible relative scale,
or contradictory relations.

SceneBuilder units are abstract display units, not strict meters. Evaluate
relative scale and support fit more than absolute real-world dimensions. Do not
mark scale as a major issue unless object ratios are clearly impossible or the
scene would not be understandable.

The final Blender renderer can create composite primitive proxies from semantic
object types, so a scene_json shape of "box" does not automatically mean the
rendered object has no detail. Treat this as a minor construction risk unless
the object type itself is generic or semantically wrong.

Scoring rubric:
- 0.90-1.00: all hard constraints pass; semantic types, support, relations, and
  relative scale are coherent; only small polish issues remain.
- 0.80-0.89: solid course-project result with minor construction simplifications.
- 0.70-0.79: acceptable but with noticeable semantic or support/placement weaknesses.
- 0.55-0.69: partial result; important objects or placements are questionable.
- below 0.55: severe prompt mismatch, wrong object identity, impossible support,
  or scene cannot be understood from the structured artifacts.

If all code tests pass, do not assign an overall score below 0.80 unless you can
name a concrete semantic error that the tests missed, such as a required object
being the wrong type, a support placement that is physically impossible, or a
key object being reduced to generic/cube when a better semantic type exists.

Construction-quality scoring should be lenient: if an object is semantically
typed and placed correctly but lacks fine modeling details, construction_quality
should usually remain at least 0.75. Use recommendations for detail improvements
instead of turning them into major failures.

Return only one JSON object:
{
  "pass": true,
  "overall_score": 0.0,
  "prompt_alignment_score": 0.0,
  "object_semantics_score": 0.0,
  "relation_plausibility_score": 0.0,
  "scale_plausibility_score": 0.0,
  "construction_quality_score": 0.0,
  "summary": "short audit summary",
  "strengths": ["specific strength"],
  "issues": [
    {"severity": "major|minor", "category": "object|relation|scale|style|construction", "object_id": "optional", "message": "specific issue", "evidence": "short evidence"}
  ],
  "recommendations": ["specific improvement"],
  "confidence": 0.0
}
"""
