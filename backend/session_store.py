"""In-memory document sessions for RAG Q&A (no database)."""

from __future__ import annotations

import threading
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

MAX_SESSIONS = 200


@dataclass
class DocumentSession:
    session_id: str
    filename: str
    raw_text: str
    chunks: list[str]
    chunk_embeddings: list[list[float]]
    extracted: dict[str, Any]


_lock = threading.Lock()
_sessions: OrderedDict[str, DocumentSession] = OrderedDict()


def create_session(
    filename: str,
    raw_text: str,
    chunks: list[str],
    embeddings: list[list[float]],
    extracted: dict[str, Any],
) -> DocumentSession:
    sid = str(uuid4())
    session = DocumentSession(
        session_id=sid,
        filename=filename,
        raw_text=raw_text,
        chunks=chunks,
        chunk_embeddings=embeddings,
        extracted=extracted,
    )
    with _lock:
        _sessions[sid] = session
        _sessions.move_to_end(sid)
        while len(_sessions) > MAX_SESSIONS:
            _sessions.popitem(last=False)
    return session


def get_session(session_id: str) -> DocumentSession | None:
    with _lock:
        s = _sessions.get(session_id)
        if s is not None:
            _sessions.move_to_end(session_id)
        return s
