import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { listStories } from "../api/client";
import type { StorySummary } from "../api/types";
import { AppHeader } from "../components/AppHeader";
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

  function clearQualities() {
    const p = new URLSearchParams(params);
    p.delete("qualities");
    setSearchParams(p);
  }

  if (repos.length === 0) {
    return (
      <div className="landing">
        <div className="landing-inner">
          <AppHeader />
          <main className="landing-main">
            <div className="discover-empty">
              <h1>No repository selected</h1>
              <p>Head back and pick a repository to explore its stories.</p>
              <button className="btn-lg btn-mint" onClick={() => navigate("/")}>
                Back to start <span className="arrow" aria-hidden="true">→</span>
              </button>
            </div>
          </main>
        </div>
      </div>
    );
  }

  const showRepoBadges = repos.length > 1;
  const storyCount = groups?.reduce((n, g) => n + (g.stories?.length ?? 0), 0) ?? 0;

  // Merge per-repo label counts so each chip shows total available stories for
  // that quality across the selected repos.
  const mergedCounts: Record<string, number> = {};
  for (const g of groups ?? []) {
    for (const [k, v] of Object.entries(g.counts ?? {})) {
      mergedCounts[k] = (mergedCounts[k] ?? 0) + v;
    }
  }

  const headline = showRepoBadges
    ? `We found ${storyCount} engineering stories across ${repos.length} repositories! 🌟`
    : `We found some great stories in ${repos[0]}! 🌟`;

  const loading = !groups;

  return (
    <div className="landing">
      <div className="landing-inner">
        <AppHeader />

        <main className="catalog-main">
          <button className="back-link" onClick={() => navigate(-1)}>
            ← Back to Repositories
          </button>

          <section className="catalog-hero">
            <span className="step-capsule yellow">Step 3 of 3</span>
            <h1>{headline}</h1>
            <p>Choose a story below to dive into the background, the debate, and the code.</p>
          </section>

          <div className="catalog-chips">
            <button
              className={`catalog-chip${qualities.length === 0 ? " active" : ""}`}
              onClick={clearQualities}
            >
              All
            </button>
            {QUALITIES.map((q) => {
              const count = mergedCounts[q.id] ?? 0;
              const active = qualities.includes(q.id);
              return (
                <button
                  key={q.id}
                  className={`catalog-chip${active ? " active" : ""}${count === 0 && !active ? " empty" : ""}`}
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
            <div className="warn-card warn-row">
              <span>Story mining failed for: {failedMining.join(", ")}</span>
              <button className="btn-sm ghost" onClick={() => setNoticeDismissed(true)}>
                Dismiss
              </button>
            </div>
          )}

          {groups?.map(
            (g) =>
              g.error && (
                <div key={g.repo} className="warn-card">
                  {g.repo}: {g.error}
                </div>
              ),
          )}

          {loading ? (
            <div className="story-feed" aria-busy="true">
              {Array.from({ length: 3 }).map((_, i) => (
                <div key={i} className="story-card skeleton" aria-hidden="true">
                  <div className="sk-line sk-title" />
                  <div className="sk-line sk-tag" />
                </div>
              ))}
            </div>
          ) : (
            <>
              <div className="story-feed">
                {groups!.flatMap(
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
                <p className="catalog-empty">
                  No stories matched the selected quality filters. Try removing a filter or picking
                  different repos.
                </p>
              )}
            </>
          )}
        </main>
      </div>
    </div>
  );
}
