from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import settings

# Initialize the FastAPI app with metadata from config.py
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Set up CORS middleware to allow the frontend to communicate with the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace "*" with the actual frontend URL
    allow_credentials=True,
    allow_methods=["*"],  # Allows all HTTP methods (GET, POST, PUT, DELETE)
    allow_headers=["*"],  # Allows all headers
)

# Root Health Check Route
@app.get("/", tags=["Health"])
async def root():
    """
    Base route to verify the API is running.
    """
    return {
        "message": "Welcome to the Manipal Chatbot Backend API!",
        "status": "Healthy",
        "version": settings.VERSION
    }