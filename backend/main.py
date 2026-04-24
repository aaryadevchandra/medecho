"""Aftercare API - upload discharge documents, structured extraction, and RAG Q&A."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

from document_parser import extract_text
from llm import LLMAuthError, extract_structured_json
from rag import answer_question, build_chunks_and_embeddings
from session_store import create_session, get_session

ALLOWED_EXTENSIONS = {".pdf", ".txt"}

app = FastAPI(title="Aftercare API", version="0.1.0")

# Local dev: allow any origin without credentials so browser reads 4xx/5xx JSON
# (avoids "CORS missing" when Origin is another localhost port or 127.0.0.1 vs localhost).
# Tighten allow_origins + allow_credentials for production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AskRequest(BaseModel):
    question: str = Field(..., max_length=4000)

    @field_validator("question")
    @classmethod
    def strip_question(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("Question cannot be empty.")
        return s



@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/upload-and-extract")
async def upload_and_extract(file: UploadFile = File(...)) -> dict:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")

    suffix = Path(file.filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Only PDF and TXT files are supported.",
        )

    if not (os.environ.get("MISTRAL_API_KEY") or "").strip():
        raise HTTPException(
            status_code=503,
            detail="Missing LLM API key. Please set MISTRAL_API_KEY.",
        )

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = Path(tmp.name)

        try:
            raw_text = extract_text(tmp_path, suffix)
        finally:
            tmp_path.unlink(missing_ok=True)

        try:
            extracted = extract_structured_json(raw_text)
        except LLMAuthError as e:
            raise HTTPException(status_code=401, detail=str(e)) from e
        except RuntimeError as e:
            raise HTTPException(status_code=503, detail=str(e)) from e
        except Exception as e:
            raise HTTPException(
                status_code=502,
                detail=f"LLM extraction failed: {e!s}",
            ) from e

        try:
            chunks, embeddings = build_chunks_and_embeddings(raw_text, extracted)
        except LLMAuthError as e:
            raise HTTPException(status_code=401, detail=str(e)) from e
        except RuntimeError as e:
            raise HTTPException(status_code=503, detail=str(e)) from e
        except Exception as e:
            raise HTTPException(
                status_code=502,
                detail=f"Could not index document for Q&A: {e!s}",
            ) from e

        session = create_session(
            filename=file.filename,
            raw_text=raw_text,
            chunks=chunks,
            embeddings=embeddings,
            extracted=extracted,
        )

        return {
            "session_id": session.session_id,
            "filename": session.filename,
            "extracted": extracted,
        }
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/sessions/{session_id}/ask")
def ask_session(session_id: str, body: AskRequest) -> dict[str, str]:
    if not (os.environ.get("MISTRAL_API_KEY") or "").strip():
        raise HTTPException(
            status_code=503,
            detail="Missing LLM API key. Please set MISTRAL_API_KEY.",
        )

    session = get_session(session_id)
    if session is None:
        raise HTTPException(
            status_code=404,
            detail="Session not found or expired. Upload your document again.",
        )

    try:
        answer = answer_question(
            session.chunks,
            session.chunk_embeddings,
            body.question,
        )
    except LLMAuthError as e:
        raise HTTPException(status_code=401, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Could not answer question: {e!s}",
        ) from e

    return {"answer": answer}
