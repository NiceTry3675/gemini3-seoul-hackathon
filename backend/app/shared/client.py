from functools import lru_cache
from google import genai
from google.genai import types
from app.config import settings


@lru_cache(maxsize=1)
def _create_client() -> genai.Client:
    # HttpOptions.timeout is in *milliseconds*
    timeout_ms = settings.GENAI_REQUEST_TIMEOUT_SECONDS * 1000
    http_options = types.HttpOptions(timeout=timeout_ms)
    return genai.Client(
        api_key=settings.GOOGLE_API_KEY,
        http_options=http_options,
    )


def get_genai_client() -> genai.Client:
    """FastAPI dependency that returns the singleton GenAI client."""
    return _create_client()
