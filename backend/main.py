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