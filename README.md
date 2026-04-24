# Aftercare

**A post-discharge assistant that turns hospital paperwork into grounded answers and voice-based follow-up support.**

Built for the **UMD x Claude hackathon on April 24, 2026**.

Aftercare helps patients understand what to do after leaving the hospital: which medicines to take, what symptoms to watch for, when to follow up, and when to escalate to a clinician. The prototype has two hackathon-ready parts:

- **Document intelligence:** upload a discharge PDF or TXT file, extract the care plan, and ask questions grounded in the document, optional web snippets, and clearly labeled general medical context.
- **Voice aftercare:** talk to Aria, a standalone ElevenLabs post-discharge voice copilot backed by a fictional discharge bundle and safety-first tool calls.

The two parts are intentionally separate in this 1.5 hour build. The intended product path is straightforward: the document extraction output becomes the personal data layer for the voice agent.

## Demo Story

Maria Santos has just been discharged after a heart-failure flare-up. Her medication schedule changed, her INR needs monitoring, and her paperwork includes red-flag symptoms. The next day she needs answers quickly, without rereading a packet.

Try questions like:

- "What medicines do I take tonight?"
- "Can I take Advil with my warfarin?"
- "I forgot my morning water pill. What now?"
- "My INR was 3.8. Is that okay?"
- "I'm having chest pain right now."

Aftercare is designed to answer from the discharge plan when it can, explain context when helpful, and escalate when it should.

## Why This Matters

Discharge is one of the riskiest transitions in care. Patients leave with dense instructions, medication changes, follow-up appointments, and warning signs that are easy to miss. A useful aftercare assistant needs to be:

- **Grounded:** patient-specific answers start from the uploaded discharge document or patient bundle.
- **Conservative:** the assistant does not invent diagnoses, dosages, or medication changes.
- **Actionable:** patients get plain-language next steps instead of raw clinical text.
- **Escalation-aware:** red flags, off-bundle questions, and unsafe medication questions route to a clinician handoff.

## What Works Today

| Area | Status |
| --- | --- |
| Upload PDF or TXT discharge documents | Working |
| Extract structured care-plan fields | Working |
| Show readable summary cards | Working |
| Ask document-grounded questions | Working |
| Blend optional web snippets into Q&A | Working |
| Render assistant answers as Markdown | Working |
| Standalone aftercare voice agent | Working prototype |
| Medication, labs, follow-up, red-flag voice tools | Working prototype |
| Dynamic connection between uploaded document and voice agent | Future integration |

## Architecture

```text
                 Part 1: Document Intelligence

Patient discharge PDF/TXT
        |
        v
Text extraction + structured extraction
        |
        v
In-memory retrieval index
        |
        +--> Web Q&A grounded in the uploaded document
        |
        +--> Optional web instant summary for extra context


                 Part 2: Voice Aftercare

Fictional discharge bundle
        |
        v
FastAPI tool server on port 8002
        |
        v
ElevenLabs voice agent, "Aria"
        |
        v
Medication help, lab explanations, adherence logging, escalation


                 Next Step

Use Part 1 extraction output as the live patient bundle for Part 2.
```

## Repository Map

```text
.
├── backend/                  FastAPI extraction, RAG, web-context API
├── frontend/                 Next.js app for upload, summary, and Q&A
├── aftercare_voice_agent/    Standalone ElevenLabs voice-agent prototype
│   ├── agent/                Prompt, first message, voice notes, knowledge bundle
│   ├── api/                  Local tool server for Aria
│   ├── tools/                Agent setup and knowledge-base upload scripts
│   └── expected_flows.md     Demo runbook and safety checks
└── README.md
```

## Tech Stack

| Layer | Stack |
| --- | --- |
| Frontend | Next.js 14, React 18, TypeScript, Tailwind CSS, `react-markdown`, `remark-gfm`, Tailwind Typography |
| Backend | FastAPI, Pydantic, `python-multipart`, `httpx` |
| PDF parsing | PyMuPDF |
| LLM and embeddings | Mistral SDK v1.x, `mistral-embed` |
| Voice agent | ElevenLabs Conversational AI |
| State | In-memory sessions for the hackathon demo |

## Document RAG Details

When a file is uploaded:

1. The backend extracts raw text from PDF or TXT.
2. Mistral extracts structured JSON: patient info, diagnoses, medications, tests, follow-up, red flags, and doctor instructions.
3. The backend builds a plain-language structured summary chunk.
4. Raw text is chunked into overlapping passages.
5. Each chunk is embedded with `mistral-embed`.
6. The session is stored in memory with a `session_id`.

When the patient asks a question:

1. The question is embedded.
2. Cosine similarity retrieves the top document chunks.
3. Optional DuckDuckGo Instant Answer context is added when available.
4. Mistral writes a Markdown answer with document-grounded sections and clearly labeled general context.

There is no database, no vector DB, and no authentication in this MVP. Sessions live in process memory and disappear when the backend restarts.

## Environment

Backend variables:

| Variable | Required | Description |
| --- | --- | --- |
| `MISTRAL_API_KEY` | Yes | Mistral API key for extraction, embeddings, and Q&A. |
| `MISTRAL_MODEL` | No | Chat model for extraction and Q&A. Defaults to `mistral-small-latest`. |
| `MISTRAL_EMBED_MODEL` | No | Embedding model. Defaults to `mistral-embed`. |
| `AFTERCARE_WEB_LOOKUP` | No | Set to `0`, `false`, or `off` to disable web snippets. |

Voice-agent variables:

| Variable | Required | Description |
| --- | --- | --- |
| `ELEVENLABS_API_KEY` | Yes | ElevenLabs API key for creating/updating Aria. |
| `ELEVENLABS_VOICE_ID_EN` | No | Optional voice override. |
| `AFTERCARE_API_PORT` | No | Defaults to `8002`. |

Do not commit real API keys. Use local `.env` files only.

## Run Part 1: Document App

Start the backend:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export MISTRAL_API_KEY="your-key-here"
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Start the frontend:

```bash
cd frontend
npm install
npm run dev
```

Open:

```text
http://localhost:3000
```

## Run Part 2: Voice Agent

Start the Aftercare voice-agent backend:

```bash
cd aftercare_voice_agent
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Add your ElevenLabs API key to `.env`:

```bash
ELEVENLABS_API_KEY=your-key-here
```

Create or update Aria:

```bash
python -m tools.setup_agent
```

Run the tool server:

```bash
uvicorn api.index:app --reload --port 8002
```

Useful endpoints:

- `GET http://localhost:8002/health`
- `GET http://localhost:8002/ledger`

The voice-agent details and demo flow live in [aftercare_voice_agent/README.md](aftercare_voice_agent/README.md).

## Safety Design

Aftercare is intentionally conservative:

- The document app separates patient-specific document facts from general medical context.
- Optional web snippets are treated as third-party orientation, not patient-specific truth.
- The voice agent uses tools for medications, labs, adherence, follow-up, and escalation.
- Aria does not change the care plan, diagnose, or invent missing instructions.
- Chest pain, severe shortness of breath, bleeding, confusion, falls, suspected overdose, and off-bundle medication questions trigger escalation paths.

## Hackathon Scope

Completed:

- Discharge document upload and extraction.
- Structured patient summary UI.
- In-memory RAG over uploaded documents.
- Optional web-context augmentation.
- Markdown-rendered assistant answers.
- Standalone ElevenLabs voice-agent prototype.
- Mock discharge bundle for realistic aftercare flows.
- Safety-first prompt and tool definitions.
- Demo runbook for medication interaction, missed dose, lab explanation, follow-up, and critical escalation.

Future work:

- Connect uploaded document sessions directly to Aria.
- Persist patient sessions and adherence logs.
- Add EHR/FHIR ingestion.
- Replace mock escalation with real clinician paging, SMS, or care-team task creation.
- Add authentication and production-grade privacy controls.

## Disclaimer

Aftercare is a demonstration prototype. It does not provide medical advice, diagnosis, or treatment. Outputs may be incomplete or wrong. Patients should follow instructions from licensed clinicians and seek urgent or emergency care when appropriate.
