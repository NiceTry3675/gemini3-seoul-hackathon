import os
from dotenv import load_dotenv

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")

GEMINI_TEXT_MODEL = "gemini-2.5-flash-preview-05-20"
GEMINI_IMAGE_MODEL = "gemini-2.0-flash-preview-image-generation"
