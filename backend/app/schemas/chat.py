from pydantic import BaseModel
from typing import List, Optional

class ChatRequest(BaseModel):
    """
    Template for incoming messages from the user.
    """
    message: str
    session_id: Optional[str] = None  # Used later for tracking mock interview states

class ChatResponse(BaseModel):
    """
    Template for the AI's response sent back to the frontend.
    """
    response: str
    sources: Optional[List[str]] = []  # For citing textbooks, PDFs, or website links