import type { RepoRecommendation } from "../api/types";

interface Props {
  repo: RepoRecommendation;
  busy: boolean;
  onSelect: () => void;
}

export function RepoCard({ repo, busy, onSelect }: Props) {
  return (
    <div className="card">
      <h3>{repo.repo}</h3>
      <p>{repo.summary}</p>
      <button onClick={onSelect} disabled={busy}>
        {busy ? "Analyzing repo..." : "Explore stories"}
      </button>
    </div>
  );
}
