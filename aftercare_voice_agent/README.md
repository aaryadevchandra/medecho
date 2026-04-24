# Aftercare Voice Agent

Standalone voice-agent prototype for the UMD x Claude hackathon on April 24, 2026.

This folder contains **Aria**, a post-discharge voice copilot that helps a fictional patient understand and follow their discharge plan. It is intentionally separate from the main Aftercare document RAG app for the hackathon build.

## What Aria does

Aria supports post-care questions like:

- "What pills do I take tonight?"
- "Can I take Advil with my warfarin?"
- "I forgot my morning water pill. What now?"
- "My INR was 3.8. Is that okay?"
- "I'm having chest pain right now."

The agent is designed to read from the discharge bundle, not invent clinical advice. When the question is outside the bundle or sounds urgent, it escalates.

## Safety approach

- Ground answers in the patient's discharge bundle.
- Never change a medication plan.
- Never diagnose.
- Escalate red flags immediately.
- Escalate off-bundle questions instead of guessing.
- Treat extra clinician callbacks as acceptable; missed emergencies are not.

## Tool surface

The ElevenLabs agent is configured with seven client tools:

| Tool | Purpose |
| --- | --- |
| `get_medications` | Return medication names, doses, timing, and food rules. |
| `get_medication_detail` | Answer one medication-specific question from the bundle. |
| `log_dose` | Record taken, missed, or skipped doses. |
| `check_adherence` | Summarize today's dose status and next dose. |
| `explain_lab_result` | Explain a lab result from the discharge bundle. |
| `get_followup_plan` | Return follow-up appointments and red flags. |
| `escalate_to_clinician` | Create a mock clinician handoff for unsafe or unclear cases. |

## Folder map

```text
aftercare_voice_agent/
  agent/
    system_prompt.md
    first_message.md
    voice_moments.json
    voices.md
    knowledge_base/
      discharge_summary.md
      prescriptions.md
      lab_results.md
      red_flags.md
  api/
    index.py
    mock_patient.py
    store.py
  tools/
    setup_agent.py
    upload_kb.py
    _config.py
  expected_flows.md
  requirements.txt
```

## Run locally

```bash
cd aftercare_voice_agent
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Add your ElevenLabs key:

```bash
ELEVENLABS_API_KEY=your-key-here
```

Create the agent:

```bash
python -m tools.setup_agent
```

Start the tool server:

```bash
uvicorn api.index:app --reload --port 8002
```

Check:

- `GET http://localhost:8002/health`
- `GET http://localhost:8002/ledger`

## Demo flows

See `expected_flows.md` for the full runbook. The best pitch flows are:

- Medication interaction: "Can I take Advil with my warfarin?"
- Missed dose: "I forgot my water pill this morning."
- Lab explanation: "My INR was 3.8. Is that okay?"
- Critical escalation: "I'm having chest pain right now."

## Integration plan

Today, Aria uses a mocked discharge bundle. Next, the main Aftercare document RAG output should populate the same fields dynamically:

- medications
- tests and lab values
- follow-up instructions
- red flags
- doctor instructions

That makes the voice agent personal to the uploaded discharge packet.
