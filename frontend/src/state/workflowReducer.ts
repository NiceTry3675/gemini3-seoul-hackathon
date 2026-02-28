import { FRAME_SEQUENCE } from '../data/workflowData';
import type {
  AppWorkflowState,
  FrameSelection,
  StoryInputMode,
  WorkflowAction,
  WorkflowStep,
} from '../types/workflow';

function createInitialFrames(): FrameSelection[] {
  return FRAME_SEQUENCE.map((label, index) => ({
    frameIndex: index + 1,
    sequenceLabel: label,
    status: index === 0 ? 'active' : 'locked',
    selectedOptionId: null,
    options: [],
    generation: 0,
  }));
}

function createInitialProcessingState(): AppWorkflowState['processing'] {
  return {
    running: false,
    errorMessage: null,
    runId: null,
    progressByStep: {},
  };
}

function recomputeFrameStatuses(frameSelections: FrameSelection[]): FrameSelection[] {
  let unlockNext = true;

  return frameSelections.map((selection) => {
    if (!unlockNext) {
      return { ...selection, status: 'locked' };
    }

    if (selection.selectedOptionId) {
      return { ...selection, status: 'complete' };
    }

    unlockNext = false;
    return { ...selection, status: 'active' };
  });
}

function isMetaPromptValid(state: AppWorkflowState): boolean {
  return state.metaPrompt.draft.trim().length > 0;
}

function hasStyleSelection(state: AppWorkflowState): boolean {
  return state.selectedStyle !== null;
}

function applyBackStep(current: WorkflowStep): WorkflowStep {
  switch (current) {
    case 'meta_prompt_1':
      return 'story_input';
    case 'meta_prompt_2':
      return 'meta_prompt_1';
    case 'meta_prompt_3':
      return 'meta_prompt_2';
    case 'processing_state':
      return 'meta_prompt_3';
    case 'result':
      return 'story_input';
    default:
      return current;
  }
}

export function createInitialWorkflowState(): AppWorkflowState {
  return {
    step: 'story_input',
    storyInput: {
      text: '',
      inputMode: 'original',
      charCount: 0,
    },
    metaPrompt: {
      draft: '',
      history: [],
    },
    selectedStyle: null,
    frameSelections: createInitialFrames(),
    processing: createInitialProcessingState(),
    result: null,
  };
}

export function workflowReducer(
  state: AppWorkflowState,
  action: WorkflowAction,
): AppWorkflowState {
  switch (action.type) {
    case 'SET_STORY_TEXT': {
      const text = action.payload;
      return {
        ...state,
        storyInput: {
          ...state.storyInput,
          text,
          charCount: text.length,
        },
      };
    }

    case 'SET_STORY_INPUT_MODE':
      return {
        ...state,
        storyInput: {
          ...state.storyInput,
          inputMode: action.payload as StoryInputMode,
        },
      };

    case 'SET_META_DRAFT':
      return {
        ...state,
        metaPrompt: {
          ...state.metaPrompt,
          draft: action.payload,
        },
      };

    case 'PUSH_META_HISTORY':
      return {
        ...state,
        metaPrompt: {
          ...state.metaPrompt,
          history: [action.payload, ...state.metaPrompt.history].slice(0, 8),
        },
      };

    case 'APPLY_STYLE': {
      const frames: FrameSelection[] = state.frameSelections.map((frame, frameIdx) => ({
        ...frame,
        status: frameIdx === 0 ? ('active' as const) : ('locked' as const),
        selectedOptionId: null,
        options: action.payload.frameOptions[frameIdx] ?? [],
        generation: 0,
      }));

      return {
        ...state,
        selectedStyle: action.payload.style,
        frameSelections: frames,
        result: null,
      };
    }

    case 'SELECT_FRAME_OPTION': {
      const next = state.frameSelections.map((frame) => {
        if (frame.frameIndex !== action.payload.frameIndex) {
          return frame;
        }
        if (frame.status === 'locked') {
          return frame;
        }
        return {
          ...frame,
          selectedOptionId: action.payload.optionId,
        };
      });

      return {
        ...state,
        frameSelections: recomputeFrameStatuses(next),
      };
    }

    case 'REGENERATE_FRAME_OPTIONS': {
      const next: FrameSelection[] = state.frameSelections.map((frame) => {
        if (frame.frameIndex < action.payload.frameIndex) {
          return frame;
        }

        if (frame.frameIndex === action.payload.frameIndex) {
          return {
            ...frame,
            options: action.payload.options,
            selectedOptionId: null,
            generation: frame.generation + 1,
          };
        }

        return {
          ...frame,
          selectedOptionId: null,
          status: 'locked' as const,
        };
      });

      return {
        ...state,
        frameSelections: recomputeFrameStatuses(next),
      };
    }

    case 'NEXT': {
      if (state.step === 'story_input') {
        return { ...state, step: 'meta_prompt_1' };
      }
      if (state.step === 'meta_prompt_1' && isMetaPromptValid(state)) {
        return { ...state, step: 'meta_prompt_2' };
      }
      if (state.step === 'meta_prompt_2' && hasStyleSelection(state)) {
        return { ...state, step: 'meta_prompt_3' };
      }
      return state;
    }

    case 'BACK':
      return {
        ...state,
        step: applyBackStep(state.step),
        processing:
          state.step === 'processing_state'
            ? { ...state.processing, running: false }
            : state.processing,
      };

    case 'START_PROCESSING':
      if (state.selectedStyle === null || state.storyInput.text.trim().length === 0) {
        return state;
      }
      return {
        ...state,
        step: 'processing_state',
        result: null,
        processing: {
          ...createInitialProcessingState(),
          running: true,
        },
      };

    case 'SET_RUN_ID':
      return {
        ...state,
        processing: {
          ...state.processing,
          runId: action.payload,
          running: true,
        },
      };

    case 'UPDATE_PROGRESS':
      return {
        ...state,
        processing: {
          ...state.processing,
          // Keep stream active across step-level "completed" updates.
          // Pipeline stops only on explicit failure or terminal success action.
          running: action.payload.status === 'failed' ? false : state.processing.running,
          progressByStep: {
            ...state.processing.progressByStep,
            [action.payload.step]: action.payload,
          },
        },
      };

    case 'PROCESSING_SUCCESS':
      return {
        ...state,
        step: 'result',
        result: action.payload,
        processing: {
          ...state.processing,
          running: false,
          errorMessage: null,
        },
      };

    case 'PROCESSING_ERROR':
      return {
        ...state,
        step: 'processing_state',
        processing: {
          ...state.processing,
          running: false,
          errorMessage: action.payload,
        },
      };

    case 'CLEAR_PROCESSING_ERROR':
      return {
        ...state,
        processing: {
          ...state.processing,
          errorMessage: null,
        },
      };

    case 'RESET':
      return createInitialWorkflowState();

    default:
      return state;
  }
}
