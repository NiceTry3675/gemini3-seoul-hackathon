# Gemini Model Handling Retrospective

> 2026-02-28 | TeaserStudio - Seoul Hackathon

## Overview

TeaserStudio는 Gemini API를 활용하여 스토리 텍스트로부터 9컷 이미지 티저와 비디오를 생성하는 파이프라인입니다.
개발 중 Gemini 모델(텍스트, 이미지, 비디오) 핸들링 과정에서 발생한 문제들과 해결 방법을 정리합니다.

## 사용 모델

| 용도 | 모델 ID | 비고 |
|------|---------|------|
| 텍스트 생성 | `gemini-3-flash-preview` | 메타 프롬프트, 플랜 생성 |
| 이미지 생성 | `gemini-3.1-flash-image-preview` | 캐릭터 앵커 + 3x3 그리드 이미지 |
| 비디오 생성 | `veo-3.1-generate-preview` | first/last frame 보간 비디오 |

---

## 1. Veo 3.1 비디오 생성 이슈

### 1.1 `video_bytes`가 None으로 반환됨

**증상**: `a bytes-like object is required, not 'NoneType'`

**원인**: Veo API의 `generate_videos` 응답에서 `video.video.video_bytes`가 None. 비디오 데이터가 bytes로 직접 포함되지 않고, URI로 제공됨.

**해결**:
```python
raw_bytes = getattr(video.video, 'video_bytes', None)
if raw_bytes is None:
    video_uri = getattr(video.video, 'uri', None)
    if video_uri:
        # URI에서 직접 다운로드
        async with httpx.AsyncClient(timeout=180, follow_redirects=True, headers=headers) as client:
            resp = await client.get(video_uri)
            raw_bytes = resp.content
```

**교훈**: Veo API 응답은 `video_bytes` 또는 `uri` 중 하나로 올 수 있으므로 항상 fallback 로직이 필요.

---

### 1.2 다운로드 시 302 리다이렉트 실패

**증상**: `Redirect response '302 Found'`

**원인**: httpx의 기본 설정이 리다이렉트를 따르지 않음.

**해결**: `follow_redirects=True` 설정.

```python
httpx.AsyncClient(timeout=180, follow_redirects=True)
```

---

### 1.3 다운로드 시 403 Forbidden

**증상**: `Client error '403 Forbidden'` on redirect URL

**원인**: API 키를 쿼리 파라미터(`?key=...`)로 전달하면 302 리다이렉트 시 키가 유실됨. 리다이렉트된 URL에는 키가 포함되지 않아 인증 실패.

**해결**: `x-goog-api-key` 헤더로 전달. 헤더는 리다이렉트 시에도 유지됨.

```python
headers = {"x-goog-api-key": settings.GOOGLE_API_KEY}
async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
    resp = await client.get(video_uri)
```

**교훈**: Google API 다운로드 URL은 리다이렉트가 발생할 수 있으므로, 인증은 반드시 헤더로 전달해야 함.

---

### 1.4 `reference_images` 사용 시 400 에러

**증상**:
- `VideoGenerationReferenceType.STYLE enum value is not supported in Gemini API.`
- `400 INVALID_ARGUMENT - Unsupported video generation request`

**원인**:
1. `reference_type="style"`은 Veo API에서 지원하지 않는 enum 값
2. `first_frame`과 `reference_images`를 동시에 사용할 수 없음

**해결**: `reference_images`를 제거하고, `first_frame` + `last_frame` 조합으로 변경.

```python
VideoGenerationRequest(
    prompt=prompt,
    aspect_ratio="9:16",
    first_frame=ImagePart(data=first_b64, mime_type="image/png"),
    last_frame=ImagePart(data=last_b64, mime_type="image/png"),
)
```

**교훈**: Veo의 기능 조합에는 제한이 있음:
- `first_frame` + `last_frame` ✅ (보간 생성)
- `first_frame` + `reference_images` ❌ (동시 사용 불가)
- `reference_type`은 `"asset"` 만 유효 (`"style"` 미지원)

---

### 1.5 스타일 비일관성

**증상**: 생성된 비디오가 원본 이미지 스타일과 다르게 나옴

**원인**: `first_frame`만 넘기면 Veo가 자유롭게 영상 방향을 결정함

**해결**:
- `last_frame`으로 마지막 컷 이미지를 추가하여 첫-끝 프레임 보간
- `story_prompt`를 프롬프트에 포함하여 스토리 맥락 전달

---

## 2. Gemini 이미지 생성 이슈

### 2.1 3x3 그리드 이미지 분할 전략

**접근**: 9장의 이미지를 개별 생성하지 않고, 3x3 그리드로 1장 생성 후 Pillow로 분할.

**장점**:
- API 호출 2회 (앵커 1장 + 그리드 1장) vs 10회
- 패널 간 스타일 일관성 향상
- 속도 개선

**구현**:
```python
grid_img = _generate_image(client, grid_prompt, anchor_image)
cell_pngs = _split_grid_image(grid_png, rows=3, cols=3)
```

---

## 3. 프론트엔드 연동 이슈

### 3.1 백엔드 연결 실패

**증상**: 모든 AI 기능 미작동

**원인**: 백엔드(port 8000)가 실행되지 않은 상태에서 프론트엔드만 실행

**해결**: `fetchFromApiBase()`가 여러 base URL을 시도하는 fallback 로직이 있지만, 백엔드 자체가 미실행이면 모두 실패. 백엔드 실행 필수.

### 3.2 대용량 base64 SSE 전송

**접근**: 비디오 base64 데이터(수십 MB)를 SSE `data:` 라인으로 전송

**확인 사항**:
- 프론트엔드 SSE 파서가 줄 단위(`\n`) 처리 → 단일 `data:` 라인이면 문제없음
- `ReadableStream` 기반 스트리밍으로 메모리 효율적 처리

---

## 4. 아키텍처 결정 사항

### 비디오 생성 전략

| 항목 | 초기 설계 | 최종 설계 |
|------|-----------|-----------|
| 비디오 수 | 9컷 각각 1개씩 (9개) | 전체 1개 |
| first_frame | 각 컷 이미지 | 첫 번째 컷 |
| last_frame | 미사용 | 마지막 컷 |
| reference_images | 인접 컷 3장 | 미사용 (호환 불가) |
| 프롬프트 | 고정 generic 문구 | 원본 스토리 + cinematic 지시 |

### URL 라우팅

각 워크플로우 스텝을 URL 해시로 분리하여 직접 접근 가능:
```
/#story_input → /#meta_prompt_1 → /#meta_prompt_2 → /#meta_prompt_3 → /#video_export
```

---

## 5. 핵심 교훈 요약

1. **Veo 응답 형식이 일정하지 않음** — `video_bytes` 또는 `uri`, 항상 양쪽 처리 필요
2. **Google API 리다이렉트 + 인증** — 쿼리파라미터는 리다이렉트에서 유실, 헤더 사용 필수
3. **Veo 기능 조합 제한** — `first_frame` + `reference_images` 동시 불가
4. **그리드 이미지 전략** — 개별 생성보다 한 장 생성 후 분할이 효율적
5. **SSE로 대용량 데이터 전송** — base64 비디오도 문제없이 스트리밍 가능
