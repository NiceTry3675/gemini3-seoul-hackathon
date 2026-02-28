export type WorkflowStep =
  | 'story_input'
  | 'meta_prompt_1'
  | 'meta_prompt_2'
  | 'meta_prompt_3'
  | 'processing_state'
  | 'video_export';

export type StoryInputMode = 'summary' | 'original';

export interface StoryInputModel {
  text: string;
  inputMode: StoryInputMode;
  charCount: number;
}

export interface MetaPromptModel {
  draft: string;
  history: string[];
}

export type VisualStyleId =
  | 'cinematic_art'
  | 'anime_2d'
  | 'oil_painting'
  | 'digital_sketch';

export interface VisualStyleOption {
  id: VisualStyleId;
  title: string;
  description: string;
  imageUrl: string;
}

export interface FrameOption {
  id: string;
  label: string;
  subtitle: string;
  tag: string;
  description: string;
  imageUrl: string;
}

export type FrameStatus = 'active' | 'locked' | 'complete';

export interface FrameSelection {
  frameIndex: number;
  sequenceLabel: string;
  status: FrameStatus;
  selectedOptionId: string | null;
  options: FrameOption[];
  generation: number;
}

export interface SourceFrame {
  index: number;
  imageUrl: string;
  selectedOptionLabel: string;
}

export interface VideoSettings {
  musicStyle: string;
  transition: string;
  duration: string;
  format: string;
}

export interface VideoExportModel {
  title: string;
  subtitle: string;
  previewImageUrl: string;
  sourceFrames: SourceFrame[];
  settings: VideoSettings;
  renderSeconds: number;
}

export interface ProcessingState {
  running: boolean;
  errorMessage: string | null;
}

export interface AppWorkflowState {
  step: WorkflowStep;
  storyInput: StoryInputModel;
  metaPrompt: MetaPromptModel;
  selectedStyle: VisualStyleId | null;
  frameSelections: FrameSelection[];
  processing: ProcessingState;
  videoExport: VideoExportModel | null;
}

export interface MockRenderPayload {
  storyText: string;
  metaPrompt: string;
  style: VisualStyleId;
  frameSelections: FrameSelection[];
}

export type WorkflowAction =
  | { type: 'SET_STORY_TEXT'; payload: string }
  | { type: 'SET_STORY_INPUT_MODE'; payload: StoryInputMode }
  | { type: 'SET_META_DRAFT'; payload: string }
  | { type: 'PUSH_META_HISTORY'; payload: string }
  | {
      type: 'APPLY_STYLE';
      payload: {
        style: VisualStyleId;
        frameOptions: FrameOption[][];
      };
    }
  | {
      type: 'SELECT_FRAME_OPTION';
      payload: {
        frameIndex: number;
        optionId: string;
      };
    }
  | {
      type: 'REGENERATE_FRAME_OPTIONS';
      payload: {
        frameIndex: number;
        options: FrameOption[];
      };
    }
  | { type: 'NEXT' }
  | { type: 'BACK' }
  | { type: 'START_PROCESSING' }
  | { type: 'PROCESSING_SUCCESS'; payload: VideoExportModel }
  | { type: 'PROCESSING_ERROR'; payload: string }
  | { type: 'CLEAR_PROCESSING_ERROR' }
  | { type: 'RESET' };

export const WORKFLOW_STEPS: WorkflowStep[] = [
  'story_input',
  'meta_prompt_1',
  'meta_prompt_2',
  'meta_prompt_3',
  'processing_state',
  'video_export',
];
