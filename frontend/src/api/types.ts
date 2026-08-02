export interface RepoRecommendation {
  repo: string;
  summary: string;
  stars?: number | null;
  language?: string | null;
}

export interface DiscoverFilters {
  domain: string;
  sizes: string[];
  stars: string | null;
  contributors: string | null;
  keyword: string | null;
  // Rotates which slice of the result pool this student sees, so returning to
  // the same filters doesn't surface the same repos again.
  student_id?: string | null;
}

export interface DiscoverResponse {
  repos: RepoRecommendation[];
  // Present when the filters matched too little on GitHub and were widened.
  notice: string | null;
  relaxed: string[];
}

export interface StorySummary {
  story_id: string;
  title: string;
  labels: string[];
  qualities: string[];
}

export interface StoryListResponse {
  stories: StorySummary[];
  quality_counts: Record<string, number>;
  // Set when the selected focus matched nothing and `stories` is the
  // unfiltered fallback instead.
  notice: string | null;
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
  domain?: string | null;
  description?: string | null;
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
