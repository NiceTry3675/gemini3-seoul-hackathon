import { useEffect, useReducer, useState, useCallback } from 'react';
import MetaPrompt1Screen from './components/screens/MetaPrompt1Screen';
import MetaPrompt2Screen from './components/screens/MetaPrompt2Screen';
import MetaPrompt3Screen from './components/screens/MetaPrompt3Screen';
import ProcessingStateScreen from './components/screens/ProcessingStateScreen';
import StoryInputScreen from './components/screens/StoryInputScreen';
import VideoExportScreen from './components/screens/VideoExportScreen';
import { fetchPipelinePreview, generateMediaFromPreview, generateReferenceImages, mapVisualStyleToPipelineTemplate, teaserResultToExport } from './services/workflowService';
import { createInitialWorkflowState, workflowReducer } from './state/workflowReducer';
import { STYLE_TONE_BY_ID } from './data/workflowData';
import type { PipelinePreviewModel, VisualStyleId, WorkflowStep } from './types/workflow';
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

function normalizeError(error: unknown): string {
  if (error instanceof DOMException && error.name === 'AbortError') return 'Generation cancelled.';
  if (error instanceof Error && error.message.trim().length > 0) return error.message;
  return 'Unknown pipeline error.';
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

  // Pipeline preview state
  const [previewData, setPreviewData] = useState<PipelinePreviewModel | null>(null);
  const [editableCutPrompts, setEditableCutPrompts] = useState<Record<number, string>>({});
  const [metaPreviewLoading, setMetaPreviewLoading] = useState(false);
  const [metaPreviewError, setMetaPreviewError] = useState<string | null>(null);
  const [referenceLoading, setReferenceLoading] = useState(false);
  const [referenceError, setReferenceError] = useState<string | null>(null);
  const [referenceImages, setReferenceImages] = useState<Partial<Record<VisualStyleId, { imageBase64: string; mimeType: string }>>>({});


  // Sync step -> URL hash
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

  // Auto-fetch pipeline preview on meta_prompt_1 when draft is empty and story text exists
  useEffect(() => {
    if (state.step !== 'meta_prompt_1') return undefined;
    if (state.metaPrompt.draft.trim().length > 0) return undefined;
    if (!state.storyInput.text.trim()) return undefined;
    if (previewData !== null) return undefined;

    let cancelled = false;
    setMetaPreviewLoading(true);
    setMetaPreviewError(null);

    const styleTemplate = state.selectedStyle
      ? mapVisualStyleToPipelineTemplate(state.selectedStyle)
      : 'webtoon_cel';

    void fetchPipelinePreview(state.storyInput.text, styleTemplate)
      .then((preview) => {
        if (!cancelled) {
          setPreviewData(preview);
          dispatch({ type: 'SET_META_DRAFT', payload: preview.anchor_prompt });
        }
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setMetaPreviewError(normalizeError(error));
        }
      })
      .finally(() => {
        if (!cancelled) {
          setMetaPreviewLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [
    state.step,
    state.metaPrompt.draft,
    state.storyInput.text,
    state.selectedStyle,
    previewData,
  ]);

  // Auto-generate reference images on meta_prompt_2
  useEffect(() => {
    if (state.step !== 'meta_prompt_2') return undefined;
    if (!previewData) return undefined;
    if (Object.keys(referenceImages).length > 0) return undefined;

    let cancelled = false;
    setReferenceLoading(true);
    setReferenceError(null);

    const mainCharacter = previewData.characters?.characters?.[0];
    const characterPrompt = mainCharacter?.visual_prompt ?? '';

    void generateReferenceImages(characterPrompt)
      .then((results) => {
        if (!cancelled) {
          const map: Partial<Record<VisualStyleId, { imageBase64: string; mimeType: string }>> = {};
          for (const r of results) {
            map[r.style] = { imageBase64: r.imageBase64, mimeType: 'image/png' };
          }
          setReferenceImages(map);
        }
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setReferenceError(normalizeError(error));
        }
      })
      .finally(() => {
        if (!cancelled) {
          setReferenceLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [state.step, previewData, referenceImages]);

  // Sync editableCutPrompts from previewData
  useEffect(() => {
    if (!previewData) return;
    const prompts: Record<number, string> = {};
    for (const cut of previewData.cuts) {
      prompts[cut.cut_number] = cut.styled_prompt;
    }
    setEditableCutPrompts(prompts);
  }, [previewData]);

  // Media generation on processing_state
  useEffect(() => {
    if (state.step !== 'processing_state' || !state.processing.running) {
      return undefined;
    }
    if (!state.selectedStyle) return undefined;

    let cancelled = false;
    const styleTemplate = mapVisualStyleToPipelineTemplate(state.selectedStyle);
    const styleTone = STYLE_TONE_BY_ID[state.selectedStyle];

    if (previewData) {
      // Use preview-based generation with prompt overrides
      const previewWithOverrides: PipelinePreviewModel = {
        ...previewData,
        cuts: previewData.cuts.map((cut) => ({
          ...cut,
          styled_prompt: editableCutPrompts[cut.cut_number] ?? cut.styled_prompt,
        })),
      };

      void generateMediaFromPreview(previewWithOverrides, styleTemplate)
        .then((result) => {
          if (!cancelled) {
            dispatch({ type: 'PROCESSING_SUCCESS', payload: result });
          }
        })
        .catch((error: unknown) => {
          if (!cancelled) {
            dispatch({ type: 'PROCESSING_ERROR', payload: normalizeError(error) });
          }
        });
    } else {
      // Fallback: fetch preview first then generate
      void fetchPipelinePreview(state.storyInput.text, styleTemplate)
        .then((preview) => {
          if (cancelled) return;
          setPreviewData(preview);
          return generateMediaFromPreview(preview, styleTemplate);
        })
        .then((result) => {
          if (!cancelled && result) {
            dispatch({ type: 'PROCESSING_SUCCESS', payload: result });
          }
        })
        .catch((error: unknown) => {
          if (!cancelled) {
            dispatch({ type: 'PROCESSING_ERROR', payload: normalizeError(error) });
          }
        });
    }

    // Suppress unused variable warning - styleTone used below in result building
    void styleTone;

    return () => {
      cancelled = true;
    };
  }, [
    state.step,
    state.processing.running,
    state.selectedStyle,
    state.storyInput.text,
    previewData,
    editableCutPrompts,
  ]);

  const goBack = () => dispatch({ type: 'BACK' });
  const goNext = () => dispatch({ type: 'NEXT' });

  const startProcessing = () => {
    dispatch({ type: 'CLEAR_PROCESSING_ERROR' });
    dispatch({ type: 'START_PROCESSING' });
  };

  const handleStoryNext = () => {
    setPreviewData(null);
    setMetaPreviewError(null);
    setEditableCutPrompts({});
    setReferenceImages({});
    setReferenceError(null);
    dispatch({ type: 'SET_META_DRAFT', payload: '' });
    dispatch({ type: 'NEXT' });
  };

  const handleStyleSelection = (style: NonNullable<typeof state.selectedStyle>) => {
    dispatch({
      type: 'APPLY_STYLE',
      payload: {
        style,
        frameOptions: [],
      },
    });
  };

  const handleDownload = () => {
    downloadWorkflowSnapshot({
      exportedAt: new Date().toISOString(),
      workflowStep: state.step,
      storyInput: state.storyInput,
      metaPrompt: state.metaPrompt,
      selectedStyle: state.selectedStyle,
      frameSelections: state.frameSelections,
      result: state.result,
      videoExport: state.videoExport,
    });
  };

  const navigateToStep = useCallback((step: WorkflowStep) => {
    dispatch({ type: 'JUMP_TO_STEP', payload: step });
  }, []);

  const buildVideoExportFromResult = () => {
    if (!state.result) return null;
    const resultCuts = state.result.cuts.slice().sort((a, b) => a.cut_number - b.cut_number);
    const styleTone = state.selectedStyle ? (STYLE_TONE_BY_ID[state.selectedStyle] ?? 'Cinematic') : 'Cinematic';
    return {
      title: 'Your Teaser',
      subtitle: 'AI-generated 9-cut teaser is ready.',
      previewImageUrl: resultCuts[0] ? `data:image/png;base64,${resultCuts[0].image_base64}` : '',
      sourceFrames: resultCuts.map((cut) => ({
        index: cut.cut_number,
        imageUrl: `data:image/png;base64,${cut.image_base64}`,
        selectedOptionLabel: `Cut ${cut.cut_number}`,
      })),
      settings: {
        musicStyle: styleTone,
        transition: 'Fade',
        duration: '15 Seconds',
        format: '9:16 Vertical',
      },
      renderSeconds: 0,
    };
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
              setEditableCutPrompts((prev) => ({ ...prev, [cutNumber]: prompt }));
            }}
            onResetPrompts={() => {
              if (!previewData) return;
              const next: Record<number, string> = {};
              for (const cut of previewData.cut_plan.cuts) {
                next[cut.cut_number] = cut.image_prompt;
              }
              setEditableCutPrompts(next);
            }}
            onStartOver={() => dispatch({ type: 'RESET' })}
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

      case 'result': {
        const videoExportData = buildVideoExportFromResult();
        if (!videoExportData) {
          return (
            <div className="flex min-h-screen flex-col items-center justify-center gap-6 text-slate-100">
              <span className="material-symbols-outlined text-6xl text-slate-500">hourglass_empty</span>
              <h2 className="text-3xl font-bold">No result yet</h2>
              <p className="text-slate-400">Generate a teaser first.</p>
              <button
                type="button"
                onClick={() => navigateToStep('story_input')}
                className="rounded-lg bg-[#2b6cee] px-6 py-3 font-bold text-white hover:bg-blue-600"
              >
                Start from Beginning
              </button>
            </div>
          );
        }
        return (
          <VideoExportScreen
            videoExport={videoExportData}
            storyText={state.storyInput.text}
            onBack={goBack}
            onDownload={handleDownload}
            onReset={() => dispatch({ type: 'RESET' })}
          />
        );
      }

      case 'video_export': {
        const videoExportData = buildVideoExportFromResult() ?? state.videoExport;
        if (!videoExportData) {
          return (
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
        }
        return (
          <VideoExportScreen
            videoExport={videoExportData}
            storyText={state.storyInput.text}
            onBack={goBack}
            onDownload={handleDownload}
            onReset={() => dispatch({ type: 'RESET' })}
          />
        );
      }

      default:
        return null;
    }
  };

  return <>{renderStep(state.step)}</>;
}
