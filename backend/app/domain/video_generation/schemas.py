from __future__ import annotations

from pydantic import BaseModel, Field


class ImagePart(BaseModel):
    data: str
    mime_type: str


class VideoReferenceImage(BaseModel):
    data: str
    mime_type: str


class VideoGenerationRequest(BaseModel):
    prompt: str
    aspect_ratio: str = Field(default="16:9")
    negative_prompt: str | None = None
    reference_images: list[VideoReferenceImage] | None = Field(default=None, max_length=3)
    first_frame: ImagePart | None = None
    last_frame: ImagePart | None = None
    extend_video_base64: str | None = None


class VideoGenerationResponse(BaseModel):
    video_base64: str
    mime_type: str = "video/mp4"
