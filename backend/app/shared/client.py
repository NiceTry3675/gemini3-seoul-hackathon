from functools import lru_cache
from google import genai
from app.config import settings


@lru_cache(maxsize=1)
def _create_client() -> genai.Client:
    return genai.Client(api_key=settings.GOOGLE_API_KEY)


def get_genai_client() -> genai.Client:
    """FastAPI dependency that returns the singleton GenAI client."""
    return _create_client()
