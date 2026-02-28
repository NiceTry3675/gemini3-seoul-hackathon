from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    GOOGLE_API_KEY: str
    TEXT_MODEL: str = "gemini-3-flash-preview"
    IMAGE_MODEL: str = "gemini-3.1-flash-image-preview"
    VIDEO_MODEL: str = "veo-3.1-generate-preview"
    DB_PATH: str = "storage/app.db"
    DEBUG: bool = False
    GENAI_REQUEST_TIMEOUT_SECONDS: int = 120

    model_config = {"env_file": "../.env", "env_file_encoding": "utf-8"}


settings = Settings()
