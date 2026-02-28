import { useEffect, useReducer, useState, useCallback } from 'react';
import MetaPrompt1Screen from './components/screens/MetaPrompt1Screen';
import MetaPrompt2Screen from './components/screens/MetaPrompt2Screen';
import MetaPrompt3Screen from './components/screens/MetaPrompt3Screen';
import ProcessingStateScreen from './components/screens/ProcessingStateScreen';
import StoryInputScreen from './components/screens/StoryInputScreen';
import VideoExportScreen from './components/screens/VideoExportScreen';
import { generateFrameOptions, buildInitialMetaPrompt, callTeaserApi, teaserResultToExport } from './services/workflowService';
import { createInitialWorkflowState, workflowReducer } from './state/workflowReducer';
import { STYLE_TONE_BY_ID } from './data/workflowData';
import type { WorkflowStep } from './types/workflow';
import { WORKFLOW_STEPS } from './types/workflow';

function downloadWorkflowSnapshot(snapshot: unknown): void {
  const blob = new Blob([JSON.stringify(snapshot, null, 2)], {
    type: 'application/json;charset=utf-8',
  });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = 'teaserstudio-mock-export.json';
  anchor.click();
  URL.revokeObjectURL(url);
}

function getStepFromHash(): WorkflowStep | null {
  const hash = window.location.hash.replace('#', '');
  if (hash && WORKFLOW_STEPS.includes(hash as WorkflowStep)) {
    return hash as WorkflowStep;
  }
  return null;
}

export default function App() {
  const [state, dispatch] = useReducer(workflowReducer, undefined, () => {
    const initial = createInitialWorkflowState();
    const hashStep = getStepFromHash();
    if (hashStep) {
      return { ...initial, step: hashStep };
    }
    return initial;
  });
  const [isPreparingMetaPrompt, setIsPreparingMetaPrompt] = useState(false);

  // Sync step → URL hash
  useEffect(() => {
    const newHash = `#${state.step}`;
    if (window.location.hash !== newHash) {
      window.history.replaceState(null, '', newHash);
    }
  }, [state.step]);

  // Listen for hash changes (browser back/forward)
  useEffect(() => {
    const onHashChange = () => {
      const hashStep = getStepFromHash();
      if (hashStep && hashStep !== state.step) {
        dispatch({ type: 'JUMP_TO_STEP', payload: hashStep });
      }
    };
    window.addEventListener('hashchange', onHashChange);
    return () => window.removeEventListener('hashchange', onHashChange);
  }, [state.step]);

  // Teaser image generation
  useEffect(() => {
    if (state.step !== 'meta_prompt_3' || !state.processing.running || !state.selectedStyle) {
      return undefined;
    }

    let cancelled = false;
    const styleTone = STYLE_TONE_BY_ID[state.selectedStyle];

    void callTeaserApi(state.storyInput.text, state.selectedStyle)
      .then((result) => {
        if (!cancelled) {
          const videoExport = teaserResultToExport(result, styleTone);
          dispatch({ type: 'PROCESSING_SUCCESS', payload: videoExport });
        }
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          dispatch({
            type: 'PROCESSING_ERROR',
            payload: error instanceof Error ? error.message : 'Unknown API error.',
          });
        }
      });

    return () => {
      cancelled = true;
    };
  }, [
    state.step,
    state.processing.running,
    state.selectedStyle,
    state.storyInput.text,
  ]);

  const goBack = () => dispatch({ type: 'BACK' });
  const goNext = () => dispatch({ type: 'NEXT' });

  const startProcessing = () => {
    dispatch({ type: 'CLEAR_PROCESSING_ERROR' });
    dispatch({ type: 'START_PROCESSING' });
  };

  const handleStoryNext = async () => {
    setIsPreparingMetaPrompt(true);

    if (!state.metaPrompt.draft.trim()) {
      try {
        const metaPrompt = await buildInitialMetaPrompt(state.storyInput.text);
        dispatch({
          type: 'SET_META_DRAFT',
          payload: metaPrompt,
        });
      } finally {
        setIsPreparingMetaPrompt(false);
      }
    } else {
      setIsPreparingMetaPrompt(false);
    }

    dispatch({ type: 'NEXT' });
  };

  const handleStyleSelection = (style: NonNullable<typeof state.selectedStyle>) => {
    const frameOptions = state.frameSelections.map((frame) =>
      generateFrameOptions(frame.frameIndex, style),
    );
    dispatch({
      type: 'APPLY_STYLE',
      payload: {
        style,
        frameOptions,
      },
    });
  };

  const handleDownload = () => {
    if (!state.videoExport) {
      return;
    }

    downloadWorkflowSnapshot({
      exportedAt: new Date().toISOString(),
      workflowStep: state.step,
      storyInput: state.storyInput,
      metaPrompt: state.metaPrompt,
      selectedStyle: state.selectedStyle,
      frameSelections: state.frameSelections,
      videoExport: state.videoExport,
    });
  };

  const navigateToStep = useCallback((step: WorkflowStep) => {
    dispatch({ type: 'JUMP_TO_STEP', payload: step });
  }, []);

  const renderStep = (currentStep: WorkflowStep) => {
    switch (currentStep) {
      case 'story_input':
        return (
          <StoryInputScreen
            text={state.storyInput.text}
            inputMode={state.storyInput.inputMode}
            charCount={state.storyInput.charCount}
            onTextChange={(value) => dispatch({ type: 'SET_STORY_TEXT', payload: value })}
            onInputModeChange={(mode) => dispatch({ type: 'SET_STORY_INPUT_MODE', payload: mode })}
            onNext={handleStoryNext}
            isPreparingMetaPrompt={isPreparingMetaPrompt}
          />
        );

      case 'meta_prompt_1':
        return (
          <MetaPrompt1Screen
            draft={state.metaPrompt.draft}
            storyText={state.storyInput.text}
            selectedStyle={state.selectedStyle ?? undefined}
            onDraftChange={(value) => dispatch({ type: 'SET_META_DRAFT', payload: value })}
            onBack={goBack}
            onNext={goNext}
          />
        );

      case 'meta_prompt_2':
        return (
          <MetaPrompt2Screen
            selectedStyle={state.selectedStyle}
            onSelectStyle={handleStyleSelection}
            onBack={goBack}
            onNext={startProcessing}
          />
        );

      case 'meta_prompt_3':
        return (
          <MetaPrompt3Screen
            storyText={state.storyInput.text}
            selectedStyle={state.selectedStyle}
            processing={state.processing}
            videoExport={state.videoExport}
            onStartOver={() => dispatch({ type: 'RESET' })}
            onGenerateTeaser={startProcessing}
            onNext={() => dispatch({ type: 'GO_VIDEO_EXPORT' })}
            onBack={goBack}
          />
        );

      case 'processing_state':
        return (
          <ProcessingStateScreen
            running={state.processing.running}
            errorMessage={state.processing.errorMessage}
            onRetry={startProcessing}
            onBack={goBack}
          />
        );

      case 'video_export':
        return state.videoExport ? (
          <VideoExportScreen
            videoExport={state.videoExport}
            storyText={state.storyInput.text}
            onBack={goBack}
            onDownload={handleDownload}
            onReset={() => dispatch({ type: 'RESET' })}
          />
        ) : (
          <div className="flex min-h-screen flex-col items-center justify-center gap-6 text-slate-100">
            <span className="material-symbols-outlined text-6xl text-slate-500">videocam_off</span>
            <h2 className="text-3xl font-bold">No teaser generated yet</h2>
            <p className="text-slate-400">Generate a teaser first, or go back to start.</p>
            <div className="flex gap-4">
              <button
                type="button"
                onClick={() => navigateToStep('story_input')}
                className="rounded-lg bg-[#2b6cee] px-6 py-3 font-bold text-white hover:bg-blue-600"
              >
                Start from Beginning
              </button>
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  return <>{renderStep(state.step)}</>;
}
