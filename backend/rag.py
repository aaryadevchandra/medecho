"""Chunking, embeddings retrieval, and RAG answers (Mistral)."""

from __future__ import annotations

import math
import os
from typing import Any

from mistralai import Mistral
from mistralai.models import SDKError

from llm import LLMAuthError, _normalize_api_key, _assistant_content_to_text


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


RAG_SYSTEM = """You are MedEcho, helping a patient understand their own uploaded medical document.

You have two sources of information — use BOTH when helpful:

1) PRIMARY — STRUCTURED SUMMARY AND DOCUMENT EXCERPTS (below). Always start here.
   - Quote or paraphrase what the document actually says about this patient.
   - Never contradict the document. If the document states a drug, dose, or instruction, treat that as authoritative for *this* patient.

2) SUPPLEMENTARY — your general medical / patient-education knowledge.
   - You MAY add well-established, non–patient-specific context when the document is silent or incomplete (e.g. typical diet counseling with metformin, what “twice daily” usually means, when to seek urgent care for common symptoms).
   - Clearly LABEL this section so the user can tell it is not from their file, e.g. a short heading: **General medical context (not from your document):**
   - Keep it accurate and conservative; prefer mainstream clinical guidance. If evidence is mixed or uncertain, say so.
   - Do not fabricate details about *this* patient that are not in the excerpts.

Safety and tone:
- Use plain language. You are not replacing their clinician; end supplementary sections with a brief reminder to confirm with their doctor or pharmacist when changing behavior, diet, or medications.
- If the user describes an emergency, tell them to seek urgent/emergency care as appropriate; you may use general knowledge for that.

STRUCTURED SUMMARY AND DOCUMENT EXCERPTS:
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
        context = "(No document excerpts were retrieved; rely on general medical education only, and say nothing is available from the uploaded file.)"

    model = os.environ.get("MISTRAL_MODEL", "mistral-small-latest")
    user_msg = (
        f"Patient question:\n{q}\n\n"
        "First, answer what their document says (if anything). "
        "Then, if useful, add a clearly labeled **General medical context (not from your document):** "
        "section with mainstream patient-education information. "
        "Keep both sections concise."
    )

    try:
        resp = client.chat.complete(
            model=model,
            messages=[
                {"role": "system", "content": RAG_SYSTEM + context},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.25,
            max_tokens=1400,
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
