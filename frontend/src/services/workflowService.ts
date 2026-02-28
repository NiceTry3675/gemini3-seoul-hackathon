import type {
  PipelineProgressEvent,
  PipelineResultModel,
  PipelineStoryInputModel,
} from '../types/workflow';

const DEFAULT_API_BASE_URL = 'http://127.0.0.1:8000';

function getApiBaseUrl(): string {
  const configured = import.meta.env.VITE_API_BASE_URL;
  if (typeof configured !== 'string') {
    return DEFAULT_API_BASE_URL;
  }

  const trimmed = configured.trim();
  return trimmed.length > 0 ? trimmed.replace(/\/+$/, '') : DEFAULT_API_BASE_URL;
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

async function parseHttpError(response: Response): Promise<string> {
  try {
    const body = await response.json();
    return parseErrorMessage(body);
  } catch {
    return `Request failed (${response.status})`;
  }
}

interface SseHandlers {
  onRunCreated: (runId: string) => void;
  onProgress: (event: PipelineProgressEvent) => void;
}

function parseSseFrame(frame: string): { event: string; data: string } | null {
  const lines = frame.split('\n');
  let event = 'message';
  const dataLines: string[] = [];

  for (const line of lines) {
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

export async function startPipelineGeneration(
  storyInput: PipelineStoryInputModel,
  handlers: SseHandlers,
  signal: AbortSignal,
): Promise<PipelineResultModel> {
  const response = await fetch(`${getApiBaseUrl()}/api/pipeline/generate`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      manuscript: storyInput.manuscript,
      genre: storyInput.genre,
      tone: storyInput.tone,
      output_language: storyInput.outputLanguage,
      output_mode: 'image',
      style_template: storyInput.styleTemplate,
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

    let jsonData: unknown;
    try {
      jsonData = JSON.parse(parsed.data);
    } catch {
      throw new Error('Received malformed SSE event payload.');
    }

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
    const frames = buffer.split('\n\n');
    buffer = frames.pop() ?? '';

    for (const frame of frames) {
      processFrame(frame);
    }
  }

  if (buffer.trim().length > 0) {
    processFrame(buffer);
  }

  if (finalResult) {
    return finalResult;
  }

  throw new Error('Pipeline finished without a result payload.');
}
