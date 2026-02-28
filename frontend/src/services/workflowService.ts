import {
  FRAME_IMAGE_POOL,
  FRAME_SEQUENCE,
  FRAME_TAGS,
} from '../data/workflowData';
import type {
  FrameOption,
  PipelineOutputLanguage,
  PipelinePreviewModel,
  PipelineProgressEvent,
  PipelineResultModel,
  PipelineStyleTemplate,
  VisualStyleId,
} from '../types/workflow';

const DEFAULT_API_BASE_URL = 'http://127.0.0.1:8000';

const STYLE_SUBTITLES: Record<VisualStyleId, string[]> = {
  webtoon_cel: ['Webtoon Flow', 'Bold Linework', 'Flat Color Pop', 'Panel Clarity'],
  cinematic_realism: ['Neon Noir Style', 'Cinematic Depth', 'Drama Lighting', 'Epic Framing'],
  watercolor_dream: ['Pastel Wash', 'Soft Texture', 'Dream Haze', 'Poetic Mood'],
  digital_masterpaint: ['Rich Brushwork', 'Concept Splash', 'Color Burst', 'Hero Composition'],
};

const STYLE_DESCRIPTORS: Record<VisualStyleId, string> = {
  webtoon_cel: '2D cel shading, crisp line art, korean webtoon style, flat colors, clear lighting, high contrast.',
  cinematic_realism: 'Semi-realistic, intricate details, cinematic lighting, dramatic shadows, 8k resolution, photorealistic textures, depth of field.',
  watercolor_dream: 'Watercolor painting, soft pastel colors, traditional media, fluid brush strokes, dreamy and ethereal atmosphere, paper texture.',
  digital_masterpaint: 'High-quality digital painting, conceptual art, thick impasto strokes, rich and vibrant colors, masterpiece, highly detailed.',
};

const STYLE_REFERENCE_ORDER: VisualStyleId[] = [
  'webtoon_cel',
  'cinematic_realism',
  'watercolor_dream',
  'digital_masterpaint',
];

const NEGATIVE_HINT = 'no watermark, no logo, no signature, no extra text';

interface SseHandlers {
  onRunCreated: (runId: string) => void;
  onProgress: (event: PipelineProgressEvent) => void;
}

export interface StartPipelineRequest {
  manuscript: string;
  styleTemplate: PipelineStyleTemplate;
  outputLanguage?: PipelineOutputLanguage;
  genre?: string;
  tone?: string;
}

export interface GeneratedReferenceImage {
  styleTemplate: VisualStyleId;
  imageBase64: string;
  mimeType: string;
}

interface CompatPromptPreviewResponse {
  plan: unknown;
  anchor_prompt: string;
  cuts: Array<{
    index: number;
    prompt: string;
    reference_inputs: string[];
  }>;
  cut_plan: PipelinePreviewModel['cut_plan'];
  character_sheet: PipelinePreviewModel['characters'];
}

interface CompatTeaserResponse {
  plan: unknown;
  character_anchor_image_base64: string;
  cuts: Array<{
    index: number;
    image_base64: string;
  }>;
}

function getApiBaseUrl(): string {
  const configured = import.meta.env.VITE_API_BASE_URL;
  if (typeof configured !== 'string') {
    return DEFAULT_API_BASE_URL;
  }

  const trimmed = configured.trim();
  return trimmed.length > 0 ? trimmed.replace(/\/+$/, '') : DEFAULT_API_BASE_URL;
}

function hashString(input: string): number {
  let hash = 2166136261;
  for (let i = 0; i < input.length; i += 1) {
    hash ^= input.charCodeAt(i);
    hash = Math.imul(hash, 16777619);
  }
  return hash >>> 0;
}

function parseErrorMessage(payload: unknown): string {
  if (typeof payload === 'string' && payload.trim().length > 0) {
    return payload;
  }

  if (payload && typeof payload === 'object' && 'error' in payload) {
    const errorValue = (payload as { error?: unknown }).error;
    if (typeof errorValue === 'string' && errorValue.trim().length > 0) {
      return errorValue;
    }
  }

  return 'Backend request failed.';
}

function parseJsonPayload(payload: string): unknown {
  try {
    return JSON.parse(payload);
  } catch {
    const start = payload.indexOf('{');
    const end = payload.lastIndexOf('}');
    if (start !== -1 && end > start) {
      return JSON.parse(payload.slice(start, end + 1));
    }
    throw new Error('Received malformed SSE event payload.');
  }
}

function parseSseFrame(frame: string): { event: string; data: string } | null {
  const lines = frame.split('\n');
  let event = 'message';
  const dataLines: string[] = [];

  for (const rawLine of lines) {
    const line = rawLine.trimEnd();
    if (!line || line.startsWith(':')) {
      continue;
    }
    if (line.startsWith('event:')) {
      event = line.slice('event:'.length).trim();
      continue;
    }
    if (line.startsWith('data:')) {
      dataLines.push(line.slice('data:'.length).trimStart());
    }
  }

  if (dataLines.length === 0) {
    return null;
  }

  return {
    event,
    data: dataLines.join('\n'),
  };
}

async function parseHttpError(response: Response): Promise<string> {
  try {
    const body = await response.json();
    return parseErrorMessage(body);
  } catch {
    return `Request failed (${response.status})`;
  }
}

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

export function mapVisualStyleToPipelineTemplate(style: VisualStyleId): PipelineStyleTemplate {
  return style;
}

function buildReferencePrompt(styleTemplate: VisualStyleId, characterVisualPrompt: string): string {
  const basePrompt = characterVisualPrompt.trim().length > 0
    ? characterVisualPrompt.trim()
    : 'young protagonist, expressive eyes, clear silhouette, consistent wardrobe details';

  return [
    STYLE_DESCRIPTORS[styleTemplate],
    `Single character, clear full-body or half-body, neutral background, high readability. ${basePrompt}`,
    NEGATIVE_HINT,
  ].join('\n\n');
}

async function generateReferenceImage(
  styleTemplate: VisualStyleId,
  characterVisualPrompt: string,
  signal: AbortSignal,
): Promise<GeneratedReferenceImage> {
  const response = await fetch(`${getApiBaseUrl()}/api/image/generate`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      prompt: buildReferencePrompt(styleTemplate, characterVisualPrompt),
      reference_images: {},
    }),
    signal,
  });

  if (!response.ok) {
    throw new Error(await parseHttpError(response));
  }

  const payload = await response.json() as { image_base64: string; mime_type: string };
  return {
    styleTemplate,
    imageBase64: payload.image_base64,
    mimeType: payload.mime_type,
  };
}

export async function generateReferenceImages(
  characterVisualPrompt: string,
  signal: AbortSignal,
): Promise<GeneratedReferenceImage[]> {
  return Promise.all(
    STYLE_REFERENCE_ORDER.map((styleTemplate) =>
      generateReferenceImage(styleTemplate, characterVisualPrompt, signal)),
  );
}

export async function fetchPipelinePreview(
  request: StartPipelineRequest,
  signal: AbortSignal,
): Promise<PipelinePreviewModel> {
  const genre = request.genre?.trim() ?? '';
  const tone = request.tone?.trim() ?? '';

  const response = await fetch(`${getApiBaseUrl()}/api/prompt-preview`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      source_text: request.manuscript,
      ...(genre ? { genre } : {}),
      ...(tone ? { tone } : {}),
      output_language: request.outputLanguage ?? 'ko',
      style_template: request.styleTemplate,
      max_image_cuts: 9,
    }),
    signal,
  });

  if (!response.ok) {
    throw new Error(await parseHttpError(response));
  }

  const payload = await response.json() as CompatPromptPreviewResponse;
  return {
    cut_plan: payload.cut_plan,
    characters: payload.character_sheet,
    anchor_prompt: payload.anchor_prompt,
    cuts: payload.cuts.map((cut) => ({
      cut_number: cut.index,
      styled_prompt: cut.prompt,
      reference_inputs: cut.reference_inputs,
    })),
  };
}

export async function generateMediaFromPreview(
  sourceText: string,
  preview: PipelinePreviewModel,
  styleTemplate: PipelineStyleTemplate,
  referenceImages: Record<string, string>,
  promptOverrides: Record<number, string>,
  signal: AbortSignal,
): Promise<PipelineResultModel> {
  const response = await fetch(`${getApiBaseUrl()}/api/teaser`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      source_text: sourceText,
      output_language: 'ko',
      style_template: styleTemplate,
      reference_images: referenceImages,
      prompt_overrides: promptOverrides,
      max_image_cuts: 9,
    }),
    signal,
  });

  if (!response.ok) {
    throw new Error(await parseHttpError(response));
  }

  const payload = await response.json() as CompatTeaserResponse;
  const cutByNumber = new Map(preview.cut_plan.cuts.map((cut) => [cut.cut_number, cut]));
  const mappedCuts = payload.cuts
    .sort((a, b) => a.index - b.index)
    .map((cut) => {
      const base = cutByNumber.get(cut.index);
      const override = promptOverrides[cut.index];
      return {
        cut_number: cut.index,
        image_base64: cut.image_base64,
        mime_type: 'image/png',
        video_base64: '',
        video_mime_type: '',
        dialogue: base?.dialogue ?? [],
        narration: base?.narration ?? '',
        description: base?.description ?? (override || ''),
      };
    });
  const nextRefs = { ...referenceImages };
  if (payload.character_anchor_image_base64) {
    nextRefs.anchor = payload.character_anchor_image_base64;
  }

  return {
    characters: preview.characters,
    cuts: mappedCuts,
    validation_report: null,
    reference_images: nextRefs,
  };
}

export async function startPipelineGeneration(
  request: StartPipelineRequest,
  handlers: SseHandlers,
  signal: AbortSignal,
): Promise<PipelineResultModel> {
  const genre = request.genre?.trim() ?? '';
  const tone = request.tone?.trim() ?? '';

  const response = await fetch(`${getApiBaseUrl()}/api/pipeline/generate`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      manuscript: request.manuscript,
      ...(genre ? { genre } : {}),
      ...(tone ? { tone } : {}),
      output_language: request.outputLanguage ?? 'ko',
      output_mode: 'image',
      style_template: request.styleTemplate,
    }),
    signal,
  });

  if (!response.ok) {
    throw new Error(await parseHttpError(response));
  }

  if (!response.body) {
    throw new Error('Streaming response is not available in this browser.');
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder('utf-8');
  let buffer = '';
  let finalResult: PipelineResultModel | null = null;

  const processFrame = (frame: string): void => {
    const parsed = parseSseFrame(frame);
    if (!parsed) {
      return;
    }

    if (
      parsed.event !== 'run_created'
      && parsed.event !== 'progress'
      && parsed.event !== 'result'
    ) {
      return;
    }

    const jsonData = parseJsonPayload(parsed.data);

    if (parsed.event === 'run_created') {
      const runId = (jsonData as { run_id?: unknown }).run_id;
      if (typeof runId === 'string' && runId.length > 0) {
        handlers.onRunCreated(runId);
      }
      return;
    }

    if (parsed.event === 'progress') {
      const progress = jsonData as PipelineProgressEvent;
      handlers.onProgress(progress);
      if (progress.status === 'failed') {
        const detail = progress.detail ?? `Pipeline failed at step ${progress.step}`;
        throw new Error(detail);
      }
      return;
    }

    if (parsed.event === 'result') {
      finalResult = jsonData as PipelineResultModel;
    }
  };

  while (true) {
    const { value, done } = await reader.read();
    if (done) {
      break;
    }

    buffer += decoder.decode(value, { stream: true });
    buffer = buffer.replace(/\r\n/g, '\n').replace(/\r/g, '\n');

    const frames: string[] = [];
    let sepIndex = buffer.indexOf('\n\n');
    while (sepIndex !== -1) {
      frames.push(buffer.slice(0, sepIndex));
      buffer = buffer.slice(sepIndex + 2);
      sepIndex = buffer.indexOf('\n\n');
    }

    for (const frame of frames) {
      processFrame(frame);
    }
  }

  if (buffer.trim().length > 0) {
    buffer = buffer.replace(/\r\n/g, '\n').replace(/\r/g, '\n');
    processFrame(buffer);
  }

  if (finalResult) {
    return finalResult;
  }

  throw new Error('Pipeline finished without a result payload.');
}
