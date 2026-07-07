# System Execution Flowcharts & Diagrams 📊

This document provides visual models of the Manipal Campus Assistant execution flows, module dependencies, and structural data transformations.

---

## 1. End-to-End Execution Flowchart

This Mermaid flowchart visualizes the operations of both the **RAG Chatbot** and the **Interview Bot** during runtime execution, outlining decision splits and database updates.

```mermaid
flowchart TD
    %% Entry
    Start([System Active / User Requests]) --> Init{Request Type?}

    %% Path 1: RAG Chat
    Init -->|POST /chat| SafetyCheck{Decorum Safety Filter?}
    SafetyCheck -->|Flagged| SafetyWarn[Return Safety warning text] --> EndChat([Return Response])
    SafetyCheck -->|Safe| CacheCheck{Response in Cache?}
    CacheCheck -->|Hit| FetchCache[Retrieve from in-memory cache] --> EndChat
    CacheCheck -->|Miss| MITCheck{Is MIT Specific Query?}
    
    MITCheck -->|No| GroqGlobal[Groq General LLM Prompt] --> SynthesizeAnswer
    MITCheck -->|Yes| EmbedQuery[SentenceTransformer 384D Embedder]
    EmbedQuery --> SupabaseVector[Supabase Cosine Similarity match_chunks]
    SupabaseVector --> MatchesFound{Any matches found?}
    MatchesFound -->|No| DirectFallback[Keyword direct lookup] --> ConstructContext
    MatchesFound -->|Yes| BoostResults[Rerank & boost placement files] --> ConstructContext
    
    ConstructContext[Assemble final context constraints] --> GroqContext[Groq contextual Prompt]
    GroqContext --> SynthesizeAnswer[Llama-3.1-8B Response Synthesis]
    SynthesizeAnswer --> SaveCache[Write response to Cache] --> EndChat

    %% Path 2: Interview Flow
    Init -->|POST /resume/upload| ExtractPDF[PyPDF2 raw text extractor]
    ExtractPDF --> AnalyzeResume[Groq llama-3.3 resume key analysis]
    AnalyzeResume --> Readiness[Calculate engineering readiness score]
    Readiness --> SaveSession[Store in-memory session_db] --> ReturnKey([Return session_key])

    Init -->|POST /interview/start| LoadQuestions[Retrieve preset role questions]
    LoadQuestions --> GenQuestions[Groq dynamic resume question generator]
    GenQuestions --> GenCoding[Retrieve preset or generate coding challenge]
    GenCoding --> CompilePrompt[services/prompt_builder compile system_prompt]
    CompilePrompt --> SaveActive[Register session details in interview_sessions]
    SaveActive --> ReturnPrompt([Return system_prompt & VAPI configs])

    Init -->|POST /interview/transcript| ParsePairs[services/evaluator _transcript_pairs parser]
    ParsePairs --> EvalLoop[Score each question with Groq llama-3.3 evaluator]
    EvalLoop --> AdjustDiff[next_difficulty complexity calculations]
    AdjustDiff --> UpdateProfile[update_skill_profile category scoring]
    UpdateProfile --> CalcOverall[Weighted overall scoring by interview type]
    CalcOverall --> WriteDB[Save to Supabase evaluations & interview_summary]
    WriteDB --> EndEval([Return final candidate report & scores])
```

---

## 2. Module Dependency Diagram

This diagram displays how directories, files, and modules import and call each other.

```mermaid
graph TD
    subgraph Frontend Client
        Layout[layout.tsx] --> ChatPage[page.tsx]
        Layout --> Placement[placement/page.tsx]
        ChatPage --> ChatInput[ChatInput.tsx]
        ChatPage --> ChatContext[ChatContext.tsx]
    end

    subgraph Backend Gateway
        Main[main.py] --> ChatRouter[routers/chat.py]
        Main --> UploadRouter[routers/upload.py]
        Main --> AudioRouter[routers/audio_stream.py]
        Main --> MockRouter[routers/mock_endpoints.py]
        UploadRouter --> FileHandler[services/file_handler.py]
        MockRouter --> DBEngine[database.py]
    end

    subgraph AI Engine Subsystems
        ChatBot[ChatBot/main.py] --> Ingest[ChatBot/ingest.py]
        InterviewBot[Interview_Bot/main.py] --> ResumeRouter[routers/resume.py]
        InterviewBot --> InterviewRouter[routers/interview.py]
        InterviewBot --> EvalRouter[routers/evaluation.py]

        %% Subsystem Services
        ResumeRouter --> ResumeService[services/resume_service.py]
        InterviewRouter --> PromptBuilder[services/prompt_builder.py]
        InterviewRouter --> QuestionLoader[services/question_loader.py]
        InterviewRouter --> VapiService[services/vapi_service.py]
        InterviewRouter --> SupabaseService[services/supabase_service.py]
        InterviewRouter --> SessionStore[services/session_store.py]
        InterviewRouter --> EvaluatorService[services/evaluator.py]
        EvalRouter --> SupabaseService
        EvaluatorService --> SupabaseService
    end

    %% Mappings
    ChatContext -->|HTTP Proxy| ChatRouter
    ChatRouter -->|HTTP Request| ChatBot
    InterviewRouter -->|Trigger Call| VapiService
    VapiService -->|Outbound HTTP| VapiAPI[VAPI Platform]
    VapiAPI -->|Inbound Webhook| InterviewRouter
```

---

## 3. Detailed Data Flow Transformations

The table below maps the exact inputs, intermediate data structures, and outputs that traverse the AI engine boundaries.

### RAG Chatbot Data Flow

```text
User Query (string)
  ↓
Decorum Safety Filter (Regex/String check)
  ↓
Smart Routing Check (Intent Classification Dictionary)
  ↓
SentenceTransformer (CPU processing -> 384-dimensional List[float])
  ↓
Supabase RPC match_chunks (List[float] -> List[Dict] with similarity scores)
  ↓
Reranker / Placement Booster (List[Dict] -> Sorted List[Dict])
  ↓
Context Constructor (Sorted List[Dict] -> String Context Block)
  ↓
Groq Completion (String Context + User Query -> JSON / String Output)
  ↓
Response Cache (String Output -> Saved Cache Dictionary)
```

### AI Interview Bot Data Flow

| Stage | Input Data Structure | Processing Module | Output Data Structure |
| :--- | :--- | :--- | :--- |
| **PDF Extraction** | Raw PDF File stream | `PyPDF2.PdfReader` | Cleaned raw string text (`resume_text`) |
| **Resume Analysis** | `resume_text` (str) | `analyse_resume` (Groq API) | JSON Object holding parsed candidate profile |
| **Readiness Check** | Candidate profile (JSON) | `calculate_readiness` | Score (int) and matched benchmark tags (dict) |
| **Questions Setup**| Candidate profile + Role | `generate_resume_questions` | List[Dict] (5 resume questions with ID and difficulty) |
| **Prompt Synthesis**| Questions + Role + Profile | `build_prompt` (Prompt Builder)| Detailed Vapi system prompt string |
| **Transcript Ingestion** | VAPI message body (JSON) | `/interview/transcript` | List[Dict] (ordered message blocks with role/message) |
| **Answer Extraction** | List[Dict] (Messages) | `extract_answer_from_transcript` | Cleaned user answer string |
| **Evaluation** | Question (str) + Answer (str)| `_groq_evaluate` (Groq API) | Score (0-10) and qualitative feedback (JSON) |
| **Summary Score** | Question evaluation list | `generate_summary` | Overall score (0-100), weaknesses, skill metrics (JSON) |
