from __future__ import annotations

import json
import re
from typing import Any

import httpx


def groq_chat_completion(
    *,
    api_base: str,
    api_key: str,
    model: str,
    messages: list[dict[str, str]],
    temperature: float = 0.2,
    timeout_s: float = 120.0,
) -> str:
    """Call Groq OpenAI-compatible chat completions; return assistant message content."""
    url = f"{api_base}/chat/completions"
    base_payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }

    def _post(payload: dict[str, Any]) -> str:
        r = httpx.post(
            url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=timeout_s,
        )
        r.raise_for_status()
        data = r.json()
        choices = data.get("choices") or []
        if not choices:
            raise RuntimeError(f"Groq response missing choices: {data}")
        content = choices[0].get("message", {}).get("content") or ""
        if not isinstance(content, str):
            raise RuntimeError("Groq assistant content is not a string")
        return content

    try:
        payload = dict(base_payload)
        payload["response_format"] = {"type": "json_object"}
        return _post(payload)
    except httpx.HTTPStatusError as e:
        if e.response is not None and e.response.status_code == 400:
            return _post(dict(base_payload))
        raise


def parse_json_object(text: str) -> dict[str, Any]:
    text = text.strip()
    m = re.search(r"\{[\s\S]*\}\s*$", text)
    if m:
        text = m.group(0)
    return json.loads(text)
