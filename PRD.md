# PRD: Novel → Webtoon Conti Generator

> **Event**: Google Gemini 3 Seoul Hackathon (2026-02-28)
> **Team size**: 4
> **Goal**: 소설 원고(max 2,000자)를 입력하면 12컷 웹툰 콘티(이미지 + 대사 + 나레이션)를 자동 생성하는 웹앱

---

## 1. Project Overview

### 1.1 Hackathon Info

| Item        | Detail                                                            |
| ----------- | ----------------------------------------------------------------- |
| Track       | Gemini API Creative Application                                   |
| Core API    | Gemini 2.5 Flash (text/structured) + Gemini 2.0 Flash (image gen) |
| Time limit  | ~10 hours                                                         |
| Deliverable | Working demo + 5-min pitch                                        |

### 1.2 Judging Criteria (expected)

1. **Creativity** — Novel use of Gemini multimodal capabilities
2. **Completeness** — End-to-end working prototype
3. **Technical depth** — Structured output, multi-step pipeline, error handling
4. **UX Polish** — Real-time progress, intuitive input, visual output

### 1.3 Key Decisions

| Decision           | Choice                                      | Rationale                                               |
| ------------------ | ------------------------------------------- | ------------------------------------------------------- |
| Text model         | `gemini-2.5-flash-preview-05-20`            | Structured JSON output, fast, cost-effective            |
| Image model        | `gemini-2.0-flash-preview-image-generation` | Native Gemini image gen, no external dependency         |
| Backend framework  | FastAPI (Python)                            | Async, Pydantic native, SSE support                     |
| Frontend framework | Next.js 16 + React 19 + Tailwind CSS 4      | Modern, fast setup, strong typing                       |
| Panel count        | Fixed 12 cuts                               | Consistent webtoon format, manageable for demo          |
| State management   | In-memory dict (server-side)                | Hackathon scope — no DB needed                          |
| Communication      | SSE (Server-Sent Events)                    | One-directional progress stream, simpler than WebSocket |

---

## 2. Architecture

### 2.1 Directory Structure

```
gemini3-seoul-hackathon/
├── backend/
│   ├── run.py                      # Uvicorn entry point
│   ├── requirements.txt
│   └── app/
│       ├── __init__.py
│       ├── main.py                 # FastAPI app + 4 endpoints
│       ├── config.py               # Env vars, model IDs
│       ├── models/
│       │   ├── __init__.py
│       │   ├── schemas.py          # All Pydantic models (shared contract)
│       │   └── prompts.py          # System prompts + templates
│       └── pipeline/
│           ├── __init__.py
│           ├── gemini.py           # Gemini API wrapper (text + image)
│           ├── scene_parser.py     # Step 1: Novel → Scenes
│           ├── character_gen.py    # Step 2: Scenes → Characters + refs
│           ├── cut_planner.py      # Step 3: Scenes + Chars → 12 Cuts
│           ├── validator.py        # Step 4: Quality check
│           ├── image_gen.py        # Step 5: Cuts → Images
│           └── orchestrator.py     # Pipeline coordinator + SSE emit
├── frontend/
│   ├── package.json                # Next.js 16 + React 19 + Tailwind 4
│   ├── next.config.ts
│   ├── tsconfig.json
│   └── src/
│       ├── app/
│       │   ├── layout.tsx          # Root layout (Geist font)
│       │   ├── page.tsx            # Main page (TBD: build out)
│       │   └── globals.css         # Tailwind base styles
│       └── lib/
│           ├── types.ts            # TypeScript types mirroring schemas.py
│           └── api.ts              # API client (fetch + EventSource)
├── .env.example                    # GOOGLE_API_KEY=...
├── .gitignore
└── PRD.md                          # This file
```

### 2.2 Tech Stack

| Layer              | Technology   | Version |
| ------------------ | ------------ | ------- |
| Backend runtime    | Python       | 3.11+   |
| Backend framework  | FastAPI      | ≥0.115  |
| ASGI server        | Uvicorn      | ≥0.34   |
| AI SDK             | google-genai | ≥1.0.0  |
| Schema validation  | Pydantic     | ≥2.0    |
| Frontend runtime   | Node.js      | 20+     |
| Frontend framework | Next.js      | 16.1.6  |
| UI library         | React        | 19.2.3  |
| CSS                | Tailwind CSS | 4.x     |
| Language           | TypeScript   | 5.x     |

### 2.3 Data Flow (5-Stage Pipeline)

```
┌─────────────────────────────────────────────────────────────────────┐
│                        USER INPUT                                   │
│  manuscript (≤2000 chars) + genre + tone + rating + language        │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
                                 ▼
┌────────────────────────────────────────────────────────────────────┐
│  STEP 1: Scene Parsing                                             │
│  Input:  NovelInput                                                │
│  Output: SceneBreakdown (2–6 scenes)                               │
│  Model:  gemini-2.5-flash (structured JSON → SceneBreakdown)       │
└────────────────────────────────┬───────────────────────────────────┘
                                 │
                                 ▼
┌────────────────────────────────────────────────────────────────────┐
│  STEP 2: Character Generation                                      │
│  Input:  SceneBreakdown + NovelInput                               │
│  Output: CharacterSheet (1–4 characters) + reference images        │
│  Model:  gemini-2.5-flash (structured) + gemini-2.0-flash (image)  │
│  Note:   Reference images are optional (for consistency anchor)    │
└────────────────────────────────┬───────────────────────────────────┘
                                 │
                                 ▼
┌────────────────────────────────────────────────────────────────────┐
│  STEP 3: 12-Cut Planning                                           │
│  Input:  SceneBreakdown + CharacterSheet + NovelInput              │
│  Output: CutPlan (exactly 12 cuts)                                 │
│  Model:  gemini-2.5-flash (structured JSON → CutPlan)              │
└────────────────────────────────┬───────────────────────────────────┘
                                 │
                                 ▼
┌────────────────────────────────────────────────────────────────────┐
│  STEP 4: Validation                                                │
│  Input:  CutPlan + CharacterSheet                                  │
│  Output: ValidationReport                                          │
│  Model:  gemini-2.5-flash (structured JSON → ValidationReport)     │
│  Logic:  If validation fails → re-run Step 3 once, then re-validate│
└────────────────────────────────┬───────────────────────────────────┘
                                 │
                                 ▼
┌────────────────────────────────────────────────────────────────────┐
│  STEP 5: Image Generation                                          │
│  Input:  CutPlan + CharacterSheet + tone + rating                  │
│  Output: list[GeneratedCut] (12 images as base64)                  │
│  Model:  gemini-2.0-flash-preview-image-generation                 │
│  Strategy: Batch of 3, 2s delay between batches, 3 retries each    │
└────────────────────────────────┬───────────────────────────────────┘
                                 │
                                 ▼
┌────────────────────────────────────────────────────────────────────┐
│                        CONTI RESULT                                │
│  ContiResult { characters, cuts, images }                          │
│  → Rendered as scrollable webtoon viewer in frontend               │
└────────────────────────────────────────────────────────────────────┘
```

---

## 3. Data Models (Schemas)

All models are defined as Pydantic v2 `BaseModel` (backend) and mirrored as TypeScript interfaces (frontend). **These are the shared contract — do not modify field names/types without coordinating with all team members.**

### 3.1 Enums

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

### 3.2 Input

```python
class NovelInput(BaseModel):
    manuscript: str       # max_length=2000
    genre: Genre
    tone: Tone
    rating: Rating        # default: Rating.ALL
    output_language: str  # "ko" | "en" | "ja" | "zh" | "es", default "ko"
```

### 3.3 Pipeline Intermediate Models

```python
class Scene(BaseModel):
    scene_id: str                    # e.g., "scene_1"
    summary: str                     # Scene description in output_language
    emotion: str                     # Dominant emotion
    key_action: str                  # Main visual action
    background: str                  # Setting/location detail
    characters_present: list[str]    # Character names appearing

class SceneBreakdown(BaseModel):
    scenes: list[Scene]  # min=2, max=6

class Character(BaseModel):
    name: str                        # Original language name
    name_en: str                     # Romanized English name
    appearance_keywords: list[str]   # EXACTLY 5 visual descriptors
    personality_one_word: str        # Single word essence
    prohibited_visuals: list[str]    # Never-draw list

class CharacterSheet(BaseModel):
    characters: list[Character]  # min=1, max=4

class Cut(BaseModel):
    id: int                          # 1–12
    scene_ref: str                   # References Scene.scene_id
    action: str                      # What's happening visually
    dialogue: str                    # max 35 chars, empty = silent panel
    narration: str                   # Optional narration text
    sfx: str                         # Optional sound effect
    camera: str                      # close-up|medium|wide|bird's-eye|low-angle|over-shoulder|dutch-angle
    mood: str                        # tense|calm|dramatic|mysterious|romantic|action|comedic|melancholic
    characters_in_frame: list[str]   # Character names in this panel
    background: str                  # Specific background for this cut

class CutPlan(BaseModel):
    cuts: list[Cut]  # EXACTLY 12

class ValidationResult(BaseModel):
    cut_id: int
    is_valid: bool
    issues: list[str]    # Empty if valid

class ValidationReport(BaseModel):
    results: list[ValidationResult]
    all_passed: bool     # True only if every cut is valid
```

### 3.4 Output Models

```python
class GeneratedCut(BaseModel):
    cut_id: int           # 1–12
    image_base64: str     # PNG base64 (empty string = generation failed)
    prompt_used: str      # The exact prompt sent to image model

class ContiResult(BaseModel):
    characters: CharacterSheet
    cuts: CutPlan
    images: list[GeneratedCut]  # 12 items
```

### 3.5 SSE Event Model

```python
# Not a Pydantic model — sent as raw JSON via SSE
{
    "step": int,          # 1–5 (pipeline stage), 0 for meta-events
    "name": str,          # "Scene Parsing" | "Character Generation" | "Cut Planning" | "Validation" | "Image Generation" | "complete" | "error"
    "status": str,        # "running" | "done" | "error"
    "data": Any | null    # Stage-specific payload (see Section 4)
}
```

---

## 4. AI Pipeline Detail

### 4.1 Step 1 — Scene Parsing

| Item          | Detail                                                                         |
| ------------- | ------------------------------------------------------------------------------ |
| File          | `pipeline/scene_parser.py`                                                     |
| Model         | `gemini-2.5-flash` (structured output)                                         |
| Input         | `NovelInput` (full object)                                                     |
| Output        | `SceneBreakdown` (2–6 scenes)                                                  |
| Temperature   | 0.7 (default)                                                                  |
| System prompt | `SCENE_PARSER_SYSTEM` — instructs to break novel into visually distinct scenes |

**Prompt strategy**: System prompt defines the role (webtoon storyboard artist). User prompt provides genre, tone, rating, and full manuscript text. The `{output_language}` placeholder is injected into the system prompt.

**SSE events**:

- `{ step: 1, name: "Scene Parsing", status: "running", data: null }`
- `{ step: 1, name: "Scene Parsing", status: "done", data: SceneBreakdown }`

### 4.2 Step 2 — Character Generation

| Item      | Detail                                                       |
| --------- | ------------------------------------------------------------ |
| File      | `pipeline/character_gen.py`                                  |
| Model     | `gemini-2.5-flash` (structured) + `gemini-2.0-flash` (image) |
| Input     | `SceneBreakdown` + `NovelInput`                              |
| Output    | `CharacterSheet` + reference images (dict[name → base64])    |
| Sub-steps | 2a: Generate character data, 2b: Generate reference images   |

**Prompt strategy**:

- **2a** (text): Extracts character names from all scenes, designs 1–4 main characters with exactly 5 appearance keywords each. These keywords are the **consistency anchor** — they're injected into every image prompt in Step 5.
- **2b** (image): Generates a front-facing portrait per character on a white background. Used as visual reference but not directly shown in final output.

**Critical constraint**: `appearance_keywords` must be **exactly 5** items, concrete and drawable (e.g., "long black wavy hair", not "beautiful"). These are reused verbatim in Step 5 image prompts.

**SSE events**:

- `{ step: 2, name: "Character Generation", status: "running", data: null }`
- `{ step: 2, name: "Character Generation", status: "done", data: { characters: CharacterSheet, reference_images: count } }`

### 4.3 Step 3 — 12-Cut Planning

| Item   | Detail                                             |
| ------ | -------------------------------------------------- |
| File   | `pipeline/cut_planner.py`                          |
| Model  | `gemini-2.5-flash` (structured)                    |
| Input  | `SceneBreakdown` + `CharacterSheet` + `NovelInput` |
| Output | `CutPlan` (exactly 12 cuts)                        |

**Prompt strategy**: System prompt (`CUT_PLANNER_SYSTEM`) enforces strict rules:

1. Exactly 12 cuts
2. Cut 1 = establishing wide shot
3. Cut 12 = cliffhanger/emotional beat
4. At least 2 silent panels (no dialogue)
5. Camera variety required (7 options)
6. Each cut references a `scene_ref`
7. Dialogue max 35 chars in `{output_language}`
8. SFX onomatopoeia where appropriate

**SSE events**:

- `{ step: 3, name: "Cut Planning", status: "running", data: null }`
- `{ step: 3, name: "Cut Planning", status: "done", data: CutPlan }`

### 4.4 Step 4 — Validation

| Item   | Detail                          |
| ------ | ------------------------------- |
| File   | `pipeline/validator.py`         |
| Model  | `gemini-2.5-flash` (structured) |
| Input  | `CutPlan` + `CharacterSheet`    |
| Output | `ValidationReport`              |

**Validation checks** (AI-driven):

1. Dialogue length ≤ 35 characters
2. Character consistency — `characters_in_frame` must exist in `CharacterSheet`
3. Camera angle variety — flag 3+ consecutive same angles
4. Scene flow — logical action progression
5. Visual clarity — each cut must be drawable as a single panel

**Retry logic**: If `all_passed == false`, orchestrator re-runs Step 3 (cut planning) once, then re-validates. No further retries — accepts whatever passes.

**SSE events**:

- `{ step: 4, name: "Validation", status: "running", data: null }`
- `{ step: 4, name: "Validation", status: "running", data: { retrying: true } }` _(on failure)_
- `{ step: 4, name: "Validation", status: "done", data: ValidationReport }`

### 4.5 Step 5 — Image Generation

| Item        | Detail                                       |
| ----------- | -------------------------------------------- |
| File        | `pipeline/image_gen.py`                      |
| Model       | `gemini-2.0-flash-preview-image-generation`  |
| Input       | `CutPlan` + `CharacterSheet` + tone + rating |
| Output      | `list[GeneratedCut]` (12 items)              |
| Batch size  | 3 concurrent requests                        |
| Batch delay | 2 seconds between batches                    |
| Max retries | 3 per cut                                    |

**Image prompt template** (`IMAGE_PROMPT_TEMPLATE`):

```
Create a webtoon-style illustration panel.

Style: {tone_style}          ← from TONE_STYLE_MAP[tone]
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
- {rating_guidance}          ← from RATING_GUIDANCE_MAP[rating]
```

**Tone style mapping**:
| Tone | Visual Style Description |
|------|------------------------|
| `dark` | Dark, high-contrast shadows, desaturated colors, noir lighting, heavy inking |
| `comic` | Bright, vibrant, exaggerated expressions, clean lines, pop art |
| `emotional` | Soft watercolor, pastel palette, warm tones, gentle lighting |
| `eerie` | Muted cold palette, unsettling compositions, thin scratchy linework, fog |

**Rating guidance**:
| Rating | Guidance |
|--------|----------|
| `all` | Suitable for all ages. No violence, no suggestive content. |
| `12` | Mild tension allowed. No graphic violence or suggestive content. |
| `15` | Moderate action and dramatic tension allowed. No explicit content. |

**Retry strategy**: On image failure, appends `"(Attempt N: Please generate a clear illustration.)"` to the prompt and retries. After 3 failures, returns `image_base64=""` (empty string = failed panel).

**SSE events**:

- `{ step: 5, name: "Image Generation", status: "running", data: null }`
- `{ step: 5, name: "Image Generation", status: "running", data: { progress: "Generated images 1-3 of 12" } }`
- `{ step: 5, name: "Image Generation", status: "done", data: { count: 12 } }`

---

## 5. API Specification

**Base URL**: `http://localhost:8000`
**CORS**: Allows `http://localhost:3000`

### 5.1 `POST /api/generate` — Start Generation

Starts the 5-step pipeline asynchronously. Returns immediately with a task ID.

**Request**:

```json
{
  "manuscript": "소설 텍스트 (max 2000 chars)...",
  "genre": "romance",
  "tone": "emotional",
  "rating": "all",
  "output_language": "ko"
}
```

**Response** `200 OK`:

```json
{
  "task_id": "uuid-string"
}
```

**Error**: `422 Unprocessable Entity` for invalid input (Pydantic validation).

### 5.2 `GET /api/progress/{task_id}` — Stream Progress (SSE)

Returns a `text/event-stream` response. Each SSE message is a `PipelineEvent` JSON.

**Event format**: `data: {"step": 1, "name": "Scene Parsing", "status": "running", "data": null}\n\n`

**Terminal events**:

- `{ "step": 0, "name": "complete", "status": "done" }` — pipeline finished successfully
- `{ "step": 0, "name": "complete", "status": "error" }` — pipeline failed

**Polling interval**: Server checks for new events every 500ms.

**Error**: `404` if `task_id` not found.

### 5.3 `GET /api/result/{task_id}` — Get Final Result

Returns the complete `ContiResult` after pipeline completes.

**Response** `200 OK`:

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

**Errors**:

- `404` — task not found
- `202 Accepted` — still processing (body: `"Still processing"`)
- `500` — pipeline error (body: error message string)

### 5.4 `POST /api/regenerate-cut/{task_id}/{cut_id}` — Regenerate Single Panel

Regenerates the image for a single cut (e.g., if the user is unhappy with it). Reuses the existing character sheet and cut plan.

**Parameters**: `task_id` (path), `cut_id` (path, 1–12)

**Response** `200 OK`:

```json
{
  "cut_id": 1,
  "image_base64": "iVBORw0KGgo...",
  "prompt_used": "Create a webtoon-style illustration panel..."
}
```

**Errors**:

- `404` — task or cut not found
- `400` — task not complete

---

## 6. Frontend Design

### 6.1 Layout (Wireframe)

```
┌──────────────────────────────────────────────────────────────────┐
│  HEADER: "Novel → Webtoon Conti"                       [About]  │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─── INPUT FORM ─────────────────────────────────────────────┐  │
│  │  📝 Manuscript textarea (2000 char limit, counter)         │  │
│  │                                                             │  │
│  │  Genre: [Romance] [Fantasy] [Mystery] [Sci-Fi] [SoL]      │  │
│  │  Tone:  [Emotional] [Dark] [Comic] [Eerie]                │  │
│  │  Rating: [All Ages] [12+] [15+]                            │  │
│  │  Language: [Korean ▼]                                       │  │
│  │                                                             │  │
│  │  [ ▶ Generate Conti ]                                      │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌─── PROGRESS (visible during generation) ────────────────────┐ │
│  │  ✅ Step 1: Scene Parsing              — done               │ │
│  │  ⏳ Step 2: Character Generation       — running...         │ │
│  │  ○ Step 3: Cut Planning                — pending            │ │
│  │  ○ Step 4: Validation                  — pending            │ │
│  │  ○ Step 5: Image Generation            — pending            │ │
│  └─────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌─── RESULT VIEWER (visible after completion) ────────────────┐ │
│  │                                                             │  │
│  │  CHARACTER CARDS (horizontal scroll)                        │  │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐                    │  │
│  │  │ Avatar  │  │ Avatar  │  │ Avatar  │                     │  │
│  │  │ "민지"  │  │ "준혁"  │  │ "소라"  │                     │  │
│  │  │ Keywords│  │ Keywords│  │ Keywords│                      │  │
│  │  └─────────┘  └─────────┘  └─────────┘                    │  │
│  │                                                             │  │
│  │  WEBTOON STRIP (vertical scroll — main output)             │  │
│  │  ┌─────────────────────────────────────────┐               │  │
│  │  │  CUT 1 — wide shot                      │               │  │
│  │  │  [Generated Image]                       │               │  │
│  │  │  narration: "그날의 시작은 고요했다"      │               │  │
│  │  │                           [🔄 Regenerate] │               │  │
│  │  ├─────────────────────────────────────────┤               │  │
│  │  │  CUT 2 — close-up                       │               │  │
│  │  │  [Generated Image]                       │               │  │
│  │  │  dialogue: "왜 이렇게 일찍 왔어?"        │               │  │
│  │  │  sfx: "삐걱"                             │               │  │
│  │  │                           [🔄 Regenerate] │               │  │
│  │  ├─────────────────────────────────────────┤               │  │
│  │  │  ... (cuts 3–12)                         │               │  │
│  │  └─────────────────────────────────────────┘               │  │
│  │                                                             │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### 6.2 Component List

| Component          | File                                  | Description                                                                  |
| ------------------ | ------------------------------------- | ---------------------------------------------------------------------------- |
| `InputForm`        | `src/components/InputForm.tsx`        | Manuscript textarea + genre/tone/rating/language selectors + generate button |
| `ProgressTracker`  | `src/components/ProgressTracker.tsx`  | 5-step progress bar with status icons (pending/running/done/error)           |
| `CharacterCards`   | `src/components/CharacterCards.tsx`   | Horizontal scroll of character avatars + keywords                            |
| `WebtoonStrip`     | `src/components/WebtoonStrip.tsx`     | Vertical scroll of 12 cut panels                                             |
| `CutPanel`         | `src/components/CutPanel.tsx`         | Single panel: image + dialogue + narration + sfx + regenerate button         |
| `RegenerateButton` | `src/components/RegenerateButton.tsx` | Calls `POST /api/regenerate-cut` and swaps the image                         |

### 6.3 State Management

Use React `useState` + `useRef` at the page level. No external state library needed.

```typescript
// Page-level state
const [phase, setPhase] = useState<"input" | "generating" | "result">("input");
const [taskId, setTaskId] = useState<string | null>(null);
const [events, setEvents] = useState<PipelineEvent[]>([]);
const [result, setResult] = useState<ContiResult | null>(null);
const [error, setError] = useState<string | null>(null);
```

**Flow**:

1. `phase="input"` → Show `InputForm`
2. User clicks "Generate" → call `startGeneration()` → get `taskId` → `phase="generating"`
3. Open `streamProgress(taskId)` via EventSource → append to `events[]` → show `ProgressTracker`
4. On complete → call `getResult(taskId)` → set `result` → `phase="result"`
5. Show `CharacterCards` + `WebtoonStrip`
6. User clicks "Regenerate" on a panel → call `regenerateCut(taskId, cutId)` → update `result.images[i]`

### 6.4 API Client (Already Implemented)

Located at `src/lib/api.ts`. Four functions matching the 4 API endpoints:

```typescript
startGeneration(input: NovelInput): Promise<string>          // → task_id
streamProgress(taskId, onEvent, onComplete, onError): () => void  // → cleanup fn
getResult(taskId): Promise<ContiResult>
regenerateCut(taskId, cutId): Promise<GeneratedCut>
```

Base URL configurable via `NEXT_PUBLIC_API_URL` env var (default: `http://localhost:8000`).

### 6.5 UI Constants (Already Defined)

Located at `src/lib/types.ts`:

- `PIPELINE_STEPS` — step number, name, icon, description for progress display
- `GENRE_OPTIONS` — value + label + emoji for genre selector
- `TONE_OPTIONS` — value + label + emoji for tone selector
- `RATING_OPTIONS` — value + label for rating selector
- `LANGUAGE_OPTIONS` — value + label for language selector

---

## 7. Dependency Graph

```
┌─────────────────────────────────────────────────────────────────┐
│                    IMPLEMENTATION ORDER                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  TIER 0 (Foundation — no dependencies)                          │
│  ├── schemas.py + types.ts      ← Shared contract, do first    │
│  ├── config.py + .env           ← API key setup                │
│  └── gemini.py                  ← API wrapper (text + image)   │
│                                                                 │
│  TIER 1 (Can start after Tier 0)                                │
│  ├── prompts.py                 ← System prompts               │
│  ├── scene_parser.py            ← Uses gemini.py + schemas     │
│  ├── character_gen.py           ← Uses gemini.py + schemas     │
│  ├── api.ts                     ← Uses types.ts only           │
│  └── InputForm.tsx              ← Uses types.ts only           │
│                                                                 │
│  TIER 2 (Requires Tier 1 outputs)                               │
│  ├── cut_planner.py             ← Needs Scene + Character      │
│  ├── validator.py               ← Needs CutPlan + Character    │
│  ├── image_gen.py + prompts     ← Needs Cut + Character        │
│  └── ProgressTracker.tsx        ← Uses types.ts only           │
│                                                                 │
│  TIER 3 (Requires Tier 2)                                       │
│  ├── orchestrator.py            ← Wires all pipeline steps     │
│  ├── main.py                    ← API endpoints + SSE          │
│  └── CharacterCards.tsx         ← Renders CharacterSheet       │
│                                                                 │
│  TIER 4 (Requires Tier 3)                                       │
│  ├── WebtoonStrip.tsx           ← Renders CutPlan + images     │
│  ├── CutPanel.tsx               ← Single panel + regenerate    │
│  └── page.tsx                   ← Assembles all components     │
│                                                                 │
│  TIER 5 (Integration & Polish)                                  │
│  ├── End-to-end testing                                         │
│  ├── Error states & loading UI                                  │
│  └── Demo preparation                                           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Parallel Work Boundaries

| Work Stream                            | Can work independently after      | Touches                                                               |
| -------------------------------------- | --------------------------------- | --------------------------------------------------------------------- |
| Pipeline Steps 1–3 (text)              | Tier 0                            | `scene_parser.py`, `character_gen.py`, `cut_planner.py`, `prompts.py` |
| Pipeline Step 4–5 (validation + image) | Tier 0                            | `validator.py`, `image_gen.py`                                        |
| API Layer                              | Tier 0 + basic pipeline structure | `main.py`, `orchestrator.py`                                          |
| Frontend Components                    | Tier 0 (types.ts)                 | All `.tsx` files, `api.ts`                                            |

**Critical path**: `schemas.py` → any pipeline step → `orchestrator.py` → `main.py` → full integration.

---

## 8. Risks & Mitigations

### 8.1 Rate Limiting

| Risk                              | Impact                              | Mitigation                                                         |
| --------------------------------- | ----------------------------------- | ------------------------------------------------------------------ |
| Gemini API rate limit (image gen) | Image generation fails mid-pipeline | Batch size = 3, 2s delay between batches. Max 3 retries per image. |
| Burst of concurrent users         | API overload                        | Hackathon scope = single user demo. In-memory storage sufficient.  |

### 8.2 Image Generation Failures

| Risk                        | Impact                              | Mitigation                                                                                                         |
| --------------------------- | ----------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| Image gen returns `None`    | Missing panel in final output       | 3 retries with modified prompt. Failed panels get `image_base64=""`. Frontend shows placeholder.                   |
| Image quality inconsistency | Different art styles across panels  | Character `appearance_keywords` (5 per character) injected into every prompt. Tone style description standardized. |
| Safety filter blocks image  | Panel blocked despite valid content | Rating guidance included in prompt. No explicit content requested.                                                 |

### 8.3 Character Drift

| Risk                                         | Impact               | Mitigation                                                                                                                                                                                               |
| -------------------------------------------- | -------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Same character looks different across panels | Visual inconsistency | `appearance_keywords` (exactly 5) are reused verbatim in all image prompts. `prohibited_visuals` prevent unwanted elements. Reference images generated in Step 2 (future: can be passed as image input). |

### 8.4 Structured Output Failures

| Risk                          | Impact                  | Mitigation                                                                                                                                        |
| ----------------------------- | ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| Gemini returns invalid JSON   | Pipeline stage crashes  | Pydantic `model_validate_json()` raises clear validation error. `response_mime_type="application/json"` + `response_schema` enforced in API call. |
| Wrong number of cuts (not 12) | Schema validation fails | `CutPlan.cuts` has `min_length=12, max_length=12`. Gemini structured output enforces schema.                                                      |

### 8.5 Prompt Injection

| Risk                                      | Impact                    | Mitigation                                                                                                                                                  |
| ----------------------------------------- | ------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| User manuscript contains adversarial text | Unexpected model behavior | System prompts clearly define role and output format. Structured output schema constrains response shape. Manuscript max 2,000 chars limits attack surface. |

### 8.6 Performance

| Risk                            | Impact                         | Mitigation                                                                                                                                                         |
| ------------------------------- | ------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Total pipeline > 3 min          | Poor demo experience           | SSE progress updates keep user engaged. Image gen is bottleneck — batch parallelism (3 concurrent) balances speed vs. rate limits. Steps 1–4 are fast (text-only). |
| Large base64 images in response | Slow result fetch, high memory | Hackathon scope — acceptable. Production would use object storage URLs.                                                                                            |

---

## 9. Verification

### 9.1 Unit-Level Checks

| Check                        | Command / Method                                                |
| ---------------------------- | --------------------------------------------------------------- |
| Backend starts without error | `cd backend && python run.py` (check for import errors)         |
| Frontend builds              | `cd frontend && npm run build`                                  |
| Schema parity                | Compare `schemas.py` fields with `types.ts` interfaces (manual) |
| Env setup                    | Copy `.env.example` to `.env`, add real `GOOGLE_API_KEY`        |

### 9.2 End-to-End Test Scenario

**Prerequisite**: Backend running on `:8000`, Frontend on `:3000`, valid `GOOGLE_API_KEY` in `.env`.

| Step | Action                                                        | Expected Result                                           |
| ---- | ------------------------------------------------------------- | --------------------------------------------------------- |
| 1    | Open `http://localhost:3000`                                  | Input form visible                                        |
| 2    | Paste sample novel text (≤2000 chars)                         | Char counter updates                                      |
| 3    | Select genre=Romance, tone=Emotional, rating=All, lang=Korean | Options highlighted                                       |
| 4    | Click "Generate Conti"                                        | Progress tracker appears, Step 1 starts                   |
| 5    | Wait for pipeline                                             | Steps 1→5 complete sequentially, progress updates visible |
| 6    | View result                                                   | Character cards shown, 12 cut panels rendered vertically  |
| 7    | Scroll through cuts                                           | Each panel has image + dialogue/narration/sfx overlays    |
| 8    | Click "Regenerate" on any panel                               | New image replaces old one                                |

### 9.3 API Smoke Test (curl)

```bash
# 1. Start generation
TASK_ID=$(curl -s -X POST http://localhost:8000/api/generate \
  -H "Content-Type: application/json" \
  -d '{"manuscript":"어느 봄날 아침, 민지는 텅 빈 교실에 혼자 앉아 있었다. 창밖으로 벚꽃이 흩날렸다.","genre":"romance","tone":"emotional","rating":"all","output_language":"ko"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['task_id'])")
echo "Task ID: $TASK_ID"

# 2. Stream progress (SSE)
curl -N http://localhost:8000/api/progress/$TASK_ID

# 3. Get result (after pipeline completes)
curl -s http://localhost:8000/api/result/$TASK_ID | python3 -c "
import sys, json
r = json.load(sys.stdin)
print(f'Characters: {len(r[\"characters\"][\"characters\"])}')
print(f'Cuts: {len(r[\"cuts\"][\"cuts\"])}')
print(f'Images: {len(r[\"images\"])}')
imgs_ok = sum(1 for i in r['images'] if i['image_base64'])
print(f'Images with content: {imgs_ok}/12')
"

# 4. Regenerate a single cut
curl -s -X POST http://localhost:8000/api/regenerate-cut/$TASK_ID/1 \
  | python3 -c "import sys,json; r=json.load(sys.stdin); print(f'Cut {r[\"cut_id\"]}: {\"OK\" if r[\"image_base64\"] else \"FAILED\"}')"
```

### 9.4 Sample Test Manuscripts

**Korean (Romance)**:

> 어느 봄날 아침, 민지는 텅 빈 교실에 혼자 앉아 있었다. 창밖으로 벚꽃이 흩날렸다. 문이 열리며 준혁이 들어왔다. "왜 이렇게 일찍 왔어?" 민지가 물었다. 준혁은 대답 대신 손에 들린 편지를 내밀었다.

**English (Mystery)**:

> The old lighthouse keeper hadn't been seen in three days. Detective Park climbed the spiral staircase, each step creaking under her weight. At the top, the lamp still rotated, casting shadows across an empty chair. But the logbook was open to today's date, and in fresh ink, someone had written: "They're watching from the water."
