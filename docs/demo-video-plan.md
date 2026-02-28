# 9-Cut Teaser Studio -- Hackathon Demo Video Production Plan

Google Gemini 3 Seoul Hackathon (2026-02-28) demo video production guide.

**Project**: "9-Cut Teaser Studio" -- a full-stack AI pipeline that transforms novel text into Instagram 9-panel webtoon teasers + video.

**Core Message**:

> "One novel input, four Gemini models in relay, producing complete marketing assets (images + video) automatically."

---

## Judging Criteria Analysis

| Criteria                    | Weight  | Our Strategy                                                     |
| --------------------------- | ------- | ---------------------------------------------------------------- |
| **Technical Execution**     | **40%** | 4-model Gemini relay pipeline -- prove with architecture diagram |
| **Innovation / Wow Factor** | **30%** | Hook with finished result in first 10s + 60s live demo           |
| **Potential Impact**        | **20%** | Web novel market problem definition + commercialization vision   |
| **Presentation / Demo**     | **10%** | Pro-level editing, clear narration, visual consistency           |

> **Critical Rule**: Judges may not watch past 3 minutes. The first 30 seconds decide everything.

---

## Gemini Ecosystem Usage (4 Models)

```
Stitch ──→ Gemini 3.1 Pro ──→ Nano Banana 2 ──→ Veo 3.1
(Design)    (Text Pipeline)    (Image Gen)       (Video Gen)
  Design        Brain            Visualize          Animate
```

---

## Scene-by-Scene Breakdown

**Total Runtime: 2 min 40 sec (160 seconds)**

---

### SCENE 1: Hook -- "This Was Made by AI" (0:00 ~ 0:10)

**Purpose**: Capture the judge's attention within 5 seconds. Show the result first.

| Element        | Detail                                                                                       |
| -------------- | -------------------------------------------------------------------------------------------- |
| **Screen**     | Finished 9-panel webtoon grid (3x3) fullscreen. Use the most impressive pre-generated sample |
| **Transition** | Fade in (1s) -> Grid hold (4s) -> Zoom out into app screen                                   |
| **Subtitle**   | Bottom: "Generated in 2 minutes from a novel excerpt"                                        |
| **BGM**        | Cinematic whoosh + subtle beat drop                                                          |

**Narration:**

> "What you're seeing is a 9-panel webtoon teaser -- automatically generated from a novel in under two minutes."

**Criteria mapping**: Innovation / Wow Factor (30%)

---

### SCENE 2: Problem Definition (0:10 ~ 0:25)

**Purpose**: Communicate why we built this -- problem size and current pain in 15 seconds.

| Element                  | Detail                                                                      |
| ------------------------ | --------------------------------------------------------------------------- |
| **Screen**               | Minimal infographic slides (dark background, highlighted stats)             |
| **Visual 1** (0:10-0:15) | Number animation: "50,000+ web novels published yearly"                     |
| **Visual 2** (0:15-0:20) | Contrast graphic: "Only 1% have visual teasers"                             |
| **Visual 3** (0:20-0:25) | Cost comparison: "Manual: 2 weeks + $800" -> "9-Cut Studio: 2 minutes + $0" |
| **Transition**           | Slide -> App screen naturally                                               |

**Narration:**

> "Over fifty thousand web novels are published every year, but less than one percent have visual marketing materials. Creating a teaser manually takes a designer two weeks and hundreds of dollars. We're changing that."

**Criteria mapping**: Potential Impact (20%)

---

### SCENE 3: Live Demo -- Full Pipeline (0:25 ~ 1:25)

**Purpose**: Show the actual working app. 60 seconds, the heart of the video.

#### Scene 3-1: Story Input (0:25 ~ 0:35)

| Element       | Detail                                                  |
| ------------- | ------------------------------------------------------- |
| **Screen**    | StoryInputScreen -- dark background, large text area    |
| **Action**    | Paste pre-prepared novel text (typing effect or Ctrl+V) |
| **Highlight** | Briefly show "Summary/Full text" toggle                 |
| **Subtitle**  | "Step 1: Paste your novel text"                         |

**Narration:**

> "Start by pasting any novel excerpt. The app accepts both summaries and full text."

#### Scene 3-2: Meta Prompt Review (0:35 ~ 0:42)

| Element       | Detail                                                                                |
| ------------- | ------------------------------------------------------------------------------------- |
| **Screen**    | MetaPrompt1Screen -- AI-generated meta prompt, editable text area, blue gradient glow |
| **Action**    | Briefly show auto-generated narrative structure -> Click "Regenerate" once            |
| **Highlight** | Gemini 3.1 Pro's structured output capability                                         |

**Narration:**

> "Gemini 3.1 Pro analyzes the narrative and generates a structured scene plan -- fully editable."

#### Scene 3-3: Visual Style Selection (0:42 ~ 0:50)

| Element            | Detail                                                                                |
| ------------------ | ------------------------------------------------------------------------------------- |
| **Screen**         | MetaPrompt2Screen -- 4 style card grid                                                |
| **Action**         | Hover over each card (0.7s enlarge animation) -> Select "Cinematic Art" or "2D Anime" |
| **Highlight**      | Blue glow + "Selected" badge animation on selection                                   |
| **Styles to show** | Cinematic Art, 2D Anime, Oil Painting, Digital Sketch -- hover all 4                  |

**Narration:**

> "Choose from four visual styles -- from webtoon cel-shading to cinematic art."

#### Scene 3-4: Generation Progress (0:50 ~ 1:10)

| Element         | Detail                                                                                                        |
| --------------- | ------------------------------------------------------------------------------------------------------------- |
| **Screen**      | ProcessingStateScreen -- spinning circle animation + 3 pulsing dots + blue glow                               |
| **Action**      | Real-time SSE progress -- 5-stage display (Scene Parse -> Character Gen -> Cut Plan -> Validate -> Image Gen) |
| **Editing tip** | If actual wait is long, use timelapse (x4~x8 speed). Insert stage name subtitles at each transition           |
| **Highlight**   | "auto_awesome" icon center animation is visually appealing -- hold this shot longer                           |

**Narration:**

> "Behind the scenes, a five-stage AI pipeline kicks in. Gemini parses scenes, designs characters, plans nine sequential cuts, validates narrative coherence, and generates each panel -- all automatically."

#### Scene 3-5: Result -- 9-Cut Grid (1:10 ~ 1:20)

| Element        | Detail                                                                                              |
| -------------- | --------------------------------------------------------------------------------------------------- |
| **Screen**     | Finished 9-panel grid (3x3). Each image contains speech bubble text                                 |
| **Action**     | Full grid view -> Zoom into individual panels (show speech bubble readability) -> Back to full view |
| **Transition** | Tap to zoom in/out or editor zoom                                                                   |

**Narration:**

> "And here it is -- nine panels with embedded dialogue, ready for Instagram's three-by-three grid."

#### Scene 3-6: Veo Video Generation (1:20 ~ 1:25)

| Element       | Detail                                                                  |
| ------------- | ----------------------------------------------------------------------- |
| **Screen**    | VideoExportScreen -- 9:16 ratio video preview + source frame thumbnails |
| **Action**    | Click play button -> Short video playback (3-5s preview)                |
| **Highlight** | "Static image -> motion video" transformation is Veo 3.1's role         |

**Narration:**

> "Then Veo 3.1 transforms the static panels into a short-form teaser video -- perfect for Reels and TikTok."

**Criteria mapping**: Innovation / Wow Factor (30%) + Technical Execution (40%)

---

### SCENE 4: Gemini Ecosystem Architecture (1:25 ~ 2:05)

**Purpose**: Directly target Technical Execution (40%). "This team deeply understands and leverages the Gemini ecosystem."

| Element       | Detail                                                                              |
| ------------- | ----------------------------------------------------------------------------------- |
| **Screen**    | Custom architecture diagram (dark background, neon blue accent, Gemini model logos) |
| **Animation** | Left-to-right data flow sequential highlight (each model lights up in turn)         |

#### Diagram Layout:

```
┌─────────────┐    ┌──────────────────┐    ┌─────────────────┐    ┌──────────────┐
│   STITCH     │    │  GEMINI 3.1 PRO  │    │ NANO BANANA 2   │    │   VEO 3.1    │
│   Design     │ →  │  Text Pipeline   │ →  │ Image Generation │ →  │ Video Gen    │
│              │    │                  │    │                  │    │              │
│ UI/UX Design │    │ 4-Stage Pipeline │    │ 9 Panels + Anchor│    │ Motion Video │
│ Prototyping  │    │ Structured JSON  │    │ Reference Chain  │    │ Short-form   │
└─────────────┘    └──────────────────┘    └─────────────────┘    └──────────────┘
```

#### Per-Model Detail (text overlay on screen):

**Stitch (highlight 5s)**

- Subtitle: "Stitch: AI-native design for rapid UX prototyping"
- Narration: "We started with Stitch to rapidly prototype and validate our user experience."

**Gemini 3.1 Pro (highlight 12s)**

- Subtitle: "4-stage text pipeline: Parse -> Character -> Plan -> Validate"
- Sub-diagram: Scene Parser -> Character Generator -> Cut Planner -> Validator
- Narration: "Gemini 3.1 Pro powers our four-stage text pipeline. It parses scenes, generates character profiles, plans nine sequential cuts, and validates narrative coherence -- all with structured JSON output and specialized system instructions for each role."

**Nano Banana 2 (highlight 10s)**

- Subtitle: "Character anchor + reference chain for 9-panel consistency"
- Sub-diagram: Anchor Image -> Panel 1 (ref: anchor) -> Panel 2 (ref: anchor + panel 1) -> ... -> Panel 9
- Narration: "Nano Banana 2 generates all nine panels. We maintain character consistency through an anchor image strategy -- each panel references the character anchor plus the previous panel."

**Veo 3.1 (highlight 8s)**

- Subtitle: "Static webtoon -> motion teaser for short-form content"
- Narration: "Finally, Veo 3.1 converts the static nine-cut grid into a motion teaser video -- bridging the gap between webtoon and short-form video content."

**Criteria mapping**: **Technical Execution (40%)** -- most important section

---

### SCENE 5: Technical Highlights (2:05 ~ 2:25)

**Purpose**: Quickly show technical depth with 3 key points.

| Time      | Highlight                   | Screen                                                                              | Narration                                                                                                                 |
| --------- | --------------------------- | ----------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| 2:05-2:11 | **Character Consistency**   | Anchor image + 9-panel character comparison (same character appearing consistently) | "Our reference chain strategy ensures character consistency across all nine panels."                                      |
| 2:11-2:17 | **Structured Output**       | JSON schema code snippet (Pydantic model) + actual JSON output example              | "Every AI response follows strict Pydantic schemas -- ensuring reliable, parseable output every time."                    |
| 2:17-2:23 | **Production Architecture** | Tech stack icon array: FastAPI + async/await + SQLite + SSE + 209 tests             | "Built with FastAPI, async pipelines, SQLite persistence, real-time SSE streaming, and over two hundred edge-case tests." |

**Criteria mapping**: Technical Execution (40%)

---

### SCENE 6: Vision & Closing (2:25 ~ 2:40)

**Purpose**: Commercialization potential + memorable ending.

| Element                  | Detail                                                                                                 |
| ------------------------ | ------------------------------------------------------------------------------------------------------ |
| **Screen 1** (2:25-2:32) | Commercialization vision diagram: Web Novel Platform API -> Auto Teaser Pipeline -> Reader Acquisition |
| **Screen 2** (2:32-2:37) | One-line vision: "Empowering every author with AI-powered marketing tools"                             |
| **Screen 3** (2:37-2:40) | Team name + project name + Gemini 3 logo. Fade out                                                     |
| **BGM**                  | Resolve chord                                                                                          |

**Narration:**

> "Our vision: integrate with web novel platforms to automatically generate visual teasers -- making professional marketing accessible to every author. This is 9-Cut Teaser Studio, powered by the Gemini ecosystem."

**Criteria mapping**: Potential Impact (20%) + Presentation (10%)

---

## Full Narration Script (Copy-Paste Ready)

### English Narration (~160 seconds)

```
[0:00 -- Hook]
What you're seeing is a 9-panel webtoon teaser -- automatically generated
from a novel in under two minutes.

[0:10 -- Problem]
Over fifty thousand web novels are published every year, but less than
one percent have visual marketing materials. Creating a teaser manually
takes a designer two weeks and hundreds of dollars. We're changing that.

[0:25 -- Demo: Input]
Start by pasting any novel excerpt. The app accepts both summaries and
full text.

[0:35 -- Demo: Meta Prompt]
Gemini 3.1 Pro analyzes the narrative and generates a structured scene
plan -- fully editable.

[0:42 -- Demo: Style]
Choose from four visual styles -- from webtoon cel-shading to cinematic art.

[0:50 -- Demo: Generation]
Behind the scenes, a five-stage AI pipeline kicks in. Gemini parses scenes,
designs characters, plans nine sequential cuts, validates narrative coherence,
and generates each panel -- all automatically.

[1:10 -- Demo: Result]
And here it is -- nine panels with embedded dialogue, ready for Instagram's
three-by-three grid.

[1:20 -- Demo: Video]
Then Veo 3.1 transforms the static panels into a short-form teaser video --
perfect for Reels and TikTok.

[1:25 -- Architecture]
Let me show you how we leverage the full Gemini ecosystem.

We started with Stitch to rapidly prototype and validate our user experience.

Gemini 3.1 Pro powers our four-stage text pipeline. It parses scenes,
generates character profiles, plans nine sequential cuts, and validates
narrative coherence -- all with structured JSON output and specialized
system instructions for each role.

Nano Banana 2 generates all nine panels. We maintain character consistency
through an anchor image strategy -- each panel references the character
anchor plus the previous panel.

Finally, Veo 3.1 converts the static nine-cut grid into a motion teaser
video -- bridging the gap between webtoon and short-form video content.

[2:05 -- Technical Highlights]
Our reference chain strategy ensures character consistency across all
nine panels.

Every AI response follows strict Pydantic schemas -- ensuring reliable,
parseable output every time.

Built with FastAPI, async pipelines, SQLite persistence, real-time SSE
streaming, and over two hundred edge-case tests.

[2:25 -- Vision]
Our vision: integrate with web novel platforms to automatically generate
visual teasers -- making professional marketing accessible to every author.

This is 9-Cut Teaser Studio, powered by the Gemini ecosystem.
```

---

## Judge Appeal Points Checklist

### Technical Execution (40%) -- Must Demonstrate

- [ ] **4 Gemini models used**: Stitch + Gemini 3.1 Pro + Nano Banana 2 + Veo 3.1
- [ ] **Structured JSON output**: `response_mime_type="application/json"` + Pydantic schemas
- [ ] **System instructions**: 5 expert roles (scene_parser, character_gen, cut_planner, validator, image_gen)
- [ ] **Multimodal I/O**: Text -> Image, Image -> Image (reference), Image -> Video
- [ ] **Async architecture**: FastAPI async + aiosqlite + SSE streaming
- [ ] **Error handling**: Quota/Rate Limit, Safety Block, JSON parse validation
- [ ] **Tests**: 209+ edge-case tests

### Innovation / Wow Factor (30%) -- Must Impress

- [ ] **Finished result in first 10 seconds** (Before -> After)
- [ ] **60-second live demo**: Actually working app (not a mock)
- [ ] **Character consistency**: Anchor image + reference chain (novel approach)
- [ ] **4-model relay**: Pipeline orchestration, not single-model usage
- [ ] **In-image speech bubbles**: Model-native rendering, not overlay

### Potential Impact (20%) -- Prove Market Viability

- [ ] **Problem size**: 50,000+ web novels/year, teaser adoption rate < 1%
- [ ] **Cost reduction**: Designer 2 weeks + $800 -> AI 2 minutes + $0
- [ ] **Target market**: Web novel platforms (KakaoPage, Naver Series, Wattpad, etc.)
- [ ] **Scalability**: API integration with platforms

### Presentation / Demo (10%) -- Be Professional

- [ ] **Clean editing**: Remove unnecessary wait times, use timelapse
- [ ] **English narration + subtitles**: For global judges
- [ ] **Architecture diagram**: Visually clear technical explanation
- [ ] **Under 3 minutes**: 2 min 40 sec target

---

## Pre-Production Checklist

### Demo Input Data Preparation

- [ ] **Prepare 3 novel texts** (Korean 1, English 1, Japanese 1) -- pre-test for most impressive results
- [ ] **Optimal input criteria**: 2-3 distinct characters, rich visual scene transitions, 200-500 characters
- [ ] **Rehearse 3+ times**: Test each style, select best quality style+text combination

### Technical Stability

- [ ] Backend server running: `uvicorn app.main:app --reload --port 8000`
- [ ] Frontend server running: `npm run dev`
- [ ] CORS configuration verified (frontend <-> backend communication)
- [ ] API key validity confirmed (Gemini API quota headroom)
- [ ] E2E pipeline test: text input -> 9-panel generation complete (no errors)
- [ ] Veo video generation test
- [ ] Network stability (backup pre-generated results in case of API failure during demo)

### Recording Equipment

- [ ] **Screen recording**: OBS Studio or macOS built-in (Command+Shift+5)
- [ ] **Resolution**: 1920x1080 (16:9)
- [ ] **Frame rate**: 30fps or higher
- [ ] **Microphone**: External mic recommended (watch for built-in mic noise)
- [ ] **Editing tool**: iMovie / DaVinci Resolve / CapCut

### Visual Assets to Create

- [ ] **Architecture diagram** -- Create with Stitch / Figma / Canva
  - Dark background (#0c1427), neon blue accent (#2b6cee)
  - Include Gemini model logos/icons
  - Left-to-right data flow arrows
- [ ] **Infographic slides** -- For problem definition section
  - "50,000+" stat, "< 1%" contrast, "$800 vs $0" comparison
- [ ] **Tech stack icons** -- FastAPI, React, SQLite, Python logo arrangement

---

## Submission Checklist (Devpost)

| Required Item                       | Status | Notes                                                   |
| ----------------------------------- | ------ | ------------------------------------------------------- |
| Text description (~200 words)       | [ ]    | Emphasize 4-model Gemini integration                    |
| Public project link or working demo | [ ]    | Deploy URL or AI Studio link                            |
| Public code repository URL          | [ ]    | GitHub repo (check if public is required for hackathon) |
| Demo video (< 3 min)                | [ ]    | 2 min 40 sec target                                     |

### 200-Word Description Draft

```
9-Cut Teaser Studio transforms novel text into Instagram-ready 9-panel
webtoon teasers using four Gemini ecosystem products in a single pipeline.

We use Stitch for AI-native UI/UX prototyping, Gemini 3.1 Pro for a
four-stage text pipeline (scene parsing, character generation, cut planning,
and narrative validation) with structured JSON output, Nano Banana 2 for
generating nine consistent panels with an anchor image reference chain
strategy, and Veo 3.1 for converting static panels into short-form teaser
videos.

The problem: Over 50,000 web novels are published annually, but fewer
than 1% have visual marketing materials. Professional teaser creation
costs $800+ and takes two weeks. Our solution automates this in under
two minutes.

Technical highlights include domain-driven architecture with FastAPI,
async five-stage AI pipeline with real-time SSE progress streaming,
SQLite persistence for pipeline state management, Pydantic schema
validation for all AI outputs, character consistency through reference
image chaining, and 209+ edge-case tests.

Our vision: API integration with web novel platforms to automatically
generate visual teasers, making professional marketing accessible to
every author worldwide.
```

---

## Sources

- [Devpost: 6 Tips for winning hackathon demo video](https://info.devpost.com/blog/6-tips-for-making-a-hackathon-demo-video)
- [Devpost: How to present a successful hackathon demo](https://info.devpost.com/blog/how-to-present-a-successful-hackathon-demo)
- [Devpost: Hackathon Judging Tips from 5 seasoned judges](https://info.devpost.com/blog/hackathon-judging-tips)
- [How to Win a Hackathon -- Judge, Mentor & Participant perspective](https://medium.com/thecapital/how-to-win-a-hackathon-from-a-judge-mentor-and-participant-perspective-b7bfe9cd20a1)
- [AngelHack: 10 Tips for hackathon demo](https://angelhack.com/blog/10-tips-to-help-you-rock-your-next-hackathon-demo/)
- [Gemini 3 Hackathon -- Devpost](https://gemini3.devpost.com/)
