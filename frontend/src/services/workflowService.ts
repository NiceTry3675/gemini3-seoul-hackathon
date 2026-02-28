import {
  FRAME_IMAGE_POOL,
  FRAME_SEQUENCE,
  FRAME_TAGS,
  STYLE_TONE_BY_ID,
} from '../data/workflowData';
import type {
  FrameOption,
  PipelineOutputLanguage,
  PipelinePreviewModel,
  PipelineProgressEvent,
  PipelineResultModel,
  PipelineStyleTemplate,
  SourceFrame,
  TeaserApiResult,
  VideoExportModel,
  VisualStyleId,
} from '../types/workflow';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const DEFAULT_API_BASE_URL = 'http://127.0.0.1:8000';

const STYLE_SUBTITLES: Record<VisualStyleId, string[]> = {
  cinematic_realism: ['Neon Noir Style', 'Cyberpunk Style', 'Cinematic Style', 'Experimental Style'],
  webtoon_cel: ['Sakura Pulse', 'Urban Neon', 'Skyline Slice', 'Action Frame'],
  watercolor_dream: ['Gallery Warmth', 'Renaissance Mood', 'Brushwork Scene', 'Canvas Grain'],
  digital_masterpaint: ['Pencil Burst', 'Charcoal Shade', 'Ink Motion', 'Storyboard Draft'],
};

const STYLE_DESCRIPTORS: Record<VisualStyleId, string> = {
  cinematic_realism: 'photorealistic cinematic film still, dramatic lighting, 4K',
  webtoon_cel: 'Korean webtoon cel-shaded illustration, bold outlines, vibrant colors',
  watercolor_dream: 'delicate watercolor painting, soft washes, painterly texture',
  digital_masterpaint: 'detailed digital matte painting, concept art, masterwork',
};

const STYLE_REFERENCE_ORDER: VisualStyleId[] = [
  'cinematic_realism',
  'webtoon_cel',
  'watercolor_dream',
  'digital_masterpaint',
];

const NEGATIVE_HINT =
  'ugly, deformed, blurry, low quality, watermark, text, duplicate, cropped';

// ---------------------------------------------------------------------------
// Exported types
// ---------------------------------------------------------------------------

export interface StartPipelineRequest {
  manuscript: string;
  style_template: PipelineStyleTemplate;
  output_language: PipelineOutputLanguage;
  genre?: string;
  tone?: string;
}

export interface GeneratedReferenceImage {
  style: VisualStyleId;
  imageBase64: string;
}

export interface SseHandlers {
  onProgress: (event: PipelineProgressEvent) => void;
  onComplete: (result: PipelineResultModel) => void;
  onError: (message: string) => void;
}

export interface VideoGenCallbacks {
  onProgress: (progress: number, message: string) => void;
  onComplete: (videoBase64: string, duration: number) => void;
  onError: (error: string) => void;
}

// ---------------------------------------------------------------------------
// Core utilities
// ---------------------------------------------------------------------------

export function getApiBaseUrl(): string {
  const envUrl =
    typeof import.meta !== 'undefined'
      ? (import.meta as { env?: Record<string, string> }).env?.VITE_API_BASE_URL
      : undefined;
  return (envUrl || DEFAULT_API_BASE_URL).replace(/\/$/, '');
}

function hashString(input: string): number {
  let hash = 2166136261;
  for (let i = 0; i < input.length; i += 1) {
    hash ^= input.charCodeAt(i);
    hash = Math.imul(hash, 16777619);
  }
  return hash >>> 0;
}

// ---------------------------------------------------------------------------
// Error / SSE parsing helpers
// ---------------------------------------------------------------------------

function parseErrorMessage(error: unknown): string {
  if (error instanceof Error) return error.message;
  return String(error ?? 'Unknown error');
}

function parseJsonPayload<T>(text: string): T | null {
  try {
    return JSON.parse(text) as T;
  } catch {
    return null;
  }
}

function parseSseFrame(line: string): Record<string, unknown> | null {
  if (!line.startsWith('data: ')) return null;
  return parseJsonPayload<Record<string, unknown>>(line.slice(6));
}

async function parseHttpError(response: Response): Promise<string> {
  try {
    const text = await response.text();
    return `HTTP ${response.status}: ${text}`;
  } catch {
    return `HTTP ${response.status}`;
  }
}

// ---------------------------------------------------------------------------
// Frame options
// ---------------------------------------------------------------------------

export function generateFrameOptions(frameIndex: number, style: VisualStyleId): FrameOption[] {
  const pool = FRAME_IMAGE_POOL[style];
  const subtitles = STYLE_SUBTITLES[style];
  const offset = hashString(`${style}:${frameIndex}`) % pool.length;

  return Array.from({ length: 4 }).map((_, optionIdx) => {
    const imageIndex = (offset + optionIdx) % pool.length;
    const subtitleIndex = (frameIndex + optionIdx) % subtitles.length;

    return {
      id: `f${frameIndex}-opt-${optionIdx + 1}`,
      label: `Option ${String.fromCharCode(65 + optionIdx)}`,
      subtitle: subtitles[subtitleIndex],
      tag: FRAME_TAGS[(offset + optionIdx) % FRAME_TAGS.length],
      description: `${FRAME_SEQUENCE[frameIndex - 1]} variation ${optionIdx + 1}`,
      imageUrl: pool[imageIndex],
    };
  });
}

// ---------------------------------------------------------------------------
// Style template mapping
// ---------------------------------------------------------------------------

export function mapVisualStyleToPipelineTemplate(style: VisualStyleId): PipelineStyleTemplate {
  return style as PipelineStyleTemplate;
}

// ---------------------------------------------------------------------------
// Reference image generation
// ---------------------------------------------------------------------------

function buildReferencePrompt(style: VisualStyleId, characterVisualPrompt: string): string {
  const descriptor = STYLE_DESCRIPTORS[style];
  return [
    descriptor,
    characterVisualPrompt,
    `NEGATIVE: ${NEGATIVE_HINT}`,
  ]
    .filter(Boolean)
    .join(', ');
}

async function generateReferenceImage(
  style: VisualStyleId,
  characterVisualPrompt: string,
): Promise<GeneratedReferenceImage> {
  const prompt = buildReferencePrompt(style, characterVisualPrompt);
  const response = await fetch(`${getApiBaseUrl()}/api/image/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt, style_template: style }),
  });

  if (!response.ok) {
    throw new Error(await parseHttpError(response));
  }

  const data = await response.json() as { image_base64: string };
  return { style, imageBase64: data.image_base64 };
}

export async function generateReferenceImages(
  characterVisualPrompt: string,
  styles: VisualStyleId[] = STYLE_REFERENCE_ORDER,
): Promise<GeneratedReferenceImage[]> {
  const results = await Promise.allSettled(
    styles.map((style) => generateReferenceImage(style, characterVisualPrompt)),
  );

  return results
    .filter((r): r is PromiseFulfilledResult<GeneratedReferenceImage> => r.status === 'fulfilled')
    .map((r) => r.value);
}

// ---------------------------------------------------------------------------
// Pipeline preview
// ---------------------------------------------------------------------------

export async function fetchPipelinePreview(
  manuscript: string,
  styleTemplate: PipelineStyleTemplate,
  outputLanguage: PipelineOutputLanguage = 'ko',
  genre = '',
  tone = '',
): Promise<PipelinePreviewModel> {
  const response = await fetch(`${getApiBaseUrl()}/api/prompt-preview`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      manuscript,
      style_template: styleTemplate,
      output_language: outputLanguage,
      genre,
      tone,
    }),
  });

  if (!response.ok) {
    throw new Error(await parseHttpError(response));
  }

  return response.json() as Promise<PipelinePreviewModel>;
}

// ---------------------------------------------------------------------------
// Generate media from preview (POST /api/teaser -> PipelineResultModel)
// ---------------------------------------------------------------------------

export async function generateMediaFromPreview(
  preview: PipelinePreviewModel,
  styleTemplate: PipelineStyleTemplate,
  outputLanguage: PipelineOutputLanguage = 'ko',
): Promise<PipelineResultModel> {
  const response = await fetch(`${getApiBaseUrl()}/api/teaser`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      preview,
      style_template: styleTemplate,
      output_language: outputLanguage,
    }),
  });

  if (!response.ok) {
    throw new Error(await parseHttpError(response));
  }

  return response.json() as Promise<PipelineResultModel>;
}

// ---------------------------------------------------------------------------
// SSE pipeline generation (POST /api/pipeline/generate)
// ---------------------------------------------------------------------------

export async function startPipelineGeneration(
  request: StartPipelineRequest,
  handlers: SseHandlers,
  abortSignal?: AbortSignal,
): Promise<void> {
  const response = await fetch(`${getApiBaseUrl()}/api/pipeline/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
    signal: abortSignal,
  });

  if (!response.ok) {
    handlers.onError(await parseHttpError(response));
    return;
  }

  const reader = response.body?.getReader();
  if (!reader) {
    handlers.onError('No response body from pipeline');
    return;
  }

  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() ?? '';

      for (const line of lines) {
        const frame = parseSseFrame(line);
        if (!frame) continue;

        const eventType = frame.type as string | undefined;

        if (eventType === 'progress') {
          handlers.onProgress(frame as unknown as PipelineProgressEvent);
        } else if (eventType === 'result' || eventType === 'complete') {
          handlers.onComplete(frame as unknown as PipelineResultModel);
        } else if (eventType === 'error') {
          handlers.onError(String(frame.message ?? 'Pipeline error'));
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}

// ---------------------------------------------------------------------------
// Chanwoong: video generation via Veo 3.1 (POST /api/teaser/video, SSE)
// ---------------------------------------------------------------------------

export async function startVideoGeneration(
  cutsBase64: string[],
  callbacks: VideoGenCallbacks,
  abortSignal?: AbortSignal,
  storyPrompt?: string,
): Promise<void> {
  const response = await fetch(`${getApiBaseUrl()}/api/teaser/video`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      cuts_base64: cutsBase64,
      story_prompt: storyPrompt || '',
      aspect_ratio: '9:16',
      duration_per_cut: 5,
    }),
    signal: abortSignal,
  });

  if (!response.ok) {
    const error = await response.text();
    callbacks.onError(`Server error: ${error}`);
    return;
  }

  const contentType = response.headers.get('content-type') || '';

  if (contentType.includes('text/event-stream')) {
    const reader = response.body?.getReader();
    if (!reader) {
      callbacks.onError('No response body');
      return;
    }

    const decoder = new TextDecoder();
    let buffer = '';

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          const frame = parseSseFrame(line);
          if (!frame) continue;

          if (frame.type === 'progress') {
            const total = Number(frame.total_steps) || 1;
            const step = Number(frame.step) || 0;
            const pct = Math.round((step / total) * 100);
            callbacks.onProgress(pct, String(frame.message ?? ''));
          } else if (frame.type === 'result') {
            callbacks.onComplete(String(frame.video_base64 ?? ''), Number(frame.duration_seconds ?? 0));
          } else if (frame.type === 'error') {
            callbacks.onError(String(frame.message ?? 'Video generation error'));
          }
        }
      }
    } finally {
      reader.releaseLock();
    }
  } else {
    const result = await response.json() as { video_base64?: string; duration_seconds?: number };
    if (result.video_base64) {
      callbacks.onComplete(result.video_base64, result.duration_seconds ?? 0);
    } else {
      callbacks.onError('Unexpected response format');
    }
  }
}

// ---------------------------------------------------------------------------
// Chanwoong: legacy direct teaser call (POST /api/teaser -> TeaserApiResult)
// ---------------------------------------------------------------------------

export async function callTeaserApi(
  storyText: string,
  backendStyleId: string,
  outputLanguage = 'ko',
): Promise<TeaserApiResult> {
  const response = await fetch(`${getApiBaseUrl()}/api/teaser`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      source_text: storyText,
      style_template: backendStyleId,
      output_language: outputLanguage,
      max_image_cuts: 9,
    }),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`API error (${response.status}): ${errorText}`);
  }

  return response.json() as Promise<TeaserApiResult>;
}

// ---------------------------------------------------------------------------
// Chanwoong: convert TeaserApiResult to VideoExportModel
// ---------------------------------------------------------------------------

export function teaserResultToExport(
  result: TeaserApiResult,
  styleTone: string,
): VideoExportModel {
  const cuts = result.cuts.slice().sort((a, b) => a.index - b.index);
  const previewImageUrl =
    cuts.length > 0
      ? `data:image/png;base64,${cuts[0].image_base64}`
      : `data:image/png;base64,${result.character_anchor_image_base64}`;

  const sourceFrames: SourceFrame[] = cuts.map((cut) => ({
    index: cut.index,
    imageUrl: `data:image/png;base64,${cut.image_base64}`,
    selectedOptionLabel: `Cut ${cut.index}`,
  }));

  return {
    title: result.plan.title || 'Your Teaser',
    subtitle: 'AI-generated 9-cut teaser is ready for preview.',
    previewImageUrl,
    sourceFrames,
    settings: {
      musicStyle: styleTone,
      transition: 'Fade',
      duration: '15 Seconds',
      format: '1:1 Square',
    },
    renderSeconds: 0,
  };
}

// ---------------------------------------------------------------------------
// Suppress unused import warning for STYLE_TONE_BY_ID (used by consumers via
// re-export or available for callers building VideoExportModel settings)
// ---------------------------------------------------------------------------
export { STYLE_TONE_BY_ID };

// Re-export parseErrorMessage for consumers that display error strings
export { parseErrorMessage };
