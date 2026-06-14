import json
import os
import re
import threading
import time

import ingest
from supabase import create_client, Client
import requests
import shutil
from fastapi import FastAPI, HTTPException, Request, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sentence_transformers import SentenceTransformer

from dotenv import load_dotenv
from groq import Groq

load_dotenv()

groq_client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_PATH = os.path.join(BASE_DIR, "dataset.json")
COLLECTION_NAME = "mit_bengaluru_data"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
GROQ_MODEL = "llama-3.1-8b-instant"
GREETING_RESPONSE = "Hello! How can I help you with MIT Bengaluru?"
USER_RATE_LIMIT = 10
USER_RATE_WINDOW_SECONDS = 60
CACHE_DURATION_SECONDS = 600
USER_RATE_LIMIT_RESPONSE = "The chatbot is currently receiving too many requests from your session. Please wait a few seconds and try again."
GROQ_BUSY_RESPONSE = "The chatbot is currently busy. Please try again in a few seconds."
GROQ_TIMEOUT_RESPONSE = "The chatbot is currently taking too long to respond. Please try again in a few seconds."

MAX_NORMAL_CONTEXT_CHARS = 1500
MAX_NORMAL_SNIPPET_CHARS = 450
MAX_FACULTY_SNIPPET_CHARS = 700
MAX_TOTAL_CONTEXT_CHARS = 1800
PLACEMENT_QUERY_TERMS = {
    "average package",
    "career",
    "companies",
    "ctc",
    "highest package",
    "internship",
    "offers",
    "package",
    "placement",
    "placements",
    "recruiters",
    "salary",
    "recruiter",
    "placed",
    "lpa",
    "student",
    "students",
    "list",
    "names",
    "who all",
}
PLACEMENT_BOOST_TERMS = {
    "career",
    "companies",
    "ctc",
    "internship",
    "offer",
    "offers",
    "package",
    "placement",
    "placements",
    "recruiter",
    "recruiters",
    "salary",
}
PLACEMENT_PRIORITY_TITLE_TERMS = {"placement", "career", "recruiter"}
PLACEMENT_PRIORITY_CONTENT_PHRASES = {
    "highest package",
    "average package",
    "ctc",
}
PLACEMENT_PRIORITY_URL_TERMS = {"placement", "career"}
MAX_PLACEMENT_SNIPPET_CHARS = 500
MAX_PLACEMENT_CONTEXT_CHARS = 2200
MAX_AGGREGATION_CONTEXT_CHARS = 4500
MAX_HYBRID_NORMAL_CHUNKS = 5
MAX_HYBRID_AGGREGATION_CHUNKS = 10
NUMERICAL_QUERY_TERMS = {
    "average ctc",
    "average package",
    "highest ctc",
    "highest package",
    "highest placement",
    "lowest ctc",
    "lowest package",
    "max package",
    "maximum package",
    "package statistics",
    "top package",
    "top placement",
}
PACKAGE_VALUE_PATTERN = re.compile(
    r"(?i)(?:ctc|package)?\s*(?:=|:)?\s*(?:rs\.?|inr|₹|€)?\s*(\d+(?:\.\d+)?)\s*lpa"
)
AGGREGATION_QUERY_TERMS = {
    "all faculty",
    "all students",
    "assistant professors",
    "committee",
    "committee members",
    "committee names",
    "committees",
    "coordinators",
    "count",
    "dean",
    "director",
    "faculty members",
    "hod",
    "how many",
    "list all",
    "list",
    "names of all",
    "members",
    "more",
    "next",
    "professors",
    "recruiters",
    "students placed",
    "total",
    "who all",
}
ACADEMIC_PROGRAM_QUERY_TERMS = {
    "academic programs",
    "branches available",
    "btech courses",
    "b.tech courses",
    "courses are in",
    "courses offered",
    "degrees offered",
    "departments available",
    "how many btech",
    "how many b.tech",
    "how many courses",
    "how many programs",
    "programs offered",
    "what can i study",
    "what courses are offered",
}
FACULTY_CATEGORY_TERMS = {
    "assistant professor",
    "associate professor",
    "coordinator",
    "dean",
    "director",
    "electronics and communication",
    "faculty",
    "head",
    "hod",
    "information technology",
    "professor",
    "school of computer engineering",
    "science and humanities",
}
PLACEMENT_RECORD_TERMS = {
    "b.tech",
    "companies",
    "company",
    "ctc",
    "lpa",
    "package",
    "placed",
    "placement",
    "recruiter",
    "student",
}
MIT_SPECIFIC_TERMS = {
    "admission",
    "admissions",
    "anti ragging",
    "anti-ragging",
    "bengaluru",
    "campus",
    "college policy",
    "college policies",
    "committee",
    "committees",
    "course offered",
    "courses offered",
    "dean",
    "department",
    "departments",
    "director",
    "events",
    "faculty",
    "grievance",
    "hod",
    "hostel",
    "internal complaint committee",
    "mahe",
    "mahe bengaluru",
    "manipal",
    "mit",
    "mit bengaluru",
    "package",
    "packages",
    "placement",
    "placements",
    "recruiter",
    "recruiters",
    "student activity council",
    "workshop",
    "workshops",
}


app = FastAPI(title="MIT Bengaluru RAG Chatbot API")
allowed_origins = [
    origin.strip()
    for origin in os.getenv("CHATBOT_ALLOWED_ORIGINS", "*").split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

embedding_model = SentenceTransformer(EMBEDDING_MODEL)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
STORAGE_BUCKET_NAME = "chatbot-assets"

if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    print("WARNING: SUPABASE_URL or SUPABASE_ANON_KEY is missing from environment variables.")
    supabase_client = None
else:
    supabase_client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    print("WARNING: SUPABASE_URL or SUPABASE_SERVICE_KEY is missing from environment variables.")
    supabase_admin_client = None
else:
    supabase_admin_client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

auto_ingestion_attempted = False
ingestion_lock = threading.Lock()
dataset_chunks = []
placement_dataset_chunks = []
classified_people_cache = None
faculty_entities_cache = None
pagination_state = {
    "entity_type": None,
    "full_result_list": [],
    "last_start_index": 0,
    "last_end_index": 0,
    "page_size": 50,
}
request_timestamps_by_user = {}
response_cache = {}


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1)


def download_dataset_from_storage():
    if os.path.exists(DATASET_PATH):
        print("dataset.json found locally.")
        return
    if not supabase_client:
        print("Supabase client not initialized. Cannot download dataset.json.")
        return
    try:
        print(f"dataset.json missing locally. Attempting to download from storage bucket '{STORAGE_BUCKET_NAME}'...")
        response = supabase_client.storage.from_(STORAGE_BUCKET_NAME).download("dataset.json")
        with open(DATASET_PATH, "wb") as f:
            f.write(response)
        print("Successfully downloaded dataset.json from Supabase Storage.")
    except Exception as e:
        print(f"WARNING: Could not download dataset.json from Supabase Storage: {e}")
        print("Rule-based lists and faculty search might not work.")


def verify_supabase_connection():
    if not supabase_client:
        print("WARNING: Supabase connection is not verified (keys missing).")
        return
    try:
        # Check if table exists and has data
        res = supabase_client.table("mit_bengaluru_data").select("id").limit(1).execute()
        print("Supabase connection verified. Table 'mit_bengaluru_data' is accessible.")
        if not res.data:
            print("WARNING: Table 'mit_bengaluru_data' is currently empty. You can ingest files by running 'python ingest.py' or uploading via the POST /upload API.")
    except Exception as e:
        print(f"WARNING: Failed to connect to Supabase or query table: {e}")
        print("Please check your database connection, SQL schema settings, and API keys.")


download_dataset_from_storage()
verify_supabase_connection()


def load_dataset_chunks():
    if not supabase_client:
        print("WARNING: Supabase client is not initialized. Cannot load chunks.")
        return []
    try:
        print("Loading all database chunks from Supabase into memory...")
        response = supabase_client.table("mit_bengaluru_data").select("id,title,knowledge_type,url,content").execute()
        db_chunks = response.data or []
        chunks = []
        for item in db_chunks:
            chunks.append({
                "chunk_id": item.get("id") or "",
                "title": item.get("title") or "",
                "knowledge_type": item.get("knowledge_type") or "",
                "url": item.get("url") or "",
                "content": item.get("content") or "",
            })
        print(f"Successfully loaded {len(chunks)} chunks from Supabase.")
        return chunks
    except Exception as e:
        print("Failed to load dataset chunks from Supabase:", e)
        return []


def load_placement_dataset_chunks():
    return load_dataset_chunks()


def is_simple_greeting(question):
    normalized = re.sub(r"[^a-z\s]", "", question.lower()).strip()
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized in {
        "hello",
        "hi",
        "hey",
        "good morning",
        "good evening",
    }


def is_faculty_query(question):
    normalized = question.lower().strip()
    if any(
        term in normalized
        for term in [
            "admission",
            "branch",
            "course",
            "department",
            "package",
            "placement",
            "program",
            "recruiter",
            "student",
        ]
    ):
        return False

    return (
        normalized.startswith("who is")
        or normalized.startswith("tell me about")
        or normalized.startswith("profile of")
        or normalized.startswith("faculty profile of")
        or " dr." in f" {normalized}"
    )


def is_placement_query(question):
    normalized = question.lower()
    return any(term in normalized for term in PLACEMENT_QUERY_TERMS)


def is_numerical_query(question):
    normalized = question.lower()
    return any(term in normalized for term in NUMERICAL_QUERY_TERMS)


def is_aggregation_query(question):
    normalized = question.lower()
    return any(term in normalized for term in AGGREGATION_QUERY_TERMS)


def is_academic_program_query(question):
    normalized = question.lower()
    return any(term in normalized for term in ACADEMIC_PROGRAM_QUERY_TERMS) or (
        any(term in normalized for term in ["course", "courses", "program", "programs", "branch", "branches"])
        and any(term in normalized for term in ["mit", "blr", "bengaluru", "available", "offered"])
    )


def is_role_lookup_query(question):
    normalized = question.lower()
    return any(
        pattern in normalized
        for pattern in [
            "who is the hod of",
            "who is hod",
            "who is head of",
            "head of",
            "head of department",
            "hod-cse",
            "hod-ece",
            "hod-it",
            "dean of",
            "director of",
            "coordinator of",
        ]
    )


def person_query_name(question):
    match = re.match(
        r"^\s*(?:who\s+is|who's|tell\s+me\s+about|profile\s+of|faculty\s+profile\s+of)\s+(.+?)\s*[?.!]*\s*$",
        question,
        re.I,
    )
    if not match:
        return ""

    name = clean_text(match.group(1)).strip(" ?.!,'\"")
    normalized = name.lower()
    if normalized.startswith(("the ", "a ", "an ")):
        return ""
    if re.search(r"\b(hod|head|dean|director|committee|faculty|professor|department|course|program|placement)\b", normalized):
        return ""

    name_tokens = re.findall(r"[a-z]+", normalized)
    name_tokens = [token for token in name_tokens if token not in {"dr", "mr", "ms", "prof"}]
    if len(name_tokens) < 2:
        return ""
    return name


def normalize_person_name(name):
    key = re.sub(r"^(?:dr|mr|ms|prof)\.?\s+", "", (name or "").lower()).strip()
    key = re.sub(r"[^a-z0-9\s]", " ", key)
    key = re.sub(r"\s+", " ", key).strip()
    return key


def mit_person_entity_match_found(person_name):
    query_key = normalize_person_name(person_name)
    if not query_key:
        return False

    query_terms = query_key.split()
    for person in all_classified_people():
        person_key = normalize_person_name(person.get("name", ""))
        if not person_key:
            continue
        if query_key == person_key:
            return True
        person_terms = person_key.split()
        if all(term in person_terms for term in query_terms):
            return True
    return False


def is_mit_specific_query(question):
    normalized = re.sub(r"[^a-z0-9\s.-]", " ", question.lower())
    normalized = re.sub(r"\s+", " ", normalized).strip()
    padded = f" {normalized} "

    if any(
        re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", normalized)
        for term in MIT_SPECIFIC_TERMS
    ):
        return True

    person_name = person_query_name(question)
    if person_name:
        return mit_person_entity_match_found(person_name)

    if is_faculty_query(question) or is_placement_query(question):
        return True

    if is_academic_program_query(question):
        return True

    if re.search(r"\b(hod|dean|director|committee|grievance|hostel|admission|admissions)\b", normalized):
        return True

    if re.search(r"\b(cse|ece|it|soce)\b", normalized) and any(
        term in normalized
        for term in ["hod", "department", "faculty", "placement", "course", "program"]
    ):
        return True

    return any(
        phrase in padded
        for phrase in [
            " courses available ",
            " programs available ",
            " branches available ",
            " courses in college ",
            " programs in college ",
        ]
    )


def expand_department_terms(question):
    normalized = question.lower()
    mapping = {
        "ece": "electronics and communication engineering",
        "cse": "computer science and engineering",
        "it": "information technology",
        "soce": "school of computer engineering",
    }
    terms = []
    for short, full in mapping.items():
        if re.search(rf"\b{short}\b", normalized) or full in normalized:
            terms.extend([short, full])
    if "electronics and communication" in normalized or "electronics & communication" in normalized:
        terms.extend(["ece", "electronics and communication", "electronics & communication", "electronics & communications"])
    if "computer science" in normalized:
        terms.extend(["cse", "computer science", "computer science & engineering"])
    return terms


def is_list_style_query(question):
    normalized = question.lower()
    return any(
        term in normalized
        for term in [
            "all students",
            "give names",
            "list",
            "names of all",
            "what packages",
            "whichever is available",
            "who all",
        ]
    )


def aggregation_type(question):
    normalized = question.lower()
    if any(term in normalized for term in ["placement", "placed", "package", "ctc", "student"]):
        return "placement_students"
    if "recruiter" in normalized or "companies" in normalized or "company" in normalized:
        return "recruiters"
    if "committee" in normalized:
        return "committee_members"
    if any(term in normalized for term in ["faculty", "professor", "hod", "dean", "director", "coordinator"]):
        return "faculty_staff"
    return "general"


def clean_text(text):
    text = re.sub(r"\s+", " ", text or "").strip()
    return text


def truncate_text(text, max_chars):
    text = clean_text(text)
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3].rsplit(" ", 1)[0] + "..."


def name_terms_from_question(question):
    stop_words = {
        "about",
        "faculty",
        "is",
        "me",
        "of",
        "profile",
        "tell",
        "who",
    }
    words = re.findall(r"[a-z0-9]+", question.lower())
    words = [word for word in words if word not in stop_words and word != "dr"]
    return words


def query_terms(question):
    stop_words = {
        "a",
        "all",
        "and",
        "are",
        "by",
        "for",
        "give",
        "got",
        "has",
        "have",
        "in",
        "is",
        "me",
        "of",
        "the",
        "there",
        "to",
        "what",
        "which",
        "who",
    }
    terms = [
        term
        for term in re.findall(r"[a-z0-9]+", question.lower())
        if term not in stop_words and len(term) > 1
    ]

    if is_placement_query(question) or is_numerical_query(question):
        terms.extend(PLACEMENT_RECORD_TERMS)
    if aggregation_type(question) == "faculty_staff":
        terms.extend(FACULTY_CATEGORY_TERMS)
    return list(dict.fromkeys(terms))


def exact_phrase_search(question, limit=5):
    phrase = clean_text(question).lower()
    if len(phrase) < 4:
        return []

    matches = []
    for chunk in placement_dataset_chunks:
        searchable = f"{chunk.get('title', '')}\n{chunk.get('content', '')}\n{chunk.get('url', '')}".lower()
        if phrase in searchable:
            matches.append(chunk)
        if len(matches) >= limit:
            break
    return matches


def keyword_search(question, limit=10):
    terms = query_terms(question)
    if not terms:
        return []

    agg_type = aggregation_type(question)
    scored_matches = []
    for chunk in placement_dataset_chunks:
        title = chunk.get("title", "")
        content = chunk.get("content", "")
        url = chunk.get("url", "")
        title_lower = title.lower()
        content_lower = content.lower()
        url_lower = url.lower()
        searchable = f"{title_lower}\n{content_lower}\n{url_lower}"

        if not any(term in searchable for term in terms):
            continue

        score = 0
        score += sum(8 for term in terms if term in title_lower)
        score += sum(4 for term in terms if term in content_lower)
        score += sum(3 for term in terms if term in url_lower)

        if is_placement_query(question) or is_numerical_query(question):
            score += placement_boost_score(chunk)
            score += sum(20 for term in PLACEMENT_RECORD_TERMS if term in searchable)

        if agg_type == "faculty_staff":
            score += sum(15 for term in FACULTY_CATEGORY_TERMS if term in searchable)
        elif agg_type == "placement_students":
            score += sum(15 for term in PLACEMENT_RECORD_TERMS if term in searchable)
        elif agg_type == "recruiters":
            score += sum(15 for term in ["recruiter", "recruiters", "companies", "company"] if term in searchable)
        elif agg_type == "committee_members":
            score += 20 if "committee" in searchable else 0

        scored_matches.append((score, chunk))

    scored_matches.sort(key=lambda item: item[0], reverse=True)
    return [chunk for _, chunk in scored_matches[:limit]]


def exact_faculty_match(question):
    if not is_faculty_query(question):
        return None

    terms = name_terms_from_question(question)
    if not terms:
        return None

    phrase = " ".join(terms)
    scored_matches = []
    for chunk in dataset_chunks:
        title = chunk.get("title", "")
        content = chunk.get("content", "")
        searchable = f"{title}\n{content}".lower()
        title_lower = title.lower()

        if not all(term in searchable for term in terms):
            continue

        score = 0
        if phrase and phrase in title_lower:
            score += 100
        if all(term in title_lower for term in terms):
            score += 75
        if phrase and phrase in searchable:
            score += 25
        score += sum(1 for term in terms if term in title_lower) * 10

        scored_matches.append((score, chunk))

    if not scored_matches:
        return None

    scored_matches.sort(key=lambda item: item[0], reverse=True)
    return scored_matches[0][1]


def placement_keyword_search(limit=8):
    scored_matches = []

    for chunk in placement_dataset_chunks:
        title = chunk.get("title", "")
        content = chunk.get("content", "")
        url = chunk.get("url", "")
        title_lower = title.lower()
        content_lower = content.lower()
        url_lower = url.lower()
        searchable = f"{title_lower}\n{content_lower}"

        if not any(term in searchable for term in PLACEMENT_BOOST_TERMS):
            continue

        score = 0
        score += sum(8 for term in PLACEMENT_BOOST_TERMS if term in searchable)
        score += sum(25 for term in PLACEMENT_PRIORITY_TITLE_TERMS if term in title_lower)
        score += sum(
            30
            for phrase in PLACEMENT_PRIORITY_CONTENT_PHRASES
            if phrase in content_lower
        )
        score += sum(20 for term in PLACEMENT_PRIORITY_URL_TERMS if term in url_lower)

        scored_matches.append((score, chunk))

    scored_matches.sort(key=lambda item: item[0], reverse=True)
    return [chunk for _, chunk in scored_matches[:limit]]


def find_relevant_snippet(document, question, max_chars=MAX_FACULTY_SNIPPET_CHARS):
    text = clean_text(document)
    if len(text) <= max_chars:
        return text

    lowered = text.lower()
    terms = name_terms_from_question(question)
    candidates = [" ".join(term for term in terms if len(term) > 1)]
    candidates.extend(term for term in terms if len(term) > 1)

    match_index = -1
    for candidate in candidates:
        candidate = candidate.strip()
        if not candidate:
            continue
        match_index = lowered.find(candidate)
        if match_index != -1:
            break

    if match_index == -1:
        return truncate_text(text, max_chars)

    start = max(0, match_index - 120)
    end = min(len(text), match_index + max_chars - 120)
    snippet = text[start:end].strip()
    return truncate_text(snippet, max_chars)


def extract_faculty_profile_fields(content):
    lines = [clean_text(line.strip("#*=:- ")) for line in content.splitlines()]
    lines = [line for line in lines if line]
    fields = {}

    for line in lines:
        if line.lower().startswith("title:"):
            fields["Name"] = clean_text(line.split(":", 1)[1])
            break
    if "Name" not in fields and lines:
        fields["Name"] = lines[0]

    for index, line in enumerate(lines):
        lower = line.lower()
        if "professor" in lower and "Designation" not in fields:
            fields["Designation"] = line
        if lower.startswith("department of") and "Department/School" not in fields:
            fields["Department/School"] = line
        if re.search(r"[\w.\-]+@manipal\.edu", line, re.I) and "Email/Contact" not in fields:
            fields["Email/Contact"] = re.search(r"[\w.\-]+@manipal\.edu", line, re.I).group(0)
        if lower.startswith("current academic role") and "Role" not in fields:
            for candidate in lines[index + 1 : index + 5]:
                if candidate.lower() != "academic" and not re.search(r"expertise|publication|responsibilities|^-+$", candidate, re.I):
                    fields["Role"] = candidate
                    break
        if lower.startswith("area of research") and "Expertise/Research" not in fields:
            for candidate in lines[index + 1 : index + 5]:
                if not re.search(r"professional affiliations|google scholar|publication", candidate, re.I):
                    fields["Expertise/Research"] = candidate
                    break

    if "Role" not in fields and "Designation" in fields and re.search(r"head|hod|coordinator", fields["Designation"], re.I):
        fields["Role"] = fields["Designation"]
    return fields


def format_faculty_profile_fields(fields):
    if not fields:
        return ""
    order = ["Name", "Designation", "Department/School", "Role", "Expertise/Research", "Email/Contact"]
    return "\n".join(f"{key}: {fields[key]}" for key in order if fields.get(key))


def faculty_profile_direct_answer(chunk):
    if not chunk or chunk.get("knowledge_type") != "faculty":
        return ""
    fields = extract_faculty_profile_fields(chunk.get("content", ""))
    useful_keys = {"Designation", "Department/School", "Role", "Expertise/Research", "Email/Contact"}
    if len(useful_keys.intersection(fields)) < 2:
        return ""
    name = fields.get("Name", "This faculty member")
    designation = fields.get("Designation", "a faculty member")
    department = fields.get("Department/School", "the department is not specified in the available data")
    sentences = [f"{name} is {designation} in {department} at MIT Bengaluru."]
    if fields.get("Role"):
        sentences.append(f"The available data mentions the role/responsibility as {fields['Role']}.")
    if fields.get("Expertise/Research"):
        sentences.append(f"Areas of expertise include {fields['Expertise/Research']}.")
    if fields.get("Email/Contact"):
        sentences.append(f"The listed email/contact is {fields['Email/Contact']}.")
    return " ".join(sentences)


def chunks_from_results(results, limit=5):
    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    ids = results.get("ids", [[]])[0]
    distances = results.get("distances", [[]])[0]
    chunks = []

    for index, document in enumerate(documents[:limit]):
        metadata = metadatas[index] if index < len(metadatas) else {}
        chunk_id = ids[index] if index < len(ids) else f"vector_{index}"
        chunks.append(
            {
                "chunk_id": chunk_id,
                "title": metadata.get("title", ""),
                "knowledge_type": metadata.get("knowledge_type", ""),
                "url": metadata.get("url", ""),
                "content": document,
                "distance": distances[index] if index < len(distances) else None,
            }
        )

    return chunks


def normalized_lookup_text(text):
    text = re.sub(r"[^a-z0-9\s]", " ", (text or "").lower())
    return re.sub(r"\s+", " ", text).strip()


def direct_chroma_text_search(collection, question, limit=5):
    person_name = person_query_name(question)
    terms = []
    if person_name:
        normalized_name = normalize_person_name(person_name)
        if normalized_name:
            terms.append(normalized_name)
            terms.extend(normalized_name.split())
    else:
        terms = query_terms(question)

    terms = [normalized_lookup_text(term) for term in terms if len(normalized_lookup_text(term)) > 1]
    if not terms:
        return []

    if not supabase_client:
        print("Supabase client is missing. Cannot run direct database text search.")
        return []

    try:
        # Build OR filter queries for database-side string matching
        filter_conditions = []
        for term in terms[:5]: # Limit to avoid overlong query parameters
            filter_conditions.append(f"content.ilike.%{term}%")
            filter_conditions.append(f"title.ilike.%{term}%")
        
        or_filter = ",".join(filter_conditions)
        
        response = supabase_client.table("mit_bengaluru_data") \
            .select("id,title,knowledge_type,url,content") \
            .or_(or_filter) \
            .limit(50) \
            .execute()
        
        db_results = response.data or []
    except Exception as exc:
        print("Direct database text search failed:", exc)
        return []

    scored_matches = []
    for row in db_results:
        title = row.get("title") or ""
        content = row.get("content") or ""
        url = row.get("url") or ""
        ktype = row.get("knowledge_type") or ""
        
        searchable = normalized_lookup_text(f"{title}\n{ktype}\n{url}\n{content}")
        
        if person_name:
            name_key = normalize_person_name(person_name)
            if name_key not in searchable and not all(term in searchable for term in name_key.split()):
                continue
            score = 1000 if name_key in searchable else 500
        else:
            if not any(term in searchable for term in terms):
                continue
            score = sum(10 for term in terms if term in searchable)

        if ktype == "placement":
            score += 50
            
        scored_matches.append(
            (
                score,
                {
                    "chunk_id": row.get("id") or "",
                    "title": title,
                    "knowledge_type": ktype,
                    "url": url,
                    "content": content,
                    "match_source": "direct_supabase_text",
                },
            )
        )

    scored_matches.sort(key=lambda item: item[0], reverse=True)
    return [chunk for _, chunk in scored_matches[:limit]]


def needs_direct_text_fallback(question, vector_chunks):
    if not vector_chunks:
        return True

    person_name = person_query_name(question)
    if person_name:
        name_key = normalize_person_name(person_name)
        searchable = normalized_lookup_text("\n".join(chunk.get("content", "") for chunk in vector_chunks[:3]))
        return name_key not in searchable

    top_distance = vector_chunks[0].get("distance")
    return isinstance(top_distance, (int, float)) and top_distance > 1.2


def chunk_key(chunk):
    return (
        chunk.get("chunk_id") or "",
        chunk.get("title") or "",
        chunk.get("url") or "",
    )


def placement_boost_score(chunk):
    title = chunk.get("title", "").lower()
    content = chunk.get("content", "").lower()
    url = chunk.get("url", "").lower()
    searchable = f"{title}\n{content}"

    score = sum(4 for term in PLACEMENT_BOOST_TERMS if term in searchable)
    score += sum(12 for term in PLACEMENT_PRIORITY_TITLE_TERMS if term in title)
    score += sum(
        15
        for phrase in PLACEMENT_PRIORITY_CONTENT_PHRASES
        if phrase in content
    )
    score += sum(10 for term in PLACEMENT_PRIORITY_URL_TERMS if term in url)
    return score


def normalize_package_value(value_text):
    value = float(value_text)
    if 100 <= value <= 999 and value.is_integer():
        digits = str(int(value))
        trailing_value = int(digits[-2:])
        if 10 <= trailing_value <= 99:
            return float(trailing_value)
        value = float(f"{digits[0]}.{digits[1:]}")
    return value


def infer_student_and_program(text, match_start):
    # Try structured key-value parsing first (e.g. from CSV, XLSX, SQLite DB)
    student_match = re.search(r"(?:student name|student|name)\s*:\s*([^,\n|]+)", text, re.I)
    program_match = re.search(r"(?:branch|program|department|specialization)\s*:\s*([^,\n|]+)", text, re.I)
    
    student = student_match.group(1).strip() if student_match else ""
    program = program_match.group(1).strip() if program_match else ""
    
    if student or program:
        return clean_student_name(student) or "Not specified", program or "Not specified"

    # Fall back to original line-by-line proximity search
    prefix = text[:match_start]
    lines = [line.strip() for line in prefix.splitlines() if line.strip()]
    recent_lines = lines[-8:]

    program = ""
    student = ""
    for line in reversed(recent_lines):
        if not program and re.search(r"\bb\.?\s*tech\b|computer science|electronics|information technology|cyber security|cse", line, re.I):
            program = clean_text(line)
            continue
        if not student and not re.search(r"ctc|lpa|b\.?\s*tech|source url|knowledge type|placement|previous year|title:", line, re.I):
            student = clean_text(line)
        if student and program:
            break

    return clean_student_name(student) or "Not specified", program or "Not specified"


def clean_student_name(name):
    name = clean_text(name)
    if re.match(r"^[A-Z][A-Z][a-z]", name):
        name = name[1:]
    return name


def extract_package_records(chunks):
    records = []
    seen = set()

    for chunk in chunks:
        content = chunk.get("content", "")
        for match in PACKAGE_VALUE_PATTERN.finditer(content):
            value = normalize_package_value(match.group(1))
            student, program = infer_student_and_program(content, match.start())
            key = (student.lower(), program.lower(), value)
            if key in seen:
                continue
            seen.add(key)
            records.append(
                {
                    "student": student,
                    "program": program,
                    "package": value,
                    "title": chunk.get("title", ""),
                }
            )

    records.sort(key=lambda record: record["package"], reverse=True)
    return records


def format_lpa(value):
    return f"{value:g} LPA"


def build_package_summary(records):
    if not records:
        return ""

    lines = ["Structured package summary:"]
    for record in records:
        lines.extend(
            [
                f"Student: {record['student']}",
                f"Program: {record['program']}",
                f"Package: {format_lpa(record['package'])}",
                "",
            ]
        )
    return "\n".join(lines).strip()


def direct_placement_answer(question):
    if not is_placement_query(question):
        return ""

    chunks = placement_keyword_search(limit=12) or keyword_search(question, limit=12)
    if not chunks:
        return "I don't have placement information in the current MIT Bengaluru data."

    records = extract_package_records(chunks)
    
    # Check if the query specifically mentions any student name from the records
    normalized_question = question.lower()
    student_matches = []
    seen_students = set()
    for record in records:
        student_name = record.get("student", "")
        if student_name and student_name.lower() in normalized_question:
            if student_name.lower() not in seen_students:
                seen_students.add(student_name.lower())
                student_matches.append(record)
                
    if student_matches:
        lines = []
        for record in student_matches:
            lines.append(
                f"Based on the available MIT Bengaluru placement data, {record['student']} is listed as a "
                f"{record['program']} student with a CTC/package of {format_lpa(record['package'])}."
            )
        return "\n".join(lines)

    recruiters = extract_recruiter_entities(chunks)
    lines = ["Based on the available MIT Bengaluru placement data:"]

    if records:
        lines.append("")
        lines.append("Package records found:")
        for index, record in enumerate(records[:8], start=1):
            lines.append(
                f"{index}. {record['student']} - {record['program']} - {format_lpa(record['package'])}"
            )

    if recruiters:
        lines.append("")
        lines.append("Recruiters/companies mentioned:")
        lines.append(", ".join(recruiters[:20]))

    if not records and not recruiters:
        lines.append("")
        lines.append("Relevant placement notes:")
        for chunk in chunks[:3]:
            snippet = truncate_text(chunk.get("content", ""), 350)
            if snippet:
                lines.append(f"- {snippet}")

    return "\n".join(lines)


def package_records_for_person(records, person_name):
    if not person_name:
        return []
    person_key = normalize_person_name(person_name)
    return [
        record
        for record in records
        if normalize_person_name(record.get("student", "")) == person_key
        or all(term in normalize_person_name(record.get("student", "")).split() for term in person_key.split())
    ]


def person_placement_answer(records, person_name):
    matches = package_records_for_person(records, person_name)
    if not matches:
        return ""
    record = matches[0]
    return (
        f"Based on the available MIT Bengaluru placement data, {record['student']} is listed as a "
        f"{record['program']} student with a CTC/package of {format_lpa(record['package'])}."
    )


def faculty_aggregation_chunks():
    chunks = []
    faculty_markers = [
        "assistant professor",
        "associate professor",
        "senior assistant professor",
        "professor",
        "faculty",
        "hod",
        "head of the department",
        "dean",
        "director",
    ]
    for chunk in placement_dataset_chunks:
        searchable = f"{chunk.get('title', '')}\n{chunk.get('content', '')}".lower()
        if any(term in searchable for term in faculty_markers):
            chunks.append(chunk)
    return chunks


def extract_person_entities(chunks):
    people = {}
    honorific_pattern = re.compile(
        r"\b(?:Dr\.?|Mr\.?|Ms\.?|Prof\.?)\s+(?:(?!(?:Dr|Mr|Ms|Prof)\.?\b)[A-Z][A-Za-z.]+)(?:\s+(?!(?:Dr|Mr|Ms|Prof)\.?\b)[A-Z][A-Za-z.]+){0,3}"
    )
    role_pattern = re.compile(
        r"(senior assistant professor|assistant professor|associate professor|professor|head of the department|hod|dean|director|coordinator|chairperson|member|speaker|student|faculty)",
        re.I,
    )

    for chunk in chunks:
        lines = [line.strip(" |") for line in chunk.get("content", "").splitlines() if line.strip()]
        for index, line in enumerate(lines):
            for match in honorific_pattern.finditer(line):
                name = clean_text(match.group(0)).rstrip(" .")
                if len(name.split()) < 2:
                    continue

                nearby = " ".join(lines[index : index + 3])
                role_match = role_pattern.search(nearby)
                role = role_match.group(0) if role_match else ""
                category = classify_person_entity(role, nearby)
                key = re.sub(r"^(dr|mr|ms|prof)\.?\s+", "", name.lower()).strip()
                if key not in people:
                    people[key] = {"name": name, "role": role, "category": category}
                elif role and not people[key]["role"]:
                    people[key]["role"] = role
                    people[key]["category"] = category

    return list(people.values())


def all_classified_people():
    global classified_people_cache
    if classified_people_cache is None:
        classified_people_cache = extract_person_entities(placement_dataset_chunks)
    return classified_people_cache


def classify_person_entity(role, context):
    role_text = (role or "").lower()
    if role_text == "student":
        return "Student"
    if role_text == "member":
        return "Committee Member"
    if role_text == "coordinator":
        return "Coordinator"
    if role_text == "speaker":
        return "Speaker"
    text = f"{role} {context}".lower()
    if "director" in text:
        return "Director"
    if "hod" in text or "head of the department" in text:
        return "HOD"
    if "dean" in text:
        return "Dean"
    if "professor" in text or "faculty" in text:
        return "Faculty"
    if "coordinator" in text:
        return "Coordinator"
    if "speaker" in text:
        return "Speaker"
    if "student" in text:
        return "Student"
    if "chairperson" in text or "committee" in text or re.search(r"\bmember\b", text):
        return "Committee Member"
    return "Unclassified"


def faculty_entities():
    global faculty_entities_cache
    if faculty_entities_cache is not None:
        return faculty_entities_cache

    allowed_roles = {
        "professor",
        "assistant professor",
        "associate professor",
        "senior assistant professor",
        "hod",
        "head of the department",
        "dean",
        "director",
    }
    people = extract_person_entities(faculty_aggregation_chunks())
    faculty = []
    seen = set()
    for person in people:
        role = (person.get("role") or "").lower()
        if not any(item in role for item in allowed_roles):
            continue
        key = re.sub(r"^(dr|mr|ms|prof)\.?\s+", "", person["name"].lower()).strip()
        if key in seen:
            continue
        seen.add(key)
        faculty.append(person)
    faculty_entities_cache = faculty
    return faculty


def entity_counts():
    committee_chunks = [
        chunk
        for chunk in placement_dataset_chunks
        if "committee" in f"{chunk.get('title', '')}\n{chunk.get('content', '')}".lower()
    ]
    event_chunks = [
        chunk
        for chunk in placement_dataset_chunks
        if "speaker" in f"{chunk.get('title', '')}\n{chunk.get('content', '')}".lower()
    ]
    committee_people = extract_person_entities(committee_chunks)
    speaker_people = extract_person_entities(event_chunks)
    counts = {
        "faculty": len(faculty_entities()),
        "student": len(extract_package_records(placement_keyword_search(limit=30))),
        "speaker": sum(1 for person in speaker_people if person.get("category") == "Speaker"),
        "committee": sum(1 for person in committee_people if person.get("category") == "Committee Member"),
    }
    return counts


def requested_range(question, default_page_size=50):
    normalized = question.lower()
    explicit = re.search(r"\b(\d+)\s*(?:-|to)\s*(\d+)\b", normalized)
    if explicit:
        start = max(1, int(explicit.group(1)))
        end = max(start, int(explicit.group(2)))
        return start - 1, end

    size_match = re.search(r"\bnext\s+(\d+)\b|\bmore\s+(\d+)\b", normalized)
    page_size = default_page_size
    if size_match:
        page_size = int(next(group for group in size_match.groups() if group))

    if re.search(r"\b(next|more|continue|show more|show next)\b", normalized):
        start = pagination_state["last_end_index"]
        return start, start + page_size

    return 0, default_page_size


def pagination_entity_type(question):
    normalized = question.lower()
    if "faculty" in normalized or "professor" in normalized:
        return "faculty"
    if "placed" in normalized or "placement" in normalized or "student" in normalized:
        return "placed_students"
    if "recruiter" in normalized or "company" in normalized or "companies" in normalized:
        return "recruiters"
    if "committee member" in normalized or ("committee" in normalized and "member" in normalized):
        return "committee_members"
    if "committee" in normalized:
        return "committees"
    if is_academic_program_query(question) or "course" in normalized or "program" in normalized:
        return "courses"
    if re.search(r"\b(next|more|continue|show more|show next)\b", normalized):
        return pagination_state.get("entity_type")
    return None


def is_pagination_request(question):
    normalized = question.lower()
    return bool(
        re.search(r"\b(\d+)\s*(?:-|to)\s*(\d+)\b", normalized)
        or re.search(r"\b(next|more|continue|show more|show next)\b", normalized)
    )


def pagination_items(entity_type, question):
    if entity_type == "faculty":
        return faculty_entities()
    if entity_type == "placed_students":
        records = extract_package_records(placement_keyword_search(limit=30))
        return [
            {
                "name": record["student"],
                "role": f"{record['program']} - {format_lpa(record['package'])}",
                "category": "Student",
            }
            for record in records
        ]
    if entity_type == "recruiters":
        return [{"name": name, "role": "", "category": "Recruiter"} for name in extract_recruiter_entities(keyword_search(question, limit=30))]
    if entity_type == "committees":
        return [{"name": name, "role": "", "category": "Committee"} for name in extract_committee_names(committee_chunks())]
    if entity_type == "committee_members":
        return [
            {"name": item["person"], "role": item.get("role", ""), "category": "Committee Member"}
            for item in committee_relationships().values()
        ]
    if entity_type == "courses":
        return [
            {
                "name": f"{record['program_type']} {record['department']}"
                + (f" ({record['specialization']})" if record.get("specialization") else ""),
                "role": "",
                "category": "Program",
            }
            for record in extract_program_records()
        ]
    return []


def save_pagination_state(entity_type, items, start, end, page_size):
    pagination_state.update(
        {
            "entity_type": entity_type,
            "full_result_list": items,
            "last_start_index": start,
            "last_end_index": end,
            "page_size": page_size,
        }
    )
    print("pagination state saved:", True)
    print("pagination entity type:", entity_type)


def format_paginated_items(title, items, question, entity_type, page_size=50):
    start, end = requested_range(question, page_size)
    total = len(items)
    if start >= total:
        print("requested range:", f"{start + 1}-{end}")
        print("returned range:", "none")
        print("next page available:", False)
        return f"No more {entity_type.replace('_', ' ')} records are available."

    end = min(end, total)
    page = items[start:end]
    save_pagination_state(entity_type, items, start, end, end - start)
    print("requested range:", f"{start + 1}-{end}")
    print("returned range:", f"{start + 1}-{end}")
    print("next page available:", end < total)

    lines = [title]
    if total > len(page):
        lines.append(f"Showing {start + 1}-{end} of {total} results.")
    for index, entity in enumerate(page, start=start + 1):
        role = f" - {entity['role']}" if entity.get("role") else ""
        lines.append(f"{index}. {entity['name']}{role}")
    return "\n".join(lines)


def format_entity_page(title, entities, question, page_size=50):
    entity_type = pagination_entity_type(question) or aggregation_type(question)
    if entity_type == "faculty_staff":
        entity_type = "faculty"
    elif entity_type == "placement_students":
        entity_type = "placed_students"
    return format_paginated_items(title, entities, question, entity_type, page_size)


def direct_pagination_answer(question):
    if not is_pagination_request(question):
        return ""
    entity_type = pagination_entity_type(question)
    if not entity_type:
        return ""
    items = pagination_items(entity_type, question)
    if not items and pagination_state.get("entity_type") == entity_type:
        items = pagination_state.get("full_result_list", [])
    if not items:
        return ""
    title = f"Here are the requested {entity_type.replace('_', ' ')} records:"
    return format_paginated_items(title, items, question, entity_type, pagination_state.get("page_size", 50))


def extract_recruiter_entities(chunks):
    recruiters = set()
    for chunk in chunks:
        content = chunk.get("content", "")
        for line in content.splitlines():
            if re.search(r"recruiter|company|companies", line, re.I):
                parts = re.split(r"[,;|•]+", line)
                for part in parts:
                    candidate = clean_text(part)
                    if (
                        2 <= len(candidate) <= 60
                        and not re.search(r"recruiter|company|companies|major|placement", candidate, re.I)
                    ):
                        recruiters.add(candidate)
    return sorted(recruiters)


def clean_academic_value(value):
    value = clean_text(value)
    value = re.sub(r"\s*[:|].*$", "", value)
    value = re.sub(r"\b(?:Admission|Courses?|Eligibility|Fees?|Fee|MAHE|MIT Bengaluru|Manipal).*$", "", value, flags=re.I)
    value = re.sub(r"^[^\w(]+|[^\w)]+$", "", value)
    value = re.sub(r"\s+", " ", value).strip()
    if value.count("(") > value.count(")"):
        value += ")"
    if value.count(")") > value.count("("):
        value = value.rstrip(")")
    return value


def normalize_program_type(text):
    if re.search(r"\b(?:b\.?\s*tech|btech|bachelor of technology)\b", text, re.I):
        return "B.Tech"
    if re.search(r"\b(?:m\.?\s*tech|mtech|master of technology)\b", text, re.I):
        return "M.Tech"
    if re.search(r"\b(?:m\.?\s*sc|msc|master of science)\b", text, re.I):
        return "M.Sc"
    if re.search(r"\b(?:ph\.?\s*d|phd|doctoral)\b", text, re.I):
        return "Ph.D"
    return ""


def program_record(program_type, department, specialization=""):
    department = clean_academic_value(department)
    specialization = clean_academic_value(specialization)
    if not program_type or not department:
        return None
    if not is_valid_program_department(department):
        return None
    return {
        "program_type": program_type,
        "department": department,
        "specialization": specialization,
    }


def is_valid_program_department(department):
    if not 3 <= len(department) <= 90:
        return False
    if re.search(
        r"^(overview|duration|course structure|important links|program list|source url|technology|the|in|all btech|bachelor of technology|master of technology|academic year|program semester detail)$",
        department,
        re.I,
    ):
        return False
    if re.search(r"\b(click here|apply now|students will|graduates|career|curriculum|semester|credits|opportunities|requirements|includes the following|leading universities)\b", department, re.I):
        return False
    if len(department.split()) > 8:
        return False
    if len(department.split()) == 1 and not re.search(r"robotics|mathematics|computing", department, re.I):
        return False
    return bool(
        re.search(
            r"computer|electronics|communication|information|technology|robotics|artificial|cyber|data|vlsi|mathematics|computing|mechanical|science|engineering|research|cloud|blockchain|iot|vision",
            department,
            re.I,
        )
    )


def parse_program_candidate(text):
    program_type = normalize_program_type(text)
    if not program_type:
        return None

    candidate = clean_text(text)
    candidate = re.sub(r"^Title:\s*", "", candidate, flags=re.I)
    candidate = re.sub(r"\s*\|.*$", "", candidate)
    candidate = re.sub(r"\s*:\s*(?:Admission|Courses?|Eligibility|Fee).*$", "", candidate, flags=re.I)
    candidate = re.sub(
        r"^(?:B\.?\s*Tech|BTech|Bachelor of Technology|M\.?\s*Tech|MTech|Master of Technology|M\.?\s*Sc|MSc|Master of Science|Ph\.?\s*D|PhD)\s*(?:in)?\s*",
        "",
        candidate,
        flags=re.I,
    )
    candidate = clean_academic_value(candidate)
    if candidate.startswith("(") and candidate.endswith(")"):
        candidate = candidate[1:-1].strip()
    if not candidate:
        return None

    specialization = ""
    paren_match = re.search(r"\(([^)]+)\)", candidate)
    if paren_match:
        specialization = paren_match.group(1)
        candidate = re.sub(r"\s*\([^)]+\)", "", candidate).strip()
    if " - " in candidate:
        candidate, specialization = [part.strip() for part in candidate.split(" - ", 1)]

    return program_record(program_type, candidate, specialization)


def add_program_record(records, record):
    if not record:
        return
    if re.search(r"\bcourse\s*-\s*(bachelor|master) of technology\b", record["department"], re.I):
        return
    if record["department"].lower() == "computer science":
        record = {**record, "department": "Computer Science and Engineering"}
    if record["department"].lower() == "ee & vlsi technology":
        record = {**record, "department": "Electronics Engineering", "specialization": "VLSI Design and Technology"}
    if record["department"].lower() == "electronics and communication":
        record = {**record, "department": "Electronics and Communication Engineering"}
    if record["department"].lower() == "electronics and computer":
        record = {**record, "department": "Electronics and Computer Engineering"}
    if record["department"].lower() == "electronics & communications":
        record = {**record, "department": "Electronics and Communication Engineering"}
    key_department = re.sub(r"\s+", " ", record["department"].lower().replace("&", "and"))
    key = (
        record["program_type"].lower(),
        key_department,
        record.get("specialization", "").lower(),
    )
    records[key] = record


def course_title_candidates(text):
    candidates = []
    for raw_line in text.splitlines():
        line = clean_text(raw_line.strip("# -*"))
        if not line or len(line) > 160:
            continue
        if re.search(
            r"\b(?:B\.?\s*Tech|BTech|M\.?\s*Tech|MTech)\b.*(?:Computer|Information|Electronics|Communication|Cyber|Artificial|Data|Mathematics|Computing|VLSI|Robotics)",
            line,
            re.I,
        ):
            candidates.append(line)
    return candidates


def extract_program_records():
    records = {}
    chunks = placement_dataset_chunks or dataset_chunks
    for chunk in chunks:
        title = chunk.get("title", "")
        content = chunk.get("content", "")
        url = chunk.get("url", "")
        is_program_chunk = (
            chunk.get("knowledge_type") == "program"
            or "program-list" in url.lower()
            or re.search(r"\b(?:b\.?\s*tech|m\.?\s*tech|btech|mtech|msc|ph\.?\s*d)\b", title, re.I)
        )
        if not is_program_chunk:
            continue

        if not re.search(r"^List of\b", title, re.I):
            add_program_record(records, parse_program_candidate(title))
        for candidate in course_title_candidates(content):
            add_program_record(records, parse_program_candidate(candidate))
        for line in content.splitlines():
            original_line = line.strip()
            line_clean = clean_text(original_line.strip(" -*#"))
            if not line_clean or len(line_clean) > 700:
                continue
            is_program_bullet = original_line.lstrip().startswith("*") and re.search(
                r"\b(?:b\.?\s*tech|m\.?\s*tech|btech|mtech|master of technology|bachelor of technology|msc|m\.?\s*sc|ph\.?\s*d)\b",
                line_clean,
                re.I,
            )
            is_program_heading = original_line.lstrip().startswith("###") and len(line_clean) <= 140 and re.search(
                r"^(?:B\.?\s*Tech|BTech|Bachelor of Technology|M\.?\s*Tech|MTech|Master of Technology|M\.?\s*Sc|MSc|Ph\.?\s*D|PhD)\b",
                line_clean,
                re.I,
            )
            if is_program_bullet or is_program_heading:
                add_program_record(records, parse_program_candidate(line_clean))
            if "ph.d" in line_clean.lower() or "phd" in line_clean.lower():
                area_text = re.split(r"to name a few", line_clean, flags=re.I, maxsplit=1)[-1]
                for part in re.split(r",|\band\b", area_text):
                    if re.search(r"artificial|machine|vision|cloud|data|blockchain|iot|comput", part, re.I):
                        add_program_record(records, program_record("Ph.D", "Research", part))

    return sorted(
        records.values(),
        key=lambda item: (item["program_type"], item["department"], item.get("specialization", "")),
    )


def extract_academic_units():
    units = {"Department": {}, "School": {}}
    chunks = placement_dataset_chunks or dataset_chunks
    pattern = re.compile(r"\b(Department|School) of ([A-Z][A-Za-z &,./()-]{3,90})", re.I)
    for chunk in chunks:
        searchable_meta = f"{chunk.get('title', '')}\n{chunk.get('url', '')}\n{chunk.get('knowledge_type', '')}".lower()
        if chunk.get("knowledge_type") not in {"program", "faculty"} and "department-faculty" not in searchable_meta:
            continue
        for line in f"{chunk.get('title', '')}\n{chunk.get('content', '')}".splitlines():
            if not re.search(r"\b(?:Department|School) of\b", line, re.I):
                continue
            line = clean_text(line)
            if len(line) > 300:
                continue
            for match in pattern.finditer(line):
                unit_type = match.group(1).title()
                name = clean_academic_value(match.group(2))
                name = re.split(r"\b(?:organized|organizes|is organizing|has organized|at MIT|MIT Bengaluru|Bengaluru)\b", name, flags=re.I)[0].strip(" ,.")
                if not name or len(name) > 80:
                    continue
                if re.search(r"^(the|this|all|next|recent|various)$", name, re.I):
                    continue
                if re.search(r"\b(?:NIT|University|Govt|Club|IEEE|Student branch|Dr\.?|Assistant Professor|offers|following programs|collaboration|Aalborg|Rouen|Boston|Massachusetts)\b", name, re.I):
                    continue
                if re.search(r"\bfirst year\b", name, re.I):
                    continue
                if unit_type == "School" and "computer engineering" not in name.lower():
                    continue
                if not re.search(r"computer|electronics|communication|information|science|humanities|management|mathematics|physics|chemistry|civil|mechanical|electrical", name, re.I):
                    continue
                if name.lower() in {"electronics & communications", "electronics and communications"}:
                    name = "Electronics and Communication Engineering"
                unit_key = re.sub(r"\s+", " ", name.lower().replace("&", "and"))
                units[unit_type][unit_key] = name
    return {
        unit_type: sorted(values.values())
        for unit_type, values in units.items()
        if values
    }


def academic_program_answer(question):
    programs = extract_program_records()
    units = extract_academic_units()
    if not programs and not units:
        return ""

    grouped = {}
    for record in programs:
        grouped.setdefault(record["program_type"], []).append(record)

    total_programs = len(programs)
    course_entities = pagination_items("courses", question)
    normalized_question = question.lower()
    if "btech" in normalized_question or "b.tech" in normalized_question:
        btech_count = len(grouped.get("B.Tech", []))
        lines = [f"Based on the available MIT Bengaluru data, I found {btech_count} B.Tech programs:"]
        for record in grouped.get("B.Tech", []):
            specialization = f" ({record['specialization']})" if record.get("specialization") else ""
            lines.append(f"- {record['department']}{specialization}")
    else:
        lines = [f"Based on the available MIT Bengaluru data, MIT Bengaluru offers the following programs/courses ({total_programs} found):"]
        for program_type in ["B.Tech", "M.Tech", "M.Sc", "Ph.D"]:
            records = grouped.get(program_type, [])
            if not records:
                continue
            lines.append("")
            lines.append(f"{program_type} programs ({len(records)}):")
            for record in records:
                specialization = f" ({record['specialization']})" if record.get("specialization") else ""
                lines.append(f"- {record['department']}{specialization}")

    if "btech" in normalized_question or "b.tech" in normalized_question:
        print("course query detected: True")
        print("course titles found:", [f"{record['program_type']} {record['department']}" for record in grouped.get("B.Tech", [])])
        print("course count:", len(grouped.get("B.Tech", [])))
        save_pagination_state("courses", course_entities, 0, min(len(course_entities), 50), 50)
        print("requested range:", f"1-{min(len(course_entities), 50)}")
        print("returned range:", f"1-{min(len(course_entities), 50)}")
        print("next page available:", len(course_entities) > 50)
        return "\n".join(lines)

    if units:
        lines.append("")
        lines.append("Academic units/departments identified:")
        for unit_type in ["School", "Department"]:
            for name in units.get(unit_type, []):
                lines.append(f"- {unit_type} of {name}")

    print("course query detected: True")
    print("course titles found:", [f"{record['program_type']} {record['department']}" for record in programs])
    print("course count:", total_programs)
    save_pagination_state("courses", course_entities, 0, min(len(course_entities), 50), 50)
    print("requested range:", f"1-{min(len(course_entities), 50)}")
    print("returned range:", f"1-{min(len(course_entities), 50)}")
    print("next page available:", len(course_entities) > 50)
    return "\n".join(lines)


def role_lookup_answer(question):
    normalized = question.lower()
    role_terms = []
    role_kind = ""
    if "hod" in normalized or "head of" in normalized:
        role_kind = "hod"
        role_terms.extend(["hod", "head of the department", "head"])
    if "dean" in normalized:
        role_kind = "dean"
        role_terms.append("dean")
    if "director" in normalized:
        role_kind = "director"
        role_terms.append("director")
    if "coordinator" in normalized:
        role_kind = "coordinator"
        role_terms.append("coordinator")

    dept_terms = expand_department_terms(question)
    dept_short = ""
    for short in ["ece", "cse", "it", "soce"]:
        if re.search(rf"\b{short}\b", normalized):
            dept_short = short
            break

    def table_cells(line):
        return [cell.strip().strip("*") for cell in line.split("|") if cell.strip().strip("*")]

    def name_from_cells(cells):
        for cell in cells:
            if re.search(r"\b(?:Dr|Prof|Mr|Ms)\.?\s+[A-Z][A-Za-z. ]+", cell):
                return re.sub(r"\s+", " ", cell).strip()
        return ""

    def role_from_cells(cells, fallback):
        for cell in cells:
            cell_clean = re.sub(r"\s+", " ", cell).strip()
            cell_lower = cell_clean.lower()
            if any(role in cell_lower for role in role_terms):
                return cell_clean
        return fallback

    def readable_hod_role(text, fallback):
        text_lower = text.lower()
        if dept_short and f"hod-{dept_short}" in text_lower:
            return f"HOD-{dept_short.upper()}"
        if dept_short and re.search(rf"head of (?:the )?{dept_short} department", text_lower):
            return f"Head of the {dept_short.upper()} Department"
        if re.search(r"head of the department", text_lower):
            return "Head of the Department"
        return fallback

    def hod_mentions_from_text(text):
        if role_kind != "hod" or not dept_short:
            return []
        person = r"(?:Dr|Prof|Mr|Ms)\.?\s+[A-Z][A-Za-z.]+(?:\s+[A-Z][A-Za-z.]+){0,3}"
        dept_pattern = re.escape(dept_short)
        if dept_short == "ece":
            dept_pattern = r"(?:ece|electronics\s*&?\s*communications?|electronics\s+and\s+communications?)"
        elif dept_short == "cse":
            dept_pattern = r"(?:cse|computer\s+science(?:\s*&?\s*engineering)?)"
        elif dept_short == "it":
            dept_pattern = r"(?:it|information\s+technology)"

        patterns = [
            (rf"\b({person})\b\s*,?\s*(?:Associate Professor,?\s*)?(?:&\s*)?Ho?D-?{re.escape(dept_short)}\b", f"HOD-{dept_short.upper()}"),
            (rf"\b({person})\b[^.\n|]{{0,80}}\bHead of (?:the )?{dept_pattern} Department\b", f"Head of the {dept_short.upper()} Department"),
            (rf"\b({person})\b[^.\n|]{{0,80}}\bHo?D,?\s*Department of {dept_pattern}\b", f"HOD, Department of {dept_short.upper()}"),
        ]
        found = []
        for pattern, role in patterns:
            for match in re.finditer(pattern, text, re.I):
                found.append((clean_text(match.group(1)), role))
        return found

    matches = []
    match_by_person = {}

    def normalize_person_key(name):
        key = re.sub(r"^(?:dr|mr|ms|prof)\.?\s+", "", name.lower()).strip()
        key = re.sub(r"[^a-z0-9\s]", " ", key)
        key = re.sub(r"\s+", " ", key).strip()
        parts = key.split()
        if len(parts) > 2 and all(len(part) == 1 for part in parts[1:-1]):
            key = f"{parts[0]} {''.join(parts[1:-1])} {parts[-1]}"
        if len(parts) > 1 and all(len(part) == 1 for part in parts[1:]):
            key = f"{parts[0]} {''.join(parts[1:])}"
        return key

    def add_match(name, role):
        name = clean_text(name).strip(" ,.")
        role = clean_text(role).strip(" ,.")
        if not name or not role:
            return
        person_key = normalize_person_key(name)
        if person_key not in match_by_person:
            match_by_person[person_key] = {"name": name, "roles": [], "aliases": set()}
            matches.append(match_by_person[person_key])
        match_by_person[person_key]["aliases"].add(name)
        if role not in match_by_person[person_key]["roles"]:
            match_by_person[person_key]["roles"].append(role)

    if role_kind == "hod" and dept_short:
        exact_role = f"HOD-{dept_short.upper()}"
        for chunk in placement_dataset_chunks:
            for line in chunk.get("content", "").splitlines():
                if exact_role.lower() not in line.lower():
                    continue
                if "|" not in line:
                    continue
                cells = table_cells(line)
                name = name_from_cells(cells)
                if not name:
                    continue
                role = role_from_cells(cells, exact_role)
                add_match(name, role)

    for chunk in placement_dataset_chunks:
        content = chunk.get("content", "")
        lines = [line for line in content.splitlines() if line.strip()]
        for index, line in enumerate(lines):
            window = " ".join(lines[max(0, index - 2) : index + 3])
            window_lower = window.lower()
            if not any(role in window_lower for role in role_terms):
                continue
            same_record_text = line if "|" in line else window
            same_record_lower = same_record_text.lower()
            if dept_terms and not any(term in same_record_lower for term in dept_terms):
                continue
            if role_kind == "hod" and "|" not in line:
                for name, role in hod_mentions_from_text(window):
                    add_match(name, role)
                continue
            cells = table_cells(line)
            if not cells:
                cells = table_cells(window)
            name = name_from_cells(cells)
            if not name:
                name_match = re.search(r"\b(?:Dr|Prof|Mr|Ms)\.?\s+[A-Z][A-Za-z. ]{2,80}", window)
                name = re.sub(r"\s+", " ", name_match.group(0)).strip(" ,") if name_match else ""
            if not name:
                continue
            role = role_from_cells(cells, role_terms[0].upper())
            if role_kind == "hod" and "hod" not in role.lower() and "head" not in role.lower():
                role = readable_hod_role(window, "HOD")
            add_match(name, role)

    if matches:
        if role_kind == "hod" and len(matches) > 1:
            dept_label = dept_short.upper() if dept_short else "the requested department"
            descriptions = [
                f"{match['name']} is mentioned as {', '.join(match['roles'])}"
                for match in matches[:6]
            ]
            return (
                f"The available MIT Bengaluru data mentions more than one {dept_label} HOD-related reference. "
                + "; ".join(descriptions)
                + "."
            )
        match = matches[0]
        return f"{match['name']} is listed as {', '.join(match['roles'])} in the available MIT Bengaluru data."
    return ""


def committee_chunks():
    return [
        chunk
        for chunk in placement_dataset_chunks
        if re.search(
            r"committee|squad|grievance redressal|complaint committee",
            f"{chunk.get('title', '')}\n{chunk.get('content', '')}",
            re.I,
        )
    ]


def extract_committee_names(chunks):
    names = {}
    pattern = re.compile(
        r"\b([A-Z][A-Za-z &/-]*(?:Committee|Squad|Cell|Council))(?:\s*\([A-Z]+\))?(?:-MIT)?",
        re.I,
    )
    for chunk in chunks:
        lines = f"{chunk.get('title', '')}\n{chunk.get('content', '')}".splitlines()
        for line in lines:
            if re.search(r"https?://|/content/|www\.|\.edu", line, re.I):
                continue
            for match in pattern.finditer(line):
                name = clean_committee_name(match.group(1))
                if not is_valid_committee_name(name):
                    continue
                key = name.lower()
                names[key] = name
    return sorted(names.values())


def clean_committee_name(name):
    name = clean_text(name).replace("-MIT", "").strip(" -")
    name = re.sub(r"^(composition of|members of|designation in)\s+", "", name, flags=re.I)
    name = re.sub(r"^.*-\s*(Working committee)$", r"\1", name, flags=re.I)
    name = re.sub(r"\bCompalint\b", "Complaint", name, flags=re.I)
    name = re.sub(r"\bComplaints Committee\b", "Complaint Committee", name, flags=re.I)
    if name.lower() == "working committee":
        name = "Working Committee"
    return name


def is_valid_committee_name(name):
    if len(name) < 8:
        return False
    if re.search(r"\b(a|the|this|once|who|members|activities|wonderful|foreign|commitment|excell|chancell)\b", name, re.I):
        return False
    if name.lower() in {"committee", "the committee", "a committee"}:
        return False
    return bool(
        re.search(
            r"anti-ragging|internal complaint|grievance redressal|quality assurance|student activity|core committee|organizing committee|class committee|working committee|squad|cell|council",
            name,
            re.I,
        )
    )


def committee_question_kind(question):
    normalized = question.lower()
    if re.search(r"\b(?:dr|mr|ms|prof)\.?\s+", normalized):
        return "person_membership"
    if any(term in normalized for term in ["who is in", "who are in", "who is on", "who are on", "members of", "member of"]):
        return "members"
    return "names"


def matching_committee_name(question, names):
    normalized = question.lower()
    best_name = ""
    best_score = 0
    for name in names:
        terms = [term for term in re.findall(r"[a-z]+", name.lower()) if term not in {"committee", "squad", "cell", "council"}]
        score = sum(1 for term in terms if term in normalized)
        if score > best_score:
            best_name = name
            best_score = score
    return best_name


def committee_relationships():
    relationships = {}
    chunks = committee_chunks()
    all_names = extract_committee_names(chunks)
    for chunk in chunks:
        chunk_names = extract_committee_names([chunk])
        committee_name = chunk_names[0] if chunk_names else matching_committee_name(chunk.get("title", ""), all_names)
        if not committee_name:
            continue
        section_text = bounded_committee_section(chunk, committee_name)
        people = extract_person_entities([{"content": section_text}])
        for person in people:
            if person.get("category") not in {"Committee Member", "Coordinator", "Director", "HOD", "Faculty", "Student"}:
                continue
            nearby = section_text.lower()
            if re.search(r"ctc|lpa|package|placed|placement record|recruiter|highest package", nearby):
                continue
            key = person["name"].lower()
            relationships.setdefault(key, {"person": person["name"], "committees": set(), "role": person.get("role", "")})
            relationships[key]["committees"].add(committee_name)
    return relationships


def bounded_committee_section(chunk, committee_name):
    lines = chunk.get("content", "").splitlines()
    start_index = 0
    committee_terms = [term for term in re.findall(r"[a-z]+", committee_name.lower()) if term not in {"committee", "cell", "squad", "council"}]
    for index, line in enumerate(lines):
        lowered = line.lower()
        if committee_name.lower() in lowered or all(term in lowered for term in committee_terms):
            start_index = index
            break

    stop_pattern = re.compile(
        r"placement|placement statistics|previous year placements|major recruiters|ctc|lpa|package|workshop|event|conference|recruiters|students placed|visisonics ai|program|b\.tech placement",
        re.I,
    )
    heading_pattern = re.compile(r"^[A-Z][A-Za-z0-9 &/-]{5,}$")
    section_lines = []
    for line in lines[start_index:]:
        if section_lines and (stop_pattern.search(line) or (heading_pattern.match(line.strip()) and "committee" not in line.lower() and "squad" not in line.lower() and "cell" not in line.lower())):
            break
        if stop_pattern.search(line):
            break
        if is_valid_committee_member_line(line):
            section_lines.append(line)
        elif "committee" in line.lower() or "squad" in line.lower() or "cell" in line.lower():
            section_lines.append(line)
    return "\n".join(section_lines)


def is_valid_committee_member_line(line):
    if re.search(r"ctc|lpa|package|placed|placement record|recruiter|highest package|b\.tech", line, re.I):
        return False
    return bool(
        re.search(r"\|\s*(?:Dr|Mr|Ms|Prof)\.?\s+|^\s*[-*]\s*(?:Dr|Mr|Ms|Prof)\.?\s+|(?:Dr|Mr|Ms|Prof)\.?\s+[A-Z]", line)
        and re.search(r"chairperson|member|officer|advisor|coordinator|director|hod|faculty|student|email|@|phone|\|", line, re.I)
    )


def committee_answer(question):
    chunks = committee_chunks()
    names = extract_committee_names(chunks)
    kind = committee_question_kind(question)
    relationships = committee_relationships()

    if kind == "person_membership":
        terms = [
            term
            for term in name_terms_from_question(question)
            if term not in {"committee", "committees", "member", "members", "what"}
        ]
        matches = [
            item
            for key, item in relationships.items()
            if all(term in key for term in terms)
        ]
        if matches:
            lines = []
            for item in matches:
                lines.append(f"{item['person']} is associated with: {', '.join(sorted(item['committees']))}.")
            return "\n".join(lines)

    if kind == "members":
        committee_name = matching_committee_name(question, names)
        member_rows = []
        for item in relationships.values():
            if not committee_name or committee_name in item["committees"]:
                member_rows.append({"name": item["person"], "role": item.get("role", ""), "category": "Committee Member"})
        seen = set()
        member_rows = [row for row in member_rows if not (row["name"].lower() in seen or seen.add(row["name"].lower()))]
        return format_paginated_items(
            f"Committee members for {committee_name or 'the matching committee'}:",
            member_rows,
            question,
            "committee_members",
        )

    committee_entities = [{"name": name, "role": "", "category": "Committee"} for name in names]
    return format_paginated_items(
        "The available MIT Bengaluru data lists these committees:",
        committee_entities,
        question,
        "committees",
    )


def build_aggregation_summary(question, package_records):
    agg_type = aggregation_type(question)
    if agg_type == "placement_students" and package_records:
        entities = [
            {
                "name": record["student"],
                "role": f"{record['program']} - {format_lpa(record['package'])}",
                "category": "Student",
            }
            for record in package_records
        ]
        return format_entity_page("Based on the available placement records:", entities, question)

    if agg_type == "faculty_staff":
        people = faculty_entities()
        title = (
            f"Based on the available MIT Bengaluru data, I found {len(people)} faculty/staff names mentioned. "
            "This may not be the complete official faculty count."
        )
        return format_entity_page(title, people, question)

    if agg_type == "recruiters":
        recruiter_chunks = keyword_search(question, limit=30)
        recruiters = extract_recruiter_entities(recruiter_chunks)
        if recruiters:
            entities = [{"name": name, "role": "", "category": "Recruiter"} for name in recruiters]
            return format_paginated_items(
                f"Recruiter/company names found in the available MIT Bengaluru data: {len(recruiters)}",
                entities,
                question,
                "recruiters",
            )

    if agg_type == "committee_members":
        return committee_answer(question)

    return ""


def direct_aggregation_answer(question):
    agg_type = aggregation_type(question)
    if agg_type == "placement_students":
        chunks = keyword_search(question, limit=30)
        records = extract_package_records(chunks)
        if records:
            return build_aggregation_summary(question, records)

    return build_aggregation_summary(question, [])


def combine_chunks(
    exact_chunk,
    vector_chunks,
    question,
    placement_chunks=None,
    keyword_chunks=None,
    exact_phrase_chunks=None,
):
    if is_placement_query(question):
        vector_chunks = sorted(
            vector_chunks,
            key=placement_boost_score,
            reverse=True,
        )

    combined = []
    seen = set()
    prioritized_chunks = []
    if exact_chunk:
        prioritized_chunks.append(exact_chunk)
    prioritized_chunks.extend(exact_phrase_chunks or [])
    if is_placement_query(question):
        prioritized_chunks.extend(placement_chunks or [])
    prioritized_chunks.extend(vector_chunks)
    prioritized_chunks.extend(keyword_chunks or [])

    for chunk in prioritized_chunks:
        key = chunk_key(chunk)
        if key in seen:
            continue
        seen.add(key)
        combined.append(chunk)

    return combined


def build_context(chunks, question):
    if not chunks:
        return ""

    if is_faculty_query(question) and chunks[0].get("knowledge_type") == "faculty":
        context_parts = []
        for chunk in chunks:
            snippet = find_relevant_snippet(chunk["content"], question)
            profile_summary = format_faculty_profile_fields(extract_faculty_profile_fields(chunk["content"]))
            context_parts.append(
                "\n".join(
                    [item for item in [
                        f"Title: {chunk['title']}",
                        f"Knowledge type: {chunk['knowledge_type']}",
                        f"Source URL: {chunk.get('url', '')}",
                        f"Structured faculty profile:\n{profile_summary}" if profile_summary else "",
                        f"Relevant profile text: {snippet}",
                    ] if item]
                )
            )
        return truncate_text("\n\n".join(context_parts), MAX_TOTAL_CONTEXT_CHARS)

    if is_placement_query(question):
        context_parts = []
        relevant_chunks = sorted(
            chunks,
            key=placement_boost_score,
            reverse=True,
        )[:10]
        for chunk in relevant_chunks:
            context_parts.append(
                "\n".join(
                    [
                        f"Title: {chunk['title']}",
                        f"Knowledge type: {chunk['knowledge_type']}",
                        f"Placement content: {truncate_text(chunk['content'], MAX_PLACEMENT_SNIPPET_CHARS)}",
                    ]
                )
            )
        max_context = (
            MAX_AGGREGATION_CONTEXT_CHARS
            if is_aggregation_query(question) or is_list_style_query(question) or is_numerical_query(question)
            else MAX_PLACEMENT_CONTEXT_CHARS
        )
        return truncate_text("\n\n".join(context_parts), max_context)

    context_parts = []
    for chunk in chunks:
        context_parts.append(
            "\n".join(
                [
                    f"Title: {chunk['title']}",
                    f"Knowledge type: {chunk['knowledge_type']}",
                    f"Relevant content: {truncate_text(chunk['content'], MAX_NORMAL_SNIPPET_CHARS)}",
                ]
            )
        )
    return truncate_text("\n\n".join(context_parts), MAX_NORMAL_CONTEXT_CHARS)


def build_prompt(question, context):
    faculty_instruction = ""
    if "Structured faculty profile:" in context:
        faculty_instruction = """
For faculty profile questions, answer in 4-6 concise lines and include available full name, designation, department/school, role/responsibilities, expertise/research areas, and email/contact. If a field is not in the context, say it is not specified in the available data.
Use a clear field-style format for faculty answers. Do not collapse a faculty profile into one sentence when structured profile fields are available.
"""
    return f"""You are MIT Bengaluru AI Assistant.

Use only the provided context.

Answer clearly and helpfully.

{faculty_instruction}

If the question asks for a list, provide all available items from the context.

If the question asks about placements, packages, CTC, students, recruiters, or companies, extract and summarize all available placement-related records.

If numerical values are present, compare them when needed.

Do not say data is unavailable if relevant information exists in the provided context.

If only partial information is available, say "Based on the available data..." and then answer.

Default to 4-8 useful lines unless the user asks for a short answer.

Context:
{context}

Question:
{question}

Answer:"""


def log_performance(question, retrieval_time, context_length, generation_time, total_time):
    print(f"Question: {question}")
    print(f"Retrieval Time: {retrieval_time:.2f}s")
    print(f"Context Length: {context_length} chars")
    if context_length > MAX_TOTAL_CONTEXT_CHARS:
        print("WARNING: Context length exceeds 1800 characters.")
    print(f"Generation Time: {generation_time:.2f}s")
    print(f"Total Time: {total_time:.2f}s")


def user_key_from_request(http_request):
    forwarded_for = http_request.headers.get("x-forwarded-for", "")
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip()
    return http_request.client.host if http_request.client else "unknown"


def is_user_rate_limited(user_key):
    now = time.time()
    timestamps = [
        timestamp
        for timestamp in request_timestamps_by_user.get(user_key, [])
        if now - timestamp < USER_RATE_WINDOW_SECONDS
    ]
    if len(timestamps) >= USER_RATE_LIMIT:
        request_timestamps_by_user[user_key] = timestamps
        print("user rate limit triggered:", user_key)
        return True
    timestamps.append(now)
    request_timestamps_by_user[user_key] = timestamps
    return False


def cached_answer(question):
    cache_key = question.strip().lower()
    item = response_cache.get(cache_key)
    if not item:
        print("cache miss:", cache_key)
        return None
    if time.time() - item["timestamp"] > CACHE_DURATION_SECONDS:
        response_cache.pop(cache_key, None)
        print("cache miss:", cache_key)
        return None
    print("cache hit:", cache_key)
    return item["answer"]


def save_cached_answer(question, answer):
    response_cache[question.strip().lower()] = {
        "answer": answer,
        "timestamp": time.time(),
    }


def groq_fallback_answer(exc):
    text = f"{type(exc).__name__}: {exc}".lower()
    if "429" in text or "rate limit" in text or "rate_limit" in text:
        print("Groq 429 received:", exc)
        print("fallback response used:", GROQ_BUSY_RESPONSE)
        return GROQ_BUSY_RESPONSE
    if "timeout" in text or "timed out" in text:
        print("fallback response used:", GROQ_TIMEOUT_RESPONSE)
        return GROQ_TIMEOUT_RESPONSE
    if "connection" in text or "temporar" in text or "service unavailable" in text or "503" in text or "502" in text:
        print("fallback response used:", GROQ_BUSY_RESPONSE)
        return GROQ_BUSY_RESPONSE
    print("fallback response used:", GROQ_BUSY_RESPONSE)
    return GROQ_BUSY_RESPONSE


def general_knowledge_answer(question):
    completion = groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a helpful educational AI assistant. Answer the user's general question clearly and accurately. "
                    "Keep the answer beginner-friendly unless the user asks for advanced detail."
                ),
            },
            {
                "role": "user",
                "content": question,
            },
        ],
        temperature=0.2,
        max_completion_tokens=300,
    )
    return completion.choices[0].message.content.strip()


def is_time_sensitive_general_question(question):
    normalized = question.lower()
    return bool(
        re.search(r"\b(latest|current|today|now|recent|newest|live|this week|this month|this year)\b", normalized)
        and re.search(r"\b(movie|film|news|release|released|price|score|weather|stock|election|result)\b", normalized)
    )


def live_search_unavailable_answer():
    return (
        "I don't have live real-time web search in this chatbot backend right now. "
        "To answer latest/current questions accurately, a web-search API needs to be added."
    )


dataset_chunks = load_dataset_chunks()
placement_dataset_chunks = load_placement_dataset_chunks()


@app.get("/")
def home():
    return {
        "message": "MIT Bengaluru Chatbot API is running",
        "docs": "/docs",
        "collection": COLLECTION_NAME,
    }


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    print("Unhandled chatbot error:", type(exc).__name__, str(exc))
    return JSONResponse(
        status_code=200,
        content={
            "answer": (
                "The chatbot had trouble processing that request. "
                "Please try again in a few seconds or ask the question another way."
            )
        },
    )


@app.on_event("startup")
def startup_check_supabase():
    print("startup check: Supabase URL:", SUPABASE_URL)
    print("startup check: Storage bucket name:", STORAGE_BUCKET_NAME)
    print("startup check: embedding model:", EMBEDDING_MODEL)
    verify_supabase_connection()


@app.post("/chat")
def chat(request: ChatRequest, http_request: Request):
    total_start = time.perf_counter()
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=422, detail="Question cannot be empty.")
        
    # Normalize 'bangalore' -> 'bengaluru' to ensure matching against the database
    question = re.sub(r"\bbangalore\b", "bengaluru", question, flags=re.I)

    # 1. Decorum & Safety Filter
    def is_inappropriate_query(q):
        flagged_words = {
            "sex", "sexual", "porn", "xxx", "naked", "nude", "orgasm", "penis", 
            "vagina", "boobs", "asshole", "bitch", "fuck", "dick", "bastard", 
            "slut", "whore", "cunt", "hentai", "erotic", "kamini", "saala",
            "condom", "rape", "masturbation", "blowjob"
        }
        normalized = re.sub(r"[^a-z\s]", " ", q.lower())
        words = set(normalized.split())
        return not words.isdisjoint(flagged_words)

    if is_inappropriate_query(question):
        print("Flagged inappropriate/sexual query:", question)
        return {
            "answer": (
                "As the MIT Bengaluru AI Assistant, I only answer questions related to academics, "
                "college life, and general education. Please keep your queries respectful."
            )
        }

    print("received query:", question)
    person_name = person_query_name(question)
    person_query_detected = bool(person_name)
    mit_entity_match_found = mit_person_entity_match_found(person_name) if person_query_detected else False
    mit_specific = is_mit_specific_query(question) or person_query_detected
    query_type = "MIT_RAG" if mit_specific else "GENERAL_KNOWLEDGE"
    print("query_type:", query_type)
    print("person_query_detected:", person_query_detected)
    print("mit_entity_match_found:", mit_entity_match_found)
    print("retrieval_skipped:", not mit_specific)
    print("fallback_used:", not mit_specific)

    user_key = user_key_from_request(http_request)
    if is_user_rate_limited(user_key):
        return {"answer": USER_RATE_LIMIT_RESPONSE}

    cached = cached_answer(question)
    if cached is not None:
        return {"answer": cached}

    if is_simple_greeting(question):
        total_time = time.perf_counter() - total_start
        log_performance(question, 0.0, 0, 0.0, total_time)
        save_cached_answer(question, GREETING_RESPONSE)
        return {"answer": GREETING_RESPONSE}

    if not mit_specific:
        if is_time_sensitive_general_question(question):
            answer = live_search_unavailable_answer()
            total_time = time.perf_counter() - total_start
            print("answer_source: general_fallback_no_live_search")
            log_performance(question, 0.0, 0, 0.0, total_time)
            save_cached_answer(question, answer)
            return {"answer": answer}

        generation_start = time.perf_counter()
        try:
            answer = general_knowledge_answer(question)
        except Exception as exc:
            answer = groq_fallback_answer(exc)
            generation_time = time.perf_counter() - generation_start
            total_time = time.perf_counter() - total_start
            log_performance(question, 0.0, 0, generation_time, total_time)
            return {"answer": answer}

        generation_time = time.perf_counter() - generation_start
        total_time = time.perf_counter() - total_start
        log_performance(question, 0.0, 0, generation_time, total_time)

        final_answer = answer or "No answer returned."
        print("answer_source: general_fallback")
        save_cached_answer(question, final_answer)
        return {"answer": final_answer}

    numerical_query = is_numerical_query(question)
    placement_query = is_placement_query(question)
    aggregation_query = is_aggregation_query(question)
    list_query = is_list_style_query(question)
    broad_query = numerical_query or placement_query or aggregation_query or list_query
    semantic_limit = 8 if numerical_query else 5
    keyword_limit = 25 if broad_query else 8
    final_chunk_limit = MAX_HYBRID_AGGREGATION_CHUNKS if broad_query else MAX_HYBRID_NORMAL_CHUNKS

    retrieval_start = time.perf_counter()
    question_embedding = embedding_model.encode(question).tolist()
    
    vector_chunks = []
    if supabase_client:
        try:
            response = supabase_client.rpc("match_chunks", {
                "query_embedding": question_embedding,
                "match_threshold": -1.0, # -1.0 Cosine similarity threshold (retrieves top matches regardless of score)
                "match_count": semantic_limit
            }).execute()
            supabase_chunks = response.data or []
            for chunk in supabase_chunks:
                vector_chunks.append({
                    "chunk_id": chunk.get("id") or "",
                    "title": chunk.get("title") or "",
                    "knowledge_type": chunk.get("knowledge_type") or "",
                    "url": chunk.get("url") or "",
                    "content": chunk.get("content") or "",
                    "distance": 1.0 - (chunk.get("similarity") or 0.0),
                })
        except Exception as db_exc:
            print("Supabase vector search failed:", db_exc)
            
    retrieval_time = time.perf_counter() - retrieval_start

    pagination_answer = direct_pagination_answer(question)
    if pagination_answer:
        total_time = time.perf_counter() - total_start
        print("answer_source: RAG")
        log_performance(question, 0.0, len(pagination_answer), 0.0, total_time)
        save_cached_answer(question, pagination_answer)
        return {"answer": pagination_answer}

    if is_role_lookup_query(question):
        answer = role_lookup_answer(question)
        if answer:
            total_time = time.perf_counter() - total_start
            print("answer_source: RAG")
            log_performance(question, 0.0, len(answer), 0.0, total_time)
            save_cached_answer(question, answer)
            return {"answer": answer}

    if is_academic_program_query(question):
        answer = academic_program_answer(question)
        if answer:
            total_time = time.perf_counter() - total_start
            print("answer_source: RAG")
            log_performance(question, 0.0, len(answer), 0.0, total_time)
            save_cached_answer(question, answer)
            return {"answer": answer}

    if is_placement_query(question):
        answer = direct_placement_answer(question)
        if answer:
            total_time = time.perf_counter() - total_start
            log_performance(question, 0.0, len(answer), 0.0, total_time)
            save_cached_answer(question, answer)
            return {"answer": answer}

    if is_aggregation_query(question):
        answer = direct_aggregation_answer(question)
        if answer:
            counts = entity_counts()
            print("Aggregation query detected: True")
            print("Aggregation type:", aggregation_type(question))
            print("faculty count:", counts["faculty"])
            print("student count:", counts["student"])
            print("speaker count:", counts["speaker"])
            print("committee count:", counts["committee"])
            if aggregation_type(question) == "committee_members":
                names = extract_committee_names(committee_chunks())
                relationships = committee_relationships()
                print("Entity Type Detected:", "COMMITTEE")
                print("Committee Count:", len(names))
                print("Committee Names:", names)
                print("Member Count:", len(relationships))
            print("final context length:", len(answer))
            total_time = time.perf_counter() - total_start
            print("answer_source: RAG")
            log_performance(question, 0.0, len(answer), 0.0, total_time)
            save_cached_answer(question, answer)
            return {"answer": answer}

    exact_chunk = exact_faculty_match(question)
    placement_chunks = placement_keyword_search(limit=8) if placement_query else []
    keyword_chunks = keyword_search(question, limit=keyword_limit)
    exact_phrase_chunks = exact_phrase_search(question, limit=5)
    direct_text_chunks = direct_chroma_text_search(None, question, limit=8) if needs_direct_text_fallback(question, vector_chunks) else []
    print("direct text fallback used:", bool(direct_text_chunks))
    print("direct text fallback titles:", [chunk.get("title", "") for chunk in direct_text_chunks])
    combined_chunks = combine_chunks(
        exact_chunk,
        vector_chunks,
        question,
        placement_chunks=placement_chunks,
        keyword_chunks=direct_text_chunks + keyword_chunks,
        exact_phrase_chunks=exact_phrase_chunks,
    )[:final_chunk_limit]
    context = build_context(combined_chunks, question)
    if is_faculty_query(question) and exact_chunk:
        direct_faculty_answer = faculty_profile_direct_answer(exact_chunk)
        if direct_faculty_answer:
            total_time = time.perf_counter() - total_start
            print("answer_source: RAG")
            log_performance(question, retrieval_time, len(direct_faculty_answer), 0.0, total_time)
            save_cached_answer(question, direct_faculty_answer)
            return {"answer": direct_faculty_answer}
    non_faculty_person_query = is_faculty_query(question) and not (
        exact_chunk and exact_chunk.get("knowledge_type") == "faculty"
    )
    package_records = extract_package_records(combined_chunks) if numerical_query or non_faculty_person_query else []
    if (placement_query or list_query or aggregation_type(question) == "placement_students") and not package_records:
        package_records = extract_package_records(combined_chunks)
    if person_query_detected and not package_records:
        package_records = extract_package_records(combined_chunks)
    direct_person_placement_answer = person_placement_answer(package_records, person_name)
    if direct_person_placement_answer:
        total_time = time.perf_counter() - total_start
        print("answer_source: RAG")
        log_performance(question, retrieval_time, len(direct_person_placement_answer), 0.0, total_time)
        save_cached_answer(question, direct_person_placement_answer)
        return {"answer": direct_person_placement_answer}
    package_summary = build_package_summary(package_records)
    aggregation_summary = build_aggregation_summary(question, package_records) if aggregation_query else ""
    structured_parts = []
    if package_summary:
        structured_parts.append(package_summary)
    if aggregation_summary and aggregation_summary != package_summary:
        structured_parts.append(aggregation_summary)

    if aggregation_query and aggregation_summary:
        counts = entity_counts()
        print("Aggregation query detected: True")
        print("Aggregation type:", aggregation_type(question))
        print("faculty count:", counts["faculty"])
        print("student count:", counts["student"])
        print("speaker count:", counts["speaker"])
        print("committee count:", counts["committee"])
        print("final context length:", len(aggregation_summary))
        total_time = time.perf_counter() - total_start
        print("answer_source: RAG")
        log_performance(question, retrieval_time, len(aggregation_summary), 0.0, total_time)
        save_cached_answer(question, aggregation_summary)
        return {"answer": aggregation_summary}

    if structured_parts:
        context = truncate_text(
            "\n\n".join(structured_parts) + f"\n\nRetrieved context:\n{context}",
            MAX_AGGREGATION_CONTEXT_CHARS if broad_query else MAX_PLACEMENT_CONTEXT_CHARS,
        )
    context_length = len(context)

    print("Semantic retrieved titles:", [chunk.get("title", "") for chunk in vector_chunks])
    print("Keyword retrieved titles:", [chunk.get("title", "") for chunk in keyword_chunks])
    print("Merged chunk count:", len(combined_chunks))
    print("Retrieved titles:", [chunk.get("title", "") for chunk in combined_chunks])
    print("Exact match used:", bool(exact_chunk))
    print("Placement/list query detected:", bool(placement_query or list_query))
    if placement_query:
        selected_placement_chunks = sorted(
            combined_chunks,
            key=placement_boost_score,
            reverse=True,
        )[:4]
        print("Placement query detected: True")
        print(
            "Retrieved placement titles:",
            [chunk.get("title", "") for chunk in selected_placement_chunks],
        )
        print(f"Placement context length: {context_length} chars")
    if numerical_query:
        highest = package_records[0] if package_records else None
        lowest = package_records[-1] if package_records else None
        print("Numerical query detected: True")
        print(
            "Package values extracted:",
            [format_lpa(record["package"]) for record in package_records],
        )
        print("Highest package found:", format_lpa(highest["package"]) if highest else "None")
        print("Lowest package found:", format_lpa(lowest["package"]) if lowest else "None")
        print("Chunks used:", [chunk.get("title", "") for chunk in combined_chunks[:8]])
    if aggregation_query:
        agg_entities = []
        if aggregation_type(question) == "faculty_staff":
            agg_entities = [person["name"] for person in extract_person_entities(faculty_aggregation_chunks())]
        elif package_records:
            agg_entities = [record["student"] for record in package_records]
        print("Aggregation query detected: True")
        print("Aggregation type:", aggregation_type(question))
        print("Extracted entity count:", len(set(agg_entities)))
        print("Extracted entity names:", list(dict.fromkeys(agg_entities))[:80])
    print("Extracted placement records:", package_records)
    print("Final context length:", context_length)
    if context_length > MAX_TOTAL_CONTEXT_CHARS:
        print("WARNING: Context length exceeds normal context limit.")

    # 2. Smart Fallback for Study-related / Academic queries
    if not context.strip():
        # Check if the user is asking a general study-related or academic query
        academic_keywords = {
            "roadmap", "syllabus", "learn", "study", "exam", "prepare", "explanation", 
            "explain", "what is", "how to", "code", "programming", "mathematics", 
            "physics", "chemistry", "algorithms", "engineering", "tutorial", "guide",
            "subject", "course", "curriculum", "career", "interview", "aptitude"
        }
        question_words = set(re.sub(r"[^a-z\s]", " ", question.lower()).split())
        is_academic = not question_words.isdisjoint(academic_keywords)
        
        if is_academic:
            print("No database context found. Bypassing RAG and falling back to general academic LLM response.")
            generation_start = time.perf_counter()
            try:
                completion = groq_client.chat.completions.create(
                    model=GROQ_MODEL,
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "You are an educational assistant for MIT Bengaluru students.\n"
                                "The student asked a general academic or study-related question that is not covered "
                                "in the university-specific database. Answer it clearly, accurately, and professionally.\n"
                                "Maintain the decorum of the college at all times."
                            )
                        },
                        {
                            "role": "user",
                            "content": question
                        }
                    ],
                    temperature=0.3,
                    max_completion_tokens=400,
                )
                answer = completion.choices[0].message.content.strip()
                print("answer_source: academic_general_fallback")
            except Exception as exc:
                answer = groq_fallback_answer(exc)
                
            generation_time = time.perf_counter() - generation_start
            total_time = time.perf_counter() - total_start
            log_performance(question, retrieval_time, 0, generation_time, total_time)
            save_cached_answer(question, answer)
            return {"answer": answer}
        else:
            # For college-specific questions not found in the DB
            total_time = time.perf_counter() - total_start
            log_performance(question, retrieval_time, context_length, 0.0, total_time)
            answer = "I don't have that specific MIT Bengaluru information in my database."
            print("answer_source: RAG_no_context_college_specific")
            save_cached_answer(question, answer)
            return {"answer": answer}

    prompt = build_prompt(question, context)
    generation_start = time.perf_counter()

    try:
        completion = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are MIT Bengaluru AI Assistant.\n\n"
                        "Use only the provided context.\n\n"
                        "Answer clearly and helpfully.\n\n"
                        "If the question asks for a list, provide all available items from the context.\n\n"
                        "If the question asks about placements, packages, CTC, students, recruiters, or companies, extract and summarize all available placement-related records.\n\n"
                        "When multiple numerical values are present:\n"
                        "* compare them when asked\n"
                        "* identify highest and lowest values\n"
                        "* perform simple reasoning and ranking\n"
                        "* answer directly\n"
                        "* do not say data is unavailable if the required values exist in the provided context.\n\n"
                        "If only partial information is available, say 'Based on the available data...' and then answer."
                    )
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.1,
            max_completion_tokens=300,
        )

        answer = completion.choices[0].message.content.strip()

    except Exception as exc:
        answer = groq_fallback_answer(exc)
        generation_time = time.perf_counter() - generation_start
        total_time = time.perf_counter() - total_start
        log_performance(question, retrieval_time, context_length, generation_time, total_time)
        return {"answer": answer}

    generation_time = time.perf_counter() - generation_start
    total_time = time.perf_counter() - total_start

    log_performance(
        question,
        retrieval_time,
        context_length,
        generation_time,
        total_time,
    )

    final_answer = answer or "No answer returned."
    print("answer_source: RAG")
    save_cached_answer(question, final_answer)
    return {
        "answer": final_answer
    }


@app.post("/upload")
def upload_knowledge_file(file: UploadFile = File(...)):
    if not supabase_admin_client:
        raise HTTPException(status_code=503, detail="Supabase admin/service client is not configured.")
        
    supported_extensions = {".json", ".txt", ".pdf", ".docx", ".csv", ".xlsx", ".db"}
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in supported_extensions:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported file format. Supported extensions: {', '.join(supported_extensions)}"
        )
        
    # Save the file temporarily
    temp_file_path = os.path.join(BASE_DIR, file.filename)
    try:
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        print(f"Uploaded file saved temporarily at: {temp_file_path}")
        
        # Run single file ingestion using the admin client (which uses service_role key)
        chunks_count = ingest.ingest_single_file(temp_file_path, supabase_admin_client)
        
        # Reload dataset chunks in memory
        global dataset_chunks, placement_dataset_chunks
        print("Knowledge base updated. Reloading in-memory chunks...")
        dataset_chunks = load_dataset_chunks()
        placement_dataset_chunks = load_placement_dataset_chunks()
            
    except Exception as e:
        print(f"Upload and ingestion failed: {e}")
        # Clean up file if it exists
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        raise HTTPException(status_code=500, detail=f"Failed to process and ingest file: {str(e)}")
        
    # Delete temporary file
    if os.path.exists(temp_file_path):
        os.remove(temp_file_path)
        
    return {
        "message": f"Successfully uploaded and ingested {file.filename}.",
        "chunks_created": chunks_count
    }


@app.delete("/delete")
def delete_knowledge_file(filename: str):
    if not supabase_admin_client:
        raise HTTPException(status_code=503, detail="Supabase admin/service client is not configured.")
        
    filename = filename.strip()
    if not filename:
        raise HTTPException(status_code=400, detail="Filename parameter is required.")
        
    deleted_db_count = 0
    try:
        # 1. Delete rows from the database (using admin client)
        print(f"Deleting database records for file: {filename}...")
        response = supabase_admin_client.table("mit_bengaluru_data").delete().eq("metadata->>source_file", filename).execute()
        if response.data:
            deleted_db_count = len(response.data)
            
        # 2. Delete file from storage (using admin client)
        print(f"Deleting file from storage bucket '{STORAGE_BUCKET_NAME}': {filename}...")
        try:
            supabase_admin_client.storage.from_(STORAGE_BUCKET_NAME).remove([filename])
            print("Successfully deleted from storage.")
        except Exception as storage_err:
            print(f"WARNING: Failed to delete {filename} from storage: {storage_err}")
            # Do not fail the request if the file is already deleted in storage but removed from DB
            
        # 3. Reload in-memory dataset chunks
        global dataset_chunks, placement_dataset_chunks
        print("Knowledge base updated. Reloading in-memory chunks...")
        dataset_chunks = load_dataset_chunks()
        placement_dataset_chunks = load_placement_dataset_chunks()
            
    except Exception as e:
        print(f"Delete operation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete file and records: {str(e)}")
        
    return {
        "message": f"Successfully deleted {filename} from database and storage.",
        "database_records_removed": deleted_db_count
    }


@app.get("/files")
def list_knowledge_files():
    if not supabase_admin_client:
        raise HTTPException(status_code=503, detail="Supabase admin/service client is not configured.")
        
    try:
        print(f"Fetching list of files from storage bucket '{STORAGE_BUCKET_NAME}'...")
        files = supabase_admin_client.storage.from_(STORAGE_BUCKET_NAME).list()
        
        file_list = []
        for f in files:
            name = f.get("name")
            if not name or name == ".placeholder":
                continue
            
            # Extract metadata safely
            meta = f.get("metadata") or {}
            size = meta.get("size") or f.get("size") or 0
            created_at = f.get("created_at") or f.get("updated_at") or "unknown"
            
            file_list.append({
                "name": name,
                "size": size,
                "created_at": created_at
            })
        return file_list
    except Exception as e:
        print(f"Failed to list files: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve files: {str(e)}")
