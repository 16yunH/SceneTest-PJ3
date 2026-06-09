"""Optional DeepSeek-backed Contract Agent.

The key is never stored in project files. Set DEEPSEEK_API_KEY in the shell
when you want live contract extraction.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from typing import Any, Dict

from scenetest.agents.contract_agent import ContractAgent
from scenetest.core.contract_schema import SceneContract


DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-v4-pro"


class DeepSeekContractAgent:
    def __init__(
        self,
        api_key: str | None = None,
        model: str = DEFAULT_MODEL,
        base_url: str = DEEPSEEK_BASE_URL,
        timeout: int = 60,
        fallback: bool = True,
    ) -> None:
        self.api_key = api_key or os.environ.get("DEEPSEEK_API_KEY")
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.fallback = fallback
        self.local_agent = ContractAgent()

    def parse(self, prompt: str, scene_id: str | None = None) -> SceneContract:
        if not self.api_key:
            if self.fallback:
                return self.local_agent.parse(prompt, scene_id=scene_id)
            raise RuntimeError("DEEPSEEK_API_KEY is not set")
        try:
            payload = self._request_contract(prompt, scene_id=scene_id)
            payload.setdefault("prompt", prompt)
            if scene_id:
                payload["id"] = scene_id
            return SceneContract.from_dict(payload)
        except Exception:
            if self.fallback:
                return self.local_agent.parse(prompt, scene_id=scene_id)
            raise

    def _request_contract(self, prompt: str, scene_id: str | None = None) -> Dict[str, Any]:
        body = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": f"scene_id: {scene_id or 'scene'}\nprompt: {prompt}",
                },
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        }
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
        content = data["choices"][0]["message"]["content"]
        return _extract_json(content)


def _extract_json(text: str) -> Dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text).strip()
        text = re.sub(r"```$", "", text).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end < start:
        raise ValueError("DeepSeek response did not contain a JSON object")
    return json.loads(text[start : end + 1])


SYSTEM_PROMPT = """You are the Contract Agent for SceneTest.
Extract a strict JSON Scene Contract from the user prompt.

Return only one JSON object with this shape:
{
  "id": "short_scene_id",
  "prompt": "original prompt",
  "objects": [
    {"id": "stable_snake_case_id", "type": "desk|table|low_table|laptop|cup|lamp|book|plant|chair|sofa|bed|shelf|cube|sphere|cylinder|cone", "required": true, "material": "optional", "color": "optional"}
  ],
  "relations": [
    {"subject": "object_id", "relation": "on|left_of|right_of|behind|in_front_of|near", "object": "object_id", "margin": 0.2}
  ],
  "style": {"lighting": "warm|neutral|minimal|cyberpunk|medieval|futuristic", "palette": ["color"], "mood": "short mood"},
  "camera": {"view": "front_perspective", "visible_objects": ["object_id"]}
}

Use only object types supported by the schema. Keep ids stable and snake_case.
For natural-language phrases like "a cup to the right of the laptop", use
{"subject":"cup","relation":"right_of","object":"laptop"}.
Do not include explanatory text.
"""
