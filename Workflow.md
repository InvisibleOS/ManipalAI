# AI Engine Pipeline and Workflow Document ⚙️

This document describes the step-by-step workflow of both AI subsystems (RAG Chatbot and Voice Interview Bot) inside the Manipal Campus Assistant. It maps raw client requests to final outputs, details the individual functions responsible for each processing step, and highlights bottlenecks and optimization strategies.

---

## 1. Subsystem 1: RAG Chatbot Pipeline (Input to Answer)

The RAG Chatbot processes textual queries or documents uploaded to the Supabase database.

### 1.1 Ingestion & Preprocessing Pipeline
1.  **Document Intake (Start):** The administrator executes the ingestion utility (`python ingest.py`) or uploads a document via the `/upload` API endpoint.
2.  **File Parsing:** The engine detects the file extension in `ingest_single_file()` and routes the file path to a specific parser:
    *   `.txt` -> `parse_txt()`: Standard file read.
    *   `.pdf` -> `parse_pdf()`: Extracts text page-by-page using `pypdf.PdfReader`.
    *   `.docx` -> `parse_docx()`: Reads paragraph objects using `docx.Document`.
    *   `.csv` / `.xlsx` -> `parse_spreadsheet()`: Loads data via `pandas.read_csv()` / `read_excel()`. Formats each row as key-value pairs (`col1: val1, col2: val2`).
    *   `.db` -> `parse_sqlite_db()`: Connects via `sqlite3`, queries table definitions and dumps row structures as text.
    *   `.json` -> `parse_json()`: Detects if it uses the structured MIT Bengaluru Q&A format (extracting "documents" and "faq_documents"), or processes generic lists/objects.
3.  **Text Chunking:** Extracted plain text is divided into overlapping blocks using `chunk_text(text, chunk_size=1000, overlap=150)`.
4.  **Embedding Generation:** Each text chunk is converted into a 384-dimensional vector using `SentenceTransformer("all-MiniLM-L6-v2")` running locally on the CPU.
5.  **Database Storage (End of Preprocessing):** Cleaned text chunks and their respective embeddings are upserted in batches of 100 to the `mit_bengaluru_data` table on Supabase, while the raw file is copied to the `chatbot-assets` storage bucket.

### 1.2 Query & Inference Pipeline (Detection & Retrieval)
1.  **User Input:** The student submits a question via the frontend, which is proxied to `POST /chat`.
2.  **Decorum Safety Filtering:** The engine scans the input against regex blocks and safety prompts. Flagged messages receive immediate warnings without hitting databases.
3.  **Query Classification (Smart Routing):**
    *   `is_mit_specific_query(question)` determines if the query requires database context.
    *   If **No**: Bypasses Supabase and directly queries Groq `llama-3.1-8b-instant` using general knowledge (reducing API overhead).
    *   If **Yes**: Triggers the retrieval pipeline.
4.  **Hybrid Vector and Keyword Retrieval (Detection & Filtering):**
    *   The user query is embedded into a 384-dimensional vector.
    *   **Vector Search:** Calls the Supabase RPC function `match_chunks(query_embedding, match_threshold, match_count)` which performs Cosine Similarity computations.
    *   **Fallback Keyword Search:** If similarity is low (`needs_direct_text_fallback()`), the engine queries Supabase using keyword indexes (`keyword_search()`) to fetch exact terms.
5.  **Data Extraction & Boosting:**
    *   If it is a placement query (`is_placement_query()`), the engine extracts student records, formatting salaries (`format_lpa()`) and prioritizing high packages (`placement_boost_score()`).
    *   If it is a faculty query (`is_faculty_query()`), it parses structured details (`extract_faculty_profile_fields()`).
6.  **Context Construction:** Chunks are formatted into a context block up to characters limits (e.g. `MAX_TOTAL_CONTEXT_CHARS = 1800`).
7.  **Answer Synthesis (Evaluation & Output):**
    *   Context and user query are injected into a Groq system prompt.
    *   Groq synthesizes a structured natural language answer.
    *   The result is saved in a local cache (`response_cache`) for 10 minutes.

---

## 2. Subsystem 2: Voice Interview Bot Pipeline (Resume to Score)

The Interview Bot analyzes a PDF resume and runs an interactive verbal technical mock interview.

### 2.1 Resume Ingestion and Preprocessing
1.  **Input:** Candidate uploads a PDF resume and selects a target role via `/resume/upload`.
2.  **Preprocessing (Extraction):** PyPDF2 extracts raw resume text (`extract_text()`).
3.  **Resume Analysis:** Groq `llama-3.3-70b-versatile` reads the text, extracting candidate name, experience, key skills, notable projects, and weak areas (`analyse_resume()`).
4.  **Readiness Score Computation:** `calculate_readiness()` checks the extracted skills against standard benchmarks (`ROLE_BENCHMARKS`) for the target role, computing an engineering readiness percentage.
5.  **Question Generation:** Generates 5 tailored technical questions based on the candidate's resume (`generate_resume_questions()`). It deduplicates against previously asked questions.
6.  **Coding Challenge Setup:** Selects a coding challenge matching the role from `questions.json` or generates a dynamic problem using Groq (`generate_coding_question()`).

### 2.2 Interactive Session & Vapi Voice Loop (State Tracking)
1.  **Start Request:** The client triggers `/interview/start`.
2.  **Prompt Builder:** The engine compiles the `system_prompt` containing candidate details, selected preset questions, and the coding problem. It defines rules (e.g. "Ask one question at a time", "Go silent during coding").
3.  **VAPI Handshake:** Sends the prompt to VAPI to initialize a voice stream call.
4.  **Verbal Interaction Loop:**
    *   The candidate speaks; VAPI streams back audio and converts voice to text.
    *   VAPI tracks conversation logs.
5.  **End of Call Webhook:** VAPI submits the final message transcript to `/interview/transcript`.

### 2.3 Transcript Evaluation & Reporting (Evaluation & Output)
1.  **Transcript Parsing:** Pairs interviewer questions with candidate answers (`_transcript_pairs()`).
2.  **Answer Assessment:**
    *   Each response is evaluated by Groq `llama-3.3-70b-versatile` (`_groq_evaluate()`) to provide a score (0-10), ideal answer description, and qualitative feedback.
    *   If Groq fails, `_heuristic_evaluate()` applies a word-count rule-based fallback.
3.  **Dynamic Difficulty & Skill Profiling:**
    *   `next_difficulty()` recalculates the difficulty for the next question.
    *   `update_skill_profile()` adjusts scores (Technical Knowledge, Confidence, DBMS, etc.) based on answer quality.
4.  **Overall Summary Generation:** Computes a weighted overall percentage score based on weights corresponding to the `interview_type` (e.g., HR Interview focuses on communication, Technical focuses on coding/concepts).
5.  **Database Storage:** Inserts row details into Supabase `evaluations` and the final candidate summary into `interview_summary`.

---

## 3. Major Function Walkthrough

Below is a detailed walkthrough of the key functions driving the AI system:

| Function Name | Location | Inputs | Outputs | Dependencies | Where It Is Called | Why It Exists |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `ingest_single_file` | `ChatBot/ingest.py` | `file_path` (str) | `total_rows` (int) | `pypdf`, `pandas`, `docx`, `SentenceTransformer` | `main()` in `ingest.py` | Core handler for document parsing, vectorization, and database uploads. |
| `is_mit_specific_query` | `ChatBot/main.py` | `question` (str) | `bool` | Regex matcher | `POST /chat` | Classifies query intent to route requests and save compute resources. |
| `match_chunks` (RPC) | Supabase DB | `query_embedding`, `match_threshold`, `match_count` | `table` (similar chunks) | pgvector extensions | `POST /chat` | High-speed vector similarity lookup in the DB layer. |
| `analyse_resume` | `Interview_Bot/services/resume_service.py` | `resume_text` (str), `role` (str) | `Dict` (structured profile) | Groq API | `/resume/upload` | Extracts structured candidate profiles from unstructured text. |
| `generate_resume_questions` | `Interview_Bot/services/resume_service.py` | `resume_analysis`, `role`, `asked_resume_questions` | `List[Dict]` (5 questions) | Groq API | `/interview/start` | Creates resume-specific technical questions for the session. |
| `build` | `Interview_Bot/services/prompt_builder.py` | `role`, `duration_mins`, questions list, resume analysis | `str` (system prompt) | `get_time_split` helper | `/interview/start` | Synthesizes custom rules and context for VAPI voice agents. |
| `evaluate_interview` | `Interview_Bot/services/evaluator.py` | `user_id`, `interview_id`, questions, transcript | `Dict` (eval summary) | `_groq_evaluate`, `save_evaluation` | `/interview/transcript` | Scores responses, updates skill maps, and writes candidate reports to DB. |

---

## 4. Performance & Resource Analysis

*   **SentenceTransformer Latency:** The `all-MiniLM-L6-v2` model runs locally on the CPU. Generating a 384D embedding for a single text chunk takes **~15ms - 50ms**, which is lightweight.
*   **Groq API Roundtrips:** Groq API inference for `llama-3.1-8b-instant` takes **~300ms - 600ms** depending on network congestion, and `llama-3.3-70b-versatile` takes **~800ms - 1.5s**. 
*   **Calculated Latency Profile:**
    *   **Chat Endpoint (RAG):** Embedding generation (30ms) + Supabase match (50ms) + Groq generation (450ms) = **~530ms total response time** under typical conditions.
    *   **Interview Start Endpoint:** Supabase user fetch (100ms) + Resume analysis (1.2s) + Question generation (1.5s) = **~2.8s total response time**. Subsequent question evaluations in the transcript take **~1.2s per question** sequentially.
*   **Memory Usage:** The SentenceTransformer model loads into CPU memory at startup, consuming **~400MB RAM**. FastAPI processes consume **~150MB RAM** each.
*   **Factors Affecting Speed:**
    *   Sequential execution of LLM calls during transcript evaluations (processing 5 questions takes 5 * 1.2s = 6s).
    *   Cold starts on Supabase connection pools.
    *   CPU limitations on SentenceTransformer inference inside small containers.

---

## 5. System Optimization Opportunities

1.  **Asynchronous Evaluation (Performance):** Currently, `evaluate_interview()` evaluates questions sequentially inside a synchronous loop. Wrapping `_groq_evaluate` in `asyncio.gather` would process all questions in parallel, reducing execution time from **~6 seconds to ~1.5 seconds**.
2.  **Vector Store Caching (Scalability):** During document uploads, the entire local file collection is synced against the database. Storing a checksum of local files and only updating modified files would reduce database writes.
3.  **Local Thread Pools (Concurrency):** `SentenceTransformer` operations in the FastAPI main thread can block requests under high concurrency. Offloading embedding generations to `asyncio` loop executors would improve throughput.
4.  **Database Connection Pooling (Stability):** The Supabase client initializes a new HTTP connection for each SQL execution in `supabase_service.py`. Replacing this with persistent connection pooling (`pgbouncer` or HTTP persistent connections) would reduce network handshakes.
