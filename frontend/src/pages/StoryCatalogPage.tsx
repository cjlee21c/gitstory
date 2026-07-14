import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { listStories } from "../api/client";
import type { StorySummary } from "../api/types";
import { StoryCard } from "../components/StoryCard";
import { QUALITIES } from "../filters";

interface RepoStories {
  repo: string;
  stories: StorySummary[] | null;
  counts: Record<string, number> | null;
  error: string | null;
}

export function StoryCatalogPage() {
  const [params, setSearchParams] = useSearchParams();
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
          stories: result.status === "fulfilled" ? result.value.stories : null,
          counts: result.status === "fulfilled" ? result.value.quality_counts : null,
          error: result.status === "rejected" ? (result.reason as Error).message : null,
        })),
      ),
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [paramKey]);

  // Toggling a quality just rewrites the URL param; the effect re-fetches
  // (a free read-time, cache-hit call — no tokens).
  function toggleQuality(id: string) {
    const next = qualities.includes(id)
      ? qualities.filter((q) => q !== id)
      : [...qualities, id];
    const p = new URLSearchParams(params);
    if (next.length) p.set("qualities", next.join(","));
    else p.delete("qualities");
    setSearchParams(p);
  }

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

  // Merge per-repo label counts so each chip shows total available stories for
  // that quality across the selected repos.
  const mergedCounts: Record<string, number> = {};
  for (const g of groups) {
    for (const [k, v] of Object.entries(g.counts ?? {})) {
      mergedCounts[k] = (mergedCounts[k] ?? 0) + v;
    }
  }

  return (
    <div className="page">
      <h1>{repos.join(" · ")}</h1>
      <p>
        {storyCount} engineering stories found
        {qualityLabels && ` — filtered by ${qualityLabels}`}
      </p>

      <div className="chip-bar">
        {QUALITIES.map((q) => {
          const count = mergedCounts[q.id] ?? 0;
          const active = qualities.includes(q.id);
          return (
            <button
              key={q.id}
              className={`chip${active ? " chip-active" : ""}${count === 0 ? " chip-empty" : ""}`}
              onClick={() => toggleQuality(q.id)}
              disabled={count === 0 && !active}
              title={count === 0 ? "No stories carry this quality" : undefined}
            >
              {q.label} ({count})
            </button>
          );
        })}
      </div>

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
