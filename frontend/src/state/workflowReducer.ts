import type {
  PipelineWorkflowAction,
  PipelineWorkflowState,
} from '../types/workflow';

function createInitialProcessingState(): PipelineWorkflowState['processing'] {
  return {
    running: false,
    errorMessage: null,
    runId: null,
    progressByStep: {},
  };
}

export function createInitialWorkflowState(): PipelineWorkflowState {
  return {
    step: 'story_input',
    storyInput: {
      manuscript: '',
      genre: '',
      tone: '',
      outputLanguage: 'ko',
      styleTemplate: 'webtoon_cel',
    },
    processing: createInitialProcessingState(),
    result: null,
  };
}

export function canStartPipeline(state: PipelineWorkflowState): boolean {
  return state.storyInput.manuscript.trim().length > 0;
}

export function workflowReducer(
  state: PipelineWorkflowState,
  action: PipelineWorkflowAction,
): PipelineWorkflowState {
  switch (action.type) {
    case 'SET_MANUSCRIPT':
      return {
        ...state,
        storyInput: {
          ...state.storyInput,
          manuscript: action.payload,
        },
      };

    case 'SET_GENRE':
      return {
        ...state,
        storyInput: {
          ...state.storyInput,
          genre: action.payload,
        },
      };

    case 'SET_TONE':
      return {
        ...state,
        storyInput: {
          ...state.storyInput,
          tone: action.payload,
        },
      };

    case 'SET_OUTPUT_LANGUAGE':
      return {
        ...state,
        storyInput: {
          ...state.storyInput,
          outputLanguage: action.payload,
        },
      };

    case 'SET_STYLE_TEMPLATE':
      return {
        ...state,
        storyInput: {
          ...state.storyInput,
          styleTemplate: action.payload,
        },
      };

    case 'START_PROCESSING':
      if (!canStartPipeline(state)) {
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

    case 'BACK_TO_INPUT':
      return {
        ...state,
        step: 'story_input',
        processing: {
          ...state.processing,
          running: false,
        },
      };

    case 'RESET':
      return createInitialWorkflowState();

    default:
      return state;
  }
}
