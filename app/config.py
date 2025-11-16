# app/config.py
import os
from dotenv import load_dotenv

# Load variables from .env into environment
load_dotenv()

class Settings:
    def __init__(self) -> None:
        # Gemini
        self.gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
        self.gemini_model_name: str = os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-pro-exp-0801")
        self.gemini_embed_model: str = os.getenv("GEMINI_EMBED_MODEL", "text-embedding-004")

        # Qdrant
        self.qdrant_url: str = os.getenv("QDRANT_URL", "")
        self.qdrant_api_key: str = os.getenv("QDRANT_API_KEY", "")
        self.qdrant_collection: str = os.getenv("QDRANT_COLLECTION", "contract_precedents")

        # Basic sanity checks (you can relax these if needed)
        if not self.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is not set in the environment / .env file")
        if not self.qdrant_url:
            raise ValueError("QDRANT_URL is not set in the environment / .env file")
        if not self.qdrant_api_key:
            raise ValueError("QDRANT_API_KEY is not set in the environment / .env file")

settings = Settings()