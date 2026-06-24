import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { discoverRepos, runPipeline } from "../api/client";
import type { RepoRecommendation } from "../api/types";
import { RepoCard } from "../components/RepoCard";

export function RepoDiscoveryPage() {
  const [params] = useSearchParams();
  const interest = params.get("interest") ?? "";
  const navigate = useNavigate();

  const [repos, setRepos] = useState<RepoRecommendation[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selecting, setSelecting] = useState<string | null>(null);

  useEffect(() => {
    if (!interest) return;
    setRepos(null);
    setError(null);
    discoverRepos(interest)
      .then(setRepos)
      .catch((e: Error) => setError(e.message));
  }, [interest]);

  async function handleSelect(repo: string) {
    setSelecting(repo);
    setError(null);
    try {
      await runPipeline(repo);
      navigate(`/stories?repo=${encodeURIComponent(repo)}`);
    } catch (e) {
      setError((e as Error).message);
      setSelecting(null);
    }
  }

  if (!interest) {
    return (
      <p className="page">
        No interest provided. <a href="/">Go back</a>
      </p>
    );
  }
  if (error) return <p className="page error">{error}</p>;
  if (!repos) {
    return (
      <p className="page">Searching GitHub for repos matching "{interest}"... this can take up to 30 seconds.</p>
    );
  }

  return (
    <div className="page">
      <h1>Repos for "{interest}"</h1>
      <div className="grid">
        {repos.map((r) => (
          <RepoCard key={r.repo} repo={r} busy={selecting === r.repo} onSelect={() => handleSelect(r.repo)} />
        ))}
      </div>
    </div>
  );
}
