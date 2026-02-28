import { useEffect, useReducer, useState } from 'react';
import MetaPrompt1Screen from './components/screens/MetaPrompt1Screen';
import MetaPrompt2Screen from './components/screens/MetaPrompt2Screen';
import MetaPrompt3Screen from './components/screens/MetaPrompt3Screen';
import ProcessingStateScreen from './components/screens/ProcessingStateScreen';
import StoryInputScreen from './components/screens/StoryInputScreen';
import VideoExportScreen from './components/screens/VideoExportScreen';
import {
  fetchPipelinePreview,
  generateMediaFromPreview,
  generateReferenceImages,
  mapVisualStyleToPipelineTemplate,
  translateResultCuts,
} from './services/workflowService';
import { createInitialWorkflowState, workflowReducer } from './state/workflowReducer';
import type {
  PipelineOutputLanguage,
  PipelinePreviewModel,
  PipelineResultModel,
  VisualStyleId,
  WorkflowStep,
} from './types/workflow';

function downloadWorkflowSnapshot(snapshot: unknown): void {
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

function defaultTranslationTarget(source: PipelineOutputLanguage): PipelineOutputLanguage {
  return source === 'ko' ? 'en' : 'ko';
}

export default function App() {
  const [state, dispatch] = useReducer(workflowReducer, undefined, createInitialWorkflowState);
  const [previewData, setPreviewData] = useState<PipelinePreviewModel | null>(null);
  const [editableCutPrompts, setEditableCutPrompts] = useState<Record<number, string>>({});
  const [metaPreviewLoading, setMetaPreviewLoading] = useState(false);
  const [metaPreviewError, setMetaPreviewError] = useState<string | null>(null);
  const [referenceLoading, setReferenceLoading] = useState(false);
  const [referenceError, setReferenceError] = useState<string | null>(null);
  const [resultTranslationLanguage, setResultTranslationLanguage] = useState<PipelineOutputLanguage>('en');
  const [resultTranslationLoading, setResultTranslationLoading] = useState(false);
  const [resultTranslationError, setResultTranslationError] = useState<string | null>(null);
  const [baseResultForTranslation, setBaseResultForTranslation] = useState<PipelineResultModel | null>(null);
  const [referenceImages, setReferenceImages] = useState<
    Partial<Record<VisualStyleId, { imageBase64: string; mimeType: string }>>
  >({});

  useEffect(() => {
    if (state.step !== 'meta_prompt_1') {
      return undefined;
    }
    if (state.storyInput.text.trim().length === 0) {
      return undefined;
    }
    if (state.metaPrompt.draft.trim().length > 0) {
      return undefined;
    }

    const abortController = new AbortController();
    const styleTemplate = state.selectedStyle
      ? mapVisualStyleToPipelineTemplate(state.selectedStyle)
      : 'webtoon_cel';

    setMetaPreviewLoading(true);
    setMetaPreviewError(null);
    setReferenceImages({});
    setReferenceError(null);

    void fetchPipelinePreview(
      {
        manuscript: state.storyInput.text,
        styleTemplate,
        outputLanguage: state.storyInput.outputLanguage,
      },
      abortController.signal,
    )
      .then((preview) => {
        setPreviewData(preview);
        const formatted = JSON.stringify(preview, null, 2);
        dispatch({ type: 'SET_META_DRAFT', payload: formatted });
        dispatch({ type: 'PUSH_META_HISTORY', payload: formatted });
      })
      .catch((error: unknown) => {
        const message = normalizeError(error);
        if (message !== 'Generation cancelled.') {
          setPreviewData(null);
          setReferenceImages({});
          setMetaPreviewError(message);
        }
      })
      .finally(() => {
        setMetaPreviewLoading(false);
      });

    return () => {
      abortController.abort();
    };
  }, [
    state.step,
    state.storyInput.text,
    state.storyInput.outputLanguage,
    state.metaPrompt.draft,
    state.selectedStyle,
  ]);

  useEffect(() => {
    if (state.step !== 'meta_prompt_2') {
      return undefined;
    }
    if (referenceError) {
      return undefined;
    }
    if (!previewData?.characters.characters[0]?.visual_prompt) {
      return undefined;
    }
    if (Object.keys(referenceImages).length === 4) {
      return undefined;
    }

    const abortController = new AbortController();
    const visualPrompt = previewData.characters.characters[0].visual_prompt;
    setReferenceLoading(true);
    setReferenceError(null);

    void generateReferenceImages(visualPrompt, abortController.signal)
      .then((generated) => {
        const byStyle = generated.reduce<Partial<Record<VisualStyleId, { imageBase64: string; mimeType: string }>>>(
          (acc, item) => {
            acc[item.styleTemplate] = {
              imageBase64: item.imageBase64,
              mimeType: item.mimeType,
            };
            return acc;
          },
          {},
        );
        setReferenceImages(byStyle);
      })
      .catch((error: unknown) => {
        const message = normalizeError(error);
        if (message !== 'Generation cancelled.') {
          setReferenceError(message);
        }
      })
      .finally(() => {
        setReferenceLoading(false);
      });

    return () => {
      abortController.abort();
    };
  }, [state.step, previewData, referenceImages, referenceError]);

  useEffect(() => {
    if (!previewData) {
      setEditableCutPrompts({});
      return;
    }
    const next: Record<number, string> = {};
    for (const cut of previewData.cut_plan.cuts) {
      next[cut.cut_number] = cut.image_prompt;
    }
    setEditableCutPrompts(next);
  }, [previewData]);

  useEffect(() => {
    if (state.step !== 'processing_state' || !state.processing.running || !state.selectedStyle) {
      return undefined;
    }
    if (!previewData) {
      dispatch({ type: 'PROCESSING_ERROR', payload: 'Preview data is missing. Please regenerate from Meta step.' });
      return undefined;
    }
    const selectedReference = referenceImages[state.selectedStyle];
    if (!selectedReference) {
      dispatch({ type: 'PROCESSING_ERROR', payload: 'Select a generated reference image first.' });
      return undefined;
    }

    const abortController = new AbortController();
    const runId = `export-${Date.now()}`;
    dispatch({ type: 'SET_RUN_ID', payload: runId });
    dispatch({
      type: 'UPDATE_PROGRESS',
      payload: { step: 1, step_name: 'scene_parse', status: 'completed', detail: 'Preview scene parse completed' },
    });
    dispatch({
      type: 'UPDATE_PROGRESS',
      payload: { step: 2, step_name: 'character_gen', status: 'completed', detail: 'Preview character generation completed' },
    });
    dispatch({
      type: 'UPDATE_PROGRESS',
      payload: { step: 3, step_name: 'cut_plan', status: 'completed', detail: 'Preview cut plan ready' },
    });
    dispatch({
      type: 'UPDATE_PROGRESS',
      payload: { step: 4, step_name: 'validate', status: 'completed', detail: 'Validation skipped in export mode' },
    });
    dispatch({
      type: 'UPDATE_PROGRESS',
      payload: { step: 5, step_name: 'media_gen', status: 'running', detail: 'Generating images with selected references' },
    });

    const primaryCharacterName = previewData.characters.characters[0]?.name || 'main_character';
    const mergedReferences: Record<string, string> = {
      anchor: selectedReference.imageBase64,
      selected_reference: selectedReference.imageBase64,
      [primaryCharacterName]: selectedReference.imageBase64,
    };

    const promptOverrides: Record<number, string> = {};
    for (const cut of previewData.cut_plan.cuts) {
      const edited = editableCutPrompts[cut.cut_number];
      if (typeof edited === 'string' && edited.trim().length > 0 && edited.trim() !== cut.image_prompt) {
        promptOverrides[cut.cut_number] = edited.trim();
      }
    }

    void generateMediaFromPreview(
      state.storyInput.text,
      previewData,
      mapVisualStyleToPipelineTemplate(state.selectedStyle),
      state.storyInput.outputLanguage,
      mergedReferences,
      promptOverrides,
      abortController.signal,
    )
      .then((result) => {
        setBaseResultForTranslation(result);
        setResultTranslationLanguage(defaultTranslationTarget(state.storyInput.outputLanguage));
        setResultTranslationError(null);
        dispatch({
          type: 'UPDATE_PROGRESS',
          payload: { step: 5, step_name: 'media_gen', status: 'completed', detail: `${result.cuts.length} images generated` },
        });
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
  }, [
    state.step,
    state.processing.running,
    state.selectedStyle,
    state.storyInput.text,
    state.storyInput.outputLanguage,
    previewData,
    referenceImages,
    editableCutPrompts,
  ]);

  const step = state.step;

  const goBack = () => dispatch({ type: 'BACK' });

  const goNext = () => dispatch({ type: 'NEXT' });

  const startProcessing = () => {
    dispatch({ type: 'CLEAR_PROCESSING_ERROR' });
    setResultTranslationError(null);
    setResultTranslationLoading(false);
    setBaseResultForTranslation(null);
    dispatch({ type: 'START_PROCESSING' });
  };

  const handleStoryNext = () => {
    dispatch({ type: 'SET_META_DRAFT', payload: '' });
    setMetaPreviewError(null);
    setPreviewData(null);
    setEditableCutPrompts({});
    setReferenceImages({});
    setReferenceError(null);
    setResultTranslationLanguage(defaultTranslationTarget(state.storyInput.outputLanguage));
    setResultTranslationError(null);
    setBaseResultForTranslation(null);
    dispatch({ type: 'NEXT' });
  };

  const handleStyleSelection = (style: NonNullable<typeof state.selectedStyle>) => {
    const frameOptions = state.frameSelections.map(() => []);
    dispatch({
      type: 'APPLY_STYLE',
      payload: {
        style,
        frameOptions,
      },
    });
  };

  const handleDownload = () => {
    if (!state.result) {
      return;
    }

    downloadWorkflowSnapshot({
      exportedAt: new Date().toISOString(),
      workflowStep: state.step,
      storyInput: state.storyInput,
      metaPrompt: state.metaPrompt,
      selectedStyle: state.selectedStyle,
      frameSelections: state.frameSelections,
      runId: state.processing.runId,
      result: state.result,
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
            outputLanguage={state.storyInput.outputLanguage}
            onTextChange={(value) => dispatch({ type: 'SET_STORY_TEXT', payload: value })}
            onInputModeChange={(mode) => dispatch({ type: 'SET_STORY_INPUT_MODE', payload: mode })}
            onOutputLanguageChange={(value) => dispatch({ type: 'SET_OUTPUT_LANGUAGE', payload: value })}
            onNext={handleStoryNext}
          />
        );

      case 'meta_prompt_1':
        return (
          <MetaPrompt1Screen
            draft={state.metaPrompt.draft}
            loading={metaPreviewLoading}
            errorMessage={metaPreviewError}
            onRegenerate={() => {
              dispatch({ type: 'SET_META_DRAFT', payload: '' });
              setMetaPreviewError(null);
              setPreviewData(null);
              setEditableCutPrompts({});
            }}
            onBack={goBack}
            onNext={goNext}
          />
        );

      case 'meta_prompt_2':
        return (
          <MetaPrompt2Screen
            selectedStyle={state.selectedStyle}
            referenceImages={referenceImages}
            loading={referenceLoading}
            errorMessage={referenceError}
            canProceed={Boolean(state.selectedStyle && referenceImages[state.selectedStyle])}
            onSelectStyle={handleStyleSelection}
            onRegenerate={() => {
              setReferenceImages({});
              setReferenceError(null);
            }}
            onBack={goBack}
            onNext={() => {
              if (state.selectedStyle && referenceImages[state.selectedStyle]) {
                goNext();
              }
            }}
          />
        );

      case 'meta_prompt_3':
        return (
          <MetaPrompt3Screen
            selectedStyle={state.selectedStyle}
            selectedReferenceImage={state.selectedStyle ? referenceImages[state.selectedStyle] ?? null : null}
            anchorPrompt={previewData?.anchor_prompt ?? ''}
            cutPrompts={previewData?.cut_plan.cuts
              .slice()
              .sort((a, b) => a.cut_number - b.cut_number)
              .map((cut) => ({
                cutNumber: cut.cut_number,
                prompt: editableCutPrompts[cut.cut_number] ?? cut.image_prompt,
              })) ?? []}
            onCutPromptChange={(cutNumber, prompt) => {
              setEditableCutPrompts((prev) => ({
                ...prev,
                [cutNumber]: prompt,
              }));
            }}
            onResetPrompts={() => {
              if (!previewData) return;
              const next: Record<number, string> = {};
              for (const cut of previewData.cut_plan.cuts) {
                next[cut.cut_number] = cut.image_prompt;
              }
              setEditableCutPrompts(next);
            }}
            onStartOver={() => {
              setResultTranslationLanguage(defaultTranslationTarget(state.storyInput.outputLanguage));
              setResultTranslationError(null);
              setBaseResultForTranslation(null);
              dispatch({ type: 'RESET' });
            }}
            onGenerateTeaser={startProcessing}
            onBack={goBack}
          />
        );

      case 'processing_state':
        return (
          <ProcessingStateScreen
            running={state.processing.running}
            runId={state.processing.runId}
            progressByStep={state.processing.progressByStep}
            errorMessage={state.processing.errorMessage}
            onRetry={startProcessing}
            onBack={goBack}
          />
        );

      case 'result':
        return state.result ? (
          <VideoExportScreen
            result={state.result}
            onBack={goBack}
            onDownload={handleDownload}
            translationLanguage={resultTranslationLanguage}
            translationLoading={resultTranslationLoading}
            translationError={resultTranslationError}
            onTranslationLanguageChange={setResultTranslationLanguage}
            onRegenerateTranslation={async () => {
              const sourceResult = baseResultForTranslation ?? state.result;
              if (!sourceResult) return;

              setResultTranslationLoading(true);
              setResultTranslationError(null);
              try {
                if (resultTranslationLanguage === state.storyInput.outputLanguage) {
                  throw new Error('Source language and target language are the same.');
                }
                const translated = await translateResultCuts(
                  sourceResult,
                  state.storyInput.outputLanguage,
                  resultTranslationLanguage,
                  new AbortController().signal,
                );
                dispatch({ type: 'PROCESSING_SUCCESS', payload: translated });
              } catch (error: unknown) {
                setResultTranslationError(normalizeError(error));
              } finally {
                setResultTranslationLoading(false);
              }
            }}
          />
        ) : (
          <ProcessingStateScreen
            running={false}
            runId={state.processing.runId}
            progressByStep={state.processing.progressByStep}
            errorMessage="Missing result payload. Please retry generation from Meta Prompt 3."
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
