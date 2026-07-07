# Manipal Virtual Campus Assistant: Developer Setup & Workspace Guide 🤖

Welcome to the unified repository for the **Manipal University Virtual Campus Assistant**. This project is a multi-service platform featuring a Next.js frontend client, a FastAPI gateway API, and two FastAPI AI microservices: a hybrid RAG Chatbot and an adaptive Voice Interview Bot.

---

## 1. Directory Topology

```text
Manipal-Chatbot/
├── frontend/            # Next.js frontend client & user dashboard
├── backend/             # FastAPI gateway API, proxy services, and DB models
├── ai-engine/           # FastAPI AI services:
│   ├── ChatBot/         # pgvector RAG document search and synthesis
│   └── Interview_Bot/   # Resume analyzer & voice mock interviewer (VAPI integration)
├── data-engineering/    # Postgres & MongoDB mock database seeding scripts
├── devops/              # Container services orchestration
├── README.md            # Workspace developer setup (This file)
├── Architecture.md      # System layout & configurations guide
├── Workflow.md          # Execution workflows, functions mapping, & performance analyses
└── Flowchart.md         # Visual Mermaid process flowcharts & module structures
```

---

## 2. Prerequisites & Environment Setup

Before starting, ensure you have the following installed on your machine:
*   **Python:** version `3.11`
*   **Node.js:** version `20` (with `npm`)
*   **PostgreSQL:** Local server or cloud-hosted instance
*   **MongoDB:** Local server or cloud-hosted instance
*   **Supabase:** A cloud project with the `pgvector` extension enabled

---

## 3. Step-by-Step Installation & Execution Guide

### Step 1: Set Up the Next.js Frontend Client
1.  Navigate to the `/frontend` directory:
    ```bash
    cd frontend
    ```
2.  Install dependencies:
    ```bash
    npm install
    ```
3.  Configure variables: Create a `.env` file in the `/frontend` directory containing:
    ```env
    NEXT_PUBLIC_API_URL=http://localhost:8000
    ```
4.  Launch the development server:
    ```bash
    npm run dev
    ```
    The UI is now accessible at `http://localhost:3000`.

### Step 2: Seed the PostgreSQL & MongoDB Databases
1.  Navigate to the `/data-engineering` directory:
    ```bash
    cd data-engineering
    ```
2.  Install seed requirements:
    ```bash
    pip install -r requirements.txt
    ```
3.  Create a `.env` file in the `/data-engineering` directory containing:
    ```env
    POSTGRES_URL=postgresql://postgres:password@localhost:5432/manipal_db
    MONGODB_URI=mongodb://localhost:27017/manipal_chatbot
    ```
4.  Run the seeding scripts:
    ```bash
    python 01_postgres_seed.py
    python 02_mongo_seed.py
    ```

### Step 3: Set Up and Run the Gateway Backend
1.  Navigate to the `/backend` directory:
    ```bash
    cd backend
    ```
2.  Install gateway packages:
    ```bash
    pip install -r requirements.txt
    ```
3.  Configure variables: Create a `.env` file in the `/backend` directory containing:
    ```env
    GROQ_API_KEY=gsk_your_groq_api_key
    POSTGRES_URL=postgresql://postgres:password@localhost:5432/manipal_db
    MONGODB_URI=mongodb://localhost:27017/manipal_chatbot
    AI_ENGINE_URL=http://localhost:8001
    ```
4.  Run the API Gateway:
    ```bash
    python -m uvicorn main:app --reload --port 8000
    ```
    The API docs will be available at `http://localhost:8000/docs`.

### Step 4: Set Up and Run the AI Engine Microservices

#### Option A: RAG Chatbot Service
1.  Navigate to `/ai-engine/ChatBot`:
    ```bash
    cd ai-engine/ChatBot
    ```
2.  Install packages:
    ```bash
    pip install -r requirements.txt
    ```
3.  Create a `.env` file in the `/ai-engine/ChatBot` directory:
    ```env
    SUPABASE_URL=https://your-project-id.supabase.co
    SUPABASE_ANON_KEY=your-anon-public-key
    SUPABASE_SERVICE_KEY=your-service-role-private-key
    GROQ_API_KEY=gsk_your_groq_api_key
    CHATBOT_ALLOWED_ORIGINS=*
    ```
4.  (Optional) Seed Supabase with local context files:
    ```bash
    python ingest.py
    ```
5.  Launch the RAG Chatbot server:
    ```bash
    python -m uvicorn main:app --reload --port 8001
    ```

#### Option B: AI Interview Bot Service
1.  Navigate to `/ai-engine/Interview_Bot`:
    ```bash
    cd ai-engine/Interview_Bot
    ```
2.  Install packages:
    ```bash
    pip install -r requirements.txt
    ```
3.  Create a `.env` file in the `/ai-engine/Interview_Bot` directory:
    ```env
    GROQ_API_KEY=gsk_your_groq_api_key
    SUPABASE_URL=https://your-project-id.supabase.co
    SUPABASE_KEY=your-supabase-key
    VAPI_PRIVATE_KEY=your-vapi-private-key
    VAPI_PUBLIC_KEY=your-vapi-public-key
    VAPI_ASSISTANT_ID=your-vapi-assistant-id
    ```
4.  Launch the Interview Bot server:
    ```bash
    python -m uvicorn main:app --reload --port 8002
    ```

---

## 4. Generated Output Files & Formats

When running, the system generates the following local and cloud-based outputs:

### 1. In-Memory and Local Output Files
*   `/backend/latest_resume.txt`: Extracted plain-text transcription of the latest uploaded PDF, used to feed downstream LLM streams.
*   `/backend/latest_score.json`: A JSON cache file capturing the ATS evaluation output (score, strengths, weaknesses).
*   `/ai-engine/Interview_Bot/storage/resumes/{session_key}.pdf`: Stores copy uploads of candidate resume PDF files.
*   `/ai-engine/Interview_Bot/storage/transcripts/{call_id}.json`: Local transcript dumps saved when running local file mode interviews.

### 2. Cloud Database Records (Supabase)
*   `mit_bengaluru_data` (Table): Unified store holding 384D float embeddings (`embedding` column) and text metadata.
*   `chatbot-assets` (Storage Bucket): Public bucket containing copy uploads of raw ingested campus files.
*   `resumes` (Table): Maps a candidate's `user_id` to their extracted resume string context.
*   `evaluations` (Table): Captures step-by-step scores (0-10) and feedback for each question during voice interviews.
*   `interview_summary` (Table): Tracks overall scores (0-100), communication levels, problem-solving, weaknesses, and skill profile maps.

---

## 5. Troubleshooting & Common Errors

*   **Error: `ModuleNotFoundError: No module named 'supabase'`**
    *   *Cause:* The packages inside `requirements.txt` are not installed or the virtual environment is inactive.
    *   *Fix:* Run `pip install -r requirements.txt` inside the corresponding folder.
*   **Error: `RuntimeError: SUPABASE_URL and SUPABASE_KEY must be configured.`**
    *   *Cause:* The environment file `.env` is missing or is placed in the wrong folder.
    *   *Fix:* Copy the values from `.env.example`, fill in valid keys, and name the file `.env` in the target service root.
*   **Error: `upstream_status = e.response.status_code (FastAPI HTTP 502/503)`**
    *   *Cause:* The backend Gateway cannot communicate with the AI Engine (port 8001 is offline or misconfigured).
    *   *Fix:* Verify that the AI Engine is running and check that the `AI_ENGINE_URL` parameter in `/backend/.env` matches the port.
*   **Error: `match_chunks does not exist (FastAPI HTTP 500)`**
    *   *Cause:* The Supabase project does not contain the required vector function.
    *   *Fix:* Open the Supabase SQL Editor and run the matching procedure SQL script (see details in [Architecture.md](Architecture.md)).
