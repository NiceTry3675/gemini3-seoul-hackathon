import { useEffect, useReducer } from 'react';
import ProcessingStateScreen from './components/screens/ProcessingStateScreen';
import StoryInputScreen from './components/screens/StoryInputScreen';
import VideoExportScreen from './components/screens/VideoExportScreen';
import { startPipelineGeneration } from './services/workflowService';
import {
  canStartPipeline,
  createInitialWorkflowState,
  workflowReducer,
} from './state/workflowReducer';

function downloadSnapshot(snapshot: unknown): void {
  const blob = new Blob([JSON.stringify(snapshot, null, 2)], {
    type: 'application/json;charset=utf-8',
  });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = 'teaserstudio-export.json';
  anchor.click();
  URL.revokeObjectURL(url);
}

function normalizeError(error: unknown): string {
  if (error instanceof DOMException && error.name === 'AbortError') {
    return 'Generation cancelled.';
  }
  if (error instanceof Error && error.message.trim().length > 0) {
    return error.message;
  }
  return 'Unknown pipeline error.';
}

export default function App() {
  const [state, dispatch] = useReducer(workflowReducer, undefined, createInitialWorkflowState);

  useEffect(() => {
    if (state.step !== 'processing_state' || !state.processing.running) {
      return undefined;
    }

    const abortController = new AbortController();

    void startPipelineGeneration(
      state.storyInput,
      {
        onRunCreated: (runId) => dispatch({ type: 'SET_RUN_ID', payload: runId }),
        onProgress: (progress) => dispatch({ type: 'UPDATE_PROGRESS', payload: progress }),
      },
      abortController.signal,
    )
      .then((result) => {
        dispatch({ type: 'PROCESSING_SUCCESS', payload: result });
      })
      .catch((error: unknown) => {
        const message = normalizeError(error);
        if (message !== 'Generation cancelled.') {
          dispatch({ type: 'PROCESSING_ERROR', payload: message });
        }
      });

    return () => {
      abortController.abort();
    };
  }, [state.step, state.processing.running, state.storyInput]);

  if (state.step === 'story_input') {
    return (
      <StoryInputScreen
        manuscript={state.storyInput.manuscript}
        genre={state.storyInput.genre}
        tone={state.storyInput.tone}
        outputLanguage={state.storyInput.outputLanguage}
        styleTemplate={state.storyInput.styleTemplate}
        canSubmit={canStartPipeline(state)}
        onManuscriptChange={(value) => dispatch({ type: 'SET_MANUSCRIPT', payload: value })}
        onGenreChange={(value) => dispatch({ type: 'SET_GENRE', payload: value })}
        onToneChange={(value) => dispatch({ type: 'SET_TONE', payload: value })}
        onOutputLanguageChange={(value) => dispatch({ type: 'SET_OUTPUT_LANGUAGE', payload: value })}
        onStyleTemplateChange={(value) => dispatch({ type: 'SET_STYLE_TEMPLATE', payload: value })}
        onSubmit={() => {
          dispatch({ type: 'CLEAR_PROCESSING_ERROR' });
          dispatch({ type: 'START_PROCESSING' });
        }}
      />
    );
  }

  if (state.step === 'processing_state') {
    return (
      <ProcessingStateScreen
        running={state.processing.running}
        runId={state.processing.runId}
        progressByStep={state.processing.progressByStep}
        errorMessage={state.processing.errorMessage}
        onRetry={() => {
          dispatch({ type: 'CLEAR_PROCESSING_ERROR' });
          dispatch({ type: 'START_PROCESSING' });
        }}
        onBack={() => dispatch({ type: 'BACK_TO_INPUT' })}
      />
    );
  }

  if (state.result) {
    return (
      <VideoExportScreen
        result={state.result}
        onBack={() => dispatch({ type: 'BACK_TO_INPUT' })}
        onDownload={() => {
          downloadSnapshot({
            exportedAt: new Date().toISOString(),
            runId: state.processing.runId,
            request: state.storyInput,
            result: state.result,
          });
        }}
      />
    );
  }

  return (
    <ProcessingStateScreen
      running={false}
      runId={state.processing.runId}
      progressByStep={state.processing.progressByStep}
      errorMessage="Missing result payload. Please retry generation."
      onRetry={() => dispatch({ type: 'START_PROCESSING' })}
      onBack={() => dispatch({ type: 'BACK_TO_INPUT' })}
    />
  );
}
