import os
import httpx
from fastapi import APIRouter, HTTPException
from app.schemas.chat import ChatRequest, ChatResponse

# Initialize the router
router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    Forwards the user's message to the external AI Engine and returns the response.
    """
    # Grab the URL from Render's environment variables
    ai_engine_url = os.getenv("AI_ENGINE_URL")
    
    if not ai_engine_url:
        raise HTTPException(status_code=500, detail="AI_ENGINE_URL environment variable is missing.")

    # Forward the request asynchronously so we don't block the server
    async with httpx.AsyncClient() as client:
        try:
            # Send the payload to the AI team's /chat endpoint
            response = await client.post(
                f"{ai_engine_url}/chat",
                json=request.model_dump()  # Converts the Pydantic model to a standard dictionary
            )
            response.raise_for_status()  # Catch 4xx or 5xx errors from the AI server
            
            # Extract the data
            ai_data = response.json()
            
            # Return it neatly packaged in our expected schema
            return ChatResponse(
                response=ai_data.get("response", "Error: AI returned an empty response."),
                sources=ai_data.get("sources", [])
            )
            
        except httpx.RequestError as e:
            raise HTTPException(status_code=503, detail=f"AI Engine is unreachable: {str(e)}")