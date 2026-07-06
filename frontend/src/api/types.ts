export interface RepoRecommendation {
  repo: string;
  summary: string;
}

export interface StorySummary {
  story_id: string;
  title: string;
  labels: string[];
}

export interface PipelineRunResponse {
  repo: string;
  story_count: number;
  cached: boolean;
  stories: StorySummary[];
}

interface BeatBase {
  beat_id: string;
  order: number;
}

export interface ContextBeat extends BeatBase {
  type: "context";
  title: string;
  body: string;
  source_refs: string[];
}

export interface DilemmaBeat extends BeatBase {
  type: "dilemma";
  title: string;
  body: string;
  source_refs: string[];
}

export interface ViewpointBeat extends BeatBase {
  type: "viewpoint";
  title: string;
  body: string;
  author: string;
  author_role: string;
  source_refs: string[];
}

export interface CheckpointBeat extends BeatBase {
  type: "checkpoint";
  question: string;
  format: "reflection";
  must_precede_decision: boolean;
}

export interface DecisionBeat extends BeatBase {
  type: "decision";
  title: string;
  body: string;
  source_refs: string[];
}

export interface LessonsBeat extends BeatBase {
  type: "lessons";
  title: string;
  lessons: string[];
}

export type Beat =
  | ContextBeat
  | DilemmaBeat
  | ViewpointBeat
  | CheckpointBeat
  | DecisionBeat
  | LessonsBeat;

export interface WorkspaceContent {
  story_id: string;
  beats: Beat[];
}

export interface LibraryEntry {
  repo: string;
  stories: StorySummary[];
}

export interface AnswerRequest {
  student_id: string;
  reflection: string;
  selected_option?: string;
}

export interface ViewpointOption {
  author: string;
  title: string;
}
