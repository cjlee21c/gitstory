import { UNAUTHORIZED_EVENT, clearAccessCode, getAccessCode } from "./access";
import type {
  AnswerRequest,
  DiscoverFilters,
  DiscoverResponse,
  LibraryEntry,
  PipelineRunResponse,
  StoryListResponse,
  WorkspaceContent,
} from "./types";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

function encodeStoryId(storyId: string): string {
  return storyId.replace("#", "%23");
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      "X-Access-Code": getAccessCode(),
      ...init?.headers,
    },
  });
  if (!res.ok) {
    // A 401 means the access code is missing/invalid (e.g. it was rotated
    // mid-deploy). Drop it and signal the app to re-prompt for a code.
    if (res.status === 401) {
      clearAccessCode();
      window.dispatchEvent(new Event(UNAUTHORIZED_EVENT));
    }
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `Request failed: ${res.status}`);
  }
  return res.json();
}

// Validates a code against the backend gate (GET /auth/check). Returns true
// only on 200; used by the access gate before storing the code.
export async function checkAccessCode(code: string): Promise<boolean> {
  const res = await fetch(`${API_BASE}/auth/check`, {
    headers: { "X-Access-Code": code },
  });
  return res.ok;
}

export function discoverRepos(filters: DiscoverFilters): Promise<DiscoverResponse> {
  return request("/discover", {
    method: "POST",
    body: JSON.stringify(filters),
  });
}

export function runPipeline(repo: string, force = false): Promise<PipelineRunResponse> {
  return request(`/repos/${repo}/pipeline?force=${force}`, { method: "POST" });
}

// In-flight pipeline runs, keyed by repo. Mining is kicked off from an effect
// now that the catalog page drives it, and StrictMode invokes effects twice in
// development — without this, both invocations would miss the backend cache and
// pay for a full duplicate run. Entries are dropped once settled so a genuine
// later visit re-requests (and gets a cache hit).
const inFlightPipelines = new Map<string, Promise<PipelineRunResponse>>();

export function runPipelineOnce(repo: string): Promise<PipelineRunResponse> {
  const existing = inFlightPipelines.get(repo);
  if (existing) return existing;

  const run = runPipeline(repo).finally(() => inFlightPipelines.delete(repo));
  inFlightPipelines.set(repo, run);
  return run;
}

export function listStories(repo: string, qualities: string[] = []): Promise<StoryListResponse> {
  const query = qualities.length ? `?qualities=${encodeURIComponent(qualities.join(","))}` : "";
  return request(`/repos/${repo}/stories${query}`);
}

export function getWorkspace(storyId: string): Promise<WorkspaceContent> {
  return request(`/stories/${encodeStoryId(storyId)}/workspace`);
}

// Part 1 (opening beats) is awaited to render; Part 2 (decision + lessons) is
// fetched in parallel and its latency hides behind the checkpoint gate.
export function getWorkspacePart(storyId: string, part: 1 | 2): Promise<WorkspaceContent> {
  return request(`/stories/${encodeStoryId(storyId)}/workspace?part=${part}`);
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
