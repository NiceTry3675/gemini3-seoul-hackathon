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

export type PipelineWorkflowStep = 'story_input' | 'processing_state' | 'result';

export type PipelineOutputLanguage = 'ko' | 'en' | 'ja';

export type PipelineStyleTemplate =
  | 'webtoon_cel'
  | 'cinematic_realism'
  | 'watercolor_dream'
  | 'digital_masterpaint';

export interface PipelineStyleOption {
  id: PipelineStyleTemplate;
  title: string;
  description: string;
}

export interface PipelineStoryInputModel {
  manuscript: string;
  genre: string;
  tone: string;
  outputLanguage: PipelineOutputLanguage;
  styleTemplate: PipelineStyleTemplate;
}

export type PipelineProgressStatus = 'running' | 'completed' | 'failed';

export interface PipelineProgressEvent {
  step: number;
  step_name: string;
  status: PipelineProgressStatus;
  detail?: string | null;
}

export interface PipelineCharacter {
  name: string;
  appearance: string;
  personality: string;
  role: string;
  visual_prompt: string;
}

export interface PipelineValidationIssue {
  cut_number?: number | null;
  issue_type: string;
  description: string;
  severity: 'error' | 'warning';
}

export interface PipelineValidationReport {
  is_valid: boolean;
  issues: PipelineValidationIssue[];
  summary: string;
}

export interface PipelineGeneratedCut {
  cut_number: number;
  image_base64: string;
  mime_type: string;
  video_base64: string;
  video_mime_type: string;
  dialogue: string[];
  narration: string;
  description: string;
}

export interface PipelineResultModel {
  characters: { characters: PipelineCharacter[] };
  cuts: PipelineGeneratedCut[];
  validation_report: PipelineValidationReport | null;
  reference_images: Record<string, string>;
}

export interface PipelineProcessingState {
  running: boolean;
  errorMessage: string | null;
  runId: string | null;
  progressByStep: Record<number, PipelineProgressEvent>;
}

export interface PipelineWorkflowState {
  step: PipelineWorkflowStep;
  storyInput: PipelineStoryInputModel;
  processing: PipelineProcessingState;
  result: PipelineResultModel | null;
}

export type PipelineWorkflowAction =
  | { type: 'SET_MANUSCRIPT'; payload: string }
  | { type: 'SET_GENRE'; payload: string }
  | { type: 'SET_TONE'; payload: string }
  | { type: 'SET_OUTPUT_LANGUAGE'; payload: PipelineOutputLanguage }
  | { type: 'SET_STYLE_TEMPLATE'; payload: PipelineStyleTemplate }
  | { type: 'START_PROCESSING' }
  | { type: 'SET_RUN_ID'; payload: string }
  | { type: 'UPDATE_PROGRESS'; payload: PipelineProgressEvent }
  | { type: 'PROCESSING_SUCCESS'; payload: PipelineResultModel }
  | { type: 'PROCESSING_ERROR'; payload: string }
  | { type: 'CLEAR_PROCESSING_ERROR' }
  | { type: 'BACK_TO_INPUT' }
  | { type: 'RESET' };
