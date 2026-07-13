import type {
  AnswerRequest,
  DiscoverFilters,
  LibraryEntry,
  PipelineRunResponse,
  RepoRecommendation,
  StorySummary,
  WorkspaceContent,
} from "./types";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

function encodeStoryId(storyId: string): string {
  return storyId.replace("#", "%23");
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `Request failed: ${res.status}`);
  }
  return res.json();
}

export function discoverRepos(filters: DiscoverFilters): Promise<RepoRecommendation[]> {
  return request("/discover", {
    method: "POST",
    body: JSON.stringify(filters),
  });
}

export function runPipeline(repo: string, force = false): Promise<PipelineRunResponse> {
  return request(`/repos/${repo}/pipeline?force=${force}`, { method: "POST" });
}

export function listStories(repo: string, qualities: string[] = []): Promise<StorySummary[]> {
  const query = qualities.length ? `?qualities=${encodeURIComponent(qualities.join(","))}` : "";
  return request(`/repos/${repo}/stories${query}`);
}

export function getWorkspace(storyId: string): Promise<WorkspaceContent> {
  return request(`/stories/${encodeStoryId(storyId)}/workspace`);
}

export function getLibrary(): Promise<LibraryEntry[]> {
  return request("/library");
}

export function saveAnswer(storyId: string, body: AnswerRequest): Promise<{ status: string }> {
  return request(`/stories/${encodeStoryId(storyId)}/answers`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}
