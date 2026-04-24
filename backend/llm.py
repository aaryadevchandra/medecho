"""LLM-backed medical document JSON extraction (Mistral AI official SDK)."""

from __future__ import annotations

import json
import os
import re
from typing import Any

from mistralai import Mistral
from mistralai.models import SDKError

MEDICATION_ITEM: dict[str, str] = {
    "name": "",
    "dose": "",
    "frequency": "",
    "timing": "",
    "duration": "",
    "warnings": "",
}

TEST_ITEM: dict[str, str] = {
    "test_name": "",
    "result": "",
    "interpretation": "",
}

EMPTY_SCHEMA: dict[str, Any] = {
    "patient_info": {
        "name": "",
        "age": "",
        "sex": "",
        "visit_date": "",
        "doctor_name": "",
    },
    "diagnoses": [],
    "medications": [],
    "tests": [],
    "follow_up": [],
    "red_flags": [],
    "doctor_instructions": [],
}

EXTRACTION_PROMPT = """You are a medical document extraction assistant.

Extract only information explicitly present in the uploaded medical document.
Do not infer, guess, diagnose, or add external medical knowledge.
If a field is missing, return an empty string or empty array.
Return valid JSON only. No markdown. No explanation.

Use this schema exactly:

{
  "patient_info": {
    "name": "",
    "age": "",
    "sex": "",
    "visit_date": "",
    "doctor_name": ""
  },
  "diagnoses": [],
  "medications": [
    {
      "name": "",
      "dose": "",
      "frequency": "",
      "timing": "",
      "duration": "",
      "warnings": ""
    }
  ],
  "tests": [
    {
      "test_name": "",
      "result": "",
      "interpretation": ""
    }
  ],
  "follow_up": [],
  "red_flags": [],
  "doctor_instructions": []
}

Document text:

"""


class LLMAuthError(Exception):
    """Mistral API rejected credentials (e.g. 401)."""


def _normalize_api_key(raw: str) -> str:
    key = raw.strip().strip('"').strip("'")
    if key.lower().startswith("bearer "):
        key = key[7:].strip()
    return key


def _deep_merge_defaults(data: Any, defaults: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(data, dict):
        return json.loads(json.dumps(defaults))
    out: dict[str, Any] = {}
    for key, default_val in defaults.items():
        if key not in data:
            out[key] = json.loads(json.dumps(default_val))
            continue
        val = data[key]
        if isinstance(default_val, dict) and isinstance(val, dict):
            out[key] = _deep_merge_defaults(val, default_val)
        elif key == "medications":
            out[key] = _normalize_list_of_dicts(val, MEDICATION_ITEM)
        elif key == "tests":
            out[key] = _normalize_list_of_dicts(val, TEST_ITEM)
        elif isinstance(default_val, list):
            out[key] = val if isinstance(val, list) else []
        else:
            out[key] = val if val is not None else default_val
    return out


def _normalize_list_of_dicts(val: Any, tmpl: dict[str, str]) -> list[dict[str, Any]]:
    if not isinstance(val, list):
        return []
    result: list[dict[str, Any]] = []
    for item in val:
        if not isinstance(item, dict):
            continue
        merged = {k: str(item.get(k, "") or "") for k in tmpl}
        result.append(merged)
    return result


def _strip_json_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _assistant_content_to_text(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for chunk in content:
            if hasattr(chunk, "text") and getattr(chunk, "text", None):
                parts.append(str(chunk.text))
            elif isinstance(chunk, dict) and chunk.get("text"):
                parts.append(str(chunk["text"]))
        return "".join(parts)
    return str(content)


def extract_structured_json(document_text: str) -> dict[str, Any]:
    raw_key = os.environ.get("MISTRAL_API_KEY")
    if not raw_key or not raw_key.strip():
        raise RuntimeError(
            "Missing LLM API key. Please set MISTRAL_API_KEY."
        )

    api_key = _normalize_api_key(raw_key)
    user_content = EXTRACTION_PROMPT + document_text
    return _call_mistral(user_content, api_key)


def _call_mistral(user_content: str, api_key: str) -> dict[str, Any]:
    model = os.environ.get("MISTRAL_MODEL", "mistral-small-latest")
    client = Mistral(api_key=api_key)

    try:
        response = client.chat.complete(
            model=model,
            messages=[{"role": "user", "content": user_content}],
            response_format={"type": "json_object"},
            temperature=0,
        )
    except SDKError as e:
        if e.status_code == 401:
            raise LLMAuthError(
                "Mistral returned 401 Unauthorized. Use an API key from "
                "https://console.mistral.ai/ (API keys), set export MISTRAL_API_KEY=... "
                "in the same terminal where you run uvicorn (no quotes; restart the server "
                "after changing env vars). OpenAI keys will not work here."
            ) from e
        raise RuntimeError(
            f"Mistral API error (HTTP {e.status_code}): {e.body or e.message!s}"
        ) from e

    msg = response.choices[0].message
    raw = _assistant_content_to_text(msg.content) or "{}"
    parsed = json.loads(_strip_json_fences(raw))
    return _deep_merge_defaults(parsed, EMPTY_SCHEMA)
