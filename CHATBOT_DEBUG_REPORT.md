# CHATBOT DEBUG REPORT 🔍

> **Scope:** RAG Chatbot pipeline only (`ai-engine/ChatBot` + `backend`).  
> **Interview Bot, VAPI, and resume analysis are excluded.**  
> **No code was modified during this analysis.**

---

## 1. Chatbot Request Flow (Traced)

```
User types message in browser
   ↓
[frontend] src/context/ChatContext.tsx  →  sendMessage()  (line 119)
   ↓  POST  {message, tool}
[frontend] NEXT_PUBLIC_API_URL/api/chat
   ↓  httpx proxy  
[backend]  backend/app/routers/chat.py  →  chat_endpoint()  (line 11)
   ↓  POST  {question}  
[AI engine] ai-engine/ChatBot/main.py  →  chat()  route  (line 2458)
   ↓
   ├─ Safety filter  (line 2469)
   ├─ Rate limiter  (line 2502)
   ├─ Cache check  (line 2505)
   ├─ MIT-specific routing  (line 2493)
   │     ↓ if MIT-specific
   │   SentenceTransformer embed query  (line 2553)
   │   Supabase RPC match_chunks()  (line 2558)
   │   Keyword fallback search  (line 2638)
   │   Build context  (line 2651)
   │     ↓
   │   Groq llama-3.1-8b-instant  (line 2808)
   │     ↓
   │   return {"answer": ...}  (line 2860)
   └─ if NOT MIT-specific
       Groq general knowledge  (line 2526)
       return {"answer": ...}  (line 2541)
   ↓
[backend] chat_endpoint() extracts data.get("answer")  (line 22)
   ↓  returns  ChatResponse{response: ..., sources: []}
[frontend] sendMessage() extracts rootData.message || rootData.response  (line 171)
   ↓
Message displayed in chat bubble
```

---

## 2. Environment Variables — Classified by Chatbot Relevance

### ✅ Required — Chatbot will NOT work without these

| Variable | Used In | File & Line | Effect if Missing |
|:---|:---|:---|:---|
| `GROQ_API_KEY` | ChatBot engine | `ai-engine/ChatBot/main.py` line 23 | All LLM calls fail silently → returns `GROQ_BUSY_RESPONSE` string |
| `SUPABASE_URL` | ChatBot engine | `ai-engine/ChatBot/main.py` line 236 | `supabase_client` is set to `None`; vector search is skipped entirely |
| `SUPABASE_ANON_KEY` | ChatBot engine | `ai-engine/ChatBot/main.py` line 237–245 | Same as above — no vector retrieval, chatbot answers nothing MIT-specific |
| `NEXT_PUBLIC_API_URL` | Frontend | `frontend/src/context/ChatContext.tsx` line 150 | Defaults to `https://manipal-chatbot.onrender.com`; points to wrong server if backend is running locally |

### ⚠️ Required for Ingestion Only (not for live chatbot queries)

| Variable | Used In | Effect if Missing |
|:---|:---|:---|
| `SUPABASE_SERVICE_KEY` | `ai-engine/ChatBot/ingest.py` line 18 | Cannot write/ingest data; read-only chatbot still works if data is already in Supabase |

### 🔧 Optional — Chatbot works without these but behaviour changes

| Variable | Used In | File & Line | Default | Effect if Missing |
|:---|:---|:---|:---|:---|
| `CHATBOT_ALLOWED_ORIGINS` | ChatBot engine | `ai-engine/ChatBot/main.py` line 223 | `*` (all origins) | Defaults to open CORS — not a problem for dev |
| `API_KEY` | Backend gateway | `backend/app/middleware/middleware.py` line 15 | `""` (empty = disabled) | No API key enforcement — requests go through freely |

### ❌ Unrelated — Interview Bot only, ignore for chatbot debugging

| Variable | Belongs To |
|:---|:---|
| `VAPI_PRIVATE_KEY` | Interview Bot |
| `VAPI_PUBLIC_KEY` | Interview Bot |
| `VAPI_ASSISTANT_ID` | Interview Bot |
| `NEXT_PUBLIC_VAPI_PUBLIC_KEY` | Voice UI only |
| `NEXT_PUBLIC_VAPI_ASSISTANT_ID` | Voice UI only |
| `SUPABASE_KEY` (Interview Bot's `.env`) | Interview Bot |

---

## 3. Identified Issues & Root Causes

### 🔴 Issue 1 — Frontend Hits Wrong API URL (Most Likely Root Cause)

**File:** `frontend/src/context/ChatContext.tsx`, **line 150**

```ts
const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'https://manipal-chatbot.onrender.com';
const response = await fetch(`${baseUrl}/api/chat`, { ... });
```

**Problem:**  
- If `NEXT_PUBLIC_API_URL` is not set in the frontend `.env`, it **hardcodes** the Render production URL.  
- If the Render backend is not deployed (or sleeping due to free tier), every request silently fails and the frontend shows the **offline fallback** message instead.  
- There is **no `.env.local` or `.env` file** present in `/frontend/` by default — the variable is never set locally.

**Fix:** Create `frontend/.env.local` with:
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

### 🔴 Issue 2 — Backend Proxies Chat but AI Engine May Be on Wrong Port

**File:** `backend/app/routers/chat.py`, **lines 13–17**

```python
ai_engine_url = os.getenv("AI_ENGINE_URL", "http://localhost:8000")
res = await client.post(f"{ai_engine_url}/chat", ...)
```

**Problem:**  
- The backend defaults to `http://localhost:8000` for the AI Engine.  
- The **backend itself also runs on port 8000** by default (`python -m uvicorn main:app --reload`).  
- If both run on 8000, the backend tries to call **itself**, causing a `503` or connection error.  
- The backend's `.env.example` only contains `GROQ_API_KEY=` — `AI_ENGINE_URL` is **not documented at all** in the backend's environment file.

**Fix:** Run the ChatBot AI Engine on a different port (e.g. 8001) and set in `backend/.env`:
```
AI_ENGINE_URL=http://localhost:8001
```

---

### 🔴 Issue 3 — Response Shape Mismatch Between AI Engine and Frontend

**AI Engine returns** (from `ai-engine/ChatBot/main.py` line 2860):
```json
{ "answer": "..." }
```

**Backend gateway wraps it as** (from `backend/app/routers/chat.py` lines 21–24):
```python
return ChatResponse(
    response=data.get("answer", "No response from AI engine"),
    sources=data.get("sources", [])
)
```
→ so the backend sends: `{ "response": "...", "sources": [] }`

**Frontend extracts** (from `frontend/src/context/ChatContext.tsx` line 171):
```ts
aiText = rootData.message || rootData.response || rootData.text || ...
```

**Verdict:** The frontend correctly reads `rootData.response` — this chain **works if all services are connected**. However, if the frontend hits the AI Engine directly (not through the backend), it would get `{ "answer": ... }` and `rootData.response` would be `undefined`, showing raw JSON or blank.

---

### 🔴 Issue 4 — Supabase Keys Missing → Silent Empty Answers for MIT Queries

**File:** `ai-engine/ChatBot/main.py`, **lines 241–251**

```python
if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    print("WARNING: SUPABASE_URL or SUPABASE_ANON_KEY is missing...")
    supabase_client = None
```

**And at line 2556:**
```python
if supabase_client:
    # vector search runs
```

**Problem:**  
- If `SUPABASE_URL` or `SUPABASE_ANON_KEY` is missing/wrong, `supabase_client` is `None`.  
- Vector search is **completely skipped** — no error is thrown to the user.  
- For any MIT-specific query (placement, faculty, policy), the system returns:  
  `"I don't have that specific MIT Bengaluru information in my database."`  
- This looks like the chatbot is working but is actually missing all knowledge.

---

### 🔴 Issue 5 — Supabase Table `mit_bengaluru_data` May Be Empty

**File:** `ai-engine/ChatBot/main.py`, **line 318–320**

```python
if not res.data:
    print("WARNING: Table 'mit_bengaluru_data' is currently empty...")
```

**Problem:**  
- If `ingest.py` was never run, the table has no data.  
- The chatbot answers "I don't have that information" for every MIT-specific question.

---

### 🟡 Issue 6 — Groq API Key Missing or Invalid

**File:** `ai-engine/ChatBot/main.py`, **lines 22–24**

```python
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
```

**Problem:**  
- If `GROQ_API_KEY` is missing or expired, all LLM calls raise an exception.  
- The `groq_fallback_answer()` function (line 2352) **catches the exception** and returns `GROQ_BUSY_RESPONSE = "The chatbot is currently busy..."` — no crash, but no answer.  
- The Groq model used is `llama-3.1-8b-instant` (line 31) — verify this model ID is still available on Groq.

---

### 🟡 Issue 7 — Backend `.env` File Has No `GROQ_API_KEY` or `AI_ENGINE_URL` Documented

**File:** `backend/.env.example` — contains **only** `GROQ_API_KEY=`  
**Observed:** `backend/app/routers/upload.py` uses `GROQ_API_KEY` for resume ATS analysis (unrelated to chatbot).  
**But:** `AI_ENGINE_URL` (the most critical variable for the chatbot proxy) is **not in `.env.example`** at all — easy to miss.

---

## 4. Debugging Checklist

Work through these in order. Each item tells you exactly where to look.

```
[ ] 1. Frontend: Is NEXT_PUBLIC_API_URL set?
        File: frontend/.env.local  (create this if missing)
        Expected: NEXT_PUBLIC_API_URL=http://localhost:8000
        Test: console.log(process.env.NEXT_PUBLIC_API_URL) in browser DevTools

[ ] 2. Frontend: What URL is being called?
        File: frontend/src/context/ChatContext.tsx  Line 150-152
        Open Network tab in browser → look for /api/chat request
        Confirm: URL host matches your running backend

[ ] 3. Backend: Is it running?
        Command: curl http://localhost:8000/
        Expected: {"message": "Welcome to the Manipal Chatbot Backend API!", ...}

[ ] 4. Backend: Is AI_ENGINE_URL set correctly?
        File: backend/.env  (create if missing)
        Add: AI_ENGINE_URL=http://localhost:8001
        Confirm backend and AI engine run on different ports

[ ] 5. ChatBot AI Engine: Is it running?
        Command: curl http://localhost:8001/
        Expected: {"message": "MIT Bengaluru Chatbot API is running", ...}

[ ] 6. ChatBot AI Engine: Are Supabase keys set?
        File: ai-engine/ChatBot/.env  (create from .env.example)
        Required:
            SUPABASE_URL=https://your-project.supabase.co
            SUPABASE_ANON_KEY=eyJ...
        Verify: Look at startup logs for "Supabase connection verified"

[ ] 7. ChatBot AI Engine: Is the Supabase table populated?
        File: ai-engine/ChatBot/main.py  Line 318-320
        Check startup logs for "WARNING: Table 'mit_bengaluru_data' is currently empty"
        If empty: run python ingest.py inside ai-engine/ChatBot/

[ ] 8. ChatBot AI Engine: Is GROQ_API_KEY set?
        File: ai-engine/ChatBot/.env
        Required: GROQ_API_KEY=gsk_...
        Test: curl -X POST http://localhost:8001/chat \
              -H "Content-Type: application/json" \
              -d '{"question": "hello"}'
        Expected: {"answer": "Hello! How can I help you with MIT Bengaluru?"}

[ ] 9. Backend: Is CORS blocking the browser request?
        File: ai-engine/ChatBot/main.py  Lines 221-232
        CHATBOT_ALLOWED_ORIGINS defaults to * — should not be an issue
        File: backend/main.py  Lines 42-48
        allow_origins=["*"] — should not be an issue for local dev
        Check browser DevTools Console for CORS error messages

[ ] 10. Response shape: Is the frontend reading the right field?
        File: frontend/src/context/ChatContext.tsx  Lines 169-174
        Frontend reads: rootData.message || rootData.response || rootData.text
        Backend sends: { response: "...", sources: [] }
        → Frontend reads rootData.response ✓  (this is correct)
        But if frontend calls AI engine DIRECTLY (not backend):
        AI engine sends: { answer: "..." }
        → rootData.response is undefined → blank message shown
```

---

## 5. Chatbot-Only Run Commands

Run these **in three separate terminals** in this order:

```bash
# Terminal 1 — ChatBot AI Engine (port 8001)
cd ai-engine/ChatBot
pip install -r requirements.txt
# create .env first (see Section 2 above)
python -m uvicorn main:app --reload --port 8001

# Terminal 2 — Backend Gateway (port 8000)
cd backend
pip install -r requirements.txt
# create .env with: AI_ENGINE_URL=http://localhost:8001
python -m uvicorn main:app --reload --port 8000

# Terminal 3 — Frontend (port 3000)
cd frontend
npm install
# create .env.local with: NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev
```

> [!IMPORTANT]
> The ChatBot AI Engine **must run on 8001** (not 8000) because the Backend Gateway defaults to calling `http://localhost:8000` — if both run on 8000, the backend calls itself and returns a 503.

---

## 6. Quick Verification Test

After all three services are running, test the full chatbot pipeline with:

```bash
# Step 1: Test AI Engine directly
curl -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the attendance policy at MIT Bengaluru?"}'

# Expected: {"answer": "Based on the available data..."}  or  "I don't have that specific..."

# Step 2: Test through Backend Gateway
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the attendance policy at MIT Bengaluru?"}'

# Expected: {"response": "...", "sources": []}
```

If Step 1 works but Step 2 doesn't → the backend `AI_ENGINE_URL` is wrong.  
If Step 2 works but the browser shows "offline" → `NEXT_PUBLIC_API_URL` is not set in frontend.

---

## 7. Summary of Root Causes (Priority Order)

| Priority | Issue | Fix |
|:---:|:---|:---|
| 🔴 1 | `NEXT_PUBLIC_API_URL` not set → frontend hits Render (down/sleeping) | Create `frontend/.env.local` |
| 🔴 2 | Both backend and AI engine on port 8000 → backend calls itself | Run AI engine on 8001; set `AI_ENGINE_URL=http://localhost:8001` in backend |
| 🔴 3 | Supabase keys missing → `supabase_client = None` → no MIT knowledge | Set `SUPABASE_URL` + `SUPABASE_ANON_KEY` in `ai-engine/ChatBot/.env` |
| 🔴 4 | Supabase table empty → `ingest.py` never run | Run `python ingest.py` in `ai-engine/ChatBot/` |
| 🟡 5 | `GROQ_API_KEY` missing or invalid → returns "chatbot busy" | Set `GROQ_API_KEY` in `ai-engine/ChatBot/.env` |
| 🟡 6 | `AI_ENGINE_URL` not documented in `backend/.env.example` | Developer may not know this variable exists |
