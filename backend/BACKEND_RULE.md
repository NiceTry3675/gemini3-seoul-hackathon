# 백엔드 코딩 규칙 및 컨벤션

이 문서는 Gemini 3 Seoul Hackathon 백엔드 프로젝트의 개발 규칙을 정의합니다. 모든 개발자는 이 규칙을 따라야 합니다.

---

## 1. 프로젝트 구조

백엔드는 **도메인 주도 설계(DDD)** 패턴을 따릅니다. 각 도메인은 완전히 독립적인 구조를 갖춘 모듈로 구성됩니다.

### 디렉토리 레이아웃

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                          # FastAPI 애플리케이션 진입점
│   ├── config.py                        # 환경 설정 (API 키, 모델명, 포트 등)
│   ├── exceptions.py                    # 도메인 예외 클래스
│   ├── prompt_manager.py                # 프롬프트 템플릿 및 시스템 지시사항 관리
│   ├── routers/
│   │   └── health.py                    # 헬스 체크 엔드포인트
│   ├── shared/                          # 모든 도메인이 공유하는 코드
│   │   ├── __init__.py
│   │   ├── client.py                    # Gemini API 클라이언트 초기화
│   │   └── multimodal.py                # 멀티모달 유틸리티 (이미지, 비디오 등)
│   └── domain/                          # 도메인별 모듈
│       ├── __init__.py
│       ├── text_generation/             # 텍스트 생성 도메인
│       │   ├── __init__.py
│       │   ├── schemas.py               # Pydantic 요청/응답 모델
│       │   ├── service.py               # 비즈니스 로직
│       │   └── router.py                # FastAPI 라우터 (엔드포인트)
│       └── image_generation/            # 이미지 생성 도메인
│           ├── __init__.py
│           ├── schemas.py
│           ├── service.py
│           └── router.py
├── prompts/                             # 프롬프트 템플릿 (YAML)
│   └── example.yaml                     # 템플릿 예제
├── tests/                               # 테스트 디렉토리
│   └── domain/
│       ├── test_text_generation.py
│       └── test_image_generation.py
├── system_instruction.toml              # 시스템 지시사항 저장소
├── requirements.txt                     # Python 의존성
└── run.py                               # 개발 서버 실행 스크립트
```

### 도메인의 구성 요소

각 도메인 폴더는 다음 3개의 파일을 **반드시** 포함해야 합니다:

| 파일명 | 역할 | 책임 |
|--------|------|------|
| **schemas.py** | Pydantic 모델 정의 | 요청/응답 데이터 검증, 타입 안정성 |
| **service.py** | 비즈니스 로직 구현 | API 호출, 데이터 처리, 예외 처리 |
| **router.py** | HTTP 엔드포인트 정의 | 요청 라우팅, DI, 응답 포맷팅 (얇게 유지) |

---

## 2. 프롬프트 관리 규칙

프롬프트 관리는 두 가지 메커니즘으로 분리됩니다:

### 2.1 시스템 프롬프트 (System Instructions)

**파일**: `system_instruction.toml`

시스템 수준의 고정 프롬프트는 TOML 형식으로 관리합니다.

```toml
[scene_parser]
instruction = "You are a scene parser. Analyze the given text and extract structured scene information."

[character_gen]
instruction = "You are a character designer. Generate detailed character descriptions based on the given parameters."
```

**접근 방법**:
```python
from app.prompt_manager import get_prompt_manager

pm = get_prompt_manager()
instruction = pm.get_system_instruction("scene_parser.instruction")  # 점 표기법으로 접근
```

### 2.2 사용자 프롬프트 템플릿

**디렉토리**: `prompts/` (YAML 파일, Jinja2 템플릿)

동적 변수가 필요한 프롬프트는 YAML 파일로 관리하고 Jinja2로 렌더링합니다.

```yaml
# prompts/character_detail.yaml
template: |
  Create a character named {{ character_name }} who is {{ age }} years old.
  Personality: {{ personality }}
  Background: {{ background }}
```

**사용 방법**:
```python
pm = get_prompt_manager()
prompt = pm.render(
    "character_detail",
    character_name="Alice",
    age=25,
    personality="brave",
    background="orphan"
)
```

### 2.3 캐싱 전략

- **개발(dev) 모드**: 매 호출 시 파일을 리로드 (변경사항 즉시 반영)
- **프로덕션(prod) 모드**: 애플리케이션 시작 시 한 번만 로드하여 캐시 (성능 최적화)

```python
# 환경 변수로 제어
# ENV=dev python run.py    # 개발 모드 (리로드)
# ENV=prod python run.py   # 프로덕션 모드 (캐시)
```

---

## 3. 새 도메인 추가 가이드

새로운 도메인(예: `video_generation`)을 추가할 때 다음 단계를 따르세요.

### Step 1: 도메인 폴더 생성

```bash
mkdir -p app/domain/video_generation
touch app/domain/video_generation/__init__.py
```

### Step 2: schemas.py 작성

```python
# app/domain/video_generation/schemas.py
from __future__ import annotations
from pydantic import BaseModel, Field

class VideoGenerationRequest(BaseModel):
    prompt: str
    duration: int = Field(default=5, ge=1, le=60)
    resolution: str = Field(default="1080p", pattern="^(720p|1080p|4k)$")
    system_instruction_key: str | None = None

class VideoGenerationResponse(BaseModel):
    video_url: str
    duration: int
    metadata: dict | None = None
```

### Step 3: service.py 작성

```python
# app/domain/video_generation/service.py
from __future__ import annotations
from google import genai
from app.config import settings
from app.exceptions import GeminiAPIError
from app.domain.video_generation.schemas import (
    VideoGenerationRequest,
    VideoGenerationResponse,
)

class GeminiVideoService:
    def __init__(self, client: genai.Client) -> None:
        self._client = client
        self._model = settings.VIDEO_MODEL  # config.py에 정의 필요

    def generate(self, request: VideoGenerationRequest) -> VideoGenerationResponse:
        try:
            # Gemini API 호출 로직
            response = self._client.models.generate_content(...)
            return VideoGenerationResponse(...)
        except Exception as exc:
            # 예외를 app.exceptions에 정의된 클래스로 변환
            raise GeminiAPIError(str(exc)) from exc
```

### Step 4: router.py 작성

```python
# app/domain/video_generation/router.py
from fastapi import APIRouter, Depends
from google import genai

from app.shared.client import get_genai_client
from app.domain.video_generation.schemas import VideoGenerationRequest, VideoGenerationResponse
from app.domain.video_generation.service import GeminiVideoService

router = APIRouter(prefix="/api/video", tags=["video-generation"])

def _get_service(client: genai.Client = Depends(get_genai_client)) -> GeminiVideoService:
    return GeminiVideoService(client)

@router.post("/generate", response_model=VideoGenerationResponse)
async def generate_video(
    request: VideoGenerationRequest,
    service: GeminiVideoService = Depends(_get_service),
):
    return service.generate(request)
```

### Step 5: main.py에 라우터 등록

```python
# app/main.py
from app.domain.video_generation.router import router as video_router

app.include_router(video_router)
```

### Step 6: 테스트 추가

```python
# tests/domain/test_video_generation.py
import pytest
from app.domain.video_generation.schemas import VideoGenerationRequest

@pytest.mark.asyncio
async def test_video_generation():
    request = VideoGenerationRequest(prompt="A beautiful sunset")
    # 테스트 로직
```

---

## 4. 코딩 컨벤션

### 4.1 Python 버전 및 타입 힌팅

- **Python 3.11 이상** 필수
- **모든 함수와 메서드에 타입 힌팅 작성 필수**
- 왕복 호출 참조를 위해 `from __future__ import annotations` 사용

```python
from __future__ import annotations

def process_data(input_str: str, count: int = 1) -> dict[str, int]:
    return {"processed": len(input_str) * count}
```

### 4.2 Pydantic v2 모델

모든 데이터 검증은 **Pydantic v2** BaseModel을 사용합니다.

```python
from pydantic import BaseModel, Field

class MyRequest(BaseModel):
    name: str                           # 필수 필드
    age: int = Field(default=0, ge=0)  # 기본값, 검증 규칙
    email: str | None = None            # 선택적 필드
```

**검증 규칙 사용**:
- `Field(ge=0, le=100)` - 범위 검증
- `Field(min_length=3, max_length=50)` - 문자열 길이
- `Field(pattern="^[a-z]+$")` - 정규식
- `Field(description="...")` - API 문서 설명

### 4.3 FastAPI 의존성 주입 (DI)

모든 서비스 인스턴스는 `Depends()`를 통해 주입받습니다.

```python
from fastapi import APIRouter, Depends
from app.shared.client import get_genai_client

@router.post("/endpoint")
async def my_endpoint(
    request: MyRequest,
    service: MyService = Depends(_get_service),  # DI로 서비스 주입
):
    return service.process(request)
```

**DI 함수 작성**:
```python
def _get_service(client: genai.Client = Depends(get_genai_client)) -> MyService:
    return MyService(client)
```

### 4.4 예외 처리

**모든 도메인 예외는 `app/exceptions.py`에 정의된 클래스를 상속해야 합니다.**

```python
# app/exceptions.py에 정의
class DomainException(Exception):
    """모든 도메인 예외의 기본 클래스"""
    status_code: int = 500
    detail: str = "Internal server error"

class CustomError(DomainException):
    status_code = 400
    detail = "Custom error message"

# 사용 예
def validate_input(data: str) -> None:
    if not data:
        raise CustomError("Input cannot be empty")
```

**기존 예외 클래스**:
- `GeminiAPIError` - SDK 호출 실패 (502)
- `QuotaExceededError` - API 쿼터 초과 (429)
- `SafetyBlockError` - 안전 필터 차단 (422)
- `InvalidInputError` - 입력 검증 실패 (400)

### 4.5 비즈니스 로직과 라우터 분리

**원칙**: 라우터는 얇게, 비즈니스 로직은 서비스에서 처리

**❌ 나쁜 예**:
```python
@router.post("/endpoint")
async def my_endpoint(request: MyRequest):
    # 서비스 로직을 라우터에서 직접 구현
    if not request.name:
        raise ValueError("Name required")
    result = gemini_api.call(request.name)
    processed = json.loads(result)
    return processed
```

**✓ 좋은 예**:
```python
# service.py
class MyService:
    def process(self, request: MyRequest) -> dict:
        if not request.name:
            raise InvalidInputError("Name required")
        result = self._client.models.generate_content(request.name)
        return self._parse_response(result)

# router.py
@router.post("/endpoint")
async def my_endpoint(
    request: MyRequest,
    service: MyService = Depends(_get_service),
):
    return service.process(request)
```

### 4.6 임포트 순서

```python
from __future__ import annotations

# 표준 라이브러리
import os
import json
from pathlib import Path

# 써드파티
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from google import genai

# 프로젝트 내부
from app.config import settings
from app.exceptions import GeminiAPIError
from app.domain.my_domain.schemas import MyRequest
```

---

## 5. 모델 스펙

### 5.1 텍스트 생성 모델

| 항목 | 값 |
|------|-----|
| **모델명** | `gemini-3.1-pro-preview` |
| **환경 변수** | `TEXT_MODEL` (app/config.py) |
| **용도** | 텍스트 생성, 구조화된 출력, 스트리밍 |
| **최대 출력 토큰** | 65,536 |

### 5.2 이미지 생성 모델

| 항목 | 값 |
|------|-----|
| **모델명** | `gemini-3.1-flash-image-preview` |
| **환경 변수** | `IMAGE_MODEL` (app/config.py) |
| **용도** | 이미지 생성, 멀티모달 처리 |
| **지원 형식** | PNG, JPEG, GIF, WebP |

### 5.3 동영상 생성 모델

| 항목 | 값 |
|------|-----|
| **모델명** | `veo-3.1-generate-preview` |
| **환경 변수** | `VIDEO_MODEL` (app/config.py) |
| **용도** | 동영상 생성 (자체 오디오 포함) |
| **SDK 메서드** | `client.models.generate_videos()` (비동기 폴링) |

### 5.4 SDK 및 클라이언트

| 항목 | 값 |
|------|-----|
| **Python SDK** | `google-genai` |
| **초기화** | `app/shared/client.py` (get_genai_client) |
| **인증** | `GOOGLE_API_KEY` 환경 변수 |

**클라이언트 초기화**:
```python
from app.shared.client import get_genai_client

# FastAPI DI를 통해 자동 주입
@router.post("/endpoint")
async def my_endpoint(
    client: genai.Client = Depends(get_genai_client),
):
    # client 사용
    pass
```

---

## 6. API 엔드포인트 목록

### 6.1 헬스 체크

| 메서드 | 경로 | 설명 | 응답 |
|--------|------|------|------|
| `GET` | `/api/health` | 서버 상태 확인 | `{"status": "ok"}` |

### 6.2 텍스트 생성 (Text Generation)

| 메서드 | 경로 | 설명 | 요청 모델 | 응답 모델 |
|--------|------|------|----------|----------|
| `POST` | `/api/text/generate` | 텍스트 생성 | `TextGenerationRequest` | `TextGenerationResponse` |
| `POST` | `/api/text/structured` | 구조화된 응답 생성 (JSON Schema) | `StructuredGenerationRequest` | JSON 객체 |
| `POST` | `/api/text/stream` | 스트리밍 텍스트 생성 | `TextGenerationRequest` | Server-Sent Events (SSE) |

**TextGenerationRequest 필드**:
- `prompt` (str, 필수): 생성 요청 프롬프트
- `parts` (list[MultimodalPart], 기본값: []): 멀티모달 입력 (비디오, 오디오, 이미지 등)
  - `data` (str): Base64 인코딩된 데이터
  - `mime_type` (str): MIME 타입 (예: `video/mp4`, `audio/mp3`, `image/jpeg`)
- `system_instruction_key` (str | None): `system_instruction.toml`의 키 (예: `scene_parser.instruction`)
- `temperature` (float, 기본값: 1.0): 0.0 ~ 2.0 범위
- `max_output_tokens` (int, 기본값: 8192): 1 ~ 65536 범위

**TextGenerationResponse 필드**:
- `text` (str): 생성된 텍스트
- `usage_metadata` (dict | None): 토큰 사용 정보

### 6.3 이미지 생성 (Image Generation)

| 메서드 | 경로 | 설명 | 요청 모델 | 응답 모델 |
|--------|------|------|----------|----------|
| `POST` | `/api/image/generate` | 이미지 생성 | `ImageGenerationRequest` | `ImageGenerationResponse` |

**ImageGenerationRequest 필드**:
- `prompt` (str, 필수): 이미지 생성 프롬프트
- `system_instruction_key` (str | None): `system_instruction.toml`의 키

**ImageGenerationResponse 필드**:
- `image_base64` (str): Base64 인코딩된 이미지 데이터
- `mime_type` (str): MIME 타입 (예: `image/png`)

### 6.4 동영상 생성 (Video Generation)

| 메서드 | 경로 | 설명 | 요청 모델 | 응답 모델 |
|--------|------|------|----------|----------|
| `POST` | `/api/video/generate` | 동영상 생성 | `VideoGenerationRequest` | `VideoGenerationResponse` |

**VideoGenerationRequest 필드**:
- `prompt` (str, 필수): 동영상 생성 프롬프트
- `aspect_ratio` (str, 기본값: "16:9"): 화면 비율 ("16:9" 또는 "9:16")
- `negative_prompt` (str | None): 제외할 요소 설명

**VideoGenerationResponse 필드**:
- `video_base64` (str): Base64 인코딩된 동영상 데이터
- `mime_type` (str, 기본값: "video/mp4"): MIME 타입

**참고**: 동영상 생성은 수십 초 소요될 수 있음 (Veo 3.1 비동기 폴링 방식)

---

## 7. 개발 워크플로우

### 7.1 환경 설정

```bash
# 1. 환경 변수 설정
export GOOGLE_API_KEY="your-api-key"
export ENV=dev  # 또는 prod

# 2. 의존성 설치
pip install -r requirements.txt

# 3. 개발 서버 실행
python run.py  # 기본: 127.0.0.1:8000
```

### 7.2 코드 테스트

```bash
# 전체 테스트 실행
pytest tests/

# 특정 도메인 테스트
pytest tests/domain/test_text_generation.py

# 커버리지 리포트
pytest --cov=app tests/
```

### 7.3 API 문서 확인

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## 8. 자주 묻는 질문 (FAQ)

### Q1: 새로운 예외 타입을 추가해야 하는 경우?

`app/exceptions.py`에서 `DomainException`을 상속하여 정의합니다:

```python
class MyCustomError(DomainException):
    status_code = 400
    detail = "My custom error message"
```

### Q2: 프롬프트를 동적으로 변경하고 싶은데?

`prompts/` 디렉토리에 YAML 템플릿을 추가하고 `PromptManager.render()`를 사용합니다:

```python
pm = get_prompt_manager()
result = pm.render("my_template", var1="value1", var2="value2")
```

### Q3: 기존 도메인에 새로운 엔드포인트를 추가하려면?

`router.py`에 새 함수를 추가하고, 필요시 `schemas.py`에서 새 요청/응답 모델을 정의합니다. 서비스 로직은 `service.py`에 추가합니다.

### Q4: 도메인 간 코드를 공유해야 하면?

`app/shared/` 디렉토리에 새 모듈을 생성합니다. 예: `app/shared/utils.py`

### Q5: 환경 변수를 추가하려면?

`app/config.py`의 `Settings` 클래스에 필드를 추가합니다:

```python
class Settings(BaseSettings):
    NEW_VAR: str = Field(default="default_value")
```

---

## 9. 체크리스트

새로운 기능을 추가할 때 다음 체크리스트를 확인하세요:

- [ ] 타입 힌팅이 모든 함수에 작성되었는가?
- [ ] Pydantic 모델로 입력 검증하는가?
- [ ] 비즈니스 로직이 service.py에 있는가?
- [ ] 라우터가 얇고 명확한가?
- [ ] 예외가 DomainException을 상속하는가?
- [ ] 테스트가 작성되었는가?
- [ ] 프롬프트가 시스템 지시사항 또는 템플릿으로 관리되는가?
- [ ] 의존성이 FastAPI Depends()로 주입되는가?

---

**마지막 수정**: 2026-02-28
**문서 버전**: 1.0
