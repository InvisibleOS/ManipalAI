from fastapi import APIRouter, UploadFile, File, HTTPException
import os
import pdfplumber
from groq import Groq
from dotenv import load_dotenv
import json
import re

from app.services.file_handler import save_file  # 🔥 NEW IMPORT

load_dotenv()

router = APIRouter()

MAX_FILE_SIZE = 5 * 1024 * 1024
ALLOWED_TYPES = ["application/pdf"]

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def clean_text(text: str) -> str:
    return " ".join(text.split())


def analyze_resume(text: str):
    try:
        prompt = f"""
        Analyze this resume and return ONLY valid JSON.

        Format:
        {{
          "score": 0-100,
          "score_reason": "",
          "skills": [],
          "strengths": "",
          "weaknesses": "",
          "suggestions": ""
        }}

        Scoring criteria:
        - Structure (20)
        - Formatting (20)
        - Content quality (30)
        - Skills relevance (20)
        - Clarity (10)

        Resume:
        {text[:3000]}
        """

        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            temperature=0.2,
            messages=[{"role": "user", "content": prompt}]
        )

        raw_output = response.choices[0].message.content

        if not raw_output or raw_output.strip() == "":
            return {"error": "Empty AI response"}

        match = re.search(r"\{.*\}", raw_output, re.DOTALL)

        if match:
            return json.loads(match.group())
        else:
            return {"error": "Invalid JSON", "raw": raw_output}

    except Exception as e:
        return {"error": str(e)}


@router.post("/upload-resume")
async def upload_resume(file: UploadFile = File(...)):
    try:
        if file.content_type not in ALLOWED_TYPES:
            raise HTTPException(status_code=400, detail="Only PDF files allowed")

        content = await file.read()

        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail="File too large")

        if len(content) == 0:
            raise HTTPException(status_code=400, detail="Empty file")

        # 🔥 USE SERVICE (IMPORTANT CHANGE)
        file_path = save_file(file, content)

        extracted_text = ""

        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                extracted_text += page.extract_text() or ""

        cleaned_text = clean_text(extracted_text)

        # Save for streaming
        with open("latest_resume.txt", "w", encoding="utf-8") as f:
            f.write(cleaned_text)

        ai_result = analyze_resume(cleaned_text)

        with open("latest_score.json", "w") as f:
            json.dump(ai_result, f)

        return {
            "status": "success",
            "filename": file.filename,
            "preview": cleaned_text[:500],
            "analysis": ai_result
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))