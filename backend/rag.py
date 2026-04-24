"""Chunking, embeddings retrieval, and RAG answers (Mistral)."""

from __future__ import annotations

import math
import os
from typing import Any

from mistralai import Mistral
from mistralai.models import SDKError

from llm import LLMAuthError, _normalize_api_key, _assistant_content_to_text
from web_context import fetch_instant_answer_snippet


def _mistral_key() -> str:
    raw = os.environ.get("MISTRAL_API_KEY")
    if not raw or not raw.strip():
        raise RuntimeError("Missing LLM API key. Please set MISTRAL_API_KEY.")
    return _normalize_api_key(raw)


def _split_long(s: str, max_chars: int, overlap: int) -> list[str]:
    s = s.strip()
    if not s:
        return []
    out: list[str] = []
    i = 0
    while i < len(s):
        piece = s[i : i + max_chars]
        out.append(piece.strip())
        if i + max_chars >= len(s):
            break
        i += max(1, max_chars - overlap)
    return [p for p in out if p]


def chunk_document(text: str, max_chars: int = 1100, overlap: int = 160) -> list[str]:
    text = (text or "").strip()
    if not text:
        return []
    parts = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not parts:
        parts = [text]
    chunks: list[str] = []
    buf = ""
    for p in parts:
        if len(buf) + len(p) + 2 <= max_chars:
            buf = f"{buf}\n\n{p}".strip() if buf else p
        else:
            if buf:
                chunks.extend(_split_long(buf, max_chars, overlap))
            if len(p) <= max_chars:
                buf = p
            else:
                chunks.extend(_split_long(p, max_chars, overlap))
                buf = ""
    if buf:
        chunks.extend(_split_long(buf, max_chars, overlap))
    seen: set[str] = set()
    uniq: list[str] = []
    for c in chunks:
        key = c[:2000]
        if key in seen:
            continue
        seen.add(key)
        uniq.append(c)
    return uniq


def extracted_to_summary_chunk(extracted: dict[str, Any]) -> str:
    """Single retrieval chunk from structured extraction (plain text, not JSON)."""
    lines: list[str] = ["STRUCTURED SUMMARY (from the document — use for facts):"]
    pi = extracted.get("patient_info") or {}
    if isinstance(pi, dict):
        for label, key in (
            ("Patient", "name"),
            ("Age", "age"),
            ("Sex", "sex"),
            ("Visit date", "visit_date"),
            ("Doctor", "doctor_name"),
        ):
            v = str(pi.get(key, "") or "").strip()
            if v:
                lines.append(f"- {label}: {v}")
    for label, key in (
        ("Diagnoses", "diagnoses"),
        ("Follow-up", "follow_up"),
        ("Red flags", "red_flags"),
        ("Doctor instructions", "doctor_instructions"),
    ):
        items = extracted.get(key)
        if isinstance(items, list) and items:
            lines.append(f"\n{label}:")
            for it in items:
                if str(it).strip():
                    lines.append(f"- {it}")
    meds = extracted.get("medications")
    if isinstance(meds, list) and meds:
        lines.append("\nMedications:")
        for m in meds:
            if not isinstance(m, dict):
                continue
            name = str(m.get("name", "") or "").strip()
            if not name:
                continue
            bits = [name]
            for k in ("dose", "frequency", "timing", "duration", "warnings"):
                v = str(m.get(k, "") or "").strip()
                if v:
                    bits.append(f"{k}: {v}")
            lines.append("- " + "; ".join(bits))
    tests = extracted.get("tests")
    if isinstance(tests, list) and tests:
        lines.append("\nTests:")
        for t in tests:
            if not isinstance(t, dict):
                continue
            tn = str(t.get("test_name", "") or "").strip()
            if not tn:
                continue
            res = str(t.get("result", "") or "").strip()
            interp = str(t.get("interpretation", "") or "").strip()
            line = f"- {tn}"
            if res:
                line += f" — Result: {res}"
            if interp:
                line += f" — Note: {interp}"
            lines.append(line)
    return "\n".join(lines).strip()


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def embed_texts(client: Mistral, texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    model = os.environ.get("MISTRAL_EMBED_MODEL", "mistral-embed")
    batch = 32
    all_emb: list[list[float]] = []
    for i in range(0, len(texts), batch):
        chunk = texts[i : i + batch]
        try:
            resp = client.embeddings.create(model=model, inputs=chunk)
        except SDKError as e:
            if e.status_code == 401:
                raise LLMAuthError(
                    "Mistral returned 401 Unauthorized when embedding. "
                    "Check MISTRAL_API_KEY and restart uvicorn."
                ) from e
            raise RuntimeError(
                f"Mistral embedding error (HTTP {e.status_code}): {e.body or e.message!s}"
            ) from e
        rows = sorted(resp.data, key=lambda d: d.index or 0)
        for row in rows:
            emb = row.embedding
            if not emb:
                all_emb.append([0.0] * 1024)
            else:
                all_emb.append(list(emb))
    return all_emb


def build_chunks_and_embeddings(
    raw_text: str, extracted: dict[str, Any]
) -> tuple[list[str], list[list[float]]]:
    summary = extracted_to_summary_chunk(extracted)
    doc_chunks = chunk_document(raw_text)
    chunks = [summary]
    chunks.extend(doc_chunks)
    if len(chunks) == 1 and not doc_chunks:
        chunks = [summary]
    client = Mistral(api_key=_mistral_key())
    embeddings = embed_texts(client, chunks)
    if len(embeddings) != len(chunks):
        raise RuntimeError("Embedding count mismatch; try a smaller document.")
    return chunks, embeddings


def retrieve_context(
    client: Mistral,
    chunks: list[str],
    embeddings: list[list[float]],
    question: str,
    top_k: int = 6,
) -> str:
    if not chunks:
        return ""
    q_embs = embed_texts(client, [question.strip()])
    if not q_embs:
        return "\n\n".join(chunks[:top_k])
    qv = q_embs[0]
    scored: list[tuple[float, int]] = []
    for i, ev in enumerate(embeddings):
        scored.append((_cosine(qv, ev), i))
    scored.sort(key=lambda t: t[0], reverse=True)
    picked: list[str] = []
    for _, idx in scored[:top_k]:
        if 0 <= idx < len(chunks) and chunks[idx].strip():
            picked.append(chunks[idx].strip())
    return "\n\n---\n\n".join(picked)


RAG_INSTRUCTIONS = """You are AfterCare, helping a patient understand their health using BOTH their uploaded medical document AND broader medical information.

You should routinely combine information from these sources (use all that apply — do not limit yourself to the document alone):

1) **From your medical document** — STRUCTURED SUMMARY AND DOCUMENT EXCERPTS appear below under that heading.
   - Lead with what the document states about *this* patient (drugs, doses, diagnoses, instructions, follow-up, red flags).
   - Treat the document as authoritative for patient-specific facts. Never contradict it.

2) **Web instant summary** — When a “WEB INSTANT SUMMARY” block appears below, it is a short third-party snippet (DuckDuckGo). It may be incomplete or out of date.
   - Use it only as extra orientation; verify important facts. Say clearly it is not from their file.

3) **General medical knowledge** — Use your training: mainstream patient education and consensus-style guidance similar to reputable public sources (e.g. NIH, CDC, NHS, major hospital patient pages, drug-label concepts).
   - You are NOT doing live browsing beyond any WEB block provided; draw on widely published medical knowledge and say so if needed.
   - Always include a clearly labeled section when you add this: **General medical context (not from your document):**
   - This section should be **substantive whenever it helps** explain conditions, medications, tests, lifestyle, monitoring, or when to seek care — not only when the document is silent. Integrate it with the document section so the answer feels like one coherent explanation.
   - Do not invent patient-specific facts (names, doses, labs) that are not in the document excerpts.

Safety and tone:
- Plain language. You are not replacing their clinician; remind them to confirm with their doctor or pharmacist for personal decisions, dose changes, or new symptoms.
- Emergencies: advise urgent/emergency care when appropriate using general standards.

Format your reply with clear headings, for example:
- **From your medical document:** …
- **General medical context (not from your document):** …
(Include a **Web instant summary** bullet only if a WEB block was provided and you used it.)
"""


def answer_question(
    chunks: list[str],
    embeddings: list[list[float]],
    question: str,
) -> str:
    q = (question or "").strip()
    if not q:
        raise ValueError("Question cannot be empty.")

    client = Mistral(api_key=_mistral_key())
    context = retrieve_context(client, chunks, embeddings, q, top_k=6)
    if not context.strip():
        context = "(No document excerpts were retrieved; say so briefly, then still provide useful general medical context for the question.)"

    web_snippet = fetch_instant_answer_snippet(q)
    system_body = RAG_INSTRUCTIONS
    if web_snippet:
        system_body += (
            "\n\n---\nWEB INSTANT SUMMARY (third party; verify):\n"
            + web_snippet
            + "\n---"
        )
    system_body += "\n\nSTRUCTURED SUMMARY AND DOCUMENT EXCERPTS (from upload):\n" + context

    model = os.environ.get("MISTRAL_MODEL", "mistral-small-latest")
    user_msg = (
        f"Patient question:\n{q}\n\n"
        "Write a helpful answer that combines (1) what their document says, "
        "(2) any web instant summary provided above if relevant, and "
        "(3) a substantive **General medical context (not from your document):** section "
        "with mainstream patient-education information aligned with widely published sources. "
        "Do not stay document-only unless the question is purely administrative."
    )

    try:
        resp = client.chat.complete(
            model=model,
            messages=[
                {"role": "system", "content": system_body},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.3,
            max_tokens=2048,
        )
    except SDKError as e:
        if e.status_code == 401:
            raise LLMAuthError(
                "Mistral returned 401 Unauthorized. Check MISTRAL_API_KEY."
            ) from e
        raise RuntimeError(
            f"Mistral chat error (HTTP {e.status_code}): {e.body or e.message!s}"
        ) from e

    msg = resp.choices[0].message
    return _assistant_content_to_text(msg.content).strip() or (
        "I could not generate an answer. Please try rephrasing your question."
    )
