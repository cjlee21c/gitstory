import { useEffect, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { listStories, runPipelineOnce } from "../api/client";
import type { StorySummary } from "../api/types";
import { AppHeader } from "../components/AppHeader";
import { StoryCard } from "../components/StoryCard";
import { QUALITIES } from "../filters";

interface RepoStories {
  repo: string;
  status: "mining" | "ready" | "error";
  stories: StorySummary[] | null;
  counts: Record<string, number> | null;
  // Explains a focus that matched nothing, when `stories` is the fallback set.
  notice: string | null;
  error: string | null;
}

// The stories API returns every match; this is how many of each repo's we show
// before the "show more" toggle. Per repo rather than per feed, so one repo
// can't crowd the others out when several are selected.
const VISIBLE_PER_REPO = 4;

export function StoryCatalogPage() {
  const [params, setSearchParams] = useSearchParams();
  // "repos" is the multi-repo param; "repo" kept for old single-repo links.
  const repos =
    params.get("repos")?.split(",").filter(Boolean) ??
    (params.get("repo") ? [params.get("repo")!] : []);
  const qualities = params.get("qualities")?.split(",").filter(Boolean) ?? [];
  const navigate = useNavigate();

  // Keyed by repo so each one can be replaced the moment it lands, independently
  // of the others — mining times vary by several seconds between repos.
  const [groups, setGroups] = useState<Record<string, RepoStories>>({});

  // Repos whose pipeline has already run this visit. Toggling a quality filter
  // must re-read stories without re-mining.
  const minedRef = useRef<Set<string>>(new Set());

  // Expanding is pure render — every story is already in `groups`, so this
  // fires no request.
  const [showAll, setShowAll] = useState(false);

  const reposKey = repos.join(",");
  const qualitiesKey = qualities.join(",");

  useEffect(() => {
    if (repos.length === 0) return;

    minedRef.current = new Set();
    setGroups(
      Object.fromEntries(
        repos.map((repo) => [
          repo,
          { repo, status: "mining" as const, stories: null, counts: null, notice: null, error: null },
        ]),
      ),
    );

    let cancelled = false;
    for (const repo of repos) {
      runPipelineOnce(repo)
        .then(() => listStories(repo, qualities))
        .then(
          (res) => {
            if (cancelled) return;
            minedRef.current.add(repo);
            setGroups((prev) => ({
              ...prev,
              [repo]: {
                repo,
                status: "ready",
                stories: res.stories,
                counts: res.quality_counts,
                notice: res.notice,
                error: null,
              },
            }));
          },
          (err: Error) => {
            if (cancelled) return;
            setGroups((prev) => ({
              ...prev,
              [repo]: {
                repo,
                status: "error",
                stories: null,
                counts: null,
                notice: null,
                error: err.message,
              },
            }));
          },
        );
    }
    return () => {
      cancelled = true;
    };
    // `qualities` is read for the initial fetch only; later changes are handled
    // by the effect below, which skips the pipeline.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reposKey]);

  // Quality toggles are a read-time, cache-hit call — no mining, no tokens. Only
  // repos that finished mining are re-read; the rest pick the filter up when
  // their initial fetch lands.
  useEffect(() => {
    const mined = repos.filter((r) => minedRef.current.has(r));
    if (mined.length === 0) return;

    let cancelled = false;
    for (const repo of mined) {
      listStories(repo, qualities).then(
        (res) => {
          if (cancelled) return;
          setGroups((prev) => ({
            ...prev,
            [repo]: {
              ...prev[repo],
              stories: res.stories,
              counts: res.quality_counts,
              notice: res.notice,
            },
          }));
        },
        () => {},
      );
    }
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [qualitiesKey]);

  // A new filter or repo set is a new list — collapse back to the preview so
  // the user isn't dropped into the middle of results they didn't ask to expand.
  useEffect(() => {
    setShowAll(false);
  }, [qualitiesKey, reposKey]);

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
  // Render in the order the user picked, not the order they happened to finish,
  // so cards don't reshuffle as later repos land.
  const orderedGroups = repos.map((r) => groups[r]).filter(Boolean);
  const storyCount = orderedGroups.reduce((n, g) => n + (g.stories?.length ?? 0), 0);
  const mining = orderedGroups.filter((g) => g.status === "mining");
  const settled = orderedGroups.filter((g) => g.status !== "mining");

  // How many of `storyCount` the collapsed feed renders. Counted the same way
  // the feed slices — per repo — so the two can't disagree. Comparing the two
  // totals (rather than storyCount against the cap) is what keeps this right
  // for several repos: three repos of three stories each is nine stories with
  // nothing hidden, and no toggle should appear.
  const collapsedCount = orderedGroups.reduce(
    (n, g) => n + Math.min(VISIBLE_PER_REPO, g.stories?.length ?? 0),
    0,
  );
  const expandable = storyCount > collapsedCount;
  const visibleCount = showAll ? storyCount : collapsedCount;

  // Merge per-repo label counts so each chip shows total available stories for
  // that quality across the selected repos.
  const mergedCounts: Record<string, number> = {};
  for (const g of orderedGroups) {
    for (const [k, v] of Object.entries(g.counts ?? {})) {
      mergedCounts[k] = (mergedCounts[k] ?? 0) + v;
    }
  }

  const headline = mining.length
    ? `Found ${storyCount} engineering stories so far… 🌟`
    : showRepoBadges
      ? `We found ${storyCount} engineering stories across ${repos.length} repositories! 🌟`
      : `We found some great stories in ${repos[0]}! 🌟`;

  // Only skeleton until the *first* repo lands — after that there is real
  // content to show while the rest keep mining.
  const loading = settled.length === 0;

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
                  // Deliberately still clickable at zero: the API answers an
                  // empty focus with a fallback set plus an explanation, which
                  // teaches more than a dead control. The dimmed `empty` style
                  // is the hint. Counts also keep accumulating while repos
                  // mine, so a zero there can just mean "not known yet".
                  title={
                    count === 0 && mining.length === 0
                      ? "No stories here carry this quality — we'll show related ones instead"
                      : undefined
                  }
                >
                  {q.label} ({count})
                </button>
              );
            })}
          </div>

          {/* Per-repo progress. Stories below fill in as each repo lands, so
              this explains why the feed is still growing. */}
          {repos.length > 1 && mining.length > 0 && (
            <div className="ab-status">
              {orderedGroups.map((g) => (
                <span
                  key={g.repo}
                  className={`ab-statuspill status-${g.status === "mining" ? "running" : g.status === "error" ? "error" : "done"}`}
                >
                  <span className="dot" aria-hidden="true" />
                  {g.repo.split("/")[1] ?? g.repo}:{" "}
                  {g.status === "mining"
                    ? "mining…"
                    : g.status === "error"
                      ? "failed"
                      : `${g.stories?.length ?? 0} stories`}
                </span>
              ))}
            </div>
          )}

          {orderedGroups.map(
            (g) =>
              g.error && (
                <div key={g.repo} className="warn-card">
                  {g.repo}: {g.error}
                </div>
              ),
          )}

          {/* One per repo: a focus with no matches falls back to that repo's
              other stories, which reads as a broken filter unless we say so.
              Same treatment as the discovery page's widened-search notice. */}
          {orderedGroups.map(
            (g) =>
              g.notice && (
                <div key={`${g.repo}-notice`} className="warn-card discover-notice">
                  {g.notice}
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
              {/* Counts come from the chips' full set, so say plainly how much
                  of it is on screen — otherwise "Usability (6)" above four
                  cards reads as a bug. */}
              {expandable && (
                <p className="catalog-meta">
                  Showing {visibleCount} of {storyCount} stories
                </p>
              )}

              <div className="story-feed">
                {orderedGroups.flatMap(
                  (g) =>
                    (showAll ? g.stories : g.stories?.slice(0, VISIBLE_PER_REPO))?.map((s) => (
                      <StoryCard
                        key={s.story_id}
                        story={s}
                        repoBadge={showRepoBadges ? g.repo : undefined}
                        onOpen={() => navigate(`/workspace?story=${encodeURIComponent(s.story_id)}`)}
                      />
                    )) ?? [],
                )}
                {/* Placeholders for repos still mining, so the feed shows that
                    more is coming rather than looking finished. */}
                {mining.map((g) => (
                  <div key={g.repo} className="story-card skeleton" aria-hidden="true">
                    <div className="sk-line sk-title" />
                    <div className="sk-line sk-tag" />
                  </div>
                ))}
              </div>

              {expandable && (
                <div className="catalog-more">
                  <button className="btn-sm ghost" onClick={() => setShowAll((v) => !v)}>
                    {showAll ? "Show fewer ↑" : `Show ${storyCount - collapsedCount} more ↓`}
                  </button>
                </div>
              )}

              {storyCount === 0 && mining.length === 0 && (
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
