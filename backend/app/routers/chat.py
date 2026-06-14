from fastapi import APIRouter, HTTPException
from app.schemas.chat import ChatRequest, ChatResponse

# Initialize the router
router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    Main entry point for the chatbot interactions. 
    Accepts a user message and returns the AI response.
    """
    try:
        # Extract data from the incoming payload
        user_message = request.message
        session = request.session_id
        
        # TODO: The AI Team will replace this placeholder with actual Groq LLM calls
        # For Week 2, we return a dummy response to prove the pipeline works
        dummy_reply = f"Backend received: '{user_message}'. AI engine is offline for maintenance."
        
        # Return the data strictly matching the ChatResponse schema
        return ChatResponse(
            response=dummy_reply,
            sources=["Backend System Test"]
        )
        
    except Exception as e:
        # Catch any unexpected errors so the server doesn't crash
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")