from __future__ import annotations

from pydantic import BaseModel, Field


class VideoReferenceImage(BaseModel):
    """참조 이미지 (캐릭터/오브젝트 일관성 유지용)."""
    data: str
    mime_type: str
    reference_type: str = "asset"


class ImagePart(BaseModel):
    """Base64 인코딩된 이미지 데이터."""
    data: str
    mime_type: str


class VideoGenerationRequest(BaseModel):
    prompt: str
    aspect_ratio: str = "16:9"
    negative_prompt: str | None = None
    reference_images: list[VideoReferenceImage] = Field(default=[], max_length=3)
    first_frame: ImagePart | None = None
    last_frame: ImagePart | None = None
    extend_video_base64: str | None = None


class VideoGenerationResponse(BaseModel):
    video_base64: str
    mime_type: str = "video/mp4"
