"""Lightweight web context via DuckDuckGo Instant Answer API (no API key)."""

from __future__ import annotations

import os
from typing import Any
from urllib.parse import urlencode

import httpx


def fetch_instant_answer_snippet(query: str, timeout: float = 10.0) -> str | None:
    """
    Returns a short plain-text snippet from DuckDuckGo's instant answer JSON.
    Disabled when MEDECHO_WEB_LOOKUP is 0/false, or on any network/parse error.
    """
    flag = (os.environ.get("MEDECHO_WEB_LOOKUP") or "1").strip().lower()
    if flag in ("0", "false", "no", "off"):
        return None

    q = (query or "").strip()
    if len(q) < 2:
        return None
    q = q[:400]

    params: dict[str, str] = {
        "q": q,
        "format": "json",
        "no_html": "1",
        "skip_disambig": "1",
    }
    url = "https://api.duckduckgo.com/?" + urlencode(params)

    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.get(url, headers={"User-Agent": "MedEcho/0.1 (patient education demo)"})
            resp.raise_for_status()
            data: dict[str, Any] = resp.json()
    except Exception:
        return None

    abstract = (data.get("Abstract") or "").strip()
    answer = (data.get("Answer") or "").strip()
    definition = (data.get("Definition") or "").strip()

    parts: list[str] = []
    for block in (answer, abstract, definition):
        if block and block not in " ".join(parts):
            parts.append(block)
    if not parts:
        return None

    source = (data.get("AbstractSource") or data.get("DefinitionSource") or "").strip()
    link = (data.get("AbstractURL") or data.get("DefinitionURL") or "").strip()

    body = "\n\n".join(parts)
    if source and link:
        return f"{body}\n(Source: {source} — {link})"
    if source:
        return f"{body}\n(Source: {source})"
    if link:
        return f"{body}\n(Link: {link})"
    return body
