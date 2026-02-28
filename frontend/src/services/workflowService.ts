import {
  FRAME_IMAGE_POOL,
  FRAME_SEQUENCE,
  FRAME_TAGS,
  STYLE_OPTIONS,
  STYLE_TONE_BY_ID,
} from '../data/workflowData';
import type {
  FrameOption,
  FrameSelection,
  MockRenderPayload,
  SourceFrame,
  VideoExportModel,
  VisualStyleId,
} from '../types/workflow';

const STYLE_SUBTITLES: Record<VisualStyleId, string[]> = {
  cinematic_realism: ['Neon Noir Style', 'Cyberpunk Style', 'Cinematic Style', 'Experimental Style'],
  webtoon_cel: ['Sakura Pulse', 'Urban Neon', 'Skyline Slice', 'Action Frame'],
  watercolor_dream: ['Gallery Warmth', 'Renaissance Mood', 'Brushwork Scene', 'Canvas Grain'],
  digital_masterpaint: ['Pencil Burst', 'Charcoal Shade', 'Ink Motion', 'Storyboard Draft'],
};

function hashString(input: string): number {
  let hash = 2166136261;
  for (let i = 0; i < input.length; i += 1) {
    hash ^= input.charCodeAt(i);
    hash = Math.imul(hash, 16777619);
  }
  return hash >>> 0;
}

function normalizeStorySnippet(text: string): string {
  const trimmed = text.trim().replace(/\s+/g, ' ');
  if (!trimmed) {
    return 'A high-impact teaser concept focused on tension, motion, and emotional payoff.';
  }
  const words = trimmed.split(' ').slice(0, 36);
  const body = words.join(' ');
  return words.length < trimmed.split(' ').length ? `${body}...` : body;
}

const PREVIEW_REQUEST_TIMEOUT_MS = 180_000;
const PREVIEW_PATHS = ['/api/pipeline/preview', '/api/prompt-preview'] as const;
const DEFAULT_API_PORT = 8000;

const API_BASE_LIST = (() => {
    const hostname = typeof window === 'undefined'
    ? '127.0.0.1'
    : (window.location.hostname || '127.0.0.1');

  return [...new Set([
    '',
    `http://localhost:${DEFAULT_API_PORT}`,
    `http://${hostname}:${DEFAULT_API_PORT}`,
    'http://127.0.0.1:8000',
  ].filter((value): value is string => Boolean(value)))].map((value) => value.replace(/\/$/, ''));
})();

async function fetchFromApiBase(path: string, options: RequestInit = {}): Promise<Response> {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  let lastError: unknown = null;

  for (const base of API_BASE_LIST) {
    const url = base ? `${base}${normalizedPath}` : normalizedPath;
    const controller = new AbortController();
    const timer = window.setTimeout(() => controller.abort(), PREVIEW_REQUEST_TIMEOUT_MS);
    const signal = options.signal
      ? (typeof AbortSignal.any === 'function'
        ? AbortSignal.any([options.signal, controller.signal])
        : controller.signal)
      : controller.signal;
    try {
      return await fetch(url, { ...options, signal });
    } catch (error) {
      lastError = error;
    } finally {
      clearTimeout(timer);
    }
  }

  if (lastError instanceof Error) {
    throw lastError;
  }
  throw new Error('Failed to connect to API server');
}

function asConnectError(error: unknown): Error {
  if (error instanceof DOMException && error.name === 'AbortError') {
    return new Error(`Request timed out after ${Math.floor(PREVIEW_REQUEST_TIMEOUT_MS / 1000)} seconds.`);
  }
  if (error instanceof TypeError) {
    return new Error('Failed to connect to API server. Please check backend is running and accessible.');
  }
  if (error instanceof Error) {
    return error;
  }
  return new Error(String(error ?? 'Unknown API error'));
}

export async function buildInitialMetaPrompt(storyText: string): Promise<string> {
  const snippet = normalizeStorySnippet(storyText);

  const fallback = [
    'Cinematic teaser composition, 8k detail, strong emotional contrast.',
    'Establish environment scale in the opening frame with dramatic lighting and atmospheric depth.',
    'Maintain consistent character silhouette, wardrobe cues, and facial readability across all frames.',
    'Use camera progression: wide establishing shot -> medium action beat -> close-up emotional peak -> iconic final frame.',
    'Color script should evolve from cool tension tones into a brighter resolution accent.',
    `Story anchor: ${snippet}`,
  ].join(' ');

  try {
    const response = await fetchFromApiBase('/api/text/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        prompt: [
          'You are a cinematic teaser prompt engineer.',
          'Given the following story excerpt, generate a detailed meta prompt that will guide AI image generation for a visual teaser.',
          'The meta prompt should include: camera angles, lighting, color palette, mood, character framing, and visual progression across frames.',
          'Write it as a single cohesive paragraph in English. Do NOT include any explanation, just the meta prompt text.',
          '',
          `Story excerpt:\n${snippet}`,
        ].join('\n'),
        temperature: 0.8,
        max_output_tokens: 1024,
      }),
    });

    if (!response.ok) {
      console.warn('Meta prompt API failed, using fallback');
      return fallback;
    }

    const data = await response.json();
    const text = data.text?.trim();
    return text || fallback;
  } catch (error) {
    console.warn('Meta prompt API error, using fallback:', asConnectError(error).message);
    return fallback;
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

function buildSourceFrames(style: VisualStyleId, frameSelections: FrameSelection[]): SourceFrame[] {
  return frameSelections.map((selection) => {
    const selected = selection.options.find(
      (option) => option.id === selection.selectedOptionId,
    );
    const fallback = generateFrameOptions(selection.frameIndex, style)[0];

    return {
      index: selection.frameIndex,
      imageUrl: selected?.imageUrl ?? fallback.imageUrl,
      selectedOptionLabel: selected?.label ?? fallback.label,
    };
  });
}

export async function startMockRender(payload: MockRenderPayload): Promise<VideoExportModel> {
  const fingerprint = `${payload.storyText}|${payload.metaPrompt}|${payload.style}|${payload.frameSelections
    .map((selection) => selection.selectedOptionId ?? 'none')
    .join('|')}`;
  const hash = hashString(fingerprint);
  const delayMs = 3000 + (hash % 2001);
  const shouldFail =
    payload.storyText.toLowerCase().includes('[force-error]') ||
    payload.metaPrompt.toLowerCase().includes('[force-error]');

  return new Promise<VideoExportModel>((resolve, reject) => {
    window.setTimeout(() => {
      if (shouldFail) {
        reject(
          new Error(
            'Mock render failed. Remove [force-error] from input to simulate a successful export.',
          ),
        );
        return;
      }

      const style = STYLE_OPTIONS.find((item) => item.id === payload.style);
      const sourceFrames = buildSourceFrames(payload.style, payload.frameSelections);
      const previewImageUrl = sourceFrames[0]?.imageUrl ?? FRAME_IMAGE_POOL[payload.style][0];

      resolve({
        title: 'Creating your Teaser',
        subtitle: 'Your short-form video is ready for preview.',
        previewImageUrl,
        sourceFrames,
        settings: {
          musicStyle: STYLE_TONE_BY_ID[payload.style],
          transition: 'Fade',
          duration: '15 Seconds',
          format: '9:16 Vertical',
        },
        renderSeconds: Number((delayMs / 1000).toFixed(1)),
      });

      if (!style) {
        console.warn('Unknown style id in mock render payload');
      }
    }, delayMs);
  });
}

export async function callTeaserApi(
  storyText: string,
  backendStyleId: string,
  outputLanguage: string = 'ko',
): Promise<import('../types/workflow').TeaserApiResult> {
  const response = await fetchFromApiBase('/api/teaser', {
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

  return response.json();
}

export interface PromptPreviewCut {
  index: number;
  prompt: string;
  reference_inputs: string[];
}

export interface PromptPreviewResult {
  plan: import('../types/workflow').TeaserPlan;
  anchor_prompt: string;
  cuts: PromptPreviewCut[];
}

type LegacyPromptPreviewPayload = {
  source_text: string;
  style_template: string;
  output_language: string;
};

type PipelinePromptPreviewPayload = {
  manuscript: string;
  style_template: string;
  output_language: string;
  genre: string;
  tone: string;
};

type PipelinePreviewResponse = {
  cut_plan: {
    cuts: Array<{
      cut_number: number;
      styled_prompt: string;
      reference_inputs: string[];
    }>;
  };
  anchor_prompt: string;
  characters: unknown;
};

async function fetchPromptPreview(
  path: string,
  body: Record<string, unknown>,
): Promise<PromptPreviewResult> {
  const response = await fetchFromApiBase(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Preview API error (${response.status}): ${errorText}`);
  }

  const data = await response.json();

  if (data?.cuts && Array.isArray(data.cuts) && 'cut_number' in (data.cuts[0] || {})) {
    return {
      plan: data.plan,
      anchor_prompt: data.anchor_prompt || '',
      cuts: (data.cuts as Array<{ cut_number: number; styled_prompt: string; prompt?: string; reference_inputs?: string[] }>).map(
        (cut) => ({
          index: cut.cut_number,
          prompt: cut.prompt ?? cut.styled_prompt ?? '',
          reference_inputs: cut.reference_inputs ?? [],
        }),
      ),
    };
  }

  if (data?.cut_plan && Array.isArray(data.cut_plan?.cuts)) {
    return {
      plan: data.cut_plan,
      anchor_prompt: data.anchor_prompt || '',
      cuts: data.cut_plan.cuts.map((cut: { cut_number: number; styled_prompt: string; reference_inputs?: string[] }) => ({
        index: cut.cut_number,
        prompt: cut.styled_prompt,
        reference_inputs: cut.reference_inputs ?? [],
      })),
    };
  }

  return data as PromptPreviewResult;
}

export async function callPromptPreview(
  storyText: string,
  backendStyleId: string,
  outputLanguage: string = 'ko',
): Promise<PromptPreviewResult> {
  try {
    const legacyPayload: LegacyPromptPreviewPayload = {
      source_text: storyText,
      style_template: backendStyleId,
      output_language: outputLanguage,
    };
    const pipelinePayload: PipelinePromptPreviewPayload = {
      manuscript: storyText,
      style_template: backendStyleId,
      output_language: outputLanguage,
      genre: '',
      tone: '',
    };

    let lastError: Error | null = null;
    for (const path of PREVIEW_PATHS) {
      try {
        const payload = path.includes('/pipeline/') ? pipelinePayload : legacyPayload;
        return await fetchPromptPreview(path, payload);
      } catch (error) {
        if (error instanceof Error) {
          lastError = error;
        }
      }
    }

    if (lastError) {
      throw lastError;
    }
    throw new Error('Failed to fetch preview');
  } catch (error) {
    throw asConnectError(error);
  }
}

export interface StylePreviewResult {
  style_template: string;
  images: string[];  // base64 PNG strings
}

export async function callStylePreview(
  styleTemplate: string,
  storyText?: string,
): Promise<StylePreviewResult> {
  const response = await fetchFromApiBase('/api/style-preview', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      style_template: styleTemplate,
      story_text: storyText || undefined,
    }),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Style preview API error (${response.status}): ${errorText}`);
  }

  return response.json();
}

export interface VideoGenCallbacks {
  onProgress: (progress: number, message: string) => void;
  onComplete: (videoBase64: string, duration: number) => void;
  onError: (error: string) => void;
}

export async function startVideoGeneration(
  cutsBase64: string[],
  callbacks: VideoGenCallbacks,
  abortSignal?: AbortSignal,
  storyPrompt?: string,
): Promise<void> {
  const response = await fetchFromApiBase('/api/teaser/video', {
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

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6));
            if (data.type === 'progress') {
              const pct = Math.round((data.step / data.total_steps) * 100);
              callbacks.onProgress(pct, data.message);
            } else if (data.type === 'result') {
              callbacks.onComplete(data.video_base64, data.duration_seconds);
            } else if (data.type === 'error') {
              callbacks.onError(data.message);
            }
          } catch {
            // skip malformed lines
          }
        }
      }
    }
  } else {
    const result = await response.json();
    if (result.video_base64) {
      callbacks.onComplete(result.video_base64, result.duration_seconds);
    } else {
      callbacks.onError('Unexpected response format');
    }
  }
}

export function teaserResultToExport(
  result: import('../types/workflow').TeaserApiResult,
  styleTone: string,
): import('../types/workflow').VideoExportModel {
  const cuts = result.cuts.sort((a, b) => a.index - b.index);
  const previewImageUrl = cuts.length > 0
    ? `data:image/png;base64,${cuts[0].image_base64}`
    : `data:image/png;base64,${result.character_anchor_image_base64}`;

  return {
    title: result.plan.title || 'Your Teaser',
    subtitle: 'AI-generated 9-cut teaser is ready for preview.',
    previewImageUrl,
    sourceFrames: cuts.map((cut) => ({
      index: cut.index,
      imageUrl: `data:image/png;base64,${cut.image_base64}`,
      selectedOptionLabel: `Cut ${cut.index}`,
    })),
    settings: {
      musicStyle: styleTone,
      transition: 'Fade',
      duration: '15 Seconds',
      format: '1:1 Square',
    },
    renderSeconds: 0,
  };
}
