# System Architecture Document 🏗️

Welcome to the **Manipal University Campus Assistant** system architecture guide. This document provides a developer-focused, deep-dive analysis of the system topography, codebase directory structures, module communications, API gateways, databases, and configuration settings.

---

## 1. High-Level System Topography

The Manipal Campus Assistant is structured as a **decoupled, multi-service platform** consisting of a React-based Next.js frontend, a FastAPI gateway backend, and two AI processing engines (the RAG Chatbot and the Voice Interview Bot), supported by Supabase, MongoDB, PostgreSQL, and Groq cloud services.

```mermaid
graph TD
    %% Clients
    User([End User / Candidate]) <--> |HTTP / WebRTC| Frontend[Next.js Frontend]
    
    %% API Gateway
    Frontend <--> |HTTP / API Proxy| Gateway[FastAPI Backend Gateway]
    
    %% AI Engines
    Gateway <--> |Proxy Chat| ChatbotEngine[ChatBot FastAPI Engine]
    Frontend <--> |VAPI / WebRTC Voice| VapiServer[VAPI Voice Platform]
    VapiServer <--> |Webhook Transcripts| InterviewEngine[Interview Bot FastAPI Engine]
    
    %% Data / DB Services
    ChatbotEngine <--> |pgvector Match / Assets| Supabase[(Supabase DB & Storage)]
    InterviewEngine <--> |CRUD Resumes / Evaluations| Supabase
    Gateway <--> |Read / Write Analytics| Postgres[(PostgreSQL DB)]
    Gateway <--> |Read / Write Questions| MongoDB[(MongoDB DB)]
    
    %% AI Inference
    ChatbotEngine <--> |all-MiniLM-L6-v2| LocalEmbedding[SentenceTransformer CPU]
    ChatbotEngine <--> |RAG Inference| GroqAPI[Groq API Llama-3.1-8B]
    InterviewEngine <--> |Resume Analysis & Eval| GroqAPI
    VapiServer <--> |Groq Voice Inference| GroqAPI
```

---

## 2. Directory and File Purpose

Below is an exhaustive description of every major directory and key file across the workspace.

### Workspace Root
*   [README.md](file:///c:/Users/ruhan/OneDrive/Desktop/Manipal-Chatbot/README.md): Master workspace guide containing quick setup, team contribution guides, and branch policies.
*   [Architecture.md](file:///c:/Users/ruhan/OneDrive/Desktop/Manipal-Chatbot/Architecture.md): This architectural design and configuration document.
*   [Workflow.md](file:///c:/Users/ruhan/OneDrive/Desktop/Manipal-Chatbot/Workflow.md): Pipeline execution tracing, data flow models, and runtime walkthroughs.
*   [Flowchart.md](file:///c:/Users/ruhan/OneDrive/Desktop/Manipal-Chatbot/Flowchart.md): Visual Mermaid diagrams showing execution flowcharts, dependency trees, and data structures.
*   `.env.example`: A global template listing environment variable placeholders across backend and AI services.

### Frontend Component (`/frontend`)
The Next.js user interface representing the student dashboard, placement statistics, and live virtual assistant.
*   `package.json`: Manages dependencies (Next.js 16.2, React 19, TailwindCSS 3.4, TypeScript).
*   `tsconfig.json` & `next.config.ts`: Configuration settings for TypeScript compilation and Next.js compiler behaviors.
*   `src/app/layout.tsx`: Root HTML layout setting up the Poppins font, page header, navigations, and global `ChatProvider` wrapper.
*   `src/app/(chat)/page.tsx`: Core interface containing welcome suggestions, typing indicators, scroll positioning, and message bubble streams.
*   `src/app/placement/`: Placement hub view containing:
    *   `page.tsx`: Dashboard displaying calendar notifications and upcoming recruitment activities.
    *   `data.ts`: Mock schedule records (Microsoft, McKinsey, etc.).
    *   `question-bank/page.tsx`: List of technical interview questions filtered by company and domain.
*   `src/context/ChatContext.tsx`: Manages active chat session state, local storage persistence, off-line fallbacks, and API calls to the Gateway.
*   `src/components/`: Reusable UI modules:
    *   `ChatInput.tsx`: Floating input bar containing option toggles (RAG Chat, Resume analysis, Voice Interview).
    *   `MarkdownRenderer.tsx`: Custom component for rendering mathematical symbols, code listings, lists, and bold text elements in assistant bubbles.

### Backend Component (`/backend`)
Acts as the **API Gateway** between the frontend client and the AI engines, and manages operational databases (PostgreSQL/MongoDB).
*   `main.py`: Entry point for the Gateway API. Initializes FastAPI, CORS policies, slowapi rate-limiting, handles exception handlings, and registers routers.
*   `config.py`: Manages central application settings and loads secrets from `.env` using Pydantic.
*   `database.py`: Establishes SQLAlchemy connection engines and session sessions for PostgreSQL.
*   `app/routers/`: Gateway route definitions:
    *   `chat.py`: Proxies `/api/chat` requests directly to the AI Engine ChatBot microservice.
    *   `upload.py`: Accepts resume PDFs, extracts text via `pdfplumber`, saves state, and runs Groq resume analysis.
    *   `audio_stream.py`: Streams structured ATS resume analysis text back to the client using Server-Sent Events (SSE).
    *   `mock_endpoints.py`: Exposes mock endpoints for placement stats and chatbot fallbacks.
*   `app/services/file_handler.py`: Utility managing local storage writes for uploaded candidate resume PDFs.
*   `requirements.txt`: Gateway dependencies including `fastapi`, `slowapi`, `pdfplumber`, `sqlalchemy`, and `groq`.

### AI Engine Component (`/ai-engine`)
Houses the main intelligence layers of the platform, divided into two FastAPI microservices.
*   `judge0_runner.py`: A utility script interacting with the Judge0 remote execution compiler API, running user code submissions against custom input/output test cases.
*   **ChatBot/ Sub-Engine:**
    *   `main.py`: A 2900-line server containing multi-tier hybrid vector retrieval logic, Decorum Safety Filter guards, query caches, and Groq-orchestrated response generation.
    *   `ingest.py`: Core ingestion pipeline. Scans local folders for `.pdf`, `.json`, `.docx`, `.txt`, `.csv`, `.xlsx`, and `.db` files, chunks contents, embeds them using SentenceTransformers, and uploads to Supabase Storage and Database.
    *   `dataset.json`: A local JSON database containing FAQs and administrative documents for local ingestion.
*   **Interview_Bot/ Sub-Engine:**
    *   `main.py`: Entry server registering routers.
    *   `routers/resume.py`: Uploads PDF resumes and triggers resume-aware profile categorization.
    *   `routers/interview.py`: Initiates system prompts, builds adaptive prompts, serves coding problems, and captures voice transcripts.
    *   `routers/evaluation.py`: Retrieves overall candidate scoring summaries and individual question feedbacks.
    *   `services/resume_service.py`: Leverages PyPDF2 and Groq `llama-3.3-70b-versatile` to analyze candidate skills, compare against standard role benchmarks, and generate tailored resume-based questions.
    *   `services/prompt_builder.py`: Compiles the dynamic, detailed VAPI voice interviewer instruction brief.
    *   `services/question_loader.py`: Handles dynamic fallback loading for technical preset and coding questions.
    *   `services/evaluator.py`: Implements deterministic and LLM-powered answer evaluation, skill profile updates, and overall candidate scoring weights.
    *   `services/vapi_service.py`: Outbound request builder for initiating interactive Vapi calls.
    *   `services/supabase_service.py`: Client connection wrapper and DB queries for `resumes`, `preset_questions`, `evaluations`, and `interview_summary`.
    *   `services/session_store.py`: Thread-safe, in-memory global dictionaries managing active session metadata.
    *   `questions.json`: Local fallback database containing preset engineering questions.

### Data Engineering Component (`/data-engineering`)
*   `01_postgres_seed.py`: Seeding script using `Faker` to populate placement history, mock metrics, and user profiles.
*   `02_mongo_seed.py`: Seeding script populating a local MongoDB `question_bank` collection.
*   `requirements.txt`: Driver packages: `psycopg2-binary`, `pymongo`, `pinecone-client`, and `langchain`.

### DevOps Component (`/devops`)
*   `docker-compose.yml`: Multi-container orchestrator composing backend (port 8000) and AI engine (port 8001) services on a common bridge network.

---

## 3. Module Interaction Map

The following description details how these components communicate during runtime operations:

1.  **Frontend to Gateway:** The Next.js frontend calls the Gateway (`/backend`) over standard HTTP requests (`/api/chat` or `/api/upload-resume`).
2.  **Gateway to AI Engine (Chat):** When the frontend requests `/api/chat`, the Gateway parses the message and immediately proxies it to the ChatBot Sub-Engine (`/ai-engine/ChatBot/chat`) using an asynchronous `httpx.AsyncClient` HTTP request.
3.  **VAPI Voice Agent to AI Engine (Interview):** For voice interviews, the user initiates a WebRTC socket directly with VAPI. VAPI triggers `/interview/start` to get the compiled prompt context, and upon call completion, VAPI sends an `end-of-call-report` webhook payload directly to the Interview Bot Sub-Engine (`/ai-engine/Interview_Bot/interview/transcript`).
4.  **AI Engines to Databases:** Both AI engines interact directly with Supabase tables to bypass local disk serialization. Ingestion scripts upload vectors directly to Supabase `mit_bengaluru_data` tables.
5.  **Gateway to local Databases:** The gateway reads mock metrics from Postgres (`placement_metrics` table) and local MongoDB instances (`question_bank` collection) for dashboard visuals.

---

## 4. System Entry Points

*   **Frontend Client:** Runs via Next.js at `http://localhost:3000`. Root landing routes are processed in [layout.tsx](file:///c:/Users/ruhan/OneDrive/Desktop/Manipal-Chatbot/frontend/src/app/layout.tsx).
*   **Gateway Backend:** Runs via Uvicorn on `http://localhost:8000` (or `http://localhost:8000/docs` for API specs). Managed by [main.py](file:///c:/Users/ruhan/OneDrive/Desktop/Manipal-Chatbot/backend/main.py).
*   **RAG Chatbot API:** Runs via Uvicorn on `http://localhost:8000` (when running separately) or customized ports. Target code is in [main.py](file:///c:/Users/ruhan/OneDrive/Desktop/Manipal-Chatbot/ai-engine/ChatBot/main.py).
*   **Interview Bot API:** Runs via Uvicorn on `http://localhost:8000` (within `/ai-engine/Interview_Bot`). Target code is in [main.py](file:///c:/Users/ruhan/OneDrive/Desktop/Manipal-Chatbot/ai-engine/Interview_Bot/main.py).
*   **Ingestion Engine:** Running `python ingest.py` in the `/ai-engine/ChatBot` directory initiates the document parser scans.
*   **Data Seeders:** Execute `python 01_postgres_seed.py` and `python 02_mongo_seed.py` to fill the database structures.

---

## 5. Configuration Variable Guide

The behavior of the platform is driven by environment variables. The table below lists all configurable parameters across the services:

### RAG Chatbot Sub-Engine Configuration (`ai-engine/ChatBot/.env`)

| Variable Name | Purpose | Default / Example Value | Increasing Effect | Decreasing Effect | Recommended Value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `SUPABASE_URL` | Endpoint of Supabase cloud project | `https://xyz.supabase.co` | N/A | N/A | Target Supabase URL |
| `SUPABASE_ANON_KEY` | Public access key for vector retrieval | `eyJhbGc...` | N/A | N/A | Project Anon Key |
| `SUPABASE_SERVICE_KEY`| Service role key for writes/deletes | `eyJhbGc...` | N/A | N/A | Service Key (secret) |
| `GROQ_API_KEY` | Authentication key for Groq API | `gsk_yX9...` | N/A | N/A | Private API Key |
| `CHATBOT_ALLOWED_ORIGINS`| CORS origins whitelist | `*` | More domains allowed | Restricted access | `http://localhost:3000` |

### AI Interview Bot Sub-Engine Configuration (`ai-engine/Interview_Bot/.env`)

| Variable Name | Purpose | Default / Example Value | Increasing Effect | Decreasing Effect | Recommended Value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `GROQ_API_KEY` | Inference auth key for Groq llama model | `gsk_yX9...` | N/A | N/A | Private API Key |
| `SUPABASE_URL` | Endpoint for interview tables DB | `https://xyz.supabase.co` | N/A | N/A | Target Supabase URL |
| `SUPABASE_KEY` | Key for CRUD on resumes & evaluations | `eyJhbGc...` | N/A | N/A | Service Key or Anon Key |
| `VAPI_PRIVATE_KEY` | Auth token for triggering Vapi calls | `vapi_priv...` | N/A | N/A | Private key from Vapi |
| `VAPI_PUBLIC_KEY` | Client token for initiating voice call | `vapi_pub...` | N/A | N/A | Public key from Vapi |
| `VAPI_ASSISTANT_ID` | UUID of VAPI configured voice agent | `uuid-vapi-id` | N/A | N/A | VAPI Assistant ID |

### Gateway Backend Configuration (`backend/.env`)

| Variable Name | Purpose | Default / Example Value | Increasing Effect | Decreasing Effect | Recommended Value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `GROQ_API_KEY` | Authentication for ATS resume scoring | `gsk_yX9...` | N/A | N/A | Private API Key |
| `POSTGRES_URL` | SQL Connection String | `postgresql://user:pass@host:5432/db`| N/A | N/A | Target Database URL |
| `MONGODB_URI` | MongoDB Connection URI | `mongodb://localhost:27107/db` | N/A | N/A | Local or Atlas URI |
| `AI_ENGINE_URL` | Root URL of proxied ChatBot API | `http://localhost:8000` | N/A | N/A | AI service endpoint |

---

> [!CAUTION]
> **Security Warning:** Never commit `.env` files to git repositories. Always ensure `.env` is declared in all `.gitignore` configurations. Only update `.env.example` when adding a new configuration variable to the architecture.
