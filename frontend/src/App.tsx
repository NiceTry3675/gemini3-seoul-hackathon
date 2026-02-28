import { useEffect, useReducer } from 'react';
import MetaPrompt1Screen from './components/screens/MetaPrompt1Screen';
import MetaPrompt2Screen from './components/screens/MetaPrompt2Screen';
import MetaPrompt3Screen from './components/screens/MetaPrompt3Screen';
import ProcessingStateScreen from './components/screens/ProcessingStateScreen';
import StoryInputScreen from './components/screens/StoryInputScreen';
import VideoExportScreen from './components/screens/VideoExportScreen';
import { generateFrameOptions, buildInitialMetaPrompt, startMockRender } from './services/workflowService';
import { createInitialWorkflowState, workflowReducer } from './state/workflowReducer';
import type { WorkflowStep } from './types/workflow';

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

export default function App() {
  const [state, dispatch] = useReducer(workflowReducer, undefined, createInitialWorkflowState);

  useEffect(() => {
    if (state.step !== 'processing_state' || !state.processing.running || !state.selectedStyle) {
      return undefined;
    }

    let cancelled = false;

    void startMockRender({
      storyText: state.storyInput.text,
      metaPrompt: state.metaPrompt.draft,
      style: state.selectedStyle,
      frameSelections: state.frameSelections,
    })
      .then((videoExport) => {
        if (!cancelled) {
          dispatch({ type: 'PROCESSING_SUCCESS', payload: videoExport });
        }
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          dispatch({
            type: 'PROCESSING_ERROR',
            payload: error instanceof Error ? error.message : 'Unknown mock rendering error.',
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
    state.metaPrompt.draft,
    state.frameSelections,
  ]);

  const step = state.step;

  const goBack = () => dispatch({ type: 'BACK' });

  const goNext = () => dispatch({ type: 'NEXT' });

  const startProcessing = () => {
    dispatch({ type: 'CLEAR_PROCESSING_ERROR' });
    dispatch({ type: 'START_PROCESSING' });
  };

  const handleStoryNext = () => {
    if (!state.metaPrompt.draft.trim()) {
      dispatch({
        type: 'SET_META_DRAFT',
        payload: buildInitialMetaPrompt(state.storyInput.text),
      });
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
          />
        );

      case 'meta_prompt_1':
        return (
          <MetaPrompt1Screen
            draft={state.metaPrompt.draft}
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
            onNext={goNext}
          />
        );

      case 'meta_prompt_3':
        return (
          <MetaPrompt3Screen
            frameSelections={state.frameSelections}
            onSelectOption={(frameIndex, optionId) =>
              dispatch({ type: 'SELECT_FRAME_OPTION', payload: { frameIndex, optionId } })
            }
            onStartOver={() => dispatch({ type: 'RESET' })}
            onGenerateTeaser={startProcessing}
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
          <VideoExportScreen videoExport={state.videoExport} onBack={goBack} onDownload={handleDownload} />
        ) : (
          <ProcessingStateScreen
            running={false}
            errorMessage="Missing export payload. Please retry generation from Meta Prompt 3."
            onRetry={goBack}
            onBack={goBack}
          />
        );

      default:
        return null;
    }
  };

  return <>{renderStep(step)}</>;
}
