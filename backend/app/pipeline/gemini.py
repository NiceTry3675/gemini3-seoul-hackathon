import base64
from typing import TypeVar, Type

from google import genai
from google.genai import types

from app.config import GOOGLE_API_KEY, GEMINI_TEXT_MODEL, GEMINI_IMAGE_MODEL

T = TypeVar("T")

client = genai.Client(api_key=GOOGLE_API_KEY)


async def call_gemini_structured(
    system_prompt: str,
    user_prompt: str,
    response_schema: Type[T],
    temperature: float = 0.7,
) -> T:
    """Call Gemini with structured JSON output validated by a Pydantic model."""
    response = client.models.generate_content(
        model=GEMINI_TEXT_MODEL,
        contents=[types.Content(role="user", parts=[types.Part(text=user_prompt)])],
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            response_mime_type="application/json",
            response_schema=response_schema,
            temperature=temperature,
        ),
    )
    return response_schema.model_validate_json(response.text)


async def generate_image(prompt: str) -> str | None:
    """Generate an image using Gemini image model. Returns base64 string or None."""
    try:
        response = client.models.generate_content(
            model=GEMINI_IMAGE_MODEL,
            contents=[types.Content(role="user", parts=[types.Part(text=prompt)])],
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
            ),
        )
        if response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if part.inline_data:
                    return base64.b64encode(part.inline_data.data).decode("utf-8")
        return None
    except Exception as e:
        print(f"Image generation failed: {e}")
        return None
