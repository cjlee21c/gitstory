import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { discoverRepos, runPipeline } from "../api/client";
import type { DiscoverFilters, RepoRecommendation } from "../api/types";
import { AppHeader } from "../components/AppHeader";
import { RepoCard } from "../components/RepoCard";
import { DOMAINS, QUALITIES } from "../filters";

const MAX_SELECTED = 3;

type PipelineStatus = "running" | "done" | "error";

function filtersFromParams(params: URLSearchParams): DiscoverFilters | null {
  const domain = params.get("domain");
  if (!domain) return null;
  return {
    domain,
    sizes: params.get("sizes")?.split(",").filter(Boolean) ?? [],
    stars: params.get("stars"),
    contributors: params.get("contributors"),
    keyword: params.get("keyword"),
  };
}

export function RepoDiscoveryPage() {
  const [params] = useSearchParams();
  const filters = filtersFromParams(params);
  const navigate = useNavigate();

  const [repos, setRepos] = useState<RepoRecommendation[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<string[]>([]);
  const [qualities, setQualities] = useState<string[]>([]);
  const [pipelineStatus, setPipelineStatus] = useState<Record<string, PipelineStatus>>({});
  const [mining, setMining] = useState(false);

  const filterKey = params.toString();
  useEffect(() => {
    if (!filters) return;
    setRepos(null);
    setError(null);
    setSelected([]);
    discoverRepos(filters)
      .then(setRepos)
      .catch((e: Error) => setError(e.message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filterKey]);

  function toggleRepo(repo: string) {
    setSelected((prev) =>
      prev.includes(repo)
        ? prev.filter((r) => r !== repo)
        : prev.length < MAX_SELECTED
          ? [...prev, repo]
          : prev,
    );
  }

  function toggleQuality(id: string) {
    setQualities((prev) => (prev.includes(id) ? prev.filter((q) => q !== id) : [...prev, id]));
  }

  async function handleMine() {
    setMining(true);
    setError(null);
    setPipelineStatus(Object.fromEntries(selected.map((r) => [r, "running" as PipelineStatus])));

    const results = await Promise.allSettled(
      selected.map((repo) =>
        runPipeline(repo).then(
          (res) => {
            setPipelineStatus((prev) => ({ ...prev, [repo]: "done" }));
            return res;
          },
          (err) => {
            setPipelineStatus((prev) => ({ ...prev, [repo]: "error" }));
            throw err;
          },
        ),
      ),
    );

    const succeeded = selected.filter((_, i) => results[i].status === "fulfilled");
    const failed = selected.filter((_, i) => results[i].status === "rejected");

    if (succeeded.length === 0) {
      setError("Story mining failed for all selected repos. Please try again.");
      setMining(false);
      return;
    }

    const query = new URLSearchParams({ repos: succeeded.join(",") });
    if (qualities.length) query.set("qualities", qualities.join(","));
    if (failed.length) query.set("failed", failed.join(","));
    navigate(`/stories?${query.toString()}`);
  }

  // No domain in the URL — nothing to discover.
  if (!filters) {
    return (
      <div className="landing discover">
        <div className="landing-inner">
          <AppHeader />
          <main className="landing-main">
            <div className="discover-empty">
              <h1>No filters selected</h1>
              <p>Head back and pick a domain to find repositories.</p>
              <button className="btn-lg btn-mint" onClick={() => navigate("/")}>
                Back to start <span className="arrow" aria-hidden="true">→</span>
              </button>
            </div>
          </main>
        </div>
      </div>
    );
  }

  const domainLabel = DOMAINS.find((d) => d.id === filters.domain)?.label ?? filters.domain;
  const heading = filters.keyword ? `${domainLabel}: "${filters.keyword}"` : domainLabel;
  const count = selected.length;
  const loading = !repos && !error;

  const primaryLabel = mining
    ? "Mining stories… (first run can take a few minutes)"
    : count === 0
      ? "Select repositories to continue"
      : `Generate stories for ${count} repositor${count === 1 ? "y" : "ies"} →`;

  return (
    <div className="landing">
      <div className="landing-inner">
        <AppHeader />

        <main className="discover-main">
          <section className="discover-hero">
            <span className="step-capsule">Step 2 of 3</span>
            <h1>Select repositories to explore</h1>
            <p>
              Choose up to {MAX_SELECTED} repositories from <strong>{heading}</strong>. We'll mine
              them to find the best engineering stories.
            </p>
          </section>

          {error && !mining && <div className="warn-card">{error}</div>}

          {loading ? (
            <div className="repo-grid" aria-busy="true">
              <p className="discover-loading">🔎 Searching GitHub for matching repos… this can take up to 30 seconds.</p>
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="repo-card skeleton" aria-hidden="true">
                  <div className="sk-line sk-title" />
                  <div className="sk-line sk-tag" />
                  <div className="sk-line" />
                  <div className="sk-line sk-short" />
                </div>
              ))}
            </div>
          ) : repos && repos.length === 0 ? (
            <div className="warn-card">
              No repositories matched these filters. Try widening your search.
            </div>
          ) : (
            <div className="repo-grid">
              {repos?.map((r) => (
                <RepoCard
                  key={r.repo}
                  repo={r}
                  selected={selected.includes(r.repo)}
                  disabled={mining || (!selected.includes(r.repo) && count >= MAX_SELECTED)}
                  onToggle={() => toggleRepo(r.repo)}
                />
              ))}
            </div>
          )}
        </main>

        <div className="discover-actionbar">
          {count > 0 && (
            <div className="ab-qualities">
              <span className="ab-label">Story focus (optional):</span>
              {QUALITIES.map((q) => (
                <button
                  key={q.id}
                  type="button"
                  className="pill"
                  aria-pressed={qualities.includes(q.id)}
                  onClick={() => toggleQuality(q.id)}
                  disabled={mining}
                >
                  {q.label}
                </button>
              ))}
            </div>
          )}

          {mining && (
            <div className="ab-status">
              {selected.map((repo) => (
                <span key={repo} className={`ab-statuspill status-${pipelineStatus[repo]}`}>
                  <span className="dot" aria-hidden="true" />
                  {repo.split("/")[1] ?? repo}:{" "}
                  {pipelineStatus[repo] === "running"
                    ? "mining…"
                    : pipelineStatus[repo] === "done"
                      ? "done"
                      : "failed"}
                </span>
              ))}
            </div>
          )}

          <div className="ab-row">
            <button className="btn-sm ghost ab-back" onClick={() => navigate(-1)} disabled={mining}>
              ← Back
            </button>
            <button
              className="btn-lg btn-mint"
              onClick={handleMine}
              disabled={mining || count === 0}
            >
              {primaryLabel}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
