import os

class Settings:
    """
    Core configuration settings for the backend.
    Later, we will use Pydantic to load .env variables here.
    """
    PROJECT_NAME: str = "Manipal Chatbot API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

# Instantiate the settings so other files can import it
settings = Settings()