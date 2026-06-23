from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import settings
from app.middleware.exceptions import (
    AppException,
    app_exception_handler,
    http_exception_handler,
    request_validation_exception_handler,
    unhandled_exception_handler,
)
from app.middleware.middleware import APIKeyMiddleware, configure_rate_limiting

# --> ADDED CHAITANYA'S IMPORTS HERE <--
from app.routers import upload, audio_stream
from app.routers import upload, audio_stream, chat, mock_endpoints
from database import engine, Base
Base.metadata.create_all(bind=engine)




# Initialize the FastAPI app with metadata from config.py
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

app.add_middleware(APIKeyMiddleware)
configure_rate_limiting(app)

app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)
app.add_exception_handler(400, http_exception_handler)
app.add_exception_handler(401, http_exception_handler)
app.add_exception_handler(403, http_exception_handler)
app.add_exception_handler(404, http_exception_handler)
app.add_exception_handler(405, http_exception_handler)
app.add_exception_handler(422, request_validation_exception_handler)

# Set up CORS middleware to allow the frontend to communicate with the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace "*" with the actual frontend URL
    allow_credentials=True,
    allow_methods=["*"],  # Allows all HTTP methods (GET, POST, PUT, DELETE)
    allow_headers=["*"],  # Allows all headers
)

# --> REGISTERED CHAITANYA'S ROUTERS HERE <--
app.include_router(upload.router, prefix="/api", tags=["Uploads"])
app.include_router(audio_stream.router, prefix="/api", tags=["Audio"])
app.include_router(chat.router, prefix="/api", tags=["Chat"])
app.include_router(mock_endpoints.router)

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
