import os

import httpx
from fastapi import APIRouter, HTTPException

from app.schemas.chat import ChatRequest, ChatResponse

router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    try:
        ai_engine_url = os.getenv("AI_ENGINE_URL", "http://localhost:8000")
        async with httpx.AsyncClient(timeout=60.0) as client:
            res = await client.post(
                f"{ai_engine_url}/chat",
                json={"question": request.message}
            )
            res.raise_for_status()
            data = res.json()
            return ChatResponse(
                response=data.get("answer", "No response from AI engine"),
                sources=data.get("sources", [])
            )
    except httpx.RequestError:
        raise HTTPException(
            status_code=503,
            detail="Unable to connect to AI Engine. Please try again later.",
        )
    except httpx.HTTPStatusError as e:
        upstream_status = e.response.status_code
        raise HTTPException(
            status_code=502,
            detail=f"AI Engine returned HTTP {upstream_status}.",
        )
    except Exception:
        raise HTTPException(status_code=500, detail="Unexpected error while contacting AI Engine.")
