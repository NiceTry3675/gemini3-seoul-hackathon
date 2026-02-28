# PRD: 소설 → 웹툰 컨티 생성기

> **행사**: Google Gemini 3 Seoul Hackathon (2026-02-28)
> **팀 규모**: 4
> **목표**: 소설 원고(최대 2,000자)를 입력하면 12컷 웹툰 컨티(이미지 + 대사 + 내레이션)를 자동으로 생성하는 웹앱

---

## 1. 프로젝트 개요

### 1.1 해커톤 정보

| 항목        | 세부사항                                                           |
| ----------- | ------------------------------------------------------------------ |
| 트랙        | Gemini API Creative Application                                    |
| 핵심 API    | 텍스트/구조화: Gemini 2.5 Flash + 이미지 생성: nano banana 2 |
| 타임리밋   | ~5시간                                                             |
| 제출물      | 동작 데모 + 5분 피치                                             |

### 1.2 평가 기준 (예상)

1. **창의성** — Gemini 멀티모달 기능의 새로운 사용 방식
2. **완성도** — E2E 동작 프로토타입
3. **기술 깊이** — 구조화된 출력, 멀티 스텝 파이프라인, 에러 처리
4. **UX 완성도** — 실시간 진행 표시, 직관적 입력, 시각적 결과물

### 1.3 핵심 결정사항

| 결정 항목          | 선택지                                    | 근거                                                       |
| ------------------ | ----------------------------------------- | ---------------------------------------------------------- |
| 텍스트 모델        | `gemini-2.5-flash-preview-05-20`          | 구조화된 JSON 출력, 빠른 응답, 비용 효율                     |
| 이미지 모델        | `nano banana 2`                           | 독립적 이미지 생성 라인업, 외부 의존성 최소화                 |
| 백엔드 프레임워크  | FastAPI (Python)                          | 비동기 처리, Pydantic 네이티브, SSE 지원                    |
| 프론트엔드 프레임워크 | Next.js 16 + React 19 + Tailwind CSS 4  | 빠른 초기 세팅, 현대적 스택, 강력한 타입 지원               |
| 컷 수              | 고정 12컷                                 | 데모 시 일관된 웹툰 포맷, 구현 범위 관리                     |
| 상태 관리          | 인메모리 dict (서버 사이드)                | 해커톤 범위이므로 DB 불필요                                  |
| 통신 방식          | SSE (Server-Sent Events)                  | 양방향이 아닌 단방향 진행 스트림에 간단한 구현
 |

---

## 2. 아키텍처

### 2.1 디렉터리 구조

```
gemini3-seoul-hackathon/
├── backend/
│   ├── run.py                      # Uvicorn 진입점
│   ├── requirements.txt
│   └── app/
│       ├── __init__.py
│       ├── main.py                 # FastAPI 앱 + API 4개 엔드포인트
│       ├── config.py               # 환경변수, 모델 ID
│       ├── models/
│       │   ├── __init__.py
│       │   ├── schemas.py          # Pydantic 모델(공유 계약)
│       │   └── prompts.py          # 시스템 프롬프트 + 템플릿
│       └── pipeline/
│           ├── __init__.py
│           ├── gemini.py           # Gemini API 래퍼 (텍스트 + 이미지)
│           ├── scene_parser.py     # Step 1: 소설 → 장면
│           ├── character_gen.py    # Step 2: 장면 → 캐릭터 + 참조 이미지
│           ├── cut_planner.py      # Step 3: 장면 + 캐릭터 → 12컷 계획
│           ├── validator.py        # Step 4: 품질 검증
│           ├── image_gen.py        # Step 5: 컷 → 이미지
│           └── orchestrator.py     # 파이프라인 오케스트레이터 + SSE 발행
├── frontend/
│   ├── package.json                # Next.js 16 + React 19 + Tailwind 4
│   ├── next.config.ts
│   ├── tsconfig.json
│   └── src/
│       ├── app/
│       │   ├── layout.tsx          # 루트 레이아웃 (Geist 폰트)
│       │   ├── page.tsx            # 메인 페이지 (TBD: 추가 구현)
│       │   └── globals.css         # Tailwind 기본 스타일
│       └── lib/
│           ├── types.ts            # schemas.py와 대응되는 TypeScript 타입
│           └── api.ts              # API 클라이언트(fetch + EventSource)
├── .env.example                    # GOOGLE_API_KEY=...
├── .gitignore
└── PRD.md                          # 이 문서
```

### 2.2 기술 스택

| 계층              | 기술         | 버전  |
| ------------------ | ------------ | ----- |
| 백엔드 런타임     | Python       | 3.11+ |
| 백엔드 프레임워크 | FastAPI      | ≥0.115 |
| ASGI 서버         | Uvicorn      | ≥0.34 |
| AI SDK            | google-genai | ≥1.0.0 |
| 스키마 검증       | Pydantic     | ≥2.0  |
| 프론트 런타임     | Node.js      | 20+   |
| 프론트 프레임워크 | Next.js      | 16.1.6 |
| UI 라이브러리     | React        | 19.2.3 |
| CSS               | Tailwind CSS | 4.x   |
| 언어              | TypeScript   | 5.x   |

### 2.3 데이터 흐름 (5단계 파이프라인)

```
┌─────────────────────────────────────────────────────────────────────┐
│                        사용자 입력                                  │
│  manuscript(≤2000자) + 장르 + 톤 + 연령등급 + 언어                 │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
                                 ▼
┌───────────────────────────────────────────────────────────────────────┐
│  STEP 1: 장면 분해                                                   │
│  Input:  NovelInput                                                  │
│  Output: SceneBreakdown (2–6 scenes)                                  │
│  Model:  gemini-2.5-flash (구조화 JSON → SceneBreakdown)              │
└──────────────────────────────────┬───────────────────────────────────┘
                                 │
                                 ▼
┌───────────────────────────────────────────────────────────────────────┐
│  STEP 2: 캐릭터 생성                                                │
│  Input:  SceneBreakdown + NovelInput                                  │
│  Output: CharacterSheet (1–4 캐릭터) + 참조 이미지                    │
│  Model:  gemini-2.5-flash (구조화) + nano banana 2 (이미지)             │
│  Note:   참조 이미지는 선택적(일관성 앵커용)                           │
└────────────────────────────────────┬──────────────────────────────────┘
                                 │
                                 ▼
┌───────────────────────────────────────────────────────────────────────┐
│  STEP 3: 12컷 플래닝                                               │
│  Input:  SceneBreakdown + CharacterSheet + NovelInput                  │
│  Output: CutPlan (정확히 12컷)                                        │
│  Model:  gemini-2.5-flash (구조화 JSON → CutPlan)                     │
└────────────────────────────────────┬──────────────────────────────────┘
                                 │
                                 ▼
┌───────────────────────────────────────────────────────────────────────┐
│  STEP 4: 검증                                                      │
│  Input:  CutPlan + CharacterSheet                                    │
│  Output: ValidationReport                                            │
│  Model:  gemini-2.5-flash (구조화 JSON → ValidationReport)            │
│  Logic:  검증 실패 시 Step 3를 1회 재실행 후 재검증                 │
└────────────────────────────────────┬──────────────────────────────────┘
                                 │
                                 ▼
┌───────────────────────────────────────────────────────────────────────┐
│  STEP 5: 이미지 생성                                                  │
│  Input:  CutPlan + CharacterSheet + 톤 + 연령등급                      │
│  Output: list[GeneratedCut] (12장 base64)                             │
│  Model:  nano banana 2                                                │
│  Strategy: 3개씩 배치, 배치 간 2초 지연, 컷당 최대 3회 재시도          │
└──────────────────────────────────────┬────────────────────────────────┘
                                 │
                                 ▼
┌───────────────────────────────────────────────────────────────────────┐
│                        CONTI 결과                                      │
│  ContiResult { characters, cuts, images }                             │
│  → 프론트엔드에서 세로형 웹툰 뷰어로 렌더링                         │
└───────────────────────────────────────────────────────────────────────┘
```

---

## 3. 데이터 모델 (스키마)

모든 모델은 backend에서 Pydantic v2 `BaseModel`로, frontend에서 TypeScript 인터페이스로 동기화한다. **이는 팀 공통 계약으로, 필드 이름/타입은 구성원 모두와 조율 없이 변경하지 않는다.**

### 3.1 열거형

```python
class Genre(str, Enum):
    MYSTERY = "mystery"
    SF = "sf"
    ROMANCE = "romance"
    FANTASY = "fantasy"
    SLICE_OF_LIFE = "slice_of_life"

class Tone(str, Enum):
    DARK = "dark"
    COMIC = "comic"
    EMOTIONAL = "emotional"
    EERIE = "eerie"

class Rating(str, Enum):
    ALL = "all"
    AGE_12 = "12"
    AGE_15 = "15"
```

### 3.2 입력

```python
class NovelInput(BaseModel):
    manuscript: str       # max_length=2000
    genre: Genre
    tone: Tone
    rating: Rating        # 기본값: Rating.ALL
    output_language: str  # "ko" | "en" | "ja" | "zh" | "es", 기본값 "ko"
```

### 3.3 파이프라인 중간 모델

```python
class Scene(BaseModel):
    scene_id: str                    # 예: "scene_1"
    summary: str                     # output_language로 작성된 장면 요약
    emotion: str                     # 주요 감정
    key_action: str                  # 핵심 시각 액션
    background: str                  # 배경/장소 상세
    characters_present: list[str]    # 장면에 등장한 캐릭터 이름

class SceneBreakdown(BaseModel):
    scenes: list[Scene]  # min=2, max=6

class Character(BaseModel):
    name: str                        # 원어명
    name_en: str                     # 로마자 표기 이름
    appearance_keywords: list[str]   # 정확히 5개
    personality_one_word: str        # 한 단어 성격 핵심
    prohibited_visuals: list[str]    # 금지 요소 목록

class CharacterSheet(BaseModel):
    characters: list[Character]  # min=1, max=4

class Cut(BaseModel):
    id: int                          # 1–12
    scene_ref: str                   # Scene.scene_id 참조
    action: str                      # 시각적으로 벌어지는 동작
    dialogue: str                    # 최대 35자, 비워두면 무언 대사
    narration: str                   # 내레이션(선택)
    sfx: str                        # 효과음(선택)
    camera: str                      # close-up|medium|wide|bird's-eye|low-angle|over-shoulder|dutch-angle
    mood: str                        # tense|calm|dramatic|mysterious|romantic|action|comedic|melancholic
    characters_in_frame: list[str]   # 컷 내 등장 캐릭터 이름
    background: str                  # 컷별 배경 설정

class CutPlan(BaseModel):
    cuts: list[Cut]  # 정확히 12

class ValidationResult(BaseModel):
    cut_id: int
    is_valid: bool
    issues: list[str]    # 통과 시 빈 배열

class ValidationReport(BaseModel):
    results: list[ValidationResult]
    all_passed: bool     # 모든 컷이 통과한 경우만 True
```

### 3.4 출력 모델

```python
class GeneratedCut(BaseModel):
    cut_id: int           # 1–12
    image_base64: str     # PNG base64 (빈 문자열 = 생성 실패)
    prompt_used: str      # 이미지 모델에 전송한 정확한 프롬프트

class ContiResult(BaseModel):
    characters: CharacterSheet
    cuts: CutPlan
    images: list[GeneratedCut]  # 12개
```

### 3.5 SSE 이벤트 모델

```python
# Pydantic 모델은 아님 — SSE에서 raw JSON으로 전송
{
    "step": int,          # 1–5(파이프라인 단계), 메타 이벤트는 0
    "name": str,          # "Scene Parsing" | "Character Generation" | "Cut Planning" | "Validation" | "Image Generation" | "complete" | "error"
    "status": str,        # "running" | "done" | "error"
    "data": Any | null    # 단계별 payload (4장에서 상세)
}
```

---

## 4. AI 파이프라인 상세

### 4.1 Step 1 — 장면 분해

| 항목        | 상세                                                                          |
| ----------- | ----------------------------------------------------------------------------- |
| 파일        | `pipeline/scene_parser.py`                                                     |
| 모델        | `gemini-2.5-flash` (구조화 출력)                                              |
| 입력        | `NovelInput` (전체 객체)                                                       |
| 출력        | `SceneBreakdown` (2–6 scenes)                                                  |
| 온도        | 0.7 (기본값)                                                                  |
| 시스템 프롬프트 | `SCENE_PARSER_SYSTEM` — 소설을 시각적으로 구분되는 장면으로 분해하도록 지시   |

**프롬프트 전략**: 시스템 프롬프트는 역할(웹툰 스토리보드 작가)을 정의한다. 사용자 프롬프트에 장르, 톤, 연령등급, 원고 텍스트를 전달한다. `{output_language}` 플레이스홀더는 시스템 프롬프트에 주입된다.

**SSE 이벤트**:

- `{ step: 1, name: "Scene Parsing", status: "running", data: null }`
- `{ step: 1, name: "Scene Parsing", status: "done", data: SceneBreakdown }`

### 4.2 Step 2 — 캐릭터 생성

| 항목        | 상세                                                          |
| ----------- | ------------------------------------------------------------- |
| 파일        | `pipeline/character_gen.py`                                   |
| 모델        | `gemini-2.5-flash` (구조화) + `nano banana 2` (이미지)          |
| 입력        | `SceneBreakdown` + `NovelInput`                               |
| 출력        | `CharacterSheet` + 참조 이미지(dict[name → base64])             |
| 하위 단계   | 2a: 캐릭터 데이터 생성, 2b: 참조 이미지 생성                   |

**프롬프트 전략**:

- **2a**(텍스트): 모든 장면에서 캐릭터명을 추출하고, 주요 캐릭터 1–4명을 생성한다. 각 캐릭터에 대해 외형 키워드를 정확히 5개 생성한다. 이 키워드는 Step 5의 모든 이미지 프롬프트에 주입되는 **일관성 앵커**가 된다.
- **2b**(이미지): 흰 배경의 정면 인물화 형태로 캐릭터별 기준 이미지를 생성한다. 최종 출력에 직접 노출되진 않지만, 시각 참조용으로 사용한다.

**핵심 제약**: `appearance_keywords`는 반드시 **정확히 5개**, 구체적이고 그릴 수 있는 형태여야 한다(예: "long black wavy hair"). Step 5 이미지 프롬프트에 그대로 재사용한다.

**SSE 이벤트**:

- `{ step: 2, name: "Character Generation", status: "running", data: null }`
- `{ step: 2, name: "Character Generation", status: "done", data: { characters: CharacterSheet, reference_images: count } }`

### 4.3 Step 3 — 12컷 플래닝

| 항목       | 상세                                                  |
| ---------- | ----------------------------------------------------- |
| 파일       | `pipeline/cut_planner.py`                             |
| 모델       | `gemini-2.5-flash` (구조화)                           |
| 입력       | `SceneBreakdown` + `CharacterSheet` + `NovelInput`    |
| 출력       | `CutPlan` (정확히 12컷)                               |

**프롬프트 전략**: 시스템 프롬프트(`CUT_PLANNER_SYSTEM`)에서 엄격 규칙 적용

1. 정확히 12컷
2. 1컷은 와이드 샷(환경 제시)
3. 12컷은 클리프행어 또는 감정적 피크
4. 대사 없는 무음 패널 최소 2컷
5. 카메라 종류의 다양성 확보(7가지 옵션)
6. 각 컷은 `scene_ref` 참조
7. 대사 35자 이내, `{output_language}`
8. 적절한 위치에 SFX 의성어 삽입

**SSE 이벤트**:

- `{ step: 3, name: "Cut Planning", status: "running", data: null }`
- `{ step: 3, name: "Cut Planning", status: "done", data: CutPlan }`

### 4.4 Step 4 — 검증

| 항목       | 상세                                                     |
| ---------- | -------------------------------------------------------- |
| 파일       | `pipeline/validator.py`                                  |
| 모델       | `gemini-2.5-flash` (구조화)                              |
| 입력       | `CutPlan` + `CharacterSheet`                             |
| 출력       | `ValidationReport`                                       |

**검증 항목** (AI 기반):

1. 대사 길이 ≤ 35자
2. 캐릭터 일관성 — `characters_in_frame`이 `CharacterSheet`에 존재
3. 카메라 각도 다양성 — 동일 각도 연속 3회 이상 감지 시 실패
4. 장면 흐름 — 액션의 논리적 진행
5. 시각적 명확성 — 컷 하나를 단일 패널로 그릴 수 있는지

**재시도 로직**: `all_passed == false`면 오케스트레이터가 Step 3(컷 플래닝)을 1회 재실행 후 다시 검증한다. 이후 재시도는 하지 않고, 통과 결과를 채택한다.

**SSE 이벤트**:

- `{ step: 4, name: "Validation", status: "running", data: null }`
- `{ step: 4, name: "Validation", status: "running", data: { retrying: true } }` _(실패 시)_
- `{ step: 4, name: "Validation", status: "done", data: ValidationReport }`

### 4.5 Step 5 — 이미지 생성

| 항목         | 상세                                                   |
| ------------ | ------------------------------------------------------ |
| 파일         | `pipeline/image_gen.py`                                |
| 모델         | `nano banana 2`                                        |
| 입력         | `CutPlan` + `CharacterSheet` + 톤 + 연령등급          |
| 출력         | `list[GeneratedCut]` (12개)                            |
| 배치 크기    | 동시 요청 3개                                         |
| 배치 간 지연  | 2초                                                  |
| 최대 재시도  | 컷당 3회                                            |

**이미지 프롬프트 템플릿** (`IMAGE_PROMPT_TEMPLATE`):

```
Create a webtoon-style illustration panel.

Style: {tone_style}          ← TONE_STYLE_MAP[tone]에서 변환
Camera: {camera} shot
Mood: {mood}
Background: {background}

Characters in frame:
{character_descriptions}     ← "- name_en: 5 appearance keywords (personality)"

Action: {action}

Requirements:
- Clean webtoon art style with bold outlines
- Expressive character poses and faces
- Dynamic composition fitting a vertical scroll webtoon panel
- No text overlay, no speech bubbles, no written words in the image
- {rating_guidance}          ← RATING_GUIDANCE_MAP[rating]에서 변환
```

**톤 스타일 매핑**:
| Tone | 비주얼 스타일 설명 |
|------|------------------|
| `dark` | 짙은 명암의 음영, 탈색 색조, 느와르 조명, 굵은 잉크 선 |
| `comic` | 밝고 선명한 톤, 과장된 표정, 깔끔한 선, 팝 아트 느낌 |
| `emotional` | 부드러운 수채화 질감, 파스텔 팔레트, 따뜻한 톤, 완만한 조명 |
| `eerie` | 차분한 냉색 팔레트, 불안감을 주는 구도, 가는 거친 선, 안개 |

**연령등급 가이드**:
| Rating | 가이드 |
|--------|--------|
| `all` | 전 연령 대상. 폭력·성적 표현 없음 |
| `12` | 완화된 긴장 가능. 잔혹/선정적 묘사 없음 |
| `15` | 중간 정도의 액션/드라마 긴장 허용. 노골적 내용 없음 |

**재시도 전략**: 이미지 생성 실패 시, 프롬프트 끝에 `"(Attempt N: Please generate a clear illustration.)"`를 추가해 재요청한다. 3회 실패 시 `image_base64=""`(빈 문자열) 반환.

**SSE 이벤트**:

- `{ step: 5, name: "Image Generation", status: "running", data: null }`
- `{ step: 5, name: "Image Generation", status: "running", data: { progress: "Generated images 1-3 of 12" } }`
- `{ step: 5, name: "Image Generation", status: "done", data: { count: 12 } }`

---

## 5. API 명세

**Base URL**: `http://localhost:8000`
**CORS**: `http://localhost:3000` 허용

### 5.1 `POST /api/generate` — 생성 시작

5단계 파이프라인을 비동기로 시작한다. 즉시 task ID를 반환한다.

**요청 본문**:

```json
{
  "manuscript": "소설 텍스트 (max 2000 chars)...",
  "genre": "romance",
  "tone": "emotional",
  "rating": "all",
  "output_language": "ko"
}
```

**응답** `200 OK`:

```json
{
  "task_id": "uuid-string"
}
```

**에러**: 입력값 검증 실패 시 `422 Unprocessable Entity`(Pydantic).

### 5.2 `GET /api/progress/{task_id}` — 진행률 스트리밍 (SSE)

`text/event-stream` 응답을 반환한다. 각 SSE 메시지는 `PipelineEvent` JSON이다.

**이벤트 형식**: `data: {"step": 1, "name": "Scene Parsing", "status": "running", "data": null}\n\n`

**종료 이벤트**:

- `{ "step": 0, "name": "complete", "status": "done" }` — 파이프라인 정상 완료
- `{ "step": 0, "name": "complete", "status": "error" }` — 파이프라인 실패

**폴링 간격**: 서버가 새 이벤트를 500ms마다 확인.

**에러**: `task_id` 미존재 시 `404`.

### 5.3 `GET /api/result/{task_id}` — 최종 결과 조회

파이프라인 완료 후 전체 `ContiResult`를 반환한다.

**응답** `200 OK`:

```json
{
  "characters": {
    "characters": [
      {
        "name": "민지",
        "name_en": "Minji",
        "appearance_keywords": [
          "long black straight hair",
          "almond-shaped brown eyes",
          "petite slender build",
          "white school uniform blouse",
          "round silver earrings"
        ],
        "personality_one_word": "determined",
        "prohibited_visuals": ["tattoos", "heavy makeup"]
      }
    ]
  },
  "cuts": {
    "cuts": [
      {
        "id": 1,
        "scene_ref": "scene_1",
        "action": "Minji walks into the empty classroom at dawn",
        "dialogue": "",
        "narration": "그날의 시작은 고요했다",
        "sfx": "",
        "camera": "wide",
        "mood": "calm",
        "characters_in_frame": ["민지"],
        "background": "Empty high school classroom with morning sunlight streaming through tall windows"
      }
    ]
  },
  "images": [
    {
      "cut_id": 1,
      "image_base64": "iVBORw0KGgo...",
      "prompt_used": "Create a webtoon-style illustration panel..."
    }
  ]
}
```

**에러**:

- `404` — task not found
- `202 Accepted` — 아직 처리 중 (바디: `"Still processing"`)
- `500` — 파이프라인 에러 (바디: 에러 메시지 문자열)

### 5.4 `POST /api/regenerate-cut/{task_id}/{cut_id}` — 단일 패널 재생성

특정 컷의 이미지를 재생성한다(사용자 재선택 시). 기존 캐릭터 시트와 컷 플랜 재사용.

**파라미터**: `task_id`(path), `cut_id`(path, 1–12)

**응답** `200 OK`:

```json
{
  "cut_id": 1,
  "image_base64": "iVBORw0KGgo...",
  "prompt_used": "Create a webtoon-style illustration panel..."
}
```

**에러**:

- `404` — task 또는 cut 미존재
- `400` — 작업 미완료

---

## 6. 프론트엔드 설계

### 6.1 레이아웃 (와이어프레임)

```
┌──────────────────────────────────────────────────────────────────┐
│  HEADER: "Novel → Webtoon Conti"                       [About]  │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─── 입력 폼 ────────────────────────────────────────────────┐  │
│  │  📝 원고 입력 텍스트영역 (2000자 제한, 카운터)             │  │
│  │                                                             │  │
│  │  장르: [Romance] [Fantasy] [Mystery] [Sci-Fi] [SoL]       │  │
│  │  톤:   [Emotional] [Dark] [Comic] [Eerie]                  │  │
│  │  연령등급: [All Ages] [12+] [15+]                            │  │
│  │  언어: [Korean ▼]                                           │  │
│  │                                                             │  │
│  │  [ ▶ Conti 생성 ]                                          │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌─── 진행 상황 (생성 중 표시) ─────────────────────────────┐  │
│  │  ✅ Step 1: Scene Parsing              — 완료               │  │
│  │  ⏳ Step 2: Character Generation       — 진행 중...        │  │
│  │  ○ Step 3: Cut Planning                — 대기             │  │
│  │  ○ Step 4: Validation                  — 대기             │  │
│  │  ○ Step 5: Image Generation            — 대기             │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌─── 결과 뷰어 (완료 후 표시) ───────────────────────────────┐ │
│  │                                                             │  │
│  │  캐릭터 카드 (가로 스크롤)                                  │  │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐                    │  │
│  │  │ Avatar  │  │ Avatar  │  │ Avatar  │                     │  │
│  │  │ "민지"  │  │ "준혁"  │  │ "소라"  │                     │  │
│  │  │ Keywords│  │ Keywords│  │ Keywords│                     │  │
│  │  └─────────┘  └─────────┘  └─────────┘                    │  │
│  │                                                             │  │
│  │  웹툰 스트립 (세로 스크롤 — 메인 출력)                    │  │
│  │  ┌─────────────────────────────────────────┐               │  │
│  │  │  CUT 1 — wide shot                      │               │
│  │  │  [Generated Image]                       │               │
│  │  narration: "그날의 시작은 고요했다"      │               │
│  │                           [🔄 다시 생성] │               │
│  │  ├─────────────────────────────────────────┤               │
│  │  │  CUT 2 — close-up                       │               │
│  │  │  [Generated Image]                       │               │
│  │  dialogue: "왜 이렇게 일찍 왔어?"        │               │
│  │  sfx: "삐걱"                             │               │
│  │                           [🔄 다시 생성] │               │
│  │  ├─────────────────────────────────────────┤               │
│  │  │  ... (cuts 3–12)                         │               │
│  │  └─────────────────────────────────────────┘               │
│  │                                                             │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### 6.2 컴포넌트 목록

| 컴포넌트          | 파일                                  | 설명                                                                  |
| ------------------ | ------------------------------------- | --------------------------------------------------------------------- |
| `InputForm`        | `src/components/InputForm.tsx`        | 원고 입력창 + 장르/톤/연령등급/언어 선택기 + 생성 버튼 |
| `ProgressTracker`  | `src/components/ProgressTracker.tsx`  | 상태 아이콘(대기/진행/완료/오류) 기반 5단계 진행 바 |
| `CharacterCards`   | `src/components/CharacterCards.tsx`   | 캐릭터 아바타/키워드 가로 스크롤 |
| `WebtoonStrip`     | `src/components/WebtoonStrip.tsx`     | 12컷 패널의 세로 스크롤 렌더링 |
| `CutPanel`         | `src/components/CutPanel.tsx`         | 단일 패널: 이미지 + 대사 + 내레이션 + SFX + 재생성 버튼 |
| `RegenerateButton` | `src/components/RegenerateButton.tsx` | `POST /api/regenerate-cut` 호출 후 이미지 교체 |

### 6.3 상태 관리

페이지 레벨에서 React `useState` + `useRef` 사용. 별도 상태관리 라이브러리 불필요.

```typescript
// 페이지 레벨 상태
const [phase, setPhase] = useState<"input" | "generating" | "result">("input");
const [taskId, setTaskId] = useState<string | null>(null);
const [events, setEvents] = useState<PipelineEvent[]>([]);
const [result, setResult] = useState<ContiResult | null>(null);
const [error, setError] = useState<string | null>(null);
```

**흐름**:

1. `phase="input"` → `InputForm` 표시
2. 사용자가 "Generate" 클릭 → `startGeneration()` 호출 → `taskId` 획득 → `phase="generating"`
3. `EventSource`로 `streamProgress(taskId)` 열기 → `events[]` 누적 → `ProgressTracker` 표시
4. 완료 시 `getResult(taskId)` 호출 → `result` 반영 → `phase="result"`
5. `CharacterCards` + `WebtoonStrip` 표시
6. 패널의 "Regenerate" 클릭 → `regenerateCut(taskId, cutId)` 호출 → `result.images[i]` 업데이트

### 6.4 API 클라이언트 (이미 구현)

`src/lib/api.ts`에 구현. 4개 API와 일치.

```typescript
startGeneration(input: NovelInput): Promise<string>                    // → task_id
streamProgress(taskId, onEvent, onComplete, onError): () => void    // → cleanup fn
getResult(taskId): Promise<ContiResult>
regenerateCut(taskId, cutId): Promise<GeneratedCut>
```

Base URL는 `NEXT_PUBLIC_API_URL` 환경변수로 구성 가능(기본값: `http://localhost:8000`).

### 6.5 UI 상수 (이미 정의)

`src/lib/types.ts`에 정의됨:

- `PIPELINE_STEPS` — 진행 표시를 위한 단계 번호, 이름, 아이콘, 설명
- `GENRE_OPTIONS` — 장르 셀렉터용 value + label + emoji
- `TONE_OPTIONS` — 톤 셀렉터용 value + label + emoji
- `RATING_OPTIONS` — 연령등급 셀렉터용 value + label
- `LANGUAGE_OPTIONS` — 언어 셀렉터용 value + label

---

## 7. 의존성 그래프

```
┌─────────────────────────────────────────────────────────────────┐
│                    구현 순서                                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  TIER 0 (기반 — 의존성 없음)                                    │
│  ├── schemas.py + types.ts      ← 공유 계약, 먼저 구현             |
│  ├── config.py + .env           ← API 키 설정                    |
│  └── gemini.py                  ← API 래퍼(텍스트 + 이미지)       |
│                                                                 │
│  TIER 1 (Tier 0 후 시작 가능)                                   │
│  ├── prompts.py                 ← 시스템 프롬프트               |
│  ├── scene_parser.py            ← gemini.py + schemas 사용      |
│  ├── character_gen.py           ← gemini.py + schemas 사용      |
│  ├── api.ts                     ← types.ts만 사용               |
│  └── InputForm.tsx              ← types.ts만 사용               |
│                                                                 │
│  TIER 2 (Tier 1 출력 필요)                                      │
│  ├── cut_planner.py             ← Scene + Character             |
│  ├── validator.py               ← CutPlan + Character           |
│  ├── image_gen.py + prompts      ← Cut + Character               |
│  └── ProgressTracker.tsx        ← types.ts만 사용               |
│                                                                 │
│  TIER 3 (Tier 2 필요)                                          │
│  ├── orchestrator.py            ← 모든 파이프라인 단계 연결      |
│  ├── main.py                    ← API 엔드포인트 + SSE           |
│  └── CharacterCards.tsx         ← CharacterSheet 렌더링         |
│                                                                 │
│  TIER 4 (Tier 3 필요)                                          │
│  ├── WebtoonStrip.tsx           ← CutPlan + images 렌더링        |
│  ├── CutPanel.tsx               ← 단일 패널 + regenerate        |
│  └── page.tsx                   ← 컴포넌트 통합                |
│                                                                 │
│  TIER 5 (통합 & 마감)                                          │
│  ├── End-to-end testing                                         |
│  ├── 오류 상태/로딩 UI                                          |
│  └── 데모 준비                                                  |
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 병렬 작업 구간

| 작업 스트림                           | 동시 진행 가능 시점                 | 수정 파일                                                               |
| ------------------------------------- | ---------------------------------- | --------------------------------------------------------------------- |
| 파이프라인 Step 1–3 (텍스트)          | Tier 0 완료 후                      | `scene_parser.py`, `character_gen.py`, `cut_planner.py`, `prompts.py` |
| 파이프라인 Step 4–5 (검증 + 이미지)   | Tier 0 완료 후                      | `validator.py`, `image_gen.py`                                        |
| API 레이어                             | Tier 0 + 기본 파이프라인 구조        | `main.py`, `orchestrator.py`                                          |
| Frontend 컴포넌트                      | Tier 0 (types.ts) 완료 후            | 모든 `.tsx` 파일, `api.ts`                                            |

**크리티컬 패스**: `schemas.py` → 임의 파이프라인 단계 → `orchestrator.py` → `main.py` → 통합 완료.

---

## 8. 리스크 및 완화

### 8.1 Rate Limiting

| 리스크                              | 영향                                   | 완화                                                  |
| ---------------------------------- | -------------------------------------- | ----------------------------------------------------- |
| Gemini API Rate Limit (이미지 생성)  | 파이프라인 중간에서 이미지 생성 실패     | 배치 3개, 배치 간 2초 지연, 컷당 최대 3회 재시도 설정 |
| 동시 사용자 급증                   | API 과부하                              | 해커톤 범위: 단일 사용자 데모. 인메모리 저장으로 충분 |

### 8.2 이미지 생성 실패

| 리스크                      | 영향                                      | 완화                                                                                                           |
| --------------------------- | ----------------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| 이미지 생성 결과 `None`      | 최종 결과에 누락 패널 발생                | 수정된 프롬프트로 3회 재시도 후에도 실패 시 `image_base64=""`으로 처리. 프론트에서 플레이스홀더 표시 |
| 이미지 품질 불일치          | 패널 간 스타일 차이                        | 각 캐릭터 `appearance_keywords` 5개를 모든 프롬프트에 삽입. 톤 스타일 설명 고정화 |
| 안전 필터에 의한 차단        | 유효한 콘텐츠인데 블로킹                  | 연령등급 가이드 반영. 노골적/과격 요청 없음 |

### 8.3 캐릭터 드리프트

| 리스크                                      | 영향                               | 완화                                                                                                                                                 |
| ------------------------------------------- | ---------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| 캐릭터가 컷마다 다르게 생성되는 문제          | 시각적 일관성 하락                   | `appearance_keywords`(정확히 5개)를 모든 이미지 프롬프트에 그대로 재사용. `prohibited_visuals`로 금지 요소 제외. Step 2에서 생성한 참조 이미지(향후 확장 시 이미지 입력 전달) 사용 |

### 8.4 구조화 출력 실패

| 리스크                             | 영향                         | 완화                                                                                                              |
| ---------------------------------- | ---------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| Gemini가 유효하지 않은 JSON 반환      | 해당 단계 파이프라인 크래시     | Pydantic `model_validate_json()`에서 명확한 유효성 오류 발생. API 호출 시 `response_mime_type="application/json"` + `response_schema` 강제 |
| 컷 수가 12가 아닌 경우             | 스키마 검증 실패                | `CutPlan.cuts`의 `min_length=12, max_length=12` 제약. 구조화 출력 스키마에서 강제 |

### 8.5 프롬프트 인젝션

| 리스크                               | 영향                            | 완화                                                                                                           |
| ------------------------------------ | ------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| 사용자가 공격적 텍스트를 입력          | 모델 동작 이탈                    | 시스템 프롬프트로 역할과 출력 형식 고정. 구조화 스키마로 shape 제약. 원고 길이를 2,000자로 제한 |

### 8.6 성능

| 리스크                            | 영향                               | 완화                                                                                                          |
| --------------------------------- | ---------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| 전체 파이프라인 > 3분            | 데모 체감 품질 저하                | SSE 진행 알림으로 사용자의 몰입 유지. 병목은 이미지 생성이므로 3개 동시 처리로 속도/요청량 균형 조정. 텍스트 단계(1–4)는 빠름 |
| 응답 이미지 base64가 큼            | 결과 조회 지연, 메모리 증가         | 해커톤 범위에서는 허용. 실제 운영은 오브젝트 스토리지 URL 사용 예정 |

---

## 9. 검증

### 9.1 단위 수준 체크

| 체크 항목                              | 명령 / 방법                                                   |
| -------------------------------------- | ------------------------------------------------------------- |
| Backend 시작 오류 유무                  | `cd backend && python run.py` (import 에러 확인)               |
| Frontend 빌드                           | `cd frontend && npm run build`                                  |
| 스키마 정합성                           | `schemas.py`와 `types.ts` 필드 비교(수동)                      |
| 환경 설정                               | `.env.example`을 `.env`로 복사 후 `GOOGLE_API_KEY` 입력         |

### 9.2 End-to-End 테스트 시나리오

**사전 조건**: Backend는 `:8000`, Frontend는 `:3000`, `.env`에 유효한 `GOOGLE_API_KEY` 존재.

| 단계 | 작업                                                         | 기대 결과                                                 |
| ---- | ------------------------------------------------------------ | --------------------------------------------------------- |
| 1    | `http://localhost:3000` 열기                                | 입력 폼 표시                                              |
| 2    | 샘플 원고 입력(≤2000자)                                     | 글자 수 카운터 업데이트                                   |
| 3    | genre=Romance, tone=Emotional, rating=All, lang=Korean 선택   | 선택값 하이라이트                                        |
| 4    | "Generate Conti" 클릭                                      | 진행 표시기 표시, Step 1 시작                            |
| 5    | 파이프라인 완료까지 대기                                      | Step 1→5 순차 완료, progress 업데이트 표시                |
| 6    | 결과 화면 확인                                                | 캐릭터 카드 표시, 12컷 세로 렌더링                         |
| 7    | 컷 스크롤                                                    | 각 컷에 이미지 + 대사/내레이션/SFX 오버레이 존재           |
| 8    | 아무 패널에서 "Regenerate" 클릭                             | 새 이미지로 교체                                         |

### 9.3 API Smoke Test (curl)

```bash
# 1. 생성 시작
TASK_ID=$(curl -s -X POST http://localhost:8000/api/generate \
  -H "Content-Type: application/json" \
  -d '{"manuscript":"어느 봄날 아침, 민지는 텅 빈 교실에 혼자 앉아 있었다. 창밖으로 벚꽃이 흩날렸다.","genre":"romance","tone":"emotional","rating":"all","output_language":"ko"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['task_id'])")
echo "Task ID: $TASK_ID"

# 2. 진행률 스트림 (SSE)
curl -N http://localhost:8000/api/progress/$TASK_ID

# 3. 결과 조회(파이프라인 완료 후)
curl -s http://localhost:8000/api/result/$TASK_ID | python3 -c "
import sys, json
r = json.load(sys.stdin)
print(f'Characters: {len(r["characters"]["characters"])}')
print(f'Cuts: {len(r["cuts"]["cuts"])}')
print(f'Images: {len(r["images"])}')
imgs_ok = sum(1 for i in r['images'] if i['image_base64'])
print(f'Images with content: {imgs_ok}/12')
"

# 4. 단일 컷 재생성
curl -s -X POST http://localhost:8000/api/regenerate-cut/$TASK_ID/1 \
  | python3 -c "import sys,json; r=json.load(sys.stdin); print(f'Cut {r[\"cut_id\"]}: {\"OK\" if r[\"image_base64\"] else \"FAILED\"}')"
```

### 9.4 샘플 테스트 원고

**한국어 (로맨스)**:

> 어느 봄날 아침, 민지는 텅 빈 교실에 혼자 앉아 있었다. 창밖으로 벚꽃이 흩날렸다. 문이 열리며 준혁이 들어왔다. "왜 이렇게 일찍 왔어?" 민지가 물었다. 준혁은 대답 대신 손에 들린 편지를 내밀었다.

**영어 (미스터리)**:

> The old lighthouse keeper hadn't been seen in three days. Detective Park climbed the spiral staircase, each step creaking under her weight. At the top, the lamp still rotated, casting shadows across an empty chair. But the logbook was open to today's date, and in fresh ink, someone had written: "They're watching from the water."
