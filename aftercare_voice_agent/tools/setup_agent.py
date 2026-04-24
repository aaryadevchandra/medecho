"""Create or update the Aftercare 'Aria' post-discharge voice agent.

Runs:
    python -m tools.setup_agent
    python -m tools.setup_agent --update
    python -m tools.setup_agent --llm <id>
"""

from __future__ import annotations

import argparse
import os
import re
import sys

from dotenv import load_dotenv

from tools._config import (
    AGENT_DIR,
    AGENT_NAME,
    AGENT_TAGS,
    ASR_PROVIDER,
    ENV_LOCAL,
    LLM_DEFAULT,
    MAX_DURATION_SECONDS,
    MAX_TOKENS,
    ROOT,
    TEMPERATURE,
    TTS_MODEL,
    TTS_SIMILARITY,
    TTS_SPEED,
    TTS_STABILITY,
    TTS_STYLE,
    TTS_USE_SPEAKER_BOOST,
    TURN_EAGERNESS,
    TURN_TIMEOUT,
    VOICE_ID_EN,
)

load_dotenv(ROOT.parent / ".env")
load_dotenv(ROOT / ".env")
load_dotenv(ROOT / ".env.local", override=True)

import requests  # noqa: E402
from elevenlabs import ElevenLabs  # noqa: E402

API_BASE = "https://api.elevenlabs.io"


def _load_system_prompt() -> str:
    return (AGENT_DIR / "system_prompt.md").read_text(encoding="utf-8")


def _load_first_message() -> str:
    md = (AGENT_DIR / "first_message.md").read_text(encoding="utf-8")
    match = re.search(r"## Primary[^\n]*\n+>\s*(.+?)\n", md)
    if not match:
        raise RuntimeError("first_message.md: could not find primary greeting line")
    return match.group(1).strip()


def _client_tool(
    *,
    name: str,
    description: str,
    properties: dict,
    required: list[str],
    expects_response: bool = True,
    response_timeout_secs: int = 15,
) -> dict:
    """Build a client-side tool config for the ElevenLabs agent."""
    return {
        "type": "client",
        "name": name,
        "description": description,
        "expects_response": expects_response,
        "response_timeout_secs": response_timeout_secs,
        "parameters": {
            "type": "object",
            "properties": properties,
            "required": required,
        },
    }


def _build_tools() -> list[dict]:
    return [
        _client_tool(
            name="get_medications",
            description=(
                "Return the patient's full medication regimen — names, doses, schedule, and "
                "with-food rules. Call when the patient says anything like 'what am I taking', "
                "'list my meds', 'what's my schedule', 'what do I take tonight', 'remind me'. "
                "After the tool returns, speak a SUMMARY (count + general timing), not a dump. "
                "Then offer to walk through one at a time."
            ),
            properties={
                "patient_id": {
                    "type": "string",
                    "description": "Optional patient id override; defaults to the demo patient.",
                },
            },
            required=[],
        ),
        _client_tool(
            name="get_medication_detail",
            description=(
                "Answer ONE specific question about ONE medication, grounded in the patient's "
                "discharge bundle. Call when the patient asks about a single drug. "
                "Pick the closest question_type: 'with_food' for timing/food questions, "
                "'if_missed' for missed-dose handling, 'side_effects' for symptom questions about "
                "that drug, 'interactions' for 'can I take X with this' or alcohol/OTC questions, "
                "'why_prescribed' for 'why am I on this'. "
                "If the tool returns not_in_bundle: true, do NOT improvise — say so plainly and "
                "call escalate_to_clinician next."
            ),
            properties={
                "medication_name": {
                    "type": "string",
                    "description": (
                        "Drug name as the patient said it — brand or generic. Examples: "
                        "'warfarin', 'coumadin', 'water pill', 'metoprolol', 'the morning pill'. "
                        "The backend resolves common aliases."
                    ),
                },
                "question_type": {
                    "type": "string",
                    "enum": ["with_food", "if_missed", "side_effects", "interactions", "why_prescribed"],
                    "description": (
                        "Which facet of the medication the patient is asking about. Pick the "
                        "closest match — do not call the tool twice for the same drug."
                    ),
                },
            },
            required=["medication_name", "question_type"],
        ),
        _client_tool(
            name="log_dose",
            description=(
                "Record a medication adherence event for the care team. Call when the patient says "
                "anything like 'I just took', 'I forgot my', 'I missed', 'I skipped', 'I'm taking "
                "it now'. "
                "After the tool returns, speak its return value verbatim — it contains the right "
                "missed-dose instruction from the patient's bundle. Do NOT invent a missed-dose rule."
            ),
            properties={
                "medication_name": {
                    "type": "string",
                    "description": "Drug name as the patient said it (the backend resolves aliases).",
                },
                "status": {
                    "type": "string",
                    "enum": ["taken", "missed", "skipped"],
                    "description": (
                        "'taken' if she took it (now or recently), 'missed' if she forgot and is "
                        "asking what to do, 'skipped' if she chose not to take it (and you should "
                        "ask why on the next turn)."
                    ),
                },
                "taken_at": {
                    "type": "string",
                    "description": (
                        "ISO-8601 datetime in the patient's local time, OR the literal string 'now'. "
                        "If the patient says 'just now' or 'a minute ago', use 'now'. If she names a "
                        "time, format it as ISO-8601 for today."
                    ),
                },
            },
            required=["medication_name", "status", "taken_at"],
        ),
        _client_tool(
            name="check_adherence",
            description=(
                "Look up what the patient has taken so far today and what's due next. Call when "
                "the patient says 'am I on track', 'did I miss anything today', 'when's my next "
                "dose', 'what's next'. "
                "After the tool returns, speak ONE short status sentence + the next dose with "
                "time and name. Do not list every dose."
            ),
            properties={
                "as_of": {
                    "type": "string",
                    "description": (
                        "Optional ISO-8601 datetime representing the patient's local time. If "
                        "omitted, the backend uses server time. Include only if the patient stated "
                        "a specific time of day."
                    ),
                },
            },
            required=[],
        ),
        _client_tool(
            name="explain_lab_result",
            description=(
                "Read a lab value from the patient's discharge labs in plain language. Call when "
                "the patient names a test ('my INR', 'my potassium', 'the kidney number') or reads "
                "a value off paper and asks what it means. "
                "If the tool returns not_in_bundle: true, do NOT speculate — say it isn't in her "
                "discharge labs and call escalate_to_clinician (urgency: medium)."
            ),
            properties={
                "test_name": {
                    "type": "string",
                    "description": (
                        "Lab name as the patient said it. Examples: 'INR', 'PT INR', 'potassium', "
                        "'kidney', 'BNP', 'blood count', 'hemoglobin'. The backend resolves aliases."
                    ),
                },
            },
            required=["test_name"],
        ),
        _client_tool(
            name="get_followup_plan",
            description=(
                "Return the patient's upcoming appointments and the key red-flag reminder. Call "
                "when she asks 'when's my appointment', 'when do I see the doctor', 'what should "
                "I watch for', 'when do I worry'. "
                "After the tool returns, speak the next appointment + one red-flag reminder. Don't "
                "list all three appointments aloud."
            ),
            properties={},
            required=[],
        ),
        _client_tool(
            name="escalate_to_clinician",
            description=(
                "THE MOST IMPORTANT TOOL. Hand off to the on-call nurse / doctor. Call this when:\n"
                "- A red-flag symptom is reported (chest pain, worsening shortness of breath, "
                "  bleeding, confusion, fall, suspected overdose, suicidal ideation, severe allergic "
                "  reaction) — urgency CRITICAL, in the SAME turn, do NOT finish your sentence first.\n"
                "- The question is outside the patient's bundle (different drug, different person, "
                "  unknown lab) — urgency MEDIUM.\n"
                "- A tool returned not_in_bundle: true or an error — urgency MEDIUM.\n"
                "- The patient explicitly asks for a human or sounds frustrated — urgency HIGH.\n"
                "- A red-flag-but-not-critical symptom (2+ lb weight gain in a day, swelling worse, "
                "  easy bruising in many spots) — urgency HIGH.\n\n"
                "Discipline:\n"
                "- Do NOT pre-announce. The tool's return value IS your spoken response.\n"
                "- Fire it in the SAME turn you decide to escalate. Never split across two turns.\n"
                "- Never invent a case reference, ETA, or nurse name. Use what the tool returns.\n"
                "- After it succeeds, stop. Do not call any more tools. Do not offer further help."
            ),
            properties={
                "reason": {
                    "type": "string",
                    "description": (
                        "Short reason. Examples: 'patient reports chest pain', 'asked about "
                        "non-bundle drug', 'tool_failure', 'patient requested human', 'red-flag "
                        "weight gain 2 lb overnight'."
                    ),
                },
                "urgency": {
                    "type": "string",
                    "enum": ["low", "medium", "high", "critical"],
                    "description": (
                        "'critical' for life-threatening / 911-adjacent. "
                        "'high' for red-flag symptoms warranting a 15-minute callback. "
                        "'medium' for non-bundle questions or tool failures. "
                        "'low' for routine non-urgent care-team notes."
                    ),
                },
                "summary": {
                    "type": "string",
                    "description": (
                        "Clinician-ready summary, UNDER 25 words. Who, what they're describing, "
                        "what you've done so far, what they need next."
                    ),
                },
                "transcript_snippet": {
                    "type": "string",
                    "description": (
                        "Recent 1-2 turn transcript excerpt. Use 'patient: ... aria: ...' format."
                    ),
                },
                "recommended_action": {
                    "type": "string",
                    "description": (
                        "One concrete next step for the clinician. Example: 'Confirm INR within "
                        "8 hours and assess for active bleeding before next warfarin dose.'"
                    ),
                },
            },
            required=["reason", "urgency", "summary", "transcript_snippet", "recommended_action"],
        ),
    ]


def _build_built_in_tools() -> dict:
    return {
        "end_call": {
            "name": "end_call",
            "description": "End the call when the patient has clearly wrapped (said goodbye, said thanks and stopped).",
            "params": {"system_tool_type": "end_call"},
        },
        # Explicitly disable transfer_to_number — same reason as mb. We have no
        # PSTN line in browser demo mode and the system-tool description
        # competes with our client-side escalate_to_clinician.
        "transfer_to_number": None,
        # No language_detection — English-only prototype. Add later when needed.
    }


def _build_conversation_config(system_prompt: str, first_message: str, llm: str) -> dict:
    return {
        "agent": {
            "first_message": first_message,
            "language": "en",
            "prompt": {
                "prompt": system_prompt,
                "llm": llm,
                "temperature": TEMPERATURE,
                "max_tokens": MAX_TOKENS,
                "tools": _build_tools(),
                # Do NOT set tool_ids here — ElevenLabs auto-creates workspace
                # tool resources and populates tool_ids; sending [] would orphan
                # them. _sync_tool_ids_by_name re-attaches by name after.
                "built_in_tools": _build_built_in_tools(),
            },
        },
        "asr": {
            "provider": ASR_PROVIDER,
            "quality": "high",
            # Keywords aid ASR for clinical terms patients may pronounce
            # softly or when foggy. Generic English words like "missed" or
            # "took" don't need this.
            "keywords": [
                "furosemide", "Lasix",
                "lisinopril",
                "metoprolol", "Toprol",
                "warfarin", "Coumadin",
                "INR", "BNP",
                "Aria",
            ],
        },
        "tts": {
            "voice_id": VOICE_ID_EN,
            "model_id": TTS_MODEL,
            "stability": TTS_STABILITY,
            "similarity_boost": TTS_SIMILARITY,
            "style": TTS_STYLE,
            "use_speaker_boost": TTS_USE_SPEAKER_BOOST,
            "speed": TTS_SPEED,
        },
        "turn": {
            "turn_eagerness": TURN_EAGERNESS,
            "turn_timeout": TURN_TIMEOUT,
        },
        "conversation": {
            "max_duration_seconds": MAX_DURATION_SECONDS,
            "text_only": False,
        },
    }


def _build_platform_settings() -> dict:
    return {
        "summary_language": "en",
        "widget": {
            "show_agent_status": True,
            "show_conversation_id": True,
            "strip_audio_tags": True,
        },
    }


def _strip_built_in_tools(conversation_config: dict) -> dict:
    """Prepare an update payload for ElevenLabs agent config PATCH calls.

    The follow-up patches re-add built_in_tools and re-attach client tool ids
    by name.
    """
    cc = {k: v for k, v in conversation_config.items()}
    if "agent" in cc and "prompt" in cc["agent"]:
        agent = {k: v for k, v in cc["agent"].items()}
        prompt = {k: v for k, v in agent["prompt"].items() if k != "built_in_tools"}
        prompt["tool_ids"] = []
        agent["prompt"] = prompt
        cc["agent"] = agent
    return cc


def _patch_agent(api_key: str, agent_id: str, payload: dict) -> None:
    res = requests.patch(
        f"{API_BASE}/v1/convai/agents/{agent_id}",
        headers={"xi-api-key": api_key, "Content-Type": "application/json"},
        json=payload,
        timeout=30,
    )
    if not res.ok:
        print(f"Update failed: {res.status_code} {res.text}", file=sys.stderr)
        sys.exit(1)


def _sync_tool_ids_by_name(api_key: str, agent_id: str, wanted_names: list[str]) -> None:
    """After the inline tools spec creates workspace tool records, re-attach
    them to the agent by name. Same pattern as mb."""
    res = requests.get(
        f"{API_BASE}/v1/convai/tools",
        headers={"xi-api-key": api_key},
        timeout=30,
    )
    if not res.ok:
        print(f"Tool list fetch failed: {res.status_code} {res.text}", file=sys.stderr)
        return
    data = res.json()
    items = data.get("tools", data) if isinstance(data, dict) else data
    name_to_ids: dict[str, list[tuple[str, int]]] = {}
    for tool in items if isinstance(items, list) else []:
        cfg = tool.get("tool_config", {})
        name = cfg.get("name")
        if name in wanted_names and cfg.get("type") == "client":
            name_to_ids.setdefault(name, []).append(
                (tool["id"], tool.get("created_at_unix_secs", 0))
            )
    ids: list[str] = []
    for name in wanted_names:
        matches = name_to_ids.get(name, [])
        if not matches:
            print(f"  (skip) no workspace tool named {name!r}")
            continue
        matches.sort(key=lambda pair: pair[1], reverse=True)
        ids.append(matches[0][0])
    if not ids:
        print("  (sync) no client tools to attach")
        return
    _patch_agent(
        api_key,
        agent_id,
        {"conversation_config": {"agent": {"prompt": {"tool_ids": ids}}}},
    )
    print(f"  OK attached {len(ids)} client tool ids to agent")


def _persist_agent_id(agent_id: str) -> None:
    existing = ENV_LOCAL.read_text(encoding="utf-8") if ENV_LOCAL.exists() else ""
    lines = [line for line in existing.splitlines() if not line.startswith("NEXT_PUBLIC_AGENT_ID=")]
    lines.append(f"NEXT_PUBLIC_AGENT_ID={agent_id}")
    ENV_LOCAL.write_text("\n".join(l for l in lines if l) + "\n", encoding="utf-8")
    print(f"  OK wrote NEXT_PUBLIC_AGENT_ID to {ENV_LOCAL.relative_to(ROOT)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--update", action="store_true", help="patch existing agent")
    parser.add_argument("--llm", default=LLM_DEFAULT, help="LLM model id")
    args = parser.parse_args()

    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        print("ELEVENLABS_API_KEY missing - check .env", file=sys.stderr)
        sys.exit(1)

    client = ElevenLabs(api_key=api_key)
    system_prompt = _load_system_prompt()
    first_message = _load_first_message()
    conversation_config = _build_conversation_config(system_prompt, first_message, args.llm)
    platform_settings = _build_platform_settings()

    print("---")
    print(f"Agent name:    {AGENT_NAME}")
    print(f"LLM:           {args.llm}")
    print(f"max_tokens:    {MAX_TOKENS}")
    print(f"ASR:           {ASR_PROVIDER}")
    print(f"TTS:           {TTS_MODEL} (voice_id={VOICE_ID_EN})")
    print("Tool mode:     client tools (run in browser via @elevenlabs/react)")
    print(f"System prompt: {len(system_prompt):,} chars")
    print(f"First message: {first_message!r}")
    print("---")

    if args.update:
        agent_id = os.environ.get("NEXT_PUBLIC_AGENT_ID")
        if not agent_id:
            print("--update requires NEXT_PUBLIC_AGENT_ID in .env.local", file=sys.stderr)
            sys.exit(1)
        print(f"Updating agent {agent_id}...")
        _patch_agent(
            api_key,
            agent_id,
            {
                "name": AGENT_NAME,
                "conversation_config": _strip_built_in_tools(conversation_config),
                "platform_settings": platform_settings,
            },
        )
        _patch_agent(
            api_key,
            agent_id,
            {
                "conversation_config": {
                    "agent": {
                        "prompt": {
                            "built_in_tools": conversation_config["agent"]["prompt"]["built_in_tools"]
                        }
                    }
                }
            },
        )
        wanted = [t["name"] for t in conversation_config["agent"]["prompt"]["tools"]]
        _sync_tool_ids_by_name(api_key, agent_id, wanted)
        print(f"\nOK updated. Agent ID: {agent_id}")
        return

    print("Creating agent...")
    agent = client.conversational_ai.agents.create(
        name=AGENT_NAME,
        conversation_config=conversation_config,
        platform_settings=platform_settings,
        tags=AGENT_TAGS,
    )

    agent_id = getattr(agent, "agent_id", None) or getattr(agent, "id", None)
    if not agent_id:
        print(f"Agent created but response missing agent_id: {agent}", file=sys.stderr)
        sys.exit(1)

    print(f"\nOK created. Agent ID: {agent_id}")
    _persist_agent_id(agent_id)
    wanted = [t["name"] for t in conversation_config["agent"]["prompt"]["tools"]]
    _sync_tool_ids_by_name(api_key, agent_id, wanted)

    print("\nNext steps:")
    print("  1. python -m tools.upload_kb")
    print("  2. uvicorn api.index:app --reload --port 8002")
    print("  3. Wire the @elevenlabs/react widget with NEXT_PUBLIC_AGENT_ID and the 7 client tools.")


if __name__ == "__main__":
    try:
        main()
    except Exception as err:
        print(f"\nSetup failed: {err}", file=sys.stderr)
        raise
