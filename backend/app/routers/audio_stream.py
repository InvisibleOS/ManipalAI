from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
import asyncio
from groq import Groq
import os
from dotenv import load_dotenv
import json

load_dotenv()

router = APIRouter()

# Build the Groq client only when a key is present, so the app (and this router)
# still import and start without a key — the WebSocket then reports a clean error
# instead of crashing the whole service at import time.
_groq_api_key = os.getenv("GROQ_API_KEY")
client = Groq(api_key=_groq_api_key) if _groq_api_key else None


async def ai_stream_generator():
    try:
        # 🔥 Load resume
        try:
            with open("latest_resume.txt", "r", encoding="utf-8") as f:
                resume_text = f.read()
        except:
            yield "No resume uploaded yet.\n"
            return

        # 🔥 Load score (single source of truth)
        try:
            with open("latest_score.json", "r") as f:
                score_data = json.load(f)
                score = score_data.get("score", "N/A")
                score_reason = score_data.get("score_reason", "")
        except:
            score = "N/A"
            score_reason = ""

        # 🔥 FINAL PROMPT (NO RE-SCORING)
        prompt = f"""
You are an ATS resume reviewer.

IMPORTANT:
The ATS score is already calculated.

Score: {score}/100  
Reason: {score_reason}

Explain this score and provide detailed analysis.

Format:

📊 Resume Analysis

🔹 ATS Score: {score}/100
🔹 Reason: {score_reason}

🔹 Structure Issues:
- ...

🔹 Formatting Problems:
- ...

🔹 Content Gaps:
- ...

🔹 Improvements:
- ...

🔹 Improved Summary:
...

Resume:
{resume_text[:2000]}
"""

        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            temperature=0.3,
            messages=[{"role": "user", "content": prompt}]
        )

        full_text = response.choices[0].message.content

        # 🔥 STREAM CLEANLY
        for line in full_text.split("\n"):
            yield line + "\n"
            await asyncio.sleep(0.05)

    except Exception as e:
        yield f"[Error: {str(e)}]\n"


@router.get("/stream-ai")
async def stream_ai():
    return StreamingResponse(
        ai_stream_generator(),
        media_type="text/plain"
    )


# ---------------------------------------------------------------------------
# Voice -> text WebSocket  (consumed by the frontend mic button in ChatInput)
# ---------------------------------------------------------------------------

WHISPER_MODEL = "whisper-large-v3-turbo"

# Map the browser MediaRecorder mimeType to a file extension Groq/Whisper accepts.
_EXT_BY_MIME = {
    "audio/webm": "webm",
    "audio/ogg": "ogg",
    "audio/mp4": "m4a",
    "audio/mpeg": "mp3",
    "audio/wav": "wav",
    "audio/x-wav": "wav",
}


def _ext_for_mime(mime: str) -> str:
    base = (mime or "").split(";", 1)[0].strip().lower()
    return _EXT_BY_MIME.get(base, "webm")


def _transcribe(audio: bytes, filename: str) -> str:
    """Blocking Groq Whisper call — run via asyncio.to_thread from the socket."""
    if client is None:
        raise RuntimeError("Speech-to-text is not configured (missing GROQ_API_KEY).")

    result = client.audio.transcriptions.create(
        file=(filename, audio),
        model=WHISPER_MODEL,
        response_format="text",
    )
    # response_format="text" yields a plain string; fall back to .text otherwise.
    text = result if isinstance(result, str) else getattr(result, "text", "")
    return (text or "").strip()


@router.websocket("/audio-stream")
async def audio_stream(websocket: WebSocket):
    """Receive streamed microphone audio and return a speech-to-text transcript.

    Protocol (matches frontend/src/components/ChatInput.tsx):
        client -> {"event":"start","mimeType":"audio/webm;codecs=opus"}
        client -> <binary audio chunks>
        client -> {"event":"stop"}
        server -> {"event":"transcript","transcript":"..."}
        server -> {"event":"done"}
        server -> {"event":"error","message":"..."}   (on failure)
    """
    await websocket.accept()
    buffer = bytearray()
    ext = "webm"

    try:
        while True:
            message = await websocket.receive()

            if message["type"] == "websocket.disconnect":
                return

            chunk = message.get("bytes")
            if chunk is not None:
                buffer.extend(chunk)
                continue

            text = message.get("text")
            if not text:
                continue

            try:
                payload = json.loads(text)
            except json.JSONDecodeError:
                continue

            event = payload.get("event")
            if event == "start":
                ext = _ext_for_mime(payload.get("mimeType", ""))
            elif event == "stop":
                if not buffer:
                    await websocket.send_json({"event": "error", "message": "No audio was received."})
                    return
                try:
                    transcript = await asyncio.to_thread(_transcribe, bytes(buffer), f"audio.{ext}")
                except Exception as exc:  # noqa: BLE001 - surface any failure to the client
                    await websocket.send_json({"event": "error", "message": f"Transcription failed: {exc}"})
                    return

                await websocket.send_json({"event": "transcript", "transcript": transcript})
                await websocket.send_json({"event": "done"})
                return
    except WebSocketDisconnect:
        return
    finally:
        try:
            await websocket.close()
        except RuntimeError:
            # Socket already closed by the client / a prior send — nothing to do.
            pass