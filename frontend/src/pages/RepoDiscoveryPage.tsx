import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { discoverRepos, runPipeline } from "../api/client";
import type { DiscoverFilters, RepoRecommendation } from "../api/types";
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

  if (!filters) {
    return (
      <p className="page">
        No filters provided. <a href="/">Go back</a>
      </p>
    );
  }
  if (error && !mining && !repos) return <p className="page error">{error}</p>;
  if (!repos) {
    return (
      <p className="page">
        Searching GitHub for matching repos... this can take up to 30 seconds.
      </p>
    );
  }

  const domainLabel = DOMAINS.find((d) => d.id === filters.domain)?.label ?? filters.domain;
  const heading = filters.keyword ? `${domainLabel}: "${filters.keyword}"` : domainLabel;

  return (
    <div className="page">
      <h1>Repos for {heading}</h1>
      <p>Select up to {MAX_SELECTED} repositories to mine stories from.</p>
      {error && <p className="error">{error}</p>}
      <div className="grid">
        {repos.map((r) => (
          <RepoCard
            key={r.repo}
            repo={r}
            selected={selected.includes(r.repo)}
            disabled={mining || (!selected.includes(r.repo) && selected.length >= MAX_SELECTED)}
            onToggle={() => toggleRepo(r.repo)}
          />
        ))}
      </div>

      {selected.length > 0 && (
        <div className="select-bar">
          <div className="select-bar-section">
            <span className="select-bar-label">Story quality focus (optional):</span>
            <div className="filter-row">
              {QUALITIES.map((q) => (
                <button
                  key={q.id}
                  type="button"
                  className={`chip${qualities.includes(q.id) ? " chip-active" : ""}`}
                  onClick={() => toggleQuality(q.id)}
                  disabled={mining}
                >
                  {q.label}
                </button>
              ))}
            </div>
          </div>
          {mining && (
            <div className="select-bar-section">
              {selected.map((repo) => (
                <span key={repo} className={`status-item status-${pipelineStatus[repo]}`}>
                  {repo}:{" "}
                  {pipelineStatus[repo] === "running"
                    ? "mining..."
                    : pipelineStatus[repo] === "done"
                      ? "done"
                      : "failed"}
                </span>
              ))}
            </div>
          )}
          <button onClick={handleMine} disabled={mining}>
            {mining
              ? "Mining stories... (first run can take a few minutes)"
              : `Mine stories (${selected.length} repo${selected.length > 1 ? "s" : ""})`}
          </button>
        </div>
      )}
    </div>
  );
}
