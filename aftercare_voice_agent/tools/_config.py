"""Shared constants for the aftercare automation scripts."""

from __future__ import annotations

import os
from pathlib import Path

# ---- paths ------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
AGENT_DIR = ROOT / "agent"
KB_DIR = AGENT_DIR / "knowledge_base"
PUBLIC_DIR = ROOT / "public"
ENV_LOCAL = ROOT / ".env.local"

# ---- agent identity ---------------------------------------------------------
AGENT_NAME = "Aftercare Aria - post-discharge copilot"
AGENT_TAGS = ["demo", "aftercare", "post-discharge", "elevenlabs"]

# ---- models -----------------------------------------------------------------
# Sonnet 4.6 over Haiku for tool-calling reliability. In a clinical-safety
# domain we want the LLM to *call the escalation tool* on edge cases, not
# improvise an answer. That's exactly the failure mode Sonnet handles better.
LLM_DEFAULT = "claude-sonnet-4-6"
TEMPERATURE = 0.2          # tighter than mb's 0.3 — safety domain, less variance
MAX_TOKENS = 110           # voice brevity ceiling (~80 spoken words)

ASR_PROVIDER = "scribe_realtime"

# Flash v2 — only TTS the API accepts on English-primary agents (same as mb).
TTS_MODEL = "eleven_flash_v2"
TTS_MODEL_GREETING = "eleven_v3"   # pre-rendered greeting + voice moments

# ---- voices (override via env) ----------------------------------------------
# Default to a calm mature female voice. Patient cohort here skews older;
# warm low-mid voice tested better than bright/young in similar deployments.
VOICE_ID_EN = os.getenv("ELEVENLABS_VOICE_ID_EN", "EXAVITQu4vr4xnSDxMaL")  # Sarah — calm multilingual

# TTS settings — slower, steadier than mb's bank persona.
TTS_STABILITY = 0.80
TTS_SIMILARITY = 0.92
TTS_STYLE = 0.10                  # care voice, not personality voice
TTS_USE_SPEAKER_BOOST = True
TTS_SPEED = 0.92                  # slower than mb's 0.95 — patients > bank customers on patience

# ---- turn taking ------------------------------------------------------------
# `patient` — patients formulate questions slowly, especially when foggy.
# Don't barge in.
TURN_EAGERNESS = "patient"
TURN_TIMEOUT = 9                   # bumped from mb's 7 — patients pause longer

# ---- backend ----------------------------------------------------------------
AFTERCARE_API_PORT = int(os.getenv("AFTERCARE_API_PORT", "8002"))
TOOL_BASE_URL = os.getenv("TOOL_BASE_URL", f"http://localhost:{AFTERCARE_API_PORT}")

# ---- KB / RAG ---------------------------------------------------------------
KB_EMBEDDING_MODEL = "multilingual_e5_large_instruct"
KB_MAX_DOCUMENTS_LENGTH = 50000
KB_MAX_RETRIEVED_CHUNKS = 6        # one extra slot vs mb — clinical answers benefit from cross-doc context (prescription + red flag)
KB_MAX_VECTOR_DISTANCE = 0.65      # tighter than mb — we want fewer false-positive RAG hits in a safety domain

# ---- call limits ------------------------------------------------------------
MAX_DURATION_SECONDS = 1200        # 20 min cap — patients can need longer than bank callers
