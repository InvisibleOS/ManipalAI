"""Mock-interview conversation endpoint.

Powers the "Interview Mode" live voice experience in the frontend. Given the
conversation so far, it returns the interviewer's next short, spoken-style line
using Groq. Self-contained (Groq only) so it works wherever GROQ_API_KEY is set,
independent of the heavier RAG ai-engine.
"""
import asyncio
import os
from typing import List, Literal, Optional

from dotenv import load_dotenv
from fastapi import APIRouter
from groq import Groq
from pydantic import BaseModel, Field

load_dotenv()

router = APIRouter()

# Build the client lazily so the app still imports/starts without a key — the
# endpoint then returns a graceful fallback instead of crashing.
_groq_api_key = os.getenv("GROQ_API_KEY")
client = Groq(api_key=_groq_api_key) if _groq_api_key else None

INTERVIEW_MODEL = "llama-3.3-70b-versatile"
MAX_HISTORY_TURNS = 24


class Turn(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class InterviewRequest(BaseModel):
    history: List[Turn] = Field(default_factory=list)
    role: Optional[str] = None  # e.g. "Software Engineer", "Data Analyst"


class InterviewResponse(BaseModel):
    reply: str


def _system_prompt(role: Optional[str]) -> str:
    target = role.strip() if role and role.strip() else "a software engineering campus placement"
    return (
        "You are a warm but rigorous mock interviewer for MIT Bengaluru students, "
        f"conducting a spoken interview for {target}. "
        "Your replies are read aloud by a text-to-speech voice, so follow these rules strictly:\n"
        "- Reply in 1-3 short, natural, conversational sentences.\n"
        "- Ask exactly ONE question at a time.\n"
        "- Briefly acknowledge or react to the candidate's previous answer before asking the next question.\n"
        "- Move across topics over the interview: a quick intro, projects, technical depth, CS fundamentals, and behavioural situations.\n"
        "- If the candidate struggles, give a small hint or encouragement.\n"
        "- Output PLAIN SPOKEN TEXT only — no markdown, lists, headings, emojis, or stage directions.\n"
        "Open the interview by greeting the candidate by no name and asking your first question."
    )


def _generate(history: List[Turn], role: Optional[str]) -> str:
    messages = [{"role": "system", "content": _system_prompt(role)}]
    for turn in history[-MAX_HISTORY_TURNS:]:
        messages.append({"role": turn.role, "content": turn.content})
    if not history:
        messages.append({"role": "user", "content": "Please start the interview."})

    response = client.chat.completions.create(
        model=INTERVIEW_MODEL,
        temperature=0.6,
        max_tokens=220,
        messages=messages,
    )
    return (response.choices[0].message.content or "").strip()


@router.post("/interview", response_model=InterviewResponse)
async def interview(req: InterviewRequest) -> InterviewResponse:
    # Keeps the live UI flowing even if the model/key isn't available.
    opening_fallback = (
        "Welcome, and thanks for joining this mock interview. "
        "To start, could you tell me a little about yourself and a project you're proud of?"
    )

    if client is None:
        return InterviewResponse(reply=opening_fallback if not req.history else
                                 "Thanks for sharing. Could you walk me through that in a bit more detail?")

    try:
        reply = await asyncio.to_thread(_generate, req.history, req.role)
    except Exception as exc:  # noqa: BLE001 - degrade gracefully, never break the call loop
        print(f"[interview] generation failed: {exc}")
        reply = ""

    if not reply:
        reply = opening_fallback if not req.history else "Got it. Could you elaborate on your last point?"

    return InterviewResponse(reply=reply)
