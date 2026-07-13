import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { listStories } from "../api/client";
import type { StorySummary } from "../api/types";
import { StoryCard } from "../components/StoryCard";
import { QUALITIES } from "../filters";

interface RepoStories {
  repo: string;
  stories: StorySummary[] | null;
  error: string | null;
}

export function StoryCatalogPage() {
  const [params] = useSearchParams();
  // "repos" is the multi-repo param; "repo" kept for old single-repo links.
  const repos =
    params.get("repos")?.split(",").filter(Boolean) ??
    (params.get("repo") ? [params.get("repo")!] : []);
  const qualities = params.get("qualities")?.split(",").filter(Boolean) ?? [];
  const failedMining = params.get("failed")?.split(",").filter(Boolean) ?? [];
  const navigate = useNavigate();

  const [groups, setGroups] = useState<RepoStories[] | null>(null);
  const [noticeDismissed, setNoticeDismissed] = useState(false);

  const paramKey = params.toString();
  useEffect(() => {
    if (repos.length === 0) return;
    setGroups(null);
    Promise.allSettled(repos.map((repo) => listStories(repo, qualities))).then((results) =>
      setGroups(
        results.map((result, i) => ({
          repo: repos[i],
          stories: result.status === "fulfilled" ? result.value : null,
          error: result.status === "rejected" ? (result.reason as Error).message : null,
        })),
      ),
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [paramKey]);

  if (repos.length === 0) {
    return (
      <p className="page">
        No repo selected. <a href="/">Go back</a>
      </p>
    );
  }
  if (!groups) return <p className="page">Loading stories for {repos.join(", ")}...</p>;

  const showRepoBadges = repos.length > 1;
  const storyCount = groups.reduce((n, g) => n + (g.stories?.length ?? 0), 0);
  const qualityLabels = qualities
    .map((id) => QUALITIES.find((q) => q.id === id)?.label ?? id)
    .join(", ");

  return (
    <div className="page">
      <h1>{repos.join(" · ")}</h1>
      <p>
        {storyCount} engineering stories found
        {qualityLabels && ` — filtered by ${qualityLabels}`}
      </p>

      {failedMining.length > 0 && !noticeDismissed && (
        <div className="notice">
          Story mining failed for: {failedMining.join(", ")}
          <button className="notice-dismiss" onClick={() => setNoticeDismissed(true)}>
            Dismiss
          </button>
        </div>
      )}

      {groups.map(
        (g) =>
          g.error && (
            <p key={g.repo} className="error">
              {g.repo}: {g.error}
            </p>
          ),
      )}

      <div className="grid">
        {groups.flatMap(
          (g) =>
            g.stories?.map((s) => (
              <StoryCard
                key={s.story_id}
                story={s}
                repoBadge={showRepoBadges ? g.repo : undefined}
                onOpen={() => navigate(`/workspace?story=${encodeURIComponent(s.story_id)}`)}
              />
            )) ?? [],
        )}
      </div>

      {storyCount === 0 && (
        <p>
          No stories matched the selected quality filters. Try removing a filter or picking
          different repos.
        </p>
      )}
    </div>
  );
}
