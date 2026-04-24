"""Ingest the patient's discharge bundle (agent/knowledge_base/*.md) into the
ElevenLabs knowledge base for the aftercare agent and enable RAG.

Runs after `python -m tools.setup_agent`:
    python -m tools.upload_kb

For each .md file in agent/knowledge_base/:
  1. POST /v1/convai/knowledge-base/file (multipart) → document_id
  2. Collect ids
Then patches the agent with prompt.knowledge_base = [{type:"file", id, ...}]
and enables RAG.

The aftercare bundle is patient-private. We upload the local markdown verbatim.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from tools._config import (
    KB_DIR,
    KB_EMBEDDING_MODEL,
    KB_MAX_DOCUMENTS_LENGTH,
    KB_MAX_RETRIEVED_CHUNKS,
    KB_MAX_VECTOR_DISTANCE,
    ROOT,
)

load_dotenv(ROOT.parent / ".env")
load_dotenv(ROOT / ".env")
load_dotenv(ROOT / ".env.local", override=True)

import requests  # noqa: E402
from elevenlabs import ElevenLabs  # noqa: E402

API_BASE = "https://api.elevenlabs.io"


def _kb_files() -> list[Path]:
    if not KB_DIR.exists():
        return []
    return sorted(KB_DIR.glob("*.md"))


def _derive_name(path: Path) -> str:
    return path.stem.replace("_", " ")


def _post_file(api_key: str, path: Path, name: str) -> str | None:
    try:
        with path.open("rb") as fh:
            res = requests.post(
                f"{API_BASE}/v1/convai/knowledge-base/file",
                headers={"xi-api-key": api_key},
                data={"name": name},
                files={"file": (path.name, fh, "text/markdown")},
                timeout=60,
            )
    except requests.RequestException as e:
        print(f"  x {path.name} -> {e}", file=sys.stderr)
        return None

    if not res.ok:
        print(f"  x {path.name} -> {res.status_code} {res.text[:160]}", file=sys.stderr)
        return None

    data = res.json()
    return data.get("id") or data.get("document_id")


def main() -> None:
    api_key = os.environ.get("ELEVENLABS_API_KEY")
    agent_id = os.environ.get("NEXT_PUBLIC_AGENT_ID")

    if not api_key:
        print("ELEVENLABS_API_KEY missing in .env", file=sys.stderr)
        sys.exit(1)
    if not agent_id:
        print(
            "NEXT_PUBLIC_AGENT_ID missing - run `python -m tools.setup_agent` first.",
            file=sys.stderr,
        )
        sys.exit(1)

    files = _kb_files()
    if not files:
        print(f"No .md files found in {KB_DIR}", file=sys.stderr)
        sys.exit(1)

    print(f"Ingesting {len(files)} bundle files into KB for agent {agent_id}...\n")

    docs: list[dict] = []
    for path in files:
        name = _derive_name(path)
        doc_id = _post_file(api_key, path, name)
        if doc_id:
            docs.append({"type": "file", "id": doc_id, "name": name, "usage_mode": "auto"})
            print(f"  OK {name}  ({doc_id})")

    if not docs:
        print("\nNo documents ingested. Aborting agent patch.", file=sys.stderr)
        sys.exit(1)

    print(f"\nPatching agent with {len(docs)} KB documents + RAG...")
    client = ElevenLabs(api_key=api_key)
    client.conversational_ai.agents.update(
        agent_id=agent_id,
        conversation_config={
            "agent": {
                "prompt": {
                    "knowledge_base": docs,
                    "rag": {
                        "enabled": True,
                        "embedding_model": KB_EMBEDDING_MODEL,
                        "max_documents_length": KB_MAX_DOCUMENTS_LENGTH,
                        "max_retrieved_rag_chunks_count": KB_MAX_RETRIEVED_CHUNKS,
                        "max_vector_distance": KB_MAX_VECTOR_DISTANCE,
                    },
                }
            }
        },
    )

    print("\nKnowledge base attached. RAG enabled.\n")
    print("Smoke-test queries (run from the demo widget):")
    print("  'What pills do I take tonight?'")
    print("  'Can I take Advil with my warfarin?'")
    print("  'I forgot my eight AM water pill, what do I do?'")
    print("  'My INR was three point two, is that okay?'")
    print("  'I have chest pain right now.'")


if __name__ == "__main__":
    try:
        main()
    except Exception as err:
        print(f"\nKB upload failed: {err}", file=sys.stderr)
        raise
