# MedEcho

MedEcho turns **medical documents** (PDF or plain text) into a **readable patient summary** and answers **follow-up questions** using retrieval over the document plus optional general medical context.

This repository is an **MVP slice**: upload → structured extraction (LLM) → in-memory RAG Q&A. There is **no database**, **no authentication**, and **no voice** features yet.

---

## Features

- **Upload** PDF or TXT (drag-and-drop or file picker).
- **Structured extraction** via [Mistral AI](https://console.mistral.ai/): patient info, diagnoses, medications, tests, follow-up, red flags, and doctor instructions (stored as structured data, not shown as raw JSON in the UI).
- **User-facing summary** cards on the web app (no JSON dump).
- **RAG Q&A** after upload: embeddings over document chunks + a plain-text “structured summary” chunk; answers **start from the document**, then may add a clearly labeled **“General medical context (not from your document)”** section when the file does not cover the question.
- **Sample document** card in the UI for demo formatting.

---

## Tech stack

| Layer | Stack |
|--------|--------|
| Frontend | Next.js 14 (App Router), React 18, TypeScript, Tailwind CSS |
| Backend | FastAPI, Python |
| PDF text | PyMuPDF (`fitz`) |
| LLM / embeddings | Mistral official Python SDK (`mistralai` v1.x) — chat + `mistral-embed` |

---

## Project layout

```
medecho/
├── README.md
├── backend/
│   ├── main.py              # FastAPI app, routes, CORS
│   ├── requirements.txt
│   ├── document_parser.py   # PDF (PyMuPDF) + TXT extraction
│   ├── llm.py               # Mistral JSON extraction
│   ├── rag.py               # Chunking, embeddings, RAG answers
│   └── session_store.py     # In-memory sessions (no DB)
└── frontend/
    ├── app/                 # Next.js app router
    ├── components/        # UploadPanel, SampleDocument, DocumentSummary, QuestionAnswer
    └── lib/api.ts         # API client
```

---

## Prerequisites

- **Python** 3.9+ (Mistral SDK v2 requires 3.10+; this project pins `mistralai>=1.9,<2` for 3.9 compatibility).
- **Node.js** 18+ (for Next.js).

---

## Environment variables (backend)

| Variable | Required | Description |
|----------|----------|-------------|
| `MISTRAL_API_KEY` | **Yes** | API key from [Mistral La Plateforme](https://console.mistral.ai/). |
| `MISTRAL_MODEL` | No | Chat model for extraction + Q&A (default: `mistral-small-latest`). |
| `MISTRAL_EMBED_MODEL` | No | Embedding model for RAG (default: `mistral-embed`). |

Do not commit API keys. Use `export` in your shell or a local `.env` file that is gitignored (load manually or add `python-dotenv` if you prefer).

---

## Run locally

### 1. Backend (port 8000)

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
export MISTRAL_API_KEY="your-key-here"
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Health check: `GET http://localhost:8000/health`

### 2. Frontend (port 3000)

Requires **Node.js 18.17+** (Next.js 14). Run commands from the **`frontend/`** directory so Tailwind picks up your source files:

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:3000** (or the port Next prints, e.g. 3001 if 3000 is busy). The UI calls the API at **http://localhost:8000** (see `frontend/lib/api.ts`). Change `API_BASE` there if your backend runs elsewhere.

---

## API overview

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Liveness check. |
| `POST` | `/upload-and-extract` | Multipart form field **`file`**. Accepts `.pdf` or `.txt`. Returns `session_id`, `filename`, and `extracted` (structured object for the UI). Indexes the document in memory for Q&A. |
| `POST` | `/sessions/{session_id}/ask` | JSON body: `{ "question": "..." }`. Returns `{ "answer": "..." }`. |

Sessions are **in-memory only** (max 200, FIFO eviction). **Restarting the backend clears all sessions.**

---

## CORS

The backend enables permissive CORS for local development (`allow_origins=["*"]`, `allow_credentials=False`). **Tighten this before production** (specific origins, credentials policy as needed).

---

## Build frontend for production

```bash
cd frontend
npm run build
npm start
```

---

## Medical disclaimer

MedEcho is a **demonstration tool**. It does not provide medical advice, diagnosis, or treatment. Output may be incomplete or wrong. Always follow instructions from your licensed clinician and pharmacist, and seek urgent or emergency care when appropriate.

---

## Publishing to GitHub

This repo is initialized with `main` and an initial commit. To create the GitHub repository and push (pick one path).

### Option A — GitHub CLI (recommended)

```bash
brew install gh          # if `gh` is not installed
gh auth login            # browser or token; one-time per machine
cd /path/to/medecho
gh repo create medecho --public --source=. --remote=origin --push
```

If `origin` already exists (for example from a manual add), use:

```bash
gh repo create medecho --public --source=. --push
```

Use `--private` instead of `--public` if you prefer a private repository.

### Option B — Create the repo in the browser

1. Open [github.com/new](https://github.com/new), name the repository (e.g. `medecho`), leave “Initialize” unchecked.
2. Point `origin` at your new URL (replace `YOUR_USER` and `REPO`):

   ```bash
   cd /path/to/medecho
   git remote remove origin 2>/dev/null || true
   git remote add origin https://github.com/YOUR_USER/REPO.git
   git push -u origin main
   ```

For SSH: `git remote add origin git@github.com:YOUR_USER/REPO.git`

---

## License

Add a license file if you open-source this project.
