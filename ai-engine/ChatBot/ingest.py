import os
import sys
import json
import sqlite3
import pandas as pd
from pypdf import PdfReader
from docx import Document
from supabase import create_client, Client
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
STORAGE_BUCKET_NAME = "chatbot-assets"

def get_supabase_client() -> Client:
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        print("ERROR: SUPABASE_URL or SUPABASE_SERVICE_KEY is missing from environment variables.")
        print("Please configure them in your .env file.")
        sys.exit(1)
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

def chunk_text(text, chunk_size=1000, overlap=150):
    """Splits plain text into overlapping chunks of a specific character length."""
    chunks = []
    start = 0
    text_len = len(text)
    while start < text_len:
        end = min(start + chunk_size, text_len)
        chunks.append(text[start:end])
        if end == text_len:
            break
        start += (chunk_size - overlap)
    return chunks

def parse_txt(file_path):
    print(f"Parsing Text file: {file_path}")
    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()
    chunks = chunk_text(text)
    documents = []
    base_name = os.path.basename(file_path)
    for i, content in enumerate(chunks):
        documents.append({
            "chunk_id": f"{base_name}_{i}",
            "title": base_name,
            "knowledge_type": "text",
            "url": "",
            "content": content,
            "metadata": {
                "source_file": base_name,
                "chunk_index": i,
                "title": base_name,
                "knowledge_type": "text"
            }
        })
    return documents

def parse_pdf(file_path):
    print(f"Parsing PDF file: {file_path}")
    reader = PdfReader(file_path)
    documents = []
    base_name = os.path.basename(file_path)
    for page_num, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        if not text.strip():
            continue
        chunks = chunk_text(text)
        for chunk_idx, content in enumerate(chunks):
            documents.append({
                "chunk_id": f"{base_name}_p{page_num}_{chunk_idx}",
                "title": f"{base_name} - Page {page_num + 1}",
                "knowledge_type": "pdf",
                "url": "",
                "content": content,
                "metadata": {
                    "source_file": base_name,
                    "page_number": page_num + 1,
                    "chunk_index": chunk_idx,
                    "title": f"{base_name} - Page {page_num + 1}",
                    "knowledge_type": "pdf"
                }
            })
    return documents

def parse_docx(file_path):
    print(f"Parsing Word document: {file_path}")
    doc = Document(file_path)
    full_text = []
    for para in doc.paragraphs:
        full_text.append(para.text)
    text = "\n".join(full_text)
    chunks = chunk_text(text)
    documents = []
    base_name = os.path.basename(file_path)
    for i, content in enumerate(chunks):
        documents.append({
            "chunk_id": f"{base_name}_{i}",
            "title": base_name,
            "knowledge_type": "word",
            "url": "",
            "content": content,
            "metadata": {
                "source_file": base_name,
                "chunk_index": i,
                "title": base_name,
                "knowledge_type": "word"
            }
        })
    return documents

def parse_spreadsheet(file_path):
    print(f"Parsing Spreadsheet: {file_path}")
    if file_path.endswith('.csv'):
        df = pd.read_csv(file_path)
    else:
        df = pd.read_excel(file_path)
    
    documents = []
    base_name = os.path.basename(file_path)
    for index, row in df.iterrows():
        row_dict = row.to_dict()
        # Clean NaN/null values from dictionary for JSON storage
        row_dict = {k: str(v) for k, v in row_dict.items() if pd.notna(v)}
        content = ", ".join(f"{k}: {v}" for k, v in row_dict.items())
        
        chunk_id = f"{base_name}_row_{index}"
        metadata = {
            "source_file": base_name,
            "row_index": index + 1,
            "title": f"{base_name} - Row {index + 1}",
            "knowledge_type": "spreadsheet",
            **row_dict
        }
        documents.append({
            "chunk_id": chunk_id,
            "title": f"{base_name} - Row {index + 1}",
            "knowledge_type": "spreadsheet",
            "url": "",
            "content": content,
            "metadata": metadata
        })
    return documents

def parse_sqlite_db(file_path):
    print(f"Parsing SQLite DB: {file_path}")
    conn = sqlite3.connect(file_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [r[0] for r in cursor.fetchall()]
    
    documents = []
    base_name = os.path.basename(file_path)
    for table in tables:
        # Ignore internal sqlite tables
        if table.startswith("sqlite_"):
            continue
        cursor.execute(f"PRAGMA table_info({table});")
        columns = [c[1] for c in cursor.fetchall()]
        
        cursor.execute(f"SELECT * FROM {table};")
        rows = cursor.fetchall()
        for row_idx, row in enumerate(rows):
            row_dict = dict(zip(columns, row))
            row_dict = {k: str(v) for k, v in row_dict.items() if v is not None}
            content = f"Table: {table} | " + ", ".join(f"{k}: {v}" for k, v in row_dict.items())
            
            chunk_id = f"{base_name}_{table}_row_{row_idx}"
            metadata = {
                "source_file": base_name,
                "table_name": table,
                "row_index": row_idx + 1,
                "title": f"Table: {table} - Row {row_idx + 1}",
                "knowledge_type": "database_row",
                **row_dict
            }
            documents.append({
                "chunk_id": chunk_id,
                "title": f"Database: {base_name} | Table: {table}",
                "knowledge_type": "database_row",
                "url": "",
                "content": content,
                "metadata": metadata
            })
    conn.close()
    return documents

def parse_json(file_path):
    print(f"Parsing JSON file: {file_path}")
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    documents = []
    base_name = os.path.basename(file_path)
    
    # Specific MIT dataset format check
    if isinstance(data, dict) and ("documents" in data or "faq_documents" in data):
        print("Detected structured MIT Bengaluru RAG dataset format.")
        docs = list(data.get("documents", []))
        for index, item in enumerate(data.get("faq_documents", [])):
            content = "\n".join(
                part for part in [item.get("question") or "", item.get("answer") or ""] if part
            )
            docs.append({
                "chunk_id": item.get("chunk_id") or f"faq_{index}",
                "title": item.get("question") or "FAQ",
                "knowledge_type": "faq",
                "source_url": item.get("source_url") or "",
                "question": item.get("question") or "",
                "content": content,
                "answer": item.get("answer") or "",
            })
            
        for index, item in enumerate(docs):
            chunk_id = item.get("chunk_id") or f"chunk_{index}"
            
            # Form standard content text
            content = item.get("content") or ""
            if not content.startswith("Title:"):
                # Prepend title and type for better semantic quality
                title = item.get("title") or "Document"
                ktype = item.get("knowledge_type") or "policy"
                content = f"Title: {title}\nType: {ktype}\nContent:\n{content}"
            
            metadata = {
                "source_file": base_name,
                "title": item.get("title") or "",
                "url": item.get("source_url") or item.get("url") or "",
                "knowledge_type": item.get("knowledge_type") or "document",
            }
            # Add other custom keys to metadata
            for k, v in item.items():
                if k not in ["content", "chunk_id"]:
                    metadata[k] = str(v) if v is not None else ""
                    
            documents.append({
                "chunk_id": chunk_id,
                "title": item.get("title") or "JSON Document",
                "knowledge_type": item.get("knowledge_type") or "json",
                "url": item.get("source_url") or item.get("url") or "",
                "content": content,
                "metadata": metadata
            })
            
    # Generic JSON list of objects
    elif isinstance(data, list):
        for index, item in enumerate(data):
            content = item.get("content") or json.dumps(item)
            chunk_id = item.get("chunk_id") or f"{base_name}_{index}"
            metadata = {
                "source_file": base_name,
                "title": item.get("title") or f"{base_name} Item {index}",
                "knowledge_type": item.get("knowledge_type") or "json",
            }
            for k, v in item.items():
                if k not in ["content", "chunk_id"]:
                    metadata[k] = str(v) if v is not None else ""
            documents.append({
                "chunk_id": chunk_id,
                "title": metadata["title"],
                "knowledge_type": metadata["knowledge_type"],
                "url": item.get("url") or "",
                "content": content,
                "metadata": metadata
            })
            
    # Generic JSON single object
    elif isinstance(data, dict):
        content = json.dumps(data, indent=2)
        metadata = {
            "source_file": base_name,
            "title": base_name,
            "knowledge_type": "json",
        }
        for k, v in data.items():
            metadata[k] = str(v) if v is not None else ""
        documents.append({
            "chunk_id": f"{base_name}_root",
            "title": base_name,
            "knowledge_type": "json",
            "url": "",
            "content": content,
            "metadata": metadata
        })
    return documents

def upload_file_to_storage(supabase_client, local_path, bucket_name, storage_path):
    """Uploads a local file to Supabase Storage."""
    print(f"Uploading {local_path} to storage bucket '{bucket_name}' as '{storage_path}'...")
    try:
        # Check if bucket exists
        buckets = supabase_client.storage.list_buckets()
        bucket_names = [b.name for b in buckets]
        if bucket_name not in bucket_names:
            print(f"Creating storage bucket '{bucket_name}'...")
            supabase_client.storage.create_bucket(bucket_name, options={"public": True})
            
        with open(local_path, "rb") as f:
            supabase_client.storage.from_(bucket_name).upload(
                path=storage_path,
                file=f,
                file_options={"cache-control": "3600", "upsert": "true"}
            )
        print("Upload successful.")
    except Exception as e:
        print(f"WARNING: File upload to storage failed: {e}")
        print("The database records will still be ingested, but server-side file download won't be configured.")

def ingest_single_file(file_path, supabase_client=None):
    """Parses, embeds, and uploads a single knowledge base file to Supabase database and storage."""
    if supabase_client is None:
        supabase_client = get_supabase_client()
        
    ext = os.path.splitext(file_path)[1].lower()
    base_name = os.path.basename(file_path)
    
    # Process
    if ext == ".json":
        chunks = parse_json(file_path)
    elif ext == ".txt":
        chunks = parse_txt(file_path)
    elif ext == ".pdf":
        chunks = parse_pdf(file_path)
    elif ext == ".docx":
        chunks = parse_docx(file_path)
    elif ext in [".csv", ".xlsx"]:
        chunks = parse_spreadsheet(file_path)
    elif ext == ".db":
        chunks = parse_sqlite_db(file_path)
    else:
        raise ValueError(f"Unsupported file format: {ext}")
        
    if not chunks:
        print(f"No text chunks could be extracted from: {base_name}")
        return 0
        
    print(f"Extracted {len(chunks)} chunks from: {base_name}")
    print(f"Generating embeddings for: {base_name}...")
    model = SentenceTransformer(EMBEDDING_MODEL)
    texts = [chunk["content"] for chunk in chunks]
    embeddings = model.encode(texts, show_progress_bar=False).tolist()
    
    # Format database rows
    db_rows = []
    for index, chunk in enumerate(chunks):
        db_rows.append({
            "id": chunk["chunk_id"],
            "title": chunk["title"],
            "knowledge_type": chunk["knowledge_type"],
            "url": chunk["url"],
            "content": chunk["content"],
            "embedding": embeddings[index],
            "metadata": chunk["metadata"]
        })
        
    # Delete old database records for this file (to avoid duplicate chunks)
    print(f"Clearing old database records for: {base_name}...")
    try:
        supabase_client.table("mit_bengaluru_data").delete().eq("metadata->>source_file", base_name).execute()
    except Exception as e:
        print(f"WARNING: Database cleanup for '{base_name}' failed: {e}")
        
    # Upload to DB in batches
    batch_size = 100
    total_rows = len(db_rows)
    print(f"Uploading {total_rows} rows to Supabase database...")
    for i in range(0, total_rows, batch_size):
        batch = db_rows[i:i + batch_size]
        supabase_client.table("mit_bengaluru_data").upsert(batch).execute()
        
    # Upload raw file to storage
    upload_file_to_storage(supabase_client, file_path, STORAGE_BUCKET_NAME, base_name)
    
    print(f"Successfully finished ingestion for: {base_name}\n")
    return total_rows

def main():
    print("==================================================")
    print("MIT Bengaluru Multi-Format Dataset Ingestion Script")
    print("==================================================")
    
    supabase = get_supabase_client()
    
    # Scan the folder for supported files
    supported_extensions = {".json", ".txt", ".pdf", ".docx", ".csv", ".xlsx", ".db"}
    files_to_process = []
    
    for f in os.listdir(BASE_DIR):
        ext = os.path.splitext(f)[1].lower()
        if ext in supported_extensions:
            if f in ["chroma.sqlite3", "requirements.txt", "package.json"]:
                continue
            files_to_process.append(os.path.join(BASE_DIR, f))
            
    if not files_to_process:
        print("No supported files found to process in the backend folder.")
        print("Please place .json, .txt, .pdf, .docx, .csv, .xlsx, or .db files here.")
        sys.exit(0)
        
    print(f"Found {len(files_to_process)} files to process:")
    for f in files_to_process:
        print(f" - {os.path.basename(f)}")
        
    # Sync: Delete database records for files that have been removed from the local folder
    try:
        active_filenames = [os.path.basename(f) for f in files_to_process]
        print("\nSyncing database: checking for removed files...")
        res = supabase.table("mit_bengaluru_data").select("metadata->>source_file").execute()
        if res.data:
            db_files = set(row.get("source_file") for row in res.data if row.get("source_file"))
            files_to_delete = db_files - set(active_filenames)
            for f_name in files_to_delete:
                print(f" -> Deleting database records for removed file: {f_name}")
                supabase.table("mit_bengaluru_data").delete().eq("metadata->>source_file", f_name).execute()
    except Exception as sync_exc:
        print(f"WARNING: Database synchronization cleanup failed: {sync_exc}")

    # Process files individually
    total_chunks = 0
    for file_path in files_to_process:
        try:
            chunks_created = ingest_single_file(file_path, supabase)
            total_chunks += chunks_created
        except Exception as e:
            print(f"ERROR: Failed to ingest file {os.path.basename(file_path)}: {e}")
            
    print("==================================================")
    print(f"Ingestion complete. Successfully saved {total_chunks} chunks to Supabase.")
    print("==================================================")

if __name__ == "__main__":
    main()
