# AfterCare

AfterCare turns **medical documents** (PDF or plain text) into a **readable patient summary** and answers **follow-up questions** by combining **retrieval from your upload**, **optional web snippets**, and **general medical context** from the chat model.

This repository is an **MVP slice**: upload → structured extraction (LLM) → in-memory indexing → RAG Q&A. There is **no database**, **no authentication**, and **no voice** features yet.

---

## Features

- **Upload** PDF or TXT (drag-and-drop or file picker).
- **Structured extraction** via [Mistral AI](https://console.mistral.ai/): patient info, diagnoses, medications, tests, follow-up, red flags, and doctor instructions (structured data rendered as summary cards — not raw JSON in the UI).
- **RAG Q&A** after upload: see [RAG & retrieval](#rag--retrieval) below.
- **Optional web context**: short [DuckDuckGo Instant Answer](https://duckduckgo.com/api) JSON snippets merged into the Q&A prompt when available (`AFTERCARE_WEB_LOOKUP`, on by default; legacy `MEDECHO_WEB_LOOKUP` still honored).
- **Assistant replies** rendered as **Markdown** in the UI (`react-markdown` + Tailwind Typography).
- **Sample document** card for demo formatting.

---

## Architecture (high level)

```text
┌─────────────┐     multipart      ┌──────────────────────────────────────────┐
│  Next.js    │ ────────────────► │ FastAPI                                   │
│  (browser)  │ ◄──────────────── │  • PyMuPDF / TXT → raw text               │
└─────────────┘   JSON responses  │  • Mistral chat → structured JSON         │
                                   │  • Chunk + Mistral embed → vectors        │
                                   │  • In-memory session (session_id)         │
                                   │  • Q&A: retrieve + DDG? + Mistral chat    │
                                   └──────────────────────────────────────────┘
```

- **Frontend** (`frontend/`): calls `POST /upload-and-extract` and `POST /sessions/{id}/ask` (see `lib/api.ts`; default API base `http://localhost:8000`).
- **Backend** (`backend/`): all Mistral traffic uses the official **`mistralai`** Python SDK (v1.x, Python 3.9+).

---

## Data storage (no database)

| Aspect | Implementation |
|--------|----------------|
| **Database** | **None.** No Postgres, SQLite, Redis, or vector DB. |
| **Sessions** | Python **`OrderedDict`** + `threading.Lock` in `session_store.py`. |
| **Capacity** | Up to **200** sessions; oldest evicted (FIFO) when the limit is exceeded. |
| **Lifetime** | **Process memory only.** Restarting Uvicorn **drops all sessions** and `session_id` values become invalid. |
| **Per session** | `session_id`, `filename`, full **`raw_text`**, text **`chunks`**, **`chunk_embeddings`** (float vectors), and the structured **`extracted`** dict. |

For production you would typically add a database (metadata), object storage (original PDFs), and a vector store or managed retrieval service — not implemented here.

---

## LLMs & models (Mistral)

All calls use **`MISTRAL_API_KEY`** (La Plateforme). Override models with environment variables.

| Step | Module | What runs | Default model | Notes |
|------|--------|-----------|---------------|--------|
| **Structured extraction** | `llm.py` | Chat completion with **`response_format: json_object`** | `MISTRAL_MODEL` → **`mistral-small-latest`** | Strict JSON schema merge for patient/meds/tests/etc. |
| **Embeddings (indexing)** | `rag.py` | `client.embeddings.create` in batches of 32 | `MISTRAL_EMBED_MODEL` → **`mistral-embed`** | One vector per text chunk; cosine similarity at query time. |
| **Q&A answer** | `rag.py` | Chat completion (no JSON mode); long system prompt + user question | Same as **`MISTRAL_MODEL`** | Temperature ~`0.3`, higher `max_tokens` for long blended answers. |

**SDK:** `mistralai>=1.9,<2` (see `backend/requirements.txt`). Older Python 3.9 is supported; Mistral’s **v2** SDK requires Python 3.10+.

---

## RAG & retrieval

### Indexing (runs once per successful upload, after extraction)

1. **Structured summary chunk** — Plain text built from the extracted JSON (`extracted_to_summary_chunk` in `rag.py`), always included so retrieval can hit high-level facts even if raw OCR is noisy.
2. **Document chunks** — Raw text split on paragraph boundaries, target **~1100 characters** per chunk with **~160** overlap (`chunk_document`).
3. **Embeddings** — Each chunk embedded with **`mistral-embed`**; vectors stored on the in-memory session next to the chunk text.

### Query-time (each `POST .../ask`)

1. **Embed the user question** with the same embedding model.
2. **Cosine similarity** between the question vector and every chunk vector (`rag.py`).
3. **Top‑k chunks** (default **6**) concatenated into the system prompt as “document excerpts”.
4. **Optional web snippet** — `web_context.py` calls DuckDuckGo’s **`api.duckduckgo.com`** (JSON); if `Abstract` / `Answer` / `Definition` exist, they are appended for the model to treat as **third-party, verify-before-trusting** context. Disable with `AFTERCARE_WEB_LOOKUP=0` (or legacy `MEDECHO_WEB_LOOKUP=0`).
5. **Chat completion** — System instructions tell the model to combine **(1) document excerpts**, **(2) web snippet if any**, and **(3) general medical knowledge**, with clear headings (Markdown) for the UI.

There is **no re-ranking**, **no hybrid BM25**, and **no citation offsets** back into the PDF — this is intentionally simple.

---

## Tech stack

| Layer | Stack |
|--------|--------|
| Frontend | Next.js 14 (App Router), React 18, TypeScript, Tailwind CSS, **react-markdown**, **remark-gfm**, **@tailwindcss/typography** |
| Backend | FastAPI, Pydantic, **httpx** (web lookup), **python-multipart** |
| PDF text | PyMuPDF (`fitz`) |
| LLM / embeddings | Mistral (`mistralai` v1.x) — chat + embeddings |

---

## Project layout

```
aftercare/
├── README.md
├── backend/
│   ├── main.py              # FastAPI routes, CORS, orchestration
│   ├── requirements.txt
│   ├── document_parser.py   # PDF (PyMuPDF) + TXT extraction
│   ├── llm.py               # Mistral JSON extraction (chat)
│   ├── rag.py               # Chunking, embeddings, retrieval, Q&A chat
│   ├── session_store.py     # In-memory sessions (no DB)
│   └── web_context.py       # DuckDuckGo instant-answer helper
└── frontend/
    ├── app/                 # Next.js app router
    ├── components/          # UploadPanel, SampleDocument, DocumentSummary, QuestionAnswer
    └── lib/api.ts           # API client (`API_BASE` → backend)
```

---

## Prerequisites

- **Python** 3.9+ (this repo pins `mistralai>=1.9,<2` for 3.9; Mistral SDK v2 needs 3.10+).
- **Node.js** 18.17+ (Next.js 14).

---

## Environment variables (backend)

| Variable | Required | Description |
|----------|----------|-------------|
| `MISTRAL_API_KEY` | **Yes** | API key from [Mistral La Plateforme](https://console.mistral.ai/). |
| `MISTRAL_MODEL` | No | Chat model for **JSON extraction** and **Q&A** (default: `mistral-small-latest`). |
| `MISTRAL_EMBED_MODEL` | No | Embedding model for **RAG indexing / query** (default: `mistral-embed`). |
| `AFTERCARE_WEB_LOOKUP` | No | Set to `0` / `false` / `off` to **disable** DuckDuckGo instant-answer snippets (default: enabled). Legacy: `MEDECHO_WEB_LOOKUP` is read if `AFTERCARE_WEB_LOOKUP` is unset. |

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

Run commands from the **`frontend/`** directory so Tailwind scans the right paths (`tailwind.config.mjs` anchors `content` to this folder).

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
| `POST` | `/upload-and-extract` | Multipart field **`file`** (`.pdf` or `.txt`). Runs extraction + embedding index; returns **`session_id`**, **`filename`**, **`extracted`**. |
| `POST` | `/sessions/{session_id}/ask` | JSON `{ "question": "..." }` → `{ "answer": "..." }` (Markdown string). |

**Sessions:** in-memory only; max **200**; **restart clears everything**.

---

## CORS

The backend uses permissive CORS for local dev (`allow_origins=["*"]`, `allow_credentials=False`). **Tighten before production** (explicit origins, credentials as needed).

---

## Build frontend for production

```bash
cd frontend
npm run build
npm start
```

---

## Medical disclaimer

AfterCare is a **demonstration tool**. It does not replace licensed medical care. Model and web snippets can be wrong or outdated. Always follow your clinician and pharmacist, and use emergency services when appropriate.

---

## Publishing to GitHub

### Option A — GitHub CLI (recommended)

```bash
brew install gh          # if `gh` is not installed
gh auth login            # browser or token; one-time per machine
cd /path/to/aftercare
gh repo create aftercare --public --source=. --remote=origin --push
```

If `origin` already exists:

```bash
gh repo create aftercare --public --source=. --push
```

Use `--private` instead of `--public` for a private repository.

### Option B — Create the repo in the browser

1. Open [github.com/new](https://github.com/new), name the repository (e.g. `aftercare`), leave “Initialize” unchecked.
2. Point `origin` at your new URL (replace `YOUR_USER` and `REPO`):

   ```bash
   cd /path/to/aftercare
   git remote remove origin 2>/dev/null || true
   git remote add origin https://github.com/YOUR_USER/REPO.git
   git push -u origin main
   ```

For SSH: `git remote add origin git@github.com:YOUR_USER/REPO.git`

---

## License

Add a license file if you open-source this project.
