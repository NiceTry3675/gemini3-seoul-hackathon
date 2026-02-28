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
  cinematic_art: ['Neon Noir Style', 'Cyberpunk Style', 'Cinematic Style', 'Experimental Style'],
  anime_2d: ['Sakura Pulse', 'Urban Neon', 'Skyline Slice', 'Action Frame'],
  oil_painting: ['Gallery Warmth', 'Renaissance Mood', 'Brushwork Scene', 'Canvas Grain'],
  digital_sketch: ['Pencil Burst', 'Charcoal Shade', 'Ink Motion', 'Storyboard Draft'],
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

export function buildInitialMetaPrompt(storyText: string): string {
  const snippet = normalizeStorySnippet(storyText);

  return [
    'Cinematic teaser composition, 8k detail, strong emotional contrast.',
    'Establish environment scale in the opening frame with dramatic lighting and atmospheric depth.',
    'Maintain consistent character silhouette, wardrobe cues, and facial readability across all frames.',
    'Use camera progression: wide establishing shot -> medium action beat -> close-up emotional peak -> iconic final frame.',
    'Color script should evolve from cool tension tones into a brighter resolution accent.',
    `Story anchor: ${snippet}`,
  ].join(' ');
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
